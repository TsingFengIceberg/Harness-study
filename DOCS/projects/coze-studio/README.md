# Coze Studio 学习笔记

> 可视化 AI Agent / 应用开发平台样本：围绕 Agent、App、Workflow 和资源（Plugin、Knowledge、Database、Prompt 等）组织开发、调试与交付能力。

## 源码

- **Submodule**: [coze-studio/](../../../submodules/coze-studio/) — 指向 `coze-dev/coze-studio`
- **官方仓库**: [github.com/coze-dev/coze-studio](https://github.com/coze-dev/coze-studio)
- **当前快照**: `22275b1c2661d35344a7493cffe401e8cc61cf8e`（2026-04-20）
- **许可**: [Apache License 2.0](../../../submodules/coze-studio/LICENSE-APACHE)

## 研究定位

Coze Studio 是 Coze 开放出来的核心 Agent / 应用开发引擎，不应与完整商业 Coze 产品的所有功能直接画等号。其公开 README 将模型服务、Agent、App、Workflow、Plugin、Knowledge Base、Database、Prompt、API 和 Chat SDK 组合为一体化的低代码 / 可视化平台。

在本仓库中，它是与 [Dify](../dify/README.md) 同层的 Agent / LLM 应用平台样本，而不是 DeerFlow 这类以 Agent Harness runtime 为核心的项目。后续应先按同一维度核验运行时、RAG、插件、授权和交付实现，再归纳平台定位。

> **边界提醒**：与 Coze Studio 相关、但承担 Prompt、评测、实验和 Trace 观测职责的 [CozeLoop](../cozeloop/README.md) 是单独的 AgentOps 项目，不应误写成 Coze Studio 的同一运行时模块。

## 笔记索引

| 文档 | 状态 | 说明 |
|---|---|---|
| `platform-architecture.md` | planned | Go 微服务 / DDD 后端与 React / TypeScript 前端的总体边界。 |
| `agent-workflow-runtime.md` | planned | Agent、App、Workflow 的编排和执行关系。 |
| `resources-plugin-knowledge.md` | planned | Plugin、Knowledge Base、Database、Prompt、变量等资源模型及其权限边界。 |
| `api-chat-sdk.md` | planned | conversation / workflow API 和 Chat SDK 的应用交付面。 |
| `security-deployment.md` | planned | 自托管模型 / 插件配置、Python code node、SSRF 和公开网络部署边界。 |

## 源码入口

| 模块 | 源码 | 首轮关注点 |
|---|---|---|
| 项目总览 | [README.md](../../../submodules/coze-studio/README.md) | 公开能力列表、部署方式和 Coze 开源版 / 商业版边界。 |
| 后端入口 | [backend/main.go](../../../submodules/coze-studio/backend/main.go) | 服务启动与应用装配入口。 |
| 应用层 | [backend/application/](../../../submodules/coze-studio/backend/application/) | Agent、App、Workflow 等业务用例的组织。 |
| 领域层 | [backend/domain/](../../../submodules/coze-studio/backend/domain/) | 领域对象、业务规则和跨资源边界。 |
| 基础设施层 | [backend/infra/](../../../submodules/coze-studio/backend/infra/) | 存储、RPC、外部服务和基础设施适配。 |
| 前端应用 | [frontend/apps/](../../../submodules/coze-studio/frontend/apps/) | 可视化 Agent / Workflow / 管理 UI 的入口。 |
| 接口定义 | [idl/](../../../submodules/coze-studio/idl/) | 服务接口与跨模块契约。 |

## 相关文档

- [Dify 学习笔记](../dify/README.md)：同层平台样本入口。
- [Coze Studio 与 Dify 的第一轮定位比较](../../comparison/qa.md#q-coze-studio-和-dify-应该如何做第一轮平台定位比较)：阶段性讨论，不代替源码专题。
- [MCP 基础与安全边界](../../concepts/mcp.md)：后续研究 Plugin / 外部工具时的共同协议和治理语言。
