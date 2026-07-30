# Xiaolin LLM Engineering Interview Notes

> **来源站点**: [小林面试笔记](https://xiaolinnote.com/ai/llm/llm_info.html)  
> **抓取日期**: 2026-07-30  
> **资料性质**: 第三方网页机械提取  
> **证据状态**: to-verify

本目录保存“大模型工程面试题介绍”入口页和 22 个子页的结构化 Markdown 提取稿，用于本地全文搜索、课程定位和问题目录整理。网页内容不是本仓库的已核验结论；涉及框架、协议、论文、版本和工程判断时，仍需回到源码或官方资料核验。

转换保留标题、正文、列表、表格、代码块、链接和远程图片 URL；重复的站点推广尾部已移除，图片文件本身未下载。重新抓取可运行 [`../../scripts/fetch-xiaolinnote.py`](../../scripts/fetch-xiaolinnote.py)。

## 章节目录

| 序号 | 标题 | 本地提取稿 | 原始网页 |
|---:|---|---|---|
| 0 | 大模型工程面试题介绍 | [00-llm-interview-guide.md](00-llm-interview-guide.md) | [source](https://xiaolinnote.com/ai/llm/llm_info.html) |
| 1 | 1. 什么是大语言模型？和传统 NLP 模型有什么区别？ | [01-what-is-llm.md](01-what-is-llm.md) | [source](https://xiaolinnote.com/ai/llm/what_is_llm.html) |
| 2 | 2. 讲讲 Transformer 架构基本原理？Encoder 和 Decoder 是什么？ | [02-transformer-architecture.md](02-transformer-architecture.md) | [source](https://xiaolinnote.com/ai/llm/transformer_architecture.html) |
| 3 | 3. 多头注意力（MHA）有哪些局限？MQA、GQA、Flash Attention 怎么解决？ | [03-mha-mqa-gqa-flash-attention.md](03-mha-mqa-gqa-flash-attention.md) | [source](https://xiaolinnote.com/ai/llm/mha_mqa_gqa_flash_attention.html) |
| 4 | 4. 大模型的位置编码是干什么用的？sin/cos、RoPE、ALiBi 有什么区别？ | [04-position-encoding.md](04-position-encoding.md) | [source](https://xiaolinnote.com/ai/llm/position_encoding.html) |
| 5 | 5. 什么是大模型项目的分词器？原理是什么？ | [05-tokenizer.md](05-tokenizer.md) | [source](https://xiaolinnote.com/ai/llm/tokenizer.html) |
| 6 | 6. 大模型是怎么训练出来的？ | [06-llm-training.md](06-llm-training.md) | [source](https://xiaolinnote.com/ai/llm/llm_training.html) |
| 7 | 7. 什么是 Scaling Law？大模型的「涌现能力」是怎么回事？ | [07-scaling-law-emergence.md](07-scaling-law-emergence.md) | [source](https://xiaolinnote.com/ai/llm/scaling_law_emergence.html) |
| 8 | 8. 大模型微调的方案有哪些？ | [08-finetuning.md](08-finetuning.md) | [source](https://xiaolinnote.com/ai/llm/finetuning.html) |
| 9 | 9. 请讲一下 LoRA 技术，除了减少参数量，它还有哪些优点？ | [09-lora.md](09-lora.md) | [source](https://xiaolinnote.com/ai/llm/lora.html) |
| 10 | 10. SFT 之后还有哪些 Post-Training？RLHF、DPO、GRPO、拒绝采样什么关系？ | [10-post-training.md](10-post-training.md) | [source](https://xiaolinnote.com/ai/llm/post_training.html) |
| 11 | 11. 大模型的 DPO 和 PPO 的区别是什么？ | [11-dpo-vs-ppo.md](11-dpo-vs-ppo.md) | [source](https://xiaolinnote.com/ai/llm/dpo_vs_ppo.html) |
| 12 | 12. 大模型生成文本时的解码策略有哪些？贪心、Beam Search、采样分别什么时候用？ | [12-decoding-strategies.md](12-decoding-strategies.md) | [source](https://xiaolinnote.com/ai/llm/decoding_strategies.html) |
| 13 | 13. 大模型的参数：温度值、Top-P、Top-K 分别是什么？各个场景下的最佳设置是什么？ | [13-temperature-top-p-top-k.md](13-temperature-top-p-top-k.md) | [source](https://xiaolinnote.com/ai/llm/temperature_top_p_top_k.html) |
| 14 | 14. KV Cache 是什么？Prompt Caching 的原理是什么？ | [14-kv-cache-prompt-caching.md](14-kv-cache-prompt-caching.md) | [source](https://xiaolinnote.com/ai/llm/kv_cache_prompt_caching.html) |
| 15 | 15. 大模型量化是什么？INT8/INT4/AWQ/GPTQ 怎么选？ | [15-quantization.md](15-quantization.md) | [source](https://xiaolinnote.com/ai/llm/quantization.html) |
| 16 | 16. 如何写好 Prompt？分享下 Prompt 工程实践经验？ | [16-prompt-engineering.md](16-prompt-engineering.md) | [source](https://xiaolinnote.com/ai/llm/prompt_engineering.html) |
| 17 | 17. 什么是 CoT？为啥效果好？它有什么缺点或局限性？ | [17-cot.md](17-cot.md) | [source](https://xiaolinnote.com/ai/llm/cot.html) |
| 18 | 18. 大模型为什么会出现幻觉？怎么缓解？ | [18-hallucination.md](18-hallucination.md) | [source](https://xiaolinnote.com/ai/llm/hallucination.html) |
| 19 | 19. MoE 混合专家模型是什么？DeepSeek V3、Qwen 为什么用 MoE？ | [19-moe.md](19-moe.md) | [source](https://xiaolinnote.com/ai/llm/moe.html) |
| 20 | 20. 大模型部署有哪些主流方案？vLLM、TGI、llama.cpp、SGLang 实际项目里怎么选？ | [20-deployment-frameworks.md](20-deployment-frameworks.md) | [source](https://xiaolinnote.com/ai/llm/deployment_frameworks.html) |
| 21 | 21. 大模型能力评测指标有哪些？ | [21-evaluation-metrics.md](21-evaluation-metrics.md) | [source](https://xiaolinnote.com/ai/llm/evaluation_metrics.html) |
| 22 | 22. 对比使用过哪些主流大模型？你们项目中最终选用了哪个模型？为什么？ | [22-model-selection.md](22-model-selection.md) | [source](https://xiaolinnote.com/ai/llm/model_selection.html) |
