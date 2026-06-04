---
id: task_20260604_017
title: Apply RFC-017 — source_manifest.status 加 superseded/archived + datawarehouse 修正
author: claude
executor: codex
status: done
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

## Execution log by codex · 2026-06-04

- Step 0 spec-review 结论：通过，无歧义。`source_manifest.statuses` 来源是 `scripts/wiki_common.py` 的 `BASE_SCHEMA["json_contracts"]["source_manifest"]["statuses"]`；`scripts/wiki_lint.py` 在 `configure()` 中执行 `SOURCE_STATUSES = set(source_contract["statuses"])`，后续只做 `src.get("status") not in SOURCE_STATUSES` 成员校验，因此只增 enum 值会自动接受，不需要改 lint 逻辑或退出码。

- 引擎改动文件 + 关键位置：
  - `scripts/wiki_common.py`：`source_manifest.statuses` 在既有 `new/triaged/ingested/skipped/failed/deleted` 后只增 `superseded`、`archived`。
  - `wiki-design/05-contracts-and-next-steps.md`：Source Manifest Schema 正本 status enum 同步。
  - `knowledge/.wiki-schema.md`：分发 schema 的 source_manifest status enum 同步。
  - `scripts/README.md`：补 source_manifest status enum 一行说明。
  - `tests/test_task_017.py`：新增 `superseded` / `archived` 合法、既有 6 值不回归、非法值仍 `ENUM_INVALID` 的 fixture。

- 验证输出：

```text
$ conda run -n py312 python -m unittest -v tests.test_task_017
test_existing_manifest_statuses_remain_valid ... ok
test_invalid_manifest_status_still_errors ... ok
test_superseded_and_archived_manifest_statuses_are_valid ... ok

Ran 3 tests in 0.782s
OK
```

```text
$ grep -c 'superseded' wiki-design/05-contracts-and-next-steps.md knowledge/.wiki-schema.md scripts/README.md
wiki-design/05-contracts-and-next-steps.md:11
knowledge/.wiki-schema.md:5
scripts/README.md:3

$ grep -c 'archived' wiki-design/05-contracts-and-next-steps.md knowledge/.wiki-schema.md scripts/README.md
wiki-design/05-contracts-and-next-steps.md:2
knowledge/.wiki-schema.md:4
scripts/README.md:2
```

```text
$ conda run -n py312 python scripts/wiki_lint.py --root knowledge --check-only
错误: 0 · 警告: 0
engine exit=0

$ conda run -n py312 python scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/knowledge/personal --check-only
错误: 0 · 警告: 0
personal exit=0

$ conda run -n py312 python scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse --check-only
错误: 0 · 警告: 0
dw-before exit=0
```

```text
$ conda run -n py312 python -m unittest -v tests.test_task_012 tests.test_task_013 tests.test_task_014 tests.test_task_015 tests.test_task_016a tests.test_task_016b
Ran 38 tests in 6.468s
OK
```

- datawarehouse 修正：
  - `/Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse/raw/source_manifest.json` 中旧集合 `src_20260603_international-data-service-tech-docs` 从 `status: deleted` 改为 `status: superseded`，notes 改为 `status=superseded` 的审计说明。
  - 对 personal / datawarehouse 执行 `scripts/wiki_init.py --sync-schema`，输出：

```text
personal:
old_sha256: 6f416bebba5085a1dd1dba264a46bd0cdbc094ce8b4a7c04e1bc2d6834203ea9
new_sha256: 5b5438835cc5109026492fc87521a52d76f340c7c55e62d837e5b8f0d20fe79c
action: replaced

datawarehouse:
old_sha256: 6f416bebba5085a1dd1dba264a46bd0cdbc094ce8b4a7c04e1bc2d6834203ea9
new_sha256: 5b5438835cc5109026492fc87521a52d76f340c7c55e62d837e5b8f0d20fe79c
action: replaced
```

  - 修正后验证：

```text
$ conda run -n py312 python scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse --check-only
错误: 0 · 警告: 0
dw-after exit=0

$ conda run -n py312 python scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/knowledge/personal --check-only
错误: 0 · 警告: 0
personal-after exit=0

$ grep -n -A14 'src_20260603_international-data-service-tech-docs' /Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse/raw/source_manifest.json
13-      "status": "superseded",
18-      "notes": "历史集合 source，保留审计；2026-06-04 已拆分为 17 个细粒度原文 source，并由 syn_20260603_international-data-service-tech-knowledge 门户聚合。status=superseded 表示该集合 source 不再作为活跃 ingest source 使用；图片原文 93 张，保留 75 张，过滤 18 张。"
```

- datawarehouse commit sha：`4bfd9eebb5dcc8afe7f77d1372b84afffa4333a6`。
- 引擎 commit sha：本 Execution log 与实现同一引擎 commit 提交，最终 SHA 见执行完成后的用户报告。

- 偏离或异常：
  - 首次按 spec 变量写法设置 `PY="/Users/.../conda run -n py312 python"` 后在 zsh 中被当作单个命令，三库 lint 返回 `127`，未实际执行。已改用直接命令重跑，三库 lint 均 exit 0。
  - `--sync-schema` 是全量 schema 覆盖；外部 personal / datawarehouse 之前尚未同步 RFC-016a/b 的 schema 文案，因此本次外部数据仓 commit 除 TASK-017 enum 外，也同步带入了既有源头 schema 中的 RFC-016a/b 文档内容。未触发其它 init 路径。

## Evaluation by claude · 2026-06-04

**Verdict: PASS。** 独立复跑全部验证；enum 扩展、三处契约同步、datawarehouse 修正、零回归均达标。

### 独立复跑

| 验证 | 结果 |
| --- | --- |
| `unittest tests.test_task_017` | 3 tests OK（superseded/archived 合法 / 既有 6 值不回归 / 非法 ENUM_INVALID） |
| BASE_SCHEMA enum | `[new,triaged,ingested,skipped,failed,deleted,superseded,archived]`（只增 2，未动既有） |
| 三处契约同步 | 05 / .wiki-schema / README 均含 superseded+archived；**三库 .wiki-schema 同 SHA** |
| datawarehouse 旧集合 | `deleted → superseded`，notes 更新审计；lint 0/0 |
| 回归 012-016b | 38 tests OK |

### 核查点

1. **只增不改**：enum 8 值（原 6 + superseded/archived），lint 读 enum 自动接受、source 单主键不误伤——test 覆盖。
2. **契约一致**：05（正本）+ .wiki-schema + README 三处同步；datawarehouse 旧集合 `superseded` 配合 source 页 `superseded_by`（016c 已建对称链）。
3. **改动范围**：引擎/数据仓分开提交，不混。

### Observation（流程小疏漏,已被本 task 顺带补齐）

- `--sync-schema` 全量覆盖,本次把外部实例 `.wiki-schema.md` 同步到最新源头时,**顺带补齐了 RFC-016a/b 改源头 schema 后未 `--sync` 留下的 drift**（三库 .wiki-schema 现在同 SHA）。这暴露:**改源头 `.wiki-schema.md` 的 apply task 应在收尾 `--sync-schema` 到各实例**,否则 drift 累积到下次。016a/b 漏了这步,017 补上。建议后续把"改源头 schema → --sync 各实例"写进 apply 收尾约定（或 RFC-015 backlog 的 drift 检测兜底）。不阻断本 task。

### 结论

RFC-017 闭环,**backlog 的 source 生命周期 gap 关闭**。source_manifest 现在能表达"被取代/归档",datawarehouse 旧集合语义回正。TASK-017 done 确认有效。
