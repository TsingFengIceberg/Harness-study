# Hermes Agent 学习笔记

> 记忆进化型个人 Agent Harness，重点研究长期记忆、会话循环、工具调用、技能沉淀、多通道入口和个人上下文。

## 源码

- **Submodule**: [hermes-agent/](../../../submodules/hermes-agent/) — 指向 `NousResearch/hermes-agent`
- **官方仓库**: [github.com/NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)
- **当前快照**: `18e840469ffe9f8235331c787e34ebbe908564b8`

## 研究定位

Hermes Agent 在本仓库中定位为 **Memory-evolving personal agent harness** 的代表。

它不是本地 coding CLI clone，也不是平台化 SWE Agent 控制面；它更适合作为研究“长期陪伴型个人 Agent 如何把记忆、偏好、技能和工具调用结合起来”的样本：

- 跨会话 conversation loop
- 长期记忆 / external memory / session persistence
- tool call 执行、interrupt、steer、budget
- skill / memory / todo 等个人化能力
- CLI / TUI / gateway / IM 等多入口协作

## 笔记目录

| 文档 | 主题 | 状态 |
|---|---|---|
| [agent-loop.md](agent-loop.md) | `run_conversation` 手写对话循环：API 调用、tool_calls、tool result 回写、interrupt / steer / iteration budget、最终响应 | draft |
| [tool-system.md](tool-system.md) | Hermes Tool System：toolsets、registry、Tool Search、sequential/concurrent 执行、guardrail、memory / skills / todo 工具化 | draft |

## 后续待研读主题

| 主题 | 说明 | 状态 |
|---|---|---|
| `memory-system.md` | 长期记忆、external memory prefetch、session history、memory tool | planned |
| `interrupt-steer.md` | interrupt / steer / gateway 多消息交互与线程中断 | planned |
| `skills-evolution.md` | skill_manage、经验沉淀与程序化技能 | planned |
| `session-persistence.md` | SessionDB、trajectory、crash recovery 与 resume | planned |

## 相关横向专题

- 整体定位：[项目定位与功能特色对比](../../comparison/project-positioning.md)
- 横向 QA：[Harness Study 横向 QA](../../comparison/qa.md)
- Agent Loop 横向专题：`../../comparison/agent-loop.md`（待撰写）
- 记忆与上下文专题：`../../comparison/memory-context.md`（待撰写）
