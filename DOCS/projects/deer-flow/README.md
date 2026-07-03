# DeerFlow 学习笔记

> 字节跳动开源的 AI Agent 框架，基于 LangGraph 构建。

## 源码

- **Submodule**: [deer-flow/](../../../deer-flow/) — 指向 `bytedance/deer-flow`
- **当前快照**: `4e6248f013aaed84ad5250fe4969de44beebeb7e`
- **官方仓库**: [github.com/bytedance/deer-flow](https://github.com/bytedance/deer-flow)

## 笔记目录

### 早期笔记归档（docs-old）

| 来源 | 日期 | 路径 | 内容 |
|---|---|---|---|
| STUDY_DOCS | 2026-05-13 | [docs-old/STUDY_DOCS/](docs-old/STUDY_DOCS/) | 中间件防线 + 沙箱系统 |
| 网页端 AI 对话导出 | 2026-04-21 ~ 04-28 | [docs-old/chat-exports/](docs-old/chat-exports/) | HITL、沙箱、中间件五大阵营、Prompt 工程、Agent 组装 |

#### STUDY_DOCS 目录

| 文件 | 主题 |
|---|---|
| [middleware/Middle_Study.md](docs-old/STUDY_DOCS/middleware/Middle_Study.md) | 16 道中间件防线全景解析（洋葱模型） |
| [sandbox/sandbox_system.md](docs-old/STUDY_DOCS/sandbox/sandbox_system.md) | 沙箱系统全景架构（抽象基类 → Docker → 本地） |

#### 网页端 AI 对话导出

| 文件 | 内容 |
|---|---|
| [chat-export-v1-overview.md](docs-old/chat-exports/chat-export-v1-overview.md) | 概览版：按会话主题归纳的核心收获（143 行） |
| [chat-export-v2-detailed.md](docs-old/chat-exports/chat-export-v2-detailed.md) | 精细版：逐轮对话原文复刻，含全部技术细节（327 行） |

两份导出覆盖的 DeerFlow 主题：HITL 中断机制、三层线程池并发调度、沙箱控制面/计算面分离、中间件五大阵营与洋葱模型、多模态图片注入、Prompt 动态装配、Agent 组装与中间件注册顺序。

### 新笔记

| 文档 | 主题 | 状态 |
|---|---|---|
| [agent-loop.md](agent-loop.md) | Gateway Run + LangGraph agent runtime 控制流：run 创建、`agent.astream(...)`、middleware、工具调用、状态与终止条件 | draft |
| [tool-system.md](tool-system.md) | LangGraph 标准生产线 + middleware 化工具治理：`BaseTool` / `ToolCallRequest` / `ToolMessage` / `Command`、sandbox 工具、deferred MCP Tool Search 与生产部署取舍 | draft |

后续 DeerFlow 深入研读的新笔记将继续放在本目录下，例如：

- `architecture.md` — 整体架构梳理
- `middleware.md` — 中间件体系深入
- `sandbox.md` — 沙箱方案详解
- `state-machine.md` — 状态机 & HITL 机制

## 相关文档

- 横向对比见 [DOCS/comparison/](../../comparison/README.md)
- 综合归纳见 [DOCS/synthesis/](../../synthesis/README.md)
