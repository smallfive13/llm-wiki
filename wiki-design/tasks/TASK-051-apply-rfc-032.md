---
id: task_20260706_051
title: Apply RFC-032 — GetFileVersion 取码 + evidence 片段模式 + reverse binding 键 / origin
author: claude
executor: claude
status: in-progress
type: apply
created: 2026-07-06
updated: 2026-07-06
related_rfcs: [RFC-032]
---

# TASK-051: Apply RFC-032

> executor 例外说明：本 task 由用户 2026-07-06 直接指令 claude 实现（规格见 RFC-032），不走 codex 执行通道；codex 可后续追加 review。

## 目标

按 RFC-032 三项增强落引擎，依赖顺序：① `get_file_version_code`（GetFileVersion 按版本取码）→ ② evidence CLI（prod 版本定位 + 片段输出 + 版本缓存）→ ③ `wiki_index` binding 查询键 + `origin` 子命令 + 未命中提示语。

## 前置条件

- RFC-032 accepted（用户直接指令）。引擎 working tree clean。凭证 env（region ap-southeast-1）。

## 强约束

1. **正确性链路**：确认"线上怎么算"= `get_latest_deployed_version` → `get_file_version_code(prod file_version)`；不得用 `get_file_code`（草稿态）替代。
2. **evidence 输出硬闸**：stdout 只含元信息 + 命中片段；全部片段合计行数封顶（默认 200，`--max-lines` 可调），超限截断并显式标记——**任何情况下不得输出整段代码**。
3. **缓存**：key=(project, file_id, file_version)，已提交版本不可变、永不失效；位置 `<engine>/.cache/dataworks/file_versions/`（allowlist gitignore 下天然不进 Git / 不被检索）；不写实例目录。
4. **binding 键只读**：`item_lookup_keys` 扩展仅消费索引已有字段（source_binding/source_datasource/source_tables/source_database），不写索引；与查询侧同用 `normalize_table_key` 归一；无 binding 字段的旧索引行为逐字节不变（六层回归）。
5. `origin` 离线只读本地索引；多上游全列；`source_binding != parsed` 注明未解析。
6. 离线三件套零依赖不变；全量回归绿；不改 knowledge-pk 仓内容。

## 步骤

1. `dataworks_client.py`：`get_file_version_code`（`_safe_error`/`parse_ref` 风格，`Data.FileContent` 缺失 → `CONTENT_MISSING`）。
2. `dataworks_client.py`：evidence 引擎函数（`scan_code_evidence` 纯函数可离线测）+ 版本缓存读写 + CLI `evidence` 动词（`--ref/--pattern*/--context/--max-lines/--case-sensitive/--json`）。
3. `wiki_index.py`：`item_binding_keys` / basename 变体接入 `item_lookup_keys`；`origin` 子命令（BFS 上溯 + 渲染）；未命中提示语追加。
4. `tests/test_task_051.py`：版本取码（mock）/ scan 命中·合并·封顶 / 缓存二次命中不调 API / 输出无全量 SQL 断言 / binding 三形态命中 + 下游照常 / origin fixture（含未解析分支）/ 提示语 / 离线隔离。
5. `scripts/README.md` + `wiki-design/02-workflows.md`（答疑回源段补"已部署版本链路 + evidence 模式"）。
6. 真实验收（pk 实例只读）：reverse `loan_biz.user_feedback`；origin `pk_data.dwd_service_cs_work_status_records_dly` → `pak_ppdai_cs_voice.cs_work_status_records`；evidence 宽表 ref 出片段。
7. 引擎 commit；RFC-032 登记 Applied。

## 验证

```bash
cd /Users/zhangjunwu/workspace/llm-wiki/llm-wiki
python3 -c "import sys; sys.path.insert(0,'scripts'); import wiki_lint,wiki_graph,wiki_eval; print('泄漏:', [m for m in sys.modules if any(k in m.lower() for k in ('dataworks','alibabacloud','sqlglot'))] or '无')"
python3 -m unittest tests.test_task_051 tests.test_task_040 tests.test_task_042 2>&1 | tail -2
python3 -m unittest discover -s tests 2>&1 | tail -2
# 真实验收见步骤 6
```

## 完成后报告格式

- 三项实现位置 + 关键判定
- test_051 明细 + 六层回归 + 全量 + 离线断言
- 真实验收输出（reverse/origin/evidence，evidence 输出须体现片段而非全量）
- commit sha + RFC-032 Applied、偏离或异常

## Execution log by claude · <date>

## Evaluation by codex · <date>

（角色对调：本 task claude 执行，codex 可追加复核。）
