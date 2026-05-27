# 契约与下一步

这份文档把审阅建议落成下一阶段的工作边界：先冻结文件契约，再创建最小可运行知识库。

参考关系：

- `llm_wiki` 提供产品化经验：两步 ingest、持久化 review、source 监听、图谱洞察、查询引用。
- `llm-wiki-skill` 提供 Agent 工作流经验：本地 Markdown 正本、source registry、模板、lint、缓存和平台入口。
- 本项目 `llm-wiki` 先沉淀成可被 Codex / Claude Code / Obsidian 共同执行的轻量规范。

## 下一步总目标

不要先做复杂 App 或完整 CLI。下一步应先让 `knowledge/` 目录可以被 Agent 稳定读写，并且每次写入都有可审查 diff。

优先级：

1. P0：冻结 `.wiki-schema.md`、`review_queue.json`、`source_manifest.json` 和页面 frontmatter 字段。
2. P0：补 source / entity / topic / decision / open-question / query 的最小页面模板。
3. P0：把 `04-agent-rules.md` 收敛成未来根目录 `AGENTS.md` 的行为规则，不再混放字段定义。
4. P1：创建一个空的 `knowledge/` 种子目录，验证 Obsidian、Git diff 和 Agent 读写路径。
5. P1：补最小 lint：frontmatter、断链、review queue、source manifest 一致性。
6. P2：再考虑轻量脚本或 CLI：`wiki init`、`wiki ingest`、`wiki query`、`wiki lint`、`wiki graph refresh`。

## 目标文件关系

```text
AGENTS.md
knowledge/
  .wiki-schema.md
  purpose.md
  index.md
  overview.md
  log.md
  raw/
    source_manifest.json
    sources/
  wiki/
    sources/
    entities/
    topics/
    comparisons/
    synthesis/
    decisions/
    queries/
    open-questions/
  maps/
    knowledge-graph.md
    graph-insights.md
    graph-data.json
  .wiki/
    review_queue.json
    cache.json
    search_index/
    lightrag/
    id_index.json
```

职责划分：

| 文件 | 职责 | 是否知识正本 |
| --- | --- | --- |
| `AGENTS.md` | Agent 行为规则，控制何时读写、如何引用、如何审阅 | 是 |
| `knowledge/.wiki-schema.md` | 知识库数据 schema，控制目录、字段、页面类型 | 是 |
| `knowledge/raw/source_manifest.json` | 原始资料登记表，连接 raw 文件、URL、hash、摘要页 | 是 |
| `knowledge/.wiki/review_queue.json` | 待人工确认的结构化队列 | 是，除非团队决定只做本地状态 |
| `knowledge/.wiki/cache.json` | hash 缓存，可重建 | 否 |
| `knowledge/maps/graph-data.json` | 图谱派生数据，可重建 | 否 |
| `knowledge/.wiki/id_index.json` | ID → 当前 path 索引，可重建 | 否 |

## Review Queue Schema

路径：`knowledge/.wiki/review_queue.json`

用途：把摄入、lint、query 中发现的冲突、重复、缺页和待确认事项结构化，避免后续 Agent 写乱。

顶层格式：

```json
{
  "version": 1,
  "updated_at": "2026-05-25T15:30:00+08:00",
  "items": []
}
```

单条 item：

```json
{
  "id": "rev_20260525_001",
  "type": "contradiction",
  "title": "Attention 复杂度说法冲突",
  "description": "两个页面对 Attention 的计算复杂度描述不一致，需要人工判断是否是语境差异。",
  "status": "pending",
  "priority": "medium",
  "source_ids": ["src_20260525_attention"],
  "source_paths": ["raw/sources/attention.md"],
  "affected_page_ids": ["ent_20260525_attention", "top_20260525_transformer"],
  "evidence": [
    {
      "page_id": "ent_20260525_attention",
      "page_path": "wiki/entities/Attention.md",
      "quote": "复杂度为 O(n^2)",
      "note": "旧结论"
    }
  ],
  "search_queries": ["Attention complexity Transformer"],
  "options": [
    {
      "label": "保留两种语境",
      "action": "split_context"
    },
    {
      "label": "标记旧结论过期",
      "action": "mark_superseded"
    },
    {
      "label": "暂不处理",
      "action": "keep_pending"
    }
  ],
  "created_at": "2026-05-25T15:30:00+08:00",
  "updated_at": "2026-05-25T15:30:00+08:00",
  "resolved_at": null,
  "resolved_action": null
}
```

字段约束：

| 字段 | 规则 |
| --- | --- |
| `id` | 稳定 ID，不用数组位置作为引用 |
| `type` | `contradiction`、`duplicate`、`missing_page`、`confirm`、`suggestion`、`source_gap`、`stale_claim` |
| `status` | `pending`、`resolved`、`dismissed` |
| `priority` | `low`、`medium`、`high` |
| `source_ids` | 对应 `source_manifest.json` 中的 `source_id` |
| `affected_page_ids` | canonical，页面 `id` 数组 |
| `evidence.quote` | 只放短摘录，长证据回链到 source 页面 |
| `evidence[].page_id` | canonical，页面 `id`；必填 |
| `evidence[].page_path` | 可选显示层；与 `page_id` 一致时由 lint 维护 |
| `options.action` | 用 snake_case，后续脚本可识别 |
| `resolved_action` | 必须来自 `options.action`，或使用 `manual_resolution` |

## Source Manifest Schema

路径：`knowledge/raw/source_manifest.json`

用途：登记所有进入知识库的原始资料，连接 hash、原始位置、来源 URL、摄入状态和 source 摘要页。

顶层格式：

```json
{
  "version": 1,
  "updated_at": "2026-05-25T15:30:00+08:00",
  "sources": []
}
```

单条 source：

```json
{
  "source_id": "src_20260525_attention",
  "title": "Attention Is All You Need",
  "source_type": "pdf",
  "hash_sha256": "9f86d081884c7d659a2feaa0c55ad015...",
  "original_path": "raw/sources/attention.pdf",
  "source_url": "https://example.com/attention.pdf",
  "imported_at": "2026-05-25T15:30:00+08:00",
  "last_ingested_at": "2026-05-25T15:35:00+08:00",
  "status": "ingested",
  "summary_page_id": "src_20260525_attention",
  "summary_page_path": "wiki/sources/attention-is-all-you-need.md",
  "adapter": "local_file",
  "language": "en",
  "notes": ""
}
```

字段约束：

| 字段 | 规则 |
| --- | --- |
| `source_id` | 稳定、唯一，优先 `src_YYYYMMDD_slug`；**摘要页已生成时**（`summary_page_id != null`），其值必须等于摘要页 frontmatter 的 `id` 字段；未生成摘要页时 `source_id` 仍然存在，作为 source_manifest 的稳定标识 |
| `source_type` | `pdf`、`markdown`、`web`、`chat`、`image`、`manual`、`code` |
| `hash_sha256` | 对进入 ingest 的原始内容计算 hash |
| `original_path` | 相对 `knowledge/` 的 raw 路径；纯 URL 可为空 |
| `source_url` | 网页或下载来源；本地私有文件可为 `null` |
| `imported_at` | 首次登记时间 |
| `last_ingested_at` | 最近一次进入 ingest 的时间 |
| `status` | `new`、`triaged`、`ingested`、`skipped`、`failed`、`deleted` |
| `summary_page_id` | source 摘要页 frontmatter 的 `id` 字段。**未生成摘要页时为 `null`；已生成时必须等于 `source_id`**。 |
| `summary_page_path` | 可选显示层；对应 source 页面当前路径，未生成时为 `null` |
| `adapter` | `local_file`、`web_clipper`、`manual`、`llm_wiki_app`、`custom` |

## Frontmatter 生命周期字段

所有 `wiki/**/*.md` 页面尽量使用同一组字段。字段少一点可以，但字段名不要变体膨胀。

```yaml
---
id: top_20260525_attention                 # 稳定主键，永不变；prefix 与 type 一致
type: topic
status: active
confidence: medium
created: 2026-05-25
updated: 2026-05-25
last_verified: 2026-05-25
review: false
source_ids:                                # canonical 引用（按 ID）
  - src_20260525_attention-is-all-you-need
related_ids:                               # canonical 引用（按 ID）
  - ent_20260524_transformer
sources:                                   # 可选显示层
  - "[[attention-is-all-you-need]]"
related:
  - "[[Transformer]]"
supersedes: []                             # ID 数组
superseded_by: []                          # ID 数组
evidence_count: 1
---
```

字段含义：

| 字段 | 说明 |
| --- | --- |
| `id` | 稳定主键 `<prefix>_YYYYMMDD_<slug>`；prefix 与 type 一致；永不随标题/slug/路径变化；详见 [01-architecture.md](01-architecture.md) "稳定 ID 规则" 段 |
| `type` | `source`、`entity`、`topic`、`comparison`、`synthesis`、`decision`、`query`、`open-question` |
| `status` | `draft`、`active`、`stale`、`archived` |
| `confidence` | `low`、`medium`、`high` |
| `created` | 首次创建日期 |
| `updated` | 最近内容更新日期 |
| `last_verified` | 最近一次对照原始资料或 source 页面验证日期 |
| `review` | `true` 表示需要人工审阅 |
| `source_ids` | canonical 来源引用（ID 数组） |
| `related_ids` | canonical 相关页引用（ID 数组） |
| `sources` | 可选显示层，Obsidian wikilink |
| `related` | 可选显示层，Obsidian wikilink |
| `supersedes` | 本页面替代的旧页面 ID 数组 |
| `superseded_by` | 替代本页面的新页面 ID 数组 |
| `evidence_count` | 主要结论背后的证据数量 |

## 最小页面模板

### Source

```markdown
---
id: {{SOURCE_ID}}                          # === source_id（source 类型单主键）
type: source
status: active
confidence: high
created: {{DATE}}
updated: {{DATE}}
last_verified: {{DATE}}
review: false
source_id: {{SOURCE_ID}}                   # 与 id 相同；保留供 source_manifest 直接关联
hash_sha256: {{HASH}}
original_path: {{RAW_PATH}}
source_url: {{SOURCE_URL}}
imported_at: {{IMPORTED_AT}}
source_ids: []                             # 本 source 引用的其它 source（按 ID）
related_ids: []                            # 相关页（按 ID）
sources: []                                # 可选显示层
related: []
supersedes: []                             # ID 数组
superseded_by: []
evidence_count: 1
---

# {{TITLE}}

> 一句话摘要。

## 基本信息

- 来源类型：{{SOURCE_TYPE}}
- 原始位置：{{RAW_PATH}}
- 来源 URL：{{SOURCE_URL}}

## 核心观点

1. ...

## 关键概念

- [[概念]]

## 证据摘录

> 短摘录。

## 关联与冲突

- ...
```

### Entity

```markdown
---
id: {{ENTITY_ID}}                          # ent_YYYYMMDD_<slug>
type: entity
status: active
confidence: medium
created: {{DATE}}
updated: {{DATE}}
last_verified: {{DATE}}
review: false
source_ids: []
related_ids: []
sources: []
related: []
supersedes: []
superseded_by: []
evidence_count: 0
---

# {{ENTITY_NAME}}

> 一句话定义。

## 简介

## 关键事实

## 不同来源中的说法

## 相关页面
```

### Topic

```markdown
---
id: {{TOPIC_ID}}                           # top_YYYYMMDD_<slug>
type: topic
status: active
confidence: medium
created: {{DATE}}
updated: {{DATE}}
last_verified: {{DATE}}
review: false
source_ids: []
related_ids: []
sources: []
related: []
supersedes: []
superseded_by: []
evidence_count: 0
---

# {{TOPIC_NAME}}

> 这个主题回答什么问题。

## 当前结论

## 证据

| 来源 | 支撑内容 | 备注 |
| --- | --- | --- |

## 开放问题

## 相关页面
```

### Decision

```markdown
---
id: {{DECISION_ID}}                        # dec_YYYYMMDD_<slug>
type: decision
status: active
confidence: medium
created: {{DATE}}
updated: {{DATE}}
last_verified: {{DATE}}
review: false
source_ids: []
related_ids: []
sources: []
related: []
supersedes: []
superseded_by: []
evidence_count: 0
---

# {{DECISION_TITLE}}

## 背景

## 决策

## 理由

## 影响

## 后续验证
```

### Open Question

```markdown
---
id: {{OQ_ID}}                              # oq_YYYYMMDD_<slug>
type: open-question
status: active
confidence: low
created: {{DATE}}
updated: {{DATE}}
last_verified: {{DATE}}
review: true
source_ids: []
related_ids: []
sources: []
related: []
supersedes: []
superseded_by: []
evidence_count: 0
---

# {{QUESTION}}

## 为什么重要

## 已知信息

## 缺口

## 下一步验证
```

### Query

```markdown
---
id: {{QUERY_ID}}                           # que_YYYYMMDD_<slug>
type: query
status: active
confidence: medium
created: {{DATE}}
updated: {{DATE}}
last_verified: {{DATE}}
review: false
derived: true
source_ids: []
related_ids: []
sources: []
related: []
supersedes: []
superseded_by: []
evidence_count: 0
---

# {{QUERY_TITLE}}

## 问题

## 回答

## 引用

- [1] [[页面名]] · `wiki/topics/example.md` · 支撑：...
```

## 答案引用格式

> 引用边界：正文中 `## 引用` 列表里的 `wiki/.../X.md` 路径是**显示用**，不是 canonical。canonical 引用走页面 `id`（见 [01-architecture.md](01-architecture.md) "Cross-ref 字段说明"）。如果同时保留 `id` 和 path，path 仅作为可读注释。

查询回答不要只说“根据 Wiki”。固定使用：

```markdown
回答正文里把关键判断标成 [1]、[2]。

## 引用

- [1] [[页面名]] · `wiki/topics/example.md` · 支撑：一句话说明
- [2] [[来源摘要]] · `wiki/sources/source-a.md` · 原始资料：`raw/sources/source-a.pdf` · source_id: `src_...`

## 置信度与缺口

- 置信度：medium
- 还需要验证：...
```

引用优先级：

1. 先引用 Human Wiki 页面，因为这是长期知识层。
2. 如果关键事实来自 source 页面，补充原始资料路径或 `source_id`。
3. 如果结论是回答时新推导的，标注为 `INFERRED`，不要伪装成已有知识。
4. 如果需要保存回答，写入 `wiki/queries/`，并把 `derived: true` 写入 frontmatter。

## 实施顺序

### 第一阶段：冻结契约

交付物：

- `knowledge/.wiki-schema.md`
- `knowledge/raw/source_manifest.json`
- `knowledge/.wiki/review_queue.json`
- 根目录 `AGENTS.md`
- `knowledge/wiki/**` 页面模板

验收标准：

- Agent 能只读 `.wiki-schema.md` 和 `AGENTS.md` 就知道怎样写页面。
- `review_queue.json` 和 `source_manifest.json` 有固定字段，不再出现临时字段名。
- 新建页面都有 `type/status/confidence/created/updated/last_verified/review/sources/related`。

### 第二阶段：创建最小知识库

交付物：

- 空的 `knowledge/` 目录。
- `purpose.md`、`index.md`、`overview.md`、`log.md` 初始内容。
- Obsidian 可打开，Git 能看到 Markdown 正本 diff。

验收标准：

- `git status` 能看到新知识页面。
- 派生缓存和 `graph-data.json` 不进入 Git。
- 普通查询默认只读，只有用户说“沉淀/更新 Wiki/结晶化”才写入。

### 第三阶段：补最小脚本

交付物：

- `scripts/wiki-lint`：检查 frontmatter、断链、source manifest、review queue。
- `scripts/wiki-context`：输出 Agent 会话开始要读的高密度上下文。
- `scripts/wiki-graph-refresh`：生成 `maps/graph-data.json` 和 `maps/graph-insights.md`。

验收标准：

- 机械检查能在不调用 LLM 的情况下跑完。
- LLM 只处理判断类问题，例如冲突解释、主题合并建议、缺口分析。

### 第四阶段：再做自动 ingest

交付物：

- Triage 输出先展示或写入 review queue。
- Apply 只更新受影响页面。
- 每次 ingest 更新 `source_manifest.json`、source 摘要页、index、log。

验收标准：

- 同一 source hash 未变化时不重复写页面。
- 有冲突时先进入 review queue，不强行改旧结论。
- 回答和页面都能回查到 source 摘要页与原始资料。

## 暂不做

- 暂不复刻 `llm_wiki` 桌面 App。
- 暂不引入 LightRAG 作为知识正本。
- 暂不做完整 Repo Wiki。
- 暂不做大型自动重构。
- 暂不把所有 raw 大文件强制纳入 Git，先由 `.gitignore` 和人工规则控制。
