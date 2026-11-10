# 公开 Agent Trajectory 转换实测报告（2026-11-10）

> [GitHub Actions 原始测试运行 #42752521707](https://github.com/1998x-stack/trajectory-analysis/actions/runs/42752521707) · Commit [f616bb5](https://github.com/1998x-stack/trajectory-analysis/commit/f616bb5232be0069e2ffb2960b4dfc263263e881) · 结果：**offline-adapters = success；public-real-compatibility = success**。

## 实测输入

CI 在临时 GitHub Runner 上下载四份公开上游样本，并调用当前安装的 LangGraph 真实执行引擎生成第五份快照；原始轨迹未提交仓库，上传的 Artifact 只包含聚合指标。数据源与真实性分级：[Provenance](provenance.md)。

## 结果

| 来源格式 | 输入记录数 | 标准化事件数 | 映射叶子字段 | 未映射叶子字段 | 映射覆盖率 | 孤立工具结果警告 |
|---|---:|---:|---:|---:|---:|---:|
| Claude Code | 232 | 200 | 3875 | 3327 | **53.8%** | 0 |
| Codex | 65 | 36 | 264 | 224 | **54.1%** | 0 |
| OpenHands | 47 | 47 | 354 | 368 | **49.0%** | 0 |
| LangGraph | 3 | 3 | 47 | 0 | **100.0%** | 0 |
| SWE-agent | 12 | 17 | 83 | 0 | **100.0%** | 0 |

**重要：这里的“映射覆盖率”不是语义保真率。**

统计口径是 Adapter 声明的 JSON Pointer 叶子字段覆盖率：mapped / (mapped + omitted)。其分母不包括未作为某条输入事件审计的外层根元数据（例如 SWE-agent 的 `history[]` 之外的键）；整体 Content Block 被复制到 Payload 时会把内部叶子标记为 mapped。事件数与输入记录数也不能作为数据损失比例，因为一个输入记录可能产生多个事件，而有些记录只承载重复的 UI 事件。

因此 **LangGraph、SWE-agent 100% 不代表任何形式的全字段无损或执行回放可逆**，只能说明对本次选取记录的叶子字段分类为全部映射。不同框架之间的比例也不应直接比较 Agent 性能。

## 实际发现及工程修复

1. **SWE-agent 双轨迹形态**：常见文档强调 `trajectory[]`，但公开的 `function_calling_simple.traj` 实际只有 `history[]`。原始测试因此失败；修复后 Adapter 支持两种结构，并保留历史里的 `tool_calls[].id` / `tool_call_ids[]`。
2. **OpenHands Socket 数据不等于 Event 数组**：其公开集成测试文件具有 `before` / `after` 重连片段，并包含 `type=delta` 和 `type=sync` 帧。新增 Delta 字段映射后，本次 mapped 从 147 提升到 354，而 omitted 从 575 降至 368。该样本使用 mock LLM，不能称为生产 Agent Trace。
3. **Codex 有双日志投影**：`response_item` 更接近 model-visible items；`event_msg` 会包含展示和统计事件。Adapter 选择避免重复显示 `event_msg/user_message`，因此有显式未映射字段。
4. **Claude Code 存在多类系统/进度事件**：普通 User/Assistant、Tool Use/Result 能映射，但部分进度、错误及环境字段在本版 Projection 中仍有所遗漏。
5. **LangGraph 的 Snapshot 不是普通对话日志**：运行时快照保存 `values`、`next`、`config`、`parent_config` 和 `tasks`；`get_state_history` 可按与自然执行时间相反的顺序返回，Adapter 当前保留输入顺序。

## 验证内容

- [x] 五个公开/运行时来源能被解析，并产生非空 Canonical Events。
- [x] 工具调用与结果 ID 的基础关联；该轮转换没有返回孤立 Result Warning。
- [x] 每条处理记录的 mapped/omitted JSON Pointer 统计及聚合比率。
- [x] 实际 LangGraph Runtime 使用 `graph.invoke` 和 `get_state_history` 输出 3 个 Snapshot。
- [x] 离线回归测试、旧格式示例校验、五格式 Batch Export。

## 尚未覆盖

- 全版本兼容性及全量生产轨迹语义完整性。
- 恢复执行环境、文件系统副作用和浏览器状态的确定性回放。
- 高精度并行 / 子 Agent / 跨 Span 树 / 原生多模态工件。
- 从普通日志恢复不可见推理、真实训练 Logprob、Reward 等不可采集信息。
- 完整原生 Schema 官方校验与可逆 round-trip。

## 复现

见 [工程 README](../README.md)。在线测试配置在 [trajectory-engineering.yml](https://github.com/1998x-stack/trajectory-analysis/blob/main/.github/workflows/trajectory-engineering.yml)。结果存储于 GitHub Actions 本轮运行的 `trajectory-public-real-summary` Artifact；下载脚本和具体 URL 在 [fetch_public.py](../scripts/fetch_public.py)。公开数据的使用许可和隐私须自行审查。
