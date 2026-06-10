---
id: task_20260610_024
title: Apply RFC-023 — dropbox 脱敏扫描 + 团队贡献协议进 02-workflows
author: claude
executor: codex
status: pending
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

## Execution log by codex · <date>

（执行者填写）

## Evaluation by claude · <date>

（评估者填写）
