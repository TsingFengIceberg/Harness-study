# Hermes Agent Context Management：session-stable system prompt、临时 recall context 与多 provider 生存修复管线

> **日期**: 2026-07-06 | **状态**: draft | **涉及版本**: `18e840469ffe9f8235331c787e34ebbe908564b8`

## 相关文档

- 项目入口：[README.md](README.md)
- Agent Loop：[agent-loop.md](agent-loop.md)
- Tool System：[tool-system.md](tool-system.md)
- Sandbox / Workspace：[sandbox-workspace.md](sandbox-workspace.md)
- Claw-Code Context Management：[../claw-code/context-management.md](../claw-code/context-management.md)
- OpenClaw Context Management：[../openclaw/context-management.md](../openclaw/context-management.md)
- 横向 Agent Loop 总结：[agent-loop.md](../../comparison/agent-loop.md)
- 横向 Tool System 总结：[tool-system.md](../../comparison/tool-system.md)
- 横向 QA：[qa.md](../../comparison/qa.md#context-management--上下文管理)

## 源码入口

| 模块 | 源码 | 作用 |
|---|---|---|
| 主对话循环 | [conversation_loop.py](../../../submodules/hermes-agent/agent/conversation_loop.py) | `run_conversation`，负责 turn prologue、API messages 构造、provider 调用、tool loop、重试 / fallback / 压缩。 |
| turn prologue | [turn_context.py](../../../submodules/hermes-agent/agent/turn_context.py) | `TurnContext` / `build_turn_context`，每轮开始前准备 messages、system prompt、memory prefetch、plugin context、preflight compression。 |
| system prompt | [system_prompt.py](../../../submodules/hermes-agent/agent/system_prompt.py) | `build_system_prompt_parts` / `build_system_prompt`，按 stable / context / volatile 层构造并缓存 system prompt。 |
| system prompt restore | [conversation_loop.py:277-399](../../../submodules/hermes-agent/agent/conversation_loop.py#L277-L399) | `_restore_or_build_system_prompt` 从 SessionDB 恢复 system prompt，失败或不匹配时重建并持久化。 |
| memory manager | [memory_manager.py](../../../submodules/hermes-agent/agent/memory_manager.py) | `MemoryManager`，external memory provider 编排、prefetch、sync、context fencing / scrubber。 |
| memory context block | [memory_manager.py:336-350](../../../submodules/hermes-agent/agent/memory_manager.py#L336-L350) | `build_memory_context_block` 把 recall memory 包成 `<memory-context>` 临时上下文块。 |
| context compressor | [context_compressor.py](../../../submodules/hermes-agent/agent/context_compressor.py) | 默认 `ContextCompressor`，旧工具结果裁剪、头尾保护、中段摘要、summary 迭代更新。 |
| compression orchestration | [conversation_compression.py](../../../submodules/hermes-agent/agent/conversation_compression.py) | `compress_context`，压缩锁、memory pre-compress hook、SessionDB rewrite / rotation、system prompt invalidation。 |
| message repair helpers | [agent_runtime_helpers.py](../../../submodules/hermes-agent/agent/agent_runtime_helpers.py) | role alternation 修复、tool-call argument sanitize、thinking/tool XML 清理等运行时辅助。 |
| turn finalizer | [turn_finalizer.py](../../../submodules/hermes-agent/agent/turn_finalizer.py) | turn 结束后的 session persist、response transform、memory sync、background review。 |
| Agent façade | [run_agent.py](../../../submodules/hermes-agent/run_agent.py) | `AIAgent` 转发 `_build_system_prompt`、`_compress_context`、`_execute_tool_calls`、external memory sync。 |

## 1. 核心结论

Hermes Agent 的 Context Management 也可以写成基础公式：

```text
system prompt + message history + tools -> LLM request
```

但它的重点不只是“把历史发回模型”，而是让一个长期个人 Agent 在多 provider、长 session、memory / plugin、工具调用异常、上下文膨胀和 fallback 切换中继续运行。

可以概括为：

> **Hermes 的 context 是多 provider 长会话的生存修复对象：每轮 turn prologue 先准备 / 压缩 / 预取上下文；每次 API call 前把持久 messages 转成 provider 可接受的 `api_messages`；每次错误后再通过压缩、重试、fallback、message repair 或 sentinel 防污染来恢复可继续状态。**

和前两个项目的差异是：

```text
Claw-Code:
  本地 CLI transcript replay
  system prompt + Session.messages -> provider conversion

OpenClaw:
  产品态实时会话状态机
  AgentContext.messages -> transformContext -> convertToLlm

Hermes:
  长期个人 Agent 生存修复管线
  messages -> turn prologue -> recall/plugin injection -> repair/sanitize/compress -> provider/fallback
```

一句话记忆：

> **Claw-Code 像本地施工日志，OpenClaw 像在线工单状态机，Hermes 像长期私人助理的工作台：它不仅要记住对话，还要临时翻笔记、修坏消息、压缩历史、切换 provider，并防止错误污染后续会话。**

## 2. 总体数据流：从 conversation history 到 API messages

Hermes 的主入口仍是 [run_conversation](../../../submodules/hermes-agent/agent/conversation_loop.py)。每轮开始时先调用 [build_turn_context](../../../submodules/hermes-agent/agent/turn_context.py)，见 [conversation_loop.py:563-598](../../../submodules/hermes-agent/agent/conversation_loop.py#L563-L598)：

```text
run_conversation(user_message, conversation_history, system_message, ...)
  -> build_turn_context(...)
       - sanitize user input
       - copy conversation_history
       - append current user message
       - restore/build cached system prompt
       - early persist current user turn
       - preflight context compression
       - plugin pre_llm_call context
       - external memory prefetch
  -> while budget remains:
       - build api_messages from messages
       - inject recall/plugin context into current user API copy
       - repair/sanitize provider-facing message sequence
       - apply prompt caching
       - pre-API pressure compression
       - call provider / fallback
       - append assistant/tool/error messages
       - continue or finalize
  -> finalize_turn(...)
       - clean/persist session
       - sync external memory
       - background memory/skill review
```

`TurnContext` 的字段定义在 [turn_context.py:92-117](../../../submodules/hermes-agent/agent/turn_context.py#L92-L117)，包含：

```text
user_message
original_user_message
messages
conversation_history
active_system_prompt
effective_task_id / turn_id
current_turn_user_idx
should_review_memory
plugin_user_context
ext_prefetch_cache
```

这说明 Hermes 把“本轮上下文准备”显式抽成了一个 prologue：它不是直接 `messages.append(user) -> call model`，而是在模型循环前就处理 session、memory、plugin、compression、todo/nudge、crash-resilience 等长期个人 Agent 需要的运行状态。

## 3. messages：真实对话轨迹的持久主干

在 [turn_context.py:261-310](../../../submodules/hermes-agent/agent/turn_context.py#L261-L310)，Hermes 会：

```text
messages = list(conversation_history) if conversation_history else []
user_msg = {"role": "user", "content": user_message}
messages.append(user_msg)
current_turn_user_idx = len(messages) - 1
```

也就是说：

| 层 | 含义 |
|---|---|
| `conversation_history` | 调用方传入的历史消息，通常来自 session persistence。 |
| `messages` | 本轮 working transcript；loop 内会继续追加 assistant / tool / recovery messages。 |
| `api_messages` | 每次 API call 前从 `messages` 拷贝 / 修复 / 注入后的 provider-facing 副本。 |

这个区分很重要：

```text
messages      = Hermes 自己维护和持久化的真实会话轨迹
api_messages  = 这一次发给当前 provider 的临时请求副本
```

Hermes 的很多上下文能力都依赖这个分层。比如 memory recall 和 plugin context 只注入 `api_messages`，不改 `messages`；provider-specific 字段清理也只清理 API copy，避免破坏内部 transcript。

[turn_context.py:330-338](../../../submodules/hermes-agent/agent/turn_context.py#L330-L338) 还会在 session row 建好后尽早 `_persist_session(...)`，把用户本轮输入先落盘。这是 crash-resilience：即使后面工具执行或 provider 调用出错，session 也不会完全丢掉本轮用户输入。

## 4. system prompt：session-stable cache prefix

Hermes 的 system prompt 是这轮讨论最值得标记的点。

### 4.1 构造层：stable / context / volatile

[system_prompt.py:113-130](../../../submodules/hermes-agent/agent/system_prompt.py#L113-L130) 把 system prompt 拆成三类：

| 层 | 内容 |
|---|---|
| `stable` | 身份、工具指导、skills prompt、环境 / 平台 / 模型族操作指导。 |
| `context` | context files，例如 `AGENTS.md`、`.cursorrules`，以及调用方传入的 system_message。 |
| `volatile` | memory snapshot、USER profile、external memory provider block、timestamp / session / model / provider 行。 |

但这里的 `volatile` 容易误解。它不是“每次 API call 都刷新”。[system_prompt.py:125-129](../../../submodules/hermes-agent/agent/system_prompt.py#L125-L129) 明确说：这些 parts 会 join 成一个字符串，并缓存到 `agent._cached_system_prompt`；Hermes 不会在 session 中途重新 render 局部 parts，因为这会破坏 prompt cache。

[system_prompt.py:470-483](../../../submodules/hermes-agent/agent/system_prompt.py#L470-L483) 也强调：

- `build_system_prompt` 每个 session 调一次；
- 压缩事件后才重建；
- 系统提示整体作为一个 cached block；
- Hermes 不在 session 中途重新注入局部内容。

### 4.2 恢复层：从 SessionDB 复用同一份 prompt

[conversation_loop.py:277-399](../../../submodules/hermes-agent/agent/conversation_loop.py#L277-L399) 的 `_restore_or_build_system_prompt(...)` 是关键。

它区分 DB 中 system prompt 的状态：

```text
missing  -> 没有 session row，通常是第一轮
null     -> row 存在但 system_prompt 为 NULL
empty    -> row 存在但 system_prompt 为空字符串
present  -> 有可用 prompt
stale_runtime -> prompt 中 Model / Provider 与当前运行时不匹配
```

如果 stored prompt 存在并且 runtime identity 匹配，[conversation_loop.py:326-330](../../../submodules/hermes-agent/agent/conversation_loop.py#L326-L330) 会：

```text
agent._cached_system_prompt = stored_prompt
return
```

否则才 rebuild，并在 [conversation_loop.py:389-398](../../../submodules/hermes-agent/agent/conversation_loop.py#L389-L398) 写回 SessionDB。

每轮 prologue 也不是无条件重建 system prompt，而是在 [turn_context.py:319-323](../../../submodules/hermes-agent/agent/turn_context.py#L319-L323)：

```text
if agent._cached_system_prompt is None:
    restore_or_build_system_prompt(...)
active_system_prompt = agent._cached_system_prompt
```

> **精髓标记**：Hermes 把 system prompt 当成 **session-stable cache prefix**。正常情况下同一个 session 复用同一份 system prompt；只有 DB 缺失、为空、过期或 runtime identity 不匹配时才重建；重建后还要写回 SessionDB，避免后续每轮都 cache miss。

这和 Claw-Code / OpenClaw 的对比是：

| 项目 | system prompt 气质 |
|---|---|
| Claw-Code | REPL 内更像启动时项目快照；后续实时状态主要靠工具读取和 `Session.messages`。 |
| OpenClaw | `AgentContext.systemPrompt` 是产品 session 状态的一部分，可被 AgentSession / extension 在 turn 入口调整。 |
| Hermes | system prompt 是 session-stable cache prefix；memory/plugin recall 不轻易写入 system，避免破坏 cache。 |

## 5. recall context：临时贴给模型看的参考资料

先用最简单的话定义：

> **recall context 就是 Hermes 临时找出来、贴到本轮用户问题后面的“参考资料 / 小抄”。模型本轮能看到，但它不是新用户输入、不是 system prompt，也不会永久写进会话历史。**

比如用户问：

```text
继续帮我分析 Hermes 的 context management。
```

Hermes 可能从 memory provider 或 plugin 中临时找到：

```text
用户之前更关心 Agent Loop / Tool System / Context Management 的横向比较；
用户喜欢标记“精髓”；
之前已经讨论过 Claw-Code 的 Session.messages 和 OpenClaw 的 transformContext。
```

那么这次真正发给模型的 user message 副本可能变成：

```text
继续帮我分析 Hermes 的 context management。

<memory-context>
[System note: The following is recalled memory context, NOT new user input...]
用户之前更关心 Agent Loop / Tool System / Context Management 的横向比较...
</memory-context>
```

### 5.1 recall context 从哪里来？

第一类来源是 external memory provider。turn prologue 在 [turn_context.py:514-520](../../../submodules/hermes-agent/agent/turn_context.py#L514-L520) 调用：

```text
ext_prefetch_cache = agent._memory_manager.prefetch_all(query)
```

`MemoryManager.prefetch_all(...)` 定义在 [memory_manager.py:495-515](../../../submodules/hermes-agent/agent/memory_manager.py#L495-L515)。它会拿当前用户问题去各个 provider 里查相关上下文，失败时 fail-open，不阻断主 turn。

第二类来源是 plugin `pre_llm_call` hook。[turn_context.py:434-483](../../../submodules/hermes-agent/agent/turn_context.py#L434-L483) 会收集 plugin 返回的 `context` 字段，并在过大时 spill，避免 runaway plugin 把 prompt 撑爆。

### 5.2 recall context 怎么进模型？

在 API messages 构造阶段，[conversation_loop.py:786-803](../../../submodules/hermes-agent/agent/conversation_loop.py#L786-L803) 只在 `idx == current_turn_user_idx` 时，把 memory 和 plugin context 追加到当前 user message 的 **API copy**：

```text
if idx == current_turn_user_idx and role == "user":
    injections = []
    if ext_prefetch_cache:
        injections.append(build_memory_context_block(ext_prefetch_cache))
    if plugin_user_context:
        injections.append(plugin_user_context)
    api_msg["content"] = base + "\n\n" + injections
```

源码注释明确说：

```text
Both are API-call-time only — the original message in `messages` is
never mutated, so nothing leaks into session persistence.
```

所以 recall context 的位置可以记成：

```text
persistent messages:
  user: "继续帮我分析 Hermes 的 context management。"

api_messages only:
  user: "继续帮我分析 Hermes 的 context management。\n\n<memory-context>...</memory-context>"
```

### 5.3 为什么不放 system prompt？

[conversation_loop.py:827-846](../../../submodules/hermes-agent/agent/conversation_loop.py#L827-L846) 明确说明：external recall context 注入 user message，不注入 system prompt，因为 system prompt 要保持 stable cache prefix。

这也是 Hermes 的核心分层：

| 层 | 作用 | 是否持久 | 是否稳定 |
|---|---|---|---|
| system prompt | 身份、规则、工具使用指导、session-stable prefix | 存入 SessionDB | 尽量稳定 |
| persistent messages | 真实 user / assistant / tool 轨迹 | 持久化 | 随对话增长 |
| recall context | 本轮临时参考资料 / 小抄 | 不持久化 | 每轮可变 |

> **精髓标记**：Hermes 把 system prompt、persistent conversation history、ephemeral recall context 严格分层：system prompt 保持 session-stable 以复用 prompt cache；conversation messages 保存真实对话轨迹；memory/plugin recall context 只在 API-call copy 中追加到当前 user message，既让模型看见相关背景，又避免污染持久化 transcript。

### 5.4 recall context 如何防泄漏？

`build_memory_context_block(...)` 在 [memory_manager.py:336-350](../../../submodules/hermes-agent/agent/memory_manager.py#L336-L350) 会先 `sanitize_context(...)`，再用 `<memory-context>` 包起来，并加 note：

```text
NOT new user input
Treat as authoritative reference data
```

同时 [memory_manager.py:163-168](../../../submodules/hermes-agent/agent/memory_manager.py#L163-L168) 的 `sanitize_context` 会剥掉已经存在的 memory-context 标签 / system note，避免 provider 返回的上下文被重复嵌套或注入。

[StreamingContextScrubber](../../../submodules/hermes-agent/agent/memory_manager.py#L171-L270) 还专门处理 streaming 输出中跨 chunk 泄漏 `<memory-context>` 的情况：如果模型把内部 memory-context 原样吐出来，scrubber 会在流式输出层把它抹掉。

这说明 Hermes 把 recall context 当成“模型可见、用户不应直接看到、也不应回写成正式对话”的内部参考资料。

## 6. API messages 构造：provider survival repair pipeline

Hermes 的 `messages -> api_messages` 不是简单 clone。每次 API call 前，[conversation_loop.py:751-825](../../../submodules/hermes-agent/agent/conversation_loop.py#L751-L825) 会先做一批修复：

| 步骤 | 作用 |
|---|---|
| `_sanitize_tool_call_arguments(...)` | 修复 corrupted tool_call arguments。 |
| `repair_message_sequence_with_cursor(...)` | 修复 malformed role alternation，并同步 SessionDB flush cursor。 |
| memory/plugin injection | 把 recall context 追加到当前 user API copy。 |
| `_copy_reasoning_content_for_api(...)` | 把内部 reasoning 信息转成 provider 需要的 API 字段。 |
| 移除 `reasoning` / `finish_reason` / `_thinking_prefill` | 清掉 provider 不接受的内部字段。 |
| `_sanitize_tool_calls_for_strict_api(...)` | 对 strict API 清理 Codex Responses 等非标准字段。 |

随后 [conversation_loop.py:827-947](../../../submodules/hermes-agent/agent/conversation_loop.py#L827-L947) 继续处理：

- prepend stable system prompt；
- 注入 prefill messages；
- `apply_anthropic_cache_control(...)`；
- `_sanitize_api_messages(...)` 清理 orphaned tool results / missing tool result；
- `_drop_thinking_only_and_merge_users(...)` 避免 thinking-only assistant turn 触发 Anthropic / gateway 400；
- normalize whitespace；
- normalize tool-call JSON；
- 清理 surrogate unicode。

这条链路可以写成：

```text
Hermes internal messages
  -> sanitize tool_call arguments
  -> repair role sequence + flush cursor
  -> inject recall/plugin context into current user API copy
  -> adapt reasoning fields
  -> strip internal/provider-incompatible fields
  -> prepend cached system prompt
  -> apply prompt cache controls
  -> remove orphan tool results / thinking-only turns
  -> normalize JSON / whitespace / unicode
  -> provider-facing api_messages
```

> **精髓标记**：Hermes 的 context management 很大一部分是 **provider survival repair pipeline**。它假设长期会话历史会被 tool-call 异常、provider 字段差异、reasoning 格式、orphan tool result、streaming 残片和 unicode 问题污染，因此每次 API call 前都把内部 transcript 修成当前 provider 能接受的请求副本。

这和 OpenClaw 的 `transformContext / convertToLlm` 有相似之处，但侧重点不同：

| 项目 | 请求前转换重点 |
|---|---|
| OpenClaw | 产品态 AgentMessage 到 provider Message 的两层适配：先治理上下文，再协议转换。 |
| Hermes | 长期运行中的 provider 兼容和错误修复：先把脏 transcript 修到可发送，再适配 provider quirks。 |

## 7. 长 session：多位置防爆，而不是单点 compact

Hermes 的上下文压缩不是只有一个入口，而是多层防线。

### 7.1 turn prologue preflight compression

[turn_context.py:340-433](../../../submodules/hermes-agent/agent/turn_context.py#L340-L433) 在每轮开始时做 preflight：

1. 先用 `_should_run_preflight_estimate(...)` 判断是否值得做完整 token estimate；
2. 用 `estimate_request_tokens_rough(...)` 估算 messages + system prompt + tools；
3. 避免 rough estimate 已知不准的场景；
4. 避免 compression failure cooldown；
5. 触发 `_compress_context(...)`；
6. 压缩后重置 empty response / thinking prefill 等恢复状态。

### 7.2 pre-API pressure compression

一轮内部可能发生多次工具调用。刚进 turn 时没爆，不代表工具结果追加后不爆。

因此 [conversation_loop.py:978-1009](../../../submodules/hermes-agent/agent/conversation_loop.py#L978-L1009) 在每次 API call 前重新估算 request pressure。触发后 [conversation_loop.py:1024-1053](../../../submodules/hermes-agent/agent/conversation_loop.py#L1024-L1053) 会：

- 调用 `_compress_context(...)`；
- 重置 retry / empty-response 状态；
- 重新设置 conversation history flush cursor；
- refund iteration budget；
- `continue` 重新组装请求。

这说明 Hermes 的 compact 可能发生在 tool loop 中间，而不只是 turn 边界。

### 7.3 provider context overflow 后的分类恢复

如果 provider 已经报 context-length error，Hermes 还会继续分类。

[conversation_loop.py:3419-3428](../../../submodules/hermes-agent/agent/conversation_loop.py#L3419-L3428) 明确区分：

```text
1. Prompt too long: input exceeds context window.
   Fix: reduce context_length + compress history.

2. max_tokens too large:
   input fits, but input_tokens + requested max_tokens > window.
   Fix: reduce max_tokens.
   Do NOT shrink context_length.
```

如果能解析出可用 output tokens，[conversation_loop.py:3429-3462](../../../submodules/hermes-agent/agent/conversation_loop.py#L3429-L3462) 会临时降低 output cap 再重试；如果确认是 output-cap error 但无法解析预算，[conversation_loop.py:3464-3503](../../../submodules/hermes-agent/agent/conversation_loop.py#L3464-L3503) 会直接提示用户降低 `model.max_tokens`，避免无意义压缩死循环。

如果确实是 input overflow，[conversation_loop.py:3505-3555](../../../submodules/hermes-agent/agent/conversation_loop.py#L3505-L3555) 才尝试从 provider error 中解析真实 context limit，更新 compressor，并进入压缩。

### 7.4 默认 compressor 算法

[context_compressor.py:662-671](../../../submodules/hermes-agent/agent/context_compressor.py#L662-L671) 的注释总结了默认算法：

```text
1. Prune old tool results
2. Protect head messages
3. Protect tail messages by token budget
4. Summarize middle turns with structured LLM prompt
5. On subsequent compactions, iteratively update previous summary
```

而 [conversation_compression.py:616-695](../../../submodules/hermes-agent/agent/conversation_compression.py#L616-L695) 还会：

- 在压缩前通知 memory provider `on_pre_compress(messages)`；
- 处理压缩 abort / summary failure；
- 添加 todo snapshot；
- invalidate 并 rebuild system prompt；
- 在 SessionDB 中 in-place compaction 或 session rotation。

> **精髓标记**：Hermes 的长上下文处理不是“爆了就 compact 一下”，而是 turn 开始前 preflight、API call 前 pressure check、provider overflow 后错误分类三层联动；同时区分 input overflow 和 output cap error，避免把所有 400 都误当成需要压缩历史。

## 8. 错误恢复：避免坏响应污染未来上下文

Hermes 的 context management 和 error recovery 紧密耦合。很多错误处理的目标不是“优雅报错”，而是防止坏消息进入持久上下文，或把错误转换成模型下一轮可理解的 observation。

### 8.1 thinking-only / empty response

[conversation_loop.py:4902-4934](../../../submodules/hermes-agent/agent/conversation_loop.py#L4902-L4934) 处理 thinking-only response：如果模型只有 reasoning 没有 visible content，Hermes 会把 assistant message 作为 incomplete prefill 追加进 `messages`，让下一轮模型继续输出文本。

如果是真的 empty response，[conversation_loop.py:4936-4963](../../../submodules/hermes-agent/agent/conversation_loop.py#L4936-L4963) 会最多重试 3 次。

重试后仍然空，[conversation_loop.py:4965-4995](../../../submodules/hermes-agent/agent/conversation_loop.py#L4965-L4995) 会尝试 fallback provider。

fallback 也失败时，[conversation_loop.py:4997-5014](../../../submodules/hermes-agent/agent/conversation_loop.py#L4997-L5014) 才追加 `(empty)` sentinel，并标记 `_empty_terminal_sentinel`，避免之后把这个失败哨兵当成正常 assistant 内容 replay。

### 8.2 hallucinated / invalid tool call

如果模型调用不存在的工具，[conversation_loop.py:4410-4418](../../../submodules/hermes-agent/agent/conversation_loop.py#L4410-L4418) 会先尝试 repair tool name。

repair 失败后，[conversation_loop.py:4422-4484](../../../submodules/hermes-agent/agent/conversation_loop.py#L4422-L4484) 不会立刻崩溃，而是：

1. 追加 assistant tool-call message；
2. 为 invalid tool call 追加一个 tool result；
3. tool result 中告诉模型 tool 不存在或 tool name 为空；
4. `continue`，让模型下一轮自修正。

超过 3 次才停止。

这和工具系统有关，也和上下文管理有关：错误被转换成 transcript 中的 observation，让模型有机会调整策略。

### 8.3 finalizer 收口：持久化前再修一次

[turn_finalizer.py:163-210](../../../submodules/hermes-agent/agent/turn_finalizer.py#L163-L210) 在 turn 结束持久化前还会：

- 删除 empty-response recovery scaffolding；
- 如果 interrupt 后最后一条是 tool result，则追加 synthetic assistant message 闭合 tool-call sequence；
- 如果用户已经看到 `final_response`，但 transcript 尾部不是 assistant，则追加 closing assistant row；
- 再 `_persist_session(...)`。

这体现了 Hermes 的一个底层目标：

> **不让本轮恢复路径里的临时脚手架、半截 tool sequence 或缺失 assistant closing row 污染下一轮可恢复的 durable transcript。**

## 9. 记忆同步：本轮结束后再沉淀，下一轮再预取

recall context 是“本轮临时参考资料”，那长期 memory 又什么时候更新？

turn finalizer 在 [turn_finalizer.py:462-468](../../../submodules/hermes-agent/agent/turn_finalizer.py#L462-L468) 调用：

```text
agent._sync_external_memory_for_turn(...)
```

具体实现见 [run_agent.py:3325-3383](../../../submodules/hermes-agent/run_agent.py#L3325-L3383)。它会在未被 interrupt 且有 final response 时：

```text
memory_manager.sync_all(user_text, response_text, messages=messages)
memory_manager.queue_prefetch_all(user_text, session_id=session_id)
```

其中：

- `sync_all` 把完成的 turn 同步给 external memory provider；
- `queue_prefetch_all` 在后台为下一轮预热；
- interrupted turn 会跳过，避免把用户没看到完成结果的 partial state 写进 memory；
- 整体 best-effort，memory provider 失败不能阻塞用户看到回答。

所以 Hermes 的 memory 相关上下文链路可以简化成：

```text
上一轮结束:
  final_response -> sync_all -> memory provider 持久化/更新
  user_text -> queue_prefetch_all -> 为下一轮预热

下一轮开始:
  user_message -> prefetch_all -> ext_prefetch_cache
  ext_prefetch_cache -> build_memory_context_block -> 注入当前 user API copy
```

这就是“长期记忆”进入当前模型输入的方式：不是每轮把所有记忆塞进 system prompt，而是 **按当前问题临时召回相关参考资料**。

## 10. 一次请求里 Hermes 塞给模型的东西

每次真正调用 provider 时，Hermes 的请求大致包含：

```text
api_messages = [
  {role: "system", content: cached_system_prompt + optional ephemeral_system_prompt},
  ...provider-repaired prior conversation messages,
  {role: "user", content: current_user_message + optional recall/plugin context},
]

tools = agent.tools
options = model / provider / base_url / api_mode / max_tokens / stream / middleware / fallback state / cache control ...
```

按来源拆开：

| 类别 | 来源 | 说明 |
|---|---|---|
| stable system prompt | `_cached_system_prompt` / SessionDB restore | 身份、工具指导、context files、memory snapshot、profile、model/provider 行；session 内尽量 byte-stable。 |
| optional ephemeral system prompt | `agent.ephemeral_system_prompt` | API-call-time 追加；不作为 SessionDB stable prompt 的主体。 |
| persistent messages | `conversation_history` + 本轮 `messages` | 真实 user / assistant / tool / recovery trajectory。 |
| recall context | `MemoryManager.prefetch_all(...)` | 临时小抄，追加到当前 user API copy，不持久化。 |
| plugin context | `pre_llm_call` hook | 同样追加到当前 user API copy。 |
| tools | `agent.tools` | 当前工具面，来自 toolsets / registry / MCP / plugin / memory provider 等装配。 |
| reasoning replay | assistant message reasoning fields | 按 provider 需要复制到 `reasoning_content` / `reasoning_details` 等字段。 |
| prompt cache controls | `apply_anthropic_cache_control(...)` | 给支持的 Claude / gateway 请求加 cache breakpoint。 |
| provider cleanup | sanitize / repair helpers | 删除 strict API 不接受的字段、修 role sequence / orphan tool results / JSON。 |

一句话：

> **Hermes 发给模型的不是原始 `messages`，而是“稳定 system prompt + 经修复的持久对话副本 + 本轮临时 recall/plugin 小抄 + 当前工具面”。**

## 11. 和 Claw-Code / OpenClaw 的横向对比

| 维度 | Claw-Code | OpenClaw | Hermes Agent |
|---|---|---|---|
| 上下文主容器 | `Session.messages` | `Agent.state.messages` / `AgentContext.messages` | `messages` working transcript + SessionDB history |
| system prompt | 启动 / REPL 初始化时构造，像项目快照 | AgentSession / extension 可参与调整 | session-stable cache prefix，DB restore，尽量 byte-stable |
| 请求前治理 | auto compact / Trident / provider conversion | `transformContext` + `convertToLlm` | provider repair/sanitize + memory/plugin injection + pressure compression |
| 临时上下文注入 | 主要靠用户输入 / 工具读取 / compact summary | transformContext 可注入 workspace / memory / extension context | recall/plugin context 追加到当前 user API copy |
| memory 角色 | 非核心长期记忆系统 | 可通过 transform / extension 接入 | 核心个人 Agent 能力，prefetch / sync / background review |
| streaming 与状态 | stream 到 CLI，最终构造 assistant message | partial assistant message 实时进入 AgentContext | streaming 异常 / scrubber / partial recovery 与 provider fallback 强耦合 |
| tool result | tool_result 回写 `Session.messages` | `ToolResultMessage` + tool execution events | tool message 回写 `messages`，错误也作为 observation 让模型自修正 |
| compaction | 本地 compact / Trident / context-window retry | AgentSession compaction entry + SessionManager rebuild | preflight + pre-API + overflow handler，多点压缩与 context engine |
| 核心气质 | 本地 CLI transcript 稳定重放 | 产品态实时会话状态机 | 多 provider 长会话生存修复管线 |

可以归纳为：

```text
Claw-Code 关注：如何让本地 CLI session 历史稳定延续。
OpenClaw 关注：如何让多端 Agent 产品状态实时演化并转换成模型输入。
Hermes 关注：如何让长期个人 Agent 在记忆、插件、多 provider、长上下文和错误恢复中继续活着。
```

## 12. 阶段性判断

Hermes Context Management 的第一轮结论：

> **Hermes 把上下文管理做成了长期个人 Agent 的运行韧性系统：system prompt 被稳定化为 session cache prefix；真实 messages 作为可持久化轨迹；memory/plugin recall context 作为本轮临时参考资料；API messages 则在每次请求前经过 provider-specific repair、sanitize、reasoning replay、压缩检查和 cache control。它的复杂度主要来自“多 provider + 长 session + 弱模型/路由器异常 + memory 演化”的组合压力。**

如果用比喻：

```text
Claw-Code 像本地施工日志：每轮把日志递回模型。
OpenClaw 像在线工单系统：状态流、UI、工具、持久化共用一条实时 transcript。
Hermes 像长期私人助理：有固定工作准则，有真实对话档案，会临时翻笔记，还会在工具坏了、provider 换了、历史太长时修补上下文继续干。
```

## QA / 讨论记录

### Q: Hermes 的 system prompt 是每轮都重新读取 / 构造吗？

> **状态**: verified
> **来源**: source-code / discussion

A: 不是。Hermes 在每轮 prologue 中只有当 `agent._cached_system_prompt is None` 时才调用 `_restore_or_build_system_prompt(...)`。如果 SessionDB 中已有可用且 model/provider 匹配的 stored prompt，就复用同一份 prompt；只有缺失、为 `NULL`、为空字符串或 runtime identity 不匹配时才重建。重建后会写回 SessionDB，避免后续 gateway / fresh-agent continuation 每轮都 cache miss。源码见 [turn_context.py:319-323](../../../submodules/hermes-agent/agent/turn_context.py#L319-L323) 和 [conversation_loop.py:277-399](../../../submodules/hermes-agent/agent/conversation_loop.py#L277-L399)。

### Q: 为什么说 Hermes 把 system prompt 当成 session-stable cache prefix？

> **状态**: verified
> **来源**: source-code / discussion

A: `build_system_prompt(...)` 的注释明确说它每个 session 调一次，并缓存到 `_cached_system_prompt`；Hermes 不在 session 中途重新 render 局部 prompt，以保持 upstream prompt cache 命中。即使 system prompt 内部有 memory snapshot、profile、timestamp 等看似 volatile 的内容，也是在 session prompt snapshot 中稳定下来。外部 recall context 和 plugin context 不注入 system prompt，而是追加到当前 user API copy，正是为了不破坏这个 stable cache prefix。

### Q: recall context 到底是什么？

> **状态**: verified
> **来源**: source-code / discussion

A: recall context 就是 Hermes 本轮临时找出来、贴到用户问题后面的“参考资料 / 小抄”。它通常来自 external memory provider 的 `prefetch_all(...)` 或 plugin `pre_llm_call` hook。模型本轮能看到它，但它不是新用户输入、不是 system prompt，也不会写入持久聊天历史。源码上，`prefetch_all` 在 [turn_context.py:514-520](../../../submodules/hermes-agent/agent/turn_context.py#L514-L520) 取回，随后 [conversation_loop.py:786-803](../../../submodules/hermes-agent/agent/conversation_loop.py#L786-L803) 把它追加到当前 user message 的 API copy。

### Q: recall context 和 compact summary 有什么区别？

> **状态**: verified
> **来源**: source-code / discussion

A: compact summary 是把旧对话压缩后形成的历史摘要，会进入可持续使用的上下文 / session 重建路径；recall context 是本轮按当前问题临时检索出的相关资料，只追加到 `api_messages` 的当前 user copy，不改 `messages`，也不持久化。简单说：compact summary 是“旧历史压缩后的新历史”，recall context 是“这次临时翻出来的小抄”。

### Q: 为什么 recall context 不放进 system prompt？

> **状态**: verified
> **来源**: source-code / discussion

A: 因为 Hermes 要让 system prompt 作为 session-stable cache prefix 复用。每轮把 memory / plugin 动态内容塞进 system prompt，会导致 prompt cache 前缀变化，也会混淆“规则”和“参考资料”的语义。源码 [conversation_loop.py:827-835](../../../submodules/hermes-agent/agent/conversation_loop.py#L827-L835) 明确写到 external recall context 和 plugin context 注入 user message，而不是 system prompt。

### Q: Hermes 的 `messages` 和 `api_messages` 有什么区别？

> **状态**: verified
> **来源**: source-code / discussion

A: `messages` 是 Hermes 内部 working transcript，会追加 user / assistant / tool / recovery messages，并用于 session persistence。`api_messages` 是每次 API call 前从 `messages` 拷贝出来、经过 repair / sanitize / recall injection / provider adaptation 后的临时请求副本。很多改写只发生在 `api_messages` 上，例如 recall context 注入、strict provider 字段清理、thinking-only turn drop、orphan tool result sanitize，避免污染持久 transcript。

### Q: Hermes 的上下文压缩和 Claw-Code compact 有什么不同？

> **状态**: draft
> **来源**: source-code / discussion

A: Claw-Code 的 compact 更像本地 CLI session 的历史压缩：auto compact、manual `/compact` / Trident、context-window retry 都围绕 `Session.messages`。Hermes 的压缩更像长期个人 Agent 的多点防爆：turn 开始前 preflight，API call 前 pressure check，provider context overflow 后还要区分 input overflow 和 output cap error；压缩过程还会通知 memory provider、处理 summary failure / cooldown、更新 context length、重建 cached system prompt，并可能对 SessionDB 做 in-place compaction 或 session rotation。

### Q: 为什么说 Hermes 的 context management 是“生存修复管线”？

> **状态**: verified
> **来源**: source-code / discussion

A: 因为 Hermes 面向多 provider / 开源模型 / router / 长会话环境，消息历史经常会出现 provider 不接受的字段、损坏的 tool_call JSON、role alternation 违规、orphan tool result、thinking-only assistant turn、surrogate unicode、empty response、partial stream、context overflow 等问题。Hermes 在每次 API call 前和每次错误后都尝试修复、压缩、重试或 fallback，让会话尽量继续，而不是一次异常就终止。

### Q: Hermes 和 OpenClaw 都有运行中用户引导，context 注入方式一样吗？

> **状态**: draft
> **来源**: source-code / discussion

A: 不一样。OpenClaw 把运行中输入拆成 `steer` / `followUp` 队列，并作为 AgentMessage 进入 `AgentContext.messages`；Hermes 的 `steer` 更偏工具循环中的软引导，通常暂存后追加到 tool result 中，避免破坏 tool-calling 协议的 role / tool_result 对齐。Hermes 的 recall context 又是另一类东西：它不是用户实时 steer，而是 memory/plugin 临时参考资料，追加到当前 user API copy，不进入持久 messages。
