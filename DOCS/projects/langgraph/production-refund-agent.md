# LangGraph 完整生产 Agent 实战：高风险退款

> **日期**: 2026-07-29 | **状态**: draft | **涉及版本**: LangGraph `30c4d58` / LangChain `7316020`

## 相关文档与源码

- [StateGraph 基础](state-graph.md)
- [Pregel Channel 与任务调度](pregel-runtime.md)
- [Interrupt、Command 与 HITL](interrupt-command-hitl.md)
- [ToolNode 与完整 Agent Tool Loop](prebuilt-agent-tools.md)
- [Checkpoint Persistence、History 与 Time Travel](checkpoint-persistence.md)
- [Streaming 与观察层](streaming-observability.md)
- [Graph 可靠性策略](graph-reliability.md)
- [幂等键与副作用安全](../../concepts/idempotency.md)
- StateGraph 构建与 Node 策略：[state.py](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py)
- `Command`、`Interrupt` 与 Runtime 类型：[types.py](../../../submodules/langgraph/libs/langgraph/langgraph/types.py)
- ToolNode 执行：[tool_node.py](../../../submodules/langgraph/libs/prebuilt/langgraph/prebuilt/tool_node.py)
- Checkpoint 基础接口：[checkpoint/base/__init__.py](../../../submodules/langgraph/libs/checkpoint/langgraph/checkpoint/base/__init__.py)

## 场景与核心原则

用户提出：

> 订单 `O-2026-001` 的商品损坏，请退款 5800 元。

不安全的实现是：

```text
用户请求 → 模型决定退款 → Tool 直接打款
```

生产实现应是：

```text
接收请求
→ Agent 调查订单、支付和物流事实
→ 形成退款建议
→ 确定性风险检查
→ 高风险人工审批
→ 幂等执行退款
→ 查询并确认退款结果
→ 通知用户
```

> **精髓：模型负责调查和提出建议，确定性系统负责权限、风险、审批与副作用执行资格。**

## Graph 总图

```text
START
→ receive_request
→ agent
→ ToolNode
→ agent
→ risk_gate
→ request_approval
→ execute_refund
→ verify_refund
→ notify_user
→ END
```

`agent ↔ ToolNode` 可以循环多轮；真正退款不能只靠模型生成 Tool Call，必须经过 `risk_gate` 和必要的人工审批。

## 入口、Runtime Context 与 thread

业务后端收到请求后，先完成登录认证、租户解析和权限初筛，再构造：

```text
tenant_id    租户
user_id      当前操作者
thread_id    当前退款案件的执行线
request_id   当前 HTTP 请求
order_id     订单标识
```

可信的 `tenant_id`、`user_id`、权限和数据库 / 支付客户端放入 Runtime Context，而不是相信聊天消息中的身份声明。`thread_id` 交给 Checkpointer，使流程可以跨服务重启和人工等待继续。

## State 设计

```text
messages              对话、Tool Call 与 ToolMessage
order_id               当前订单
requested_amount       用户申请金额
order_snapshot         订单事实快照
policy_evidence        退款政策证据
proposed_refund        Agent 的退款建议与理由
risk_level             确定性风险等级
risk_reasons           风险规则命中原因
approval               人工审批结果
refund_operation_key   退款幂等键
refund_external_id     支付平台退款 ID
refund_status          not_started / unknown / succeeded / failed
case_status            investigating / pending_approval / completed 等
final_response         最终用户回复
```

State 保存当前退款案件；Store 保存跨案件长期档案；RAG 提供政策证据；Runtime Context 提供可信身份和依赖；Model Context 只选取本轮模型需要的材料。

## 第一步：HTTP 请求启动 Graph

初始输入：

```text
messages = [HumanMessage("订单损坏，申请退款 5800 元")]
order_id = O-2026-001
requested_amount = 5800
refund_status = not_started
```

业务后端使用 `thread_id=refund-case-O-2026-001` 调用 Graph。`receive_request` 规范化金额与原因，返回：

```text
case_status = investigating
normalized_reason = item_damaged
```

Node 返回的是 pending writes；superstep 的 Update 阶段把它们应用到 Channel，形成下一份 State，并由 Checkpointer 保存快照。

## 第二步：模型只提出查询意图

第一次执行 `agent` 时，State 只有用户说法，没有业务证据。模型产生三个 Tool Call：

```text
get_order(order_id)
get_payment_status(order_id)
get_delivery_evidence(order_id)
```

每个 Tool Call 有独立 ID。模型此时没有查询数据库，只是生成结构化调用请求。`agent` 返回 `AIMessage`，Update 阶段将它追加到 `messages`；路由函数发现存在 Tool Call，下一节点才是 ToolNode。

## 第三步：ToolNode 建立事实

Graph Runtime 看到一个 ToolNode Graph Task。ToolNode 内部可以并发执行三个查询工具：

```text
订单：金额 5800，状态 delivered
支付：支付成功，尚无退款记录
物流：已签收，存在损坏证据
```

ToolNode 为三个结果分别生成按 Tool Call ID 配对的 ToolMessage。这里有两个并行层次：

- Graph 层是一个 ToolNode Task；
- ToolNode 内部可以并行执行多个 Tool Call。

ToolMessage 在 Update 阶段追加进 `messages`，回边再触发 `agent`。

## 第四步：模型形成建议但不获得授权

第二次执行 `agent` 时，模型看到用户请求、三个 Tool Call 和三个结果回执，形成：

```text
proposed_refund = {
  amount: 5800,
  reason: "商品损坏且证据完整",
  confidence: 0.93
}
```

本轮不再产生 Tool Call，路由离开 Agent Tool Loop，进入确定性的 `risk_gate`。模型建议不是退款授权。

## 第五步：确定性风险门

`risk_gate` 检查：

```text
5800 > 自动退款上限 1000       → 高额
支付状态为 paid                 → 具备退款前提
历史退款次数正常                → 未命中基础欺诈规则
当前操作者是普通客服            → 无权直接批准
```

返回：

```text
risk_level = high
risk_reasons = [
  "退款金额超过自动审批上限",
  "当前操作者无高额退款权限"
]
```

Conditional edge 根据 `risk_level` 路由到 `request_approval`。不能把模型建议、风险判断和批准权全部放在一个 LLM Node 中。

## 第六步：Interrupt 产生审批待办

`request_approval` 组合订单事实、政策证据、Agent 建议和风险原因，然后调用 `interrupt()`。Runtime：

```text
记录当前 Task 的 Interrupt
→ 保存 State、Channel version、待执行 Task 和 Interrupt ID
→ 本次 invoke 返回
→ 业务后端创建审批待办
→ 服务进程无需保持 Python 调用栈
```

等待审批是业务暂停，不应配置成超时后自动批准，也不应把它当成普通失败 Retry。

## 第七步：主管恢复同一 thread

主管在前端批准 5800 元退款。后端先验证主管权限，再使用同一 `thread_id` 调用：

```text
Command(resume={
  decision: approved,
  amount: 5800,
  approver_id: manager-007
})
```

Runtime 加载最新 Checkpoint，并从头重新执行 `request_approval` Node。当相同顺序的 `interrupt()` 再次出现时，Runtime 返回保存的 resume 值。Node 才产生：

```text
approval = approved
case_status = approved
```

Update barrier 后，下一节点才是 `execute_refund`。

## 第八步：幂等执行退款

系统为最小不可重复业务动作构造：

```text
refund:tenant-A:order-O-2026-001:payment-P-001:5800:v1
```

执行顺序：

1. 创建或读取该 key 的退款操作记录；
2. 校验相同 key 的金额和参数 hash 一致；
3. 已经 `succeeded` 时直接返回历史结果；
4. 尚未执行时调用支付系统；
5. 保存支付平台 `refund_id` 与状态。

支付成功后 Node 返回：

```text
refund_operation_key = ...
refund_external_id = R-90001
refund_status = succeeded
```

## 第九步：处理最危险的崩溃窗口

可能出现：

```text
支付系统已经退款成功
→ Graph 尚未保存 succeeded checkpoint
→ 进程崩溃
```

恢复后 `execute_refund` 可能再次执行。稳定幂等键应让支付系统或本地操作记录返回原 `refund_id`，而不是产生第二笔退款。

如果第一次调用超时且结果未知：

```text
按幂等键 / external request ID 查询
→ succeeded：记录成功
→ definitely_not_started：允许有限 Retry
→ still_unknown：暂停、对账或人工介入
```

> **Checkpoint 恢复 Graph 执行现场；幂等键和对账保护 Graph 外部的真实资金操作。**

## 第十步：确认与通知

`verify_refund` 再查询支付平台，确认退款 ID、金额与状态。`notify_user` 使用独立消息幂等键：

```text
notification:refund:R-90001:success:v1
```

最终 State：

```text
case_status = completed
refund_status = succeeded
approval = approved
refund_external_id = R-90001
final_response = "退款 5800 元已受理成功"
```

Runtime 保存最终 Checkpoint，然后到达 `END`。

## Node 级可靠性矩阵

| Node | 推荐策略 |
|---|---|
| 读取订单 / 支付 / 物流 | Timeout + 有限 Retry |
| 检索退款政策 | Cache + Retry；key 包含政策 / 索引版本 |
| 模型分析 | Model Retry / Fallback + Tool / Token / 时间预算 |
| 风险判断 | 确定性代码；失败时终止，不能猜测放行 |
| 人工审批 | Interrupt + Checkpoint + 权限 + 审计 |
| 执行退款 | 幂等键 + 状态查询 + 谨慎 Retry + 对账 |
| 用户通知 | 消息幂等键 + Retry + 失败队列 |

## Streaming 与观察

```text
messages  → 模型生成文本与消息事件
updates   → 当前完成了哪个业务阶段
custom    → “正在查询支付状态”等业务进度
tasks     → Node Task 开始、成功、Retry 或失败
interrupt → 当前需要谁审批什么
```

用户页面主要展示业务进度和审批；运维平台展示 Task、Retry、Timeout、Checkpoint 和 Trace。两者消费同一执行过程的不同观察面。

## LangGraph 与业务平台的边界

LangGraph 负责：

```text
State、Task 调度、循环、Checkpoint、Interrupt、恢复和 Stream
```

业务系统仍负责：

```text
登录认证、权限校验、审批待办、支付系统、幂等记录、审计日志、
密钥管理、数据权限、限流、告警和对账
```

生产 Agent 因此不是“一个 Graph 加几个 Tool”，而是：

> **Graph Runtime + 模型决策 + 确定性业务控制 + 持久化 + 权限 + 幂等副作用 + 业务前端 + 可观测系统。**

## 面试回答

> 生产 LangGraph Agent 应把模型限制在调查和建议层，把权限、风险、审批与副作用资格放在确定性节点和业务系统。查询型 Tool 可以进入 Agent Tool Loop，高风险写操作应经过 risk gate 与 Interrupt 审批，再使用稳定幂等键执行。Checkpoint 负责恢复 Graph 现场，但支付成功到 checkpoint 落盘之间仍有崩溃窗口，因此外部副作用必须通过幂等键、状态查询和对账保护；Streaming、Trace 和审计则分别服务用户体验与生产治理。
