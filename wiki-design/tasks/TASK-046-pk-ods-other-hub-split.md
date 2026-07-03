---
id: task_20260703_046
title: knowledge-pk ods-other hub 二期拆分 — 按源系统拆子 hub（保链迁移）
author: claude
executor: codex
status: done
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

## Execution log by codex · 2026-07-03

结论：完成。按方案先建子 hub 收链，再瘦父页；最终 lint / graph / eval 全过。

子 hub 清单（名称 / 收纳 source 链数 / 行数）：

- `app-server` / 3 / 36 行
- `audit-center` / 21 / 54 行
- `loan-biz` / 22 / 55 行
- `metadata` / 3 / 36 行
- `misc` / 64 / 97 行
- `pak-backend` / 6 / 39 行
- `pak-capsule` / 6 / 39 行
- `pak-cds` / 27 / 60 行
- `pak-ddp` / 3 / 36 行
- `pak-dmp` / 3 / 36 行
- `pak-es` / 3 / 36 行
- `pak-gpms` / 45 / 78 行
- `pak-listing-autosync-3` / 69 / 102 行
- `pak-listing-core` / 6 / 39 行
- `pak-loan-markting` / 21 / 54 行
- `pak-ppdai` / 33 / 66 行
- `pak-sword` / 51 / 84 行
- `pak-thirdparty` / 28 / 61 行
- `pak-xtms` / 27 / 60 行
- `pk-vos3000` / 3 / 36 行
- `ppdai-site-msg` / 3 / 36 行
- `sdk-backend-autosync-2` / 30 / 63 行
- `sdk-backend-autosync-3` / 15 / 48 行
- `sdk-backend-autosync-4` / 109 / 142 行
- `sdk-backend-base` / 9 / 42 行
- `sdk-backend-service` / 6 / 39 行

合计：26 个子 hub，616 个 source 链；最大子页 142 行。

拆分前后 graph 对比：

- TASK-044 后基线：nodes 1405 / edges 1987 / isolated 0 / connectivity 100 / eval score 83。
- 子 hub 建完、父页未瘦身中间态：nodes 1434 / edges 3341 / isolated 0。
- 最终态：nodes 1434 / edges 2750 / isolated 0 / dangling 0 / ambiguous 0 / connectivity 100 / eval score 82。

父页最终形态：

- `wiki/topics/ods-other-source-lineage.md` 保留原 id `top_20260629_ods-other-source-lineage`。
- 父页从 658 行压到 55 行，仅保留说明、26 个子 hub 目录、路由口径与使用提示。
- 原 616 条 `source_ids` 已迁移到子 hub，父页 `source_ids: []`，避免继续作为巨型 source hub。

验证输出：

```text
wiki-lint instance root: /Users/zhangjunwu/workspace/obsidian/knowledge-pk · profile: knowledge-pk
扫描: knowledge-pk/wiki/ (1434 文件) · knowledge-pk/inbox/ (0 draft) · knowledge-pk/raw/ (1354 source)
[OK] schema 校验: 1434 页扫描
[OK] ID 唯一性: 1434 个 id
[OK] canonical 引用 + supersedes 对称
[OK] source 单主键
[OK] entity 别名（含链式跳转 / status:redirect）: 0 entries
[OK] inbox: 0 draft
[OK] 脱敏扫描（inbox/archive）: 0 命中
错误: 0 · 警告: 0
lint_exit=0
graph_exit=0
eval_exit=0
graph_nodes 1434
graph_edges 2750
isolated 0
dangling 0
ambiguous 0
eval_score 82
eval_connectivity 100
parent_lines 55
children 26
child_max_lines 142
child_total_source_mentions 616
```

pk commit：

- 子 hub per-hub commits：`a9a6927`、`1a18ebd`、`b5766f2`、`acb44d4`、`a4585f0`、`5fe7159`、`81b07d4`、`3deea0d`、`a3986f6`、`420f867`、`6b36c3d`、`0c1a7cf`、`69d01b5`、`ecd6125`、`8c773c5`、`7423cac`、`56300bf`、`35dc14a`、`330fcfb`、`9649bc3`、`be1b5bd`、`27dbbad`、`c580a59`、`50b0070`、`4795df9`、`5eca018`。
- 父页瘦身 + id 格式修正 + index/log：`0f46fb6`。

偏离或异常：

- 首轮验证发现 26 个子 hub 新 id 使用了下划线 slug，触发 `ID_FORMAT`。已在最终 pk commit `0f46fb6` 中统一修为 hyphen slug，并同步修正父页 `related_ids`。
- 第一次 lint/graph 命令从 pk repo cwd 调用，引擎脚本报 `must run from repo root containing scripts/`；随后从引擎 repo cwd 重跑通过。
- pk repo 仍有 3 个既有未跟踪文件未纳入本 task：`wiki/asset-mappings/product-user-type.md`、`wiki/queries/new-old-customer-how-defined.md`、`wiki/topics/asset-user-type-caliber.md`。


## Evaluation by claude · <date>
