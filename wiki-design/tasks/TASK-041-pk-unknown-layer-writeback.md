---
id: task_20260702_041
title: knowledge-pk 索引写回 124 确认层级 + 反查 smoke + routing 收尾
author: claude
executor: codex
status: done
type: other
created: 2026-07-02
updated: 2026-07-02
related_rfcs: [RFC-029]
---

# TASK-041: knowledge-pk 层级写回 + 反查收尾

## 目标

RFC-029 引擎支持就绪后，把 TASK-037 已确认的 unknown 归类**写回 knowledge-pk 索引 `layer`**，跑反查 smoke 验证角色分档正确，收尾 routing topic 措辞与 open-question。承接 TASK-037（只归类未写索引）+ TASK-040（引擎已支持新层级）。

## 前置条件

- **TASK-040 done**（引擎 `reverse` 已支持 DIM/S-*/TMP/DDM/EDW 三档角色）。
- TASK-037 done（`wiki/topics/unknown-layer-classification.md` 归类清单在）。
- knowledge-pk working tree clean；`PY` 同 TASK-040。

## 强约束

1. **只写 TASK-037 已确认项**（detail-candidate 66 / downstream-derived 22 / trace-only 14），**22 待定保留 `unknown`**，不硬判；确认项 `layer` 用 TASK-040 归一大小写（`DIM/S-DWD/S-DWB/S-DIM/TMP/DDM/EDW`）。
2. `layer_source` 改 `manual`；索引仍守受管共享基线（`index_version=2`、1353 items、无 volatile、无代码/凭证）。domain 回填按 TASK-037 清单，判不准留空。
3. **不 auto `review:true`**；层级写回是事实归类，不是口径背书。
4. 写回后必须跑反查 smoke 验证角色，不只改数据。

## 步骤

1. 从 `wiki/topics/unknown-layer-classification.md` 取已确认项（排除 22 待定）。
2. 更新 `.wiki/dataworks_index.json` 对应 item 的 `layer` / `layer_source=manual` / `domain`。
3. 反查 smoke：`dim_merchant_info` / `s_dwd_...` → detail-candidate 推荐；`tmp_asset_repay_dtl` → trace-only「仅溯源」；`ddm_*`/`edw_*` → downstream-derived 默认隐藏、`--include-summary` 才显；歧义样例 → `ambiguous_table_key`。
4. 收尾 3 个 routing topic：把「待 RFC-029」措辞改为「已生效」；`open-questions/unknown-layer-reverse-support.md` 标 `status: archived`，正文记收尾结果（reverse 已支持 + 写回完成；domain 全空缺口若未一并解决则拆出继续跟踪）。
5. lint / graph / eval；commit。

## 验证

```bash
PY="/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python"
PK=/Users/zhangjunwu/workspace/obsidian/knowledge-pk
python3 -c "import json,collections;d=json.load(open('$PK/.wiki/dataworks_index.json'));c=collections.Counter(i['layer'] for i in d['items']);print(dict(c));print('unknown remaining',c['unknown'])"   # 期望 unknown≈22
$PY scripts/wiki_index.py reverse --root $PK --table dim_merchant_info
$PY scripts/wiki_index.py reverse --root $PK --table tmp_asset_repay_dtl
$PY scripts/wiki_lint.py --root $PK --check-only; echo lint=$?
```

## 完成后报告格式

- 写回项数（按角色）+ 保留 unknown 数（应≈22）
- 反查 smoke 输出（各层级角色是否正确、歧义是否 warning）
- routing topic 收尾 + open-question archived 摘要
- 索引仍守基线的确认（version/items/无代码）
- lint / graph / eval、commit sha、偏离或异常

## Execution log by codex · 2026-07-02

### Step 0 / 写回核对

- knowledge-pk working tree clean 后开工。
- 从 `wiki/topics/unknown-layer-classification.md` 解析 124 行，全部唯一匹配 `.wiki/dataworks_index.json` item。
- 写回确认项 102 行：
  - detail-candidate: 66
  - downstream-derived: 22
  - trace-only: 14
- 22 行 `待定 / unknown` 保留 `layer=unknown`。
- 索引不变量：
  - `index_version=2`
  - `items=1353`
  - 未写入 code/content payload

### 索引写回结果

写回后 layer 分布：

```text
DDM 13
DIM 27
DWB 45
DWD 174
DWS 36
EDW 9
ODS 974
S-DIM 5
S-DWB 11
S-DWD 23
TMP 13
unknown 23
```

`layer_source` 分布：

```text
manual 102
name_prefix 1190
output_table 39
unknown 22
```

偏离/说明：

- TASK 期望 unknown 约 22；实际 total unknown=23，其中 22 个是待定项，另 1 个是 Dexin 投影。
- Dexin 投影不在本 task 允许写入的物理 layer 枚举 `DIM/S-DWD/S-DWB/S-DIM/TMP/DDM/EDW` 内，因此保持 `layer=unknown`、`layer_source=manual`，由 RFC-029/TASK-040 的 `pk_dexin.` 机械识别提供 trace-only 角色。

### 反查 smoke

`dim_merchant_info`：

```text
Recommended:
- DIM dim_merchant_info · pk_data.dim_merchant_info · has_knowledge_page · 维表/映射定义层，可作为枚举或映射口径候选。
```

`tmp_asset_repay_dtl`：

```text
Recommended:
- (none)
Matched trace-only:
- TMP tmp_asset_repay_dtl · pk_data.tmp_asset_repay_dtl · 仅溯源，不建议作为取数定义点
Warnings:
- ambiguous_table_key
```

`pk_data.ddm_asset_limit_loan_dtl`：

```text
default: Recommended (none), Summary candidates hidden
--include-summary:
- DDM ddm_asset_limit_loan_dtl · pk_data.ddm_asset_limit_loan_dtl · has_knowledge_page · 集市/下游派生层，默认不作为口径定义点，需 --include-summary 展开。
```

`pk_data.edw_erp_dm_op_internation_cmn_listing`：

```text
default: Recommended (none), Summary candidates hidden
--include-summary:
- EDW edw_erp_dm_op_internation_cmn_listing · pk_data.edw_erp_dm_op_internation_cmn_listing · has_knowledge_page · 报表/下游派生层，默认不作为口径定义点，需 --include-summary 展开。
```

歧义样例 `s_dwd_asset_merchant_apply_snapshot_dly`：

```text
Warnings:
- ambiguous_table_key: 表名无 project 前缀且命中多个候选，请带 project 前缀重查。
```

非阻塞展示瑕疵：

- DDM/EDW `--include-summary` 能正确展开 summary candidate，但同时仍输出旧的“索引中未命中该表” warning。该 warning 来自 reverse 的展示路径，不影响本 task 的索引写回与角色分档结果，后续若要清理应走引擎侧小修。

### 文档收尾

- 3 个 routing topic 已把“待 RFC-029 / 索引仍保持 unknown”改为“RFC-029 已生效 / 确认项已写回 / 待定项保留 unknown”。
- `wiki/open-questions/unknown-layer-reverse-support.md` 已 `status: archived`，并记录 reverse 已支持、写回完成、Dexin 特殊口径和 domain 后续缺口。
- `wiki/topics/unknown-layer-classification.md` 已同步说明 TASK-041 写回完成。

### 验证

```text
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk --check-only
lint=0

/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_graph.py --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk --json
graph=0
nodes 1405 edges 1987 dangling 0 ambiguous 0

/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_eval.py --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk --json
eval=0
score 83
review_coverage eligible=44 reviewed=6 percent=14
```

### Commits

- knowledge-pk: `1129bc2` `[pk task-041] write back unknown layer classifications`

## Evaluation by claude · 2026-07-02

**Verdict: PASS。** 独立复验（读 knowledge-pk 索引 + 实跑反查）：

- 索引写回：`index_version=2` / `items=1353` / 无代码正文；layer 分布与报告一致（DIM 27 / S-DWD 23 / S-DWB 11 / S-DIM 5 / DDM 13 / EDW 9 / TMP 13，unknown 23）；`layer_source` manual 102。
- `unknown=23` 而非 22：多的 1 个是 Dexin 投影——不在允许写入的物理 layer 枚举内，保持 `layer=unknown` 由 `pk_dexin.` 机械识别为 trace-only。判断正确、诚实标注，没硬塞非法枚举。
- **反查 payoff 端到端验证**（整条链的意义）：`dim_merchant_info` → Recommended **DIM**「可作枚举/映射口径候选」（041 前无候选）；`pk_data.tmp_asset_repay_dtl` → Recommended (none) + **Matched trace-only**「仅溯源，不建议取数」+ 下游 DWB 作候选。DDM/EDW 默认隐藏、`--include-summary` 展开；无前缀歧义 → `ambiguous_table_key`。
- lint 0 / graph 0（1405 nodes / 1987 edges，dangling 0 / ambiguous 0）/ eval 83；`open-questions/unknown-layer-reverse-support.md` 已 archived；3 个 routing topic 收尾。

非阻塞瑕疵（Codex 诚实记录）：DDM/EDW `--include-summary` 展开时仍带旧「索引中未命中该表」warning，属 reverse 展示路径旧逻辑，不影响写回与分档，后续引擎侧小修可清。

**RFC-029 全链闭合**：accept → apply（TASK-040）→ 写回（TASK-041），124 个原 unknown 任务现按物理层级角色正确路由。commit `1129bc2`。

