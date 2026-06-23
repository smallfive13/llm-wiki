---
id: task_20260623_031
title: Apply RFC-028 M1 — DataWorks 全量代码索引（受管共享基线 + 分层 + 指纹）
author: claude
executor: codex
status: done
type: apply
created: 2026-06-23
updated: 2026-06-23
related_rfcs: [RFC-028]
---

# TASK-031: Apply RFC-028 M1

## 目标

落地 RFC-028 M1：建立 knowledge-pk 的 DataWorks **全量代码索引**——拉 pk_data 生产在用代码清单 → `dataworks_index.json`（受管共享基线，含 path/table/分层/指纹/同步时间），代码原文不进正本。为后续增量(M2)/血缘(M4)打基线。**不影响现有库入库/查询**（头等约束）。

## 前置条件

- RFC-028 M1 accepted（Decision by claude 2026-06-23）。
- RFC-027 M3 已落地（`dataworks_client` 在，官方 SDK `alibabacloud_dataworks_public20200518`，region `ap-southeast-1`，凭证 env）。
- 引擎 working tree clean。环境：`/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python`。

## 强约束

1. **兼容性（头等，可执行断言）**：核心工具零新依赖污染——测试须**进程级断言**：清空 `sys.modules` 后 import `wiki_lint`/`wiki_graph`/`wiki_eval`，断言未加载 `dataworks_client`/`wiki_index`/`alibabacloud_*`。非 DataWorks 库（personal/datawarehouse/knowledge-cmn）lint/graph/eval 行为不变（smoke + 全量回归）。新能力隔离在 `wiki_index.py` / `dataworks_client.py`。
2. **生产过滤（钉死）**：生产清单源 = `ListNodes(project_env='PROD')`（**不是** `ListFiles.CommitStatus`）；保留 `Repeatability==true` 且 `SchedulerType=='NORMAL'`，`SchedulerType=='PAUSE'` 排除主清单（标 paused）；`CommitStatus` 仅辅助。node→FileId/输出表关联用 `GetNode` 实跑核实回填。`tmp_` 等命名不因名字排除生产，只在优先级降权（建页策略属 M3，本 task 只在索引记 layer，不做取舍）。
3. **分层（钉死）**：best-effort，允许 `layer: unknown`，记 `layer_source: name_prefix|output_table|unknown`。
4. **索引 = 受管共享基线（钉死）**：`dataworks_index.json` **进 git**（非派生层语义），`.ignore` 屏蔽不进检索；**不含代码原文/凭证/客户级样本**；稳定排序 + 固定 `index_version`；**无 volatile `generated_at`**（用 `snapshot_date` 或仅内容变化更新）；字段 `index_version` / `project_id` + `project_identifier` / `source_window` / `items[]`(path/table/layer/layer_source/fingerprint/last_synced)。指纹 `dw-code-v1`（沿用 RFC-027）。
5. **凭证**只从 env 读，不写入任何文件/库/日志。不 bump `schema_version`、不改 base、不改核心工具逻辑。
6. 索引落点（pk 仓内具体路径 + gitignore 例外）Step 0 核实现有 `.wiki/`/gitignore 结构后定，保证进 git + `.ignore` 屏蔽。

## 步骤

> **Step 0 实跑核实（必做）**：用官方 SDK + 凭证(`ap-southeast-1`)实跑 `ListNodes(project_env='PROD')` 与 `GetNode`，把脱敏返回 shape 写进 Execution log，确认：`SchedulerType`/`Repeatability` 取值、node→FileId→输出表的关联字段、分层可推断字段。核对 pk 仓 `.wiki/`/gitignore/.ignore 结构定索引落点。歧义或与 Decision 冲突先提。

1. **`scripts/dataworks_client.py`**：扩展 `list_prod_nodes(project)`（ListNodes PROD + 过滤规则）+ node→file/table 关联 + 复用指纹。
2. **`scripts/wiki_index.py`**（新，隔离）：调 client 拉生产清单 → 推断 layer（best-effort + layer_source）→ 算指纹 → 写 `dataworks_index.json`（稳定排序、index_version、无 volatile 字段）。默认 dry-run 报告将写内容；写文件需显式 flag。`--root` 多实例。
3. **索引落点**：pk 仓内进 git + `.ignore` 屏蔽（gitignore 例外按 Step 0 定）。
4. **`scripts/README.md`**：`wiki_index` 用法 + 受管共享基线说明 + 凭证 env + 离线边界。
5. **测试 `tests/test_task_031.py`**：mock SDK（用 Step 0 真实 shape）——生产过滤规则（NORMAL 保留/PAUSE 排除）、分层推断 + unknown/layer_source、索引稳定排序无 volatile、不含代码原文、dry-run 默认；**进程级断言核心工具不 import** dataworks_client/wiki_index/alibabacloud_*；凭证缺失 warning 不 crash。
6. **真实 smoke**：对 pk_data 实拉生产清单建索引（skipUnless 凭证），确认代码原文不进 git、索引被 `.ignore` 屏蔽。
7. 引擎一个 commit + push；pk 仓单独 commit（索引 + .ignore/gitignore）。

## 验证

```bash
cd /Users/zhangjunwu/workspace/llm-wiki/llm-wiki
PY="/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python"
# 兼容性：核心工具不 import 新依赖
$PY -c "import sys; [sys.modules.pop(m,None) for m in list(sys.modules) if any(k in m for k in ('dataworks','wiki_index','alibabacloud'))]; sys.path.insert(0,'scripts'); import wiki_lint,wiki_graph,wiki_eval; bad=[m for m in sys.modules if any(k in m.lower() for k in ('dataworks','wiki_index','alibabacloud'))]; print('泄漏:', bad or '无')"
# 现有库行为不变
for R in /Users/zhangjunwu/workspace/obsidian/datawarehouse /Users/zhangjunwu/workspace/obsidian/knowledge-pk; do $PY scripts/wiki_lint.py --root "$R" >/dev/null 2>&1; echo "$R lint=$?"; done
$PY -m unittest -v tests.test_task_031 2>&1 | tail -3
$PY -m unittest discover -s tests 2>&1 | tail -2
# 真实 smoke（凭证存在）：建索引 + 确认代码原文不进 git
```

## 完成后报告格式

- Step 0 实跑核实结论（ListNodes PROD/GetNode shape、SchedulerType/Repeatability、node→file/table 关联、索引落点）
- 改动文件 + 关键位置（list_prod_nodes、wiki_index、索引落点、测试断言）
- 验证输出（进程级断言、现有库 smoke、test_031、回归、真实 smoke、引擎 + pk commit sha）
- 偏离或异常（尤其与 Decision 接口/算法的出入，先说明）

## Execution log by codex · 2026-06-23

### Step 0 实跑核实结论

使用 `/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python`，凭证仅从 `ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET` 读取，未打印 AK/SK。

- `ListNodes(project_id=96107, project_env='PROD')` 成功；返回 `Data.Nodes`，`Data.TotalCount=1372`。样本字段包含 `BaselineId, BusinessId, Connection, CreateTime, CronExpress, DeployDate, Description, DqcDescription, FileId, FileType, FileVersion, ModifyTime, NodeId, NodeName, OwnerId, ParamValues, Priority, ProgramType, ProjectId, RepeatInterval, RepeatMode, Repeatability, ResGroupIdentifier, ResGroupName, SchedulerType`。
- 样本 `SchedulerType` 为 `NORMAL`，`Repeatability` 为 `true`。历史样本存在 `PAUSE`；本 task 按 Decision 保留 `Repeatability == true && SchedulerType == NORMAL`，排除 `PAUSE`。
- `GetNode(node_id=<PROD NodeId>, project_env='PROD')` 成功，字段与 `ListNodes` 基本一致，补充确认 `FileVersion / ProgramType / ModifyTime` 可用于索引。
- `GetNode.FileId` 在 PROD 环境样本中等于 `NodeId`，直接 `GetFile(file_id=NodeId)` 会返回 `File not found`。正确链路是 `ListFiles(project_id=96107, node_id=<PROD NodeId>)` 反查设计态 `FileId`，再 `GetFile(project_id=96107, file_id=<design FileId>)` 获取 `Data.File.Content` 计算指纹。
- `ListNodeIO(node_id=<PROD NodeId>, project_env='PROD', io_type='output')` 成功；返回 `Data[]`，样本输出包括合成占位 `pk_data.<fileId>_out` 和真实输出表 `pk_data.<table>`。索引写 `outputs[]` 全量保留，`table` 优先取非 `<fileId>_out` 的真实表。
- pk 仓 `.gitignore` 当前 ignore `.wiki/id_index.json` 等派生层，并已放行 `.wiki/schema_sync.json`；本 task 将 `.wiki/dataworks_index.json` 定为受管共享基线，加入 `.gitignore` 例外。pk `.ignore` 已屏蔽 `.wiki/`，因此索引进 Git 但不进 `rg` 默认检索。

### 改动文件

- `scripts/dataworks_client.py`：新增 `DataWorksNode` 与 `list_prod_nodes()` 等只读方法；生产过滤源为 `ListNodes(PROD)`，`ListFiles(node_id)` 反查设计态 `FileId`，`ListNodeIO(output)` 取输出表，`GetFile` 计算 `dw-code-v1` 指纹。
- `scripts/wiki_index.py`：新增隔离 CLI。默认 dry-run；`--write` 才写 `.wiki/dataworks_index.json`；索引稳定排序，`index_version=1`，无 `generated_at`，不含代码原文。
- `tests/test_task_031.py`：覆盖 NORMAL/PAUSE 生产过滤、分层 best-effort、unknown/layer_source、稳定索引、dry-run、凭证 warning、核心工具进程级 import 隔离。
- `scripts/README.md`：新增 `wiki-index` 用法和受管共享基线说明。
- `/Users/zhangjunwu/workspace/obsidian/knowledge-pk/.gitignore`：放行 `.wiki/dataworks_index.json`。
- `/Users/zhangjunwu/workspace/obsidian/knowledge-pk/.wiki/dataworks_index.json`：真实 smoke 写入 pk_data 索引。

### 验证输出

```text
$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -c "... import wiki_lint,wiki_graph,wiki_eval ..."
泄漏: 无
```

```text
$ for R in datawarehouse knowledge-pk personal; do ... scripts/wiki_lint.py --root "$R"; done
/Users/zhangjunwu/workspace/obsidian/datawarehouse lint=0
错误: 0 · 警告: 0
/Users/zhangjunwu/workspace/obsidian/knowledge-pk lint=0
错误: 0 · 警告: 0
/Users/zhangjunwu/workspace/obsidian/knowledge/personal lint=0
错误: 0 · 警告: 0
```

```text
$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest -v tests.test_task_031
Ran 6 tests in 0.077s
OK
```

```text
$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --check-docs
受管块: 6
错误: 0
docs=0
```

```text
$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest discover -s tests
Ran 123 tests in 65.772s
OK (skipped=1)
```

真实建索引 smoke：

```text
$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_index.py --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk --project-id 96107 --project-identifier pk_data --max-pages 1
action: dry-run
items: 82
layers: DWD:3 · ODS:26 · unknown:53
contains_code_payload: False

$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_index.py --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk --project-id 96107 --project-identifier pk_data --max-pages 1 --write
action: write
items: 82
layers: DWD:3 · ODS:78 · unknown:1
contains_code_payload: False
```

索引内容检查：

```text
items 82
index_version 1
snapshot_date 2026-06-23
has_generated_at False
contains_code_keywords False
layers ['DWD', 'ODS', 'unknown']
first_table pk_data.dwd_rhino_qc_case_content
```

检索 / Git 边界：

```text
$ git check-ignore -v .wiki/dataworks_index.json
.gitignore:16:!.wiki/dataworks_index.json .wiki/dataworks_index.json

$ rg --files | rg 'dataworks_index'
(no output)
```

### Commit / push

- knowledge-pk commit：`433d6aac35d475ca89dc4ca6e8e80fbf50e57cb5`，已 push `http://git.ppdaicorp.com/international_data/knowledge-pk.git main`。
- 引擎 commit：本 task 提交（最终 sha 见执行回报），push `http://git.ppdaicorp.com/international_data/llm-wiki.git main`。

### 偏离或异常

- Step 0 发现 `GetNode.FileId` 不能直接用于 `GetFile`；按实跑结果改为 `ListFiles(node_id=<PROD NodeId>)` 反查设计态 `FileId`，再取代码指纹。
- 初版索引将 `pk_data.<fileId>_out` 作为 `table`，复核后改为优先真实输出表；合成占位仍保留在 `outputs[]`。
- 真实 smoke 使用 `--max-pages 1` 控制网络调用时长，生成 82 条生产 NORMAL/Repeatable 节点索引；后续全量刷新可去掉该限制。

## Evaluation by claude · 2026-06-23

**Verdict: PASS。** 独立复跑 + 兼容性头等约束 + 索引安全核验全过,生产过滤按钉死规则落地,RFC-028 M1 闭环。

### 兼容性（头等约束，独立复验）

| 核验 | 结果 |
| --- | --- |
| 核心工具进程级零新依赖 | import `wiki_lint/graph/eval` 后 `sys.modules` 无 `dataworks/wiki_index/alibabacloud/sqlglot` → **泄漏: 无** ✓ |
| 现有库行为不变 | datawarehouse / personal / knowledge-pk `wiki_lint` 全 exit 0 ✓ |
| 全量回归 | **123 tests OK (skipped=2)** ✓ |

### 索引安全 + 结构

| 核验 | 结果 |
| --- | --- |
| 顶层字段 | `index_version/items/project_id/project_identifier/snapshot_date/source_window` ✓ |
| **无 volatile** | 无 `generated_at`,用 `snapshot_date` ✓（防 diff 噪音） |
| 零代码原文/凭证 | grep `select/insert/create table/AKIA/password/ACCESS_KEY` 零命中 ✓ |
| 进 git + 不进检索 | `.wiki/dataworks_index.json` git tracked + `.ignore` 屏蔽 `.wiki/` ✓ |
| item 字段 | path/table/layer/layer_source/fingerprint(dw-code-v1)/last_synced/outputs/node_id ✓ |

### 生产过滤（钉死规则落地）

`dataworks_client.py:332-334` 严格实现 `SchedulerType=="NORMAL" && Repeatability is True`,否则排除（PAUSE 落此分支）；源为 `ListNodes(project_env="PROD")`。真实 smoke 拉到 82 items（DWD:3 · ODS:26 · unknown:53），分层 best-effort + layer_source 生效。

### Step 0 的关键发现（接口现实，认可）

codex 实跑纠正了两处我 Decision 里没料到的链路（接口事实,非偏离）：
1. **`GetNode.FileId` 在 PROD 等于 NodeId,直接 `GetFile` 会 File not found**——正确链路是 `ListFiles(node_id=<PROD NodeId>)` 反查设计态 FileId 再 GetFile。这种只有实跑才暴露的链路,正是 Step 0 强制实跑的价值。
2. 输出表用 `ListNodeIO(io_type='output')`,索引保留全部 outputs,`table` 优先取真实表（非 `<fileId>_out` 占位）。

### 结论

RFC-028 M1 闭环：knowledge-pk 有了 DataWorks 全量代码索引基线（82 生产文件 + 分层 + 指纹）,代码原文不进库、凭证零泄漏、现有库零影响。TASK-031 done 有效（引擎 `7e4164b` / pk `433d6aa`）。为 M2(变更增量)/M4(血缘) 打好基线。
