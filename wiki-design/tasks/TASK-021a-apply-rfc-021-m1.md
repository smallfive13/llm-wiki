---
id: task_20260608_021a
title: Apply RFC-021 M1 — schema_version 递增纪律 + profile 兼容范围校验（bump 到 2）
author: claude
executor: codex
status: pending
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

## Execution log by codex · <date>

（执行者填写）

## Evaluation by claude · <date>

（评估者填写）
