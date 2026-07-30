# Xiaolin RAG Interview Notes

> **来源站点**: [小林面试笔记](https://xiaolinnote.com/ai/rag/rag_info.html)  
> **抓取日期**: 2026-07-30  
> **资料性质**: 第三方网页机械提取  
> **证据状态**: to-verify

本目录保存“RAG 面试题介绍”入口页和 20 个子页的结构化 Markdown 提取稿，用于本地全文搜索、课程定位和问题目录整理。网页内容不是本仓库的已核验结论；涉及框架、协议、论文、版本和工程判断时，仍需回到源码或官方资料核验。

转换保留标题、正文、列表、表格、代码块、链接和远程图片 URL；重复的站点推广尾部已移除，图片文件本身未下载。重新抓取可运行 [`../../scripts/fetch-xiaolinnote.py`](../../scripts/fetch-xiaolinnote.py)。

## 章节目录

| 序号 | 标题 | 本地提取稿 | 原始网页 |
|---:|---|---|---|
| 0 | RAG 面试题介绍 | [00-rag-interview-guide.md](00-rag-interview-guide.md) | [source](https://xiaolinnote.com/ai/rag/rag_info.html) |
| 1 | 1. 什么是 RAG？详细描述一个完整 RAG 系统的详细工作流程？ | [01-whatisrag.md](01-whatisrag.md) | [source](https://xiaolinnote.com/ai/rag/1_whatisrag.html) |
| 2 | 2. 大模型的 RAG 主要用来解决什么问题？ | [02-rag-problems.md](02-rag-problems.md) | [source](https://xiaolinnote.com/ai/rag/2_rag_problems.html) |
| 3 | 3. 相比直接微调 LLM，RAG 解决了什么问题？微调和 RAG 各自的优劣势是什么？ | [03-rag-vs-finetune.md](03-rag-vs-finetune.md) | [source](https://xiaolinnote.com/ai/rag/3_rag_vs_finetune.html) |
| 4 | 4. RAG 中的文档是怎么存的？粒度是多大？详细说说文档切割（Chunking）策略？ | [04-chunking.md](04-chunking.md) | [source](https://xiaolinnote.com/ai/rag/4_chunking.html) |
| 5 | 5. 怎么规避语义被切割掉的问题？ | [05-semantic-cuts.md](05-semantic-cuts.md) | [source](https://xiaolinnote.com/ai/rag/5_semantic_cuts.html) |
| 6 | 6. 在 RAG 中 Embedding 究竟是什么？如何选择和评估一个 Embedding 模型？ | [06-embedding.md](06-embedding.md) | [source](https://xiaolinnote.com/ai/rag/6_embedding.html) |
| 7 | 7. Embedding 有哪几种算法你了解过吗？ | [07-embedding-algos.md](07-embedding-algos.md) | [source](https://xiaolinnote.com/ai/rag/7_embedding_algos.html) |
| 8 | 8. 什么是向量数据库？有没有做过向量数据库的对比选型？ | [08-vectordb.md](08-vectordb.md) | [source](https://xiaolinnote.com/ai/rag/8_vectordb.html) |
| 9 | 9. 讲讲你用的向量数据库？数据量级是多大？性能如何？遇到过性能瓶颈吗？ | [09-vectordb-practice.md](09-vectordb-practice.md) | [source](https://xiaolinnote.com/ai/rag/9_vectordb_practice.html) |
| 10 | 10. 你使用 RAG 给大模型一个输入，系统是怎样的工作流程？ | [10-online-workflow.md](10-online-workflow.md) | [source](https://xiaolinnote.com/ai/rag/10_online_workflow.html) |
| 11 | 11. 请你介绍一下向量检索和关键词检索的区别？ | [11-retrieval-types.md](11-retrieval-types.md) | [source](https://xiaolinnote.com/ai/rag/11_retrieval_types.html) |
| 12 | 12. 如何润色用户的 Query（Query Rewrite）？目的是什么？ | [12-query-rewrite.md](12-query-rewrite.md) | [source](https://xiaolinnote.com/ai/rag/12_query_rewrite.html) |
| 13 | 13. 什么是多路召回？具体怎么做？ | [13-multi-retrieval.md](13-multi-retrieval.md) | [source](https://xiaolinnote.com/ai/rag/13_multi_retrieval.html) |
| 14 | 14. RAG 检索优化策略有哪些？ | [14-retrieval-opt.md](14-retrieval-opt.md) | [source](https://xiaolinnote.com/ai/rag/14_retrieval_opt.html) |
| 15 | 15. 了解哪些更复杂的 RAG 范式？ | [15-advanced-paradigms.md](15-advanced-paradigms.md) | [source](https://xiaolinnote.com/ai/rag/15_advanced_paradigms.html) |
| 16 | 16. 在什么场景下，你会选择使用图数据库来增强传统的向量检索？ | [16-graph-db.md](16-graph-db.md) | [source](https://xiaolinnote.com/ai/rag/16_graph_db.html) |
| 17 | 17. 如何规避 RAG 系统中大模型的幻觉？ | [17-hallucination.md](17-hallucination.md) | [source](https://xiaolinnote.com/ai/rag/17_hallucination.html) |
| 18 | 18. 怎么量化你的 RAG 效果？ | [18-evaluation.md](18-evaluation.md) | [source](https://xiaolinnote.com/ai/rag/18_evaluation.html) |
| 19 | 19. RAG 知识库如何实现动态与持续更新？ | [19-dynamic-update.md](19-dynamic-update.md) | [source](https://xiaolinnote.com/ai/rag/19_dynamic_update.html) |
| 20 | 20. 在实际落地中，你觉得 RAG 最难的地方是哪里？ | [20-hardest-parts.md](20-hardest-parts.md) | [source](https://xiaolinnote.com/ai/rag/20_hardest_parts.html) |
