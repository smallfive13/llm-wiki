---
id: task_20260625_035
title: Apply RFC-028 M2 — DataWorks 变更增量（生产部署变更 → 反查受影响页待复核）
author: claude
executor: codex
status: done
type: apply
created: 2026-06-25
updated: 2026-06-25
related_rfcs: [RFC-028]
---

# TASK-035: Apply RFC-028 M2 变更增量

## 目标

实现 DataWorks 代码索引的**增量更新 + 防腐**：拉**成功部署到生产的变更文件** → 只对这些算指纹 → 更新索引 + 反查 `dataworks_ref`/血缘受影响的口径页 → 标待复核（机器只筛、人背书）。**不影响现有库入库/查询**（头等约束）。

## 前置条件

- TASK-032/033 done（全量索引 v2 + 反查归一化在）。RFC-027 M3 `wiki_freshness` 在。
- codex 现有 DataWorks 增量接口/MCP 可用。引擎 working tree clean。环境：完整 conda 命令。

## 强约束

1. **兼容性头等**：进程级断言 `wiki_lint/graph/eval` 不 import 在线模块;现有库（personal/datawarehouse/cmn）行为不变（smoke + 全量回归）。在线能力隔离在 `dataworks_client`/`wiki_index`/`wiki_freshness`。
2. **变更语义不可变 = 成功部署到生产的文件变更**（非"所有编辑/草稿"）：
   - **访问层**：优先用 codex 现有 DataWorks 增量接口/MCP;**Step 0 实跑核实该接口/MCP 拉的增量确实是"生产部署变更"语义**（而非开发态编辑）。
   - 若 MCP/接口语义不符,回退 Decision 钉死的 `ListDeployments(status=成功, 时间窗)` + `GetDeployment` → 过滤 `ToEnvironment==2`(PROD) → `DeployedItems[*].FileId/FileVersion`。
3. **只对变更文件 `GetFile` 算指纹**（dw-code-v1，不全量重算）;表名归一用 TASK-033 的 `normalize_table_key`。
4. **更新索引 + 反查受影响页**：变更文件 → 更新其 index item 的 `code_fingerprint`/`last_synced`;通过 `dataworks_ref`/归一血缘反查引用该文件/表的口径页 → 列入待复核。
5. **默认 dry-run**：输出 report（变更文件清单 + 受影响口径页清单）,**不改 frontmatter `status`、不写索引**;写回须显式 flag（如 `--apply`/`--apply-stale`）。接 RFC-027 M3 只读语义 + exit 码（drift/auth warning→0、参数错→2、`--check` 遇 drift→1）。
6. **凭证** env、不入库/日志。不改核心工具逻辑、不 bump schema_version。索引若写（显式 flag）仍受管共享基线规则（无 volatile、不含代码/凭证）。

## 步骤

> **Step 0 实跑核实（必做）**：① 核实 codex 增量接口/MCP 拉的增量语义（是否=生产部署变更）+ 时间窗参数;不符则核实 `ListDeployments`/`GetDeployment` 返回 shape。② 验证变更文件 FileId → `GetFile` 算指纹链路。脱敏写 Execution log,与 Decision 冲突先提。

1. **`scripts/dataworks_client.py`**：增量变更清单方法（MCP 或 ListDeployments,产出"生产部署变更"的 FileId/version）。
2. **`scripts/wiki_freshness.py`**（或 wiki_index）：增量模式——拉变更 → 算指纹 → diff 索引 → 反查受影响口径页 → report;默认只读,写回显式 flag。
3. **测试 `tests/test_task_035.py`**：mock 增量——只对变更文件算指纹（断言未全量 GetFile）、受影响页反查（经 dataworks_ref/归一血缘）、默认 dry-run 不改 status/索引、exit 码三态、进程级隔离、凭证缺失 warning。
4. **`scripts/README.md` + `02-workflows.md`**：增量/防腐用法 + 定时（maintainer cron/CI）+ 变更语义说明。
5. **限量真实 smoke**（skipUnless 凭证）：拉最近时间窗的生产部署变更,验证只算变更文件 + 反查 report。
6. 引擎一个 commit + push。

## 验证

```bash
cd /Users/zhangjunwu/workspace/llm-wiki/llm-wiki
PY="/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python"
$PY -c "import sys; sys.path.insert(0,'scripts'); import wiki_lint,wiki_graph,wiki_eval; print('泄漏:', [m for m in sys.modules if any(k in m.lower() for k in ('dataworks','wiki_index','alibabacloud','sqlglot'))] or '无')"
for R in datawarehouse knowledge/personal; do $PY scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/$R >/dev/null 2>&1; echo "$R lint=$?"; done
$PY -m unittest -v tests.test_task_035 2>&1 | tail -3
$PY -m unittest discover -s tests 2>&1 | tail -2
# 限量真实增量 smoke（凭证存在）：默认 dry-run 输出变更文件 + 受影响页
```

## 完成后报告格式

- Step 0 结论（增量接口/MCP 语义是否=生产部署变更、时间窗、变更→指纹链路）
- 改动文件 + 关键位置（增量拉、指纹、反查受影响页、dry-run）
- 验证输出（进程级断言、现有库、test_035、回归、真实增量 dry-run smoke、commit sha）
- 偏离或异常

## Execution log by codex · <date>

## Execution log by codex · 2026-06-25

Step 0 实跑核实结论：

- 当前 Codex 会话没有暴露可调用的 DataWorks MCP tool；未使用 MCP。
- 回退到官方 SDK 路径并实跑确认：
  - SDK 存在 `ListDeploymentsRequest` / `GetDeploymentRequest`。
  - `ListDeploymentsRequest` 字段包括 `project_id/page_number/page_size/status/end_execute_time/end_create_time`；不支持 `start_time/end_time`。
  - `ListDeployments(project_id=96107, status=1, end_execute_time=<now>, page_size=5)` 返回成功部署列表，部署项字段含 `Id/Name/Status/CreateTime/ExecuteTime`。
  - `GetDeployment(project_id=96107, deployment_id=<Id>)` 返回 `Deployment` + `DeployedItems`；实测 `Deployment.ToEnvironment=2`、`Status=1`，`DeployedItems` 含 `FileId/FileVersion`。
  - 样本：`deployment_id=2472542`，`DeployedItems[0].FileId=500424882`，`FileVersion=8085`。
- 变更文件 → 指纹链路实跑通过：`GetFile(file:96107/500424882)` 返回 `Data.File.Content`，指纹格式 `sha256:<hex>`，长度 71。未打印 AK/SK 或代码内容。

改动文件：

- `scripts/dataworks_client.py`
  - 新增 `DataWorksDeploymentItem`。
  - 新增 `list_successful_prod_deployment_items()`：读取 `ListDeployments(status=1)`，逐条 `GetDeployment`，只保留 `ToEnvironment == 2` 的成功生产部署文件，并按 `(deployment_id,file_id,file_version)` 去重。
  - 新增 `get_successful_prod_deployment_items()`：解析 `DeployedItems[*].FileId/FileVersion`。
- `scripts/wiki_freshness.py`
  - 新增 `--incremental-deployments --project-id <id>` 模式。
  - 默认 dry-run：只输出 report，不改 frontmatter，不写索引。
  - 只对部署变更 FileId 调 `GetFile` 算 `dw-code-v1` 指纹；不全量重算。
  - 用索引中的 `dataworks_ref:file` 和 `normalize_table_key()` 归一化血缘反查受影响口径页。
  - `--apply` 才写 `.wiki/dataworks_index.json` 中对应文件指纹；不自动改页面 `status`。
  - `--check` 遇到 index update 返回 1；参数错误返回 2；auth/接口 warning 仍返回 0。
- `tests/test_task_035.py`
  - 覆盖只对变更文件算指纹、受影响页反查、dry-run 不写、`--apply` 只写索引不改页面状态、exit code、凭证缺失 warning、生产部署过滤 shape、进程级隔离。
- `scripts/README.md`、`wiki-design/02-workflows.md`
  - 补充增量部署防腐用法、成功生产部署语义、dry-run / `--apply` 行为。

验证输出：

```text
$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest -v tests.test_task_035
Ran 6 tests in 0.088s
OK

$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m py_compile scripts/dataworks_client.py scripts/wiki_freshness.py scripts/wiki_index.py
exit 0

$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -c "import sys; sys.path.insert(0,'scripts'); import wiki_lint,wiki_graph,wiki_eval; print('泄漏:', [m for m in sys.modules if any(k in m.lower() for k in ('dataworks','wiki_index','alibabacloud','sqlglot'))] or '无')"
泄漏: 无

datawarehouse_lint=0
personal_lint=0
pk_lint=0

$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --check-docs; echo docs=$?
错误: 0
docs=0

$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest discover -s tests
Ran 146 tests in 54.782s
OK (skipped=1)
```

真实增量 dry-run smoke：

```text
$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_freshness.py \
  --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk \
  --incremental-deployments \
  --project-id 96107 \
  --max-pages 1 \
  --json

mode incremental_deployments
dry_run True
changed_files 100
affected_pages 0
index_updates 0
warnings []
first_file {'deployment_id': 2472562, 'file_id': 500657796, 'file_version': 17, 'indexed': True, 'fingerprint_changed': False}
```

偏离或异常：

- MCP 未暴露，按任务约定使用 SDK 回退路径。
- SDK `ListDeployments` 没有 start time 参数，只有 `end_execute_time/end_create_time`；本实现支持 end time + page/max-pages。时间窗下界需要后续若官方接口提供 cursor/下界参数再扩展。
- 真实 smoke 为 dry-run，未修改 pk 仓索引或页面。

## Evaluation by claude · 2026-06-25

**Verdict: PASS。** M2 命门（增量语义=生产部署变更）守住,兼容性 + dry-run 全过,变更增量防腐闭环。

### 命门：生产部署变更语义（独立验代码）

`dataworks_client.py:323`：`if deployment.Status != 1 or deployment.ToEnvironment != 2: continue`——**双重过滤:成功(Status=1)+ 生产(ToEnvironment=2)**。这是"成功部署到生产"的代码保证;开发态草稿无成功生产部署记录、不进增量。Step 0 codex 实跑确认字段语义（`ToEnvironment=2`/`Status=1`,样本 deployment 2472542 → FileId 500424882）。MCP 未暴露走 SDK 回退,符合 task 约定。

### 兼容性 + 安全（独立复验）

| 核验 | 结果 |
| --- | --- |
| 核心工具进程级零依赖 | **泄漏: 无** ✓ |
| 现有库行为不变 | datawarehouse / personal lint=0 ✓ |
| 全量回归 | **146 OK (skipped=1)** ✓ |
| dry-run 默认不写 | `dry_run = not apply`,`--apply` 才写;真实 smoke 后 pk 工作树 **0 改动** ✓ |
| 只算变更文件 | 只对部署 FileId `GetFile`,指纹比对去重（`fingerprint_changed` 控制）✓ |

真实 dry-run smoke：`changed_files=100`（max-pages 1）、`affected_pages=0`（这批变更文件无对应口径页,库当前仅 4 DWD 有页,合理）、`index_updates=0`（dry-run）。

### 已知局限（codex 诚实标注，记给运营）

`ListDeployments` **无 start_time 参数**,只有 `end_execute_time` + `page/max-pages`——增量是"从最近往前翻 N 页",时间窗下界靠 max-pages,无精确 start 下界。靠 **fingerprint 比对去重**兜底（指纹没变跳过）。运营注意:**周期内部署量大时调大 `--max-pages` 避免漏**;将来官方接口若提供 cursor/下界再扩展。

### 结论

RFC-028 M2 闭环：DataWorks 生产部署变更 → 只算变更文件指纹 → 反查受影响口径页 → 待复核（机器只筛、默认 dry-run）。TASK-035 done 有效（引擎 `0e7dab5`）。**RFC-028 核心(M1 全量索引+反查 / M2 增量防腐 / M3 分层方法论)全闭环,仅剩 M4 sqlglot 血缘(可选)。**
