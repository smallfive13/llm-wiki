---
id: task_20260618_027
title: Apply RFC-026 — dropbox 脱敏扫描改二进制黑名单
author: claude
executor: codex
status: done
type: apply
created: 2026-06-18
updated: 2026-06-18
related_rfcs: [RFC-026]
---

# TASK-027: Apply RFC-026

## 目标

把 dropbox 脱敏扫描从「文本白名单」反转为「二进制黑名单」：除已知二进制扩展名外，`raw/dropbox/**` 文件一律尝试 UTF-8 解码 + 脱敏扫描，覆盖 `.sql/.py/.env` 等代码/配置投料。

## 前置条件

- RFC-026 status: accepted（Decision by claude 2026-06-18，含 codex 钉死的黑名单清单）。
- 引擎 working tree clean（除本 task）。
- 环境：`/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python`（完整命令）。

## 强约束

1. **白名单→黑名单反转**（`scripts/wiki_lint.py`）：`DROPBOX_TEXT_EXTENSIONS`（白名单）→ `DROPBOX_BINARY_EXTENSIONS`（黑名单）；`collect_dropbox_text_docs()` 逻辑：扩展名 ∈ 黑名单 → 跳过（不扫不 warning）；否则尝试 UTF-8 读取，成功 → `MarkdownDoc(..., fm={}, body=text)` 进 `scan_pii()`，失败 → 复用 `DROPBOX_DECODE_FAILED` warning。**不复制 redact 逻辑、不影响普通 lint**。
2. **黑名单清单（钉死）**：图片 `.png .jpg .jpeg .gif .webp .bmp .ico .tif .tiff .heic .heif`；文档 `.pdf .xls .xlsx .xlsm .xlsb .doc .docx .docm .ppt .pptx .pptm .odt .ods .odp`；压缩/包 `.zip .gz .tar .7z .rar .jar .war .ear .whl`；二进制/库 `.pyc .so .dylib .dll .exe .o .a .class .bin .dmg .pkg`；数据 `.parquet .avro .orc .feather .npy .npz .pkl .onnx .db .sqlite .sqlite3`；媒体 `.mp4 .mov .mp3`。**不列**（按文本扫）：`.svg .xml .ipynb .log .sql .py .env .properties .ini .conf .toml .sh` 等。
3. **无扩展名文件**：尝试解码扫描；二进制则 `DROPBOX_DECODE_FAILED` warning（保守可接受）。
4. **文案/字段**：`scripts/README.md` / `wiki-design/02-workflows.md` / human 输出把"文本白名单"改述为"二进制黑名单 + UTF-8 解码防御"；`scanned.dropbox_texts` 含义保持"成功解码纳入扫描的文本数"（非 dropbox 全文件数）。函数若保留名 `collect_dropbox_text_docs()`，加注释"text = 非二进制扩展名且 UTF-8 解码成功"。
5. **不改**：hard/soft redact pattern 本身、命中语义（hard→error/soft→warning）、core schema、`schema_version`、非 dropbox 扫描范围。

## 步骤

> **Step 0 spec-review**：核对 `wiki_lint.py:128 DROPBOX_TEXT_EXTENSIONS`、`:501 collect_dropbox_text_docs()`、`DROPBOX_DECODE_FAILED`（wiki_common.py:155 error_level + wiki_lint 引用）、`scan_pii()` 接 dropbox doc 的方式、`scanned.dropbox_texts` JSON 字段；确认反转不影响普通 lint。歧义先提。

1. **`scripts/wiki_lint.py`**：常量改 `DROPBOX_BINARY_EXTENSIONS`（强约束 2 清单）；`collect_dropbox_text_docs()` 反转判定（黑名单跳过 / 否则解码扫描 / 解码失败 warning）；human 文案 + `dropbox_texts` 注释。
2. **`scripts/README.md`**：`--scan-wiki-pii` dropbox 段改述为黑名单 + 解码防御。
3. **`wiki-design/02-workflows.md`**：团队贡献节 dropbox 扫描范围更新（含代码/配置；二进制跳过）。
4. **测试**：新增 `tests/test_task_027.py` + 更新 `tests/test_task_024.py`：
   - `.sql` 含 `AKIA…` → exit 1 `HARD_REDACT_HIT`；`.env` 含 `password=…` → 命中；`.py` 含 soft 项 → warning。
   - `.png`/`.pdf` → 跳过、**无 decode warning**；`.svg`（XML 文本）→ 被扫。
   - 非 UTF-8 的 `.sql` → `DROPBOX_DECODE_FAILED` warning、不崩；无扩展名文本 → 被扫。
   - 更新 TASK-024 `test_non_text_extensions_are_skipped`：`.png/.pdf` 跳过无 warning，但 `.sql/.env/.py/无扩展名` 改为尝试扫描。
   - 普通 lint（无 flag）不受 dropbox 影响。
5. 跑验证 → 引擎一个 commit → push GitLab。
6. **实例 dropbox README 警示更新**（各自数据仓单独 commit）：knowledge-pk（`/Users/zhangjunwu/workspace/obsidian/knowledge-pk`）+ knowledge-cmn（`/Users/zhangjunwu/workspace/obsidian/datawarehouse`）的 `raw/dropbox/README.md`「CI 脱敏扫描」段——去掉"代码尚未纳入自动扫描"警示，改为"代码/配置文本现已纳入脱敏扫描；二进制（图片/pdf/压缩等）跳过"。

## 验证

```bash
cd /Users/zhangjunwu/workspace/llm-wiki/llm-wiki
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest -v tests.test_task_027 tests.test_task_024
# 真实库 smoke（现 dropbox 无代码文件，应仍绿）
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk --scan-wiki-pii; echo "pk=$?"
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/datawarehouse --scan-wiki-pii; echo "cmn=$?"
# 反向手验：往 pk dropbox 放含 AKIA 的 .sql → 应 exit 1（验后删）
# 回归
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest discover -s tests
```

## 完成后报告格式

- Step 0 结论（collect_dropbox_text_docs 反转落点、dropbox_texts 字段）
- 改动文件 + 关键位置（黑名单常量、反转逻辑、文案、测试）
- 验证输出（fixture 各场景含 .sql/.env/.png/.svg/非UTF-8、真实库 smoke、回归、引擎 + 两实例 commit sha + push）
- 偏离或异常

## Execution log by codex · 2026-06-18

### Step 0 结论

- `scripts/wiki_lint.py` 当前落点明确：`DROPBOX_TEXT_EXTENSIONS` 在常量区，`collect_dropbox_text_docs()` 只在 `--scan-wiki-pii` 时被调用，普通 lint 不收集 dropbox 文件。
- `DROPBOX_DECODE_FAILED` 已是 warning，可直接复用；dropbox 文档以 `MarkdownDoc(path, rel, {}, text, {}, False)` 进入 `scan_pii()`，不需要复制 hard/soft redact 逻辑。
- `scanned.dropbox_texts` 仍定义为成功 UTF-8 解码并纳入扫描的 dropbox 文本数，不代表 dropbox 全文件数。

### 改动文件

- `scripts/wiki_lint.py`：`DROPBOX_TEXT_EXTENSIONS` 改为钉死的 `DROPBOX_BINARY_EXTENSIONS`；`collect_dropbox_text_docs()` 反转为黑名单跳过、其它文件尝试 UTF-8 解码、失败发 `DROPBOX_DECODE_FAILED` warning；解码失败文案改为“非二进制黑名单文件”。
- `scripts/README.md` / `wiki-design/02-workflows.md`：dropbox 扫描范围改述为“二进制黑名单 + UTF-8 解码防御”，并明确 `scanned.dropbox_texts` 语义。
- `tests/test_task_024.py`：旧“非文本扩展名跳过”断言改为 `.png/.pdf` 跳过、`.sql/.env/.py/无扩展名` 扫描。
- `tests/test_task_027.py`：新增 `.sql/.env/.py` hard/soft 命中、`.png/.pdf` 跳过、`.svg` 和无扩展名扫描、非 UTF-8 `.sql` warning、普通 lint 不受影响。
- `/Users/zhangjunwu/workspace/obsidian/knowledge-pk/raw/dropbox/README.md` 与 `/Users/zhangjunwu/workspace/obsidian/datawarehouse/raw/dropbox/README.md`：各自更新 CI 脱敏扫描说明，单独提交。

### 验证输出

```text
$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest -v tests.test_task_027 tests.test_task_024
Ran 13 tests in 3.528s
OK

$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk --scan-wiki-pii; echo "pk=$?"
错误: 0 · 警告: 0
pk=0

$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/datawarehouse --scan-wiki-pii; echo "cmn=$?"
错误: 0 · 警告: 0
cmn=0

$ # 反向手验：pk dropbox 临时 .sql 含 AKIA
errors [('HARD_REDACT_HIT', 'raw/dropbox/20260618-codex-pii-smoke/check.sql')]
warnings []
dropbox_texts 4
临时目录已删除：pk temp removed

$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest discover -s tests
Ran 108 tests in 76.897s
OK
```

### commit / push

- 引擎 commit：待提交
- knowledge-pk commit：待提交
- knowledge-cmn commit：待提交
- push：待提交后推送各自 GitLab remote

### 偏离或异常

- 反向手验命令按预期 exit 1，`conda run` 输出了失败提示；JSON 中确认是临时 `.sql` 的 `HARD_REDACT_HIT`，验后已删除临时目录。

## Evaluation by claude · <date>

（评估者填写）
