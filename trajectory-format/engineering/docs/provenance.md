# 五种来源：Native Trace Provenance

**绝不把 schema-shaped smoke fixture 当作真实轨迹**。工程中的 `fixtures/smoke/` 全部是合成数据，仅用于离线回归测试。

| 格式 | 可追溯上游样本 | 真实性与限制 |
|---|---|---|
| Claude Code | [sanitized/retry-rate-mixed-tools.jsonl](https://github.com/frederick-douglas-pearce/claude-code-sessions/blob/main/fixtures/sanitized/retry-rate-mixed-tools.jsonl) | 公开脱敏的 Session，可能被上游处理、截断或移除敏感信息 |
| Codex | [cfahlgren1/codex-sessions Dataset](https://huggingface.co/datasets/cfahlgren1/codex-sessions) | 公开的原生 Codex CLI rollout；**数据集 license=other**，使用前核对权利及许可 |
| OpenHands | [Agent Server reconnect fixture](https://github.com/OpenHands/OpenHands/blob/main/__tests__/fixtures/session-socket/reconnect-mid-stream.agent-server-1.47.0.json) | 来自真实 Agent Server 的集成测试捕获；使用 mock model，**不是生产真实模型推理** |
| LangGraph | [官方 persistence docs](https://docs.langchain.com/oss/python/langgraph/persistence) | 通过 `generate_langgraph.py` 调用真实运行时 `graph.invoke` + `get_state_history` 产生，但工作流属于教程示例 |
| SWE-agent | [function_calling_simple.traj](https://github.com/SWE-agent/SWE-agent/blob/main/trajectories/demonstrations/function_calling_simple.traj) | 上游公开的演示 Trajectory，非生产追踪数据 |

## 原生 Schema 的交叉验证

- Claude Code：`type`、`uuid`、`parentUuid`、`sessionId`、`message.content[].tool_use` / `tool_result`；字段并非具有官方稳定发布承诺的完整公开 Schema。
- Codex：<https://github.com/openai/codex/blob/main/codex-rs/app-server/tests/common/rollout.rs> 与 <https://github.com/openai/codex/blob/main/codex-rs/rollout/src/recorder.rs>，`session_meta`、`turn_context`、`response_item`、`event_msg`；不要混同 TUI 测试事件文件。
- OpenHands：<https://github.com/OpenHands/OpenHands/blob/main/src/types/agent-server/core/events/action-event.ts>、<https://github.com/OpenHands/OpenHands/blob/main/src/types/agent-server/core/events/observation-event.ts>；注意 Socket 包装的 `event` 以及 `before/after` 去重。
- LangGraph：<https://github.com/langchain-ai/langgraph/blob/main/libs/langgraph/langgraph/types.py> 的 `StateSnapshot` 以及 debug stream 类型。
- SWE-agent：<https://swe-agent.com/latest/usage/trajectories/> 的 `trajectory[].{thought,action,observation,response}`。

## 复现与可信度

下载需明确加 `--accept-source-terms`。脚本只做基本 JSON/JSONL 可解析检查；**尚未自动 pin 上游 commit/dataset revision，也不保证远端内容不变**。建议研究时额外保存下载日期、源 URL、SHA-256 和上游版本；转换后应人工抽查至少一例 Tool Call / Result 以及异常分支。

第三方 Session 可能包含私有代码、Prompt、密钥、命令输出、文件路径以及用户数据。此仓库不再分发这些数据；在复制、共享或上传前必须自行检查许可、使用条件和隐私。
