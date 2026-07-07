# DeerFlow Sandbox / Workspace / Execution Environment 研读笔记

> **日期**: 2026-07-07 | **状态**: draft | **涉及版本**: `deer-flow@0808738c5876b04b4aa8e9aca7379a0a62b4232d`

## 相关文档

- DeerFlow Agent Loop：[agent-loop.md](agent-loop.md)
- DeerFlow Tool System：[tool-system.md](tool-system.md)
- DeerFlow Context Management：[context-management.md](context-management.md)
- DeerFlow Permission / Security：[permission-security.md](permission-security.md)
- 横向 Permission / Security：[../../comparison/permission-security.md](../../comparison/permission-security.md)
- 横向 QA：[../../comparison/qa.md](../../comparison/qa.md#sandbox--workspace--execution-environment--沙箱与执行环境)

## 源码入口

| 模块 | 源码 | 说明 |
|---|---|---|
| Agent factory | [factory.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/factory.py) | `build_middlewares(...)` 把 `SandboxMiddleware(lazy_init=True)` 装进 LangGraph agent middleware 链。 |
| Sandbox middleware | [middleware.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/sandbox/middleware.py) | middleware 级 sandbox lifecycle，默认 lazy init，只在工具调用阶段确保 sandbox 可用。 |
| Sandbox abstraction | [sandbox.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/sandbox/sandbox.py) | `Sandbox` 抽象接口：command、file、list、glob、grep、download、update。 |
| Sandbox provider | [sandbox_provider.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/sandbox/sandbox_provider.py) | provider 抽象、全局 singleton、按配置选择 Local / AIO / E2B / BoxLite 等 provider。 |
| Sandbox config | [sandbox_config.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/config/sandbox_config.py) | `SandboxConfig`：provider 类型、host bash 开关、image、replicas、idle timeout、mounts、env。 |
| Local sandbox | [local_sandbox.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/sandbox/local/local_sandbox.py) | 本地 path-mapping sandbox，实现虚拟路径映射、文件读写、命令执行和 escape 防护。 |
| Local provider | [local_sandbox_provider.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/sandbox/local/local_sandbox_provider.py) | 按 `(user_id, thread_id)` 缓存 LocalSandbox，建立 `/mnt/user-data/...` 等虚拟路径映射。 |
| Sandbox tools | [tools.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/sandbox/tools.py) | `ensure_sandbox_initialized(...)` 和 bash / file / grep / glob 等 sandbox tool 的真正入口。 |
| Sandbox security | [security.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/sandbox/security.py) | 判断 LocalSandbox host bash 是否允许，默认禁用 host bash 的安全提示。 |
| AIO provider | [aio_sandbox_provider.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/community/aio_sandbox/aio_sandbox_provider.py) | Docker / K8s backend、warm pool、replicas、idle timeout、orphan reconciliation。 |

## 核心结论

DeerFlow 的 sandbox 可以先用一句话理解：

> **DeerFlow 的 sandbox 是工具执行工作台，不是 OpenHands 那种“每个任务一个远程开发房间”。**

它服务的是 LangGraph agent runtime 里的工具调用：模型决定调用 bash / file / grep / glob 等工具时，工具先通过 `ensure_sandbox_initialized(runtime)` 找到或创建当前 thread 的 sandbox，然后在这个 workspace abstraction 里执行动作。

最关键的架构点是：

> **DeerFlow 的 sandbox 默认是 lazy init：Agent 进场不立刻开工位，只有第一次真正调用需要 sandbox 的工具时，`SandboxMiddleware` / `ensure_sandbox_initialized(...)` 才获取 sandbox，并把 `sandbox_id` 写回 `ThreadState`。**

简化主线：

```text
create_agent(...)
  -> build_middlewares(...)
  -> SandboxMiddleware(lazy_init=True)
  -> LangGraph agent runtime
  -> model requests tool call
  -> sandbox tool calls ensure_sandbox_initialized(runtime)
  -> SandboxProvider.acquire(user_id, thread_id)
  -> sandbox_id persisted in runtime.state["sandbox"]
  -> tool executes command / file operation inside sandbox abstraction
```

如果 OpenHands 像“远程开发园区”，DeerFlow 更像“工作流工厂”：

> **OpenHands 是先给 conversation 分配远程工位，再让工位里的 Agent Server 干活；DeerFlow 是先让 LangGraph 工作流跑起来，等某个工具真的要动手时，再给当前 thread 领一个工具工作台。**

## DeerFlow sandbox 的功能清单

如果只问“DeerFlow sandbox 有什么功能、起什么作用”，可以浓缩成这些：

| 功能 | 作用 |
|---|---|
| 统一工具执行环境 | 给 bash / file / grep / glob / download 等工具一个统一执行入口，而不是每个工具自己管理路径和 runtime。 |
| 保存 thread 级 workspace | 以 `user_id + thread_id` 作为隔离维度，让同一 thread 的工具操作共享同一个工作目录 / sandbox。 |
| 延迟获取资源 | 默认 lazy init，只有第一次工具调用才 acquire sandbox，避免纯对话、澄清、提前终止的 run 白白创建容器或目录。 |
| 虚拟路径映射 | LocalSandbox 把 `/mnt/user-data/workspace`、uploads、outputs、ACP workspace、skills 等虚拟路径映射到宿主本地目录。 |
| 路径逃逸防护 | LocalSandbox 解析路径后用 `relative_to(local_root)` 防止 `../` 逃出映射根目录。 |
| 命令执行约束 | LocalSandbox 的 host bash 默认禁用，只有显式 `allow_host_bash=true` 才允许在宿主执行 bash。 |
| 文件操作封装 | read / write / list / glob / grep / download / update 都走 sandbox abstraction，便于替换 provider。 |
| 生产容器化执行 | AIO provider 可用 Docker / K8s backend、warm pool、replicas、idle timeout 等机制承载更强隔离。 |
| 状态持久化 | `sandbox_id` 写入 LangGraph state，后续工具调用可以复用同一个 sandbox，而不是每次新建。 |
| 和 middleware 治理协同 | Sandbox 不是孤立系统，它和 ToolErrorHandling、Guardrail、LoopDetection、ReadBeforeWrite、RunManager 等共同构成工具治理链。 |

最短理解：

> **DeerFlow sandbox 的作用，是把 LangGraph 工具调用变成“在当前 thread 的受控工作台里执行动作”。**

## SandboxMiddleware：默认 lazy init 是关键

[factory.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/agents/factory.py) 装配 agent middleware 时，会加入：

```text
SandboxMiddleware(lazy_init=True)
```

这点非常关键。很多人一听 sandbox，直觉会以为：

```text
Agent 开始运行
  -> 立刻创建 sandbox
  -> 后续工具都在里面跑
```

但 DeerFlow 的默认思路更像：

```text
Agent 开始运行
  -> 先不创建 sandbox
  -> 模型可能只是聊天 / 澄清 / 规划
  -> 直到第一次工具调用需要执行环境
  -> 再 acquire sandbox
```

为什么这很重要？

1. **省资源**：不是每个 run 都一定会执行工具；有些 run 可能直接回答、要求澄清，或者被 guardrail / user interrupt 截断。
2. **适合长任务平台**：Gateway 可能同时管理很多 thread / run，如果每个 run 一开始就创建容器，会制造很高的冷启动和资源压力。
3. **和 LangGraph state 对齐**：sandbox 被真正用到后，`sandbox_id` 写入 state，后续工具调用继续复用。
4. **让 sandbox 成为工具层资源**：它不是 agent loop 的入口前置条件，而是 tool execution 的按需依赖。

可以记成：

> **DeerFlow 不是“先开房再聊天”，而是“聊到要动手时才领工具台”。**

## ensure_sandbox_initialized：工具侧的真正入口

[sandbox/tools.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/sandbox/tools.py) 里有 `ensure_sandbox_initialized(runtime)`，这是 sandbox tool 的关键入口。

它的核心职责是：

```text
检查 runtime.state["sandbox"] 有没有 sandbox_id
  -> 有：通过 provider.get(sandbox_id) 取回 sandbox
  -> 没有：通过 provider.acquire(...) 创建 / 获取 sandbox
  -> 把 sandbox_id 写入 state update
  -> 返回 sandbox 对象给具体工具使用
```

这说明 DeerFlow 的 sandbox lifecycle 有两个入口互相配合：

| 入口 | 作用 |
|---|---|
| `SandboxMiddleware(lazy_init=True)` | 把 sandbox 能力挂入 agent middleware 链，并在工具调用生命周期参与初始化 / 状态更新。 |
| `ensure_sandbox_initialized(runtime)` | 具体 sandbox tool 执行前的保险：没有 sandbox 就按需获取，已有 sandbox 就复用。 |

精髓：

> **lazy init 不是“没人管 sandbox”，而是把创建时机推迟到第一只真正要执行的工具手上。**

## sandbox_id 写入 ThreadState：同一 thread 复用同一工作台

[middleware.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/sandbox/middleware.py) 会把 acquired sandbox 的 `sandbox_id` 放进 LangGraph state update，类似：

```text
Command(update={"sandbox": {"sandbox_id": sandbox.id}})
```

因此 DeerFlow 不是每个工具调用都创建新环境，而是：

```text
第一次 sandbox tool call
  -> acquire sandbox
  -> state.sandbox.sandbox_id = xxx

后续 sandbox tool call
  -> 从 state 读 sandbox_id
  -> provider.get(xxx)
  -> 复用同一 sandbox
```

这和 DeerFlow 的 thread / checkpoint / state 模型是一体的：sandbox 是当前 thread 的执行环境资源，`sandbox_id` 是这份资源在 state 里的引用。

## SandboxProvider：可替换的执行环境后端

[sandbox_provider.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/sandbox/sandbox_provider.py) 定义 provider 抽象：

```text
acquire(user_id, thread_id, ...)
get(sandbox_id)
release(sandbox_id)
```

同时提供全局 provider singleton。具体使用哪个 provider 由 [sandbox_config.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/config/sandbox_config.py) 的配置决定。

这种设计把“工具想要执行动作”与“动作到底在哪里执行”解耦：

```text
sandbox tool
  -> Sandbox abstraction
  -> SandboxProvider
  -> LocalSandbox / AioSandbox / E2B / BoxLite / ...
```

所以 DeerFlow 的 sandbox 不等于某一个固定实现。它是一层 provider 化的 execution environment abstraction。

## LocalSandbox：本地 path-mapping，不等于强容器隔离

LocalSandbox 是第一轮研读里最容易误解的部分。

[local_sandbox_provider.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/sandbox/local/local_sandbox_provider.py) 会为 thread 构造虚拟路径映射，典型包括：

```text
/mnt/user-data/workspace
/mnt/user-data/uploads
/mnt/user-data/outputs
/mnt/acp-workspace
/mnt/skills/custom
```

[local_sandbox.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/sandbox/local/local_sandbox.py) 再把这些虚拟路径解析到宿主本地目录。

所以 LocalSandbox 更像：

```text
虚拟路径命名空间
  + 本地目录映射
  + 路径逃逸检查
  + 文件 / 命令工具封装
```

而不是：

```text
强隔离容器
  + 独立进程 namespace
  + 独立网络 / 文件系统边界
```

因此文档里要谨慎表达：

> **LocalSandbox 是本地执行的 path-mapping sandbox；它提供 workspace 组织和路径边界检查，但不能把它误写成 Docker / VM 级安全隔离。**

## 路径逃逸防护：relative_to(local_root)

LocalSandbox 的关键安全点是路径解析。

它会把虚拟路径映射到本地路径，然后检查解析后的路径是否仍然位于 mapping root 下。可以简化成：

```text
virtual_path -> local_path.resolve()
local_path.relative_to(local_root)
```

如果 `../` 或 symlink 等方式导致路径逃出映射根目录，就拒绝。

这解决的是：

```text
/mnt/user-data/workspace/../../etc/passwd
```

不能逃出 workspace mapping root 去读写宿主敏感路径。

但它不等于“命令完全安全”。如果 host bash 被允许，命令本身仍然在宿主进程环境执行，所以 DeerFlow 默认关闭 LocalSandbox 的 host bash。

## host bash 默认禁用：LocalSandbox 的重要安全边界

[security.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/sandbox/security.py) 定义了 LocalSandbox host bash 的安全判断。

核心结论：

```text
LocalSandboxProvider + allow_host_bash != true
  -> bash disabled
```

也就是说，在 LocalSandbox provider 下，DeerFlow 默认不允许模型直接在宿主执行 bash。只有配置显式打开 `allow_host_bash=true` 时，bash tool 才能执行。

这点非常重要，因为 LocalSandbox 本身不是容器隔离；如果默认允许 host bash，它的风险会明显高于纯文件 path-mapping。

可以记成：

> **LocalSandbox 管路径，host bash 管风险；默认禁用 host bash，是为了避免把本地 path-mapping 当成强隔离沙箱使用。**

## 文件工具：workspace 里的读写检索工作台

[sandbox/tools.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/sandbox/tools.py) 里的 read / write / list / glob / grep 等工具都围绕 sandbox abstraction 工作。

典型逻辑是：

```text
tool called
  -> ensure_sandbox_initialized(runtime)
  -> validate / normalize path
  -> sandbox.read_file / write_file / glob / grep / list_dir
  -> return ToolMessage / structured result
```

这带来几个效果：

1. 工具不需要知道底层是 Local / Docker / K8s / E2B。
2. 文件路径可以统一使用 DeerFlow 的虚拟路径语义。
3. read / write / grep / glob 的结果都能走同一套 tool result / middleware / error handling 回写给模型。
4. 后续要替换 sandbox provider，不需要改每个工具的上层语义。

## AioSandboxProvider：生产化容器 / K8s 执行面

如果 LocalSandbox 更像本地 path-mapping 工作台，那么 [aio_sandbox_provider.py](../../../submodules/deer-flow/backend/packages/harness/deerflow/community/aio_sandbox/aio_sandbox_provider.py) 更接近生产环境的隔离执行后端。

第一轮已读代码里，AIO provider 涉及：

```text
LocalContainerBackend / RemoteSandboxBackend
Docker / Kubernetes runtime
warm pool
replicas
idle timeout
orphan reconciliation
```

这说明 DeerFlow 的 sandbox provider 层不是只为本地开发设计，而是为多后端执行环境预留了生产化扩展点。

可以这样区分：

| 实现 | 适合理解为 | 隔离强度 |
|---|---|---|
| LocalSandboxProvider | 本地 path-mapping 工作台 | 较弱，依赖路径检查和 host bash 开关 |
| AioSandboxProvider | Docker / K8s 执行后端 | 较强，依赖容器 / 集群隔离 |
| E2B / BoxLite | 外部 sandbox provider | 取决于外部服务实现 |

## 和 OpenHands sandbox 的区别

OpenHands 与 DeerFlow 都有 sandbox / workspace，但架构位置不同。

```text
OpenHands：
  App Server 创建 / 管理 sandbox
  sandbox 内运行 Agent Server
  Agent Server 启动 SDK Conversation
  Terminal / FileEditor 在 sandbox workspace 中执行

DeerFlow：
  Gateway / worker 启动 LangGraph agent runtime
  SandboxMiddleware 挂在 middleware chain 中
  第一次 sandbox tool call 时 acquire sandbox
  tool 通过 Sandbox abstraction 执行命令 / 文件操作
```

一句话：

> **OpenHands 的 sandbox 是“Agent Server 所在的远程工位”；DeerFlow 的 sandbox 是“LangGraph 工具调用按需领取的执行工作台”。**

再口语一点：

> **OpenHands 是先分房间，再让工人进去；DeerFlow 是工厂流程先跑，等某道工序要用工具时才领工具台。**

## 和 Permission / Security 的关系

DeerFlow 的 permission / security 已在 [permission-security.md](permission-security.md) 中总结为多层防线：

```text
Gateway authz
  -> GuardrailMiddleware + provider
  -> workflow safety middleware / RunManager / Sandbox
```

Sandbox 在这里回答的是“动作被允许后在哪里执行、能影响什么范围”。

它不能替代 Guardrail，也不能替代 Gateway authz：

- Gateway authz 管 API 资源访问，例如谁能读写 thread / run；
- GuardrailMiddleware 管工具调用前策略检查；
- ToolErrorHandling / LoopDetection / ReadBeforeWrite 等管工具运行过程的稳定性和安全性；
- Sandbox 管工具的执行落点、workspace、路径映射和 provider 隔离。

所以完整理解是：

> **DeerFlow 的 sandbox 是工具治理链中的执行环境边界；lazy init 让这条边界只在真正需要工具执行时才被创建。**

## QA / 讨论记录

### Q: DeerFlow 的 sandbox 到底是什么？

> **状态**: verified  
> **来源**: source-code / discussion

A: DeerFlow 的 sandbox 是工具执行工作台。它通过 `Sandbox` 抽象和 `SandboxProvider` 后端，为 bash / file / grep / glob / download 等工具提供统一执行环境。它不是 OpenHands 那种先给 conversation 分配一个运行 Agent Server 的远程开发房间，而是 LangGraph agent runtime 中工具调用按需使用的 execution environment abstraction。

### Q: DeerFlow 为什么要 lazy init sandbox？

> **状态**: verified  
> **来源**: source-code / discussion

A: 因为不是每个 run 都一定会执行工具。DeerFlow 默认 `SandboxMiddleware(lazy_init=True)`，只有第一次 sandbox tool call 时才 acquire sandbox，并把 `sandbox_id` 写回 `ThreadState`。这样能减少纯对话 / 澄清 / 提前终止 run 的资源浪费，也适合 Gateway 同时管理很多 thread / run 的平台场景。

### Q: LocalSandbox 是强安全沙箱吗？

> **状态**: verified  
> **来源**: source-code / discussion

A: 不是。LocalSandbox 更准确地说是本地 path-mapping sandbox：它把 `/mnt/user-data/workspace` 等虚拟路径映射到宿主目录，并用路径解析和 `relative_to(local_root)` 防止逃逸。它不等于 Docker / VM 级强隔离。DeerFlow 因此默认禁用 LocalSandbox 的 host bash，只有显式配置 `allow_host_bash=true` 才允许宿主 bash 执行。

### Q: DeerFlow 和 OpenHands 的 sandbox 精髓差异是什么？

> **状态**: verified  
> **来源**: source-code / discussion

A: OpenHands 的 sandbox 是平台化 SWE Agent 的远程隔离工位：App Server 创建 sandbox，sandbox 内运行 Agent Server，Terminal / FileEditor 在 workspace 里执行。DeerFlow 的 sandbox 是 LangGraph 工具调用的执行工作台：Agent runtime 先跑起来，第一次需要 sandbox 的工具调用才 lazy acquire sandbox。可以概括为：OpenHands 是“先分房间再开工”，DeerFlow 是“工作流跑到要动手时才领工具台”。
