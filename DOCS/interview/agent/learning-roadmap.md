# Agent 面试联合学习路线

> **日期**: 2026-07-30 | **状态**: draft | **范围**: 2026-02-23 与 2026-07 两版资料并集

## 学习顺序

| 阶段 | 主题 | 来源重点 | 验收目标 |
|---|---|---|---|
| 0 | 面试回答方法与任务边界 | 7 月版 | 会用“定义、机制、取舍、工程化、例子”组织答案。 |
| 1 | Agent、Workflow 与 Agent Loop | 两版 | 能定义 Agent，解释完整 Loop、停止条件、预算、错误恢复和死循环防御。 |
| 2 | ReAct、Planning、Reflection 与搜索 | 2 月版为主 | 能比较 ReAct、Plan-and-Execute、LATS、Reflexion，说明适用边界。 |
| 3 | Tool Calling、MCP、A2A 与权限 | 两版 | 能从模型契约、Runtime 执行、协议接入、权限和副作用说明工具系统。 |
| 4 | State、Memory、Context 与 RAG | 两版 | 能区分 State、消息、长期记忆、检索证据和模型上下文。 |
| 5 | Agent 框架与编排 | 2 月版 + 现有源码笔记 | 能按抽象和边界比较 LangGraph、OpenAI Agents SDK、AutoGen / CrewAI、ADK 与自研 Loop。 |
| 6 | Multi-Agent 与协作 | 两版 | 能解释结构、通信、责任、共享状态、成本和不应拆分的场景。 |
| 7 | Harness、Eval 与 Benchmark | 7 月版为主 | 能设计 Dataset、Environment、Runner、Scorer、Sandbox、回归集和真实状态判分。 |
| 8 | Observability、Debug 与 Bad Case 回流 | 7 月版为主 | 能用 trace、state diff、trajectory replay 定位失败并进入回归集。 |
| 9 | Python 工程、并发与 Streaming | 2 月版为主 | 能回答 asyncio、TaskGroup、限流、GIL、结构化输出和流式处理。 |
| 10 | 安全、Guardrails 与 HITL | 两版 | 能解释间接注入、最小权限、沙箱、审批、数据泄露和记忆污染。 |
| 11 | 部署、可靠性、成本与版本演进 | 两版 | 能设计队列、并发池、Retry、Checkpoint、灰度、回滚和成本治理。 |
| 12 | 系统设计、编码题与模拟面试 | 两版 | 能完整回答代码 Agent、浏览器 Agent、知识库 Agent、客服 Agent 和追问题。 |

## 优先级

### P0：必须熟练口述

- Agent / Workflow / Agent Loop；
- Tool Calling 与权限边界；
- State / Memory / Context / RAG；
- Harness、Eval、Observability；
- 安全、HITL、可靠性与副作用；
- 一个完整生产 Agent 系统设计。

### P1：常见深入题

- ReAct、Plan-and-Execute、Reflection；
- Multi-Agent；
- 框架选型；
- Python 并发、Streaming、结构化输出；
- benchmark、LLM-as-Judge、灰度和成本优化。

### P2：岗位相关或加分题

- LATS / MCTS；
- Computer Use、代码 Agent 与前沿论文；
- A2A、GraphRAG、MemGPT / Letta；
- 自定义底层 Runtime、分布式调度与专业 benchmark。

## 每个主题的学习节奏

1. 从 `question-catalog.md` 选一个主问题和相关追问；
2. 机械提取稿只用于定位，以两版 PDF 原页核对题目、上下文和来源差异；
3. 先用通俗场景讲机制，不直接背 PDF 答案；
4. 链接现有项目笔记，必要时小范围核验源码或官方文档；
5. 形成 30 秒回答、2 分钟回答和高频追问；
6. 用户确认理解程度后记录掌握状态；
7. 主题完成后更新目录，不一次性生成大量空笔记。

知识正文与模拟面试 QA 分开保存：`topics/` 记录可复习的正式知识，`qa/` 保留用户真实回答、纠偏过程和待复习点；两边通过知识点编号与 QA 编号双向链接。

## 当前进度

- 已完成第一课 [Agent、Workflow、Agent Loop 与 Agent Harness](topics/agent-workflow-loop-harness.md) 的概念边界、退款场景和 30 秒回答；
- 已完成 [Q1-Q6 模拟面试](qa/agent-workflow-loop-harness.md)，覆盖四个概念、下一步控制权、Harness 完整性、Runner / Scorer 与真实状态判分；
- Workflow 与混合式系统结构已达到 `understood`；Agent 准确定义、Loop 边界、Runner / Scorer 和真实结果判分仍为 `learning` 或待复习；
- 下一课进入完整 Agent Eval Harness，不提前扩展到复杂 Benchmark 或 LLM-as-Judge 组合策略。

## 第一阶段建议

LangChain / LangGraph 基础已经完成，因此不必从框架 API 重学。新主线建议从 7 月版最核心、现有课程尚未系统覆盖的内容开始：

```text
Agent、Workflow 与 Agent Loop 总复盘
→ Agent Harness
→ Eval Dataset / Environment / Runner / Scorer
→ 结果评测、轨迹评测和线上 bad case 回流
```

这条路线既能复用已有 Agent Loop 知识，又能进入两份资料中最值得新增学习的 Harness / Eval 主线。
