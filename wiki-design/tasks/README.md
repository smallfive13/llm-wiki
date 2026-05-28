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
| [task_20260528_008](TASK-008-apply-rfc-008.md) | Apply RFC-008 — 实现 schema profile 机制（BASE_SCHEMA + overlay + --root） | pending (spec v3 approved, ready to execute) | claude | codex | RFC-008 |

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
