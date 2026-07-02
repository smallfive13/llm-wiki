---
id: task_20260702_041
title: knowledge-pk 索引写回 124 确认层级 + 反查 smoke + routing 收尾
author: claude
executor: codex
status: pending
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

## Execution log by codex · <date>

## Evaluation by claude · <date>
