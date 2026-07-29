# LangGraph Dynamic Send 与 Functional API

> **日期**: 2026-07-29 | **状态**: draft | **涉及版本**: LangGraph `30c4d58`

## 相关文档与源码

- [StateGraph 基础](state-graph.md)
- [Pregel Channel 与任务调度](pregel-runtime.md)
- [Checkpoint Persistence、History 与 Time Travel](checkpoint-persistence.md)
- [Graph 可靠性策略](graph-reliability.md)
- `Send` 与 `Command.goto`：[types.py](../../../submodules/langgraph/libs/langgraph/langgraph/types.py)
- Conditional edge 对 `Send` 的处理：[graph/_branch.py](../../../submodules/langgraph/libs/langgraph/langgraph/graph/_branch.py)
- `@task` 与 `@entrypoint`：[func/__init__.py](../../../submodules/langgraph/libs/langgraph/langgraph/func/__init__.py)
- Dynamic Send 场景测试：[test_large_cases.py](../../../submodules/langgraph/libs/langgraph/tests/test_large_cases.py)
- Functional API 并行、Interrupt 与恢复测试：[test_pregel.py](../../../submodules/langgraph/libs/langgraph/tests/test_pregel.py)

## 核心结论

> **Dynamic Send 解决“运行时才知道要并行处理多少份任务”；Functional API 解决“希望使用普通 Python 控制流编排任务，但仍需要 LangGraph Runtime 的 Task、Checkpoint、Interrupt 和可靠性能力”。**

两者都支持动态并行，但抽象位置不同：

```text
Send
= Graph API 中动态创建下一轮 pushed tasks
= 结果通过 State Channel 与 Reducer 汇合

@task
= Functional API 中像调用函数一样创建 Runtime Task
= 结果通过 Future 返回，由普通 Python 代码汇总
```

## 贯穿场景：合同批量审查

```text
读取合同
→ 动态拆出 N 个条款
→ 并行审查每个条款
→ 汇总风险
→ 高风险时人工审批
→ 生成最终报告
```

写 Graph 时并不知道一份合同有多少条款。普通合同可能有 20 条，复杂合同可能有 300 条，因此不能预先画出固定数量的 Worker Node。

## Dynamic Send：动态生成 Task 实例

普通 Edge：

```text
split_contract → review_clause
```

只表达下一步执行一次 `review_clause`。Dynamic Send 则让路由函数根据实际条款数返回多张任务单：

```python
def route_clauses(state: ContractState) -> list[Send]:
    return [
        Send(
            "review_clause",
            {"clause_id": index, "clause": clause},
        )
        for index, clause in enumerate(state["clauses"])
    ]
```

每个 `Send` 包含：

- `node`：目标 Node 的已注册名称；
- `arg`：本次 Task 单独收到的输入，可以不同于完整 Graph State；
- `timeout`：可选的 pushed task 超时策略，缺省时使用目标 Node 的策略。

Conditional edge 返回这些 Send 后，Runtime 不会在路由函数内部立即调用 Worker，而是在下一轮为同一个 Node 创建多个 Pregel Task：

```text
Send(review_clause, 条款 1) → review_clause Task 1
Send(review_clause, 条款 2) → review_clause Task 2
Send(review_clause, 条款 3) → review_clause Task 3
```

这些 Task 可以并行执行，但真实并发量仍受 `max_concurrency`、线程池、连接池、模型配额和外部服务限流约束。

> **精髓：Send 不是动态创建新的 Node 定义，而是动态创建同一个 Node 的多个 Task 实例。**

## Send 结果如何汇合

每个 Worker 可以返回一项部分更新：

```text
risk_results = [本条款审查结果]
```

多个并行 Task 会同时写 `risk_results`，因此该字段需要列表追加等 Reducer。到 superstep 的 Update barrier 后，Runtime 才统一合并：

```text
旧 risk_results
+ Task 1 结果
+ Task 2 结果
+ Task 3 结果
→ 新 risk_results
```

并行完成顺序不稳定，业务不能假设列表第一个结果一定属于第一条款。生产中应在结果里保留 `clause_id`，汇总 Node 再按 ID 排序。对并行写入使用的 Reducer 最好满足结合律；需要相互比较或竞争的最终业务结论，应由汇合后的决策 Node 产生。

## Send 与其他路由机制

| 机制 | 适用情况 |
|---|---|
| 普通 Edge | 目标固定，只执行一次 |
| 静态并行 Edge | 分支数量在写代码时已知 |
| Conditional Edge | 根据 State 动态选择一条或多条已知路线 |
| `Send` | 运行时动态产生任意数量的 Task，并给每个 Task 不同输入 |
| `Command(goto=Send(...))` | Node 需要把 State 更新和动态发任务作为同一个结果提交 |

Send 本身不创建 Subgraph、Agent、thread 或 checkpoint namespace。它只是当前 Graph 中的一项 pushed task；目标 Node 可以恰好是编译后的 Subgraph，但那是另一层结构。

每个 Send Task 可以独立失败、Retry 和 Timeout。配置 Checkpointer 后，Runtime 可以保存成功 Task 的 pending writes，在恢复时避免无意义地重做整批 Worker；外部副作用仍需幂等键和对账。

## Functional API 的通俗定义

> **Graph API 是先画流程图，再让 Runtime 按图执行；Functional API 是直接写普通 Python 办事步骤，再让 Runtime 在背后记录关键 Task。**

这里的 Functional API 不等于高深的“函数式编程”。它更接近“用函数写 LangGraph，而不是显式注册 Node 和 Edge”。

### Graph API：公司的标准流程图

报销流程使用 Graph API 时，会显式设计：

```text
START
→ split_invoices
→ Send 多个 check_invoice
→ Reducer 汇总
→ calculate_total
→ conditional edge
→ request_approval / complete_payment
→ END
```

开发者还要声明 State schema、Node、Edge、Reducer 和分支条件。它像贴在墙上的标准流程图，适合需要看清全局路线、阶段边界和共享状态的复杂系统。

### Functional API：主管的办事脚本

同一个流程可以直接使用普通 Python 的函数调用、循环和 `if`：

```python
@task
def check_invoice(invoice: Invoice) -> CheckResult:
    return inspect_invoice(invoice)


@entrypoint(checkpointer=checkpointer)
def reimburse(invoices: list[Invoice]) -> ReimburseResult:
    futures = [check_invoice(invoice) for invoice in invoices]
    results = [future.result() for future in futures]
    total = calculate_total(results)

    if total > 10_000:
        approved = interrupt("请主管审批")
        if not approved:
            return ReimburseResult(status="rejected")

    return execute_reimbursement(total)
```

表面上它是普通 Python；底层 `@entrypoint` 会把整个函数包装成 Pregel workflow，`@task` 调用则交给 Runtime 调度。

## `@entrypoint` 与 `@task` 分别做什么

`@entrypoint` 是整个 workflow 的入口。它支持同步或异步函数，接收一个主要业务输入，还可以由 Runtime 注入 `config`、`previous` 和 `runtime`。装饰后得到的对象仍支持 `invoke`、`ainvoke`、`stream`、Checkpoint、Store、Cache、Retry、Timeout 和 Interrupt。

`@task` 把一个函数变成可持久化调度的工作单元。调用时返回 Future，而不是直接返回业务结果：

```text
调用 check_invoice(invoice)
→ Runtime 创建 Task
→ 立即得到 Future
→ future.result() 等待并取得结果
```

先创建全部 Future，再统一等待，可以并行；如果创建一个 Future 后立即等待，再创建下一个，就会退化成串行。`@task` 只能在 entrypoint 或 StateGraph 执行上下文中调用，并可单独配置 Retry、Cache 和 Timeout。

## Functional API 的 State 在哪里

Functional API 没有要求用户显式定义共享 State schema 和 Reducer，用户主要看到：

```text
函数参数
→ 局部变量
→ Task Future
→ Task 返回值
→ entrypoint 返回值
```

底层并不是没有 Runtime State。`@entrypoint` 实际会构造带 `START`、`END` 和 `PREVIOUS` 等 Channel 的 Pregel workflow，只是 Channel 和 Task 调度被 API 隐藏了。

因此：

- Graph API 主要依靠共享 State、部分更新、Channel 与 Reducer 传递数据；
- Functional API 主要依靠函数参数、返回值、Future 和普通 Python 控制流传递数据。

## Interrupt 后怎样恢复

假设系统检查完 100 张发票后停在主管审批处。恢复时，`entrypoint` 函数仍然从开头重新运行；当它再次按相同执行位置调用已经完成的 `@task` 时，Runtime 可以从 Checkpoint 恢复 Task 结果，不再真实检查 100 张发票：

```text
entrypoint 从头运行
→ 再次调用 check_invoice
→ Runtime 找到已完成的 Task 结果
→ Future 直接得到保存结果
→ 回到 interrupt 并使用审批答案继续
```

这不是 CachePolicy 的跨请求通用缓存，而是当前 thread 执行历史中的 Task 结果复用。

直接写在 entrypoint 函数体里的普通代码仍会在恢复时重新执行。因此网络请求、付款、写数据库等非确定性或有副作用操作应包装成 `@task`；即使如此，外部系统仍需幂等键，因为崩溃可能发生在外部成功与 Checkpoint 落盘之间。

启用 Checkpointer 后，`previous` 表示同一 `thread_id` 上一次 entrypoint 调用保存的值，不是当前函数全部局部变量，也不是 Graph API 的完整共享 State。默认返回值也会成为下一次 `previous`；需要分离时可返回：

```python
entrypoint.final(
    value=返回给调用者的报告,
    save=下一次运行需要延续的内部状态,
)
```

## Graph API 与 Functional API 的选择

| 更适合 Graph API | 更适合 Functional API |
|---|---|
| 路线复杂，需要清晰展示拓扑 | 流程天然像普通 Python 程序 |
| 多团队维护不同 Node | 单模块内有较多循环、条件和函数组合 |
| 依赖共享 State 与 Reducer | 主要依赖参数、返回值和 Future |
| 分支、汇合和 HITL 路线要可视化 | 希望较少修改现有代码就获得持久化执行 |
| Node 是权限、治理或恢复边界 | Task 是更自然的可靠性边界 |

两者不是互斥关系。Functional workflow 可以调用编译后的 StateGraph，`@task` 也可以在 StateGraph 执行上下文中使用。常见组合是外层 Graph API 表达长期业务阶段，某个 Node 内部用普通 Runnable 或 Functional API 完成局部动态任务。

## 常见误区

1. `Send` 数量动态，不等于并发无限；必须设置并发、限流和预算。
2. Send 的自定义 `arg` 不会自动包含完整父 State；Worker 需要什么就显式传什么。
3. 并行结果顺序不稳定；需要稳定顺序时保留业务 ID 并在汇总阶段排序。
4. Functional API 隐藏图结构，不等于没有 Pregel、Channel 或 Checkpoint。
5. entrypoint 的普通代码会在恢复时重放，副作用不能随意直接写在函数体里。
6. `previous` 是同 thread 上次保存值，不是 Store、Memory 或完整 checkpoint 快照。
7. Functional API 更简洁，不代表所有复杂工作流都应该放弃显式 Graph；可视化和治理边界也是生产需求。

## 面试回答

> Dynamic Send 用于运行时动态 fan-out。路由函数或 Command 产生多个 `Send(node, arg)`，Runtime 在下一轮为目标 Node 创建多个独立 Task，各 Task 接收不同输入，并在 barrier 后通过 Reducer 汇合结果。Functional API 使用 `@entrypoint` 和 `@task`，让开发者用普通 Python 条件、循环和 Future 编排工作流，同时复用 Pregel Runtime、Checkpoint、Retry、Cache、Timeout 和 Interrupt。Send 更适合保留显式 Graph 拓扑和共享 State，Functional API 更适合以函数调用和局部数据流为中心的动态流程。

## QA / 讨论记录

### Q: Functional API 是不是另一套不使用 Pregel 的轻量框架？

> **状态**: verified
> **来源**: source-code / discussion

A: 不是。`@entrypoint` 在内部构造并返回 Pregel workflow，`@task` 通过 Runtime 提供的 call 机制调度任务。它与 Graph API 的主要差异是用户面对的编程模型，而不是底层换成了另一套执行引擎。

### Q: Functional API 恢复时，整个 Python 函数是否从断点所在代码行继续？

> **状态**: verified
> **来源**: source-code / tests / discussion

A: 不是。entrypoint 从开头重新执行，已完成的 `@task` 结果可从 Checkpoint 复用。普通函数体代码仍会重跑，所以外部副作用应放进 Task 并设计幂等与对账。
