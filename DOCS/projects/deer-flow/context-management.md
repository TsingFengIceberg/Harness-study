# DeerFlow Context Management：ThreadState、Middleware Projection 与工作流状态上下文

> **日期**: 2026-07-07 | **状态**: draft | **涉及版本**: `0808738c5876b04b4aa8e9aca7379a0a62b4232d`

## 相关文档

- 项目入口：[README.md](README.md)
- Agent Loop：[agent-loop.md](agent-loop.md)
- Tool System：[tool-system.md](tool-system.md)
- Multi-Agent：[multi-agent.md](multi-agent.md)
- Sandbox / Workspace：[sandbox-workspace.md](sandbox-workspace.md)
- Claw-Code Context Management：[../claw-code/context-management.md](../claw-code/context-management.md)
- OpenClaw Context Management：[../openclaw/context-management.md](../openclaw/context-management.md)
- Hermes Agent Context Management：[../hermes-agent/context-management.md](../hermes-agent/context-management.md)
- 横向 Agent Loop 总结：[agent-loop.md](../../comparison/agent-loop.md)
- 横向 Tool System 总结：[tool-system.md](../../comparison/tool-system.md)
- 横向 QA：[qa.md](../../comparison/qa.md#context-management--上下文管理)

## 源码入口

| 模块 | 源码 | 作用 |
|---|---|---|
| LangGraph graph factory | [agent.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/agent.py) | `make_lead_agent` / `_make_lead_agent`，装配 model、tools、middleware、system prompt、`ThreadState`。 |
| Middleware chain | [agent.py:269-405](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/agent.py#L269-L405) | lead agent middleware 顺序：DynamicContext、DurableContext、Summarization、Memory、ViewImage、SystemMessageCoalescing 等。 |
| Shared runtime middleware | [tool_error_handling_middleware.py:154-256](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/tool_error_handling_middleware.py#L154-L256) | InputSanitization、ToolOutputBudget、ThreadData、Uploads、Sandbox、DanglingToolCall、LLMErrorHandling、Guardrail、ToolProgress、ToolErrorHandling 等共享卡口。 |
| ThreadState | [thread_state.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/thread_state.py) | 扩展 LangChain `AgentState`，加入 sandbox、thread_data、todos、uploaded_files、viewed_images、delegations、skill_context、summary_text 等 state channel。 |
| Dynamic context | [dynamic_context_middleware.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/dynamic_context_middleware.py) | 当前日期和 memory snapshot 注入，frozen-snapshot pattern，保持 base system prompt 静态。 |
| Durable context | [durable_context_middleware.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/durable_context_middleware.py) | 捕获 delegation / skill context，并把 `summary_text`、delegations、skill_context 投影成 hidden durable context data。 |
| Summarization | [summarization_middleware.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/summarization_middleware.py) | 长历史压缩，删除旧 messages、保留尾部 messages，并写入 `summary_text` state channel。 |
| Memory update | [memory_middleware.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/memory_middleware.py) | agent 结束后过滤 user / final assistant 消息，异步排队更新长期 memory。 |
| System message coalescing | [system_message_coalescing_middleware.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/system_message_coalescing_middleware.py) | provider 请求前把 static system prompt 与 middleware 产生的 SystemMessages 合并为单个 leading SystemMessage。 |
| Upload context | [uploads_middleware.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/uploads_middleware.py) | 根据上传文件 metadata 注入 `<uploaded_files>` 上下文。 |
| Image context | [view_image_middleware.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/view_image_middleware.py) | `view_image` 工具完成后，把图片 details / base64 作为 HumanMessage 注入模型上下文。 |
| Worker runtime | [worker.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/runtime/runs/worker.py) | Gateway 后台 run worker，安装 runtime context、checkpointer、store，并驱动 `agent.astream(...)`。 |
| Gateway run API | [thread_runs.py](../../../submodules/deer-flow/backend/app/gateway/routers/thread_runs.py) | thread run / stream / wait / cancel / checkpoint regenerate 等 API，读取 checkpoint 中的 messages。 |

## 1. 核心结论

DeerFlow 的 Context Management 可以先用一句话理解：

> **DeerFlow 的上下文管理不是“一个模块在拼 prompt”，而是 `ThreadState + middleware projection`：上下文字段存在 LangGraph state / checkpoint 中，不同 middleware 在 before_agent / before_model / wrap_model_call / after_agent 等生命周期点写入、压缩、修复或投影成最终模型请求。**

和前面几个项目相比：

```text
Claw-Code:
  system prompt + Session.messages
  本地 CLI transcript replay

OpenClaw:
  AgentContext.messages
  产品态实时会话状态机

Hermes:
  messages -> api_messages
  多 provider 长会话生存修复管线

DeerFlow:
  ThreadState + middleware projection + LangGraph checkpoint
  工作流状态上下文
```

所以读 DeerFlow 的上下文管理，重点不是找一个“大号 ContextManager”，而是问五个问题：

```text
1. 状态字段在哪里？
2. 哪个 middleware 写这个字段？
3. 哪个 middleware 读这个字段？
4. 它改的是 checkpointed state，还是只改本次 request payload？
5. 它发生在 before_agent、before_model、wrap_model_call、after_model，还是 after_agent？
```

一句话记忆：

> **Claw-Code 看 transcript；OpenClaw 看 AgentContext 事件状态；Hermes 看 API-call repair；DeerFlow 看 ThreadState 中有哪些 channel，以及 middleware 在流水线哪个位置操作这些 channel。**

## 2. Graph 装配点：system prompt、middleware、ThreadState 汇合

DeerFlow 的 lead agent 在 [agent.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/agent.py) 中装配。

核心创建点见 [agent.py:603-626](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/agent.py#L603-L626)：

```text
create_agent(
  model=create_chat_model(...),
  tools=final_tools,
  middleware=build_middlewares(...),
  system_prompt=apply_prompt_template(...),
  state_schema=ThreadState,
)
```

这里说明一次模型请求的上下文来源至少有四类：

| 来源 | 说明 |
|---|---|
| `system_prompt=apply_prompt_template(...)` | 基础 system prompt，包含角色、工具使用规则、skill / subagent / deferred tools 等静态指导。 |
| `state_schema=ThreadState` | LangGraph state schema，包含 `messages` 和 DeerFlow 扩展字段。 |
| `middleware=build_middlewares(...)` | 上下文注入、压缩、memory、durable context、uploads、images、provider 合规等都在 middleware。 |
| `Runtime(context=...)` / checkpointer / store | run_id、thread_id、user_id、agent_name、trace、store、checkpoint 等运行时上下文和持久化支撑。 |

这和 Claw-Code 的差异很大。Claw-Code 更像：

```text
run_turn(system_prompt, Session.messages, tools)
```

DeerFlow 更像：

```text
LangGraph agent(
  state_schema=ThreadState,
  middleware=[...],
  system_prompt=static prompt,
  checkpointer=thread checkpoint,
)
```

## 3. ThreadState：上下文不只是一串 messages

`ThreadState` 定义在 [thread_state.py:223-235](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/thread_state.py#L223-L235)：

```text
class ThreadState(AgentState):
    sandbox
    thread_data
    title
    artifacts
    todos
    goal
    uploaded_files
    viewed_images
    promoted
    delegations
    skill_context
    summary_text
```

其中 `AgentState` 自带 `messages`。所以 DeerFlow 的上下文主容器不是一个裸 `messages` 数组，而是：

```text
ThreadState {
  messages,
  summary_text,
  delegations,
  skill_context,
  uploaded_files,
  viewed_images,
  todos,
  goal,
  sandbox,
  thread_data,
  promoted,
  ...
}
```

这些字段各自有不同语义：

| 字段 | 上下文意义 |
|---|---|
| `messages` | LangGraph / LangChain 的模型对话轨迹，包含 human / ai / tool / injected hidden messages。 |
| `summary_text` | SummarizationMiddleware 生成的历史摘要，独立于普通 messages。 |
| `delegations` | 子任务 delegation ledger，记录 subagent 任务状态和结果引用。 |
| `skill_context` | 已加载 skill 的轻量引用，保存 name/path/description，不保存完整 body。 |
| `uploaded_files` | 当前 thread 上传文件 metadata。 |
| `viewed_images` | 通过 `view_image` 工具读取过的图片数据。 |
| `todos` | plan mode / task tracking 状态。 |
| `promoted` | deferred tool search 后提升为可见的工具名集合。 |
| `sandbox` / `thread_data` | 运行环境和 workspace / uploads / outputs 路径。 |
| `goal` | 当前 thread 的目标状态。 |

> **精髓标记**：DeerFlow 把上下文从“聊天记录”扩展成“工作流状态”。`messages` 只是 ThreadState 的一个 channel；summary、delegation、skill、uploads、images、todo、sandbox 等都可以成为模型上下文的来源。

## 4. Middleware chain：上下文管理是一条流水线

lead agent middleware 顺序见 [agent.py:269-405](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/agent.py#L269-L405)。和上下文管理最相关的是：

```text
shared runtime base:
  InputSanitizationMiddleware
  ToolOutputBudgetMiddleware
  ThreadDataMiddleware
  UploadsMiddleware
  SandboxMiddleware
  DanglingToolCallMiddleware
  LLMErrorHandlingMiddleware
  GuardrailMiddleware
  SandboxAuditMiddleware
  ReadBeforeWriteMiddleware
  ToolProgressMiddleware
  ToolErrorHandlingMiddleware

lead-only:
  DynamicContextMiddleware
  SkillActivationMiddleware
  DurableContextMiddleware
  SummarizationMiddleware
  TodoMiddleware
  TokenUsageMiddleware
  TitleMiddleware
  MemoryMiddleware
  ViewImageMiddleware
  DeferredToolFilterMiddleware
  SystemMessageCoalescingMiddleware
  SubagentLimitMiddleware
  LoopDetectionMiddleware
  TokenBudgetMiddleware
  SafetyFinishReasonMiddleware
  ClarificationMiddleware
```

为了理解上下文管理，可以按职责分组：

| 分组 | Middleware | 作用 |
|---|---|---|
| 动态注入 | DynamicContextMiddleware | 当前日期 + memory snapshot，frozen snapshot。 |
| 耐久投影 | DurableContextMiddleware | `summary_text` / delegation ledger / skill references 投影给模型。 |
| 压缩 | SummarizationMiddleware | 摘要旧 messages，写入 `summary_text`。 |
| 长期记忆更新 | MemoryMiddleware | agent 完成后把 user + final assistant 排队更新 memory。 |
| 文件 / 媒体上下文 | UploadsMiddleware / ViewImageMiddleware | 上传文件、图片 details 注入模型上下文。 |
| provider 合规 | SystemMessageCoalescingMiddleware / DanglingToolCallMiddleware | 合并 system messages，修补 dangling tool calls。 |
| 预算保护 | ToolOutputBudgetMiddleware / TokenBudgetMiddleware | 控制工具输出和 run token 消耗，保护上下文窗口。 |
| 工具/状态治理 | DeferredToolFilter / ToolProgress / ToolErrorHandling / LoopDetection | 控制工具可见性、进度、错误和重复 loop。 |

所以 DynamicContextMiddleware 很重要，但它不是唯一“掌管上下文”的中间件。更准确的说法是：

> **DynamicContextMiddleware 管“动态背景如何首次进入对话”；SummarizationMiddleware 管“历史太长怎么压缩”；DurableContextMiddleware 管“非 messages 的耐久状态如何投影给模型”；SystemMessageCoalescingMiddleware 管“发给 provider 前如何合并 system 信息”；MemoryMiddleware 管“本轮结束后如何沉淀长期记忆”。**

## 5. DynamicContextMiddleware：日期 + memory 的 frozen snapshot

### 5.1 它的职责

[dynamic_context_middleware.py:1-7](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/dynamic_context_middleware.py#L1-L7) 开头说明：

```text
The system prompt is kept fully static for maximum prefix-cache reuse.
The current date is always injected.
Per-user memory is also injected when memory.injection_enabled is True.
Both are delivered once per conversation as a dedicated <system-reminder>
SystemMessage inserted before the first user message (frozen-snapshot pattern).
```

白话说：

> **DynamicContextMiddleware 把当前日期和可选 memory snapshot 作为隐藏上下文插进 `messages`，同时让 base system prompt 保持静态。**

它回答的是：

```text
动态信息怎么进模型？
```

不是每轮拼 system prompt，而是第一次进入 thread 时，把动态信息变成 checkpointed hidden messages。

### 5.2 为什么不直接改 system prompt？

[agent.py:304-308](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/agent.py#L304-L308) 对这个设计有直接注释：

```text
Always inject current date (and optionally memory) as <system-reminder> into the
first HumanMessage to keep the system prompt fully static for prefix-cache reuse.
```

也就是说，DeerFlow 和 Hermes 一样重视 prompt cache，但采取的方式不同：

| 项目 | 做法 |
|---|---|
| Hermes | system prompt 是 session-stable cache prefix；recall context 临时追加当前 user API copy。 |
| DeerFlow | base system prompt 静态；日期 / memory 作为 hidden messages 注入并 checkpoint。 |

### 5.3 具体注入流程

核心逻辑在 [dynamic_context_middleware.py:239-278](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/dynamic_context_middleware.py#L239-L278)：

```text
messages = state["messages"]
current_date = today
last_date = _last_injected_date(messages)

if last_date is None:
    first_idx = first injectable HumanMessage
    date_reminder, memory_block = _build_full_reminder()
    result_msgs = _make_reminder_and_user_messages(...)
    return {"messages": result_msgs}

if last_date == current_date:
    return None

else midnight crossed:
    inject date-update reminder before current turn
```

第一次注入前：

```text
messages:
  HumanMessage("帮我写一个报告")
```

第一次注入后：

```text
messages:
  SystemMessage(
    "<system-reminder><current_date>2026-07-07, Tuesday</current_date></system-reminder>",
    hide_from_ui=True,
    dynamic_context_reminder=True,
  )

  HumanMessage(
    "<memory>...</memory>",
    hide_from_ui=True,
    dynamic_context_reminder=True,
  )

  HumanMessage("帮我写一个报告")
```

这不是简单地把文本拼到用户问题前面，而是用 ID-swap 把原始 HumanMessage 拆成 reminder + memory + 原始用户消息三段。

### 5.4 ID-swap 技术

ID-swap 实现在 [dynamic_context_middleware.py:184-237](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/dynamic_context_middleware.py#L184-L237)。关键点：

```text
SystemMessage 使用原始 message id
memory HumanMessage 使用 {id}__memory
原始用户 HumanMessage 使用 {id}__user
```

这样做是为了配合 LangGraph 的 `add_messages` reducer：使用原始 ID 的 SystemMessage 可以替换原始 HumanMessage，随后追加 memory 和真正用户消息，避免重复注入和 ghost-message re-execution。

为了防递归，[_is_user_injection_target](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/dynamic_context_middleware.py#L106-L122) 会排除：

- 已经是 dynamic context reminder 的消息；
- summary trigger message；
- id 以 `__user` 结尾的消息。

### 5.5 framework-owned data 与 user-owned memory 分权

[dynamic_context_middleware.py:148-154](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/dynamic_context_middleware.py#L148-L154) 是一个很重要的安全设计：

```text
Framework-owned data (date) is separated from user-owned data (memory)
so the downstream SystemMessage carries only framework authority and
memory stays at role:user — preventing untrusted content from gaining
system privilege (OWASP LLM01).
```

所以：

| 内容 | 属性 | 承载消息 |
|---|---|---|
| 当前日期 / reminder metadata | framework-owned | hidden SystemMessage |
| memory | user-owned / user-influenceable | hidden HumanMessage |
| 当前用户输入 | user-owned | HumanMessage |

> **精髓标记**：DeerFlow 不只是“把 memory 塞进 prompt”，它还把 framework-owned context 和 user-owned memory 分权：日期等框架事实可以走 SystemMessage；memory 虽然隐藏，但仍用 HumanMessage 承载，避免用户可影响的记忆获得 system 级指令权限。

### 5.6 frozen snapshot 与跨天更新

`DynamicContextMiddleware` 不会每轮重新注入。

- 如果没有注入过日期：注入 full reminder；
- 如果同一天已经注入过：什么都不做；
- 如果跨过午夜：只注入轻量 date-update reminder。

这就是 [dynamic_context_middleware.py:125-140](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/dynamic_context_middleware.py#L125-L140) 说的：

```text
First turn: frozen for the whole session
Midnight crossing: prepend date-update reminder to current HumanMessage
```

> **精髓标记**：DynamicContextMiddleware 使用 frozen-snapshot pattern：动态 context 不是每轮刷新，而是在首次进入会话时冻结成隐藏历史；只有跨天这种客观变化才追加轻量更新。这样既保留动态信息，又保持 system prompt 和历史前缀稳定。

### 5.7 before_agent 位置与 I/O 保护

它挂在 `before_agent`，见 [dynamic_context_middleware.py:280-307](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/dynamic_context_middleware.py#L280-L307)。异步路径会把 `_inject(...)` 放到线程里并设置 5 秒 timeout：

```text
await asyncio.wait_for(asyncio.to_thread(self._inject, state), timeout=5.0)
```

原因是 `_inject` 可能读取 memory JSON，甚至触发 token counting 依赖加载；不能阻塞 Gateway event loop。

这体现 DeerFlow 的平台化意识：上下文注入不是单机 CLI 小动作，而是服务端并发请求路径上的操作，必须防止阻塞 SSE / HTTP handler。

## 6. SummarizationMiddleware：把旧 messages 压缩成 summary_text

DeerFlow 的压缩入口是 [DeerFlowSummarizationMiddleware](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/summarization_middleware.py)。

核心逻辑在 [summarization_middleware.py:252-280](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/summarization_middleware.py#L252-L280)：

```text
messages = state["messages"]
previous_summary = state.get("summary_text")
trigger_messages = messages + optional summary-count message
total_tokens = token_counter(trigger_messages)

if should_summarize:
    messages_to_summarize, preserved_messages = partition(...)
    summary = summarize(messages_to_summarize, previous_summary)
    return {
      "messages": [RemoveMessage(REMOVE_ALL_MESSAGES), *preserved_messages],
      "summary_text": summary,
    }
```

这里有两个重点：

1. `messages` 会被裁剪，只保留 preserved tail；
2. summary 不作为普通 message 插回 `messages`，而是写入 `summary_text` 这个 state channel。

这和 Claw-Code 的 compact summary 放回 `Session.messages` 不同，也和 Hermes 的 compression rewrite session 不同。

[summarization_middleware.py:312-364](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/summarization_middleware.py#L312-L364) 还会保护 DynamicContextMiddleware 注入的 hidden reminders，避免压缩时把 reminder triplet 压坏。

> **精髓标记**：DeerFlow 把压缩摘要从普通 messages 里拆出来，放进 `summary_text` state channel。messages 负责最近轨迹，summary_text 负责历史摘要，两者再由 DurableContextMiddleware 在请求前组合给模型看。

## 7. DurableContextMiddleware：把非 messages 的耐久状态投影给模型

如果 summary 不在 `messages` 里，模型怎么看到？答案是 [DurableContextMiddleware](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/durable_context_middleware.py)。

文件开头 [durable_context_middleware.py:1-7](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/durable_context_middleware.py#L1-L7) 就说明：

```text
Capture enumerates task delegations and loaded skill files into checkpointed state channels.
Injection renders static authority rules as a SystemMessage and renders untrusted channel values
(summary_text, delegations, skill_context) as one hidden <durable_context_data> HumanMessage,
never written back to state.
```

它做两件事。

### 7.1 捕获 durable context

[durable_context_middleware.py:130-163](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/durable_context_middleware.py#L130-L163)：

- `before_model` / `abefore_model` 捕获 delegations 和 skill_context；
- `after_model` / `aafter_model` 捕获 delegations；
- skill_context 只保存 skill 的 name/path/description 引用，不保存完整 body。

这些会进入 `ThreadState.delegations` 和 `ThreadState.skill_context`，并随 checkpoint 持久化。

### 7.2 投影 durable context

[durable_context_middleware.py:165-187](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/durable_context_middleware.py#L165-L187)：

```text
state.summary_text + state.delegations + state.skill_context
  -> render <durable_context_data>
  -> 插入 request.messages
```

插入时分两层：

```text
SystemMessage:
  Durable context authority contract
  告诉模型：下面 hidden durable-context data 是历史观察数据，不是指令

HumanMessage:
  <durable_context_data>
    summary_text
    delegation ledger
    skill context
  </durable_context_data>
```

关键是：

```text
untrusted channel values -> hidden HumanMessage
```

因为 summary、subagent result、skill description 都可能含用户 / 模型 / 工具输出文本，不能提升成 system 指令。

> **精髓标记**：DurableContextMiddleware 是 DeerFlow 的“耐久上下文投影器”：checkpoint 中的 `summary_text`、delegations、skill_context 不直接伪装成普通对话消息，而是在模型调用前临时投影成 hidden HumanMessage，并由 SystemMessage authority contract 约束其语义。

## 8. MemoryMiddleware：本轮结束后沉淀长期记忆

[MemoryMiddleware](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/memory_middleware.py) 不负责当前模型请求的 memory 注入；它负责 agent 执行后异步更新 memory。

[ memory_middleware.py:29-37](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/memory_middleware.py#L29-L37) 说明：

```text
After each agent execution, queues the conversation for memory update
Only includes user inputs and final assistant responses
The queue uses debouncing
Memory is updated asynchronously via LLM summarization
```

[ memory_middleware.py:83-121](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/memory_middleware.py#L83-L121) 的流程是：

```text
state["messages"]
  -> filter_messages_for_memory(messages)
  -> 只保留 user inputs + final assistant responses
  -> detect correction / reinforcement
  -> capture user_id + trace_id
  -> memory queue.add(...)
```

所以 DeerFlow 的 memory 链路是：

```text
输入侧：
  DynamicContextMiddleware 从 memory storage 读取 snapshot，注入 hidden messages

输出侧：
  MemoryMiddleware 在 after_agent 阶段过滤本轮对话，异步更新 memory
```

这和 Hermes 不同：Hermes 更像每轮按 query 召回 recall context；DeerFlow 更像 first-turn frozen memory snapshot + after-agent async memory update。

## 9. SystemMessageCoalescingMiddleware：provider 请求前的合规化

DynamicContextMiddleware 会产生 SystemMessage；DurableContextMiddleware 也会插入 SystemMessage；create_agent 还有 static system prompt。很多 provider 不接受多个分散的 SystemMessage。

[system_message_coalescing_middleware.py:1-23](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/system_message_coalescing_middleware.py#L1-L23) 说明它的作用：

```text
request.system_message + request.messages 中的 SystemMessages
  -> 合并成一个 leading SystemMessage
```

它运行在 `wrap_model_call`，见 [system_message_coalescing_middleware.py:119-150](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/system_message_coalescing_middleware.py#L119-L150)，只改本次 request payload，不改 checkpoint state。

这个区分很重要：

| 位置 | 是否持久 |
|---|---|
| DynamicContextMiddleware 写入 state messages | 是，进入 checkpoint。 |
| DurableContextMiddleware 注入 request messages | 否，只是本次 model request。 |
| SystemMessageCoalescingMiddleware 合并 system messages | 否，只是 provider-facing payload。 |

> **精髓标记**：DeerFlow 明确区分 checkpointed state 和 provider-facing request。某些 middleware 写入长期 state；另一些只在 `wrap_model_call` 阶段修改本次请求，既满足 provider 协议，又不破坏 LangGraph checkpoint 结构。

## 10. Uploads / ViewImage：文件与多模态上下文也是 middleware 注入

DeerFlow 的上下文管理不只文本历史。

[UploadsMiddleware](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/uploads_middleware.py) 负责上传文件上下文。文件头 [uploads_middleware.py:112-118](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/uploads_middleware.py#L112-L118) 说明：它读取当前 message 的 `additional_kwargs.files`，把 `<uploaded_files>` block prepend 到最后一个 human message，让模型知道有哪些文件可用。

[ViewImageMiddleware](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/view_image_middleware.py) 负责图片上下文。文件头 [view_image_middleware.py:19-31](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/view_image_middleware.py#L19-L31) 说明：当 `view_image` 工具完成后，它在 LLM call 前创建 HumanMessage，包含图片 details 和 base64，让模型能直接看图。

这进一步体现 DeerFlow 的形态：

```text
文件上下文、图片上下文、memory、summary、delegation、skill context
都不是集中在一个 prompt builder 里，
而是由对应 middleware 在合适的生命周期点注入。
```

## 11. Checkpoint / Runtime：上下文持久化是 LangGraph state 持久化

Gateway worker 在 [worker.py:291-308](../../../submodules/deer-flow/backend/packages/harness/deerflow/runtime/runs/worker.py#L291-L308) 会读取 pre-run checkpoint，用于 rollback。

在 [worker.py:392-396](../../../submodules/deer-flow/backend/packages/harness/deerflow/runtime/runs/worker.py#L392-L396) 会把 checkpointer / store 挂到 agent 上：

```text
if checkpointer is not None:
    agent.checkpointer = checkpointer
if store is not None:
    agent.store = store
```

因此 DeerFlow 的上下文恢复路径是：

```text
thread_id
  -> LangGraph checkpointer
     -> checkpoint.channel_values
        -> messages
        -> summary_text
        -> todos
        -> delegations
        -> skill_context
        -> uploaded_files
        -> viewed_images
        -> ...
```

Gateway 侧也能从 checkpoint 中读 messages，例如 [thread_runs.py](../../../submodules/deer-flow/backend/app/gateway/routers/thread_runs.py) 中 `_checkpoint_messages(...)` 会读取 `checkpoint.channel_values["messages"]`。

所以 DeerFlow 的持久化不是自己维护一个 `Session.messages` 文件，而是依赖 LangGraph checkpoint 存整套 ThreadState。

## 12. 一次请求里 DeerFlow 塞给模型的东西

一次 DeerFlow lead agent 模型请求大致包含：

```text
request.system_message:
  apply_prompt_template(...) 生成的 base system prompt

request.messages:
  checkpointed ThreadState.messages
  + DynamicContext hidden reminder / memory snapshot
  + Uploads / ViewImage 等注入消息
  + tool messages / assistant messages
  + DurableContextMiddleware 临时投影的 summary/delegation/skill data

request.tools:
  final_tools，经 toolsets / MCP / Tool Search / deferred filter 控制

runtime/config:
  thread_id / run_id / user_id / agent_name / store / checkpoint / metadata
```

再经过：

```text
SystemMessageCoalescingMiddleware
  -> request.system_message + in-message SystemMessages 合并成单个 leading SystemMessage

ToolOutputBudget / TokenBudget / LLMErrorHandling / Safety / LoopDetection 等
  -> 保护请求和运行预算
```

最终发给 provider 的不是简单 transcript，而是 middleware chain 投影后的 request。

## 13. 和 Claw-Code / OpenClaw / Hermes 的横向对比

| 维度 | Claw-Code | OpenClaw | Hermes | DeerFlow |
|---|---|---|---|---|
| 主容器 | `Session.messages` | `AgentContext.messages` | `messages` + `api_messages` copy | `ThreadState` / LangGraph checkpoint |
| system prompt | 启动 / REPL 快照 | AgentSession 状态 | session-stable cache prefix | base prompt 静态，动态信息走 middleware |
| 动态上下文 | 工具读取 / compact | transformContext / custom messages | recall context 临时追加 user API copy | DynamicContext hidden reminder / frozen snapshot |
| summary | compact summary 回到 messages | compaction entry + context rebuild | compression rewrite session / messages | `summary_text` 独立 state channel |
| memory | 非核心 | 可通过 extension / transform 接入 | 每轮 prefetch + sync | hidden memory snapshot + after-agent async update |
| tool result | 回写 `Session.messages` | ToolResultMessage + events | tool message 回写 messages | LangGraph ToolMessage / middleware 兜底 |
| provider repair | provider conversion 较集中 | convertToLlm | heavy repair/sanitize pipeline | provider 合规更多由 middleware / provider adapter 分层处理 |
| 持久化 | 本地 session | SessionManager | SessionDB / trajectory | LangGraph checkpointer + store |
| 核心气质 | 本地 transcript | 实时产品状态机 | 长会话生存修复管线 | 工作流状态投影系统 |

可以归纳为：

```text
Claw-Code 关注：如何稳定重放本地 session transcript。
OpenClaw 关注：如何让多端产品态 AgentContext 实时演化。
Hermes 关注：如何让长期个人 Agent 在多 provider / 长 session 中继续活着。
DeerFlow 关注：如何把 LangGraph state 通过 middleware 原子化治理并投影成模型请求。
```

## 14. 阶段性判断

DeerFlow Context Management 的第一轮结论：

> **DeerFlow 的上下文管理本质是工作流状态管理。它把上下文拆成多个 checkpointed state channel：messages、summary_text、delegations、skill_context、uploaded_files、viewed_images、todos、sandbox 等；再由 DynamicContext、Summarization、DurableContext、Uploads、ViewImage、SystemMessageCoalescing、Memory 等 middleware 在不同生命周期点注入、压缩、投影、修复和沉淀。学 DeerFlow 的关键，是把状态流转和 middleware 位置学明白。**

如果用比喻：

```text
Claw-Code 像本地施工日志。
OpenClaw 像在线工单状态机。
Hermes 像长期私人助理的工作台。
DeerFlow 像工作流工厂的状态看板：每个中间件负责一个卡口，状态在看板上流转，最终由流水线投影成模型能看的上下文。
```

## QA / 讨论记录

### Q: DynamicContextMiddleware 是 DeerFlow 上下文管理的主角吗？

> **状态**: verified
> **来源**: source-code / discussion

A: 它是重要入口之一，但不是唯一主角。DynamicContextMiddleware 主要负责当前日期和可选 memory snapshot 的首次注入，并保持 base system prompt 静态。DeerFlow 的上下文管理实际由一组 middleware 协作完成：SummarizationMiddleware 管历史压缩，DurableContextMiddleware 管 `summary_text` / delegation / skill context 投影，MemoryMiddleware 管长期记忆更新，UploadsMiddleware / ViewImageMiddleware 管文件和图片上下文，SystemMessageCoalescingMiddleware 管 provider-facing system message 合规化。

### Q: DynamicContextMiddleware 具体做什么？

> **状态**: verified
> **来源**: source-code / discussion

A: 它在 `before_agent` 阶段读取 `state["messages"]`，如果还没有注入过日期，就找到第一个可注入的 HumanMessage，用 ID-swap 技术替换成 hidden SystemMessage 日期 reminder、hidden HumanMessage memory block、原始 HumanMessage。如果同一天已经注入过，就不做任何事；如果跨天，则在当前 turn 前追加轻量 date-update reminder。源码见 [dynamic_context_middleware.py:239-278](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/dynamic_context_middleware.py#L239-L278)。

### Q: 为什么 DeerFlow 要把日期和 memory 拆成 SystemMessage / HumanMessage？

> **状态**: verified
> **来源**: source-code / discussion

A: 因为二者权限属性不同。日期是 framework-owned data，可以作为 hidden SystemMessage；memory 是 user-owned / user-influenceable data，即使隐藏也不能获得 system authority，所以用 hidden HumanMessage 承载。这样可以防止用户写入 memory 的内容变成系统级指令。源码注释见 [dynamic_context_middleware.py:148-154](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/dynamic_context_middleware.py#L148-L154)。

### Q: frozen-snapshot pattern 是什么意思？

> **状态**: verified
> **来源**: source-code / discussion

A: 指动态上下文不是每轮刷新，而是在首次进入会话时冻结成隐藏历史并持久到 checkpoint。DynamicContextMiddleware 首轮注入日期和 memory snapshot；同一天后续 turn 不重复注入；跨天时只追加轻量 date-update reminder。这样既让模型看到动态背景，又保持 base system prompt 和历史前缀稳定。

### Q: DeerFlow 的上下文管理为什么要看 middleware 位置？

> **状态**: verified
> **来源**: source-code / discussion

A: 因为 DeerFlow 是高度原子化 / 流水线化的 LangGraph agent。不同上下文动作发生在不同 lifecycle hook：DynamicContext 在 `before_agent` 写入 hidden messages；Summarization 在 `before_model` 压缩 messages 并写 `summary_text`; DurableContext 在 `before_model` / `after_model` 捕获 durable channels，并在 `wrap_model_call` 投影到 request；SystemMessageCoalescing 在 `wrap_model_call` 合并 system messages；Memory 在 `after_agent` 异步更新长期记忆。弄清这些位置，就能看懂状态怎么流转。

### Q: DeerFlow 的 summary 和 Claw-Code compact summary 有什么不同？

> **状态**: draft
> **来源**: source-code / discussion

A: Claw-Code 的 compact summary 会作为会话消息的一部分回到 `Session.messages`，provider conversion 时再发给模型。DeerFlow 的 SummarizationMiddleware 删除旧 messages、保留尾部 messages，并把摘要写进 `summary_text` 这个独立 state channel；随后 DurableContextMiddleware 在模型调用前把 `summary_text` 投影成 hidden durable context data。也就是说，DeerFlow 把“历史摘要”从普通消息里拆出来，作为 checkpointed state channel 管理。

### Q: DeerFlow 的 context management 最核心的学习方法是什么？

> **状态**: verified
> **来源**: discussion / source-code

A: 不要找一个总控 `ContextManager`，而是按状态流转读：先看 ThreadState 有哪些 channel；再看哪个 middleware 写入这些 channel；再看哪个 middleware 在 before_agent / before_model / wrap_model_call / after_model / after_agent 读它们、投影它们或清理它们；最后区分它改的是 checkpointed state 还是本次 provider-facing request。这样 DeerFlow 的上下文管理会比大函数式 harness 更清晰。
