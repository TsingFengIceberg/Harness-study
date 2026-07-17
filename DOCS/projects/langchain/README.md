# LangChain 学习笔记

> Agent / LLM 应用开发框架样本：提供模型、消息、Prompt、Runnable、Tool、Retriever 与 Agent 等通用抽象，并通过集成生态连接不同 provider 和外部能力。

## 源码

- **Submodule**: [langchain/](../../../submodules/langchain/) — 指向 `langchain-ai/langchain`
- **官方仓库**: [github.com/langchain-ai/langchain](https://github.com/langchain-ai/langchain)
- **当前快照**: `98216c0c1d7d2dc13e3ebeac36329853a5cb52a0`（2026-07-17）

## 研究定位

LangChain 在本仓库中暂定位为 **Agent / LLM 应用组件与组装框架**。它和本仓库既有 Harness 的研究层次有交集，但不能只因为提供 Agent API 就直接等同于一个完整 Coding Agent 产品或运行平台。

可以先用三层关系理解 LangChain 生态：

```text
LangChain：提供模型、消息、工具、检索器、Runnable 和 Agent 等应用构件
LangGraph：承载有状态、可持久化、可中断恢复的 Agent 编排 runtime
LangSmith：提供 tracing、调试、评测与生产观测平台；其公开 GitHub 仓库主要是客户端 SDK
```

后续源码研读重点包括：

- `langchain-core` 如何定义消息、模型、Runnable、Tool、Retriever 等稳定协议
- LangChain v1 Agent API 如何组装模型、工具和 middleware，并与 LangGraph runtime 衔接
- `langchain-classic` 中传统 chains / agents / memory / retrievers 与当前 v1 API 的演进关系
- provider integrations、standard tests 与 model profiles 如何管理庞大的适配生态
- LangChain 的便利抽象与 Harness 自身的权限、workspace、session、审计和执行硬边界应如何分层

一句话定位：

> **LangChain 像 Agent 应用的“通用零件库与装配层”：它让模型、消息、工具和检索组件能够用相近接口组合；真正的长生命周期状态编排更多由 LangGraph 承担，而产品级权限和执行边界仍需要具体 Harness 负责。**

## 笔记索引

| 文档 | 状态 | 说明 |
|---|---|---|
| `core-abstractions.md` | planned | Message、ChatModel、Runnable、Tool、Retriever 等核心协议及其组合方式。 |
| `agent-runtime.md` | planned | LangChain v1 Agent 工厂、middleware、tool loop 与 LangGraph runtime 的衔接。 |
| `integrations-and-testing.md` | planned | Provider integrations、model profiles、standard tests 与兼容性治理。 |
| `retrieval-rag.md` | planned | Document、Text Splitter、Embedding、VectorStore、Retriever 与 RAG 组装边界。 |
| `classic-to-v1.md` | planned | `langchain-classic` 与当前 v1 包结构、API 和迁移方向。 |

## 初始源码入口

> 当前只建立后续研读地图，不把目录观察写成已经完成的机制结论。

| 模块 | 源码 | 后续核验重点 |
|---|---|---|
| 项目入口 | [README.md](../../../submodules/langchain/README.md) | 官方定位、安装边界与 LangChain / LangGraph / LangSmith 的公开关系。 |
| Runnable 基础 | [base.py](../../../submodules/langchain/libs/core/langchain_core/runnables/base.py) | 组合、调用、批处理、流式和配置传播的统一协议。 |
| Tool 基础 | [base.py](../../../submodules/langchain/libs/core/langchain_core/tools/base.py) | Tool schema、调用、异常与结果表示。 |
| Chat Model 基础 | [chat_models.py](../../../submodules/langchain/libs/core/langchain_core/language_models/chat_models.py) | 模型统一接口、消息输入输出、streaming 与配置边界。 |
| Message 基础 | [base.py](../../../submodules/langchain/libs/core/langchain_core/messages/base.py) | 消息对象、content blocks、序列化与跨 provider 表示。 |
| v1 Agent 工厂 | [factory.py](../../../submodules/langchain/libs/langchain_v1/langchain/agents/factory.py) | 当前 Agent 装配入口，以及 model、tools、middleware 与 graph 的连接方式。 |
| Classic Agent | [agent.py](../../../submodules/langchain/libs/langchain/langchain_classic/agents/agent.py) | 传统 AgentExecutor / planning-execution 路径，供理解历史演进而非默认代表当前 API。 |

## 与现有研究的关系

- [LangGraph 学习入口](../langgraph/README.md)：后续应把 LangChain 的组件协议与 LangGraph 的状态图 runtime 分层阅读。
- [DeerFlow 学习入口](../deer-flow/README.md)：DeerFlow 基于 LangGraph 构建，可作为观察上层产品 Harness 如何使用 LangChain 生态能力的实例。
- [Tool System 横向总结](../../comparison/tool-system.md)：待源码研读达到同等深度后，再比较 LangChain Tool 抽象与各 Harness 的权限、执行和事件回流。
- [RAG 概念底座](../../concepts/rag.md)：后续用于区分通用检索组件、完整 RAG pipeline 与具体应用平台。

## QA / 讨论记录

### Q: LangChain、LangGraph、LangSmith 可以称为“三剑客”吗？

> **状态**: draft
> **来源**: discussion / official-docs / source-code

A: 可以作为便于学习的非官方称呼，但更准确的是“LangChain 生态三层组合”：LangChain 偏组件与应用组装，LangGraph偏有状态 Agent 编排，LangSmith 偏 tracing、评测和生产观测。三者可配合，但并非部署时必须同时采用；尤其 LangSmith 的 GitHub 仓库主要承载客户端 SDK，不能用其 star 数直接衡量整个平台的产品使用量。
