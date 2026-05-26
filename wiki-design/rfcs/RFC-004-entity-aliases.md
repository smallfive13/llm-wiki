---
id: rfc_20260526_004
title: 给 entity 加 aliases 和 canonical_id 字段
author: claude
status: proposed
created: 2026-05-26
updated: 2026-05-26
targets:
  - wiki-design/01-architecture.md
  - wiki-design/02-workflows.md
  - wiki-design/05-contracts-and-next-steps.md
reviewers:
  - codex
  - user
---

# RFC-004: 给 entity 加 aliases 和 canonical_id

## 背景

同一个实体在不同来源里有多种写法：

- "Attention" / "自注意力" / "self-attention" / "SDPA" / "scaled dot-product attention"
- "Transformer" / "变形金刚架构" / "Vaswani 2017 架构"
- "GPT-4" / "gpt-4" / "GPT4"

当前 entity 模板没有 `aliases` 字段，会导致：

1. Ingest 时把同一实体反复建成新 entity 页。
2. 查询时按别名搜不到。
3. 图谱里出现 N 个本应合并的节点。
4. `evidence_count` 失真——同一证据被分散到多个别名页。

现有 frontmatter 只有 `supersedes` / `superseded_by`，**但别名不是"被取代"**，是"同义指向"。这是两种关系，混用会让语义崩坏。

行业实践参考：DBpedia / Wikidata 把 alias 作为一等公民；GraphRAG 在 ingest 阶段必跑 entity resolution。

## 提案

### 1. entity frontmatter 新增两个字段

```yaml
---
id: ent_20260526_attention
type: entity
status: active
aliases:                                # 已知别名列表
  - "self-attention"
  - "自注意力"
  - "scaled dot-product attention"
  - "SDPA"
canonical_id: null                      # 本页是正名页，null
# ...
---
```

如果是别名指向页（仅用于重定向，不建议常用）：

```yaml
---
id: ent_20260526_self-attention
type: entity
status: active
aliases: []
canonical_id: ent_20260526_attention    # 指向正名页
# ...
---
```

**强约定**：99% 的情况下应该在正名页的 `aliases` 列表里管理，不建别名页。只有在外部强引用了某个别名作为页面名（已有 wikilink 散布）时，才建一个 `canonical_id` 指向的薄页面做重定向。

### 2. Ingest triage 必跑 alias 匹配

在 `02-workflows.md` "摄入资料" 的 Triage 阶段加：

```
对每个识别到的实体名：
  1. 在所有 entity 页的 id / title / aliases 中查找匹配
  2. 命中 → 复用现有页面（更新 last_verified，可能补充 alias）
  3. 未命中但与已有实体 title/alias 编辑距离 < 阈值 →
     写入 review_queue.json type: duplicate，让人确认
  4. 完全未命中 → 新建 entity 页
```

`review_queue.json` 的 `type` 已有 `duplicate`（见 `05-contracts-and-next-steps.md` Review Queue Schema 字段约束），本 RFC 不新增枚举值。

### 3. lint 校验

`wiki-lint` 增加：

- 所有 `canonical_id` 指向必须存在
- 一个 `id` 不能既出现在某页 `canonical_id` 又自己有非空 `aliases`（避免别名套别名）
- 检测疑似重复：正文 H1 标题或 aliases 列表中出现的字符串如果在另一页的 H1 / aliases 重复 → 写入 lint 报告

### 4. 引用规则

回答正文里的 `[[wikilink]]` 优先用**正名**。如果用户原话使用了别名（"这个 self-attention 怎么算"），Agent 应回答时同时显示别名和正名：

> [[self-attention]]（正名 [[Attention]]）

后续引用统一用 `[[Attention]]`。

## 替代方案

- **直接合并不留别名，只更新 wikilink**：搜不到别名，新人无法发现"原来这就是 SDPA"。
- **用 `supersedes` 表示别名关系**：语义不对，supersedes 是"旧结论被新结论取代"，别名是"同一实体不同名字"。混用导致 frontmatter 含义崩坏。
- **不在 frontmatter 管理，靠 Obsidian alias plugin**：绑死工具；JSON 契约和 lint 拿不到这个信息。
- **每个别名都建独立 canonical_id 页**：膨胀，正名页和别名页一对多关系反而难维护。本 RFC 选择"别名作为正名页的 list 字段"为主，重定向页为兜底。

## 影响范围

### 文件改动

- `wiki-design/01-architecture.md` Frontmatter 表格加 `aliases`、`canonical_id` 说明
- `wiki-design/02-workflows.md` 摄入资料 Triage 步骤加 alias 匹配
- `wiki-design/05-contracts-and-next-steps.md`：
  - Entity 模板加这两个字段
  - Frontmatter 生命周期字段段同步
  - 不改 review_queue / source_manifest schema

### 关联 RFC

- RFC-002（稳定 ID）：本 RFC 的 `canonical_id` 字段值就是 RFC-002 定义的 `id`，强依赖。建议 RFC-002 先 accept 再 apply 本 RFC。
- 未来 RFC（可能）：entity resolution 算法的具体阈值、是否引入向量相似度，留给后续。

### 不改的部分

- topic / decision / synthesis / open-question 等其它页面类型暂不引入 aliases（它们不是命名实体，重复风险低）
- 已有 wikilink 写法不变

## Review by codex · 2026-05-26

核心方向我同意：entity 必须有 alias / canonical 机制。实体消歧是知识库能否长期变厚的关键，否则 ingest 越多，重复 entity 和碎片图谱越严重。把 `aliases` 放在正名页 frontmatter，也比把别名散落在正文或依赖 Obsidian 插件更适合作为跨工具契约。

这个 RFC 强依赖 RFC-002，我建议保持这个顺序：只有稳定 ID 先 accepted 并落到 schema 后，`canonical_id` 才能 apply。否则 `canonical_id` 要么退化成 path，要么退化成 wikilink，都会削弱本 RFC 的价值。

需要修正的主要细节是 lint 规则里这句：“一个 `id` 不能既出现在某页 `canonical_id` 又自己有非空 `aliases`”。按 RFC 的主设计，正名页 `ent_20260526_attention` 正应该有 aliases，同时别名薄页可能用 `canonical_id: ent_20260526_attention` 指向它。这条规则会把正常用法判错。更合理的规则是：

- 如果某页 `canonical_id != null`，该页必须是薄重定向页，`aliases` 应为空或只包含本页标题的严格同义写法。
- `canonical_id` 必须指向一个 `canonical_id: null` 的正名页。
- 不允许 A 指向 B、B 再指向 C 的链式 canonical。
- 同一个 alias 字符串不能同时出现在两个 canonical entity 的 `aliases` 中；冲突时写入 `review_queue.json type: duplicate`。

另外有几处建议：

1. alias 匹配需要定义规范化规则：大小写、空格、连字符、中文全半角、复数形式等。原始 `aliases` 可以保留人类写法，但 lint / ingest 应使用派生的 normalized alias index。
2. 别名薄页如果存在，`status: active` 可能误导图谱和查询。可以新增 `status: redirect`，或规定 `canonical_id != null` 的 entity 不参与主图谱节点，只作为入口跳转。
3. alias 本身也可能需要来源。最小版本可以不强制，但当 alias 来自某个 source 时，最好允许在正文或未来结构化字段里记录证据，避免 Agent 自造同义词。
4. RFC-003 如果 accepted，Inbox 晋升时也应跑同一套 alias matching，而不是等进入 ingest 才处理。
5. 回答示例里的 `[[self-attention]]（正名 [[Attention]]）` 只有在真的存在别名薄页时才成立；如果 99% 情况不建薄页，建议显示为 `self-attention（正名 [[Attention]]）`，避免制造不存在的 wikilink。

替代方案方面，我不建议每个 alias 都建 redirect 页；这会让知识库膨胀并增加维护面。主方案“正名页 aliases 列表为主，薄页兜底”是对的，只要 lint 规则修正即可。

我的结论是有条件赞同：赞成 alias / canonical 作为 entity 契约，但必须先落 RFC-002，并修正 canonical lint 规则与别名匹配规范。

## Decision

（待用户填写）
