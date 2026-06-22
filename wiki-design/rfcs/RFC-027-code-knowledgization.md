---
id: rfc_20260622_027
title: DataWorks 代码知识化（asset-mapping 页型 + 代码锚点 + L1/L2/L3 更新机制 + fun-cli 接入）
author: claude
status: proposed
created: 2026-06-22
updated: 2026-06-22
targets:
  - wiki-design/02-workflows.md
  - scripts/wiki_freshness.py
  - scripts/wiki_common.py
  - scripts/README.md
  - tests/
reviewers:
  - codex
  - user
---

# RFC-027: DataWorks 代码知识化

## 背景

knowledge-pk 的核心场景是把 **DataWorks 上的代码（SQL/Python 加工逻辑）** 沉淀成可答疑的业务知识。代码本体不进库（留在 DataWorks），库里存的是"从代码梳理出的口径/语义/血缘/坑"。这带出三个当前缺失的机制：

1. **没有"业务概念 ↔ 物理表字段"的结构化页型**。实测：用户问"收款渠道是 jazz 还是 ep、在哪张表，有没有还款渠道记录表"——这是"业务词 → 物理表字段"的发现问题，机器元数据按业务词搜不到（字段叫 `pay_channel` 不叫"收款渠道"），而库里也没有承载这种映射的页型。
2. **代码会变，但没有失效检测**。从代码梳理的口径是**快照**；上游代码改了，库里的口径会悄悄过时，现在只能靠时间阈值（RFC-025 staleness）粗略提醒，不精准。
3. **答疑没有回源代码的约定**。库快照不够细或可能过时时，agent 应能回源查 DataWorks 当前代码确认，但既无约定也无访问通道。

第 3 点的访问通道现已就位：本机 **`fun-cli` skill** 能查数据表/字段/任务元数据（描述/负责人/类型/血缘/上下游/**建表代码**），且**凭证封装在 fun-cli 内部**（`auth login`），知识库无需碰 AK/SK——既解决访问、又不违"不存凭证"红线、不让知识库越界自管凭证。

## 提案

分四个 milestone。原则贯穿全程：**对代码 pull 不 push、检测失效不自动重写、机器筛人来判、DataWorks 访问统一走 fun-cli。**

### M1 — `asset-mapping` 结构化页型（走 profile）

在 **knowledge-pk 的 `.wiki-profile.json`**（RFC-008 overlay，只增不改 base）加一个页型 `asset-mapping`，承载"业务概念 ↔ 物理表字段"映射。建议字段：

- `business_concept`（业务概念名，如"收款渠道"；答疑检索的命中锚）
- `physical_table` / `physical_field`（物理落点，如 `edw.xxx` / `pay_channel`）
- `value_mapping`（枚举语义，如 `jazz=…` / `ep=…`）
- `lineage_upstream`（血缘上游表 / 上游口径页，复用 `related_ids` 表达，见 M2）
- `caveats`（坑 / 适用边界）
- **代码锚点**（`dataworks_ref` / `code_fingerprint` / `last_synced`，见 M3）

> 先在 pk 落地验证页型设计（用户的 jazz/ep 问题就是验收用例）；确认 cmn/未来 mex 也通用后，再抽成引擎共享 dw profile——**那一步是 RFC-008 的增强（profile 从"每实例独立"到"引擎定义+实例引用"），不在本 RFC**，本 RFC 先落 pk profile。

### M2 — 代码梳理方法论 + 传导口径

**代码梳理 7 维**（通用部分进引擎 `02-workflows.md`，pk 特定进 pk AGENTS 引用）：口径与定义 / 血缘数据流 / 关键逻辑（说明非代码）/ 设计决策（为什么）/ 调度运行特性 / 踩坑 / 适用边界。反面约束：不贴整段代码当正文、不逐行翻译、不沉淀一次性查询。

**传导口径**（口径从 ODS→DWD→DWS→ADS 逐层叠加）：
- 口径只在**定义点**写一次（canonical 正本），下游**只记本层增量**、用 `related_ids` 指向上游定义点，完整口径沿链累积、不重抄。
- 血缘链 = `related_ids` 有向边，复用现成 `wiki_graph`（`in_degree` 高即根口径）。**边类型化**（区分"血缘"vs"一般参见"，如 `derives_from`）列为 backlog，不在本 RFC。
- 上游口径未整理 → `open-question`（source-gap，RFC-018）占位；同名不同口径 → `open-question`（口径分歧）/ `decision`（对齐），不让矛盾口径并存。

### M3 — 代码锚点 + 失效检测（L2，机器筛）

口径页 / `asset-mapping` 页 frontmatter 加**代码锚点**：`dataworks_ref`（表名或任务标识）+ `code_fingerprint` + `last_synced`。

新增 **`scripts/wiki_freshness.py`**（职责单一、隔离外部依赖）：调 `fun-cli meta table get <table> --type code` 拉当前代码 → 算指纹 → 与页锚点比对 → 漂移则把页标 `stale`，进巡检/复核清单（接 RFC-025）。

- **指纹方案**：`--type done_time` 是"任务最近完成时间"（每天调度跑完就变），**不可做版本指纹**（会天天误报）。指纹用 `--type code` 拉回的**代码内容 hash**；若 fun-cli 的 `detail` 提供"代码最后修改时间"则优先用它（更轻）。**Step 0 由 codex 用 fun-cli 实跑核实**。
- **隔离原则**：`wiki_lint/graph/eval` 保持**离线纯本地**（无网络无凭证）；唯独 `wiki_freshness` 调 fun-cli。失效检测是**后台定期批量**跑，不在答疑或 lint 热路径。
- 这把 staleness 从"按时间过期"升级为"**按上游代码真的动了才过期**"。

### M4 — 答疑回源策略（L1 + L3）

**默认信库，触发式回源**（写进 pk AGENTS 答疑节 + 引擎 `02-workflows`）。回源 = 调 fun-cli 查 DataWorks 当前代码。

答疑决策树：
- 命中口径页 + `review:true` + 未 `stale` + 问的是语义/口径 → **用库，不回源**（最快、最常见，零 fun-cli 调用）。
- 命中但 `stale` / `review:false` 且关键 / 问"当前实现/最新值" → **回源**（fun-cli 查代码）合并答 + 标 maintainer 复核。
- 未命中 → 回源（先 `meta table search` 定位表、`field list` / `follow` 查字段血缘）+ 登记 source-gap。

**L3 人控**：回源发现口径变了，**永不自动写正本**——标复核，由 maintainer 梳理 + 背书（接 trust loop）。

## 真实摩擦来源

机制类，证据具体：本会话初始化 knowledge-pk（要把 DataWorks 代码知识化）时，用户连续追问暴露三处机制缺口——(a) 实测问"收款渠道 jazz/ep 在哪张表"库无承载页型答不了；(b) 代码会变而库快照无失效检测、只能靠时间阈值粗判；(c) 答疑无回源 DataWorks 当前代码的约定与通道。fun-cli skill 的出现使访问层落地可行（凭证已封装）。

## 验证方式

- **M1**：pk `.wiki-profile.json` 加 `asset-mapping` 后 `wiki_lint --root <pk>` exit 0；写一页"收款渠道"映射过校验；模拟答"jazz/ep 在哪张表"能命中该页。
- **M2**：`02-workflows` / AGENTS 改动后 `wiki_lint --check-docs` 不破 doc-consistency；方法论可指导一次真实 ingest。
- **M3**：fixture——锚点指纹未变 → 不标 stale；指纹变（mock fun-cli 输出）→ 标 stale 进清单；非数仓表 / fun-cli 不可用 → 优雅降级（warning 非 crash）。真实库 smoke：`wiki_freshness` 对一张真实 `edw` 表调 fun-cli 拉 code 成功。
- **M4**：答疑路径验证——命中未 stale 页时**不触发 fun-cli 调用**；命中 stale/缺失时触发回源。
- **回归**：012~026 全套过；`wiki_lint/graph/eval` 仍离线可跑（无 fun-cli 依赖）。

## 替代方案

- **每天爬代码自动重写知识库**：反模式——把库降级成代码劣质镜像，自动搬运冲掉人工梳理 + 背书，代码无关变更制造海量噪音。**放弃**。
- **纯手动定期更新**："人来梳理入库"对（保留为 L3），但"靠人发现哪些代码变了"会漏。**部分放弃**（保留人控 ingest，失效检测交给 M3 机器）。
- **知识库自连 DataWorks API + 自管凭证**：违"不存凭证"红线、让知识库越界。**放弃**，统一走 fun-cli（凭证已封装）。
- **`asset-mapping` 直接进引擎 BASE_SCHEMA**：污染 personal 等非数仓实例。**放弃**，走 profile（M1）。
- **失效检测并入 wiki_lint/eval**：会把网络/凭证依赖污染进离线纯本地工具。**放弃**，隔离到独立 `wiki_freshness.py`。

## 影响范围

- **引擎**：`wiki-design/02-workflows.md`（代码梳理方法论 + 传导口径 + 答疑回源约定）；新 `scripts/wiki_freshness.py`（L2，调 fun-cli）；`scripts/wiki_common.py`（若锚点字段需 schema 校验支持，复用 RFC-008 `extra_optional_fields`）；`scripts/README.md`；`tests/`。
- **实例 knowledge-pk**（apply 时，非引擎 targets）：`.wiki-profile.json`（`asset-mapping` 页型）、`AGENTS.md`（梳理方法论 + 答疑回源）、示例 asset-mapping 页。
- **依赖**：本机安装并登录 `fun-cli`（M3/M4 运行时）；离线工具不受影响。
- **不改**：core BASE_SCHEMA 8 类、`schema_version`（profile overlay）、hard/soft redact、非 dropbox 扫描范围。

## Apply 拆分建议

- **TASK-A（M1+M2）**：pk profile `asset-mapping` 页型 + 示例页 + 方法论/传导口径写进 02 + pk AGENTS。不依赖 fun-cli，可先落。
- **TASK-B（M3）**：代码锚点字段 + `wiki_freshness.py` + fun-cli 接入 + fixture/真实 smoke。依赖 fun-cli。
- **TASK-C（M4）**：答疑回源策略进 pk AGENTS + 02。
- 顺序 A → B → C；A 落地即可让 pk 答 jazz/ep 类问题，B/C 补失效检测与回源。
