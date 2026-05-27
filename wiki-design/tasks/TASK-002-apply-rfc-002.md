---
id: task_20260526_002
title: Apply RFC-002 — 把稳定 ID 机制落到 01-architecture / 05-contracts / .gitignore
author: claude
executor: codex
status: done
type: apply
created: 2026-05-26
updated: 2026-05-26  # v2 after codex spec review v1
related_rfcs:
  - rfc_20260526_002
---

# TASK-002: Apply RFC-002 — 把稳定 ID 机制落到正本

## 目标

把 RFC-002 Decision 中的 8 条 apply 条件落到三个正本：

- `wiki-design/01-architecture.md`
- `wiki-design/05-contracts-and-next-steps.md`
- `.gitignore`

执行完成后，从这三份文件读到的 schema 必须能让一个不读 RFC-002 的 Agent 也能正确建页面、写 cross-ref。

## 前置条件

- 仓库根目录：`/Users/zhangjunwu/workspace/llm-wiki/llm-wiki`
- HEAD 包含 RFC-002 status: accepted（commit `f387851` 及之后）
- working tree clean
- 已读 `wiki-design/rfcs/RFC-002-stable-page-ids.md`（含 Decision 8 条）
- 已读 `wiki-design/tasks/README.md` 理解 task 规则
- **本 task 不动 RFC-003 / RFC-004 相关内容**（即不加 `inb_` prefix、不加 `aliases`、不加 `status: redirect` 等；这些由 TASK-003 / TASK-004 处理）

## 强约束

违反任一即视为执行失败，应在 Execution log 写明并把 status 改为 failed：

1. **只动 3 个文件**：`wiki-design/01-architecture.md`、`wiki-design/05-contracts-and-next-steps.md`、`.gitignore`。其它一律不动。
2. **不创建** `knowledge/` 任何文件或目录（属于 TASK-005）。
3. **不动** AGENTS.md、wiki-design/02-workflows.md、wiki-design/04-agent-rules.md、wiki-design/README.md、任何 RFC 文件、以及**其它** TASK 文件。
   - **本 TASK-002 文件本身按 Step 0 / 6 / 7 允许编辑**：追加 Spec review 段、推进 frontmatter `status`、追加 Execution log 段。除此之外不得改本文件其它部分（不动原 Proposal、不动其它 agent 的 Spec review 段）。
4. **保留** 01/05 原有不被本 task 覆盖的章节和段落（设计目标、分层、与 Repo Wiki 的关系、实施顺序等）。
5. **必须先经 Codex spec review**：本 task 在 frontmatter `status: pending` 状态下不可执行。Codex 要先在文件末尾追加 `## Spec review by codex · 2026-05-26` 段，给出"通过" 或 "需修改" 结论。只有 spec review 通过后，executor 才能开始 Step 1（见"工作流"段）。
6. 一次性 commit 所有正本改动；TASK 状态推进单独 commit。
7. 不引入除 RFC-002 Decision 8 条之外的新概念或字段。

## 工作流

```
Step 0  Codex spec review (本 task 文件，追加 Spec review 段)
        │
        │  通过 → Step 1
        │  需修改 → Claude 改 spec → 重新进入 Step 0
        │
        ▼
Step 1~4  Codex 执行文件编辑
        │
        ▼
Step 5  自检验证
        │
        ▼
Step 6  Commit 正本改动
        │
        ▼
Step 7  推进 task status pending → done + 追加 Execution log + commit
```

## 步骤

### Step 0：Spec review（执行前必跑）

在本 task 文件末尾追加：

```markdown
## Spec review by codex · 2026-05-26

### 完整性
- [ ] Decision 8 条是否全部覆盖
- [ ] 新内容是否仅来自 RFC-002（不混 003/004）
- [ ] 边界（哪些不改）是否清晰

### 可执行性
- [ ] 每个 Step 是否有明确的 anchor / 新内容
- [ ] 验证步骤是否可机械跑

### 风险
- 列出可能踩坑的地方

### 结论
- 通过 / 需修改 (列出建议)
```

如果"需修改"，Codex 不要自行改 spec；只给出建议，由 Claude 修订。Spec review 段一旦写入，**status 字段不改**（保持 pending），由 Claude 或用户决定下一步。

### Step 1：更新 `wiki-design/01-architecture.md`

#### 1a：在 "正本与派生层" 的"派生数据"列表末尾加一行

找到这段（应在 "派生数据：" 标题下的 code block 内）：

```text
knowledge/maps/graph-data.json
knowledge/.wiki/cache.json
knowledge/.wiki/search_index/
knowledge/.wiki/lightrag/
```

末尾追加：

```text
knowledge/.wiki/id_index.json
```

#### 1b：替换 Frontmatter section 中的 YAML 示例

把当前 YAML 示例（以 `type: topic` 开头到 `evidence_count: 1` 结束的那个）整段替换为：

```yaml
---
id: top_20260524_agent-native-wiki         # 稳定主键，永不随 slug / title / path 变化
type: topic
status: active
confidence: medium
created: 2026-05-24
updated: 2026-05-24
last_verified: 2026-05-24
review: false
tags:
  - wiki/topic
source_ids:                                # canonical 来源引用（按 ID）
  - src_20260524_some-source
related_ids:                               # canonical 相关页引用（按 ID）
  - ent_20260524_lightrag
sources:                                   # 可选显示层，Obsidian wikilink
  - "[[某篇来源摘要]]"
related:
  - "[[LightRAG]]"
  - "[[Agent-native Wiki]]"
supersedes: []                             # ID 数组
superseded_by: []                          # ID 数组
evidence_count: 1
---
```

#### 1c：替换 Frontmatter section 中的字段表

把当前字段表（从 `| 字段 | 说明 |` 一直到 `| evidence_count | ... |`）整体替换为：

```markdown
| 字段 | 说明 |
| --- | --- |
| `id` | 稳定主键，格式 `<prefix>_YYYYMMDD_<slug>`；**永不随标题、slug、路径变化**；prefix 见下方"稳定 ID 规则" |
| `type` | 页面类型 |
| `status` | `draft`、`active`、`stale`、`archived` |
| `confidence` | `low`、`medium`、`high` |
| `created` | 页面创建日期 |
| `updated` | 最近维护日期 |
| `last_verified` | 最近一次对照来源验证核心结论的日期 |
| `source_ids` | canonical 来源引用，按 ID；lint 校验完整性 |
| `related_ids` | canonical 相关页引用，按 ID |
| `sources` | 可选显示层（Obsidian wikilink），不参与 lint 完整性 |
| `related` | 可选显示层（Obsidian wikilink），不参与 lint 完整性 |
| `review` | 是否需要人工审核 |
| `supersedes` | 本页面替代的旧页面 ID 列表 |
| `superseded_by` | 替代本页面的新页面 ID 列表 |
| `evidence_count` | 支撑核心结论的来源或证据数量 |
```

#### 1d：在字段表之后、`Schema 与 Agent 规则` 段之前插入三个新子节

插入下列内容（注意保留与原文档一致的标题级别——这三个新段都是 `###`）：

~~~markdown
### 稳定 ID 规则

每个页面的 `id` 一旦创建，**永不变化**。重命名、移动目录、改 H1 标题都不动 `id`。

格式：`<prefix>_YYYYMMDD_<slug>`

| 类型 | prefix | 示例 |
| --- | --- | --- |
| source | `src_` | `src_20260526_attention-is-all-you-need` |
| entity | `ent_` | `ent_20260526_attention` |
| topic | `top_` | `top_20260526_transformer-architecture` |
| comparison | `cmp_` | `cmp_20260526_rag-vs-graphrag` |
| synthesis | `syn_` | `syn_20260526_attention-overview` |
| decision | `dec_` | `dec_20260526_use-lightrag` |
| query | `que_` | `que_20260526_what-is-rag` |
| open-question | `oq_` | `oq_20260526_consistency-vs-availability` |

**source 单主键约束**：source 类型页面 `id` 必须等于该 source 在 `knowledge/raw/source_manifest.json` 中的 `source_id`。其它页面类型的 `id` 与业务 ID 无关。

**同日冲突**：同 prefix 同日同 slug 重名时，追加 `_NN` 短序号，例如 `ent_20260526_attention_002`。由 lint 强制全局唯一。

**slug 不是当前标题镜像**：slug 是页面**创建时**的可读提示。页面 H1 改名后 slug 不变。

### 拆分与合并语义

页面被拆分时：

- 拆出的新页面拿**新 ID**。
- 旧页面若部分内容保留，**原 ID 不变**，正文调整即可。
- 旧页面若完全被新页面取代，标 `status: archived` + `superseded_by: [新 ID 数组]`。

页面被合并时：

- 被合并页（要消失的那个）保留**壳 frontmatter**，标 `status: archived` + `superseded_by: [合并目标 ID]`，正文清空或留一行重定向说明。
- 合并目标页保留**原 ID**，吸收被合并页的实质内容。

### Cross-ref 字段说明

下列引用是 **canonical** 的（lint 严格校验、未来工具按 ID 索引）：

| 位置 | 字段 |
| --- | --- |
| 页面 frontmatter | `id`、`source_ids`、`related_ids`、`supersedes`、`superseded_by` |
| `review_queue.json` 单条 item | `affected_page_ids`、`evidence.page_id` |
| `source_manifest.json` 单条 source | `summary_page_id` |
| 未来 `maps/graph-data.json` 节点 key | 页面 `id` |

下列是 **可选显示层**（仅给人看，lint 不强制完整性）：

| 位置 | 字段 |
| --- | --- |
| 页面 frontmatter | `sources`、`related`（wikilink） |
| `review_queue.json` 单条 item | `evidence.page_path`、`source_paths` |
| `source_manifest.json` 单条 source | `summary_page_path` |
| 答案引用里的 `wiki/.../X.md` 字符串 | 可读 path |
~~~

### Step 2：更新 `wiki-design/05-contracts-and-next-steps.md`

#### 2a：在 "目标文件关系" 的代码块中加一行 `id_index.json`

找到这段（应有 `cache.json` 和 `search_index/` 的条目，可能在 `.wiki/` 块下）：

```text
.wiki/
  review_queue.json
  cache.json
  search_index/
  lightrag/
```

末尾在 `lightrag/` 后追加一行：

```text
  id_index.json
```

并在该代码块下方"职责划分"表里追加一行（如果存在该表的话）：

```markdown
| `knowledge/.wiki/id_index.json` | ID → 当前 path 索引，可重建 | 否 |
```

#### 2b：替换 "Frontmatter 生命周期字段" 段的 YAML 示例

把当前 YAML 示例整段替换为：

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

#### 2c：替换 "Frontmatter 生命周期字段" 段的字段含义表

把现有 `| 字段 | 推荐值 |` 表整体替换为：

```markdown
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
```

#### 2d：更新 "Review Queue Schema" 的 JSON 示例和约束表

把"单条 item" 的 JSON 示例整段替换为：

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

更新字段约束表，分两步：

**(i) 替换 `affected_pages` 行**（1 行 → 1 行）：

```markdown
| `affected_page_ids` | canonical，页面 `id` 数组 |
```

**(ii) 在约束表中新增 2 行 evidence 相关说明**（插入位置建议紧贴 `evidence.quote` 行之后）：

```markdown
| `evidence[].page_id` | canonical，页面 `id`；必填 |
| `evidence[].page_path` | 可选显示层；与 `page_id` 一致时由 lint 维护 |
```

保留原 `evidence.quote` / `source_ids` / `options.action` / `resolved_action` 等行不动。

#### 2e：更新 "Source Manifest Schema" 的 JSON 示例和约束表

把"单条 source" 的 JSON 示例整段替换为：

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

更新约束表里的 `summary_page` 行，替换为以下两行：

```markdown
| `summary_page_id` | source 摘要页 frontmatter 的 `id` 字段。**未生成摘要页时为 `null`；已生成时必须等于 `source_id`**。 |
| `summary_page_path` | 可选显示层；对应 source 页面当前路径，未生成时为 `null` |
```

并在 `source_id` 行的"规则"列追加："**摘要页已生成时**（`summary_page_id != null`），其值必须等于摘要页 frontmatter 的 `id` 字段；未生成摘要页时 `source_id` 仍然存在，作为 source_manifest 的稳定标识"。

#### 2f：更新所有"最小页面模板"的 frontmatter

下列六个模板都要加 `id` 字段、`source_ids`、`related_ids`，并把 `supersedes` / `superseded_by` 注释为 ID 数组。下面给出每个模板的**新 frontmatter 块**，正文部分保持不变。

**Source 模板**（保留 `source_id` 字段不动；本 RFC 不删该字段，新增 `id` 字段与之相等）：

```yaml
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
```

**Entity 模板**：

```yaml
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
```

**Topic 模板**：

```yaml
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
```

**Decision 模板**：

```yaml
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
```

**Open Question 模板**：

```yaml
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
```

**Query 模板**：

```yaml
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
```

模板正文部分（`# {{...}}`、`## 简介` 等小标题及其内容）**保持不动**，本步骤只替换 frontmatter。

#### 2g：在"答案引用格式"段开头加一段说明（canonical 边界）

在 "答案引用格式" 段第一行前插入一段：

```markdown
> 引用边界：正文中 `## 引用` 列表里的 `wiki/.../X.md` 路径是**显示用**，不是 canonical。canonical 引用走页面 `id`（见 [01-architecture.md](01-architecture.md) "Cross-ref 字段说明"）。如果同时保留 `id` 和 path，path 仅作为可读注释。
```

### Step 3：更新 `.gitignore`

在文件末尾追加一行：

```
knowledge/.wiki/id_index.json
```

（如果文件末尾已有 `knowledge/maps/graph-data.json` 这类派生层条目，紧贴其后追加。）

### Step 4：自检验证

所有 grep 用 `-c` 返回计数（即使 0 命中也是 exit 0，避免脚本中断）。每条 echo 都标注"应为 X"方便人眼比对。

```bash
cd /Users/zhangjunwu/workspace/llm-wiki/llm-wiki

set +e   # 容忍负向 grep 没有命中（grep 0 命中本身会返回 exit 1）

echo "=== 1. .gitignore 包含 id_index.json（应 ≥ 1）==="
echo "命中: $(grep -c 'id_index.json' .gitignore)"

echo "=== 2. 01-architecture.md 含三个新子节（应 = 3）==="
echo "命中: $(grep -cE '^### (稳定 ID 规则|拆分与合并语义|Cross-ref 字段说明)' wiki-design/01-architecture.md)"

echo "=== 3. 01 中 prefix 表 8 个类型行（应 ≥ 8）==="
echo "命中: $(grep -cE '^\| (source|entity|topic|comparison|synthesis|decision|query|open-question) \|' wiki-design/01-architecture.md)"

echo "=== 4. 05 中页面模板 frontmatter id 字段（应 ≥ 6）==="
echo "命中: $(grep -c '^id: {{' wiki-design/05-contracts-and-next-steps.md)"

echo "=== 5. affected_pages → affected_page_ids ==="
echo "  旧字段 '\"affected_pages\":' 命中（应 = 0）: $(grep -c '\"affected_pages\":' wiki-design/05-contracts-and-next-steps.md)"
echo "  新字段 'affected_page_ids' 命中（应 ≥ 1）: $(grep -c 'affected_page_ids' wiki-design/05-contracts-and-next-steps.md)"

echo "=== 6. summary_page → summary_page_id ==="
echo "  旧字段 '\"summary_page\":' 命中（应 = 0）: $(grep -c '\"summary_page\":' wiki-design/05-contracts-and-next-steps.md)"
echo "  新字段 'summary_page_id' 命中（应 ≥ 1）: $(grep -c 'summary_page_id' wiki-design/05-contracts-and-next-steps.md)"

echo "=== 7. 白名单外的文件不应被动（应输出空 stat / 无文件列表）==="
git diff --stat -- wiki-design/02-workflows.md wiki-design/04-agent-rules.md wiki-design/README.md AGENTS.md wiki-design/rfcs/
git diff --name-only -- wiki-design/tasks/ | grep -v '^wiki-design/tasks/TASK-002-apply-rfc-002.md$' || echo "  (no other task files modified)"

echo "=== 8. knowledge/ 不应存在 ==="
if [ -d knowledge/ ]; then echo "FAIL: knowledge/ exists"; else echo "OK: knowledge/ absent"; fi
```

预期：

- 1：≥ 1
- 2：= 3
- 3：≥ 8
- 4：≥ 6（六个模板各一个，可能更多）
- 5：旧字段 = 0，新字段 ≥ 1
- 6：旧字段 = 0，新字段 ≥ 1
- 7：`git diff --stat` 输出空（无文件被列）；第二条要么无输出，要么打印 "(no other task files modified)"。**TASK-002 本身允许有改动**（Spec review / status / Execution log），因此从这条检查中排除。
- 8：`OK: knowledge/ absent`

### Step 5：Commit 正本改动

```bash
git add .gitignore wiki-design/01-architecture.md wiki-design/05-contracts-and-next-steps.md

git commit -m "$(cat <<'EOF'
[apply rfc-002] stable page IDs across schema and templates

Decision 8 条全部落地：
- id 字段加入 01-architecture frontmatter 表 + 所有 05 页面模板
- 新增 prefix 表（src_/ent_/top_/cmp_/syn_/dec_/que_/oq_）
- source 单主键约束（id == source_id）
- field naming: source_ids / related_ids canonical, sources/related 显示层
- review_queue.affected_pages -> affected_page_ids;
  evidence.page -> evidence.page_id + evidence.page_path
- source_manifest.summary_page -> summary_page_id + summary_page_path
- 新增"稳定 ID 规则" / "拆分与合并语义" / "Cross-ref 字段说明" 三节
- 同日冲突追加 _NN 短序号
- knowledge/.wiki/id_index.json 加入 .gitignore

Co-Authored-By: Codex <noreply@openai.com>
EOF
)"
```

### Step 6：推进 task status pending → done

完成 Step 5 后：

1. 修改本文件 frontmatter `status: pending` → `status: done`
2. `updated: 2026-05-26`（同日不变）
3. 在文件末尾追加 `## Execution log by codex · 2026-05-26` 段，按下方"完成后报告格式"填写
4. Commit：

```bash
git add wiki-design/tasks/TASK-002-apply-rfc-002.md
git commit -m "[task] TASK-002 done by codex"
```

## 完成后报告格式

把以下内容贴进 `## Execution log by codex · 2026-05-26` 段：

```markdown
## Execution log by codex · 2026-05-26

### 步骤完成情况
- Step 0 Spec review: 通过 / 需修改: <reason>
- Step 1 01-architecture: done / partial / failed: <reason>
  - 1a 派生数据加 id_index.json: done
  - 1b frontmatter YAML 示例替换: done
  - 1c 字段表替换: done
  - 1d 三个新子节插入: done
- Step 2 05-contracts: done / partial / failed
  - 2a 目标文件关系加 id_index.json: done
  - 2b frontmatter YAML 替换: done
  - 2c 字段表替换: done
  - 2d review_queue 例子和约束: done
  - 2e source_manifest 例子和约束: done
  - 2f 六个页面模板 frontmatter 更新: done
  - 2g 答案引用格式段前置说明: done
- Step 3 .gitignore: done
- Step 4 验证: 输出见下

### 验证输出
\`\`\`
<Step 4 全部 grep / git diff 输出>
\`\`\`

### Commit
- Step 5 commit sha: <sha>
- Step 6 commit sha: <commit 后填入或写"本 commit">

### 偏离 / 异常
<列出与指令不一致的地方；没有就写"无"。>
```

## Spec review by codex · 2026-05-26

### 完整性
- [x] Decision 8 条基本覆盖：稳定 ID、source 单主键、`source_ids` / `related_ids`、`id_index.json`、拆分/合并语义、冲突短序号、canonical 边界都已映射到 01 / 05 / .gitignore。
- [x] 新内容基本仅来自 RFC-002：未混入 RFC-003 的 `inb_`、capture policy，也未混入 RFC-004 的 aliases / canonical_id / redirect。
- [ ] 边界仍需修正：强约束 1 和 3 写成“只动 3 个文件 / 不动任何 TASK 文件”，但 Step 0 和 Step 6 都要求修改本 task 文件。这会让 executor 在执行时天然违反 spec。建议改成“Step 1~5 正本改动只动 3 个文件；Step 0 / Step 6 允许修改本 task 文件，且只允许修改本 task 文件”。

### 可执行性
- [x] Step 1 / Step 2 的大部分 anchor 明确，当前 01 / 05 中对应段落都存在。
- [x] Step 3 的 `.gitignore` anchor 存在，追加 `knowledge/.wiki/id_index.json` 可执行。
- [ ] Step 2e 的 `summary_page_id` 规则存在语义冲突：它同时说“必须 === `source_id`”和“未生成摘要页时为 `null`”。建议改为“生成 source 摘要页后，`summary_page_id == source_id == source 页 frontmatter id`；尚未生成时为 `null`”。
- [ ] Step 2d 文案说“替换为以下两行”，但代码块实际是三行（`affected_page_ids`、`evidence[].page_id`、`evidence[].page_path`）。建议改成“三行”，避免执行者误删。
- [ ] Step 4 的负向 grep 验证不够机械：`grep "affected_pages"` 和 `grep '"summary_page":'` 预期 0 行时会返回 exit 1。若后续用 `set -e` 或脚本串行执行会中断。建议改成 `! grep ...`，或明确“允许 exit 1 且无输出即通过”。

### 风险
- `summary_page_path` 是新增显示层字段，方向合理，但需要在 Source Manifest 字段约束表里明确它只是可读 path，不是 canonical，否则后续 Agent 可能重新把 path 当主键。
- `source_id` 行追加“必须等于对应 source 摘要页 frontmatter `id`”时，要覆盖“摘要页尚未生成”的空状态，否则会和 `summary_page_id: null` 场景冲突。
- Step 4 第 5 条写“`affected_pages` grep 应 0 行（或仅历史/讨论中提及）”，但目标文件是 05 正本，最好改成严格 0 行；历史/讨论应该只存在 RFC / task，不应留在 05 的 schema 正本里。

### 结论
- 需修改。建议 Claude 先修正上述 4 个阻塞点（task 文件修改例外、`summary_page_id` null 语义、2d 两行/三行文案、负向 grep 验证方式），再进入下一轮 Step 0 review。

## Execution log by codex · YYYY-MM-DD

（待执行者在 Step 6 填写）

## Evaluation by claude · YYYY-MM-DD

（待评估者填写）

## Spec review v2 by codex · 2026-05-26

### v1 阻塞点复核
- [x] task 文件修改例外：已解决。强约束 3 明确 `TASK-002` 本身可在 Step 0 / 6 / 7 编辑，并限定只允许追加 Spec review、推进 status、追加 Execution log，不动原 Proposal 和其它 agent review。虽然强约束 1 仍写“只动 3 个文件”，但强约束 3 的专门例外足以消除执行歧义。
- [x] `summary_page_id` null 语义：已解决。Step 2e 已改为“未生成摘要页时为 `null`；已生成时必须等于 `source_id`”，并补充 `source_id` 在未生成摘要页时仍作为 source_manifest 稳定标识。
- [x] Step 2d 两行 / 三行文案：已解决。v2 拆成两步：替换 `affected_pages` 一行，以及新增两行 `evidence` 说明，不再存在“两行但给三行”的歧义。
- [x] 负向 grep 验证：已解决。Step 4 改成 `set +e` + `grep -c` 计数，并用精确字段匹配 `\"affected_pages\":` / `\"summary_page\":`，可以机械执行且不会因 0 命中中断。

### 完整性
- [x] RFC-002 Decision 8 条仍然全部覆盖。
- [x] 未混入 RFC-003 / RFC-004 的概念或字段。
- [x] Step 1~5 的正本改动边界和 Step 0 / 6 / 7 的 task 文件例外已经清楚。

### 可执行性
- [x] 01 / 05 / .gitignore 的 anchors 明确。
- [x] 验证脚本可以机械运行，并能区分旧字段残留与新字段命中。
- [x] commit 边界清楚：正本改动和 task 状态推进分开提交。

### 风险
- apply 时仍需注意只替换指定 schema / template 块，保留 01 / 05 中不被 RFC-002 覆盖的章节。
- Step 4 第 5 / 6 条现在按精确 JSON 字段检查旧字段；如果正文说明里出现旧字段名但不是 JSON 字段，不会被计入失败。这符合 v2 的机械验证设计。

### 结论
- 通过。可以进入 Step 1~7。

## Execution log by codex · 2026-05-26

### 步骤完成情况
- Step 0 Spec review: 通过
- Step 1 01-architecture: done
  - 1a 派生数据加 id_index.json: done
  - 1b frontmatter YAML 示例替换: done
  - 1c 字段表替换: done
  - 1d 三个新子节插入: done
- Step 2 05-contracts: done
  - 2a 目标文件关系加 id_index.json: done
  - 2b frontmatter YAML 替换: done
  - 2c 字段表替换: done
  - 2d review_queue 例子和约束: done
  - 2e source_manifest 例子和约束: done
  - 2f 六个页面模板 frontmatter 更新: done
  - 2g 答案引用格式段前置说明: done
- Step 3 .gitignore: done
- Step 4 验证: 输出见下

### 验证输出
```
=== 1. .gitignore 包含 id_index.json（应 ≥ 1）===
命中: 1
=== 2. 01-architecture.md 含三个新子节（应 = 3）===
命中: 3
=== 3. 01 中 prefix 表 8 个类型行（应 ≥ 8）===
命中: 16
=== 4. 05 中页面模板 frontmatter id 字段（应 ≥ 6）===
命中: 6
=== 5. affected_pages → affected_page_ids ===
  旧字段 '"affected_pages":' 命中（应 = 0）: 0
  新字段 'affected_page_ids' 命中（应 ≥ 1）: 2
=== 6. summary_page → summary_page_id ===
  旧字段 '"summary_page":' 命中（应 = 0）: 0
  新字段 'summary_page_id' 命中（应 ≥ 1）: 3
=== 7. 白名单外的文件不应被动（应输出空 stat / 无文件列表）===
  (no other task files modified)
=== 8. knowledge/ 不应存在 ===
OK: knowledge/ absent
```

### Commit
- Step 5 commit sha: a7938820763101e841f532e86a7f9ffbb00c08ad
- Step 6 commit sha: 本 commit；实际 sha 由提交后最终回复报告

### 偏离 / 异常
无。
