---
id: rfc_20260528_007
title: 自建 canonical wiki-graph（03 第二层增强图谱生成器）
author: claude
status: proposed
created: 2026-05-28
updated: 2026-05-28
targets:
  - scripts/wiki_graph.py
  - scripts/wiki_lint.py
  - scripts/README.md
  - wiki-design/02-workflows.md
  - wiki-design/03-obsidian-graph.md
  - .gitignore
reviewers:
  - codex
  - user
---

# RFC-007: 自建 canonical wiki-graph（03 第二层增强图谱生成器）

## 背景

`03-obsidian-graph.md` 把图谱分三层：

| 层 | 内容 | 现状 |
| --- | --- | --- |
| 第一层 Obsidian 原生 | `[[wikilink]]` 直接形成 | 写页面时天然产生，无需工具 |
| **第二层 增强图谱** | `maps/graph-data.json` + `maps/graph-insights.md`（共享来源 / tag / related / 共同邻居 / 类型亲和 / 社区 / 孤立 / 中心性） | **设计已命名，无生成器** |
| 第三层 机器图谱 | LightRAG / graphify 抽实体关系 | 留给 RFC-008 |

`02-workflows.md` 的「图谱刷新」workflow 写了流程（扫 wiki → 提取 wikilink/sources/related → 生成 graph-data.json / graph-insights.md），但没有实现体。本 RFC 实现**第二层**。

**为什么 canonical 图谱必须自建、而不是用 graphify（第三层）生成**：

我们的图谱边有 canonical 归宿——它们是 frontmatter 里**判断式抽取后固化为正本**的关系（`source_ids` / `related_ids` / `supersedes` / `canonical_id` + `[[wikilink]]`），被 wiki-lint 校验、可手改、git 管。graphify 是**机械全量抽取（无正本，可重算）**：它解析 raw 内容推断边，且其 markdown 抽取器只看 heading/code/反引号，**完全不读我们的 frontmatter 和 wikilink**（已实测 `graphify/extract.py:extract_markdown`）。

所以两者是**互补**而非替代：

- 第二层（本 RFC）：把已固化的 canonical 边**投影**成图谱（高精度，lint 校验过）
- 第三层（RFC-008）：graphify 在 raw 上**发现**我们没策展的连接 → 喂 review_queue 等人确认

而且我们比参考实现（nashsu/llm_wiki 的 `wiki-graph.ts`）起点更高：它的边只能靠文件名 wikilink 匹配 + 临时 lowercase/连字符归一化；**我们有 lint 校验过的 canonical ID 引用 + 现成的 `normalized_alias_index.json`**（RFC-004）。所以本 RFC 不是从零造，而是"把 lint 已经解析好的关系多投影一个 graph-data.json"。

## 提案

新增 `scripts/wiki_graph.py`：从 canonical frontmatter 边 + wikilink 生成第二层增强图谱派生层。复用 wiki-lint 已有的 frontmatter 解析、`id_index`、`normalized_alias_index`。

### 范围（MVP 包含）

#### 1. 节点

- 来源：`knowledge/wiki/**/*.md`（8 类页面）
- 字段：`id`（frontmatter id）/ `label`（H1 标题，回退 slug）/ `type` / `status` / `degree` / `community`
- `status: redirect` 的薄重定向页：**折叠**到正名页（不单独成节点；其入边重定向到 `canonical_id` 目标），与 RFC-004 "薄页不参与主图谱节点" 一致
- inbox / archive / 上下文层 md：**不进图**（非 wiki 页面）

#### 2. 边（全部来自显式 canonical 数据或 wikilink，无推断）

| relation | 来源字段 | source_kind | 有向性 |
| --- | --- | --- | --- |
| `source_ref` | `source_ids[]` | canonical | 有向（page → source） |
| `related` | `related_ids[]` | canonical | 无向 |
| `supersedes` | `supersedes[]` / `superseded_by[]` | canonical | 有向 |
| `wikilink` | 正文 `[[...]]` 经 `normalized_alias_index` 解析 | wikilink | 有向 |

每条边带：`source` / `target` / `relation` / `source_kind`（`canonical` \| `wikilink`）/ `weight`（canonical=2，wikilink=1；同一对节点多关系取最大权重并合并 relation 列表）。

> **不引入 INFERRED / AMBIGUOUS**：我们的边都是显式写的。推断类边是第三层 graphify 的事（RFC-008）。本层只投影"已存在的边"。

> **第二层"计算关系"**（共享来源 / 共享 tag / 共同邻居 / 类型亲和）：03 列为增强项。MVP **只做共享来源**（两个页面 `source_ids` 有交集 → `co_source` 边，`source_kind: computed`，weight=1），其余计算关系（共享 tag / 共同邻居 / 类型亲和）留给后续迭代，避免 MVP 边爆炸。

#### 3. wikilink 解析（复用 RFC-004 派生层）

- `[[X]]` → 先查 `normalized_alias_index.json`（命中正名 entity 的 canonical_id）
- 未命中 alias index → 查 `id_index` 的 label / slug 匹配
- 都未命中 → 记为 `dangling_wikilink`（进 insights 警示，不建边）

#### 4. 社区检测（纯标准库）

- MVP 用**确定性 label propagation**（固定节点遍历顺序 = id 字典序，固定迭代轮数上限，平局取最小 community id），保证多次运行结果一致
- 不引入 networkx（保持 wiki-lint 零重依赖原则）
- 社区仅用于 insights 分组和可视化着色，不写回 canonical

#### 5. Insights（`maps/graph-insights.md`）

MVP 计算（对齐 03「Graph Insights」段，取与 lint 不重叠的项）：

- **孤立节点**：degree 0 的页面（可能需关联或归档）
- **高中心性 hub**：degree top N（核心概念）
- **最大社区**：size 排序 + 每个社区 top 节点
- **跨类型连接**：不同 `type` 之间的边（借 llm_wiki「surprising connections」思路）
- **dangling wikilink**：解析不到目标的 `[[...]]`

不做（避免与现有机制重复）：

- 断引检测（wiki-lint 已管 `CANONICAL_DANGLING`）
- 重复 entity（wiki-lint `ALIAS_CONFLICT` + review_queue 已管）
- 合并 / 拆分建议（需语义判断，留后续 RFC）

#### 6. 输出（三个派生文件，全部进 `.gitignore`）

| 文件 | 内容 |
| --- | --- |
| `knowledge/maps/graph-data.json` | 节点 + 边 + 社区（机器可读，给 Obsidian / d3 / graphify 消费） |
| `knowledge/maps/knowledge-graph.md` | 人类可读图谱概览（节点数 / 边数 / 社区列表 / 类型分布） |
| `knowledge/maps/graph-insights.md` | 上述 insights |

`graph-data.json` schema：

```json
{
  "version": 1,
  "generated_at": "<ISO 8601 with tz>",
  "stats": { "nodes": 0, "edges": 0, "communities": 0 },
  "nodes": [
    { "id": "ent_20260526_attention", "label": "Attention", "type": "entity",
      "status": "active", "degree": 0, "community": 0 }
  ],
  "edges": [
    { "source": "top_x", "target": "src_y", "relation": ["source_ref"],
      "source_kind": "canonical", "weight": 2 }
  ],
  "communities": [
    { "id": 0, "size": 0, "top_nodes": [] }
  ]
}
```

### 范围（MVP 不包含 → 留后续）

- graphify / LightRAG 第三层机器图谱（RFC-008）
- 推断边（INFERRED / AMBIGUOUS）
- 交互式 HTML 可视化（graph.html）—— 出 graph-data.json 即可，渲染交给 Obsidian / graphify / 未来 RFC
- 第二层其余计算关系（共享 tag / 共同邻居 / 类型亲和）—— MVP 只做共享来源
- 语义关系类型（`supports` / `contradicts` / `depends_on` 等，03「关系类型」表）—— 当前无 frontmatter 字段承载，留给"evidence 结构化"相关 RFC
- networkx / Louvain（MVP 用标准库 label propagation）
- edge relevance 加权（llm_wiki 用单独 retrieval graph；MVP 用固定权重）
- 合并 / 拆分建议
- pre-commit / 自动触发

### CLI 与实现约束

```bash
conda activate py312
python3 scripts/wiki_graph.py            # 生成 3 个派生文件
python3 scripts/wiki_graph.py --json     # graph-data 打到 stdout（不写文件，预览/管道用）
```

退出码：`0` 正常；`2` 配置 / 脚本自身错误（knowledge/ 不存在、依赖缺失等）。

- **语言**：Python 3.12（统一环境）+ PyYAML（与 wiki-lint 同款唯一依赖），其余标准库
- **复用**：import `wiki_lint.py` 的 frontmatter 解析 / id 解析 helper，**不重复实现**；为此对 `wiki_lint.py` 做**轻量 refactor**，把解析函数抽成可 import（不改变 lint 对外行为和退出码）
- **派生索引依赖**：运行前若 `id_index.json` / `normalized_alias_index.json` 不存在，先内部调用 lint 的构建逻辑生成（或提示先跑 `wiki_lint.py`）
- **原子写**：与 wiki-lint 同款（`<file>.<pid>.<uuid>.tmp` + `os.replace` + 确定序）
- **确定性**：同样输入多次运行产出字节一致（社区 label propagation 固定顺序，JSON sort_keys）
- **零网络 / 零 LLM**：纯机械投影

### 与现有流程的衔接

- `02-workflows.md`「图谱刷新」：把流程描述替换为 `python3 scripts/wiki_graph.py`
- ingest Apply / inbox 晋升 / 结晶化 完成后建议刷新图谱（非强制）
- `03-obsidian-graph.md`：第二层标注落地（RFC-007），第三层仍待 RFC-008

## 替代方案

### A. 独立脚本 vs lint 子命令

| 方案 | 评价 |
| --- | --- |
| **独立 `scripts/wiki_graph.py`（import lint parser）** | 推荐：单一职责（lint 校验 / graph 投影分开），互不拖累退出码语义 |
| `wiki_lint.py --graph` 子命令 | lint 职责膨胀；校验失败时该不该出图含糊 |

### B. 社区检测

| 方案 | 评价 |
| --- | --- |
| **标准库确定性 label propagation** | 推荐：零依赖，结果确定；小规模够用 |
| networkx + Louvain | 质量更好但引入重依赖；留作后续可选（`--use-networkx`） |
| 仅 connected components | 太粗，社区即连通分量，无法分簇 |

### C. 边来源范围

| 方案 | 评价 |
| --- | --- |
| **canonical 引用 + wikilink + 共享来源** | 推荐：覆盖第一层 + 第二层核心，标 `source_kind` 可区分 |
| 仅 canonical 引用 | 漏掉 wikilink 显示层连接 |
| 全量计算关系（含 tag/邻居/类型亲和） | MVP 边爆炸，难读 |

### D. 语义关系类型（supports/contradicts/...）

| 方案 | 评价 |
| --- | --- |
| **MVP 推迟**（只做字段派生的结构关系） | 推荐：当前无 frontmatter 字段承载语义关系，硬塞会无数据 |
| 现在引入 | 需先加 frontmatter 字段（动 schema = 另一个 RFC） |

### E. 可视化

| 方案 | 评价 |
| --- | --- |
| **MVP 只出 graph-data.json + 2 个 md** | 推荐：渲染交给 Obsidian 原生图谱 / graphify / 未来 RFC |
| 自建 graph.html | 重复造轮子，graphify 已有成熟交互 HTML |

## 影响范围

### 新增

- `scripts/wiki_graph.py`（约 400~600 行 Python）

### 改动正本

- `scripts/wiki_lint.py`：轻量 refactor，把 frontmatter / id 解析抽成可 import 函数（**不改对外行为、退出码、error code**）
- `scripts/README.md`：新增 wiki-graph 段（用法 + 输出 + MVP 范围）
- `wiki-design/02-workflows.md`：「图谱刷新」流程 → 具体命令
- `wiki-design/03-obsidian-graph.md`：第二层标注落地状态
- `.gitignore`：新增 `knowledge/maps/knowledge-graph.md` + `knowledge/maps/graph-insights.md`（`graph-data.json` 已在）

### 不改动

- 任何 `knowledge/**` 数据（wiki_graph 只读 + 写 maps/ 派生层）
- RFC-001~006 的 schema 定义
- wiki-lint 的校验语义

### 依赖

- PyYAML（已有，wiki-lint 同款）
- 无新增重依赖（networkx 仅作后续可选）

### 与 Backlog / 后续 RFC 的关系

| 议题 | 关系 |
| --- | --- |
| RFC-008 graphify（第三层） | 本 RFC 是其前置：canonical 图谱先立住，graphify 才好接成发现层 |
| 查询路由表（Backlog P1） | graph-data.json 可作"图谱多跳"通道的数据底座 |
| Wiki 健康度指标（Backlog P2） | insights 的孤立 / hub / 社区可喂健康度 |
| evidence 结构化（Backlog P1） | 语义关系类型（supports/contradicts）依赖它，故本 RFC 推迟 |

### 风险

1. **wiki_lint.py refactor 回归**：抽 parser 时可能破坏 lint 行为。缓解：refactor 后必须重跑 TASK-006 Step 6 全量验证（A/B/C/D/E1~E11/F）确认 lint 无回归。
2. **社区检测确定性**：label propagation 天然随机。缓解：固定遍历顺序（id 字典序）+ 平局取最小 community id + 固定迭代上限。
3. **派生索引依赖顺序**：wiki_graph 依赖 id_index / normalized_alias_index。缓解：运行前检测，缺失则先构建或提示先跑 lint。
4. **空 knowledge/ 当前态**：wiki/ 全空时应产出空图（nodes/edges/communities 全空）+ exit 0，不报错。
5. **规模**：MVP 全量重算，< 1000 页 < 1 秒；规模上去再考虑增量。

## Review by codex · YYYY-MM-DD

（待 Codex 追加）

## Decision

（待用户填写或授权 Agent 代写）
