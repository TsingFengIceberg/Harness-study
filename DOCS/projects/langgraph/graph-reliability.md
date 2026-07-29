# LangGraph Graph 可靠性策略

> **日期**: 2026-07-29 | **状态**: draft | **涉及版本**: LangGraph `30c4d58`

## 相关文档与源码

- [StateGraph 基础](state-graph.md)
- [Pregel Channel 与任务调度](pregel-runtime.md)
- [Checkpoint Persistence、History 与 Time Travel](checkpoint-persistence.md)
- [Interrupt、Command 与 HITL](interrupt-command-hitl.md)
- [幂等键概念底座](../../concepts/idempotency.md)
- Node 策略声明与图级默认值：[state.py](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py)
- `RetryPolicy`、`TimeoutPolicy` 与 `CachePolicy`：[types.py](../../../submodules/langgraph/libs/langgraph/langgraph/types.py)
- Node attempt、Timeout 与 Retry 执行：[pregel/_retry.py](../../../submodules/langgraph/libs/langgraph/langgraph/pregel/_retry.py)
- Runtime 错误类型：[errors.py](../../../submodules/langgraph/libs/langgraph/langgraph/errors.py)
- Retry、Timeout 与 Error Handler 测试：[test_retry.py](../../../submodules/langgraph/libs/langgraph/tests/test_retry.py)

## 核心结论

> **精髓：Graph 可靠性不是“失败就重试”，而是先识别失败类型，再决定重试、降级、暂停、终止、恢复还是人工介入。**

LangGraph 的可靠性不是一个开关，而是一组分层机制：

```text
RetryPolicy       → 临时技术故障后是否重做当前 Node attempt
TimeoutPolicy     → 一次 Node attempt 最多运行多久、多久无进展
Error Handler     → Retry 耗尽后怎样记录失败、降级或改道
CachePolicy       → 相同计算能否跳过真实执行并复用结果
Recursion Limit   → Graph 循环失控时的最后保险丝
Checkpoint        → 进程中断后怎样恢复 Graph 运行现场
幂等键与对账      → 怎样保护 Graph 之外的付款、出票等副作用
预算与观察        → 怎样限制总成本并知道可靠性策略是否真的有效
```

前五项主要解决 Graph Runtime 内部的执行控制；Checkpoint 解决恢复；幂等键、事务、outbox 和外部状态查询解决 Runtime 无法单独保证的业务一致性。

## 贯穿场景：企业差旅预订

使用下面的 Graph 贯穿全部机制：

```text
load_policy
→ search_flights
→ compare_options
→ request_approval
→ book_flight
→ notify_user
```

这些 Node 看起来都可能“失败”，但失败含义完全不同：

| 失败 | 性质 | 正确方向 |
|---|---|---|
| 航班接口短暂返回 503 | 临时技术故障 | 有限 Retry |
| 航班接口一直卡住 | 执行时间异常 | Timeout 后再判断是否 Retry |
| 供应商长期不可用 | 主路径不可用 | Error Handler 转人工预订 |
| 员工没有预订权限 | 确定性业务拒绝 | 不 Retry，终止或请求授权 |
| 用户拒绝审批 | 正常业务结果 | 写入 State 后结束，不应视为技术异常 |
| 出票请求超时，结果未知 | 副作用状态不确定 | 用幂等键查询或对账，不能盲目重做 |
| Agent 不断修改条件并搜索 | 流程失控 | 业务退出条件、预算与 Recursion Limit |
| 服务在审批等待期间重启 | 运行中断 | Checkpoint + 同一 `thread_id` 恢复 |

可靠性设计的第一步因此不是填写重试次数，而是建立失败分类。

## Node 策略在什么位置起作用

`StateGraph.add_node()` 可以为单个 Node 设置 `retry_policy`、`cache_policy`、`error_handler` 和 `timeout`。`StateGraph.set_node_defaults()` 可以设置当前图的默认策略，Node 显式配置优先于图级默认值。

一次普通 Node 的处理顺序可概括为：

```text
Runtime 准备 Graph Task
→ 如果配置 Cache，先根据输入计算 key 并查询
→ 未命中才开始一次 Node attempt
→ TimeoutPolicy 监控这一次 attempt
→ Node 成功，产生 State / Command 写入
→ Node 抛出普通异常，按 RetryPolicy 判断是否再次 attempt
→ Retry 不匹配或耗尽，进入 Error Handler
→ Handler 返回更新或 Command，Graph 继续
→ 没有 Handler 或 Handler 失败，异常向整个 run 冒泡
```

图级默认值还有三个容易忽略的边界：

1. 默认策略只属于当前图，不自动继承到 Subgraph；子图需要自己配置。
2. 默认 Retry 和 Timeout 也适用于 Error Handler Node。
3. 默认 Cache 和 Error Handler 只适用于普通 Node；Handler 不缓存，也不能捕获自己或其他 Handler 的失败。

## RetryPolicy：只处理值得再试的故障

`RetryPolicy` 的主要字段是：

| 字段 | 当前默认值 | 含义 |
|---|---:|---|
| `initial_interval` | `0.5` 秒 | 第一次重试前等待多久 |
| `backoff_factor` | `2.0` | 后续等待时间的增长倍数 |
| `max_interval` | `128.0` 秒 | 单次等待的最大值 |
| `max_attempts` | `3` | 最大 attempt 数，包含第一次调用 |
| `jitter` | `True` | 是否加入随机抖动，降低重试风暴 |
| `retry_on` | 默认异常判断器 | 哪类异常值得重试，可用异常类型、类型序列或谓词 |

假设 `search_flights` 第一次返回 503，Runtime 会捕获异常、找到第一个匹配的 RetryPolicy、等待后重新执行整个 Node。若 `max_attempts=3`，总共最多执行三次，而不是“第一次加三次重试”。指数退避让等待间隔逐步增加；jitter 让大量同时失败的 Graph 不会在完全相同的时间再次冲击供应商。

适合 Retry 的通常是网络抖动、限流、短暂 5xx、连接中断和可恢复的超时。不适合 Retry 的通常是参数错误、权限不足、业务规则拒绝、余额不足、用户拒绝以及确定性代码错误。生产代码最好通过 `retry_on` 明确本 Node 的异常分类，不要把所有异常都当作瞬时故障。

当一个 Node 配置多个 RetryPolicy 时，Runtime 使用第一个匹配的策略。因此策略顺序也是行为的一部分，例如可分别给限流和普通网络故障配置不同退避时间。

## TimeoutPolicy：约束一次 attempt

Retry 回答“失败以后是否再试”，Timeout 回答“这一次最多等多久”。

`TimeoutPolicy` 有两个互不替代的时间维度：

- `run_timeout` 是单次 attempt 的硬总时限。即使 Node 持续汇报进度，达到总时限仍超时。
- `idle_timeout` 是单次 attempt 最长允许多久没有可观察进展。持续有有效进度时，它可以运行得比 idle timeout 更久。

`idle_timeout` 的刷新方式由 `refresh_on` 控制：

- `auto`：Graph 写入、stream、子任务调度、LangChain callback 和显式 heartbeat 等标准进度可以刷新。
- `heartbeat`：只有 Node 显式调用 `runtime.heartbeat()` 才刷新，适合不能把普通日志或回调当成真实进展的严格任务。

Timeout 超过后产生 `NodeTimeoutError`，随后仍由 RetryPolicy 决定是否重试。也就是说：

```text
Timeout 负责把“卡住”转成明确失败
Retry 负责决定这个失败是否值得再做一次
```

当前实现依赖 asyncio 协作取消，因此只对 async Node 提供可靠的 Node timeout。同步 `time.sleep()`、阻塞 I/O 或占住 GIL 的 CPU 计算不能在同一进程内被安全及时取消；这类工作应放入支持超时和隔离的外部 Worker、任务队列或独立进程。

## Error Handler：Retry 之后的降级路径

Error Handler 是一个由 Runtime 调度的特殊 Node。普通 Node 的匹配 RetryPolicy 耗尽后，Handler 可以获得失败 Node 的 State 和 `NodeError` 上下文，其中包含来源 Node 与原异常。

Handler 可以返回普通 State 更新：

```text
flight_search_status = unavailable
failure_reason = supplier_timeout
needs_manual_booking = true
```

它也可以返回 `Command`，把状态更新和动态路由一起交给 Runtime，例如跳到 `manual_booking_queue`。因此 Handler 的本质不是“吞掉异常”，而是把技术失败翻译成 Graph 可以继续处理的业务状态或降级路线。

Error Handler 的边界同样重要：

- Handler 自己抛错时，整个 run 失败；不能形成 Handler 套 Handler 的无限兜底。
- `GraphInterrupt` 等 Graph 控制流信号不能被普通 Error Handler 当作业务异常吞掉。
- 父图可以给“整个 Subgraph 作为一个 Node”配置 Handler，从父图边界处理子图向外冒出的普通失败。
- Handler 能让 Graph 流程继续，不代表外部失败已经被修复；仍需保存错误原因、attempt、外部请求 ID 和审计信息。

## CachePolicy：复用计算，不是恢复执行

`CachePolicy` 使用 `key_func` 根据 Node 输入生成 key，并通过 `ttl` 控制缓存有效期。默认 key 会序列化并散列 Node 输入。只有在 `compile(cache=...)` 提供实际 Cache 后端时，Node 缓存才有存取位置。

适合缓存的是无副作用、相同输入应得到可复用结果的昂贵计算，例如稳定政策解析、确定性格式转换、固定版本索引上的检索或模型结果。付款、出票、发消息、创建工单、实时余额和实时权限检查通常不适合缓存。

Cache key 必须覆盖所有会改变结果的维度：

```text
业务输入
+ tenant / user / permission scope
+ Prompt 与模型版本
+ 政策或知识库索引版本
+ 工具配置与语言
```

否则“命中”可能意味着复用了其他租户、旧 Prompt 或旧索引的错误答案。

> **Cache 解决“相同计算不要再做”，Checkpoint 解决“同一个 thread 执行到了哪里以及如何恢复”。**

## Recursion Limit、业务退出条件与预算

带回边的 Graph 可能不断执行“搜索航班 → 不满意 → 修改条件 → 再搜索”。超过 Graph 允许的 step 数会抛出 `GraphRecursionError`，防止错误循环无限运行。

但 Recursion Limit 只是最后保险丝，不能代替业务退出条件。生产 Graph 还应在 State 或治理层记录和限制：

```text
iteration_count
tool_call_count
model_call_count
total_tokens
elapsed_time
estimated_cost
```

达到预算后需要有明确路线：正常结束、返回当前最佳结果、请求用户缩小范围、转人工或者记录失败。盲目提高 `recursion_limit` 只会让错误循环运行得更久、更贵。

## Superstep、Pending Writes 与 Checkpoint

假设同一 superstep 并行查询航班、酒店和天气，它们读取同一个 State 快照。某项失败时，Runtime 不能把这一轮当成已经完整提交的新 State。

配置 Checkpointer 后，LangGraph 可以把成功 Task 的 pending writes 与 checkpoint 现场关联保存。恢复时可复用已经成功的 Task 结果，避免无意义地重复执行整轮工作；失败 Task 则按恢复与 Retry 规则重新处理。

这解决的是 Graph 内部任务恢复，却没有覆盖下面这个崩溃窗口：

```text
外部供应商已经出票成功
→ Graph 尚未来得及保存“出票成功”的 checkpoint
→ 进程崩溃
```

恢复后，Graph 只知道当前 Task 没有完成记录，却不能仅凭 checkpoint 判断供应商是否已出票。因此 Checkpoint 提供 at-least-once 恢复基础，不自动提供外部副作用的 exactly-once。

## 副作用 Node：幂等键、查询与对账

`book_flight`、付款、发券和发消息等 Node 在配置 Retry 前，必须先设计外部一致性：

1. 使用稳定的幂等键标识最小不可重复业务动作。
2. 同一个 key 重试时校验 request hash，避免相同 key 携带不同请求内容。
3. 请求超时且结果未知时，先按幂等键查询外部状态，再决定继续等待、补偿还是重试。
4. 数据库写入与消息发布需要时使用事务、outbox / inbox 或唯一约束。
5. Time travel / fork 产生新业务动作时，不应错误复用旧分支的副作用 key。

Graph Retry 只能决定“再次调用 Node”，不能替外部系统定义同一业务动作，也不能自动完成资金和资源对账。

## Node Retry 与 Middleware Retry 的重试乘法

高层 Agent 还可能在 LangChain middleware 中对单次模型调用或 Tool 调用重试：

```text
Graph Node Retry
└── Node 内部的 Model / Tool Middleware Retry
```

如果 middleware 最多调用模型三次，Graph Node 又最多执行三次，最坏情况下模型调用会接近九次。副作用 Tool 被包在多层 Retry 中时风险更高。

责任边界应明确：

| 层级 | 负责的问题 |
|---|---|
| Model / Tool middleware | 一次模型或 Tool 调用附近的瞬时故障、fallback 与治理 |
| Node RetryPolicy | 整个 Graph Task 是否重新执行 |
| Error Handler | Task 最终失败后怎样降级、记录或改道 |
| Checkpoint | 整个 thread 如何恢复运行现场 |
| 幂等键与对账 | 外部副作用怎样避免重复并处理未知状态 |

配置多层 Retry 时必须计算总 attempt 上限，而不是分别看每一层都觉得“三次不多”。

## 差旅 Graph 的生产策略矩阵

| Node | 推荐策略 | 关键原因 |
|---|---|---|
| `load_policy` | Cache；失败时终止或转配置修复 | 同版本政策解析可复用，错误政策不能继续预订 |
| `search_flights` | run / idle Timeout + 有限 Retry + 降级 Handler | 外部查询有瞬时故障，也可能长期不可用 |
| `compare_options` | Cache + 模型次数、Token 和时间预算 | 无副作用但成本高，需防止 Agent 反复比较 |
| `request_approval` | Interrupt + Checkpoint | 这是等待人工，不是异常或 Timeout Retry |
| `book_flight` | 幂等键 + 外部状态查询 + 谨慎 Retry | 出票是不可随意重复的外部副作用 |
| `notify_user` | 幂等消息 ID + Retry + 失败队列 | 通知失败不应回滚已经成功的出票 |

还应通过 stream、trace、日志或指标记录：Node attempt 数、异常分类、退避时间、Timeout 类型、Cache 命中率、Handler 路由、checkpoint 恢复次数、幂等冲突和最终业务结果。没有这些观察数据，就无法判断策略是在恢复业务，还是在隐藏错误和放大成本。

## 面试回答

> LangGraph 的可靠性是分层实现的：RetryPolicy 处理值得重试的临时故障，TimeoutPolicy 约束单次 Node attempt，Error Handler 在重试耗尽后把错误转成降级状态或路由，CachePolicy 避免相同计算重复执行，Recursion Limit 和业务预算防止循环失控，Checkpoint 保存 Graph 现场并支持恢复。外部付款、出票等副作用仍必须依赖幂等键、状态查询、事务或对账。核心不是统一重试，而是先分类失败，再选择重试、降级、暂停、终止、恢复或人工介入。

## QA / 讨论记录

### Q: Graph 可靠性是不是给所有 Node 都配置三次重试？

> **状态**: verified
> **来源**: source-code / discussion

A: 不是。Retry 只适合可恢复的临时故障。业务拒绝、参数错误和确定性 Bug 不应重试；副作用不明确时要先查询和对账；等待人工应使用 Interrupt；主路径长期不可用应进入 Error Handler 降级。统一重试既可能放大流量和成本，也可能制造重复付款或出票。

### Q: Checkpoint 能否保证一次付款绝不重复？

> **状态**: verified
> **来源**: source-code / discussion

A: 不能。Checkpoint 保存 Graph Runtime 现场和 pending writes，但外部系统可能已经完成付款而 Graph 尚未保存成功记录。恢复执行仍需幂等键、外部状态查询、事务或对账处理该崩溃窗口。
