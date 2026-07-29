# LangGraph Subgraph、Multi-Agent 与父子 Checkpoint

> **日期**: 2026-07-29 | **状态**: draft | **涉及版本**: `30c4d58`

## 相关文档与源码

- 前置课程：[StateGraph](state-graph.md)、[Pregel runtime](pregel-runtime.md)、[Interrupt、Command 与 HITL](interrupt-command-hitl.md)
- 观察层：[Streaming 与运行观察层](streaming-observability.md)
- 学习入口：[LangGraph 学习笔记](README.md)
- Graph compile 与子图 checkpointer：[state.py](../../../submodules/langgraph/libs/langgraph/langgraph/graph/state.py)
- 子图 namespace / State 查询与恢复：[main.py](../../../submodules/langgraph/libs/langgraph/langgraph/pregel/main.py)
- 父子持久化测试：[test_subgraph_persistence.py](../../../submodules/langgraph/libs/langgraph/tests/test_subgraph_persistence.py)
- 预构建 Agent 的子图命名：[chat_agent_executor.py](../../../submodules/langgraph/libs/prebuilt/langgraph/prebuilt/chat_agent_executor.py)

## 本课主线

```text
Subgraph = Graph 内嵌 Graph 的编排能力
Multi-Agent = 多个职责不同的决策 / 执行单元的协作架构
→ 明确父子图 State 输入输出契约
→ 明确谁有最终决策权
→ 明确 checkpoint 的继承、隔离与积累边界
→ 只在职责与状态所有权真正分离时拆图
```

## 第一小节：Subgraph 与 Multi-Agent 不是同义词

Subgraph 是一个被父图调度的 `CompiledStateGraph`，可拥有自己的 Node、Edge、循环、Tool、Interrupt 和 Checkpoint。它不必使用 LLM，例如“抽取 PDF 条款并转成结构化字段”的流程也可以是子图。

Multi-Agent 则是一种系统分工：多个有不同提示、工具、权限、状态或决策职责的单元协作完成任务。它可以使用多个 Subgraph，也可以只是多个普通 Node；多个 Agent 还可以使用同一个模型 provider。不要把“模型数量”误当成 Multi-Agent 的定义。

企业合同审查可作为贯穿例子：主图 Coordinator 将合同分别交给法律、隐私安全和商业条款审查流程，三个流程返回专业报告，主图最后统一给出接受、修改或人工审批的结论。

> **本节精髓：Subgraph 解决“怎样嵌套编排”；Multi-Agent 解决“怎样分工协作”。前者是 Runtime 结构，后者是应用架构。**

## 第二小节：父子图的 State 契约

父图与子图不是自动共享同一份 Python dict。父图需要明确给子图什么输入，子图需要明确向父图提交什么输出。稳定的边界通常是：

```text
父图：contract_ref、review_scope
→ 输入适配
法律子图：document_id、applicable_policies、legal_working_notes
→ 输出适配
父图：review_reports += legal_report
```

共享少量语义稳定字段时，可以把子图作为父图 Node 使用；子图只读写双方约定的字段。若父子 schema 差异很大，更适合用适配 Node 调用子图，把父图输入转换成子图专用输入，再将子图结果转换成父图的部分 State 更新。

不要把完整 `messages`、全部业务数据和最终决策字段无差别交给每个子 Agent。这样会造成 Context Window 膨胀、提示相互污染、敏感信息暴露与责任不清。

```text
可共存的事实：legal_report / privacy_report / commercial_report
→ Reducer 追加或按键合并

竞争性的结论：final_decision
→ 汇合后的 Coordinator / Synthesis Node 统一生成
```

> **精髓：checkpoint 继承不等于 State 自动共享。checkpoint 解决“怎样恢复”，State schema 与输入输出契约决定“谁能看见和修改什么”。**

## 第三小节：四种常见 Multi-Agent 结构

| 结构 | 运行方式 | 适合场景 | 关键风险 |
|---|---|---|---|
| Supervisor | 中央 Coordinator 分派 Worker，统一读取结果并决定下一步。 | 任务中心明确、最终责任集中。 | Supervisor 变成全知瓶颈。 |
| Handoff | 当前负责 Agent 将会话或控制权转给下一位专业 Agent。 | 客服、技术支持、财务等职责互斥的会话。 | Agent 之间反复转交形成循环。 |
| Parallel specialists | 多个独立子图并行产出证据，barrier 后汇总。 | 尽调、审查、多来源检索、扫描。 | 把并行建议直接当最终结论。 |
| Hierarchy | 总协调器管理团队负责人，负责人再管理子团队。 | 稳定且确有层级的复杂组织任务。 | 为形式而过度嵌套。 |

Supervisor 适合合同审查：法律、隐私、商业子图只产出证据与建议，Coordinator 才有 `final_decision` 的写权。Handoff 则更接近“当前会话负责人改变”；可使用 `Command.goto` 动态路由，若子图需要将意图交由父图解释，使用 `Command.PARENT`，仍受父图 State、Reducer 和调度边界约束。

## 第四小节：Tool 与 Subgraph 的层级差异

Tool 是一次受限的能力调用，例如查询数据库、搜索航班、创建订单。Subgraph 是一段可包含多个 Node、循环、Tool、Interrupt 与 Checkpoint 的完整流程，例如“审查一份合同”或“完成一次退款案件”。

可以把一个 Agent 作为 Tool 暴露给 Supervisor：父 Agent 像 RPC 一样委派一次任务，并读取其结果。若该子 Agent 需要自己的持久状态、人工审批、流式观察或内部循环，直接作为 Subgraph 嵌入通常更自然。ToolNode 源码也考虑了 supervisor-with-tools 架构中子图 interrupt 向上冒泡的场景，见 [tool_node.py:977-981](../../../submodules/langgraph/libs/prebuilt/langgraph/prebuilt/tool_node.py#L977-L981)。

## 第五小节：父子图 Checkpoint 的联系

可以把一次合同审查想成总案卷与专业小组案卷：

```text
thread_id
= 整个案件编号，例如 contract-review-2026-001

父图 checkpoint
= Coordinator 保存的全局调度现场

子图 checkpoint
= 法务 / 隐私小组保存的局部工作现场

checkpoint namespace
= 区分“总案卷”和“哪个子图实例”的目录路径

checkpoint_id
= 某一目录下某一时刻的具体快照
```

父图和子图通常使用同一个 `thread_id`，表示它们属于同一案件；Runtime 通过不同 checkpoint namespace 区分父图与各子图的状态和执行位置。父图保存“案件已进入法律审查、下一步应等待哪个任务”等全局编排信息；子图保存“已抽取哪些条款、正在等哪项人工确认”等局部细节。

若法律子图触发 interrupt，Runtime 保存该子图的暂停现场；应用使用同一 `thread_id` 恢复时，Runtime 能依 namespace 找到暂停所在的子图并继续，再将子图最终结果交回父图。Pregel 通过 namespace 查找和委派子图 State / 历史操作，见 [main.py:1195-1223](../../../submodules/langgraph/libs/langgraph/langgraph/pregel/main.py#L1195-L1223) 与 [main.py:1394-1433](../../../submodules/langgraph/libs/langgraph/langgraph/pregel/main.py#L1394-L1433)。

## 第六小节：三种子图 Checkpointer 策略

| 子图 compile 配置 | 与父图的关系 | 跨独立调用的子图 State | 典型用途 |
|---|---|---|---|
| `checkpointer=None` | 默认；可继承父图 checkpointer，以支持嵌套 interrupt / resume。 | 默认不积累，每次独立调用从新的局部 State 开始。 | 一次性分析、检索、格式转换。 |
| `checkpointer=False` | 明确不使用、也不继承 checkpoint。 | 不持久化。 | 纯计算、可重算、无需暂停恢复的小流程。 |
| `checkpointer=True` | 子图拥有独立持久化 namespace。 | 同一 thread 下可累积该子图自己的 State。 | 长期参与案件的专业 Agent、跨回合工作草稿。 |

`None` 的微妙之处是：它借用父图的恢复链路，不代表子图自动成为“有长期记忆的 Agent”。当前测试验证它在父图内可 interrupt / resume，但两次独立调用的消息历史互不串联，[test_subgraph_persistence.py:30-153](../../../submodules/langgraph/libs/langgraph/tests/test_subgraph_persistence.py#L30-L153)。

`True` 不是单纯“更可靠”。它意味着开发者宣布“这个子 Agent 应在同一案件中保有独立且持续的局部工作档案”。测试验证 stateful 子图跨调用积累消息，并按不同子图节点名称隔离 namespace，[test_subgraph_persistence.py:291-365](../../../submodules/langgraph/libs/langgraph/tests/test_subgraph_persistence.py#L291-L365)。

如果刻意为子图传入不同 `thread_id`，它会成为独立案件，而不再是父图自然嵌套的一段可恢复流程。此时父图需要显式保存关联 ID、查询该独立任务状态，并处理异步完成和失败补偿。

## 第七小节：Streaming、权限与运行治理

对子图启用 streaming 时，事件会带 namespace，说明它来自主图还是哪个子图。UI 不应把所有 Agent 的 token 混入同一聊天气泡：终端用户通常只看 Coordinator 的结论和筛选后的进度；开发者才看子图 Task、debug、checkpoint 和原始错误。

多 Agent 会扩大授权面。每个 Agent / 子图都应明确：可读取哪些 State 字段、可调用哪些 Tool、可写哪些字段、能否发起副作用、可委派给谁、预算与循环上限是多少。子图可恢复不等于副作用 exactly once；支付、邮件、合同发送等仍须依赖业务幂等键、权限、审计和外部状态核验。

## 第八小节：什么时候不该拆 Multi-Agent

> **本课最高优先级精髓：不要因为任务能被描述成多个角色，就拆成 Multi-Agent。只有职责、权限、工具、上下文或 State / 恢复边界真正不同，并且能定义稳定输入输出契约时，拆分才有价值。**

以下情况优先保留一个 Agent、一个清晰的 StateGraph，或普通 Tool 调用：

1. 任务只是稳定线性流程；
2. 同一模型加少量 Tool 已能可靠完成；
3. 所谓不同角色只是同一上下文下的不同提示词；
4. 多个 Agent 仍必须读取完整相同消息、调用相同工具并按同一规则决策；
5. 系统还无法治理权限、成本、失败、观测、循环和副作用幂等。

拆分会引入额外 token、延迟、路由、State 同步、checkpoint namespace、权限和排错成本。若拆分后每个 Agent 仍依赖同一份全部上下文，得到的通常不是清晰分工，而是多个互相转发消息的循环。

一句判断可用于设计评审和面试：

> 如果多个“Agent”仍需看同一份完整上下文、调用同一组 Tool、由同一规则作决策，而且没有独立 State 或恢复边界，那么优先保留一个 Agent 或普通 StateGraph。

## 面试收口

> Subgraph 是 LangGraph 中可嵌套、可独立组织 Node、State、Tool、Interrupt 与 Checkpoint 的编排单元；Multi-Agent 是多个职责不同的决策或执行单元协作的架构方式。生产设计应先定义输入输出契约、State 所有权、Reducer 汇总规则、checkpoint namespace、权限与预算边界，再决定是否需要拆成多个 Agent；多 Agent 不是复杂度的自动解法。

## QA / 讨论记录

### Q: 子图继承父图 checkpoint，是否就自动共享父图所有 State 和记忆？

> **状态**: verified
> **来源**: source-code / discussion

A: 不是。checkpoint 继承解决的是嵌套运行的保存与恢复；State 是否传入、子图能看到哪些字段、结果怎样回写，仍由 State schema、输入输出适配和 Node 返回的部分更新决定。`checkpointer=None` 默认还不会让子图在独立调用之间自动累积局部 State。

### Q: `checkpointer=True` 是否应该成为每个子 Agent 的默认配置？

> **状态**: verified
> **来源**: source-code / discussion

A: 不应该。它适合确实需要在同一 thread 中跨调用积累独立局部 State 的长期角色；一次性工作子图保留默认 `None` 通常更清晰，能避免旧上下文污染后续任务，并降低持久化与调试成本。

## 下一小节

下一大点进入 Checkpoint persistence、history 与 time travel：怎样查询历史快照、从过去分叉、恢复或重放执行，以及这些能力和外部副作用的安全边界。
