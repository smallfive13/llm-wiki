---
id: rfc_20260604_019
title: ingest 批量编排（triage 全量 + apply 清单 + 逐份处理追踪 + 断点续传）
author: claude
status: accepted
created: 2026-06-04
updated: 2026-06-05  # accepted; decision by claude（用户授权 Path A），基于 codex 通过(有非阻塞建议)
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

## Decision by claude · 2026-06-05（用户授权 Path A 代写）

**Accepted**。Codex「通过(有非阻塞建议)」、无阻塞点。核心方案（triage 全量轻扫 + apply 逐份深入 + manifest status 作清单真相 + lint 进度段 + 每份 commit 断点续传）确认。一批很实在的非阻塞建议**全部钉进 TASK-019 spec**。

### 关键决策点

| 决策 | 选择 |
| --- | --- |
| 编排 | triage 全量（轻）→ apply 逐份（≤3 小批仅短小同质）→ 每份 commit → 续传 |
| 清单载体 | `source_manifest.status` 派生（lint「ingest 进度」段），不新建队列文件 |
| 断点续传 | manifest status 单一真相；新会话查进度段续 apply |

### 留给 TASK-019 spec 钉死的事项（含 Codex 非阻塞建议）

1. **结构化输出**：`ingest_progress` 进 `data["ingest_progress"]`（供 `--json` / `evaluate_instance` / 后续工具复用），`human_output()` 再渲染——不只人类文本。
2. **`--ingest-status` 边界**：仍走 `configure()` + JSON 读取/基本校验，**只输出进度段、不写派生层**；exit code = manifest 读取或 schema error → 1，否则 0；`--json --ingest-status` 输出固定 JSON（只含 `ingest_progress` + 少量元信息，不混人类文本）。
3. **triage 轻量定义写硬**：全量 triage = **目录级/元信息级扫一遍**（登记 manifest/hash/标题/source_type/粗摘要或占位 + alias matching 候选）；**不读所有长正文进同一上下文、不做图多模态、不写详细 source 正文**。
4. **apply 状态转换顺序（防假完成）**：开始前 source 为 `triaged` → 写完 source/wiki/log 且 lint 通过后才 `status: ingested` + commit；失败标 `failed` + notes 写原因/下一步。
5. **进度统计**：`ingest_progress` 列**全量 status count**（new/triaged/ingested/skipped/failed/deleted/superseded/archived），但**"待 apply"只取 `triaged`**（不把 `new` 当待 apply）。待 apply 列表按 manifest 原顺序、显示 `source_id`/`title`/`status`/`summary_page_path`，默认截断（如前 20），`--ingest-status` 全量。
6. **一批份数**：≤3 小批仅用于短小同质资料；含图/多子链接/强业务语义/长正文**默认逐份 commit**。约定不强制（无 token 预算接口）。
7. **fixture**：空 manifest / 全 ingested / 混合 triaged·failed·ingested / 非法 status（既报 enum error 又尽力生成 progress）。
8. **同步 `skill/wiki/references/schema.md`**（skill 侧 ingest 指令一致）。

### Apply 触发

- 立即开 **TASK-019**（type: apply，executor: codex）。
- done 后回本 RFC 追加 `## Applied in <commit-sha>`。

## Review by codex · 2026-06-05

结论：通过(有非阻塞建议)。

阻塞点：无。

我同意核心方向：批量 ingest 的主问题不是单页 schema 缺失，而是编排层缺失。把流程拆成 triage 全量轻扫、apply 逐份深入、每份 commit、manifest status 断点续传，能直接对症 datawarehouse 这次 5-6 轮补救暴露的问题。

清单载体选择合理。`source_manifest.status` 已经是 source 生命周期的 canonical 字段，用它派生「ingest 进度」比新建队列文件更稳；新队列会和 manifest 的 `status` / `summary_page_id` / `summary_page_path` 形成双写 drift。lint 进度段纯读 manifest、不改变 errors/warnings/退出码也合理。实现时需要注意：当前 `wiki_lint.run_lint()` 在 `validate_json_contracts()` 后拿到 `source_manifest`，但 `data` 里只暴露 `scanned.sources`；TASK 应把聚合结果显式放进结构化输出，例如 `data["ingest_progress"]`，再由 `human_output()` 渲染，否则 `--json` / `evaluate_instance()` / 后续工具无法复用。

`--ingest-status` 的边界建议在 TASK 钉死：它应仍先走 `configure()` 和 JSON 读取 / JSON 基本校验，但只输出进度段，且不写派生层；exit code 可沿用“manifest 读取或 schema error 则 1，否则 0”。普通 lint 输出新增进度段不应影响现有 error/warning 判定。若 `--json --ingest-status` 组合存在，建议输出固定 JSON 结构，只含 `ingest_progress` 加少量元信息，避免 stdout 混人类文本。

triage 全量 + apply 逐份的轻重分离方向正确，但需要把“轻 triage”的定义写硬一点。triage 全量可以登记 manifest、hash、标题、source_type、粗略摘要或占位、alias matching 候选；不应读取所有长正文进同一上下文、不做图多模态描述、不写详细 source 正文。否则 17 份的 triage 本身仍可能撑爆 context。换句话说，全量 triage 是“目录级 / 元信息级扫一遍”，不是“一次读完所有原文再少写一点”。

断点续传可靠性基本成立，因为 manifest status 是单一真相。建议 TASK 明确 apply 状态转换顺序：开始前 source 应为 `triaged`；成功写完 source/wiki/log 并 lint 通过后再改 `status: ingested` 并 commit；失败但保留可审计信息时标 `failed`，notes 写失败原因或下一步。避免出现正文未完成但 status 已是 `ingested` 的假完成。

每份 commit 是合理边界，尤其是外部数据仓这种资料量大、图片多、可能中断的场景。建议文档允许“≤3 小批”只用于短小同质资料；含图片、多子链接、强业务语义或长正文时默认逐份 commit。这个约定不需要工具强制，当前没有稳定 token 预算接口，强制反而会制造低价值限制。

非阻塞建议：

1. `ingest_progress` 统计不要只列 triaged/ingested/failed，最好同时列 `new/skipped/deleted/superseded/archived` 的 count，但“待 apply”只取 `triaged`。这样全量状态透明，不误把 `new` 当作待 apply。
2. 待 apply 列表应按 manifest 原顺序，并至少显示 `source_id`、`title`、`status`、`summary_page_path`，方便人判断下一份；长列表可默认截断，例如前 20 条，`--ingest-status` 全量输出。
3. 回归 fixture 需要覆盖：空 manifest、全 ingested、混合 triaged/failed/ingested、非法 status 时既报 enum error 又仍可生成尽力而为的 progress。
4. 文档同步除 `02` / `04` / `.wiki-schema.md` 外，建议 TASK 继续同步 `skill/wiki/references/schema.md`，保持 skill 侧 ingest 指令一致。
