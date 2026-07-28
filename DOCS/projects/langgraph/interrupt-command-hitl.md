# LangGraph Interrupt、Command 与 Human-in-the-loop

> **日期**: 2026-07-28 | **状态**: draft | **涉及版本**: `30c4d58`

## 相关文档与源码

- 前置课程：[Pregel Channel 与运行时](pregel-runtime.md)
- 学习入口：[LangGraph 学习笔记](README.md)
- `Command` 与 `interrupt()`：[types.py](../../../submodules/langgraph/libs/langgraph/langgraph/types.py)
- 外部 `Command` 输入映射：[_io.py](../../../submodules/langgraph/libs/langgraph/langgraph/pregel/_io.py)
- 恢复调用的启动处理：[_loop.py](../../../submodules/langgraph/libs/langgraph/langgraph/pregel/_loop.py)
- Node 返回值与控制写入：[state.py](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py)
- Interrupt Runner 处理：[_runner.py](../../../submodules/langgraph/libs/langgraph/langgraph/pregel/_runner.py)

## 本课主线

```text
interrupt() 暂停什么
→ Command(resume=...) 怎样恢复
→ Command 的整体定位
→ Command 从哪里产生
→ 外部输入与 Node 输出分别何时生效
→ update / resume / goto 的边界
→ Human-in-the-loop 如何避免重复副作用
```

当前进度：

- [x] `interrupt()` 暂停 Task 而不是冻结 Python 调用栈；
- [x] 恢复时 Node 从开头重新执行；
- [x] `resume`、`update`、`goto` 的职责边界；
- [x] Command 的外部输入与 Node 输出入口；
- [x] 人工、应用后端、Node 与 Tool 的 Command 产生关系；
- [x] Command 在 superstep 中的生效时机；
- [x] `Command.goto` 与 conditional edge 的选择；
- [x] 多个 interrupt、interrupt ID 与并行恢复；
- [x] subgraph 中的 `Command.PARENT`；
- [x] 可审计 HITL 的完整工程结构。

## 第一小节：`interrupt()` 暂停的不是 Python 调用栈

一句话结论：

> **`interrupt()` 终止当前 Graph Task 的本次执行，把“正在等待什么”交给 Runtime 和 Checkpointer 保存；它不会把 Python 函数冻结在某一行。**

例如人工审核 Node：

```python
def human_review(state):
    approved = interrupt({
        "question": "是否批准退款？",
        "amount": state["amount"],
    })
    return {"approved": approved}
```

第一次执行到 `interrupt()` 时没有恢复值，函数会抛出特殊的 `GraphInterrupt`。Runtime 将中断信息返回给调用方，并依靠 Checkpointer 保存可以重建工作的 State、任务和运行进度。原进程此后可以退出，不需要一直阻塞等待人工。

`interrupt()` 的说明明确指出：第一次调用会抛出 `GraphInterrupt`，恢复后会从 Node 开头重新执行，而且使用该能力必须配置 Checkpointer。见 [types.py:811-899](../../../submodules/langgraph/libs/langgraph/langgraph/types.py#L811-L899)。实现会按当前 Task 内的 interrupt 顺序查找已有 resume value；找不到时才创建 `Interrupt` 并抛出异常，见 [types.py:908-936](../../../submodules/langgraph/libs/langgraph/langgraph/types.py#L908-L936)。

## 第二小节：恢复是“重新执行并回放答案”

外部应用收到人工答案后，使用同一个 `thread_id` 恢复：

```python
graph.invoke(
    Command(resume=True),
    config={"configurable": {"thread_id": "refund-001"}},
)
```

运行过程是：

```text
第一次执行 human_review
→ interrupt() 找不到 resume value
→ 抛出 GraphInterrupt
→ 保存暂停现场并结束本次调用

外部提交 Command(resume=True)
→ Runtime 用同一 thread_id 读取 Checkpoint
→ 重建被中断的 Task
→ human_review 从开头重新执行
→ 再次调用同一个 interrupt()
→ interrupt() 取得 True 并正常返回
→ Node 返回 {"approved": True}
→ Runtime 在 Update 阶段更新 State
```

`resume=True` 本身没有直接执行 `State["approved"] = True`。它只是成为 `interrupt()` 的返回值；真正把答案写入 State 的，是恢复后的 Node 返回 `{"approved": approved}`。

> **本节精髓：LangGraph 恢复的是可重建的 Graph 执行，不是旧进程的函数栈。`Command(resume=...)` 提供回放答案，Node 重新执行到同一暂停点后才继续。**

## 第三小节：Command 的整体定位

`Command` 是交给 Runtime 的运行控制指令包。它不是 State、Node 或函数调用，也不会在创建时立即产生跳转。当前类型包含四个核心字段，见 [types.py:759-800](../../../submodules/langgraph/libs/langgraph/langgraph/types.py#L759-L800)：

| 字段 | 含义 | 常见使用位置 |
|---|---|---|
| `resume` | 为暂停的 interrupt 提供答案 | 外部应用恢复现有 thread |
| `update` | 提交 State 部分更新 | Node / Tool 输出，也可由外部调用提供 |
| `goto` | 提交后续调度目标 | Node / Tool 动态控制路线，也可由外部调用提供 |
| `graph` | 指定当前图或父图 | subgraph 跨层控制 |

可以用办事大厅类比：

```text
State       = 业务档案
Node        = 处理业务的工作人员
Edge        = 预先制定的流转路线
Runtime     = 调度中心
Command     = 运行期间交给调度中心的操作单
Checkpoint  = 运行存档
```

因此，“Command 是执行流中的插入机制”可以作为初步直觉，但更准确的说法是：

> **Command 是图运行期间向 Runtime 动态提交状态更新、恢复信息或调度意图的机制。它是受 Runtime 规则约束的一等指令，不是任意代码注入或立即跳转。**

## 第四小节：Command 从哪里产生

`Command` 本质上是普通 Python 对象，可以由外部应用、Node 或 Tool 创建。需要区分“谁提供业务决定”与“谁创建 Python 对象”。

### 外部应用创建

人工审批时，人工通常只在前端点击“批准”或填写补充信息。后端收到输入后才真正构造 Command：

```text
Graph 产生 interrupt
→ 前端展示审批问题
→ 人工提交决定
→ 后端创建 Command(resume=人工决定)
→ 后端调用 graph.invoke(..., 同一 thread_id)
```

因此，“人工产生 Command”在业务含义上成立，但技术上通常是人工提供决定，应用后端负责包装成 `Command`。

### Node 创建

Node 可以根据 State、规则或模型结果返回动态指令：

```python
def risk_router(state):
    if state["risk_score"] > 80:
        return Command(
            update={"status": "manual_review"},
            goto="human_review",
        )
    return Command(
        update={"status": "approved"},
        goto="execute_refund",
    )
```

这类 `Command(update=..., goto=...)` 完全可以在没有人工参与的情况下产生。

### Tool 创建

Tool 也可以返回 Command，用于在工具执行后更新 Agent State 或影响后续路线。LLM 通常只是产生 Tool Call；真正的 Python Command 由 Tool 实现创建，再由 ToolNode 和 Runtime 处理。

| 决定来源 | Command 的实际创建者 | 常见字段 |
|---|---|---|
| 人工审批 | 应用后端 | `resume`，有时同时有 `update` |
| 业务规则 | Node 代码 | `update` + `goto` |
| 模型判断 | 调用模型的 Node 或被调用 Tool | `update` / `goto` |
| 工具执行结果 | Tool 代码 | `update`，有时有 `goto` |

Runtime 通常不是业务 Command 的决策者。它负责识别、拆解和执行 Command 描述的意图。

## 第五小节：Command 的两个起作用时机

Command 有两个主要入口，它们进入 Runtime 的时机不同。

### 外部 Command：一次调用开始时

当调用方执行：

```python
graph.invoke(Command(resume=...), config)
```

Runtime 会在恢复已有 Checkpoint、准备本次 Tasks 之前处理 Command。`PregelLoop._first()` 将 Command 输入视为在已有状态上继续运行，并要求 `Command(resume=...)` 配合 Checkpointer，见 [_loop.py:854-945](../../../submodules/langgraph/libs/langgraph/langgraph/pregel/_loop.py#L854-L945)。

`map_command()` 把不同字段映射为不同内部 writes，见 [_io.py:56-78](../../../submodules/langgraph/libs/langgraph/langgraph/pregel/_io.py#L56-L78)：

```text
resume → RESUME 控制写入
update → State 字段的数据 Channel 写入
goto   → branch Channel 或 TASKS 写入
```

这些 writes 先应用到恢复现场，随后 Runtime 才规划本次调用需要执行的 Tasks。

### Node 返回 Command：本轮 Execution 结束后

Node 返回的 Command 是本轮计算结果。StateGraph 编译时为 Node 输出安装 writers：`update` 被提取为 State Channel writes，`goto` 被提取为控制 Channel writes，见 [state.py:1439-1490](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py#L1439-L1490) 和 [state.py:1738-1756](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py#L1738-L1756)。

```text
Execution
→ Node 返回 Command(update=..., goto=...)
→ Runtime 收集 pending writes

Update / barrier
→ Channel / Reducer 应用 update
→ branch Channel 应用 goto 触发信号

下一轮 Plan
→ Runtime 为 goto 目标创建 Task
```

所以 Node 创建 Command 不会让目标 Node 在当前函数调用栈中立即运行，也不会让同一 superstep 已经执行的其他 Node 突然看到新 State。

> **本节精髓：外部 Command 在一次恢复调用开始、任务规划之前起效；Node 返回的 Command 在本 superstep 的 Update 阶段起效，目标 Node 通常在下一 superstep 执行。**

## 第六小节：一条完整 HITL 控制链

```python
def human_review(state):
    decision = interrupt({
        "question": "是否批准退款？",
        "amount": state["amount"],
    })

    if decision["approved"]:
        return Command(
            update={
                "status": "approved",
                "reviewer": decision["reviewer"],
            },
            goto="execute_refund",
        )

    return Command(
        update={
            "status": "rejected",
            "reviewer": decision["reviewer"],
        },
        goto="notify_rejection",
    )
```

完整时间线：

```text
第一次 invoke
→ Runtime 调度 human_review
→ interrupt() 暂停当前 Task
→ Checkpointer 保存运行现场
→ 调用方收到审批问题

人工在外部系统完成审批
→ 后端创建 Command(resume=decision)
→ 使用同一 thread_id 再次 invoke
→ Runtime 读取 Checkpoint 并注入 resume
→ human_review 从头重新执行
→ interrupt() 返回 decision
→ Node 返回 Command(update=..., goto=...)

本轮 Update
→ status / reviewer 合并进 State
→ goto 写入控制 Channel
→ 保存新的 Checkpoint

下一 superstep
→ Runtime 调度 execute_refund 或 notify_rejection
```

其中有两个不同 Command 入口：

```text
外部 Command(resume)
= 重新启动并回答已暂停的 Task

Node 返回 Command(update, goto)
= 说明本轮结束后如何更新 State、安排下一站
```

## 第七小节：Command 的边界规则

### `resume` 不等于 State update

`resume` 只是 `interrupt()` 的返回值。Node 可以把它写入 State，也可以仅用于局部判断；是否进入 State 由 Node 返回值或显式 `Command.update` 决定。

### `goto` 不等于直接函数调用

`goto="execute_refund"` 产生调度写入，由 Runtime 在后续任务规划中解释。当前 Node 不会直接调用 `execute_refund()`。

### Command 仍遵守 superstep 边界

Node 返回的 `update` 和 `goto` 都先成为 writes，在 barrier 后统一应用。Command 没有绕开 Channel、Reducer、Checkpoint、stream 或 tracing。

### `goto` 不天然覆盖已有 Edge

Command 是额外的动态控制意图，不应默认理解成“覆盖图上所有既有路线”。如果同一 Node 还配置了固定 Edge 或其他 branch，它们也可能产生控制写入和后续任务。建图时应明确使用哪一种控制方式，避免重复调度。

## 第八小节：恢复重放与外部副作用

因为恢复会从 Node 开头重新执行，`interrupt()` 前面的代码可能重复运行：

```python
def unsafe_review(state):
    send_email("审批已创建")
    approved = interrupt("是否批准？")
    return {"approved": approved}
```

恢复时 `send_email()` 可能再次执行。支付、退款、短信、邮件和外部数据库写入必须使用业务幂等键，或拆到审批完成后的独立 Node：

```text
prepare_review
→ human_review：只负责 interrupt 和记录决定
→ execute_refund：使用 refund:{request_id} 幂等键执行退款
```

即使副作用放在 `interrupt()` 后面，也仍需考虑 Node 在副作用成功、Checkpoint 保存前失败并被重试的情况。Durable execution 不能替外部系统提供 exactly-once。

## 第九小节：`Command.goto` 与 conditional edge

二者都可以动态选择下一站，但决策位置不同。可以把 StateGraph 想成医院：Node 是科室，State 是病历，Runtime 是调度中心。

conditional edge 像科室门口的独立分诊员：科室只把检查结果写进病历，分诊员再读取结果并决定病人去普通门诊还是急诊。

```text
Node 完成业务计算
→ 返回 State 部分更新
→ 独立 routing function 读取结果
→ 选择目标
→ Runtime 调度目标 Node
```

`Command.goto` 像医生在写检查结果时同时开出转诊单：Node 已经掌握完整决定，因此把 State 更新和下一站一起交给 Runtime。

```text
Node 完成业务计算
→ 返回 Command(update=..., goto=...)
→ Runtime 在 barrier 后应用状态和控制写入
→ 下一轮调度目标 Node
```

选择原则：

| 场景 | 更自然的方式 |
|---|---|
| 路线只依赖 State 中已有字段，希望业务与路由分离 | conditional edge |
| Node 刚得到一个决定，状态更新与下一站天然属于同一结果 | `Command(update, goto)` |
| 希望路线集中在 Builder 中，便于阅读和测试 | conditional edge |
| Tool、subgraph 或 HITL Node 需要同时更新状态和控制路线 | Command |

conditional edge 的 path 在 Node writer 阶段读取最新值并产生目标 writes，见 [_branch.py:146-225](../../../submodules/langgraph/libs/langgraph/langgraph/graph/_branch.py#L146-L225) 和 [state.py:1563-1612](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py#L1563-L1612)。Command 的 `goto` 同样会转换为 branch Channel 或 Task write。因此二者在业务表达上不同，进入 Runtime 后都不会直接调用目标函数。

还要注意，`Command.goto` 不天然取消已经配置在该 Node 上的普通 Edge 或其他 branch。它更像增加一张动态调度单，而不是撕掉所有既有路线。

> **本节精髓：conditional edge 是独立分诊员，`Command.goto` 是 Node 开出的转诊单。前者强调业务计算与路由分离，后者强调状态更新与路线属于同一个运行结果。**

## 第十小节：多个 Interrupt 怎样匹配答案

`thread_id` 标识整条工作流执行线，`interrupt.id` 标识这条执行线中的一个具体暂停问题。可以继续使用医院类比：`thread_id` 是本次就诊档案号，interrupt ID 是心内科或药剂科各自开出的待确认单号。

### 同一个 Task 内依次出现多个 interrupt

如果同一个 Node 依次询问“是否同意治疗”和“希望安排哪一天”，第一次先在第一个问题暂停。恢复后 Node 从头执行，第一个 `interrupt()` 取得已经保存的答案，再运行到第二个 `interrupt()` 并暂停。LangGraph 在同一 Task 内按调用顺序匹配 resume values，见 [types.py:824-828](../../../submodules/langgraph/libs/langgraph/langgraph/types.py#L824-L828)。

因此，恢复前后不应随意重排、增加或删除这些 interrupt 调用，否则原有答案与调用位置可能错配。

### 多个并行 Task 同时 interrupt

如果两个并行 Node 分别等待人工修改两段文本，它们可能同时形成两个 pending interrupts。此时只有一个无 ID 的答案会产生歧义，Runtime 要求调用方按 interrupt ID 提供答案映射：

```text
interrupt-A → 给任务 A 的答案
interrupt-B → 给任务 B 的答案
```

每个 `Interrupt` 暴露 `value` 和可用于定向恢复的 `id`，见 [types.py:557-582](../../../submodules/langgraph/libs/langgraph/langgraph/types.py#L557-L582)。当前测试明确覆盖了多个并行 interrupt 拒绝单一无 ID resume、接受 ID 到答案映射的行为，见 [test_pregel.py:8915-8961](../../../submodules/langgraph/libs/langgraph/tests/test_pregel.py#L8915-L8961)。

可以一次只回答其中一个，也可以一次提交多个 ID 对应的答案。未回答的任务继续保持暂停。

> **本节精髓：`thread_id` 回答“恢复哪条工作流”，`interrupt.id` 回答“这条工作流里的哪个暂停任务”。同一 Task 的连续 interrupt 按调用顺序匹配；多个并行 interrupt 必须用 ID 防止答案错投。**

## 第十一小节：Subgraph 与 `Command.PARENT`

Subgraph 是嵌套在主流程里的小流程，可以把它理解成总公司里的法务部门：法务内部还有检查合同、核对证据和形成结论等多个工位。

普通 Command 默认交给当前图处理。法务内部 Node 返回 `goto="check_evidence"`，意思是在法务子图内部继续流转。

当子图需要更新父图或跳转到父图中的 Node 时，Command 必须把收件层级指定为 `Command.PARENT`：

```text
法务子图发现重大风险
→ 产生交给 PARENT 的状态更新和跳转意图
→ 指令上交给紧邻的父图 Runtime
→ 父图更新自己的 State
→ 父图调度高级审核 Node
```

`Command.graph` 支持 `None` 和 `Command.PARENT`：前者表示当前图，后者表示最近一层父图；`goto` 目标也必须属于所指定的图，见 [types.py:759-780](../../../submodules/langgraph/libs/langgraph/langgraph/types.py#L759-L780)。三层嵌套时，`PARENT` 只上交一级，不会直接越过中间层到最外层。

并非子图正常结束都需要 `PARENT`。如果子图只返回结果，父图已有固定 Edge 负责继续执行，就让子图正常结束即可。只有子图内部需要动态修改父层状态或选择父层路线时，才需要这张“上交一级”的调度单。

> **本节精髓：普通 Command 是当前部门内部的调度单，`Command.PARENT` 是交给紧邻上级组织的调度单。它改变的是指令的解释层级，不是直接调用父图 Node。**

## 第十二小节：完整可审计 HITL 闭环

Human-in-the-loop 不是让 Python 进程停在原地等人，而是工作流生成一张人工待办并保存现场，人通过外部系统处理待办，后端再把结果送回原来的 thread。

完整链路是：

```text
机器运行 Graph
→ 发现需要人工决定
→ interrupt 暂停 Task，Checkpointer 保存现场
→ 应用后端把 interrupt 转换为人工待办
→ 审核人在审批页面查看材料并处理
→ 后端验证身份、权限、待办状态和输入
→ 后端记录审计信息
→ Command(resume=人工决定)
→ Runtime 恢复原 thread
→ Node 取得答案并更新 State
→ 独立执行 Node 处理支付、通知等副作用
→ 保存后续 Checkpoint 和执行结果
```

LangGraph 与业务系统的责任不同：

| LangGraph 提供 | 业务系统仍需提供 |
|---|---|
| 暂停 Graph Task | 审批页面和待办分配 |
| Checkpoint 与 thread 恢复 | 登录、身份和权限验证 |
| Interrupt value 与 ID | 审核人、时间、理由和材料快照 |
| `Command(resume=...)` 回流 | 防重复审批和输入校验 |
| 后续状态与任务调度 | 支付、短信等外部操作幂等 |

一条可审计记录通常需要关联业务单号、`thread_id`、interrupt ID、暂停时的 checkpoint ID、审核人、时间、动作、理由、人工修改内容、恢复后的 checkpoint，以及后续真实执行结果。LangGraph 能提供其中的运行时标识和恢复底座，但不会自动成为完整的企业审批与权限系统。

审批决定和真实副作用最好拆开：人工审核 Node 只记录“谁批准了什么”，退款执行 Node 再使用业务幂等键完成支付操作。这样才能分别追踪审批完成、退款执行、失败重试和用户通知。

> **本节精髓：生产级 HITL 是 LangGraph Runtime、Checkpointer、业务后端、审批界面、权限系统、审计日志和幂等执行共同组成的闭环。LangGraph 提供可暂停、可保存、可恢复的底座，不自动包办整个审批平台。**

## QA / 讨论记录

### Q: Command 是否相当于整体图执行流中的插入机制？

> **状态**: verified
> **来源**: source-code / discussion

A: 可以作为初步直觉，但 Command 不是任意代码注入。它是在图运行期间向 Runtime 提交 `resume`、`update`、`goto` 等动态意图的一等数据结构。外部 Command 很像从图外插入恢复信息；Node 或 Tool 返回 Command 则属于图内正常产生的运行时指令。所有意图最终仍由 Runtime 映射为 writes，并遵守 Update、Channel 和任务规划边界。

### Q: Command 是人工产生的，还是 Node 产生的？

> **状态**: verified
> **来源**: source-code / discussion

A: 两种来源都存在。人工通常只提供决定，应用后端将其包装为 `Command(resume=...)`；Node 或 Tool 可以在执行期间创建并返回 `Command(update=..., goto=...)`。Runtime 通常负责解释 Command，而不是替业务决定并自动创建它。

### Q: `Command(resume=True)` 是否会自动把 `approved=True` 写入 State？

> **状态**: verified
> **来源**: source-code / discussion

A: 不会。`resume=True` 是 `interrupt()` 的返回值。只有恢复后的 Node 返回 `{"approved": True}`，或某个 Command 明确携带 `update={"approved": True}`，State 才会收到该更新。

### Q: Node 返回 Command 后，`goto` 目标是否立即执行？

> **状态**: verified
> **来源**: source-code / discussion

A: 不会在当前 Python 调用栈中直接执行。Node 返回 Command 后，Runtime 把 `goto` 转换为控制 Channel write，在 barrier 后应用，并在后续 Plan 阶段创建目标 Task。

## 本课小结与下一步

本课已经串起 `interrupt()` 暂停、Checkpoint 保存、`Command(resume=...)` 恢复、Command 的产生来源和两个 Runtime 入口，并比较了 conditional edge、多个 interrupt ID、`Command.PARENT` 与生产级 HITL 的责任边界。

下一课进入 ToolNode 与预构建 Agent，先回答：模型只产生 Tool Call 意图后，谁负责找到真实 Tool、校验参数、执行调用，并把 `ToolMessage` 放回消息历史。
