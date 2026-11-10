# Trajectory Engineering · Five Native Adapters + Loss Audit + Viewer

在 [trajectory-format](../README.md) 下提供可运行的 Agent 轨迹研究原型：Claude Code、Codex、OpenHands、LangGraph、SWE-agent 原生结构 → 统一 Canonical Event → 字段损失报告 → 可视化 Viewer。

## 立即体验（Python 标准库，无额外依赖）

在仓库根目录执行：

```bash
cd trajectory-format/engineering
python3 -m unittest discover -s tests -v

python3 trajlab.py batch \
  fixtures/smoke/claude-code.jsonl \
  fixtures/smoke/codex.jsonl \
  fixtures/smoke/openhands.json \
  fixtures/smoke/langgraph.json \
  fixtures/smoke/swe-agent.traj \
  --outdir demo/data

python3 -m http.server 8000
```

在浏览器访问 **http://localhost:8000/demo/**。可在下拉菜单切换五种格式，筛选事件类型和参与者，查看完整 Payload、Tool Call 关联、原生 Source Pointer 与 JSON 叶子字段覆盖率。也可通过文件选择器打开已转换的 Canonical JSON（不上传到远程服务）。

> 注意：`fixtures/smoke/` 的五份样本是根据原生结构构造的合成测试数据，**不是实际 Agent 运行记录**。若未先运行 batch，Viewer 只显示明确标注的内置合成预览。

## 五种公开/真实运行样本

样本真实性等级、链接和许可细节在 [docs/provenance.md](docs/provenance.md) 中；**[公开来源实测转换与字段损失报告](docs/real-results-2026-11-10.md)**（GitHub Actions 双 Job 均成功）。

```bash
cd trajectory-format/engineering

# 从第三方源下载 Claude Code / Codex / OpenHands / SWE-agent 公开轨迹
# 下载前请审查数据集许可、敏感数据与使用条件
python3 scripts/fetch_public.py --accept-source-terms

# LangGraph：使用真实运行时 graph.invoke + get_state_history 创建 checkpoint 记录
python3 -m pip install langgraph
python3 scripts/generate_langgraph.py --output fixtures/real/langgraph.json

python3 trajlab.py batch \
  fixtures/real/claude-code.jsonl \
  fixtures/real/codex.jsonl \
  fixtures/real/openhands.json \
  fixtures/real/langgraph.json \
  fixtures/real/swe-agent.traj \
  --outdir demo/data

python3 -m http.server 8000
```

**真实性边界：** Claude 样本是公开脱敏 Session；Codex 样本是公开原生 rollout；OpenHands 样本是使用 **mock LLM** 捕获的真实 Agent Server 集成测试事件，不是生产模型调用；SWE-agent 是公开演示轨迹；LangGraph 由本地实际图执行生成教程级 `StateSnapshot`。上述第三方文件未打包在仓库内；GitHub Actions 已在一次性 Runner 中抓取并测试，运行后只保留聚合指标 Artifact，不提交原始数据。`fixtures/real/` 和 `demo/data/` 都已加入 Git 忽略。

## 单文件转换

```bash
python3 trajlab.py convert fixtures/smoke/codex.jsonl \
  --format auto \
  --out /tmp/codex.canonical.json \
  --report /tmp/codex.loss.json
```

输出分为两类：

- **Canonical**：`schema_version=trajlab/v1`、`session_id`、`source_format`、`events[]`；每个 Event 有 `event_id`、`sequence`、`kind`、`actor`、`summary`、`payload`、可选 `timestamp`、`call_id` 和 `parent_source_id`，另有 `source.record_index` / `pointer` / `sha256` / `source_id`。
- **Loss Report**：逐条输入记录计算 `mapped` / `omitted` 的 JSON Pointer 路径、`mapped_leaf_count` / `omitted_leaf_count` / `mapped_leaf_ratio` 与 `warnings`。

`mapped_leaf_ratio` 表示**被 Adapter 显式分类为已映射的 JSON 叶子字段比例**，不是语义保真率、字节损失率或可逆还原率。部分 Content Blocks 会整体保留于 Payload，其他信息（如某些 CLI 私有元数据、重复 TUI 消息、状态）可能遗漏。生成的 Canonical 不包含所有原始字节，应保留原始源文件与哈希。

## 目录结构

```text
engineering/
├── trajlab.py
├── fixtures/
│   ├── smoke/                 # 合成离线测试数据
│   └── real/                  # 外部真实轨迹，不追踪
├── scripts/
│   ├── fetch_public.py
│   └── generate_langgraph.py
├── tests/
│   └── test_trajlab.py
├── docs/
│   ├── provenance.md
│   └── field-mapping.md
└── demo/
    ├── index.html
    └── data/                  # CLI batch 生成，不追踪
```

**现阶段限制**：原生 Session 格式随框架版本变化；还未实现环境状态的确定性回放、复杂多 Agent 分支/Span Tree、正式 Schema 全量验证或 Token 级 RL 数据重建。请勿将转换覆盖率用于评判模型/框架性能。
