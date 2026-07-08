# OpenClaw Multi-Agent：ACP 父子 Session、Lineage 与后台所有权

> **日期**: 2026-07-08 | **状态**: draft | **涉及版本**: `9eeebf7cb13ada247ae94d8e3ab6810dc1b3070a`

## 相关文档

- OpenClaw 项目入口：[README.md](README.md)
- Agent Loop：[agent-loop.md](agent-loop.md)
- Tool System：[tool-system.md](tool-system.md)
- Context Management：[context-management.md](context-management.md)
- Permission / Security：[permission-security.md](permission-security.md)
- Sandbox / Workspace：[sandbox-workspace.md](sandbox-workspace.md)
- 横向 Multi-Agent 总结：[../../comparison/multi-agent.md](../../comparison/multi-agent.md)

## 源码入口

| 模块 | 源码 | 作用 |
|---|---|---|
| Sub-agents 官方文档 | [subagents.md](../../../submodules/openclaw/docs/tools/subagents.md) | 说明 `sessions_spawn`、`sessions_yield`、context mode、completion delivery、thread binding、tool policy 与配置项。 |
| `sessions_spawn` executor | [subagent-spawn.ts](../../../submodules/openclaw/src/agents/subagent-spawn.ts) | 校验 spawn 请求、准备 child session、继承 workspace / tools / delivery context、注册 run、调用 gateway 启动子 session。 |
| Subagent registry | [subagent-registry.ts](../../../submodules/openclaw/src/agents/subagent-registry.ts) | 子 run 的注册、生命周期、delivery retry、steering、orphan recovery、持久化和 cleanup 协调器。 |
| `subagents` tool | [subagents-tool.ts](../../../submodules/openclaw/src/agents/tools/subagents-tool.ts) | 列出当前 requester session 可控制的 active / recent subagent runs。 |
| Subagent control | [subagent-control.ts](../../../submodules/openclaw/src/agents/subagent-control.ts) | 解析 controller session，限制 caller 只能查看 / 控制自己 session tree 下的 subagents。 |
| ACP spawn | [acp-spawn.ts](../../../submodules/openclaw/src/agents/acp-spawn.ts) | ACP runtime 子 session spawn：depth、active children、agentId、thread / mode / streamTo 等约束。 |
| ACP parent stream | [acp-spawn-parent-stream.ts](../../../submodules/openclaw/src/agents/acp-spawn-parent-stream.ts) | ACP child 输出流向 parent session 的桥接逻辑。 |
| ACP session lineage | [session-lineage-meta.ts](../../../submodules/openclaw/packages/acp-core/src/session-lineage-meta.ts) | 把持久化 session row 转成 ACP lineage metadata：parentSessionId、spawnedBy、spawnDepth、subagentRole、subagentControlScope 等。 |
| ACP interaction mode | [session-interaction-mode.ts](../../../submodules/openclaw/packages/acp-core/src/session-interaction-mode.ts) | 判断 ACP session 是直接 interactive，还是 parent-owned-background 后台子 session。 |
| Sessions schema | [sessions.ts](../../../submodules/openclaw/packages/gateway-protocol/src/schema/sessions.ts) | gateway protocol 中 session 创建、父 session、spawn depth、subagent role / control scope 等字段定义。 |
| Subagent system prompt | [subagent-system-prompt.ts](../../../submodules/openclaw/src/agents/subagent-system-prompt.ts) | 子 agent 的系统提示和运行规则入口。 |
| Subagent tests | [subagent-spawn.depth-limits.test.ts](../../../submodules/openclaw/src/agents/subagent-spawn.depth-limits.test.ts)、[subagent-registry.persistence.test.ts](../../../submodules/openclaw/src/agents/subagent-registry.persistence.test.ts) | depth limit、registry persistence 等关键行为测试。 |

## 核心结论

OpenClaw 的多 Agent / 子 Agent 结构，最核心的是 **`sessions_spawn` 驱动的后台子 session + registry / lineage 治理**。普通 native sub-agent 通过 `sessions_spawn` 创建独立 session 并由 registry 跟踪；当 runtime 是 ACP 时，这个结构进一步表现为 ACP 父子 session 谱系。子 Agent 有自己的 key、cwd / workspace、事件流和 runtime，但它不应该直接变成面向用户的主对话，而应该通过父 / requester session 回流和展示。

```text
Requester / Parent Session
  -> sessions_spawn
      -> Child subagent session
          -> subagent-registry run record
          -> optional ACP lineage metadata
              parentSessionKey / spawnedBy / spawnDepth
              subagentRole / subagentControlScope
          -> completion announce / handoff back to requester
```

通俗比喻：

> **OpenClaw 像一个多会话工作室总控台。主 session 是老板办公室，子 agent 是后台工作间。后台工作间可以干活，但不能直接跑到客户面前说话；它要把结果交回老板办公室，由父 session 统一对外表达。**

**精髓标记：OpenClaw 的 multi-agent 是“会话级后台任务治理”，而不是局部工具函数。** `sessions_spawn` 负责创建独立子 session，subagent registry 负责生命周期和回流，ACP lineage 则把外部 ACP harness 的父子关系协议化。

## 一、为什么 OpenClaw 的 multi-agent 要从 session 看？

OpenClaw 的整体构型是 Claude Code-like / 多端 Agent 控制面。它要对接的不只是自己的本地 agent loop，还可能包括 ACP-compatible agent、不同 channel、不同 provider、不同前端展示面。

因此它不能只把子 agent 当成父 agent 上下文里的一次函数调用。它需要回答更平台化的问题：

```text
这个子执行体是不是一个独立 session？
它由哪个父 session 创建？
它是后台工作，还是用户直接交互？
它的输出应该发到哪里？
它能不能继续控制 children？
它的嵌套深度是多少？
它所在 workspace / cwd 是什么？
```

这些问题就是 OpenClaw 把 multi-agent 放到 ACP session lineage 层的原因。

## 二、调度者：ACP control plane / session manager

OpenClaw 的调度者不是固定的 Lead Agent，而是 `sessions_spawn` 工具背后的 session manager / subagent registry / control plane 一类平台层组件。

它负责：

```text
创建 / 管理 child subagent session
注册 subagent run record
记录 requester / controller session
计算 depth / active children
处理 completion announce / delivery retry
在 ACP runtime 下记录 parentSessionKey / spawnedBy / parent-owned-background
```

这和 DeerFlow 的区别很明显：

```text
DeerFlow: Lead Agent 在 LangGraph run 中调用 task tool
OpenClaw: sessions_spawn 在 session / registry / protocol 层管理后台子 session
```

所以 OpenClaw 的 multi-agent 更像“多会话后台任务编排”，不是单一 agent runtime 内部机制。

## 三、`sessions_spawn` 与 registry：先创建后台子 session，再登记 run

[subagent-spawn.ts](../../../submodules/openclaw/src/agents/subagent-spawn.ts) 是 native sub-agent 的创建入口。它会校验 spawn 请求、解析 task / model / cwd / thread / context / cleanup 等参数，准备 child session，继承必要 workspace 和 tool policy，然后把 run 注册进 [subagent-registry.ts](../../../submodules/openclaw/src/agents/subagent-registry.ts)。

registry 负责的不只是“记一下 id”，而是一整套后台任务生命周期：

```text
register run
  -> track active / recent children
  -> delivery retry / announce flow
  -> steering / yield / wake parent
  -> orphan recovery
  -> persistence / cleanup
```

这就是 OpenClaw 的“后台任务登记处”。它回答的是：

```text
这个 child session 是谁请求的？
现在是否 active？
完成结果有没有送回 requester？
失败 / 超时 / orphan 怎么恢复？
用户或父 session 如何列出和控制它？
```

如果 runtime 是 ACP，OpenClaw 还会进一步使用 session lineage metadata 记录父子 session 家谱。

## 四、ACP lineage 与 parent-owned-background：外部 ACP 子 session 的家谱

[session-interaction-mode.ts](../../../submodules/openclaw/packages/acp-core/src/session-interaction-mode.ts) 把 ACP session 分成两类：

```text
interactive
parent-owned-background
```

判断逻辑很有代表性：如果一个 ACP session 有 `spawnedBy` 或 `parentSessionKey`，它就是 parent-owned-background。

这句话背后的产品含义是：

> 子 session 是父 session 委托出来的后台工作。它可以产生事件和结果，但不应该直接抢占用户当前对话；它应该通过父 session 的 task notifier / presentation 回流。

这和普通“多开几个聊天窗口”完全不同。对 ACP runtime，OpenClaw 要在协议层回答：

```text
谁有资格对用户说话？
谁只是后台干活？
后台活完成后通过谁汇报？
```

## 五、上下文隔离：native sub-agent 默认 isolated，必要时 fork

OpenClaw 的隔离单位是 session。官方文档 [subagents.md](../../../submodules/openclaw/docs/tools/subagents.md) 把 context mode 分成：

```text
isolated: 创建干净 child transcript，适合独立调研 / 慢工具 / 清晰任务 brief
fork:    从 requester transcript 分支，适合依赖当前对话细节的任务
```

所以 OpenClaw 不是默认把父会话完整塞给 child。默认 native sub-agent 是 isolated；只有 caller 明确要求 `context: "fork"`，或 thread-bound session 场景需要分支时，才复制当前 transcript。

同时 child session 还可以有自己的 cwd、model、thinking、thread binding、cleanup 策略和 runtime。它的事件和生命周期由 registry 跟踪，完成后再 announce 给 requester。

这和 OpenHands / DeerFlow / Hermes 的相似点是：都在构造一个受控子执行上下文。不同点是 OpenClaw 把这个上下文提升成了 **session + registry run**。

## 六、结果回流：non-blocking spawn + completion announce

OpenClaw 的 `sessions_spawn` 是 non-blocking：工具调用很快返回 accepted / run id，child 在后台跑。完成后，OpenClaw 通过 announce / handoff 把结果送回 requester session。

```text
sessions_spawn accepted
  -> child session runs in background
  -> subagent registry captures completion
  -> announce flow / delivery retry
  -> requester session receives internal completion context
  -> parent / requester agent decides whether user-facing update is needed
```

这和 Hermes 同步模式不一样。Hermes 的 child result 可以直接变成 `delegate_task` 的 JSON tool result；OpenClaw 更强调“后台 child 完成后如何可靠送回 requester，如何避免另开一条可见回复路径，如何让父 / requester agent 综合结果”。

所以 OpenClaw 的 multi-agent 和 UI / protocol / session persistence / delivery retry 联系更紧。

## 七、role、depth 与 control scope：OpenClaw 的递归控制语言

OpenClaw 的递归控制同时体现在 native sub-agent 的 depth / active children 限制，以及 ACP lineage metadata 中的 role / control scope 字段。

```text
subagentRole: orchestrator | leaf
subagentControlScope: children | none
```

这和 Hermes 的 leaf / orchestrator 语义相似，但 OpenClaw 的表达更偏 protocol metadata：

- `leaf`：叶子子 agent，不应继续扩散控制
- `orchestrator`：可以作为更高一层协调者
- `children`：控制范围包含 children
- `none`：没有子控制能力

这种设计让 OpenClaw 可以跨 agent runtime / channel / UI 保留同一套“谁能控制谁”的语义。

## 八、OpenClaw 怎么防止 multi-agent 失控？

OpenClaw 的防线重点在 session 所有权和 protocol 归属：

1. **`sessions_spawn` tool policy**：只有有效工具策略允许时才能派工。
2. **context mode**：native sub-agent 默认 isolated，只有必要时 fork。
3. **max spawn depth / active children**：限制递归层级和当前活跃 child 数量。
4. **subagent registry**：记录 active / recent runs、delivery state、orphan recovery 和 cleanup。
5. **`sessions_yield` / announce flow**：让 completion push 回 requester，避免轮询等待。
6. **`parentSessionKey` / `spawnedBy`**：ACP runtime 下明确子 session 责任归属。
7. **`subagentRole` / `subagentControlScope`**：协议层区分 orchestrator / leaf 和控制范围。
8. **`parent-owned-background`**：ACP 后台子 session 不直接对用户发言。

## QA / 讨论记录

### Q: OpenClaw 的 multi-agent 为什么不像 Hermes 那样集中在一个 `delegate_task` 文件里？

> **状态**: draft
> **来源**: source-code / discussion

A: 因为 OpenClaw 的核心构型是多端 / 多 session 控制面。它要管理的不只是一个父 agent 内部的工具调用，还要管理 child session 的创建、registry、delivery retry、orphan recovery、thread binding、展示归属、取消和控制范围。因此 OpenClaw 把 multi-agent 拆在 `sessions_spawn` executor、subagent registry、tool policy、completion announce、ACP lineage 和 presentation 层，而不是集中写成一个本地 `delegate_task` 函数。

### Q: OpenClaw 的 session lineage 和 DeerFlow 的 delegation ledger 有什么不同？

> **状态**: draft
> **来源**: source-code / discussion

A: 两者都在记录“派工关系”，但层级不同。DeerFlow 的 delegation ledger 是 agent state 里的派工台账，记录 Lead Agent 曾经委托过什么任务、结果如何，方便后续模型调用时注入 durable context。OpenClaw 的 subagent registry 是 session / task 层的运行登记处，记录 child run 是否 active、结果是否 delivery、是否需要 retry / cleanup；ACP lineage 则进一步记录外部 ACP child session 由谁创建、属于谁、嵌套几层、角色和控制范围是什么，方便平台控制面路由、展示和治理后台子 session。

## 相关文档

- 横向 Multi-Agent 总结：[../../comparison/multi-agent.md](../../comparison/multi-agent.md)
- 横向 Agent Loop 总结：[../../comparison/agent-loop.md](../../comparison/agent-loop.md)
- 横向 Tool System 总结：[../../comparison/tool-system.md](../../comparison/tool-system.md)
- 横向 Permission / Security 总结：[../../comparison/permission-security.md](../../comparison/permission-security.md)
