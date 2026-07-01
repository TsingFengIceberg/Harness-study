# OpenHands 学习笔记

> 面向软件工程任务的 AI Agent / Agent Canvas 生态，用于研究平台化 SWE Agent Harness。

## 源码

- **Submodule**: [openhands/](../../../openhands/) — 指向 `OpenHands/OpenHands`
- **官方仓库**: [github.com/OpenHands/OpenHands](https://github.com/OpenHands/OpenHands)
- **当前快照**: `0571ff530fa6114360feb10d2d1a0c2570987450`

## 研究定位

OpenHands 不作为单纯的 Claude Code 本地 CLI clone 来看，而作为 **平台化 SWE Agent Harness** 的代表：

- 从本地交互式 coding agent 扩展到 Agent Server / Agent Canvas / Automation
- 支持 local、Docker、VM、cloud 等多种 agent backend
- 面向 GitHub issue、代码维护、报告生成等软件工程自动化任务
- 可与 Claude Code、Codex、Gemini 或 ACP-compatible agent 协同

## 笔记索引

| 文档 | 状态 | 说明 |
|---|---|---|
| [agent-loop.md](agent-loop.md) | draft | OpenHands Agent Loop：控制面 / 执行面分离、Agent Server / SDK Conversation loop、action / observation 事件模型与工具执行边界。 |

## 待研读主题

| 主题 | 说明 | 状态 |
|---|---|---|
| `agent-loop.md` | 控制面 / 执行面分离、Agent Server / SDK Conversation loop、action / observation 事件模型 | draft |
| `architecture.md` | OpenHands 生态拆分：OpenHands / software-agent-sdk / agent-canvas / automation | planned |
| `agent-server.md` | Agent Server、会话 API、远程运行与流式事件 | planned |
| `workspace-runtime.md` | local / Docker / VM / cloud workspace 抽象与隔离边界 | planned |
| `tool-system.md` | terminal、file editor、task tracker、MCP / ACP 工具体系 | planned |
| `automation.md` | cron / webhook / GitHub / Slack / Linear 自动化触发 | planned |

## 相关对比方向

- 和 Claw-Code / OpenClaw 对比：本地 CLI Harness vs 平台化 SWE Agent Harness
- 和 SWE-agent 对比：产品化工程平台 vs benchmark / issue-repair harness
- 和 DeerFlow 对比：通用 Agent 中间件/沙箱 vs 软件工程垂直场景 runtime
- 和 E2B / CUA 对比：workspace / sandbox / computer-use 基础设施

## 相关文档

- 横向对比见 [DOCS/comparison/](../../comparison/README.md)
- 综合归纳见 [DOCS/synthesis/](../../synthesis/README.md)
