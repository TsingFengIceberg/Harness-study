# OpenClaw 研读笔记

> OpenClaw 是 Claude Code-like / 多端 Agent 控制面方向的开源实现。本目录用于记录对 OpenClaw 源码的纵向研读，先从 Agent Loop / Session Runtime 开始。

## 源码

- **Submodule**: [openclaw/](../../../submodules/openclaw/) — 指向 `openclaw/openclaw`
- **官方仓库**: [github.com/openclaw/openclaw](https://github.com/openclaw/openclaw)
- **当前快照**: `780ca1d25315b34d3118e1db2d8dcafcc16415f3`

## 笔记索引

| 文档 | 状态 | 说明 |
|---|---|---|
| [agent-loop.md](agent-loop.md) | draft | OpenClaw Agent Loop：AgentSession / Agent / runLoop 三层结构、double loop、steer/followUp 队列与事件状态机。 |
| [tool-system.md](tool-system.md) | draft | OpenClaw Tool System：AgentTool、createOpenClawCodingTools、policy pipeline、before_tool_call runtime、sequential/parallel 执行与 Tool Search。 |
| [context-management.md](context-management.md) | draft | OpenClaw Context Management：AgentContext.messages、transformContext / convertToLlm、streaming message、steer/followUp、compaction 与 session persistence。 |

## 源码入口

| 模块 | 源码 | 说明 |
|---|---|---|
| Session 外壳 | [agent-session.ts](../../../submodules/openclaw/src/agents/sessions/agent-session.ts) | 产品会话层：模型校验、prompt 入口、hook、compaction、retry、持久化、事件处理。 |
| Agent 核心 | [agent.ts](../../../submodules/openclaw/packages/agent-core/src/agent.ts) | Agent 状态、事件订阅、`prompt()` / `continue()` / `steer()` / `followUp()`、队列管理。 |
| Loop 本体 | [agent-loop.ts](../../../submodules/openclaw/packages/agent-core/src/agent-loop.ts) | `runAgentLoop()` / `runAgentLoopContinue()` / `runLoop()`，负责模型流式调用、工具执行与 steer/followUp 调度。 |
| 类型定义 | [types.ts](../../../submodules/openclaw/packages/agent-core/src/types.ts) | `AgentEvent`、`AgentState`、`AgentContext`、`AgentMessage`、`AgentTool`、`AgentLoopConfig`、`transformContext` / `convertToLlm` 等类型。 |
| Harness 消息转换 | [messages.ts](../../../submodules/openclaw/packages/agent-core/src/harness/messages.ts) | `convertToLlm` 把 bashExecution / custom / branchSummary / compactionSummary 等产品态消息转换成 LLM-facing message。 |
| Harness 上下文 hook | [agent-harness.ts](../../../submodules/openclaw/packages/agent-core/src/harness/agent-harness.ts) | `CoreAgentHarness` 安装 context hook、tool hook、prepareNextTurn 和 session write flush。 |
| 工具装配 | [agent-tools.ts](../../../submodules/openclaw/src/agents/agent-tools.ts) | `createOpenClawCodingTools` 按 run/session/channel/model/sandbox/policy 动态组装工具面。 |
| 工具治理 | [agent-tools.before-tool-call.ts](../../../submodules/openclaw/src/agents/agent-tools.before-tool-call.ts) | before_tool_call policy runtime：plugin hooks、approval、diagnostics、loop detection 等。 |
| Tool Search | [tool-search.ts](../../../submodules/openclaw/src/agents/tool-search.ts) | search / describe / call / code-mode 工具目录服务。 |

## 阶段性定位

OpenClaw 的 Agent Loop 可以概括为：

> **手写 core double loop + Agent 事件状态机 + AgentSession 产品会话外壳。**

它不像 DeerFlow 那样把模型/工具循环主要交给 LangGraph runtime，也不像 Claw-Code 那样把本地 CLI 单轮对话主线集中在一个 `run_turn` 附近；OpenClaw 更像一个有事件、有队列、有状态的 Agent session runtime。

## 相关横向讨论

- 横向 QA：[OpenClaw Agent Loop 是否只是普通 `while tool_use`？](../../comparison/qa.md#q-openclaw-agent-loop-是否只是普通-while-tool_use)
- 横向 QA：[OpenClaw 与 DeerFlow / Claw-Code 的精髓差异是什么？](../../comparison/qa.md#q-openclaw-与-deerflow--claw-code-的精髓差异是什么)
- 横向 QA：[OpenClaw 的 steer / followUp 队列有什么价值？](../../comparison/qa.md#q-openclaw-的-steer--followup-队列有什么价值)
- Tool System 横向专题：[Tool System 横向总结](../../comparison/tool-system.md)
