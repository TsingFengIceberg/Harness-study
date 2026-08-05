# SWE-bench：真实 GitHub Issue Resolution 评测原点

> **论文网站**: [SWE-bench: Can Language Models Resolve Real-World GitHub Issues?](https://arxiv.org/abs/2310.06770)
> **本地 PDF**: [swe-bench-2024.pdf](../../../references/swe-agent-evaluation/papers/swe-bench-2024.pdf)
> **会议**: ICLR 2024 | **本地版本**: arXiv v3
> **证据状态**: official-paper / verified | **学习状态**: learning

## 相关入口

- [SWE Agent Evaluation 学习入口](README.md)
- [七篇后续论文：从 ACI 到持续更新评测](post-swe-bench-evolution.md)
- [SWE Agent Evaluation 面试 QA](qa.md)
- [SWE Agent Evaluation 原始资料集](../../../references/swe-agent-evaluation/README.md)
- [SWE-bench 官方仓库](https://github.com/SWE-bench/SWE-bench)
- [SWE-bench 官方网站](https://www.swebench.com/)

## 一句话定位

SWE-bench 把代码能力评测从“根据短题目写一个函数”推进到“根据真实 GitHub issue，在指定仓库版本上产出可应用的补丁，并用真实项目测试判断问题是否解决”。

它的关键进步不只是题目更长，而是把真实 issue、真实仓库快照、开发者实际修复、能暴露问题的测试和可复现的执行环境绑成一个可执行评测。

## 为什么函数题不够

HumanEval 一类函数级题目通常已经告诉模型函数签名、局部需求和输入输出。模型主要回答“这段算法怎样实现”。真实软件工程任务还要先回答：

1. 问题究竟落在哪些文件、类和函数？
2. issue 里的自然语言怎样映射到现有架构和历史行为？
3. 哪些旧行为必须保持，哪些边界条件需要新增？
4. 修改能否在原项目依赖和测试系统里运行？
5. 最终交付的是一个能应用到仓库的 patch，而不是一段孤立代码。

因此 SWE-bench 测的是一条更长的因果链：

    理解问题 -> 定位代码 -> 理解依赖 -> 设计修改 -> 生成补丁 -> 执行测试 -> 避免回归

这仍不等于完整生产开发。它没有完整衡量需求澄清、代码评审、上线、监控和长期维护，但比函数补全更接近仓库级软件工程。

## 数据是怎样构造出来的

### 从 Pull Request 反推一道题

论文寻找“issue 与修复 PR 对应，并且 PR 中有测试变化”的历史记录：

    issue 文本                     -> 给被测系统的问题描述
    PR 合并前的 base commit        -> 待修复仓库起点
    PR 中的生产代码修改            -> gold patch / 参考修复
    PR 中的测试修改                -> test patch / 判题依据

开发者当年的 patch 证明这个问题至少存在一个实际修复路径；测试变化则帮助判断模型补丁是否恢复预期行为。

### 过滤漏斗

论文附录给出的完整漏斗是：

    93,139 个抓取到的 PR
            |
            v
    11,407 个候选任务
            |
            v
    2,294 个通过环境与测试验证的任务
            |
            v
    12 个 Python 开源仓库

大量候选会因 issue/PR 关系、测试不可执行、依赖环境无法复现或补丁无法形成稳定判据而被过滤。最终 2,294 不是“随机 2,294 个 issue”，而是满足论文采集和可执行性条件的子集。

这也带来选择偏差：容易建立环境、能用测试表达、来自活跃 Python 项目的问题更容易进入 benchmark；难以自动验证的产品、运维、安全或交互问题会被低估。

## 一个 instance 里有什么

| 组成 | 作用 |
|---|---|
| **problem_statement** | issue 标题和正文，交给模型理解需求。 |
| **repo** | 任务来自哪个 GitHub 仓库。 |
| **base_commit** | 必须从哪个历史快照开始修复。 |
| **patch** | 开发者当年的生产代码修改，即 gold patch；通常不交给被测模型。 |
| **test_patch** | PR 中用于暴露和验证问题的测试修改；评测时由 Harness 应用。 |
| **FAIL_TO_PASS** | 在 base 状态失败、修复后应通过的测试。 |
| **PASS_TO_PASS** | 修复前已通过、修复后仍必须通过的回归测试。 |

可以把它理解为一张“历史维修工单”：problem statement 是报修描述，base commit 是故障发生时的机器快照，gold patch 是原维修人员的方案，test patch 和两组测试是验收清单。模型需要提交自己的维修方案，不要求逐字复刻 gold patch。

### Gold patch 不是唯一标准答案

最终判分主要看测试，而不是把模型 patch 与开发者 patch 做文本相似度比较。只要模型采用了另一种正确实现，并通过规定测试，也可以被判为 resolved。

这既是优点也是边界：测试允许多种实现，却也可能漏掉未编码进测试的错误。通过测试不能自动推出补丁安全、可维护、高效、风格良好或已经达到生产质量。

## Evaluation Harness 怎样判分

对一个任务，逻辑流程可以概括为：

    1. checkout repo@base_commit
    2. 安装或激活该任务对应的依赖环境
    3. 应用 benchmark 的 test_patch
    4. 应用模型提交的 model patch
    5. 执行指定测试
    6. 检查 FAIL_TO_PASS 与 PASS_TO_PASS
    7. 生成该 instance 的评测结果

### 为什么要同时看两组测试

只看 FAIL_TO_PASS 会奖励“让新需求通过，但破坏旧功能”的补丁。只看 PASS_TO_PASS 又无法证明 issue 被修复。

严格 resolved 的核心条件是全部 FAIL_TO_PASS 通过，并且全部 PASS_TO_PASS 继续通过，也就是“新问题确实修好，并且指定的旧行为没有被破坏”。

### 六类诊断结果

| 结果 | 直观解释 |
|---|---|
| Resolved | 应修测试全部通过，回归测试也全部保持。 |
| Breaking Resolved | 应修测试通过了，但破坏了原本通过的行为。 |
| Partially Resolved | 修复了一部分目标测试，且没有造成指定回归。 |
| Work in Progress | 修了一部分目标，但同时产生回归。 |
| No-Op | 没有修好目标，也没有让指定旧测试变差。 |
| Regression | 目标没修好，还破坏了旧测试。 |

这些类别适合解释失败原因，但 leaderboard 的主指标仍是严格的任务级 **% Resolved**，不能把“部分通过”混成“解决”。

### Harness 能修什么，不能修什么

原始实验要求模型输出 patch。Harness 可以对常见输出格式做有限清理，例如从 Markdown 中提取 diff、补全可解析的 patch 上下文或处理头部格式；它不能替模型修正业务逻辑。

因此 **% Apply** 是重要诊断：patch 连仓库都应用不上，后面无从测试；但 apply 成功也不代表问题被修复。

## 论文里的量化指标

### 主指标：% Resolved

    Resolved tasks / evaluated tasks * 100%

这是最重要、最严格也最容易被引用的指标。它是 instance 级 0/1 判分：一个任务即使通过 9/10 个目标测试，严格指标下仍不是 resolved。

### 执行诊断

- **% Apply**：模型 patch 能否应用到 base commit。
- **F2P / P2P 结果分布**：区分完整修复、部分修复、无效修改和回归。
- **Patch Fix %**：分析生成 patch 与 gold patch 所涉及位置的关系，属于诊断而非最终正确性。
- **修改规模**：文件、函数、行数等，用于理解任务和生成补丁的复杂度。
- **成本与上下文**：调用成本、输入长度和不同上下文策略的表现。

### Retrieval 指标

| 指标 | 含义 |
|---|---|
| Avg | 平均找回多少相关项。 |
| Any | 是否至少找回一个相关项。 |
| All | 是否找回全部相关项。 |

检索命中 gold patch 位置不等于补丁正确；没有命中全部 gold 位置也不一定无法通过另一条正确路径修复。

## 原始实验告诉了我们什么

### 低分不只是“模型不会写代码”

论文基线不是今天常见的完整 Coding Agent。模型主要基于准备好的仓库上下文一次性、贪心地产生一个 patch，并没有在 shell、编辑器和测试结果之间持续观察、修改、重试。

所以原始成绩混合测量了模型理解 issue 和代码、检索器定位、上下文组织、patch 格式和非交互式生成协议等因素。不能把 1.96% 简化成“Claude 2 只有 1.96% 软件工程能力”，也不能拿它与使用现代 Agent Harness、多次工具调用和不同预算的成绩直接横比。

### 更多上下文反而可能更差

| 上下文预算 | % Resolved |
|---|---:|
| 13K | 1.96% |
| 27K | 1.87% |
| 50K | 1.22% |

更长上下文提升了部分 retrieval recall，却没有提升最终解决率。原因不能仅由表格确定，但它至少说明：

> **精髓**：上下文容量是“能放多少”，检索和组织决定“放什么、以什么顺序放”，模型注意力决定“能否真正利用”。更多噪声不等于更多有效信息。

### Oracle 仍然不高

给模型 gold patch 涉及的文件后，Claude 2 约解决 4.8%；进一步把 oracle 内容压缩到相关位置后约为 5.93%。定位正确明显有帮助，但远非充分条件：模型还需要理解跨代码关系、构造正确修改并避免回归。

### 版本数字要谨慎引用

本地保存的是 arXiv v3。摘要仍写 Claude 2 的 1.96% 是最佳结果，而更新后的 Table 5 已包含 Claude 3 Opus 3.79%。这是同一 PDF 内摘要与后续修订表格的版本不一致。

面试或文档中引用数字时应说清“原始基线”或“arXiv v3 更新表格”，不要把不同版本的结果混成同一实验快照。

## 环境、数据年代与污染边界

### 原论文的环境并非今天的 Docker 体系

原始工作为仓库和版本手工配置 Conda 环境。后来 SWE-bench 工程才逐步提供更标准化的 Docker 镜像和评测基础设施。读论文时不能把今天官方仓库的实现倒写成 2023 年论文已经具备。

### 数据为什么大多仍是旧代码

原始 benchmark 来自历史 issue 和 PR。论文对 2,140 个任务做时间分析，其中约 88.6% 早于 2023 年，也就是大模型广泛参与代码生产之前。

- **优点**：更可能是人类自然产生的问题，降低“任务本身由参评模型生成”的循环污染。
- **缺点**：仓库版本、依赖和工程习惯会变旧；模型也可能在预训练中见过公开 issue、PR 或代码。

SWE-bench Verified 主要是对 500 个任务做人工筛选，提高任务清晰度和测试可靠性；它不是“更新到更近年份”的新鲜数据集。关于年代与当前 benchmark 的问答见 [QA：今天的任务是否仍以旧代码为主](qa.md#qa-2今天的-swe-bench-任务是否仍以大模型普及前的旧代码为主)。

### 测试判分的天花板

测试是可扩展、客观的 executable scorer，但只能检查被编码的行为。隐藏安全漏洞、可维护性、性能、未覆盖输入、产品真实意图和部署稳定性通常不会被 resolved 自动证明。

因此 SWE-bench 是“在指定仓库快照和测试契约下解决 issue”的评测，不是对生产工程质量的完整认证。

## 一个通俗的完整例子

假设某个数据处理库有 issue：“空 CSV 文件读取时应返回空表，但当前抛异常。”原开发者随后提交 PR：在解析器里处理空输入，新增一个空文件测试，并保持原有 CSV 测试继续通过。

benchmark 把 PR 合并前的 commit 当 base commit，把 issue 当题目，把新测试放进 test patch。评测时，被测 Agent 看 issue 和旧仓库，自行搜索解析入口，提交自己的 patch。

Harness 在旧快照上应用测试与模型 patch：

- 新测试仍失败：issue 没修好；
- 新测试通过但旧编码测试失败：Breaking Resolved；
- 新旧指定测试都通过：Resolved；
- patch 语法正确但 diff 对不上旧文件：连 apply 都失败。

Agent 不必写出与原开发者完全相同的代码，但它只能获得测试契约能观察到的认可。

## 面试表达

### 30 秒回答

SWE-bench 是一个真实仓库级软件工程 benchmark。它从 GitHub issue 和对应修复 PR 反推任务，让模型在 PR 合并前的 base commit 上根据 issue 生成 patch，再通过 FAIL_TO_PASS 和 PASS_TO_PASS 测试判断问题是否修好且没有指定回归。它比 HumanEval 更接近真实开发，因为还包含代码定位、跨文件理解、环境复现和补丁执行，但它仍受历史数据污染、环境可复现性和测试覆盖范围限制。

### 2 分钟展开骨架

1. **问题**：函数题给定局部接口，不能代表真实仓库里的定位、理解和回归控制。
2. **构造**：issue 是题目，PR 前 commit 是起点，开发者 patch 是参考修复，PR 测试变化形成判据。
3. **执行**：Harness checkout 环境，应用 test patch 和 model patch，执行 F2P/P2P。
4. **指标**：主指标是严格的 % Resolved；% Apply、部分修复和 retrieval recall 是诊断指标。
5. **历史意义**：原始低分暴露了仓库检索、上下文和非交互式生成的困难，随后才出现 SWE-agent、Agentless 等不同 Harness 路线。
6. **边界**：通过测试不等于生产质量；旧公开任务可能污染，当前成绩必须连同 Harness、模型、预算、重试和数据版本一起读。

## 高频追问

1. 为什么需要 PASS_TO_PASS，只跑新测试不行吗？
2. Gold patch 是否是唯一正确答案？
3. % Apply 与 % Resolved 分别诊断什么？
4. 为什么给模型更多上下文，解决率反而可能下降？
5. SWE-bench Verified 是否解决了数据新鲜度问题？
6. 使用不同 Agent Harness 的 leaderboard 分数为什么不能只归功于底层模型？

已讨论问题与答案集中记录在 [qa.md](qa.md)。
