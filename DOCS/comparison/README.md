# 横向对比

> 跨项目的专题对比分析——同一维度，横切多个 Harness。

## 已归档报告

| 文档 | 涉及项目 | 说明 |
|---|---|---|
| [agent-harness-architecture.md](agent-harness-architecture.md) | DeerFlow / Hermes Agent / Claw-Code / OpenClaw / learn-claude-code | Deep Research 调研 Base：按 15 个维度比较五个 Agent Harness，作为后续自研专题拆分和综合归纳的底稿。注：本文生成早于 OpenHands 接入，暂未覆盖 OpenHands；文中判断后续需回到源码与官方文档逐项核验。 |
| [agent-harness-architecture-six-projects.md](agent-harness-architecture-six-projects.md) | DeerFlow / Hermes Agent / Claw-Code / OpenClaw / learn-claude-code / OpenHands | Deep Research 六项目扩展版：在五项目 Base 基础上补入 OpenHands，并加强平台化 SWE Agent、SDK / Server / Canvas / Automation 趋势讨论。文中可信度标注仍需后续源码研读逐项复核。 |
| [agent-harness-local-source-verification.md](agent-harness-local-source-verification.md) | Claw-Code / OpenClaw / learn-claude-code / OpenHands | Claude workflow 本地源码核验补充：成功读取四个 submodule 并提炼源码路径与工程判断；DeerFlow / Hermes Agent 因 API 524 timeout 未完成，本文不替代六项目调研 Base。 |

## QA / 讨论记录

| 文档 | 说明 |
|---|---|
| [qa.md](qa.md) | 横向学习 QA：收集跨项目问题、阶段性讨论结论与待核验点，后续成熟后迁移到 synthesis FAQ 或具体专题正文。 |

## 已完成专题

| 文档 | 涉及项目 | 说明 |
|---|---|---|
| [agent-loop.md](agent-loop.md) | Claw-Code / DeerFlow / Hermes Agent / OpenClaw / OpenHands | Agent Loop 第一轮横向总结：共同骨架、五类 loop 形态、工作组织 / 开车 / 公司组织比喻、关键维度对比与分类法。 |
| [tool-system.md](tool-system.md) | Claw-Code / DeerFlow / OpenHands / OpenClaw / Hermes Agent | Tool System 第一轮横向总结：覆盖 Claw-Code 集中式工具中枢、DeerFlow LangGraph 标准生产线、OpenHands 控制面 / software-agent-sdk 执行面分离、OpenClaw 事件化工具调度与 Hermes toolsets / Tool Search / guardrail / memory-skills 工具工作台，提炼两道权限门、ToolSearch / Tool Search、sequential / parallel 调度、ActionEvent / ObservationEvent 等跨项目比较框架。 |
| [context-management.md](context-management.md) | Claw-Code / OpenClaw / Hermes Agent / DeerFlow / OpenHands | Context Management 第一轮横向总结：围绕“模型下一轮看什么”，用本地施工日志、会话调度室、个人助理脑、状态流水线工厂、平台事件账本等比喻比较五类上下文管理模型。 |
| [multi-agent.md](multi-agent.md) | DeerFlow / Claw-Code / OpenClaw / Hermes Agent / OpenHands | Multi-Agent / Subagent 第一轮横向总结：提炼“派工、隔离、执行、回报、治理”的统一设计原则，对比 LangGraph `task` tool、Hermes `delegate_task`、OpenHands `TaskToolSet` / `AgentDefinition`、OpenClaw ACP 父子 session 与 Claw-Code TaskPacket / Worker / Team。 |
| [permission-security.md](permission-security.md) | Claw-Code / DeerFlow / OpenClaw / OpenHands / Hermes Agent | Permission / Security 第一轮横向笔记：从 Claw-Code 本地工具调用双闸门出发，对比 DeerFlow 工作流工厂安全生产线、OpenClaw 工具门禁 + 审批工单系统、OpenHands Action 风险安检 + 工位隔离、Hermes 长期个人助理自我保护系统，并标记 hooks 是外挂监工、middleware 是内建工位这一核心差异。 |
| [sandbox-systems.md](sandbox-systems.md) | DeerFlow / OpenHands / Claw-Code / OpenClaw / Hermes Agent | Sandbox / Workspace 第一轮横向总结：比较远程开发园区、工作流工厂生产线、本地施工围栏、多端协作工作室隔间与长期个人助理工作台五类执行环境边界。 |
| [production-deployment-tradeoffs.md](production-deployment-tradeoffs.md) | Claw-Code / OpenClaw / Hermes Agent / DeerFlow / OpenHands | 生产部署取舍：从实际运行、部署、长期运维、多用户、多端交互、长任务可靠性、安全隔离和成本角度比较五类 Agent Harness 设计。 |
| [project-positioning.md](project-positioning.md) | DeerFlow / Hermes Agent / Claw-Code / OpenClaw / learn-claude-code / OpenHands / Claude Code guide | 第一轮整体功能特色分析：说明这些项目是否同类、各自在 Agent Harness 演化树上的位置、Claude Code-like 基准、OpenHands 与 Claw-Code 差异、Hermes / DeerFlow / OpenClaw 的特色分工。 |

## 对比专题（待撰写）

| 专题 | 涉及项目 | 说明 |
|---|---|---|
| `hitl-patterns.md` | DeerFlow / Hermes Agent / OpenHands / OpenClaw | 人机协同模式：中断、审批、澄清、等待确认。 |
| `memory-context.md` | DeerFlow / Hermes Agent | 记忆系统专题：长期记忆、recall、memory provider、污染防护与 skill evolution（上下文管理总论见 [context-management.md](context-management.md)） |
| `middleware-pipeline.md` | DeerFlow / OpenClaw | 中间件 / 拦截器管道设计 |

## 各项目研读入口

| 项目 | 笔记目录 |
|---|---|
| DeerFlow | [DOCS/projects/deer-flow/](../projects/deer-flow/README.md) |
| OpenClaw | [DOCS/projects/openclaw/](../projects/openclaw/README.md) |
| Claw-Code | [DOCS/projects/claw-code/](../projects/claw-code/README.md) |
| Hermes Agent | [DOCS/projects/hermes-agent/](../projects/hermes-agent/README.md) |
| OpenHands | [DOCS/projects/openhands/](../projects/openhands/README.md) |
| learn-claude-code | `DOCS/projects/learn-claude-code/`（待建立） |

## 相关文档

- 综合归纳见 [DOCS/synthesis/](../synthesis/README.md)
