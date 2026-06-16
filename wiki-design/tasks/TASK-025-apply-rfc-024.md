---
id: task_20260610_025
title: Apply RFC-024 — wiki_init 固化实例 .ignore
author: claude
executor: codex
status: pending
type: apply
created: 2026-06-10
updated: 2026-06-10
related_rfcs: [RFC-024]
---

# TASK-025: Apply RFC-024 — wiki_init 固化实例 .ignore

## 目标

`wiki_init` scaffold 实例时写入实例根 `.ignore`（rg/fd 检索默认跳过 raw/sources、source_manifest、maps、.wiki，保留 raw/dropbox），幂等；并给引擎自带 `knowledge` 实例补一份 `.ignore`。

## 前置条件

- RFC-024 status: accepted（Decision by claude 2026-06-10，含已采纳的 codex 建议）。
- 引擎 working tree clean（除本 task）。
- 环境：`/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python`（完整命令）。

## 强约束

1. **`.ignore` 内容固定**（与已验证的手动版逐字一致）：
   ```
   # 检索优化（rg / fd 原生读 .ignore，对 agent 答疑透明；不影响 wiki_lint/graph 的 Python 扫描）。
   # 答疑只需 wiki/ + 上下文层（purpose/index/overview/log）；原始材料、图片、派生层、图谱不参与全文检索。
   # ingest 若需检索已归档原文，用 `rg --no-ignore` 或显式路径；raw/dropbox/（待处理投料）刻意保留可搜。
   raw/sources/
   raw/source_manifest.json
   maps/
   .wiki/
   ```
2. **总是写、不依赖 `--git`**：`.ignore` 随普通 init 产生（与 `.gitignore` 仅 `--git` 写不同）。
3. **幂等（补行不覆盖）**：抽通用 `ensure_lines_file(path, lines, counters, label)`，让 `.gitignore`（`ensure_gitignore`）与 `.ignore` 共用"读现有行 → 只 append 缺失标准行 → 保留用户自定义行 → 不整文件覆盖"语义。**不得**用 `ensure_text_file()`（已有 `.ignore` 缺标准行时补不齐）。
4. **`.ignore` 是目录 → exit 2**（config error，纳入 type-conflict 检查或 `ensure_*` 内处理），不抛未捕获异常（与 `ensure_gitignore` 对目录的处理一致）。
5. **不改**：`wiki_lint` / `wiki_graph` 逻辑、core schema、`schema_version`、`.ignore` 内容之外的 scaffold 产物。
6. **现有实例**：本 task 在引擎仓给 `knowledge/.ignore` 补一份（内容同上）；`personal` / `knowledge-cmn` 已有手动版（在各自数据仓，不在本 task 范围，幂等逻辑保证将来重跑不重复）。

## 步骤

> **Step 0 spec-review**：核对 `ensure_gitignore()`（`wiki_init.py:509`）现有语义与 `GITIGNORE_LINES`、`create_skeleton()` 调用链、type-conflict 检查位置（`collect_type_conflicts`）、counters 计数方式；确认抽 `ensure_lines_file` 不破坏 `.gitignore` 现有行为。发现歧义先提。

1. **`scripts/wiki_init.py`**：
   - 新增 `IGNORE_LINES` 常量（强约束 1 的内容，逐行）。
   - 抽通用 `ensure_lines_file(path, lines, counters, label)`；用它重写 `ensure_gitignore` 主体（行为不变）+ 新增 `.ignore` 写入。
   - `.ignore` 写入在普通 init 路径触发（不依赖 `--git`）；`.ignore` 是目录时 exit 2。
   - counters 计 created/skipped。
2. **`knowledge/.ignore`**：在引擎仓创建（内容 == `IGNORE_LINES`）。
3. **`scripts/README.md`**：`wiki_init` 产物说明补 `.ignore`（用途、不依赖 --git、幂等）。
4. **测试 `tests/test_task_025.py`**：
   - `wiki_init` 建临时实例 → `.ignore` 存在且内容 == `IGNORE_LINES`。
   - 检索验证：临时实例放 `raw/sources/x.md` 与 `wiki/topics/y.md` 含同词 → `rg <词>` 只命中 wiki/。
   - 幂等：已有 `.ignore`（含 1 行用户自定义）重跑 → 用户行保留 + 缺失标准行补齐 + 已存在标准行不重复。
   - 不依赖 `--git`：不带 `--git` 跑也写 `.ignore`。
   - `.ignore` 是目录 → config error / exit 2，不 traceback。
   - `ensure_gitignore` 重写后行为回归（`.gitignore` 仍正确）。
5. 跑验证 → commit（引擎一个 commit，含 `knowledge/.ignore`）→ push GitLab。

## 验证

```bash
cd /Users/zhangjunwu/workspace/llm-wiki/llm-wiki
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest -v tests.test_task_025
# 新建临时实例自带 .ignore + rg 只命中 wiki
TMP=$(mktemp -d)/inst
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_init.py --root "$TMP"
cat "$TMP/.ignore"
# knowledge 自带 .ignore + lint/graph 不受影响
cat knowledge/.ignore
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root knowledge --check-only; echo "lint=$?"
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_graph.py --root knowledge >/dev/null 2>&1; echo "graph=$?"
# 回归
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest tests.test_task_020a tests.test_task_021a tests.test_task_021b tests.test_task_022 tests.test_task_024
```

## 完成后报告格式

- Step 0 结论（ensure_gitignore 复用面、type-conflict 落点）
- 改动文件 + 关键位置（IGNORE_LINES、ensure_lines_file 抽取、knowledge/.ignore）
- 验证输出（fixture 各场景、临时实例 .ignore + rg 命中、knowledge lint/graph、回归）
- commit sha + push 记录
- 偏离或异常

## Execution log by codex · <date>

（执行者填写）

## Evaluation by claude · <date>

（评估者填写）
