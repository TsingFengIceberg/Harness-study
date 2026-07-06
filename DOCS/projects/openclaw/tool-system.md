# OpenClaw Tool System：工具装配管线、事件化执行与产品级治理

> **日期**: 2026-07-02 | **状态**: draft | **涉及版本**: `cb44f40474bd88d3ba2e1c3c3f60767c9f6194e5`

## 相关文档

- 项目入口：[README.md](README.md)
- Agent Loop：[agent-loop.md](agent-loop.md)
- 横向对比：[Tool System 横向总结](../../comparison/tool-system.md)
- 横向 QA：[qa.md](../../comparison/qa.md#tool-system--工具体系)

## 源码入口

| 模块 | 源码 | 作用 |
|---|---|---|
| 工具抽象 | [types.ts](../../../submodules/openclaw/packages/agent-core/src/types.ts) | `AgentTool`、`AgentToolResult`、`ToolExecutionMode`、`beforeToolCall` / `afterToolCall` 等核心类型。 |
| Loop 执行工具 | [agent-loop.ts](../../../submodules/openclaw/packages/agent-core/src/agent-loop.ts) | `executeToolCalls`、sequential / parallel 调度、`prepareToolCall`、`executePreparedToolCall`、`ToolResultMessage` 回写。 |
| Agent 状态外壳 | [agent.ts](../../../submodules/openclaw/packages/agent-core/src/agent.ts) | `Agent` 持有 tools、messages、steer/followUp 队列，并把 hook 配置传给 loop。 |
| Harness 装配层 | [agent-harness.ts](../../../submodules/openclaw/packages/agent-core/src/harness/agent-harness.ts) | `CoreAgentHarness` 管理 session、active tools、hook 事件、turn state 和 tool result 持久化。 |
| 工具面总装配 | [agent-tools.ts](../../../submodules/openclaw/src/agents/agent-tools.ts) | `createOpenClawCodingTools` 按 run/session/channel/model/sandbox/policy 动态组装本轮工具面。 |
| OpenClaw 内置工具 | [openclaw-tools.ts](../../../submodules/openclaw/src/agents/openclaw-tools.ts) | message、sessions、subagents、cron、gateway、web、media、nodes、goal、update_plan 等产品工具 factory。 |
| before_tool_call runtime | [agent-tools.before-tool-call.ts](../../../submodules/openclaw/src/agents/agent-tools.before-tool-call.ts) | plugin hooks、trusted policy、approval、diagnostics、loop detection、skill telemetry、参数调整。 |
| 工具策略管线 | [tool-policy-pipeline.ts](../../../submodules/openclaw/src/agents/tool-policy-pipeline.ts) | profile / provider / agent / group / sender / sandbox / subagent / inherited policies 分层过滤工具。 |
| Tool Search | [tool-search.ts](../../../submodules/openclaw/src/agents/tool-search.ts) | `tool_search` / `tool_describe` / `tool_call` / `tool_search_code` 管理大规模 OpenClaw / MCP / client 工具目录。 |
| MCP 工具物化 | [agent-bundle-mcp-materialize.ts](../../../submodules/openclaw/src/agents/agent-bundle-mcp-materialize.ts) | 将 MCP catalog 投影成 `AgentTool`，并根据 server 能力设置并发模式。 |

## 一句话总结

OpenClaw 的 Tool System 是一个 **面向多端 Agent 产品的工具调度与治理平台**：它不是单一 tools 大中枢，而是把工具抽象、工具装配、策略过滤、hook / approval 包裹、事件化执行、Tool Search 目录压缩和 session 回写拆成多层。

最关键的判断是：

> **OpenClaw 的工具系统像“带进度大屏和安全审批的后厨调度系统”：模型不是直接拿工具干活，而是下工具工单；OpenClaw 先核单、再决定排队或并行、执行中持续发事件、最后把验收单写回会话给模型继续推理。**

如果和 Claw-Code 对比：

```text
Claw-Code：本地老师傅 / 本地万能工具箱
OpenClaw：多端工作室 / 工具调度与治理平台
```

## 总体流程

OpenClaw 工具调用主链路可以压缩成：

```text
AgentTool 定义工具对象
  -> createOpenClawCodingTools 动态组装本轮工具面
    -> tool policy pipeline 根据 profile/provider/agent/group/sender/sandbox/subagent/inheritance 过滤
      -> normalizeToolParameters 做 provider schema 兼容
        -> wrapToolWithBeforeToolCallHook 给工具套上 before_tool_call policy runtime
          -> AgentLoopConfig 把 tools 交给 provider-visible context
            -> 模型返回 assistant toolCall
              -> executeToolCalls 判断 sequential / parallel
                -> prepareToolCall 核单、校验参数、beforeToolCall
                  -> executePreparedToolCall 调用 tool.execute
                    -> tool_execution_update 发进度
                      -> finalizeExecutedToolCall 运行 afterToolCall
                        -> tool_execution_end
                          -> ToolResultMessage 写入 transcript
                            -> 下一轮模型看到 tool result 后继续推理
```

这个流程说明：

> **OpenClaw 的工具系统不是“工具定义 + 执行函数”这么简单，而是一个围绕 Agent Session、产品事件、权限策略、插件生态和多端 UI 组织起来的运行时管线。**

## AgentTool：带 UI、进度和并发策略的工具对象

`AgentTool` 定义在 [types.ts](../../../submodules/openclaw/packages/agent-core/src/types.ts)，继承自 llm-core 的 `Tool`。

它包含：

```text
name
  给模型和 runtime 识别的工具名

description
  给模型看的工具说明

parameters
  TypeBox / JSON schema 参数

label
  UI 展示标签

prepareArguments
  schema 校验前的参数兼容修正

execute
  实际执行函数

executionMode
  工具级 sequential / parallel 覆盖
```

相比 Claw-Code 的 `ToolSpec`，OpenClaw 的 `AgentTool` 更产品化：

| 能力 | 含义 |
|---|---|
| `label` | 工具可以面向 UI 展示。 |
| `prepareArguments` | 可以兼容 provider / 旧 schema / 模型参数差异。 |
| `onUpdate` | 工具执行中可以发进度。 |
| `executionMode` | 工具自己声明能否并发。 |
| `AgentToolResult.details` | 工具结果可同时服务模型、UI 和日志。 |

所以可以这样概括：

> **Claw-Code 的工具更像本地函数能力；OpenClaw 的工具更像一个可展示、可进度更新、可策略包裹、可参与事件流的产品对象。**

## AgentToolResult：不只是字符串

OpenClaw 的 `AgentToolResult` 定义在 [types.ts](../../../submodules/openclaw/packages/agent-core/src/types.ts)：

```text
content
  给模型看的 text / image 内容

details
  给 UI / logs / runtime 的结构化细节

progress
  执行过程中的公开进度提示

terminate
  是否提示当前工具 batch 后终止
```

这和 Claw-Code 的 `ToolExecutor.execute(...) -> Result<String, ToolError>` 形成对比：

| 维度 | Claw-Code | OpenClaw |
|---|---|---|
| 工具返回 | 主要是字符串 output | `content` + `details` + `progress` + `terminate` |
| 面向对象 | 模型下一轮 observation | 模型 + UI + session + diagnostics |
| 进度 | 主要靠工具输出或外部任务 | 工具执行中可发 `tool_execution_update` |
| 终止提示 | loop 主逻辑判断 | 工具结果可带 `terminate` hint |

这体现了 OpenClaw 更强的产品 runtime 味道。

## 工具执行：像后厨工单调度

OpenClaw 的工具执行主线在 [agent-loop.ts](../../../submodules/openclaw/packages/agent-core/src/agent-loop.ts)。

可以用餐厅后厨比喻：

| OpenClaw 概念 | 比喻 |
|---|---|
| 模型输出的 `toolCall` | 客人点的一道菜 / 一张工单 |
| `AgentTool` | 后厨能做的菜品 / 工种 |
| `prepareToolCall` | 前台核单：有没有这道菜？参数对不对？要不要经理批准？ |
| `executePreparedToolCall` | 厨师真正开始做菜 / 工人真正施工 |
| `finalizeExecutedToolCall` | 出餐前质检、包装、改备注 |
| `ToolResultMessage` | 出餐回执 / 工单验收单，交回给模型 |
| `tool_execution_start/update/end` | 后厨大屏进度事件 |
| `message_start/message_end` | 把回执正式写入对话记录 |

一句话：

> **模型不是直接拿工具干活，而是给 OpenClaw 下工单；OpenClaw 像调度员一样核单、调度、监督、记录和回写。**

## sequential / parallel：排队窗口与多窗口并行

`ToolExecutionMode` 定义在 [types.ts](../../../submodules/openclaw/packages/agent-core/src/types.ts)，有两种：

```text
sequential
parallel
```

### sequential：一张做完，再做下一张

对应 [executeToolCallsSequential](../../../submodules/openclaw/packages/agent-core/src/agent-loop.ts)。

流程是：

```text
A start
A prepare
A execute
A finalize
A end
A result message

B start
B prepare
B execute
B finalize
B end
B result message
```

像一个窗口排队办业务：

```text
慢一点，但顺序稳定、状态安全、hook / approval / session 写入清楚。
```

适合：

```text
写文件
编辑文件
发送有顺序语义的消息
操作同一个进程
需要审批或共享状态的工具
```

### parallel：先核单，再多窗口同时办

对应 [executeToolCallsParallel](../../../submodules/openclaw/packages/agent-core/src/agent-loop.ts)。

流程是：

```text
A start
A prepare
B start
B prepare
C start
C prepare

A/B/C 同时 execute

谁先完成谁先 tool_execution_end
最后按原始 A/B/C 顺序生成 ToolResultMessage
```

这点非常关键：

> **UI 关心真实完成顺序，所以 `tool_execution_end` 可以按完成顺序发；模型上下文关心协议稳定和顺序可预测，所以 tool result message 按原始 tool call 顺序回写。**

比喻：

```text
后厨多个人同时做菜；大屏按真实完成顺序显示谁做好了；但服务员最后整理账单时仍按点菜单顺序归档。
```

## 串行 / 并发的判定策略

OpenClaw 的判定逻辑在 [executeToolCalls](../../../submodules/openclaw/packages/agent-core/src/agent-loop.ts)：

```text
如果 config.toolExecution === "sequential"：
  整批工具调用串行执行

否则：
  先预扫描这一批 toolCalls
  对每个 toolCall：
    resolveToolCallTool(...)
    如果这个工具自己的 executionMode === "sequential"：
      hasSequentialToolCall = true
      break

  如果 hasSequentialToolCall：
    整批串行
  否则：
    整批并发
```

也就是：

| 条件 | 结果 |
|---|---|
| 全局 `config.toolExecution === "sequential"` | 整批串行 |
| 全局不是 sequential，但任一工具 `executionMode === "sequential"` | 整批串行 |
| 全局不是 sequential，且没有工具要求 sequential | 整批并发 |

这是一种：

> **默认并行提升效率，但遇到任何串行约束就整批保守降级。**

为什么不是只让那个工具串行、其他工具并行？因为如果某个工具声明不能和别人并发，通常说明它可能依赖共享状态、有外部副作用或需要顺序语义。整批降级虽然保守，但避免文件、消息、进程、审批、session 状态交错。

MCP 工具也体现了这个策略。[agent-bundle-mcp-materialize.ts](../../../submodules/openclaw/src/agents/agent-bundle-mcp-materialize.ts) 会根据 MCP server 是否支持 parallel tool calls 设置工具 `executionMode`：

```text
server.supportsParallelToolCalls === true
  -> parallel
否则
  -> sequential
```

## immediate result：还没开工就退单

`prepareToolCall` 可能返回 `immediate`，意思是：

> **这张工单还没真正执行，就已经确定不能做。**

常见原因：

```text
工具不存在
参数 schema 校验失败
beforeToolCall hook 拦截
审批不通过
run 已 abort
```

这时 OpenClaw 仍然会发 `tool_execution_start` / `tool_execution_end`，但 `executionStarted` 是 false。

比喻：

```text
服务员开始处理订单，但前台发现菜单没有这道菜，或者经理不批准，于是直接退单。厨师没有真的开火，但订单系统仍然要记录“处理过并退单”。
```

## prepareToolCall：前台核单

`prepareToolCall` 位于 [agent-loop.ts](../../../submodules/openclaw/packages/agent-core/src/agent-loop.ts)，它回答：

> **这张工具工单能不能进入执行阶段？**

它做：

```text
resolveToolCallTool
  找当前 visible tools；找不到则尝试 resolveDeferredTool

prepareArguments
  工具自己修正或兼容参数

validateToolArguments
  根据 schema 校验参数

beforeToolCall
  产品层 hook / policy 入口，可 block

abort 检查
  如果 run 已中止，生成 error result
```

这相当于：

```text
先核单，再进厨房。
```

## executePreparedToolCall：真正执行并发进度

`executePreparedToolCall` 会真正调用：

```text
tool.execute(toolCall.id, args, signal, onUpdate)
```

其中 `onUpdate` 会发：

```text
tool_execution_update
```

这让长任务工具可以告诉 UI：

```text
下载中
生成中
测试运行中
远程调用等待中
```

因此 OpenClaw 工具执行不是黑盒，而是一个可观测过程。

## finalizeExecutedToolCall：出餐质检 / after hook

工具执行结束后，`finalizeExecutedToolCall` 会调用 `afterToolCall`。

`afterToolCall` 可以 patch：

```text
content
  给模型看的结果

details
  给 UI / logs 的细节

isError
  是否标记错误

terminate
  是否提示工具 batch 后停止
```

这类似 Claw-Code 的 PostToolUse，但 OpenClaw 更结构化。它不是只追加字符串反馈，而是可以改工具结果对象本身。

## ToolResultMessage：验收单写回会话

最终会创建 `ToolResultMessage`：

```text
role: "toolResult"
toolCallId
toolName
content
details
isError
timestamp
```

这相当于工具执行的验收单。模型下一轮看到它后继续推理。

注意区分两类事件：

| 事件 | 意思 |
|---|---|
| `tool_execution_end` | 工具工单处理结束。 |
| `message_start` / `message_end` | 工具结果消息正式写入 transcript / session。 |

这不是重复，而是面向不同系统：

```text
tool_execution_* 给 UI / runtime 看执行生命周期
message_* 给 transcript / session / model context 看消息生命周期
```

## createOpenClawCodingTools：按上下文动态组装工具车

真正的工具面装配在 [agent-tools.ts](../../../submodules/openclaw/src/agents/agent-tools.ts) 的 `createOpenClawCodingTools`。

它会根据大量 run context 动态组装本轮工具：

```text
agentId
messageProvider / messageChannel / chatType
sandbox
sessionKey / runSessionKey / sessionId
trigger / jobId
workspaceDir / cwd
modelProvider / modelId / modelApi / modelCompat
group / sender / subagent policy
runtimeToolAllowlist
authProfileStore
toolSearchCatalogRef
```

所以 OpenClaw 不是一张静态工具表，而是：

> **按 run / session / channel / model / sandbox / policy 计算出的 effective tool surface。**

它装配的工具大致包括：

```text
base coding tools
  read / write / edit

shell tools
  exec / process / apply_patch

channel tools
  channel-defined agent tools

OpenClaw product tools
  message / sessions_* / subagents / cron / gateway / web_fetch / web_search
  media tools / nodes / goals / update_plan / transcripts / skill_workshop

plugin tools

Tool Search controls
  tool_search / tool_describe / tool_call / tool_search_code
```

## policy pipeline：工具进场前过多层门禁

OpenClaw 工具装完后，还会经过多层 policy 过滤。入口在 [agent-tools.ts](../../../submodules/openclaw/src/agents/agent-tools.ts) 和 [tool-policy-pipeline.ts](../../../submodules/openclaw/src/agents/tool-policy-pipeline.ts)。

典型层级：

```text
tools.profile
tools.byProvider.profile
tools.allow
tools.byProvider.allow
agents.<id>.tools.allow
agents.<id>.tools.byProvider.allow
group tools.allow
tools.toolsBySender
sandbox tools.allow
subagent tools.allow
inherited tools
```

这说明 OpenClaw 的工具可见性不是只由一个 `allowedTools` 决定，而是多层产品上下文共同决定：

```text
profile / provider / agent / group / sender / sandbox / subagent / inheritance
```

## before_tool_call runtime：工具把手上的安全锁

OpenClaw 在工具执行前不仅有 agent-core 的 `beforeToolCall`，还有产品层 [agent-tools.before-tool-call.ts](../../../submodules/openclaw/src/agents/agent-tools.before-tool-call.ts)。

文件头说明它会运行：

```text
plugin hooks
trusted tool policies
approvals
diagnostics
loop detection
skill-use telemetry
adjusted parameter tracking
```

这比简单 hook 更重。

比喻：

```text
工具车准备好了，但每个工具把手上都套了一把安全锁。
真正使用前，安全员会检查插件策略、审批、循环风险、诊断记录和参数调整。
```

对应实现上，OpenClaw 会把工具包一层 wrapper：

```text
wrapToolWithBeforeToolCallHook
rewrapToolWithBeforeToolCallHook
```

见 [agent-tools.ts](../../../submodules/openclaw/src/agents/agent-tools.ts)。这和 Claw-Code 在 `run_turn` 中显式调用 `PreToolUse hook` 不同：

| Claw-Code | OpenClaw |
|---|---|
| loop 内显式调用 hook | 工具对象被 wrapper 包裹 |
| hook 是 `run_turn` 中的一步 | hook/policy 成为工具 execute 的装饰层 |
| 主线线性 | 更 composable / 产品化 |

## Tool Search：大工具目录服务

OpenClaw 的 [tool-search.ts](../../../submodules/openclaw/src/agents/tool-search.ts) 比 Claw-Code ToolSearch 更重。

它提供：

```text
tool_search
tool_describe
tool_call
tool_search_code
```

并且管理多类 catalog source：

```text
openclaw
mcp
client
```

可以这样理解：

> **Claw-Code 的 ToolSearch 像工具箱旁边的一本目录；OpenClaw 的 Tool Search 更像工具目录服务：可以搜索、查看 schema、代为调用，甚至用 code-mode 在受控环境里探索目录。**

横向对比：

| 维度 | Claw-Code ToolSearch | OpenClaw Tool Search |
|---|---|---|
| 形态 | 单个目录检索工具 | search / describe / call / code-mode 控制工具 |
| 搜索对象 | deferred built-in tools | OpenClaw / MCP / client 大 catalog |
| 执行能力 | 主要返回工具名 | 可通过 `tool_call` 调用 cataloged tools |
| 复杂度 | 关键词打分 | 目录压缩、schema 描述、受控 code-mode、工具桥接 |
| 目标 | 减少默认工具表 | 管理大规模工具库存和不同来源工具 |

## 和 Claw-Code 的核心差异

| 维度 | Claw-Code | OpenClaw |
|---|---|---|
| 工具抽象 | `ToolSpec` + `ToolExecutor` | `AgentTool` + `AgentToolResult` |
| 工具定义位置 | Rust tools crate 中心化 | 多个 TS tool factory + assembly pipeline |
| 工具装配 | `GlobalToolRegistry` builtin/plugin/runtime | `createOpenClawCodingTools` 按 run/session/channel/model/sandbox/policy 动态组装 |
| 工具执行 | `run_turn` 逐个执行 `ToolUse` | `agent-loop.ts` 支持 sequential / parallel batch |
| 工具结果 | 字符串输出转 `ToolResult` | `AgentToolResult` 含 content/details/progress/terminate |
| hook | `PreToolUse` / `PostToolUse` 外部命令 hook | `beforeToolCall` / `afterToolCall` + 产品层 before_tool_call policy runtime |
| 权限 / policy | PermissionPolicy + PermissionEnforcer 两道门 | tool policy pipeline + before_tool_call policies / approvals / loop detection |
| ToolSearch | 轻量目录检索器 | 大 catalog search/describe/call/code-mode |
| 架构风格 | 集中式工具中枢 | 工具装配工厂 + 策略管线 + hook wrapper + 事件执行流 |
| 适合场景 | 本地 CLI coding agent | 多端 session runtime / 产品化 Agent 控制面 |

一句话：

> **Claw-Code 的工具系统像“本地万能工具箱”；OpenClaw 的工具系统像“多端 Agent 产品里的工具调度与治理平台”。**

## QA / 讨论记录

### Q: OpenClaw 为什么要把工具执行生命周期拆成这么多事件？

> **状态**: draft
> **来源**: discussion / source-code

A: 因为 OpenClaw 是多端 Agent 产品 runtime，不只是本地 CLI。工具执行过程要服务 Web UI、IM channel、session persistence、diagnostics、approval、progress display 和 audit。因此它需要 `tool_execution_start/update/end` 表示执行生命周期，也需要 `message_start/message_end` 表示工具结果消息进入 transcript。

### Q: `tool_execution_start` 是否表示工具已经真正执行？

> **状态**: draft
> **来源**: discussion / source-code

A: 不一定。它更像“工单开始被处理”。之后还要经过工具解析、deferred hydration、参数准备、schema 校验、beforeToolCall、approval 和 abort 检查。如果这些阶段失败，会生成 immediate error result，并在 `tool_execution_end` 里标记 `executionStarted: false`。

### Q: OpenClaw 如何决定 sequential / parallel？

> **状态**: draft
> **来源**: discussion / source-code

A: 如果全局 `config.toolExecution === "sequential"`，整批串行；否则先预扫描这批 tool calls，解析真实工具对象，如果任意工具 `executionMode === "sequential"`，整批串行；否则整批并发。这是一种“默认并行，但遇到任何串行约束就保守降级”的策略。

### Q: OpenClaw 和 Claw-Code 在多工具调用执行上最大差异是什么？

> **状态**: draft
> **来源**: discussion / source-code

A: Claw-Code 在 `run_turn` 中用 for loop 逐个处理 `ToolUse`，已读代码中没有 batch-level parallel 策略；OpenClaw 则把一轮 assistant message 中的多个 tool calls 当成 batch，根据全局配置和工具级 `executionMode` 选择 sequential 或 parallel，并用事件流记录 start / update / end / result message。
