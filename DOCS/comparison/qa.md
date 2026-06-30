# Harness Study 横向 QA

> **状态**: draft | **用途**: 收集学习过程中出现的跨项目问题、阶段性讨论结论与待核验点。
>
> 本文是 QA 的临时收集区。回答可以来自讨论、Deep Research、源码阅读或官方文档；正式引用前需要回到对应 submodule 源码或官方文档复核。成熟结论后续迁移到 [synthesis/faq.md](../synthesis/faq.md) 或吸收到具体专题正文中。

## 记录规则

每个 QA 建议使用以下格式：

```markdown
### Q: xxx？

> **状态**: draft / to-verify / verified  
> **来源**: discussion / source-code / official-docs / deep-research / inference

A: xxx。
```

状态含义：

| 状态 | 含义 |
|---|---|
| `draft` | 当前阶段的讨论理解，尚未系统核验 |
| `to-verify` | 问题重要，但需要回到源码或官方文档确认 |
| `verified` | 已经由源码、仓库内文档或官方文档支撑 |

来源含义：

| 来源 | 含义 |
|---|---|
| `discussion` | 来自学习过程中的问答讨论 |
| `source-code` | 来自 submodule 源码或仓库内文档 |
| `official-docs` | 来自官方文档 |
| `deep-research` | 来自 Deep Research 报告 |
| `inference` | 基于多源资料的推断，需要谨慎使用 |

## 项目定位

### Q: Claude Code 算不算 SWE Agent？

> **状态**: draft  
> **来源**: discussion

A: 算。Claude Code 面向软件工程任务，能够读写代码、运行命令、修改文件、辅助调试和提交，因此可以视作 Coding / SWE Agent。但它更偏本地交互式 Coding Agent，并不等同于 OpenHands 这类平台化 SWE Agent。

### Q: OpenHands 和 Claw-Code 是否重复？

> **状态**: draft  
> **来源**: discussion / deep-research

A: 不完全重复。Claw-Code 更像 Claude Code-like 本地 CLI Harness，重点是本地 runtime、权限、工具和代码编辑体验；OpenHands 更像平台化 SWE Agent Harness，重点是 Agent Server、Sandbox / Workspace、事件、Web UI / Canvas、Automation 和多 backend。两者都处理软件工程任务，但架构层级不同。

### Q: OpenHands 的团队 / 平台 / 自动化能力和 Claw-Code / Claude Code-like CLI 的区别是什么？

> **状态**: draft  
> **来源**: discussion / deep-research

A: OpenHands 把 Coding Agent 放进 App Server、Workspace / Sandbox、Event、Automation、Web UI / Canvas、Agent Backend 管理组成的平台控制面中；Claw-Code / Claude Code-like CLI 主要强化单开发者本地交互式代码执行体验。后者可以通过外部脚本和平台包装实现部分自动化，但这些不是其默认架构核心。区别不是“谁更会写代码”，而是 OpenHands 把多人、多会话、多 workspace、远程 backend、事件状态和自动触发做成平台的一等公民。

### Q: Claude Code-like / SWE Agent 是否比通用 Agent Harness 更强？

> **状态**: draft  
> **来源**: discussion

A: 在工具原语层面通常更强，因为 SWE Agent 需要文件、shell、git、test、diff、权限、上下文压缩等复杂能力，很多通用任务可以由这些工具组合完成。但在架构形态层面不是绝对超集：DeerFlow 的长周期图编排、Hermes 的长期记忆、OpenClaw 的多端控制面、OpenHands 的平台化 SWE 控制面，都是各自独立强化的方向。更准确的说法是：SWE Agent 工具原语强，但不天然覆盖所有架构形态。

### Q: 这些项目是不是同一类东西？

> **状态**: draft  
> **来源**: discussion / deep-research

A: 它们都属于 Agent Harness 大范畴，但不是同一类东西。它们共享 agent loop、工具、上下文、状态、权限、执行环境、人机交互等基础构件；差异在于谁把哪一层能力做成架构核心。learn-claude-code 是最小教学模型，Claw-Code 是本地 Coding CLI，OpenClaw 是多端控制面，OpenHands 是平台化 SWE Agent，DeerFlow 是长周期任务编排，Hermes 是记忆进化型个人 Agent，claude-code-complete-guide_v2 是 Claude Code-like 学习参考。

### Q: 项目定位会不会变成源码阅读偏见？

> **状态**: draft  
> **来源**: discussion

A: 会有这个风险，因此定位只用于建立学习地图和比较维度，不能作为细节判断的预设。多数 Harness 的基础构件大同小异，后续阅读源码时应先按同一技术维度做事实核验，再回到定位解释差异。文档表达应尽量写“该项目在某方向更突出 / 更中心”，避免写成“其他项目没有 / 不能做”，除非已有源码或官方文档证据。

### Q: claude-code-complete-guide_v2 应该怎么定位？

> **状态**: draft  
> **来源**: discussion

A: 它作为 Claude Code-like Harness 的第三方学习参考资料保留，帮助理解 Claude Code 的架构、工具系统、权限安全、上下文、多 Agent、Hooks / Skills / Plugins 等机制；不作为本仓库核心 Harness 实现项目，也默认不在 `DOCS/projects/` 下建立纵向源码研读目录。

## 调研材料使用

### Q: Deep Research 报告能不能直接作为最终结论？

> **状态**: draft  
> **来源**: discussion

A: 不能。Deep Research 报告适合作为 research-base 或问题清单，帮助确定比较维度和后续专题方向；但具体判断需要回到 submodule 源码、仓库内文档或官方文档逐项核验。

### Q: 本地 workflow 源码核验报告如何使用？

> **状态**: draft  
> **来源**: workflow / discussion

A: 本地 workflow 报告适合作为源码核验补充材料，尤其对 Claw-Code、OpenClaw、learn-claude-code、OpenHands 的路径和工程判断有参考价值。但 DeerFlow 与 Hermes Agent 的 inspect 子任务因 API 524 timeout 未完成，因此该报告不能替代完整六项目调研 Base。

## Hermes Agent 定位

### Q: Hermes Agent 比 DeerFlow 有特点的地方是什么？

> **状态**: draft  
> **来源**: discussion / deep-research

A: DeerFlow 更像长周期任务编排系统，核心是状态图、middleware、sandbox 和复杂任务流程治理；Hermes Agent 更像长期陪伴型个人 Agent，核心特色在跨会话记忆、个人偏好沉淀、经验转化为技能、以及面向日常多通道交互的持续协作。两者都能做复杂任务，但 DeerFlow 强在“把任务跑完并可控”，Hermes 强在“和同一个人长期共事并越用越贴合”。

### Q: Hermes Agent 比常规通用 Agent 多了什么，为什么能成为长期陪伴型私人 Agent？

> **状态**: draft  
> **来源**: discussion / deep-research

A: 常规通用 Agent 多数围绕单次会话、工具调用和任务完成设计；Hermes Agent 的特色在于将长期记忆、会话检索、个人偏好、程序化技能沉淀和多通道入口作为架构核心，让 Agent 不只是“能做任务”，而是能在多次互动后积累用户习惯、复用过往经验，并逐步形成面向个人的操作手册。

### Q: Hermes Agent 相比 OpenClaw 更先进或更有特色的地方是什么？

> **状态**: draft  
> **来源**: discussion / deep-research

A: OpenClaw 更强在 gateway/control-plane：多设备、多 IM、多入口、队列、审批和节点能力路由；Hermes Agent 更强在 Agent 内核的长期记忆与自我改进：它更关注如何把长期交互沉淀为可复用经验、技能和个人上下文。简单说，OpenClaw 先进在“连接更多入口和设备”，Hermes 先进在“让同一个 Agent 越用越懂你”。

## 学习方法

### Q: QA 应该每个问题单独成文件，还是附在各文档里？

> **状态**: draft  
> **来源**: discussion

A: 采用混合方式：局部解释型 QA 附在对应项目笔记或专题文档末尾；横向比较型 QA 先收集在本文；经过源码或官方文档核验后的稳定结论，再迁移到 [synthesis/faq.md](../synthesis/faq.md)。一般不建议每个 QA 单独建文件，避免碎片化。
