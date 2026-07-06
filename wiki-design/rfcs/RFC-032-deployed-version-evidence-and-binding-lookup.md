---
id: rfc_20260706_032
title: 已部署版本取码 + evidence 证据片段模式 + reverse 线上 binding 查询键 / origin 溯源
author: claude
status: accepted
created: 2026-07-06
updated: 2026-07-06
targets:
  - scripts/dataworks_client.py
  - scripts/wiki_index.py
  - scripts/README.md
  - wiki-design/02-workflows.md
  - tests/
reviewers:
  - codex
  - user
---

# RFC-032: 已部署版本取码 + evidence 片段 + binding 反查

## 背景（knowledge-pk 答疑效率复盘，用户 2026-07-06 提出）

三个引擎侧根因导致生产答疑慢 / 有正确性风险：

1. **上下文爆炸**：一次答疑中 agent 绕过 `dataworks_client.py` 裸调 SDK `ListFileVersions`，多版本 `FileContent`（宽表 SQL）约 123.5k token 进模型上下文。引擎封装 `list_file_versions` 本身已丢弃 `FileContent`，但**没有提供"拉指定已部署版本内容 + 只输出证据片段"的通道**，agent 才会裸调。
2. **草稿态正确性风险**：`get_file_code()`（GetFile）返回设计态最新草稿，可能比任何 DEPLOYED 版本新；用它确认"线上怎么算"不可靠。`get_latest_deployed_version()` 已能拿 prod `file_version`，但**没有按版本取内容的配套方法**（SDK `GetFileVersion` 可用，响应含 `FileContent`）。
3. **线上表名反查 miss**：`wiki_index.py reverse` 的 `item_lookup_keys()` 只查 `table/inputs/outputs/node_name`；TASK-048/050 已回填 `source_binding=parsed` 330 条 + `source_datasource/source_tables/source_database`，这些线上源表键没接进查询入口，查 `loan_biz.user_feedback` 这类"线上 datasource.table"直接 miss；也没有"从仓内表向上追线上来源"的 origin 通道。

## 提案

### 1. `get_file_version_code(raw_ref, file_version)`（正确性修复，其它两项依赖）

`dataworks_client.py` 新增：走 `GetFileVersion` API 拉指定已提交版本内容（`Data.FileContent`），沿用 `parse_ref` / `_safe_error` / `code_sha256`（dw-code-v1）风格，返回 `DataWorksFileCode`。与 `get_latest_deployed_version()` 组合成标准路径：**先元信息定位 prod 版本 → 再拉那一版内容**。

### 2. evidence 证据片段模式 + 版本缓存（CLI）

`dataworks_client.py` 增加 CLI（此前是纯库，无入口）：`evidence` 动词。

- 输入：`--ref file:<project>/<fileId>`、`--pattern <regex>`（可多个）、`--context N`（默认 5）。
- 行为：`get_latest_deployed_version` → `get_file_version_code` → 进程内 regex scan。
- 输出只含：`file_id` / `file_version` / `commit_time` / dw-code-v1 指纹 / 每 pattern 命中情况 / 命中行 ±N 行片段。**整段 SQL 严禁落 stdout**——除意图约束外加硬闸：全部片段合计行数封顶（默认 200，超限截断并标记），防止 `.*` 这类 pattern 把片段模式退化成全量 dump。
- 缓存：按 `(project, file_id, file_version)` 缓存内容——已提交版本不可变，**缓存永不失效**。位置 `<engine>/.cache/dataworks/file_versions/`：引擎 `.gitignore` 为 allowlist（`*` 打头），该目录天然不进 Git、不被 gitignore-aware 检索工具扫到；不写进任何知识库实例。

### 3. reverse 接入 source binding 键 + origin 溯源

`wiki_index.py`：

- `item_lookup_keys()` / `item_lookup_basename_keys()` 增加 binding 键（仅 `source_binding=parsed` 项）：`<source_database>.<t>`、`<source_datasource>.<t>`（逐 `source_tables`）与 basename `<t>`，与查询侧同用 `normalize_table_key` 归一。效果：`reverse --table loan_biz.user_feedback` / `loan_biz_autosync_3.user_feedback` / `user_feedback`（basename 兜底）都命中对应 ODS extract item 并照常给下游 DWD/DWB。
- 新增 `origin` 子命令：从仓内表沿 `inputs` 向上 BFS 追到带 binding 的 ODS item，输出线上 `datasource.table`（含 `db_type:source_database`），多条上游全部列出；`source_binding != parsed` 的上游注明未解析。
- 未命中提示语追加："若查询的是线上库表（datasource.table），已支持直接输入线上表名反查；仍未命中可能是该同步任务 binding 未解析。"

### 不变量

索引契约不变（读侧增强，不写索引）；`wiki_lint/graph/eval` 离线零依赖不变；`wiki_index` 离线不联网不变（origin/binding 只读本地索引）；现有六层反查行为逐字节回归；凭证只从 env。

## 真实摩擦来源

knowledge-pk 生产答疑复盘（用户 2026-07-06）：123.5k token 裸调事故 + GetFile 草稿态风险 + `loan_biz.user_feedback` 反查 miss。pk 侧 `AGENTS.md` 答疑规范已更新为引用本 RFC 能力（pk 仓不在本 RFC 范围）。

## 验证方式

- 单测：GetFileVersion 取码（含错误封装 / 版本参数校验）、evidence scan（命中 / 合并 / 封顶截断 / 输出不含全量 SQL 断言）、缓存命中不再调 API、binding 键三种形态命中、origin 溯源 fixture、未命中提示语、六层回归、离线隔离。
- 真实验收（knowledge-pk 实例 + env 凭证，region ap-southeast-1 / project 96107）：`reverse loan_biz.user_feedback` 命中 ODS extract + 下游；`origin pk_data.dwd_service_cs_work_status_records_dly` 输出 `pak_ppdai_cs_voice.cs_work_status_records`;evidence 对宽表 file ref 输出片段而非整段 SQL。
- 不改 knowledge-pk 仓内容。

## 替代方案

1. 只写答疑规范禁止裸调、不给引擎通道：否决——没有合规通道时规范挡不住下一次裸调（本次事故已证明）。
2. evidence 输出整段代码由 agent 自行截取：否决——整段进上下文正是事故本身。
3. binding 反查建独立命令而非接入 reverse：否决——用户心智里"查表"就是 reverse 一个入口，分裂入口增加误用。

## 影响范围

`scripts/dataworks_client.py`（新方法 + CLI + 缓存）、`scripts/wiki_index.py`（lookup 键 + origin + 提示语）、`scripts/README.md`、`wiki-design/02-workflows.md`（答疑回源段：确认"线上怎么算"必须走已部署版本链路 / evidence 模式，GetFile 是草稿态）、`tests/`。

## Decision

**Accepted**（用户 2026-07-06 直接指令给出完整规格与验收标准，本 RFC 为按仓库惯例补记；授权 claude 实现，executor 例外为 claude）。

## Applied in d61321f

- Applied by claude on 2026-07-06。三项全部落地：`get_file_version_code`（GetFileVersion）、evidence CLI（片段 + 行数硬闸 + `(file_id, file_version)` 不变缓存）、`wiki_index` binding 查询键 + `origin` 子命令 + 未命中提示语。
- 真实验收全过：`reverse loan_biz.user_feedback` 命中 ODS extract + 下游 `dwd_user_feedback_dly`；`origin pk_data.dwd_service_cs_work_status_records_dly` → `mysql:pak_ppdai_cs_voice.cs_work_status_records`；evidence 对 165 行宽表 SQL 只输出 20 行片段、二跑 cache hit。
- `tests/test_task_051.py` 19 项；全量回归 OK；离线三件套零依赖；knowledge-pk 仓零改动。
