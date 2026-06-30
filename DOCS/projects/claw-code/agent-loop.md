# Claw-Code Agent Loop：ConversationRuntime::run_turn

> **日期**: 2026-06-30 | **状态**: draft | **涉及版本**: `4ea31c1bc91c4e9bcbd67d51c550c01e127e6d0d`
>
> 本文记录 Claw-Code 本地 CLI runtime 的核心对话循环。重点是 `ConversationRuntime::run_turn` 的主干控制流，不展开工具系统、权限系统、hooks、session、compaction 等子系统的完整实现；这些内容后续拆到对应专题笔记。

## 相关源码

- 核心对话循环：[conversation.rs](../../../claw-code/rust/crates/runtime/src/conversation.rs)
- `ApiClient` 抽象：[conversation.rs:56-59](../../../claw-code/rust/crates/runtime/src/conversation.rs#L56-L59)
- `ToolExecutor` 抽象：[conversation.rs:61-64](../../../claw-code/rust/crates/runtime/src/conversation.rs#L61-L64)
- `ConversationRuntime` 结构：[conversation.rs:129-143](../../../claw-code/rust/crates/runtime/src/conversation.rs#L129-L143)
- `run_turn` 主循环：[conversation.rs:325-531](../../../claw-code/rust/crates/runtime/src/conversation.rs#L325-L531)
- 自动压缩检查：[conversation.rs:571-594](../../../claw-code/rust/crates/runtime/src/conversation.rs#L571-L594)
- 最大迭代次数测试候选：[conversation.rs:1808](../../../claw-code/rust/crates/runtime/src/conversation.rs#L1808) 附近（后续需复核具体测试内容）

## 最小 Agent Loop 参照

Claw-Code 的实现可以先和 learn-claude-code 的最小 loop 对照。

最小 loop 见 [learn-claude-code/s01_agent_loop/code.py:84-113](../../../learn-claude-code/s01_agent_loop/code.py#L84-L113)：

```text
while True:
    response = LLM(messages, tools)
    append assistant message

    if response.stop_reason != "tool_use":
        return

    execute tool calls
    append tool_result
```

这个抽象的含义不是“纯文本回答也是工具调用”，而是：模型每轮要么给出最终文本回答，要么请求外部动作。

```text
LLM response
├── final text answer        -> harness 结束本轮
└── tool_use / tool_calls    -> harness 执行工具，把 tool_result 回写给 LLM，再继续下一轮
```

术语上，Anthropic 常用 `tool_use` / `stop_reason == "tool_use"`，OpenAI 风格常说 `tool_calls`。二者在 Harness 设计里都指“模型请求宿主系统执行外部动作”。纯文本回答不是 tool call；它是 loop 的终止输出。

## ConversationRuntime 是什么

`ConversationRuntime` 是 Claw-Code 本地 CLI runtime 的核心组合对象之一。它把以下构件放在同一个 turn runtime 里：

- session / messages
- API client
- tool executor
- permission policy / permission prompter
- system prompt
- max_iterations
- usage tracker
- hook runner
- compaction 配置

对应结构定义见 [conversation.rs:129-143](../../../claw-code/rust/crates/runtime/src/conversation.rs#L129-L143)。

因此，回答“[conversation.rs](../../../claw-code/rust/crates/runtime/src/conversation.rs) 是不是 Claw-Code 的核心对话实现文件”：是核心之一，尤其是单轮对话 / 工具循环主干；但不是整个 Claw-Code 的全部。CLI 入口、工具注册、权限策略、sandbox、session 持久化、MCP/plugin 等仍分布在其他模块，后续需要分专题继续读。

## run_turn 主干控制流

`run_turn` 的主循环大致可以拆成以下阶段：

```text
1. 把用户输入追加到 session
2. maybe_auto_compact：必要时先压缩上下文
3. 进入最多 max_iterations 次循环
4. 调用模型并流式接收 assistant 输出
5. 把 assistant message 写回 session
6. 从 assistant content blocks 中提取 ToolUse
7. 如果没有 ToolUse：说明模型给出最终回答，退出 loop
8. 对每个 ToolUse：
   - 运行 pre-tool hook
   - 做 permission 检查 / 用户确认
   - 执行工具
   - 运行 post-tool hook
   - 组装 tool_result 并写回 session
9. 继续下一次模型调用
10. 汇总 TurnSummary
```

其中最关键的终止条件在 [conversation.rs:414-416](../../../claw-code/rust/crates/runtime/src/conversation.rs#L414-L416) 附近：如果本轮 assistant 消息里没有 pending tool use，就 break loop。也就是说，模型不再请求工具时，Harness 认为这个 turn 的 agent loop 已经结束。

## 最大迭代次数是什么意思

`max_iterations` 是 Agent Loop 的熔断阈值。相关检查在 [conversation.rs:354-362](../../../claw-code/rust/crates/runtime/src/conversation.rs#L354-L362)：每一次“模型调用 + 可能的工具执行 + tool_result 回写”都算一次 iteration。

它要防止这种情况：

```text
LLM -> tool_use A
Tool A -> tool_result
LLM -> tool_use B
Tool B -> tool_result
LLM -> tool_use C
...
```

如果模型持续认为“还需要调用工具”，或者工具结果不断诱发新的工具请求，loop 就可能无限运行。`max_iterations` 的作用是给本轮对话设置上限：超过上限后停止继续请求模型 / 执行工具，并返回相应错误或终止信息。

这不是业务任务完成度判断，而是 runtime 层的安全边界：

- 防止无限循环
- 控制 API 成本
- 控制本地命令 / 文件操作风险
- 避免 session 被无限追加 tool_result
- 让调用方能拿到明确失败，而不是一直挂起

## ToolUse 提取与 tool_result 回写

Claw-Code 在模型返回 assistant message 后，会扫描 assistant content blocks 提取 `ToolUse`。相关逻辑见 [conversation.rs:387-396](../../../claw-code/rust/crates/runtime/src/conversation.rs#L387-L396)。

提取到 tool use 后，后续会进入工具执行段，主干范围在 [conversation.rs:418-517](../../../claw-code/rust/crates/runtime/src/conversation.rs#L418-L517)：

1. 执行前 hook
2. 权限检查
3. 调用 `ToolExecutor`
4. 执行后 hook
5. 把结果包装成 `tool_result`
6. 写回 session messages

这里体现了成熟 Coding CLI Harness 相比最小教学 loop 的工程化增量：最小 loop 只关心“有工具就执行”；Claw-Code 还要关心 hook、permission、错误处理、结果格式、usage、session 持久化等运行时边界。

## QA / 讨论记录

### Q: Claw-Code 的“检查最大迭代次数”是什么意思？

> **状态**: draft  
> **来源**: discussion / source-code

A: 在 `ConversationRuntime::run_turn` 中，每一次“模型调用 + 工具执行 + tool_result 回写”构成一次 loop iteration。`max_iterations` 是防止模型持续调用工具、工具结果又诱发下一轮工具调用，从而陷入无限循环的熔断阈值。它主要是 runtime 安全边界，不是任务完成度判断。

### Q: 为什么 Agent Loop 的最简形式可以抽象为 `if response.stop_reason != "tool_use": return; execute tool calls`？纯文本回答也算 tool call 吗？

> **状态**: draft  
> **来源**: discussion / source-code

A: 纯文本回答不算 tool call。这个抽象表达的是：模型每轮要么给出最终文本回答，要么请求外部动作。如果模型没有请求工具，Harness 就把当前 assistant 消息视为终止输出；如果模型请求工具，Harness 执行工具并把 tool_result 回写给模型，进入下一轮。`tool_use` 是 Anthropic 常用术语，`tool_calls` 是 OpenAI 风格常用术语，本质上都是模型请求 Harness 执行外部动作。

### Q: `conversation.rs` 是 Claw-Code 的核心对话实现文件吗？

> **状态**: draft  
> **来源**: discussion / source-code

A: 是核心之一，尤其是本地 CLI runtime 的单轮对话 / 工具循环核心。它定义并串联 `ApiClient`、`ToolExecutor`、`ConversationRuntime` 和 `run_turn`，负责模型流式输出、tool use 提取、权限检查、hooks、工具执行、tool_result 回写、自动压缩和 usage 汇总。但 Claw-Code 的完整系统还包括 CLI 入口、工具注册、权限策略、sandbox、session 持久化、MCP/plugin 等其他模块。

### Q: 从 Agent Loop 里延伸出来的问题都应该放在本专题吗？

> **状态**: draft  
> **来源**: discussion

A: 不必。`run_turn` 会把模型流、工具、权限、session、hooks、compaction、summary 串在一起，因此很多问题虽然从 Agent Loop 里冒出来，但更适合放到后续对应专题中：`ToolExecutor` 属于工具系统，`PermissionPolicy` / `PermissionPrompter` 属于权限与 HITL，`maybe_auto_compact` 属于上下文压缩，pre/post tool hooks 属于 Hooks / Middleware，`TurnSummary` 属于事件、观测和调用方边界。Agent Loop 专题先画主干控制流，并把分支问题链接到后续专题。

## 后续分流到其他 Claw-Code 专题的问题

| 问题 | 后续专题 |
|---|---|
| `ToolExecutor` 如何注册和分发内置工具 / MCP 工具？ | `tool-system.md` |
| `PermissionPolicy` 如何决定 allow / deny / ask？ | `permission-security.md` |
| bash / 文件路径安全边界在哪里？ | `permission-security.md` / `sandbox-runtime.md` |
| pre-tool / post-tool hooks 的调用时机和失败策略是什么？ | `hooks-compaction.md` |
| `maybe_auto_compact` 如何判断上下文需要压缩？ | `hooks-compaction.md` / `session-state.md` |
| `Session` 如何持久化 messages、branch / fork？ | `session-state.md` |
| `TurnSummary` 被 CLI 或上层调用方如何使用？ | `session-state.md` / 入口专题 |
| CLI 命令如何创建 runtime 并调用 `run_turn`？ | CLI 入口专题（待定） |

## 相关文档

- 项目入口：[README.md](README.md)
- 横向 QA：[../../comparison/qa.md](../../comparison/qa.md)
- 项目定位对比：[../../comparison/project-positioning.md](../../comparison/project-positioning.md)
- learn-claude-code 最小 loop：[../../../learn-claude-code/s01_agent_loop/code.py](../../../learn-claude-code/s01_agent_loop/code.py)
