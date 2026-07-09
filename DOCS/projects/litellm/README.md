# LiteLLM 学习笔记

> LLM Gateway / AI Gateway 方向的开源实现，用于研究统一模型入口、provider adapter、OpenAI-compatible proxy、model routing、budget / spend tracking、fallback / retry 与 guardrails 等模型治理基础设施。

## 源码

- **Submodule**: [litellm/](../../../submodules/litellm/) — 指向 `BerriAI/litellm`
- **官方仓库**: [github.com/BerriAI/litellm](https://github.com/BerriAI/litellm)
- **当前快照**: `e84a19acd566f6ac95ec6346ba603104adea728f`

## 研究定位

LiteLLM 在本仓库中暂不作为一个完整 Agent Harness 主线，而作为 **LLM Gateway / Model Routing 基础设施** 样本来研究。

它和 DeerFlow、Claw-Code、OpenClaw、Hermes Agent、OpenHands 的关系是：这些 Harness 关心“Agent 如何循环、调用工具、管理上下文和执行任务”；LiteLLM 更靠近底层模型访问控制面，关心“多个模型 / 多个 provider 如何被统一接入、路由、限额、计费、降级和观测”。

后续研读重点包括：

- OpenAI-compatible proxy 如何把上层应用请求统一接入不同 LLM provider
- model list、deployment、router strategy、fallback / retry 如何组成模型调度层
- model price map、token usage、spend logs、budget manager 如何支撑成本归因和预算控制
- virtual key、user / team / org budget 如何把模型成本治理前移到网关层
- guardrails、callbacks、logging、metrics 如何变成模型调用的横切治理面

一句话定位：

> **LiteLLM 像是 Agent Harness 下面的“模型网关收费站 + 调度站”。Agent 决定要不要调用模型，LiteLLM 负责把调用送到哪个 provider、花多少钱、有没有超预算、失败后怎么 fallback、以及这笔账记到谁头上。**

## 笔记索引

| 文档 | 状态 | 说明 |
|---|---|---|
| `gateway-architecture.md` | planned | LiteLLM Gateway / Proxy 总体架构：SDK、proxy server、router、provider adapter 与管理面。 |
| `model-routing-cost-budget.md` | draft | LiteLLM Model Routing / Cost / Token Budget：router strategy、latency / health cache、virtual key 授权边界、fallback 校验、model price map、spend tracking、budget manager 与限流预算。 |
| `provider-adapters.md` | planned | Provider adapter / OpenAI-compatible schema 转换：不同 provider 的参数、响应、异常和 token usage 如何统一。 |
| `proxy-auth-permission.md` | planned | Proxy auth / virtual key / user-team-org 权限与预算边界。 |
| `observability-guardrails.md` | planned | Logging、callbacks、metrics、guardrails 与调用链观测。 |

## 源码入口

| 模块 | 源码 | 说明 |
|---|---|---|
| 项目入口说明 | [README.md](../../../submodules/litellm/README.md) | 官方 README：LiteLLM 的 SDK、AI Gateway、OpenAI-compatible proxy、supported endpoints 与核心功能概览。 |
| Python SDK 主入口 | [main.py](../../../submodules/litellm/litellm/main.py) | `completion` 等 SDK 调用入口，后续用于理解 direct SDK mode 和 proxy mode 的边界。 |
| Router 主体 | [router.py](../../../submodules/litellm/litellm/router.py) | LiteLLM Router 主实现，后续重点看 deployment selection、fallback、retry、pre-call checks 与 response metadata。 |
| Router 类型 | [router.py](../../../submodules/litellm/litellm/types/router.py) | Router 相关类型定义，后续用于梳理 model group、deployment、routing strategy 等配置语义。 |
| Routing strategy 基类 | [base_routing_strategy.py](../../../submodules/litellm/litellm/router_strategy/base_routing_strategy.py) | 路由策略抽象入口，用于比较 lowest cost、lowest latency、least busy、budget limiter 等策略。 |
| Simple shuffle strategy | [simple_shuffle.py](../../../submodules/litellm/litellm/router_strategy/simple_shuffle.py) | 默认随机 / 加权随机路由策略入口。 |
| Least busy strategy | [least_busy.py](../../../submodules/litellm/litellm/router_strategy/least_busy.py) | 当前 in-flight 请求数最少优先的并发均衡策略入口。 |
| Lowest latency strategy | [lowest_latency.py](../../../submodules/litellm/litellm/router_strategy/lowest_latency.py) | 基于近期 latency / time-to-first-token 样本选择 deployment 的策略入口。 |
| Usage-based strategy v2 | [lowest_tpm_rpm_v2.py](../../../submodules/litellm/litellm/router_strategy/lowest_tpm_rpm_v2.py) | 按当前分钟 TPM / RPM 使用量和限额选择 deployment 的策略入口。 |
| Lowest cost strategy | [lowest_cost.py](../../../submodules/litellm/litellm/router_strategy/lowest_cost.py) | 成本优先路由策略入口，适合接入 Model Routing / Cost 专题。 |
| Budget limiter strategy | [budget_limiter.py](../../../submodules/litellm/litellm/router_strategy/budget_limiter.py) | 预算限制型路由策略入口，后续核验请求级 / 模型级预算防线。 |
| Tag-based routing | [tag_based_routing.py](../../../submodules/litellm/litellm/router_strategy/tag_based_routing.py) | 按 request metadata tags / header regex 过滤候选 deployment 的分流入口。 |
| Cooldown handlers | [cooldown_handlers.py](../../../submodules/litellm/litellm/router_utils/cooldown_handlers.py) | provider / deployment 近期失败后的 cooldown 判断和候选过滤辅助逻辑。 |
| Health state cache | [health_state_cache.py](../../../submodules/litellm/litellm/router_utils/health_state_cache.py) | background health check 写入的 deployment health state 缓存与 staleness 处理。 |
| Adaptive router README | [README.md](../../../submodules/litellm/litellm/router_strategy/adaptive_router/README.md) | request type + model bandit 反馈的学习型路由说明。 |
| Complexity router README | [README.md](../../../submodules/litellm/litellm/router_strategy/complexity_router/README.md) | 本地规则型复杂度分层路由说明。 |
| LAR-1 routing | [lar1_routing.py](../../../submodules/litellm/litellm/router_strategy/lar1_routing.py) | 基于 Agent confidence / evidence / time metadata 选择模型档位的路由入口。 |
| Proxy server | [proxy_server.py](../../../submodules/litellm/litellm/proxy/proxy_server.py) | LiteLLM Proxy Server 主入口之一，承载 OpenAI-compatible HTTP API、管理端点和请求生命周期。 |
| Proxy CLI | [proxy_cli.py](../../../submodules/litellm/litellm/proxy/proxy_cli.py) | `litellm` proxy 启动入口，后续用于理解 config 加载、server 启动和本地运行方式。 |
| Proxy auth | [user_api_key_auth.py](../../../submodules/litellm/litellm/proxy/auth/user_api_key_auth.py) | API key / user auth 入口，后续研究 virtual key、team / user / org 维度预算与权限边界。 |
| Key management endpoints | [key_management_endpoints.py](../../../submodules/litellm/litellm/proxy/management_endpoints/key_management_endpoints.py) | key 创建 / 管理相关 API，后续关联预算、限额、归因和管理面。 |
| Budget manager | [budget_manager.py](../../../submodules/litellm/litellm/budget_manager.py) | Budget 管理入口，后续重点看 spend 更新、预算检查和重置逻辑。 |
| Budget models | [budget.py](../../../submodules/litellm/litellm/models/budget.py) | Budget 数据模型，后续用于梳理预算边界和状态结构。 |
| Cost calculator | [cost_calculator.py](../../../submodules/litellm/litellm/cost_calculator.py) | 模型调用成本计算入口，连接 token usage、model price map 和 spend tracking。 |
| Model price map | [model_prices_and_context_window.json](../../../submodules/litellm/model_prices_and_context_window.json) | 模型价格、上下文窗口和能力元数据表，是 model routing / cost / token budget 研究的关键资料。 |
| Guardrail hook types | [base.py](../../../submodules/litellm/litellm/types/proxy/guardrails/guardrail_hooks/base.py) | Guardrail hook 类型入口，后续用于研究模型网关层的输入 / 输出安全治理。 |

## 与现有横向专题的关系

- [Model Routing / Cost / Token Budget 横向总结](../../comparison/model-routing-cost-token-budget.md)：LiteLLM 可以作为模型网关专题的重点样本，用来补充“Agent Harness 内部成本控制”之外的“外部 LLM Gateway 成本治理”，并作为 DeerFlow 模型出口改造的候选基础设施。
- [Tool System 横向总结](../../comparison/tool-system.md)：LiteLLM 不是传统工具系统，但它在上层 Harness 看来可以成为统一模型调用工具 / provider adapter 层。
- [Permission / Security 横向笔记](../../comparison/permission-security.md)：LiteLLM 的 virtual key、budget、guardrails 和 auth 可以补充模型访问控制面的安全治理视角。

## QA / 讨论记录

### Q: 为什么把 LiteLLM 放进 Harness Study？它不是 Agent Harness 吧？

> **状态**: draft
> **来源**: discussion / source-code

A: 是的，LiteLLM 不是和 DeerFlow、Claw-Code、OpenClaw、Hermes Agent、OpenHands 同一层的 Agent Harness。它更像这些 Harness 下方或旁边的 LLM Gateway / Model Access Control Plane。把它接入本仓库，是为了补齐 Model Routing / Cost / Token Budget 这一层的专门样本：Agent Harness 负责“怎么思考和行动”，LiteLLM 负责“模型请求如何统一接入、路由、限额、计费、fallback 和观测”。

### Q: LiteLLM 的 latency / health routing 算长期记忆吗？

> **状态**: draft
> **来源**: discussion / source-code

A: 常规 latency / health routing 不算传统长期记忆。它记录的是短窗口运行指标，例如 latency 样本、time-to-first-token、当前分钟 TPM/RPM、in-flight 请求数、失败次数、cooldown 状态和 health check 结果。这些状态服务于 deployment 调度，不服务于用户偏好或任务历史。只有 adaptive router 这类学习型路由，才部分接近“长期学习”，因为它会维护 request type / model 的质量反馈和 bandit 状态。详见 [model-routing-cost-budget.md](model-routing-cost-budget.md#一延迟--健康状态不是传统长期记忆)。

### Q: provider 故障自动切换是否意味着用户把所有切换权都交给网关？

> **状态**: draft
> **来源**: discussion / source-code

A: 不是。LiteLLM 的自动切换发生在预授权边界内。管理员先配置 provider credentials、model_list、deployment 和 fallback；virtual key 再限制调用方可访问的 models、routes、budget、TPM/RPM、guardrails、policies、access groups 等；team / org / project 还会继续收窄边界。尤其是 fallback 目标也要经过 key 的模型访问检查，不能通过 fallback 偷偷调用 key 不允许访问的模型。详见 [model-routing-cost-budget.md](model-routing-cost-budget.md#二自动-fallback--provider-切换不是无限授权)。

### Q: LiteLLM Router 的核心策略如何理解？

> **状态**: draft
> **来源**: discussion / source-code

A: LiteLLM Router 的核心不是某个单点算法，而是“候选池过滤 + 策略选择 + 失败恢复 + 指标回写”的调度流水线。先确认调用方有资格访问哪些 model group / deployment；再排除 blocked、health check unhealthy、cooldown、tag 不匹配、budget 超限、TPM/RPM 超限的候选；然后按 simple-shuffle、least-busy、usage-based、latency-based、cost-based、complexity、adaptive、LAR-1 等策略选 deployment；失败后通过 retry / fallback / cooldown 恢复；最后把 latency、usage、spend、failure 写回网关状态。详见 [model-routing-cost-budget.md](model-routing-cost-budget.md#四核心路由策略文字整理)。

### Q: 如果 DeerFlow 想接入 LiteLLM，应该让 LiteLLM 替代 DeerFlow Gateway 吗？

> **状态**: draft
> **来源**: discussion / source-code

A: 不应该。DeerFlow Gateway 管的是 Agent run 生命周期，包括 run / thread / runtime context、lead agent、subagent、tools、sandbox 和 middleware；LiteLLM Gateway 管的是模型调用出口，包括 provider credentials、model group / deployment、routing strategy、virtual key、budget、fallback、cooldown 和 spend tracking。更合理的接入方式是：DeerFlow 继续作为 Agent Harness 和业务入口，模型出口通过 OpenAI-compatible client 指向 LiteLLM Proxy，让 LiteLLM 接管真实 provider 路由与预算治理。详见 [model-routing-cost-token-budget.md](../../comparison/model-routing-cost-token-budget.md#九litellm-与-deerflow模型网关机制边界与接入设想)。
