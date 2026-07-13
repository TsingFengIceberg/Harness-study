# MCP：让 Agent 以标准协议连接外部能力

> **日期**: 2026-07-10 | **状态**: draft

## 相关文档

- [基础概念目录](README.md)
- [RAG：让模型先查证据，再基于证据回答](rag.md)
- [DeerFlow Tool System](../projects/deer-flow/tool-system.md)
- [DeerFlow RAG 相关能力映射](../projects/deer-flow/rag.md)
- [Lark CLI 与官方 Lark OpenAPI MCP 的 Agent 接入比较](../comparison/qa.md#q-lark-cli-和官方-lark-openapi-mcp-交给-agent-使用时有什么区别共同点和联系)

## 一句话��释

**MCP（Model Context Protocol）**是一���让 Agent Host 以统一方式连接外部能力的协议边界��

它解决的不是"模型怎么思考"，而是：

```text
一个 Agent / Host
如何发现、调用和管理外部系统提供的工具、数据和工作流能力？
```

可以把 MCP 想成 Agent 世界的"标准插座"：Host 不必为每个外部服务分别发明���种私有接法；外部服务只要实现 MCP server，就能��协议把能力提���给支持 MCP 的 Host。

## 一��先认识四个角色

```text
用户
  -> Host：承载 Agent、UI、权限和运行时的应用
    -> MCP Client：Host 内负责连接某个 server 的协议客户端
      -> MCP Server：对外暴露能力的进程或远程服务
        -> 外部系统：数据库、GitHub、��识库、文件系统、SaaS、内部 API ...
```

### 1.1 Host

Host 是最终运行 Agent 的应用。例如某个桌面 Agent、IDE、Web Agent 平台或 DeerFlow Gateway。它通常负责：

```text
- 用户身份和产品权限
- Agent runtime / model 调用
- 哪些 MCP server 可以连接
- 工具 schema 如何交给模型
- 工具调用如何执行、审计和展示
```

### 1.2 MCP Client

Client 在 Host 内部，负责与一个 MCP server 建立会话、发��能力、发送调用请求和接���结果。

一个 Host 可以同时有多个 MCP client：一个接 GitHub，一个接数据库，一个接知��库，一个接内部工单系统。

### 1.3 MCP Server

Server 连接真实外部系统���把能力按 MCP 语义暴露出来��它可以是本地启动的命令行进程��也可以是远程网络服务。

例如：

```text
GitHub MCP server
  -> search_issues / create_comment / list_pull_requests

Knowledge MCP server
  -> search_knowledge_base / get_document_section

Database MCP server
  -> query_orders / get_customer_profile
```

### 1.4 模型不是 MCP Client

模型通常不会自己通过网络连接 MCP server。更常见的分层是：

```text
模型：决定"我想调�� search_knowledge_base"
Host：校验、路由、执行这次工具调用
MCP Client：按协议向 Server 发请求
Server：访问真实外部系统并返回结果
```

**精髓标记：模型负责提出动作意图；Host 和 MCP 负责把意图安全地变���外部调用。**

## 二、MCP 能��露什么？深度理解 Tools、Resources、Prompts

初学时最容易把 MCP 等价于"给 Agent 加工具函数"，但 MCP 的能力面更宽：它标准化了三类可交换能力。

### 2.1 Tools（工具）

**直觉理解：** Agent 可以执行的动作。这是 MCP 三种能力里离 Agent 产品需求最近的一面，也是目前几乎所有 Host 实现都优先支持的面��

```text
示例：
  搜索知识库（search_knowledge_base）
  创建 GitHub issue（create_issue）
  查询数据库（query_orders）
  发送消息（send_message）
  部署代码（deploy）
  写文件（write_file）
  删除资源（delete_resource）
```

每个 tool 典型地包含：
- `name`：工具名
- `description`：告诉模型什么时候该用、怎么用
- `inputSchema`：期望的参数 JSON Schema，声明类型、required、enum 等

模型通过 tool calling 表达"我想调用某个 tool 及参数"，Host 再通过 MCP Client 向 Server 发出调用，Server 执行并返回结果。

**精髓标记：Tool 是"模型请外部世界做的事情"——可以读、可以写、可以改、可以��。不要把 MCP tool ��认当只读。**

### 2.2 Resources（资源）

**直觉理解：** 可被 Agent 读取的外部数据对象，类似"可供查阅的资料"。它不是动作，而是内容块。

```text
示例：
  数据库 schema 本身
  一份常驻配置（feature flags、限流规则）
  参考文档���文
  用户历史偏好快照
  环境变量模板
  SQL 表���构
```

Resource 通��用来让 Agent "先知道世界长什么样，再决定做什么"��先读取 schema 知道有哪些表和索引，再构造 `query_orders` �� SQL 参数；先读配置知道有哪些 flag，再决定用哪个。

资源的一项重要特征是：每个 resource 都绑定了 URI，这意味着它��可检索性。Host 或 Client 可以按 URI ��获取具体某份资源的当前版本，实现类似"先知��文件结构，再决定读哪些文件"的探路模式。

**精髓标记：Tool 是"给我做事"，Resource 是"先让我看��情况"。**

### 2.3 Prompts（提示模板）

**直觉理解：** Server 端提供的可复用提示模板或工���流入口。不���让 Agent 执行代码，而是让 Host ��用户用它来组织 Agent 的任务。

```text
示例：
  "审查这个 PR"——Server 提供一个��有 check list 的标准审查提示
  "���析这次 incident"——Server 提供一个带上下文收集步骤的提示模��
  "生成月度报告"——Server 提供一份报告结构模板和填写指���
```

Prompts 是 MCP 里目前支���最少的能力面。部分 Server 甚至不提供任何 prompt；多数 Host 的默认流程也不会主动消费 prompt���但在特定封闭��务场景下，prompt 的价值显著：它让后端团队可以预设"这件事的标准做法"，前端 Agent 照做即可。

**精髓标记：Prompts 保存的不是"Agent 能不能��"，而是"这件事的标��姿势"。**

### 2.4 为什么 Tools 是最高优先级的 MCP 能力？

这三种能力的产品落地闭环��间差异很大：

```text
Tools：Agent 做动作 -> 外部系统响应 -> 结果回流 -> 模型继续推理
  这是最短、最强的 Agent 价值闭��。

Resources：Agent 读取数据 -> 重新理解世界 -> 再决定做什么
  产品上需要更长的探索步骤，往往配合 Tool 一起用。

Prompts：后端规定模板 -> 前端用户/模型填��
  感受近似 MCP 额外带了模板管理功能，在很多场景下不如靠 Skill 或配置直接。
```

因此实际实现中：
- 几乎所有 MCP Host 都先支持 Tools
- Resources 常作为 Tool 的���助面
- Prompts ���选配中的选配

### 2.5 哪种 MCP 能力和 RAG 有关系？

**如果要通过 MCP 做 RAG，直接相关���是 Tool。**

一个知识库 MCP server 会把"从这个知识库里找内���"暴露成一个 tool：

```text
search_knowledge_base(query, collection, filters, top_k)
get_document_section(document_id, section_id)
```

Agent 调用这个 tool 做检索，MCP server 返回 chunks + source + score——这就是通过 MCP Tool 实现的 agent-mediated RAG。

Resources 也可能间接参与 RAG：例如通过 resource 先拿到知识库的结构（有哪些 collection），再决定如何构造 search 参数。但直接承担检索动作的仍是 Tool��

### 2.6 对比速查

| MCP 能力 | 本质 | 方向 | 示例 |
|---|---|---|---|
| Tool | 执行���作 | Agent → 外部世界 | search、create、update、delete |
| Resource | ���供数据 | ��部世界 → Agent | schema、config、文档全文 |
| Prompt | 规定模板 | Server → Host/用户/Agent | 审查清单、报告框架 |

不同 Host 对这些能力面的支持、UI 展示和授权方式可以不同���因此要区分：

```text
MCP 协议定义可交换的能力表达
!= 每个 Host 都必须以相同方式暴露所有能力
```

## 三、最小交互���程

从 Agent 视��看，常见调用路径是：

```text
Host 配置 / 连接 MCP server
  -> Client 初始化并发现 server capabilities
  -> Host 将允许的 tool schema 交给模型
  -> 模型提出 tool call
  -> Host 做权限、参数和运行时检查
  -> MCP Client 调用 server
  -> Server 访问外部���统
  -> result 回到 Host
  -> Host 作为 tool result 放回模型上下文
  -> 模型继续推理��给最终回答
```

这条主线和一般 function calling 很像，但 MCP 额外标准化了"Host 如何接入外部 server、如何发现能力、如何���护会话与传输"的部分。

## 四、MCP、Function Calling、Skills、Plugins、RAG 的区别

| 概念 | 主要解决什么 | 和 MCP 的���系 |
|---|---|---|
| Function / Tool Calling | 模型怎样表达"请执行这个��数及参数" | 常是 MCP tool 最终暴露给模型时使用的调用形态；但本地工具也可���经 MCP。 |
| MCP | Host 怎样标准化连接外部能力 | 协议与互操作层。 |
| Plugin | 对 Host 扩展能力的泛称 | 可用 MCP 实现，也可以是私有 SDK / 进程内扩���。 |
| Skill | Agent 做某类任务时应遵循什么流程与说明 | 可告诉 Agent 如何用 MCP 工具，但 Skill 自身不是连接协议。 |
| RAG | 如何检索外部证据并用于回答 | MCP server 可以提供 RAG Tool；RAG 也可在没有 MCP 的情况下实现。 |

��容易记住的一组句子：

```text
MCP：怎么接上外部世界。
Tool calling：模型怎样要求使用某个能力。
Skill：遇到某类任务时该怎么做。
RAG：回答前怎样找外部知识证据。
```

## 五、MCP 与 RAG：���组合，但不是���回事

一个知识库 MCP server 可以提供：

```text
search_knowledge_base(query, collection, filters, top_k)
get_document_section(document_id, section_id)
```

此时 Agent 可以通过 MCP 做 RAG：

```text
用户问题
  -> Agent 调 search_knowledge_base
  -> server 返回 chunks + source + version + score
  -> Agent 发现证据冲突时继续检索或读取原文
  -> 带引用回答
```

但下面的说法都不准确：

```text
"配置了 MCP 就有 RAG"          # 错：server 可能只提供写 issue 的工具
"MCP server 天然只读且安全"     # 错：它可以删除、写���、发送、��署
"RAG 必须用 MCP"                # 错��RAG 也可以直接用 HTTP / SDK / 本地库
```

## ���、连接方式：本地进程与远程服务

概念上可先��解为两类。

### 6.1 本地 stdio

```text
Host 启动一个本地 server 进程
  -> 双方通过标准���入 / 输出通信
```

适合本地命令行工具、开发环��、单机文件系统访问。优点是部署简单、无需公开网络端口；风险是 Host 实际在本机启动了一个外部程序，因此命令来源、环境变量和文件权限必须受控。

### 6.2 远程网络传输

```text
Host / Client
  -> HTTP 或流式网络连接
  -> Remote MCP Server
```

适合共享知识库、企业 SaaS、云端数据库或多用户服务。优点是���中治理；风险和要求包括认证、OAuth / token 生命周期、网络边界、租户隔离、重试、审计与服务可用性。

具体协议细节会演进��学习时先抓住稳定边界：**stdio 是本地进程���界，网络 transport 是远程服务边界。**

## 七、安全：MCP 工具调用的七层防线模型

MCP 让外部能力更容易接入，也扩大了 Agent 可触及的边界。把安全放在一个"不可信"原则里固然不错，但工程上需要更精确的防线拆分。

以下七层防线，从"谁可以被接"到"结果怎么处理"，构成一次 MCP tool call 的完整安全治理线。

### Layer 0：哪些 Server 可以��� Host 连接？

这是最外层防线：Host 知道哪些 MCP server 存在，哪些可以被信任。

```text
不可信 server 不应该出现在可用列表里。
已弃用或已废弃的 server 不应该还连着。
server 来源、版本和维护者必须有迹可查。
```

在 DeerFlow 中，这个防线由 `extensions_config.json` 和 MCP client builder 共同实现：[mcp/client.py:10-67](../../submodules/deer-flow/backend/packages/harness/deerflow/mcp/client.py#L10-L67) 只根据声明式配置构建 server 参数，不���自动发现或猜测 server；server 要进入可用集合必须先被 operator 明确配��。

**��问：如果配置了但 server 不可达怎么办？** Host 需要在连接/发现阶段有合理的超时和 fallback，而不是让不可达 server 阻塞整个 agent 启动。

### Layer 1：每个 Server 能对 Host 暴露哪些 Tool Schema？

即使 server 被连接了，也不意味着它���露的所有 tool 都应该交给模型。

```text
server 可能提供 30 个 tool，但当前 agent/scenario/host 策略只需要其中 5 个
read-only tool 和 write tool 不应该都放进同一个 agent
不用的 tool 放进模型上下文会���费 token 和增加误调用面
```

DeerFlow ��这里主要依靠通用工具过滤链和 deferred Tool Search 机制：`get_available_tools(...)` 汇总 MCP tools 后，由 `skill allowed-tools` 过滤，再由 `assemble_deferred_tools(...)` 控制哪些 tool schema 直接可见。详见 [DeerFlow Tool System](../projects/deer-flow/tool-system.md)。

### Layer 2：这次调用匹配的任务/意图边界是什么？

同一把 tool，在不同上下文中应该有不同的权限。例如 `query_database`：

```text
在"写月度报告"任务里，应该只能 SELECT
在"数据导入"任务里，应该可以 INSERT/UPDATE
在"���常查询"任务里，可能只需要读 replica，不能读 prod
```

这一层不是"能不能执行这个 tool"，而是"现在以什么样的身份和目的执行这个 tool"。实际实现中，这往往和 Host 端 RBAC、session scope、agent definition 或 conversation-level context 协同。

### Layer 3：这次调用是否需要人类审批？

即使 tool 在允许范围内、参数合法，也可能���要人类确认。

```text
write、delete、deploy、send 等高影响动作默认应审批
读操作通常放行，但读敏感数据（PII、财务、密钥）也可要求确认
批量操作和跨 scope 操作应升级确认级别
```

这是 HITL（Human-in-the-Loop）在 tool call 层的精确位置。DeerFlow 中 GuardrailMiddleware 可以在工具执行前做 deny/allow 判定，ClarificationMiddleware 可以把控制权交回用户。OpenClaw 有 before_tool_call approval broker，Hermes 有 dangerous command approval 和 ACP edit approval。

**But note：审批框本身也会疲劳。** 如果每次 `write_file` 都弹框，用户会习惯性点"允许"。合理的设计是区分 hardline block（绝对不能做）、approval（需要确认）、auto-allowed（可信动作）。

### Layer 4：真正执行时，Server 拥有什么凭据和权限？

这是 tool call 到达 server 端时，server 和目标系统的权限边界。

```text
MCP server 用什么身份访问 GitHub？是 org member、admin 还是 read-only token？
数据库用的连接凭据是 read replica 还是 prod RW？
token 有没有过期？刷新机制是否正常？
是否使用了最小权限 OAuth scope，而不是一把大 token 到处用？
```

DeerFlow 中 MCP tools 的发现和缓存机制在 [mcp/tools.py](../../submodules/deer-flow/backend/packages/harness/deerflow/mcp/tools.py) 和 [mcp/cache.py](../../submodules/deer-flow/backend/packages/harness/deerflow/mcp/cache.py)，但凭据管理和 OAuth 生命周期在 server 配置和外部凭据层，不在 MCP 协议本身。

**精髓标记：MCP 替 Host 解决了"呼叫 server"的问题，但不替 Host 决定"server 应该有��么权限"。**

### Layer 5���Tool Result 回来后怎么处理？

tool result 回到 Host 后，是直接交给模型，还是要经过处理？

```text
result 可能包含敏感数据，需要截断或脱敏
result 可能很大，需要做预算控制或持久化后再给模型
result 可能包含可执行文��/HTML/script，不应该原样放进后续 system message
result 可能包含虚假、过时或未授权的内容
```

DeerFlow 的 `ToolOutputBudgetMiddleware` 控制���果大小，`SandboxAuditMiddleware` 审计文件操作，Tool Search deferred 机制做 schema promotion 而非结果管理。**但 tool result 的脱敏、权限化标注、来源可信度标记，通常需要 Host 侧或 server 侧额外实现**，不在 MCP 协议的默认语义内。

### Layer 6：调用可被审计和恢复吗？

最后一道防线是"事后能不能追溯"。

```text
谁、在哪个 session、以什么权限、调了哪个 server 的哪个 tool？
参数摘要、结果摘要、耗时、成功/失败
如果需要回滚，这次调用对应的外部系统变更是否有记录？
```

DeerFlow 的 Gateway run lifecycle 和 `RunManager` 管理 run 状态、cancel、interrupt 和 rollback；middleware chain 中有审计点；`StreamBridge` 传输 events。但完整的"MCP tool call 端到端审计"，需要 Host、server 配置和外部系统日志三方协作。

### 七层防线的精���

```text
Layer 0: 这个 server 能被连吗？（server trust）
Layer 1: 这些 tool schema 能给模型看吗？（tool visibility）
Layer 2: 当前任务/意图下能不能调这个 tool？（intent/task boundary）
Layer 3: 这次调用需要人看一眼吗？（execution approval / HITL）
Layer 4: server 和下游系统有什么凭据和权限？（server-side permission）
Layer 5: tool result 回来如何脱敏、预算和防注入？（result handling）
Layer 6: 事后能追溯和回滚吗？（audit & recovery）
```

**精髓标记：MCP 标准化的是连接（Layer 0-1 的协议面），不会���动替你完成信任（Layer 0）、授权（Layer 2-4）、审批（Layer 3）、数据隔离（Layer 5）和审计（Layer 6）。**

这七层不是���每次接一个新 MCP server 都要全部重建一遍；更合理的做法是：**先为每个 server 回答 Layer 0-1，再按 tool 的风险等级回答 Layer 2-6 中哪些层必须有、哪些层可选。**

## 八、用 DeerFlow 作为具体例子

DeerFlow 在 [mcp/client.py](../../submodules/deer-flow/backend/packages/harness/deerflow/mcp/client.py) 中根据配置构建 `stdio`、`sse`、`http` 类型的 server 参数；在 [mcp/tools.py](../../submodules/deer-flow/backend/packages/harness/deerflow/mcp/tools.py) 中发现并加载 enabled server 的工���；在 [mcp/cache.py](../../submodules/deer-flow/backend/packages/harness/deerflow/mcp/cache.py) 中按配置变���刷新工具缓存。

可以把它的链路理解为：

```text
extensions_config.json
  -> DeerFlow MCP client / tool discovery
  -> LangChain BaseTool 集合
  -> DeerFlow middleware / tool policy
  -> LangGraph agent runtime
  -> 模型可调用的 MCP tool
```

当 MCP tools 很多时，DeerFlow 的 deferred Tool Search 可延迟暴露 tool schema，降低模型上下文负担。它解决的是"模型如何发现大量工具"，���是"从业务文档���索事实"；详细实现见 [DeerFlow Tool System](../projects/deer-flow/tool-system.md)。

以下映射可以帮助理解 DeerFlow 在各层的覆盖程度：

| 防线层 | DeerFlow 对应能力 | 覆盖程度 |
|---|---|---|
| Layer 0 (server trust) | `extensions_config.json` + MCP client builder | operator 显式配置 |
| Layer 1 (tool visibility) | `get_available_tools(...)` → skill filter → deferred tool search | 有 schema promotion / fail-closed |
| Layer 2 (intent/task boundary) | GuardrailMiddleware 前策略检查 | 有 allow/deny |
| Layer 3 (HITL / approval) | GuardrailMiddleware deny + ClarificationMiddleware | 有（但不是 per-tool approval UI） |
| Layer 4 (server credential) | MCP tools/cache 层 | protocol 侧有；凭据管理在外部 |
| Layer 5 (result handling) | ToolOutputBudget、SandboxAudit、ToolErrorHandling | 有大小控制、审计和异常兜底 |
| Layer 6 (audit/recovery) | Gateway run lifecycle + RunManager cancel/rollback | 有 run 级治理，非 tool-call 级审计 |

## QA / 讨论记录

### Q: MCP 是否等于给 Agent 提供 API？

> **状态**: draft
> **来源**: discussion / official-docs

A: 可以把它理解为"让 Agent Host 标准化接入外部 API / 数据 / 工具"的协议，但它比某一个业务 API 更上层：它定义 Host、Client 与 Server 如何发现和交换能力。模型通常不直接连 server；模型通过 tool calling 表达意��，Host 再通过 MCP client 实际调用 server。

### Q: MCP server 能不能做 RAG？

> **状态**: draft
> **来源**: discussion

A: 可以。知识库 MCP server 可以把 `search_knowledge_base`、`get_document_section` 等检索能力暴露成 tools，供 Agent 做多轮检索和核验。但 MCP 是连接协议，RAG 是检索增强模式；server 也可能只提供 GitHub、数据库或写操作工具，完全不涉及 RAG。

### Q: Tools、Resources、Prompts 三种能力分别对应什么场景���

> **状态**: draft
> **��源**: discussion / official-docs

A: Tool 是 Agent 可以执行的动作（���索、创建、删除、查询、部署），是目前产品闭环最短、Host 支持最广的能力面。Resource 是可读取的数据对象（schema、配置、文档全文），用来让 Agent 在执行动作前先了解环境。Prompt 是 Server 提供��标准任务模板（审查清单、报告结��），由后端团队预设标准做法。绝大部分 Host 实现都优先支持 Tool，Resource 常见为辅助面，Prompt 是选配中的选配��详见本文第二节。

### Q: MCP 安全是不是只要"不要信任外部输入"就��了？

> **状态**: draft
> **来源**: discussion

A: 不够。"不要信任外部输入"是正确的原则，但工程上需要更精确的防线拆分。本文提出了七层防线模型：Server 信任（Layer 0）→ Tool 可见性（Layer 1）→ 任务/意图边界（Layer 2）→ 执行���批/HITL（Layer 3）→ Server 端权限（Layer 4）→ ��果处理（Layer 5）→ 审计/恢复（Layer 6）。MCP 协议标准化的是连接面，不会自动完成信任、授权、审批、脱敏和审计。详见本文第七��。

### Q: MCP tool call 安全能全部靠 DeerFlow middleware 实现吗？

> **状态**: draft
> **来源**: discussion / source-code

A: 不能全部靠 middleware。DeerFlow 在 Layer 0-1（server 配置 + tool 发现/过滤）、Layer 2（GuardrailMiddleware 前策略检查）、Layer 3（HITL/clarification）、Layer 5（ToolOutputBudget/SandboxAudit/ToolErrorHandling）和 Layer 6（run lifecycle/RunManager）都有对应能力。但完整的凭据管理（Layer 4 的 OAuth scope、refresh、最小权限）在外部凭据层，完整的 per-tool-call 审计和端到端回滚也需要 Host、server 和下游系统三方协同。

## 参考资��

- [Model Context Protocol 官方网站](https://modelcontextprotocol.io/)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/specification)
- [DeerFlow MCP 操作文档](../../submodules/deer-flow/backend/docs/MCP_SERVER.md)
