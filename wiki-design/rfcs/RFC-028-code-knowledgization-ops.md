---
id: rfc_20260623_028
title: 代码知识化工程化（全量索引 + 变更增量 + 分层建页 + sqlglot 血缘解析）
author: claude
status: proposed
created: 2026-06-23
updated: 2026-06-23
targets:
  - scripts/dataworks_client.py
  - scripts/wiki_freshness.py
  - scripts/wiki_index.py
  - wiki-design/02-workflows.md
  - scripts/README.md
  - tests/
reviewers:
  - codex
  - user
---

# RFC-028: 代码知识化工程化

## 背景

RFC-027 让 knowledge-pk 具备代码知识化的**单元能力**（asset-mapping 页型 / 代码梳理方法论 / 官方 SDK 失效检测 / 答疑回源），但只验证了"单页"。要把整个 pk_data **系统性**知识化、可持续运营，还缺三块工程化：

1. **全量索引**：不知道"pk_data 有哪些生产在用代码、当前指纹基线是什么"——失效检测只能逐页锚点被动查，没有全景。
2. **增量更新**：代码每天有变更（量不大），需要高效拿到"变了哪些"，而不是全量重算。用户已确认 **DataWorks 有接口可直接拿每天变更文件清单**。
3. **分层建页策略**：数仓按 ODS/DWD/DWS/ADS 分层建设，知识库不能每层每表都建页（那是数据字典的活），要按口径价值密度取舍；并从 SQL 自动抽血缘作梳理参考。

## 兼容性（头等约束）

**本 RFC 不得影响任何现有库的入库与查询流程。** 新增能力全部是 DataWorks 专属旁路，隔离在 `dataworks_client` / 新脚本；`wiki_lint`/`wiki_graph`/`wiki_eval` 保持离线零依赖（含不 import `sqlglot`/SDK/索引模块）。不接 DataWorks 的库（personal / datawarehouse / knowledge-cmn）行为完全不变。这是可验证项（见验证方式），不是口头保证。

## 提案

延续 RFC-027 原则：**对代码 pull 不 push、检测失效不自动重写、机器筛人背书、访问统一走官方 SDK（凭证 env）。** 分四个 milestone。

### M1 — 全量代码索引层

新增 `scripts/wiki_index.py`（或并入 `dataworks_client` + freshness，executor 定）：拉 pk_data **生产在用**代码清单 → 建索引。

- **"生产在用"过滤**：用 `ListFiles` 的 `CommitStatus`（已提交）+ 是否挂生产调度 + 节点状态，排掉临时/测试/废弃（具体判据 Step 0 用 SDK 核实）。
- **索引内容**：每文件 `path` / 对应 `table` / **分层**（从 project·table 命名约定推断 ODS/DWD/DWS/ADS）/ `code_fingerprint`（dw-code-v1）/ `last_synced`。
- **代码原文不进 wiki 正本**；要加速可本地 cache（gitignore）。
- **索引落点**：`.wiki/dataworks_index.json`（派生层）；因团队/CI 需共享基线,类比 RFC-021 的 `schema_sync.json` **进 git**（具体 gitignore 例外路径 Step 0 核实），并由 `.ignore` 屏蔽**不进检索**。
- 用途：失效检测基线 + "有哪些代码/表"全景 + 梳理导航（从索引挑高价值 DWD 文件梳理）。

### M2 — 变更增量

`wiki_freshness` 增强为支持全量增量模式：

- 调 **DataWorks 变更清单接口**（Step 0 核实具体接口：ListFiles 带时间过滤 / 操作审计 / 等）拿当天变更文件（量小）。
- 只对变更文件 `GetFile` 算指纹 → 更新 `dataworks_index.json` → 反查 `dataworks_ref` 受影响的口径页 → 标待复核（默认只读 report，接 RFC-027 M3 的只读语义 + `--apply-stale`）。
- 不全量重算（避免对所有文件 GetFile）。定时由 maintainer cron / CI。

### M3 — 分层建页策略（方法论，纯文档）

写进 `02-workflows`（通用）+ pk AGENTS（pk 特定）：

| 层 | 策略 |
| --- | --- |
| ODS 贴源 | 一般不建页；作血缘起点 + asset-mapping 溯源 |
| DWD 加工 | **口径定义点重点梳理** → topic/decision/asset-mapping |
| DWS 汇总 | 引用 DWD 定义点 + 只记聚合维度/粒度增量 |
| ADS 应用 | 引用上游 + 记应用过滤/展示增量 |

asset-mapping 锚**定义层（通常 DWD）**为权威,正文标注下游 DWS/ADS 衍生表。血缘 `related_ids` 串 ODS→DWD→DWS→ADS（下游→上游定义点）。

### M4 — sqlglot 血缘解析（参考，不自动写）

新增血缘解析（`sqlglot` 解析 `GetFile` 拉的 SQL → 表/列级血缘）：

- 仅产出**建议**（freshness report / ingest 参考 / review_queue），**不自动写 `related_ids`**——人背书才进正本（接血缘权威性：工具血缘不一定准）。
- `sqlglot` 为新依赖,**隔离**在血缘解析脚本，不进 `wiki_lint`/`graph`/`eval` 的 import。

## 真实摩擦来源

机制类，证据具体：本会话把 knowledge-pk 代码知识化从单元能力（RFC-027）推向整库运营时，用户明确提出三个工程化需求——① 初始化想全量拉 pk_data 生产代码 ② 后续定时只拉变更（DataWorks 有现成变更接口、变更不多）③ 数仓按 ODS/DWD/DWS/ADS 分层建设，知识库建页要有分层取舍策略。开源调研（见 reference 记忆）确认无适配阿里云栈的 drop-in 方案,自造主体 + 复用 sqlglot 是合身选择。

## 验证方式

- **兼容性（头等）**：personal / datawarehouse / knowledge-cmn 的 `wiki_lint`/`graph`/`eval` 回归行为不变（smoke + 全量回归）；**进程级断言** `wiki_lint`/`graph`/`eval` 不 import `sqlglot`/SDK/`wiki_index`。
- **M1**：对 pk_data 拉生产清单建 `dataworks_index.json`，代码原文不进 git；索引被 `.ignore` 屏蔽（检索验证）。
- **M2**：变更清单接口拿当天变更 → 只对变更文件算指纹（断言未对全量 GetFile）；反查受影响页进 report（默认只读）。
- **M3**：`--check-docs` 不破；分层策略可指导一次真实建页。
- **M4**：`sqlglot` 解析一段真实 SQL → 产出血缘建议、不写正本；fixture mock + 真实 smoke（skipUnless 凭证）。
- **回归**：RFC-012~027 全套过；离线工具仍离线可跑。

## 替代方案

- **全量 GetFile 算指纹做增量**：贵。**放弃**，用 DataWorks 变更清单接口。
- **代码原文进 wiki 正本**：库变代码仓、检索被淹。**放弃**，只存索引 + 口径，原文按需。
- **自写 SQL 解析器**：重复造轮子。**放弃**，复用 `sqlglot`。
- **引入 OpenMetadata / DataHub / codegraph**：调研确认不支持 DataWorks 栈 / 错配（建代码结构图非数据血缘）/ 重型。**放弃**（见 reference 记忆）。
- **OKF 导出 / visualizer / graphify（LLM 自动建图）**：非刚需 + 维护/漂移成本,旁路不影响性能但当前无明确需求。**列 backlog**，有真需求再单独起 RFC。

## 影响范围

- **引擎**：`scripts/dataworks_client.py`（扩展：列生产文件 / 变更清单 / SQL 血缘）；新 `scripts/wiki_index.py`（或并入 freshness）；`scripts/wiki_freshness.py`（增量模式）；`wiki-design/02-workflows.md`（分层建页策略）；`scripts/README.md`；`tests/`；新依赖 `sqlglot`（隔离）。
- **实例 knowledge-pk**（apply 时）：`.wiki/dataworks_index.json`（派生,进 git 共享基线）、`AGENTS.md`（分层策略）、`.ignore`（屏蔽索引）。
- **不改**：core BASE_SCHEMA、`schema_version`、核心 `wiki_lint`/`graph`/`eval` 逻辑、非 DataWorks 库行为、hard/soft redact。

## Apply 拆分建议

- **TASK-A（M1 全量索引）**：`wiki_index` + 生产文件过滤 + 索引建立 + 分层推断 + 测试。
- **TASK-B（M2 变更增量）**：变更清单接口 + freshness 增量模式 + 反查受影响页。
- **TASK-C（M3 分层方法论）**：纯文档（02 + pk AGENTS）。
- **TASK-D（M4 sqlglot 血缘）**：血缘解析 + 建议产出（不写正本）+ 隔离依赖。
- 顺序 A → B → D（D 依赖 A 的代码拉取）；C 文档可随时落。每个 task 必带兼容性验证（现有库回归 + 离线断言）。
