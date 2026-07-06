# Agent Harness 本地源码核验补充报告

> **日期**: 2026-06-30 | **状态**: local-source-verification | **来源**: Claude workflow `local-six-harness-research`
>
> 本文由本地源码读取 workflow 生成，用于补充 [六项目 Agent Harness 架构对比分析](agent-harness-architecture-six-projects.md)。该 workflow 成功核验了 Claw-Code、OpenClaw、learn-claude-code、OpenHands 四个 submodule；DeerFlow 与 Hermes Agent 两个子任务因 API 524 timeout 未完成，因此本文不替代六项目调研 Base，只作为本地源码核验补充材料。
>
> 文中路径已从绝对路径改为相对于本文件的仓库相对路径。后续写正式专题时，应继续回到对应 submodule 源码逐项复核。

## 执行摘要

本次综合基于用户提供的本地源码/文档验证报告，覆盖 4 个有实证材料的项目：Claw-Code Rust、OpenClaw、learn-claude-code、OpenHands；另外两个报告项为空，因此本报告对六项目视角中的 DeerFlow、Hermes Agent 只保留为“待补证”槽位，不做未经验证的细节判断。

高层结论：

1. **现代 Agent Harness 的共同核心不是复杂规划器，而是可恢复、可治理的执行外壳**：稳定的 agent loop、工具注册与调度、上下文压缩、权限/审批、会话持久化、事件队列、沙箱/runtime，是比“多智能体树状规划”更反复出现的工程主线。
2. **四个已验证项目呈现三类架构重心**：
   - Claw-Code Rust：面向 CLI coding agent 的高性能单机 harness，强调权限、hooks、session、MCP、工具面 parity。
   - OpenClaw：本地优先的 gateway/control-plane，强调多通道、多设备节点、队列恢复、审批和插件化。
   - OpenHands：SWE-agent 平台控制面，强调 app server、sandbox/agent-server 容器、事件存储、ACP/MCP 互操作和自动化入口。
   - learn-claude-code：教学型最小 harness，把 loop、tool、todo、subagent、compact、cron、MCP 等机制拆成逐层叠加的工程课程。
3. **OpenHands 的新增理解最重要**：它不应被简单理解为“一个 coding agent loop”，而更像“Agent Canvas / Agent Server / Sandbox / Event / Automation 的控制面仓库”。本地代码已显示其运行重心在 FastAPI app server、sandbox service、conversation metadata、event persistence、MCP tools、webhooks 和前端状态，而低层 agent loop 很大一部分已经迁移或依赖外部 `openhands-agent-server`、`openhands-sdk`、`openhands-tools`。
4. **平台化方向明显分叉**：Claw-Code Rust 追求 Claude Code 类 CLI 工具面 parity；OpenClaw 走个人设备与消息通道 control plane；OpenHands 走 SWE agent 云/本地/远程后端和 ACP/MCP 互操作；learn-claude-code 则提供机制拆解的教学基线。
5. **安全/HITL 的成熟度差异很大**：OpenClaw 和 Claw-Code Rust 的审批/权限模型较具体；OpenHands 在本地验证材料中更偏认证、session key、sandbox ownership 和 secrets mediation，未看到通用 tool approval gate；learn-claude-code 明确是简化/教学实现。

---

## 六项目定位

> 说明：当前输入 JSON 中前两个项目报告为 `null`。结合 Harness Study 仓库上下文，六项目大概率对应 DeerFlow、Hermes Agent、Claw-Code、OpenClaw、learn-claude-code、OpenHands。本节对 DeerFlow/Hermes 只写“待补证”，不从模型记忆补充源码事实。

| 项目 | 当前证据状态 | 工程定位 | 主要研究价值 |
|---|---:|---|---|
| DeerFlow | 本轮报告缺失 | 待补证；仓库中作为 Harness Study 参考基线 | 需要补齐状态机、中间件、沙箱、HITL、工作流/研究流等纵向笔记后再横向比较 |
| Hermes Agent | 本轮报告缺失 | 待补证 | 需要补齐 agent framework、runtime、memory/tooling 等源码验证后再定位 |
| Claw-Code Rust | 高 | Claude/Claw 风格 coding harness 的 Rust 重写；CLI/REPL/one-shot；强调性能、安全、native tool execution | 理解“单机 coding harness 如何工程化”：loop、permission、hook、session、MCP、plugin、sandbox、task/team/cron |
| OpenClaw | 高 | Local-first gateway control plane；个人设备、通道、节点、插件、session 的协调层 | 理解“个人 AI 助手平台”的 durable queue、node/device pairing、approval、plugin runtime 和 channel routing |
| learn-claude-code | 高 | 教学型最小 harness；逐课拆解 Claude Code 类机制 | 作为架构最小模型：证明很多复杂 harness 机制可围绕同一个 tool-use loop 逐层叠加 |
| OpenHands | 高 | SWE-agent platform/control-plane；app server + sandbox/agent-server + event + automation + ACP/MCP | 理解 coding agent 平台化：不是单 loop，而是 conversation/runtime/sandbox/event/webhook/frontend 的控制面 |

---

## 单项目分析

### Claw-Code Rust

**定位**：高性能 Rust 版 Claude/Claw 风格 coding harness。二进制 `claw` 支持 REPL、prompt mode、session、permissions、MCP、hooks、plugins、JSON output 等。

**核心 loop**：`ConversationRuntime<C, T>` 是中枢。`run_turn` 的基本流程是：追加用户消息 → 调用模型流式输出 → 重建 assistant content blocks → 执行 tool calls → 把 tool results 追加回 session → 直到 assistant 不再发起 tool use。该 loop 同时记录 `turn_started`、`assistant_iteration_completed`、`tool_execution_started`、`turn_completed` 等 telemetry 事件。

**运行时与沙箱**：`sandbox.rs` 支持 Linux `unshare` namespace、network isolation、workspace-only/allow-list filesystem 模式、synthetic `HOME`/`TMPDIR`。它更像“本机命令执行的隔离增强层”，而不是远程容器平台。

**工具与扩展**：工具目录硬编码了广泛工具面，包括 shell/file、web、todo、structured output、notebook/REPL、多 agent/task/team/cron、MCP、LSP、git read tools。`GlobalToolRegistry` 支持 plugin tools、runtime-added tools、aliases 和 allowedTools 归一化。

**权限/HITL**：权限模型较完整：`read-only`、`workspace-write`、`danger-full-access`、`prompt`、`allow`；支持 allow/deny/ask、deniedTools、hook override；`permission_enforcer.rs` 对 bash、路径、文件写入做具体约束。

**架构特征**：单进程/本机 CLI runtime 很强，内含 task/team/cron registry，但这些 registry 当前被验证为 in-memory/process-local。它代表“把 coding agent CLI 做成高完整度工程产品”的方向。

关键路径：
- `../../submodules/claw-code/rust/crates/runtime/src/conversation.rs`
- `../../submodules/claw-code/rust/crates/runtime/src/permissions.rs`
- `../../submodules/claw-code/rust/crates/runtime/src/permission_enforcer.rs`
- `../../submodules/claw-code/rust/crates/runtime/src/sandbox.rs`
- `../../submodules/claw-code/rust/crates/tools/src/lib.rs`

---

### OpenClaw

**定位**：本地优先的 AI assistant gateway/control-plane。它不是单纯聊天机器人，也不是默认 manager-of-managers 多 planner 系统，而是一个协调 sessions、channels、tools、events、plugins、nodes/devices 的控制面。

**核心架构**：`src/gateway/server.impl.ts` 是装配点，负责 runtime state、HTTP/WebSocket、method registries、config reload、plugin pinning、cron state、health/readiness/restart。`node-registry.ts` 和 `server-node-events.ts` 显示远程节点/设备通过 gateway WebSocket 连接、声明 capabilities/commands/permissions、接收 invoke、回传 events。

**Agent runtime**：内置 agent runtime 位于 `src/agents/embedded-agent-runner/`，OpenClaw facade 在 `src/agents/runtime/`，底层 contracts 在 `packages/agent-core/`。`AgentSession` 抽象覆盖 interactive/print/RPC 模式、event subscription、compaction、tool execution、session switching、persistence。

**状态与队列**：这是 OpenClaw 最突出的工程特征。session transcript JSONL 支持 parent-child branching、labels、compaction entries、custom entries、metadata。channel ingress queue、outbound delivery queue、session delivery queue 均有 durable/retry/recovery 语义；还有 keyed async queue 和 ACP session actor queue 做 per-key/per-session serialization。

**安全/HITL**：OpenClaw 的审批不是薄 confirm dialog，而是多面向审批系统：channel pairing、device pair approval/removal、token lifecycle、node/gateway exec approval、allowlist policy、host targeting、operator approvals client。

**平台化方向**：面向个人控制的多设备/多通道 assistant 平台。gateway 是核心控制面，macOS/iOS/Android/Windows companion apps 是可选 surface；nodes 提供 voice/canvas/camera/screen/device commands 等能力。

关键路径：
- `../../submodules/openclaw/src/gateway/server.impl.ts`
- `../../submodules/openclaw/src/gateway/node-registry.ts`
- `../../submodules/openclaw/src/agents/sessions/agent-session.ts`
- `../../submodules/openclaw/src/channels/message/ingress-queue.ts`
- `../../submodules/openclaw/src/infra/exec-approvals.ts`
- `../../submodules/openclaw/src/infra/outbound/delivery-queue-storage.ts`

---

### learn-claude-code

**定位**：教学型最小 harness，不是生产 clone。它的价值在于把 Claude Code 类 harness 拆成可理解、可运行、可渐进叠加的课程序列。

**核心 loop**：最小模式非常明确：`client.messages.create(...)` → append assistant content → 如果 `stop_reason != "tool_use"` 则结束 → 执行每个 tool call → append `tool_result` user message → repeat。后续机制都是围绕这个 loop 增层，而不是替换 loop。

**机制叠加路径**：
- `s01_agent_loop`：单工具 bash loop。
- `s02_tool_use`：`TOOLS` schema + `TOOL_HANDLERS` dispatch map。
- `s05_todo_write`：in-memory planning/todo。
- `s06_subagent`：父 agent 通过 `task` tool 启动子 agent，子 agent 新 messages、限制工具、不可递归。
- `s08_context_compact`：四层上下文压缩。
- `s12_task_system`：file-backed task graph。
- `s14_cron_scheduler`：scheduler thread + queue processor。
- `s15_agent_teams`：teammates + file mailbox。
- `s19_mcp_plugin`：动态合并 MCP tools。

**上下文管理**：`s08_context_compact` 是高价值样本：L1 snip compact、L2 micro compact、L3 tool result budget、L4 LLM summary；并通过测试保证 tool_use/tool_result pairing 不被破坏。

**安全边界**：有 `safe_path`、简单 bash deny-list、工具子集限制等，但 README 明确说明完整权限治理、信任工作流、完整 MCP runtime/OAuth/subscription 等被简化或省略。

**研究价值**：它是横向比较的“最小解释器”。当 Claw-Code/OpenClaw/OpenHands 出现复杂子系统时，可以回到 learn-claude-code 问：这个复杂机制到底是在 loop 外加了哪一层？工具注册、上下文压缩、任务状态、队列、审批、沙箱，还是平台控制面？

关键路径：
- `../../submodules/learn-claude-code/s01_agent_loop/code.py`
- `../../submodules/learn-claude-code/s02_tool_use/code.py`
- `../../submodules/learn-claude-code/s08_context_compact/code.py`
- `../../submodules/learn-claude-code/s12_task_system/code.py`
- `../../submodules/learn-claude-code/s15_agent_teams/code.py`
- `../../submodules/learn-claude-code/s19_mcp_plugin/code.py`

---

### OpenHands

**定位**：OpenHands 在本地验证材料中更准确地说是 SWE-agent 平台控制面/app server，而不是单一 agent loop 仓库。README 已说明代码正在向 `agent-canvas` 和 `software-agent-sdk` 等拆分；本仓库消费 `openhands-agent-server`、`openhands-sdk`、`openhands-tools` 等外部包。

**App server 架构**：`openhands.app_server.app:app` 挂载 `/mcp`，包含 `/api/v1` routers、health、可选静态前端、CORS/cache/rate-limit middleware、lifespan composition。分层包括：
- FastAPI app server：`openhands/app_server`
- sandbox/runtime abstraction：`sandbox_service.py` 及 Docker/remote/process 实现
- conversation metadata/live status：`app_conversation/*`
- event persistence/query：`event/*`
- webhook/event-callback automation：`event_callback/*`
- frontend state/config：`frontend/src/*`
- MCP tools/proxies：`mcp/mcp_router.py`

**Runtime/sandbox**：`SandboxService` 提供 start/resume/pause/delete/batch query/archive。Docker 实现启动 agent-server containers，设置 workspace env、工作目录 `/workspace/project`，健康检查 agent server，并维护 session API key、exposed URLs、sandbox records。删除前可从 agent-server 拉取 archive/patch/tar。

**事件与状态**：conversation metadata 包含 title、repo/branch、trigger、agent_kind、metrics、tags、parent/subconversation。事件服务支持按 conversation、kind、time、pagination、count 查询。前端 Zustand event store 做 ID dedupe、timestamp ordering、action/observation 和 ACP tool-call progress 的 UI 折叠。

**ACP/MCP 与自动化**：前端 agent settings 支持在 `openhands` 与 `acp` 间切换，并配置 ACP command/model/provider。FastAPI app 挂载 stateless HTTP MCP app；MCP router 提供如 `create_pr`、`create_mr` 的工具；webhooks 通过 tags/trigger/outcome 连接外部自动化。

**安全/HITL**：已验证的是 session-scoped `X-Session-API-Key`、sandbox ownership checks、sandbox-scoped secrets mediation、auth dependency signaling。未在本地文件中看到类似 Claw-Code/OpenClaw 那样通用的每工具 HITL approval gate。

**OpenHands-specific 新理解**：

- 不能把 OpenHands 简化为“一个自主 coding agent”。本仓库更像 **Agent Canvas/Server 的平台控制面**。
- Agent loop 细节不应从本仓库过度推断，因为 `openhands-agent-server`、`openhands-sdk`、`openhands-tools` 的 pinned dependencies 暗示大量 runtime/agent 逻辑在外部包。
- 本仓库可验证的核心是：conversation metadata、sandbox lifecycle、event store、automation callbacks、MCP exposure、frontend runtime readiness、ACP settings。
- OpenHands 的平台趋势是“多 agent backend + ACP/MCP interoperability + sandboxed agent-server containers + automation/webhook”，而不是“单机 CLI 工具面 parity”。

关键路径：
- `../../submodules/openhands/openhands/app_server/app.py`
- `../../submodules/openhands/openhands/app_server/sandbox/sandbox_service.py`
- `../../submodules/openhands/openhands/app_server/sandbox/docker_sandbox_service.py`
- `../../submodules/openhands/openhands/app_server/app_conversation/app_conversation_models.py`
- `../../submodules/openhands/openhands/app_server/event/event_service.py`
- `../../submodules/openhands/openhands/app_server/event_callback/webhook_router.py`
- `../../submodules/openhands/openhands/app_server/mcp/mcp_router.py`
- `../../submodules/openhands/frontend/src/routes/agent-settings.tsx`

---

## 横向对比表

### 定位对比

| 维度 | Claw-Code Rust | OpenClaw | learn-claude-code | OpenHands | DeerFlow | Hermes Agent |
|---|---|---|---|---|---|---|
| 主要形态 | CLI coding harness | Local-first gateway control plane | 教学 harness | SWE-agent platform/app server | 待补证 | 待补证 |
| 首要用户场景 | 本地代码任务、REPL、one-shot | 个人助手、多设备、多通道 | 学习 harness 工程 | 浏览器/平台化 coding agent 控制 | 待补证 | 待补证 |
| 架构重心 | runtime + tools + permissions | gateway + sessions + queues + nodes | minimal loop layering | app server + sandbox + events + ACP/MCP | 待补证 | 待补证 |
| 产品化方向 | Claude Code parity | personal AI OS/control plane | education/reference | SWE-agent control platform | 待补证 | 待补证 |

### Agent loop 对比

| 维度 | Claw-Code Rust | OpenClaw | learn-claude-code | OpenHands |
|---|---|---|---|---|
| loop 所在 | `ConversationRuntime::run_turn` | `AgentSession`/embedded runtime | 每课 `code.py` 中显式 while-loop | 本仓库低层 loop 不完整可见，部分在外部 agent-server/SDK |
| 基本模式 | user → stream assistant → execute tools → append results → repeat | session 抽象统一 interactive/print/RPC、tool execution、compaction、persistence | 最小 tool_use loop | app server 负责 conversation/runtime orchestration，不宜推断内层 loop |
| 事件/telemetry | turn/tool/cache/compaction usage 事件 | session/channel/node/plugin 事件与 durable queues | 教学输出为主 | event service + frontend event store + webhook callbacks |
| 多轮中断恢复 | session persistence | JSONL transcript + queues + delivery recovery | 文件任务/邮箱示例 | conversation metadata + event persistence + sandbox resume |

### Runtime / Sandbox 对比

| 维度 | Claw-Code Rust | OpenClaw | learn-claude-code | OpenHands |
|---|---|---|---|---|
| sandbox 形态 | Linux namespace/unshare，本机增强隔离 | host vs sandbox policy；Docker/SSH/OpenShell 文档化 | lightweight path guard/deny-list | SandboxService；Docker/remote/process；agent-server containers |
| workspace 绑定 | session `workspace_root`，防跨 worktree 混淆 | per-agent workspace/session dirs | `WORKDIR` 和本地隐藏目录 | workspace env、`/workspace/project`、archive before deletion |
| 网络隔离 | 可配置 network isolation | 取决于 sandbox backend/policy | 无完整实现 | Docker/runtime 层，具体网络策略需另证 |
| 运行时控制面 | CLI runtime 内部 | gateway | 教学脚本 | FastAPI app server + sandbox service |

### Tools / Extension 对比

| 维度 | Claw-Code Rust | OpenClaw | learn-claude-code | OpenHands |
|---|---|---|---|---|
| 工具注册 | hardcoded MVP specs + GlobalToolRegistry + plugins | built-ins + extension/custom tools + plugin registry | `TOOLS` schema + `TOOL_HANDLERS` map | MCP tools + agent/runtime backend tools |
| MCP | MCP tools/resources/auth/stdio | 未在本轮详述为核心，但有 plugin/runtime extensibility | s19 mock MCP pool merge | `/mcp` stateless HTTP app，proxied tools，PR/MR tools |
| 插件 | plugin lifecycle/parity 仍有 gap | manifest/resource package/plugin slots | 教学化 skill/MCP | 外部 packages + MCP + app integrations |
| 工具面广度 | 很宽，追求 parity | browser/canvas/nodes/cron/sessions/channel actions | 渐进添加 | 平台工具、PR/MR、secrets、agent backend tools |

### Memory / Context 对比

| 维度 | Claw-Code Rust | OpenClaw | learn-claude-code | OpenHands |
|---|---|---|---|---|
| session memory | structured session JSON/JSONL、compaction metadata、prompt history | JSONL transcript trees、branching、labels、compaction | messages list + file-backed tasks/outputs | conversation metadata + event history + settings/secrets |
| prompt memory | CLAUDE/CLAW/AGENTS 等 instruction discovery | AGENTS/SOUL/TOOLS + resources/prompts/skills | 动态 prompt sections 教学 | prompt 构造部分可能在外部 SDK/agent-server |
| context compact | auto-compaction threshold | `AgentSession` handling compaction | 四层压缩，测试保护 tool pairs | 本地未看到低层 compact 细节 |
| long-term memory | 文件/指令/会话层 | single active memory plugin slot | 教学简化 | app-side metadata/event，agent memory 待外部包验证 |

### HITL / Security 对比

| 维度 | Claw-Code Rust | OpenClaw | learn-claude-code | OpenHands |
|---|---|---|---|---|
| 权限模式 | read-only/workspace-write/danger/prompt/allow | channel/device/exec approvals + allowlist | 概念/简化 | auth/session key/ownership/secrets mediation |
| Tool approval | PermissionPrompter + hook override | exec approval requests/decisions | 仅 annotation/mock | 未验证通用 tool approval gate |
| Path/shell 安全 | lexical path normalization、bash command checks | sandbox policy + host targeting | safe_path + deny-list | sandbox API key + sandbox router checks |
| 外部主体接入 | MCP/plugin permissions | pairing code、device tokens、admin checks | 无 | auth dependencies、session-scoped sandbox APIs |

### Platformization 对比

| 维度 | Claw-Code Rust | OpenClaw | learn-claude-code | OpenHands |
|---|---|---|---|---|
| 平台边界 | 本地 CLI runtime | Gateway + nodes + channels + companion apps | 教学 repo | App server + frontend + sandbox service + agent server |
| 分布式能力 | process-local task/team/cron，MCP | WebSocket nodes/devices，durable queues | file mailbox demo | local/remote/cloud sandbox backends，ACP-compatible agents |
| 自动化 | cron tools/registries | cron/channel/plugin hooks | cron lesson | webhooks/event callbacks/schedules 文档化 |
| 互操作 | Anthropic/OpenAI-compatible、MCP | plugins、nodes、channels | MCP interface teaching | ACP + MCP + provider integrations |

---

## 架构分类学

### 类型 A：Minimal Loop Harness

代表：learn-claude-code。

特征：
- 单 while-loop + tool_use/tool_result 协议。
- 工具通过 schema + handler map 接入。
- 任务、子 agent、cron、MCP、context compact 都是 loop 外增层。
- 安全、持久化、分布式能力多为教学简化。

适合作为 Harness Study 的“最小概念模型”。

### 类型 B：Single-machine Coding Harness

代表：Claw-Code Rust。

特征：
- CLI/REPL/one-shot 为主。
- runtime 内聚：session、prompt、permissions、tools、MCP、hooks、usage、sandbox。
- 工具面广，追求 Claude Code/Claw parity。
- 沙箱偏本机 namespace/permission enforcement，而不是完整云平台。

适合研究“如何把 minimal loop 产品化为本地 coding agent”。

### 类型 C：Local-first Gateway Control Plane

代表：OpenClaw。

特征：
- Gateway 是中心，不是 agent loop 本身。
- 多 channel、多 node/device、多 plugin、多 session。
- durable queue、delivery recovery、per-session serialization 是一等公民。
- 安全模型围绕 pairing、approval、operator、device tokens 展开。

适合研究“个人 AI 助手如何从 CLI 扩展到多入口/多设备平台”。

### 类型 D：SWE-agent Platform Control Plane

代表：OpenHands。

特征：
- App server 管 conversation、sandbox、event、webhook、frontend、MCP。
- 低层 agent runtime 可外置到 agent-server/SDK。
- 支持 OpenHands/ACP agents、多 backend、本地/远程/云 sandbox。
- 事件和 conversation metadata 是平台状态骨架。

适合研究“coding agent 如何平台化、服务化、互操作化”。

### 类型 E：Workflow/Research Graph Harness

代表候选：DeerFlow，但本轮材料缺失，待补证。

需要验证：是否以 graph/state/middleware/workflow 为核心，如何处理 research/deep-research、多 agent 协作、沙箱与 HITL。

### 类型 F：Agent Framework / Model-native Harness

代表候选：Hermes Agent，但本轮材料缺失，待补证。

需要验证：是否偏通用 agent framework、memory/tool abstraction、multi-agent protocol、model/runtime 绑定。

---

## 趋势判断

1. **Agent loop 稳定化，外围系统复杂化**  
   四个已验证项目都没有显示“神秘复杂 loop”是核心差异。差异主要出现在外围：工具治理、上下文管理、session/event、runtime/sandbox、审批、插件、平台控制面。

2. **从工具调用转向执行治理**  
   工具数量变多不是难点，难点是：谁允许调用、在哪执行、如何恢复、如何审计、如何回放、如何限制副作用。Claw-Code Rust 的 permission/hook、OpenClaw 的 approval/queue、OpenHands 的 session key/sandbox/event 都体现这一点。

3. **Context 不只是 token 压缩，而是状态生命周期设计**  
   learn-claude-code 显示压缩要保护 tool pair；Claw-Code Rust 把 compaction metadata 放进 session；OpenClaw 把 transcript、branch、queue、delivery 都持久化；OpenHands 则把 conversation/event metadata 平台化。

4. **MCP/ACP 正在把 harness 变成互操作控制面**  
   Claw-Code Rust 内建 MCP tool/resource/auth；learn-claude-code 教学化展示 MCP tool pool merge；OpenHands 同时暴露 MCP 并支持 ACP agent settings。未来 harness 的竞争点会从“内置工具多少”转向“如何安全接入外部工具、agent backend、runtime”。

5. **平台化有两条路线**  
   - Local-first personal platform：OpenClaw，强调设备、通道、节点、个人审批。
   - SWE-agent control platform：OpenHands，强调 sandbox/agent-server、events、webhooks、ACP/MCP、前端控制。
   Claw-Code Rust 则更像强 CLI 基座，未必走同样平台路线。

6. **多 agent 的真实工程重心不是树状规划，而是隔离、通信和可恢复调度**  
   learn-claude-code 从 subagent 到 teams/mailbox；Claw-Code Rust 有 task/team/cron registry；OpenClaw 有 per-session queues 和 isolated agent routing；OpenHands 有 parent/subconversation 和 multiple agent backends。关键问题是状态隔离、消息投递、恢复、权限，而不是“多 agent”标签本身。

---

## 高置信结论

1. **Claw-Code Rust 是研究 Claude Code 类 CLI harness 工程面的最佳样本之一**：loop、tools、permissions、hooks、session、sandbox、MCP 均有直接源码证据。
2. **OpenClaw 的核心不是 agent reasoning，而是 local-first gateway control plane**：durable queue、node/device pairing、approval、plugin runtime、channel routing 是主要工程资产。
3. **learn-claude-code 适合做所有复杂 harness 的最小对照组**：它清楚展示 agent loop 如何在不改变核心协议的情况下逐步获得 todo、subagent、compaction、cron、MCP、team 能力。
4. **OpenHands 需要按 platform/control-plane 研究，而不是按单 agent loop 研究**：本地仓库已明显分层为 app server、sandbox service、event service、conversation metadata、MCP、frontend；低层 agent/runtime 分散到外部包。
5. **HITL/security 是区分成熟 harness 和教学/平台壳的重要指标**：OpenClaw、Claw-Code Rust 具备较具体的执行审批/权限模型；learn-claude-code 明确简化；OpenHands 本轮只验证到 auth/session/sandbox/secrets 层。
6. **事件/队列/持久化是平台型 harness 的分水岭**：OpenClaw 和 OpenHands 都把事件/队列/metadata 作为核心结构，而不仅是日志。

---

## Caveats / To Verify

1. **DeerFlow 与 Hermes Agent 本轮报告为空**：不能在本报告中做源码级结论。需要补齐后再更新六项目横向表。
2. **OpenHands 低层 agent loop 未完整验证**：由于仓库依赖外部 `openhands-agent-server`、`openhands-sdk`、`openhands-tools`，本报告只对本地 app/control-plane 代码做高置信判断。
3. **OpenClaw memory 细节待深入**：当前只高置信验证了 single active memory plugin slot，未完整分析 memory plugin 的数据模型和 retrieval 策略。
4. **Claw-Code Rust roadmap 未完整读取**：报告中的平台趋势主要来自 README、PARITY、源码注释和已验证文件，不代表完整 roadmap 审计。
5. **learn-claude-code 是教学实现**：不可把其 mock MCP、简化 permissions、file mailbox 直接等同生产系统。
6. **各项目版本点固定在 submodule 当前状态**：后续 upstream 更新可能改变实现细节，尤其 OpenHands 当前处于仓库拆分迁移期。

---

## 建议的 DOCS 后续写作计划

### 第一优先级：补齐缺失项目纵向笔记

1. 新建或完善 DeerFlow 纵向笔记：
   - `../../DOCS/projects/deer-flow/agent-loop.md`
   - `../../DOCS/projects/deer-flow/state-machine.md`
   - `../../DOCS/projects/deer-flow/middleware.md`
   - `../../DOCS/projects/deer-flow/runtime-sandbox.md`
   - `../../DOCS/projects/deer-flow/hitl-security.md`

2. 新建 Hermes Agent 项目目录和入口：
   - `../../DOCS/projects/hermes-agent/README.md`
   - `../../DOCS/projects/hermes-agent/architecture.md`
   - `../../DOCS/projects/hermes-agent/agent-loop.md`
   - `../../DOCS/projects/hermes-agent/tools-memory.md`

### 第二优先级：为已验证项目沉淀纵向笔记

建议新增：

- `../../DOCS/projects/claw-code/rust-runtime.md`
- `../../DOCS/projects/claw-code/permissions-hooks-sandbox.md`
- `../../DOCS/projects/openclaw/gateway-control-plane.md`
- `../../DOCS/projects/openclaw/queues-approvals-nodes.md`
- `../../DOCS/projects/learn-claude-code/minimal-harness-lessons.md`
- `../../DOCS/projects/openhands/app-server-sandbox-events.md`
- `../../DOCS/projects/openhands/acp-mcp-platformization.md`

### 第三优先级：横向专题

建议在 `../../DOCS/comparison/` 下新增：

1. `agent-loop-patterns.md`  
   对比 minimal loop、ConversationRuntime、AgentSession、OpenHands 外置 loop。

2. `runtime-sandbox-systems.md`  
   对比 Claw-Code namespace、OpenClaw Docker/SSH/OpenShell policy、OpenHands SandboxService、DeerFlow 待补。

3. `permission-hitl-security.md`  
   对比 Claw-Code permission/hook、OpenClaw approvals、OpenHands session auth/secrets、learn-claude-code 简化模型。

4. `event-queue-state.md`  
   聚焦 OpenClaw durable queues、OpenHands event service、Claw session/task registry、learn task/cron/file mailbox。

5. `mcp-acp-extension.md`  
   对比 MCP/ACP/plugin/skills/resource packages 的接入方式。

6. `platformization-paths.md`  
   对比 CLI parity、local-first gateway、SWE-agent platform、教学 harness、DeerFlow/Hermes 待补。

### 第四优先级：综合抽象文档

在 `../../DOCS/synthesis/` 下规划：

- `architecture-taxonomy.md`：沉淀本报告中的 A-F 分类。
- `harness-design-patterns.md`：总结 loop shell、tool registry、permission gate、sandbox adapter、event log、durable queue、context compactor、session branch、plugin slot、agent backend adapter 等模式。
- `engineering-checklist.md`：为未来评估新 harness 提供固定问题清单。

建议固定评估清单：

1. Agent loop 在哪里？是否可中断/恢复？
2. Tool registry 如何定义、发现、授权、执行、回传错误？
3. Session/message/event 是否持久化？是否可查询/回放/分支？
4. Context compaction 是否保护 tool_use/tool_result pairing？
5. Runtime/sandbox 的隔离边界是什么？host/container/remote/process？
6. 权限/HITL 是 prompt 级、tool 级、exec 级、channel/device 级，还是仅认证？
7. Extension 是 plugin、MCP、ACP、skills、resource packages，还是 hardcoded？
8. 多 agent 是真实调度系统，还是 isolated sessions / mailbox / backend switching？
9. 平台控制面是否有 queue、webhook、frontend、API、auth、multi backend？
10. 哪些能力是源码验证，哪些只是 README 声称？

---

## Workflow 运行说明

- Workflow ID: `wybc76mmj`
- 成功核验：Claw-Code、OpenClaw、learn-claude-code、OpenHands
- 未完成核验：DeerFlow、Hermes Agent
- 失败原因：两个 inspect agent 均遇到 API 524 timeout；因此本文中的 DeerFlow / Hermes 部分保持待补证，不做源码级结论。
