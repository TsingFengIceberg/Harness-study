# DeerFlow 自进化、Skill Evolution 与 Custom Agent 配置

> **日期**: 2026-07-10 | **状态**: draft | **涉及版本**: `c9fb9768d476e28de0294ac7a23cab9819b93f83`

## 相关文档

- 项目入口：[DeerFlow 学习笔记](README.md)
- [Context Management](context-management.md)：长期 memory 如何作为后续模型上下文。
- [Agent Loop](agent-loop.md)：Gateway run、middleware 和 Goal Evaluator 所在的运行时主干。
- [Tool System](tool-system.md)：Skill、MCP 和工具治理。
- [Permission / Security](permission-security.md)：持久化写入、权限与安全边界。
- 横向问题收集：[QA](../../comparison/qa.md)

## 一句话结论

DeerFlow 有“从经验中改善后续行为”的若干机制，但没有完整的自动强化学习闭环。

```text
本次任务内：目标检查 -> 未完成则继续
跨会话：用户偏好 / 显式纠正 -> 持久 memory -> 下次注入上下文
可选能力沉淀：复杂流程 / 已修复的 Skill 缺口 -> Agent 决定调用 skill_manage -> 写入 custom Skill
显式可配置：人通过 config.yaml + SOUL.md 或 HTTP API 定义 Custom Agent
```

因此更准确的说法是：

> **DeerFlow 是“受控的经验沉淀与能力扩展型 Agent”，不是“自动训练、自动改全局策略的强化学习系统”。**

## 一、自进化要先拆成四个层级

“自进化”很容易把不同机制混在一起。DeerFlow 当前的能力可分为四层：

| 层级 | DeerFlow 是否具备 | 改变什么 | 是否自动改变模型权重 / 全局策略 |
|---|---:|---|---:|
| 运行时自纠错 | 是 | 当前 run 是否继续完成目标 | 否 |
| 长期记忆 / 用户纠正 | 是 | 后续对该用户 / Agent 的上下文与行为 | 否 |
| Skill Evolution | 是，默认关闭 | 可复用的 custom Skill | 否 |
| 自动训练 / RL / 自动全局优化 | 未发现完整闭环 | 模型权重、全局 prompt、模型路由、工具策略 | 不适用 |

这四层不能混为一谈：Memory 不是 Skill，Skill 写入不是模型训练，Goal Evaluator 也不是长期学习。

## 二、长期记忆：把用户纠正沉淀为后续上下文

### 2.1 谁触发、谁执行、状态放在哪里

一次 Agent run 完成后，`MemoryMiddleware.after_agent(...)` 会从 state 中筛出用户消息和最终 assistant 回答，识别其中是否有用户纠正或正向确认，然后异步加入记忆更新队列。入口见 [memory_middleware.py:54-121](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/middlewares/memory_middleware.py#L54-L121)。

```text
用户 / Agent 完成一轮对话
  -> MemoryMiddleware 过滤可用 messages
  -> detect_correction / detect_reinforcement
  -> queue.enqueue(...)
  -> MemoryUpdater 使用 LLM 生成结构化 memory 更新
  -> 按 user_id / agent_name 写入 memory.json
  -> 下次 prompt construction 读取并注入相关 memory
```

Memory 更新提示明确要求模型处理“是否出现了 Agent 错误或用户纠正”：如果出现，记录错误根因和正确方法为高置信度 `correction` fact。见 [memory/prompt.py:34-48](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/memory/prompt.py#L34-L48)、[memory/prompt.py:73-87](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/memory/prompt.py#L73-L87)。

**精髓标记：** 这是一种“给特定用户 / Agent 建立经验档案”的机制。它改变后续模型可见的上下文，而不改模型权重。

### 2.2 记忆不是无限累积：有过期复核和保护类别

Memory 不是只加不减。配置允许开启 staleness review：系统挑出足够旧、且不属于受保护类别的 facts，让 MemoryUpdater 判断 KEEP / REMOVE；默认 `correction` 是受保护类别之一。相关配置见 [memory_config.py:101-134](../../../submodules/deer-flow/backend/packages/harness/deerflow/config/memory_config.py#L101-L134)，候选筛选与受限删除见 [updater.py:427-464](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/memory/updater.py#L427-L464)、[updater.py:772-809](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/memory/updater.py#L772-L809)。

这说明 DeerFlow 试图避免“旧偏好或过期事实永远污染 prompt”，但它仍是 memory hygiene，不是对 Agent 策略效果的自动评测。

## 三、Goal Evaluator：当前任务的自我检查，不会沉淀为全局学习

DeerFlow 的 Goal Evaluator 用独立、非 thinking 的评估模型，根据当前可见对话证据判断目标是否完成。见 [goal.py:240-290](../../../submodules/deer-flow/backend/packages/harness/deerflow/runtime/goal.py#L240-L290)。

```text
Agent 给出一个看似完成的回答
  -> Goal Evaluator 判定目标是否满足
  -> goal_not_met_yet
  -> 注入隐藏 continuation message
  -> Agent 继续同一 run
  -> 连续次数上限 + 无进展熔断
```

可继续的 blocker 当前是 `goal_not_met_yet`，见 [goal.py:47-49](../../../submodules/deer-flow/backend/packages/harness/deerflow/runtime/goal.py#L47-L49)。评估结果会写入 goal 的 `last_evaluation`，见 [goal.py:497-525](../../../submodules/deer-flow/backend/packages/harness/deerflow/runtime/goal.py#L497-L525)。

它像“员工交付后由质检员验收；不合格就退回继续做”。但 evaluator 的结论只驱动当前 run 的 continuation；当前未见它把失败原因自动转成新的全局 system prompt、模型选择规则或 Skill。

## 四、Skill Evolution：受控的能力沉淀，而不是自动流程挖掘

### 4.1 开关和工具暴露

Skill Evolution 的配置模型只有两个字段：是否允许 Agent 管理 `skills/custom`，以及可选的安全审核模型。默认关闭。见 [skill_evolution_config.py:3-13](../../../submodules/deer-flow/backend/packages/harness/deerflow/config/skill_evolution_config.py#L3-L13)。

```yaml
skill_evolution:
  enabled: false
  moderation_model_name: null
```

示例配置也明确把它称为“允许 Agent 自主创建和改进 `skills/custom/` 中 Skill”的功能，见 [config.example.yaml:1442-1447](../../../submodules/deer-flow/config.example.yaml#L1442-L1447)。只有开关开启时，`get_available_tools(...)` 才把 `skill_manage` 放进 Agent 工具集合，见 [tools.py:90-96](../../../submodules/deer-flow/backend/packages/harness/deerflow/tools/tools.py#L90-L96)。

### 4.2 Agent 如何“发现一个流程值得复用”

这里必须避免夸大。DeerFlow 当前**没有**一个跨历史任务的 workflow miner；没有看到它自动统计“相同任务出现了几次”、聚类历史 run 或用成功率评估是否应创建 Skill。

实际机制是：启用后，DeerFlow 把一段 **Skill Self-Evolution system prompt** 加给模型，告诉模型在当前任务结束时遇到下列情形要考虑创建 / 更新 Skill：

```text
- 任务用了 5 次以上工具调用
- 克服了不明显的错误或陷阱
- 用户纠正了做法，且修正后的版本有效
- 发现一套不简单、可能反复出现的工作流
- 既有 Skill 没覆盖遇到的问题
```

原始提示见 [lead_agent/prompt.py:227-251](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/prompt.py#L227-L251)。

所以“发现”实际上是：

```text
当前任务的 messages、工具调用和结果
  + system prompt 给出的判断准则
  -> LLM 在当前上下文做语义判断
  -> 决定是否调用 skill_manage
```

它是 **LLM 驱动、提示词约束的机会式沉淀**，不是数据驱动的自动经验挖掘。

例如，用户在当前对话中说“以后每周都要按这个格式处理 GitHub issue 并出周报”，模型可以从“以后每周”判断流程具有重复性；但系统并不是先从历史数据库统计出它重复了 12 次。

### 4.3 写 Skill 时有哪些控制

Agent 不能直接在 workspace / outputs 中随意写 `SKILL.md`。Prompt 要求所有 Skill 操作通过 `skill_manage`，并要求创建新 Skill 前优先向用户确认，见 [lead_agent/prompt.py:239-251](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/prompt.py#L239-L251)。

`skill_manage` 支持：

| 操作 | 含义 |
|---|---|
| `create` | 新建 custom Skill |
| `edit` | 完整改写 `SKILL.md` |
| `patch` | 对已有 `SKILL.md` 进行局部替换 |
| `delete` | 删除 Skill |
| `write_file` | 写配套脚本或资源文件 |
| `remove_file` | 删除配套文件 |

工具主实现见 [skill_manage_tool.py:113-261](../../../submodules/deer-flow/backend/packages/harness/deerflow/tools/skill_manage_tool.py#L113-L261)。写入前会做名称和 Markdown 校验、静态扫描、LLM 安全扫描；写入后记录变更历史，并刷新该用户的 Skill system-prompt cache。

**精髓标记：** Skill Evolution 给 Agent 一支受控的“写操作手册的笔”。它能把经验写成 Skill，但并不意味着系统拥有自动发现、自动验证、自动回滚所有 Skill 的完整进化闭环。

## 五、Custom Agent：既可以对话更新，也可以显式配置

### 5.1 Custom Agent 的基本形态

Custom Agent 的核心是一个用户隔离的目录：

```text
{base_dir}/users/{user_id}/agents/{agent_name}/
├── config.yaml  # 结构化运行配置
└── SOUL.md      # 身份、行为准则、领域规则
```

路径解析和 per-user 优先、legacy shared fallback 的规则见 [agents_config.py:173-200](../../../submodules/deer-flow/backend/packages/harness/deerflow/config/agents_config.py#L173-L200)。`SOUL.md` 会作为自定义 Agent 的人格、价值观和行为护栏读入 system prompt，见 [agents_config.py:252-274](../../../submodules/deer-flow/backend/packages/harness/deerflow/config/agents_config.py#L252-L274)。

`AgentConfig` 目前可定义：

```yaml
name: code-reviewer
description: 专门审查代码质量和回归风险
model: deep
tool_groups:
  - filesystem
  - search
skills:
  - code-review
  - test-planning
```

对应 schema 见 [agents_config.py:125-151](../../../submodules/deer-flow/backend/packages/harness/deerflow/config/agents_config.py#L125-L151)。其中 `skills: null` 表示全部启用 Skill，`skills: []` 表示禁用所有 Skill，显式列表表示白名单。

### 5.2 显式配置方式一：直接维护文件

最适合 GitOps、部署和人工审核的方式，是由 operator 直接创建 / 审查 `config.yaml` 与 `SOUL.md`。这不依赖用户和 Agent 对话，也不需要让 Agent 持有 `update_agent` 工具。

```text
operator 维护 config.yaml + SOUL.md
  -> 下一次创建该 custom Agent 时读取最新文件
  -> Agent 获得确定的身份、默认模型、工具组和 Skill 白名单
```

注意：当前 `AgentConfig` schema 会忽略未知顶层字段；复杂的 GitHub 事件绑定则有专门的 `github:` 字段。见 [agents_config.py:137-170](../../../submodules/deer-flow/backend/packages/harness/deerflow/config/agents_config.py#L137-L170)。

### 5.3 显式配置方式二：Custom Agent Management HTTP API

DeerFlow 还提供显式的 Custom Agent CRUD API；这不是对话接口。路由见 [agents.py:106-188](../../../submodules/deer-flow/backend/app/gateway/routers/agents.py#L106-L188)、[agents.py:191-361](../../../submodules/deer-flow/backend/app/gateway/routers/agents.py#L191-L361)：

```text
GET  /api/agents             列出当前用户的 custom agents
GET  /api/agents/{name}      读取 config 与 SOUL.md
POST /api/agents             创建 custom agent
PUT  /api/agents/{name}      更新 config 和 / 或 SOUL.md
```

创建 / 更新请求可以显式提交 `name`、`description`、`model`、`tool_groups`、`skills`、`soul`。请求 schema 见 [agents.py:22-58](../../../submodules/deer-flow/backend/app/gateway/routers/agents.py#L22-L58)。

该 API 默认关闭，只有在可信、已认证的管理边界下才应显式开启：

```yaml
agents_api:
  enabled: true
```

默认关闭和安全提醒见 [config.example.yaml:1433-1440](../../../submodules/deer-flow/config.example.yaml#L1433-L1440)，路由会在未开启时返回 403，见 [agents.py:81-88](../../../submodules/deer-flow/backend/app/gateway/routers/agents.py#L81-L88)。

### 5.4 对话中的 update_agent 是便利入口，不是唯一入口

`update_agent` 是 Custom Agent 在正常聊天中根据用户明确要求，更新自己的 `SOUL.md`、描述、Skill 白名单、工具组和默认模型的工具。见 [update_agent_tool.py:93-126](../../../submodules/deer-flow/backend/packages/harness/deerflow/tools/builtins/update_agent_tool.py#L93-L126)。

它有重要边界：

```text
- 只能在当前 custom agent 的上下文中使用
- 必须至少传入一个更新字段
- 指定 model 必须存在于 config.yaml 的 models
- 更新限定在当前 user_id 的 Agent 目录
- 新配置从下一次用户 turn 开始生效
- 不可信 webhook channel 禁用，防止外部输入诱导持久化自修改
```

这些约束分别可见 [update_agent_tool.py:135-170](../../../submodules/deer-flow/backend/packages/harness/deerflow/tools/builtins/update_agent_tool.py#L135-L170)、[update_agent_tool.py:282-291](../../../submodules/deer-flow/backend/packages/harness/deerflow/tools/builtins/update_agent_tool.py#L282-L291)。

因此，三种路径的关系是：

| 路径 | 谁发起 | 最适合的用途 |
|---|---|---|
| 直接维护 `config.yaml` + `SOUL.md` | operator / 开发者 | GitOps、部署、代码审查、确定性配置 |
| Custom Agent HTTP API | 管理界面、脚本、管理员 | 产品化的显式 Agent 管理 |
| 对话 `update_agent` | 当前 Custom Agent 按用户明确请求执行 | 快速微调角色、模型或白名单 |

## 六、Feedback API：有评价记录，不等于评价驱动的自动学习

DeerFlow 的 Feedback API 支持为 run 写入 `+1` / `-1` 评分和评论、查询记录和汇总统计。请求模型和 endpoint 见 [feedback.py:27-54](../../../submodules/deer-flow/backend/app/gateway/routers/feedback.py#L27-L54)、[feedback.py:61-164](../../../submodules/deer-flow/backend/app/gateway/routers/feedback.py#L61-L164)。

但在当前已核验的 harness 范围内，尚未看到这些结构化评分被送入：

```text
MemoryUpdater
Skill Evolution
prompt optimizer
model router
自动微调 / RL pipeline
```

应区分两种信号：

```text
用户在自然语言对话中纠正 Agent：
  -> MemoryMiddleware / MemoryUpdater 可识别 correction
  -> 有机会影响后续上下文

用户在 UI/API 点击赞 / 踩：
  -> Feedback 记录与统计
  -> 当前未见自动学习消费者
```

## QA / 讨论记录

### Q: DeerFlow 有真正的自进化吗？

> **状态**: verified
> **来源**: discussion / source-code

A: DeerFlow 有受控的经验沉淀与能力扩展，而不是完整的自动强化学习。当前 run 内，Goal Evaluator 会检查目标是否完成并让 Agent 在满足条件时继续；跨会话，MemoryMiddleware / MemoryUpdater 能把用户偏好和显式纠正写入长期 memory；可选的 Skill Evolution 允许 Agent 通过受控 `skill_manage` 将复杂或已修正的流程沉淀为 custom Skill；Custom Agent 也能由用户或管理员持久化配置。当前未见基于 feedback 自动改全局 prompt、模型路由、工具策略或模型权重的闭环。

### Q: Skill Evolution 如何判断某个流程值得沉淀？

> **状态**: verified
> **来源**: discussion / source-code

A: 当前没有独立的历史任务聚类或 workflow mining 模块。开启 `skill_evolution.enabled` 后，DeerFlow 通过 system prompt 告诉模型在“任务使用 5+ 工具调用、克服非显然错误、用户纠正且修正有效、发现非简单的重复工作流、现有 Skill 有缺口”等情形下考虑创建或更新 Skill。是否沉淀由 LLM 根据当前对话、工具调用和结果做语义判断；创建前 prompt 要求优先确认用户，写入必须经 `skill_manage` 的校验和安全扫描。因此这是提示词约束的机会式能力沉淀，而不是统计驱动的自动经验挖掘。

### Q: Custom Agent 必须通过对话才能被配置或修改吗？

> **状态**: verified
> **来源**: discussion / source-code

A: 不必。Custom Agent 可由用户 / operator 直接维护其 per-user `config.yaml` 和 `SOUL.md`，显式定义身份、行为准则、默认模型、工具组和 Skill 白名单；也可启用 `agents_api.enabled=true` 后，通过 `GET/POST/PUT /api/agents` 管理。对话中的 `update_agent` 只是当前 custom agent 在用户明确要求时使用的便利入口，并非唯一或推荐的生产配置路径。
