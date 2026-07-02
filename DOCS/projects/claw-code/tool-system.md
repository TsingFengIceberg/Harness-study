# Claw-Code Tool System：集中式工具中枢与延迟工具发现

> **日期**: 2026-07-02 | **状态**: draft | **涉及版本**: `4ea31c1bc91c4e9bcbd67d51c550c01e127e6d0d`

## 相关文档

- 项目入口：[README.md](README.md)
- Agent Loop：[agent-loop.md](agent-loop.md)
- 横向对比：[Tool System 横向总结](../../comparison/tool-system.md)
- 横向 QA：[qa.md](../../comparison/qa.md#tool-system--工具体系)

## 源码入口

| 模块 | 源码 | 作用 |
|---|---|---|
| 工具定义与注册 | [lib.rs](../../../claw-code/rust/crates/tools/src/lib.rs) | `ToolSpec`、`GlobalToolRegistry`、内置工具表、allowed tools 过滤、ToolSearch、执行分发。 |
| Agent Loop 调用工具 | [conversation.rs](../../../claw-code/rust/crates/runtime/src/conversation.rs) | `ConversationRuntime::run_turn` 串起 `ToolUse` 提取、hooks、permission、execute、`ToolResult` 回写。 |
| 权限策略 | [permissions.rs](../../../claw-code/rust/crates/runtime/src/permissions.rs) | `PermissionMode`、`PermissionPolicy`、`PermissionPrompter`、allow / deny / ask 规则。 |
| 执行层权限门 | [permission_enforcer.rs](../../../claw-code/rust/crates/runtime/src/permission_enforcer.rs) | `PermissionEnforcer` 做非交互式二次权限检查。 |
| 会话消息结构 | [session.rs](../../../claw-code/rust/crates/runtime/src/session.rs) | `ContentBlock::ToolUse` / `ToolResult` 的内部表示。 |
| Hook 系统 | [hooks.rs](../../../claw-code/rust/crates/runtime/src/hooks.rs) | `PreToolUse`、`PostToolUse`、`PostToolUseFailure` 外部命令 hook。 |
| MCP 工具桥 | [mcp_tool_bridge.rs](../../../claw-code/rust/crates/runtime/src/mcp_tool_bridge.rs) | MCP server tool 调用桥接。 |

## 一句话总结

Claw-Code 的 Tool System 是一个 **集中式、本地 CLI 风格的能力中枢**：它把工具定义、工具暴露、工具过滤、权限检查、hook 横切、执行分发、结果回写和延迟工具发现，都串在本地 `ConversationRuntime::run_turn` 这一条 Agent Loop 主线上。

最关键的判断是：

> **Claw-Code 的工具系统不是单纯“给模型几个函数调用”，而是本地 Agent 触达外部世界的统一能力总线。**

它既包括基础 coding 工具：

```text
bash
read_file
write_file
edit_file
glob_search
grep_search
```

也逐渐承载更高层 runtime 能力：

```text
WebFetch / WebSearch
TodoWrite
Skill
Agent
ToolSearch
NotebookEdit
TaskCreate / TaskOutput / TaskStop
WorkerCreate / TeamCreate
CronCreate
LSP
MCP
GitStatus / GitDiff / GitLog / GitShow / GitBlame
```

因此它的风格可以概括为：

```text
直接、内联、可控；
适合本地 CLI；
但工具越来越多后，会变成一个工具大中枢。
```

## 工具系统主流程

Claw-Code 工具调用主链路可以压缩成：

```text
ToolSpec 定义工具
  -> GlobalToolRegistry 汇总 builtin / plugin / runtime tools
    -> ProviderRuntimeClient 把 ToolDefinition 暴露给模型
      -> 模型返回 ContentBlock::ToolUse
        -> ConversationRuntime::run_turn 逐个处理 ToolUse
          -> PreToolUse hook
            -> PermissionPolicy / PermissionPrompter 第一层授权
              -> ToolExecutor.execute
                -> execute_tool_with_enforcer 分发具体工具
                  -> PermissionEnforcer 第二层动态权限检查
                    -> run_xxx_tool
                      -> ContentBlock::ToolResult 写回 Session
                        -> convert_messages 转成 provider API tool_result
                          -> 下一轮模型看到 observation 后继续推理
```

对应源码主线：

- `ToolSpec` 定义在 [lib.rs](../../../claw-code/rust/crates/tools/src/lib.rs)
- `GlobalToolRegistry` 定义在 [lib.rs](../../../claw-code/rust/crates/tools/src/lib.rs)
- `run_turn` 工具处理主流程在 [conversation.rs](../../../claw-code/rust/crates/runtime/src/conversation.rs)
- 工具执行分发在 [execute_tool_with_enforcer](../../../claw-code/rust/crates/tools/src/lib.rs)
- 内部消息块定义在 [session.rs](../../../claw-code/rust/crates/runtime/src/session.rs)

## ToolSpec：工具的最小描述单元

`ToolSpec` 是 Claw-Code 内置工具的基础描述结构，位于 [lib.rs](../../../claw-code/rust/crates/tools/src/lib.rs)：

```text
name
  工具名，例如 bash / read_file / edit_file

description
  给模型看的工具说明

input_schema
  给模型看的 JSON schema，用来约束工具参数

required_permission
  该工具默认需要的权限模式
```

这说明 Claw-Code 里的工具不是只给 Rust 代码调用的函数，而是同时承担三层职责：

| 层级 | ToolSpec 提供什么 |
|---|---|
| 模型协议层 | name / description / input_schema，让模型知道能调用什么、怎么传参。 |
| Harness 执行层 | name 对应到 `execute_tool_with_enforcer` 里的具体分支。 |
| 安全策略层 | `required_permission` 给第一层权限检查提供默认风险等级。 |

## GlobalToolRegistry：builtin / plugin / runtime tools 的统一入口

`GlobalToolRegistry` 位于 [lib.rs](../../../claw-code/rust/crates/tools/src/lib.rs)，负责汇总三类工具：

```text
builtin tools
  Claw-Code 内置工具，来自 mvp_tool_specs()

plugin tools
  plugin 扩展进来的工具

runtime tools
  运行时动态注入的工具定义
```

它的核心职责包括：

| 方法 / 能力 | 说明 |
|---|---|
| `builtin()` | 创建只包含内置工具的 registry。 |
| `with_plugin_tools(...)` | 注入 plugin tools，并检查不能和内置工具重名。 |
| `with_runtime_tools(...)` | 注入 runtime tools，并检查不能和已有工具重名。 |
| `definitions(...)` | 转成 provider 能理解的 `ToolDefinition` 列表。 |
| `permission_specs(...)` | 提取工具默认权限，供权限策略使用。 |
| `normalize_allowed_tools(...)` | 规范化用户配置的 allowed tools。 |
| `search(...)` | ToolSearch 的底层工具目录检索入口。 |
| `execute(...)` | 根据工具名执行 builtin 或 plugin tool。 |

这也体现了 Claw-Code 的核心风格：

> **工具注册、工具暴露、工具权限、工具搜索和工具执行分发都集中在一个 registry / tools 模块附近。**

## allowedTools / alias：用户配置友好性，不是模型 query 解析

`normalize_allowed_tools(...)` 和 `allowed_tool_aliases(...)` 处理的是 **用户配置层**，不是模型理解用户自然语言 query 的过程。

例如 [allowed_tool_aliases](../../../claw-code/rust/crates/tools/src/lib.rs) 支持：

```text
read  -> read_file
write -> write_file
edit  -> edit_file
glob  -> glob_search
grep  -> grep_search
```

这表示用户在配置或 CLI 参数里写 allowed tools 时，不必总是写内部精确名。

例如用户可能配置：

```text
--allowedTools read write grep
```

系统会规范化成：

```text
read_file
write_file
grep_search
```

它不是说：

```text
用户在对话里说“读一下文件”
  -> normalize_allowed_tools 自动解析成 read_file
```

真正的自然语言理解仍由模型完成。模型看到 provider 暴露的工具定义后，自己决定是否产生：

```text
ToolUse { name: "read_file", input: ... }
```

所以这里要区分两件事：

| 问题 | 谁负责 |
|---|---|
| 用户配置里 `read` 这个别名怎么变成 `read_file`？ | `normalize_allowed_tools(...)`。 |
| 用户自然语言“帮我看一下 README”怎么变成工具调用？ | 模型根据工具 schema 和上下文决定。 |

## allowed tools 过滤：暴露给模型之前先裁剪工具表

`GlobalToolRegistry::definitions(...)` 会把工具转成 provider 使用的 `ToolDefinition`。在转换前，它会根据 `allowed_tools` 过滤。

过滤逻辑的核心是：

```text
allowed_tools 为空 / None：
  暴露所有可用工具

allowed_tools 有具体集合：
  只暴露 canonical name 在集合里的工具
```

这层过滤会同时作用于：

```text
builtin tools
runtime tools
plugin tools
```

也就是说，allowed tools 不是工具执行之后才拒绝，而是会影响 **模型看得到哪些工具**。

如果某个工具没有被暴露给模型，模型一般就不会正常地产生这个工具名的 tool use。这属于工具系统的第一层收口：

> **先从模型可见性上减少可调用工具面。**

## run_turn：工具执行链路的主干

Claw-Code 的工具调用不是工具模块自己独立完成的，而是在 [conversation.rs](../../../claw-code/rust/crates/runtime/src/conversation.rs) 的 `ConversationRuntime::run_turn` 里被 Agent Loop 串起来。

主流程是：

```text
1. 调用模型，得到 assistant_message
2. 从 assistant_message.blocks 中提取 ToolUse
3. 如果没有 ToolUse，本轮结束
4. 如果有 ToolUse，逐个处理
5. 每个 ToolUse 先跑 PreToolUse hook
6. 根据 hook 结果构造 PermissionContext
7. PermissionPolicy / PermissionPrompter 判断是否允许
8. 允许则调用 ToolExecutor.execute
9. 工具成功或失败后跑 PostToolUse / PostToolUseFailure hook
10. 构造 ConversationMessage::tool_result
11. tool_result 写回 Session
12. 下一轮 API 调用时把 tool_result 转回 provider 消息
```

这个结构说明：

> **Claw-Code 的工具系统不是外挂在 Agent Loop 外面，而是 Agent Loop 本身的核心组成部分。**

## Hook：工具调用前后的横切插槽

Hook 可以理解为：

> **在工具执行前后，让外部命令插入一段检查、改写、拒绝、补充上下文或审计逻辑。**

Claw-Code 的 hook 定义在 [hooks.rs](../../../claw-code/rust/crates/runtime/src/hooks.rs)，核心事件包括：

```text
PreToolUse
PostToolUse
PostToolUseFailure
```

其中 `PreToolUse` 发生在工具真正执行之前，因此它可以做很多横切操作：

| 能力 | 含义 |
|---|---|
| 看工具调用 | hook 能拿到 tool name 和 tool input。 |
| 改工具 input | 通过 `updated_input` 修改工具参数。 |
| 允许 / 拒绝 / 要求 ask | 通过 permission override 影响后续权限判断。 |
| 失败或取消 | hook 自身失败、取消或 deny，会让工具不执行。 |
| 附加 message | 给工具结果合并额外 feedback，让模型下一轮看到。 |
| 审计 / 记录 | 外部命令可以记录敏感操作、检查策略或通知其他系统。 |

这就是 Claw-Code 工具系统中的一层重要“横切能力”：

```text
模型想调工具
  -> 先经过 hook
    -> hook 可以看、改、拦、补充反馈
      -> 再进入权限策略和实际执行
```

它类似 middleware，但 Claw-Code 没有把它组织成 DeerFlow 那种统一 LangGraph middleware chain，而是把 pre/post hook 明确插在 `run_turn` 的工具处理流程中。

## 第一扇门：PermissionPolicy / PermissionPrompter

工具调用进入执行前，`run_turn` 会先调用权限策略。相关结构在 [permissions.rs](../../../claw-code/rust/crates/runtime/src/permissions.rs)：

| 组件 | 作用 |
|---|---|
| `PermissionMode` | 权限等级，例如 `ReadOnly`、`WorkspaceWrite`、`DangerFullAccess`、`Prompt`、`Allow`。 |
| `PermissionPolicy` | 当前整体权限策略，管理 active mode、工具默认需求、allow / deny / ask rules、denied tools。 |
| `PermissionContext` | 承载 PreToolUse hook 给出的 permission override 和 reason。 |
| `PermissionPrompter` | 需要用户确认时，负责交互式询问用户 Allow / Deny。 |

这层回答的问题是：

> **模型当前想用这个工具类型，按照当前模式和规则，能不能进入执行流程？**

例如：

```text
当前 active mode = ReadOnly
模型想用 write_file
write_file 默认 required_permission = WorkspaceWrite
=> 第一扇门可能拒绝或要求询问
```

或者：

```text
PreToolUse hook 明确 deny
=> 即使工具默认权限够，也不执行
```

所以权限不是工具执行器自己随便决定的，而是由：

```text
PreToolUse hook
PermissionPolicy
PermissionPrompter
```

共同决定第一层授权。

## 第二扇门：PermissionEnforcer 和动态权限

第一扇门基于工具名和默认权限，但这还不够。

因为同一个工具的不同参数可能风险完全不同：

```text
bash "git status"
bash "rm -rf /"

read_file "README.md"
read_file "/etc/passwd"

write_file "DOCS/note.md"
write_file "~/.ssh/config"
```

所以 Claw-Code 在工具执行分发层还有第二扇门。它位于 [execute_tool_with_enforcer](../../../claw-code/rust/crates/tools/src/lib.rs)。

典型流程是：

```text
1. 解析具体工具 input
2. 根据真实参数分类 required_mode
3. 调用 maybe_enforce_permission_check_with_mode(...)
4. 当前 active mode 足够才执行 run_xxx
```

例如：

| 工具 | 动态分类依据 |
|---|---|
| `bash` | command 是否只读、是否含危险 shell 行为。 |
| `PowerShell` | command 是否只读或高风险。 |
| `read_file` | path 是否在 workspace 内。 |
| `write_file` / `edit_file` | path 是否在 workspace 内、是否写入越界位置。 |
| `glob_search` / `grep_search` | 搜索范围是否在 workspace 内。 |
| `WebFetch` / `WebSearch` | 网络访问按更高风险处理。 |

这层回答的问题是：

> **这个具体调用参数会不会越界？**

## `maybe_enforce_permission_check_with_mode`：动态权限检查的小闸门

`maybe_enforce_permission_check_with_mode(...)` 位于 [lib.rs](../../../claw-code/rust/crates/tools/src/lib.rs)。它不是分类器，而是统一执行动态检查的小 helper。

它的输入是：

```text
enforcer
  可选 PermissionEnforcer

tool_name
  当前工具名

input
  当前工具输入

required_mode
  前面根据具体参数算出来的权限需求
```

它做的事情是：

```text
如果没有 enforcer：
  直接 Ok

如果有 enforcer：
  调用 enforcer.check_with_required_mode(tool_name, input, required_mode)
  Allowed -> Ok
  Denied  -> Err(reason)
```

所以它的定位是：

> **拿这次具体调用的风险等级，和当前权限模式比一比，不够就拦住。**

这不是重复检查，而是和第一扇门互补：

| 层级 | 问题 | 例子 |
|---|---|---|
| 第一扇门 | 这个工具类型当前能不能用？ | 当前模式允许 `write_file` 吗？ |
| 第二扇门 | 这个具体参数会不会越界？ | `write_file` 写的是 workspace 内文件，还是 `/etc/hosts`？ |

用工地比喻：

```text
第一扇门：你有没有资格进入工地、使用施工工具？
第二扇门：你进了工地以后，是不是只在指定区域施工？有没有跑去拆隔壁楼？
```

## ToolResult 为什么要转成 provider 的 tool result？

Claw-Code 内部消息结构定义在 [session.rs](../../../claw-code/rust/crates/runtime/src/session.rs)，里面有：

```text
ContentBlock::ToolUse
ContentBlock::ToolResult
```

这是 Claw-Code 自己的 session 表示。

但模型 API 不直接理解 Claw-Code 的 Rust enum。下一轮调用 provider 时，需要把内部消息转换成 provider 协议里的消息块。这个转换发生在 [lib.rs](../../../claw-code/rust/crates/tools/src/lib.rs) 的 `convert_messages(...)` 附近。

所以：

```text
内部 ToolResult
  -> provider API InputContentBlock::ToolResult
```

不是多此一举，而是必要的协议适配。

它解决三个问题：

| 问题 | 说明 |
|---|---|
| 会话内部表示 | Claw-Code 需要自己的 `Session` / `ContentBlock`，方便持久化、压缩、统计和跨 provider 处理。 |
| provider 协议要求 | 模型下一轮必须看到合法的 `tool_result`，才能把工具结果和之前的 `tool_use_id` 对齐。 |
| 解耦 provider | 内部不直接绑定某一个 API 的消息类型，调用前再转换。 |

如果不把 tool result 转回 provider 可理解的格式，模型下一轮就无法知道：

```text
刚才那个 tool_use 的执行结果是什么？
有没有 error？
下一步应该怎么继续？
```

## ToolSearch：延迟工具发现，而不是智能搜索 Agent

这是 Claw-Code 工具系统里非常精髓的一点。

> **ToolSearch 不是调用模型来智能搜索工具，而是一个内置的工具目录检索器。**

它解决的问题是：

> **工具很多，但不一定要一次性全部暴露给模型。**

如果把所有几十个工具都塞进模型上下文，会带来：

```text
1. 工具定义占用更多 prompt
2. 模型每轮选择工具的噪音变大
3. 当前任务用不上的专用工具会干扰决策
4. 工具越多，越需要可见性管理
```

因此 Claw-Code 区分两类工具：

```text
always-visible tools
  高频基础 coding 工具，默认给模型看

deferred tools
  专用工具，默认不全部展开，需要时通过 ToolSearch 查目录
```

[deferred_tool_specs](../../../claw-code/rust/crates/tools/src/lib.rs) 中可以看到，下面 6 个基础工具不属于 deferred：

```text
bash
read_file
write_file
edit_file
glob_search
grep_search
```

这些相当于 coding agent 桌面上的常用工具。

其他工具则可以通过 `ToolSearch` 按需发现，例如：

```text
query: "notebook"
  -> 可能返回 NotebookEdit

query: "task"
  -> 可能返回 TaskCreate / TaskOutput / TaskStop

query: "cron"
  -> 可能返回 CronCreate / CronDelete / CronList
```

## ToolSearch 怎么搜索？

搜索逻辑在 [search_tool_specs](../../../claw-code/rust/crates/tools/src/lib.rs)。它是代码里的关键词匹配和打分，不是模型推理。

核心特征：

| 机制 | 说明 |
|---|---|
| 工具名精确匹配 | 得分高，尤其 canonical token 完全匹配。 |
| 工具名包含 query | 得中等分。 |
| 描述 / haystack 包含 query | 得较低分。 |
| `+term` | 可表示 required term，缺少 required term 的工具会被过滤。 |
| `select:` | 直接按工具名选择，例如 `select:NotebookEdit,CronCreate`。 |
| canonical token | 会去掉非字母数字、转小写，并去掉末尾 `tool`，提升匹配稳定性。 |

可以把它比喻为工具箱旁边的一本目录：

```text
常用扳手、螺丝刀直接放桌上；
不常用的专用工具放柜子里；
需要的时候先查目录，再拿出来用。
```

这点非常关键，因为它说明：

> **工具系统的设计不只是“工具越多越好”，还要管理模型每一轮看到的工具表规模。**

## 中心化工具中枢：精髓与代价

Claw-Code 的工具系统有一个很鲜明的风格：

> **工具定义和执行分发都集中在一个大工具中枢里。**

集中体现在：

```text
mvp_tool_specs() 很大
execute_tool_with_enforcer() 很大
ToolSearch / allowedTools / permission specs 都在 tools 模块附近
run_turn 明确内联 hook / permission / execute / result 回写
```

这个设计的优点：

```text
主线直观
本地 CLI 调试方便
工具调用链短
权限链路容易顺代码读下来
不需要先理解多个服务边界
```

代价也明显：

```text
工具越来越多后，中心文件会变大
新增工具容易继续往大 match / 大 specs 里塞
工具定义、schema、权限、执行、搜索、过滤容易耦合
不像 OpenHands 那样把 action / observation、tools package、Agent Server 分开
不像 DeerFlow 那样交给 LangGraph / middleware 体系治理
```

所以 Claw-Code 的 Tool System 可以被标记为：

> **集中式工具中枢：直接、内联、可控，但会随着工具生态扩大而变重。**

## 和 OpenHands / DeerFlow 的初步对照

更分层的系统通常有另一种取舍。

OpenHands 更像平台化 SWE Agent：

```text
App Server / Agent Canvas 管控制面
Agent Server / SDK 跑 agent loop
openhands-tools 承载工具能力
ActionEvent / ObservationEvent 作为事件模型
```

它的扩展性、远程运行、事件追踪、多 backend 和团队协作更自然，但调试链路也更长。

DeerFlow 更像 workflow / LangGraph run lifecycle：

```text
Gateway 管 run/thread/status
LangGraph agent runtime 管模型/工具循环
middleware 管预算、安全、澄清、压缩、错误处理等横切逻辑
```

它更适合长任务治理和图式编排，但不像 Claw-Code 这样能在一个本地 `run_turn` + tools 模块里看到大部分主线。

因此第一轮横向结论是：

> **Claw-Code 是“集中式工具中枢”：直接、内联、可控，适合本地 CLI；OpenHands / DeerFlow 是“分层式工具治理”：扩展、观测、平台化更强，但复杂度和调试链路也更高。**

## QA / 讨论记录

### Q: allowedTools 的 alias 是用户 query 里的别名吗？

> **状态**: draft
> **来源**: discussion / source-code

A: 不是。`read -> read_file`、`write -> write_file` 这类 alias 处理的是用户配置 / CLI 参数里的 allowed tools，不是自然语言 query。模型是否从“帮我读 README”推理出 `read_file`，仍由模型根据当前可见工具 schema 决定。

### Q: 为什么要过滤 allowed tools？

> **状态**: draft
> **来源**: discussion / source-code

A: allowed tools 过滤发生在工具定义暴露给模型之前。它可以减少模型可见工具面，让用户或子 agent 限定“这次只能用哪些工具”。如果 `allowed_tools` 是具体集合，`definitions(...)` 只会返回集合里的 builtin / plugin / runtime tools。

### Q: Hook 是什么？为什么说它是横切能力？

> **状态**: draft
> **来源**: discussion / source-code

A: Hook 是工具执行前后的外部插槽。`PreToolUse` 可以看工具调用、修改 input、拒绝、取消、要求 ask、附加反馈；`PostToolUse` / `PostToolUseFailure` 可以在结果产生后补充反馈或标记问题。它不是主业务工具本身，却横切每次工具调用，因此类似 middleware。

### Q: 为什么需要两道权限门？

> **状态**: draft
> **来源**: discussion / source-code

A: 第一扇门在 `run_turn`，判断“这个工具类型当前能不能用”；第二扇门在工具执行层，判断“这个具体参数会不会越界”。例如 `read_file README.md` 和 `read_file /etc/passwd` 都是 `read_file`，但风险不同；`bash git status` 和 `bash rm -rf /` 都是 `bash`，但风险不同。

### Q: ToolResult 为什么要转换成 provider 的 tool result？

> **状态**: draft
> **来源**: discussion / source-code

A: Claw-Code 内部用 `ContentBlock::ToolResult` 保存会话，但 provider API 需要自己的 `tool_result` 消息块。转换的目的是让下一轮模型调用能合法地看到工具结果，并用 `tool_use_id` 对齐上一轮工具调用。

### Q: ToolSearch 的精髓是什么？

> **状态**: draft
> **来源**: discussion / source-code

A: ToolSearch 是一个内置工具目录检索器，不是智能搜索 Agent。它让 Claw-Code 可以只默认暴露 `bash`、`read_file`、`write_file`、`edit_file`、`glob_search`、`grep_search` 等基础工具，把更多专用工具延迟到需要时按关键词检索。精髓是：工具系统不仅要扩展工具数量，还要管理模型每轮看到的工具表规模。

### Q: MCP / Agent / Task / Worker 算不算工具系统膨胀？

> **状态**: draft
> **来源**: discussion / source-code

A: 算，但不一定是贬义。它说明 Claw-Code 的工具系统已经从文件 / shell / 搜索扩展成 Agent Runtime 的能力总线：子 agent、后台任务、worker/team、MCP、skill、cron、LSP、git 等能力都被工具化，统一通过 tool use 暴露给模型。
