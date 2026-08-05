# Agent Systems Study

系统学习生产级 AI Agent 系统：从 Harness 架构与框架源码，到编排、工具、评测、安全与面试导向的工程实践。

本仓库以开源源码和官方资料为事实基础，纵向研读 Agent Harness、框架、平台与基础设施，横向比较共性机制，并将结论沉淀为概念笔记、项目研究、架构对比和面试课程。

## 研究范围

| 项目 | 说明 | 官方仓库 |
|---|---|---|
| [deer-flow/](submodules/deer-flow/) | 字节跳动开源的 AI Agent 框架，基于 LangGraph | [bytedance/deer-flow](https://github.com/bytedance/deer-flow) |
| [hermes-agent/](submodules/hermes-agent/) | Nous Research 的 Agent 框架 | [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) |
| [claw-code/](submodules/claw-code/) | Claude Code 的开源替代实现 | [ultraworkers/claw-code](https://github.com/ultraworkers/claw-code) |
| [openclaw/](submodules/openclaw/) | 另一个 Claude Code 开源替代 | [openclaw/openclaw](https://github.com/openclaw/openclaw) |
| [learn-claude-code/](submodules/learn-claude-code/) | 手把手教你构建 Claude Code 同款 Agent Harness，20 个模块从 Agent Loop 到完整系统 | [shareAI-lab/learn-claude-code](https://github.com/shareAI-lab/learn-claude-code) |
| [openhands/](submodules/openhands/) | OpenHands 平台控制面：Agent Canvas、App Server、Sandbox、自动化与多后端运行 | [OpenHands/OpenHands](https://github.com/OpenHands/OpenHands) |
| [software-agent-sdk/](submodules/software-agent-sdk/) | OpenHands 执行面：Agent Server、SDK Conversation / Agent、`openhands-tools` 工具包 | [OpenHands/software-agent-sdk](https://github.com/OpenHands/software-agent-sdk) |
| [litellm/](submodules/litellm/) | LLM Gateway / AI Gateway：统一 LLM provider 接入、OpenAI-compatible proxy、model routing、成本 / token budget 与 guardrails | [BerriAI/litellm](https://github.com/BerriAI/litellm) |
| [dify/](submodules/dify/) | LLM 应用开发平台：模型、RAG / 知识库、Workflow、Agent、工具扩展与应用 API / 交付 | [langgenius/dify](https://github.com/langgenius/dify) |
| [coze-studio/](submodules/coze-studio/) | Coze 开源 Agent / 应用开发平台：Agent、App、Workflow、Plugin、Knowledge Base 与 Chat SDK | [coze-dev/coze-studio](https://github.com/coze-dev/coze-studio) |
| [cozeloop/](submodules/cozeloop/) | Coze 相关 AgentOps / LLMOps 平台：Prompt 开发、评测实验、Trace 与观测；不等同于 Coze Studio Agent runtime | [coze-dev/coze-loop](https://github.com/coze-dev/coze-loop) |
| [langchain/](submodules/langchain/) | Agent / LLM 应用组件与组装框架：模型、消息、Runnable、Tool、Retriever、Agent 与 provider 集成 | [langchain-ai/langchain](https://github.com/langchain-ai/langchain) |
| [langgraph/](submodules/langgraph/) | 有状态 Agent 编排 runtime：StateGraph、Pregel、Checkpoint、Interrupt 与 durable execution | [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) |

## 学习参考

| 资料 | 说明 | 来源 |
|---|---|---|
| [claude-code-complete-guide_v2/](submodules/claude-code-complete-guide_v2/) | Claude Code 完全指南 V2，作为理解 Claude Code-like Harness 架构、工具系统、权限、安全、上下文、多 Agent、Hooks / Skills / Plugins 等机制的学习参考；不作为本仓库核心 Harness 实现项目 | [bcefghj/claude-code-complete-guide_v2](https://github.com/bcefghj/claude-code-complete-guide_v2) |
| [Agent 面试资料](references/agent-interview/README.md) | 第三方 2026-02-23 与 2026-07 两版 Agent 面试 PDF、机械提取稿和来源说明；用于建立问题集，不自动视为已核验结论 | 本地第三方资料 |
| [Xiaolin AI 面试知识库](references/agent-interview/xiaolinnote/README.md) | Agent、RAG、LLM 工具调用和大模型工程四个专题；用于问题发现、全文检索和来源对照，内容保持 `to-verify` | [小林面试笔记 AI 专题](https://www.xiaolinnote.com/ai/) |
| [JavaGuide AI 知识库](references/agent-interview/javaguide/README.md) | AI 侧栏 6 个分组、28 个页面，覆盖面试题、大模型基础、Agent、RAG 和系统设计；内容保持 `to-verify` | [JavaGuide AI 应用开发](https://javaguide.cn/ai/ai-core-concepts.html) |
| [SWE Agent 评测论文资料](references/swe-agent-evaluation/README.md) | SWE Agent evaluation 代表性论文原文；论文事实仍需在学习笔记中标明具体章节、表格和版本 | [SWE-bench arXiv](https://arxiv.org/abs/2310.06770) |

## 文档导航

学习笔记位于 `DOCS/` 目录，由**面试专项**、可复用的**概念底座**和**三层研究金字塔**组成：

```
DOCS/
├── interview/         ← 面试专项：联合问题目录、学习路线、口述答案与追问
│   ├── agent/         ← Agent 面试联合课程与模拟 QA
│   └── swe-agent-evaluation/ ← SWE Agent 评测论文、benchmark 机制与 QA
├── concepts/          ← 概念底座：跨项目的 RAG、MCP 等基础机制
│   ├── rag.md         ← RAG：检索增强生成、现代检索与安全边界
│   └── mcp.md         ← MCP：外部能力接入协议、工具与安全边界
├── projects/          ← 纵向深挖：每个项目的研读笔记
│   ├── deer-flow/     ← DeerFlow 笔记（含 sandbox-workspace.md 与早期归档 docs-old/）
│   ├── claw-code/     ← Claw-Code 笔记（本地 Coding CLI runtime / Agent Loop / sandbox-workspace）
│   ├── hermes-agent/  ← Hermes Agent 笔记（长期个人 Agent / run_conversation / sandbox-workspace）
│   ├── openclaw/      ← OpenClaw 笔记（事件驱动 Session / Message loop / sandbox-workspace）
│   ├── openhands/     ← OpenHands 笔记（平台化 SWE Agent Harness）
│   ├── litellm/       ← LiteLLM 笔记（LLM Gateway / Model Routing / Cost / Token Budget）
│   ├── dify/          ← Dify 笔记（LLM Application / RAG / Workflow / Agent）
│   ├── coze-studio/   ← Coze Studio 笔记（Visual Agent / App Platform）
│   ├── cozeloop/      ← CozeLoop 笔记（AgentOps / Evaluation / Trace）
│   ├── langchain/     ← LangChain 笔记（Agent / LLM Components and Assembly）
│   └── langgraph/     ← LangGraph 笔记（Stateful Agent Orchestration Runtime）
├── comparison/        ← 横向对比：同一维度横切多个项目
│   ├── agent-loop.md  ← Agent Loop 横向总结
│   ├── tool-system.md ← Tool System 横向总结
│   ├── context-management.md ← Context Management 横向总结
│   ├── permission-security.md ← Permission / Security / Guardrail 横向总结
│   ├── sandbox-systems.md ← Sandbox / Workspace 横向总结
│   ├── multi-agent.md ← Multi-Agent / Subagent 横向总结
│   ├── model-routing-cost-token-budget.md ← Model Routing / Cost / Token Budget 横向总结
│   └── qa.md          ← 横向学习 QA：跨项目问题、讨论结论、待核验点
└── synthesis/         ← 拔高归纳：共性设计模式与架构分类
    └── faq.md         ← 最终沉淀 FAQ：已验证、可复用的核心问答
```

此外，[claude-code-complete-guide_v2/](submodules/claude-code-complete-guide_v2/) 作为 Claude Code 架构学习参考资料，以 submodule 形式保留；[Agent 面试资料](references/agent-interview/README.md) 保留原始 PDF、机械提取稿，以及 [Xiaolin](references/agent-interview/xiaolinnote/README.md) 和 [JavaGuide](references/agent-interview/javaguide/README.md) 两套独立网页知识库。所有第三方资料都只用于问题发现、检索和来源对照，不自动构成本仓库的源码核验结论。

| 想看什么 | 去哪里 |
|---|---|
| Agent 面试联合学习路线与问题目录 | [`DOCS/interview/agent/`](DOCS/interview/agent/) |
| SWE Agent 评测论文与 benchmark 学习 | [`DOCS/interview/swe-agent-evaluation/`](DOCS/interview/swe-agent-evaluation/) |
| Xiaolin Agent / RAG / Tool Calling / LLM 面试资料 | [`references/agent-interview/xiaolinnote/`](references/agent-interview/xiaolinnote/README.md) |
| JavaGuide AI 应用开发知识库 | [`references/agent-interview/javaguide/`](references/agent-interview/javaguide/README.md) |
| 某个项目的源码怎么设计的 | [`DOCS/projects/<项目名>/`](DOCS/projects/) |
| RAG 是什么、与 Memory / 文件上传 / Skills 有何区别 | [`DOCS/concepts/rag.md`](DOCS/concepts/rag.md) |
| MCP 是什么、如何连接外部能力、与 RAG 有何区别 | [`DOCS/concepts/mcp.md`](DOCS/concepts/mcp.md) |
| DeerFlow 当前有哪些 RAG 相关能力、哪些没有 | [`DOCS/projects/deer-flow/rag.md`](DOCS/projects/deer-flow/rag.md) |
| LiteLLM LLM Gateway / Model Routing | [`DOCS/projects/litellm/README.md`](DOCS/projects/litellm/README.md) |
| Dify LLM 应用 / RAG / Workflow / Agent 平台 | [`DOCS/projects/dify/README.md`](DOCS/projects/dify/README.md) |
| Coze Studio Agent / App / Workflow 平台 | [`DOCS/projects/coze-studio/README.md`](DOCS/projects/coze-studio/README.md) |
| CozeLoop Prompt / Evaluation / Trace AgentOps 平台 | [`DOCS/projects/cozeloop/README.md`](DOCS/projects/cozeloop/README.md) |
| LangChain Agent / LLM 应用组件与组装框架 | [`DOCS/projects/langchain/README.md`](DOCS/projects/langchain/README.md) |
| LangGraph 有状态 Agent 编排 runtime | [`DOCS/projects/langgraph/README.md`](DOCS/projects/langgraph/README.md) |
| Coze Studio 与 Dify、或 Lark CLI 与 Lark OpenAPI MCP 的扩展讨论 | [`DOCS/comparison/qa.md`](DOCS/comparison/qa.md#项目定位) / [`MCP 外部能力接入`](DOCS/comparison/qa.md#mcp--外部能力接入) |
| Claw-Code 本地 Agent Loop | [`DOCS/projects/claw-code/agent-loop.md`](DOCS/projects/claw-code/agent-loop.md) |
| Claw-Code Sandbox / Workspace | [`DOCS/projects/claw-code/sandbox-workspace.md`](DOCS/projects/claw-code/sandbox-workspace.md) |
| OpenClaw Sandbox / Workspace | [`DOCS/projects/openclaw/sandbox-workspace.md`](DOCS/projects/openclaw/sandbox-workspace.md) |
| Hermes Agent Sandbox / Workspace | [`DOCS/projects/hermes-agent/sandbox-workspace.md`](DOCS/projects/hermes-agent/sandbox-workspace.md) |
| Tool System 项目笔记 | [`DOCS/projects/claw-code/tool-system.md`](DOCS/projects/claw-code/tool-system.md)、[`DOCS/projects/deer-flow/tool-system.md`](DOCS/projects/deer-flow/tool-system.md)、[`DOCS/projects/openclaw/tool-system.md`](DOCS/projects/openclaw/tool-system.md)、[`DOCS/projects/hermes-agent/tool-system.md`](DOCS/projects/hermes-agent/tool-system.md)、[`DOCS/projects/openhands/tool-system.md`](DOCS/projects/openhands/tool-system.md) |
| DeerFlow / Hermes / OpenClaw / OpenHands Agent Loop | [`DOCS/projects/deer-flow/agent-loop.md`](DOCS/projects/deer-flow/agent-loop.md)、[`DOCS/projects/hermes-agent/agent-loop.md`](DOCS/projects/hermes-agent/agent-loop.md)、[`DOCS/projects/openclaw/agent-loop.md`](DOCS/projects/openclaw/agent-loop.md)、[`DOCS/projects/openhands/agent-loop.md`](DOCS/projects/openhands/agent-loop.md) |
| Agent Loop 横向总结 | [`DOCS/comparison/agent-loop.md`](DOCS/comparison/agent-loop.md) |
| Tool System 横向总结 | [`DOCS/comparison/tool-system.md`](DOCS/comparison/tool-system.md) |
| Context Management 横向总结 | [`DOCS/comparison/context-management.md`](DOCS/comparison/context-management.md) |
| Permission / Security 横向总结 | [`DOCS/comparison/permission-security.md`](DOCS/comparison/permission-security.md) |
| DeerFlow Sandbox / Workspace | [`DOCS/projects/deer-flow/sandbox-workspace.md`](DOCS/projects/deer-flow/sandbox-workspace.md) |
| OpenHands Sandbox / Workspace | [`DOCS/projects/openhands/sandbox-workspace.md`](DOCS/projects/openhands/sandbox-workspace.md) |
| Sandbox / Workspace 横向总结 | [`DOCS/comparison/sandbox-systems.md`](DOCS/comparison/sandbox-systems.md) |
| Multi-Agent / Subagent 横向总结 | [`DOCS/comparison/multi-agent.md`](DOCS/comparison/multi-agent.md) |
| Model Routing / Cost / Token Budget 横向总结 | [`DOCS/comparison/model-routing-cost-token-budget.md`](DOCS/comparison/model-routing-cost-token-budget.md) |
| 生产部署取舍对比 | [`DOCS/comparison/production-deployment-tradeoffs.md`](DOCS/comparison/production-deployment-tradeoffs.md) |
| 整体功能特色与项目定位分析 | [`DOCS/comparison/project-positioning.md`](DOCS/comparison/project-positioning.md) |
| 多个项目在某个维度上怎么不同 | [`DOCS/comparison/`](DOCS/comparison/) |
| 学习过程中的横向问题与讨论结论 | [`DOCS/comparison/qa.md`](DOCS/comparison/qa.md) |
| 从这些项目中提炼的通用设计模式 | [`DOCS/synthesis/`](DOCS/synthesis/) |
| 已验证、可复用的最终 FAQ | [`DOCS/synthesis/faq.md`](DOCS/synthesis/faq.md) |

### QA 记录方式

学习过程中会持续产生 QA。采用**文档内局部 QA + 横向 QA 总集 + 最终 FAQ 沉淀**的方式管理：

- 局部问题：附在对应项目笔记或专题文档末尾的 `## QA / 讨论记录`
- 横向问题：先收集到 [`DOCS/comparison/qa.md`](DOCS/comparison/qa.md)，例如“OpenHands 和 Claw-Code 是否重复？”、“Claude Code 算不算 SWE Agent？”
- 最终结论：经过源码或官方文档核验后，再沉淀到 [`DOCS/synthesis/faq.md`](DOCS/synthesis/faq.md)
- 每个 QA 尽量标注状态：`draft` / `to-verify` / `verified`，避免把讨论结论误当最终结论

## 使用方式

### 克隆本仓库

```bash
git clone git@github.com:TsingFengIceberg/agent-systems-study.git
cd agent-systems-study
git submodule update --init --recursive
```

### 同步上游项目更新

```bash
git submodule update --remote --merge
git add submodules/<submodule-name>
git commit -m "chore: sync <submodule-name> to latest"
```

### 切换分支后

```bash
git checkout <branch>
git submodule update --recursive
```
