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
  inbox/
    archive/
      promoted/
      dropped/
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
    capture_policy.json
    inbox_index.json
    normalized_alias_index.json
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
| `knowledge/inbox/` | capture 缓冲层；draft 文件等待 promotion | 是 |
| `knowledge/inbox/archive/{promoted,dropped}/` | 归档；不计入健康度告警阈值 | 是 |
| `knowledge/.wiki/capture_policy.json` | capture 控制策略，团队级共享 | 是 |
| `knowledge/.wiki/inbox_index.json` | inbox 索引，由 lint 生成，可重建 | 否 |
| `knowledge/.wiki/normalized_alias_index.json` | entity 别名规范化倒排索引，由 lint 生成，可重建 | 否 |

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

## Capture Item Schema

Inbox 文件不算 `wiki/**/*.md` 页面，独立为 **capture item**，schema 不混入"页面类型"表。

### 位置

`knowledge/inbox/`，平级于 `wiki/`、`raw/`、`maps/`、`.wiki/`。

进 Git 知识正本，但**不计入主图谱**、**不参与综合**、**不作为引用来源**。

### 文件命名

`YYYYMMDD-HHmmss-<slug>.md`，时间戳到秒级。同秒冲突时追加 `-NN` 短序号。

### 归档目录

promoted / dropped 文件移动到 `knowledge/inbox/archive/<status>/<filename>`：

```text
knowledge/inbox/
├── 20260526-153012-attention-complexity.md     # status: draft
├── 20260526-160045-rag-vs-graphrag.md          # status: draft
└── archive/
    ├── promoted/
    │   └── 20260520-091200-tx-isolation.md     # status: promoted
    └── dropped/
        └── 20260518-143300-misc.md             # status: dropped
```

健康度统计**只计 `knowledge/inbox/*.md`**（即 draft 状态），archive 不计入告警阈值。

### Frontmatter 字段

```yaml
---
id: inb_20260526_153012_attention-complexity     # inb_ prefix，slug 紧跟秒级时间戳
type: inbox                                       # 不进入 wiki 页面类型枚举
status: draft                                     # draft | promoted | dropped
created: 2026-05-26
captured_from: "chat-20260526-1530"               # 来源会话/上下文标识，可选
confidence: low
review: true
suggested_target_type: topic                      # Agent 建议晋升后的类型
suggested_target_title: "Attention 复杂度讨论"
---
```

| 字段 | 说明 |
| --- | --- |
| `id` | `inb_YYYYMMDD_HHmmss_<slug>`；inb_ 是 [01-architecture.md](01-architecture.md) "稳定 ID 规则" prefix 表的扩展 |
| `type` | 固定为 `inbox`；**不参与 wiki 页面 lint**（不校验 sources / related 完整性） |
| `status` | `draft` / `promoted` / `dropped` |
| `created` | 创建日期 |
| `captured_from` | 来源会话或上下文标识，可选 |
| `confidence` | `low` / `medium` / `high`，默认 `low` |
| `review` | 默认 `true` |
| `suggested_target_type` | Agent 建议晋升时的目标页面类型（`topic` / `entity` / `decision` / ...） |
| `suggested_target_title` | Agent 建议晋升时的标题 |

正文：不超过 30 行。可带 `[[wikilink]]`，但不强制。

### Capture item 不参与的 lint

- sources / related 完整性
- canonical cross-ref 校验
- 主图谱节点统计
- evidence_count 一致性

参与的 lint：

- `knowledge/inbox/*.md` 文件数（仅 draft 状态）
- 最老 draft 年龄
- 超过阈值（默认 30 天）未处理 draft 告警
- `capture_policy.json` schema 校验

## Capture Policy Schema

路径：`knowledge/.wiki/capture_policy.json`

用途：控制 Agent 是否被允许直接写入 `knowledge/inbox/`，以及哪些内容/路径默认不自动 capture。属于知识正本（进 Git，团队级可共享）。

### 顶层格式

```json
{
  "version": 1,
  "auto_capture": false,
  "exclude_patterns": [
    "密钥", "token", "API[_ ]?key",
    "客户(姓名|名单|信息)",
    "@[a-z]+\\.com",
    "1[3-9]\\d{9}"
  ],
  "exclude_paths": [],
  "max_inbox_files": 100,
  "updated_at": "2026-05-26T15:00:00+08:00"
}
```

### 字段约束

| 字段 | 含义 |
| --- | --- |
| `version` | schema 版本，当前 `1` |
| `auto_capture` | 是否允许 Agent 直接写 `knowledge/inbox/`，**默认 `false`**（必须用户主动 opt-in） |
| `exclude_patterns` | 正则数组，命中任一就降级为"建议 capture"模式，不自动写入 |
| `exclude_paths` | glob 数组，Agent 在涉及这些路径的对话中不自动 capture。**默认空数组**——决策类讨论是 capture 的高价值场景，不应被默认排除 |
| `max_inbox_files` | inbox/ 文件超过此数时停止自动 capture，强制 promotion；默认 100 |
| `updated_at` | ISO 8601 时间戳 |

### 重要约束（apply 时必须显式标注）

> **`exclude_patterns` 中的默认正则仅是初始规则，不代表完整 PII 检测**。生产用法必须由 lint 规则、人工 review 规则和组织安全规范共同保障。Agent 不得把这套正则当作唯一 PII 兜底。

## Wiki Profile Schema

路径：`<instance-root>/.wiki-profile.json`

用途：给某个知识库实例声明 base schema 之外的业务扩展。它是实例级 canonical config，进 Git；不放在 `<instance-root>/.wiki/`，因为 `.wiki/` 主要承载派生层和工具状态。

不存在 `.wiki-profile.json` 时，实例使用纯 base schema；缺省实例根是 `knowledge/`。

### 顶层格式

```json
{
  "schema_version": 1,
  "profile": "risk-control",
  "description": "风控业务知识库（可选）",
  "extra_page_types": [
    {
      "type": "case",
      "id_prefix": "case",
      "dir": "wiki/cases",
      "description": "风险案例（可选）",
      "required_fields": ["case_id", "severity"],
      "optional_fields": ["resolved_at"]
    }
  ],
  "extra_field_enums": {
    "severity": ["low", "medium", "high", "critical"]
  },
  "extra_optional_fields": {
    "topic": ["business_line"]
  }
}
```

### 字段约束

| 字段 | 规则 |
| --- | --- |
| `schema_version` | 必填；必须等于引擎 `BASE_SCHEMA.schema_version`，当前为 `1` |
| `profile` | 可读 profile 名，`^[a-z][a-z0-9-]*$` |
| `description` | 可选说明 |
| `extra_page_types[].type` | 新页面类型，`^[a-z][a-z0-9-]*$`，不得撞 base 类型或同 profile 其它类型 |
| `extra_page_types[].id_prefix` | 2-5 位小写字母，不含下划线；不得撞 base prefix、`inb` 或同 profile 其它 prefix |
| `extra_page_types[].dir` | 必须在 `wiki/` 下，不含 `..`，不得撞 base 目录或同 profile 其它目录 |
| `extra_page_types[].required_fields` | 新增必填字段名数组，字段名 `^[a-z][a-z0-9_]*$` |
| `extra_page_types[].optional_fields` | 新增可选字段名数组；不得与同 type required 字段重复 |
| `extra_field_enums` | 只允许给 profile 引入的新字段声明 enum |
| `extra_optional_fields` | key 必须是 base type 或 profile extra type；value 是新增可选字段名数组 |

### 不可改写的核心不变量

profile 只能新增，不能覆盖或收窄 base：

- 稳定 ID 格式 `<id_prefix>_YYYYMMDD_<slug>`；inbox 固定 `inb_YYYYMMDD_HHmmss_<slug>`。
- canonical 引用语义：`source_ids`、`related_ids`、`supersedes`、`superseded_by`、`canonical_id`。
- source 单主键：`id == source_id == summary_page_id`。
- entity alias/redirect 语义：`status: redirect` 仅 entity，不允许 canonical 链式跳转。
- inbox 必经缓冲、派生层不进 Git。
- core 必填字段、`status` / `confidence` enum。
- JSON 契约：`source_manifest`、`review_queue`、`capture_policy`、`id_index`、`normalized_alias_index`、`inbox_index`、`graph-data`。
- PII 兜底下限。

### Lint 错误码

| code | 触发 |
| --- | --- |
| `PROFILE_SCHEMA_VERSION` | profile schema_version 与 base 不兼容 |
| `PROFILE_PREFIX_FORMAT` | `id_prefix` 格式非法 |
| `PROFILE_PREFIX_COLLISION` | `id_prefix` 与 base/inbox/其它 profile prefix 冲突 |
| `PROFILE_TYPE_COLLISION` | extra type 与 base/其它 profile type 冲突 |
| `PROFILE_DIR_INVALID` | `dir` 不在 `wiki/` 下、逃逸或冲突 |
| `PROFILE_FIELD_INVALID` | 字段名或字段结构非法 |
| `PROFILE_FIELD_OVERLAP` | required/optional 字段重复 |
| `PROFILE_CORE_SHADOW` | profile 尝试覆盖 core/base 字段 |
| `PROFILE_ENUM_UNKNOWN_FIELD` | enum 指向未声明的新字段 |
| `PROFILE_OPTFIELD_UNKNOWN_TYPE` | optional fields 指向未知 type |

### PII 降级流程

```text
对话内容 → 命中 exclude_patterns 任一正则？
  ├── 是 → 强制降级为"建议 capture"模式（无论 auto_capture 开关）
  └── 否 → 检查 exclude_paths
        ├── 命中 → 强制降级为"建议 capture"
        └── 未命中 → 按 auto_capture 开关决定写入或建议
```

## Inbox Index Schema

路径：`knowledge/.wiki/inbox_index.json`

用途：Agent 会话开始读取的 inbox 高密度索引；提供 draft 数量、最老 draft 年龄和最近 N 条 draft 轻摘要，避免 Agent 把全部 draft 正文拉进上下文。

**派生层**（由 `wiki-lint` 扫描 `knowledge/inbox/*.md` 生成；可重建；进 `.gitignore`，不作为知识正本）。

### 顶层格式

```json
{
  "version": 1,
  "draft_count": 12,
  "oldest_draft_age_days": 8,
  "recent_drafts": [
    {
      "filename": "20260526-153012-attention-complexity.md",
      "summary": "Attention 复杂度讨论",
      "captured_at": "2026-05-26T15:30:12+08:00"
    }
  ],
  "updated_at": "2026-05-26T16:00:00+08:00"
}
```

### 字段约束

| 字段 | 含义 |
| --- | --- |
| `version` | schema 版本，当前 `1` |
| `draft_count` | `knowledge/inbox/*.md` 中 `status: draft` 的文件数；**不含** `archive/` |
| `oldest_draft_age_days` | 最老 draft 距今天数，按 frontmatter `created` 计算 |
| `recent_drafts[]` | 最近 N 条 draft 的轻摘要数组，默认 `N = 10` |
| `recent_drafts[].filename` | inbox 文件名（不含路径） |
| `recent_drafts[].summary` | 摘要文本，优先来自 frontmatter `suggested_target_title`，回退到正文首句 |
| `recent_drafts[].captured_at` | ISO 8601 时间戳，优先 frontmatter `created`，回退到文件名解析的秒级时间戳 |
| `updated_at` | 索引重建时刻，ISO 8601 |

### 生成时机

- `wiki-lint` 每次扫描时重新生成
- 新 capture 写入 / promotion / drop 后建议触发重建

### 不包含

- draft 正文（保持索引高密度，正文按需另读）
- `archive/promoted/` 或 `archive/dropped/` 的文件

## Normalized Alias Index Schema

路径：`knowledge/.wiki/normalized_alias_index.json`

用途：把所有 entity 页的 `aliases`（以及 H1 标题、别名薄页 `id`）规范化后建立倒排索引，供摄入 Triage 和 Inbox 晋升做 entity 消歧。

**派生层**（由 `wiki-lint` 扫描 `knowledge/wiki/entities/*.md` 生成；可重建；进 `.gitignore`，不作为知识正本）。

### 顶层格式

```json
{
  "version": 1,
  "updated_at": "2026-05-27T10:00:00+08:00",
  "entries": {
    "attention": {
      "canonical_id": "ent_20260526_attention",
      "matched_form": "Attention",
      "source": "title"
    },
    "self-attention": {
      "canonical_id": "ent_20260526_attention",
      "matched_form": "self-attention",
      "source": "alias"
    },
    "自注意力": {
      "canonical_id": "ent_20260526_attention",
      "matched_form": "自注意力",
      "source": "alias"
    },
    "sdpa": {
      "canonical_id": "ent_20260526_attention",
      "matched_form": "SDPA",
      "source": "alias"
    }
  }
}
```

### 字段约束

| 字段 | 含义 |
| --- | --- |
| `version` | schema 版本，当前 `1` |
| `updated_at` | 索引重建时刻，ISO 8601 |
| `entries` | normalized key → entity 信息映射 |
| `entries[k]` | 规范化字符串作为 key |
| `entries[k].canonical_id` | 指向正名页 `id`（不指向薄重定向页 `id`，链式跳转在 lint 阶段平展） |
| `entries[k].matched_form` | 原始未规范化字符串 |
| `entries[k].source` | `title` / `alias` / `redirect`（来源是 H1 标题 / aliases 字段 / 薄重定向页） |

### 规范化规则

至少覆盖：

- 大小写折叠（`Attention` ↔ `attention`）
- 首尾空白与连续空白合并
- 连字符 / 下划线 / 空格 互换（`self-attention` ↔ `self attention` ↔ `self_attention`）
- 中文全角 / 半角统一（`，` ↔ `,`、`（` ↔ `(`）
- 英文复数尾 `s` / `es`（可选；歧义较大时不规范化）

规范化算法本身的具体实现留给 `wiki-lint`；本 schema 只规定**结果格式**。

### lint 校验（Decision #2 替代版）

- 所有 `canonical_id` 指向必须存在
- 若某页 `canonical_id != null`：该页必须是薄重定向页，`aliases` 应为空或只含本页标题严格同义写法，且 `status` 必须是 `redirect`
- `canonical_id` 必须指向 `canonical_id: null` 的正名页（不允许链式：A → B → C）
- 同一规范化 alias key 不能映射到两个不同 `canonical_id`；冲突时 lint 写入 `review_queue.json type: duplicate`

### 生成时机

- `wiki-lint` 每次扫描重新生成
- 新 entity 创建 / aliases 字段变化后建议触发重建

### 不包含

- 非 entity 类型页面
- inbox draft（inbox 晋升时若涉及 entity，先做 alias matching 再决定晋升路径）

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
| `status` | `draft`、`active`、`stale`、`archived`、`redirect`（`redirect` 仅 entity 别名薄页） |
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
| `aliases` | （仅 entity）已知别名字符串数组；规范化匹配走派生 `normalized_alias_index.json` |
| `canonical_id` | （仅 entity）`null` = 正名页；指向某 `id` = 薄重定向页，必须配 `status: redirect` |
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
aliases: []                                # entity 已知别名字符串数组（人类写法）；正名页可有，薄重定向页应为空
canonical_id: null                         # null = 正名页；指向某 ent_id = 薄重定向页（须 status: redirect）
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

> **别名管理**：99% 的别名应只放在正名页的 `aliases` 列表里。仅在外部已有 wikilink 散布到某别名时，才建薄重定向页（`canonical_id` 指向正名页 + `status: redirect`，正文留一行"重定向到 [[正名]]" 即可）。
>
> **alias 来源**（可选，不强制）：alias 字符串可在正文里附上 source 引用，例如：
> ```
> ## 别名来源
> - "SDPA" → [[src_xxx_attention-paper]]
> ```
> 未来如需结构化此关系，另开 RFC。本期不引入新 frontmatter 字段。

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

**别名引用规则**：如果用户原话用了某 entity 的别名（如 "self-attention"），Agent 回答时应保留用户原写法并附正名 wikilink，**不要把别名包成 wikilink**：

- 正确：`self-attention（正名 [[Attention]]）`
- 错误：`[[self-attention]]（正名 [[Attention]]）`（除非别名薄页确实存在）

后续段落引用统一用正名 `[[Attention]]`。

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

> **状态（2026-05-28）**：`scripts/wiki-lint` 已由 RFC-006 + TASK-006 落地为 `scripts/wiki_lint.py`，覆盖 frontmatter / 断链 / source manifest / review queue / entity alias / inbox / PII 八类校验，并生成 `id_index.json` / `normalized_alias_index.json` / `inbox_index.json` 三类派生层。`wiki-context` / `wiki-graph-refresh` 仍待后续 RFC。

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
