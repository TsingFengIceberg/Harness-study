# OpenClaw Agent Loop：事件驱动的 Session / Message 双层循环

> **日期**: 2026-07-01 | **状态**: draft | **涉及版本**: `openclaw` submodule `9003042c5f`

## 相关文档

- OpenClaw 笔记入口：[README.md](README.md)
- 核心源码：
  - Session 外壳：[agent-session.ts](../../../submodules/openclaw/src/agents/sessions/agent-session.ts)
  - Agent 核心：[agent.ts](../../../submodules/openclaw/packages/agent-core/src/agent.ts)
  - Loop 本体：[agent-loop.ts](../../../submodules/openclaw/packages/agent-core/src/agent-loop.ts)
  - 类型定义：[types.ts](../../../submodules/openclaw/packages/agent-core/src/types.ts)
- 横向 QA：[Harness Study 横向 QA](../../comparison/qa.md#agent-loop--控制流)
- Sandbox / Workspace：[sandbox-workspace.md](sandbox-workspace.md)

## 1. 核心结论

OpenClaw 的 Agent Loop 不是简单的 `while tool_use`，也不是 DeerFlow 那种把模型/工具循环主要交给 LangGraph runtime 的架构。它更像一个 **事件驱动的 session/message runtime**。

可以概括为：

> **OpenClaw = 手写 core double loop + Agent 事件状态机 + AgentSession 产品会话外壳。**

它的精髓对比是：

- **和 DeerFlow 比**：DeerFlow 更像“长任务工作流平台的 run 控制”；OpenClaw 更像“聊天式 Agent 产品的实时会话控制”。
- **和 Claw-Code 比**：Claw-Code 更像“本地 CLI 一轮干到底”；OpenClaw 更像“有事件、有队列、有状态的 Agent session runtime”。

## 2. 三层结构：AgentSession / Agent / runLoop

OpenClaw 的 loop 阅读路径需要跨三层：

```text
AgentSession：产品会话层
  -> Agent：状态 / 事件 / 队列层
     -> runLoop：模型 / 工具执行层
```

### AgentSession：产品会话外壳

[AgentSession](../../../submodules/openclaw/src/agents/sessions/agent-session.ts) 是面向产品运行时的会话对象。它不是模型/工具循环本体，而是负责把核心 Agent loop 接到 OpenClaw 的会话体系里。

重点职责包括：

- 用户 prompt 入口与排队；
- 模型校验；
- tool hook 安装；
- compaction / retry / continuation；
- session persistence；
- turn tracking；
- 将 `AgentEvent` 接到 UI / runtime / 持久化逻辑。

关键入口：

- `AgentSession` class：[agent-session.ts](../../../submodules/openclaw/src/agents/sessions/agent-session.ts#L334)
- `installAgentToolHooks(...)`：[agent-session.ts](../../../submodules/openclaw/src/agents/sessions/agent-session.ts#L497)
- `handleAgentEvent(...)`：[agent-session.ts](../../../submodules/openclaw/src/agents/sessions/agent-session.ts#L576)
- `runAgentPrompt(...)`：[agent-session.ts](../../../submodules/openclaw/src/agents/sessions/agent-session.ts#L1089)
- `prompt(...)`：[agent-session.ts](../../../submodules/openclaw/src/agents/sessions/agent-session.ts#L1133)

### Agent：状态、事件与消息队列

[Agent](../../../submodules/openclaw/packages/agent-core/src/agent.ts) 是核心 Agent 抽象，负责维护 `AgentState`、订阅 / 处理 `AgentEvent`，并暴露 `prompt()`、`continue()`、`steer()`、`followUp()` 等方法。

关键入口：

- `Agent` class：[agent.ts](../../../submodules/openclaw/packages/agent-core/src/agent.ts#L203)
- `steer(...)`：[agent.ts](../../../submodules/openclaw/packages/agent-core/src/agent.ts#L313)
- `followUp(...)`：[agent.ts](../../../submodules/openclaw/packages/agent-core/src/agent.ts#L318)
- `prompt(...)`：[agent.ts](../../../submodules/openclaw/packages/agent-core/src/agent.ts#L374)
- `continue(...)`：[agent.ts](../../../submodules/openclaw/packages/agent-core/src/agent.ts#L390)
- `runPromptMessages(...)`：[agent.ts](../../../submodules/openclaw/packages/agent-core/src/agent.ts#L438)
- `processEvents(...)`：[agent.ts](../../../submodules/openclaw/packages/agent-core/src/agent.ts#L568)

### runLoop：模型 / 工具循环本体

真正执行“模型调用 -> 工具执行 -> 工具结果回写 -> 再调用模型”的核心逻辑在 [agent-loop.ts](../../../submodules/openclaw/packages/agent-core/src/agent-loop.ts)。

关键入口：

- `runAgentLoop(...)`：[agent-loop.ts](../../../submodules/openclaw/packages/agent-core/src/agent-loop.ts#L171)
- `runAgentLoopContinue(...)`：[agent-loop.ts](../../../submodules/openclaw/packages/agent-core/src/agent-loop.ts#L198)
- `runLoop(...)`：[agent-loop.ts](../../../submodules/openclaw/packages/agent-core/src/agent-loop.ts#L265)
- `streamAssistantResponse(...)`：[agent-loop.ts](../../../submodules/openclaw/packages/agent-core/src/agent-loop.ts#L446)
- `executeToolCalls(...)`：[agent-loop.ts](../../../submodules/openclaw/packages/agent-core/src/agent-loop.ts#L548)

所以如果问“OpenClaw 的 Agent Loop 在哪里”，可以分两层回答：

1. **核心循环本体**在 [agent-loop.ts](../../../submodules/openclaw/packages/agent-core/src/agent-loop.ts)，尤其是 `runLoop(...)`。
2. **产品化 session runtime**在 [agent-session.ts](../../../submodules/openclaw/src/agents/sessions/agent-session.ts)，负责把核心 loop 接到会话、工具 hook、压缩、持久化和 UI 事件。

## 3. 为什么说它是 double loop？

OpenClaw 的核心不是一个单纯的：

```text
while 模型还要工具:
    执行工具
    把工具结果给模型
```

它更像：

```text
外层 loop：处理 follow-up / 追加消息 / 下一轮继续
  内层 loop：处理 tool call / tool result / steer
```

更口语地说：

```text
内层：这件事没干完，就继续干。
外层：这件事干完了，但用户又追加了，就接着干下一件。
```

### 内层 loop：模型和工具之间来回

内层 loop 处理的是普通 Agent Loop 的主干：

```text
模型：我要读文件
工具：返回文件内容
模型：我要跑测试
工具：返回测试结果
模型：我要看报错文件
工具：返回文件内容
模型：最终回答
```

也就是：

```text
模型 -> 工具 -> 模型 -> 工具 -> 模型
```

这部分对应 [runLoop(...)](../../../submodules/openclaw/packages/agent-core/src/agent-loop.ts#L265) 中围绕 assistant response、tool calls 和 tool execution 的循环，以及 [executeToolCalls(...)](../../../submodules/openclaw/packages/agent-core/src/agent-loop.ts#L548)。

### 外层 loop：结束后还有 followUp，就继续

外层 loop 处理的是 Agent 本来要结束时，用户又追加了一句的情况。

例如：

```text
Agent：测试失败原因是 backend mock 配置不对。
用户：那你顺便看看怎么修。
```

这句话不是运行中的 steer，因为 Agent 已经到结束点；它更像“追加下一轮任务”。OpenClaw 用 `followUp` 队列表达这类消息。

## 4. steer 与 followUp：两类中途输入

OpenClaw 把用户中途输入拆成两类：

| 类型 | 发生时机 | 含义 | 类比 |
|---|---|---|---|
| `steer` | Agent 正在运行中 | 调整当前任务方向 | 坐副驾提醒：“先往左走” |
| `followUp` | Agent 准备结束或已结束后 | 追加下一轮任务 | 任务完成后又补一张工单 |

### steer：当前任务中的软引导

`steer` 是运行中的软引导。用户不是要打断整个 run，而是在当前任务还没结束时补充方向。

例如：

```text
Agent 正在分析 frontend
用户：等等，先看 backend，frontend 先别管
```

OpenClaw 将这类消息放进 steering queue，在后续模型调用中让模型看到。它解决的是“当前任务正在跑，用户怎么扶方向盘”的问题。

关键位置：

- `Agent.steer(...)`：[agent.ts](../../../submodules/openclaw/packages/agent-core/src/agent.ts#L313)
- `runLoop(...)`：[agent-loop.ts](../../../submodules/openclaw/packages/agent-core/src/agent-loop.ts#L265)

### followUp：结束点之后的追加

`followUp` 是 Agent 已经准备结束或已经结束时的追加输入。

例如：

```text
Agent：问题定位完了。
用户：那顺便给我写个修复方案。
```

OpenClaw 将这类消息放进 follow-up queue，由外层 loop 决定是否再开启一轮执行。

关键位置：

- `Agent.followUp(...)`：[agent.ts](../../../submodules/openclaw/packages/agent-core/src/agent.ts#L318)
- `runLoop(...)`：[agent-loop.ts](../../../submodules/openclaw/packages/agent-core/src/agent-loop.ts#L265)

### 为什么要拆成两个队列？

如果所有用户补充都只是普通 user message，系统就很难判断：

```text
这是要改变当前任务方向？
还是要等当前任务结束后再处理？
还是要硬打断？
```

OpenClaw 把它们拆成 `steer` 和 `followUp`，等于把“运行中引导”和“结束后追加”变成 Agent core 的一等调度语义。

## 5. 事件驱动：loop 一边跑，一边发事件

OpenClaw 的 loop 不只是最后返回一个字符串，而是在执行过程中不断发出 `AgentEvent`。Agent 层消费这些事件并更新 `AgentState`；Session 层订阅事件后做 UI 更新、持久化、hook 等产品逻辑。

可以理解为：

```text
runLoop 产生事件
Agent 根据事件更新状态
AgentSession 根据事件做产品侧处理
```

典型事件链路包括：

```text
agent_start
turn_start
message_start
message_update
message_end
tool_execution_start
tool_execution_end
turn_end
agent_end
```

这让 OpenClaw 更像一个可观察的 Agent session runtime，而不只是“执行一轮然后返回结果”。

相关位置：

- `processEvents(...)`：[agent.ts](../../../submodules/openclaw/packages/agent-core/src/agent.ts#L568)
- loop event 产生：[agent-loop.ts](../../../submodules/openclaw/packages/agent-core/src/agent-loop.ts#L265)
- Session event 处理：[agent-session.ts](../../../submodules/openclaw/src/agents/sessions/agent-session.ts#L576)

## 6. 与 Claw-Code / DeerFlow / Hermes 的对比

### 对比 Claw-Code：本地 CLI 一轮干到底 vs Agent session runtime

Claw-Code 的 Agent Loop 更像本地 CLI 的单轮对话循环本体：

```text
用户说一句
  -> ConversationRuntime::run_turn
     -> 模型流
     -> tool_use
     -> 权限 / hook
     -> 工具执行
     -> tool_result
     -> 下一轮模型调用或结束
```

它的优点是主线直观、局部可调试，适合本地命令行“一轮干到底”的交互模式。

OpenClaw 则把同类能力拆成：

```text
AgentSession：产品会话
Agent：状态、事件、队列
runLoop：模型 / 工具执行
```

所以 OpenClaw 更适合表达 UI、多端、session 状态、中途插话和事件可观察性，但源码阅读时也更需要跨文件理解。

### 对比 DeerFlow：run 控制 vs 实时会话控制

DeerFlow 的 Agent Loop 由 Gateway run lifecycle + LangGraph agent runtime 共同构成：Gateway 创建 run，worker 调 `agent.astream(...)`，真正的模型/工具循环由 LangGraph / LangChain agent runtime 执行。

所以 DeerFlow 更像：

```text
长任务工作流平台的 run 控制
```

它关注 run/thread/checkpoint/stream/middleware/cancel/clarification 等长任务治理能力。

OpenClaw 则自己手写 [runLoop(...)](../../../submodules/openclaw/packages/agent-core/src/agent-loop.ts#L265)，并在 core Agent 中放入 steer/followUp 队列，因此更像：

```text
聊天式 Agent 产品的实时会话控制
```

它关注运行中的用户插话、结束后的追加消息、事件状态和 session runtime。

### 对比 Hermes：长期个人 Agent 大循环 vs 队列化 session runtime

Hermes 的 `run_conversation` 是长期个人 Agent 的大型手写 loop，memory、provider fallback、empty response recovery、interrupt/steer、session persistence、compression 等逻辑都围绕长期协作展开。

OpenClaw 和 Hermes 都有软引导思想，但组织方式不同：

- Hermes 的 steer 更像长期个人 Agent loop 里的中途引导分支；
- OpenClaw 的 steer/followUp 更像 Agent core 的消息调度队列。

所以 Hermes 更像“长期个人助理的大脑主循环”，OpenClaw 更像“事件化、队列化、session 化的 Agent 产品 runtime”。

## 7. 阶段性判断

OpenClaw 的独特价值不是“它也有 tool loop”，而是它把 tool loop 放进了一个更产品化的 session/message runtime 里：

1. 核心模型/工具循环自己手写，不委托 LangGraph；
2. 外面包了一层 Agent 状态和事件系统；
3. 再外面包了一层 AgentSession 产品会话层；
4. 用户中途输入被拆成 `steer` 和 `followUp` 两类队列；
5. 因此形成外层消息调度 loop + 内层模型/工具 loop 的双层结构。

一句话总结：

> **OpenClaw 把 Agent Loop 产品化了：不只是模型工具循环，而是一个能被 UI 观察、能中途调整、能追加任务、能持久化的 session loop。**

## QA / 讨论记录

### Q: OpenClaw 的 Agent Loop 是不是像 Claw-Code 一样是手写 loop？

> **状态**: draft  
> **来源**: discussion / source-code

A: 是手写 loop，但组织方式和 Claw-Code 不同。Claw-Code 的 `run_turn` 更像本地 CLI 的单轮对话循环本体；OpenClaw 的核心 `runLoop(...)` 虽然也是手写，但外面包了 `Agent` 事件状态层和 `AgentSession` 产品会话层，并且把运行中 `steer` 与结束后 `followUp` 做成队列。因此 OpenClaw 更像“有事件、有队列、有状态的 Agent session runtime”。

### Q: OpenClaw 的 double loop 怎么理解？

> **状态**: draft  
> **来源**: discussion / source-code

A: 可以把它理解成“外层处理追加消息，内层处理当前任务”。内层 loop 是普通模型/工具循环：模型要工具、工具返回结果、模型继续思考；外层 loop 是当前任务到结束点后，如果用户还有 `followUp`，就再开下一轮。口语化地说：内层是“这件事没干完，继续干”；外层是“这件事干完了，但用户又追加了，接着干下一件”。

### Q: OpenClaw 的 `steer` 和 `followUp` 有什么区别？

> **状态**: draft  
> **来源**: discussion / source-code

A: `steer` 是 Agent 正在运行时用户补充方向，语义是“扶方向盘”，影响当前任务后续模型调用；`followUp` 是 Agent 准备结束或已经结束后用户追加下一句，语义是“再补一张工单”，由外层 loop 开启下一轮处理。拆成两类队列，可以避免把运行中引导、结束后追加和硬打断混成一种普通 user message。

### Q: OpenClaw 的 Session 层分离和 double loop 是一回事吗？

> **状态**: draft  
> **来源**: discussion / source-code

A: 相关但不是一回事。Session 层分离是架构分层：`AgentSession` 负责产品会话、持久化、模型校验、hook、compaction、retry 等，`Agent` / `runLoop` 负责 Agent 状态和模型/工具执行。double loop 是运行控制流分层：外层处理 followUp / 追加消息，内层处理 tool call / tool result / steer。可以记成：Session 分离回答“谁负责产品会话”，double loop 回答“运行时怎么处理消息和工具”。

### Q: OpenClaw 与 DeerFlow / Claw-Code 的精髓差异是什么？

> **状态**: draft  
> **来源**: discussion / source-code

A: 和 DeerFlow 比，DeerFlow 更像“长任务工作流平台的 run 控制”，核心是 run/thread/checkpoint/stream/middleware/cancel/clarification 等生命周期治理；OpenClaw 更像“聊天式 Agent 产品的实时会话控制”，核心是手写 loop、事件状态、steer/followUp 队列和 session runtime。和 Claw-Code 比，Claw-Code 更像“本地 CLI 一轮干到底”，核心是 `run_turn` 主干；OpenClaw 更像“有事件、有队列、有状态的 Agent session runtime”，核心是 `AgentSession -> Agent -> runLoop` 分层。
