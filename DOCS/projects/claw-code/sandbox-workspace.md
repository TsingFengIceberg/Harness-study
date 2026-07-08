# Claw-Code Sandbox / Workspace / Execution Environment 研读笔记

> **日期**: 2026-07-08 | **状态**: draft | **涉及版本**: `claw-code@4ea31c1bc91c4e9bcbd67d51c550c01e127e6d0d`

## 相关文档

- Claw-Code Agent Loop：[agent-loop.md](agent-loop.md)
- Claw-Code Tool System：[tool-system.md](tool-system.md)
- Claw-Code Context Management：[context-management.md](context-management.md)
- Claw-Code Permission / Security：[permission-security.md](permission-security.md)
- 横向 Permission / Security：[../../comparison/permission-security.md](../../comparison/permission-security.md)
- 横向 QA：[../../comparison/qa.md](../../comparison/qa.md#sandbox--workspace--execution-environment--沙箱与执行环境)

## 源码入口

| 模块 | 源码 | 说明 |
|---|---|---|
| Sandbox config / status | [sandbox.rs](../../../submodules/claw-code/rust/crates/runtime/src/sandbox.rs) | `SandboxConfig`、`SandboxRequest`、`SandboxStatus`、filesystem mode、container detection、Linux `unshare` launcher。 |
| Bash tool runtime | [bash.rs](../../../submodules/claw-code/rust/crates/runtime/src/bash.rs) | bash tool 输入参数、`sandbox_status_for_input(...)`、`prepare_command(...)`、`.sandbox-home` / `.sandbox-tmp`。 |
| Bash validation | [bash_validation.rs](../../../submodules/claw-code/rust/crates/runtime/src/bash_validation.rs) | command mode validation、destructive command 检查、path traversal / home path warning。 |
| Permission modes | [permissions.rs](../../../submodules/claw-code/rust/crates/runtime/src/permissions.rs) | `ReadOnly` / `WorkspaceWrite` / `DangerFullAccess` / `Prompt` / `Allow` 权限等级。 |
| Permission enforcer | [permission_enforcer.rs](../../../submodules/claw-code/rust/crates/runtime/src/permission_enforcer.rs) | `check_file_write(...)`、`check_bash(...)`、workspace boundary lexical normalize。 |
| Tool specs / execution | [lib.rs](../../../submodules/claw-code/rust/crates/tools/src/lib.rs) | bash schema 暴露 sandbox 参数，`execute_tool_with_enforcer(...)` 做动态权限分类。 |
| File operations | [file_ops.rs](../../../submodules/claw-code/rust/crates/runtime/src/file_ops.rs) | `read_file_in_workspace(...)`、`write_file_in_workspace(...)`、`edit_file_in_workspace(...)`、workspace boundary enforcement。 |
| Runtime config | [config.rs](../../../submodules/claw-code/rust/crates/runtime/src/config.rs) | settings 中 `sandbox.enabled`、`namespaceRestrictions`、`networkIsolation`、`filesystemMode`、`allowedMounts` 的解析。 |

## 核心结论

Claw-Code 的 sandbox / workspace 机制可以先用一句话理解：

> **Claw-Code 的 sandbox 不是 OpenHands 那种远程工位，也不是 DeerFlow 那种 provider 化工具工作台，而是本地 CLI 的 workspace 围栏 + permission mode + bash namespace wrapper。**

它服务的是本地 coding CLI：Agent 直接在用户当前工作目录附近读文件、写文件、跑 shell，所以最重要的问题不是“给每个任务分配一个远程环境”，而是：

```text
这次工具调用能不能碰当前 workspace？
这次路径有没有逃出 workspace？
这次 bash 是只读、workspace 内写入，还是高危全权限？
如果系统支持，能不能给 bash 套一层 Linux namespace？
```

可以把 Claw-Code 的执行边界拆成四层：

```text
ToolSpec.required_permission
  -> PermissionPolicy / PermissionPrompter
  -> PermissionEnforcer / dynamic classification
  -> workspace boundary + bash sandbox status
```

通俗比喻：

> **Claw-Code 像本地施工现场。代码就在你机器上的工地里，workspace 是围栏，PermissionMode 是施工许可证，PermissionEnforcer 是门口保安，bash 的 unshare sandbox 是给危险工具临时罩上的安全棚。**

## 功能清单

如果只问“Claw-Code 的 sandbox / workspace 执行边界有什么作用”，可以浓缩成这些：

| 功能 | 作用 |
|---|---|
| 以当前 workspace 为中心执行 | read / write / edit / glob / grep 等工具默认围绕 `std::env::current_dir()` 作为 workspace root。 |
| 区分权限等级 | `ReadOnly`、`WorkspaceWrite`、`DangerFullAccess`、`Prompt`、`Allow` 表示当前 session / tool call 的权限边界。 |
| 文件写入围栏 | `WorkspaceWrite` 下写文件必须留在 workspace 内；workspace 外路径需要 `DangerFullAccess` 或被拒绝。 |
| 读 / 搜索边界 | `read_file`、`glob_search`、`grep_search` 也会按路径是否在 workspace 内动态分类，越界则升级为高风险。 |
| bash 动态分类 | bash 默认高风险，但只读命令且路径看起来在 workspace 内时，可以降为较低风险；危险命令仍要求更高权限。 |
| bash validation | 对 read-only mode、`sed -i`、destructive command、`../`、`~/`、`$HOME` 等做 warning / block。 |
| Linux namespace wrapper | Linux 且 `unshare` 可用时，bash 可以通过 user / mount / pid / ipc / uts / optional net namespace 启动。 |
| network isolation 开关 | `networkIsolation` 或工具参数 `isolateNetwork` 可请求 `unshare --net`。 |
| filesystem mode 状态 | `off` / `workspace-only` / `allow-list` 写入 sandbox status 和环境变量，供执行环境识别。 |
| fallback 可观测 | `SandboxStatus` 会记录 enabled、supported、active、fallback_reason、container markers，避免“以为隔离了但其实没有”不可见。 |

最短理解：

> **Claw-Code 的本地执行安全感来自“路径别出 workspace、权限别越级、bash 别裸奔”。**

## WorkspaceWrite：本地 workspace 围栏

[permissions.rs](../../../submodules/claw-code/rust/crates/runtime/src/permissions.rs) 定义权限等级：

```text
ReadOnly
WorkspaceWrite
DangerFullAccess
Prompt
Allow
```

其中 `WorkspaceWrite` 是 sandbox / workspace 主题的核心词。

它不是“可以随便写本机”，而是：

> **可以写，但应该只写当前 workspace 内。**

执行层的 [permission_enforcer.rs](../../../submodules/claw-code/rust/crates/runtime/src/permission_enforcer.rs) 里，`check_file_write(path, workspace_root)` 的核心逻辑是：

```text
ReadOnly
  -> deny file write

WorkspaceWrite
  -> path 在 workspace_root 内：allow
  -> path 在 workspace_root 外：deny，要求 DangerFullAccess

DangerFullAccess / Allow
  -> allow

Prompt
  -> deny / 需要交互确认
```

这就是 Claw-Code 的 workspace jail 精髓：

> **workspace 是围栏；WorkspaceWrite 只允许在围栏内施工。**

## 路径边界：不是简单字符串前缀

`PermissionEnforcer` 的 workspace 判断会先做 lexical normalize，再比较 workspace root：

```text
/workspace/src/main.rs          -> OK
/workspace                      -> OK
/workspacex/hack                -> not OK
/workspace/../../etc/crontab    -> not OK
../etc/passwd                   -> not OK
```

它不是简单 `starts_with("/workspace")`，否则 `/workspacex` 这种路径会误判。

同时 [file_ops.rs](../../../submodules/claw-code/rust/crates/runtime/src/file_ops.rs) 的 `read_file_in_workspace(...)`、`write_file_in_workspace(...)`、`edit_file_in_workspace(...)` 也会在真实文件操作前做 workspace boundary enforcement。

所以 Claw-Code 的文件边界有两层：

| 层 | 作用 |
|---|---|
| `PermissionEnforcer` | 按权限模式判断这次路径是否允许。 |
| `file_ops::*_in_workspace` | 在真实 read / write / edit / glob / grep 前再检查 workspace boundary。 |

这点和 Permission / Security 里的“两道权限门”是一致的。

## ToolSpec：工具默认风险标签

[tools/src/lib.rs](../../../submodules/claw-code/rust/crates/tools/src/lib.rs) 里的内置工具定义会给每个工具一个默认 `required_permission`。

典型例子：

| 工具 | 默认权限 | 理由 |
|---|---|---|
| `read_file` | `ReadOnly` | 读 workspace 文件。 |
| `glob_search` / `grep_search` | `ReadOnly` | 搜索 workspace 内容。 |
| `write_file` / `edit_file` | `WorkspaceWrite` | 修改 workspace 文件。 |
| `bash` | `DangerFullAccess` | shell 能做任意事。 |
| `WebFetch` / `WebSearch` | `DangerFullAccess` | 外部网络访问。 |

这只是第一层粗粒度标签。真正执行前，`execute_tool_with_enforcer(...)` 还会按具体参数动态分类。

## 动态分类：同一个工具，不同参数风险不同

[execute_tool_with_enforcer(...)](../../../submodules/claw-code/rust/crates/tools/src/lib.rs) 会针对具体工具参数重新计算 required mode：

```text
bash
  -> classify_bash_permission(command)

read_file
  -> classify_read_path_permission(path)

write_file / edit_file
  -> classify_file_path_permission(path)

glob_search / grep_search
  -> classify_glob_permission / classify_grep_permission
```

这说明 Claw-Code 不只问“你用了哪个工具”，还问“你这次怎么用”。

例如：

```text
read_file("README.md")
  -> ReadOnly

read_file("/etc/passwd")
  -> DangerFullAccess

write_file("src/main.rs")
  -> WorkspaceWrite

write_file("/tmp/outside.txt")
  -> DangerFullAccess
```

bash 更典型：

```text
bash("ls -la")
  -> 可能是较低风险

bash("rm -rf /")
  -> 动态分类会提升到高风险权限；是否进一步 warning / block 取决于 bash validation 在具体执行路径中的接入情况
```

精髓：

> **Claw-Code 的 sandbox 边界不是单靠工具名，而是工具名 + 参数 + 当前 workspace + 当前 permission mode 一起决定。**

## Bash validation：安全检查模块，调用路径需继续核验

bash 是 Claw-Code sandbox 主题里最危险的一类工具。

[bash_validation.rs](../../../submodules/claw-code/rust/crates/runtime/src/bash_validation.rs) 提供一套 command validation pipeline：

```text
validate_command(command, mode, workspace)
  -> validate_mode(...)
  -> validate_sed(...)
  -> check_destructive(...)
  -> validate_paths(...)
```

重点包括：

| 检查 | 作用 |
|---|---|
| ReadOnly mode validation | read-only 模式下只允许保守的只读命令。 |
| WorkspaceWrite mode validation | 检查是否明显操作 `/etc`、`/usr`、`/var`、`/boot`、`/sys`、`/proc`、`/dev` 等系统路径。 |
| sed validation | read-only 下阻止 `sed -i` 这种原地修改。 |
| destructive command | 检查 `rm -rf` 等危险模式，尤其 broad target。 |
| path validation | 对 `../`、`~/`、`$HOME` 等可能逃出 workspace 的路径给出 warning。 |

但第一轮 grep 到的主工具执行路径里，已经确认的是 [tools/src/lib.rs](../../../submodules/claw-code/rust/crates/tools/src/lib.rs) 的 `classify_bash_permission(...)` 和 `PermissionEnforcer` 动态权限检查；`validate_command(...)` 是否在实际 CLI bash 执行路径中被调用，还需要后续继续核验。

因此当前应谨慎表述为：

> **文件工具主要看路径；bash 工具已确认会做动态权限分类，另有 bash validation 安全检查模块，但完整 validation pipeline 在真实执行链路中的接入位置暂标记为 to-verify。**

## Bash sandbox：Linux unshare wrapper

Claw-Code 确实有一个明确的 bash sandbox 层，实现在 [sandbox.rs](../../../submodules/claw-code/rust/crates/runtime/src/sandbox.rs) 和 [bash.rs](../../../submodules/claw-code/rust/crates/runtime/src/bash.rs)。

配置结构包括：

```text
SandboxConfig:
  enabled
  namespace_restrictions
  network_isolation
  filesystem_mode
  allowed_mounts
```

每次 bash tool 执行时，[bash.rs](../../../submodules/claw-code/rust/crates/runtime/src/bash.rs) 会：

```text
读取 settings.sandbox
  -> 合并 tool input override
  -> resolve_sandbox_status_for_request(...)
  -> prepare_command / prepare_tokio_command
  -> 如果可以 build_linux_sandbox_command，就用 unshare 包装
  -> 否则 fallback 到 sh -lc
```

`build_linux_sandbox_command(...)` 会构造：

```text
unshare
  --user
  --map-root-user
  --mount
  --ipc
  --pid
  --uts
  --fork
  [--net]
  sh -lc <command>
```

并设置：

```text
HOME=<cwd>/.sandbox-home
TMPDIR=<cwd>/.sandbox-tmp
CLAWD_SANDBOX_FILESYSTEM_MODE=workspace-only / allow-list / off
CLAWD_SANDBOX_ALLOWED_MOUNTS=<paths>
```

这说明 Claw-Code 的 sandbox 更像：

> **给 bash 这把万能钥匙套一层 Linux namespace 安全棚。**

## SandboxStatus：隔离是否真的生效要可观测

[sandbox.rs](../../../submodules/claw-code/rust/crates/runtime/src/sandbox.rs) 的 `SandboxStatus` 记录：

```text
enabled
supported
active
namespace_supported / namespace_active
network_supported / network_active
filesystem_mode / filesystem_active
allowed_mounts
in_container / container_markers
fallback_reason
```

这点很重要，因为本地 sandbox 可能因为系统环境不支持而退化：

```text
不是 Linux
没有 unshare
user namespace 不可用
network namespace 不可用
allow-list 没有 mounts
```

此时不能假装“已经强隔离”。`SandboxStatus` 把请求、支持情况、active 状态和 fallback reason 带回 bash output，方便上层和用户知道真实情况。

## 不能夸大：filesystem mode 不是完整 Docker / VM 隔离

第一轮已读代码里，[sandbox.rs](../../../submodules/claw-code/rust/crates/runtime/src/sandbox.rs) 会构造 namespace launcher 和环境变量，但没有看到完整的：

```text
bind mount workspace
remount root readonly
chroot / pivot_root
按 allowed_mounts 裁剪真实 filesystem
```

因此文档里要谨慎表达：

> **Claw-Code 有 bash namespace sandbox 和 filesystem mode 配置，但当前第一轮读到的实现更像 namespace wrapper + sandbox status + 环境变量 + permission / path validation 共同防护；不能直接写成 Docker / VM 级强隔离。**

它和 OpenHands / DeerFlow AIO provider 不是同一种隔离层级。

## 和 OpenHands / DeerFlow 的区别

```text
OpenHands：
  App Server 创建 sandbox
  sandbox 内运行 Agent Server
  Terminal / FileEditor 在 sandbox workspace 中执行

DeerFlow：
  LangGraph agent runtime 先跑
  第一次 sandbox tool call 时 acquire SandboxProvider
  工具在 sandbox abstraction 中执行

Claw-Code：
  本地 CLI 当前 workspace 直接作为执行中心
  工具调用前用 PermissionPolicy / PermissionEnforcer 管权限
  文件工具检查 workspace boundary
  bash 可选套 Linux unshare sandbox
```

一句话：

> **OpenHands 是“把 Agent 放进远程房间”；DeerFlow 是“工具要用时领工作台”；Claw-Code 是“在本地工地干活，但用 workspace 围栏、权限闸门和 bash 安全棚限制危险动作”。**

## 和 Permission / Security 的关系

Claw-Code 的 sandbox / workspace 边界和 [permission-security.md](permission-security.md) 是同一条链路的不同侧面。

Permission / Security 专题强调的是：

```text
PreToolUse hook
  -> PermissionPolicy / PermissionPrompter
  -> PermissionEnforcer / dynamic classification
  -> PostToolUse hook
```

Sandbox / Workspace 专题强调的是：

```text
PermissionEnforcer 怎么判断 workspace 内外？
bash 怎么判断危险路径 / 命令？
Linux unshare sandbox 什么时候生效？
如果 sandbox 不支持，怎么通过 SandboxStatus 暴露 fallback？
```

因此可以合起来理解：

> **Claw-Code 的 sandbox 不是独立子系统，而是本地工具权限链路里的执行边界层。**

## QA / 讨论记录

### Q: Claw-Code 的 sandbox 到底是什么？

> **状态**: verified  
> **来源**: source-code / discussion

A: Claw-Code 的 sandbox 主要是本地 CLI 的执行边界组合：当前 workspace 是核心围栏，`PermissionMode` 控制读 / 写 / 高危动作，`PermissionEnforcer` 和文件工具检查路径是否留在 workspace 内，bash 工具还可以在 Linux 下用 `unshare` 套 user / mount / pid / ipc / uts / optional network namespace。它不是 OpenHands 那种远程 sandbox，也不是 DeerFlow 那种 provider 化 sandbox abstraction。

### Q: WorkspaceWrite 是不是可以写任意本机文件？

> **状态**: verified  
> **来源**: source-code / discussion

A: 不是。`WorkspaceWrite` 的含义是可以写 workspace 内资源。`PermissionEnforcer.check_file_write(...)` 在 `WorkspaceWrite` 下会检查 path 是否位于 `workspace_root` 内；如果路径在 workspace 外，会拒绝并要求 `DangerFullAccess`。真实文件工具如 `write_file_in_workspace(...)` / `edit_file_in_workspace(...)` 也会执行 workspace boundary enforcement。

### Q: Claw-Code 的 bash sandbox 是强容器隔离吗？

> **状态**: to-verify  
> **来源**: source-code / discussion

A: 第一轮已读代码确认 Claw-Code 会在 Linux 且 `unshare` 可用时为 bash 构造 user / mount / pid / ipc / uts / optional network namespace，并设置 `.sandbox-home`、`.sandbox-tmp` 和 sandbox 环境变量。但当前未看到完整 bind mount / remount readonly / chroot / pivot_root / allowed_mounts 强制裁剪，因此不应直接写成 Docker / VM 级强隔离。更谨慎的说法是：它是 bash 的本地 Linux namespace wrapper，和 permission / path validation 共同构成防线。

### Q: `bash_validation.rs` 的完整 validation pipeline 是否每次 bash 执行都会调用？

> **状态**: to-verify  
> **来源**: source-code / discussion

A: 暂不能这样断言。第一轮 grep 已确认 `bash_validation.rs` 定义了 `validate_command(command, mode, workspace)`，并有 read-only、sed、destructive、path traversal 等检查和测试；但在已读主工具执行路径里，已经确认的是 `tools/src/lib.rs` 的 `classify_bash_permission(...)` 以及 `PermissionEnforcer` 动态 required mode 检查。`validate_command(...)` 在实际 CLI bash 执行链路中的接入点需要继续核验，因此当前只写成“存在 bash validation 安全检查模块”，不写成“每次 bash 都会走完整 pipeline”。

### Q: Claw-Code 和 OpenHands / DeerFlow 的 sandbox 精髓差异是什么？

> **状态**: verified  
> **来源**: source-code / discussion

A: OpenHands 的 sandbox 是远程隔离工位，sandbox 内跑 Agent Server；DeerFlow 的 sandbox 是 LangGraph 工具调用按需 acquire 的 provider 化工作台；Claw-Code 的 sandbox 是本地 CLI workspace 执行边界，靠 workspace 围栏、权限模式、动态分类、文件路径检查和 bash namespace wrapper 限制危险动作。可以概括为：OpenHands 把 Agent 放进房间，DeerFlow 让工具领工作台，Claw-Code 在本地工地加围栏和安全棚。
