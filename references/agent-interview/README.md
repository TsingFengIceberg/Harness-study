# Agent Interview Source Materials

> **资料性质**: 第三方博主整理的 Agent 面试学习材料，不是本仓库原创内容，也不自动构成已核验技术结论。

## 文件结构

```text
agent-interview/
├── README.md
├── originals/
│   ├── agent-interview-guide-2026-02-23.pdf
│   └── agent-interview-guide-2026-07.pdf
└── extracted/
    ├── agent-interview-guide-2026-02-23.md
    └── agent-interview-guide-2026-07.md
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
