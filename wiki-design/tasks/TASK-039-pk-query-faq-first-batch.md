---
id: task_20260702_039
title: knowledge-pk 高频问答 query 页 — 首批 FAQ（补 P1 缺失页型）
author: claude
executor: codex
status: done
type: other
created: 2026-07-02
updated: 2026-07-02
related_rfcs: []
---

# TASK-039: knowledge-pk query FAQ 首批

## 目标

建立 `wiki/queries/` 页型的首批 FAQ（当前该页型为 0），把团队高频业务问题沉淀成可检索问答，双读者（团队成员 + AI）直接命中。首批聚焦已有厚口径 / 已背书支撑的资产域 + 少量风控域，避免把 FAQ 建在空口径上。

## 前置条件

- 支撑口径页已在：资产借还款 DWD topic + 4 个已背书 asset-mapping（asset-product / debt-status / cooling-off-repayment / loan-apply-no）。
- knowledge-pk working tree clean；`PY` 同 TASK-036。

## 强约束

1. **query 只增量说明使用方式**，口径以上游定义点为准，`related_ids` / `sources` 回指支撑的 topic / asset-mapping / source，**禁止在 query 里重复展开口径枚举**（指回定义点）。
2. 每条 FAQ 遵循「答疑引用格式」：关键判断用 `[1]`/`[2]` 标注，末尾列 `[[page|名]] · 路径 · 支撑说明`；依赖 source 摘要页的同时给 `source_url`。
3. **每条强结论必须有 ≥1 source / related 支撑页**，不能建成无出处的自由问答；`related_ids` 必须**实际非空**（校验时不能只 grep 字段名，要确认列表有项）。
4. query 页 AI 可写 `review: false`（入库复核第 1 档：普通问答沉淀），**不必逐条 maintainer 背书**——这是 query 与 TASK-038 口径页的关键差异，门槛低、快速见效。
5. 不制造 dangling wikilink；新增 FAQ 区进 `index.md`。

## 步骤

1. **定 query 页模板**：`## 问题` / `## 一句话答案` / `## 口径依据（含引用）` / `## 适用边界` / `## 相关页`。
2. **首批 FAQ（我拟，Codex 按现有支撑页可增删）**：
   - `debt_status 债务状态怎么算 / 有哪些取值` → 指 debt-status
   - `冷静期还款怎么识别` → 指 cooling-off-repayment（依赖 repay_type='cancel'）
   - `借款申请进件号 loan_apply_no 从哪来` → 指 loan-apply-no（上游 publish_apply_no）
   - `成交标 is_deal 怎么定义 / asset_product 怎么分类` → 指 asset-loan-repayment-dwd + asset-product
   - `查逾期 / 延期用哪张表` → 指 asset-delay-status + 反查路由 + tmp caveat
   - `信用报告 DataCheck 和 Tasdeeq 有什么区别、该用哪个` → 先指两个 topic，并在正文标注「更完整对比见 comparison（待建）」
3. 建 `wiki/queries/*.md`，`related_ids` 指支撑页，加 Obsidian `#tag`。
4. 更新 `index.md`（新增「常见问答」区）+ `log.md`。
5. lint / graph / eval。

## 验证

```bash
PY="/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python"
PK=/Users/zhangjunwu/workspace/obsidian/knowledge-pk
ls $PK/wiki/queries/*.md | wc -l
# related_ids 非空校验：grep -L 只证明字段存在，executor 须另确认列表非空（脚本 / lint）
grep -L "related_ids:" $PK/wiki/queries/*.md   # 字段存在性：期望无输出（非空需额外校验）
$PY scripts/wiki_graph.py --root $PK 2>&1 | tail -5   # 期望无 dangling wikilink
$PY scripts/wiki_lint.py --root $PK --check-only; echo lint=$?
$PY scripts/wiki_eval.py --root $PK --json | python3 -c "import sys,json;d=json.load(sys.stdin);print('score',d['score'],'connectivity',d['dims']['connectivity'])"
```

## 完成后报告格式

- query 页模板定义
- 首批 FAQ 清单（问题 + 支撑页）
- graph 校验：无 dangling / 无 orphan、connectivity 不降
- index.md 新增区、lint / eval 输出、commit sha、偏离或异常

## Execution log by codex · 2026-07-02

### Step 0 spec-review

复核通过。`query` 是 base schema 页型，目录 `wiki/queries/`、id prefix `que_`；knowledge-pk 当前仅有 `.gitkeep`，本 task 是合理的 0→1 补齐。执行时额外用脚本确认每个 query 的 `related_ids` 列表非空。

### query 页模板

每页固定段：`## 问题` / `## 一句话答案` / `## 口径依据（含引用）` / `## 适用边界` / `## 相关页`。query 页只做入口和使用说明，不复制上游枚举或完整口径。

### 首批 FAQ

- `wiki/queries/debt-status-how-defined.md`：`debt_status` 债务状态怎么算；支撑 `debt-status` 与 `asset-loan-debt-caliber`。
- `wiki/queries/cooling-off-repayment-how-to-identify.md`：冷静期还款怎么识别；支撑 `cooling-off-repayment` 与 `asset-loan-list-caliber`。
- `wiki/queries/loan-apply-no-source.md`：`loan_apply_no` 从哪来；支撑 `loan-apply-no` 与资产借还款概览。
- `wiki/queries/is-deal-and-asset-product.md`：`is_deal` 和 `asset_product` 怎么看；支撑 `asset-loan-list-caliber` 与 `asset-product`。
- `wiki/queries/overdue-delay-which-table.md`：查逾期 / 延期用哪张表；支撑债务期次、延期状态和资产 DWB 候选。
- `wiki/queries/datacheck-vs-tasdeeq.md`：DataCheck 和 Tasdeeq 区别；支撑两个三方信用报告 topic，并明确完整 comparison 待建。

### 导航

- `index.md` 新增「常见问答」区。
- `log.md` 新增 TASK-039 记录。

### 验证

```text
find wiki/queries -maxdepth 1 -type f -name '*.md' | wc -l
6

related_ids non-empty:
cooling-off-repayment-how-to-identify.md 3
datacheck-vs-tasdeeq.md 3
debt-status-how-defined.md 3
is-deal-and-asset-product.md 3
loan-apply-no-source.md 3
overdue-delay-which-table.md 5

wiki_graph.py --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk
wiki-graph: 1405 nodes, 1987 edges, 52 communities

wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk --check-only
错误: 0 · 警告: 0
lint=0

wiki_eval.py --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk --json
score 82 connectivity 100 review_coverage eligible=45 reviewed=4 percent=9
```

### Commit

- knowledge-pk commit：`646bce0` (`[pk task-039] add first query FAQ pages`)

### 偏离或异常

- 无。query 页保持 `review:false`，且不参与 endorsement eligible 分母。


## Evaluation by claude · 2026-07-02

**Verdict: PASS。** 独立核验 `wiki/queries/debt-status-how-defined.md`（+ 另 5 页清单齐）：

- 6 个 query 覆盖资产核心 + DataCheck/Tasdeeq；`related_ids` 实测非空。
- **守边界**：答案指回 `debt-status` mapping + caliber 定义点，未复制枚举；`[1][2]` 引用含 `page · path · 支撑`，符合答疑格式。
- `datacheck-vs-tasdeeq` 正确标「完整 comparison 待建」，没抢 comparison 页型。
- query 属复核第 1 档，`review:false` 合理；graph connectivity 未降（1405 nodes / 1987 edges）。

提示：这 6 页仍未背书，若要作为团队 / AI 命中的「标准答案」，需 maintainer 背书或至少确认。


## Review by codex · 2026-07-02

结论：通过。

核实结果：

- `query` 是 base schema 已有页型：`type=query`、id prefix `que`、目录 `wiki/queries/`。knowledge-pk 不需要额外 profile 扩展即可创建 query 页。
- 当前 `wiki/queries/` 只有 `.gitkeep`，本 task 是合理的 0→1 补齐。
- 首批 FAQ 的支撑页基本已在：`asset-product`、`debt-status`、`cooling-off-repayment`、`loan-apply-no`、`asset-delay-status`、`asset-loan-repayment-dwd`、`asset-dwb-repay-amount`、`risk-datacheck-section-dwd`、`risk-tasdeeq-dwd-foundation` 均存在或有 source 支撑。
- `query` 不参与 stale / `UNVERIFIED_HIGH` 检查，`review:false` 作为低摩擦 FAQ 沉淀符合现有 trust 设计。

执行注意：

- 每个 query 页必须至少有一个 `related_ids` 支撑页；不要把字段枚举复制到 query 正文里，保持“问答入口指向定义点”的边界。
- “DataCheck vs Tasdeeq”可以先建 query 并明确“完整 comparison 待建”，不要在 query 里提前替代 comparison 页。
- 验证里的 `grep -L "related_ids:"` 只能证明字段存在，不能证明非空；实现时建议额外用 lint 或小脚本确认 `related_ids` 列表非空。
