# AI Agent Trajectory Format Research

研究 Agent 消息、原生 Session、ATIF、OTLP/OpenInference、RL Episode 的数据形态及字段映射。

## 工程项目

**[Trajectory Engineering：五种原生 Adapter、公开样本采集、字段损失测试和统一 Viewer](engineering/README.md)**

原有调研内容：

| 方向 | 文档 |
|---|---|
| 全景 | [01 Landscape](docs/01-landscape.md) |
| Messages | [02 Messages](docs/02-message-formats.md) |
| Events / Session | [03 Events](docs/03-event-and-session.md) |
| ATIF | [04 ATIF](docs/04-atif.md) |
| Observability | [05 OTel](docs/05-observability.md) |
| Training / Evaluation | [06 RL](docs/06-training-and-evaluation.md) |
| Mapping | [07 字段映射](docs/07-field-mapping.md) |
| Canonical 设计 | [08 Canonical](docs/08-canonical-design.md) |
| Sources | [09 Sources](docs/09-sources-and-versioning.md) |

## 格式示例与验证

- [examples/](examples/)：Message、ATIF、STS、OTLP、Episode、Canonical 示例。
- [schema/](schema/)：此前提案的 Canonical JSON Schema。
- [scripts/validate_examples.py](scripts/validate_examples.py)：旧示例基础校验。
- [engineering/trajlab.py](engineering/trajlab.py)：**新的独立 Canonical v1 实验模型**。本版与旧 `schema/canonical-trajectory.schema.json` 的 `0.1.0` 并非同一 Schema；应通过单独版本管理，不能误认为二者字段完全相容。
- [engineering/demo/index.html](engineering/demo/index.html)：本地浏览器 Viewer。

**注意：** HTML Demo 的数据需要先运行 `engineering/trajlab.py batch` 生成；工程 Smoke Data 为合成数据。真实源记录由 opt-in 脚本获取，必须自行检查许可与隐私。
