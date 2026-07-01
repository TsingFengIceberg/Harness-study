# Agent Loop 横向总结：从本地 turn loop 到平台化控制面

> **日期**: 2026-07-01 | **状态**: draft | **涉及项目**: Claw-Code / DeerFlow / Hermes Agent / OpenClaw / OpenHands

## 相关文档

- 项目笔记：
  - [Claw-Code Agent Loop](../projects/claw-code/agent-loop.md)
  - [DeerFlow Agent Loop](../projects/deer-flow/agent-loop.md)
  - [Hermes Agent Loop](../projects/hermes-agent/agent-loop.md)
  - [OpenClaw Agent Loop](../projects/openclaw/agent-loop.md)
  - [OpenHands Agent Loop](../projects/openhands/agent-loop.md)
- 横向 QA：[qa.md](qa.md#agent-loop--控制流)
- 项目定位：[project-positioning.md](project-positioning.md)

## 1. Agent Loop 的共同骨架

这些 Harness 的 Agent Loop 写法差异很大，但底层骨架相似：

```text
用户输入 / 任务
  -> 整理上下文
     -> 调模型
        -> 模型输出：
           A. 最终回答：结束
           B. 工具调用 / action：执行外部动作
              -> 拿到工具结果 / observation
                 -> 回写上下文
                    -> 再调模型
```

最简伪代码可以写成：

```text
while True:
    response = call_model(messages)

    if response is final answer:
        return response

    if response asks for tools/actions:
        results = execute_tools(response.tool_calls)
        messages += results
        continue
```

但真实工程的难点不在这个最小循环，而在循环周围的横切能力：

```text
权限
安全
状态
压缩
事件
持久化
取消
重试
中断
多端 UI
sandbox
记忆
provider fallback
HITL
自动化
```

因此本专题真正比较的是：

> **每个 Harness 把这些横切能力放在哪里、强化成什么架构核心。**

## 2. 五个 Harness 的一句话总结

| 项目 | Agent Loop 精髓 | 一句话 |
|---|---|---|
| Claw-Code | 本地 CLI `run_turn` | 本地 CLI 一轮干到底 |
| DeerFlow | Gateway run lifecycle + LangGraph runtime | 长任务工作流平台的 run 控制 |
| Hermes Agent | 大型 `run_conversation` + memory / fallback / steer | 长期个人助理的大脑主循环 |
| OpenClaw | AgentSession + Agent + double loop + steer/followUp | 聊天式 Agent 产品的实时会话控制 |
| OpenHands | App Server + Agent Server + SDK action/observation loop | 平台化 SWE Agent 的控制面 / 执行面分离 |

浓缩成一句话：

> **Claw-Code 是本地一轮干到底；DeerFlow 是工作流平台跑任务；Hermes 是长期私人助理思考；OpenClaw 是聊天式 Agent session runtime；OpenHands 是托管很多 Coding Agent 的平台控制中心。**

## 3. 工作组织方式比喻

### Claw-Code：本地老师傅

Claw-Code 像一个本地老师傅。你把活交给他，他就在你旁边一轮干到底：

```text
看代码
跑命令
检查权限
调用工具
记录结果
再想
再改
最后回复
```

它的主线集中在 [Claw-Code Agent Loop](../projects/claw-code/agent-loop.md) 记录的 `ConversationRuntime::run_turn` 附近。

**优点**：主线清楚、适合本地 CLI、调试直观、很容易学习 Agent Loop 基本骨架。  
**缺点**：权限、hook、压缩、session、工具执行等横切逻辑容易挤到主循环附近；多端 UI、复杂 session 状态、平台化能力不是默认重心。

关键词：

```text
本地 CLI
run_turn
一轮干到底
内联横切逻辑
```

### DeerFlow：工作流调度中心

DeerFlow 像一个大型项目管理系统 / 工作流工厂。任务进来以后，系统创建 run，派给 worker，中间有各种质检、预算、安全、澄清、循环检测节点。

它的 Agent Loop 不集中在一个手写 `while tool_use` 函数里，而是由 Gateway run lifecycle + LangGraph agent runtime 共同构成，详见 [DeerFlow Agent Loop](../projects/deer-flow/agent-loop.md)。

**优点**：适合长任务、run 生命周期管理、middleware 系统化处理横切逻辑、checkpoint / stream / cancel / clarification 很自然。  
**缺点**：Agent Loop 不像 Claw-Code 那样一眼看到；需要理解 Gateway、worker、LangGraph、middleware 多层；模型/工具循环本体被框架吸收。

关键词：

```text
run lifecycle
LangGraph runtime
middleware
checkpoint
clarification
长任务治理
```

### Hermes Agent：长期私人助理的大脑

Hermes 像一个长期跟你共事的私人助理。它不是只处理当前这一轮任务，还会关心：

```text
你是谁
过去聊过什么
偏好是什么
记忆是什么
当前工具是否失败
provider 是否要 fallback
用户是否中途 steer
是否被 interrupt
上下文是否太长
```

所以 [Hermes Agent Loop](../projects/hermes-agent/agent-loop.md) 中的 `run_conversation` 很长，因为它承担的是长期个人 Agent 的真实复杂度。

**优点**：长期协作能力强、memory / session persistence / provider fallback 突出、interrupt 和 steer 适合个人 Agent、真实复杂环境下韧性强。  
**缺点**：loop 容易变成 god function；provider fallback、empty response recovery、memory、tool guardrail 都会吸进主循环；维护成本高。

关键词：

```text
run_conversation
memory
provider fallback
interrupt
steer
长期个人 Agent
```

### OpenClaw：有前台、调度员、工人的聊天工作室

OpenClaw 像一个小型 Agent 工作室：

```text
AgentSession：前台 / 产品会话层
Agent：调度员 / 状态和队列层
runLoop：工人 / 模型工具执行层
```

它的核心是 [OpenClaw Agent Loop](../projects/openclaw/agent-loop.md) 记录的 `AgentSession -> Agent -> runLoop` 三层结构，以及 double loop：

```text
内层：当前任务没干完，模型还要工具，继续干
外层：当前任务结束了，但用户又 followUp，接着干下一件
```

再加上两类中途输入：

```text
steer：运行中用户扶方向盘
followUp：结束后用户追加工单
```

**优点**：适合聊天式 Agent 产品；steer / followUp 队列语义清晰；event / state / session 分层比单函数更产品化；比 DeerFlow 更贴近实时会话控制。  
**缺点**：阅读时要跨 AgentSession / Agent / runLoop；比 Claw-Code 更复杂；需要理解事件、状态、队列和 double loop。

关键词：

```text
AgentSession
Agent
runLoop
double loop
steer / followUp
聊天式实时会话控制
```

### OpenHands：远程开发控制中心

OpenHands 当前仓库更像一个 Agent 平台控制中心，而不是把 Agent Loop 全写在当前仓库里。它拆成：

```text
控制面：
  App Server / Agent Canvas / conversation / sandbox / event / UI / automation

执行面：
  Agent Server / software-agent-sdk / Conversation.run / Agent.step / tools
```

详见 [OpenHands Agent Loop](../projects/openhands/agent-loop.md)。工具执行在执行面；控制面负责开会话、管 sandbox、转发消息、查状态、存事件、展示 UI 和触发自动化。

**优点**：适合多 backend、远程运行、团队共享、automation、长期任务和事件追踪；action / observation 模型很适合 SWE Agent。  
**缺点**：源码理解跨当前仓库 + `software-agent-sdk`；调试链路长；对本地单人 CLI 场景显得重；控制面和执行面边界要先搞清楚。

关键词：

```text
App Server
Agent Server
software-agent-sdk
Conversation.run
Agent.step
ActionEvent / ObservationEvent
控制面 / 执行面分离
```

## 4. 开车比喻

### Claw-Code：本地老司机

你坐上车，告诉司机目的地。司机自己看路、打方向、踩油门、查地图，最后到达。

```text
本地老司机，一轮开到底。
```

### DeerFlow：交通调度中心

你不是直接找司机，而是提交运输任务。系统安排路线、检查点、调度员、中转站、监控、异常处理和暂停确认。

```text
大型交通调度系统，任务按流程跑。
```

### Hermes Agent：长期私人司机兼管家

这个司机长期为你服务，知道你喜欢走哪条路、讨厌堵车、上次去哪里，也能区分你中途说话是在打断还是提醒。

```text
长期私人司机，不只是开车，还记得你。
```

### OpenClaw：可实时插话的网约车系统

你在车上说“先别去公司，绕去咖啡店”，这是 `steer`；到目的地后又说“顺便再去超市”，这是 `followUp`。

```text
聊天式实时会话控制，副驾可以扶方向盘。
```

### OpenHands：车队运营平台

它不是一辆车，而是一个车队平台：控制台、多个司机、多辆车、远程车库、任务调度、行车记录、自动派单、团队管理。

```text
能托管很多司机和车辆的远程运营中心。
```

## 5. 公司组织比喻

| 项目 | 公司比方 |
|---|---|
| Claw-Code | 一个全能工程师，接到任务自己干完 |
| DeerFlow | 一个项目管理办公室，任务按流程、节点、审批、检查点推进 |
| Hermes Agent | 一个长期私人助理，记得你的历史、偏好和沟通方式 |
| OpenClaw | 一个聊天客服工作室，有前台、调度员、执行员，用户能中途补充方向 |
| OpenHands | 一个工程外包平台 / Agent 运维中心，能管理很多远程工程师和工作区 |

## 6. 关键维度横向比较

### Loop 本体在哪里？

| 项目 | Loop 本体 |
|---|---|
| Claw-Code | 本仓库 `ConversationRuntime::run_turn` |
| DeerFlow | LangGraph runtime 内部，外层由 Gateway worker 驱动 |
| Hermes Agent | 本仓库 `run_conversation` |
| OpenClaw | 本仓库 `agent-loop.ts` 的 `runLoop` |
| OpenHands | 外部 `software-agent-sdk` 的 `Conversation.run` / `Agent.step` |

### 谁负责工具执行？

| 项目 | 工具执行位置 |
|---|---|
| Claw-Code | 本地 runtime / ToolExecutor |
| DeerFlow | LangGraph / tool runtime / sandbox / middleware 包裹 |
| Hermes Agent | `tool_executor.py`，可串行 / 并发 |
| OpenClaw | `agent-loop.ts` 工具执行层，Session hook 包裹 |
| OpenHands | 执行面：Agent Server / SDK / `openhands-tools` / workspace-sandbox |

### 用户中途干预怎么处理？

| 项目 | 中途干预方式 |
|---|---|
| Claw-Code | 主要是本地 turn / 权限 / hook / interrupt 相关机制，实时 steer 不是核心抽象 |
| DeerFlow | run lifecycle、clarification、interrupt / rollback、checkpoint |
| Hermes Agent | interrupt 硬打断，steer 软引导 |
| OpenClaw | steer / followUp 队列是一等机制 |
| OpenHands | 控制面通过 events endpoint / confirmation / conversation status 介入，执行面继续 run |

### 状态和事件有多中心？

| 项目 | 状态 / 事件地位 |
|---|---|
| Claw-Code | 有 session / turn summary，但主线更函数式 |
| DeerFlow | run/thread/checkpoint/stream 是核心 |
| Hermes Agent | session persistence 和 memory 很核心 |
| OpenClaw | AgentEvent / AgentState 是核心 |
| OpenHands | Event storage / ActionEvent / ObservationEvent / ConversationState 是平台核心 |

### 更适合什么场景？

| 项目 | 适合场景 |
|---|---|
| Claw-Code | 本地 CLI coding agent |
| DeerFlow | 长任务、复杂流程、图式编排 |
| Hermes Agent | 长期个人 Agent、记忆、偏好、持续协作 |
| OpenClaw | 聊天式、多端、实时会话 Agent |
| OpenHands | 平台化 SWE Agent、远程 backend、sandbox、automation、团队控制面 |

## 7. Agent Loop 分类法

### 函数式 turn loop

代表：Claw-Code。

```text
一个函数附近串起一轮模型 / 工具 / 权限 / hook / 结果回写。
```

适合学习最清楚的主干。

### 生命周期式 run driver

代表：DeerFlow。

```text
外层是 run lifecycle，内部模型/工具循环交给框架 runtime。
```

适合平台化长任务治理。

### 长期个人 conversation loop

代表：Hermes Agent。

```text
Agent Loop 吸收 memory、provider fallback、interrupt、steer、压缩、长期上下文。
```

适合个人长期协作。

### 事件驱动 session/message loop

代表：OpenClaw。

```text
手写 core loop + AgentEvent / AgentState + steer/followUp 队列 + Session 外壳。
```

适合聊天式实时 Agent 产品。

### 控制面 / 执行面分离的 action-observation loop

代表：OpenHands。

```text
App Server 管平台，Agent Server / SDK 跑 loop，工具调用抽象成 ActionEvent / ObservationEvent。
```

适合 SWE Agent 平台和远程托管。

## 8. 最浓缩版

如果只记五句话：

```text
Claw-Code：本地 CLI 一轮干到底。
DeerFlow：长任务工作流平台的 run 控制。
Hermes：长期个人助理的大脑主循环。
OpenClaw：聊天式 Agent 产品的实时会话控制。
OpenHands：平台化 SWE Agent 的控制面 / 执行面分离。
```

如果只记一个总比喻：

```text
Claw-Code 是本地老师傅；
DeerFlow 是工作流调度中心；
Hermes 是长期私人助理；
OpenClaw 是可实时插话的聊天工作室；
OpenHands 是能托管很多 coding agents 的远程开发控制中心。
```

如果只记一个技术抽象：

> **Agent Loop 的本质都是“模型决策 -> 外部动作 -> 环境反馈 -> 再决策”，差异在于：这个循环被放在本地函数里、框架 runtime 里、长期记忆大脑里、聊天 session runtime 里，还是平台化 Agent Server 里。**

## QA / 讨论记录

### Q: Agent Loop 第一轮是否已经完成？

> **状态**: draft  
> **来源**: discussion / source-code

A: Claw-Code / DeerFlow / Hermes Agent / OpenClaw / OpenHands 这五个主线 Harness 的 Agent Loop 第一轮已经形成稳定理解，可以视作第一轮完成。后续还可以补 learn-claude-code 作为“最小教学模型 / baseline”，用来反推最简 Agent Loop 骨架；但它不影响当前五项目核心比较的完成。

### Q: 为什么不能只比较谁有没有 `while tool_use`？

> **状态**: draft  
> **来源**: discussion

A: 因为最小 `while tool_use` 只是所有 Agent Loop 的共同骨架。真实 Harness 的差异在于权限、安全、状态、压缩、事件、持久化、取消、重试、中断、多端 UI、sandbox、记忆、provider fallback、HITL、自动化等横切能力被放在哪里、怎么组织、是否成为架构核心。Agent Loop 比较要从“循环骨架”上升到“横切能力的架构归属”。
