---
id: task_20260702_040
title: Apply RFC-029 — 反查物理层级扩展 + 推荐角色分档（引擎侧）
author: claude
executor: codex
status: pending
type: apply
created: 2026-07-02
updated: 2026-07-02
related_rfcs: [RFC-029]
---

# TASK-040: Apply RFC-029 引擎侧

## 目标

把 RFC-029 落到引擎：`wiki_index.py reverse` 支持物理层级 `DIM / S-DWD / S-DWB / S-DIM / TMP / DDM / EDW` 并按 `detail-candidate / downstream-derived / trace-only` 三档分档；补无 project 前缀命中 + 歧义规则、Dexin 机械识别、trace-only 精确命中输出。**不动 knowledge-pk 索引内容**（层级写回是 TASK-041）。

## 前置条件

- **RFC-029 status = accepted**（未 accepted 不得开工）。
- 引擎 working tree clean；`PY="/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python"`。

## 强约束

1. **兼容性头等**：`DWD/DWB/DWS/ADS/ODS/unknown` 反查输出与改动前**逐字节一致**（保留 `DETAIL_LAYERS`/`SUMMARY_LAYERS` 兼容 wrapper 从 `LAYER_ROLE` 派生并断言）；`reverse` 仍只读本地索引不联网；`wiki_lint/graph/eval` 离线零依赖断言不变。
2. **三档角色**：`LAYER_ROLE` 声明表——`detail-candidate`（DWD/DWB/DIM/S-DWD/S-DWB/S-DIM，默认推荐）、`downstream-derived`（DWS/ADS/DDM/EDW，`--include-summary` 才显）、`trace-only`（ODS/TMP/Dexin，仅溯源）。`LAYER_ORDER` 补新层级。
3. **归一化 + 歧义**：无前缀 `dim_/s_dwd_/s_dwb_/s_dim_/tmp_/ddm_/edw_` 表名在有/无 `pk_data.`、`pk_dexin.` 前缀时命中同一 item；**只在唯一命中时 resolve**，多候选同 basename → `ambiguous_table_key` warning、不推荐、提示带前缀重查。大小写统一归一后再查 `LAYER_ROLE`。
4. **Dexin 机械识别**：`table`/`node_name`/`outputs` 任一以 `pk_dexin.` 或 `pk_data.pk_dexin.` 开头 → `trace-only`。
5. **trace-only 精确命中输出**：查询正是某 trace-only 表时，CLI 显式输出「matched trace-only item · 仅溯源，不建议作为取数定义点」，不进 Recommended。
6. 不 bump schema_version（除非 RFC-029 明确要求）；不改其它库行为。

## 步骤

1. `scripts/wiki_index.py`：`LAYER_ROLE` 表 + `LAYER_ORDER` + `normalize_table_key` 前缀/歧义 + Dexin 识别 + `reverse` 三档输出 + trace-only 命中输出；`DETAIL_LAYERS`/`SUMMARY_LAYERS` 改为从 `LAYER_ROLE` 派生的兼容 wrapper。
2. `tests/test_task_040.py`：三档分档 fixture、归一化 fixture、歧义 fixture（多 project 同 basename）、trace-only 输出 fixture、六层回归逐字节断言、进程级离线隔离断言。
3. `wiki-design/02-workflows.md`「DataWorks 表名反查路由」段 + `scripts/README.md`：补物理层级 → 角色 + 歧义 + trace-only 输出说明。
4. 引擎一个 commit；RFC-029 末尾登记 `## Applied in <sha>`。

## 验证

```bash
PY="/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python"
cd /Users/zhangjunwu/workspace/llm-wiki/llm-wiki
$PY -c "import sys; sys.path.insert(0,'scripts'); import wiki_lint,wiki_graph,wiki_eval; print('泄漏:', [m for m in sys.modules if any(k in m.lower() for k in ('dataworks','alibabacloud','sqlglot'))] or '无')"
$PY -m unittest -v tests.test_task_040 2>&1 | tail -3
$PY -m unittest discover -s tests 2>&1 | tail -2
# 现有六层回归：改动前后 reverse 输出 diff 应为空（DWD/DWB/DWS/ADS/ODS/unknown）
```

## 完成后报告格式

- 改动位置（LAYER_ROLE / 归一化+歧义 / Dexin 识别 / trace-only 输出 / 兼容 wrapper）
- 六层逐字节回归结果、离线隔离断言、test_040、全量回归
- commit sha + RFC-029 `Applied in`
- 偏离或异常

## Execution log by codex · <date>

## Evaluation by claude · <date>
