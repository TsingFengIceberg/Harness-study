# Xiaolin LLM Tool Calling Interview Notes

> **来源站点**: [小林面试笔记](https://xiaolinnote.com/ai/tools/tools_info.html)  
> **抓取日期**: 2026-07-30  
> **资料性质**: 第三方网页机械提取  
> **证据状态**: to-verify

本目录保存“LLM工具调用面试题介绍”入口页和 16 个子页的结构化 Markdown 提取稿，用于本地全文搜索、课程定位和问题目录整理。网页内容不是本仓库的已核验结论；涉及框架、协议、论文、版本和工程判断时，仍需回到源码或官方资料核验。

转换保留标题、正文、列表、表格、代码块、链接和远程图片 URL；重复的站点推广尾部已移除，图片文件本身未下载。重新抓取可运行 [`../../scripts/fetch-xiaolinnote.py`](../../scripts/fetch-xiaolinnote.py)。

## 章节目录

| 序号 | 标题 | 本地提取稿 | 原始网页 |
|---:|---|---|---|
| 0 | LLM工具调用面试题介绍 | [00-tools-interview-guide.md](00-tools-interview-guide.md) | [source](https://xiaolinnote.com/ai/tools/tools_info.html) |
| 1 | 1. 什么是 Function Calling？原理是什么？ | [01-function-calling.md](01-function-calling.md) | [source](https://xiaolinnote.com/ai/tools/1_function_calling.html) |
| 2 | 2. LLM 是如何学会调用外部工具的？ | [02-llm-tool-learning.md](02-llm-tool-learning.md) | [source](https://xiaolinnote.com/ai/tools/2_llm_tool_learning.html) |
| 3 | 3. 大模型的 Function Call 能力是怎么训练出来的？ | [03-fc-training.md](03-fc-training.md) | [source](https://xiaolinnote.com/ai/tools/3_fc_training.html) |
| 4 | 4. 什么是 MCP（模型上下文协议）？讲讲它的核心内容？ | [04-what-is-mcp.md](04-what-is-mcp.md) | [source](https://xiaolinnote.com/ai/tools/4_what_is_mcp.html) |
| 5 | 5. MCP 由哪几部分组成？ | [05-mcp-components.md](05-mcp-components.md) | [source](https://xiaolinnote.com/ai/tools/5_mcp_components.html) |
| 6 | 6. MCP 和 Function Calling 有什么区别？有没有实际跑过 MCP？ | [06-mcp-vs-fc.md](06-mcp-vs-fc.md) | [source](https://xiaolinnote.com/ai/tools/6_mcp_vs_fc.html) |
| 7 | 7. Function Calling 也属于工具调用，请问什么场景下使用 Function Calling，什么场景下使用 MCP？ | [07-fc-vs-mcp-usage.md](07-fc-vs-mcp-usage.md) | [source](https://xiaolinnote.com/ai/tools/7_fc_vs_mcp_usage.html) |
| 8 | 8. 为什么有些特定的推理模型不支持 MCP 协议？ | [08-reasoning-no-mcp.md](08-reasoning-no-mcp.md) | [source](https://xiaolinnote.com/ai/tools/8_reasoning_no_mcp.html) |
| 9 | 9. Skill 是什么？ | [09-skill.md](09-skill.md) | [source](https://xiaolinnote.com/ai/tools/9_skill.html) |
| 10 | 10. MCP 和 Agent Skill 的区别是什么？ | [10-mcp-vs-skill.md](10-mcp-vs-skill.md) | [source](https://xiaolinnote.com/ai/tools/10_mcp_vs_skill.html) |
| 11 | 11. Function Calling、Skill、MCP 这三个有什么区别？ | [11-fc-skill-mcp.md](11-fc-skill-mcp.md) | [source](https://xiaolinnote.com/ai/tools/11_fc_skill_mcp.html) |
| 12 | 12. 什么是 A2A 协议？它和 MCP 协议的区别是什么？ | [12-a2a-protocol.md](12-a2a-protocol.md) | [source](https://xiaolinnote.com/ai/tools/12_a2a_protocol.html) |
| 13 | 13. MCP 协议通常采用什么通信方式？ | [13-mcp-transport.md](13-mcp-transport.md) | [source](https://xiaolinnote.com/ai/tools/13_mcp_transport.html) |
| 14 | 14. 说说 WebSocket 和 SSE 通信的区别及局限性？ | [14-sse-vs-websocket.md](14-sse-vs-websocket.md) | [source](https://xiaolinnote.com/ai/tools/14_sse_vs_websocket.html) |
| 15 | 15. 为什么要用 WebRTC 协议？它和 WebSocket（WS）在 AI 对话流中的核心差异是什么？ | [15-webrtc-vs-ws.md](15-webrtc-vs-ws.md) | [source](https://xiaolinnote.com/ai/tools/15_webrtc_vs_ws.html) |
| 16 | 16. 有没有用过大模型的网关框架？网关层解决了什么问题？ | [16-llm-gateway.md](16-llm-gateway.md) | [source](https://xiaolinnote.com/ai/tools/16_llm_gateway.html) |
