# Agent Eval Harness 模拟面试 QA

> **日期**: 2026-07-30 | **证据状态**: to-verify | **学习状态**: learning / paused

## 相关文档

- 知识笔记：[Agent Eval Harness](../topics/agent-eval-harness.md)
- 前置 QA：[Agent / Workflow / Loop / Harness QA](agent-workflow-loop-harness.md)
- 问题目录：[Agent 面试问题目录](../question-catalog.md)

## QA 索引

| QA | 考查点 | 当前状态 |
|---|---|---|
| EH-Q1 | Runner 与 Scorer | understood / 待复习 |
| EH-Q2 | Environment Reset | understood |
| EH-Q3 | Dataset / Sample | learning |
| EH-Q4 | Environment 与 Sandbox | understood |
| EH-Q5 | Logger 与 Scorer | understood |
| EH-Q6 | 完整执行顺序 | learning |
| EH-Q7 | 为什么 20 个 Prompt 不够 | learning |
| EH-Q8 | User Simulator | learning |
| EH-Q9 | 硬性失败条件 | learning |
| EH-Q10 | Harness 完整定义 | learning |
| EH-Q11-EH-Q13 | 骨架复测 | pending；已出题但未回答 |

## EH-Q1 Runner and scorer

### 问题

用退款 Agent 举例说明 Runner 和 Scorer 分别负责什么，以及一次测试中怎样配合。

### 用户回答

> 前者负责执行，后者负责根据各种信息判断是否执行成功。

### 点评与纠偏

核心方向正确，但“Runner 负责执行”过于宽泛。Runner 负责组织并启动评测运行，不是亲自查询订单或创建退款。它读取 Sample、Reset 环境、加载版本、启动 Agent、控制预算并收集最终输出、环境状态和轨迹；Scorer 再根据这些证据判定任务是否成功。

### 精炼回答

> Runner 负责让实验在规定条件下真正跑起来，Scorer 负责根据最终输出、环境状态和执行轨迹判断它做得对不对。

## EH-Q2 Reset

### 问题

模型 A 测试后留下退款记录，模型 B 在未恢复数据库的情况下测试同一道题。二者能否公平比较？缺少什么？

### 用户回答

> 不能，缺少了 reset 机制。

### 点评

回答正确。模型 B 面对的是被 A 污染的环境，不再是同一道题，可能把读取已有退款误判成 B 成功完成任务。Setup / Reset 必须在每次运行前恢复相同初始快照。

## EH-Q3 Dataset and sample

### 问题

退款 Dataset 中只有金额、身份和订单状态是否足够？完整 Sample 还需要什么？

### 用户回答

> 暂时想不出来。

### 补充答案

这些字段只是初始数据。完整 Sample 还应有用户任务、初始环境、成功目标、约束和 metadata。记忆公式是：

> **Sample = 题目 + 初始世界 + 成功标准 + 约束。**

## EH-Q4 Environment and sandbox

### 问题

测试系统提供模拟数据库和支付系统，并用 Docker 隔离 Agent。Environment 和 Sandbox 分别是什么？

### 用户回答

> 前者是模拟数据库和支付系统，Sandbox 是指隔离的操作环境。

### 点评

回答正确。Environment 说明 Agent 面对什么世界；Sandbox 说明这个世界如何与生产隔离。Sandbox 是保护层，不是完整 Environment。

## EH-Q5 Logger and scorer

### 问题

Logger 记录到 Agent 查询了 6 次工具并回复退款成功，但数据库没有退款记录。Logger 和 Scorer 分别做什么？

### 用户回答

> 前者记录，后者根据各方面信息判断最后状态。如果只有 Logger 没有 Scorer，可能记录中说退款成功，但支付系统因为网络等原因没有实际退款，没有 Scorer 去支付系统核实就容易出错。

### 点评

回答正确，已经抓住“声明”和“事实”的差异。Logger 保存发生了什么，Scorer 根据数据库最终状态、工具轨迹和约束判断是否真的成功。

## EH-Q6 Execution order

### 问题

排列 Dataset 读取、Environment Reset、Runner 启动、Agent Loop、Logger、Scorer 的顺序。

### 用户回答

> 6, 4, 1, 5, 2, 3。

### 纠偏

按原题编号，概念顺序应为：

```text
6 从 Dataset 读取 Sample
→ 3 Environment Reset
→ 4 Runner 启动任务
→ 1 Agent Loop 执行
→ 5 Logger 贯穿记录
→ 2 Scorer 判分
```

Logger 实际贯穿 Runner 与 Agent Loop，不是等 Loop 完成后才开始。原回答把 Reset 放到最后，失去了恢复统一起跑线的意义。

## EH-Q7 Twenty prompts

### 问题

为什么 Agent Eval 不能只靠人工写 20 个 Prompt、问一遍并观察答案？

### 用户回答

> 总会有人工考虑不到的情况？

### 点评与补充

覆盖不足是原因之一，但不是完整答案。Prompt 只描述输入文本，不能保证相同初始环境，也不能检查真实数据库状态、工具轨迹、权限、成本、版本和失败复现。即使 20 个问题覆盖充分，没有这些设施也仍不是完整 Harness。

## EH-Q8 User simulator

### 问题

客服 Agent Eval 为什么需要 User Simulator？它模拟什么？

### 用户回答

> 尽量真实？

### 点评与补充

“更真实”是方向，但需要说清行为。User Simulator 模拟用户在多轮对话中不提供完整信息、补充或更正信息、改变需求、拒绝方案、表达不满或诱导 Agent 违规，用于测试 Agent 的澄清、规则坚持和多轮推进能力。

## EH-Q9 Hard failure

### 问题

Agent 回复礼貌完整，但退款金额错误、访问其他用户或发生重复退款，任务怎样判？

### 用户回答

> 进入失败的流程环节？

### 纠偏

这些情况应直接判任务失败，并记录具体失败原因。金额、权限和重复副作用属于硬性条件，不能由语言质量抵消。

## EH-Q10 Harness definition

### 问题

用一句话定义 Agent Eval Harness，尽量包含可复现环境、任务、运行、记录和判分。

### 用户回答

> 对 Agent 的任务记录进行原始化保存，可追溯，并且可通过这些记录进行评测改进？

### 点评与纠偏

该回答主要描述 Logger 与 Replayer，遗漏任务、环境、Runner 和 Scorer。记录和追溯只是 Harness 的一部分。

### 参考回答

> Agent Eval Harness 是把测试任务、可重置环境、工具、Runner、运行记录和 Scorer 连接起来的实验系统，用于可复现地运行 Agent、记录行为、判断结果并比较版本。

## 待后续回答

用户因疲劳暂停 Harness 专题，以下问题已经提出但尚未回答，不得计入已完成 QA：

### EH-Q11 六字骨架

将 Dataset、Environment、Runner、Logger、Scorer、Replayer 分别放入“题、场、跑、记、判、复”。

### EH-Q12 对象识别

把历史退款工单、模拟数据库、恢复快照、启动模型、保存轨迹、检查退款记录分别映射到 Harness 对象。

### EH-Q13 完整性判断

只有完整 Trace 和回放，但没有成功标准与数据库最终状态检查，是否是完整 Eval Harness？当前主要具备哪部分能力？

## 后续复习入口

回到本专题时，不重新从头讲解。先让用户回答 EH-Q11-EH-Q13，再根据答案决定是否复习 Sample、执行顺序和 Harness 完整定义。
