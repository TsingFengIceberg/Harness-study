# Harness Study 横向 QA

> **状态**: draft | **用途**: 收集学习过程中出现的跨项目问题、阶段性讨论结论与待核验点。
>
> 本文是 QA 的临时收集区。回答可以来自讨论、Deep Research、源码阅读或官方文档；正式引用前需要回到对应 submodule 源码或官方文档复核。成熟结论后续迁移到 [synthesis/faq.md](../synthesis/faq.md) 或吸收到具体专题正文中。

## 记录规则

每个 QA 建议使用以下格式：

```markdown
### Q: xxx？

> **状态**: draft / to-verify / verified  
> **来源**: discussion / source-code / official-docs / deep-research / inference

A: xxx。
```

状态含义：

| 状态 | 含义 |
|---|---|
| `draft` | 当前阶段的讨论理解，尚未系统核验 |
| `to-verify` | 问题重要，但需要回到源码或官方文档确认 |
| `verified` | 已经由源码、仓库内文档或官方文档支撑 |

来源含义：

| 来源 | 含义 |
|---|---|
| `discussion` | 来自学习过程中的问答讨论 |
| `source-code` | 来自 submodule 源码或仓库内文档 |
| `official-docs` | 来自官方文档 |
| `deep-research` | 来自 Deep Research 报告 |
| `inference` | 基于多源资料的推断，需要谨慎使用 |

## 项目定位

### Q: Claude Code 算不算 SWE Agent？

> **状态**: draft  
> **来源**: discussion

A: 算。Claude Code 面向软件工程任务，能够读写代码、运行命令、修改文件、辅助调试和提交，因此可以视作 Coding / SWE Agent。但它更偏本地交互式 Coding Agent，并不等同于 OpenHands 这类平台化 SWE Agent。

### Q: OpenHands 和 Claw-Code 是否重复？

> **状态**: draft  
> **来源**: discussion / deep-research

A: 不完全重复。Claw-Code 更像 Claude Code-like 本地 CLI Harness，重点是本地 runtime、权限、工具和代码编辑体验；OpenHands 更像平台化 SWE Agent Harness，重点是 Agent Server、Sandbox / Workspace、事件、Web UI / Canvas、Automation 和多 backend。两者都处理软件工程任务，但架构层级不同。

### Q: OpenHands 的团队 / 平台 / 自动化能力和 Claw-Code / Claude Code-like CLI 的区别是什么？

> **状态**: draft  
> **来源**: discussion / deep-research

A: OpenHands 把 Coding Agent 放进 App Server、Workspace / Sandbox、Event、Automation、Web UI / Canvas、Agent Backend 管理组成的平台控制面中；Claw-Code / Claude Code-like CLI 主要强化单开发者本地交互式代码执行体验。后者可以通过外部脚本和平台包装实现部分自动化，但这些不是其默认架构核心。区别不是“谁更会写代码”，而是 OpenHands 把多人、多会话、多 workspace、远程 backend、事件状态和自动触发做成平台的一等公民。

### Q: Claude Code-like / SWE Agent 是否比通用 Agent Harness 更强？

> **状态**: draft  
> **来源**: discussion

A: 在工具原语层面通常更强，因为 SWE Agent 需要文件、shell、git、test、diff、权限、上下文压缩等复杂能力，很多通用任务可以由这些工具组合完成。但在架构形态层面不是绝对超集：DeerFlow 的长周期图编排、Hermes 的长期记忆、OpenClaw 的多端控制面、OpenHands 的平台化 SWE 控制面，都是各自独立强化的方向。更准确的说法是：SWE Agent 工具原语强，但不天然覆盖所有架构形态。

### Q: 这些项目是不是同一类东西？

> **状态**: draft  
> **来源**: discussion / deep-research

A: 它们都属于 Agent Harness 大范畴，但不是同一类东西。它们共享 agent loop、工具、上下文、状态、权限、执行环境、人机交互等基础构件；差异在于谁把哪一层能力做成架构核心。learn-claude-code 是最小教学模型，Claw-Code 是本地 Coding CLI，OpenClaw 是多端控制面，OpenHands 是平台化 SWE Agent，DeerFlow 是长周期任务编排，Hermes 是记忆进化型个人 Agent，claude-code-complete-guide_v2 是 Claude Code-like 学习参考。

### Q: 项目定位会不会变成源码阅读偏见？

> **状态**: draft  
> **来源**: discussion

A: 会有这个风险，因此定位只用于建立学习地图和比较维度，不能作为细节判断的预设。多数 Harness 的基础构件大同小异，后续阅读源码时应先按同一技术维度做事实核验，再回到定位解释差异。文档表达应尽量写“该项目在某方向更突出 / 更中心”，避免写成“其他项目没有 / 不能做”，除非已有源码或官方文档证据。

### Q: claude-code-complete-guide_v2 应该怎么定位？

> **状态**: draft  
> **来源**: discussion

A: 它作为 Claude Code-like Harness 的第三方学习参考资料保留，帮助理解 Claude Code 的架构、工具系统、权限安全、上下文、多 Agent、Hooks / Skills / Plugins 等机制；不作为本仓库核心 Harness 实现项目，也默认不在 `DOCS/projects/` 下建立纵向源码研读目录。

## Agent Loop / 控制流

### Q: Claw-Code 的 `run_turn` 为什么要检查最大迭代次数？

> **状态**: draft  
> **来源**: discussion / source-code

A: 在 Claw-Code 的 `ConversationRuntime::run_turn` 中，每一次“模型调用 + 可能的工具执行 + tool_result 回写”都算一次 loop iteration。`max_iterations` 是防止模型持续调用工具、工具结果又诱发下一轮工具调用，从而陷入无限循环的熔断阈值。源码位置：[conversation.rs](../../claw-code/rust/crates/runtime/src/conversation.rs)。后续写正式专题时应结合 CLI 配置、测试和默认值继续核验。

### Q: 为什么 Agent Loop 的最简形式可以抽象为 `if response.stop_reason != "tool_use": return; execute tool calls`？纯文本回答也算 tool call 吗？

> **状态**: draft  
> **来源**: discussion / source-code

A: 纯文本回答不算 tool call。这个抽象表达的是：模型每轮要么给出最终文本回答，要么请求外部动作（tool use / tool calls）。如果模型没有请求工具，Harness 就把当前 assistant 消息视为终止输出；如果模型请求工具，Harness 执行工具并把 tool_result 回写给模型，进入下一轮。不同供应商术语不同：Anthropic 常用 `tool_use` / `stop_reason == "tool_use"`，OpenAI 风格常说 `tool_calls`；本质都是“模型请求 Harness 执行外部动作”。

### Q: `claw-code/rust/crates/runtime/src/conversation.rs` 是 Claw-Code 的核心对话实现文件吗？

> **状态**: draft  
> **来源**: discussion / source-code

A: 是核心之一，尤其是本地 CLI runtime 的单轮对话 / 工具循环核心。该文件定义了 `ApiClient`、`ToolExecutor`、`ConversationRuntime` 和 `run_turn`，负责把 session、模型流式输出、tool_use 提取、权限检查、hooks、工具执行、tool_result 回写、自动压缩和 usage 汇总串起来。但它不是整个 Claw-Code 的全部：CLI 入口、工具注册、权限策略、sandbox、session 持久化、MCP/plugin 等还分布在其他模块。

### Q: Claw-Code Agent Loop 里延伸出的细节问题应该全部放在 Agent Loop 专题里吗？

> **状态**: draft  
> **来源**: discussion

A: 不必。`ConversationRuntime::run_turn` 会把模型流、工具、权限、session、hooks、compaction、summary 串在一起，因此很多问题虽然从 Agent Loop 里冒出来，但更适合放到后续对应的大专题中：provider stream 到 `ToolUse` 的转换属于 Agent Loop / Streaming；`ToolExecutor` 属于工具系统；`PermissionPolicy` / `PermissionPrompter` 属于权限与 HITL；`Session` 属于状态管理；`maybe_auto_compact` 属于上下文压缩；pre/post tool hooks 属于 Hooks / Middleware；`TurnSummary` 属于事件、观测和调用方边界；CLI 如何调用 `run_turn` 属于入口与产品形态。Agent Loop 专题只需要先画清楚主干控制流，并把这些分支问题链接到后续专题。

### Q: DeerFlow 的 Agent Loop 在哪里？为什么不像 Claw-Code 那样有一个明显的 `while tool_use`？

> **状态**: draft  
> **来源**: source-code / discussion

A: DeerFlow 的 Agent Loop 不集中在一个手写 `while tool_use` 函数里，而是由 Gateway run lifecycle + LangGraph agent runtime 共同构成。Gateway 的 run API 调用 `start_run(...)`，后台 worker 调用 `agent.astream(...)`，真正的“模型调用 -> tool calls -> tool messages -> 再调用模型”循环由 `create_agent(...)` 生成的 LangGraph / LangChain agent 执行。源码入口见 [thread_runs.py](../../deer-flow/backend/app/gateway/routers/thread_runs.py)、[services.py](../../deer-flow/backend/app/gateway/services.py)、[worker.py](../../deer-flow/backend/packages/harness/deerflow/runtime/runs/worker.py) 和 [agent.py](../../deer-flow/backend/packages/harness/deerflow/agents/lead_agent/agent.py)。

### Q: DeerFlow 的 `run_agent(...)` 是不是等价于 Claw-Code 的 `run_turn`？

> **状态**: draft  
> **来源**: source-code / discussion

A: 不完全等价。`run_agent(...)` 是 DeerFlow Gateway 的后台 run worker，负责构建 agent、调用 `agent.astream(...)`、转发 stream event、处理 abort / status / journal / checkpoint。它不是逐个解析 tool call 并执行工具的手写 loop。Claw-Code 的 `run_turn` 更像低层对话循环；DeerFlow 的 `run_agent(...)` 更像平台 run driver。可以概括为：Claw-Code 的 `run_turn` 是“对话循环本体”，DeerFlow 的 `run_agent` 是“平台运行驱动器”，内部模型/工具循环委托给 LangGraph agent runtime。

### Q: DeerFlow / Claw-Code 的 Agent Loop 为什么一个像函数，一个像生命周期 runtime？

> **状态**: draft  
> **来源**: discussion / source-code

A: 主要是前置架构设计不同。Claw-Code 面向本地 coding CLI，把模型调用、ToolUse 提取、权限 / hook、工具执行、tool_result 回写和终止条件显式串在 `ConversationRuntime::run_turn` 附近，优势是主干清楚、局部可调试。DeerFlow 面向 Gateway / LangGraph run，把执行抽象成 run/thread/checkpoint/stream，`run_agent(...)` 负责驱动生命周期，内部模型/工具循环交给 LangGraph runtime，优势是天然适合 Web、多入口、长任务、流式事件、取消和恢复。两者不是高低关系，而是“函数式 loop”与“生命周期式 run driver”的取舍。

### Q: “横切逻辑”和“内联式”在 Agent Loop 讨论里是什么意思？

> **状态**: draft  
> **来源**: discussion

A: Agent Loop 主线是“用户输入 -> 模型调用 -> 工具调用 -> 工具结果回写 -> 继续或结束”。权限检查、错误兜底、上下文压缩、token 预算、安全审计、日志、状态持久化、memory 注入等不是主线本身，却会插入主线很多位置，因此称为“横切逻辑”。“内联式”指这些横切逻辑直接写在主流程函数附近；Claw-Code 的 `run_turn` 更接近这种方式。DeerFlow 则把类似能力拆成 middleware、RunManager、checkpointer、StreamBridge 等多层机制，挂在 LangGraph agent runtime 外层。

### Q: `ToolErrorHandlingMiddleware` 是所有 tool call 错误的兜底吗？

> **状态**: draft  
> **来源**: source-code / discussion

A: 不是所有 tool call 错误的总兜底，而是“工具执行异常兜底”。它包住已经被 runtime 识别出的 `ToolCallRequest`，当具体工具函数抛异常时，把异常转换成 `ToolMessage(status="error")`，让模型看到错误并有机会换策略继续。provider 返回格式不合法、tool_calls 缺 tool result、tool name/schema 不匹配、工具输出过大、provider 调用失败等问题可能由 LangGraph/provider adapter、`DanglingToolCallMiddleware`、`ToolOutputBudgetMiddleware`、`LLMErrorHandlingMiddleware`、Guardrail / Safety middleware 等不同层处理。

### Q: Claw-Code 有没有 DeerFlow 这种 middleware？

> **状态**: draft  
> **来源**: discussion / source-code

A: 如果严格说 LangChain `AgentMiddleware` 这种统一 middleware chain，Claw-Code 没有。但它有很多 middleware-like 的横切机制：pre/post tool hooks、`PermissionPolicy` / `PermissionPrompter`、`ToolExecutor`、auto compaction、session persistence、usage tracker、sandbox / 安全检查等。区别在组织方式：Claw-Code 把横切逻辑显式串在 `run_turn` 主干附近；DeerFlow 把类似能力拆成 middleware、RunManager、checkpointer、StreamBridge 等多层机制。

### Q: DeerFlow 如何处理 loop 失控或长时间运行？

> **状态**: draft  
> **来源**: source-code

A: DeerFlow 主要通过多层机制处理：`RunManager` 管理同一 thread 上的并发 run，支持 reject / interrupt / rollback；worker 支持 cancel 和 abort event；middleware 链里有 `LoopDetectionMiddleware` 检测重复工具调用循环，也有 `TokenBudgetMiddleware` 限制 token 预算；`ClarificationMiddleware` 可以用 `Command(goto=END)` 把控制权交回用户。具体默认配置和触发条件后续应在配置专题继续核验。

## 调研材料使用

### Q: Deep Research 报告能不能直接作为最终结论？

> **状态**: draft  
> **来源**: discussion

A: 不能。Deep Research 报告适合作为 research-base 或问题清单，帮助确定比较维度和后续专题方向；但具体判断需要回到 submodule 源码、仓库内文档或官方文档逐项核验。

### Q: 本地 workflow 源码核验报告如何使用？

> **状态**: draft  
> **来源**: workflow / discussion

A: 本地 workflow 报告适合作为源码核验补充材料，尤其对 Claw-Code、OpenClaw、learn-claude-code、OpenHands 的路径和工程判断有参考价值。但 DeerFlow 与 Hermes Agent 的 inspect 子任务因 API 524 timeout 未完成，因此该报告不能替代完整六项目调研 Base。

## Hermes Agent 定位

### Q: Hermes Agent 比 DeerFlow 有特点的地方是什么？

> **状态**: draft  
> **来源**: discussion / deep-research

A: DeerFlow 更像长周期任务编排系统，核心是状态图、middleware、sandbox 和复杂任务流程治理；Hermes Agent 更像长期陪伴型个人 Agent，核心特色在跨会话记忆、个人偏好沉淀、经验转化为技能、以及面向日常多通道交互的持续协作。两者都能做复杂任务，但 DeerFlow 强在“把任务跑完并可控”，Hermes 强在“和同一个人长期共事并越用越贴合”。

### Q: Hermes Agent 比常规通用 Agent 多了什么，为什么能成为长期陪伴型私人 Agent？

> **状态**: draft  
> **来源**: discussion / deep-research

A: 常规通用 Agent 多数围绕单次会话、工具调用和任务完成设计；Hermes Agent 的特色在于将长期记忆、会话检索、个人偏好、程序化技能沉淀和多通道入口作为架构核心，让 Agent 不只是“能做任务”，而是能在多次互动后积累用户习惯、复用过往经验，并逐步形成面向个人的操作手册。

### Q: Hermes Agent 相比 OpenClaw 更先进或更有特色的地方是什么？

> **状态**: draft  
> **来源**: discussion / deep-research

A: OpenClaw 更强在 gateway/control-plane：多设备、多 IM、多入口、队列、审批和节点能力路由；Hermes Agent 更强在 Agent 内核的长期记忆与自我改进：它更关注如何把长期交互沉淀为可复用经验、技能和个人上下文。简单说，OpenClaw 先进在“连接更多入口和设备”，Hermes 先进在“让同一个 Agent 越用越懂你”。

## 学习方法

### Q: QA 应该每个问题单独成文件，还是附在各文档里？

> **状态**: draft  
> **来源**: discussion

A: 采用混合方式：局部解释型 QA 附在对应项目笔记或专题文档末尾；横向比较型 QA 先收集在本文；经过源码或官方文档核验后的稳定结论，再迁移到 [synthesis/faq.md](../synthesis/faq.md)。一般不建议每个 QA 单独建文件，避免碎片化。
