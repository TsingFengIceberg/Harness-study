# CozeLoop 学习笔记

> AgentOps / LLMOps 生命周期平台样本：面向 Prompt 开发调试、评测数据与实验、Trace 上报和观测，补充 Coze Studio 的 Agent / 应用构建层。

## 源码

- **Submodule**: [cozeloop/](../../../submodules/cozeloop/) — 指向 `coze-dev/coze-loop`
- **官方仓库**: [github.com/coze-dev/coze-loop](https://github.com/coze-dev/coze-loop)
- **当前快照**: `4546006c6a5b176100fd4690ab469183cdc1a442`（2026-07-17）
- **许可**: [Apache License 2.0](../../../submodules/cozeloop/LICENSE)

## 研究定位

CozeLoop 不是 Coze Studio 中“再造一个 Agent”的子模块。它是独立的 Agent 生命周期与优化平台，公开能力重点为：Prompt 开发和调试、评测集 / evaluator / experiment 管理，以及 SDK trace 上报与查询。

可以先将二者分层理解：

```text
Coze Studio：构建 Agent / App / Workflow / Plugin / Knowledge 等应用能力
CozeLoop：开发调试、评测实验、Trace 观测与持续优化能力
```

它在本仓库中的角色接近 [LiteLLM](../litellm/README.md) 所代表的“相邻基础设施样本”：不替代 Agent Harness，而是补齐生产 Agent 应用的质量与运行治理视角。

## 笔记索引

| 文档 | 状态 | 说明 |
|---|---|---|
| `architecture.md` | planned | 后端模块、前端、IDL 和部署边界。 |
| `prompt-development.md` | planned | Prompt 创建、调试和版本 / 运行记录。 |
| `evaluation-experiments.md` | planned | 评测集、evaluator、实验和指标统计。 |
| `trace-observability.md` | planned | SDK trace 上报、查询、观测与诊断链路。 |
| `agentops-comparison.md` | planned | 与 Dify LLMOps、LiteLLM logging / callbacks 及 Harness run event 的分层比较。 |

## 源码入口

| 模块 | 源码 | 首轮关注点 |
|---|---|---|
| 项目总览 | [README.md](../../../submodules/cozeloop/README.md) | Prompt、Evaluation、Observation 的公开能力和部署指引。 |
| 架构地图 | [ARCHITECTURE.md](../../../submodules/cozeloop/ARCHITECTURE.md) | Backend、Frontend、IDL、Release 的代码地图和横切关注点。 |
| 后端模块 | [backend/modules/](../../../submodules/cozeloop/backend/modules/) | Prompt、评测、Trace 等领域模块的实际分层。 |
| 基础设施 | [backend/infra/](../../../submodules/cozeloop/backend/infra/) | storage、RPC、MQ 等基础设施实现。 |
| 服务接口 | [idl/](../../../submodules/cozeloop/idl/) | 前后端 / 服务间接口契约。 |
| 前端 | [frontend/](../../../submodules/cozeloop/frontend/) | Prompt、评测和 Trace 的产品交互入口。 |
| 部署 | [release/](../../../submodules/cozeloop/release/) | Docker Compose、Helm 和环境配置边界。 |

## 相关文档

- [Coze Studio 学习笔记](../coze-studio/README.md)：Agent / 应用构建层与 AgentOps 层的边界。
- [Dify 学习笔记](../dify/README.md)：另一个应用平台样本，后续可比较内聚式 LLMOps 与独立 AgentOps 的取舍。
- [Model Routing / Cost / Token Budget](../../comparison/model-routing-cost-token-budget.md)：与 LiteLLM 的模型出口治理互补，但不应混同。
