---
id: task_20260604_016c
title: Apply RFC-016 数据对齐 — datawarehouse 已 ingest 产物对齐最终规范
author: claude
executor: codex
status: pending
type: apply
created: 2026-06-04
updated: 2026-06-04
related_rfcs: [RFC-016]
---

# TASK-016c: datawarehouse 数据对齐

## 目标

把 datawarehouse 06-04 已 ingest 的产物对齐 RFC-016 最终规范：补 `visibility`、清理旧集合 source、确认图引用过 016b lint、核对图的多模态描述。**纯数据动作**（外部实例迁移），在数据仓单独提交，不混引擎 apply。

## 前置条件

- TASK-016a + TASK-016b done（visibility/脱敏/图校验规则已落地）。
- datawarehouse 数据仓 working tree clean（先确认 06-04 那批产物已提交；若未提交，先让用户/执行者提交基线）。

## 强约束

1. **纯数据动作**：只改 datawarehouse 实例数据（wiki 页 / source_manifest / capture_policy），不改引擎 scripts。
2. **append/迁移要可追溯**：source 清理用 `supersedes`/`status: archived`，不硬删（保留审计）。
3. **在数据仓提交**，报告外部 git 状态，不进引擎仓。

## 步骤

> Step 0：先 `git -C <数据仓> status` 确认 06-04 产物已是干净基线（17 source + 75 图 + 13 知识页）。不干净先提交基线再开工。

1. **补 visibility**：
   - `capture_policy.default_visibility: internal`（016a 可能已做；确认）。
   - 各 source（source_manifest + source 页 frontmatter）+ 各 wiki 页：按需显式标 `visibility: internal`（或依赖库默认继承——二选一，记录策略；建议依赖默认、只在例外页显式标，避免冗余）。

2. **清理旧集合 source**（用户决策"清理"）：
   - 旧集合 `src_20260603_international-data-service-tech-docs`：标 `status: archived` + `superseded_by`（指向 17 个细粒度 source，或指向 synthesis 门户，择一记录）。
   - 把仍引用集合 source_id 的 ~18 页的 `source_ids` 改指对应**细粒度 source**（按主题对应）。
   - source_manifest 里旧集合条目 status 改 `superseded`（若 enum 不支持则 `archived` + 备注）。

3. **图引用过 016b lint**：跑 016b 的图引用校验,现有 75 张图的相对引用应全部解析（无 `IMAGE_DANGLING`）；若有断引（路径口径不符）→ 修引用路径使其符合 016b 校验。

4. **核对图描述**：抽查图的多模态描述（语义 + 关键文字）是否到位；缺的按需补（写入 AI 多模态）。OCR 全文不强求（原图保底）。

5. 跑校验 → 数据仓提交 → 报告。

## 验证

```bash
ENGINE=/Users/zhangjunwu/workspace/llm-wiki/llm-wiki
PY="/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python"
DW=/Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse

cd $ENGINE
$PY scripts/wiki_lint.py --root $DW          # exit 0，无 IMAGE_DANGLING、无旧集合悬挂引用
$PY scripts/wiki_graph.py --root $DW          # 0 dangling
$PY scripts/wiki_eval.py --root $DW --json    # score 合理（visibility 不影响 score）
# 确认旧集合 source 不再被任何页 source_ids 引用（除其自身 superseded 链）
grep -rl 'src_20260603_international-data-service-tech-docs' $DW/wiki | grep -v sources/international || echo "OK 无悬挂引用"
```

## 完成后报告格式

- Step 0 基线确认（06-04 产物 git 状态）
- visibility 策略（显式 vs 继承）+ 改了哪些
- 旧集合 source 清理：archived/superseded + 改了哪些页的 source_ids
- 图引用 lint 结果（IMAGE_DANGLING 数）+ 图描述核对
- 数据仓 commit sha + 外部 git 状态
- 偏离或异常

## Execution log by codex · <date>

（执行者填写）

## Evaluation by claude · <date>

（评估者填写）
