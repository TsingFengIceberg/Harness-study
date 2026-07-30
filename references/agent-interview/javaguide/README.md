# JavaGuide AI Knowledge Base

> **来源站点**: [JavaGuide AI 应用开发](https://javaguide.cn/ai/ai-core-concepts.html)  
> **抓取日期**: 2026-07-30  
> **资料性质**: 第三方网页机械提取  
> **证据状态**: to-verify

本目录是独立的 JavaGuide AI 知识库镜像，不属于 Xiaolin 面试资料。当前保存左侧 AI 侧栏的 6 个分组、28 个页面，用于本地全文搜索、课程定位和来源对照。网页内容不是本仓库的已核验结论；涉及框架行为、版本、性能数字和工程判断时，仍需回到源码或官方资料核验。

转换保留标题、正文、列表、表格、代码块、链接和远程图片 URL，图片文件本身未下载。少量客户端动态图在服务端 HTML 中只有“图表加载中”占位，提取稿会如实保留；需要查看图形时应回到原始网页。重新抓取全部页面可运行：

```bash
python3 references/agent-interview/javaguide/scripts/fetch-javaguide-ai.py
```

也可以在命令后指定 `overview`、`interview-questions`、`llm-basis`、`agent`、`rag` 或 `system-design`，只刷新部分侧栏分组。

## 入门总览

| 标题 | 本地提取稿 | 原始网页 |
|---|---|---|
| ⭐️AI 核心概念总览 | [ai/ai-core-concepts.md](ai/ai-core-concepts.md) | [source](https://javaguide.cn/ai/ai-core-concepts.html) |

## 面试题

| 标题 | 本地提取稿 | 原始网页 |
|---|---|---|
| ⭐️AI 应用开发面试指南 | [ai/interview-questions/ai-interview-guide.md](ai/interview-questions/ai-interview-guide.md) | [source](https://javaguide.cn/ai/interview-questions/ai-interview-guide.html) |
| 大模型基础面试题总结 | [ai/interview-questions/llm-interview-questions.md](ai/interview-questions/llm-interview-questions.md) | [source](https://javaguide.cn/ai/interview-questions/llm-interview-questions.html) |
| AI Agent 面试题总结 | [ai/interview-questions/agent-interview-questions.md](ai/interview-questions/agent-interview-questions.md) | [source](https://javaguide.cn/ai/interview-questions/agent-interview-questions.html) |
| RAG 面试题总结 | [ai/interview-questions/rag-interview-questions.md](ai/interview-questions/rag-interview-questions.md) | [source](https://javaguide.cn/ai/interview-questions/rag-interview-questions.html) |
| AI 系统设计面试题总结 | [ai/interview-questions/ai-system-design-interview-questions.md](ai/interview-questions/ai-system-design-interview-questions.md) | [source](https://javaguide.cn/ai/interview-questions/ai-system-design-interview-questions.html) |

## 大模型基础

| 标题 | 本地提取稿 | 原始网页 |
|---|---|---|
| 万字拆解 LLM 运行机制 | [ai/llm-basis/llm-operation-mechanism.md](ai/llm-basis/llm-operation-mechanism.md) | [source](https://javaguide.cn/ai/llm-basis/llm-operation-mechanism.html) |
| 大模型 API 调用工程实践 | [ai/llm-basis/llm-api-engineering.md](ai/llm-basis/llm-api-engineering.md) | [source](https://javaguide.cn/ai/llm-basis/llm-api-engineering.html) |
| 大模型结构化输出详解 | [ai/llm-basis/structured-output-function-calling.md](ai/llm-basis/structured-output-function-calling.md) | [source](https://javaguide.cn/ai/llm-basis/structured-output-function-calling.html) |
| AI 应用评测体系 | [ai/llm-basis/llm-evaluation.md](ai/llm-basis/llm-evaluation.md) | [source](https://javaguide.cn/ai/llm-basis/llm-evaluation.html) |

## AI Agent

| 标题 | 本地提取稿 | 原始网页 |
|---|---|---|
| ⭐️AI Agent 核心概念详解 | [ai/agent/agent-basis.md](ai/agent/agent-basis.md) | [source](https://javaguide.cn/ai/agent/agent-basis.html) |
| ⭐️AI Agent 记忆系统详解 | [ai/agent/agent-memory.md](ai/agent/agent-memory.md) | [source](https://javaguide.cn/ai/agent/agent-memory.html) |
| 提示词工程实战指南 | [ai/agent/prompt-engineering.md](ai/agent/prompt-engineering.md) | [source](https://javaguide.cn/ai/agent/prompt-engineering.html) |
| 上下文工程实战指南 | [ai/agent/context-engineering.md](ai/agent/context-engineering.md) | [source](https://javaguide.cn/ai/agent/context-engineering.html) |
| 万字详解 Agent Skills | [ai/agent/skills.md](ai/agent/skills.md) | [source](https://javaguide.cn/ai/agent/skills.html) |
| 万字拆解 MCP 协议 | [ai/agent/mcp.md](ai/agent/mcp.md) | [source](https://javaguide.cn/ai/agent/mcp.html) |
| Harness Engineering 详解 | [ai/agent/harness-engineering.md](ai/agent/harness-engineering.md) | [source](https://javaguide.cn/ai/agent/harness-engineering.html) |
| AI 工作流详解 | [ai/agent/workflow-graph-loop.md](ai/agent/workflow-graph-loop.md) | [source](https://javaguide.cn/ai/agent/workflow-graph-loop.html) |
| Loop Engineering 详解 | [ai/agent/loop-engineering.md](ai/agent/loop-engineering.md) | [source](https://javaguide.cn/ai/agent/loop-engineering.html) |

## RAG

| 标题 | 本地提取稿 | 原始网页 |
|---|---|---|
| ⭐️RAG 基础概念详解 | [ai/rag/rag-basis.md](ai/rag/rag-basis.md) | [source](https://javaguide.cn/ai/rag/rag-basis.html) |
| RAG 文档处理与切分策略 | [ai/rag/rag-document-processing.md](ai/rag/rag-document-processing.md) | [source](https://javaguide.cn/ai/rag/rag-document-processing.html) |
| ⭐️RAG 向量索引算法和向量数据库 | [ai/rag/rag-vector-store.md](ai/rag/rag-vector-store.md) | [source](https://javaguide.cn/ai/rag/rag-vector-store.html) |
| RAG 知识库文档更新策略 | [ai/rag/rag-knowledge-update.md](ai/rag/rag-knowledge-update.md) | [source](https://javaguide.cn/ai/rag/rag-knowledge-update.html) |
| GraphRAG 详解 | [ai/rag/graphrag.md](ai/rag/graphrag.md) | [source](https://javaguide.cn/ai/rag/graphrag.html) |
| RAG 检索优化 | [ai/rag/rag-optimization.md](ai/rag/rag-optimization.md) | [source](https://javaguide.cn/ai/rag/rag-optimization.html) |

## AI 系统设计

| 标题 | 本地提取稿 | 原始网页 |
|---|---|---|
| AI 应用系统设计 | [ai/system-design/ai-application-architecture.md](ai/system-design/ai-application-architecture.md) | [source](https://javaguide.cn/ai/system-design/ai-application-architecture.html) |
| 大模型网关详解 | [ai/system-design/llm-gateway.md](ai/system-design/llm-gateway.md) | [source](https://javaguide.cn/ai/system-design/llm-gateway.html) |
| AI 语音技术详解 | [ai/system-design/ai-voice.md](ai/system-design/ai-voice.md) | [source](https://javaguide.cn/ai/system-design/ai-voice.html) |
