# 05 · OpenTelemetry、OpenInference 和 Observability 原生格式

## 三个层次

1. **OpenTelemetry 数据模型**：Trace、Span、Event、Link、Resource。
2. **OTLP（OpenTelemetry Protocol）**：标准化遥测传输，Protobuf 及其 JSON 映射。
3. **GenAI Semantic Conventions / OpenInference**：约定 AI / Agent 操作的 Span 名称和属性，而非取代 OTel。

## OTLP GenAI 示例

[otlp-genai.json](../examples/otlp-genai.json) 展示 `resourceSpans → scopeSpans → spans`，使用 `traceId`、`spanId`、`parentSpanId`、`startTimeUnixNano`、`endTimeUnixNano` 和 typed `attributes`。示例中一个 Agent Span 包含一个 Model Span，时间戳是纳秒字符串。

这是**教学用精简 OTLP/JSON 结构**。不同 OTLP Exporter 的可选字段、具体采集配置和 GenAI semconv 版本会不同；需用实际 OTLP 接收端与 protobuf 校验产品互操作性。

## OpenInference 示例

[openinference-logical-spans.json](../examples/openinference-logical-spans.json) 是方便阅读的**逻辑 JSON 视图**，并非可以直接发送到 Collector 的 OTLP Payload；属性如 `openinference.span.kind`、`tool.name`、`input.value`、`output.value` 表达 AI 操作。

## 与 LangSmith / Langfuse 等的关系

LangSmith 有 Run/Run Tree；Langfuse 有 Trace + Typed Observation；OpenAI Agents SDK 有 Trace + Span；MLflow 有自己的 TraceData / Span Model。这些都可以作为可观测性 Adapter 来源，**不能简单假设原生导出就是同一 JSON Schema**。

## 关键边界

- Span ≠ Message。一个 LLM Span 的 Input 可能重复包含前面所有 Messages。
- Span ≠ Environment Snapshot。不等于可确定性回放。
- Parent Span、Span Links、工具 Call ID 分别解决不同的关系，不可直接互相代替。
- Provider 输出的 Token、Cost、事件时钟可能存在不同的统计口径。
- 记录 prompt / tool result 到属性会引入隐私、成本和体积问题；生产环境须控制采样、脱敏与存储策略。

原始资料见 [09 Sources](09-sources-and-versioning.md)。
