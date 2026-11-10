# Native Schema → trajlab/v1 字段对照

核心 Event 为：`event_id`、`sequence`、`kind`、`actor`、`summary`、`payload`、`source.{record_index,pointer,sha256,source_id}`，可选 `timestamp`、`call_id`、`parent_source_id`。

## Claude Code

| Native path | Canonical | 说明 |
|---|---|---|
| `type=user / assistant` + `message.content` | message | 字符串或 Content Blocks |
| `message.content[].type=thinking` | thought | Block 保留 |
| `message.content[].type=tool_use` | tool_call | `id → call_id`，`name/input → payload` |
| `message.content[].type=tool_result` | tool_result | `tool_use_id → call_id` |
| `uuid` / `parentUuid` | source ID / parent source ID | 非 OTel Span 关系 |
| `message.model` / `message.usage` | payload | 多条内容块可能重复 Usage |
| `progress` / `system` | state/error | 仅映射部分元数据 |
| `cwd`、`gitBranch`、`permissionMode` | omitted | 不保证可逆 |

## Codex

| Native path | Canonical | 说明 |
|---|---|---|
| `session_meta.payload` | metadata | id、cwd、originator、cli_version、model_provider |
| `turn_context.payload` | state | model、cwd、turn_id、approval_policy |
| `response_item.payload.type=message` | message | role / content |
| `response_item.payload.type=function_call` | tool_call | call_id、name、arguments |
| `response_item.payload.type=function_call_output` | tool_result | 按 call_id 关联 |
| `response_item.payload.type=reasoning` | thought | 仅显示 summary |
| `event_msg.payload.type=token_count` | metadata | input/output usage info |
| `event_msg.payload.type=user_message` | omitted | 避免与 response_item 重复 |
| `base_instructions`、其它 TUI 附加信息 | omitted | 不自动存入 Canonical |

## OpenHands

| Native path | Canonical | 说明 |
|---|---|---|
| `before[]/after[]/events[]` | 解包源行 | 对同 event.id 去重 |
| `event.kind=MessageEvent` | message | llm_message / message |
| `event.kind=ActionEvent` | tool_call | tool_name、tool_call_id、action、thought |
| `event.kind=ObservationEvent` | tool_result | tool_call_id、observation |
| `event.kind=AgentErrorEvent` | error | error field |
| 其余 kind | state | Opaque 状态可能大量遗漏 |

## LangGraph

| Native path | Canonical | 说明 |
|---|---|---|
| `StateSnapshot.values` | checkpoint.payload.values | 执行状态 |
| `StateSnapshot.next` | checkpoint.payload.next | 计划执行的节点 |
| `StateSnapshot.config / parent_config` | checkpoint.payload | checkpoint 关系 |
| `StateSnapshot.tasks` | checkpoint.payload.tasks | 异步节点/错误状态 |
| `created_at` / `metadata` | timestamp / payload | 当前记录顺序可能为**倒序** |
| `debug stream type=task / task_result` | state | 不假定每个 task 都是外部工具调用 |

## SWE-agent

| Native path | Canonical | 说明 |
|---|---|---|
| `trajectory[].thought / response` | thought | 思路与响应文字 |
| `trajectory[].action` | tool_call | 合成 `swe-step-N` 关联键（并非原生 Call ID） |
| `trajectory[].observation` | tool_result | 与对应 Step 关联 |
| `trajectory[].state` / `execution_time` | omitted | 当前未映射 |
| 根 `history`、`info` | omitted + warning | 根部元数据不参与逐 Step Leaf 覆盖率 |

## Loss Report 的口径

`mapped` / `omitted` 均按原始 JSON 的叶子字段路径计算。`mapped_leaf_ratio` = 已标记映射叶子数 /（已标记映射叶子数 + 未映射叶子数）。某些叶子被整体 Block 保留，而一些值被重新组织，因此该指标**既不是语义保真度，也不代表可重新生成完全一致的原生 JSON/JSONL**。

已知边界：原始时间不全、独立并行工具执行、重试与版本变化、嵌套子 Agent、Environment Checkpoint、Span 关系需要进一步扩展。保留 Raw + SHA 后才能做可审计的转换复核。

## SWE-agent Demonstration Export (history[] without trajectory[])

公开的 `function_calling_simple.traj` 仅有 `history[]`。在这一形式下，`history[].role=assistant` 的 `tool_calls[].id` 表示真实的 Call ID，`history[].role=tool` 的 `tool_call_ids[]` 给出返回关联。Adapter 现在支持此形式并保留原生关联 ID；区别于有 `trajectory[]` 时合成的 `swe-step-N`。

### OpenHands Socket Deltas（真实集成测试发现）

对于不在 durable `event` 包装内的 `type=delta`，Converter 会把 `item_id`、`attempt`、`order`、`kind`、`content`、`chunk_id`、`choice_index` 保存在一个 `kind=state` 的事件 Payload 中，而不会猜测它一定是最终回答。`type=sync` 的 `from_seq` 作为 Metadata 保存。这里的流式增量不等于完整 LLM Message。
