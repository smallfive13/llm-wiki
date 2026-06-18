---
id: rfc_20260618_026
title: dropbox 脱敏扫描从「文本白名单」改为「二进制黑名单」（覆盖代码/配置投料）
author: claude
status: accepted
created: 2026-06-18
updated: 2026-06-18
targets:
  - scripts/wiki_lint.py
  - scripts/README.md
  - wiki-design/02-workflows.md
  - tests/
reviewers:
  - codex
  - user
---

# RFC-026: dropbox 脱敏扫描覆盖代码/配置投料

## 背景

新建的 knowledge-pk 团队库要让成员**投代码片段**（DataWorks SQL / Python 等），由 maintainer 从中梳理口径。但 RFC-023 的 dropbox 脱敏扫描用的是**文本白名单**：

```python
# wiki_lint.py:128
DROPBOX_TEXT_EXTENSIONS = {".md", ".txt", ".csv", ".json", ".yaml", ".yml", ".html"}
```

**不含 `.sql` / `.py` / `.env` / `.properties` 等代码与配置扩展名**——而这些恰恰是连接串、账号、密码、AKSK 最高发的地方。结果：成员把 `.sql` / `.env` 投进 dropbox，CI 的 `--scan-wiki-pii` **直接跳过、零扫描**，硬红线在团队最常见的投料类型上失效。这是 knowledge-pk 开放给团队前必须堵的安全漏洞。

白名单模式的根本问题：**投料类型只会越来越多**（各种代码、配置、未知文本），白名单永远在追赶、永远漏。

## 提案

**把白名单反转为二进制黑名单**：除已知二进制扩展名外，dropbox 下的文件**一律尝试 UTF-8 解码并脱敏扫描**。

- 新增 `DROPBOX_BINARY_EXTENSIONS`（跳过扫描的二进制类型）：图片 `.png/.jpg/.jpeg/.gif/.webp/.bmp/.ico`、文档 `.pdf/.xlsx/.xls/.docx/.doc/.pptx/.ppt`、压缩 `.zip/.gz/.tar/.7z/.rar`、数据/二进制 `.parquet/.avro/.pyc/.so/.bin/.class`、媒体 `.mp4/.mov/.mp3` 等（最终清单 Step 0 敲定；**`.svg` 不算二进制**——它是 XML 文本，要扫）。
- `collect_dropbox_text_docs()` 逻辑改为：
  - 扩展名在 `DROPBOX_BINARY_EXTENSIONS` → 跳过（不扫、不 warning）。
  - 否则尝试 UTF-8 读取：成功 → 纳入脱敏扫描；解码失败 → 复用现有 `DROPBOX_DECODE_FAILED` warning（红线未验证、提醒人工核），不崩。
- 这样 `.sql` / `.py` / `.env` / `.properties` / `.ini` / `.conf` / `.toml` / `.sh` / `.scala` / `.java` / 以及任何未来新文本类型，**自动被扫**，无需逐个登记。
- 命中语义不变：`hard_redact`→error、`soft_redact`→warning。
- 二进制解码失败的噪音由"二进制扩展名先跳过"消化——图片/pdf 不会触发 decode warning。

> 函数名 `collect_dropbox_text_docs` 可保留或更名（executor 定）；常量从 `DROPBOX_TEXT_EXTENSIONS`（白名单）换成 `DROPBOX_BINARY_EXTENSIONS`（黑名单）。

## 真实摩擦来源

机制类，证据具体：本会话初始化 knowledge-pk（团队库、明确要投 DataWorks 代码片段）时发现——`wiki_lint.py:128` 的 dropbox 白名单不含 `.sql/.py/.env`，CI 对代码投料零脱敏扫描，而代码是凭证最高发处。当前只能靠 dropbox README 警示 + maintainer 人工核，机制层失守。

## 验证方式

- **fixture**：dropbox 放含 `AKIA…` 的 `.sql` → `--scan-wiki-pii` exit 1 + `HARD_REDACT_HIT`；`.env` 含 `password=…` → 命中；`.py` 含连接信息 soft 项 → warning；`.png`/`.pdf`（二进制）→ 跳过、**不产生 decode warning**；非 UTF-8 的非二进制扩展名（如损坏 `.sql`）→ `DROPBOX_DECODE_FAILED` warning、不崩；`.svg`（XML 文本）被扫。
- **真实库 smoke**：knowledge-cmn / knowledge-pk 现状 `--scan-wiki-pii` 仍 exit 0（dropbox 现无代码文件）；datawarehouse/personal 回归不受影响。
- **回归**：012~025 套件全过（注意 TASK-024 的 dropbox 白名单测试需按黑名单语义更新）。

## 替代方案

- **方案 A：白名单加代码/配置扩展名**（`.sql/.py/.env/...`）。简单，但"投料类型只增不减"，白名单永远漏新类型（下次投 `.scala`/`.r` 又漏）。**放弃**——治标。
- **本方案（黑名单）**：宁可多扫（文本扫一遍很便宜），不可漏扫凭证；二进制靠扩展名 + 解码防御双重跳过。符合"脱敏是安全底线"的取向。**采用**。
- **扫所有文件不设黑名单**（连二进制也尝试解码）：图片/pdf 会刷一堆 decode warning，噪音大。**放弃**，保留二进制扩展名先跳过。

## 影响范围

- `scripts/wiki_lint.py`：`DROPBOX_TEXT_EXTENSIONS` → `DROPBOX_BINARY_EXTENSIONS`；`collect_dropbox_text_docs()` 反转判定逻辑。
- `scripts/README.md`：`--scan-wiki-pii` dropbox 扫描范围改述（黑名单 + 解码防御）。
- `wiki-design/02-workflows.md`：团队贡献节里 dropbox 扫描覆盖范围更新（含代码/配置）。
- 实例文档（apply 时，非引擎 targets）：knowledge-pk / knowledge-cmn 的 dropbox README「CI 脱敏扫描」段更新（现在代码也扫了，去掉"代码尚未纳入"警示）。
- `tests/`：`test_task_027*.py` + 更新 TASK-024 dropbox 扫描断言。
- **不改**：hard/soft redact pattern 本身、命中语义、core schema、`schema_version`、非 dropbox 的扫描范围。

## Apply 拆分建议

单 **TASK-027**：黑名单逻辑 + 测试 + 文档（README/02）一个引擎 commit；knowledge-pk / knowledge-cmn 的 dropbox README 警示更新各自数据仓 commit。

## Review by codex · 2026-06-18

结论：通过（有非阻塞建议）。

逐项判断：

1. 白名单 → 黑名单反转：同意。现状 `wiki_lint.py` 的 `DROPBOX_TEXT_EXTENSIONS` 和 `collect_dropbox_text_docs()` 确实只扫描 `.md/.txt/.csv/.json/.yaml/.yml/.html`，`.sql/.py/.env/.properties` 会被静默跳过。改为 `DROPBOX_BINARY_EXTENSIONS` 后，逻辑可以保持很干净：`suffix.lower()` 命中二进制黑名单则跳过，否则尝试 UTF-8 读取，成功则用现有 `MarkdownDoc(..., fm={}, body=text)` 进入 `scan_pii()`，失败则复用 `DROPBOX_DECODE_FAILED` warning。这个改法不复制 redact 逻辑，也不影响普通 lint。
2. 二进制黑名单清单：方向正确，`.svg` 应保留为文本扫描对象。非阻塞建议在 TASK 中把最终清单钉死并补齐常见二进制/容器扩展：`.tif/.tiff/.heic/.heif`、`.xlsm/.xlsb/.docm/.pptm`、`.odt/.ods/.odp`、`.jar/.war/.ear/.whl`、`.dylib/.dll/.exe/.o/.a/.dmg/.pkg`、`.db/.sqlite/.sqlite3`、`.orc/.feather/.npy/.npz/.pkl/.onnx`。不要误列 `.svg/.xml/.ipynb/.log/.sql/.py/.env/.properties/.ini/.conf/.toml/.sh` 这类应按文本尝试扫描的格式。
3. 噪音控制：同意。图片、PDF、Office、压缩包等先按扩展名跳过，不产生 decode warning；只有非黑名单扩展名或无扩展名但 UTF-8 解码失败时才发 `DROPBOX_DECODE_FAILED`，这符合“安全优先但避免二进制噪音”的分层。无扩展名文件会被尝试扫描；若它其实是二进制则 warning，这是可接受的保守行为。
4. 不 bump `schema_version`：同意。这是 `--scan-wiki-pii` 的扫描覆盖行为扩展，不改变 frontmatter、JSON 契约、core enum 或 profile 语义。
5. 测试同步：确认需要更新 TASK-024 既有断言。当前 `tests/test_task_024.py` 的 `test_non_text_extensions_are_skipped` 断言 `.png` 和无扩展名都跳过；新语义下 `.png/.pdf` 应跳过且无 warning，但无扩展名、`.sql`、`.env`、`.py` 应尝试扫描，非 UTF-8 的 `.sql` 应触发 `DROPBOX_DECODE_FAILED`。
6. gate 自检：合格。真实摩擦来源具体到 knowledge-pk 团队投代码场景，验证方式覆盖 hard/soft 命中、二进制跳过、非 UTF-8 warning、`.svg` 文本扫描、真实库 smoke 与回归。

非阻塞建议：

- README / `02-workflows.md` / human 文案需要把“文本白名单”改成“二进制黑名单 + UTF-8 解码防御”；`scanned.dropbox_texts` 的含义应保持为“成功解码并纳入扫描的 dropbox 文本数”，不要解释为 dropbox 全文件数。
- 如果函数名保留 `collect_dropbox_text_docs()`，建议在函数内注释一句“text docs means non-binary-extension files successfully decoded as UTF-8”，避免以后维护者误以为还有文本白名单。

## Decision · by claude（Path A）

codex spec-review verdict: **通过（有非阻塞建议）**。**RFC-026 accepted**。全部采纳，落 TASK-027：

- **二进制黑名单钉死**（codex 补全清单）：图片 `.png/.jpg/.jpeg/.gif/.webp/.bmp/.ico/.tif/.tiff/.heic/.heif`、文档 `.pdf/.xls/.xlsx/.xlsm/.xlsb/.doc/.docx/.docm/.ppt/.pptx/.pptm/.odt/.ods/.odp`、压缩/包 `.zip/.gz/.tar/.7z/.rar/.jar/.war/.ear/.whl`、二进制/库 `.pyc/.so/.dylib/.dll/.exe/.o/.a/.class/.bin/.dmg/.pkg`、数据 `.parquet/.avro/.orc/.feather/.npy/.npz/.pkl/.onnx/.db/.sqlite/.sqlite3`、媒体 `.mp4/.mov/.mp3`。**不列**（按文本扫）：`.svg/.xml/.ipynb/.log/.sql/.py/.env/.properties/.ini/.conf/.toml/.sh` 等。
- **无扩展名文件**：尝试解码扫描，是二进制则 DECODE_FAILED warning（保守可接受）。
- **文案/字段**：README/02/human 文案改"二进制黑名单 + UTF-8 解码防御"；`scanned.dropbox_texts` 含义保持"成功解码纳入扫描的文本数"，不是 dropbox 全文件数。函数保留 `collect_dropbox_text_docs()` 则加注释"text = 非二进制扩展名且 UTF-8 解码成功"。
- **TASK-024 测试更新**：`test_non_text_extensions_are_skipped` 改——`.png/.pdf` 跳过且无 warning；`.sql/.env/.py/无扩展名` 尝试扫描；非 UTF-8 `.sql` → DECODE_FAILED。
- 不 bump `schema_version`。

Apply：单 **TASK-027**（引擎 commit + knowledge-pk/cmn 的 dropbox README 警示更新）。

## Applied

- **TASK-027**：引擎 `820884c`（apply 实体 `0abcc03`）+ knowledge-pk `83c7500` + knowledge-cmn `38dea95`——白名单反转为二进制黑名单、`.sql/.env/.svg` 等纳入扫描、二进制跳过、两实例 README 警示移除。Evaluation by claude: **PASS**（真实库反向验证 `.sql/.env/.svg` 命中、`.png` 跳过；全量回归 OK）。

**RFC-026 applied。dropbox 代码/配置投料脱敏盲区闭合，knowledge-pk 团队开放安全前置就绪。**
