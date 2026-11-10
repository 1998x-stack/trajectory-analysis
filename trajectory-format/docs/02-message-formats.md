# 02 · Message 与 Content Block 格式

## OpenAI Chat Completions

示例：[openai-chat-messages.json](../examples/openai-chat-messages.json)。

关键字段：

| 字段 | 说明 |
|---|---|
| `messages[].role` | `system`、`developer`、`user`、`assistant`、`tool` |
| `assistant.tool_calls[]` | 模型发起的工具调用数组 |
| `tool_calls[].id` | 工具调用 ID |
| `tool_calls[].function.arguments` | **JSON 字符串**，不是直接内嵌 JSON 对象 |
| `role=tool.tool_call_id` | 与调用的 `id` 对齐 |

此示例是“对话记录容器”，不是可直接提交的 API 请求；若实际调用模型，还需要正确的工具定义、有效模型和运行逻辑。

## OpenAI Responses API

示例：[openai-responses-items.json](../examples/openai-responses-items.json)。

Responses 使用 Typed Items，典型 `function_call` 与 `function_call_output` 通过 `call_id` 关联。示例把一次调用及返回项放在同一个**示意性 input item 列表**中，便于理解，不是某一单次响应的完整实际输出。不要机械套用 Chat Completions 的 `role=tool` 结构。

## Anthropic Messages API

示例：[anthropic-content-blocks.json](../examples/anthropic-content-blocks.json)。

关键点：Assistant 内容中可出现 `tool_use` block；工具执行结果一般作为后续 **user message** 中的 `tool_result` content block，使用 `tool_use_id` 对齐。工具参数 `input` 为对象；与 OpenAI Chat `arguments` 字符串不同。

## 三种格式的最重要差异

| 语义 | OpenAI Chat | OpenAI Responses | Anthropic |
|---|---|---|---|
| 工具调用 | `tool_calls[]` | `type=function_call` | `type=tool_use` content block |
| 工具调用参数 | JSON 字符串 | JSON 字符串 | JSON 对象 |
| 工具结果 | `role=tool` | `type=function_call_output` | `type=tool_result` content block |
| 关联键 | `tool_call_id` | `call_id` | `tool_use_id` |

## 转换注意事项

保留原始 Content Blocks 和 Provider Specific Items。多模态输入、并行 Tool Calls、Reasoning、拒答与中间输出类型可能无法一一映射；缺失项只能标为 unknown，不能补造时间、成本或推理内容。

官方资料见 [09 Sources](09-sources-and-versioning.md)。
