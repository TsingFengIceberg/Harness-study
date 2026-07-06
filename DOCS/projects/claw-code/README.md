# Claw-Code 学习笔记

> Claude Code-like 本地 Coding CLI Harness，重点研究 Rust runtime、Agent Loop、工具系统、权限安全、sandbox、hooks、session 和 MCP 等机制。

## 源码

- **Submodule**: [claw-code/](../../../submodules/claw-code/) — 指向 `ultraworkers/claw-code`
- **官方仓库**: [github.com/ultraworkers/claw-code](https://github.com/ultraworkers/claw-code)
- **当前快照**: `4ea31c1bc91c4e9bcbd67d51c550c01e127e6d0d`

## 研究定位

Claw-Code 在本仓库中定位为 **Claude Code-like 本地 Coding CLI Harness** 的代表。

它不是平台控制面，也不是长周期通用工作流系统；它更适合作为研究“本地软件工程 Agent 如何工程化”的样本：

- 本地 CLI / REPL / one-shot 交互
- 对话 runtime 与 tool loop
- 文件、shell、grep/glob、MCP 等工具面
- permission / prompt / deny / allow 权限策略
- pre/post tool hooks
- session、auto compaction、usage / telemetry
- Linux namespace / sandbox 等本机执行安全边界

## 笔记目录

| 文档 | 主题 | 状态 |
|---|---|---|
| [agent-loop.md](agent-loop.md) | `ConversationRuntime::run_turn` 控制流：模型流式输出、ToolUse 提取、权限检查、工具执行、tool_result 回写与终止条件 | draft |
| [tool-system.md](tool-system.md) | 集中式工具中枢：`ToolSpec` / `GlobalToolRegistry`、allowed tools、hooks、两道权限门、ToolSearch 延迟工具发现与工具能力总线 | draft |

## 后续待研读主题

| 主题 | 说明 | 状态 |
|---|---|---|
| `permission-security.md` | `PermissionPolicy`、`PermissionPrompter`、allow / deny / ask、bash/path/file safety | planned |
| `sandbox-runtime.md` | Linux `unshare`、workspace 边界、本机 sandbox 与跨平台差异 | planned |
| `session-state.md` | `Session`、message 持久化、branch/fork、`TurnSummary` 调用方 | planned |
| `hooks-compaction.md` | pre/post tool hooks、auto compaction、prompt cache / usage 统计 | planned |

## 相关横向专题

- 整体定位：[项目定位与功能特色对比](../../comparison/project-positioning.md)
- 横向 QA：[Harness Study 横向 QA](../../comparison/qa.md)
- Agent Loop 横向专题：[Agent Loop 横向总结](../../comparison/agent-loop.md)
- 工具系统横向专题：[Tool System 横向总结](../../comparison/tool-system.md)
- 权限安全横向专题：`../../comparison/permission-security.md`（待撰写）
