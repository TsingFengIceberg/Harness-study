# Agent Interview Source Materials

> **资料性质**: 第三方博主整理的 Agent 面试学习材料，不是本仓库原创内容，也不自动构成已核验技术结论。

## 文件结构

```text
agent-interview/
├── README.md
├── originals/
│   ├── agent-interview-guide-2026-02-23.pdf
│   └── agent-interview-guide-2026-07.pdf
├── extracted/
│   ├── agent-interview-guide-2026-02-23.md
│   └── agent-interview-guide-2026-07.md
├── scripts/
│   └── fetch-xiaolinnote.py
├── xiaolinnote/
│   ├── README.md
│   ├── agent/    # Agent 入口页 + 16 个子页
│   ├── rag/      # RAG 入口页 + 20 个子页
│   ├── tools/    # LLM 工具调用入口页 + 16 个子页
│   └── llm/      # 大模型工程入口页 + 22 个子页
└── javaguide/
    ├── README.md
    ├── scripts/fetch-javaguide-ai.py
    └── ai/       # JavaGuide AI 侧栏 6 个分组、28 个页面
```

## 原始文件

| 版本 | 文件 | 页数 | SHA-256 |
|---|---|---:|---|
| 2026-02-23 | [agent-interview-guide-2026-02-23.pdf](originals/agent-interview-guide-2026-02-23.pdf) | 40 | `024ede94d33ce4a3f676b8705141214d3c4a6ce33a944cd4d3c3f7ca56004d51` |
| 2026-07 | [agent-interview-guide-2026-07.pdf](originals/agent-interview-guide-2026-07.pdf) | 21 | `4c438ea8d0f093d099b690fcec24d1a893b56510b7ecf802bd00de00b46d16c7` |

`originals/` 中的 PDF 是原始证据文件。除非重新取得明确的新版本，否则不编辑、不覆盖；文件名只做稳定的英文规范化。

## Markdown 提取稿

| 版本 | 提取稿 | 用途 |
|---|---|---|
| 2026-02-23 | [agent-interview-guide-2026-02-23.md](extracted/agent-interview-guide-2026-02-23.md) | 搜索旧版章节、问题与原始回答。 |
| 2026-07 | [agent-interview-guide-2026-07.md](extracted/agent-interview-guide-2026-07.md) | 搜索新版 Agent Loop、Harness、Eval 与生产工程内容。 |

提取稿由 `pdftotext -layout` 机械生成，保留大部分文字，但分页、表格、代码缩进和换行可能失真。它只用于搜索、定位和建立问题清单；引用细节发生歧义时，以 PDF 页面为准。

## 小林 AI 面试网页

[Xiaolin 本地总索引](xiaolinnote/README.md)汇总以下四个专题；该知识库与 JavaGuide 分开保存和维护。

| 专题 | 本地索引 | 子页数 | 原始入口 |
|---|---|---:|---|
| Agent | [agent/README.md](xiaolinnote/agent/README.md) | 16 | [source](https://xiaolinnote.com/ai/agent/agent_info.html) |
| RAG | [rag/README.md](xiaolinnote/rag/README.md) | 20 | [source](https://xiaolinnote.com/ai/rag/rag_info.html) |
| LLM 工具调用 | [tools/README.md](xiaolinnote/tools/README.md) | 16 | [source](https://xiaolinnote.com/ai/tools/tools_info.html) |
| 大模型工程 | [llm/README.md](xiaolinnote/llm/README.md) | 22 | [source](https://xiaolinnote.com/ai/llm/llm_info.html) |

四个专题均按“一个入口页或子页对应一个 Markdown 文件”保存，并保留标题、正文、列表、表格、代码块、链接及远程图片 URL，便于本地搜索和后续整理问题目录。

这些网页属于第三方 `to-verify` 材料，不自动成为本仓库的技术结论。网页可能更新，远程图片也可能失效；重新抓取全部专题可运行：

```bash
python3 references/agent-interview/scripts/fetch-xiaolinnote.py
```

也可以在命令后指定 `agent`、`rag`、`tools` 或 `llm`，只刷新部分专题。脚本会校验 Agent、RAG、Tools 的连续章节编号；LLM 子页没有数字 URL 前缀，因此按入口页中的出现顺序稳定编号。

## JavaGuide AI 知识库

[JavaGuide 本地索引](javaguide/README.md)与 `xiaolinnote/` 同级保存，是另一套独立第三方来源。目录镜像 JavaGuide `/ai/` 下的 URL 结构，当前覆盖左侧侧栏 6 个分组、28 个页面：入门总览、面试题、大模型基础、AI Agent、RAG 和 AI 系统设计。

```bash
python3 references/agent-interview/javaguide/scripts/fetch-javaguide-ai.py
```

JavaGuide 提取稿同样保持 `to-verify`。普通图片保留远程 URL；少量客户端动态图在服务端 HTML 中只有“图表加载中”占位，需要查看图形时回到原始网页。

## 使用原则

1. 两版都保留。7 月版聚焦生产闭环，但页数更少，不能假定完整替代 2 月版。
2. 重合问题合并学习，但记录两个来源；旧版独有问题不能因为新版省略而删除。
3. PDF 中的回答统一先视为第三方 `draft / to-verify` 材料，不直接升级为 `verified`。
4. 涉及框架行为、协议版本、论文结论、benchmark、价格和时间敏感信息时，回到源码、论文或官方文档核验。
5. 自有解释、纠偏、面试回答和学习进度写入 [`DOCS/interview/agent/`](../../DOCS/interview/agent/README.md)，不回写机械提取稿。

## 学习入口

- [Agent 面试学习入口](../../DOCS/interview/agent/README.md)
- [两版资料初步比较](../../DOCS/interview/agent/source-comparison.md)
- [联合学习路线](../../DOCS/interview/agent/learning-roadmap.md)
- [问题目录](../../DOCS/interview/agent/question-catalog.md)
