---
id: task_20260604_017
title: Apply RFC-017 — source_manifest.status 加 superseded/archived + datawarehouse 修正
author: claude
executor: codex
status: pending
type: apply
created: 2026-06-04
updated: 2026-06-04
related_rfcs: [RFC-017]
---

# TASK-017: Apply RFC-017 — source_manifest.status enum 扩展

## 目标

`source_manifest.statuses` 只增不改地加 `superseded` / `archived`，同步三处 schema 文档，并把 datawarehouse 旧集合 source 的 `deleted` 回正为 `superseded`。

## 前置条件

- RFC-017 status: accepted（Decision by claude 2026-06-04）。
- working tree clean（除本 task）。
- 环境：`conda run -n py312 python`。

## 强约束

1. **只增不改**：`source_manifest.statuses` 既有 6 值（new/triaged/ingested/skipped/failed/deleted）不动，只加 2 个。
2. 不改 lint 逻辑（读 enum 自动接受）、不改退出码、不动 graph/eval。
3. **datawarehouse 数据修正在数据仓单独提交**，不混引擎 apply commit。

## 步骤

> Step 0 spec-review：确认 `wiki_common` 的 source_manifest statuses 来源 + `wiki_lint` 的 SOURCE_STATUSES 构造，确认加值即自动接受；发现歧义先提。

1. **`scripts/wiki_common.py`**：`BASE_SCHEMA.json_contracts.source_manifest.statuses` 加 `superseded`、`archived`。

2. **同步三处 schema 文档**（契约一致）：
   - `wiki-design/05-contracts-and-next-steps.md`：Source Manifest Schema 的 status enum 加 `superseded`/`archived`（契约正本）。
   - `knowledge/.wiki-schema.md`：source_manifest status enum 同步（之后 `--sync-schema` 到各实例）。
   - `scripts/README.md`：source_manifest status enum 一行简述补两值。

3. **测试**（unittest）：manifest 用 `superseded` / `archived` → 合法不报错；非法值（如 `bogus`）仍 error；既有 6 值不回归。

4. **引擎验证 + commit**（引擎一个 commit）：跑三库 lint（现有 manifest 不含新值，应不变）+ fixture + 回归 012-016。

5. **datawarehouse 数据修正**（数据仓单独 commit）：
   - `raw/source_manifest.json` 旧集合 source 条目 `status: deleted` → `superseded`（notes 保留/更新审计说明）。
   - 跑 `wiki_lint --root datawarehouse` exit 0。
   - 各库 `--sync-schema` 同步 `.wiki-schema.md`（含本次 enum 更新）。

## 验证

```bash
ENGINE=/Users/zhangjunwu/workspace/llm-wiki/llm-wiki
PY="/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python"
DW=/Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse

cd $ENGINE && $PY -m unittest -v tests.test_task_017
# 05 / .wiki-schema / README 同步确认
grep -c 'superseded' wiki-design/05-contracts-and-next-steps.md knowledge/.wiki-schema.md scripts/README.md
# 三库 lint 不回归
$PY scripts/wiki_lint.py --root knowledge --check-only; echo "engine exit=$?"
# datawarehouse 修正后
$PY scripts/wiki_lint.py --root $DW --check-only; echo "dw exit=$?"
grep -E '"status"' $DW/raw/source_manifest.json   # 旧集合应为 superseded
# 回归
$PY -m unittest -v tests.test_task_012 tests.test_task_013 tests.test_task_014 tests.test_task_015 tests.test_task_016a tests.test_task_016b
```

## 完成后报告格式

- Step 0 spec-review 结论
- 改动文件 + 关键位置（enum + 三处文档同步点）
- 验证输出（fixture、三处 grep、三库 lint、回归）
- datawarehouse 修正：source_manifest diff + 数据仓 commit sha + `--sync-schema` 结果
- commit sha（引擎 / 数据仓分开）
- 偏离或异常

## Execution log by codex · <date>

（执行者填写）

## Evaluation by claude · <date>

（评估者填写）
