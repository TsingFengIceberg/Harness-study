# SWE Agent Evaluation References

> **状态**: source archive | **用途**: SWE Agent 评测论文原文归档

本目录保存 SWE Agent evaluation 学习所依赖的外部原始资料。学习笔记、证据状态和面试问答统一维护在 [SWE Agent Evaluation Learning](../../DOCS/interview/swe-agent-evaluation/README.md)，不要把论文原文与二次整理混为一类证据。

**papers/** 是本机论文档案，已由 .gitignore 排除，不会随仓库提交。表格同时保留官方 arXiv 页面作为可移植来源；其他机器没有本地 PDF 时，应从官方入口获取并核对版本。

## 论文索引

| 论文 | 本地原文 | 官方入口 | 学习笔记 |
|---|---|---|---|
| Jimenez et al., 2024, *SWE-bench: Can Language Models Resolve Real-World GitHub Issues?* | [PDF](papers/swe-bench-2024.pdf) | [arXiv:2310.06770](https://arxiv.org/abs/2310.06770) | [SWE-bench](../../DOCS/interview/swe-agent-evaluation/swe-bench.md) |
| Yang et al., 2024, *SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering* | [PDF](papers/swe-agent-2024.pdf) | [arXiv:2405.15793](https://arxiv.org/abs/2405.15793) | [七篇演进综述](../../DOCS/interview/swe-agent-evaluation/post-swe-bench-evolution.md#swe-agent接口本身就是能力) |
| Xia et al., 2024, *Agentless: Demystifying LLM-based Software Engineering Agents* | [PDF](papers/agentless-2024.pdf) | [arXiv:2407.01489](https://arxiv.org/abs/2407.01489) | [七篇演进综述](../../DOCS/interview/swe-agent-evaluation/post-swe-bench-evolution.md#agentless固定工作流也能很强) |
| Wang et al., 2025, *OpenHands: An Open Platform for AI Software Developers as Generalist Agents* | [PDF](papers/openhands-2025.pdf) | [arXiv:2407.16741](https://arxiv.org/abs/2407.16741) | [七篇演进综述](../../DOCS/interview/swe-agent-evaluation/post-swe-bench-evolution.md#openhands从单个-agent-到通用平台) |
| Pan et al., 2025, *Training Software Engineering Agents and Verifiers with SWE-Gym* | [PDF](papers/swe-gym-2025.pdf) | [arXiv:2412.21139](https://arxiv.org/abs/2412.21139) | [七篇演进综述](../../DOCS/interview/swe-agent-evaluation/post-swe-bench-evolution.md#swe-gym把评测任务变成训练场) |
| Yang et al., 2025, *SWE-smith: Scaling Data for Software Engineering Agents* | [PDF](papers/swe-smith-2025.pdf) | [arXiv:2504.21798](https://arxiv.org/abs/2504.21798) | [七篇演进综述](../../DOCS/interview/swe-agent-evaluation/post-swe-bench-evolution.md#swe-smith先造环境再规模化造-bug) |
| Badertdinov et al., 2025, *SWE-rebench: An Automated Pipeline for Task Collection and Decontaminated Evaluation of Software Engineering Agents* | [PDF](papers/swe-rebench-2025.pdf) | [arXiv:2505.20411](https://arxiv.org/abs/2505.20411) | [七篇演进综述](../../DOCS/interview/swe-agent-evaluation/post-swe-bench-evolution.md#swe-rebench把新鲜度做成评测制度) |
| Zhang et al., 2025, *SWE-bench Goes Live!* | [PDF](papers/swe-bench-live-2025.pdf) | [arXiv:2505.23419](https://arxiv.org/abs/2505.23419) | [七篇演进综述](../../DOCS/interview/swe-agent-evaluation/post-swe-bench-evolution.md#swe-bench-live持续纳入近期真实-issue) |

## 使用规则

- 论文事实优先从本地 PDF 或官方版本核验，并在笔记中标明章节或表格。
- 当前 benchmark 仓库、数据版本和 leaderboard 属于会变化的信息，不能仅凭论文原文宣称为当前事实。
- 后续论文采用稳定的 ASCII 文件名归档，避免标题变化或下载器命名影响文档链接。
- 本地 PDF 不提交；提交范围只包含来源索引与自有学习笔记。
