---
id: task_20260703_047
title: Apply RFC-030 — ODS 源表 binding 解析器 + freshness binding diff（引擎侧）
author: claude
executor: codex
status: pending
type: apply
created: 2026-07-03
updated: 2026-07-03
related_rfcs: [RFC-030]
---

# TASK-047: Apply RFC-030 引擎侧

## 目标

把 RFC-030 落到引擎：DI 同步任务 reader 配置解析（→ `source_binding` / `source_datasource` / `source_tables`）+ freshness 增量路径的 binding diff。**不写 knowledge-pk 索引内容**（回填是 TASK-048）。

## 前置条件

- **RFC-030 status = accepted**（已登记 Decision）。
- Step 0 基线已由 RFC-030 review 实跑钉死（DI 336 / PYODPS3 638；reader 分布 mysql 253 / mongodb 82 / sqlserver 1；真实 shape 见 RFC review 段），**不必重跑 survey**，直接按该 shape 实现。
- 引擎 working tree clean；命令用完整 `/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python ...`（勿放 shell 变量）。

## 强约束

1. **解析规则按 RFC 提案 §1 逐条**：只解析 `category == "reader"` step；mysql/sqlserver 走 `parameter.connection[].datasource + table[]`（多表全收进 list，不截断）；mongodb 走 `parameter.datasource + collectionName`（落 `source_tables`）；**writer ODPS step 的 `parameter.table` 严禁当源表**。
2. **四态枚举**：`parsed` / `ambiguous`（JSON 可读但 shape 超支持：多 reader、缺 datasource、table 空 → 附 `binding_warnings`）/ `unparsed`（非 JSON / 结构异常）/ `inferred`（PYODPS3 等不走解析）。宁 ambiguous 不硬 parsed。
3. **索引契约**：新字段 additive、可选，不 bump `index_version=2`；无 volatile、无代码正文、稳定排序。
4. **freshness 联动**：只在 `--incremental-deployments` 路径对 **changed file 且（`program_type=DI` 或已 `source_binding=parsed`）** 的项重解析（本地 JSON parse）；不扫全量。diff 输出结构化区分 `fingerprint_changed` / `binding_changed`（含 `binding_previous/current/changed`）；binding 变入待复核建议，**不自动改页面状态、不撤 review**。
5. 兼容头等：现有 reverse / freshness / lint / graph / eval 行为不变（全量回归）；核心三件套离线零依赖断言不变；凭证只从 env。

## 步骤

1. `scripts/dataworks_client.py`（或 `wiki_index`，executor 定）：`parse_di_source_binding(content) -> (binding, datasource, tables, warnings)`，覆盖三种 reader shape + writer 排除 + 四态判定。
2. `scripts/wiki_index.py`：索引 item 写入/读取新字段的支持（供 TASK-048 回填与 reverse/答疑消费；本 task 不动 pk 索引）。
3. `scripts/wiki_freshness.py`：增量路径挂 binding 重解析 + 结构化 diff（约束 4）。
4. `tests/test_task_047.py`：mysql 多表 list / mongodb collectionName / sqlserver / writer 被排除 / 多 reader→ambiguous+warnings / 非 JSON→unparsed / PYODPS3→inferred 不触碰 / 增量只重解析 changed 项断言 / 索引契约（additive、v2 不变）/ 离线隔离。
5. `wiki-design/02-workflows.md`（批量快审背书流程 + 答疑三档口径）+ `scripts/README.md`。
6. 限量真实 smoke（凭证在 env）：抽 mysql / mongodb / sqlserver 各 ≥1 个真实 DI 文件解析，脱敏记录结果。
7. 引擎 commit；RFC-030 末尾登记 `## Applied in <sha>`。

## 验证

```bash
cd /Users/zhangjunwu/workspace/llm-wiki/llm-wiki
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -c "import sys; sys.path.insert(0,'scripts'); import wiki_lint,wiki_graph,wiki_eval; print('泄漏:', [m for m in sys.modules if any(k in m.lower() for k in ('dataworks','alibabacloud','sqlglot'))] or '无')"
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest -v tests.test_task_047 2>&1 | tail -3
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest discover -s tests 2>&1 | tail -2
```

## 完成后报告格式

- 解析函数位置 + 三种 shape 处理点 + 四态判定逻辑
- freshness binding diff 挂点 + 只重解析 changed 项的实现
- test_047 明细 + 全量回归 + 离线断言
- 真实 smoke（三 stepType 各 ≥1，脱敏）
- commit sha + RFC-030 `Applied in`、偏离或异常

## Execution log by codex · <date>

## Evaluation by claude · <date>
