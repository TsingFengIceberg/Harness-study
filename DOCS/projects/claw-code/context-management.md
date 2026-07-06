# Claw-Code Context Management：本地 CLI Agent 的上下文组装、消息历史与压缩

> **日期**: 2026-07-06 | **状态**: draft | **涉及版本**: `4ea31c1bc91c4e9bcbd67d51c550c01e127e6d0d`

## 相关文档

- 项目入口：[README.md](README.md)
- Agent Loop：[agent-loop.md](agent-loop.md)
- Tool System：[tool-system.md](tool-system.md)
- 横向 Agent Loop 总结：[agent-loop.md](../../comparison/agent-loop.md)
- 横向 Tool System 总结：[tool-system.md](../../comparison/tool-system.md)

## 源码入口

| 模块 | 源码 | 作用 |
|---|---|---|
| Prompt 构建 | [prompt.rs](../../../submodules/claw-code/rust/crates/runtime/src/prompt.rs) | `SystemPromptBuilder`、`ProjectContext`、项目指令文件发现、git status / diff 快照、runtime config 注入。 |
| Session / Message | [session.rs](../../../submodules/claw-code/rust/crates/runtime/src/session.rs) | `Session`、`ConversationMessage`、`ContentBlock`、message JSONL 持久化、prompt history、fork / compaction metadata。 |
| Runtime loop | [conversation.rs](../../../submodules/claw-code/rust/crates/runtime/src/conversation.rs) | `ApiRequest`、`ConversationRuntime::run_turn`、assistant stream 转 message、tool result 写回、usage 与自动压缩触发。 |
| 基础压缩 | [compact.rs](../../../submodules/claw-code/rust/crates/runtime/src/compact.rs) | 本地启发式 summary compaction：估算 token、保留最近消息、避免切断 tool_use / tool_result 配对。 |
| Trident 压缩 | [trident.rs](../../../submodules/claw-code/rust/crates/runtime/src/trident.rs) | `/compact` 和上下文溢出重试使用的三阶段压缩 pipeline：supersede / collapse / cluster。 |
| CLI wiring | [main.rs](../../../submodules/claw-code/rust/crates/rusty-claude-cli/src/main.rs) | `build_system_prompt`、`build_runtime`、`AnthropicRuntimeClient::stream`、`convert_messages`、REPL prompt history 与 context-window retry。 |

## 1. 核心结论

Claw-Code 的 Context Management 不是一个单独的 `Context` 对象，而是由两条上下文通道拼起来：

```text
System prompt channel
  prompt.rs -> SystemPromptBuilder -> Vec<String>
  包含静态行为规则、环境信息、项目指令、git 快照、runtime config

Conversation history channel
  session.rs -> Session.messages -> Vec<ConversationMessage>
  包含用户输入、assistant 文本 / thinking / tool_use、tool_result、压缩摘要 message
```

每次模型调用前，[conversation.rs](../../../submodules/claw-code/rust/crates/runtime/src/conversation.rs) 会组装：

```text
ApiRequest {
  system_prompt: self.system_prompt.clone(),
  messages: self.session.messages.clone(),
}
```

对应代码见 [conversation.rs:364-367](../../../submodules/claw-code/rust/crates/runtime/src/conversation.rs#L364-L367)。

因此最短链路是：

```text
用户输入
  -> Session.push_user_text
  -> ApiRequest(system_prompt + session.messages)
  -> provider client convert_messages
  -> assistant stream
  -> ConversationMessage::assistant_with_usage
  -> Session.push_message
  -> tool_result 写回 Session
  -> 下一轮继续把 Session.messages 发给模型
```

可以把 Claw-Code 的上下文系统概括为：

> **本地系统提示快照 + Session 消息日志 + 本地启发式压缩。**

它不像 OpenHands 那样以平台事件流为核心，也不像 Hermes 那样以长期 memory 为核心；Claw-Code 更像本地 CLI runtime：把系统提示、项目指令、历史消息、工具轨迹和压缩摘要都收敛到单机 `ConversationRuntime` / `Session` 里。

## 2. System Prompt：静态骨架 + 动态项目上下文

Prompt 构建集中在 [prompt.rs](../../../submodules/claw-code/rust/crates/runtime/src/prompt.rs)。核心对象是：

- `ProjectContext`：[prompt.rs:84-93](../../../submodules/claw-code/rust/crates/runtime/src/prompt.rs#L84-L93)
- `SystemPromptBuilder`：[prompt.rs:153-164](../../../submodules/claw-code/rust/crates/runtime/src/prompt.rs#L153-L164)
- `SystemPromptBuilder::build()`：[prompt.rs:211-233](../../../submodules/claw-code/rust/crates/runtime/src/prompt.rs#L211-L233)
- `load_system_prompt_with_context(...)`：[prompt.rs:635-653](../../../submodules/claw-code/rust/crates/runtime/src/prompt.rs#L635-L653)

`SystemPromptBuilder::build()` 的顺序大致是：

```text
simple intro
  -> output style（可选）
  -> system rules
  -> doing tasks
  -> executing actions with care
  -> SYSTEM_PROMPT_DYNAMIC_BOUNDARY
  -> environment section
  -> project context
  -> project instruction files
  -> runtime config
  -> append sections
```

`SYSTEM_PROMPT_DYNAMIC_BOUNDARY` 定义在 [prompt.rs:39-45](../../../submodules/claw-code/rust/crates/runtime/src/prompt.rs#L39-L45)，用于区分静态 prompt scaffolding 和动态 runtime context。结合 CLI 侧 Anthropic prompt cache 初始化（[main.rs:12573-12583](../../../submodules/claw-code/rust/crates/rusty-claude-cli/src/main.rs#L12573-L12583)），可以理解为：Claw-Code 希望稳定部分利于 prompt cache，动态部分承载当前项目状态。

### ProjectContext 注入什么

`ProjectContext` 包括：

```text
cwd
current_date
git_status
git_diff
git_context
instruction_files
```

`discover_with_git(...)` 会读取 git status、git diff 和 git context，见 [prompt.rs:129-138](../../../submodules/claw-code/rust/crates/runtime/src/prompt.rs#L129-L138)。具体渲染在 [render_project_context](../../../submodules/claw-code/rust/crates/runtime/src/prompt.rs#L477-L517)：

- 日期与工作目录；
- 已发现的 project instruction 文件数量；
- `git status --short --branch` 快照；
- 最近提交；
- staged / unstaged diff 快照；
- 额外 git context。

`git diff` 有最大字符限制，`MAX_GIT_DIFF_CHARS = 50_000`，超过后会追加 `... [diff truncated — too large for system prompt]`，见 [prompt.rs:43-45](../../../submodules/claw-code/rust/crates/runtime/src/prompt.rs#L43-L45) 和 [prompt.rs:433-463](../../../submodules/claw-code/rust/crates/runtime/src/prompt.rs#L433-L463)。

### Project instruction 文件发现规则

项目指令文件发现入口是 [discover_instruction_files](../../../submodules/claw-code/rust/crates/runtime/src/prompt.rs#L289-L314)。它从当前目录向上走到最近 git root，收集：

```text
CLAUDE.md
CLAW.md
AGENTS.md
CLAUDE.local.md
.claw/CLAUDE.md
.claude/CLAUDE.md
.claw/instructions.md
.claw/rules/*.{md,txt,mdc}
.claw/rules.local/*.{md,txt,mdc}
```

并可导入其他生态的规则文件，例如 `.cursorrules`、`.github/copilot-instructions.md`、`.windsurfrules`、`.plandex/instructions.md`、`.crush/CLAUDE.md` 等，见 [prompt.rs:389-413](../../../submodules/claw-code/rust/crates/runtime/src/prompt.rs#L389-L413)。

指令内容还有两个预算：

- 单个 instruction file 最大 `MAX_INSTRUCTION_FILE_CHARS = 4_000`；
- 所有 instruction 总量最大 `MAX_TOTAL_INSTRUCTION_CHARS = 12_000`；

相关逻辑在 [render_instruction_files](../../../submodules/claw-code/rust/crates/runtime/src/prompt.rs#L519-L540) 和 [truncate_instruction_content](../../../submodules/claw-code/rust/crates/runtime/src/prompt.rs#L582-L591)。

这说明 Claw-Code 的“项目记忆”首先不是长期 memory，而是类似 Claude Code 的本地 instruction 文件 + git snapshot 注入。

## 3. System prompt 的生命周期：REPL 中不是每轮重新 discover

CLI 侧 [build_system_prompt](../../../submodules/claw-code/rust/crates/rusty-claude-cli/src/main.rs#L11873-L11880) 调用 `load_system_prompt(...)`。

在交互式 REPL 初始化时，[LiveCli::new](../../../submodules/claw-code/rust/crates/rusty-claude-cli/src/main.rs#L7628-L7660) 会：

```text
build_system_prompt(model)
new_cli_session()
build_runtime(..., system_prompt.clone(), ...)
把 system_prompt 存在 LiveCli 上
```

后续每一轮 [prepare_turn_runtime](../../../submodules/claw-code/rust/crates/rusty-claude-cli/src/main.rs#L7723-L7740) 是用 `self.system_prompt.clone()` 重新构造 runtime，而不是每轮重新从 [prompt.rs](../../../submodules/claw-code/rust/crates/runtime/src/prompt.rs) 读取 instruction 文件和 git diff。

这意味着：

- one-shot CLI 每次启动都会构造新的 system prompt；
- REPL 内的基础 system prompt 是启动时快照，后续 turn 主要靠 `Session.messages` 延续；
- `/status`、`/diff` 等命令可以显示当前工作区状态，但不等同于每轮自动刷新 system prompt。

这个设计符合本地 CLI 的简单性：启动时抓一份项目上下文，之后靠工具调用和 session history 更新模型视野。

> **精髓标记**：REPL 里的 system prompt 更像“启动时项目快照”，不是每一轮实时项目状态。启动时的 git diff / instruction files 会进入顶层 system prompt，但后续工作区变化不一定自动刷新；模型如果要知道最新文件内容、最新 diff 或最新状态，需要通过工具显式读取。

## 4. Session：模型上下文的主历史日志

Session 定义在 [session.rs](../../../submodules/claw-code/rust/crates/runtime/src/session.rs)。核心结构包括：

- `MessageRole`：[session.rs:22-29](../../../submodules/claw-code/rust/crates/runtime/src/session.rs#L22-L29)
- `ContentBlock`：[session.rs:31-52](../../../submodules/claw-code/rust/crates/runtime/src/session.rs#L31-L52)
- `ConversationMessage`：[session.rs:54-60](../../../submodules/claw-code/rust/crates/runtime/src/session.rs#L54-L60)
- `Session`：[session.rs:117-133](../../../submodules/claw-code/rust/crates/runtime/src/session.rs#L117-L133)

`Session.messages` 承载真正会进入模型上下文的对话历史：

```text
ConversationMessage
  role: System | User | Assistant | Tool
  blocks:
    Text
    Thinking
    ToolUse
    ToolResult
  usage: Option<TokenUsage>
```

常用构造函数见 [session.rs:711-755](../../../submodules/claw-code/rust/crates/runtime/src/session.rs#L711-L755)：

- `ConversationMessage::user_text(...)`
- `ConversationMessage::assistant(...)`
- `ConversationMessage::assistant_with_usage(...)`
- `ConversationMessage::tool_result(...)`

`push_message(...)` 是 session 追加消息的主入口，见 [session.rs:279-292](../../../submodules/claw-code/rust/crates/runtime/src/session.rs#L279-L292)。它会先更新内存中的 `messages`，再追加持久化；如果持久化失败，会把刚 push 的 message 回滚掉。这说明 Claw-Code 把 session history 当作一份可持久化的本地运行状态，而不只是内存里的 prompt buffer。

### `Session.messages` 的细粒度组成

细看 `Session.messages`，它不是纯文本聊天记录，而是一串结构化 transcript：

```text
Session.messages: Vec<ConversationMessage>

ConversationMessage {
  role: MessageRole,
  blocks: Vec<ContentBlock>,
  usage: Option<TokenUsage>,
}
```

`role` 决定这一条消息在内部语义上是谁说的：

| Role | 内部语义 | 是否随 messages 进入模型 | 备注 |
|---|---|---|---|
| `System` | session 内部系统类消息，主要用于 compact continuation summary | 是 | provider conversion 中映射成 `user` role，不是顶层 system prompt。 |
| `User` | 用户输入 | 是 | 当前输入会先追加为 `ConversationMessage::user_text(...)`。 |
| `Assistant` | 模型输出 | 是 | 可包含普通文本、thinking、tool_use。 |
| `Tool` | 工具执行结果 | 是 | 通过 `ToolResult` block 回写给下一轮模型。 |

`blocks` 决定这一条 message 里具体有什么内容：

| Block | 字段 | 典型含义 |
|---|---|---|
| `Text` | `text` | 用户自然语言、assistant 普通回复、compact summary 文本。 |
| `Thinking` | `thinking` / `signature` | provider 返回的 reasoning / thinking 内容，后续会随上下文 replay。 |
| `ToolUse` | `id` / `name` / `input` | assistant 请求调用某个工具。 |
| `ToolResult` | `tool_use_id` / `tool_name` / `output` / `is_error` | 工具执行结果或拒绝 / 错误结果。 |

所以动态对话上下文里会有附近几轮完整对话，但来源不是 `prompt_history`，而是这些 `ConversationMessage`：

```text
User(Text)
Assistant(Text + ToolUse)
Tool(ToolResult)
Assistant(Text + ToolUse)
Tool(ToolResult)
User(Text)
...
```

不直接进入 `Session.messages` 的内容也要区分清楚：`prompt_history`、`session_id`、`created_at_ms` / `updated_at_ms`、`workspace_root`、`fork` metadata、`persistence_path` 等是 session 管理元数据或 CLI 辅助信息；真正随请求发给模型的是 `Session.messages` 本身。


## 5. Prompt history 不是模型上下文主源

`Session` 里还有 `prompt_history`，见 [session.rs:126](../../../submodules/claw-code/rust/crates/runtime/src/session.rs#L126)。CLI 在 REPL 读到用户输入后，会先记录 prompt history，再调用 `run_turn`，见 [main.rs:7080-7103](../../../submodules/claw-code/rust/crates/rusty-claude-cli/src/main.rs#L7080-L7103)。

记录逻辑在 [LiveCli::record_prompt_history](../../../submodules/claw-code/rust/crates/rusty-claude-cli/src/main.rs#L8283-L8298)：

```text
prompt_history.push(entry)
runtime.session_mut().push_prompt_entry(prompt)
```

但模型请求实际发送的是 `Session.messages`，不是 `prompt_history`。`prompt_history` 更像 CLI 辅助功能，用于 `/history` / prompt 历史展示；真正进入模型上下文的是随后 [run_turn](../../../submodules/claw-code/rust/crates/runtime/src/conversation.rs#L325-L531) 中追加的 `ConversationMessage::user_text(...)`。

因此，“prompt_history 不进模型上下文”不等于“模型看不到附近几轮对话”。模型能看到的是 `Session.messages` 里的完整对话日志：前几次用户输入、assistant 文本、thinking、tool_use 和 tool_result 都会作为 message history 传给 provider。只有当 session 被 compact 后，较早消息才会被一条 continuation summary 替换，最近若干条消息仍按 `preserve_recent_messages` 规则原样保留。

## 6. run_turn：每轮如何把历史交给模型

[ConversationRuntime::run_turn](../../../submodules/claw-code/rust/crates/runtime/src/conversation.rs#L325-L531) 是上下文进入模型的主入口。关键步骤：

```text
1. 用户输入 -> self.session.push_user_text(user_input)
2. loop iteration 开始
3. ApiRequest { system_prompt, messages }
4. api_client.stream(request)
5. streamed events -> assistant ConversationMessage
6. assistant message 写回 Session
7. maybe_auto_compact()
8. 如果没有 tool_use：结束本 turn
9. 如果有 tool_use：执行工具，tool_result 写回 Session
10. 下一轮模型调用看到更新后的 Session.messages
```

对应源码：

- 用户输入写入：[conversation.rs:343-347](../../../submodules/claw-code/rust/crates/runtime/src/conversation.rs#L343-L347)
- 构造 API 请求：[conversation.rs:364-367](../../../submodules/claw-code/rust/crates/runtime/src/conversation.rs#L364-L367)
- assistant stream 转 message：[conversation.rs:375-386](../../../submodules/claw-code/rust/crates/runtime/src/conversation.rs#L375-L386)
- 提取 pending tool use：[conversation.rs:387-396](../../../submodules/claw-code/rust/crates/runtime/src/conversation.rs#L387-L396)
- assistant message 写回：[conversation.rs:403-406](../../../submodules/claw-code/rust/crates/runtime/src/conversation.rs#L403-L406)
- auto compact 检查：[conversation.rs:408-412](../../../submodules/claw-code/rust/crates/runtime/src/conversation.rs#L408-L412)
- tool_result 写回：[conversation.rs:503-516](../../../submodules/claw-code/rust/crates/runtime/src/conversation.rs#L503-L516)

这个顺序有一个细节：`maybe_auto_compact()` 在 assistant message 写回后运行，而且即使本轮没有 tool use 也会检查，注释说明是为了避免 terminal no-tool iteration 后 session 无界增长，见 [conversation.rs:408-410](../../../submodules/claw-code/rust/crates/runtime/src/conversation.rs#L408-L410)。

## 7. Provider conversion：内部 message 如何变成 API message

Runtime 抽象里的 [ApiRequest](../../../submodules/claw-code/rust/crates/runtime/src/conversation.rs#L21-L26) 只有：

```text
system_prompt: Vec<String>
messages: Vec<ConversationMessage>
```

真正转成 provider 请求发生在 CLI 侧 [AnthropicRuntimeClient::stream](../../../submodules/claw-code/rust/crates/rusty-claude-cli/src/main.rs#L12627-L12646)：

```text
MessageRequest {
  model,
  max_tokens,
  messages: convert_messages(&request.messages),
  system: request.system_prompt.join("\n\n"),
  tools,
  tool_choice,
  stream: true,
  reasoning_effort,
}
```

`convert_messages(...)` 位于 [main.rs:14000-14052](../../../submodules/claw-code/rust/crates/rusty-claude-cli/src/main.rs#L14000-L14052)。它有几个关键点：

| 内部表示 | Provider message 表示 |
|---|---|
| `MessageRole::Assistant` | role = `assistant` |
| `MessageRole::System` | role = `user` |
| `MessageRole::User` | role = `user` |
| `MessageRole::Tool` | role = `user` |
| `ContentBlock::Text` | text block |
| `ContentBlock::Thinking` | thinking / reasoning block |
| `ContentBlock::ToolUse` | tool_use block |
| `ContentBlock::ToolResult` | tool_result block |

这里需要区分两个“system”：

1. 顶层 system prompt：来自 [prompt.rs](../../../submodules/claw-code/rust/crates/runtime/src/prompt.rs)，通过 `MessageRequest.system` 发送；
2. `Session.messages` 中的 `MessageRole::System`：主要用于 compaction continuation summary，在 provider message 中被映射成 `user` role。

这和 Anthropic 风格 tool result 在 user 消息中回传的模型协议相匹配，也避免把压缩摘要误当成新的顶层 system prompt。

> **精髓标记**：compact summary 本质上是“这段对话历史的摘要”，不是新的系统规则。把它放在 `Session.messages` 里并映射成 user-like context，可以让模型知道历史发生过什么；如果把它提升成真正的顶层 system prompt，可能会改变权限层级、规则优先级或 provider 语义。

此外，`ContentBlock::Thinking` 会被保留并回传，源码注释说明这是为了兼容 OpenAI-compatible / DeepSeek V4 的 reasoning content replay 要求，见 [main.rs:14015-14024](../../../submodules/claw-code/rust/crates/rusty-claude-cli/src/main.rs#L14015-L14024)。

## 8. 一次请求里 Claw-Code 塞给模型的东西

把上面的链路压缩成“单次 provider 请求清单”，一次模型请求主要包含：

| 类别 | 来源 | 进入 provider request 的位置 | 说明 |
|---|---|---|---|
| 模型名 / max tokens | CLI model 配置 | `MessageRequest.model` / `max_tokens` | 由 [AnthropicRuntimeClient::stream](../../../submodules/claw-code/rust/crates/rusty-claude-cli/src/main.rs#L12633-L12646) 设置。 |
| 顶层 system prompt | [prompt.rs](../../../submodules/claw-code/rust/crates/runtime/src/prompt.rs) 构造出的 `Vec<String>` | `MessageRequest.system` | 身份、行为规则、环境、项目指令、git 快照、runtime config。 |
| 历史 messages | `Session.messages` | `MessageRequest.messages` | 用户输入、assistant 输出、thinking、tool_use、tool_result、compact summary。 |
| 当前用户输入 | `run_turn(user_input)` | 先追加到 `Session.messages`，再随 messages 发出 | 见 [conversation.rs:343-367](../../../submodules/claw-code/rust/crates/runtime/src/conversation.rs#L343-L367)。 |
| 工具定义 | `GlobalToolRegistry` + allowed tools | `MessageRequest.tools` | 只在 `enable_tools` 时发送，且会受 allowed tools 过滤。 |
| tool choice | CLI/runtime 配置 | `MessageRequest.tool_choice` | 启用工具时是 auto。 |
| reasoning effort | runtime client 设置 | `MessageRequest.reasoning_effort` | 可选。 |
| prompt cache | Anthropic client session cache | provider client 内部行为 | Anthropic 路径会用 `PromptCache::new(session_id)`，见 [main.rs:12573-12583](../../../submodules/claw-code/rust/crates/rusty-claude-cli/src/main.rs#L12573-L12583)。 |

用伪结构表示：

```text
MessageRequest {
  model,
  max_tokens,
  system: join(system_prompt),
  messages: convert_messages(Session.messages),
  tools: filtered tool definitions,
  tool_choice: auto,
  stream: true,
  reasoning_effort,
}
```

注意：`prompt_history` 不在这个请求结构里；它只是 CLI 历史记录。附近几轮对话之所以会被模型看到，是因为它们已经写进了 `Session.messages`。

## 9. Usage 与自动压缩触发

Token usage 定义在 [usage.rs](../../../submodules/claw-code/rust/crates/runtime/src/usage.rs)：

```text
TokenUsage {
  input_tokens,
  output_tokens,
  cache_creation_input_tokens,
  cache_read_input_tokens,
}
```

`UsageTracker::from_session(...)` 会从历史 assistant messages 的 `usage` 字段恢复累计 usage，见 [usage.rs:181-190](../../../submodules/claw-code/rust/crates/runtime/src/usage.rs#L181-L190)。每轮收到 provider usage 后，`ConversationRuntime` 调用 `usage_tracker.record(usage)`，见 [conversation.rs:383-385](../../../submodules/claw-code/rust/crates/runtime/src/conversation.rs#L383-L385)。

自动压缩阈值在 [conversation.rs:18-19](../../../submodules/claw-code/rust/crates/runtime/src/conversation.rs#L18-L19)：

```text
DEFAULT_AUTO_COMPACTION_INPUT_TOKENS_THRESHOLD = 100_000
CLAUDE_CODE_AUTO_COMPACT_INPUT_TOKENS
```

解析逻辑见 [conversation.rs:704-720](../../../submodules/claw-code/rust/crates/runtime/src/conversation.rs#L704-L720)。

`maybe_auto_compact()` 的判断是：

```text
if cumulative_usage.input_tokens < threshold:
    不压缩
else:
    compact_session(max_estimated_tokens=0, preserve_recent_messages=4)
    如果 removed_message_count > 0，替换 self.session
```

源码见 [conversation.rs:571-594](../../../submodules/claw-code/rust/crates/runtime/src/conversation.rs#L571-L594)。

注意这里用的是 provider 返回的累计 input token 触发阈值；真正压缩时用 [compact.rs](../../../submodules/claw-code/rust/crates/runtime/src/compact.rs) 的本地启发式逻辑，不是调用模型重新总结。

### 自动 compact：高频检查，不是从一开始高频压缩

这里容易产生一个误解：Claw-Code 并不是“每一轮都小幅压缩一点”。更准确的说法是：

```text
每轮 assistant message 写回后都会检查 maybe_auto_compact
  -> 累计 input tokens 未达到阈值：不压缩
  -> 达到阈值后：开始把保留窗口之外的旧消息滚入 summary
```

也就是说，前期它是高频检查但不压缩；超过 `DEFAULT_AUTO_COMPACTION_INPUT_TOKENS_THRESHOLD` 后，因为 `UsageTracker` 的累计 input tokens 不会因压缩而归零，后续每轮仍会满足阈值条件。此时如果 compact summary 后面的消息又超过 `preserve_recent_messages`，就会继续把更早一段消息合并进已有 summary。

可以把它理解成：

> **达到 usage 阈值前，Claw-Code 保留完整 `Session.messages`；达到阈值后，进入滚动式 compact 状态，持续把最近窗口之外的旧消息压进 continuation summary。**

这和用户主动 `/compact` 或 context-window error 后的救火式压缩不是一回事。

### 三种 compact 的区别

| 类型 | 触发方式 | 使用算法 | 激进程度 | 目标 |
|---|---|---|---|---|
| 自动 compact | 运行中 usage 超阈值后自动 | 基础 `compact_session(...)` | 中等 | 预防 session 无界增长，维持可继续对话。 |
| 手动 `/compact` | 用户主动命令 | Trident + `compact_session(...)` | 较强 | 主动整理当前 session，把历史压瘦。 |
| context-window retry compact | provider 请求已失败 | Trident + progressive preserve `[4, 2, 1, 0]` | 最强 | 救回已经塞不进模型窗口的请求。 |

所以“整体 compact”更像用户显式整理或错误恢复；自动 compact 更像 runtime 在长会话里的滚动维护机制。


## 10. compact.rs：本地启发式 summary compaction

基础压缩配置在 [compact.rs:8-21](../../../submodules/claw-code/rust/crates/runtime/src/compact.rs#L8-L21)：

```text
preserve_recent_messages: 4
max_estimated_tokens: 10_000
```

`estimate_session_tokens(...)` 和 `should_compact(...)` 位于 [compact.rs:33-51](../../../submodules/claw-code/rust/crates/runtime/src/compact.rs#L33-L51)。估算方式在 [compact.rs:458-474](../../../submodules/claw-code/rust/crates/runtime/src/compact.rs#L458-L474)，基本是按字符串长度粗估：

```text
Text: text.len() / 4 + 1
ToolUse: (name.len() + input.len()) / 4 + 1
ToolResult: (tool_name.len() + output.len()) / 4 + 1
Thinking: thinking.len() / 4 + signature estimate
```

`compact_session(...)` 位于 [compact.rs:94-191](../../../submodules/claw-code/rust/crates/runtime/src/compact.rs#L94-L191)，核心策略是：

```text
1. 如果不满足 should_compact，原样返回
2. 如果已有 compact summary，识别第一条 system summary
3. 计算要保留的最近 N 条消息
4. 调整边界，避免保留区以孤立 tool_result 开头
5. 对被移除消息做本地 summary
6. 合并已有 summary 与新 summary
7. 创建一条 MessageRole::System continuation message
8. system summary + preserved tail 组成新的 Session.messages
9. record_compaction(summary, removed_message_count)
```

避免切断 `tool_use / tool_result` 配对是这里非常重要的工程细节。相关逻辑在 [compact.rs:123-166](../../../submodules/claw-code/rust/crates/runtime/src/compact.rs#L123-L166)：如果保留区第一条消息是 `ToolResult`，会向前移动边界，尽量把对应 assistant `ToolUse` 一起保留，避免 OpenAI-compatible provider 报 “tool message must follow assistant with tool_calls” 之类错误。

### Summary 内容怎么生成

`summarize_messages(...)` 位于 [compact.rs:203-287](../../../submodules/claw-code/rust/crates/runtime/src/compact.rs#L203-L287)。它不是 LLM 摘要，而是本地规则拼接，包含：

- 被压缩消息数量；
- user / assistant / tool 消息数量；
- 涉及过的工具名；
- 最近用户请求；
- 推断出的 pending work；
- 关键文件路径；
- 当前工作；
- key timeline。

关键文件提取和当前工作推断见 [compact.rs:386-447](../../../submodules/claw-code/rust/crates/runtime/src/compact.rs#L386-L447)。已有 summary 再次压缩时会通过 `merge_compact_summaries(...)` 合并，避免不断嵌套 `Previously compacted context` 导致 summary 递归膨胀，见 [compact.rs:290-325](../../../submodules/claw-code/rust/crates/runtime/src/compact.rs#L290-L325)。

最终 continuation message 文案由 [get_compact_continuation_message](../../../submodules/claw-code/rust/crates/runtime/src/compact.rs#L70-L92) 生成，包含：

```text
This session is being continued from a previous conversation that ran out of context...
Summary: ...
Recent messages are preserved verbatim.
Continue the conversation from where it left off...
```

这和 Claude Code 常见的 compact continuation 体验非常接近，但源码显示 Claw-Code 当前是本地启发式摘要，不是专门发起一个 summarization LLM call。

## 11. Trident：手动 compact 和溢出重试的增强压缩

除了基础 [compact.rs](../../../submodules/claw-code/rust/crates/runtime/src/compact.rs)，还有 [trident.rs](../../../submodules/claw-code/rust/crates/runtime/src/trident.rs)。

`TridentConfig` 默认启用三阶段，见 [trident.rs:5-29](../../../submodules/claw-code/rust/crates/runtime/src/trident.rs#L5-L29)：

```text
supersede_enabled
collapse_enabled
cluster_enabled
collapse_threshold
cluster_min_size
cluster_similarity_threshold
max_file_operations
```

主入口 [trident_compact_session](../../../submodules/claw-code/rust/crates/runtime/src/trident.rs#L103-L160) 先做三阶段消息压缩，再调用标准 `compact_session(...)`：

```text
Stage 1: Supersede
  删除被后续 write/edit 覆盖的旧 read/write/edit 轨迹

Stage 2: Collapse
  把重复 / 连续模式消息折叠为 summary

Stage 3: Cluster
  聚类相似消息并压缩

最后：compact_session(summary + preserved tail)
```

从调用点看，Trident 主要用于：

- resume 命令里的 `/compact`：[main.rs:6499-6521](../../../submodules/claw-code/rust/crates/rusty-claude-cli/src/main.rs#L6499-L6521)
- REPL context-window 溢出后的 progressive retry：[main.rs:7864-7872](../../../submodules/claw-code/rust/crates/rusty-claude-cli/src/main.rs#L7864-L7872)

而 [ConversationRuntime::maybe_auto_compact](../../../submodules/claw-code/rust/crates/runtime/src/conversation.rs#L571-L594) 直接调用的是基础 `compact_session(...)`，不是 Trident pipeline。

## 12. Context-window 溢出恢复：逐步更激进地保留更少消息

在普通 `run_turn` 失败后，CLI 会检查错误字符串是否像 context-window overflow。相关逻辑在 [main.rs:7793-7835](../../../submodules/claw-code/rust/crates/rusty-claude-cli/src/main.rs#L7793-L7835)，覆盖：

```text
context_window
Context window
no parseable body
exceed_context_size
exceeds the available context size
context size has been exceeded
assistant stream produced no content
Failed to parse input at pos
error decoding response body
```

如果错误里能解析出 server context window，则把 auto-compaction threshold 调整为窗口的 70%，见 [main.rs:7835-7846](../../../submodules/claw-code/rust/crates/rusty-claude-cli/src/main.rs#L7835-L7846)。

然后进入最多 4 轮 progressive compaction，保留消息数量按：

```text
[4, 2, 1, 0]
```

逐步降低，见 [main.rs:7848-7856](../../../submodules/claw-code/rust/crates/rusty-claude-cli/src/main.rs#L7848-L7856)。每轮用 Trident + `compact_session` 压缩，再重建 runtime 调用 `run_turn(input, ...)` 重试，见 [main.rs:7892-7904](../../../submodules/claw-code/rust/crates/rusty-claude-cli/src/main.rs#L7892-L7904)。

这里体现了 Claw-Code 在上下文管理上的实用取舍：

> **平时靠 usage threshold 自动压缩；真遇到 provider context error 时，再用更激进的 Trident progressive retry。**



## 13. 一个例子：修复测试失败时上下文如何流转

假设用户在 Claw-Code REPL 里说：

```text
帮我修复 cargo test 的失败
```

### 阶段 0：启动时先构造顶层 system prompt

REPL 启动时，Claw-Code 会读取项目指令、当前 cwd、日期、git status、git diff 和 runtime config，形成顶层 `system_prompt`。这部分通过 `MessageRequest.system` 发给 provider。

这一步给模型的是“施工现场说明”：

```text
你是 coding agent
当前目录是 /repo
项目指令如下 ...
当前 git status 是 ...
当前 git diff 是 ...
工具可用，但要遵守权限 ...
```

### 阶段 1：当前用户输入写入 `Session.messages`

`run_turn` 先把用户输入追加为 user message：

```text
User(Text("帮我修复 cargo test 的失败"))
```

然后第一次模型请求包含：

```text
system: 启动时 system prompt
messages:
  - User: 帮我修复 cargo test 的失败
tools:
  - bash / read_file / edit_file / grep_search / ...
```

### 阶段 2：模型请求跑测试，tool_result 写回

模型可能返回：

```text
Assistant:
  Text("我先运行测试看看失败信息。")
  ToolUse bash({"command":"cargo test"})
```

Claw-Code 执行工具后，把结果写回：

```text
Tool:
  ToolResult bash("test_parse_config failed at src/config.rs:87 ...")
```

下一轮模型请求时，模型已经能看到：

```text
用户目标：修复 cargo test
assistant 决策：已经选择跑测试
环境反馈：测试失败点在 src/config.rs:87
```

### 阶段 3：模型读取文件、编辑文件、再跑测试

模型随后可能继续产生：

```text
Assistant ToolUse read_file({"path":"src/config.rs"})
Tool ToolResult read_file("源码内容...")
Assistant ToolUse edit_file({...})
Tool ToolResult edit_file("updated src/config.rs")
Assistant ToolUse bash({"command":"cargo test"})
Tool ToolResult bash("tests passed")
```

这些并不是一次性文本拼接，而是结构化 `ConversationMessage` / `ContentBlock`，会被持续追加到 `Session.messages`，下一轮模型就能基于完整工具轨迹继续推理。

### 阶段 4：会话变长后 compact

如果任务拖得很长，早期消息可能被压成 continuation summary：

```text
System(Text("
This session is being continued from a previous conversation that ran out of context.

Summary:
- User asked to fix cargo test failures.
- Initial failure was test_parse_config at src/config.rs:87.
- Tools mentioned: bash, read_file, edit_file.
- Key files referenced: src/config.rs, tests/config_test.rs.
- Current work: remaining clippy warning in src/config.rs.

Recent messages are preserved verbatim.
Continue the conversation from where it left off...
"))

Assistant / Tool / User 最近若干条原文
```

此时模型不再看到最早完整的 `cargo test` 全量输出，但会看到摘要和最近几条原始消息。compact 的价值就在这里：减少输入上下文体积，同时尽量保留任务连续性。

这个例子可以概括为：

```text
LLM 本身无状态；
Claw-Code 通过每轮重新发送 system_prompt + Session.messages + tools，制造出“连续工作的 Agent”效果。
```

## 14. 和 Agent Loop / Tool System 的关系

把前两篇笔记串起来看：

```text
Agent Loop 决定：什么时候调用模型、什么时候执行工具、什么时候结束。
Tool System 决定：模型能看到什么工具、工具怎么权限检查和执行。
Context Management 决定：每次调用模型时，模型看到什么历史、规则、项目状态和工具反馈。
```

在 Claw-Code 里三者并不是彼此独立的服务，而是在本地 runtime 里直接交织：

```text
prompt.rs
  -> system_prompt

session.rs
  -> messages / compaction / prompt_history / persistence

conversation.rs
  -> run_turn(system_prompt + messages)
  -> assistant message / tool result 写回
  -> usage / maybe_auto_compact

main.rs
  -> provider message conversion
  -> prompt cache / stream events
  -> context-window retry
```

这也是 Claw-Code 作为本地 CLI Harness 的典型风格：结构直接、边界清晰、实现集中，但 context 策略主要依赖本地启发式和 provider usage，而不是平台级 memory service 或复杂 state graph。

## 15. 阶段性判断

Claw-Code Context Management 的第一轮结论：

> **Claw-Code 把上下文管理做成“启动时构造 system prompt + Session 持久化消息日志 + 本地 compact summary + context-window retry”的组合。它的重点不是长期知识库，而是让本地 CLI Agent 在一个 session 内可靠地延续工具轨迹、压缩历史并从上下文溢出中恢复。**

如果用一句话记：

```text
Claw-Code 的 context 是本地会话日志，不是远程记忆系统；
压缩是本地摘要，不是平台事件回放；
恢复策略是够用优先，逐步牺牲历史细节换取继续运行。
```

## QA / 讨论记录

### Q: Claw-Code 每次模型调用前到底发什么上下文？

> **状态**: verified
> **来源**: source-code / discussion

A: 每次调用前，`ConversationRuntime::run_turn` 构造 `ApiRequest { system_prompt, messages }`。`system_prompt` 来自启动时构造的 `Vec<String>`；`messages` 是当前 `Session.messages` 的 clone。CLI 侧 `AnthropicRuntimeClient::stream` 再把 `system_prompt.join("\n\n")` 放进 provider request 的 `system` 字段，把 `Session.messages` 经 `convert_messages(...)` 转为 provider messages。

### Q: `prompt_history` 会进入模型上下文吗？

> **状态**: verified
> **来源**: source-code / discussion

A: 不直接进入。`prompt_history` 是 CLI 侧记录用户输入历史的辅助结构，用于 `/history` 和 session JSONL 记录。真正进入模型上下文的是 `Session.messages`，用户输入会在 `run_turn` 中通过 `push_user_text(...)` 变成 `ConversationMessage::user_text(...)`。

### Q: Claw-Code 的 compact 是调用 LLM 总结吗？

> **状态**: verified
> **来源**: source-code

A: 当前基础 `compact_session(...)` 不是 LLM 总结，而是本地启发式 summary：统计消息数量、工具名、近期请求、pending work、关键文件、当前工作和 timeline。Trident 也是本地三阶段压缩 pipeline，然后再调用基础 summary compaction。源码中没有在 compact 路径里发起单独 summarization LLM call。

### Q: 为什么 compact 要特别处理 tool_use / tool_result 边界？

> **状态**: verified
> **来源**: source-code

A: 如果压缩时把 assistant 的 `ToolUse` 删除了，却保留对应 `ToolResult`，OpenAI-compatible provider 可能会收到孤立的 tool role message，从而报错。`compact_session(...)` 在计算保留边界时会检查第一条保留消息是否是 `ToolResult`，必要时向前移动边界，把对应 assistant `ToolUse` 一起保留。

### Q: REPL 里 system prompt 会随着 git diff 每轮刷新吗？

> **状态**: draft
> **来源**: source-code / inference

A: 源码显示 `LiveCli::new` 初始化时调用 `build_system_prompt(...)`，后续 `prepare_turn_runtime(...)` 使用 `self.system_prompt.clone()` 构造每轮 runtime。因此 REPL 中的基础 system prompt 更像启动时快照，不是每一轮自动重新 discover instruction 文件和 git diff。后续模型视野主要依赖 `Session.messages` 和工具调用结果；实时状态可通过 `/status`、`/diff` 等命令显式查看。这个判断后续可结合 CLI 命令刷新 runtime 的其他路径继续复核。

### Q: Claw-Code 是不是一直小幅高频地 compact 前面对话？

> **状态**: verified
> **来源**: source-code / discussion

A: 更准确地说，是“高频检查，过阈值后滚动式 compact”。`maybe_auto_compact()` 在 assistant message 写回后检查，但只有累计 input tokens 达到阈值才会压缩。超过阈值后，因为累计 usage 不会因 compact 归零，后续如果保留窗口之外又积累了新消息，就会继续把旧消息合并进已有 summary。它不是从会话一开始就每轮小幅压缩。

### Q: 自动 compact、手动 `/compact` 和 context-window retry compact 有什么区别？

> **状态**: verified
> **来源**: source-code / discussion

A: 自动 compact 是运行中 usage 超阈值后的预防性维护，走基础 `compact_session(...)`；手动 `/compact` 是用户主动整理 session，走 Trident + summary compaction；context-window retry compact 是 provider 请求已经塞不进窗口后的救火流程，走 Trident 并按 `[4, 2, 1, 0]` 逐步减少保留消息，最激进。

### Q: `Session.messages` 细致包含哪些动态对话上下文？

> **状态**: verified
> **来源**: source-code / discussion

A: `Session.messages` 是 `Vec<ConversationMessage>`，每条 message 有 `role`、`blocks` 和可选 `usage`。`role` 包括 `System`、`User`、`Assistant`、`Tool`；`blocks` 包括 `Text`、`Thinking`、`ToolUse`、`ToolResult`。因此动态上下文里既有附近几轮用户 / assistant 文本，也有工具调用请求、工具结果、thinking replay 和 compact summary。`prompt_history`、session id、workspace root、fork metadata 等是 session 管理信息，不是主模型上下文。

### Q: 为什么说 LLM 本身无状态，Claw-Code 通过 `Session.messages` 制造连续工作的效果？

> **状态**: draft
> **来源**: discussion / source-code

A: 每次 provider 请求都是一次新的模型调用。Claw-Code 之所以能连续完成“跑测试 -> 读文件 -> 编辑 -> 再跑测试”的任务，是因为每轮都会把顶层 `system_prompt`、当前 `Session.messages` 和工具定义重新发给模型。工具输出一旦写成 `ToolResult` message，下一轮模型就能看到环境反馈并继续推理。compact 后，较早轨迹会变成 summary，最近消息仍尽量原样保留。

### Q: compact summary 为什么不应该放进真正顶层 system prompt？

> **状态**: verified
> **来源**: source-code / discussion

A: compact summary 是历史摘要，不是系统规则。源码中它以 `MessageRole::System` 存在于 `Session.messages`，但 provider conversion 会把它映射成 user-like message，而不是 `MessageRequest.system`。这样模型能知道历史发生过什么，但不会把历史摘要提升为高优先级系统指令，避免改变权限层级、规则优先级或 provider 语义。
