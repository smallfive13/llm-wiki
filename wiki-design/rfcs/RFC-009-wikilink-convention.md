---
id: rfc_20260528_009
title: wikilink 约定标准化（slug-based + 管道显示别名，Obsidian/wiki_graph 双解析）
author: claude
status: proposed
created: 2026-05-28
updated: 2026-05-28
targets:
  - scripts/wiki_graph.py
  - scripts/README.md
  - wiki-design/03-obsidian-graph.md
  - wiki-design/05-contracts-and-next-steps.md
  - wiki-design/02-workflows.md
  - knowledge/.wiki-schema.md
  - knowledge/wiki/synthesis/llm-wiki-architecture.md
  - knowledge/wiki/topics/rfc-task-protocol.md
  - knowledge/wiki/topics/wiki-schema-rules.md
  - knowledge/wiki/topics/toolchain-usage.md
reviewers:
  - codex
  - user
---

# RFC-009: wikilink 约定标准化（slug-based + 管道显示别名）

## 背景

首次结晶化（4 页自身设计）在 Obsidian 中暴露问题：wikilink 用了 H1 **标题**（`[[RFC + Task 协作协议]]`），但 Obsidian 按**文件名**解析（文件实际叫 `rfc-task-protocol.md`），对不上 → 点击未解析链接时 Obsidian 在 vault 根创建空桩文件，原生图谱显示"未解析节点"。

两套解析方式不一致：

| 工具 | wikilink 解析方式 | 现状 |
| --- | --- | --- |
| `wiki_graph` | 按 `title/slug → id` 内存映射 | 标题 wikilink 能解析（16 边正常） |
| Obsidian | 按**文件名**（slug） | 标题 wikilink 解析不到 → 建空桩 |

canonical 的 `related_ids` 不受影响（图谱真正的边来自它），wikilink 只是显示层便利。但既然 Obsidian 是主要人读浏览工具，wikilink 必须在 Obsidian 里也解析。

## 提案

统一 wikilink 标准形式为 **slug-based + 可选管道显示别名**，并让 `wiki_graph` 解析管道。

### 1. 标准 wikilink 形式

```
[[<slug>|<显示文本>]]      推荐：文件名锚定 + 中文显示
[[<slug>]]                 可接受：无显示别名
```

- `<slug>` = 目标页**文件名**（不含 `.md`、不含目录），如 `rfc-task-protocol`
- `<显示文本>` = 给人看的可读文字（可选），如 `RFC + Task 协作协议`
- **不再用 H1 标题作为 wikilink target**

双解析：

- **Obsidian**：按 `<slug>` 文件名解析（命中 `rfc-task-protocol.md`），渲染显示 `<显示文本>`
- **wiki_graph**：取 `|` 前的 `<slug>` 为 target，经现有 `slug → id` 映射解析为节点

### 2. wiki_graph 增强（管道解析）

- wikilink 正则捕获后，若含 `|`：**取第一个 `|` 前的部分**为 target slug，`|` 后为 display（丢弃，不影响图）
- target slug 经现有内存 `slug → id`（归一化）解析；解析不到 → dangling（沿用现有 insights）
- 仍先查 `normalized_alias_index`（entity 别名），再查 slug→id —— 顺序不变，只在"取 target"前先剥离 `|display`

### 3. slug 歧义处理

- slug = 文件名，跨类型理论上可能重名（`topics/foo.md` 与 `sources/foo.md`）
- **约定**：歧义时 wikilink 用带目录的形式 `[[wiki/topics/foo|Foo]]`（Obsidian 支持路径锚定；wiki_graph 取末段 slug 或全路径匹配）
- MVP：slug→id 映射遇重复 slug 时，记 `ambiguous_wikilink`（进 insights warning），不武断建边

### 4. answer-reference / 文档同步

- `knowledge/.wiki-schema.md`「答案引用格式」、`wiki-design/05`、`02` 的 wikilink 示例统一改为 `[[slug|标题]]`
- `wiki-design/03-obsidian-graph.md` 增「wikilink 约定」段，钉死 slug-based + 管道
- `scripts/README.md` wiki-graph 段补管道解析说明

### 5. 迁移现有 4 页

把首次结晶化的 4 页 wikilink 从标题形式改为 `[[slug|标题]]`：

- `[[RFC + Task 协作协议]]` → `[[rfc-task-protocol|RFC + Task 协作协议]]`
- `[[知识库 Schema 与页面规则]]` → `[[wiki-schema-rules|知识库 Schema 与页面规则]]`
- `[[工具链与使用说明]]` → `[[toolchain-usage|工具链与使用说明]]`
- `[[llm-wiki 系统架构]]` → `[[llm-wiki-architecture|llm-wiki 系统架构]]`

（frontmatter 的 `related:` 显示层字段同步；canonical `related_ids` 不变。）

### 范围（MVP 不包含）

- lint 不校验 wikilink 解析（保持现状，dangling 由 wiki_graph insights 报）
- 不改 canonical `related_ids` 机制（wikilink 仍是显示层）
- 不做历史批量迁移工具（只有 4 页，手改）
- 不引入 `[[id]]` 形式（Obsidian 按文件名解析，id≠文件名，不可行）
- block/heading 锚（`[[slug#heading]]`）暂不纳入

## 替代方案

| 方案 | 评价 |
| --- | --- |
| **A. slug + 管道显示别名（本 RFC）** | Obsidian 文件名解析 + 中文显示；wiki_graph 取管道前；两边通、可读 |
| B. 纯 `[[slug]]` | 零代码但 raw markdown 显示 slug，中文场景可读性差 |
| C. 文件名改成标题 | 破坏 RFC-002 稳定 slug；中文/特殊字符文件名跨平台风险 |
| D. Obsidian `aliases` frontmatter | `aliases` 是 RFC-004 entity 专用字段，topic 用语义冲突 |

## 影响范围

### 改动正本 / 代码

- `scripts/wiki_graph.py`：wikilink 解析加管道剥离（取 `|` 前）+ slug 歧义 insights
- `scripts/README.md`：wiki-graph 段补管道说明
- `wiki-design/03-obsidian-graph.md`：新增「wikilink 约定」段
- `wiki-design/05-contracts-and-next-steps.md` / `02-workflows.md` / `knowledge/.wiki-schema.md`：answer-reference wikilink 示例改管道形式
- 4 个现有 wiki 页：wikilink 迁移为 `[[slug|标题]]`

### 不改动

- canonical `related_ids`（图谱真正的边）
- wiki_lint 行为（不碰 wikilink）
- RFC-002~008 其它契约

### 与既有约束的衔接

- wiki_graph 改动后需重跑 RFC-007 fixture（content_hash）+ RFC-008 零回归（结构等价），确认管道解析不破坏既有边投影。
- 迁移 4 页后重跑 wiki_lint（应仍 exit 0）+ wiki_graph（边数应不变或更准，0 dangling）。

### 风险

1. **wiki_graph 管道解析回归**：动了刚稳定的 wikilink 解析。缓解：重跑 RFC-007/008 验证。
2. **slug 歧义**：跨类型重名 slug。缓解：insights 报 ambiguous，约定带目录锚定。
3. **Obsidian 短路径匹配差异**：Obsidian 在多同名文件时行为依赖配置。缓解：约定 slug 尽量全局唯一（与 RFC-002 同日冲突 `_NN` 一致）。

## Review by codex · YYYY-MM-DD

（待 Codex 追加）

## Decision

（待用户填写或授权 Agent 代写）
