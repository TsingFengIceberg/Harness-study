# 横向对比

> 跨项目的专题对比分析——同一维度，横切多个 Harness。

## 已归档报告

| 文档 | 涉及项目 | 说明 |
|---|---|---|
| [agent-harness-architecture.md](agent-harness-architecture.md) | DeerFlow / Hermes Agent / Claw-Code / OpenClaw / learn-claude-code | Deep Research 调研 Base：按 15 个维度比较五个 Agent Harness，作为后续自研专题拆分和综合归纳的底稿。注：本文生成早于 OpenHands 接入，暂未覆盖 OpenHands；文中判断后续需回到源码与官方文档逐项核验。 |
| [agent-harness-architecture-six-projects.md](agent-harness-architecture-six-projects.md) | DeerFlow / Hermes Agent / Claw-Code / OpenClaw / learn-claude-code / OpenHands | Deep Research 六项目扩展版：在五项目 Base 基础上补入 OpenHands，并加强平台化 SWE Agent、SDK / Server / Canvas / Automation 趋势讨论。文中可信度标注仍需后续源码研读逐项复核。 |
| [agent-harness-local-source-verification.md](agent-harness-local-source-verification.md) | Claw-Code / OpenClaw / learn-claude-code / OpenHands | Claude workflow 本地源码核验补充：成功读取四个 submodule 并提炼源码路径与工程判断；DeerFlow / Hermes Agent 因 API 524 timeout 未完成，本文不替代六项目调研 Base。 |

## 对比专题（待撰写）

| 专题 | 涉及项目 | 说明 |
|---|---|---|
| `agent-loop.md` | DeerFlow / OpenClaw / Claw-Code | 主循环设计：Event Loop vs Graph vs Reactive |
| `sandbox-systems.md` | DeerFlow / OpenClaw / Claw-Code | 沙箱方案对比：Docker / Local / 远程 RPC |
| `tool-calling.md` | 全部 | 工具调用模型：定义、执行、结果回写 |
| `hitl-patterns.md` | DeerFlow / Hermes Agent | 人机协同模式：中断、审批、澄清 |
| `memory-context.md` | DeerFlow / Hermes Agent | 记忆 & 上下文管理 |
| `middleware-pipeline.md` | DeerFlow / OpenClaw | 中间件 / 拦截器管道设计 |
| `permission-security.md` | DeerFlow / Claw-Code | 权限控制 & 安全模型 |

## 各项目研读入口

| 项目 | 笔记目录 |
|---|---|
| DeerFlow | [DOCS/projects/deer-flow/](../projects/deer-flow/README.md) |
| OpenClaw | [DOCS/projects/openclaw/](../projects/openclaw/) (待建立) |
| Claw-Code | [DOCS/projects/claw-code/](../projects/claw-code/) (待建立) |
| Hermes Agent | [DOCS/projects/hermes-agent/](../projects/hermes-agent/) (待建立) |
| learn-claude-code | [DOCS/projects/learn-claude-code/](../projects/learn-claude-code/) (待建立) |

## 相关文档

- 综合归纳见 [DOCS/synthesis/](../synthesis/README.md)
