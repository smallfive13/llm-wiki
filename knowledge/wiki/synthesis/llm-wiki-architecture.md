---
id: syn_20260528_llm-wiki-architecture
type: synthesis
status: active
confidence: high
created: 2026-05-28
updated: 2026-05-28
last_verified: 2026-05-28
review: false
source_ids: []
related_ids:
  - top_20260528_rfc-task-protocol
  - top_20260528_wiki-schema-rules
  - top_20260528_toolchain-usage
sources: []
related:
  - "[[RFC + Task 协作协议]]"
  - "[[知识库 Schema 与页面规则]]"
  - "[[工具链与使用说明]]"
supersedes: []
superseded_by: []
evidence_count: 8
---

# llm-wiki 系统架构

> 一个人和 Agent 都能读写的长期知识层。由 Codex 与 Claude Code 协作维护，Markdown 为正本、Git 为审计、派生层可重建。本页是顶层综合，细节见 [[RFC + Task 协作协议]]、[[知识库 Schema 与页面规则]]、[[工具链与使用说明]]。

## 一句话定位

Wiki 是「长期知识层」而非一次性 RAG 缓存：知识以 Markdown 正本沉淀，关系由人/Agent 策展进 frontmatter，工具机械校验并投影图谱。设计借鉴 Karpathy llm-wiki 的 `raw → wiki → schema` 编译范式、nashsu/llm_wiki 的两步摄入与图谱洞察、LightRAG 的图增强检索（仅作派生层）。

## 分层架构

```text
┌──────────────────────────────────────────────────────────────┐
│ 引擎 / 协议层（单一来源，跨业务复用）                          │
│   wiki-design/   RFC + Task + 设计正本（01~05）                │
│   AGENTS.md      Codex/Claude 协作规则                         │
│   scripts/       wiki_common · wiki_lint · wiki_graph（py312） │
│   BASE_SCHEMA    RFC-002~007 冻结契约的单一来源               │
└──────────────────────────────────────────────────────────────┘
                          │ --root 指向任一实例
                          ▼
┌──────────────────────────────────────────────────────────────┐
│ 实例层（每业务一份；可选 .wiki-profile.json 增量扩展 schema）  │
│                                                                │
│  raw/            原始资料 + source_manifest.json（canonical）  │
│  wiki/           8 类知识正本页（source/entity/topic/          │
│                  comparison/synthesis/decision/query/          │
│                  open-question）                               │
│  inbox/          capture 缓冲层（draft → archive/）            │
│  .wiki/          review_queue / capture_policy（canonical）    │
│                  + id_index / alias_index / inbox_index（派生）│
│  maps/           graph-data.json / knowledge-graph.md /        │
│                  graph-insights.md（派生，gitignore）          │
│  purpose/index/overview/log.md   上下文层（无 frontmatter）   │
└──────────────────────────────────────────────────────────────┘
```

## 知识图谱三层

| 层 | 内容 | 状态 |
| --- | --- | --- |
| 第一层 Obsidian 原生 | wikilink 双链直接形成 | 写页面天然产生 |
| 第二层 增强图谱 | `wiki_graph` 从 canonical 引用 + wikilink + 共享来源投影 `maps/graph-data.json` + insights | 已落地（RFC-007） |
| 第三层 机器图谱 | graphify / LightRAG 在 raw 上发现隐性连接 → review_queue suggestion | 待后续 RFC |

**canonical 图谱必须自建**：边是 frontmatter 里「判断式抽取后固化为正本」的关系（lint 校验、可手改）；graphify 是「机械全量抽取（无正本）」且不读 frontmatter/wikilink，因此只当第三层发现层，不作正本引擎。

## 核心设计原则

1. **正本 vs 派生强分离**：frontmatter 引用 / source_manifest / review_queue 是 canonical；id_index / 图谱 / 缓存是派生（gitignore，可重建）。
2. **canonical 按 ID，显示按 path/wikilink**：改名不破坏机器引用。
3. **inbox 必经缓冲**：低门槛 capture 先落 inbox，整理时才晋升 wiki/，严禁绕过。
4. **机械保障替代人肉遵守**：schema 约束由 `wiki_lint` 校验，不靠记忆。
5. **决策与执行分离**：RFC 决定「要不要」，Task 决定「怎么做」，append-only + git 即审计。
6. **引擎单一来源 + 实例 profile 扩展**：一套工具服务多个 schema 各异的业务库。

## 演进历程（RFC 链）

| RFC | 主题 |
| --- | --- |
| RFC-001 | Codex + Claude 协作机制（RFC + AGENTS.md） |
| RFC-002 | 稳定页面 ID（`<prefix>_YYYYMMDD_<slug>`，永不变） |
| RFC-003 | 低门槛 capture + inbox 缓冲层 + PII 兜底 |
| RFC-004 | entity 别名 / canonical_id / 规范化别名索引 |
| RFC-005 | Task 通道（执行指令载体） |
| RFC-006 | wiki-lint MVP（8 类机械校验 + 派生索引） |
| RFC-007 | wiki-graph（第二层增强图谱生成器） |
| RFC-008 | 业务 schema profile（base + overlay，多实例复用） |

## 引用

- 设计正本：`wiki-design/01-architecture.md` ~ `05-contracts-and-next-steps.md`
- 决策记录：`wiki-design/rfcs/RFC-001` ~ `RFC-008`
- 工具实现：`scripts/wiki_common.py` / `wiki_lint.py` / `wiki_graph.py`

## 置信度与缺口

- 置信度：high（本系统自身设计，已 8 轮 RFC + Task 落地验证）
- 缺口：第三层机器图谱（graphify）未落地；首次外部资料 ingest 尚未发生；部署形态（单仓多实例 vs 多 repo）未定。
