---
id: task_20260604_016b
title: Apply RFC-016 M3 — 富媒体规则（图引用断引校验 + 硬底线文本兜底）
author: claude
executor: codex
status: pending
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

## Execution log by codex · <date>

（执行者填写）

## Evaluation by claude · <date>

（评估者填写）
