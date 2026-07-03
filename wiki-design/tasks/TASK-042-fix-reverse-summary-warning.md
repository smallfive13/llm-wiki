---
id: task_20260702_042
title: 修 reverse --include-summary 对 DDM/EDW 的残留「未命中该表」warning（引擎小修）
author: claude
executor: codex
status: done
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

## Execution log by codex · 2026-07-03

### 根因与修法

- 根因：`build_reverse_report()` 的 warning 判据只检查 `upstream` / `downstream`，没有把 `summary_candidates` 和 `matched_trace_only` 计入“已命中”。因此 DDM/EDW 在 `--include-summary` 已正确展开 summary candidate 时，仍会走到“索引中未命中该表” warning。
- 修法：新增 `has_any_match = bool(upstream or downstream or summary or trace_only)`，只有没有任何命中时才输出“索引中未命中该表”。
- 未改 `LAYER_ROLE`、推荐排序、summary 隐藏/展开逻辑、trace-only 逻辑。

### 验证

真实 knowledge-pk DDM smoke：

```text
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_index.py reverse --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk --table pk_data.ddm_asset_limit_loan_dtl --include-summary

Recommended
-----------
- [unknown] DDM ddm_asset_limit_loan_dtl · pk_data.ddm_asset_limit_loan_dtl · has_knowledge_page · 集市/下游派生层，默认不作为口径定义点，需 --include-summary 展开。

Summary candidates
------------------
- [unknown] DDM ddm_asset_limit_loan_dtl · pk_data.ddm_asset_limit_loan_dtl · has_knowledge_page · 集市/下游派生层，默认不作为口径定义点，需 --include-summary 展开。
```

该输出不再包含“索引中未命中该表” warning。

测试：

```text
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest tests.test_task_042 tests.test_task_040
Ran 11 tests in 0.042s
OK

/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest discover -s tests
Ran 158 tests in 94.670s
OK (skipped=1)
```

### Commits

- engine: `d5c24fc` `[task-042] fix reverse summary warning`

## Evaluation by claude · 2026-07-03

**Verdict: PASS。** 独立复验：DDM `--include-summary` 真实 smoke 输出已无「索引中未命中该表」warning；`test_task_042 + test_task_040` 共 11 OK、全量 158 OK；修法（`has_any_match` 计入 summary/trace_only 命中）范围最小，未动 LAYER_ROLE / 推荐 / 隐藏逻辑。真正无命中的表仍会报 warning（fixture 覆盖），warning 逻辑没改死。

一处记录出入：Execution log 写 engine commit `d5c24fc`，实际落库为 `b4f6125`（应为 amend 后 sha 未回填），以 git 为准，不影响结论。

