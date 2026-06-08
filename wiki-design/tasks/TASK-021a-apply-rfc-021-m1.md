---
id: task_20260608_021a
title: Apply RFC-021 M1 — schema_version 递增纪律 + profile 兼容范围校验（bump 到 2）
author: claude
executor: codex
status: done
type: apply
created: 2026-06-08
updated: 2026-06-08
related_rfcs: [RFC-021]
---

# TASK-021a: Apply RFC-021 M1

## 目标

落地 RFC-021 M1：`BASE_SCHEMA` 加 `schema_version`（bump 1→2）+ `min_compatible_profile_version`（=1）；`validate_profile()` 从严格相等改为兼容范围校验；`.wiki-schema.md` 的 profile 版本文案同步；fixture + 真实实例 smoke。M2（`--sync-schema` 保护 + datawarehouse 迁移）留 TASK-021b。

## 前置条件

- RFC-021 status: accepted（Decision by claude 2026-06-08）。
- working tree clean（除本 task）。
- 环境：`/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python`（完整命令，勿塞 zsh 变量）。

## 强约束

1. **范围校验**：`profile.schema_version ∈ [min_compatible_profile_version, schema_version]` → 兼容；`< min_compatible_profile_version` 或 `> schema_version` → `PROFILE_SCHEMA_VERSION` error（**复用**错误码，仅调 message 指出兼容边界）。
2. **健壮性**：`profile.schema_version` 缺失 / 非整数（字符串 / null / 浮点）→ 报 `PROFILE_SCHEMA_VERSION` error，**不得抛 Python 异常**（先类型校验、再比较）。
3. **基线 bump**：`schema_version` 1→2、`min_compatible_profile_version`=1（RFC-001~020 无破坏性 core 变更，故 v1 profile 仍兼容）。
4. **personal v1 profile bump 后必须仍 pass**（必测 smoke：真实 personal 实例 lint exit 0）。
5. **不改**：M2 的 sync 逻辑（留 021b）、core schema 语义 / enum / 页面机制、任何实例数据；不动 graph / eval。

## 步骤

> **Step 0 spec-review**：核对 `wiki_common.py:21`（`schema_version`）、`:626`（`validate_profile()` 严格相等）、`PROFILE_SCHEMA_VERSION` 现有 message / 用法；定位 `knowledge/.wiki-schema.md` 的 profile `schema_version` 兼容文案位置（**确认它不在 RFC-020 的 6 个 generated block 内**，需手动改 + 单独验证）；核对 personal `.wiki-profile.json`（应为 v1、无扩展）。发现歧义先提。

1. **`scripts/wiki_common.py`**：
   - `BASE_SCHEMA["schema_version"]` 1→2；新增 `BASE_SCHEMA["min_compatible_profile_version"] = 1`。
   - `validate_profile()` 把严格相等改为范围校验：先校验 `profile.schema_version` 存在且为 int（否则 `PROFILE_SCHEMA_VERSION` error、不抛异常）；再判 `< min_compatible_profile_version`（跨破坏性下界，提示按 migration note 升级）/ `> schema_version`（profile 比引擎新，提示升级引擎）/ 否则 pass。
2. **`scripts/wiki_lint.py`**：`PROFILE_SCHEMA_VERSION` message 调整为兼容边界提示（错误码不变）。
3. **`knowledge/.wiki-schema.md`**：Schema Profile 段把「profile `schema_version` 必须等于 `BASE_SCHEMA`」文案改为兼容范围语义（`∈ [min_compatible_profile_version, schema_version]`）。该文案**不在** generated block 内，手动改。
4. **`scripts/README.md`**：补 `schema_version` 递增纪律 + 兼容范围语义。
5. **测试 `tests/test_task_021a.py`**（unittest）：
   - profile v1（== min_compat 1）对 base(2) → **pass**。
   - profile == base(2) → pass。
   - profile < min_compat（如 0）→ `PROFILE_SCHEMA_VERSION` error。
   - profile > base（如 3）→ `PROFILE_SCHEMA_VERSION` error。
   - `schema_version` 缺失 → error，**无 Python 异常**。
   - `schema_version` 非 int（字符串 "2" / null / 浮点）→ error，**无 Python 异常**。
   - base 实例（无 profile）不受影响。
6. 跑验证 → commit（引擎一个 commit）。

## 验证

```bash
cd /Users/zhangjunwu/workspace/llm-wiki/llm-wiki
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest -v tests.test_task_021a
# 真实实例 smoke：personal v1 profile bump 后仍兼容
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/knowledge/personal --check-only; echo "personal exit=$?"
# knowledge（无 profile）+ datawarehouse（无 profile）
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root knowledge --check-only; echo "knowledge exit=$?"
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse --check-only; echo "dw exit=$?"
# .wiki-schema 文案改动不破坏 6 生成块
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root knowledge --check-docs; echo "check-docs exit=$?"
# 回归
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest tests.test_task_012 tests.test_task_013 tests.test_task_014 tests.test_task_015 tests.test_task_016a tests.test_task_016b tests.test_task_017 tests.test_task_019 tests.test_task_020a
```

## 完成后报告格式

- Step 0 spec-review 结论（含 personal `.wiki-profile.json` 现状 + `.wiki-schema.md` profile 文案位置）
- 改动文件 + 关键位置（BASE_SCHEMA 两字段、validate_profile 范围校验、message、.wiki-schema 文案）
- 验证输出（fixture 6+ 场景、personal/knowledge/datawarehouse smoke、check-docs、回归）
- commit sha
- 偏离或异常

## Execution log by codex · 2026-06-08

Step 0 spec-review 结论：

- `scripts/wiki_common.py` 当前 `BASE_SCHEMA["schema_version"]` 为 1，`validate_profile()` 对 `profile.schema_version` 使用严格相等校验，错误码为 `PROFILE_SCHEMA_VERSION`。
- `PROFILE_SCHEMA_VERSION` 由 `wiki_common.validate_profile()` 生成 `ProfileIssue`，`wiki_lint.py` 在 `run_lint()` 开头统一转成 lint issue；因此 message 的实际落点是 `wiki_common.py`，不是 `wiki_lint.py` 的独立映射表。
- `knowledge/.wiki-schema.md` 的 Schema Profile 段在第 68 行附近，不在 RFC-020 的 6 个 generated block 内；可手动修改，并用 `--check-docs` 单独验证。
- personal 实例存在 `/Users/zhangjunwu/workspace/obsidian/knowledge/personal/.wiki-profile.json`，内容为 `schema_version: 1`、`profile: personal`，扩展字段/类型均为空。
- 未发现 spec 与现有代码结构的阻塞歧义。

改动文件与关键位置：

- `scripts/wiki_common.py`
  - `BASE_SCHEMA["schema_version"]` 从 1 bump 到 2。
  - 新增 `BASE_SCHEMA["min_compatible_profile_version"] = 1`。
  - `validate_profile()` 改为范围校验：缺失/非整数、低于下界、高于 base 均报 `PROFILE_SCHEMA_VERSION`；兼容范围内通过。
  - 类型判断使用 `type(schema_version) is not int`，避免 Python `bool` 作为 `int` 子类被误放行。
- `knowledge/.wiki-schema.md`
  - Schema Profile 示例改为 `schema_version: 2`。
  - 约束段新增兼容范围说明：当前 base `schema_version: 2`、`min_compatible_profile_version: 1`，v1 profile 仍兼容。
- `scripts/README.md`
  - `PROFILE_SCHEMA_VERSION` 说明改为缺失、非整数或超出兼容范围。
  - Schema profile 段补充递增纪律和兼容范围语义。
- `tests/test_task_021a.py`
  - 覆盖 v1/v2 pass、低于下界、高于 base、缺失、字符串/null/浮点/bool 非 int、无 profile base 实例不受影响。

验证输出：

```text
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest -v tests.test_task_021a
test_base_instance_without_profile_is_unchanged ... ok
test_profile_v1_is_compatible_with_base_v2 ... ok
test_profile_v2_is_compatible_with_base_v2 ... ok
test_profile_version_above_base_is_error ... ok
test_profile_version_below_min_is_error ... ok
test_profile_version_missing_is_error_without_traceback ... ok
test_profile_version_non_int_is_error_without_traceback ... ok

Ran 7 tests in 1.718s
OK
```

```text
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/knowledge/personal --check-only; echo "personal exit=$?"
实例: /Users/zhangjunwu/workspace/obsidian/knowledge/personal · profile: personal
扫描: personal/wiki/ (10 文件) · personal/inbox/ (0 draft) · personal/raw/ (0 source)
错误: 0 · 警告: 0
personal exit=0
```

```text
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root knowledge --check-only; echo "knowledge exit=$?"
实例: /Users/zhangjunwu/workspace/llm-wiki/llm-wiki/knowledge · profile: base
扫描: knowledge/wiki/ (4 文件) · knowledge/inbox/ (0 draft) · knowledge/raw/ (0 source)
错误: 0 · 警告: 0
knowledge exit=0
```

```text
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse --check-only; echo "dw exit=$?"
实例: /Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse · profile: base
扫描: datawarehouse/wiki/ (33 文件) · datawarehouse/inbox/ (0 draft) · datawarehouse/raw/ (18 source)
错误: 0 · 警告: 0
dw exit=0
```

```text
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root knowledge --check-docs; echo "check-docs exit=$?"
wiki-lint v0.1.0 --check-docs
受管块: 6
错误: 0
check-docs exit=0
```

```text
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest tests.test_task_012 tests.test_task_013 tests.test_task_014 tests.test_task_015 tests.test_task_016a tests.test_task_016b tests.test_task_017 tests.test_task_019 tests.test_task_020a
Ran 56 tests in 8.553s
OK
```

偏离或异常：

- Step 2 写的是 `scripts/wiki_lint.py` message 调整；现有实现中 profile message 的单一来源是 `wiki_common.validate_profile()`，`wiki_lint.py` 只透传 `ProfileIssue`。因此实际改动在 `wiki_common.py`，并同步 `scripts/README.md` 的错误码说明；未新增 `wiki_lint.py` 分支，避免重复消息源。
- 未修改 M2 sync 逻辑、graph/eval、core enum、页面机制或任何实例数据。

Commit：本提交（sha 见最终报告）。

## Evaluation by claude · <date>

（评估者填写）
