# DeerFlow Multi-Agent：Lead Agent、Subagent 与 Delegation Ledger

> **日期**: 2026-07-08 | **状态**: draft | **涉及版本**: `c9fb9768d476e28de0294ac7a23cab9819b93f83`

## 相关文档

- DeerFlow 项目入口：[README.md](README.md)
- Agent Loop：[agent-loop.md](agent-loop.md)
- Tool System：[tool-system.md](tool-system.md)
- Context Management：[context-management.md](context-management.md)
- Sandbox / Workspace：[sandbox-workspace.md](sandbox-workspace.md)
- Permission / Security：[permission-security.md](permission-security.md)
- 横向 Agent Loop 总结：[../../comparison/agent-loop.md](../../comparison/agent-loop.md)
- 横向 Multi-Agent 总结：[../../comparison/multi-agent.md](../../comparison/multi-agent.md)
- 横向 Context Management 总结：[../../comparison/context-management.md](../../comparison/context-management.md)
- 横向 QA：[../../comparison/qa.md](../../comparison/qa.md)

## 源码入口

| 模块 | 源码 | 作用 |
|---|---|---|
| Lead agent 装配 | [lead_agent/agent.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/agent.py) | 创建 lead agent，装配 model、tools、middleware、`ThreadState`，并按 runtime config 决定是否启用 subagent 工具和并发限制。 |
| Lead prompt subagent 指导 | [lead_agent/prompt.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/prompt.py) | 告诉 Lead Agent 何时拆分任务、何时不要用 subagent、如何分 batch 并行。 |
| `task` 工具 | [tools/builtins/task_tool.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/tools/builtins/task_tool.py) | Lead Agent 调用 subagent 的桥：解析 `subagent_type`、继承父 runtime context、启动 `SubagentExecutor`、轮询并返回 `ToolMessage`。 |
| Subagent 配置模型 | [subagents/config.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/subagents/config.py) | `SubagentConfig`：name、description、system_prompt、tools、skills、model、max_turns、timeout 等。 |
| Subagent registry | [subagents/registry.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/subagents/registry.py) | 内置 subagent + custom subagent 的解析、覆盖、可见性判断。 |
| Subagent executor | [subagents/executor.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/subagents/executor.py) | 创建并运行子 agent，管理 background task、isolated event loop、状态、取消、超时和结果提取。 |
| General-purpose subagent | [subagents/builtins/general_purpose.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/subagents/builtins/general_purpose.py) | 通用复杂任务 subagent，继承父工具，禁止嵌套 `task`、`ask_clarification`、`present_files`。 |
| Bash subagent | [subagents/builtins/bash_agent.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/subagents/builtins/bash_agent.py) | 命令执行 specialist，只暴露 bash / file 类工具。 |
| Subagent 并发限制 | [subagent_limit_middleware.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/subagent_limit_middleware.py) | 截断单次模型响应中过量的 `task` tool calls，防止并发失控。 |
| Delegation ledger | [delegation_ledger.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/delegation_ledger.py) | 从 `messages` 中抽取 `task` 派工记录和结果，并渲染成 “Work already delegated”。 |
| Durable context middleware | [durable_context_middleware.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/durable_context_middleware.py) | 把 delegation ledger 写入 `ThreadState.delegations`，并在后续模型调用前作为低权限 durable context 注入。 |
| ThreadState | [thread_state.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/thread_state.py) | Lead / subagent 共用的 state schema，包含 `messages`、`sandbox`、`thread_data`、`delegations`、`summary_text` 等。 |
| Subagent 配置示例 | [config.example.yaml](../../../submodules/deer-flow/config.example.yaml) | `subagents:` 配置示例：timeout、max_turns、per-agent override、custom_agents。 |

## 核心结论

DeerFlow 的多 Agent 结构不是固定写死的 `coordinator -> planner -> researcher -> coder -> reporter` 节点图，而是一个 **Lead Agent 动态派工** 模型：

```text
Lead Agent
  -> 通过 task 工具委派
      -> SubagentExecutor
          -> built-in subagent / custom subagent
              -> 独立 LangGraph agent run
                  -> 结果回到 Lead Agent 的 tool_result
                  -> delegation ledger 持久化摘要
```

通俗比喻：

> **DeerFlow 像一个工作流工厂。Lead Agent 是总工 / 调度员，subagent 是被临时叫来的外包小组。每个小组拿到一张工单，去同一个工厂 workspace 里独立干活；小组进展会通过看板事件回报，最终结果交回总工，总工再综合。**

最核心的判断是：

> **DeerFlow 的多 Agent 是“受控的一层派工”：Lead Agent 可以把复杂任务拆给 subagent，但 subagent 不再拿到 `task` 工具，不能继续无限派工；子 agent 的中间过程隔离，最终结果以标准工具结果回流，并被 delegation ledger 记成可复用的派工历史。**

## 一、为什么 DeerFlow 需要 subagent？

复杂任务如果全部由 Lead Agent 自己完成，会遇到几个工程问题。

第一是 **上下文污染**。大任务通常会产生大量搜索、文件阅读、命令输出和中间推理。很多中间过程只服务于某个局部子问题，不应该长期留在主对话里。如果全部塞回 Lead Agent 的 `messages`，主上下文会越来越脏，模型后续判断也更容易被无关细节干扰。

第二是 **任务天然可并行**。例如分析一个大代码库，可以让不同 subagent 分别看认证、数据层、测试、部署配置。Lead Agent 不必自己串行读完所有文件，而是可以把任务拆成几个相对独立的小工单，让多个 subagent 同时处理。

第三是 **工具输出噪声很大**。bash、测试日志、搜索结果和构建输出常常很长。让 subagent 去消化这些噪声，再返回一份浓缩报告，可以保护主上下文。

第四是 **不同子任务需要不同能力边界**。有的任务需要通用探索，有的只需要命令执行，有的可能需要特定 skill 或特定模型。DeerFlow 用 `SubagentConfig` 把这些差异配置化，而不是把所有工作都塞给同一个 Lead Agent。

**精髓标记：DeerFlow subagent 的第一价值是“上下文隔离 + 并行分解”，不是固定角色扮演。**

## 二、谁是调度者：Lead Agent，而不是固定 supervisor 节点

DeerFlow 当前主线里，没有把多 Agent 流程写成固定的 `planner / researcher / coder / reporter` graph 节点。真正的调度者是 Lead Agent 本身。

Lead Agent 会根据任务现场决定：

```text
这个任务要不要拆？
拆成几个子任务？
哪些子任务可以并行？
每个子任务交给哪类 subagent？
结果回来以后如何综合？
```

这和固定 workflow 节点不同。固定多角色 graph 往往是：

```text
节点 A 必然执行
  -> 节点 B 必然执行
      -> 节点 C 必然执行
```

DeerFlow 更像：

```text
Lead Agent 临场判断
  -> 需要时才开外包小组
  -> 不需要时直接自己使用工具完成
```

Lead prompt 对 subagent 的使用方式有明确指导：复杂研究、多维分析、大代码库、全面调查适合拆；简单单步动作、需要澄清、顺序依赖任务不适合拆，见 [prompt.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/prompt.py)。

**精髓标记：DeerFlow 是“Lead Agent 动态派工”，不是“固定多角色图”。**

## 三、`task` 工具：把普通工具调用升级成子 Agent 调度

`task` 工具是 Lead Agent 调用 subagent 的入口。可以把它理解成一张“派工单”。

Lead Agent 调用 `task` 时，需要给出：

| 字段 | 含义 |
|---|---|
| `description` | 工单短标题，便于日志和 UI 展示。 |
| `prompt` | 子 agent 真正要完成的详细任务说明。 |
| `subagent_type` | 要调用哪类 subagent，例如 `general-purpose`、`bash` 或自定义 subagent。 |

普通工具调用是“执行一个动作”，例如读文件、跑命令、写文件。`task` 则是“启动一个新的小 agent 去完成一段工作”。它把多 Agent 调度包装进标准 tool-calling 协议里。

这样设计的好处是：Lead Agent 不需要进入另一套特殊的 agent-to-agent 协议；它只是调用了一个工具。LangGraph / LangChain runtime 仍然看到的是标准的 tool call / tool result。

**精髓标记：`task` 是“把工具调用升级成子 Agent 调度”的桥。**

## 四、Subagent 类型：内置工种 + 配置化专门小组

DeerFlow 当前有两个典型内置 subagent。

### general-purpose：通用外包小组

`general-purpose` 适合复杂、多步、需要探索和行动的任务。它可以继承父 agent 的大部分工具，自己阅读文件、搜索、运行工具、综合结果，最后返回一份简洁报告。

它像一个通用研究 / 执行小组：

```text
给它一张复杂工单
  -> 它自己探索
  -> 自己使用工具
  -> 自己整理结果
  -> 最后给 Lead Agent 一份摘要
```

### bash：命令执行小组

`bash` subagent 更像命令执行 specialist。它适合跑一串相关命令、处理 verbose output、执行构建 / 测试 / 部署前检查，并把嘈杂输出整理成可读结果。

它不适合简单单命令；简单命令 Lead Agent 可以直接调用 bash 工具。它适合那种“命令过程可能很长、结果需要整理”的场景。

### custom subagent：配置化专门工种

DeerFlow 还允许在 `config.yaml` 中定义 custom agents。每个 custom subagent 可以配置：

- 什么时候适合用它；
- 它的 system prompt；
- 可用工具 allowlist；
- 禁用工具 denylist；
- skill whitelist；
- 是否继承父模型；
- 最大 turns；
- timeout。

所以 DeerFlow 的“多角色”不是硬编码在 graph 中，而是通过 registry 和配置系统变成可扩展工种。

**精髓标记：DeerFlow 的“多角色”不是硬编码在 graph 里，而是通过 subagent registry 和 config.yaml 配出来的。**

## 五、Lead / Subagent 的状态流转整体结构

DeerFlow 的 Lead Agent 和 subagent 不是共享同一份完整状态，而是“父状态下发一部分运行上下文，子状态独立执行，最终结果再回写父状态”。

整体结构可以写成：

```text
用户输入
  -> Lead Agent ThreadState
     - messages
     - sandbox
     - thread_data
     - delegations
     - summary_text
     - skill_context
  -> Lead 模型决定调用 task
  -> AIMessage(tool_calls=[task])
  -> task_tool 读取父 runtime / state
     - sandbox_state
     - thread_data
     - thread_id
     - user_id / user_role
     - run_id
     - trace_id
     - parent_model
  -> SubagentExecutor 创建子 agent 初始状态
     - messages = [子 agent system prompt, 子任务 prompt]
     - sandbox = 继承自父
     - thread_data = 继承自父
  -> Subagent 独立执行模型 / 工具循环
  -> 产生 task_started / task_running / task_completed 等事件给 UI
  -> 最终结果包装成 ToolMessage(name="task") 回到 Lead messages
  -> DurableContextMiddleware 抽取 delegation ledger
  -> ThreadState.delegations 记录派工台账
  -> 后续模型调用前注入 durable_context_data
```

这条链路的关键在于：

```text
messages 不完整共享，运行环境和身份归属部分继承。
```

子 agent 不会直接拿到 Lead Agent 的整段聊天历史。它拿到的是自己的任务说明、自己的 system prompt、可用工具，以及从父 run 继承来的 workspace / sandbox / user / trace 等运行上下文。

这样可以同时满足两个目标：

1. **上下文隔离**：子任务中间噪声不污染 Lead Agent。
2. **执行一致性**：子 agent 仍然在同一个 workspace / sandbox / 用户身份下工作。

**精髓标记：DeerFlow 子 agent 继承的是“工作环境和权限身份”，不是父 agent 的完整思考历史。**

## 六、子 agent 是完整 Agent，但不是新的长期 thread

SubagentExecutor 会为子任务创建一个新的 LangGraph agent。这个子 agent 有自己的 messages、工具循环、middleware 和 `ThreadState` schema，因此它不是一个普通函数调用。

但是它和 Lead Agent 又有一个关键区别：子 agent 的 graph `checkpointer=False`。这说明它不是一个新的长期 thread，而是一次性的 delegated task。

可以这样理解：

```text
Lead Agent：
  是主 thread 的长期运行者，有 checkpoint、run lifecycle、stream、rollback 等平台语义。

Subagent：
  是一次性外包任务，有独立执行状态和工具循环，但不作为新的长期 thread 保存完整 checkpoint。
```

这很像工厂里的临时外包小组：它能独立施工，有自己的施工日志，但它不是新开一个长期项目线。最终它交付结果，主项目继续由总工推进。

**精髓标记：DeerFlow subagent 是完整 Agent，但不是新的长期 thread；它是一次性 delegated run。**

## 七、子 agent 的工具边界：禁止无限嵌套 delegation

子 agent 的工具不是无条件继承。DeerFlow 会通过多层规则过滤工具：

```text
父 agent 的 tool_groups
  -> subagent_enabled=False
  -> subagent config 的 tools allowlist
  -> disallowed_tools denylist
  -> skill allowed-tools
  -> deferred MCP tool_search
```

其中最重要的一点是：**子 agent 不会再拿到 `task` 工具。**

如果不限制，系统可能变成无限递归的 Agent 树：

```text
Lead Agent
  -> subagent A
      -> subagent B
          -> subagent C
              -> subagent D
                  -> ...
```

这种无限嵌套会带来一连串工程问题：

- 上下文层级失控；
- 成本和并发指数级扩散；
- 权限归属难以判断；
- 中间失败难以汇总；
- 取消、超时、回滚难以传播；
- Lead Agent 很难知道最终结果来自哪一层。

所以 DeerFlow 选择把多 Agent 控制成一层派工：Lead Agent 可以派 subagent，但 subagent 不能继续派孙 agent。

> **精髓标记：子 agent 不会再拿到 `task` 工具，防止无限嵌套 delegation。DeerFlow 把多 Agent 控制成“Lead -> Subagent”一层派工，而不是无限递归的 Agent 树。**

## 八、Subagent 如何运行：后台工单，而不是普通函数

SubagentExecutor 运行子 agent 时，不是简单 `result = child_agent(prompt)`。它更像一个受管理的后台工单系统。

大致流程是：

```text
1. 创建 SubagentResult，状态为 PENDING。
2. 放进全局 background task registry。
3. scheduler thread pool 接手调度。
4. 在 persistent isolated event loop 中运行子 agent。
5. 子 agent 自己执行 LangGraph agent.astream(...)。
6. 执行过程中捕获 assistant turns 和 tool outputs。
7. 根据结果转为 COMPLETED / FAILED / CANCELLED / TIMED_OUT / MAX_TURNS_REACHED。
8. task_tool 周期性轮询这个后台状态。
```

这套机制让 DeerFlow 可以处理长任务、超时、取消、实时进展和 token usage 记录，而不是把子 agent 当成一次同步函数调用。

## 九、子 agent 状态：区分失败、超时、取消和 max_turns

DeerFlow 的 subagent 状态包括：

| 状态 | 含义 |
|---|---|
| `PENDING` | 工单已创建，还没真正开始。 |
| `RUNNING` | 子 agent 正在执行。 |
| `COMPLETED` | 正常完成并返回结果。 |
| `FAILED` | 执行异常或工具失败导致任务失败。 |
| `CANCELLED` | 被父 run / 用户取消。 |
| `TIMED_OUT` | 超过执行时间上限。 |
| `MAX_TURNS_REACHED` | 子 agent 用尽最大 turn budget，但可能已有 partial result。 |

这里最值得注意的是 `MAX_TURNS_REACHED`。它不是普通失败，而是“预算耗尽但可能已有阶段成果”。因此 Lead Agent 可以复用 partial result、缩小范围重试，或者提高 max_turns。

**精髓标记：DeerFlow 区分 failed、timed_out、cancelled、max_turns_reached，让 Lead Agent 能根据失败类型采取不同策略。**

## 十、结果回流：UI 事件线 + Lead 工具结果线

子 agent 的进展有两条回流路径。

### 路径一：给 UI / StreamBridge 的事件线

task_tool 会把子 agent 状态变成事件：

```text
task_started
task_running
task_completed
task_failed
task_cancelled
task_timed_out
```

这条线服务于用户观测。它像工厂看板：用户能看到工单启动、运行、完成、失败或超时。

### 路径二：给 Lead Agent 的工具结果线

对 Lead Agent 来说，子 agent 最终表现为一个普通工具结果：

```text
AIMessage(tool_calls=[task])
  -> ToolMessage(name="task", content="...")
```

这意味着多 Agent 协作复用了标准 tool-calling 协议。Lead Agent 下一轮只需要读这个 `task` 工具结果，然后继续综合、决策或追加下一批 subagents。

**精髓标记：DeerFlow subagent 对 UI 是“任务事件流”，对 Lead Agent 是“一个 task 工具结果”。**

**精髓标记：DeerFlow 把 subagent 结果伪装成普通 `task` 工具结果，让多 Agent 协作复用标准 tool-calling 协议。**

## 十一、Delegation ledger：中间件维护的派工台账

Delegation ledger 是 DeerFlow 多 Agent 很关键的一层。

如果只有原始 `messages`，Lead Agent 后续要自己从历史里回忆：

```text
我刚才派过哪些任务？
哪些完成了？
哪些失败了？
哪些还在进行中？
哪些结果可以复用？
失败的是不是应该换策略重试？
```

这既不稳定，也容易受 summarization 影响。DeerFlow 因此把 `task` 派工历史提炼成结构化台账：

```text
ThreadState.delegations
```

### delegation ledger 工作在哪里？

严格说，`delegation_ledger.py` 本身不是 middleware 类。它负责两件事：

1. 从 `messages` 中抽取 `task` tool call 和 paired `ToolMessage`；
2. 把抽取出的 entries 渲染成模型可读的 “Work already delegated”。

真正把它接入运行时的是 `DurableContextMiddleware`。所以机制上可以说：

> **delegation ledger 是 DurableContextMiddleware 管理的一条状态通道。它由中间件维护、写入 `ThreadState.delegations`，再在后续模型调用前投影回 Lead Agent。**

### 它怎么抽取？

它会先看 Lead `messages` 里的 `task` tool call：

```text
看到 Lead 发出 task 派工
  -> 记录一条 in_progress delegation
```

等对应的 `ToolMessage(name="task")` 回来后：

```text
读取 ToolMessage additional_kwargs 中的 subagent status / result / error
  -> 把 delegation 更新成 completed / failed / timed_out / max_turns_reached 等
  -> 记录 result_brief / result_sha256 / result_ref
```

这就像项目经理维护表格：

| 工单 | 小组 | 状态 | 结果 |
|---|---|---|---|
| 分析认证模块 | general-purpose | completed | 找到 3 个问题 |
| 跑测试 | bash | failed | npm install 失败 |
| 调研 API | general-purpose | in_progress | 暂无 |

### 它怎么注入后续模型？

`DurableContextMiddleware` 会在后续模型调用前，把 `ThreadState.delegations` 渲染成隐藏 durable context，大意是：

```text
Work already delegated:
- [completed] xxx via general-purpose -> completed result; do NOT delegate again; reuse this result
- [failed] yyy via bash -> failed attempt; may retry with a changed plan
- [in_progress] zzz -> already delegated; do NOT delegate again
```

这让 Lead Agent 在下一轮决策前看到派工台账，避免重复派工，也能复用已完成结果。

### 它和普通 messages 的区别

```text
messages：事件流水账
  记录发生过什么。

delegation ledger：派工状态表
  提炼出哪些任务被派出、当前状态是什么、结果能不能复用。
```

普通 messages 可能很长、可能被压缩、也不方便模型稳定读取。Delegation ledger 则是专门为多 Agent 协作提炼出来的结构化状态。

**精髓标记：delegation ledger 是 DeerFlow 多 Agent 的“派工台账”，它让 Lead Agent 记得哪些工作已经委派、哪些结果可复用、哪些失败需要换策略。**

**精髓标记：messages 是事件历史，delegation ledger 是从事件历史中提炼出来的任务状态表。**

**精髓标记：DeerFlow 把 subagent 历史作为“低权限耐久数据”注入，而不是提升成 system 指令。**

## 十二、并发控制：软提示、硬截断、工位上限

DeerFlow 的 subagent 并发不是无限开放，而是三层控制。

第一层是 prompt 软提示。Lead prompt 告诉模型：复杂任务可以拆，但每轮最多派出 `n` 个 `task`；如果子任务超过上限，要分 batch。

第二层是 middleware 硬截断。`SubagentLimitMiddleware` 会检查模型一次响应里发出的 `task` tool calls。如果超过上限，只保留前几个，丢弃超出的。这防止模型不听 prompt 时真的派出过多 subagents。

第三层是 executor 工位上限。SubagentExecutor 后台有 scheduler pool 和最大并发限制，确保系统实际运行时不会无限开工。

可以概括为：

```text
Prompt 是调度规则
Middleware 是门禁
Thread pool 是实际工位数量
```

**精髓标记：DeerFlow 的 subagent 并发是“软提示 + 硬截断 + 工位上限”三层控制，不是无限并行。**

## 十三、和固定多角色 workflow 的区别

DeerFlow 基于 LangGraph，但当前多 Agent 结构不是固定 graph 多节点团队。

| 模式 | 特点 |
|---|---|
| 固定多角色 graph | 角色节点预先定义，流程顺序较固定，例如 planner -> researcher -> reporter。 |
| DeerFlow 当前模式 | Lead Agent 动态决定是否委派、委派给谁、并行多少、何时综合。 |
| Claude Code-like subagent | 主 agent 调 task 工具，子 agent 隔离上下文后返回结果。 |

因此 DeerFlow 的特殊点是：

> **它把 Claude Code-like 的 task subagent 模式，放进 LangGraph run / middleware / ThreadState / checkpoint 平台里。**

## QA / 讨论记录

### Q: DeerFlow 的多 Agent 是固定 planner / researcher / coder / reporter 结构吗？

> **状态**: verified
> **来源**: source-code / discussion

A: 当前源码主线不是固定的 planner / researcher / coder / reporter 节点图，而是 Lead Agent 动态调用 `task` 工具，把任务交给 registry 中的 built-in 或 custom subagent。角色可以通过 `SubagentConfig` 和 `config.yaml` 扩展，但不是写死在固定 graph 节点中。

### Q: Lead Agent 和 subagent 是否共享同一份完整状态？

> **状态**: verified
> **来源**: source-code / discussion

A: 不共享完整状态。Lead Agent 有主 `ThreadState`；subagent 会创建自己的初始 `messages` 和独立 LangGraph agent。父 run 会下发 sandbox、thread_data、thread_id、user / role / run / trace 等运行上下文，但不会把 Lead 的完整 messages 复制给子 agent。子 agent 最终通过 `ToolMessage(name="task")` 把结果回给 Lead。

### Q: 为什么子 agent 不再拥有 `task` 工具？

> **状态**: verified
> **来源**: source-code / discussion

A: 这是为了防止无限嵌套 delegation。如果 subagent 还能继续调用 `task`，系统可能形成 Lead -> subagent -> subagent -> ... 的递归 Agent 树，导致上下文、成本、权限归属、取消传播和结果回流都失控。DeerFlow 通过 `subagent_enabled=False`、默认 `disallowed_tools=["task"]` 等边界，把多 Agent 控制成 Lead -> Subagent 的一层派工。

### Q: delegation ledger 是什么，它是不是 middleware？

> **状态**: verified
> **来源**: source-code / discussion

A: delegation ledger 是 DeerFlow 多 Agent 的派工台账。严格说，`delegation_ledger.py` 是抽取 / 渲染逻辑模块，不是 middleware 类；真正把它接入 agent 生命周期的是 `DurableContextMiddleware`。它从 `messages` 中抽取 `task` tool call 和 paired `ToolMessage`，写入 `ThreadState.delegations`，再在后续模型调用前作为低权限 durable context 投影给 Lead Agent。

### Q: delegation ledger 和普通 messages 有什么区别？

> **状态**: verified
> **来源**: source-code / discussion

A: messages 是事件流水账，记录用户、模型、工具调用和工具结果；delegation ledger 是从这份流水账中提炼出来的结构化派工状态表。它告诉 Lead Agent 哪些工作已经委派、哪些还在进行、哪些已经完成且结果可复用、哪些失败需要换策略。这样可以防止重复委派，也能在 messages 被压缩后保留关键派工状态。
