# OpenHands Multi-Agent：`TaskToolSet`、`AgentDefinition` 与平台化 Sub-Agent

> **日期**: 2026-07-08 | **状态**: draft | **涉及版本**: `openhands 1869baf49914309f2115cd8f75d5c7a57a92b371` / `software-agent-sdk ebdb4566aca5a9834578ff8067a7aa6d26730cc4`

## 相关文档

- OpenHands 项目入口：[README.md](README.md)
- Agent Loop：[agent-loop.md](agent-loop.md)
- Tool System：[tool-system.md](tool-system.md)
- Context Management：[context-management.md](context-management.md)
- Permission / Security：[permission-security.md](permission-security.md)
- Sandbox / Workspace：[sandbox-workspace.md](sandbox-workspace.md)
- 横向 Multi-Agent 总结：[../../comparison/multi-agent.md](../../comparison/multi-agent.md)

## 源码入口

| 模块 | 源码 | 作用 |
|---|---|---|
| App Server conversation build | [live_status_app_conversation_service.py](../../../submodules/openhands/openhands/app_server/app_conversation/live_status_app_conversation_service.py) | 控制面创建 conversation request 时，根据 `enable_sub_agents` 注册 built-in agents、启用 TaskToolSet、传递 `agent_definitions`。 |
| User agent settings | [model.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/settings/model.py) | SDK settings 中的 `enable_sub_agents`、`agent_definitions`、默认工具推导。 |
| Default tools | [defaults.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/tool/defaults.py) | `default_tool_specs(enable_sub_agents=...)` 决定是否加入 sub-agent delegation 工具名。 |
| Tool preset | [default.py](../../../submodules/software-agent-sdk/openhands-tools/openhands/tools/preset/default.py) | `get_default_tools(...)` / `register_builtins_agents(...)`，注册内置 sub-agent 并按开关加入 `TaskToolSet`。 |
| TaskToolSet | [definition.py](../../../submodules/software-agent-sdk/openhands-tools/openhands/tools/task/definition.py) | sub-agent delegation 工具定义：声明 action / observation schema、暴露可用 subagent 类型、接入 TaskManager-backed executor。 |
| Subagent registry | [registry.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/subagent/registry.py) | 注册 / 查询 `AgentDefinition`，从 definition 创建 agent factory。 |
| AgentDefinition schema | [schema.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/subagent/schema.py) | sub-agent 定义模型：name、description、system_prompt、tools、model、MCP config、metadata、level 等。 |
| Conversation request | [request.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/conversation/request.py) | `agent_definitions` 作为 conversation request 的一部分传入执行面。 |
| Agent Server sub-agents API | [sub_agents_router.py](../../../submodules/software-agent-sdk/openhands-agent-server/openhands/agent_server/sub_agents_router.py) | Agent Server 暴露 sub-agent definition 查询接口。 |
| Agent delegation example | [25_agent_delegation.py](../../../submodules/software-agent-sdk/examples/01_standalone_sdk/25_agent_delegation.py) | standalone SDK 中 main agent 使用 `TaskToolSet` 委派给 sub-agent 的示例。 |
| TaskToolSet example | [41_task_tool_set.py](../../../submodules/software-agent-sdk/examples/01_standalone_sdk/41_task_tool_set.py) | `TaskToolSet` 基础使用示例。 |
| File-based subagents example | [42_file_based_subagents.py](../../../submodules/software-agent-sdk/examples/01_standalone_sdk/42_file_based_subagents.py) | 用 Markdown / `AgentDefinition` 定义自定义 sub-agent 的示例。 |
| Frontend subagent card | [subagent-observation-content.tsx](../../../submodules/openhands/frontend/src/components/v1/chat/subagent/subagent-observation-content.tsx) | 前端展示 sub-agent task / observation 的卡片。 |
| Frontend action / observation types | [action.ts](../../../submodules/openhands/frontend/src/types/v1/core/base/action.ts)、[observation.ts](../../../submodules/openhands/frontend/src/types/v1/core/base/observation.ts) | sub-agent action / observation 的前端类型定义。 |

## 核心结论

OpenHands 的多 Agent / 子 Agent 结构，是典型的平台化做法：控制面通过用户设置决定是否启用 sub-agents，执行面 SDK 用 `AgentDefinition` 注册专业子 agent，再由主 agent 通过 `TaskToolSet` 发起委派，结果以 TaskObservation / event stream / UI card 的形式回流。

```text
OpenHands App Server
  -> user.agent_settings.enable_sub_agents
      -> register_builtins_agents(enable_browser=True)
      -> get_default_tools(enable_sub_agents=True) includes TaskToolSet
      -> agent_definitions = get_registered_agent_definitions()
      -> Conversation request
          -> SDK / Agent Server
              -> TaskToolSet
                  -> selected AgentDefinition / sub-agent executor
                      -> TaskObservation / event stream / frontend sub-agent card
```

通俗比喻：

> **OpenHands 像一个远程开发平台。用户打开“允许 sub-agents”后，平台把可用专业工种注册进任务系统；主 agent 遇到适合外包的活，就通过 `TaskToolSet` 派给某个注册 sub-agent，最后 UI 把它显示成 sub-agent task card。**

**精髓标记：OpenHands 的 multi-agent 是“平台注册制”。** 子 agent 不是随手 spawn 的匿名分身，而是被注册、被配置、被传入 conversation request、被 TaskToolSet 调用、被 UI 事件展示的专业工种。

## 一、为什么 OpenHands 的 multi-agent 要分控制面和执行面？

OpenHands 本身不是单仓库单进程 CLI，而是平台化 SWE Agent Harness。它需要同时处理：

- App Server / Agent Canvas / 用户设置
- Sandbox / RemoteWorkspace / LocalWorkspace
- Agent Server / SDK Conversation
- frontend event stream / UI 展示
- built-in / project / user / plugin sub-agents

因此它的 multi-agent 不是一个本地 `delegate_task.py` 文件能讲完的。它天然分成两层：

```text
控制面：决定是否启用、传哪些 definitions、如何展示
执行面：TaskToolSet 如何调用对应 AgentDefinition
```

这也是 OpenHands 和 Hermes 的核心差异：Hermes 是个人助理工具化分身；OpenHands 是平台注册和远程执行。

## 二、控制面：`enable_sub_agents` 决定是否打开派工能力

在 [live_status_app_conversation_service.py](../../../submodules/openhands/openhands/app_server/app_conversation/live_status_app_conversation_service.py) 中，App Server 创建 conversation request 时会读取用户设置：

```text
user.agent_settings.enable_sub_agents
```

当它为 true 时，控制面会：

```text
register_builtins_agents(enable_browser=True)
get_default_tools(enable_sub_agents=True)
agent_definitions = get_registered_agent_definitions()
```

这说明 OpenHands 把 sub-agent 作为用户 / profile 可配置的平台能力，而不是默认永远打开。

**精髓标记：OpenHands 的 sub-agent 首先是平台能力开关，其次才是 agent tool。**

## 三、执行面：`AgentDefinition` 是专业工种说明书

OpenHands SDK 的 sub-agent 由 `AgentDefinition` 描述。它可以来自：

```text
builtin
project
user
plugin
programmatic
```

`AgentDefinition` 可以携带：

- `name`
- `description`
- `system_prompt`
- `tools`
- `model`
- `mcp_config`
- `when_to_use_examples`
- `metadata`
- `level`

这让 OpenHands 的子 agent 更像平台里的“专业工种”：

```text
grammar-checker
browser-capable researcher
general-purpose subagent
plugin-provided worker
project-defined maintainer agent
```

它们不是匿名一次性 child，而是可声明、可发现、可复用、可由插件 / 项目扩展的 agent definition。

## 四、`TaskToolSet`：OpenHands 的派工窗口

[definition.py](../../../submodules/software-agent-sdk/openhands-tools/openhands/tools/task/definition.py) 里的 `TaskToolSet` 是主 agent 调用 sub-agent 的工具入口。

它和 DeerFlow 的 `task` tool 在抽象上类似：

```text
main agent
  -> TaskToolSet action
      subagent_type
      query / task
  -> sub-agent execution
  -> TaskObservation
```

但它比单纯工具函数更平台化：

- 它从 registry 中知道有哪些 registered agent definitions。
- 它把 subagent 类型暴露给模型。
- 它接入 TaskManager-backed executor。
- 它产生标准 Action / Observation 事件。
- 它被前端识别为 sub-agent task card。

所以 `TaskToolSet` 是 OpenHands 的“派工窗口”，`AgentDefinition` 是“工种说明书”。

## 五、上下文隔离：AgentDefinition + conversation execution context + workspace

OpenHands 的子 agent 隔离，不只是 message 隔离，也包括平台运行环境隔离。

子 agent 拿到的是：

```text
任务 query
subagent_type
AgentDefinition 中的 system prompt / tools / model / MCP config
conversation request 中的 workspace / settings
Agent Server / SDK runtime 环境
```

这意味着它继承的不是父 agent 的完整历史，而是平台定义的任务、工具和 workspace 上下文。

和 DeerFlow / Hermes 的相似点：

> 都会把子任务放到独立执行上下文里，避免主 agent 被中间工具输出污染。

和 DeerFlow / Hermes 的不同点：

> OpenHands 的隔离天然连着远程开发工位、Agent Server、event log、frontend 展示和用户 profile 设置。

## 六、结果回流：TaskObservation + event stream + UI card

OpenHands 的结果回流比本地 CLI 更产品化：

```text
sub-agent execution
  -> TaskObservation / DelegateObservation
  -> SDK event stream
  -> App Server / websocket
  -> frontend sub-agent task card
  -> main agent 继续消费 observation
```

也就是说，结果有两个读者：

1. **主 agent**：作为 observation，继续推理。
2. **用户 / 前端**：作为 sub-agent task card，看到“正在委托 / 委托结果”。

这解释了为什么 OpenHands 的前端有专门的 subagent observation content 和 action / observation 类型。

## 七、内置、项目、用户、插件：OpenHands 的 sub-agent 扩展面

OpenHands / SDK 不把 sub-agent 固定为几个硬编码角色，而是通过 registry 支持不同来源：

```text
built-in agents
project .openhands agents
user agents
plugin agents
programmatic agents
```

示例文件 [42_file_based_subagents.py](../../../submodules/software-agent-sdk/examples/01_standalone_sdk/42_file_based_subagents.py) 展示了如何通过 `AgentDefinition` 定义 file-based subagent。

这说明 OpenHands 希望 sub-agent 成为平台扩展点：项目可以定义自己的工种，插件可以带来自己的专业 agent，用户也可以配置偏好。

## 八、OpenHands 怎么防止 multi-agent 失控？

OpenHands 的防线分散在平台层，而不是集中在单个 delegation 函数：

1. **`enable_sub_agents`**：用户 / profile 级开关。
2. **default tools gating**：只有启用时才加入 `TaskToolSet`。
3. **AgentDefinition registry**：子 agent 必须先注册 / 定义。
4. **definition-level tools / model / MCP config**：能力边界写在工种说明书里。
5. **conversation request**：控制面只把允许的 `agent_definitions` 传给执行面。
6. **Agent Server lifecycle**：执行面负责 conversation / action / observation 生命周期。
7. **frontend event schema**：UI 明确展示 sub-agent 任务，避免黑箱后台动作。

和 Hermes 不同，OpenHands 没有把所有 depth / blocked tools / spawn_pause 集中写在一个文件里；它更像通过 setting、registry、tool defaults、request schema、event stream 分层治理。

## QA / 讨论记录

### Q: OpenHands 的 sub-agent 和 DeerFlow / Hermes 的 subagent 是同一种机制吗？

> **状态**: draft
> **来源**: source-code / discussion

A: 抽象原理相似，都是主执行体把局部任务交给受控的独立子执行上下文，最后把 observation / summary 回流。但 OpenHands 的承载层不同：它是平台化 SWE Agent Harness，子 agent 先由 `AgentDefinition` 注册，再作为 conversation request 的 `agent_definitions` 传给 SDK / Agent Server，由 `TaskToolSet` 调用，并通过 event stream / frontend card 展示。它更像平台工种注册，而不是本地分身函数。

### Q: 为什么 OpenHands 要把 sub-agent 做成 `AgentDefinition` registry？

> **状态**: draft
> **来源**: source-code / discussion

A: 因为 OpenHands 要支持 built-in、project、user、plugin、programmatic 多来源 agent。如果只做一个硬编码 `delegate_task`，就很难让项目 / 插件 / 用户声明自己的专业工种。`AgentDefinition` 把 name、description、system_prompt、tools、model、MCP config、when-to-use examples 和 metadata 统一成注册对象，使 sub-agent 成为平台扩展面。

## 相关文档

- 横向 Multi-Agent 总结：[../../comparison/multi-agent.md](../../comparison/multi-agent.md)
- 横向 Agent Loop 总结：[../../comparison/agent-loop.md](../../comparison/agent-loop.md)
- 横向 Tool System 总结：[../../comparison/tool-system.md](../../comparison/tool-system.md)
- 横向 Sandbox / Workspace 总结：[../../comparison/sandbox-systems.md](../../comparison/sandbox-systems.md)
