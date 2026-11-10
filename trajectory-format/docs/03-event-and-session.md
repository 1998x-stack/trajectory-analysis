# 03 · Native Session JSONL 与 Event Stream

## JSONL 的用途

Codex、Claude Code、Pi 等 Coding Agent 通常使用或可导出原生 Session 记录。**它们原生 JSONL 的字段并不相同**，仅扩展名相同不能代表 Schema 兼容。Hugging Face Agent Traces Viewer 支持其中多种原生日志。

## HF Session Trace Simple Format（STS）

示例：[hf-sts.jsonl](../examples/hf-sts.jsonl)。

第一行必须是 `type=session`，需要 `harness` 和 `id`；后续每行是 `type=message`，其中包含 `message.role` 和 `message.content`。可选 `toolCalls`、`toolCallId`、`reasoningContent`、`timestamp`（epoch milliseconds）、`model`。**注意 camelCase：和 OpenAI Chat 字段不同。**

STS 适合低门槛显示单次 Session 的消息和工具结果，未强制提供 Span 树、RL reward 或环境状态。

## 通用 Event 流（自定义）

示例：[custom-event-stream.jsonl](../examples/custom-event-stream.jsonl)。

本仓库定义 `event_id`、`sequence`、`timestamp`、`event_type`、`tool_call_id` 和 `payload` 的示意结构；它**不是 Claude Code、Codex、OpenHands 任一方的官方事件协议**。

与 Message 不同，工具“发起”与“完成”可写成两个事件；对于异步工具、流式消息、错误和重试更有表现力。若要重放，除了 event 还需要：

- 工具调用关联（`tool_call_id` / `parent_event_id`）。
- 明确的排序规则与时钟语义。
- 工具副作用和运行环境的版本/快照。
- 失败重试、并发和幂等策略。

## Raw-first 实践

原始 JSONL 最好**只读保存**，解析器另行输出 normalized 事件，记录每条事件的源文件路径或字节偏移，方便排错。公开分享时必须处理隐私数据、密钥与私人代码。

相关：[01 格式全景](01-landscape.md) · [08 Canonical](08-canonical-design.md)。
