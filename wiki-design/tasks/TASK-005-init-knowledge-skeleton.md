---
id: task_20260526_005
title: 初始化 knowledge/ 骨架（基于 RFC-001~005 冻结 schema）
author: claude
executor: codex
status: pending
type: bookkeeping
created: 2026-05-27
updated: 2026-05-27  # v2 after codex spec review v1
related_rfcs:
  - rfc_20260526_001
  - rfc_20260526_002
  - rfc_20260526_003
  - rfc_20260526_004
  - rfc_20260526_005
---

# TASK-005: 初始化 knowledge/ 骨架

## 目标

基于已冻结的 RFC-001~005 schema 创建 `knowledge/` 目录骨架，包含：

- 4 个上下文层 seed markdown：`purpose.md` / `index.md` / `overview.md` / `log.md`（无 frontmatter，普通 Markdown）
- 1 个高密度契约镜像：`.wiki-schema.md`（从 01/05 抽出，Agent 会话起点）
- 3 个 JSON 契约：`raw/source_manifest.json` / `.wiki/review_queue.json` / `.wiki/capture_policy.json`（初始为空 / 默认值）
- 14 个空子目录（用 `.gitkeep` 占位）

执行完成后，Agent 可以从 `knowledge/` 开始进行 ingest / capture / query / promotion 工作。

## 前置条件

- 仓库根目录：`/Users/zhangjunwu/workspace/llm-wiki/llm-wiki`
- HEAD 包含 **TASK-004 已 done**（commit `054b1b0` 及之后），即所有 wiki-design 正本 schema 已冻结：
  - 01 含 prefix 表（含 inb_）/ status 含 redirect / Cross-ref 字段说明
  - 02 含被动 capture / Inbox 晋升 / 摄入资料 Triage（含 alias matching）
  - 05 含 Capture Item / Capture Policy / Inbox Index / Normalized Alias Index 四段 Schema + Entity 模板有 aliases/canonical_id
  - AGENTS.md 含低摩擦 capture 子节
  - .gitignore 含 id_index/inbox_index/normalized_alias_index 三个派生层
- working tree clean
- 已读 wiki-design/01-architecture.md / 05-contracts-and-next-steps.md（理解契约）
- 已读 TASK-002/003/004 Evaluation（理解 apply 类 task 工作流惯例）

## 强约束

违反任一即视为执行失败：

1. **只创建** `knowledge/**` 路径下的文件。不修改 `knowledge/` 以外任何文件（包括 AGENTS.md、wiki-design/、.gitignore）。
2. 本 TASK-005 文件本身按 Step 0 / 6 / 7 允许编辑（追加 Spec review、推进 status、追加 Execution log）。
3. **必须先经 Codex spec review（Step 0）**：在 Step 0 通过前 status 保持 pending。
4. 4 个上下文层 markdown（purpose/index/overview/log）**无 frontmatter**，纯 Markdown。它们是上下文层文件，不是 wiki 页面，不走 RFC-002 ID 规范。
5. `.wiki-schema.md` 内容**必须**按 Step 3 给出的完整模板逐字生成，**不**自行增删字段或表格。
6. 3 个 JSON 契约必须是**合法 JSON**（验证用 `python -m json.tool` 或 `jq`）。
7. JSON 默认值必须符合 RFC-003 Decision：
   - `capture_policy.json` 的 `auto_capture: false`
   - `capture_policy.json` 的 `exclude_paths: []`（空数组，**不**含 `wiki/decisions/**`）
8. 所有空子目录用 `.gitkeep` 占位（git 不跟踪空目录）。
9. **不要**创建任何真实的 wiki 页面（如 `wiki/topics/foo.md`）。本 task 只建骨架，不填充内容。
10. 三个 commit 分别：Step 0 Spec review（codex 写时自行 commit）/ Step 6 创建 knowledge/ / Step 7 task status 推进。

## 工作流

```
Step 0  Codex spec review (本 task 文件，追加 Spec review 段) + 单独 commit
        │
        │  通过 → Step 1
        │  需修改 → Claude 改 spec → 重新进入 Step 0
        │
        ▼
Step 1~4  Codex 创建 knowledge/ 下所有文件
        │
        ▼
Step 5  自检验证
        │
        ▼
Step 6  Commit 全部新建文件（[init knowledge/] 前缀）
        │
        ▼
Step 7  推进 task status pending → done + 追加 Execution log + commit
```

## 步骤

### Step 0：Spec review（执行前必跑）

在本 task 文件末尾追加：

```markdown
## Spec review by codex · 2026-05-27

### 完整性
- [ ] knowledge/ 目录结构 + 所有 seed 文件是否完整覆盖 RFC-001~005 schema
- [ ] .wiki-schema.md 内容是否高密度但够用（不过度精简）
- [ ] JSON 默认值是否符合 RFC-003 Decision（auto_capture: false, exclude_paths: []）

### 可执行性
- [ ] 每个 Step 是否有明确的文件列表 / 内容模板
- [ ] 验证步骤是否能机械跑（JSON 合法性、文件存在性、关键字段）

### 风险
- 列出可能踩坑的地方

### 结论
- 通过 / 需修改 (列出建议)
```

Codex 自行 commit 这次 Spec review 改动（commit message：`[task] TASK-005 spec review by codex (conclusion: <通过/需修改>)`）。

### Step 1：创建目录骨架 + .gitkeep

创建以下 14 个空目录，每个目录放一个 `.gitkeep` 文件（空文件）：

```text
knowledge/raw/sources/.gitkeep
knowledge/wiki/sources/.gitkeep
knowledge/wiki/entities/.gitkeep
knowledge/wiki/topics/.gitkeep
knowledge/wiki/comparisons/.gitkeep
knowledge/wiki/synthesis/.gitkeep
knowledge/wiki/decisions/.gitkeep
knowledge/wiki/queries/.gitkeep
knowledge/wiki/open-questions/.gitkeep
knowledge/inbox/.gitkeep
knowledge/inbox/archive/promoted/.gitkeep
knowledge/inbox/archive/dropped/.gitkeep
knowledge/maps/.gitkeep
knowledge/.wiki/.gitkeep
```

注意：`.gitkeep` 是空文件（0 字节），不写任何内容。

### Step 2：创建 4 个上下文层 seed markdown 文件

#### 2a：`knowledge/purpose.md`

完整内容：

```markdown
# Purpose

> 一句话说明这个知识库为什么存在、典型读者是谁、长期目标是什么。

（占位：请填写实际意图。例如：「记录与 Agent-native Wiki 设计相关的研究、决策与延伸阅读，供本人长期参考和迭代。」）

---

更新此页时同步更新 `log.md`。
```

#### 2b：`knowledge/index.md`

完整内容：

```markdown
# Index

## 入口

- [Purpose](purpose.md) — 知识库目的
- [Overview](overview.md) — 顶层综合视图
- [Log](log.md) — 变更日志
- [Wiki Schema](.wiki-schema.md) — 数据契约（Agent 会话起点）

## 主目录

| 路径 | 用途 |
| --- | --- |
| `raw/` | 原始资料（PDF / 网页 / 对话 / 代码片段） |
| `raw/source_manifest.json` | 资料登记表 |
| `wiki/sources/` | 单来源摘要 |
| `wiki/entities/` | 公司 / 人物 / 项目 / 指标 / 模型 / 工具 |
| `wiki/topics/` | 跨来源主题页 |
| `wiki/comparisons/` | 工具 / 方案 / 观点对比 |
| `wiki/synthesis/` | 多来源综合结论 |
| `wiki/decisions/` | 重要判断 / 选择 / 取舍 |
| `wiki/queries/` | 值得沉淀的问题和回答 |
| `wiki/open-questions/` | 待验证 / 冲突 / 空白 |
| `inbox/` | Capture 缓冲层（draft），定期 promote |
| `inbox/archive/promoted/` | 已晋升 capture（审计） |
| `inbox/archive/dropped/` | 已丢弃 capture（审计） |
| `maps/` | 派生图谱可视化 |
| `.wiki/review_queue.json` | 待人工审核队列 |
| `.wiki/capture_policy.json` | Capture 控制策略 |

## 当前状态

- 初始化日期：2026-05-27
- Schema 版本：RFC-001~005 applied
- Wiki 页面数：0（待填充）
- Inbox draft 数：0

> 此页面是入口；具体规范见 [.wiki-schema.md](.wiki-schema.md)。
```

#### 2c：`knowledge/overview.md`

完整内容：

```markdown
# Overview

> 高层综合：这个知识库目前包含什么、围绕什么主题展开、有哪些重要决策、有哪些开放问题。

（占位：知识库初始化时为空。随着 wiki 增长，此页面应定期更新为顶层综合视图。建议每 10 个新 wiki 页面或每月一次回顾。）

## 主要主题

（待填充）

## 重要决策

（待填充）

## 开放问题

（待填充）

## 知识健康度

| 指标 | 当前值 |
| --- | --- |
| wiki 页面总数 | 0 |
| sources 摘要数 | 0 |
| inbox draft 数 | 0 |
| 最老 draft 年龄（天） | — |
| review_queue pending 数 | 0 |
| 平均 confidence | — |

> 健康度由 `wiki-lint`（未实现）周期性更新。当前是手动维护。
```

#### 2d：`knowledge/log.md`

完整内容：

```markdown
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
```

### Step 3：创建 `.wiki-schema.md`（高密度契约镜像）

文件路径：`knowledge/.wiki-schema.md`

**完整内容**（必须逐字生成，不增删字段或表格）：

```markdown
# Wiki Schema

知识库结构、字段、契约的高密度参考。Agent 会话开始时优先读本文件。更详细规范回到 [wiki-design/01-architecture.md](../wiki-design/01-architecture.md) 和 [wiki-design/05-contracts-and-next-steps.md](../wiki-design/05-contracts-and-next-steps.md)。

## 目录结构

```text
knowledge/
├── purpose.md / index.md / overview.md / log.md     # 上下文层（无 frontmatter）
├── .wiki-schema.md                                   # 本文件
├── raw/
│   ├── source_manifest.json                          # 原始资料登记（canonical）
│   └── sources/                                       # 原始资料文件
├── wiki/{sources,entities,topics,comparisons,synthesis,decisions,queries,open-questions}/
├── inbox/                                            # capture 缓冲（RFC-003）
│   └── archive/{promoted,dropped}/
├── maps/                                             # 派生图谱可视化
└── .wiki/
    ├── review_queue.json                             # 待审核（canonical）
    ├── capture_policy.json                           # capture 策略（canonical）
    └── (派生层 .gitignore: id_index / inbox_index / normalized_alias_index / cache 等)
```

## 页面类型与 ID prefix

每个 wiki 页面 frontmatter 必须有 `id`，格式 `<prefix>_YYYYMMDD_<slug>`。`id` 一旦创建**永不变**（不随标题 / slug / 路径变化）。

| 类型 | 目录 | prefix | 示例 |
| --- | --- | --- | --- |
| source | `wiki/sources/` | `src_` | `src_20260526_attention-paper` |
| entity | `wiki/entities/` | `ent_` | `ent_20260526_attention` |
| topic | `wiki/topics/` | `top_` | `top_20260526_transformer` |
| comparison | `wiki/comparisons/` | `cmp_` | `cmp_20260526_rag-vs-graphrag` |
| synthesis | `wiki/synthesis/` | `syn_` | `syn_20260526_attention-overview` |
| decision | `wiki/decisions/` | `dec_` | `dec_20260526_use-lightrag` |
| query | `wiki/queries/` | `que_` | `que_20260526_what-is-rag` |
| open-question | `wiki/open-questions/` | `oq_` | `oq_20260526_cap-tradeoff` |
| inbox（非 wiki 页面） | `inbox/` | `inb_` | `inb_20260526_153012_attention-complexity` |

**source 单主键约束**：source 类型页面 `id == source_id`（与 `source_manifest.json` 中该 source 一致）。

**同日冲突**：同 prefix 同日同 slug 重名追加 `_NN` 短序号，如 `ent_20260526_attention_002`。

**slug 不是当前标题镜像**：slug 是创建时的可读提示，页面改名后 slug 不变。

## 标准 frontmatter（wiki/ 页面）

```yaml
---
id: <prefix>_YYYYMMDD_<slug>             # 永不变
type: source | entity | topic | comparison | synthesis | decision | query | open-question
status: draft | active | stale | archived | redirect  # redirect 仅 entity 别名薄页
confidence: low | medium | high
created: YYYY-MM-DD
updated: YYYY-MM-DD
last_verified: YYYY-MM-DD
review: true | false
source_ids: []                           # canonical 来源引用（按 ID）
related_ids: []                          # canonical 相关页引用（按 ID）
sources: []                              # 可选显示层（Obsidian wikilink）
related: []                              # 可选显示层（Obsidian wikilink）
supersedes: []                           # 替代的旧页面 ID 数组
superseded_by: []                        # 替代本页面的新页面 ID 数组
evidence_count: 0
# 仅 entity 类额外字段：
aliases: []                              # 别名字符串数组；正名页可有，薄重定向页应为空
canonical_id: null                       # null = 正名页；指向 ent_id = 薄重定向页（须 status: redirect）
# 仅 source 类额外字段：
source_id: src_...                       # 必须 == id
hash_sha256: ...
original_path: raw/sources/...
source_url: ... | null
imported_at: ISO 8601
---
```

## inbox capture item frontmatter

inbox 文件不是 wiki 页面，但有自己的 frontmatter：

```yaml
---
id: inb_YYYYMMDD_HHmmss_<slug>           # 秒级时间戳
type: inbox
status: draft | promoted | dropped       # draft → archive/promoted/ 或 archive/dropped/
created: YYYY-MM-DD
captured_from: <session-id>              # 可选
confidence: low
review: true
suggested_target_type: topic | entity | decision | ...
suggested_target_title: <晋升后页面标题>
---
```

文件命名：`YYYYMMDD-HHmmss-<slug>.md`（同秒冲突追加 `-NN`）。

## JSON 契约

### `raw/source_manifest.json`

```json
{
  "version": 1,
  "sources": [
    {
      "source_id": "src_YYYYMMDD_<slug>",
      "title": "...",
      "source_type": "pdf | markdown | web | chat | image | manual | code",
      "hash_sha256": "...",
      "original_path": "raw/sources/...",
      "source_url": "..." ,
      "imported_at": "ISO 8601",
      "last_ingested_at": "ISO 8601",
      "status": "new | triaged | ingested | skipped | failed | deleted",
      "summary_page_id": "src_..." ,
      "summary_page_path": "wiki/sources/..." ,
      "adapter": "local_file | web_clipper | manual | ...",
      "language": "...",
      "notes": "..."
    }
  ]
}
```

`summary_page_id` 未生成时为 `null`；已生成时**必须等于** `source_id`。

### `.wiki/review_queue.json`

```json
{
  "version": 1,
  "items": [
    {
      "id": "rev_YYYYMMDD_NNN",
      "type": "contradiction | duplicate | missing_page | confirm | suggestion | source_gap | stale_claim",
      "title": "...",
      "status": "pending | resolved | dismissed",
      "priority": "low | medium | high",
      "source_ids": ["src_..."],
      "affected_page_ids": ["ent_...", "top_..."],
      "evidence": [
        {
          "page_id": "ent_...",
          "page_path": "wiki/entities/...",
          "quote": "...",
          "note": "..."
        }
      ],
      "options": [
        { "label": "...", "action": "snake_case_action" }
      ],
      "created_at": "ISO 8601",
      "updated_at": "ISO 8601",
      "resolved_at": null,
      "resolved_action": null
    }
  ]
}
```

`affected_page_ids` / `evidence[].page_id` 是 canonical；`evidence[].page_path` / `source_paths` 是显示层。

### `.wiki/capture_policy.json`

```json
{
  "version": 1,
  "auto_capture": false,
  "exclude_patterns": [
    "密钥", "token", "API[_ ]?key",
    "客户(姓名|名单|信息)",
    "@[a-z]+\\.com",
    "1[3-9]\\d{9}"
  ],
  "exclude_paths": [],
  "max_inbox_files": 100,
  "updated_at": "ISO 8601"
}
```

⚠ **`exclude_patterns` 中的默认正则仅是初始规则，不代表完整 PII 检测**。生产用法必须由 lint、人工 review 和组织安全规范共同保障。Agent 不得把这套正则当作唯一 PII 兜底。

## 派生层（不进 Git）

以下文件由 lint 或工具生成，进 `.gitignore`：

- `knowledge/.wiki/id_index.json`（RFC-002，ID → 当前 path）
- `knowledge/.wiki/inbox_index.json`（RFC-003，draft 计数 + 最近 N 摘要）
- `knowledge/.wiki/normalized_alias_index.json`（RFC-004，规范化 alias → canonical_id）
- `knowledge/.wiki/cache.json`
- `knowledge/.wiki/search_index/`
- `knowledge/.wiki/lightrag/`
- `knowledge/maps/graph-data.json`

## Cross-ref canonical 边界

**canonical**（lint 严格校验、按 ID）：

| 位置 | 字段 |
| --- | --- |
| 页面 frontmatter | `id`、`source_ids`、`related_ids`、`supersedes`、`superseded_by`、`canonical_id` |
| `review_queue.json` 单条 item | `affected_page_ids`、`evidence.page_id` |
| `source_manifest.json` 单条 source | `summary_page_id` |
| 未来 `maps/graph-data.json` 节点 key | 页面 `id` |

**显示层**（仅给人看，lint 不校验完整性）：

| 位置 | 字段 |
| --- | --- |
| 页面 frontmatter | `sources`、`related`（wikilink） |
| `review_queue.json` 单条 item | `evidence.page_path`、`source_paths` |
| `source_manifest.json` 单条 source | `summary_page_path` |
| 答案引用里的 `wiki/.../X.md` 字符串 | 可读 path |

## 答案引用格式

```markdown
正文用 [1]、[2] 标注关键判断。

## 引用

- [1] [[页面名]] · `wiki/topics/example.md` · 支撑：一句话说明
- [2] [[来源摘要]] · `wiki/sources/x.md` · 原始资料：`raw/sources/x.pdf` · source_id: `src_...`

## 置信度与缺口

- 置信度：medium
- 还需要验证：...
```

**别名引用规则**：用户用别名时，回答保留别名原写法并附正名 wikilink，**不要**把别名包成 wikilink：

- 正确：`self-attention（正名 [[Attention]]）`
- 错误：`[[self-attention]]（正名 [[Attention]]）`（除非别名薄页确实存在）

## 写入规则

- 只有用户明确说"存下来 / 沉淀 / 整理进知识库 / 消化这篇资料 / 结晶化 / 更新 Wiki"时才写 `wiki/`。
- 普通对话遵循 RFC-003 capture 规则：默认建议模式（回答末尾 `💡 建议 capture：...`），仅当 `capture_policy.json` 的 `auto_capture: true` 时才直接写 `inbox/`，且每次必须可见报告（`✏️ 已 capture：...`）。
- PII 兜底：内容含密钥 / 客户姓名 / 内部业务等，**无论 auto_capture 开关**一律降级为建议模式。
- **严禁绕过 inbox 直接写 `wiki/`**。

完整 Agent 行为规则见 [../AGENTS.md](../AGENTS.md) 和 [../wiki-design/04-agent-rules.md](../wiki-design/04-agent-rules.md)。

## 拆分与合并语义

- 拆分：新页面拿新 ID；旧页面若保留则原 ID 不变；若完全被取代标 `status: archived` + `superseded_by: [新 ID]`。
- 合并：被合并页保留壳 frontmatter，`status: archived` + `superseded_by: [合并目标 ID]`，正文清空或留一行重定向说明。

## entity 别名机制

99% 别名应放在正名页的 `aliases` 列表里，不建薄页。

少数情况（外部已有 wikilink 散布、不便迁移）才建薄重定向页：`canonical_id` 指向正名页 `id`，`status: redirect`，不参与主图谱节点 / 综合 / 引用来源。

`normalized_alias_index.json` 维护规范化匹配（大小写 / 空格 / 连字符 / 中文全/半角 / 复数）。

## Inbox 晋升 workflow

```text
触发: "消化 inbox" / "整理 inbox"
-> 列出 status: draft 文件
-> 按主题分组 + alias matching（entity 类必须，复用 normalized_alias_index）
-> 用户决策每项: 晋升 / 合并 / 丢弃
-> apply: 移动原 inbox 文件到 archive/{promoted,dropped}/，更新 status
```

健康度统计只计 `knowledge/inbox/*.md`（draft 状态），archive 不计入告警阈值。
```

### Step 4：创建 3 个 JSON 契约文件

#### 4a：`knowledge/raw/source_manifest.json`

完整内容（初始空）：

```json
{
  "version": 1,
  "sources": []
}
```

#### 4b：`knowledge/.wiki/review_queue.json`

完整内容（初始空）：

```json
{
  "version": 1,
  "items": []
}
```

#### 4c：`knowledge/.wiki/capture_policy.json`

完整内容（RFC-003 默认值）：

```json
{
  "version": 1,
  "auto_capture": false,
  "exclude_patterns": [
    "密钥",
    "token",
    "API[_ ]?key",
    "客户(姓名|名单|信息)",
    "@[a-z]+\\.com",
    "1[3-9]\\d{9}"
  ],
  "exclude_paths": [],
  "max_inbox_files": 100,
  "updated_at": "2026-05-27T00:00:00+08:00"
}
```

### Step 5：自检验证

```bash
cd /Users/zhangjunwu/workspace/llm-wiki/llm-wiki

set +e

echo "=== 1. knowledge/ 目录存在 ==="
[ -d knowledge ] && echo "OK" || echo "FAIL"

echo "=== 2. 14 个 .gitkeep 文件（应 = 14）==="
echo "命中: $(find knowledge -name .gitkeep -type f | wc -l)"

echo "=== 3. 4 个上下文层 markdown（应都存在）==="
for f in purpose.md index.md overview.md log.md; do
  [ -f "knowledge/$f" ] && echo "  OK: $f" || echo "  FAIL: $f"
done

echo "=== 4. .wiki-schema.md 存在 ==="
[ -f knowledge/.wiki-schema.md ] && echo "OK" || echo "FAIL"

echo "=== 5. 3 个 JSON 契约存在且合法 ==="
for f in raw/source_manifest.json .wiki/review_queue.json .wiki/capture_policy.json; do
  if [ -f "knowledge/$f" ]; then
    if python3 -m json.tool "knowledge/$f" > /dev/null 2>&1; then
      echo "  OK: $f (valid JSON)"
    else
      echo "  FAIL: $f (invalid JSON)"
    fi
  else
    echo "  FAIL: $f (missing)"
  fi
done

echo "=== 6. capture_policy.json 关键字段 ==="
python3 -c "
import json
d = json.load(open('knowledge/.wiki/capture_policy.json'))
print(f'  auto_capture: {d[\"auto_capture\"]} (应 = False)')
print(f'  exclude_paths: {d[\"exclude_paths\"]} (应 = [])')
print(f'  max_inbox_files: {d[\"max_inbox_files\"]} (应 = 100)')
print(f'  version: {d[\"version\"]} (应 = 1)')
"

echo "=== 7. source_manifest / review_queue 初始为空 ==="
python3 -c "
import json
sm = json.load(open('knowledge/raw/source_manifest.json'))
rq = json.load(open('knowledge/.wiki/review_queue.json'))
print(f'  source_manifest.sources: {sm[\"sources\"]} (应 = [])')
print(f'  review_queue.items: {rq[\"items\"]} (应 = [])')
"

echo "=== 8. .wiki-schema.md 包含关键 schema 段 ==="
for section in '^## 页面类型与 ID prefix' '^## 标准 frontmatter' '^## inbox capture item frontmatter' '^## JSON 契约' '^## 派生层' '^## Cross-ref canonical 边界' '^## 答案引用格式' '^## 写入规则' '^## entity 别名机制' '^## Inbox 晋升 workflow'; do
  cnt=$(grep -cE "$section" knowledge/.wiki-schema.md)
  echo "  $section: $cnt"
done

echo "=== 9. log.md 含初始化记录 ==="
echo "命中: $(grep -c '2026-05-27 · Initialized' knowledge/log.md)"
echo "RFC 引用 (应 ≥ 5): $(grep -cE 'RFC-00[12345]' knowledge/log.md)"

echo "=== 10. 不应有 frontmatter 在 4 个上下文层文件 ==="
for f in purpose.md index.md overview.md log.md; do
  if head -1 "knowledge/$f" | grep -q '^---$'; then
    echo "  FAIL: $f has frontmatter"
  else
    echo "  OK: $f no frontmatter"
  fi
done

echo "=== 11. 不应有真实 wiki 页面（除 .gitkeep） ==="
non_gitkeep_in_wiki=$(find knowledge/wiki -type f ! -name .gitkeep | wc -l)
echo "命中: $non_gitkeep_in_wiki (应 = 0)"

echo "=== 12. 白名单外文件不应被动（应输出 (none)）==="
# 注意：纯创建场景，必须用 --porcelain -uall 展开 untracked 目录；
# git diff --name-only 看不到 untracked 文件，不能用于此检查
out=$(git status --porcelain -uall | cut -c4- | grep -v '^knowledge/' || true)
if [ -z "$out" ]; then echo "  (none)"; else echo "  FAIL: $out"; fi

echo "=== 13. knowledge/ 下新增文件总数（应 = 22）==="
total=$(git status --porcelain -uall | cut -c4- | grep -c '^knowledge/' || true)
echo "命中: $total （14 .gitkeep + 4 md + 1 .wiki-schema.md + 3 json = 22）"

echo "=== 14. knowledge/ 下文件清单（按类型分组验证）==="
echo "  .gitkeep ($(find knowledge -name .gitkeep -type f | wc -l)):"
find knowledge -name .gitkeep -type f | sort | sed 's/^/    /'
echo "  上下文层 md (4):"
ls knowledge/{purpose,index,overview,log}.md 2>/dev/null | sed 's/^/    /'
echo "  .wiki-schema.md (1):"
ls knowledge/.wiki-schema.md 2>/dev/null | sed 's/^/    /'
echo "  JSON 契约 (3):"
ls knowledge/raw/source_manifest.json knowledge/.wiki/review_queue.json knowledge/.wiki/capture_policy.json 2>/dev/null | sed 's/^/    /'
```

预期：

- 1：`OK`
- 2：`14`
- 3：4 个 `OK`
- 4：`OK`
- 5：3 个 `OK: ... (valid JSON)`
- 6：`auto_capture: False`、`exclude_paths: []`、`max_inbox_files: 100`、`version: 1`
- 7：`sources: []`、`items: []`
- 8：10 个段落各 ≥ 1
- 9：初始化记录 ≥ 1，RFC 引用 ≥ 5
- 10：4 个 `OK: ... no frontmatter`
- 11：`命中: 0`
- 12：`(none)` ← `git status --porcelain -uall` 展开后过滤 knowledge/，剩余应为空
- 13：`命中: 22`
- 14：四组清单各项齐全，行数累计 = 22（14+4+1+3）

### Step 6：Commit 全部新建文件

```bash
git add knowledge/

git commit -m "$(cat <<'EOF'
[init knowledge/] scaffold from RFC-001~005 frozen schema

创建知识库实例骨架：

- 4 个上下文层 markdown（无 frontmatter）：
  - purpose.md (用户意图占位)
  - index.md (入口 + 主目录)
  - overview.md (顶层综合骨架 + 健康度表)
  - log.md (首条 Initialized 记录，引用 RFC-001~005 apply commits)
- 1 个高密度契约镜像：
  - .wiki-schema.md (页面类型 / frontmatter / JSON 契约 / canonical 边界 /
    答案引用 / 写入规则 / 别名机制 / inbox 晋升)
- 3 个 JSON 契约（合法 JSON）：
  - raw/source_manifest.json (空 items)
  - .wiki/review_queue.json (空 items)
  - .wiki/capture_policy.json (RFC-003 默认: auto_capture: false,
    exclude_paths: [], max_inbox_files: 100)
- 14 个空子目录用 .gitkeep 占位：
  - raw/sources/
  - wiki/{sources,entities,topics,comparisons,synthesis,decisions,queries,open-questions}/
  - inbox/, inbox/archive/{promoted,dropped}/
  - maps/, .wiki/

Setup commit 范围：a7b5c40 (pre-RFC baseline) → 054b1b0 (TASK-004 evaluated)。

Schema 已冻结，所有 wiki-design 正本（01~05 + AGENTS.md）与 .gitignore
反映 RFC-001~005 的最终状态。

下一步：用户首次 ingest / capture / promotion / 决策时追加新 log 段。

Co-Authored-By: Codex <noreply@openai.com>
EOF
)"
```

### Step 7：推进 task status pending → done

完成 Step 6 后：

1. 修改本文件 frontmatter `status: pending` → `status: done`
2. `updated:` 改为今天
3. 在文件末尾追加 `## Execution log by codex · 2026-05-27` 段，按"完成后报告格式"填写
4. Commit：

```bash
git add wiki-design/tasks/TASK-005-init-knowledge-skeleton.md
git commit -m "[task] TASK-005 done by codex"
```

## 完成后报告格式

把以下内容贴进 `## Execution log by codex · 2026-05-27` 段：

```markdown
## Execution log by codex · 2026-05-27

### 步骤完成情况
- Step 0 Spec review: 通过
- Step 1 目录骨架 + 14 个 .gitkeep: done
- Step 2 4 个上下文层 markdown: done
  - 2a purpose.md: done
  - 2b index.md: done
  - 2c overview.md: done
  - 2d log.md: done
- Step 3 .wiki-schema.md: done
- Step 4 3 个 JSON 契约: done
  - 4a source_manifest.json: done
  - 4b review_queue.json: done
  - 4c capture_policy.json: done
- Step 5 验证: 输出见下

### 验证输出
\`\`\`
<Step 5 全部输出>
\`\`\`

### Commit
- Step 6 commit sha: <sha>
- Step 7 commit sha: 本 commit（实际 sha 由提交后回复报告）

### 偏离 / 异常
<列出与指令不一致的地方；没有就写"无"。验证不完美时在此段解释，不改 spec 或绕过。>
```

## Spec review by codex · YYYY-MM-DD

（待 Codex 在 Step 0 填写）

## Execution log by codex · YYYY-MM-DD

（待执行者在 Step 7 填写）

## Evaluation by claude · YYYY-MM-DD

（待评估者填写）

## Spec review by codex · 2026-05-27

### 完整性
- [x] 22 个文件清单完整：14 个 `.gitkeep`、4 个上下文层 Markdown、1 个 `.wiki-schema.md`、3 个 JSON 契约，覆盖 RFC-001~005 落地后的知识库入口、canonical JSON、capture/inbox、alias 派生索引说明与 task/RFC 协作留痕。
- [x] `.wiki-schema.md` 是高密度但够用的 Agent 起点：覆盖目录结构、页面类型与 ID prefix、wiki frontmatter、inbox frontmatter、JSON 契约、派生层、Cross-ref 边界、答案引用、写入规则、拆分合并、entity 别名、Inbox 晋升。Step 5 只验证其中 10 个关键 H2；模板实际还包含"目录结构"和"拆分与合并语义"，这不是缺口。
- [x] 3 个 JSON 默认值符合 RFC-003 Decision：`source_manifest.json` / `review_queue.json` 初始空数组；`capture_policy.json` 为 `auto_capture: false`、`exclude_paths: []`、`max_inbox_files: 100`，且默认 `exclude_paths` 不含 `wiki/decisions/**`。

### 边界
- [x] 强约束 #1 / #2 的边界清晰：执行阶段只新建 `knowledge/**`，task 文件本身只在 Step 0 / 7 允许追加 review / log 和推进 status。
- [x] 强约束 #4 清楚说明 `purpose.md` / `index.md` / `overview.md` / `log.md` 无 frontmatter，且不走 RFC-002 ID 规范。
- [x] 强约束 #9 清楚禁止真实 wiki 页面；Step 1 只在 `wiki/*/` 下放 `.gitkeep`，Step 5 第 11 项也会检查非 `.gitkeep` 文件数。

### 可执行性
- [x] Step 1~4 的文件路径和内容模板足够明确，JSON 内容本身合法；Step 5 的 `python3 -m json.tool` 和后续 `python3 -c` 字段检查可机械执行。
- [x] Step 5 第 2 项 `find knowledge -name .gitkeep -type f | wc -l` 能捕获 14 个 `.gitkeep` 的数量要求。
- [ ] Step 5 第 13 项的命令与预期不一致：`git status --porcelain | grep '^??' | head -30` 在全新未跟踪目录下通常只显示 `?? knowledge/`，不会列出 22 个新文件；但预期写成"应为 14 + 4 + 1 + 3 = 22 个新文件"。建议改为 `git status --porcelain --untracked-files=all | grep '^?? knowledge/'` 或直接 `find knowledge -type f | sort`，并显式校验文件数 `22`。
- [ ] Step 5 第 12 项只用 `git diff --name-only`，无法捕获未跟踪的白名单外文件；如果误创建了 `tmp.md`，该项仍会输出 `(none)`。建议用 `git status --porcelain --untracked-files=all` 做白名单过滤，例如只允许 `?? knowledge/` 和已有 tracked diff 为空。

### 风险
- `.gitkeep` 要求为空文件，但 Step 5 只检查数量，不检查 0 字节。建议可选增加 `find knowledge -name .gitkeep -type f ! -size 0c`，输出应为空。
- Step 6 commit message 里 `raw/source_manifest.json (空 items)` 与实际 JSON key `sources` 不一致；建议顺手改成"空 sources"，避免历史信息小歧义。

### 结论
- 需修改。主体文件清单、schema 内容和 JSON 默认值都可以进入执行，但 Step 5 第 12 / 13 项需要先修到能准确验证"只创建 knowledge/**"和"22 个新文件"后，再执行 Step 1~7。

## Spec review v2 by codex · 2026-05-27

### v1 阻塞点复核
- [x] Step 5 第 12 项已改为 `git status --porcelain -uall | cut -c4- | grep -v '^knowledge/'`。`-uall` 会展开未跟踪目录，`cut -c4-` 能抽出 porcelain path，过滤 `knowledge/` 后剩余即白名单外文件；可以捕获误创建的未跟踪文件和已修改的非 knowledge 路径。
- [x] Step 5 第 13 项已改为统计 `^knowledge/`，预期 `22` 准确：14 个 `.gitkeep` + 4 个上下文层 md + 1 个 `.wiki-schema.md` + 3 个 JSON。
- [x] Step 5 第 14 项新增按类型分组清单，能人工/机械复核四组文件：`.gitkeep`、上下文层 md、`.wiki-schema.md`、JSON 契约，覆盖全部 22 个应有文件。

### 其它验证机制
- [x] Step 5 第 5/6/7 项依赖 `python3` 做 JSON 合法性和字段解析；当前执行环境有 `/usr/bin/python3`，因此可机械执行。
- [x] JSON 默认值仍符合 RFC-003 Decision：`auto_capture: false`、`exclude_paths: []`、`max_inbox_files: 100`。
- [x] 强约束 #1 / #4 / #9 未被 v2 改弱：只创建 `knowledge/**`、4 个上下文文件无 frontmatter、不创建真实 wiki 页面。

### 非阻塞建议
- 如果未来希望 spec 更跨环境，可给 Step 5 第 5/6/7 项加 `jq` fallback；当前仓库执行环境同时有 `python3` 和 `jq`，不阻塞本 task。
- Step 6 commit message 里 `raw/source_manifest.json (空 items)` 仍可改成"空 sources"更精确，但不影响执行正确性。

### 结论
- 通过。可以进入 Step 1~7。
