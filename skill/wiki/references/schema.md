# llm-wiki schema 详细参考

写 wiki 页面时遵循。简版速查见 SKILL.md，本文件是完整规范。

## 目录

- [标准 frontmatter（wiki 页面）](#标准-frontmatter)
- [各类页面模板](#各类页面模板)
- [inbox（capture item）](#inbox-capture-item)
- [canonical vs 显示层](#canonical-vs-显示层)
- [entity 别名机制](#entity-别名机制)
- [ingest 两步流程](#ingest-两步流程)
- [硬约束（lint 会查）](#硬约束)

## 标准 frontmatter

wiki/ 下每个页面：

```yaml
---
id: <prefix>_YYYYMMDD_<slug>      # 永不变
type: source | entity | topic | comparison | synthesis | decision | query | open-question
status: draft | active | stale | archived | redirect   # redirect 仅 entity 薄页
confidence: low | medium | high
created: YYYY-MM-DD
updated: YYYY-MM-DD
last_verified: YYYY-MM-DD
review: true | false
source_ids: []        # canonical 来源引用（按 ID）
related_ids: []       # canonical 相关页引用（按 ID）
sources: []           # 显示层 wikilink（可选）
related: []           # 显示层 wikilink（可选）
supersedes: []        # 替代的旧页 ID
superseded_by: []     # 替代本页的新页 ID
evidence_count: 0
---
```

source 额外：`source_id`（== id）/ `hash_sha256`（64 hex）/ `original_path` / `source_url` / `imported_at`。
entity 额外：`aliases: []` / `canonical_id: null`（正名页 null；薄重定向页指向正名 id + status: redirect）。

日期 `YYYY-MM-DD`；wikilink 用 `[[slug|显示标题]]`。

## 各类页面模板

正文结构灵活，但建议每页有：H1 标题、一句话摘要（`>` 引言）、分节正文、`## 引用`（如有来源）、`## 置信度与缺口`。

**topic**（跨来源主题）：当前结论 / 证据 / 开放问题 / 相关页。
**synthesis**（多来源综合）：高层综述，关联多个页面，常作枢纽。
**entity**（公司/人/项目/模型/工具）：简介 / 关键事实 / 不同来源说法 / 相关页。aliases 放别名。
**decision**（重要判断/取舍）：背景 / 决策 / 理由 / 影响 / 后续验证。
**comparison**（对比）：对比维度表 + 结论。
**source**（单来源摘要）：基本信息 / 核心观点 / 关键概念 / 证据摘录 / 关联冲突；id == source_id。
**query**（值得沉淀的问答）：问题 / 回答 / 引用。
**open-question**（待验证/冲突/空白）：为什么重要 / 已知 / 缺口 / 下一步验证。

## inbox capture item

`<root>/inbox/YYYYMMDD-HHmmss-<slug>.md`：

```yaml
---
id: inb_YYYYMMDD_HHmmss_<slug>
type: inbox
status: draft          # draft → 晋升后移到 archive/promoted/ 或 archive/dropped/
created: YYYY-MM-DD
review: true
confidence: low
suggested_target_type: topic | entity | decision | ...
suggested_target_title: <晋升后页面标题>
---

正文：一句话/一段要点。
```

文件名 `YYYYMMDD-HHmmss-<slug>.md`（秒级，同秒冲突追加 `-NN`）。inbox 不是 wiki 页，不进图谱、不作引用来源。

## canonical vs 显示层

| | canonical（lint 校验、按 ID） | 显示层（给人看，不校验完整性） |
| --- | --- | --- |
| 字段 | `source_ids`/`related_ids`/`supersedes`/`superseded_by`/`canonical_id` | `sources`/`related`（wikilink） |
| 原则 | 机器引用，改名不破坏 | Obsidian 可读 |

建页面互联时：`related_ids` 填目标页 **id**；`related` 填 `[[目标slug|标题]]`。两者要对应。

## entity 别名机制

- 99% 别名放正名页的 `aliases: []`，不建薄页。
- 极少数才建薄重定向页：`canonical_id` 指向正名页 id + `status: redirect`（仅 entity），不链式（A→B→C 非法）。
- 答案里用户用别名时：保留别名原文 + 附正名 wikilink，**别名本身不要包成 wikilink**。
  - 正确：`self-attention（正名 [[attention|Attention]]）`
  - 错误：`[[self-attention]]（…）`

## ingest 两步流程

资料在 `<root>/raw/sources/<file>`。

### Triage（识别 + 登记，不动 wiki/）

1. 算 `sha256`
2. 在 `raw/source_manifest.json` 的 `sources[]` 追加一条：`source_id`（`src_YYYYMMDD_slug`）/ title / source_type / hash_sha256 / original_path / status: triaged / summary_page_id: null
3. 抽实体 → alias matching（查 `.wiki/normalized_alias_index.json` 复用现有 entity，编辑距离近的入 review_queue duplicate）
4. 子链接处理：
   - 内部文档链接：脱 token / 内部 URL，但保留"链向 X 文档"；目标值得收时建子 source，正文未抓到时用 `status: draft` + `confidence: low` 占位，父 source 用 `related_ids` / `related` 关联子 source
   - 相关且未抓到 / 未 ingest 的子文档：建 `wiki/open-questions/*-source-gap.md`，正文写 `## 已知信息` + `## 待确认`
   - 导航、页脚、泛工单入口等弱相关链接不建 source-gap；外部链接只保留脱敏说明，不建 source
   - 不自动递归；用户要求补抓某子文档时，作为新的独立 ingest
5. 冲突/重复/缺口 → 写 `.wiki/review_queue.json` 的 `items[]`；其中 `source_gap` 只作临时队列，长期待办晋升为 open-question
6. 给用户审阅计划，**先不写 wiki/**

### Apply（用户确认后）

1. 写 `wiki/sources/<slug>.md` 摘要页（id == source_id == summary_page_id）
2. 联动 entities/topics（新建或更新 last_verified + source_ids）
3. 回填 manifest：status: ingested、summary_page_id = source_id、summary_page_path
4. 跑 lint + graph + 更新 log

## 硬约束

lint 会机械检查，违反不算完成：

- source 单主键：source 页 `id == source_id == manifest.summary_page_id`
- supersedes 对称：A `supersedes:[B]` ⇒ B `superseded_by` 含 A
- canonical 引用不断：所有 ID 引用能解析到真实页
- 同日同 slug 冲突：追加 `_NN`
- hash 64 位小写 hex；日期 `YYYY-MM-DD`；JSON 顶层 `version: 1`
- 上下文层四文件（purpose/index/overview/log）**无 frontmatter**
- entity alias 全局唯一、canonical_id 不链式、redirect 仅 entity
- 三个 JSON 契约（source_manifest/review_queue/capture_policy）只能按 schema 写

## 业务 profile（如果库有 .wiki-profile.json）

实例根若有 `.wiki-profile.json`，该库可能有额外页类型/字段（只增不改 base）。写之前看一眼实例根的 `.wiki-schema.md` 和 `.wiki-profile.json` 了解本库定制。lint 会按 effective schema（base + profile）校验。
