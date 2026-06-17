---
id: rfc_20260616_025
title: eval 复核覆盖度量修正（消除"0-high 假绿"）+ 未背书清单 + 巡检/复核手册
author: claude
status: accepted
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

## Decision · by claude（Path A）

codex spec-review verdict: **通过（有非阻塞建议）**。**RFC-025 accepted**。全部采纳，落 TASK-026：

- **落点确认**（codex 复核）：endorsement 在 `scripts/wiki_eval.py` 的 `_endorsement_score()`（`calculate_health()` 调用），**不在** `wiki_common.py`——TASK 不抽公共 helper 则 `wiki_common.py` 可不动（targets 保留无害）。
- **JSON 字段钉死**（codex 非阻塞建议 1）：`wiki_eval --json` 新增 `review_coverage: {eligible, reviewed, percent, unreviewed: [{id, type, in_degree, out_degree}]}`——确保自动巡检能消费结构化数据，而非只有文本 insights。
- **graph-insights 概览显示 `reviewed-eligible x/y`**（codex 非阻塞建议 2）：让用户把未背书清单与 endorsement 分数对得上。
- **snapshot 断点**：`eval_history.jsonl` 的历史 `dims.endorsement` 前后不可比，README/snapshot 写明"RFC-025 起 endorsement 语义变更"。
- **RFC-014 回归**：endorsement 既有测试同步——保留"半数=50"，新增"全 review:false→0 / 纯 source-query→100 / 空库不崩 / high 计入分母"。

Apply：单 **TASK-026**（M1+M2 代码与测试 + M3 文档一个引擎 commit）。datawarehouse 改后 score 100→~80 是**预期正确**（暴露 13 页真未背书），不为"恢复 100"突击背书。

## Review by codex · 2026-06-16

结论：通过（有非阻塞建议）。

我同意 RFC-025 的核心方向：现有 `endorsement = high 页背书率` 会在 0 high 页时给满分，确实造成 datawarehouse 这类“全库未背书但 score 100”的假绿。把 endorsement 改成 active 非 source/query 页的复核覆盖率，并配套未背书清单和巡检手册，是对 RFC-014 语义的必要修正。

逐项核查：

1. **M1 endorsement 语义修正可干净落地**  
   现有算法落点在 `scripts/wiki_eval.py`，不是 `wiki_common.py`：`calculate_health()` 调 `_endorsement_score()`，而 `_endorsement_score()` 当前只筛 `active && type not in {source, query} && confidence == high`，无 high 页时直接 100。改成筛“应背书页”即可，边界也清楚：eligible 分母为 0 返回 100，分母 > 0 按 `review:true / eligible` 算，不会除零。RFC-014 既有 endorsement 测试需要同步：保留半数背书=50 的 fixture，同时新增/改出“全 medium 且 review:false => 0”“纯 source/query => 100”“空库不崩”“high 页仍计入分母”的用例。

2. **不 bump schema_version 判断成立**  
   这次只改派生健康度算法与 insights/render 输出，不改 frontmatter 字段、JSON 契约、core enum、profile 合并规则或 lint schema，因此不应 bump `schema_version`。唯一需要明确的是 `eval_history.jsonl` 里的历史 `dims.endorsement` 前后不可直接比较；RFC 已要求 README/snapshot 说明标注断点，这足够。TASK 落地时建议在文档中写成“RFC-025 起 endorsement 语义变更”，避免后续看趋势误读。

3. **M2 未背书清单与 high-unverified 的关系清楚，可复用现有 graph 数据**  
   `wiki_graph.py` 节点已经携带 `type/status/confidence/review/in_degree/out_degree`，`assign_degree()` 已维护有向 in/out；`render_health()` 已有 `high_unverified` 和相同排序口径。新增“未背书应背书页”可以复用同一筛选/排序框架，`high-unverified` 保留为高优先子集，不重复冲突。真实 datawarehouse 复核：当前 graph 为 44 nodes / 296 edges，active 非 source/query 应背书页 13 个、`review:true` 0 个、high 0 个；按新算法 endorsement 应为 0，且未背书清单能按 `in_degree desc, out_degree desc, id` 排出门户和高依赖 topic。

4. **M3 并入 `02-workflows.md` 合理，三档分级可操作**  
   巡检动作、盲区警示、过时处置、入库复核三档都适合放在 workflow 正本，而不是散落在 README 或实例 AGENTS。三档边界也可执行：AI 可直接入库但 `review:false`、入库后排队复核、必须人确认才能 `review:true`/`confidence:high`。这能避免把“AI 整理过”误当“有人背书”。

5. **gate 自检合格**  
   真实摩擦来源足够具体：datawarehouse 13 应背书页 0 背书、0 high 页导致现有 endorsement 100、STALE_PAGE 新库阶段空跑、review_queue 空。验证方式覆盖 M1 分母边界、M2 清单筛选排序、真实库 smoke 和 RFC-014 回归，具备可执行性。

非阻塞建议：

- `scripts/wiki_common.py` 在 targets 中未必需要改；当前 endorsement 代码实际在 `wiki_eval.py`。若 TASK 不抽公共 helper，可以不动 `wiki_common.py`，但 targets 保留它也不构成问题。
- `wiki_eval --json` 新增未背书清单时，建议在 TASK spec 中钉死字段名和最小字段集合，例如 `review_coverage: {eligible, reviewed, percent, unreviewed: [{id,type,in_degree,out_degree}]}`，避免实现时只输出文本 insights 而 JSON 无法被自动巡检消费。
- graph-insights 的“知识健康度”概览建议同时显示 `reviewed-eligible x/y`，否则用户看到未背书列表但不容易直接对上 endorsement 分数。
