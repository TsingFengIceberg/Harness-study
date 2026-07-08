# Hermes Agent Permission / Security / Guardrail 研读笔记

> **日期**: 2026-07-07 | **状态**: draft | **涉及版本**: `05cbddc01234ea120cccc1f62d36f1ef352b0d52`

## 相关文档

- Hermes Agent Loop：[agent-loop.md](agent-loop.md)
- Hermes Tool System：[tool-system.md](tool-system.md)
- Hermes Context Management：[context-management.md](context-management.md)
- Hermes Sandbox / Workspace：[sandbox-workspace.md](sandbox-workspace.md)
- 横向 Permission / Security：[../../comparison/permission-security.md](../../comparison/permission-security.md)
- 横向 QA：[../../comparison/qa.md](../../comparison/qa.md#permission--security--guardrail--权限安全与防护)

## 源码入口

| 模块 | 源码 | 说明 |
|---|---|---|
| Agent init | [agent_init.py](../../../submodules/hermes-agent/agent/agent_init.py) | 初始化 `enabled_toolsets` / `disabled_toolsets` / `valid_tool_names`，形成当前 session 的工具可见性边界。 |
| Tool definitions / Tool Search bridge | [model_tools.py](../../../submodules/hermes-agent/model_tools.py) | `get_tool_definitions(...)` 工具表过滤；`handle_function_call(...)` 中 Tool Search bridge 的 scoped catalog 检查。 |
| Tool runtime helpers | [agent_runtime_helpers.py](../../../submodules/hermes-agent/agent/agent_runtime_helpers.py) | 工具调用分发主路径：plugin `pre_tool_call` block、tool request middleware、post hook、工具结果回写。 |
| Tool guardrails | [tool_guardrails.py](../../../submodules/hermes-agent/agent/tool_guardrails.py) | `ToolCallGuardrailController`：exact failure、same-tool failure、idempotent no-progress 检测；warning 默认开，hard stop 可选。 |
| Dangerous command approval | [approval.py](../../../submodules/hermes-agent/tools/approval.py) | shell / command 风险审批：`DANGEROUS_PATTERNS`、`HARDLINE_PATTERNS`、YOLO 冻结、contextvars session approval。 |
| ACP permissions bridge | [permissions.py](../../../submodules/hermes-agent/acp_adapter/permissions.py) | 把 ACP client permission decision 映射为 Hermes approval callback：allow_once / allow_session / allow_always / deny。 |
| ACP edit approval | [edit_approval.py](../../../submodules/hermes-agent/acp_adapter/edit_approval.py) | diff-based edit proposal、sensitive path 检查、ask / session / workspace 自动批准策略。 |
| Conversation loop | [conversation_loop.py](../../../submodules/hermes-agent/agent/conversation_loop.py) | 手写长期对话循环，承载 interrupt / steer / budget / tool result / context repair 等运行时边界。 |
| Turn context | [turn_context.py](../../../submodules/hermes-agent/agent/turn_context.py) | 每轮构造 messages、system prompt、memory prefetch、plugin context、preflight compression。 |
| Memory manager | [memory_manager.py](../../../submodules/hermes-agent/agent/memory_manager.py) | memory provider 编排、`<memory-context>` fencing、streaming scrubber，涉及长期记忆污染防护边界。 |

## 核心结论

Hermes Agent 的权限安全不是一个单独的“文件权限系统”，而是服务长期个人 Agent 的 **多层自我保护系统**：

```text
工具可见性：enabled_toolsets / disabled_toolsets / valid_tool_names
  -> 当前 session / subagent / worker 能看到哪些工具？

Tool Search bridge scope gate
  -> deferred tool 通过 bridge 调用时，是否仍受当前 scoped catalog 约束？

危险命令审批
  -> command 是否命中 dangerous / hardline pattern？是否需要用户确认？是否绝对禁止？

ACP / edit approval bridge
  -> 外部客户端如何批准工具 / 编辑？敏感路径和 diff proposal 如何处理？

Plugin hooks / middleware
  -> plugin pre_tool_call 能否阻断？tool request middleware / post hook 如何参与？

ToolCallGuardrailController
  -> 工具失败 / 无进展 / 重复失败是否要警告或硬停？

Memory / skills 写入边界
  -> 长期个人记忆和技能沉淀如何避免被错误或注入内容污染？
```

最重要的精髓：

> **Hermes 的安全重心不是“每次动作都变成平台 Action 安检”，而是“长期个人助理在多工具、多 provider、多入口、多记忆场景下，如何避免拿错工具、执行危险命令、反复失败、污染记忆和绕过当前 session 范围”。**

通俗比喻：

> **Hermes 像一个长期个人助理。它不只要防止今天误删文件，还要防止明天继续记错事、学坏技能、通过隐藏工具越权、在同一个坑里反复失败；所以它需要工具抽屉锁、危险动作确认、外部客户端审批、失败自检和记忆卫生。**

## 1. 工具可见性：先决定当前助理有哪些“工具抽屉”

Hermes 初始化时会把当前 session 的工具可见性固化下来。相关入口在 [agent_init.py](../../../submodules/hermes-agent/agent/agent_init.py) 和 [model_tools.py](../../../submodules/hermes-agent/model_tools.py)。

核心概念：

| 概念 | 作用 |
|---|---|
| `enabled_toolsets` | 只启用某些工具集。 |
| `disabled_toolsets` | 显式禁用某些工具集。 |
| `valid_tool_names` | 当前 session 实际可调用工具名集合。 |
| `get_tool_definitions(...)` | 根据 toolsets / config / cache 生成模型可见工具表。 |

这层回答的是：

```text
当前主 agent / subagent / kanban worker / 特定入口
到底能看到哪些 Hermes core tools、MCP tools、plugin tools？
```

它和 OpenClaw 的 tool policy pipeline 相似，都先控制“工具菜单”；但 Hermes 更偏个人 Agent 的 session / worker 范围，而不是多端产品里的 profile / sender / sandbox 多层策略管线。

## 2. Tool Search bridge scope gate：防止通过 bridge 绕过工具范围

Hermes 使用 progressive disclosure：工具太多时，不把所有工具一次性暴露给模型，而是暴露 `tool_search` / `tool_describe` / `tool_call` 等 bridge 工具。

这带来一个安全问题：

```text
如果当前 session 只允许一小部分工具，
模型能不能通过 tool_call bridge 直接调用全局 registry 里的其他工具？
```

[model_tools.py](../../../submodules/hermes-agent/model_tools.py) 的 `handle_function_call(...)` 对这个问题做了 scope gate。代码注释明确指出，如果没有这个检查，受限工具集的 session 可以通过 bridge 看到并调用整个进程 registry。

所以 Hermes 的 Tool Search 安全精髓是：

> **deferred tool 不是绕过权限的后门。通过 bridge 调用工具时，仍必须检查目标工具是否在当前 session 的 scoped catalog 里。**

通俗说：

```text
工具抽屉被锁起来后，不能因为有一个“帮我找工具”的前台，
就让助理从仓库后门拿到所有工具。
```

## 3. 危险命令审批：confirmable danger 与 hardline block

Hermes 的 shell / command 安全主要在 [tools/approval.py](../../../submodules/hermes-agent/tools/approval.py)。它区分两类风险：

| 类型 | 含义 |
|---|---|
| `DANGEROUS_PATTERNS` | 可确认的危险动作：命中后需要用户批准或 session approval。 |
| `HARDLINE_PATTERNS` | 无条件阻断的危险动作：即使 yolo / approval 也不能执行。 |

典型 hardline 包括：

```text
rm -rf /
mkfs
dd to /dev/
fork bomb
kill -1
shutdown / reboot
```

这里有几个关键设计：

1. **hardline 与 dangerous 分层**
   - dangerous 是“可能危险，需要问人”；
   - hardline 是“太危险，不能让模型靠确认绕过去”。

2. **YOLO mode frozen at import time**
   - 宽松模式在 import 时冻结，降低 prompt injection 在运行时篡改 approval 语义的风险。

3. **contextvars 管 session-local approval**
   - approval 状态按 session / context 隔离，避免并发会话互相污染。

4. **sudo stdin guard**
   - 防止模型通过 stdin 猜 sudo 密码。

这层比 Claw-Code 的 PermissionEnforcer 更偏命令 pattern / session approval；不像 OpenHands 那样先把动作做成 `ActionEvent` 再由 analyzer 评分。

## 4. ACP permission / edit approval：把外部客户端审批接入 Hermes

Hermes 还支持 ACP adapter。相关文件：

- [acp_adapter/permissions.py](../../../submodules/hermes-agent/acp_adapter/permissions.py)
- [acp_adapter/edit_approval.py](../../../submodules/hermes-agent/acp_adapter/edit_approval.py)

### 4.1 ACP permission bridge

[permissions.py](../../../submodules/hermes-agent/acp_adapter/permissions.py) 把 ACP client 的 decision 映射成 Hermes approval callback 语义：

```text
allow_once    -> once
allow_session -> session
allow_always  -> always
deny          -> deny
```

这说明 Hermes 的审批不只来自本地 CLI confirm，也可以由外部客户端 / 协议层承接。

### 4.2 ACP edit approval

[edit_approval.py](../../../submodules/hermes-agent/acp_adapter/edit_approval.py) 对文件编辑做 diff-based proposal：

```text
模型提出编辑
  -> 构造 EditProposal
  -> 检查 sensitive path（如 .git / .ssh）
  -> 按 ask / session / workspace policy 决定是否自动批准
  -> 必要时向 ACP client 请求批准
  -> timeout / deny / approve
```

这层类似“改文件前把差异单给用户看”。它和危险命令审批互补：一个偏 command risk，一个偏 edit proposal risk。

## 5. Plugin hooks / middleware：插件可以参与工具前后治理

Hermes 的工具调用分发主路径在 [agent_runtime_helpers.py](../../../submodules/hermes-agent/agent/agent_runtime_helpers.py)。其中关键点是：

```text
invoke_tool(...)
  -> plugin pre_tool_call
     - 可以 block
  -> tool request middleware
  -> per-tool handler dispatch
  -> post_tool_call hook
```

这说明 Hermes 也有 hook-like 防线。它和 Claw-Code hooks 的相似点是：都能在工具调用前后插入外部治理逻辑；不同点是 Hermes 的 hook / middleware 服务于 plugin、memory、session 和长期个人 Agent 生态，而不是主要围绕本地 coding CLI 的 `PreToolUse` / `PostToolUseFailure`。

## 6. ToolCallGuardrailController：防反复失败和无进展

[tool_guardrails.py](../../../submodules/hermes-agent/agent/tool_guardrails.py) 定义 `ToolCallGuardrailController`。它不是“授权系统”，而是运行时自检机制。

默认配置特点：

```text
warnings_enabled = True
hard_stop_enabled = False
```

也就是说，默认先提醒模型，不默认硬停；平台 / 用户可以选择开启 hard stop。

它主要检测三类模式：

| 检测 | 含义 |
|---|---|
| exact failure | 同一个工具 + 同一参数反复失败。 |
| same-tool failure | 同一工具连续失败，即使参数略有变化。 |
| idempotent no-progress | 幂等工具重复调用但没有推进任务。 |

这和 DeerFlow 的 LoopDetection / ToolProgress 非常值得对比：

```text
DeerFlow：工作流生产线的 loop / progress 熔断。
Hermes：长期个人助理的失败模式自检，默认提醒，hard stop 可选。
```

## 7. Memory / skills 写入边界：长期个人 Agent 的特殊风险

Hermes 的定位是长期个人 Agent，所以 memory 和 skills 是安全核心之一。已读源码确认：

- [memory_manager.py](../../../submodules/hermes-agent/agent/memory_manager.py) 负责 memory provider 编排、prefetch、`<memory-context>` fencing、streaming scrubber；
- [turn_context.py](../../../submodules/hermes-agent/agent/turn_context.py) 在每轮构造上下文时注入 memory / plugin / preflight compression；
- [conversation_loop.py](../../../submodules/hermes-agent/agent/conversation_loop.py) 和 turn finalizer 周边把工具结果、session persist、external memory sync 串进长期运行链路。

这里的安全风险不是传统“命令危险”，而是：

```text
模型会不会把 prompt injection 当成用户偏好记住？
会不会把一次错误工具结果沉淀成长期事实？
skill_manage 会不会写入有害或过拟合的技能？
外部 memory provider 同步失败 / 重试会不会造成不一致？
```

当前笔记只把它列为 Hermes 权限安全的特殊边界；后续 memory-system / skills-evolution 专题应继续核验具体写入、过滤、删除、审计和回滚机制。

## 8. 和 DeerFlow / OpenHands 的关键区别

### 对比 DeerFlow

DeerFlow 的安全像工作流工厂：Gateway authz、GuardrailMiddleware、RunManager、middleware chain 和 sandbox 共同维护 run 的健康。

Hermes 更像长期个人助理：工具可见性、Tool Search scope gate、危险命令审批、ACP edit approval、plugin hooks、guardrail 和 memory / skills 卫生共同维护长期协作安全。

一句话区别：

```text
DeerFlow 重点防 workflow run 失控。
Hermes 重点防长期个人 agent 拿错工具、做危险动作、反复失败和污染长期状态。
```

### 对比 OpenHands

OpenHands 的中心对象是 `ActionEvent`，每个模型动作进入平台事件层后由 `SecurityAnalyzer` 和 `ConfirmationPolicy` 判断风险。

Hermes 不把所有动作统一转换成 ActionEvent 风险等级，而是按实际风险点分散治理：

```text
工具范围 -> toolsets / valid_tool_names / scope gate
命令危险 -> approval.py patterns
编辑危险 -> ACP edit approval diff proposal
插件风险 -> plugin pre_tool_call block
重复失败 -> ToolCallGuardrailController
长期污染 -> memory / skills 边界
```

所以 Hermes 更像多层“自我保护”，OpenHands 更像平台“动作安检 + 工位隔离”。

## 9. QA / 讨论记录

### Q: Hermes 的 ToolCallGuardrailController 是权限系统吗？

> **状态**: verified
> **来源**: source-code / discussion

A: 严格说不是。它不决定某个工具是否授权，而是观察工具调用后的失败 / 无进展模式，发现 exact failure、same-tool failure 或 idempotent no-progress 时给模型 warning，必要时 hard stop。它更像长期个人助理的“自检提醒器”，防止模型在同一个坑里反复尝试。

### Q: Hermes 为什么需要 Tool Search bridge scope gate？

> **状态**: verified
> **来源**: source-code / discussion

A: 因为 Hermes 会用 `tool_search` / `tool_describe` / `tool_call` 做 deferred tools。如果 `tool_call` bridge 直接访问全局 registry，受限工具集的 session 或 subagent 就能绕过当前 `valid_tool_names` 调到不该暴露的工具。scope gate 确保 bridge 调用目标仍必须在当前 session 的 scoped catalog 中。

### Q: Hermes 的危险命令审批和 hardline block 有什么区别？

> **状态**: verified
> **来源**: source-code / discussion

A: dangerous pattern 是“需要确认的危险动作”，用户或 session approval 可以批准；hardline pattern 是“绝对不能执行的动作”，即使 yolo / approval 也阻断，例如 `rm -rf /`、`mkfs`、`dd` 写 `/dev/`、fork bomb、shutdown / reboot 等。这个分层避免把不可接受风险交给一次确认框处理。

### Q: 为什么说 Hermes 是“长期个人助理自我保护系统”？

> **状态**: verified
> **来源**: source-code / discussion

A: 因为 Hermes 的安全不只关心一次工具调用是否危险，还关心长期协作状态是否健康：当前 session 能看到哪些工具、deferred tool bridge 是否绕权、危险命令是否审批、编辑是否经过 diff proposal、plugin 是否能阻断、工具失败是否反复、memory / skills 是否可能被污染。它像个人助理的自我保护系统，而不是单个门禁或单个平台安检点。
