# 08 · 面向统一 Viewer 的 Canonical Event Model（项目提案）

这是一个**项目自定义 Schema 草案 v0.1.0**，不是社区标准。相关文件：

- [JSON 示例](../examples/canonical-trajectory.json)
- [JSON Schema Draft 2020-12](../schema/canonical-trajectory.schema.json)
- [Event JSONL](../examples/custom-event-stream.jsonl)

## 设计目标

1. 同一 API 能接收 OpenAI / Anthropic Messages、原生 JSONL、ATIF、OTel Spans。
2. 保留来源可追踪性；不要在标准化时丢掉原始 Provider Payload。
3. 同时展示按时间的 Step Timeline 与父子关系图，避免并发被强行线性化。
4. 导出 STS / ATIF / 训练数据集时显式说明字段损失。

## Event 字段

| 字段 | 含义 |
|---|---|
| `event_id` | 当前 Session 中唯一事件 |
| `session_id` | 放在根对象上 |
| `sequence` | 处理顺序（可用于确定稳定的 Viewer 顺序） |
| `timestamp` | ISO 8601，事件时刻 |
| `actor.type / id` | 谁生成事件 |
| `event_type` | message、tool_call、tool_result、state_update、checkpoint、handoff、error |
| `tool_call_id` | 工具 Call / Result 关联（可选） |
| `parent_event_id` | 父事件（可选） |
| `trace_id / span_id / parent_span_id` | Telemetry 关联（可选） |
| `payload` | 类型相关的具体 JSON 数据 |
| `source.format / raw_ref` | 源格式与原始数据地址 |

## 必须显式设计的边界

- `sequence` 是事件**接收/解析顺序**，并不保证所有物理执行严格串行；并发由父子关系和时间重叠呈现。
- `parent_event_id` 和 `parent_span_id` 不等价：前者是业务事件归属，后者是遥测操作归属。
- `source.raw_ref` 只是引用；实际服务需搭配哈希、偏移量、访问控制和加密策略。
- `payload` 暂不细分 discriminator schema；后续稳定后可以定义各 `event_type` 的 JSON Schema `oneOf`。
- 该 v0.1.0 示例仅处理单 Session，不包含完整跨 Session Handoff、全局重试与 Snapshot State。

## 建议的落地步骤

Phase 1：支持 OpenAI Chat、HF STS、ATIF 三种解析器，Viewer 展示 Message 与 Tool Timeline。

Phase 2：扩展原生 Codex / Claude Code JSONL Adapter，同时支持并发 Action/Observation 和原始记录定位。

Phase 3：接入 OTLP + OpenInference，构建 Span Tree、Latency/Token/Cost 汇总。

Phase 4：构建 Dataset Exporter（ATIF/Parquet）并增加转换损失报告与版本化测试。
