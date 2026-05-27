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
knowledge/inbox/**
knowledge/.wiki/capture_policy.json
```

派生数据：

```text
knowledge/maps/graph-data.json
knowledge/.wiki/cache.json
knowledge/.wiki/search_index/
knowledge/.wiki/lightrag/
knowledge/.wiki/id_index.json
knowledge/.wiki/inbox_index.json
knowledge/.wiki/normalized_alias_index.json
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
id: top_20260524_agent-native-wiki         # 稳定主键，永不随 slug / title / path 变化
type: topic
status: active
confidence: medium
created: 2026-05-24
updated: 2026-05-24
last_verified: 2026-05-24
review: false
tags:
  - wiki/topic
source_ids:                                # canonical 来源引用（按 ID）
  - src_20260524_some-source
related_ids:                               # canonical 相关页引用（按 ID）
  - ent_20260524_lightrag
sources:                                   # 可选显示层，Obsidian wikilink
  - "[[某篇来源摘要]]"
related:
  - "[[LightRAG]]"
  - "[[Agent-native Wiki]]"
supersedes: []                             # ID 数组
superseded_by: []                          # ID 数组
evidence_count: 1
---
```

建议字段：

| 字段 | 说明 |
| --- | --- |
| `id` | 稳定主键，格式 `<prefix>_YYYYMMDD_<slug>`；**永不随标题、slug、路径变化**；prefix 见下方"稳定 ID 规则" |
| `type` | 页面类型 |
| `status` | `draft`、`active`、`stale`、`archived`、`redirect`（`redirect` 仅用于 entity 别名薄页，不参与主图谱节点） |
| `confidence` | `low`、`medium`、`high` |
| `created` | 页面创建日期 |
| `updated` | 最近维护日期 |
| `last_verified` | 最近一次对照来源验证核心结论的日期 |
| `source_ids` | canonical 来源引用，按 ID；lint 校验完整性 |
| `related_ids` | canonical 相关页引用，按 ID |
| `sources` | 可选显示层（Obsidian wikilink），不参与 lint 完整性 |
| `related` | 可选显示层（Obsidian wikilink），不参与 lint 完整性 |
| `review` | 是否需要人工审核 |
| `supersedes` | 本页面替代的旧页面 ID 列表 |
| `superseded_by` | 替代本页面的新页面 ID 列表 |
| `aliases` | （仅 entity）已知别名字符串数组，保留人类写法；规范化匹配由派生 `normalized_alias_index.json` 维护 |
| `canonical_id` | （仅 entity）若为 `null` 则本页是正名页；若指向某 `id` 则本页是薄重定向页，必须 `status: redirect` |
| `evidence_count` | 支撑核心结论的来源或证据数量 |

更完整的字段约定、`review_queue.json` 和 `source_manifest.json` 契约见
[05-contracts-and-next-steps.md](05-contracts-and-next-steps.md)。

### 稳定 ID 规则

每个页面的 `id` 一旦创建，**永不变化**。重命名、移动目录、改 H1 标题都不动 `id`。

格式：`<prefix>_YYYYMMDD_<slug>`

| 类型 | prefix | 示例 |
| --- | --- | --- |
| source | `src_` | `src_20260526_attention-is-all-you-need` |
| entity | `ent_` | `ent_20260526_attention` |
| topic | `top_` | `top_20260526_transformer-architecture` |
| comparison | `cmp_` | `cmp_20260526_rag-vs-graphrag` |
| synthesis | `syn_` | `syn_20260526_attention-overview` |
| decision | `dec_` | `dec_20260526_use-lightrag` |
| query | `que_` | `que_20260526_what-is-rag` |
| open-question | `oq_` | `oq_20260526_consistency-vs-availability` |
| inbox（capture item，非 wiki 页面类型） | `inb_` | `inb_20260526_153012_attention-complexity` |

**source 单主键约束**：source 类型页面 `id` 必须等于该 source 在 `knowledge/raw/source_manifest.json` 中的 `source_id`。其它页面类型的 `id` 与业务 ID 无关。

**inbox capture item**：`inb_` prefix 的文件不属于 `knowledge/wiki/`，独立放在 `knowledge/inbox/`，schema 见 [05-contracts-and-next-steps.md](05-contracts-and-next-steps.md) "Capture Item Schema" 段。capture item 不参与主图谱、不作引用来源、不进 wiki 页面 lint。

**同日冲突**：同 prefix 同日同 slug 重名时，追加 `_NN` 短序号，例如 `ent_20260526_attention_002`。由 lint 强制全局唯一。

**slug 不是当前标题镜像**：slug 是页面**创建时**的可读提示。页面 H1 改名后 slug 不变。

**entity 别名薄页**：极少数情况下，别名以独立页面形式存在（外部已有 wikilink 散布、不便迁移），该页 frontmatter 用 `canonical_id` 指向正名页 `id`，`status: redirect`，不参与主图谱节点 / 综合 / 引用来源。99% 的别名应只放在正名页的 `aliases` 列表里，不建薄页。详见 [05-contracts-and-next-steps.md](05-contracts-and-next-steps.md) "Normalized Alias Index Schema" 段和 entity 模板。

### 拆分与合并语义

页面被拆分时：

- 拆出的新页面拿**新 ID**。
- 旧页面若部分内容保留，**原 ID 不变**，正文调整即可。
- 旧页面若完全被新页面取代，标 `status: archived` + `superseded_by: [新 ID 数组]`。

页面被合并时：

- 被合并页（要消失的那个）保留**壳 frontmatter**，标 `status: archived` + `superseded_by: [合并目标 ID]`，正文清空或留一行重定向说明。
- 合并目标页保留**原 ID**，吸收被合并页的实质内容。

### Cross-ref 字段说明

下列引用是 **canonical** 的（lint 严格校验、未来工具按 ID 索引）：

| 位置 | 字段 |
| --- | --- |
| 页面 frontmatter | `id`、`source_ids`、`related_ids`、`supersedes`、`superseded_by`、`canonical_id`（entity 别名薄页指向） |
| `review_queue.json` 单条 item | `affected_page_ids`、`evidence.page_id` |
| `source_manifest.json` 单条 source | `summary_page_id` |
| 未来 `maps/graph-data.json` 节点 key | 页面 `id` |

下列是 **可选显示层**（仅给人看，lint 不强制完整性）：

| 位置 | 字段 |
| --- | --- |
| 页面 frontmatter | `sources`、`related`（wikilink） |
| `review_queue.json` 单条 item | `evidence.page_path`、`source_paths` |
| `source_manifest.json` 单条 source | `summary_page_path` |
| 答案引用里的 `wiki/.../X.md` 字符串 | 可读 path |

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
