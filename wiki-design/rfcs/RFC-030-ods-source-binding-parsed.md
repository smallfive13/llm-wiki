---
id: rfc_20260703_030
title: ODS 源表 binding 从命名推断升级为配置解析（parsed）+ 批量快审背书流程
author: claude
status: discussing
created: 2026-07-03
updated: 2026-07-03
targets:
  - scripts/wiki_index.py
  - scripts/dataworks_client.py
  - scripts/wiki_freshness.py
  - wiki-design/02-workflows.md
  - scripts/README.md
  - tests/
reviewers:
  - codex
  - user
---

# RFC-030: ODS 源表 binding 配置解析 + 批量快审背书

> **作者修订 · 2026-07-03（回应 codex review 实跑结论）**：本版已按 review 调整——解析规则钉死为 reader-only 真实 shape（mysql/sqlserver `connection[]`、mongodb `collectionName`）、`source_tables` 改 list、binding 枚举扩为 `parsed/inferred/unparsed/ambiguous`、覆盖面明确 DI 336/974、freshness 只重解析 changed 项、抽样改按 reader stepType 分层。status → discussing，待用户 Decision。

## 背景

ODS 表对应的**线上源表**（源系统 MySQL/Mongo 表）目前是靠 **ODS 命名模糊匹配**推断的（如 `ods_pak_vendor_biz_merchant_goods` → 猜数据源 `pak_vendor_biz` 的 `merchant_goods` 表）。三个问题：

1. **不可靠**：`autosync_2/3` 版本后缀、表名截断、多库同名、命名不规范都会猜错。
2. **无法表达权威性**：模糊匹配和权威事实长得一样（都是 `review: false` 的 source 页正文），答疑分不清"猜的"和"配置里写的"。
3. **背书不可行**：974 个 ODS source 页逐页人工核对源表映射不现实，导致 ODS 映射永远挂着"未经人工背书"免责。

而 DataWorks 数据集成（DI）同步任务的配置里**明确写着** `DataSource` + `table`——这是机器可解析的权威事实，且这些任务全部已在索引（1353 items 含 code_fingerprint），变更可被增量防腐检测。

**治理前提（不动摇）**：解析自权威配置 ≠ 人工背书。`review: true` 的不变量仍是"当前仍由人背书"（L3 红线），机器不得 auto 设置。本 RFC 用**正交信号**表达来源权威性，并用"批量快审"降低人工背书成本，不是让机器绕过背书。

## 提案

### 1. binding 解析（引擎）

**覆盖面（codex 实跑钉死）**：974 个 ODS 任务中 `DI` 336（全部 content 可 `json.loads`）、`PYODPS3` 638。**首批 parsed 上限 ≈ 336**；PYODPS3 默认保持 `inferred`，除非后续另立脚本解析策略。不得暗示"974 全可 parsed"。

**解析规则（按实跑 shape，非通用 `steps[].parameter.datasource/table`）**：

- 只解析 `steps[]` 中 `category == "reader"` 的 step；**writer ODPS step 的 `parameter.table` 是目标表，严禁当源表**。
- MySQL / SQLServer reader（253 + 1 个）：从 `parameter.connection[]` 取 `datasource` + `table[]`（table 是 list）。
- MongoDB reader（82 个）：从 `parameter.datasource` + `parameter.collectionName` 取 binding；collectionName 落入 `source_tables`，文档注明 collection→source_tables 的语义映射。

**索引字段**（additive，不 bump `index_version=2`，仍守受管基线——无 volatile、无代码正文、稳定排序）：

- `source_binding` 枚举四态：
  - `parsed`：reader shape 受支持，binding 完整提取；
  - `ambiguous`：DI JSON 可读但 shape 超出支持（多 reader、connection 缺 datasource、table 空等），附 `binding_warnings`；
  - `unparsed`：解析尝试失败（非 JSON / 结构异常）；
  - `inferred`：未走解析（PYODPS3 等），沿用命名推断。
- `source_datasource` + `source_tables`（**list**，多表不截断不丢信息）；`binding_warnings`（可选）。

### 2. 三个正交信号的联动（实例约定 + 引擎支持）

| 信号 | 承载 | 规则 |
| --- | --- | --- |
| 来源权威性 | `source_binding` + `confidence` | binding=`parsed` 的 ODS source 页 confidence 可升 `medium`（机器事实、来源权威）；`inferred` 保持 `low`。写入 pk `AGENTS.md` confidence 规则表（扩展 TASK-045）。 |
| 变更风险 | 既有 freshness 锚点 + 增量防腐 | **只对 changed file 且 `program_type=DI` 或已 `source_binding=parsed` 的项**重解析 binding（本地 JSON parse，成本可忽略；不扫全量 974）。diff 结构化区分 `fingerprint_changed` 与 `binding_changed`（`binding_previous/current/changed` 字段）：仅指纹变→只更指纹；binding 变（换源表/换数据源）→标待复核。 |
| 人工背书 | `review: true`（仍是唯一途径） | 见下"批量快审"。 |

### 3. 批量快审背书流程（写入 02-workflows）

把 ODS 映射背书从"逐页考证"降为"抽查解析器 + 批量确认"：

1. maintainer 对解析结果做**分层抽查**（codex review 钉死，随机 20 不够）：
   - 按 reader `stepType` 分层，mysql / mongodb / sqlserver 都必须覆盖（sqlserver 仅 1 个则必查）；
   - 按 `source_datasource` 去重抽样，避免样本集中在同一源系统；
   - 抽样记录含：解析器 commit、索引 snapshot、样本 `file_id`/`node_name`、reader stepType、`source_datasource`/`source_tables`、人工核对结论。
2. 抽查通过 → maintainer 可批量设 `review: true`，**范围仅限「本次解析器支持且抽查通过的 binding shape」**（如 mysql connection-list、mongodb collectionName）；`ambiguous` / `unparsed` / `inferred` 一律不在批量背书范围。背书依据记入 log 与 review_queue 决议——背书责任仍在人，核对单位从"每页"变成"解析器 + 批次"。
3. 后续增量防腐发现某 parsed 文件 `binding_changed` → 该页进待复核 queue（**只标记，不自动撤 `review:true`**，撤回仍需人确认——与 L3 红线一致）。

### 4. 答疑口径

- `parsed` + `review:true`：直接答，可省"未经人工背书"免责。
- `parsed` + `review:false`：答时标注"解析自同步任务配置（权威来源），待批量背书"。
- `inferred`：答时必须标注"按命名推断，未经核实"。

## 真实摩擦来源

用户 2026-07-03 提出：ODS 线上表映射靠名字模糊匹配、被视为未背书、还可能变更；直接从脚本解析 DataSource+table 是否应视为背书。经讨论确认：解析提升权威性但不该占用 review 语义，正确落点是 binding 字段 + confidence + 防腐联动 + 批量快审。974 个 ODS 页逐页背书不可行是真实运营瓶颈。

## 验证方式

- Step 0 已由 codex review 实跑完成：DI 336 / PYODPS3 638，336/336 JSON 可解析，reader 分布 mysql 253 / mongodb 82 / sqlserver 1（脱敏样本 shape 见 review 段）。apply-task 直接以此为基线。
- 解析 fixture：mysql `connection[]`（含**多 table list**）、mongodb `collectionName`、sqlserver、writer ODPS step 被排除、多 reader / 缺 datasource → `ambiguous` + `binding_warnings`、非 JSON → `unparsed`、PYODPS3 → 保持 `inferred` 不误解析。
- binding drift fixture：指纹变 + binding 变 → `binding_changed` 待复核；指纹变 + binding 不变 → 仅更新指纹；增量路径只重解析 changed 且 DI/parsed 项（断言未触碰未变更项）。
- 真实 smoke：按 stepType 分层抽样解析并人工比对 DataWorks 控制台（sqlserver 必含）。
- 不变量：索引 `index_version=2`、新字段 additive、无代码正文；`wiki_lint/graph/eval` 离线零依赖；全量 unittest 绿。

## 替代方案

1. **parsed 即 auto `review: true`**：否决——污染背书语义（"人确认过" vs "机器抄配置"不可分），破坏 L3 人控与 endorsement 维度的含义。
2. **维持模糊匹配 + 逐页人工背书**：否决——974 页不可行，映射将永远处于"未核实"状态。
3. **答疑时实时回源解析、不落库**：否决——违反"默认信库"决策树（每问必查 SDK），且无防腐、无审计。

## 影响范围

- `scripts/dataworks_client.py` / `scripts/wiki_index.py`：DI 配置解析 + 索引 binding 字段。
- `scripts/wiki_freshness.py`：漂移时重解析 binding 并 diff。
- `wiki-design/02-workflows.md`：批量快审背书流程 + 答疑口径。
- `scripts/README.md`、`tests/`。
- 实例侧后续 task（不在本 RFC targets）：回填 974 个 ODS binding、ODS source 页正文补 parsed 映射行、pk `AGENTS.md` confidence 规则扩展、maintainer 首次抽查 + 批量背书。

## Decision

（由用户填写，或用户明确授权某个 Agent 代写。）

## Review by codex · 2026-07-03

结论：需调整。

我同意 RFC 的核心方向：把 ODS 源表映射拆成 `source_binding` 这类正交信号，而不是污染 `review:true` 语义；批量快审也比 974 页逐页背书更可操作。但实跑 survey 发现提案里对 DI JSON 字段路径和覆盖面的描述不够准确，必须先钉死，否则 TASK 容易实现错解析器。

### 1. 可解析性实跑结论

基于当前 knowledge-pk `.wiki/dataworks_index.json`（`index_version=2`、1353 items）筛 ODS 任务，得到：

```text
total_items 1353
ods_items 974
program_type_distribution
PYODPS3 638
DI 336
```

也就是说，DI 只覆盖 336/974（约 34.5%），多数 ODS 任务是 `PYODPS3` 脚本/预处理任务。RFC 里“脚本模式保持 inferred”方向对，但后续实例 task 不能暗示 974 个 ODS 都能 parsed；应明确首批 parsed 上限约为 DI 336，PYODPS3 638 默认 inferred，除非后续另开脚本解析策略。

我用 `GetFile` 抽样并全量扫了 336 个 DI：

- 336/336 的 `GetFile.Content` 都是可 `json.loads` 的 JSON。
- JSON 顶层含 `steps`，常见 step 组合是 reader / writer / processor。
- 真实 reader 分布：`reader|mysql` 253、`reader|mongodb` 82、`reader|sqlserver` 1。

关键反例：提案写的 `steps[].parameter.datasource / table` 不是通用 reader 路径。

真实 reader shape 是：

- MySQL / SQLServer：`steps[].category == "reader"`，`parameter.connection` 是 list，元素形态含 `datasource` 和 `table` list；reader 参数本身没有 `datasource/table`。
- MongoDB：`steps[].category == "reader"`，`parameter.datasource` + `parameter.collectionName`，不是 `table`。
- Writer step 是 ODPS 目标表，也有 `parameter.table`，不能被误当成源表；解析器必须只取 `category=reader` 的源端 step。

脱敏样本 shape：

```text
DI sample file:96107/500410074 · node=ods.app_server_em_flow_deployment.extract
reader stepType=mysql · parameter keys: column, connection, encoding, envType, socketTimeout, splitPk, tableComment, useSpecialSecret, where
connection[0] keys: datasource, table(list)

DI sample file:96107/500618917 · node=ods.sdk_backend_autosync_4_darazevent.extract.fix
reader stepType=mongodb · parameter keys: batchSize, collectionName, column, cursorTimeoutInMs, datasource, enableJsonPrintNull, envType, objectIdOutputType, query, tableComment, useSplitVector
```

调整建议：RFC 提案段把解析规则改成：

- 只解析 `steps[]` 中 `category == "reader"` 的 step。
- MySQL/SQLServer：从 `parameter.connection[]` 取 `datasource` 和 `table[]`；若多 table，`source_table` 要定义为 list 还是拒绝 parsed，需要钉死。我倾向 `source_tables: []` 或 `source_table` 允许 list，否则多表源会丢信息。
- MongoDB：从 `parameter.datasource` + `parameter.collectionName` 取 binding；字段名可仍落入 `source_table`，但文档要说明 collection 映射到 source_table，或新增 `source_object` 避免语义混淆。
- Writer ODPS step 不参与 source binding。

### 2. 索引契约

`source_binding/source_datasource/source_table` 作为 additive optional 字段，不 bump `index_version=2`，原则上不冲突 RFC-028 受管共享基线：不含代码正文、不含 volatile、稳定排序即可。

但基于实跑 shape，我认为字段契约还不够：

- `source_table` 单值不足以表达 `connection[].table` list、多 reader、多源表情形。
- 如果保持单值，必须定义多表时 `source_binding=ambiguous` 或 `inferred`，并记录 warning；否则会产生看似权威但实际截断的 binding。
- 建议枚举扩为 `parsed / inferred / unparsed / ambiguous`，至少把“DI JSON 可读但源表多值或 shape 不支持”和“命名推断”区分开。若不扩枚举，也要有 `source_binding_reason` 或 `binding_warnings`，否则治理和抽查会混淆。

### 3. freshness 联动

挂在 `wiki_freshness.py --incremental-deployments` 是合适的，因为该路径已经按 changed file 拉 `GetFile` 算 fingerprint，重解析同一个 content 是本地 JSON parse，额外成本很小，不会显著拖慢增量路径。

需要在 TASK 里钉死两点：

- 只对 changed file 且 index item 已有 `source_binding=parsed` 或 `program_type=DI` 的项重解析；不要在增量路径里扫全量 974。
- diff 维度要区分 `fingerprint_changed` 与 `binding_changed`：fingerprint 变但 binding 不变只更新指纹；binding 变则进待复核。这个 RFC 已有方向，但 TASK 需要结构化字段，例如 `binding_previous/current/changed`。

### 4. 批量快审流程

“抽查 ≥20 后批量 review:true”方向可以，但治理表述还不够严。336 个 DI 覆盖 mysql/mongodb/sqlserver，且解析规则至少有两类不同 shape；随机 20 可能漏掉 Mongo/SQLServer 或多表 edge case。

建议调整为分层抽样：

- 按 reader `stepType` 分层：mysql、mongodb、sqlserver 都必须覆盖；sqlserver 只有 1 个则必查。
- 按数据源 / source_datasource 去重抽样，避免 20 个样本都来自同一系统。
- 抽样记录应包括解析器 commit、索引 snapshot、样本 file_id/node_name、reader stepType、source_datasource/source_table、人工核对结论。
- 批量背书范围仅限“本次解析器支持且抽查通过的 binding shape”，例如 mysql connection-list 与 mongodb collectionName；不应覆盖 `ambiguous/unparsed/inferred`。
- 后续 drift 自动进待复核可以只标 queue，不自动撤 `review:true`，这一点与 L3 红线一致。

### 5. 其他边界

- RFC 写“DI 任务配置里明确写着 DataSource + table”需要改成更精确的“DataWorks DI JSON reader 配置里明确写源端 datasource 与 table/collection；不同 reader stepType 字段路径不同”。
- `confidence` 从 low 升 medium 只应适用于 parsed 且无 ambiguity 的 ODS source；不应扩大到 PYODPS3 inferred。
- accepted 后建议拆两步：先实现 parser + index 字段 + fixtures + survey report；再做 pk 实例回填和批量快审文档，避免把工具契约和批量背书动作混在一个 commit。
