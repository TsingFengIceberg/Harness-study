# OpenClaw 研读笔记

> OpenClaw 是 Claude Code-like / 多端 Agent 控制面方向的开源实现。本目录用于记录对 OpenClaw 源码的纵向研读，先从 Agent Loop / Session Runtime 开始。

## 源码

- **Submodule**: [openclaw/](../../../openclaw/) — 指向 `openclaw/openclaw`
- **官方仓库**: [github.com/openclaw/openclaw](https://github.com/openclaw/openclaw)
- **当前快照**: `cb44f40474bd88d3ba2e1c3c3f60767c9f6194e5`

## 笔记索引

| 文档 | 状态 | 说明 |
|---|---|---|
| [agent-loop.md](agent-loop.md) | draft | OpenClaw Agent Loop：AgentSession / Agent / runLoop 三层结构、double loop、steer/followUp 队列与事件状态机。 |

## 源码入口

| 模块 | 源码 | 说明 |
|---|---|---|
| Session 外壳 | [agent-session.ts](../../../openclaw/src/agents/sessions/agent-session.ts) | 产品会话层：模型校验、prompt 入口、hook、compaction、retry、持久化、事件处理。 |
| Agent 核心 | [agent.ts](../../../openclaw/packages/agent-core/src/agent.ts) | Agent 状态、事件订阅、`prompt()` / `continue()` / `steer()` / `followUp()`、队列管理。 |
| Loop 本体 | [agent-loop.ts](../../../openclaw/packages/agent-core/src/agent-loop.ts) | `runAgentLoop()` / `runAgentLoopContinue()` / `runLoop()`，负责模型流式调用、工具执行与 steer/followUp 调度。 |
| 类型定义 | [types.ts](../../../openclaw/packages/agent-core/src/types.ts) | `AgentEvent`、`AgentState`、`AgentTool`、`AgentMessage`、`AgentLoopConfig` 等类型。 |

## 阶段性定位

OpenClaw 的 Agent Loop 可以概括为：

> **手写 core double loop + Agent 事件状态机 + AgentSession 产品会话外壳。**

它不像 DeerFlow 那样把模型/工具循环主要交给 LangGraph runtime，也不像 Claw-Code 那样把本地 CLI 单轮对话主线集中在一个 `run_turn` 附近；OpenClaw 更像一个有事件、有队列、有状态的 Agent session runtime。

## 相关横向讨论

- 横向 QA：[OpenClaw Agent Loop 是否只是普通 `while tool_use`？](../../comparison/qa.md#q-openclaw-agent-loop-是否只是普通-while-tool_use)
- 横向 QA：[OpenClaw 与 DeerFlow / Claw-Code 的精髓差异是什么？](../../comparison/qa.md#q-openclaw-与-deerflow--claw-code-的精髓差异是什么)
- 横向 QA：[OpenClaw 的 steer / followUp 队列有什么价值？](../../comparison/qa.md#q-openclaw-的-steer--followup-队列有什么价值)
