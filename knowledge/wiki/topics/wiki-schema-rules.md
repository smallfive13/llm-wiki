---
id: top_20260528_wiki-schema-rules
type: topic
status: active
confidence: high
created: 2026-05-28
updated: 2026-05-28
last_verified: 2026-05-28
review: false
source_ids: []
related_ids:
  - syn_20260528_llm-wiki-architecture
  - top_20260528_toolchain-usage
sources: []
related:
  - "[[llm-wiki 系统架构]]"
  - "[[工具链与使用说明]]"
supersedes: []
superseded_by: []
evidence_count: 4
---

# 知识库 Schema 与页面规则

> 写一个 wiki 页面要遵守的契约：页面类型、稳定 ID、frontmatter 字段、canonical vs 显示层、别名机制。机械校验见 [[工具链与使用说明]]，整体定位见 [[llm-wiki 系统架构]]。

## 8 类页面 + ID prefix

每个 wiki 页 frontmatter 必须有 `id`，格式 `<prefix>_YYYYMMDD_<slug>`，**一次创建永不变**（不随标题/路径变化）。

| 类型 | 目录 | prefix |
| --- | --- | --- |
| source | `wiki/sources/` | `src` |
| entity | `wiki/entities/` | `ent` |
| topic | `wiki/topics/` | `top` |
| comparison | `wiki/comparisons/` | `cmp` |
| synthesis | `wiki/synthesis/` | `syn` |
| decision | `wiki/decisions/` | `dec` |
| query | `wiki/queries/` | `que` |
| open-question | `wiki/open-questions/` | `oq` |
| inbox（非 wiki 页） | `inbox/` | `inb`（含秒级 `inb_YYYYMMDD_HHmmss_<slug>`） |

## 标准 frontmatter

```yaml
id / type / status / confidence / created / updated / last_verified / review
source_ids: []        # canonical 来源引用（按 ID）
related_ids: []       # canonical 相关页引用（按 ID）
sources: []           # 显示层 wikilink（可选）
related: []           # 显示层 wikilink（可选）
supersedes: [] / superseded_by: []
evidence_count: 0
```

enum：`status ∈ {draft, active, stale, archived, redirect}`，`confidence ∈ {low, medium, high}`。`status: redirect` 仅 entity 薄页。

## canonical vs 显示层

| | canonical（lint 校验、按 ID） | 显示层（给人看，不校验完整性） |
| --- | --- | --- |
| 引用字段 | `source_ids` / `related_ids` / `supersedes` / `superseded_by` / `canonical_id` | `sources` / `related`（wikilink） |
| 原则 | 机器引用，改名不破坏 | Obsidian 可读，可断 |

## 几条硬约束（lint 守）

- **source 单主键**：source 页 `id == source_id == source_manifest 中 summary_page_id`
- **supersedes 对称**：A `supersedes:[B]` ⇒ B `superseded_by` 含 A
- **canonical 引用不断**：所有 ID 引用必须能解析到真实页
- **同日同 slug 冲突**：追加 `_NN` 短序号
- **日期 / hash 格式**：`YYYY-MM-DD`、64 位十六进制
- **上下文层四文件无 frontmatter**：purpose / index / overview / log

## entity 别名机制（RFC-004）

- 99% 别名放正名页 `aliases: []`，不建薄页
- 少数才建薄重定向页：`canonical_id` 指向正名页 `id` + `status: redirect`，不链式（A→B→C 非法）
- `normalized_alias_index.json` 维护规范化匹配（大小写 / 空格 / 连字符 / 中文全半角）

## 业务 schema profile（RFC-008）

实例根可放 `.wiki-profile.json` 增量扩展：新页类型 / 新字段 enum / 额外可选字段。**只增不改**——不能动 ID 格式、core 字段、source 单主键、PII 下限等核心不变量。无 profile = 纯 base。

## 引用

- `wiki-design/01-architecture.md`（页面类型 / ID / canonical 边界）
- `wiki-design/05-contracts-and-next-steps.md`（JSON 契约 / 页面模板 / Wiki Profile Schema）
- `knowledge/.wiki-schema.md`（实例内高密度契约镜像）

## 置信度与缺口

- 置信度：high
- 缺口：语义关系类型（supports/contradicts 等）尚无 frontmatter 字段承载，待 evidence 结构化 RFC。
