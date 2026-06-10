---
id: task_20260610_024
title: Apply RFC-023 — dropbox 脱敏扫描 + 团队贡献协议进 02-workflows
author: claude
executor: codex
status: done
type: apply
created: 2026-06-10
updated: 2026-06-10
related_rfcs: [RFC-023]
---

# TASK-024: Apply RFC-023

## 目标

落地 RFC-023：M2 `wiki_lint --scan-wiki-pii` 扩展覆盖 `raw/dropbox/**` 文本（仅 redact 扫描）+ M1 团队贡献协议写入 `wiki-design/02-workflows.md`；`knowledge-cmn` 实例文档对齐（如有出入）。

## 前置条件

- RFC-023 status: accepted（Decision by claude 2026-06-10，含已采纳的 codex 非阻塞建议）。
- 引擎 working tree clean（除本 task）；`knowledge-cmn` 本地 clone `/Users/zhangjunwu/workspace/obsidian/datawarehouse` clean。
- 环境：`/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python`（完整命令，勿塞 zsh 变量）。

## 强约束

1. **扫描范围**：`--scan-wiki-pii` 时新增 `raw/dropbox/**` 文本文件组；**普通 lint（无 flag）行为完全不变**；`raw/sources/` 不纳入。
2. **扩展名白名单固定**：`.md` / `.txt` / `.csv` / `.json` / `.yaml` / `.yml` / `.html`；其余（图片 / pdf / office / 无后缀）跳过，不报错。
3. **解码策略钉死**：UTF-8 解码失败 → **跳过该文件 + 记 warning**（语义：红线未验证，提醒 maintainer 人工查看）；**不得抛未捕获异常**。
4. **dropbox 文件不是 wiki 页**：不做任何 schema / frontmatter / ID 校验，只跑 redact 扫描；接入方式用轻量 doc（`fm={}`，visibility 走 `effective_visibility(None, capture_policy)` 继承库默认）——复用现有 `scan_pii()`，不复制 redact 逻辑。
5. **命中语义不变**：`hard_redact` → error、`soft_redact` → warning；错误码沿用现有（`HARD_REDACT_HIT` / PII 系列），不新增错误码体系。
6. **human 文案按实际范围写**：Step 0 核实 archive 是否实扫，「脱敏扫描」行据实标注（如 `inbox/archive + wiki + dropbox`）。
7. **不 bump `schema_version`**（codex review 已确认：lint 行为扩展，不动 core 契约）；不改 graph / eval / manifest 结构。
8. **两仓 commit 分开**：引擎改动一个 commit（含推送 GitLab）；`knowledge-cmn` 文档对齐（若需）单独实例仓 commit + push。

## 步骤

> **Step 0 spec-review**：核对 `scan_pii()` 签名与内部对 doc 的使用面（`path.read_text` / `rel` / `fm.get("visibility")`）、`scan_markdown_files()` 是否适合复用或需单独收集 dropbox 文件、archive 组在 `--scan-wiki-pii` 下是否实扫（决定文案）、`MarkdownDoc` 结构能否以 `fm={}` 安全实例化。发现歧义先提。

1. **`scripts/wiki_lint.py`**：
   - `--scan-wiki-pii` 分支下收集 `raw/dropbox/**` 白名单扩展名文本文件，构造轻量 doc 接入 `scan_pii()`（或等价重构，保持单一 redact 实现）。
   - UTF-8 解码失败 → warning（说明文件 + 原因 + "请人工核查红线"）+ 跳过。
   - human「脱敏扫描」行按实际范围更新；`--json` 输出如有 pii 计数字段保持一致语义。
2. **`scripts/README.md`**：`--scan-wiki-pii` 范围说明更新（含 dropbox、白名单、解码失败语义）。
3. **`wiki-design/02-workflows.md`**：新增「团队贡献（投料 → MR → CI → 单 writer ingest）」节，内容按 RFC-023 M1 全量落（角色表 / 投料约定 / GitLab 机制要求 / 单 writer ingest 节奏 / dropbox 队列语义——**含 ingest 移位后 manifest `original_path` 更新 + `hash_sha256` 重算确认** / 扩 maintainer 条件）。
4. **测试 `tests/test_task_024.py`**（unittest，fixture 实例含 dropbox）：
   - dropbox 含 `AKIA...` 的 `.md` → `--scan-wiki-pii` exit 1 + hard 命中。
   - soft 项（如邮箱，fixture 库 soft_redact 非空 + `default_visibility: internal`）→ warning（覆盖 visibility 继承表现）。
   - 干净 dropbox → 0 命中 exit 0。
   - 白名单外文件（`.png` / 无后缀）跳过不报错。
   - **非 UTF-8 文件**（如写入 GBK / 随机字节的 `.txt`）→ warning + 不 crash。
   - 普通 lint（无 flag）完全不受 dropbox 内容影响（含红线内容也不报）。
   - `--check-only` 行为不变。
5. **`knowledge-cmn` 对齐**（实例仓）：比对 `AGENTS.md` / `raw/dropbox/README.md` 与 02 定版措辞，有出入则对齐（如 ingest 移位语义、扩展名/解码提示可选加入 README）；无出入则记录"无需改动"。
6. 跑验证 → 引擎 commit + push GitLab；实例仓（若有改动）单独 commit + push。

## 验证

```bash
cd /Users/zhangjunwu/workspace/llm-wiki/llm-wiki
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest -v tests.test_task_024
# 真实库 smoke：knowledge-cmn（dropbox 现仅 README/.gitkeep）
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/datawarehouse --scan-wiki-pii; echo "cmn pii=$?"
# personal 回归
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/knowledge/personal --scan-wiki-pii; echo "personal pii=$?"
# 引擎自检 + check-docs 不破
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root knowledge --check-only; echo "lint=$?"
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root knowledge --check-docs; echo "check-docs=$?"
# 回归
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest tests.test_task_012 tests.test_task_013 tests.test_task_014 tests.test_task_015 tests.test_task_016a tests.test_task_016b tests.test_task_017 tests.test_task_019 tests.test_task_020a tests.test_task_021a tests.test_task_021b tests.test_task_022
# CI 端到端（用户配合）：引擎 push 后，在 knowledge-cmn 提含 AKIA fixture 的测试 MR → pipeline 应红；删除后绿
```

## 完成后报告格式

- Step 0 结论（scan_pii 接入面、archive 实扫与否与文案决定）
- 改动文件 + 关键位置（dropbox 收集 / 轻量 doc / 解码 warning / 02 节落点 / knowledge-cmn 对齐与否）
- 验证输出（fixture 7 场景、两真实库 smoke、check-docs、回归、引擎与实例仓 commit sha + push 记录）
- 待用户事项（GitLab 测试 MR 红/绿确认）
- 偏离或异常

## Execution log by codex · 2026-06-10

### Step 0 结论

- `scan_pii()` 的 doc 使用面为 `doc.path.read_text(encoding="utf-8")`、`doc.rel`、`doc.fm.get("visibility")`；dropbox 文本可用轻量 `MarkdownDoc(path, rel, fm={}, body=text, line_map={}, has_frontmatter=False)` 接入，不需要 schema/frontmatter 校验。
- `scan_markdown_files()` 只适合 wiki/inbox；dropbox 需要单独收集 `raw/dropbox/**` 白名单扩展名文本。
- archive 组在普通 lint 与 `--scan-wiki-pii` 下都实扫：`scan_pii()` 无条件扫描 `inbox_docs` 和 `archived_docs`，`scan_wiki=True` 时再扫描 `wiki_docs`。因此 human 文案落为普通模式 `inbox/archive`，`--scan-wiki-pii` 模式 `inbox/archive + wiki + dropbox`。
- `MarkdownDoc` 结构可安全实例化；dropbox `fm={}` 会通过 `effective_visibility(None, capture_policy)` 继承库默认 visibility。
- 解码失败缺少合适既有 warning code；新增 `DROPBOX_DECODE_FAILED` 为 warning，不 bump `schema_version`，只表达 dropbox 文本未验证。

### 改动文件

- `scripts/wiki_lint.py`
  - 新增 `DROPBOX_TEXT_EXTENSIONS`：`.md` / `.txt` / `.csv` / `.json` / `.yaml` / `.yml` / `.html`。
  - 新增 `collect_dropbox_text_docs()`：只在 `--scan-wiki-pii` 下收集 `raw/dropbox/**` 白名单文本；UTF-8 解码失败时记 `DROPBOX_DECODE_FAILED` warning 并跳过。
  - 扩展 `scan_pii()` 参数，dropbox 复用同一套 hard/soft redact 逻辑，不复制扫描实现。
  - JSON `scanned` 增加 `dropbox_texts`，普通 lint 下为 0。
  - human「脱敏扫描」范围文案改为实际范围。
- `scripts/wiki_common.py`
  - `BASE_SCHEMA.error_level` 增加 `DROPBOX_DECODE_FAILED: warning`。
- `scripts/README.md`
  - 更新 `--scan-wiki-pii` 范围、dropbox 白名单、UTF-8 解码失败语义和 error code 表。
- `wiki-design/02-workflows.md`
  - 新增「团队贡献」节：角色、投料约定、GitLab 机制、单 writer ingest、dropbox 队列语义、扩 maintainer 条件、dropbox 脱敏扫描。
  - 明确 ingest 移位后同步更新 manifest `original_path`，并重算或确认 `hash_sha256`。
- `tests/test_task_024.py`
  - 新增 7 个 fixture 场景。
- `knowledge-cmn`
  - 对齐 `raw/dropbox/README.md`：补 ingest 后归档、CI 脱敏扫描、UTF-8 解码 warning；同时把 README 自身 hard_redact 触发词改为不触发的概括表达。

### 验证输出

```text
$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest -v tests.test_task_024
test_check_only_does_not_write_derived_layers ... ok
test_clean_dropbox_has_no_hits ... ok
test_dropbox_hard_redact_blocks_scan_wiki_pii ... ok
test_dropbox_soft_redact_warns_and_inherits_default_visibility ... ok
test_non_text_extensions_are_skipped ... ok
test_non_utf8_text_file_warns_without_crashing ... ok
test_plain_lint_ignores_dropbox_even_when_it_contains_hard_redact ... ok

Ran 7 tests in 2.315s
OK
```

```text
$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/datawarehouse --scan-wiki-pii; echo "cmn pii=$?"
扫描: datawarehouse/wiki/ (33 文件) · datawarehouse/inbox/ (0 draft) · datawarehouse/raw/ (18 source)
脱敏扫描（inbox/archive + wiki + dropbox）: 0 命中
错误: 0 · 警告: 0
cmn pii=0
```

```text
$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/knowledge/personal --scan-wiki-pii; echo "personal pii=$?"
扫描: personal/wiki/ (11 文件) · personal/inbox/ (0 draft) · personal/raw/ (0 source)
脱敏扫描（inbox/archive + wiki + dropbox）: 1 命中
详细警告:
  [WARN] SOFT_REDACT_HIT wiki/topics/knowledge-organization.md:72 -: 命中 soft_redact pattern '客户(姓名|名单|信息)'
错误: 0 · 警告: 1
personal pii=0
```

```text
$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root knowledge --check-only; echo "lint=$?"
脱敏扫描（inbox/archive）: 0 命中
错误: 0 · 警告: 0
lint=0
```

```text
$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root knowledge --check-docs; echo "check-docs=$?"
受管块: 6
错误: 0
check-docs=0
```

```text
$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest tests.test_task_012 tests.test_task_013 tests.test_task_014 tests.test_task_015 tests.test_task_016a tests.test_task_016b tests.test_task_017 tests.test_task_019 tests.test_task_020a tests.test_task_021a tests.test_task_021b tests.test_task_022
Ran 80 tests in 58.170s
OK
```

```text
$ git diff --check && git -C /Users/zhangjunwu/workspace/obsidian/datawarehouse diff --check
(no output)
```

### commit sha

- `knowledge-cmn` 对齐 commit：`5975c59dd377bd8ac78f26b1e41cdff94ffb61e7`（已 push）
- 引擎 commit：见最终报告（待本 Execution log 提交后生成并 push）

### 待用户事项

- 引擎 push 后，在 `knowledge-cmn` 提一个含 hard_redact fixture 的测试 MR，确认 pipeline 红；删除 fixture 后确认 pipeline 绿。

### 偏离或异常

- 首次跑 `knowledge-cmn --scan-wiki-pii` 时发现 `raw/dropbox/README.md` 自身包含 hard_redact 触发词，导致 `HARD_REDACT_HIT`。已作为 Step 5 实例文档对齐修复：README 改为引用 `purpose.md` 完整红线，并补入 ingest 归档与 CI 扫描说明。
- 新增 `DROPBOX_DECODE_FAILED` warning code。原因是现有错误码没有能准确表达"dropbox 白名单文本解码失败但 lint 不应阻断"的 warning；该改动是 lint 行为扩展，不改 core schema，不 bump `schema_version`。

## Evaluation by claude · 2026-06-10

**Verdict: PASS。** 独立复跑 + 真实库端到端反向验证，M1 / M2 均达标，RFC-023 闭环。

### 独立复跑

| 验证 | 结果 |
| --- | --- |
| `unittest tests.test_task_024` | 7 tests OK |
| **端到端反向验证（真实库）** | 往 `knowledge-cmn` dropbox 放 `AKIA...` 文件 → `--scan-wiki-pii` **exit 1 + `HARD_REDACT_HIT` 精确到文件行号**；删除后恢复 exit 0——**CI 盲区闭合实锤** |
| knowledge-cmn / personal smoke | exit 0 / exit 0（warning 见下） |
| `--check-docs` | exit 0（BASE_SCHEMA error_level 新增不破生成块） |
| 回归 020a/021a/021b/022 | OK |
| `02-workflows.md:171` | 「团队贡献」节就位（角色 / 投料 / GitLab 机制 / 单 writer / 队列语义含 original_path+hash / 扩权条件） |
| 两仓 | 引擎 `0c08e3b`、knowledge-cmn `5975c59`，均 clean 且已推送 |

### 核查点

1. **复用单一 redact 实现**：dropbox 走轻量 doc 接入 `scan_pii()`，未复制扫描逻辑；普通 lint 完全不受 dropbox 影响（专测覆盖，含红线内容也不报）。
2. **解码防御**：非 UTF-8 → `DROPBOX_DECODE_FAILED` warning + 跳过，不 crash（fixture 覆盖）。
3. **文案按实际范围**：Step 0 核实 archive 实扫，落为 `inbox/archive + wiki + dropbox`——准确。

### 偏离评估（合理）

- **新增错误码 `DROPBOX_DECODE_FAILED`**（强约束 5 写"不新增错误码体系"）：Step 0 预先声明——解码失败是新场景、PII 系列码语义不适配，新增 warning 级专码且不 bump `schema_version`。**合理**：错误码新增不影响 profile 兼容与实例数据契约（同 RFC-020 加 `DOC_BLOCK_*` 先例），实例零迁移。
- knowledge-cmn README 顺手把自身的 hard_redact 触发词改为概括表达——正确（避免 README 自己挡 CI）。

### 额外发现（非本 task 引入）

personal `knowledge-organization.md:72` 有一条 `SOFT_REDACT_HIT` warning："讨论脱敏规则的句子"（capture_policy 加客户信息正则）命中了 `客户(姓名|名单|信息)` pattern——同 datawarehouse 处理过的"规则说明误报"，且该句还在用 legacy 词 `exclude_patterns`。warning 级不挡，由 claude 评估后顺手修复 personal 措辞。

### 结论

RFC-023 **全部闭环**：团队贡献协议入引擎正本（02-workflows）、dropbox 红线扫描盲区闭合且 CI 零改动自动获益。团队开放链路（投料 → MR → CI → 单 writer ingest）机制与文档双就位。TASK-024 done 确认有效。**待用户**：在 GitLab 提含 AKIA fixture 的测试 MR 确认 pipeline 红→绿（端到端本地已等价验证）。
