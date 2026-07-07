# Context Management 横向总结：五类 Harness 如何决定“模型下一轮看什么”

> **日期**: 2026-07-07 | **状态**: draft | **涉及项目**: Claw-Code / OpenClaw / Hermes Agent / DeerFlow / OpenHands

## 相关文档

- 项目笔记：
  - [Claw-Code Context Management](../projects/claw-code/context-management.md)
  - [OpenClaw Context Management](../projects/openclaw/context-management.md)
  - [Hermes Agent Context Management](../projects/hermes-agent/context-management.md)
  - [DeerFlow Context Management](../projects/deer-flow/context-management.md)
  - [OpenHands Context Management](../projects/openhands/context-management.md)
- 横向专题：
  - [Agent Loop 横向总结](agent-loop.md)
  - [Tool System 横向总结](tool-system.md)
  - [Project Positioning](project-positioning.md)
- 横向 QA：[qa.md](qa.md#context-management--上下文管理)

## 1. 一句话总览

上下文管理本质上是在回答一个问题：

> **下一次模型调用时，模型到底应该看到什么？**

Agent Harness 里“发生过的事”和“模型现在该知道的事”不是一回事：

```text
发生过的事：
  用户消息、assistant 回复、工具调用、工具结果、文件变化、状态变化、记忆更新、中断、审批、错误、压缩、分支

模型现在该知道的事：
  本轮 provider request 里的 system / user / assistant / tool messages、summary、动态上下文、记忆小抄、工具 schema
```

上下文管理就是把“发生过的事”筛选、修正、压缩、投影成“模型现在该知道的事”。

五个 harness 的核心差异可以先记成：

> **Claw-Code 管一条本地日志；OpenClaw 管一个会话状态机；Hermes 管一个有记忆和自救能力的个人助理脑；DeerFlow 管一条状态流水线；OpenHands 管一本可分支的平台事件账本。**

## 2. 总比喻：如果 Agent 做任务像拍一部施工纪录片

### Claw-Code：本地施工日志

Claw-Code 像一个本地师傅干活时随手记的施工日志：用户说了什么、模型做了什么、工具返回什么，都按顺序写下来。下一轮继续干活，就翻这本日志。

```text
本地 transcript / session messages
  -> 追加 user / assistant / tool result
  -> 必要时 compact
  -> 下一轮发给模型
```

### OpenClaw：带调度室的会话状态机

OpenClaw 除了施工日志，还有一个现场调度室：当前 agent 是 running 还是 idle，用户有没有中途 steer，followUp 队列里还有什么，streaming message 怎么收束，都要被 session runtime 管起来。

```text
AgentSession / Agent
  -> AgentContext.messages
  -> steer / followUp queue
  -> transformContext / convertToLlm
  -> 下一轮模型输入
```

### Hermes Agent：有长期记忆和应急修复能力的个人助理脑

Hermes 像一个长期跟着你的私人助理：它有稳定人格设定，有长期记忆本；每轮回答前会翻小抄；上下文太长会压缩；provider 格式不兼容、空响应、溢出时会修复和重试。

```text
session-stable system prompt
  + persistent messages
  + recall context 临时小抄
  + provider repair / sanitize
  + preflight / pre-API compression
```

### DeerFlow：状态流水线工厂

DeerFlow 像自动化工厂：原材料不是一串聊天记录，而是一组 state channels。每个 middleware 站在流水线上的一个工位，负责写入、压缩、修正或投影某类状态。

```text
ThreadState
  + messages
  + summary_text
  + delegations
  + skill_context
  + uploaded_files / viewed_images
  -> middleware projection
  -> provider messages
```

### OpenHands：远程开发平台的事件账本 + 当前分支剪辑

OpenHands 像远程开发平台：它全程记账，记录用户消息、系统提示、agent action、workspace observation、压缩事件和分支 HEAD。模型每次看到的不是全部账本，而是当前 active branch 剪辑出来的 View。

```text
ConversationState + EventLog
  -> active branch
  -> View
  -> Condensation
  -> LLMConvertibleEvent.events_to_messages
  -> provider messages
```

## 3. 横向总表

| Harness | 最通俗比喻 | 核心上下文容器 | 上下文投影方式 | 最值得记住的精髓 |
|---|---|---|---|---|
| Claw-Code | 本地施工日志 | 本地 transcript / session messages | 线性历史 + compact / retry | 简单线性的 CLI 上下文 |
| OpenClaw | 带调度室的会话状态机 | `AgentContext.messages` + Agent state | `transformContext` / `convertToLlm` | 会话状态、steer、followUp 和消息历史一起管理 |
| Hermes Agent | 有记忆和自救能力的个人助理脑 | session messages + memory / recall context | `build_turn_context` + repair / compression | 稳定 prompt、长期记忆、临时小抄、provider 自救 |
| DeerFlow | 状态流水线工厂 | `ThreadState` channels | middleware projection | 状态通道 + 中间件投影 |
| OpenHands | 远程开发平台事件账本 | `ConversationState + EventLog + View` | active branch View -> LLM messages | 事件账本 + 当前分支剪辑 + 事件化压缩 |

## 4. 统一问题：模型下一轮看到什么？

### 4.1 Claw-Code：模型看到本地线性历史

Claw-Code 的上下文可以概括为：

```text
system prompt
  + session messages
  + tool results
  + compact summary（必要时）
```

模型下一轮看到的是本地 coding turn 的线性历史。工具结果和模型回复按顺序进入 session；当上下文太长时，通过 compact / context-window retry 一类机制缩短历史。

所以它的思路最接近：

> **我把这次本地施工的日志整理好，下一轮继续给师傅看。**

适合场景：本地 CLI coding agent，主线短、执行现场近、调试直观。

### 4.2 OpenClaw：模型看到产品态 session 转换后的 LLM messages

OpenClaw 的上下文管理围绕 `AgentContext.messages`，但这些 messages 同时服务：

- UI streaming；
- tool result 回写；
- session persistence；
- steer / followUp；
- context transform；
- LLM request。

模型下一轮看到的是：

```text
AgentContext.messages
  -> transformContext
  -> convertToLlm
  -> LLM-facing messages
```

这说明 OpenClaw 的 messages 不是裸 provider messages，而是产品态会话消息。它要在用户体验、事件流、持久化和模型协议之间做转换。

所以它的思路更像：

> **调度室先把现场记录、插话、排队任务整理成模型能读的简报，再交给模型。**

适合场景：聊天式 Agent 产品、多端交互、中途 steer / followUp、session runtime。

### 4.3 Hermes Agent：模型看到稳定 prompt + 历史 + 临时记忆小抄 + 修复后的 provider messages

Hermes 的上下文管理有几个关键词：

- session-stable system prompt；
- persistent messages；
- recall context；
- provider repair / sanitize；
- preflight / pre-API compression；
- context overflow recovery。

模型下一轮看到的是：

```text
stable system prompt
  + persistent conversation messages
  + 当前轮 recall context 小抄
  + provider-compatible repaired messages
```

这里最重要的是区分：

```text
长期记录：persistent messages / SessionDB
临时资料：recall context
稳定规则：system prompt
运行韧性：repair / sanitize / compression / fallback
```

Hermes 不把 recall context 当成新的永久聊天消息，也不把它塞进 system prompt 破坏 stable cache prefix。它更像回答前临时翻到的一页参考资料。

所以它的思路更像：

> **私人助理先翻长期记忆本，拿出本轮相关小抄，再检查格式和长度，修好后再去问模型。**

适合场景：长期个人 Agent、多 provider、多入口、长会话、记忆和偏好持续演化。

### 4.4 DeerFlow：模型看到 ThreadState 经 middleware 投影后的当前状态

DeerFlow 的上下文不应该只看 `messages`。更重要的是 `ThreadState` 里的各类 state channel：

- `messages`
- `summary_text`
- `delegations`
- `skill_context`
- uploaded files / viewed images
- todo / thread metadata 等

模型下一轮看到的是：

```text
ThreadState
  -> DynamicContextMiddleware
  -> SummarizationMiddleware
  -> DurableContextMiddleware
  -> MemoryMiddleware / Uploads / ViewImage / SystemMessageCoalescing...
  -> provider request
```

其中每个 middleware 负责一个明确位置：有的在 before_agent，有的在 before_model，有的在 wrap_model_call，有的在 after_agent。理解 DeerFlow 的关键不是找一个万能 context manager，而是问：

```text
这个状态字段在哪里写入？
哪个 middleware 读取它？
它在哪个生命周期点投影给模型？
```

所以它的思路更像：

> **工厂流水线上的每个工位处理一种上下文材料，最后输出当前模型请求。**

适合场景：LangGraph workflow、长任务 run、状态可 checkpoint、多 middleware 协作。

### 4.5 OpenHands：模型看到当前 active branch 的 View

OpenHands 的完整历史在 `EventLog`，但模型每次看到的是 `View`：

```text
EventLog
  -> current leaf_event_id
  -> active_branch()
  -> View
  -> apply Condensation
  -> LLMConvertibleEvent.events_to_messages
```

这个区别非常重要：

```text
EventLog：完整账本 / 完整录像带
View：当前分支剪辑版
LLM messages：View 的 provider 协议投影
```

OpenHands 还带有 conversation tree / branch 概念。`leaf_event_id` 表示当前 HEAD；`active_branch()` 只取当前分支；abandoned branches 不进入当前 View。这让它更适合 Agent Canvas / 远程开发平台里的 fork、navigate、回溯、轨迹管理。

所以它的思路更像：

> **平台保留完整录像和所有分支，但模型每次只看当前分支的剪辑版。**

适合场景：平台化 SWE Agent、workspace / sandbox、事件审计、远程运行、多 conversation、可持久化轨迹。

## 5. 按“发生过的事”和“模型该知道的事”比较

| Harness | “发生过的事”在哪里 | “模型现在该知道的事”怎么来 |
|---|---|---|
| Claw-Code | 本地 session / transcript | 线性历史截取、compact、context-window retry |
| OpenClaw | AgentContext / session event / runtime state | `transformContext -> convertToLlm` |
| Hermes Agent | SessionDB / messages / memory providers / plugin context | turn context 构造、recall context 注入、repair / sanitize、compression |
| DeerFlow | ThreadState / checkpoint / LangGraph messages | middleware 在不同生命周期点投影 state channels |
| OpenHands | ConversationState / EventLog / conversation tree | 当前 active branch View + Condensation + LLMConvertibleEvent 转换 |

统一理解：

> **上下文管理不是保存所有历史，而是决定哪些历史、状态、记忆和环境信息应该以什么形式进入本轮模型输入。**

## 6. 按“压缩 / 遗忘”比较

| Harness | 压缩 / 遗忘方式 | 设计倾向 |
|---|---|---|
| Claw-Code | compact / context-window retry，把本地 history 缩短 | 本地 CLI 继续跑下去 |
| OpenClaw | compaction summary / context transform | 保持 session runtime 和 LLM request 可继续 |
| Hermes Agent | preflight compression、pre-API pressure check、overflow handler | 多 provider 长会话生存韧性 |
| DeerFlow | SummarizationMiddleware 写 `summary_text` state channel | 把旧 messages 压成 durable state projection |
| OpenHands | Condensation event + View.apply | append-only 账本不改，模型 View 应用压缩语义 |

这里 OpenHands 最特别：

```text
普通压缩：改 messages / 替换历史
OpenHands：追加 Condensation 事件，View 决定模型看到压缩后版本
```

Hermes 最特别的是：

```text
压缩不只一个点，而是 turn prologue / API call 前 / overflow recovery 多点防爆
```

DeerFlow 最特别的是：

```text
压缩结果成为 ThreadState 的 summary_text channel，再由 DurableContextMiddleware 投影
```

## 7. 按“动态上下文”比较

| Harness | 动态上下文来源 | 注入方式 | 典型风险 / 取舍 |
|---|---|---|---|
| Claw-Code | 本地项目、session、工具结果、可能的 compact summary | 直接进入本地 conversation history / prompt | 简洁，但平台态状态较少 |
| OpenClaw | session state、steer / followUp、branch summary、产品态消息 | transformContext / convertToLlm 前处理 | 产品消息与 LLM 消息要保持边界 |
| Hermes Agent | memory recall、plugin context、todo / nudge、provider-specific repair | build_turn_context + API-call-time injection | 动态记忆不能污染 stable system prompt |
| DeerFlow | current date、memory snapshot、summary_text、delegations、skill_context | middleware projection | middleware 顺序和生命周期要清楚 |
| OpenHands | AgentContext、skills、secrets、runtime info、SystemPromptEvent.dynamic_context | static system block + dynamic_context block；user extended_content | 要区分 App Server 配置材料、AgentContext 背景资料和 EventLog 历史 |

尤其值得注意两组相似但不同的设计：

### Hermes vs OpenHands：都重视稳定 prompt，但分层不同

```text
Hermes：
  session-stable system prompt
  recall context 追加到当前 user message 的 API copy

OpenHands：
  SystemPromptEvent = static system prompt block + dynamic_context block
  cache marker 由 LLM 层按 provider 处理
```

两者共同点：都不希望每轮随便改 system prompt。

差异：Hermes 更强调长期个人会话中的 stable prompt snapshot；OpenHands 更强调平台执行面里的 static / dynamic content block 分层。

### DeerFlow vs OpenHands：都做投影，但投影对象不同

```text
DeerFlow：
  ThreadState channels -> middleware projection -> provider messages

OpenHands：
  EventLog active branch -> View -> LLMConvertibleEvent.events_to_messages
```

DeerFlow 是 state-channel projection；OpenHands 是 event-sourced View projection。

## 8. 按“工具结果如何回到上下文”比较

| Harness | 工具结果进入上下文的方式 | 关键理解 |
|---|---|---|
| Claw-Code | tool_result 回写本地 session | 工具结果是下一轮模型继续推理的材料 |
| OpenClaw | tool execution lifecycle + message 写入 AgentContext | 工具执行既服务 UI event，也服务 LLM context |
| Hermes Agent | tool results 写回 messages，并可能附带 steer / repair | 要保持 provider tool_call / tool_result 协议结构 |
| DeerFlow | ToolMessage / Command 写入 LangGraph state | 工具结果是 graph runtime 状态的一部分 |
| OpenHands | ObservationEvent 转 role=`tool` message | observation 既是环境观察，也是平台事件和下一轮模型上下文 |

OpenHands 的 Action / Observation 特别适合 SWE Agent：

```text
模型不是只“调用函数”
而是在 workspace 里采取 action
环境返回 observation
这些 action / observation 又成为平台事件、审计轨迹和模型上下文
```

## 9. 按“项目定位”理解上下文管理为什么不同

### 9.1 Claw-Code：本地执行效率优先

Claw-Code 面向本地 CLI coding agent。它的上下文管理追求：

- 本地 loop 主线清楚；
- 工具结果直接回写；
- compact 足够支撑长任务；
- 不引入过重平台事件层。

所以它像“本地施工日志”。

### 9.2 OpenClaw：交互会话 runtime 优先

OpenClaw 面向多端 Agent 控制面 / Claude Code-like 产品会话。它的上下文管理追求：

- session state 明确；
- steer / followUp 可控；
- streaming message、工具事件、持久化和模型输入能互相转换；
- 产品态消息和 LLM-facing messages 分层。

所以它像“带调度室的会话状态机”。

### 9.3 Hermes Agent：长期个人上下文优先

Hermes 面向 memory-evolving personal agent。它的上下文管理追求：

- 长期记忆能参与本轮回答；
- system prompt 稳定；
- recall context 临时可见；
- provider 不稳定时能修复 / fallback；
- 长会话能压缩并继续。

所以它像“有记忆和自救能力的个人助理脑”。

### 9.4 DeerFlow：工作流状态投影优先

DeerFlow 面向 LangGraph / Gateway / 长任务 workflow。它的上下文管理追求：

- state channels 可 checkpoint；
- middleware 职责原子化；
- 每个生命周期点投影明确；
- summary / durable context / memory / uploads / images 分工清楚。

所以它像“状态流水线工厂”。

### 9.5 OpenHands：平台化 SWE Agent 轨迹优先

OpenHands 面向 Agent Canvas / Agent Server / sandbox / automation。它的上下文管理追求：

- conversation 可持久化；
- action / observation 可审计；
- workspace 轨迹可展示；
- 当前分支可投影；
- compression 不破坏原始账本；
- 控制面和执行面分离。

所以它像“远程开发平台的事件账本 + 当前分支剪辑”。

## 10. 精髓标记汇总

### Claw-Code

> **Claw-Code 的上下文管理像本地施工日志：围绕本地 CLI session，把 system prompt、历史消息和工具结果线性组织起来，必要时 compact。**

### OpenClaw

> **OpenClaw 的上下文管理像带调度室的会话状态机：`AgentContext.messages` 不只是 LLM messages，而是 UI、事件、工具回写、steer / followUp、持久化和模型输入之间的产品态中枢。**

### Hermes Agent

> **Hermes 的上下文管理像长期个人助理的大脑：稳定 system prompt 保持人格和 cache，recall context 是本轮临时小抄，repair / compression / fallback 保障长会话能活下去。**

### DeerFlow

> **DeerFlow 的上下文管理像状态流水线工厂：`ThreadState` 是仓库，middleware 是工位，模型看到的是 state channels 被流水线投影后的当前版本。**

### OpenHands

> **OpenHands 的上下文管理像平台事件账本 + 当前分支剪辑：完整历史保存在 EventLog，模型每轮只看 active branch 的 View，压缩通过 Condensation 事件表达。**

## 11. 常见误区

### 误区一：上下文管理就是 messages append

不对。messages append 只是最朴素形式。五个项目里，只有 Claw-Code 最接近这个直觉；OpenClaw 有产品态转换，Hermes 有 memory / repair / compression，DeerFlow 有 state channels / middleware，OpenHands 有 EventLog / View。

### 误区二：动态上下文越多越好

不对。动态上下文会破坏 prompt cache、增加 token、引入污染风险，还可能把临时事实误提升为长期规则。Hermes 把 recall context 放到当前 user message 的 API copy，而不是 system prompt；OpenHands 把 static system prompt 和 dynamic_context 分 block；DeerFlow 用 frozen-snapshot pattern 控制动态上下文漂移。

### 误区三：压缩就是删历史

不完全对。不同项目的压缩语义不同：

- Claw-Code 更像缩短本地历史；
- Hermes 更像多点防爆；
- DeerFlow 把摘要写入 state channel；
- OpenHands 用 Condensation event 表达遗忘语义，原始 EventLog 不直接改。

### 误区四：项目定位会决定它“有没有”某个能力

不能这么看。各项目都有 agent loop、工具结果回写、压缩、状态等基础能力；差别在于谁把哪套机制做成架构核心。例如 DeerFlow 也有 memory，Hermes 也有工具，OpenHands 也有 dynamic context，但它们的中心不一样。

## 12. 后续专题线索

- **OpenHands conversation tree / branch**：`leaf_event_id`、`active_branch()`、fork / navigate、abandoned branches、UI 轨迹展示，值得单独学习。
- **Hermes memory system**：recall context 只是入口，后续应深入 memory provider、事实 / 偏好沉淀、污染防护、skill evolution。
- **DeerFlow middleware lifecycle**：继续按 before_agent / before_model / wrap_model_call / after_agent 梳理每个 middleware 的输入输出。
- **OpenClaw steer / followUp**：从 context management 延伸到 HITL / interaction runtime。
- **Claw-Code compact / Trident**：从本地 session context 延伸到压缩策略和 token budget。

## 13. 最终一句话

> **上下文管理不是“把历史都塞给模型”，而是每个 Harness 按自己的产品形态，把历史、状态、记忆、工具结果和环境信息投影成下一次模型调用可用、可控、不过载的输入。**
