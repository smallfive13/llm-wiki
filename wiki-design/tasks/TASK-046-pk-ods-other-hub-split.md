---
id: task_20260703_046
title: knowledge-pk ods-other hub 二期拆分 — 按源系统拆子 hub（保链迁移）
author: claude
executor: codex
status: pending
type: other
created: 2026-07-03
updated: 2026-07-03
related_rfcs: []
---

# TASK-046: ods-other hub 二期拆分

## 目标

TASK-044 方案 b 压缩后 `ods-other-source-lineage.md` 仍 ~1257 行（616 任务挤一页）。本 task 按**源系统 / 业务前缀**把它拆成 N 个子 hub，父页降为轻量目录页，彻底解决 AI 单页可读问题。**迁移期间 616 个 source 页的入链一个不丢。**

## 前置条件

- **TASK-044 done**（方案 b 已 apply，压缩后基线在）。
- knowledge-pk working tree clean；graph orphan 0 / connectivity 100。

## 强约束

1. **保链迁移是硬底线**：每个 source 页的 wikilink 必须落到某个子 hub；拆分前后 `wiki_graph` 的 isolated 必须保持 0、connectivity 100、dangling 0。迁移用「先建子 hub 全量收链 → 再瘦父页」顺序，任何中间 commit 不得出现 orphan。
2. **拆分维度**：按 ODS 源系统前缀（如 `app_server` / `audit_center` / `pak_vendor_biz` / `pak_capital` / `sdk_backend` / `user_main` …）聚类；单个子 hub 目标 ≤ 300 行；尾部散表可归一个「misc」子 hub。
3. 父页 `ods-other-source-lineage.md` 保留：说明 + 子 hub 目录（wikilink）+ 原 frontmatter `source_ids` 按需迁移到子 hub；不改页面 id 语义（子 hub 是新页新 id，父页保留原 id 避免外部引用断链）。
4. 子 hub 沿用 routing topic 措辞规范（物理层级 / 是否可作口径取数 / ODS 只作溯源）；`review: false`。
5. 更新 `index.md` / `log.md`；不动其它 hub（`ods-user` 等压缩后已可接受，除非 maintainer 另点）。

## 步骤

1. 从索引导出 616 任务按源系统聚类，定子 hub 清单（名称 + 行数预估），报数。
2. 建子 hub 页并收链（每个子 hub 单独 commit）；graph 校验 orphan 0。
3. 父页瘦成目录页；graph / lint / eval 全过。
4. 更新 index.md / log.md；commit。

## 验证

```bash
PK=/Users/zhangjunwu/workspace/obsidian/knowledge-pk
wc -l $PK/wiki/topics/ods-other-source-lineage.md          # 目录页，应大幅小于 1257
wc -l $PK/wiki/topics/ods-other-*-lineage.md 2>/dev/null | sort -rn | head   # 子 hub 单页 ≤ ~300 行
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_graph.py --root $PK 2>&1 | tail -3   # isolated 0 / dangling 0
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_eval.py --root $PK --json | python3 -c "import sys,json;d=json.load(sys.stdin);print('score',d['score'],'connectivity',d['dims']['connectivity'])"   # connectivity 100
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root $PK --check-only; echo lint=$?
```

## 完成后报告格式

- 子 hub 清单（名称 / 收纳任务数 / 行数）
- 拆分前后 graph 对比（isolated / connectivity / edges）
- 父页最终形态摘要
- lint / graph / eval、per-hub commit sha、偏离或异常

## Execution log by codex · <date>

## Evaluation by claude · <date>
