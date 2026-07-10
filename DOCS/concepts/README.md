# Agent / Harness 基础概念

> 跨项目、跨供应商的可复用概念底座。这里解释机制本身，不把某个项目的实现细节误写成通用规律。

## 这个目录解决什么问题

本仓库原有的研究主线是：

```text
项目源码事实
  -> 横向比较
  -> 综合归纳
```

但学习 Agent / Harness 时，还常会先遇到一些不属于任何单一项目的问题：RAG 是什么？MCP 与 tool calling 有何不同？Memory、Skill、Context Window 各在哪一层？

这些概念需要先建立共同语言，再回到具体项目核验实现。因此本目录作为研究金字塔的**概念底座**：

```text
概念底座：DOCS/concepts/
  -> 项目纵向：DOCS/projects/
    -> 横向专题：DOCS/comparison/
      -> 综合归纳：DOCS/synthesis/
```

它不替代项目笔记：通用页描述“一个机制通常解决什么问题”；项目页必须回答“这个项目到底有没有、怎么做、边界在哪里”。

## 当前概念索引

| 文档 | 说明 | 可继续阅读的实现案例 |
|---|---|---|
| [rag.md](rag.md) | RAG / 检索增强生成：外部知识如何成为带证据的模型上下文；与 Memory、上传文件、搜索、Skills、MCP 的边界。 | [DeerFlow RAG 相关能力映射](../projects/deer-flow/rag.md) |
| [mcp.md](mcp.md) | MCP：Host / Client / Server、Tools / Resources / Prompts 三面能力、七层安全防线、交互流程、传输方式，以及它��� RAG / Tool Calling / Skills 的区���。 | [DeerFlow Tool System](../projects/deer-flow/tool-system.md) |

## 后续候选主题

随着更多项目源码核验，可继续扩展：

- Tool Calling / Function Calling
- Memory 与长期用户画像
- Context Window、Summarization 与 Context Engineering
- Skills、Plugins 与工作流知识
- Agent Loop、状态机与运行时生命周期
- Evaluation、Feedback 与自我改进
- Permission、Sandbox 与外部能力的安全治理

## 使用原则

- 通用概念页中提到某个具体项目时，必须链接到项目笔记或源码，不用概念类比代替实现证据。
- 不把“能调用一个工具”“能上传文件”“有 Memory”直接写成“已经有完整 RAG”。
- 对仍在快速演变的生态概念，先说明稳定的架构边界，再说明不同实现的可变部分。

## 相关文档

- [DeerFlow 学习入口](../projects/deer-flow/README.md)
- [横向对比目录](../comparison/README.md)
- [综合归纳目录](../synthesis/README.md)
