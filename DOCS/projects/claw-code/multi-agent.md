# Claw-Code Multi-Agent：TaskPacket、Worker 与 Team 调度板

> **日期**: 2026-07-08 | **状态**: draft | **涉及版本**: `4ea31c1bc91c4e9bcbd67d51c550c01e127e6d0d`

## 相关文档

- Claw-Code 项目入口：[README.md](README.md)
- Agent Loop：[agent-loop.md](agent-loop.md)
- Tool System：[tool-system.md](tool-system.md)
- Context Management：[context-management.md](context-management.md)
- Permission / Security：[permission-security.md](permission-security.md)
- Sandbox / Workspace：[sandbox-workspace.md](sandbox-workspace.md)
- 横向 Multi-Agent 总结：[../../comparison/multi-agent.md](../../comparison/multi-agent.md)
- 横向 Agent Loop 总结：[../../comparison/agent-loop.md](../../comparison/agent-loop.md)

## 源码入口

| 模块 | 源码 | 作用 |
|---|---|---|
| TaskPacket | [task_packet.rs](../../../submodules/claw-code/rust/crates/runtime/src/task_packet.rs) | 标准化任务包：目标、scope、worktree、repo、branch policy、验收、测试、资源、模型、权限、提交和恢复策略。 |
| TaskRegistry | [task_registry.rs](../../../submodules/claw-code/rust/crates/runtime/src/task_registry.rs) | 任务生命周期登记处：任务状态、消息、heartbeat、lane board 与 freshness。 |
| TeamRegistry | [team_cron_registry.rs](../../../submodules/claw-code/rust/crates/runtime/src/team_cron_registry.rs) | Team / Cron 维度的任务集合管理，把多个 task id 组织成一个协作单元。 |
| Worker boot | [worker_boot.rs](../../../submodules/claw-code/rust/crates/runtime/src/worker_boot.rs) | Worker 启动与状态机：spawning、trust、tool permission、ready、running、finished / failed。 |
| Analog agents CLI | [agents.rs](../../../submodules/claw-code/rust/crates/claw-analog/src/agents.rs) | `claw-analog agents` 顺序多 agent preset：Audit / Explain / Implement 等角色化执行入口。 |
| Tools snapshot | [tools_snapshot.json](../../../submodules/claw-code/src/reference_data/tools_snapshot.json) | 参考工具快照中保留 `spawnMultiAgent` 等历史 / 镜像工具线索。 |
| Runtime exports | [lib.rs](../../../submodules/claw-code/rust/crates/runtime/src/lib.rs) | runtime 对 task / team / worker 等能力的模块导出入口。 |

## 核心结论

Claw-Code 的多 Agent / 子 Agent 结构，表面上不如 DeerFlow 或 Hermes 那样是一个明显的 `task` / `delegate_task` 工具主线。它更像一个 **本地工程施工队调度系统**：先把任务写成标准施工单，再交给 worker 工位执行，多个任务可以被 Team 组织起来，执行过程由 registry / lane board / worker boot 状态机跟踪。

```text
用户 / CLI / 上层工具
  -> TaskPacket：标准施工单
      -> TaskRegistry：任务登记处 / 看板
          -> WorkerRegistry / worker boot：工位生命周期
              -> worktree / permission / tests / acceptance：施工边界和验收
                  -> task status / messages / heartbeat / team 汇总
```

通俗比喻：

> **Claw-Code 像本地施工队任务看板。多 Agent 不是先表现为“一个模型召唤另一个模型”，而是表现为“把工作标准化成 TaskPacket，分配给有独立工位和权限边界的 worker，再用 Team / Registry 跟踪进度和验收”。**

**精髓标记：Claw-Code 的 multi-agent 重点是任务工程化，而不是聊天分身。** 它把 Agent 协作问题拆成：任务怎么定义、worker 怎么启动、worktree 怎么隔离、权限怎么放行、验收怎么证明、失败怎么记录。

## 一、为什么 Claw-Code 的 multi-agent 看起来“不像 subagent”？

如果只用 DeerFlow 的标准去找，可能会问：Claw-Code 有没有一个 `task` tool？有没有一个 `SubagentExecutor`？有没有子 agent 的 `messages` 隔离？

但 Claw-Code 的设计重心是本地 Coding CLI runtime。它关心的是：

```text
这个工作要改哪个仓库？
能不能开独立 worktree？
允许动哪些路径？
用什么权限 profile？
怎么测试？
完成标准是什么？
worker 启动时是否需要 trust / tool permission？
失败以后状态怎么挂在看板上？
```

所以它把“多 agent”承载在更工程化的对象上，而不是只承载在一个模型工具调用上。

这并不代表它没有多 Agent 思想，而是它的子执行体首先是 **worker / task execution unit**，然后才可能是某个模型会话。

## 二、调度者：不是固定 supervisor，而是 Task / Worker / Team runtime

Claw-Code 的调度者不是一个固定写死的 supervisor agent。它更像几层 runtime 合在一起：

```text
TaskPacket 负责把任务讲清楚
TaskRegistry 负责登记和追踪任务
WorkerRegistry / worker boot 负责工位生命周期
TeamRegistry 负责把多个任务绑成一个协作组
```

这和 DeerFlow 的 Lead Agent 不同。DeerFlow 是模型自己在运行中决定是否调用 `task`；Claw-Code 更强调 **外层任务系统先把任务边界定义清楚**。

### TaskPacket：施工单，而不是一句 prompt

[task_packet.rs](../../../submodules/claw-code/rust/crates/runtime/src/task_packet.rs) 的价值在于：它把一个待执行任务从“自然语言愿望”变成“可交给 worker 的工程对象”。一个 TaskPacket 可以携带：

- `objective`：目标
- `scope`：工作范围，可能是 workspace / module / single file / custom
- `worktree`：是否 / 如何隔离工作树
- `repo`：仓库信息
- `branch_policy`：分支策略
- `acceptance` / `verification_plan`：验收与验证计划
- `resources`：参考资源
- `model` / `provider`：模型选择
- `permission_profile`：权限边界
- `commit_policy`：提交策略
- `reporting`：汇报方式
- `escalation` / `recovery_policy`：升级与恢复策略

这说明 Claw-Code 的 multi-agent 起点不是“开一个聊天窗口”，而是：

> **先把活写成一张能被执行、能被审查、能被验收的任务卡。**

## 三、子执行体：Worker 是带生命周期的工位

[worker_boot.rs](../../../submodules/claw-code/rust/crates/runtime/src/worker_boot.rs) 暴露了 Claw-Code 对 worker 的理解：worker 不是一启动就能干活，而是要经过一串状态。

```text
Spawning
  -> TrustRequired
  -> ToolPermissionRequired
  -> ReadyForPrompt
  -> Running
  -> Finished / Failed
```

这条状态机很有 Claw-Code 气质。它关心的问题不是“模型有没有返回 tool_call”，而是：

```text
worker 进程 / 会话是否生成？
workspace 是否可信？
工具权限是否被批准？
现在能不能接 prompt？
运行中状态如何？
结束是成功还是失败？
```

**精髓标记：Claw-Code 的 worker 是“可审计工位”，不是透明函数调用。** 子执行体必须先通过 trust / permission / readiness 的工程闸门，才能进入真正执行。

## 四、上下文隔离：worktree、scope、permission profile 比 message 隔离更中心

DeerFlow / Hermes 更容易讲 `messages` 隔离：子 agent 不继承父对话，只拿任务目标和必要上下文。

Claw-Code 的隔离更工程化：

```text
TaskPacket.scope 控制任务范围
TaskPacket.worktree 控制文件系统隔离
permission_profile 控制工具权限
branch_policy / commit_policy 控制 Git 行为
acceptance / verification_plan 控制验收方式
```

这相当于给 worker 建一个本地施工围栏：

> **不是把父上下文整包塞给 worker，而是把目标、范围、工位、权限和验收条件压缩成施工单。**

这也解释了为什么 Claw-Code 的 sandbox / workspace、permission / hooks、task / worker 几个专题不能割裂看。它的多 Agent 协作很依赖这些本地工程边界。

## 五、结果回流：不一定回到父模型上下文，而是进入任务看板

DeerFlow / Hermes 同步 delegation 的结果通常会作为 tool result 回到父 agent，让父 agent 继续推理。

Claw-Code 的回流更像看板：

```text
worker 执行
  -> 更新 TaskRegistry 中的 task status
  -> 写入 task messages / heartbeat
  -> lane board 展示任务新鲜度 / 阻塞状态
  -> TeamRegistry 汇总多个 task
```

任务状态包括 created / running / blocked / completed / failed / stopped 等，这更像项目管理系统，而不是单轮 tool result。

这带来一个重要差异：

> Claw-Code 的多 Agent 结果未必立即塞回同一个父模型窗口；它可以成为 runtime / UI / team 层面的状态事实，再由人或后续 agent 消费。

## 六、Team：多个 worker 的协作外壳

[team_cron_registry.rs](../../../submodules/claw-code/rust/crates/runtime/src/team_cron_registry.rs) 中的 TeamRegistry 把多个 task id 组织到一个 team 下。

这相当于：

```text
Team
  ├─ task A
  ├─ task B
  └─ task C
```

Team 不是复杂的 LangGraph 多节点 supervisor，而是更轻量的“任务集合 / 协作单元”。它把多个独立施工单合成一组，方便追踪、展示和管理。

## 七、`claw-analog agents`：角色化多 agent 的另一条线索

[agents.rs](../../../submodules/claw-code/rust/crates/claw-analog/src/agents.rs) 里的 `claw-analog agents` CLI 更接近我们直觉里的“多个 agent preset”：Audit、Explain、Implement 等。

这说明 Claw-Code 也有角色化 agent 编排的表达方式，但它和 runtime 的 TaskPacket / WorkerRegistry 关系更像上层用法和底层设施的关系：

```text
上层：按 Audit / Explain / Implement 等 preset 组织执行
底层：TaskPacket / Registry / Worker boot 提供任务、工位、状态和权限基础设施
```

## 八、Claw-Code 怎么防止 multi-agent 失控？

它的防线不是单一的“不给子 agent task tool”，而是几层工程边界叠加：

1. **TaskPacket scope**：任务范围先被写清楚。
2. **worktree**：子执行体可以被放进独立工作树。
3. **permission_profile**：工具权限随任务携带，而不是默认全开。
4. **worker boot state**：trust / tool permission 未满足前不能进入执行。
5. **TaskRegistry 状态**：blocked / failed / stopped 都可记录，不是静默失控。
6. **acceptance / verification_plan**：完成不是一句“done”，而要有验收标准。
7. **TeamRegistry**：多任务集合可被看板化管理。

## QA / 讨论记录

### Q: Claw-Code 没有像 DeerFlow 那样明显的 `task` tool，是不是 multi-agent 比较弱？

> **状态**: draft
> **来源**: source-code / discussion

A: 不能这样判断。Claw-Code 的 multi-agent 不是首先表现为“模型调用子模型工具”，而是表现为本地工程任务系统：`TaskPacket` 把任务标准化，`TaskRegistry` 追踪生命周期，`WorkerRegistry` 管工位状态，`TeamRegistry` 组织多个任务，worktree / permission / acceptance 提供执行边界。它的强项不是 LangGraph 式子 agent 编排，而是把本地 Coding Agent 的协作变成可审计、可隔离、可验收的施工队模型。

### Q: Claw-Code 的子 agent / worker 和 DeerFlow subagent 的本质差异是什么？

> **状态**: draft
> **来源**: source-code / discussion

A: DeerFlow subagent 更像运行时内部的 LangGraph 子任务执行体，结果以 tool result 回到 Lead Agent；Claw-Code worker 更像拿着 TaskPacket 的本地工程工位，重点在 worktree、权限、验收、worker boot 和任务看板。两者共同点都是“父执行体切分任务，交给受控的独立执行上下文”；差异是 DeerFlow 把这个机制放在 agent runtime / tool 层，Claw-Code 把它放在本地任务 / worker / worktree 调度层。

## 相关文档

- 横向 Multi-Agent 总结：[../../comparison/multi-agent.md](../../comparison/multi-agent.md)
- 横向 Agent Loop 总结：[../../comparison/agent-loop.md](../../comparison/agent-loop.md)
- 横向 Sandbox / Workspace 总结：[../../comparison/sandbox-systems.md](../../comparison/sandbox-systems.md)
- 横向 Permission / Security 总结：[../../comparison/permission-security.md](../../comparison/permission-security.md)
