# OpenClaw Permission / Security / Guardrail 研读笔记

> **日期**: 2026-07-07 | **状态**: draft | **涉及版本**: `780ca1d25315b34d3118e1db2d8dcafcc16415f3`

## 相关文档

- OpenClaw Tool System：[tool-system.md](tool-system.md)
- OpenClaw Context Management：[context-management.md](context-management.md)
- 横向 Permission / Security：[../../comparison/permission-security.md](../../comparison/permission-security.md)
- 横向 Tool System：[../../comparison/tool-system.md](../../comparison/tool-system.md)
- 横向 QA：[../../comparison/qa.md](../../comparison/qa.md#permission--security--guardrail--权限安全与防护)

## 源码入口

| 模块 | 源码 | 说明 |
|---|---|---|
| before_tool_call runtime | [agent-tools.before-tool-call.ts](../../../submodules/openclaw/src/agents/agent-tools.before-tool-call.ts) | 工具执行前治理主入口：loop detection、trusted policy、approval、plugin hooks、diagnostics。 |
| Tool policy pipeline | [tool-policy-pipeline.ts](../../../submodules/openclaw/src/agents/tool-policy-pipeline.ts) | 多层工具策略 pipeline：profile、provider、global、agent、group、sender、sandbox、subagent、inherited。 |
| Tool policy 数据结构 | [tool-policy.ts](../../../submodules/openclaw/src/agents/tool-policy.ts) | `ToolPolicyLike`、allow / deny、plugin group 展开、allowlist 诊断。 |
| Tool policy 执行 | [agent-tools.policy.ts](../../../submodules/openclaw/src/agents/agent-tools.policy.ts) | `filterToolsByPolicy`、subagent / inherited policy、subagent denylist。 |
| Tool policy 共享规则 | [tool-policy-shared.ts](../../../submodules/openclaw/src/agents/tool-policy-shared.ts) | `normalizeToolName`、tool aliases、tool groups、group 展开。 |
| Plugin approval 类型 | [plugin-approvals.ts](../../../submodules/openclaw/src/infra/plugin-approvals.ts) | `PluginApprovalRequest`、approval decision、timeout、allowed decisions。 |
| Embedded approval broker | [embedded-plugin-approval-broker.ts](../../../submodules/openclaw/src/infra/embedded-plugin-approval-broker.ts) | TUI / embedded 模式下的进程内 pending approval broker。 |

## 核心结论

OpenClaw 的权限治理不能简单理解成“某个命令能不能执行”。它更像一个多端 Agent 产品里的 **工具门禁 + 审批工单系统**：

```text
工具可见性阶段：
  createOpenClawCodingTools
    -> tool policy pipeline
    -> 当前 agent / sender / sandbox / subagent 能看到哪些工具

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

最重要的精髓：

> **OpenClaw 的权限治理是两段式：先用 tool policy pipeline 决定“你有没有这把工具”，再用 before_tool_call approval / hook / diagnostics 决定“这次使用要不要审批、放行或拦截”。**

更口语一点：

> **Claw-Code 像本地门卫；DeerFlow 像流水线质检；OpenClaw 像平台化工具门禁 + 审批工单系统。**

## 和 Claw-Code 的第一层区别

Claw-Code 的安全主问题是：

```text
这个工具调用能不能在我的本机 / workspace 里执行？
```

所以它围绕 `PermissionPolicy / PermissionPrompter` 和 `PermissionEnforcer` 做本地工具调用双闸门。

OpenClaw 的安全主问题更像：

```text
当前 agent 在当前 profile / provider / group / sender / sandbox / subagent 层级下，
应该看到哪些工具？

如果它要调用某个敏感 plugin tool，
审批请求应该送到哪里，由谁决定？
```

这不是谁更高级，而是产品形态不同：OpenClaw 是多端 Agent session runtime，天然要考虑 gateway、channel、plugin、sender、subagent 和 sandbox 等上下文。

## Tool policy pipeline：先决定“工具菜单”

### 基础表达：allow / deny

OpenClaw 的工具策略基础形态是 [tool-policy.ts](../../../submodules/openclaw/src/agents/tool-policy.ts) 里的 `ToolPolicyLike`：

```text
{
  allow?: string[]
  deny?: string[]
}
```

可以理解为：

```text
allow：允许哪些 tool 进入当前工具菜单
 deny：从当前工具菜单里剔除哪些 tool
```

但这些条目不只是裸工具名。OpenClaw 会继续处理：

- 具体 tool name；
- tool alias；
- tool group；
- plugin group；
- plugin id 对应的 tool set。

因此 policy 写的是较高层规则，执行前会归一化并展开成具体 tool set。

### normalizeToolName：把习惯名归一到内部名

[tool-policy-shared.ts](../../../submodules/openclaw/src/agents/tool-policy-shared.ts) 提供 `normalizeToolName` 和 aliases。一个典型例子是：

```text
bash -> exec
```

也就是说，配置层可以出现用户更熟悉的名称，但进入 policy 判断前会被归一到 OpenClaw 内部 canonical tool name。

这个设计很重要：权限配置如果直接做字符串匹配，很容易因为别名、大小写或历史兼容名导致策略失效。

### group expansion：把组展开成具体工具

OpenClaw 支持类似 `group:plugins` 的高层表达。它不是一个真实工具，而是一组 plugin tools 的集合。

相关逻辑在 [tool-policy.ts](../../../submodules/openclaw/src/agents/tool-policy.ts) 和 [tool-policy-shared.ts](../../../submodules/openclaw/src/agents/tool-policy-shared.ts)：

```text
policy 中出现 group / plugin id
  -> expandPolicyWithPluginGroups
  -> 根据当前 plugin registry / plugin tool set 展开
  -> 得到具体 tool names
  -> 再进入 allow / deny 过滤
```

所以 OpenClaw 可以表达：

```text
允许一组 plugin tools
但 deny 其中某几个敏感工具
```

或者：

```text
只允许某个 plugin id 暴露出来的工具
```

这比简单白名单更适合 plugin 生态。

### 多层 pipeline：不只看 agent，也看来源和位置

默认 pipeline 在 [tool-policy-pipeline.ts](../../../submodules/openclaw/src/agents/tool-policy-pipeline.ts) 中装配。它不是单点 policy，而是多层来源叠加：

```text
profile
provider profile
global
provider global
agent
agent provider
group
sender
sandbox
subagent
inherited
```

可以类比为公司门禁：

```text
你是谁？                 -> profile / agent
你用哪个 provider？       -> provider profile / provider global / agent provider
你属于哪个组？             -> group
你从哪个入口发起请求？       -> sender
你在哪个环境里运行？         -> sandbox
你是不是 subagent？         -> subagent
父会话有没有额外限制？       -> inherited
```

因此 OpenClaw 的工具菜单不是静态的：同一个 agent，在不同 sender、sandbox 或 subagent 层级下，可能看到不同工具。

## sender / sandbox / subagent 三个关键维度

### sender：调用来源也是权限上下文

`sender` 层说明 OpenClaw 会考虑请求从哪里来。

同一个 agent，如果来自不同 channel、gateway、client 或 requester，可能应当拥有不同工具菜单。这个点非常符合 OpenClaw 的多端形态：它不是只有本地 CLI 一个入口，而是可能同时服务 TUI、Gateway、远端 channel、plugin 和 subagent。

### sandbox：运行环境影响工具开放

`sandbox` 层说明工具策略还和运行位置有关。

同一个工具在某些 sandbox / runtime 下可以开放，在另一些环境下需要禁用或收紧。这把“工具本身是否危险”和“工具在哪里运行”分开了：

```text
工具风险 = tool capability + 当前执行环境
```

这比单纯按工具名判断更贴近真实 Agent 产品。

### subagent：默认压低控制面能力

Subagent 是 OpenClaw 明确防护的一层。[agent-tools.policy.ts](../../../submodules/openclaw/src/agents/agent-tools.policy.ts) 中有 subagent denylist，例如：

```text
SUBAGENT_TOOL_DENY_ALWAYS
SUBAGENT_TOOL_DENY_LEAF
```

典型禁止项包括：

```text
gateway
agents_list
session_status
cron
sessions_send
subagents
sessions_list
sessions_history
sessions_spawn
```

这些工具大多属于 gateway、session、cron、spawn 等控制面能力。OpenClaw 不希望子 agent 默认拿到这些高层编排权限。

精髓：

> **OpenClaw 对 subagent 的限制不是临时判断，而是内建在 tool policy 层：子 agent 默认不能随便管理 gateway、session、cron、spawn 等控制面工具。**

这是在防“代理递归失控”：子 agent 如果能随意 spawn、发 session、管 gateway，就可能从执行助手变成控制面操作者。

## before_tool_call runtime：再判断“这次使用”

工具菜单只是第一关。模型真正发出某次 `toolCall` 后，还要进入 [agent-tools.before-tool-call.ts](../../../submodules/openclaw/src/agents/agent-tools.before-tool-call.ts) 的 before-tool-call runtime。

可以简化为：

```text
model toolCall
  -> resolve current AgentTool
  -> beforeToolCall / runBeforeToolCallHook
     -> loop detection
     -> skill workshop / trusted policies
     -> approval check
     -> plugin before_tool_call hooks
     -> diagnostics / event feedback
  -> allow / deny / modified args / diagnostic result
```

这一层处理的是“某次调用实例”，而不是“工具是否出现在菜单里”。

### loop detection：防止重复调用失控

OpenClaw 在 before-tool-call 阶段会做 loop detection。它关注的是模型是否对同类工具、同类参数或无进展结果反复尝试。

这类机制不完全等同于权限，但属于 guardrail：它保护 session 不陷入重复工具循环，也保护用户和系统资源。

### trusted policy / skill approval：部分工具可被信任策略放行

before-tool-call runtime 里还有 trusted policy / skill workshop approval 相关路径。它说明 OpenClaw 的放行逻辑不只是“用户每次点按钮”，也可以根据当前工具、技能、策略和来源决定某些调用是否已被信任。

### plugin hooks：插件生态里的执行前拦截

OpenClaw 的 plugin hook 更接近平台内建的扩展点：plugin 可以在 tool call 前参与判断、修改或拒绝。

它和 Claw-Code 的外部 command hook 不同：

| 维度 | Claw-Code hook | OpenClaw plugin before_tool_call |
|---|---|---|
| 形态 | 外部 command hook 为主 | plugin runtime / product runtime 内部生命周期 |
| 位置 | 本地 CLI 工具调用前后 | AgentTool 执行前 runtime 中 |
| 典型目的 | 本地安全脚本、审计、企业规则 | plugin 生态、approval、diagnostics、多端事件治理 |
| 和 UI / Gateway 关系 | 较弱，主要回到 CLI | 更强，能进入 event / approval / diagnostics 链路 |

所以 OpenClaw 也有 hook-like 能力，但它更像产品 runtime 的一站，不是单纯本地外挂脚本。

## Approval：plugin tool 调用工单系统

OpenClaw 的 approval 不只是 confirm 弹窗，而是一个 plugin tool 调用审批工单系统。

核心入口是 [agent-tools.before-tool-call.ts](../../../submodules/openclaw/src/agents/agent-tools.before-tool-call.ts) 中的 `requestPluginToolApproval(...)`，审批数据结构见 [plugin-approvals.ts](../../../submodules/openclaw/src/infra/plugin-approvals.ts)。

### 审批决策

`PluginApprovalRequest` 支持的核心决策可以概括为：

```text
allow-once
allow-always
deny
```

还有 timeout 和 allowed decisions 等字段。默认 timeout 约 120 秒，最大可到 600 秒；timeout 后按 `timeoutBehavior` 决定 allow 或 deny，默认更偏 deny。

这意味着 OpenClaw 把审批视作有生命周期的 runtime decision，而不是无限等待。

### Embedded TUI 路径：本地审批柜台

在 TUI / embedded 模式下，OpenClaw 使用 [embedded-plugin-approval-broker.ts](../../../submodules/openclaw/src/infra/embedded-plugin-approval-broker.ts) 的 `EmbeddedPluginApprovalBroker`。

流程可以写成：

```text
agent 要调用 plugin tool
  -> before_tool_call 发现需要 approval
  -> requestPluginToolApproval 创建 PendingApproval
  -> EmbeddedPluginApprovalBroker 登记 pending request
  -> 发出 plugin.approval.requested 事件
  -> TUI / CLI 展示给用户
  -> 用户选择 allow-once / allow-always / deny
  -> broker.resolve(...)
  -> 发出 plugin.approval.resolved / removed
  -> before_tool_call 得到决策
```

通俗比喻：

> **Embedded broker 就像本地柜台叫号机。Agent 把审批单放到柜台，TUI 看到后叫用户处理；用户按下同意或拒绝，柜台把结果递回给 Agent。**

### Gateway 路径：远端 / 多端审批服务台

如果不走 embedded broker，OpenClaw 可以通过 Gateway 发送审批请求，典型 gateway tool 包括：

```text
plugin.approval.request
plugin.approval.waitDecision
```

流程可以写成：

```text
agent 要调用 plugin tool
  -> requestPluginToolApproval 构造审批请求
  -> callGatewayTool("plugin.approval.request", ...)
  -> Gateway 把审批请求路由到 reviewer / device / UI
  -> 如需等待，再 callGatewayTool("plugin.approval.waitDecision", ...)
  -> Gateway 返回 allow-once / allow-always / deny / timeout
  -> before_tool_call 根据结果放行或拒绝
```

这一路会携带更丰富的 routing context，例如当前 session、source channel、source target、reviewer device 等。

通俗比喻：

> **Gateway approval 就像把审批单递到公司服务台。Agent 不直接找用户，而是把工单交给 Gateway；Gateway 再决定发到哪个端、哪个 reviewer、哪个 device。**

这就是 OpenClaw 相比本地 CLI 更平台化的地方：审批人不一定坐在当前终端前，审批请求可能需要跨设备、跨 channel、跨 UI 送达。

## diagnostics：治理结果也进入产品事件流

OpenClaw 的 before-tool-call runtime 还会产生 diagnostics / event feedback。这个点和它的 Tool System、Context Management 相关：

```text
治理判断
  -> event / diagnostic
  -> UI 展示 / session persistence / 后续模型上下文
```

所以 OpenClaw 的权限系统不仅是安全判断，也服务产品可观测性。

## 和 DeerFlow middleware 的区别

OpenClaw 的 before-tool-call runtime 看起来也像 middleware，但它的架构位置和 DeerFlow 不一样。

DeerFlow middleware 是 LangGraph agent runtime 的内建工位，直接参与 `ThreadState`、before_model、wrap_model_call、after_agent、tool error handling、clarification、summarization 等生命周期。

OpenClaw 的治理更集中在：

```text
tool visibility policy pipeline
+ AgentTool before_tool_call runtime
+ plugin approval / gateway / diagnostics
```

可以概括为：

| 项目 | 权限 / guardrail 组织方式 | 比喻 |
|---|---|---|
| Claw-Code | 本地 ToolUse 前后的 permission + enforcer + hooks | 本地门卫 / 双闸门 |
| DeerFlow | LangGraph middleware pipeline + run lifecycle | 流水线质检 / 中间件防线 |
| OpenClaw | 工具菜单 policy pipeline + plugin approval 工单 + before_tool_call runtime | 平台化工具门禁 + 审批工单系统 |

## 当前阶段判断

OpenClaw 的权限治理最值得记住三句话：

1. **tool policy pipeline 管“看得见”：当前 agent / sender / sandbox / subagent 能看到哪些工具。**
2. **before_tool_call runtime 管“这次怎么用”：loop detection、trusted policy、approval、plugin hook、diagnostics 决定单次调用是否放行。**
3. **approval 是工单系统：本地 TUI 走 embedded broker，多端 / 远端场景走 Gateway approval routing。**

这使 OpenClaw 的安全模型比本地 CLI 更平台化，也比单纯 middleware 更贴近多端 Agent 产品的工具治理需求。

## QA / 讨论记录

### Q: OpenClaw 的权限治理和 Claw-Code 的两道权限门有什么本质不同？

> **状态**: verified
> **来源**: source-code / discussion

A: Claw-Code 的重点是本地工具调用能不能在用户机器 / workspace 里执行，因此有 `PermissionPolicy / PermissionPrompter` 和 `PermissionEnforcer` 两道门。OpenClaw 的重点是当前 agent 在当前 profile、provider、group、sender、sandbox、subagent 和 inherited 限制下能看到什么工具，以及某次 plugin tool 调用是否需要通过 approval / hook / diagnostics 放行。可以概括为：Claw-Code 是本地工具双闸门，OpenClaw 是平台化工具门禁 + 审批工单系统。

### Q: OpenClaw 的 approval broker 是怎么把审批请求送到用户的？

> **状态**: verified
> **来源**: source-code / discussion

A: 有两条路径。TUI / embedded 模式下，`EmbeddedPluginApprovalBroker` 在本进程内登记 pending approval，并通过 `plugin.approval.requested/resolved/removed` 事件让 UI 展示和回填决策；多端 / Gateway 模式下，`requestPluginToolApproval(...)` 调用 `plugin.approval.request`，必要时再调用 `plugin.approval.waitDecision`，由 Gateway 根据 session、channel、reviewer device 等上下文路由审批请求。前者像本地审批柜台，后者像平台审批服务台。

### Q: OpenClaw 的 tool policy pipeline 具体管什么？

> **状态**: verified
> **来源**: source-code / discussion

A: 它管工具可见性，也就是当前运行上下文下模型能看到哪些 tools。策略基础形态是 `{ allow?: string[]; deny?: string[] }`，但会经过 tool name normalization、alias 处理、tool group / plugin group 展开，再按 profile、provider、global、agent、group、sender、sandbox、subagent、inherited 等层叠加。特别是 subagent 层有内建 denylist，限制 gateway、session、cron、spawn 等控制面工具，防止子 agent 默认拿到过高权限。
