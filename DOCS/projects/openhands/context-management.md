# OpenHands Context Management：事件账本、当前分支 View 与平台化 SWE Agent 上下文投影

> **日期**: 2026-07-07 | **状态**: draft | **涉及版本**: `openhands` submodule `ef3323a`；`software-agent-sdk` submodule `0737c05`

## 相关文档

- OpenHands 笔记入口：[README.md](README.md)
- OpenHands Agent Loop：[agent-loop.md](agent-loop.md)
- OpenHands Tool System：[tool-system.md](tool-system.md)
- 横向上下文管理总结：[context-management.md](../../comparison/context-management.md)
- 横向 QA：[Harness Study 横向 QA](../../comparison/qa.md#context-management--上下文管理)
- 控制面源码：
  - App conversation start：[live_status_app_conversation_service.py](../../../submodules/openhands/openhands/app_server/app_conversation/live_status_app_conversation_service.py)
  - App conversation router：[app_conversation_router.py](../../../submodules/openhands/openhands/app_server/app_conversation/app_conversation_router.py)
  - App conversation models：[app_conversation_models.py](../../../submodules/openhands/openhands/app_server/app_conversation/app_conversation_models.py)
  - App conversation service base：[app_conversation_service_base.py](../../../submodules/openhands/openhands/app_server/app_conversation/app_conversation_service_base.py)
- 执行面源码：
  - Agent Server conversation service：[conversation_service.py](../../../submodules/software-agent-sdk/openhands-agent-server/openhands/agent_server/conversation_service.py)
  - Agent Server event router：[event_router.py](../../../submodules/software-agent-sdk/openhands-agent-server/openhands/agent_server/event_router.py)
  - Agent Server event service：[event_service.py](../../../submodules/software-agent-sdk/openhands-agent-server/openhands/agent_server/event_service.py)
  - SDK conversation state：[state.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/conversation/state.py)
  - Local conversation：[local_conversation.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/conversation/impl/local_conversation.py)
  - Agent step：[agent.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/agent/agent.py)
  - Agent utils：[utils.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/agent/utils.py)
  - Event base：[base.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/event/base.py)
  - View：[view.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/context/view/view.py)
  - Condenser README：[README.md](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/context/condenser/README.md)

## 1. 核心结论

OpenHands 的上下文管理不能只看 [openhands/](../../../submodules/openhands/) 控制面仓库，也不能把它简化为普通的 `messages.append(...)`。它更准确的形态是：

> **OpenHands = 控制面准备任务 / workspace / sandbox / agent 配置，执行面用 append-only EventLog 记录对话、动作、观察和压缩，再从当前 active branch 投影出 View，最后转成 LLM messages。**

一句通俗比喻：

> **OpenHands 像远程开发平台的“事件账本 + 当前分支剪辑”。EventLog 是完整录像带 / 账本，View 是剪给模型看的当前剧情版。**

和前面几个 harness 对比：

- **Claw-Code** 更像一本本地施工日志：线性 transcript / session history。
- **OpenClaw** 更像带调度室的会话状态机：`AgentContext.messages` 结合 `steer` / `followUp` / session state。
- **Hermes Agent** 更像有长期记忆和应急修复能力的个人助理脑：stable prompt、recall context、provider repair、multi-stage compression。
- **DeerFlow** 更像状态流水线工厂：`ThreadState` channels 经过 middleware 投影给模型。
- **OpenHands** 更像平台事件账本：完整事件流可持久化、可分支、可压缩，模型每轮只看当前分支 View。

## 2. 一张总图：从控制面材料到模型输入

OpenHands 的上下文链路可以拆成四层：

```text
第一层：App Server 控制面上下文
  repo / branch / initial_message / secrets / plugins / working_dir / sandbox
  作用：决定“这个 agent 在哪里、带什么配置启动”

第二层：AgentContext / SystemPromptEvent
  static system prompt + dynamic_context + skills + secrets + datetime
  作用：决定“模型一开始知道哪些规则和环境信息”

第三层：EventLog / ConversationState
  MessageEvent / ActionEvent / ObservationEvent / Condensation / state fields
  作用：记录“这场 conversation 发生过什么”

第四层：View -> LLM messages
  active branch + condensation 后的 LLMConvertibleEvent 列表
  作用：决定“下一次模型实际看见什么”
```

从一次模型调用视角看：

```text
App Server
  -> 准备 sandbox / working_dir / repo / secrets / plugins / initial_message
  -> POST /api/conversations 到 Agent Server

Agent Server / SDK
  -> ConversationState 持有 agent / workspace / execution_status / EventLog / View cache
  -> LocalConversation.send_message(...) 把用户输入写成 MessageEvent
  -> LocalConversation.run(...)
     -> Agent.step(...)
        -> prepare_llm_messages(state.view, condenser, llm)
           -> View.events
           -> condenser.condense(view) 可选压缩
           -> LLMConvertibleEvent.events_to_messages(...)
           -> make_llm_completion(...)
```

这就是 OpenHands 上下文管理的主干：

> **控制面准备材料，执行面记录事件，View 做当前分支投影，LLM messages 是投影结果。**

## 3. 控制面：准备上下文材料，但不直接拼 provider messages

OpenHands 当前仓库 [openhands/](../../../submodules/openhands/) 更偏 App Server / Agent Canvas / sandbox 管理。创建 conversation 时，[live_status_app_conversation_service.py](../../../submodules/openhands/openhands/app_server/app_conversation/live_status_app_conversation_service.py#L425-L443) 会构造 start conversation request，把以下材料交给 Agent Server：

- `conversation_id`
- `initial_message`
- `system_message_suffix`
- `git_provider`
- `selected_repository` / `selected_branch`
- `working_dir`
- `agent_type` / `llm_model`
- `plugins`
- `api_secrets`

之后它把请求 POST 到 Agent Server：[live_status_app_conversation_service.py](../../../submodules/openhands/openhands/app_server/app_conversation/live_status_app_conversation_service.py#L450-L477)。

后续用户消息也是薄代理。控制面 router 中的 send-message endpoint 最终会 POST 到 Agent Server 的 conversation events endpoint：[app_conversation_router.py](../../../submodules/openhands/openhands/app_server/app_conversation/app_conversation_router.py#L553-L568)。执行面 Agent Server 的 [event_router.py](../../../submodules/software-agent-sdk/openhands-agent-server/openhands/agent_server/event_router.py#L202-L210) 再把请求转成 SDK `Message` 并调用 `event_service.send_message(...)`。

所以控制面不是这样：

```text
App Server 自己拼 system / user / tool messages -> 调 LLM
```

而是这样：

```text
App Server 准备 workspace / sandbox / repo / secrets / plugins / initial task
  -> Agent Server / SDK 执行真正 Conversation / Agent loop
```

这点和 DeerFlow 不同。DeerFlow 的 middleware 会直接站在 model call 前后参与 provider request 投影；OpenHands 控制面更多是把平台上下文材料和运行环境交给执行面。

## 4. Agent Server：启动执行面的 Conversation

在 [conversation_service.py](../../../submodules/software-agent-sdk/openhands-agent-server/openhands/agent_server/conversation_service.py#L697-L838) 中，Agent Server 负责真正创建 / 恢复 conversation：

1. 生成或复用 `conversation_id`；
2. 准备 workspace / worktree；
3. 动态注册工具、client tools、subagent definitions；
4. 保存 `StoredConversation`；
5. 启动 `EventService`；
6. 如果有 initial_message，就调用 `event_service.send_message(message, True)`。

也就是说，App Server 发来的 initial message 最终仍然进入执行面的事件流。

[EventService.send_message(...)](../../../submodules/software-agent-sdk/openhands-agent-server/openhands/agent_server/event_service.py#L488-L517) 做两件事：

```text
conversation.send_message(message)
如果 run=True：event_service.run()
```

这说明 OpenHands 的“用户输入进入上下文”发生在 SDK `LocalConversation.send_message(...)`，不是 App Server 本地拼消息。

## 5. ConversationState：不是 messages 数组，而是上下文账本索引

执行面核心状态是 [ConversationState](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/conversation/state.py#L82-L223)。它不只是：

```text
messages: list[Message]
```

而是保存：

| 字段 / 结构 | 作用 |
|---|---|
| `agent` | 当前 conversation 使用的 agent 配置，可用于 resume / tool 校验 |
| `workspace` | agent 读写文件、执行命令的 workspace，不等于进程 cwd |
| `execution_status` | `IDLE` / `RUNNING` / `PAUSED` / `WAITING_FOR_CONFIRMATION` / `FINISHED` / `STUCK` 等运行状态 |
| `confirmation_policy` / `security_analyzer` | 审批和安全风险分析相关上下文 |
| `activated_knowledge_skills` / `invoked_skills` | skill 激活和显式调用记录 |
| `blocked_actions` / `blocked_messages` | hook 阻断 action / message 的记录 |
| `last_user_message_id` | 最近用户消息 ID，辅助 hook block 检查 |
| `leaf_event_id` / `head_is_empty` | 当前 conversation tree 的 HEAD / 空 HEAD 标记 |
| `stats` | LLM token / cost 等统计 |
| `secret_registry` | secrets 注册表，用于 dynamic context |
| `agent_state` | agent-specific runtime state |
| `hook_config` | session hooks 配置 |
| `_events` | 私有 EventLog，保存事件账本 |
| `_view` / `_view_branch_leaf` | 当前 active branch 的 View cache |

这里的关键是 [state.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/conversation/state.py#L223-L233)：

```text
_events: EventLog
_view: View
_view_branch_leaf
```

这说明 OpenHands 的上下文管理不是“一个可变 messages 列表”，而是：

```text
持久事件账本 EventLog
  + 当前分支 View cache
  + 运行状态 / skill / secret / hook / agent_state 等旁路状态
```

**精髓标记：**

> **ConversationState 是 OpenHands 的上下文账本索引；完整历史在 EventLog，模型输入来自 View。**

## 6. EventLog：完整账本；View：模型当前可见版本

OpenHands 的 EventLog 更像“完整录像带 / 审计账本”，记录 conversation 中发生过的事件。每个事件被 append 时，`ConversationState.append_event(...)` 会 stamp parent_id、写入 `_events` 并推进 HEAD：[state.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/conversation/state.py#L292-L311)。

但模型不是每次都看完整 EventLog。真正给模型看的，是当前 active branch 的 View。

[state.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/conversation/state.py#L272-L279) 中 `active_branch(...)` 会从当前 leaf 回溯到 root：

```text
active_branch = path_to_root(leaf)
```

[state.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/conversation/state.py#L314-L358) 中 `view` 属性维护 active branch 的懒加载 View：

- 如果只是线性 append，就只增量 replay tail；
- 如果 branch 切换、fork、navigation 或恢复失败，就从 active branch 重建；
- abandoned branches 不进入当前 View；
- `View.from_events(...)` 会应用 condensation 并 enforce LLM API 需要的结构约束。

通俗说：

```text
EventLog：完整录像带 / 完整账本
View：剪辑给模型看的当前剧情版
```

**精髓标记：**

> **OpenHands 每轮不是直接发送完整历史，而是从当前 active branch 投影出 View。**

## 7. conversation tree / branch：后续值得单独学习的机制

OpenHands 现在已经不只是线性 conversation history。`ConversationState` 里有：

- `leaf_event_id`
- `head_is_empty`
- `active_branch(...)`
- `append_event(...)` 的 `parent_id` stamping
- `View` 的 branch-aware cache

这些机制让 conversation 可以形成 tree / branch。Agent Server 也暴露了 fork / navigate 相关能力，适合 Agent Canvas / 远程开发平台中的回溯、分支探索、轨迹管理。

当前文档只把它作为上下文管理的关键背景记录，后续可以单独开专题继续看：

- `EventLog.path_to_root(...)` 如何组织事件树；
- fork / navigate API 如何移动 HEAD；
- abandoned branches 如何排除出当前 View；
- rerun / replay action 和分支上下文的关系；
- UI 如何展示 conversation tree / branch。

**精髓标记：**

> **OpenHands 的 context 不只是线性时间轴，而是有当前 HEAD 的 conversation tree；模型看到的是当前分支，不是所有分支。**

## 8. 哪些事件能进入模型上下文？

OpenHands 不是把所有事件都发给模型。只有继承 [LLMConvertibleEvent](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/event/base.py#L75-L80) 的事件才能转成 LLM message。

主要 LLMConvertible events：

| 事件 | LLM 里变成什么 | 源码 |
|---|---|---|
| `SystemPromptEvent` | `role="system"` message | [system.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/event/llm_convertible/system.py#L12-L85) |
| `MessageEvent` | user / assistant message | [message.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/event/llm_convertible/message.py#L25-L119) |
| `ActionEvent` | assistant tool_calls | [action.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/event/llm_convertible/action.py#L24-L144) |
| `ObservationEvent` | tool result message | [observation.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/event/llm_convertible/observation.py#L31-L57) |
| `UserRejectObservation` | action rejected tool result | [observation.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/event/llm_convertible/observation.py#L71-L120) |
| `AgentErrorEvent` | agent/tool error result | [observation.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/event/llm_convertible/observation.py#L123-L149) |

转换入口在 [base.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/event/base.py#L107-L155)：

```text
LLMConvertibleEvent.events_to_messages(events)
```

这里有一个关键细节：如果多个 `ActionEvent` 来自同一个 LLM response，会合并成一个 assistant message，保留 parallel tool calls 的结构：[base.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/event/base.py#L119-L143)。这说明 OpenHands 不只是“事件转文本”，而是努力保持 provider tool-calling 协议结构。

## 9. Agent.step：每轮调用前从 View 投影 messages

真正调用模型前，主线在 [agent.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/agent/agent.py#L645-L697)：

```text
call_context = conversation.get_llm_call_context()

_messages_or_condensation = prepare_llm_messages(
    state.view,
    condenser=self.condenser,
    llm=self.llm,
)

make_llm_completion(
    self.llm,
    _messages,
    tools=list(self.tools_map.values()),
    call_context=call_context,
)
```

[utils.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/agent/utils.py#L548-L600) 中 `prepare_llm_messages(...)` 的逻辑是：

```text
llm_convertible_events = view.events

如果有 condenser：
  condensation_result = condenser.condense(view, agent_llm=llm)
  - 如果返回 View：使用 condensed View.events
  - 如果返回 Condensation：先把 Condensation event 写入历史，本轮不继续采样 action

messages = LLMConvertibleEvent.events_to_messages(llm_convertible_events)
追加 additional_messages（如 ask_agent）
返回 messages
```

所以 OpenHands 每轮模型输入不是“历史 messages 原样 append”，而是：

```text
state.view
  -> 可选 condenser
  -> LLMConvertibleEvent.events_to_messages
  -> provider messages
```

**精髓标记：**

> **OpenHands 每轮是从事件 View 投影 messages，而不是维护一个唯一真相的 messages 数组。**

## 10. SystemPromptEvent：静态 prompt + dynamic_context 分块

Agent 初始化 state 时，[agent.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/agent/agent.py#L502-L522) 会创建 `SystemPromptEvent`：

```text
system_prompt = static_system_message
dynamic_context = get_dynamic_context(state)
tools = list(self.tools_map.values())
```

`SystemPromptEvent` 的定义在 [system.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/event/llm_convertible/system.py#L12-L40)。注释明确说明：

- `system_prompt` 是 static system prompt；
- `dynamic_context` 是 per-conversation context；
- dynamic context 作为同一 system message 的第二个 content block；
- cache markers 不在事件转换阶段加，而在 LLM 层按 provider 处理；
- 这样静态 prompt 可以跨 conversation 共享缓存，动态内容不污染静态缓存块。

`to_llm_message()` 在 [system.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/event/llm_convertible/system.py#L72-L85) 中把它转成：

```text
role="system"
content=[system_prompt, dynamic_context]
```

这和 Hermes 的 session-stable system prompt 有相似处：两者都重视稳定 prompt / prompt cache。但差异是：

| 项目 | system prompt 思路 |
|---|---|
| Hermes | session-stable system prompt snapshot，临时 recall context 不放进 system prompt |
| OpenHands | static system prompt block + dynamic_context block，同一 system message 内分层，cache marker 由 LLM 层处理 |

**精髓标记：**

> **OpenHands 把 system prompt 拆成 static block 和 dynamic_context block：静态部分利于 prompt cache，动态部分承载每个 conversation 不同的 runtime / secrets / repo / skills 信息。**

## 11. AgentContext：背景资料管理器，不是 conversation history 本身

[AgentContext](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/context/agent_context.py#L55-L75) 是 OpenHands 管理 prompt extension 的中心结构，包含：

- repository context / repo skills；
- runtime context；
- conversation instructions；
- knowledge skills；
- secrets；
- current datetime；
- system message suffix；
- user message suffix。

它不是“历史消息列表”，而是“模型应该知道的背景资料”。

用户消息进入 conversation 时，[local_conversation.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/conversation/impl/local_conversation.py#L1542-L1605) 会把 `Message` 包成 `MessageEvent`。如果 `agent_context` 触发了 knowledge skill，还会产生 `extended_content`：

```text
MessageEvent(
  source="user",
  llm_message=message,
  activated_skills=activated_skill_names,
  extended_content=extended_content,
)
```

`MessageEvent.to_llm_message()` 在 [message.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/event/llm_convertible/message.py#L116-L119) 中会把 `extended_content` 拼到原 message content 后面。

通俗说：

```text
用户原话：
  帮我修 bug

模型实际看到：
  帮我修 bug
  + 这轮由 AgentContext / skill 触发的附加背景资料
```

因此：

> **AgentContext 是 prompt 背景资料管理器；EventLog / View 才是 conversation history 到模型输入的主链路。**

## 12. ActionEvent / ObservationEvent：工具轨迹如何回到上下文

OpenHands 的工具调用不是只存在 provider 协议层，而是事件化为 Action / Observation：

```text
LLM tool_calls
  -> ActionEvent
     -> ToolDefinition / executor
        -> Observation
           -> ObservationEvent
              -> 后续 View 转成 tool result message
```

`ActionEvent.to_llm_message()` 会转成 assistant tool_calls：[action.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/event/llm_convertible/action.py#L135-L144)。

`ObservationEvent.to_llm_message()` 会转成 role=`tool` 的 message：[observation.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/event/llm_convertible/observation.py#L51-L57)。

这意味着：

- action / observation 既是平台事件；
- 也是后续 LLM 上下文的一部分；
- 还能服务 UI 展示、事件存储、审计、远程运行和轨迹导出。

**精髓标记：**

> **OpenHands 的工具结果不是孤立字符串，而是 ObservationEvent：既是环境观察，也是下一轮模型上下文中的 tool result。**

## 13. Condensation：append-only 账本上的事件化压缩

OpenHands 的压缩机制叫 condenser / condensation。它的关键点不是“直接删掉旧 messages”，而是在 append-only EventLog 上追加一个 `Condensation` 事件。

[condenser README](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/context/condenser/README.md#L13-L21) 说明：

- conversation 的核心是 append-only event log；
- append-only 结构不能直接删除旧事件；
- 所以用特殊 `Condensation` 事件标记如何 forget 旧事件、插入 summary；
- View 应用 Condensation 语义，得到当前 LLM 可见事件列表。

触发条件包括 [condenser README](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/context/condenser/README.md#L23-L30)：

1. 当前 View 达到 `max_tokens` / `max_size`；
2. 用户或 agent 显式请求 condensation；
3. agent 检测到 context window 相关错误。

Agent.step 里也有错误恢复：provider 报 malformed conversation history 或 context window exceeded 时，会触发 `CondensationRequest`，见 [agent.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/agent/agent.py#L731-L768)。

通俗说：

> **OpenHands 不撕掉旧账本，而是在账本里加一张说明：“这些旧记录对模型来说现在用这个摘要代替”。**

这和直接修改 messages list 的压缩很不一样。

**精髓标记：**

> **OpenHands 的 condensation 是事件化压缩：旧事件保留在 EventLog，模型可见的 View 应用压缩语义。**

## 14. 和 DeerFlow 的上下文管理差异

DeerFlow 和 OpenHands 都不是简单 messages append，但核心机制完全不同：

| 维度 | DeerFlow | OpenHands |
|---|---|---|
| 核心容器 | `ThreadState` | `ConversationState + EventLog` |
| 主导机制 | middleware lifecycle | event-sourced View projection |
| 模型输入来源 | state channels 经 middleware 投影 | active branch View 经 event-to-message 转换 |
| 压缩方式 | `SummarizationMiddleware` 写 `summary_text` state channel | `Condensation` event + View.apply |
| 动态上下文 | `DynamicContextMiddleware` 注入 frozen snapshot | `SystemPromptEvent.dynamic_context` + `AgentContext` |
| 工具结果 | `ToolMessage` / `Command` 进入 LangGraph state | `ObservationEvent` 转 role=`tool` message |
| 历史结构 | LangGraph messages + checkpointed state channels | append-only event log + conversation tree / branch |
| 比喻 | 状态流水线工厂 | 平台事件账本 + 当前分支剪辑 |

一句话：

```text
DeerFlow：状态通道 + 中间件投影。
OpenHands：事件账本 + 当前分支 View 投影。
```

## 15. 和其他 Harness 的横向定位

| Harness | OpenHands 相比它的差异 |
|---|---|
| Claw-Code | Claw-Code 更像本地线性 transcript；OpenHands 是远程平台事件账本，工具动作和观察都事件化、可持久化、可分支。 |
| OpenClaw | OpenClaw 强调产品态 session runtime、steer / followUp 队列；OpenHands 强调 App Server / Agent Server 分离和 workspace 事件轨迹。 |
| Hermes Agent | Hermes 强调长期个人记忆、recall context、provider survival；OpenHands 强调 SWE workspace 中 action / observation 轨迹和平台事件流。 |
| DeerFlow | DeerFlow 强调 LangGraph state channels 和 middleware projection；OpenHands 强调 EventLog / View / Condensation 的 event-sourced projection。 |

OpenHands 的上下文管理成熟点不在“记忆像 Hermes 一样丰富”，也不在“middleware 像 DeerFlow 一样原子化”，而在：

```text
平台化 SWE Agent 的轨迹管理：
  conversation 可持久化
  action / observation 可审计
  workspace 变更可追踪
  context 可从当前分支投影
  compression 不破坏原始账本
```

## 16. QA / 讨论记录

### Q: OpenHands 的上下文管理可以理解为普通 messages 数组吗？

> **状态**: verified  
> **来源**: source-code / discussion

A: 不适合。OpenHands 执行面的 `ConversationState` 私有持有 `EventLog` 和 `View` cache；模型输入来自 `prepare_llm_messages(state.view, condenser, llm)`，再由 `LLMConvertibleEvent.events_to_messages(...)` 转换。messages 是最终 provider request 的投影结果，不是唯一真相。完整历史、分支、压缩语义、action / observation 轨迹都先存在事件系统中。

### Q: OpenHands 的 conversation tree / branch 为什么重要？

> **状态**: to-verify  
> **来源**: source-code / discussion

A: 它说明 OpenHands 的上下文不只是线性 transcript。`leaf_event_id` 表示当前 HEAD，`active_branch()` 从当前 leaf 回溯当前分支，`View` 只投影当前 active branch，abandoned branches 不进入当前模型上下文。这对 Agent Canvas / 远程开发平台很重要，因为用户可能需要 fork、navigate、回到某个历史点重试或比较不同 agent 轨迹。本文已标记该点；后续可单独写 conversation tree / branch 专题继续核验 Agent Server fork / navigate API、EventLog tree 结构和 UI 展示。

### Q: OpenHands 的 Condensation 和普通 summarize messages 有什么不同？

> **状态**: verified  
> **来源**: source-code / discussion

A: 普通 summarize messages 往往直接替换或裁剪消息列表；OpenHands 在 append-only EventLog 上追加 `Condensation` 事件，由 View 应用“哪些旧事件被遗忘、插入什么 summary”的语义。因此原始事件账本仍可用于调试、审计、导出和 replay，模型上下文则看到压缩后的 View。这种设计更适合平台化 SWE Agent 的长期轨迹管理。

## 17. 小结

OpenHands context management 可以总结为：

```text
控制面准备任务材料：repo / branch / workspace / sandbox / secrets / plugins
执行面保存上下文事实：ConversationState + append-only EventLog
当前分支决定模型视角：leaf_event_id -> active_branch -> View
View 处理模型可见历史：condensation + LLMConvertibleEvent
provider request 是投影结果：View -> LLM messages
```

最终一句话：

> **OpenHands 的上下文管理是平台化 SWE Agent 的 event-sourced context system：完整历史保存在事件账本里，模型每轮只看当前分支 View。**
