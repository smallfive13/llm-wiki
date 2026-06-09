---
id: task_20260608_021b
title: Apply RFC-021 M2 — --sync-schema 覆盖前保护（last-synced hash）+ datawarehouse 迁移
author: claude
executor: codex
status: done
type: apply
created: 2026-06-08
updated: 2026-06-09
related_rfcs: [RFC-021]
---

# TASK-021b: Apply RFC-021 M2

## 目标

落地 RFC-021 M2：`--sync-schema` 加 **last-synced hash 三方比较**覆盖前保护 + `--force` + `.wiki/schema_sync.json`（进 Git）；`.wiki-schema.md` 加「引擎镜像、特化外移」原则；`02-workflows.md` schema 升级 / 分发流程；fixture。**最后执行 datawarehouse 迁移**（删冗余特化 → `--force` 首次纳管同步 RFC-020 的 6 生成块 → 全绿），数据仓单独 commit。

## 前置条件

- RFC-021 status: accepted；TASK-021a status: done（`schema_version: 2` 已生效）。
- 引擎 working tree clean（除本 task）。
- **datawarehouse 迁移前**：`/Users/zhangjunwu/workspace/obsidian/knowledge` git **clean**（必查；不 clean 则停下报告，不混提交）。
- 环境：`/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python`（完整命令，勿塞 zsh 变量）。

## 强约束

1. **hash 口径**：`.wiki-schema.md` **字节级 sha256**，复用现有 `sha256_file()`；**不做**换行 / 编码 / Markdown / frontmatter 归一化；写模板时用同一份 bytes（防 LF/CRLF / 编码假 drift）。
2. **覆盖前保护算法**（RFC-021 M2 钉死，按序）：
   1. 实例无 `.wiki-schema.md` → 写入 + 写 `schema_sync.json`。
   2. 实例当前 hash == 引擎当前 hash → no-op；**但若 `schema_sync.json` 缺失 / 旧 → 写入当前 hash 并报 metadata repair**（纳管手工已同步实例，免 `--force`）。
   3. 实例当前 hash == `last_synced_engine_sha256` → 安全覆盖 + 更新 `schema_sync.json`。
   4. 否则（被本地改过 / 无记录）→ **默认拒绝 + 打印 diff**，提示 `--force`（exit 非 0）。
3. **`--force`**：跳过判定直接覆盖 + 写 `schema_sync.json`。
4. **原子写**：`.wiki-schema.md` 与 `.wiki/schema_sync.json` 均写临时文件 + `os.replace()`，**先写 schema、再写 sync 元数据**（崩溃最多致下次保守拒绝，绝不误覆盖）。
5. **`.wiki/schema_sync.json` 进 Git**（实例正本元数据）：`.gitignore` 显式放行，不当派生层。
6. **两个 commit 分开**：引擎改动（步骤 1-6）一个引擎仓 commit；**datawarehouse 迁移（步骤 8）在数据仓单独 commit**，不混入引擎 commit。
7. **不改**：core schema 语义、M1 已落的版本逻辑、graph / eval、datawarehouse 的 wiki 页面 / source 数据（迁移只动其 `.wiki-schema.md` + `.wiki/schema_sync.json`）。

## 步骤

> **Step 0 spec-review**：核对 `wiki_init.py:132 sync_schema()` + `:126 write_sync_report()` 现状（整文件覆盖、报告格式）、`sha256_file()` 位置与口径；核对 `.gitignore` 现有 `.wiki/` 派生层规则（确认 `schema_sync.json` 需显式放行的写法）；**复核 datawarehouse `.wiki-schema.md:251/262/274` 特化措辞确已在 `purpose.md` / 库根 `AGENTS.md` 覆盖**（codex re-review 已确认 capture_policy.json `soft_redact:[]` + `purpose.md:16` + `AGENTS.md:31/:37`，复跑确认）。发现歧义先提。

1. **`scripts/wiki_init.py`**：`sync_schema()` 重写为强约束 2 的状态机 + `--force`；读写 `.wiki/schema_sync.json`（`last_synced_engine_sha256`）；no-op 元数据修复；原子写；扩展 `write_sync_report()` 持久化。
2. **`.gitignore`**：放行 `.wiki/schema_sync.json`（实例元数据进 Git）。
3. **`knowledge/.wiki-schema.md`**：新增「`.wiki-schema.md` 是引擎统一镜像、不承载实例特化；实例特化只在 `.wiki-profile.json` / `.wiki/capture_policy.json` / `purpose.md` / 库根 `AGENTS.md`」原则段。**不破坏 6 生成块**（改完 `--check-docs` 仍 exit 0）。
4. **`wiki-design/02-workflows.md`**：schema 升级 / 分发流程（bump 规则、migration note、`--sync-schema` 保护 + `--force`、特化外移）。
5. **`scripts/README.md`**：`--sync-schema [--force]` 用法、保护算法四分支、`schema_sync.json` 说明、退出码。
6. **测试 `tests/test_task_021b.py`**：sync 保护各分支——target 缺失→写；==engine current→no-op（+ 元数据缺失时 repair）；==last_synced→安全覆盖；被改 / 无记录→拒绝（exit 非 0、打印 diff）；`--force`→覆盖；原子写不留临时文件；hash 字节级一致。
7. **引擎 commit**（步骤 1-6，引擎仓一个 commit）。
8. **datawarehouse 迁移**（数据仓单独操作，需用户授权动数据仓）：
   - a. 查 `/Users/zhangjunwu/workspace/obsidian/knowledge` git **clean**；不 clean 则停下报告。
   - b. 复核 datawarehouse `.wiki-schema.md:251/262/274` 特化已在 `purpose.md` / `AGENTS.md` 覆盖（Step 0 已确认）。
   - c. 删 datawarehouse `.wiki-schema.md` 冗余特化措辞。
   - d. `--sync-schema --root /Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse --force`（首次纳管：写引擎镜像含 6 生成块 + `schema_sync.json`）。
   - e. 验证：datawarehouse `wiki_lint --check-only` / `--scan-wiki-pii` / `wiki_eval` 全绿；`.wiki-schema.md` 与引擎一致（diff 仅余实例无关差异或为空）；脱敏边界在 `purpose.md` / `AGENTS.md` 仍在。
   - f. 数据仓单独 commit。

## 验证

```bash
ENGINE=/Users/zhangjunwu/workspace/llm-wiki/llm-wiki
DW=/Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse
cd $ENGINE
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest -v tests.test_task_021b
# 引擎自身不回归
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root knowledge --check-only; echo "knowledge exit=$?"
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root knowledge --check-docs; echo "check-docs exit=$?"
# 迁移后 datawarehouse 全绿
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root $DW --check-only; echo "dw lint exit=$?"
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root $DW --scan-wiki-pii; echo "dw pii exit=$?"
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_eval.py --root $DW | tail -5
# 迁移后 datawarehouse .wiki-schema 与引擎一致
diff $ENGINE/knowledge/.wiki-schema.md $DW/.wiki-schema.md && echo "schema 一致"
# 回归
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest tests.test_task_012 tests.test_task_013 tests.test_task_014 tests.test_task_015 tests.test_task_016a tests.test_task_016b tests.test_task_017 tests.test_task_019 tests.test_task_020a tests.test_task_021a
```

## 完成后报告格式

- Step 0 spec-review 结论（含 datawarehouse 特化外移复核结果、`.gitignore` 放行写法）
- 改动文件 + 关键位置（sync_schema 状态机、schema_sync.json 读写 / 原子写、.gitignore、.wiki-schema 原则段、02-workflows）
- 验证输出（fixture 各分支、引擎 lint/check-docs、datawarehouse 迁移后全绿 + schema diff、回归）
- **两个 commit sha**（引擎 / 数据仓）
- 偏离或异常（datawarehouse 若非 clean 则停下，必须报告）

## Execution log by codex · 2026-06-09

Step 0 spec-review 结论：

- `scripts/wiki_init.py` 原 `sync_schema()` 是直接整文件覆盖：target hash 等于 engine hash 时 `unchanged`，否则 `target.write_bytes(source.read_bytes())` 后 `replaced/created`；没有 last-synced 保护。
- `write_sync_report()` 现有稳定输出为 `old_sha256` / `new_sha256` / `action`，可沿用并扩展 action。
- `sha256_file()` 已是文件字节级 sha256：`open("rb")` 分块读取，不做换行、编码、Markdown 或 frontmatter 归一化。
- 引擎 `.gitignore` 当前忽略 `.wiki/id_index.json` / `inbox_index.json` / `normalized_alias_index.json` / cache/search/lightrag/maps 等派生层；`schema_sync.json` 需显式 `!knowledge/.wiki/schema_sync.json` 放行。`wiki_init.GITIGNORE_LINES` 也需加 `!**/.wiki/schema_sync.json`，让新实例/外部实例 git ignore 模板同步该语义。
- datawarehouse 迁移前复查 git clean：`git -C /Users/zhangjunwu/workspace/obsidian/knowledge status --short` 输出为空。
- datawarehouse 特化外移复核：
  - `.wiki-schema.md` 原 `soft_redact` 特化在行 251 附近，本库实际策略已由 `datawarehouse/.wiki/capture_policy.json` 的 `soft_redact.patterns: []` 承载。
  - 内部共享/敏感边界已在 `datawarehouse/purpose.md:16` 和 `datawarehouse/AGENTS.md:31` 覆盖。
  - 外链/子链接处理已在 `datawarehouse/AGENTS.md:35-37` 覆盖。
- 未发现继续执行的阻塞歧义。

改动文件与关键位置：

- `scripts/wiki_init.py`
  - 新增 `--force`，仅可与 `--sync-schema` 组合；脱离 `--sync-schema` 使用 exit 2。
  - 新增 `atomic_write_bytes()`，使用同目录 `<file>.<pid>.<uuid>.tmp` + `os.replace()`；`.wiki-schema.md` 与 `.wiki/schema_sync.json` 均原子写。
  - 新增 `read_schema_sync()` / `schema_sync_bytes()` / `write_schema_and_metadata()` / `write_schema_diff()`。
  - `sync_schema()` 改为 last-synced hash 状态机：缺失写入；`old == engine` 时 no-op 或 metadata repair；`old == last_synced` 时安全覆盖；否则拒绝、打印 diff、exit 1；`--force` 跳过保护并覆盖。
  - `schema_sync.json` 内容为 `version` / `last_synced_engine_sha256` / `updated_at`，hash 为引擎 `.wiki-schema.md` 字节级 sha256。
  - `GITIGNORE_LINES` 加 `!**/.wiki/schema_sync.json`。
- `.gitignore`
  - 显式放行 `!knowledge/.wiki/schema_sync.json`，作为实例正本审计状态进 Git。
- `knowledge/.wiki-schema.md`
  - 新增原则段：`.wiki-schema.md` 是引擎统一分发镜像，不承载实例特化；实例差异外移到 `.wiki-profile.json` / `.wiki/capture_policy.json` / `purpose.md` / 库根 `AGENTS.md`。
- `wiki-design/02-workflows.md`
  - 新增 Schema 升级 / 分发流程，记录 bump 规则、profile 兼容、`--sync-schema` 保护、`--force` 和特化外移。
- `scripts/README.md`
  - 同步 `--sync-schema [--force]` 用法、四分支保护算法、`schema_sync.json` 进 Git、稳定 action 集合和退出码语义。
- `tests/test_task_021b.py`
  - 覆盖 target 缺失、等于 engine 且元数据当前、等于 engine 但元数据缺失 repair、`old == last_synced` 安全覆盖、本地改/无记录拒绝+diff、`--force` 覆盖、`--force` 脱离 sync exit 2、`schema_sync.json` 为目录 exit 2、无临时文件残留。
- `tests/test_task_015.py`
  - 同步 RFC-015 旧 `--sync-schema` 测试到新保护语义：无记录本地旧 schema 默认拒绝；metadata repair 不碰 schema mtime；`--force` 只变 schema 并新增 sync 元数据。

验证输出：

```text
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest -v tests.test_task_021b
test_directory_sync_metadata_is_config_error ... ok
test_equal_target_noops_when_metadata_current ... ok
test_equal_target_repairs_missing_metadata_without_touching_schema ... ok
test_force_overwrites_local_change_and_records_metadata ... ok
test_force_requires_sync_schema ... ok
test_last_synced_match_allows_safe_replace ... ok
test_local_change_without_record_refuses_and_prints_diff ... ok
test_missing_target_writes_schema_and_metadata ... ok

Ran 8 tests in 2.425s
OK
```

```text
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root knowledge --check-only; echo "knowledge exit=$?"
实例: /Users/zhangjunwu/workspace/llm-wiki/llm-wiki/knowledge · profile: base
扫描: knowledge/wiki/ (4 文件) · knowledge/inbox/ (0 draft) · knowledge/raw/ (0 source)
错误: 0 · 警告: 0
knowledge exit=0
```

```text
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root knowledge --check-docs; echo "check-docs exit=$?"
wiki-lint v0.1.0 --check-docs
受管块: 6
错误: 0
check-docs exit=0
```

```text
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest tests.test_task_012 tests.test_task_013 tests.test_task_014 tests.test_task_015 tests.test_task_016a tests.test_task_016b tests.test_task_017 tests.test_task_019 tests.test_task_020a tests.test_task_021a
Ran 63 tests in 13.232s
OK
```

datawarehouse 迁移：

```text
git -C /Users/zhangjunwu/workspace/obsidian/knowledge status --short
(empty)
```

```text
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_init.py --root /Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse --sync-schema --force
old_sha256: b6b4cd6dabb1c3fccf893feef0fe2cb57490b3055594ad9d614fa7feb0aa7fbf
new_sha256: a499d0fb3becc2ce6a65550304a89afa3f399f25c55a0f74b5aff8028bad86a7
action: forced
```

```text
cat /Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse/.wiki/schema_sync.json
{
  "last_synced_engine_sha256": "a499d0fb3becc2ce6a65550304a89afa3f399f25c55a0f74b5aff8028bad86a7",
  "updated_at": "2026-06-09T10:30:28+08:00",
  "version": 1
}
```

```text
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse --check-only; echo "dw lint exit=$?"
扫描: datawarehouse/wiki/ (33 文件) · datawarehouse/inbox/ (0 draft) · datawarehouse/raw/ (18 source)
错误: 0 · 警告: 0
dw lint exit=0
```

```text
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse --scan-wiki-pii; echo "dw pii exit=$?"
扫描: datawarehouse/wiki/ (33 文件) · datawarehouse/inbox/ (0 draft) · datawarehouse/raw/ (18 source)
脱敏扫描（inbox + wiki）: 0 命中
错误: 0 · 警告: 0
dw pii exit=0
```

```text
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_eval.py --root /Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse | tail -5; echo "dw eval exit=$?"

lint_errors: 0
graph_config_errors: 0
snapshot: not written
dw eval exit=0
```

```text
diff /Users/zhangjunwu/workspace/llm-wiki/llm-wiki/knowledge/.wiki-schema.md /Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse/.wiki-schema.md && echo "schema 一致"
schema 一致
```

```text
git -C /Users/zhangjunwu/workspace/obsidian/knowledge status --short
(empty, after datawarehouse commit)
```

两个 commit sha：

- 引擎仓：本提交（sha 见最终报告）。
- datawarehouse：`54a791c36111161961915f29d8b3f187708592e7`

偏离或异常：

- 为了把 Execution log 与引擎实现放进同一个引擎 commit，引擎 commit 放在 datawarehouse 单独 commit 之后完成；两个仓库的改动和提交仍严格分离。
- datawarehouse 迁移只改 `.wiki-schema.md` 和新增 `.wiki/schema_sync.json`；未修改 wiki 页面、source 数据、`purpose.md`、`AGENTS.md` 或 capture policy。
- datawarehouse 仓库 `.gitignore` 未忽略 `.wiki/schema_sync.json`，新增元数据可直接纳入 Git；引擎 `.gitignore` 和 `wiki_init.GITIGNORE_LINES` 已同步显式放行。

## Evaluation by claude · <date>

（评估者填写）
