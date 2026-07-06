# Hermes Agent Tool System：toolsets、渐进式工具发现与个人 Agent 工具工作台

> **日期**: 2026-07-02 | **状态**: draft | **涉及版本**: `9be39de0f2afc8adc58f8f37970f26a6d7e734a0`

## 相关文档

- 项目入口：[README.md](README.md)
- Agent Loop：[agent-loop.md](agent-loop.md)
- 横向对比：[Tool System 横向总结](../../comparison/tool-system.md)
- 横向 QA：[qa.md](../../comparison/qa.md#tool-system--工具体系)

## 源码入口

| 模块 | 源码 | 作用 |
|---|---|---|
| 工具注册中心 | [tools/registry.py](../../../submodules/hermes-agent/tools/registry.py) | `ToolRegistry`、`registry.register(...)`、schema / handler / check_fn / toolset 元数据、同步/异步 dispatch。 |
| 工具集定义 | [toolsets.py](../../../submodules/hermes-agent/toolsets.py) | `_HERMES_CORE_TOOLS`、`TOOLSETS`、`resolve_toolset(...)`、平台 bundle 与 plugin / MCP toolset 解析。 |
| 工具定义装配 | [model_tools.py](../../../submodules/hermes-agent/model_tools.py) | `discover_builtin_tools()`、`get_tool_definitions(...)`、toolset 过滤、schema 动态修正、Tool Search assembly、`handle_function_call(...)`。 |
| Agent 初始化 | [agent_init.py](../../../submodules/hermes-agent/agent/agent_init.py) | `enabled_toolsets` / `disabled_toolsets`、`agent.tools`、`agent.valid_tool_names`、`ToolCallGuardrailController` 初始化。 |
| 系统提示注入 | [system_prompt.py](../../../submodules/hermes-agent/agent/system_prompt.py)、[prompt_builder.py](../../../submodules/hermes-agent/agent/prompt_builder.py) | memory / session_search / skills / parallel tool calls / tool-use enforcement 等工具行为提示。 |
| 主循环工具分支 | [conversation_loop.py](../../../submodules/hermes-agent/agent/conversation_loop.py) | tool_calls 名称修复、JSON 参数校验、assistant tool-call message 追加、调用 `_execute_tool_calls(...)`。 |
| 工具执行入口 | [run_agent.py](../../../submodules/hermes-agent/run_agent.py) | `_execute_tool_calls(...)` 根据 batch 安全性分派 sequential / concurrent；`_invoke_tool(...)` 转发到 runtime helper。 |
| 并发判定 | [tool_dispatch_helpers.py](../../../submodules/hermes-agent/agent/tool_dispatch_helpers.py) | `_should_parallelize_tool_batch(...)`、parallel-safe 白名单、path overlap 判定、MCP parallel flag。 |
| 工具执行器 | [tool_executor.py](../../../submodules/hermes-agent/agent/tool_executor.py) | `execute_tool_calls_concurrent(...)` / `execute_tool_calls_sequential(...)`、Tool Search unwrap、middleware、guardrail、checkpoint、result 回写、steer 注入。 |
| Tool Search | [tools/tool_search.py](../../../submodules/hermes-agent/tools/tool_search.py) | progressive disclosure：`tool_search` / `tool_describe` / `tool_call`，BM25 catalog、scope gate、bridge dispatch。 |
| 工具循环 guardrail | [tool_guardrails.py](../../../submodules/hermes-agent/agent/tool_guardrails.py) | 重复失败、同工具失败、只读无进展重复调用的 warning / block / halt 控制器。 |
| 工具结果分类 | [tool_result_classification.py](../../../submodules/hermes-agent/agent/tool_result_classification.py) | 文件修改结果是否真正 landed 的辅助分类。 |

## 一句话总结

Hermes Agent 的 Tool System 可以概括为：

> **以 toolsets 为工具菜单、以 registry 为工具总账、以 Tool Search 压缩大工具面、以 tool_executor 串起 middleware / guardrail / interrupt / steer 的长期个人 Agent 工具工作台。**

如果用比喻理解：

```text
Claw-Code：本地万能工具箱，老师傅把工具都放在手边。
OpenClaw：多端后厨工单系统，工具调用被事件化调度和审批。
Hermes：长期私人助理的工作台，常用工具放桌面，插件/MCP 工具放工具仓库，需要时查目录；执行时还会记账、限流、防循环、接收用户中途扶方向盘。
```

Hermes 不只是“有很多工具”。它把工具系统和长期个人 Agent 的能力深度耦合：memory、todo、skills、session_search、delegate_task、clarify、MCP / plugin、provider 兼容、interrupt、steer、session persistence 都会经过工具装配或工具执行路径。

## 总体流程

Hermes 工具调用主链路可以压缩成：

```text
tools/*.py 顶层 registry.register(...)
  -> model_tools.discover_builtin_tools() 导入自注册工具
    -> toolsets.resolve_toolset(enabled/disabled)
      -> registry.get_definitions(...) 按 toolset + check_fn 取 schema
        -> model_tools.get_tool_definitions(...)
          -> 动态 schema 修正 / schema sanitizer
          -> Tool Search assembly：必要时把 MCP/plugin 工具折叠成 search/describe/call
            -> agent_init.init_agent 写入 agent.tools / agent.valid_tool_names
              -> system_prompt 根据有效工具注入 memory/skills/parallel guidance
                -> conversation_loop 收到 assistant.tool_calls
                  -> 修复 tool name / 校验 JSON args / 追加 assistant tool-call message
                    -> run_agent._execute_tool_calls 判断 sequential / concurrent
                      -> tool_executor 运行 request middleware / plugin hook / guardrail / checkpoint
                        -> agent._invoke_tool 或 model_tools.handle_function_call
                          -> registry.dispatch(handler)
                            -> post_tool_call / transform_tool_result / budget / persistence
                              -> make_tool_result_message 写回 messages
                                -> apply_pending_steer_to_tool_results
                                  -> 下一轮模型看到 tool result 后继续推理
```

这条链路说明 Hermes 的工具系统不是单点函数分发，而是一个围绕长期会话运转的工具工作台：工具从注册、可见性、提示词指导、协议修复、执行调度、插件拦截、防循环、结果预算、会话持久化到用户中途 steer，都会在这条链上发生。

## registry：工具总账，而不是一个静态列表

Hermes 的工具注册中心在 [tools/registry.py](../../../submodules/hermes-agent/tools/registry.py)。文件头说明每个工具文件会在模块导入时调用 `registry.register(...)` 自注册，`model_tools.py` 负责触发 discovery。

### discover_builtin_tools：导入即注册

[discover_builtin_tools(...)](../../../submodules/hermes-agent/tools/registry.py#L58) 会扫描 [tools/](../../../submodules/hermes-agent/tools/) 下包含顶层 `registry.register(...)` 的模块并导入它们。对应调用在 [model_tools.py:188](../../../submodules/hermes-agent/model_tools.py#L188)：

```text
model_tools import tools.registry.registry
  -> discover_builtin_tools()
    -> import tools/*.py
      -> 每个工具模块顶层 registry.register(...)
```

这和 Claw-Code 的中心化 `mvp_tool_specs()` 不同：Hermes 的 schema 和 handler 主要分散在各工具模块中，注册中心统一收账。

### ToolEntry：schema、handler 和可用性都在一起

`ToolRegistry.register(...)` 位于 [registry.py:356](../../../submodules/hermes-agent/tools/registry.py#L356)。每个 `ToolEntry` 保存：

```text
name
  工具名

toolset
  所属工具集

schema
  provider-facing function schema

handler
  实际执行函数

check_fn
  可用性探针，例如 Docker / Playwright / API key / 环境变量是否满足

requires_env
  所需环境变量

is_async
  是否异步 handler

description / emoji / max_result_size_chars / dynamic_schema_overrides
  UI、预算、动态 schema 调整等产品化元数据
```

`registry.get_definitions(...)` 位于 [registry.py:521](../../../submodules/hermes-agent/tools/registry.py#L521)，会按工具名集合取 schema，并用 `check_fn` 过滤不可用工具。`check_fn` 结果带 TTL 和 transient failure grace，避免 Docker / 外部依赖瞬时波动时把工具从当前 turn 中误删。

`registry.dispatch(...)` 位于 [registry.py:574](../../../submodules/hermes-agent/tools/registry.py#L574)，根据工具名找到 handler；如果是 async handler，会通过 [model_tools.py](../../../submodules/hermes-agent/model_tools.py) 中的 `_run_async(...)` 桥接到同步调用路径。

## toolsets：工具菜单和场景化工具面

Hermes 的工具可见性核心不是一个简单 `allowed_tools` 字符串列表，而是 [toolsets.py](../../../submodules/hermes-agent/toolsets.py) 中的 toolset 系统。

### _HERMES_CORE_TOOLS：长期个人 Agent 的基础工具面

`_HERMES_CORE_TOOLS` 定义在 [toolsets.py:31](../../../submodules/hermes-agent/toolsets.py#L31)，包含 Hermes 默认认为个人 Agent 常用的一组能力：

```text
web_search / web_extract
terminal / process
read_file / write_file / patch / search_files
vision / image_generate
skills_list / skill_view / skill_manage
browser_*
text_to_speech
todo / memory
session_search
clarify
execute_code / delegate_task
cronjob
homeassistant
kanban
computer_use
```

这组工具很能体现 Hermes 定位：它不是单纯 coding CLI，而是把“查网页、操作文件、跑命令、管理 todo、写 memory、检索历史、沉淀 skills、派发子 agent、智能家居、多端任务协作”等都放进同一个个人助理工具面。

### TOOLSETS：可组合的工具菜单

`TOOLSETS` 位于 [toolsets.py:95](../../../submodules/hermes-agent/toolsets.py#L95)。它把工具分成 `web`、`terminal`、`file`、`skills`、`memory`、`session_search`、`clarify`、`delegation`、`browser`、`homeassistant`、`kanban` 等场景工具集，也包含多个平台 bundle。

`resolve_toolset(...)` 位于 [toolsets.py:665](../../../submodules/hermes-agent/toolsets.py#L665)，负责把一个 toolset 名称展开为真实工具名。`validate_toolset(...)` 位于 [toolsets.py:832](../../../submodules/hermes-agent/toolsets.py#L832)，用于判断 toolset 是否存在。平台 bundle 的 disabled 处理还会用到 [bundle_non_core_tools(...)](../../../submodules/hermes-agent/toolsets.py#L637)，避免禁用某个平台 bundle 时误删 `_HERMES_CORE_TOOLS`。

### enabled_toolsets / disabled_toolsets

[agent_init.py](../../../submodules/hermes-agent/agent/agent_init.py) 的 `init_agent(...)` 参数包含 `enabled_toolsets` 和 `disabled_toolsets`，见 [agent_init.py:179-180](../../../submodules/hermes-agent/agent/agent_init.py#L179-L180)。初始化时会把它们保存到 agent 上，见 [agent_init.py:495-496](../../../submodules/hermes-agent/agent/agent_init.py#L495-L496)。

工具定义装配入口在 [agent_init.py:1052-1056](../../../submodules/hermes-agent/agent/agent_init.py#L1052-L1056)：

```text
agent.tools = get_tool_definitions(
  enabled_toolsets=enabled_toolsets,
  disabled_toolsets=disabled_toolsets,
  quiet_mode=agent.quiet_mode,
)
```

随后 `agent.valid_tool_names` 从 `agent.tools` 中建立，见 [agent_init.py:1059-1062](../../../submodules/hermes-agent/agent/agent_init.py#L1059-L1062)。后续 conversation loop 会用它校验模型是否调用了不存在的工具。

### 菜单不是死菜单：MCP / plugin / provider 可以“加菜”

Hermes 预定义了很多 toolsets，但这不是封闭菜单。更准确地说：

> **Hermes 有一套可扩展菜单系统：菜单可以加菜，但不能绕过点菜系统。**

典型“菜单之外但进入菜单体系”的来源包括：

| 来源 | 如何进入工具系统 | 理解 |
|---|---|---|
| 内置工具 | `tools/*.py` 顶层 `registry.register(...)` | 默认写进工具总账。 |
| MCP 工具 | MCP server 发现后注册到 registry，并归入类似 `mcp-<server>` 的 toolset | 外部工具服务变成动态菜单。 |
| plugin 工具 | plugin 注册新工具 / toolset | 用户或生态扩展菜单。 |
| context engine | runtime context engine 暴露上下文工具 | 根据运行时环境临时加工具。 |
| memory provider | `agent._memory_manager.has_tool(...)` / `handle_tool_call(...)` | 外部记忆系统提供自己的工具入口。 |

但是，无论工具来自哪里，正常执行前都要进入以下约束：

```text
registry 登记
  -> toolset / enabled_toolsets / disabled_toolsets 解析
    -> get_tool_definitions(...) 生成 agent.tools
      -> agent.valid_tool_names 校验
        -> Tool Search bridge 还要做 scoped_deferrable_names gate
```

如果模型直接调用一个当前菜单之外 / 当前 session 不可见的工具，Hermes 不会直接执行。主循环会先尝试修复近似工具名；修复失败时，会把 unknown tool error 作为 tool result 交还给模型，让模型下一轮自我修正。若模型通过 `tool_call` bridge 调隐藏工具，也必须通过当前 session 的 scope gate，不能借 Tool Search 绕过 `enabled_toolsets` / `disabled_toolsets`。

比喻：

```text
私人助理有固定菜单，但可以接入外包公司 / 插件 / MCP 服务。
新服务会先登记进工具总账，并挂到某个菜单下。
菜单可以扩展，但不能让模型绕过菜单系统直接闯进仓库拿工具。
```

## get_tool_definitions：从工具总账算出本轮有效工具面

`get_tool_definitions(...)` 位于 [model_tools.py:279](../../../submodules/hermes-agent/model_tools.py#L279)，是 Hermes 工具暴露给模型前的总装配入口。

它的职责包括：

| 阶段 | 作用 |
|---|---|
| toolset 解析 | `enabled_toolsets` 非空时只展开这些 toolsets；否则默认展开所有 toolsets。 |
| disabled subtraction | `disabled_toolsets` 永远作为最后的减法，确保显式禁用生效。 |
| registry schema 获取 | 调 `registry.get_definitions(...)`，并按 `check_fn` 过滤不可用工具。 |
| 动态 schema 修正 | 例如 `execute_code` schema 会只列出当前真实可用的 sandbox tools。 |
| provider/schema 兼容 | `sanitize_tool_schemas(...)` 清理后端不兼容 schema。 |
| Tool Search assembly | 工具面太大时，把 MCP / plugin 非核心工具折叠成桥接工具。 |

这一步很像“开工前配工具车”：根据当前场景、profile、平台、依赖可用性和配置，算出这一轮模型真正能看到的工具表。

## Tool Search：渐进式工具发现

Hermes 的 Tool Search 在 [tools/tool_search.py](../../../submodules/hermes-agent/tools/tool_search.py)。文件头直接说明它是 progressive tool disclosure：当启用时，用 `tool_search`、`tool_describe`、`tool_call` 三个桥接工具替换 MCP 和非核心 plugin 工具。

### 哪些工具会被延迟暴露？

`classify_tools(...)` 位于 [tool_search.py:189](../../../submodules/hermes-agent/tools/tool_search.py#L189)。核心规则是：

```text
_HERMES_CORE_TOOLS 永不 deferred
bridge tools 自身永不 deferred
MCP 工具可以 deferred
非核心 plugin 工具可以 deferred
```

这和 Claw-Code 的“基础工具 always-visible，专用工具 deferred”方向类似，但 Hermes 更明确地保护 `_HERMES_CORE_TOOLS`：memory、todo、session_search、skills、file / terminal 等核心个人助理工具不会被藏起来。

### 什么时候启用 Tool Search？

`should_activate(...)` 位于 [tool_search.py:234](../../../submodules/hermes-agent/tools/tool_search.py#L234)。配置支持：

```text
off   -> 永不启用
on    -> 有 deferrable tools 就启用
auto  -> 当 deferrable schemas token 成本超过 context_length 的 threshold_pct 时启用
```

默认 `threshold_pct` 是 10%。如果无法解析 context length，则使用 20K token 固定阈值兜底。

`assemble_tool_defs(...)` 位于 [tool_search.py:529](../../../submodules/hermes-agent/tools/tool_search.py#L529)。真正启用时：

```text
visible core tools 保留
MCP / plugin deferrable tools 从 tools array 移除
追加 tool_search / tool_describe / tool_call 三个 bridge tools
```

这说明 Hermes 的 Tool Search 是“工具表压缩器”，不是让模型自由探索任意外部能力。

### 如何搜索？

`search_catalog(...)` 位于 [tool_search.py:378](../../../submodules/hermes-agent/tools/tool_search.py#L378)。Hermes 使用一个小型 BM25 实现，对工具名、描述和顶层参数名做检索；如果 BM25 没命中，会退回工具名 substring match。

相比 Claw-Code 的关键词打分，Hermes 的检索更像一个轻量 IR catalog；相比 OpenClaw 的 `tool_search_code`，Hermes 当前没有 code-mode 工具目录探索，而是 search / describe / call 三段式桥接。

### 为什么要 scope gate？

`tool_call` 这个 bridge 最危险：如果它可以调用任何全局 registry 中的 deferrable tool，就会绕过 subagent、gateway session、kanban worker 等场景的 toolset 限制。

Hermes 做了两层防线：

1. `model_tools.handle_function_call(...)` 的 Tool Search bridge dispatch 会用当前 session 的 `enabled_toolsets` / `disabled_toolsets` 重建 pre-assembly 工具表，见 [model_tools.py:950-1007](../../../submodules/hermes-agent/model_tools.py#L950-L1007)。
2. `tool_executor.py` 在执行前会 unwrap `tool_call` 到 underlying tool，并调用 `_tool_search_scoped_names(...)` 做 session scope gate，见 [tool_executor.py:198-244](../../../submodules/hermes-agent/agent/tool_executor.py#L198-L244) 与 [tool_executor.py:353-385](../../../submodules/hermes-agent/agent/tool_executor.py#L353-L385)。

源码注释还明确写到这是“OpenClaw lesson”：hooks 必须看到真实 underlying tool name，而不是只看到 `tool_call` bridge。

因此 Hermes 的 Tool Search 不是简单“查目录并调用”，而是：

```text
先按当前 session toolsets 生成可达目录
再搜索 / 描述 / 调用
执行前 unwrap 成真实工具名
然后让 middleware / hook / guardrail / display / trajectory 都看到真实工具
```

## conversation_loop：工具调用进入执行器之前的协议修复

主循环里的 tool_calls 分支在 [conversation_loop.py:4262](../../../submodules/hermes-agent/agent/conversation_loop.py#L4262) 附近。执行工具前，Hermes 会先做几类协议级修复和校验：

| 步骤 | 源码位置 | 含义 |
|---|---|---|
| tool name 修复 | [conversation_loop.py:4271-4282](../../../submodules/hermes-agent/agent/conversation_loop.py#L4271-L4282) | 如果模型输出大小写、分隔符或后缀错误，先尝试 `_repair_tool_call(...)`。 |
| invalid tool retry | [conversation_loop.py:4283-4343](../../../submodules/hermes-agent/agent/conversation_loop.py#L4283-L4343) | 未知工具名会作为 tool error 回写给模型，让模型下一轮自我修正。 |
| JSON args 校验 | [conversation_loop.py:4347-4365](../../../submodules/hermes-agent/agent/conversation_loop.py#L4347-L4365) | 空参数转 `{}`；非字符串参数转 JSON；非法 JSON 触发 retry 或 recovery tool result。 |
| tool-call assistant message | [conversation_loop.py:4413-4416](../../../submodules/hermes-agent/agent/conversation_loop.py#L4413-L4416) | 确保 assistant 的 tool_calls 进入 transcript。 |
| 调用执行器 | [conversation_loop.py:4531](../../../submodules/hermes-agent/agent/conversation_loop.py#L4531) | 调用 `agent._execute_tool_calls(...)`。 |

这说明 Hermes 很重视多 provider / 弱模型兼容：很多错误不是直接崩掉，而是通过“工具错误结果”交回模型，让模型有机会纠正。

## 工具调用外壳：先修协议，再查权限，再执行，再归档

Hermes 工具调用最容易被误解成“就是执行函数”。更准确地说，它像一个厚执行外壳：真正的 handler 执行只在中间一小段，前后包了很多检查、修复、拦截、预算和持久化。

可以分成三层：

### 第一层：conversation_loop 的协议卫生层

这一层发生在进入 executor 之前，主要处理模型 / provider 输出是否能形成合法工具调用：

```text
tool name 修复
unknown tool error 回写
arguments 空字符串转 {}
arguments 非字符串转 JSON
非法 JSON retry / recovery result
截断 arguments 检测
assistant tool-call message 入 transcript
```

它回答的问题不是“有没有权限”，而是：

> **这张工具任务条写得对不对？能不能交给执行器？**

比喻：私人助理收到任务条，先看字有没有写错、工具名是不是胡编、参数是不是半截。

### 第二层：tool_executor 的执行前门

进入 [tool_executor.py](../../../submodules/hermes-agent/agent/tool_executor.py) 后，真正执行 handler 前还会过多道门：

```text
Tool Search unwrap
  如果模型调用 tool_call，先展开到底层真实工具名

tool_call scope gate
  底层工具必须属于当前 session 的 scoped deferrable tools

tool request middleware
  允许中间件观察 / 调整请求参数

plugin pre_tool_call
  plugin 可以返回 block message 阻止执行

guardrail before_call
  检查是否重复失败或无进展循环

checkpoint preflight
  write_file / patch / 破坏性 terminal 前保存现场

interrupt check
  用户已中断则不启动后续工具

sequential / concurrent dispatch
  根据白名单、路径冲突和 MCP opt-in 判断是否并发
```

它回答的是：

> **这次工具调用在当前上下文里能不能安全执行？执行前要不要先做保护？**

### 第三层：执行后处理层

handler 返回后，Hermes 仍然不会直接把原始结果塞回模型，而是继续处理：

```text
post_tool_call hook
transform_tool_result
append_guardrail_observation
maybe_persist_tool_result
enforce_turn_budget
multimodal result adaptation
SessionDB flush
pending steer injection
```

它回答的是：

> **结果怎么给模型看、怎么归档、怎么防上下文爆炸、怎么让用户中途 steer 进入下一轮？**

因此 Hermes 工具执行更像：

```text
模型任务条
  -> 协议修复
  -> scope / hook / guardrail / checkpoint
  -> 真正 handler dispatch
  -> result transform / budget / persist / steer
  -> tool result message
```

这也是 Hermes 相比 OpenClaw 的一个重要观察点：OpenClaw 更强调 `AgentTool` 承载的一次调用工单流程；Hermes 更强调一个 provider tool-call 进入厚执行外壳后被修复、拦截、分派、归档。

### OpenClaw vs Hermes：不是“工具对象用完重建”，而是调用承载物不同

本轮讨论中，用户一直卡在“OpenClaw 的 `AgentTool` 生命周期”和“Hermes 的 `function_name + args` 厚执行外壳”到底差在哪里。关键澄清是：

> **OpenClaw 不是每次调用都新生成一个工具对象、用完再销毁；Hermes 也不是没有工具定义对象。差异在于执行阶段这次调用主要被什么东西承载。**

可以分三层看：

```text
第一层：工具定义 / Tool Definition
  长期存在，像菜谱 / 工位 / 函数定义。
  OpenClaw 里是 AgentTool；Hermes 里是 registry entry / schema / handler。

第二层：候选工具列表 / tools exposed to model
  每轮请求前告诉模型这轮能看见哪些工具。
  这可能随 session、toolsets、policy、plugin、MCP、provider 能力变化。

第三层：工具调用实例 / toolCall
  模型这一轮真的点了某个工具。
  这张“点菜单 / 工单”有 tool_call_id、name 和 arguments。
```

OpenClaw 的执行阶段更像：

```text
模型输出 toolCall(name="write_file", args={...})
  -> currentContext.tools.find(t => t.name === "write_file")
  -> 找到已有 AgentTool(write_file)
  -> 围绕这个 AgentTool 做 prepareArguments / validate / beforeToolCall / execute / afterToolCall
  -> 发 tool_execution_start / end 与 ToolResultMessage
```

因此 OpenClaw 的“生命周期”更准确说是**一次 toolCall 绑定到已有 AgentTool 后的标准工单流程**，不是 `AgentTool` 对象被一次性消耗。

Hermes 的执行阶段更像：

```text
模型输出 tool_call.function.name = "write_file"
       tool_call.function.arguments = JSON string
  -> executor 拆出 function_name / function_args
  -> Tool Search unwrap / scope gate / middleware / plugin block / guardrail / checkpoint
  -> agent._invoke_tool(function_name, function_args)
  -> registry / agent runtime handler dispatch
  -> result budget / persistence / SessionDB flush / steer injection
```

因此 Hermes 的重点不是“这次调用先绑定到一个 `AgentTool` 对象”，而是**`function_name + function_args` 这个请求包穿过厚执行器管线**。真正 handler dispatch 发生在中段；前后还有协议卫生、治理、归档和长期会话协作逻辑。

用户后来形成的较准确理解可以写成：

```text
OpenClaw：
  先把模型的工具调用归属到某个已有 AgentTool 工具定义对象，
  然后围绕这个 AgentTool 跑一套标准工单流程。

Hermes：
  先把模型的工具调用拆包成 function_name + args，
  然后让这个调用请求穿过厚执行器管线，
  最后再按名字 dispatch 到具体 handler。
```

这个版本修正了两个容易误解的说法：

- OpenClaw 不是“生成一个一次性工具执行对象，执行完就重新生成候选对象”；候选工具列表是每轮暴露给模型的菜单，工具定义对象通常长期存在。
- Hermes 不是“对象未生成之前才检查”；Hermes 同样有 registry / schema / handler，只是执行阶段没有强烈地以 `AgentTool` 对象生命周期为中心，而是以 `function_name + args + agent execution context` 为中心。

一句话记忆：

> **OpenClaw：toolCall 找到 `AgentTool`，进入工具对象承载的标准工单流程。Hermes：toolCall 拆成 `function_name + args`，进入厚执行器流水线。**

## sequential / concurrent：白名单式并发，不是默认并发

Hermes 的执行入口在 [run_agent.py:5581](../../../submodules/hermes-agent/run_agent.py#L5581)。它不是像 Claw-Code 那样固定串行，也不是像 OpenClaw 那样默认并行再遇到 sequential 工具整批降级，而是调用 `_should_parallelize_tool_batch(...)` 做白名单式安全判定：

```text
if not _should_parallelize_tool_batch(tool_calls):
  execute_tool_calls_sequential(...)
else:
  execute_tool_calls_concurrent(...)
```

### 并发判定规则

`_should_parallelize_tool_batch(...)` 位于 [tool_dispatch_helpers.py:104](../../../submodules/hermes-agent/agent/tool_dispatch_helpers.py#L104)。规则可以概括为：

| 条件 | 结果 |
|---|---|
| tool_calls 数量 <= 1 | 不并发。 |
| 任一工具在 `_NEVER_PARALLEL_TOOLS`，目前包括 `clarify` | 不并发。 |
| 任一工具 arguments 不是可解析 JSON object | 不并发。 |
| `read_file` / `write_file` / `patch` 这类 path-scoped 工具无法提取 path | 不并发。 |
| path-scoped 工具目标路径重叠 | 不并发。 |
| 工具不在 `_PARALLEL_SAFE_TOOLS`，且不是 MCP server 标记 parallel safe 的工具 | 不并发。 |
| 全部通过 | 并发。 |

并发安全白名单定义在 [tool_dispatch_helpers.py:45](../../../submodules/hermes-agent/agent/tool_dispatch_helpers.py#L45)，包括 `read_file`、`search_files`、`web_search`、`web_extract`、`session_search`、`skill_view`、`skills_list`、若干浏览器只读工具等。

path-scoped 工具定义在 [tool_dispatch_helpers.py:60](../../../submodules/hermes-agent/agent/tool_dispatch_helpers.py#L60)，目前包括 `read_file`、`write_file`、`patch`。它们可以并发，但必须目标路径不重叠，判定在 [_paths_overlap(...)](../../../submodules/hermes-agent/agent/tool_dispatch_helpers.py#L166) 中。

MCP 工具是否允许并发由 server 的 `supports_parallel_tool_calls` 影响，判定入口是 [tool_dispatch_helpers.py:90](../../../submodules/hermes-agent/agent/tool_dispatch_helpers.py#L90)，MCP 配置说明也写在 [mcp_tool.py:30](../../../submodules/hermes-agent/tools/mcp_tool.py#L30) 与 [mcp_tool.py:63-64](../../../submodules/hermes-agent/tools/mcp_tool.py#L63-L64)。

### 和 OpenClaw 的差异

| 项目 | 并发策略 |
|---|---|
| Claw-Code | 已读主线中是 `run_turn` for-loop 逐个执行，没有 batch-level parallel。 |
| OpenClaw | 默认 batch 并发；只要全局 sequential 或任一工具 `executionMode === "sequential"`，整批降级串行。 |
| Hermes | 默认保守；只有多工具批次全部满足白名单、安全 path、不重叠、MCP opt-in 等条件时才并发。 |

可以用“厨房窗口”比喻：

```text
Claw-Code：一个老师傅按顺序处理每张工单。
OpenClaw：默认多窗口并行；只要一张工单要求单窗口，就整批排队。
Hermes：先检查这批工单是不是都属于安全快办件；只有确认互不影响，才开多窗口。
```

Hermes 的并发策略更像“安全白名单 + 路径冲突检测”，而不是“工具对象自声明 executionMode”。

## concurrent 执行：线程池、顺序回写和中断传播

`execute_tool_calls_concurrent(...)` 位于 [tool_executor.py:306](../../../submodules/hermes-agent/agent/tool_executor.py#L306)。它的 docstring 说明：工具在 thread pool 中并发执行，但结果按原始 tool-call 顺序追加到 `messages`。

核心流程：

```text
预解析每个 tool_call 的 name / args
  -> Tool Search unwrap 到真实工具名
  -> tool request middleware
  -> plugin pre_tool_call block
  -> tool guardrail before_call
  -> checkpoint preflight
  -> ThreadPoolExecutor(max_workers <= 8)
    -> 每个 worker 注册线程 id，便于 interrupt fan-out
    -> agent._invoke_tool(...)
  -> 等待 futures，5s poll + activity heartbeat
  -> timeout / interrupt 时 cancel 未开始任务，并对 worker 设置 interrupt bit
  -> 收集结果，按原始顺序写回 tool messages
  -> result budget / session flush / steer injection
```

关键点：

| 机制 | 源码 | 作用 |
|---|---|---|
| 最大 worker 数 | [tool_executor.py:68-73](../../../submodules/hermes-agent/agent/tool_executor.py#L68-L73) | `_MAX_TOOL_WORKERS = 8`，默认 concurrent timeout 420s。 |
| worker 注册 | [tool_executor.py:537-545](../../../submodules/hermes-agent/agent/tool_executor.py#L537-L545) | 把 worker thread id 记录到 agent，用于 interrupt fan-out。 |
| 调用工具 | [tool_executor.py:568-578](../../../submodules/hermes-agent/agent/tool_executor.py#L568-L578) | worker 调 `agent._invoke_tool(...)`。 |
| heartbeat / interrupt / timeout | [tool_executor.py:681-756](../../../submodules/hermes-agent/agent/tool_executor.py#L681-L756) | 每 5s poll，长时间批次发 activity heartbeat；超时或用户 interrupt 时 cancel。 |
| 顺序回写 | [tool_executor.py:787-942](../../../submodules/hermes-agent/agent/tool_executor.py#L787-L942) | 即使执行完成顺序不同，也按原始 tool call 顺序 append tool result。 |
| turn budget | [tool_executor.py:944-948](../../../submodules/hermes-agent/agent/tool_executor.py#L944-L948) | 对本 turn 的工具结果总量做预算控制。 |
| steer 注入 | [tool_executor.py:950-955](../../../submodules/hermes-agent/agent/tool_executor.py#L950-L955) | 把 pending steer 追加到最后的 tool result。 |

这点和 OpenClaw 有相通之处：UI / activity 可以看到真实执行状态，但模型上下文要保持 tool result 顺序稳定。

## sequential 执行：一张工单一张工单办

`execute_tool_calls_sequential(...)` 位于 [tool_executor.py:959](../../../submodules/hermes-agent/agent/tool_executor.py#L959)。它保留了原始行为：逐个工具执行、逐个结果回写。

它在每个工具前先检查 interrupt，见 [tool_executor.py:963-983](../../../submodules/hermes-agent/agent/tool_executor.py#L963-L983)。如果用户已经发出 interrupt，会为剩余工具追加取消结果，不再启动新的工具。

sequential 路径同样会做：

```text
Tool Search unwrap
request middleware
plugin pre_tool_call block
guardrail before_call
checkpoint preflight
agent runtime tool inline handling
registry dispatch
post_tool_call / transform result
append_guardrail_observation
maybe_persist_tool_result
enforce_turn_budget
apply_pending_steer_to_tool_results
```

与 concurrent 不同的是，sequential 对很多 agent-runtime tools 保留了 inline 分支，例如 `todo`、`session_search`、`memory`、`clarify`、`read_terminal`、`delegate_task` 等，见 [tool_executor.py:1161](../../../submodules/hermes-agent/agent/tool_executor.py#L1161) 起的一系列分支。这些工具直接依赖 agent 实例状态或回调，不只是 registry 里的普通 handler。

## middleware / hooks：不是统一 pipeline，但执行前后有多个切面

Hermes 没有 OpenClaw 那种显式的 tool policy pipeline 表，但有多处 middleware / hook 切入点：

| 切面 | 源码 | 作用 |
|---|---|---|
| tool request middleware | [tool_executor.py:247-271](../../../submodules/hermes-agent/agent/tool_executor.py#L247-L271)、[model_tools.py:1025-1043](../../../submodules/hermes-agent/model_tools.py#L1025-L1043) | 修改 / 记录工具请求参数。 |
| tool execution middleware | [tool_executor.py:274-303](../../../submodules/hermes-agent/agent/tool_executor.py#L274-L303)、[model_tools.py:1157-1169](../../../submodules/hermes-agent/model_tools.py#L1157-L1169) | 包裹真实 handler 执行。 |
| plugin pre_tool_call block | [tool_executor.py:417-445](../../../submodules/hermes-agent/agent/tool_executor.py#L417-L445)、[model_tools.py:1049-1092](../../../submodules/hermes-agent/model_tools.py#L1049-L1092) | plugin 可以阻止工具执行并返回 error result。 |
| ACP edit approval | [model_tools.py:1094-1106](../../../submodules/hermes-agent/model_tools.py#L1094-L1106) | 对 `write_file` / `patch` 等编辑操作做审批。 |
| checkpoint preflight | [tool_executor.py:464-486](../../../submodules/hermes-agent/agent/tool_executor.py#L464-L486)、[tool_executor.py:1102-1124](../../../submodules/hermes-agent/agent/tool_executor.py#L1102-L1124) | 文件修改或破坏性 terminal 前先做 snapshot。 |
| post_tool_call hook | [model_tools.py:1178-1189](../../../submodules/hermes-agent/model_tools.py#L1178-L1189) | 工具完成后发观察事件。 |
| transform_tool_result | [model_tools.py:1191-1223](../../../submodules/hermes-agent/model_tools.py#L1191-L1223) | plugin 可替换最终写回模型的工具结果。 |

因此 Hermes 的工具治理更像“多个拦截点围着执行器”，而不是 DeerFlow 的 LangGraph middleware chain 或 OpenClaw 的 policy pipeline。

### 不要把所有治理都叫权限

本轮讨论中一个重要修正是：Hermes 的 toolsets、scope gate、plugin hook、checkpoint、guardrail、result budget 都属于工具治理，但它们不是同一种“权限”。如果混成一类，会误导后续比较。

更准确的拆分是：

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

一句话记忆：

> **toolsets 管“看得见”；scope gate 管“别越权绕路”；plugin / approval 管“能不能执行”；checkpoint 管“能不能回滚”；guardrail 管“别原地打转”；result budget 管“别撑爆上下文”。**

这也修正了一个比较误区：Claw-Code / OpenClaw / Hermes 并不是分别“只有权限 / 只有 policy / 只有 guardrail”。成熟工具系统都会有可见性门、执行前门、参数风险、审批、执行后 hook 和错误/循环处理；差异在于这些门放在本地 runtime、产品 policy pipeline，还是 Hermes 这种 toolsets + plugin hook + executor 外壳中。

## guardrail：工具循环防抖和熔断

Hermes 的工具循环 guardrail 在 [tool_guardrails.py](../../../submodules/hermes-agent/agent/tool_guardrails.py)。`ToolCallGuardrailConfig` 位于 [tool_guardrails.py:64](../../../submodules/hermes-agent/agent/tool_guardrails.py#L64)，默认：

```text
warnings_enabled = True
hard_stop_enabled = False
exact_failure_warn_after = 2
exact_failure_block_after = 5
same_tool_failure_warn_after = 3
same_tool_failure_halt_after = 8
no_progress_warn_after = 2
no_progress_block_after = 5
```

也就是说，默认先给模型 warning，不直接 hard stop；hard stop 需要显式配置。

`ToolCallGuardrailController.before_call(...)` 位于 [tool_guardrails.py:241](../../../submodules/hermes-agent/agent/tool_guardrails.py#L241)。当 hard stop 开启时，它可以在执行前阻止重复失败的相同工具调用，或者阻止只读工具重复拿到相同结果却继续原样调用。

`after_call(...)` 位于 [tool_guardrails.py:285](../../../submodules/hermes-agent/agent/tool_guardrails.py#L285)，会根据工具结果更新计数：

| 情况 | 行为 |
|---|---|
| 相同工具 + 相同参数重复失败 | 累计 exact failure；达到阈值后 warning 或 block。 |
| 同一个工具多次失败 | 累计 same tool failure；达到阈值后 warning 或 halt。 |
| 只读工具重复返回相同结果 | 累计 no-progress；达到阈值后 warning 或 block。 |
| 成功或换策略 | 清理对应失败计数。 |

warning / halt 会通过 [append_toolguard_guidance(...)](../../../submodules/hermes-agent/agent/tool_guardrails.py#L394) 追加到工具结果里，让模型下一轮看到“你在循环，换策略”。block 则通过 [toolguard_synthetic_result(...)](../../../submodules/hermes-agent/agent/tool_guardrails.py#L383) 生成 synthetic tool result。

这套机制很适合 Hermes 的长期个人 Agent 场景：用户可能让它持续跑任务，模型也可能在多 provider / 弱模型场景下重复失败；guardrail 不是权限系统，而是“防止自己撞墙”的运行安全带。

## 个人 Agent 能力如何工具化

Hermes 的特色之一是：长期个人助理能力不是游离在工具系统之外，而是通过工具进入同一条执行链。

| 能力 | 工具 / 入口 | 说明 |
|---|---|---|
| 任务计划 | `todo` | per-agent `TodoStore`，由 executor inline 调用。 |
| 长期记忆 | `memory` | 内置 memory store；成功写入还可 mirror 到 external memory provider。 |
| 外部 memory provider | `agent._memory_manager.has_tool(...)` | memory provider 可以提供自己的工具，由 `invoke_tool(...)` 或 executor 分支处理。 |
| 会话检索 | `session_search` | 从 SessionDB 检索历史对话，服务跨会话 recall。 |
| 技能沉淀 | `skills_list` / `skill_view` / `skill_manage` | 作为核心工具出现在 `_HERMES_CORE_TOOLS` 和 skills toolset 中。 |
| 澄清 | `clarify` | 通过 callback 向平台 / 用户提问，且属于 never-parallel 工具。 |
| 子 Agent | `delegate_task` | 派发子任务，和 iteration budget / parent agent 状态交织。 |

这也是 Hermes 和 Claw-Code / OpenClaw 很不一样的地方：Claw-Code 的工具系统重点服务本地 coding runtime；OpenClaw 的工具系统重点服务多端产品调度；Hermes 的工具系统重点服务“长期陪伴型 Agent 的个人工作台”。

## 工具结果回写：不只是 append string

Hermes 工具 handler 大多返回 JSON 字符串，但执行器在写回前还会做多层处理：

| 处理 | 源码 | 作用 |
|---|---|---|
| multimodal 结果适配 | [tool_executor.py:923-932](../../../submodules/hermes-agent/agent/tool_executor.py#L923-L932)、[tool_executor.py:1578-1581](../../../submodules/hermes-agent/agent/tool_executor.py#L1578-L1581) | 对 vision / image 等工具返回 OpenAI-style content list 或文本 fallback。 |
| 大结果持久化 | [tool_executor.py:906-912](../../../submodules/hermes-agent/agent/tool_executor.py#L906-L912)、[tool_executor.py:1562-1568](../../../submodules/hermes-agent/agent/tool_executor.py#L1562-L1568) | `maybe_persist_tool_result(...)` 把大工具结果落盘并给模型短引用。 |
| turn budget | [tool_executor.py:944-948](../../../submodules/hermes-agent/agent/tool_executor.py#L944-L948)、[tool_executor.py:1623-1627](../../../submodules/hermes-agent/agent/tool_executor.py#L1623-L1627) | `enforce_turn_budget(...)` 限制本 turn 工具结果总量。 |
| session flush | [tool_executor.py:933-937](../../../submodules/hermes-agent/agent/tool_executor.py#L933-L937)、[tool_executor.py:1581-1586](../../../submodules/hermes-agent/agent/tool_executor.py#L1581-L1586) | 工具结果追加后立即 flush 到 SessionDB，增强 crash recovery。 |
| steer 注入 | [tool_executor.py:939-955](../../../submodules/hermes-agent/agent/tool_executor.py#L939-L955)、[tool_executor.py:1588-1592](../../../submodules/hermes-agent/agent/tool_executor.py#L1588-L1592) | 用户中途 `/steer` 会尽早附加到 tool result。 |

这使得 Hermes 的 tool result 是下一轮模型输入、会话持久化、跨通道交互和用户实时引导的交汇点。

## 和 Claw-Code / OpenClaw 的核心差异

### 总比喻

| 项目 | 总比喻 | Tool System 的核心气质 |
|---|---|---|
| Claw-Code | 本地老师傅 / 单人工具箱 | 工具集中、主线直接、一个个干。 |
| OpenClaw | 多端工作室 / 餐厅后厨工单系统 | 工单化、事件化、默认追求并行效率。 |
| Hermes Agent | 长期私人助理的工作台 | 工具 + 记忆 + 技能 + 历史 + 用户插话融合在一起。 |

### 工具组装：动态依据不同

OpenClaw 和 Hermes 都是动态组装工具，但动态依据不同：

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
OpenClaw：
  多端工作室经理按当前工单场景配工具车。
  这次是 Web 端？IM channel？sandbox？subagent？不同场景配不同车。

Hermes：
  私人助理按任务菜单从工具总账里拿工具摆上桌。
  今天是 research 菜单、file 菜单、memory 菜单，还是 plugin / MCP 扩展菜单？
```

这比简单说“OpenClaw 动态、Hermes 预定义”更准确：Hermes 菜单可以扩展，但所有“加菜”都要进入 registry / toolset / valid_tool_names / scope gate。

### 串行 / 并发：三种架构性格

| 项目 | 策略 | 比喻 | 体现的架构性格 |
|---|---|---|---|
| Claw-Code | 已读主线中固定串行 | 老师傅一个人按顺序干活 | 本地 CLI，清楚、直接、可控。 |
| OpenClaw | 默认并发；任一 sequential 工具让整批降级 | 后厨默认多窗口，有特殊菜就整批排队 | 多端产品 runtime，追求效率和事件调度。 |
| Hermes | 白名单式并发；确认安全才并发 | 私人助理只把安全快办件并行分派 | 长期个人 Agent，保守处理状态、副作用和用户交互。 |

最浓缩：

```text
Claw-Code：顺序是默认秩序。
OpenClaw：并发是默认效率，sequential 是刹车。
Hermes：安全是默认前提，并发是通过审查后的加速。
```

### 权限 / 治理：不要强行说成完全不同

三者底层都绕不开同一组门：

```text
工具是否可见？
当前 session 是否允许？
参数是否危险？
是否需要用户审批？
执行前后是否要 hook？
失败 / 循环是否要拦？
```

差异不是“谁有权限，谁没有权限”，而是这些门被放在哪一层：

| 项目 | 更中心的位置 | 更准确说法 |
|---|---|---|
| Claw-Code | 本地 runtime + tools enforcer | 集中式权限门比较清楚，尤其是工具类型与具体参数两道门。 |
| OpenClaw | 产品 policy pipeline + before_tool_call runtime | 多上下文产品策略更突出。 |
| Hermes | toolsets / plugin hooks / ACP approval / scope gate / checkpoint / guardrail 分散在执行链 | 治理更分散；guardrail 主要防循环，不应等同权限。 |

### 工具调用本体：待继续讲清

当前阶段可以暂时写成：

```text
OpenClaw：
  更像 AgentTool 对象的标准工单生命周期。
  工具对象自带 execute / executionMode / prepareArguments，执行过程伴随 tool_execution_* 与 message_* 事件。

Hermes：
  更像 function_name + function_args 进入厚执行器外壳。
  执行器负责协议修复、Tool Search unwrap、middleware、plugin block、guardrail、checkpoint、registry dispatch、result budget、SessionDB flush 和 steer 注入。
```

但这个解释仍然没有完全讲清。后续待办：选一个具体工具调用，如 `read_file` 或 `write_file`，逐行对比 OpenClaw 与 Hermes 的数据流：模型输出后是什么结构、在哪里 resolve 工具、在哪里执行、哪里生成 result、哪些 hook/事件/持久化发生。避免继续只靠抽象比喻。

### 对比表

| 维度 | Claw-Code | OpenClaw | Hermes Agent |
|---|---|---|---|
| 比喻 | 本地万能工具箱 / 老师傅 | 多端工作室 / 后厨工单调度系统 | 长期私人助理的工具工作台 |
| 工具注册 | `ToolSpec` + `GlobalToolRegistry` 中心化 | 多个 TS factory 动态组装 `AgentTool` | tools 模块自注册到 `ToolRegistry`，toolsets 组合工具面 |
| 工具可见性 | allowed tools + deferred ToolSearch | policy pipeline + OpenClaw/MCP/client Tool Search | enabled/disabled toolsets + check_fn + Tool Search progressive disclosure |
| Tool Search | 轻量关键词目录 | search / describe / call / code-mode 大目录服务 | MCP/plugin 非核心工具延迟暴露，BM25 search + describe + call，核心工具永不 deferred |
| 并发策略 | 已读主线固定串行 | 默认并行，遇 sequential 整批降级 | 白名单式并发：safe tools、path 不重叠、MCP opt-in 才并发 |
| 权限 / 治理 | PermissionPolicy + PermissionEnforcer 两道门 | tool policy pipeline + before_tool_call approval / diagnostics / loop detection | toolsets 可见性、scope gate、plugin hook、ACP approval、checkpoint、guardrail、result budget 分工治理 |
| 工具结果 | 字符串 output 转 tool result | `AgentToolResult` 结构化服务 UI / runtime / model | JSON/string + multimodal envelope + 大结果持久化 + turn budget + steer 注入 |
| 长期个人能力 | 不是核心定位 | 多端 session 产品能力强 | memory / todo / session_search / skills / delegate_task 是核心工具面 |

一句话：

> **Hermes 的 Tool System 不是最集中，也不是最事件化，而是最“个人 Agent 化”：工具菜单、记忆、技能、历史检索、子 agent、用户 steer、会话持久化和多 provider 兼容被缝在同一条工具执行链上。**

## 阶段性判断

Hermes Tool System 的精髓可以记成四点：

1. **toolsets 是工具菜单**：不同平台、profile、subagent、kanban worker 可以拿到不同工具面。
2. **registry 是工具总账**：工具模块自注册 schema / handler / check_fn，`get_tool_definitions(...)` 动态算出有效工具表。
3. **Tool Search 是工具仓库目录**：核心工具永远在桌面上，MCP / plugin 非核心工具在工具仓库里，超过阈值后通过 search / describe / call 渐进式使用。
4. **tool_executor 是个人 Agent 的执行工作台**：它不仅执行工具，还处理 plugin hook、middleware、checkpoint、guardrail、interrupt、steer、result budget 和 session persistence。

## QA / 讨论记录

### Q: Hermes 的工具系统为什么更像“个人 Agent 工具工作台”？

> **状态**: draft  
> **来源**: source-code / discussion

A: 因为 Hermes 的工具系统不仅服务外部动作，还承载长期个人 Agent 的核心能力。`memory`、`todo`、`session_search`、`skill_manage`、`delegate_task`、`clarify` 等都在 `_HERMES_CORE_TOOLS` 或 toolsets 中，通过同一套 registry、tool execution、middleware、guardrail、result 回写进入模型循环。工具结果还会触发 session flush 和 pending steer 注入，因此工具系统同时是执行层、记忆/技能入口和多轮协作交汇点。

### Q: Hermes 的并发执行和 OpenClaw 的 sequential / parallel 最大区别是什么？

> **状态**: draft  
> **来源**: source-code

A: OpenClaw 更像“默认并行，遇到任一 sequential 工具整批降级”；Hermes 更像“默认保守，只有白名单安全批次才并发”。Hermes 的 `_should_parallelize_tool_batch(...)` 要求工具数量大于 1、没有 `clarify` 等 never-parallel 工具、参数 JSON 可解析、path-scoped 工具路径不重叠、工具在 parallel-safe 白名单中或 MCP server 显式支持并行。这样避免共享状态、副作用和交互式工具交错。

### Q: Hermes 的 Tool Search 和 Claw-Code / OpenClaw 有什么不同？

> **状态**: draft  
> **来源**: source-code / discussion

A: Claw-Code 的 ToolSearch 是轻量内置目录检索器；OpenClaw 的 Tool Search 是面向 OpenClaw / MCP / client 多来源的大工具目录服务，还支持 code-mode；Hermes 的 Tool Search 是 progressive disclosure：核心 Hermes 工具永不 deferred，MCP / plugin 非核心工具在工具表过大时被 `tool_search` / `tool_describe` / `tool_call` 三个 bridge 替代。它特别强调 session toolset scope，避免受限 session 通过 `tool_call` 调到未授权的全局工具。

### Q: Hermes 的 tool guardrail 是权限系统吗？

> **状态**: draft  
> **来源**: source-code

A: 不是。`ToolCallGuardrailController` 主要防止工具循环和无进展重复调用：相同参数重复失败、同一工具多次失败、只读工具重复返回相同结果等。默认启用 warning，不默认 hard stop；hard stop 需要配置打开。权限 / 审批更多由 plugin hook、ACP edit approval、checkpoint 和具体工具安全策略承担。

### Q: Hermes 为什么要把 steer 注入到 tool result，而不是插入新的 user message？

> **状态**: draft  
> **来源**: source-code / discussion

A: tool-calling 协议通常要求 assistant tool_calls 后面紧跟对应 tool result，随意插入新的 user message 可能破坏 tool_call_id 对齐和 role alternation。Hermes 的 `steer(...)` 是软引导，不打断当前工具，而是在工具结果产生后通过 `apply_pending_steer_to_tool_results(...)` 附加到 tool result，让下一轮模型在合法消息序列中看到用户补充方向。这个设计把交互控制和工具结果回写耦合在一起。
