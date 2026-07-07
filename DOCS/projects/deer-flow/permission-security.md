# DeerFlow Permission / Security / Guardrail 研读笔记

> **日期**: 2026-07-07 | **状态**: draft | **涉及版本**: `0808738c5876b04b4aa8e9aca7379a0a62b4232d`

## 相关文档

- DeerFlow Agent Loop：[agent-loop.md](agent-loop.md)
- DeerFlow Tool System：[tool-system.md](tool-system.md)
- DeerFlow Context Management：[context-management.md](context-management.md)
- 横向 Permission / Security：[../../comparison/permission-security.md](../../comparison/permission-security.md)
- 横向 QA：[../../comparison/qa.md](../../comparison/qa.md#permission--security--guardrail--权限安全与防护)

## 源码入口

| 模块 | 源码 | 说明 |
|---|---|---|
| Gateway authz | [authz.py](../../../submodules/deer-flow/backend/app/gateway/authz.py) | Gateway API 的鉴权 / 授权层：`AuthContext`、`require_auth`、`require_permission`、resource action permissions、owner_check。 |
| Agent factory | [factory.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/factory.py) | 从 feature config 组装 agent middleware chain，保证 `ClarificationMiddleware` 位于最后。 |
| Guardrail middleware | [middleware.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/guardrails/middleware.py) | 工具调用前的策略检查：构造 `GuardrailRequest`，调用 provider，deny 时返回错误 `ToolMessage`，异常默认 fail-closed。 |
| Guardrail provider | [provider.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/guardrails/provider.py) | `GuardrailRequest` / `GuardrailDecision` / `GuardrailProvider` 协议，定义外部策略引擎接入边界。 |
| Tool error handling | [tool_error_handling_middleware.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/tool_error_handling_middleware.py) | 捕获工具执行异常，转换为模型可见的 error `ToolMessage` 和恢复提示。 |
| Loop detection | [loop_detection_middleware.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/loop_detection_middleware.py) | 检测重复工具调用集合和同类工具高频调用，warn / hard-stop 防止 loop 失控。 |
| Tool progress | [tool_progress_middleware.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/tool_progress_middleware.py) | 根据工具结果质量跟踪进展，维护 ACTIVE / WARNED / BLOCKED 状态机。 |
| Read-before-write | [read_before_write_middleware.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/read_before_write_middleware.py) | 对已有文件写入要求先读，使用内容版本 / hash 和 per-path lock 降低误写风险。 |
| Clarification / HITL | [clarification_middleware.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/clarification_middleware.py) | 把澄清请求变成可终止当前 run 的 HITL 工具；非交互模式可禁用。 |
| Sandbox lifecycle | [middleware.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/sandbox/middleware.py) | 按 thread 获取 / 复用 sandbox，把工具执行环境和会话线程绑定。 |
| Run manager | [manager.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/runtime/runs/manager.py) | 同一 thread 的 run lifecycle、并发策略、cancel / interrupt / rollback、状态持久化和 orphan reconciliation。 |
| Memory middleware | [memory_middleware.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/memory_middleware.py) | agent 完成后过滤消息并异步更新长期 memory，涉及记忆写入边界和污染风险。 |
| App config | [app_config.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/config/app_config.py) | guardrails、loop_detection、tool_progress、read_before_write、sandbox、memory、token_budget 等安全相关配置入口。 |

## 核心结论

DeerFlow 不是 Claw-Code 那种“本地工具权限门”，也不是 OpenHands 那种“ActionEvent 风险安检”。它更像一个 **工作流工厂安全生产线**：

```text
外层：Gateway API authz
  -> 谁能读 / 写 / 删除 thread？谁能创建 / 读取 / 取消 run？是否是 owner？

中层：GuardrailMiddleware + GuardrailProvider
  -> 某次工具调用是否被平台策略允许？外部策略引擎是否 deny？失败时是否 fail-closed？

内层：Workflow safety middleware chain + RunManager + Sandbox
  -> 工具异常怎么恢复？是否陷入 loop？是否有进展？写文件前是否读过？
     是否需要澄清？run 是否要 interrupt / rollback？工具在哪个 sandbox 里跑？
```

最重要的精髓：

> **DeerFlow 的权限安全不是一个单点 PermissionPolicy，而是 Gateway 授权、工具 guardrail、LangGraph middleware / run lifecycle 三层防线叠加。**

通俗比喻：

> **DeerFlow 像一座工作流工厂。Gateway 是厂门门禁，GuardrailMiddleware 是每个工位开工前的安全检查员，LoopDetection / ToolProgress / ReadBeforeWrite / Clarification / RunManager 是生产线上的质检、熔断、返工、停线和班次调度机制。**

## 1. 第一层：Gateway API authz，先管“谁能操作资源”

DeerFlow 有平台 / Gateway 形态，因此第一层不是模型工具调用，而是 API 资源授权。核心在 [authz.py](../../../submodules/deer-flow/backend/app/gateway/authz.py)。

这一层回答的问题是：

```text
当前请求是谁发起的？
它有没有 threads:read / threads:write / threads:delete？
它有没有 runs:create / runs:read / runs:cancel？
这个资源是否属于当前 user / principal？
```

典型构件包括：

| 构件 | 作用 |
|---|---|
| `AuthContext` | 表示当前调用方身份、权限集合、principal / user 等认证上下文。 |
| `require_auth` | 路由层认证要求。 |
| `require_permission` | 按 `resource:action` permission 检查 API 能力。 |
| `owner_check` | 对 thread / run 等资源做归属检查，避免跨用户访问。 |
| `Permissions` | 统一定义 `THREADS_READ`、`THREADS_WRITE`、`THREADS_DELETE`、`RUNS_CREATE`、`RUNS_READ`、`RUNS_CANCEL` 等权限字符串。 |

这一层和后面的 tool guardrail 不是同一件事：

```text
Gateway authz：调用方有没有资格操作 DeerFlow 平台资源。
Tool guardrail：模型这一次工具调用能不能执行。
Workflow safety：run 内部是否继续、安全、可恢复。
```

## 2. 第二层：GuardrailMiddleware，工具调用前的策略检查

DeerFlow 的工具级防线在 [guardrails/middleware.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/guardrails/middleware.py) 和 [guardrails/provider.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/guardrails/provider.py)。

它的流程可以简化为：

```text
ToolCallRequest
  -> GuardrailMiddleware.wrap_tool_call
  -> 构造 GuardrailRequest(tool_name, tool_input, agent_id, thread_id, user_id, is_subagent, ...)
  -> provider.aevaluate(...) / provider.evaluate(...)
  -> GuardrailDecision(allow=True/False, reasons, policy_id, metadata)
  -> allow：继续执行工具
  -> deny：返回 error ToolMessage 给模型
  -> provider 异常：默认 fail_closed，拒绝工具调用
```

这层的几个关键点：

1. **策略引擎是可插拔的**
   - `GuardrailProvider` 是协议，不把策略写死在 middleware 里。
   - 平台可以接内部规则、外部策略服务、企业审计系统或简单 allow / deny provider。

2. **评估对象不是裸工具名，而是带上下文的请求**
   - `GuardrailRequest` 不只包含 `tool_name` / `tool_input`，还携带 agent、thread、user、subagent 等上下文。
   - 这使策略可以表达“某个用户 / 某个 thread / 某个子 agent 不能调用某类工具”。

3. **拒绝会反馈给模型**
   - deny 不是静默丢弃，而是转换为 error `ToolMessage`。
   - 下一轮模型能看到 guardrail 拒绝原因，从而换策略、请求用户或停止。

4. **异常默认 fail-closed**
   - provider 出错时默认拒绝，而不是放行。
   - 对安全策略服务来说，这是更保守的边界。

所以 GuardrailMiddleware 更像“开工前安全检查员”：

> **每次工具调用开工前，检查员拿着上下文问策略引擎：这次能不能干？能干就放行，不能干就把拒绝原因写回工单；检查系统坏了默认停工。**

## 3. 第三层：Workflow safety middleware chain，管 run 是否健康

DeerFlow 的第三层是 agent runtime 的 middleware chain。装配入口在 [factory.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/factory.py)。

这层不是传统“权限审批”，但属于安全 / guardrail：它防止长任务 workflow 在工具错误、重复循环、无进展、上下文污染、写文件竞争、非交互澄清等情况下失控。

### 3.1 ToolErrorHandling：工具异常变成可恢复反馈

[tool_error_handling_middleware.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/tool_error_handling_middleware.py) 捕获工具函数抛出的异常，并转换成 error `ToolMessage`。

价值在于：

```text
工具抛异常
  -> middleware 捕获
  -> 生成模型可见的错误消息 + recovery hint
  -> agent 下一轮可以改参数 / 换工具 / 请求用户
```

这和安全有关，因为工具错误如果直接打断进程，会让 run 状态和上下文难以恢复；如果吞掉错误，又会让模型误以为工具成功。

### 3.2 LoopDetection：重复工具循环熔断

[loop_detection_middleware.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/loop_detection_middleware.py) 主要做两类检测：

| 检测 | 含义 |
|---|---|
| hash-based | 当前一批工具调用集合和历史重复，说明模型可能在重复做同一组动作。 |
| frequency-based | 同类工具调用次数过高，说明可能陷入某类工具的局部循环。 |

它有 warn 和 hard limit 两级机制：

```text
接近阈值：给下一轮模型注入 warning，让模型自我修正。
达到硬限制：剥离 tool_calls / 强制文本输出，阻止继续调用工具。
```

这不是“权限拒绝”，而是“生产线熔断”：模型不是没有权限，而是行为模式已经像失控循环。

### 3.3 ToolProgress：看工具结果是否真的推进任务

[tool_progress_middleware.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/tool_progress_middleware.py) 和 LoopDetection 分工不同：

```text
LoopDetection：看调用模式是否重复。
ToolProgress：看工具结果是否有进展。
```

它维护类似：

```text
ACTIVE -> WARNED -> BLOCKED
```

的状态机。适合处理“模型一直调用不同参数，但没有实质进展”的情况。

### 3.4 ReadBeforeWrite：写之前必须先看过当前版本

[read_before_write_middleware.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/read_before_write_middleware.py) 处理文件写入风险：

```text
read_file(path)
  -> 记录 path 当前版本 / hash
write_file 或 str_replace(path)
  -> 如果是已有文件但本 thread 未读过，拒绝
  -> 如果版本变化，拒绝 / 要求重新读
  -> per-(thread, path) lock 降低并发写竞争
```

这类机制在 coding / file tool 场景非常重要：它不是防止恶意命令，而是防止模型基于过期上下文误写、覆盖用户改动或并发踩踏。

### 3.5 ClarificationMiddleware：把不确定性变成 HITL 边界

[clarification_middleware.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/clarification_middleware.py) 把“需要用户澄清”变成一个工具化的人机交互边界。

关键点：

```text
模型调用 clarification tool
  -> middleware 拦截
  -> 返回 Command(goto=END)
  -> 当前 run 停在需要用户补充的位置
```

它还有非交互模式禁用逻辑，避免 scheduler / background run 这类不能问用户的场景卡住。

这层属于安全边界：当信息不足时，不是让模型继续猜，而是让 workflow 停下来问人。

## 4. RunManager：同一 thread 的并发、取消和回滚边界

[manager.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/runtime/runs/manager.py) 管的是 run lifecycle。它和权限安全的关系在于：长任务 agent 不仅要防单次工具危险，还要防同一 thread 上多个 run 互相踩踏、取消后状态不一致、崩溃后 inflight 状态残留。

关键能力：

| 能力 | 说明 |
|---|---|
| `create_or_reject` | 原子检查同一 thread 是否已有 running run，并按 `multitask_strategy` 决定 reject / interrupt / rollback。 |
| `cancel(action=...)` | 取消 run，`interrupt` 保留 checkpoint，`rollback` 回到 run 前状态。 |
| `abort_event` / `abort_action` | worker 和工具链可以观察取消意图。 |
| status persistence | 记录 queued / running / interrupted / failed / completed 等状态。 |
| orphan reconciliation | 服务重启后清理或修复遗留 inflight run。 |

这层的通俗比喻是“班次调度 + 停线按钮”：

> **同一条生产线不能随便同时开两批工单；如果要打断，要说明是保留当前半成品，还是回滚到开工前。**

## 5. SandboxMiddleware：执行环境是硬边界

DeerFlow 也有 sandbox 维度，入口在 [sandbox/middleware.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/sandbox/middleware.py)。它的特点是按 thread 获取 / 复用 sandbox：

```text
thread_id
  -> lazy acquire sandbox
  -> 绑定到当前 agent run / tool context
  -> 跨 turn 复用
  -> 生命周期不等同于单次 tool call
```

这说明 DeerFlow 的安全不是只靠软策略：

```text
GuardrailMiddleware：软门禁，判断某次工具调用能不能做。
SandboxMiddleware：硬环境，把工具执行限制在某个隔离工作区 / 运行环境里。
```

## 6. MemoryMiddleware：长期记忆写入也是安全问题

[memory_middleware.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/memory_middleware.py) 在 agent 完成后异步更新长期 memory。它会过滤消息，只把 user 和 final assistant 等关键内容进入记忆更新流程，并在 enqueue 时捕获 user_id。

这属于权限 / 安全的延伸问题：

```text
工具危险：模型能不能执行外部动作？
记忆危险：模型会不会把错误、敏感、临时、被注入的信息长期保存？
```

当前笔记只确认了 memory update 的 middleware 边界；memory 污染防护、事实提取、删除 / 回滚策略应放到后续 memory-system 专题继续核验。

## 7. 和 Claw-Code / OpenHands 的关键区别

### 对比 Claw-Code

Claw-Code 的核心问题是：

```text
这次工具调用能不能在用户本机 / workspace 执行？
```

因此它需要 PermissionPolicy、PermissionPrompter、PermissionEnforcer 和 hooks。

DeerFlow 的核心问题更像：

```text
这个 Gateway run 能否被当前用户操作？
这次工具调用是否通过平台 guardrail？
这个 LangGraph workflow 是否还健康、可恢复、可中断、可澄清？
```

所以 DeerFlow 的安全治理更分布式，不集中在一个本地 permission policy。

### 对比 OpenHands

OpenHands 的中心是 `ActionEvent`：

```text
ActionEvent -> SecurityAnalyzer -> ConfirmationPolicy -> WAITING_FOR_CONFIRMATION / Observation
```

DeerFlow 的中心更像 run + middleware：

```text
Gateway run -> agent.astream(...) -> middleware chain -> ToolMessage / Command / state / checkpoint
```

OpenHands 问“这个 Action 风险多高，要不要确认”；DeerFlow 问“这个 workflow run 在多层防线下能不能继续健康执行”。

## 8. QA / 讨论记录

### Q: DeerFlow 的安全治理是不是只有 middleware？

> **状态**: verified
> **来源**: source-code / discussion

A: 不是。middleware 是 DeerFlow 的核心风格，但完整防线至少有三层：Gateway API authz 管用户和资源权限；GuardrailMiddleware + GuardrailProvider 管工具调用前策略检查；workflow safety middleware chain + RunManager + Sandbox 管 run lifecycle、工具错误、loop、进展、写入版本、HITL 和执行环境。把 DeerFlow 简化成“只有中间件防线”会漏掉 Gateway 和 run / sandbox 两层。

### Q: GuardrailMiddleware 和 ToolErrorHandlingMiddleware 的区别是什么？

> **状态**: verified
> **来源**: source-code / discussion

A: GuardrailMiddleware 发生在工具执行前，问“这次工具调用按策略能不能执行”；deny 时不执行工具，直接返回 error ToolMessage。ToolErrorHandlingMiddleware 发生在工具执行过程中，问“工具已经执行但抛异常时如何恢复”；它把异常转换成模型可见的错误反馈。前者是开工前门禁，后者是开工后故障处理。

### Q: DeerFlow 的 loop detection 是权限系统吗？

> **状态**: verified
> **来源**: source-code / discussion

A: 严格说不是权限系统，而是 workflow safety guardrail。它不判断某个工具是否被授权，而是判断模型行为是否出现重复调用集合或同类工具高频调用。达到 warn 阈值时提醒模型，达到 hard limit 时阻止继续工具调用。因此它更像生产线熔断器，而不是门卫。

### Q: 为什么说 DeerFlow 像“工作流工厂安全生产线”？

> **状态**: verified
> **来源**: source-code / discussion

A: 因为它的安全不是一个单点确认框，而是沿着 Gateway -> run -> agent middleware -> tool -> sandbox -> memory 的生产线分布。Gateway 门禁管谁能操作资源；GuardrailMiddleware 管工具调用前策略检查；ToolErrorHandling、LoopDetection、ToolProgress、ReadBeforeWrite、Clarification 等 middleware 管 run 内部健康；RunManager 管同一 thread 的并发、取消和回滚；SandboxMiddleware 管执行环境边界。这种形态更像工厂里的门禁、安检、质检、熔断、停线和工位隔离共同组成的安全生产线。
