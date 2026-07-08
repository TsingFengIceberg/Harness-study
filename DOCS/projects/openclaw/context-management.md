# OpenClaw Context Management：事件驱动 AgentContext、上下文适配层与实时会话状态

> **日期**: 2026-07-06 | **状态**: draft | **涉及版本**: `c9219c7f80f4ccacc7bfcbce976e1d5abd718769`

## 相关文档

- 项目入口：[README.md](README.md)
- Agent Loop：[agent-loop.md](agent-loop.md)
- Tool System：[tool-system.md](tool-system.md)
- Sandbox / Workspace：[sandbox-workspace.md](sandbox-workspace.md)
- Claw-Code Context Management：[../claw-code/context-management.md](../claw-code/context-management.md)
- 横向 Agent Loop 总结：[agent-loop.md](../../comparison/agent-loop.md)
- 横向 Tool System 总结：[tool-system.md](../../comparison/tool-system.md)

## 源码入口

| 模块 | 源码 | 作用 |
|---|---|---|
| 核心类型 | [types.ts](../../../submodules/openclaw/packages/agent-core/src/types.ts) | `AgentMessage`、`AgentState`、`AgentContext`、`AgentLoopConfig`、`transformContext` / `convertToLlm` 类型。 |
| Agent 状态层 | [agent.ts](../../../submodules/openclaw/packages/agent-core/src/agent.ts) | `Agent` 持有 `state.messages`、`systemPrompt`、tools、steer/followUp 队列，创建 loop context。 |
| Agent loop | [agent-loop.ts](../../../submodules/openclaw/packages/agent-core/src/agent-loop.ts) | `runAgentLoop`、`runLoop`、`streamAssistantResponse`、tool result 回写、steer/followUp 注入。 |
| Harness message conversion | [messages.ts](../../../submodules/openclaw/packages/agent-core/src/harness/messages.ts) | 把 `bashExecution`、`custom`、`branchSummary`、`compactionSummary` 等产品态消息转换为 LLM message。 |
| Harness context hooks | [agent-harness.ts](../../../submodules/openclaw/packages/agent-core/src/harness/agent-harness.ts) | `CoreAgentHarness` 安装 `transformContext`、`convertToLlm`、`prepareNextTurn`、tool hooks。 |
| Session 外壳 | [agent-session.ts](../../../submodules/openclaw/src/agents/sessions/agent-session.ts) | prompt 入口、extension 注入、message 持久化、compaction、retry、session context rebuild。 |
| 图片历史裁剪示例 | [history-image-prune.ts](../../../submodules/openclaw/src/agents/embedded-agent-runner/run/history-image-prune.ts) | 包装 `transformContext`，在模型输入前裁剪旧图片 / 媒体历史。 |

## 1. 核心结论

OpenClaw 的 Context Management 和 Claw-Code 同样遵循：

```text
system prompt + message history + tools -> LLM request
```

但它不是一个本地 CLI transcript 直接 clone 给 provider，而是更像一个 **事件驱动实时会话状态机**：

```text
Agent.state.messages
  -> AgentContext.messages
     -> transformContext(messages)
        -> convertToLlm(messages)
           -> LLM Context { systemPrompt, messages, tools }
```

可以概括为：

> **OpenClaw 的 context 是产品态 Agent transcript：它既要服务模型输入，也要服务 UI streaming、session persistence、工具调度、steer/followUp 插话、extension hook 和 compaction。**

和 Claw-Code 的关键差异是：

```text
Claw-Code:
  system_prompt + Session.messages
  本地 CLI transcript 风格

OpenClaw:
  AgentContext.systemPrompt + AgentContext.messages + tools
  发送前经过 transformContext / convertToLlm
  实时会话状态机风格
```

一句话记忆：

> **Claw-Code 的 context 像本地 transcript 文件；OpenClaw 的 context 像实时会话状态机。前者重在把 `Session.messages` 稳定塞回模型，后者重在让 `AgentContext.messages` 在事件流、工具回写、steer/followUp 插话和 context transform 中持续演化。**

## 2. AgentContext：一次 LLM 调用的核心上下文快照

OpenClaw 低层 loop 使用 [AgentContext](../../../submodules/openclaw/packages/agent-core/src/types.ts#L489-L497) 表示要传给模型 loop 的上下文快照：

```text
AgentContext {
  systemPrompt: string,
  messages: AgentMessage[],
  tools?: AgentTool[],
}
```

对应三类输入：

| 字段 | 含义 | 类比 Claw-Code |
|---|---|---|
| `systemPrompt` | 顶层系统提示 | `ApiRequest.system_prompt` |
| `messages` | 动态 transcript | `Session.messages` |
| `tools` | 当前可见工具面 | provider tool definitions |

`AgentMessage` 定义在 [types.ts:388-393](../../../submodules/openclaw/packages/agent-core/src/types.ts#L388-L393)：

```text
AgentMessage = Message | CustomAgentMessages[keyof CustomAgentMessages]
```

它既包括 LLM 原生消息：

```text
user
assistant
toolResult
```

也包括 OpenClaw / harness 自定义消息：

```text
bashExecution
custom
branchSummary
compactionSummary
```

这些自定义消息让 OpenClaw 能把“产品运行时事件”也纳入 transcript，但是否、如何喂给模型，要等后面的 `convertToLlm` 决定。

## 3. AgentState：messages 是 Agent 状态的一部分

OpenClaw 的 `Agent` 是 stateful wrapper。状态创建在 [agent.ts:72-100](../../../submodules/openclaw/packages/agent-core/src/agent.ts#L72-L100)：

```text
systemPrompt
model
thinkingLevel
tools
messages
isStreaming
streamingMessage
pendingToolCalls
errorMessage
```

其中 `messages` 由闭包持有，并在 setter 里复制顶层数组：

```text
let messages = initialState?.messages?.slice() ?? []

get messages() { return messages }
set messages(nextMessages) { messages = nextMessages.slice() }
```

这说明：

> **OpenClaw 的 message history 不是临时请求参数，而是 Agent state 的核心组成部分。**

`Agent` 每次启动 prompt / continue 时，会从当前 state 创建 context snapshot，见 [agent.ts:466-472](../../../submodules/openclaw/packages/agent-core/src/agent.ts#L466-L472)：

```text
createContextSnapshot() {
  return {
    systemPrompt: this.mutableState.systemPrompt,
    messages: this.mutableState.messages.slice(),
    tools: this.mutableState.tools.slice(),
  }
}
```

这和 Claw-Code 的 `ConversationRuntime` 每轮 clone `Session.messages` 很像，但 OpenClaw 还把 streaming state、pending tool calls、queue 和 event reducer 都纳入 `Agent`。

## 4. Prompt 入口：用户输入变成 AgentMessage

低层 `runAgentLoop(...)` 的入口在 [agent-loop.ts:171-195](../../../submodules/openclaw/packages/agent-core/src/agent-loop.ts#L171-L195)。新 prompt 会先被追加进 context：

```text
newMessages = [...prompts]
currentContext = {
  ...context,
  messages: [...context.messages, ...prompts],
}
```

然后对 prompt 发事件：

```text
message_start
message_end
```

最后进入 `runLoop(...)`。

这和 Claw-Code 的：

```text
run_turn(user_input)
  -> Session.push_user_text(user_input)
```

是同构关系。区别是 OpenClaw 的 prompt 可以是一批 `AgentMessage[]`，不一定只有一个纯文本 user message。

产品层的 [AgentSession.prompt](../../../submodules/openclaw/src/agents/sessions/agent-session.ts#L1219-L1289) 还会在提交给 core agent 前做更多事情：

- 检查是否需要预先 compaction；
- 构造当前 user message；
- 注入 pending `nextTurn` messages；
- 触发 extension `before_agent_start`；
- 允许 extension 添加 `custom` messages；
- 允许 extension 临时修改 `systemPrompt`，否则恢复 `baseSystemPrompt`。

所以 OpenClaw 的“用户输入进入上下文”不是只有 `text -> user message`，而是一个产品层上下文装配点。

## 5. transformContext 与 convertToLlm：两道上下文适配层

这是 OpenClaw Context Management 最值得标记的设计。

在 [streamAssistantResponse](../../../submodules/openclaw/packages/agent-core/src/agent-loop.ts#L446-L468) 里，每次调用 LLM 前都会经过：

```text
let messages = context.messages
if (config.transformContext) {
  messages = await config.transformContext(messages, signal)
}
const llmMessages = await config.convertToLlm(messages)

llmContext = {
  systemPrompt: context.systemPrompt,
  messages: llmMessages,
  tools: context.tools,
}
```

也就是说：

```text
AgentContext.messages
  -> transformContext
  -> convertToLlm
  -> provider-facing messages
```

### transformContext：AgentMessage 层的上下文治理

`transformContext` 的类型注释在 [types.ts:176-196](../../../submodules/openclaw/packages/agent-core/src/types.ts#L176-L196)。它的输入输出都是：

```text
AgentMessage[] -> AgentMessage[]
```

它适合处理 OpenClaw 自己的消息世界：

| 能力 | 例子 |
|---|---|
| 裁剪 | 删除旧图片、旧日志、重复工具结果。 |
| 压缩 | 把长 bash 输出或旧消息替换成摘要。 |
| 注入 | 插入 workspace context、检索结果、外部 memory、相关文件提示。 |
| 改写 | 把大媒体内容替换成 `[history image pruned]`。 |
| 安全治理 | 移除不应 replay 的内容，或加边界标记。 |

真实例子见 [history-image-prune.ts](../../../submodules/openclaw/src/agents/embedded-agent-runner/run/history-image-prune.ts)。它包装 `agent.transformContext`，先调用已有 transform，再执行 `pruneProcessedHistoryImages(...)`，见 [history-image-prune.ts:157-170](../../../submodules/openclaw/src/agents/embedded-agent-runner/run/history-image-prune.ts#L157-L170)。

这说明 `transformContext` 是“模型输入前的上下文整形器”，但仍停留在 OpenClaw `AgentMessage` 层。

### convertToLlm：provider 协议适配层

`convertToLlm` 的类型注释在 [types.ts:143-174](../../../submodules/openclaw/packages/agent-core/src/types.ts#L143-L174)。它的输入输出是：

```text
AgentMessage[] -> Message[]
```

它负责把产品态 transcript 翻译成 provider 能理解的 LLM message。默认转换在 [agent.ts:33-38](../../../submodules/openclaw/packages/agent-core/src/agent.ts#L33-L38)，只保留：

```text
user
assistant
toolResult
```

Harness 实现更丰富，见 [messages.ts:123-179](../../../submodules/openclaw/packages/agent-core/src/harness/messages.ts#L123-L179)：

| AgentMessage role | convertToLlm 结果 |
|---|---|
| `bashExecution` | 转成 user text；如果 `excludeFromContext` 为 true 则过滤。 |
| `custom` | 转成 user message。 |
| `branchSummary` | 加 summary prefix 后转成 user message。 |
| `compactionSummary` | 加 compact summary prefix 后转成 user message。 |
| `user` / `assistant` / `toolResult` | 原样保留。 |
| 未识别 / UI-only 类型 | 过滤。 |

所以两者区别可以记成：

```text
transformContext 负责：这段上下文应该保留 / 改写成什么。
convertToLlm 负责：这段上下文怎么翻译成模型 API 能吃的格式。
```

> **精髓标记**：OpenClaw 把“上下文治理”和“协议转换”拆成两层。`transformContext` 在 AgentMessage 层做裁剪、压缩、注入；`convertToLlm` 在 provider 边界做过滤和消息类型翻译。这让它能同时服务实时 UI、session persistence、工具调度和模型输入，而不是把所有内容都当作纯文本 prompt 拼接。

## 6. Streaming assistant response：流式输出如何进入 context

OpenClaw 的 streaming 不是等模型完整生成后才写入 context，而是随着 provider stream event 实时更新。

在 [streamAssistantResponse](../../../submodules/openclaw/packages/agent-core/src/agent-loop.ts#L482-L542) 中：

```text
start:
  partialMessage = event.partial
  context.messages.push(message)
  emit message_start

text_delta / thinking_delta / toolcall_delta:
  partialMessage = resolveAssistantMessageUpdate(...)
  context.messages[last] = partialMessage
  emit message_update

done / error:
  finalMessage = await response.result()
  context.messages[last] = finalMessage
  emit message_end
```

这就是 OpenClaw 流式呈现的底层模式：

```text
provider stream event
  -> AgentEvent(message_start / message_update / message_end)
  -> Agent state / context 更新
  -> UI 订阅事件并 patch 同一条 assistant message
```

可以把它理解成：

```text
创建一条 assistant 草稿消息
  -> 每个 delta 修改这条消息
  -> 最后 finalize 成完整 assistant message
```

这也解释了为什么 OpenClaw 的 context 和 UI 是绑在一起的：动态上下文不只是下一轮模型输入，也是实时产品界面正在展示的状态。

和 Claw-Code 对比：

```text
Claw-Code:
  也会 stream 到终端，但 runtime 更像收集 AssistantEvent -> build_assistant_message -> 最终 push Session。

OpenClaw:
  stream event 本身就是 AgentEvent，partial assistant message 会进入 context.messages 并被 message_update 持续替换。
```

> **精髓标记**：在 CLI 里，streaming 主要是终端显示体验；在 OpenClaw 这种产品 runtime 里，streaming 是状态流、UI 流、持久化流和工具调度流的一部分。

## 7. Tool result：工具结果作为 message 回写 context

OpenClaw 的工具结果回写在 [agent-loop.ts:356-372](../../../submodules/openclaw/packages/agent-core/src/agent-loop.ts#L356-L372)：

```text
if assistant stopReason === toolUse:
  executeToolCalls(...)
  toolResults.push(...executedToolBatch.messages)
  for result in toolResults:
    currentContext.messages.push(result)
    newMessages.push(result)
```

所以模型下一轮能看到工具结果，仍然是靠 transcript 回写。

但 OpenClaw 比 Claw-Code 多一层事件化产品语义：工具执行会产生：

```text
tool_execution_start
tool_execution_update
tool_execution_end
message_start / message_end for ToolResultMessage
```

工具结果既是下一轮模型 observation，也是 UI / diagnostics / persistence 的状态输入。

## 8. steer / followUp：运行中插话如何进入上下文

OpenClaw 把中途用户输入拆成两类：

| 类型 | 时机 | 语义 |
|---|---|---|
| `steer` | Agent 正在运行中 | 调整当前任务方向。 |
| `followUp` | Agent 准备结束或已结束后 | 追加下一轮任务。 |

队列实现见 [agent.ts:155-190](../../../submodules/openclaw/packages/agent-core/src/agent.ts#L155-L190)，公开方法见 [agent.ts:312-320](../../../submodules/openclaw/packages/agent-core/src/agent.ts#L312-L320)。

低层 loop 在 [agent-loop.ts:279-329](../../../submodules/openclaw/packages/agent-core/src/agent-loop.ts#L279-L329) 处理 steering messages：

```text
pendingMessages = await getSteeringMessages()
if pendingMessages.length > 0:
  emit message_start / message_end
  currentContext.messages.push(message)
  newMessages.push(message)
```

followUp 在外层 loop 末尾处理，见 [agent-loop.ts:427-433](../../../submodules/openclaw/packages/agent-core/src/agent-loop.ts#L427-L433)：

```text
followUpMessages = await getFollowUpMessages()
if followUpMessages.length > 0:
  pendingMessages = followUpMessages
  continue
```

因此 steer / followUp 最终也会成为 `AgentMessage`，进入 `currentContext.messages`，再参与下一次 `transformContext -> convertToLlm -> LLM request`。

这和 Claw-Code 的“一轮用户输入 -> run_turn”不同：OpenClaw 支持在 live session 中把用户插话排队注入上下文。

## 9. AgentSession：产品层如何接入 context

[AgentSession](../../../submodules/openclaw/src/agents/sessions/agent-session.ts) 把 core `Agent` 接到产品会话、持久化、extension 和 compaction。

### message 持久化

`handleAgentEvent` 会在 [message_end](../../../submodules/openclaw/src/agents/sessions/agent-session.ts#L624-L670) 时持久化消息：

- `custom` 走 `appendCustomMessageEntry(...)`；
- `user` / `assistant` / `toolResult` 走 `sessionManager.appendMessage(...)`；
- `bashExecution`、`compactionSummary`、`branchSummary` 等由其他路径持久化；
- assistant message 会被记录为 `lastAssistantMessage`，供 auto-compaction 检查。

这说明 OpenClaw 的 context 不只是内存数组，也会落到 session manager 中，成为可恢复 / 可展示的会话记录。

### prompt 装配

[AgentSession.prompt](../../../submodules/openclaw/src/agents/sessions/agent-session.ts#L1219-L1289) 在每次用户输入前会：

```text
flush pending bash messages
检查 pre-prompt compaction
构造 user message
注入 pending nextTurn messages
触发 before_agent_start extension
加入 extension custom messages
按 extension 结果临时修改或恢复 systemPrompt
runAgentPrompt(messages)
```

这使得 OpenClaw 的用户输入不只是文本，还可以携带图片、extension context 和动态 system prompt 调整。

### compaction 与 context rebuild

手动 compact 入口见 [agent-session.ts:1817-2005](../../../submodules/openclaw/src/agents/sessions/agent-session.ts#L1817-L2005)。核心是：

```text
abort 当前 agent operation
emit compaction_start
runCompactionWork(...)
sessionManager.appendCompaction(...)
sessionContext = sessionManager.buildSessionContext()
agent.state.messages = sessionContext.messages
emit session_compact / compaction_end
```

也就是说：

> **OpenClaw 的 compaction 不只是改内存里的 messages，而是写入 session compaction entry，再由 SessionManager rebuild session context，最后替换 `agent.state.messages`。**

这比 Claw-Code 的本地 `compact_session(...) -> self.session = compacted_session` 更产品化，也更依赖 session persistence。

## 10. 一次请求里 OpenClaw 塞给模型的东西

一次模型调用最终由 [streamAssistantResponse](../../../submodules/openclaw/packages/agent-core/src/agent-loop.ts#L446-L480) 发出，大致是：

```text
LLM Context {
  systemPrompt: context.systemPrompt,
  messages: convertToLlm(transformContext(context.messages)),
  tools: context.tools,
}

options {
  model,
  thinkingLevel / reasoning,
  apiKey,
  sessionId,
  transport,
  maxRetryDelayMs,
  signal,
  onPayload / onResponse,
}
```

按来源拆开：

| 类别 | 来源 | 说明 |
|---|---|---|
| `systemPrompt` | `Agent.state.systemPrompt` / AgentSession base prompt / extension 修改 | 顶层系统提示。 |
| `messages` | `Agent.state.messages` / prompt / assistant streaming / tool result / steer / followUp / compaction | 动态 transcript，发送前可 transform 和 convert。 |
| `tools` | `Agent.state.tools` / AgentSession 工具装配 | 当前工具面。 |
| `model` | `Agent.state.model` / turn state | 当前模型。 |
| `thinkingLevel` / `reasoning` | `Agent.state.thinkingLevel` / config | 推理配置。 |
| `apiKey` | `getApiKey(...)` / session model registry | 每次请求可动态解析。 |
| `sessionId` | Agent options | 给 cache-aware provider 使用。 |
| `onPayload` / `onResponse` | Agent options | 请求 / 响应观察 hook。 |

一句话：

```text
OpenClaw 发给模型的不是原始 UI 事件流，
而是经过 context transform 和 provider conversion 后的 AgentContext 快照。
```

## 11. 和 Claw-Code 的横向对比

| 维度 | Claw-Code | OpenClaw |
|---|---|---|
| 上下文主容器 | `Session.messages` | `Agent.state.messages` / `AgentContext.messages` |
| 顶层 system | `system_prompt: Vec<String>` | `AgentContext.systemPrompt: string` |
| 请求前上下文治理 | `maybe_auto_compact` / provider client conversion | `transformContext` / `prepareNextTurn` / compaction / extension hook |
| provider conversion | CLI `convert_messages(...)` | `convertToLlm(...)`，可过滤 / 转换产品态消息 |
| streaming 进入状态 | 终端 streaming 后 build assistant message | partial assistant message 实时进入 context 并发 `message_update` |
| 工具结果 | `ConversationMessage::tool_result` | `ToolResultMessage` + 工具执行事件 |
| 用户中途输入 | 下一次 CLI turn | `steer` / `followUp` 队列注入 live context |
| compaction | 本地启发式 summary / Trident | compaction entry + SessionManager rebuild context |
| 核心气质 | 本地 CLI transcript | 实时产品会话状态机 |

可以归纳为：

```text
Claw-Code 关注“如何把本地 session 历史稳定发回模型”；
OpenClaw 关注“如何让一个实时多端 Agent session 的状态持续演化，并在每次请求前转换成模型可消费的上下文”。
```

## 12. 阶段性判断

OpenClaw Context Management 的第一轮结论：

> **OpenClaw 把上下文管理做成了产品态实时会话状态：`AgentContext.messages` 不只是 prompt buffer，而是 event stream、UI rendering、tool scheduling、extension hooks、session persistence 和 model input 的共同载体。`transformContext` / `convertToLlm` 是它区别于更朴素 CLI harness 的关键适配层。**

如果用比喻：

```text
Claw-Code 像本地施工日志：每轮把日志重新递给模型。
OpenClaw 像在线工单系统：施工日志、进度大屏、用户插话、工具回执和历史归档共用一条实时状态流，再在模型调用前整理成可读上下文。
```

## QA / 讨论记录

### Q: OpenClaw 的 `transformContext` 和 `convertToLlm` 分别能干什么？

> **状态**: verified
> **来源**: source-code / discussion

A: `transformContext` 输入输出都是 `AgentMessage[]`，负责在 OpenClaw 内部消息层做上下文治理，例如裁剪旧消息、压缩历史、注入外部 context、替换旧图片 / 大媒体内容。`convertToLlm` 输入 `AgentMessage[]`、输出 provider-facing `Message[]`，负责过滤 UI-only message，并把 `bashExecution`、`custom`、`branchSummary`、`compactionSummary` 等产品态消息翻译成模型能接收的 user / assistant / toolResult message。

### Q: `transformContext` 中“每次请求前改写 / 裁剪 / 注入上下文”是什么意思？

> **状态**: verified
> **来源**: source-code / discussion

A: 每次 `streamAssistantResponse` 调用 provider 之前，OpenClaw 都会先把 `context.messages` 交给 `transformContext`。这个 hook 可以把很旧的图片替换成占位符、把长日志压成摘要、删除重复工具结果，或插入 workspace context / 相关文件 / memory 检索结果。它仍然工作在 `AgentMessage` 层，不负责 provider 协议格式。

### Q: assistant response streaming 时就进入 context 是什么意思？

> **状态**: verified
> **来源**: source-code / discussion

A: OpenClaw 在收到 provider stream 的 `start` 事件时，会把 partial assistant message push 到 `context.messages` 并发 `message_start`；后续 `text_delta` / `thinking_delta` / `toolcall_delta` 会更新 `context.messages` 最后一条 message 并发 `message_update`；`done` / `error` 时再替换为 final message 并发 `message_end`。所以前端流式显示的本质是订阅同一条 assistant 草稿消息的持续 patch。

### Q: OpenClaw 的 streaming 和 Claw-Code streaming 有什么区别？

> **状态**: draft
> **来源**: discussion / source-code

A: Claw-Code 也 stream 给终端，但 runtime 更像收集 `AssistantEvent` 后构造完整 `ConversationMessage` 再写入 `Session`。OpenClaw 则把 provider stream event 直接变成 `AgentEvent`，partial assistant message 会实时进入 `AgentContext.messages` 并触发 UI / state 更新。因此在 CLI 中 streaming 主要是终端显示体验；在 OpenClaw 中 streaming 同时是状态流、UI 流、持久化流和工具调度流的一部分。

### Q: OpenClaw 一次请求塞给模型的上下文有哪些？

> **状态**: verified
> **来源**: source-code / discussion

A: 核心是 `LLM Context { systemPrompt, messages, tools }`。其中 `systemPrompt` 来自 `Agent.state.systemPrompt` / AgentSession base prompt / extension 修改；`messages` 来自 `Agent.state.messages`，包括用户输入、assistant streaming message、tool result、steer/followUp、custom message、summary 等，经 `transformContext` 和 `convertToLlm` 后发给 provider；`tools` 来自当前 Agent tools。请求 options 还包括 model、thinking / reasoning、apiKey、sessionId、transport、signal、payload/response hooks 等。

### Q: OpenClaw 的 compaction 和 Claw-Code compact 有什么不同？

> **状态**: draft
> **来源**: source-code / discussion

A: Claw-Code 的基础 compact 更像本地函数 `compact_session(...) -> compacted_session`，直接替换 runtime session。OpenClaw 的 compaction 由 AgentSession 产品层协调：abort 当前 run，运行 compaction work，写入 session compaction entry，再通过 `SessionManager.buildSessionContext()` 重建 context，最后替换 `agent.state.messages`。因此 OpenClaw 的 compaction 和 session persistence / extension hook / UI events 绑定更紧。

### Q: OpenClaw 和 Claw-Code 上下文管理最核心的差异是什么？

> **状态**: verified
> **来源**: discussion / source-code

A: Claw-Code 的 context 像本地 transcript 文件，核心是把 `system_prompt + Session.messages` 稳定塞回模型；OpenClaw 的 context 像实时会话状态机，核心是让 `AgentContext.messages` 在 streaming event、tool result、steer/followUp、extension hook、compaction 和 session persistence 中持续演化，再通过 `transformContext` / `convertToLlm` 变成 provider 可消费的上下文。
