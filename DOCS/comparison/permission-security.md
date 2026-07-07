# Permission / Security / Guardrail 横向笔记：从 Claw-Code 双闸门到 DeerFlow 中间件防线

> **日期**: 2026-07-07 | **状态**: draft | **当前覆盖**: Claw-Code / DeerFlow（后续扩展 OpenClaw / OpenHands / Hermes Agent）

## 相关文档

- Claw-Code 权限安全：[../projects/claw-code/permission-security.md](../projects/claw-code/permission-security.md)
- Claw-Code Tool System：[../projects/claw-code/tool-system.md](../projects/claw-code/tool-system.md)
- DeerFlow Tool System：[../projects/deer-flow/tool-system.md](../projects/deer-flow/tool-system.md)
- DeerFlow Context Management：[../projects/deer-flow/context-management.md](../projects/deer-flow/context-management.md)
- 横向 Tool System：[tool-system.md](tool-system.md)
- 横向 Context Management：[context-management.md](context-management.md)
- 横向 QA：[qa.md](qa.md#permission--security--guardrail--权限安全与防护)

## 1. 当前阶段核心结论

本专题刚开始，当前先记录 Claw-Code 权限安全与 DeerFlow middleware 的对比。后续会继续补 OpenClaw、OpenHands、Hermes Agent。

先给一句总判断：

> **Claw-Code 的权限安全像本地 CLI 工具调用双闸门；DeerFlow 的安全治理像 LangGraph 工作流里的中间件防线。**

最值得标记的横向精髓：

> **Claw-Code hooks 是工具调用关卡上的“外挂监工”；DeerFlow middleware 是 agent runtime 流水线里的“内建工位”。**

这句话很重要，因为 hook 和 middleware 都是横切逻辑，但不要简单等同。

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
sandbox、hook、middleware、policy 如何配合？
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

## 4. DeerFlow：中间件防线与工作流治理

DeerFlow 的安全治理不集中在一个 `PermissionPolicy` 文件里。它更偏 LangGraph / middleware 化：

```text
ThreadState / messages
  -> middlewares
     -> dynamic context
     -> summarization
     -> durable context
     -> memory
     -> tool error handling
     -> loop detection
     -> clarification / HITL
     -> provider-facing message normalization
```

在已有 DeerFlow 笔记中，middleware 主要见：

- [agent.py](../../submodules/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/agent.py) 中的 agent / middleware 装配；
- [tool-system.md](../projects/deer-flow/tool-system.md) 中对 ToolCallRequest / ToolMessage / middleware 化工具治理的讨论；
- [context-management.md](../projects/deer-flow/context-management.md) 中对 DynamicContext、Summarization、DurableContext、Memory、SystemMessageCoalescing 的分析。

DeerFlow 更关注：

```text
这个 run 是否继续？
是否需要 clarification / HITL？
工具错误怎么让模型恢复？
上下文是否过长？
是否陷入重复工具循环？
哪些 state channel 应该投影给模型？
```

所以它的安全 / guardrail 更像“中间件防线”，而不是本地 CLI 的“文件 / shell 权限闸门”。

## 5. Hooks vs Middleware：外挂监工 vs 内建工位

### 5.1 共同点：都是横切逻辑

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

### 5.2 最关键区别

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

### 5.3 横向对比表

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

## 6. 从上下文管理角度看差异

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

所以：

> **Claw-Code hook 是上下文的旁路影响者；DeerFlow middleware 是上下文投影的主执行者。**

## 7. 从权限安全角度看差异

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
这个 run 是否应该继续？
模型是否需要澄清？
工具错误如何恢复？
是否陷入 loop？
哪些状态应进入模型？
```

所以它需要：

```text
middleware chain
LangGraph state / checkpoint
ToolMessage / Command
loop detection
clarification / HITL
summary / durable context / memory projection
```

可以概括：

```text
Claw-Code：权限安全更像本地工具闸门。
DeerFlow：安全治理更像工作流中间件防线。
```

## 8. 从扩展方式看差异

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

## 9. 当前阶段的横向判断

Claw-Code 和 DeerFlow 都有“防线”，但防线的形态不同：

| 项目 | 防线形态 | 设计重心 |
|---|---|---|
| Claw-Code | 本地工具调用双闸门 + hook 监工 | 防止模型在本机执行越权 / 危险工具调用 |
| DeerFlow | middleware pipeline + state / run lifecycle guardrail | 防止长任务 workflow 上下文、工具、状态、run 流程失控 |

这不是谁更高级，而是场景不同：

```text
本地 CLI coding agent：
  最危险的是模型在你的机器上乱跑命令、乱改文件。

长任务 workflow agent：
  最危险的是 run 状态失控、上下文污染、工具错误无法恢复、无限循环、HITL 边界不清。
```

## 10. 后续扩展方向

本专题后续应继续补：

- **OpenClaw**：`before_tool_call` policy runtime、approval、diagnostics、loop detection，与 Claw-Code hooks 的关系；
- **OpenHands**：`ConfirmationPolicy`、`SecurityAnalyzer`、ActionEvent risk、sandbox / workspace 边界；
- **Hermes Agent**：tool guardrail、interrupt / steer、memory pollution 防护、skill / memory 写入安全；
- **Sandbox Runtime**：权限系统和执行环境隔离的边界；
- **HITL Patterns**：ask / approval / clarification / interrupt / steer 的统一比较。

## 11. QA / 讨论记录

### Q: Claw-Code hooks 和 DeerFlow middleware 是一回事吗？

> **状态**: verified  
> **来源**: source-code / discussion

A: 不是。它们都属于横切治理机制，但定位不同。Claw-Code hooks 更像本地 CLI 工具调用前后的外挂监工，主要围绕 `PreToolUse` / `PostToolUse` / `PostToolUseFailure` 拦截、审批、改写和审计工具调用；DeerFlow middleware 更像 LangGraph agent runtime 的内建工位，直接参与 `ThreadState`、上下文投影、模型调用、压缩、memory、HITL 和错误治理。可以概括为：**hook 是外挂监工，middleware 是内建工位**。

### Q: 为什么说 Claw-Code 是双闸门，而 DeerFlow 是中间件防线？

> **状态**: draft  
> **来源**: discussion / source-code

A: Claw-Code 面向本地 CLI，工具调用直接触达用户机器和 workspace，因此安全重点是工具调用能否执行：第一道门由 `PermissionPolicy / PermissionPrompter` 按模式、工具、规则和用户确认授权；第二道门由 `PermissionEnforcer / dynamic classification` 按具体命令和路径复查。DeerFlow 面向 LangGraph 长任务 workflow，安全治理更多分布在 middleware pipeline 中，包括上下文压缩、状态投影、tool error recovery、loop detection、clarification / HITL 和 memory 更新等，因此更像多道中间件防线。
