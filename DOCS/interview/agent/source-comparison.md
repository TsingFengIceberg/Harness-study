# 两版 Agent 面试资料初步比较

> **日期**: 2026-07-29 | **状态**: draft | **来源**: third-party PDFs / mechanical extraction

## 基本信息

| 维度 | 2026-02-23 版 | 2026-07 版 |
|---|---|---|
| 页数 | 40 | 21 |
| 文本提取规模 | 约 5.3 万字符 | 约 3.5 万字符 |
| 组织方式 | 13 章百科式知识面 | 16 个围绕生产闭环的主题 |
| 主要倾向 | 架构、框架、协议、RAG、多 Agent、记忆、论文、Python、评测、安全、部署 | Loop、Harness、Eval、Observability、生产工程、安全和系统设计 |
| 当前判断 | 广度更大，含大量新版未重复列出的知识 | 不是旧版全文修订，更像面向 2026 工程面试的重点补充与重构 |

当前比较只基于目录、问题标题和初步浏览，尚未完成逐题语义去重，不能给出精确重合比例。

## 2 月版范围

1. AI Agent 核心概念与架构；
2. Agent 主流框架；
3. Tool Use / Function Calling；
4. MCP 与 A2A；
5. RAG；
6. Multi-Agent；
7. Agent Memory；
8. 科研前沿、论文与算法；
9. Python Agent 工程；
10. 评估基准与可观测性；
11. 安全、对齐与 Guardrails；
12. 部署与成本优化；
13. 高频综合题。

## 7 月版范围

1. 2026 年 Agent 面试关注点；
2. Agent Loop；
3. Agent Eval Harness；
4. Workflow / Agent 与架构模式；
5. Tool Calling、MCP 与权限；
6. State、Memory 与 Context Engineering；
7. 验证、评估与 benchmark；
8. 可观测性与排障；
9. 生产部署、并发、限流与 durable execution；
10. 安全、对齐与权限；
11. 框架选型；
12. 高频系统设计；
13. 高频编码题；
14. 面试官追问；
15. 回答模板；
16. 资料源与继续阅读。

## 初步重合区

两版都涉及：

- Agent 定义、Workflow / Agent 边界与 Agent Loop；
- Agent 架构模式和框架选型；
- Tool Calling、MCP、权限与错误处理；
- State、Memory、RAG 和上下文管理；
- Multi-Agent；
- 评估、可观测性、安全、部署和成本；
- 系统设计与综合面试回答。

重合不等于内容重复。2 月版更常给概念分类和框架知识，7 月版更常追问如何控制、验证、复现、上线和排障。

## 2 月版明显需要保留的内容

- ReAct、Plan-and-Execute、LATS、Reflexion 等架构与算法；
- LangGraph、OpenAI Agents SDK、CrewAI、AutoGen、Google ADK 的具体框架题；
- Function Calling provider 格式与失败处理；
- A2A、RAG 演进、GraphRAG、chunking、embedding 和 RAG 评估；
- Agent Memory 分类、MemGPT / Letta；
- 推理、代码 Agent、Computer Use 与论文清单；
- Python asyncio、并发、流式处理、GIL 和 Pydantic；
- 传统 benchmark、LLM-as-Judge、成本估算和综合编码题。

这些内容不能因为 7 月版没有逐项展开就从学习路线中删除。

## 7 月版明显新增或强化的内容

- Loop 的终止、预算、重复调用检测与错误恢复；
- Harness 的 Dataset、Environment、Runner、Scorer、Sandbox、Logger 和 Replayer；
- 最终结果、轨迹、策略、安全和成本多维评测；
- Eval 泄漏、过拟合、复现、置信区间、灰度和线上 bad case 回流；
- Trace、trajectory diff 与线上失败归因；
- Queue、限流、稀缺资源、重试风暴与 durable execution；
- 间接 Prompt Injection、工具越权、审批绕过和记忆污染；
- 代码修复、浏览器购物、企业知识库和客服 Agent 系统设计；
- 面试官追问清单与结构化回答模板。

## 合并策略

```text
两版语义相同
→ 合成一个主问题，保留双来源

新版在旧题上增加生产追问
→ 旧题作为基础，新版作为进阶和追问

旧版独有
→ 保留，按面试价值重新排序

新版独有
→ 纳入高优先级生产课程
```

## 风险提示

PDF 是问题来源，不是权威事实来源。框架 API、协议版本、产品能力、benchmark 状态、价格、发布日期和论文结论都可能过时或表述不严谨。后续正式笔记必须区分：

```text
PDF 原始说法
讨论形成的通俗解释
源码 / 官方文档核验结果
最终面试回答
```
