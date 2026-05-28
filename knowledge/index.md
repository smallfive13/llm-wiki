# Index

## 入口

- [Purpose](purpose.md) — 知识库目的
- [Overview](overview.md) — 顶层综合视图
- [Log](log.md) — 变更日志
- [Wiki Schema](.wiki-schema.md) — 数据契约（Agent 会话起点）

## 主目录

| 路径 | 用途 |
| --- | --- |
| `raw/` | 原始资料（PDF / 网页 / 对话 / 代码片段） |
| `raw/source_manifest.json` | 资料登记表 |
| `wiki/sources/` | 单来源摘要 |
| `wiki/entities/` | 公司 / 人物 / 项目 / 指标 / 模型 / 工具 |
| `wiki/topics/` | 跨来源主题页 |
| `wiki/comparisons/` | 工具 / 方案 / 观点对比 |
| `wiki/synthesis/` | 多来源综合结论 |
| `wiki/decisions/` | 重要判断 / 选择 / 取舍 |
| `wiki/queries/` | 值得沉淀的问题和回答 |
| `wiki/open-questions/` | 待验证 / 冲突 / 空白 |
| `inbox/` | Capture 缓冲层（draft），定期 promote |
| `inbox/archive/promoted/` | 已晋升 capture（审计） |
| `inbox/archive/dropped/` | 已丢弃 capture（审计） |
| `maps/` | 派生图谱可视化 |
| `.wiki/review_queue.json` | 待人工审核队列 |
| `.wiki/capture_policy.json` | Capture 控制策略 |

## 当前状态

- 初始化日期：2026-05-27
- Schema 版本：RFC-001~008 applied
- Wiki 页面数：4（1 synthesis + 3 topic，见 [系统架构](wiki/synthesis/llm-wiki-architecture.md)）
- Inbox draft 数：0

> 此页面是入口；具体规范见 [.wiki-schema.md](.wiki-schema.md)。
