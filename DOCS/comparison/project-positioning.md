# 项目定位与功能特色对比

> **日期**: 2026-06-30 | **状态**: draft | **来源**: 讨论整理 + Deep Research Base + 本地 workflow 核验补充
>
> 本文整理第一轮横向学习的“整体功能特色分析”：这些项目是否属于同一类 Agent Harness、各自代表哪条演化分支、哪些能力是共性基础设施、哪些能力是差异化强化点。本文仍是阶段性讨论结论，后续需要结合各项目纵向源码笔记继续核验。

## 核心结论

这些项目**都属于 Agent Harness 的大范畴，但不是同一类东西**。

它们共享同一个底层母题：

> 给 LLM 加上工具、上下文、状态、权限、执行环境和人机交互，让模型能在真实环境里持续完成任务。

但它们分别强化了 Harness 的不同层面：

- `learn-claude-code` 强化“最小 Agent Loop 如何逐层长成完整 Harness”
- `claude-code-complete-guide_v2` 提供 Claude Code-like Harness 的能力清单和学习参考
- `claw-code` 强化本地 Coding CLI 的 runtime、工具、权限、沙箱和交互体验
- `openclaw` 强化多端入口、多设备节点、队列、审批和控制面
- `openhands` 强化 SWE Agent 的 Server / Workspace / Sandbox / Canvas / Automation 平台化
- `deer-flow` 强化长周期任务的状态图、中间件、沙箱和流程治理
- `hermes-agent` 强化长期个人记忆、经验沉淀和私人助理式持续协作

因此，后续比较时不应问“谁替代谁”，而应问：

> **谁把 Agent Harness 的哪一层能力做成了架构核心？**

## 研究方法提醒：定位不是偏见

项目定位用于建立地图、比较维度和问题意识，但不能反过来成为阅读源码时的预设偏见。

多数 Agent Harness 在基础构件上大同小异，都会涉及：

- Agent loop
- 工具调用 / tool schema / tool result 回写
- Runtime / workspace / sandbox
- 权限、安全、审批
- 上下文压缩与记忆
- 状态持久化与事件流
- 子任务 / 子 Agent / 后台调度
- MCP / plugin / hook / skill 等扩展机制

差异通常不是“有没有”，而是：

- 谁把某个机制作为一等公民
- 谁做得更深、更稳、更产品化
- 谁在边界条件、错误恢复、状态持久化、权限约束和测试覆盖上更成熟

因此后续研读细节时，应先按同一技术维度做事实核验，再回到项目定位解释差异。文档里尽量写“该项目在某方向更突出 / 更中心”，避免写成“其他项目没有 / 不能做”，除非已有源码或官方文档证据。

## 演化树视角

```text
Agent Harness
├── Claude Code-like / Coding CLI 方向
│   ├── claude-code-complete-guide_v2  ← 能力清单 / 参考靶标
│   ├── learn-claude-code              ← 最小教学实现
│   └── Claw-Code                      ← 本地 CLI 工程实现
│
├── 多端控制面 / Gateway 方向
│   └── OpenClaw                       ← 多设备、多 IM、审批、队列、节点
│
├── 平台化 SWE Agent 方向
│   └── OpenHands                      ← Agent Server / Canvas / Automation / Workspace
│
├── 长周期任务编排方向
│   └── DeerFlow                       ← LangGraph / Middleware / Sandbox / Subagents
│
└── 记忆进化个人 Agent 方向
    └── Hermes Agent                   ← Memory / Skills / Personal Agent / Long-term assistant
```

这张图不是“能力高低排名”，而是研究入口图：不同项目处在 Harness 演化树的不同枝杈上。

## 总体定位表

| 对象 | 定位 | 核心问题 | 最值得学习的点 |
|---|---|---|---|
| [learn-claude-code](../../learn-claude-code/) | 教学型 / 原理型 Harness | Agent Harness 最小机制是什么？ | 从最小 loop 逐层叠加 tools、permission、todo、subagent、compact、cron、MCP |
| [claude-code-complete-guide_v2](../../claude-code-complete-guide_v2/) | Claude Code 架构学习参考 | 成熟 Claude Code-like 系统有哪些模块？ | QueryEngine、工具治理、权限、安全、上下文、多 Agent、Hooks / Skills / Plugins 的问题清单 |
| [claw-code](../../claw-code/) | Claude Code-like 本地 Coding CLI Harness | 本地代码 Agent 如何工程化？ | Rust runtime、工具面、权限、sandbox、session、MCP、CLI 交互 |
| [openclaw](../../openclaw/) | 多端 Gateway / Control Plane | Agent 如何接入多入口、多设备？ | Gateway、node registry、durable queues、device pairing、remote approval、plugins |
| [openhands](../../openhands/) | 平台化 SWE Agent Harness | Coding Agent 如何变成 Server / Canvas / Automation 平台？ | App Server、Agent Server、Workspace / Sandbox、event、automation、ACP / MCP backend |
| [deer-flow](../../deer-flow/) | 长周期通用任务 Harness | 复杂任务如何图状态化、可恢复、可治理？ | LangGraph、middleware chain、sandbox、summarization、subagents、long-horizon workflow |
| [hermes-agent](../../hermes-agent/) | 记忆进化型个人 Agent | Agent 如何长期陪伴用户并沉淀经验？ | 长期记忆、procedural memory、skills、自我改进、多通道私人助理 |

## Claude Code / Claude Code-like 是什么基准？

Claude Code-like Harness 不是“能聊天的 CLI”，而是一个面向软件工程任务的本地 Agent 外壳，通常包含：

1. 读取项目上下文
2. 维护多轮会话状态
3. 调用工具读写文件
4. 执行 bash / test / build
5. 搜索代码
6. 修改代码并展示 diff
7. 管理权限和用户确认
8. 压缩上下文
9. 支持项目记忆，如 `CLAUDE.md` / `AGENTS.md` / rules
10. 支持 hooks / skills / plugins / MCP
11. 支持子任务或子 Agent
12. 在 CLI / IDE 中提供交互界面

在本仓库中：

| 对象 | 和 Claude Code-like 的关系 |
|---|---|
| `claude-code-complete-guide_v2` | Claude Code-like 的完整能力清单 / 学习参考 |
| `learn-claude-code` | Claude Code-like 的最小教学拆解 |
| `claw-code` | Claude Code-like 的开源工程实现 / 重写路线 |
| `openclaw` | 从 Claude Code-like 能力外扩到多端控制面 |
| `openhands` | 从 Coding Agent 外扩到 SWE 平台控制面 |
| `deer-flow` | 不是 Claude Code-like，偏长周期通用任务 |
| `hermes-agent` | 不是 Claude Code-like，偏个人 Agent / 记忆进化 |

## learn-claude-code 与 claude-code-complete-guide_v2 的角色差异

### learn-claude-code：最小可运行解释器

`learn-claude-code` 的价值是回答：

> Agent Harness 的最小结构是什么？

它从最基础的 loop 开始：

```text
user input
  ↓
LLM
  ↓
tool_use?
  ↓
execute tool
  ↓
tool_result
  ↓
LLM again
```

然后逐步加入 tool schema、file edit、bash、permission、todo、subagent、context compact、task system、cron、agent teams、MCP 等机制。

它适合做所有复杂 Harness 的“最小解释器”：当复杂项目出现工具注册、上下文压缩、任务状态、队列、审批、沙箱或平台控制面时，可以回到它来理解这些机制是在最小 loop 外叠加了哪一层。

### claude-code-complete-guide_v2：完整能力清单 / 参考靶标

`claude-code-complete-guide_v2` 不是核心 Harness 实现，而是 Claude Code-like Harness 的学习参考。

它的价值是提供研究问题清单，例如：

- Claude Code-like 工具系统应该有哪些层？
- 权限系统如何分模式？
- Bash / file / search 工具如何治理？
- 上下文压缩有哪些层级？
- 多 Agent 如何隔离和路由？
- Hooks / Skills / Plugins 如何组织？
- MCP / LSP / OAuth 如何接入？
- CLI 与 IDE 如何桥接？

因此它适合辅助研究 `claw-code`、`openclaw`、`learn-claude-code`，但不作为源码级结论来源。

## Claw-Code 与 OpenClaw：都是 Claude Code 替代吗？

两者都和 Claude Code-like 相关，但替代的是不同层面。

| 维度 | Claw-Code | OpenClaw |
|---|---|---|
| 核心形态 | 本地 CLI Harness | 多端 Gateway / Control Plane |
| 重点 | 执行代码任务 | 接入入口、设备、消息、审批 |
| 用户交互 | 终端为主 | IM / Web / 设备节点为主 |
| 安全重点 | 本地命令、路径、权限 | 设备配对、通道鉴权、远程审批 |
| 类比 | 高性能电钻 | 智能家居中控 |
| 与 Claude Code 的关系 | 偏本地工具替代 | 偏入口 / 控制面外扩 |

Claw-Code 更像“数据面 / 执行面”：回答在本地代码库里，Agent 如何安全高效地读写代码和跑命令。

OpenClaw 更像“控制面 / 网关层”：回答如何从任何设备、任何 IM、任何入口把任务交给 Agent，并管理执行和审批。

## OpenHands 与 Claw-Code：为什么不重复？

两者都处理软件工程任务，但架构层级不同。

Claw-Code 的默认中心是：

```text
Developer terminal
        ↓
Claw CLI runtime
        ↓
local repo / shell / tools
```

OpenHands 的默认中心是：

```text
Web / Canvas / Automation / GitHub issue
          ↓
OpenHands App Server / Control Plane
          ↓
Agent Server / Workspace / Sandbox Backend
          ↓
repo task execution
```

| 维度 | Claw-Code / Claude Code-like CLI | OpenHands |
|---|---|---|
| 核心产品 | CLI | App Server / Canvas / Automation |
| 执行位置 | 本地为主 | local / Docker / remote / cloud backend |
| 用户 | 单个开发者 | 团队 / 平台 / 自动化任务 |
| 状态 | 本地 session 为主 | conversation / event / server state |
| 自动化 | 可脚本化、可外接 | 架构核心能力之一 |
| 扩展方向 | Claude Code parity | SWE Agent platform |
| 类比 | 开发者手里的工具 | 软件工程自动化工厂 |

OpenHands 的“团队 / 平台 / 自动化”不是因为模型更会写代码，而是因为它把 Coding Agent 放入 App Server、Workspace / Sandbox、Event、Automation、Web UI / Canvas、Agent Backend 管理组成的平台控制面中。

Claw-Code / Claude Code-like CLI 可以通过外部脚本和平台包装实现部分自动化，但这些不是其默认架构核心。

## DeerFlow 与 Hermes：为什么不是 Claude Code-like？

### DeerFlow：长周期任务编排

DeerFlow 的核心不是在本地 repo 中交互式改代码，而是复杂任务如何被拆成状态图，经过多轮工具调用、沙箱执行、中间件处理，最终完成长周期研究或生成任务。

它代表的是：

> **Graph-oriented long-horizon harness**

核心问题是：

> 如何让 Agent 在复杂、长时间、多步骤任务里不丢状态、不爆上下文、不失控？

### Hermes Agent：记忆进化型个人 Agent

Hermes 的核心不是本地 coding CLI，而是一个 Agent 如何长期陪伴用户，跨会话记忆、沉淀经验、扩展工具、接入不同交互渠道。

它代表的是：

> **Memory-evolving personal agent harness**

核心问题是：

> 如何让 Agent 在长期使用中越来越懂你、越来越会做你的事？

## Hermes 与 DeerFlow / OpenClaw 的差异

| 对比 | DeerFlow | Hermes Agent | OpenClaw |
|---|---|---|---|
| 核心定位 | 长周期任务编排 | 长期个人记忆与经验沉淀 | 多端入口与设备控制面 |
| 中心抽象 | Task / Workflow / State Graph | User / Memory / Skill / Personal Context | Channel / Node / Queue / Approval |
| 更像 | 项目经理 | 私人秘书 / 长期同事 | 总机 / 中控台 |
| 强项 | 把复杂任务跑完且过程可控 | 越用越懂用户，复用历史经验 | 接入更多入口和设备，远程触发与审批 |

一句话概括：

```text
DeerFlow = Workflow brain
Hermes   = Memory brain
OpenClaw = Gateway nervous system
```

Hermes 相比 DeerFlow 的特色，是它不只关心“这个任务怎么完成”，而是关心“这个 Agent 怎么在长期互动中变得更像你的个人助理”。

Hermes 相比 OpenClaw 的特色，是它不只关心“任务如何从哪里进来、怎样路由和审批”，而是关心“Agent 如何把长期交互沉淀为可复用经验、技能和个人上下文”。

## SWE Agent 是否比通用 Agent Harness 更强？

从工具原语和功能复杂度看，Claude Code-like / SWE Agent 往往比很多通用 Agent Harness 更重、更接近能力超集。

一个成熟 SWE Agent 通常必须处理：

- 文件系统
- 多文件编辑
- 命令执行
- Git
- 测试
- 依赖安装
- 构建
- 搜索
- diff
- LSP / IDE
- 上下文压缩
- 项目记忆
- 权限
- 沙箱
- 用户审批
- 子任务
- 长输出
- 错误恢复
- tool result 清洗
- 终端 UI
- MCP / hooks / plugins

因此在“底层工具原语”层面，SWE Agent 很强，很多通用任务可以被 SWE Agent 用工具组合出来。

但在“系统目标和架构形态”层面，SWE Agent CLI 不是所有 Harness 的绝对超集：

| 架构能力 | 代表项目 | 为什么不只是 Claude Code-like CLI 的默认能力 |
|---|---|---|
| 长周期图状态机 | DeerFlow | 可以模拟长任务，但 DeerFlow 把 graph / checkpoint / middleware 做成核心 |
| 长期个人记忆 | Hermes Agent | 可以接 memory 工具，但 Hermes 把个人记忆和技能沉淀作为产品中心 |
| 多端控制面 | OpenClaw | 可以外接 IM / Webhook，但 OpenClaw 把 channel / device / queue / approval 做成核心 |
| SWE 平台控制面 | OpenHands | 可以脚本化 CLI，但 OpenHands 把 server / workspace / event / automation 做成核心 |

更准确的判断是：

> SWE Agent 的工具原语强，但不天然覆盖所有架构形态。

## 学习路线启发

第一轮定位之后，可以采用“先主干、再分支”的学习策略：

1. `learn-claude-code`：建立最小 Agent loop 心智模型
2. `claude-code-complete-guide_v2`：建立 Claude Code-like 完整能力清单
3. `claw-code`：看本地 CLI runtime 如何产品化
4. `openhands`：看 SWE Agent 如何平台化
5. `openclaw`：补多端 control plane
6. `deer-flow`：补 graph / long-horizon workflow
7. `hermes-agent`：补 memory-evolving personal agent

这不是价值排序，而是学习顺序建议：先学机制最密集的 SWE Agent 主干，再补其他分支的独特架构增量。

## 后续待核验问题

- OpenHands 的低层 Agent loop 具体边界在哪里？哪些逻辑在主仓库，哪些在 `openhands-agent-server` / `openhands-sdk` / `openhands-tools`？
- Hermes 的长期记忆、procedural memory、skill 自动沉淀机制在源码里如何触发、评估和防污染？
- DeerFlow 的 LangGraph 状态、middleware、sandbox、subagent 如何串联成完整长周期任务控制流？
- OpenClaw 的 durable queue、node registry、exec approval 和 embedded agent runtime 如何协同？
- Claw-Code 的权限、sandbox、MCP、hooks 与 Claude Code-like 能力清单之间有哪些 parity / 差异？

## 相关文档

- 调研 Base：[agent-harness-architecture-six-projects.md](agent-harness-architecture-six-projects.md)
- 本地源码核验补充：[agent-harness-local-source-verification.md](agent-harness-local-source-verification.md)
- 横向 QA：[qa.md](qa.md)
- 后续综合沉淀：[../synthesis/architecture-taxonomy.md](../synthesis/architecture-taxonomy.md)（待撰写）
