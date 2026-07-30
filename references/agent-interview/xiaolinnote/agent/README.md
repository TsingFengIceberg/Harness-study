# Xiaolin Agent Interview Notes

> **来源站点**: [小林面试笔记](https://xiaolinnote.com/ai/agent/agent_info.html)  
> **抓取日期**: 2026-07-30  
> **资料性质**: 第三方网页机械提取  
> **证据状态**: to-verify

本目录保存“Agent 面试题介绍”入口页和 16 个子页的结构化 Markdown 提取稿，用于本地全文搜索、课程定位和问题目录整理。网页内容不是本仓库的已核验结论；涉及框架、协议、论文、版本和工程判断时，仍需回到源码或官方资料核验。

转换保留标题、正文、列表、表格、代码块、链接和远程图片 URL；重复的站点推广尾部已移除，图片文件本身未下载。重新抓取可运行 [`../../scripts/fetch-xiaolinnote.py`](../../scripts/fetch-xiaolinnote.py)。

## 章节目录

| 序号 | 标题 | 本地提取稿 | 原始网页 |
|---:|---|---|---|
| 0 | Agent 面试题介绍 | [00-agent-interview-guide.md](00-agent-interview-guide.md) | [source](https://xiaolinnote.com/ai/agent/agent_info.html) |
| 1 | 1. 什么是 Agent？与大模型有什么本质不同？ | [01-whatisagent.md](01-whatisagent.md) | [source](https://xiaolinnote.com/ai/agent/1_whatisagent.html) |
| 2 | 2. Agent 的基本架构由哪些核心组件构成？ | [02-components.md](02-components.md) | [source](https://xiaolinnote.com/ai/agent/2_components.html) |
| 3 | 3. Workflow，Agent，Tools 这三个的概念和区别介绍一下？ | [03-workflow-tools.md](03-workflow-tools.md) | [source](https://xiaolinnote.com/ai/agent/3_workflow_tools.html) |
| 4 | 4. 了解哪些其他的 Agent 设计范式？Agent 和 Workflow的区别是什么？ | [04-patterns.md](04-patterns.md) | [source](https://xiaolinnote.com/ai/agent/4_patterns.html) |
| 5 | 5. Agent 推理模式有哪些？ReAct 是啥？具体是怎么实现的？ | [05-react.md](05-react.md) | [source](https://xiaolinnote.com/ai/agent/5_react.html) |
| 6 | 6. ReAct、Plan-and-Execute、Reflection 三种范式有什么核心区别？实际项目中该如何选型？ | [06-three-patterns.md](06-three-patterns.md) | [source](https://xiaolinnote.com/ai/agent/6_three_patterns.html) |
| 7 | 7. 复杂任务怎么做的任务拆分？为什么要拆分？效果如何提升？ | [07-tasksplit.md](07-tasksplit.md) | [source](https://xiaolinnote.com/ai/agent/7_tasksplit.html) |
| 8 | 8. 请你介绍一下 AI Agent 的记忆机制，并说明在实际开发中应该如何设计记忆模块？ | [08-memory.md](08-memory.md) | [source](https://xiaolinnote.com/ai/agent/8_memory.html) |
| 9 | 9. Agent 的长短期记忆系统怎么做的？记忆是怎么存的？粒度是多少？怎么用的？ | [09-memory-storage.md](09-memory-storage.md) | [source](https://xiaolinnote.com/ai/agent/9_memory_storage.html) |
| 10 | 10. 什么是 Multi-Agent？ | [10-multiagent.md](10-multiagent.md) | [source](https://xiaolinnote.com/ai/agent/10_multiagent.html) |
| 11 | 11. 说说 Single-Agent 和 Multi-Agent 的设计方案？ | [11-single-multi.md](11-single-multi.md) | [source](https://xiaolinnote.com/ai/agent/11_single_multi.html) |
| 12 | 12. Agent 记忆压缩通常有哪些方法？ | [12-memcompress.md](12-memcompress.md) | [source](https://xiaolinnote.com/ai/agent/12_memcompress.html) |
| 13 | 13. 在工程实践中，为什么有时候选择「手搓」Agent，而不是直接用成熟框架？ | [13-handcode.md](13-handcode.md) | [source](https://xiaolinnote.com/ai/agent/13_handcode.html) |
| 14 | 14. 如何赋予 LLM 规划能力？ | [14-planning.md](14-planning.md) | [source](https://xiaolinnote.com/ai/agent/14_planning.html) |
| 15 | 15. 讲讲 Agent 的反思机制？为什么要用反思？具体怎么实现？ | [15-reflection.md](15-reflection.md) | [source](https://xiaolinnote.com/ai/agent/15_reflection.html) |
| 16 | 16. 如何设计多 Agent 的协作与动态切换机制？ | [16-collab.md](16-collab.md) | [source](https://xiaolinnote.com/ai/agent/16_collab.html) |
