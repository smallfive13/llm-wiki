# Knowledge Base Log

> 重要知识库更新（ingest / promote / 决策 / 综合 / schema 变更）追加到此文件，按时间倒序排列。

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
