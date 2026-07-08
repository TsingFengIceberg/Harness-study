# Claw-Code Permission / Security：两道权限门、Hook 监工与动态风险分类

> **日期**: 2026-07-07 | **状态**: draft | **涉及版本**: `4ea31c1bc91c4e9bcbd67d51c550c01e127e6d0d`

## 相关文档

- Claw-Code 笔记入口：[README.md](README.md)
- Claw-Code Agent Loop：[agent-loop.md](agent-loop.md)
- Claw-Code Tool System：[tool-system.md](tool-system.md)
- Claw-Code Context Management：[context-management.md](context-management.md)
- Claw-Code Sandbox / Workspace：[sandbox-workspace.md](sandbox-workspace.md)
- 横向权限安全总结：[permission-security.md](../../comparison/permission-security.md)
- 横向 QA：[Harness Study 横向 QA](../../comparison/qa.md#permission--security--guardrail--权限安全与防护)

## 相关源码

| 模块 | 源码 | 作用 |
|---|---|---|
| Agent Loop 工具处理 | [conversation.rs](../../../submodules/claw-code/rust/crates/runtime/src/conversation.rs) | `ConversationRuntime::run_turn` 串起 PreToolUse hook、PermissionPolicy、ToolExecutor、PostToolUse hook、tool_result 回写。 |
| 权限策略 | [permissions.rs](../../../submodules/claw-code/rust/crates/runtime/src/permissions.rs) | `PermissionMode`、`PermissionPolicy`、`PermissionPrompter`、allow / deny / ask 规则、hook permission override。 |
| 执行层权限门 | [permission_enforcer.rs](../../../submodules/claw-code/rust/crates/runtime/src/permission_enforcer.rs) | `PermissionEnforcer`、`EnforcementResult`、bash / file write 的非交互式执行层检查与测试面。 |
| Hook 系统 | [hooks.rs](../../../submodules/claw-code/rust/crates/runtime/src/hooks.rs) | `PreToolUse`、`PostToolUse`、`PostToolUseFailure`、hook 输出解析、permission override、updated_input。 |
| 工具定义与分发 | [lib.rs](../../../submodules/claw-code/rust/crates/tools/src/lib.rs) | `ToolSpec.required_permission`、`execute_tool_with_enforcer`、bash/path/glob/grep 动态权限分类、具体工具执行。 |
| 配置 | [config.rs](../../../submodules/claw-code/rust/crates/runtime/src/config.rs) | hooks、permissions allow / deny / ask、默认模式等配置解析与测试。 |

## 1. 核心结论

Claw-Code 的权限安全不是一个独立“安全模块”最后兜底，而是嵌在本地 Agent Loop 和 Tool System 里的多层治理：

> **Claw-Code = ToolSpec 默认权限等级 + PreToolUse Hook 监工 + PermissionPolicy / PermissionPrompter 第一层授权 + PermissionEnforcer / 动态分类第二层复查 + PostToolUse 验收 + 拒绝结果回写模型上下文。**

通俗比喻：

> **Claw-Code 像本地施工队。模型是师傅，工具是电钻 / 锤子 / 挖掘机；权限系统不仅问“师傅能不能用这类工具”，还问“这次具体要怎么用、会不会越界、要不要业主确认、监工有没有提前拦”。**

最重要的精髓是“两道权限门”：

```text
第一道门：PermissionPolicy / PermissionPrompter
  问：这个工具按当前模式、规则、hook 指示，能不能用？要不要问用户？

第二道门：PermissionEnforcer / dynamic classification
  问：这次具体参数、命令、路径是否安全？是否越出 workspace？是否需要更高权限？
```

工具调用不是被静默拒绝。拒绝原因会作为 error `tool_result` 写回 session，下一轮模型可以看到并调整策略。

## 2. 总流程：模型 ToolUse 到 tool_result

Claw-Code 的权限治理发生在工具执行主链路里。主流程在 [conversation.rs](../../../submodules/claw-code/rust/crates/runtime/src/conversation.rs#L418-L517)：

```text
模型返回 ToolUse
  -> run_pre_tool_use_hook(tool_name, input)
     - cancel / fail / deny
     - updated_input
     - permission_override: Allow / Deny / Ask
     - permission_reason / messages
  -> PermissionPolicy.authorize_with_context(...)
     - denied_tools
     - deny_rules
     - ask_rules
     - allow_rules
     - active_mode vs required_mode
     - PermissionPrompter interactive approval
  -> ToolExecutor.execute(tool_name, effective_input)
     -> execute_tool_with_enforcer(...)
        - bash command classification
        - file path / workspace boundary classification
        - dynamic required_mode
  -> run actual tool
  -> PostToolUse / PostToolUseFailure hook
  -> ConversationMessage::tool_result(...)
  -> Session.messages
  -> 下一轮模型看到 tool_result
```

可以记成：

```text
Pre hook：开工前监工
PermissionPolicy：门卫看规则和当前模式
PermissionPrompter：需要时问用户
PermissionEnforcer：工具执行层硬闸门
Post hook：完工后验收
ToolResult：把结果 / 拒绝原因回写给模型
```

## 3. PermissionMode：权限等级和运行模式

[permissions.rs](../../../submodules/claw-code/rust/crates/runtime/src/permissions.rs#L7-L15) 定义：

```rust
pub enum PermissionMode {
    ReadOnly,
    WorkspaceWrite,
    DangerFullAccess,
    Prompt,
    Allow,
}
```

通俗解释：

| Mode | 含义 | 典型例子 |
|---|---|---|
| `ReadOnly` | 只读动作 | 读 workspace 内文件、搜索 workspace 内内容 |
| `WorkspaceWrite` | 可写 workspace 内资源 | 写文件、编辑文件、更新 todo |
| `DangerFullAccess` | 高风险动作 | 任意 shell、联网、workspace 外路径、外部触发等 |
| `Prompt` | 需要审批时问用户 | CLI 交互确认模式 |
| `Allow` | 宽松放行 | 明确放开权限的模式 |

这里要区分两个概念：

```text
active_mode：当前会话 / runtime 处于什么权限模式
required_mode：某个工具或某次具体调用要求什么权限等级
```

如果 `active_mode >= required_mode`，通常可以放行；如果不够，就可能需要 prompt 或直接 deny。

## 4. ToolSpec.required_permission：第一层粗粒度风险标签

工具定义里每个 `ToolSpec` 都有 `required_permission`。例如 [tools/src/lib.rs](../../../submodules/claw-code/rust/crates/tools/src/lib.rs#L507-L590)：

| 工具 | 默认权限 | 理由 |
|---|---|---|
| `read_file` | `ReadOnly` | 读取文件 |
| `glob_search` | `ReadOnly` | 搜索文件名 |
| `grep_search` | `ReadOnly` | 搜索文件内容 |
| `write_file` | `WorkspaceWrite` | 写文件 |
| `edit_file` | `WorkspaceWrite` | 编辑文件 |
| `TodoWrite` | `WorkspaceWrite` | 修改任务列表 |
| `Skill` | `ReadOnly` | 加载本地 skill 指令 |
| `bash` | `DangerFullAccess` | shell 能执行任意命令 |
| `WebFetch` / `WebSearch` | `DangerFullAccess` | 外部网络访问 |

这是一层“工具默认风险标签”：

> **先按工具类型判断大概风险：读工具低风险，写工具中风险，shell / web / 外部能力高风险。**

但它还不够，因为同一个工具的具体参数风险可能不同，所以后面还有动态分类。

## 5. PermissionPolicy：allow / deny / ask 的策略层

[PermissionPolicy](../../../submodules/claw-code/rust/crates/runtime/src/permissions.rs#L97-L109) 保存：

```text
active_mode
工具默认 required_mode 表：tool_requirements
allow_rules
deny_rules
ask_rules
denied_tools
```

授权入口是 [authorize_with_context](../../../submodules/claw-code/rust/crates/runtime/src/permissions.rs#L186-L312)。核心顺序是：

```text
1. denied_tools 命中：无条件 deny
2. deny_rules 命中：deny
3. 读取 current_mode 和 required_mode
4. 读取 ask_rules / allow_rules 命中情况
5. hook override = Deny：deny
6. hook override = Ask：prompt_or_deny
7. hook override = Allow：仍要尊重 ask_rule；若 allow_rule 或 mode 足够则 allow
8. ask_rules 命中：prompt_or_deny
9. allow_rules 命中，或 active_mode == Allow，或 active_mode >= required_mode：allow
10. Prompt 模式，或 WorkspaceWrite 想升到 DangerFullAccess：prompt_or_deny
11. 其他情况：deny
```

几个重要结论：

- `deny` 优先于 `allow`；
- `denied_tools` 是工具名级别无条件拒绝；
- `ask_rules` 可以压过 hook `Allow`；
- 需要确认但没有 `PermissionPrompter` 时，默认 deny；
- `WorkspaceWrite -> DangerFullAccess` 这种升级会触发确认。

**精髓标记：**

> **PermissionPolicy 不是简单白名单，而是 active mode、工具默认需求、allow / deny / ask 规则、denied_tools 和 hook override 的合成决策器。**

## 6. PermissionPrompter：交互确认边界

[PermissionPrompter](../../../submodules/claw-code/rust/crates/runtime/src/permissions.rs#L85-L88) 是交互确认接口：

```rust
pub trait PermissionPrompter {
    fn decide(&mut self, request: &PermissionRequest) -> PermissionPromptDecision;
}
```

`PermissionRequest` 包含 [permissions.rs](../../../submodules/claw-code/rust/crates/runtime/src/permissions.rs#L69-L76)：

```text
tool_name
input
current_mode
required_mode
reason
```

当 policy 需要用户确认时，会调用 prompter。如果没有 prompter，[prompt_or_deny](../../../submodules/claw-code/rust/crates/runtime/src/permissions.rs#L314-L343) 会直接 deny。

这对 CLI / 非交互环境很重要：

```text
交互模式：可以问用户，这条命令要不要放行？
非交互模式：问不了就拒绝，避免高风险动作自动执行。
```

## 7. allow / deny / ask rule 如何匹配 input？

规则解析在 [permissions.rs](../../../submodules/claw-code/rust/crates/runtime/src/permissions.rs#L355-L424)。规则基本形态：

```text
ToolName
ToolName(subject)
```

例如：

```text
Bash
Bash(git status)
read_file(src/main.rs)
read_file(src:*)
grep_search(DOCS:*)
```

匹配语义：

| 规则 | 含义 |
|---|---|
| `Bash` | 匹配所有 `Bash` 调用 |
| `Bash(*)` | 匹配所有 `Bash` 调用 |
| `Bash(git status)` | subject 精确等于 `git status` |
| `read_file(src/main.rs)` | subject 精确等于 `src/main.rs` |
| `read_file(src:*)` | subject 以 `src` 开头 |
| `grep_search(DOCS:*)` | subject 以 `DOCS` 开头 |

括号内容解析规则在 [parse_rule_matcher](../../../submodules/claw-code/rust/crates/runtime/src/permissions.rs#L415-L424)：

```text
空 或 *    -> Any
xxx:*      -> Prefix("xxx")
其他       -> Exact("xxx")
```

subject 提取在 [extract_permission_subject](../../../submodules/claw-code/rust/crates/runtime/src/permissions.rs#L469-L491)。它会尝试把 input 当 JSON 解析，并按顺序取这些字段：

```text
command
path
file_path
filePath
notebook_path
notebookPath
url
pattern
code
message
```

例如：

```json
{"command": "git status"}
```

subject 是 `git status`。

```json
{"path": "src/main.rs"}
```

subject 是 `src/main.rs`。

如果 input 不是 JSON 或找不到这些字段，就用整个 input 字符串。

## 8. PreToolUse Hook：权限前的外挂监工

Hook 系统定义在 [hooks.rs](../../../submodules/claw-code/rust/crates/runtime/src/hooks.rs)。工具前 hook 在 `run_turn` 中先于 PermissionPolicy 执行：[conversation.rs](../../../submodules/claw-code/rust/crates/runtime/src/conversation.rs#L419-L426)。

`HookRunResult` 可以携带 [hooks.rs](../../../submodules/claw-code/rust/crates/runtime/src/hooks.rs#L83-L92)：

```text
denied
failed
cancelled
messages
permission_override
permission_reason
updated_input
```

所以 `PreToolUse` hook 可以：

- 拒绝工具调用；
- 标记 hook 失败；
- 取消工具调用；
- 改写工具输入；
- 通过 `permission_override` 指示 `Allow` / `Deny` / `Ask`；
- 附加消息给模型可见的 tool_result。

在 [conversation.rs](../../../submodules/claw-code/rust/crates/runtime/src/conversation.rs#L428-L463) 中，hook cancelled / failed / denied 会直接变成 `PermissionOutcome::Deny`；否则 hook 的 `permission_override` 会进入 `PermissionContext`，交给 `PermissionPolicy.authorize_with_context(...)`。

通俗说：

> **PreToolUse hook 是工具执行前的外挂监工：它可以拦、可以改施工单、可以要求审批，也可以给后续权限判断提供理由。**

## 9. PostToolUse / PostToolUseFailure Hook：执行后验收

工具执行后，[conversation.rs](../../../submodules/claw-code/rust/crates/runtime/src/conversation.rs#L475-L501) 会根据工具是否出错选择：

```text
run_post_tool_use_hook
run_post_tool_use_failure_hook
```

如果 post hook `denied / failed / cancelled`，当前工具结果会被标为 error，并把 hook feedback merge 到输出中。

所以 post hook 不是“执行前放行”，而是“执行后验收 / 审计 / 追加反馈”：

```text
工具跑完了
  -> hook 检查输出
  -> 可以补充消息
  -> 可以把结果标成 error
  -> error tool_result 进入 session，下一轮模型看到
```

通俗说：

> **Pre hook 是开工前监工；Post hook 是完工后验收。**

## 10. 第二道权限门：PermissionEnforcer 与动态风险分类

第一层 policy 主要按工具名和规则判断，但同一个工具的具体风险可能不同：

```text
bash("git status")
bash("rm -rf /")

read_file("README.md")
read_file("/etc/passwd")
```

所以工具执行层还有第二道门。入口在 [execute_tool_with_enforcer](../../../submodules/claw-code/rust/crates/tools/src/lib.rs#L1367-L1499)，它会对部分工具按具体参数重新计算 `required_mode`：

| 工具 | 动态分类函数 | 目的 |
|---|---|---|
| `bash` | `classify_bash_permission(command)` | 按命令和路径判断是否高风险 |
| `PowerShell` | `classify_powershell_permission(command)` | Windows shell 命令分类 |
| `read_file` | `classify_read_path_permission(path, false)` | workspace 内读为 `ReadOnly`，越界读为 `DangerFullAccess` |
| `write_file` | `classify_file_path_permission(path, true)` | workspace 内写为 `WorkspaceWrite`，越界写为 `DangerFullAccess` |
| `edit_file` | `classify_file_path_permission(path, false)` | workspace 内改为 `WorkspaceWrite`，越界改为 `DangerFullAccess` |
| `glob_search` | `classify_glob_permission(input)` | base path / pattern 越界则高风险 |
| `grep_search` | `classify_grep_permission(input)` | path 越界则高风险 |

随后 [maybe_enforce_permission_check_with_mode](../../../submodules/claw-code/rust/crates/tools/src/lib.rs#L1502-L1522) 调用：

```text
enforcer.check_with_required_mode(tool_name, input, required_mode)
```

如果 active mode 不满足动态 required mode，则拒绝。

**精髓标记：**

> **第一道门问“这个工具类型能不能用”；第二道门问“这次具体参数有没有越界”。**

## 11. bash 动态分类：保守但存在两个相关实现面

当前 `execute_tool_with_enforcer(...)` 路径用的是 [tools/src/lib.rs](../../../submodules/claw-code/rust/crates/tools/src/lib.rs#L2187-L2220) 中的 `classify_bash_permission(command)`。

它做三步：

1. 取 base command；
2. 判断 base command 是否在 read-only allowlist；
3. 检查是否存在 dangerous paths；
4. 如果 read-only 且路径不危险，返回 `WorkspaceWrite`，否则返回 `DangerFullAccess`。

allowlist 包括：

```text
cat, head, tail, less, more, ls, ll, dir, find, test,
grep, rg, awk, sed, file, stat, readlink, wc, sort,
uniq, cut, tr, pwd, echo, printf
```

路径检查在 [has_dangerous_paths](../../../submodules/claw-code/rust/crates/tools/src/lib.rs#L2222-L2285)，会检查：

- 绝对路径是否不在当前 cwd 内；
- `~/` 路径；
- Windows 绝对路径；
- token 中 `$`；
- `../` / `../..` 等父目录逃逸；
- canonicalize 后是否不在 cwd 内。

需要注意一个细节：当前分类中 read-only bash 命令返回的是 `WorkspaceWrite`，不是 `ReadOnly`。源码注释也写着 ROADMAP：read-only commands targeting CWD paths get `WorkspaceWrite`，其他是 `DangerFullAccess`。

另外 [permission_enforcer.rs](../../../submodules/claw-code/rust/crates/runtime/src/permission_enforcer.rs#L224-L340) 里还有更保守的 `check_bash(...)` / `is_read_only_command(...)` helper 和测试面，明确拒绝 shell metacharacters、解释器、build driver、mutating git 子命令等。后续正式深入时需要继续核验这两套逻辑在实际产品路径中的调用关系，避免把它们混成一套。

## 12. 文件 / glob / grep 动态分类

文件路径相关函数在 [tools/src/lib.rs](../../../submodules/claw-code/rust/crates/tools/src/lib.rs#L2554-L2593)：

```text
classify_file_path_permission(path):
  workspace 内 -> WorkspaceWrite
  workspace 外 -> DangerFullAccess

classify_read_path_permission(path):
  workspace 内 -> ReadOnly
  workspace 外 -> DangerFullAccess

classify_glob_permission(input):
  base path 和 pattern 都在 workspace 内 -> ReadOnly
  否则 -> DangerFullAccess

classify_grep_permission(input):
  path 为空或在 workspace 内 -> ReadOnly
  否则 -> DangerFullAccess
```

`path_within_current_workspace(...)` 在 [tools/src/lib.rs](../../../submodules/claw-code/rust/crates/tools/src/lib.rs#L2595-L2631)，大致做：

```text
trim 包裹符号
拒绝 Windows absolute path
取 current_dir 作为 workspace root
相对路径 join cwd
必要时 canonicalize parent
最后检查 resolved.starts_with(cwd)
```

这说明 Claw-Code 不仅区分读 / 写，还把 workspace boundary 纳入权限等级：

```text
读 workspace 内文件 -> ReadOnly
读 workspace 外文件 -> DangerFullAccess
写 workspace 内文件 -> WorkspaceWrite
写 workspace 外文件 -> DangerFullAccess
```

## 13. 拒绝如何回写给模型？

在 [conversation.rs](../../../submodules/claw-code/rust/crates/runtime/src/conversation.rs#L465-L510)：

```text
PermissionOutcome::Allow
  -> 执行工具
  -> tool_result(output, is_error)

PermissionOutcome::Deny { reason }
  -> tool_result(reason, is_error=true)
```

所以权限系统不是只“保护环境”，还会影响模型下一轮上下文：

```text
工具没执行
拒绝理由作为 error tool_result 写回 Session
下一轮模型看到后，可以换策略
```

例如：

```text
模型想 bash("rm -rf build")
权限拒绝：command may modify state / requires approval
下一轮模型看到拒绝原因，改成只读检查、请求用户确认或给出手动步骤
```

这和 Context Management 是连起来的：

> **权限拒绝本身也是上下文事件，模型需要知道为什么被拦。**

## 14. Claw-Code hooks 与 DeerFlow middleware：外挂监工 vs 内建工位

用户讨论中特别标记的精髓：

> **Claw-Code hooks 是工具调用关卡上的“外挂监工”；DeerFlow middleware 是 agent runtime 流水线里的“内建工位”。**

两者相同点：都属于横切治理机制，都会插入 agent loop / tool loop 周边，处理安全、审计、上下文、错误、HITL 等非主线但关键的逻辑。

但它们不是同一种东西。

| 维度 | Claw-Code hooks | DeerFlow middleware |
|---|---|---|
| 主要定位 | 本地 CLI 工具调用前后扩展点 | LangGraph / agent runtime 的流程管线组件 |
| 作用范围 | 主要围绕 `PreToolUse` / `PostToolUse` / `PostToolUseFailure` | 覆盖 before_agent、before_model、wrap_model_call、after_agent、tool handling 等生命周期 |
| 实现形态 | 外部 command hook 为主，输入环境变量 / payload，解析 stdout / exit code | Python middleware，直接参与 state、messages、model call、tool call |
| 和权限关系 | 很强，PreToolUse 可 deny / ask / allow / updated_input | 有 guardrail / HITL / tool middleware，但权限不是集中在一个 hook 点 |
| 和上下文关系 | 主要通过 tool_result / feedback 间接影响 Session.messages | 上下文管理本身就是 middleware projection 的核心职责 |
| 对状态的控制 | 通常不拥有主流程状态，只在固定关卡给结果 | 深度读写 / 投影 `ThreadState` 和 LangGraph runtime state |
| 比喻 | 外挂监工 / 外接传感器 / 开工前审批与完工后验收 | 内建工位 / 流水线组件 / runtime 器官 |

为什么说 hook 是“外挂监工”？

```text
主流程：我要执行 bash
hook：等一下，我先检查；这次要 deny / ask / 改 input / 追加消息
主流程：根据 hook 结果继续或拒绝
```

为什么说 middleware 是“内建工位”？

```text
ThreadState 进入 agent runtime
  -> DynamicContextMiddleware 注入动态上下文
  -> SummarizationMiddleware 压缩历史
  -> DurableContextMiddleware 投影 durable state
  -> SystemMessageCoalescingMiddleware 合并 system message
  -> model call
```

Hook 像工具调用关卡上的外部监工；middleware 像状态流水线里不可缺少的一站。

## 15. 和 Agent Loop / Tool System / Context Management 的关系

### 和 Agent Loop 的关系

权限安全嵌在 `run_turn` 工具执行段：

```text
模型 -> ToolUse -> hook -> permission -> execute -> tool_result -> 模型
```

没有 tool use，就没有这段权限判断。

### 和 Tool System 的关系

Tool System 提供：

```text
ToolSpec.required_permission
GlobalToolRegistry.permission_specs
execute_tool_with_enforcer
```

权限系统基于这些工具定义和执行分发做判断。

### 和 Context Management 的关系

拒绝和 hook feedback 会进入 `tool_result`，再进入 Session messages。下一轮模型能看到这些安全反馈。

所以权限系统既是安全边界，也是模型上下文的一部分。

## 16. 阶段性结论

Claw-Code 的权限安全可以总结为：

> **本地 CLI Harness 里的工具调用双闸门：策略层先按工具名、模式、规则和用户确认做授权；执行层再按具体命令 / 路径做动态复查；hook 在前后提供外部治理；所有拒绝都作为 tool_result 回写给模型。**

最值得保留的精髓标记：

1. **两道权限门**：`PermissionPolicy / PermissionPrompter` 与 `PermissionEnforcer / dynamic classification`。
2. **ToolSpec 默认权限等级**：每个工具先有粗粒度 `required_permission`。
3. **策略合成决策**：`denied_tools / deny_rules / ask_rules / allow_rules / active_mode / hook override`。
4. **PreToolUse hook 是外挂监工**：可 deny / ask / allow / 改 input / 加反馈。
5. **PostToolUse hook 是完工验收**：可标错、附加反馈、审计输出。
6. **动态分类看具体参数**：bash command、文件路径、glob / grep path 会重新定级。
7. **workspace boundary 是本地安全核心**：workspace 内外决定 ReadOnly / WorkspaceWrite / DangerFullAccess。
8. **拒绝不是静默失败**：denial reason 作为 error tool_result 回写，模型下一轮可调整策略。
9. **hook vs middleware 的精髓区别**：Claw-Code hooks 是外挂监工；DeerFlow middleware 是内建工位。

## 17. QA / 讨论记录

### Q: Claw-Code 为什么需要“两道权限门”？

> **状态**: verified  
> **来源**: source-code / discussion

A: 第一层 `PermissionPolicy / PermissionPrompter` 按工具名、默认权限、active mode、allow / deny / ask rules、hook override 和用户确认做策略判断；第二层 `PermissionEnforcer / dynamic classification` 在工具执行层按具体参数重新定级，防止同一个工具的高风险参数绕过粗粒度判断。例如 `read_file("README.md")` 和 `read_file("/etc/passwd")` 都是 `read_file`，但后者应该升级为 `DangerFullAccess`；`bash("cat README.md")` 和 `bash("rm -rf /")` 也不应同等处理。

### Q: Claw-Code hooks 和 DeerFlow middleware 是一回事吗？

> **状态**: verified  
> **来源**: source-code / discussion

A: 不是。它们都是横切治理机制，但定位不同。Claw-Code hooks 更像本地 CLI 工具调用前后的外挂监工，主要围绕 `PreToolUse` / `PostToolUse` / `PostToolUseFailure` 拦截、审批、改写和审计工具调用；DeerFlow middleware 更像 LangGraph agent runtime 的内建工位，直接参与 `ThreadState`、上下文投影、模型调用、压缩、memory、HITL 和错误治理。可以概括为：**hook 是外挂监工，middleware 是内建工位**。

### Q: 权限拒绝后模型会知道吗？

> **状态**: verified  
> **来源**: source-code / discussion

A: 会。`ConversationRuntime::run_turn` 在 `PermissionOutcome::Deny` 时不会执行工具，而是把拒绝原因包装成 `ConversationMessage::tool_result(..., is_error=true)` 写回 session。下一轮模型会看到这个 error tool_result，从而改用只读操作、请求用户授权或给出手动步骤。

## 18. 后续待深入

- `PermissionPolicy` 和 CLI / config 的默认 mode 如何组合；
- `PermissionEnforcer.check_bash(...)` 与 `tools::classify_bash_permission(...)` 两套 bash 安全面的实际产品路径关系；
- sandbox runtime 与 permission system 的边界：权限拒绝和 Linux namespace / sandbox 哪个先发生、各自防什么；
- hooks 配置格式、stdout JSON 协议、exit code 语义和失败策略；
- 与 OpenClaw before_tool_call policy runtime、OpenHands confirmation policy / security analyzer、DeerFlow guardrail middleware 的横向对比。
