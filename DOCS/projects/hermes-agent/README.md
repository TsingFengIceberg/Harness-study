# Hermes Agent 学习笔记

> 记忆进化型个人 Agent Harness，重点研究长期记忆、会话循环、工具调用、技能沉淀、多通道入口和个人上下文。

## 源码

- **Submodule**: [hermes-agent/](../../../submodules/hermes-agent/) — 指向 `NousResearch/hermes-agent`
- **官方仓库**: [github.com/NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)
- **当前快照**: `05cbddc01234ea120cccc1f62d36f1ef352b0d52`

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
| [context-management.md](context-management.md) | Hermes Context Management：session-stable system prompt、临时 recall context、provider repair/sanitize、preflight / pre-API compression 与错误恢复 | draft |

## 源码入口

| 模块 | 源码 | 说明 |
|---|---|---|
| Agent Loop 主线 | [conversation_loop.py](../../../submodules/hermes-agent/agent/conversation_loop.py) | `run_conversation`，模型调用、tool loop、retry / fallback、API messages 构造与上下文压缩入口。 |
| Turn Context | [turn_context.py](../../../submodules/hermes-agent/agent/turn_context.py) | `build_turn_context`，每轮开始前准备 messages、system prompt、memory prefetch、plugin context、preflight compression。 |
| System Prompt | [system_prompt.py](../../../submodules/hermes-agent/agent/system_prompt.py) | `build_system_prompt_parts` / `build_system_prompt`，session-stable prompt snapshot 与 cache prefix。 |
| Memory Manager | [memory_manager.py](../../../submodules/hermes-agent/agent/memory_manager.py) | memory provider 编排、prefetch / sync、`<memory-context>` fencing 与 streaming scrubber。 |
| Context Compressor | [context_compressor.py](../../../submodules/hermes-agent/agent/context_compressor.py) | 默认 context engine，旧工具结果裁剪、头尾保护、中段摘要和 summary 迭代更新。 |
| Compression Orchestration | [conversation_compression.py](../../../submodules/hermes-agent/agent/conversation_compression.py) | `compress_context`，压缩锁、SessionDB rewrite / rotation、system prompt invalidation。 |
| Turn Finalizer | [turn_finalizer.py](../../../submodules/hermes-agent/agent/turn_finalizer.py) | session persist、response transform、external memory sync、background review。 |

## 后续待研读主题

| 主题 | 说明 | 状态 |
|---|---|---|
| `memory-system.md` | 长期记忆、external memory provider 内部、memory tool、事实 / 偏好沉淀与污染防护 | planned |
| `interrupt-steer.md` | interrupt / steer / gateway 多消息交互与线程中断 | planned |
| `skills-evolution.md` | skill_manage、经验沉淀与程序化技能 | planned |
| `session-persistence.md` | SessionDB、trajectory、crash recovery 与 resume | planned |

## 相关横向专题

- 整体定位：[项目定位与功能特色对比](../../comparison/project-positioning.md)
- 横向 QA：[Harness Study 横向 QA](../../comparison/qa.md)
- Agent Loop 横向专题：`../../comparison/agent-loop.md`（待撰写）
- 记忆与上下文专题：`../../comparison/memory-context.md`（待撰写）
