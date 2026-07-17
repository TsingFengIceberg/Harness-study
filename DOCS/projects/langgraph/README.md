# LangGraph 学习笔记

> 低层有状态 Agent 编排框架样本：用 State、Node、Edge、Pregel runtime、Checkpoint 与 Interrupt 组织长生命周期、可持久化和可恢复的 Agent 工作流。

## 源码

- **Submodule**: [langgraph/](../../../submodules/langgraph/) — 指向 `langchain-ai/langgraph`
- **官方仓库**: [github.com/langchain-ai/langgraph](https://github.com/langchain-ai/langgraph)
- **当前快照**: `49ae27c2ae983cfb92091b0dea9f7bc37a716479`（2026-07-17）

## 研究定位

LangGraph 在本仓库中定位为 **有状态 Agent orchestration runtime** 的重点样本。它不只是把步骤画成 DAG，而是研究以下运行时问题的合适入口：

- State 如何在节点之间合并和传播
- Node / Edge / conditional routing 如何表达循环与动态控制流
- Pregel runtime 如何调度任务、处理 channel 更新并产生 stream
- Checkpoint 如何支持 thread 持久化、恢复和 time travel
- Interrupt / Command 如何承载 human-in-the-loop 与跨节点控制
- 预构建 Agent / ToolNode 如何建立模型决策与工具执行的标准路径

它与 LangChain 的关系可先理解为：LangChain 提供模型、消息、工具等通用构件；LangGraph 负责把这些构件放进一个有状态、可循环、可恢复的执行图中。DeerFlow 则是在此之上继续加入 Gateway、run lifecycle、middleware、sandbox、memory 和 subagent 等产品级 Harness 治理。

一句话定位：

> **LangGraph 像 Agent 的“状态机底盘与运行调度器”：节点决定做什么，边决定下一步去哪里，checkpoint 保存走到哪里，interrupt 让外部人员或系统能够暂停、检查并继续。**

## 笔记索引

| 文档 | 状态 | 说明 |
|---|---|---|
| `state-graph.md` | planned | StateGraph、channel / reducer、Node、Edge、conditional routing 与编译过程。 |
| `pregel-runtime.md` | planned | Pregel 执行循环、task 调度、stream、retry、错误与停止条件。 |
| `checkpoint-persistence.md` | planned | Checkpointer、thread、checkpoint tuple、memory / SQLite / Postgres 持久化与恢复。 |
| `interrupt-command-hitl.md` | planned | Interrupt、Command、resume、human-in-the-loop 与可审计控制流。 |
| `prebuilt-agent-tools.md` | planned | `create_react_agent`、ToolNode、tool validation 与标准 Agent tool loop。 |
| `deer-flow-integration.md` | planned | DeerFlow 如何在 LangGraph runtime 上叠加 lead agent、middleware、sandbox、memory 与 subagent。 |

## 初始源码入口

> 当前只建立后续研读地图，不把目录观察写成已经完成的机制结论。

| 模块 | 源码 | 后续核验重点 |
|---|---|---|
| 项目入口 | [README.md](../../../submodules/langgraph/README.md) | 官方定位、核心能力与 Python / JS 生态边界。 |
| StateGraph | [state.py](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py) | State schema、channel、node / edge 注册和 graph compile。 |
| Pregel 主体 | [main.py](../../../submodules/langgraph/libs/langgraph/langgraph/pregel/main.py) | graph invoke / stream 的执行入口、step 调度与 checkpoint 交互。 |
| Runtime context | [runtime.py](../../../submodules/langgraph/libs/langgraph/langgraph/runtime.py) | 节点可见 runtime context、store 与 stream writer。 |
| Checkpoint 基础 | [__init__.py](../../../submodules/langgraph/libs/checkpoint/langgraph/checkpoint/base/__init__.py) | Checkpointer 接口、checkpoint / metadata / tuple 类型与版本语义。 |
| 预构建 ReAct Agent | [chat_agent_executor.py](../../../submodules/langgraph/libs/prebuilt/langgraph/prebuilt/chat_agent_executor.py) | 模型节点、工具节点、路由和 Agent state 的预构建组合。 |
| ToolNode | [tool_node.py](../../../submodules/langgraph/libs/prebuilt/langgraph/prebuilt/tool_node.py) | tool call 解析、执行、错误处理、状态 / store 注入与 tool result 回流。 |

## 与现有研究的关系

- [LangChain 学习入口](../langchain/README.md)：用于区分“应用组件与统一协议”和“状态编排 runtime”。
- [DeerFlow Agent Loop](../deer-flow/agent-loop.md)：后续可从具体产品集成反向观察 LangGraph runtime 如何被 Harness 包装。
- [DeerFlow Context Management](../deer-flow/context-management.md)：适合比较 LangGraph state / checkpoint 与上层 run、thread、memory、file 和 model context 的边界。
- [Agent Loop 横向总结](../../comparison/agent-loop.md)：待完成同粒度源码研读后，再把 LangGraph runtime 纳入正式横向结论。
- [Context Management 横向总结](../../comparison/context-management.md)：后续研究 checkpoint 与消息上下文、长期记忆、session persistence 的区别。

## QA / 讨论记录

### Q: LangGraph 是否就是“更高级的 LangChain Agent”？

> **状态**: to-verify
> **来源**: discussion / official-docs / source-code

A: 不宜这样简化。LangChain 提供模型、消息、工具和 Agent 装配 API；LangGraph 提供更低层的状态图与 durable execution runtime。LangChain 的高层 Agent 可以建立在 LangGraph 上，但 LangGraph 也能编排不依赖 LangChain Agent 工厂的自定义节点和工作流。后续需要通过 `StateGraph.compile()`、Pregel 执行路径、checkpoint 与 prebuilt agent 源码进一步核验两者的调用边界。
