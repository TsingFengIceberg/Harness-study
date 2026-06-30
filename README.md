# Harness Study

横向学习多个 Agent Harness 的设计思路与实现对比。

## 研究项目

| 项目 | 说明 | 官方仓库 |
|---|---|---|
| [deer-flow/](deer-flow/) | 字节跳动开源的 AI Agent 框架，基于 LangGraph | [bytedance/deer-flow](https://github.com/bytedance/deer-flow) |
| [hermes-agent/](hermes-agent/) | Nous Research 的 Agent 框架 | [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) |
| [claw-code/](claw-code/) | Claude Code 的开源替代实现 | [ultraworkers/claw-code](https://github.com/ultraworkers/claw-code) |
| [openclaw/](openclaw/) | 另一个 Claude Code 开源替代 | [openclaw/openclaw](https://github.com/openclaw/openclaw) |
| [learn-claude-code/](learn-claude-code/) | 手把手教你构建 Claude Code 同款 Agent Harness，20 个模块从 Agent Loop 到完整系统 | [shareAI-lab/learn-claude-code](https://github.com/shareAI-lab/learn-claude-code) |
| [openhands/](openhands/) | 平台化 SWE Agent Harness，覆盖 Agent Canvas、Agent Server、自动化与多后端运行 | [OpenHands/OpenHands](https://github.com/OpenHands/OpenHands) |

## 学习参考

| 资料 | 说明 | 官方仓库 |
|---|---|---|
| [claude-code-complete-guide_v2/](claude-code-complete-guide_v2/) | Claude Code 完全指南 V2，作为理解 Claude Code-like Harness 架构、工具系统、权限、安全、上下文、多 Agent、Hooks / Skills / Plugins 等机制的学习参考；不作为本仓库核心 Harness 实现项目 | [bcefghj/claude-code-complete-guide_v2](https://github.com/bcefghj/claude-code-complete-guide_v2) |

## 文档导航

学习笔记位于 `DOCS/` 目录，按**三层金字塔**组织：

```
DOCS/
├── projects/          ← 纵向深挖：每个项目的研读笔记
│   ├── deer-flow/     ← DeerFlow 笔记（含早期归档 docs-old/）
│   └── openhands/     ← OpenHands 笔记（平台化 SWE Agent Harness）
├── comparison/        ← 横向对比：同一维度横切多个项目
│   └── qa.md          ← 横向学习 QA：跨项目问题、讨论结论、待核验点
└── synthesis/         ← 拔高归纳：共性设计模式与架构分类
    └── faq.md         ← 最终沉淀 FAQ：已验证、可复用的核心问答
```

此外，[claude-code-complete-guide_v2/](claude-code-complete-guide_v2/) 作为 Claude Code 架构学习参考资料，以 submodule 形式保留在仓库根目录，不纳入 `DOCS/projects/` 的核心项目研读目录。

| 想看什么 | 去哪里 |
|---|---|
| 某个项目的源码怎么设计的 | [`DOCS/projects/<项目名>/`](DOCS/projects/) |
| 整体功能特色与项目定位分析 | [`DOCS/comparison/project-positioning.md`](DOCS/comparison/project-positioning.md) |
| 多个项目在某个维度上怎么不同 | [`DOCS/comparison/`](DOCS/comparison/) |
| 学习过程中的横向问题与讨论结论 | [`DOCS/comparison/qa.md`](DOCS/comparison/qa.md) |
| 从这些项目中提炼的通用设计模式 | [`DOCS/synthesis/`](DOCS/synthesis/) |
| 已验证、可复用的最终 FAQ | [`DOCS/synthesis/faq.md`](DOCS/synthesis/faq.md) |

### QA 记录方式

学习过程中会持续产生 QA。采用**文档内局部 QA + 横向 QA 总集 + 最终 FAQ 沉淀**的方式管理：

- 局部问题：附在对应项目笔记或专题文档末尾的 `## QA / 讨论记录`
- 横向问题：先收集到 [`DOCS/comparison/qa.md`](DOCS/comparison/qa.md)，例如“OpenHands 和 Claw-Code 是否重复？”、“Claude Code 算不算 SWE Agent？”
- 最终结论：经过源码或官方文档核验后，再沉淀到 [`DOCS/synthesis/faq.md`](DOCS/synthesis/faq.md)
- 每个 QA 尽量标注状态：`draft` / `to-verify` / `verified`，避免把讨论结论误当最终结论

## 使用方式

### 克隆本仓库

```bash
git clone git@github.com:TsingFengIceberg/Harness-study.git
cd Harness-study
git submodule update --init --recursive
```

### 同步上游项目更新

```bash
git submodule update --remote --merge
git add <submodule-name>
git commit -m "chore: sync <submodule-name> to latest"
```

### 切换分支后

```bash
git checkout <branch>
git submodule update --recursive
```
