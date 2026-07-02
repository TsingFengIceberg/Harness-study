# Tool System 横向总结：从集中式工具中枢到分层式工具治理

> **日期**: 2026-07-02 | **状态**: draft | **涉及项目**: Claw-Code / DeerFlow / OpenHands / OpenClaw / Hermes Agent

## 相关文档

- 项目笔记：
  - [Claw-Code Tool System](../projects/claw-code/tool-system.md)
  - [Claw-Code Agent Loop](../projects/claw-code/agent-loop.md)
  - [DeerFlow Agent Loop](../projects/deer-flow/agent-loop.md)
  - [OpenHands Agent Loop](../projects/openhands/agent-loop.md)
  - [OpenClaw Agent Loop](../projects/openclaw/agent-loop.md)
  - [Hermes Agent Loop](../projects/hermes-agent/agent-loop.md)
- 横向 QA：[qa.md](qa.md#tool-system--工具体系)
- 上一专题：[Agent Loop 横向总结](agent-loop.md)

## 本文范围

本文是 Tool System 专题的第一轮横向总结，重点基于已经完成的 [Claw-Code Tool System](../projects/claw-code/tool-system.md) 源码研读，先建立一组后续比较 DeerFlow / OpenHands / OpenClaw / Hermes Agent 时可复用的问题框架。

因此本文中的 Claw-Code 判断已结合源码路径；其他项目的工具系统判断暂时主要来自已完成的 Agent Loop 笔记和阶段性讨论，后续需要在各项目 `tool-system.md` 中继续源码核验。

## Tool System 不是只有 tool call

最容易误解的是：

```text
Tool System = 模型能调用几个函数
```

但在真实 Agent Harness 里，Tool System 至少包含：

```text
工具定义
工具 schema
工具注册
工具可见性
工具权限
工具执行
工具结果回写
错误恢复
hook / middleware
sandbox / workspace 边界
外部工具生态接入
子 agent / background task / worker 等高阶能力工具化
```

所以更准确地说：

> **Tool System 是 Agent 触达外部世界的能力总线。**

模型本身只产生意图和参数，Harness 通过工具系统把这些意图翻译成真实环境动作，再把 observation / tool result 回写给模型。

## Claw-Code：集中式工具中枢

Claw-Code 的工具系统主线见 [Claw-Code Tool System](../projects/claw-code/tool-system.md)。它可以概括为：

> **集中式、本地 CLI 风格的工具中枢。**

核心源码集中在 [lib.rs](../../claw-code/rust/crates/tools/src/lib.rs) 与 [conversation.rs](../../claw-code/rust/crates/runtime/src/conversation.rs)：

| 层级 | Claw-Code 做法 |
|---|---|
| 工具定义 | `ToolSpec` 定义 name、description、input_schema、required_permission。 |
| 工具注册 | `GlobalToolRegistry` 汇总 builtin / plugin / runtime tools。 |
| 工具暴露 | `definitions(...)` 转成 provider `ToolDefinition`，并按 allowed tools 过滤。 |
| 工具执行 | `ConversationRuntime::run_turn` 提取 `ToolUse`，调用 `ToolExecutor.execute`。 |
| 执行分发 | `execute_tool_with_enforcer(...)` 用大 match 分发到 `run_xxx`。 |
| 权限治理 | `PreToolUse hook + PermissionPolicy / PermissionPrompter + PermissionEnforcer` 两道门。 |
| 结果回写 | `ContentBlock::ToolResult` 写回 Session，下一轮转成 provider tool result。 |
| 工具发现 | `ToolSearch` 对 deferred tools 做目录式关键词检索。 |

### 精髓一：工具大中枢

Claw-Code 的优点是：

```text
直接
内联
可控
本地 CLI 调试直观
工具调用链短
```

代价是：

```text
mvp_tool_specs() 越来越大
execute_tool_with_enforcer() 越来越大
工具定义、schema、权限、搜索、执行分发集中在一个工具模块附近
```

这形成了一个很典型的本地 Coding CLI 取舍：

> **清楚，但重；直接，但集中；适合本地 CLI，但长期会面临工具中枢膨胀。**

### 精髓二：两道权限门

Claw-Code 不是只按工具名判断权限。

第一扇门在 [conversation.rs](../../claw-code/rust/crates/runtime/src/conversation.rs)：

```text
PreToolUse hook
  -> PermissionPolicy
    -> PermissionPrompter
```

它问：

> **这个工具类型当前能不能用？**

第二扇门在 [execute_tool_with_enforcer](../../claw-code/rust/crates/tools/src/lib.rs)：

```text
根据具体参数分类 required_mode
  -> maybe_enforce_permission_check_with_mode
    -> PermissionEnforcer.check_with_required_mode
```

它问：

> **这个具体调用参数会不会越界？**

例如：

```text
bash "git status" 和 bash "rm -rf /" 都是 bash，但风险不同。
read_file "README.md" 和 read_file "/etc/passwd" 都是 read_file，但边界不同。
write_file "DOCS/note.md" 和 write_file "~/.ssh/config" 都是 write_file，但权限不同。
```

所以两道门不是重复，而是分工：

| 门 | 问题 | 类比 |
|---|---|---|
| 第一扇门 | 能不能使用这类工具？ | 有没有资格进入工地、使用施工工具？ |
| 第二扇门 | 这次参数是否越界？ | 是在指定区域施工，还是跑去拆隔壁楼？ |

### 精髓三：ToolSearch 是工具目录，不是智能搜索 Agent

Claw-Code 的 [ToolSearch](../projects/claw-code/tool-system.md#toolsearch延迟工具发现而不是智能搜索-agent) 解决的是工具可见性问题：

> **工具很多，但不一定要一次性全部暴露给模型。**

它把工具分成：

```text
always-visible tools
  bash / read_file / write_file / edit_file / glob_search / grep_search

deferred tools
  其他专用工具，需要时通过 ToolSearch 查询
```

搜索逻辑在 [search_tool_specs](../../claw-code/rust/crates/tools/src/lib.rs)，本质是代码里的关键词匹配和打分：

```text
工具名精确匹配：高分
工具名包含 query：中分
描述 / haystack 包含 query：低分
+term：required term
select:：直接选择工具名
canonical token：归一化工具名和 query
```

这点非常关键：

> **ToolSearch 不是“智能 agent 搜索工具”，而是一个内置工具目录检索器。它像工具箱旁边的一本目录：常用扳手、螺丝刀直接放桌上；不常用的专用工具放柜子里；需要的时候先查目录，再拿出来用。**

这说明工具系统设计不只是“工具越多越好”，还要管理模型每一轮看到的工具表规模。

## OpenHands：分层式平台工具治理

OpenHands 的 Agent Loop 笔记见 [OpenHands Agent Loop](../projects/openhands/agent-loop.md)。当前理解是：OpenHands 更偏平台化 SWE Agent，不把工具系统全部塞进一个本地 tools 大文件里，而是拆成控制面 / 执行面：

```text
App Server / Agent Canvas / conversation / sandbox / event / automation
  -> 控制面：创建会话、管理 workspace/sandbox、转发消息、记录事件、展示 UI

Agent Server / software-agent-sdk / openhands-tools
  -> 执行面：运行 Conversation.run / Agent.step、执行工具、产生 ObservationEvent
```

它的工具抽象更接近：

```text
ActionEvent
  -> 工具 / runtime / workspace 执行
    -> ObservationEvent
      -> 下一轮 Agent.step
```

和 Claw-Code 对比：

| 维度 | Claw-Code | OpenHands |
|---|---|---|
| 形态 | 本地 CLI 工具中枢 | 平台控制面 / 执行面分离 |
| 工具执行位置 | 本地 runtime / tools crate | Agent Server / SDK / tools package / sandbox |
| 事件模型 | tool_use / tool_result 主线 | ActionEvent / ObservationEvent 平台事件流 |
| 优势 | 主线短、调试直观 | 多 backend、远程运行、团队共享、事件追踪 |
| 代价 | 中心模块变重 | 调试链路更长、跨 repo / service 理解成本高 |

可以概括为：

> **Claw-Code 像本地万能工具箱；OpenHands 像远程工程平台。**

## DeerFlow：LangGraph / middleware 化的工具治理

DeerFlow 的 Agent Loop 笔记见 [DeerFlow Agent Loop](../projects/deer-flow/agent-loop.md)。它的工具系统不像 Claw-Code 那样围绕一个本地 `run_turn + tools.rs` 大中枢展开，而是嵌在：

```text
Gateway run lifecycle
LangGraph agent runtime
middleware chain
sandbox / checkpoint / stream / cancel / clarification
```

里治理。

和 Claw-Code 对比：

| 维度 | Claw-Code | DeerFlow |
|---|---|---|
| Loop 位置 | 本地 `ConversationRuntime::run_turn` | Gateway worker + LangGraph runtime |
| 工具循环 | 手写提取 ToolUse、执行、回写 | 主要交给 LangGraph / LangChain agent runtime |
| 横切能力 | hook / permission / compaction 等内联插入主线 | middleware、RunManager、checkpointer、StreamBridge 等分层处理 |
| 适合场景 | 本地 Coding CLI | 长任务、图式编排、run 生命周期治理 |

可以概括为：

> **Claw-Code 把工具系统写成可顺代码读下来的本地能力中枢；DeerFlow 把工具调用放进 run lifecycle 和 middleware 体系里治理。**

## OpenClaw / Hermes：后续工具系统比较的问题清单

OpenClaw 和 Hermes 的 Agent Loop 笔记已经完成，但工具系统还需要后续单独研读。

从已有 Agent Loop 讨论可以先提出问题清单。

### OpenClaw 后续应看什么？

参考 [OpenClaw Agent Loop](../projects/openclaw/agent-loop.md)，OpenClaw 的工具系统应重点核验：

```text
AgentTool 类型如何定义？
工具如何注册到 AgentLoopConfig？
executeToolCalls 如何处理并发、错误和结果回写？
AgentSession hook 如何包裹工具调用？
steer / followUp 与工具结果的消息协议如何保持一致？
工具权限、审批、队列、节点能力路由在哪里做？
```

它可能更像：

> **事件驱动 session runtime 里的工具系统。**

### Hermes 后续应看什么？

参考 [Hermes Agent Loop](../projects/hermes-agent/agent-loop.md)，Hermes 的工具系统应重点核验：

```text
toolsets 如何注册？
tool_search 如何发现工具？
tool_executor.py 如何串行 / 并发执行？
interrupt / steer 如何影响工具 worker？
工具 guardrail 如何做？
长期记忆、todo、skill_manage 这些个人能力如何工具化？
provider fallback 与工具协议差异如何兼容？
```

它可能更像：

> **长期个人 Agent 的工具执行与记忆 / 技能能力融合层。**

## 横向分类法

第一轮可以把 Tool System 分成几类：

### 集中式本地工具中枢

代表：Claw-Code。

```text
工具定义、schema、权限、搜索、执行分发集中在本地工具模块；Agent Loop 内联串起 hook / permission / execute / result。
```

优势是直观、可控、本地 CLI 体验好；代价是工具越多，中心模块越重。

### 分层式平台工具治理

代表：OpenHands。

```text
控制面管理 conversation / sandbox / event / UI；执行面通过 Agent Server / SDK / tools package 跑工具，并产生 Action / Observation 事件。
```

优势是远程运行、多 backend、团队协作、自动化和事件追踪；代价是链路长。

### Workflow / middleware 化工具治理

代表：DeerFlow。

```text
工具调用被吸收到 LangGraph agent runtime，横切能力通过 middleware、checkpoint、run lifecycle、sandbox 等机制治理。
```

优势是长任务治理和流程编排；代价是最小 tool loop 不像本地 CLI 那样一眼可见。

### 事件驱动 session 工具系统

代表候选：OpenClaw。

```text
工具调用被 AgentSession / Agent / runLoop 的事件状态机包裹，需要结合 steer / followUp 队列理解。
```

后续需要源码核验。

### 长期个人 Agent 工具系统

代表候选：Hermes Agent。

```text
工具系统和 memory、skill、todo、interrupt、steer、provider fallback 深度交织。
```

后续需要源码核验。

## 最浓缩版

如果只记一个结论：

> **Tool System 是 Agent 的能力总线；不同 Harness 的差异，不只是有哪些工具，而是工具定义、可见性、权限、执行、结果回写和横切治理被放在什么架构位置。**

如果只记 Claw-Code：

> **Claw-Code 是集中式工具中枢：直接、内联、可控；ToolSearch 则通过“常用工具默认可见 + 专用工具延迟发现”控制工具表规模。**

如果和其他项目比：

```text
Claw-Code：本地万能工具箱 / 集中式工具中枢
OpenHands：远程工程平台 / 控制面与执行面分离
DeerFlow：工作流工厂 / LangGraph + middleware 治理
OpenClaw：聊天工作室 / 事件驱动 session 工具系统
Hermes：长期私人助理 / 记忆与技能融合的工具系统
```

## QA / 讨论记录

### Q: 为什么 Tool System 专题不继续叫 tool-calling？

> **状态**: draft
> **来源**: discussion

A: `tool-calling` 更像协议层术语，强调模型发起 tool call、Harness 返回 tool result；`tool-system` 范围更大，包含工具定义、注册、schema、权限、hook/middleware、sandbox、工具可见性、工具执行、结果回写、MCP/plugin/runtime 扩展、子 agent / task / worker 等高阶能力工具化。对于横向研究 Harness，`tool-system` 更能覆盖真实工程复杂度。

### Q: Claw-Code 的 ToolSearch 为什么是精髓？

> **状态**: draft
> **来源**: discussion / source-code

A: 因为它体现了工具系统的可见性管理：常用基础工具默认放在桌面上，专用工具放进 deferred 目录，需要时用 ToolSearch 做关键词检索。它不是智能搜索 Agent，而是内置工具目录。这个设计避免把所有工具一次性塞给模型，减少 prompt 负担和工具选择噪音。

### Q: 集中式工具中枢是缺点吗？

> **状态**: draft
> **来源**: discussion / source-code

A: 不是单纯缺点，而是一种本地 CLI 取舍。集中式工具中枢让 Claw-Code 的主线非常直观，本地调试和源码学习都方便；但随着工具数量增加，`mvp_tool_specs()`、执行分发、权限分类和工具搜索都会集中膨胀，长期维护压力上升。横向比较时应写成“直接可控但中心化变重”，而不是简单评价好坏。
