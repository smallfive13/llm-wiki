---
id: rfc_20260703_031
title: DataWorks 数据源 → 线上库解析（datasource alias resolution）
author: claude
status: proposed
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

## 背景

RFC-030 落地后，ODS binding 的 `source_datasource` 是 **DataWorks 数据源名（连接别名）**，不是线上系统的物理库名（maintainer 在 TASK-048 抽查时指出）。例如 `pak_vendor_biz_autosync_2` 是 DataWorks 里配的连接名，它背后真正指向哪个 MySQL/Mongo 实例、哪个 database，要调 DataWorks 数据源 API（`ListDataSources` / `GetDataSource` 一类）才能拿到。

影响：答疑"这张 ODS 来自线上哪个库"时，目前只能答到别名层；别名与线上库的对应关系还可能被 DBA/平台调整（连接改指向），现有防腐检测不到这层变更。

## 提案

### 1. 数据源解析（引擎）

- `dataworks_client` 增加数据源清单/详情查询：按 project 拉取数据源列表，提取每个数据源的**线上库信息**。
- **Step 0 必核**（本 RFC 最大不确定点）：实跑确认 SDK 的可用接口（`ListDataSources` / 新版 `ListDataSourceInstances` 等）、返回 shape、以及连接信息以什么形态暴露（结构化字段还是 JDBC URL 字符串）。
- 产出一张**数据源解析表**：`datasource_name → {db_type, database_name, instance_label?}`。

### 2. 安全红线（比解析本身更重要）

数据源详情通常携带连接串 / host / 端口 / 账号——purpose.md 硬红线明确**不收连接串、不收凭证**：

- **只提取并落库**：`db_type`（mysql/mongodb/sqlserver）、`database_name`（物理库名）；可选 `instance_label`（人可读的实例别称，如有且不含敏感信息）。
- **严禁落库**：完整 JDBC/连接 URL、host、端口、用户名、密码、AK/SK。解析函数必须在返回前丢弃这些字段，fixture 断言输出不含 `jdbc:` / `host` / `password` 等模式。
- 若 API 返回的 URL 无法安全拆出库名（格式异常），标 `resolution: failed`，不落任何原始串。

### 3. 索引与页面落点

- 索引 item（additive，不 bump `index_version=2`）：`source_database` / `source_db_type`（仅 binding=parsed 且解析成功的项）。
- 数据源解析表落 `.wiki/datasource_map.json`（受管派生物，进 Git，同守"无凭证/无连接串"基线）。
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

- Step 0 实跑：可用 API、返回 shape、连接信息形态（脱敏记录，只记字段名不记值）。
- 解析 fixture：结构化字段 / JDBC URL 两种形态拆库名；异常格式 → `resolution: failed`；**输出不含凭证/host/端口/URL 的断言**（安全 fixture 是本 RFC 的核心测试）。
- 真实 smoke：拉全量数据源（预计几十个），人工比对 2-3 个已知库。
- 不变量：索引 additive / v2 不变；`datasource_map.json` 无敏感串；离线三件套零依赖；全量回归绿。

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
