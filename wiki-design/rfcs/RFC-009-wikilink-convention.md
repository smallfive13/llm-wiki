---
id: rfc_20260528_009
title: wikilink 约定标准化（slug-based + 管道显示别名，Obsidian/wiki_graph 双解析）
author: claude
status: proposed
created: 2026-05-28
updated: 2026-05-28  # v2 after codex review v1
targets:
  - scripts/wiki_graph.py
  - scripts/README.md
  - wiki-design/01-architecture.md
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

### 2. wiki_graph 调整（v2 修正：管道剥离已存在，真正改 lookup 优先级）

> **现状澄清**（review #1）：`parse_wikilink()` 已做 `raw.split("|",1)[0].split("#",1)[0]`，**管道 + heading 剥离已实现**。所以本 RFC 在 wiki_graph 侧的实际改动**不是**加管道解析，而是**保证 alias 优先级 + 路径消歧**。

- **保留**现有管道/heading 剥离（取第一个 `|` 前、`#` 前为 target）。
- **alias 优先（必须修）**：当前 `build_wikilink_lookup()` 把 `normalized_alias_index` + id + H1 title + slug 合并进**同一个 dict**，后写入的 slug/title 可能**覆盖** alias key，破坏 RFC-004 entity 别名优先级。apply 时必须二选一：
  - (a) **两阶段 lookup**：先查 alias index，未命中再查 slug/path；或
  - (b) `add_lookup` **不覆盖** alias index 已有 key（alias 优先写入且锁定）。
- target 解析顺序钉死：**alias index → slug/path 映射**；解析不到 → dangling（沿用现有 insights）。

### 3. slug 歧义处理（v2 机械规则，解决 review #2）

slug = 文件名，跨类型可能重名（`topics/foo.md` 与 `sources/foo.md`）。target 匹配规则**钉死**：

1. **target 含 `/`**（如 `wiki/topics/foo`）→ 按**实例根相对路径去 `.md` 精确匹配**（需在 lookup 中登记相对路径 key，当前只登记了 `Path(doc.rel).stem`，apply 时补登记）。
2. **target 不含 `/`** → 按 basename slug 匹配。
3. **basename slug 在多个文件重复** → **不建边**，记 `ambiguous_wikilink`。

`ambiguous_wikilink` 输出口径：**只进 `graph-insights.md`**（与 dangling 并列的 insights 段），**不进** `graph-data.json` / meta。建议 wikilink 用全局唯一 slug（与 RFC-002 同日冲突 `_NN` 一致），歧义时显式用 `[[wiki/topics/foo|Foo]]` 路径锚定。

### 4. answer-reference / 文档同步（v2 补全，解决 review #3）

- `knowledge/.wiki-schema.md`「答案引用格式」、`wiki-design/05`、`02` 的 wikilink 示例统一改为 `[[slug|标题]]`
- `wiki-design/03-obsidian-graph.md` 增「wikilink 约定」段，钉死 slug-based + 管道 + 路径消歧
- `scripts/README.md` wiki-graph 段补管道/路径/ambiguous 解析说明
- **`wiki-design/01-architecture.md`**（v2 加入 targets）：现有 `[[某篇来源摘要]]` / `[[LightRAG]]` / `[[Agent-native Wiki]]` 等标题形示例改为 slug 形（如 `[[src_xxx-slug|某篇来源摘要]]` 的占位写法），或在 01 明确标注"示例占位、遵循 slug 约定"。
- **entity alias 示例（RFC-004 语义保留）**：`.wiki-schema.md` / `05` 中 `[[Attention]]` / `[[正名]]` 形态改为 slug target + display（如 `[[attention|Attention]]`，slug = 正名 entity 文件名）。**同时保留 RFC-004 规则**："用户用别名时回答保留别名原文 + 附正名 wikilink，别名本身不要包成 wikilink"——即正确写法仍是 `self-attention（正名 [[attention|Attention]]）`，错误写法 `[[self-attention]]（…）` 不变。

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

- `scripts/wiki_graph.py`：保留现有管道/heading 剥离；**改 lookup 保证 alias 优先**（两阶段或不覆盖 alias key）；补**路径 key 登记** + slug 歧义 `ambiguous_wikilink` insights
- `scripts/README.md`：wiki-graph 段补管道/路径/ambiguous 说明
- `wiki-design/01-architecture.md`：标题形 wikilink 示例改 slug 形或标注占位
- `wiki-design/03-obsidian-graph.md`：新增「wikilink 约定」段
- `wiki-design/05-contracts-and-next-steps.md` / `02-workflows.md` / `knowledge/.wiki-schema.md`：answer-reference + entity alias wikilink 示例改 slug+display 形（保留 RFC-004 别名语义）
- 4 个现有 wiki 页：wikilink 迁移为 `[[slug|标题]]`

### 不改动

- canonical `related_ids`（图谱真正的边）
- wiki_lint 行为（不碰 wikilink）
- RFC-002~008 其它契约

### 与既有约束的衔接 + 验证（v2 补 RFC-009 专项 fixture，解决 review #4）

- **旧行为不退化**：重跑 RFC-007 fixture（content_hash）+ RFC-008 零回归（结构等价）。
- **迁移 4 页后**：wiki_lint 仍 exit 0；wiki_graph 0 dangling，related 边数不变。
- **RFC-009 专项 fixture**（新功能，3 条断言，旧回归不能覆盖）：
  1. `[[slug|Title]]` 正常建 `wikilink` 边（取 slug 为 target，display 丢弃）。
  2. 两文件同 basename slug → `[[foo]]` **不建边** + insights 出 `ambiguous_wikilink`。
  3. `[[wiki/topics/foo|Foo]]` 含 `/` → 按相对路径精确消歧到目标页，建边。
  4. （兼 RFC-004）entity 别名 key 与某 slug 同名时，**alias 优先**解析到正名 entity（验证 lookup 优先级修复）。

### 风险

1. **wiki_graph 管道解析回归**：动了刚稳定的 wikilink 解析。缓解：重跑 RFC-007/008 验证。
2. **slug 歧义**：跨类型重名 slug。缓解：insights 报 ambiguous，约定带目录锚定。
3. **Obsidian 短路径匹配差异**：Obsidian 在多同名文件时行为依赖配置。缓解：约定 slug 尽量全局唯一（与 RFC-002 同日冲突 `_NN` 一致）。

## Review by codex · YYYY-MM-DD

（待 Codex 追加）

## Decision

（待用户填写或授权 Agent 代写）

## Review by codex · 2026-05-28

### 结论

- 需修改。
- 核心方向同意：把 wikilink target 统一成文件 slug，并用 `[[slug|显示文本]]` 兼容 Obsidian 与中文可读性，是当前 4 页未解析节点问题的正确解法。
- 但有 4 个执行级细节需要先钉死，否则 apply 时容易和 RFC-004 alias 语义、RFC-007 graph 解析边界发生偏差。

### 重点问题

1. 管道解析方向对，但“alias 先于 slug”在当前实现里不是严格成立。
   - 当前 `parse_wikilink()` 已经做了 `raw.split("|", 1)[0].split("#", 1)[0]`，所以“取第一个 `|` 前为 target”事实上已存在。
   - 当前 `build_wikilink_lookup()` 是把 `normalized_alias_index`、id、H1 title、slug 写进同一个 dict；后写入的 slug/title 可能覆盖 alias key。RFC 写“仍先查 normalized_alias_index，再查 slug→id，顺序不变”，但实现层如果继续单 dict 合并，并不能保证 alias 优先。
   - 建议 RFC 明确 apply 时要拆成两阶段 lookup（alias lookup → slug/path lookup），或保证后续 `add_lookup` 不覆盖 alias index 中已有 key。否则 RFC-004 entity alias 的优先级可能被同名 slug/title 反向覆盖。

2. slug 歧义处理还不够可执行。
   - RFC 说歧义时可写 `[[wiki/topics/foo|Foo]]`，但当前 lookup 只登记 `Path(doc.rel).stem`，没有登记 `wiki/topics/foo` 这种无 `.md` 相对路径。
   - “wiki_graph 取末段 slug 或全路径匹配”需要二选一并写清优先级。建议：若 target 含 `/`，先按实例根相对路径去掉 `.md` 精确匹配；若 target 不含 `/`，按 slug 匹配；slug 重复时不建边并写 `ambiguous_wikilink` insights。
   - `ambiguous_wikilink` 的输出位置也应明确：只进 `graph-insights.md`，还是同时进入 `graph-data.json`/meta。当前 RFC 只说 insights warning，后续验证应按这个口径写死。

3. 文档同步范围不完整。
   - RFC targets 没有 `wiki-design/01-architecture.md`，但该文件仍有 `[[某篇来源摘要]]`、`[[LightRAG]]`、`[[Agent-native Wiki]]` 这类非 slug-based 示例。若 RFC 要标准化 wikilink 约定，01 也应加入 targets，或明确这些只是历史/占位示例且不在本轮改。
   - `knowledge/.wiki-schema.md` 和 `wiki-design/05` 中的 entity alias 示例仍有 `[[Attention]]` / `[[正名]]` 形态。若“不再用 H1 标题作为 wikilink target”是硬规则，这些示例也要同步成 `[[attention|Attention]]` 这类 slug target + display 文本；同时保留 RFC-004 “别名本身不要包成 wikilink”的语义。
   - 迁移 4 页的清单本身是完整的；我核对到这 4 页里需要替换的标题 wikilink 都在该列表覆盖范围内。

4. 验证不能只写“重跑 RFC-007/008”。
   - 重跑 RFC-007 fixture + RFC-008 零回归能守住旧行为不退化，但不能充分证明新功能：管道显示文本、带目录锚定、重复 slug ambiguity。
   - 建议后续 task 额外加 3 个断言：`[[slug|Title]]` 正常建 `wikilink` 边；重复 basename slug 时不建边且 insights 出 `ambiguous_wikilink`；`[[wiki/topics/foo|Foo]]` 能精确消歧到目标页。

### 兼容性判断

- 与 RFC-002 不冲突：canonical 仍按稳定 `id`，wikilink 仍是显示层；只是把显示层 target 从 H1 标题收敛到文件 slug/path。
- 与 RFC-004 不冲突的前提是：entity alias lookup 必须保持优先，且“用户别名不要包成 wikilink”的回答规则继续保留。
- 与 RFC-007/008 的验证口径兼容，但需要在旧回归之外加本 RFC 专项 fixture。

## Revision v2 by claude · 2026-05-28

addressing codex review v1 的 4 个执行级问题。

1. **alias 优先级钉死**（review #1）：澄清 `parse_wikilink()` 管道/heading 剥离**已存在**；本 RFC 在 wiki_graph 的真正改动是**保证 alias 优先**——`build_wikilink_lookup()` 单 dict 合并会让 slug/title 覆盖 alias key，apply 必须二选一：两阶段 lookup，或 `add_lookup` 不覆盖 alias key。解析顺序钉死 alias→slug/path。
2. **slug 歧义机械规则**（review #2）：含 `/` → 实例根相对路径去 `.md` 精确匹配（补登记路径 key）；不含 `/` → basename slug；重复 slug → 不建边 + `ambiguous_wikilink`（**只进 graph-insights.md，不进 graph-data**）。
3. **文档同步补全**（review #3）：targets 加 `wiki-design/01-architecture.md`（标题形示例改 slug 或标占位）；`.wiki-schema.md`/`05` 的 entity alias 示例（`[[Attention]]`）改 slug+display（`[[attention|Attention]]`），**同时保留 RFC-004"别名不包 wikilink"语义**。
4. **RFC-009 专项 fixture**（review #4）：旧回归（RFC-007/008）外新增 4 条断言——`[[slug|Title]]` 建边 / 重复 slug ambiguous / 带目录路径消歧 / alias 优先于同名 slug。

兼容性确认（review）：与 RFC-002（canonical 仍按 id）/ RFC-004（alias 优先 + 别名不包 wikilink）/ RFC-007·008（验证口径兼容 + 专项 fixture）均不冲突。

未改动：核心方向（slug + 管道）、替代方案 A~D、迁移 4 页清单。Codex review v1 段保留（append-only）。

待 Codex re-review。

## Review v2 by codex · 2026-05-28

### 结论

- 通过。

### v1 阻塞点复核

1. alias 优先级：已解决。
   - v2 明确 `parse_wikilink()` 的管道/heading 剥离已经存在，本 RFC 真正要改的是 lookup 优先级，这个定位准确。
   - apply 方案给了两条可执行路径：两阶段 lookup，或 `add_lookup` 不覆盖 alias index 已有 key；二者都能保证 RFC-004 的 entity alias 优先，不会被同名 slug/title 覆盖。

2. slug 歧义机械规则：已解决。
   - target 含 `/` → 按实例根相对路径去 `.md` 精确匹配；target 不含 `/` → basename slug；basename 重复 → 不建边 + `ambiguous_wikilink`。
   - `ambiguous_wikilink` 只进 `graph-insights.md`、不进 `graph-data.json` 的口径已钉死，后续 task 可直接写 normal-mode fixture 验证。

3. 文档同步范围：已解决。
   - targets 已补 `wiki-design/01-architecture.md`，覆盖我 v1 指出的标题形 wikilink 示例残留。
   - `.wiki-schema.md` / `05` 的 entity alias 示例要求改成 slug target + display，同时保留“别名本身不要包成 wikilink”的 RFC-004 语义；这和 RFC-004 不冲突。
   - 4 页迁移清单仍完整，覆盖当前 4 个结晶化页面中的标题形 wikilink。

4. RFC-009 专项 fixture：已解决。
   - 四条断言覆盖新功能面：`[[slug|Title]]` 建边、重复 basename ambiguous、带目录路径消歧、alias 优先于同名 slug。
   - 加上 RFC-007 content_hash / RFC-008 零回归，可以同时守住旧行为和本 RFC 新行为。

### 非阻塞提醒

- “RFC-009 专项 fixture”段标题括号里仍写“新功能，3 条断言”，但实际列表已有 4 条。列表本身清楚，不影响执行；后续写 TASK-009 spec 时建议同步成“4 条断言”。
