---
id: task_20260702_040
title: Apply RFC-029 — 反查物理层级扩展 + 推荐角色分档（引擎侧）
author: claude
executor: codex
status: done
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

## Execution log by codex · 2026-07-02

### Step 0 spec-review

确认 RFC-029 已 accepted，Decision 已登记。现有 `wiki_index.py` 反查核心落点为 `normalize_table_key` / `item_keys` / `build_reverse_report` / `render_reverse`，旧 `DETAIL_LAYERS={DWD,DWB}` 与 `SUMMARY_LAYERS={DWS,ADS}` 是兼容重点。

### 改动位置

- `scripts/wiki_index.py`
  - 新增 `LAYER_ROLE`：`detail-candidate` / `downstream-derived` / `trace-only` 三档角色。
  - `DETAIL_LAYERS` / `SUMMARY_LAYERS` 保留为兼容 wrapper，并断言仍等于旧值 `{'DWD','DWB'}` / `{'DWS','ADS'}`。
  - `infer_layer` 支持 `DIM / S-DWD / S-DWB / S-DIM / TMP / DDM / EDW`。
  - 新增 `normalize_layer` / `layer_role` / `is_dexin_projection` / `item_role`。
  - 无 project 前缀查询先按 basename 候选数判断：唯一命中才 resolve，多候选输出 `ambiguous_table_key`，不推荐。
  - Dexin 通过 `table` / `node_name` / `outputs` 的 `pk_dexin.` 或 `pk_data.pk_dexin.` 前缀机械识别为 `trace-only`。
  - TMP / Dexin 精确命中输出 `Matched trace-only`，并标注「仅溯源，不建议作为取数定义点」；ODS 旧输出保持不变以满足兼容性。
- `tests/test_task_040.py`
  - 覆盖三档分档、无前缀唯一命中、无前缀歧义、node_name 合成输出命中、Dexin 机械识别、trace-only 精确命中 suppress downstream recommendation、旧六层逐字节回归、离线隔离。
- `wiki-design/02-workflows.md` / `scripts/README.md`
  - 补物理层级三档角色、`--include-summary`、`ambiguous_table_key`、Dexin trace-only 与 trace-only 输出说明。

### 兼容 / 回归

- 旧六层渲染在 `tests.test_task_040.test_legacy_six_layer_rendering_is_byte_compatible` 中逐字节断言。
- `tests.test_task_032` / `tests.test_task_033` 旧反查回归通过。
- `wiki_lint` / `wiki_graph` / `wiki_eval` 离线隔离断言通过：`泄漏: 无`。

### 验证输出

```text
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -c "import sys; sys.path.insert(0,'scripts'); import wiki_lint,wiki_graph,wiki_eval; print('泄漏:', [m for m in sys.modules if any(k in m.lower() for k in ('dataworks','alibabacloud','sqlglot'))] or '无')"
泄漏: 无

/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest -v tests.test_task_040
Ran 9 tests in 0.046s
OK

/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest discover -s tests
Ran 156 tests in 84.553s
OK (skipped=1)
```

### Real instance smoke

在当前 knowledge-pk 索引尚未执行 TASK-041 写回 124 项层级前，真实 smoke 仍受现有索引内容限制：

- `dim_merchant_info` 可归一到 `pk_data.dim_merchant_info`，但当前索引 item 输出为合成表名且 layer 仍未写回，因此暂无候选；TASK-041 写回后会进入 DIM 角色。
- `s_dwd_asset_merchant_apply_snapshot_dly` 当前同 basename 多候选，输出 `ambiguous_table_key`，符合 RFC-029 歧义规则。
- `pk_data.tmp_asset_repay_dtl` 当前索引 layer 仍未写回 TMP，因此仍表现为旧 DWB 下游推荐；TASK-041 写回 TMP 后会触发 trace-only 精确命中。

### Commits

- Apply commit: `4c3bf92` (`[apply rfc-029] add physical layer reverse roles`)
- RFC Applied commit: `d8797b3` (`[rfc-029] mark applied by codex`)

### 偏离或异常

- 首次验证命令把完整 conda 命令放入 shell 变量，zsh 按整串路径执行失败；已按要求改为每条命令直接写完整 `/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python ...` 后重跑通过。
- 为满足“旧 ODS 反查输出逐字节不变”，trace-only 精确命中提示只对新增 trace-only 类型（TMP / Dexin）触发；ODS 保持旧渲染。


## Evaluation by claude · 2026-07-02

**Verdict: PASS。** 独立复验（重跑 + 读码，非橡皮图章）：

- 离线不变量：`泄漏: 无`（`wiki_lint/graph/eval` 未引入 dataworks/sqlglot/alibabacloud）。
- 测试：`test_task_040`(9) + 旧反查回归 `032/033` 共 26 OK；Codex 报全量 156 OK(skipped 1)。
- **兼容头等真守住**：`DETAIL_LAYERS/SUMMARY_LAYERS` 从 `LAYER_ROLE` 派生 + `assert == {"DWD","DWB"}` / `{"DWS","ADS"}`（`wiki_index.py:50-53`），六层逐字节回归非空壳。
- `LAYER_ROLE` 映射与 RFC-029 §1 逐条一致（ODS/TMP=trace-only、DWD/DWB/DIM/S-*=detail-candidate、DWS/ADS/DDM/EDW=downstream-derived）。
- `is_dexin_projection`（`wiki_index.py:315`）按 `pk_dexin.` / `pk_data.pk_dexin.` 前缀机械识别、`item_role` 让 Dexin 覆盖为 trace-only——与 RFC §3 判据一致、fixture 同源。三点阻塞（歧义 / Dexin / trace-only 输出）都落测。

边界正确：真实 knowledge-pk 里 DIM/TMP 仍表现旧行为（索引 layer 未写回，属 TASK-041 范围），Codex 诚实标注、未越界。TASK-040 锁死引擎能力 + fixture，done 有效（apply `4c3bf92` / RFC applied `d8797b3` / task `1d41049`）。RFC-029 三步走完两步：accept → **apply done** → 待 TASK-041 写回。

