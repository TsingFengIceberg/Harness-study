# Agent 面试学习

> **日期**: 2026-07-29 | **状态**: draft | **当前阶段**: 资料建档与联合问题目录初始化

## 学习目标

目标不是逐字背诵两份 PDF，而是做到：

1. 听到问题后能先给出一句准确结论；
2. 能解释机制为什么存在、谁触发、谁执行、状态在哪里、结果如何回流；
3. 能给出真实工程例子、适用边界和常见错误；
4. 能承接面试官的一至三轮追问；
5. 对版本敏感或容易过时的结论，知道应回到什么源码或官方资料核验。

“背”可以作为最后的表达训练，但正式学习顺序是：

```text
建立直觉
→ 理解运行机制
→ 用真实场景走一遍
→ 对照源码 / 官方资料纠偏
→ 压缩成 30 秒和 2 分钟面试回答
→ 用追问检验是否真正理解
```

## 原始资料

- [2026-02-23 PDF](../../../references/agent-interview/originals/agent-interview-guide-2026-02-23.pdf)：40 页，覆盖 13 章，主题广。
- [2026-07 PDF](../../../references/agent-interview/originals/agent-interview-guide-2026-07.pdf)：21 页，重点强化 Agent Loop、Harness、Eval、可观测性与生产工程。
- [机械提取稿与来源说明](../../../references/agent-interview/README.md)：便于全文搜索，不能替代 PDF，也不是已核验答案。

## 当前文档

| 文档 | 状态 | 职责 |
|---|---|---|
| [source-comparison.md](source-comparison.md) | draft | 比较两版范围，记录重合、新增和旧版独有内容的整理规则。 |
| [learning-roadmap.md](learning-roadmap.md) | draft | 合并两版后的学习顺序、阶段目标和验收方式。 |
| [question-catalog.md](question-catalog.md) | draft | 联合问题总表；后续逐题去重、拆分和关联正式笔记。 |

后续主题笔记按实际课程推进创建，不预先生成大量空文件。每篇笔记聚焦一个可形成完整回答的主题，例如 `agent-loop.md`、`eval-harness.md`、`tool-calling.md`、`memory-context.md` 和 `agent-security.md`。

## 与现有笔记的关系

本仓库已经完成大量相关学习，不会从零重复：

- [Agent Loop 横向总结](../../comparison/agent-loop.md)
- [Tool System 横向总结](../../comparison/tool-system.md)
- [Context Management 横向总结](../../comparison/context-management.md)
- [Permission / Security 横向总结](../../comparison/permission-security.md)
- [Multi-Agent 横向总结](../../comparison/multi-agent.md)
- [RAG 概念底座](../../concepts/rag.md)
- [MCP 概念底座](../../concepts/mcp.md)
- [LangChain 学习入口](../../projects/langchain/README.md)
- [LangGraph 学习入口](../../projects/langgraph/README.md)

PDF 提供“面试官可能怎么问”；现有项目与概念笔记提供“真实机制和源码证据”。新课程负责把两者合并成可理解、可复述的答案。

## 每个问题的学习产物

每个问题最终应尽量形成：

```text
一句话回答
核心机制
真实例子
适用场景与边界
常见误区
30 秒回答
2 分钟回答
高频追问
证据与版本
个人掌握状态
```

掌握状态与证据状态分开：某个答案可能已经由源码 `verified`，但用户还没有完全掌握；也可能用户已能复述讨论结论，但结论仍需官方资料核验。

## 去重原则

1. 语义相同的问题合并成一个主问题，保留两个版本的来源定位。
2. 新版改写或加深的问题，主问题采用更完整问法，旧版知识点作为子问题保留。
3. 旧版独有的框架、协议、算法和 Python 工程问题继续学习，不因新版省略而删除。
4. 新版独有的 Harness、Eval、线上 bad case、生产安全和系统设计问题作为高优先级补充。
5. 同一主题下若问题考查层次不同，例如“定义 Agent Loop”和“手写生产 Loop”，不能只因关键词重合而错误合并。

## 当前下一步

先完成两版问题的逐条提取和语义去重，再按 [联合学习路线](learning-roadmap.md) 从 Agent / Workflow / Agent Loop 基础开始。每完成一个主题，更新问题目录和学习进度，并把经核验的结论链接回现有正式文档。
