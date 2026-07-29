# Agent 面试问题目录

> **日期**: 2026-07-29 | **状态**: draft | **当前粒度**: 主题级初始索引，待逐题提取与语义去重

## 状态说明

- **来源**：`Feb` 表示 2026-02-23 版，`Jul` 表示 2026-07 版，`Both` 表示两版都有相关问题。
- **证据状态**：当前均为 `planned / to-verify`；PDF 回答不是 `verified` 证据。
- **学习状态**：与证据状态分开维护，后续记录 `not-started / learning / review / fluent`。

## 联合主题目录

| ID | 主问题簇 | 来源 | 当前证据状态 | 现有基础 |
|---|---|---|---|---|
| A01 | 什么是 Agent？与普通 LLM 应用、Workflow 有什么区别？ | Both | to-verify | [Agent Loop 对比](../../comparison/agent-loop.md) |
| A02 | Agent Loop 如何运行、停止、恢复并防止死循环？ | Both | to-verify | [Agent Loop 对比](../../comparison/agent-loop.md) |
| A03 | ReAct、Plan-and-Execute、LATS、Reflexion 如何比较？ | Feb | to-verify | 待建立专题。 |
| A04 | 如何选择 Workflow、Single Agent、Multi-Agent 和确定性流程？ | Both | to-verify | [Multi-Agent 对比](../../comparison/multi-agent.md) |
| T01 | Function Calling 的模型契约和 Runtime 执行面是什么？ | Both | to-verify | [LangChain 核心抽象](../../projects/langchain/core-abstractions.md) |
| T02 | Tool schema、权限、Retry、错误回流和副作用如何设计？ | Both | to-verify | [Tool System 对比](../../comparison/tool-system.md) |
| T03 | MCP 与 Function Calling、普通 API、RAG 有何区别？ | Both | to-verify | [MCP 概念](../../concepts/mcp.md) |
| T04 | A2A 解决什么问题，与 MCP、Multi-Agent 通信有何区别？ | Feb | to-verify | 待核验官方协议。 |
| S01 | State、messages、Checkpoint、Store、Memory 和 Context Window 如何区分？ | Both | to-verify | [State / Memory / Context](../../projects/langgraph/state-memory-context.md) |
| R01 | RAG 基础流程、Advanced / Agentic RAG 和长上下文如何选择？ | Both | to-verify | [RAG 概念](../../concepts/rag.md) |
| R02 | Chunking、Embedding、Rerank、GraphRAG 和 RAG Eval 如何设计？ | Feb | to-verify | 待扩展 RAG 专题。 |
| F01 | LangGraph 的 StateGraph、Checkpoint、HITL 和 durable execution 是什么？ | Both | to-verify | [LangGraph 学习入口](../../projects/langgraph/README.md) |
| F02 | OpenAI Agents SDK、AutoGen / CrewAI、Google ADK 和自研 Loop 如何选？ | Both | to-verify | 待按官方源码 / 文档核验。 |
| M01 | Multi-Agent 有哪些结构、通信与责任边界？ | Both | to-verify | [Multi-Agent 对比](../../comparison/multi-agent.md) |
| H01 | Agent Harness 是什么，与 Agent Loop 有什么区别？ | Jul | to-verify | 待建立 Harness 专题。 |
| H02 | Dataset、Environment、Tool Adapter、Runner、Scorer、Sandbox 如何协作？ | Jul | to-verify | 待建立 Harness 专题。 |
| E01 | Agent 应评最终结果、轨迹、策略、安全还是成本？ | Both | to-verify | CozeLoop 等项目笔记可复用。 |
| E02 | LLM-as-Judge、程序判分、人工标注如何组合？ | Both | to-verify | 待建立 Eval 专题。 |
| E03 | Eval 泄漏、过拟合、统计波动和不可复现如何处理？ | Jul | to-verify | 待建立 Eval 专题。 |
| E04 | SWE-bench、WebArena、OSWorld、tau-bench 等 benchmark 测什么？ | Both | to-verify | 必须回到 benchmark 官方资料。 |
| O01 | Trace、Span、State diff、trajectory replay 如何支持排障？ | Both | to-verify | [Streaming / Observability](../../projects/langgraph/streaming-observability.md) |
| O02 | 线上 bad case 如何脱敏、标注并回流离线回归集？ | Jul | to-verify | 待建立 EvalOps 专题。 |
| P01 | Python asyncio、TaskGroup、限流、GIL 与 Agent 并发有什么关系？ | Feb | to-verify | 待建立 Python 工程专题。 |
| P02 | Streaming、Pydantic 和结构化输出验证如何实现？ | Feb | to-verify | LangChain / LangGraph 笔记可复用。 |
| SEC01 | Prompt Injection、工具越权、数据泄露和记忆污染如何防御？ | Both | to-verify | [Permission / Security](../../comparison/permission-security.md) |
| SEC02 | Guardrails、Sandbox、最小权限与 HITL 分别放在哪里？ | Both | to-verify | [Sandbox 对比](../../comparison/sandbox-systems.md) |
| D01 | Agent 服务如何部署、排队、限流、持久化和恢复？ | Both | to-verify | [生产部署取舍](../../comparison/production-deployment-tradeoffs.md) |
| D02 | Token、延迟、模型路由、缓存和并行成本如何优化？ | Both | to-verify | [模型路由与成本](../../comparison/model-routing-cost-token-budget.md) |
| D03 | 如何灰度、回滚并处理 model / prompt / tool / index 版本变化？ | Jul | to-verify | 待建立版本演进专题。 |
| SYS01 | 如何设计代码修复 Agent？ | Jul | to-verify | OpenHands / Coding Harness 笔记可复用。 |
| SYS02 | 如何设计浏览器购物 Agent？ | Jul | to-verify | 待结合 WebArena / Browser Harness。 |
| SYS03 | 如何设计企业知识库 Agent？ | Jul | to-verify | RAG、安全与权限笔记可复用。 |
| SYS04 | 如何设计客服工具 Agent？ | Jul | to-verify | [生产退款 Agent](../../projects/langgraph/production-refund-agent.md) |
| Q01 | 高频编码题、Debug 题和面试官连续追问 | Both | to-verify | 待逐题拆分。 |

## 逐题整理模板

```markdown
### Q: 问题？

> **来源**: Feb p.xx / Jul p.xx
> **证据状态**: draft / to-verify / verified
> **学习状态**: not-started / learning / review / fluent

一句话回答：

机制：

真实例子：

边界与误区：

30 秒回答：

2 分钟回答：

高频追问：

证据：
```

## 下一步

下一轮对两份提取稿逐条识别 `Q:`、章节标题和编码题，建立问题级清单，并人工判断语义重合。自动文本相似度只能提供候选，不能代替人工合并，因为相同关键词可能考查完全不同的深度。
