# SWE Agent Evaluation Learning

> **日期**: 2026-08-05 | **状态**: draft | **当前阶段**: SWE-bench 与七篇后续论文第一轮

本专项研究如何评测 Software Engineering Agent。主线不是只看 leaderboard，而是同时理解论文提出的问题、benchmark instance 的构造、可执行环境、Agent rollout、补丁协议、Scorer、污染与复现边界，最后形成可以解释和比较不同 SWE benchmark 的工程认知。

## 研究边界

需要持续区分四类对象：

| 对象 | 回答的问题 |
|---|---|
| Benchmark paper | 为什么这样出题、样本怎样构造、指标是否有效、有哪些局限？ |
| Benchmark repository | instance、Docker、Runner、patch、test 与 report 实际怎样实现？ |
| Agent / Harness | 被测 Agent 如何搜索、编辑、执行测试并在预算内结束？ |
| Leaderboard result | 在特定模型、Harness、预算、重试和数据版本下取得了什么结果？ |

论文中的数据构造、实验设置和作者结论可以按官方论文标为 verified；对当前代码、当前数据集、当前 leaderboard 或其他项目的推断必须重新核验，不能沿用论文发表时的状态。

## 当前文档

| 文档 | 证据状态 | 学习状态 | 说明 |
|---|---|---|---|
| [SWE-bench 原始论文](swe-bench.md) | official-paper / verified | learning | 从函数级代码生成转向真实 GitHub issue resolution 的原点论文。 |
| [SWE-bench 之后的七篇代表性工作](post-swe-bench-evolution.md) | official-paper / verified | learning | ACI、固定工作流、通用平台、训练数据和持续更新评测的演进。 |
| [SWE Agent Evaluation 面试 QA](qa.md) | mixed，逐题标注 | learning | 量化指标、历史任务新鲜度和公开/私有评测边界。 |

原始资料统一归档在 [SWE Agent Evaluation References](../../../references/swe-agent-evaluation/README.md)。PDF 是本地忽略文件，笔记同时保留论文网站链接，确保不依赖本机资料也能追溯来源。

## 论文路线

| 阶段 | 论文 | 本地 PDF | 论文网站 | 状态 | 重点 |
|---|---|---|---|---|---|
| 原点 | SWE-bench | [PDF](../../../references/swe-agent-evaluation/papers/swe-bench-2024.pdf) | [arXiv](https://arxiv.org/abs/2310.06770) | learning | 真实 issue、仓库快照、patch 与测试判分。 |
| Agent / Interface | SWE-agent | [PDF](../../../references/swe-agent-evaluation/papers/swe-agent-2024.pdf) | [arXiv](https://arxiv.org/abs/2405.15793) | learning | Agent-Computer Interface 与 Harness 对成绩的影响。 |
| Fixed Workflow | Agentless | [PDF](../../../references/swe-agent-evaluation/papers/agentless-2024.pdf) | [arXiv](https://arxiv.org/abs/2407.01489) | learning | 定位、修复、验证的固定流程与复杂 Agent loop 的比较。 |
| General Platform | OpenHands | [PDF](../../../references/swe-agent-evaluation/papers/openhands-2025.pdf) | [arXiv](https://arxiv.org/abs/2407.16741) | learning | Event stream、Runtime、Sandbox、Skills 与统一评测平台。 |
| 训练环境 | SWE-Gym | [PDF](../../../references/swe-agent-evaluation/papers/swe-gym-2025.pdf) | [arXiv](https://arxiv.org/abs/2412.21139) | learning | 真实任务、轨迹、Verifier 与 inference-time scaling。 |
| 规模化数据 | SWE-smith | [PDF](../../../references/swe-agent-evaluation/papers/swe-smith-2025.pdf) | [arXiv](https://arxiv.org/abs/2504.21798) | learning | 自动构建环境、程序变异和大规模训练任务。 |
| 新鲜度 | SWE-rebench | [PDF](../../../references/swe-agent-evaluation/papers/swe-rebench-2025.pdf) | [arXiv](https://arxiv.org/abs/2505.20411) | learning | 自动收集、公开训练集、中心化新鲜评测。 |
| 新鲜度 | SWE-bench Live | [PDF](../../../references/swe-agent-evaluation/papers/swe-bench-live-2025.pdf) | [arXiv](https://arxiv.org/abs/2505.23419) | learning | 持续更新、污染控制和自动任务生产。 |
| 广度 | Multi-SWE-bench / SWE-bench Multimodal | 待收录 | 待核验 | planned | 多语言、多生态与视觉软件任务。 |
| 新任务形态 | SWT-Bench / SWE-Lancer / Ambig-SWE | 待收录 | 待核验 | planned | 测试生成、真实经济任务和人机澄清。 |

## 默认学习方法

1. 先读论文的问题定义、数据构造、评测协议、实验和局限，不逐句翻译。
2. 用一个具体 instance 串起 repo + base commit + issue -> rollout -> model patch -> tests -> resolved。
3. 再读官方仓库，把论文描述映射到数据字段、Docker、Runner、Grading 和日志。
4. 区分模型能力与 Harness、工具、上下文、预算、重试和采样带来的提升。
5. 每篇完成后形成通俗机制、30 秒回答、2 分钟回答、局限和连续追问。

## 相关入口

- [Agent 面试学习](../agent/README.md)
- [Agent Eval Harness 知识笔记](../agent/topics/agent-eval-harness.md)
- [OpenHands 学习入口](../../projects/openhands/README.md)
- [本地论文资料集](../../../references/swe-agent-evaluation/README.md)
- [SWE-bench 官方论文](https://arxiv.org/abs/2310.06770)
- [SWE-bench 官方仓库](https://github.com/SWE-bench/SWE-bench)

## 当前下一步

第一轮已经完成原始 SWE-bench 与七篇后续论文的机制梳理。下一步适合回到官方仓库核验当前 instance schema、Docker evaluation flow 和 leaderboard 版本，再选择一个现代 Agent 的完整 rollout 做端到端复盘。
