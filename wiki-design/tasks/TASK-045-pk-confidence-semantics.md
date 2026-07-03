---
id: task_20260702_045
title: knowledge-pk confidence 赋值规则落地 + 模板 source 页批量回填 low
author: claude
executor: codex
status: pending
type: other
created: 2026-07-02
updated: 2026-07-02
related_rfcs: []
---

# TASK-045: knowledge-pk confidence 语义落地

## 目标

解决 review 发现的「1405 页全部 `confidence: medium`，字段不承载信息」问题：给 knowledge-pk 定 confidence 赋值规则并批量回填，让 `confidence` 与 `review`/`status` 形成有区分度的双信号，答疑排序可用。

## 前置条件

- knowledge-pk working tree clean。

## 强约束

1. **赋值规则**（写入 knowledge-pk 库根 `AGENTS.md`，作为实例约定；不改引擎 schema）：
   | 页况 | confidence |
   | --- | --- |
   | 机器生成模板 source 摘要页（占位句式、未深化） | `low` |
   | 深化 caliber topic / asset-mapping / query / 人工整理 topic，未背书 | `medium` |
   | maintainer 背书（`review: true`）时可随背书升 | `high`（仅随背书设，遵守引擎「非 source/query 页标 high 须人工确认」规则） |
2. **本 task 只做批量回填 low**：范围 = `wiki/sources/` 下 DataWorks 模板摘要页（B001-B136 机器产物）。已深化 / 已背书页、非 source 页一律不动。**不改 `review` / `status`，不 auto 背书。**
3. 回填后 lint 必须 0 error（确认 `low` 与现有 lint 规则无冲突；`UNVERIFIED_HIGH` 只查 high，不受影响）。
4. 规则写入 pk `AGENTS.md` 时只增段落，不重写既有约定。

## 步骤

1. 确认回填范围清单（模板 source 页判定：`wiki/sources/dataworks-*.md` 且 `review: false` 且非 caliber 深化关联页），报数。
2. 批量 `confidence: medium → low`；已背书 asset-mapping、caliber、query 等保持不动。
3. pk `AGENTS.md` 增「confidence 赋值规则」段（上表 + 「high 仅随背书」）。
4. `log.md` 记录；lint / graph / eval + commit。

## 验证

```bash
PK=/Users/zhangjunwu/workspace/obsidian/knowledge-pk
grep -rl "^confidence: low" $PK/wiki/sources --include='*.md' | wc -l    # ≈ 模板 source 页数
grep -rl "^confidence: high" $PK/wiki --include='*.md' | wc -l           # 应为 0（当前无背书升 high）
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root $PK --check-only; echo lint=$?
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_eval.py --root $PK --json | python3 -c "import sys,json;d=json.load(sys.stdin);print('score',d['score'])"
```

## 完成后报告格式

- 回填页数 + confidence 分布前后对比（low/medium/high 各多少）
- AGENTS.md 新增段摘要
- lint / eval 输出、commit sha、偏离或异常

## Execution log by codex · <date>

## Evaluation by claude · <date>
