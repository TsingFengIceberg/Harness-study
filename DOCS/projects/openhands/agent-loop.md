# OpenHands Agent Loop：控制面 / 执行面分离的 SWE Agent 事件循环

> **日期**: 2026-07-01 | **状态**: draft | **涉及版本**: `openhands` submodule `760d6e9b`；`software-agent-sdk` submodule `f328b7b4`

## 相关文档

- OpenHands 笔记入口：[README.md](README.md)
- OpenHands 当前仓库源码（控制面）：
  - 项目说明：[README.md](../../../openhands/README.md)
  - App conversation service：[live_status_app_conversation_service.py](../../../openhands/openhands/app_server/app_conversation/live_status_app_conversation_service.py)
  - App conversation router：[app_conversation_router.py](../../../openhands/openhands/app_server/app_conversation/app_conversation_router.py)
  - Event service：[event_service_base.py](../../../openhands/openhands/app_server/event/event_service_base.py)
  - Conversation models：[app_conversation_models.py](../../../openhands/openhands/app_server/app_conversation/app_conversation_models.py)
- 执行面源码：[software-agent-sdk/](../../../software-agent-sdk/) 指向 `OpenHands/software-agent-sdk`，其中 [conversation.py](../../../software-agent-sdk/openhands-sdk/openhands/sdk/conversation/conversation.py) 是 Local / Remote Conversation 工厂，[local_conversation.py](../../../software-agent-sdk/openhands-sdk/openhands/sdk/conversation/impl/local_conversation.py) 持有 `Conversation.run()` / `arun()` loop，[agent.py](../../../software-agent-sdk/openhands-sdk/openhands/sdk/agent/agent.py) 持有 `Agent.step()` / tool action execution，[response_dispatch.py](../../../software-agent-sdk/openhands-sdk/openhands/sdk/agent/response_dispatch.py) 负责 response 分类与 tool call dispatch。
- 横向 QA：[Harness Study 横向 QA](../../comparison/qa.md#agent-loop--控制流)

## 1. 核心结论

OpenHands 的 Agent Loop 不能只在当前 `OpenHands/OpenHands` 仓库里找一个类似 `run_turn` 的函数。当前仓库更像 **Agent Canvas / App Server 控制面**，真正的 Agent / Agent Server / SDK loop 在本仓库新接入的 [software-agent-sdk/](../../../software-agent-sdk/) submodule 中。这一点在 OpenHands 当前仓库 [README.md](../../../openhands/README.md#L49-L54) 中也有明确说明。

可以概括为：

> **OpenHands = 平台控制面 + Agent Server 执行面 + action/observation 事件循环。**

它和前面几个 harness 的精髓差异是：

- **Claw-Code**：本地 CLI `run_turn`，更像“一个师傅一轮干到底”。
- **DeerFlow**：Gateway run lifecycle + LangGraph runtime，更像“长任务工作流平台”。
- **Hermes Agent**：`run_conversation` + memory / fallback / steer，更像“长期个人助理大脑”。
- **OpenClaw**：`AgentSession -> Agent -> runLoop`，更像“聊天式 Agent session runtime”。
- **OpenHands**：`App Server -> Sandbox -> Agent Server -> SDK Conversation.run -> Agent.step`，更像“能托管很多 coding agents 的远程开发控制中心”。

## 2. 当前仓库和 software-agent-sdk 的边界

OpenHands 当前仓库的 [README.md](../../../openhands/README.md#L31-L44) 把项目定位为 Agent Canvas / developer control center：可以运行 OpenHands、Claude Code、Codex、Gemini 或 ACP-compatible agent，并支持本地、Docker、VM、云端等多种 backend。

同一 README 还说明：

- OpenHands Agent 和 Agent Server 源码在 [OpenHands/software-agent-sdk](https://github.com/OpenHands/software-agent-sdk)，本仓库已作为 [software-agent-sdk/](../../../software-agent-sdk/) submodule 接入；
- Agent Canvas 源码在 `OpenHands/agent-canvas`；
- 当前仓库保留 App Server / Agent Canvas 相关控制面代码。

因此研读 OpenHands Agent Loop 时需要拆成两层：

```text
OpenHands 当前仓库：
  App Server / Conversation 管理 / Sandbox 管理 / Event 存储 / UI 控制面

software-agent-sdk：
  Agent Server / SDK Conversation / Agent.step / tool action / observation loop
```

这和 Claw-Code、Hermes、OpenClaw 不同：那些项目的 loop 本体基本在各自仓库内；OpenHands 当前仓库把 loop 本体服务化、依赖化到了 Agent Server / SDK 执行面。

## 3. 当前仓库里的控制面主链路

在当前仓库里，一次 conversation 的启动大致是：

```text
前端 / API
  -> OpenHands App Server
     -> 找到或启动 Sandbox
        -> Sandbox 暴露 Agent Server URL
           -> App Server 构造 StartConversationRequest
              -> POST 到 Agent Server /api/conversations
                 -> Agent Server / SDK 内部跑 Agent Loop
```

### 创建 conversation

[LiveStatusAppConversationService](../../../openhands/openhands/app_server/app_conversation/live_status_app_conversation_service.py) 会：

1. 验证 / 准备 sandbox 和 agent-server URL；
2. 构造 working directory；
3. 运行 setup scripts；
4. 构造 `StartConversationRequest`；
5. 向 Agent Server 发起 `POST /api/conversations`。

关键位置：

- 获取 / 验证 agent server URL、准备工作区：[live_status_app_conversation_service.py](../../../openhands/openhands/app_server/app_conversation/live_status_app_conversation_service.py#L380-L416)
- 构造 `StartConversationRequest`：[live_status_app_conversation_service.py](../../../openhands/openhands/app_server/app_conversation/live_status_app_conversation_service.py#L418-L435)
- `POST {agent_server_url}/api/conversations`：[live_status_app_conversation_service.py](../../../openhands/openhands/app_server/app_conversation/live_status_app_conversation_service.py#L442-L469)
- 保存 conversation metadata：[live_status_app_conversation_service.py](../../../openhands/openhands/app_server/app_conversation/live_status_app_conversation_service.py#L487-L529)

这说明 App Server 不是自己执行模型/工具 loop，而是把完整 conversation 请求交给 sandbox 里的 Agent Server。

### 发送后续消息

[app_conversation_router.py](../../../openhands/openhands/app_server/app_conversation/app_conversation_router.py) 里 `send_message_to_conversation(...)` 是一个 thin proxy。

关键位置：

- endpoint 定义：[app_conversation_router.py](../../../openhands/openhands/app_server/app_conversation/app_conversation_router.py#L430-L449)
- 设计说明：该 endpoint 有意保持为薄代理，避免和直接调用 Agent Server 出现行为差异：[app_conversation_router.py](../../../openhands/openhands/app_server/app_conversation/app_conversation_router.py#L455-L471)
- `POST {agent_server_url}/api/conversations/{conversation_id}/events`：[app_conversation_router.py](../../../openhands/openhands/app_server/app_conversation/app_conversation_router.py#L553-L568)

也就是说，后续用户消息并不在 App Server 进入本地模型循环，而是被转发给 Agent Server 的 events endpoint。

### Event 存储 / 查询

当前仓库的 [event_service_base.py](../../../openhands/openhands/app_server/event/event_service_base.py) 更偏控制面的事件管理：

- `get_event(...)`：[event_service_base.py](../../../openhands/openhands/app_server/event/event_service_base.py#L86-L92)
- `search_events(...)`：[event_service_base.py](../../../openhands/openhands/app_server/event/event_service_base.py#L94-L143)
- `iter_events_for_export(...)`：[event_service_base.py](../../../openhands/openhands/app_server/event/event_service_base.py#L145-L156)
- `save_event(...)`：[event_service_base.py](../../../openhands/openhands/app_server/event/event_service_base.py#L190-L198)

这些事件的语义主要来自 Agent Server / SDK 执行面，App Server 负责存储、查询、分页、导出和展示。

## 4. 执行面里的 Conversation.run / Agent.step

真正的 Agent Loop 在外部 `software-agent-sdk` 中。少量源码核验显示核心链路是：

```text
Conversation.run() / arun()
  while True:
      Agent.step() / astep()
```

更展开一些：

```text
Conversation.run / arun
  -> 检查 RUNNING / PAUSED / FINISHED / STUCK / WAITING_FOR_CONFIRMATION
  -> stuck detection / stop hook / max iteration / budget
  -> agent.step / astep
     -> prepare_llm_messages
     -> make_llm_completion
     -> classify_response
        -> TOOL_CALLS: tool_call -> ActionEvent -> execute tool -> ObservationEvent
        -> CONTENT: MessageEvent -> FINISHED
        -> EMPTY / REASONING_ONLY: corrective nudge
```

software-agent-sdk 的关键文件路径：

| 外部路径 | 作用 |
|---|---|
| [conversation.py](../../../software-agent-sdk/openhands-sdk/openhands/sdk/conversation/conversation.py) | `Conversation` factory，根据 workspace 类型选择 `LocalConversation` 或 `RemoteConversation`。 |
| [local_conversation.py](../../../software-agent-sdk/openhands-sdk/openhands/sdk/conversation/impl/local_conversation.py) | `LocalConversation.run()` / `arun()`，外层 conversation execution loop。 |
| [agent.py](../../../software-agent-sdk/openhands-sdk/openhands/sdk/agent/agent.py) | `Agent.step()` / `astep()`，单步 LLM 决策和 action 执行。 |
| [response_dispatch.py](../../../software-agent-sdk/openhands-sdk/openhands/sdk/agent/response_dispatch.py) | 将 LLM response 分类为 `TOOL_CALLS` / `CONTENT` / `REASONING_ONLY` / `EMPTY` 并分派。 |
| [action.py](../../../software-agent-sdk/openhands-sdk/openhands/sdk/event/llm_convertible/action.py) | Action 事件模型。 |
| [observation.py](../../../software-agent-sdk/openhands-sdk/openhands/sdk/event/llm_convertible/observation.py) | Observation 事件模型。 |
| [README.md](../../../software-agent-sdk/openhands-agent-server/openhands/agent_server/README.md) | Agent Server REST / WebSocket API 说明。 |

> 注意：这些文件来自本仓库的 [software-agent-sdk/](../../../software-agent-sdk/) submodule。后续 OpenHands Tool System / Agent Server 专题应继续以该 submodule 作为执行面源码核验入口。

## 5. Action / Observation 与 tool_use / tool_result

OpenHands 的 action / observation 和普通 tool calling 的底层模式是一回事：

```text
模型提出要做外部动作
Harness 执行动作
把结果返回给模型
模型继续思考
```

普通 tool calling 通常表达为：

```text
assistant tool_use
  -> tool 执行
     -> tool_result
        -> assistant 下一轮
```

OpenHands SDK 则表达为：

```text
LLM tool_calls
  -> ActionEvent
     -> 执行 action 对应 tool
        -> Observation
           -> ObservationEvent
              -> 下一轮 Agent.step 再看到 observation
```

区别在抽象视角：

| 维度 | 普通 tool_use / tool_result | OpenHands Action / Observation |
|---|---|---|
| 抽象视角 | 模型调用工具 | Agent 对环境采取行动 |
| 主要对象 | tool call / tool result | ActionEvent / ObservationEvent |
| 关注点 | 协议配对、参数、结果 | 事件持久化、环境变化、UI 展示、审批、安全、轨迹 |
| 适合场景 | 单个 Agent loop / 本地 CLI / 简单 tool runtime | 平台化 SWE Agent / workspace / sandbox / automation |
| 是否回写模型 | 是 | 是，ObservationEvent 后续进入 LLM 上下文 |

因此可以总结为：

> **tool_use / tool_result 是协议层概念；Action / Observation 是平台事件层概念。**

例如跑测试：

```text
tool_use 视角：
  模型调用 run_command("pytest")，工具返回 stdout/stderr。

action/observation 视角：
  Agent 在 workspace 里运行 pytest，环境返回测试失败、错误栈、退出码和输出。
```

后者更适合 SWE Agent，因为 SWE Agent 关心的不只是工具返回字符串，还关心 action 对 workspace / runtime / sandbox 的影响。

## 6. 工具执行在哪个面？

工具执行在 **执行面**。

更具体地说：

```text
控制面：
  App Server / UI / conversation metadata / sandbox 管理 / event 查询

执行面：
  Agent Server / SDK Conversation.run / Agent.step / tool executor / workspace or sandbox
```

当前仓库的 [pyproject.toml](../../../openhands/pyproject.toml#L61-L63) 也能看到执行面依赖：

```text
openhands-agent-server
openhands-sdk
openhands-tools
```

所以链路是：

```text
用户消息
  -> App Server 转发给 Agent Server
     -> Agent Server 运行 Conversation.run()
        -> Agent.step()
           -> LLM 生成 tool_calls
              -> 转成 ActionEvent
                 -> SDK 调用具体 tool
                    -> tool 在 workspace / sandbox 中执行
                       -> 返回 Observation
                          -> 包成 ObservationEvent
```

控制面可以准备工具配置，例如 LLM、tools、MCP、skills、hooks、secrets、workspace 信息，这些在构造 `StartConversationRequest` 时完成，相关位置见 [live_status_app_conversation_service.py](../../../openhands/openhands/app_server/app_conversation/live_status_app_conversation_service.py#L1521-L1782)。但真正的工具运行在 Agent Server / SDK / tools runtime 里。

可以记成：

```text
控制面决定：这个 conversation 有哪些工具、在哪个 sandbox 跑。
执行面负责：模型什么时候调用工具、工具实际怎么跑、结果怎么回给模型。
```

## 7. 与 OpenClaw / DeerFlow / Claw-Code 的对比

### 与 OpenClaw：聊天式 runtime vs 平台执行面分离

OpenClaw 是：

```text
AgentSession
  -> Agent
     -> runLoop
```

它把 session、状态、事件、队列、loop 都放在一个项目内完成，特色是 `steer` / `followUp` 队列和聊天式实时会话控制。

OpenHands 是：

```text
App Server
  -> Sandbox
     -> Agent Server
        -> SDK Conversation.run
           -> Agent.step
```

它不强调本仓库内的 steer/followUp 队列，而强调多 backend、多 sandbox、远程 Agent Server、conversation lifecycle、event storage、automation、workspace/runtime 隔离。

简化对比：

| 对比 | OpenClaw | OpenHands |
|---|---|---|
| 主要形态 | 聊天式 Agent session runtime | 平台化 SWE Agent control plane |
| loop 本体 | 本仓库 `agent-loop.ts` | 外部 `software-agent-sdk` |
| 用户消息 | steer/followUp 队列 | event endpoint / conversation run |
| 工具结果 | tool execution result | ObservationEvent |
| 平台边界 | AgentSession 内部产品化 | App Server / Sandbox / Agent Server 分离 |
| 适合场景 | 多端聊天式 Agent 交互 | 多 backend、多 sandbox、多 automation 的 SWE Agent 平台 |

### 与 DeerFlow：工作流 run 控制 vs SWE Agent 托管平台

DeerFlow 也是平台化，但平台边界不同：

```text
DeerFlow:
  Gateway -> run worker -> agent.astream -> LangGraph agent runtime -> middleware

OpenHands:
  App Server -> Sandbox -> Agent Server -> SDK Conversation.run -> Agent.step
```

DeerFlow 更像“长任务工作流平台的 run 控制”，核心是 run/thread/checkpoint/stream/middleware/clarification/loop detection/token budget；OpenHands 更像“SWE Agent 托管平台”，核心是 workspace/sandbox、Agent Server backend、多 conversation、event storage、automation、action/observation 轨迹。

### 与 Claw-Code：本地 turn loop vs 远程托管平台

Claw-Code 的 `ConversationRuntime::run_turn` 是本地 CLI runtime 的低层 turn loop，主线是：

```text
用户输入 -> 模型流 -> tool_use -> 权限 / hook -> 工具执行 -> tool_result -> 下一轮或结束
```

OpenHands 则把这个能力拆成平台控制面和执行面：控制面负责会话、sandbox、事件、UI、automation；执行面负责真正的 LLM action / observation loop。它适合长时间运行、远程 backend、多 agent、多 workspace、多自动化触发，但对本地单人 CLI 场景来说比 Claw-Code 重。

## 8. 阶段性判断

OpenHands 最值得记录的精髓是：

> **它不是把 Agent Loop 做在一个本地 runtime 里，而是把 Agent Loop 平台化、服务化、远程化。App Server 是控制面，Agent Server / SDK 是执行面，工具调用被抽象成 action / observation 事件流。**

一句话记忆：

```text
OpenHands 不只是一个 Agent Loop；
它是一个能托管很多 Agent Loop 的平台。
```

## QA / 讨论记录

### Q: OpenHands 的 Agent Loop 在当前仓库里吗？

> **状态**: draft  
> **来源**: discussion / source-code / official-repo-docs

A: 当前 `OpenHands/OpenHands` 仓库主要是 Agent Canvas / App Server 控制面，真正的 OpenHands Agent 和 Agent Server 源码在 [OpenHands/software-agent-sdk](https://github.com/OpenHands/software-agent-sdk)，本仓库已作为 [software-agent-sdk/](../../../software-agent-sdk/) submodule 接入。当前仓库负责启动 / 管理 sandbox、构造 conversation request、转发用户消息、查询状态和存储事件；真正的 `Conversation.run()` / `Agent.step()` / ActionEvent / ObservationEvent loop 在 SDK / Agent Server 执行面中。

### Q: OpenHands 的 action / observation 和普通 tool_use / tool_result 是一回事吗？

> **状态**: draft  
> **来源**: discussion / source-code

A: 底层模式是一回事，抽象层级不一样。普通 tool calling 是协议视角：`assistant tool_use -> tool_result -> assistant next`；OpenHands 的 action / observation 是 Agent 与环境交互视角：`ActionEvent -> tool/runtime 执行 -> ObservationEvent -> 下一轮 Agent.step`。前者强调模型调用工具，后者强调 Agent 在 workspace / sandbox 里采取行动并观察环境反馈，更适合平台化 SWE Agent。

### Q: OpenHands 的工具执行在哪个面？

> **状态**: draft  
> **来源**: discussion / source-code

A: 工具执行在执行面。App Server / Agent Canvas 控制面负责创建 conversation、管理 sandbox、准备 tools / MCP / skills / hooks / secrets / workspace 配置、转发消息、查询状态和展示事件；真正执行工具的是 Agent Server / SDK / `openhands-tools`，在对应 workspace / sandbox 中运行。可以记成：控制面决定“这个 conversation 有哪些工具、在哪个 sandbox 跑”；执行面负责“模型什么时候调用工具、工具实际怎么跑、结果怎么回给模型”。

### Q: OpenHands 的控制面 / 执行面分离有什么优缺点？

> **状态**: draft  
> **来源**: discussion / source-code

A: 优点是适合多 backend、远程运行、长时间任务、团队共享、自动化触发、event 追踪和平台 UI；Agent Server / SDK 可以独立承载多个 conversation，App Server 专心管理用户、sandbox、事件、状态和集成。缺点是源码理解和调试链路更长：一次消息可能经过 frontend、App Server、SandboxService、Agent Server HTTP API、SDK Conversation、Agent.step、tool execution、ObservationEvent、event callback 和前端刷新。对本地单人 CLI 场景来说也比 Claw-Code 这种本地 `run_turn` 更重。

### Q: OpenHands 与 OpenClaw / DeerFlow 的精髓差异是什么？

> **状态**: draft  
> **来源**: discussion / source-code

A: OpenClaw 更像“聊天式 Agent 产品的实时会话控制”，loop 本体在本仓库内，核心是 `AgentSession -> Agent -> runLoop`、事件状态和 `steer` / `followUp` 队列；OpenHands 更像“平台化 SWE Agent 的控制面 / 执行面分离”，核心是 App Server / Sandbox / Agent Server / SDK action-observation loop。DeerFlow 更像“长任务工作流平台的 run 控制”，核心是 Gateway run lifecycle、LangGraph runtime 和 middleware；OpenHands 更像“能托管很多 coding agents 的远程开发控制中心”，核心是 workspace/sandbox、Agent Server backend、多 conversation、event storage 和 automation。
