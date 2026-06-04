---
id: rfc_20260604_018
title: ingest 子链接处理（关联保留 + source-gap 登记 + 不递归）
author: claude
status: proposed
created: 2026-06-04
updated: 2026-06-04
targets:
  - knowledge/.wiki-schema.md
  - wiki-design/02-workflows.md
  - wiki-design/04-agent-rules.md
reviewers:
  - codex
  - user
---

# RFC-018: ingest 子链接处理

## 背景

整理数仓内部 Wiki 文档、做问答时发现：**源文档正文里指向其它文档的子链接没被处理**——既没保留"链向哪个文档"的关联，子链接目标文档也没进库或登记成待办。用户答问时"A 文档提到的 B 文档"在库里查无此页。

排查确认这是 **ingest 规范的真空**：`AGENTS.md` / `schema.md` / `02-workflows` 的 ingest 段从未规定"文档内部子链接怎么处理"（grep 全空）。叠加脱敏红线"不保存内部分享链接 token"，新 agent 把链接**整个脱掉**，连"这里链向 X 文档"的语义都丢了。

> 真实使用驱动 gap 的又一例。期间新 agent 已自主跑出一套合理实践（见下"现状"），本 RFC 把它固化成规范。

### 现状：新 agent 已实践的模式（本 RFC 对齐它）

- 父 source（`dw-common-qa`）用 `related_ids` 关联子 source（`aliyun-data-analysis`）；子 source 降 `draft`/`low`（只抓到标题元信息、正文 iframe 空）。
- 新建 **open-question** `oq_..._aliyun-data-analysis-source-gap` 登记待补抓：`source_ids` 指父 + 子 source，正文「已知信息（来源 + 当前抓到什么）+ 待确认（缺什么 / 为何没抓到）」。
- 没有自动递归。

## 提案

把"ingest 时源文档内部链接怎么处理"写进规范。核心三条：**关联保留、待办登记、不递归**。

### 1. 链接分类（写入 AI 在 ingest 时判断）

源文档正文里的链接分两类：

| 类型 | 处理 |
| --- | --- |
| **内部文档链接**（同 Wiki / 同知识源的其它文档） | 走 §2 关联保留 + §3 source-gap 登记 |
| **外部链接**（其它站点 / 文档外的 URL） | 仅在正文保留为外链说明（脱 token），**不建 source、不跟进** |

### 2. 关联保留（脱 token，但留"链向谁"）

- 脱掉链接里的 token / 内部 URL（红线不变），但**保留"父文档链向 X 文档"这个语义事实**——不要把关联也脱没。
- 子链接目标若值得收：建子 source（正文未抓到时为 `draft`/`low` 占位），父 source 用 `related_ids` + 显示层 `related` 双层关联子 source。

### 3. source-gap 登记（子链接目标未 ingest / 正文未抓到）

建一个 **open-question**（`oq_YYYYMMDD_<slug>-source-gap`，沿用现状模式）：

- `source_ids`：指向父 source（发现处）+ 子 source 占位（若建了）。
- 正文：
  - `## 已知信息`：父文档在哪提到、当前对子文档抓到了什么（标题 / 修改时间等元信息）。
  - `## 待确认`：缺什么、为何没抓到（权限 / iframe 空 / 需重新分享等）、是否含值得收的内容。
- 这样"待补抓的文档"成为知识库里**可见、可导航、进图谱**的一等待办，而不是埋在 `review_queue.json`。

### 4. 不自动递归（用户强调）

- **绝不自动跟着链接 ingest**：内部链接会形成文档环（A→B→A），外部链接更会无限延伸 / 循环。
- 只**登记** source-gap open-question 待办，由人决定哪些跟进、何时补抓。
- 补抓时把对应 source-gap open-question 标 `archived`/`status` 收尾（配合 RFC-017 的 source `superseded`/`archived`）。

### 工具边界（为什么是约定而非工具强制）

- 工具**读不到源文档原文**、也不知道一篇文档里有哪些子链接——所以"是否发现了所有子链接"**无法机械校验**，这条只能是**写入 AI 的约定**。
- 工具侧无需新增：source-gap 就是 open-question，现有 lint 已校验其结构（id/引用完整）；本 RFC 不改 scripts。
- 这是"机械校验 > 人肉遵守"原则的**能力边界例外**：工具够不到的地方，靠明确约定 + 可见的 open-question 待办兜住。

## 范围（不做 → Backlog）

| 议题 | 不做的理由 | 触发条件 |
| --- | --- | --- |
| 自动抓取子链接正文（web/wiki adapter） | 抓取是另一环（RFC-016 已把 URL 抓取留 backlog）；且需登录态 | 有稳定抓取通道时 |
| 工具校验"子链接是否都登记 gap" | 工具读不到原文、无法判断 | — |
| source-gap 自动转 source（补抓后） | 人工补抓 + 手动收尾即可 | 抓取自动化后 |

## 替代方案

| 决策点 | 选择 | 拒绝 |
| --- | --- | --- |
| 待办载体 | **open-question（`*-source-gap`）**（进图谱、可导航，对齐新 agent 实践） | `review_queue.json`（埋在 JSON、不可见、不进图谱） |
| 递归 | **不递归，只登记待办** | 自动递归（内/外链都会循环、触达不该收的） |
| 关联 | **保留"链向 X"语义 + related_ids 关联子 source** | 整个脱掉（丢关联，就是当前 bug） |
| 外部链接 | **正文外链说明，不建 source** | 建 source（外部不可控、会爆炸） |

## 影响范围

### 改动（纯约定 / 流程文档，不改 scripts）
- `wiki-design/02-workflows.md`：ingest 流程加"子链接处理"步骤（分类 / 关联保留 / source-gap 登记 / 不递归）。
- `wiki-design/04-agent-rules.md`：Agent ingest 行为补子链接约定。
- `knowledge/.wiki-schema.md`：ingest 子链接约定 + source-gap open-question 模式（`--sync-schema` 到实例）。
- 衍生同步（非引擎 targets，TASK 内或后续）：skill `references/schema.md`、各库根 `AGENTS.md`。

### 不改动
- scripts（lint/graph/eval/init）：source-gap 就是 open-question，现有校验够；无新工具。
- core schema、page 类型、ID/canonical 规则。

### 落地后数据动作（TASK 内、数据仓单独提交）
- datawarehouse：新 agent 已建的 source-gap open-question + 父子关联**已符合本规范**，TASK 只需确认对齐（必要时补正文骨架/命名），不重做。

### 零回归验证
- 纯文档约定，scripts 不变 → 现有测试不回归。
- datawarehouse 现有 source-gap open-question 跑 lint exit 0（已验证 30 页 0/0）。

## Review by codex · YYYY-MM-DD

（待 Codex 追加）

## Decision

（待用户填写，或授权某 Agent 代写）
