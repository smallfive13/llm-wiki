---
id: task_20260623_031
title: Apply RFC-028 M1 — DataWorks 全量代码索引（受管共享基线 + 分层 + 指纹）
author: claude
executor: codex
status: pending
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

## Execution log by codex · <date>

（执行者填写）

## Evaluation by claude · <date>

（评估者填写）
