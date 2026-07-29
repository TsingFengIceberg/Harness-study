# LangGraph State、Memory 与 Model Context 边界

> **日期**: 2026-07-29 | **状态**: draft | **涉及版本**: LangGraph `30c4d58` / LangChain `7316020`

## 相关文档与源码

- [StateGraph 基础](state-graph.md)
- [Checkpoint Persistence、History 与 Time Travel](checkpoint-persistence.md)
- [LangChain Message、Runnable 与 Tool](../langchain/core-abstractions.md)
- [RAG 概念底座](../../concepts/rag.md)
- LangGraph Runtime 注入：[runtime.py](../../../submodules/langgraph/libs/langgraph/langgraph/runtime.py)
- LangChain Message 类型：[base.py](../../../submodules/langchain/libs/core/langchain_core/messages/base.py)

## 一张表区分全部概念

| 概念 | 核心职责 | 典型生命周期 | 是否自动进入模型 |
|---|---|---|---|
| State | 当前 Graph 的共享工作状态。 | 当前 run；配置 Checkpointer 后可跨同一 thread 恢复。 | 否，由 Node / middleware 选择。 |
| `messages` | State 中带对话、Tool Call 与 ToolMessage 因果语义的消息链。 | 通常随同一 thread 累积。 | 常被选入，但仍可裁剪、摘要。 |
| Checkpoint | State 加 channel version、任务定位等 Runtime 现场的历史快照。 | 同一 thread 的多个版本。 | 否，先恢复 Runtime，再构造模型输入。 |
| Store | 跨 thread 的长期档案或可检索记录。 | 多次会话、多个 run。 | 否，必须按身份、权限和任务查询。 |
| Memory | 产品层对“系统记住了什么”的泛称。 | 取决于 messages、checkpoint、Store 或业务数据库实现。 | 取决于注入策略。 |
| RAG | 从外部知识库按问题检索相关证据。 | 每次查询按需取用。 | 仅检索和筛选后的证据进入。 |
| Context Window | 模型本轮真正收到的 prompt、消息、证据和 Tool schema。 | 一次模型调用。 | 它本身就是模型输入。 |
| Runtime Context | 当前 run 的可信身份、依赖和配置。 | 一次运行或请求。 | 否，除非代码显式转成模型材料。 |

## 核心包含关系

```text
messages 通常是 State 的一个字段
Checkpoint 保存 State 及 Runtime 调度现场
Store / RAG / 业务数据库在 Graph 外长期存在
Node / middleware 从这些来源选取信息
→ 形成一次 Model Context Window
```

因此：

```text
messages ⊂ State
State ≠ Checkpoint
Checkpoint ≠ Store
Store ≠ RAG
Memory 不是唯一存储类型
Context Window 不是持久化存储
```

## 企业差旅例子

用户提出东京出差请求时：

```text
State
= 本次出差需求、航班候选、审批状态和预订结果

messages
= 用户请求、模型 Tool Call、航班 ToolMessage 和最终答复

Checkpoint
= 每个 step 的 State、channel version、下一任务与 interrupt 现场

Store
= 该用户跨会话稳定的靠窗座位、酒店集团等偏好

RAG
= 从公司差旅政策文档中检索出的相关条款与来源

Runtime Context
= 可信 user_id、tenant_id、数据库连接与当次依赖

Context Window
= 本轮近期消息 + 偏好摘要 + 政策证据 + 可用 Tool schema
```

完整 State、全部 Store 和整个 RAG 知识库都不会自动进入模型。Context Engineering 负责保留近期消息、压缩旧历史、按权限读取长期档案、检索外部证据，并控制敏感信息和 token 预算。

## Memory 应继续追问什么

“Agent 有 Memory”不是足够精确的技术结论。设计和面试中应继续追问：

1. 记住的是当前任务进度、同一会话历史，还是跨会话用户档案？
2. 数据由 State / Checkpoint、Store、业务数据库还是检索系统保存？
3. 谁可以读取、修改和删除，生命周期多长？
4. 哪些内容会在什么条件下进入模型 Context Window？
5. 用户本次临时选择是否有资格升级为长期 Memory？

LangGraph `Runtime` 将 `context`、`store` 与 `stream_writer` 等运行能力注入 Node，但 Store 内容仍需代码显式读取，[runtime.py:127-207](../../../submodules/langgraph/libs/langgraph/langgraph/runtime.py#L127-L207)。LangChain `BaseMessage` 则定义消息的 content、ID 与消息类型语义，[base.py:93-173](../../../submodules/langchain/libs/core/langchain_core/messages/base.py#L93-L173)。

## 常见误用

| 误用 | 后果 | 正确方向 |
|---|---|---|
| 全部历史不断追加到 messages | Context Window 膨胀、旧信息污染。 | 摘要、裁剪、按需检索。 |
| 把 Checkpoint 当用户资料数据库 | thread 范围、查询与数据治理不匹配。 | 跨会话档案使用 Store / 业务数据库。 |
| 用 RAG 回答实时订单、余额或权限 | 检索文档不是权威交易状态。 | 查询真实业务系统。 |
| 把 Store 全量塞进 Prompt | 隐私、过期数据和 token 风险。 | 按身份、权限和任务筛选。 |
| 假设模型会自动记住旧 run | 模型每轮只看到实际 Context Window。 | 显式恢复、读取、检索和注入。 |

## 面试收口

> State 是当前 Graph 的共享工作状态，messages 是其中带模型和 Tool 协议语义的消息链；Checkpoint 是 State 加 Runtime 调度信息的可恢复历史，Store 是跨 thread 的长期档案。Memory 是这些机制形成的产品能力，RAG 按需检索外部知识，Context Window 则是模型本轮真正看到的有限材料。关键不是把信息全部保存并塞给模型，而是明确其生命周期、权限、权威来源和注入条件。

## 学习状态

本比较已完成第一轮教学，用户对主要边界已基本清楚，不列为当前理解卡点。后续仅在具体项目实现或生产案例中按需回看。
