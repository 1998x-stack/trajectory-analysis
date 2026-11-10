# 09 · 官方来源、规范版本和可验证范围

截至 2026-11-10 整理。这里优先列规范或项目官方资料；供应商和社区规范会持续更新。

| 名称 | 官方来源 | 本项目覆盖内容 |
|---|---|---|
| OpenAI Chat Completions | [API reference](https://platform.openai.com/docs/api-reference/chat) | Messages / Tool Calls |
| OpenAI Responses | [Responses API](https://platform.openai.com/docs/api-reference/responses) | Typed Items、`function_call_output` |
| Anthropic Messages | [Tool use](https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview) | `tool_use` / `tool_result` Content Blocks |
| ATIF | [Harbor RFC 0001](https://github.com/harbor-framework/harbor/blob/main/rfcs/0001-trajectory-format.md) | ATIF-v1.8 |
| HF STS | [Session Traces Format](https://huggingface.co/docs/hub/session-traces-format) | Header + Message JSONL |
| Hugging Face Agent Traces | [Agent Traces](https://huggingface.co/docs/hub/agent-traces) | 原生 Agent Session Viewer |
| OpenTelemetry GenAI | [Semantic Conventions](https://github.com/open-telemetry/semantic-conventions-genai) | GenAI Span 属性 |
| OTLP | [OTLP Specification](https://opentelemetry.io/docs/specs/otlp/) | Trace/Span 传输模型 |
| OpenInference | [OpenInference](https://github.com/Arize-ai/openinference) | AI Span 语义属性 |
| LangSmith | [Observability concepts](https://docs.langchain.com/langsmith/observability-concepts) | Run / Trace Tree 概念 |
| Langfuse | [Data model](https://langfuse.com/docs/observability/data-model) | Trace / Observation 概念 |
| MLflow | [Tracing](https://mlflow.org/docs/latest/genai/tracing/) | MLflow Trace 概念 |

## 如何验证

1. JSON / JSONL 语法：`python3 trajectory-format/scripts/validate_examples.py`。
2. 示例内部关系：脚本检查 Tool Call ID、事件排序、Span ID 等。
3. ATIF：使用 Harbor 官方模型校验最新版本，关注 RFC breaking changes。
4. OTLP：使用 OpenTelemetry Proto 与 Collector 对接测试；本库脚本只做基础形状检查。
5. Canonical：可使用 JSON Schema Draft 2020-12 验证 `schema/canonical-trajectory.schema.json`。

## 更新纪律

- 每个示例说明“官方规范形状 / 简化逻辑结构 / 本仓库自定义”。
- 规范改变时记录版本、示例修改和不兼容字段。
- 不复制真实私有 Session 到公共仓库；公开轨迹先做敏感信息检查。
- 不把“可解析 JSON”当作“符合官方协议”。
