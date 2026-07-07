# Permission / Security / Guardrail 横向笔记：从 Claw-Code 双闸门到 Hermes 长期助理自我保护

> **日期**: 2026-07-07 | **状态**: draft | **当前覆盖**: Claw-Code / DeerFlow / OpenClaw / OpenHands / Hermes Agent

## 相关文档

- Claw-Code 权限安全：[../projects/claw-code/permission-security.md](../projects/claw-code/permission-security.md)
- DeerFlow 权限安全：[../projects/deer-flow/permission-security.md](../projects/deer-flow/permission-security.md)
- OpenClaw 权限安全：[../projects/openclaw/permission-security.md](../projects/openclaw/permission-security.md)
- OpenHands 权限安全：[../projects/openhands/permission-security.md](../projects/openhands/permission-security.md)
- Hermes Agent 权限安全：[../projects/hermes-agent/permission-security.md](../projects/hermes-agent/permission-security.md)
- Claw-Code Tool System：[../projects/claw-code/tool-system.md](../projects/claw-code/tool-system.md)
- OpenClaw Tool System：[../projects/openclaw/tool-system.md](../projects/openclaw/tool-system.md)
- DeerFlow Tool System：[../projects/deer-flow/tool-system.md](../projects/deer-flow/tool-system.md)
- DeerFlow Context Management：[../projects/deer-flow/context-management.md](../projects/deer-flow/context-management.md)
- 横向 Tool System：[tool-system.md](tool-system.md)
- 横向 Context Management：[context-management.md](context-management.md)
- 横向 QA：[qa.md](qa.md#permission--security--guardrail--权限安全与防护)

## 1. 当前阶段核心结论

本专题当前覆盖 Claw-Code、DeerFlow、OpenClaw、OpenHands 和 Hermes Agent。

先给一句总判断：

> **Claw-Code 的权限安全像本地 CLI 工具调用双闸门；DeerFlow 的安全治理像工作流工厂安全生产线；OpenClaw 的权限治理像多端 Agent 产品里的工具门禁 + 审批工单系统；OpenHands 的权限治理像远程开发园区里的 Action 风险安检 + 工位隔离；Hermes Agent 的权限安全像长期个人助理自我保护系统。**

当前最值得标记的横向精髓有几句：

> **Claw-Code hooks 是工具调用关卡上的“外挂监工”；DeerFlow middleware 是 agent runtime 流水线里的“内建工位”。**

> **OpenClaw 先用 tool policy pipeline 决定“你有没有这把工具”，再用 before_tool_call approval / hook / diagnostics 决定“这次使用要不要审批、放行或拦截”。**

> **OpenHands 先把模型动作登记成 ActionEvent，再用 SecurityAnalyzer / ConfirmationPolicy 判断风险和确认，最后把执行或拒绝作为 Observation 写回事件账本。**

> **Hermes Agent 先用 toolsets / valid_tool_names 和 Tool Search scope gate 限制工具范围，再用 dangerous command approval、ACP edit approval、plugin hooks、tool guardrails 和 memory / skills 卫生保护长期个人状态。**

这几句话很重要：hook、middleware、policy、approval、analyzer、confirmation、scope gate、guardrail 都是横切治理机制，但不要简单等同。它们分别服务本地 CLI、工作流 runtime、多端 Agent 产品、平台化 SWE sandbox、长期个人 Agent 五种不同场景。

## 2. 为什么需要权限 / 安全 / Guardrail 专题？

Agent Harness 的前三个大点已经回答了：

```text
Agent Loop：模型怎么一轮轮跑？
Tool System：模型怎么触达外部工具？
Context Management：模型下一轮看到什么？
```

Permission / Security / Guardrail 接着回答：

```text
模型想做动作时，谁判断能不能做？
是否需要问用户？
谁判断这次参数危险不危险？
被拒绝后模型怎么知道？
sandbox、hook、middleware、policy、scope gate 如何配合？
```

这不是附属问题，而是 Tool System 的安全边界，也是 Agent Loop 能否在真实环境中运行的前提。

## 3. Claw-Code：本地 CLI 工具调用双闸门

Claw-Code 的权限主线在 [permission-security.md](../projects/claw-code/permission-security.md) 已详细记录。可以简化为：

```text
模型 ToolUse
  -> PreToolUse Hook
  -> PermissionPolicy / PermissionPrompter
  -> ToolExecutor.execute
     -> execute_tool_with_enforcer
        -> dynamic classification
  -> run actual tool
  -> PostToolUse / PostToolUseFailure Hook
  -> tool_result 写回模型上下文
```

它的核心机制：

| 机制 | 作用 |
|---|---|
| `ToolSpec.required_permission` | 给每个工具一个默认风险等级：ReadOnly / WorkspaceWrite / DangerFullAccess 等。 |
| `PermissionPolicy` | 根据 active mode、工具默认需求、allow / deny / ask rules、denied_tools、hook override 做策略决策。 |
| `PermissionPrompter` | 当需要交互确认时询问用户；没有 prompter 时需要确认的动作默认拒绝。 |
| `PreToolUse hook` | 工具执行前的外挂监工，可 deny / ask / allow / 修改输入 / 附加反馈。 |
| `PermissionEnforcer` | 工具执行层非交互式复查，按具体命令 / 路径动态定级。 |
| `PostToolUse hook` | 工具执行后的验收 / 审计 / 输出检查。 |
| error `tool_result` | 权限拒绝作为错误结果写回模型上下文。 |

一句话：

> **Claw-Code 的安全重点是“这个工具调用能不能在我的本机 / workspace 里执行”。**

## 4. DeerFlow：工作流工厂安全生产线

DeerFlow 的权限安全在 [DeerFlow Permission / Security](../projects/deer-flow/permission-security.md) 已单独记录。它不能只概括为“middleware 防线”，更准确是三层防线：

```text
第一层：Gateway API authz
  -> AuthContext / require_permission / owner_check
  -> threads:read/write/delete、runs:create/read/cancel

第二层：GuardrailMiddleware + GuardrailProvider
  -> ToolCallRequest
  -> GuardrailRequest(tool_name, tool_input, agent_id, thread_id, user_id, is_subagent, ...)
  -> GuardrailDecision allow / deny
  -> deny 时返回 error ToolMessage，provider 异常默认 fail-closed

第三层：Workflow safety middleware chain + RunManager + Sandbox
  -> ToolErrorHandling：工具异常转成可恢复 ToolMessage
  -> LoopDetection：重复工具调用 warn / hard-stop
  -> ToolProgress：ACTIVE / WARNED / BLOCKED 进展状态机
  -> ReadBeforeWrite：已有文件写入前必须读过当前版本
  -> Clarification：信息不足时 Command(goto=END) 交还用户
  -> RunManager：同一 thread 的 reject / interrupt / rollback / cancel
  -> SandboxMiddleware：按 thread 获取和复用隔离执行环境
```

它的核心机制：

| 机制 | 作用 |
|---|---|
| Gateway authz | 管平台资源操作权限：谁能读写 thread、创建 / 读取 / 取消 run，是否是 owner。 |
| `GuardrailMiddleware` | 工具执行前调用可插拔 provider 做策略检查，deny 时把拒绝原因作为 error `ToolMessage` 写回模型。 |
| fail-closed guardrail | 策略 provider 出错时默认拒绝工具调用，而不是放行。 |
| `ToolErrorHandlingMiddleware` | 工具执行异常转成模型可见错误和恢复提示。 |
| `LoopDetectionMiddleware` | 检测重复工具调用集合和同类工具高频调用，warn / hard-stop 防 loop 失控。 |
| `ToolProgressMiddleware` | 观察工具结果是否推进任务，防止“换着参数但没有进展”。 |
| `ReadBeforeWriteMiddleware` | 对已有文件写入做先读和版本检查，降低误写 / 并发覆盖风险。 |
| `ClarificationMiddleware` | 把不确定性变成 HITL 边界，非交互场景可禁用。 |
| `RunManager` | 管同一 thread 的并发 run、cancel、interrupt / rollback、状态持久化和 orphan reconciliation。 |
| `SandboxMiddleware` | 提供 thread 级执行环境隔离和跨 turn 复用。 |

一句话：

> **DeerFlow 的安全重点是“这个 Gateway run 在多层防线下能不能被授权、健康、可恢复、可中断、可隔离地继续执行”。**

通俗比喻：

> **DeerFlow 像工作流工厂。Gateway 是厂门门禁，GuardrailMiddleware 是开工前安全检查员，LoopDetection / ToolProgress / ReadBeforeWrite / Clarification 是生产线质检和熔断器，RunManager 是班次调度和停线按钮，Sandbox 是实际干活的隔离工位。**

## 5. OpenClaw：工具门禁 + 审批工单系统

OpenClaw 的权限治理在 [OpenClaw Permission / Security](../projects/openclaw/permission-security.md) 已单独记录。它不是只问“这个命令能不能执行”，而是先问：

```text
当前 agent / sender / sandbox / subagent 能看到哪些工具？
某次 plugin tool 调用是否需要审批？
审批请求应该走本地 TUI，还是走 Gateway 路由到远端 / 多端用户？
```

可以简化为两段式：

```text
工具可见性阶段：
  createOpenClawCodingTools
    -> tool policy pipeline
       -> profile / provider / global / agent / group / sender / sandbox / subagent / inherited
    -> 当前模型看到的工具菜单

单次执行阶段：
  model toolCall
    -> AgentTool.beforeToolCall
    -> runBeforeToolCallHook
       -> loop detection
       -> trusted policy / skill approval
       -> plugin approval
       -> plugin before_tool_call hooks
       -> diagnostics
    -> execute actual tool
    -> events + tool result 回写
```

它的核心机制：

| 机制 | 作用 |
|---|---|
| `ToolPolicyLike` | 基础策略 `{ allow?: string[]; deny?: string[] }`，控制工具可见性。 |
| tool name normalization | 把 alias / 习惯名归一到内部工具名，例如 `bash -> exec`。 |
| group / plugin expansion | 把 `group:plugins`、plugin id 等高层表达展开成具体 plugin tool names。 |
| tool policy pipeline | 按 profile、provider、global、agent、group、sender、sandbox、subagent、inherited 多层叠加策略。 |
| subagent denylist | 默认限制子 agent 拿到 gateway、session、cron、spawn 等控制面工具。 |
| `runBeforeToolCallHook` | 对单次工具调用做 loop detection、trusted policy、approval、plugin hook、diagnostics。 |
| `PluginApprovalRequest` | 把敏感 plugin tool 调用抽象成审批请求，支持 allow-once / allow-always / deny。 |
| Embedded approval broker | TUI / embedded 模式下的本地 pending approval broker。 |
| Gateway approval | 多端 / 远端模式下通过 `plugin.approval.request` / `plugin.approval.waitDecision` 路由审批。 |

一句话：

> **OpenClaw 的安全重点是“当前 agent 在当前产品上下文下能拿到什么工具，以及敏感 plugin tool 的审批工单该由谁处理”。**

## 6. OpenHands：Action 风险安检 + 工位隔离

OpenHands 的权限治理在 [OpenHands Permission / Security](../projects/openhands/permission-security.md) 已单独记录。它不是以工具菜单为中心，而是以 `ActionEvent` 为中心。

OpenHands 执行面把模型 tool call 转成平台事件层的 ActionEvent，再做风险分析和确认暂停：

```text
LLM tool call
  -> parse / normalize / validate
  -> ActionEvent(security_risk, summary, tool_call, action)
  -> SecurityAnalyzer.security_risk(ActionEvent)
  -> ConfirmationPolicy.should_confirm(risk)
     -> WAITING_FOR_CONFIRMATION 或继续执行
  -> ObservationEvent / UserRejectObservation
  -> EventLog / View / 下一轮 LLM messages
```

它的核心机制：

| 机制 | 作用 |
|---|---|
| `ActionEvent` | 平台事件层的一次模型动作，包含 action、tool_call、summary、security_risk 等。 |
| `SecurityRisk` | `UNKNOWN` / `LOW` / `MEDIUM` / `HIGH` 风险等级。 |
| `ConfirmationPolicy` | `AlwaysConfirm` / `NeverConfirm` / `ConfirmRisky`，按风险决定是否暂停确认。 |
| `SecurityAnalyzer` | 对 ActionEvent 做风险分析，可由 LLM、pattern、policy rail、GraySwan 或 ensemble 提供。 |
| `WAITING_FOR_CONFIRMATION` | conversation lifecycle 中的正式等待确认状态。 |
| `UserRejectObservation` | 用户拒绝后作为 tool role observation 回写给模型。 |
| workspace / sandbox | 动作执行的硬边界，限制 action 即使执行也只能在对应工作区 / sandbox 中运行。 |

一句话：

> **OpenHands 的安全重点是“这个具体 ActionEvent 风险多高，是否需要暂停确认；即使执行，也被限制在哪个 workspace / sandbox 里”。**

通俗比喻：

> **OpenHands 像远程开发园区：Agent 每个动作都要登记成工单；危险工单过安检和确认；拒绝也会记到账本；真正干活只能在分配的 workspace / sandbox 工位里干。**

## 7. Hermes Agent：长期个人助理自我保护系统

Hermes Agent 的权限安全在 [Hermes Agent Permission / Security](../projects/hermes-agent/permission-security.md) 已单独记录。它不是单点 PermissionPolicy，也不是统一 ActionEvent 风险评分，而是长期个人 Agent 的多层自我保护：

```text
工具可见性：enabled_toolsets / disabled_toolsets / valid_tool_names
  -> 当前 session / subagent / worker 能看到哪些工具

Tool Search bridge scope gate
  -> deferred tool 通过 tool_call bridge 执行时仍受 scoped catalog 限制

危险命令审批
  -> DANGEROUS_PATTERNS 需要确认
  -> HARDLINE_PATTERNS 即使 yolo / approval 也无条件阻断

ACP / edit approval bridge
  -> 外部 client permission decision
  -> diff-based EditProposal、sensitive path、ask / session / workspace policy

Plugin hooks / middleware
  -> plugin pre_tool_call 可以 block
  -> tool request middleware / post_tool_call hook 参与工具前后治理

ToolCallGuardrailController
  -> exact failure / same-tool failure / idempotent no-progress
  -> warning 默认开启，hard_stop 可选

Memory / skills 写入边界
  -> 长期记忆和技能沉淀需要防错误事实、prompt injection、过拟合经验污染
```

它的核心机制：

| 机制 | 作用 |
|---|---|
| toolsets / `valid_tool_names` | 控制当前 session / worker 实际可见和可调用的工具集合。 |
| Tool Search scope gate | 防止受限 session 通过 `tool_call` bridge 调用全局 registry 中未授权工具。 |
| dangerous command approval | 对危险 shell / command pattern 要求确认，approval 状态按 session 隔离。 |
| hardline command block | 对 `rm -rf /`、`mkfs`、fork bomb、shutdown 等不可接受风险无条件阻断。 |
| ACP permission bridge | 把外部 client 的 allow_once / allow_session / allow_always / deny 映射进 Hermes approval。 |
| ACP edit approval | 用 diff proposal 和 sensitive path 检查治理文件编辑。 |
| plugin pre_tool_call | 插件可在工具调用前阻断或参与治理。 |
| `ToolCallGuardrailController` | 检测重复失败和无进展，默认 warning，必要时 hard stop。 |
| memory / skills hygiene | 长期个人状态的污染防护边界，后续 memory / skills 专题继续深挖。 |

一句话：

> **Hermes 的安全重点是“长期个人助理不要拿错工具、绕过当前 session 范围、执行危险命令、反复失败，或把错误 / 注入内容沉淀成长期记忆和技能”。**

通俗比喻：

> **Hermes 像长期个人助理。它不只要防止今天误删文件，还要防止明天继续记错事、学坏技能、从后门拿工具、在同一个坑里反复失败；所以它需要工具抽屉锁、危险动作确认、外部客户端审批、失败自检和记忆卫生。**

## 8. Hooks vs Middleware：外挂监工 vs 内建工位

### 8.1 共同点：都是横切逻辑

Claw-Code hooks 和 DeerFlow middleware 都用于处理 Agent Loop 主线之外但必须插入主线的逻辑：

- 权限 / 审批；
- 日志 / 审计；
- 工具执行前后检查；
- 上下文注入 / 压缩；
- 错误处理；
- HITL；
- loop / budget 防护；
- memory 更新。

这类逻辑不属于“模型调用 -> 工具调用 -> 工具结果”的主干，但会在主干多个位置发挥作用，所以叫横切逻辑。

### 8.2 最关键区别

> **Claw-Code hooks 是外挂监工；DeerFlow middleware 是内建工位。**

这句话可以展开为：

```text
Claw-Code hook：
  主流程走到工具调用关卡时，调用一个外部监工脚本；
  监工可以放行、拒绝、要求审批、改输入、追加反馈。

DeerFlow middleware：
  它本身就是 agent runtime 流水线的一站；
  负责读写 ThreadState、投影上下文、包裹模型调用、处理工具错误和 run 状态。
```

### 8.3 横向对比表

| 维度 | Claw-Code hooks | DeerFlow middleware |
|---|---|---|
| 主要定位 | 本地 CLI 工具调用前后扩展点 | LangGraph / agent runtime 的流程管线组件 |
| 作用范围 | 主要围绕 tool use 生命周期 | 覆盖 agent / model / tool / state 多个生命周期点 |
| 典型事件 / 位置 | `PreToolUse`、`PostToolUse`、`PostToolUseFailure` | before_agent、before_model、wrap_model_call、after_agent、tool middleware 等 |
| 实现形态 | 外部 command hook 为主，输入环境变量 / payload，输出解析结果 | Python middleware 类 / 函数，直接操作 state、messages、model call |
| 能否改输入 | 可以，`updated_input` | 可以，直接改 / 投影 state 或 messages |
| 能否拒绝动作 | 可以，`denied / failed / cancelled`，或 permission override | 可以，通过 middleware 返回错误、Command、终止、HITL 等 |
| 是否深度参与上下文管理 | 较弱，主要通过工具反馈间接进入 Session messages | 很强，DeerFlow 上下文管理本身就是 middleware projection |
| 是否深度参与权限 | 很强，PreToolUse 能影响 PermissionPolicy | 有 guardrail / HITL / tool middleware，但权限不集中在一个 hook 点 |
| 典型比喻 | 工具执行前后的外部监工 | 状态流水线里的内建工位 |
| 更适合 | 本地 CLI、安全审计、工具调用前后拦截、企业脚本扩展 | 工作流 runtime、状态投影、模型调用治理、长任务管线 |

## 9. OpenClaw 和 hooks / middleware 的关系

OpenClaw 也有 hook-like 的 before-tool-call runtime 和 plugin hooks，但它和 Claw-Code / DeerFlow 都不完全一样：

```text
Claw-Code hook：
  本地 CLI 工具调用关卡上的外挂监工。

DeerFlow middleware：
  LangGraph agent runtime 里的内建工位。

OpenClaw before_tool_call / plugin approval：
  多端 Agent 产品工具调用前的工单审查站，连接 tool policy、plugin、approval、Gateway、diagnostics、event stream。
```

OpenClaw 的关键差异是它把工具治理放进产品会话上下文中：同一次审批可能要知道 sender、channel、reviewer device、sandbox、session、plugin id 等信息。

因此 OpenClaw 更像：

> **工具菜单门禁 + 审批工单中心 + 插件生态治理点。**

## 10. 从上下文管理角度看差异

Claw-Code 上下文主链路仍是：

```text
Session.messages
  -> provider message conversion
  -> model
```

Hook 会影响上下文，但主要是旁路影响：

```text
hook deny / feedback
  -> error tool_result
  -> Session.messages
  -> 下一轮模型看到
```

DeerFlow 则不同。DeerFlow 的上下文主链路本身就是 middleware projection：

```text
ThreadState
  -> DynamicContextMiddleware
  -> SummarizationMiddleware
  -> DurableContextMiddleware
  -> SystemMessageCoalescingMiddleware
  -> provider messages
```

OpenClaw 的上下文影响则更产品事件化：

```text
tool policy / approval / diagnostics
  -> AgentTool execution event
  -> session event stream / UI / persistence
  -> tool result / diagnostic feedback
  -> AgentContext.messages / 下一轮模型输入
```

OpenHands 的上下文影响则是 action / observation 账本化：

```text
ActionEvent risk / confirmation / rejection
  -> WAITING_FOR_CONFIRMATION 或 ObservationEvent
  -> EventLog / View
  -> prepare_llm_messages
  -> 下一轮模型看到执行结果或拒绝原因
```

所以可以概括：

> **Claw-Code hook 是上下文的旁路影响者；DeerFlow middleware 是上下文投影的主执行者；OpenClaw approval / diagnostics 是产品事件流里的治理反馈源；OpenHands ActionEvent / ObservationEvent 是安全判断、执行结果和拒绝反馈的事件账本；Hermes toolsets / approval / guardrail / memory hygiene 是长期个人状态的自我保护层。**

## 11. 从权限安全角度看差异

### Claw-Code

核心问题是：

```text
这个工具调用能不能在本机执行？
这个命令会不会改系统？
这个路径会不会越出 workspace？
要不要问用户？
```

所以它需要：

```text
ToolSpec.required_permission
PermissionPolicy
PermissionPrompter
PermissionEnforcer
bash / file path dynamic classification
PreToolUse / PostToolUse hook
```

### DeerFlow

核心问题更像：

```text
当前用户是否有权限操作 thread / run？
这次工具调用是否通过 guardrail provider？
工具错误如何恢复？
是否陷入 loop 或无进展？
写文件前是否读过当前版本？
run 取消时是 interrupt 还是 rollback？
工具实际在哪个 sandbox 里执行？
```

所以它需要：

```text
Gateway authz / owner_check
GuardrailMiddleware / GuardrailProvider
ToolErrorHandling / LoopDetection / ToolProgress
ReadBeforeWrite / Clarification
RunManager interrupt / rollback / cancel
SandboxMiddleware
LangGraph state / checkpoint / Command
```

### OpenClaw

核心问题更像：

```text
当前 agent 能看到哪些工具？
请求来源 sender / channel 是否影响工具面？
sandbox 环境是否允许某些工具？
subagent 是否应该被禁止使用控制面工具？
plugin tool 调用是否需要审批？
审批走本地 TUI 还是 Gateway？
```

所以它需要：

```text
tool policy pipeline
ToolPolicyLike allow / deny
normalize / group expansion
sender / sandbox / subagent / inherited layers
before_tool_call runtime
PluginApprovalRequest
EmbeddedPluginApprovalBroker
Gateway approval routing
diagnostics / event stream
```

### OpenHands

核心问题更像：

```text
这个具体 ActionEvent 风险多高？
风险来自 LLM 自评、本地 pattern、policy rail，还是外部安全服务？
是否需要把 conversation 暂停到 WAITING_FOR_CONFIRMATION？
用户拒绝后模型是否能收到 observation 反馈？
即使 action 执行，它在哪个 workspace / sandbox 中执行？
```

所以它需要：

```text
ActionEvent
SecurityRisk
SecurityAnalyzer
PatternSecurityAnalyzer / PolicyRailSecurityAnalyzer / GraySwanAnalyzer
EnsembleSecurityAnalyzer
ConfirmationPolicy
WAITING_FOR_CONFIRMATION
UserRejectObservation
workspace / sandbox boundary
```

### Hermes Agent

核心问题更像：

```text
当前 session / subagent / worker 能看到哪些工具？
Tool Search bridge 会不会绕过当前 scoped catalog？
危险命令是需要确认，还是无条件 hardline block？
编辑是否应该通过 diff proposal 和 ACP client 审批？
plugin hook 是否能在工具调用前阻断？
工具是否在反复失败或幂等无进展？
长期 memory / skills 是否可能被污染？
```

所以它需要：

```text
toolsets / valid_tool_names
Tool Search bridge scope gate
DANGEROUS_PATTERNS / HARDLINE_PATTERNS
ACP permission bridge / edit approval
plugin pre_tool_call block
ToolCallGuardrailController
memory / skills hygiene
```

可以概括：

```text
Claw-Code：权限安全更像本地工具闸门。
DeerFlow：安全治理更像工作流工厂安全生产线。
OpenClaw：权限治理更像平台化工具门禁 + 审批工单系统。
OpenHands：权限治理更像远程开发园区的 Action 风险安检 + 工位隔离。
Hermes Agent：权限治理更像长期个人助理自我保护系统。
```

## 12. 从扩展方式看差异

### Claw-Code hooks：用户 / 部署侧可配置

Hook 更适合由用户、团队或部署环境注入：

```text
配置一个 command
Claw-Code 在 PreToolUse / PostToolUse 时调用
hook 根据 tool_name / input / output 判断
返回 deny / allow / ask / feedback / updated_input
```

适合：

- 企业安全脚本；
- 本地审计日志；
- 禁止某类命令；
- 检查文件路径；
- 对工具输出做敏感信息扫描；
- 不改 Rust 源码的扩展。

### DeerFlow middleware：开发者 / 平台侧内建

Middleware 更适合作为平台开发者写入 agent runtime：

```text
make_lead_agent
  -> build_middlewares
  -> create_agent(..., middleware=[...])
```

适合：

- 深度操作 ThreadState；
- 在 model call 前后统一治理；
- 和 LangGraph checkpoint / Command / stream 集成；
- 把 memory、summary、durable context 做成长期机制；
- 让 workflow runtime 拥有稳定的中间件防线。

### OpenClaw policy / approval：产品运行时内建 + Gateway 可路由

OpenClaw 的扩展更偏产品运行时和 plugin / gateway 生态：

```text
createOpenClawCodingTools
  -> tool policy pipeline
  -> AgentTool.beforeToolCall
  -> plugin approval / hooks
  -> embedded broker 或 gateway approval
```

适合：

- 多端 Agent 产品的工具可见性控制；
- 按 sender / channel / sandbox / subagent 改变工具菜单；
- plugin tool 调用审批；
- 把审批请求路由到 TUI、远端 UI、reviewer device；
- 让工具治理结果进入 diagnostics / event stream。

### OpenHands analyzer / confirmation：执行面内建 + 控制面配置

OpenHands 的扩展更偏 conversation settings 和执行面 action analyzer：

```text
conversation_settings
  -> confirmation_mode / security_analyzer
  -> ConversationSettings.create_request
  -> StartConversationRequest
  -> SDK ConversationState
  -> ActionEvent risk / confirmation
```

适合：

- 平台化 SWE Agent 的 action 风险分析；
- 用本地 pattern / policy rail 或外部 API 评估具体动作；
- 在 conversation lifecycle 中暂停等待用户确认；
- 把拒绝结果作为 observation 写回模型；
- 将 action 执行限制在 workspace / sandbox 中。

### Hermes toolsets / approval / guardrail：长期个人 Agent 运行时自我保护

Hermes 的扩展更偏 session 工具范围、命令审批、ACP client、plugin hooks 和长期状态治理：

```text
agent init
  -> enabled_toolsets / disabled_toolsets / valid_tool_names
  -> get_tool_definitions / Tool Search bridge scope gate
  -> dangerous command approval / hardline block
  -> ACP permission / edit approval
  -> plugin pre_tool_call / tool request middleware
  -> ToolCallGuardrailController
  -> memory / skills write boundary
```

适合：

- 长期个人 Agent 的工具范围控制；
- deferred tool / Tool Search 的越权防护；
- shell / edit 等高风险动作的人机审批；
- plugin 生态的工具前后治理；
- 对重复失败、无进展和长期记忆污染做自我保护。

## 13. 当前阶段横向判断

Claw-Code、DeerFlow、OpenClaw、OpenHands 和 Hermes Agent 都有“防线”，但防线形态不同：

| 项目 | 防线形态 | 设计重心 |
|---|---|---|
| Claw-Code | 本地工具调用双闸门 + hook 监工 | 防止模型在本机执行越权 / 危险工具调用 |
| DeerFlow | Gateway authz + GuardrailMiddleware + workflow safety middleware / RunManager / Sandbox | 防止长任务 workflow 资源越权、工具策略绕过、run 流程失控、上下文和文件写入出错 |
| OpenClaw | tool policy pipeline + before_tool_call runtime + approval broker / gateway | 控制多端 Agent 产品中的工具可见性、plugin 审批、subagent 控制面边界和事件化治理 |
| OpenHands | ActionEvent risk analyzer + ConfirmationPolicy + workspace / sandbox boundary | 控制平台化 SWE Agent 的具体动作风险、确认暂停、拒绝反馈和执行环境隔离 |
| Hermes Agent | toolsets / scope gate + dangerous command / ACP approval + plugin hooks + tool guardrail + memory hygiene | 控制长期个人 Agent 的工具范围、危险命令、编辑审批、重复失败和长期记忆 / 技能污染 |

这不是谁更高级，而是场景不同：

```text
本地 CLI coding agent：
  最危险的是模型在你的机器上乱跑命令、乱改文件。

长任务 workflow agent：
  最危险的是 run 状态失控、上下文污染、工具错误无法恢复、无限循环、HITL 边界不清。

多端 Agent session runtime：
  最危险的是不同入口、不同 sender、不同 sandbox、不同 subagent 层级拿到不该拿的工具，
  或敏感 plugin tool 调用没有被正确审批和路由。

平台化 SWE Agent：
  最危险的是具体 action 破坏 workspace、执行高风险命令、受 prompt injection 影响，
  或在 sandbox / workspace 边界之外访问不该访问的资源。

长期个人 Agent：
  最危险的是跨会话记错事、学坏技能、通过 deferred tool bridge 绕权、
  或在危险命令 / 编辑 / 插件调用里把一次错误变成长期风险。
```

## 14. 后续扩展方向

本专题后续可继续补：

- **Sandbox Runtime**：权限系统和执行环境隔离的边界；
- **HITL Patterns**：ask / approval / clarification / interrupt / steer 的统一比较；
- **Memory / Skills Hygiene**：长期记忆、技能沉淀、外部 memory provider 的污染防护与回滚策略。

## 15. QA / 讨论记录

### Q: Claw-Code hooks 和 DeerFlow middleware 是一回事吗？

> **状态**: verified
> **来源**: source-code / discussion

A: 不是。它们都属于横切治理机制，但定位不同。Claw-Code hooks 更像本地 CLI 工具调用前后的外挂监工，主要围绕 `PreToolUse` / `PostToolUse` / `PostToolUseFailure` 拦截、审批、改写和审计工具调用；DeerFlow middleware 更像 LangGraph agent runtime 的内建工位，直接参与 `ThreadState`、上下文投影、模型调用、压缩、memory、HITL 和错误治理。可以概括为：**hook 是外挂监工，middleware 是内建工位**。

### Q: 为什么说 Claw-Code 是双闸门，而 DeerFlow 是中间件防线？

> **状态**: draft
> **来源**: discussion / source-code

A: Claw-Code 面向本地 CLI，工具调用直接触达用户机器和 workspace，因此安全重点是工具调用能否执行：第一道门由 `PermissionPolicy / PermissionPrompter` 按模式、工具、规则和用户确认授权；第二道门由 `PermissionEnforcer / dynamic classification` 按具体命令和路径复查。DeerFlow 面向 Gateway + LangGraph 长任务 workflow，安全治理至少分成 Gateway API authz、GuardrailMiddleware + provider、workflow safety middleware / RunManager / Sandbox 三层，因此更像工作流工厂安全生产线。

### Q: OpenClaw 的权限治理和 Claw-Code 的两道权限门有什么本质不同？

> **状态**: verified
> **来源**: source-code / discussion

A: Claw-Code 的重点是本地工具调用能不能在用户机器 / workspace 里执行，因此有 `PermissionPolicy / PermissionPrompter` 和 `PermissionEnforcer` 两道门。OpenClaw 的重点是当前 agent 在当前 profile、provider、group、sender、sandbox、subagent 和 inherited 限制下能看到什么工具，以及某次 plugin tool 调用是否需要通过 approval / hook / diagnostics 放行。可以概括为：Claw-Code 是本地工具双闸门，OpenClaw 是平台化工具门禁 + 审批工单系统。

### Q: OpenClaw approval 为什么说是审批工单系统？

> **状态**: verified
> **来源**: source-code / discussion

A: 因为 OpenClaw 把敏感 plugin tool 调用抽象成 `PluginApprovalRequest`，支持 `allow-once`、`allow-always`、`deny`、timeout 和 allowed decisions。TUI / embedded 模式下，请求进入 `EmbeddedPluginApprovalBroker` 的 pending map，并通过 approval events 让 UI 展示和回填；多端 / Gateway 模式下，请求通过 `plugin.approval.request` 和 `plugin.approval.waitDecision` 路由到 reviewer / device / UI。它不是单纯本地 confirm，而是可本地、可远端、可路由、可超时的审批生命周期。

### Q: OpenHands 的权限治理中心是什么？

> **状态**: verified
> **来源**: source-code / discussion

A: OpenHands 的权限治理中心是 `ActionEvent`，不是工具菜单。模型 tool call 会先被解析、规范化、校验并转换成 `ActionEvent`；`SecurityAnalyzer` 对 ActionEvent 评估 `SecurityRisk`；`ConfirmationPolicy` 根据风险决定是否把 conversation 置为 `WAITING_FOR_CONFIRMATION`；执行或拒绝结果再通过 `ObservationEvent` / `UserRejectObservation` 回写给模型。workspace / sandbox 则提供动作执行硬边界。

### Q: OpenHands 会无条件相信模型自评的 security_risk 吗？

> **状态**: verified
> **来源**: source-code / discussion

A: 不会。OpenHands 会在工具 schema 中暴露 `security_risk` 参数，让模型可以预测风险；但只有显式配置了 `security_analyzer` 时才采纳这个字段。没有 analyzer 时，模型提供的 `security_risk` 会被忽略并返回 `UNKNOWN`。这避免模型通过自报 `LOW` 绕过确认策略。

### Q: OpenHands 的用户拒绝会反馈给模型吗？

> **状态**: verified
> **来源**: source-code / discussion

A: 会。`reject_pending_actions(...)` 会为每个 pending action 写入 `UserRejectObservation`，它转成 LLM message 时是 tool role，内容为 `Action rejected: <reason>`，并保留对应 `tool_name` 和 `tool_call_id`。所以拒绝不是静默丢弃，而是进入 EventLog，并作为 observation 反馈给下一轮模型。

### Q: DeerFlow 的安全治理是不是只有 middleware？

> **状态**: verified
> **来源**: source-code / discussion

A: 不是。middleware 是 DeerFlow 的核心风格，但完整防线至少有三层：Gateway API authz 管用户和资源权限；GuardrailMiddleware + GuardrailProvider 管工具调用前策略检查；workflow safety middleware chain + RunManager + Sandbox 管 run lifecycle、工具错误、loop、进展、写入版本、HITL 和执行环境。把 DeerFlow 简化成“只有中间件防线”会漏掉 Gateway 和 run / sandbox 两层。详见 [DeerFlow Permission / Security](../projects/deer-flow/permission-security.md)。

### Q: DeerFlow 的 GuardrailMiddleware 和 ToolErrorHandlingMiddleware 差别是什么？

> **状态**: verified
> **来源**: source-code / discussion

A: GuardrailMiddleware 发生在工具执行前，问“这次工具调用按策略能不能执行”；deny 时不执行工具，直接返回 error ToolMessage。ToolErrorHandlingMiddleware 发生在工具执行过程中，问“工具已经执行但抛异常时如何恢复”；它把异常转换成模型可见的错误反馈。前者是开工前门禁，后者是开工后故障处理。

### Q: Hermes 的 ToolCallGuardrailController 是权限系统吗？

> **状态**: verified
> **来源**: source-code / discussion

A: 严格说不是。它不决定某个工具是否授权，而是观察工具调用后的失败 / 无进展模式，发现 exact failure、same-tool failure 或 idempotent no-progress 时给模型 warning，必要时 hard stop。它更像长期个人助理的“自检提醒器”，防止模型在同一个坑里反复尝试。详见 [Hermes Agent Permission / Security](../projects/hermes-agent/permission-security.md)。

### Q: Hermes 为什么需要 Tool Search bridge scope gate？

> **状态**: verified
> **来源**: source-code / discussion

A: 因为 Hermes 会用 `tool_search` / `tool_describe` / `tool_call` 做 deferred tools。如果 `tool_call` bridge 直接访问全局 registry，受限工具集的 session 或 subagent 就能绕过当前 `valid_tool_names` 调到不该暴露的工具。scope gate 确保 bridge 调用目标仍必须在当前 session 的 scoped catalog 中。

### Q: Hermes 为什么说是“长期个人助理自我保护系统”？

> **状态**: verified
> **来源**: source-code / discussion

A: 因为 Hermes 的安全不只关心一次工具调用是否危险，还关心长期协作状态是否健康：当前 session 能看到哪些工具、deferred tool bridge 是否绕权、危险命令是否审批、编辑是否经过 diff proposal、plugin 是否能阻断、工具失败是否反复、memory / skills 是否可能被污染。它像个人助理的自我保护系统，而不是单个门禁或单个平台安检点。
