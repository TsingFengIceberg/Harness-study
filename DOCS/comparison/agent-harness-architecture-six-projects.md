# 六项目 Agent Harness 架构对比分析

> **日期**: 2026-06-30 | **状态**: research-base | **来源**: 外部 Deep Research 报告
>
> 本文是对 DeerFlow、Hermes Agent、Claw-Code、OpenClaw、learn-claude-code、OpenHands 六个 Agent Harness 项目的全景式架构对比，作为五项目调研 Base 的扩展版保留。文中已尝试标注 `source-code verified`、`official-docs`、`official-issue`、`third-party`、`inference` 等可信度层级；但所有关键判断仍需要在后续自研专题笔记中回到 submodule 源码与官方文档逐项核验，不视为最终源码结论。

## **执行摘要**

Agent Harness（智能体支架或运行环境）正在经历从单纯的“大语言模型 API 包装器”向“云原生操作系统级基础设施”的深刻范式跃迁。本研究对六个极具代表性的开源 Agent Harness 项目（DeerFlow、Hermes Agent、Claw-Code、OpenClaw、learn-claude-code 以及新增的 OpenHands）进行了深度架构剖析。分析表明，当前赛道已产生明显的分化与演进：一方面，本地 CLI 形态（如 Claw-Code）在追求极致性能与底层 Linux 命名空间级别的沙箱安全；另一方面，多端控制面（如 OpenClaw）正在抢占全天候个人助理的即时通讯入口。  
更为关键的是，以 OpenHands V1 和 DeerFlow 为代表的演进方向，明确指向了 SDK 化、Server 化与 Platform 化的云原生基础设施路径。特别是 OpenHands V1 架构的彻底重构——引入可选沙箱、状态全面抽离为单一可变数据源、以及强事件驱动机制——标志着软件工程（SWE）Agent 正在从单机实验品走向大规模、多租户的生产可用阶段。本报告将详细阐述这些架构的底层机制，为后续自研工作提供坚实的理论与工程参考。

## **研究对象与资料来源**

本报告基于官方源码、官方文档、官方 Issue 以及经过交叉验证的第三方技术分析生成。为满足严格的工程化与可验证性要求，报告内所有关键结论均通过内联引用标明了信息来源的可信度层级，包括 \[source-code verified\]（源码核验）、\[official-docs\]（官方文档）、\[official-issue\]（官方问题追踪）以及 \[third-party\]（第三方分析）和 \[inference\]（合理推断）。研究对象涵盖：

1. **bytedance/deer-flow**：字节跳动开源的通用长周期任务 SuperAgent Harness。  
2. **NousResearch/hermes-agent**：具备闭环学习能力与持久化记忆的自进化个人 Agent 框架。  
3. **ultraworkers/claw-code**：使用 Rust 重写的极速本地 Claude Code 运行环境。  
4. **openclaw/openclaw**：跨平台、多设备接入的个人 AI 助理 Gateway 控制面。  
5. **shareAI-lab/learn-claude-code**：揭示 Agent 底层原理的白盒教学型极简 Harness。  
6. **OpenHands/OpenHands**：面向软件开发（SWE）的开源平台化 SDK 与企业级应用系统。

## **六项目总体定位与演进趋势**

在对六个项目进行全景审视后，可以清晰地识别出它们各自解决的核心问题以及在生态位中的重叠与互补关系。这六个项目实际上代表了 Agent Harness 演进树上的不同分支。  
DeerFlow 属于**通用长周期 Agent Harness**，其核心使命是解决复杂任务（耗时数分钟至数小时）的分解、并发子智能体编排与沙箱执行问题，填补了单次对话脚本与重型企业工作流之间的空白 \[official-docs, cite: 1, 4\]。Hermes Agent 被定位为**记忆进化型个人 Agent Harness**，其核心抽象在于解决智能体“如何越用越聪明”的问题，通过程序化记忆（技能自动生成）和跨会话的混合检索记忆，实现个人知识资产的积累 \[official-docs, cite: 49, 52\]。Claw-Code 则是典型的 **Claude Code 类本地 CLI Harness**，它剥离了订阅制的束缚，核心解决本地代码库的智能交互问题，主打高性能状态机与底层沙箱安全 \[source-code verified, cite: 13, 16\]。OpenClaw 代表了**多设备/多端控制面 Agent Harness**，解决的是 AI 智能体的泛在访问问题，充当连接 20 余种 IM 平台与本地/云端 Agent 的网络层网关 \[official-docs, cite: 22\]。learn-claude-code 作为**教学型/原理型 Harness**，剥离了工业界项目的所有复杂中间件，以最简代码向开发者揭示 Agent 循环、沙箱、记忆与并发等架构的本质面貌 \[source-code verified, cite: 25, 84\]。新增的 OpenHands 则占据了**平台化 SWE Agent Harness** 的高地，核心解决软件开发自动化的问题，提供无缝跨越本地与云端的执行能力、标准 SDK 抽象及面向组织的 Web 协作面板 \[official-docs, cite: 33, 41\]。  
在这些项目中，重叠与互补关系错综复杂。Claw-Code 与 OpenHands 的 CLI 模式在“本地代码编辑与重构”场景下存在直接的赛道重叠，两者均为 SWE 领域的执行框架，但底层哲学完全不同（极致本地化 vs 云原生解耦）。OpenClaw 作为控制面（Control Plane），与 Claw-Code/OpenHands 等数据面（Data Plane）形成完美的互补关系，OpenClaw 完全可以作为网关接入 OpenHands 的后端。Hermes Agent 侧重于个人长效记忆和通用事务，而 DeerFlow 则侧重于重度图文研究与长周期报告生成的“异步工作流”，两者在任务复杂度支持上形成阶梯。OpenHands 的加入极大地冲击了原有的五项目分类法，它证明了单一形态（如 CLI 或 Web）的分类已经失效，必须引入“以 SDK 为核心抽象，CLI/UI/Server 仅为不同挂载外壳”的现代架构视角 \[official-docs, cite: 36\]。  
当前 Agent Harness 的主流演进趋势正呈现出显著的底层收敛与上层发散。首先是 **SDK 化与 Server 化**，胖客户端 CLI 正在被解构，核心逻辑下沉至无状态 SDK，执行环境封装入独立的 Agent Server 以支持多租户。其次是 **MCP/ACP 协议标准化**，无论是 OpenHands 还是 Hermes Agent，都在积极拥抱 Model Context Protocol 以统一工具接口，并开始支持 Agent-Client Protocol (ACP) 以实现异构智能体间的嵌套调度 \[official-issue, cite: 40, 64\]。最后是 **Sandbox 基础设施化与 Workflow 自动化**，沙箱不再是简单的本地子进程，而是演变为可通过标准接口热插拔的 Docker/K8s 容器集群；同时，结合 Webhook 与 Cron 定时任务的自动化流水线，正使得 Agent 从被动响应的工具转变为主动巡检的数字员工 \[official-docs, cite: 32, 40\]。

## **逐项目深度分析**

### **1\. DeerFlow**

**架构定位与主循环机制**：DeerFlow 是一个面向长周期研究与代码创建的泛用型 SuperAgent Harness，其核心抽象是基于 LangGraph 的图状态机与动态子智能体（Sub-agent）编排系统，主要服务于需要处理海量图文、执行长程步骤的重度研发或研究分析人员 \[official-docs, cite: 4, 45\]。其 Agent Loop 的核心入口位于 make\_lead\_agent 中构建的 LangGraph，采用异步并发的设计，天然突破了同步阻塞循环的限制。状态流转完全依靠有向图进行，这种设计极其适合 Long-horizon 任务，并通过底层的 LangGraph Checkpointer 实现了完善的会话中断、恢复与流式输出能力 \[source-code verified, cite: 66, 69\]。  
**工具、沙箱与扩展生态**：在工具调用层面，DeerFlow 放弃了全量 Prompt 注入的传统做法，转而采用以 Markdown 文件（SKILL.md）定义的动态渐进式技能加载机制。工具 Schema 按需暴露给模型，不仅支持原生 MCP 服务器，还内置了包含信息抽取（InfoQuest）、文件操作、代码执行等一系列强大工具 \[official-docs, cite: 45, 47\]。其沙箱与 Runtime 体系经过了精心的接口抽象，提供 LocalSandboxProvider（宿主机直跑）与 AioSandboxProvider（Docker 容器及 Kubernetes Pod）等多种模式。为了确保多并发下的文件一致性，DeerFlow 实现了基于虚拟路径映射（如 /mnt/user-data/workspace）的 Per-thread 级别文件系统强隔离，并通过底层的文件读写锁解决并发竞争问题 \[source-code verified, cite: 66, 69\]。  
**权限、安全与人机交互 (HITL)**：DeerFlow 的安全边界严重依赖于其底层的 Docker/K8s 沙箱隔离，其在工具层的危险命令拦截相对薄弱，更倾向于通过系统隔离防范物理损伤 \[source-code verified, cite: 103\]。在人机交互方面，DeerFlow 引入了独创的 Plan Mode（计划模式），在处理复杂任务时，中间件会自动向系统注入 Todo Tracker，要求模型在执行前输出计划列表，用户借此可直观审查并干预任务进度 \[official-docs, cite: 102\]。交互介质不仅包含自研的 Web UI，还深度整合了 Feishu、Slack 等 IM 频道 \[official-docs, cite: 45\]。  
**状态、记忆与任务管理**：记忆与上下文管理是 DeerFlow 架构的重中之重。系统配置了 SummarizationMiddleware，当 Token 消耗逼近设定阈值时，该中间件会触发动态压缩策略：它不仅能将旧消息折叠为紧凑的系统摘要，还会巧妙地保护近期加载的技能规范与 Tool Call/Result 映射对，防止大模型出现逻辑断层 \[source-code verified, cite: 98\]。其长期记忆采用异步抽取与防抖动（Debounced）写入机制，持续累积用户偏好与项目事实。状态管理完全托管于后端的 LangGraph 持久化层，支持跨并发请求的多线程协作。  
**韧性、中间件与 Prompt 机制**：DeerFlow 的架构极其强调 Middleware 的拦截与切面编程能力。系统定义了多达 9 层的 Middleware 链（包括 ThreadData、Sandbox、Summarization、TodoList、Memory 等），负责在每次 LLM 调用前后进行沙箱注入、日志记录与上下文修剪 \[source-code verified, cite: 66\]。多智能体方面，Lead Agent 有权根据任务规划动态创建具有独立隔离环境的子智能体（最高允许每轮 3 个并发），并采用 Fan-out/Fan-in 模式合并结果 \[official-docs, cite: 45\]。当底层沙箱意外崩溃时，中间件具备捕获状态并重新拉起新容器环境自动挂载虚拟路径的韧性机制 \[source-code verified, cite: 66\]。其 Prompt 体系支持高度动态组装，将技能指引与工作目录实时注入特定的 XML 标签中。

### **2\. Hermes Agent**

**架构定位与主循环机制**：Hermes Agent 是由 NousResearch 开发的、具有强大闭环自我进化能力的个人 Agent Harness。它的核心抽象围绕着“三层记忆模型”与“经验自动化凝结”展开，专为那些需要 AI 助理在跨日、跨周的长周期协作中“越用越聪明”的终端极客与开发者设计 \[official-docs, cite: 49, 52\]。其 Agent Loop 的核心是一个名为 run\_conversation 的同步阻塞控制流，但在与用户的交互面上，该循环被封装在异步的 Gateway Runner 之中，依靠细粒度的事件回调（Callbacks）将工具执行状态和 Token 生成流式推送到 TUI（终端用户界面）或 IM 前端。其循环依靠严格的 max\_iterations（迭代预算，默认 90 次）来防止死循环失控 \[source-code verified, cite: 74, 76\]。  
**工具、沙箱与扩展生态**：Hermes 的工具定义采用 Python 装饰器辅以 Pydantic Schema，系统原生地对 MCP 协议提供了第一级支持，甚至支持将第三方大模型封装为 MoA（Mixture of Agents）虚拟模型工具 \[source-code verified, cite: 8, 75\]。系统拥有 6 种不同的运行环境后端（Local, Docker, SSH, Daytona, Singularity, Modal），其 Runtime 隔离依赖于每次会话分配的独立 Task ID。其生态系统的杀手锏是“自动技能生成（Auto Skill Creation）”机制：当 Agent 通过多次试错完成某项复杂任务后，系统会触发一个内部微型反思 Loop，将经验总结为 Markdown 格式的 procedural memory（程序记忆），后续执行同类任务时直接复用 \[official-docs, cite: 49, 52\]。技能加载分为 L0（仅名称描述）、L1（详细参数）、L2（完整执行步骤）的渐进式展开策略，以兼顾性能与 Token 开销 \[official-docs, cite: 49\]。  
**权限、安全与人机交互 (HITL)**：为了适应其泛在接入的特性，Hermes 构建了深度防御（Defense in Depth）安全模型。底层有独立的外部 Rust 扫描器（Tirith）对二进制与依赖项进行强制校验，中间层有防范路径穿越和混淆的正则危险命令检测机制，上层则引入了独特的 Smart Approval（智能审批）系统。该系统允许使用一个廉价的辅助 LLM 对敏感操作（如文件修改、网络请求）进行风险定级，高风险操作才会被推送至 TUI 或 IM 界面由人类进行异步或同步审批，大幅缓解了全手动审批带来的“审批疲劳” \[official-docs, official-issue, cite: 52, 104\]。  
**状态、记忆与任务管理**：Hermes 的记忆系统设计是其与其他所有 Harness 拉开代差的关键。它实现了三层记忆：单次会话的短期工作记忆；依赖 SQLite FTS5（甚至可通过插件扩展为 Milvus 混合检索）构建的情节记忆（Episodic Memory）；以及由 AI 自主写入的程序性记忆（Procedural Memory / Skills）。通过检索与大模型信息凝结技术的结合，Hermes 几乎彻底消除了 Context Window 爆炸的隐患 \[official-docs, third-party, cite: 49, 50\]。状态管理依托于本地化的强目录隔离（HERMES\_HOME）机制，确保持久化数据与执行环境的严格对齐。不仅如此，系统内建了 Cron 调度机制，支持后台执行自动化的例行检查和播报任务 \[official-docs, cite: 9\]。  
**韧性、中间件与 Prompt 机制**：在架构原则上，Hermes 将“Prompt 缓存稳定性”奉为圭臬。在长时间的会话中，除了必要的上下文压缩，任何导致缓存失效的中途 Prompt 突变（如临时加载庞杂的项目文档）都被严格限制。其 build\_system\_prompt() 采用固定的模块拼接顺序（Persona, Platform Hints, Memory, Skills Guidance），以此确保能稳定命中底层 Provider 的 Prompt Caching \[source-code verified, cite: 73, 76\]。系统的容错性表现为对工具崩溃的强韧性包裹，任何运行时异常都会被转化为结构化的文本反馈给 LLM 以便其自行修正，绝不允许工具异常导致主循环崩溃 \[source-code verified, cite: 76\]。它同样支持独立上下文的子智能体任务派发，实现并发信息搜集与处理。

### **3\. Claw-Code**

**架构定位与主循环机制**：Claw-Code 是一个追求极致性能与底层控制的本地 CLI Harness，其定位是对 Anthropic 闭源应用 Claude Code 的 Rust 语言级白盒重写。核心抽象是高性能的事件流状态机（State Machine）和底层操作系统级的安全沙箱机制。其主要用户群体是重度依赖本地 IDE 旁路协作、对响应延迟零容忍的极客开发者 \[source-code verified, cite: 13, 57\]。其 Agent Loop 彻底摒弃了传统的同步阻塞模型，完全建立在异步事件驱动之上。模型的单轮生成、工具执行请求以及结果回写全部通过 Rust 的 Channel 转化为离散事件，尽管不具备图状态机的复杂分支能力，但在单线长对话和流式呈现（Streaming）上表现出了无与伦比的平滑度 \[source-code verified, third-party, cite: 13, 57\]。  
**工具、沙箱与扩展生态**：在工具调用系统上，Claw-Code 直接内置了高度优化的底层文件与系统工具（读写、编辑、Bash 终端、Grep、Glob）。这些工具在代码层面通过 Rust Trait 强类型定义，其参数解析直接映射到系统级操作。虽然其路线图中规划了 MCP 的全面支持，但根据源码核验，当前的 MCP 生命周期管理与桥接主要停留在 Registry 分发层面，尚未达到复杂的外部生产环境即插即用水平 \[source-code verified, official-issue, cite: 13, 58\]。沙箱架构是 Claw-Code 最为硬核的亮点：在 Linux 环境下，它直接调用底层的 unshare 机制创建完全隔离的 Namespace 容器，阻止恶意代码越权；而在 macOS 和 Windows 上，则退化为依靠文件系统权限的弱隔离模式 \[source-code verified, cite: 57, 110\]。  
**权限、安全与人机交互 (HITL)**：配合底层沙箱，Claw-Code 设计了极为克制的三级权限安全模型：read-only、workspace-write 与 danger-full-access \[source-code verified, cite: 57, 110\]。系统的安全拦截前置于工具层，并在执行层交由操作系统沙箱兜底。人机交互（HITL）主要通过本地的终端 REPL 环境进行，对于危险命令会在终端抛出交互式确认（Prompt）。其内部实现了强大的 /teleport 和 /ultraplan 等动态 Slash 指令，极大提升了本地开发过程中的澄清（Clarification）和中断调整效率 \[source-code verified, cite: 91\]。  
**状态、记忆与任务管理**：Claw-Code 拥有高度优化的短程上下文压缩机制，复刻了 Claude Code 的 auto\_compaction 功能。当上下文长度超出设定阈值时，引擎会智能提取先前的关键信息片段拼接成摘要系统提示，同时无缝保留最近 N 轮的具体对话轨迹以确保连续性 \[third-party, source-code verified, cite: 13, 58\]。长期记忆层面相对薄弱，但深度整合了基于项目文件的记忆注入（主动读取 CLAUDE.md，.claw.json 以及特定的 rules 目录）\[source-code verified, cite: 110\]。状态管理是其架构设计的一绝：每一次的交互状态都被实时、细粒度地写入本地工作区的 .claw/worker-state.json 文件中，这意味着无论 CLI 遭遇怎样的崩溃断电，重启后均能读取 JSON 精准重构内存并无缝恢复会话（Resume）\[source-code verified, cite: 110\]。  
**韧性、中间件与 Prompt 机制**：由于是用 Rust 编写的紧凑型二进制文件，Claw-Code 在灵活的 Middleware/Hooks 链上远不如 Python 框架动态，其核心拦截机制硬编码在内部验证通道（Validation Lane）中 \[source-code verified, cite: 58\]。多智能体协作能力虽然在架构中有预留，但实操中依然倾向于单向的 Subagent 同步调用，缺乏复杂的异步编排能力。Prompt 的构建高度格式化，系统利用 Rust 解析器将项目上下文、当前环境信息等组装为静态结构发送，极大地降低了 Prompt Injection 的风险。

### **4\. OpenClaw**

**架构定位与主循环机制**：OpenClaw 并非一个纯粹的执行引擎，其被精准定位为“多设备/多端控制面（Control Plane）Agent Harness”。它的核心抽象是统一的网络网关（Gateway）与消息路由总线，其核心目标是打破终端墙，充当用户私有云与超过 20 种即时通讯平台（如 WhatsApp, Telegram, Slack, Discord 等）之间的超级桥梁 \[official-docs, cite: 22\]。它的 Agent Loop 依托于 Node.js 单线程异步非阻塞事件循环运行，主循环的入口隐藏在处理各类 Webhook 和 WebSocket 帧的消息分发器之中，天然是队列与事件驱动的，非常适合高并发的轻量级助理请求 \[official-docs, inference, cite: 22\]。  
**工具、沙箱与扩展生态**：OpenClaw 构建了一个类似于操作系统包管理器的繁荣生态系统——ClawHub。工具既可以通过纯文本 Markdown 编写的 Skills 进行声明式扩展，也可以通过兼容 NPM 的 JS 代码插件（Code Plugins）进行深度定制。工具 Schema 以 JSON 格式在注册表中暴露，并支持完整的 MCP 协议接驳 \[official-docs, source-code verified, cite: 19, 78\]。在沙箱与 Workspace 方面，OpenClaw 默认采用极其轻量级的宿主机直接执行模式，它并不关注深度的 Docker 或 VM 隔离，而是将重点放在如何打通本地 Node.js 进程与外部服务（如 GitHub CLI gh）的交互上 \[official-docs, cite: 21, 61\]。  
**权限、安全与人机交互 (HITL)**：由于重度暴露在各种公共 IM 网络下，OpenClaw 的安全模型侧重于入口层面的防范。它设计了严格的 DM Pairing（私信配对授权）验证和身份拦截机制，以阻止未经授权的聊天请求触及底层的执行沙箱 \[official-docs, cite: 117\]。一旦授权通过，执行层面的权限控制则相对宽松。由于交互介质是各种 IM 工具，其 HITL 审批极其灵活——用户可以在手机微信或 Telegram 上随时收到工具执行风险预警，并点击异步确认按钮放行任务，天然支持远程及断线恢复的审批工作流 \[official-docs, cite: 20\]。  
**状态、记忆与任务管理**：受限于跨渠道对话的离散性，OpenClaw 的上下文管理高度依赖外部组件（如整合 DuckDB 进行历史 Issue 或对话数据的外置化管理）\[official-docs, cite: 21\]。系统根据发出指令的不同用户和 Channel 智能切分独立的上下文 Session。其在任务系统上的布局极为抢眼，内置强大的 Automation 控制流，不仅支持 Cron 定时任务（如每日晨报），还能深入集成 Webhook，实现在 GitHub 提交代码后自动触发 Agent 后台静默执行代码审查并回传评论的无值守流水线 \[official-docs, cite: 21\]。  
**韧性、中间件与 Prompt 机制**：OpenClaw 基于 WebSocket 实现了卓越的流式响应支持。系统的架构核心就是一个巨大的事件路由器，因此任何节点（如移动端 iOS Node 或 Android Node）的掉线与重连都能被平滑处理 \[official-docs, cite: 22\]。错误恢复依赖于宿主机的守护进程监控（Launchd/Systemd）\[official-docs, cite: 23\]。Prompt 的装配主要通过读取用户挂载的 AGENTS.md 和 SOUL.md 进行人格与业务域的约束 \[official-docs, cite: 117\]。多智能体支持体现在基于角色的 Agent 路由机制上，但彼此间复杂的协同谈判能力稍弱。

### **5\. learn-claude-code**

**架构定位与主循环机制**：顾名思义，learn-claude-code 是一个极其纯粹的教学型、原理级 Agent Harness。它的存在目的不是为了应用，而是用不到 100 行的核心代码向开发者白盒解密商业化闭源产品（如 Claude Code）底层的运行哲学 \[source-code verified, cite: 25, 84\]。其主循环（Agent Loop）毫无花巧可言，是一个完全同步阻塞的 while stop\_reason \== "tool\_use" 结构。大模型判断是否需要调用工具，Harness 捕获结果并附加到消息栈，循环往复直至任务终结，不包含复杂的并发状态树，亦不支持中断恢复 \[source-code verified, cite: 84\]。  
**工具、沙箱与扩展生态**：在工具调用系统上，它将复杂的 Schema 定义简化为基础的 Python 字典结构透传给模型，工具的解析仅仅是简单的函数名分发 \[source-code verified, cite: 84\]。它彻底去除了沙箱（Sandbox）机制，一切命令直接在宿主机进程中以原生权限赤裸执行，因此安全边界极弱，没有任何的防穿越和容器隔离保护措施 \[source-code verified, cite: 24, 84\]。生态扩展上，教程虽然演示了如何手工接入简单的 MCP Client，但不具备生产环境的插件管理能力 \[source-code verified, cite: 87\]。  
**权限、安全与人机交互 (HITL)**：为了展示概念，它在部分章节通过命令行 input() 挂起线程，模拟实现了基础的危险命令拦截和 Allow/Deny 手动审批 \[source-code verified, cite: 87\]。  
**状态、记忆与任务管理**：系统在后期演进章节（阶段 8）揭示了避免 Context Window 爆炸的核心技术——上下文修剪（Snipping），即暴力提取历史消息进行粗粒度压缩后替换原有数组 \[source-code verified, cite: 87\]。任务系统方面，教学版利用纯文本或简单的 JSON 文件演示了如何构建一个包含依赖关系状态的本地任务看板（Todo/Task Tracker）以及基础的 Cron 线程驱动背景任务 \[source-code verified, cite: 87, 119\]。  
**韧性、中间件与 Prompt 机制**：教程深刻阐述了 Middleware 与 Hook 的本质，通过简单的 Python 装饰器和函数拦截数组实现了工具执行前后的切面逻辑（Pre-tool / Post-tool hook）\[source-code verified, cite: 87\]。在教学演进中，系统示范了如何从零构造 XML 标签驱动的 System Prompt，以及如何通过文本信箱机制（JSONL Inbox）实现基础的多智能体消息投递与协作 \[source-code verified, cite: 121\]。

### **6\. OpenHands (原 OpenDevin) 专项深度分析**

**架构定位与核心抽象**：OpenHands 代表了目前开源社区最为庞大且成熟的**平台化 SWE（软件工程）Agent Harness**。相较于追求单机极客体验的 Claw-Code，OpenHands V1 的视野是企业级的研发效能底座。它的核心抽象是将系统彻底解耦为三个维度：**不可变的执行系统（Workspace）、隔离的组件树（Tools）以及被严格抽离为单一可变数据源的状态管理（Conversation State）** \[official-docs, source-code verified, cite: 36, 96\]。它不仅是一个可以本地跑的 CLI 工具，更是一套集成了 software-agent-sdk、分布式的 Agent Server 和面向组织管理的 Web 交互界面 agent-canvas 的完整平台 \[official-docs, cite: 33, 94\]。  
**与 Claw-Code / OpenClaw 及闭源工具的对比差异**：  
OpenHands 绝对不是单纯的 Claude Code 开源替代品。Claw-Code 和 Claude Code 属于“数据面的执行单元”，而 OpenHands 则是可以包含这些执行单元的“基础设施引擎”。OpenHands 的特殊之处在于其全面实现了 **ACP（Agent-Client Protocol）** 兼容 \[official-issue, cite: 40, 64\]。这意味着，OpenHands 的平台（Agent Canvas 和 Automation 引擎）不仅可以调度自研的智能体模型，还可以将第三方的闭源智能体（如 Claude Code、Codex）作为透明的 Backend 节点直接挂载并编排调度，其平台化野心远超传统的 CLI 框架。  
**核心技术栈解析**：

* **Agent Server 的本质**：它是整个 OpenHands 架构的心脏，一个基于 FastAPI 的 RESTful Python 服务，负责在指定的沙箱环境中监听前端或自动化引擎下发的指令流。它的设计支持延迟初始化和睡眠模式，随时待命以接管繁重的编译与运行任务 \[source-code verified, official-docs, cite: 33, 64\]。  
* **Session、Conversation 与 Workspace 的解耦管理**：在 V0 版本中，状态常常因意外崩溃而丢失。V1 版本将 Agent 和 LLM 设计为纯粹的 Pydantic 不可变模型（Stateless by default），系统中唯一的“状态”就是 Conversation 对象。这一变革彻底消除了状态漂移，实现了完美的 Deterministic Replay（确定性回放）和多分布式节点的会话接力 \[official-docs, source-code verified, cite: 36, 96\]。  
* **Workspace 多后端的无缝支持**：在沙箱机制上，V1 放弃了 V0 强制捆绑 Docker 的做法，改为“可选隔离（Opt-in Isolation）”。它定义了抽象的 BaseWorkspace 契约，并派生出三条执行路径：用于轻量级可信开发且适配本地 MCP 的 LocalWorkspace；自动拉起并销毁独立容器的 DockerWorkspace；以及通过 HTTP API 代理连接远程受控虚拟机的 RemoteAPIWorkspace \[official-docs, source-code verified, cite: 34, 97\]。  
* **SWE 场景适配与 Context Condenser**：作为针对软件工程（SWE-Bench）深度优化的引擎，代码库扫描极易触发上下文爆炸。OpenHands 首创了 LLMSummarizingCondenser 上下文冷凝器：当 Token 长度突破设定阈值，系统会自动启动一个小型 LLM 分析历史轨迹。它能精准提取用户原始意图和近几轮的代码变更，抛弃无用的反复纠错步骤，将耗资巨大的 O(N²) Token 增长曲线强行压平为 O(N) 线性增长，并且极度考究地对齐了 Prompt Caching 以避免缓存穿透 \[official-docs, source-code verified, cite: 37, 95\]。  
* **自动化平台与防御纵深**：在任务编排上，结合 automation 模块，OpenHands 可以监听 GitHub Issue 或 GitLab Webhook，当新的代码审查请求到达时，无头系统（Headless）会自动分配独立的 Workspace 处理任务并回推补丁 \[official-docs, cite: 38\]。针对安全风险，它在 SDK 层面内嵌了 SecurityRisk 多级风险分析引擎与 PolicyRails，通过 RBAC 和细粒度的容器管控构筑了极其厚重的安全纵深 \[source-code verified, cite: 60\]。

## **横向对比**

### **表 1：六项目总体定位对比**

| 项目 | 类型 | 核心定位 | 主要场景 | 技术栈 | 运行形态 | 最值得研究的架构点 |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **DeerFlow** | 状态图引擎类 | 通用长周期任务编排框架 | 耗时数小时的研究、分析与复杂生成 | Python / LangGraph | 后台服务 \+ 前端 UI | 基于 LangGraph 的多中间件链拦截与并发子智能体图编排 |
| **Hermes Agent** | 个人自进化类 | 记忆闭环的个人助理 | 跨日/周持续协作、多平台辅助 | Python / SQLite | 守护进程 / 桌面端 | L0-L2 渐进式自动技能生成技术与三层架构的持久化混合记忆系统 |
| **Claw-Code** | 本地 CLI 类 | 极速本地代码开发环境 | 极客级 IDE 旁路开发、代码库重构 | Rust / Python | 命令行终端 CLI | 极致优化的事件流状态机与依赖底层 Linux Unshare 机制的硬核沙箱 |
| **OpenClaw** | 平台网关类 | 多端互联消息总线控制面 | 20+ IM 平台泛在接入、个人全天候管家 | TypeScript / Node.js | 网关服务进程 | 跨 IM 平台的轻量级事件路由、设备节点接驳以及基于 ClawHub 的动态扩展 |
| **learn-claude** | 教学原理类 | 底层架构白盒脱水教程 | 开发者学习与研究 Agent 底层原理 | Python / Bash | 本地交互脚本 | “仅用少于 100 行代码实现核心执行循环”的剥离思想及基础记忆修剪（Snipping） |
| **OpenHands** | 平台化 SDK | 企业级软件开发（SWE）底座 | 自动化修复 Bug、CI/CD 深度集成与评测集打榜 | Python / React | SDK / Server / Web Canvas | **(高优)** 彻底的 Stateless 组件重构、完全解耦的 Workspace 体系与高效的上下文冷凝器（Context Condenser） |

### **表 2：Agent Loop 对比**

| 项目 | Loop 类型 | 是否状态图 | 是否事件驱动 | 是否支持 checkpoint | 是否适合 long-horizon tasks | 主要优点 | 主要限制 |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **DeerFlow** | 异步并发循环 | 是 | 是 | 是 | **高度适合** | 完美适配多步骤分解，任务失败可借助图机制优雅回滚 | 底层对 LangGraph 引擎依赖过重，系统资源消耗大 |
| **Hermes Agent** | 同步阻塞循环 | 否 | 否 (内部基于Callbacks) | 否 | 适合 (主要依靠记忆外挂) | 逻辑线性清晰，确保单会话执行步骤的绝对可靠 | 崩溃后无法精确恢复到工具执行过程中的中间状态 |
| **Claw-Code** | 状态机循环 | 否 | **强事件驱动** | 是 (依赖外部状态文件) | 不适合 | 响应极速无阻塞，发生任意崩溃均可从工作区 JSON 无缝重建 | 长程对话上下文管理能力相对单一，缺乏复杂规划跟踪 |
| **OpenClaw** | 异步回调循环 | 否 | 是 | 否 | 不适合 | Node.js 底层模型支撑极高并发的外部 IM 会话接入 | 执行层面缺乏复杂的长程规划与子步骤精细回溯追踪 |
| **learn-claude** | While 循环 | 否 | 否 | 否 | 极不适合 | 机制极度直观，易于开发者理解与深度魔改 | 仅具备演示性质，无工业级可用性边界防范 |
| **OpenHands** | 异步步骤循环 | 否 | **强事件驱动** | 是 | **高度适合** | EventBroker 事件总线贯穿始终，单点可变状态保证 100% 确定性回放 | 架构从 V0 升级到 V1 带来的重型组件迁移包袱尚未完全消化 |

### **表 3：Runtime / Sandbox 对比**

| 项目 | 执行环境 | workspace 隔离 | Docker / VM / cloud 支持 | 多租户能力 | 安全边界 | 适合场景 |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **DeerFlow** | 混合隔离环境 | Per-thread 虚拟路径挂载隔离 | 完美支持 Docker 与 K8s | 支持 (依赖 User ID) | 强 (容器级阻隔) | 企业内部团队级重负载分析研究任务池 |
| **Hermes Agent** | 混合环境 | 基于任务分配独立环境进程 | 支持 Modal, Daytona 等云端服务 | 弱 (面向单一用户设计) | 强 (外部引擎拦截 \+ 大模型评估) | 个人自建 VPS 私有化部署日常开发助理 |
| **Claw-Code** | 宿主机本地 | 仅限于文件系统权限约束 | 不支持 (强依赖主机本地 Namespace) | 无 | 中 (基于运行时三级权限) | 本地受极客完全信任的系统工程代码库开发 |
| **OpenClaw** | 宿主机本地 | 无强制物理隔离边界 | 不支持 | 无 | 弱 (仅依赖消息层接入鉴权) | 纯私有物理环境内网托管与控制面中转 |
| **learn-claude** | 宿主机本地 | 无任何隔离机制 | 不支持 | 无 | 极弱 (可轻易逃逸) | 虚拟机沙盒内的快速功能性学习与逻辑调试 |
| **OpenHands** | 抽象统一接口 | 通过多态 Workspace 类严格隔绝 | **完美支持** (具备热切换能力) | 强 (原生支持企业级组织结构) | 强 (容器物理隔绝 \+ PolicyRails 规则引擎) | 面向企业 CI/CD 自动流水线的安全漏洞修复与自动化仓库维护 |

### **表 4：工具与扩展系统对比**

| 项目 | 工具定义方式 | MCP 支持 | ACP 支持 | Skills / Plugins | Model provider 扩展 | 外部工具生态 |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **DeerFlow** | LangChain Tools 规范 | 支持 | 待验证 | 支持 (基于动态扫描 Markdown 文件) | 支持泛化 Provider | 一般，主要依赖字节系内置的高效搜推模块 |
| **Hermes Agent** | Python 装饰器辅以 Schema | **原生支持** | 支持 (可接入虚拟子智能体) | 支持 (执行后自主编写经验凝结) | 支持泛化多 Provider 池化 | 极度丰富，可通过终端直接调度各种存量 Python 脚本 |
| **Claw-Code** | 静态预编译的 Rust Trait | 开发中 | 待验证 | 无 (完全内置固化以追求速度) | 支持兼容架构 (Anthropic/OpenAI 等) | 较弱，强绑定于本地基础的 Shell 工具及文件系统工具 |
| **OpenClaw** | 声明式的 JS Schema 规范 | **强支持** | 待验证 | 支持 (依托巨大的 ClawHub NPM 生态包) | 支持泛化 Provider | **极强**，拥有专供个人事务处理的大量跨平台第三方插件库 |
| **learn-claude** | 极简字典名值映射 | 基础示例支持 | 不支持 | 不支持 | 仅支持硬编码接入配置 | 贫乏，完全仅作教学代码演示 |
| **OpenHands** | 面向对象的 Python Class 继承 | **强支持** | **完美兼容** | 支持 (依赖统一的 Plugin Registry) | 支持 (利用 LiteLLM 代理一切网关) | **极强**，覆盖海量高阶 SWE 工具与专业的评测集探针 |

### **表 5：记忆与上下文管理对比**

| 项目 | 短期压缩 | 长期记忆 | 会话恢复 | 项目记忆 | prompt caching | 独特机制 |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **DeerFlow** | 支持 (触发拦截) | 支持 (防抖动抽取) | 支持 | 弱 | 待验证 | 通过动态限制载入 Token，优先保护子工具执行对与高频技能不受阶段性截断的影响 |
| **Hermes Agent** | 支持 | 强 (FTS5全文搜索 \+ Milvus向量搜索) | 支持 | 支持 | **极度优化** | 将 Prompt 组件顺序绝对固化并拒绝中途重装，极大限度博取底层大模型的 Cache 命中率以降低成本 |
| **Claw-Code** | 支持 (auto\_compaction) | 无内置机制 | 强支持 | 支持 (注入 CLAUDE.md) | 待验证 | 针对特定路径的代码段，使用滑动窗口自动进行局部摘要替换，以实现流式日志精简 |
| **OpenClaw** | 较弱 | 外部挂载如 DuckDB | 弱 | 支持 (注入 AGENTS.md) | 待验证 | 根据来源渠道的不同智能隔离和索引对话记忆碎片，避免不同 IM 的话题污染 |
| **learn-claude** | 粗暴剔除机制 | 无 | 否 | 弱 | 无 | 为初学者展示了如何剔除大块中间废话而只保留首尾意图的原理 |
| **OpenHands** | 强 (ContextCondenser) | 需结合外部存储 | 强支持 | 支持 | 高度优化 | 部署独立小模型担任上下文“冷凝器”，自动过滤掉多轮无效 Debug 循环记录，将 Token 开销降级至线性 |

### **表 6：HITL 与安全模型对比**

| 项目 | 审批方式 | 危险操作检测 | 权限模型 | 多用户/多端授权 | sandbox 依赖程度 | 主要风险 |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **DeerFlow** | 预留任务看板的 Plan 模式供人为把控 | 薄弱 | 基于任务的粗放型管控 | 支持 (通过租户权限下发) | **极高** (安全完全依赖底层的 K8s 屏蔽) | 并发繁多的子 Agent 在长周期中如果缺乏干预，可能耗尽系统 API 预算 |
| **Hermes Agent** | CLI / Web TUI / IM 多端随时打断审批 | **极强** (结合正则表达式与 Tirith 第三方强扫) | 细粒度操作级拦截模型 | 弱 | 低 | Smart 模式基于小模型预判，面对精心构造的复杂 Prompt Injection 可能出现防范穿透漏洞 |
| **Claw-Code** | 本地终端原生拦截提示 | 中度 (内置目录写保护检测) | 静态的三级安全放行模式配置 | 无 | 中等 (强依赖 Linux 内核级的 Namespace 划分) | 在非 Linux (如 macOS) 平台上缺乏原生底层防逃逸能力支持 |
| **OpenClaw** | IM 消息推拉触发异步确认 | 薄弱 | 粗粒度的对话发起人身份核验鉴权 | 支持 (配备专门的 DM 配对扫码控制) | 低 | 长期暴露在公网 IM 的接收节点上，若网关鉴权机制受攻击则整台主机的控制权将会彻底沦陷 |
| **learn-claude** | 简单的命令行输入挂起等待 | 毫无检测 | 无任何鉴权 | 无 | 无 | 在真实环境运行中可被模型轻易误操作删除系统核心文件目录 |
| **OpenHands** | 专属 Canvas 面板中的工作流审批节点 | 强 (内嵌复杂的 PolicyRails 多维度规则验证引擎) | 基于 RBAC 的系统化访问与企业级组织权限链条 | 支持 | 极高 | 部署规模引发的组织级别集群核心密钥管理不当或因容器被横向逃逸攻击 |

### **表 7：平台化趋势对比**

| 项目 | CLI 化 | SDK 化 | Server 化 | Web UI / Canvas | Automation | Cloud/多租户 | 平台化成熟度 |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **DeerFlow** | 弱 | 中等 | 强 | 提供定制的 React 大后台控制监控界面 | 支持 | 中等 (适合企业部门级组队部署) | 高 |
| **Hermes Agent** | 强 | 中等 | 弱 | 构建了 Electron 极客桌面工具与进阶终端界面 | 提供基础的 Cron 自动循环定时器 | 弱 | 中等 (产品形态强偏向于单机 C 端高净值开发者用户) |
| **Claw-Code** | 极强 | 极弱 | 极弱 | 完全摈弃 | 需依赖第三方的控制面进行外部轮询调用 | 无 | 低 (战略上刻意保持本地基础操作工具流的极致纯粹) |
| **OpenClaw** | 弱 | 中等 | 强 | 提供集成的 Web 云端设备节点管控面 | **原厂支持**丰富的 Webhook 钩子 | 弱 | 中等 (技术架构偏向网络层面的消息代理中转枢纽) |
| **learn-claude** | 强 | 弱 | 弱 | 无 | 没有任何相关支持 | 无 | 零 (纯科研与教学研究用物) |
| **OpenHands** | 包含基础版 | **极其完善** | **极度健壮** | 拥有完整的 Agent Canvas 生态前端矩阵 | **强** (实现与 GitHub 自动化流程的重度绑定) | 强 | 极高 (技术底座已成熟孵化出可商业化扩展的大型 SaaS 产品生态线) |

## **架构分类法与未来融合演进**

基于对这六个代表性项目的深度解构，可以对当前纷繁复杂的 Agent Harness 赛道提出一套精准的五维架构分类法。这五大类别的边界并非绝对对立，而是针对特定问题域演化出的“适者生存”形态。

1. **Graph-oriented long-horizon harness (图状态机重负载引擎)**  
   * **代表**：DeerFlow。  
   * **核心抽象**：流式的并发状态图（State Graph），一切处理步骤均被抽象为图中流转的实体节点。  
   * **最适合任务**：海量图文归纳、极长上下文深度研究、多工种混合（爬虫+写代码+画图表+排版）的长周期并发生成。  
   * **典型风险**：框架体积极度沉重，状态流转排错困难，且系统资源占用极为夸张。  
2. **Memory-evolving personal agent harness (记忆闭环个人智体)**  
   * **代表**：Hermes Agent。  
   * **核心抽象**：记忆沉淀体（Episodic & Procedural Memory）。执行引擎的设计是为累积经验而服务的，追求长期价值。  
   * **最适合任务**：伴随极客用户长期成长、自动化记录非标准化个人操作流程的经验固化。  
   * **典型风险**：记忆数据库随时间线急剧膨胀，且劣质经验一旦被错误固化为默认技能，将会污染模型的执行路径。  
3. **Local coding CLI harness (本地代码极速命令行支架)**  
   * **代表**：Claw-Code。  
   * **核心抽象**：底层事件流（Event Stream）与轻量化本地系统 API 调用层。  
   * **最适合任务**：受控安全目录下的零延迟代码批量重构、单测极速生成、纯键盘操作。  
   * **典型风险**：严重缺乏真正的云原生强物理隔离机制，对危险指令的拦截极度依赖本地用户的专业安全敏感度。  
4. **Multi-device control-plane harness (多端互联控制面网关)**  
   * **代表**：OpenClaw。  
   * **核心抽象**：异构网络节点下的统一消息总线（Message Bus & Gateway）。  
   * **最适合任务**：全天候移动办公随时指派任务、多碎片化即时信息流的处理整合。  
   * **典型风险**：对外网的暴露攻击面无可避免地过大，系统底层容易在短时间内被超大容量的并发垃圾信息洪流彻底阻塞打垮。  
5. **Platform-oriented SWE agent harness (软件工程云平台抽象底座)**  
   * **代表**：OpenHands (V1)。  
   * **核心抽象**：全面解耦的组件依赖树（Stateless Agent \+ 可替换的 Remote Workspace \+ Event Broker）。  
   * **最适合任务**：工业界企业内源仓库的 CI/CD 管道深度无缝对接、夜间自动化拦截与修复 GitHub 高危漏洞 Issues、横向团队级的安全基线代码大面积审计。  
   * **典型风险**：部署技术栈严重依赖重型的各种云平台资源后端（Docker容器调度池、外部 LLM 节点管理群等），前期旧代码的研发接入改造具有极大的阵痛摩擦力。

**演进与融合的终局预判**：  
未来上述五种分类的边界将会加速消融。最终的工业级形态将是：底层的 **"数据面/计算面"**（继承 Claw-Code 与 OpenHands 的核心）负责沙箱内极致的安全与计算并发；上层的 **"控制面"**（吸收 OpenClaw 经验）全权接管泛在终端设备的协议认证与负载路由；而在中场的任务规划中枢，则交由 **"编排系统"**（融合 DeerFlow 的图理论机制）去进行细粒度跨组件调度；这一切的外围，包裹着持续更新的 **"记忆体"**（Hermes 路线）。

## **当前趋势判断**

结合资料交叉比对，关于当前 Agent Harness 的演进脉络，可总结出以下四个高度成熟且不可逆转的技术趋势：

1. **全面走向系统级 SDK 化与组件无状态化（Stateless）**  
   胖客户端（Fat Client）CLI 工具已触及发展的天花板。未来的发展要求核心能力必须下沉并完全抽离至无状态的 SDK 层中（例如 OpenHands 果断重写了其 software-agent-sdk）。核心计算引擎（Agent/LLM）禁止持有任何可变的局部业务变量，所有的多轮交互状态被收束至单独的 Conversation 数据总线对象中。这一彻底的重构直接打通了向大规模云端多租户集群及分布式 Server 端点部署的演进之路 \[official-docs, cite: 36\]。  
2. **沙箱隔离的“强制解绑”与“接口级动态适配化”**  
   在 V0 的上古蒙昧时期（如早期 OpenDevin），业界强制让所有的工具调用都进驻沉重的 Docker 集群。这种粗暴的设计引发了灾难性的通讯性能衰减与不同子系统间状态的不断撕裂漂移。现代的顶级架构（以 OpenHands V1 和 DeerFlow 为代表）已全部迭代为精密的抽象接口挂载模式（BaseWorkspace / SandboxProvider），它能够智能评估当前负荷，做到在 Host 本地直跑、Docker 进程派发、或是 K8s Pod 集群远端热插拔之间瞬时平滑热切换 \[official-docs, source-code verified, cite: 34, 69\]。  
3. **MCP / ACP 协议正式登顶为“行业通行世界语”**  
   MCP（Model Context Protocol）标准化已经完成跑马圈地，无论是 Hermes, OpenHands 抑或是 OpenClaw 均将其纳入最优先级的核心构建组件序列之中。更具颠覆性的是 ACP（Agent-Client Protocol）标准异军突起——它打破了“智能体只是大模型增强品”的刻板印象。如今，类似于 OpenHands 或 Agent Canvas 这样的底层控制台，可以轻易凭借 ACP 协议实现将任何第三方已调优的成品智能体大系统（例如商业版 Claude Code 等）直接像积木一样挂载在其后端被动态嵌套调度 \[official-issue, cite: 40, 64\]。  
4. **长程上下文防爆策略由“生硬截断”向“精细化语义冷凝”跃迁**  
   对于处理数万行级项目的长周期（Long-horizon）任务而言，仅依靠滑动窗口抛弃顶部历史数据的传统做法，等同于变相将上下文切断并引发模型逻辑崩溃。主流前沿技术路线已锁定为使用专用独立的小模型构建 **Context Condenser（语义冷凝器）**：比如在 OpenHands 的 LLMSummarizingCondenser 组件中，它会精密地在 Token 洪峰来临前夕，过滤掉冗杂的多轮重试操作日志记录，将其中真正的关键意图高度抽象化后注入主进程。这一冷凝提炼技术能够将惊人的 O(N²) 二次级数 Token 消耗曲线强制硬拉压平为近乎完美的 O(N) 线性平缓增长斜率，同时更兼顾了不打破底层 LLM Prompt Caching 命中缓存前缀的精微平衡策略 \[official-docs, cite: 37\]。

## **OpenHands 加入后的新认识**

引入新增项目 OpenHands 并进行重点剖析后，带来了全新的破局视点，推翻了早期单纯评估五大项目的局限认知：  
首先，针对“OpenHands 是否等同于又一个本地 Claude Code 复制品？”的疑问，答案被明确证伪。Claude Code 或 Claw-Code 本质上依然围绕终端极客提供深度集成的 CLI 服务外壳。而经过 V1 烈火洗礼后的 OpenHands，其立命之本早已脱离具体执行体，跃升为面向大型开发组织的底层基础设施底座平台。它通过标准化的 RESTful API 挂载任何异构后端智能体，志在全盘接管并重塑整个企业的工程自动化开发流转系统。  
其次，体现出对**架构“分形抽象（Fractal Abstraction）”设计**的工程启示。在彻底抛弃可变状态耦合与死锁陷阱后，OpenHands 对一切资源的解耦分离已经做到了极致：完全解构剥离出了负责后台任务流转调度的独立的 Agent Server 守护层；分离出了专司界面协同展示并可让多个运维开发工程师同屏跨地域实时交互追踪 Debug 修复进程的 Agent Canvas 交互面系统。这一前沿技术理念不仅对原有的终端孤岛 CLI 模式构成了多维度的降维打击，更深刻指示了我们在随后着手进行企业级自有平台自研改造时所必须遵循的首要红线铁律——绝不在调度总枢纽处残存任何局部执行状态堆栈。

## **高可信结论**

* **\[source-code verified\]** OpenHands V1 已经彻底颠覆了过往的庞大耦合架构，全面达成了组件的无状态化分离重构，其全新的 software-agent-sdk 完全抽离了底层通信框架与 UI/Server 业务逻辑层。  
* **\[official-docs\]** 在面对复杂的并发隔离防污染诉求时，无论是大厂出品的 DeerFlow 还是开源中坚的 OpenHands，皆高度默契地采用了一致的系统接口化隔离抽象方案，全面实现了针对 Local/Docker/集群虚拟环境资源的平滑挂载与瞬间热切换支持。  
* **\[source-code verified\]** 聚焦极限响应的 Claw-Code，其架构内核虽然呈现为一具事件驱动状态机与极强 Rust 协程执行网络，但其防逃逸沙箱深度紧密捆绑并严重依赖 Linux 内核级的底层 unshare 进程隔离机制，在 macOS 及 Windows 异构跨平台上无法实现等同量级的系统级别硬件强隔离防线。  
* **\[official-docs\]** Hermes Agent 架构中存在独步赛道的前沿理念——它是迄今被验证的极少数能够在核心引擎代码构建源头，即原生把“将失败经验进行闭环自动反思萃取并转化为持久态系统技能”作为首要运转目标的个人 Agent Harness 系统，其 L0 至 L2 级别的梯队递进式技能组动态加载策略展现出显著的性能红利与算力节省优势。

## **待源码核验结论**

* **\[inference / 待源码核验\]** 致力于充当无界超级连通网关的 OpenClaw，其面向移动终端及 Web 的 WebSocket 全天候暴露点群，是否已经内嵌了足够强韧且底层的防中间人篡改攻击过滤机制与防止泛滥假消息伪造重放机制，以守护系统内核资源池不被意外冲爆。  
* **\[official-issue / 待源码核验\]** 正在主线开发分支激进演进中的 Claw-Code，其处于实验研发规划节点内的 MCP 标准协议接入适配层，在极度注重并发性能的 Rust 组件桥接层面上，是否真能毫无瓶颈阻力地稳健穿透并支撑起大量重载第三方异构外部子插件及复杂业务环境即插即用型交互的吞吐并发考验。  
* **\[third-party / 待源码核验\]** Hermes Agent 架构通过强行拼接独立于主引擎的外置 Milvus 大规模内存检索组件，以此来试图弥合及接盘 FTS5 全文倒排索引面对极端跨越式对话下由于上下文断层产生的匹配流失失败的混合架构。这种操作所直接诱发增加的针对复杂长文内容切割与海量嵌入（Embedding）向量即时生成的连带运算开销成本边界究竟在哪里，还需在千万级 Token 量级的生产压测场景下被实地测算和深入扒出。  
* **\[inference / 待源码核验\]** DeerFlow 在极重度的任务拓扑处理中调度引发极其庞大且层层深套的并发派发嵌套子智能体（Nested Sub-Agents）调用簇时，如果处于执行链路最远端的叶子节点子智能体发生未知异变而引发逻辑死循环甚至无限自我递归报错洪流，处于中心调控位置的 LangGraph 引擎总线及其配套配置好的 Error Boundary（异常抛掷捕获圈套）等关键保护措施，究竟是从何种精确的链路反向传递点上实现防雪崩级别的跨节点优雅软着陆切断与熔断保护截流。

## **后续自研文档建议**

本详尽调研报告应直接入库至名为 Harness Study 的专属核心技术研究仓库中，作为架构重组战略与核心基建选型演练阶段至关重要的前置基础数据基座（Base）。为了能在实操阶段精准吸收各类优势特性并快速赋能落地产出，建议必须且立即围绕以下核心方向展开精细度更进一层的架构拆解专题梳理：

### **1\. 应拆分出的 Comparison 专题**

* **【专题一】应对极度 Context 膨胀灾难下的无损提炼对抗网络研究**：重点实施深入比对解析，将 OpenHands 提供的精细化自动梳理提纯抽象算法体系 LLMSummarizingCondenser，与直接被装配进主截流关卡内的 DeerFlow 型 SummarizationMiddleware 处理手段放入同一尺度下的源码级别显微镜中相互攻防映射剖析。  
* **【专题二】应对穿透型入侵下的沙箱壁垒与宿主异构通讯防范设计**：横向对比探究 OpenHands DockerWorkspace 基于 HTTP Proxy 的内网穿透隔离防范机制，与依靠底层系统级权限屏障并透过底层匿名管道（Pipes）硬通的 Claw-Code unshare 隔离网技术，二者在不同高危阻击战役场景下究竟哪种隔离粒度架构的护城河壁垒与抗逃逸攻击冗余容限更为完美和无懈可击。  
* **【专题三】MCP 协议与更高阶 ACP 子总线接驳底层报文全息解析实战**：重点提取抓取捕获各系统框架底层在遭遇及对接收纳大型 FastMCP 重载节点或是尝试远程跨层调度其他 ACP-compatible 成品大模型 Server 端口阵列群时，其主引擎负责路由中继传输与底层二进制报文格式解包包装重构拼装机制的最深层底层算法优化路径。

### **2\. 应补充的 Projects 纵向研读笔记**

* **针对 OpenHands software-agent-sdk 中枢组件的最核心模块代码实施无死角地毯式精读**：尤其是聚焦于透彻理解其基于 Pydantic Models 所重度设计的极度精美的不可变强类型对象（Immutable DTO）架构状态机设计理念，并将其如何协同 EventService 的异步非阻塞高并发事件路由监听总线共同奏响出“绝对不串流漂移状态管理机制”的全过程底层细节逻辑。  
* **对标挖掘 Hermes Agent 系统内的“自我成长闭环觉醒技术”反思源码拆解机制图谱**：必须极度详细地逐代码段深入溯源并建立其自始至终——从监控工具运行成败结果截获，到利用反思模型展开精准逻辑评估，再到最终如何彻底实现通过调用底层 skill\_manage 把新凝结沉淀萃取出来的优质操作动作树自动化完整转写拼合固化进宿主机 Markdown 技能实体库里的整个全生命周期完整流转机制细节画像。  
* **透视解构 DeerFlow 巨型重器那引以为豪的 9 连环高强度防线 Middleware 链网阵列的驱动引擎枢纽源码**：彻底解剖分析并掌握这足足高达九个维度的中间件阻绝隔离保护过滤网罩（包含但不限于日志拦截、权限抽查、上下文强减重切割处理等），到底是依照着何种精密高效的时序优先级在每一步沉重的 LangGraph 巨量节点流转触发前，成功实现精准插入打断操作、安全数据抽取提取以及强行执行向 Prompt 隐性暗槽系统深处精准投毒（注入业务信息流参数）的控制流精妙技法。

### **3\. 应进入 Synthesis 的架构模式**

在充分汲取总结上述六家顶级前沿开源项目的所有成败血泪核心工程化教训经验后，建议在即将要启动着手铺开自研大型 Agent Harness 系统核心框架主干时，必须无任何退路地强制遵循采用以下融合杂交提纯出来的顶层黄金组合架构演进指导蓝图作为最终行动纲领准则：

* **底座地基层**：严苛地全部全面套用吸收借鉴 **OpenHands 那套经过了最严酷的大规模重构洗礼验证后的解耦分离结构哲学思想（独立彻底的无状态抽象 SDK 库配合极致健壮的 Stateless Event Server 异步并发执行服务引擎单元）** 作为坚不可摧的地基承载系统底座防线。  
* **核心挂载层**：在高阶引擎逻辑处理链路的中枢位置，引入摘取 **Hermes 系统对于长线记忆分层分类机制和具备长效长尾效应自我演进生长（进化）能力的强自适应反馈控制层技术** 作为主干中间件外脑插件。  
* **边界交互层**：而在对外向海量移动互联乃至公网异构弱网接入设备主动对外进行广泛接口暴露及信号覆盖触达时，则全盘承袭挪用 **OpenClaw 的极具弹性的全域多活集群级横向扩张扩容网络分发中控网关（Gateway）集联打通接入设计逻辑路线思想** 作为对外防波堤前沿哨所堡垒端点群。  
* **重载指挥层**：当真正迎面遭逢面对内部爆发超巨型深度业务逻辑解算压力流、需要展开实施大面积多轮高危险超大规模步骤分解编排、同时伴随需要超大批次异步并行启动大量子智能体兵团执行海量数据深加工繁重高精尖业务挑战的极限高压实战时，随时切换并唤醒呼叫部署 **DeerFlow 所极度擅长的子系统并行流转分派与通过有向无环图（DAG）精准进行统筹调度的多核并联阵列引擎模式** 来彻底接管压制并梳理编排出最完美的任务攻坚执行队列。