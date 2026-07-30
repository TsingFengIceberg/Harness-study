# Agent Eval Harness

> **日期**: 2026-07-30 | **证据状态**: to-verify | **学习状态**: learning / paused for review

## 相关文档

- 模拟面试：[Agent Eval Harness QA](../qa/agent-eval-harness.md)
- 前置知识：[Agent、Workflow、Agent Loop 与 Agent Harness](agent-workflow-loop-harness.md)
- 问题目录：[H02、E01、Q01](../question-catalog.md)
- 学习路线：[Agent 面试联合学习路线](../learning-roadmap.md)

## 来源与范围

本课主要依据 [2026-07 版原始 PDF](../../../../references/agent-interview/originals/agent-interview-guide-2026-07.pdf) 第 6-8 页的 Harness 章节，并直接回看原始页面。机械 Markdown 仅用于定位。

本课只覆盖 Eval Harness 的基础组成、运行链和退款场景，不展开复杂 Benchmark、LLM-as-Judge 可靠性、统计置信度与 Eval 泄漏。第三方 PDF 不是官方证据，因此当前状态保持 `to-verify`。

## 知识地图与 QA 索引

| 知识点 | 核心问题 | 模拟面试 |
|---|---|---|
| EH-K1 Harness 价值 | 为什么不能只写 20 个 Prompt 人工看结果？ | [EH-Q7](../qa/agent-eval-harness.md#eh-q7-twenty-prompts) |
| EH-K2 完整运行链 | 一条 Sample 怎样从读取走到判分？ | [EH-Q2](../qa/agent-eval-harness.md#eh-q2-reset)、[EH-Q6](../qa/agent-eval-harness.md#eh-q6-execution-order) |
| EH-K3 核心对象 | Dataset、Environment、Runner、Scorer 等分别做什么？ | [EH-Q1](../qa/agent-eval-harness.md#eh-q1-runner-and-scorer)、[EH-Q3](../qa/agent-eval-harness.md#eh-q3-dataset-and-sample)、[EH-Q4](../qa/agent-eval-harness.md#eh-q4-environment-and-sandbox) |
| EH-K4 记录与判分 | Logger 和 Scorer 为什么不能互相替代？ | [EH-Q5](../qa/agent-eval-harness.md#eh-q5-logger-and-scorer) |
| EH-K5 多轮用户模拟 | User Simulator 模拟什么？ | [EH-Q8](../qa/agent-eval-harness.md#eh-q8-user-simulator) |
| EH-K6 真实成功标准 | 文本正确但业务状态错误怎样判？ | [EH-Q9](../qa/agent-eval-harness.md#eh-q9-hard-failure) |
| EH-K7 完整定义 | 如何一句话定义 Agent Eval Harness？ | [EH-Q10](../qa/agent-eval-harness.md#eh-q10-harness-definition) |

## EH-K1：Harness 把 Agent 运行变成实验

人工写 20 个 Prompt，再凭感觉判断回答好不好，仍不能稳定回答：

- 不同 Agent 是否面对相同初始环境；
- Agent 是否真的改变了数据库或外部系统；
- 中间是否发生越权、重复调用和无效循环；
- 成功是否消耗了不可接受的时间、Token 和工具次数；
- 模型、Prompt、工具或 Policy 变化后是否发生回归；
- 一次失败能否复现并定位到具体步骤。

Harness 的核心价值是：

> **把 Agent 的运行变成任务明确、环境一致、过程可见、结果可判、失败可复现、版本可比较的实验。**

覆盖更多边界情况只是价值之一。即使 20 个 Prompt 覆盖充分，如果没有环境、Reset、轨迹、Scorer 和版本记录，也仍然不是完整 Eval Harness。

## EH-K2：完整运行链

```text
从 Dataset 读取 Sample
→ Setup / Reset Environment
→ 准备 Tools、Action Space 和权限
→ Runner 加载指定版本并启动 Agent
→ Agent Loop 与 Environment 交互
→ Logger / Trace 贯穿运行过程
→ Scorer 检查结果、轨迹与约束
→ 汇总指标
→ Replayer / Regression 复现失败并比较新版本
```

Logger 不是 Agent 结束后才补记，而是贯穿 Runner 启动、模型调用、工具行动、环境反馈和状态更新。实现上 Runner 可以负责调用 Reset，但概念顺序仍是先恢复统一起跑线，再让 Agent 执行。

## EH-K3：核心对象

| 对象 | 负责什么 | 退款场景 |
|---|---|---|
| Dataset | 一组可运行、可判分的 Sample | 退款、改地址、查物流和异常升级任务集。 |
| Sample / Task | 一道具体题及其初始条件 | 用户诉求、订单快照、目标、约束和 metadata。 |
| Environment | Agent 面对的外部世界 | 模拟订单库、支付系统、客服系统。 |
| Setup / Reset | 恢复统一初始状态 | 每次运行前恢复数据库快照。 |
| Tools / Action Space | Agent 能采取的行动及返回的 Observation | 查订单、查支付、创建退款、转人工。 |
| Runner | 组织并启动评测运行 | 加载版本、控制预算、执行任务、收集结果。 |
| Scorer / Oracle | 判断是否成功及失败原因 | 检查退款记录、金额、权限、轨迹和成本。 |
| Sandbox | 隔离危险副作用 | 禁止测试操作真实订单和真实支付接口。 |
| Logger / Trace | 保存过程证据 | 模型输出、工具参数、环境反馈、状态变化和成本。 |
| Replayer | 重放或复现实验 | 恢复相同条件，比较失败与修复后的版本。 |
| User Simulator | 模拟多轮用户行为 | 补充信息、改变需求、表达不满或尝试诱导越权。 |

### Sample 不是字段集合

金额、用户身份和订单状态只是初始数据。完整 Sample 还应包含：

```text
题目：用户要求查明为什么未退款并正确处理
初始世界：订单已取消、支付成功、没有退款记录
成功目标：为正确订单产生正确金额的退款
约束：不得访问其他用户，不得重复退款，高金额必须审批
元数据：任务类型、难度、风险等级、来源和版本
```

可压缩为：

> **Sample = 题目 + 初始世界 + 成功标准 + 约束。**

### Environment 不等于 Sandbox

Environment 说明 Agent 面对什么世界；Sandbox 说明这个世界如何与生产系统隔离。模拟订单库和支付系统是 Environment，Docker、网络限制或测试账号边界是 Sandbox。

### Runner 不等于业务执行者

Runner 负责拿题、Reset、加载模型 / Prompt / Tool 版本、启动 Agent、控制超时和预算，并收集结果。真正查询订单和创建退款的是 Agent 与 Tools。

Agent Loop 内部的 Retry 是当前任务中的恢复策略；Runner 重新执行整个 Sample 属于外层实验调度。两者都可能出现“重试”，但控制层次不同。

## EH-K4：Logger 记录，Scorer 判定

Logger 回答“发生了什么”：

- 模型输出了什么；
- 调用了哪些工具和参数；
- 工具返回什么；
- State 如何变化；
- 用了多少时间、Token 和成本。

Scorer 回答“这算不算成功”：

- 是否为正确订单创建正确金额的退款；
- 是否访问无关用户或绕过审批；
- 是否出现重复退款；
- 最终回复是否和真实状态一致；
- 工具次数、延迟和成本是否超过限制。

完整 Trace 但没有成功标准和环境检查，主要具备 Observability，不是完整 Eval Harness。

## EH-K5：User Simulator 模拟会变化的用户

User Simulator 不只是让对话“更真实”，而是模拟多轮任务中会影响 Agent 决策的用户行为，例如：

- 一开始不提供订单号，等待 Agent 追问；
- 补充或更正信息；
- 中途改变需求；
- 拒绝处理方案；
- 表达不满；
- 诱导 Agent 违反退款 Policy。

它用于测试 Agent 能否正确澄清、维持业务规则，并在多轮交互中完成任务。

## EH-K6：硬性条件不能被语言质量抵消

以下情况即使最终回复礼貌、完整，也必须判失败：

- 退款金额错误；
- 查询其他用户数据；
- 重复退款；
- 绕过必要审批；
- 声称退款成功但数据库没有记录。

Scorer 可以记录多个子分数和失败原因，但业务、安全或副作用硬性条件失败时，不能让语言质量把总任务“补成成功”。

## EH-K7：Harness 如何支持改进

Harness 不会自动让 Agent 进化。更准确的闭环是：

```text
Harness 发现失败
→ Trace 定位模型、Prompt、工具、环境或 Policy 问题
→ 工程人员修改系统
→ Runner 重跑回归集
→ Scorer 比较新旧版本
```

线上 bad case 也应先脱敏、去重、补充初始环境和成功标准，并经人工审核后再成为 Eval Sample。

## 记忆骨架与面试回答

可以用“题、场、跑、记、判、复”记住主干：

```text
题：Dataset / Sample
场：Environment / Reset / Sandbox
跑：Runner
记：Logger / Trace
判：Scorer
复：Replayer / Regression
```

### 30 秒回答

> Agent Eval Harness 是把测试任务、可重置环境、工具、Runner、Scorer、Sandbox、日志和回放连接起来的实验系统。Runner 在固定模型、Prompt、工具版本和预算下启动 Agent，Logger 记录完整轨迹，Scorer 根据环境最终状态、工具行为、权限和成本判断是否成功。它让 Agent 评测可复现、可判分、可回归，而不是只看几个 Prompt 的最终文本。

## 本轮学习状态

| 知识点 | 当前状态 | 记录 |
|---|---|---|
| Runner 与 Scorer 基本职责 | understood / 待复习 | 已抓住“前者组织运行、后者判定成功”，需避免把 Runner 说成业务执行者。 |
| Setup / Reset | understood | 已能判断环境污染会破坏公平比较。 |
| Environment 与 Sandbox | understood | 已能区分模拟世界和隔离操作环境。 |
| Logger 与 Scorer | understood | 已能说明记录成功声明不等于核实真实支付状态。 |
| Dataset / Sample | learning | 尚不能独立说出题目、初始世界、目标和约束。 |
| 完整执行顺序 | learning | 曾把 Reset 放到最后，已完成纠偏。 |
| User Simulator | learning | 只形成“更真实”的初步直觉，尚未稳定口述多轮行为。 |
| Harness 完整定义 | learning | 仍容易只描述日志、追溯和改进，遗漏任务、环境、Runner 与 Scorer。 |

用户因疲劳暂停本专题。后续回看时从 [未回答的 EH-Q11-EH-Q13](../qa/agent-eval-harness.md#待后续回答) 开始，不重复整节讲解。
