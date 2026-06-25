---
id: task_20260625_034
title: Apply RFC-028 M3 — 分层建页策略 + 反查路由（纯文档）
author: claude
executor: codex
status: pending
type: apply
created: 2026-06-25
updated: 2026-06-25
related_rfcs: [RFC-028]
---

# TASK-034: Apply RFC-028 M3 分层建页 + 反查路由

## 目标

把数仓分层建页策略 + 表名反查路由固化进 `02-workflows`（通用）+ pk `AGENTS.md`（pk 特定）。**纯文档,不改 scripts**（反查能力 TASK-032/033 已落地并验证）。

## 前置条件

- TASK-033 done（反查归一化 + 收敛 + 域分组已闭环）。
- 引擎 working tree clean。环境：`/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python`。

## 强约束

1. **纯文档**：只动 `wiki-design/02-workflows.md` + `knowledge-pk/AGENTS.md`;不改 scripts、不 bump schema。
2. **分层建页策略**：ODS 一般不建页（作血缘起点 / 反查溯源入口）;DWD = 口径定义点重点梳理;DWB = 明细宽表;DWS 记聚合维度/粒度增量、引用上游;ADS 记应用过滤/展示增量、引用上游。asset-mapping 锚定义层（DWD/DWB）、正文标下游衍生;血缘 `related_ids` 串层（下游 → 上游定义点）。
3. **反查路由**（按 TASK-033 已验证形态）：答疑遇"线上表 / 某表 离线用哪张"→ 调 `wiki_index reverse` → 输出 ODS 溯源 + **到第一明细层（DWD/DWB）候选** + **主题域分组** + 推荐明细层 + review/知识页标注 + 无下游兜底 + caveat。**默认不含 DWS/ADS**（`--include-summary` 展开）。ODS 仅作溯源、不作直接取数推荐。**已知局限**：经临时表（`tmp_`）中转的间接下游反查不覆盖,需人工/caveat 补。
4. doc-consistency 不破（`wiki_lint --check-docs`）。

## 步骤

> **Step 0**：核对 `02-workflows.md` 现有结构（「代码 → 口径知识」「答疑回源」「DataWorks freshness」段）+ pk `AGENTS.md` 节 5/7 找落点,避免与既有分层/反查/回源约定重复冲突。歧义先提。

1. **`wiki-design/02-workflows.md`**：新增/扩展「数仓分层建页 + 反查路由」——分层策略（强约束 2）+ 反查路由决策（强约束 3）。
2. **`knowledge-pk/AGENTS.md`**：pk 特定的分层建页 + 反查路由（指向 02 通用 + pk 命名约定 `<层>_<域>_<业务>`、主题域集合）。
3. doc-consistency：`wiki_lint --check-docs` 通过。
4. 引擎一个 commit + push;pk 仓单独 commit。

## 验证

```bash
cd /Users/zhangjunwu/workspace/llm-wiki/llm-wiki
PY="/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python"
$PY scripts/wiki_lint.py --check-docs; echo "docs=$?"
$PY scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk; echo "pk_lint=$?"
$PY -m unittest discover -s tests 2>&1 | tail -2
```

## 完成后报告格式

- Step 0 落点 + 改动文件 + 验证输出（--check-docs / pk lint / 回归 / 引擎 + pk commit sha）+ 偏离

## Execution log by codex · <date>

（执行者填写）

## Evaluation by claude · <date>

（评估者填写）
