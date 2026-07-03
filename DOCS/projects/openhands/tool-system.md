# OpenHands Tool System：平台执行面里的 Action / Observation 工具体系

> **日期**: 2026-07-03 | **状态**: draft | **涉及版本**: `openhands` submodule `760d6e9b`；`software-agent-sdk` submodule `f328b7b4`

## 相关文档

- OpenHands 笔记入口：[README.md](README.md)
- OpenHands Agent Loop：[agent-loop.md](agent-loop.md)
- 横向 Tool System 总结：[tool-system.md](../../comparison/tool-system.md)
- 控制面源码：
  - OpenHands App Server：[openhands/openhands/app_server/](../../../openhands/openhands/app_server/)
  - App conversation router：[app_conversation_router.py](../../../openhands/openhands/app_server/app_conversation/app_conversation_router.py)
  - App conversation models：[app_conversation_models.py](../../../openhands/openhands/app_server/app_conversation/app_conversation_models.py)
- 执行面源码：
  - SDK README：[README.md](../../../software-agent-sdk/README.md)
  - Agent Server README：[openhands-agent-server/openhands/agent_server/README.md](../../../software-agent-sdk/openhands-agent-server/openhands/agent_server/README.md)
  - Conversation factory：[conversation.py](../../../software-agent-sdk/openhands-sdk/openhands/sdk/conversation/conversation.py)
  - Local conversation loop：[local_conversation.py](../../../software-agent-sdk/openhands-sdk/openhands/sdk/conversation/impl/local_conversation.py)
  - Agent step / action execution：[agent.py](../../../software-agent-sdk/openhands-sdk/openhands/sdk/agent/agent.py)
  - Response dispatch：[response_dispatch.py](../../../software-agent-sdk/openhands-sdk/openhands/sdk/agent/response_dispatch.py)
  - Tool base class：[tool.py](../../../software-agent-sdk/openhands-sdk/openhands/sdk/tool/tool.py)
  - Default preset：[default.py](../../../software-agent-sdk/openhands-tools/openhands/tools/preset/default.py)

## 1. 核心结论

OpenHands 的 Tool System 不能只在 [openhands/](../../../openhands/) 这个控制面仓库里看。现在更准确的边界是：

```text
openhands/（OpenHands/OpenHands）
  -> 控制面：App Server、Agent Canvas、conversation / event 管理、sandbox 管理、配置与转发

software-agent-sdk/（OpenHands/software-agent-sdk）
  -> 执行面：Agent Server、SDK Conversation / Agent、ToolDefinition、Action / Observation、openhands-tools
```

因此 OpenHands 的工具系统精髓可以概括为：

> **平台控制面决定“在哪个 workspace / sandbox、带哪些配置启动 conversation”；执行面把 LLM tool call 转成 ActionEvent，调用 ToolDefinition 的 executor，再把 Observation 包成 ObservationEvent 回写事件流和模型上下文。**

和 Claw-Code / OpenClaw / Hermes / DeerFlow 对比，它的重点不是“一个本地工具中枢”或“一个厚 tool executor”，而是把工具执行放进平台化 SWE Agent 的远程执行面里。

## 2. 默认工具面：Terminal / FileEditor / TaskTracker / Browser / TaskTool

默认工具入口在 [default.py](../../../software-agent-sdk/openhands-tools/openhands/tools/preset/default.py)。

`register_default_tools(...)` 注册：

```text
TerminalTool
FileEditorTool
TaskTrackerTool
BrowserToolSet（可选）
```

`get_default_tools(...)` 返回给 Agent 的默认工具规格：

```text
Tool(name=TerminalTool.name)
Tool(name=FileEditorTool.name)
Tool(name=TaskTrackerTool.name)
+ BrowserToolSet（enable_browser=True）
+ TaskToolSet（enable_sub_agents=True）
```

这说明 OpenHands 的默认工具面仍然围绕 SWE Agent 最基础的三类能力：

| 工具 | 作用 | 代表源码 |
|---|---|---|
| TerminalTool | 在持久 terminal session 中执行 shell command | [terminal/definition.py](../../../software-agent-sdk/openhands-tools/openhands/tools/terminal/definition.py) |
| FileEditorTool | 查看、创建、替换、插入、撤销文件编辑 | [file_editor/definition.py](../../../software-agent-sdk/openhands-tools/openhands/tools/file_editor/definition.py) |
| TaskTrackerTool | 维护 agent 的任务列表 / plan | [task_tracker/definition.py](../../../software-agent-sdk/openhands-tools/openhands/tools/task_tracker/definition.py) |
| BrowserToolSet | 浏览器相关能力，可按配置启用 | [default.py](../../../software-agent-sdk/openhands-tools/openhands/tools/preset/default.py) |
| TaskToolSet | 子 agent / task delegation，可按配置启用 | [default.py](../../../software-agent-sdk/openhands-tools/openhands/tools/preset/default.py) |

## 3. ToolDefinition：工具不是裸函数，而是 Action / Observation 类型化对象

执行面基础抽象在 [tool.py](../../../software-agent-sdk/openhands-sdk/openhands/sdk/tool/tool.py)。`ToolDefinition` 负责：

```text
工具名 / description
Action schema
Observation schema
executor
schema conversion（OpenAI / Responses / MCP）
input validation
output coercion
resource declaration
```

关键点：

- `ToolDefinition.create(...)` 由具体工具实现，用 conversation state 初始化 executor；
- `action_from_arguments(...)` 把模型参数校验成 `Action`；
- `__call__(action, conversation)` 调用 executor，并确保输出是 `Observation`；
- `declared_resources(...)` 给并发工具执行提供资源锁信息；
- `to_openai_tool(...)` / `to_responses_tool(...)` / `to_mcp_tool(...)` 把内部工具定义转成 provider 或 MCP schema。

这和“模型直接调用 Python 函数”不同。OpenHands 的工具调用承载物更像：

```text
LLM tool_call
  -> Action（类型化参数）
     -> ToolDefinition / executor
        -> Observation（类型化结果）
           -> ObservationEvent
```

## 4. Agent.step：tool_call 如何变成 ActionEvent / ObservationEvent

[Agent.step(...)](../../../software-agent-sdk/openhands-sdk/openhands/sdk/agent/agent.py) 的主线是：

```text
prepare_llm_messages
  -> make_llm_completion(..., tools=list(self.tools_map.values()))
  -> classify_response
     -> TOOL_CALLS: _handle_tool_calls
     -> CONTENT: _handle_content_response
     -> REASONING_ONLY / EMPTY: corrective nudge
```

[response_dispatch.py](../../../software-agent-sdk/openhands-sdk/openhands/sdk/agent/response_dispatch.py) 中 `_handle_tool_calls(...)` 会把每个 `MessageToolCall` 转成 `ActionEvent`，必要时进入 user confirmation，然后执行 action。

更底层的 `_execute_action_event(...)` 在 [agent.py](../../../software-agent-sdk/openhands-sdk/openhands/sdk/agent/agent.py) 中完成：

```text
ActionEvent
  -> self.tools_map[action_event.tool_name]
  -> tool(action_event.action, conversation)
  -> Observation
  -> ObservationEvent(action_id, tool_name, tool_call_id)
```

这正是 OpenHands 和普通 tool calling 的对应关系：

| 普通 tool calling | OpenHands 执行面 |
|---|---|
| `tool_use` | `MessageToolCall` / `ActionEvent` |
| 工具参数 | `Action` |
| 工具函数 / handler | `ToolDefinition.executor` |
| `tool_result` | `Observation` / `ObservationEvent` |
| 下一轮模型上下文 | conversation state / event view |

## 5. 并发执行：ParallelToolExecutor + declared_resources

OpenHands SDK 不是简单串行执行所有工具。[parallel_executor.py](../../../software-agent-sdk/openhands-sdk/openhands/sdk/agent/parallel_executor.py) 提供 `ParallelToolExecutor`：

```text
一批 ActionEvent
  -> ThreadPoolExecutor / asyncio gather
  -> ResourceLockManager
  -> 每个 tool_runner 产出 Event list
```

它的设计重点是：

- 每个 Agent 有自己的 thread pool 和 resource lock manager；
- `tool_concurrency_limit` 控制并发度；
- `ToolDefinition.declared_resources(...)` 声明资源锁；
- 操作同一文件 / terminal session / browser 等共享资源时需要串行，操作不同资源时可以并行；
- async path 会把阻塞工具调用放进 executor，避免卡住 event loop。

例如 [FileEditorTool](../../../software-agent-sdk/openhands-tools/openhands/tools/file_editor/definition.py) 会把目标文件路径声明成 `file:<absolute-path>` 资源，避免并发写同一文件造成部分读取或冲突。

这让 OpenHands 的工具系统相比最朴素的 CLI loop 更接近平台执行器：它不只关心“能不能调用工具”，还关心并发、资源锁、取消和中断。

## 6. Conversation.run：工具循环由执行面持有

[Conversation](../../../software-agent-sdk/openhands-sdk/openhands/sdk/conversation/conversation.py) 是工厂类：

- local workspace -> `LocalConversation`
- remote workspace -> `RemoteConversation`

本地实际 loop 在 [local_conversation.py](../../../software-agent-sdk/openhands-sdk/openhands/sdk/conversation/impl/local_conversation.py) 的 `run()` / `arun()`：

```text
Conversation.run
  -> _ensure_agent_ready
  -> execution_status = RUNNING
  -> while True:
       stuck detection / stop hook / confirmation / budget / max iteration
       agent.step(...)
```

这说明工具执行不是 App Server 控制面直接做，而是 SDK conversation loop 在执行面里做。App Server 可以准备配置、sandbox、secrets、plugins、skills、hooks、workspace 等，但工具真正执行发生在 Agent Server / SDK / tools runtime。

## 7. 控制面负责配置和转发，执行面负责动作和观察

结合 [agent-loop.md](agent-loop.md)，OpenHands 的控制面 / 执行面分工可以简化为：

| 层 | 负责什么 | 不负责什么 |
|---|---|---|
| 控制面 `openhands/` | UI / App Server、conversation metadata、event 查询、sandbox lifecycle、secrets / skills / plugins / setup scripts 配置、向 Agent Server 转发请求 | 不直接跑 `Agent.step()`，不直接执行 Terminal / FileEditor 等工具 |
| 执行面 `software-agent-sdk/` | Agent Server API、SDK `Conversation.run()`、`Agent.step()`、ToolDefinition / executor、ActionEvent / ObservationEvent、工具并发与资源锁 | 不负责完整产品 UI 和平台级 conversation 展示 |

可以记成：

```text
控制面：把任务、配置、workspace 和 sandbox 准备好。
执行面：让模型决策，执行工具动作，产生 observation，再进入下一轮。
```

## 8. 和其他项目的工具调用承载物对比

延续前面几篇工具系统笔记里的“调用承载物”比较：

```text
Claw-Code：ToolUse -> ToolExecutor
OpenClaw：toolCall -> AgentTool
Hermes：tool_call -> function_name + args -> tool_executor
DeerFlow：ToolCallRequest -> BaseTool -> ToolMessage / Command
OpenHands：MessageToolCall -> ActionEvent -> ToolDefinition / executor -> ObservationEvent
```

OpenHands 的特色是：

- carrier 从模型协议层的 `MessageToolCall` 升级为平台事件层的 `ActionEvent`；
- 工具结果不是只作为 tool result 字符串，而是 `Observation` / `ObservationEvent`；
- Action / Observation 事件既服务模型上下文，也服务 UI 展示、事件存储、审计和远程运行；
- ToolDefinition / executor 在 SDK 执行面内，默认工具包独立放在 `openhands-tools`。

## 9. 阶段性判断

OpenHands Tool System 的第一轮结论：

> **OpenHands 把工具系统平台化了：工具定义和执行在 software-agent-sdk / openhands-tools 中，工具调用以 ActionEvent / ObservationEvent 的事件形式穿过 Agent Server / SDK loop；OpenHands/OpenHands 控制面负责把 conversation、sandbox、workspace、secrets、skills、plugins、hooks 和 UI 串起来。**

如果用比喻：

```text
Claw-Code 像本地万能工具箱；
OpenClaw 像实时聊天工单系统；
Hermes 像长期私人助理的工具工作台；
DeerFlow 像 LangGraph 标准化生产线；
OpenHands 像远程开发平台里的工具执行车间。
```

## QA / 讨论记录

### Q: 为什么说 OpenHands 的工具系统要看 software-agent-sdk，而不是只看 OpenHands/OpenHands？

> **状态**: verified
> **来源**: source-code / official-docs / discussion

A: 因为 `OpenHands/OpenHands` 当前主要是 App Server / Agent Canvas 控制面；OpenHands Agent、Agent Server、SDK `Conversation` / `Agent` 和 `openhands-tools` 在 `OpenHands/software-agent-sdk`。本仓库已将后者作为 [software-agent-sdk/](../../../software-agent-sdk/) submodule 接入，因此后续涉及 `Conversation.run()`、`Agent.step()`、`ToolDefinition`、Terminal / FileEditor / TaskTracker 等工具执行细节，应引用该 submodule 下的源码。

### Q: OpenHands 的 ActionEvent / ObservationEvent 和 tool_use / tool_result 是什么关系？

> **状态**: verified
> **来源**: source-code / discussion

A: 底层模式对应，但抽象层级不同。`tool_use / tool_result` 是模型协议层概念；OpenHands 的 `ActionEvent / ObservationEvent` 是平台事件层概念。模型输出 `MessageToolCall` 后，SDK 把它转成 `ActionEvent`，调用 `ToolDefinition.executor` 得到 `Observation`，再包成 `ObservationEvent`。这样同一条工具轨迹既能回写给模型，也能被 UI、event store、审计、远程 Agent Server 消费。
