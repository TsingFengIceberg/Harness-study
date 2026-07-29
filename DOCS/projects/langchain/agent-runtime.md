# LangChain v1 Agent Factory 与 Middleware

> **日期**: 2026-07-29 | **状态**: draft | **涉及版本**: `7316020`

## 相关文档与源码

- 前置课程：[Message、Runnable 与 Tool](core-abstractions.md)
- 工具执行层：[LangGraph ToolNode 与完整 Agent Tool Loop](../langgraph/prebuilt-agent-tools.md)
- 状态编排层：[LangGraph StateGraph](../langgraph/state-graph.md)
- Agent factory：[factory.py](../../../submodules/langchain/libs/langchain_v1/langchain/agents/factory.py)
- Middleware 基类与 hooks：[types.py](../../../submodules/langchain/libs/langchain_v1/langchain/agents/middleware/types.py)

## 本课主线

```text
create_agent 如何装配标准 Agent Graph
→ model / tools / prompt / state / context / checkpoint / store 分别属于什么层
→ middleware 在完整 Agent 生命周期的哪些位置介入
→ 普通 hook 与 wrap_*_call 的能力差异
→ middleware 怎样承担权限、重试、成本、上下文和审计治理
```

当前进度：

- [x] `create_agent` 是标准 Agent Graph 装配器，返回 `CompiledStateGraph`；
- [x] `model`、`tools`、`system_prompt`、`state_schema`、`context_schema`、checkpointer、store、interrupt 参数的层级；
- [x] `before_agent`、`before_model`、`after_model`、`after_agent` 生命周期位置；
- [x] `wrap_model_call` 与 `wrap_tool_call` 的拦截、短路、重试和嵌套顺序；
- [x] Tool Error、Tool Retry、Model Retry 与 Model Fallback 的可靠性边界；
- [x] 动态模型 / 动态工具 / 上下文选择；
- [ ] 其他内置 middleware 的具体源码 trace；
- [ ] structured output、middleware 与 ToolNode 的组合边界。

## 第一小节：`create_agent` 不是一次模型调用

`create_agent` 不会创建一个新的模型，也不只是调用一次 Chat Model。它是标准 Agent 流水线的装配器：传入模型、工具、提示、middleware 和持久化配置后，返回可调用、可 streaming、可 checkpoint、可 interrupt 的 `CompiledStateGraph`。

当前函数签名和文档明确说明，它创建“持续调用工具直到满足停止条件”的 Agent Graph，见 [factory.py:808-905](../../../submodules/langchain/libs/langchain_v1/langchain/agents/factory.py#L808-L905)。

可以用汽车制造类比：

```text
StateGraph
= 可以自己设计底盘、路线和工作站的底层装配线

ToolNode
= 已经造好的工具执行总成

create_agent
= 把常见底盘、模型、工具执行总成和循环路线装配成标准整车
```

因此：

```text
create_agent(...)
→ 得到一个 CompiledStateGraph
→ 可 invoke / stream
→ 可配置 checkpointer / store
→ 可使用 interrupt
→ 仍处在 LangGraph Runtime 的状态、任务与恢复边界内
```

如果 `tools` 为空，Agent 只有 Model Node，不形成工具调用循环；提供工具后，才形成 `Model → ToolNode → Model` 的标准 Agent Loop。

> **本节精髓：`create_agent` 是预装常见 Agent Loop 的高层 Graph factory，而不是替代 LangGraph Runtime 的另一套执行器。**

## 第二小节：装配参数分别解决什么问题

可以把 create_agent 想成一家客服公司的开业配置：

| 参数 | 公司类比 | 负责的边界 |
|---|---|---|
| `model` | 负责思考和决策的客服经理 | 产生回答或 Tool Call 意图。 |
| `tools` | 可被派单的业务部门 | 执行查询、计算、外部 API 或业务动作。 |
| `system_prompt` | 客服手册 | 模型调用时置于消息开头的长期规则。 |
| `middleware` | 质检、风控、权限、审计岗 | 在模型 / 工具的关键边界介入。 |
| `state_schema` | 单个案件档案结构 | 当前 Agent Graph 内持续演进的 State。 |
| `context_schema` | 当前班次的可信工作资料 | 本次运行中注入的身份、依赖或配置。 |
| `checkpointer` | 单个客户案件的存档系统 | 同一 thread 的暂停、恢复和历史。 |
| `store` | 跨案件客户档案库 | 跨 thread 的长期数据。 |
| `interrupt_before / after` | 人工确认闸门 | 指定 Node 前后暂停执行。 |

`state_schema`、`context_schema`、checkpointer 与 store 的存在说明，高层 Agent API 并没有把 State、Runtime Context、Checkpoint 和长期 Store 混为同一个“memory”。

## 第三小节：标准 Agent Graph 的位置

create_agent 装配的常见核心结构仍然是：

```text
用户消息
→ Model Node
→ 是否有 Tool Call？
   ├── 有：ToolNode 执行 → ToolMessage 写回 messages → 回到 Model Node
   └── 没有：最终 AIMessage → END
```

ToolNode 如何解析 Tool Call、执行真实 Tool、生成 ToolMessage、处理 Command 和回到模型，见 [ToolNode 与完整 Agent Tool Loop](../langgraph/prebuilt-agent-tools.md)。create_agent 的价值在于，开发者不必为每个标准 Agent 手写上述节点、边和默认连接；需要非标准 RAG、审批、子图或专用状态时，仍可以回到手写 StateGraph。

## 第四小节：Middleware 的生命周期位置

Middleware 不是业务 Tool，也不是模型。它是插在 Agent 关键通道上的可编程治理层。

```text
before_agent
→ before_model
→ wrap_model_call
→ 真实模型调用
→ after_model
→ 有 Tool Call？
   → wrap_tool_call
   → 真实 Tool 执行
   → 回到 before_model
→ after_agent
```

同一请求可能反复循环模型与工具，因此：

| Hook | 触发频率 | 常见职责 |
|---|---|---|
| `before_agent` | 整个 Agent run 一次 | 初始化案件、加载用户资料、记录开始。 |
| `before_model` | 每轮模型调用前 | 裁剪上下文、补充规则、准备状态。 |
| `after_model` | 每轮模型调用后 | 检查输出、记录 Tool Call、准备下一步。 |
| `wrap_model_call` | 每轮真实模型调用外侧 | 修改请求、选择模型、重试、短路。 |
| `wrap_tool_call` | 每次真实工具调用外侧 | 权限检查、审批、重试、审计、参数限制。 |
| `after_agent` | 整个 Agent run 一次 | 结案、统计、清理、保存摘要。 |

基础生命周期 hooks 接收 State 与 Runtime，并可返回 State 更新；相关定义见 [types.py:419-485](../../../submodules/langchain/libs/langchain_v1/langchain/agents/middleware/types.py#L419-L485)。

## 第五小节：普通 hook 与 wrapper 的区别

普通 hook 像流程上的固定检查点：它们适合读取当前 State、准备上下文、检查输出或留下记录。

`wrap_model_call` 和 `wrap_tool_call` 则像真正包住关键调用的闸门。它们收到一个 `handler`，可以：

```text
调用 handler 一次
→ 正常放行

调用 handler 多次
→ 在明确策略下重试

修改 request / response
→ 动态选择模型、压缩上下文或转换结果

完全不调用 handler
→ 拒绝、缓存命中、模拟结果或进入人工审批
```

`wrap_model_call` 的说明明确指出 middleware 可以调用 handler 多次、跳过调用以 short-circuit，或修改请求与响应，见 [types.py:491-580](../../../submodules/langchain/libs/langchain_v1/langchain/agents/middleware/types.py#L491-L580)。`wrap_tool_call` 同样可拦截工具调用，见 [types.py:662-738](../../../submodules/langchain/libs/langchain_v1/langchain/agents/middleware/types.py#L662-L738)。

> **本节精髓：hook 主要在固定时点读写状态；wrapper 直接控制真实模型或工具调用是否发生、怎样发生、是否重试和如何处理结果。**

### 用会议助手区分三者

假设用户说：“帮我约下周三上午十点的产品发布会，并邀请市场、销售和外部合作方。”模型随后提出 `create_calendar_event(...)` Tool Call。这里容易把三个概念混成同一件事，但它们处在不同层次：

| 概念 | 在会议助手中的真实职责 | 是否持有真实调用的放行权 |
|---|---|---|
| middleware | 一整个“会议治理模块”，包含时区、外部参会人、审批、审计和重试规则。 | 取决于模块内部实现。 |
| hook | `before_model` 查询用户时区、工作时间和默认会议时长，并把结果写入 State，供模型规划会议。 | 不直接持有 `handler`。 |
| wrapper | `wrap_tool_call` 包住 `create_calendar_event`：发现有外部参会人或参会人数过多时，先请求确认；确认后才执行真实日历 API。 | 是。 |

对应运行过程为：

```text
before_model hook
→ 读取可信日历偏好，返回 State 更新
→ 模型提出 create_calendar_event Tool Call
→ wrap_tool_call wrapper 检查外部参会人和人数
   ├── 未获确认：不调用 handler，返回“会议未创建”的结果
   └── 已获确认：调用 handler(request)，真实日历 API 创建事件并发送邀请
→ ToolMessage 回流模型
```

同一个 middleware 可以同时实现多个 hook 和 wrapper；它们不是互斥的三种 Agent。真正的分界是：hook 是“流程到固定时点，我补资料或留记录”；wrapper 是“这次真实操作先交给我，我决定是否调用、怎样调用以及失败后怎样处理”。`before_model` 的源码签名只接收 `state` 和 `runtime`，返回可应用的 State 更新；`wrap_model_call` / `wrap_tool_call` 额外接收 `handler`，因此能调用、重复调用或跳过真实操作，见 [types.py:419-570](../../../submodules/langchain/libs/langchain_v1/langchain/agents/middleware/types.py#L419-L570) 与 [types.py:662-738](../../../submodules/langchain/libs/langchain_v1/langchain/agents/middleware/types.py#L662-L738)。

## 第六小节：多个 Middleware 的嵌套

假设配置顺序是：权限 middleware、成本控制 middleware、重试 middleware。它们像连续安检门：

```text
权限岗
  → 成本岗
    → 重试岗
      → 真实模型或真实 Tool
    ← 重试岗处理结果
  ← 成本岗处理结果
← 权限岗处理结果
```

当前 API 约定，middleware 列表中靠前者是外层包装者。顺序会影响谁先拒绝、谁看到原始错误、谁看到已重试的结果，以及成本与审计的统计口径。

例如“每一次真实重试都计费”和“整次逻辑请求只计费一次”需要不同的 middleware 位置。middleware 顺序因此属于行为与治理设计，而不只是代码排版。

## 第七小节：退款场景的完整治理链

```text
客户请求退款
→ before_agent：加载订单、身份和案件档案
→ before_model：补充退款规则与上下文
→ wrap_model_call：按复杂度选择模型，调用模型
→ after_model：发现模型请求 refund_tool
→ wrap_tool_call：检查权限、金额和订单状态
   ├── 高风险：不放行，进入 interrupt 等待人工审批
   └── 正常：使用 refund:订单号 幂等键执行退款
→ ToolNode：写入退款 ToolMessage
→ before_model：将退款结果整理进上下文
→ Model：生成最终答复
→ after_agent：写入审计和结案记录
```

这条链说明 middleware 可以承担权限、成本、重试和审计等治理，但它不替代支付系统的幂等键、数据库事务、审批前端或业务权限数据源。

## 第八小节：动态选择模型、工具与上下文

middleware 不必让同一个模型每轮都看到同一份消息和同一套工具。它可以在每轮模型调用前，依据当前任务生成新的 `ModelRequest`，就像为当班客服经理准备一张本轮工作简报。

ModelRequest 包含本轮模型、消息、system message、可用工具、tool choice、State、Runtime 和模型设置；`override()` 采用创建新请求的方式替换这些字段，而不是原地修改旧请求，见 [types.py:70-220](../../../submodules/langchain/libs/langchain_v1/langchain/agents/middleware/types.py#L70-L220)。

### 动态模型

可以根据任务复杂度、风险、预算或失败情况选择本轮模型：简单订单查询使用快速模型，复杂合同解释或高风险退款使用更强模型，主模型超时时切换备用模型。它改变的是本轮 `ModelRequest.model`，不是重新创建一个 Agent。

### 动态工具

当应用登记数十个工具时，没必要每轮都把所有工具 schema 交给模型。middleware 可以按当前问题只暴露相关工具，例如旅行问题暴露航班、酒店、天气，退款问题暴露订单、规则和审批工具。当前 `LLMToolSelectorMiddleware` 会先筛选与用户问题相关的工具，再交给主模型，以降低 token 消耗和工具选择难度，见 [tool_selection.py:70-145](../../../submodules/langchain/libs/langchain_v1/langchain/agents/middleware/tool_selection.py#L70-L145)。

动态工具选择是效率与准确性策略，不是安全策略。工具即使对模型可见，`wrap_tool_call` 或 Tool 自身仍必须检查用户身份、订单归属、金额和审批要求。

### 动态上下文

完整 `State.messages` 是 Runtime 保存的案件档案；`ModelRequest.messages` 是本轮实际送进模型的精选材料。middleware 可以保留近期对话、压缩早期内容、去除无关工具原始结果，并补充订单摘要、业务规则或审批结论。完整状态不必等于每轮模型上下文。

```text
State
= 完整案件档案

ModelRequest
= 本轮给模型的工作简报

middleware
= 每轮生成和调整工作简报的调度岗
```

> **本节精髓：动态选择在每轮模型调用前换合适的模型、收窄可见工具、整理模型上下文；它服务成本、准确率和 Context Window 管理，但不替代真实工具执行时的权限校验。**

## 第九小节：错误回流、重试与 Fallback

错误回流、重试和 fallback 解决的不是同一个问题：

```text
错误回流
= 把适合公开的失败告诉模型

重试
= 同一个 Tool 或模型在临时故障后再尝试

Fallback
= 主模型持续失败后切换备用模型
```

### 先判断错误类型

| 失败类型 | 例子 | 合理方向 |
|---|---|---|
| 模型调用错误 | 工具不存在、参数缺失、类型不符 | ToolNode 在真实 Tool 前生成错误 ToolMessage，让模型修正或询问用户。 |
| 临时执行错误 | 超时、限流、5xx、连接重置 | 对明确安全的 Tool / 异常做有限退避重试。 |
| 业务或权限错误 | 无退款资格、订单不属于用户、金额超限 | 拒绝、审批或业务处理，通常不重试。 |
| 高风险结果不确定 | 退款是否已提交、库存是否已扣减 | 查外部状态、使用幂等键或交给人工，不能盲目重试。 |

### Tool Error

`ToolErrorMiddleware` 选择性地将 Tool 执行异常转换为 `status="error"` 的 ToolMessage，使模型能够换工具、说明失败或向用户补充提问。开发者必须明确决定哪些异常允许暴露；未处理异常继续传播，避免把内部路径、密钥或堆栈细节泄露给模型或用户。

它只看到真实 Tool 执行异常，不处理参数绑定 / 校验错误；后者已由 ToolNode 在 Tool 运行前处理。`interrupt` 和父图 Command 等控制流信号也必须正常传播，不能被错误 middleware 吞掉。见 [tool_error.py:24-113](../../../submodules/langchain/libs/langchain_v1/langchain/agents/middleware/tool_error.py#L24-L113)。

### Tool Retry

`ToolRetryMiddleware` 适合网络超时、短暂限流、临时 5xx 等基础设施故障。它支持按异常类型筛选、有限重试、指数退避、最大延迟和随机抖动。重试耗尽后可以生成错误 ToolMessage 让模型继续，或重新抛错停止 Agent。见 [tool_retry.py:22-170](../../../submodules/langchain/libs/langchain_v1/langchain/agents/middleware/tool_retry.py#L22-L170)。

查询、搜索和读取类 Tool 往往更适合重试；退款、扣款、发邮件、创建工单等副作用 Tool 必须先有业务幂等键、明确的异常白名单和外部状态确认。不能因为“超时”就假设第一次没有成功。

### Model Retry 与 Model Fallback

Model Retry 是同一个模型在超时或限流后有限重试；Model Fallback 是主模型持续失败后依次改用备用模型。后者还需要考虑不同 provider 的工具调用、结构化输出、上下文长度与专属参数兼容性。当前 `ModelFallbackMiddleware` 会按顺序尝试备用模型，并在跨 provider 时处理某些 provider 专属缓存标记，见 [model_fallback.py:278-403](../../../submodules/langchain/libs/langchain_v1/langchain/agents/middleware/model_fallback.py#L278-L403)。

### Middleware 组合顺序

若目标是“先重试，最终再向模型安全地说明失败”，逻辑层次应是：

```text
ToolErrorMiddleware
  → ToolRetryMiddleware
    → 真实 Tool
```

内层 Retry 重试耗尽后抛出最终异常，外层 Error middleware 决定是否转换成安全的错误 ToolMessage。当前 ToolError middleware 的说明也明确推荐该组合方向。

> **本节精髓：临时技术故障才考虑有限重试；错误 ToolMessage 让模型知道可解释的失败；fallback 用于换模型；权限、业务拒绝和不可逆副作用不能靠自动重试掩盖。**

## QA / 讨论记录

### Q: `create_agent` 与手写 StateGraph 是替代关系吗？

> **状态**: verified
> **来源**: source-code / discussion

A: 不是。create_agent 是返回 CompiledStateGraph 的高层 factory，适合标准模型 - 工具循环；手写 StateGraph 适合需要自定义 State、RAG、审批、子图、非标准路由或特殊恢复策略的场景。二者处于同一个 LangGraph Runtime 体系，只是抽象层不同。

### Q: Middleware 与 ToolNode 的区别是什么？

> **状态**: verified
> **来源**: source-code / discussion

A: ToolNode 负责把模型已提出的 Tool Call 变成真实工具执行和 ToolMessage；middleware 在模型或工具调用的前后插入权限、重试、上下文、成本、审计等治理。ToolNode 是执行总成，middleware 是围绕关键调用的治理层。

### Q: middleware、hook、wrapper 分别是什么关系？

> **状态**: verified
> **来源**: source-code / discussion

A: middleware 是一整个可插拔的治理模块；hook 是它在 `before_model`、`after_model` 等固定生命周期点执行的动作；wrapper 是它在 `wrap_model_call` 或 `wrap_tool_call` 中包住真实调用的接口。hook 可读写 State，但没有直接执行核心调用的 `handler`；wrapper 持有 `handler`，所以可以放行、短路、修改请求或结果、有限重试。一个 middleware 可以同时提供 hook 和 wrapper，不是三选一关系。

### Q: Middleware 能保证高风险 Tool 一定安全么？

> **状态**: verified
> **来源**: source-code / inference

A: 不能单独保证。它能拒绝、修改或暂停调用，但仍需依赖可信身份、业务权限数据、审批系统、Tool 内部校验、外部服务幂等键、事务和审计基础设施共同形成安全边界。

## 下一小节

下一小节讨论 `response_format` 与 structured output：Agent 怎样把最终回答从自然语言变成稳定的结构化业务结果，以及这和 Tool Call 的区别。
