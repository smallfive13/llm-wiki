---
id: rfc_20260703_030
title: ODS 源表 binding 从命名推断升级为配置解析（parsed）+ 批量快审背书流程
author: claude
status: proposed
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

## 背景

ODS 表对应的**线上源表**（源系统 MySQL/Mongo 表）目前是靠 **ODS 命名模糊匹配**推断的（如 `ods_pak_vendor_biz_merchant_goods` → 猜数据源 `pak_vendor_biz` 的 `merchant_goods` 表）。三个问题：

1. **不可靠**：`autosync_2/3` 版本后缀、表名截断、多库同名、命名不规范都会猜错。
2. **无法表达权威性**：模糊匹配和权威事实长得一样（都是 `review: false` 的 source 页正文），答疑分不清"猜的"和"配置里写的"。
3. **背书不可行**：974 个 ODS source 页逐页人工核对源表映射不现实，导致 ODS 映射永远挂着"未经人工背书"免责。

而 DataWorks 数据集成（DI）同步任务的配置里**明确写着** `DataSource` + `table`——这是机器可解析的权威事实，且这些任务全部已在索引（1353 items 含 code_fingerprint），变更可被增量防腐检测。

**治理前提（不动摇）**：解析自权威配置 ≠ 人工背书。`review: true` 的不变量仍是"当前仍由人背书"（L3 红线），机器不得 auto 设置。本 RFC 用**正交信号**表达来源权威性，并用"批量快审"降低人工背书成本，不是让机器绕过背书。

## 提案

### 1. binding 解析（引擎）

- `dataworks_client` / `wiki_index` 增加 ODS 同步任务配置解析：从 DI 任务 content（JSON，`steps[].parameter.datasource / table` 形态）机械提取源端 `datasource` + `table`。
- 索引 item 增加**可选**字段（additive，不 bump `index_version`，仍守受管基线——无 volatile、无代码正文）：
  - `source_binding`: `parsed`（配置解析）/ `inferred`（命名推断）/ 缺省（未处理）
  - `source_datasource` / `source_table`: parsed 时填解析值
- **Step 0 必核**：survey 974 个 ODS 任务的 `program_type` 分布——多少是可解析的 DI JSON、多少是脚本模式同步（shell / 脚本内拼 SQL）；后者保持 `inferred` 不硬解析。

### 2. 三个正交信号的联动（实例约定 + 引擎支持）

| 信号 | 承载 | 规则 |
| --- | --- | --- |
| 来源权威性 | `source_binding` + `confidence` | binding=`parsed` 的 ODS source 页 confidence 可升 `medium`（机器事实、来源权威）；`inferred` 保持 `low`。写入 pk `AGENTS.md` confidence 规则表（扩展 TASK-045）。 |
| 变更风险 | 既有 freshness 锚点 + 增量防腐 | parsed binding 依附已有 file `code_fingerprint`；`--incremental-deployments` 发现同步任务文件漂移时，**重解析 binding 并 diff**——binding 变了（换源表/换数据源）标待复核，binding 没变仅指纹更新。 |
| 人工背书 | `review: true`（仍是唯一途径） | 见下"批量快审"。 |

### 3. 批量快审背书流程（写入 02-workflows）

把 ODS 映射背书从"逐页考证"降为"抽查解析器 + 批量确认"：

1. maintainer 对解析结果做**随机抽查**（建议 ≥20 个样本，跨数据源），核对 DataWorks 控制台配置。
2. 抽查通过 → maintainer 可对「`source_binding=parsed` 且指纹当前」的 ODS source 页**批量设 `review: true`**，背书依据（抽查样本量、日期、解析器版本/commit）记入 log 与 review_queue 决议——背书责任仍在人，只是核对单位从"每页"变成"解析器 + 批次"。
3. 后续增量防腐发现某 parsed 文件漂移且 binding 变化 → 该页自动进待复核（撤 review 仍需人确认，机器只标记）。

### 4. 答疑口径

- `parsed` + `review:true`：直接答，可省"未经人工背书"免责。
- `parsed` + `review:false`：答时标注"解析自同步任务配置（权威来源），待批量背书"。
- `inferred`：答时必须标注"按命名推断，未经核实"。

## 真实摩擦来源

用户 2026-07-03 提出：ODS 线上表映射靠名字模糊匹配、被视为未背书、还可能变更；直接从脚本解析 DataSource+table 是否应视为背书。经讨论确认：解析提升权威性但不该占用 review 语义，正确落点是 binding 字段 + confidence + 防腐联动 + 批量快审。974 个 ODS 页逐页背书不可行是真实运营瓶颈。

## 验证方式

- Step 0 survey 输出：ODS 任务 program_type 分布、可解析比例（脱敏样本进 Execution log）。
- 解析 fixture：DI JSON → `datasource`/`table` 提取正确；脚本模式任务不误解析、保持 inferred。
- binding drift fixture：同步任务文件指纹变 + binding 变 → 待复核；指纹变 + binding 不变 → 仅更新指纹。
- 真实 smoke：抽 10-20 个 ODS 任务解析并人工比对 DataWorks 控制台。
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
