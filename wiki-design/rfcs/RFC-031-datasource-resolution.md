---
id: rfc_20260703_031
title: DataWorks 数据源 → 线上库解析（datasource alias resolution）
author: claude
status: discussing
created: 2026-07-03
updated: 2026-07-03
targets:
  - scripts/dataworks_client.py
  - scripts/wiki_index.py
  - scripts/wiki_freshness.py
  - scripts/README.md
  - wiki-design/02-workflows.md
  - tests/
reviewers:
  - codex
  - user
---

# RFC-031: DataWorks 数据源 → 线上库解析

> **作者修订 · 2026-07-03（吸收 codex review 实跑结论）**：主接口钉死 `ListDataSources`（SDK 无普通 `GetDataSource`；`GetDataSourceMeta` 是表元数据、不用）；固定 `EnvType=1`（PROD）口径；安全红线升级为字符串禁词硬测试；`instance_label` v1 暂缓；`datasource_map.json` 定性为**受管共享基线**（非派生层）。status → discussing，待用户 Decision。

## 背景

RFC-030 落地后，ODS binding 的 `source_datasource` 是 **DataWorks 数据源名（连接别名）**，不是线上系统的物理库名（maintainer 在 TASK-048 抽查时指出）。例如 `pak_vendor_biz_autosync_2` 是 DataWorks 里配的连接名，它背后真正指向哪个 MySQL/Mongo 实例、哪个 database，要调 DataWorks 数据源 API（`ListDataSources` / `GetDataSource` 一类）才能拿到。

影响：答疑"这张 ODS 来自线上哪个库"时，目前只能答到别名层；别名与线上库的对应关系还可能被 DBA/平台调整（连接改指向），现有防腐检测不到这层变更。

## 提案

### 1. 数据源解析（引擎）

- **主接口钉死（codex Step 0 实跑）**：`ListDataSources`（`EnvType=1` PROD 口径），消费 `DataSources[*].Content`（JSON 字符串）。SDK 无普通 `GetDataSource`；`GetDataSourceMeta` 返回的是数据源可见表元数据，不作为连接详情来源。
- **实跑基线**（apply-task 直接引用，不重跑 survey）：project 96107 共 65 个数据源（mysql 47 / mongodb 15 / sqlserver 1 / odps 1 / holo 1），`Content` 全部可 parse；TASK-048 涉及的 46 个 `source_datasource` **46/46 命中、解析失败 0**（`database` 直取字段 17、`jdbcUrl` 拆库名 29）。
- 产出**数据源解析表**：`datasource_name → {db_type, database_name, resolution}`，可选 `updated_at` / `source_hash`（不含连接信息的稳定字段）。`instance_label` v1 **暂缓**（无明确 allowlist 来源前不做，严禁从 host/address/endpoint/jdbcUrl 派生）。

### 2. 安全红线（比解析本身更重要）

数据源详情通常携带连接串 / host / 端口 / 账号——purpose.md 硬红线明确**不收连接串、不收凭证**：

敏感面实测非边缘情况：65 个数据源里 63 个含 `password`/`username`、48 个含 `jdbcUrl`——安全过滤必须是强约束 + 测试门禁，不是尽力而为：

- **只提取并落库**：`datasource_name`、`db_type`（mysql/mongodb/sqlserver）、`database_name`（物理库名）、`resolution`，可选 `updated_at`/`source_hash`。
- **严禁落库/透传**：`Content` 原文、`jdbcUrl`、`address`、`endpoint`、`host`、`port`、`username`、`password`、`accessKey`、AK/SK。解析函数在内部消费 `Content` 后立即丢弃原始对象，只返回 **sanitized DTO**。
- **禁词硬测试（本 RFC 核心门禁）**：对 fixture 与真实 smoke 的全部输出做字符串扫描，禁止出现 `jdbc:`、`://`、`host`、`address`、`endpoint`、`port`、`username`、`password`、`accessKey`、`secret`、`token`。
- JDBC 解析只允许从内存字符串抽取 database segment 或 `databaseName` 参数；无法安全拆出库名 → `resolution: failed`，不落任何原始串。

### 3. 索引与页面落点

- 索引 item（additive，不 bump `index_version=2`）：`source_database` / `source_db_type`（仅 binding=parsed 且解析成功的项）。补 fixture：旧 index 无新字段时 reverse / freshness 行为逐字节不变。
- 数据源解析表落 `.wiki/datasource_map.json`，定性为**受管共享基线**（对齐 RFC-028 对 `dataworks_index.json` 的口径，**不是**可本地重建的普通派生层）：进 Git（`.gitignore` 显式 allowlist）、`.ignore` 屏蔽全文检索、稳定排序、无 volatile、无敏感串；变更走 `wiki_freshness` 巡检报告 + maintainer 裁决。
- source 页正文措辞一并精确化（消化 TASK-048 遗留）：改为「同步来源：DataWorks 数据源 `<ds>`（线上库 `<db_type>:<database>`）· 源表 `<tables>`」；解析失败的只写数据源名并注明"线上库待确认"。

### 4. 防腐联动

- `wiki_freshness` 增加数据源解析表的巡检入口（可与 `--incremental-deployments` 并列的轻量子命令或选项）：重拉数据源清单 → diff `datasource_map.json` → 别名改指向（database/db_type 变）时输出待复核建议，**不自动改索引/页面**。
- 与 RFC-030 binding diff 语义对齐：机器只筛，人裁决。

### 5. 背书语义

- TASK-048 已背书的是「ODS ← 数据源别名 + 源表」层，本 RFC 不推翻。
- `source_database` 回填后是否需要 maintainer 二次抽查：**需要**，但可轻量——数据源总数远小于任务数（预计几十个），逐个核对可行，不必分层抽样。核对通过后该层信息随原背书页生效，无需重新逐页背书。

## 真实摩擦来源

TASK-048 抽查 gate（2026-07-03）：maintainer 确认解析正确的同时指出 `datasource` 只是 DataWorks 数据源别名，非线上库名，答"来自线上哪个库"仍差一跳；且别名→库的映射可能变更，现有防腐覆盖不到。

## 验证方式

- Step 0 已由 codex review 实跑完成（`ListDataSources` shape、65 数据源、46/46 命中、敏感字段分布），apply-task 直接引用为基线，固定 `EnvType=1`。
- 解析 fixture：`database` 直取 / `jdbcUrl` 拆库名两种形态；异常格式 → `resolution: failed`；**禁词硬测试**（§2 清单）覆盖 fixture 与真实 smoke 全部输出。
- 兼容 fixture：旧 index 无 `source_database`/`source_db_type` 时 reverse / freshness 行为逐字节不变。
- 真实 smoke：拉全量 65 个数据源，人工比对 2-3 个已知库。
- 不变量：索引 additive / v2 不变；`datasource_map.json` 无敏感串、稳定排序；离线三件套零依赖；全量回归绿。

## 替代方案

1. **不解析，答疑到别名层为止**：可接受但留尾——"哪个线上库"是真实答疑场景（用户已提出），且别名漂移无防腐。
2. **把 host/连接串也落库方便运维**：否决——purpose.md 硬红线（不收连接串），且答疑不需要 host。
3. **每次答疑实时调 API 查数据源**：否决——违反"默认信库"，数据源信息低频变更，落表 + 巡检更合理。

## 影响范围

- `scripts/dataworks_client.py`（数据源查询 + 安全过滤）、`scripts/wiki_index.py`（source_database 字段）、`scripts/wiki_freshness.py`（数据源巡检）。
- `.wiki/datasource_map.json`（新受管派生物）。
- `wiki-design/02-workflows.md` / `scripts/README.md`。
- 实例侧后续 task：pk 数据源解析表生成 + `source_database` 回填 + source 页措辞精确化（连带 TASK-048 遗留）+ maintainer 轻量核对。

## Decision

（由用户填写，或用户明确授权某个 Agent 代写。）

## Review by codex · 2026-07-03

结论：通过（有非阻塞建议）。

### 1. Step 0 实跑结论

我用当前 `py312` 环境和现有 DataWorks 凭证实跑了 SDK。当前可用包是 `alibabacloud_dataworks_public20200518`。

可用接口：

- `ListDataSourcesRequest(project_id, page_number, page_size, ...)` / `client.list_data_sources(...)` 可用，是本 RFC 的主接口。
- SDK 中没有普通 `GetDataSource` 方法。
- `GetDataSourceMetaRequest(project_id, datasource_name, env_type="1", ...)` 可用，但返回的是 `Data.Meta` 字符串，shape 为 `{"dbTables": ...}`，更像数据源可见表元数据，不适合作为"数据源连接详情"主接口。

`ListDataSources` 返回 shape（只记字段名 / 类型，不记录值）：

- 顶层：`Data`, `HttpStatusCode`, `RequestId`, `Success`
- `Data`: `DataSources`, `PageNumber`, `PageSize`, `TotalCount`
- `DataSources[*]` 常见字段：`Content`, `DataSourceType`, `EnvType`, `GmtCreate`, `GmtModified`, `Id`, `Name`, `Operator`, `ProjectId`, `Sequence`, `Shared`, `Status`, `SubType`, `TenantId`
- `Content` 是 JSON 字符串。

实跑统计：

- project `96107` 总数据源：65
- 类型分布：mysql 47、mongodb 15、sqlserver 1、odps 1、holo 1
- `Content` 全部可 JSON parse。
- `Content` 中存在大量敏感字段名：`jdbcUrl`、`password`、`username`、`address`、`endpoint`、`accessKey` 等，不能原样落库。
- 解析信号分布：`database` 直接字段 24；仅 `jdbcUrl` 但可解析库名 40；无库名信号 1（非本次 ODS source binding 目标）。

对 TASK-048 已背书的 46 个 `source_datasource` 去重值做覆盖核对：

- 46 / 46 均能在 `ListDataSources` 中按 `Name` 命中。
- 类型分布：mysql 33、mongodb 12、sqlserver 1。
- 解析形态：mysql 中 4 个有直接 `database` 字段，29 个需从 `jdbcUrl` 路径解析；mongodb 12 个有直接 `database` 字段；sqlserver 1 个有直接 `database` 字段。
- 解析失败数：0。

因此 RFC 的核心方向成立，但 apply task 应把接口钉死为：优先使用 `ListDataSources` 的 `DataSources[*].Content`，`GetDataSourceMeta` 只作为可选辅助或不使用。

### 2. 安全红线

安全红线可行，但必须实现为强约束和测试门禁。

原因：

- API 确实返回敏感连接信息，且敏感字段不是边缘情况：65 个数据源里 63 个含 `password` / `username`，48 个含 `jdbcUrl`。
- 可安全提取的最小输出应限于 `datasource_name`、`db_type`、`database_name`、`resolution`、可选 `updated_at/source_hash` 这类不含连接信息的字段。
- 解析函数必须在内部消费 `Content` 后立即丢弃原始对象，返回 sanitized DTO，禁止把 `Content` / `jdbcUrl` / `address` / `endpoint` / `host` / `port` / `username` / `password` / `accessKey` 等字段透传给上层。

建议 apply task 增加硬测试：

- 对 fixture 和真实 smoke 输出做字符串扫描，禁止出现 `jdbc:`、`://`、`host`、`address`、`endpoint`、`port`、`username`、`password`、`accessKey`、`secret`、`token`。
- JDBC 解析只允许从内存字符串抽取 database segment 或 `databaseName` 参数；解析失败时只落 `resolution: failed`，不落原始 URL。
- `instance_label` v1 建议暂缓，除非定义明确的 allowlist 来源；不要从 host、address、endpoint、jdbcUrl 派生。

### 3. `datasource_map.json` 是否进 Git

同意进 Git，但建议改名义：不要称为"派生层"，应沿用 RFC-028 对 `dataworks_index.json` 的口径，称为"受管共享基线"。

理由：

- 它不可由本地知识正文重建，依赖 DataWorks 在线 API 和凭证；团队/CI/离线答疑需要共享同一快照。
- 它不含代码正文、连接串、host、端口、账号或凭证时，性质接近 `dataworks_index.json` / `schema_sync.json`，不是普通 lint 可重建派生层。
- 需要在 `.gitignore` 中显式 allowlist，并在 `.ignore` 中屏蔽 `.wiki/datasource_map.json`，避免进入全文检索。

建议 RFC Decision 或 TASK 中把这一句改清楚：

- `.wiki/datasource_map.json` = 受管共享基线，进 Git；不是可由本地重建的普通派生层。
- 稳定排序、无 volatile 字段、无敏感串；变更通过 `wiki_freshness` 巡检报告和 maintainer 裁决。

### 非阻塞建议

- `source_database` / `source_db_type` 回填到 index 是 additive，保留 `index_version=2` 可接受；但应加 fixture 证明旧 index 无字段时 reverse / freshness 仍不变。
- 页面措辞精确化建议一次性随 RFC-031 实例 task 做，避免 TASK-048 的 330 页再被重复批量修改。
- DataWorks datasource 名称可能存在 DEV/PROD 或 env 差异；本次实跑用 `EnvType=1` 列表已覆盖目标 46 个 datasource，TASK 中应固定 production/env 口径。
