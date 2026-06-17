# Tasks 索引

本目录承载 Codex 和 Claude Code 之间的执行指令。机制定义见 [RFC-005](../rfcs/RFC-005-task-channel.md)。

Task 回答"怎么做、谁来做"，与 RFC 回答"要不要这么改"互补。

## 索引

| id | 标题 | status | author | executor | related_rfcs |
| --- | --- | --- | --- | --- | --- |
| [task_20260526_001](TASK-001-write-rfc-decisions.md) | 把 RFC-002/003/004 的 Decision 落到文件并 commit | done | claude | codex | RFC-002, RFC-003, RFC-004 |
| [task_20260526_002](TASK-002-apply-rfc-002.md) | Apply RFC-002 — 把稳定 ID 机制落到 01/05/.gitignore | done | claude | codex | RFC-002 |
| [task_20260526_003](TASK-003-apply-rfc-003.md) | Apply RFC-003 — capture 机制 + inbox 缓冲层落到 AGENTS / 01 / 02 / 04 / 05 / .gitignore | done | claude | codex | RFC-003 |
| [task_20260526_004](TASK-004-apply-rfc-004.md) | Apply RFC-004 — entity aliases / canonical_id / status:redirect / normalized index | done | claude | codex | RFC-004 |
| [task_20260526_005](TASK-005-init-knowledge-skeleton.md) | 初始化 knowledge/ 骨架（基于 RFC-001~005 冻结 schema） | done | claude | codex | RFC-001~005 |
| [task_20260528_006](TASK-006-apply-rfc-006.md) | Apply RFC-006 — 实现 wiki-lint MVP（scripts/wiki_lint.py + 文档同步） | done | claude | codex | RFC-006 |
| [task_20260528_007](TASK-007-apply-rfc-007.md) | Apply RFC-007 — 实现 wiki-graph MVP（wiki_common + wiki_graph.py + 文档同步） | done | claude | codex | RFC-007 |
| [task_20260528_008](TASK-008-apply-rfc-008.md) | Apply RFC-008 — 实现 schema profile 机制（BASE_SCHEMA + overlay + --root） | done | claude | codex | RFC-008 |
| [task_20260528_009](TASK-009-apply-rfc-009.md) | Apply RFC-009 — wikilink 约定（wiki_graph lookup + 迁移 4 页 + 文档同步） | done | claude | codex | RFC-009 |
| [task_20260529_010](TASK-010-apply-rfc-010.md) | Apply RFC-010 — 实现 wiki_init.py 脚手架 | done | claude | codex | RFC-010 |
| [task_20260601_011](TASK-011-apply-rfc-011.md) | Apply RFC-011 — wiki_init Obsidian 友好增强 | done | claude | codex | RFC-011 |
| [task_20260602_012](TASK-012-apply-rfc-012.md) | Apply RFC-012 — 知识可信度信号（lint 2 warning + graph in/out degree + insights 健康度段） | done | claude | codex | RFC-012 |
| [task_20260602_013](TASK-013-apply-rfc-013.md) | Apply RFC-013 — wiki_graph wikilink 解析鲁棒性（strip_code_spans + parse_wikilink 转义 + fixture） | done | claude | codex | RFC-013 |
| [task_20260602_014](TASK-014-apply-rfc-014.md) | Apply RFC-014 — wiki-eval 健康度量化（health score + 维度分解 + 趋势 + CI 闸） | done | claude | codex | RFC-014 |
| [task_20260603_015](TASK-015-apply-rfc-015.md) | Apply RFC-015 — .wiki-schema.md 分发鲁棒性（断链修复 + 写入规则 + --sync-schema） | done | claude | codex | RFC-015 |
| [task_20260604_016a](TASK-016a-apply-rfc-016-m1-m2.md) | Apply RFC-016 M1+M2 — visibility 分级 + 脱敏分级 + capture_policy 迁移 | done | claude | codex | RFC-016 |
| [task_20260604_016b](TASK-016b-apply-rfc-016-m3.md) | Apply RFC-016 M3 — 富媒体规则（图引用断引校验 + 硬底线文本兜底） | done | claude | codex | RFC-016 |
| [task_20260604_016c](TASK-016c-datawarehouse-align.md) | Apply RFC-016 数据对齐 — datawarehouse 已 ingest 产物对齐最终规范 | done | claude | codex | RFC-016 |
| [task_20260604_017](TASK-017-apply-rfc-017.md) | Apply RFC-017 — source_manifest.status 加 superseded/archived + datawarehouse 修正 | done | claude | codex | RFC-017 |
| [task_20260604_018](TASK-018-apply-rfc-018.md) | Apply RFC-018 — ingest 子链接处理约定（流程文档，不改 scripts） | done | claude | codex | RFC-018 |
| [task_20260604_019](TASK-019-apply-rfc-019.md) | Apply RFC-019 — ingest 批量编排（lint ingest 进度段 + 流程文档） | done | claude | codex | RFC-019 |
| [task_20260608_020a](TASK-020a-apply-rfc-020-m1-m4.md) | Apply RFC-020 M1+M4 — doc-consistency 校验（wiki_lint --check-docs）+ soft_redact 正则 ASCII 化 | done | claude | codex | RFC-020 |
| [task_20260608_020b](TASK-020b-apply-rfc-020-m2-m3.md) | Apply RFC-020 M2+M3 — 写入指令正本收敛（05/skill 降指针）+ 新 RFC 准入 gate | done | claude | codex | RFC-020 |
| [task_20260608_021a](TASK-021a-apply-rfc-021-m1.md) | Apply RFC-021 M1 — schema_version 递增纪律 + profile 兼容范围校验（bump 到 2） | done | claude | codex | RFC-021 |
| [task_20260608_021b](TASK-021b-apply-rfc-021-m2.md) | Apply RFC-021 M2 — --sync-schema 覆盖前保护（last-synced hash）+ datawarehouse 迁移 | done | claude | codex | RFC-021 |
| [task_20260609_022](TASK-022-apply-rfc-022.md) | Apply RFC-022 — bin/wiki CLI 薄 wrapper | done | claude | codex | RFC-022 |
| [task_20260610_023](TASK-023-team-opening-infra.md) | 团队开放基建 — datawarehouse 带历史拆库上 GitLab + CI 门禁 + 投料约定 | done | claude | codex | — |
| [task_20260610_024](TASK-024-apply-rfc-023.md) | Apply RFC-023 — dropbox 脱敏扫描 + 团队贡献协议进 02-workflows | done | claude | codex | RFC-023 |
| [task_20260610_025](TASK-025-apply-rfc-024.md) | Apply RFC-024 — wiki_init 固化实例 .ignore | done | claude | codex | RFC-024 |
| [task_20260616_026](TASK-026-apply-rfc-025.md) | Apply RFC-025 — endorsement 复核覆盖修正 + 未背书清单 + 巡检/复核手册 | pending | claude | codex | RFC-025 |

## 状态机

```
pending → in-progress → done
                      → failed
pending → cancelled
```

| status | 含义 | 谁可以推进 |
| --- | --- | --- |
| `pending` | 已创建，等待 executor 开工 | author / executor |
| `in-progress` | executor 正在执行 | executor |
| `done` | 完成 | executor |
| `failed` | 失败 | executor |
| `cancelled` | 撤销，不再执行 | author / user |

约束：

- 不允许 `done → 其他`，`failed → done`。
- 失败修补另开新 task，新 task frontmatter 可写 `supersedes: task_xxx`。

## 文件命名

`TASK-NNN-<slug>.md`，NNN 从 001 起全局递增。slug 简短可读。

## 写入约定

- `## 目标 / 前置条件 / 强约束 / 步骤 / 验证 / 完成后报告格式` 一旦定稿，**不重写**。
- executor 只能**追加** `## Execution log by <executor> · <date>` 段并推进 `status`。
- evaluator 只能**追加** `## Evaluation by <evaluator> · <date>` 段。
- 偏离 / 失败必须在 Execution log 段写明原因。
- author 修改 task 内容（在 executor 开工前）允许，须更新 `updated:` 字段。

## 新建 Task 模板

```markdown
---
id: task_YYYYMMDD_NNN
title: 简短标题
author: claude
executor: codex
status: pending
type: decision-write
created: YYYY-MM-DD
updated: YYYY-MM-DD
related_rfcs: []
---

# TASK-NNN: 简短标题

## 目标

一句话说清要达成什么。

## 前置条件

- 任务能开始的检查点（例如：working tree clean、某 RFC 已 accepted）

## 强约束

- 不可违反的规则

## 步骤

1. ...

## 验证

跑这些命令应得到预期输出：

\`\`\`bash
...
\`\`\`

## 完成后报告格式

executor 完成后，把以下内容贴在 Execution log 段：

- 第 X 步实际执行命令和输出
- commit sha
- 偏离或异常

## Execution log by <executor> · <date>

（执行者填写）

## Evaluation by <evaluator> · <date>

（评估者填写）
```

## Type 枚举说明

| type | 用途 |
| --- | --- |
| `decision-write` | 把已 accepted 的 RFC Decision 写入文件、翻 status |
| `apply` | 把 accepted 的 RFC 落到 targets（动正本文档/schema） |
| `bookkeeping` | 索引整理、状态同步、commit 收尾 |
| `refactor` | 仓库结构调整 |
| `other` | 不属于上述 |
