---
id: task_20260702_044
title: knowledge-pk 巨型路由 hub 页瘦身 — Step 0 图谱影响实测 + 方案报 maintainer 拍板
author: claude
executor: codex
status: pending
type: other
created: 2026-07-02
updated: 2026-07-02
related_rfcs: []
---

# TASK-044: knowledge-pk 巨型 hub 页瘦身

## 目标

解决 review 发现的巨型路由页问题：`wiki/topics/ods-other-source-lineage.md`（约 1883 行 / 出度 617）、`ods-user-source-lineage`（约 587 行 / 出度 185）等 ODS/unknown 路由 hub 单页过大，AI 读者一页吃掉大量上下文、人也不可读。**先实测图谱影响，再报方案拍板，拿到 maintainer 确认后才动结构**——结构调整（拆分/降级/归档）属「必须人工确认」档。

## 前置条件

- knowledge-pk working tree clean；graph 当前 orphan 0 / connectivity 100。
- 引擎 `wiki_graph` / `wiki_eval` 可用。

## 强约束

1. **Step 0 必测、不许跳**：这些 hub 是 ~800 个 ODS source 页的**唯一入链来源**，直接砍链/降级会批量制造 orphan、打穿 connectivity（现 100）。任何方案必须先在临时副本或 dry-run 上量化 orphan 数与 eval 分变化，再报方案。
2. **方案候选**（Step 0 后按数据推荐其一，交 maintainer 拍板后才 apply）：
   - a) **按源系统再拆**：`ods-other`（616 任务）按 autosync 源系统 / 业务前缀拆成 N 个子 hub，保留全部 wikilink（不产生 orphan），单页控制在合理行数。
   - b) **压缩正文**：一任务一行（表名 wikilink + 层级 + 一句用途），去掉宽表格冗余列；保留链接，行数减半以上。
   - c) **降级为索引投影**：正文改由脚本从 `dataworks_index.json` 生成（类 maps/ 派生物）——**必须先解决 orphan 问题**（如保留最小链接清单段），且涉及引擎侧生成能力时另开 RFC，不在本 task 私改引擎。
3. 未获 maintainer 确认前**不得改动 / 归档任何 hub 页**；获确认后 apply 也不动 source 页本身。
4. lint / graph / eval 全过；orphan 必须保持 0（或 maintainer 明确接受的替代锚定方式）。

## 步骤

1. **Step 0**：统计各 hub 页行数 / 出度 / 承担的唯一入链数；对候选方案 a/b（必要时 c）做 dry-run 或临时副本实测 graph orphan / connectivity / eval score 变化。
2. 汇总成对比表 + 推荐方案，追加到本 task Execution log，**停下等 maintainer 拍板**。
3. maintainer 确认后 apply 所选方案；更新 index.md / log.md。
4. lint / graph / eval + commit。

## 验证

```bash
PK=/Users/zhangjunwu/workspace/obsidian/knowledge-pk
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_graph.py --root $PK 2>&1 | tail -3   # orphan 0
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_eval.py --root $PK --json | python3 -c "import sys,json;d=json.load(sys.stdin);print('score',d['score'],'connectivity',d['dims']['connectivity'])"   # connectivity 不降
wc -l $PK/wiki/topics/ods-other-source-lineage.md 2>/dev/null || echo "(已拆分/重命名，按新结构核对)"
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root $PK --check-only; echo lint=$?
```

## 完成后报告格式

- Step 0 实测对比表（各方案 orphan / connectivity / eval / 单页行数）+ 推荐结论
- maintainer 拍板记录
- apply 后 graph / eval / lint 输出、单页行数分布、commit sha
- 偏离或异常

## Execution log by codex · <date>

## Evaluation by claude · <date>
