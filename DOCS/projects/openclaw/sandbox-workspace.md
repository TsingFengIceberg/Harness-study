# OpenClaw Sandbox / Workspace / Execution Environment 研读笔记

> **日期**: 2026-07-08 | **状态**: draft | **涉及版本**: `openclaw@780ca1d25315b34d3118e1db2d8dcafcc16415f3`

## 相关文档

- OpenClaw Agent Loop：[agent-loop.md](agent-loop.md)
- OpenClaw Tool System：[tool-system.md](tool-system.md)
- OpenClaw Context Management：[context-management.md](context-management.md)
- OpenClaw Permission / Security：[permission-security.md](permission-security.md)
- 横向 Permission / Security：[../../comparison/permission-security.md](../../comparison/permission-security.md)
- 横向 QA：[../../comparison/qa.md](../../comparison/qa.md#sandbox--workspace--execution-environment--沙箱与执行环境)

## 源码入口

| 模块 | 源码 | 说明 |
|---|---|---|
| Sandbox barrel | [sandbox.ts](../../../submodules/openclaw/src/agents/sandbox.ts) | sandbox 公共导出面，统一暴露 config、context、backend、Docker、SSH、fs bridge、tool policy 等能力。 |
| Runtime status | [runtime-status.ts](../../../submodules/openclaw/src/agents/sandbox/runtime-status.ts) | 根据 `mode=off/non-main/all`、session key 和 main session 判断当前 session 是否 sandboxed，并格式化 tool policy block 信息。 |
| Sandbox config | [config.ts](../../../submodules/openclaw/src/agents/sandbox/config.ts) | 合并 global / agent sandbox 配置，解析 backend、scope、workspaceAccess、Docker、SSH、browser、tools、prune。 |
| Sandbox types | [types.ts](../../../submodules/openclaw/src/agents/sandbox/types.ts) | `SandboxConfig`、`SandboxContext`、`SandboxWorkspaceAccess`、`SandboxScope`、tool policy 等核心类型。 |
| Sandbox context | [context.ts](../../../submodules/openclaw/src/agents/sandbox/context.ts) | `resolveSandboxContext(...)` 总装配入口：workspace layout、backend、registry、browser、fsBridge。 |
| Workspace layout | [shared.ts](../../../submodules/openclaw/src/agents/sandbox/shared.ts) | session slug、scope key、agent workspace / sandbox workspace / skills workspace 路径解析。 |
| Workspace bootstrap | [workspace.ts](../../../submodules/openclaw/src/agents/sandbox/workspace.ts) | 创建 sandbox workspace，并从 agent workspace seed bootstrap / identity / tools 等文件。 |
| Backend registry | [backend.ts](../../../submodules/openclaw/src/agents/sandbox/backend.ts) | process-wide backend registry，注册 Docker / SSH / custom sandbox backend factory。 |
| Docker backend | [docker-backend.ts](../../../submodules/openclaw/src/agents/sandbox/docker-backend.ts) | Docker backend handle：创建 / 复用 container，构造 `docker exec` 执行 spec。 |
| Docker runtime | [docker.ts](../../../submodules/openclaw/src/agents/sandbox/docker.ts) | Docker create / start / inspect / exec、config hash、container recreate、labels、workspace mount。 |
| Docker security | [validate-sandbox-security.ts](../../../submodules/openclaw/src/agents/sandbox/validate-sandbox-security.ts) | 阻止危险 bind mounts、host network、container namespace join、unconfined seccomp / AppArmor。 |
| Workspace mounts | [workspace-mounts.ts](../../../submodules/openclaw/src/agents/sandbox/workspace-mounts.ts) | 构造 workspace / agent workspace / read-only skill mounts 的 Docker `-v` 参数。 |
| FS bridge | [fs-bridge.ts](../../../submodules/openclaw/src/agents/sandbox/fs-bridge.ts) | host <-> sandbox 文件桥：read / write / mkdir / remove / rename / stat 与 pathGuard。 |
| FS path mapping | [fs-paths.ts](../../../submodules/openclaw/src/agents/sandbox/fs-paths.ts) | container path / host path mount table，解析 sandbox 文件路径是否可写。 |
| Tool policy | [tool-policy.ts](../../../submodules/openclaw/src/agents/sandbox/tool-policy.ts) | sandbox 默认 allow / deny 工具策略，合并 global / agent allow / alsoAllow / deny。 |
| Tool assembly | [agent-tools.ts](../../../submodules/openclaw/src/agents/agent-tools.ts) | `createOpenClawCodingTools` 根据 sandbox context 重配 read / write / edit / exec / browser / plugin tools。 |
| Exec tool | [bash-tools.exec.ts](../../../submodules/openclaw/src/agents/bash-tools.exec.ts) | exec target 解析：`gateway` / `sandbox` / `node` / `auto`，sandbox 下 resolve workdir / env / process。 |
| Exec runtime | [bash-tools.exec-runtime.ts](../../../submodules/openclaw/src/agents/bash-tools.exec-runtime.ts) | `runExecProcess(...)`，有 sandbox 时调用 backend `buildExecSpec(...)` 或 Docker exec。 |

## 核心结论

OpenClaw 的 sandbox 可以先用一句话理解：

> **OpenClaw 的 sandbox 是 Agent session 级的产品化隔离工位：它不只是 bash 的保护壳，而是会影响 workspace、exec 目标、文件工具、browser、plugin tools 和 tool policy 的整套 runtime context。**

它和前面几个 harness 的差异非常明显：

```text
OpenHands：sandbox 内跑 Agent Server，App Server 管生命周期。
DeerFlow：LangGraph 工具调用按需 acquire SandboxProvider。
Claw-Code：本地 workspace 围栏 + permission mode + bash unshare wrapper。
OpenClaw：session 是否 sandboxed 决定整套工具面如何重配到 Docker / SSH / browser / fsBridge runtime。
```

可以压缩成主线：

```text
sessionKey + config
  -> resolveSandboxRuntimeStatus(mode=off/non-main/all)
  -> resolveSandboxConfigForAgent(global + agent)
  -> ensureSandboxWorkspaceLayout(agent / sandbox / skills workspace)
  -> requireSandboxBackendFactory(docker / ssh / custom)
  -> backend creates / reuses runtime
  -> create SandboxContext(fsBridge, browser, tool policy, workdir)
  -> createOpenClawCodingTools rewire read/write/edit/exec/plugin/browser tools
```

通俗比喻：

> **OpenClaw 像一个多端 Agent 工作室。sandbox 是给某个 session / agent / shared scope 分配的隔离工位；工位可能是 Docker，也可能是 SSH；项目资料怎么挂进去、能不能写、命令在哪跑、浏览器怎么连、哪些工具能看到，都由这个工位配置决定。**

## 功能清单

如果只问“OpenClaw sandbox 有什么功能、起什么作用”，可以浓缩成这些：

| 功能 | 作用 |
|---|---|
| session 是否 sandboxed | `mode=off/non-main/all` 决定当前 session 是否启用 sandbox，常见策略是非 main session 才 sandbox。 |
| 多后端执行 | backend registry 默认注册 Docker 和 SSH，也允许插件 / 测试注册 custom backend。 |
| 作用域管理 | `scope=session/agent/shared` 决定 sandbox 生命周期和复用粒度。 |
| workspace layout | 区分 `agentWorkspaceDir`、`sandboxWorkspaceDir`、`skillsWorkspaceDir` 和最终 `workspaceDir`。 |
| workspaceAccess | `none/ro/rw` 控制是否暴露 agent workspace，以及在容器里是只读还是可写。 |
| Docker 隔离 | 默认 image、read-only root、tmpfs、network none、cap-drop ALL、no-new-privileges、资源限制等。 |
| Docker 配置安全校验 | 阻止挂载系统目录、凭据目录、Docker socket、host network、unconfined seccomp / AppArmor。 |
| 文件桥 fsBridge | 在 host 和 sandbox mount 之间映射路径，执行 read / write / rename / remove / stat，并做 pathGuard。 |
| 工具面重配 | sandbox 下 read / write / edit / apply_patch / exec 等工具会切换到 sandbox root / fsBridge / backend。 |
| exec 目标切换 | `host=auto` 且 sandbox 可用时可以选 sandbox；`host=sandbox` 没有 runtime 会直接报错。 |
| tool policy 收窄 | sandbox 模式有默认 allow / deny 工具策略，默认限制 gateway / cron / channel / nodes 等控制面工具。 |
| browser bridge | 可选创建 sandbox browser / CDP / noVNC bridge，把 browser 能力也绑定到 sandbox。 |
| registry / prune | sandbox runtime 会写入 registry，支持 describe / remove / recreate / prune 等运维操作。 |

最短理解：

> **OpenClaw sandbox 的作用，是把某个 Agent session 的执行能力从“直接在宿主产品 runtime 里做事”改成“在一个受策略约束的工位里做事”。**

## 1. 是否启用：mode = off / non-main / all

OpenClaw 不会无条件给所有 session 创建 sandbox。判断入口是 [runtime-status.ts](../../../submodules/openclaw/src/agents/sandbox/runtime-status.ts)。

核心逻辑是：

```text
mode = off
  -> 不启用 sandbox

mode = all
  -> 所有 session sandboxed

mode = non-main
  -> main session 不 sandbox，非 main session sandboxed
```

这和 OpenClaw 的产品形态有关：它有 main session、子 session、spawned session、cron / gateway / IM channel session 等不同入口。sandbox policy 需要按 session 类型生效，而不是全局一刀切。

可以记成：

> **OpenClaw sandbox 的第一步不是创建容器，而是判断“这个 session 要不要进工位”。**

## 2. 配置：backend / scope / workspaceAccess 是三个核心旋钮

[config.ts](../../../submodules/openclaw/src/agents/sandbox/config.ts) 的 `resolveSandboxConfigForAgent(...)` 会合并 global sandbox config 和 agent-specific sandbox config。

`SandboxConfig` 核心字段见 [types.ts](../../../submodules/openclaw/src/agents/sandbox/types.ts)：

```text
mode: off / non-main / all
backend: docker / ssh / custom
scope: session / agent / shared
workspaceAccess: none / ro / rw
workspaceRoot
docker
ssh
browser
tools
prune
```

三个最重要的旋钮：

| 旋钮 | 问题 | 典型值 |
|---|---|---|
| `backend` | 工位在哪里跑？ | `docker` / `ssh` / custom |
| `scope` | 工位多久复用？ | `session` / `agent` / `shared` |
| `workspaceAccess` | 工位能不能碰原始 workspace？ | `none` / `ro` / `rw` |

这说明 OpenClaw sandbox 不是一个布尔开关，而是一个 runtime profile。

## 3. Backend registry：Docker / SSH / custom 后端

[backend.ts](../../../submodules/openclaw/src/agents/sandbox/backend.ts) 维护 process-wide backend registry：

```text
registerSandboxBackend("docker", ...)
registerSandboxBackend("ssh", ...)
```

同时提供：

```text
getSandboxBackendFactory(...)
requireSandboxBackendFactory(...)
getSandboxBackendManager(...)
getSandboxBackendWorkdirResolver(...)
```

这说明 OpenClaw 的 sandbox 是 backend 化的：Docker 是默认后端，SSH 是另一种内建后端，插件或测试也可以注册 custom backend。

可以和 DeerFlow 类比：

```text
DeerFlow: SandboxProvider
OpenClaw: SandboxBackendFactory / SandboxBackendHandle
```

但 OpenClaw 的 backend 不只是“执行工具”，还要服务 session runtime、exec workdir、fsBridge、browser、registry 和 lifecycle manager。

## 4. resolveSandboxContext：sandbox 总装配入口

[context.ts](../../../submodules/openclaw/src/agents/sandbox/context.ts) 的 `resolveSandboxContext(...)` 是核心总装配入口。

它的大致流程：

```text
resolveSandboxSession(...)
  -> resolveSandboxRuntimeStatus(...)
  -> 如果当前 session 不 sandboxed，返回 null

maybePruneSandboxes(...)
  -> 按 idle / max age 清理旧 runtime

ensureSandboxWorkspaceLayout(...)
  -> agentWorkspaceDir
  -> sandboxWorkspaceDir
  -> skillsWorkspaceDir
  -> workspaceDir
  -> scopeKey

resolveSandboxDockerUser(...)
  -> 尝试用 workspace uid/gid 补 docker user

requireSandboxBackendFactory(...)
  -> backendFactory(...)
  -> 创建 / 复用 Docker / SSH / custom runtime

updateRegistry(...)
  -> 记录 containerName / backendId / sessionKey / image / lastUsedAt

ensureSandboxBrowser(...)
  -> 可选创建 browser bridge / noVNC / CDP

createSandboxFsBridge(...)
  -> 创建 host <-> sandbox 文件桥

return SandboxContext
```

`SandboxContext` 是后续工具装配的关键输入。它包含：

```text
workspaceDir
agentWorkspaceDir
skillsWorkspaceDir
workspaceAccess
runtimeId / runtimeLabel / containerName
containerWorkdir
docker
tools
browser
fsBridge
backend
```

精髓：

> **SandboxContext 是“这个 session 的工位说明书”：工作目录在哪里、容器叫什么、后端怎么 exec、文件怎么桥接、browser 怎么连、工具策略是什么。**

## 5. Workspace layout：agent workspace 与 sandbox workspace 可以不同

路径解析在 [shared.ts](../../../submodules/openclaw/src/agents/sandbox/shared.ts) 的 `resolveSandboxWorkspaceLayoutPaths(...)`。

关键字段：

```text
agentWorkspaceDir
sandboxWorkspaceDir
skillsWorkspaceDir
workspaceDir
scopeKey
```

核心逻辑是：

```text
workspaceAccess === "rw"
  -> workspaceDir = agentWorkspaceDir

workspaceAccess !== "rw"
  -> workspaceDir = sandboxWorkspaceDir
```

也就是说：

| 模式 | workspaceDir 指向 | 含义 |
|---|---|---|
| `rw` | agent workspace | sandbox 直接读写原始 agent workspace。 |
| `ro` / `none` | sandbox workspace | sandbox 使用独立 workspace，避免直接写原始项目。 |

[workspace.ts](../../../submodules/openclaw/src/agents/sandbox/workspace.ts) 的 `ensureSandboxWorkspace(...)` 会创建 sandbox workspace，并从 agent workspace seed `AGENTS` / identity / tools / bootstrap / heartbeat 等默认文件。

可以记成：

> **OpenClaw 的 workspace 不是一个路径，而是一组路径：原始 agent workspace、sandbox workspace、skills workspace，根据 workspaceAccess 决定哪个给工具看。**

## 6. Docker sandbox：默认是强约束容器

Docker backend 见 [docker-backend.ts](../../../submodules/openclaw/src/agents/sandbox/docker-backend.ts) 与 [docker.ts](../../../submodules/openclaw/src/agents/sandbox/docker.ts)。

默认 Docker config 来自 [config.ts](../../../submodules/openclaw/src/agents/sandbox/config.ts)：

```text
image = openclaw-sandbox:bookworm-slim
workdir = /workspace
readOnlyRoot = true
tmpfs = /tmp, /var/tmp, /run
network = none
capDrop = ALL
```

创建容器时 [docker.ts](../../../submodules/openclaw/src/agents/sandbox/docker.ts) 会构造类似：

```text
docker create
  --name openclaw-sbx-...
  --label openclaw.sandbox=1
  --label openclaw.sessionKey=...
  --read-only
  --tmpfs /tmp
  --tmpfs /var/tmp
  --tmpfs /run
  --network none
  --cap-drop ALL
  --security-opt no-new-privileges
  --workdir /workspace
  -v <workspaceDir>:/workspace:ro-or-rw
  <image> sleep infinity
```

这和 Claw-Code 的 bash `unshare` wrapper 不同：

> **OpenClaw Docker sandbox 是长期存在、可复用、可 registry 管理的容器 runtime；exec 工具通过 `docker exec` 进入容器。**

## 7. Docker 安全校验：防止把宿主命门挂进容器

[validate-sandbox-security.ts](../../../submodules/openclaw/src/agents/sandbox/validate-sandbox-security.ts) 是 OpenClaw sandbox 的重要安全层。

它会阻止危险 bind mount，例如：

```text
/etc
/proc
/sys
/dev
/root
/boot
/run
/var/run/docker.sock
~/.ssh
~/.aws
~/.docker
~/.gnupg
~/.npm
```

还会阻止：

```text
network = host
network = container:...
seccomp = unconfined
apparmor = unconfined
```

并且会检查：

- bind source 必须是 absolute path；
- source 是否在 allowed roots 内；
- source 是否通过 symlink / existing ancestor 指向 blocked path；
- bind target 是否覆盖 `/workspace` 或 `/agent` 等 reserved container paths。

这说明 OpenClaw 不只是“用 Docker 就安全”，还会防止配置把宿主高风险路径暴露给 sandbox。

## 8. Workspace mounts：workspaceAccess 决定 ro / rw

[workspace-mounts.ts](../../../submodules/openclaw/src/agents/sandbox/workspace-mounts.ts) 构造 Docker `-v` mount 参数。

核心逻辑：

```text
workspaceDir -> container workdir
  workspaceAccess === "rw"  => writable
  workspaceAccess !== "rw"  => read-only
```

如果 `workspaceAccess !== "none"` 且 `workspaceDir !== agentWorkspaceDir`，还会额外挂载：

```text
agentWorkspaceDir -> /agent
```

读写权限取决于：

```text
workspaceAccess === "ro" -> /agent read-only
workspaceAccess === "rw" -> /agent writable
```

另一个关键细节是 skill mounts：

> **RW workspace 下，项目可以写，但 skill source 仍然会用 read-only mount 暴露，防止 sandbox 命令修改 skill 指令源。**

这体现了 OpenClaw 的产品化边界：项目 workspace 可以授权写，但 agent / skill 的指令源仍要保护。

## 9. fsBridge：host / sandbox 文件桥

[fs-bridge.ts](../../../submodules/openclaw/src/agents/sandbox/fs-bridge.ts) 创建 sandbox 文件桥，配合 [fs-paths.ts](../../../submodules/openclaw/src/agents/sandbox/fs-paths.ts) 做 path mapping。

它提供：

```text
resolvePath
readFile
writeFile
mkdirp
remove
rename
stat
```

内部会先建立 mount table：

```text
workspace mount
agent mount
read-only skill mount
custom bind mount
```

每个 mount 都有：

```text
hostRoot
containerRoot
writable
source = workspace / agent / bind / protectedSkill
```

写入 / 删除 / 重命名时，会执行：

```text
ensureWriteAccess(...)
pathGuard.assertPathSafety(...)
resolveAnchoredPinnedEntry(...)
runCheckedCommand(...)
```

这说明 OpenClaw 的文件工具不是简单地在 host 上 `fs.writeFile`，而是通过 fsBridge 处理：

- container path -> host path 映射；
- read-only / writable 判断；
- symlink / TOCTOU 防护；
- pinned path 检查；
- 必要时通过 backend command 执行 mutation。

可以记成：

> **fsBridge 是 OpenClaw sandbox 的“文件翻译官 + 安全门”。**

## 10. 工具装配：sandbox 会重配 read / write / edit / exec

[agent-tools.ts](../../../submodules/openclaw/src/agents/agent-tools.ts) 是工具面总装配入口。sandbox context 会直接改变工具表。

关键变量：

```text
const sandboxRoot = sandbox?.workspaceDir
const sandboxFsBridge = sandbox?.fsBridge
const allowWorkspaceWrites = sandbox?.workspaceAccess !== "ro"
const codingRoot = sandboxRoot ?? runtimeRoot
```

### read

如果有 sandbox：

```text
createSandboxedReadTool({
  root: sandboxRoot,
  bridge: sandboxFsBridge,
})
```

### write / edit

如果有 sandbox，普通 host write / edit 不加入；后面根据 `workspaceAccess` 决定是否加入 sandboxed write / edit：

```text
workspaceAccess = ro
  -> 不提供 write / edit

workspaceAccess = rw / none(只要 allowWorkspaceWrites 为 true)
  -> 提供 createSandboxedWriteTool / createSandboxedEditTool
```

这里要注意：`workspaceAccess !== "ro"` 会让写工具可构造，但最终能不能写还要由 fsBridge 的 mount writable 和 pathGuard 共同判断。

### exec

exec tool 会接收 `sandbox` 配置：

```text
containerName
workspaceDir
containerWorkdir
workdirValidation
validateWorkdir
buildExecSpec
finalizeExec
```

因此有 sandbox 时，exec 不再只是本地 gateway 命令，而可以进入 Docker / SSH / custom backend 执行。

精髓：

> **OpenClaw sandbox 一旦启用，工具不是同一套工具换个路径，而是 read / write / edit / exec / apply_patch / plugin / browser 都围绕 SandboxContext 重新接线。**

## 11. Exec target：auto 可落到 sandbox

exec 逻辑在 [bash-tools.exec.ts](../../../submodules/openclaw/src/agents/bash-tools.exec.ts) 和 [bash-tools.exec-runtime.ts](../../../submodules/openclaw/src/agents/bash-tools.exec-runtime.ts)。

exec target 包括：

```text
gateway
sandbox
node
auto
```

如果请求 `host=sandbox` 但当前没有 sandbox runtime，会报错：

```text
exec host=sandbox requires a sandbox runtime for this session.
Enable sandbox mode (`agents.defaults.sandbox.mode="non-main" or "all"`) or use host=auto/gateway/node.
```

如果有 sandbox，`runExecProcess(...)` 会调用 backend：

```text
sandbox.buildExecSpec({
  command,
  workdir: containerWorkdir,
  env,
  usePty,
})
```

Docker backend 会生成：

```text
docker exec ... <containerName> sh -c <command>
```

可以记成：

> **Claw-Code 是本地 bash 加安全罩；OpenClaw 是 exec target 可以直接切到 sandbox backend。**

## 12. Sandbox tool policy：sandbox 还会收窄工具菜单

[tool-policy.ts](../../../submodules/openclaw/src/agents/sandbox/tool-policy.ts) 合并 global、agent 和 default sandbox tool policy。

默认 allow / deny 来自 [constants.ts](../../../submodules/openclaw/src/agents/sandbox/constants.ts)：

```text
DEFAULT_TOOL_ALLOW:
  exec, process, read, write, edit, apply_patch, image,
  sessions_list, sessions_history, sessions_send,
  sessions_spawn, sessions_yield, subagents, session_status

DEFAULT_TOOL_DENY:
  browser, canvas, nodes, cron, gateway, channels...
```

这说明 sandbox 模式不仅改变执行环境，还改变工具可见性。默认会限制 gateway / cron / channel / nodes 等控制面工具，避免 sandboxed agent 仍然拿到过高产品控制面能力。

如果工具被 sandbox tool policy block，[runtime-status.ts](../../../submodules/openclaw/src/agents/sandbox/runtime-status.ts) 会格式化用户可读提示，并指出：

```text
Tool "..." blocked by sandbox tool policy
Reason: deny list / allow list
Fix: 修改 agents.defaults.sandbox.mode 或 sandbox tools allow / deny
```

这和 OpenClaw Permission / Security 里的结论一致：

> **OpenClaw sandbox 也是 tool policy pipeline 的一层，不只是文件系统隔离。**

## 13. Browser sandbox：浏览器能力也能绑定到工位

[context.ts](../../../submodules/openclaw/src/agents/sandbox/context.ts) 会在 `browser.enabled` 时调用 `ensureSandboxBrowser(...)`。

返回的 `SandboxContext.browser` 包括：

```text
bridgeUrl
noVncUrl
containerName
```

同时工具装配会把：

```text
sandboxBrowserBridgeUrl
allowHostBrowserControl
```

传给 OpenClaw tools 和 plugin tools。

这说明 OpenClaw sandbox 不只是命令和文件，还可以承载 browser / CDP / noVNC 这类产品能力。

## 14. Registry / prune：sandbox 是可运维资源

`resolveSandboxContext(...)` 创建 / 复用 backend 后会调用 `updateRegistry(...)`，记录：

```text
containerName
backendId
runtimeLabel
sessionKey
createdAtMs
lastUsedAtMs
image
configLabelKind
```

配置里还有：

```text
prune.idleHours
prune.maxAgeDays
```

这说明 OpenClaw sandbox 是可管理资源：可以 explain、list、recreate、remove、prune，而不只是工具调用里临时起一个进程。

## 15. 和 OpenHands / DeerFlow / Claw-Code 的区别

```text
OpenHands：
  App Server 创建 sandbox，sandbox 内运行 Agent Server。
  核心是平台控制面 / 执行面分离。

DeerFlow：
  LangGraph agent runtime 先跑，第一次 sandbox tool call 才 acquire SandboxProvider。
  核心是工作流工具执行工作台。

Claw-Code：
  本地 CLI 当前 workspace 直接作为执行中心。
  核心是 workspace 围栏 + permission + bash unshare wrapper。

OpenClaw：
  session 是否 sandboxed 决定整套工具面如何装配。
  Docker / SSH / browser / fsBridge / tool policy 一起组成 session runtime 工位。
```

一句话：

> **OpenHands 把执行面放进 sandbox；DeerFlow 让工具按需领 sandbox；Claw-Code 在本地工具调用上加边界；OpenClaw 把 sandbox 做成 Agent session 的产品级隔离工位。**

## QA / 讨论记录

### Q: OpenClaw 的 sandbox 到底是什么？

> **状态**: verified  
> **来源**: source-code / discussion

A: OpenClaw 的 sandbox 是 Agent session 级的产品化隔离运行时上下文。它先按 `mode=off/non-main/all` 判断当前 session 是否 sandboxed，再按 global / agent config 创建或复用 Docker / SSH / custom backend，准备 workspace mount、fsBridge、browser bridge、tool policy，并在 `createOpenClawCodingTools` 中把 read / write / edit / exec / plugin / browser 工具重新接到 sandbox context。

### Q: OpenClaw sandbox 的 workspaceAccess 有什么作用？

> **状态**: verified  
> **来源**: source-code / discussion

A: `workspaceAccess` 控制 sandbox workspace 和原始 agent workspace 的关系：`rw` 时 `workspaceDir = agentWorkspaceDir`，sandbox 可以直接读写原始 workspace；`ro` / `none` 时 `workspaceDir = sandboxWorkspaceDir`，sandbox 使用独立工作区。Docker mount 时 `workspaceAccess !== "rw"` 会把 workspace 以只读方式挂载；工具装配时 `ro` 会隐藏 write / edit，fsBridge 还会按 mount writable 状态做最终写入判断。

### Q: OpenClaw sandbox 和 Claw-Code sandbox 最大区别是什么？

> **状态**: verified  
> **来源**: source-code / discussion

A: Claw-Code 的 sandbox 是本地 CLI 执行边界，主要围绕当前 workspace、permission mode、文件路径检查和 bash `unshare` wrapper；OpenClaw 的 sandbox 是 session runtime 工位，会创建 / 复用 Docker 或 SSH backend，并改变工具菜单、exec target、文件桥、browser bridge 和 plugin tool 能力。可以概括为：Claw-Code 是本地施工围栏，OpenClaw 是多端 Agent 工作室里的隔离工位。

### Q: OpenClaw sandbox 是否只是 Docker container？

> **状态**: verified  
> **来源**: source-code / discussion

A: 不是。Docker 是默认 backend，但 sandbox 抽象通过 backend registry 支持 Docker、SSH 和 custom backend。即使用 Docker，sandbox 也不只是 container：还包括 scope、workspaceAccess、workspace layout、config hash、registry、prune、fsBridge、browser bridge 和 sandbox tool policy。

### Q: OpenClaw sandbox 为什么会影响工具菜单？

> **状态**: verified  
> **来源**: source-code / discussion

A: 因为 OpenClaw 是多端 Agent 产品，sandbox 不只限制文件系统，还要限制 sandboxed agent 能看到哪些产品控制面工具。默认 sandbox tool policy allow `exec/read/write/edit/apply_patch/process` 等工作区能力，deny `gateway/cron/nodes/channel/browser/canvas` 等控制面或外部能力；然后 tool policy pipeline 会把 sandbox policy 作为一层过滤规则参与最终工具面装配。
