---
id: task_20260702_042
title: 修 reverse --include-summary 对 DDM/EDW 的残留「未命中该表」warning（引擎小修）
author: claude
executor: codex
status: pending
type: other
created: 2026-07-02
updated: 2026-07-02
related_rfcs: [RFC-029]
---

# TASK-042: 修 reverse --include-summary 残留 warning

## 目标

`wiki_index.py reverse --include-summary` 对 downstream-derived（DDM/EDW）表能正确展开 summary candidate，但**同时仍输出旧的「索引中未命中该表」warning**（TASK-041 Execution log 记录的非阻塞瑕疵）。本 task 只清这个误报 warning，不动角色分档 / 推荐结果。

## 前置条件

- TASK-040 done（三档角色反查在）。引擎 working tree clean。
- `PY="/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python"`（每条命令写全路径，勿放 shell 变量——见 TASK-040 偏离）。

## 强约束

1. **只修展示路径的 warning 触发条件**：当查询命中了 summary/downstream candidate（`--include-summary` 展开）时，不应再报「未命中该表」。不改 `LAYER_ROLE`、不改推荐/隐藏逻辑、不改 trace-only 输出。
2. 兼容头等：DWD/DWB/DWS/ADS/ODS/unknown + 新层级反查输出除该 warning 外逐字节不变；离线零依赖断言不变。
3. 补 fixture 断言：`--include-summary` 展开 DDM/EDW candidate 时 warning 列表**不含**「未命中」误报；真正无命中的表仍应报 warning（不要把 warning 逻辑改死）。

## 步骤

1. 定位 `reverse` 渲染里「未命中该表」warning 的触发点，判断为什么在有 summary candidate 时仍触发（很可能是 warning 判据只看 Recommended 非空、没算 summary candidate）。
2. 修正判据：命中任一 candidate（含 summary/downstream）即不算「未命中」。
3. `tests/test_task_042.py`（或扩 test_task_040）：DDM/EDW `--include-summary` 无误报 warning；完全无命中表仍报 warning；六层回归不变。
4. 引擎一个 commit。

## 验证

```bash
PK=/Users/zhangjunwu/workspace/obsidian/knowledge-pk
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_index.py reverse --root $PK --table pk_data.ddm_asset_limit_loan_dtl --include-summary   # 期望展开 DDM candidate，无「未命中」warning
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest tests.test_task_042 tests.test_task_040 2>&1 | tail -3
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest discover -s tests 2>&1 | tail -2
```

## 完成后报告格式

- warning 误报根因 + 修法
- DDM/EDW --include-summary 修前/修后 warning 对比
- test_042 + 六层回归 + 全量、commit sha、偏离或异常

## Execution log by codex · <date>

## Evaluation by claude · <date>
