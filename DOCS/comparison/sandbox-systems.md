# Sandbox / Workspace 横向总结：从远程云工位到本地施工围栏

> **日期**: 2026-07-08 | **状态**: draft | **涉及项目**: DeerFlow / OpenHands / Claw-Code / OpenClaw / Hermes Agent

## 相关文档

- 项目笔记：
  - [DeerFlow Sandbox / Workspace](../projects/deer-flow/sandbox-workspace.md)
  - [OpenHands Sandbox / Workspace](../projects/openhands/sandbox-workspace.md)
  - [Claw-Code Sandbox / Workspace](../projects/claw-code/sandbox-workspace.md)
  - [OpenClaw Sandbox / Workspace](../projects/openclaw/sandbox-workspace.md)
  - [Hermes Agent Sandbox / Workspace](../projects/hermes-agent/sandbox-workspace.md)
- 横向专题：
  - [Permission / Security 横向总结](permission-security.md)
  - [Tool System 横向总结](tool-system.md)
  - [Context Management 横向总结](context-management.md)
  - [生产部署取舍对比](production-deployment-tradeoffs.md)
- 横向 QA：[qa.md](qa.md)

## 核心结论

五个主要 Harness 都有 sandbox / workspace / execution boundary 相关设计，但它们说的 “sandbox” 不是同一个东西。

```text
OpenHands：平台给 agent 分配远程开发工位
DeerFlow：workflow run 在受控生产线上执行
Claw-Code：本地 CLI 给 agent 拉一圈施工围栏
OpenClaw：每个聊天 session 绑定一个可切换的执行隔间
Hermes Agent：长期个人助理有一个可配置的工具工作台
```

所以横向比较 sandbox 时，不能只问“有没有 Docker”，而要问：

1. **模型动作在哪里执行？**
2. **文件读写边界在哪里？**
3. **bash / terminal 有没有隔离？**
4. **权限审批在工具前、workflow middleware 中，还是平台事件层？**
5. **长任务、多任务、子 agent 如何避免互相踩？**

最浓缩的判断是：

> **五个 Harness 的 sandbox 差异，本质上是它们把“模型动作的外部世界”放在了不同地方：OpenHands 放在平台云工位里，DeerFlow 放在 workflow 生产线里，Claw-Code 放在本地项目围栏里，OpenClaw 放在 session 执行隔间里，Hermes 放在长期个人助理的可配置工作台里。**

## 总览表

| 项目 | sandbox / workspace 精髓 | 隔离强度 | 比喻 |
|---|---|---:|---|
| OpenHands | 平台化远程开发环境，ActionEvent 进入 sandbox，ObservationEvent 回流 | 强 | **远程开发园区 / 云端工位** |
| DeerFlow | workflow run 的受控执行环境，middleware / RunManager / sandbox 一起治理 | 中强 | **工作流工厂的安全生产线** |
| Claw-Code | 本地 CLI workspace 边界 + 权限审批 + 可选 sandbox wrapper | 中 | **本地施工围栏** |
| OpenClaw | session-level SandboxContext，工具菜单和执行方式随 sandbox 改写 | 中强 | **多端协作工作室的独立隔间** |
| Hermes Agent | 可配置 Terminal Environment，默认 local，可切 Docker / SSH / Modal / Daytona | 可变 | **长期个人助理的工具工作台** |

这里的“隔离强度”不是安全审计结论，而是第一轮架构研读中的相对判断：OpenHands 更偏平台强隔离，Claw-Code 更偏本地权限围栏，Hermes 隔离强度取决于当前 Terminal Environment backend。

## OpenHands：远程开发园区 / 云端工位

OpenHands 的 sandbox 最像一个 **远程开发园区**。

用户不是把 agent 放在自己电脑上随便跑，而是通过平台控制面创建 conversation / session，然后 agent 在后端 sandbox 里执行动作。它的核心不是“本地命令前加一层确认”，而是：

```text
模型动作
  -> ActionEvent
  -> sandbox 执行
  -> ObservationEvent
  -> 回到上下文
```

比喻：

> **OpenHands 像一个远程开发园区。**
> 每个 agent 被分配到一个云端工位，工位里有 terminal、file editor、浏览器或其他工具。模型不能直接伸手到用户电脑上操作，而是通过园区的动作系统提交工单，园区执行后把观察结果反馈回来。

它的 sandbox 重点是：

- 平台化 workspace；
- action / observation 事件流；
- session / conversation 管理；
- 远程执行环境；
- 更适合多用户、长任务、SWE Agent 平台。

所以 OpenHands 的安全感来自：

```text
动作被平台事件化 + 执行环境远程隔离 + 结果可观测
```

这也解释了为什么 OpenHands 需要同时看控制面仓库和执行面仓库：控制面负责 conversation / sandbox / automation 等平台能力，执行面负责 SDK `Conversation` / `Agent` loop 与 terminal / file editor / task tracker 等工具能力，详见 [OpenHands Sandbox / Workspace](../projects/openhands/sandbox-workspace.md)。

## DeerFlow：工作流工厂的安全生产线

DeerFlow 的 sandbox 更像 **工作流工厂里的受控工位**。

它不是 Claude Code 那种本地 CLI coding agent，也不是 OpenHands 那种完整远程开发平台。DeerFlow 的中心是 workflow / run lifecycle。

比喻：

> **DeerFlow 像一个工作流工厂。**
> 每个 run 是一张生产订单，LangGraph 是生产线，middleware 是工位规则，sandbox 是某些工序的安全操作台。任务不是随便在本地乱跑，而是在 run lifecycle 和 middleware chain 里被调度、检查、限制和记录。

它的 sandbox 重点是：

- run lifecycle；
- middleware pipeline；
- workflow state；
- tool execution governance；
- sandbox middleware / execution environment；
- loop detection / token budget / guardrails。

所以 DeerFlow 关心的是：

```text
这个 workflow run 会不会越界？
这个工具调用会不会破坏流程？
这个 agent 是否陷入循环？
这个 run 的状态是否可恢复？
```

它不像 OpenHands 那样把所有东西都产品化成远程 IDE 工位；它更像在 workflow 框架内部给危险步骤设置安全工位，详见 [DeerFlow Sandbox / Workspace](../projects/deer-flow/sandbox-workspace.md)。

## Claw-Code：本地施工围栏

Claw-Code 的 sandbox 最像 **本地施工围栏**。

它是 Claude Code-like 本地 CLI。agent 的动作主要发生在用户本地项目目录里。它的核心问题是：

```text
既然 agent 在我本地跑，怎么防止它乱改、乱删、乱执行？
```

比喻：

> **Claw-Code 像一个本地老师傅进场施工。**
> 项目目录是一块工地，workspace boundary 是围栏，权限系统是施工许可，bash validation 是安全员，optional sandbox wrapper 是临时加装的防护棚。它不是云端园区，而是在本地工地上尽量立规矩。

它的 sandbox / workspace 重点是：

- 本地 workspace 边界；
- WorkspaceWrite 类权限；
- bash command validation；
- permission / prompter；
- hook 机制；
- 可选 sandbox wrapper；
- 本地项目上下文。

所以 Claw-Code 的隔离不是平台级强隔离，而是：

```text
本地执行 + 明确 workspace + 工具权限 + 危险动作审批
```

它的优点是轻、直接、贴近开发者本地工作流；缺点是默认仍然强依赖本机信任边界，详见 [Claw-Code Sandbox / Workspace](../projects/claw-code/sandbox-workspace.md)。

## OpenClaw：多端协作工作室的独立隔间

OpenClaw 的 sandbox 像 **一个聊天工作室里的独立执行隔间**。

它比 Claw-Code 更产品化、更 session 化。Claw-Code 更像本地 CLI 工具；OpenClaw 更像一个支持实时聊天、session、steer / follow-up、多端交互的 agent runtime。

比喻：

> **OpenClaw 像一个多端协作工作室。**
> 每个 AgentSession 进来时，会被安排到一个执行隔间。这个隔间可以是本地、Docker、SSH 等不同后端。更关键的是，用户看到的工具菜单也会根据这个隔间改写：在什么环境里工作，就给模型什么样的工具入口。

它的 sandbox 重点是：

- session-level SandboxContext；
- Docker / SSH / local 之类 backend；
- fsBridge / terminalBridge；
- 工具菜单按 sandbox 能力改写；
- before_tool_call approval；
- 实时 follow-up / steer；
- 多端产品形态。

OpenClaw 的核心不是单纯“命令怎么跑”，而是：

```text
当前 session 绑定了什么执行环境？
这个环境支持什么工具？
模型看到的工具说明是否和真实执行环境一致？
用户能不能中途插话或审批？
```

所以它比 Claw-Code 更像一个产品化 agent studio，详见 [OpenClaw Sandbox / Workspace](../projects/openclaw/sandbox-workspace.md)。

## Hermes Agent：长期个人助理的工具工作台

Hermes 的 sandbox 最像 **长期个人助理的工具工作台**。

它不是默认强隔离平台。Hermes 默认 backend 可以是 local，也就是直接在宿主环境执行。但它提供了可配置 Terminal Environment，可以切换到 Docker、Singularity、Modal、Daytona、SSH 等环境。

比喻：

> **Hermes 像一个长期私人助理。**
> 默认它就在你的书房工作，直接用你的电脑和工具；如果任务危险或需要外部环境，可以让它去 Docker 房间、SSH 远程机器、Modal 云环境或 Daytona workspace。它的重点不是每次都关进保险箱，而是长期协作中选择合适的工作台，并防止助理拿错工具、反复失败或污染记忆。

Hermes 的 sandbox / workspace 重点是：

- Terminal Environment 抽象；
- local / Docker / Singularity / Modal / Daytona / SSH backend；
- bash 每次 fresh process，但维护 cwd / env snapshot；
- file tools 跟随 terminal cwd / task cwd；
- `execute_code` 有单独 mini sandbox；
- dangerous command approval；
- ACP edit approval；
- memory / skills hygiene；
- tool guardrails。

所以 Hermes 的安全边界更分散：

```text
工具可见性
命令审批
terminal backend
file safety
plugin hook
guardrail
memory hygiene
session persistence
```

它不像 OpenHands 那样所有动作都平台事件化，也不像 DeerFlow 那样以 workflow run 为中心。它的中心是：

```text
长期个人 agent 如何持续、安全、可恢复地和用户协作？
```

详见 [Hermes Agent Sandbox / Workspace](../projects/hermes-agent/sandbox-workspace.md)。

## 横向分类：五种 sandbox 思路

| 类型 | 项目 | 核心问题 |
|---|---|---|
| 平台工位型 | OpenHands | 如何给 SWE Agent 一个远程、可观测、可管理的开发工位？ |
| 工作流工厂型 | DeerFlow | 如何让 workflow run 在受控流程中执行工具？ |
| 本地围栏型 | Claw-Code | 如何让本地 coding agent 在项目目录内安全施工？ |
| Session 隔间型 | OpenClaw | 如何让每个聊天 session 绑定正确的执行环境和工具菜单？ |
| 个人助理工作台型 | Hermes Agent | 如何让长期个人 agent 在多 backend、多工具、多记忆中安全协作？ |

## 关键比较维度

### 维度一：默认执行在哪里？

| 项目 | 默认执行位置 |
|---|---|
| OpenHands | 远程 / 平台 sandbox |
| DeerFlow | workflow runtime / sandbox middleware 管理的执行环境 |
| Claw-Code | 用户本地项目目录 |
| OpenClaw | session 绑定的 sandbox backend |
| Hermes Agent | 默认 local，可配置到 Docker / SSH / Modal 等 |

结论：

```text
OpenHands 最平台化
Claw-Code 最本地化
Hermes 最可配置
OpenClaw 最 session 化
DeerFlow 最 workflow 化
```

### 维度二：workspace 是什么？

| 项目 | workspace 含义 |
|---|---|
| OpenHands | 远程开发工作区 |
| DeerFlow | workflow run 的执行上下文 / sandbox workspace |
| Claw-Code | 本地项目目录边界 |
| OpenClaw | AgentSession 的 sandbox workspace |
| Hermes Agent | terminal cwd / task cwd / session cwd 共同决定的工作目录 |

结论：

```text
workspace 不只是一个路径。
在不同 Harness 中，它可能是：
- 远程工位
- workflow run context
- 本地项目根目录
- session sandbox
- terminal backend 的当前目录
```

### 维度三：bash / terminal 是否强隔离？

| 项目 | bash / terminal 隔离 |
|---|---|
| OpenHands | 通常在远程 sandbox 中执行 |
| DeerFlow | 受 workflow sandbox / middleware 控制 |
| Claw-Code | 本地执行为主，可叠加权限和可选 sandbox |
| OpenClaw | 由 session sandbox backend 决定 |
| Hermes Agent | backend 决定；默认 local，Docker / SSH 等可选 |

结论：

```text
不能只问“有没有 bash 工具”。
要问 bash 落在哪里：
- 本地宿主机？
- Docker？
- SSH 远端？
- 平台 sandbox？
- workflow runtime？
```

### 维度四：权限系统和 sandbox 的关系

| 项目 | 权限与 sandbox 关系 |
|---|---|
| OpenHands | 动作进入平台事件层后，由 security / confirmation 策略处理 |
| DeerFlow | middleware / guardrail / run lifecycle 管工具执行 |
| Claw-Code | PreToolUse / PermissionPolicy / Prompter 类机制守住本地工具 |
| OpenClaw | tool policy + before_tool_call + sandbox-aware tool menu |
| Hermes Agent | toolsets / approval / plugin hook / guardrail / memory hygiene 分层治理 |

结论：

```text
sandbox 负责“在哪里执行”
permission 负责“能不能执行”
guardrail 负责“执行中是否失控”
它们经常交织，但不是同一个东西。
```

## 最浓缩的五句比喻

1. **OpenHands：远程开发园区**
   Agent 不在你电脑上乱跑，而是在平台分配的云端工位里工作。

2. **DeerFlow：工作流工厂生产线**
   每个 run 是生产订单，middleware 是工位规程，sandbox 是危险工序的安全操作台。

3. **Claw-Code：本地施工围栏**
   Agent 是本地老师傅，workspace 是施工范围，权限系统是动火证和施工许可。

4. **OpenClaw：多端协作工作室隔间**
   每个 session 有自己的执行隔间，工具菜单会根据隔间能力变化。

5. **Hermes Agent：长期个人助理工作台**
   助理默认在你书房工作，也可以被派到 Docker、SSH、云环境；重点是长期协作中的工具、记忆和风险治理。

## QA / 讨论记录

### Q: 五个主要 Harness 的 sandbox 部分都讨论过了吗？

> **状态**: verified
> **来源**: source-code / discussion

A: 是。DeerFlow、OpenHands、Claw-Code、OpenClaw 和 Hermes Agent 都已经完成项目级 [Sandbox / Workspace](../projects/) 研读笔记，并在本文汇总为横向比较。learn-claude-code 是教学项目，不纳入五个主要生产 / 实现型 Harness 的 sandbox 主线比较。

### Q: 为什么不能只用“有没有 Docker”判断 sandbox 能力？

> **状态**: draft
> **来源**: discussion / source-code

A: 因为 Agent Harness 的 sandbox 不是单一容器开关，而是执行位置、workspace 边界、工具权限、事件观测、长任务状态、子 agent 隔离和恢复机制的组合。OpenHands 更像平台云工位，DeerFlow 更像 workflow 生产线，Claw-Code 更像本地施工围栏，OpenClaw 更像 session 隔间，Hermes 更像可配置个人助理工作台；它们可以都涉及 Docker，但架构含义并不相同。

### Q: sandbox、permission 和 guardrail 有什么区别？

> **状态**: draft
> **来源**: discussion / source-code

A: sandbox 主要回答“动作在哪里执行、环境如何隔离”；permission 主要回答“这次动作能不能执行、是否要用户批准”；guardrail 主要回答“执行过程中是否反复失败、越界、无进展或破坏 run 健康”。真实 Harness 往往把三者交织在一起，但分析时要拆开看。
