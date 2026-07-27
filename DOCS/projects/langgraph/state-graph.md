# 第二课：LangGraph StateGraph 基础

> **日期**: 2026-07-23 | **更新**: 2026-07-27 | **状态**: draft | **涉及版本**: `langgraph@30c4d58db86455128e42ddec96b1ba53c553ba22`

## 相关文档

- [LangGraph 学习入口](README.md)
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
```

当前学习进度：

- [x] 第一小节：State 的基本直觉；
- [x] 第二小节：State schema 与部分更新；
- [ ] Node；
- [ ] Edge / conditional edge；
- [ ] Reducer；
- [ ] 完整运行流程与 Runnable pipeline 边界。

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

## 下一小节

下一步进入 Node，计划依次讨论：

1. Node 的本质是什么：图中的命名计算单元，而不是自己驱动流程的线程或服务；
2. `add_node()` 做了什么：注册名称、action、输入 schema、retry / cache / timeout 等规格，但此时并不执行 Node；
3. 普通函数和 Runnable 如何统一接入：action 会被 `coerce_to_runnable()` 包装后保存为 `StateNodeSpec`；
4. Node 能接收什么：State 是核心输入，还可按签名接收 `RunnableConfig`、`Runtime`、`StreamWriter` 或 `BaseStore`；
5. Node 返回什么：通常返回 `Partial<State>`，进阶场景也可以返回 `Command`；
6. 谁真正调用 Node：`compile()` 生成的运行图由 Pregel runtime 调度，而 Edge 只描述控制流关系；
7. Node 名称、专用 `input_schema`、同步 / 异步函数以及错误重试的边界；
8. 最后用一个两节点例子串起“注册、调度、读取 State、返回更新、结果回流”。

这些内容目前是下一节的问题清单，不在正式讲解和源码核验完成前标记为已完成。
