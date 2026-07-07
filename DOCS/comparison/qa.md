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

A: 在 Claw-Code 的 `ConversationRuntime::run_turn` 中，每一次“模型调用 + 可能的工具执行 + tool_result 回写”都算一次 loop iteration。`max_iterations` 是防止模型持续调用工具、工具结果又诱发下一轮工具调用，从而陷入无限循环的熔断阈值。源码位置：[conversation.rs](../../submodules/claw-code/rust/crates/runtime/src/conversation.rs)。后续写正式专题时应结合 CLI 配置、测试和默认值继续核验。

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

A: DeerFlow 的 Agent Loop 不集中在一个手写 `while tool_use` 函数里，而是由 Gateway run lifecycle + LangGraph agent runtime 共同构成。Gateway 的 run API 调用 `start_run(...)`，后台 worker 调用 `agent.astream(...)`，真正的“模型调用 -> tool calls -> tool messages -> 再调用模型”循环由 `create_agent(...)` 生成的 LangGraph / LangChain agent 执行。源码入口见 [thread_runs.py](../../submodules/deer-flow/backend/app/gateway/routers/thread_runs.py)、[services.py](../../submodules/deer-flow/backend/app/gateway/services.py)、[worker.py](../../submodules/deer-flow/backend/packages/harness/deerflow/runtime/runs/worker.py) 和 [agent.py](../../submodules/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/agent.py)。

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

A: 不是。OpenClaw 的核心模型/工具循环确实是手写在 [agent-loop.ts](../../submodules/openclaw/packages/agent-core/src/agent-loop.ts) 中，尤其是 `runAgentLoop(...)`、`runAgentLoopContinue(...)` 和 `runLoop(...)`；但它不是单纯的 `while tool_use`。它外面还有 [Agent](../../submodules/openclaw/packages/agent-core/src/agent.ts) 负责状态、事件和 `steer` / `followUp` 队列，再外面由 [AgentSession](../../submodules/openclaw/src/agents/sessions/agent-session.ts) 接入产品会话、hook、compaction、retry、持久化和事件处理。更准确地说，OpenClaw 是“手写 core double loop + Agent 事件状态机 + AgentSession 产品会话外壳”。

### Q: OpenClaw 的 double loop 怎么理解？

> **状态**: draft
> **来源**: discussion / source-code

A: 可以把 OpenClaw 的 double loop 理解成“外层处理追加消息，内层处理当前任务”。内层 loop 处理普通模型/工具循环：模型要工具、工具返回结果、模型继续思考；同时也处理运行中用户发来的 `steer`。外层 loop 处理 Agent 到结束点后用户追加的 `followUp`，如果还有 follow-up，就再开下一轮。口语化地说：内层是“这件事没干完，继续干”；外层是“这件事干完了，但用户又追加了，接着干下一件”。源码主线见 [agent-loop.ts](../../submodules/openclaw/packages/agent-core/src/agent-loop.ts)，入口包括 `runLoop(...)`、`streamAssistantResponse(...)` 和 `executeToolCalls(...)`。

### Q: OpenClaw 的 `steer` / `followUp` 队列有什么价值？

> **状态**: draft
> **来源**: discussion / source-code

A: 它把用户中途输入拆成两种不同语义：`steer` 是 Agent 正在运行时用户补充方向，类似“扶方向盘”，影响当前任务后续模型调用；`followUp` 是 Agent 准备结束或已经结束后用户追加下一句，类似“再补一张工单”，由外层 loop 开启下一轮处理。这样可以避免把运行中引导、结束后追加和硬打断都混成一种普通 user message。源码入口见 [Agent.steer(...)](../../submodules/openclaw/packages/agent-core/src/agent.ts) 和 [Agent.followUp(...)](../../submodules/openclaw/packages/agent-core/src/agent.ts)，执行调度见 [runLoop(...)](../../submodules/openclaw/packages/agent-core/src/agent-loop.ts)。

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

### Q: OpenHands Agent Loop 在当前仓库里吗？

> **状态**: draft
> **来源**: discussion / source-code / official-repo-docs

A: 当前 `OpenHands/OpenHands` 仓库主要是 Agent Canvas / App Server 控制面，真正的 OpenHands Agent 和 Agent Server 源码在 [OpenHands/software-agent-sdk](https://github.com/OpenHands/software-agent-sdk)，本仓库已作为 [software-agent-sdk/](../../submodules/software-agent-sdk/) submodule 接入。当前仓库负责启动 / 管理 sandbox、构造 conversation request、转发用户消息、查询状态和存储事件；真正的 `Conversation.run()` / `Agent.step()` / ActionEvent / ObservationEvent loop 在 SDK / Agent Server 执行面中。当前仓库 [README.md](../../submodules/openhands/README.md) 明确说明 Agent 和 Agent Server 源码位于 `software-agent-sdk`。

### Q: OpenHands 的 action / observation 和普通 tool_use / tool_result 是一回事吗？

> **状态**: draft
> **来源**: discussion / source-code

A: 底层模式是一回事，抽象层级不一样。普通 tool calling 是协议视角：`assistant tool_use -> tool_result -> assistant next`；OpenHands 的 action / observation 是 Agent 与环境交互视角：`ActionEvent -> tool/runtime 执行 -> ObservationEvent -> 下一轮 Agent.step`。前者强调模型调用工具，后者强调 Agent 在 workspace / sandbox 里采取行动并观察环境反馈，更适合平台化 SWE Agent。可以概括为：`tool_use` / `tool_result` 是协议层概念，Action / Observation 是平台事件层概念。

### Q: OpenHands 的工具执行在哪个面？

> **状态**: draft
> **来源**: discussion / source-code

A: 工具执行在执行面。App Server / Agent Canvas 控制面负责创建 conversation、管理 sandbox、准备 tools / MCP / skills / hooks / secrets / workspace 配置、转发消息、查询状态和展示事件；真正执行工具的是 [software-agent-sdk/](../../submodules/software-agent-sdk/) 中的 Agent Server / SDK / `openhands-tools`，在对应 workspace / sandbox 中运行。可以记成：控制面决定“这个 conversation 有哪些工具、在哪个 sandbox 跑”；执行面负责“模型什么时候调用工具、工具实际怎么跑、结果怎么回给模型”。当前仓库 [pyproject.toml](../../submodules/openhands/pyproject.toml) 依赖 `openhands-agent-server`、`openhands-sdk`、`openhands-tools`，也体现了这个执行面边界。

### Q: OpenHands 的控制面 / 执行面分离有什么优缺点？

> **状态**: draft
> **来源**: discussion / source-code

A: 优点是适合多 backend、远程运行、长时间任务、团队共享、自动化触发、event 追踪和平台 UI；Agent Server / SDK 可以独立承载多个 conversation，App Server 专心管理用户、sandbox、事件、状态和集成。缺点是源码理解和调试链路更长：一次消息可能经过 frontend、App Server、SandboxService、Agent Server HTTP API、SDK Conversation、Agent.step、tool execution、ObservationEvent、event callback 和前端刷新。对本地单人 CLI 场景来说也比 Claw-Code 这种本地 `run_turn` 更重。

### Q: OpenHands 与 OpenClaw / DeerFlow / Claw-Code 的精髓差异是什么？

> **状态**: draft
> **来源**: discussion / source-code

A: OpenClaw 更像“聊天式 Agent 产品的实时会话控制”，loop 本体在本仓库内，核心是 `AgentSession -> Agent -> runLoop`、事件状态和 `steer` / `followUp` 队列；OpenHands 更像“平台化 SWE Agent 的控制面 / 执行面分离”，核心是 App Server / Sandbox / Agent Server / SDK action-observation loop。DeerFlow 更像“长任务工作流平台的 run 控制”，核心是 Gateway run lifecycle、LangGraph runtime 和 middleware；OpenHands 更像“能托管很多 coding agents 的远程开发控制中心”，核心是 workspace/sandbox、Agent Server backend、多 conversation、event storage 和 automation。Claw-Code 则更像“本地 CLI 一轮干到底”，主线集中在本地 `run_turn`。

## Context Management / 上下文管理

### Q: Claw-Code、OpenClaw、Hermes、DeerFlow、OpenHands 的上下文管理核心差异是什么？

> **状态**: verified
> **来源**: source-code / discussion

A: Claw-Code 的 context 像本地 CLI transcript / 本地施工日志：核心是把 `system_prompt + Session.messages` 稳定发回模型，并通过 compact / Trident / context-window retry 处理历史过长。OpenClaw 的 context 像产品态实时会话状态机 / 调度室：`AgentContext.messages` 同时服务 UI streaming、事件、工具回写、持久化和模型输入，并在请求前经过 `transformContext -> convertToLlm`。Hermes 的 context 像长期个人 Agent 的生存修复管线 / 个人助理脑：stable system prompt、persistent messages、临时 recall context、provider repair/sanitize、preflight / pre-API compression、retry / fallback 共同保证多 provider 长会话能继续运行。DeerFlow 的 context 像工作流状态投影系统 / 状态流水线工厂：`ThreadState` / checkpoint 保存 messages、summary_text、delegations、skill_context、uploads、images、todos 等 state channel，再由 middleware 在不同生命周期点写入、压缩、修复或投影成模型请求。OpenHands 的 context 像平台事件账本 + 当前分支剪辑：控制面准备 workspace / sandbox / repo / secrets / plugins，执行面用 `ConversationState + EventLog + View` 记录事件账本、选择 active branch、应用 Condensation，再把 `LLMConvertibleEvent` 转成模型 messages。项目笔记见 [Claw-Code Context Management](../projects/claw-code/context-management.md)、[OpenClaw Context Management](../projects/openclaw/context-management.md)、[Hermes Context Management](../projects/hermes-agent/context-management.md)、[DeerFlow Context Management](../projects/deer-flow/context-management.md)、[OpenHands Context Management](../projects/openhands/context-management.md)；横向总结见 [Context Management 横向总结](context-management.md)。

### Q: OpenHands 的上下文管理为什么说是“平台事件账本 + 当前分支剪辑”？

> **状态**: verified
> **来源**: source-code / discussion

A: OpenHands 的 App Server 控制面主要准备 workspace、sandbox、repo、secrets、plugins 和 initial message；真正的上下文主链路在 `software-agent-sdk` 执行面。执行面 `ConversationState` 持有 append-only `EventLog` 和当前 active branch 的 `View` cache，用户消息、ActionEvent、ObservationEvent、Condensation 等事件进入账本；每轮 `Agent.step()` 调用模型前，`prepare_llm_messages(state.view, condenser, llm)` 从当前 View 取出 `LLMConvertibleEvent`，必要时先做 Condensation，再转成 provider messages。因此 EventLog 像完整录像带 / 账本，View 像剪给模型看的当前分支剧情版。conversation tree / branch（如 `leaf_event_id`、`active_branch()`、fork / navigate）后续值得单独开专题继续学习。

### Q: DeerFlow 的 DynamicContextMiddleware 是上下文管理的主角吗？

> **状态**: verified
> **来源**: source-code / discussion

A: 它是重要入口之一，但不是唯一主角。DynamicContextMiddleware 负责当前日期和可选 memory snapshot 的首次注入，使用 frozen-snapshot pattern 保持 base system prompt 静态；但 DeerFlow 的上下文管理是一组 middleware 协作：SummarizationMiddleware 管历史压缩并写 `summary_text`，DurableContextMiddleware 管 summary / delegation / skill context 投影，MemoryMiddleware 管长期记忆异步更新，Uploads / ViewImage 管文件和图片上下文，SystemMessageCoalescingMiddleware 管 provider-facing system message 合规化。学 DeerFlow 的关键是看清 ThreadState 中有哪些 state channel，以及哪个 middleware 在 before_agent / before_model / wrap_model_call / after_agent 等位置写入、读取或投影它们。

### Q: Hermes 的 recall context 应该怎么理解？

> **状态**: verified
> **来源**: source-code / discussion

A: recall context 是 Hermes 本轮临时找出来、贴到当前用户问题后面的“参考资料 / 小抄”。它通常来自 external memory provider 的 `prefetch_all(...)` 或 plugin `pre_llm_call` hook；模型本轮能看到，但它不是新用户输入、不是 system prompt，也不会写入持久 `messages`。源码上，prefetch 在 [turn_context.py](../../submodules/hermes-agent/agent/turn_context.py) 取回，API messages 构造时追加到当前 user message 的副本，且注释明确说明原始 `messages` 不会被修改。

### Q: Hermes 为什么不把 recall context 放进 system prompt？

> **状态**: verified
> **来源**: source-code / discussion

A: 因为 Hermes 把 system prompt 当作 session-stable cache prefix：同一 session 尽量复用同一份 prompt，避免破坏 prompt cache，也避免把“临时参考资料”提升成“长期系统规则”。因此 memory / plugin 的动态 recall context 追加到当前 user message 的 API copy；persistent messages 继续保存真实对话轨迹；system prompt 则保持稳定。源码对应 [conversation_loop.py](../../submodules/hermes-agent/agent/conversation_loop.py) 中 API-call-time injection 与 system prompt 注释。

### Q: Hermes 的 system prompt 是每轮重建吗？

> **状态**: verified
> **来源**: source-code / discussion

A: 不是。Hermes 在 turn prologue 中只有当 `_cached_system_prompt` 为空时才恢复或构建 system prompt；如果 SessionDB 中已有可用且 model/provider 匹配的 prompt，就复用 verbatim。DB 缺失、为空、为 `NULL` 或 runtime identity 不匹配时才重建，并写回 SessionDB，避免后续每轮 cache miss。这个设计的精髓是：system prompt 是 session-stable cache prefix，而不是每轮动态拼接的上下文容器。

### Q: Hermes 的上下文压缩为什么说是多点防爆？

> **状态**: verified
> **来源**: source-code / discussion

A: Hermes 不只在一个地方 compact。它在 turn prologue 做 preflight compression；在每次 API call 前做 request pressure check，防止工具结果把下一次请求撑爆；provider 报 context overflow 后还会区分 input prompt 太长和 `max_tokens` output cap 太大，前者压缩历史 / 更新 context length，后者降低输出预算或提示改配置。相比 Claw-Code 的本地 session compact，Hermes 更强调多 provider 长会话的运行韧性。

## Permission / Security / Guardrail / 权限安全与防护

### Q: Claw-Code 为什么需要两道权限门？

> **状态**: verified
> **来源**: source-code / discussion

A: 第一层 `PermissionPolicy / PermissionPrompter` 按工具名、默认权限、active mode、allow / deny / ask rules、hook override 和用户确认做策略判断；第二层 `PermissionEnforcer / dynamic classification` 在工具执行层按具体参数重新定级，防止同一个工具的高风险参数绕过粗粒度判断。例如 `read_file("README.md")` 和 `read_file("/etc/passwd")` 都是 `read_file`，但后者应该升级为 `DangerFullAccess`；`bash("cat README.md")` 和 `bash("rm -rf /")` 也不应同等处理。详见 [Claw-Code Permission / Security](../projects/claw-code/permission-security.md)。

### Q: Claw-Code hooks 和 DeerFlow middleware 是一回事吗？

> **状态**: verified
> **来源**: source-code / discussion

A: 不是。它们都属于横切治理机制，但定位不同。Claw-Code hooks 更像本地 CLI 工具调用前后的外挂监工，主要围绕 `PreToolUse` / `PostToolUse` / `PostToolUseFailure` 拦截、审批、改写和审计工具调用；DeerFlow middleware 更像 LangGraph agent runtime 的内建工位，直接参与 `ThreadState`、上下文投影、模型调用、压缩、memory、HITL 和错误治理。可以概括为：**hook 是外挂监工，middleware 是内建工位**。详见 [Permission / Security / Guardrail 横向笔记](permission-security.md)。

### Q: Claw-Code 权限拒绝后模型会知道吗？

> **状态**: verified
> **来源**: source-code / discussion

A: 会。`ConversationRuntime::run_turn` 在 `PermissionOutcome::Deny` 时不会执行工具，而是把拒绝原因包装成 `ConversationMessage::tool_result(..., is_error=true)` 写回 session。下一轮模型会看到这个 error tool_result，从而改用只读操作、请求用户授权或给出手动步骤。这个设计说明权限系统不只是保护环境，也会把安全反馈纳入 agent loop 和上下文管理。

### Q: OpenClaw 的权限治理和 Claw-Code 的两道权限门有什么本质不同？

> **状态**: verified
> **来源**: source-code / discussion

A: Claw-Code 的重点是本地工具调用能不能在用户机器 / workspace 里执行，因此有 `PermissionPolicy / PermissionPrompter` 和 `PermissionEnforcer` 两道门。OpenClaw 的重点是当前 agent 在当前 profile、provider、group、sender、sandbox、subagent 和 inherited 限制下能看到什么工具，以及某次 plugin tool 调用是否需要通过 approval / hook / diagnostics 放行。可以概括为：Claw-Code 是本地工具双闸门，OpenClaw 是平台化工具门禁 + 审批工单系统。详见 [OpenClaw Permission / Security](../projects/openclaw/permission-security.md) 和 [Permission / Security / Guardrail 横向笔记](permission-security.md)。

### Q: OpenClaw 的 approval broker 是怎么把审批请求送到用户的？

> **状态**: verified
> **来源**: source-code / discussion

A: 有两条路径。TUI / embedded 模式下，`EmbeddedPluginApprovalBroker` 在本进程内登记 pending approval，并通过 `plugin.approval.requested/resolved/removed` 事件让 UI 展示和回填决策；多端 / Gateway 模式下，`requestPluginToolApproval(...)` 调用 `plugin.approval.request`，必要时再调用 `plugin.approval.waitDecision`，由 Gateway 根据 session、channel、reviewer device 等上下文路由审批请求。前者像本地审批柜台，后者像平台审批服务台。

### Q: OpenClaw 的 tool policy pipeline 具体管什么？

> **状态**: verified
> **来源**: source-code / discussion

A: 它管工具可见性，也就是当前运行上下文下模型能看到哪些 tools。策略基础形态是 `{ allow?: string[]; deny?: string[] }`，但会经过 tool name normalization、alias 处理、tool group / plugin group 展开，再按 profile、provider、global、agent、group、sender、sandbox、subagent、inherited 等层叠加。特别是 subagent 层有内建 denylist，限制 gateway、session、cron、spawn 等控制面工具，防止子 agent 默认拿到过高权限。

### Q: OpenClaw 为什么说是“工具门禁 + 审批工单系统”？

> **状态**: verified
> **来源**: source-code / discussion

A: 因为它把权限治理拆成两段：tool policy pipeline 先决定当前 agent 在当前来源、sandbox、subagent 层级下能看到哪些工具；before_tool_call runtime 再对单次调用做 loop detection、trusted policy、plugin approval、plugin hooks 和 diagnostics。前者像门禁，决定有没有这把工具；后者像工单审查，决定这次使用是否需要审批、放行或拦截。

### Q: OpenHands 的权限治理中心是什么？

> **状态**: verified
> **来源**: source-code / discussion

A: OpenHands 的权限治理中心是 `ActionEvent`，不是工具菜单。模型 tool call 会先被解析、规范化、校验并转换成 `ActionEvent`；`SecurityAnalyzer` 对 ActionEvent 评估 `SecurityRisk`；`ConfirmationPolicy` 根据风险决定是否把 conversation 置为 `WAITING_FOR_CONFIRMATION`；执行或拒绝结果再通过 `ObservationEvent` / `UserRejectObservation` 回写给模型。workspace / sandbox 则提供动作执行硬边界。详见 [OpenHands Permission / Security](../projects/openhands/permission-security.md) 和 [Permission / Security / Guardrail 横向笔记](permission-security.md)。

### Q: OpenHands 会无条件相信模型自评的 security_risk 吗？

> **状态**: verified
> **来源**: source-code / discussion

A: 不会。OpenHands 会在工具 schema 中暴露 `security_risk` 参数，让模型可以预测风险；但只有显式配置了 `security_analyzer` 时才采纳这个字段。没有 analyzer 时，模型提供的 `security_risk` 会被忽略并返回 `UNKNOWN`。这避免模型通过自报 `LOW` 绕过确认策略。

### Q: OpenHands 的用户拒绝会反馈给模型吗？

> **状态**: verified
> **来源**: source-code / discussion

A: 会。`reject_pending_actions(...)` 会为每个 pending action 写入 `UserRejectObservation`，它转成 LLM message 时是 tool role，内容为 `Action rejected: <reason>`，并保留对应 `tool_name` 和 `tool_call_id`。所以拒绝不是静默丢弃，而是进入 EventLog，并作为 observation 反馈给下一轮模型。

### Q: OpenHands 为什么说是“远程开发园区安检 + 工位隔离”？

> **状态**: verified
> **来源**: source-code / discussion

A: 因为 OpenHands 把具体模型动作登记成 `ActionEvent`，由 `SecurityAnalyzer` / `ConfirmationPolicy` 做动作前风险安检；如果需要确认，conversation 进入 `WAITING_FOR_CONFIRMATION`；用户拒绝会变成 `UserRejectObservation` 写回事件账本；真正执行动作时又在 workspace / sandbox 中运行。安检负责“这次动作要不要停下来让人看”，工位隔离负责“即使执行，也只能在分配环境里执行”。


### Q: DeerFlow 的安全治理是不是只有 middleware？

> **状态**: verified
> **来源**: source-code / discussion

A: 不是。middleware 是 DeerFlow 的核心风格，但完整防线至少有三层：Gateway API authz 管用户和资源权限；GuardrailMiddleware + GuardrailProvider 管工具调用前策略检查；workflow safety middleware chain + RunManager + Sandbox 管 run lifecycle、工具错误、loop、进展、写入版本、HITL 和执行环境。把 DeerFlow 简化成“只有中间件防线”会漏掉 Gateway 和 run / sandbox 两层。详见 [DeerFlow Permission / Security](../projects/deer-flow/permission-security.md) 和 [Permission / Security / Guardrail 横向笔记](permission-security.md)。

### Q: DeerFlow 的 GuardrailMiddleware 和 ToolErrorHandlingMiddleware 差别是什么？

> **状态**: verified
> **来源**: source-code / discussion

A: GuardrailMiddleware 发生在工具执行前，问“这次工具调用按策略能不能执行”；deny 时不执行工具，直接返回 error ToolMessage。ToolErrorHandlingMiddleware 发生在工具执行过程中，问“工具已经执行但抛异常时如何恢复”；它把异常转换成模型可见的错误反馈。前者是开工前门禁，后者是开工后故障处理。

### Q: DeerFlow 为什么说是“工作流工厂安全生产线”？

> **状态**: verified
> **来源**: source-code / discussion

A: 因为它的安全不是一个单点确认框，而是沿着 Gateway -> run -> agent middleware -> tool -> sandbox -> memory 的生产线分布。Gateway 门禁管谁能操作资源；GuardrailMiddleware 管工具调用前策略检查；ToolErrorHandling、LoopDetection、ToolProgress、ReadBeforeWrite、Clarification 等 middleware 管 run 内部健康；RunManager 管同一 thread 的并发、取消和回滚；SandboxMiddleware 管执行环境边界。这种形态更像工厂里的门禁、安检、质检、熔断、停线和工位隔离共同组成的安全生产线。

### Q: Hermes 的 ToolCallGuardrailController 是权限系统吗？

> **状态**: verified
> **来源**: source-code / discussion

A: 严格说不是。它不决定某个工具是否授权，而是观察工具调用后的失败 / 无进展模式，发现 exact failure、same-tool failure 或 idempotent no-progress 时给模型 warning，必要时 hard stop。它更像长期个人助理的“自检提醒器”，防止模型在同一个坑里反复尝试。详见 [Hermes Agent Permission / Security](../projects/hermes-agent/permission-security.md)。

### Q: Hermes 为什么需要 Tool Search bridge scope gate？

> **状态**: verified
> **来源**: source-code / discussion

A: 因为 Hermes 会用 `tool_search` / `tool_describe` / `tool_call` 做 deferred tools。如果 `tool_call` bridge 直接访问全局 registry，受限工具集的 session 或 subagent 就能绕过当前 `valid_tool_names` 调到不该暴露的工具。scope gate 确保 bridge 调用目标仍必须在当前 session 的 scoped catalog 中。

### Q: Hermes 的危险命令审批和 hardline block 有什么区别？

> **状态**: verified
> **来源**: source-code / discussion

A: dangerous pattern 是“需要确认的危险动作”，用户或 session approval 可以批准；hardline pattern 是“绝对不能执行的动作”，即使 yolo / approval 也阻断，例如 `rm -rf /`、`mkfs`、`dd` 写 `/dev/`、fork bomb、shutdown / reboot 等。这个分层避免把不可接受风险交给一次确认框处理。

### Q: Hermes 为什么说是“长期个人助理自我保护系统”？

> **状态**: verified
> **来源**: source-code / discussion

A: 因为 Hermes 的安全不只关心一次工具调用是否危险，还关心长期协作状态是否健康：当前 session 能看到哪些工具、deferred tool bridge 是否绕权、危险命令是否审批、编辑是否经过 diff proposal、plugin 是否能阻断、工具失败是否反复、memory / skills 是否可能被污染。它像个人助理的自我保护系统，而不是单个门禁或单个平台安检点。


## Sandbox / Workspace / Execution Environment / 沙箱与执行环境

### Q: OpenHands 的 sandbox 到底是什么？

> **状态**: verified
> **来源**: source-code / discussion

A: 它是给 Agent 准备的远程隔离工作间。App Server 负责创建 / 管理 sandbox 并把请求送到 sandbox 内的 Agent Server；Agent Server 在 sandbox 内启动 SDK conversation；Terminal / FileEditor 等工具在 `ConversationState.workspace.working_dir` 对应的 sandbox 文件系统和进程环境里执行。详见 [OpenHands Sandbox / Workspace](../projects/openhands/sandbox-workspace.md)。

### Q: OpenHands sandbox 的功能有哪些？

> **状态**: verified
> **来源**: source-code / discussion

A: 主要包括：隔离执行环境、提供 workspace、运行 Agent Server、承载 Terminal / FileEditor 等工具执行、保存 conversation / event / bash 记录、管理 STARTING / RUNNING / PAUSED / ERROR / MISSING 生命周期、通过 `conversation_id -> sandbox_id` 隔离或分组任务、用 session API key 保护访问、支持远程文件访问 / workspace 归档，以及暴露 VSCode / VNC / browser / Agent Server API 等远程开发能力。

### Q: OpenHands 的 App Server 会直接执行 Terminal / FileEditor 吗？

> **状态**: verified
> **来源**: source-code / discussion

A: 不会。App Server 是控制面，它检查 sandbox 状态、找到 sandbox exposed Agent Server URL，并用 `X-Session-API-Key` 把 start / message / file 请求发给 sandbox 内 Agent Server。真正的 Terminal / FileEditor 执行发生在 Agent Server 所在环境，也就是 sandbox 内。

### Q: 为什么 OpenHands start request 里是 LocalWorkspace，而 App Server 又用 RemoteWorkspace？

> **状态**: verified
> **来源**: source-code / discussion

A: 因为视角不同。App Server 在 sandbox 外部，所以通过 `AsyncRemoteWorkspace(host=agent_server_url, api_key=..., working_dir=...)` 访问 sandbox。Agent Server 运行在 sandbox 内部，所以 `/workspace/project` 对它来说就是本地路径，`StartConversationRequest.workspace` 使用 `LocalWorkspace(working_dir=...)`。

### Q: OpenHands FileEditor 是否强制只能编辑 workspace_root 内文件？

> **状态**: to-verify
> **来源**: source-code / discussion

A: 第一轮已读代码确认 FileEditorTool 用 `workspace_root=conv_state.workspace.working_dir` 初始化，并在工具说明中引导模型从 current working directory 开始；但 `file_editor/editor.py` 的 `validate_path(...)` 主要检查 path 是否为 absolute、create / view / edit 条件，暂未看到强制 path 必须位于 workspace_root 内的 containment 检查。因此当前结论应写成：FileEditor 的工作引导来自 workspace，硬隔离主要依赖 sandbox / container / volume 边界；后续可继续核验是否还有上层 hook、policy 或部署配置限制绝对路径访问。

### Q: DeerFlow 的 sandbox 到底是什么？

> **状态**: verified
> **来源**: source-code / discussion

A: DeerFlow 的 sandbox 是 LangGraph 工具调用的执行工作台。它通过 `Sandbox` 抽象和 `SandboxProvider` 后端，为 bash / file / grep / glob / download 等工具提供统一执行环境；工具调用前通过 `ensure_sandbox_initialized(runtime)` 获取或复用当前 thread 的 sandbox。它不是 OpenHands 那种“sandbox 内跑 Agent Server 的远程开发房间”，而是 agent runtime 中工具层按需使用的 execution environment abstraction。详见 [DeerFlow Sandbox / Workspace](../projects/deer-flow/sandbox-workspace.md)。

### Q: DeerFlow 为什么要 lazy init sandbox？

> **状态**: verified
> **来源**: source-code / discussion

A: 因为不是每个 run 都一定会执行工具。DeerFlow 默认装配 `SandboxMiddleware(lazy_init=True)`，Agent 进入 LangGraph runtime 后不会立刻创建 sandbox；只有第一次 sandbox tool call 时才 acquire sandbox，并把 `sandbox_id` 写回 `ThreadState`。这样可以避免纯对话、澄清、提前终止或被 guardrail 截断的 run 白白创建容器 / 工作目录，也适合 Gateway 同时管理很多 thread / run 的平台场景。

### Q: DeerFlow 的 LocalSandbox 是强安全沙箱吗？

> **状态**: verified
> **来源**: source-code / discussion

A: 不是。LocalSandbox 更准确地说是本地 path-mapping sandbox：它把 `/mnt/user-data/workspace`、uploads、outputs、ACP workspace、skills 等虚拟路径映射到宿主目录，并通过路径解析和 `relative_to(local_root)` 防止 `../` 等方式逃逸 mapping root。它不等于 Docker / VM 级强隔离；因此 DeerFlow 默认禁用 LocalSandbox 的 host bash，只有显式配置 `allow_host_bash=true` 才允许宿主 bash 执行。

### Q: DeerFlow 和 OpenHands 的 sandbox 精髓差异是什么？

> **状态**: verified
> **来源**: source-code / discussion

A: OpenHands 的 sandbox 是平台化 SWE Agent 的远程隔离工位：App Server 创建 sandbox，sandbox 内运行 Agent Server，Terminal / FileEditor 在 workspace 里执行。DeerFlow 的 sandbox 是 LangGraph 工具调用的按需执行工作台：Gateway / worker 启动 agent runtime，`SandboxMiddleware(lazy_init=True)` 挂在 middleware chain 中，第一次需要 sandbox 的工具调用才 acquire sandbox。可以概括为：OpenHands 是“先分房间再开工”，DeerFlow 是“工作流跑到要动手时才领工具台”。

## Tool System / 工具体系

### Q: 为什么后续专题叫 Tool System，而不是只叫 tool-calling？

> **状态**: draft
> **来源**: discussion

A: `tool-calling` 更像协议层术语，强调模型发起工具调用、Harness 返回工具结果；`tool-system` 覆盖范围更大，包括工具定义、schema、注册、可见性、权限、hook / middleware、sandbox、执行分发、结果回写、MCP / plugin / runtime 扩展，以及子 agent、task、worker 等高阶能力工具化。研究 Agent Harness 时，后者更能表达真实工程复杂度。

### Q: Claw-Code 的工具系统为什么可以称为“集中式工具中枢”？

> **状态**: draft
> **来源**: discussion / source-code

A: Claw-Code 将 `ToolSpec`、`GlobalToolRegistry`、allowed tools 过滤、ToolSearch、权限规格、动态权限分类和 `execute_tool_with_enforcer(...)` 执行分发集中在 [tools/src/lib.rs](../../submodules/claw-code/rust/crates/tools/src/lib.rs)，再由 [conversation.rs](../../submodules/claw-code/rust/crates/runtime/src/conversation.rs) 的 `run_turn` 内联串起 hook、permission、execute、tool_result 回写。优点是直接、内联、可控；代价是工具越来越多后，中心模块会变重。

### Q: Claw-Code 为什么需要两道权限门？

> **状态**: draft
> **来源**: discussion / source-code

A: 第一扇门在 `run_turn`，通过 `PreToolUse` hook、`PermissionPolicy` 和 `PermissionPrompter` 判断“这个工具类型当前能不能用”；第二扇门在工具执行层，通过 `PermissionEnforcer` 和动态权限分类判断“这个具体调用参数会不会越界”。例如 `bash git status` 与 `bash rm -rf /` 都是 `bash`，但风险不同；`read_file README.md` 与 `read_file /etc/passwd` 都是 `read_file`，但边界不同。

### Q: Claw-Code 的 ToolSearch 精髓是什么？

> **状态**: draft
> **来源**: discussion / source-code

A: ToolSearch 是内置工具目录检索器，不是智能搜索 Agent。Claw-Code 默认暴露 `bash`、`read_file`、`write_file`、`edit_file`、`glob_search`、`grep_search` 等基础工具；其他专用工具作为 deferred tools，需要时通过 ToolSearch 按工具名和描述做关键词检索。这个设计的精髓是：工具系统不只是“工具越多越好”，还要控制模型每轮看到的工具表规模。

### Q: Claw-Code 与 OpenHands / DeerFlow 的工具系统风格差异是什么？

> **状态**: draft
> **来源**: discussion / source-code

A: Claw-Code 更像本地万能工具箱 / 集中式工具中枢，适合本地 CLI、源码主线短、调试直观；OpenHands 更像远程工程平台，把工具执行放在 Agent Server / SDK / tools package / sandbox 执行面，用 ActionEvent / ObservationEvent 做平台事件流；DeerFlow 更像工作流工厂，把工具调用放进 LangGraph runtime、run lifecycle 和 middleware 体系中治理。差异不是谁“有工具”，而是工具治理被放在本地函数、平台执行面，还是工作流 runtime 中。
### Q: OpenHands 的工具调用承载物是什么？

> **状态**: verified
> **来源**: source-code / discussion

A: OpenHands 执行面把模型协议层的 `MessageToolCall` 转成平台事件层的 `ActionEvent`，再用 SDK `tools_map` 找到对应 `ToolDefinition`，把参数校验成 `Action`，调用 `ToolDefinition.executor` 得到 `Observation`，最后包成 `ObservationEvent`。所以它的承载物链路可以写成：`MessageToolCall -> ActionEvent -> ToolDefinition / executor -> ObservationEvent`。这和 Claw-Code 的 `ToolUse -> ToolExecutor`、OpenClaw 的 `toolCall -> AgentTool`、Hermes 的 `tool_call -> function_name + args -> tool_executor`、DeerFlow 的 `ToolCallRequest -> BaseTool -> ToolMessage / Command` 都不同。


### Q: OpenClaw 的工具系统和 Claw-Code 的工具系统最大差异是什么？

> **状态**: draft
> **来源**: discussion / source-code

A: Claw-Code 更像本地万能工具箱，工具定义、权限、搜索和执行分发集中在 Rust tools 模块与 `run_turn` 主线中；OpenClaw 更像多端 Agent 产品里的工具调度与治理平台，工具先由 `createOpenClawCodingTools` 按 run/session/channel/model/sandbox/policy 动态装配，再经过 tool policy pipeline、before_tool_call wrapper、sequential/parallel batch 调度和事件流回写。简单说，Claw-Code 是集中式工具中枢，OpenClaw 是工具装配工厂 + 策略管线 + 事件化执行流。

### Q: OpenClaw 为什么要把工具执行做成事件化生命周期？

> **状态**: draft
> **来源**: discussion / source-code

A: OpenClaw 面向多端 Agent 产品，不只是本地 CLI。工具执行过程要服务 Web UI、IM channel、session persistence、diagnostics、approval、progress display 和 audit，因此需要 `tool_execution_start/update/end` 表示执行生命周期，同时用 `message_start/end` 表示 tool result 消息进入 transcript。前者服务 UI / runtime，后者服务会话记录和下一轮模型上下文。

### Q: OpenClaw 如何决定工具调用串行还是并发？

> **状态**: draft
> **来源**: discussion / source-code

A: 如果全局 `config.toolExecution === "sequential"`，整批工具调用串行；否则先预扫描这一批 tool calls 并解析真实工具对象，如果任一工具声明 `executionMode === "sequential"`，整批串行；否则整批并发。这是一种“默认并行，但遇到任何串行约束就保守降级”的策略。Claw-Code 在已读 `run_turn` 主线中则是 for loop 逐个执行，没有这种 batch-level parallel 调度。

### Q: Hermes Agent 的 Tool System 为什么更像“长期个人 Agent 工具工作台”？

> **状态**: draft
> **来源**: discussion / source-code

A: 因为 Hermes 的工具系统不只负责外部动作，还承载长期个人 Agent 的核心能力。`memory`、`todo`、`session_search`、`skills_list` / `skill_view` / `skill_manage`、`delegate_task`、`clarify` 等都进入 `_HERMES_CORE_TOOLS` 或 toolsets，通过同一套 `ToolRegistry`、`get_tool_definitions(...)`、`tool_executor.py`、middleware / hooks、guardrail 和 tool result 回写进入模型循环。工具结果还会触发 SessionDB flush 与 pending steer 注入，因此它同时是执行层、记忆/技能入口和长期协作交汇点。

### Q: Hermes 的 Tool Search 和 Claw-Code / OpenClaw 有什么差异？

> **状态**: draft
> **来源**: discussion / source-code

A: Claw-Code 的 ToolSearch 是轻量内置目录检索器；OpenClaw 的 Tool Search 是面向 OpenClaw / MCP / client 多来源的大工具目录服务，还支持 code-mode；Hermes 的 Tool Search 是 progressive disclosure：核心 Hermes 工具永不 deferred，MCP / plugin 非核心工具在工具表过大时被 `tool_search` / `tool_describe` / `tool_call` 三个 bridge 替代。Hermes 还特别强调 session toolset scope，避免受限 subagent / kanban worker 通过 `tool_call` 调到未授权的全局工具。

### Q: Hermes 如何决定工具调用串行还是并发？

> **状态**: draft
> **来源**: discussion / source-code

A: Hermes 采用白名单式并发。`_should_parallelize_tool_batch(...)` 要求工具数量大于 1、没有 `clarify` 等 never-parallel 工具、参数 JSON 可解析、`read_file` / `write_file` / `patch` 等 path-scoped 工具目标路径不重叠，并且每个工具都在 parallel-safe 白名单中或所属 MCP server 显式 `supports_parallel_tool_calls`。否则整批回到 sequential 路径。它比 OpenClaw 的“默认并行，遇 sequential 整批降级”更保守。

### Q: Hermes 的 tool guardrail 是权限系统吗？

> **状态**: draft
> **来源**: discussion / source-code

A: 不是。`ToolCallGuardrailController` 主要防止工具循环和无进展重复调用，例如相同参数重复失败、同一工具多次失败、只读工具重复返回相同结果等。默认启用 warning，不默认 hard stop；hard stop 需要配置打开。权限 / 审批更多由 plugin hook、ACP edit approval、checkpoint 和具体工具安全策略承担。

### Q: Hermes 预定义了 toolsets 菜单，那有没有菜单之外的工具？

> **状态**: draft
> **来源**: discussion / source-code

A: 有，但不是绕过菜单系统。Hermes 的菜单是可扩展菜单系统：内置工具通过 `registry.register(...)` 登记，MCP 工具会注册进 registry 并归入类似 `mcp-<server>` 的动态 toolset，plugin 可以注册自己的工具 / toolset，context engine 和 memory provider 也可能提供运行时工具入口。无论来源如何，正常执行前都要进入 `registry` / `toolsets` / `get_tool_definitions(...)` / `agent.valid_tool_names` / `tool_call` scope gate 这套约束。可以记成：菜单可以加菜，但不能绕过点菜系统。

### Q: OpenClaw 和 Hermes 的工具组装方式到底有什么区别？

> **状态**: draft
> **来源**: discussion / source-code

A: 两者都动态组装工具，区别不是动态 vs 静态，而是动态依据不同。OpenClaw 的动态性来自产品会话上下文：run、session、channel、model、sandbox、sender、policy 等决定当前工具面，像多端工作室按当前工单配工具车。Hermes 的动态性来自工具总账 + 工具菜单：registry、toolsets、enabled_toolsets、disabled_toolsets、check_fn 决定当前工具面，像私人助理按任务菜单从工具总账拿工具摆上桌。

### Q: Hermes 的工具调用是不是在执行前外围包了大量检查？

> **状态**: draft
> **来源**: discussion / source-code

A: 是。Hermes 的工具调用像一个厚执行外壳：`conversation_loop` 先做协议卫生，如修复 tool name、校验 JSON args、处理 unknown tool、追加 assistant tool-call message；`tool_executor` 再做 Tool Search unwrap、scope gate、request middleware、plugin block、guardrail、checkpoint、interrupt check 和并发判定；真正执行时通过 `agent._invoke_tool` / `model_tools.handle_function_call` / `registry.dispatch` 找到 handler；执行后还要做 post hook、transform result、result budget、大结果持久化、SessionDB flush 和 steer 注入。真正 handler dispatch 只是中间一段。

### Q: Hermes 的权限 / 治理应该怎么拆开理解？

> **状态**: draft
> **来源**: discussion / source-code

A: 不能把 toolsets、scope gate、plugin hook、checkpoint、guardrail、result budget 都笼统叫“权限”。更准确是：`toolsets` 管“看得见”，是可见性 / 菜单控制；`tool_call` scope gate 管“别越权绕路”，接近权限；plugin `pre_tool_call` 和 ACP edit approval 是执行前门 / HITL；checkpoint 是回滚保险；guardrail 是防循环 / 防无进展；result budget 是上下文保护；SessionDB flush 是持久化 / 恢复；steer injection 是交互控制。

### Q: OpenClaw 和 Hermes 在工具调用本体上的差异是否已经讲清？

> **状态**: draft
> **来源**: discussion / source-code

A: 已经比上一轮更清楚。关键不在“谁有工具对象、谁没有工具对象”，也不在“OpenClaw 会不会用完重建对象”。OpenClaw 的 `AgentTool` 更像长期存在的工具定义 / 工位 / 菜谱；每次模型产生的 `toolCall` 是一次性调用实例 / 工单。OpenClaw 的执行阶段会先把这次 `toolCall` 匹配到当前工具列表里的已有 `AgentTool`，再围绕这个工具定义跑 `prepareArguments`、参数校验、`beforeToolCall`、`execute`、`afterToolCall`、`tool_execution_*` 事件和 `ToolResultMessage` 回写。Hermes 也有 registry / schema / handler 等工具定义，但执行阶段的主变量更像 `function_name + function_args + tool_call_id + agent context`；executor 先拆包，再经过 Tool Search unwrap、scope gate、middleware、plugin block、guardrail、checkpoint、并发 worker、`agent._invoke_tool(function_name, function_args)`、result budget、SessionDB flush、steer 注入等厚执行管线。可以记成：OpenClaw 是 `toolCall -> AgentTool -> 标准工单流程`；Hermes 是 `tool_call -> function_name + args -> 厚执行器流水线 -> handler dispatch`。

### Q: OpenClaw 的“AgentTool 生命周期”是不是指工具对象用完要重新生成？

> **状态**: draft
> **来源**: discussion / source-code

A: 不是。这里“生命周期”容易误导，更准确应叫“一次工具调用的标准工单流程”。`AgentTool` 是工具定义对象，通常长期存在，像菜谱或工位；模型每次输出的 `toolCall` 才是一次性的调用实例，像某桌客人的一张点菜单。每次调用会根据 `toolCall.name` 找到已有 `AgentTool`，然后跑准备参数、校验、执行前 hook、执行、执行后 hook、事件和结果回写。候选工具列表每轮可能重算，但那是为了告诉模型本轮能看见哪些工具，不是因为上一次工具对象被“用掉”。

### Q: 能不能理解成 OpenClaw 先生成工具执行对象，Hermes 在对象未生成前先检查参数？

> **状态**: draft
> **来源**: discussion

A: 这个理解接近但需要校正。OpenClaw 不是先新生成一个一次性工具执行对象，而是把这次 `toolCall` 归属到已有 `AgentTool` 工具定义对象，再围绕它跑标准流程。Hermes 也不是“对象未生成前才检查”，因为 Hermes 同样有 registry、schema 和 handler；只是执行阶段没有强烈地以 `AgentTool` 对象生命周期为中心，而是以 `function_name + args` 这个调用请求为中心。更准确的表述是：OpenClaw 先把模型的工具调用归属到某个已有 `AgentTool`，然后围绕这个工具对象跑检查、执行、事件、结果；Hermes 先把模型的工具调用拆包为 `function_name + args`，然后让这个请求穿过厚执行器管线，最后再按名字 dispatch 到具体 handler。

### Q: DeerFlow 之所以显得非常标准化，首要原因是不是直接使用了 LangGraph？

> **状态**: draft
> **来源**: discussion / source-code

A: 是。DeerFlow 把模型-工具循环交给 LangGraph / LangChain agent runtime，因此天然采用 `BaseTool`、`ToolCallRequest`、`ToolMessage`、`Command`、`AgentMiddleware`、state schema、checkpoint 等标准件。但这只是第一层原因；DeerFlow 自己也沿着这个框架方向，把 Gateway run lifecycle、ThreadState、SandboxMiddleware、ToolErrorHandling、Clarification、TokenBudget、LoopDetection 等生产治理能力拆成中间件和 run 生命周期组件。可以概括为：LangGraph 提供标准生产线，DeerFlow 把生产环境需要的治理能力做成生产线卡口。

### Q: DeerFlow 的 Tool System 和 Claw-Code / OpenClaw / Hermes 的核心差异是什么？

> **状态**: draft
> **来源**: discussion / source-code

A: DeerFlow 的工具调用主语不是本地 `ToolExecutor`、不是自研 `AgentTool` 工单对象，也不是 Hermes 那种 `function_name + args` 厚执行器，而是 LangGraph / LangChain 标准生产线。工具定义成 `BaseTool` / `@tool`，工具调用进入 `ToolCallRequest -> BaseTool -> ToolMessage / Command` 的框架链路，DeerFlow 在外层通过 middleware、ThreadState、Sandbox 和 Gateway run lifecycle 做治理。可以记成：Claw-Code 是本地老师傅，OpenClaw 是事件化工单系统，Hermes 是长期私人助理厚流程，DeerFlow 是标准化工作流工厂。

### Q: 从生产部署角度看，这五类 Harness 的优缺点应该怎么分？

> **状态**: draft
> **来源**: discussion / source-code

A: 不应按“源码好不好读”评价，而应按生产目标匹配。Claw-Code 赢在轻量、本地直接、基础设施少，适合个人本地 coding CLI，但不天然适合多用户 / 多端 / 长任务平台化。OpenClaw 赢在多端实时产品化，适合 Web / IM / approval / steer / followUp，但事件一致性、channel 差异和 policy 配置复杂。Hermes 赢在长期个人状态、记忆和技能沉淀，适合私人助理和个人自动化，但长期记忆治理、隐私、迁移和状态恢复压力大。DeerFlow 赢在标准化工作流 run、checkpoint、stream、middleware 和 sandbox 治理，适合长任务 Agent 服务，但框架依赖强、部署链路较重、middleware 顺序敏感。OpenHands 赢在团队级远程 SWE 平台，适合 workspace / sandbox / Agent Server / 自动化，但部署和运维成本最高。

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
