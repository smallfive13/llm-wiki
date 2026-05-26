# Agent-native Wiki 设计草案

本文档沉淀本项目关于“由 Codex / Claude Code 触发知识库整理”的设计思路。

目标不是复刻 Qoder Repo Wiki，也不是直接绑定某个知识库产品，而是设计一套轻量、可审查、可演进的 Wiki 工作流：

- 以 Markdown 文件作为知识正本，方便 Git、Obsidian、Agent 共同使用。
- 由 Codex / Claude Code 在需要时触发摄入、整理、查询、结晶化和健康检查。
- 借鉴 `sdyckjq-lab/llm-wiki-skill` 的轻量本地工作流。
- 借鉴 `nashsu/llm_wiki` 的两步摄入、review queue、图谱洞察和产品化经验。
- 借鉴 Karpathy `llm-wiki` 的 `raw -> wiki -> schema` 知识编译范式。
- 借鉴 LightRAG 的图谱增强检索，但把它放在派生索引层，而不是知识正本。
- 借鉴 Qoder Repo Wiki 的增量更新和显性化隐性知识思路，但不把 Repo Wiki 当主目标。

## 核心结论

Wiki 应该是“人和 Agent 都能读写的长期知识层”，不是一次性 RAG 问答缓存。

推荐分层：

```text
Raw Source 层       原始资料、网页、PDF、对话、代码片段
Human Wiki 层       Markdown 正本，Git 管理，Obsidian 可浏览
Graph/Search 层     Obsidian 链接图、LightRAG/qmd/向量索引等可重建派生层
Agent Context 层    高密度规则、近期结论、待办、决策、开放问题
Workflow 层         ingest、query、crystallize、lint、review、graph refresh
```

## 推荐目录

```text
knowledge/
  purpose.md
  index.md
  overview.md
  log.md
  .wiki-schema.md

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
    graph-data.json
    graph-insights.md

  dashboards/
    review.base
    sources.base
    entities.base
    questions.base
    decisions.base

  .wiki/
    cache.json
    review_queue.json
    search_index/
    lightrag/
```

## 参考项目角色

| 来源 | 吸收内容 | 不直接照搬的部分 |
| --- | --- | --- |
| Karpathy llm-wiki | `raw -> wiki -> schema`，`ingest/query/lint` | 不只停留在概念，需要落成本地工作流 |
| sdyckjq-lab/llm-wiki-skill | Agent 直接维护本地 Markdown Wiki | 需要补充项目自身规则和审核边界 |
| nashsu/llm_wiki | 两步 ingest、review queue、图谱洞察、Obsidian 友好 | 不强依赖桌面 App 或本地 HTTP 服务 |
| LightRAG | 实体关系图、多跳检索、增量机器索引 | 不把图谱数据库当知识正本 |
| Qoder Repo Wiki | 增量更新、隐性知识显性化、Agent 上下文 | 不以完整 Repo Wiki 为目标 |

## 当前设计文档

- [01-architecture.md](01-architecture.md)：整体架构和分层。
- [02-workflows.md](02-workflows.md)：Agent 触发工作流。
- [03-obsidian-graph.md](03-obsidian-graph.md)：Obsidian、wikilink、知识图谱和 dashboard 设计。
- [04-agent-rules.md](04-agent-rules.md)：Codex / Claude Code 可复用规则。
- [05-contracts-and-next-steps.md](05-contracts-and-next-steps.md)：review queue、source manifest、页面模板、答案引用格式和下一步实施顺序。
