# SWE Agent Evaluation 面试 QA

> **日期**: 2026-08-05 | **证据状态**: mixed，逐题标注 | **学习状态**: learning

本页记录 SWE-bench 学习过程中已经展开讨论的追问。机制正文见 [SWE-bench 原始论文详解](swe-bench.md)，后续路线见 [七篇代表性工作演进](post-swe-bench-evolution.md)。

## QA-1：SWE-bench 的量化指标有哪些

> **状态**: verified
> **来源**: official-paper
> **知识索引**: [论文里的量化指标](swe-bench.md#论文里的量化指标)

**回答**：主指标是任务级 **% Resolved**，即同时通过全部 FAIL_TO_PASS 和 PASS_TO_PASS 的任务比例。它是严格 0/1 判分，部分修好不能算 resolved。

辅助指标用于解释为什么失败：

- % Apply 看生成 patch 能否应用；
- F2P/P2P 六类结果区分完整解决、部分解决、无效修改和回归；
- Retrieval 的 Avg/Any/All 看相关文件或位置是否被检索到；
- Patch Fix%、修改文件/函数/行数分析生成补丁；
- 上下文长度、成本等分析资源与表现的关系。

**面试精髓**：主指标回答“最后有没有修好”，辅助指标回答“卡在定位、补丁格式、目标测试还是回归”。

## QA-2：今天的 SWE-bench 任务是否仍以大模型普及前的旧代码为主

> **状态**: verified for original paper / to-verify for changing current suites
> **来源**: official-paper + discussion
> **知识索引**: [环境、数据年代与污染边界](swe-bench.md#环境数据年代与污染边界)

**回答**：对原始 SWE-bench，大体可以这样说。论文对 2,140 个任务的时间分析显示约 88.6% 早于 2023 年，因此原始集合大部分来自生成式 AI 大规模进入编码流程之前。

但要区分几个名字：

- 原始 SWE-bench 是历史静态集合；
- SWE-bench Lite 是较小子集，不代表更新；
- SWE-bench Verified 是人工筛选的 500 题，重点是清晰度和可判性，也不代表更新；
- SWE-rebench、SWE-bench Live 等后续工作才专门把近期任务和持续更新作为目标。

旧任务的好处是更可能自然产生、便于稳定复现；风险是公开 issue、PR 和代码可能已经进入模型训练，而且依赖和工程分布会陈旧。不能仅凭发布日期断言某个模型被污染，也不能把 Verified 当成去污染的新鲜集。

## QA-3：LMArena 和 Artificial Analysis 的 SWE 评测框架与数据是否公开

> **状态**: to-verify-current
> **来源**: official-sites checked during discussion on 2026-08-05
> **知识索引**: [模型分数不是模型单变量](post-swe-bench-evolution.md#模型分数不是模型单变量)

**回答**：不能简单回答“全公开”或“全不公开”，应分层看方法、Runner、题目、用户数据和 verifier。

### LMArena / Copilot Arena

- 排名实现和部分后端代码公开，Copilot Arena 也公开了仓库和经过检查的样本；
- 生产环境中的完整用户 prompt、投票、过滤规则和当前全量数据并没有端到端公开；
- 它的核心是开发者对候选补全的盲测偏好，不是 SWE-bench 那种“在仓库 issue 上运行测试”的 executable resolution benchmark。

所以它更适合回答“真实交互中开发者更偏好哪个输出”，不能与 % Resolved 当成同一种指标。

### Artificial Analysis

截至 2026-08-05 前次讨论核验，Coding Agent Index v1.3（2026-07）公开了方法说明、任务组成、任务标识、pass@1、成本、token 和运行时间等结果。该版本组合：

    DeepSWE:           113
    Terminal-Bench v2: 84
    SWE-Atlas-QnA:     124
    总计:              321
    每题 3 次尝试

但完整内部 Runner、全部任务内容和所有 verifier 并非端到端公开。另一个 AA-AgentPerf 评测明确保持完整测试集私有。

**面试精髓**：公开 methodology 和 task IDs 不等于完整 benchmark 可本地复现；私有题目有利于抗污染，却降低外部审计和复现能力。评价此类榜单时要逐层问“公开了什么、隐藏了什么、隐藏的部分会不会影响排名”。

## 待复习追问

1. 为什么 executable tests 比 LLM-as-Judge 更适合判仓库修复？它又遗漏了什么？
2. pass@1、mean、SEM、pass@5 分别怎样反映随机 Agent 的能力？
3. 同一个模型换 Harness 后分数大幅变化，比较时应锁定哪些变量？
4. 新鲜私有测试集与完全公开可复现之间怎样取舍？
