# Agent Harness 架构对比分析

> **日期**: 2026-06-30 | **状态**: research-base | **来源**: Deep Research 报告
>
> 本文是对 DeerFlow、Hermes Agent、Claw-Code、OpenClaw、learn-claude-code 五个 Agent Harness 项目的全景式架构对比，作为本仓库后续自研文档的调研 Base 底稿保留。文中判断需要在后续专题笔记中回到 submodule 源码与官方文档逐项核验，不视为最终源码结论。

## **执行摘要**

随着大语言模型（LLM）推理能力的指数级跃升，人工智能的工程前沿已不可逆转地从“基础模型调优”向“系统外壳（Harness）构建”发生转移。模型提供了感知与推理的原生智力，而 Agent Harness 作为承载这些智力的运行时外壳，决定了代理系统在真实物理或数字环境中的执行边界与鲁棒性。本报告针对开源社区中当前最具代表性、架构设计最为成熟的五款 Agent Harness 项目进行了全景式深度解构：由字节跳动推出的长周期复杂任务编排框架 **deer-flow**、Nous Research 打造的具备跨平台通信与技能自进化能力的 **hermes-agent**、UltraWorkers 团队采用 Rust 语言极致重写的终端原生高性能外壳 **claw-code**、基于 TypeScript 与分布式 WebSocket 网关构建的多设备中枢 **openclaw**，以及 ShareAI Lab 专门用于解构 Agent 运行时原理的全景式基准教学项目 **learn-claude-code**。  
通过对这五大项目在架构总览、主循环机制、沙箱隔离、安全模型、记忆工程等十五个核心维度的详尽剖析，本研究揭示了智能体架构演进的深层脉络。当前的架构设计正在经历从单一的线性同步阻塞调用向基于状态图及并发队列的异步事件驱动模式跃迁；系统提示词（System Prompt）的臃肿堆砌正被动态按需加载的技能（Skills）与模型上下文协议（MCP）所取代。这些开源项目不仅展示了各自针对不同业务场景的工程权衡，更共同勾勒出了未来准操作系统级（OS-level）Agent 基础设施的技术雏形。

## **逐个项目深度分析**

### **1\. deer-flow (ByteDance)**

#### **1.1 架构总览**

deer-flow 作为一个面向长周期（Long-horizon）复杂任务的超级智能体外壳（SuperAgent Harness），其整体架构呈现出严格的分层解耦设计。底层由 deerflow.\* 命名空间构成的可发布 Harness 包承载了所有的核心代理逻辑，涵盖编排器、沙箱控制、工具管理与记忆系统；上层由 app.\* 构成的应用程序代码则提供了基于 FastAPI 的网关服务、Nginx 反向代理以及 Next.js 驱动的 Web 交互界面1。架构的核心中枢深度绑定了 LangGraph 状态图引擎，将代理的交互过程转化为具备检查点（Checkpoint）和断点恢复能力的状态机，使得其能稳健地处理耗时数十分钟甚至数小时的深层次研究与代码生成任务3。

#### **1.2 Agent 主循环（核心执行周期）**

在主循环机制上，deer-flow 的核心流转由 LangGraph 的图节点跃迁驱动。主入口点定义在 make\_lead\_agent(config) 函数中，该函数在每次图状态初始化时，会依据 RunnableConfig 配置动态组装出一条包含 9 层逻辑的中间件链（Middleware Chain）4。当用户输入抵达时，状态机依次穿透数据目录初始化、文件上传处理、沙箱资源获取以及上下文压缩等中间件，最终进入核心代理模型节点。模型节点依据当前上下文判定是否输出最终答案抑或触发工具调用（Tool Calls）。若触发工具调用，执行流程将挂起大模型生成，进入安全的沙箱内执行对应的 Bash 或 Python 指令，随后将带有执行反馈的工具消息（ToolMessage）重新注回状态机，由此驱动下一轮次的状态迭代1。

#### **1.3 工具调用系统**

工具调用层集成了内置能力、开源社区扩展以及标准化协议。系统原生提供了诸如 read\_file、包含针对大模型优化的长文本替换能力的 str\_replace 以及受控的 bash 执行终端1。为防止大语言模型在多参数工具调用时出现格式混淆，系统对工具描述进行了专门重构，例如将文件路径（path）与内容（content）置于最前以适应不同模型的输出偏好7。更具前瞻性的是，deer-flow 深度融合了模型上下文协议（MCP），支持通过根目录的配置文件以 HTTP/SSE 或 stdio 模式无缝挂载包含 OAuth 自动令牌刷新功能的外部 MCP 服务器，从而实现了系统能力边界的无限外扩8。

#### **1.4 沙箱 / 执行环境**

针对代码执行的不可控风险，deer-flow 确立了极高工业标准的三层沙箱虚拟化体系。最基础的 LocalSandboxProvider 允许命令直接在宿主机运行，通常仅限于开发调试；生产环境默认激活的是基于容器隔离的 AioSandboxProvider，该提供者为每一个并发线程分配独立的 Docker 实例，并在实例内部映射了专用的 /mnt/user-data/ 虚拟工作空间，包含隔离的上传目录与输出目录1。对于需要应对极大规模并发请求的企业级多租户场景，框架进一步提供了 Kubernetes 供应器（Provisioner）模式，使得沙箱环境可以在宿主集群中被动态编排与弹性伸缩6。在应对容器冷启动导致的瞬间网络断开异常时，沙箱驱动内建了重试机制与严格的 /v1/sandbox 三次健康探测逻辑，极大提升了环境供应的韧性11。

#### **1.5 权限与安全模型**

除了依赖底层容器隔离外，框架在应用程序逻辑层引入了名为 Guardrails（安全护栏）的预调用（Pre-Tool-Call）鉴权模型。这一防御层运行在工具被真实触发之前，针对特定高危操作进行正则表达式与特征模式拦截，例如硬编码阻断包含 rm \-rf 的恶意命令或防止路径穿越攻击4。当 Guardrail 捕获到越权操作时，它并非简单地抛出导致系统崩溃的异常，而是将拒绝理由打包为 status="error" 的工具消息反馈给大语言模型，促使模型自行纠错与重新规划12。对于并发的文件写入操作，底层更是在 (sandbox.id, path) 粒度上实现了读改写序列化锁，防止了并发破坏1。

#### **1.6 人机协同（HITL）**

人机协作在 deer-flow 中主要依靠 ask\_clarification 工具及处于中间件链末端的 ClarificationMiddleware 实现。当智能体在多步执行中遇到模糊语义、权限索要或达到预设决策断点时，会主动调用该澄清工具。此时，中间件通过返回特定的终止命令（goto=END）中断 LangGraph 的图流转，将包含澄清问题的交互界面推送至前端。只有在人类操作员通过界面补全必要信息后，被序列化的系统状态才会被重新唤醒，状态图将从中断节点安全恢复并继续推进长周期任务4。

#### **1.7 记忆与上下文管理**

记忆系统设计摒弃了同步阻断式的数据更新，采用了带有 30 秒去抖（Debounced）机制的异步提取队列。系统在后台调用轻量级模型对历史对话进行语义剥离，提取出带有置信度分数的用户职业偏好、工作习惯等结构化事实并存入本地 JSON，单用户最高可存储 100 条高置信度事实1。在应对当前对话上下文膨胀的问题上，SummarizationMiddleware 提供了一种自适应的滑动窗口截断方案。当上下文 Token 数或消息比例触碰警戒阈值时，触发大模型的历史消息归纳。尤为精妙的是该中间件内嵌的“技能救援（Skill Rescue）”逻辑，在抹除长文本前，系统会优先将近期加载的技能指令从旧会话中提取出来拼接到最新窗口，确保智能体在压缩记忆后不会遗忘当前执行规范15。

#### **1.8 中间件 / 拦截器管道**

框架采用了横向切面编程（AOP）思想，通过有序的拦截器管道解决横切关注点。在 make\_lead\_agent 装配阶段，系统依次挂载 ThreadData（目录准备）、Uploads（多模态解析）、Sandbox（容器挂载）、Summarization（Token 压缩）、TodoList（规划监控）、Title（标题生成）、Memory（记忆抽取）、ViewImage（视觉前处理）与 Clarification（人机对齐）共九大核心中间件1。开发者还可以遵循 AgentMiddleware 接口，在配置文件中向管道顶部无缝注入自定义的鉴权或审计中间件，彰显了极佳的开放性16。

#### **1.9 多 Agent / 子 Agent 系统**

通过 SubagentExecutor 模块与 task\_tool.py 的结合，主导智能体（Lead Agent）获得了动态裂变的能力。在面对具有挑战性的研究课题时，主智能体能够即时派生出专门负责代码分析、数据检索的隔离子代理。每个子代理拥有全新的对话上下文空间、重置的 Token 计数器以及独立的任务终止条件17。受限于早期 LangGraph 线程池阻塞等待的局限性，框架正积极筹备向基于 A2A（Agent-to-Agent）协议的事件驱动范式演进，以期实现子代理运转过程中主节点不被冻结，从而支持更深层次的迭代细化工作流19。

#### **1.10 状态管理**

由于深度集成了 LangGraph 框架，系统的状态管理极其严密且可溯源。所有并发工具和代理节点产生的副作用均被收敛至 ThreadState 数据模式中。为了支持重放（Replay）及人工干预，系统利用 SqliteSaver 检查点机制在每一次图节点变动后将状态树序列化并落盘16。这种不可变的追加状态机制不仅消除了并发写导致的数据竞争幽灵更新，也使得前端用户界面能够精准渲染长达数小时任务中的任意中间快照21。

#### **1.11 事件与流式系统**

在通信边界上，后端 FastAPI 通过 Server-Sent Events (SSE) 协议实现了工业级的实时可观测性。底层的模型输出、工具运行进度、甚至是容器资源使用警告都被转换为标准化的事件流推送至前端。通过严格的状态字典分离与事件派发，系统能够平滑处理涉及视觉图像识别（Vision）和链式思维（Thinking）字段在不同 LLM 厂商 API 间非标准实现的兼容转换1。

#### **1.12 任务与调度系统**

针对微观任务，Pro 模式引入的 TodoListMiddleware 提供了一种自上而下的思维拆解策略，模型利用 write\_todos 工具自主维护 pending、in\_progress 与 completed 状态的检查清单，使用户能直观监督进度23。在宏观调度层面，框架结合 APScheduler 引入了原生的 Cron 定时系统机制。用户在 YAML 中声明诸如“每日监控数据库状态”等表达式后，网关会依约启动隔离的背景智能体执行任务并最终反馈，极大扩展了系统在运维自动化场景的想象空间24。

#### **1.13 可扩展性与插件系统**

该框架推崇声明式的轻量扩展，最核心的体现即为技能（Skills）体系。技能本质上是被存放于 skills/custom 目录下的 Markdown 文件，包含执行逻辑、工具链声明与参考范例25。当主循环检测到特定语义触发时，才会将技能内容按需加载进系统提示词。除了基于 MCP 的外部集成外，配置文件 config.yaml 也暴露了对任意符合 LangChain 标准的外部 LLM 接口及大语言模型变体的热插拔支持6。

#### **1.14 错误恢复与韧性**

在处理脆弱的网络通信与不稳定的 LLM 输出时，系统体现了极强的容错设计。除上文提及的沙箱断连指数级退避重试外，若调用工具时遗漏必填参数，解析器将通过抛出内部 GraphBubbleUp 异常拦截并提示 LLM 重塑参数，避免直接陷入无穷死循环7。当大模型的推理触发上下文熔断或 JSON 格式崩坏，管道底层能够利用LangChain的补偿机制平滑注回异常 Traceback 供模型自行理解消化。

#### **1.15 提示词工程与系统提示**

框架采用了动态提示词组装策略，而非硬编码长文本。通过向 System Prompt 中动态注入 \<todo\_list\_system\> 规划规则、最新提取的用户上下文库、已激活的特定技能文件内容，系统能够在每一轮交互时自适应地平衡信息密度与背景噪声1。同时兼容各类推理模型（如 Qwen-Plus 等），使得高级思维与工作流控制通过专用的元标签进行了有效解耦3。

### **2\. hermes-agent (Nous Research)**

#### **2.1 架构总览**

Hermes Agent 是一款以“跨平台连接”与“持续自进化”为核心设计目标的自治人工智能外壳。其整体架构以极其内聚的 AIAgent 循环控制引擎为中枢，向外扩展出一套高度抽象的网关（Gateway）适配器系统。这套系统使其能够无缝挂载于命令行终端（CLI）、基于 Ink 框架的终端用户界面（TUI），以及高达 20 余种主流企业或社交即时通讯平台（包括 Slack、Discord、WhatsApp、Telegram 等）。这种剥离了重度云端依赖的精巧设计，允许它部署在低至 $5 成本的轻量级虚拟专用服务器（VPS）或是能够随需休眠的 Serverless 容器架构中27。

#### **2.2 Agent 主循环（核心执行周期）**

它的运行骨架是一个单体同步编排的事件泵，主要由 run\_agent.py 文件中的 run\_conversation 生命周期主导。每当用户输入抵达时，主循环依次经历任务 ID 生成、历史记录挂载、基于 prompt\_builder.py 的提示词动态合成、容量超过 50% 时的前置压缩检测，最后组装 API 消息体进入 \_interruptible\_api\_call 进行大语言模型轮询30。系统强制推行严格的 User \-\> Assistant \-\> Tool \-\> Assistant 交替逻辑，并在工具执行完毕后迅速回调启动下一个子迭代，整个过程直至达到任务完毕或迭代预算枯竭方告终止。

#### **2.3 工具调用系统**

在此框架中，工具层针对各 LLM 厂商不同格式标准进行了名为 ProviderTransport 的深度抽象改造。传输层接管了信息转换、工具字典格式化与请求参数构建（如针对 Anthropic、OpenAI、Bedrock 等异构后端的抹平），使得上层逻辑只需关注标准的 role 与 content 解析28。系统原生集成浏览器自动化控制、视觉多模态分析以及通过模型上下文协议（MCP）实现的一键挂接外部工具库等能力32。

#### **2.4 沙箱 / 执行环境**

相比强制依赖单一容器方案，Hermes 提供了异常灵活的执行环境插拔选项。开发者可以根据安全容忍度与运算需求，通过简单的命令行配置（hermes config set terminal.backend），使其运行在宿主机本地环境、被加固的 Docker 实例中，或者通过 SSH 直接跃迁至远程高性能计算集群。更为极致的是，系统还支持 Singularity、Daytona 与 Modal 等无服务器化计算底座的支持，满足了多样化的生产力场景27。

#### **2.5 权限与安全模型**

权限管理采取了纵深安全防护哲学。在网络接触面，针对网关引入了严格的直接通信请求（DM Policy）拦截，未知访问者必须通过临时 8 位配对码验证方可唤醒智能体服务；在执行纵深，它规避了虚假的系统阻断，引入了分层权限架构雏形，即将系统所有者（Owner）、管理员（Admin）、操作员（User）与访客（Guest）赋予不同级别的文件访问与终端口令通行能力。所有在容器边界内或外触发的操作都受到这种白名单体系的严格规管35。

#### **2.6 人机协同（HITL）**

该项目中最引人注目的 HITL 实现是其危险命令审批（Command Approval Workflow）机制。系统内置了针对潜在破坏性操作（如递归删除 rm \-rf、覆盖系统关键配置或 Fork 炸弹等）的正则与语法树模式匹配。审批流被细分为 manual（全量人工验证）、smart（利用辅助小模型评估风险并拦截高危请求）与 off 模式。当被挂起时，位于即时通讯软件另一端的人类操作员只需简单回复确认词，即可解锁执行流程，构建了天然的操作保险栓37。

#### **2.7 记忆与上下文管理**

持续运作的跨期记忆与经验内化是 Hermes 脱颖而出的绝对核心。在短期内存上，它设计了独特的双轨制压缩防溢出方案：主 Agent 引擎维持 50% 阈值的精细化摘要生成，而底层 Gateway 则保留了 85% 阈值的紧急防崩溃冲洗（Hygiene Flush）机制33。在长期记忆上，系统通过维护一个被模型自主管理的 MEMORY.md 知识快照实现实体属性持久化，同时依靠 SQLite FTS5 引擎支持过往所有对话的全文追溯40。最具前瞻性的是其程序化技能生成机制（Procedural Memory）：当智能体依靠连续 5 次以上复杂的工具调用成功解决未知难题后，它会触发隐式的后台进程进行复盘反思，自动生成包含避坑指南与最佳实践的 SKILL.md 固化文件。当未来遇到近似困境时，这段技能将被激活并在随后的多轮迭代中得到模型自主完善28。

#### **2.8 中间件 / 拦截器管道**

与采用重型装饰器模式的系统不同，它的中间件表现为灵活的无侵入式钩子（Hooks）拦截。在 \~/.hermes/plugins/ 目录中，开发者可以放置简单的 Python 钩子脚本。当生命周期运行至 on\_session\_start 或大模型即将请求前的 pre\_llm\_call 瞬间，这些钩子可动态修改并重新编排注入进 Prompt 的结构化数据，成为各种自研日志平台和安全审核方案的数据抓取温床28。

#### **2.9 多 Agent / 子 Agent 系统**

子代理生态同样经历了从同步到异步的巨大演变。早期的 delegate\_task 函数启动的克隆体会在全新的上下文中工作，但会阻塞父代理的交互循环；最新的版本利用线程池支持并发数量高达 3 个的异步任务分发。通过引入 async\_delegation 工具集，父代理不仅不再受阻，还可以指派携带特定身份画像（如代码分析师角色）的配置化代理奔赴不同的技术方向探查并最终提炼总结44。

#### **2.10 状态管理**

由于必须在多种异步通讯通道之间保存连贯逻辑，Hermes 的事务状态均锚定在采用 Write-Ahead Logging (WAL) 并发模式的本地 state.db SQLite 数据库中。这种以树状 ID 追溯母子代理及对话分支的底层持久化方式，保证了复杂任务运行时的防丢特性和断电恢复能力40。

#### **2.11 事件与流式系统**

对于极度重视终端体验的系统，它利用 \_interruptible\_streaming\_api\_call 函数提供无损的字符级流失渲染。即使在处理多层工具调用时，流式系统也能够并行回显“深度思考”动画或执行耗时预估。值得一提的是，针对诸如 WhatsApp 这种不支持流式修改消息的落后协议环境，流控系统会自动探测网络特征并无缝降级为最终整段文本回送机制28。

#### **2.12 任务与调度系统**

通过集成底层的 Cron 规划工具，用户直接通过对话指配定时任务（如“每日早晨九点读取昨日邮件摘要并生成技术简报发送至 Slack”）。底层后台会定期苏醒，在完全静默且隔离的上下文沙箱中装载指定模型与工具集合进行处理，无需时刻消耗宝贵的前台操作视窗资源27。

#### **2.13 可扩展性与插件系统**

其插拔架构远不止于工具库。它建立了一整套涵盖模型提供商（Model Provider）、图像和语音生成模块、甚至是外部图数据库记忆提供商（如 Honcho 和 Hindsight）的插件协议。仅需将遵循配置契约的独立文件夹投放至对应插件根目录，该服务即可自动发现在途模块40。

#### **2.14 错误恢复与韧性**

在面对极其复杂的运行环境时，框架采取了预算熔断的恢复准则。父系统与子代理均受到 IterationBudget 迭代预算（例如 90 次或 50 次）的严格钳制，防止模型陷入死胡同幻觉。遇到 HTTP 超时或是格式反序列化崩塌时，代理依靠自愈捕捉追踪日志（Traceback）生成修正提示促使 LLM 修改其函数结构，并通过多账号凭据池化（Credential Pools）自动轮换 API Key 抵抗云端提供商的并发限流30。

#### **2.15 提示词工程与系统提示**

在系统提示层采用了独特的冷冻快照（Frozen Snapshot）模式。在对话启动之初，系统融合诸如界定职业素养的 SOUL.md 以及涵盖项目全景的 AGENTS.md，构建一幅巨型却静止的系统前言。在多轮次的问答推演中，这一部分内容由于不再轻易篡改，能够完美击中 Anthropic 等厂商的 Prompt Caching 功能，为重度自动化作业节省了天量的 API 开支39。

### **3\. claw-code (UltraWorkers)**

#### **3.1 架构总览**

claw-code 项目脱胎于对知名闭源辅助工具 Claude Code 的白室逆向重构（Clean-Room Reimplementation）。该项目核心不走寻常路，毅然抛弃了臃肿的 Python 虚拟机依赖层，使用超过 2 万行代码的 Rust 工作空间（Workspace）重铸了代理运行时。通过极度严苛的编译期静态分发、事件驱动总线、与少量 Python 提供的前置编排（OmX 层）融合，它成为了目前内存消耗最低、启动速度最快且完全摆脱厂商绑定的高性能终端驱动器53。

#### **3.2 Agent 主循环（核心执行周期）**

主运行状态机被高度抽象为一组 Rust 原生泛型特征 ConversationRuntime\<C, T\>。在循环机制下，C (ApiClient) 负责应对大模型端点异步 HTTP 调用的长时延等待与状态机挂起，而 T (ToolExecutor) 扮演物理世界的触手去直接操纵文件与进程。这种以 Trait 为隔离边界的轮询模式剥离了指令生成与具体动作系统，使整个执行引擎既支持单步调试又具备完美的确定性（Deterministic）55。

#### **3.3 工具调用系统**

在此体系中，所有的工具如原生 grep 文件查找、glob 目录遍历及高效大文件切割读写等，全部依托于 Rust 的系统级线程调度实现，彻底清除了中间层解释器带来的运行开销。所有的工具声明与限制，均在编译期间强制转化为符合 JSON Schema 规范的强类型结构映射至大模型端，极大地减少了模型输出格式破裂的可能性55。

#### **3.4 沙箱 / 执行环境**

对于执行环境，claw-code 内置了基于 Linux namespaces 与 cgroups 技术的深度操作系统原生沙箱隔离支持。通过读取 /proc/1/cgroup 或 .dockerenv 指示器，运行时引擎不仅可以判定自身是否已处于安全容器中，还会依此动态调节可信任的命令暴露范围，实现无需前置搭建庞大集群即可获取的高等级沙箱隔离性能54。

#### **3.5 权限与安全模型**

权限保障是该系统安全架构最夺目的基石之一。主要由 PermissionEnforcer 提供三级控制：Allow、Prompt 与 Deny。其内置长达逾千行的验证组件 bash\_validation.rs 使用极其复杂的语法树识别防范路径逃逸（Path Traversal）、只读违例与各类提权漏洞。相比于纯文本规则配置，硬编码到编译层面的权限核验真正让不可控的系统调用受到了不可逾越的边界约束55。

#### **3.6 人机协同（HITL）**

针对高危修改，它同样采取了挂起请求的信任审批提示（Trust Prompt）。然而，受限于追求“无人工盯盘自治”的终极设计理念（Clawable Harness 目标），其演进方向正在试图将所有的界面阻塞指令转换为机器可读的故障转移报告。当需要破坏性更改但无人操作时，它可以依据特定的自动策略流进入降级模式或者自动撤回，而非在终端僵死干等55。

#### **3.7 记忆与上下文管理**

为避免长期作业中历史垃圾信息撑破 LLM Context Window，该体系采用了独特的 SummaryCompressor 模型。对话序列超过阀值时，压缩器不仅能无损摘要过往语境，还能针对诸如大型 Git diff 报告之类的异常体积文本实行基于块（Chunk-based）的切断聚合。与之配套的 .claude.json 文件则保留着最纯粹且全局一致的工程上下文，将核心开发基调永久传递给新生回话55。

#### **3.8 中间件 / 拦截器管道**

框架未像 Python 生态那样广泛利用装饰器，而是内置了底层原生的生命周期事件钩子，例如预工具调用（PreToolUse）与后置清理（PostToolUse）。这种明确在编译期定义的拦截管道，大幅提升了对运行时状态改变的掌控粒度和审查能力57。

#### **3.9 多 Agent / 子 Agent 系统**

通过 TaskRegistry 机制，并行工作的并发子代理脱离了传统的主从进程羁绊。这些驻留的后台任务记录在一个线程安全的内存注册表（Registry）内，系统能独立启动代理模块跟踪长周期的任务进程或分配特定角色执行编译构建，极大提升了资源多路复用率57。

#### **3.10 状态管理**

系统坚决抵制任何不透明的黑盒内存状态。单次对话周期内的每一点细微推移——例如请求是否送达、任务是否因为缺少权限被阻塞等信息，都严苛地通过原子化写入保存在 .claw/worker-state.json 磁盘文件中。这意味着外部自动化监督套件（如 clawhip）能随时跨越进程生死实时监听并重建整个代码编写的因果链条60。

#### **3.11 事件与流式系统**

采用了极为健壮的高并发 Server-Sent Events (SSE) 引擎处理与推理端点的密集通信。该协议栈能够在处理例如 Anthropic 提示缓存控制（Prompt Caching）等繁复参数的同时，无抖动地在 CLI 界面的标准输出通道里逐字还原出高度定制化带有 ANSI 色彩渲染的极速回复流55。

#### **3.12 任务与调度系统**

任务生命周期完全以事件为先（Event-first），而非模糊的自然语言驱动。系统内嵌特殊的航道探测（Lane Completion）自动机逻辑，当模型最终完成代码改写后，只要编译结果监控为绿灯（Green State），自动机便触发闭环指令自动清理当前代理环境并终结调遣会话。这构成了打造无人值守软件工程组的核心基础59。

#### **3.13 可扩展性与插件系统**

其通过嵌入 LSP（Language Server Protocol）客户端扩展了对多语言语法的深度理解。相比盲目的正则表达式提取，智能体可以通过原生解析代码抽象语法树获取完整的变量定义及引用网络，并整合针对复杂 MCP 后端服务器生命周期的管理控制桥接（Bridge），展现了极致的技术硬核向扩展范式57。

#### **3.14 错误恢复与韧性**

在容错工程上倾注了大量心血。应对云端 API 429 限流或 5xx 熔断时，特有的指数退避重试（Exponential Backoff）模块保障了通讯的健壮性。并且对于如错误推送陈旧 Git 分支或编译连环报错，编排策略已预置了自救动作组：Agent 能利用异常日志自我解析，主动重新发启一次热修复（Hot-fix）推演55。

#### **3.15 提示词工程与系统提示**

这方面的设计极致精简而高效。通过解析当前目录内诸如 CLAUDE.md 及各种预设模型别名的配置层次（如从系统级 \~/.claw.json 到项目级覆盖文件加载），启动瞬间系统会编译生成兼顾身份认同和项目级编程范式的指令前导片段，保障了后续执行的极高确定性与专业聚焦54。

### **4\. openclaw (OpenClaw)**

#### **4.1 架构总览**

如果说其他方案倾向于本地沙箱运算，那么 OpenClaw 则是一部面向跨平台多设备的网络分布式拓扑系统。它使用强类型的 TypeScript/Node.js 生态系统进行构建，推崇以“控制平面为王（Control-plane-first）”的设计思维。一个部署在 NAS 甚至树莓派上长期在线的 WebSocket 网关服务器负责承担所有的智能推演及指令分发中枢；而连接在这个虚拟枢纽上的智能手机应用、macOS 伴侣或者单纯的网页端 UI，都成为只提供本地界面呈现并转发物理环境数据的分布式远端节点（Nodes）29。

#### **4.2 Agent 主循环（核心执行周期）**

它的运行轨迹不再依赖阻塞或繁复的树形图计算，而是构建在一个严格串行化的进程内存级队列之上。所有来自异构即时通讯端口的“自动回复（Auto-reply）”事件包进入称为 main 的队列流接受秩序化的大语言模型召唤处理。在运行间隙（Mid-turn），针对突发的对话插入，代理运行环境具备吸收及接纳（Steering）修改动态响应意图的核心能力66。

#### **4.3 工具调用系统**

凭借分布式的节点哲学，其工具链触角打破了系统自身的软件屏障：除了处理标准的文本内容爬取、文件操作以外，它的网络拓扑允许中枢命令某一台被授权信任的移动端节点打开手机摄像头（camera.\*）、捕获电脑屏幕像素流（screen.record）抑或是控制物理画布图层显示（canvas.\*），实现了真正意义上虚实融合的广域行动能力65。

#### **4.4 沙箱 / 执行环境**

系统不纠结于在主控制节点开辟虚拟机沙箱，而是将其去中心化为一个个独立运作且各自接受宿主操作系统原生沙箱限制的节点运行环境（Runner）。基于各设备的本机操作能力并结合严苛的跨系统权限，这种利用终端算力充当执行沙盒的思路彻底打通了云网与端侧的异构协同65。

#### **4.5 权限与安全模型**

该系统的通讯安全门槛是工业级的。从设备连接伊始就必须携带基于 Ed25519 的设备加密指纹；甚至跨设备的网络准入也能与 Tailscale 服务等零信任环境强力绑定。具体至针对命令发起的拦截体系（Exec Approvals），执行操作的节点主机各自捍卫一本独有的 exec-approvals.json 白名单。来自网枢的破坏指令若未曾在本机预置允许，不仅执行将会碰壁，控制面也必须启动远程审核弹窗请求多重签核后方可强行越狱通过71。

#### **4.6 人机协同（HITL）**

这是一个高度分离且异步的人机共治模型。即便 Agent 在处理高阶或危险操作任务时陷入纠结，产生的阻断指令（Block Events）也能通过事件流直接路由至用户所处任意通讯软体（如 Telegram），用户只需轻点内嵌回复按钮（如发送✅确认执行）即可实现远程非阻塞断点通关，将对流程卡死的烦恼降至最低72。

#### **4.7 记忆与上下文管理**

面对随着时间推移爆炸的长程记忆负担，系统采取了隐式压缩与结构轮换双管齐下的打法。所有轨迹与对话日志均以高效率的 sessionId.jsonl 文件格式呈只追加（Append-Only）记录。当活跃上下文达到触发容量阈值前，架构底层通过投喂一个无痕的内置提示符（NO\_REPLY），在幕后指挥大模型默默提纯出总结记录；若启用字节防御系统，更可直接在存储端将臃肿的流数据滚动更替至冷数据归档卷，确保运行中的大模型总是保持如婴儿般的计算敏锐度75。

#### **4.8 中间件 / 拦截器管道**

在架构演化中并未暴露过多的繁杂插件钩子，而是聚焦于唯一的生死判官 —— before\_tool\_call。该拦截器在任何功能工具实际触达外部前执行策略裁判。它可以产生三种终局：通行、无条件抛弃该请求，或是更进一步将其打包入驻异步排队系统，直至获得权限签发人员的回执77。

#### **4.9 多 Agent / 子 Agent 系统**

子代理（Subagent）在此体系中只是被赋予了诸如 agent:main:subagent:\<id\> 此等特殊前缀 ID 的普通隔离会话而已。凭借中枢强大的排队并行处理能效，主 Agent 如同一位将军，根据子任务拆分情况将多个请求分别推入多航道中齐头并进处理（如并发核对多篇竞品财报），并在各个子会话结束后自然交接回汇总成果78。

#### **4.10 状态管理**

由于支持全平台与多频段客户端的随意登入登出，其一切真理状态数据皆归集在网关守护进程下的 sessions.json 当中。记录诸如最终交互戳、当前模型载体配置等核心快照，并配有极度严谨的清道夫系统按照基于每日轮询（Daily Reset）抑或是发呆超时（Idle Reset）等机制自我保养庞大的状态基石76。

#### **4.11 事件与流式系统**

通信的血液就是基于 JSON Schema 高度结构化的 WebSocket 数据帧负载体系。网络上的握手认证（connect）、资源下推探针（hello-ok）、请求回复配对乃至维持链路生机的全局广播（event:presence）心跳包交织出了一张低延迟且具备精准背压防洪限流管控的神经网。前端展现毫无迟滞，且因为幂等键防重机制（Idempotency Key），即使断网重连也绝无二次执行之忧65。

#### **4.12 任务与调度系统**

针对动态任务流控制设计了极具创意的多模控制参数群：steer 准许顺滑切入调整即时运行轨迹，followup 则是在单次迭代结束后依序安排执行，而 collect 则会像漏斗一般吸收所有的指令洪峰压缩汇总一并处理。另外完全割裂的 Cron 定时任务也使得智能管家在无人问津之时尚能按点打卡干活66。

#### **4.13 可扩展性与插件系统**

其基于元数据描述的插件生态允许扩展系统深入到每一台挂载在案的执行节点。借助根目录的配置中心和节点握手期间所主动公开声明的一簇能力清单（如是否持有图形视窗或高权限命令控制台），网关能智能适配并将相关操作交由这些被激活的分布式功能触角包揽处理65。

#### **4.14 错误恢复与韧性**

在软件崩溃这一根本性梦魇面前，OpenClaw 通过采用 systemd 或 LaunchDaemons 守护进程服务实施监控与微秒级拉起，使得自身如不死鸟般顽强。叠加消息幂等与离线间隙事务补偿处理技术，即便主进程因某种极限消耗而崩溃，也绝不会让用户的单条核心命令因网络阻断或宕机而永远随风消散65。

#### **4.15 提示词工程与系统提示**

该系统的知识背景注入策略讲究组合与边界。除了传统的利用 AGENTS.md（项目规约）、TOOLS.md 和性格塑性文件 SOUL.md 进行静态背景前置以外；系统甚至演化出了能自动依据上一个结束周期的会话移交纪要（Session Handoff），给下一个全新的工作流动态注回关键历史脉络与下一步待办清单（Next Actions）的高度拟人化情境重载能力78。

### **5\. learn-claude-code (ShareAI Lab)**

#### **5.1 架构总览**

区别于一切试图覆盖生产应用死角的工程级框架，该项目是一部极尽精简之美、使用纯 Python 语言撰写的多段式基准教学源码。在其长达 20 课时的递进式演化脉络中，作者毫无保留地解剖了从一句简单的接口封套逐渐膨胀为大型架构的系统原貌。整套代码的核心哲学直指灵魂：“智能与代理能力（Agency）来源于模型基座本身的训练，而 Harness（外壳）仅仅是承载这些智能使其不爆缸运行的坚实容器”84。

#### **5.2 Agent 主循环（核心执行周期）**

教学中的 s01 章节摒除了诸多框架炫技的包装图计算或是复杂协程，通过一段朴实无华的 while True 循环揭示了智能体执行循环的最核心规律：推送上下文至 LLM \-\> 解析拦截 stop\_reason \-\> 判断如果是进行函数使用（tool\_use）则执行后挂载至列表 \-\> 返回循环重新请求；否则循环终止并返回纯文本答复87。

#### **5.3 工具调用系统**

s02 进一步解构工具逻辑：将繁杂的命令与能力分发拆解成单纯的方法字典映射（TOOL\_HANDLERS.get）。这种以原子化和可组合为原则的设计模式，通过提供 read\_file 等操作系统直接接触级的基础能力展示了让智能体“获得双手”的最基础路径85。

#### **5.4 沙箱 / 执行环境**

相较于动辄启挂 Docker 的重型体系，s02 及后续教件通过最为经典的程序限制方式解析安全准入边界的设计原则：通过简单的 safe\_path 检验拦截试图通过相对路径（如 ../）穿越出当前操作目录范畴的任何违规请求，从而实现了最轻量化但意义深刻的逻辑隔离“沙盘”85。

#### **5.5 权限与安全模型**

权限的概念在 s03 被单独具象化：“在授予完全自由前必须设定清晰护栏”。该节采用最纯粹的命令行读取技术拦截大语言模型下达的执行申请并等待确认输入，向学习者剖析了授权阻断引擎的基本形态84。

#### **5.6 人机协同（HITL）**

该教学项目没有设计分布式异步通讯，只是在破坏性命令行被抛出的临界点拦截主进程并将控制权抛还至终端标准输入（stdin）。这就赤裸裸地证明了所有宏大复杂系统里 HITL 人工介入的本源机理就是一句话：流程挂起配合信号注回85。

#### **5.7 记忆与上下文管理**

面对被无限增长历史逼到崩溃极限的模型，s06 到 s08 以精巧的三级压缩策略予以破解：其 Layer 1 是每轮静默替换超龄文本的隐式 micro\_compact；Layer 2 是监控 Token 容量到顶后主动启用模型摘录并全量替换历史的 auto\_compact；Layer 3 则是暴露压缩权限给模型本身，由大模型根据任务阶段自主决定收敛的 manual compact。这套由简入繁的压缩理论向所有学习者普及了解决上下文溢出的通用解法85。

#### **5.8 中间件 / 拦截器管道**

如何不修改主执行循环的情况下加入观测逻辑？s04 给出了生动的“Hooks”概念教学。向函数外部抛出执行节点前后的触发切面，开发者可以籍此在系统运行时截取统计消耗或是干预传导数据，而不必将整个主系统变得臃肿不堪85。

#### **5.9 多 Agent / 子 Agent 系统**

通过逐步进阶的学习路径（从 s06 的初步主从结构委托衍生至 s15 与 s17 所揭示的多智能体自治协作系统），项目深刻展示了不同专精领域的模型如何依靠解耦的任务信箱机制传递并认领状态信标。这为实现真正庞大复杂的体系构建拆除了认知高墙85。

#### **5.10 状态管理**

教学在 s12 展示了纯粹依靠内存变量是不可能持久的。系统以显式的磁盘文件为落脚点建立有向依赖拓扑图，通过监控每一独立节点的 ready、blocked 及 done 流转状态彻底化解了超长期作业中的状态崩溃困境85。

#### **5.11 事件与流式系统**

在多代理信箱互通机制（s16 协议讲解）的实现上，依靠一套只附加无修改的共享 JSONL 通信总线协议（Message Bus），确立了系统组件间对话的唯一正确语法，证明了即便没有复杂的中介网关，依靠标准的握手问答设计也能实现稳定可靠的数据交换85。

#### **5.12 任务与调度系统**

当任务庞大时（如编译巨构项目），单纯的阻塞必定让主线宕机。s13 以最通俗的方式呈现了如何将沉重的子任务推至后台（Background Task）进程池并维系进程通信。随后引入的 s14 更是以纯代码的层级展现如何集成并运行无须人催促的定时触发调度系统85。

#### **5.13 可扩展性与插件系统**

该系统从根本上指出将各类指令统统扔进系统设定词中是效率低下的设计噩梦。s07 与 s19 强有力地推行了“知识与行动库的懒加载与按需加载”。仅在任务必要时，外部复杂的模型上下文协议工具集群（MCP Plugins）或专业背景长文本方才被提取并注入，实现了高效率外扩85。

#### **5.14 错误恢复与韧性**

在 s11 中教学直击要害：“失败不是终止，而是重试和自愈的起点”。代码展示了在发生异常时不仅不能死机，还必须把详尽的异常追踪流（Traceback）封存在结果中扔回给生成层，通过利用 LLM 的内置理解能力让其重构修正指令进而自主逃出生天85。

#### **5.15 提示词工程与系统提示**

贯穿整个课程（尤其在 s10）的终极主线原则：优秀的系统级提示（System Prompt）不是那些由大量“你是一个强大的机器人”所组成的刻板长文。而是基于环境约束条件、当下调用的工作空间模块与按需引用的动态工具说明，利用程序在每一轮通信发起之始实时动态组装并渲染而出的生命有机体85。

## **跨项目对比：结构、分歧与趋同分析**

为了更直观地把握 Agent Harness 系统从实验室走向企业级工程生产中的深层次架构与设计权衡，本节对上述五个开源方案展开全面的跨界对比与深度透视。

### **结构对比**

下表从技术栈、架构聚焦、执行机制以及关键拓展生态四个维度概括了项目的核心差异。

| 框架项目 | 技术基座与编程语言 | 核心架构侧重点 | 执行模型流转机制 | 代表性应用场景 |
| :---- | :---- | :---- | :---- | :---- |
| **deer-flow** | Python / LangGraph \+ FastAPI | 状态机流转与多步骤长时间任务分解编排 | 同步图节点切换、基于 Checkpointer 的持久快照 | 企业级数小时深层次研报生成及代码实现 |
| **hermes-agent** | Python | 闭环自我演进及跨重度 IM 平台统一接入 | 轻量级严格同步角色交替循环 | 高并发多终端私人工作助理、记忆固化归档 |
| **claw-code** | Rust Workspace \+ Python | 极致低耗的运行态及绝对内存/权限安全性 | 借助静态特征与状态机生命周期的极速推进 | 高性能本地单机代码开发、硬核终端代码生成 |
| **openclaw** | TypeScript / Node.js | 以网络路由控制面优先的跨异地物理终端控制 | 高并发内存队列及分布式异步非阻塞指令集 | 极客全平台多设备（移动端＋桌面）智能联动中心 |
| **learn-claude-code** | Python (渐进式教学解构) | 透明化、去框架化的微内核运行原理解密 | 无任何封套的原始无限轮询大循环机制推演 | 从 0 到 1 的开发者概念破冰与底层原理自修 |

### **设计哲学分析**

每一个开源框架的代码演进均直接折射出其立项之初为解决特定应用场景所做出的强烈的哲学取舍。

* **确定性工业编排 vs 演进式记忆固化**：以 **deer-flow** 为代表的企业长任务处理系统深信：“复杂的任务不可预测，但处理任务的状态图必须严谨透明”。通过引入极其厚重的 LangGraph 底座以保证所有推演节点的可视化追踪、审查及任意深度的回滚复盘，体现出大型互联网厂商追求过程“绝对可控”的执念2。反其道而行的 **hermes-agent** 则视记忆与经验为珍宝，其设计理念深信不疑地指出“数字员工应当随着陪伴而成长”。它不在流程编排上下重注，而是用极高密度的代码投入至诸如 SQLite 全文检索库、双通道摘要压缩甚至在满足 5 次深层交互后强制自我催化并持久化提炼出新技能 .md 的体系中，充分演绎了拟人化生长的架构哲学29。  
* **极致硬核的运行极客 vs 追求万物互联的路由中心**：由 UltraWorkers 用 Rust 从底向上再造的 **claw-code** 充满了极客对臃肿系统的抗拒。它抛弃 Python 层层重叠的虚拟机损耗与繁复动态特性，强行将所有的生命周期收紧进编译期的 Trait 和严密的 PermissionEnforcer 中。它相信“唯有将模型意图封锁于原生极速的静态隔离笼中，安全和效能方可兼得”54。另一面的 **openclaw**，不把性能极致挤压在单机上，而视系统为跨设备信息的高速集线器。其将 WebSocket 作为中枢神经网，任何接入的外壳节点（甚至是移动手机设备）仅负责根据 hello-ok 回调通报自己拥有的摄像与录屏能力并等待网关的分布式调遣。这种“计算去中心、控制强中心”思路正是跨云网设备互联互通的大势所趋65。

### **关键分歧及其意义**

在长达两年的架构混战中，不同的实现路径在以下几个技术深水区产生了极其鲜明的分歧，这些分歧直接影响了后续框架的演进路线：

1. **多代理（Multi-Agent）并发与阻塞模型的撕裂** 在处理任务分发时，到底该不该让主管（Lead Agent）停下来等待？**deer-flow** 在默认状态下派生子代理后会由于底层并发等待轮询循环，主节点将彻底陷入阻塞僵死之中，屏蔽任何主航道的突发调阅，这种做法牺牲了系统互动敏捷性但最大化保障了后续集成输出的确定无误18。敏锐捕捉到痛点的 **hermes-agent** 和 **openclaw** 迅速倒向异步模式，通过 async\_delegation 不仅让子代理去后台潜行，同时主服务即刻恢复对人类终端的心跳连线。这种从同步到彻底基于事件总线的飞跃，标志着框架正逐步从“宏观函数执行器”演变向现代操作系统般的进程池调度模式45。  
2. **面对无底洞般上下文的截断挽救流派** 所有的系统都在应对 Token 无限增长之痛，但在处理“如何体面地忘记”上分为数派。**learn-claude-code** 用教科书般的三层提纯（占位符转换 \-\> 模型批量重读摘要 \-\> 人工触发切断）指明了最小阻力路径90；**openclaw** 选用了最极端的仅追加归档路线和强制 Byte Guard 更迭策略，让老旧消息不复干扰视线76；而 **deer-flow** 以及 **hermes-agent** 的精细化运营则达到了另一高度。deer-flow 引入了抢救机制（Skill Rescue），在屠刀落下之际将近期的关键执行指导书（Skill）提走并拼接回新首段；而 hermes-agent 更首创了针对 Anthropic 等厂商特殊 Prompt Caching 的“冻结系统快照”保护机制，保证摘要更新的同时让大量前置上下文依然稳稳命中便宜的缓存空间15。

### **趋同点**

尽管存在诸多细节分歧，大潮之下的技术演化不可避免地涌向了以下被验证行之有效的设计黄金法则：

1. **从硬编码 Prompt 演进为声明式的按需知识抽取** 没有任何一个成熟框架还在系统提示词内灌装上万字的死板规约指令集。无论是内置 SKILL.md 知识库映射，亦或者外部扩展通过引入通用大模型环境协议 MCP (Model Context Protocol) 作为插件神经接口，大家都在默契地应用了懒加载范式（Lazy Loading）和外挂向量工具映射：当判定需求边界触发时方才从外部资源引入长文本设定，从根本上终结了无效 Token 消耗与模型幻觉的双重暴击。  
2. **在不受信任的计算沙箱建立深水区的审查堡垒** 不管外壳是由何种语言编写，各大团队在面对由概率运算产生的无束缚的执行逻辑时出奇地一致：决不信任大模型输出的直连环境操作代码。从 **openclaw** 跨平台设备严苛的 Ed25519 Token 指纹鉴权配合多端批准（Exec Approvals），再到 **deer-flow** 和 **claw-code** 利用 Regex 及 Bash AST 层面对敏感命令进行封杀。沙盒（Docker 或 Linux 原生隔离）已然构筑起了最后防线，“防泄漏、防自毁”的纵深多道策略现今已确立为生产环境代理体系的基础标配。

### **差距分析**

纵观全局，开源世界中虽然各种流派百花齐放，依然暴露出许多横跨现有全部解决方案尚未被彻底弥合的断层差距。例如，**claw-code** 以牺牲多设备轻量级通信网络为代价去追求单机的绝对高光性能，这限制了它向大众社交群组服务中介转型的可能；另一端的 **openclaw** 通过繁密的 WebSocket 构建了无处不在的接入网络，然而其在诸如处理需要精确保留历史长链追踪以执行断点纠错及防系统宕机遗忘等巨型长时间周期作业上（如 **deer-flow** 依托 LangGraph 特别擅长的几个小时起步的长程调研与代码构筑事务），底层事务性约束与图结构序列化机制反而显得过于粗放。  
换言之，时至今日，业界尚缺少一个能够集 **deer-flow** 的史诗级复杂规划容错体系、**hermes-agent** 的惊艳技能记忆进化机制、以及 **claw-code** 原生毫秒级低功耗安全隔离于一身的究极融合体。各种外壳在某一极端方向猛冲之后，仍需大量的工程磨合才能填补那些因架构先天排他性带来的空白洼地。

## **综合归纳**

从单一的智能聊天机器人脱胎换骨为全自动且高度受控的虚拟雇员群体，Agent Harness 无疑已成为将原始模型感知智力成功引入现代计算物理空间不可或缺的核心转化介质。通过对 deer-flow、hermes-agent、claw-code、openclaw 以及 learn-claude-code 这五大代表性开源项目的细致入微的对比与全景解剖，一幅横跨智能体调度与执行底座的宏伟演进画卷被清晰展现在眼前。  
一个合格、能经历生产环境验证的架构，绝不再是针对 LLM API 的一次简单同步包装。这些顶尖架构的共同演进给出了深刻的昭示：成功驾驭智能的系统，必须要解决四大极为棘手的工程难题。首先是**极高复杂状态与上下文的精准治理**，需要彻底摒弃落后的全量传导，跃升为能够自适应压缩、基于向量或图结构自动追忆的多级分层模型；其次是**打造极其苛刻的安全执行纵深边界**，不仅需要沙箱与虚拟化提供隔离兜底，还需要借助各类前置护栏及跨屏人机对齐确认阻隔大语言模型非线性抽风引发的毁灭性破坏；第三点是**拥有具备超级弹性的并行异构编排能力**，支持将如汪洋般繁重的终极目标打散交付至可以独立潜行且异步互通的子代理群体中协同突击；最后则是**借助标准化协议打造生态无限扩展的热插拔接口**，利用声明式技能设定结合如火如荼的 MCP 协议组件群使得外扩工具不依赖于模型核心改动而自在繁荣。唯有这四大支柱稳固合龙，AI Agent 才真正摆脱了演示版实验玩具的稚嫩标签，庄严地站上了成为支撑人类社会数字生产力中枢的历史舞台。

#### **引用的著作**

1. deer-flow/backend/README.md at main \- GitHub, [https://github.com/bytedance/deer-flow/blob/main/backend/README.md](https://github.com/bytedance/deer-flow/blob/main/backend/README.md)  
2. DeerFlow 2.0 深度拆解：字节跳动70K Star 的Super Agent Harness \- iTech \- 博客园, [https://www.cnblogs.com/itech/p/20206290](https://www.cnblogs.com/itech/p/20206290)  
3. GitHub \- bytedance/deer-flow: An open-source long-horizon SuperAgent harness that researches, codes, and creates. With the help of sandboxes, memories, tools, skill, subagents and message gateway, it handles different levels of tasks that could take minutes to hours., [https://github.com/bytedance/deer-flow](https://github.com/bytedance/deer-flow)  
4. deer-flow/backend/docs/ARCHITECTURE.md at main \- GitHub, [https://github.com/bytedance/deer-flow/blob/main/backend/docs/ARCHITECTURE.md](https://github.com/bytedance/deer-flow/blob/main/backend/docs/ARCHITECTURE.md)  
5. Super Agent Harness 框架DeerFlow 2.0 源码分析解读原创 \- CSDN博客, [https://blog.csdn.net/qq\_43692950/article/details/160893672](https://blog.csdn.net/qq_43692950/article/details/160893672)  
6. deer-flow:基于 LangGraph 和 LangChain 的 super agent harness 项目 \- AtomGit \- GitCode, [https://gitcode.com/yongzhousz/deer-flow/blob/main/backend/docs/CONFIGURATION.md](https://gitcode.com/yongzhousz/deer-flow/blob/main/backend/docs/CONFIGURATION.md)  
7. tool description parameter issue · Issue \#1261 · bytedance/deer-flow \- GitHub, [https://github.com/bytedance/deer-flow/issues/1261](https://github.com/bytedance/deer-flow/issues/1261)  
8. deer-flow/backend/docs/MCP\_SERVER.md at main \- GitHub, [https://github.com/bytedance/deer-flow/blob/main/backend/docs/MCP\_SERVER.md](https://github.com/bytedance/deer-flow/blob/main/backend/docs/MCP_SERVER.md)  
9. deer-flow/backend/docs/CONFIGURATION.md at main \- GitHub, [https://github.com/bytedance/deer-flow/blob/main/backend/docs/CONFIGURATION.md](https://github.com/bytedance/deer-flow/blob/main/backend/docs/CONFIGURATION.md)  
10. How to Deploy DeerFlow with Docker for Production \- BSWEN, [https://docs.bswen.com/blog/2026-03-16-deerflow-docker-deployment/](https://docs.bswen.com/blog/2026-03-16-deerflow-docker-deployment/)  
11. \[runtime\] Sandbox container "Server disconnected without sending a response" due to unnecessary services consuming resources · Issue \#1739 · bytedance/deer-flow \- GitHub, [https://github.com/bytedance/deer-flow/issues/1739](https://github.com/bytedance/deer-flow/issues/1739)  
12. deer-flow/backend/docs/GUARDRAILS.md at main \- GitHub, [https://github.com/bytedance/deer-flow/blob/main/backend/docs/GUARDRAILS.md](https://github.com/bytedance/deer-flow/blob/main/backend/docs/GUARDRAILS.md)  
13. \[backend\] ClarificationMiddleware can duplicate HITL clarification messages on repeated tool-call execution · Issue \#2350 · bytedance/deer-flow \- GitHub, [https://github.com/bytedance/deer-flow/issues/2350](https://github.com/bytedance/deer-flow/issues/2350)  
14. How Memory Works in DeerFlow? \- Mem0, [https://mem0.ai/blog/how-memory-works-in-deerflow](https://mem0.ai/blog/how-memory-works-in-deerflow)  
15. deer-flow/backend/docs/summarization.md at main \- GitHub, [https://github.com/bytedance/deer-flow/blob/main/backend/docs/summarization.md](https://github.com/bytedance/deer-flow/blob/main/backend/docs/summarization.md)  
16. Customization \- DeerFlow, [https://deerflow.tech/en/docs/harness/customization](https://deerflow.tech/en/docs/harness/customization)  
17. DeerFlow | AI Native Landscape \- Jimmy Song, [https://landscape.jimmysong.io/projects/deer-flow/](https://landscape.jimmysong.io/projects/deer-flow/)  
18. Subagent Delegation | Hermes Agent \- nous research, [https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation](https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation)  
19. \[Feature Proposal\] Persistent, Interruptible Subagents via A2A Protocol · Issue \#1339 · bytedance/deer-flow \- GitHub, [https://github.com/bytedance/deer-flow/issues/1339](https://github.com/bytedance/deer-flow/issues/1339)  
20. \[runtime\] Plan mode fails with duplicate todos channel type conflict · Issue \#3199 · bytedance/deer-flow \- GitHub, [https://github.com/bytedance/deer-flow/issues/3199](https://github.com/bytedance/deer-flow/issues/3199)  
21. sandbox key in ThreadState missing reducer causes INVALID\_CONCURRENT\_GRAPH\_UPDATE on parallel tool calls · Issue \#3636 · bytedance/deer-flow \- GitHub, [https://github.com/bytedance/deer-flow/issues/3636](https://github.com/bytedance/deer-flow/issues/3636)  
22. Verified Detection and Prevention of Concurrency Anomalies in Multi-Agent Large Language Model Systems \- arXiv, [https://arxiv.org/html/2606.17182v1](https://arxiv.org/html/2606.17182v1)  
23. deer-flow/backend/docs/plan\_mode\_usage.md at main \- GitHub, [https://github.com/bytedance/deer-flow/blob/main/backend/docs/plan\_mode\_usage.md](https://github.com/bytedance/deer-flow/blob/main/backend/docs/plan_mode_usage.md)  
24. \[Feature\] Implement built-in Cron Scheduler for Agent Automation · Issue \#1651 · bytedance/deer-flow \- GitHub, [https://github.com/bytedance/deer-flow/issues/1651](https://github.com/bytedance/deer-flow/issues/1651)  
25. ByteDance DeerFlow 2.0 : Docker of AI Workers | by Mehul Gupta | Data Science in Your Pocket \- Medium, [https://medium.com/data-science-in-your-pocket/bytedance-deerflow-2-0-docker-of-ai-workers-c866b4ff558f](https://medium.com/data-science-in-your-pocket/bytedance-deerflow-2-0-docker-of-ai-workers-c866b4ff558f)  
26. deer-flow | 阿超, [https://vampireachao.github.io/2026/03/27/deer-flow/index.html](https://vampireachao.github.io/2026/03/27/deer-flow/index.html)  
27. NousResearch/hermes-agent: The agent that grows with you \- GitHub, [https://github.com/nousresearch/hermes-agent](https://github.com/nousresearch/hermes-agent)  
28. mudrii/hermes-agent-docs \- GitHub, [https://github.com/mudrii/hermes-agent-docs](https://github.com/mudrii/hermes-agent-docs)  
29. AI 101: Hermes Agent vs OpenClaw: Local AI Agents Compared \- Turing Post, [https://www.turingpost.com/p/hermes](https://www.turingpost.com/p/hermes)  
30. Agent Loop Internals | Hermes Agent \- nous research, [https://hermes-agent.nousresearch.com/docs/developer-guide/agent-loop](https://hermes-agent.nousresearch.com/docs/developer-guide/agent-loop)  
31. tracking: provider transport refactor (agent/transports/) · Issue \#13473 · NousResearch/hermes-agent \- GitHub, [https://github.com/NousResearch/hermes-agent/issues/13473](https://github.com/NousResearch/hermes-agent/issues/13473)  
32. Features Overview | Hermes Agent, [https://hermes-agent.nousresearch.com/docs/user-guide/features/overview](https://hermes-agent.nousresearch.com/docs/user-guide/features/overview)  
33. Hermes Agent: What It Is, How It Works, and How to Build Your Personal AI News Briefing, [https://datasciencedojo.com/blog/hermes-agent-how-it-works-tutorial/](https://datasciencedojo.com/blog/hermes-agent-how-it-works-tutorial/)  
34. Hermes Agent: A Self-Improving AI Agent That Runs Anywhere \- DEV Community, [https://dev.to/arshtechpro/hermes-agent-a-self-improving-ai-agent-that-runs-anywhere-2b7d](https://dev.to/arshtechpro/hermes-agent-a-self-improving-ai-agent-that-runs-anywhere-2b7d)  
35. Hermes Agent Security: 7-Layer Defense Setup Guide \- Hostinger, [https://www.hostinger.com/tutorials/hermes-agent-security](https://www.hostinger.com/tutorials/hermes-agent-security)  
36. Feature: Gateway Permission Tiers — Role-Based Access Control (Owner/Admin/User/Guest) for Messenger Platforms · Issue \#527 · NousResearch/hermes-agent \- GitHub, [https://github.com/NousResearch/hermes-agent/issues/527](https://github.com/NousResearch/hermes-agent/issues/527)  
37. Security | Hermes Agent \- nous research, [https://hermes-agent.nousresearch.com/docs/user-guide/security](https://hermes-agent.nousresearch.com/docs/user-guide/security)  
38. Tips & Best Practices | Hermes Agent, [https://hermes-agent.nousresearch.com/docs/guides/tips](https://hermes-agent.nousresearch.com/docs/guides/tips)  
39. Context Compression and Caching | Hermes Agent \- nous research, [https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching)  
40. Hermes Agent Memory System: Curated Memory, Session Search, and Self-Improvement, [https://medium.com/@xpf6677/hermes-agent-memory-system-curated-memory-session-search-and-self-improvement-a84d2a9d5d01](https://medium.com/@xpf6677/hermes-agent-memory-system-curated-memory-session-search-and-self-improvement-a84d2a9d5d01)  
41. Persistent Memory | Hermes Agent \- nous research, [https://hermes-agent.nousresearch.com/docs/user-guide/features/memory](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory)  
42. How Hermes Agent Memory Actually Works (And How to Make It Better) \- Vectorize.io, [https://vectorize.io/articles/hermes-agent-memory-explained](https://vectorize.io/articles/hermes-agent-memory-explained)  
43. Feature: Multi-Agent Architecture — Orchestration, Cooperation, Specialized Roles & Resilient Workflows · Issue \#344 · NousResearch/hermes-agent \- GitHub, [https://github.com/NousResearch/hermes-agent/issues/344](https://github.com/NousResearch/hermes-agent/issues/344)  
44. feat(delegation): agent profiles for delegate\_task — custom orchestration harness support · Issue \#9459 · NousResearch/hermes-agent \- GitHub, [https://github.com/NousResearch/hermes-agent/issues/9459](https://github.com/NousResearch/hermes-agent/issues/9459)  
45. Hermes Agent Adds Asynchronous Subagents, So Delegated Work No Longer Blocks the Parent Chat \- MarkTechPost, [https://www.marktechpost.com/2026/06/16/hermes-agent-adds-asynchronous-subagents-so-delegated-work-no-longer-blocks-the-parent-chat/](https://www.marktechpost.com/2026/06/16/hermes-agent-adds-asynchronous-subagents-so-delegated-work-no-longer-blocks-the-parent-chat/)  
46. Delegation & Parallel Work | Hermes Agent \- nous research, [https://hermes-agent.nousresearch.com/docs/guides/delegation-patterns](https://hermes-agent.nousresearch.com/docs/guides/delegation-patterns)  
47. stephenschoettler/hermes-lcm: Lossless Context Management plugin for Hermes Agent — DAG-based context engine that never loses a message \- GitHub, [https://github.com/stephenschoettler/hermes-lcm](https://github.com/stephenschoettler/hermes-lcm)  
48. What Is Hermes Agent? The Open-Source AI Agent Platform Explained | MindStudio, [https://www.mindstudio.ai/blog/what-is-hermes-agent-open-source-ai-platform-explained](https://www.mindstudio.ai/blog/what-is-hermes-agent-open-source-ai-platform-explained)  
49. Model Provider Plugins \- Hermes Agent, [https://hermes-agent.nousresearch.com/docs/developer-guide/model-provider-plugin](https://hermes-agent.nousresearch.com/docs/developer-guide/model-provider-plugin)  
50. Configure, extend, or contribute to Hermes Agent \- nous research, [https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/autonomous-ai-agents/autonomous-ai-agents-hermes-agent](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/autonomous-ai-agents/autonomous-ai-agents-hermes-agent)  
51. hermes-agent/AGENTS.md at main \- GitHub, [https://github.com/NousResearch/hermes-agent/blob/main/AGENTS.md](https://github.com/NousResearch/hermes-agent/blob/main/AGENTS.md)  
52. Hermes Agent: The Practitioner's Reference (2026), [https://blakecrosley.com/guides/hermes](https://blakecrosley.com/guides/hermes)  
53. GitHub \- ultraworkers/claw-code: An agent-managed museum exhibit, built in Rust with Gajae-Code / LazyCodex — developed and maintained with no human intervention., [https://github.com/ultraworkers/claw-code](https://github.com/ultraworkers/claw-code)  
54. Claw Code: Open-Source Claude Code Alternative in Rust (Install Guide), [https://computingforgeeks.com/claw-code-open-source-claude-code-alternative/](https://computingforgeeks.com/claw-code-open-source-claude-code-alternative/)  
55. Claw Code Killed Claude Code?. Why Anthropic can't take down Claw… | by Mehul Gupta | Data Science in Your Pocket, [https://medium.com/data-science-in-your-pocket/claw-code-killed-claude-code-02aab80b0838](https://medium.com/data-science-in-your-pocket/claw-code-killed-claude-code-02aab80b0838)  
56. What is Claw Code? Leaked Claude Code Cloned | by Mehul Gupta | Data Science in Your Pocket | Medium, [https://medium.com/data-science-in-your-pocket/what-is-claw-code-leaked-claude-code-cloned-3f3e1ca4edd2](https://medium.com/data-science-in-your-pocket/what-is-claw-code-leaked-claude-code-cloned-3f3e1ca4edd2)  
57. claw-code-parity/rust/README.md at main \- GitHub, [https://github.com/ultraworkers/claw-code-parity/blob/main/rust/README.md](https://github.com/ultraworkers/claw-code-parity/blob/main/rust/README.md)  
58. claw-code/docs/container.md at main \- GitHub, [https://github.com/ultraworkers/claw-code/blob/main/docs/container.md](https://github.com/ultraworkers/claw-code/blob/main/docs/container.md)  
59. PARITY.md \- ultraworkers/claw-code \- GitHub, [https://github.com/ultraworkers/claw-code/blob/main/PARITY.md](https://github.com/ultraworkers/claw-code/blob/main/PARITY.md)  
60. claw-code/ROADMAP.md at main \- GitHub, [https://github.com/ultraworkers/claw-code/blob/main/ROADMAP.md](https://github.com/ultraworkers/claw-code/blob/main/ROADMAP.md)  
61. claw-code/USAGE.md at main \- GitHub, [https://github.com/ultraworkers/claw-code/blob/main/USAGE.md](https://github.com/ultraworkers/claw-code/blob/main/USAGE.md)  
62. ROADMAP.md \- ultraworkers/claw-code-parity \- GitHub, [https://github.com/ultraworkers/claw-code-parity/blob/main/ROADMAP.md](https://github.com/ultraworkers/claw-code-parity/blob/main/ROADMAP.md)  
63. CLAUDE.md \- ultraworkers/claw-code-parity \- GitHub, [https://github.com/ultraworkers/claw-code-parity/blob/main/CLAUDE.md](https://github.com/ultraworkers/claw-code-parity/blob/main/CLAUDE.md)  
64. OpenClaw — Personal AI Assistant, [https://openclaw.ai/](https://openclaw.ai/)  
65. openclaw/docs/concepts/architecture.md at main \- GitHub, [https://github.com/openclaw/openclaw/blob/main/docs/concepts/architecture.md](https://github.com/openclaw/openclaw/blob/main/docs/concepts/architecture.md)  
66. openclaw/docs/concepts/queue.md at main \- GitHub, [https://github.com/openclaw/openclaw/blob/main/docs/concepts/queue.md](https://github.com/openclaw/openclaw/blob/main/docs/concepts/queue.md)  
67. openclaw/docs/index.md at main \- GitHub, [https://github.com/openclaw/openclaw/blob/main/docs/index.md](https://github.com/openclaw/openclaw/blob/main/docs/index.md)  
68. Command queue \- OpenClaw Docs, [https://docs.openclaw.ai/concepts/queue](https://docs.openclaw.ai/concepts/queue)  
69. openclaw/docs/tools/skills.md at main \- GitHub, [https://github.com/openclaw/openclaw/blob/main/docs/tools/skills.md](https://github.com/openclaw/openclaw/blob/main/docs/tools/skills.md)  
70. Windows companion suite for OpenClaw \- System Tray app, Shared library, Node, and PowerToys Command Palette extension \- GitHub, [https://github.com/openclaw/openclaw-windows-node](https://github.com/openclaw/openclaw-windows-node)  
71. espressif/esp-openclaw-node • v1.0.0 \- ESP Component Registry, [https://components.espressif.com/components/espressif/esp-openclaw-node/versions/1.0.0/readme](https://components.espressif.com/components/espressif/esp-openclaw-node/versions/1.0.0/readme)  
72. Exec approvals \- OpenClaw Docs, [https://docs.openclaw.ai/tools/exec-approvals](https://docs.openclaw.ai/tools/exec-approvals)  
73. Security \- OpenClaw Docs, [https://docs.openclaw.ai/gateway/security](https://docs.openclaw.ai/gateway/security)  
74. OpenClaw Approval Design: What Needs Human Sign-Off, [https://www.codebridge.tech/articles/openclaw-approval-design-what-actually-needs-human-sign-off-in-a-production-workflow](https://www.codebridge.tech/articles/openclaw-approval-design-what-actually-needs-human-sign-off-in-a-production-workflow)  
75. openclaw/docs/concepts/compaction.md at main \- GitHub, [https://github.com/openclaw/openclaw/blob/main/docs/concepts/compaction.md](https://github.com/openclaw/openclaw/blob/main/docs/concepts/compaction.md)  
76. openclaw/docs/reference/session-management-compaction.md at main \- GitHub, [https://github.com/openclaw/openclaw/blob/main/docs/reference/session-management-compaction.md](https://github.com/openclaw/openclaw/blob/main/docs/reference/session-management-compaction.md)  
77. OpenClaw Human Approval for Sensitive Actions: Adding Gates Before Tools Execute, [https://zedly.ai/blog/openclaw-human-approval-for-sensitive-actions](https://zedly.ai/blog/openclaw-human-approval-for-sensitive-actions)  
78. OpenClaw Session Management Explained — The Dench Blog, [https://www.dench.com/blog/openclaw-session-management](https://www.dench.com/blog/openclaw-session-management)  
79. Session management \- OpenClaw Docs, [https://docs.openclaw.ai/concepts/session](https://docs.openclaw.ai/concepts/session)  
80. Gateway protocol \- OpenClaw Docs, [https://docs.openclaw.ai/gateway/protocol](https://docs.openclaw.ai/gateway/protocol)  
81. openclaw/docs/gateway/protocol.md at main \- GitHub, [https://github.com/openclaw/openclaw/blob/main/docs/gateway/protocol.md](https://github.com/openclaw/openclaw/blob/main/docs/gateway/protocol.md)  
82. Gateway runbook \- OpenClaw Docs, [https://docs.openclaw.ai/gateway](https://docs.openclaw.ai/gateway)  
83. OpenClaw — Personal AI Assistant \- GitHub, [https://github.com/openclaw/openclaw](https://github.com/openclaw/openclaw)  
84. shareAI-lab/learn-claude-code: Bash is all you need \- A nano claude code–like 「agent harness」, built from 0 to 1 \- GitHub, [https://github.com/shareAI-lab/learn-claude-code](https://github.com/shareAI-lab/learn-claude-code)  
85. Learn Claude Code — Free 20-Lesson Course (Build an Agent Harness from Scratch), [https://awesomeclaude.ai/learn-claude-code](https://awesomeclaude.ai/learn-claude-code)  
86. Learn Harness Engineering by Building a Mini Claude Code \- DEV Community, [https://dev.to/truongpx396/learn-harness-engineering-by-building-a-mini-claude-code-45a9](https://dev.to/truongpx396/learn-harness-engineering-by-building-a-mini-claude-code-45a9)  
87. s01-the-agent-loop.md \- shareAI-lab/learn-claude-code \- GitHub, [https://github.com/shareAI-lab/learn-claude-code/blob/main/docs/en/s01-the-agent-loop.md](https://github.com/shareAI-lab/learn-claude-code/blob/main/docs/en/s01-the-agent-loop.md)  
88. learn-claude-code/docs/en/s02-tool-use.md at main \- GitHub, [https://github.com/shareAI-lab/learn-claude-code/blob/main/docs/en/s02-tool-use.md](https://github.com/shareAI-lab/learn-claude-code/blob/main/docs/en/s02-tool-use.md)  
89. wulawulu/learn-claude-code-rs: Build an AI agent harness in Rust, from a minimal loop to tools, subagents, memory, teams, worktrees, MCP, and typed tool routing. \- GitHub, [https://github.com/wulawulu/learn-claude-code-rs](https://github.com/wulawulu/learn-claude-code-rs)  
90. learn-claude-code/docs/en/s06-context-compact.md at main \- GitHub, [https://github.com/shareAI-lab/learn-claude-code/blob/main/docs/en/s06-context-compact.md](https://github.com/shareAI-lab/learn-claude-code/blob/main/docs/en/s06-context-compact.md)  
91. s09-agent-teams.md \- shareAI-lab/learn-claude-code · GitHub, [https://github.com/shareAI-lab/learn-claude-code/blob/main/docs/en/s09-agent-teams.md](https://github.com/shareAI-lab/learn-claude-code/blob/main/docs/en/s09-agent-teams.md)  
92. learn-claude-code/docs/en/s07-task-system.md at main \- GitHub, [https://github.com/shareAI-lab/learn-claude-code/blob/main/docs/en/s07-task-system.md](https://github.com/shareAI-lab/learn-claude-code/blob/main/docs/en/s07-task-system.md)  
93. learn-claude-code/docs/en/s10-team-protocols.md at main \- GitHub, [https://github.com/shareAI-lab/learn-claude-code/blob/main/docs/en/s10-team-protocols.md](https://github.com/shareAI-lab/learn-claude-code/blob/main/docs/en/s10-team-protocols.md)  
94. learn-claude-code/docs/en/s05-skill-loading.md at main \- GitHub, [https://github.com/shareAI-lab/learn-claude-code/blob/main/docs/en/s05-skill-loading.md](https://github.com/shareAI-lab/learn-claude-code/blob/main/docs/en/s05-skill-loading.md)