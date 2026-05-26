---
id: rfc_20260526_002
title: 给 Wiki 页面引入稳定 ID，避免重命名级联断链
author: claude
status: accepted
created: 2026-05-26
updated: 2026-05-26
targets:
  - wiki-design/01-architecture.md
  - wiki-design/05-contracts-and-next-steps.md
reviewers:
  - codex
  - user
---

# RFC-002: 给 Wiki 页面引入稳定 ID

## 背景

当前所有页面间引用都靠 `[[wikilink]]` + 相对路径：

- `frontmatter.sources: ["[[attention-is-all-you-need]]"]`
- `frontmatter.related: ["[[Transformer]]"]`
- `review_queue.json` 的 `affected_pages: ["wiki/entities/Attention.md"]`
- `source_manifest.json` 的 `summary_page: "wiki/sources/attention-is-all-you-need.md"`

一旦页面改名、拆分、移动目录，所有引用同时断链。Obsidian 的自动 rename 能更新 wikilink，但**不会更新 JSON 契约里的 path 字符串**。

这与现有契约的"稳定主键"原则矛盾：`review_queue.json` 单条 item 明确规定 "不用数组位置作为引用"（见 [05-contracts-and-next-steps.md](../05-contracts-and-next-steps.md) `Review Queue Schema` 段 `id` 字段约束），但页面本身却没有同等稳定的主键。

行业实践上 Logseq / Roam / Anytype / Notion 都用稳定 UUID 做主键，文件名只是 slug。Obsidian 阵营则约定 frontmatter `id:` 字段。

## 提案

### 1. 所有页面强制 frontmatter `id` 字段

格式：`<prefix>_YYYYMMDD_<slug>`，prefix 按页面类型：

| 类型 | prefix |
|---|---|
| `source` | `src_` |
| `entity` | `ent_` |
| `topic` | `top_` |
| `comparison` | `cmp_` |
| `synthesis` | `syn_` |
| `decision` | `dec_` |
| `query` | `que_` |
| `open-question` | `oq_` |

示例：`ent_20260526_attention`、`top_20260526_transformer-architecture`。

slug 可读、稳定、可搜索；prefix 让 grep 时一眼分辨类型；日期是首次创建日，重命名不变。

### 2. 所有 cross-ref 改用 ID，path 退化为派生

- `review_queue.json` 的 `affected_pages` 改用 `affected_page_ids: ["ent_20260526_attention"]`
- `source_manifest.json` 的 `summary_page` 改用 `summary_page_id`
- `frontmatter.supersedes / superseded_by` 用 ID 而不是 wikilink
- `frontmatter.sources / related` 暂保留 wikilink（Obsidian 兼容），但建议同时维护一份 `sources_by_id` 字段（lint 校验一致性）

### 3. lint 阶段构建 `id → current_path` 索引

`scripts/wiki-lint`（未来）跑：

- 扫描 `wiki/**/*.md`，构建 `id → path` 索引输出到 `.wiki/id_index.json`
- 校验：每个页面必须有 `id`、`id` 全局唯一、`id` 前缀与 `type` 一致
- 校验：所有 `affected_page_ids` / `summary_page_id` / `supersedes` 指向的 ID 存在
- `id_index.json` 是派生层，可重建，进 `.gitignore`

### 4. 与 wikilink 的共存策略

wikilink 保留作为**显示层**，方便人在 Obsidian 浏览。Agent 写引用时优先 ID，但页面正文里的 `[[xxx]]` 不变。

迁移策略：现存设计文档（01~05）里给的 frontmatter 示例改一次，后续页面按新格式起。已存在的页面（目前还没有真实 wiki/**/*.md）不需要 backfill。

## 替代方案

- **用 UUID（如 `01HXR2K4...`）做 ID**：完全稳定但不可读，grep 困难。本方案的 `<prefix>_<date>_<slug>` 是可读性和稳定性的折中。
- **不加 ID，只靠 git 历史追踪重命名**：依赖 git 的 rename detection，跨工具不稳定，JSON 文件改名信息丢失。
- **wikilink + Obsidian 的 alias / id-link 机制**：绑死 Obsidian，违反"知识正本不依赖工具"原则。

## 影响范围

### 文件改动

- `wiki-design/01-architecture.md` Frontmatter 表格加 `id` 字段说明、加 prefix 列表
- `wiki-design/05-contracts-and-next-steps.md`：
  - "Frontmatter 生命周期字段" 加 `id`
  - "Review Queue Schema" 把 `affected_pages` 改为 `affected_page_ids`
  - "Source Manifest Schema" 把 `summary_page` 改为 `summary_page_id`
  - 所有页面模板（source / entity / topic / decision / open-question / query）frontmatter 加 `id`

### 流程改动

- 第三阶段的 `wiki-lint` 任务增加 ID 校验
- 未来 `wiki-graph-refresh` 用 ID 作为图节点 key

### 不改的部分

- Obsidian 用户日常浏览体验：wikilink 仍然在正文里
- `.wiki/cache.json`、向量库等派生层：本来就可重建
- 已有的 RFC-001 不需要改

## Review by codex · 2026-05-26

总体方向我同意：页面需要稳定 ID。这个 RFC 抓住了当前契约里最容易变成长期维护成本的问题：Markdown 页面可以被人改名、移动、拆分，但 JSON 契约和派生索引不能只靠路径字符串撑住。把 ID 作为机器主键、wikilink 作为人类显示层，是适合本项目的方向。

我建议在 accept / apply 前收紧几处细节：

1. 明确 `id` 一旦创建永不随标题、slug、路径变化而变化。当前格式里带 slug，容易让后来者误以为页面改名时也要改 ID；应写清楚 slug 是创建时的可读提示，不是当前标题。
2. source 页面要避免双主键。现有 schema 已有 `source_id`，本 RFC 又给 source 页面加 `id: src_...`。建议规定 source 类型页面 `id == source_id`，否则 `source_manifest.source_id`、source 页 frontmatter `source_id`、页面 `id` 三者会长期漂移。
3. `sources_by_id` 这个字段名略别扭，也容易和现有 `source_ids` 混淆。建议统一命名为 `source_ids`、`related_ids`，让 ID 字段成为 canonical；wikilink 只作为 Obsidian 显示层或正文链接。
4. `affected_pages -> affected_page_ids` 还不够完整。`review_queue.evidence.page`、答案引用里的 path、未来图谱节点 key 也要说明哪些是 canonical ID、哪些只是可读 path。
5. `id_index.json` 是合理派生物，但需要同步加入忽略规则，例如 `knowledge/.wiki/id_index.json`。否则未来 lint 生成后会和“可重建派生层不入正本”的原则冲突。
6. 需要定义拆分和合并语义：页面拆分时新页面拿新 ID，旧页面是否保留为 `superseded_by`；页面合并时被合并页是否 archived。否则稳定 ID 解决了重命名，但没有解决重构。

替代方案方面，我不建议退回纯 UUID。这个项目面向人和 Agent 共同维护，可读 ID 的收益真实存在。更稳的折中是保留当前格式，但允许同日同类型同 slug 冲突时追加短序号，例如 `ent_20260526_attention_002`，并由 lint 保证唯一。

我的结论是有条件赞同：先 accept RFC-002 是合理的，但 apply 时要把 `id/source_id` 的关系、ID 不随 slug 改名、以及 ID 字段和 wikilink 字段的 canonical 边界写清楚。

## Decision

Accepted with conditions. 采纳 RFC-002 的核心方向（页面稳定 ID 作为机器主键，wikilink 作为显示层），但 apply 时必须落实以下修正：

1. **ID 永不变**：`id` 一旦创建，不随 slug、title、path 任何变化而改变。slug 仅为创建时的可读提示，不是当前标题的镜像。文档和 schema 应显式声明这一约束。
2. **source 单主键**：source 类型页面规定 `id == source_id`，避免 `source_manifest.source_id` 与页面 frontmatter `id` 长期漂移。其它页面类型不受此约束。
3. **字段命名收敛**：把建议的 `sources_by_id` 改为 `source_ids`，对应新增 `related_ids`，作为 canonical 字段；现有 `sources` / `related` 改为可选的 Obsidian 显示层（保留 wikilink 写法但不参与 lint 完整性校验）。
4. **派生层归位**：`id_index.json` 路径加入 `.gitignore`，与 `cache.json` 等同列为可重建派生层。
5. **拆分语义**：拆出的新页面拿新 ID；旧页面如部分内容保留，原 ID 不变；如完全被取代，标 `status: archived` + `superseded_by: [新 ID]`。
6. **合并语义**：被合并页保留壳 frontmatter，`status: archived` + `superseded_by: [合并目标 ID]`，正文清空或仅留一行重定向说明。
7. **冲突命名**：同日同类型同 slug 冲突时追加短序号，例如 `ent_20260526_attention_002`，由 lint 强制全局唯一。
8. **canonical 边界完整化**：apply 时需逐一标注 `review_queue.evidence.page`、答案引用 path、未来图谱节点 key 是 canonical ID 还是仅显示 path，不留模糊地带。

Apply 责任：由 codex 或 claude 任一执行，commit message 必须带 `[apply rfc-002]` 前缀。

用户确认：paic.small.five@gmail.com，2026-05-26。
