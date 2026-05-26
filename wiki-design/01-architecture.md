# 架构设计

## 设计目标

这套 Wiki 的目标是让知识持续沉淀，而不是每次查询时从零拼答案。

它需要同时服务三类用户：

- 人：可以在 Obsidian 或编辑器里阅读、修改、审查。
- Agent：可以快速获取项目背景、历史结论、来源和开放问题。
- 检索系统：可以用 BM25、向量、LightRAG 或图谱做派生索引。

## 分层

```text
1. Raw Source 层
   保留原始资料，不改写，记录 hash、来源、日期。

2. Human Wiki 层
   Markdown 正本，包含来源摘要、实体、主题、决策、综合结论。

3. Graph/Search 层
   可重建索引，包括 Obsidian 图谱、LightRAG、qmd、向量库。

4. Agent Context 层
   高密度上下文，包括 purpose、schema、最近决策、review queue。

5. Workflow 层
   固定动作，包括 ingest、query、crystallize、lint、graph refresh。
```

## 正本与派生层

必须区分“知识正本”和“可重建派生数据”。

知识正本：

```text
knowledge/purpose.md
knowledge/.wiki-schema.md
knowledge/index.md
knowledge/overview.md
knowledge/log.md
knowledge/raw/source_manifest.json
knowledge/wiki/**
knowledge/.wiki/review_queue.json
```

派生数据：

```text
knowledge/maps/graph-data.json
knowledge/.wiki/cache.json
knowledge/.wiki/search_index/
knowledge/.wiki/lightrag/
```

原则：

- Markdown 页面是长期事实层。
- 图谱、向量、搜索索引可以随时重建。
- Agent 修改正本必须产生可审查 diff。
- 自动生成内容必须标注来源和置信度。

## 页面类型

| 类型 | 目录 | 用途 |
| --- | --- | --- |
| source | `wiki/sources/` | 单个来源的摘要、关键点、可靠性 |
| entity | `wiki/entities/` | 公司、人物、项目、指标、模型、工具 |
| topic | `wiki/topics/` | 跨来源主题页 |
| comparison | `wiki/comparisons/` | 工具、方案、观点对比 |
| synthesis | `wiki/synthesis/` | 多来源综合结论 |
| decision | `wiki/decisions/` | 重要判断、选择、取舍 |
| query | `wiki/queries/` | 值得沉淀的问题和回答 |
| open-question | `wiki/open-questions/` | 待验证、冲突、空白 |

## Frontmatter

页面应尽量使用 Obsidian 友好的 properties。

```yaml
---
type: topic
status: active
confidence: medium
created: 2026-05-24
updated: 2026-05-24
last_verified: 2026-05-24
review: false
tags:
  - wiki/topic
sources:
  - "[[某篇来源摘要]]"
related:
  - "[[LightRAG]]"
  - "[[Agent-native Wiki]]"
supersedes: []
superseded_by: []
evidence_count: 1
---
```

建议字段：

| 字段 | 说明 |
| --- | --- |
| `type` | 页面类型 |
| `status` | `draft`、`active`、`stale`、`archived` |
| `confidence` | `low`、`medium`、`high` |
| `created` | 页面创建日期 |
| `updated` | 最近维护日期 |
| `last_verified` | 最近一次对照来源验证核心结论的日期 |
| `sources` | 来源页 wikilink |
| `related` | 相关页面 |
| `review` | 是否需要人工审核 |
| `supersedes` | 本页面替代的旧页面或旧结论 |
| `superseded_by` | 替代本页面的新页面或新结论 |
| `evidence_count` | 支撑核心结论的来源或证据数量 |

更完整的字段约定、`review_queue.json` 和 `source_manifest.json` 契约见
[05-contracts-and-next-steps.md](05-contracts-and-next-steps.md)。

## Schema 与 Agent 规则

后续落地时建议分成两个文件：

```text
knowledge/.wiki-schema.md   # 知识库结构、字段、页面类型、引用格式
AGENTS.md                   # Codex / Claude Code 读写边界和操作规则
```

`.wiki-schema.md` 回答“知识长什么样”，`AGENTS.md` 回答“Agent 在什么情况下怎么读写”。
本目录中的 `04-agent-rules.md` 只是未来根目录 `AGENTS.md` 的草案，不应混入页面字段定义。

## 与 Repo Wiki 的关系

Repo Wiki 只是参考，不是主目标。

本设计只吸收 Qoder Repo Wiki 的三点：

- 增量更新：只更新受影响页面。
- 隐性知识显性化：把讨论、判断、踩坑沉淀成页面。
- Agent 可用上下文：让 Agent 能快速读入项目知识。

不要求：

- 自动生成完整代码仓库文档。
- 绑定分支级 Wiki。
- 实现 IDE 产品级 Repo Wiki UI。
- 解析整个仓库的 AST、调用图和 import graph。
