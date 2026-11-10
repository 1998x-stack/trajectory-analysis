# 06 · Trajectory、SFT、RL Rollout 与 Benchmark

## 训练数据不等于运行日志

Agent Rollout / Episode 一般围绕任务、状态（Observation）、动作（Action）、结果（Next Observation）、奖励（Reward）、终止条件（Done）构造。示例：[rl-episode.json](../examples/rl-episode.json)。

本示例是**教学用自定义 Episode Schema**，并非 verl、TRL、OpenRLHF 或某个 Benchmark 的官方格式。

## 一份数据集的常见维度

| 层次 | 常见字段 | 用途 |
|---|---|---|
| Task | `episode_id`, `instruction`, `environment` | 测试环境与任务关联 |
| Transition | `observation`, `action`, `next_observation` | 轨迹重建 |
| Outcome | `success`, `reward`, `done` | 评测、训练信号 |
| LLM sampling（可选） | `token_ids`, `logprobs`, `masks` | Token 级学习 |
| Metrics | `latency`, `tokens`, `cost` | 效率分析 |

## SFT 和 RL 常见转换问题

- SFT 可能需要准确重建模型当时看到的 Prompt、工具定义、消息角色、Tokenization 与 Target Mask。
- RL 训练还可能依赖 Behavior Policy Logprobs、Reward、Value/Advantage、Returns 等；**这些值无法从普通文本聊天记录推算为真实采样值**。
- Multi-agent / branching 轨迹不能简单压平成单个线性轨迹而不丢失执行信息。
- ATIF 的 `is_copied_context` 和 `llm_call_count=0` 等字段对于筛选训练样本有重要意义。
- 不同 Benchmark 的成功标准不同，需要显式记录评分器与版本。

## 导出

适合数据湖的方式是拆出 `episodes`、`steps`、`tool_calls`、`observations` 等逻辑表写入 Parquet，同时保留原始文件引用与版本号。

相关：[04 ATIF](04-atif.md) · [07 字段映射](07-field-mapping.md)。
