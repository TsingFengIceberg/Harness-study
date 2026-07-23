# LangChain / LangGraph 面试学习路线

> **日期**: 2026-07-23 | **状态**: draft | **涉及版本**: `langchain@98216c0c1d7d2dc13e3ebeac36329853a5cb52a0` / `langgraph@49ae27c2ae983cfb92091b0dea9f7bc37a716479`

## 相关文档

- [LangChain 学习入口](README.md)
- [第一课：Message、Runnable 与 Tool](core-abstractions.md)
- [LangGraph 学习入口](../langgraph/README.md)
- [RAG 概念底座](../../concepts/rag.md)
- [Agent Loop 横向总结](../../comparison/agent-loop.md)

## 一句话路线

> **先学 LangChain 的应用组件与 Agent 组装，再学 LangGraph 的状态、循环、持久化和恢复；每个知识点都要能回答“是什么、为什么需要、运行时如何协作、适用场景是什么、边界在哪里”。**

面试学习与完整源码通读的目标不同。推荐按三个层次准备：

| 层次 | 能力要求 |
|---|---|
| 基础 | 能解释核心概念，能实现基础 RAG 和 Tool Calling Agent。 |
| 进阶 | 能画出端到端运行流程，讲清 LangChain、LangGraph、LangSmith 的边界。 |
| 深入 | 能解释 State reducer、Pregel、checkpoint、interrupt、durable execution 与生产可靠性问题。 |

普通 AI 应用岗位以进阶层次为主要目标；Agent 平台、AI Infra、Agent Harness 岗位应继续深入运行时和生产边界。

## 生态总框架

```text
LangChain：零件与装配层
LangGraph：状态机与运行时
LangSmith：Tracing、调试、评测与生产观测平台
```

一条典型 Agent 链路是：

```text
用户消息
  ↓
LangChain 组装模型、消息、工具和 middleware
  ↓
LangGraph runtime 保存 State 并执行模型节点
  ↓
AIMessage 可能产生 tool_calls
  ↓
ToolNode / Agent Runtime 执行工具
  ↓
ToolMessage 写回 messages state
  ↓
重新调用模型，直至没有新 Tool Call
  ↓
Checkpointer 保存运行状态，LangSmith 记录 Trace / Eval
```

三者可以配合，但部署时并非必须全部使用。尤其 LangSmith 主要是平台产品，其公开源码仓库以客户端 SDK 为主；不能把三个项目都当成同一类开源 runtime。

## LangChain 必学模块

### 核心组件

1. **Message**：`SystemMessage`、`HumanMessage`、`AIMessage`、`ToolMessage`、content blocks、Tool Call ID、usage / response metadata。
2. **Chat Model**：`invoke` / `ainvoke`、`stream` / `astream`、`batch`、`bind_tools`、structured output、provider 参数和错误处理。
3. **Prompt**：`PromptTemplate`、`ChatPromptTemplate`、message placeholder、动态上下文和 Prompt Injection 边界。
4. **Runnable / LCEL**：统一执行接口、`RunnableSequence`、`RunnableParallel`、`RunnableLambda`、`RunnablePassthrough`、配置、回调、重试和 fallback。
5. **Tool**：name、description、args schema、`@tool`、参数验证、错误返回、并行 Tool Call，以及模型请求与 Runtime 执行的边界。
6. **Agent**：`create_agent`、模型—工具循环、停止条件、middleware、动态模型 / 工具选择、工具失败恢复。
7. **RAG**：Document Loader、Text Splitter、Embedding、VectorStore、Retriever、top-k、metadata filter、hybrid search、rerank、citation 和 evaluation。
8. **Memory / Context**：消息历史、Graph State、Checkpoint、Store、RAG 和 Context Window 的区别。

### 当前版本边界

新学习主线优先放在：

```text
langchain-core
Runnable / LCEL
Tool Calling
LangChain v1 create_agent / middleware
LangGraph state / checkpoint
```

旧项目和旧面试题中仍可能出现以下概念，因此需要认识，但不应把它们当成当前新代码主线：

```text
LLMChain
SequentialChain
initialize_agent
传统 AgentExecutor
ConversationBufferMemory
langchain-classic 中的早期 Chain / Agent API
```

面试时应主动区分 current v1 路径和 classic / legacy 路径，避免照搬过时教程。

## LangGraph 必学模块

1. **定位**：低层、有状态、支持循环与持久化恢复的 Agent orchestration runtime，不只是 DAG。
2. **StateGraph**：State、Node、Edge、`START`、`END`、conditional edge、compile、invoke 和 stream。
3. **State / Reducer**：Node 返回部分 State 更新；Reducer 定义覆盖、追加或自定义冲突合并语义。
4. **Pregel runtime**：计划本轮任务、执行节点、收集写入、在 step 边界合并、保存 checkpoint、计算下一轮任务。
5. **Checkpoint**：checkpointer、`thread_id`、checkpoint namespace / ID、状态历史、恢复和 time travel。
6. **Durable execution**：进程崩溃或长时间暂停后恢复；不等于自动保证外部副作用 exactly-once。
7. **Interrupt / Command**：持久化暂停、人工审批、补充输入、`resume` 和控制流更新。
8. **ToolNode**：解析 Tool Call、执行 Tool、处理异常、产生 ToolMessage、注入 State / Runtime / Store。
9. **Streaming**：模型 token、消息、State values / updates、自定义事件与调试事件属于不同观察层。
10. **Subgraph / Multi-Agent**：子图状态边界、checkpoint namespace、共享文件与上下文隔离、父子结果回流。

## LangChain 与 LangGraph 高频比较

| 问题 | 阶段性回答 |
|---|---|
| LangChain 与 LangGraph 的区别 | LangChain 偏模型、消息、Tool、Retriever、Runnable 和 Agent 组装；LangGraph 偏有状态图执行、循环、checkpoint、interrupt 和 durable execution。 |
| 什么时候只用 LangChain | 单次调用、简单 Prompt → Model → Parser、简单 RAG、短且确定的控制流、不需要持久化恢复。 |
| 什么时候使用 LangGraph | 多步骤、循环、条件分支、明确 State、HITL、checkpoint、长任务恢复、subgraph / multi-agent。 |
| LCEL 与 LangGraph 的区别 | LCEL 更像输入输出函数管道；LangGraph 更像带持久状态、循环和恢复能力的状态机 runtime。 |
| LangGraph 是否是 DAG | 不是纯 DAG；它支持循环、条件路由、interrupt / resume、subgraph 和持久状态。 |
| LangChain Agent 与 LangGraph 的关系 | LangChain 高层 Agent 可以建立在 LangGraph 上；LangGraph 也可以独立编排自定义节点，二者不是同一 API 层。 |

## 生产化必学边界

### 可靠性

- 最大迭代次数、timeout、retry、fallback、取消和 context overflow；
- Tool Error、模型错误、checkpoint 和 partial failure；
- 外部副作用的幂等键、事务、outbox 与去重；
- checkpoint 之前已成功执行副作用、随后进程崩溃所导致的重复执行风险。

### 安全

- Prompt Injection 与不可信检索 / Tool Result；
- Tool 参数验证不等于执行授权；
- workspace boundary、path traversal、Shell 隔离和网络 allowlist；
- credential isolation、least privilege、HITL 和多租户数据隔离。

### 上下文与状态

- Context Window、消息历史、Graph State、Checkpoint、Store 和 RAG 的区别；
- trimming、summarization、工具结果截断、大文件处理和长期记忆污染；
- checkpoint 保存 Runtime 状态，但不意味着全部状态都应注入下一次模型上下文。

### 可观测性、评测与成本

- callbacks、trace、token usage、latency、Tool success rate；
- retrieval recall、answer faithfulness、trajectory evaluation；
- 离线数据集、在线监控和 LangSmith 的作用；
- 模型分层、上下文长度、RAG top-k、Tool Loop 次数、并行调用和子 Agent 成本放大。

## 推荐学习顺序

### 第一阶段：LLM 应用基础

```text
Chat Model
→ Message
→ Prompt
→ Tool Calling
→ Embedding / VectorStore / Retriever
→ RAG
→ Agent Loop
→ Context Window
```

验收：能手写模型调用，解释完整 Tool Calling 消息链，实现最小 RAG，并区分 Chain 与 Agent。

### 第二阶段：LangChain 核心

```text
Message
→ ChatModel
→ Prompt
→ Output Parser / Structured Output
→ Runnable / LCEL
→ Tool / bind_tools
→ create_agent
→ middleware
→ RAG 组件
```

推荐实践：

1. 一个 `Document → Split → Embedding → VectorStore → Retriever → Prompt → Model` 的 RAG 问答；
2. 一个 `User → Agent → Tool Call → Tool execution → ToolMessage → Final AIMessage` 的 Tool Calling Agent。

### 第三阶段：LangGraph 核心

```text
State
→ Node
→ Edge / conditional edge
→ Reducer
→ compile
→ Pregel step
→ Checkpointer / thread_id
→ Interrupt / Command
→ ToolNode
→ Streaming
→ Subgraph
```

推荐实践：人工审批客服 Agent。

```text
START
  ↓
classify
  ├── 普通问题 → RAG
  ├── 账户问题 → account_tool
  └── 退款问题 → prepare_refund
                       ↓
                  interrupt 等待审批
                       ↓
                  execute_refund
                       ↓
                      END
```

实现中加入 messages state、reducer、conditional edge、checkpointer、thread_id、interrupt / resume、Tool Error、streaming 和幂等 refund ID。

### 第四阶段：源码与生产问题

只追主调用链，不无差别通读：

```text
create_agent / StateGraph.compile
  ↓
invoke / stream
  ↓
Pregel step
  ↓
model node
  ↓
tool_calls
  ↓
ToolNode
  ↓
State update / reducer
  ↓
checkpoint
  ↓
下一 step
```

LangChain 入口见 [Message](../../../submodules/langchain/libs/core/langchain_core/messages/base.py)、[ChatModel](../../../submodules/langchain/libs/core/langchain_core/language_models/chat_models.py)、[Runnable](../../../submodules/langchain/libs/core/langchain_core/runnables/base.py)、[Tool](../../../submodules/langchain/libs/core/langchain_core/tools/base.py) 与 [Agent factory](../../../submodules/langchain/libs/langchain_v1/langchain/agents/factory.py)。

LangGraph 入口见 [StateGraph](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py)、[Pregel](../../../submodules/langgraph/libs/langgraph/langgraph/pregel/main.py)、[Checkpoint](../../../submodules/langgraph/libs/checkpoint/langgraph/checkpoint/base/__init__.py)、[ToolNode](../../../submodules/langgraph/libs/prebuilt/langgraph/prebuilt/tool_node.py) 与 [预构建 Agent](../../../submodules/langgraph/libs/prebuilt/langgraph/prebuilt/chat_agent_executor.py)。

## 高频题清单

### LangChain

1. LangChain 是什么，解决什么问题？
2. LangChain 与直接调用模型 SDK 有什么区别？
3. LangChain、LangGraph、LangSmith 是什么关系？
4. Message 有哪些主要类型？
5. Tool Call 与 Tool Result 如何配对？
6. Runnable 与 LCEL 是什么？
7. `invoke`、`batch`、`stream` 有什么区别？
8. `bind_tools` 做了什么？
9. Agent 与 Chain 有什么区别？
10. ReAct 是什么，Agent 如何停止？
11. Tool 执行失败如何回流？
12. RAG 的完整流程是什么？
13. Retriever 与 VectorStore 有何区别？
14. chunk size / overlap 如何选择？
15. 如何评价 RAG 的召回和生成质量？
16. Memory、RAG、消息历史、Context Window 有何区别？

### LangGraph

17. LangGraph 为什么不只是 DAG？
18. State、Node、Edge 分别是什么？
19. Reducer 是什么，为什么需要？
20. Pregel / superstep 如何理解？
21. Checkpoint 与 `thread_id` 是什么？
22. Checkpoint 与长期 Memory 有何区别？
23. Interrupt 与 Command 如何实现 HITL？
24. Durable execution 是什么？
25. 恢复执行如何避免重复副作用？
26. ToolNode 负责什么，不负责什么？
27. LangGraph streaming 有哪些观察层？
28. Subgraph 与 Multi-Agent 如何组织和隔离状态？

## 统一答题模板

每道题按五步组织：

```text
1. 定义：它是什么
2. 动机：为什么需要
3. 机制：运行时怎么协作
4. 场景：什么时候使用
5. 边界：缺点是什么、不负责什么
```

例如回答 Checkpoint：

> Checkpoint 是 LangGraph 对某个 thread 执行状态的持久化快照。它解决长任务暂停、崩溃恢复和历史状态查看问题。Runtime 通常在执行 step 边界保存 State、channel version 和后续任务信息，恢复时根据 `thread_id` 加载快照继续执行。它适合长任务、HITL 和可恢复 Agent，但不自动保证外部副作用 exactly-once；发送邮件、付款等操作仍需幂等键和业务事务控制。

## 最终判断标准

面试准备的重点不是记住所有类名，而是能从一次请求开始讲清：

```text
谁调用模型？
谁执行工具？
消息如何表达请求和结果？
State 放在哪里？
并行节点如何合并状态？
Checkpoint 如何保存和恢复？
外部副作用如何防重？
Context、Checkpoint、Memory、Store 与 RAG 有何区别？
LangChain 抽象与产品 Harness 的权限、安全和执行边界在哪里？
```

> **精髓：真正的主线是“模型调用 → Tool Call → Tool 执行 → State 更新 → Checkpoint → 下一轮模型调用”，而不是孤立背诵 API 名称。**
