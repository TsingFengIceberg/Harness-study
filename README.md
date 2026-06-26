# Harness Study

横向学习多个 Agent Harness 的设计思路与实现对比。

## 研究项目

| 项目 | 说明 | 官方仓库 |
|---|---|---|
| [deer-flow/](deer-flow/) | 字节跳动开源的 AI Agent 框架，基于 LangGraph | [bytedance/deer-flow](https://github.com/bytedance/deer-flow) |
| [hermes-agent/](hermes-agent/) | Nous Research 的 Agent 框架 | [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) |
| [claw-code/](claw-code/) | Claude Code 的开源替代实现 | [ultraworkers/claw-code](https://github.com/ultraworkers/claw-code) |
| [openclaw/](openclaw/) | 另一个 Claude Code 开源替代 | [openclaw/openclaw](https://github.com/openclaw/openclaw) |
| [learn-claude-code/](learn-claude-code/) | 社区对 Claude Code 实现原理的分析 | [shareAI-lab/learn-claude-code](https://github.com/shareAI-lab/learn-claude-code) |

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
