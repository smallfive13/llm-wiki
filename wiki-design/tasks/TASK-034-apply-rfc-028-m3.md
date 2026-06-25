---
id: task_20260625_034
title: Apply RFC-028 M3 — 分层建页策略 + 反查路由（纯文档）
author: claude
executor: codex
status: done
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

## Execution log by codex · 2026-06-25

Step 0 落点：

- `wiki-design/02-workflows.md`：现有"代码 → 口径知识"下已有 `asset-mapping`、口径传导、血缘权威性、DataWorks freshness、答疑回源和表名反查段。新增分层建页策略放在"口径传导"之后、"血缘权威性"之前；反查路由在既有 "DataWorks 表名反查路由" 段内扩展，避免重复新开一套规则。
- pk `AGENTS.md`：分层建页策略放在第 2 节"写页面"的 `asset-mapping`/血缘说明之后；答疑路由扩展第 7 节现有"表名反查" bullet。

改动文件：

- `wiki-design/02-workflows.md`
  - 新增"数仓分层建页策略"：ODS 一般不建页，仅作血缘起点/source 证据/反查溯源；DWD 是口径定义点；DWB 是明细宽表定义点；DWS 只写聚合维度/粒度增量并引用上游；ADS 只写应用过滤/展示增量并引用上游。
  - 扩展反查路由：输出包含主题域分组，默认推荐第一明细层 DWD/DWB，ODS 只作溯源不作直接取数推荐；DWS/ADS 默认不含，使用 `--include-summary` 展开；补充 `tmp_` 临时表中转的间接下游不覆盖。
- `/Users/zhangjunwu/workspace/obsidian/knowledge-pk/AGENTS.md`
  - 增加 pk 特定分层建页约定，强调 pk 命名通常为 `<层>_<域>_<业务>`，主题域只作路由辅助。
  - 扩展表名反查答疑规则，与 TASK-033 已验证 reverse 形态一致。

验证输出：

```text
$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --check-docs; echo docs=$?
受管块: 6
错误: 0
docs=0

$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk; echo pk_lint=$?
错误: 0 · 警告: 0
pk_lint=0

$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest discover -s tests 2>&1 | tail -2
OK (skipped=1)
```

提交：

- pk commit：`4197825d4b72b7817bb3cb7f1733f76922f3283d` `[docs] add warehouse layering guidance`，已 push 到 `http://git.ppdaicorp.com/international_data/knowledge-pk.git`。

偏离或异常：

- 无。按要求未改 scripts、未 bump schema、未改 pk 索引。

## Evaluation by claude · 2026-06-25

**Verdict: PASS。** 纯文档,内容符合 TASK-033 验证的反查形态 + M3 分层策略,doc-consistency 不破、零 scripts 改动。

### 复验

| 验证 | 结果 |
| --- | --- |
| `--check-docs` | exit 0（受管块 6） |
| 全量回归 | 140 OK (skipped=1) |
| 未改 scripts | 本提交触及 `scripts/` = **0** ✓ |
| 双仓 | 引擎 `3b25a8d` / pk `4197825d` |

### 内容核对

- **分层建页策略**(02:260)：ODS 一般不建页（作血缘起点/反查溯源）;DWD=口径定义点;DWB=明细宽表;DWS/ADS 记增量引用上游。**且加了合理例外**——ODS 自身承载稳定业务语义/异常清洗/跨系统映射时才建页,不教条。
- **反查路由**(02:300)：输出含 ODS 溯源 + 下游候选 + 层级说明 + 主题域分组 + 知识页状态 + caveat;决策顺序"穿 ODS 到第一明细层 + 域分组、DWS/ADS 默认不展示(`--include-summary` 展开)、`tmp_` 临时表间接下游漏的 caveat"——与 TASK-033 已验证形态一致。
- pk AGENTS 同步分层 + 反查口径（`<层>_<域>_<业务>` 命名 + 主题域辅助路由）。

### 结论

RFC-028 M3 闭环：分层建页 + 反查路由成文规范。TASK-034 done 有效。剩 M2(TASK-035 待执行)/ M4(sqlglot 可选)。
