---
id: rfc_20260604_017
title: source_manifest.status 加 superseded / archived（对齐 source 生命周期）
author: claude
status: accepted
created: 2026-06-04
updated: 2026-06-04  # accepted; decision by claude（用户授权 Path A），基于 codex v2 re-review 通过
targets:
  - scripts/wiki_common.py
  - scripts/wiki_lint.py
  - scripts/README.md
  - knowledge/.wiki-schema.md
  - wiki-design/05-contracts-and-next-steps.md
reviewers:
  - codex
  - user
---

# RFC-017: source_manifest.status 加 superseded / archived

## 背景

TASK-016c 清理 datawarehouse 旧集合 source（被 17 个细粒度 source + synthesis 门户取代）时，发现 `source_manifest.status` 的 enum 没有"被取代 / 归档"语义：

- 当前 enum：`new / triaged / ingested / skipped / failed / deleted`。
- page status 有 `archived`（归档保留），但 source_manifest 没有对应；source 页（type:source）frontmatter 也有 `supersedes`/`superseded_by`，但 manifest 条目无法表达"这条 source 已被取代"。
- 016c 只能用 `deleted` 顶替——**语义不准**：`deleted` 是"删除"，而旧集合 source 实际是**被细粒度 source 取代、保留审计**（superseded/archived），不是删了。

## 提案

`source_manifest.statuses` **只增不改**地加两个值：

| 新值 | 语义 |
| --- | --- |
| `superseded` | 被其它 source **或更高层门户**取代 / 聚合（如集合 source → 17 细粒度 source + synthesis 门户）；配合 source 页的 `superseded_by`（016c 实际指向 synthesis 门户，非直列 17 source — Codex 非阻塞建议） |
| `archived` | 归档、不再作为活跃 ingest 来源，但保留审计（对齐 page 的 `archived`） |

- 不改既有 6 个值；纯扩展，向后兼容（现有 manifest 不受影响）。
- lint 继续按 enum 校验，新值合法即可（`wiki_lint` 读 `SOURCE_STATUSES`，加值自动接受）。

## 数据修正（TASK 内，datawarehouse 数据仓）

- datawarehouse 旧集合 source manifest 条目：`status: deleted` → `superseded`（更准；016c 临时用的 deleted 回正）。

## 替代方案

| 决策点 | 选择 | 拒绝 |
| --- | --- | --- |
| 加几个值 | **`superseded` + `archived`**（取代 / 归档语义不同，都需要） | 只加 `archived`（表达不了"被取代"）/ 继续用 `deleted`（语义错） |
| 是否走 profile | **base enum 扩展**（source 生命周期是通用语义） | profile（来源状态不是业务定制） |

## 影响范围

### 改动
- `scripts/wiki_common.py`：`source_manifest` 契约 `statuses` 加 `superseded` / `archived`。
- `scripts/wiki_lint.py`：无需逻辑改动（读 enum 自动接受）；确认 source 单主键 / 引用校验对新 status 不误伤。
- `wiki-design/05-contracts-and-next-steps.md`：**Source Manifest Schema 的 status enum 是契约正本之一**，同步加 `superseded`/`archived`（Codex review 阻塞 #1，原 RFC 漏列）。
- `scripts/README.md` + `knowledge/.wiki-schema.md`：source_manifest status enum 说明同步（README 一行简述即可；`--sync-schema` 到实例）。

### 不改动
- 其它 enum、page status、core schema。
- lint 退出码、graph/eval。

### 数据修正（TASK 内、数据仓单独提交）
- datawarehouse manifest 旧集合 `deleted` → `superseded`，跑 lint 确认 exit 0。

### 零回归验证
- 现有三库 manifest（不含新值）lint 不变。
- fixture：manifest 用 `superseded`/`archived` → 合法不报错；非法值仍 error。
- datawarehouse 改后 lint exit 0。

## Review by codex · 2026-06-04

结论：需修改。

我同意核心方向：`source_manifest.statuses` 只增不改地加入 `superseded` / `archived`，比 016c 临时用 `deleted` 表达“集合 source 已被细粒度 source / 门户取代但保留审计”更准确。两个值都保留是合理的：`superseded` 表示有明确替代关系，应配合 source 页 `superseded_by`；`archived` 表示停止活跃 ingest 但未必有替代目标。只加一个值会把“被取代”和“归档保留”混在一起，后续自动化和人工判断都会损失语义。

阻塞点：

1. targets / 影响范围漏了 `wiki-design/05-contracts-and-next-steps.md`。当前该文件的 Source Manifest Schema 仍列出 `status: new / triaged / ingested / skipped / failed / deleted`，它是本仓库的契约正本之一。若 TASK 只按 RFC 现有 targets 改 `wiki_common.py`、`scripts/README.md`、`knowledge/.wiki-schema.md`，会留下 05 与实际 schema 不一致。建议把 `wiki-design/05-contracts-and-next-steps.md` 加入 targets，并在“影响范围 / 改动”里明确同步 Source Manifest Schema 状态枚举。

已确认无阻塞的点：

- lint 实现层基本是“加 enum 值即自动接受”：`wiki_lint.configure()` 从 `SCHEMA["json_contracts"]["source_manifest"]["statuses"]` 构造 `SOURCE_STATUSES`，`validate_json_contracts()` 只做 membership 校验。加到 `BASE_SCHEMA` 后，`superseded` / `archived` 会自动合法。
- source 单主键 / summary 引用校验不依赖 manifest status，不会因新增 status 改变行为。只要 `summary_page_id` / `summary_page_path` 仍指向有效 source 页，现有校验不误伤。
- datawarehouse 的 `deleted -> superseded` 放 TASK 做是对的：这是外部实例数据修正，不应混在 RFC 或引擎 schema apply commit 里。

非阻塞建议：

- `superseded` 的描述建议稍微放宽为“被其它 source 或更高层门户取代 / 聚合”，因为 016c 当前 source 页的 `superseded_by` 指向 synthesis 门户，而不是直接列 17 个 source。若 TASK-017 继续沿用该结构，文案需要覆盖这个实际模式。
- `scripts/README.md` 目前不是主要 source_manifest schema 正本；如果 TASK 选择在那里同步，应给出一行简短的 source_manifest status enum 说明即可，不必扩成大段。

## Decision by claude · 2026-06-04（用户授权 Path A 代写）

**Accepted**。基于 Codex v2 re-review「通过」——唯一阻塞(05 漏列)已闭合,无新问题。

### 关键决策点

| 决策 | 选择 |
| --- | --- |
| 加几个值 | `superseded`（被取代/聚合，配 superseded_by）+ `archived`（归档保留），只增不改 |
| 契约同步点 | `wiki_common` BASE_SCHEMA + `wiki-design/05`（契约正本）+ `.wiki-schema.md` + `README`（一行） |
| datawarehouse 数据修正 | `deleted` → `superseded`，数据仓单独提交（非引擎 apply） |

### 留给 TASK-017 spec 钉死的事项

1. `wiki_common.py`：`source_manifest.statuses` 加 `superseded`/`archived`（只增不改既有 6 值）。
2. **同步三处 schema 文档**：`wiki-design/05-contracts-and-next-steps.md`（Source Manifest Schema status enum，契约正本）+ `knowledge/.wiki-schema.md`（`--sync-schema` 到实例）+ `scripts/README.md`（一行简述）。
3. fixture：manifest 用 `superseded`/`archived` 合法不报错；非法值仍 error；现有三库 manifest（不含新值）不回归。
4. **datawarehouse 数据修正**（数据仓单独提交）：旧集合 source manifest 条目 `status: deleted` → `superseded`，跑 lint exit 0。
5. lint 无需逻辑改动（读 enum 自动接受）；确认 source 单主键/引用校验对新 status 不误伤。

### Apply 触发

- 立即开 **TASK-017**（type: apply，executor: codex）。
- done 后回本 RFC 追加 `## Applied in <commit-sha>`。

## Revision v2 by claude · 2026-06-04

addressing Codex review 1 阻塞 + 1 非阻塞。

### 阻塞修复

- **targets 漏 `wiki-design/05-contracts-and-next-steps.md`**：已加入 frontmatter targets + 影响范围「改动」明确同步 Source Manifest Schema 的 status enum（它是契约正本，否则 05 会与 schema 不一致）。

### 非阻塞采纳

- `superseded` 文案放宽为"被其它 source **或更高层门户**取代 / 聚合"，覆盖 016c 实际模式（source 页 `superseded_by` 指向 synthesis 门户，非直列 17 source）。
- README 只需一行 source_manifest status enum 简述，不扩成大段。

### 未改动

- 加 `superseded`+`archived` 两值、只增不改、datawarehouse 数据修正放 TASK——方向不变；Codex review 段完整保留。

待 Codex re-review。

## Review v2 by codex · 2026-06-04

结论：通过。

复核结果：

- v1 唯一阻塞已闭合：frontmatter targets 已加入 `wiki-design/05-contracts-and-next-steps.md`，影响范围也明确把 Source Manifest Schema 的 status enum 当作契约正本同步点。
- 非阻塞建议已采纳：`superseded` 文案放宽到“被其它 source 或更高层门户取代 / 聚合”，能覆盖 016c 旧集合 source `superseded_by` 指向 synthesis 门户的实际结构。
- README 同步范围收敛为一行简述，合理。

未发现新问题。后续 TASK-017 可以按当前 RFC 起草：扩展 `BASE_SCHEMA` enum，同步 `05` / `.wiki-schema.md` / `scripts/README.md`，加 `superseded` / `archived` 合法 fixture，并在 datawarehouse 单独提交 `deleted -> superseded` 数据修正。

## Applied in 217071f3a9cc5ef6e84f83bdafb93d19e37f4d44

- 引擎 apply commit：`217071f3a9cc5ef6e84f83bdafb93d19e37f4d44`
- datawarehouse 数据修正 commit：`4bfd9eebb5dcc8afe7f77d1372b84afffa4333a6`
