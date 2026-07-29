# ToolNode 与完整 Agent Tool Loop

> **日期**: 2026-07-29 | **状态**: draft | **涉及版本**: `30c4d58`

## 相关文档与源码

- 前置课程：[Interrupt、Command 与 Human-in-the-loop](interrupt-command-hitl.md)
- StateGraph / Pregel 基础：[StateGraph](state-graph.md) 与 [Pregel runtime](pregel-runtime.md)
- 学习入口：[LangGraph 学习笔记](README.md)
- ToolNode：[tool_node.py](../../../submodules/langgraph/libs/prebuilt/langgraph/prebuilt/tool_node.py)
- 预构建 ReAct Agent：[chat_agent_executor.py](../../../submodules/langgraph/libs/prebuilt/langgraph/prebuilt/chat_agent_executor.py)
- LangChain v1 Agent factory：[factory.py](../../../submodules/langchain/libs/langchain_v1/langchain/agents/factory.py)

## 本课主线

```text
模型产生 Tool Call 意图
→ Runtime 路由到 ToolNode
→ ToolNode 校验并执行真实 Tool
→ ToolMessage 按 ID 回流到 messages State
→ Runtime 再次调度模型
→ 模型继续调用工具或输出最终回答
```

当前进度：

- [x] 模型、ToolNode、Tool、Runtime 与 ToolMessage 的职责边界；
- [x] 标准 `Model → ToolNode → Model` 循环；
- [x] Tool Call / ToolMessage 的 ID 因果配对；
- [x] 工具登记、查找、参数 / 名称错误与执行错误边界；
- [x] 多 Tool Call 并行、State / Store / Runtime 注入和 Command 工具结果；
- [x] 结束条件、Checkpoint / Interrupt 组合与生产安全边界；
- [x] 手写 ToolNode 图与预构建 Agent 的层级关系；
- [ ] LangChain v1 `create_agent` 的实际组图路径与 middleware 链；
- [ ] ToolNode 与 HITL / subgraph 的详细源码 trace；
- [x] streaming 与 tracing 观察面的基础边界（详见 [Streaming 与运行观察层](streaming-observability.md)）。

## 第一小节：Agent Loop 的四个角色

完整 Agent 不是模型单独完成任务。可以把它看成旅行服务公司：

| 角色 | 类比 | 真实职责 |
|---|---|---|
| Model | 前台旅行顾问 | 理解用户需求，决定是否调用哪个工具及其参数。 |
| ToolNode | 后台任务中心 | 接收模型工作单、查找工具、执行、处理结果或错误。 |
| Tool | 航班 / 酒店 / 天气等专业部门 | 执行真实函数、API、数据库或业务动作。 |
| Runtime | 公司总调度系统 | 根据状态和路由决定先调用模型、ToolNode、其他 Node 或结束。 |

模型只能提出“我想调用什么”，不能真的访问 API、数据库或支付系统。ToolNode 不负责判断用户旅行方案，也不应该自行猜测要调用什么；它只执行模型已经提出、且应用已注册允许执行的 Tool Call。Runtime 不理解航班业务，只负责状态合并、任务调度、Checkpoint 等统一运行时工作。

> **本节精髓：模型负责决定，ToolNode 负责可靠执行，Tool 负责真实业务，Runtime 负责循环和状态。**

## 第二小节：一条完整 Tool Loop

用户提出“查询明天北京到上海的航班和酒店”。模型本轮输出一条 `AIMessage`，其中包含两张工作单：

```text
flight_search：北京、上海、明天，ID = call-flight-001
hotel_search：上海、明天，ID = call-hotel-002
```

正常运行路径是：

```text
用户消息进入 State.messages
→ Runtime 调度 Model Node
→ Model 产生含 Tool Calls 的 AIMessage
→ 路由发现存在 Tool Calls
→ Runtime 调度 ToolNode
→ ToolNode 查找并执行 flight_search / hotel_search
→ 写入带相应 ID 的 ToolMessages
→ Runtime 再次调度 Model Node
→ Model 阅读真实工具结果
→ 继续产生 Tool Calls，或给出最终回答
```

如果模型再次产生 Tool Call，循环继续；只有模型本轮不再产生 Tool Call 时，路由才转向 `END`。标准路由函数 `tools_condition()` 正是根据最新 AIMessage 是否含有 `tool_calls` 返回工具节点或结束，见 [tool_node.py:1582](../../../submodules/langgraph/libs/prebuilt/langgraph/prebuilt/tool_node.py#L1582)。

> **本节精髓：Agent 的停止条件通常不是“工具执行过一次”，而是“模型不再提出新的 Tool Call”。**

## 第三小节：消息历史与 ID 配对

标准 Agent 将交互过程持续追加到 `State.messages`：

```text
[用户消息]
→ [用户消息, 含 Tool Call 的 AIMessage]
→ [用户消息, AIMessage, 匹配 ID 的 ToolMessage]
→ [用户消息, AIMessage, ToolMessage, 最终 AIMessage]
```

AIMessage 中每个 Tool Call 的 `id` 是任务单号；对应 ToolMessage 的 `tool_call_id` 是回执单号：

```text
AIMessage.tool_calls[*].id
        =
ToolMessage.tool_call_id
```

模型可以一次请求多个工具，因此没有 ID 就无法可靠判断哪份结果回答哪次请求。消息被追加而非覆盖，是为了保留用户意图、模型决策、调用参数、真实结果和最终回答之间的因果链；`messages` reducer 负责这种安全累积。

> **本节精髓：Tool Call ID 是请求单号，ToolMessage ID 是回执单号；messages State 是模型、运行时和 tracing 共同依赖的因果记录。**

## 第四小节：ToolNode 的输入、查找与执行

正常 Agent 用法中，ToolNode 接收带 `messages` 的 Graph State，从中反向寻找最新一条 AIMessage，再取出该消息的 Tool Calls。它也支持直接 Tool Call 列表等输入形状，便于程序化调用和测试；但这不是普通 Agent Loop 的主要入口。解析逻辑见 [tool_node.py:1224-1266](../../../submodules/langgraph/libs/prebuilt/langgraph/prebuilt/tool_node.py#L1224-L1266)。

每个 ToolNode 都维护一份应用显式传入的工具目录。收到 `flight_search` 后，它按名字查找已登记 Tool；模型提出未登记名称时，ToolNode 返回带相同 `tool_call_id` 的错误 ToolMessage，而不是猜测或执行任意能力。相关校验见 [tool_node.py:1268-1280](../../../submodules/langgraph/libs/prebuilt/langgraph/prebuilt/tool_node.py#L1268-L1280)。

单次 Tool Call 的执行路径会构造请求上下文、调用真实 Tool，并把普通结果转换为 ToolMessage 或保留 Command 型结果，见 [tool_node.py:1014-1070](../../../submodules/langgraph/libs/prebuilt/langgraph/prebuilt/tool_node.py#L1014-L1070)。

```text
模型提出工具名与普通业务参数
→ ToolNode 查找已注册 Tool
→ ToolNode 准备可信运行上下文
→ Tool 执行
→ 正常结果 / 错误 / Command 回到 Runtime
```

## 第五小节：校验、错误与并行

工具调用失败至少有三层：

| 失败类型 | 例子 | 常见处理方向 |
|---|---|---|
| 模型调用错误 | 工具不存在、参数缺失、类型不符 | 返回错误 ToolMessage，让模型修正、询问用户或换工具。 |
| 工具执行错误 | API 超时、数据库不可用 | 依据策略重试、降级、报告失败或中断。 |
| 业务 / 权限错误 | 无退款资格、无权读取账户 | 明确拒绝、进入审批或提示用户，不能盲目重试。 |

`handle_tool_errors` 决定哪些异常被包装为错误 ToolMessage、哪些继续抛出。它是错误表达策略，不是“任何错误都安全重试”的开关。

当多个 Tool Call 真正互不依赖时，ToolNode 可以并行执行，例如查天气、查航班和查酒店。并行只能缩短等待时间，不能解决业务竞争：扣款与退款、更新同一订单、写同一外部资源仍需明确顺序、锁、事务或幂等设计。

> **本节精髓：ToolNode 能校验、并发和表达错误，但不能替业务判断“这次重试会不会重复扣款”。**

## 第六小节：可信运行时注入

有些 Tool 需要的不只是模型填写的普通参数。例如“查询当前订单”还需要可信的当前用户、Graph State、长期 Store、Config 或 Runtime 信息。

这些值不应由模型随意声明。ToolNode 支持向 Tool 注入 State、Store、Runtime 等运行时依赖，使模型只提交“查询哪个订单”之类的业务意图，而身份、权限上下文和存储访问权由应用与 Runtime 提供。ToolNode 的职责说明明确涵盖 state injection、persistent storage 和 control flow，见 [tool_node.py:622-654](../../../submodules/langgraph/libs/prebuilt/langgraph/prebuilt/tool_node.py#L622-L654)。

```text
模型提供：想做什么、普通业务参数
Runtime 提供：当前 State、可信身份、Store、Config
Tool 执行：在真实权限边界内完成操作
```

这避免模型通过参数伪造“我是管理员”或绕过当前线程的业务上下文。

## 第七小节：普通结果、ToolMessage 与 Command

查询型 Tool 通常返回普通数据，例如航班列表。ToolNode 将其包装为带原 Tool Call ID 的 ToolMessage，模型在下一轮读取并解释结果。

更高级的 Tool 可能需要改变 Graph，而不仅是返回查询报告。例如切换当前客户、更新订单状态或把流程转入人工审核。此类 Tool 可以返回 Command，让 Runtime 统一处理 State 更新、动态路由或父图通信。

```text
普通 Tool 结果
→ ToolMessage
→ 回到 Model Node

控制型 Tool 结果
→ Command
→ Runtime 应用 update / goto / parent graph 意图
```

Command 不会让 Tool 绕过 Channel、Reducer、Checkpoint 或 Runtime。若该 Tool Call 还需要让模型继续推理，结果链仍必须满足模型协议中 Tool Call 与 ToolMessage 的配对要求；ToolNode 会校验这类混合输出的有效性。

## 第八小节：Checkpoint、Interrupt 与安全边界

ToolNode 是普通 Graph Node，因此它执行前后的 State、ToolMessages 和后续任务都可以被 Checkpoint 持久化。恢复时，Runtime 依据 thread / checkpoint 重建 Graph 状态，但不会替外部系统保证 exactly once。

高风险 Tool 不应因为模型提出请求就立即执行。典型安全链是：

```text
模型提出 refund Tool Call
→ ToolNode 或前置路由识别为高风险
→ interrupt 生成审批待办
→ 人工批准并 Command(resume=...)
→ 独立退款 Node / Tool 使用业务幂等键执行
```

ToolNode 只是“已登记工具的执行边界”，不是完整安全系统。权限验证、参数约束、敏感信息隔离、沙箱、人工审批、审计日志和外部幂等仍属于 Tool 实现、middleware、业务后端和基础设施的责任。

## 第九小节：手写图、ToolNode 与 `create_agent`

手写 StateGraph 时，开发者显式配置：

```text
Model Node
→ 条件路由：有 Tool Call 则去 ToolNode，否则 END
→ ToolNode
→ 普通 Edge 回到 Model Node
```

优势是可以自由插入 RAG、审批、专用路由、额外 State、子图和非标准错误策略。

LangChain v1 的 `create_agent` 则像标准整车：它把模型、ToolNode、工具路由和常见 Agent Loop 组合为高层 API。当前 ToolNode 的源码说明也建议标准 ReAct 场景使用 `create_agent`，由其在内部使用 ToolNode；需要细粒度控制或非标准架构时再手写 ToolNode 图。完整的 `create_agent` 组图路径和 middleware 还没有在本课展开，将在下一课直接核验。

> **本节精髓：StateGraph 是可自定义底盘，ToolNode 是工具执行总成，`create_agent` 是组装好常见循环的标准整车。**

## 第十小节：生产观察与常见误区

生产中至少要观察模型 Tool Call、Tool 执行开始 / 结束、ToolMessage、State 更新、Checkpoint、错误和重试。用户界面不必展示全部，但 tracing 必须足以回答“模型为什么调用这个工具、使用了什么参数、是否成功、是否重复执行”。

常见误区：

1. 认为模型真的执行工具。实际上模型只产生结构化调用意图。
2. 忽略 Tool Call ID，导致多工具结果无法可靠配对。
3. 在 Node 内直接调用 Tool，绕过 ToolNode、messages、Checkpoint、stream 与 tracing 边界。
4. 认为 ToolNode 的并行能力天然保证业务安全。
5. 认为 ToolNode 已经提供全部权限、审批和幂等控制。
6. 认为执行一次 Tool 后 Agent 必然结束；真正停止条件是模型不再产生 Tool Call。

## QA / 讨论记录

### Q: ToolNode 负责什么，不负责什么？

> **状态**: verified
> **来源**: source-code / discussion

A: ToolNode 解析模型 Tool Calls，在已注册工具中查找目标，处理执行、结果包装、部分错误策略、并行调用和运行时依赖注入，并将 ToolMessage 或 Command 交回 Graph Runtime。它不负责决定是否调用工具，不替代最终自然语言回答，也不自动提供权限、沙箱、审批、外部事务或 exactly-once 保障。

### Q: 为什么 Tool 执行后必须回到模型？

> **状态**: verified
> **来源**: source-code / discussion

A: Tool 通常只产生原始业务数据或动作结果；模型需要读取 ToolMessage，结合用户问题、其他工具结果和对话上下文组织最终回答，或决定下一轮工具调用。因此标准循环是 `Model → ToolNode → Model`，而不是 `Model → ToolNode → 用户`。

### Q: ToolNode 与 Command 如何连接？

> **状态**: verified
> **来源**: source-code / discussion

A: 普通 Tool 结果通常变成 ToolMessage；控制型 Tool 可以返回 Command，让 Runtime 处理 State 更新和调度意图。Command 仍然受 Graph 的 Channel、Reducer、Checkpoint 和 superstep 边界约束，不是 Tool 直接调用下一个 Node。

## 下一课

下一课进入 LangChain v1 `create_agent` 与 middleware：重点学习高层 Agent API 怎样组装模型、ToolNode 和循环，以及 middleware 如何在模型与工具调用前后插入权限、重试、上下文管理和人工审核等治理逻辑。
