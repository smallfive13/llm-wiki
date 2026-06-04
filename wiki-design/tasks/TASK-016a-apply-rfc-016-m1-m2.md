---
id: task_20260604_016a
title: Apply RFC-016 M1+M2 — visibility 分级 + 脱敏分级 + capture_policy 迁移
author: claude
executor: codex
status: pending
type: apply
created: 2026-06-04
updated: 2026-06-04
related_rfcs: [RFC-016]
---

# TASK-016a: Apply RFC-016 M1+M2 — visibility + 脱敏分级

## 目标

落地 RFC-016 的 M1（`visibility` core optional 字段 + 继承）和 M2（脱敏分级 hard/soft + `capture_policy` v2 契约 + `exclude_patterns` legacy 兼容），并迁移 engine/personal/datawarehouse 三库的 `capture_policy`。纯工具 + 配置，不动富媒体（M3 在 016b）。

## 前置条件

- RFC-016 status: accepted（Decision by claude 2026-06-04）。
- working tree clean（除本 task）。
- 环境：`conda run -n py312 python`。

## 强约束

1. **兼容优先**：lint 必须**同时接受 v1（`exclude_patterns`）和 v2（`hard_redact`/`soft_redact`）** capture_policy；v1 视为 `soft_redact` legacy alias + `CAPTURE_POLICY_LEGACY` warning。不得让现有库直接报 error。
2. **visibility 是 core optional**：不进 `core_required_fields`；缺失不报错、lint **不补字段**；仅出现时校验 enum。
3. 不改 lint 退出码语义（enum 非法 = error；legacy/软项 = warning）；不动 graph/eval。
4. **外部实例迁移单独提交**：personal/datawarehouse 的 capture_policy 迁移在数据仓提交，engine 实例的在引擎仓。

## 步骤

> Step 0 spec-review：核对现有 `capture_policy` 校验（`wiki_common` 的 json_contracts + `wiki_lint` 的 capture_policy 校验段），确认 legacy alias 能在不破坏 v1 的前提下加 v2；发现歧义先提。

1. **`wiki_common.py`**：
   - BASE_SCHEMA `core_enums` 加 `visibility: [public, internal, private]`（**不**加进 `core_required_fields`）。
   - `capture_policy` 契约：新增 `default_visibility`（enum，缺省 `private`）、`hard_redact`（对象/数组，缺省用内置硬底线默认：token/AKSK/password/密钥/连接串/私钥正则）、`soft_redact`；**保留 `exclude_patterns` 合法**（legacy）。
   - `error_level` 加 `CAPTURE_POLICY_LEGACY: warning`、`VISIBILITY_INVALID`(error，或复用 ENUM)。

2. **`wiki_lint.py`**：
   - 页面 + source_manifest：`visibility` 出现时校验 enum（非法 error），缺失继承 effective（页/source → 库 `default_visibility` → `private`），**不写回文件**。
   - capture_policy：v1 `exclude_patterns` 存在 → `CAPTURE_POLICY_LEGACY` warning + 当作 soft_redact；v2 字段校验类型；`hard_redact` 命中（inbox/PII 扫描）= error；soft 命中 = warning（`visibility:public` 页/source 升 warning，已是 warning 则保持）。
   - 硬底线缺失用内置默认（保证密钥永远扫）。

3. **`wiki_init.py`**：新库 `capture_policy` 模板写 v2（`default_visibility` + `hard_redact` 默认 + `soft_redact` 默认）。不动既有实例（迁移在步骤 5）。

4. **文档**：`scripts/README.md`（visibility + 脱敏分级 + legacy 兼容 + error code）；`knowledge/.wiki-schema.md`（补 visibility / 脱敏分级，`--sync-schema` 同步留 016c 或本 task 末尾）；`wiki-design/02-workflows.md`（脱敏分级流程）。

5. **迁移三库 capture_policy 到 v2**（engine 在引擎仓 commit；personal/datawarehouse 在数据仓单独 commit）：
   - engine `knowledge/`：v2 结构，`default_visibility: internal`（引擎样板）或 `private`（择一，记录理由）。
   - personal：`default_visibility: private`，soft 保持默认。
   - datawarehouse：`default_visibility: internal`，**soft_redact 清空**（只留硬底线）。
   - 迁移前后跑三库 lint：迁移后应无 `CAPTURE_POLICY_LEGACY`（已是 v2）、无新 error。

6. **测试**（unittest）：v1 capture_policy → `CAPTURE_POLICY_LEGACY` warning 不报 error；v2 校验；`visibility` enum（合法/非法/缺失继承）；硬底线 error；软项 warning；`visibility:public` 软项升级。

7. 跑验证 → commit（引擎改动一个 commit；数据仓迁移单独 commit）。

## 验证

```bash
ENGINE=/Users/zhangjunwu/workspace/llm-wiki/llm-wiki
PY="/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python"
P=/Users/zhangjunwu/workspace/obsidian/knowledge/personal
DW=/Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse

cd $ENGINE && $PY -m unittest -v tests.test_task_016a
# 迁移后三库 lint：0 error，无 CAPTURE_POLICY_LEGACY
$PY scripts/wiki_lint.py --root knowledge --check-only; echo "engine exit=$?"
$PY scripts/wiki_lint.py --root $P --check-only; echo "personal exit=$?"
$PY scripts/wiki_lint.py --root $DW --check-only; echo "dw exit=$?"
# 回归
$PY -m unittest -v tests.test_task_012 tests.test_task_013 tests.test_task_014 tests.test_task_015
```

## 完成后报告格式

- Step 0 spec-review 结论
- 改动文件 + 关键位置
- 验证输出（三库 lint、回归、fixture）
- 迁移：三库 capture_policy v2 diff + 数据仓 commit sha
- commit sha（引擎 / 数据仓分开）
- 偏离或异常

## Execution log by codex · <date>

（执行者填写）

## Evaluation by claude · <date>

（评估者填写）
