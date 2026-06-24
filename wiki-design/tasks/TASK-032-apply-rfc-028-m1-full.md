---
id: task_20260624_032
title: Apply RFC-028 M1 全量初始化 + 反查能力（双向血缘 + ODS↔线上源表 + 表名反查）
author: claude
executor: codex
status: pending
type: apply
created: 2026-06-24
updated: 2026-06-24
related_rfcs: [RFC-028]
---

# TASK-032: Apply RFC-028 M1 全量初始化 + 反查能力

## 目标

把 `dataworks_index.json` 从 smoke（82）升级为支持 pk_data **全量**生产基线,并新增**双向血缘 + ODS↔线上源表映射 + 完善分层**;新增**表名反查能力**(线上表 → 离线各层候选 + 分层说明)。**实现 + 限量验证**;完整 1372 全量初始化作为运营动作由 maintainer 跑（task 提供命令）。**不影响现有库入库/查询**（头等约束）。

## 前置条件

- RFC-028 M1 accepted + Decision 增补（by claude 2026-06-24）。
- TASK-031 已落地（`dataworks_client.list_prod_nodes` + `wiki_index.py` + 索引基线在）。
- 引擎 working tree clean。环境：`/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python`。

## 强约束

1. **兼容性（头等，可执行断言）**:进程级断言 `wiki_lint/graph/eval` 不 import `dataworks_client/wiki_index/alibabacloud_*`;现有库（personal/datawarehouse/knowledge-cmn）行为不变（smoke + 全量回归）。新能力隔离在 `wiki_index.py`/`dataworks_client.py`。
2. **全量拉能力**:`list_prod_nodes` 支持**翻页拉全**（去掉 `--max-pages` 硬截断,保留可选限量参数）;处理分批/限流;建议支持断点续传或分批写,避免一次性 OOM/超时。
3. **双向血缘**:每 item 增 `inputs[]`（`ListNodeIO io_type=input`）+ 保留 `outputs[]`。
4. **ODS↔线上源表映射**:ODS 节点 `inputs` 视为线上库表,索引记录线上表 → ODS 对应。
5. **完善分层**:layer 认全 `ods/dwd/dwb/dws/ads`,best-effort + `layer_source` + 允许 `unknown`。
6. **反查能力**:`wiki_index` 增反查子命令——给表名 → 输出 ① 贴源 ODS（溯源）② 下游候选（DWD/DWB/DWS/ADS）,每候选带 `layer` + **层定位说明** + `review` 状态 + 是否有对应知识页;**全候选 + 分层说明**（不藏非明细层,推荐倾向明细层）;**无下游兜底**推 ODS + 警示;输出带血缘 caveat。反查默认读本地索引。
7. **索引受管共享基线**:进 git + `.ignore` 屏蔽、稳定排序、**无 volatile**（snapshot_date）、不含代码原文/凭证;结构变更 → `index_version` bump。
8. **凭证**只 env 读、不入库/日志。不 bump `schema_version`、不改 base、不改核心工具逻辑。

## 步骤

> **Step 0 实跑核实（必做）**:用 SDK + 凭证实跑确认——`ListNodeIO(io_type='input')` 返回 shape、全量翻页机制（`NextToken`/`PageNumber`/`PageSize`,确认能拉满 ~1372）、ODS 节点 inputs 是否含线上库表名、`dwb/dws/ads` 实际命名前缀样本。脱敏写进 Execution log。歧义/与 Decision 冲突先提。

1. **`scripts/dataworks_client.py`**:`list_prod_nodes` 翻页拉全（保留可选限量）;`get_node_io(node_id)` 取 input+output;ODS↔线上源表抽取。
2. **`scripts/wiki_index.py`**:全量建索引（双向血缘 + ODS 映射 + 完善分层）;`index_version` bump;新增**反查子命令**（强约束 6 形态,JSON + human 输出）。
3. **测试 `tests/test_task_032.py`**:mock SDK——翻页拉全（多页拼接）、双向血缘、ODS↔线上源表、分层认全 dwb/dws/ads + unknown、`index_version` bump、稳定排序无 volatile;**反查各场景**:线上表→ODS→DWD 命中、多候选含分层说明、无下游兜底 ODS+警示、有/无知识页标注;**进程级隔离断言**;凭证缺失 warning 不 crash。
4. **`scripts/README.md` + `wiki-design/02-workflows.md`**:`wiki_index` 全量/反查用法 + **M3 反查路由策略**（优先明细层、全候选分层说明、兜底、caveat）;pk `AGENTS.md` 同步路由策略（答疑遇"线上表用哪张"调反查）。
5. **限量真实 smoke**（skipUnless 凭证）:验证翻页（拉 ≥2 页确认机制）+ 反查（用真实样本跑一次线上表反查）。**不在 task 内跑满 1372**（耗时/配额);全量初始化命令文档化,由 maintainer 事后执行。
6. 引擎一个 commit + push;pk 仓（如重建全量索引）单独 commit。

## 验证

```bash
cd /Users/zhangjunwu/workspace/llm-wiki/llm-wiki
PY="/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python"
# 兼容性
$PY -c "import sys; sys.path.insert(0,'scripts'); import wiki_lint,wiki_graph,wiki_eval; print('泄漏:', [m for m in sys.modules if any(k in m.lower() for k in ('dataworks','wiki_index','alibabacloud','sqlglot'))] or '无')"
for R in datawarehouse knowledge/personal; do $PY scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/$R >/dev/null 2>&1; echo "$R lint=$?"; done
$PY -m unittest -v tests.test_task_032 2>&1 | tail -3
$PY -m unittest discover -s tests 2>&1 | tail -2
# 反查 human 形态（用 fixture 或真实样本）
$PY scripts/wiki_index.py reverse --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk --table <某线上表> 2>&1 | head -20
# 限量真实翻页 smoke（凭证存在）
```

## 完成后报告格式

- Step 0 实跑核实结论（ListNodeIO input shape、翻页机制、ODS↔线上表、dwb/dws/ads 命名）
- 改动文件 + 关键位置（翻页、双向血缘、ODS 映射、反查子命令、分层说明）
- 验证输出（进程级断言、现有库 smoke、test_032、回归、反查形态、限量翻页 smoke、commit sha）
- 偏离或异常 + maintainer 全量初始化命令

## Execution log by codex · <date>

（执行者填写）

## Evaluation by claude · <date>

（评估者填写）
