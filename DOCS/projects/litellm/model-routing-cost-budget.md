# LiteLLM Model Routing / Cost / Token Budget 初步笔记

> **日期**: 2026-07-09 | **状态**: draft | **涉及版本**: `e84a19acd566f6ac95ec6346ba603104adea728f`

## 相关文档

- 项目入口：[LiteLLM 学习笔记](README.md)
- 横向专题：[Model Routing / Cost / Token Budget 横向总结](../../comparison/model-routing-cost-token-budget.md)
- 权限专题：[Permission / Security 横向笔记](../../comparison/permission-security.md)

## 一句话结论

LiteLLM 的 Router 不是简单的“随机挑一个模型”，而是一条 **候选池过滤 -> 路由策略选择 -> 失败恢复 -> 指标回写** 的模型调度流水线。

可以把它理解成：

> **模型网关调度站。** 先确认调用方有资格访问哪些 model group / deployment；再排除坏掉、超预算、超限流、标签不匹配的候选；然后按“随机 / 最空闲 / 最少用量 / 最低延迟 / 最低成本 / 智能分层”等策略选一个；如果失败，再按 retry / fallback / cooldown 预案恢复；最后把 latency、usage、spend、failure 等运行指标写回网关状态。

## 一、延迟 / 健康状态不是传统长期记忆

讨论中容易把 “historical latency” 和 “provider health” 理解成 Agent 记忆。这里需要区分：LiteLLM 常规路由记录的不是用户偏好、任务历史或长期经验，而是 **短窗口运行指标缓存**。

### 1.1 latency-based routing 记的是近期响应表现

Latency routing 会在调用成功后记录每个 deployment 的近期响应时间。非 streaming 场景主要看整体响应时间；streaming 场景更关注 time-to-first-token。

源码入口：

- 默认参数：`ttl` 默认 1 小时，`max_latency_list_size` 默认 10，见 [lowest_latency.py](../../../submodules/litellm/litellm/router_strategy/lowest_latency.py#L22-L26)
- 成功后写入 latency / TTFT / TPM / RPM，见 [lowest_latency.py](../../../submodules/litellm/litellm/router_strategy/lowest_latency.py#L37-L152) 与异步版本 [lowest_latency.py](../../../submodules/litellm/litellm/router_strategy/lowest_latency.py#L225-L345)
- 选择时按平均 latency 排序，并在 lowest latency buffer 范围内随机选一个，见 [lowest_latency.py](../../../submodules/litellm/litellm/router_strategy/lowest_latency.py#L358-L493)

所以这里的“历史”更像：

```text
最近一小时 / 最近若干次调用里，哪个 deployment 更快？
```

而不是：

```text
这个用户过去喜欢哪个模型？这个 provider 长期表现如何？
```

### 1.2 health / cooldown 记的是近期故障状态

LiteLLM 的健康状态主要来自两条线。

第一条是 **请求失败后的 cooldown**：某个 deployment 如果近期失败过多，或遇到 429 / 401 / 404 / 408 / 5xx 等需要避开的错误，会被暂时放进 cooldown 列表，后续路由时从候选池里过滤掉。

源码入口：

- 失败回调会记录失败并尝试设置 cooldown，见 [router.py](../../../submodules/litellm/litellm/router.py#L6890-L6956)
- cooldown 是否触发会看错误码、失败率、allowed_fails / allowed_fails_policy 等，见 [cooldown_handlers.py](../../../submodules/litellm/litellm/router_utils/cooldown_handlers.py#L151-L227)
- 已 cooldown 的 deployment 会从候选池过滤，见 [router.py](../../../submodules/litellm/litellm/router.py#L10931-L10948)

第二条是 **background health check 的健康状态**：如果开启 health-check routing，后台健康检查可以把 deployment 标记成 unhealthy；Router 读取这个状态并过滤候选。

源码入口：

- DeploymentHealthCache 保存 deployment_id -> health state，并用 staleness threshold 避免旧状态长期生效，见 [health_state_cache.py](../../../submodules/litellm/litellm/router_utils/health_state_cache.py#L29-L36)
- 取 healthy deployments 时会先做 health-check filter，再做 cooldown filter，见 [router.py](../../../submodules/litellm/litellm/router.py#L10271-L10296)

**精髓标记：** LiteLLM 常规 Router 的“记忆”是机器调度视角的短期运行状态，不是 Agent 视角的长期用户记忆。

### 1.3 例外：adaptive router 接近学习型路由

LiteLLM 还有更高级的 adaptive router。它会把请求分成 request type，并为 `(request_type, model)` 维护 bandit 状态；调用后根据 response 信号更新质量估计，并批量写入 Postgres。

源码说明见 [adaptive_router/README.md](../../../submodules/litellm/litellm/router_strategy/adaptive_router/README.md#L1-L11)。它的 cold start、per-request decision、owner-cache attribution、per-turn updates 和 persistence 说明见 [adaptive_router/README.md](../../../submodules/litellm/litellm/router_strategy/adaptive_router/README.md#L51-L70)。

所以可以这样分类：

| 机制 | 是否长期记忆 | 记什么 |
|---|---:|---|
| least-busy | 否 | 当前 in-flight 请求数 |
| usage-based-routing | 否 | 当前分钟 TPM / RPM |
| latency-based-routing | 否 | 近期 latency / TTFT 样本 |
| cooldown | 否 | 近期失败 deployment |
| health-check routing | 否 | 未过期的健康检查结果 |
| adaptive router | 部分是 | request type / model 的质量反馈与 bandit 状态 |

## 二、自动 fallback / provider 切换不是无限授权

LiteLLM 的自动切换需要放在授权边界里理解。它不是“用户给了一个 key，网关就可以任意换 provider / 任意换模型”，而是：

```text
管理员预先配置 provider credentials / model_list / deployment / fallback
  +
virtual key 限制调用方能访问哪些 model / route / budget / rate limit
  +
team / org / project / access group 继续收窄权限
  +
fallback 目标也必须通过模型访问检查
```

### 2.1 第一层：管理员配置 model group / deployment

LiteLLM 只能在配置里存在的 deployment 里选。用户请求的通常是 public model name / model group，例如 `company-fast-model` 或 `gpt-4o`；这个 model group 背后可以绑定多个实际 deployment。

如果管理员没有配置某个 provider API key、deployment 或 fallback，网关不会凭空切过去。

### 2.2 第二层：virtual key 绑定访问范围、预算和速率

LiteLLM 的 key 不是普通 bearer token，而是可以携带模型访问范围、预算、速率和路由设置的对象。

Key 生成 / 更新请求里能看到这些字段：

- `models`
- `max_budget`
- `tpm_limit` / `rpm_limit`
- `model_max_budget`
- `model_tpm_limit` / `model_rpm_limit`
- `budget_fallbacks`
- `permissions`
- `guardrails` / `policies`
- `allowed_routes`
- `router_settings`
- `access_group_ids`

源码入口见 [proxy/_types.py](../../../submodules/litellm/litellm/proxy/_types.py#L1018-L1086)。

模型访问检查会判断 requested model 是否在 key / team / alias / wildcard / access group 允许范围内，见 [auth_checks.py](../../../submodules/litellm/litellm/proxy/auth/auth_checks.py#L2866-L2930) 与 key 级入口 [auth_checks.py](../../../submodules/litellm/litellm/proxy/auth/auth_checks.py#L2969-L3013)。

### 2.3 第三层：fallback 目标也要过权限检查

这是本轮讨论里最重要的授权点：fallback 不能绕过 key 的模型 allowlist。

LiteLLM 会检查三类 fallback 字段：

- `fallbacks`
- `context_window_fallbacks`
- `content_policy_fallbacks`

无论这些 fallback 出现在请求顶层，还是出现在 `router_settings_override` 里，LiteLLM 都会抽出 leaf model name，逐个调用 `can_key_call_model`，并用 `is_valid_fallback_model` 确认能被正常路由。源码入口见 [user_api_key_auth.py](../../../submodules/litellm/litellm/proxy/auth/user_api_key_auth.py#L2765-L2828)。

因此它不是：

```text
用户被允许调用 A，fallback 可以偷偷切到 B
```

而是：

```text
用户被允许调用 A；如果 fallback 要切到 B，B 也必须是这个 key 被允许访问、且 Router 能正常路由的模型
```

### 2.4 授权形态：预授权，不是每次 HITL 审批

LiteLLM 的授权更像企业网关的预授权，而不是 Claude Code / OpenHands 那种工具执行前弹窗确认。

Agent Harness 里的权限常问：

```text
这次 bash / edit / delete 是否危险？要不要问用户确认？
```

LiteLLM 网关里的权限更常问：

```text
这个 key 是否能访问这个 model group？
这个 team / org / project 是否有预算？
这个 fallback 目标是否在 allowlist 内？
这个 route 是否允许？
这个 deployment 是否被 admin paused / blocked？
```

**精髓标记：** LiteLLM 的自动切换是“配置边界内的自动恢复”，不是“越权切换”。它依赖管理员配置、virtual key、team / org / project、预算和 fallback 校验共同形成边界。

## 三、Router 总流程

LiteLLM Router 可以抽象为这条流水线：

```text
用户请求 model
  -> 解析 model group / alias
  -> 找出候选 deployments
  -> 过滤 team / blocked / health check / cooldown / tag / budget / pre-call checks
  -> 按 routing_strategy 选择 deployment
  -> 调用真实 provider
  -> 记录 success / failure / latency / usage / spend
  -> 失败时 retry / cooldown / fallback
```

相关源码入口：

- RoutingStrategy 枚举： [types/router.py](../../../submodules/litellm/litellm/types/router.py#L746-L753)
- Router 初始化 selector： [router.py](../../../submodules/litellm/litellm/router.py#L783-L865)
- 异步策略分发： [router.py](../../../submodules/litellm/litellm/router.py#L1006-L1057)
- healthy deployments 过滤流程： [router.py](../../../submodules/litellm/litellm/router.py#L10218-L10345)

## 四、核心路由策略文字整理

### 4.1 simple-shuffle：默认随机 / 加权随机

simple-shuffle 是默认策略。它会在 healthy deployments 里随机选一个；如果 deployment 配了 `weight`、`rpm` 或 `tpm`，则按这些字段加权随机。

源码入口：[simple_shuffle.py](../../../submodules/litellm/litellm/router_strategy/simple_shuffle.py#L20-L68)

适合场景：

- 多个 deployment 大体等价
- 只想做简单负载均衡
- 不希望引入复杂状态

设计精髓：

> 先把流量摊开，保持策略简单稳定。

### 4.2 least-busy：选择当前最不忙的 deployment

least-busy 关注当前并发。请求发出前增加 in-flight count；成功或失败后减少 count；选择时找当前 request_count 最低的 deployment。

源码入口：

- pre-call 增加计数：[least_busy.py](../../../submodules/litellm/litellm/router_strategy/least_busy.py#L23-L47)
- success / failure 后减少计数：[least_busy.py](../../../submodules/litellm/litellm/router_strategy/least_busy.py#L49-L97)
- 选择最少请求的 deployment：[least_busy.py](../../../submodules/litellm/litellm/router_strategy/least_busy.py#L159-L187)

适合场景：

- 请求耗时差异较大
- 某些 deployment 当前排队更多
- 希望新请求优先派给空闲后端

设计精髓：

> 看每个窗口前面排了几个人，而不是看长期历史表现。

### 4.3 usage-based-routing / usage-based-routing-v2：按 TPM/RPM 使用量选

usage-based routing 关注当前分钟的 token / request 使用量。v2 版本更适合多实例和并发场景，会用 cache / Redis 记录每个 deployment 当前分钟的 TPM/RPM。

它大致会：

1. 读取每个 deployment 当前分钟 TPM/RPM
2. 估算本次请求 input tokens
3. 过滤即将超过 TPM/RPM 的候选
4. 选择当前 TPM 最低的 deployment
5. 多个一样低时随机选

源码入口：

- pre-call RPM 检查：[lowest_tpm_rpm_v2.py](../../../submodules/litellm/litellm/router_strategy/lowest_tpm_rpm_v2.py#L59-L139)
- 选择低 TPM/RPM deployment：[lowest_tpm_rpm_v2.py](../../../submodules/litellm/litellm/router_strategy/lowest_tpm_rpm_v2.py#L315-L429)

适合场景：

- provider 有明确 RPM / TPM 限流
- 多个 API key / deployment 需要分摊压力
- 想尽量减少 429

设计精髓：

> 把请求放到还没用满额度的 deployment 上，避免某个 provider key 被打爆。

### 4.4 latency-based-routing：选近期响应最快的 deployment

latency-based routing 关注近期 latency / time-to-first-token。它会保留每个 deployment 最近若干次 latency 样本，选择平均 latency 最低的一组候选，并在 buffer 范围内随机挑一个。

源码入口：

- 参数和样本窗口：[lowest_latency.py](../../../submodules/litellm/litellm/router_strategy/lowest_latency.py#L22-L26)
- latency 记录：[lowest_latency.py](../../../submodules/litellm/litellm/router_strategy/lowest_latency.py#L37-L152)
- timeout 惩罚：[lowest_latency.py](../../../submodules/litellm/litellm/router_strategy/lowest_latency.py#L165-L213)
- deployment 选择：[lowest_latency.py](../../../submodules/litellm/litellm/router_strategy/lowest_latency.py#L358-L493)

适合场景：

- chat UI / streaming answer
- 多 region deployment
- 用户体验强依赖响应速度

设计精髓：

> 谁最近响应快，就让谁多接请求；但仍保留 buffer 内随机，避免过度集中。

### 4.5 cost-based-routing：选单位成本最低的 deployment

cost-based routing 关注 token 单价。它会看 deployment 上配置的 `input_cost_per_token` / `output_cost_per_token`，或 LiteLLM 内置 model cost map，然后按输入输出单价之和排序，选择最便宜的 deployment。

源码入口：[lowest_cost.py](../../../submodules/litellm/litellm/router_strategy/lowest_cost.py#L250-L305)

适合场景：

- 同类任务可以由多个模型完成
- 希望默认走便宜模型
- 多 provider 价格不同

设计精髓：

> 成本优先不是“不用强模型”，而是让便宜模型优先处理足够简单或等价的请求。

### 4.6 provider-budget-routing / budget limiter：预算过滤器

budget limiter 更像过滤器，而不是单独选择器。它会在候选池中排除已经超过 provider / deployment / tag budget 的 deployment。这个过滤器可以和 simple-shuffle、latency-based、cost-based 等策略组合。

源码入口：

- 文件说明中明确它是 filter：[budget_limiter.py](../../../submodules/litellm/litellm/router_strategy/budget_limiter.py#L1-L8)
- 过滤超预算候选：[budget_limiter.py](../../../submodules/litellm/litellm/router_strategy/budget_limiter.py#L114-L188)
- 检查 provider / deployment / tag budget：[budget_limiter.py](../../../submodules/litellm/litellm/router_strategy/budget_limiter.py#L190-L206)

适合场景：

- 某 provider 本月预算用完后自动避开
- 某 deployment 超预算后切到其他 deployment
- 某 tag / tenant / project 超预算后限制调用

设计精髓：

> 先问“谁还允许继续花钱”，再问“谁最快 / 最便宜 / 最空闲”。

### 4.7 tag-based routing：按 tag / header 分流

tag-based routing 也是过滤器。它会用请求 metadata 里的 tags 匹配 deployment 上的 tags，也可以用 `tag_regex` 匹配 header。

源码入口：[tag_based_routing.py](../../../submodules/litellm/litellm/router_strategy/tag_based_routing.py#L151-L220)

适合场景：

- team A 只走 team-a deployment
- EU 请求只走 EU region
- 特定 client / User-Agent 走专门 deployment
- 某些 tenant 排除某类 provider

设计精髓：

> tag 决定候选池边界，不直接决定谁最快或最便宜。

### 4.8 cooldown / health-check routing：避开近期故障后端

cooldown / health-check routing 是所有策略前面的健康过滤层。它不会直接回答“谁最好”，而是先排除明显坏掉或近期不该再打的 deployment。

源码入口：

- cooldown 判断：[cooldown_handlers.py](../../../submodules/litellm/litellm/router_utils/cooldown_handlers.py#L151-L227)
- cooldown 过滤：[router.py](../../../submodules/litellm/litellm/router.py#L10931-L10948)
- health state cache：[health_state_cache.py](../../../submodules/litellm/litellm/router_utils/health_state_cache.py#L29-L36)
- health-check filter：[router.py](../../../submodules/litellm/litellm/router.py#L10978-L11010)

适合场景：

- provider region 挂了
- 某个 key 429 了
- 某个 deployment auth 失效
- 某个 endpoint 一直 timeout

设计精髓：

> 高可用调度的第一步不是选最优，而是别继续打坏后端。

### 4.9 retry / fallback：失败后的恢复路径

retry / fallback 不是首次选择策略，而是失败后的恢复机制。

Router 类型里可以看到相关字段：`num_retries`、`fallbacks`、`context_window_fallbacks`、`model_group_alias`、`retry_policy`、`model_group_retry_policy` 等，见 [types/router.py](../../../submodules/litellm/litellm/types/router.py#L64-L78) 与 [types/router.py](../../../submodules/litellm/litellm/types/router.py#L84-L119)。

它可以抽象成：

```text
第一次选中 deployment A
  -> 调用失败
  -> 如果可重试，按 retry_policy 重试
  -> 如果 A 需要避开，把 A cooldown / 排除
  -> 同 model group 内尝试其他 deployment
  -> 如果配置了 cross-model fallback，再切到 fallback model group
  -> 如果 context window 超限，可走 context_window_fallbacks
  -> 如果内容策略失败，可走 content_policy_fallbacks
```

关键授权点是：fallback 目标也必须通过 key 的模型访问检查，见 [user_api_key_auth.py](../../../submodules/litellm/litellm/proxy/auth/user_api_key_auth.py#L2765-L2828)。

设计精髓：

> fallback 是预授权边界内的自动恢复，不是绕过权限的后门。

### 4.10 complexity_router：按请求复杂度选模型档位

complexity_router 是本地规则型智能路由。它不调用外部 API，而是用规则和权重把请求分成 SIMPLE / MEDIUM / COMPLEX / REASONING，再映射到不同模型。

README 里列出的维度包括 tokenCount、codePresence、reasoningMarkers、technicalTerms、simpleIndicators、multiStepPatterns、questionComplexity，见 [complexity_router/README.md](../../../submodules/litellm/litellm/router_strategy/complexity_router/README.md#L13-L35)。

适合场景：

- 简单问题走便宜模型
- 复杂技术任务走强模型
- 推理任务走 reasoning model
- 希望低延迟、无额外分类 API 调用

设计精髓：

> 按任务复杂度分配模型档位，而不是所有请求都用同一个脑子。

### 4.11 adaptive_router：按质量反馈学习路由

adaptive_router 会对请求类型和模型维护 bandit 状态，结合质量和成本做选择，并在调用后根据 response signals 更新状态。

源码说明见 [adaptive_router/README.md](../../../submodules/litellm/litellm/router_strategy/adaptive_router/README.md#L1-L11)。

适合场景：

- 模型池复杂
- 不同模型擅长不同任务
- 希望随着真实流量调整模型选择

设计风险：

- 反馈信号是否可靠
- 质量 / 成本权重如何调
- bandit 学错后如何观测和回滚
- 多 tenant 是否共享学习状态

设计精髓：

> 从静态规则路由，进一步走向基于真实调用反馈的在线调度。

### 4.12 LAR-1 routing：按 Agent confidence 选模型档位

LAR-1 routing 会读取请求 metadata 里的 `lar1` 信息，例如 confidence、evidence、time，并据此选择不同类型的 deployment。

源码入口：

- 文件说明：[lar1_routing.py](../../../submodules/litellm/litellm/router_strategy/lar1_routing.py#L1-L7)
- 分类逻辑：[lar1_routing.py](../../../submodules/litellm/litellm/router_strategy/lar1_routing.py#L133-L153)

它可以把请求分到类似这些模型类型：

- `cloud-smart`
- `cloud-fast`
- `local`
- `deep`

适合场景：

- Agent 能表达自身置信度
- 低置信度任务走更强模型
- 高置信度或低风险任务走本地 / 快速模型
- 需要把 Agent 自评传给模型网关做调度

设计精髓：

> Agent 不只请求“一个模型”，还可以把自己对任务风险和置信度的判断交给网关参与调度。

## 五、核心策略总表

| 策略 / 过滤器 | 主要依据 | 状态来源 | 适合场景 |
|---|---|---|---|
| simple-shuffle | 随机 / weight / rpm / tpm 权重 | 几乎无 | 默认负载均衡 |
| least-busy | 当前 in-flight 请求数 | 实时计数 | 并发均衡 |
| usage-based-routing-v2 | 当前分钟 TPM/RPM | 分钟级 cache / Redis | 避免 rate limit |
| latency-based-routing | 最近 latency / TTFT | 短窗口 latency cache | 低延迟服务 |
| cost-based-routing | input/output token 单价 | 价格表 / deployment 配置 | 成本优先 |
| provider-budget-routing | provider / deployment / tag spend | spend cache / budget window | 预算治理 |
| tag-based routing | request tags / header regex | 请求 metadata / deployment tags | tenant / region / client 分流 |
| cooldown | 错误码 / 失败率 / allowed_fails | 短期 cooldown cache | 避开坏后端 |
| health-check routing | background health check | health state cache | 主动健康过滤 |
| retry / fallback | 错误类型 / fallback 配置 | 尝试状态 + 权限检查 | 高可用恢复 |
| complexity_router | 本地复杂度规则评分 | 无长期学习 | 简单任务走便宜模型 |
| adaptive_router | request type + bandit 反馈 | Postgres / owner cache | 在线学习型路由 |
| LAR-1 | Agent confidence / evidence / time | 请求 metadata | Agent 自评驱动模型档位 |

## QA / 讨论记录

### Q: LiteLLM 的 latency / health routing 算长期记忆吗？

> **状态**: draft
> **来源**: discussion / source-code

A: 常规 latency / health routing 不算传统长期记忆。它记录的是短窗口运行指标，例如 latency 样本、time-to-first-token、当前分钟 TPM/RPM、in-flight 请求数、失败次数、cooldown 状态和 health check 结果。这些状态服务于机器调度，不服务于用户偏好或任务历史。只有 adaptive router 这类学习型路由，才部分接近“长期学习”，因为它会维护 request type / model 的质量反馈和 bandit 状态。

### Q: provider 故障自动切换是否意味着用户把所有切换权都交给网关？

> **状态**: draft
> **来源**: discussion / source-code

A: 不是。LiteLLM 的自动切换发生在预授权边界内。管理员先配置 provider credentials、model_list、deployment 和 fallback；virtual key 再限制调用方可访问的 models、routes、budget、TPM/RPM、guardrails、policies、access groups 等；team / org / project 还会继续收窄边界。尤其是 fallback 目标也要经过 key 的模型访问检查，不能通过 fallback 偷偷调用 key 不允许访问的模型。

### Q: LiteLLM Router 的核心设计不是某个算法，而是什么？

> **状态**: draft
> **来源**: discussion / source-code

A: 核心不是某个单点算法，而是“候选池过滤 + 策略选择 + 失败恢复 + 指标回写”的调度流水线。先确认调用方有资格访问哪些 model group / deployment；再排除 blocked、health check unhealthy、cooldown、tag 不匹配、budget 超限、TPM/RPM 超限的候选；然后按 simple-shuffle、least-busy、usage-based、latency-based、cost-based、complexity、adaptive、LAR-1 等策略选 deployment；失败后通过 retry / fallback / cooldown 恢复；最后把 latency、usage、spend、failure 写回网关状态。

### Q: LiteLLM 与 DeerFlow 的网关机制应该如何分工？

> **状态**: draft
> **来源**: discussion / source-code

A: LiteLLM 更适合作为 DeerFlow 下方的模型网关，而不是替代 DeerFlow Gateway。DeerFlow Gateway 管 Agent run 生命周期、runtime context、lead agent / subagent、tools、sandbox 和 middleware；LiteLLM Gateway 管 provider credentials、model group / deployment、routing strategy、virtual key、budget、fallback、cooldown 和 spend tracking。推荐接入方式是让 DeerFlow 的模型出口通过 OpenAI-compatible client 指向 LiteLLM Proxy，把真实 provider 路由、预算和 fallback 交给 LiteLLM，同时 DeerFlow 保留 per-run TokenBudgetMiddleware、model_name allowlist 和 Agent runtime 治理。详见 [Model Routing / Cost / Token Budget 横向总结](../../comparison/model-routing-cost-token-budget.md#九litellm-与-deerflow模型网关机制边界与接入设想)。
