# DeerFlow Tool System：LangGraph 标准生产线与 middleware 化工具治理

> **日期**: 2026-07-03 | **状态**: draft | **涉及版本**: `4e6248f013aaed84ad5250fe4969de44beebeb7e`

## 相关文档

- 项目入口：[README.md](README.md)
- Agent Loop：[agent-loop.md](agent-loop.md)
- 横向对比：[Tool System 横向总结](../../comparison/tool-system.md)
- 生产部署取舍：[production-deployment-tradeoffs.md](../../comparison/production-deployment-tradeoffs.md)
- 横向 QA：[qa.md](../../comparison/qa.md#tool-system--工具体系)

## 源码入口

| 模块 | 源码 | 作用 |
|---|---|---|
| lead agent 装配 | [agent.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/agent.py) | `_make_lead_agent(...)` 解析 runtime config、装配 model / tools / middleware / state schema，并调用 `create_agent(...)`。 |
| middleware 组装 | [agent.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/agent.py#L260-L393) | 组装 lead agent 的 DynamicContext / SkillActivation / Summarization / DeferredToolFilter / LoopDetection / Clarification 等中间件。 |
| 工具集合装配 | [tools.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/tools/tools.py) | `get_available_tools(...)` 汇总 config tools、builtins、MCP、ACP、subagent、vision 等 `BaseTool`。 |
| 工具 runtime 类型 | [types.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/tools/types.py) | 定义 `Runtime = ToolRuntime[dict[str, Any], ThreadState]`，让工具拿到 context / state。 |
| sandbox 工具 | [sandbox/tools.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/sandbox/tools.py) | `bash` / `ls` / `glob` / `grep` / `read_file` / `write_file` / `str_replace` 等 LangChain `@tool`。 |
| 共享 runtime middleware | [tool_error_handling_middleware.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/tool_error_handling_middleware.py) | `ToolErrorHandlingMiddleware` 以及共享 runtime middleware builder。 |
| deferred MCP Tool Search | [tools/builtins/tool_search.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/tools/builtins/tool_search.py) | MCP deferred tools 的 catalog、`tool_search` schema promotion、fail-closed 装配。 |
| deferred tool 过滤 | [deferred_tool_filter_middleware.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/deferred_tool_filter_middleware.py) | 模型绑定前隐藏未 promoted 的 deferred tool schema，并阻断直接调用。 |
| clarification 控制流 | [clarification_middleware.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/clarification_middleware.py) | 拦截 `ask_clarification`，返回 `Command(goto=END)` 把控制权交回用户。 |
| loop detection | [loop_detection_middleware.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/loop_detection_middleware.py) | 检测重复工具调用集合和高频同类工具调用，必要时 warning / hard stop。 |

## 一句话总结

DeerFlow 的 Tool System 可以概括为：

> **以 LangChain `BaseTool` / `@tool` 作为标准工具接口，以 LangGraph agent runtime / ToolNode 执行模型工具循环，再用 DeerFlow 自己的 middleware、ThreadState、Sandbox 和 Gateway run lifecycle 做生产线式治理。**

如果用比喻理解：

```text
Claw-Code：本地老师傅亲自从工具箱拿工具。
OpenClaw：多端工作室把工具调用做成事件化工单。
Hermes：长期私人助理把 function_name + args 放进厚执行器。
DeerFlow：工作流工厂把工具放进 LangGraph 标准生产线，再在生产线上挂一圈中间件卡口。
```

因此 DeerFlow 最重要的感觉不是“一个厚工具执行器”，而是：

> **标准生产线 + middleware 卡口群。**

## 为什么 DeerFlow 显得特别标准化？

本轮讨论形成的关键判断是：DeerFlow 之所以显得非常流水线化、标准化、原子化，首要原因是它直接使用 LangGraph / LangChain 作为 agent runtime 与工具执行底座。

但这不是唯一原因。更准确地说有两层：

```text
框架标准化：
  LangGraph / LangChain 提供 BaseTool、ToolMessage、Command、AgentMiddleware、state schema、checkpoint、graph execution 等标准件。

产品架构标准化：
  DeerFlow 自己把 Gateway run lifecycle、ThreadState、SandboxMiddleware、ToolErrorHandling、Clarification、TokenBudget、LoopDetection 等能力拆成 run 生命周期组件和 middleware 卡口。
```

所以 DeerFlow 不是“用了 LangGraph 就自然完成全部标准化”，而是：

```text
LangGraph 提供标准生产线；
DeerFlow 沿着这个方向继续把生产环境需要的治理能力拆成中间件和 run lifecycle。
```

## 总体流程

DeerFlow 工具调用主链路可以压缩成：

```text
config.yaml / builtin / sandbox / MCP / ACP / subagent / vision tools
  -> get_available_tools(...) 汇总为 list[BaseTool]
    -> skill allowed-tools 过滤
      -> assemble_deferred_tools(...) 处理 MCP deferred tool_search
        -> create_agent(
             model=...,
             tools=final_tools,
             middleware=build_middlewares(...),
             system_prompt=...,
             state_schema=ThreadState,
           )
          -> LangGraph / LangChain agent runtime 执行 model -> tool -> ToolMessage 循环
            -> middleware wrap_model_call / wrap_tool_call / after_model 等切入治理
              -> Gateway worker 通过 agent.astream(...) 把 values / messages / custom 事件写入 StreamBridge
```

这条链路说明 DeerFlow 的工具系统不以某个 DeerFlow 自研大 executor 为中心，而是把工具执行交给 LangGraph runtime；DeerFlow 自己负责工具面装配、运行上下文、sandbox、middleware 和 Gateway run 生命周期。

## 工具定义：BaseTool / @tool / Runtime

DeerFlow 的工具定义本体是 LangChain 生态里的 `BaseTool` / `@tool`。

`get_available_tools(...)` 在 [tools.py:44](../../../submodules/deer-flow/backend/packages/harness/deerflow/tools/tools.py#L44) 返回 `list[BaseTool]`。这意味着 DeerFlow 最终交给 agent runtime 的不是自定义 `AgentTool`，而是一组 LangChain 标准工具。

sandbox 工具在 [sandbox/tools.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/sandbox/tools.py) 中用 `@tool` 定义，例如：

```text
@tool("bash")
@tool("ls")
@tool("glob")
@tool("grep")
@tool("read_file")
@tool("write_file")
@tool("str_replace")
```

工具 runtime 类型在 [types.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/tools/types.py) 中定义：

```text
Runtime = ToolRuntime[dict[str, Any], ThreadState]
```

这点很关键：DeerFlow 的工具不是孤立函数。它们可以通过 runtime 拿到：

```text
runtime.context
runtime.state / ThreadState
thread_id / run_id / sandbox / user data 等运行上下文
```

因此工具接口是标准化的，但执行时仍能连接 DeerFlow 自己的 thread state、sandbox 和 Gateway run 上下文。

## 工具来源：配置、内置、MCP、ACP、subagent、vision

工具总装配入口是 [get_available_tools(...)](../../../submodules/deer-flow/backend/packages/harness/deerflow/tools/tools.py#L44-L176)。它汇总多类工具：

| 来源 | 源码位置 | 说明 |
|---|---|---|
| config tools | [tools.py:66-88](../../../submodules/deer-flow/backend/packages/harness/deerflow/tools/tools.py#L66-L88) | 从 `config.tools` 里取 `use` 路径，通过 `resolve_variable(cfg.use, BaseTool)` 加载。 |
| builtin tools | [tools.py:15-18](../../../submodules/deer-flow/backend/packages/harness/deerflow/tools/tools.py#L15-L18) | 默认包括 `present_files`、`ask_clarification`。 |
| skill evolution | [tools.py:90-97](../../../submodules/deer-flow/backend/packages/harness/deerflow/tools/tools.py#L90-L97) | 配置启用时加入 `skill_manage_tool`。 |
| subagent tool | [tools.py:98-101](../../../submodules/deer-flow/backend/packages/harness/deerflow/tools/tools.py#L98-L101) | runtime `subagent_enabled` 时加入 `task`。 |
| vision tool | [tools.py:103-111](../../../submodules/deer-flow/backend/packages/harness/deerflow/tools/tools.py#L103-L111) | 只有当前模型 `supports_vision` 时加入 `view_image`。 |
| MCP tools | [tools.py:113-140](../../../submodules/deer-flow/backend/packages/harness/deerflow/tools/tools.py#L113-L140) | 从 extensions config 读取 enabled MCP servers，再取 cached MCP tools，并打 `deerflow_mcp` metadata tag。 |
| ACP agent tool | [tools.py:142-157](../../../submodules/deer-flow/backend/packages/harness/deerflow/tools/tools.py#L142-L157) | 配置了 ACP agents 时构造 `invoke_acp_agent`。 |
| 去重 | [tools.py:161-176](../../../submodules/deer-flow/backend/packages/harness/deerflow/tools/tools.py#L161-L176) | 按工具名去重；config-loaded tools 优先，其后 builtins、MCP、ACP。 |

一句话：

> **DeerFlow 的工具面是“配置工具 + 内置工具 + sandbox 工具 + MCP + ACP + subagent + vision”的 `BaseTool` 列表。**

## agent factory：工具交给 LangGraph runtime

lead agent 的装配在 [agent.py:425-556](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/agent.py#L425-L556)。默认路径的核心是 [agent.py:533-556](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/agent.py#L533-L556)：

```text
raw_tools = get_available_tools(...)
filtered = filter_tools_by_skill_allowed_tools(...)
final_tools, setup = assemble_deferred_tools(...)
return create_agent(
  model=...,
  tools=final_tools,
  middleware=build_middlewares(...),
  system_prompt=...,
  state_schema=ThreadState,
)
```

这个装配点是 DeerFlow Tool System 的核心：工具不是交给 DeerFlow 自己手写的 while-loop executor，而是通过 `create_agent(...)` 交给 LangGraph / LangChain agent runtime。

横向对比：

| 项目 | 工具执行中心 |
|---|---|
| Claw-Code | `ConversationRuntime::run_turn` 提取 `ToolUse`，调用本地 `ToolExecutor`。 |
| OpenClaw | `toolCall` 匹配到 `AgentTool`，进入标准工单生命周期。 |
| Hermes | `function_name + args` 进入 `tool_executor` 厚执行器。 |
| DeerFlow | `BaseTool` 列表交给 LangGraph agent runtime / ToolNode，DeerFlow 用 middleware 包治理。 |

所以 DeerFlow 的主语不是“工具执行器怎么写”，而是：

> **如何把 LangGraph 的工具执行嵌进 run lifecycle、middleware、sandbox 和状态图治理里。**

## 工具调用承载物：ToolCallRequest / BaseTool / ToolMessage / Command

前几篇笔记一直追问“工具调用在 runtime 里由什么承载”。DeerFlow 的答案更框架化：

```text
model tool call
  -> LangGraph / LangChain ToolCallRequest
    -> BaseTool / handler
      -> ToolMessage 或 Command
```

[ToolErrorHandlingMiddleware](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/tool_error_handling_middleware.py#L59-L126) 的接口最能说明这一点：

```text
wrap_tool_call(request: ToolCallRequest, handler: Callable[[ToolCallRequest], ToolMessage | Command])
```

它拿到的是 LangGraph `ToolCallRequest`，调用 `handler(request)` 继续交给下一站；如果工具抛异常，就构造 error `ToolMessage` 回给模型，而不是让整个 run 直接崩溃。

这和 OpenClaw / Hermes 的区别是：

```text
OpenClaw：
  toolCall -> AgentTool -> 工单生命周期

Hermes：
  tool_call -> function_name + args -> 厚执行器流水线

DeerFlow：
  ToolCallRequest -> BaseTool -> ToolMessage / Command，外侧由 middleware 治理
```

## middleware：DeerFlow Tool System 的核心治理面

DeerFlow 的工具治理不集中在一个大 executor，而是拆成很多 middleware。

共享 runtime middleware 由 [tool_error_handling_middleware.py:129-197](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/tool_error_handling_middleware.py#L129-L197) 组装：

```text
InputSanitizationMiddleware
ToolOutputBudgetMiddleware
ThreadDataMiddleware
UploadsMiddleware
SandboxMiddleware
DanglingToolCallMiddleware
LLMErrorHandlingMiddleware
GuardrailMiddleware
SandboxAuditMiddleware
ToolErrorHandlingMiddleware
```

lead-only middleware 由 [agent.py:260-393](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/agent.py#L260-L393) 组装：

```text
DynamicContextMiddleware
SkillActivationMiddleware
DurableContextMiddleware
SummarizationMiddleware
TodoListMiddleware
TokenUsageMiddleware
TitleMiddleware
MemoryMiddleware
ViewImageMiddleware
DeferredToolFilterMiddleware
SystemMessageCoalescingMiddleware
SubagentLimitMiddleware
LoopDetectionMiddleware
TokenBudgetMiddleware
SafetyFinishReasonMiddleware
ClarificationMiddleware
```

这些 middleware 分别承担生产治理能力：

| 机制 | 作用 |
|---|---|
| `ToolErrorHandlingMiddleware` | 工具异常转 error `ToolMessage`，让 run 继续。 |
| `ToolOutputBudgetMiddleware` | 控制工具输出大小，保护上下文。 |
| `SandboxMiddleware` | 在工具执行前准备 / 注入 sandbox 生命周期。 |
| `SandboxAuditMiddleware` | 对 sandbox shell / file 操作做审计。 |
| `DanglingToolCallMiddleware` | 修补缺失 ToolMessage 的历史，避免 provider 协议错位。 |
| `LoopDetectionMiddleware` | 检测重复工具调用集合和高频同类工具调用。 |
| `TokenBudgetMiddleware` | 控制单次 run token 预算。 |
| `DeferredToolFilterMiddleware` | 隐藏未 promoted 的 MCP deferred tool schema，并阻断直接调用。 |
| `ClarificationMiddleware` | 把 `ask_clarification` 变成 `Command(goto=END)`，交回用户。 |
| `SubagentLimitMiddleware` | 限制同一轮过多 `task` subagent 调用。 |

一句话：

> **DeerFlow 的 Tool System 治理不是“一个厚 executor”，而是“LangGraph 工具生产线 + 一圈 middleware 卡口”。**

## sandbox 工具：标准工具接口里的隔离环境

DeerFlow 的 sandbox 工具很能体现“标准接口 + 运行上下文 + sandbox 治理”。

以 [read_file_tool](../../../submodules/deer-flow/backend/packages/harness/deerflow/sandbox/tools.py#L1672-L1743) 为例：

```text
@tool("read_file")
  -> ensure_sandbox_initialized(runtime)
  -> ensure_thread_directories_exist(runtime)
  -> local sandbox 时做 path validation
  -> skills / ACP workspace / user-data virtual path 解析
  -> sandbox.read_file(path)
  -> 按配置截断输出
  -> 捕获 SandboxError / FileNotFoundError / PermissionError / UnicodeDecodeError
```

以 [write_file_tool](../../../submodules/deer-flow/backend/packages/harness/deerflow/sandbox/tools.py#L1763-L1853) 为例：

```text
@tool("write_file")
  -> non-append 单次 80KB payload 上限
  -> ensure_sandbox_initialized(runtime)
  -> ensure_thread_directories_exist(runtime)
  -> local sandbox path validation
  -> get_file_operation_lock(sandbox, path)
  -> sandbox.write_file(path, content, append)
```

这里的生产含义是：

```text
工具本体是 LangChain @tool；
工具通过 Runtime 拿 ThreadState / context；
sandbox 是真实执行环境；
local sandbox 需要虚拟路径映射和路径校验；
write_file 还要做 payload size guard 和同路径 file lock。
```

DeerFlow 因此不是简单“把 read_file 函数暴露给模型”，而是把文件工具接进 thread-scoped user data、sandbox provider、path validation 和 tool output budget 的生产线。

## Tool Search：MCP deferred schema promotion

DeerFlow 也有 Tool Search，但当前读到的主线比 OpenClaw / Hermes 更窄，主要服务 MCP deferred tools。

[tools/builtins/tool_search.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/tools/builtins/tool_search.py#L1-L15) 说明：

```text
Deferred tools appear by name in <available-deferred-tools>
but cannot be called until the model fetches their full schema via tool_search.
```

核心机制：

| 机制 | 源码 | 作用 |
|---|---|---|
| `DeferredToolCatalog` | [tool_search.py:56-72](../../../submodules/deer-flow/backend/packages/harness/deerflow/tools/builtins/tool_search.py#L56-L72) | 保存 deferred MCP tools，支持按名称 / 描述搜索。 |
| `tool_search(...)` | [tool_search.py:130-160](../../../submodules/deer-flow/backend/packages/harness/deerflow/tools/builtins/tool_search.py#L130-L160) | 返回匹配工具的完整 schema，并用 `Command(update=...)` 写入 `promoted` state。 |
| `assemble_deferred_tools(...)` | [tool_search.py:184-201](../../../submodules/deer-flow/backend/packages/harness/deerflow/tools/builtins/tool_search.py#L184-L201) | 在 agent build 后追加 `tool_search`，并确保 fail-closed。 |
| `DeferredToolFilterMiddleware` | [deferred_tool_filter_middleware.py:29-112](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/deferred_tool_filter_middleware.py#L29-L112) | 模型绑定前隐藏未 promoted schema；直接调用未 promoted tool 时返回 error `ToolMessage`。 |

和 Hermes / OpenClaw 对比：

```text
Hermes：
  Tool Search 是个人 Agent 大工具仓库的一部分，MCP / plugin 非核心工具都可能 deferred。

OpenClaw：
  Tool Search 是多来源大 catalog 服务，支持 search / describe / call / code-mode。

DeerFlow：
  当前主线是 MCP deferred schema promotion，重点是把 MCP 工具表压缩进 LangGraph 工具生产线。
```

## clarification：工具调用变成图控制流

DeerFlow 的 `ask_clarification` 很能体现工作流特征。

[ClarificationMiddleware](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/clarification_middleware.py#L25-L36) 拦截 `ask_clarification`。在 [clarification_middleware.py:117-156](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/clarification_middleware.py#L117-L156) 中，它不是让普通工具继续执行，而是：

```text
ToolCallRequest
  -> 提取 question / options
  -> 构造 ToolMessage
  -> return Command(update={"messages": [tool_message]}, goto=END)
```

这说明 DeerFlow 的工具结果不只是字符串，也可以是 LangGraph `Command`：

```text
普通工具：执行外部动作，返回 ToolMessage。
clarification：改变图控制流，停到 END，把问题交给用户。
```

这就是 DeerFlow 作为工作流系统的典型表现：某个工具调用可以从“外部动作”升级成“图调度指令”。

## 生产部署视角：为什么这套设计适合长任务服务

从实际运行 / 生产部署角度看，DeerFlow 的优缺点不是“代码好不好读”，而是：

### 优势

| 生产需求 | DeerFlow 的对应能力 |
|---|---|
| 长任务 run 管理 | Gateway run lifecycle、RunManager、status、cancel / rollback、StreamBridge。 |
| 工具治理可演进 | 横切能力拆成 middleware，新增治理点不必重写大 tool executor。 |
| checkpoint / state | LangGraph state schema / checkpointer 与 `ThreadState` 融合。 |
| 前端进度展示 | `agent.astream(...)` 产出的 values / messages / custom 事件进入 StreamBridge。 |
| sandbox 隔离 | `SandboxMiddleware` + sandbox tools + virtual path / path validation。 |
| HITL / clarification | `ask_clarification` 可通过 `Command(goto=END)` 暂停 run。 |
| 外部工具扩展 | config tools、MCP tools、ACP agent、subagent tool 都能汇总成 `BaseTool`。 |

### 代价

| 生产风险 | 说明 |
|---|---|
| 框架依赖强 | LangGraph / LangChain 的 ToolNode、middleware、state、checkpoint 语义变化会影响运行行为。 |
| 部署比 CLI 重 | Gateway、frontend、nginx、sandbox、checkpoint、stream bridge 等组件都要运维。 |
| middleware 顺序敏感 | InputSanitization、Sandbox、ToolErrorHandling、DeferredToolFilter、Clarification 等顺序有语义。 |
| 调用链路长 | 一个工具调用会穿过 Gateway run、LangGraph runtime、middleware、BaseTool、sandbox、stream bridge。 |
| 故障定位更分散 | 出问题时可能在框架、middleware、tool、sandbox、run manager、stream 层中的任一处。 |

因此 DeerFlow 生产定位更像：

> **长任务 Agent 工作流服务 / Gateway run 平台，而不是极简本地 CLI 或长期私人记忆助理。**

## 横向定位

| 项目 | 工具调用承载物 | 生产定位 |
|---|---|---|
| Claw-Code | `ToolUse -> ToolExecutor` | 本地个人 coding CLI，轻量、直接、基础设施少。 |
| OpenClaw | `toolCall -> AgentTool` | 多端实时 Agent 产品，强调事件、channel、policy、approval、steer / followUp。 |
| Hermes | `function_name + args -> tool_executor` | 长期个人 Agent，强调 memory、skills、session continuity、steer、长期状态。 |
| DeerFlow | `ToolCallRequest -> BaseTool / ToolMessage / Command` | LangGraph 标准生产线，强调 run lifecycle、middleware、sandbox、checkpoint、长任务治理。 |
| OpenHands | `ActionEvent -> ObservationEvent` | 团队级远程 SWE Agent 平台，强调 workspace、sandbox、Agent Server、事件平台和自动化。 |

DeerFlow 的最短记忆版：

> **DeerFlow：标准工具接口 + LangGraph 生产线 + middleware 卡口群。**

## QA / 讨论记录

### Q: DeerFlow 之所以这么标准化，首要原因是不是直接使用了 LangGraph？

> **状态**: draft  
> **来源**: discussion / source-code

A: 是，首要原因是 DeerFlow 把模型-工具循环交给 LangGraph / LangChain agent runtime，因此天然采用 `BaseTool`、`ToolMessage`、`Command`、`AgentMiddleware`、state schema、checkpoint 等标准件。但还需要补一句：DeerFlow 自己也沿着这个框架方向，把 Gateway run lifecycle、ThreadState、SandboxMiddleware、ToolErrorHandling、Clarification、TokenBudget、LoopDetection 等能力拆成中间件和 run 生命周期组件。因此它的标准化来自“框架标准化 + 产品架构标准化”两层。

### Q: 为什么说 DeerFlow 更像标准生产线，而不是老师傅或私人助理？

> **状态**: draft  
> **来源**: discussion / source-code

A: 因为 DeerFlow 没有把工具执行集中写进一个自研大 executor，也不是围绕长期个人记忆工作台组织工具，而是把工具做成标准 `BaseTool`，交给 LangGraph agent runtime 调度，再用大量 middleware 分别处理输入卫生、sandbox、tool error、tool output budget、loop detection、token budget、deferred tool、clarification 等横切能力。可以类比为：`BaseTool` 是标准机器接口，LangGraph runtime 是生产线调度系统，middleware 是质检 / 安全 / 预算 / 暂停 / 审计卡口，ThreadState 是工单状态板，Sandbox 是隔离车间，RunManager / StreamBridge 是外部订单系统和看板。
