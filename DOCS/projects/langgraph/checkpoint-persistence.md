# LangGraph Checkpoint Persistence、History 与 Time Travel

> **日期**: 2026-07-29 | **状态**: draft | **涉及版本**: `30c4d58`

## 相关文档与源码

- 前置课程：[Pregel Channel 与任务调度](pregel-runtime.md)、[Interrupt、Command 与 Human-in-the-loop](interrupt-command-hitl.md)
- 子图边界：[Subgraph、Multi-Agent 与父子 Checkpoint](subgraph-multi-agent.md)
- 副作用安全：[幂等键与副作用安全](../../concepts/idempotency.md)
- Checkpoint 基础类型与 saver 接口：[__init__.py](../../../submodules/langgraph/libs/checkpoint/langgraph/checkpoint/base/__init__.py)
- Graph State 查询、历史与更新：[main.py](../../../submodules/langgraph/libs/langgraph/langgraph/pregel/main.py)
- Replay / fork 测试：[test_time_travel.py](../../../submodules/langgraph/libs/langgraph/tests/test_time_travel.py)

## 本课主线

```text
Checkpoint = 可恢复的计算现场，不是旧 Python 调用栈
→ thread_id 标识整条执行线
→ checkpoint_id 标识一个具体历史快照
→ get_state / get_state_history 查询现在与过去
→ replay 从过去继续计算
→ update_state + invoke 从过去 fork 新分支
→ 外部副作用不能被 time travel 撤销
```

## 第一小节：Checkpoint 保存的不是普通 State

Checkpoint 是 Runtime 在执行边界保存的状态机快照。除各 channel 的值外，它还保存 channel version、各 Node 已见版本以及更新信息，使 Runtime 能在恢复时判断哪些任务应执行、哪些写入已应用。`Checkpoint` 类型中的 `channel_values`、`channel_versions`、`versions_seen` 与 `updated_channels` 见 [__init__.py:92-136](../../../submodules/langgraph/libs/checkpoint/langgraph/checkpoint/base/__init__.py#L92-L136)。

```text
State
= 当前业务字段，例如订单、消息、审批结论

Checkpoint
= State + channel version + 调度所需版本信息 + 历史关系
```

这解释了为什么 durable execution 不是冻结 Python 调用栈：进程恢复后，Runtime 从 checkpoint 重建 channel 与待执行任务，再重新调用相关 Node。

## 第二小节：Checkpointer、thread 与快照身份

```text
Checkpointer
= 存取 checkpoint 的适配器

thread_id
= 一整条运行线 / 一个案件编号

checkpoint namespace
= 主图、子图或嵌套实例的目录路径

checkpoint_id
= 某一 namespace 中的具体快照编号
```

配置 Checkpointer 后，`thread_id` 是保存、查询、interrupt resume 与 time-travel 的主键；同一对话或案件复用同一个 `thread_id`，独立运行使用不同 ID，见 [__init__.py:176-201](../../../submodules/langgraph/libs/checkpoint/langgraph/checkpoint/base/__init__.py#L176-L201)。

`BaseCheckpointSaver` 定义了 `get_tuple`、`list`、`put` 与 `put_writes` 等接口：它不仅保存完整 checkpoint，也能关联中间 writes，[__init__.py:239-318](../../../submodules/langgraph/libs/checkpoint/langgraph/checkpoint/base/__init__.py#L239-L318)。`InMemorySaver` 适合测试和调试；生产环境应选择适合持久化、并发、备份与访问控制的 saver。

## 第三小节：暂停、恢复与历史查询

以高风险退款为例：

```text
verify_identity
→ C1
calculate_refund
→ C2
ask_human_approval / interrupt
→ C3，保存暂停现场
Command(resume=...)
→ 从 C3 重建并继续 issue_refund
```

`get_state(config)` 用于取得当前 `StateSnapshot`：包括当前 values、下一批 Task 和 interrupt 等运行状态。`get_state_history(config)` 则按 checkpoint 历史返回多个 `StateSnapshot`，可用于审计、定位错误和选择过去的分叉点；它最终调用 Checkpointer 的 `list()` 并把 tuple 准备成 StateSnapshot，[main.py:1480-1537](../../../submodules/langgraph/libs/langgraph/langgraph/pregel/main.py#L1480-L1537)。

Stream 只负责把“刚发生什么”通知观察者；checkpoint / history 才负责断线、重启或恢复后可靠找回执行事实。

## 第四小节：Replay 不是回滚

从某个历史 snapshot 的 config 调用：

```python
graph.invoke(None, old_snapshot.config)
```

表示从该 checkpoint 的计算现场继续执行后续 Node。若选择的是 `node_b` 前的快照，前面的 `node_a` 不会重跑，`node_b` 会重新执行；当前测试直接验证了这一行为，[test_time_travel.py:75-141](../../../submodules/langgraph/libs/langgraph/tests/test_time_travel.py#L75-L141)。

Replay 不会删除旧分支，更不会撤销该分支已经影响的支付、邮件、工单或外部数据库。它只是重新执行 Graph 的后半段计算。

## 第五小节：Fork 与 `update_state()`

Fork 是从旧 checkpoint 修改部分 State 后继续运行：

```python
fork_config = graph.update_state(
    old_snapshot.config,
    {"refund_amount": 699},
    as_node="calculate_refund",
)
graph.invoke(None, fork_config)
```

`update_state()` 的语义是“把这份更新视为某个 Node 的返回值”；`as_node` 若不明确，Runtime 只会在最后更新 Node 不存在歧义时推断它，[main.py:2515-2537](../../../submodules/langgraph/libs/langgraph/langgraph/pregel/main.py#L2515-L2537)。因此它不是让前端任意改 dict 的接口，而应由可信后端完成权限、字段和业务校验。

原分支仍保留。测试验证了从同一个 checkpoint 创建多个 fork 后，各分支独立运行、互不污染，[test_time_travel.py:143-218](../../../submodules/langgraph/libs/langgraph/tests/test_time_travel.py#L143-L218)。

```text
原分支：退款金额 999 → 原审批 → 原结果
新分支：退款金额 699 → 新审批 / 新结果
```

若从 interrupt 前 replay 或 fork，`interrupt()` 会重新触发，因为 Graph 回到了“尚未提出该问题”的计算位置；旧人工回答不能被 Runtime 自动视作新分支的合法决定。

## 第六小节：外部副作用与 Time Travel 的硬边界

> **Time travel 能回到计算历史，不能回到现实历史。**

如果旧分支已经退款、发邮件、创建工单或修改外部系统，fork 不会自动撤销它。新分支若再次经过同一副作用 Node，可能重复退款或重复通知。因此：

1. 查询、分析、总结 Node 通常适合 replay；
2. 支付、退款、发货、权限变更等 Node 必须使用业务幂等键、外部状态查询与审计；
3. 改变金额、收款人或审批版本的 fork 是新的业务意图，必须重新授权，而不是静默重放旧副作用；
4. 高风险 replay / fork 应受管理员或审批流程控制。

详见跨项目概念页：[幂等键与副作用安全](../../concepts/idempotency.md)。

## 第七小节：生产持久化治理

生产 Checkpoint 设计至少要回答：

| 问题 | 设计方向 |
|---|---|
| 存在哪里 | 按可用性、并发、备份和恢复目标选择持久化 saver。 |
| 保留多久 | 覆盖恢复和审计窗口，同时设计清理、归档或 prune。 |
| 谁能读取 | 按租户、用户、thread、namespace 和角色控制访问。 |
| 保存什么 | State 中避免无必要的密钥、敏感原文与超大临时产物。 |
| 怎样删除 | 支持按用户或 thread 删除相关 checkpoint 与中间 writes。 |
| 怎样追责 | 记录 checkpoint 分支、操作者、审批和外部副作用关联。 |

Checkpointer 接口包含删除 thread、复制 thread 与 prune 等生命周期能力，[__init__.py:320-389](../../../submodules/langgraph/libs/checkpoint/langgraph/checkpoint/base/__init__.py#L320-L389)。这些能力不替代业务数据库的数据删除、合规保留和审计策略。

## 面试收口

> LangGraph checkpoint 是包含 channel 值、版本和调度上下文的可恢复运行快照；`thread_id` 标识整条执行线，`checkpoint_id` 标识具体版本，namespace 区分嵌套图。`get_state` 查询当前现场，`get_state_history` 查询历史；从旧 checkpoint `invoke` 是 replay，`update_state` 后继续执行是 fork。Time travel 只重放或分叉计算，外部副作用仍需要幂等、事务、对账、审计和权限治理。

## QA / 讨论记录

### Q: Replay 和 fork 的区别是什么？

> **状态**: verified
> **来源**: source-code / discussion

A: Replay 以旧 checkpoint 为起点、未修改 State 地重新执行后续 Node；fork 先通过 `update_state()` 创建一条携带新 State 的历史分支，再执行后续 Node。两者均不会删除原历史，且经过 interrupt 前的位置时 interrupt 会重新触发。

### Q: Checkpoint 能否保证退款只执行一次？

> **状态**: verified
> **来源**: source-code / discussion

A: 不能。Checkpoint 保证 Runtime 能保存和恢复计算现场，但不控制外部支付系统是否已处理请求。退款等副作用必须由业务系统的幂等键、外部交易查询、事务 / outbox 和审计共同保护。

## 下一小节

下一大点见 [State、Memory 与 Model Context 边界](state-memory-context.md)：它们都像“记住信息”，但服务的对象、生命周期、可见范围和治理方式不同。
