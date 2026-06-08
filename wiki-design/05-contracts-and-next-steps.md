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

权威字段定义见 `knowledge/.wiki-schema.md` 的 `.wiki/review_queue.json` 段；本节只保留设计意图：

- review queue 是人工审查入口，不是长期知识结论本身。
- canonical 引用应落到 `affected_page_ids` / `evidence[].page_id`，显示路径只作辅助。
- `source_gap` 可以作为 triage 阶段临时队列；决定长期保留时应晋升为 `wiki/open-questions/*-source-gap.md`。

## Source Manifest Schema

路径：`knowledge/raw/source_manifest.json`

用途：登记所有进入知识库的原始资料，连接 hash、原始位置、来源 URL、摄入状态和 source 摘要页。

权威字段定义见 `knowledge/.wiki-schema.md` 的 `raw/source_manifest.json` 段；本节只保留设计意图：

- `source_id` 是原始资料进入知识库后的稳定主键。
- source 摘要页生成后必须满足 source 单主键：`id == source_id == summary_page_id`。
- ingest 进度以 manifest status 为单一事实源，`--ingest-status` 只读 manifest 派生待 apply 清单。

## Capture Item Schema

Inbox 文件不算 `wiki/**/*.md` 页面，独立为 **capture item**，schema 不混入"页面类型"表。

权威字段、命名、归档和 lint 口径见 `knowledge/.wiki-schema.md` 的 `inbox capture item frontmatter` 段；本节只保留设计意图：

- `knowledge/inbox/` 是低摩擦缓冲层，进 Git，但不计入主图谱、不参与综合、不作为引用来源。
- draft 文件只统计 `knowledge/inbox/*.md`；`archive/promoted/` 和 `archive/dropped/` 不计入健康度告警阈值。
- capture item 只承担“先存下来”的职责，晋升到长期知识时再写入 `knowledge/wiki/**`。

## Capture Policy Schema

路径：`knowledge/.wiki/capture_policy.json`

用途：控制 Agent 是否被允许直接写入 `knowledge/inbox/`，以及哪些内容/路径默认不自动 capture。属于知识正本（进 Git，团队级可共享）。

权威字段定义见 `knowledge/.wiki-schema.md` 的 `.wiki/capture_policy.json` 段与引擎 `BASE_SCHEMA`；本节只保留设计意图：

- `auto_capture` 默认关闭，自动 capture 必须显式 opt-in。
- `hard_redact` 是任何库都不可放宽的 error 级硬底线；`soft_redact` 是 warning 级软项，可按库配置。
- `visibility` 的 effective 值由页面 / source 显式字段、库默认值和 legacy fallback 共同决定，lint 不写回字段。
- 默认正则仅是初始规则，不代表完整 PII 检测；生产用法必须由 lint、人工 review 和组织安全规范共同兜底。

## Wiki Profile Schema

路径：`<instance-root>/.wiki-profile.json`

用途：给某个知识库实例声明 base schema 之外的业务扩展。它是实例级 canonical config，进 Git；不放在 `<instance-root>/.wiki/`，因为 `.wiki/` 主要承载派生层和工具状态。

权威字段定义见 `knowledge/.wiki-schema.md` 的 `Schema Profile` 段与引擎 `BASE_SCHEMA`；本节只保留设计意图：

- 不存在 `.wiki-profile.json` 时，实例使用纯 base schema。
- profile 只能新增页面类型、新字段 enum 和某类型额外可选字段，不能覆盖或收窄 base。
- 稳定 ID、canonical 引用、source 单主键、entity alias/redirect、inbox、JSON 契约、PII 下限和派生层规则都是不可改写的核心不变量。

## Inbox Index Schema

路径：`knowledge/.wiki/inbox_index.json`

用途：Agent 会话开始读取的 inbox 高密度索引；提供 draft 数量、最老 draft 年龄和最近 N 条 draft 轻摘要，避免 Agent 把全部 draft 正文拉进上下文。

权威格式见 `knowledge/.wiki-schema.md` 的派生层 JSON 契约；本节只保留设计意图：

- 它是派生层，由 `wiki-lint` 扫描 `knowledge/inbox/*.md` 生成，可重建，不作为知识正本。
- 它不包含 draft 正文，也不包含 `archive/promoted/` 或 `archive/dropped/` 文件。

## Normalized Alias Index Schema

路径：`knowledge/.wiki/normalized_alias_index.json`

用途：把所有 entity 页的 `aliases`（以及 H1 标题、别名薄页 `id`）规范化后建立倒排索引，供摄入 Triage 和 Inbox 晋升做 entity 消歧。

权威格式见 `knowledge/.wiki-schema.md` 的派生层 JSON 契约；本节只保留设计意图：

- 它是派生层，由 `wiki-lint` 扫描 `knowledge/wiki/entities/*.md` 生成，可重建，不作为知识正本。
- 规范化算法由 `wiki-lint` 实现；schema 只规定结果格式和 alias/redirect 不变量。
- 它不包含非 entity 类型页面，也不包含 inbox draft。

## Frontmatter 生命周期字段

所有 `wiki/**/*.md` 页面尽量使用同一组字段。字段少一点可以，但字段名不要变体膨胀。

权威字段定义、status / confidence / visibility enum 和各类型额外字段见 `knowledge/.wiki-schema.md` 的 `标准 frontmatter（wiki/ 页面）` 段。`wiki-design/01-architecture.md` 仍保留稳定 ID 与 cross-ref 的设计解释。

## 最小页面模板

最小页面模板的权威版本见 `knowledge/.wiki-schema.md`。本文件不再镜像 source / entity / topic / decision / open-question / query 等模板，避免字段和 enum 漂移。

保留的设计边界：

- Source 摘要页必须满足 source 单主键。
- Entity 别名优先放正名页 `aliases`；只有外部已有 wikilink 散布且不便迁移时才建薄重定向页。
- Query 页面只保存值得长期沉淀的问答，并标注引用和置信度缺口。

## 答案引用格式

权威格式见 `knowledge/.wiki-schema.md` 的 `答案引用格式` 段；本节只保留设计意图：

1. 先引用 Human Wiki 页面，因为这是长期知识层。
2. 如果关键事实来自 source 页面，补充原始资料路径或 `source_id`。
3. 如果结论是回答时新推导的，标注为 `INFERRED`，不要伪装成已有知识。
4. 如果需要保存回答，写入 `wiki/queries/`，并把 `derived: true` 写入 frontmatter。
5. 用户原话用了 entity 别名时，保留别名原文并附正名 wikilink，不把别名本身包成 wikilink。

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
