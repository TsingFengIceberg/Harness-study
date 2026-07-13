# Dify 学习笔记

> LLM 应用开发平台样本：把模型、知识库 / RAG、Workflow、Agent、工具扩展与应用交付放在同一产品层，适合与 Agent Harness 和自动化平台比较其边界。

## 源码

- **Submodule**: [dify/](../../../submodules/dify/) — 指向 `langgenius/dify`
- **官方仓库**: [github.com/langgenius/dify](https://github.com/langgenius/dify)
- **当前快照**: `e35187f37626a1d3a7af5bedbebc19d40cf20cb5`（2026-07-13）
- **许可提示**: [Dify Open Source License](../../../submodules/dify/LICENSE)，以 Apache 2.0 为基础并附加条件；不要简单等同为无附加条件的 Apache-2.0。

## 研究定位

Dify 不是单纯的 Agent loop SDK。它将模型接入、应用配置、Dataset / RAG、可视化 Workflow、Agent、工具 / 插件 / MCP，以及应用 API 和运行观测组织为一套 LLM 应用平台。

在本仓库中，它是 DeerFlow 等 Agent Harness 的相邻研究对象：

```text
Agent Harness：强调 Agent runtime、工具执行、Memory、Sandbox、长任务治理
Dify：强调把模型和知识能力做成可配置、可交付、可运营的 AI 应用
```

其初步定位与 [Coze Studio](../coze-studio/README.md) 有重叠，二者的阶段性边界讨论见 [Coze Studio 与 Dify 的平台定位](../../comparison/qa.md#q-coze-studio-和-dify-应该如何做第一轮平台定位比较)。

## 笔记索引

| 文档 | 状态 | 说明 |
|---|---|---|
| `platform-architecture.md` | planned | 应用、模型、API、Web、后台任务和存储组件的总体边界。 |
| `rag-knowledge.md` | planned | 文档摄取、清洗、切分、embedding、索引、检索、重排和 Dataset 治理。 |
| `workflow-agent.md` | planned | Workflow 图运行时、Function Calling / ReAct Agent Runner 及工具回流。 |
| `plugins-mcp-tools.md` | planned | 内置工具、插件、自定义工具和 MCP 的发现、授权、执行边界。 |
| `llmops-observability.md` | planned | 应用日志、trace、评测、模型与生产质量的观测闭环。 |

## 源码入口

| 模块 | 源码 | 首轮关注点 |
|---|---|---|
| API / 应用启动 | [api/app_factory.py](../../../submodules/dify/api/app_factory.py) | 后端应用装配、服务入口与模块边界。 |
| Agent Runner | [api/core/agent/](../../../submodules/dify/api/core/agent/) | `BaseAgentRunner`、Function Calling 与 CoT / ReAct 路径。 |
| RAG | [api/core/rag/](../../../submodules/dify/api/core/rag/) | 清洗、提取、切分、embedding、索引、检索和 rerank 的分层。 |
| 检索实现 | [dataset_retrieval.py](../../../submodules/dify/api/core/rag/retrieval/dataset_retrieval.py) | dataset 检索、关键词 / 向量评分、metadata filter 与追踪入口。 |
| Workflow | [api/core/workflow/](../../../submodules/dify/api/core/workflow/) | 图拓扑、节点运行时、变量池和 workflow entry。 |
| MCP | [api/core/mcp/](../../../submodules/dify/api/core/mcp/) | MCP client / server / auth / session 的实现边界。 |
| 工具与插件 | [api/core/tools/](../../../submodules/dify/api/core/tools/) / [api/core/plugin/](../../../submodules/dify/api/core/plugin/) | Tool schema、插件运行和第三方扩展治理。 |
| Telemetry | [api/core/telemetry/](../../../submodules/dify/api/core/telemetry/) | 观测与 trace 的代码入口。 |

## 相关文档

- [RAG 基础与现代检索](../../concepts/rag.md)：Dify 的 RAG 源码研读应回到该概念页区分 RAG、Memory、文件访问和 MCP。
- [MCP 基础与安全边界](../../concepts/mcp.md)：MCP 是外部能力接入协议，不等于 Dify 内建 RAG。
- [横向 QA](../../comparison/qa.md)：保留 Dify / Coze 的阶段性平台定位和后续待核验问题。
