# OpenHands 学习笔记

> 面向软件工程任务的 AI Agent / Agent Canvas 生态，用于研究平台化 SWE Agent Harness。

## 源码

- **Submodule（控制面）**: [openhands/](../../../submodules/openhands/) — 指向 `OpenHands/OpenHands`，覆盖 Agent Canvas / App Server / Sandbox / automation
- **Submodule（执行面）**: [software-agent-sdk/](../../../submodules/software-agent-sdk/) — 指向 `OpenHands/software-agent-sdk`，覆盖 Agent Server / SDK Conversation / Agent / `openhands-tools`
- **官方仓库（控制面）**: [github.com/OpenHands/OpenHands](https://github.com/OpenHands/OpenHands)
- **官方仓库（执行面）**: [github.com/OpenHands/software-agent-sdk](https://github.com/OpenHands/software-agent-sdk)
- **当前快照**:
  - `openhands`: `af7efea64fb097e75dabc439288356d6156fb247`
  - `software-agent-sdk`: `701644b2043d1d42a485680e0b8ed471ecfbe98b`

## 研究定位

OpenHands 不作为单纯的 Claude Code 本地 CLI clone 来看，而作为 **平台化 SWE Agent Harness** 的代表。研读时需要把两个官方仓库合在一起理解：

- [openhands/](../../../submodules/openhands/) 是平台控制面：负责 Agent Canvas / App Server、会话与事件管理、sandbox 管理、自动化入口和多 backend 接入。
- [software-agent-sdk/](../../../submodules/software-agent-sdk/) 是执行面：负责 Agent Server、SDK `Conversation` / `Agent` 循环、Action / Observation 事件模型，以及 Terminal / FileEditor / TaskTracker / Browser / TaskTool 等工具包。

它的研究重点包括：

- 从本地交互式 coding agent 扩展到 Agent Server / Agent Canvas / Automation
- 支持 local、Docker、VM、cloud 等多种 agent backend
- 面向 GitHub issue、代码维护、报告生成等软件工程自动化任务
- 可与 Claude Code、Codex、Gemini 或 ACP-compatible agent 协同

## 笔记索引

| 文档 | 状态 | 说明 |
|---|---|---|
| [agent-loop.md](agent-loop.md) | draft | OpenHands Agent Loop：控制面 / 执行面分离、Agent Server / SDK Conversation loop、action / observation 事件模型与工具执行边界。 |
| [tool-system.md](tool-system.md) | draft | OpenHands Tool System：默认工具预设、ToolDefinition / Action / Observation、ActionEvent / ObservationEvent、并发执行与控制面 / 执行面边界。 |

## 待研读主题

| 主题 | 说明 | 状态 |
|---|---|---|
| `agent-loop.md` | 控制面 / 执行面分离、Agent Server / SDK Conversation loop、action / observation 事件模型 | draft |
| `architecture.md` | OpenHands 生态拆分：OpenHands / software-agent-sdk / agent-canvas / automation | planned |
| `agent-server.md` | Agent Server、会话 API、远程运行与流式事件 | planned |
| `workspace-runtime.md` | local / Docker / VM / cloud workspace 抽象与隔离边界 | planned |
| `tool-system.md` | terminal、file editor、task tracker、browser、subagent、MCP / ACP 工具体系 | draft |
| `automation.md` | cron / webhook / GitHub / Slack / Linear 自动化触发 | planned |

## 相关对比方向

- 和 Claw-Code / OpenClaw 对比：本地 CLI Harness vs 平台化 SWE Agent Harness
- 和 SWE-agent 对比：产品化工程平台 vs benchmark / issue-repair harness
- 和 DeerFlow 对比：通用 Agent 中间件/沙箱 vs 软件工程垂直场景 runtime
- 和 E2B / CUA 对比：workspace / sandbox / computer-use 基础设施

## 相关文档

- 横向对比见 [DOCS/comparison/](../../comparison/README.md)
- 综合归纳见 [DOCS/synthesis/](../../synthesis/README.md)
