# OpenHands Sandbox / Workspace / Execution Environment 研读笔记

> **日期**: 2026-07-07 | **状态**: draft | **涉及版本**: `openhands@ef3323afd9676b5cf44ede15683fc56a570ea0d8` / `software-agent-sdk@0737c05e5d5218cdb15cadf1bc03d3e4f108a60b`

## 相关文档

- OpenHands Agent Loop：[agent-loop.md](agent-loop.md)
- OpenHands Tool System：[tool-system.md](tool-system.md)
- OpenHands Context Management：[context-management.md](context-management.md)
- OpenHands Permission / Security：[permission-security.md](permission-security.md)
- 横向 Permission / Security：[../../comparison/permission-security.md](../../comparison/permission-security.md)
- 横向 QA：[../../comparison/qa.md](../../comparison/qa.md#sandbox--workspace--execution-environment--沙箱与执行环境)

## 源码入口

| 模块 | 源码 | 说明 |
|---|---|---|
| App conversation model | [app_conversation_models.py](../../../submodules/openhands/openhands/app_server/app_conversation/app_conversation_models.py) | 控制面 conversation 信息，`AppConversationInfo` 显式保存 `sandbox_id`，把 conversation 绑定到 sandbox。 |
| App conversation start flow | [live_status_app_conversation_service.py](../../../submodules/openhands/openhands/app_server/app_conversation/live_status_app_conversation_service.py) | 控制面启动 conversation：等待 sandbox、解析 Agent Server URL、确定 `working_dir`、构造 `AsyncRemoteWorkspace`、POST 到 sandbox 内 Agent Server。 |
| App conversation router | [app_conversation_router.py](../../../submodules/openhands/openhands/app_server/app_conversation/app_conversation_router.py) | 控制面后续消息 / 文件访问 / workspace proxy：按 `sandbox_id` 找 RUNNING sandbox 和 exposed Agent Server URL。 |
| Docker sandbox service | [docker_sandbox_service.py](../../../submodules/openhands/openhands/app_server/sandbox/docker_sandbox_service.py) | 创建 Docker sandbox container：注入 session API key、端口映射、volume、`working_dir`、Agent Server image。 |
| Docker sandbox spec | [docker_sandbox_spec_service.py](../../../submodules/openhands/openhands/app_server/sandbox/docker_sandbox_spec_service.py) | 默认 sandbox spec：Agent Server image、`/workspace/project`、`/workspace/conversations`、`/workspace/bash_events`。 |
| Start conversation request | [request.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/conversation/request.py) | Agent Server 接收的 `StartConversationRequest`，核心字段 `workspace: LocalWorkspace`。 |
| Agent Server conversation router | [conversation_router.py](../../../submodules/software-agent-sdk/openhands-agent-server/openhands/agent_server/conversation_router.py) | Agent Server `/api/conversations` 入口，接收 start request 并启动 SDK conversation。 |
| Agent Server conversation service | [conversation_service.py](../../../submodules/software-agent-sdk/openhands-agent-server/openhands/agent_server/conversation_service.py) | 创建 `StoredConversation`、可选 `worktree=True` 时建立 conversation 级 git worktree。 |
| SDK workspace base | [base.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/workspace/base.py) | `BaseWorkspace` 抽象：`working_dir`、`execute_command`、file upload / download、git changes / diff、pause / resume。 |
| SDK LocalWorkspace | [local.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/workspace/local.py) | Agent Server 视角的本地 workspace：在当前进程 / 容器文件系统执行命令和复制文件。 |
| SDK RemoteWorkspace | [base.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/workspace/remote/base.py) | App Server / 外部客户端视角的远程 workspace：通过 Agent Server API 执行命令、传输文件。 |
| LocalConversation | [local_conversation.py](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/conversation/impl/local_conversation.py) | SDK conversation 初始化时保存 `ConversationState.workspace`，后续工具从 state 读取 working_dir。 |
| TerminalTool | [definition.py](../../../submodules/software-agent-sdk/openhands-tools/openhands/tools/terminal/definition.py) | `TerminalTool.create(...)` 从 `conv_state.workspace.working_dir` 创建 `TerminalExecutor`。 |
| TerminalExecutor | [impl.py](../../../submodules/software-agent-sdk/openhands-tools/openhands/tools/terminal/impl.py) | 在 `working_dir` 下创建 tmux / subprocess / powershell session，承载真实命令执行。 |
| FileEditorTool | [definition.py](../../../submodules/software-agent-sdk/openhands-tools/openhands/tools/file_editor/definition.py) | `FileEditorTool.create(...)` 从 `conv_state.workspace.working_dir` 创建 `FileEditorExecutor`，并把 current working directory 写入工具说明。 |
| FileEditorExecutor | [impl.py](../../../submodules/software-agent-sdk/openhands-tools/openhands/tools/file_editor/impl.py) | 使用 `FileEditor(workspace_root=...)` 执行文件读写。 |
| FileEditor path validation | [editor.py](../../../submodules/software-agent-sdk/openhands-tools/openhands/tools/file_editor/editor.py) | 校验 absolute path、create / view / edit 条件；第一轮已读代码未看到强制 path containment，硬边界主要依赖外层 sandbox / container。 |

## 核心结论

OpenHands 的 sandbox 不是一个附属配置，而是平台化 SWE Agent 的 **远程隔离工作间**。

它的核心链路是：

```text
用户 / UI / API
  -> OpenHands App Server（控制面）
     -> 创建 / 获取 sandbox
     -> 找到 sandbox 暴露的 Agent Server URL
     -> 确定 sandbox 内 working_dir
     -> 用 session_api_key 调 Agent Server

  -> Agent Server（运行在 sandbox 内）
     -> 创建 SDK LocalConversation
     -> ConversationState.workspace = LocalWorkspace(working_dir)
     -> Agent loop 产生 ActionEvent
     -> Terminal / FileEditor / grep / glob 等工具读取 workspace.working_dir
     -> 在 sandbox 文件系统 / 进程环境中执行
```

最重要的一句话：

> **OpenHands 的 App Server 是控制室，sandbox 里跑的 Agent Server 才是施工队；Terminal / FileEditor 的 working_dir 来自 conversation 的 workspace，通常是 sandbox 内的 `/workspace/project` 或其分组子目录。**

通俗比喻：

> **OpenHands 像远程开发园区。App Server 是前台 / 调度中心，sandbox 是分配给任务的隔离工位，Agent Server 是工位里的施工队长，workspace 是桌面上的项目目录，Terminal / FileEditor 是施工工具。**

## 1. Sandbox 的功能清单

如果只问“OpenHands 的 sandbox 有哪些功能、起什么作用”，可以浓缩成十个：

| 功能 | 作用 |
|---|---|
| 隔离执行环境 | Agent 的命令、文件操作、浏览器 / VSCode / VNC 等能力主要发生在 sandbox runtime 内，降低影响 App Server 或宿主控制面的风险。 |
| 提供 workspace | 给 Agent 一个明确项目目录，默认 `/workspace/project`，也可以按 conversation grouping 变成分组子目录。 |
| 运行 Agent Server | sandbox 里通常运行 Agent Server；App Server 不直接执行工具，而是把请求转发给 sandbox 内 Agent Server。 |
| 承载工具执行 | Terminal / FileEditor / grep / glob / TaskTool 等工具最终从 `ConversationState.workspace.working_dir` 取路径并在 sandbox 内执行。 |
| 保存 conversation / event / bash 记录 | 默认有 `/workspace/conversations` 和 `/workspace/bash_events`，用于保存会话状态、事件、bash 执行记录。 |
| 管理生命周期 | sandbox 有 STARTING / RUNNING / PAUSED / ERROR / MISSING 等状态，可启动、暂停、恢复、删除。 |
| 隔离或分组多个 conversation | 控制面保存 `conversation_id -> sandbox_id`，并可通过 grouping strategy 给不同 conversation 分配不同 workspace path。 |
| 用 session API key 保护访问 | App Server 调 sandbox 内 Agent Server 时使用 `X-Session-API-Key`，避免任意调用。 |
| 支持远程文件访问 / 归档 | App Server 可通过 RemoteWorkspace / Agent Server 读取、下载、归档 sandbox workspace。 |
| 支持远程开发体验 | sandbox 可暴露 Agent Server API、workspace static files、VSCode server、VNC / browser 等服务。 |

最短理解：

> **OpenHands sandbox 的作用，就是把 Agent 从“聊天模型”变成“能在隔离远程开发环境里真实干活的工程 Agent”。**

更口语：

> **它就是给 Agent 准备的一间安全施工房：代码放里面，命令在里面跑，文件在里面改，日志在里面记，出了问题也尽量关在这间房里。**

## 2. 默认 sandbox：Agent Server image + `/workspace/project`

Docker sandbox 的默认 spec 在 [docker_sandbox_spec_service.py](../../../submodules/openhands/openhands/app_server/sandbox/docker_sandbox_spec_service.py)：

```text
SandboxSpecInfo(
  id=get_agent_server_image(),
  command=["--port", "8000"],
  initial_env={
    OH_CONVERSATIONS_PATH=/workspace/conversations,
    OH_BASH_EVENTS_DIR=/workspace/bash_events,
    ...
  },
  working_dir=/workspace/project,
)
```

这说明默认 sandbox 不是空容器，而是：

```text
/workspace/project        # Agent 默认项目工作目录
/workspace/conversations  # conversation / event 持久化目录
/workspace/bash_events    # bash event 记录目录
Agent Server              # 通过 --port 8000 启动
```

Docker sandbox 创建在 [docker_sandbox_service.py](../../../submodules/openhands/openhands/app_server/sandbox/docker_sandbox_service.py) 中，主流程包括：

```text
start_sandbox(...)
  -> resolve_sandbox_spec(...)
  -> generate sandbox_id
  -> generate session_api_key
  -> env_vars[SESSION_API_KEY] = session_api_key
  -> env_vars[WEBHOOK_CALLBACK] = App Server webhook URL
  -> ports / volumes / labels
  -> docker_client.containers.run(
       image=sandbox_spec.id,
       command=sandbox_spec.command,
       environment=env_vars,
       ports=port_mappings,
       volumes=volumes,
       working_dir=sandbox_spec.working_dir,
       labels={"sandbox_spec_id": sandbox_spec.id},
       detach=True,
       init=True,
     )
```

所以它的硬边界主要来自：

```text
Docker container
  + working_dir
  + volumes
  + exposed ports
  + session_api_key
```

## 3. AppConversation 显式绑定 sandbox

控制面 conversation model 在 [app_conversation_models.py](../../../submodules/openhands/openhands/app_server/app_conversation/app_conversation_models.py) 中：

```text
AppConversationInfo:
  id
  created_by_user_id
  sandbox_id
  selected_repository
  selected_branch
  git_provider
  tags
```

关键是：

```text
conversation_id -> sandbox_id
```

这说明 OpenHands 的 conversation 不是纯聊天记录，而是“有工位的会话”：

> **一个 conversation 会绑定一个 sandbox，后续发消息、读文件、归档 workspace 都要先通过 sandbox_id 找到对应 runtime。**

## 4. App Server 启动 conversation：先找工位，再发工单

控制面启动主线在 [live_status_app_conversation_service.py](../../../submodules/openhands/openhands/app_server/app_conversation/live_status_app_conversation_service.py)。简化流程：

```text
_start_app_conversation(request)
  -> _wait_for_sandbox_start(task)
  -> sandbox = sandbox_service.get_sandbox(sandbox_id)
  -> agent_server_url = _get_agent_server_url(sandbox)
  -> _verify_agent_server_version(agent_server_url)
  -> _seed_sandbox_profiles(...)
  -> sandbox_spec = sandbox_spec_service.get_sandbox_spec(...)
  -> conversation_id = request.conversation_id or uuid4()

  -> working_dir = grouped_workspace_dir(
       sandbox_spec.working_dir,
       sandbox_grouping_strategy,
       conversation_id.hex,
     )

  -> remote_workspace = AsyncRemoteWorkspace(
       host=agent_server_url,
       api_key=sandbox.session_api_key,
       working_dir=working_dir,
     )

  -> run_setup_scripts(..., remote_workspace, ...)

  -> start_conversation_request =
       _build_start_conversation_request_for_user(..., working_dir, ...)

  -> POST {agent_server_url}/api/conversations
       json=start_conversation_request
       headers X-Session-API-Key=sandbox.session_api_key

  -> save AppConversationInfo(
       id=info.id,
       sandbox_id=sandbox.id,
       tags[archiveworkspacepath] = working_dir,
       ...
     )
```

这里两个变量最关键：

| 变量 | 作用 |
|---|---|
| `agent_server_url` | App Server 要把请求发到哪个 sandbox 内 Agent Server。 |
| `working_dir` | Agent 在 sandbox 里的项目工作目录。 |

并且 OpenHands 会把最终 resolved workspace path 写入 tag：

```text
tags[ARCHIVE_WORKSPACE_PATH_TAG_KEY] = working_dir
```

这样删除 / 归档时不需要重新按当前配置推导，而是记住“当初真正用的是哪个目录”。

## 5. App Server 后续消息只是代理，不自己执行工具

后续发消息入口在 [app_conversation_router.py](../../../submodules/openhands/openhands/app_server/app_conversation/app_conversation_router.py)：

```text
send_message_to_conversation(conversation_id, request)
  -> conversation = app_conversation_service.get_app_conversation(conversation_id)
  -> sandbox = sandbox_service.get_sandbox(conversation.sandbox_id)
  -> 必须 sandbox.status == RUNNING
  -> 从 sandbox.exposed_urls 找 AGENT_SERVER URL
  -> POST {agent_server_url}/api/conversations/{conversation_id}/events
       headers X-Session-API-Key: sandbox.session_api_key
       json role/content/run
```

这说明 App Server 本身不执行工具。它只是：

```text
检查 sandbox 状态
找到 Agent Server URL
带 session key 把请求送进去
```

通俗说：

> **前台不进工位干活；前台只确认工位还开着，然后把新工单送到工位里的施工队长。**

## 6. 为什么 Agent Server 里是 LocalWorkspace？

Agent Server 接收的 [StartConversationRequest](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/conversation/request.py) 核心字段是：

```text
StartConversationRequest:
  workspace: LocalWorkspace
  worktree: bool = False
  conversation_id
  confirmation_policy
  security_analyzer
  initial_message
  ...
```

这看起来像矛盾：控制面明明是远程 sandbox，为什么 start request 是 `LocalWorkspace`？

答案是视角不同：

```text
App Server 视角：
  sandbox 是远程环境，所以用 AsyncRemoteWorkspace / RemoteWorkspace 访问。

Agent Server 视角：
  自己已经跑在 sandbox 容器里，/workspace/project 就是本地路径，
  所以 conversation 用 LocalWorkspace。
```

比喻：

```text
园区前台看工位：远程房间。
工位里的施工队长看项目目录：本地桌面。
```

## 7. Workspace 抽象：工具执行的统一边界

SDK 的 [BaseWorkspace](../../../submodules/software-agent-sdk/openhands-sdk/openhands/sdk/workspace/base.py) 抽象包括：

```text
working_dir
execute_command(command, cwd, timeout)
file_upload(source_path, destination_path)
file_download(source_path, destination_path)
git_changes(path)
git_diff(path)
pause()
resume()
```

它的注释直接说明：workspace 提供 agent 执行命令、读写文件和执行其他操作的 sandboxed environment。

两个重要实现：

| 实现 | 视角 | 功能 |
|---|---|---|
| `LocalWorkspace` | Agent Server / SDK conversation 视角 | 在当前进程所在文件系统执行命令和文件 copy；如果 Agent Server 跑在 container 内，这个“local”就是 sandbox 内。 |
| `RemoteWorkspace` / `AsyncRemoteWorkspace` | App Server / 外部客户端视角 | 通过远程 Agent Server API 执行命令、上传 / 下载文件、读取 git diff 等。 |

一句话：

> **同一个 sandbox workspace，在 App Server 看来是 remote，在 Agent Server 看来是 local。**

## 8. TerminalTool：真实命令在 sandbox 的 working_dir 里跑

Terminal 工具创建在 [terminal/definition.py](../../../submodules/software-agent-sdk/openhands-tools/openhands/tools/terminal/definition.py)：

```text
TerminalTool.create(conv_state):
  working_dir = conv_state.workspace.working_dir
  if not os.path.isdir(working_dir):
    raise ValueError(...)
  executor = TerminalExecutor(working_dir=working_dir, ...)
```

TerminalExecutor 在 [terminal/impl.py](../../../submodules/software-agent-sdk/openhands-tools/openhands/tools/terminal/impl.py) 中：

```text
TerminalExecutor(working_dir):
  self._working_dir = working_dir

  if tmux available:
    TmuxPanePool(working_dir, ...)
  else:
    create_terminal_session(work_dir=working_dir, ...)
```

所以 Terminal 的执行位置是：

> **Agent Server 所在环境里的 `conv_state.workspace.working_dir`。在平台 sandbox 模式下，这就是 sandbox 容器内的 workspace 目录。**

## 9. FileEditorTool：文件编辑以 workspace 为引导，硬边界靠 sandbox

FileEditor 工具创建在 [file_editor/definition.py](../../../submodules/software-agent-sdk/openhands-tools/openhands/tools/file_editor/definition.py)：

```text
FileEditorTool.create(conv_state):
  executor = FileEditorExecutor(
    workspace_root=conv_state.workspace.working_dir
  )

  description += "Your current working directory is: {working_dir}"
  description += "start with this directory instead of the root filesystem"
```

FileEditorExecutor 在 [file_editor/impl.py](../../../submodules/software-agent-sdk/openhands-tools/openhands/tools/file_editor/impl.py)：

```text
FileEditorExecutor(workspace_root):
  self.editor = FileEditor(workspace_root=workspace_root)
```

FileEditor 初始化在 [file_editor/editor.py](../../../submodules/software-agent-sdk/openhands-tools/openhands/tools/file_editor/editor.py)：

```text
FileEditor(workspace_root):
  self._cwd = absolute workspace_root
```

但第一轮已读代码里，path validation 主要检查：

```text
path 必须是 absolute path
create 不能覆盖已有文件
非 create 的 path 必须存在
非 view 不能操作 directory
```

未看到强制要求 path 必须在 `workspace_root` 内。

所以要谨慎理解：

> **FileEditor 的默认工作引导来自 workspace，但硬隔离主要依赖外层 sandbox / container 边界；FileEditor 自身第一轮已读路径校验更偏 absolute path 和命令条件检查，不应误写成它一定强制所有 path containment。**

这点解释了 OpenHands 为什么需要 sandbox：如果工具能访问容器内绝对路径，真正防止影响宿主机的是 container / volume 边界。

## 10. Conversation 级 worktree：可选代码目录隔离

Agent Server 还有可选 `worktree=True` 机制，在 [conversation_service.py](../../../submodules/software-agent-sdk/openhands-agent-server/openhands/agent_server/conversation_service.py)：

```text
_prepare_request_workspace(request, conversation_id):
  if not request.worktree:
    return request

  worktree = _create_conversation_worktree(request.workspace, conversation_id)
  if worktree is None:
    return request

  new_workspace = LocalWorkspace(working_dir=workspace_dir)
  agent = _append_worktree_guidance(...)
  return request.model_copy(update={"workspace": new_workspace, "agent": agent})
```

`_create_conversation_worktree(...)` 会：

```text
source_workspace = Path(workspace.working_dir)
validate_git_repository(source_workspace)
repo_root = git rev-parse --show-toplevel
conversation_worktree_root = /tmp/conversation-worktrees/<conversation_id>
branch = openhands/<conversation_id>
git worktree add -b branch worktree_root start_point
workspace_dir = worktree_root / relative_workspace
return LocalWorkspace(working_dir=workspace_dir)
```

这说明 OpenHands 可能有两层隔离：

```text
Docker sandbox：进程 / 文件系统 / runtime 隔离
Git worktree：同一个 sandbox 内的 conversation 级代码目录隔离
```

## 11. Sandbox 与 Permission / Security 的关系

在 Permission / Security 专题里，OpenHands 的中心是：

```text
ActionEvent -> SecurityAnalyzer -> ConfirmationPolicy -> WAITING_FOR_CONFIRMATION / ObservationEvent
```

Sandbox 这一层回答的是另一个问题：

```text
Action 被允许之后，到底在哪里执行？
它最多能影响哪个文件系统 / workspace / container？
```

两者关系是：

```text
Permission / Security = 动作前软决策
  -> 这个 Action 风险多高？要不要确认？用户拒绝怎么反馈？

Sandbox / Workspace = 动作执行硬边界
  -> 即使允许执行，也在 sandbox workspace / container 内执行。
```

合起来就是：

```text
模型动作
  -> ActionEvent 风险安检
  -> approved
  -> ToolDefinition.executor
  -> Terminal / FileEditor
  -> sandbox workspace
```

所以 OpenHands 的完整安全感来自两层叠加：

> **先把动作事件化做风险治理，再把执行落到 sandbox / workspace 里控制影响半径。**

## 12. QA / 讨论记录

### Q: OpenHands 的 sandbox 到底是什么？

> **状态**: verified
> **来源**: source-code / discussion

A: 它是给 Agent 准备的远程隔离工作间。App Server 负责创建 / 管理 sandbox 并把请求送到 sandbox 内的 Agent Server；Agent Server 在 sandbox 内启动 SDK conversation；Terminal / FileEditor 等工具在 `ConversationState.workspace.working_dir` 对应的 sandbox 文件系统和进程环境里执行。

### Q: OpenHands sandbox 的功能有哪些？

> **状态**: verified
> **来源**: source-code / discussion

A: 主要包括：隔离执行环境、提供 workspace、运行 Agent Server、承载 Terminal / FileEditor 等工具执行、保存 conversation / event / bash 记录、管理 STARTING / RUNNING / PAUSED / ERROR / MISSING 生命周期、通过 `conversation_id -> sandbox_id` 隔离或分组任务、用 session API key 保护访问、支持远程文件访问 / workspace 归档，以及暴露 VSCode / VNC / browser / Agent Server API 等远程开发能力。

### Q: App Server 会直接执行 Terminal / FileEditor 吗？

> **状态**: verified
> **来源**: source-code / discussion

A: 不会。App Server 是控制面，它检查 sandbox 状态、找到 sandbox exposed Agent Server URL，并用 `X-Session-API-Key` 把 start / message / file 请求发给 sandbox 内 Agent Server。真正的 Terminal / FileEditor 执行发生在 Agent Server 所在环境，也就是 sandbox 内。

### Q: 为什么 StartConversationRequest 里是 LocalWorkspace，而 App Server 又用 RemoteWorkspace？

> **状态**: verified
> **来源**: source-code / discussion

A: 因为视角不同。App Server 在 sandbox 外部，所以通过 `AsyncRemoteWorkspace(host=agent_server_url, api_key=..., working_dir=...)` 访问 sandbox。Agent Server 运行在 sandbox 内部，所以 `/workspace/project` 对它来说就是本地路径，`StartConversationRequest.workspace` 使用 `LocalWorkspace(working_dir=...)`。

### Q: FileEditor 是否强制只能编辑 workspace_root 内文件？

> **状态**: to-verify
> **来源**: source-code / discussion

A: 第一轮已读代码确认 FileEditorTool 用 `workspace_root=conv_state.workspace.working_dir` 初始化，并在工具说明中引导模型从 current working directory 开始；但 [editor.py](../../../submodules/software-agent-sdk/openhands-tools/openhands/tools/file_editor/editor.py) 的 `validate_path(...)` 主要检查 path 是否为 absolute、create / view / edit 条件，暂未看到强制 path 必须位于 workspace_root 内的 containment 检查。因此当前结论应写成：FileEditor 的工作引导来自 workspace，硬隔离主要依赖 sandbox / container / volume 边界；后续可继续核验是否还有上层 hook、policy 或部署配置限制绝对路径访问。
