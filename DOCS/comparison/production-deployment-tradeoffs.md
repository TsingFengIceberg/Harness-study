# Agent Harness 生产部署取舍：Agent Loop 与 Tool System 的运行优缺点

> **日期**: 2026-07-03 | **状态**: draft | **涉及项目**: Claw-Code / OpenClaw / Hermes Agent / DeerFlow / OpenHands

## 相关文档

- Agent Loop 横向总结：[agent-loop.md](agent-loop.md)
- Tool System 横向总结：[tool-system.md](tool-system.md)
- 项目定位分析：[project-positioning.md](project-positioning.md)
- 横向 QA：[qa.md](qa.md)
- 项目笔记：
  - [Claw-Code Tool System](../projects/claw-code/tool-system.md)
  - [OpenClaw Tool System](../projects/openclaw/tool-system.md)
  - [Hermes Agent Tool System](../projects/hermes-agent/tool-system.md)
  - [DeerFlow Tool System](../projects/deer-flow/tool-system.md)
  - [OpenHands Agent Loop](../projects/openhands/agent-loop.md)

## 本文范围

本文不讨论“源码好不好读”或“文档学习难不难”，而是从实际运行、生产部署、长期运维、资源成本、安全隔离、多用户、多端交互和长任务可靠性的角度，比较不同 Agent Loop / Tool System 设计的优缺点。

一句话总览：

| 项目 | 架构气质 | 最适合的生产场景 | 最大优势 | 最大代价 |
|---|---|---|---|---|
| Claw-Code | 本地集中式 CLI runtime | 单人本地 coding agent | 轻量、低基础设施、反馈直接 | 不天然适合多用户 / 多端 / 长任务平台化 |
| OpenClaw | 事件化 Agent session runtime | 多端聊天式 Agent 产品 | 实时交互、事件流、channel / approval / policy 强 | 状态、事件、队列、channel 一致性复杂 |
| Hermes Agent | 长期个人 Agent 厚执行器 | 长期私人助理 / 个人自动化 | 记忆、技能、steer、长期上下文强 | 长期状态、隐私、记忆污染、迁移和恢复压力大 |
| DeerFlow | LangGraph 标准生产线 + middleware | Web / Gateway / 长任务 run | 标准化、checkpoint、run 生命周期、中间件治理强 | 框架依赖、运行链路重、middleware 顺序和状态复杂 |
| OpenHands | 平台控制面 + 执行面 | 团队 / 远程 SWE Agent 平台 | 多用户、workspace、sandbox、事件、自动化平台能力强 | 部署成本最高、服务边界多、运维复杂 |

## Claw-Code：本地集中式 runtime

Claw-Code 更像一个本地进程里的 coding agent：用户输入、模型调用、工具执行、结果回写都围绕本地 runtime 展开。

### 生产运行优势

| 优势 | 说明 |
|---|---|
| 部署成本低 | 适合安装一个 CLI / 二进制，在本地项目目录配置 API key 后直接运行；不需要 Gateway、数据库、远程 sandbox、队列或多端 channel。 |
| 工具执行路径短 | 本地 `read_file` / `bash` / `edit` 等工具调用少了远程 worker、事件总线、sandbox provisioner 等服务跳转，反馈直接。 |
| 本地文件 / shell 体验自然 | Coding Agent 最常用的读写文件、跑测试、git diff、执行命令等操作天然贴近开发者机器。 |
| 基础设施风险小 | 没有多服务协调，少了跨服务网络、队列、远程 workspace 等故障点。 |

### 生产运行劣势

| 劣势 | 说明 |
|---|---|
| 不天然适合多用户 SaaS | 多用户 workspace 隔离、shell 权限、工具审计、并发调度、后台恢复都需要额外平台层。 |
| 长任务恢复能力弱一些 | 本地进程崩溃、终端关闭、机器休眠都会影响任务连续性；可做 session 持久化，但不是架构中心。 |
| 多端交互不自然 | Web / IM / 手机 / 审批流 / 后台任务继续跑等能力需要外部包装。 |
| 安全边界依赖本机环境 | 本地执行能力强，但如果要交给不可信用户或云端多租户，必须额外设计隔离层。 |

### 适合与不适合

适合：

```text
个人本地 coding
开发者 CLI 助手
低基础设施成本的本地自动化
```

不适合直接承担：

```text
大型多租户 Agent SaaS
多端实时产品
需要强隔离远程 sandbox 的团队平台
```

## OpenClaw：事件化 Agent session runtime

OpenClaw 面向多端 Agent 产品，核心不是“单轮函数调用”，而是 AgentSession、Agent、runLoop、steer / followUp、tool_execution events、policy pipeline 和 channel integration。

### 生产运行优势

| 优势 | 说明 |
|---|---|
| 适合多端实时交互 | `tool_execution_start/update/end`、message events、session state 适合 Web 前端和 IM channel 展示实时进度。 |
| 运行中交互语义清楚 | `steer`、`followUp`、interrupt、approval 等语义适合用户在 Agent 工作中途补充方向或审批。 |
| 产品上下文驱动工具治理 | 工具面可按 run、session、channel、sender、sandbox、provider、policy、group 等上下文动态装配。 |
| 事件可观测性强 | 工具执行生命周期和消息生命周期分离，方便 UI、diagnostics、audit、approval 等消费不同事件。 |

### 生产运行劣势

| 劣势 | 说明 |
|---|---|
| 事件一致性复杂 | tool_execution 事件、message 事件、session 持久化、channel 更新之间可能出现顺序、重复、丢失、回放问题。 |
| 多 channel 边界条件多 | Web、Telegram、Feishu、Slack 等 channel 的消息长度、编辑能力、速率限制、附件能力都不同。 |
| 策略系统配置风险高 | policy / plugin / approval / channel routing 越强，配置错误或升级兼容问题越可能影响工具可用性和安全边界。 |
| 状态队列需要精细治理 | steer / followUp / interrupt / approval 在并发和边界时机下需要稳定的状态机。 |

### 适合与不适合

适合：

```text
多端聊天式 Agent 产品
需要实时进度展示的工具调用
需要 channel / approval / policy 的产品 runtime
```

不适合：

```text
极简本地 CLI
不想维护事件一致性和多 channel 状态的轻量部署
```

## Hermes Agent：长期个人 Agent 厚执行器

Hermes 更像长期私人助理：memory、skills、session history、steer、provider fallback、tool guardrail、SessionDB 都围绕同一个长期个人 Agent 运转。

### 生产运行优势

| 优势 | 说明 |
|---|---|
| 长期连续性强 | 适合同一个 Agent 长期服务同一个人，记住偏好、沉淀经验、复用历史、形成 skills。 |
| 真实环境容错强 | provider fallback、empty response recovery、invalid tool args recovery、guardrail、checkpoint、result budget、SessionDB flush 等机制对抗模型和工具的不稳定性。 |
| 个人自动化能力强 | memory、todo、session_search、skills、file、terminal、browser、MCP、plugin、delegate_task 等能力能融合成个人工作台。 |
| 中途引导友好 | interrupt / steer 适合用户在长期任务中不断调整方向，而不是只能等待任务结束。 |

### 生产运行劣势

| 劣势 | 说明 |
|---|---|
| 长期记忆治理压力大 | 记错、过期偏好、敏感信息、删除权、身份隔离、记忆污染等都是生产问题。 |
| 状态迁移和备份复杂 | session history、memory、skills、todo、artifacts、profile config、checkpoint、plugin state 都需要升级、备份、恢复和迁移策略。 |
| 厚执行器增加延迟和故障点 | middleware、plugin、guardrail、checkpoint、budget、persistence、steer 等每个环节都可能增加调用开销或引入长尾 bug。 |
| 多租户隐私边界更敏感 | 个人 Agent 越懂用户，越需要严格的数据隔离、访问控制和隐私治理。 |

### 适合与不适合

适合：

```text
长期私人助理
个人知识 / 任务 / 自动化工作台
跨会话协作与技能沉淀
```

不适合：

```text
只跑一次性短任务
没有准备好处理记忆治理和隐私合规的多用户部署
```

## DeerFlow：LangGraph 标准生产线 + middleware

DeerFlow 的标准化首先来自使用 LangGraph / LangChain agent runtime；DeerFlow 自己又把 run、thread、sandbox、stream、middleware、checkpoint 组织成生产线式架构。

### 生产运行优势

| 优势 | 说明 |
|---|---|
| 适合 run 生命周期管理 | Gateway run lifecycle、RunManager、status、cancel / rollback、StreamBridge 适合 Web / Gateway 长任务服务。 |
| 中间件化便于治理演进 | 输入清洗、工具输出预算、sandbox、tool error、guardrail、loop detection、token budget、clarification、deferred tool 等能力可以作为 middleware 卡口插入。 |
| 框架生态提供标准能力 | BaseTool、ToolMessage、Command、AgentMiddleware、state schema、checkpoint、stream mode 等不必完全自研。 |
| 适合任务型 Agent 服务 | 用户提交复杂任务、后台运行、前端看进度、必要时澄清、支持取消 / 回滚、结果归档。 |
| sandbox 与状态融合 | 工具通过 Runtime / ThreadState 接入 thread-scoped user data、sandbox provider、virtual path 和路径校验。 |

### 生产运行劣势

| 劣势 | 说明 |
|---|---|
| 框架依赖强 | LangGraph / LangChain 的 ToolNode、middleware、state、checkpoint 行为变化会影响系统运行语义。 |
| 运行链路重于本地 CLI | Gateway、frontend、nginx、LangGraph runtime、sandbox、checkpoint、StreamBridge 等组件都要运维。 |
| middleware 顺序敏感 | InputSanitization、Sandbox、ToolErrorHandling、DeferredToolFilter、Clarification 等顺序错误会导致治理失效。 |
| 故障定位分散 | 问题可能发生在框架、middleware、tool、sandbox、run manager、stream bridge 等任一层。 |

### 适合与不适合

适合：

```text
长任务 Agent 工作流服务
Web / Gateway 任务运行平台
需要 checkpoint / cancel / stream / middleware 治理的任务型 Agent
```

不适合：

```text
极简本地 CLI
不想绑定 LangGraph 框架或维护中间件组合复杂度的轻量部署
```

## OpenHands：平台控制面 + 执行面

OpenHands 更像团队级远程 SWE Agent 平台，核心是 App Server / Agent Canvas / Sandbox / Agent Server / SDK / tools 的控制面与执行面分离。

### 生产运行优势

| 优势 | 说明 |
|---|---|
| 最适合多人 / 团队 / SaaS 化 | 多用户、多 workspace、远程 sandbox、团队协作、任务自动化、Web UI 和事件历史都是平台原生需求。 |
| 安全隔离和资源管理更自然 | workspace、sandbox、secret 注入、任务资源回收、远程执行边界比本地 CLI 更适合云端部署。 |
| 自动化和可观测性强 | 事件记录、状态面板、后台运行、任务重试、结果归档、多人查看都更自然。 |
| 执行面可独立演进 | Agent Server / SDK / tools 可以与 App Server 控制面分离，适合扩展不同 backend。 |

### 生产运行劣势

| 劣势 | 说明 |
|---|---|
| 部署成本最高 | App Server、Agent Server、sandbox runtime、数据库 / event store、前端、认证、workspace storage、队列等都需要运维。 |
| 跨服务故障点多 | frontend、app server、sandbox service、agent server、tool execution、event callback、storage、UI refresh 任一层都可能卡住任务。 |
| 资源消耗高 | 远程 sandbox、workspace、agent server 会消耗 CPU、内存、存储、网络和容器启动成本。 |
| 对轻量个人场景过重 | 如果只是个人本地 coding，平台控制面和远程执行面可能显著过度设计。 |

### 适合与不适合

适合：

```text
团队级 SWE Agent 平台
远程 workspace / sandbox 托管
自动化处理 issue / PR / coding task
```

不适合：

```text
个人轻量 CLI
低成本单机部署
不想运维平台服务的场景
```

## 按生产目标重新分类

| 生产目标 | 更匹配的项目 | 原因 |
|---|---|---|
| 本地个人 coding 工具 | Claw-Code | 轻、直接、本地文件和 shell 自然、基础设施少。 |
| 多端聊天式 Agent 产品 | OpenClaw | AgentSession、事件流、steer / followUp、channel routing、approval / policy。 |
| 长期私人助理 | Hermes Agent | memory、skills、session_search、长期状态、个人偏好和中途 steer。 |
| 长任务 / 工作流式 Agent 服务 | DeerFlow | LangGraph、run lifecycle、middleware、checkpoint、stream、cancel / rollback。 |
| 团队级 SWE Agent 平台 | OpenHands | workspace、sandbox、event platform、Agent Server、多用户、远程执行、自动化。 |

## 关键生产维度对比

### 部署复杂度

从轻到重可以粗略排序：

```text
Claw-Code
  最轻，本地 CLI。

Hermes Agent
  本地 / 个人服务可跑，但长期状态多。

OpenClaw
  多端产品 runtime，需要 session / channel / event / policy。

DeerFlow
  Gateway + LangGraph + sandbox + frontend + run lifecycle。

OpenHands
  平台级，控制面 + 执行面 + sandbox / workspace。
```

### 多用户 / 多租户能力

```text
Claw-Code：
  默认单用户本地。

Hermes Agent：
  偏个人长期 Agent，多用户隔离要小心。

OpenClaw：
  多端多会话产品，较适合多用户交互。

DeerFlow：
  Gateway / thread / run 架构适合服务化多用户任务。

OpenHands：
  平台化，多用户 / workspace / sandbox 最自然。
```

### 长任务可靠性

```text
Claw-Code：
  本地进程型，长任务依赖本地 session 和进程稳定性。

OpenClaw：
  session / event / runtime 支持运行中交互，但要处理事件一致性。

Hermes Agent：
  长期状态和 SessionDB 强，适合长期个人任务，但记忆 / 状态治理复杂。

DeerFlow：
  run / checkpoint / cancel / rollback 天然适合长任务。

OpenHands：
  平台级长任务能力强，但资源和运维成本高。
```

### 工具安全与权限治理

```text
Claw-Code：
  本地集中式权限门，适合本地明确边界。

OpenClaw：
  policy pipeline + approval + channel/context，非常适合产品级策略。

Hermes Agent：
  plugin / approval / checkpoint / guardrail / scope 分散在厚执行器，适合个人 Agent 防失控。

DeerFlow：
  middleware + sandbox + guardrail + token budget，适合工作流服务治理。

OpenHands：
  sandbox / workspace / secrets 平台边界最强，但安全面最大。
```

### 实时交互体验

```text
Claw-Code：
  本地终端交互直接，但多端能力弱。

OpenClaw：
  最适合实时聊天式交互，steer / followUp / channel / event 都是强项。

Hermes Agent：
  steer / interrupt 也强，但更偏个人长期助理。

DeerFlow：
  stream run 适合前端看任务进度，聊天产品感不如 OpenClaw 强。

OpenHands：
  Web 平台事件体验强，但更偏 workspace / SWE task，不一定是聊天 runtime 最灵活。
```

### 成本

```text
Claw-Code：
  基础设施成本最低。

Hermes Agent：
  基础设施可低，但长期存储 / 多 provider / 工具状态会增加管理成本。

OpenClaw：
  中等，取决于 channel、session、plugin、gateway。

DeerFlow：
  中高，Gateway / frontend / sandbox / checkpoint / LangGraph stack。

OpenHands：
  最高，平台和远程执行资源成本最大。
```

## 总结

如果只问“哪个设计最好”，答案并不固定。更准确的是：

```text
个人本地 coding：Claw-Code 最合理。
多端 Agent 产品：OpenClaw 更合理。
长期私人助理：Hermes Agent 更合理。
长任务工作流服务：DeerFlow 更合理。
团队级 SWE 平台：OpenHands 更合理。
```

Agent Loop 决定任务怎么开始、继续、中断、恢复、流式输出和结束；Tool System 决定工具怎么暴露、授权、执行、审计、回写和限制副作用。生产系统的稳定性，是这两者叠加出来的。

最浓缩的判断：

> **Claw-Code 赢在轻和本地直接；OpenClaw 赢在多端实时产品化；Hermes 赢在长期个人状态和记忆；DeerFlow 赢在标准化工作流 run 和 middleware 治理；OpenHands 赢在团队级远程 SWE 平台。它们的优缺点不是代码写法不同，而是生产部署目标不同。**
