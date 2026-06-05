---
id: rfc_20260604_019
title: ingest 批量编排（triage 全量 + apply 清单 + 逐份处理追踪 + 断点续传）
author: claude
status: proposed
created: 2026-06-04
updated: 2026-06-04
targets:
  - scripts/wiki_lint.py
  - scripts/wiki_common.py
  - scripts/README.md
  - knowledge/.wiki-schema.md
  - wiki-design/02-workflows.md
  - wiki-design/04-agent-rules.md
reviewers:
  - codex
  - user
---

# RFC-019: ingest 批量编排

## 背景

一次性 ingest 大量资料（datawarehouse 一次 17 文档 + 75 图）会撑爆写入 AI 的 context，导致**整理不详细、遗漏、前后标准不一**。这个风险**已经发生**：datawarehouse 整理做了 5-6 轮（初版 source 被脱空 / 图全丢 → 多轮补图、补描述、补录纠错），这些"多轮"正是"一次吞不下、事后补救"的症状。

根因：ingest 规范（RFC-003/016/018）只定义"一份资料怎么整理"，**没有"批量怎么编排"**——一次给 N 份就一次性吞，context 必然不够。

> 机制其实已具备（triage/apply 两步 + `source_manifest.status` 的 `new/triaged/ingested/failed`），只是没规定"分批 + 清单 + 续传"的用法。本 RFC 补这层编排。

## 提案

把批量 ingest 编排成 **triage 全量（轻）→ apply 清单 → 逐份深入（重）→ 每份持久化 → 进度追踪 / 断点续传**。

### 1. triage 全量（一次扫完，轻量）

一次处理所有待 ingest 资料的 **triage**（不写正文，context 占用小）：

- 每份登记 `source_manifest`（`status: triaged`）+ 建 source 占位（`status: draft` / `confidence: low`）+ 抽实体做 alias matching。
- **不写详细正文 / 不做图多模态描述**——这些留给 apply。
- 全量 triage 后，库里有一份"待深入"的 source 骨架清单。

### 2. apply 清单（进度可见，单一真相）

`source_manifest.status` 就是进度真相；`wiki_lint` 新增 **「ingest 进度」报告段**（从 manifest 算，不引新字段）：

```
ingest 进度：triaged 待 apply N · ingested 完成 M · failed K
待 apply（按 manifest 顺序）：
  - src_xxx_aaa  （triaged）
  - src_xxx_bbb  （triaged）
  ...
```

这就是**可见的 apply 清单**——随时知道"还剩哪些没深入整理"。可选 `--ingest-status` 只出这段。

### 3. apply 逐份深入（每次 context 只装一份）

- **一次只 apply 1 份**（默认；可小批 ≤3，由人/AI 视 context 决定）：读该份原文 → 写详细 source 正文 + 联动 topic/entity + 图多模态描述 + 子链接处理（RFC-018）→ 校验 → `status: triaged → ingested`。
- context 每次只装一份原文 + 写一份页 → **详细度不会因"第 17 份"而降**。

### 4. 每份持久化 + 断点续传

- 每 apply 完一份（或一小批）**立即 commit**（数据仓）——持久化，会话可随时中断。
- **断点续传**：新会话跑 `wiki_lint`（看 ingest 进度段）→ 取下一个 `triaged` → 继续 apply。不依赖会话记忆,manifest status 是真相。
- apply 失败的份标 `status: failed`，进度段单列,人决定重试/跳过。

### 防 context 爆的约定

- triage 可全量（轻）；**apply 严禁一次吞多份**——逐份或 ≤3 小批。
- 单份原文过大时，apply 内部也可分段，但一份的 source 是一个 commit 单元。

## 范围（不做 → Backlog）

| 议题 | 不做的理由 | 触发条件 |
| --- | --- | --- |
| 自动决定"一批几份"（按 token 估算） | AI/人按 context 判断即可，自动估算过度 | 有稳定 token 预算接口 |
| 并行 apply（多 agent） | 单 writer 简单可靠；并行有 git 冲突（backlog 并发约束） | 有并发需求 |
| 自动抓取原文（adapter） | RFC-016 已留 backlog | 有抓取通道 |

## 替代方案

| 决策点 | 选择 | 拒绝 |
| --- | --- | --- |
| 编排 | **triage 全量 + apply 逐份 + manifest 追踪** | 一次性全 apply（context 爆、质量降，就是现状 bug） |
| 清单载体 | **manifest status 派生（lint 进度段）** | 新建独立队列文件（与 manifest 重复、易 drift） |
| 持久化 | **每份 commit + 断点续传** | 全做完再 commit（中途丢、不可恢复） |
| 一批份数 | **逐份 / ≤3 小批（约定）** | 不限（爆 context） |

## 影响范围

### 改动
- `scripts/wiki_lint.py`：新增「ingest 进度」报告段（从 `source_manifest.status` 聚合 triaged/ingested/failed + 待 apply 列表）；可选 `--ingest-status` 只出该段。**纯读 manifest、不改校验逻辑/退出码**。
- `scripts/wiki_common.py`：可能加聚合 helper（如需）。
- `scripts/README.md`：ingest 进度用法。
- `wiki-design/02-workflows.md`：ingest 流程改批量编排（triage 全量 → apply 清单 → 逐份 → commit → 续传）。
- `wiki-design/04-agent-rules.md`：Agent 批量 ingest 约定（apply 严禁一次吞多份）。
- `knowledge/.wiki-schema.md`：批量编排约定（`--sync-schema` 到实例）。

### 不改动
- `source_manifest` 字段 / status enum（复用 RFC-017 的现有值）；core schema；graph/eval。
- lint 退出码（进度段是信息输出，不改 error/warning 判定）。

### 零回归验证
- 进度段是新增只读输出：现有 lint error/warning/退出码不变。
- fixture：manifest 含混合 status（triaged/ingested/failed）→ 进度段计数 + 待 apply 列表正确。
- 现有三库 lint 不回归（datawarehouse 全 ingested → 待 apply 0）。

## Review by codex · YYYY-MM-DD

（待 Codex 追加）

## Decision

（待用户填写，或授权某 Agent 代写）
