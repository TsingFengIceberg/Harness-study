# 第一课：Message、Runnable 与 Tool

> **日期**: 2026-07-23 | **状态**: draft | **涉及版本**: `langchain@98216c0c1d7d2dc13e3ebeac36329853a5cb52a0`

## 相关文档

- [LangChain 学习入口](README.md)
- [LangChain / LangGraph 面试学习路线](interview-roadmap.md)
- [LangGraph 学习入口](../langgraph/README.md)
- [Agent Loop 横向总结](../../comparison/agent-loop.md)
- [Tool System 横向总结](../../comparison/tool-system.md)

## 本课目标

第一课先建立 LangChain 最重要的三个底层概念：

```text
Message：一次模型对话中的结构化信封
Runnable：所有可执行组件共同遵循的插座标准
Tool：带有模型可理解契约的特殊 Runnable
```

学完后应能回答：

1. 为什么模型输入输出不能只用字符串表达；
2. Tool Call 请求与 Tool Result 如何配对；
3. Runnable 为什么能够被串联、并行、批处理和流式执行；
4. 为什么“所有 Tool 都是 Runnable，但不是所有 Runnable 都是 Tool”；
5. 模型提出工具请求后，究竟是谁真正执行工具；
6. 一条 LCEL pipeline 中的数据类型怎样逐步变化。

> **精髓：Message 负责表达运行中的语义，Runnable 负责统一组件执行方式，Tool 则在 Runnable 之上增加了供模型选择和调用的契约。**

## Message：结构化的对话信封

### 为什么不能只传字符串

普通聊天看起来只是用户说一句、模型回答一句，但 Agent 运行时还要区分：

- 谁说的：System、Human、AI 还是 Tool；
- AI 是在回答，还是在请求调用工具；
- 某个 Tool Result 对应哪一次 Tool Call；
- 本次调用消耗了多少 token，provider 返回了哪些 metadata；
- 哪部分内容应发给模型，哪部分完整结果只留给应用程序；
- 流式响应中的多个 chunk 应如何合并。

因此，LangChain 用 Message 对象承载这些结构化语义，而不是把所有内容压成无法可靠区分的字符串。

源码入口是 [messages/base.py](../../../submodules/langchain/libs/core/langchain_core/messages/base.py)。`BaseMessage` 的核心职责是保存消息内容、附加字段、响应 metadata、消息类型、可选名称和 ID，并提供标准化的 `content_blocks` 视图。

### 四种主要消息

| 类型 | 谁产生 | 主要作用 |
|---|---|---|
| `SystemMessage` | 应用 / Harness | 设定角色、行为规则和全局上下文。 |
| `HumanMessage` | 用户 / 应用 | 表达用户输入，也可包含文本、图片等内容块。 |
| `AIMessage` | Chat Model | 表达模型输出；既可能包含自然语言，也可能包含 `tool_calls`。 |
| `ToolMessage` | Tool Runtime | 把工具执行结果返回给模型，并通过 `tool_call_id` 对应原请求。 |

模型返回的 `AIMessage` 不只是最终答案。[messages/ai.py](../../../submodules/langchain/libs/core/langchain_core/messages/ai.py) 中还定义了：

- `tool_calls`：成功解析的工具请求；
- `invalid_tool_calls`：参数等内容无法解析的工具请求；
- `usage_metadata`：统一后的 token usage；
- `response_metadata`：provider 相关响应信息；
- `content_blocks`：标准化后的文本、推理、工具请求等内容块。

这就是为什么 `AIMessage` 比单纯的 `str` 更适合被 Agent Runtime 解析和编排。

### Tool Call 与 Tool Result 如何配对

一个典型工具调用消息链是：

```text
HumanMessage
  ↓
AIMessage(tool_calls=[
  {name: "get_weather", args: {city: "Beijing"}, id: "call_123"}
])
  ↓
Runtime 查找并执行 get_weather
  ↓
ToolMessage(
  content="晴，28℃",
  tool_call_id="call_123"
)
  ↓
模型根据工具结果继续生成答案
```

这里有两个容易混淆的字段：

- `AIMessage.tool_calls[i].id`：模型发出的某一次工具调用请求 ID；
- `ToolMessage.tool_call_id`：工具结果声明自己正在回应哪一个请求。

它们承担的是请求—响应关联关系，因此对应同一次工具调用时值应相同。这个关联在模型一次请求多个并行 Tool Call 时尤其重要，否则 Runtime 和模型都无法判断每条结果属于哪次调用。

源码证据见 [messages/tool.py](../../../submodules/langchain/libs/core/langchain_core/messages/tool.py)：`ToolCall` 包含 `name`、`args` 和 `id`，`ToolMessage` 则要求 `tool_call_id`。

> **精髓：Tool Call ID 不是工具名字，也不是执行结果 ID；它是一条因果链上的 correlation ID。**

### `content` 与 `artifact`

`ToolMessage` 可以同时保存：

- `content`：准备返回模型上下文的内容；
- `artifact`：应用仍要保留，但不准备直接发给模型的完整产物。

例如一个搜索工具返回 100 条原始记录：

```text
content  = 给模型阅读的摘要和关键证据
artifact = 100 条原始结果、调试字段、二进制对象或完整结构化数据
```

这样设计不是因为 artifact 一定是“多余信息”，而是为了拆开两个不同需求：

1. 模型上下文需要短小、可读、与推理相关的内容；
2. 应用程序可能仍需要完整数据，用于展示、下载、后处理、审计或调试。

如果把所有原始结果都注入模型，不仅消耗 Context Window 和 token，还可能把不可信内容、内部字段或大对象带进下一轮推理。

工具可以通过 `response_format="content_and_artifact"` 返回二元组 `(content, artifact)`。相关定义见 [tools/base.py](../../../submodules/langchain/libs/core/langchain_core/tools/base.py) 和 [tools/convert.py](../../../submodules/langchain/libs/core/langchain_core/tools/convert.py)。

## Runnable：统一的执行协议

### 一句话定义

> **Runnable 是 LangChain 对“一个可执行步骤”的统一抽象：给它输入，它产生输出，并统一支持同步、异步、批处理、流式、配置传播和组合。**

源码中的定义位于 [runnables/base.py](../../../submodules/langchain/libs/core/langchain_core/runnables/base.py)。它可概括成：

```text
Runnable[Input, Output]
```

这说明 Runnable 不是某一种具体业务组件，而是一种执行协议。Prompt、Chat Model、Output Parser、Retriever、Tool，以及用普通函数包装出的步骤，都可以表现成 Runnable。

### 为什么需要统一协议

假设每个组件都有完全不同的调用方式：

```text
prompt.render(...)
model.chat(...)
retriever.search(...)
parser.parse(...)
tool.run(...)
```

应用就必须为每一种组件手写胶水代码，重试、异步、批处理、Tracing 和流式也很难统一传播。

Runnable 把这些能力收敛为共同接口：

| 方法 | 含义 |
|---|---|
| `invoke(input)` | 同步处理一个输入。 |
| `ainvoke(input)` | 异步处理一个输入。 |
| `batch(inputs)` | 批量处理多个输入。 |
| `abatch(inputs)` | 异步批处理。 |
| `stream(input)` | 流式产生输出。 |
| `astream(input)` | 异步流式产生输出。 |

所有方法还可以接收 `config`，用于传递 callbacks、tags、metadata、并发限制等运行配置。

统一接口带来的核心收益不是“少写一个函数名”，而是组合后的整条 chain 仍能作为一个新的 Runnable：它也可以 `invoke`、`batch`、`stream`、添加 retry 或被继续嵌套。

### `RunnableSequence`：前一步输出给后一步

`|` 操作符会把两个可组合对象构造成 `RunnableSequence`：

```python
chain = prompt | model | parser
result = chain.invoke({"topic": "LangChain"})
```

运行方向是：

```text
原始输入
  ↓
prompt
  ↓
model
  ↓
parser
  ↓
最终输出
```

关键约束是：**上一步的输出类型必须能被下一步接受。**

源码中的 `Runnable.__or__()` 会创建 `RunnableSequence(self, coerce_to_runnable(other))`，见 [runnables/base.py](../../../submodules/langchain/libs/core/langchain_core/runnables/base.py)。`coerce_to_runnable` 还允许普通 callable 或字典在组合时被转换成相应 Runnable。

### `RunnableParallel`：同一输入送给多个分支

`RunnableParallel` 与 Sequence 不同：它把同一个输入同时交给多个分支，并把各分支结果合并成一个字典。

```python
parallel = RunnableParallel(
    original=RunnablePassthrough(),
    upper=RunnableLambda(lambda text: text.upper()),
    length=RunnableLambda(len),
)

parallel.invoke("hello")
# {"original": "hello", "upper": "HELLO", "length": 5}
```

数据流是：

```text
               ┌─ original ─→ "hello"
"hello" ──────┼─ upper    ─→ "HELLO"  ─→ 合并成 dict
               └─ length   ─→ 5
```

这里的“并行”来自程序事先定义的 pipeline 结构，并不是由模型临时决定。不要把它和模型一次产生多个 Tool Call 混为一谈：

- `RunnableParallel`：应用代码规定哪些分支接收同一输入；
- 并行 Tool Call：模型返回多个工具请求，Runtime 决定如何调度执行。

### `RunnablePassthrough`：原样保留输入

`RunnablePassthrough` 可理解为一根直通线：输入是什么，主要输出就仍是什么。它常用于并行结构中保留原始数据。

典型 RAG pipeline 需要同时保存用户问题和检索上下文：

```python
chain = (
    {
        "question": RunnablePassthrough(),
        "context": retriever | format_documents,
    }
    | prompt
    | model
    | parser
)
```

输入问题会被复制到两个分支：

```text
question: "什么是 Runnable？"
        │
        ├─ RunnablePassthrough
        │      ↓
        │  question = 原始问题
        │
        └─ retriever → format_documents
               ↓
           context = 检索文档文本

合并为：
{
  "question": "什么是 Runnable？",
  "context": "...检索到的资料..."
}
```

如果没有 passthrough，检索分支仍可以得到输入，但后续 Prompt 未必还能同时拿到原始问题。

### `RunnableLambda`：把普通函数接入协议

`RunnableLambda` 把普通 Python callable 包装为 Runnable：

```python
format_documents = RunnableLambda(
    lambda docs: "\n\n".join(doc.page_content for doc in docs)
)
```

包装后，这个函数便能参与 `|`、Parallel、Tracing、异步适配等 Runnable 组合。

它适合轻量的数据转换；复杂业务步骤仍应使用命名清楚、可测试的函数或专门 Runnable，而不是堆叠大量匿名 lambda。

### Runnable 是执行协议，不是状态机

RunnableSequence 可以表达确定的数据管道，但它不天然等于 LangGraph 的 StateGraph。

| Runnable / LCEL | LangGraph |
|---|---|
| 主要关注输入到输出的组合。 | 主要关注共享 State、节点调度与控制流。 |
| 常见结构是顺序或并行 pipeline。 | 支持循环、条件路由、interrupt 和 subgraph。 |
| 中间值通常沿数据链传递。 | Node 返回部分 State 更新，由 reducer 合并。 |
| 不以持久化恢复为核心。 | Checkpoint 和 durable execution 是核心能力。 |

> **精髓：Runnable 更像可组合函数，LangGraph 更像有持久状态的运行时状态机。**

## Tool：带模型契约的特殊 Runnable

### 为什么所有 Tool 都是 Runnable

[tools/base.py](../../../submodules/langchain/libs/core/langchain_core/tools/base.py) 中，`BaseTool` 继承自：

```text
RunnableSerializable[str | dict | ToolCall, Any]
```

因此 Tool 具备 Runnable 的执行与组合能力，可以被 `invoke`、`ainvoke`，也可以放入更大的执行结构中。

### 为什么不是所有 Runnable 都是 Tool

普通 Runnable 只需说明“给定输入，产生输出”。但 Tool 还必须提供一份模型和 Runtime 能理解的工具契约：

| 字段 / 能力 | 作用 |
|---|---|
| `name` | 模型请求调用时使用的稳定标识。 |
| `description` | 告诉模型何时、为何使用这个工具。 |
| `args_schema` | 描述并验证结构化输入参数。 |
| `response_format` | 规定返回纯 content，还是 content + artifact。 |
| Tool Call 语义 | 接受并回应带调用 ID 的工具请求。 |
| Tool Error 语义 | 可将验证错误或执行错误转成可回流的结果。 |

一个普通的 `prompt | model | parser` chain 即使是 Runnable，也没有天然的工具名字、面向模型的用途描述和参数 schema，因此模型无法把它当成一个可选择的 Tool。

可以把两者的关系记成：

```text
Runnable = 可执行能力
Tool     = 可执行能力 + 模型可见契约 + Tool Call / Result 语义
```

### Tool 的两张脸

Tool 同时面向两个不同角色。

#### 模型看到的契约面

模型通常看到：

```text
name
+ description
+ args schema
+ 可能的 provider-specific extras
```

这些信息帮助模型决定：

- 是否调用工具；
- 调用哪个工具；
- 生成什么结构的参数。

#### Runtime 使用的执行面

Runtime 持有真正的实现，用来：

- 根据 name 找到工具；
- 验证和解析 args；
- 检查权限、审批、超时、沙箱等产品级约束；
- 调用同步或异步函数；
- 捕获错误；
- 构造对应的 `ToolMessage` 并回流。

因此，“把 Tool schema 绑定给模型”和“实际执行工具”是两个步骤。

> **模型只提出 Tool Call 请求；真正执行工具的是 Agent Runtime / Harness。**

### `@tool` 做了什么

`@tool` 装饰器位于 [tools/convert.py](../../../submodules/langchain/libs/core/langchain_core/tools/convert.py)。它能够把普通函数或合适的 Runnable 转换成 `BaseTool`，通常会：

1. 从函数名得到默认 Tool name；
2. 从显式 description 或 docstring 得到用途说明；
3. 从类型注解推导参数 schema；
4. 区分同步函数与异步函数；
5. 构造 `StructuredTool` 或简单 `Tool`；
6. 配置 `return_direct`、`response_format`、docstring parsing 和 extras。

示例：

```python
from langchain_core.tools import tool

@tool
def get_weather(city: str) -> str:
    """Get the current weather for a city."""
    return f"Weather for {city}: sunny"
```

这段代码不是让函数被模型“直接执行”。它只是建立了：

- 一份可发送给模型的工具定义；
- 一份由 Runtime 在收到匹配 Tool Call 后调用的本地实现。

### 参数验证不等于执行授权

`args_schema` 能验证类型、必填字段和结构，但不能代替：

- 当前用户是否有权限读取或写入资源；
- 文件路径是否越过 workspace boundary；
- Shell 命令是否允许执行；
- 网络目标是否在 allowlist；
- 付款、删除、发送消息等动作是否需要 HITL；
- 凭据是否按租户隔离。

这也是 LangChain Tool 抽象和产品级 Agent Harness 之间的重要边界。

## 三者如何协作

一条完整的 Tool Calling 链可以画成：

```text
1. 应用用 Message 组织模型输入
2. 应用把 Tool 的契约绑定或传给模型
3. Chat Model 返回 AIMessage
4. Runtime 检查 AIMessage.tool_calls
5. Runtime 根据 name 找到 BaseTool
6. BaseTool 校验 args 并执行真实函数
7. Runtime 生成 ToolMessage
8. ToolMessage.tool_call_id 对应原 Tool Call ID
9. ToolMessage 被追加到消息历史
10. 模型再次调用，生成最终答案或下一批 Tool Call
```

三种抽象在其中的分工是：

```text
Message 记录“发生了什么”
Runnable 统一“组件怎样被执行和组合”
Tool 规定“模型怎样请求一个外部能力”
Runtime 决定“请求是否、何时、在哪里真正执行”
```

## LCEL 数据类型练习

考虑一条典型 RAG chain：

```python
chain = (
    {
        "question": RunnablePassthrough(),
        "context": retriever | format_documents,
    }
    | prompt
    | model
    | parser
)
```

如果输入是一个字符串，数据类型大致按以下路径变化：

```text
str
  ↓ RunnableParallel
{
  "question": str,
  "context": str
}
  ↓ ChatPromptTemplate
ChatPromptValue（内部可转换为消息列表）
  ↓ ChatModel
AIMessage
  ↓ Output Parser
str 或其他解析后的业务类型
```

为什么 `RunnableParallel` 必须放在 Prompt 前？因为 Prompt 同时需要 `question` 和 `context` 两个变量。Retriever 只产生相关文档，不能替代原始问题；Parallel 先让两个分支共享输入并合并结果，再交给 Prompt 渲染。

这道题的真正考点不是记语法，而是逐步检查：

1. 当前步骤接收什么类型；
2. 它返回什么类型；
3. 下一步是否能接受该类型；
4. 哪些字段需要保留，哪些字段需要经过转换。

## 课后小测与纠偏记录

### Q1：为什么 `AIMessage` 不应简化成字符串？

**阶段性回答**：因为它还要承载 `tool_calls`、无法解析的调用、usage 和 provider metadata、结构化 content blocks 等运行时信息。字符串不足以稳定支持 Agent 编排。

### Q2：Tool Call ID 和 `ToolMessage.tool_call_id` 有什么关系？

**阶段性回答**：前者标识模型发出的某一次工具请求，后者声明工具结果回应的是哪一次请求。对应同一次调用时值相同，作用类似 correlation ID。

### Q3：多个 Tool Result 应串行还是并行返回？

**纠偏**：不能只回答“看模型请求的是串行还是并行”。模型可以一次产生多个 Tool Call，但是否并发执行还受 Runtime 能力、工具依赖、权限、副作用和并发策略影响。无论调度方式如何，每条结果都必须用正确 ID 与请求配对。

### Q4：`RunnableSequence` 会不会自动把所有步骤并行执行？

**答案**：不会。Sequence 必须让前一步完成并把输出交给后一步。需要同一输入分发到多分支时使用 `RunnableParallel`。

### Q5：`RunnablePassthrough` 的用途是什么？

**答案**：原样保留输入，常用于并行分支。RAG 中可让一支保留原问题，另一支执行检索，最后合并为 Prompt 所需字典。

### Q6：Tool 的模型契约面与 Runtime 执行面分别是什么？

**答案**：模型契约面包括 name、description、args schema 等；执行面是真实函数、参数验证、错误处理和 Runtime 调度。模型依据前者提出请求，Runtime 使用后者完成动作。

### Q7：为什么普通 Runnable 不能自动成为 Tool？

**答案**：它虽能执行，却未必有供模型发现和选择的稳定 name、description、结构化参数 schema，也不天然具备 Tool Call / Tool Result 关联语义。需要显式转换或包装。

### Q8：模型提到“请调用搜索工具”是否等于工具已执行？

**答案**：不是。只有产生可解析的 Tool Call，并被 Runtime 接受、授权和调度后，真实工具才会执行。

### Q9：参数 schema 是否足以保证 Tool 安全？

**答案**：不足。Schema 主要解决输入结构和类型问题，权限、workspace、沙箱、网络、凭据、审批和审计仍由 Runtime / Harness 负责。

### Q10：为什么要区分 `content` 与 `artifact`？

**答案**：为了分离模型上下文和应用完整产物。不是所有原始数据都适合进入模型；artifact 可供 UI、下载、后处理、审计和调试使用，同时减少上下文成本与数据暴露。

## 面试答题模板

### Runnable 是什么？

> Runnable 是 LangChain 的统一执行协议，用 `Runnable[Input, Output]` 抽象一个可调用步骤，并统一提供 invoke、ainvoke、batch、stream、配置传播和组合能力。它解决 Prompt、Model、Retriever、Parser、Tool 等组件调用方式不一致的问题。`RunnableSequence` 把前一步输出交给下一步，`RunnableParallel` 把同一输入交给多个分支并合并结果。Runnable 适合构造可复用的数据 pipeline，但它本身不是带 checkpoint、interrupt 和持久 State 的 LangGraph runtime。

### Tool 为什么是特殊 Runnable？

> BaseTool 继承 RunnableSerializable，所以 Tool 具备 Runnable 的执行能力；但 Tool 还增加 name、description、args schema、Tool Call ID、ToolMessage 和错误回流等模型调用语义。模型根据工具契约生成请求，Runtime 才负责验证权限并执行真实函数。因此所有 Tool 都是 Runnable，但普通 Runnable 只有显式补齐模型契约后才能作为 Tool。

### Tool Call 和 Tool Result 如何配对？

> 模型在 AIMessage 的 tool_calls 中产生请求，每个请求包含 name、args 和 ID。Runtime 执行工具后构造 ToolMessage，并令 `tool_call_id` 等于原 Tool Call 的 ID。这个关联在一次并行请求多个工具时用于区分每条结果。它只解决消息关联，不代表权限已通过，也不保证工具一定成功。

## 本课验收标准

完成本课后，应能不看文档画出：

```text
HumanMessage
  ↓
Chat Model
  ↓
AIMessage(tool_calls)
  ↓
Runtime
  ↓
BaseTool
  ↓
ToolMessage(tool_call_id)
  ↓
Chat Model
  ↓
Final AIMessage
```

并能解释：

- 每个对象是谁产生的；
- Runtime 在哪里介入；
- Tool Call ID 为什么必须配对；
- Sequence 和 Parallel 的数据流差异；
- Tool 相比普通 Runnable 多了什么；
- schema、执行授权和安全治理为什么是不同层。

> **本课最终精髓：模型并不直接掌握工具实现。它通过 Message 写出结构化 Tool Call；Runtime 根据 Tool 契约找到并执行一个特殊 Runnable，再用 ToolMessage 把结果接回对话因果链。**
