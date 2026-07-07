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
| [rfc_20260528_009](RFC-009-wikilink-convention.md) | wikilink 约定标准化（slug-based + 管道显示别名，Obsidian/wiki_graph 双解析） | accepted | claude | `scripts/wiki_graph.py`, `scripts/README.md`, `wiki-design/03-obsidian-graph.md`, `wiki-design/05-contracts-and-next-steps.md`, `wiki-design/02-workflows.md`, `knowledge/.wiki-schema.md`, `knowledge/wiki/**` |
| [rfc_20260529_010](RFC-010-wiki-init.md) | wiki init 脚手架（外部 vault 实例 + 叠加已有 vault + git 初始化） | accepted | claude | `scripts/wiki_init.py`, `scripts/README.md`, `wiki-design/02-workflows.md` |
| [rfc_20260601_011](RFC-011-wiki-init-obsidian-friendly.md) | wiki_init Obsidian 友好初始化（排除派生层 + 结构化上下文层占位） | accepted | claude | `scripts/wiki_init.py`, `scripts/README.md` |
| [rfc_20260601_012](RFC-012-knowledge-trust-signal.md) | 知识可信度信号（激活 review 语义 + 时间衰减 + 使用热度 + 用户反馈） | accepted | claude | `scripts/wiki_common.py`, `scripts/wiki_lint.py`, `scripts/wiki_graph.py`, `scripts/README.md`, `knowledge/.wiki-schema.md`, `wiki-design/02-workflows.md` |
| [rfc_20260602_013](RFC-013-wikilink-parse-robustness.md) | wiki_graph wikilink 解析鲁棒性（剥离 code 段 + 处理表格转义管道） | accepted | claude | `scripts/wiki_common.py`, `scripts/wiki_graph.py`, `scripts/README.md` |
| [rfc_20260602_014](RFC-014-wiki-eval-health-score.md) | wiki-eval 知识库健康度量化（health score + 维度分解 + 趋势） | accepted | claude | `scripts/wiki_eval.py`, `scripts/wiki_common.py`, `scripts/README.md`, `wiki-design/02-workflows.md` |
| [rfc_20260603_015](RFC-015-wiki-schema-distribution.md) | .wiki-schema.md 分发鲁棒性（外部实例断链 + 写入规则措辞 + 同步机制） | accepted | claude | `knowledge/.wiki-schema.md`, `scripts/wiki_init.py`, `scripts/README.md` |
| [rfc_20260603_016](RFC-016-ingest-v2.md) | ingest v2 — visibility 分级 + 脱敏分级 + 富媒体（图片多模态） | accepted | claude | `scripts/wiki_common.py`, `scripts/wiki_lint.py`, `scripts/wiki_init.py`, `scripts/README.md`, `knowledge/.wiki-schema.md`, `wiki-design/02-workflows.md` |
| [rfc_20260604_017](RFC-017-source-manifest-status.md) | source_manifest.status 加 superseded / archived（对齐 source 生命周期） | accepted | claude | `scripts/wiki_common.py`, `scripts/wiki_lint.py`, `scripts/README.md`, `knowledge/.wiki-schema.md`, `wiki-design/05-contracts-and-next-steps.md` |
| [rfc_20260604_018](RFC-018-ingest-sublink-handling.md) | ingest 子链接处理（关联保留 + source-gap 登记 + 不递归） | accepted | claude | `knowledge/.wiki-schema.md`, `wiki-design/02-workflows.md`, `wiki-design/04-agent-rules.md` |
| [rfc_20260604_019](RFC-019-ingest-batch-orchestration.md) | ingest 批量编排（triage 全量 + apply 清单 + 逐份处理追踪 + 断点续传） | accepted | claude | `scripts/wiki_lint.py`, `scripts/wiki_common.py`, `scripts/README.md`, `knowledge/.wiki-schema.md`, `wiki-design/02-workflows.md`, `wiki-design/04-agent-rules.md` |
| [rfc_20260608_020](RFC-020-doc-consistency-and-source-of-truth.md) | 文档一致性根治（doc-consistency 校验 + 写入指令正本收敛 + RFC 准入 gate） | accepted | claude | `scripts/wiki_lint.py`, `scripts/wiki_common.py`, `AGENTS.md`, `knowledge/.wiki-schema.md`, `wiki-design/05-contracts-and-next-steps.md`, `wiki-design/04-agent-rules.md`, `skill/wiki/` |
| [rfc_20260608_021](RFC-021-schema-versioning-and-distribution.md) | schema 版本递增纪律 + 实例分发安全（.wiki-schema 镜像 vs 实例特化） | accepted | claude | `scripts/wiki_common.py`, `scripts/wiki_init.py`, `scripts/wiki_lint.py`, `knowledge/.wiki-schema.md`, `wiki-design/02-workflows.md` |
| [rfc_20260609_022](RFC-022-wiki-cli-wrapper.md) | wiki CLI 薄 wrapper（统一入口，消除 conda/cwd/路径摩擦） | accepted | claude | `bin/wiki`, `scripts/README.md`, `wiki-design/02-workflows.md`, `skill/wiki/SKILL.md` |
| [rfc_20260610_023](RFC-023-team-contribution-protocol.md) | 团队贡献协议（投料 → MR → CI → 单 writer ingest）+ dropbox 脱敏扫描 | accepted | claude | `scripts/wiki_lint.py`, `scripts/README.md`, `wiki-design/02-workflows.md` |
| [rfc_20260610_024](RFC-024-wiki-init-ignore-file.md) | wiki_init 固化实例 .ignore（检索默认跳过非正本目录） | accepted | claude | `scripts/wiki_init.py`, `scripts/README.md`, `knowledge/.ignore` |
| [rfc_20260616_025](RFC-025-review-coverage-and-audit.md) | eval 复核覆盖度量修正（消除 0-high 假绿）+ 未背书清单 + 巡检/复核手册 | accepted | claude |
| [rfc_20260618_026](RFC-026-dropbox-scan-binary-blocklist.md) | dropbox 脱敏扫描改二进制黑名单（覆盖代码/配置投料） | accepted | claude | `scripts/wiki_lint.py`, `scripts/README.md`, `wiki-design/02-workflows.md` | `scripts/wiki_eval.py`, `scripts/wiki_common.py`, `scripts/wiki_graph.py`, `knowledge/.wiki-schema.md`, `wiki-design/02-workflows.md` |
| [rfc_20260622_027](RFC-027-code-knowledgization.md) | DataWorks 代码知识化（M1+M2 accepted：asset-mapping 页型 + 代码梳理/传导口径；M3+M4 deferred：失效检测/回源待接口核实） | accepted | claude |
| [rfc_20260623_028](RFC-028-code-knowledgization-ops.md) | 代码知识化工程化（全量索引 + 变更增量 + 分层建页 + sqlglot 血缘解析；不影响现有库入库/查询） | accepted | claude | `scripts/dataworks_client.py`, `scripts/wiki_freshness.py`, `scripts/wiki_index.py`, `wiki-design/02-workflows.md`, `scripts/README.md`, `tests/` | `wiki-design/02-workflows.md`, `scripts/wiki_freshness.py`, `scripts/wiki_common.py`, `scripts/README.md`, `tests/` |
| [rfc_20260702_029](RFC-029-reverse-lookup-physical-layer-roles.md) | 反查物理层级扩展 + 推荐角色分档（DIM / S-* / TMP / DDM / EDW） | accepted | claude | `scripts/wiki_index.py`, `wiki-design/02-workflows.md`, `scripts/README.md`, `tests/` |
| [rfc_20260703_030](RFC-030-ods-source-binding-parsed.md) | ODS 源表 binding 配置解析（parsed/inferred/unparsed/ambiguous）+ 批量快审背书流程 | accepted | claude |
| [rfc_20260703_031](RFC-031-datasource-resolution.md) | DataWorks 数据源 → 线上库解析（别名 resolution + 无凭证红线） | accepted | claude | `scripts/dataworks_client.py`, `scripts/wiki_index.py`, `scripts/wiki_freshness.py`, `scripts/README.md`, `wiki-design/02-workflows.md`, `tests/` | `scripts/wiki_index.py`, `scripts/dataworks_client.py`, `scripts/wiki_freshness.py`, `wiki-design/02-workflows.md`, `scripts/README.md`, `tests/` |
| [rfc_20260706_032](RFC-032-deployed-version-evidence-and-binding-lookup.md) | 已部署版本取码 + evidence 证据片段模式 + reverse binding 键 / origin 溯源 | accepted | claude | `scripts/dataworks_client.py`, `scripts/wiki_index.py`, `scripts/README.md`, `wiki-design/02-workflows.md`, `tests/` |
| [rfc_20260707_033](RFC-033-per-machine-env-config.md) | 每机器环境配置抽象 — bin/wiki 覆盖在线工具 + 实例 root 别名 + doctor | accepted | claude | `bin/wiki`, `scripts/wiki_common.py`, `scripts/README.md`, `wiki-design/02-workflows.md`, `tests/` |

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

## 真实摩擦来源

机制类 RFC 必填：说明这个机制来自哪个真实使用摩擦、审计发现、数据实例或重复失败案例。非机制类可写：`不适用：纯 bugfix / 文档修复，未引入新机制`。

## 验证方式

机制类 RFC 必填：说明 apply 后如何验证，包括 fixture、真实实例 smoke、lint/graph/eval、人工审计或回归命令。非机制类可写：`不适用：纯 bugfix / 文档修复，未引入新机制`。

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
| 双 Agent 并发写入约束 | P2 | 明确 single-writer 或把 `review_queue.json` / `source_manifest.json` 拆成一条一文件，降低 git 冲突（团队场景已由 RFC-023 单 writer 模式部分解决） |
| MR 自动评审 | P1 | 本机 agent 经 GitLab API 自动评估 knowledge-cmn 投料 MR：diff 路径合规（机械）+ 图片/PDF 多模态查凭证（补文本扫描盲区）+ 质量初判。**边界已定**：低风险自动 approve+merge（评估理由留 MR 评论），可疑留人工；触发先用 ingest 会话顺带。**启动条件：首批真实 MR 人工审过几个、有样本后再立 RFC**（用户 2026-06-10 拍板） |
| visibility / PII 字段 | P2 | frontmatter 加 `visibility: private \| team \| public`，lint 在 public 页扫描 PII pattern |
