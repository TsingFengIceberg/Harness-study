# Tool System 横向总结：从集中式工具中枢到分层式工具治理

> **日期**: 2026-07-02 | **状态**: draft | **涉及项目**: Claw-Code / DeerFlow / OpenHands / OpenClaw / Hermes Agent

## 相关文档

- 项目笔记：
  - [Claw-Code Tool System](../projects/claw-code/tool-system.md)
  - [Claw-Code Agent Loop](../projects/claw-code/agent-loop.md)
  - [DeerFlow Agent Loop](../projects/deer-flow/agent-loop.md)
  - [OpenHands Agent Loop](../projects/openhands/agent-loop.md)
  - [OpenClaw Tool System](../projects/openclaw/tool-system.md)
  - [OpenClaw Agent Loop](../projects/openclaw/agent-loop.md)
  - [Hermes Agent Tool System](../projects/hermes-agent/tool-system.md)
  - [Hermes Agent Loop](../projects/hermes-agent/agent-loop.md)
- 横向 QA：[qa.md](qa.md#tool-system--工具体系)
- 上一专题：[Agent Loop 横向总结](agent-loop.md)

## 本文范围

本文是 Tool System 专题的第一轮横向总结，已经完成 [Claw-Code Tool System](../projects/claw-code/tool-system.md)、[OpenClaw Tool System](../projects/openclaw/tool-system.md) 与 [Hermes Agent Tool System](../projects/hermes-agent/tool-system.md) 的源码研读，并用它们建立后续比较 DeerFlow / OpenHands 时可复用的问题框架。

因此本文中的 Claw-Code / OpenClaw / Hermes 判断已结合源码路径；DeerFlow / OpenHands 的工具系统判断暂时主要来自已完成的 Agent Loop 笔记和阶段性讨论，后续需要在各项目 `tool-system.md` 中继续源码核验。

## Tool System 不是只有 tool call

最容易误解的是：

```text
Tool System = 模型能调用几个函数
```

但在真实 Agent Harness 里，Tool System 至少包含：

```text
工具定义
工具 schema
工具注册
工具可见性
工具权限
工具执行
工具结果回写
错误恢复
hook / middleware
sandbox / workspace 边界
外部工具生态接入
子 agent / background task / worker 等高阶能力工具化
```

所以更准确地说：

> **Tool System 是 Agent 触达外部世界的能力总线。**

模型本身只产生意图和参数，Harness 通过工具系统把这些意图翻译成真实环境动作，再把 observation / tool result 回写给模型。

## Claw-Code：集中式工具中枢

Claw-Code 的工具系统主线见 [Claw-Code Tool System](../projects/claw-code/tool-system.md)。它可以概括为：

> **集中式、本地 CLI 风格的工具中枢。**

核心源码集中在 [lib.rs](../../claw-code/rust/crates/tools/src/lib.rs) 与 [conversation.rs](../../claw-code/rust/crates/runtime/src/conversation.rs)：

| 层级 | Claw-Code 做法 |
|---|---|
| 工具定义 | `ToolSpec` 定义 name、description、input_schema、required_permission。 |
| 工具注册 | `GlobalToolRegistry` 汇总 builtin / plugin / runtime tools。 |
| 工具暴露 | `definitions(...)` 转成 provider `ToolDefinition`，并按 allowed tools 过滤。 |
| 工具执行 | `ConversationRuntime::run_turn` 提取 `ToolUse`，调用 `ToolExecutor.execute`。 |
| 执行分发 | `execute_tool_with_enforcer(...)` 用大 match 分发到 `run_xxx`。 |
| 权限治理 | `PreToolUse hook + PermissionPolicy / PermissionPrompter + PermissionEnforcer` 两道门。 |
| 结果回写 | `ContentBlock::ToolResult` 写回 Session，下一轮转成 provider tool result。 |
| 工具发现 | `ToolSearch` 对 deferred tools 做目录式关键词检索。 |

### 精髓一：工具大中枢

Claw-Code 的优点是：

```text
直接
内联
可控
本地 CLI 调试直观
工具调用链短
```

代价是：

```text
mvp_tool_specs() 越来越大
execute_tool_with_enforcer() 越来越大
工具定义、schema、权限、搜索、执行分发集中在一个工具模块附近
```

这形成了一个很典型的本地 Coding CLI 取舍：

> **清楚，但重；直接，但集中；适合本地 CLI，但长期会面临工具中枢膨胀。**

### 精髓二：两道权限门

Claw-Code 不是只按工具名判断权限。

第一扇门在 [conversation.rs](../../claw-code/rust/crates/runtime/src/conversation.rs)：

```text
PreToolUse hook
  -> PermissionPolicy
    -> PermissionPrompter
```

它问：

> **这个工具类型当前能不能用？**

第二扇门在 [execute_tool_with_enforcer](../../claw-code/rust/crates/tools/src/lib.rs)：

```text
根据具体参数分类 required_mode
  -> maybe_enforce_permission_check_with_mode
    -> PermissionEnforcer.check_with_required_mode
```

它问：

> **这个具体调用参数会不会越界？**

例如：

```text
bash "git status" 和 bash "rm -rf /" 都是 bash，但风险不同。
read_file "README.md" 和 read_file "/etc/passwd" 都是 read_file，但边界不同。
write_file "DOCS/note.md" 和 write_file "~/.ssh/config" 都是 write_file，但权限不同。
```

所以两道门不是重复，而是分工：

| 门 | 问题 | 类比 |
|---|---|---|
| 第一扇门 | 能不能使用这类工具？ | 有没有资格进入工地、使用施工工具？ |
| 第二扇门 | 这次参数是否越界？ | 是在指定区域施工，还是跑去拆隔壁楼？ |

### 精髓三：ToolSearch 是工具目录，不是智能搜索 Agent

Claw-Code 的 [ToolSearch](../projects/claw-code/tool-system.md#toolsearch延迟工具发现而不是智能搜索-agent) 解决的是工具可见性问题：

> **工具很多，但不一定要一次性全部暴露给模型。**

它把工具分成：

```text
always-visible tools
  bash / read_file / write_file / edit_file / glob_search / grep_search

deferred tools
  其他专用工具，需要时通过 ToolSearch 查询
```

搜索逻辑在 [search_tool_specs](../../claw-code/rust/crates/tools/src/lib.rs)，本质是代码里的关键词匹配和打分：

```text
工具名精确匹配：高分
工具名包含 query：中分
描述 / haystack 包含 query：低分
+term：required term
select:：直接选择工具名
canonical token：归一化工具名和 query
```

这点非常关键：

> **ToolSearch 不是“智能 agent 搜索工具”，而是一个内置工具目录检索器。它像工具箱旁边的一本目录：常用扳手、螺丝刀直接放桌上；不常用的专用工具放柜子里；需要的时候先查目录，再拿出来用。**

这说明工具系统设计不只是“工具越多越好”，还要管理模型每一轮看到的工具表规模。

## OpenHands：分层式平台工具治理

OpenHands 的 Agent Loop 笔记见 [OpenHands Agent Loop](../projects/openhands/agent-loop.md)。当前理解是：OpenHands 更偏平台化 SWE Agent，不把工具系统全部塞进一个本地 tools 大文件里，而是拆成控制面 / 执行面：

```text
App Server / Agent Canvas / conversation / sandbox / event / automation
  -> 控制面：创建会话、管理 workspace/sandbox、转发消息、记录事件、展示 UI

Agent Server / software-agent-sdk / openhands-tools
  -> 执行面：运行 Conversation.run / Agent.step、执行工具、产生 ObservationEvent
```

它的工具抽象更接近：

```text
ActionEvent
  -> 工具 / runtime / workspace 执行
    -> ObservationEvent
      -> 下一轮 Agent.step
```

和 Claw-Code 对比：

| 维度 | Claw-Code | OpenHands |
|---|---|---|
| 形态 | 本地 CLI 工具中枢 | 平台控制面 / 执行面分离 |
| 工具执行位置 | 本地 runtime / tools crate | Agent Server / SDK / tools package / sandbox |
| 事件模型 | tool_use / tool_result 主线 | ActionEvent / ObservationEvent 平台事件流 |
| 优势 | 主线短、调试直观 | 多 backend、远程运行、团队共享、事件追踪 |
| 代价 | 中心模块变重 | 调试链路更长、跨 repo / service 理解成本高 |

可以概括为：

> **Claw-Code 像本地万能工具箱；OpenHands 像远程工程平台。**

## DeerFlow：LangGraph / middleware 化的工具治理

DeerFlow 的 Agent Loop 笔记见 [DeerFlow Agent Loop](../projects/deer-flow/agent-loop.md)。它的工具系统不像 Claw-Code 那样围绕一个本地 `run_turn + tools.rs` 大中枢展开，而是嵌在：

```text
Gateway run lifecycle
LangGraph agent runtime
middleware chain
sandbox / checkpoint / stream / cancel / clarification
```

里治理。

和 Claw-Code 对比：

| 维度 | Claw-Code | DeerFlow |
|---|---|---|
| Loop 位置 | 本地 `ConversationRuntime::run_turn` | Gateway worker + LangGraph runtime |
| 工具循环 | 手写提取 ToolUse、执行、回写 | 主要交给 LangGraph / LangChain agent runtime |
| 横切能力 | hook / permission / compaction 等内联插入主线 | middleware、RunManager、checkpointer、StreamBridge 等分层处理 |
| 适合场景 | 本地 Coding CLI | 长任务、图式编排、run 生命周期治理 |

可以概括为：

> **Claw-Code 把工具系统写成可顺代码读下来的本地能力中枢；DeerFlow 把工具调用放进 run lifecycle 和 middleware 体系里治理。**

## OpenClaw：事件化工具调度与产品级治理

OpenClaw 的工具系统主线见 [OpenClaw Tool System](../projects/openclaw/tool-system.md)。它可以概括为：

> **工具装配工厂 + 策略管线 + hook wrapper + 事件化执行流。**

核心源码分布在 [agent-loop.ts](../../openclaw/packages/agent-core/src/agent-loop.ts)、[types.ts](../../openclaw/packages/agent-core/src/types.ts)、[agent-tools.ts](../../openclaw/src/agents/agent-tools.ts)、[agent-tools.before-tool-call.ts](../../openclaw/src/agents/agent-tools.before-tool-call.ts) 和 [tool-search.ts](../../openclaw/src/agents/tool-search.ts)。

| 层级 | OpenClaw 做法 |
|---|---|
| 工具定义 | `AgentTool` 继承 provider-facing `Tool`，并增加 `label`、`prepareArguments`、`execute`、`executionMode`。 |
| 工具结果 | `AgentToolResult` 包含 `content`、`details`、`progress`、`terminate`，同时服务模型、UI、日志和 runtime。 |
| 工具装配 | `createOpenClawCodingTools(...)` 按 run / session / channel / model / sandbox / policy 动态组装工具面。 |
| 工具过滤 | `applyToolPolicyPipeline(...)` 按 profile、provider、agent、group、sender、sandbox、subagent、inherited policies 分层过滤。 |
| 工具治理 | `wrapToolWithBeforeToolCallHook(...)` 把 plugin hooks、trusted policies、approval、diagnostics、loop detection 包进工具执行。 |
| 工具执行 | `executeToolCalls(...)` 按全局配置和工具级 `executionMode` 判断 sequential / parallel。 |
| 事件流 | `tool_execution_start/update/end` 记录工具生命周期；`message_start/end` 记录 tool result 消息生命周期。 |
| 工具目录 | `tool_search` / `tool_describe` / `tool_call` / `tool_search_code` 管理 OpenClaw / MCP / client 大工具目录。 |

### 精髓一：工具像工单，不是裸函数

OpenClaw 可以用“餐厅后厨 / 工单调度系统”理解：

```text
模型输出 toolCall
  -> 像客人点菜 / 下工单
prepareToolCall
  -> 前台核单：工具是否存在、参数是否正确、hook 是否允许
executePreparedToolCall
  -> 厨师真正做菜 / 工人真正施工
finalizeExecutedToolCall
  -> 出餐前质检、afterToolCall patch 结果
ToolResultMessage
  -> 出餐回执 / 工单验收单，写回给模型
```

所以 OpenClaw 的重点不只是执行工具，而是把工具调用变成可观测、可审批、可并发、可持久化的事件化工单。

### 精髓二：默认并行，但遇到串行约束整批降级

OpenClaw 的 `executeToolCalls(...)` 判定逻辑是：

```text
如果 config.toolExecution === "sequential"：
  整批串行
否则：
  预扫描本批 toolCalls，解析真实 AgentTool
  如果任一工具 executionMode === "sequential"：
    整批串行
  否则：
    整批并发
```

这是一种：

> **默认并行提升效率，但遇到任何串行约束就保守降级。**

它不像 Claw-Code 那样在 `run_turn` 中固定 for-loop 串行；OpenClaw 会把一轮 assistant message 的多个 tool calls 作为 batch 调度。

### 精髓三：事件流分离“执行生命周期”和“消息生命周期”

OpenClaw 同时发两类事件：

| 事件 | 含义 |
|---|---|
| `tool_execution_start/update/end` | 工具工单被受理、进度更新、处理结束。 |
| `message_start/message_end` | 工具结果消息正式进入 transcript / session。 |

parallel 模式下，`tool_execution_end` 可以按真实完成顺序发；但最终 `ToolResultMessage` 仍按模型原始 tool call 顺序回写，保证模型上下文稳定。

### 精髓四：Tool Search 是大工具目录服务

OpenClaw 的 Tool Search 比 Claw-Code 更重。Claw-Code 的 ToolSearch 更像内置工具目录检索器；OpenClaw 的 Tool Search 则是：

```text
tool_search
tool_describe
tool_call
tool_search_code
```

它面向 OpenClaw / MCP / client 多来源大工具目录，支持搜索、查看 schema、代为调用，甚至 code-mode 受控探索。

### 和 Claw-Code 对比

| 维度 | Claw-Code | OpenClaw |
|---|---|---|
| 比喻 | 本地万能工具箱 / 老师傅 | 多端工作室 / 后厨工单调度系统 |
| 工具抽象 | `ToolSpec` + `ToolExecutor` | `AgentTool` + `AgentToolResult` |
| 工具装配 | `GlobalToolRegistry` 汇总 builtin/plugin/runtime | `createOpenClawCodingTools` 动态组装 effective tool surface |
| 工具执行 | `run_turn` 逐个串行执行 `ToolUse` | `executeToolCalls` batch 调度，支持 sequential / parallel |
| 工具结果 | 字符串 output 转 `ToolResult` | `content/details/progress/terminate` 结构化结果 |
| 权限 / policy | PermissionPolicy + PermissionEnforcer 两道门 | tool policy pipeline + before_tool_call runtime + approval / diagnostics / loop detection |
| ToolSearch | 轻量目录检索器 | 大工具目录服务，支持 search / describe / call / code-mode |

可以概括为：

> **Claw-Code 把工具系统集中在本地 runtime 中；OpenClaw 把工具系统拆成工具对象、装配管线、策略管线、hook wrapper、事件流和大工具目录。**

## Hermes Agent：长期个人 Agent 的工具工作台

Hermes 的工具系统主线见 [Hermes Agent Tool System](../projects/hermes-agent/tool-system.md)。它可以概括为：

> **toolsets 工具菜单 + registry 工具总账 + Tool Search 渐进式发现 + tool_executor 执行工作台。**

核心源码分布在 [tools/registry.py](../../hermes-agent/tools/registry.py)、[toolsets.py](../../hermes-agent/toolsets.py)、[model_tools.py](../../hermes-agent/model_tools.py)、[tool_executor.py](../../hermes-agent/agent/tool_executor.py)、[tool_dispatch_helpers.py](../../hermes-agent/agent/tool_dispatch_helpers.py)、[tools/tool_search.py](../../hermes-agent/tools/tool_search.py) 和 [tool_guardrails.py](../../hermes-agent/agent/tool_guardrails.py)。

| 层级 | Hermes 做法 |
|---|---|
| 工具注册 | 各 `tools/*.py` 模块顶层调用 `registry.register(...)` 自注册 schema / handler / check_fn / toolset。 |
| 工具菜单 | `toolsets.py` 定义 `_HERMES_CORE_TOOLS` 和可组合 `TOOLSETS`，按 `enabled_toolsets` / `disabled_toolsets` 计算工具面。 |
| 工具装配 | `get_tool_definitions(...)` 解析 toolsets、按 check_fn 过滤可用性、动态修正 schema、再做 Tool Search assembly。 |
| 工具执行 | `_execute_tool_calls(...)` 根据 `_should_parallelize_tool_batch(...)` 分派 sequential / concurrent。 |
| 并发策略 | 白名单式并发：safe tools、path 不重叠、MCP server opt-in 才并发。 |
| 工具治理 | request / execution middleware、plugin pre_tool_call、ACP edit approval、checkpoint、tool loop guardrail。 |
| 工具目录 | `tool_search` / `tool_describe` / `tool_call` 折叠 MCP / plugin 非核心工具；核心 Hermes 工具永不 deferred。 |
| 个人能力 | `memory`、`todo`、`session_search`、`skills_*`、`delegate_task`、`clarify` 等作为核心工具进入同一执行链。 |

### 精髓一：toolsets 是工具菜单，不是单个 allowed-tools 列表

Hermes 的 [toolsets.py](../../hermes-agent/toolsets.py) 把工具组织成 `web`、`terminal`、`file`、`skills`、`memory`、`session_search`、`clarify`、`delegation`、`browser`、`kanban` 等菜单。

`_HERMES_CORE_TOOLS` 包含的不只是 coding tools，还有长期个人 Agent 常用能力：

```text
web / terminal / file / browser
memory / todo / session_search / skills
clarify / delegate_task / cronjob / homeassistant / kanban / computer_use
```

这说明 Hermes 的工具系统天然服务“长期私人助理”：工具不是只帮它改代码，而是帮它记事、查历史、沉淀技能、追踪任务、询问用户、派发子 agent。

但这个“菜单”不是死菜单。Hermes 还可以通过 MCP、plugin、context engine、memory provider 等来源把新工具登记进 [ToolRegistry](../../hermes-agent/tools/registry.py)，并挂到动态 toolset 或 provider-specific 工具入口上。更准确的说法是：

> **Hermes 有可扩展菜单系统：菜单可以加菜，但不能绕过点菜系统。**

无论工具来自内置模块、MCP、plugin 还是 memory provider，正常执行前都要进入 `registry` / `toolsets` / `get_tool_definitions(...)` / `agent.valid_tool_names` / `tool_call` scope gate 这套约束。模型如果直接调用当前 session 不可见的工具，主循环会修复或拒绝；模型如果通过 `tool_call` 调隐藏工具，也必须属于当前 session 的 scoped deferrable names。

### 精髓一补充：OpenClaw 和 Hermes 都动态，但动态依据不同

这里容易误解成“OpenClaw 是动态组装，Hermes 是预定义菜单”。更准确是：两者都动态，只是动态依据不同。

```text
OpenClaw：
  动态性来自产品会话上下文。
  run / session / channel / model / sandbox / sender / policy 决定工具面。

Hermes：
  动态性来自工具总账 + 工具菜单。
  registry / toolsets / enabled_toolsets / disabled_toolsets / check_fn 决定工具面。
```

比喻：

```text
OpenClaw：多端工作室经理按当前工单场景配工具车。
  这次是 Web 端、IM channel、sandbox、subagent，都会影响工具车怎么配。

Hermes：私人助理按任务菜单从工具总账里拿工具摆上桌。
  今天启用 research 菜单、file 菜单、memory 菜单，或者接入 plugin / MCP 扩展菜单。
```

这个点是本轮讨论中比较稳定的横向结论：**OpenClaw 的动态性偏产品上下文，Hermes 的动态性偏 registry + toolsets。**

### 精髓二：Tool Search 是渐进式工具发现

Hermes 的 [tools/tool_search.py](../../hermes-agent/tools/tool_search.py) 和 Claw-Code / OpenClaw 都不同。

它的核心规则是：

```text
_HERMES_CORE_TOOLS 永远可见，不 deferred
MCP / plugin 非核心工具可被 deferred
当 deferrable schema 成本超过阈值时：
  保留 core tools
  用 tool_search / tool_describe / tool_call 代替 deferred tools
```

搜索逻辑是轻量 BM25 + 工具名 substring fallback；调用 deferred tool 时还会按当前 session 的 `enabled_toolsets` / `disabled_toolsets` 做 scope gate，避免受限 subagent / kanban worker 通过 `tool_call` 绕到全局工具。

### 精髓三：白名单式并发，而不是默认并行

Hermes 的并发判定在 [_should_parallelize_tool_batch(...)](../../hermes-agent/agent/tool_dispatch_helpers.py)。逻辑是：

```text
单工具不并发
clarify 等 never-parallel 工具不并发
参数 JSON 解析失败不并发
read_file / write_file / patch 必须有 path 且路径不重叠
工具必须在 parallel-safe 白名单，或 MCP server 显式 supports_parallel_tool_calls
全部通过才并发
```

这和 OpenClaw 的默认并行不同。Hermes 更像“安全快办窗口”：只有确认互不影响的 read/search/非重叠 path 工具才开多窗口。

### 精髓四：tool_executor 同时处理执行、记账、防循环和 steer

Hermes 的 [tool_executor.py](../../hermes-agent/agent/tool_executor.py) 不只是调用 handler。它还会：

```text
unwrap tool_call 到真实 underlying tool
运行 request middleware / execution middleware
运行 plugin pre_tool_call block
运行 tool guardrail
对文件修改 / 破坏性 terminal 做 checkpoint preflight
管理并发 worker thread 和 interrupt fan-out
持久化大工具结果并执行 turn budget
工具结果 append 后立即 flush SessionDB
把 pending steer 注入到 tool result
```

所以 Hermes 的工具执行器更像私人助理的“工作台”：每张工具工单都要记账、归档、防止原地打转，并允许用户中途补一句方向。

更精确地说，Hermes 的工具调用像一个“厚执行外壳”：

```text
conversation_loop 协议卫生层：
  修复 tool name、校验 JSON args、处理 unknown tool、追加 assistant tool-call message

tool_executor 执行前门：
  Tool Search unwrap、scope gate、request middleware、plugin block、guardrail、checkpoint、interrupt check、并发判定

执行与分发：
  agent._invoke_tool / model_tools.handle_function_call / registry.dispatch

执行后处理：
  post_tool_call、transform_tool_result、result budget、大结果持久化、SessionDB flush、steer 注入
```

这和 OpenClaw 的差异不能简单写成“谁复杂谁简单”。更准确的阶段性说法是：

```text
OpenClaw：
  更像 AgentTool 对象的标准工单生命周期。
  工具对象自带 execute / executionMode / prepareArguments，执行过程伴随 tool_execution_* 与 message_* 事件。

Hermes：
  更像 function_name + function_args 进入厚执行器外壳。
  执行器负责协议修复、Tool Search unwrap、middleware、plugin block、guardrail、checkpoint、registry dispatch、result budget、SessionDB flush 和 steer 注入。
```

不过这个点当前仍是待讲清事项：用户已经明确表示经过多轮解释后仍未真正理解 OpenClaw 和 Hermes 在“工具调用本体”上的差异。后续应选一个具体工具调用做源码级 trace，而不是继续只用“工单生命周期 vs 厚执行外壳”的抽象比喻。

### 精髓五：Hermes 的治理不能都叫权限

本轮讨论也修正了一个表达误区：不要把 Hermes 的 toolsets、scope gate、plugin hook、checkpoint、guardrail、result budget 都笼统叫“权限”。它们都是工具治理，但性质不同。

| 机制 | 问的问题 | 是否是权限？ | 比喻 |
|---|---|---|---|
| `toolsets` | 当前 Agent 能看到哪些工具？ | 不是严格权限，更像可见性 / 菜单控制 | 今天桌上摆哪些工具。 |
| `tool_call` scope gate | 通过 Tool Search bridge 调的底层工具是否属于当前 session？ | 很接近权限 | 不能拿仓库目录绕过当前授权。 |
| plugin `pre_tool_call` | 插件是否允许这次调用？ | 是执行前门 | 助理主管说这事不能办。 |
| ACP edit approval | 写文件 / patch 是否需要审批？ | 是权限 / HITL | 改文件前要用户盖章。 |
| checkpoint | 执行前是否保存现场？ | 不是权限，是回滚保险 | 动工前拍照留档。 |
| guardrail | 是否重复失败 / 无进展？ | 不是权限，是防循环 | 别在同一个抽屉翻五遍。 |
| result budget | 工具结果是否太大、会污染上下文？ | 不是权限，是上下文保护 | 文件太厚就归档，不全塞桌面。 |
| SessionDB flush | 工具结果是否及时落盘？ | 不是权限，是持久化 / 恢复 | 每办完一件事马上写日志。 |
| steer injection | 用户中途补充方向如何进入下一轮？ | 不是权限，是交互控制 | 在工具回执上贴便签。 |

一句话：

> **toolsets 管“看得见”；scope gate 管“别越权绕路”；plugin / approval 管“能不能执行”；checkpoint 管“能不能回滚”；guardrail 管“别原地打转”；result budget 管“别撑爆上下文”。**

这也让横向比较更严谨：Claw-Code / OpenClaw / Hermes 都有可见性门、执行前门、参数风险、审批、执行后 hook 和错误/循环处理；差异在于这些门被放在本地 runtime、产品 policy pipeline，还是 Hermes 的 toolsets + plugin hook + executor 外壳中。

### 和 Claw-Code / OpenClaw 对比

| 维度 | Claw-Code | OpenClaw | Hermes Agent |
|---|---|---|---|
| 比喻 | 本地万能工具箱 / 老师傅 | 多端工作室 / 后厨工单调度系统 | 长期私人助理的工具工作台 |
| 工具注册 | `ToolSpec` + `GlobalToolRegistry` 中心化 | 多 TS factory 组装 `AgentTool` | tools 模块自注册到 `ToolRegistry`，toolsets 组合工具面 |
| 工具可见性 | allowed tools + deferred ToolSearch | policy pipeline + 大工具目录服务 | enabled/disabled toolsets + check_fn + Tool Search progressive disclosure |
| Tool Search | 轻量关键词目录 | search / describe / call / code-mode | core tools 永不 deferred；MCP / plugin 非核心工具用 BM25 search + describe + call |
| 并发策略 | 已读主线固定串行 | 默认并行，遇 sequential 整批降级 | 白名单式并发：safe tools、path 不重叠、MCP opt-in 才并发 |
| 治理重点 | 权限两道门 | policy pipeline / approval / event lifecycle | toolsets 可见性、scope gate、plugin hook、ACP approval、checkpoint、guardrail、result budget 分工治理 |
| 长期个人能力 | 非核心定位 | 多端 session 产品能力强 | memory / todo / session_search / skills 深度工具化 |

可以概括为：

> **Hermes 的 Tool System 不是最集中，也不是最事件化，而是最“个人 Agent 化”：工具菜单、记忆、技能、历史检索、子 agent、用户 steer、会话持久化和多 provider 兼容被缝在同一条工具执行链上。**

## 三者对比：工具箱、后厨工单、私人助理工作台

本轮讨论中，Claw-Code / OpenClaw / Hermes 的工具系统可以用三个工作场所来理解：

| 项目 | 总比喻 | Tool System 的核心气质 |
|---|---|---|
| Claw-Code | 本地老师傅 / 单人工具箱 | 工具集中、主线直接、一个个干。 |
| OpenClaw | 多端工作室 / 餐厅后厨工单系统 | 工单化、事件化、默认追求并行效率。 |
| Hermes Agent | 长期私人助理的工作台 | 工具 + 记忆 + 技能 + 历史 + 用户插话融合在一起。 |

### 工具组装：不是“动态 vs 静态”，而是动态依据不同

OpenClaw 和 Hermes 都不是简单静态工具列表。区别在于动态依据：

```text
OpenClaw：产品上下文驱动
  run / session / channel / model / sandbox / sender / policy
  -> 当前这辆工具车怎么配

Hermes：工具总账 + 工具菜单驱动
  registry / toolsets / enabled_toolsets / disabled_toolsets / check_fn
  -> 当前桌面摆哪些工具
```

比喻上：

```text
OpenClaw 像多端工作室经理：
  看这次工单来自 Web、IM、sandbox、subagent 还是某个 group/sender，
  再按产品上下文配一辆工具车。

Hermes 像长期私人助理：
  办公室里有工具总账，桌上有任务菜单，
  今天做 research 就拿 web / session_search，
  今天做 coding 就拿 file / terminal / patch，
  接了 MCP / plugin 就把新能力登记成扩展菜单。
```

所以“toolsets 是预定义菜单”不等于 Hermes 不能有菜单之外的工具。MCP、plugin、context engine、memory provider 都可能加菜；但它们仍要进入 registry / toolsets / valid_tool_names / scope gate，不能绕过点菜系统。

### 工具可见性：谁放桌面，谁放仓库

| 项目 | Tool Search 比喻 | 核心策略 |
|---|---|---|
| Claw-Code | 工具箱旁边的轻量目录 | 基础工具默认可见，专用工具 deferred。 |
| OpenClaw | 多端工作室的中央工具仓库服务 | 面向 OpenClaw / MCP / client 多来源 catalog，支持 search / describe / call / code-mode。 |
| Hermes | 私人助理的桌面核心工具 + 插件仓库 | `_HERMES_CORE_TOOLS` 永不 deferred；MCP / plugin 非核心工具过大时用 search / describe / call 渐进暴露。 |

这个差异说明 Tool Search 不只是“有没有搜索工具”，而是在管理模型每轮看到的工具表规模：Claw-Code 控制本地工具箱噪音，OpenClaw 管理多来源大 catalog，Hermes 保护 memory / todo / session_search / skills 等个人核心工具始终在桌面上。

### 串行 / 并发：性能细节背后的架构性格

本轮最重要的结论之一是：串行 / 并发不是单纯性能优化，而是架构取舍。

| 项目 | 策略 | 比喻 | 体现的架构性格 |
|---|---|---|---|
| Claw-Code | 已读主线中固定串行 | 老师傅一个人按顺序干活 | 本地 CLI，清楚、直接、可控。 |
| OpenClaw | 默认并发；任一 sequential 工具让整批降级 | 后厨默认多窗口，有特殊菜就整批排队 | 多端产品 runtime，追求效率和事件调度。 |
| Hermes | 白名单式并发；确认安全才并发 | 私人助理只把安全快办件并行分派 | 长期个人 Agent，保守处理状态、副作用和用户交互。 |

最浓缩可以记成：

```text
Claw-Code：顺序是默认秩序。
OpenClaw：并发是默认效率，sequential 是刹车。
Hermes：安全是默认前提，并发是通过审查后的加速。
```

这点尤其能解释 OpenClaw 和 Hermes 的差异：OpenClaw 让工具对象自己声明 `executionMode`，执行器默认争取 batch 并发；Hermes 没有统一把并发标签放在工具对象上，而是由 `_should_parallelize_tool_batch(...)` 依据 safe 白名单、path overlap 和 MCP opt-in 判断。

### 工具调用本体：从“未讲清”到“调用承载物不同”

三者最小 loop 都是：模型发起 tool call，Harness 执行工具，tool result 回写给模型。因此不能把差异夸大成“完全不同物种”。本轮真正讲清的点是：**一次工具调用在 runtime 里由什么东西承载**。

```text
Claw-Code：
  本地 runtime 直接提取 ToolUse，逐个执行并回写 ContentBlock::ToolResult。

OpenClaw：
  toolCall 会先归属到已有 AgentTool 工具定义对象。
  这个 AgentTool 不是用完即销毁的一次性对象，而像长期存在的工位 / 菜谱。
  每次 toolCall 是一张新工单，找到对应 AgentTool 后，
  再跑 prepareArguments / validate / beforeToolCall / execute / afterToolCall，
  并伴随 tool_execution_* 与 message_* 事件。

Hermes：
  tool_call 主要被拆成 function_name + function_args 这个请求包。
  它进入厚执行器外壳，经过协议修复、Tool Search unwrap、scope gate、middleware、plugin block、guardrail、checkpoint，
  中段再 agent._invoke_tool(function_name, function_args) / registry dispatch，
  执行后继续 result budget、SessionDB flush 和 steer 注入。
```

此前容易误解成：

```text
OpenClaw：先生成一个一次性工具执行对象，执行完再重新生成候选对象。
Hermes：对象未生成前先对参数做检查，通过外壳后才执行。
```

这个理解需要修正：

```text
OpenClaw：
  不是每次新造并消耗 AgentTool。
  更准确是：这次 toolCall 找到当前工具列表里已有的 AgentTool，
  然后围绕这个工具定义跑一套标准工单流程。

Hermes：
  也不是没有工具定义对象。
  更准确是：执行阶段的主要变量是 function_name / function_args / tool_call_id / agent context，
  这个调用请求在执行器里被层层检查、改写、阻断、执行、归档。
```

用三层区分更清楚：

```text
工具定义 Tool Definition：
  OpenClaw 的 AgentTool；Hermes 的 registry entry / schema / handler。

候选工具列表 tools exposed to model：
  每轮模型请求前给模型看的菜单，可能动态重算。

工具调用实例 toolCall：
  模型这一轮实际点的一张工单，有 id、name、arguments。
```

OpenClaw 的关键动作是：

```text
toolCall 实例 -> 找到 AgentTool 定义 -> 按 AgentTool 标准流程执行
```

Hermes 的关键动作是：

```text
tool_call 实例 -> 拆出 function_name + args -> 经过厚执行器管线 -> dispatch handler
```

最短记忆版：

> **OpenClaw：toolCall 找到 `AgentTool`，进入工具对象承载的标准工单流程。Hermes：toolCall 拆成 `function_name + args`，进入厚执行器流水线。**

### 权限 / 治理：先承认共性，再看组织位置

此前若写成“Claw-Code 是权限、OpenClaw 是 policy、Hermes 是 guardrail”，会显得强行贴标签。更准确的说法是：成熟工具系统都会面对同一组门：

```text
工具是否可见？
当前 session 是否允许？
参数是否危险？
是否需要用户审批？
执行前后是否要 hook？
失败 / 循环是否要拦？
```

差异在这些门放在哪：

| 项目 | 更中心的位置 | 更准确说法 |
|---|---|---|
| Claw-Code | 本地 runtime + tools enforcer | 集中式权限门比较清楚，尤其是工具类型与具体参数两道门。 |
| OpenClaw | 产品 policy pipeline + before_tool_call runtime | 多上下文产品策略更突出。 |
| Hermes | toolsets / plugin hooks / ACP approval / scope gate / checkpoint / guardrail 分散在执行链 | 治理更分散；guardrail 主要防循环，不应等同权限。 |

Hermes 尤其需要拆开：`toolsets` 管“看得见”；`tool_call` scope gate 管“别越权绕路”；plugin / ACP approval 管“能不能执行”；checkpoint 管“能不能回滚”；guardrail 管“别原地打转”；result budget 管“别撑爆上下文”。

### 工具结果回写：结果不是简单字符串

| 项目 | 结果回写重点 |
|---|---|
| Claw-Code | 工具 output 转成 `ToolResult` / session content，下一轮模型继续。 |
| OpenClaw | `tool_execution_*` 记录执行生命周期，`message_*` 记录 tool result 消息生命周期；二者服务 UI/runtime 与 transcript/model context 的不同需求。 |
| Hermes | 工具结果还要经过 multimodal 适配、大结果持久化、turn budget、SessionDB flush 和 pending steer 注入；结果是长期协作状态载体。 |

比喻上：Claw-Code 是老师傅把结果写回工作单；OpenClaw 是后厨大屏和账单归档分开；Hermes 是私人助理把结果写日志、归档厚材料，并把用户中途补充贴成便签。

## 横向分类法

第一轮可以把 Tool System 分成几类：

### 集中式本地工具中枢

代表：Claw-Code。

```text
工具定义、schema、权限、搜索、执行分发集中在本地工具模块；Agent Loop 内联串起 hook / permission / execute / result。
```

优势是直观、可控、本地 CLI 体验好；代价是工具越多，中心模块越重。

### 分层式平台工具治理

代表：OpenHands。

```text
控制面管理 conversation / sandbox / event / UI；执行面通过 Agent Server / SDK / tools package 跑工具，并产生 Action / Observation 事件。
```

优势是远程运行、多 backend、团队协作、自动化和事件追踪；代价是链路长。

### Workflow / middleware 化工具治理

代表：DeerFlow。

```text
工具调用被吸收到 LangGraph agent runtime，横切能力通过 middleware、checkpoint、run lifecycle、sandbox 等机制治理。
```

优势是长任务治理和流程编排；代价是最小 tool loop 不像本地 CLI 那样一眼可见。

### 事件驱动 session 工具系统

代表：OpenClaw。

```text
工具调用被 AgentSession / Agent / runLoop 的事件状态机包裹，通过工具装配工厂、策略管线、before_tool_call wrapper、sequential/parallel 调度和 Tool Search 目录服务治理。
```

### 长期个人 Agent 工具系统

代表：Hermes Agent。

```text
toolsets / registry / Tool Search / tool_executor 共同组成个人 Agent 工具工作台；memory、todo、session_search、skills、delegate_task、clarify 等长期协作能力通过同一工具执行链进入模型循环。
```

优势是个人能力和工具执行融合深，适合跨会话长期协作；代价是执行器要同时处理 provider 兼容、middleware、guardrail、interrupt、steer、budget、persistence，工程复杂度高。

## 最浓缩版

如果只记一个结论：

> **Tool System 是 Agent 的能力总线；不同 Harness 的差异，不只是有哪些工具，而是工具定义、可见性、权限、执行、结果回写和横切治理被放在什么架构位置。**

如果只记 Claw-Code：

> **Claw-Code 是集中式工具中枢：直接、内联、可控；ToolSearch 则通过“常用工具默认可见 + 专用工具延迟发现”控制工具表规模。**

如果只记 OpenClaw：

> **OpenClaw 是事件化工具调度：工具像工单，经过装配、策略过滤、hook wrapper、sequential / parallel batch 调度和事件生命周期。**

如果只记 Hermes：

> **Hermes 是长期个人 Agent 的工具工作台：toolsets 是工具菜单，registry 是工具总账，Tool Search 是工具仓库目录，tool_executor 把记忆、技能、steer、防循环和会话持久化缝进工具执行链。**

如果和其他项目比：

```text
Claw-Code：本地万能工具箱 / 集中式工具中枢
OpenHands：远程工程平台 / 控制面与执行面分离
DeerFlow：工作流工厂 / LangGraph + middleware 治理
OpenClaw：多端工作室 / 事件化工具调度与产品级治理
Hermes：长期私人助理 / toolsets + memory + skills 的工具工作台
```

## QA / 讨论记录


### Q: OpenClaw 的工具执行为什么要区分 sequential / parallel？

> **状态**: draft
> **来源**: discussion / source-code

A: 因为一轮 assistant message 可能包含多个 tool calls，其中有些天然可以并发，如读取、查询、远程 fetch；有些则可能有共享状态或外部副作用，如写文件、发消息、操作进程、审批型工具。OpenClaw 默认并行提升效率，但如果全局配置或任一工具 `executionMode` 要求 sequential，就整批保守降级为串行，避免状态和副作用交错。

### Q: OpenClaw 的 `tool_execution_end` 和 `message_end` 是重复的吗？

> **状态**: draft
> **来源**: discussion / source-code

A: 不是。`tool_execution_end` 表示工具工单处理结束，主要服务 UI / runtime / diagnostics；`message_end` 表示工具结果消息已经进入 transcript / session，主要服务消息生命周期和下一轮模型上下文。parallel 模式下工具完成顺序和 tool result 回写顺序可能不同，因此二者需要分离。

### Q: 为什么 Tool System 专题不继续叫 tool-calling？

> **状态**: draft
> **来源**: discussion

A: `tool-calling` 更像协议层术语，强调模型发起 tool call、Harness 返回 tool result；`tool-system` 范围更大，包含工具定义、注册、schema、权限、hook/middleware、sandbox、工具可见性、工具执行、结果回写、MCP/plugin/runtime 扩展、子 agent / task / worker 等高阶能力工具化。对于横向研究 Harness，`tool-system` 更能覆盖真实工程复杂度。

### Q: Claw-Code 的 ToolSearch 为什么是精髓？

> **状态**: draft
> **来源**: discussion / source-code

A: 因为它体现了工具系统的可见性管理：常用基础工具默认放在桌面上，专用工具放进 deferred 目录，需要时用 ToolSearch 做关键词检索。它不是智能搜索 Agent，而是内置工具目录。这个设计避免把所有工具一次性塞给模型，减少 prompt 负担和工具选择噪音。

### Q: 集中式工具中枢是缺点吗？

> **状态**: draft
> **来源**: discussion / source-code

A: 不是单纯缺点，而是一种本地 CLI 取舍。集中式工具中枢让 Claw-Code 的主线非常直观，本地调试和源码学习都方便；但随着工具数量增加，`mvp_tool_specs()`、执行分发、权限分类和工具搜索都会集中膨胀，长期维护压力上升。横向比较时应写成“直接可控但中心化变重”，而不是简单评价好坏。
