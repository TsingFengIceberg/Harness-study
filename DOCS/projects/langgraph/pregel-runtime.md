# 第三课：Pregel Channel 与任务调度

> **日期**: 2026-07-28 | **状态**: draft | **涉及版本**: `langgraph@30c4d58db86455128e42ddec96b1ba53c553ba22`

## 相关文档

- [LangGraph 学习入口](README.md)
- [第二课：LangGraph StateGraph 基础](state-graph.md)
- [LangChain / LangGraph 面试学习路线](../langchain/interview-roadmap.md)
- 源码：[Pregel 主体](../../../submodules/langgraph/libs/langgraph/langgraph/pregel/main.py)
- 源码：[Pregel 调度算法](../../../submodules/langgraph/libs/langgraph/langgraph/pregel/_algo.py)
- 源码：[Pregel loop](../../../submodules/langgraph/libs/langgraph/langgraph/pregel/_loop.py)
- 源码：[Channel 基类](../../../submodules/langgraph/libs/langgraph/langgraph/channels/base.py)
- 源码：[Checkpoint 基础类型](../../../submodules/langgraph/libs/checkpoint/langgraph/checkpoint/base/__init__.py)

## 本课路线

```text
State schema 与 Channel 的层级边界
→ 数据 Channel 与隐藏控制 Channel
→ Runtime 如何生成下一轮任务
→ channel_versions 与 versions_seen
→ 回环中的版本推进
→ 版本表现形式与使用边界
→ pending writes、checkpoint 与 durable execution
```

当前学习进度：

- [ ] Channel 的声明、编译与运行时对象边界：已讨论，但用户尚未完全理解，待换角度回看；
- [x] Runtime 根据触发更新生成下一轮任务；
- [x] `channel_versions` 与 `versions_seen` 的新旧判断；
- [x] 回环中的触发版本推进；
- [x] 版本值的表现形式与非业务语义；
- [x] pending writes 与 checkpoint；
- [x] 同一 thread 下的 checkpoint 历史；
- [x] durable execution 与失败恢复。

## 第一小节：Channel 在哪一层

准确的分层结论是：Channel 属于 LangGraph 的构建、编译和运行时机制，不是业务代码中的 State 本身；但数据 Channel 会根据用户编写的 State schema 自动生成。

```text
State schema
= 用户编写的逻辑数据声明和设计图

Channel
= LangGraph 根据设计图建立的运行时存储与通信设施

State snapshot
= Runtime 从数据 Channels 读取并组装出的当前逻辑状态
```

### 从声明到执行的生命周期

用户先声明：

```python
class State(TypedDict):
    status: str
    notes: Annotated[list[str], operator.add]
```

这段代码只说明图中存在什么字段，以及字段采用什么合并规则。创建 `StateGraph(State)` 时，schema 会被解析为数据 Channel：

```text
status → LastValue
notes  → BinaryOperatorAggregate(operator.add)
```

`_get_channels()` 会读取 schema 注解；普通字段回退为 `LastValue`，带二元 Reducer 的字段映射为 `BinaryOperatorAggregate`。见 [state.py:1804-1858](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py#L1804-L1858) 和 [state.py:1890-1907](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py#L1890-L1907)。

注册 Node 和 Edge 时，Builder 保存计算单元和图结构。`compile()` 产生 `CompiledStateGraph`，复制数据 Channel，并补充 Edge、conditional edge 和 barrier 所需的隐藏控制 Channel。调用 `invoke()` 后，Runtime 才维护某次真实运行中的 Channel 值、版本、pending writes 和任务进度。

| 层级 | 主要内容 | 负责方 |
|---|---|---|
| 业务声明 | State 字段、类型、Reducer 注解 | 用户代码 |
| Builder | Node、Edge、schema 解析出的数据 Channel | `StateGraph` |
| 编译图 | PregelNode、Trigger Channel、Barrier Channel | `compile()` |
| 运行实例 | Channel 当前值、版本、pending writes、Tasks | Pregel Runtime |
| Node 输入 | Runtime 从数据 Channel 组装的 State 快照 | Runtime 提供 |

Node 收到的是 State 的逻辑视图，不会直接拿到 `LastValue`、`BinaryOperatorAggregate`、`branch:to:*`、channel version 或 pending writes。

### 当前理解状态

> **待回看**：这一分层已经完成源码核验和第一轮讲解，但用户仍未完全建立“State 声明、构建期 Channel、编译期控制 Channel、invoke 期间运行状态”的清晰直觉。后续不能把这一点标记为已掌握，应使用新的端到端真实场景重新解释。

## 第二小节：数据 Channel 与控制 Channel

Channel 可以理解为带类型、更新规则、生命周期和 checkpoint 能力的运行时信箱。`BaseChannel` 定义了以下核心能力：

```text
get()        → 读取当前值
update()     → 接收本轮的一组更新并计算新值
checkpoint() → 生成可序列化快照
consume()    → 通知 Channel：订阅任务已经运行
finish()     → 通知 Channel：本次 run 即将结束
```

见 [base.py:17-104](../../../submodules/langgraph/libs/langgraph/langgraph/channels/base.py#L17-L104)。

### 数据 Channel

数据 Channel 与业务 State 字段对应：

```text
State.status ↔ status Channel
State.notes  ↔ notes Channel
```

它们保存和合并业务数据。普通字段使用 `LastValue`，Reducer 字段可以使用 `BinaryOperatorAggregate`。

### 隐藏控制 Channel

不是所有 Channel 都对应 State 字段。编译图会为普通 Node 创建类似下面的内部 Channel：

```text
branch:to:approve_order
```

目标 Node 把该 Channel 放进自己的 `triggers`；来源 Node 完成后，Edge writer 向目标 trigger Channel 写入信号。见 [state.py:1437-1534](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py#L1437-L1534) 和 [state.py:1537-1561](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py#L1537-L1561)。

两类 Channel 的职责可以概括为：

```text
Trigger Channel
→ 告诉 Runtime：什么时候执行这个 Node

State Channel
→ 告诉 Node：执行时读取什么业务数据
```

多起点 Edge 还会创建 `NamedBarrierValue`，用于收集多个前置 Node 的完成标识；conditional edge 则只向被选中目标的 `branch:to:*` Channel 写入信号。

用餐厅类比：State 是整块订单白板，数据 Channel 是每个栏目的管理员，Trigger Channel 是通知岗位开工的呼叫铃，Barrier Channel 是必须集齐多张完成牌的托盘，Runtime 是更新白板并根据铃声安排岗位的经理。

## 第三小节：Runtime 如何生成下一轮任务

Runtime 不需要每轮无差别扫描所有 Node。编译后的 Pregel 会建立一张反向索引：

```text
trigger_to_nodes
= Trigger Channel → 订阅该 Channel 的 Node 列表
```

索引由每个 PregelNode 的 `triggers` 生成，见 [main.py:4175-4181](../../../submodules/langgraph/libs/langgraph/langgraph/pregel/main.py#L4175-L4181)。

假设 `receive_order` 有两条普通 Edge：

```python
builder.add_edge("receive_order", "fraud_check")
builder.add_edge("receive_order", "inventory_check")
```

来源 Node 完成后会产生两个控制流写入：

```text
branch:to:fraud_check
branch:to:inventory_check
```

本轮 Update 完成后，Runtime 根据 `updated_channels` 查询 `trigger_to_nodes`，得到下一轮候选 Node，再为符合条件的候选准备输入、Config、Runtime 和实际 Task。见 [_algo.py:471-511](../../../submodules/langgraph/libs/langgraph/langgraph/pregel/_algo.py#L471-L511)。

```text
本轮 Node 执行完成
→ 收集 State 更新和控制流写入
→ barrier 处统一应用
→ 得到本轮更新的 Trigger Channels
→ 通过 trigger_to_nodes 找到候选 Node
→ 构造下一轮 Tasks
```

普通 Edge 可以同时触发多个目标；conditional edge 只写入实际选中的目标 Channel；Barrier Channel 只有在收齐所有前置完成标识并变为 available 后，才会触发汇合 Node；回边则再次写入前面 Node 的 Trigger Channel，使它在后续轮次重新成为任务。

> **本节精髓：Edge 声明路线，Node 完成后产生控制流写入，Runtime 在 barrier 后通过 `trigger_to_nodes` 找到订阅者并创建下一轮 Task。**

## 第四小节：`channel_versions` 与 `versions_seen`

Runtime 还必须判断一个可用的 Trigger 是新通知，还是目标 Node 已处理过的旧通知。

```text
channel_versions
= 每个 Channel 当前更新到了哪个版本

versions_seen
= 每个 Node 已处理到各 Trigger Channel 的哪个版本
```

任务准备阶段的核心判断是：Trigger Channel 可用，并且当前版本大于目标 Node 已见版本，才创建 PULL Task。见 [_algo.py:598-617](../../../submodules/langgraph/libs/langgraph/langgraph/pregel/_algo.py#L598-L617) 和 [_algo.py:1260-1277](../../../submodules/langgraph/libs/langgraph/langgraph/pregel/_algo.py#L1260-L1277)。

```text
Trigger 当前版本 > Node 已见版本
→ 新通知，创建 Task

Trigger 当前版本 == Node 已见版本
→ 旧通知，不重复创建 Task
```

例如：

```text
branch:to:fraud_check 当前版本 = v4
fraud_check 已见版本 = v3
→ v4 > v3，执行

执行完成后：
fraud_check 已见版本 = v4

没有新写入时：
当前 v4 == 已见 v4
→ 不重复执行
```

Channel value 和 Channel version 不是同一概念：value 是当前业务数据或控制信号，version 是 Runtime 判断这份状态是否比 Node 已处理内容更新的顺序标记。

## 第五小节：版本何时推进

版本不会在 `add_edge()`、`compile()`、Node 开始执行或 Node 刚返回时立即变化。Node 返回后，写入先留在任务的 pending writes；等本轮任务结束，Runtime 进入 Update 阶段，`apply_writes()` 才真正处理。

```text
Node return
→ 产生 pending write
→ Channel version 暂时不变

本轮 barrier
→ apply_writes()
→ Channel.update(values)
→ Channel 报告状态发生变化
→ Runtime 写入 next_version
```

`apply_writes()` 会先记录本轮 Tasks 已处理的 trigger versions，再计算 `next_version`、按 Channel 分组 pending writes，并调用各 Channel 的 `update()`；只有返回 `True` 的 Channel 才推进版本。见 [_algo.py:255-336](../../../submodules/langgraph/libs/langgraph/langgraph/pregel/_algo.py#L255-L336)。

假设 `A → B`：

```text
执行 A 前：
branch:to:B 当前版本 = v3
B 已见版本 = v3

A 完成：
pending write = (branch:to:B, None)
版本仍是 v3

Update 阶段：
branch:to:B.update([None]) 返回 True
版本写为 v4，Channel available

下一轮 Plan：
v4 > B 已见 v3
→ 创建 B Task
```

普通 Edge 的触发 Channel 通常使用 `EphemeralValue`：收到信号时变为 available，下一 step 没有新写入时会清空。清空也可能推进内部版本，但 Channel 已不可用，因此不会触发任务。见 [ephemeral_value.py:17-74](../../../submodules/langgraph/libs/langgraph/langgraph/channels/ephemeral_value.py#L17-L74)。

## 第六小节：回环中的版本推进

回环不需要特殊的版本算法。它只是后面的 Node 再次向前面 Node 的 Trigger Channel 写入新信号。

```text
check_order → enrich_order → check_order
```

一次可能的逻辑时间线是：

```text
branch:to:check_order = v1
→ check_order 第一次执行
→ versions_seen[check_order] = v1

branch:to:enrich_order = v2
→ enrich_order 执行
→ versions_seen[enrich_order] = v2

branch:to:check_order = v3
→ v3 > check_order 已见 v1
→ check_order 第二次执行
```

具体版本值不保证按单个 Channel 连续递增，因为同一轮可能还有其他 Channel 更新或临时 Channel 清空。关键条件始终是：新的可用 Trigger 版本大于目标 Node 的已见版本。

自环 `A → A` 同理：A 执行前处理 v1；Update 阶段先记录 A 已见 v1，再把 A 产生的新自环写入应用为 v2；下一轮 v2 大于已见 v1，A 再次执行。

循环结束也不是因为版本达到某个特殊值，而是 conditional edge 路由到 `END`，不再向循环节点写入新 Trigger，最终没有下一轮 Task。

Channel version 不能代替业务循环计数：

```text
Channel version
→ Runtime 内部判断触发新旧

State.retry_count
→ 业务上已经重试多少次以及何时退出
```

## 第七小节：版本的表现形式和边界

`ChannelVersions` 允许 `str | int | float`。默认 `BaseCheckpointSaver` 可以使用从 `1` 开始递增的整数；具体 checkpointer 也可以生成带单调递增前缀的字符串。见 [checkpoint/base/__init__.py:692-714](../../../submodules/langgraph/libs/checkpoint/langgraph/checkpoint/base/__init__.py#L692-L714) 和 [checkpoint/memory/__init__.py:619-627](../../../submodules/langgraph/libs/checkpoint/langgraph/checkpoint/memory/__init__.py#L619-L627)。

Runtime 只依赖以下性质：

```text
版本可比较
并且新版本单调大于旧版本
```

当前 `apply_writes()` 在一个 superstep 中先计算一次 `next_version`，本轮多个发生变化的 Channels 可能共享同一版本标记。因此 version 更像运行时更新顺序 token，不一定等于某个 Channel 自己累计写过多少次。

版本推进也不只代表新的业务值写入。只要 Channel 内部状态真正改变并由 `update()`、`consume()` 或 `finish()` 报告变化，版本就可能推进；任务判断还会检查 Channel 是否 available，所以临时 Trigger 被清空后即使版本变化也不会误触发。

不要混淆以下编号：

| 概念 | 职责 |
|---|---|
| Channel version | 判断 Channel 状态是否出现新变化 |
| `versions_seen` | 记录每个 Node 已处理到哪个 Trigger 版本 |
| Checkpoint ID | 标识一次持久化快照 |
| Superstep number | 表示 Pregel 执行到第几轮 |
| State 中的 `retry_count` | 业务循环次数 |
| Message ID | 标识和匹配具体 Message |

业务代码不应依赖 Channel version 的具体格式或数值；如果需要计数、排序或退出条件，应显式放进 State。

## 第八小节：Pending writes

Pending writes 是 Node 已经计算出来、但当前 superstep 尚未统一提交到正式 State Channels 的临时写入。

```text
Node 返回 Partial<State>
→ 形成 Task writes / pending writes
→ 当前正式 State 暂时不变
→ barrier 等待本轮任务完成
→ apply_writes() 按 Channel 分组并统一应用
→ 形成下一版 State
```

概念上一份持久化 pending write 包含：

```text
哪个 Task 产生
写入哪个 Channel
写入什么值
```

源码类型是 `(task_id, channel_name, value)`，见 [checkpoint/base/__init__.py:31](../../../submodules/langgraph/libs/checkpoint/langgraph/checkpoint/base/__init__.py#L31)。

例如两个并行检查分别返回：

```python
# fraud_check
{"risk_level": "high", "notes": ["风险检查完成"]}

# inventory_check
{"in_stock": True, "notes": ["库存检查完成"]}
```

Runtime 先保留四份写入；等本轮完成后按 Channel 分组：

```text
risk_level → ["high"]
in_stock   → [True]
notes      → [["风险检查完成"], ["库存检查完成"]]
```

再由 `LastValue` 或 Reducer 处理。这样即使 `fraud_check` 先完成，仍在执行的 `inventory_check` 也不会提前看到它的结果，同一 superstep 始终读取一致快照。

必须区分三个时刻：

```text
Node return
→ 业务计算完成

Pending write 已记录
→ 结果存在，但尚未进入正式 State

apply_writes 完成
→ Channels 更新，下一版 State 正式形成
```

Runner 在任务成功、失败、取消或 interrupt 时会把相应 writes 或控制信息交给 checkpointer，见 [_runner.py:574-614](../../../submodules/langgraph/libs/langgraph/langgraph/pregel/_runner.py#L574-L614)。正常 superstep 完成后，`after_tick()` 调用 `apply_writes()`，清空 pending writes 并创建 loop checkpoint，见 [_loop.py:683-725](../../../submodules/langgraph/libs/langgraph/langgraph/pregel/_loop.py#L683-L725)。

如果同一轮部分任务成功、部分任务失败，正式 State 可以保持在上一 checkpoint；成功任务的 writes 则可以单独保存。恢复时 `_reapply_writes_to_succeeded_nodes()` 会把成功 Channel writes 恢复到对应 Task，同时跳过 error、interrupt 和 resume 控制信息，使失败或中断任务继续处理。见 [_loop.py:736-750](../../../submodules/langgraph/libs/langgraph/langgraph/pregel/_loop.py#L736-L750)。

Pending writes 只管理 LangGraph 内部 State 写入，不能回滚 Node 已经执行的支付、短信、邮件或其他外部副作用。生产 Node 仍需使用幂等键、事务或 outbox 防止恢复和重试造成重复操作。

> **本节精髓：Node 返回只产生待提交写入；只有整个 superstep 完成并执行 `apply_writes()`，这些结果才统一进入正式 Channels。Pending writes 同时为一致快照、Reducer 合并和失败恢复提供中间层。**

## 第九小节：Checkpoint、Checkpointer 与 `thread_id`

Checkpoint 是某一时刻的运行存档；Checkpointer 是负责保存和读取存档的存储组件；`thread_id` 是定位一组工作流存档的主键。

### State 不是完整运行存档

State 只能说明当前业务数据，例如：

```python
{
    "decision": "waiting_for_evidence",
    "evidence_round": 1,
}
```

它不能单独说明哪些 Node 已执行、哪些 Trigger 已处理、下一轮该执行谁。Checkpoint 还包括：

```text
id               → 当前 checkpoint 的唯一标识
ts               → 保存时间
channel_values   → 当时的 Channel 值
channel_versions → 各 Channel 当时的版本
versions_seen    → 每个 Node 已处理到各 Trigger 的哪个版本
updated_channels → 这次存档中刚更新的 Channels
```

见 [checkpoint/base/__init__.py:90-124](../../../submodules/langgraph/libs/checkpoint/langgraph/checkpoint/base/__init__.py#L90-L124)。`CheckpointTuple` 再将 Checkpoint 与 Config、Metadata、父配置和 pending writes 组合，见 [checkpoint/base/__init__.py:136-146](../../../submodules/langgraph/libs/checkpoint/langgraph/checkpoint/base/__init__.py#L136-L146)。

### Checkpointer 是存储驱动

`BaseCheckpointSaver` 负责读取、写入、列举 checkpoint 和保存 pending writes。配置 checkpointer 后，调用图时需要提供 `thread_id`；源码将其定义为保存和检索 checkpoints 的主键。见 [checkpoint/base/__init__.py:176-205](../../../submodules/langgraph/libs/checkpoint/langgraph/checkpoint/base/__init__.py#L176-L205)。

```python
checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)

config = {
    "configurable": {
        "thread_id": "refund:R-001",
    }
}
```

`InMemorySaver` 适合测试和教学，但进程退出后通常无法跨进程恢复；生产 durable execution 需要数据库等真正持久化的 saver。仅传 `thread_id` 而不配置 checkpointer，不会自动产生持久化能力。

### 一个 thread 为什么有多个 checkpoint

`thread_id` 标识整条工作流执行线，checkpoint 则是这条执行线在不同时间点的快照：

```text
thread_id = refund:R-001

C0：收到申请
→ C1：字段校验完成
→ C2：并行检查完成
→ C3：暂停等待材料
→ C4：补充材料审核完成
→ C5：人工审批完成
```

可以把 `thread_id` 类比为 Git branch，把 `checkpoint_id` 类比为该分支上的 commit。只提供 `thread_id` 时通常定位这条执行线的最新 checkpoint；同时提供 `checkpoint_id` 时可以定位某个历史快照，具体查看、重放或分支操作取决于调用 API。

一次 `invoke()` 可能经过多个 superstep，因此可以产生多个 checkpoints；同一 thread 也可以跨多次 `invoke()`，例如第一次运行到 interrupt 暂停，第二次使用同一 `thread_id` 恢复并继续追加 checkpoints。

`thread_id` 不等于用户 ID。同一用户的三张退款单应使用三条独立 thread：

```text
user_id = customer-123

thread_id = refund:R-001
thread_id = refund:R-002
thread_id = refund:R-003
```

> **本节精髓：Thread 是随时间推进的工作流历史，Checkpoint 是历史中的一个快照。State 保存业务事实，Checkpoint 还保存 Runtime 继续执行所需的版本与进度。**

## 第十小节：Durable execution 与失败恢复

Durable execution 不保证进程永远不崩，而是让新进程能够根据持久化 checkpoint 和 pending writes 重建执行现场，继续未完成工作。

假设上一份正式存档 C2 表示下一轮要并行执行 A、B、C：

```text
A 成功并保存 writes
B 成功并保存 writes
C 执行时进程崩溃
```

因为整个 superstep 未完成，正式 State 仍停在 C2；A、B 的成功结果可以作为 pending writes 与 C2 关联保存。新进程使用相同 Graph、持久化 Checkpointer 和 `thread_id` 恢复时：

```text
读取 C2 与关联 pending writes
→ 根据版本和 Trigger 重建 A、B、C Tasks
→ 把 A、B 的成功 writes 恢复到对应 Task
→ 重新执行没有成功结果的 C
→ A + B + C 全部就绪后统一 apply_writes()
→ 形成下一版 State 和 Checkpoint C3
```

Runtime 保存的不是旧进程的 Python 调用栈或某个函数第几行，而是可以重建工作的 State、Channel versions、`versions_seen`、pending writes、interrupt / error 信息和任务触发依据。

### Durability 模式

当前版本支持：

| 模式 | 持久化时点 | 主要权衡 |
|---|---|---|
| `sync` | 下一 step 前同步等待保存完成 | 边界最明确，延迟较高 |
| `async` | 下一 step 执行时异步保存上一轮变化 | 默认模式，吞吐与持久化并行 |
| `exit` | Graph 退出时统一保存 | 开销低，中途恢复粒度最弱 |

源码说明见 [main.py:2705-2714](../../../submodules/langgraph/libs/langgraph/langgraph/pregel/main.py#L2705-L2714)。

生产级 durable execution 需要：

1. 真正持久化的 Checkpointer；
2. 恢复时使用同一个 `thread_id`；
3. Graph 定义、Node 名称和 State schema 保持兼容或提供迁移；
4. 外部副作用使用幂等键、去重、事务或 outbox。

Durable execution 不等于外部副作用 exactly once。支付成功后、State 写入保存前如果进程崩溃，恢复可能再次调用支付接口；支付系统必须通过类似 `refund:R-001` 的幂等键返回第一次结果，而不是重复退款。

> **本节精髓：Durable execution 通过 Checkpoint 保存已提交运行状态，通过 pending writes 保留未完成 superstep 中的成功任务结果。新进程据此重建任务并继续执行；外部副作用是否恰好一次，仍需要业务系统提供幂等和事务保障。**

## QA / 讨论记录

### Q: Channel 属于 State 声明还是 Runtime？

> **状态**: verified（源码边界）/ 待回看（学习理解）
> **来源**: source-code / discussion

A: Channel 属于 LangGraph 的构建和运行时机制。用户写 State schema 和 Reducer 声明；`StateGraph` 据此创建数据 Channel，`compile()` 再加入 Edge / barrier 所需的隐藏控制 Channel，`invoke()` 期间 Runtime 维护每次运行的 Channel 值、版本和写入。Node 只看到由数据 Channel 组装出的 State 快照。该源码结论已核验，但用户暂未完全理解，后续不能写成“已掌握”。

### Q: Runtime 为什么不会因旧 Trigger 无限重复执行 Node？

> **状态**: verified
> **来源**: source-code / discussion

A: Runtime 同时检查 Trigger 是否 available，以及其当前版本是否大于目标 Node 的 `versions_seen`。Node 处理过该版本后会更新已见版本；只有后续新的可用版本才能再次触发。回环通过再次写入目标 Trigger 产生新版本，而不是复用旧通知。

### Q: Channel version 能否当作重试次数？

> **状态**: verified
> **来源**: source-code / discussion

A: 不能。版本可能是整数、浮点数或字符串，同一 superstep 的多个 Channel 可能共享版本，而且清空、消费等内部状态变化也可能推进版本。业务重试次数必须显式保存在 State 中。

### Q: 为什么同一个 thread 下可以有多个 checkpoint？

> **状态**: verified
> **来源**: source-code / discussion

A: `thread_id` 标识整条工作流执行线，checkpoint 标识其中某个时间点。一次 `invoke()` 可以包含多个 superstep 并产生多个 checkpoints，同一 thread 也可以跨多次调用继续追加历史。默认恢复通常从最新 checkpoint 继续，特定 `checkpoint_id` 则用于定位历史快照。

### Q: Durable execution 是否保证外部操作 exactly once？

> **状态**: verified
> **来源**: source-code / inference

A: 不保证。LangGraph 能持久化并恢复自己管理的 State、运行进度和 pending writes，但无法自动回滚任意外部支付、短信或数据库副作用。Node 可能在外部调用成功、内部结果持久化前崩溃，因此外部系统仍需使用幂等键、事务或 outbox。

## 下一小节

下一课进入 [Interrupt、Command 与 Human-in-the-loop](interrupt-command-hitl.md)，重点讨论暂停发生在哪里、Checkpoint 如何保存暂停位置、`Command(resume=...)` 如何恢复同一 thread，以及人工决策怎样安全地更新 State 和控制后续路线。
