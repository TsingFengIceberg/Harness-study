# Hermes Agent Multi-Agent：`delegate_task`、Child AIAgent 与后台分身

> **日期**: 2026-07-08 | **状态**: draft | **涉及版本**: `58e1647b498291bdd28563714513292406d6a876`

## 相关文档

- Hermes Agent 项目入口：[README.md](README.md)
- Agent Loop：[agent-loop.md](agent-loop.md)
- Tool System：[tool-system.md](tool-system.md)
- Context Management：[context-management.md](context-management.md)
- Permission / Security：[permission-security.md](permission-security.md)
- Sandbox / Workspace：[sandbox-workspace.md](sandbox-workspace.md)
- 横向 Multi-Agent 总结：[../../comparison/multi-agent.md](../../comparison/multi-agent.md)

## 源码入口

| 模块 | 源码 | 作用 |
|---|---|---|
| Delegation tool | [delegate_tool.py](../../../submodules/hermes-agent/tools/delegate_tool.py) | `delegate_task` 主实现：创建 child AIAgent、工具隔离、leaf / orchestrator、并行 / 后台执行、结果聚合、active registry。 |
| Agent 初始化 | [agent_init.py](../../../submodules/hermes-agent/agent/agent_init.py) | AIAgent 初始化、共享 iteration budget、interrupt 传播、后台 review 等 agent runtime 状态。 |
| Conversation loop | [conversation_loop.py](../../../submodules/hermes-agent/agent/conversation_loop.py) | 父 / 子 AIAgent 都会运行的主对话循环，负责模型调用、tool_calls、tool result、interrupt / steer。 |
| ACP tool formatting | [tools.py](../../../submodules/hermes-agent/acp_adapter/tools.py) | ACP 侧对 `delegate_task` 结果和 subagent 事件的格式化 / presentation。 |
| Kanban tools | [kanban_tools.py](../../../submodules/hermes-agent/tools/kanban_tools.py) | durable kanban worker / dispatcher 的另一类多 worker 协作入口。 |
| Hermes root guide | [AGENTS.md](../../../submodules/hermes-agent/AGENTS.md) | 官方开发指引中对 Delegation、Kanban、多 agent worker 的概览和配置说明。 |

## 核心结论

Hermes Agent 的多 Agent / 子 Agent 结构，是五个 harness 里最像“私人助理分身术”的一类。父 AIAgent 可以通过 `delegate_task` 工具创建一个或多个 child AIAgent；每个 child 有自己的 fresh conversation、task id、terminal session、受限工具集和专门 system prompt。父 agent 默认只看到 delegation 调用和结果摘要，不接收 child 的完整中间轨迹。

```text
Parent AIAgent
  -> delegate_task
      -> _build_child_agent()
          -> Child AIAgent
              fresh conversation
              restricted toolsets
              own terminal / task id
              leaf or orchestrator role
      -> _run_single_child() / ThreadPool batch / background queue
      -> JSON result or async completion
```

通俗比喻：

> **Hermes 像一个长期私人助理工作台。主助理遇到大任务，可以按下 `delegate_task` 召唤几个分身。分身有自己的便签本、工具箱和终端；默认只是叶子工人，不能再召唤分身，除非被明确授权为 orchestrator 小队长。**

**精髓标记：Hermes 的 multi-agent 是工具化的分身系统。** `delegate_task` 是召唤入口，child AIAgent 是分身，blocked tools 是安全绳，role / depth 是组织层级，background queue 是异步回报通道。

## 一、为什么 Hermes 需要 `delegate_task`？

Hermes 是长期个人 Agent Harness，不只是一次性 coding CLI。它要处理的任务可能很杂：搜索、读文件、改代码、整理记忆、做长期计划、跨入口协作。

如果所有事情都由父 AIAgent 串行完成，会有几个问题：

1. **上下文污染**：子任务产生的大量工具输出会进入主会话。
2. **无法并行**：多个独立探索任务只能排队。
3. **用户体验阻塞**：长任务会卡住主助理。
4. **权限风险**：子任务可能不该拥有记忆写入、发消息、定时任务等高影响能力。
5. **长期状态污染**：临时调研不应随便写入 MEMORY 或 skills。

因此 Hermes 把复杂任务拆给 child AIAgent，让它们在隔离上下文里跑，最后只把摘要结果交回。

## 二、调度者：父 AIAgent 通过 `delegate_task` 派工

Hermes 的调度入口非常明确：[delegate_tool.py](../../../submodules/hermes-agent/tools/delegate_tool.py) 中的 `delegate_task(...)`。

它支持三种使用方式：

```text
单任务：goal + context
批量任务：tasks: [{goal, context, role}, ...]
后台任务：background=true
```

执行流程可以概括为：

```text
delegate_task
  -> 检查 parent_agent
  -> 检查 spawn_pause
  -> 解析 role / background / tasks
  -> 检查 max_spawn_depth
  -> 读取 delegation config
  -> 为每个 task 创建 child AIAgent
  -> 单任务直接跑，多任务并行跑，background 则进入后台完成队列
  -> 聚合结果返回
```

这和 DeerFlow 的 `task` tool 很像，但 Hermes 更偏本地助理 / TUI：它额外关心 subagent id、active registry、interrupt、approval callback、后台完成回流。

## 三、Child AIAgent：不是函数，而是完整子助理

`_build_child_agent()` 会创建真正的 child AIAgent。child 会拿到：

- `goal` / `context`
- focused child system prompt
- `subagent_id`
- `parent_id`
- `depth`
- model / provider / API credentials
- inherited but restricted toolsets
- own task id / terminal context
- progress callback

这说明 Hermes 的子 agent 不是轻量函数，也不是普通 tool call，而是一个完整 agent loop 的执行体。

**精髓标记：child AIAgent 是“独立分身”，不是父 agent 的一段内联推理。**

## 四、上下文隔离：fresh conversation + summary-only 回流

[delegate_tool.py](../../../submodules/hermes-agent/tools/delegate_tool.py) 文件头部已经明确说明每个 child 获得：

```text
fresh conversation
own task_id
restricted toolset
focused system prompt
```

父 agent 的上下文里不会塞入 child 的完整中间轨迹。父 agent 看到的是：

```text
delegate_task 调用
child summary / JSON result
```

这和 DeerFlow 一样，目标是保护主上下文：

> **父助理只读外包报告，不读外包工人的全部草稿、命令输出和试错记录。**

## 五、工具隔离：默认 blocked tools 是安全绳

Hermes 明确规定 child 默认不能访问一些高风险工具。`DELEGATE_BLOCKED_TOOLS` 包括：

- `delegate_task`：默认不允许递归派生
- `clarify`：子 agent 不直接打扰用户
- `memory`：不写共享长期记忆
- `send_message`：不做外部消息副作用
- `execute_code`：避免子 agent 写脚本绕过逐步推理
- `cronjob`：不替父 agent 安排长期任务

这说明 Hermes 的默认 child 是 **leaf worker**：只处理被派发的局部任务，最后返回报告。

这和权限安全专题里的 Hermes 特点一致：长期个人助理最怕污染长期状态、私自发消息、私自安排后续任务，所以子 agent 默认必须收紧工具面。

## 六、leaf 与 orchestrator：默认工人，显式小队长

Hermes 有很清晰的角色模型：

```text
role = leaf
role = orchestrator
```

### leaf

默认角色。特点是：

```text
不能调用 delegate_task
不能继续生孙 agent
适合完成明确小任务
```

### orchestrator

显式授权的小队长。特点是：

```text
保留 delegation toolset
可以继续派生 worker
受 max_spawn_depth 限制
受 orchestrator_enabled 开关限制
```

`_build_child_agent()` 会根据 `delegation.orchestrator_enabled`、`delegation.max_spawn_depth` 和当前 `child_depth` 决定最终 role。即使模型要求 orchestrator，如果深度或开关不允许，也会降级成 leaf。

**精髓标记：Hermes 不是一刀切禁止递归，而是“默认叶子工人，显式授权小队长”。**

## 七、同步、批量、后台：三种派工体验

### 单任务同步

```text
parent AIAgent
  -> delegate_task(goal)
  -> child AIAgent 跑完
  -> JSON result 回到父 agent
```

适合明确小任务。

### 批量并行

```text
delegate_task(tasks=[...])
  -> 每个 task 一个 child
  -> ThreadPool / daemon executor 并行跑
  -> 聚合 results
```

适合多个独立调研 / 文件检查 / 子模块阅读。

### 后台 delegation

```text
delegate_task(background=true)
  -> 立即返回 handle / running 状态
  -> child 在后台跑
  -> 完成后通过 async delegation completion queue 回到主对话
```

这体现 Hermes 的个人助理产品感：用户可以继续和主助理交互，分身完成后再把报告送回来。

## 八、active registry、interrupt 与 spawn pause

Hermes 对运行中 subagent 有模块级 registry：

```text
_active_subagents
  subagent_id -> record
```

它支持：

- `list_active_subagents()`：查看当前分身树
- `interrupt_subagent(subagent_id)`：中断指定 child
- `set_spawn_paused()`：暂停新的 delegation，防 runaway tree

这些机制说明 Hermes 不只是能 spawn child，还能在 TUI / gateway 里观察和干预 child。

## 九、结果回流：tool result 或后台完成队列

Hermes 有两种结果回流：

```text
同步 / 批量：delegate_task 返回 JSON，父 agent 继续推理
后台：completion queue 后续把结果重新注入主会话
```

这和 OpenClaw 的 parent-owned-background 有相似点：都承认子执行体可以后台运行。但 Hermes 更偏工具 / TUI 层，OpenClaw 更偏 ACP session / protocol 层。

## 十、Hermes 怎么防止 multi-agent 失控？

Hermes 的防线很集中也很完整：

1. **blocked tools**：子 agent 默认不能 delegation / clarify / memory / message / cronjob 等。
2. **role**：leaf / orchestrator 明确区分。
3. **max_spawn_depth**：限制嵌套层级。
4. **max_concurrent_children**：限制并行 child 数量。
5. **child_timeout_seconds**：限制子 agent 运行时间。
6. **orchestrator_enabled**：全局控制是否允许小队长。
7. **active registry**：记录活跃 child，支持观察。
8. **interrupt_subagent**：可以中断单个 child。
9. **spawn_pause**：可以冻结新派工。
10. **subagent approval callback**：子线程危险命令默认 auto-deny，避免卡死 TUI stdin。

## QA / 讨论记录

### Q: Hermes 的 `delegate_task` 和 DeerFlow 的 `task` tool 是不是一回事？

> **状态**: draft
> **来源**: source-code / discussion

A: 原理相似，都是父 agent 通过工具把子任务交给独立子执行体，子执行体隔离上下文和工具输出，最后返回摘要结果。但承载层不同：DeerFlow 是 Gateway / LangGraph runtime 里的 Lead Agent + SubagentExecutor；Hermes 是长期个人助理里的 `delegate_task` + child AIAgent，并额外支持 TUI 可观测、后台 delegation、active registry、interrupt、spawn pause、leaf / orchestrator 等本地助理体验。

### Q: Hermes 为什么默认禁止子 agent 再调用 `delegate_task`？

> **状态**: draft
> **来源**: source-code / discussion

A: 因为 delegation 树很容易失控。默认 leaf 子 agent 不能继续派工，可以保证一次派发只产生一层 worker；如果确实需要层级化协作，必须显式设置 `role="orchestrator"`，并受 `delegation.orchestrator_enabled` 与 `delegation.max_spawn_depth` 限制。这个设计相当于“默认工人，显式小队长”。

## 相关文档

- 横向 Multi-Agent 总结：[../../comparison/multi-agent.md](../../comparison/multi-agent.md)
- 横向 Agent Loop 总结：[../../comparison/agent-loop.md](../../comparison/agent-loop.md)
- 横向 Tool System 总结：[../../comparison/tool-system.md](../../comparison/tool-system.md)
- 横向 Permission / Security 总结：[../../comparison/permission-security.md](../../comparison/permission-security.md)
