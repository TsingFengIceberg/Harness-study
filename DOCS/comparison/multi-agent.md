# Multi-Agent / Subagent 横向总结：派工、隔离、执行、回报与治理

> **日期**: 2026-07-08 | **状态**: draft | **涉及版本**: DeerFlow `c9fb9768d476e28de0294ac7a23cab9819b93f83` / Claw-Code `4ea31c1bc91c4e9bcbd67d51c550c01e127e6d0d` / OpenClaw `57db713ff73f8bf177feac882c1fa40531eea282` / Hermes Agent `88a58ff1355eabe468b4dcd4e152a596932632e6` / OpenHands `1869baf49914309f2115cd8f75d5c7a57a92b371` + software-agent-sdk `ebdb4566aca5a9834578ff8067a7aa6d26730cc4`

## 相关项目笔记

| 项目 | 项目笔记 | 主题 |
|---|---|---|
| DeerFlow | [../projects/deer-flow/multi-agent.md](../projects/deer-flow/multi-agent.md) | Lead Agent、`task` tool、SubagentExecutor、Delegation Ledger。 |
| Claw-Code | [../projects/claw-code/multi-agent.md](../projects/claw-code/multi-agent.md) | TaskPacket、TaskRegistry、Worker、Team 与 worktree 工程调度。 |
| OpenClaw | [../projects/openclaw/multi-agent.md](../projects/openclaw/multi-agent.md) | ACP 父子 session、lineage metadata、parent-owned-background。 |
| Hermes Agent | [../projects/hermes-agent/multi-agent.md](../projects/hermes-agent/multi-agent.md) | `delegate_task`、child AIAgent、leaf / orchestrator、后台分身。 |
| OpenHands | [../projects/openhands/multi-agent.md](../projects/openhands/multi-agent.md) | `TaskToolSet`、`AgentDefinition` registry、平台化 sub-agent。 |

## 核心结论

五个 Harness 的 multi-agent / subagent 机制，底层原理高度相似：父执行体把一部分任务切成明确 work item，交给一个受控的独立执行上下文运行，子执行体只继承必要任务、工具、权限和 workspace，最后把摘要结果、状态或事件回流给父执行体或平台。

真正的差异不在“有没有多 Agent 思想”，而在 **各项目把这个共同骨架安放在了不同的架构层级里**：

```text
DeerFlow   -> LangGraph runtime / task tool 层
Hermes     -> 长期个人助理 / delegate_task 工具层
OpenHands  -> App Server + SDK / AgentDefinition 平台注册层
OpenClaw   -> ACP session protocol / control plane 层
Claw-Code  -> TaskPacket / Worker / Worktree 本地工程调度层
```

通俗比喻：

> **多 Agent 的共同骨架是一样的：派工、隔离、执行、回报、治理。** 但 DeerFlow 穿的是 LangGraph 工厂制服，Hermes 穿的是私人助理制服，OpenHands 穿的是远程平台制服，OpenClaw 穿的是会话协议制服，Claw-Code 穿的是本地工程施工队制服。

**精髓标记：共性在任务协作模型，差异在承载层。** 承载层不同，multi-agent 就会表现成 tool、executor、session、registry、worker、team、worktree 或 UI event。

## 一、统一抽象：multi-agent 不是“多个模型聊天”

成熟 Harness 里的 multi-agent，不应该被理解成“开几个模型窗口互相聊天”。更准确的抽象是：

```text
Parent / Coordinator
  -> Work Item
      -> Child Execution Context
          -> Child Agent / Worker / Session
              -> Result / Observation / Status
                  -> Parent Aggregation / UI / Registry
```

也可以写成更机制化的七步：

1. 父执行体发现任务太大、太杂、太适合并行或太容易污染主上下文。
2. 父执行体把任务切成一个更小的 work item。
3. runtime / control plane 为 work item 创建独立执行上下文。
4. 子执行上下文拿到有限任务、有限上下文、有限工具、有限权限和有限 workspace。
5. 子执行体独立跑一段 agent loop、worker loop 或 session loop。
6. 子执行体把结果压缩成 summary、observation、event、status 或 task board update。
7. 父执行体、平台或用户界面再综合这些结果，决定下一步。

**精髓标记：子 Agent 的本质不是“多一个模型”，而是把一部分任务从父上下文中切出去，放进一个受控的独立执行上下文里跑，最后只把压缩后的结果拿回来。**

## 二、五个 Harness 如何映射到统一模型

| 抽象节点 | DeerFlow | Hermes Agent | OpenHands | OpenClaw | Claw-Code |
|---|---|---|---|---|---|
| Parent / Coordinator | Lead Agent | parent AIAgent | main agent / App Server | parent ACP session | CLI / runtime / team |
| Work Item | `task` tool input | `goal` / `tasks` | TaskAction query | child session request | TaskPacket |
| Child Context | subagent state / runtime context | child AIAgent fresh conversation | AgentDefinition + conversation / workspace | child ACP session | worker + worktree + permission profile |
| Child Runner | SubagentExecutor | `_run_single_child` / ThreadPool / background queue | TaskToolSet / Agent Server | ACP runtime session | WorkerRegistry / worker boot |
| Result | tool result + delegation ledger | JSON result / async completion queue | TaskObservation / event stream / UI card | parent notifier / protocol event | task status / lane board / team summary |
| Guardrail | subagent 不拿 `task`；SubagentLimitMiddleware | blocked tools、leaf / orchestrator、depth、concurrency、timeout | `enable_sub_agents`、registry、tool defaults、request schema | parent-owned-background、spawnDepth、role、control scope | worktree、permission、trust / tool permission、acceptance tests |

这张表是本专题最重要的横向框架。它说明：

> 只问“有没有 subagent tool”是不够的。更应该问：这个项目把任务切分、上下文隔离、权限继承、结果回流和生命周期治理放在架构的哪一层？

## 三、五类 multi-agent 形态

### 3.1 DeerFlow：工作流工厂的动态派工

DeerFlow 的形态是：

```text
Lead Agent
  -> task tool
      -> SubagentExecutor
          -> independent LangGraph subagent run
              -> ToolMessage result
              -> Delegation Ledger
```

它的核心不是固定 `planner -> researcher -> coder -> reporter` 节点图，而是 Lead Agent 根据任务现场动态决定是否派工。

比喻：

> **DeerFlow 像工作流工厂。Lead Agent 是总工，`task` tool 是派工窗口，SubagentExecutor 是后台工位调度器，subagent 是临时外包小组。**

关键设计：

- 子 agent 不继承父 messages，只拿任务目标、runtime context、sandbox / thread / user / trace 等必要环境。
- 子 agent 默认不拿 `task` tool，避免无限递归。
- `SubagentLimitMiddleware` 截断单次模型响应中过量的 task calls。
- Delegation Ledger 把派工历史写入 durable context，后续模型调用能知道“哪些活已经派过”。

### 3.2 Hermes Agent：私人助理的分身术

Hermes 的形态是：

```text
Parent AIAgent
  -> delegate_task
      -> child AIAgent
          -> fresh conversation
          -> restricted toolsets
          -> own terminal / task id
      -> sync result / batch result / background completion
```

比喻：

> **Hermes 像私人助理召唤分身。主助理可以同步、批量或后台地召唤 child AIAgent；child 默认是 leaf 工人，不能再召唤分身，除非显式授权为 orchestrator。**

关键设计：

- `DELEGATE_BLOCKED_TOOLS` 默认移除 `delegate_task`、`clarify`、`memory`、`send_message`、`execute_code`、`cronjob` 等高影响工具。
- `role="leaf"` 是默认，`role="orchestrator"` 才能继续派工。
- `max_spawn_depth`、`max_concurrent_children`、timeout、spawn pause 和 active registry 控制 runaway tree。
- `background=true` 允许子 agent 后台运行，完成后通过 async completion queue 回到主会话。

### 3.3 OpenHands：远程平台里的专业工种注册

OpenHands 的形态是：

```text
App Server
  -> enable_sub_agents
      -> register AgentDefinition
      -> include TaskToolSet
      -> conversation request carries agent_definitions
          -> SDK / Agent Server
              -> TaskToolSet executes selected sub-agent
              -> TaskObservation / event stream / frontend card
```

比喻：

> **OpenHands 像远程开发平台。用户打开 sub-agents 开关后，平台把专业工种注册进系统；主 agent 通过 `TaskToolSet` 派工，执行面跑 sub-agent，前端显示 sub-agent task card。**

关键设计：

- `enable_sub_agents` 是 profile / setting 级开关。
- `AgentDefinition` 描述子 agent 的 name、description、system prompt、tools、model、MCP config、when-to-use examples 等。
- sub-agent 来源可以是 builtin、project、user、plugin、programmatic。
- 结果既是主 agent 可消费的 observation，也是用户可见的 UI event。

### 3.4 OpenClaw：ACP 父子会话家谱

OpenClaw 的形态是：

```text
Parent ACP Session
  -> Child ACP Session
      -> parentSessionKey / spawnedBy
      -> spawnDepth
      -> subagentRole / subagentControlScope
      -> interaction mode = parent-owned-background
      -> child events routed through parent-facing presentation
```

比喻：

> **OpenClaw 像多会话工作室总控台。主 session 是老板办公室，子 session 是后台工作间；后台工作间能干活，但不能直接对客户说话，要通过父 session 汇报。**

关键设计：

- `session-lineage-meta.ts` 把 session row 转成 parentSessionId、spawnedBy、spawnDepth、subagentRole 等 metadata。
- `session-interaction-mode.ts` 把带父关系的 ACP session 判为 `parent-owned-background`。
- 子 session 的结果通过 control plane / translator / presentation 归属回父 session。
- role / control scope 语义在 protocol 层保留，可跨 runtime / channel / UI 使用。

### 3.5 Claw-Code：本地施工队任务看板

Claw-Code 的形态是：

```text
TaskPacket
  -> TaskRegistry
      -> WorkerRegistry / worker boot
          -> worktree / permission / tests / acceptance
              -> task status / lane board / team summary
```

比喻：

> **Claw-Code 像本地施工队任务看板。任务先变成标准施工单 TaskPacket，再交给 worker 工位；多个任务可以被 Team 组织，执行进度通过 registry、heartbeat、lane board 和 worker 状态机回流。**

关键设计：

- `TaskPacket` 是任务边界：objective、scope、worktree、repo、branch policy、acceptance、tests、resources、model、permission、commit、reporting、recovery。
- `WorkerStatus` 包含 spawning、trust required、tool permission required、ready、running、finished / failed 等工位生命周期。
- 上下文隔离更偏 worktree / permission / scope，而不是只讲 message 隔离。
- 结果不一定马上回到父模型上下文，而是进入 TaskRegistry / TeamRegistry / lane board。

## 四、统一设计原则：五个 Harness 都绕不开的 8 个问题

下面是本专题最重要的抽象原则。后续无论继续研究哪个 Harness，都可以用这 8 个问题检查它的 multi-agent 设计是否完整。

### 原则 1：先定义任务边界，再创建子执行体

子 Agent 不是凭空出现的。成熟 Harness 都会先把任务缩成一个可交付的 work item：

```text
DeerFlow: task description / subagent_type
Hermes: goal / context / tasks[]
OpenHands: TaskAction query / subagent_type
OpenClaw: child session request / session metadata
Claw-Code: TaskPacket
```

任务边界越清楚，子 agent 越不容易乱跑。Claw-Code 的 TaskPacket 是这个原则最工程化的版本；Hermes / DeerFlow 则是更轻量的工具参数版本。

**设计原则：不要把完整父上下文扔给子 agent，让它自己猜任务；应该把目标、范围、可用资源、验收标准和限制条件压缩成明确 work item。**

### 原则 2：子 Agent 必须是受控的独立执行上下文

五个 Harness 都在避免“子 agent 只是父 agent 的内联延伸”。它们都会制造某种独立上下文：

```text
DeerFlow: independent LangGraph subagent run
Hermes: fresh child AIAgent conversation
OpenHands: AgentDefinition + conversation execution context
OpenClaw: child ACP session
Claw-Code: worker + worktree + task state
```

独立上下文的价值是：

- 中间工具输出不污染父上下文。
- 子任务失败可以单独记录。
- 子任务权限可以单独收紧。
- 并发执行不会互相踩状态。
- UI / registry 可以单独展示进展。

**设计原则：multi-agent 的核心不是“多模型”，而是“多受控上下文”。**

### 原则 3：继承要最小化，不能把父能力全量下放

子 agent 一般需要继承一些东西：

```text
任务目标
workspace / repo / sandbox 线索
用户 / thread / trace context
必要工具
必要模型 / provider 配置
```

但成熟 Harness 都会刻意不继承某些东西：

```text
完整父 messages
无限工具面
长期记忆写权限
外部消息发送权
无限递归派工权
危险命令自动批准权
```

典型设计：

- DeerFlow subagent 默认不拿 `task` / `ask_clarification` / `present_files` 等工具。
- Hermes child 默认 block `delegate_task`、`clarify`、`memory`、`send_message`、`cronjob`。
- OpenHands 通过 `AgentDefinition` 和 `enable_sub_agents` 控制工具 / agent 可见性。
- OpenClaw 通过 role / control scope / parent-owned-background 控制发言和子控制能力。
- Claw-Code 通过 permission profile、worktree、scope 限制工程行为。

**设计原则：子 agent 的安全边界，主要不是“有没有模型”，而是“它继承了什么、不继承什么”。**

### 原则 4：结果回流要压缩，不要把子过程全塞回父上下文

子 agent 最大价值之一是吸收噪声。如果把它的所有工具输出、试错、日志和中间推理全部塞回父 agent，就失去了隔离意义。

五个项目的回流方式不同：

```text
DeerFlow: final ToolMessage + Delegation Ledger
Hermes: JSON summary result / async completion
OpenHands: TaskObservation + event stream + UI card
OpenClaw: protocol event routed through parent presentation
Claw-Code: task status / messages / lane board / team summary
```

共同原则是：

> 父执行体需要的是可决策的结果，而不是子执行体的全部噪声。

**设计原则：子 agent 回流应该是 summary / observation / status，而不是完整 transcript 倾倒。**

### 原则 5：父子关系要可追踪，否则无法取消、审计和展示

只要支持多 agent，就必须回答：

```text
这个子任务是谁创建的？
属于哪个父任务 / 父 session？
当前第几层？
是否还活着？
怎么取消？
结果应该显示在哪里？
```

不同项目的答案：

- DeerFlow：Delegation Ledger + SubagentExecutor state。
- Hermes：`subagent_id`、`parent_id`、`_active_subagents` registry。
- OpenHands：AgentDefinition + TaskObservation / event stream。
- OpenClaw：`parentSessionKey`、`spawnedBy`、`spawnDepth`、`subagentRole`。
- Claw-Code：task id、team id、worker status、heartbeat。

**设计原则：multi-agent 不能只 spawn，不记账。没有 lineage / registry / ledger / board，就无法治理。**

### 原则 6：必须有递归和并发熔断

多 Agent 最容易失控的地方是：

```text
子 agent 继续生子 agent
模型一次生成太多 task calls
后台任务永不结束
多个 worker 互相踩 workspace
子线程危险命令卡死 UI
```

五个项目各自有不同防线：

| 防线 | 代表 |
|---|---|
| 子 agent 不拿 delegation tool | DeerFlow、Hermes leaf 默认 |
| role / depth | Hermes、OpenClaw |
| concurrent cap | DeerFlow、Hermes |
| timeout / cancel / interrupt | DeerFlow、Hermes、OpenHands、OpenClaw |
| session ownership | OpenClaw |
| registry / settings gate | OpenHands |
| worktree / permission / acceptance | Claw-Code |

**设计原则：只要允许 multi-agent，就必须同时设计“最多几个、最多几层、多久超时、谁能取消、失败怎么记”。**

### 原则 7：结果既可能给父 Agent，也可能给平台 / UI

不同 Harness 对“结果回流给谁”有不同产品取向：

```text
给父 agent 继续推理：DeerFlow、Hermes 同步、OpenHands observation
给平台 / UI 展示：OpenHands、OpenClaw、Claw-Code
两者都给：OpenHands、Hermes background、部分 DeerFlow stream event
```

这会影响设计细节：

- 如果主要给父 agent，需要关心 tool result schema 和上下文压缩。
- 如果主要给 UI / 平台，需要关心 event stream、session lineage、task card、status board。
- 如果两者都给，需要避免重复显示和状态不一致。

**设计原则：multi-agent 的 result 不是单一 return value，而是面向父模型、用户界面和持久状态的多路投影。**

### 原则 8：multi-agent 是整体架构的投影，不是可孤立复制的插件

同样的“派工、隔离、执行、回报、治理”，放在不同架构里，会长成不同形态：

- LangGraph runtime 里长成 `task` tool + SubagentExecutor。
- 个人助理 TUI 里长成 `delegate_task` + child AIAgent + background queue。
- 平台 SDK 里长成 `AgentDefinition` registry + `TaskToolSet`。
- ACP 控制面里长成 parent / child session lineage。
- 本地 coding CLI 里长成 TaskPacket + worker + worktree。

所以设计 multi-agent 时，不能只抄某个项目的表面 API。要先看自己的主架构是什么：

```text
主抽象是 run？session？conversation？task？worker？workspace？event stream？
```

**设计原则：multi-agent 的外形应该服从 Harness 的主抽象。**

## 五、五个 Harness 的相似性与差异性总结

### 5.1 相似性

五个项目本质都在解决同一组问题：

```text
任务如何拆？
子执行上下文如何创建？
继承什么、不继承什么？
工具 / 权限如何收紧？
子任务怎么并发？
结果怎么压缩回流？
父子关系怎么追踪？
失控时怎么停？
```

这就是共同骨架。

### 5.2 差异性

差异来自承载层：

| 项目 | 承载层 | 设计外观 |
|---|---|---|
| DeerFlow | LangGraph / Gateway run runtime | Lead Agent 调 `task`，SubagentExecutor 跑独立 LangGraph subagent。 |
| Hermes Agent | 个人助理工具系统 / TUI | `delegate_task` 创建 child AIAgent，支持批量、后台、interrupt。 |
| OpenHands | 平台控制面 + SDK Agent Server | `AgentDefinition` 注册专业工种，`TaskToolSet` 派工，UI 展示 task card。 |
| OpenClaw | ACP session protocol / control plane | 父子 session lineage，parent-owned-background，事件归属回父 session。 |
| Claw-Code | 本地工程任务 / worker / worktree | TaskPacket 标准施工单，worker boot 状态机，TaskRegistry / TeamRegistry 看板。 |

## 六、课堂版总比喻

| Harness | 比喻 | 精髓 |
|---|---|---|
| DeerFlow | 工作流工厂 | Lead Agent 动态派工，SubagentExecutor 跑独立工位，ledger 留档。 |
| Hermes Agent | 私人助理分身术 | `delegate_task` 召唤 child AIAgent，默认 leaf，显式 orchestrator。 |
| OpenHands | 远程开发平台外包工位 | 注册专业 `AgentDefinition`，主 agent 通过 `TaskToolSet` 派工，前端显示 task card。 |
| OpenClaw | 多会话工作室总控台 | 父 session 拥有后台子 session，lineage 和 interaction mode 控制回流。 |
| Claw-Code | 本地施工队任务看板 | TaskPacket、worker、team、worktree、permission 和验收标准组成协作系统。 |

## 七、QA / 讨论记录

### Q: 五个 Harness 的 multi-agent / subagent 机制是不是本质相似，只是架构外观不同？

> **状态**: draft
> **来源**: discussion / source-code

A: 是。抽象来看，multi-agent / subagent 的共同原理都是：父执行体把一部分任务切成明确 work item，交给一个受控的独立执行上下文运行，并把摘要结果、状态或事件回流给父执行体或平台。差异主要来自各项目的整体架构构型：DeerFlow 把它放在 LangGraph runtime 和 `task` tool；Hermes 把它做成 `delegate_task` 分身工具；OpenHands 把它做成 `AgentDefinition` 注册 + `TaskToolSet` 平台能力；OpenClaw 把它提升为 ACP 父子 session 谱系；Claw-Code 则把它工程化为 `TaskPacket`、worker、team 和 worktree 调度。因此不要只问“有没有 subagent tool”，而要问该项目把任务切分、上下文隔离、权限继承、结果回流和生命周期治理放在架构的哪一层。

### Q: 为什么不能直接照搬某个 Harness 的 subagent API？

> **状态**: draft
> **来源**: discussion / inference

A: 因为 subagent API 是主架构的投影。DeerFlow 的 `task` tool 依赖 LangGraph state / middleware / Gateway run；Hermes 的 `delegate_task` 依赖本地 AIAgent、TUI、active registry 和 approval callback；OpenHands 的 `TaskToolSet` 依赖 SDK registry、Agent Server、conversation request 和 event stream；OpenClaw 的父子 session 依赖 ACP protocol / control plane；Claw-Code 的 TaskPacket / worker 则依赖本地 worktree、permission 和 task board。真正可复用的是“派工、隔离、执行、回报、治理”这些原则，而不是某个项目表面的函数名。

### Q: multi-agent 最容易被忽略的风险是什么？

> **状态**: draft
> **来源**: discussion / source-code

A: 最容易被忽略的是继承边界和回流边界。子 agent 如果全量继承父 messages、工具、长期记忆写权限、外部消息发送权和递归派工权，很容易造成上下文污染、权限扩大、无限递归和不可审计副作用。相反，如果结果回流时把子过程完整 transcript 全塞回父上下文，也会抵消子 agent 的隔离价值。成熟 Harness 通常会同时做两件事：最小化继承，压缩式回流。

## 八、相关文档

- [Agent Loop 横向总结](agent-loop.md)
- [Tool System 横向总结](tool-system.md)
- [Context Management 横向总结](context-management.md)
- [Permission / Security 横向总结](permission-security.md)
- [Sandbox / Workspace 横向总结](sandbox-systems.md)
- [横向 QA](qa.md)
