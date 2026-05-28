# RFC 索引

本目录用于 Codex 和 Claude Code 在修改设计正本前对齐提案、review 和决策。除 typo、措辞、链接、格式或示例补全外，涉及 `wiki-design/*.md`、`AGENTS.md`、`knowledge/.wiki-schema.md` 的非平凡修改都应先走 RFC。

## 索引

| id | 标题 | status | author | targets |
| --- | --- | --- | --- | --- |
| [rfc_20260526_001](RFC-001-multi-agent-collaboration.md) | 引入 Codex 与 Claude Code 的 RFC 协作机制 | accepted | codex | `AGENTS.md`, `.gitignore`, `wiki-design/rfcs/README.md` |
| [rfc_20260526_002](RFC-002-stable-page-ids.md) | 给 Wiki 页面引入稳定 ID | accepted | claude | `wiki-design/01-architecture.md`, `wiki-design/05-contracts-and-next-steps.md` |
| [rfc_20260526_003](RFC-003-inbox-capture-layer.md) | 引入 inbox 缓冲层，允许低门槛 capture | accepted | claude | `AGENTS.md`, `wiki-design/01-architecture.md`, `wiki-design/02-workflows.md`, `wiki-design/04-agent-rules.md`, `wiki-design/05-contracts-and-next-steps.md` |
| [rfc_20260526_004](RFC-004-entity-aliases.md) | 给 entity 加 aliases 和 canonical_id | accepted | claude | `wiki-design/01-architecture.md`, `wiki-design/02-workflows.md`, `wiki-design/05-contracts-and-next-steps.md` |
| [rfc_20260526_005](RFC-005-task-channel.md) | 引入 wiki-design/tasks/ 作为执行指令通道 | accepted | claude | `AGENTS.md`, `wiki-design/tasks/`, `wiki-design/rfcs/README.md` |
| [rfc_20260527_006](RFC-006-wiki-lint-mvp.md) | 引入 wiki-lint MVP，闭合 RFC-002/003/004 的约束 | accepted | claude | `scripts/wiki_lint.py`, `AGENTS.md`, `wiki-design/02-workflows.md`, `wiki-design/05-contracts-and-next-steps.md` |
| [rfc_20260528_007](RFC-007-wiki-graph.md) | 自建 canonical wiki-graph（03 第二层增强图谱生成器） | accepted | claude | `scripts/wiki_graph.py`, `scripts/wiki_common.py`, `scripts/wiki_lint.py`, `scripts/README.md`, `wiki-design/02-workflows.md`, `wiki-design/03-obsidian-graph.md`, `.gitignore` |
| [rfc_20260528_008](RFC-008-schema-profiles.md) | 业务 schema profile 机制（base + 可扩展 overlay，支持多实例复用） | accepted | claude | `scripts/wiki_common.py`, `scripts/wiki_lint.py`, `scripts/wiki_graph.py`, `scripts/README.md`, `knowledge/.wiki-schema.md`, `wiki-design/01-architecture.md`, `wiki-design/05-contracts-and-next-steps.md` |
| [rfc_20260528_009](RFC-009-wikilink-convention.md) | wikilink 约定标准化（slug-based + 管道显示别名，Obsidian/wiki_graph 双解析） | proposed | claude | `scripts/wiki_graph.py`, `scripts/README.md`, `wiki-design/03-obsidian-graph.md`, `wiki-design/05-contracts-and-next-steps.md`, `wiki-design/02-workflows.md`, `knowledge/.wiki-schema.md`, `knowledge/wiki/**` |

## 状态

| status | 含义 |
| --- | --- |
| `proposed` | 已提出，等待另一个 Agent 或用户 review |
| `discussing` | 正在讨论，尚未决策 |
| `accepted` | 用户已接受，可以 apply 到 targets |
| `rejected` | 已拒绝，不应继续 apply |
| `superseded` | 已被后续 RFC 替代 |

## 新建 RFC 模板

```markdown
---
id: rfc_YYYYMMDD_NNN
title: 简短标题
author: codex
status: proposed
created: YYYY-MM-DD
updated: YYYY-MM-DD
targets:
  - wiki-design/example.md
reviewers:
  - claude
  - user
---

# RFC-NNN: 简短标题

## 背景

说明为什么需要改，当前问题是什么。

## 提案

说明具体要改什么，边界是什么。

## 替代方案

列出考虑过但暂不采用的方案。

## 影响范围

列出会影响的文件、工作流、schema、模板或脚本。

## Review by claude · YYYY-MM-DD

由 Claude Code 追加，不覆盖原作者内容。

## Decision

由用户填写，或由用户明确授权某个 Agent 代写。
```

## Review 规则

- Review 只能追加新段落，不修改原作者提案正文。
- 如果发现已有相关 RFC，优先在原 RFC 追加 review，不新建重复 RFC。
- 如果一个 RFC 被拆分或替代，把旧 RFC 标记为 `superseded`，并在正文写明替代 RFC。
- apply 后在 RFC 末尾登记 `## Applied in <commit-sha>`；未提交时先登记 `working tree · YYYY-MM-DD · <agent>`。

## Backlog

以下议题已在 review 中识别但尚未拆成 RFC。当 RFC-002 ~ RFC-004 落地后再视情况启动。

| 主题 | 优先级 | 简述 |
| --- | --- | --- |
| 查询路由表 | P1 | 在 `02-workflows.md` 加意图类型 → 检索通道映射（BM25 / 向量 / 图谱多跳 / 直接读页），避免 Agent 检索时乱试 |
| evidence 结构化 | P1 | `evidence_count` 退化为派生字段，frontmatter 改为 `evidence: [{source_id, independence}]`，区分独立来源 / 互证 / 派生 |
| review queue SLA | P2 | 加 pending 时长告警、健康度报告，防止队列变成死信 |
| Wiki 健康度指标 | P2 | 新增 `maps/metrics.md`（派生层），跟踪页面增长、孤立率、平均 confidence、`last_verified` 年龄 |
| 双 Agent 并发写入约束 | P2 | 明确 single-writer 或把 `review_queue.json` / `source_manifest.json` 拆成一条一文件，降低 git 冲突 |
| visibility / PII 字段 | P2 | frontmatter 加 `visibility: private \| team \| public`，lint 在 public 页扫描 PII pattern |
