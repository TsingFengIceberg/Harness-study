# DeerFlow RAG 相关能力映射：文件访问、Memory、Skills 与外部检索边界

> **日期**: 2026-07-10 | **状态**: draft | **涉及版本**: `c9fb9768d476e28de0294ac7a23cab9819b93f83`

## 相关文档

- 通用解释：[RAG：让模型先查证据，再基于证据回答](../../concepts/rag.md)
- 通用协议：[MCP：让 Agent 以标准协议连接外部能力](../../concepts/mcp.md)
- [Context Management](context-management.md)
- [Tool System](tool-system.md)
- [Sandbox / Workspace](sandbox-workspace.md)

## 一句话结论

当前 DeerFlow **没有观察到内置的经典向量 RAG 主线**：没有看到由 DeerFlow 核心负责的 embedding 生成、向量索引 / vector store、query-to-vector retrieval、hybrid fusion、reranker 或统一 citation / retrieval evaluation pipeline。

但它已经具备多种可组合的 RAG-adjacent 能力：

```text
上传文件与可选 Markdown 转换
+ Agent 调用 read_file / grep / glob 按需查原文
+ per-user / per-agent 长期 Memory
+ Skill 元数据发现与按需加载
+ MCP / config-defined tools 接外部知识库或检索服务
```

因此更准确的定位是：

> **DeerFlow 是能够编排检索的 Agent Harness，而不是内建固定检索栈的知识库 / 向量数据库产品。**

## 源码入口

| 能力 | 源码 | 作用 |
|---|---|---|
| 文件上传 API | [uploads.py](../../../submodules/deer-flow/backend/app/gateway/routers/uploads.py) | 向 thread 上传文件、列出和删除文件。 |
| 文档转换 | [file_conversion.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/utils/file_conversion.py) | PDF / Office 文档可选转换为同目录 Markdown。 |
| 上传文件上下文 | [uploads_middleware.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/uploads_middleware.py) | 注入文件名、路径、outline / preview，并引导 Agent 用 `read_file` / `grep` / `glob`。 |
| Memory 写入 | [memory_middleware.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/memory_middleware.py) | run 完成后筛选消息、异步排队更新长期 memory。 |
| Memory 注入 | [dynamic_context_middleware.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/dynamic_context_middleware.py) | 读取当前用户 / Agent memory snapshot，投影进模型上下文。 |
| Memory 存储与格式化 | [storage.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/memory/storage.py)、[prompt.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/memory/prompt.py) | JSON facts 存储、confidence 排序和 token-budgeted memory injection。 |
| Skill 发现 | [catalog.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/skills/catalog.py)、[describe.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/skills/describe.py) | 用名称 / description 的关键词或正则发现 Skill metadata，再按需读取完整 SKILL.md。 |
| MCP client / tools / cache | [client.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/mcp/client.py)、[tools.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/mcp/tools.py)、[cache.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/mcp/cache.py) | 配置 stdio/SSE/HTTP server、发现其 tools、按配置变化刷新缓存。 |
| 工具总装配 | [tools.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/tools/tools.py) | 汇总内置、配置、MCP、ACP、subagent 等工具。 |
| Memory retrieval 路线图 | [MEMORY_IMPROVEMENTS.md](../../../submodules/deer-flow/backend/docs/MEMORY_IMPROVEMENTS.md) | TF-IDF / context-aware memory retrieval 是规划项，不是已合入 RAG 功能。 |

## 一、把通用 RAG 阶段映射到 DeerFlow

| 通用 RAG 阶段 | DeerFlow 当前对应能力 | 判断 |
|---|---|---|
| 知识摄入 | thread upload、可选文档转 Markdown | 有局部能力，但主要服务当前 thread 文件。 |
| 文档切分 / embedding / 索引 | 未发现 DeerFlow 原生实现 | 不是内置 RAG。 |
| 候选召回 | 上传文件名 / stem / extension 的轻量匹配；Agent 自己用 grep / glob / read_file | 是 agentic file access，不是语义 chunk retrieval。 |
| 上下文组装 | UploadsMiddleware 注入 `<uploaded_files>`；DynamicContext 注入 memory | 有，但不是一个统一 RAG evidence packer。 |
| rerank / citations / retrieval eval | 未发现原生统一管线 | 外部知识服务应负责，或需另外实现。 |
| 多源外部知识 | MCP / config-defined tools 可接入 | 是最合理的扩展边界。 |

## 二、上传文件：Agent 自己翻档案，不是自动 RAG

### 2.1 运行时发生什么

上传文件进入当前 thread 的 uploads 目录；若启用文档转换，PDF、PPT、Excel、Word 等可被转换成同目录 Markdown。上传 API 在 [uploads.py](../../../submodules/deer-flow/backend/app/gateway/routers/uploads.py)，转换逻辑在 [file_conversion.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/utils/file_conversion.py)。

随后 `UploadsMiddleware` 将文件信息写入 `<uploaded_files>` 区块：文件名、虚拟路径、大小，以及转换 Markdown 中的 outline 或少量开头 preview。它明确告诉 Agent：

```text
根据 outline 的行号用 read_file 读相关段落
不确定位置时用 grep 搜关键词
用 glob 查文件名
文件不足时才考虑 web search
```

见 [uploads_middleware.py:112-253](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/uploads_middleware.py#L112-L253)。

### 2.2 它怎样选出优先展示的文件

文件选择并不是 embedding 或语义检索。`_query_match_strength(...)` 只看当前 query 是否包含：

```text
完整文件名
文件 stem
stem 中的 token
文件扩展名
```

然后按匹配强度和时间排序。见 [uploads_middleware.py:40-65](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/uploads_middleware.py#L40-L65)、[uploads_middleware.py:167-192](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/uploads_middleware.py#L167-L192)。

所以它更像：

```text
文件清单 + 目录索引
  -> Agent 决定怎么翻
```

而不是：

```text
用户问题
  -> 系统从所有文档自动召回最相关的 5 个证据 chunk
```

**精髓标记：DeerFlow 上传文件机制是“把档案室钥匙交给 Agent”；经典 RAG 是“图书管理员先找好相关页”。**

## 三、Memory：个人化长期经验，不是外部知识库检索

`MemoryMiddleware` 在 Agent 完成后筛选对话并异步排队，由 MemoryUpdater 用 LLM 将偏好、事实、纠正等沉淀进 per-user / per-agent 的 memory 数据。见 [memory_middleware.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/memory_middleware.py)。

下次对话中，DynamicContextMiddleware 读取 memory snapshot；格式化逻辑根据 confidence 和 token budget 选择可注入的 facts。见 [dynamic_context_middleware.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/dynamic_context_middleware.py)、[memory/prompt.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/memory/prompt.py)。

它适合记住：

```text
用户偏好
用户长期背景
显式纠正
长期目标
Agent 与该用户协作中形成的事实
```

它不等于“针对本次问题从海量公司文档找相关段落”。当前 Memory facts 是 JSON 结构化数据，不是向量；注入重点是 confidence、类别和 token budget，不是 query embedding 相似度。

上游 [MEMORY_IMPROVEMENTS.md](../../../submodules/deer-flow/backend/docs/MEMORY_IMPROVEMENTS.md) 中出现过 TF-IDF、current context、similarity 等想法，但该文档描述的是改进计划，不能写成已实现的 DeerFlow RAG。

## 四、Skills：检索做事方法，不是检索业务证据

开启 deferred discovery 后，`SkillCatalog.search(...)` 用 Skill 名和 description 做精确选择、前缀、正则 / 关键词匹配，最多返回若干候选。见 [catalog.py:41-101](../../../submodules/deer-flow/backend/packages/harness/deerflow/skills/catalog.py#L41-L101)。Agent 接着通过 `describe_skill` 得到 metadata 和 `SKILL.md` 位置，再按需读取工作流说明。

这回答的是：

```text
“遇到这个任务，我应加载哪份操作手册？”
```

RAG 通常回答的是：

```text
“哪份业务资料能证明这次回答的事实？”
```

二者都是 retrieval，但检索目标和使用目的不同。

## 五、MCP：把外部知识检索接成可调用工具

DeerFlow 的 MCP client 可以按配置连接 `stdio`、`sse`、`http` server。见 [mcp/client.py:10-67](../../../submodules/deer-flow/backend/packages/harness/deerflow/mcp/client.py#L10-L67)。启用的 server tools 会被发现并进入 DeerFlow 的可用工具集合；缓存的是 tool list / schema，不是知识向量索引。

因此，一个外部知识服务可以暴露：

```text
search_knowledge_base(query, collection, filters, top_k)
get_document_section(document_id, section_id)
```

推荐调用链：

```text
用户问题
  -> DeerFlow Agent 判断需要外部知识
  -> MCP search_knowledge_base
  -> 外部 RAG / Knowledge Service
       ingest / index / ACL / hybrid retrieval / rerank / citations
  -> 返回 chunks + source + version + score
  -> DeerFlow Agent 判断证据是否够、是否继续核验
  -> 组织答案、引用和后续动作
```

这样 DeerFlow 继续负责 Agent orchestration、工具选择、任务状态和上下文治理；外部服务继续负责文档生命周期、知识权限、检索质量和索引成本。

## 六、为什么不建议把固定 RAG 栈硬塞进 DeerFlow 核心

不同组织的知识源和约束变化很大：

```text
Confluence / Notion / 飞书文档 / GitHub / 网盘 / PDF
+ 数据库 / CRM / ERP / 工单 / 邮件 / IM
+ 不同 tenant 与 ACL 模型
+ 不同向量库、关键词索引、embedding 模型
+ 不同更新频率、合规和保留期限
```

如果 DeerFlow 固定实现“PDF -> chunk -> embedding -> 某个 vector DB”，它会迫使所有用户接受同一种文档处理、权限和索引选择。通过 MCP 或自定义 Tool 连接可替换的知识服务更符合通用 Harness 的职责边界。

不过，MCP 不是自动安全层：外部检索结果、文档内容和 tool result 仍应当被视为不可信数据；知识服务应在检索前应用 ACL / tenant / version 过滤，DeerFlow 侧还应有工具权限、结果预算和提示注入防护。

## QA / 讨论记录

### Q: DeerFlow 是否内置 RAG？

> **状态**: verified
> **来源**: discussion / source-code

A: 当前快照未观察到 DeerFlow 内置 embedding、向量库、语义 chunk retrieval、hybrid fusion、reranker 或统一 citation/evaluation pipeline。它提供的是文件上传后由 Agent 通过 `read_file` / `grep` / `glob` 按需访问、长期 memory 注入、Skill 发现，以及通过 MCP / 配置工具外接检索服务的能力。因此更适合称为“可编排 RAG-adjacent 能力的 Agent Harness”，而不是“内建向量 RAG 平台”。

### Q: DeerFlow 接入外部 RAG 时，检索结果应该永久写入 ThreadState 吗？

> **状态**: draft
> **来源**: inference / discussion

A: 默认不应把每次检索的完整 chunks 永久写成长期 ThreadState 或 Memory。检索结果通常有版本、权限和时效边界，长期保存会污染后续上下文并可能扩大敏感资料暴露面。更稳妥的设计是：把本轮必要证据作为受 token budget 控制的临时 tool result / context；只把经过确认、与用户协作有关的稳定偏好或结论按严格规则进入 Memory。若需要可恢复性，应保存受权限控制的 retrieval metadata、source reference、版本和摘要，而不是无差别持久化原文。
