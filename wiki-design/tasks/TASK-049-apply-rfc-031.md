---
id: task_20260703_049
title: Apply RFC-031 — 数据源解析 sanitized DTO + 禁词门禁 + 数据源巡检（引擎侧）
author: claude
executor: codex
status: done
type: apply
created: 2026-07-03
updated: 2026-07-03
related_rfcs: [RFC-031]
---

# TASK-049: Apply RFC-031 引擎侧

## 目标

把 RFC-031 落到引擎：`ListDataSources` 数据源解析（→ sanitized DTO：`datasource_name / db_type / database_name / resolution`）+ `datasource_map.json` 生成支持 + 索引 `source_database`/`source_db_type` 字段支持 + freshness 数据源巡检。**不写 knowledge-pk 实例数据**（回填是 TASK-050）。

## 前置条件

- **RFC-031 status = accepted**（Decision 已登记）。
- Step 0 基线已由 RFC-031 review 实跑钉死（`ListDataSources` shape、65 数据源、`Content` JSON、`database` 直取 vs `jdbcUrl` 拆库名分布、46/46 命中 0 失败），不重跑 survey。
- 引擎 working tree clean；命令写完整 conda 路径（勿放 shell 变量）。

## 强约束

1. **接口钉死**：`ListDataSources`（`EnvType=1` PROD），消费 `DataSources[*].Content`；`GetDataSourceMeta` 不用。凭证只从 env。
2. **sanitized DTO 是唯一出口**：解析函数内部消费 `Content` 后立即丢弃原始对象，只返回 `{datasource_name, db_type, database_name, resolution}`（可选 `source_hash`/`updated_at`）。**严禁透传** `Content` 原文 / `jdbcUrl` / `address` / `endpoint` / `host` / `port` / `username` / `password` / `accessKey`。
3. **禁词硬测试（本 task 核心门禁）**：fixture 与真实 smoke 的全部输出（DTO 序列化、map 文件、日志）做字符串扫描，禁止出现 `jdbc:`、`://`、`host`、`address`、`endpoint`、`port`、`username`、`password`、`accessKey`、`secret`、`token`。JDBC 拆库名只允许内存中提取 database segment / `databaseName` 参数；拆不出 → `resolution: failed`，不落原始串。
4. **`datasource_map.json` = 受管共享基线**（非派生层）：稳定排序、无 volatile、无敏感串；生成逻辑归引擎，落地在实例 `.wiki/`；`instance_label` v1 不做。
5. **索引契约**：`source_database` / `source_db_type` additive 可选，不 bump `index_version=2`；**兼容 fixture**：旧 index 无新字段时 reverse / freshness 行为逐字节不变。
6. **freshness 数据源巡检**：轻量入口（子命令或选项）——重拉 `ListDataSources` → diff `datasource_map.json` → `database/db_type` 变（别名改指向）输出待复核建议；默认 dry-run，**不自动改索引/页面**；`--apply` 只更新 map。离线三件套零依赖不变。

## 步骤

1. `scripts/dataworks_client.py`：`list_datasource_bindings(project_id)` → sanitized DTO list（含 mysql `database` 直取 / `jdbcUrl` 拆库名 / mongodb / sqlserver 分支 + `resolution: failed` 兜底）。
2. `scripts/wiki_index.py`：`datasource_map.json` 读写 + 索引 `source_database`/`source_db_type` 附着支持（供 TASK-050 消费）。
3. `scripts/wiki_freshness.py`：数据源巡检入口（约束 6）。
4. `tests/test_task_049.py`：`database` 直取 / `jdbcUrl` 拆库名（常见 + 带参数格式）/ 异常格式→failed / **禁词扫描断言（fixture 全输出）** / map 稳定排序 / 旧 index 兼容逐字节 / 巡检 diff（database 变→待复核，没变→no-op）/ 离线隔离。
5. `wiki-design/02-workflows.md`（数据源解析层 + 巡检 + 答疑口径："线上库"信息来源与边界）+ `scripts/README.md`。
6. 限量真实 smoke：拉 project 96107 全量 65 数据源 → DTO 输出禁词扫描 0 命中 → 脱敏记录（只记 name/db_type/resolution 计数，不记 database 值也行，记了也须过禁词扫描）。
7. 引擎 commit；RFC-031 末尾登记 `## Applied in <sha>`。

## 验证

```bash
cd /Users/zhangjunwu/workspace/llm-wiki/llm-wiki
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -c "import sys; sys.path.insert(0,'scripts'); import wiki_lint,wiki_graph,wiki_eval; print('泄漏:', [m for m in sys.modules if any(k in m.lower() for k in ('dataworks','alibabacloud','sqlglot'))] or '无')"
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest -v tests.test_task_049 2>&1 | tail -3
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest discover -s tests 2>&1 | tail -2
```

## 完成后报告格式

- DTO 函数位置 + 两种拆库名分支 + failed 兜底
- 禁词门禁实现点（测试 + smoke 双覆盖）
- map 读写 / 索引附着 / 巡检 diff 挂点
- test_049 明细 + 全量回归 + 离线断言 + 真实 smoke 禁词扫描结果
- commit sha + RFC-031 `Applied in`、偏离或异常

## Execution log by codex · 2026-07-03

### Implementation

- `scripts/dataworks_client.py`
  - 新增 `DataWorksDatasourceResolution` sanitized DTO。
  - 新增 `parse_datasource_resolution()`：支持 `database` 直取、MongoDB `authDb` 兜底、JDBC path / `databaseName` 内存解析、异常格式 `resolution: failed`。
  - 新增 `list_datasource_resolutions(project_id)`：固定 `ListDataSources(env_type=1)`，只返回 sanitized DTO。
  - 新增 `assert_no_datasource_secrets()` 禁词门禁，禁止 sanitized 输出包含 `jdbc:`、`://`、`host/address/endpoint/port`、`username/password/accessKey/secret/token`。
- `scripts/wiki_index.py`
  - 新增 `datasource-map` 子命令，生成 `.wiki/datasource_map.json` 受管共享基线。
  - 新增 `stable_datasource_map()` / `load_datasource_map()` / `attach_datasource_resolutions()`。
  - `--attach-datasource-map` 可在 `source_binding=parsed` 且 map 解析成功的 index item 上附加 `source_database` / `source_db_type`；`index_version` 保持 2。
- `scripts/wiki_freshness.py`
  - 新增 `--datasource-map` 巡检模式：重拉 datasource map，diff 本地 `.wiki/datasource_map.json`，输出 `changes` 和 `datasource_target_changed` review_queue suggestion。
  - 默认 dry-run；`--apply` 只更新 map，不改 index / 页面。
- `tests/test_task_049.py`
  - 覆盖直取 / JDBC / MongoDB / failed 兜底 / 禁词门禁 / map 稳定排序 / index additive attach / 旧 index reverse 兼容 / datasource freshness diff / CLI check exit / 离线三件套零依赖。
- `scripts/README.md`、`wiki-design/02-workflows.md`
  - 补数据源解析层、受管共享基线定位、禁词红线、巡检入口和答疑边界。

实现 commit：

- `a41f2ca1a5c4354057b4b1c91a188911a22be504` (`[apply rfc-031] add datasource resolution map`)

### Verification

离线依赖断言：

```text
泄漏: 无
```

`tests.test_task_049`：

```text
Ran 10 tests in 0.337s
OK
```

全量回归：

```text
Ran 177 tests in 86.224s
OK (skipped=1)
```

docs / base knowledge lint：

```text
wiki-lint v0.1.0 --check-docs
受管块: 6
错误: 0

wiki-lint --root knowledge --check-only
错误: 0 · 警告: 0
```

真实 DataWorks datasource-map smoke（project 96107，按 RFC-031 review 基线，不打印库名）：

```text
items 65
resolution {'parsed': 64, 'failed': 1}
types {'mysql': 47, 'sqlserver': 1, 'mongodb': 15, 'odps': 1, 'holo': 1}
forbidden_hits []
```

真实 freshness datasource-map dry-run smoke（本地尚无 map，因此全部为 added，符合预期）：

```text
mode datasource_map
changes 65
warnings 0
forbidden_hits []
```

真实 index attach smoke（临时目录，`max-pages 1`）：

```text
index_version 2
items 82
source_database_count 26
forbidden_hits []
```

### Deviations / notes

- 未使用 `GetDataSourceMeta`，按 RFC-031 Decision 固定 `ListDataSources`。
- `instance_label` v1 未实现，符合 task 约束。
- 未写 knowledge-pk 实例数据；TASK-050 负责生成 pk map、回填 index、产出 46+ 数据源核对清单并在 Step 3 硬停。

## Evaluation by claude · <date>
