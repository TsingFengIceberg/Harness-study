# Harness Study

横向学习多个 Agent Harness 的设计思路与实现对比。

## 研究项目

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

| 资料 | 说明 | 官方仓库 |
|---|---|---|
| [claude-code-complete-guide_v2/](submodules/claude-code-complete-guide_v2/) | Claude Code 完全指南 V2，作为理解 Claude Code-like Harness 架构、工具系统、权限、安全、上下文、多 Agent、Hooks / Skills / Plugins 等机制的学习参考；不作为本仓库核心 Harness 实现项目 | [bcefghj/claude-code-complete-guide_v2](https://github.com/bcefghj/claude-code-complete-guide_v2) |

## 文档导航

学习笔记位于 `DOCS/` 目录，由一个可复用的**概念底座**和**三层研究金字塔**组成：

```
DOCS/
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

此外，[claude-code-complete-guide_v2/](submodules/claude-code-complete-guide_v2/) 作为 Claude Code 架构学习参考资料，以 submodule 形式保留在 `submodules/` 目录，不纳入 `DOCS/projects/` 的核心项目研读目录。

| 想看什么 | 去哪里 |
|---|---|
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

## Agent Loop 第一轮总结

五个主线 Harness 的 Agent Loop 第一轮研读已形成稳定比较，详见 [`DOCS/comparison/agent-loop.md`](DOCS/comparison/agent-loop.md)：

| 项目 | Agent Loop 精髓 | 比喻 |
|---|---|---|
| Claw-Code | 本地 CLI `run_turn`，一轮干到底 | 本地老师傅 / 本地老司机 |
| DeerFlow | Gateway run lifecycle + LangGraph runtime | 工作流调度中心 / 交通调度系统 |
| Hermes Agent | 大型 `run_conversation` + memory / fallback / steer | 长期私人助理 / 长期私人司机兼管家 |
| OpenClaw | AgentSession + Agent + double loop + steer/followUp | 可实时插话的聊天工作室 / 网约车系统 |
| OpenHands | App Server + Agent Server + SDK action/observation loop | 远程开发控制中心 / 车队运营平台 |

最浓缩的理解是：**Agent Loop 的本质都是“模型决策 -> 外部动作 -> 环境反馈 -> 再决策”，差异在于这个循环被放在本地函数里、框架 runtime 里、长期记忆大脑里、聊天 session runtime 里，还是平台化 Agent Server 里。**


## Tool System 第一轮总结

Tool System 专题已完成 Claw-Code、DeerFlow、OpenClaw、Hermes Agent 与 OpenHands 的第一轮源码研读。OpenHands 部分已接入 [software-agent-sdk/](submodules/software-agent-sdk/) 作为执行面源码核验入口。详见 [`DOCS/projects/claw-code/tool-system.md`](DOCS/projects/claw-code/tool-system.md)、[`DOCS/projects/deer-flow/tool-system.md`](DOCS/projects/deer-flow/tool-system.md)、[`DOCS/projects/openclaw/tool-system.md`](DOCS/projects/openclaw/tool-system.md)、[`DOCS/projects/hermes-agent/tool-system.md`](DOCS/projects/hermes-agent/tool-system.md)、[`DOCS/projects/openhands/tool-system.md`](DOCS/projects/openhands/tool-system.md) 与 [`DOCS/comparison/tool-system.md`](DOCS/comparison/tool-system.md)：

| 观察点 | 阶段性结论 |
|---|---|
| 工具系统定位 | Agent 触达外部世界的统一能力总线，不只是几个 function call。 |
| Claw-Code 风格 | 集中式工具中枢：`ToolSpec`、`GlobalToolRegistry`、执行分发、权限分类、ToolSearch 都集中在本地 tools 模块附近。 |
| DeerFlow 风格 | LangGraph 标准生产线 + middleware 化工具治理：`BaseTool` / `@tool` 接入 LangGraph agent runtime，DeerFlow 用 run lifecycle、ThreadState、SandboxMiddleware、ToolErrorHandling、Clarification、LoopDetection、TokenBudget 等中间件卡口治理工具调用。 |
| OpenClaw 风格 | 事件化工具调度与产品级治理：`AgentTool`、`createOpenClawCodingTools`、policy pipeline、before_tool_call wrapper、sequential / parallel batch 调度和 Tool Search 目录服务。 |
| Hermes 风格 | 长期个人 Agent 工具工作台：toolsets 菜单、registry 总账、Tool Search 渐进式发现、tool_executor 串起 memory / skills / todo / steer / guardrail / persistence。 |
| OpenHands 风格 | 平台控制面 + 执行面分离：`OpenHands/OpenHands` 管 Agent Canvas / App Server / Sandbox / automation，`OpenHands/software-agent-sdk` 管 Agent Server / SDK Conversation / Agent.step / `openhands-tools`；工具调用落到 ActionEvent / ObservationEvent 事件流。 |
| 权限 / 治理 | Claw-Code 的两道权限门较集中；OpenClaw 的多层 tool policy pipeline 与 before_tool_call approval / diagnostics / loop detection 较产品化；Hermes 需要拆分理解：toolsets 是可见性，scope gate 接近权限，plugin / approval 是执行前门，checkpoint 是回滚保险，guardrail 是防循环，result budget 是上下文保护。 |
| 工具目录精髓 | Claw-Code ToolSearch 是轻量目录检索器；OpenClaw Tool Search 是 search / describe / call / code-mode 的大工具目录服务；Hermes Tool Search 用 search / describe / call 把 MCP / plugin 非核心工具延迟暴露，同时保证核心工具永不 deferred。 |

第一轮横向理解是：**Tool System 的差异不只在“有哪些工具”，更在于工具定义、可见性、权限 / policy、串并行执行、结果回写、事件观测和横切治理被放在什么架构位置。**


## Permission / Security 第一轮总结

Permission / Security / Guardrail 专题已完成 Claw-Code、DeerFlow、OpenClaw、OpenHands 与 Hermes Agent 的第一轮源码研读。详见 [`DOCS/comparison/permission-security.md`](DOCS/comparison/permission-security.md)：

| 项目 | 权限 / 安全精髓 | 比喻 |
|---|---|---|
| Claw-Code | ToolSpec 默认权限、PreToolUse hook、PermissionPolicy / Prompter、PermissionEnforcer / 动态分类、Post hook 和 error tool_result | 本地 CLI 工具调用双闸门 |
| DeerFlow | Gateway authz、GuardrailMiddleware + provider、workflow safety middleware、RunManager 与 Sandbox 三层防线 | 工作流工厂安全生产线 |
| OpenClaw | tool policy pipeline 先控工具可见性，before_tool_call approval / hook / diagnostics 再控单次执行 | 工具门禁 + 审批工单系统 |
| OpenHands | ActionEvent、SecurityAnalyzer、ConfirmationPolicy、WAITING_FOR_CONFIRMATION、UserRejectObservation 与 workspace / sandbox | 远程开发园区安检 + 工位隔离 |
| Hermes Agent | toolsets / scope gate、dangerous command / ACP approval、plugin hooks、tool guardrails 与 memory / skills hygiene | 长期个人助理自我保护系统 |

第一轮横向理解是：**权限安全不只是“要不要问用户确认”，还包括工具可见性、动作风险评估、执行环境隔离、run 生命周期、失败 / loop 熔断、拒绝反馈和长期状态污染防护。**

## Sandbox / Workspace 第一轮总结

Sandbox / Workspace 专题已完成 DeerFlow、OpenHands、Claw-Code、OpenClaw 与 Hermes Agent 的第一轮源码研读。详见 [`DOCS/comparison/sandbox-systems.md`](DOCS/comparison/sandbox-systems.md)：

| 项目 | sandbox / workspace 精髓 | 比喻 |
|---|---|---|
| OpenHands | 平台化远程开发环境，ActionEvent 进入 sandbox，ObservationEvent 回流 | 远程开发园区 / 云端工位 |
| DeerFlow | workflow run 的受控执行环境，middleware / RunManager / sandbox 一起治理 | 工作流工厂的安全生产线 |
| Claw-Code | 本地 CLI workspace 边界 + 权限审批 + 可选 sandbox wrapper | 本地施工围栏 |
| OpenClaw | session-level SandboxContext，工具菜单和执行方式随 sandbox 改写 | 多端协作工作室的独立隔间 |
| Hermes Agent | 可配置 Terminal Environment，默认 local，可切 Docker / SSH / Modal / Daytona | 长期个人助理的工具工作台 |

第一轮横向理解是：**sandbox 不只是“有没有 Docker”，而是模型动作在哪里执行、workspace 边界在哪里、bash / terminal 如何受控、权限审批放在哪一层，以及长任务 / 多任务 / 子 agent 如何避免互相踩。**

## Multi-Agent / Subagent 第一轮总结

Multi-Agent / Subagent 专题已完成 DeerFlow、Claw-Code、OpenClaw、Hermes Agent 与 OpenHands 的第一轮源码研读，详见 [`DOCS/comparison/multi-agent.md`](DOCS/comparison/multi-agent.md)：

| 项目 | Multi-Agent 精髓 | 比喻 |
|---|---|---|
| DeerFlow | Lead Agent 通过 `task` 工具动态派工，SubagentExecutor 跑独立 LangGraph subagent，Delegation Ledger 留档 | 工作流工厂 |
| Hermes Agent | `delegate_task` 创建 child AIAgent，支持 leaf / orchestrator、批量并行、后台分身、active registry 与 interrupt | 私人助理分身术 |
| OpenHands | `enable_sub_agents` 打开平台能力，`AgentDefinition` 注册专业工种，`TaskToolSet` 派工并以 TaskObservation / UI card 回流 | 远程开发平台外包工位 |
| OpenClaw | ACP 父子 session 谱系、parent-owned-background、spawnDepth、subagentRole / controlScope 管理后台子会话 | 多会话工作室总控台 |
| Claw-Code | TaskPacket、TaskRegistry、Worker boot、TeamRegistry、worktree / permission / acceptance 构成本地任务协作系统 | 本地施工队任务看板 |

第一轮横向理解是：**多 Agent 的共同骨架是“派工、隔离、执行、回报、治理”；差异主要来自承载层不同，所以它会表现成 LangGraph `task` tool、Hermes `delegate_task`、OpenHands `TaskToolSet` / `AgentDefinition`、OpenClaw ACP 父子 session，或 Claw-Code TaskPacket / Worker / Team。**

## Model Routing / Cost / Token Budget 第一轮总结

Model Routing / Cost / Token Budget 专题已完成五个主线 Harness 的第一轮讨论沉淀，并已接入 [LiteLLM](DOCS/projects/litellm/README.md) 作为后续 LLM Gateway / Model Routing 基础设施样本，详见 [`DOCS/comparison/model-routing-cost-token-budget.md`](DOCS/comparison/model-routing-cost-token-budget.md)：

| 项目 | 模型 / 成本 / token budget 精髓 | 比喻 |
|---|---|---|
| DeerFlow | run config / app_config 解析模型，SubagentConfig 配置子模型，TokenBudgetMiddleware 做 run 级预算闸门 | 工作流工厂的能源调度室 |
| Hermes Agent | parent / child AIAgent 可分模型，max_iterations、child timeout、context compressor 和 background review 共同管长期成本 | 私人助理的用脑预算表 |
| OpenHands | LLM profiles、AgentDefinition.model、LLM metrics、Context Condenser 和 event log 投影共同构成平台计费面 | 远程开发平台的工位计费系统 |
| OpenClaw | subagent model / thinking defaults、per-call override、runTimeoutSeconds、resolvedModel / estimated cost 组成多会话模型档位 | 多会话控制台的模型档位面板 |
| Claw-Code | TaskPacket.model / provider 加上 scope、worktree、permission、acceptance，把成本控制前移到任务单 | 本地施工队的任务成本单 |

第一轮横向理解是：**不要把模型当成全局常量，要把模型当成可调度资源。主 Agent、子 Agent、后台任务、摘要器、记忆更新器、critic、planner、worker 都可以有不同的模型、thinking 档位、上下文预算和运行上限；成熟 Harness 的成本控制，不是“少用模型”，而是“让每一类工作用合适的模型和合适的预算”。**

LiteLLM 的接入会把这个专题从“Agent Harness 内部如何选择模型和限制预算”，进一步扩展到“模型网关层如何统一 provider、路由 deployment、做 virtual key / team / org 预算、记录 spend、执行 fallback / retry 和 guardrails”。

## 使用方式

### 克隆本仓库

```bash
git clone git@github.com:TsingFengIceberg/Harness-study.git
cd Harness-study
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
