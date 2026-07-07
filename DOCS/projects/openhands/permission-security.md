# OpenHands Permission / Security / Guardrail 研读笔记

> **日期**: 2026-07-07 | **状态**: draft | **涉及版本**: `openhands` `ef3323afd9676b5cf44ede15683fc56a570ea0d8` / `software-agent-sdk` `0737c05e5d5218cdb15cadf1bc03d3e4f108a60b`

## 相关文档

- OpenHands Agent Loop：[agent-loop.md](agent-loop.md)
- OpenHands Tool System：[tool-system.md](tool-system.md)
- OpenHands Context Management：[context-management.md](context-management.md)
- OpenHands Sandbox / Workspace：[sandbox-workspace.md](sandbox-workspace.md)
- 横向 Permission / Security：[../../comparison/permission-security.md](../../comparison/permission-security.md)
- 横向 Tool System：[../../comparison/tool-system.md](../../comparison/tool-system.md)
- 横向 QA：[../../comparison/qa.md](../../comparison/qa.md#permission--security--guardrail--权限安全与防护)

## 源码入口

| 模块 | 源码 | 说明 |
|---|---|---|
| Confirmation Policy | [confirmation_policy.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/security/confirmation_policy.py) | `AlwaysConfirm` / `NeverConfirm` / `ConfirmRisky`，按 `SecurityRisk` 决定是否暂停确认。 |
| Security Risk | [risk.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/security/risk.py) | `UNKNOWN` / `LOW` / `MEDIUM` / `HIGH` 风险等级与比较规则。 |
| Security Analyzer Base | [analyzer.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/security/analyzer.py) | `SecurityAnalyzerBase.security_risk(ActionEvent)` 抽象接口与 pending actions 批量分析。 |
| LLM Analyzer | [llm_analyzer.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/security/llm_analyzer.py) | 读取模型在 tool call 中预测的 `security_risk`。 |
| Pattern Analyzer | [pattern.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/security/defense_in_depth/pattern.py) | 本地正则特征库，扫描危险命令、download-and-run、prompt injection。 |
| Policy Rails | [policy_rails.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/security/defense_in_depth/policy_rails.py) | 本地结构规则，识别 `fetch-to-exec`、raw disk、critical `rm -rf` 等组合威胁。 |
| GraySwan Analyzer | [grayswan/analyzer.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/security/grayswan/analyzer.py) | 调用 GraySwan Cygnal API，用近期历史 + 当前 action 做外部安全评估。 |
| Ensemble Analyzer | [ensemble.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/security/ensemble.py) | 多 analyzer 聚合，默认取最高 concrete risk，异常时 fail-closed 为 HIGH。 |
| ActionEvent | [action.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/event/llm_convertible/action.py) | 工具调用进入平台事件账本前的 action 承载物，包含 `security_risk`、summary、tool_call。 |
| Observation / Reject | [observation.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/event/llm_convertible/observation.py) | `ObservationEvent` / `UserRejectObservation` 把执行结果或拒绝结果回写给模型。 |
| Agent action flow | [agent.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/agent/agent.py) | tool call -> ActionEvent、风险提取、confirmation 判断、action 执行。 |
| Conversation state | [state.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/conversation/state.py) | `WAITING_FOR_CONFIRMATION`、`confirmation_policy`、`security_analyzer`、workspace 等 conversation state。 |
| SDK settings | [model.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/settings/model.py) | `ConversationSettings` 把 `confirmation_mode` / `security_analyzer` 转成 SDK policy / analyzer。 |
| Control-plane settings | [settings_models.py](../../../submodules/openhands/openhands/app_server/settings/settings_models.py) | OpenHands App Server 持久化 `conversation_settings`。 |
| App conversation service | [app_conversation_service_base.py](../../../submodules/openhands/openhands/app_server/app_conversation/app_conversation_service_base.py) | 控制面把 analyzer 字符串转对象，并通过 Agent Server API 下发。 |
| Agent Server router | [conversation_router.py](../../../submodules/software-agent-sdk/openhands-agent-server/openhands/agent_server/conversation_router.py) | `/confirmation_policy`、`/security_analyzer` API 更新执行面 conversation。 |

## 核心结论

OpenHands 的权限 / 安全主线可以概括为：

> **OpenHands 是“ActionEvent 风险评估 + ConfirmationPolicy 暂停闸门 + Sandbox / Workspace 硬边界 + EventLog 审计反馈”。**

它不像 Claw-Code 那样以本地工具调用双闸门为中心，也不像 OpenClaw 那样先做工具菜单门禁再走 plugin approval 工单。OpenHands 的执行面先把模型工具调用转成平台事件层的 `ActionEvent`，然后围绕这个 action 做风险标注、确认暂停、执行或拒绝反馈。

简化主线：

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

精髓标记：

> **OpenHands 的安全治理中心不是工具菜单，而是 ActionEvent：模型动作先登记成事件，再由 SecurityAnalyzer 评估风险，由 ConfirmationPolicy 决定是否进入 `WAITING_FOR_CONFIRMATION`，最后用 ObservationEvent / UserRejectObservation 把执行或拒绝反馈写回事件账本；sandbox / workspace 则提供动作执行的硬边界。**

更口语一点：

> **OpenHands 像远程开发园区：Agent 每个动作都要登记成工单；危险工单过安检和确认；拒绝也会记到账本；真正干活只能在分配的 workspace / sandbox 工位里干。**

## Conversation 状态：确认是正式 lifecycle 状态

`WAITING_FOR_CONFIRMATION` 定义在 [state.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/conversation/state.py) 的 `ConversationExecutionStatus` 中。它和 `IDLE`、`RUNNING`、`PAUSED`、`FINISHED`、`ERROR`、`STUCK` 一样，是 conversation lifecycle 的正式状态。

这说明 OpenHands 的确认机制不是 UI 临时弹窗，而是执行状态机中的暂停点：

```text
ActionEvent 生成
  -> policy 判断需要确认
  -> state.execution_status = WAITING_FOR_CONFIRMATION
  -> action 暂不执行
  -> 用户确认后继续
  -> 用户拒绝后写入 UserRejectObservation
```

这个设计特别适合平台化 SWE Agent：前端、Agent Server、事件流和状态查询都能观察到“当前 run 正在等待确认”。

## ConfirmationPolicy：按风险等级决定是否确认

[confirmation_policy.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/security/confirmation_policy.py) 定义了三种基础策略：

| Policy | 含义 |
|---|---|
| `AlwaysConfirm` | 所有 action 都需要确认。 |
| `NeverConfirm` | 所有 action 都不确认。 |
| `ConfirmRisky` | 达到风险阈值才确认，默认 `threshold = HIGH`，并且默认 `confirm_unknown = True`。 |

核心接口是：

```text
should_confirm(risk: SecurityRisk = UNKNOWN) -> bool
```

风险等级在 [risk.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/security/risk.py) 中定义：

```text
UNKNOWN
LOW
MEDIUM
HIGH
```

`ConfirmRisky` 的关键点是：

```text
HIGH 默认需要确认
UNKNOWN 默认也需要确认
```

所以 OpenHands 的确认闸门不是简单按工具名判断，而是按 action 风险等级判断。风险来源则由 SecurityAnalyzer 提供。

## ActionEvent：权限治理的中心承载物

[action.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/event/llm_convertible/action.py) 中的 `ActionEvent` 承载一次模型动作。它包含：

```text
action
tool_name
tool_call_id
tool_call
security_risk
summary
thought / reasoning_content / thinking_blocks
critic_result
```

这说明 OpenHands 的权限治理发生在平台事件层，而不是只停留在 provider tool-call 协议层：

```text
MessageToolCall
  -> ActionEvent
  -> risk / confirmation / execution
  -> ObservationEvent
```

`security_risk` 字段保存模型或 analyzer 产生的风险标签，`summary` 提供可解释动作摘要，便于 UI 展示和审计。

## SecurityAnalyzer：给 ActionEvent 打风险标签

[analyzer.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/security/analyzer.py) 定义抽象接口：

```text
security_risk(action: ActionEvent) -> SecurityRisk
```

也就是说 analyzer 的输入不是裸字符串，而是完整 `ActionEvent`。它可以看 tool name、arguments、summary、thought、reasoning、历史上下文等不同信息。

`analyze_pending_actions(...)` 有一个重要安全细节：如果 analyzer 抛异常，默认把风险按 `HIGH` 处理。这是 fail-closed：

```text
安全分析器坏了
  -> 不能静默放行
  -> 默认高风险
```

## LLM 自评风险：可用，但不会无条件信任

[agent/utils.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/agent/utils.py) 中的 LLM 调用会给工具 schema 增加 `security_risk` 参数，让模型可以在 tool call 里预测风险。

但 [agent.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/agent/agent.py) 的 `_extract_security_risk(...)` 有关键约束：

```text
如果没有配置 security_analyzer：
  忽略 LLM 提供的 security_risk
  返回 UNKNOWN
```

只有显式配置了 analyzer，LLM 自评风险才会进入 ActionEvent。否则模型不能靠自报 `LOW` 来绕过确认逻辑。

精髓：

> **OpenHands 可以让 LLM 参与风险标注，但不会无条件信任 LLM；必须显式启用 SecurityAnalyzer，风险字段才进入确认策略。**

## PatternSecurityAnalyzer：本地安检特征库

[pattern.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/security/defense_in_depth/pattern.py) 是本地 deterministic pattern analyzer。

它分两类扫描对象：

```text
Executable corpus：
  tool_name + tool_call arguments
  扫真正会执行的命令 / 参数

All-field corpus：
  executable + thought / reasoning / summary
  扫 prompt injection / social engineering 文本
```

这种分离很重要：如果模型只是“想到了 `rm -rf /` 很危险”，但实际 action 是 `ls /tmp`，不应被误判成真的要删系统。

典型 HIGH pattern：

```text
rm -rf variants
sudo rm
mkfs.*
dd ... of=/dev/
eval(...)
exec(...)
os.system(...)
subprocess.run / Popen / check_output
curl ... | sh
wget ... | sh
```

典型 MEDIUM pattern：

```text
curl http(s)://...
wget http(s)://...
```

Injection pattern 会扫全部字段，例如：

```text
ignore / disregard / override previous instructions
you are now ... mode
pretend you are different ...
```

可以记成：

> **PatternSecurityAnalyzer 是本地安检特征库：真正会执行的命令按可执行字段扫，prompt injection 按全部文本扫。**

## PolicyRailSecurityAnalyzer：结构规则安检

[policy_rails.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/security/defense_in_depth/policy_rails.py) 抓的是“组合起来才危险”的结构规则。

当前 v1 rails：

```text
fetch-to-exec
raw-disk-op
catastrophic-delete
```

典型逻辑：

```text
curl / wget + | sh / bash / python / perl / ruby
  -> HIGH

dd ... of=/dev/ 或 mkfs.*
  -> HIGH

rm -rf variants + critical path(/, ~, /etc, /usr, /var, /home, /boot)
  -> HIGH
```

它强调 per-segment evaluation：危险组合必须出现在同一个 executable segment 里，避免 thought 和 action 跨字段拼接导致误报。

可以记成：

> **PolicyRailSecurityAnalyzer 是结构规则安检：它抓的不是单个危险词，而是危险组合，并且要求组合出现在同一个可执行片段里。**

## GraySwanAnalyzer：外部安全审查服务

[grayswan/analyzer.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/security/grayswan/analyzer.py) 会把近期 conversation history 和当前 `ActionEvent` 转成 OpenAI message format，发给 GraySwan Cygnal API。

默认配置包括：

```text
history_limit = 20
max_message_chars = 30000
timeout = 30s
low_threshold = 0.3
medium_threshold = 0.7
```

API 返回 violation score 后映射为：

```text
score <= 0.3  -> LOW
score <= 0.7  -> MEDIUM
score > 0.7   -> HIGH
```

如果 API 返回 `ipi = true`，会直接升级为 `HIGH`，用于 indirect prompt injection 等场景。

失败时，例如没有 API key、timeout、API 错误、返回格式不对，GraySwanAnalyzer 返回 `UNKNOWN`。如果它被放进 `EnsembleSecurityAnalyzer`，UNKNOWN 如何处理由 ensemble 决定。

可以记成：

> **GraySwanAnalyzer 是外部安检服务：它看近期上下文 + 当前动作，给 violation score；本地 analyzer 更像门口安检仪，GraySwan 更像把工单送到专门安全审查服务。**

## EnsembleSecurityAnalyzer：多路评估取最坏情况

[ensemble.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/security/ensemble.py) 把多个 analyzer 组合起来：

```text
多个 analyzer 分别返回风险
  -> 默认过滤 UNKNOWN
  -> 取最高 concrete risk
  -> 如果全部 UNKNOWN，则 UNKNOWN
  -> 如果 analyzer 抛异常，则按 HIGH
```

也可以打开 `propagate_unknown=True`，让任一 UNKNOWN 都使整体 UNKNOWN，适合更严格环境。

这说明 OpenHands 的风险评估不是单一路径，而是可组合的多层 action analyzer：模型可自评，规则可本地扫，rail 可抓组合威胁，外部服务可做上下文安全审查，最后 ensemble 取最坏风险。

## Agent 执行阶段：从 tool call 到 ActionEvent，再到确认

[agent.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/agent/agent.py) 的 action 创建流程可以简化为：

```text
tool_call
  -> parse_tool_call_arguments
  -> normalize_tool_call
  -> 找 ToolDefinition
  -> fix_malformed_tool_arguments
  -> _extract_security_risk(...)
  -> _extract_summary(...)
  -> tool.action_from_arguments(...)
  -> ActionEvent(...)
  -> on_event(action_event)
```

确认判断逻辑可以简化为：

```text
如果只有 FinishAction / ThinkAction：
  不确认

如果没有 action：
  不确认

如果有 security_analyzer：
  analyze_pending_actions(action_events)
else：
  risks = UNKNOWN

如果任一 risk 触发 confirmation_policy.should_confirm(risk)：
  state.execution_status = WAITING_FOR_CONFIRMATION
  暂停执行
```

这里是批量判断：同一轮模型可能产生多个 pending actions，只要其中一个 action 需要确认，conversation 就进入等待确认状态。

## 用户拒绝：用 UserRejectObservation 回写给模型

[local_conversation.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/conversation/impl/local_conversation.py) 的 `reject_pending_actions(...)` 会为 pending action 写入 `UserRejectObservation`。

[observation.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/event/llm_convertible/observation.py) 中 `UserRejectObservation.to_llm_message()` 会生成 tool role message：

```text
Action rejected: <reason>
```

并保留 `tool_name` 和 `tool_call_id`。

所以 OpenHands 的拒绝不是静默丢弃，而是进入事件账本，并作为 tool result 式反馈回到下一轮模型上下文。

精髓：

> **OpenHands 的拒绝也是 observation：模型会看到动作被拒绝，并可以换策略。**

## 控制面如何接入执行面安全能力

OpenHands 需要同时看控制面仓库 [openhands/](../../../submodules/openhands/) 和执行面仓库 [software-agent-sdk/](../../../submodules/software-agent-sdk/)。权限治理配置从控制面进入执行面。

### 用户设置：conversation_settings

[settings_models.py](../../../submodules/openhands/openhands/app_server/settings/settings_models.py) 说明：

```text
Agent settings live in agent_settings.
Conversation settings (max_iterations, confirmation_mode, security_analyzer)
live in conversation_settings.
```

执行面 [model.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/settings/model.py) 的 `ConversationSettings` 包含：

```text
confirmation_mode: bool = False
security_analyzer: "llm" | None = "llm"
max_iterations: int = 500
workspace
plugins
hook_config
```

### settings -> SDK 对象

`ConversationSettings` 会把配置转成真正的 SDK 对象：

```text
if not confirmation_mode:
  NeverConfirm()

if confirmation_mode and security_analyzer == "llm":
  ConfirmRisky()

else:
  AlwaysConfirm()
```

Security analyzer 构建逻辑：

```text
security_analyzer == "llm" -> LLMSecurityAnalyzer()
none / empty -> None
```

所以：

```text
confirmation_mode = false
  -> 完全不确认

confirmation_mode = true + security_analyzer = llm
  -> 按风险确认

confirmation_mode = true + 没有 analyzer / 非 llm
  -> 所有动作都确认
```

这体现了保守策略：用户打开确认模式但没有可用 analyzer 时，OpenHands 倾向于 `AlwaysConfirm`。

### StartConversationRequest 接收 policy / analyzer / workspace

[request.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/conversation/request.py) 的 start request 接收：

```text
workspace
confirmation_policy
security_analyzer
max_iterations
stuck_detection
secrets
plugins
hook_config
```

其中 `workspace` 是 agent operations 和 tool execution 的工作目录，`confirmation_policy` / `security_analyzer` 是执行面 action risk / confirmation 的核心配置。

### App Server 下发到 Agent Server

[app_conversation_service_base.py](../../../submodules/openhands/openhands/app_server/app_conversation/app_conversation_service_base.py) 也有同样的转换逻辑：

```text
"llm" -> LLMSecurityAnalyzer()
"none" / None -> None
unknown -> warning + None
```

并且可以通过 Agent Server API 下发 analyzer：

```text
POST {agent_server_url}/api/conversations/{conversation_id}/security_analyzer
headers: X-Session-API-Key: <session_api_key>
body: {"security_analyzer": analyzer.model_dump()}
```

Agent Server API 在 [conversation_router.py](../../../submodules/software-agent-sdk/openhands-agent-server/openhands/agent_server/conversation_router.py) 中提供：

```text
POST /{conversation_id}/confirmation_policy
POST /{conversation_id}/security_analyzer
```

这说明 OpenHands 控制面不是直接执行每个 action，而是通过 conversation settings、sandbox、agent_server_url 和 session API key，把安全配置送到执行面。

## workspace / sandbox：动作执行硬边界

OpenHands 的 confirmation / analyzer 是动作前软闸门；workspace / sandbox 是执行环境硬边界。

可以拆成：

```text
SecurityAnalyzer / ConfirmationPolicy：
  这次 action 要不要停下来让用户看？

Workspace / Sandbox：
  即使 action 被执行，它在哪里执行、能看到哪些文件 / secrets / runtime？
```

这两层不能互相替代：

- 用户可以关闭 confirmation mode，所以不能只靠确认；
- sandbox 里也可能破坏 workspace 或泄露配置，所以不能只靠隔离；
- 安全分析、确认、sandbox、事件审计需要共同构成防线。

## 和 OpenClaw 的区别

OpenClaw 和 OpenHands 都是平台化方向，但权限治理中心不同：

```text
OpenClaw：
  policy pipeline 决定工具菜单；
  before_tool_call / plugin approval 决定敏感 plugin tool 是否审批；
  重点是“谁能拿到什么工具，审批请求送到哪里”。

OpenHands：
  tool call 先变成 ActionEvent；
  SecurityAnalyzer 评估 action 风险；
  ConfirmationPolicy 决定是否暂停确认；
  sandbox / workspace 提供执行硬边界；
  重点是“这个具体 action 有多危险，是否暂停确认，即使执行也在哪里执行”。
```

一句话：

> **OpenClaw 像“平台工具门禁 + 审批工单”；OpenHands 像“远程开发园区安检 + 工位隔离”。**

## QA / 讨论记录

### Q: OpenHands 的权限治理中心是什么？

> **状态**: verified
> **来源**: source-code / discussion

A: OpenHands 的权限治理中心是 `ActionEvent`，不是工具菜单。模型 tool call 会先被解析、规范化、校验并转换成 `ActionEvent`；`SecurityAnalyzer` 对 ActionEvent 评估 `SecurityRisk`；`ConfirmationPolicy` 根据风险决定是否把 conversation 置为 `WAITING_FOR_CONFIRMATION`；执行或拒绝结果再通过 `ObservationEvent` / `UserRejectObservation` 回写给模型。workspace / sandbox 则提供动作执行硬边界。

### Q: OpenHands 会无条件相信模型自评的 security_risk 吗？

> **状态**: verified
> **来源**: source-code / discussion

A: 不会。OpenHands 会在工具 schema 中暴露 `security_risk` 参数，让模型可以预测风险；但 `_extract_security_risk(...)` 只有在显式配置了 `security_analyzer` 时才采纳这个字段。没有 analyzer 时，模型提供的 `security_risk` 会被忽略并返回 `UNKNOWN`。这避免模型通过自报 `LOW` 绕过确认策略。

### Q: OpenHands 的用户拒绝会反馈给模型吗？

> **状态**: verified
> **来源**: source-code / discussion

A: 会。`reject_pending_actions(...)` 会为每个 pending action 写入 `UserRejectObservation`，它转成 LLM message 时是 tool role，内容为 `Action rejected: <reason>`，并保留对应 `tool_name` 和 `tool_call_id`。所以拒绝不是静默丢弃，而是进入 EventLog，并作为观察结果反馈给下一轮模型。
