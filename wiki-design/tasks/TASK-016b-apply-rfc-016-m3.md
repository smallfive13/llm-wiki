---
id: task_20260604_016b
title: Apply RFC-016 M3 — 富媒体规则（图引用断引校验 + 硬底线文本兜底）
author: claude
executor: codex
status: done
type: apply
created: 2026-06-04
updated: 2026-06-04
related_rfcs: [RFC-016]
---

# TASK-016b: Apply RFC-016 M3 — 富媒体规则

## 目标

落地 RFC-016 M3 的**工具规则**：图片引用断引校验（相对路径）+ 硬底线文本兜底 + 引用约定文档。纯工具规则，不动大规模数据（数据对齐在 016c）。多模态描述是写入 AI 职责，工具永不读图像素。

## 前置条件

- TASK-016a done（visibility/脱敏分级已落地）。
- working tree clean（除本 task）。

## 强约束

1. **工具永不读图像素**：只做文本/路径机械校验。
2. 不动 knowledge 数据正本（本 task 是工具规则 + fixture；datawarehouse 数据对齐在 016c）。
3. 断引、硬底线文本命中 = error；缺描述 = 可选 warning。退出码语义不变。

## 步骤

> Step 0 spec-review：复用 RFC-013 的 `strip_code_spans()` 与 wikilink dangling 思路；确认图引用解析能套用；发现歧义先提。

1. **`wiki_lint.py` — 图引用断引校验**：
   - 提取 wiki 页正文的图片引用 `![alt](path)` 和 `![[path]]`。
   - **先 `strip_code_spans()`**（RFC-013）跳过代码块里的假图片。
   - **跳过非本地 scheme**：`http://`、`https://`、`data:`、`mailto:`（写死这 4 个 + fixture 覆盖；Codex re-review 非阻塞建议）。
   - 本地相对路径：按引用页所在目录解析 + **归一化并限制在实例根内**（解析后路径逃出实例根 → error，拒 `../` 逃逸）。
   - 目标文件不存在 → `IMAGE_DANGLING`（error，类比 wikilink dangling）。

2. **`wiki_lint.py` — 硬底线文本兜底**：对图片**文件名、相对路径、紧邻描述文本、source notes / manifest caption** 扫 `hard_redact` 正则（复用 016a 的硬底线），命中 → error（`IMAGE_HARD_REDACT` 或复用 PII error code）。**不读图像素**。

3. **`wiki_lint.py` — 可选**：嵌入图缺紧邻描述文本 → warning（`IMAGE_NO_DESCRIPTION`）。

4. **文档**：`scripts/README.md`（图引用约定 + 校验 + error code）；`knowledge/.wiki-schema.md`（M3 富媒体引用约定：`raw/sources/assets/` 布局 + `![alt](相对路径)` + 写入 AI 多模态描述）；`wiki-design/02-workflows.md`（ingest 富媒体步骤）。

5. **测试**（unittest）：
   - 本地图存在 → 通过；不存在 → `IMAGE_DANGLING` error。
   - 非本地 scheme（http/https/data/mailto）→ **跳过、不报断引**（每种一个 fixture）。
   - 代码块里的 `![](x.png)` → `strip_code_spans` 跳过、不报。
   - `../` 逃逸实例根 → error。
   - 硬底线文本兜底：文件名/路径/描述含密钥正则 → error；不含 → 通过。
   - 缺描述 → warning（可选）。

6. 跑验证 → commit（引擎一个 commit）。

## 验证

```bash
ENGINE=/Users/zhangjunwu/workspace/llm-wiki/llm-wiki
PY="/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python"
DW=/Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse

cd $ENGINE && $PY -m unittest -v tests.test_task_016b
# datawarehouse（已含 75 图引用）跑 lint：图引用应解析（现有相对引用），看是否有 IMAGE_DANGLING
$PY scripts/wiki_lint.py --root $DW --check-only; echo "dw exit=$?"
# 回归
$PY -m unittest -v tests.test_task_012 tests.test_task_013 tests.test_task_014 tests.test_task_015 tests.test_task_016a
```

> 注：datawarehouse 现有图引用若此时报 `IMAGE_DANGLING`（相对路径与新校验口径不符），属 016c 数据对齐范畴——本 task 记录现象、不在此修数据；但若是**校验器 bug**（误报真实存在的图）则必须在本 task 修。

## 完成后报告格式

- Step 0 spec-review 结论
- 改动文件 + 关键位置（图引用解析、scheme 跳过、路径归一化、硬底线兜底）
- 验证输出（fixture 全绿 + datawarehouse lint 现象 + 回归）
- commit sha
- 偏离或异常

## Execution log by codex · 2026-06-04

- Step 0 spec-review 结论：通过。现有 `wiki_common.strip_code_spans()` 已由 RFC-013 落地，`wiki_graph.build_edges()` 已先剥代码块再解析 wikilink；`wiki_lint.run_lint()` 在 `validate_json_contracts()` 后能拿到 `capture_policy` 与 `source_manifest`，图引用校验可作为只读检查插入，不触达派生层写入，不读图像像素。未发现需要改 spec 的歧义。
- 改动文件 + 关键位置：
  - `scripts/wiki_common.py`：注册 `IMAGE_DANGLING` / `IMAGE_PATH_ESCAPE` / `IMAGE_HARD_REDACT` / `IMAGE_NO_DESCRIPTION` level。
  - `scripts/wiki_lint.py`：新增 Markdown/Obsidian 图片引用提取；先 `strip_code_spans()`；跳过 `http://` / `https://` / `data:` / `mailto:`；按引用页目录解析本地相对路径并限制在实例根；缺失报 `IMAGE_DANGLING`，逃逸报 `IMAGE_PATH_ESCAPE`；图片文件名、相对路径、紧邻描述、manifest notes/caption 命中 hard_redact 报 `IMAGE_HARD_REDACT`；缺紧邻描述报 `IMAGE_NO_DESCRIPTION` warning。
  - `tests/test_task_016b.py`：覆盖本地图存在/缺失、4 类非本地 scheme、代码块跳过、路径逃逸、hard_redact 文件名/路径/描述/manifest 文本兜底、缺描述 warning。
  - `scripts/README.md` / `knowledge/.wiki-schema.md` / `wiki-design/02-workflows.md`：补富媒体引用约定、error code 和 ingest 工作流。`.wiki-schema.md` 示例避免 `](../` 断链，保持 RFC-015 分发约束。

验证输出：

```text
$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest -v tests.test_task_016b
test_code_blocks_are_ignored_for_image_refs (tests.test_task_016b.Task016bImageLintTest.test_code_blocks_are_ignored_for_image_refs) ... ok
test_hard_redact_scans_filename_path_description_and_manifest_text (tests.test_task_016b.Task016bImageLintTest.test_hard_redact_scans_filename_path_description_and_manifest_text) ... ok
test_local_image_exists_and_missing_image_errors (tests.test_task_016b.Task016bImageLintTest.test_local_image_exists_and_missing_image_errors) ... ok
test_missing_adjacent_description_is_warning (tests.test_task_016b.Task016bImageLintTest.test_missing_adjacent_description_is_warning) ... ok
test_nonlocal_schemes_are_skipped (tests.test_task_016b.Task016bImageLintTest.test_nonlocal_schemes_are_skipped) ... ok
test_path_escape_is_error (tests.test_task_016b.Task016bImageLintTest.test_path_escape_is_error) ... ok

----------------------------------------------------------------------
Ran 6 tests in 1.918s

OK
```

```text
$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse --check-only; echo "dw exit=$?"
wiki-lint instance root: /Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse · profile: base

wiki-lint v0.1.0
================
实例: /Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse · profile: base
扫描: datawarehouse/wiki/ (30 文件) · datawarehouse/inbox/ (0 draft) · datawarehouse/raw/ (18 source)

[OK]    schema 校验: 30 页扫描
[OK]    ID 唯一性: 30 个 id
[OK]    canonical 引用 + supersedes 对称
[OK]    source 单主键
[OK]    entity 别名（含链式跳转 / status:redirect）: 0 entries
[OK]    inbox: 0 draft
[OK]    脱敏扫描（inbox-only）: 0 命中

派生层未重建（--check-only）

错误: 0 · 警告: 0

dw exit=0
```

```text
$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest -v tests.test_task_012 tests.test_task_013 tests.test_task_014 tests.test_task_015 tests.test_task_016a
test_co_source_keeps_degree_but_skips_in_out (tests.test_task_012.Task012GraphTest.test_co_source_keeps_degree_but_skips_in_out) ... ok
test_related_edges_are_directed (tests.test_task_012.Task012GraphTest.test_related_edges_are_directed) ... ok
test_stale_and_unverified_trigger_sets (tests.test_task_012.Task012LintTest.test_stale_and_unverified_trigger_sets) ... ok
test_fenced_block_boundaries (tests.test_task_013.StripCodeSpansTest.test_fenced_block_boundaries) ... ok
test_inline_backtick_run_boundaries (tests.test_task_013.StripCodeSpansTest.test_inline_backtick_run_boundaries) ... ok
test_preserves_length_and_newlines (tests.test_task_013.StripCodeSpansTest.test_preserves_length_and_newlines) ... ok
test_unclosed_fence_strips_to_eof (tests.test_task_013.StripCodeSpansTest.test_unclosed_fence_strips_to_eof) ... ok
test_build_edges_keeps_real_and_table_links_but_ignores_code_links (tests.test_task_013.WikilinkParsingTest.test_build_edges_keeps_real_and_table_links_but_ignores_code_links) ... ok
test_canonical_edges_do_not_use_stripped_body (tests.test_task_013.WikilinkParsingTest.test_canonical_edges_do_not_use_stripped_body) ... ok
test_code_duplicate_slug_does_not_create_false_ambiguous (tests.test_task_013.WikilinkParsingTest.test_code_duplicate_slug_does_not_create_false_ambiguous) ... ok
test_parse_wikilink_unescapes_table_pipe_before_display_and_anchor (tests.test_task_013.WikilinkParsingTest.test_parse_wikilink_unescapes_table_pipe_before_display_and_anchor) ... ok
test_check_requires_zero_lint_errors_even_when_score_is_high (tests.test_task_014.Task014EvalTest.test_check_requires_zero_lint_errors_even_when_score_is_high) ... ok
test_deterministic_except_timestamp (tests.test_task_014.Task014EvalTest.test_deterministic_except_timestamp) ... ok
test_empty_instance_has_null_score_check_zero_and_no_snapshot (tests.test_task_014.Task014EvalTest.test_empty_instance_has_null_score_check_zero_and_no_snapshot) ... ok
test_fixture_a_all_green_scores_100 (tests.test_task_014.Task014EvalTest.test_fixture_a_all_green_scores_100) ... ok
test_fixture_b_endorsement_low_is_weakest_dimension (tests.test_task_014.Task014EvalTest.test_fixture_b_endorsement_low_is_weakest_dimension) ... ok
test_fixture_c_integrity_formula_counts_dangling_by_page_count (tests.test_task_014.Task014EvalTest.test_fixture_c_integrity_formula_counts_dangling_by_page_count) ... ok
test_json_smoke_and_eval_does_not_write_derived_layers (tests.test_task_014.Task014EvalTest.test_json_smoke_and_eval_does_not_write_derived_layers) ... ok
test_multi_root_calls_do_not_leak_lint_global_state (tests.test_task_014.Task014EvalTest.test_multi_root_calls_do_not_leak_lint_global_state) ... ok
test_snapshot_appends_for_non_empty_ok_result (tests.test_task_014.Task014EvalTest.test_snapshot_appends_for_non_empty_ok_result) ... ok
test_new_instance_schema_has_no_parent_links (tests.test_task_015.Task015SyncSchemaTest.test_new_instance_schema_has_no_parent_links) ... ok
test_sync_schema_creates_missing_file (tests.test_task_015.Task015SyncSchemaTest.test_sync_schema_creates_missing_file) ... ok
test_sync_schema_only_changes_schema_file (tests.test_task_015.Task015SyncSchemaTest.test_sync_schema_only_changes_schema_file) ... ok
test_sync_schema_rejects_conflicting_options (tests.test_task_015.Task015SyncSchemaTest.test_sync_schema_rejects_conflicting_options) ... ok
test_sync_schema_rejects_invalid_roots_and_directory_target (tests.test_task_015.Task015SyncSchemaTest.test_sync_schema_rejects_invalid_roots_and_directory_target) ... ok
test_sync_schema_replaces_existing_file (tests.test_task_015.Task015SyncSchemaTest.test_sync_schema_replaces_existing_file) ... ok
test_sync_schema_unchanged_does_not_touch_mtime (tests.test_task_015.Task015SyncSchemaTest.test_sync_schema_unchanged_does_not_touch_mtime) ... ok
test_hard_redact_is_error (tests.test_task_016a.Task016aLintTest.test_hard_redact_is_error) ... ok
test_public_wiki_page_soft_redact_warning (tests.test_task_016a.Task016aLintTest.test_public_wiki_page_soft_redact_warning) ... ok
test_v1_capture_policy_is_legacy_warning_not_error (tests.test_task_016a.Task016aLintTest.test_v1_capture_policy_is_legacy_warning_not_error) ... ok
test_v2_capture_policy_has_no_legacy_warning (tests.test_task_016a.Task016aLintTest.test_v2_capture_policy_has_no_legacy_warning) ... ok
test_visibility_optional_and_invalid_values_error (tests.test_task_016a.Task016aLintTest.test_visibility_optional_and_invalid_values_error) ... ok

----------------------------------------------------------------------
Ran 32 tests in 6.065s

OK
```

- commit sha：本日志与实现按 task 要求同一引擎 commit 提交；实际 SHA 在最终报告中回报。
- 偏离或异常：首次回归发现 `knowledge/.wiki-schema.md` 的图片示例含 `](../`，触发 TASK-015 断链分发测试；已改为不含脆弱相对链接的占位示例并重跑通过。datawarehouse lint 结果为 errors 0 / warnings 0，没有 `IMAGE_DANGLING`，未改任何 datawarehouse 数据。

## Evaluation by claude · <date>

（评估者填写）
