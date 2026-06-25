---
id: task_20260625_033
title: 修复 RFC-028 反查 — 表名归一化 + 收敛到第一明细层 + 主题域分组
author: claude
executor: codex
status: pending
type: apply
created: 2026-06-25
updated: 2026-06-25
related_rfcs: [RFC-028]
---

# TASK-033: 修复 reverse 反查

## 目标

修复 TASK-032 反查在真实全量数据上暴露的实质缺陷（多跳爆炸 + 表名不归一导致真下游连不上、假候选泛滥）。三件:① 表名归一化让血缘精确连;② 反查收敛到第一明细层（DWD/DWB）;③ 主题域分组。**归一化 + 主题域都在反查时实时计算,不改索引结构、不 bump index_version、不需重跑全量**（现有 1356 索引直接用）。

## 前置条件

- TASK-032 done（全量索引 v2 在,1356 items,双向血缘正确）。
- 引擎 working tree clean。环境：`/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python`。

## 背景（真实数据暴露）

- 还款 ODS `pk_data.ods.pak_listing_autosync_3_tb_repay_record.extract` 反查返回 30+ 候选,蔓延到风控/催收/财务;真直接下游 `dwd_asset_repay_record`（其 inputs 写作 `pk_data.ods_pak_listing_autosync_3_tb_repay_record` 下划线无后缀）反而精确匹配不上。
- 根因:`reverse` 用 `range(5)` 多跳 + 表名不归一靠 token 模糊匹配。

## 强约束（钉死，口径已与用户聊定）

1. **兼容性头等**:进程级断言 `wiki_lint/graph/eval` 不 import `dataworks_client/wiki_index/alibabacloud_*`;现有库（personal/datawarehouse/cmn）行为不变（smoke + 全量回归）。
2. **表名归一化**（反查时实时算,统一 key）:
   - 去**点分末段环节词**,集合 `{extract, pre, assign, fix}`（抽取/检查/分发/修复,均 ODS 处理环节;**Step 0 统计点分末段后缀全集兜底,补全遗漏的环节词再钉死**）;
   - 统一**层分隔符** `层.名` ↔ `层_名`（`ods.X` 和 `ods_X` 归一）;
   - **保留**下划线身份后缀（`_dly/_snp/_mly/_hly` 等粒度标识,绝不去）+ project 前缀;
   - 归一后**精确血缘匹配,移除 token/basename 模糊匹配**（假候选根源）。
3. **反查收敛**:从给定表沿正向血缘,**穿过 ODS 层内部环节,到第一层 DWD/DWB 停**;**默认不纳入 DWS/ADS**,可选 `--depth`/`--include-summary` 展开。去掉无界 `range(5)`。
4. **主题域分组**（反查时实时算）:从命名 `<层>_<域>_<业务>` 抽 `domain`;域集合 `{risk, fin, coll, asset, mkt, ...}` 由 **Step 0 实跑统计真实分布**确认、best-effort + `unknown`、不写死;reverse 输出**按 domain 分组/标注**候选,每候选保留 layer + 层定位说明 + review + 知识页状态。
5. **跨 project**:靠归一后真实 input/output 连接自然决定,不特殊跨 project 合并。
6. **无下游兜底**+ **血缘 caveat** 保留。
7. **不改索引结构**、不 bump `index_version`、不 bump `schema_version`、不改核心工具逻辑。

## 步骤

> **Step 0 实跑核实（必做，纯本地读现有索引，可不连 DataWorks）**:① 统计 `dataworks_index.json` 所有点分末段后缀全集 → 确认环节词集合（除 extract/pre/assign/fix 外有无遗漏）;② 统计表名第二段分布 → 确认主题域集合;③ 抽样验证归一化能让 `ods.X.extract`/`.pre` 与 `ods_X` 归到同一 key;④ 对还款 ODS 验证归一+第一明细层收敛后真直接下游是哪几个。结论写进 Execution log,与口径冲突先提。

1. **`scripts/wiki_index.py`**:新增 `normalize_table_key()`（强约束 2）+ `table_domain()`（强约束 4）;`build_reverse_report` 改:归一精确匹配、穿 ODS 到第一明细层停（去 range(5)）、移除模糊匹配、按 domain 分组输出。
2. **测试 `tests/test_task_033.py`**（真实命名 fixture,锁死本次缺陷）:
   - 命名不一致 `ods.X.extract`/`.pre` ↔ `ods_X` 经归一**精确连**;
   - 多跳**不爆炸**（到第一 DWD/DWB 停,不蔓延 DWS/ADS,不蔓延无关域）;
   - 身份后缀 `_dly/_snp` **不被误合并**;
   - 多域**分组**输出;跨 project 仅真血缘连;
   - 进程级隔离断言;无下游兜底 + caveat。
3. **`scripts/README.md` / `wiki-design/02-workflows.md` / pk `AGENTS.md`**:反查口径更新（到第一明细层 + 主题域分组 + 归一化说明）。
4. 引擎一个 commit + push。pk 仓**无需改**（索引不变）。

## 验证

```bash
cd /Users/zhangjunwu/workspace/llm-wiki/llm-wiki
PY="/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python"
$PY -c "import sys; sys.path.insert(0,'scripts'); import wiki_lint,wiki_graph,wiki_eval; print('泄漏:', [m for m in sys.modules if any(k in m.lower() for k in ('dataworks','wiki_index','alibabacloud','sqlglot'))] or '无')"
for R in datawarehouse knowledge/personal; do $PY scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/$R >/dev/null 2>&1; echo "$R lint=$?"; done
$PY -m unittest -v tests.test_task_033 2>&1 | tail -3
$PY -m unittest discover -s tests 2>&1 | tail -2
# 真实反查（还款链）：应收敛到少数 asset 域 DWD（含 dwd_asset_repay_record has_knowledge_page），按域分组，不再 30+
$PY scripts/wiki_index.py reverse --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk --table pk_data.ods.pak_listing_autosync_3_tb_repay_record.extract 2>&1 | head -30
```

## 完成后报告格式

- Step 0 结论（环节词全集、主题域集合、归一化验证、还款链真直接下游）
- 改动文件 + 关键位置（normalize_table_key、table_domain、reverse 收敛、域分组）
- 验证输出（进程级断言、现有库、test_033、回归、真实反查前后对比：30+ → 收敛后数量 + 域分组）
- 偏离或异常

## Execution log by codex · <date>

（执行者填写）

## Evaluation by claude · <date>

（评估者填写）
