# Hermes Agent Agent Loop：run_conversation

> **日期**: 2026-07-01 | **状态**: draft | **涉及版本**: `44ddc552f5e054759a6970af8997ea588a9d81c9`
>
> 本文记录 Hermes Agent 的核心对话循环。Hermes 和 Claw-Code 一样有明显的手写循环，但比最小 `while tool_calls` 复杂很多：它把 API 调用、工具调用、interrupt、steer、iteration budget、上下文压缩、provider fallback、session 持久化、memory / skill nudge 等机制都放进 `run_conversation` 的 turn loop 中。

## 相关源码

- `AIAgent.run_conversation` 转发入口：[run_agent.py:5441-5464](../../../submodules/hermes-agent/run_agent.py#L5441-L5464)
- 简易 chat 包装：[run_agent.py:5466-5478](../../../submodules/hermes-agent/run_agent.py#L5466-L5478)
- 核心循环函数：[conversation_loop.py:498-5017](../../../submodules/hermes-agent/agent/conversation_loop.py#L498-L5017)
- turn context 构建入口：[conversation_loop.py:543-579](../../../submodules/hermes-agent/agent/conversation_loop.py#L543-L579)
- 主循环条件与 iteration budget：[conversation_loop.py:613-638](../../../submodules/hermes-agent/agent/conversation_loop.py#L613-L638)
- API messages 构造与清洗：[conversation_loop.py:725-927](../../../submodules/hermes-agent/agent/conversation_loop.py#L725-L927)
- API retry / middleware / streaming 调用：[conversation_loop.py:992-1220](../../../submodules/hermes-agent/agent/conversation_loop.py#L992-L1220)
- response normalize 与 tool_calls 分支：[conversation_loop.py:3939-4133](../../../submodules/hermes-agent/agent/conversation_loop.py#L3939-L4133)
- tool_calls 校验与执行：[conversation_loop.py:4132-4400](../../../submodules/hermes-agent/agent/conversation_loop.py#L4132-L4400)
- tool 执行后继续循环 / 压缩：[conversation_loop.py:4438-4496](../../../submodules/hermes-agent/agent/conversation_loop.py#L4438-L4496)
- 无 tool_calls 的最终回答分支：[conversation_loop.py:4498-4936](../../../submodules/hermes-agent/agent/conversation_loop.py#L4498-L4936)
- turn finalizer：[conversation_loop.py:4995-5013](../../../submodules/hermes-agent/agent/conversation_loop.py#L4995-L5013)
- 工具执行分发入口：[run_agent.py:5327-5434](../../../submodules/hermes-agent/run_agent.py#L5327-L5434)
- sequential / concurrent 工具执行实现：[tool_executor.py:285](../../../submodules/hermes-agent/agent/tool_executor.py#L285)、[tool_executor.py:858](../../../submodules/hermes-agent/agent/tool_executor.py#L858)
- tool result message 追加：[tool_executor.py:1461-1485](../../../submodules/hermes-agent/agent/tool_executor.py#L1461-L1485)
- iteration budget：[iteration_budget.py:16-58](../../../submodules/hermes-agent/agent/iteration_budget.py#L16-L58)
- interrupt / steer：[run_agent.py:2487-2638](../../../submodules/hermes-agent/run_agent.py#L2487-L2638)
- Sandbox / Workspace：[sandbox-workspace.md](sandbox-workspace.md)

## 和 Claw-Code / DeerFlow 的差异

Hermes 的 Agent Loop 介于 Claw-Code 和 DeerFlow 之间：

- 像 Claw-Code：有一个明确的手写对话循环，循环里直接判断工具调用、执行工具、把 tool result 追加回 messages。
- 不像 DeerFlow：没有把主循环整体交给 LangGraph `agent.astream(...)`，而是自己维护 OpenAI / Anthropic / Bedrock / Codex 等 provider 的请求、响应归一化和错误恢复。
- 比 Claw-Code 更“个人 Agent 化”：循环里有 memory prefetch、plugin hooks、steer、session persistence、skill nudge、context compression、provider fallback 等长期协作能力。

抽象上可以写成：

```text
AIAgent.chat / run_conversation
  -> build_turn_context
  -> while api_call_count < max_iterations and budget remains:
       handle interrupt / steer
       build and sanitize api_messages
       call provider API with retry / middleware / streaming
       normalize assistant response
       if assistant_message.tool_calls:
           validate / repair tool calls
           append assistant tool-call message
           execute tools sequentially or concurrently
           append tool result messages
           maybe compact context
           continue
       else:
           treat as final answer or recover from empty/incomplete response
           break
  -> finalize_turn
```

## 入口：AIAgent.run_conversation

`AIAgent.run_conversation(...)` 在 [run_agent.py:5441-5464](../../../submodules/hermes-agent/run_agent.py#L5441-L5464) 只是转发到 [conversation_loop.py](../../../submodules/hermes-agent/agent/conversation_loop.py) 的模块级函数。`chat(...)` 是更薄的一层包装，调用 `run_conversation(...)` 后返回 `result["final_response"]`，见 [run_agent.py:5466-5478](../../../submodules/hermes-agent/run_agent.py#L5466-L5478)。

这说明 Hermes 的主循环核心在 [agent/conversation_loop.py](../../../submodules/hermes-agent/agent/conversation_loop.py)，而不是散在 CLI 或 gateway 入口里。

## turn context：进入循环前的一次性准备

`run_conversation(...)` 开头先调用 `build_turn_context(...)`，见 [conversation_loop.py:543-567](../../../submodules/hermes-agent/agent/conversation_loop.py#L543-L567)。注释说明这个 prologue 负责：

- stdio guarding
- retry-counter reset
- user message sanitize
- todo / nudge hydration
- system prompt restore or build
- crash-resilience persistence
- preflight compression
- `pre_llm_call` plugin hook
- external-memory prefetch

返回的 context 会提供 `messages`、`conversation_history`、`active_system_prompt`、`effective_task_id`、`turn_id`、当前 user message index、memory prefetch cache、plugin context 等局部变量，见 [conversation_loop.py:568-579](../../../submodules/hermes-agent/agent/conversation_loop.py#L568-L579)。

这和 Claw-Code 的 `session + system_prompt + maybe_auto_compact` 类似，但 Hermes 更强调长期会话与个人上下文：turn 开始前就会准备 memory / plugin / session 相关数据。

## 主循环：max_iterations + IterationBudget

Hermes 的主循环条件在 [conversation_loop.py:613](../../../submodules/hermes-agent/agent/conversation_loop.py#L613)：

```text
while (api_call_count < agent.max_iterations and agent.iteration_budget.remaining > 0) or agent._budget_grace_call:
```

这里有两层限制：

1. `api_call_count < agent.max_iterations`：本次 conversation turn 内最多 API 调用次数。
2. `agent.iteration_budget.remaining > 0`：线程安全的 iteration budget，可被父 agent / 子 agent 共享或继承。

`IterationBudget` 定义在 [iteration_budget.py:16-58](../../../submodules/hermes-agent/agent/iteration_budget.py#L16-L58)，提供 `consume()`、`refund()` 和 `remaining`。初始化位置在 [agent_init.py:290-295](../../../submodules/hermes-agent/agent/agent_init.py#L290-L295)。

循环开头还会检查 interrupt：如果 `agent._interrupt_requested` 为真，就设置 `interrupted=True` 并 break，见 [conversation_loop.py:617-623](../../../submodules/hermes-agent/agent/conversation_loop.py#L617-L623)。

## steer：不中断当前工具，但影响下一轮模型输入

Hermes 有一个比普通 interrupt 更细的 `/steer` 机制。初始化说明见 [agent_init.py:460-468](../../../submodules/hermes-agent/agent/agent_init.py#L460-L468)：steer 不会设置 `_interrupt_requested`，而是把用户补充说明暂存起来，等当前工具批次自然结束后，注入到最后一个 tool result 中。

`steer(...)` 方法定义在 [run_agent.py:2588-2622](../../../submodules/hermes-agent/run_agent.py#L2588-L2622)，`_drain_pending_steer()` 定义在 [run_agent.py:2624-2638](../../../submodules/hermes-agent/run_agent.py#L2624-L2638)。

主循环里也有一次 pre-API-call steer drain：如果 steer 在上一轮 API call 期间到达，会尝试追加到最近的 tool message 中，让模型在本次 API 调用就看到它，见 [conversation_loop.py:674-723](../../../submodules/hermes-agent/agent/conversation_loop.py#L674-L723)。

这体现 Hermes 的个人助理式交互：用户不一定要打断 agent，而是可以“边跑边补一句方向”。

## API messages 构造与请求执行

每次循环中，Hermes 会把内部 `messages` 转成 `api_messages`，并做大量 provider 兼容和历史修复，见 [conversation_loop.py:725-927](../../../submodules/hermes-agent/agent/conversation_loop.py#L725-L927)：

- 修复 tool call arguments
- 修复 role alternation
- 注入 external memory prefetch / plugin user context
- 回放 reasoning content
- 合并 system prompt / ephemeral prompt
- 注入 prefill messages
- 应用 Anthropic prompt caching
- 清理 orphaned tool results
- drop thinking-only turns
- 规范化 tool-call JSON
- 清理 surrogate 字符
- 估算 request token / context size

API 调用本身位于 retry loop 中，见 [conversation_loop.py:992-1220](../../../submodules/hermes-agent/agent/conversation_loop.py#L992-L1220)。这里会处理：

- provider rate-limit guard
- fallback provider
- API kwargs 构造
- LLM request middleware
- plugin `pre_api_request` hook
- streaming / non-streaming 路径选择
- interruptible API call
- LLM execution middleware

Hermes 默认偏向 streaming path，即使没有 stream consumer，也用 streaming 获得更好的健康检查和 stale stream 检测，见 [conversation_loop.py:1141-1151](../../../submodules/hermes-agent/agent/conversation_loop.py#L1141-L1151)。

## response normalize 与 tool_calls 分支

API 返回后，Hermes 通过 transport 把不同 provider 的响应归一化，见 [conversation_loop.py:3939-3947](../../../submodules/hermes-agent/agent/conversation_loop.py#L3939-L3947)。随后进入核心分支：

```text
if assistant_message.tool_calls:
    validate / repair / execute tools
    continue
else:
    final_response = assistant_message.content
    break 或进入空响应恢复
```

### 有 tool_calls：校验、追加 assistant message、执行工具

tool calls 分支从 [conversation_loop.py:4132](../../../submodules/hermes-agent/agent/conversation_loop.py#L4132) 开始。主要步骤：

1. 打印 / 记录 tool call 数量。
2. 自动修复或拒绝不存在的 tool name，见 [conversation_loop.py:4141-4212](../../../submodules/hermes-agent/agent/conversation_loop.py#L4141-L4212)。
3. 校验 tool arguments JSON；如果 JSON invalid，会重试或注入 tool error result，见 [conversation_loop.py:4216-4304](../../../submodules/hermes-agent/agent/conversation_loop.py#L4216-L4304)。
4. 对 delegate task 等工具做 guardrail / dedup / cap，见 [conversation_loop.py:4309-4315](../../../submodules/hermes-agent/agent/conversation_loop.py#L4309-L4315)。
5. 构造并追加 assistant tool-call message，见 [conversation_loop.py:4317-4379](../../../submodules/hermes-agent/agent/conversation_loop.py#L4317-L4379)。
6. 调用 `agent._execute_tool_calls(...)` 执行工具，见 [conversation_loop.py:4400](../../../submodules/hermes-agent/agent/conversation_loop.py#L4400)。
7. 工具执行后 `continue`，进入下一次 API call，见 [conversation_loop.py:4492-4496](../../../submodules/hermes-agent/agent/conversation_loop.py#L4492-L4496)。

### 工具执行：sequential / concurrent

`agent._execute_tool_calls(...)` 定义在 [run_agent.py:5327-5346](../../../submodules/hermes-agent/run_agent.py#L5327-L5346)，会根据工具批次是否可并行，分派到 sequential 或 concurrent：

- concurrent 实现：[tool_executor.py:285](../../../submodules/hermes-agent/agent/tool_executor.py#L285)
- sequential 实现：[tool_executor.py:858](../../../submodules/hermes-agent/agent/tool_executor.py#L858)

sequential 路径会在每个工具前检查 interrupt，如果用户已经打断，就为剩余工具追加取消结果并停止继续执行，见 [tool_executor.py:862-882](../../../submodules/hermes-agent/agent/tool_executor.py#L862-L882)。

工具执行完成后，结果会经过持久化 / budget / multimodal 处理，然后以 tool message 形式追加回 `messages`，见 [tool_executor.py:1461-1485](../../../submodules/hermes-agent/agent/tool_executor.py#L1461-L1485)。随后还会在工具结果上应用 pending steer，见 [tool_executor.py:1487-1491](../../../submodules/hermes-agent/agent/tool_executor.py#L1487-L1491)。

这就是 Hermes 的 tool result 回写点。

### 无 tool_calls：最终回答或恢复逻辑

如果没有 tool calls，Hermes 进入最终回答分支，见 [conversation_loop.py:4498-4936](../../../submodules/hermes-agent/agent/conversation_loop.py#L4498-L4936)。正常情况下：

- `final_response = assistant_message.content or ""`
- 构建 final assistant message
- 持久化 / callback / verification hook
- 设置 `_turn_exit_reason`
- break loop

但 Hermes 对空响应 / thinking-only / partial stream 做了很多恢复：

- partial stream recovery
- 使用上一轮 content + housekeeping tools 的 fallback
- post-tool empty response nudge
- thinking-only prefill continuation
- empty response retry
- fallback provider

这说明 Hermes 的 loop 不只是“有没有工具”的分支，还包含大量“弱模型 / 多 provider / streaming 异常 / reasoning-only 响应”的恢复策略。

## interrupt：硬中断当前 loop 与工具执行

`interrupt(...)` 方法在 [run_agent.py:2487-2554](../../../submodules/hermes-agent/run_agent.py#L2487-L2554)。它会：

- 设置 `_interrupt_requested=True`
- 记录触发 interrupt 的 message
- 对当前 agent execution thread 设置 interrupt signal
- 对并发工具 worker threads fan out interrupt
- 向 active child agents 传播 interrupt

主循环顶部会检查 `_interrupt_requested` 并 break，见 [conversation_loop.py:617-623](../../../submodules/hermes-agent/agent/conversation_loop.py#L617-L623)。工具执行路径也会在执行前 / 执行后检查 interrupt，见 [tool_executor.py:298-312](../../../submodules/hermes-agent/agent/tool_executor.py#L298-L312) 和 [tool_executor.py:1502-1517](../../../submodules/hermes-agent/agent/tool_executor.py#L1502-L1517)。

所以 Hermes 的 interrupt 不是只停止下一次模型调用，而是试图同时影响：主 loop、当前工具、并发工具 worker、子 agent。

## 上下文压缩与 session 持久化

工具执行后，如果 token 压力达到阈值，Hermes 会压缩上下文，见 [conversation_loop.py:4445-4488](../../../submodules/hermes-agent/agent/conversation_loop.py#L4445-L4488)。

它还会在工具调用前后做增量持久化，例如 tool-call assistant message 会在工具副作用执行前 flush 到 SessionDB，见 [conversation_loop.py:4372-4379](../../../submodules/hermes-agent/agent/conversation_loop.py#L4372-L4379)。工具结果追加后也会 flush，见 [tool_executor.py:1480-1485](../../../submodules/hermes-agent/agent/tool_executor.py#L1480-L1485)。

这和个人 Agent 的长期协作目标有关：即使工具执行中断、进程重启或发生副作用，历史也尽量保持可恢复。

## turn finalization

主循环结束后，Hermes 调用 `finalize_turn(...)` 汇总结果，见 [conversation_loop.py:4995-5013](../../../submodules/hermes-agent/agent/conversation_loop.py#L4995-L5013)。它会接收：

- final_response
- api_call_count
- interrupted / failed
- messages / conversation_history
- effective_task_id / turn_id
- user_message / original_user_message
- should_review_memory
- turn_exit_reason

这相当于 Hermes 的 turn summary / persistence boundary。

## QA / 讨论记录

### Q: Hermes Agent 的 Agent Loop 核心在哪里？

> **状态**: draft  
> **来源**: source-code / discussion

A: 核心在 [agent/conversation_loop.py](../../../submodules/hermes-agent/agent/conversation_loop.py) 的 `run_conversation(...)`。`AIAgent.run_conversation(...)` 在 [run_agent.py:5441-5464](../../../submodules/hermes-agent/run_agent.py#L5441-L5464) 只是转发。主循环从 [conversation_loop.py:613](../../../submodules/hermes-agent/agent/conversation_loop.py#L613) 开始，根据 `max_iterations`、`IterationBudget` 和 `_budget_grace_call` 控制是否继续调用模型。

### Q: Hermes 更像 Claw-Code 还是 DeerFlow？

> **状态**: draft  
> **来源**: source-code / discussion

A: 从 Agent Loop 形态看，Hermes 更像 Claw-Code：它有手写 loop，显式处理 API 调用、tool_calls、工具执行、tool result 回写和最终回答。不同之处是 Hermes 的 loop 更强调个人 Agent 的长期协作：memory prefetch、plugin hooks、steer、session persistence、provider fallback、context compression、skill nudge 等都被纳入同一个 turn loop。DeerFlow 则更多把底层模型/工具循环交给 LangGraph agent runtime。

### Q: Hermes 的 interrupt 和 steer 有什么区别？

> **状态**: draft  
> **来源**: source-code

A: `interrupt(...)` 是硬中断：设置 `_interrupt_requested`，通知当前执行线程、并发工具 worker 和子 agent，让主 loop / 工具执行尽快停止。`steer(...)` 是软引导：不停止当前工具，而是把用户补充说明暂存起来，等当前工具结果产生后追加到 tool result 中，让模型在下一轮 API 调用看到。源码见 [run_agent.py:2487-2638](../../../submodules/hermes-agent/run_agent.py#L2487-L2638)。

### Q: Hermes 如何防止工具循环无限运行？

> **状态**: draft  
> **来源**: source-code

A: 主要靠 `max_iterations` 和 `IterationBudget`。主循环条件同时检查 `api_call_count < agent.max_iterations` 和 `agent.iteration_budget.remaining > 0`，见 [conversation_loop.py:613](../../../submodules/hermes-agent/agent/conversation_loop.py#L613)。`IterationBudget` 是线程安全计数器，定义在 [iteration_budget.py:16-58](../../../submodules/hermes-agent/agent/iteration_budget.py#L16-L58)。此外工具 guardrail、invalid tool retries、invalid JSON retries、empty response retries 等也会在不同异常路径中阻止无限自我修复循环。

### Q: Hermes 的 loop 准备过程和 Claw-Code 基本类似吗？

> **状态**: draft  
> **来源**: discussion / source-code

A: 结构角色类似，都是进入模型/工具循环前的 turn prologue：准备消息、system prompt、历史上下文、工具/配置、压缩和本轮状态。但目标不同。Claw-Code 的准备过程偏 coding turn runtime：围绕本地 session、项目上下文、权限、工具和 `maybe_auto_compact`。Hermes 的准备过程偏 personal agent turn context：`build_turn_context(...)` 还负责 memory prefetch、plugin context、todo/nudge hydration、session persistence、crash-resilience、external memory 等长期协作上下文。简言之：两者都有“本轮上下文准备”，但 Hermes 准备的是更厚的个人历史和长期运行上下文。

### Q: Hermes 的 `run_conversation` 为什么会长成一个很长的文件 / 函数？

> **状态**: draft  
> **来源**: discussion / source-code

A: Agent Loop 天然容易变成“控制流磁铁”：memory prefetch 要在 API call 前注入，plugin hooks 要插在 pre/post API 或 pre/post tool，provider fallback 要包住 API retry，empty response recovery 要在模型返回后判断，interrupt / steer 要在 loop 顶部和工具前后检查，session persistence 要在工具副作用前后保存，context compression 要在工具结果进入上下文后判断。这些功能都必须依赖 loop 的精确位置和顺序，因此很容易被吸到 `run_conversation` 周边。

Hermes 实际已经把一些实现外提到 `build_turn_context(...)`、`tool_executor.py`、transport normalize、`finalize_turn(...)`、plugin middleware、compression helper、tool guardrails 等模块，但主循环仍保留大量控制流分叉：retry / fallback / partial / continue / break / tool error / final response 等。强行拆得很碎会让控制流隐藏在多个 handler 之间，调试时反而更难判断为什么继续、重试、fallback 或结束。因此这更像典型 agent-loop god function 的维护性风险：行为可见、补丁直接，但文件变长、职责聚合、后续重构困难。

### Q: Hermes 的 `interrupt` / `steer` 属于 Agent Loop 还是后续专题？

> **状态**: draft  
> **来源**: discussion / source-code

A: 在 Agent Loop 阶段只需要理解它们如何影响 loop：`interrupt` 是硬打断，会让主 loop、工具 worker、子 agent 尽快停下；`steer` 是软引导，不中断当前工具，而是暂存用户补充说明，并在工具结果产生后追加到 tool message 中，让下一轮模型调用看到。具体插入位置、role alternation、tool_call_id 对齐、是否持久化、多入口消息如何注入等细节，不宜在 Agent Loop 一次讲完，后续更适合放到 `interrupt-steer.md`、HITL / interaction runtime 或 message protocol / tool-calling 专题。

### Q: 软引导是不是只是“下一轮插一句话”？

> **状态**: draft  
> **来源**: discussion / source-code

A: 概念上像“下一轮补一句方向”，工程上不能随便插一条新的 user message，因为 tool-calling 协议要求 assistant 的 tool_calls 后面要跟对应 tool result；在 tool result 未补齐时插入 user message 可能破坏 role alternation 或 tool_call_id 对齐。Hermes 的方式是把 steer 文本暂存在 `_pending_steer`，在工具批次结束后通过 `_drain_pending_steer()` 追加到最后一个 tool result，使消息序列仍保持 `assistant(tool_calls) -> tool(result + steer) -> assistant(next)` 的合法结构。这是 Agent Loop 的控制点，但完整机制应在 HITL / interaction runtime / message protocol 专题继续核验。

## 后续分流到其他 Hermes 专题的问题

| 问题 | 后续专题 |
|---|---|
| `build_turn_context` 如何注入 memory / plugin / session context？ | `memory-system.md` / `session-persistence.md` |
| provider transport 如何统一 OpenAI / Anthropic / Bedrock / Codex 响应？ | `provider-runtime.md` |
| `tool_search`、toolsets、guardrails 如何治理工具面？ | `tool-system.md` |
| interrupt 如何和 gateway / CLI / worker thread 协同？ | `interrupt-steer.md` |
| steer 作为“不中断引导”适合哪些交互场景？ | `interrupt-steer.md` |
| context compression 与 prompt caching 如何保持长期会话可持续？ | `memory-context.md` |
| SessionDB / trajectory 如何支持 crash recovery？ | `session-persistence.md` |

## 相关文档

- 项目入口：[README.md](README.md)
- Claw-Code Agent Loop 对照：[../claw-code/agent-loop.md](../claw-code/agent-loop.md)
- DeerFlow Agent Loop 对照：[../deer-flow/agent-loop.md](../deer-flow/agent-loop.md)
- 横向 QA：[../../comparison/qa.md](../../comparison/qa.md)
- 项目定位对比：[../../comparison/project-positioning.md](../../comparison/project-positioning.md)
