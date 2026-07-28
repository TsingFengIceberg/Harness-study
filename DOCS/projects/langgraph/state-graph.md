# 第二课：LangGraph StateGraph 基础

> **日期**: 2026-07-23 | **更新**: 2026-07-27 | **状态**: draft | **涉及版本**: `langgraph@30c4d58db86455128e42ddec96b1ba53c553ba22`

## 相关文档

- [LangGraph 学习入口](README.md)
- [第三课：Pregel Channel 与任务调度](pregel-runtime.md)
- [LangChain / LangGraph 面试学习路线](../langchain/interview-roadmap.md)
- [第一课：Message、Runnable 与 Tool](../langchain/core-abstractions.md)
- 源码：[StateGraph 实现](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py)
- 源码：[LastValue channel](../../../submodules/langgraph/libs/langgraph/langgraph/channels/last_value.py)
- 测试：[StateGraph 状态测试](../../../submodules/langgraph/libs/langgraph/tests/test_state.py)

## 本课路线

```text
State
→ State schema 与部分更新
→ Node
→ Edge / conditional edge
→ Reducer
→ 串起完整 StateGraph step
→ 与 Runnable pipeline 对比
```

当前学习进度：

- [x] 第一小节：State 的基本直觉；
- [x] 第二小节：State schema 与部分更新；
- [x] 第三小节：Node 的本质、注册与执行边界；
- [x] 第四小节：Node 的 State / Config / Runtime / Store / Writer 输入；
- [x] 第五小节：Edge / conditional edge；
- [x] 第六小节：循环、分叉与汇合；
- [x] 第七小节：Reducer 与并行冲突原则；
- [x] 第八小节：完整 StateGraph superstep 与 BFS 类比；
- [x] 第九小节：Runnable pipeline 与 StateGraph 的执行边界。

## 第一小节：State 是 Runtime 管理的共享工作状态

### 一句话定义

> **State 是整张图共享的、由 LangGraph Runtime 管理的结构化工作状态。**

可以把 State 想成由图运行时保管的一块“共享工作白板”：

- Node 执行时读取当前白板；
- Node 完成工作后提交需要修改的字段；
- Runtime 负责收集并合并更新；
- 后续 Node 再读取更新后的状态。

源码对 `StateGraph` 的直接定义是：节点通过读写共享状态进行通信，并把节点签名概括为 `State -> Partial<State>`。见 [state.py:130-137](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py#L130-L137)。

### 最小例子

假设一张图负责生成文章：

```python
from typing_extensions import TypedDict


class State(TypedDict):
    topic: str
    outline: str
    article: str
```

初始 State 可以是：

```python
{
    "topic": "什么是 Agent Harness",
    "outline": "",
    "article": "",
}
```

生成大纲的 Node 读取 `topic`，只返回自己产生的更新：

```python
def create_outline(state: State):
    return {
        "outline": f"{state['topic']} 的文章大纲",
    }
```

Runtime 合并后，逻辑上的新 State 为：

```python
{
    "topic": "什么是 Agent Harness",
    "outline": "Agent Harness 的文章大纲",
    "article": "",
}
```

后续写文章的 Node 就能读取新的 `outline`。

### 一次更新如何流动

```text
用户调用 compiled_graph.invoke(...)
        ↓
Runtime 读取当前 State
        ↓
Runtime 调用当前 Node
        ↓
Node 读取 State 并完成计算
        ↓
Node 返回部分 State 更新
        ↓
Runtime 提取合法字段并写入对应 channel
        ↓
后续 Node 读取更新后的 State
```

`StateGraph` 本身是 builder，必须经过 `compile()` 才得到支持 `invoke()`、`stream()`、`ainvoke()` 等执行方法的图，见 [state.py:139-144](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py#L139-L144)。

### 为什么 State 不是普通局部变量

普通局部变量只属于一次函数调用：

```python
def node():
    result = "只存在于当前函数中的值"
```

它不能自然承担以下职责：

- 让多个 Node 通过统一协议共享数据；
- 让条件路由读取当前运行状态；
- 让循环中的多轮执行持续更新同一组逻辑字段；
- 让 Runtime 统一处理字段合并；
- 后续与 checkpoint、interrupt 和恢复机制衔接。

因此职责需要分开：

```text
Node：负责业务计算，声明本次产生了哪些更新
Runtime：负责调度 Node，并管理、合并和传播 State
```

> **本节精髓：Node 不拥有整张图的全局状态。Node 读取当前 State，返回部分更新；真正管理状态生命周期的是 Runtime。**

### State、Messages 与 Checkpoint 的边界

| 概念 | 当前阶段的理解 |
|---|---|
| State | 图执行过程中使用的逻辑数据集合。 |
| Messages | State 中可能存在的一个字段，不等于全部 State。 |
| Checkpoint | State 和运行进度在某个执行时刻的持久化记录；其准确结构将在 checkpoint 专题中核验。 |

例如：

```python
class State(TypedDict):
    messages: list
    current_plan: str
    retry_count: int
```

`messages` 只是 State 的一部分；State 还可以保存计划、计数器、检索结果或其他节点协作数据。

## 源码核验摘要

1. `StateGraph` 明确描述为“节点通过读取和写入共享状态进行通信”，节点契约为 `State -> Partial<State>`：[state.py:130-137](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py#L130-L137)。
2. `state_schema`、`input_schema` 和 `output_schema` 会在构造阶段分别注册；未单独指定输入输出 schema 时，默认使用 `state_schema`：[state.py:260-269](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py#L260-L269)。
3. schema 注册会将字段解析为 channel 或 managed value：[state.py:342-372](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py#L342-L372)。
4. `_get_channels()` 读取 schema 的类型注解，并为每个字段创建对应 channel：[state.py:1801-1821](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py#L1801-L1821)。
5. Node 返回字典时，Runtime 只提取属于允许输出字段的键值对：[state.py:1434-1449](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py#L1434-L1449)。
6. 普通字段回退为 `LastValue` channel；它每个 step 最多接收一个值，多值写入会抛出 `INVALID_CONCURRENT_GRAPH_UPDATE`：[last_value.py:20-21](../../../submodules/langgraph/libs/langgraph/langgraph/channels/last_value.py#L20-L21)、[last_value.py:56-66](../../../submodules/langgraph/libs/langgraph/langgraph/channels/last_value.py#L56-L66)。

## QA / 讨论记录

### Q: State 为什么不是普通全局字典？

> **状态**: verified
> **来源**: source-code / discussion

A: 在编程表面上，State 经常表现为一个字典或类似字典的对象；但在运行语义上，它不是由 Node 随意原地修改的普通全局变量。State schema 会被解析成 channels，Node 返回部分更新，Runtime 再负责提取、合并和传播这些更新。这个边界为后续 reducer、并行写入、checkpoint 和恢复提供统一基础。

### Q: `messages` 是否就是 LangGraph 的全部 State？

> **状态**: verified
> **来源**: source-code / discussion

A: 不是。`messages` 只是常见的 State 字段。State 还可以包含计划、检索结果、计数器、业务对象和路由标记等数据。

### Q: State、Context、Config、Store 与 Writer 应如何区分？

> **状态**: verified
> **来源**: source-code / discussion

A: 最实用的判断依据是数据的作用域和生命周期。当前图运行中会变化、后续 Node 需要读取的业务事实放入 State；本次 run 固定使用的身份和依赖放入 Context；控制 Runnable 本次如何调用和观测的参数放入 Config；需要跨 thread 或跨 run 共享的数据放入 Store；只需实时发送给外部观察者、不参与状态合并的信息通过 Writer 输出。Runtime 不是第六类业务数据，而是把 context、store、stream writer 和执行信息集中提供给 Node 的运行时对象。

### Q: Edge 是否直接调用下一个 Node？

> **状态**: verified
> **来源**: source-code / discussion

A: 不直接调用。Builder 中的 Edge 只声明控制流关系；编译时，普通 Edge 被转换为 channel 写入与 trigger，conditional edge 被挂载为 branch writer。来源 Node 完成后，Runtime 根据这些触发关系安排后续 Node。Node 负责计算，Edge 负责描述路线，Runtime 负责解释路线并执行调度。

### Q: 并行 Node 同时写一个字段时，什么时候应该使用 Reducer？

> **状态**: verified
> **来源**: source-code / discussion

A: 当多份更新在业务上可以共存或累计时，例如日志追加、计数累加、集合并集，可以用 Reducer 明确合并规则。如果多份更新是互相竞争、最终只能选一个的业务结论，例如两个并行检查都试图决定订单最终状态，不应靠“最后写入胜出”或随意设计 Reducer 掩盖竞争；应让各 Node 分别写自己的事实，再由汇合后的决策 Node 统一产生最终结论。

### Q: 一个 Pregel superstep 是否可以类比为一次 BFS 的分层扩展？

> **状态**: verified
> **来源**: source-code / discussion

A: 可以作为直觉类比。当前活跃任务类似 BFS frontier，本轮 Node 基于同一 State 快照执行，Edge 和更新后的 channels 决定下一轮 frontier；但它不是严格 BFS。LangGraph 允许回边和重复执行，conditional edge 会动态选路，多起点 Edge 还要求 barrier 汇合，而且运行目标是计算和合并 State，而不是按最短距离遍历每个节点一次。

### Q: StateGraph 已经有复杂的状态与调度，为什么 `CompiledStateGraph` 仍然是 Runnable？

> **状态**: verified
> **来源**: source-code / discussion

A: Runnable 是统一的外部调用协议，不要求内部实现必须是简单线性流程。从图内部看，`CompiledStateGraph` 通过 Pregel 执行多个 Node、superstep、状态合并和动态路由；从调用者看，它仍然接收输入并产生输出，可以使用 `invoke()`、`stream()` 等统一方法。源码上 `CompiledStateGraph` 继承 Pregel，而 `PregelProtocol` 继承 Runnable，因此 Node 内部可以嵌入 Runnable pipeline，整张编译图也可以作为一个更大的 Runnable 嵌入外层 pipeline。

## 第二小节：State schema 与部分更新

LangGraph 的 State 可以理解为整张图共用的一份工作记录，但它不是一个让所有函数随意修改的全局字典。真正保存和管理 State 的是 Runtime，Node 只读取 Runtime 交给它的当前状态，然后返回自己本次产生的更新。因此源码把节点契约概括为 `State -> Partial<State>`：输入当前 State，输出 State 的一部分更新。

例如：

```python
from typing_extensions import TypedDict


class State(TypedDict):
    topic: str
    outline: str
    retry_count: int
```

这个 `State` 就是 State schema。它声明这张图有哪些状态字段以及字段的数据类型。创建 `StateGraph(State)` 时，LangGraph 会读取这些类型注解，并在 Runtime 中为字段建立对应的 channel。当前可以先把 channel 理解成“某个 State 字段在运行时的专用槽位”：它保存字段值，也规定收到新写入时如何更新。普通字段默认使用 `LastValue`，也就是用本轮的新值替换旧值；通过 `Annotated` 声明 reducer 后，字段可以采用追加或自定义合并规则，这部分将在 Reducer 小节展开。

State schema 定义的是图中可能存在的状态字段，并不等于 Runtime 会自动为每个字段生成初始值。假设初始输入只有：

```python
{"topic": "LangGraph"}
```

那么 `outline` 不会仅凭类型声明自动变成空字符串，它通常要等前置 Node 写入后才存在。因此 Node 读取字段时，仍要保证执行到当前阶段时该字段已经由初始输入或前置节点产生。默认情况下，未单独指定 `input_schema` 和 `output_schema` 时，`StateGraph` 会同时使用 `state_schema` 作为输入和输出 schema；复杂图也可以分别限制外部输入和最终输出的形状。

假设当前 State 是：

```python
{
    "topic": "LangGraph",
    "outline": "",
    "retry_count": 2,
}
```

生成大纲的 Node 可以读取整个 State，但只返回自己负责的字段：

```python
def create_outline(state: State):
    outline = f"{state['topic']} 的文章大纲"
    return {"outline": outline}
```

Runtime 不会用这个小字典替换整个 State，而是把它当成一张修改单：本次只更新 `outline`，没有出现在返回值中的 `topic` 和 `retry_count` 不产生新写入，继续保留原值。因此合并后的逻辑 State 是：

```python
{
    "topic": "LangGraph",
    "outline": "LangGraph 的文章大纲",
    "retry_count": 2,
}
```

这里需要区分“字段缺席”和“字段值为 `None`”。返回值中没有 `topic`，表示本轮不更新 `topic`；如果明确返回 `{"topic": None}`，则表示本轮确实要向 `topic` 写入 `None`，前提是字段类型和业务逻辑允许这样做。

Node 也可以返回完整字典：

```python
def create_outline(state: State):
    return {
        **state,
        "outline": f"{state['topic']} 的文章大纲",
    }
```

这种写法不一定立即报错，但所有出现在返回值中的合法字段都会被视为本轮写入，即使某些值看起来没有变化。这样做会模糊节点职责，也会给后续并行执行和 reducer 合并带来问题：同一 superstep 的多个 Node 如果都返回完整 State，就可能同时写入同一个 `LastValue` channel，从而触发并发更新错误；对于追加型 reducer，重新返回已经累积的完整列表，还可能让旧内容被再次合并。因此 Node 通常只应返回自己真正产生的更新。

完整运行关系是：Runtime 根据 State schema 管理字段及其 channel，调用 Node 时把当前 State 交给它；Node 完成业务计算并返回 `Partial<State>`；Runtime 从返回值中提取合法字段，将每项更新交给对应 channel；后续 Node 再读取合并后的状态。Node 负责计算，Runtime 负责状态生命周期，两者通过“读取 State、返回部分更新”协作。

> **本节精髓：State schema 定义整张图有哪些状态槽位以及这些槽位如何更新；Node 返回值不是一个新的完整 State，而是一张交给 Runtime 的状态修改单。字段缺席表示本轮不更新，字段出现才表示本轮产生一次写入。**

### 面试简答

> State schema 定义 LangGraph 状态中的字段、类型和字段更新规则。StateGraph 会读取 schema 的类型注解，把字段注册成 Runtime 管理的 channel。Node 接收当前 State，但通常只返回自己负责的部分更新；Runtime 再把这些更新写入对应 channel。部分更新能明确节点职责，并减少无关字段写入、并行冲突和 reducer 重复合并。

## 第三小节：Node 的本质、注册与执行边界

LangGraph Node 是图中一个有名字的计算单元。它接收 Runtime 交给它的当前输入，完成一项具体工作，再把结果交还 Runtime。Node 本身不保存整张图的状态，也不会因为被 `add_node()` 注册就立刻运行；状态生命周期和实际调度仍由编译后的运行图负责。

最常见的 Node 是一个普通函数：

```python
def create_outline(state: State):
    outline = f"{state['topic']} 的文章大纲"
    return {"outline": outline}
```

这个函数只描述业务计算。要让它成为图的一部分，还要注册：

```python
builder = StateGraph(State)
builder.add_node("create_outline", create_outline)
```

`add_node()` 的职责是建立 Node 规格，而不是执行函数。它记录 Node 名称、action、输入 schema、metadata、retry policy、cache policy、timeout、error handler 等信息；如果没有显式传入名称，普通函数通常使用函数名，Runnable 则尝试使用自己的名称。源码的公开说明也直接把 `node` 描述为“该 Node 将运行的 function or runnable”，并说明默认从整张图的 State schema 推断输入 schema，见 [state.py:375-397](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py#L375-L397)。

在具体注册过程中，LangGraph 会检查名称是否重复或使用了 `START` / `END` 等保留名，尝试从函数类型注解推断专用输入 schema，再使用 `coerce_to_runnable()` 把 action 统一成 Runnable，最后保存为 `StateNodeSpec`。见 [state.py:768-855](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py#L768-L855) 和 [state.py:872-907](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py#L872-L907)。`StateNodeSpec` 则集中保存 runnable、input schema、retry、cache、error handler、defer 和 timeout 等 Node 级运行规格，见 [_node.py:84-95](../../../submodules/langgraph/libs/langgraph/langgraph/graph/_node.py#L84-L95)。

因此普通函数能够成为 Node，并不是因为 StateGraph 为每种函数设计了一套独立执行方法，而是因为注册阶段先把不同 callable 统一到 Runnable 协议：

```text
普通函数 / 异步函数 / 现成 Runnable
                ↓
        coerce_to_runnable()
                ↓
          StateNodeSpec
                ↓
       编译进运行时图结构
```

这也连接了上一课的 Runnable：Runnable 解决“一个计算单元如何被统一调用”，Node 进一步增加“它在状态图里叫什么、读取什么输入、采用哪些重试和缓存策略、如何参与图调度”等语义。

注册之后还不能直接运行，因为 `StateGraph` 是 Builder。调用 `compile()` 后才会产生实现 Runnable 接口的 `CompiledStateGraph`，支持 invoke、stream、batch 和异步调用，见 [state.py:1164-1179](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py#L1164-L1179)。编译阶段会创建 `CompiledStateGraph`，把已注册的 Node、Edge 和 branch 分别 attach 进去；而 `CompiledStateGraph` 本身继承 Pregel，见 [state.py:1333-1388](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py#L1333-L1388) 和 [state.py:1391-1394](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py#L1391-L1394)。

于是三个动作的边界是：

```text
add_node()：登记计算单元及其运行规格
compile()：把 Builder 转成可执行的 CompiledStateGraph
invoke()：启动一次运行，由 Pregel runtime 调度实际 Node
```

Edge 在这里描述控制流依赖，告诉运行图某个 Node 完成后哪些节点可能具备执行条件；Edge 本身不是函数调用者。真正读取状态、准备 Node 输入并调用 Runnable 的是编译后图中的 Runtime。普通 Node 也不应该通过直接调用另一个 Node 来隐藏图控制流，否则 Edge、checkpoint、interrupt、stream 和 tracing 都难以完整观察这段执行关系。进阶场景可以返回 `Command`，同时向 Runtime 提交状态更新和跳转意图，但仍然是 Runtime 解释并执行命令，而不是当前 Node 私自接管调度。

一次最小运行可以表示为：

```text
builder.add_node(...) 注册 Node
        ↓
builder.add_edge(...) 声明控制流
        ↓
builder.compile() 生成 CompiledStateGraph
        ↓
graph.invoke(initial_state) 启动运行
        ↓
Pregel runtime 根据图结构调度 Node
        ↓
Node 读取 State 并返回 Partial<State>
        ↓
Runtime 合并更新并继续调度
```

> **本节精髓：Node 是被 Runtime 调用的命名计算单元。`add_node()` 只注册，`compile()` 生成运行图，`invoke()` 才启动调度；Node 负责计算，Runtime 负责状态与执行生命周期，Edge 负责描述控制流。**

### 面试简答

> LangGraph Node 是状态图中的命名计算单元，可以由普通函数、异步函数或 Runnable 构成。`add_node()` 会把 action 统一包装成 Runnable，并与输入 schema、重试、缓存和超时等信息一起保存为 `StateNodeSpec`，但不会立即执行。`compile()` 生成继承 Pregel 的 `CompiledStateGraph`，调用 `invoke()` 后才由 Runtime 根据图结构调度 Node。Node 读取 State 并返回部分更新，Runtime 负责合并状态和推进执行。

## 第四小节：Node 的输入边界

只说“Node 接收 State”并不完整。实际任务还会用到用户身份、数据库连接、调用配置、长期记忆和实时进度；如果把这些内容全部塞进 State，业务状态就会混入运行控制和基础设施对象。LangGraph 因此把 Node 可用的信息分成不同作用域，最实用的判断方式不是背 API，而是看一项数据“负责什么、会不会变化、需要存活多久”。

| 对象 | 通俗理解 | 典型内容 |
|---|---|---|
| State | 当前任务的实时存档 | messages、plan、outline、retry count、当前房间和生命值 |
| `RunnableConfig` | 本次调用的执行说明 | `thread_id`、tags、metadata、callbacks、recursion limit |
| Context | 本次 run 固定使用的身份与依赖 | user ID、tenant ID、region、数据库连接 |
| Store | 可跨 thread / run 使用的长期档案 | 用户偏好、长期记忆、共享资料 |
| `StreamWriter` | 发给 UI 或调用者的实时播报 | “正在检索”“已处理 3/10 个文件” |

可以用“地牢闯关”理解这组边界。战斗中的当前房间、生命值、金币和 Boss 是否被击败会随着这一局游戏变化，后续房间也需要读取这些结果，所以属于 State：

```python
class DungeonState(TypedDict):
    current_room: int
    hp: int
    gold: int
    boss_hp: int
```

玩家身份和所在区域在这一局开始时已经确定，通常不应由战斗 Node 修改，因此适合作为 run-scoped Context：

```python
from dataclasses import dataclass


@dataclass
class Context:
    player_id: str
    region: str
```

同一个玩家可以开启多局地牢。`player_id` 回答“谁在玩”，而 `thread_id` 回答“继续他的哪一局存档”。`thread_id` 属于调用 Config，通常放在 `configurable` 中，同时还可以携带 tracing tags、metadata、callbacks、并发与递归限制等执行设置。`RunnableConfig` 的字段定义见 [config.py:57-128](../../../submodules/langchain/libs/core/langchain_core/runnables/config.py#L57-L128)。

```python
config = {
    "configurable": {"thread_id": "dungeon-run-007"},
    "tags": ["boss-challenge"],
    "recursion_limit": 30,
}
```

玩家永久等级、已解锁装备和语言偏好需要在退出当前地牢后继续存在，因此适合放在 Store。源码把 `BaseStore` 定义为可跨 thread、按 user ID、assistant ID 或其他 namespace 共享的持久化键值存储，见 [store/base/__init__.py:708-725](../../../submodules/langgraph/libs/checkpoint/langgraph/store/base/__init__.py#L708-L725)。它和 checkpointer 的边界可以先概括为：checkpointer 以 `thread_id` 为主键保存并恢复某条图执行线的 State 与进度；Store 保存不局限于单条执行线的长期数据。checkpointer 的准确契约见 [checkpoint/base/__init__.py:176-192](../../../submodules/langgraph/libs/checkpoint/langgraph/checkpoint/base/__init__.py#L176-L192)。

`StreamWriter` 则像实时战斗播报。Node 可以发出“玩家造成 40 点伤害”，但这条消息不会自动把 `boss_hp` 减少 40；真正参与 State 合并的仍然是 Node 返回的 `{"boss_hp": 60}`。源码将 `StreamWriter` 定义为接收任意数据的 callable，并用于 custom stream，见 [types.py:129-136](../../../submodules/langgraph/libs/langgraph/langgraph/types.py#L129-L136)。

```text
runtime.stream_writer({"damage": 40})
    → 给 UI / 调用者的实时观察信息

return {"boss_hp": 60}
    → 交给 Runtime 合并的正式 State 更新
```

`Runtime` 不是第六份业务数据，而是 Runtime 交给 Node 的运行工具包。当前 `Runtime[Context]` 集中提供 `context`、`store`、`stream_writer`、previous 和 execution info 等对象；它明确不包含 `RunnableConfig`，需要 Config 时应在 Node 参数中单独声明 `config: RunnableConfig`。见 [runtime.py:124-141](../../../submodules/langgraph/libs/langgraph/langgraph/runtime.py#L124-L141) 和 [runtime.py:198-228](../../../submodules/langgraph/libs/langgraph/langgraph/runtime.py#L198-L228)。

一个 Boss Node 可以把几类信息同时使用，但各自职责不同：

```python
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime


def fight_boss(
    state: DungeonState,
    config: RunnableConfig,
    runtime: Runtime[Context],
):
    player_id = runtime.context.player_id
    thread_id = config["configurable"]["thread_id"]

    profile = None
    if runtime.store is not None:
        profile = runtime.store.get(("players",), player_id)

    has_long_sword = bool(profile and profile.value["long_sword_unlocked"])
    damage = 40 if has_long_sword else 20

    runtime.stream_writer(
        {"thread_id": thread_id, "message": f"造成 {damage} 点伤害"}
    )

    return {"boss_hp": state["boss_hp"] - damage}
```

这段代码翻译成自然语言是：Node 从 State 读取这一局的 Boss 血量，从 Context 确认玩家身份，从 Config 得知当前存档编号，从 Store 查询玩家永久解锁的装备，通过 Writer 向 UI 播报伤害，最后只把新的 Boss 血量作为 State 更新返回。

LangGraph 会在包装函数时检查参数签名。当前源码识别 `config`、`writer`、`store`、`previous` 和 `runtime` 等可注入参数，并在真正调用 Node 时从 Config 和 Runtime 中取出对应对象，见 [_runnable.py:145-198](../../../submodules/langgraph/libs/langgraph/langgraph/_internal/_runnable.py#L145-L198) 和 [_runnable.py:317-398](../../../submodules/langgraph/libs/langgraph/langgraph/_internal/_runnable.py#L317-L398)。Node 也可以直接接收 `writer` 或 `store`，但使用完整 `Runtime[Context]` 能把 run-scoped context 和常用运行工具组织在同一对象中。

最后可以按生命周期快速判断：

```text
当前任务中会变化，后续 Node 要读取
→ State

本次 run 固定使用的身份或依赖
→ Context

控制 Runnable 本次如何调用、追踪和恢复
→ RunnableConfig

换一个 thread / run 后仍需共享
→ Store

只想实时告诉外部，不参与状态合并
→ StreamWriter
```

> **本节精髓：State 是当前运行的业务存档，Context 是本次 run 的固定背景，Config 是调用说明，Store 是跨运行档案，Writer 是观察通道；Runtime 负责把 Context、Store 和 Writer 等运行能力提供给 Node，只有 Node 返回的更新才进入 State 合并。**

### 面试简答

> LangGraph Node 的核心业务输入是 State，但还可以按函数签名接收 RunnableConfig 或 Runtime。State 保存当前图运行中会变化的业务事实；Config 保存 thread_id、tags 和 recursion limit 等调用配置；Runtime context 提供本次 run 固定的身份与依赖；Store 保存可跨 thread 共享的长期数据；StreamWriter 发送不参与 State 合并的自定义流事件。LangGraph 在 Runnable 包装阶段检查函数签名，并在运行时注入对应对象。

## 第五小节：Edge 与 conditional edge

Node 决定“做什么”，Edge 决定“做完以后往哪里走”，Runtime 负责真正执行和调度。可以把 StateGraph 看成订单处理中心：Node 是检查订单、自动审批和人工审核等岗位，State 是订单档案，Edge 是岗位之间的路线，Runtime 则是读取路线并安排岗位工作的调度员。

Edge 本身不会审核订单，也不会像普通 Python 调用那样直接执行下一个 Node。`add_edge()` 在 Builder 中登记有向关系；`compile()` 再通过 `attach_edge()` 把关系转换成运行时 channel 写入和 trigger。见 [state.py:915-966](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py#L915-L966)、[state.py:1377-1387](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py#L1377-L1387) 和 [state.py:1537-1561](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py#L1537-L1561)。

### 普通 Edge：固定路线

下面是一条没有分支的固定流程：

```text
START → check_order → auto_approve → END
```

对应代码：

```python
builder.add_edge(START, "check_order")
builder.add_edge("check_order", "auto_approve")
builder.add_edge("auto_approve", END)
```

调用 `graph.invoke(initial_state)` 后，Runtime 从 `START` 接收初始输入，调度 `check_order`，合并它返回的 State 更新，再根据 Edge 调度 `auto_approve`；最后一条路线到达 `END`，本次执行结束。因此：

```python
builder.add_edge("check_order", "auto_approve")
```

并不等于在 Python 中立即执行：

```python
check_order()
auto_approve()
```

前者声明图的控制流，后者是在当前调用栈中直接调用函数，会绕过图 Runtime 的调度、状态合并、checkpoint、interrupt、stream 和 tracing 边界。

### Conditional Edge：根据最新 State 动态选路

订单可能有三种情况：资料不完整时要求补充，资料完整且风险低时自动通过，资料完整且风险高时转人工审核。这时下一站无法在建图时固定，需要路由函数读取 State：

```python
from typing import Literal


def route_order(
    state: OrderState,
) -> Literal["auto", "manual", "supplement"]:
    if not state["documents_complete"]:
        return "supplement"
    if state["risk_level"] == "high":
        return "manual"
    return "auto"
```

注册条件路由：

```python
builder.add_conditional_edges(
    "check_order",
    route_order,
    {
        "auto": "auto_approve",
        "manual": "manual_review",
        "supplement": "request_more_info",
    },
)
```

三部分的职责分别是：

| 内容 | 含义 |
|---|---|
| `"check_order"` | 条件路线从哪个 Node 出发 |
| `route_order` | 读取当前 State 并返回路径标识 |
| `path_map` | 把路径标识映射到真正的目标 Node |

如果 `route_order(state)` 返回 `"manual"`，Runtime 通过 `path_map` 找到 `manual_review` 并调度它。完整关系是：

```text
check_order 返回部分 State 更新
        ↓
Runtime 取得本轮更新后的最新 State
        ↓
执行 route_order(state)
        ↓
得到路径标识 "manual"
        ↓
映射到 manual_review
        ↓
Runtime 调度 manual_review
```

`add_conditional_edges()` 会把路由函数包装成 Runnable 并保存为 `BranchSpec`；编译时，`attach_branch()` 将 branch writer 挂到来源 Node 上，并通过 fresh state reader 读取当前状态。见 [state.py:969-1014](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py#L969-L1014) 和 [state.py:1563-1605](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py#L1563-L1605)。路由函数会被 Runtime 执行，但它的核心职责是选路，不应偷偷承担大量业务计算或原地修改 State。

### `START` 与 `END`

`START` 和 `END` 分别是内部值 `"__start__"` 与 `"__end__"`，见 [constants.py:28-30](../../../submodules/langgraph/libs/langgraph/langgraph/constants.py#L28-L30)。它们是控制流标记，不是普通业务 Node：`START` 表示初始输入从哪里进入图，`END` 表示当前执行路线到此结束。`set_entry_point(key)` 等价于 `add_edge(START, key)`，`set_finish_point(key)` 等价于 `add_edge(key, END)`，见 [state.py:1066-1113](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py#L1066-L1113)。

> **本节精髓：Edge 不负责执行业务，它负责声明控制流。普通 Edge 给出固定下一站；conditional edge 通过路由函数读取最新 State，动态选择下一站；最终仍由 Runtime 解释路线并调度 Node。**

### 面试简答

> LangGraph Edge 描述节点之间的控制流，不直接调用 Node。普通 Edge 表示固定跳转；conditional edge 会在来源 Node 完成后执行路由函数，根据最新 State 返回目标或路径标识，再由 Runtime 调度对应 Node。`START` 和 `END` 分别表示图的入口与终点，不是普通业务节点。

## 第六小节：循环、分叉与汇合

### 循环由回边形成

LangGraph 的循环通常不是藏在某个 Node 内部的 `while`，而是让 conditional edge 把控制流重新指向前面的 Node。例如订单风险信息不足时先补充数据，然后重新检查：

```text
check_order
    ├─ 低风险 → auto_approve → END
    ├─ 高风险 → manual_review → END
    └─ 信息不足 → enrich_order_data → check_order
```

循环次数属于当前图运行中会变化、后续 Node 和路由函数都要读取的事实，因此应放入 State：

```python
class OrderState(TypedDict):
    risk_score: float | None
    check_attempts: int
    status: str


def check_order(state: OrderState):
    return {
        "risk_score": calculate_risk_score(),
        "check_attempts": state["check_attempts"] + 1,
    }
```

路由函数只读取最新状态并决定出口：

```python
def route_after_check(state: OrderState):
    score = state["risk_score"]
    if score is not None and score < 0.3:
        return "approve"
    if score is not None and score >= 0.7:
        return "manual"
    if state["check_attempts"] >= 3:
        return "manual"
    return "enrich"
```

注册回边：

```python
builder.add_conditional_edges(
    "check_order",
    route_after_check,
    {
        "approve": "auto_approve",
        "manual": "manual_review",
        "enrich": "enrich_order_data",
    },
)
builder.add_edge("enrich_order_data", "check_order")
```

`check_attempts >= 3` 是业务退出条件；Config 中的 `recursion_limit` 是 Runtime 防止图失控的保险丝，不能代替正常出口。图循环的优势是每轮 Node 调用、State 更新和路由都显式暴露给 Runtime，后续可以分别进行 tracing、stream、checkpoint、interrupt 和错误恢复。

还要注意，普通 Edge 回到前一个 Node 只表示立即继续调度，不代表自动等待用户。`request_more_info → check_order` 如果没有任何新输入，可能高速空转；真正等待用户补充资料，需要后续学习的 interrupt、checkpoint、`thread_id` 和恢复执行机制。

### 分叉：多个目标都执行

一个来源 Node 可以通过多条普通 Edge 激活多个后续 Node：

```python
builder.add_edge("receive_order", "fraud_check")
builder.add_edge("receive_order", "inventory_check")
```

这表示两个检查都要执行，不是二选一。二者在控制流上属于同一后续 superstep，可以由 Runtime 并发调度，但是否在物理时间上同时执行仍受同步或异步调用、执行器、并发配置、资源和限流策略影响。

两个并行 Node 读取同一轮开始时的 State，各自返回更新；它们不会在本轮执行过程中直接看到对方刚返回的结果。例如：

```python
def fraud_check(state: OrderState):
    return {"risk_level": calculate_risk(state["amount"])}


def inventory_check(state: OrderState):
    return {"in_stock": check_inventory(state["product_id"])}
```

`fraud_check` 不应假设 `in_stock` 已经由并行节点写入，`inventory_check` 也不应假设 `risk_level` 已经存在。Runtime 会在轮次边界收集和合并二者的更新。

### 汇合：等待所有前置 Node

最终决策必须同时读取风险和库存结果时，可以注册多起点 Edge：

```python
builder.add_edge(
    ["fraud_check", "inventory_check"],
    "make_decision",
)
```

这表示 `make_decision` 必须等待列表中的所有前置 Node 完成，不是任选一个完成就继续。当前实现会为多起点 Edge 建立 barrier channel，见 [state.py:915-922](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py#L915-L922) 和 [state.py:1546-1561](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py#L1546-L1561)。

```text
receive_order
        ↓
fraud_check  +  inventory_check
        ↓              ↓
risk_level       in_stock
        └──── Runtime 合并 ────┘
                      ↓
               make_decision
```

Conditional edge 的路由函数也可以返回多个目标，形成动态分叉；但如果静态 barrier 等待了某条本轮根本没有选择的分支，汇合就会更复杂。因此动态 fan-out、`Send` 和高级 barrier 语义留到 Pregel 专题继续核验。

> **本节精髓：回边形成循环，State 保存循环进度，业务条件负责正常退出；一个来源连接多条普通 Edge 表示多个目标都执行，`add_edge([A, B], C)` 表示 C 等待 A、B 全部完成。并行 Node 读取同一轮 State，Runtime 在轮次边界统一收集并合并更新。**

## 第七小节：Reducer 与并行冲突原则

Reducer 是 State 字段的合并规则，决定 Runtime 如何用“旧值 + 新更新”计算该字段的新值：

```text
新字段值 = reducer(当前字段值, Node 返回的新更新)
```

Reducer 声明在 State schema 的字段上，而不是 Node 或 Edge 上。普通字段默认回退为 `LastValue` channel：一个 step 没有写入时保留原值，只有一份写入时使用该值，同时收到多份写入时抛出 `INVALID_CONCURRENT_GRAPH_UPDATE`，见 [last_value.py:20-21](../../../submodules/langgraph/libs/langgraph/langgraph/channels/last_value.py#L20-L21) 和 [last_value.py:56-66](../../../submodules/langgraph/libs/langgraph/langgraph/channels/last_value.py#L56-L66)。

### 用 `Annotated` 声明合并规则

如果多个订单检查产生的记录都要保留，可以声明列表追加：

```python
import operator
from typing import Annotated


class OrderState(TypedDict):
    notes: Annotated[list[str], operator.add]
```

`operator.add` 在这里相当于：

```python
def append_notes(
    current: list[str],
    update: list[str],
) -> list[str]:
    return current + update
```

假设旧值是 `['订单已创建']`，风险检查和库存检查分别返回 `['风险检查完成']` 与 `['库存检查完成']`，Runtime 将当前值和每份新更新依次交给 Reducer，得到三条都保留的新列表。

State schema 解析会检查 `Annotated` 元数据中的 callable 是否接受两个位置参数，符合时创建 `BinaryOperatorAggregate` channel，见 [state.py:1840-1858](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py#L1840-L1858) 和 [state.py:1890-1907](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py#L1890-L1907)。该 channel 的 `update()` 会把当前值与收到的新值逐一交给 operator，见 [binop.py:61-125](../../../submodules/langgraph/libs/langgraph/langgraph/channels/binop.py#L61-L125)。

Reducer 不只在并行场景中生效。只要字段收到更新，顺序执行的 Node 也会继续将新更新与当前累计值合并。不同字段可以采用不同更新语义：

```python
class OrderState(TypedDict):
    status: str
    notes: Annotated[list[str], operator.add]
    total_checks: Annotated[int, operator.add]
```

其中 `status` 默认覆盖，`notes` 追加记录，`total_checks` 累加 Node 返回的增量。

### Node 必须返回增量

带 Reducer 的字段尤其不能无脑返回已经手工合并好的完整旧值。假设当前 `notes` 是 `['订单已创建']`，下面的写法会把旧记录重复合并：

```python
def fraud_check(state: OrderState):
    return {
        "notes": state["notes"] + ["风险检查完成"],
    }
```

正确写法只提交新增部分：

```python
def fraud_check(state: OrderState):
    return {"notes": ["风险检查完成"]}
```

字段没有出现在返回值中表示本轮不更新；空列表、`0` 和 `None` 一旦出现在返回值中，就是实际更新，Reducer 必须能够处理对应类型。

### 并行冲突不是多个线程同时改字典

LangGraph 中的典型并行冲突，是 Runtime 在同一个 step 结束时发现一个字段收到了多张更新单，却没有合并规则。判断时可以分三种情况。

第一种，两个 Node 写不同字段，不冲突：

```python
# fraud_check
{"risk_level": "low"}

# inventory_check
{"in_stock": True}
```

第二种，同一字段的多份更新可以共存或累计，使用符合业务含义的 Reducer：

```python
# 两条日志都保留
notes: Annotated[list[str], operator.add]

# 两份检查增量相加
total_checks: Annotated[int, operator.add]
```

第三种，多份更新互相竞争、最终只能选一个业务结论。这种情况不应靠“最后写入胜出”或随意设计 Reducer 掩盖竞争。例如风险检查和库存检查都不应直接写最终 `status`：

```python
# 不推荐：两个并行 Node 竞争最终结论
{"status": "approved"}
{"status": "out_of_stock"}
```

正确设计是让它们分别保存事实，再由汇合后的决策 Node 统一写最终状态：

```python
def make_decision(state: OrderState):
    if state["risk_level"] == "high":
        return {"status": "manual_review"}
    if not state["in_stock"]:
        return {"status": "out_of_stock"}
    return {"status": "approved"}
```

可以用下面的顺序判断：

```text
并行 Node 是否写同一字段？
│
├─ 否 → 没有字段冲突
│
└─ 是
   ├─ 多份更新可以共存或累计
   │  → 使用 Reducer
   │
   └─ 多份更新互相竞争，只能选一个
      → 分开保存事实
      → 由汇合后的决策 Node 统一判断
```

自定义 Reducer 还应考虑合并顺序。并行场景下最好满足结合律，理想情况下也满足交换律；整数加法同时满足，列表拼接不满足交换律，因此不要把并行列表项的先后顺序当成重要业务保证。如果顺序有业务意义，应在元素中携带时间、序号或其他显式排序依据。

### `add_messages` 是带 Message 语义的 Reducer

常见的消息状态写法是：

```python
from langgraph.graph import add_messages


class ChatState(TypedDict):
    messages: Annotated[list, add_messages]
```

`add_messages` 不只是简单拼接列表：新 ID 的 Message 会追加，相同 ID 的 Message 会替换已有 Message。见 [message.py:61-92](../../../submodules/langgraph/libs/langgraph/langgraph/graph/message.py#L61-L92) 和 [message.py:372-373](../../../submodules/langgraph/libs/langgraph/langgraph/graph/message.py#L372-L373)。

> **本节精髓：Reducer 负责用“旧值 + 新更新”计算字段的新值，适合合并可以共存的增量，不适合替代只能选一个结果的业务决策。并行 Node 应分别记录事实，再由汇合后的 Node 产生竞争性结论；Node 始终只返回自己产生的增量。**

### 面试简答

> Reducer 是 LangGraph State 字段级的更新函数，签名通常是 `(current, update) -> merged`。Runtime 用它把字段当前值和 Node 返回的增量合并，尤其用于处理同一个 step 中多个 Node 对同一字段的写入。没有 Reducer 的普通字段默认使用 `LastValue`，同一 step 收到多份更新会报错。Reducer 应用于可共存或可累计的更新；竞争性的最终结论应由汇合后的决策 Node 统一产生。

## 第八小节：完整 StateGraph superstep

一次 `invoke()` 往往包含多个 superstep。一个 superstep 是 Runtime 先选择一批当前可以执行的 Node，让它们读取同一份 State 快照并完成计算，最后统一收集写入、通过 channel 和 Reducer 合并，再根据更新产生下一轮任务。一个 Node 不一定独占一个 superstep；如果风险检查和库存检查没有相互依赖，它们可以属于同一轮。

Pregel 源码把每个 step 分成三个阶段：

```text
Plan：选择本轮要执行的 actors / Node
Execution：执行本轮任务，写入在本轮内对其他任务不可见
Update：统一把本轮写入应用到 channels
```

完成 Update 后再次 Plan，直到没有 actor 被选中或达到最大步数。见 [main.py:450-477](../../../submodules/langgraph/libs/langgraph/langgraph/pregel/main.py#L450-L477)。

### 用订单流程走完四轮

图结构如下：

```text
START → receive_order
                  ├→ fraud_check ─────┐
                  └→ inventory_check ─┤
                                      ↓
                               make_decision
                              ├→ auto_approve → END
                              └→ manual_review → END
```

初始输入可以是：

```python
{
    "order_id": "order-001",
    "amount": 1200,
    "product_id": "phone-01",
    "notes": [],
}
```

输入阶段先把初始输入写入特殊的 `START` channel，`START → receive_order` 使 `receive_order` 成为第一批业务任务。

**Superstep 1**：Plan 选择 `receive_order`。Execution 执行该 Node，并暂存它返回的更新：

```python
{"status": "checking", "notes": ["订单已接收"]}
```

Update 阶段才将这些写入应用到 State channels，Edge 的运行时写入同时使两个检查节点具备后续触发条件。

**Superstep 2**：Plan 选择 `fraud_check` 和 `inventory_check`。二者读取同一份 State 快照，分别返回：

```python
# fraud_check
{"risk_level": "high", "notes": ["风险检查完成"]}

# inventory_check
{"in_stock": True, "notes": ["库存检查完成"]}
```

Execution 阶段的返回值先保存在各自任务的 pending writes 中。即使 `fraud_check` 先完成，`inventory_check` 在当前轮也看不到它刚写入的 `risk_level`。等本轮任务完成后，Update 按 channel 对写入分组：

```text
risk_level → 一份更新 → LastValue 写入 "high"
in_stock   → 一份更新 → LastValue 写入 True
notes      → 两份更新 → Reducer 合并两条记录
```

`apply_writes()` 会排序任务、收集各任务写入、按 channel 分组，再调用对应 channel 的 `update()`，见 [_algo.py:232-336](../../../submodules/langgraph/libs/langgraph/langgraph/pregel/_algo.py#L232-L336)。

**Superstep 3**：多起点 Edge 的 barrier 已确认两个检查都完成，`make_decision` 才被调度。它读取的是已经合并的新 State：

```python
{
    "risk_level": "high",
    "in_stock": True,
    "notes": ["订单已接收", "风险检查完成", "库存检查完成"],
}
```

`make_decision` 返回 `{"status": "manual_review"}`；Runtime 合并该更新，conditional edge 再根据最新状态选择 `manual_review`。

**Superstep 4**：Runtime 调度 `manual_review`。当它完成且所有活跃路线都到达 `END` 时，没有新的 Node 被触发，Pregel loop 结束。

### Barrier 为什么重要

如果一个并行 Node 完成后立刻把更新暴露给仍在执行的其他 Node，后者能看到什么就会取决于并发任务的完成速度。Bulk Synchronous Parallel 用 barrier 把计算和提交分开：

```text
本轮所有 Node：读取旧快照并独立计算
                    ↓
                 barrier
                    ↓
Runtime：统一合并并发布下一版 State
```

Runtime loop 的 `tick()` 先调用 `prepare_next_tasks()` 准备任务；所有任务执行结束后，`after_tick()` 才调用 `apply_writes()` 完成本轮 channel 更新并保存 checkpoint。见 [_loop.py:599-681](../../../submodules/langgraph/libs/langgraph/langgraph/pregel/_loop.py#L599-L681) 和 [_loop.py:683-725](../../../submodules/langgraph/libs/langgraph/langgraph/pregel/_loop.py#L683-L725)。

### 下一轮任务从哪里来

Edge 在编译后表现为运行时 channel 写入与 trigger。完成 Update 后，Runtime 根据上一轮更新了哪些 channels，以及哪些 Node 订阅这些触发 channel，准备下一轮任务。`prepare_next_tasks()` 会先从 `updated_channels` 找到候选 Node，再为可执行候选构造任务，见 [_algo.py:471-511](../../../submodules/langgraph/libs/langgraph/langgraph/pregel/_algo.py#L471-L511)。

因此完整闭环是：

```text
选择任务并读取 State 快照
→ 执行 Node 并暂存 Partial<State>
→ barrier
→ channel / Reducer 合并本轮写入
→ Edge / branch channels 触发下一批任务
→ 重复，直到没有任务
```

### 与 BFS 的类比和边界

可以把每个 superstep 类比成一次 BFS 的分层扩展：当前被选中的 Node 是 active frontier，本轮执行相当于处理当前层，Edge 和更新后的 channels 产生下一轮 frontier。

```text
Superstep 1：[receive_order]
Superstep 2：[fraud_check, inventory_check]
Superstep 3：[make_decision]
Superstep 4：[manual_review]
```

这个类比抓住了“当前层完成后再推进下一层”的直觉，但 LangGraph 不是严格 BFS：

| BFS 常见语义 | LangGraph superstep |
|---|---|
| 邻接关系通常固定 | conditional edge 可根据 State 动态选路 |
| 常用 visited 避免重复访问 | 回边允许同一个 Node 在多轮中重复执行 |
| 重点是遍历和路径 | 重点是读取、计算并合并 State |
| 发现邻居形成下一层 | channel 更新和 trigger 形成下一批任务 |
| 通常不要求多个父节点共同完成 | 多起点 Edge 可以通过 barrier 等待全部前置 Node |

因此更准确的说法是：Pregel superstep 像带动态路由、状态更新、重复执行和 barrier 汇合能力的 BFS frontier 推进。

> **本节精髓：同一 superstep 的 Node 读取同一份 State 快照，执行期间只产生暂存写入；Runtime 在 barrier 处统一通过 channel / Reducer 合并，更新后的 channels 再触发下一轮 Node。它可以类比 BFS 的分层 frontier，但允许循环、动态路由和汇合，并不等同于严格 BFS。**

### 面试简答

> LangGraph 的 Pregel Runtime 使用 Bulk Synchronous Parallel 模型。每个 superstep 包含 Plan、Execution 和 Update：先根据上一轮 channel 更新选择任务，再让本轮 Node 基于同一 State 快照执行，最后在 barrier 处统一应用写入。更新后的 channels 再触发下一轮任务。它可以类比 BFS 的 frontier 分层推进，但支持动态条件路由、回边重复执行和 barrier 汇合。

## 第九小节：Runnable pipeline 与 StateGraph 的边界

Runnable 关注“一个输入怎样经过计算单元变成输出”，StateGraph 关注“Runtime 怎样围绕共享 State，按轮次决定接下来执行哪些计算单元”。两者不是互相排斥的框架，而是局部计算协议和全局状态编排两个层级。

### Runnable pipeline：固定的加工流水线

以制作薯条为例：

```text
土豆 → 清洗 → 切条 → 油炸 → 装盘
```

每个工位都遵守同一个规则：接收输入、完成加工、返回输出。这对应 Runnable 的统一调用协议。把工位串成 `RunnableSequence`：

```python
fries_chain = wash | cut | fry | plate
```

数据会沿着预先声明的管道传递：`wash` 的输出成为 `cut` 的输入，`cut` 的输出再成为 `fry` 的输入。Runnable pipeline 的核心是 Input / Output 数据变换；`RunnableSequence` 负责前后依赖，`RunnableParallel` 则把同一个输入交给多个预先声明的分支并组装结果。见 [base.py:3063](../../../submodules/langchain/libs/core/langchain_core/runnables/base.py#L3063) 和 [base.py:3852](../../../submodules/langchain/libs/core/langchain_core/runnables/base.py#L3852)。

Runnable pipeline 并非只能是一条直线，`RunnableParallel` 可以分叉；但它的组合关系通常在构建 pipeline 时已经声明，核心仍然是值如何从前一个计算单元流向后一个计算单元。它本身不自动提供 State channels、Reducer、conditional edge、回边循环和 barrier 汇合语义。

### StateGraph：围绕共享订单板的餐厅调度中心

处理一张完整餐厅订单时，流程可能包括检查库存和过敏信息、同时制作主菜和饮料、缺货时更换菜品、失败时重做，以及所有餐品完成后一起出餐。这时仅靠一条固定加工线不够，需要一块共享订单板：

```python
{
    "order_id": "001",
    "main_dish": "牛排",
    "drink": "咖啡",
    "allergy": "花生",
    "main_dish_ready": False,
    "drink_ready": False,
    "status": "preparing",
}
```

订单板对应 State。每个岗位完成工作后，不直接私自调用另一个岗位，而是提交自己产生的状态更新：

```python
# 饮料岗位
{"drink_ready": True}

# 主菜岗位
{"main_dish_ready": True}
```

Runtime 像餐厅调度员：查看当前订单板，选择本轮可以工作的岗位，等待并行岗位完成，在 barrier 处合并更新，再根据 Edge 和最新 State 判断继续制作、重新制作还是出餐。

因此两种数据回流方式不同：

```text
RunnableSequence
A 的 Output → 直接成为 B 的 Input

StateGraph
A 返回 Partial<State>
→ Runtime 写入 channels 并通过 Reducer 合并
→ Edge / trigger 选择 B
→ B 读取下一版 State
```

### `RunnableParallel` 与图并行的区别

`RunnableParallel` 主要把同一个输入分发给多个 Runnable，再按键组装输出：

```text
同一个输入
├→ Runnable A → result_a
└→ Runnable B → result_b
最终得到 {"a": result_a, "b": result_b}
```

StateGraph 中的并行 Node 则读取同一 State 快照并分别返回状态增量，Runtime 在 superstep barrier 处通过 channel 和 Reducer 合并：

```text
同一 State 快照
├→ Node A → Partial<State>
└→ Node B → Partial<State>
Runtime 合并为下一版 State，并继续触发控制流
```

前者主要是组合计算结果，后者是更新共享逻辑状态并用更新继续驱动调度。

### Node 内部可以是一条 Runnable pipeline

餐厅中的一个岗位本身也可以有固定流水线。例如主菜岗位内部执行“读取订单、生成烹饪方案、烹饪、检查结果”：

```python
cook_chain = read_order | plan_recipe | cook | inspect


def cook_main_dish(state: RestaurantState):
    result = cook_chain.invoke({"order": state["order"]})
    return {"main_dish_result": result}
```

也可以把符合输入输出契约的 Runnable 直接注册为 Node；前文已经核验 `add_node()` 会通过 `coerce_to_runnable()` 统一包装 callable。此时职责是：

```text
StateGraph
→ 决定什么时候做主菜、失败后是否重做、做完后走向哪里

cook_chain
→ 完成“制作主菜”这项局部任务内部的固定加工步骤
```

### 为什么整张编译图对外又是 Runnable

从餐厅内部看，它包含多个岗位、共享订单板、并行制作、条件判断和失败重试；但从顾客外部看，餐厅仍然是“提交订单，得到出餐结果”。同理，从图内部看，`CompiledStateGraph` 运行多个 superstep；从外部看，它仍可以统一调用：

```python
result = compiled_graph.invoke(order)
```

源码上，`CompiledStateGraph` 继承 `Pregel`，见 [state.py:1391-1408](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py#L1391-L1408)；`PregelProtocol` 又继承 `Runnable`，见 [protocol.py:25](../../../submodules/langgraph/libs/langgraph/langgraph/pregel/protocol.py#L25)。这说明 Runnable 约束的是外部调用协议，不限制内部只能是简单线性实现。

因此整张图还可以嵌入更外层的数据 pipeline：

```python
application = normalize_input | compiled_graph | render_result
```

形成以下层次：

```text
外层 Runnable pipeline
→ 输入预处理
→ 内部 StateGraph 多轮状态调度
→ 输出后处理
```

### 选型判断

| 需求 | 更合适的抽象 |
|---|---|
| 固定、局部、无循环的数据变换 | `RunnableSequence` / `RunnableParallel` |
| 根据中间状态动态选择下一步 | StateGraph |
| 需要循环、Reducer、barrier 或共享 State | StateGraph |
| 需要 checkpoint、恢复或 HITL | StateGraph Runtime |
| 复杂应用中的局部模型调用和解析 | Node 内部使用 Runnable pipeline |
| 复杂应用的全局任务编排 | StateGraph 管理 Node 和 State |

用餐厅类比可以最终记成：

```text
Runnable
= 标准化工位：输入 → 加工 → 输出

RunnableSequence
= 多个工位组成的固定流水线

StateGraph
= 拿着共享订单板、动态调度多个工位的经理

CompiledStateGraph
= 内部是复杂餐厅，对外仍提供“订单输入 → 结果输出”的 Runnable 接口
```

> **本节精髓：Runnable 是工位或固定流水线，StateGraph 是围绕共享订单板调度这些工位的经理。Node 内部可以用 Runnable pipeline 完成局部计算；整张 StateGraph 编译后对外又是一个 Runnable，因此还可以嵌入更大的 pipeline。两者分别解决局部数据加工与全局有状态编排。**

### 面试简答

> Runnable 是统一的 Input / Output 调用与组合协议，`RunnableSequence` 和 `RunnableParallel` 主要描述预先声明的数据流。StateGraph 建立在 Runnable 之上，由 Pregel Runtime 围绕共享 State 按 superstep 调度 Node，并处理动态路由、循环、Reducer 和 barrier。Node 内部可以使用 Runnable pipeline，`CompiledStateGraph` 因为实现 Runnable 协议，也可以作为一个整体嵌入外层 pipeline。

## 本课小结与下一步

至此，State、State schema、Partial State、Node、运行时输入、Edge、conditional edge、循环、并行分叉、barrier 汇合、Reducer、Pregel superstep，以及 Runnable pipeline 与 StateGraph 的边界已经串成完整基础链路。下一课进入 [Pregel Channel 与任务调度](pregel-runtime.md)，继续核验 task preparation、channel version、pending writes、checkpoint 与 durable execution 的连接。
