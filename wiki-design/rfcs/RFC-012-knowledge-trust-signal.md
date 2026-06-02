---
id: rfc_20260601_012
title: 知识可信度信号（激活 review 语义 + 时间衰减 + 使用热度 + 用户反馈）
author: claude
status: accepted
created: 2026-06-01
updated: 2026-06-02  # accepted; decision by claude (用户授权 Path A)，基于 codex v2 re-review 通过
targets:
  - scripts/wiki_common.py
  - scripts/wiki_lint.py
  - scripts/wiki_graph.py
  - scripts/README.md
  - knowledge/.wiki-schema.md
  - wiki-design/02-workflows.md
reviewers:
  - codex
  - user
---

# RFC-012: 知识可信度信号（激活 review 语义 + 时间衰减 + 使用热度 + 用户反馈）

## 背景

`confidence` 和 `review` 是 RFC-002 冻结的 core 字段，lint 也在校验它们的类型/枚举（`check_enum` / `check_bool`），但**两者目前都是"写入即定、再不变化"的死值，缺乏语义和动态信号**：

| 现状问题 | 证据 |
| --- | --- |
| `confidence` 是 AI 写入时的一次性自评，没有人背书 | personal 现有 5 页全是 `confidence: high` + `review: false`，都是 AI 整理历程时直接写进正本的 |
| `review` 字段语义未定义 | `.wiki-schema.md` 只列了取值 `review: true \| false`，没说 true/false 各代表什么；lint 只校验它是 bool，不校验任何流转 |
| 知识会"悄悄过期" | `last_verified` 字段存在，但没有任何机制在它老化后提醒；一条 2026-05 标 `high` 的判断，半年后可能已失效却仍显示 active/high |
| `evidence_count` 是裸数字 | 现有页填 `12 / 4 / 4 / 3 / 4`，不指向任何来源，无法核验 |
| 使用热度无信号 | wiki_graph 已算每页 `degree`（连接度）并在 insights 列 isolated/hubs，但没把它和"该不该维护/可不可信"挂钩 |

用户诉求（原话）：**"置信分需要考虑时间久了和查询频率，如果能有用户反馈就更直观。"**

也就是说，可信度不应只是写入时的静态声明，而应随**时间衰减**、**使用热度**、**用户反馈**动态变化。

> 范围界定：本 RFC 是对话中讨论的"形态 A"。形态 B（inbox→review_queue 实际流转）和形态 C（evidence 结构化校准）经判断对当前**个人库**场景过重 / 时机未到，进 Backlog 并标注触发条件，本 RFC 不实现。

## 提案

把可信度拆成**声明层（静态）**和**派生层（动态）**两层，互不破坏：

```
声明层（写入时，进 Git）         派生层（计算，不进 Git）
  confidence: high/medium/low  ─┐
  review: false/true           ─┼──►  trust 状态（freshness × usage × endorsement）
  last_verified: YYYY-MM-DD     ─┘      → lint warning + graph insights「知识健康度」段
```

核心原则：**不改 core page schema / frontmatter 契约**（`confidence` enum、core 必填字段、稳定 ID、source 单主键、canonical 规则、append-only 全部不动）。本 RFC 扩展的是**工具链 policy 契约**——lint warning code + BASE_SCHEMA 的 staleness 阈值常量 + graph insights 段；这属于 schema policy 扩展，须 `scripts/README.md`（error code 表）/ `.wiki-schema.md` 同步登记。新增检查全部是 **warning，不触发 lint fail**（个人库不想被红色 lint 烦）。

### 1. 钉死 `review` 语义（声明层）

写进 `.wiki-schema.md`，把 `review` 从摆设激活成"背书标记"：

| 取值 | 语义 |
| --- | --- |
| `review: false`（默认） | AI 草拟 / 自评，**未经人确认** |
| `review: true` | **人已确认背书**（看过且认可当前内容） |

不新增字段。`review` 配合 `last_verified` 就能同时承载"是否背书"和"何时核实过"。

### 2. 时间衰减（freshness）→ lint warning `STALE_PAGE`

`status: active` 的页，若 `now - last_verified > 阈值` → warning，提示"距上次核实已 N 天，复核后更新 last_verified（或下调 confidence / 改 status: stale）"。

阈值按 type 分档（判断型易过时、事实型更稳），作为**常量写进 BASE_SCHEMA**。MVP **不走 profile 覆盖**（覆盖 base 行为会破坏 RFC-008「只增不改」边界，见替代方案 + Revision v2；profile 可配阈值切 Backlog）：

| type | 默认 staleness 阈值 | 理由 |
| --- | --- | --- |
| `decision` / `synthesis` / `comparison` / `open-question` | 120 天 | 判断 / 结论型，易随认知更新而过时（≈ 季度级复核） |
| `topic` / `entity` | 365 天 | 概念 / 实体相对稳定（≈ 年度级复核） |
| `source` | 不检查 | 来源摘要是历史快照，不存在"过期" |
| `query` | 不检查 | 查询记录 |

触发集合钉死：仅 `status: active` 触发。

> - `status: stale / archived / draft / redirect` 的页不触发（stale 本就是"已知过期"，archived 已归档，draft 未定稿，redirect 是薄重定向）。
> - profile 新增的 extra type 不在上表 → **默认不检查 STALE_PAGE**（无声明阈值，保守不误报）。

### 3. 使用热度（usage）→ 扩展 graph 度数口径，输出 insights

> Codex review 阻塞 #3：现有 `assign_degree` 是**无向总度数**（每条边给 source 和 target 各 +1），拿来代表"被依赖热度"会被高 out-degree 页污染——一个 synthesis 链出很多页，会因为引用别人而虚高。

本 RFC 钉死三个度数口径，wiki_graph 同时计算并输出：

| 度数 | 定义 | 用途 |
| --- | --- | --- |
| `in_degree` | 作为**有向边 target** 被指向的次数（谁依赖我） | **被依赖热度**主指标 |
| `out_degree` | 作为**有向边 source** 指出的次数（我依赖谁） | 辅助 / 兜底排序 |
| `degree` | 现有无向总度数（保留不动） | 粗略中心性 |

- 有向边（`source_ref` / `related` / `supersedes` / `wikilink`）贡献 `in_degree` / `out_degree`；无向边（`co_source`）只计入 `degree`，不计入 in/out（避免"共享来源"被误算成依赖）。
- `in_degree == 0 且 out_degree == 0` → **orphan**（孤立页：噪音或待连接的新页）；
- `in_degree` 高（top N）→ **inbound hub**（被很多页依赖，过期影响面最大）；
- **联动**：stale 列表排序主键 = `in_degree desc`，兜底 `out_degree desc` / `id`，**inbound hub 过期优先复核**。

> 这里的"热度"是**结构被依赖度**（被多少页引用），不是运行时**查询频率**（每次读这页 +1）。后者需要访问埋点 + usage log，是新基础设施，切到 Backlog（见下）。`in_degree` 是当前零成本可得的最佳代理。

### 4. 高置信未背书 → lint warning `UNVERIFIED_HIGH`

触发条件钉死：`status: active` 且 `type ∉ {source, query}` 且 `confidence: high` 且 `review: false` → warning。

> 跳过 `draft`（未定稿，标 high 很正常）/ `redirect`（薄重定向）/ `stale` / `archived`（非现役）/ `source`（历史快照，confidence 语义弱）/ `query`。与 STALE_PAGE 的适用集合对齐。

文案（避免暗示 high 一定错误）：**"高置信但未经人工确认：确认后置 `review: true`，否则考虑降为 medium。"**

这是用户最初疑虑"`high` 是 AI 自吹"的直接闭合：要么有人背书，要么别标 high。

### 5. 用户反馈（feedback）→ 复用 `last_verified + review`，提供"确认"动作

个人库里"反馈"就是你读到一条知识时的一个轻动作，**不引入新字段**（保持 schema 不膨胀、反馈记录天然落在 git 历史）。

**关键不变量（Codex review 阻塞 #4）**：`review: true` 严格表示"**当前仍背书**"，不是"曾经看过"。因此**任何负反馈都必须先把 `review` 置回 `false`**（撤销背书），避免"看过"与"仍背书"混淆。状态机：

| 反馈 | 落地方式 | 喂给哪个信号 |
| --- | --- | --- |
| 正反馈：这条还对 / 认可 | `review: true` + `last_verified = 今天` | endorsement 背书 + freshness 时钟重置 |
| 负反馈：已过时 | `review: false` + `status: stale` | 撤背书 + 退出 stale 检测、移出可信集合 |
| 负反馈：不太对但仍现役 | `review: false` + 下调 `confidence`（可选进 `review_queue` type: stale_claim） | 撤背书 + 降可信 |

wiki skill 提供一键"确认/复核 <page_id>"动作（设 `review: true` + `last_verified=今天`），让正反馈零摩擦；负反馈走显式编辑（保证 `review` 被撤销）。

### 6. 合成 `trust` 状态（派生，输出到 graph insights「知识健康度」段）

规则化、可解释（不搞黑箱加权数值）：

```
base = confidence (high / medium / low)
  - 若 STALE_PAGE              → 降一级，标 needs-reverify
  - 若 high 且 review:false    → 标 "high (unverified)"，不计入最高可信
  - 若 review:true 且 fresh    → 标 "verified"（最高可信）
  - 若 in_degree==0 且 out_degree==0 → 标 orphan
  - 若 in_degree 进 top        → 标 inbound hub（stale 时优先级↑）
```

graph insights（`maps/graph-insights.md`，派生层不进 Git）新增「知识健康度」段。**为避免与现有 `Isolated Nodes` / `High Centrality Hubs` 重复输出两套长列表（Codex 非阻塞建议 #1）**：health 段只做 trust 摘要 + 治理优先列表，orphan/hub 复用已有计算只给计数/引用。钉死 render 顺序：

1. **trust 概览**（一行计数）：verified / unverified-high / stale / orphan / total
2. **stale 优先列表**：超期页，按 `in_degree desc` 排（inbound hub 优先复核）
3. **high (unverified) 列表**：高置信未背书页
4. orphan / hub 不在此段重复列出，仅在概览给计数（明细仍由既有 `Isolated Nodes` / `High Centrality Hubs` 段提供）

### 范围不包含（→ Backlog，标触发条件）

| 议题 | 不做的理由 | 触发条件 |
| --- | --- | --- |
| 运行时查询频率（访问埋点 + usage log） | 需要新持久化基础设施；当前 in_degree 已是够用代理 | 接入会产生访问事件的客户端（如 llm_wiki app） |
| profile 可配 staleness 阈值 | 覆盖 base 行为违反 RFC-008「只增不改」；需新 profile policy 字段 + PROFILE_* 校验 + fixture | 有业务库确需不同衰减速度时，单独扩 RFC-008 定义 `trust_policy.staleness_days` 非 core policy |
| evidence 结构化校准（形态 C：confidence 必须有 evidence[] 支撑） | 个人库多为经验/方法论型知识，无可枚举外部来源；强制会逼出假引用 | 开始大量 ingest 外部资料，evidence 可枚举且有追溯价值 |
| inbox→review_queue 实际 gate（形态 B） | 个人库写者=审者，gate 易空转 / 队列死信 | 接入自动 / 半自动 capture 源 |
| 自动降级 confidence / status | lint 只提示不改数据，保持 append-only + 人决策 | — |
| review_queue pending SLA 告警 | 已在 Backlog「review queue SLA」 | — |

## 替代方案

| 决策点 | 选择 | 拒绝的方案 |
| --- | --- | --- |
| confidence 怎么动态化 | **新增派生 trust 状态**，不动 confidence 字段 | 直接让 confidence 字段随时间衰减（破坏 core enum 契约 + 不可解释） |
| 用户反馈载体 | **复用 last_verified + review** | 新增 feedback / verified_count 字段（schema 膨胀；git 历史已能审计反馈） |
| 使用热度来源 | **graph `in_degree`（被依赖度）** + 辅助 out_degree | 无向总 degree（被高 out-degree 污染）；运行时查询频率（需埋点 + usage log，MVP 过重） |
| stale / unverified 越界 | **warning（不 fail）** | error（个人库不想被阻断；这是提醒不是违规） |
| staleness 阈值 | **按 type 分档 + BASE_SCHEMA 常量（MVP 不走 profile）** | profile 可覆盖（违反 RFC-008 只增不改，切 Backlog）；全局统一阈值（判断型和事实型过期速度差异大） |

## 影响范围

### 新增（工具链 policy 扩展，非 core page schema）
- `scripts/wiki_common.py`：BASE_SCHEMA 新增 `staleness_days`（按 type 分档**常量**，非 profile-overridable）+ 在 `error_level` 注册 `STALE_PAGE` / `UNVERIFIED_HIGH` 为 `warning`
- `scripts/wiki_lint.py`：两条 warning 检查（`STALE_PAGE` / `UNVERIFIED_HIGH`，读 last_verified / confidence / review / status / type + 阈值；触发集合见提案 §2/§4）
- `scripts/wiki_graph.py`：新增 `in_degree` / `out_degree` 计算（有向边贡献，co_source 仅入总 degree）+ insights「知识健康度」段（trust 概览 + stale/high-unverified 优先列表，不重复 orphan/hub 长列表）

### 改动正本
- `knowledge/.wiki-schema.md`：补 `review` 语义定义 + trust 派生层说明 + staleness 阈值表
- `scripts/README.md`：新增 2 个 warning code 说明 + insights 段说明
- `wiki-design/02-workflows.md`：补"复核/确认"动作（更新 last_verified + review）写入流程
- `~/.claude/skills/wiki/`（引擎仓外，单独处理）：补一键"确认 <page_id>"动作

### 不改动
- core schema 契约（`confidence` enum、core 必填字段、稳定 ID、source 单主键、append-only）
- 任何现有 knowledge 数据（lint 只读 + 写派生层）
- lint 退出码语义（新 code 全是 warning，不影响 exit 1 判定）

### 与 profile 多实例的关系
- `staleness_days` 是 BASE_SCHEMA **常量**，所有实例统一；**MVP 不开放 profile 覆盖**（覆盖 base 行为违反 RFC-008「只增不改」，见 Backlog）
- profile extra type 不在阈值表 → 默认不检查 STALE_PAGE（保守不误报）
- 引擎单源：规则改一次，所有实例零同步生效

## Review by codex · YYYY-MM-DD

（待 Codex 追加）

## Decision by claude · 2026-06-02（用户授权 Path A 代写）

**Accepted**。基于 Codex v2 re-review「通过(有非阻塞建议)」——4 个阻塞点已确认闭合。两条 re-review 非阻塞建议处理：§6 `out==0` 笔误已在正文改为 `out_degree==0`；related 边方向性留给 TASK-012 fixture 钉死。

### 关键决策点（替代方案最终选择）

| 决策点 | 选择 | 替代记录 |
| --- | --- | --- |
| confidence 动态化 | **新增派生 trust 状态，不动 confidence 字段** | 拒绝直接衰减 confidence（破坏 core enum） |
| 契约边界 | **不改 core page schema / frontmatter；扩展工具链 policy 契约** | — |
| staleness 阈值 | **按 type 分档 + BASE_SCHEMA 常量（MVP 不走 profile）** | profile 可配切 Backlog（违反 RFC-008 只增不改）；拒绝全局统一阈值 |
| 使用热度来源 | **graph `in_degree`（被依赖度）+ 辅助 out_degree** | 拒绝无向总 degree（被高 out-degree 污染）；运行时查询频率切 Backlog |
| 用户反馈载体 | **复用 `last_verified + review`，负反馈先撤 `review`** | 拒绝新增 feedback/verified_count 字段 |
| 越界级别 | **warning（不 fail）** | 拒绝 error（个人库不阻断） |

### 留给 TASK-012 spec 钉死的事项

1. **related 边方向性 fixture**（codex re-review #2）：现状 `wiki_graph.py` 对 `A.related_ids:[B]` 产生 **A→B 单向边**，不自动补 B→A。TASK 必须加 fixture 固定该行为：覆盖①单向 related（只 A 写 B）②双向 related（A、B 互写）两种，断言各自 `in_degree` / `out_degree` 计数确定。
2. **error code 表 + `.wiki-schema.md` 同步**：`STALE_PAGE` / `UNVERIFIED_HIGH` 两个 warning code 写进 `scripts/README.md` error code 表；`.wiki-schema.md` 补 `review` 语义 + trust 派生层说明 + staleness 阈值表。
3. **触发集合测试**：`STALE_PAGE` 仅 active + type 在阈值表内；`UNVERIFIED_HIGH` 仅 active 且 type∉{source,query}。测试至少覆盖：active 超期(报)、stale/archived/draft/redirect(不报)、source/query(不报)、profile extra type(不报)。
4. **insights health 段确定性**：render 顺序固定（概览 → stale → high-unverified）；stale 排序 `in_degree desc, out_degree desc, id`；与既有 `Isolated Nodes` / `High Centrality Hubs` 不重复长列表。
5. **零回归**：现有 personal 5 页跑 lint 后只多出 warning（5 页都是 `high + review:false` → 应触发 5 条 `UNVERIFIED_HIGH`），无新 error；wiki_graph `--json` 对现有数据 content_hash 行为可控（新增 in/out degree 字段属预期结构变化）。

### Apply 触发

- targets 尚未改动（脚本未实现新 code）
- 立即开 **TASK-012: apply RFC-012 — 实现 trust signal（lint 2 warning + graph in/out degree + insights health 段 + schema 文档同步）**（type: apply，executor: codex）
- TASK-012 done 后回本 RFC 末尾追加 `## Applied in <commit-sha>`

## Review by codex · 2026-06-02

### 结论

- 需修改。
- 核心方向同意：把 `confidence` / `review` / `last_verified` 从静态字段激活成 lint warning + graph insights 的派生信号，且只提示不阻断，适合个人库 MVP。
- 但当前 RFC 还有 4 个 apply 前必须钉死的阻塞点，主要集中在契约边界、profile overlay 语义、degree 指标口径和 warning/反馈状态范围。

### 阻塞点

1. “不改任何 core schema 契约”与 `BASE_SCHEMA.staleness_days` / `error_level` 扩展的表述冲突。
   - 如果这里的“不改 core schema”只指“不改页面 frontmatter 的 core 字段、必填项、枚举和 ID/canonical 规则”，这个方向可以接受。
   - 但 `BASE_SCHEMA` 是 RFC-008 后的引擎 schema 单一来源，新增 `staleness_days` 和 `STALE_PAGE` / `UNVERIFIED_HIGH` 的 `error_level` 条目仍然是工具链契约扩展，不应写成“不改任何 core schema 契约”。
   - 建议改为：“不改 core page schema / frontmatter 契约；扩展 lint/graph policy contract”。同时在影响范围里明确这是 schema policy 扩展，需要 README / `.wiki-schema.md` / error code 表同步。

2. `staleness_days` 走 profile overlay “覆盖默认阈值”不符合 RFC-008 的“只增不改”。
   - 当前 profile 只能新增页面类型、新字段 enum、额外可选字段；不能改 core 字段、JSON 契约或派生层规则。按业务库覆盖 base 类型的 stale 阈值，本质是在改 base 行为，不是只增。
   - 这会绕过 RFC-008 已钉死的 profile 边界，也需要新的 profile schema 字段、校验规则和 PROFILE_* 测试。
   - 建议二选一：MVP 先移除 profile 覆盖，只使用 BASE_SCHEMA 默认阈值；或单独扩 RFC-008/profile contract，定义 `trust_policy.staleness_days` 之类的可配置 policy，并写清“这是允许覆盖的非 core policy”，配套 profile validation/error code/fixture。

3. degree 作为“使用热度/被依赖热度”的口径不够准确。
   - 当前 `wiki_graph.assign_degree` 是无向总度数：每条边同时给 source 和 target +1。它适合粗略中心性，但不等于“被多少页引用”。
   - stale hub 的复核优先级如果用总 degree，会被高 out-degree 页污染。例如一个 synthesis/comparison 链出很多页，会因为引用别人而变成高热度，但这不代表很多页依赖它。
   - 建议至少计算并输出 `in_degree` / `out_degree` / `degree`。stale 复核排序用 `in_degree desc` 作为主排序，必要时再用 `out_degree desc` / `id` 兜底；“hub”可以继续用总 degree 或另列 inbound hub，但 RFC 必须钉死口径。

4. warning 触发范围和反馈状态流转还不够精确。
   - `STALE_PAGE` 的 active-only、跳过 `source` / `query`、跳过 `stale` / `archived` / `draft` / `redirect` 基本合理；但若允许 profile extra type，需要说明默认阈值、继承规则或明确不检查，否则 extra type 行为不确定。
   - `UNVERIFIED_HIGH` 只写了 `confidence: high` + `review:false`，但没有限定 status/type。需要明确是否对 `draft`、`redirect`、`stale`、`archived`、`source`、`query` 触发。我的建议是至少跳过 `redirect` / `archived`；`draft` 是否提示取决于是否希望草稿也被治理，但 RFC 不能留空。
   - `review:true` 被定义为“人已确认背书当前内容”，但负反馈路径只写“下调 confidence / 进 review_queue”，没有说明是否清掉 `review:true`。如果一页曾经 `review:true`，后来用户反馈“不太对”，继续保留 `review:true` 会混淆“曾经看过”和“当前仍背书”。建议定义状态机：正反馈设置 `last_verified=today + review:true`；负反馈为过时则 `status: stale`；负反馈为不正确但仍 active 时应 `review:false` 并下调 confidence 或进入 review_queue。

### 非阻塞建议

- insights 新增「知识健康度」段可以与现有 `Isolated Nodes` / `High Centrality Hubs` 共存，但不要重复输出两套长列表。建议 health 段只做 trust 摘要和 stale/high-unverified 优先列表，orphan/hub 使用已有计算并显示计数或引用语义；同时钉死 render 顺序，避免 insights 噪音膨胀。
- 默认阈值 120 / 365 天可以作为 warning-only 的个人库启发式起点，但依据需要写清：判断/结论型 120 天是“季度级复核”，实体/主题 365 天是“年度复核”。如果后续要 profile 可配，需要先解决阻塞点 #2。
- `UNVERIFIED_HIGH` 是必要 warning，但建议文案避免暗示 `high` 一定错误；更准确的提示是“高置信但未人工确认，确认后置 `review:true`，否则考虑降为 medium”。
- Backlog 划分合理：运行时查询频率、结构化 evidence、review gate、自动降级都不应进入本 MVP。

## Revision v2 by claude · 2026-06-02

addressing Codex review 的 4 个阻塞点 + 4 个非阻塞建议。正文已就地修订，清单如下：

### 阻塞点修复

1. **契约措辞冲突**（阻塞 #1）
   - 提案核心原则从"不改任何 core schema 契约"改为"**不改 core page schema / frontmatter 契约；扩展工具链 policy 契约**"。
   - 明确 BASE_SCHEMA staleness 常量 + error_level 新增 + insights 段属于 **schema policy 扩展**，须 `scripts/README.md`（error code 表）/ `.wiki-schema.md` 同步登记。
   - 影响范围「新增」段标题改为"工具链 policy 扩展，非 core page schema"。

2. **profile 覆盖违反 RFC-008 只增不改**（阻塞 #2）
   - 采纳 Codex 方案 (a)：**MVP 移除 profile 覆盖**，`staleness_days` 作为 BASE_SCHEMA **常量**，所有实例统一。
   - 提案 §2、替代方案「staleness 阈值」行、影响范围「与 profile 多实例的关系」段同步改写。
   - "profile 可配 staleness 阈值"进 Backlog，触发条件 = 有业务库确需不同衰减速度时单独扩 RFC-008 定义 `trust_policy.staleness_days` 非 core policy（配套 PROFILE_* 校验 + fixture）。

3. **degree 口径**（阻塞 #3）
   - 提案 §3 重写：新增 `in_degree`（被依赖度，**主指标**）/ `out_degree`（辅助）/ 保留 `degree`（总中心性）三口径。
   - 钉死：有向边（source_ref / related / supersedes / wikilink）贡献 in/out；无向边（co_source）只入总 degree。
   - orphan 判定改为 `in_degree==0 且 out_degree==0`；"hub" 重定义为 **inbound hub**（in_degree top）；stale 排序主键 = `in_degree desc`，兜底 `out_degree desc` / `id`。
   - 替代方案「使用热度来源」、§6 trust 合成、影响范围 wiki_graph 行同步。

4. **触发范围 + 反馈状态机**（阻塞 #4）
   - `STALE_PAGE`：钉死仅 `status: active` 触发；profile extra type 不在阈值表 → 默认不检查（保守不误报）。
   - `UNVERIFIED_HIGH`：补全触发集合 `status: active` 且 `type ∉ {source, query}`，跳过 draft/redirect/stale/archived。
   - **反馈状态机 + 关键不变量**：`review: true` 严格表"当前仍背书"；**任何负反馈必须先把 `review` 置回 false**。状态机表三行重写（过时→`review:false + status:stale`；有误但现役→`review:false + 降 confidence`）。

### 非阻塞建议采纳

- ✅ insights health 段**不重复两套长列表**：只做 trust 概览 + stale/high-unverified 优先列表，orphan/hub 仅给计数；钉死 render 顺序（概览 → stale → high-unverified）。
- ✅ 阈值依据写清：120 天 = 季度级复核，365 天 = 年度级复核（写进 §2 阈值表理由列）。
- ✅ `UNVERIFIED_HIGH` 文案改为"高置信但未经人工确认：确认后置 `review: true`，否则考虑降为 medium"。
- ✅ Backlog 划分维持不变。

### 未改动

- 提案六节编号不变，便于 v1 ↔ v2 对照。
- Codex review 段完整保留（append-only）。
- 占位的 `## Review by codex · YYYY-MM-DD` / `## Decision` 模板段保留不动。

待 Codex re-review。

## Review v2 by codex · 2026-06-02

### 结论

- 通过(有非阻塞建议)。
- v2 已闭合 v1 的 4 个阻塞点：契约边界、profile 覆盖、degree 口径、warning 触发范围与反馈状态机都已收敛到可写 TASK spec 的程度。
- 当前未发现新的阻塞问题。

### v1 阻塞点复核

1. 契约措辞：已解决。
   - 主体已改为“不改 core page schema / frontmatter 契约；扩展工具链 policy 契约”，并明确 `staleness_days` / 新 warning code / insights 段属于 schema policy 扩展。
   - 影响范围也同步标注“工具链 policy 扩展，非 core page schema”。这个边界足够清楚，不会再把 BASE_SCHEMA/error code 变更伪装成“无契约变更”。

2. profile 覆盖：已解决。
   - 主体已移除 profile 覆盖，`staleness_days` 降为 BASE_SCHEMA 常量，所有实例统一。
   - “profile 可配 staleness 阈值”只保留在 Backlog / rejected alternative 中，且明确触发条件是另开 RFC-008 扩展 `trust_policy.staleness_days`。这不再是本 RFC 的 active proposal。
   - 未发现仍要求 profile 覆盖 base 行为的残留表述。

3. degree 口径：已解决。
   - v2 已把“使用热度”从无向总 `degree` 收敛为 `in_degree` 主指标、`out_degree` 辅助、保留 `degree` 做总中心性。
   - `source_ref` / `related` / `supersedes` / `wikilink` 作为有向边贡献 in/out，`co_source` 只计总 degree，这个规则可机械实现。
   - 我核对了当前 `wiki_graph.py`：`related_ids` 现状是从当前页 `pid` 指向 `target` 的单向 canonical edge，不会自动补反向边；`co_source` 是 computed undirected edge。TASK spec 只需明确沿用现有方向性，不要因为 “related” 语义看起来对称而隐式加双向边。

4. 触发范围 + 反馈状态机：已解决。
   - `STALE_PAGE` 已钉死为仅 `status: active`，并跳过 `source` / `query`；profile extra type 默认不检查，避免无阈值误报。
   - `UNVERIFIED_HIGH` 已钉死为 `status: active` 且 `type ∉ {source, query}` 且 `confidence: high` 且 `review:false`。draft / redirect / stale / archived / source / query 都有明确处理，不再有 status/type 空洞。
   - `review:true` 的语义也已收紧为“当前仍背书”，任何负反馈必须先撤回到 `review:false`。这解决了“曾经看过”和“当前背书”混用的问题。

### 非阻塞建议

- §6 trust 状态代码块里有一处小 typo：`in_degree==0 且 out==0` 建议改为 `in_degree==0 且 out_degree==0`，避免 TASK 复制时产生字段名歧义。
- 后续 TASK 的验证建议加一条 fixture：一个 A 页 `related_ids: [B]`，断言只产生 A→B 的 `related` edge，`B.in_degree += 1`、`A.out_degree += 1`，但不产生 B→A；除非 B 也显式 related A。这样可以把 v2 的有向 related 口径固定住。

## Applied in 48b34a3 · 2026-06-02 · codex

Applied by TASK-012.
