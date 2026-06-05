---
id: task_20260604_019
title: Apply RFC-019 — ingest 批量编排（lint ingest 进度段 + 流程文档）
author: claude
executor: codex
status: pending
type: apply
created: 2026-06-05
updated: 2026-06-05
related_rfcs: [RFC-019]
---

# TASK-019: Apply RFC-019 — ingest 批量编排

## 目标

落地 RFC-019：`wiki_lint` 加只读「ingest 进度」段（从 `source_manifest.status` 派生，作 apply 清单）+ `--ingest-status` 模式；并把"triage 全量 → apply 逐份 → 每份 commit → 断点续传"编排写进流程文档。

## 前置条件

- RFC-019 status: accepted（Decision by claude 2026-06-05）。
- working tree clean（除本 task）。
- 环境：`conda run -n py312 python`。

## 强约束

1. **进度段纯读 manifest、不改校验逻辑/退出码**：普通 lint 新增进度段不影响 error/warning 判定。
2. 不改 `source_manifest` 字段 / status enum（复用 RFC-017 现值）；不动 graph/eval、core schema。
3. triage/apply 编排是**写入 AI 约定**（流程文档），不是工具强制。

## 步骤

> Step 0 spec-review：核对 `wiki_lint.run_lint()` 拿到 `source_manifest` 的位置、`data` 结构（现只暴露 `scanned.sources`）、`human_output()` 渲染点、`configure()`；确认进度段能插入；发现歧义先提。

1. **`wiki_lint.py` — ingest 进度（结构化优先）**：
   - 聚合 `source_manifest.sources[*].status` → `data["ingest_progress"]`：**全量 status count**（new/triaged/ingested/skipped/failed/deleted/superseded/archived）+ `pending_apply`（**只取 `triaged`**）列表（每项 `source_id`/`title`/`status`/`summary_page_path`，按 manifest 原顺序）。
   - `human_output()` 渲染「ingest 进度」段：计数 + 待 apply 列表（默认截断前 20）。
   - `--json` 输出含 `ingest_progress`。

2. **`wiki_lint.py` — `--ingest-status` 模式**：
   - 走 `configure()` + JSON 读取/基本校验，**只输出 ingest 进度段、不写派生层**；待 apply 列表全量（不截断）。
   - exit code：manifest 读取或 schema error → 1，否则 0。
   - `--json --ingest-status` → 固定 JSON（只含 `ingest_progress` + 少量元信息，不混人类文本）。

3. **`wiki_common.py`**：如需，加聚合 helper（纯函数，便于 fixture 直测）。

4. **流程文档**：
   - `wiki-design/02-workflows.md`：ingest 改批量编排——**triage 全量定义写硬**（目录/元信息级：manifest/hash/标题/source_type/粗摘要或占位 + alias 候选；**不读所有长正文、不图多模态、不写详细正文**）→ apply 清单（lint 进度段）→ **apply 逐份**（≤3 仅短小同质；含图/子链接/长正文逐份）→ **状态转换顺序**（triaged → 写完+lint 通过 → ingested + commit；失败 failed + notes）→ 每份 commit + 断点续传。
   - `wiki-design/04-agent-rules.md`：Agent 批量 ingest 约定（apply 严禁一次吞多份；triage 轻扫不读长正文）。
   - `knowledge/.wiki-schema.md`：批量编排约定（`--sync-schema` 到实例）。
   - `skill/wiki/references/schema.md`：skill 侧 ingest 指令同步。

5. **测试**（unittest，直测聚合函数 + CLI）：
   - 空 manifest → progress 全 0、pending_apply []。
   - 全 ingested → pending_apply []。
   - 混合 triaged/failed/ingested → count 正确、pending_apply 只列 triaged（不含 new/failed）。
   - 非法 status → 既报既有 enum error，又尽力生成 progress（不崩）。
   - `--ingest-status` 不写派生层（运行前后 `.wiki/*`、`maps/*` 不变）。

6. 跑验证 → commit（引擎一个 commit；文档/衍生同步含其中或分开）。

## 验证

```bash
ENGINE=/Users/zhangjunwu/workspace/llm-wiki/llm-wiki
PY="/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python"
DW=/Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse

cd $ENGINE && $PY -m unittest -v tests.test_task_019
# datawarehouse（全 ingested + 1 superseded）：进度段 pending_apply 应为 0
$PY scripts/wiki_lint.py --root $DW --ingest-status
$PY scripts/wiki_lint.py --root $DW --ingest-status --json
# 普通 lint 仍 exit 0、退出码不受进度段影响
$PY scripts/wiki_lint.py --root $DW --check-only; echo "exit=$?"
# 回归
$PY -m unittest tests.test_task_012 tests.test_task_013 tests.test_task_014 tests.test_task_015 tests.test_task_016a tests.test_task_016b tests.test_task_017
```

## 完成后报告格式

- Step 0 spec-review 结论
- 改动文件 + 关键位置（ingest_progress 聚合、--ingest-status、流程文档落点）
- 验证输出（fixture、datawarehouse 进度段 human+json、不写派生层证据、回归）
- commit sha
- 偏离或异常

## Execution log by codex · <date>

（执行者填写）

## Evaluation by claude · <date>

（评估者填写）
