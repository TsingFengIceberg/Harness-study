# DeerFlow Agent Loop：Gateway Run + LangGraph Agent

> **日期**: 2026-07-01 | **状态**: draft | **涉及版本**: `e5424cbab9a2a1ec9a09aa9d4c6737aab7ad42c1`
>
> 本文记录 DeerFlow 的 Agent Loop / 控制流主干。不同于 Claw-Code 在一个 Rust `run_turn` 中手写 loop，DeerFlow 把循环交给 LangGraph / LangChain agent runtime：Gateway 负责创建 run、后台 worker 驱动 `agent.astream(...)`，lead agent factory 负责装配 model、tools、middleware、state schema。工具调用、tool message 回写和循环推进主要由 LangGraph agent 执行器完成。

## 相关源码

- LangGraph 配置入口：[langgraph.json](../../../submodules/deer-flow/backend/langgraph.json)
- Gateway run API：[thread_runs.py](../../../submodules/deer-flow/backend/app/gateway/routers/thread_runs.py)
- 创建 run 并启动后台任务：[services.py:356](../../../submodules/deer-flow/backend/app/gateway/services.py#L356)
- 后台 worker 主体：[worker.py:121](../../../submodules/deer-flow/backend/packages/harness/deerflow/runtime/runs/worker.py#L121)
- `agent.astream(...)` 驱动位置：[worker.py:305-334](../../../submodules/deer-flow/backend/packages/harness/deerflow/runtime/runs/worker.py#L305-L334)
- Multi-Agent 笔记：[multi-agent.md](multi-agent.md)
- lead agent factory：[agent.py:424-428](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/agent.py#L424-L428)
- lead agent 装配：[agent.py:431-562](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/agent.py#L431-L562)
- middleware 组装：[agent.py:270-399](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/agent.py#L270-L399)
- Sandbox / Workspace 笔记：[sandbox-workspace.md](sandbox-workspace.md)
- 共享 runtime middleware：[tool_error_handling_middleware.py:128-207](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/tool_error_handling_middleware.py#L128-L207)
- 工具集合装配：[tools.py:44-175](../../../submodules/deer-flow/backend/packages/harness/deerflow/tools/tools.py#L44-L175)
- ThreadState schema：[thread_state.py:149-157](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/thread_state.py#L149-L157)
- 澄清中断 middleware：[clarification_middleware.py:116-155](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/clarification_middleware.py#L116-L155)
- RunManager 并发策略：[manager.py:543-629](../../../submodules/deer-flow/backend/packages/harness/deerflow/runtime/runs/manager.py#L543-L629)

## 和 Claw-Code 的差异

Claw-Code 的主循环更接近手写 runtime：

```text
ConversationRuntime::run_turn
  -> call model
  -> extract tool_use
  -> permission / hook / execute tool
  -> append tool_result
  -> continue until no tool_use or max_iterations
```

DeerFlow 的主循环更像平台化 LangGraph run：

```text
HTTP / embedded client request
  -> create RunRecord
  -> background asyncio task
  -> build LangGraph lead agent
  -> agent.astream(input, config, stream_mode)
  -> LangGraph/LangChain agent runtime repeatedly calls model/tools
  -> stream values/messages/custom events
  -> set run status success / interrupted / error
```

所以 DeerFlow 不是没有 Agent Loop，而是 loop 的中心不在单个 `while tool_use` 函数里，而在 LangGraph agent runtime 中。DeerFlow 自己主要负责：run 生命周期、stream bridge、状态 schema、middleware 链、工具集合、sandbox / memory / subagent / clarification 等横切能力。

> **精髓对照**：Claw-Code 的 `run_turn` 是“对话循环本体”；DeerFlow 的 `run_agent` 是“平台运行驱动器”，内部模型/工具循环委托给 LangGraph agent runtime。前者把 loop 写成一个可直接阅读和调试的函数，后者把 loop 放进 run/thread/checkpoint/stream/middleware 生命周期里。

## 控制流主干

### 入口：LangGraph-compatible run API

Gateway 在 [thread_runs.py](../../../submodules/deer-flow/backend/app/gateway/routers/thread_runs.py) 中实现 LangGraph Platform 风格的 runs API：

- `POST /api/threads/{thread_id}/runs`：创建后台 run，立即返回，见 [thread_runs.py:414-419](../../../submodules/deer-flow/backend/app/gateway/routers/thread_runs.py#L414-L419)
- `POST /api/threads/{thread_id}/runs/stream`：创建 run 并用 SSE 流式返回事件，见 [thread_runs.py:422-447](../../../submodules/deer-flow/backend/app/gateway/routers/thread_runs.py#L422-L447)
- `POST /api/threads/{thread_id}/runs/wait`：创建 run 并阻塞等待最终状态，见 [thread_runs.py:450-474](../../../submodules/deer-flow/backend/app/gateway/routers/thread_runs.py#L450-L474)
- `POST /api/threads/{thread_id}/runs/{run_id}/cancel`：取消运行中的 run，见 [thread_runs.py:499-529](../../../submodules/deer-flow/backend/app/gateway/routers/thread_runs.py#L499-L529)

这些 endpoint 统一调用 [services.py:356](../../../submodules/deer-flow/backend/app/gateway/services.py#L356) 的 `start_run(...)`。

### run 创建：RunManager + background task

`start_run(...)` 的关键步骤是：

1. 调用 `RunManager.create_or_reject(...)` 创建 `RunRecord`，并处理同一 thread 上已有 run 的并发策略，见 [services.py:423-432](../../../submodules/deer-flow/backend/app/gateway/services.py#L423-L432)。
2. 解析 agent factory，默认对应 `lead_agent`，见 [services.py:460](../../../submodules/deer-flow/backend/app/gateway/services.py#L460)。
3. 归一化 graph input、构造 run config、合并 runtime context，见 [services.py:461-476](../../../submodules/deer-flow/backend/app/gateway/services.py#L461-L476)。
4. 用 `asyncio.create_task(...)` 启动后台 `run_agent(...)`，见 [services.py:478-492](../../../submodules/deer-flow/backend/app/gateway/services.py#L478-L492)。

`RunManager.create_or_reject(...)` 在 [manager.py:543-629](../../../submodules/deer-flow/backend/packages/harness/deerflow/runtime/runs/manager.py#L543-L629) 中实现。它支持的并发策略包括：

- `reject`：同一 thread 已有 pending/running run 时拒绝新 run
- `interrupt`：中断已有 run 后创建新 run
- `rollback`：中断已有 run，并让 worker 后续回滚到 pre-run checkpoint

这说明 DeerFlow 的 Agent Loop 从一开始就是“run / thread / checkpoint”语义，而不是简单的单函数同步调用。

### worker：驱动 LangGraph agent streaming

后台 worker 的核心是 [worker.py:121](../../../submodules/deer-flow/backend/packages/harness/deerflow/runtime/runs/worker.py#L121) 的 `run_agent(...)`。

它的主干流程：

```text
1. 设置 run status = running
2. 捕获 pre-run checkpoint，用于 rollback
3. 通过 StreamBridge 发布 metadata
4. 构造 Runtime(context=..., store=...)
5. 调用 agent_factory 创建 LangGraph agent
6. 挂载 checkpointer / store
7. 设置 interrupt_before / interrupt_after
8. 将请求的 stream_mode 映射成 LangGraph stream_mode
9. async for 遍历 agent.astream(...)
10. 将 values / messages / custom 等事件发布到 StreamBridge
11. 根据 abort / provider error / 正常结束设置 run status
12. finally 中 flush journal、同步 title、发布 end、清理 bridge
```

最像“loop”的位置是 [worker.py:305-334](../../../submodules/deer-flow/backend/packages/harness/deerflow/runtime/runs/worker.py#L305-L334)：

```text
async for chunk/item in agent.astream(...):
    if abort_event is set:
        break
    publish serialized chunk to StreamBridge
```

注意：这里的 `async for` 不是直接枚举工具调用；它枚举的是 LangGraph agent runtime 产出的 stream chunk。真正的“模型调用 -> tool calls -> tool messages -> 再调用模型”的循环由 `create_agent(...)` 生成的 LangGraph / LangChain agent 内部执行。

### agent factory：装配 model / tools / middleware / state

DeerFlow 在 [langgraph.json:7-9](../../../submodules/deer-flow/backend/langgraph.json#L7-L9) 注册 graph：

```json
"graphs": {
  "lead_agent": "deerflow.agents:make_lead_agent"
}
```

`make_lead_agent(...)` 位于 [agent.py:424-428](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/agent.py#L424-L428)，内部进入 `_make_lead_agent(...)`。

`_make_lead_agent(...)` 在 [agent.py:431-562](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/agent.py#L431-L562) 中做几件事：

- 从 runtime config 中读取 `thinking_enabled`、`model_name`、`is_plan_mode`、`subagent_enabled`、`agent_name` 等参数
- 解析最终模型配置
- 加载 enabled skills 和 tool policy
- 调用 `get_available_tools(...)` 装配工具集合
- 对 MCP 工具做 deferred tool assembly
- 调用 `create_agent(...)` 生成 LangGraph agent
- 传入 `system_prompt`、`middleware` 和 `ThreadState`

默认 lead agent 的创建位置见 [agent.py:542-562](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/agent.py#L542-L562)。这里是 DeerFlow Agent Loop 的“图装配点”：模型、工具、middleware、state schema 都在这里汇合。

## 工具调用与 tool result 回写在哪里

在 DeerFlow 中，工具调用不由 `run_agent(...)` 手写执行，而由 `create_agent(...)` 生成的 LangGraph / LangChain agent runtime 负责执行。DeerFlow 对工具执行链的控制主要通过两层实现：

1. 工具集合装配：`get_available_tools(...)`，见 [tools.py:44-175](../../../submodules/deer-flow/backend/packages/harness/deerflow/tools/tools.py#L44-L175)
2. tool-call middleware：尤其是 `ToolErrorHandlingMiddleware` 和 `ClarificationMiddleware`

`get_available_tools(...)` 组合的工具来源包括：

- `config.yaml` 中定义的工具
- 内置工具，如 `present_files`、`ask_clarification`
- vision tool，如 `view_image`
- subagent tool，如 `task`
- MCP tools
- ACP agent tool

`ToolErrorHandlingMiddleware` 在 [tool_error_handling_middleware.py:58-125](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/tool_error_handling_middleware.py#L58-L125) 中包装工具调用，把工具异常转换成 `ToolMessage`，让 run 可以继续而不是直接崩溃。

这和 Claw-Code 手写 `ToolExecutor` 的差异是：Claw-Code 在 `run_turn` 中显式处理 tool_use；DeerFlow 把工具执行交给 LangGraph agent runtime，但用 middleware 在工具调用前后插入治理逻辑。

## middleware 链：DeerFlow 的核心扩展点

DeerFlow 的 Agent Loop 不是一个裸循环，而是一条 middleware 管道包裹的 LangGraph agent。

共享 runtime middleware 由 [tool_error_handling_middleware.py:128-207](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/tool_error_handling_middleware.py#L128-L207) 构造，包括：

- input sanitization
- tool output budget
- thread data
- uploads
- sandbox lifecycle
- dangling tool call patch
- LLM error handling
- guardrails
- sandbox audit
- tool error handling

lead-only middleware 由 [agent.py:270-399](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/agent.py#L270-L399) 构造，包括：

- dynamic context
- skill activation
- summarization
- todo / plan mode
- token usage
- title
- memory
- view image
- deferred tool filter
- delegation ledger
- system message coalescing
- subagent limit
- loop detection
- token budget
- safety finish reason
- clarification

其中 [agent.py:372-382](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/agent.py#L372-L382) 体现了 DeerFlow 对“循环失控”和“预算”的控制：`LoopDetectionMiddleware` 用于检测重复 tool-call loop，`TokenBudgetMiddleware` 用于限制单次 run 的 token 消耗。

## 状态与终止条件

### ThreadState

DeerFlow 的状态 schema 是 [ThreadState](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/thread_state.py#L149-L157)，扩展了 LangChain `AgentState`，增加：

- sandbox
- thread_data
- title
- artifacts
- todos
- uploaded_files
- viewed_images
- promoted deferred tools
- delegations

这些 state 会通过 LangGraph checkpoint / stream values 参与 run 的持续状态管理。

### 正常终止

正常情况下，LangGraph agent 内部完成“模型不再请求工具 / 图到达终点”后，`agent.astream(...)` 结束，worker 在 [worker.py:355-362](../../../submodules/deer-flow/backend/packages/harness/deerflow/runtime/runs/worker.py#L355-L362) 将 run 标记为 `success`。

### 用户取消 / interrupt / rollback

用户取消入口在 [thread_runs.py:499-529](../../../submodules/deer-flow/backend/app/gateway/routers/thread_runs.py#L499-L529)。`RunManager.cancel(...)` 会设置 `abort_event` 并 cancel task，见 [manager.py:520-540](../../../submodules/deer-flow/backend/packages/harness/deerflow/runtime/runs/manager.py#L520-L540)。worker 捕获 abort 后会标记 `interrupted` 或执行 rollback，见 [worker.py:336-362](../../../submodules/deer-flow/backend/packages/harness/deerflow/runtime/runs/worker.py#L336-L362)。

### clarification 中断

`ClarificationMiddleware` 会拦截 `ask_clarification` tool call，把它转换成 `ToolMessage`，然后返回 `Command(goto=END)` 结束当前图执行，见 [clarification_middleware.py:116-155](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/clarification_middleware.py#L116-L155)。

这相当于一种 HITL 终止 / 暂停模式：模型没有继续自动跑工具，而是把澄清问题交给用户。

## QA / 讨论记录

### Q: DeerFlow 与 Claw-Code 的 Agent Loop 为什么一个像函数、一个像生命周期 runtime？各自优势是什么？

> **状态**: draft  
> **来源**: source-code / discussion

A: Claw-Code 的 `ConversationRuntime::run_turn` 更像“对话循环本体”：它直接串起模型调用、ToolUse 提取、权限 / hook、工具执行、tool_result 回写和终止条件。优势是主干清楚、局部可调试、适合本地 coding CLI；代价是如果要做 server / run / checkpoint / stream / rollback 等平台能力，需要在外层继续封装。

DeerFlow 的 `run_agent(...)` 更像“平台运行驱动器”：它负责创建和驱动一个 LangGraph run，管理 RunRecord、StreamBridge、checkpoint、status、cancel / rollback；内部模型/工具循环委托给 LangGraph / LangChain agent runtime。优势是天然适合 Web / Gateway / 多入口 / 长任务 / 流式事件 / 可恢复状态；代价是主循环不集中在一个函数里，阅读时需要同时理解 Gateway、worker、agent factory、middleware 和 LangGraph runtime。

可以把这点记成：**Claw-Code 的 `run_turn` 是对话循环本体；DeerFlow 的 `run_agent` 是平台运行驱动器。**

### Q: “横切逻辑”和“内联式”是什么意思？

> **状态**: draft  
> **来源**: discussion

A: Agent Loop 的主流程是“用户输入 -> 模型调用 -> 工具调用 -> 工具结果回写 -> 继续或结束”。但成熟 Harness 还需要权限检查、日志、错误兜底、上下文压缩、token 预算、安全审计、状态持久化、memory 注入等管理动作。这些动作不是主剧情，但会插在主流程的很多位置，所以叫“横切逻辑”。

“内联式”指这些横切逻辑直接写在主流程函数附近。Claw-Code 的 `run_turn` 就更接近这种形态：pre/post hook、permission、tool executor、auto compaction、usage summary 等都在对话循环附近显式串接。

DeerFlow 则是“middleware 管道式”：主循环交给 LangGraph agent runtime，横切逻辑拆成 InputSanitization、ToolOutputBudget、Sandbox、Guardrail、ToolErrorHandling、Summarization、Memory、LoopDetection、TokenBudget、Clarification 等 middleware，挂在 agent runtime 外层。

### Q: `ToolErrorHandlingMiddleware` 是什么兜底？是不是处理所有 tool call 解析错误？

> **状态**: draft  
> **来源**: source-code / discussion

A: 它是工具执行异常兜底，不是所有 tool-call 消息解析错误的总兜底。`ToolErrorHandlingMiddleware` 包住已经被 runtime 识别出来的 `ToolCallRequest`，当具体工具函数执行抛异常时，把异常转换成 `ToolMessage(status="error")`，让模型看到错误并有机会换策略继续，而不是让整个 run 直接崩溃。

模型返回格式不合法、tool_calls 缺 tool result、tool name/schema 不匹配、provider 调用失败、工具输出过大等问题会由不同层处理，例如 LangGraph / provider adapter、`DanglingToolCallMiddleware`、`LLMErrorHandlingMiddleware`、`ToolOutputBudgetMiddleware`、Guardrail / Safety middleware 等。DeerFlow 的特点是把这些兜底拆在多层 middleware / runtime 中，而不是集中写在一个 `run_turn` 函数内。

### Q: Claw-Code 有没有 middleware？

> **状态**: draft  
> **来源**: discussion / source-code

A: 如果严格说 LangChain `AgentMiddleware` 这种统一 middleware chain，Claw-Code 没有。但它有很多 middleware-like 的横切机制：pre/post tool hooks、`PermissionPolicy` / `PermissionPrompter`、`ToolExecutor`、auto compaction、session persistence、usage tracker、sandbox / 安全检查等。

区别在组织方式：Claw-Code 把这些横切逻辑显式串在 `ConversationRuntime::run_turn` 主干附近；DeerFlow 把类似能力拆成 middleware、RunManager、checkpointer、StreamBridge 等多层机制。前者读一个函数更直观，后者扩展成平台 runtime 更自然。

### Q: DeerFlow 防 loop 失控更复杂，主要是产品定位原因吗？

> **状态**: draft  
> **来源**: discussion / source-code

A: 产品定位有影响，但不是主要原因。更主要的是前置架构设计决定了防线分布方式。Claw-Code 的 loop 是显式 `run_turn` 函数，所以最自然的熔断是 `max_iterations`。DeerFlow 的 loop 被拆成 Gateway run lifecycle、LangGraph agent runtime、middleware chain、checkpoint、stream bridge 多层结构，所以防线也分散在多层：RunManager 控制并发和 interrupt / rollback，worker 控制 cancel/status/stream end，middleware 控制 loop detection、token budget、tool error、clarification 等。

因此，不能简单说“DeerFlow 面向普通用户所以防线更多，Claw-Code 面向开发者所以防线少”。更准确的说法是：**多层生命周期式设计带来更多平台能力，也要求每层都有自己的兜底机制；函数式 loop 则更适合用局部、直接的熔断和显式控制流。**

### Q: DeerFlow 的 middleware / permission / compaction / checkpoint 都强属于 Agent Loop 吗？

> **状态**: draft  
> **来源**: discussion

A: 不完全。它们从 Agent Loop 里冒出来，因为 loop 会经过这些机制；但它们不都应该在 Agent Loop 专题里一次讲完。Agent Loop 专题只需要说明这些机制如何影响“模型调用 -> 工具调用 -> 结果回写 -> 继续/结束”的主干。更深入的实现应分流到后续专题：middleware 链进入 `middleware.md`，工具执行进入 `tool-system.md`，权限和 guardrail 进入 `permission-security.md` / `hitl-runtime.md`，summarization / memory 进入 `memory-context.md`，run/thread/checkpoint 进入 `state-checkpoint.md` 或 `session-persistence.md`。

### Q: DeerFlow 的 Agent Loop 在哪里？为什么不像 Claw-Code 那样有一个明显的 `while tool_use`？

> **状态**: draft  
> **来源**: source-code / discussion

A: DeerFlow 的 Agent Loop 不集中在一个手写 `while tool_use` 函数里，而是由 Gateway run lifecycle + LangGraph agent runtime 共同构成。Gateway 的 run API 调用 `start_run(...)`，后台 worker 调用 `agent.astream(...)`，而真正的“模型调用 -> tool calls -> tool messages -> 再调用模型”循环由 `create_agent(...)` 生成的 LangGraph / LangChain agent 执行。DeerFlow 自己的核心增量在 run 管理、checkpoint、stream bridge、middleware、state schema、tools、sandbox 和 HITL。

### Q: DeerFlow 的 `run_agent(...)` 是不是等价于 Claw-Code 的 `run_turn`？

> **状态**: draft  
> **来源**: source-code / discussion

A: 不完全等价。`run_agent(...)` 是 DeerFlow Gateway 的后台 run worker，负责构建 agent、调用 `agent.astream(...)`、转发 stream event、处理 abort / status / journal / checkpoint。它不是逐个解析 tool call 并执行工具的手写 loop。Claw-Code 的 `run_turn` 更像低层对话循环；DeerFlow 的 `run_agent(...)` 更像平台 run driver。

### Q: DeerFlow 如何处理 loop 失控或长时间运行？

> **状态**: draft  
> **来源**: source-code

A: DeerFlow 主要通过多层机制处理：`RunManager` 管理同一 thread 上的并发 run，支持 reject / interrupt / rollback；worker 支持 cancel 和 abort event；middleware 链里有 `LoopDetectionMiddleware` 检测重复工具调用循环，也有 `TokenBudgetMiddleware` 限制 token 预算；clarification 可以用 `Command(goto=END)` 把控制权交回用户。具体默认配置和触发条件后续应在配置专题继续核验。

## 后续分流到其他 DeerFlow 专题的问题

| 问题 | 后续专题 |
|---|---|
| LangGraph checkpoint 如何持久化 ThreadState？ | `state-checkpoint.md` |
| middleware 洋葱模型的执行顺序与失败策略是什么？ | `middleware.md` |
| sandbox lifecycle 如何和 ThreadDataMiddleware / SandboxMiddleware 配合？ | [sandbox-workspace.md](sandbox-workspace.md) |
| subagent `task` tool 如何启动子图 / 子 agent？ | `subagents.md` |
| memory / summarization 如何影响上下文？ | `memory-context.md` |
| clarification / interrupt / rollback 如何形成 HITL？ | `hitl-runtime.md` |
| Gateway SSE stream 和前端 useStream 如何对应？ | `streaming-runtime.md` |

## 相关文档

- 项目入口：[README.md](README.md)
- Claw-Code Agent Loop 对照：[../claw-code/agent-loop.md](../claw-code/agent-loop.md)
- 横向 QA：[../../comparison/qa.md](../../comparison/qa.md)
- 项目定位对比：[../../comparison/project-positioning.md](../../comparison/project-positioning.md)
