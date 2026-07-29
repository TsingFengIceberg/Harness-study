# LangGraph Streaming 与运行观察层

> **日期**: 2026-07-29 | **状态**: draft | **涉及版本**: `30c4d58`

## 相关文档与源码

- 前置课程：[ToolNode 与完整 Agent Tool Loop](prebuilt-agent-tools.md)
- Runtime 基础：[Pregel Channel 与任务调度](pregel-runtime.md)
- 人工介入：[Interrupt、Command 与 Human-in-the-loop](interrupt-command-hitl.md)
- 学习入口：[LangGraph 学习笔记](README.md)
- Stream mode 与 `StreamWriter`：[types.py](../../../submodules/langgraph/libs/langgraph/langgraph/types.py)
- Pregel streaming / 输出格式：[main.py](../../../submodules/langgraph/libs/langgraph/langgraph/pregel/main.py)
- Runtime 注入的 stream writer：[runtime.py](../../../submodules/langgraph/libs/langgraph/langgraph/runtime.py)
- Platform SDK 的 server runtime：[runtime.py](../../../submodules/langgraph/libs/sdk-py/langgraph_sdk/runtime.py)

## 本课主线

```text
同一次 Graph Run
→ 模型 token、Node 状态更新、业务进度、Task 生命周期、Checkpoint
→ 各自产生不同类型的 stream event
→ 聊天 UI、业务 UI、开发调试台分别消费合适事件
→ Checkpoint / 业务数据库而不是短暂 stream 保存可靠事实
```

## 第一小节：Streaming 不等于模型逐字输出

Streaming 是 Runtime 向外报告运行事实的观察层，不是一条只负责模型逐 token 吐字的管道。模型输出、Node 返回的部分 State 更新、业务主动播报、Task 开始或结束、Checkpoint 创建，分别由不同对象产生，也应该被不同消费者使用。

可以用企业差旅 Agent 理解：用户要求预订航班，Agent 读取差旅政策、模型决定查询、ToolNode 调用航班供应商、模型选择候选项、再调用预订 Tool。前端既希望看到“正在查询”，也希望逐字看到最终答复；运维则需要知道哪个 Task 超时；恢复系统需要知道最后一个可持久化快照。这四种需要不是同一种流。

> **本节精髓：token stream 是模型输出观察面；Graph stream 是整个 Runtime 的多视角观察面。看到模型 token 不表示 Tool 已执行，也没有 token 不表示 Graph 没有在工作。**

## 第二小节：七种 stream mode

当前 `StreamMode` 包含 `values`、`updates`、`custom`、`messages`、`checkpoints`、`tasks` 和 `debug`，见 [types.py:120-134](../../../submodules/langgraph/libs/langgraph/langgraph/types.py#L120-L134)。一次调用可以请求多个 mode；不同 mode 是同一次运行的不同观察口。

| Mode | 生产者与内容 | 合适用途 | 不应误用为 |
|---|---|---|---|
| `messages` | Node / Tool 内部 LLM 调用的消息块和元数据。 | 聊天文本逐块显示、Tool Call 参数可视化。 | 整个 Graph 的业务进度或持久状态。 |
| `updates` | Node / Task 提交的局部 State 更新；同一 step 的多个更新会分别发送。 | 订单状态、审批结论、阶段完成事件。 | 每步完整 State。 |
| `values` | 每个 step 后完整 State；也包含 interrupt。 | 原型调试、完整状态重绘、状态检查。 | 默认公开给浏览器的业务数据。 |
| `custom` | Node / Task 主动经 `StreamWriter` 发出的任意数据。 | “已查询 2/4 个供应商”等业务进度。 | State 更新或后续 Node 的触发信号。 |
| `tasks` | Runtime Task 的开始、结束、结果和错误。 | 耗时、失败和重试诊断。 | 面向终端用户的文案。 |
| `checkpoints` | Checkpointer 创建快照时的事件，形状接近 `get_state()`。 | 恢复、历史与审计观察。 | 聊天输出。 |
| `debug` | `tasks` 与 `checkpoints` 的调试级组合。 | 本地或受控诊断。 | 生产 UI 的直接数据源。 |

`values`、`updates`、`messages`、`custom` 的差异尤其重要：它们分别回答“完整 State 现在是什么”“哪个 Node 写了什么”“模型正在生成什么”“业务代码主动报告什么”。

## 第三小节：事件从哪里产生

一条典型事件链如下：

```text
Model 调用
→ messages：LLM 的输出块及其元数据

Node 返回 Partial State
→ updates：该 Node / Task 的局部更新
→ Runtime 在 step 边界合并后
→ values：完整 State 快照

Node 调用 StreamWriter(payload)
→ custom：仅向观察者发送 payload

Runtime 调度 / 完成 Task
→ tasks 或 debug

Runtime 创建 Checkpoint
→ checkpoints 或 debug
```

`Runtime` 可以将 `stream_writer` 注入 Node；未启用 `stream_mode="custom"` 时该 writer 是 no-op，见 [runtime.py:127-140](../../../submodules/langgraph/libs/langgraph/langgraph/runtime.py#L127-L140) 与 [types.py:136-139](../../../submodules/langgraph/libs/langgraph/langgraph/types.py#L136-L139)。因此 custom event 是主动播报，不会写 State、触发 Edge 或替代 Checkpoint。

## 第四小节：ToolNode 中到底会流出什么

仍以差旅 Agent 为例：

```text
1. Model Node 生成 search_flights Tool Call
   → messages 可以出现模型输出块或 Tool Call 参数块。

2. ToolNode 执行 search_flights
   → tasks / custom 可以显示“正在查询航班”；通常没有用户可见 token。

3. ToolNode 取得真实结果
   → ToolMessage 写入 State.messages；updates 报告 tools Node 的局部更新；
     values 在 Runtime 合并后看到完整 State。

4. Model Node 读取 ToolMessage 并总结
   → messages 才再次产生面向用户的自然语言输出。
```

Tool Call 是模型的执行意图，ToolNode 是真实执行边界，ToolMessage 是写回 State 的结果；三者不要被“模型流式输出”混成一个对象。

## 第五小节：Streaming、Checkpoint 与 Interrupt

Stream 是短暂观察信号，Checkpoint 是可恢复的运行事实。浏览器断线、事件消费者重启或网络抖动后，应用不应依靠回放旧 token 恢复界面；应依据 `thread_id` 查询 Checkpoint / State，并从业务后端读取关键订单、审批或支付事实。

当高风险预订触发 `interrupt` 时，Runtime 暂停并保存可恢复现场；前端从 stream 得知需要确认的事项，展示审批界面；可信后端完成鉴权后，用同一 `thread_id` 和 `Command(resume=...)` 恢复 Graph。前端点击确认不是恢复本身，更不应直接绕过后端创建 Command。当前 v2 stream 输出会把 `values` 中的 interrupt 放到结构化 `interrupts` 字段，见 [main.py:4219-4235](../../../submodules/langgraph/libs/langgraph/langgraph/pregel/main.py#L4219-L4235)。

> **本节精髓：stream 负责及时看见暂停；checkpoint 负责暂停后还能回来；Command 负责恢复执行。三者不能互相替代。**

## 第六小节：前端接入的实际边界

LangGraph Core 提供 `graph.stream()` / `graph.astream()` 及各类 stream mode，应用可以在自己的后端将其转换为 SSE、WebSocket 或其他浏览器连接。Core 不生成聊天窗口、进度条、审批表单，也不替应用完成用户鉴权与字段脱敏。

LangGraph Platform / SDK 进一步提供面向前端的连接和 State / thread 协作能力。当前 Platform Python SDK 的注释表明，`useStream` 会通过 state history 渲染 interrupt 并支持 branch；但 JS SDK 已迁至独立的 LangGraph.js 仓库，见 [sdk-js README](../../../submodules/langgraph/libs/sdk-js/README.md) 与 [runtime.py:58-67](../../../submodules/langgraph/libs/sdk-py/langgraph_sdk/runtime.py#L58-L67)。因此“有前端 streaming 支持”不等于“Core 自带完整前端产品”。

建议的职责分层是：

| 层 | 应承担的责任 |
|---|---|
| Graph / Runtime | 产生 messages、updates、custom、interrupt、checkpoint 等事实。 |
| Agent Server / 业务后端 | 鉴权、连接管理、事件过滤、敏感字段脱敏、`Command` 构造和业务状态查询。 |
| SDK 或前端传输层 | 订阅流、断线处理、按 thread 同步可见状态。 |
| 业务 UI | 聊天气泡、进度条、订单卡片、审批交互和错误提示。 |

## 第七小节：并行、子图与生产观察

并行 Node 的事件抵达顺序由实际耗时决定，不等于业务结论的优先级。前端不能把最后一条事件当作最终结论；应以汇合后的业务 State 或明确的决策字段为准。对子图启用 streaming 时，事件 namespace 用于说明事件来自主图还是哪个子图，未来 Multi-Agent 场景中必须依此区分不同 Agent 的输出。

生产系统还需遵守三个底线：

1. stream 不是可靠业务总线。关键业务事实写入 Checkpointer、数据库或外部系统，断线后重新查询。
2. stream 不是权限边界。完整 State、debug payload、原始 Tool 结果与异常可能含敏感数据，必须服务端过滤。
3. stream 不是幂等保证。用户看到“正在创建订单”不能证明订单没有创建成功；超时恢复仍需幂等键和外部状态核验。

## 面试收口

> LangGraph streaming 是 Runtime 的多视角观察机制，而不仅是 LLM token 输出。`messages` 用于模型逐块输出，`updates` 用于 Node 的局部 State 更新，`values` 用于完整 State 快照，`custom` 用于业务主动进度；`tasks`、`checkpoints` 和 `debug` 服务执行观测与恢复诊断。生产系统必须将聊天展示、业务状态和调试追踪分开消费，并将 checkpoint 与业务数据库作为可靠事实来源。

## QA / 讨论记录

### Q: LangGraph 有直接给前端用的 streaming 功能吗？

> **状态**: to-verify
> **来源**: source-code / discussion

A: 有两层。LangGraph Core 可通过 `graph.stream()` / `graph.astream()` 把 Runtime 事件交给应用后端，后端自行用 SSE 或 WebSocket 转发；它不提供完整业务前端。LangGraph Platform / SDK 提供前端友好的连接与 thread / state 协作能力，当前 SDK 源码提到 `useStream` 的 interrupt 渲染和 branching，但实际 JS / React API 已迁到独立 LangGraph.js 仓库，尚未在本课程中做完整源码 trace，因此保持 `to-verify`。

### Q: `messages` 流能代表 Agent 的完整状态吗？

> **状态**: verified
> **来源**: source-code / discussion

A: 不能。`messages` 表示 Node / Tool 内部 LLM 调用的消息块与元数据；它不等于 Tool 是否已经执行、State 是否已合并或 Checkpoint 是否已保存。业务进度优先使用经筛选的 `updates` / `custom`，完整 State 使用 `values` 或 checkpoint 查询。

## 下一小节

下一大点进入 Subgraph / Multi-Agent：Graph 怎样嵌套、多个 Agent 怎样分工、State 怎样跨图传递，以及何时不该为了“多 Agent”而拆图。
