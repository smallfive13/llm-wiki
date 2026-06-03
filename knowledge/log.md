# Knowledge Base Log

> 重要知识库更新（ingest / promote / 决策 / 综合 / schema 变更）追加到此文件，按时间倒序排列。

## 2026-06-03 · 样板实例维护：填实 purpose + 同步 overview + 4 页降级

外部评估指出本实例（引擎自带样板）数据不实：purpose 占位、overview 报 RFC-001~008（实际 14）、4 页 high 但 review:false（unverified-high 全标红）。处理：

- **purpose.md** 填实：明确本实例 = base schema 最小样板 + 工具自测样本，**非权威**；权威说明转交 `wiki-design/rfcs/` + personal 库。
- **overview.md** 同步：RFC-001~008 → **001~014**；开放问题更新（部署形态已部分落地）；健康度改用 `wiki_eval` 口径。
- **4 页 confidence high → medium**（诚实降级，非背书）：它们是 2026-05-28 样板快照、滞后 RFC-006~014、无人背书，声称 high 不实。降级后 `UNVERIFIED_HIGH` 清零、eval endorsement 不再被惩罚。
- 决定：本样板不与 personal 重复维护「最新系统说明」，保持「永远合法、可自测」即可。

校验：`wiki_lint --root knowledge` exit 0；投影：`wiki_graph`；评估：`wiki_eval`。

## 2026-05-28 · 首次结晶化：llm-wiki 自身架构

把本知识库系统的设计结晶化进 `wiki/`（首次真实写入，crystallization）。新建 4 个页面：

- `syn_20260528_llm-wiki-architecture`（synthesis）：[llm-wiki 系统架构](wiki/synthesis/llm-wiki-architecture.md)——分层架构 + 架构图 + 图谱三层 + 核心原则 + RFC 链
- `top_20260528_rfc-task-protocol`（topic）：[RFC + Task 协作协议](wiki/topics/rfc-task-protocol.md)
- `top_20260528_wiki-schema-rules`（topic）：[知识库 Schema 与页面规则](wiki/topics/wiki-schema-rules.md)
- `top_20260528_toolchain-usage`（topic）：[工具链与使用说明](wiki/topics/toolchain-usage.md)

校验 / 投影：`wiki_lint --check-only` exit 0（4 页全过）；`wiki_graph` 投影 4 节点 / 16 边（canonical related + wikilink）/ 1 社区 / 0 dangling。来源为本仓库 `wiki-design/` + RFC-001~008，未注册 source（结晶化非外部 ingest），`source_ids` 为空。

下一步：首次外部资料 ingest 时激活 source_manifest 链路。

## 2026-05-27 · Initialized

Knowledge base scaffold created by TASK-005 (apply RFC-001~005 frozen schema).

Schema frozen by:

- **RFC-001**（commit `a7b5c40` baseline）：Codex + Claude Code 协作机制，引入 wiki-design/rfcs/ 和 AGENTS.md
- **RFC-002**（commit `a793882` apply）：稳定页面 ID（`<prefix>_YYYYMMDD_<slug>`），8 个页面类型 prefix，拆分/合并语义，Cross-ref canonical/display 边界
- **RFC-003**（commit `fd32feb` apply）：低摩擦 capture（opt-in 自动 / 默认建议），inbox 缓冲层，capture_policy.json（PII 兜底），Capture Item / Inbox Index Schema
- **RFC-004**（commit `4453fb8` apply）：entity aliases / canonical_id，status: redirect 枚举，Normalized Alias Index Schema，alias matching 跨 ingest 与 inbox 晋升共享
- **RFC-005**（与 RFC-001 同期）：tasks/ 通道作为执行指令载体

Setup commit 范围：`a7b5c40` (pre-RFC baseline) → `054b1b0` (TASK-004 evaluated, all RFC applied)。

骨架内容：

- 14 个空子目录用 `.gitkeep` 占位
- `source_manifest.json` 和 `review_queue.json` 初始为空 items 数组
- `capture_policy.json` 使用 RFC-003 默认值（`auto_capture: false`、`exclude_paths: []`、`max_inbox_files: 100`）
- 派生层（`id_index.json` / `inbox_index.json` / `normalized_alias_index.json` / `cache.json` / `search_index/` / `lightrag/` / `maps/graph-data.json`）在 `.gitignore` 中排除

下一步：用户首次 ingest / capture / promotion / 决策时追加新 log 段。
