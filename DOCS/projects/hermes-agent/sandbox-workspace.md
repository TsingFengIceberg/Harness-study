# Hermes Agent Sandbox / Workspace：可配置 Terminal Environment、远程后端与 execute_code 小沙箱

> **日期**: 2026-07-08 | **状态**: draft | **涉及版本**: `05cbddc01234ea120cccc1f62d36f1ef352b0d52`

## 相关文档

- Hermes Agent 笔记入口：[README.md](README.md)
- Agent Loop：[agent-loop.md](agent-loop.md)
- Tool System：[tool-system.md](tool-system.md)
- Context Management：[context-management.md](context-management.md)
- Permission / Security：[permission-security.md](permission-security.md)
- 横向 QA：[../../comparison/qa.md](../../comparison/qa.md#sandbox--workspace--execution-environment--沙箱与执行环境)

## 源码入口

| 模块 | 源码 | 作用 |
|---|---|---|
| Terminal tool 主入口 | [terminal_tool.py](../../../submodules/hermes-agent/tools/terminal_tool.py) | `terminal_tool(...)`，读取 `TERMINAL_ENV` / `TERMINAL_CWD` / container 配置，创建或复用执行环境，执行危险命令审批、workdir 校验、前后台进程管理。 |
| Environment 基类 | [base.py](../../../submodules/hermes-agent/tools/environments/base.py) | `BaseEnvironment`，统一 spawn-per-call、session snapshot、cwd tracking、interrupt / timeout / stdout drain。 |
| Local backend | [local.py](../../../submodules/hermes-agent/tools/environments/local.py) | `LocalEnvironment`，直接在宿主机执行 bash，过滤 Hermes provider / gateway secrets，管理本地进程组。 |
| Docker backend | [docker.py](../../../submodules/hermes-agent/tools/environments/docker.py) | `DockerEnvironment`，Docker / Podman 容器、cap / tmpfs / resource limit、workspace / home mount、credential / skills read-only mount、container reuse / orphan reaper。 |
| Singularity backend | [singularity.py](../../../submodules/hermes-agent/tools/environments/singularity.py) | `SingularityEnvironment`，Apptainer / Singularity instance、`--containall` / `--no-home`、overlay / writable tmpfs。 |
| Modal backend | [modal.py](../../../submodules/hermes-agent/tools/environments/modal.py) | `ModalEnvironment`，Modal cloud sandbox、snapshot restore、file sync、credential / skills mount。 |
| Daytona backend | [daytona.py](../../../submodules/hermes-agent/tools/environments/daytona.py) | `DaytonaEnvironment`，Daytona cloud sandbox、persistent sandbox resume、resource config、file sync。 |
| SSH backend | [ssh.py](../../../submodules/hermes-agent/tools/environments/ssh.py) | `SSHEnvironment`，远程 SSH 执行、ControlMaster、remote `.hermes` sync。 |
| File sync | [file_sync.py](../../../submodules/hermes-agent/tools/environments/file_sync.py) | `FileSyncManager`，SSH / Modal / Daytona 等远程后端的 credentials / skills / cache 文件同步与 sync-back。 |
| File tools | [file_tools.py](../../../submodules/hermes-agent/tools/file_tools.py) | read / write / patch / search 的工具层入口，路径解析、敏感路径 / cross-profile guard、file ops cache。 |
| Shell file operations | [file_operations.py](../../../submodules/hermes-agent/tools/file_operations.py) | `ShellFileOperations`，通过当前 terminal env 执行 `cat` / `mkdir` / atomic write / patch / lint / LSP diagnostics。 |
| File safety | [file_safety.py](../../../submodules/hermes-agent/agent/file_safety.py) | sensitive write denylist、safe write root、read block、cross-profile / sandbox mirror 警告。 |
| Command approval | [approval.py](../../../submodules/hermes-agent/tools/approval.py) | dangerous / hardline command detection、per-session approval、gateway / interactive approval context。 |
| execute_code | [code_execution_tool.py](../../../submodules/hermes-agent/tools/code_execution_tool.py) | Python PTC 小沙箱：临时脚本 + `hermes_tools.py` RPC stub，限制可调用工具、scrub env、timeout / stdout cap。 |
| ACP session cwd | [session.py](../../../submodules/hermes-agent/acp_adapter/session.py) | ACP session `cwd` 到 terminal/file tool task override 的绑定。 |
| ACP edit approval | [edit_approval.py](../../../submodules/hermes-agent/acp_adapter/edit_approval.py) | diff-based edit approval，workspace / session auto-approve policy 与敏感路径例外。 |
| 默认配置 | [config.py](../../../submodules/hermes-agent/hermes_cli/config.py) | terminal backend、Docker volumes、network、container persistence、code execution mode、checkpoints 等配置默认值。 |

## 1. 核心结论

Hermes Agent 的 sandbox / workspace 不能简单理解成“固定 Docker 沙箱”。它更像一个长期个人 Agent 的 **可配置执行工作台**：

```text
模型调用 terminal / file / execute_code
  -> terminal_tool / file_tools / code_execution_tool
     -> 当前 task/session 的 Terminal Environment
        -> local / docker / singularity / modal / daytona / ssh backend
        -> cwd / workspace / env snapshot / file ops / approval / guardrail
```

最重要的一句话：

> **Hermes 的 sandbox 是以 Terminal Environment 为核心的可切换执行后端：默认可以直接跑在本机 local，也可以切到 Docker / Singularity / Modal / Daytona / SSH 等隔离或远程环境；file tools 和 execute_code 都围绕这套环境复用 cwd、workspace 和安全 guardrail。**

所以它和前几个项目的差异是：

```text
OpenHands:
  App Server 创建远程 sandbox，sandbox 内跑 Agent Server。

DeerFlow:
  LangGraph 工具调用按需 acquire SandboxProvider。

Claw-Code:
  本地 CLI workspace 围栏 + permission mode + unshare wrapper。

OpenClaw:
  session 级 sandbox context 重写工具菜单 / exec target / fsBridge。

Hermes:
  长期个人 Agent 的 terminal execution workbench；
  local 是默认，Docker / cloud / SSH 是可选 backend，
  execute_code 又有一层小型 Python RPC sandbox。
```

一句话比喻：

> **Hermes 像长期个人助理的工作间：默认就在你的电脑桌面上干活；需要隔离时可以切到 Docker / Modal / Daytona / SSH 工位；需要批处理时还能开一个临时 Python 小隔间，让脚本通过 RPC 调有限工具。**

## 2. 总体结构：Terminal Environment 是执行环境核心

Hermes 的终端工具说明直接说它支持多种环境，见 [terminal_tool.py:4-17](../../../submodules/hermes-agent/tools/terminal_tool.py#L4-L17)：

```text
local        -> 直接在宿主机执行
Docker       -> 容器环境
Modal        -> 云 sandbox
SSH          -> 远程机器
Singularity  -> HPC / Apptainer 风格容器
Daytona      -> cloud sandbox
```

真正的执行环境接口集中在 [BaseEnvironment](../../../submodules/hermes-agent/tools/environments/base.py#L290-L347)。它统一了这些后端的行为：

```text
BaseEnvironment
  - _run_bash(...)       # 每个后端自己实现如何跑 bash
  - execute(...)         # 基类统一封装命令执行
  - init_session(...)    # 捕获 shell env / alias / function snapshot
  - cwd tracking         # 每次命令后通过 marker 更新 cwd
  - interrupt / timeout  # 统一轮询、kill、超时
```

注意 Hermes 的基类文档很关键：[base.py:1-5](../../../submodules/hermes-agent/tools/environments/base.py#L1-L5) 明确说：

```text
Unified spawn-per-call model:
  every command spawns a fresh bash -c process.
A session snapshot is captured once at init and re-sourced before each command.
CWD persists via stdout markers or temp file.
```

这说明 Hermes 并不是始终保留一个真正的交互 shell 进程，而是：

```text
每次工具调用新起 bash
  -> source 上一次保存的 env / alias / function snapshot
  -> cd 到当前 cwd
  -> eval 用户命令
  -> 保存新的 env snapshot 和 cwd marker
```

这和 OpenHands / OpenClaw 那种“远程 Agent Server / session runtime”不同。Hermes 的执行环境更偏工具层：它给 terminal / file / code execution 提供统一工作台。

## 3. 环境选择：`TERMINAL_ENV` 决定跑在哪里

Hermes 的终端环境配置入口是 [terminal_tool.py:_get_env_config](../../../submodules/hermes-agent/tools/terminal_tool.py#L1256-L1378)。关键字段来自环境变量：

| 配置 | 含义 |
|---|---|
| `TERMINAL_ENV` | `local` / `docker` / `singularity` / `modal` / `daytona` / `ssh`。默认 `local`。 |
| `TERMINAL_CWD` | 当前工作目录 / workspace 根。local 下通常是宿主 cwd；container 下会做 sanitization。 |
| `TERMINAL_DOCKER_IMAGE` | Docker backend 镜像，默认 `nikolaik/python-nodejs:python3.11-nodejs20`。 |
| `TERMINAL_CONTAINER_CPU/MEMORY/DISK` | container / cloud backend 资源限制。 |
| `TERMINAL_CONTAINER_PERSISTENT` | 是否持久化 container filesystem。默认 true。 |
| `TERMINAL_DOCKER_VOLUMES` | 用户配置的 Docker bind mounts。 |
| `TERMINAL_DOCKER_MOUNT_CWD_TO_WORKSPACE` | 是否把宿主 cwd 挂到 `/workspace`。默认 false。 |
| `TERMINAL_DOCKER_NETWORK` | Docker 是否联网。默认 true；false 时加 `--network=none`。 |
| `TERMINAL_DOCKER_RUN_AS_HOST_USER` | 是否用宿主 uid/gid 跑容器，解决 bind mount 文件 ownership。 |

默认配置也能在 [config.py:1150-1188](../../../submodules/hermes-agent/hermes_cli/config.py#L1150-L1188) 看到：Docker volumes 默认空，`docker_mount_cwd_to_workspace` 默认 false，`docker_network` 默认 true，`container_persistent` 默认 true。

这个默认组合很重要：

> **Hermes 默认不是“所有命令自动进强隔离容器”。默认 `TERMINAL_ENV=local`，终端命令直接在宿主机跑；只有配置为 Docker / Singularity / Modal / Daytona / SSH 时，terminal 和 file tools 才进入对应后端。**

## 4. Terminal tool：命令执行前的统一关口

模型调用 `terminal` 时，入口是 [terminal_tool.py:2010](../../../submodules/hermes-agent/tools/terminal_tool.py#L2010)。主流程可以简化为：

```text
terminal_tool(command, background, timeout, task_id, workdir, ...)
  -> _get_env_config()
  -> _resolve_container_task_id(task_id)
  -> resolve_task_overrides(task_id)
  -> get/create active environment
  -> check_all_guards(command, env_type, has_host_access)
  -> validate workdir
  -> foreground: env.execute(command, cwd=...)
  -> background: process_registry.spawn_local / spawn_via_env
```

两个点特别值得标记。

### 4.1 `task_id` 默认会折叠到 `default`

Hermes 会把工具调用的 `task_id` 映射成 active environment key，见 [terminal_tool.py:1123-1155](../../../submodules/hermes-agent/tools/terminal_tool.py#L1123-L1155)。注释直接说明：

```text
delegate_task 子 agent 有自己的 task_id，
但默认折叠回 "default"，共享父 agent 的 long-lived container：
  one bash, one /workspace, one set of installed packages。
```

只有当 `register_task_env_overrides(...)` 注册了 `docker_image` / `modal_image` / `singularity_image` / `daytona_image` / `env_type` 这类隔离相关 override 时，才返回原始 task_id，创建独立 sandbox。

这说明 Hermes 的默认思路不是“每个子 agent 一个独立容器”，而是长期个人 Agent 共享一个工作台；RL / benchmark / 特定任务才按 task 隔离。

### 4.2 危险命令在执行前统一检查

命令真正执行前，会进入 [terminal_tool.py:2273-2319](../../../submodules/hermes-agent/tools/terminal_tool.py#L2273-L2319)：

```text
_check_all_guards(command, env_type, has_host_access)
  -> dangerous command / hardline command / approval
```

`has_host_access` 会在 Docker 后端下考虑宿主路径是否被 bind mount，见 [terminal_tool.py:272-278](../../../submodules/hermes-agent/tools/terminal_tool.py#L272-L278)：

```text
Docker sandbox 暴露 host path 时，风险更接近 host access。
```

这点很关键：Hermes 不只看 `env_type=docker` 就认为安全。如果 Docker 配了 `docker_mount_cwd_to_workspace` 或用户 volumes，把宿主目录挂进容器，危险命令判断会知道它有 host access。

## 5. LocalEnvironment：默认本地执行，不是强沙箱

[LocalEnvironment](../../../submodules/hermes-agent/tools/environments/local.py#L922-L934) 的注释很直接：

```text
Run commands directly on the host machine.
Spawn-per-call: every execute() spawns a fresh bash process.
Session snapshot preserves env vars across calls.
CWD persists via file-based read after each command.
```

也就是说：

```text
TERMINAL_ENV=local
  -> bash 在宿主机当前用户权限下执行
  -> 不是 Docker / VM / namespace 强隔离
  -> 安全主要靠 command approval、env filtering、file safety、interrupt、进程组 kill
```

Local backend 会做一些重要防护：

| 防护 | 位置 | 说明 |
|---|---|---|
| Provider / gateway secret blocklist | [local.py:119-227](../../../submodules/hermes-agent/tools/environments/local.py#L119-L227) | 从 provider / tool / gateway config 推导需要剥离的 secret env。 |
| Hermes dynamic secret 过滤 | [local.py:242-284](../../../submodules/hermes-agent/tools/environments/local.py#L242-L284) | 过滤 `AUXILIARY_*_API_KEY`、`GATEWAY_RELAY_*_SECRET` 等动态密钥。 |
| run env 构造 | [local.py:794-836](../../../submodules/hermes-agent/tools/environments/local.py#L794-L836) | 构造 subprocess env，剥离敏感变量、桥接 session context、清掉 `VIRTUAL_ENV` / `CONDA_PREFIX` marker。 |
| process group kill | [local.py:1059-1137](../../../submodules/hermes-agent/tools/environments/local.py#L1059-L1137) | interrupt / timeout 时 kill 整个进程组，避免子进程残留。 |

但要注意：这些是 **本地执行安全工程**，不是强隔离边界。Hermes 的 local 模式和 Claw-Code 本地 CLI 有点像：都要保护本机，但 Hermes 更强调长期个人 Agent 的 secret hygiene、approval 和 session cwd。

## 6. DockerEnvironment：可选容器后端，但默认不是最严格隔离

Docker 后端在 [docker.py](../../../submodules/hermes-agent/tools/environments/docker.py)。核心定位见 [docker.py:568-577](../../../submodules/hermes-agent/tools/environments/docker.py#L568-L577)：

```text
Hardened Docker container execution with resource limits and persistence.
The container itself is the security boundary.
Filesystem inside is writable so agents can install packages.
Writable workspace via tmpfs or bind mounts.
```

### 6.1 安全参数

基础安全参数在 [docker.py:336-344](../../../submodules/hermes-agent/tools/environments/docker.py#L336-L344)：

```text
--cap-drop ALL
--cap-add DAC_OVERRIDE / CHOWN / FOWNER
--security-opt no-new-privileges
--tmpfs /tmp:rw,nosuid,size=512m
--tmpfs /var/tmp:rw,noexec,nosuid,size=256m
```

如果容器不是用 `--user` 直接跑宿主 uid/gid，还会为 image 内 init/drop privilege 加回 `SETUID` / `SETGID`，见 [docker.py:357-379](../../../submodules/hermes-agent/tools/environments/docker.py#L357-L379)。资源限制会在 cgroup controller 可用时加 `--cpus` / `--memory` / `--pids-limit`，见 [docker.py:449-498](../../../submodules/hermes-agent/tools/environments/docker.py#L449-L498)。

这比普通 `docker run` 更谨慎，但和 OpenClaw 的默认 Docker sandbox 仍有差异：

| 点 | Hermes Docker | OpenClaw Docker |
|---|---|---|
| 网络 | 默认 `docker_network=true`，可设 false 加 `--network=none` | 默认偏 `network=none`。 |
| rootfs | 容器内 filesystem 可写，方便 install packages | 更强调 read-only root + tmpfs。 |
| host cwd mount | 默认不挂；显式 `docker_mount_cwd_to_workspace=true` 才挂 | 由 workspaceAccess / mounts 控制。 |
| 工具重写 | terminal/file tools 走同一 env backend | sandbox context 会重写 read/write/edit/exec/plugin/browser 工具面。 |

所以不要把 Hermes Docker 直接等同于 OpenClaw / OpenHands 的产品级 sandbox。它是一个可选的终端执行后端，目标是让长期个人 Agent 能在容器里跑命令和保留工作状态。

### 6.2 workspace / home mount

Docker workspace 处理在 [docker.py:645-705](../../../submodules/hermes-agent/tools/environments/docker.py#L645-L705)：

- persistent 模式：在 `get_sandbox_dir() / "docker" / task_id` 下创建 host-side `home` 和 `workspace`，分别挂到 `/root` 和 `/workspace`；
- non-persistent 模式：给 `/workspace`、`/home`、`/root` 挂 tmpfs；
- 如果 `docker_mount_cwd_to_workspace=true` 且宿主 cwd 有效，会把 host cwd bind mount 到 `/workspace`；
- 如果用户 `docker_volumes` 已经挂了 `/workspace`，就不重复挂 cwd。

默认配置注释在 [config.py:1157-1167](../../../submodules/hermes-agent/hermes_cli/config.py#L1157-L1167) 也强调：

```text
Explicit opt-in: mount the host cwd into /workspace for Docker sessions.
Default off because passing host directories into a sandbox weakens isolation.
```

这就是 Hermes Docker sandbox 的关键取舍：

> **不挂宿主 cwd 时，容器隔离更强，但和真实项目文件的连通性弱；挂宿主 cwd 时，开发体验更像本地 workspace，但隔离边界明显变弱。**

### 6.3 credentials / skills / cache mount

Docker 会把 credential files、skills 目录、cache 目录挂进去，见 [docker.py:710-787](../../../submodules/hermes-agent/tools/environments/docker.py#L710-L787)：

- credential files：read-only mount；
- skill directories：read-only mount；
- cache directories：read-only mount；

这符合 Hermes 的个人助理定位：容器里的 agent 仍需要访问 OAuth token、skills、缓存媒体等个人上下文，但默认尽量用只读方式挂进去。

### 6.4 container reuse 与 orphan reaper

Hermes Docker 还支持跨进程复用 labeled container，见 [docker.py:885-965](../../../submodules/hermes-agent/tools/environments/docker.py#L885-L965)。如果之前同一 task/profile 的容器还在，就 attach / start，而不是每次创建新容器。

同时有 orphan reaper 清理异常退出留下的容器，见 [docker.py:140-231](../../../submodules/hermes-agent/tools/environments/docker.py#L140-L231)。

这说明 Hermes 追求的是长期个人 Agent 工作台：容器状态可以保留、复用、清理，而不是每个 turn 都一次性起销毁。

## 7. Remote / cloud backends：SSH、Modal、Daytona、Singularity

Hermes 的 terminal env 不止 Docker。

### 7.1 SSHEnvironment

[SSHEnvironment](../../../submodules/hermes-agent/tools/environments/ssh.py#L35-L80) 通过 SSH 在远程机器执行命令：

```text
ssh ... bash -c
ControlMaster connection reuse
remote .hermes sync
cwd via stdout markers
```

它用 [FileSyncManager](../../../submodules/hermes-agent/tools/environments/file_sync.py#L130-L160) 同步 credentials / skills / cache 到远端 `.hermes`，并在 cleanup 时支持 sync-back。这里的“sandbox”更像远程机器工作环境，不一定是容器隔离，安全边界取决于远程账号和机器本身。

### 7.2 ModalEnvironment / DaytonaEnvironment

[ModalEnvironment](../../../submodules/hermes-agent/tools/environments/modal.py#L164-L293) 创建 Modal cloud sandbox；[DaytonaEnvironment](../../../submodules/hermes-agent/tools/environments/daytona.py#L29-L151) 创建或恢复 Daytona cloud sandbox。

这两者都强调：

```text
cloud sandbox
persistent filesystem / snapshot / resume
file sync
cancel / stop support
```

它们更接近“远程沙箱工位”，但依然是 Hermes terminal backend 的一种，不是整个 Agent loop 搬到 sandbox 内跑。Hermes 主 loop 仍在主进程里，工具执行通过 backend 下发。

### 7.3 SingularityEnvironment

[SingularityEnvironment](../../../submodules/hermes-agent/tools/environments/singularity.py#L158-L195) 用 Apptainer / Singularity instance 执行命令。启动时加：

```text
--containall
--no-home
--overlay 或 --writable-tmpfs
credential / skills read-only bind
```

这更适合 HPC / 受限环境。

## 8. File tools：不是直接本地写文件，而是跟随 terminal env

Hermes 的 file tools 是 sandbox / workspace 主题里最容易误解的部分。

表面上模型调用的是：

```text
read_file / write_file / patch / search_files
```

但实际路径是：

```text
file_tools.py
  -> _resolve_path_for_task(task_id)
  -> _get_file_ops(task_id)
     -> get or create terminal environment
     -> ShellFileOperations(terminal_env)
        -> terminal_env.execute(shell command, cwd=live cwd)
```

也就是说：

> **Hermes 的 file tools 跟 terminal env 绑定。如果当前 `TERMINAL_ENV=docker`，文件读写会通过 Docker 环境执行；如果是 SSH / Modal / Daytona，也会通过对应远程后端执行；如果是 local，就直接操作宿主文件系统。**

### 8.1 路径解析：围绕 task/session cwd

路径解析逻辑在 [file_tools.py:371-435](../../../submodules/hermes-agent/tools/file_tools.py#L371-L435)：

```text
_resolve_base_dir(task_id)
  1. live terminal cwd
  2. registered task/session cwd override
  3. absolute TERMINAL_CWD
  4. process cwd

_resolve_path_for_task(path, task_id)
  - absolute path: 原样 resolve
  - relative path: base_dir / path
  - container backend: 用 PurePosixPath 做 syntax normalize，不在宿主 deref
```

这个设计的背景是 workspace / worktree 可靠性：ACP / Desktop / TUI session 会把编辑器 cwd 注册成 task override，见 [session.py:123-136](../../../submodules/hermes-agent/acp_adapter/session.py#L123-L136)。这样 file tools 即使在 terminal env 还没跑过命令时，也知道当前 workspace 在哪里。

### 8.2 ShellFileOperations：同一套 file ops 跑在任意 backend

[ShellFileOperations](../../../submodules/hermes-agent/tools/file_operations.py#L764-L803) 的注释明确说：

```text
Works with ANY terminal backend that has execute(command, cwd).
This includes local, docker, singularity, ssh, modal, daytona.
```

它读写文件的方式不是 Python 直接 open，而是通过 backend shell：

- read：`cat` / `head` / shell command；
- write：`mkdir -p` + stdin 写入 temp file + same-directory `mv` 原子替换，见 [file_operations.py:1408-1423](../../../submodules/hermes-agent/tools/file_operations.py#L1408-L1423)；
- patch：读当前文件、fuzzy replace、再调用 write_file；
- lint / LSP diagnostics：写后做 delta check。

这就是为什么 file tools 能自然跟随 Docker / SSH / Modal / Daytona：它们只是对 `terminal_env.execute(...)` 的封装。

### 8.3 写入安全：敏感路径硬挡 + cross-profile soft guard

写文件前，Hermes 先做敏感路径检查，见 [file_tools.py:633-660](../../../submodules/hermes-agent/tools/file_tools.py#L633-L660)：

```text
_check_sensitive_path(path)
  - sensitive exact path
  - sensitive prefix
  - Hermes config file
```

底层 file safety 的 denylist 在 [file_safety.py:28-77](../../../submodules/hermes-agent/agent/file_safety.py#L28-L77)，包括：

```text
~/.ssh/authorized_keys
~/.ssh/id_rsa / id_ed25519 / config
~/.hermes/.env
~/.hermes/.anthropic_oauth.json
~/.netrc / .pgpass / .npmrc / .pypirc / .git-credentials
/etc/sudoers / /etc/passwd / /etc/shadow
~/.aws / ~/.gnupg / ~/.kube / ~/.docker / cloud CLI config 等目录
```

如果设置 `HERMES_WRITE_SAFE_ROOT`，还可以把写入限制到一组 safe roots，见 [file_safety.py:80-144](../../../submodules/hermes-agent/agent/file_safety.py#L80-L144)。

另外有 cross-profile soft guard，见 [file_tools.py:697-754](../../../submodules/hermes-agent/tools/file_tools.py#L697-L754)：

```text
写到其他 Hermes profile 的 skills/plugins/cron/memories
写到 sandbox mirror / container mirror 的 .hermes 状态
  -> 默认返回 warning/error
  -> 模型可在用户明确指示后用 cross_profile=True 覆盖
```

这里要分清：

| 类型 | 性质 |
|---|---|
| sensitive path | 硬挡，防止写安全敏感路径 / Hermes config。 |
| cross-profile guard | 软挡，防止个人 Agent 写错 profile / sandbox mirror；可显式 `cross_profile=True`。 |
| workspace boundary | Hermes 没有 Claw-Code 那种统一 “WorkspaceWrite 只能写 workspace 内” 的强模式；可用 safe root / ACP approval / backend isolation / sensitive denylist 组合约束。 |

## 9. ACP workspace：编辑器 cwd 进入 Hermes 工具体系

Hermes 的 ACP adapter 会把 editor / client 传来的 cwd 写入 session state，并注册到 terminal env override。

关键位置：

- `_register_task_cwd(...)`：[session.py:123-136](../../../submodules/hermes-agent/acp_adapter/session.py#L123-L136)
- `SessionManager.create_session(...)`：[session.py:210-229](../../../submodules/hermes-agent/acp_adapter/session.py#L210-L229)
- `SessionManager.fork_session(...)`：[session.py:253-280](../../../submodules/hermes-agent/acp_adapter/session.py#L253-L280)

流程是：

```text
ACP client 创建 / 恢复 session，传入 cwd
  -> SessionState.cwd = cwd
  -> register_task_env_overrides(session_id, {"cwd": cwd})
  -> terminal_tool / file_tools 用 raw session id 找到 cwd override
  -> relative path 解析到编辑器 workspace
```

这让 Hermes 在 IDE / ACP 场景下知道“当前工作区在哪里”。但注意：CWD override 本身不是隔离信号。`_resolve_container_task_id` 明确说 CWD-only override 会折叠到共享 `default` container，不会为每个 workspace 自动创建独立容器。

## 10. ACP edit approval：workspace policy 不是文件系统沙箱

ACP 编辑审批在 [edit_approval.py](../../../submodules/hermes-agent/acp_adapter/edit_approval.py)。它会把 `write_file` / `patch` 变成 diff proposal，并根据 policy 决定是否自动通过。

`should_auto_approve_edit(...)` 在 [edit_approval.py:200-230](../../../submodules/hermes-agent/acp_adapter/edit_approval.py#L200-L230)：

```text
AUTO_APPROVE_ASK       -> 都问
AUTO_APPROVE_SESSION   -> 本 session 自动过，但敏感路径仍问
AUTO_APPROVE_WORKSPACE -> cwd 或 tmp 下自动过，敏感路径仍问
```

这层和 sandbox 的关系是：

> **ACP workspace policy 是审批策略，不是底层文件系统 jail。它决定是否要向客户端展示 diff approval；真正路径读写仍由 file tools / terminal env / backend / sensitive denylist 执行。**

所以 Hermes 的 workspace 管理更偏“用户协作与审批语义”，而不是 OpenClaw 那种 `workspaceAccess=ro/rw/none` 直接重写工具菜单。

## 11. execute_code：临时 Python 小沙箱，不等于强 OS 沙箱

Hermes 的 `execute_code` 是另一个需要单独理解的 sandbox。它不是 terminal backend 本身，而是 programmatic tool calling：让模型写一段 Python 脚本，脚本通过生成的 `hermes_tools.py` RPC stub 调 Hermes 工具。

文件头 [code_execution_tool.py:1-27](../../../submodules/hermes-agent/tools/code_execution_tool.py#L1-L27) 把架构说得很清楚：

```text
Local backend:
  parent 生成 hermes_tools.py
  parent 开 Unix domain socket / TCP loopback RPC listener
  parent spawn child process 跑模型脚本
  tool calls 通过 RPC 回到 parent dispatch

Remote backend:
  parent 生成 hermes_tools.py 和 script.py
  ship 到 remote environment
  script 在 remote terminal backend 内执行
  tool calls 通过 request/response files 轮询代理
```

### 11.1 工具白名单

`execute_code` 允许脚本调用的工具只有 7 个，见 [code_execution_tool.py:59-69](../../../submodules/hermes-agent/tools/code_execution_tool.py#L59-L69)：

```text
web_search
web_extract
read_file
write_file
search_files
patch
terminal
```

并且会和当前 session enabled tools 取交集，见 [code_execution_tool.py:1192-1197](../../../submodules/hermes-agent/tools/code_execution_tool.py#L1192-L1197)。这意味着：

```text
execute_code 不能直接绕过 toolsets；
脚本只能通过 RPC 调有限工具；
中间工具结果不会全部进入模型上下文，只返回脚本 stdout。
```

### 11.2 execute_code 自己也要 guard

`execute_code` 会运行任意 Python，脚本内部可以 `subprocess` / `os.system`。这类行为不会天然经过 `terminal()` 的 dangerous command pattern，所以 Hermes 在执行脚本前做整体 guard，见 [code_execution_tool.py:1150-1167](../../../submodules/hermes-agent/tools/code_execution_tool.py#L1150-L1167)：

```text
check_execute_code_guard(code, env_type, has_host_access)
  -> 不通过就阻断，不 spawn child process
```

这点很关键：Hermes 明确知道 `execute_code` 是 bypass terminal pattern 的风险入口，因此给它单独加了 guard。

### 11.3 local execute_code：env scrub + tempdir / project mode

local path 会创建临时目录，写入 `hermes_tools.py` 和 `script.py`，见 [code_execution_tool.py:1199-1244](../../../submodules/hermes-agent/tools/code_execution_tool.py#L1199-L1244)。随后创建 RPC socket / TCP endpoint，见 [code_execution_tool.py:1246-1265](../../../submodules/hermes-agent/tools/code_execution_tool.py#L1246-L1265)。

child env 会 scrub，大量 secret 不传给脚本，见 [code_execution_tool.py:1280-1333](../../../submodules/hermes-agent/tools/code_execution_tool.py#L1280-L1333)。核心规则在 [_scrub_child_env](../../../submodules/hermes-agent/tools/code_execution_tool.py#L145-L206)：

- 明确 passthrough 的变量可以传；
- 名字里带 KEY / TOKEN / SECRET / PASSWORD / CREDENTIAL / DSN / WEBHOOK 等的变量默认挡；
- 只允许安全前缀、少量 operational `HERMES_*`、Windows OS essential vars；
- `HERMES_RPC_SOCKET` / `HERMES_RPC_TOKEN` / `TZ` / `HOME` 等由 parent 注入。

`execute_code.mode` 有两种，见 [code_execution_tool.py:1651-1673](../../../submodules/hermes-agent/tools/code_execution_tool.py#L1651-L1673)：

| mode | cwd / python | 含义 |
|---|---|---|
| `project` | session working directory + active venv python | 默认，更方便访问项目依赖和相对路径。 |
| `strict` | staging tempdir + Hermes 自己的 Python | 更可复现，和项目依赖隔离，但相对路径不指向项目。 |

对应 cwd 解析在 [code_execution_tool.py:1748-1767](../../../submodules/hermes-agent/tools/code_execution_tool.py#L1748-L1767)。

这里要谨慎表述：

> **local `execute_code` 是“受限工具 RPC + env scrub + timeout + stdout cap”的小沙箱，但不是 OS 级强隔离。Python 子进程仍以当前用户运行，尤其 project mode 下在 session workspace 中运行。**

### 11.4 remote execute_code：脚本在 remote backend 内执行

如果 `TERMINAL_ENV != local`，`execute_code` 走 remote path，见 [code_execution_tool.py:1179-1180](../../../submodules/hermes-agent/tools/code_execution_tool.py#L1179-L1180)。

remote path 会：

```text
_get_or_create_env(task_id)
mkdir remote sandbox_dir
ship hermes_tools.py + script.py
启动 file-based RPC polling thread
在 remote env 中 python3 script.py
清理 remote sandbox_dir
```

关键实现见 [code_execution_tool.py:913-1049](../../../submodules/hermes-agent/tools/code_execution_tool.py#L913-L1049)。这时 Python 脚本的隔离强度取决于底层 remote backend：Docker / Modal / Daytona / SSH / Singularity 各不相同。

## 12. 和 Claw-Code / OpenClaw / DeerFlow / OpenHands 的对比

| 维度 | Hermes Agent | Claw-Code | OpenClaw | DeerFlow | OpenHands |
|---|---|---|---|---|---|
| sandbox 主体 | Terminal Environment backend + execute_code 小沙箱 | 本地 workspace boundary + permission + unshare wrapper | Session SandboxContext + tool menu / fsBridge / exec target rewrite | SandboxProvider + tools acquire sandbox | 平台 sandbox 内跑 Agent Server |
| 默认执行位置 | `local`，宿主机当前用户 | 本机 CLI workspace | 产品 session runtime，可按 mode 进 sandbox | tool call 首次需要时 acquire provider | 远程 sandbox |
| workspace 边界 | `TERMINAL_CWD` / ACP cwd / backend cwd；无统一 WorkspaceWrite jail | `WorkspaceWrite` 内写 workspace，外部需 DangerFullAccess | `workspaceAccess=none/ro/rw` 影响工具面 | virtual paths / workspace mapping | sandbox workspace working_dir |
| 文件工具 | `ShellFileOperations` 通过当前 terminal env 执行 | Rust file_ops + PermissionEnforcer | fsBridge + sandbox context | sandbox file tools | FileEditor in sandbox Agent Server |
| 命令执行 | `terminal_tool` 多 backend | bash tool + permission / validation / unshare | exec target 可切 sandbox | sandbox bash tool | Terminal tool in Agent Server sandbox |
| 强隔离形态 | 可选 Docker / Singularity / Modal / Daytona；默认 local 不是强隔离 | 可选 Linux namespace wrapper，不是 Docker | Docker / SSH / custom sandbox backend | LocalSandbox / AioSandboxProvider | runtime sandbox 平台 |
| 长期状态 | 环境 snapshot、cwd、container reuse、remote sync、personal `.hermes` | 本地 session / workspace | session runtime / persistence | thread state / checkpoint | conversation / event log / sandbox lifecycle |
| 安全重心 | secret scrub、dangerous command approval、file sensitive path、toolsets、memory hygiene | permission mode + workspace boundary | tool policy + approval + sandbox context | middleware / guardrail / provider boundary | Action analyzer + confirmation + sandbox |

最核心的横向判断：

> **Hermes 的 sandbox 不是一个平台统一强制隔离层，而是长期个人 Agent 的执行后端选择器。它把 terminal、file tools、execute_code 都接到同一个可配置工作台上，并用 secret scrub、approval、sensitive path guard、toolset scope、RPC whitelist 等机制做个人助理式防护。**

## 13. 阶段性判断

Hermes Agent 的 Sandbox / Workspace 第一轮结论：

1. **默认 local，不等于强沙箱**
   - 默认 `TERMINAL_ENV=local`，命令在宿主机当前用户下执行；安全靠 approval / guard / env filtering / file safety。

2. **真正的执行抽象是 Terminal Environment**
   - `BaseEnvironment` 统一 local / Docker / Singularity / Modal / Daytona / SSH 的命令执行、cwd、snapshot、interrupt、timeout。

3. **file tools 跟随 terminal env**
   - `read_file` / `write_file` / `patch` 通过 `ShellFileOperations` 调 backend shell，不是简单本机 Python open；因此 Docker / SSH / Modal / Daytona 下会在对应环境里操作文件。

4. **Docker 是可选工作台，不是默认产品级 sandbox**
   - Docker backend 有 cap-drop、no-new-privileges、tmpfs、resource limit、可选 network none、credential / skills ro mount；但默认 network on，rootfs 可写，host cwd mount 是显式 opt-in。

5. **workspace 是 cwd / backend / approval 语义，不是统一 jail**
   - Hermes 有 `TERMINAL_CWD`、ACP cwd、safe root、sensitive path denylist、cross-profile guard、ACP edit approval，但没有 Claw-Code 那种全局 `WorkspaceWrite` 强边界。

6. **execute_code 是第二层小沙箱**
   - 它用临时脚本 + RPC stub + tool whitelist + env scrub + timeout / stdout cap；local 下不是 OS 强隔离，remote 下取决于 backend。

一句话收束：

> **Hermes 的 execution environment 是“长期个人助理工作台”而不是“平台强隔离房间”：它可以在本机、容器、云 sandbox、SSH 远端之间切换，并把文件、终端、Python 批处理统一接到这个工作台上；安全靠可见工具范围、危险命令审批、敏感路径防护、secret scrub 和长期状态卫生共同完成。**

## QA / 讨论记录

### Q: Hermes Agent 的 sandbox 到底是什么？

> **状态**: verified  
> **来源**: source-code / discussion

A: Hermes 的 sandbox 更准确地说是可配置 Terminal Environment：默认 `local` 直接在宿主机执行，也可以切到 Docker、Singularity、Modal、Daytona、SSH 等 backend。terminal、file tools 和 remote `execute_code` 都复用这套环境；local `execute_code` 另有临时 Python 子进程 + RPC 工具白名单的小沙箱。因此 Hermes 不是单一固定 Docker sandbox，而是长期个人 Agent 的可切换执行工作台。

### Q: Hermes 默认会不会把命令放进 Docker / VM？

> **状态**: verified  
> **来源**: source-code / discussion

A: 不会。默认 `TERMINAL_ENV=local`，`LocalEnvironment` 直接在宿主机当前用户权限下执行 bash。只有显式配置 `TERMINAL_ENV=docker/singularity/modal/daytona/ssh`，terminal 和 file tools 才会进入对应容器、云 sandbox 或远程机器。因此 Hermes 的默认安全模型不是“强隔离容器”，而是本地执行 + dangerous command approval + secret env scrub + file safety guard。

### Q: Hermes 的 file tools 是否总是在宿主文件系统上读写？

> **状态**: verified  
> **来源**: source-code / discussion

A: 不一定。Hermes 的 `read_file` / `write_file` / `patch` 通过 `ShellFileOperations` 调当前 terminal backend 的 `execute(...)`。如果当前 backend 是 local，它们操作宿主文件系统；如果是 Docker、SSH、Modal、Daytona 或 Singularity，它们会在对应环境里执行 shell file operations。相对路径会先按 live terminal cwd、registered task/session cwd、`TERMINAL_CWD` 等解析。

### Q: Hermes 的 Docker backend 和 OpenClaw / OpenHands sandbox 有什么区别？

> **状态**: verified  
> **来源**: source-code / discussion

A: Hermes Docker 是 terminal execution backend：主 Agent loop 仍在 Hermes 主进程里，工具调用时把 terminal / file 操作下发到 Docker 容器。OpenClaw sandbox 是 session runtime context，会重写工具菜单、exec target、fsBridge、browser bridge 和 policy；OpenHands sandbox 则更像远程开发工位，Agent Server 直接跑在 sandbox 内。Hermes Docker 更像个人助理的可选容器工作台，不是整个平台会话都搬进 sandbox。

### Q: Hermes 的 execute_code 是强沙箱吗？

> **状态**: draft  
> **来源**: source-code / discussion

A: 它是受限 Python 批处理小沙箱，但 local 模式下不是 OS 级强隔离。它会创建临时脚本和 `hermes_tools.py`，通过 UDS / TCP loopback RPC 调 parent 允许的 7 类工具，并 scrub child env、限制 timeout / stdout / tool call 次数；但 Python 子进程仍以当前用户运行，project mode 下还会在 session working directory 和 active venv 中运行。非 local backend 下，脚本运行在 remote terminal backend 中，隔离强度取决于 Docker / Modal / Daytona / SSH / Singularity 本身。

### Q: Hermes 有没有类似 Claw-Code WorkspaceWrite 的统一 workspace jail？

> **状态**: verified  
> **来源**: source-code / discussion

A: 第一轮看下来没有看到等价的统一 `WorkspaceWrite` jail。Hermes 通过 `TERMINAL_CWD` / ACP cwd 决定相对路径锚点，通过 sensitive path denylist、`HERMES_WRITE_SAFE_ROOT`、cross-profile soft guard、ACP edit approval 和 backend 隔离来约束写入。也就是说，Hermes 的 workspace 更像当前工作目录和审批语义，不是全局 permission mode 下的文件系统围栏。
