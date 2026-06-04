---
id: rfc_20260604_017
title: source_manifest.status 加 superseded / archived（对齐 source 生命周期）
author: claude
status: proposed
created: 2026-06-04
updated: 2026-06-04
targets:
  - scripts/wiki_common.py
  - scripts/wiki_lint.py
  - scripts/README.md
  - knowledge/.wiki-schema.md
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
| `superseded` | 被其它 source 取代（如集合 source → 多个细粒度 source）；配合 source 页的 `superseded_by` |
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
- `scripts/README.md` + `knowledge/.wiki-schema.md`：source_manifest status enum 说明同步（`--sync-schema` 到实例）。

### 不改动
- 其它 enum、page status、core schema。
- lint 退出码、graph/eval。

### 数据修正（TASK 内、数据仓单独提交）
- datawarehouse manifest 旧集合 `deleted` → `superseded`，跑 lint 确认 exit 0。

### 零回归验证
- 现有三库 manifest（不含新值）lint 不变。
- fixture：manifest 用 `superseded`/`archived` → 合法不报错；非法值仍 error。
- datawarehouse 改后 lint exit 0。

## Review by codex · YYYY-MM-DD

（待 Codex 追加）

## Decision

（待用户填写，或授权某 Agent 代写）
