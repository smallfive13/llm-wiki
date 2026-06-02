---
id: rfc_20260601_012
title: 知识可信度信号（激活 review 语义 + 时间衰减 + 使用热度 + 用户反馈）
author: claude
status: proposed
created: 2026-06-01
updated: 2026-06-01
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

核心原则：**不改任何 core schema 契约**（`confidence` enum、core 必填字段、稳定 ID、append-only 全部不动）。新增的只有：lint warning code + graph insights 段 + BASE_SCHEMA 的可配阈值。全部是 **warning，不触发 lint fail**（个人库不想被红色 lint 烦）。

### 1. 钉死 `review` 语义（声明层）

写进 `.wiki-schema.md`，把 `review` 从摆设激活成"背书标记"：

| 取值 | 语义 |
| --- | --- |
| `review: false`（默认） | AI 草拟 / 自评，**未经人确认** |
| `review: true` | **人已确认背书**（看过且认可当前内容） |

不新增字段。`review` 配合 `last_verified` 就能同时承载"是否背书"和"何时核实过"。

### 2. 时间衰减（freshness）→ lint warning `STALE_PAGE`

`status: active` 的页，若 `now - last_verified > 阈值` → warning，提示"距上次核实已 N 天，复核后更新 last_verified（或下调 confidence / 改 status: stale）"。

阈值按 type 分档（判断型易过时、事实型更稳），默认值写进 BASE_SCHEMA，profile 可覆盖（只增不改）：

| type | 默认 staleness 阈值 | 理由 |
| --- | --- | --- |
| `decision` / `synthesis` / `comparison` / `open-question` | 120 天 | 判断 / 结论型，易随认知更新而过时 |
| `topic` / `entity` | 365 天 | 概念 / 实体相对稳定 |
| `source` | 不检查 | 来源摘要是历史快照，不存在"过期" |
| `query` | 不检查 | 查询记录 |

> `status: stale / archived / draft / redirect` 的页不触发（stale 本就是"已知过期"，archived 已归档）。

### 3. 使用热度（usage）→ 复用 graph `degree`，输出 insights

wiki_graph 已有 `assign_degree`，无需新基础设施：

- `degree == 0` → **orphan**（孤立页：可能是噪音，或待连接的新页）——insights 已有 `isolated`，本 RFC 复用并明确语义；
- `degree` 高（top N）→ **hub**（枢纽页：很多页依赖它）——insights 已有 `hubs`；
- **联动**：stale 列表按 degree 降序排，**hub 过期优先复核**（它过期影响面最大）。

> 这里的"热度"是**结构热度**（被多少页引用），不是运行时**查询频率**（每次读这页 +1）。后者需要访问埋点 + usage log，是新基础设施，切到 Backlog（见下）。结构 degree 是当前零成本可得的最佳代理。

### 4. 高置信未背书 → lint warning `UNVERIFIED_HIGH`

`confidence: high` 且 `review: false` → warning，提示"高置信但未经确认：确认后置 `review: true`，否则建议降为 medium"。

这是用户最初疑虑"`high` 是 AI 自吹"的直接闭合：要么有人背书，要么别标 high。

### 5. 用户反馈（feedback）→ 复用 `last_verified + review`，提供"确认"动作

个人库里"反馈"就是你读到一条知识时的一个轻动作，**不引入新字段**（保持 schema 不膨胀、反馈记录天然落在 git 历史）：

| 反馈 | 落地方式 | 喂给哪个信号 |
| --- | --- | --- |
| 正反馈：这条还对 / 认可 | `last_verified = 今天` + `review: true` | freshness 时钟重置 + endorsement 背书 |
| 负反馈：过时了 | `status: stale` | 退出 stale 检测 + 从可信集合移除 |
| 负反馈：不太对 | 下调 `confidence` / 进 `review_queue`（type: stale_claim） | 降可信 |

wiki skill 提供一键"确认/复核 <page_id>"动作（更新 last_verified + review），让正反馈零摩擦。

### 6. 合成 `trust` 状态（派生，输出到 graph insights「知识健康度」段）

规则化、可解释（不搞黑箱加权数值）：

```
base = confidence (high / medium / low)
  - 若 STALE_PAGE          → 降一级，标 needs-reverify
  - 若 high 且 review:false → 标 "high (unverified)"，不计入最高可信
  - 若 review:true 且 fresh → 标 "verified"（最高可信）
  - 若 degree == 0          → 标 orphan
  - 若 degree 进 top        → 标 hub（stale 时优先级↑）
```

graph insights（`maps/graph-insights.md`，派生层不进 Git）新增「知识健康度」段：

- **stale**：超期未核实页，按 degree 降序（hub 优先）
- **high (unverified)**：高置信未背书页
- **orphan**：孤立页
- **trust 概览**：verified / unverified-high / stale / total 计数

### 范围不包含（→ Backlog，标触发条件）

| 议题 | 不做的理由 | 触发条件 |
| --- | --- | --- |
| 运行时查询频率（访问埋点 + usage log） | 需要新持久化基础设施；当前 degree 已是够用代理 | 接入会产生访问事件的客户端（如 llm_wiki app） |
| evidence 结构化校准（形态 C：confidence 必须有 evidence[] 支撑） | 个人库多为经验/方法论型知识，无可枚举外部来源；强制会逼出假引用 | 开始大量 ingest 外部资料，evidence 可枚举且有追溯价值 |
| inbox→review_queue 实际 gate（形态 B） | 个人库写者=审者，gate 易空转 / 队列死信 | 接入自动 / 半自动 capture 源 |
| 自动降级 confidence / status | lint 只提示不改数据，保持 append-only + 人决策 | — |
| review_queue pending SLA 告警 | 已在 Backlog「review queue SLA」 | — |

## 替代方案

| 决策点 | 选择 | 拒绝的方案 |
| --- | --- | --- |
| confidence 怎么动态化 | **新增派生 trust 状态**，不动 confidence 字段 | 直接让 confidence 字段随时间衰减（破坏 core enum 契约 + 不可解释） |
| 用户反馈载体 | **复用 last_verified + review** | 新增 feedback / verified_count 字段（schema 膨胀；git 历史已能审计反馈） |
| 使用热度来源 | **graph degree（结构热度）** | 运行时查询频率（需埋点 + usage log，新基础设施，MVP 过重） |
| stale / unverified 越界 | **warning（不 fail）** | error（个人库不想被阻断；这是提醒不是违规） |
| staleness 阈值 | **按 type 分档 + profile 可覆盖** | 全局统一阈值（判断型和事实型过期速度差异大） |

## 影响范围

### 新增
- `scripts/wiki_common.py`：BASE_SCHEMA 新增 `staleness_days`（按 type 分档默认值）+ 在 `error_level` 注册 `STALE_PAGE` / `UNVERIFIED_HIGH` 为 `warning`
- `scripts/wiki_lint.py`：两条 warning 检查（读 last_verified / confidence / review / status + 阈值）
- `scripts/wiki_graph.py`：insights 新增「知识健康度」段（stale / high-unverified / orphan / trust 概览）

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
- `staleness_days` 走 profile overlay 机制（只增不改）：业务库可按自己的知识衰减速度覆盖默认阈值
- 引擎单源：规则改一次，所有实例零同步生效

## Review by codex · YYYY-MM-DD

（待 Codex 追加）

## Decision

（待用户填写，或授权某 Agent 代写）
