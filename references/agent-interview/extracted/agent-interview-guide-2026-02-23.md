# Agent Interview Guide 2026-02-23 - Mechanical Extraction

> **Source**: [`../originals/agent-interview-guide-2026-02-23.pdf`](../originals/agent-interview-guide-2026-02-23.pdf)
> **Status**: mechanically extracted with `pdftotext -layout`; not normalized or fact-checked
> **Warning**: page breaks, tables, code indentation, punctuation and line wrapping may be inaccurate. The PDF is authoritative.

---

AI Agent           算法工程师 & 开发工程师 面试八股
文（  2025-2026         最新版）
     涵盖：Agent 架构原理、前沿论文、工程实现、Python 编程、框架实战、RAG/MCP/A2A 协议、
     安全对齐、部署运维等全方位面试题。


目录
      第一章 AI Agent 核心概念与架构
      第二章 Agent 主流框架深度解析
      第三章 Tool Use / Function Calling 机制
      第四章 MCP 协议与 A2A 协议（2025 最新）
      第五章 RAG 检索增强生成（前沿进展）
      第六章 多智能体系统（Multi-Agent）
      第七章 Agent 记忆系统
      第八章 Agent 科研前沿（论文 & 算法）
      第九章 Python Agent 工程实战
      第十章 Agent 评估基准与可观测性
      第十一章 Agent 安全、对齐与 Guardrails
      第十二章 Agent 部署与成本优化
      第十三章 高频综合面试题精选


第一章 AI Agent 核心概念与架构
1.1   什么是 AI Agent？与普通 LLM 应用的本质区别
Q: 请定义 AI Agent 并说明它与普通 LLM 应用（如 ChatGPT 聊天）的本质区别。
AI Agent 是一个能够自主感知环境 → 做出决策 → 采取行动 → 观察反馈 → 循环迭代以实现特定目标的
AI 系统。


---

    维度            普通 LLM 应用                           AI Agent

 执行模式 单轮请求-响应                     多步循环 (Action-Observation Loop)
 自主性          被动响应用户输入            主动规划、自主决策下一步
 工具使用 无或有限                        可调用外部工具扩展能力边界
 环境交互 仅文本输入输出                     与外部环境双向交互（API、文件系统、浏览器等）
 目标驱动 完成单次回答                      以完成复杂目标为导向
 状态管理 无状态或简单上下文 维护跨步骤的状态和记忆
核心公式：Agent = LLM + Memory + Planning + Tool Use + Action Loop
吴恩达（Andrew Ng）在 2024 年总结的四种 Agentic Design Patterns：
 1. Reflection：自我反思与修正
 2. Tool Use：工具调用
 3. Planning：任务规划与分解
 4. Multi-Agent Collaboration：多智能体协作




1.2 ReAct   （Reasoning + Acting）
Q:详细解释 ReAct 模式的工作原理、优势与局限性。
由 Yao et al. (2022) 提出，将推理（Reasoning） 和行动（Acting） 交错进行。
执行流程：
 用户问题 → Thought(思考) → Action(调用工具) → Observation(观察结果) → Thought → Action → ... → Fin


示例：


---

 Question: 特斯拉2024年Q4的营收是多少？


 Thought: 我需要搜索特斯拉最新财报数据
 Action: search("特斯拉 2024 Q4 财报 营收")
 Observation: 特斯拉2024年第四季度营收为257.07亿美元...


 Thought: 我已经找到了答案
 Final Answer: 特斯拉2024年Q4营收为257.07亿美元。


优势：
  相比纯 CoT，可通过 Action 获取外部真实信息，减少幻觉
  推理过程可解释，便于调试
  灵活适应多种任务场景
局限性：
  顺序执行效率较低，无法并行
  缺乏全局规划，可能陷入局部最优或死循环
  对 LLM 的工具选择能力依赖度高
  没有显式回溯机制，一旦走错路难以纠正


1.3 Plan-and-Execute       （计划与执行）
Q: Plan-and-Execute   与 ReAct 的核心区别是什么？什么场景该用哪个？
架构：
 用户任务 → Planner(生成子任务列表) → Executor(逐步执行)
              ↑                        |
              └── Replanner(根据结果调整计划) ←┘



    维度                      ReAct                 Plan-and-Execute

 决策方式                 每步即时决策                先全局规划再执行
 全局视野                 弱，只看当前步               强，有全局任务分解
 灵活性                  高，实时调整                中，需 Replan 触发调整


---

      维度             ReAct                Plan-and-Execute

 适用场景          简单多步任务、实时交互       复杂长链任务、项目级工作
 Token 消耗      较少                较多（规划本身消耗 token）
Replanning 触发条件：

 1. 子任务执行失败
 2. 获取到与预期不符的信息
 3. 发现原计划不完善需要补充步骤
 4. 发现更优路径




               （
1.4 LATS Language Agent Tree Search   ）
Q: LATS  如何将蒙特卡洛树搜索应用到 Agent 决策中？
LATS 将 Agent 的决策过程建模为树搜索问题，结合 MCTS 的四步循环：

  1. Selection（选择）：用 UCT 策略从根节点选择最有前景的节点
  2. Expansion（扩展）  ：LLM 生成可能的下一步动作，创建子节点
  3. Evaluation（评估） ：LLM 自我评估当前状态的价值或获取环境反馈
  4. Backpropagation（回传） ：将评估结果传播回父节点，更新统计信息
相比 ReAct 的改进： ReAct 是单路径探索，一旦犯错难以回溯。LATS 探索多条路径，能回溯到之前
的状态尝试不同策略。但计算成本显著增加（需要多次 LLM 调用）。
适用场景： 复杂推理任务、代码生成（需要多次尝试）、博弈决策。


1.5 Reflexion      （自我反思）
Q: Reflexion  如何实现"不更新权重的学习"？
由 Shinn et al. (2023) 提出。
工作流程：


---

 Task → Actor(执行) → Evaluator(评估) → Self-Reflection(生成反思)
                                         ↓
                                  Memory(存储反思文本)
                                         ↓
                                  Actor(利用反思重新执行) → ...


核心机制： 将自我反思结果以自然语言形式存储在情景记忆（Episodic Memory）中，在后续尝试中将
这些反思作为 prompt 的一部分提供给 LLM。这是一种 in-context learning 的方式，不需要微调模型
参数。
反思示例：
 [第1次尝试] 我直接搜索了完整问题，得到的结果不相关。
 [反思] 下次应该将问题分解为子问题，逐步搜索。
 [第2次尝试] 成功——将问题分解后逐步查找。




1.6   其他重要架构
            架构                    核心思想                           特点
 Self-Ask                 将问题分解为子问题逐一回答                     适合多跳推理
 AutoGPT    式自主循环         设定目标后完全自主运行                       高自主性，但可控性差
 Cognitive Architecture   模拟人类认知（感知→记忆→推理→行动）               学术前沿
 OpenAI Deep Research     长时间自主研究型 Agent                    多轮搜索分析生成报告


1.7   如何选择 Agent 架构？
Q:   给定一个具体任务，如何选择合适的 Agent 架构？


---

 简单工具调用         → 基础 Function Calling Agent
 需要多步推理         → ReAct
 复杂任务需要全局规划     → Plan-and-Execute
 需要高质量决策/回溯     → LATS (Tree Search)
 需要从失败中学习       → Reflexion
 需要多角色协作        → Multi-Agent (CrewAI / AutoGen / LangGraph)
 需要精细流程控制       → LangGraph 自定义 StateGraph




第二章 Agent 主流框架深度解析
2.1 LangGraph   （LangChain 团队）
Q: LangGraph的核心抽象是什么？相比 LangChain AgentExecutor 有什么优势？
基于有向图（Directed Graph） 的 Agent 编排框架。
核心概念：
  State：全局状态对象，在节点间传递（TypedDict 或 Pydantic Model）
  Node：图中的计算节点，接收 State 返回更新
  Edge：连接节点的边，决定执行流程
  Conditional Edge：根据状态动态选择下一个节点
  Reducer：定义状态合并策略（如 add_messages 追加消息列表）
  Checkpointer：状态持久化，支持断点续跑
  Human-in-the-Loop：关键节点暂停等待人类确认

代码示例：


---

from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    iteration_count: int


def call_model(state: AgentState):
    response = llm.invoke(state["messages"])
    return {"messages": [response], "iteration_count": state["iteration_count"] + 1}


def should_continue(state: AgentState) -> str:
    last = state["messages"][-1]
    if last.tool_calls:
        return "tools"
    return END


graph = StateGraph(AgentState)
graph.add_node("agent", call_model)
graph.add_node("tools", tool_node)
graph.add_edge(START, "agent")
graph.add_conditional_edges("agent", should_continue)
graph.add_edge("tools", "agent")


# 编译时加入持久化和人机交互
app = graph.compile(
    checkpointer=MemorySaver(),
    interrupt_before=["tools"]    # 工具执行前暂停等人类确认
)


相比 AgentExecutor 的优势：
 1. 任意复杂的图拓扑（条件分支、循环、并行）
 2. 内置状态持久化 → 支持长时间运行任务
 3. Human-in-the-Loop 原生支持
 4. 更好的可观测性和调试能力
 5. 支持多 Agent 协作编排


---

2.2 OpenAI Agents SDK                 （2025.3 发布）
Q: OpenAI Agents SDK的四大原语是什么？Handoff 机制如何工作？
替代了之前的 Swarm 实验项目，面向生产级部署。
四大原语：
 1. Agent：指令 + 模型 + 工具 + 可选 Guardrails
 2. Handoff：Agent 间任务转交（类似客服"转接"）
 3. Guardrails：输入/输出验证和安全护栏
 4. Tracing：内置追踪和可观测性


 from agents import Agent, Runner, function_tool, handoff


 @function_tool
 def search_knowledge_base(query: str) -> str:
     """搜索内部知识库"""
     return vector_db.search(query, top_k=5)


 billing_agent = Agent(
     name="Billing Agent",
     instructions="处理账单和退款问题。",
     model="gpt-4o",
     tools=[search_knowledge_base],
 )


 triage_agent = Agent(
     name="Triage Agent",
     instructions="根据问题类型转给合适的专家。",
     handoffs=[handoff(billing_agent, description="账单和付款问题")],
 )


 result = await Runner.run(triage_agent, "我的账单多扣了钱")


Handoff  底层原理： Handoff 注册为特殊 function tool → LLM 决定调用 → Runner 检测到并切换
active agent → 消息历史完整传递给新 Agent。


---

2.3 CrewAI
        的核心抽象和多 Agent 协作模式是什么？
Q: CrewAI

专注于角色扮演式多智能体协作。
核心抽象：
  Agent：角色（role）+ 目标（goal）+ 背景故事（backstory）
  Task：任务定义 + 预期输出 + 指定 Agent
  Crew：团队编排 + 执行流程
  Process：Sequential（顺序）/ Hierarchical（层次化，有 Manager Agent）


 from crewai import Agent, Task, Crew, Process


 researcher = Agent(
     role="市场研究员",
     goal="收集AI Agent市场最新趋势数据",
     backstory="你是一位资深市场分析师...",
     tools=[search_tool, web_scraper],
 )


 writer = Agent(
     role="技术作家",
     goal="将研究结果整理成专业报告",
     backstory="你擅长将复杂技术概念转化为易懂文字...",
 )


 research_task = Task(description="调研2025年AI Agent市场", agent=researcher)
 write_task = Task(description="撰写市场报告", agent=writer)


 crew = Crew(
     agents=[researcher, writer],
     tasks=[research_task, write_task],
     process=Process.sequential,
 )
 result = crew.kickoff()


---

2.4 AutoGen      （微软）
            的重大重构有哪些变化？
Q: AutoGen 0.4

   事件驱动架构（Event-Driven Architecture）
   更好的可扩展性和模块化
   支持自定义 Agent runtime
   核心概念：ConversableAgent、GroupChat、GroupChatManager
与 CrewAI 的区别： CrewAI 更注重角色扮演和任务流程编排（像组建团队）；AutoGen 更注重 Agent
间的对话和消息传递（像多方会议）。


2.5 Google ADK       （Agent Development Kit）
2025   年 Google 开源的 Agent 开发框架，内置支持 MCP 和 A2A 协议，深度集成 Gemini 模型。


2.6    框架选型指南
           框架                    最佳场景            学习曲线     生产就绪度
 LangGraph             复杂自定义工作流、需要精细控制           中高       高
 OpenAI Agents SDK     OpenAI 生态、快速构建            低        高
 CrewAI                多角色协作、任务流编排               低        中高
 AutoGen               多 Agent 对话、研究探索           中        中
 Google ADK            Google 生态、A2A 互操作         中        中高
 Dify/Coze             低代码/无代码快速原型               极低       中


---

第三章 Tool Use / Function Calling 机制
3.1 Function Calling                 工作原理
Q: Function Calling     是 prompt 工程还是模型训练的结果？
完整工作流程：
 1. 开发者定义工具 schema (JSON Schema)
 2. LLM 判断是否需要调用工具
 3. 如需要，LLM 输出结构化工具调用请求 (name + arguments)
 4. 应用层实际执行工具调用
 5. 将工具结果返回给 LLM
 6. LLM 基于结果生成最终响应（或继续调用工具）


回答： 现代主流模型（GPT-4o、Claude Sonnet/Opus 4 等）都经过专门的 tool use 训练。底层实现
上，tool schema 会被转化为特殊格式注入系统 prompt，但模型对这种格式的理解和生成能力是通过训
练获得的，不仅仅是简单的 prompt 工程。


3.2 OpenAI vs Anthropic                   工具定义格式对比
OpenAI    ：
 {
     "tools": [{
      "type": "function",
      "function": {
          "name": "get_weather",
          "description": "获取城市天气",
          "parameters": {
              "type": "object",
              "properties": {"city": {"type": "string"}},
              "required": ["city"]
          }
      }
     }]
 }


Anthropic     ：


---

 {
     "tools": [{
      "name": "get_weather",
      "description": "获取城市天气",
      "input_schema": {
          "type": "object",
          "properties": {"city": {"type": "string"}},
          "required": ["city"]
      }
     }]
 }



      差异项                              OpenAI                     Anthropic

 Schema 字段名               parameters                    input_schema

 停止原因                     finish_reason: "tool_calls"   stop_reason: "tool_use"

 结果返回方式                   tool role   独立消息              tool_result    在 user 消息中
 并行调用                     parallel_tool_calls   参数      默认支持


3.3   提升 Function Calling 准确性的技巧
Q:工具太多导致 LLM 选错工具怎么办？
 1. 写清晰的工具描述：description 要明确说明何时使用该工具
 2. 控制工具数量：单次请求 < 20 个工具，太多用工具路由分组
 3. 使用 enum 限制参数值：减少参数填写错误
 4. 设置 tool_choice ：强制或引导工具选择
 5. 工具分组 / 路由：先用小模型判断类别，再加载对应工具集
 6. 在 system prompt 中给出工具使用指南和示例




3.4   工具调用失败处理策略
Q:   工具调用失败了怎么办？


---

 async def execute_tool_with_retry(tool_call, max_retries=3):
     for attempt in range(max_retries):
         try:
             result = await execute_tool(tool_call)
             return {"type": "tool_result", "tool_use_id": tool_call.id, "content": result}
         except RateLimitError:
             await asyncio.sleep(2 ** attempt)   # 指数退避
         except ToolExecutionError as e:
             # 将错误信息返回给 LLM，让它决定下一步
             return {
                  "type": "tool_result",
                  "tool_use_id": tool_call.id,
                  "content": f"工具执行失败: {str(e)}",
                  "is_error": True
             }
     return {"type": "tool_result", "tool_use_id": tool_call.id,
             "content": "工具在多次重试后仍然失败", "is_error": True}


关键原则： 将错误信息返回给 LLM，让 LLM 决定是重试、换工具、还是告知用户。


第四章 MCP 协议与 A2A 协议（2025 最新）
           （
4.1 MCP Model Context Protocol                    ）
Q: MCP  是什么？它解决了什么问题？
Anthropic 于 2024.11 发布的开放协议，为 LLM 应用提供连接外部数据源和工具的统一标准。

类比：MCP 之于 AI 应用 = USB-C 之于硬件设备
解决的核心问题： M 个 AI 应用 × N 个外部服务 = M×N 个集成。有了 MCP 只需 M+N 个实现。
架构：
 Host (Claude Desktop / Cursor / VS Code)
   └── MCP Client（维护连接）
         └── MCP Server（暴露能力）
                 └── External Resource（GitHub / 数据库 / 文件系统）


---

三种能力（Primitives）：
   Primitive                 控制方                   用途                   示例
 Tools             Model-controlled         LLM 自主决定何时调用          执行 SQL、发送邮件
 Resources         Application-controlled   应用决定何时加载              文件内容、配置信息
 Prompts           User-controlled          用户显式触发                预定义交互模板


4.2 MCP 2025           年重大更新
Q: MCP在 2025 年有哪些关键更新？
   时间               更新                                             内容
 2025.03       Streamable HTTP Transport              替代 SSE，支持 Lambda/无服务器部署
 2025.06       OAuth 2.1   授权 + Elicitation + 结构化输出   生产级安全、服务器主动请求用户输入
 2025.09       MCP Registry                           开放目录，2000+ 服务器条目
 2025.11       Tasks Primitive   （1周年大更新）             异步长时任务、进度推送、工作流编排
 2025.12  捐赠给 Linux Foundation (AAIF)                 Anthropic + OpenAI + Block 共建

生态数据（截至 2025 底）：
  月 SDK 下载量 9700 万+
  10,000+ 活跃 MCP Server
  ChatGPT、Claude、Cursor、Gemini、VS Code、Copilot 全部支持




4.3 MCP Transport                层
Q: stdio   和 Streamable HTTP 两种 Transport 各适用什么场景？
      Transport                  适用场景                         特点
 stdio                     本地 MCP Server（子进程）         简单、低延迟、无需网络


---

     Transport            适用场景                    特点
 Streamable HTTP   远程/云端 MCP Server       支持鉴权、可部署在 Lambda/Cloud Run


4.4 A2A   协议（Google Agent2Agent）
Q: A2A 和 MCP 有什么区别？它们是互补还是竞争关系？
Google 于 2025.4 发布，50+ 合作伙伴共建。2025.6 捐赠给 Linux Foundation。

核心区别：
    维度                    MCP                    A2A

 定位           Agent ↔ 工具/数据 的标准接口 Agent ↔ Agent 的通信协议

 通信对象 工具是结构化 I/O，被动执行             Agent 是自主的，能推理和决策

 类比           人使用工具（锤子、搜索引擎）      人与人之间的协作沟通
 协议基础 JSON-RPC over stdio/HTTP    HTTP + SSE + JSON-RPC

关系：互补而非竞争。 一个完整的 Agentic 应用可能同时使用 MCP（连接工具和数据）和 A2A
（Agent 间协作）。
A2A 核心概念：

   Agent Card：Agent 的"名片"，描述能力和接口
   Task：Agent 间协作的基本单元
   Message / Part：通信的消息格式，支持多模态




第五章 RAG 检索增强生成（前沿进展）
5.1 RAG    基础流程
 文档处理: 加载 → 分块(Chunking) → 嵌入(Embedding) → 存入向量数据库
 查询处理: 用户查询 → 查询改写 → 检索 → 重排序(Reranking) → 生成回答


---

5.2 RAG   演进：Naive → Advanced → Agentic
Q:什么是 Agentic RAG？与传统 RAG 有何区别？
       阶段                        特点                局限
 Naive RAG      简单 embed→retrieve→generate    检索质量差、幻觉多
 Advanced RAG   查询改写 + 混合搜索 + 重排序             流程固定，不能自适应
 Agentic RAG    Agent 自主决定何时检索、如何改写、从哪检索      成本较高
Agentic RAG 的核心改进：

   Agent 可以动态决定是否需要检索（不是每个问题都需要）
   检索失败时自动调整策略（换关键词、换数据源）
   支持多轮检索和推理（先检索背景知识，再检索细节）
   可以跨多个数据源路由检索


5.3 Graph RAG  （微软）
           解决了传统 RAG 的什么问题？
Q: Graph RAG

传统 RAG 擅长回答具体细节问题（如"X 的定义是什么？"），但对全局性/总结性问题（如"数据集的主
要主题有哪些？"）表现差。
Graph RAG 流程：


 文档 → LLM 提取实体和关系 → 构建知识图谱 → 社区检测(Leiden算法)
 → 为每个社区生成摘要 → 查询时汇总相关社区摘要 → 生成回答


优势： 在全局性问题上显著优于传统向量 RAG。
代价： 索引构建成本高（大量 LLM 调用），图谱维护复杂。


---

5.4    其他前沿 RAG 技术
               技术                       核心思想                       场景
                               LLM 自我反思决定何时检索，生成反思
 Self-RAG
                               token
                                                             按需检索，避免冗余
 CRAG (Corrective RAG)         评估检索质量，质量差时用网络搜索补充            提升鲁棒性
 Contextual Retrieval
                               为每个 chunk 添加上下文描述前缀           解决 chunk
 (Anthropic)                                                 上下文丢失
 Late Chunking
                               先长上下文编码整个文档，再切分               保留全局语义
                               embedding

                               先让 LLM 生成假设性回答，用其             短查询增强
                               embedding 检索
 HyDE




5.5    分块策略（Chunking）
Q:不同分块策略的优缺点？
    策略               方法                         优点                 缺点
 固定大小     按字符/token 数                      简单               可能割裂语义
 递归分块     按分隔符层次切分                         平衡效果好            需要调参
 语义分块     基于 embedding 相似度                 语义完整             计算成本高
 文档结构     按标题/段落/章节                        保持结构             依赖文档格式
最佳实践： 大多数场景用 RecursiveCharacterTextSplitter ，chunk_size=512，overlap=50-100。


5.6 Embedding           模型与向量数据库选型
2025   主流 Embedding 模型：
     OpenAI: text-embedding-3-small/large
     Cohere: embed-v3


---

   开源: BGE-M3 、 Jina Embedding v3 、 GTE-Qwen2
向量数据库选型：
       数据库                   类型                 规模             最佳场景
 Milvus/Zilliz        开源分布式                  10亿+      大规模生产
 Pinecone             全托管 SaaS               10亿+      快速上线
 Qdrant               开源                     千万级       高性能、Rust 实现
 Weaviate             开源                     千万级       语义搜索、GraphQL
 ChromaDB             开源轻量                   百万级       原型/小项目
 pgvector             PG 扩展                  千万级       已有 PostgreSQL


5.7 RAG    评估
Q:   如何评估 RAG 系统的质量？RAGAS 评估框架有哪些指标？
            指标                              含义
 Faithfulness                 回答是否忠实于检索到的上下文（不编造）
 Answer Relevancy             回答是否与问题相关
 Context Precision            检索到的内容中相关内容占比
 Context Recall               是否检索到了所有需要的相关内容


5.8 RAG vs        长上下文 vs 微调
Q:这三种方式如何选择？
   方案           适用场景                                    优势         劣势
 RAG    知识更新频繁、数据量大、需要引用来源                           实时性、可追溯    检索质量瓶颈
 长上下文 数据量不大、需同时理解全部信息                                简单直接       成本高、有上限


---

  方案           适用场景               优势         劣势
 微调    需要改变模型行为/风格、领域适配       深度定制        数据准备成本高
实际中往往组合使用。 长上下文模型的出现并没有取代 RAG，因为 RAG 在大规模知识库、成本控
制、可追溯性方面仍有优势。


第六章 多智能体系统（Multi-Agent）
6.1   多 Agent 架构模式
Q:   列举并解释常见的多 Agent 协作模式。
         模式                       描述              典型应用
 流水线 (Pipeline)       顺序执行，前者输出 = 后者输入         内容创作流水线
 层次化 (Hierarchical)   主管 Agent 分配任务、汇总结果       客服系统、项目管理
 协作 (Collaborative)   多 Agent 互相配合完成任务         代码开发 (写/审/测)
 辩论 (Debate)          多 Agent 给出不同观点，辩论达成共识    决策分析、推理增强
 网状 (Mesh)            自由通信，无固定拓扑               AutoGen GroupChat

 路由 (Router)          一个路由 Agent 分发给专家 Agent   客服分流


6.2   多 Agent 的优势与劣势
 什么时候该用多 Agent？什么时候单 Agent 更好？
Q:

优势：
  任务分解，每个 Agent 专注特定领域
  可并行执行提高效率
  通过辩论/审查提升质量
  更好的可扩展性
劣势：


---

  通信开销大，token 消耗显著增加
  协调复杂度高，可能出现死循环
  错误传播风险
  调试困难
经验法则： 如果单 Agent 能在 5-10 步内完成，优先用单 Agent。任务确实需要不同专业能力或并行处
理时才用多 Agent。


6.3   防止多 Agent 死循环
Q:多 Agent 系统如何防止无限循环？
 1. 设置最大迭代/对话轮次
 2. 引入终止条件判断（如任务完成检测 Agent）
 3. 设置超时机制
 4. 使用状态追踪检测循环模式
 5. 引入裁判 Agent 决定何时终止
 6. 指数退避：连续相似输出时增加终止概率




第七章 Agent 记忆系统
7.1   记忆类型分类
Q: Agent   的记忆系统有哪些类型？分别如何实现？
   类型                       描述                      实现方式
 短期记忆          当前会话的上下文（context window）   消息历史列表
 长期记忆          跨会话持久化信息                   向量数据库 / KV 存储
 情景记忆          Agent 过去的"经历"（成功/失败经验）     结构化存储 + 检索
 语义记忆          事实性知识和概念                   知识图谱 / RAG
 程序性记忆         "如何做"的知识                   Prompt / 工具定义 / SOP


---

7.2   上下文窗口管理策略
Q:上下文窗口有限，长对话怎么处理？
        策略                 方法                       适用场景
 滑动窗口        保留最近 N 条消息                           简单对话
 Token 截断    超限时截断旧消息                             通用
 对话摘要        LLM 定期总结历史                           长对话
 分层记忆        最近完整 + 较远摘要 + 更远检索                   复杂场景
 RAG 式检索     存入向量库按需检索                            海量历史


7.3 MemGPT / Letta
Q: MemGPT的核心思路是什么？
将操作系统虚拟内存管理思想应用到 LLM Agent：
  上下文窗口 = "主存"（有限）
  外部存储 = "磁盘"（无限）
  Agent 主动执行"内存管理"：将不重要信息"换出"（page out）
                                      ，需要时"换入"（page in）
  使得 Agent 能管理远超上下文窗口大小的信息


第八章 Agent 科研前沿（论文 & 算法）
8.1   推理增强（Reasoning）
Q:   当前 LLM 推理能力增强的主要方法有哪些？
          方法                           代表       核心思想
 Chain-of-Thought    Wei et al. 2022        分步推理
 Tree-of-Thought     Yao et al. 2023        树状探索多条推理路径


---

            方法                                代表                     核心思想
 Graph-of-Thought             Besta et al. 2023                  图结构推理，允许合并
 Reasoning Models             OpenAI o1/o3, DeepSeek-R1          训练时学会"慢思考"
 Extended Thinking            Claude Sonnet/Opus 4               可控的内部推理预算
DeepSeek-R1  关键创新：
    通过纯 RL（强化学习）训练出推理能力，无需监督数据
    训练过程中自发涌现了 Chain-of-Thought 行为
    开源模型中推理能力最强之一
    蒸馏技术：将大模型的推理能力蒸馏到小模型
Extended Thinking（Claude）的 Agent 应用：


 response = client.messages.create(
      model="claude-sonnet-4-20250514",
      max_tokens=16000,
      thinking={"type": "enabled", "budget_tokens": 10000},
      messages=[{"role": "user", "content": "分析这段代码的安全漏洞..."}]
 )
 # thinking block 包含内部推理过程
 # text block 包含最终回答




8.2   代码生成 Agent
Q:   当前代码 Agent 的前沿发展如何？
            Agent                     来源                           特点
 Devin                          Cognition          首个"AI 软件工程师"，全自主开发
 Claude Code                    Anthropic          CLI 工具，终端内 agentic coding

 OpenHands                      开源                 原 OpenDevin，开源代码 Agent
 Codex Agent                    OpenAI             云端异步代码 Agent
 Cursor / Windsurf              商业                 IDE 内集成的 AI Agent


---

SWE-bench  指标： 评估 Agent 自动修复真实 GitHub issue 的能力。2025 年顶级系统在 SWE-bench
Verified 上得分已超过 50%。




8.3 Computer Use / GUI Agent
Q:什么是 Computer Use Agent？技术原理是什么？
让 AI Agent 像人类一样操作计算机 GUI（截图 → 理解 → 生成鼠标/键盘操作）。
技术流程：
 截屏 → 多模态 LLM 理解界面 → 生成操作指令(点击坐标/输入文字)
     ↑                                       ↓
     └──────── 执行操作并再次截屏 ←────────────┘


代表工作：
     Claude Computer Use（Anthropic）
     WebArena / VisualWebArena（学术基准）
     Browser Use / Playwright Agent




8.4      重要论文清单
                 论文                    年份                      核心贡献
 ReAct                                2022       推理+行动交错模式
 Reflexion                            2023       语言反思实现无梯度学习
 LATS                                 2023       树搜索与 Agent 结合
 Voyager                              2023       Minecraft 中的终身学习 Agent

 AutoGen                              2023       多 Agent 对话框架
 Graph RAG                            2024       知识图谱增强的 RAG
 SWE-Agent                            2024       软件工程 Agent
 OpenHands                            2024       开源代码 Agent 平台


---

                 论文          年份                   核心贡献
 MCP Spec                   2024   工具连接标准协议
 A2A Spec                   2025   Agent 间通信标准

 DeepSeek-R1                2025   RL 训练推理能力

 Agent Survey (Xi et al.)   2025   LLM Agent 综述




8.5 Agent      学习方法
Q: Agent 如何"学习"？有哪些方法？
             方法                     描述                   是否更新权重
 In-Context Learning  通过 prompt 中的示例学习               否
 Reflexion            通过反思记忆学习                       否
 微调 (Fine-tuning)     在 tool use 数据上微调               是
 RLHF / DPO           通过人类偏好强化学习                     是
 经验回放                 存储成功轨迹用于后续参考                   否


第九章 Python Agent 工程实战
9.1   异步编程基础
Q:为什么 Agent 开发大量使用 async/await？
Agent 的核心操作（LLM API 调用、工具执行、数据检索）都是 I/O 密集型。asyncio 的单线程协作式
并发完美适配：


---

 import asyncio


 async def agent_step(tools_to_call: list):
      """并行执行多个工具调用"""
      async with asyncio.TaskGroup() as tg:   # Python 3.11+
          tasks = {tool.name: tg.create_task(execute_tool(tool)) for tool in tools_to_call}
      return {name: task.result() for name, task in tasks.items()}



          概念                            定义                                      用途
 协程                      async def 定义的函数                                  定义异步逻辑
 Task                    对协程的封装，被事件循环调度                                   并发执行
 Semaphore               信号量，限制并发数                                        控制 API 并发
 gather                  等待多个协程同时完成                                       并行调用
 TaskGroup               结构化并发（3.11+）                                     更安全的并行


9.2   并发控制与限流
Q:   如何实现 API 调用的速率限制？
 class RateLimitedLLMClient:
      def __init__(self, rpm: int = 60, tpm: int = 100000):
          self.rpm_semaphore = asyncio.Semaphore(rpm)
          self.token_bucket = TokenBucket(tpm)


      async def call(self, messages, **kwargs):
          async with self.rpm_semaphore:
               await self.token_bucket.acquire(estimated_tokens)
               for attempt in range(3):
                  try:
                      return await self._raw_call(messages, **kwargs)
                  except RateLimitError:
                      wait = 2 ** attempt + random.uniform(0, 1)
                      await asyncio.sleep(wait)
               raise MaxRetriesExceeded()


---

9.3 Agentic Loop             实现（Anthropic 风格）
Q:   手写一个完整的 Agent Loop。
 import anthropic


 async def agent_loop(client, system_prompt, user_message, tools, max_steps=10):
      messages = [{"role": "user", "content": user_message}]


      for step in range(max_steps):
         response = await client.messages.create(
              model="claude-sonnet-4-20250514",
              system=system_prompt,
              max_tokens=4096,
              tools=tools,
              messages=messages,
          )


          # 收集 assistant 的回复
         messages.append({"role": "assistant", "content": response.content})


          # 检查是否需要调用工具
          if response.stop_reason == "tool_use":
              tool_results = []
              for block in response.content:
                  if block.type == "tool_use":
                     result = await execute_tool(block.name, block.input)
                     tool_results.append({
                          "type": "tool_result",
                          "tool_use_id": block.id,
                          "content": str(result)
                     })
              messages.append({"role": "user", "content": tool_results})
          else:
              # 模型结束，返回最终文本
              return next(b.text for b in response.content if b.type == "text")


      return "达到最大步数限制"


---

9.4   流式响应处理
Q:   如何实现 Agent 的流式输出？
 # Anthropic 流式 + 工具调用
 async def stream_agent(client, messages, tools):
      async with client.messages.stream(
          model="claude-sonnet-4-20250514",
          max_tokens=4096,
          tools=tools,
          messages=messages,
      ) as stream:
          async for event in stream:
              if event.type == "content_block_delta":
                 if event.delta.type == "text_delta":
                     yield {"type": "text", "content": event.delta.text}
              elif event.type == "message_stop":
                 message = await stream.get_final_message()
                 if message.stop_reason == "tool_use":
                     yield {"type": "tool_call", "content": message.content}




9.5 Python GIL           对 Agent 并发的影响
Q: GIL   对 Agent 开发有什么影响？如何绕过？
                 场景                                           推荐方案                原因
 LLM API 调用（I/O 密集）                                asyncio                     无 GIL 影响
 文档解析/Embedding 计算（CPU 密集）                          ProcessPoolExecutor        绕过 GIL
 调用阻塞同步库                                            ThreadPoolExecutor         兼容性
 混合场景                                              asyncio + run_in_executor   最佳组合


---

 import asyncio
 from concurrent.futures import ProcessPoolExecutor


 async def hybrid_agent():
     loop = asyncio.get_running_loop()
     # CPU 密集任务放进程池
     embeddings = await loop.run_in_executor(
         ProcessPoolExecutor(), compute_embeddings, documents
     )
     # I/O 密集直接异步
     llm_response = await async_llm_call(prompt)


      新特性： 实验性 Free-threaded 模式（ python3.13t ）移除 GIL，CPU 密集 Agent 任务可
Python 3.13
直接用多线程。


9.6 Pydantic      在 Agent 中的应用
Q: Pydantic   在 Agent 开发中有哪些关键用途？


---

 from pydantic import BaseModel, Field
 from typing import Literal


 # 1. 结构化输出验证
 class AgentAction(BaseModel):
    thought: str = Field(description="推理过程")
    action: Literal["search", "calculate", "answer"] = Field(description="动作类型")
    action_input: str = Field(description="动作参数")


 # 2. 工具参数定义
 class SearchParams(BaseModel):
    query: str = Field(description="搜索关键词")
    max_results: int = Field(default=5, ge=1, le=20)


 # 3. Agent State 定义
 class ConversationState(BaseModel):
    messages: list[dict]
    tool_results: list[str] = []
    iteration: int = 0


     class Config:
        arbitrary_types_allowed = True




第十章 Agent 评估基准与可观测性
10.1   主要基准测试
             基准                               评估内容                       2025   最高水平
 SWE-bench Verified                自动修复 GitHub issue                  >50%

 GAIA                              多步推理 + 工具使用                        Level 3   仍很难
 WebArena                          网页环境操作                             ~40%

 AgentBench                        8 种环境综合评估                          持续提升
 HumanEval                         代码生成                               >95%

 TAU-bench                         Tool-Agent-User 交互可靠性              新兴基准


---

10.2 Agent    评估维度
Q:如何全面评估一个 Agent 系统？
      维度                                指标
 功能性              任务完成率、正确性
 效率               步骤数、Token 消耗、延迟
 安全性              是否遵守安全限制
 可靠性              重复执行结果一致性
 成本               API 调用费用

 用户体验             响应速度、交互自然度


10.3 LLM-as-Judge
           评估方法的优缺点？
Q: LLM-as-Judge

优点： 成本低、可大规模自动化、能评估开放式问题。
缺点：
  偏好偏差（偏好更长回答）
  自我偏好（对自身模型输出评分更高）
  位置偏差（偏好第一个/最后一个答案）
缓解方法： 多 Judge 投票、随机化顺序、标注数据校准、使用不同模型做 Judge。


10.4   可观测性（Observability）
      的 Tracing 和 Observability 如何实现？
Q: Agent

工具生态：
  LangSmith：LangChain 官方，trace 可视化


---

               ：开源 LLM 可观测性
     Phoenix (Arize)
  Braintrust：评估 + 监控
  OpenTelemetry：通用可观测性标准

关键数据： 每步延迟、Token 使用量、工具调用成功率、错误率、决策路径。


第十一章 Agent 安全、对齐与 Guardrails
11.1   核心安全威胁
Q: Agent   系统面临的主要安全威胁有哪些？
              威胁                     描述          危险程度
 直接 Prompt Injection   用户输入中嵌入恶意指令              高
 间接 Prompt Injection   恶意指令隐藏在 Agent 检索的外部数据中   极高
 Tool Abuse            Agent 执行超出预期的工具操作        高
 Data Exfiltration     Agent 通过工具泄露敏感信息         高
 Denial of Wallet      恶意触发大量 API 调用耗尽预算        中


11.2   间接 Prompt Injection 防御
Q:什么是间接 Prompt Injection？如何防御？
恶意指令不在用户输入中，而隐藏在 Agent 检索/读取的外部数据中（网页、文档、邮件）。当 Agent 处
理这些数据时，恶意指令可能被执行。
防御措施：
 1. 数据/指令分离：对外部数据加标记，明确区分数据和指令
 2. 独立检测：用独立 LLM 调用检测可疑内容
 3. 权限隔离：处理外部数据后限制可用操作
 4. 敏感操作强制 HITL：Human-in-the-Loop 确认


---

11.3      权限控制与沙箱
Q:   如何实现 Agent 的权限控制？
 工具级别: 每个工具定义所需权限，Agent 只能调用被授权的工具
 参数级别: 限制参数范围（如只允许查询特定数据库表）
 操作级别: 区分读/写操作，写操作需额外确认
 用户级别: 不同用户角色有不同 Agent 权限
 环境级别: Agent 在沙箱中运行，限制系统调用和网络




11.4 Guardrails            实现
Q:   如何实现 Agent 的输入/输出安全护栏？
 # OpenAI Agents SDK 风格
 from agents import Agent, GuardrailFunctionOutput, input_guardrail


 @input_guardrail
 async def check_injection(ctx, agent, input_data):
      """检测 prompt injection"""
      result = await classifier.classify(input_data)
      return GuardrailFunctionOutput(
          output_info={"score": result.score},
          tripwire_triggered=result.score > 0.8   # 触发则阻断
      )


 agent = Agent(
      name="Safe Agent",
      instructions="...",
      input_guardrails=[check_injection],
 )


---

第十二章 Agent 部署与成本优化
12.1 Token         管理与成本优化
Q: Agent系统如何控制 Token 消耗和 API 成本？
        策略                             方法                          预期节省
 Prompt 缓存       Anthropic/OpenAI 的 prompt caching                最高 90%
 语义缓存            相似查询直接返回缓存结果                                     30-60%

 模型路由            简单任务用小模型，复杂任务用大模型                                40-70%

 Batch API       非实时任务用批处理接口                                      50%

 上下文压缩           压缩/截断历史消息                                        20-40%

 工具结果摘要          对长工具输出进行摘要                                       10-30%


 class ModelRouter:
     async def route(self, query: str, complexity: str) -> str:
           if complexity == "simple":
              return "claude-haiku-4-5-20251001"   # 最便宜
           elif complexity == "medium":
              return "claude-sonnet-4-20250514"
           else:
              return "claude-opus-4-20250514"      # 最强




12.2 Agent         部署架构
Q: Agent   服务如何部署到生产环境？


---

 # Docker Compose 示例
 services:
   agent-api:
      build: .
      ports: ["8000:8000"]
      environment:
       - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
       - REDIS_URL=redis://redis:6379
      depends_on: [redis, milvus]


   redis:
      image: redis:7-alpine
      # 用于缓存和会话管理


   milvus:
      image: milvusdb/milvus:latest
      # 向量数据库用于 RAG 和长期记忆


关键考虑：
  无状态 API 层：Agent 状态存储在 Redis/数据库，API 层可水平扩展
  异步任务队列：长时间运行的 Agent 任务放入 Celery/RQ
  流式输出：用 SSE 或 WebSocket 推送中间结果
  健康检查：监控 LLM API 连通性和响应时间


第十三章 高频综合面试题精选
Q1:   从零设计一个客服 Agent 系统，你会怎么做？
答题框架：


---

 1. 需求分析
   - 支持的渠道（网页/APP/微信）
   - 业务范围（售前/售后/技术支持）
   - 是否需要多语言


 2. 架构设计
   - 路由层：意图分类 → 分发到专业 Agent
   - Agent 层：每个领域一个专业 Agent（退款/物流/技术）
   - 工具层：CRM 查询、工单创建、知识库检索
   - 记忆层：短期（对话历史）+ 长期（用户画像）
   - 安全层：Guardrails + Human-in-the-Loop


 3. 技术选型
   - 框架：OpenAI Agents SDK（Handoff 天然适合客服分流）
   - RAG：知识库检索 + 重排序
   - 向量数据库：Milvus（生产级）
   - 可观测性：LangSmith


 4. 关键指标
   - 解决率、转人工率、平均响应时间、用户满意度


 5. 迭代策略
   - 先上线单 Agent MVP
   - 收集失败案例，迭代优化
   - 逐步加入多 Agent 和高级功能




Q2: Agent    产生幻觉怎么办？
 1. RAG Grounding    ：强制基于检索到的事实回答
 2. Prompt 约束：明确指示"如果不确定请说不知道"
 3. Self-Verification：让 Agent 自检回答是否有依据
 4. 引用标注：要求 Agent 标注信息来源
 5. Guardrails：输出检测器过滤无依据内容
 6. 使用 Reasoning Model：o1/o3/DeepSeek-R1 等推理模型幻觉率更低


---

Q3:   如何处理 Agent 的延迟问题？
        优化方向                                  具体措施
 并行化                       工具并行调用、多路检索并行
 流式输出                      SSE 实时推送中间结果

 模型选择                      非关键步骤用小模型
 缓存                        Prompt 缓存 + 语义缓存

 预计算                       热门查询预生成答案
 异步架构                      长任务异步执行 + 通知


Q4:   你如何调试一个复杂的 Agent 系统？
 1. Tracing链路追踪：LangSmith / Phoenix 查看每步输入输出
 2. 日志分级：Agent 决策日志、工具调用日志、错误日志分开
 3. Replay 回放：保存完整消息历史，支持重放调试
 4. 单步执行：在关键节点设置断点（LangGraph 的 interrupt_before）
 5. A/B 测试：对比不同 prompt / 模型 / 工具配置的效果
 6. 评估套件：构建回归测试用例集，每次改动自动验证




Q5:   解释 Prompt Caching 的原理和适用场景
                    ：
Anthropic Prompt Caching

  对于重复使用的长 prompt 前缀（如 system prompt + 工具定义），缓存其处理结果
  后续请求只需处理变化的部分
  缓存命中时输入 token 价格降低最高 90%
  TTL 为 5 分钟（最后使用后）

适用场景： System prompt 很长（如包含大量工具定义）、RAG 中固定的上下文前缀、多轮对话中重复
的历史消息。


---

Q6: MCP     和 Function Calling 有什么区别？
      维度                 Function Calling        MCP

 层级        API 级别（单次请求）              应用级别（协议标准）
 工具定义      每次请求静态传入                  Server 动态注册和发现

 状态        无状态                       支持有状态连接
 生态        各厂商自定义格式                  统一标准，跨平台
 连接管理      无                         Transport 层管理生命周期

MCP 是更高层次的抽象，Function Calling 是其底层实现机制之一。




Q7: Agent     系统的 Token 消耗如何估算和优化？
 总 Token ≈ Σ(每步的 input_tokens + output_tokens)


 其中每步 input_tokens 包括:
 - System prompt（固定）
 - 工具定义（固定）
 - 对话历史（递增！）
 - 工具结果（可变）


 优化关键：
 1. 控制对话历史长度（摘要/截断）
 2. 工具结果摘要（不要把大段原文放进上下文）
 3. Prompt caching（缓存固定前缀）
 4. 模型路由（小任务用小模型）
 5. 提前终止（检测到答案就停止循环）




Q8:   如何实现 Agent 的"可中断 & 可恢复"？
使用 LangGraph Checkpoint：


---

# 编译时指定 checkpointer
app = graph.compile(checkpointer=SqliteSaver("agent.db"))


# 每次调用指定 thread_id
config = {"configurable": {"thread_id": "session-123"}}


# 执行到一半中断（如用户关闭页面）
partial_result = app.invoke(input, config)


# 后续恢复，从上次状态继续
resumed_result = app.invoke(None, config)    # 传 None 继续上次




Q9:   比较 RLHF、DPO、Constitutional AI
        方法                     训练信号                       是否需要           特点
                                                              RM


 RLHF
                   人类偏好对 → 训练 Reward                      是        经典方法，训练复杂
                   Model → PPO

 DPO               人类偏好对 → 直接优化策略                         否        简单高效，无需 RM
                                                                   Anthropic 提出，
 Constitutional
 AI
                   AI   自我评估 + 一组原则                       否        减少人工标注
 RLAIF             AI   反馈替代人类反馈                          可选       可扩展性强


---

Q10:   设计一个 Agentic RAG 系统
class AgenticRAG:
    """自适应 RAG Agent"""


    async def answer(self, question: str) -> str:
        # Step 1: 判断是否需要检索
       need_retrieval = await self.judge_need_retrieval(question)


        if not need_retrieval:
            return await self.direct_answer(question)


        # Step 2: 查询改写
       queries = await self.rewrite_queries(question)   # 生成多个查询


        # Step 3: 多源并行检索
       results = await asyncio.gather(
            self.vector_search(queries),
            self.keyword_search(queries),
            self.web_search(queries) if self.need_web else asyncio.sleep(0),
        )


        # Step 4: 重排序
       ranked = await self.rerank(question, flatten(results))


        # Step 5: 质量检查（CRAG 思想）
        if self.context_quality(ranked) < 0.5:
            # 质量差，补充网络搜索
            web_results = await self.web_search([question])
            ranked = await self.rerank(question, ranked + web_results)


        # Step 6: 生成回答
       answer = await self.generate(question, ranked[:5])


        # Step 7: 自验证（Self-RAG 思想）
        if not await self.verify_faithfulness(answer, ranked[:5]):
            answer = await self.regenerate_with_citation(question, ranked[:5])


        return answer


---

Q11: Python       中 asyncio.gather vs asyncio.TaskGroup 的区别？
   特性                         asyncio.gather     asyncio.TaskGroup (3.11+)

 错误处理            可选 return_exceptions=True     异常自动传播和取消
 取消行为            需手动处理                         一个失败自动取消所有
 结构化             非结构化                          结构化并发
 推荐              兼容旧版本                         新项目推荐


Q12: Agent       系统如何做灰度发布和 A/B 测试？
 1. 流量分流：按用户 ID hash 分配到不同 Agent 版本
 2. 指标对比：完成率、延迟、成本、用户满意度
 3. 渐进放量：5% → 20% → 50% → 100%
 4. 快速回滚：发现问题立即切回旧版本
 5. 评估自动化：LLM-as-Judge 自动评估输出质量




 参考资料：
     Model Context Protocol   官方文档
     MCP 2025 年 Roadmap
     MCP 1 周年 Spec 更新
     Google A2A 协议公告
     A2A 协议升级
     OpenAI Agents SDK
     LangGraph文档
     RAGAS 评估框架
     SWE-bench 排行榜


---
