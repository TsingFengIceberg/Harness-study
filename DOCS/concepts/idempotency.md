# 幂等键与副作用安全

> **日期**: 2026-07-29 | **状态**: draft | **来源**: discussion / inference

## 相关文档

- [LangGraph Checkpoint Persistence、History 与 Time Travel](../projects/langgraph/checkpoint-persistence.md)
- [LangGraph Interrupt、Command 与 Human-in-the-loop](../projects/langgraph/interrupt-command-hitl.md)
- [LangGraph ToolNode 与完整 Agent Tool Loop](../projects/langgraph/prebuilt-agent-tools.md)

## 一句话定义

> **幂等键让系统识别“这些重复请求其实要求同一件现实业务动作”，从而只让该动作生效一次，并在重试时返回既有结果、处理中状态或对账结果。**

它不是 LangGraph 专有概念；支付、订单、消息投递、API Gateway、队列消费者与 Agent Tool 都会面对同类问题。

## 为什么 Agent 特别需要它

Agent 可能因模型重试、Tool Retry、网络超时、interrupt 重放、checkpoint 恢复、time-travel fork、消息重复投递或用户重复点击，多次到达同一副作用 Tool。查询与计算通常可以重试；退款、扣款、发邮件、发货、创建工单、修改权限则不能只因“超时”便假设第一次没有生效。

```text
Retry
= 再发一次请求

Idempotency key
= 让重复请求在业务系统中仍被识别为同一次动作
```

## 退款例子

```text
refund_request_id = rr_001
approval_version = v1
idempotency_key = refund:rr_001:approval-v1
```

首次请求以该 key 调退款服务。若支付平台实际已退款但响应丢失，重试仍带相同 key；退款服务或支付平台应返回第一次的退款交易号，而不是再次退款。

Tool Call ID 不等于幂等键：前者配对模型 Tool Call 与 ToolMessage；后者识别真实业务动作。Agent 重放时可能产生新的 Tool Call ID，但仍应使用同一个可信业务幂等键。

## 正确粒度：最小不可重复业务动作

幂等键并非越细越好，也不应粗到“一个订单一把 key”。正确粒度是：**这一次不应被重复生效的最小业务意图**。

同一订单可能产生多项合法动作：

```text
提交订单：place-order:cart-submit-001
支付：payment:payment-intent-008:capture-v1
创建发货单：shipment:fulfillment-request-019
部分退款 30：refund:refund-request-101:approval-v1
另一笔部分退款 20：refund:refund-request-102:approval-v1
```

不能所有动作都用 `order:1024`，否则支付成功会错误阻止发货或退款；也不能把 timestamp 放入 key，否则每次重试都会被误认为新动作。金额、币种、收款账户、批准版本等通常应同时进入 request hash 或版本校验：相同 key 携带不同关键参数时应拒绝，而非静默复用旧结果或执行新动作。

> **精髓：粒度要足够小，避免把不同合法动作误去重；也要足够稳定，确保同一次重试始终命中同一个操作记录。**

## 服务端的最小状态机

| 状态 | 含义 | 相同 key 再次到达时的方向 |
|---|---|---|
| `processing` | 已领取执行权，但最终结果未确认。 | 等待、返回处理中，或对账；不能重新执行。 |
| `succeeded` | 副作用已确认成功。 | 返回第一次结果与外部交易号。 |
| `retryable_failed` | 已确认在副作用前失败。 | 可按策略用相同 key 重试。 |
| `unknown` | 超时或崩溃，外部是否成功未知。 | 查询外部状态；不能盲目重做。 |
| `rejected` | 业务或权限拒绝。 | 依据业务语义稳定拒绝或要求新业务请求。 |

一条操作记录通常还包含 `tenant_id`、`operation`、`request_hash`、`external_reference`、响应快照与过期策略。`idempotency_key` 应受唯一索引、原子 insert / upsert、事务或锁保护，否则并发请求可能同时看到“key 不存在”并重复执行。

## 跨系统与副作用链

一个 key 通常不能原子覆盖退款、写本地数据库、发送消息和发邮件。常见分层是：

```text
退款 key
→ 保护真实退款动作

本地事务 + outbox
→ 防止本地记录已提交但外部事件丢失

消费端 event ID / inbox 去重
→ 防止重复发送通知、重复创建工单或重复发放积分
```

支付平台成功而本地服务崩溃时，应用需要用同一个 key 查询或重试外部平台，并将外部交易号写回本地记录。若 provider 不支持幂等键，则必须依赖外部查询、对账、事务协调或人工处理降低不确定性。

## Agent、Checkpoint 与 Time Travel

Graph checkpoint 能恢复计算现场，不保证支付、邮件或订单只执行一次。副作用 Tool 的稳定 key 应由可信业务后端或 Runtime Context 注入，而不是由模型随机生成。

Time travel 尤其需要警惕：从已发生退款的旧 checkpoint fork 后，若仍是同一次批准方案，应复用原 key 并得到“已处理”结果；若金额或批准版本改变，这是新的业务意图，必须使用新 key，并重新经过权限和审批。调试 fork 不应自动变成新的真实退款。

## 生产检查清单

1. 同一业务意图的稳定 ID 是什么？
2. 哪些参数变化意味着它已经是新意图？
3. key 由哪个可信系统生成、保存和绑定租户？
4. 并发相同 key 时，谁获得实际执行权？
5. 超时后怎样区分成功、失败与未知？
6. 外部 provider 是否支持同 key 重试或按 key 查询？
7. 下游事件和通知是否有独立的消费去重？
8. replay / fork 是否允许经过该副作用 Node？
9. key 保留多久，谁有权查询、重试、作废或创建新版本？

## 边界

幂等键不是 exactly-once 的万能保证：它只能保护真正执行该副作用、并持久化识别该 key 的系统。它也不替代身份认证、权限校验、数据库事务、外部对账、审计、数据保留和删除策略。
