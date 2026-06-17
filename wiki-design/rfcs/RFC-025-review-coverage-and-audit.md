---
id: rfc_20260616_025
title: eval 复核覆盖度量修正（消除"0-high 假绿"）+ 未背书清单 + 巡检/复核手册
author: claude
status: proposed
created: 2026-06-16
updated: 2026-06-16
targets:
  - scripts/wiki_eval.py
  - scripts/wiki_common.py
  - scripts/wiki_graph.py
  - scripts/README.md
  - knowledge/.wiki-schema.md
  - wiki-design/02-workflows.md
  - tests/
reviewers:
  - codex
  - user
---

# RFC-025: 复核覆盖度量修正 + 巡检/复核手册

## 背景

需求：怎么定期发现知识过时、哪些入库要人复核。按现有信号（STALE_PAGE / UNVERIFIED_HIGH / eval / review_queue）实跑 datawarehouse，暴露**现有度量对"大面积未复核"是盲的**：

- 实测：datawarehouse **13 个应背书页（12 topic + 1 synthesis，active 且 type ∉ {source,query}）复核覆盖率 0%**（全 `review:false`、0 个 `review:true`），但 `wiki_eval` 给 **score 100 / endorsement 100**。
- 根因：`endorsement` 维度（RFC-014）只算 **high 页的背书率**；datawarehouse **0 个 high 页** → 分母 0 → 满分。**全库无人背书，度量却满分 = 假绿。**
- 叠加：STALE_PAGE 对新库是**空跑**——知识 6 月初入，阈值 decision/synthesis/comparison/open-question=120 天（最早 ~10 月才首触发）、topic/entity=365 天。
- review_queue 空，没有任何机制把"该复核的"自动排进去。

结论：光看现有信号会被 score 100 骗。需要（M1）修度量让"未背书"拉低分、（M2）把"该复核啥"列成行动清单、（M3）把巡检与复核规则沉淀成正本手册并写明这些盲区。

## 提案

### M1 · endorsement 维度修正（消除 0-high 假绿）

把 `endorsement` 从"high 页背书率"改为"**应背书页复核覆盖率**"：

- **分母**：active 且 `type ∉ {source, query}` 的页（"应背书页"——source 是原始证据、query 是问答入口，本就不要求人背书）。
- **分子**：其中 `review: true` 的页。
- **边界**：
  - 分母 > 0 且分子 0（全未背书）→ endorsement **0**（**不再假绿**）。
  - 分母 = 0（纯 source/query 库或空库，无应背书页）→ endorsement 100（无可背书内容，不假惩罚）。
- high 页是应背书页的子集，自然计入；不再因"没有 high 页"而满分。
- **影响**：这是对 RFC-014 endorsement 语义的**修正**（原 high-only 定义即假绿之源）。eval snapshot 的 endorsement 历史值语义变化、趋势不可直接比——在 README/snapshot 说明里标注断点。**不动** frontmatter / JSON 契约 / core enum，故**不 bump `schema_version`**（待 codex 复核此判断）。

### M2 · 未背书清单（行动化）

`wiki_graph` 的 `maps/graph-insights.md`「知识健康度」段 + `wiki_eval --json` 增加**「未背书应背书页」清单**：

- 入选：active、`type ∉ {source, query}`、`review: false`。
- 排序：`in_degree desc, out_degree desc, id`（同 stale 优先列表——被依赖越多越该先复核）。
- 与现有 `high-unverified`（UNVERIFIED_HIGH）的关系：后者是前者中 `confidence: high` 的高优先子集，**保留单列**（最该先背书的）。
- 价值：maintainer 一眼看到"该背书哪几页、先背哪页"，而不只是一个掉下来的分数。

### M3 · 巡检与复核手册进正本（`02-workflows.md`）

把"怎么定期查 + 哪些入库要复核"沉淀为标准流程（以用户提供的方案为底稿，补实测发现的盲区警示）：

- **周巡检动作**：跑 `wiki_lint`（STALE_PAGE/UNVERIFIED_HIGH）+ `wiki_graph`（stale 优先 / 未背书清单）+ `wiki_eval --json`（score + endorsement 覆盖率）+ 看 `review_queue`（7 类：contradiction/duplicate/missing_page/confirm/suggestion/source_gap/stale_claim）+ 近期高频命中页。
- **⚠️ 盲区警示**（必须写进手册）：① 新库前几个月 staleness 是空跑（未到阈值不代表没过时）；② endorsement 修正前对"全未背书"是盲的——即便修正后，也要看**未背书清单**而非只看 score。
- **过时处置**：局部口径变→改正文保持 active；整体过时无新答案→`status: stale` + `review:false`；被替代→`archived` + `superseded_by`；人确认仍有效→更新 `last_verified`，必要时 `review:true`。
- **入库复核分级**（三档）：
  - AI 可直接入库（`review:false`）：原始 source 摘要、普通问答、低风险操作说明、检索入口。
  - 入库后排队复核：权限/审批/账号/生产操作流程、数据口径/指标定义/分层规范/命名规范、安全/隐私/敏感数据/凭证、来源冲突或新源推翻旧口径、仅从截图/聊天/残缺文档整理出的内容。
  - 必须人确认才能背书：设 `review:true`、标 `confidence:high`（非 source/query）、归档/合并/拆分/替代等结构性变更、"标准口径"页。
- 一句定调写进手册：**`review:true` 不是"AI 整理过"，而是"有人愿意为当前内容背书"。**

## 真实摩擦来源

机制类，证据为本会话实测：datawarehouse 13 应背书页复核覆盖率 0%，`wiki_eval` 却 score 100 / endorsement 100（0 high 页导致），STALE_PAGE 空跑、review_queue 空——现有度量发现不了"整库未背书"。

## 验证方式

- **M1 fixture**：应背书页全 `review:false` → endorsement 0；半数 true → 50；纯 source/query 库（无应背书页）→ endorsement 100（不假惩罚）；空库不崩；含 high 页时 high 计入分母分子。
- **M2 fixture**：未背书清单只含 active 非 source/query 的 review:false 页、按 in_degree 排序；high-unverified 仍单列。
- **真实库 smoke**：datawarehouse 改后 endorsement → 0、score 100 → ~80、graph-insights 列出 13 页未背书清单（被依赖多的 topic 在前）。
- **回归**：012~024 套件全过（注意 RFC-014 既有 endorsement 测试需按新语义更新）。

## 替代方案

- **新增独立维度 review-coverage、endorsement 保持 high-only**：两个相近维度易混；且 high-only 本身就是假绿 bug，不该保留。**放弃**，直接修 endorsement 语义。
- **惩罚式封顶**（全未背书时 score 强制 ≤ X）：不平滑、不可解释。**放弃**，用比例覆盖率（0~100 连续）。
- **lint 加未背书 warning 挡 CI**：复核覆盖是"进度"非"对错"，不该挡 CI（CI 是机械门禁）；放 eval/graph 度量 + 手册足够。**放弃**（业务库若要强制，可用 `wiki_eval --check` 设高阈值，已有机制）。

## 影响范围

- `scripts/wiki_eval.py` / `scripts/wiki_common.py`：endorsement 计算落点（Step 0 定位 `evaluate_instance`）改分母语义 + 边界。
- `scripts/wiki_graph.py`：graph-insights 未背书清单（复用现有 trust 视图渲染）。
- `scripts/README.md`：endorsement 新语义 + snapshot 断点说明。
- `knowledge/.wiki-schema.md`：「review 与可信度派生信号」段更新 endorsement 描述（散文，非 generated block）。
- `wiki-design/02-workflows.md`：M3 巡检/复核手册。
- `tests/`：`test_task_026*.py` + 更新 RFC-014 endorsement 相关断言。
- **不改**：frontmatter/JSON 契约、core enum、`schema_version`、STALE 阈值、实例数据。

## Apply 拆分建议

单 **TASK-026**：M1+M2 代码与测试 + M3 文档一个引擎 commit（M3 纯文档可同 commit）。datawarehouse 改后 score 下降是**预期正确行为**（暴露真实未背书），不需要为"恢复 100"去突击背书——背书是 maintainer 的真实判断动作，不在本 task。

## Review by codex · YYYY-MM-DD

（由 codex 追加，不覆盖本提案正文。）

## Decision

（由用户填写，或用户明确授权某 Agent 代写。）
