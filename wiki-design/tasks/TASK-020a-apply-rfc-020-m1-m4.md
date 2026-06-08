---
id: task_20260608_020a
title: Apply RFC-020 M1+M4 — doc-consistency 校验（wiki_lint --check-docs）+ soft_redact 正则 ASCII 化
author: claude
executor: codex
status: pending
type: apply
created: 2026-06-08
updated: 2026-06-08
related_rfcs: [RFC-020]
---

# TASK-020a: Apply RFC-020 M1+M4

## 目标

落地 RFC-020 的 M1（doc-consistency 校验：从 `BASE_SCHEMA` 生成确定性清单块，`wiki_lint --check-docs` 比对受管文档的 `BEGIN/END GENERATED` 块，漂移即 error；`--fix` 回写）+ M4（`soft_redact` 默认邮箱正则 ASCII 化）。M2/M3 留 TASK-020b。

## 前置条件

- RFC-020 status: accepted（Decision by claude 2026-06-08，含已采纳的 codex 非阻塞建议）。
- working tree clean（除本 task）。
- 环境：`/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python`（完整命令，勿塞 zsh 变量）。

## 强约束

1. **`--check-docs` 独立模式**：在 `main()` 的 `configure(args)` 后、`run_lint(args)` 前分支；**不触发** `validate_*`、**不写** `.wiki/` 派生层、**不污染**普通 lint 退出码；普通 `wiki_lint` / `--check-only` / `--scan-wiki-pii` **不运行** docs checker。
2. **`generate_doc_block(name)` 是纯函数、确定性**：按 `BASE_SCHEMA` 原始顺序渲染（不 re-sort，除非该字段本就排序）、固定末尾换行；同输入恒等输出，避免 dict/格式抖动误报。
3. **marker 行为钉死**：missing / duplicate / unclosed / nested 一律 **error**；`--fix` 只替换**已成对存在**的块内容、**不猜插入位置**、**不碰块外散文**。
4. **不改**：core schema 语义、`schema_version`（留 RFC-021）、graph/eval 逻辑、任何**实例数据**（wiki 页/source/manifest）。
5. **M4 改动面收窄**：只动 `BASE_SCHEMA` 默认 `soft_redact` 邮箱正则 + 引擎 `knowledge/.wiki/capture_policy.json` 同一项；**不动** datawarehouse（其 `soft_redact.patterns: []`，不继承默认）。

## 步骤

> **Step 0 spec-review**：核对 `wiki_common.BASE_SCHEMA` 实际字段路径——`core_enums.status` / `core_enums.confidence` / `page_types`（type+id_prefix+dir）/ `json_contracts.capture_policy`（字段含 hard_redact/soft_redact/default_visibility/exclude_patterns=legacy）/ `json_contracts.source_manifest.statuses` / visibility enum 的实际存放位置；核对 `wiki_lint.main()` / `configure()` / `run_lint()` / `human_output()` 挂载点与现有 `ERROR_CODES` 风格。发现歧义（尤其 visibility enum 在 BASE_SCHEMA 的确切键）先提，不臆造。

1. **`scripts/wiki_common.py`**：
   - 新增纯函数 `generate_doc_block(name) -> str`，支持 6 个块：`status-enum` / `confidence-enum` / `page-types` / `capture-policy-fields` / `source-manifest-status` / `visibility-enum`（第 6 个按 codex 建议新增，因 visibility 正是 P0 漂移项）。每块从 `BASE_SCHEMA` 对应路径渲染确定性 markdown。
   - 新增受管目标清单（块名 → 落点文档；首批落点全部 = `knowledge/.wiki-schema.md`）。
   - 新增 marker 解析 helper：定位 `<!-- BEGIN GENERATED: <name> ... -->` / `<!-- END GENERATED: <name> -->`，检测 missing / duplicate / unclosed / nested。

2. **`scripts/wiki_lint.py`**：
   - 新增 `--check-docs`：`configure()` 后独立分支，遍历受管目标 → 解析 marker → 重新生成比对；漂移收 `DOC_BLOCK_DRIFT`、缺块收 `DOC_BLOCK_MISSING`、重复/嵌套收 `DOC_BLOCK_DUPLICATE`（unclosed 归入 MISSING）；全 error。
   - 新增 `--check-docs --fix`：把成对块内容回写为生成值，仅改块内。
   - exit code：有 error → 1，否则 0。human 输出列「文件 + 块名 + diff」。`--check-docs --json` 暂不做。
   - 错误码加进 `ERROR_CODES`（或独立常量，executor 定），命名 `DOC_BLOCK_DRIFT` / `DOC_BLOCK_MISSING` / `DOC_BLOCK_DUPLICATE`。

3. **`knowledge/.wiki-schema.md`**：在 6 处对应描述位置（status enum、confidence、page types 表、capture policy 字段、source_manifest.status、visibility enum）嵌入 `BEGIN/END GENERATED` 标记块；初始内容用 `--check-docs --fix` 生成，确保随后 `--check-docs` exit 0。块要嵌在既有可读上下文中，不破坏文档结构。

4. **M4 正则**：`BASE_SCHEMA` 默认 `soft_redact` 邮箱正则 `@[a-z]+\.com` → `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}`（ASCII，避免 `\w` Unicode 行为）；同步引擎 `knowledge/.wiki/capture_policy.json` 同一项。datawarehouse 不动。

5. **`scripts/README.md`**：补 `--check-docs` / `--fix` 用法、3 个错误码、exit code 与「普通 lint 不跑 docs checker」边界。

6. **测试 `tests/test_task_020a.py`**（unittest）：
   - `generate_doc_block` 确定性（同输入恒等输出、顺序固定）。
   - 对齐后 `--check-docs` exit 0。
   - 故意改某块一个 enum → exit 1 + `DOC_BLOCK_DRIFT`。
   - `--fix` 只改块内、不碰块外散文（块外文本逐字节不变）。
   - 缺 BEGIN/END → `DOC_BLOCK_MISSING`；重复块 → `DOC_BLOCK_DUPLICATE`。
   - 普通 `wiki_lint --check-only` 不运行 docs checker（不产生 doc 错误、不写多余派生层）。
   - M4：新正则匹配 `a.b+x@sub.example.cn` / 不破坏既有用例。

7. 跑验证 → commit（引擎一个 commit）。

## 验证

```bash
ENGINE=/Users/zhangjunwu/workspace/llm-wiki/llm-wiki
DW=/Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse
cd $ENGINE
CONDA="/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python"   # 仅示意，实际逐条用完整命令

/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest -v tests.test_task_020a
# 对齐后 docs 一致
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root knowledge --check-docs; echo "check-docs exit=$?"
# 普通 lint 不受影响、退出码独立
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root knowledge --check-only; echo "lint exit=$?"
# datawarehouse 回归（M4 不应影响：soft_redact []）
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root $DW --scan-wiki-pii; echo "dw pii exit=$?"
# 回归
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest tests.test_task_012 tests.test_task_013 tests.test_task_014 tests.test_task_015 tests.test_task_016a tests.test_task_016b tests.test_task_017 tests.test_task_019
```

## 完成后报告格式

- Step 0 spec-review 结论（含 visibility enum 在 BASE_SCHEMA 的确切位置）
- 改动文件 + 关键位置（generate_doc_block、--check-docs 分支、6 个 marker 块落点、M4 两处）
- 验证输出（fixture、check-docs exit 0、普通 lint 不跑 docs checker 的证据、datawarehouse 回归、回归套件）
- commit sha
- 偏离或异常

## Execution log by codex · <date>

（执行者填写）

## Evaluation by claude · <date>

（评估者填写）
