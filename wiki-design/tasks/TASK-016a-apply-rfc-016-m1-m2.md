---
id: task_20260604_016a
title: Apply RFC-016 M1+M2 — visibility 分级 + 脱敏分级 + capture_policy 迁移
author: claude
executor: codex
status: done
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

## Execution log by codex · 2026-06-04

### Step 0 spec-review 结论

通过，可以执行。

- 现有 `BASE_SCHEMA.json_contracts.capture_policy.required_fields` 硬要求 `exclude_patterns`，`wiki_lint.validate_json_contracts()` 也硬校验该字段；直接改成 v2 会打断现有 v1 实例。
- 采用兼容实现：`exclude_patterns` 从 required 降为 legacy optional，v1 policy 被归一为 `soft_redact` legacy alias，并产生 `CAPTURE_POLICY_LEGACY` warning；v2 policy 不需要 `exclude_patterns`。
- `hard_redact` 缺失时从 `BASE_SCHEMA` 内置默认读取，保证旧 policy 不会失去密钥/凭证硬底线扫描。
- `visibility` 可作为 `core_enums.visibility` 加入，但不进入 `core_required_fields`；页面/source 缺失时只内部计算 effective visibility，不写回文件。

### 改动文件 + 关键位置

- `scripts/wiki_common.py`：新增 `visibility` enum；扩展 `capture_policy` v2 契约；保留 `exclude_patterns` legacy；注册 `CAPTURE_POLICY_LEGACY` / `SOFT_REDACT_HIT` / `HARD_REDACT_HIT`。
- `scripts/wiki_lint.py`：新增 visibility 校验；新增 capture_policy v1/v2 归一化；hard 命中为 error、soft/legacy 为 warning；source_manifest visibility enum 校验。
- `scripts/wiki_init.py`：新实例 `capture_policy.json` 模板改为 v2。
- `knowledge/.wiki/capture_policy.json`：engine 样板迁移为 v2，`default_visibility: internal`。选择 internal 的理由：engine 样板是系统/团队协作样板，不是个人私密库。
- `knowledge/.wiki-schema.md` / `scripts/README.md` / `wiki-design/02-workflows.md`：同步 visibility、脱敏分级、legacy 兼容和 error code 文档。
- `tests/test_task_016a.py`：新增 v1/v2 policy、visibility、hard/soft/public warning fixture。

### 验证输出

```text
=== tests.test_task_016a ===
test_hard_redact_is_error ... ok
test_public_wiki_page_soft_redact_warning ... ok
test_v1_capture_policy_is_legacy_warning_not_error ... ok
test_v2_capture_policy_has_no_legacy_warning ... ok
test_visibility_optional_and_invalid_values_error ... ok

Ran 5 tests in 0.887s
OK
```

```text
=== engine lint ===
扫描: knowledge/wiki/ (4 文件) · knowledge/inbox/ (0 draft) · knowledge/raw/ (0 source)
错误: 0 · 警告: 0
engine exit=0

=== personal lint ===
扫描: personal/wiki/ (10 文件) · personal/inbox/ (0 draft) · personal/raw/ (0 source)
错误: 0 · 警告: 0
personal exit=0

=== datawarehouse lint ===
扫描: datawarehouse/wiki/ (30 文件) · datawarehouse/inbox/ (0 draft) · datawarehouse/raw/ (18 source)
错误: 0 · 警告: 0
dw exit=0
```

```text
=== regression tests 012-015 ===
Ran 27 tests in 4.328s
OK
```

### 迁移：三库 capture_policy v2

- engine `knowledge/.wiki/capture_policy.json`：v2；`default_visibility: internal`；soft 默认保留。
- personal `/Users/zhangjunwu/workspace/obsidian/knowledge/personal/.wiki/capture_policy.json`：v2；`default_visibility: private`；soft 默认保留。
- datawarehouse `/Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse/.wiki/capture_policy.json`：v2；`default_visibility: internal`；`soft_redact.patterns: []`，只留硬底线。
- 迁移后三库 lint 均为 `错误: 0 · 警告: 0`，无 `CAPTURE_POLICY_LEGACY`。

数据仓迁移前状态：clean，HEAD `71b372549ac34e447bdcfd01646789882b5522a4`。  
数据仓迁移 commit：`129c612c113e2e41ba1b82192f547e0a3fe31b66` (`[capture policy] migrate personal and datawarehouse to v2`)。  
数据仓迁移后状态：clean。

### Commit sha

- 引擎 apply commit：`8a2d0d84ced1a574dc41e65211a5f99d416331c4`
- 数据仓迁移 commit：`129c612c113e2e41ba1b82192f547e0a3fe31b66`

### 偏离或异常

- 第一次最终验证命令使用 `PY="/Users/.../conda run -n py312 python"` 后直接 `$PY ...`，zsh 不做 word splitting，导致 `exit 127`。已按 TASK 既有经验改为直接展开 `/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python ...` 重跑，全部验证通过。

## Evaluation by claude · <date>

（评估者填写）
