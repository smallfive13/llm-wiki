---
id: task_20260624_032
title: Apply RFC-028 M1 全量初始化 + 反查能力（双向血缘 + ODS↔线上源表 + 表名反查）
author: claude
executor: codex
status: done
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

## Execution log by codex · 2026-06-24

Step 0 实跑核实结论：

- `ListNodes(project_env="PROD")` 使用 `PageNumber` / `PageSize` 翻页；实跑 page1=100、page2=100，raw `TotalCount=1384`，全 raw 翻页 pages=14、raw_nodes=1384。
- 生产过滤口径实跑结果：`Repeatability == true` 且 `SchedulerType == "NORMAL"` 后 normal_repeatable=1353；PAUSE=30。
- `ListNodeIO(io_type="input")` 返回顶层 `Data/ErrorCode/ErrorMessage/HttpStatusCode/RequestId/Success`；`Data` 是列表，每项含 `Data/NodeId/TableName` 等字段。本 task 读取 `Data`，缺失时回退 `TableName`。
- ODS inputs 含线上 / 前序源表名。样本：node `ods.loan_biz_credit_enhancement_apply.extract` 的 input 为 `pk_data.ods.loan_biz_credit_enhancement_apply.pre`，outputs 含 `pk_data.ods.loan_biz_credit_enhancement_apply.extract`。
- 分层样本覆盖 `ODS/DWD/DWB/DWS/unknown`；实跑前 500 raw 节点样本中有 `dwb_oper_coupon_detail`、`dwd_rhino_qc_case_content_2mysql`、`dws_holo.dws_train_user_paper_subject_detail_info`、`ods_sdk_backend_autosync_...`。

改动文件：

- `scripts/dataworks_client.py`：`DataWorksNode` 增 `inputs`；`list_node_io_items()` 统一读 input/output；`list_prod_nodes()` 记录双向血缘。
- `scripts/wiki_index.py`：`index_version` bump 到 2；索引 item 增 `inputs[]`；分层识别扩展到 `ods/dwd/dwb/dws/ads`；新增 `reverse` 子命令，输出 ODS 溯源、下游候选、分层说明、知识页命中状态和调度血缘 caveat。
- `tests/test_task_031.py`：适配 v2 index 与 inputs。
- `tests/test_task_032.py`：覆盖分页、双向血缘、ODS↔线上源表、DWB/DWS/ADS/unknown、reverse、全限定表名不按后缀误匹配、进程级隔离、缺凭证 warning。
- `scripts/README.md`、`wiki-design/02-workflows.md`：补全全量索引 / reverse 用法与答疑路由策略。
- pk 实例 `/Users/zhangjunwu/workspace/obsidian/knowledge-pk/AGENTS.md`：同步表名反查约定。
- pk 实例 `/Users/zhangjunwu/workspace/obsidian/knowledge-pk/.wiki/dataworks_index.json`：限量两页 smoke 写入 v2 受管索引。

验证输出：

```text
$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -c "import sys; sys.path.insert(0,'scripts'); import wiki_lint,wiki_graph,wiki_eval; print('泄漏:', [m for m in sys.modules if any(k in m.lower() for k in ('dataworks','wiki_index','alibabacloud','sqlglot'))] or '无')"
泄漏: 无

$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest -v tests.test_task_031 tests.test_task_032
Ran 15 tests ... OK

$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest discover -s tests
Ran 132 tests in 41.259s
OK (skipped=1)

$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --check-docs
受管块: 6
错误: 0

engine_lint=0
engine_graph=0
engine_eval=0
datawarehouse_lint=0
personal_lint=0
pk_lint=0
pk_graph=0
pk_eval=0
```

真实限量翻页 smoke：

```text
$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_index.py --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk --project-id 96107 --project-identifier pk_data --max-pages 2 --write
wiki-index
==========
action: write
target: /Users/zhangjunwu/workspace/obsidian/knowledge-pk/.wiki/dataworks_index.json
items: 176
layers: DWB:1 · DWD:11 · DWS:1 · ODS:155 · unknown:8
contains_code_payload: False
```

真实 reverse smoke：

```text
$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_index.py reverse --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk --table pk_data.ods.loan_biz_credit_enhancement_apply.pre
wiki-index reverse
table: pk_data.ods.loan_biz_credit_enhancement_apply.pre
caveat: 基于 DataWorks 调度血缘，可能漏掉动态 SQL、脚本内临时表或未登记依赖。
Recommended:
- ODS ods.loan_biz_credit_enhancement_apply.extract ... missing_knowledge_page
- ODS ods.loan_biz_credit_enhancement_apply.pre ... missing_knowledge_page
Warnings:
- 未找到下游明细/汇总/应用层候选；先返回 ODS 溯源结果，需人工继续查下游。
```

执行中发现并修复的异常：

- 初版 reverse 对全限定表名 `pk_data....pre` 会按最后一段 `pre` 误匹配所有 `.pre` ODS。已改为：全限定查询只精确匹配；只有用户输入无点短名时才允许 basename 匹配，并新增单测锁定。

pk 实例 commit：

- `8ac50e7cc948ff1cb662780a68a105e1a68073d3` `[index] upgrade DataWorks index reverse baseline`，已 push 到 `http://git.ppdaicorp.com/international_data/knowledge-pk.git`。

maintainer 全量初始化命令：

```bash
cd /Users/zhangjunwu/workspace/llm-wiki/llm-wiki
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_index.py \
  --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk \
  --project-id 96107 \
  --project-identifier pk_data \
  --write
```

## Evaluation by claude · 2026-06-24

**Verdict: PASS。** 兼容性头等约束守住,反查能力按钉死形态实现并由完整链单测验证,M1 全量初始化能力 + 反查能力就绪。

### 兼容性（头等，独立复验）

| 核验 | 结果 |
| --- | --- |
| 核心工具进程级零新依赖 | `wiki_lint/graph/eval` import 后无 dataworks/wiki_index/alibabacloud/sqlglot → **泄漏: 无** ✓ |
| 现有库行为不变 | datawarehouse / personal lint=0 ✓ |
| 全量回归 | **132 tests OK (skipped=1)** ✓ |

### 反查形态（实现 + 单测确认，不受 smoke 索引血缘稀疏限制）

- **5 层定位说明全在**(wiki_index.py:167-171):ODS=贴源溯源不优先 / DWD=明细定义层优先 / DWB=明细宽表优先 / DWS=汇总粒度 / ADS=应用报表;
- 单测 `test_reverse_online_source_to_ods_and_downstream_with_knowledge_page`:线上表 → 反查 → **断言 `recommended[0].layer=="DWD"`(推荐明细层首位)+ `has_knowledge_page`(知识页标注)** ✓——这正是我们定的"全候选+推荐明细层+review 标注"形态;
- `test_reverse_ods_without_downstream_warns`:无下游兜底警示 ✓;`caveat`(调度血缘可能漏动态SQL)✓。

### Step 0 实跑 + 索引 v2

- 翻页 `PageNumber/PageSize` 拉满(raw TotalCount **1384**、过滤后 normal_repeatable **1353**;较 TASK-031 的 1372 涨 12,生产节点动态变化正常);`ListNodeIO(input)` 拿到 ODS 输入表;分层认全 ods/dwd/dwb/dws;
- 索引 **v2**:item 含 `inputs[]`+`outputs[]` 双向血缘 + ODS↔线上源表;`index_version` bump;无 volatile、零代码/凭证(沿用 TASK-031 校验)。

### 主动质量（认可）

codex 自查发现并修复 reverse 的**全限定表名误匹配**(`...pre` 按末段 `pre` 误匹配所有 ODS)→ 改为全限定只精确匹配、仅短名允 basename,并加单测 `test_reverse_fully_qualified_table_does_not_match_only_suffix` 锁定。

### 限量验证（按 task 设计）

176 items(前 2 页)而非全量——task 明确"完整 1353 全量由 maintainer 跑"。**全量初始化命令已文档化**,待 maintainer 执行一次即得完整基线。

### 结论

RFC-028 M1 全量初始化能力 + 反查能力就绪。TASK-032 done 有效(引擎 `21e7cad` / pk `8ac50e7`)。下一步:maintainer 跑一次全量命令得完整 1353 索引;之后"线上表用离线哪张"可按"全候选+分层说明+推荐明细层+兜底"回答。剩 M2(变更增量)/M3(分层方法论文档)/M4(sqlglot)。
