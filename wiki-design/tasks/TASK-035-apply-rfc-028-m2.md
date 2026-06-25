---
id: task_20260625_035
title: Apply RFC-028 M2 — DataWorks 变更增量（生产部署变更 → 反查受影响页待复核）
author: claude
executor: codex
status: pending
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

（执行者填写）

## Evaluation by claude · <date>

（评估者填写）
