# SWE-bench 之后：七篇代表性工作的演进

> **日期**: 2026-08-05
> **范围**: SWE-agent、Agentless、OpenHands、SWE-Gym、SWE-smith、SWE-rebench、SWE-bench Live
> **证据状态**: official-paper / verified | **学习状态**: learning

## 相关入口

- [SWE Agent Evaluation 学习入口](README.md)
- [SWE-bench 原始论文详解](swe-bench.md)
- [SWE Agent Evaluation 面试 QA](qa.md)
- [本地论文资料集与官方网站](../../../references/swe-agent-evaluation/README.md)

## 一条主线看懂七篇论文

原始 SWE-bench 提出了“真实 issue + 仓库快照 + executable tests”的问题。后续工作主要沿三条轴推进：

    怎样让 Agent 做得更好？
      -> SWE-agent 的 ACI
      -> Agentless 的固定工作流
      -> OpenHands 的通用平台

    怎样获得足够训练数据？
      -> SWE-Gym 的真实可执行训练任务
      -> SWE-smith 的规模化合成任务

    怎样让评测保持新鲜和可比较？
      -> SWE-rebench 的自动收集与中心化评测
      -> SWE-bench Live 的持续更新 benchmark

> **精髓**：后续论文不只是“换更强模型刷分”。它们分别改造 Agent 与计算机的接口、控制流程、运行平台、训练数据生产和 benchmark 更新制度。

## 总览

| 工作 | 本地 PDF | 论文网站 | 核心问题 | 代表性事实 |
|---|---|---|---|---|
| SWE-agent | [PDF](../../../references/swe-agent-evaluation/papers/swe-agent-2024.pdf) | [arXiv](https://arxiv.org/abs/2405.15793) | 怎样设计更适合 LM 的 Agent-Computer Interface？ | GPT-4 Turbo：Full 12.47%，Lite 18.00%。 |
| Agentless | [PDF](../../../references/swe-agent-evaluation/papers/agentless-2024.pdf) | [arXiv](https://arxiv.org/abs/2407.01489) | 是否一定需要自由规划的 autonomous Agent loop？ | Lite 32.00%，平均约 $0.70。 |
| OpenHands | [PDF](../../../references/swe-agent-evaluation/papers/openhands-2025.pdf) | [arXiv](https://arxiv.org/abs/2407.16741) | 怎样构建可扩展、可复用的软件开发 Agent 平台？ | 统一 State/Event、Action/Observation、Runtime 与评测框架。 |
| SWE-Gym | [PDF](../../../references/swe-agent-evaluation/papers/swe-gym-2025.pdf) | [arXiv](https://arxiv.org/abs/2412.21139) | 从哪里获得可训练 Agent 和 verifier 的真实轨迹？ | 11 个不重合仓库、2,438 个真实可执行任务。 |
| SWE-smith | [PDF](../../../references/swe-agent-evaluation/papers/swe-smith-2025.pdf) | [arXiv](https://arxiv.org/abs/2504.21798) | 怎样大规模制造有环境、有测试的训练任务？ | 128 个仓库、50,137 个任务。 |
| SWE-rebench | [PDF](../../../references/swe-agent-evaluation/papers/swe-rebench-2025.pdf) | [arXiv](https://arxiv.org/abs/2505.20411) | 怎样自动收集新任务并降低 benchmark 过拟合？ | 21,336 个训练任务；新鲜评测集 294 题、169 个仓库。 |
| SWE-bench Live | [PDF](../../../references/swe-agent-evaluation/papers/swe-bench-live-2025.pdf) | [arXiv](https://arxiv.org/abs/2505.23419) | 怎样持续发布近期真实 issue 任务？ | 首版 1,319 题、93 个仓库，覆盖 2024 至 2025-04。 |

数字用于理解论文当时的实验与数据版本，不代表 2026-08 的当前 leaderboard。

## SWE-agent：接口本身就是能力

SWE-agent 的核心不是简单地“让 GPT-4 多调用几次 shell”，而是设计一套 LM 更容易正确使用的 ACI（Agent-Computer Interface）。

人类终端命令能力强但反馈冗长，语言模型容易迷失。SWE-agent 提供面向代码定位、查看和编辑的简洁命令，控制单次观察长度，对编辑范围和语法提供明确反馈，并用 guardrail 阻止明显无效操作。

    读 issue -> 搜索 -> 查看文件 -> 编辑 -> 运行测试
            ^                         |
            +------ 根据反馈修正 <----+

论文使用 GPT-4 Turbo 在 SWE-bench Full 报告 12.47%（286/2,294），在 Lite 报告 18.00%（54/300）。它说明固定模型的表现会被 Harness 和交互接口显著改变。

边界是：成绩提升不能全部归因于“模型变聪明”，ACI、提示、工具和预算都是实验变量。更多自由命令也不一定更强；对 LM 来说，动作简单、反馈明确往往比完整 Unix 能力更可用。

## Agentless：固定工作流也能很强

Agentless 把仓库修复拆成确定性的“定位 -> 修复 -> 验证”流水线，不让模型在开放工具空间里自由决定下一步：

    Localization
      仓库级 -> 文件级 -> 类/函数级定位
            |
            v
    Repair
      对候选位置生成多个补丁
            |
            v
    Validation
      过滤、排序并选择候选补丁

它仍然使用 LLM，但 LLM 被放进预先设计的步骤中；“Agentless”不是“没有模型”，而是没有通用 autonomous tool-planning loop。

论文在 SWE-bench Lite 报告 32.00%（96/300），平均成本约 $0.70。核心启示是：当任务结构稳定、关键中间产物可定义时，固定工作流可以减少漫游、循环失控和无效 token。

SWE-agent 让模型根据 observation 动态选动作，适合交互探索；Agentless 预先规定阶段，过程更可控但可能错过流程外的修复路径。二者不是“Agent 一定优于 workflow”的胜负关系，而是在不同不确定性下选择控制权放在哪里。

## OpenHands：从单个 Agent 到通用平台

OpenHands 把软件开发 Agent 所需的事件、状态、工具执行、隔离环境、能力扩展和评测接入做成通用平台，而不是只发布一条刷 benchmark 的脚本。

- **State / Event Stream**：所有动作、观察和状态变化形成可追踪事件流。
- **Action / Observation**：Agent 提出动作，Runtime 执行后返回观察，形成统一交互协议。
- **Docker Runtime**：代码和命令在隔离环境中执行。
- **Action API / Skills**：既能用底层操作，也能加载更高层的复用能力。
- **AgentHub 与 delegation**：允许接入不同 Agent 实现及委派结构。
- **Evaluation framework**：把同一 Agent/Runtime 接到不同 benchmark。

通俗地说，SWE-agent 更像设计了一套“适合模型使用的维修工具箱”；OpenHands 更像建设“维修工位、隔离车间、操作日志、工具插件和统一考场”。

平台统一了基础设施，但不会自动消除 Agent 策略差异。模型、提示、工具集、预算、Runtime 镜像和 benchmark adapter 仍然决定结果，复现实验时必须完整记录。

## SWE-Gym：把评测任务变成训练场

SWE-Gym 关注的不是再做一个静态测试榜，而是构造与 SWE-bench 仓库不重合的真实、可执行训练任务，用成功/失败轨迹训练 Agent 和 verifier。

- 从 11 个与 SWE-bench test 不重合的仓库构造 2,438 个真实任务；
- 每个任务有仓库环境和测试验证，不只是一对自然语言与代码文本；
- Agent rollout 产生搜索、编辑、测试等轨迹；
- outcome verifier 学习判断候选修复质量；
- 推理时可生成多个候选，用 verifier 做 best-of-N 选择。

这把问题从“给模型更多代码语料”变成“给 Agent 更多带环境反馈和最终结果的练习”。边界是失败轨迹并不直接告诉每一步错在哪里，best-of-N 也要支付多次 rollout 成本；仓库不重合有助于减少直接记忆，但不能证明底层模型从未见过相关公开代码。

## SWE-smith：先造环境，再规模化造 Bug

SWE-smith 以“可执行仓库环境”为基础，通过 LM mutation/rewrite、AST mutation、组合多个 bug 和 PR inversion 等方式批量制造 bug 与修复任务，再用测试执行过滤不可验证任务。

最终形成 128 个仓库、50,137 个任务。只有“错误代码 + 描述”不够训练工程 Agent，任务还必须能安装依赖、触发失败、应用修复并验证结果。SWE-smith 把环境可构建性放在数据规模化之前，避免生产大量无法执行的文本样本。

边界是合成 bug 可能比真实 issue 更局部、更规则，描述也可能泄露变异方式。规模大不等于分布真实，因此这类数据更适合训练，不能未经验证就替代真实世界评测。

## SWE-rebench：把新鲜度做成评测制度

SWE-rebench 建立自动任务收集流水线，同时把公开训练数据与中心化、保持隐藏的新鲜评测分开：

- 大规模公开数据包含 21,336 个可验证任务，来自 3,468 个仓库；
- 论文的新鲜 benchmark 包含 294 个任务，覆盖 169 个仓库；
- 使用固定的最小 ReAct scaffold，减少私有 Harness 对比较的干扰；
- 每个任务运行五次，并报告 mean、SEM 与 pass@5，显式呈现随机性。

如果所有新题、测试和答案立即公开，它们很快又会进入训练集。中心化 Runner 可以在服务端运行隐藏任务和 verifier，延缓污染。代价是外界无法在本地完整重放私有 leaderboard，公开性与去污染之间存在真实取舍。

## SWE-bench Live：持续纳入近期真实 Issue

SWE-bench Live 使用自动化流水线持续从近期 GitHub issue/PR 构造任务，直接应对固定 benchmark 的陈旧与污染。首版包含 1,319 个任务、93 个仓库，issue 时间覆盖 2024 年至 2025 年 4 月；RepoLaunch 负责自动建立 Docker 环境，论文规划按月更新。

论文在相同 OpenHands + Claude 3.7 设置下报告：

    SWE-bench Verified: 43.20%
    SWE-bench Live:     19.25%

这个落差说明静态旧榜分数可能高估 Agent 面对新任务的表现，但不能把全部差距直接证明为“训练污染”：两个集合在仓库分布、任务难度、测试和筛选标准上也不同。

近期任务只能降低已知污染风险，不能证明模型供应商的训练截止日期和数据来源。持续更新还会让不同时间提交的系统面对不同快照，因此必须版本化榜单和评测窗口。

## 七篇论文放在一起后的工程结论

### 模型分数不是模型单变量

一个 SWE benchmark 结果至少由模型、Agent 策略、ACI/工具、检索与上下文、Runtime、时间和成本预算、采样次数、benchmark 版本及 scorer 共同决定。

正确表述是“某系统在某版本 benchmark、某 Harness 和预算下取得多少”，而不是“某模型的软件工程能力等于某个百分比”。

### Agent 与 Workflow 没有绝对胜负

SWE-agent 证明高质量交互接口能释放动态 Agent 能力；Agentless 证明稳定的任务结构可以用固定工作流获得很强结果。生产系统通常混合两者：外层用确定性阶段控制预算、权限和验收，在代码定位或调试等高不确定步骤里允许 Agent loop，最终用 executable tests 和 verifier 收口。

### 训练集和评测集必须分工

SWE-Gym、SWE-smith 追求可训练任务的数量和轨迹；SWE-rebench、SWE-bench Live 追求新鲜评测。训练集需要开放和规模，评测集需要代表性、隐藏性与稳定性，不能要求同一个集合同时最大化所有目标。

### 未来前沿不是单纯扩大题数

- 自动构建更多语言和生态的可靠环境；
- 持续去重、去污染并记录任务版本；
- 同时报告成功率、成本、延迟和方差；
- 评价测试之外的安全、可维护性与人类协作；
- 区分底层模型、Harness 和 inference-time scaling 的贡献；
- 让私有新鲜评测具备足够透明的方法和可审计性。

## 面试表达

### 30 秒回答

SWE-bench 之后的工作主要分三类：SWE-agent、Agentless 和 OpenHands 研究怎样通过 ACI、固定工作流或通用平台让 Agent 更有效；SWE-Gym 和 SWE-smith 研究怎样生产可执行训练任务与轨迹；SWE-rebench 和 SWE-bench Live 研究怎样持续收集新题、控制污染并更可靠地报告结果。共同结论是 SWE 成绩不只是模型能力，还取决于 Harness、工具、预算、采样、环境和 benchmark 版本。

### 高频追问

1. SWE-agent 的 ACI 与普通 shell 工具有何区别？
2. Agentless 没有 autonomous loop，为什么仍然使用 LLM？
3. OpenHands 是 Agent 算法还是 Agent 平台？
4. SWE-Gym 与 SWE-smith 的真实任务和合成任务分别适合什么？
5. SWE-rebench 为什么选择中心化评测，它牺牲了什么？
6. SWE-bench Live 分数更低能否直接证明旧榜被污染？
