# 04 · ATIF（Agent Trajectory Interchange Format）

官方规范：[Harbor RFC 0001](https://github.com/harbor-framework/harbor/blob/main/rfcs/0001-trajectory-format.md)。本仓库示例基于 **ATIF-v1.8**：[atif-v1.8.json](../examples/atif-v1.8.json)。

## 核心对象

| 字段 | 是否必须 | 意义 |
|---|---|---|
| `schema_version` | 是 | 例如 `ATIF-v1.8` |
| `agent.name` / `agent.version` | 是 | 生产该轨迹的 Agent |
| `steps[]` | 是 | 对话、Agent 行为、Observation 的有序序列 |
| `session_id` | 否（v1.7+） | Run 级 ID，不保证单个文档唯一 |
| `trajectory_id` | 有条件 | 文档级 ID；嵌入式子 Agent 必须提供 |
| `final_metrics` | 否 | 聚合 Token、Cost 等 |
| `subagent_trajectories` | 否 | 嵌套 Agent 轨迹 |

每个 `StepObject` 包含从 1 开始的 `step_id`、`source`（`system` / `user` / `agent`）以及消息、调用、Observation 等字段。**工具的 observation 不必独立占一条 user/tool Step**。

### Tool Calls 与 Observation

```text
steps[i].tool_calls[j].tool_call_id
            == steps[i].observation.results[k].source_call_id
```

`ToolCallSchema` 的 `function_name` 为字符串，`arguments` 是 **JSON 对象**；与 OpenAI Chat 的 JSON 字符串不同。

## v1.7 / v1.8 注意点

- v1.7 新增嵌套 `subagent_trajectories`、`trajectory_id`，并将根 `session_id` 改为可选。
- 子 Agent Reference 的 `session_id` **不能单独作为嵌入式轨迹解析键**；使用 `trajectory_id` / `trajectory_path`。
- `llm_call_count=0` 表示确定性非 LLM dispatch；不应混入 SFT target。
- `is_copied_context` 标记复制的上下文，应在 SFT 训练时过滤。
- v1.8 支持 audio content part，音频通过文件路径引用而非原始实时流。

## 注意：结构校验与官方符合性校验的区别

`scripts/validate_examples.py` 只做本地基本结构和 ID 关联检查。**不能替代 Harbor 官方 Pydantic 校验器**。版本升级请检查 RFC 及官方 Model，不要凭文档猜测新字段。

## 为什么适合交换

ATIF 的强项是把 Message、Tool Action、Observation、Metrics 和 Subagent 放入单个可序列化轨迹；但它不等于实时 Event Bus，也不天然提供分布式 Span 耗时信息或环境状态快照。
