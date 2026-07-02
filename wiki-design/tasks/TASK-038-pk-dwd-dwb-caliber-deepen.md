---
id: task_20260702_038
title: knowledge-pk DWD/DWB 业务口径深化 — 深化模板 + 首批优先表
author: claude
executor: codex
status: done
type: other
created: 2026-07-02
updated: 2026-07-02
related_rfcs: [RFC-027, RFC-028]
---

# TASK-038: knowledge-pk DWD/DWB 口径深化

## 目标

把优先 DWD/DWB 主题页从「table-cluster 摘要」深化到可回答业务问题的粒度：字段含义、过滤条件、枚举取值、主键粒度、join / 去重逻辑、适用边界、caveat。本 task **建立深化模板 + 完成首批（资产借还款 + 风控审核额度）**，形成可复制方法，不一次做完 174 张 DWD。

## 前置条件

- 相关 source 摘要页已在（B001-B136 已回源）。**不依赖 TASK-037**（037 已重构为纯实例侧归类，不产出可直接消费的 layer；见其 Review）。
- knowledge-pk working tree clean；`PY` 同 TASK-036；DataWorks 凭证在 env（回源比对用）。

## 强约束

1. **分层建页策略**：深化只落 DWD / DWB 定义层（topic 或 asset-mapping），**不深化 DWS / ADS**（那些只记聚合增量，另 task）。
2. **口径唯一定义点**：同一字段只在一个权威页展开，其它页 `related_ids` 指回。深化时厘清与已有 asset-mapping 的分工——asset-mapping 放「业务词 → 字段」轻映射，topic 放完整口径，禁止重复展开同一枚举。
3. **回源不搬代码**：Codex `GetFile` 回源真实生产代码，正文只沉淀口径 / 血缘 / 判断 / caveat，不落代码正文、不落凭证 / 样本值；每条强结论标 source（`source_url` 或 source 页）。
4. **补 freshness 锚点**（顺带解 stream 1 长期病根）：深化页 frontmatter 补 `dataworks_ref` / `code_fingerprint` / `last_synced`，使未来增量防腐能反查到这些口径页（目前全库仅 8 个 asset-mapping 有锚点）。
5. **背书纪律**：口径页属「必须人工确认」档，深化后仍 `review: false` + 进 review_queue，**不 auto `review: true`**。预期 endorsement 维度会因新未背书页略降，属正常，不为抬分突击背书。
6. 逐表处理，每表单独 commit（RFC-019 逐份 ingest 纪律）。

## 步骤

1. **定深化模板**：frontmatter 加锚点字段；正文固定段：`## 字段字典`（字段→含义→枚举）/`## 过滤与粒度`（过滤条件 + 主键粒度）/`## join 与去重`/`## 适用边界`/`## caveat`。模板落一个约定页或 task 附录。
2. **首批表清单**（我拟，Codex 可据回源实况微调）。**本 task 只交付第一小批**：深化模板 + 资产 2 张核心（`dwd_asset_loan_list`、`dwd_asset_loan_debt`）+ 风控 1 张核心（额度变更或审核案件），其余表转后续 task，避免单 task 过大：
   - 资产借还款 DWD：`dwd_asset_loan_list`、`dwd_asset_loan_debt`、`dwd_asset_loan_list_apply_dtl`、`dwd_asset_repay_record`（已有基础，补 per-字段枚举 / 粒度 / 去重 / 非冷静期成交排序等）。
   - 风控审核与额度 DWD：审核案件 / 流程 / 人工审核结果 / 额度初始化 / 额度变更（挑核心 4-5 张，答疑高频）。
3. 逐表回源 → 按模板写深化正文 → 补锚点 → `related_ids` 回指 source 页 → 写 review_queue（**按「口径点」聚合，不每字段一条，避免队列噪音**）。
4. 更新 `index.md`（相关条目升级描述）/ `overview.md` / `log.md`。
5. lint / graph / eval；每表单独 commit。

## 验证

```bash
PY="/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python"
PK=/Users/zhangjunwu/workspace/obsidian/knowledge-pk
# 深化页含全部要素（字段字典/过滤粒度/join去重/适用边界/caveat）：抽查
grep -l "## 字段字典" $PK/wiki/topics/*.md $PK/wiki/asset-mappings/*.md
# 锚点字段合法、freshness 能识别新增锚点页
grep -c "^dataworks_ref:" $PK/wiki/topics/*.md 2>/dev/null | grep -v ':0'
$PY scripts/wiki_lint.py --root $PK --check-only; echo lint=$?
$PY scripts/wiki_eval.py --root $PK --json | python3 -c "import sys,json;d=json.load(sys.stdin);print('score',d['score'],'dims',d['dims'])"
```

## 完成后报告格式

- 深化模板定义（frontmatter 锚点 + 正文段结构）
- 首批表清单 + 每表深化前后正文差异摘要（新增了哪些字段口径 / 枚举 / 粒度 / 去重结论）
- 新增锚点页数（带 dataworks_ref 的口径页从 8 增到 N）
- review_queue 新增项（待 maintainer 背书清单）
- lint / eval 输出、每表 commit sha、偏离或异常

## Execution log by codex · 2026-07-02

### Step 0 spec-review

复核通过，按调整后的缩版范围执行：不依赖 TASK-037，不碰引擎代码；首批只做模板 + 资产 2 张核心表 + 风控 1 张核心表。knowledge-pk profile 已允许 topic 携带 `dataworks_ref` / `code_fingerprint` / `last_synced`，因此锚点可落在 topic 页。

### 深化模板

- Frontmatter：保留 topic 基础字段，并补 `dataworks_ref`、`code_fingerprint`、`last_synced`。
- 正文固定段：`## 字段字典` / `## 过滤与粒度` / `## join 与去重` / `## 适用边界` / `## caveat`。
- 边界：不复制 DataWorks SQL，不自动 `review:true`，新增 review_queue 背书项。

### 首批表与新增页

1. `pk_data.dwd_asset_loan_list`
   - 新增 `wiki/topics/asset-loan-list-caliber.md`
   - 补充 `listing_id` 粒度、`asset_product`、`is_deal`、`is_calm_period_repay`、成交排序字段、与还款记录和债务期次的 join 边界。
   - commit: `3ee1d5b` (`[pk task-038] deepen dwd_asset_loan_list caliber`)
2. `pk_data.dwd_asset_loan_debt`
   - 新增 `wiki/topics/asset-loan-debt-caliber.md`
   - 补充 `debt_id` 粒度、`listing_id` 关联、`asset_product` 非空过滤、`debt_status`、`overdue_day` 和 DWB 聚合边界。
   - commit: `687d507` (`[pk task-038] deepen dwd_asset_loan_debt caliber`)
3. `pk_data.dwd_risk_merchant_apply_limit_record_dly`
   - 新增 `wiki/topics/risk-merchant-apply-limit-record-caliber.md`
   - 补充 `merchant_id`、`dt`、商户授信申请记录、与额度初始化 / 额度变更链路的使用边界。
   - commit: `0150276` (`[pk task-038] deepen risk merchant limit caliber`)

### 新增锚点页数

- topic 中 `dataworks_ref` 计数从 1 增到 4。
- 新增锚点 topic：3 个。

### review_queue

新增 3 个待 maintainer 背书项：

- `rev_20260702_004`：背书 `dwd_asset_loan_list` 借款标口径深化。
- `rev_20260702_005`：背书 `dwd_asset_loan_debt` 债务期次口径深化。
- `rev_20260702_006`：背书 `dwd_risk_merchant_apply_limit_record_dly` 商户授信额度申请口径深化。

### 验证

```text
grep -l "## 字段字典" ...
asset-loan-debt-caliber.md
asset-loan-list-caliber.md
risk-merchant-apply-limit-record-caliber.md

grep -h "^dataworks_ref:" wiki/topics/*.md | wc -l
4

wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk --check-only
错误: 0 · 警告: 0
lint=0

wiki_graph.py --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk
wiki-graph: 1399 nodes, 1918 edges, 54 communities

wiki_eval.py --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk --json
score 82 dims {'connectivity': 100, 'endorsement': 9, 'freshness': 100, 'integrity': 100}
review_coverage eligible=45 reviewed=4 percent=9
```

### 偏离或异常

- 曾从 knowledge-pk repo 目录直接调用 `scripts/wiki_lint.py`，触发 repo-root 检查并退出 2；随后从引擎 repo 根目录重跑同一 lint，结果 0/0。内容验证以引擎 repo 根目录的成功输出为准。
- 新增未背书 topic 使 endorsement 从 10 降至 9，符合 task 预期，不做突击背书。


## Evaluation by claude · <date>

## Review by codex · 2026-07-02

结论：通过（有非阻塞建议）。

核实结果：

- knowledge-pk 的 `.wiki-profile.json` 当前 `schema_version=2`，已启用 `asset-mapping` extra type；`asset-mapping` optional fields 包含 `dataworks_ref/code_fingerprint/last_synced`。
- 同一 profile 的 `extra_optional_fields.topic` 也包含 `dataworks_ref/code_fingerprint/last_synced`，因此 topic 页可以合法承载 freshness 锚点，不会因未知字段触发 lint error。
- 当前 pk lint 通过，说明 profile 与现有 schema 合并正常。
- 深化模板的段落结构合理，能覆盖字段含义、枚举、过滤、粒度、join/去重、适用边界和 caveat；首批资产借还款 + 风控审核额度也符合已有 source/topic 支撑情况。

非阻塞建议：

- TASK-037 当前需要调整，但不阻塞本 task 对已明确的 DWD/DWB 页面做深化；只要不要依赖未知层归类结果作为唯一输入即可。
- “每表单独 commit”质量较高但执行成本大。若首批表回源复杂，建议先完成模板 + 2 张资产核心表 + 1 张风控核心表作为第一批，剩余表拆后续 task，避免一次 task 过大。
- 深化页新增锚点后仍 `review:false` 是正确选择；review_queue 条目建议按“字段/口径点”聚合，而不是每个字段一条，避免队列噪音。
