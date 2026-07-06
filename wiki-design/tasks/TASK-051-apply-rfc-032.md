---
id: task_20260706_051
title: Apply RFC-032 — GetFileVersion 取码 + evidence 片段模式 + reverse binding 键 / origin
author: claude
executor: claude
status: done
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

## Execution log by claude · 2026-07-06

### 实现位置

- **任务一** `scripts/dataworks_client.py::get_file_version_code(raw_ref, file_version)`：`GetFileVersion` 拉指定已提交版本 `Data.FileContent`；`parse_ref` / `_safe_error` / `code_sha256`（dw-code-v1）风格一致；`INVALID_VERSION` / `CONTENT_MISSING` 错误封装。
- **任务二** 同文件新增 evidence 层 + CLI（此前该模块无 CLI）：
  - `scan_code_evidence`：纯函数、进程内 regex（默认忽略大小写，`--case-sensitive` 关闭）、命中行 ±context 合并、**全部片段合计行数硬封顶**（默认 200，`--max-lines`），`.*` 无法退化成全量 dump；超限标 `truncated`。
  - 缓存 `default_version_cache_dir()` = `<engine>/.cache/dataworks/file_versions/`，key `(project, file_id, file_version)`，已提交版本不可变、永不失效；引擎 `.gitignore` 是 allowlist（`*` 打头），该目录天然不进 Git / 不被 gitignore-aware 检索。
  - `main()`：`evidence --ref --pattern* --context --max-lines --json`；无 DEPLOYED 版本 → `NO_DEPLOYED_VERSION` exit 1。
- **任务三** `scripts/wiki_index.py`：
  - `item_binding_keys` / `item_binding_basename_keys`（仅 `source_binding=parsed`，与查询侧同用 `normalize_table_key`）接入 `item_lookup_keys` / `item_lookup_basename_keys`；旧索引无字段 → 空集，行为不变。
  - `origin` 子命令：`build_origin_report`（inputs 向上 BFS，默认 max-hops 10）+ `render_origin`；多上游全列；**链级去噪**——同一 ODS 处理链已由 extract 项给出 parsed 来源时，`pre`/终表等 inferred 阶段不再列 unresolved（真实 smoke 中发现的噪音，实现时补充）。
  - 未命中提示语追加线上表名反查说明（`test_task_042` 的 `assertIn` 兼容）。
- 文档：`scripts/README.md` 新增「dataworks-client evidence」段 + wiki-index 段补 binding 反查/origin；`wiki-design/02-workflows.md` 答疑回源段新增「回源取码规则」（已部署版本链路强制 + evidence 优先 + 禁裸调）、反查路由段补第 7/8 条。

### 验证

```text
tests.test_task_051: Ran 19 tests, OK
六层回归 040/042/032/033: Ran 28 tests, OK
全量: OK (skipped=2)   # 第 2 个 skip 为 test_task_025 rg 不在本 shell PATH（环境性 skipUnless，与本次改动无关）
离线三件套: 泄漏: 无
--check-docs: 错误 0
.cache 未被 git 跟踪（allowlist gitignore）
```

### 真实验收（knowledge-pk 只读，env 凭证，project 96107）

```text
reverse --table loan_biz.user_feedback
→ Recommended: [user] DWD dwd_user_feedback_dly · has_knowledge_page
  ODS upstream: ods.loan_biz_autosync_2_user_feedback.extract 等 3 项

origin --table pk_data.dwd_service_cs_work_status_records_dly
→ Online origins: mysql:pak_ppdai_cs_voice.cs_work_status_records · via datasource pak_ppdai_cs_voice
  （去噪后无冗余 unresolved）

evidence --ref file:96107/500338693 --pattern repay_amount --context 2
→ file_version 9 (DEPLOYED) · commit 2026-04-08 · code_lines 165 · snippet_lines 20（非全量）
  二跑 cache: hit，指纹一致
```

### Commits

- 规格：`98be85b`（RFC-032 + TASK-051 + 索引）
- 实现：`d61321f`（`[apply rfc-032]`）
- RFC-032 已登记 `## Applied in d61321f`。

### 偏离或异常

- knowledge-pk 仓零改动（验收只读），符合约束 6。
- origin 链级去噪为实现期补充（规格只要求"未解析注明"），已在 RFC Applied 段与 README 说明，fixture 覆盖两个方向（同链去噪 / 独立链保留）。

## Evaluation by codex · <date>

（角色对调：本 task claude 执行，codex 可追加复核。）
