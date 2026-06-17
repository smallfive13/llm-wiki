---
id: task_20260616_026
title: Apply RFC-025 — endorsement 复核覆盖修正 + 未背书清单 + 巡检/复核手册
author: claude
executor: codex
status: pending
type: apply
created: 2026-06-16
updated: 2026-06-16
related_rfcs: [RFC-025]
---

# TASK-026: Apply RFC-025

## 目标

M1 `wiki_eval` 的 endorsement 从"high 页背书率"改为"应背书页复核覆盖率"（消除 0-high 假绿）+ M2 graph-insights/eval-json 加未背书清单 + M3 巡检与复核手册进 `02-workflows.md`。

## 前置条件

- RFC-025 status: accepted（Decision by claude 2026-06-16，含已采纳 codex 建议）。
- 引擎 working tree clean（除本 task）。
- 环境：`/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python`（完整命令）。

## 强约束

1. **endorsement 新语义**（`scripts/wiki_eval.py` 的 `_endorsement_score()`，codex 已定位）：
   - eligible（应背书页）= `status == active` 且 `type ∉ {source, query}`。
   - endorsement = `review:true 的 eligible 数 / eligible 数 × 100`。
   - eligible == 0（纯 source/query 库 / 空库）→ **100**（不假惩罚、不除零）；eligible > 0 且 reviewed == 0 → **0**（消除假绿）。
   - high 页是 eligible 子集，自然计入；不再以 high 为分母。
2. **`wiki_eval --json` 新增字段（钉死）**：`review_coverage: {eligible:int, reviewed:int, percent:int, unreviewed: [{id, type, in_degree, out_degree}]}`；`unreviewed` 按 `in_degree desc, out_degree desc, id` 排序。普通（非 json）输出也显示 `reviewed-eligible x/y`。
3. **M2 graph-insights**（`scripts/wiki_graph.py` 的 `render_health()`）：「知识健康度」段新增「未背书应背书页」清单（active、type∉{source,query}、review:false，同上排序），概览行显示 `reviewed-eligible x/y`；现有 `high-unverified` 保留为高优先子集（不删不重复）。
4. **不 bump `schema_version`**（派生度量算法变更，不动 frontmatter/JSON 契约/core enum）；README/snapshot 标注「RFC-025 起 endorsement 语义变更、`eval_history.jsonl` 历史值不可直接比」。
5. **不改**：frontmatter/JSON 契约、core enum、STALE 阈值、`schema_version`、实例知识数据；datawarehouse 不去突击背书（score 下降是预期）。

## 步骤

> **Step 0 spec-review**：核对 `wiki_eval.py` `_endorsement_score()` / `calculate_health()` / `--json` 组装、`wiki_graph.py` `render_health()` 的 high_unverified 渲染与排序口径、RFC-014 既有 endorsement 测试位置。确认 graph 节点已带 in_degree/out_degree（codex 已核：有）。歧义先提。

1. **`scripts/wiki_eval.py`**：`_endorsement_score()` 改 eligible 语义 + 边界；`calculate_health()`/JSON 组装加 `review_coverage` 字段；非 json 输出加 `reviewed-eligible x/y`。
2. **`scripts/wiki_graph.py`**：`render_health()` 加「未背书应背书页」清单 + 概览 `reviewed-eligible x/y`；high-unverified 保留。
3. **`scripts/README.md`**：endorsement 新语义 + `review_coverage` JSON 字段 + snapshot 断点说明。
4. **`knowledge/.wiki-schema.md`**：「review 与可信度派生信号」段更新 endorsement 描述（散文，非 generated block；改完 `--check-docs` 仍 exit 0）。
5. **`wiki-design/02-workflows.md`**：新增「知识巡检与复核」节——周巡检动作（lint/graph/eval/review_queue/高频页）、盲区警示（新库 staleness 空跑、别只看 score 要看未背书清单）、过时处置四态、入库复核三档分级、`review:true = 人背书` 定调。
6. **测试 `tests/test_task_026.py`** + 更新 RFC-014 endorsement 断言：
   - 全 review:false eligible → endorsement 0；半数 → 50；纯 source/query（eligible 0）→ 100；空库不崩；high 计入分母分子。
   - `--json` 有 `review_coverage`，`unreviewed` 排序正确。
   - graph-insights 未背书清单筛选/排序正确、high-unverified 仍单列。
7. 跑验证 → 引擎一个 commit → push GitLab。

## 验证

```bash
cd /Users/zhangjunwu/workspace/llm-wiki/llm-wiki
DW=/Users/zhangjunwu/workspace/obsidian/datawarehouse
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest -v tests.test_task_026
# datawarehouse smoke：endorsement→0、score 100→~80、review_coverage eligible=13 reviewed=0
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_eval.py --root "$DW" --json | python3 -c "import json,sys;d=json.load(sys.stdin);print('score',d['score'],'endorsement',d['dims']['endorsement']);print('review_coverage',d.get('review_coverage'))"
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_graph.py --root "$DW" >/dev/null 2>&1 && grep -A6 '未背书' "$DW/maps/graph-insights.md" | head
# knowledge check-docs 不破 + 引擎自检
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root knowledge --check-docs; echo "check-docs=$?"
# 回归（含 RFC-014 endorsement 更新）
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest discover -s tests
```

## 完成后报告格式

- Step 0 结论（_endorsement_score / render_health 落点）
- 改动文件 + 关键位置（eligible 语义、review_coverage 字段、未背书清单渲染、02 节、.wiki-schema 描述）
- 验证输出（fixture 各场景、datawarehouse endorsement/score/review_coverage smoke、未背书清单、check-docs、全量回归）
- commit sha + push 记录
- 偏离或异常

## Execution log by codex · <date>

（执行者填写）

## Evaluation by claude · <date>

（评估者填写）
