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

### Q: Hermes 的 `run_conversation` 和 Claw-Code 的 `run_turn` 都是手写 loop，为什么 Hermes 长这么多？

> **状态**: draft  
> **来源**: discussion / source-code

A: Hermes 的 loop 更像典型 agent-loop god function：Agent Loop 天然是“控制流磁铁”，memory prefetch、plugin hooks、provider fallback、empty response recovery、interrupt / steer、session persistence、context compression、tool guardrails 等都依赖模型调用前后、工具执行前后、turn 结束等精确位置，因此容易聚到 `run_conversation` 周边。Hermes 已经把部分细节外提到 `build_turn_context(...)`、`tool_executor.py`、transport normalize、`finalize_turn(...)` 等模块，但主循环仍保留大量 retry / fallback / continue / break / final 的流程分叉。它的长函数是维护性风险，但也反映真实长期个人 Agent 在多 provider、多工具、多中断场景下的工程压力。

### Q: Hermes 的 loop 准备过程和 Claw-Code 基本类似吗？

> **状态**: draft  
> **来源**: discussion / source-code

A: 在结构角色上类似：两者进入模型/工具循环前都要准备 messages、system prompt、历史上下文、工具/配置、压缩和本轮状态。但 Claw-Code 准备的是 coding turn runtime，偏本地 session、项目上下文、权限、工具和 `maybe_auto_compact`；Hermes 准备的是 personal agent turn context，`build_turn_context(...)` 还会处理 memory prefetch、plugin context、todo/nudge hydration、session persistence、crash-resilience、external memory 等长期协作上下文。也就是说，Hermes 不是只“多了个人历史”，还多了长期运行和多入口协作所需的上下文准备。

### Q: Hermes 的 `interrupt` 和 `steer` 有什么区别，为什么适合长期个人 Agent？

> **状态**: draft  
> **来源**: discussion / source-code

A: `interrupt` 是硬打断，语义是“停下当前 loop，优先响应用户新消息”，会影响主 loop、当前执行线程、并发工具 worker 和子 agent。`steer` 是软引导，语义是“不要停，当前工具跑完后把用户补充方向带给下一轮模型”。长期个人 Agent 经常遇到用户中途补充方向但不想完全打断的情况，因此 `steer` 相当于“扶方向盘”，`interrupt` 相当于“踩刹车”。源码层面 Hermes 会把 steer 文本暂存在 `_pending_steer`，在工具结果产生后追加到 tool message 中，让下一轮 API 调用看到。

### Q: 软引导是不是简单地在下一轮插一句 user message？

> **状态**: draft  
> **来源**: discussion / source-code

A: 概念上像“下一轮补一句方向”，工程上不能随便插入新的 user message。tool-calling 协议通常要求 assistant 的 tool_calls 后面跟对应 tool result；如果 tool result 未补齐就插 user message，可能破坏 role alternation 或 tool_call_id 对齐。Hermes 的做法是把 steer 文本暂存后追加到最后一个 tool result，保持消息序列类似 `assistant(tool_calls) -> tool(result + steer) -> assistant(next)`。这个点和 Agent Loop 有关，但完整机制更适合后续放到 HITL / interaction runtime / message protocol 或 tool-calling 专题继续核验。

### Q: Hermes 的 `IterationBudget` 和 Claw-Code 的 `max_iterations` 本质差在哪？

> **状态**: draft  
> **来源**: discussion / source-code

A: 两者都防止工具循环无限跑，但抽象层级不同。Claw-Code 的 `max_iterations` 更像“当前 `run_turn` 最多循环 N 次”的刹车。Hermes 也有 `max_iterations`，但还引入 `IterationBudget`，更像 agent / subagent 的运行额度账户，支持 `consume()`、`refund()` 和线程安全的 `remaining` 查询；某些程序化工具调用还可以 refund。可以概括为：Claw-Code 的 `max_iterations` 是循环刹车，Hermes 的 `IterationBudget` 是运行额度账户。

### Q: Hermes 的 memory / session persistence 属于 Agent Loop 还是后续 memory 专题？

> **状态**: draft  
> **来源**: discussion

A: 两者都有关，但层次不同。Agent Loop 阶段只需要说明 memory / session persistence 如何影响当前 turn：turn 开始时 memory prefetch 可能注入输入，API call 前会拼接外部上下文，工具调用前后会 flush session，工具结果进入 messages 后影响下一轮模型调用，上下文过长会触发 compression。memory 数据结构、事实提取、偏好沉淀、procedural memory、技能演化、污染防护等内部机制，应留到后续 memory / session 专题深入。

### Q: Hermes 这么多 provider fallback / empty response recovery，是不是说明它只是“多模型兼容壳”？

> **状态**: draft  
> **来源**: discussion / source-code

A: Hermes 确实有很厚的多 provider 兼容层，loop 里大量处理 OpenAI-compatible、Anthropic Messages、Bedrock、Codex Responses、OpenRouter、本地模型、空响应、thinking-only、partial stream、invalid tool args、fallback provider 等问题。但它不只是通用 LLM SDK；这些兼容和恢复能力服务于“长期个人 Agent 在真实、多变、不稳定模型环境里持续协作”的目标。provider fallback 是长期稳定性的底层能力，而不是 Hermes 的全部定位。

### Q: OpenClaw Agent Loop 是否只是普通 `while tool_use`？

> **状态**: draft
> **来源**: discussion / source-code

A: 不是。OpenClaw 的核心模型/工具循环确实是手写在 [agent-loop.ts](../../openclaw/packages/agent-core/src/agent-loop.ts) 中，尤其是 `runAgentLoop(...)`、`runAgentLoopContinue(...)` 和 `runLoop(...)`；但它不是单纯的 `while tool_use`。它外面还有 [Agent](../../openclaw/packages/agent-core/src/agent.ts) 负责状态、事件和 `steer` / `followUp` 队列，再外面由 [AgentSession](../../openclaw/src/agents/sessions/agent-session.ts) 接入产品会话、hook、compaction、retry、持久化和事件处理。更准确地说，OpenClaw 是“手写 core double loop + Agent 事件状态机 + AgentSession 产品会话外壳”。

### Q: OpenClaw 的 double loop 怎么理解？

> **状态**: draft
> **来源**: discussion / source-code

A: 可以把 OpenClaw 的 double loop 理解成“外层处理追加消息，内层处理当前任务”。内层 loop 处理普通模型/工具循环：模型要工具、工具返回结果、模型继续思考；同时也处理运行中用户发来的 `steer`。外层 loop 处理 Agent 到结束点后用户追加的 `followUp`，如果还有 follow-up，就再开下一轮。口语化地说：内层是“这件事没干完，继续干”；外层是“这件事干完了，但用户又追加了，接着干下一件”。源码主线见 [agent-loop.ts](../../openclaw/packages/agent-core/src/agent-loop.ts)，入口包括 `runLoop(...)`、`streamAssistantResponse(...)` 和 `executeToolCalls(...)`。

### Q: OpenClaw 的 `steer` / `followUp` 队列有什么价值？

> **状态**: draft
> **来源**: discussion / source-code

A: 它把用户中途输入拆成两种不同语义：`steer` 是 Agent 正在运行时用户补充方向，类似“扶方向盘”，影响当前任务后续模型调用；`followUp` 是 Agent 准备结束或已经结束后用户追加下一句，类似“再补一张工单”，由外层 loop 开启下一轮处理。这样可以避免把运行中引导、结束后追加和硬打断都混成一种普通 user message。源码入口见 [Agent.steer(...)](../../openclaw/packages/agent-core/src/agent.ts) 和 [Agent.followUp(...)](../../openclaw/packages/agent-core/src/agent.ts)，执行调度见 [runLoop(...)](../../openclaw/packages/agent-core/src/agent-loop.ts)。

### Q: OpenClaw 的 Session 层分离和 double loop 是一回事吗？

> **状态**: draft
> **来源**: discussion / source-code

A: 相关但不是一回事。Session 层分离是架构分层：`AgentSession` 负责产品会话、模型校验、hook、compaction、retry、持久化和事件处理，`Agent` / `runLoop` 负责 Agent 状态与模型/工具执行。double loop 是运行控制流分层：外层处理 `followUp` / 追加消息，内层处理 tool call / tool result / `steer`。可以记成：Session 分离回答“谁负责产品会话”，double loop 回答“运行时怎么处理消息和工具”。

### Q: OpenClaw 与 DeerFlow / Claw-Code 的精髓差异是什么？

> **状态**: draft
> **来源**: discussion / source-code

A: 和 DeerFlow 比，DeerFlow 更像“长任务工作流平台的 run 控制”，核心是 Gateway run lifecycle、LangGraph runtime、run/thread/checkpoint/stream/middleware/cancel/clarification 等生命周期治理；OpenClaw 更像“聊天式 Agent 产品的实时会话控制”，核心是手写 `runLoop`、事件状态、`steer` / `followUp` 队列和 session runtime。和 Claw-Code 比，Claw-Code 更像“本地 CLI 一轮干到底”，核心是 `ConversationRuntime::run_turn` 主干；OpenClaw 更像“有事件、有队列、有状态的 Agent session runtime”，核心是 `AgentSession -> Agent -> runLoop` 分层。

### Q: OpenClaw 的 steer 和 DeerFlow 的 HITL / clarification 有什么区别？

> **状态**: draft
> **来源**: discussion / source-code

A: OpenClaw 的 `steer` 更贴近聊天产品里的运行中软引导：Agent 正在执行，用户补一句方向，系统把它放入 steering queue，让后续模型调用看到。DeerFlow 也有人机协同和中断 / 澄清能力，但更偏 run lifecycle / middleware / checkpoint 级别：例如 `ClarificationMiddleware` 可以把控制权交回用户，`RunManager` 管理 run 的并发、取消、interrupt / rollback 策略。可以类比为：OpenClaw 像“副驾扶方向盘”，DeerFlow 像“工作流节点暂停等待用户确认”。两者不是谁有谁没有，而是控制粒度和架构位置不同。

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
