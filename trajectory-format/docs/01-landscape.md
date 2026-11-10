# 01 · 轨迹格式的五个层次

## 定义

AI Agent Trajectory 记录任务过程中**用户输入、模型推理输出、工具动作、环境反馈和结果**。但不同系统记录的对象并不相同：

| 语义层 | 核心对象 | 常见来源 | 典型问题 |
|---|---|---|---|
| Conversation | role/message/content/tool call | OpenAI、Anthropic | Agent 与谁说了什么？ |
| Session Event | append-only event / JSONL | Codex、Claude Code、OpenHands | 按什么顺序发生了什么？ |
| Interchange Trajectory | agent / steps / tool_calls / observation | ATIF | 不同 Agent 如何交换轨迹？ |
| Observability | trace / span / parent / attributes | OTel、OpenInference、LangSmith | 哪个操作慢、贵或失败？ |
| Training / Evaluation | episode / transition / reward / outcome | Benchmark、Agent RL | 哪个行为导致成功或失败？ |

## 别混淆物理与逻辑格式

- `JSON`：可保存整个 Trajectory / Trace / Episode。
- `JSONL`：每行一个独立 JSON 值，适合持续追加和流式消费。
- `Parquet`：适合分析与训练批处理，仍需约定每行代表 Step、Event 或 Episode。
- `OTLP`：Telemetry 交换协议；不等同于 Agent Session 文件。
- `SQLite` / Checkpoint：可存执行状态，并不是通用轨迹交换格式。

## 同一次工具调用的四种表示

1. Chat：assistant 发 `tool_calls`，随后收到 `role=tool` 消息。
2. ATIF：`steps[].tool_calls` 与 `steps[].observation.results` 通过 ID 关联。
3. Event：`tool_call` 和 `tool_result` 各是一个可独立排序的事件。
4. OTel：工具调用是 Span；父 Span 表示 Agent Run，关联 Context。

**不可逆性**：如果只有 Span 耗时和 Token 计数，就无法凭空恢复工具输出；如果只有 Messages，就不能可靠推断工具实际执行开始时刻、重试、部署拓扑。

## 选型速览

- 做聊天重放：Messages / HF STS。
- 做跨 Agent 导出：ATIF，保留原始 JSONL。
- 做生产监控：OTel GenAI + OpenInference 语义属性。
- 做任务训练：Episode + Reward / Outcome + Token 级别训练记录（如果确有采集）。
- 做断点恢复：运行时 State/Checkpoint + 环境快照，不可只存 Messages。

下一篇：[02 Message 格式](02-message-formats.md)。
