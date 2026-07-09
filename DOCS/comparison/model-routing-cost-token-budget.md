# Model Routing / Cost / Token Budget 横向总结：模型调度、成本控制与上下文预算

> **日期**: 2026-07-09 | **状态**: draft | **涉及版本**: DeerFlow `c9fb9768d476e28de0294ac7a23cab9819b93f83` / Claw-Code `4ea31c1bc91c4e9bcbd67d51c550c01e127e6d0d` / OpenClaw `9eeebf7cb13ada247ae94d8e3ab6810dc1b3070a` / Hermes Agent `58e1647b498291bdd28563714513292406d6a876` / OpenHands `2abf0b1303c8d3c8dcd9fb080507395afbaa21d4` + software-agent-sdk `65ee52f817f5b30292abe5f2ac620f84576eb91f`

## 相关项目笔记

| 项目 | 相关笔记 | 本专题相关点 |
|---|---|---|
| DeerFlow | [Agent Loop](../projects/deer-flow/agent-loop.md)、[Context Management](../projects/deer-flow/context-management.md)、[Multi-Agent](../projects/deer-flow/multi-agent.md) | run config / app config 解析模型，`TokenBudgetMiddleware`，SubagentConfig.model / max_turns / timeout，summarization / memory update 关闭 thinking。 |
| Hermes Agent | [Agent Loop](../projects/hermes-agent/agent-loop.md)、[Context Management](../projects/hermes-agent/context-management.md)、[Multi-Agent](../projects/hermes-agent/multi-agent.md) | parent / child AIAgent 模型继承与 delegation override，max_iterations，context compressor，background review / delegation 成本控制。 |
| OpenHands | [Agent Loop](../projects/openhands/agent-loop.md)、[Context Management](../projects/openhands/context-management.md)、[Multi-Agent](../projects/openhands/multi-agent.md) | LLM profiles / agent settings，`AgentDefinition.model`，LLM metrics，context condenser，TaskToolSet 子 agent 成本归因。 |
| OpenClaw | [Agent Loop](../projects/openclaw/agent-loop.md)、[Context Management](../projects/openclaw/context-management.md)、[Multi-Agent](../projects/openclaw/multi-agent.md) | `agents.defaults.subagents.model` / `thinking`，per-call `sessions_spawn.model` / `thinking`，runTimeoutSeconds，resolvedModel / estimated cost / truncation。 |
| Claw-Code | [Agent Loop](../projects/claw-code/agent-loop.md)、[Context Management](../projects/claw-code/context-management.md)、[Multi-Agent](../projects/claw-code/multi-agent.md) | TaskPacket.model / provider，usage / compaction，scope / worktree / permission / acceptance 作为工程成本边界。 |

## 源码入口

| 项目 | 源码 | 作用 |
|---|---|---|
| DeerFlow | [lead_agent/agent.py](../../submodules/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/agent.py) | run 创建时解析 `model_name` / `thinking_enabled` / `reasoning_effort`，检查模型能力并 fallback。 |
| DeerFlow | [token_budget_middleware.py](../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/token_budget_middleware.py) | run 级 token budget warning / stop reason / budget enforcement。 |
| DeerFlow | [subagents/config.py](../../submodules/deer-flow/backend/packages/harness/deerflow/subagents/config.py) | SubagentConfig 中的 model、max_turns、timeout 等子工位预算配置。 |
| Hermes | [agent_init.py](../../submodules/hermes-agent/agent/agent_init.py) | AIAgent 初始化中的 model、max_tokens、max_iterations、iteration budget、usage counters、context window / compression 信息。 |
| Hermes | [delegate_tool.py](../../submodules/hermes-agent/tools/delegate_tool.py) | child AIAgent provider / model override、max_concurrent_children、max_spawn_depth、child timeout、background delegation。 |
| Hermes | [context_compressor.py](../../submodules/hermes-agent/agent/context_compressor.py) | 长期会话上下文压缩、旧工具输出裁剪、头尾保护。 |
| OpenHands | [model.py](../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/settings/model.py) | agent settings / `enable_sub_agents` / `agent_definitions` / 默认工具与模型配置。 |
| OpenHands | [schema.py](../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/subagent/schema.py) | `AgentDefinition` 中的 model、tools、system_prompt、MCP config 等子工种模型配置。 |
| OpenHands | [13_get_llm_metrics.py](../../submodules/software-agent-sdk/examples/01_standalone_sdk/13_get_llm_metrics.py) | SDK LLM metrics 示例，展示 token / usage 观测。 |
| OpenHands | [14_context_condenser.py](../../submodules/software-agent-sdk/examples/01_standalone_sdk/14_context_condenser.py) | context condenser 示例，说明长事件账本如何压缩成模型视图。 |
| OpenClaw | [subagents.md](../../submodules/openclaw/docs/tools/subagents.md) | subagent model / thinking defaults、per-call override、run timeout、resolvedModel、cost / truncation 说明。 |
| OpenClaw | [acp-spawn.ts](../../submodules/openclaw/src/agents/acp-spawn.ts) | ACP subagent spawn 的 model / thinking / runTimeout / depth / active children 约束。 |
| OpenClaw | [sessions.ts](../../submodules/openclaw/packages/gateway-protocol/src/schema/sessions.ts) | session 创建、model、thinking、parent linkage 等 protocol schema。 |
| Claw-Code | [task_packet.rs](../../submodules/claw-code/rust/crates/runtime/src/task_packet.rs) | TaskPacket 中 model / provider / permission / acceptance / recovery 等任务成本边界。 |
| Claw-Code | [task_registry.rs](../../submodules/claw-code/rust/crates/runtime/src/task_registry.rs) | Task status / heartbeat / lane board，为多 worker 成本归因提供任务状态基础。 |

## 核心结论

Model Routing / Cost / Token Budget 不是单纯“选哪个模型更聪明 / 更便宜”，而是在回答一个成熟 Agent Harness 的资源调度问题：

```text
谁适合用强模型？
谁可以用便宜模型？
谁要开 thinking / reasoning？
谁要限制 token？
谁要压缩上下文？
谁跑太久要停？
谁的工具输出太大要截断？
多 agent 并发以后成本如何归因？
```

如果说 Multi-Agent 是“把活派给谁干”，那么 Model Routing / Cost / Token Budget 就是：

> **给每个工位分配合适的脑子、工时、电量和账单归属。**

五个 Harness 的共同方向是：主 Agent 不应该无脑用同一个模型跑所有事情；模型选择、thinking 档位、上下文预算、工具输出预算、子任务并发、超时和压缩策略必须组合起来看。

## 一、这个专题包含三件事

### 1.1 Model Routing：谁用哪个脑子？

Model Routing 回答的是：

```text
主 agent 用什么模型？
子 agent 用什么模型？
总结 / 标题 / memory update 用什么模型？
critic / reviewer / planner 是否用不同模型？
用户能不能 per-task override？
模型不支持 thinking / vision 时怎么 fallback？
```

成熟 Harness 会把模型当成一种可调度资源，而不是全局常量。

### 1.2 Cost Control：怎么别烧太多钱？

Cost Control 回答的是：

```text
能不能让 subagent 用更便宜模型？
能不能限制并发子 agent？
能不能限制 child timeout？
能不能限制 max_turns / max_iterations？
能不能观测 token usage / estimated cost？
能不能让长任务先 yield / 后台跑？
```

成本不只是模型单价，还包括：

```text
模型单价 × 上下文长度 × 循环次数 × 工具输出长度 × 子 agent 数量
```

### 1.3 Token Budget：上下文和循环怎么别爆？

Token Budget 回答的是：

```text
上下文快满了怎么办？
工具输出太长怎么办？
循环太久怎么办？
中间结果要不要压缩？
thinking / reasoning 会不会撑爆预算？
模型 context window 小怎么办？
```

Token budget 不只是省钱。它也影响可靠性：上下文太长会让模型慢、贵、容易出错；工具输出太大则会污染父上下文；子 agent 不设预算，可能跑到 timeout 才停。

## 二、统一抽象：成熟 Harness 都有三层预算

可以把五个项目抽象成这张图：

```text
用户任务
  -> Model Routing：选什么脑子
      主模型 / 子模型 / 工具模型 / 总结模型 / fallback 模型

  -> Runtime Budget：允许跑多远
      max_turns / max_iterations / timeout / concurrency / depth

  -> Context Budget：每轮能看多少
      context window / compression / tool output cap / summary / truncation

  -> Cost Observability：花了多少
      token usage / cache tokens / estimated cost / metrics / run stats
```

**精髓标记：Model Routing 是“用哪个脑子”，Cost Control 是“允许烧多少钱和多久”，Token Budget 是“每次思考能带多少上下文”。三者必须一起设计，不能拆开看。**

## 三、DeerFlow：工作流工厂的能源调度室

DeerFlow 的特点是有非常明显的 Gateway run / middleware / config 结构，所以 Model / Budget 治理比较像“工厂里的能源管理”。

### 3.1 Model Routing：Lead Agent 先解析 runtime model

DeerFlow 的 Lead Agent 创建时会解析：

```text
model_name / model
thinking_enabled
reasoning_effort
agent_config.model
app_config.models
```

它不是写死一个模型，而是：请求指定 model 时，如果配置里存在就使用；如果不存在，就 fallback 到默认模型；如果 `thinking_enabled` 打开但模型不支持 thinking，就关闭 thinking 并记录 warning。

这说明 DeerFlow 把模型能力当成配置对象，而不是字符串常量。它会处理“这个模型能不能 thinking”“这个模型能不能 vision”“这个 agent 是否有指定模型”“runtime config 是否覆盖默认模型”。

### 3.2 Subagent Routing：子 agent 可以有自己的模型、max_turns、timeout

DeerFlow 的 `SubagentConfig` 可以定义：

```text
name / description / system_prompt / tools / model / max_turns / timeout
```

这意味着：Lead Agent 可以用强模型做总控；某些 subagent 可以用专门模型；bash subagent 可以限制 max_turns；general-purpose subagent 可以给更长预算；custom agent 可以自己配置模型和工具。

这就是“工位分级用电”：总工位用强脑，专门工位按任务需要配置脑子和预算。

### 3.3 TokenBudgetMiddleware：真正的 per-run 预算闸门

DeerFlow 最像“预算硬闸门”的是 `TokenBudgetMiddleware`。它的角色不是压缩上下文，而是：统计本 run 的 token 使用、接近预算时给 warning、超过预算时引导结束 / stop，并把 stop reason 暴露给 agent。

可以把它想成工厂电表：

```text
你已经用了 80% 电量：请收尾
你已经接近上限：不要再开新机器
你已经超过预算：停止扩张，交付结果
```

这和单纯 context compression 不一样：compression 是“把东西压小，让模型还能看”，token budget 是“这次 run 总消耗不能无限长”。

**精髓标记：DeerFlow 的 TokenBudgetMiddleware 是 run 级成本刹车，不只是上下文裁剪器。**

### 3.4 DeerFlow 的成本风险：subagent 会放大 token 消耗

DeerFlow 的 multi-agent 让成本结构变成：

```text
Lead Agent 一轮模型调用
  -> 可能发出多个 task tool calls
      -> 每个 subagent 自己跑多轮
          -> 每个 subagent 有自己的 messages / tools / token usage
```

所以它需要多层组合防线：`SubagentLimitMiddleware` 限制一次模型响应中过多 task calls；Subagent `max_turns` 限制子 agent 最大轮数；Subagent `timeout` 限制子 agent 时间；TokenBudgetMiddleware 限制 run token 消耗；Delegation Ledger 提醒 Lead Agent 已经派过哪些任务，避免重复派工。

### 3.5 辅助任务不一定使用主模型和 thinking

DeerFlow 的 summarization、title generation、memory update 等辅助任务通常不需要和 Lead Agent 同等推理配置。源码中能看到一些辅助调用会关闭 thinking。这是一种常见模式：主推理用强模型，维护性任务用非 thinking / 较轻配置。

### 3.6 DeerFlow 小结

```text
模型选择：run config + app_config + agent_config
子模型选择：SubagentConfig.model
预算控制：TokenBudgetMiddleware + max_turns + timeout
成本放大控制：SubagentLimitMiddleware + Delegation Ledger
上下文控制：Summarization / Durable Context / Tool output budget
```

比喻：

> **DeerFlow 像工作流工厂的能源调度室：总控工位、外包工位、辅助工位可以用不同电力档位；TokenBudgetMiddleware 是总电表，subagent max_turns / timeout 是每个工位的小断路器。**

## 四、Hermes Agent：私人助理的用脑预算表

Hermes 是长期个人助理，所以它的预算问题不是单次 workflow，而是长期会话别越来越贵、后台 review 别乱烧、分身 delegation 别爆炸、provider / model credential 别失效、上下文压缩要跟长期记忆配合。

### 4.1 Model Routing：主助理和分身可以走不同 provider / model

Hermes 的 `delegate_task` 中，child AIAgent 默认可以继承父 agent 的 provider / model / API credentials，也支持 delegation config 中的 provider / model override。

也就是说：父助理可以用强模型处理主对话和复杂判断；子助理可以配置成便宜 / 快速模型处理局部调研；后台 review 也可以有自己的辅助模型配置。

这很像私人助理分配工作：主助理本人用最好的判断力跟用户沟通，跑腿分身可以用更便宜、更快的脑子完成局部任务。

### 4.2 成本控制重点：max_iterations 和 child budget

Hermes 里很重要的是 `max_iterations`。长期 agent 如果没有 iteration 限制，很容易进入工具失败、重试、上下文变长、成本变高的循环。

父 AIAgent 有 `max_iterations`，delegation 里的 child AIAgent 也有自己的 max iteration cap。这带来一个产品取舍：子 agent 有自己的预算，可以独立完成任务；但总成本也会超过父 agent 单独运行的预算。

所以 Hermes 还需要 `max_concurrent_children`、`max_spawn_depth`、`child_timeout_seconds`、`spawn_pause`、active registry 和 interrupt。这些不是单纯安全机制，也是成本控制机制。

### 4.3 Token Budget：长期会话必须依赖压缩

Hermes 是长期个人助理，所以 token budget 最大的问题不是一次 run，而是聊久以后历史、工具输出、记忆、skills、todo、session context 都越来越多。

Hermes 的 context compressor 可以理解为：

```text
保留开头关键系统信息
保留最近消息
压缩中间历史
裁剪旧工具输出
保护重要上下文
避免 provider context window 爆掉
```

这和 DeerFlow 的 TokenBudgetMiddleware 不一样。DeerFlow 更像本次 workflow token 预算闸门；Hermes 更像长期私人助理的记忆整理和会话瘦身系统。

### 4.4 输出长度、后台任务和长期成本

Hermes 还会控制模型输出长度、后台 review、background delegation、kanban worker 等长期能力。后台能力让 agent 更像“长期助理”，但也会带来用户不盯着时的成本风险。

所以 Hermes 需要 daemon executor、background queue、child timeout、completion callback、active registry、interrupt / stop、memory / skill write guard 等机制组合治理。

**精髓标记：Hermes 的成本控制不是一次性“token 上限”，而是长期个人助理生命周期里的“别让分身、后台 review、长期上下文共同烧穿预算”。**

### 4.5 Hermes 小结

```text
模型选择：父 agent model / provider + delegation override
子模型选择：child AIAgent 可继承或覆盖 provider/model
预算控制：max_iterations、child max_iterations、timeout
成本放大控制：max_concurrent_children、max_spawn_depth、spawn_pause
上下文控制：context_compressor、tool output 裁剪、session 压缩
长期成本控制：background review / memory sync / skill maintenance 的异步治理
```

比喻：

> **Hermes 像私人助理的用脑预算表：主助理负责高价值判断，分身负责局部任务；但每个分身都要有工时上限、工具边界和回报机制，否则长期助理会在后台悄悄烧钱。**

## 五、OpenHands：远程开发平台的工位计费系统

OpenHands 是平台化 SWE Agent Harness，所以它的 Model Routing / Cost / Token Budget 更像平台能力：用户 profile、LLM profiles、AgentDefinition.model、TaskToolSet、LLM metrics、context condenser、event observability 共同组成成本治理面。

### 5.1 Model Routing：profile / settings / AgentDefinition 共同决定

OpenHands 的模型不是只写在一个 CLI 参数里。它有用户 agent settings、LLM profiles、conversation settings、`AgentDefinition.model` 和 `SwitchLLMTool`。

这意味着：主 conversation 可以有默认 LLM；某个 sub-agent definition 可以指定自己的 model；用户可以在平台设置里切换 profile；某些任务可以通过 LLM routing 使用 secondary model。

**精髓标记：OpenHands 的模型选择不是一次性启动参数，而是用户 profile、agent definition、conversation request 和 runtime tool 共同组成的配置面。**

### 5.2 Subagent 成本逻辑：专业工种可以有自己的模型

OpenHands 的 `AgentDefinition` 可以包含 `model`。这点和 DeerFlow 的 `SubagentConfig.model` 很像，但 OpenHands 更平台化。

```text
grammar-checker 可以用轻模型
browser researcher 可以用强模型
critic agent 可以用不同模型
project-defined maintainer agent 可以指定模型
plugin agent 可以带自己的模型偏好
```

所以 OpenHands 的 model routing 更像“按工种分配模型”，而不是按“主 / 子”简单分配。

### 5.3 Cost Observability：OpenHands 重视 LLM metrics

OpenHands SDK 示例里有 LLM metrics / conversation cost 相关例子。这体现了平台型 Harness 的关注点：用户跑了多少 token，prompt / completion / cache token 怎么统计，conversation 累积成本如何展示，多 agent / 多工具调用下成本如何归因。

OpenHands 作为远程开发平台，不能只做“跑起来”，还要做“可观测、可计费、可解释”。

### 5.4 Token Budget：Context Condenser 是核心机制之一

OpenHands 的执行面是 conversation / event log 模型。长任务会产生大量 ActionEvent、ObservationEvent、terminal output、file diff、browser observation、task tracker update、subagent observation。

如果全部原样投给模型，token 会爆。因此 OpenHands 需要 condenser：

```text
EventLog 是完整账本
View / Condenser 是投给模型的压缩视图
模型不是每轮读取全部历史，而是读取当前可用投影
```

这和 Context Management 专题里的 OpenHands 结论一致：平台完整保存事件账本，但模型每轮只看经过裁剪 / 压缩 / 投影的视图。

### 5.5 OpenHands 小结

```text
模型选择：LLM profiles + agent settings + AgentDefinition.model
子模型选择：registered sub-agent definition 可指定 model
成本观测：LLM metrics / accumulated usage / observability
上下文控制：EventLog + View + Condenser
平台治理：conversation request / Agent Server / UI event stream
```

比喻：

> **OpenHands 像远程开发平台的工位计费系统：不同专业工种可以用不同模型，平台保存完整施工日志，但模型每次只看压缩视图；同时 metrics 告诉你这次远程工位到底花了多少。**

## 六、OpenClaw：多会话控制台的模型档位面板

OpenClaw 的 Model / Cost / Token Budget 和它的 session / subagent / ACP control plane 绑定很深。

### 6.1 Model Routing：主 agent、subagent、ACP session 都可以有模型档位

OpenClaw 的 subagents 文档说明：native sub-agents 默认继承 caller model；可以设置 `agents.defaults.subagents.model`；可以设置 per-agent subagents.model；`sessions_spawn.model` 显式覆盖优先；ACP runtime 也可以接收 model / thinking defaults。

这说明 OpenClaw 的模型路由有优先级：

```text
per-call override
  > per-agent subagent override
  > global subagent default
  > caller inherited model
```

这很像控制台上的模型档位面板：主会话用高级模型，普通 subagent 继承主模型，重型 subagent 显式指定强模型，重复性 subagent 默认用便宜模型，ACP 子会话带自己的模型参数启动。

### 6.2 Thinking Routing：不仅选模型，还选思考档位

OpenClaw 还显式处理 `thinking`。子 agent 可以继承 caller thinking，使用 `agents.defaults.subagents.thinking`，使用 per-agent subagents.thinking，或通过 `sessions_spawn.thinking` 覆盖。

这点很重要。成本不只由模型决定，也由 reasoning / thinking 决定。低 thinking 适合读文件、简单搜索、格式转换；高 thinking 适合架构判断、复杂修复、审计。

### 6.3 Cost Control：subagent 默认模型可以比主模型便宜

OpenClaw 文档直接提醒：heavy / repetitive tasks 可以给 subagents 设置 cheaper model，main agent 保持高质量模型。

这是典型的 multi-agent 成本策略：主 agent 负责综合、判断、对用户表达；子 agent 负责搜索、读取、跑慢工具、整理材料。很多子 agent 不需要顶级模型，只需要完成局部、可验证的任务。

### 6.4 Run Timeout、resolvedModel、estimated cost 与 truncation

OpenClaw 支持 `agents.defaults.subagents.runTimeoutSeconds`。这说明子 run 时间预算更像 operator 策略，而不是让模型随意决定。

OpenClaw 还会在 accepted spawn tool result 中返回 resolvedModel / resolvedProvider；当 pricing 配置存在时可以估算 cost；completion handoff 会截断长文本 block，并丢弃 thinking signatures、reasoning replay payload 和 inline image data。

这些细节说明 OpenClaw 不只是运行 subagent，还关心：child 到底用了哪个模型、成本是否可估算、回传给父 agent 的内容是否过长、哪些高成本 / 高噪声内容不应该进入回流。

**精髓标记：OpenClaw 把子 agent 成本治理放在控制面配置和 session metadata，而不是完全交给模型参数。**

### 6.5 OpenClaw 小结

```text
模型选择：caller inheritance + agents.defaults.subagents.model + per-agent override + sessions_spawn.model
thinking 选择：同样支持 inheritance/default/override
时间预算：subagents.runTimeoutSeconds
成本观测：resolvedModel / resolvedProvider / pricing estimated cost
上下文控制：isolated/fork context、completion handoff truncation、session compaction
平台治理：control plane / protocol schema / model catalog / UI selectors
```

比喻：

> **OpenClaw 像多会话控制台的模型档位面板：每个 session、subagent、ACP runtime 都可以有模型和 thinking 档位；控制面负责默认值、覆盖值、超时和成本可见性。**

## 七、Claw-Code：本地施工队的任务成本单

Claw-Code 比 OpenHands / OpenClaw 更偏本地 CLI，所以它的 Model / Cost / Token Budget 更“工程任务化”。

### 7.1 Model Routing：TaskPacket 可以携带 model / provider

Claw-Code 的 `TaskPacket` 里有 model / provider 相关字段。这说明在 Claw-Code 的多任务模型中，模型选择可以成为任务包的一部分：

```text
这个任务用哪个 provider？
用哪个 model？
权限 profile 是什么？
worktree 怎么开？
验证计划是什么？
```

这和 DeerFlow 的 `SubagentConfig.model` 不一样。DeerFlow 是“agent 类型配置模型”；Claw-Code 更像“每张施工单可以带自己的模型 / provider 要求”。

### 7.2 Cost Control：Claw-Code 更偏“任务验收”和“本地边界”

Claw-Code 的成本控制不一定表现为一个显眼的 TokenBudgetMiddleware。它更偏工程治理：任务范围 scope、worktree 隔离、permission profile、acceptance tests、verification plan、worker lifecycle status。

为什么这些也算 cost control？因为成本不只是 token，还包括误改代码的修复成本、跑错目录的时间成本、重复执行测试的时间成本、权限误放大的安全成本、worker 卡住的人工成本。

Claw-Code 是本地 coding CLI，它最怕的是 agent 在本地工程里乱跑。所以它把预算控制前移到任务定义：先限定做什么，再限定在哪做，再限定能用什么工具，最后限定怎么验收。

### 7.3 Token Budget：本地 CLI 重点在 context management / compaction

Claw-Code 的 token budget 主要和上下文管理相关：SystemPromptBuilder、Session.messages、provider message conversion、usage threshold、auto compaction、context-window retry。

本地 coding agent 的典型问题是：用户和 agent 聊很久、工具输出很多、文件 diff 很大、测试日志很长、上下文窗口逐渐接近上限。所以它需要 usage 统计、auto compaction、context-window retry、tool result 裁剪和 session persistence。

### 7.4 Worker / Team 模式下的成本放大

Claw-Code 一旦进入 TaskPacket / Worker / Team 模式，也会遇到 multi-agent 成本放大：一个 team 多个 task，每个 task 一个 worker，每个 worker 一个独立上下文 / worktree / verification plan。

但 Claw-Code 的优势是每个 task 是标准化对象。一个 worker 超时或失败时，可以追问：任务是不是定义太大、scope 是否太宽、acceptance 是否不清楚、权限是否卡住、测试是否太重。这比“一个大 agent 黑箱烧 token”更容易定位问题。

### 7.5 Claw-Code 小结

```text
模型选择：TaskPacket.model / provider
成本边界：scope、worktree、permission_profile、branch_policy、acceptance
上下文预算：session messages、usage threshold、auto compaction、context-window retry
任务成本观测：TaskRegistry status、worker status、heartbeat、team summary
```

比喻：

> **Claw-Code 像本地施工队的任务成本单：每个任务先写清楚要用什么工位、什么工具、什么模型、怎么验收；预算控制更多体现在施工边界和验收机制，而不是单个 token 电表。**

## 八、五个 Harness 横向对比表

| 维度 | DeerFlow | Hermes Agent | OpenHands | OpenClaw | Claw-Code |
|---|---|---|---|---|---|
| 主模型选择 | run config / app_config / agent_config | AIAgent provider / model | LLM profiles / agent settings | agent config / model catalog | CLI / TaskPacket model |
| 子模型选择 | SubagentConfig.model | delegation provider / model override | AgentDefinition.model | subagents.model / sessions_spawn.model | TaskPacket.model / provider |
| thinking / reasoning | thinking_enabled + supports_thinking fallback | provider/model specific handling | Anthropic thinking / Responses reasoning examples | subagents.thinking / per-call thinking | provider dependent |
| token 硬预算 | TokenBudgetMiddleware | max_iterations / context compressor | condenser / metrics / max_iterations patterns | timeout / truncation / compaction / context mode | usage threshold / auto compaction |
| 成本观测 | token budget warning / tracing | session token counters / background cost risk | LLM metrics / accumulated token usage | resolvedModel / estimated cost when pricing configured | usage / task state / worker status |
| multi-agent 成本风险 | 多 subagent 各自跑多轮 | child AIAgent / background delegation | TaskToolSet + sub-agent event stream | background subagent sessions | Team 多 worker |
| 成本防线 | max_turns、timeout、SubagentLimit | max_children、depth、timeout、spawn_pause | profile、definition、condenser、metrics | default subagent model、runTimeout、truncation | scope、worktree、permission、acceptance |

## 九、抽象出的统一设计原则

> **本节是本专题的重点。后续研究或设计任意 Agent Harness 的模型调度 / 成本控制 / token budget，都可以用下面这些原则做 checklist。**

### 原则 1：主 Agent 和子 Agent 不一定该用同一个模型

成熟 Harness 都在走向：

```text
主 Agent：强模型，负责判断 / 综合 / 对用户表达
子 Agent：按任务选择模型，负责局部执行 / 搜索 / 整理
辅助 Agent：便宜模型或 non-thinking，负责标题 / summary / memory update
```

最典型的证据是：OpenClaw 文档明确建议 heavy / repetitive sub-agent 可用 cheaper model；Hermes delegation 可以给 child 配不同 provider / model；OpenHands `AgentDefinition.model` 让不同工种用不同模型；DeerFlow `SubagentConfig.model` 支持 per-subagent 模型；Claw-Code `TaskPacket.model / provider` 把模型选择放进任务单。

**精髓标记：模型路由的目标不是“永远用最强模型”，而是“把强模型留给高价值判断，把便宜模型用于可验证的局部工作”。**

### 原则 2：thinking / reasoning 也是预算，不只是能力开关

现在很多模型有 thinking / reasoning 档位。它会影响质量、延迟、输出结构、token 消耗和成本。

所以 Harness 不能只路由 model，还要路由 thinking。OpenClaw 对 subagent thinking default / override 很明确；DeerFlow 会检查模型是否支持 thinking；OpenHands 有 Anthropic thinking / Responses reasoning 示例；Hermes / Claw-Code 则更多依赖 provider adapter 和配置。

**设计原则：thinking 应该像 model 一样有默认值、覆盖值和兼容性检查。**

### 原则 3：Token Budget 不是一个单点功能，而是一组刹车

真正的 token budget 通常由多层组成：

```text
context window 检查
tool output cap
summary / compression
max_turns / max_iterations
timeout
concurrency limit
depth limit
final answer warning
usage metrics
```

比如 DeerFlow 有 TokenBudgetMiddleware，但它仍然需要 subagent max_turns / timeout。Hermes 有 context compressor，但仍然需要 max_iterations 和 child timeout。OpenHands 有 condenser，但仍然需要 metrics 和 profile model。OpenClaw 有 timeout / truncation，但仍然需要 model defaults。Claw-Code 有 auto compaction，但仍然需要 task scope 和 worker boundaries。

**精髓标记：Token Budget 不是一个开关，而是一整套“输入、输出、循环、并发、时间、压缩”的组合刹车。**

### 原则 4：成本控制要和 multi-agent 一起设计

一旦支持子 agent，成本结构就从：

```text
1 个 agent × N 轮
```

变成：

```text
1 个 parent agent × N 轮
+ K 个 child agent × 各自 M 轮
+ 每个 child 的工具输出 / 压缩 / 回流
```

这会迅速放大。

所以 multi-agent 必须配套：子 agent 默认便宜模型、max concurrent children、max spawn depth、child timeout、child max_turns、result summary only、ledger / registry 防重复派工。

这也是为什么 DeerFlow、Hermes、OpenClaw、OpenHands 都不会只做“spawn child”，还会做 registry / limit / timeout / summary。

### 原则 5：成本观测必须能归因

只知道“这次花了很多 token”是不够的。成熟系统要回答：

```text
是主 agent 花的？
是 subagent 花的？
是 summary 花的？
是 tool output 太长？
是 context 没压缩？
是模型太贵？
是重复派工？
```

OpenHands 的 LLM metrics、OpenClaw 的 resolvedModel / estimated cost、Hermes 的 session counters、DeerFlow 的 token budget / tracing、Claw-Code 的 task / worker status 都是在往这个方向走。

**设计原则：没有归因的 cost metric，只是账单；有归因的 cost metric，才是调度依据。**

### 原则 6：辅助任务不应默认使用最高档模型

常见辅助任务包括：

```text
生成标题
压缩上下文
更新记忆
整理工具输出
分类风险
生成摘要
```

这些任务通常有两个特点：结果可被主 agent / 用户校验；不需要完整高 reasoning。

所以它们适合低成本模型、非 thinking 模式、较小 max_tokens、批处理 / 异步处理。DeerFlow 的 title / summarization / memory update 已经体现这种倾向；OpenHands condenser / metrics 示例也说明同类思路；Hermes background review 更需要这类策略。

### 原则 7：预算应该由 runtime / operator 控制，不应该完全交给模型

模型可以建议“我需要更多时间”，但不能自己随便决定：

```text
我要开 20 个 subagent
我要跑 3 小时
我要用最贵模型
我要无限 fork context
我要把所有日志塞回父上下文
```

成熟 Harness 会把这些放进 runtime config：max_concurrent_children、max_spawn_depth、runTimeoutSeconds、max_turns、max_iterations、tools policy、context mode、model defaults。

OpenClaw 的 `runTimeoutSeconds` 不让模型 per-call 随意决定，是典型的 operator-control 思路。Hermes 的 delegation config、DeerFlow 的 app config、OpenHands 的 user / profile settings、Claw-Code 的 TaskPacket / permission profile 也是类似思想。

### 原则 8：上下文压缩和成本控制不是一回事，但必须配合

上下文压缩解决的是“模型下一轮能不能看得下”；成本控制解决的是“这次运行总共能不能烧得起、跑得住”。两者相互依赖，但不是同一层。

```text
压缩可以让一次模型调用继续进行，但不能阻止 agent 无限循环。
max_iterations 可以阻止无限循环，但不能保证每轮上下文不爆。
tool output cap 可以保护上下文，但不能决定哪个模型更适合任务。
```

所以成熟 Harness 往往同时有 context compressor、tool output budget、iteration limit、timeout、token usage warning、model routing 和 cost metrics。

**设计原则：压缩是“整理行李”，预算是“限制旅程”，模型路由是“选择交通工具”。三者必须协同。**

### 原则 9：模型选择应服务于任务可验证性，而不只是服务于便宜

便宜模型适合可验证、局部、低风险任务：搜索、列文件、格式整理、候选生成、初步分类、提取摘要。强模型适合不可轻易验证、需要综合判断、高风险决策的任务：架构设计、安全审计、复杂修复、用户最终答复。

因此，模型路由不能简单写成“子 agent 用便宜模型，主 agent 用贵模型”。更准确的规则是：

```text
可验证局部任务 -> 可以用便宜模型
不可验证关键判断 -> 应使用强模型
会影响用户 / 代码 / 安全的最终决策 -> 交回强模型综合
```

**精髓标记：成本优化不是降智，而是把低成本模型放在“可验证、可回滚、可由强模型复核”的位置。**

## 十、课堂版总结

如果只用一句话总结这个专题：

> **Model Routing / Cost / Token Budget 是 Agent Harness 的资源调度系统。它决定谁用什么模型、能跑多久、能看多少上下文、能开多少子任务、结果如何压缩、成本如何归因。**

五个 Harness 的差异是：

```text
DeerFlow：
  工厂式 middleware 和 SubagentConfig，TokenBudgetMiddleware 是明显电表。

Hermes：
  私人助理式长期预算，分身可换模型，靠 iteration / timeout / compression 防烧穿。

OpenHands：
  平台式 profile / AgentDefinition / metrics / condenser，按专业工种和远程事件账本治理成本。

OpenClaw：
  多会话控制台式 model / thinking defaults，subagent session 可继承或覆盖模型，并带 timeout / cost visibility。

Claw-Code：
  本地工程任务式成本控制，TaskPacket 带 model / provider，scope / worktree / permission / acceptance 控制工程成本。
```

最终精髓：

> **不要把模型当成全局常量，要把模型当成可调度资源。**
>
> 主 Agent、子 Agent、后台任务、摘要器、记忆更新器、critic、planner、worker 都可以有不同的模型、thinking 档位、上下文预算和运行上限。成熟 Harness 的成本控制，不是“少用模型”，而是“让每一类工作用合适的模型和合适的预算”。

## QA / 讨论记录

### Q: Model Routing / Cost / Token Budget 是不是只是“省钱”？

> **状态**: draft
> **来源**: discussion / source-code

A: 不是。省钱只是其中一部分。更准确地说，它是 Agent Harness 的资源调度系统：决定不同任务使用什么模型、是否开启 thinking、允许跑多少轮、上下文如何压缩、工具输出如何裁剪、子 agent 并发如何限制、成本如何归因。它同时影响效果、速度、可靠性、安全和可观测性。

### Q: 为什么 multi-agent 之后更需要模型路由和预算治理？

> **状态**: draft
> **来源**: discussion / source-code

A: 因为 multi-agent 会把成本从单个 agent 的线性循环，放大成 parent + 多个 child 的并发消耗。每个 child 都可能有自己的上下文、工具输出、循环次数和模型调用。如果没有子模型默认、max_turns / max_iterations、timeout、concurrency cap、结果压缩和成本归因，multi-agent 很容易从“并行提效”变成“并行烧钱”。

## 相关文档

- [Agent Loop 横向总结](agent-loop.md)
- [Tool System 横向总结](tool-system.md)
- [Context Management 横向总结](context-management.md)
- [Multi-Agent / Subagent 横向总结](multi-agent.md)
- [Permission / Security 横向总结](permission-security.md)
- [Sandbox / Workspace 横向总结](sandbox-systems.md)
- [生产部署取舍](production-deployment-tradeoffs.md)
