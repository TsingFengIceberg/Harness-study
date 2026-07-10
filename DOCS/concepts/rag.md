# RAG：让模型先查证据，再基于证据回答

> **日期**: 2026-07-10 | **状态**: draft

## 相关文档

- [基础概念目录](README.md)
- [MCP：连接外部能力的协议](mcp.md)
- [DeerFlow RAG 相关能力映射](../projects/deer-flow/rag.md)
- [DeerFlow Context Management](../projects/deer-flow/context-management.md)
- [DeerFlow Tool System](../projects/deer-flow/tool-system.md)

## 一句话解释

**RAG（Retrieval-Augmented Generation，检索增强生成）**是一种“开卷答题”模式：模型回答前，系统先从外部知识中找出与当前问题相关、且用户有权查看的证据，再把少量高质量证据放进上下文，让模型据此作答。

```text
闭卷回答：模型只依赖训练时学到的知识 + 当前对话

RAG 回答：模型先查资料
  -> 看到当前、相关、允许访问的证据
  -> 再解释或完成任务
```

它的目标不是让模型“记住更多”，而是让它在需要时能引用外部、可更新、可追溯的资料。

## 一、最小工作流：离线准备与在线问答

RAG 通常分成两段。

### 1.1 离线：把知识准备成可检索材料

```text
原始知识源
  PDF / Word / Markdown / Wiki / Git / 数据库导出 / 网页
  -> 解析、清洗、权限与版本标记
  -> 按段落、标题、表格、页面或语义边界切分
  -> 建立索引
     关键词全文索引 / 向量索引 / 结构化索引 / 混合索引
  -> 保留 source、版本、时间、权限、页码等 metadata
```

这里最重要的产物不是“很多文本块”，而是**带身份、来源和生命周期的证据单元**。

### 1.2 在线：根据当前问题检索并组装证据

```text
用户问题
  -> 识别 query、用户身份、租户、权限、时间范围
  -> 先做 ACL / version / status 过滤
  -> 召回候选资料
  -> 可选：融合、去重、rerank、读取相邻上下文
  -> 在 token 预算内组成 evidence packet
  -> 模型基于证据生成答案、引用和不确定性说明
```

一个最简单的 RAG 可能只做“关键词检索 top-3”；一个企业级 RAG 则可能同时处理权限、版本、向量检索、全文检索、重排、引用和审计。

**精髓标记：RAG 的重点不是把资料全部塞给模型，而是为当前问题挑出最少但足够、可信且有权限的证据。**

## 二、RAG 不是什么

相邻机制很容易被混淆。它们都可能让模型“多看到一些东西”，但解决的问题不同。

| 概念 | 核心问题 | 与 RAG 的区别 |
|---|---|---|
| 模型训练 / 微调 | 模型参数如何吸收通用能力？ | RAG 不改模型权重，知识更新不必重新训练。 |
| Long-term Memory | 如何跨会话保留某用户的偏好、纠正、目标？ | Memory 面向关系与经验；RAG 面向当前问题的外部证据。 |
| 文件上传 | 如何把这次任务的材料交给 Agent？ | 上传只解决材料进入工作区；是否索引、检索和引用仍是另一层。 |
| Web Search | 如何获取公开、偏实时的信息？ | Web Search 是一种知识源 / 检索工具；RAG 更泛化，也可检索内部知识。 |
| Skill | 某类任务该按什么流程做？ | Skill 检索的是操作方法；RAG 检索的是回答业务问题的事实证据。 |
| Prompt cache | 如何复用相同 prompt 前缀并减少成本？ | Cache 是性能机制，不负责找知识。 |
| MCP | Host 如何标准化连接外部能力？ | MCP 是协议；MCP server 可以提供 RAG 工具，但 MCP 本身不是 RAG。 |

## 三、RAG 的实现形态：不只有向量数据库

### 3.1 直接文件访问

```text
Agent 看到文件目录
  -> grep / read_file / SQL / API
  -> 找到材料后阅读
```

适合文件少、任务复杂、Agent 需要核验原文或执行多步分析的场景。优点是简单、可追溯；缺点是 Agent 会消耗更多轮次，面对海量文档效率较低。

### 3.2 关键词 / 全文检索

```text
query = "合同 CN-2026-001 生效日期"
  -> BM25 / inverted index / SQL LIKE / document search
```

适合编号、专名、函数名、错误码、制度条款等精确匹配问题。它不是“低级版 RAG”；在大量企业问题里，精确检索反而不可替代。

### 3.3 向量 / embedding 检索

```text
文本与 query
  -> embedding vectors
  -> 相似度检索
  -> 找语义相近的内容
```

适合用户措辞与原文不一致、需要按意思查资料的问题。单独使用时容易召回“看起来像、但事实不对”的段落，也可能错过编号或版本等精确信号。

### 3.4 Hybrid retrieval + rerank

成熟实现常组合：

```text
关键词 / BM25 召回
+ 向量召回
+ metadata / ACL / 时间过滤
  -> fusion
  -> reranker
  -> top evidence
```

这比“只做 cosine similarity”更适应企业资料：既能精确匹配编号，也能理解用户的自然语言表达。

### 3.5 Agentic retrieval：让 Agent 把检索当工具使用

固定 RAG 通常是：

```text
每个问题 -> 固定检索 top-k -> 直接回答
```

Agentic retrieval 则是：

```text
Agent 判断是否需要检索
  -> 第一次 query
  -> 发现证据不足或冲突
  -> 改写 query / 分解子问题 / 换数据源 / 读取原文
  -> 直到证据足够或明确说明无法判断
```

适合研究、排障、企业跨系统分析；但必须配合检索轮数、时间、token、权限和失败处理限制，避免 Agent 无意义地反复搜索。

## 四、为什么 2024/2025 的 RAG Demo 和当前成熟应用看起来不同

早期常见图式是：

```text
PDF -> chunk -> embedding -> vector DB -> top-k -> prompt
```

这个骨架仍有效，但单独使用已不足以解决真实企业知识问题。较成熟的系统把关注点从“有没有向量库”转向以下问题。

### 4.1 从单一向量相似度到混合、权限、版本和时效

企业问题可能包含：

```text
政策编号、合同号、函数名、错误码、组织权限、已废止版本、生效日期
```

因此更合理的顺序通常是：

```text
身份 / tenant / role
  -> ACL 与文档状态过滤
  -> 版本、时间、生效日期过滤
  -> keyword + vector + structure retrieval
  -> rerank
```

而不是一开始就对所有文档做向量相似度。

### 4.2 从纯文本块到多模态、结构感知证据

重要信息经常藏在表格、流程图、财务报表、PPT 布局、扫描页和图片标注中。现代资料处理更强调保留：

```text
文本 + 标题层级 + 页码 + 表格结构 + 图表说明
+ 原始页面 / 图片 + 文档版本 + 来源链接
```

最终给模型的不是“第 42 个裸文本 chunk”，而应尽量是能回溯的证据：哪份文档、哪个版本、第几页、哪一节、何时生效。

### 4.3 从单一文档库到多源事实编排

企业问题往往同时需要：

```text
稳定制度 / 手册       -> RAG / 文档检索
实时订单 / 审批 / 库存 -> 数据库或业务 API
代码 / issue / PR      -> 代码仓库和工单工具
公开动态信息           -> Web Search
```

**精髓标记：不是所有知识都应向量化。稳定的非结构化知识适合检索；实时结构化事实更适合 API / SQL；Agent 负责在这些能力之间编排。**

### 4.4 从“多塞资料”到 Context Engineering

检索到 20 段文字后全部塞进 prompt，常带来成本、冲突、噪声和注意力分散。更好的链路是：

```text
召回
  -> 去重 / 过滤过期材料
  -> rerank
  -> contextual compression
  -> 保留 provenance
  -> 在 token budget 内注入证据
```

这里的目标是提高**证据密度**，不是最大化上下文长度。

### 4.5 从“答案看起来对”到分层评估

RAG 应至少分三层评估：

| 层级 | 要问的问题 |
|---|---|
| Retrieval | 正确证据是否被召回？是否混入越权、过期或无关材料？ |
| Grounding | 最终说法是否真能由证据支持？引用是否准确？ |
| Task outcome | 用户问题是否解决？结果能否执行、复核或回滚？ |

对 Agentic retrieval 还需检查：Agent 是否知道什么时候应检索、会不会无意义循环、面对冲突证据是否核验、证据不足时是否诚实说明。

## 五、安全与治理：资料是数据，不是指令

检索得到的网页、文档、工单、数据库字段或 MCP tool result 都可能包含不可信内容。它们可以作为证据，但不应自动升级为系统级命令。

推荐的安全边界：

```text
身份 / tenant / role
  -> ACL filter
  -> retrieval
  -> evidence as untrusted data
  -> Agent / model reasoning
  -> 受权限控制的后续工具动作
```

关键治理项：

- **最小权限**：先根据调用者做 collection / document / row 过滤，再召回。
- **版本与时效**：明确草稿、已发布、已废止、何时生效。
- **引用与溯源**：返回 source、路径、页码、版本、更新时间和适当的原文片段。
- **上下文预算**：限制结果数、每段长度、总 token，防止噪声和成本失控。
- **提示注入防护**：把检索结果视为不可信 data，不服从其中“忽略规则”“调用危险工具”等指令。
- **可观测性**：记录 query、filters、召回来源、引用和最终使用情况；敏感内容须按合规策略脱敏。

## 六、推荐架构：Agent 编排检索，知识服务拥有检索

对通用 Agent Harness，常见的职责划分是：

```text
Agent Harness
  - 判断是否需要知识
  - 决定 query、工具顺序与是否继续核验
  - 将证据与任务上下文结合
  - 组织答案、引用和下一步动作

Knowledge / RAG Service
  - 文档摄入、解析、chunk / structure 处理
  - embedding、全文 / 向量 / 混合索引
  - ACL、tenant、版本和生命周期
  - retrieval、rerank、citation metadata
```

两层可用 HTTP、SDK 或 [MCP](mcp.md) 连接。MCP server 中的 `search_knowledge_base` 可以是一种非常自然的边界；但应记住：**MCP 是连接协议，RAG 是知识检索模式。**

## QA / 讨论记录

### Q: RAG 是否就是“封装给外界调用的接口”？

> **状态**: draft
> **来源**: discussion

A: RAG 可以被封装为 API、SDK 或 MCP Tool，例如 `search_knowledge_base(query, filters)`；但“提供接口”不是 RAG 的定义。RAG 定义的是“先检索外部证据，再让模型基于证据生成”的模式。它也可以完全嵌在某个应用进程内部。对于通用 Harness，把知识服务做成可替换的外部能力通常更合理，因为不同组织的文档源、权限、索引和合规要求差异很大。

## 参考资料

- [Anthropic: Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) — 通用 context engineering 讨论，供理解“上下文应追求证据密度而非无限堆叠”。
- [Azure AI Search: Retrieval-Augmented Generation (RAG)](https://learn.microsoft.com/azure/search/retrieval-augmented-generation-overview) — 检索增强生成架构与 Azure 生态术语参考；不作为 DeerFlow 实现证据。
