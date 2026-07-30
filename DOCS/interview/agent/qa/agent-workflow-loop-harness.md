# Agent、Workflow、Agent Loop 与 Agent Harness 模拟面试 QA

> **日期**: 2026-07-30 | **证据状态**: to-verify | **学习状态**: learning

## 相关文档

- 知识笔记：[Agent、Workflow、Agent Loop 与 Agent Harness](../topics/agent-workflow-loop-harness.md)
- 问题目录：[Agent 面试问题目录](../question-catalog.md)
- 学习路线：[Agent 面试联合学习路线](../learning-roadmap.md)

## 记录说明

本文单独保存真实模拟面试过程，避免把用户当时的回答、理解卡点和后续纠偏混入知识正文。用户回答按原意整理，不把纠偏后的答案反写成用户一开始就已经掌握。

状态含义：

- `learning`：已经接触并能说出部分要点，但表达或边界仍不稳定；
- `understood`：讲解后已明确表示理解，但仍可能需要后续脱稿复测；
- `review`：可以回答主体，需要通过混合追问巩固；
- `fluent`：能够稳定独立回答并承接追问。本轮没有题目达到该状态。

## QA 与知识点索引

| QA | 考查点 | 关联知识 |
|---|---|---|
| Q1 | 四个概念的定义、区别与联系 | [K1-K4](../topics/agent-workflow-loop-harness.md#k1四个概念不在同一维度) |
| Q2 | 有分支和循环是否就是 Agent | [K2 Agent 与 Workflow](../topics/agent-workflow-loop-harness.md#k2agent-与-workflow-的边界) |
| Q3 | Runtime 控制是否等于完整 Eval Harness | [K4 Agent Harness](../topics/agent-workflow-loop-harness.md#k4agent-harness-管外部运行与评测) |
| Q4 | 最小 Eval Harness 的组成 | [K5 Eval Harness 初步组成](../topics/agent-workflow-loop-harness.md#k5eval-harness-初步组成) |
| Q5 | 最终回复正确但环境状态错误如何判分 | [K6 真实结果判分](../topics/agent-workflow-loop-harness.md#k6最终文本是说法环境状态是事实) |
| Q6 | 用一句话区分 Loop 与 Harness | [K3](../topics/agent-workflow-loop-harness.md#k3agent-loop-管内部推进) / [K4](../topics/agent-workflow-loop-harness.md#k4agent-harness-管外部运行与评测) |

## Q1 Four concepts

### 问题

请用自己的话说明：Agent、Workflow、Agent Loop 和 Agent Harness 分别是什么？它们之间有什么区别和联系？

### 用户回答记录

用户将 Agent 暂时描述为“一个整体概念”，将 Workflow 描述为固定的流程执行模板；将 Agent Loop 理解为模型执行过程中的循环，包括数据查询、整合、传给模型、接收模型结果和工具调用；将 Agent Harness 理解为围绕 Agent 执行过程提供测试、错误处理、沙箱、兜底和反馈的机制。

退款例子中，用户把发起退款、身份和金额审核、历史数据读取、机器或人工审批、退款成功或失败理解为 Workflow；同时指出某个“机器审批”节点内部可能再次获取用户数据、交给模型判断，因此局部节点也可能有 Agent Loop。

### 已答对的部分

- 正确识别 Workflow 的预定义路径特征；
- 正确意识到 Agent Loop 涉及模型调用、工具行动和反馈；
- 正确提出一个 Workflow 的局部节点内部可以运行 Agent Loop；
- 已经注意到 Harness 与测试、沙箱、记录和治理有关。

### 需要修正的部分

- Agent 不能只描述为“整体概念”，需要明确它是获得部分下一步控制权的目标驱动决策系统；
- Agent Loop 不是整个 Workflow Runtime 执行所有节点的过程；
- Harness 不是错误兜底机制的集合，重试和错误回流也可以直接属于 Loop Runtime；
- 本 PDF 语境下 Harness 主要指 Eval Harness，重点还包括任务、环境、Runner、Scorer 和可复现评测。

### 参考回答

> Agent 是目标驱动的决策系统，模型根据当前状态和环境反馈动态决定下一步。Workflow 的主要路径由代码预先规定。Agent Loop 是 Agent 内部反复进行“决策、行动、观察、状态更新和终止判断”的循环。Harness 位于 Loop 外部，负责提供任务和环境、启动和限制 Agent、记录轨迹、判断成功并复现失败。生产中常见外层 Workflow 包住局部 Agent 节点，Agent 节点内部再运行 Agent Loop。

> **学习状态**: learning

## Q2 Control ownership

### 问题

一个退款程序有条件分支，而且每隔 10 秒查询一次退款状态，最多查询 5 次。它是不是 Agent？如果只有“退款异常调查”节点让 LLM 自己决定调用哪些工具，整个系统应该怎样描述？

### 用户回答记录

用户判断它不是 Agent，因为条件分支已经固定，没有由 LLM 根据状态和环境动态决定；如果局部节点让 LLM 自主调查，则整个系统可以描述为固定 Workflow 中包含 Agent Loop。

### 已答对的部分

- 结论正确：固定轮询仍是 Workflow；
- 已经抓到模型动态决定与固定代码路径的区别；
- 能识别外层 Workflow 和局部 Agent Loop 的嵌套关系。

### 需要修正的部分

“没有根据状态和环境动态执行”不够准确。轮询程序确实读取动态环境状态，真正固定的是“状态到下一步行动”的映射规则。是否使用 LLM 也不是唯一判据：固定节点调用一次 LLM 仍可能只是 Workflow；关键是 LLM 是否获得下一步行动的控制权。

### 参考回答

> 它不是 Agent，而是带条件分支和轮询循环的确定性 Workflow。环境状态会变化，但每种状态对应的动作已经由代码写死。如果只有异常调查节点允许 LLM 动态选择工具，那么这是混合式 Agent 系统：外层是确定性 Workflow，其中包含一个运行 Agent Loop 的 Agent 节点。

> **学习状态**: understood

## Q3 Harness completeness

### 问题

系统加入模型解析失败重试、工具超时后换备用工具、重复调用终止和 Token 预算控制后，是否已经构成完整 Agent Eval Harness？为什么？

### 用户回答记录

用户判断还不是完整 Eval Harness，并认为 Eval Harness 还需要记录和观察模型多次执行过程，做分析、统计和总结，从而帮助 Agent 后续升级。

### 已答对的部分

- 正确判断这些 Runtime 控制不足以构成完整 Eval Harness；
- 正确注意到 Harness 需要运行记录、观察和统计；
- 已经意识到 Eval 结果可以支持后续系统改进。

### 需要修正的部分

- 只有日志和统计仍然更接近 Observability，不是完整 Eval Harness；
- 最关键的缺失项还包括可运行的任务集、可重置环境和明确的 Scorer / Oracle；
- Harness 通常提供改进证据，不会因为记录了轨迹就自动让 Agent “进化”。工程团队或训练流程仍需根据证据修改模型、Prompt、工具或流程，并重新做回归测试。

### 参考回答

> 不能。这些能力主要属于 Agent Loop 的错误恢复、预算控制和防死循环机制。完整 Eval Harness 还需要 Dataset、可初始化和重置的 Environment、Tool Adapter、Runner、Scorer、Sandbox、Trace 和 Replayer。它不仅要记录 Agent 做了什么，还要定义什么叫成功，并保证不同版本能在相同条件下公平、可复现地比较。

> **学习状态**: learning

## Q4 Minimal eval harness

### 问题

为退款客服 Agent 设计一个最小 Eval Harness。Dataset、Environment、Tools、Runner 和 Scorer 中应该放什么？怎样判断一次任务真正成功？

### 用户回答记录

用户认为 Dataset 应包含金额、身份信息和各种真实场景组合；Environment 应提供 Sandbox 或模拟环境，避免接入真实支付系统；Tools 包括支付金额查询、用户信息和数据库查询等工具。用户明确表示尚不理解 Runner 和 Scorer。

### 已答对的部分

- 已能把真实业务场景和初始数据放入 Dataset；
- 已意识到测试不能直接操作生产支付系统；
- 已能列出 Agent 需要使用的业务工具；
- 对未知概念进行了明确标记，没有用模糊术语掩盖理解缺口。

### 需要补充的部分

- Dataset 不是字段集合，而是一组包含任务、初始环境、目标、约束和元数据的可运行 Sample；
- Environment 是完整外部世界，Sandbox 只是其中的隔离设施；Environment 还需要支持 Setup / Reset；
- Runner 负责重置环境、加载固定版本、启动 Agent、控制预算并收集轨迹；
- Scorer 负责根据数据库最终状态、工具轨迹、权限、回复和成本判断任务是否成功。

### 参考回答

> Dataset 保存退款任务、订单初始状态、目标和限制；Environment 提供可重置的模拟订单库和支付系统；Tools 提供查询订单、查询支付、创建退款和转人工等接口；Runner 在统一模型、Prompt、工具版本和预算下逐题启动 Agent 并记录轨迹；Scorer 检查是否为正确订单创建正确金额的退款、是否越权或重复退款，以及最终回复是否与真实状态一致。

> **学习状态**: learning

## Q5 Result versus claim

### 问题

Agent 回复“您的 500 元退款已经成功发起”，但数据库中没有任何退款记录。这次任务怎样判分？为什么不能只看最终文本？

### 用户回答记录

用户表示当时不清楚，并提醒课程应继续围绕两份 PDF 的基础知识，不要扩展过远。

### 讲解后的结论

这次任务必须判失败。Agent 的最终文本只是它对结果的陈述，数据库和支付系统中的最终状态才是实际业务事实。就像工作人员声称已经退款，但支付系统没有退款流水，任务实际上没有完成。

这一问题直接对应 7 月版 PDF 对 Harness 价值的说明：工具行为或环境状态可能错误，但最终语言仍可能包装得像正确答案。因此评测必须检查真实环境结果，不能只看文本质量。

> **学习状态**: learning；待后续脱稿复测

## Q6 Loop versus harness

### 问题

只用一句话说明：Agent Loop 和 Agent Harness 最核心的区别是什么？

### 用户回答记录

用户认为 Agent Loop 管理核心业务 Agent 的运行过程，例如数据输入、模型输入输出和工具使用；Harness 则在此基础上增加系统化错误兜底、可追溯和可观察能力、Sandbox，以及额外的流程测试、记录和检查。

### 已答对的部分

- 已能把模型调用和工具使用放入 Agent Loop；
- 已能把 Sandbox、过程记录、可观察性和测试检查与 Harness 联系起来。

### 需要修正的部分

Harness 不是“Loop 再多出一些功能”，二者是内外层关系。Loop 自己也可以包含解析重试、工具错误恢复、预算和重复调用检测。Harness 的决定性边界是从外部提供任务和环境、运行和限制 Loop、记录轨迹、判分并复现。

### 最终精髓

> **Agent Loop 管 Agent 内部怎样循环做事；Agent Harness 管外部怎样让这个 Loop 在可控环境中运行、被记录、被评测和被复现。**

用户在讲解后表示已经理解，因此没有再次口述。当前记录为 `understood / 待复习`，不能标记为 `fluent`。

## 后续复习题

1. 不使用“动态”这个模糊词，改用“下一步控制权”解释 Agent 与 Workflow；
2. 用一分钟稳定说明 Agent、Workflow、Agent Loop 和 Harness 的层次；
3. 说明为什么 Loop 中的错误重试不等于完整 Eval Harness；
4. 用退款场景分别举例 Dataset、Environment、Runner 和 Scorer；
5. 解释为什么真实环境状态比最终文本更能证明任务成功。
