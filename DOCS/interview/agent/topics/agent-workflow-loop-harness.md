# Agent、Workflow、Agent Loop 与 Agent Harness

> **日期**: 2026-07-30 | **证据状态**: to-verify | **学习状态**: learning

## 相关文档

- 模拟面试：[Agent / Workflow / Loop / Harness QA](../qa/agent-workflow-loop-harness.md)
- 问题目录：[A01、A02、A04、H01、H02](../question-catalog.md)
- 学习路线：[Agent 面试联合学习路线](../learning-roadmap.md)
- 既有基础：[Agent Loop 横向总结](../../../comparison/agent-loop.md)
- 生产场景：[LangGraph 生产退款 Agent](../../../projects/langgraph/production-refund-agent.md)

## 来源与证据边界

本课主要回看以下原始 PDF 页面：

- [2026-02-23 版 PDF](../../../../references/agent-interview/originals/agent-interview-guide-2026-02-23.pdf) 第 1-2 页：Agent 定义、普通 LLM 应用与 Agent 的比较。
- [2026-07 版 PDF](../../../../references/agent-interview/originals/agent-interview-guide-2026-07.pdf) 第 1-8 页：Agent System、Agent Loop、Workflow / Agent 边界与 Eval Harness。

机械 Markdown 提取稿只用于定位关键词。本课已经回看 PDF 原页，但 PDF 本身是第三方面试资料，不是官方事实来源，因此当前结论保持 `to-verify`。其中关于 Agent 定义、Harness 宽窄含义和框架能力的进一步结论，后续仍需用官方文档或源码核验。

## 知识地图与 QA 索引

| 知识点 | 核心问题 | 模拟面试 |
|---|---|---|
| K1 四个概念的层次 | Agent、Workflow、Loop、Harness 是否是同一维度？ | [Q1](../qa/agent-workflow-loop-harness.md#q1-four-concepts) |
| K2 Agent 与 Workflow | 有分支、有循环、有 LLM 是否就算 Agent？ | [Q1](../qa/agent-workflow-loop-harness.md#q1-four-concepts)、[Q2](../qa/agent-workflow-loop-harness.md#q2-control-ownership) |
| K3 Agent Loop | Loop 管理什么，和 Workflow Runtime 有何区别？ | [Q1](../qa/agent-workflow-loop-harness.md#q1-four-concepts)、[Q6](../qa/agent-workflow-loop-harness.md#q6-loop-versus-harness) |
| K4 Agent Harness | Harness 是否等于 Loop 加重试、日志和沙箱？ | [Q3](../qa/agent-workflow-loop-harness.md#q3-harness-completeness)、[Q6](../qa/agent-workflow-loop-harness.md#q6-loop-versus-harness) |
| K5 Eval Harness 初步组成 | Dataset、Environment、Tools、Runner、Scorer 分别做什么？ | [Q4](../qa/agent-workflow-loop-harness.md#q4-minimal-eval-harness) |
| K6 真实结果判分 | 为什么不能只看 Agent 最终文本？ | [Q5](../qa/agent-workflow-loop-harness.md#q5-result-versus-claim) |

## K1：四个概念不在同一维度

| 概念 | 回答的问题 | 一句话定位 |
|---|---|---|
| Agent | 谁根据目标和反馈决定下一步？ | 目标驱动的决策系统。 |
| Workflow | 整体路径主要由谁控制？ | 由代码预先规定主要路径的控制方式。 |
| Agent Loop | Agent 的一次任务如何反复推进？ | Agent 内部“决策、行动、观察、更新、终止”的控制循环。 |
| Agent Harness | 外部如何让 Agent 运行、受控、被记录和评测？ | 包围 Agent / Loop 的运行与实验设施。 |

本课精髓：

> **Agent 是决策主体，Workflow 是控制方式，Agent Loop 是内部运行机制，Agent Harness 是外部运行与评测设施。**

它们不是四个互斥选项。一个生产系统可以用确定性 Workflow 包住一个 Agent 节点，Agent 节点内部运行 Agent Loop，外部再由 Harness 提供任务、环境、限制、记录和评测。

## K2：Agent 与 Workflow 的边界

### Agent

面试中更稳妥的定义是：

> Agent 是目标驱动的决策系统。系统把一部分流程控制权交给模型，让模型根据当前状态和环境反馈动态决定下一步行动。

2 月版使用 `Agent = LLM + Memory + Planning + Tool Use + Action Loop` 帮助入门，但它不是严格的必要条件集合。并不是每个 Agent 都必须有独立长期记忆或显式 Planner。

判断 Agent 时应重点看：

1. 是否有目标和当前状态；
2. 是否能观察环境；
3. 模型是否能决定下一步行动；
4. 行动结果是否回到后续决策；
5. 是否有完成、失败或受控终止条件。

### Workflow

Workflow 的主要路径由程序预先规定。它可以有条件分支、循环、工具调用，甚至可以在某个固定节点调用 LLM；这些特征本身都不能证明它是 Agent。

关键判断不是“系统是否动态读取状态”，而是：

> **状态到下一步行动的映射，主要由预定义代码决定，还是由模型在运行时决定。**

例如程序每 10 秒查询一次退款状态，成功则结束，处理中则继续，最多查询 5 次。环境状态会变化，但状态对应的动作已经由代码写死，因此这是带轮询的确定性 Workflow。

同样，使用 LLM 也不自动等于 Agent。如果代码只要求 LLM 做一次固定分类，再按分类进入预定义分支，整体仍主要是 Workflow。在现代 LLM Agent 面试语境中，LLM 是否获得下一步行动的控制权比“是否调用过 LLM”更重要。

## K3：Agent Loop 管内部推进

Agent Loop 是一次 Agent run 内部的控制循环：

```text
读取目标和当前状态
→ 构造模型输入
→ 模型决定下一步
→ 校验并执行工具或输出答案
→ 获得环境反馈
→ 更新状态、预算和轨迹
→ 判断继续还是终止
```

Loop 不等于整个 Workflow Runtime。Workflow Runtime 还可能执行身份校验、固定规则、人工审批和支付落账等确定性节点，这些节点不一定属于 Agent Loop。

解析失败重试、工具错误回流、重复调用检测、最大步数、Token / 时间 / 成本预算等能力，可以直接属于 Loop Runtime。它们让 Loop 可控，但不能单独构成 Eval Harness。

ReAct、Plan-and-Execute 和 Reflection 是 Loop 内可采用的决策策略；LangGraph 等框架可以承载和调度 Loop。它们都不应与 Loop 本身混为同一层概念。

## K4：Agent Harness 管外部运行与评测

7 月版在这一章主要使用狭义的 **Agent Eval Harness**：

> 让 Agent 在可复现环境中运行、被观测、被判分的一套外壳。

Loop 与 Harness 的边界是：

- Loop 关心 Agent 自己怎样一步步做事；
- Harness 关心外部怎样给它任务和环境、启动和限制它、记录它、判断成功与否并复现失败。

因此 Harness 不是“Agent Loop 再加一些高级功能”，而是处在 Loop 外部的另一层。错误重试可能由 Loop 自己完成；Harness 则可以把同一个 Loop 在多组任务和相同初始环境中运行，记录它如何重试，并判断新版本是否真的更可靠。

术语还存在宽窄差异：

- **狭义 Eval Harness**：强调 Dataset、Environment、Runner、Scorer、Sandbox、Logger、Replayer 和可复现实验。
- **广义生产 Harness**：在本仓库的架构研究中，还可能包含编排 Runtime、工具治理、权限、上下文、持久化和生产可观测性。

面试时应先说明自己采用的含义，避免把评测外壳与整个生产 Agent Runtime 混写。

## K5：Eval Harness 初步组成

本轮只建立基础角色，不展开复杂 Eval 策略。

| 对象 | 通俗比喻 | 退款 Agent 示例 |
|---|---|---|
| Dataset / Task | 试卷和题目 | 用户诉求、订单初始状态、目标、约束和元数据。 |
| Environment | 考场和题目世界 | 模拟订单库、支付系统、客服系统及可恢复的初始快照。 |
| Tools / Tool Adapter | 允许使用的工具 | 查询订单、查询支付、检查政策、创建退款、转人工。 |
| Runner | 监考和考试组织者 | 重置环境、加载指定版本、启动 Loop、控制预算并收集轨迹。 |
| Scorer / Oracle | 阅卷规则和阅卷者 | 检查退款记录、金额、权限、轨迹、最终回复和成本。 |
| Sandbox | 隔离考场 | 防止测试调用真实生产退款接口。 |
| Logger / Trace | 录像与答题过程 | 记录模型调用、工具参数、结果、状态变化和成本。 |
| Replayer | 考试回放 | 重放失败轨迹并比较新旧版本。 |

### Dataset 不是一堆原始字段

一个 Eval Sample 至少应描述任务、初始环境、成功目标、限制条件和元数据。金额、用户身份、订单信息只是 Sample 的组成部分。它是可运行、可判分的测试任务，不等于模型训练数据集。

### Environment 不等于 Sandbox

Environment 是 Agent 面对的外部世界；Sandbox 只是隔离设施。Environment 还需要支持 Setup / Reset，保证不同 Agent 版本面对相同初始状态，否则结果不能公平比较。

### Runner 与 Scorer

Runner 解决“怎样公平、稳定、批量地把实验跑起来”；Scorer 解决“怎样根据真实结果判断做对没有”。完整记录但没有任务、初始环境和判分标准，只是日志或 Observability，不是完整 Eval Harness。

## K6：最终文本是说法，环境状态是事实

退款 Agent 可能回复“您的 500 元退款已经成功发起”，但数据库中没有退款记录。此时必须判失败。

> **最终文本只是 Agent 对结果的陈述；环境最终状态才是实际发生的业务事实。**

因此 Scorer 不能只评价语言是否流畅，还应检查：

- 是否为正确订单创建了正确金额的退款；
- 是否出现重复退款或越权访问；
- 高风险操作是否经过审批；
- 工具轨迹和成本是否满足约束；
- 最终回复是否与真实状态一致。

程序化环境状态检查通常比单纯 LLM-as-Judge 更适合判断确定性业务结果。复杂评分组合属于后续 Eval 专题，本课只保留这一基础原则。

## K7：生产退款场景中的组合关系

一个混合式退款 Agent 系统可以表示为：

```text
外层确定性 Workflow
├── 身份认证
├── Agent 调查节点
│   └── Agent Loop
├── 固定风控规则
├── 必要时人工审批
├── 支付系统执行退款
└── 审计归档
```

Agent 调查节点内部可能先查订单，再根据结果决定查询支付记录或退款流水。身份认证、金额阈值、人工审批、实际打款和审计仍由外层 Workflow 控制。

Eval Harness 在系统外部准备模拟订单、数据库快照、Mock 工具、Runner、Scorer、Sandbox 和 Trace，用来检查这个 Agent 是否调查正确、是否越权、是否真正完成目标，并复现失败。

这一结构应描述为：

> **混合式 Agent 系统：外层是确定性 Workflow，其中包含一个运行 Agent Loop 的 Agent 节点，外部再由 Harness 提供运行和评测设施。**

## 适用边界

- 路径稳定、规则明确、风险高：优先使用 Workflow。
- 任务开放、步骤未知、需要根据反馈探索：使用 Agent。
- 只有一次明确查询或转换：普通模型调用或 Function Calling 可能已经足够。
- 既有严格业务边界又有开放判断：外层 Workflow 包住局部 Agent。
- 无论采用哪种 Agent，都需要可控 Loop；要稳定比较和回归，还需要 Eval Harness。

自主性不是越高越好。模型获得的流程控制权越大，系统通常越灵活，但不确定性、成本、延迟和安全风险也越高。

## 面试回答

### 30 秒版本

> Agent 是目标驱动的决策系统，它根据状态和环境反馈动态决定下一步。Workflow 的主要路径由代码预先规定。Agent Loop 是 Agent 内部反复执行“决策、行动、观察、更新和终止”的循环，而 Harness 是 Loop 外部的任务、环境、Runner、Scorer、Sandbox 和日志等设施，用来运行、限制、评测和复现 Agent。生产系统通常由外层 Workflow 控制确定性和高风险步骤，局部 Agent Loop 处理开放任务。

### 2 分钟展开要点

1. 先用“下一步控制权”区分 Workflow 与 Agent；
2. 说明分支、循环、工具调用甚至一次 LLM 调用都不能单独证明是 Agent；
3. 给出 Agent Loop 的决策、行动、观察和状态更新链；
4. 说明 Loop 管内部推进，Harness 管外部任务、环境、运行、记录和判分；
5. 用“外层 Workflow + Agent 节点 + 内部 Loop + 外部 Harness”的退款场景收束；
6. 强调真实环境状态比最终语言更能证明任务是否完成。

## 本轮学习状态

| 知识点 | 当前状态 | 记录 |
|---|---|---|
| Workflow 的确定性控制 | understood | 已能识别固定条件分支和轮询仍是 Workflow。 |
| 混合式系统结构 | understood | 已能说明 Workflow 的局部节点可包含 Agent Loop。 |
| Agent 的准确口述定义 | learning | 已理解“动态”的方向，仍需稳定表达为“下一步控制权”。 |
| Agent Loop 的边界 | learning | 容易把整个 Workflow Runtime 都归入 Agent Loop。 |
| Loop 与 Harness 的边界 | understood / 待复习 | 用户表示已理解内外层关系，但尚未再次独立口述。 |
| Runner 与 Scorer | learning | 已完成第一轮通俗解释，尚不能独立设计。 |
| Eval 成功判据 | learning | 已解释真实环境状态优先于最终文本，待后续复测。 |

当前没有任何项目应标记为 `fluent`。下一次复习优先抽问“下一步控制权”“Loop 内部推进与 Harness 外部评测”以及“最终文本与真实状态”的区别。
