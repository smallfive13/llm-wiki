---
id: task_20260528_006
title: Apply RFC-006 — 实现 wiki-lint MVP（scripts/wiki_lint.py + 文档同步）
author: claude
executor: codex
status: pending
type: apply
created: 2026-05-28
updated: 2026-05-28
related_rfcs:
  - rfc_20260527_006
---

# TASK-006: Apply RFC-006 — 实现 wiki-lint MVP

## 目标

把 RFC-006（accepted）的 8 项 lint 范围 + 派生层生成 + 文档同步落地。执行完成后：

- 任一 Agent 在改动 `knowledge/wiki/**`、`knowledge/inbox/**`、`knowledge/raw/source_manifest.json`、`knowledge/.wiki/review_queue.json`、`knowledge/.wiki/capture_policy.json` 之后，可跑 `python3 scripts/wiki_lint.py --check-only` 机械校验
- 3 个派生层文件（`id_index.json` / `normalized_alias_index.json` / `inbox_index.json`）由 lint 重建，原子写入，进 `.gitignore`
- AGENTS.md / 02-workflows.md / 05-contracts-and-next-steps.md 同步反映 lint 触发约束 + 第三阶段落地状态

## 前置条件

- 仓库根目录：`/Users/zhangjunwu/workspace/llm-wiki/llm-wiki`
- HEAD 包含 **RFC-006 status: accepted**（commit `db255b9` 及之后）
- working tree clean
- 已读 `wiki-design/rfcs/RFC-006-wiki-lint-mvp.md` 全文（含 v1 review / v2 / v2 review / Decision）
- 已读 `wiki-design/05-contracts-and-next-steps.md` 中 Source Manifest / Review Queue / Capture Item / Capture Policy / Inbox Index / Normalized Alias Index 六段 Schema
- 已读 TASK-002/003/004/005 Evaluation（理解 apply 类 task 工作流惯例）
- Python 3.9+ 可用；PyYAML 可装（`pip3 install pyyaml`）

## 强约束

违反任一即视为执行失败：

1. **只动以下 5 个路径**：
   - `scripts/wiki_lint.py`（新建）
   - `scripts/README.md`（新建）
   - `AGENTS.md`（追加一节）
   - `wiki-design/02-workflows.md`（局部改动）
   - `wiki-design/05-contracts-and-next-steps.md`（局部改动）
2. **本 TASK-006 文件本身**按 Step 0 / 8 允许编辑（追加 Spec review、推进 status、追加 Execution log）。
3. **RFC-006 文件**按 Step 7b 允许追加 `## Applied in <commit-sha>` 段（一行），不动正文。
4. **不动** `knowledge/**` 数据文件（lint 只读它们；派生层在 `.wiki/`，已 .gitignore，**不要 commit**）。
5. **不动** 其它 RFC、其它 task、wiki-design 其它文档、`.gitignore`、`knowledge/.wiki-schema.md`。
6. **必须先经 Codex spec review（Step 0）**：在 Step 0 通过前 status 保持 pending。
7. `scripts/wiki_lint.py` 严格按本 spec 的 enum 列表 / 派生层 schema / error code 表实现，**不**自行扩展规则或字段。
8. PyYAML 是允许的唯一外部依赖；其它一律标准库。
9. lint 必须 **原子写**所有派生层 JSON（`<file>.<pid>.<uuid4_hex8>.tmp` + `os.replace`），且 JSON `sort_keys=True`。
10. commit 拆三个：Step 7a apply 改动 / Step 7b RFC-006 Applied 段 / Step 8 task status 推进。

## 工作流

```
Step 0  Codex spec review (本 task 文件，追加 Spec review 段) + 单独 commit
        │
        │  通过 → Step 1
        │  需修改 → Claude 改 spec → 重新进入 Step 0
        │
        ▼
Step 1  实现 scripts/wiki_lint.py
        │
        ▼
Step 2  写 scripts/README.md
        │
        ▼
Step 3  改 AGENTS.md (新增「lint 触发约束」段)
        │
        ▼
Step 4  改 wiki-design/02-workflows.md (运行 lint → 具体命令)
        │
        ▼
Step 5  改 wiki-design/05-contracts-and-next-steps.md (第三阶段 lint 落地)
        │
        ▼
Step 6  自检验证 (空 knowledge/ 全 OK + 派生层 JSON 合法 + 11 项错误注入测试)
        │
        ▼
Step 7a Commit apply 改动 [apply rfc-006]
        │
        ▼
Step 7b RFC-006 末尾追加 ## Applied in <Step 7a sha> + commit [rfc-006]
        │
        ▼
Step 8  推进本 task status pending → done + 追加 Execution log + commit [task]
```

## 步骤

### Step 0：Spec review（执行前必跑）

在本 task 文件末尾追加：

```markdown
## Spec review by codex · 2026-05-28

### 完整性
- [ ] 8 项 lint 范围是否齐全（schema + ID + canonical + source + alias + inbox + PII + 跨流程）
- [ ] enum 列表（含 v2 codex 3 条补充：inbox status/confidence/review、JSON version==1、resolved_action 来源）是否完整
- [ ] 三个派生层 JSON 模板是否与 05 已冻结 schema 一致
- [ ] error code 表是否覆盖每个 lint 大类

### 可执行性
- [ ] 11 项错误注入测试用例是否机械可跑
- [ ] Step 6 验证脚本是否能直接 bash 执行
- [ ] Step 7a/7b/8 commit 拆分是否清晰

### 边界
- [ ] 5 个 white list 路径是否清晰（其它一律不动）
- [ ] 派生层在 .gitignore 中是否真不会被 commit 进去
- [ ] RFC-006 文件只追加 Applied 段是否够明确

### 风险
- 列出可能踩坑的地方（如 PyYAML 不可用 / Python 版本 / encoding）

### 结论
- 通过 / 需修改 (列出建议)
```

Codex 自行 commit 这次 Spec review 改动（commit message：`[task] TASK-006 spec review by codex (conclusion: <通过/需修改>)`）。

### Step 1：实现 `scripts/wiki_lint.py`

#### 1.1 文件位置与基本约束

- 路径：`scripts/wiki_lint.py`
- Shebang：`#!/usr/bin/env python3`
- Python 3.9+
- 依赖：标准库 + `PyYAML`（仅此）
- 单文件实现（约 600~800 行），允许内部用 dataclass / 函数分组组织代码
- 所有 IO 用 UTF-8 显式声明
- 工作根目录：脚本自检测，确保从仓库根（含 `knowledge/`）跑

#### 1.2 CLI 接口

```
python3 scripts/wiki_lint.py [--check-only] [--json] [--scan-wiki-pii]
```

| 选项 | 含义 |
| --- | --- |
| （无） | 校验 + 重建派生层 |
| `--check-only` | 只校验，不写派生层 |
| `--json` | 输出固定 JSON 结构（见 1.5），与人类可读互斥 |
| `--scan-wiki-pii` | 默认只扫 `inbox/*.md`；加此开关后额外扫 `wiki/**/*.md` |

退出码：

- `0` = 所有 error 段为空（warning 可有）
- `1` = 有 error
- `2` = 配置 / 脚本自身错误（如 PyYAML 缺失、JSON 解析失败、knowledge/ 不存在等）

#### 1.3 校验范围与 enum 列表

实现 RFC-006 v2 范围 #1~#8 的全部 8 项。各 enum 字段必须严格按下表校验（**不**接受其它值）：

**wiki 页面 frontmatter enum**（仅校验 `wiki/**/*.md`，4 个上下文层 md 反向校验"无 frontmatter"）：

| 字段 | 合法取值 |
| --- | --- |
| `type` | `source` / `entity` / `topic` / `comparison` / `synthesis` / `decision` / `query` / `open-question` |
| `status` | `draft` / `active` / `stale` / `archived` / `redirect` |
| `confidence` | `low` / `medium` / `high` |
| `review` | `true` / `false`（bool 类型） |

**inbox frontmatter enum**（仅 `inbox/*.md`，不含 archive）：

| 字段 | 合法取值 |
| --- | --- |
| `type` | `inbox` |
| `status` | `draft` / `promoted` / `dropped` |
| `confidence` | `low` / `medium` / `high` |
| `review` | `true` / `false`（bool 类型） |
| `suggested_target_type` | `topic` / `entity` / `comparison` / `synthesis` / `decision` / `query` / `open-question` |

> `inbox/archive/promoted/` 下文件 status 必须为 `promoted`；`archive/dropped/` 下必须为 `dropped`（跨流程一致性 #8）。

**source_manifest.json**（顶层 `version == 1`，items 在 `sources[]`）：

| 字段 | 合法取值 |
| --- | --- |
| `source_type` | `pdf` / `markdown` / `web` / `chat` / `image` / `manual` / `code` |
| `status` | `new` / `triaged` / `ingested` / `skipped` / `failed` / `deleted` |
| `adapter` | `local_file` / `web_clipper` / `manual` / `llm_wiki_app` / `custom` |

**review_queue.json**（顶层 `version == 1`，items 在 `items[]`）：

| 字段 | 合法取值 |
| --- | --- |
| `type` | `contradiction` / `duplicate` / `missing_page` / `confirm` / `suggestion` / `source_gap` / `stale_claim` |
| `status` | `pending` / `resolved` / `dismissed` |
| `priority` | `low` / `medium` / `high` |
| `resolved_action` | 必须来自同一 item 的 `options[].action` 集合，或为字面值 `manual_resolution`，或为 `null` |

**capture_policy.json**：

| 字段 | 约束 |
| --- | --- |
| `version` | 必须 == `1` |
| `auto_capture` | 必须是 `bool` |
| `exclude_paths` | 必须是 `array<string>` |
| `exclude_patterns` | 必须是 `array<string>` |
| `max_inbox_files` | 必须是正整数 |

**日期格式**：

| 字段位置 | 格式 |
| --- | --- |
| wiki 页 `created` / `updated` / `last_verified` | `YYYY-MM-DD` |
| inbox `created` | `YYYY-MM-DD` |
| 三个 JSON 中 `imported_at` / `last_ingested_at` / `updated_at` / `created_at` / `resolved_at` / `captured_at` | 带时区 ISO 8601 或 `null`（`null` 仅在字段允许时） |

`YYYY-MM-DD` 正则：`^\d{4}-\d{2}-\d{2}$`（额外用 `datetime.strptime` 验证日期有效性）
ISO 8601 带时区：解析后必须有 `tzinfo`（用 `datetime.fromisoformat` Python 3.11+；3.9~3.10 需自行处理或要求 Python 3.11）

**hash_sha256 格式**：`^[0-9a-f]{64}$`

#### 1.4 派生层 JSON 模板（严格按 05 冻结 schema）

每次跑 lint（不带 `--check-only`）必须重建以下三个文件：

**`knowledge/.wiki/id_index.json`**：

```json
{
  "version": 1,
  "updated_at": "<ISO 8601 with tz>",
  "entries": {
    "<id>": {
      "path": "<相对 knowledge/ 的 wiki/.../xx.md>",
      "type": "<page type>",
      "status": "<page status>"
    }
  }
}
```

- entries key 按字典序排序
- 空时 `entries = {}`

**`knowledge/.wiki/normalized_alias_index.json`**：

```json
{
  "version": 1,
  "updated_at": "<ISO 8601 with tz>",
  "entries": {
    "<normalized key>": {
      "canonical_id": "<ent_...>",
      "matched_form": "<原始未规范化字符串>",
      "source": "title | alias | redirect"
    }
  }
}
```

- 来源优先级：`title`（H1 标题）> `alias`（`aliases[]` 字段）> `redirect`（薄重定向页 `id`）
- 同一规范化 key 命中多个 canonical_id 时报 `ALIAS_CONFLICT` 并写入 review_queue（见下文）；entries 保留**最先**命中的
- 规范化算法：lowercase + 去首尾空白 + 连续空白→单空格 + `_`/`-`/空格互换为 `-` + 中文全角→半角（仅 `，。（）！？：；""''`）。**不**做复数归一（MVP 不引入歧义）。
- 空时 `entries = {}`

**`knowledge/.wiki/inbox_index.json`**：

```json
{
  "version": 1,
  "draft_count": 0,
  "oldest_draft_age_days": null,
  "recent_drafts": [
    {
      "filename": "20260526-153012-attention-complexity.md",
      "summary": "Attention 复杂度讨论",
      "captured_at": "2026-05-26T15:30:12+08:00"
    }
  ],
  "updated_at": "<ISO 8601 with tz>"
}
```

- `draft_count` = `inbox/*.md` 中 `status: draft` 文件数（**不含** archive）
- `oldest_draft_age_days` = 最老 draft 距今天数（按 frontmatter `created`）；无 draft 时为 `null`
- `recent_drafts` 默认 N = 10，按 `captured_at` 倒序
- `summary` 优先 frontmatter `suggested_target_title`；回退正文首行非空文本（截断 80 字符）
- `captured_at` 优先 frontmatter `created`，回退按文件名 `YYYYMMDD-HHmmss-...` 解析

**原子写算法**（所有派生层强制）：

```python
import os, json, uuid, tempfile

def atomic_write_json(path: str, data: dict) -> None:
    pid = os.getpid()
    suffix = uuid.uuid4().hex[:8]
    tmp = f"{path}.{pid}.{suffix}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)
```

**禁止**使用固定 `<file>.tmp`（两进程并发会踩）。

#### 1.5 输出格式

**人类可读**（默认）：

```
wiki-lint v0.1.0
================
扫描: knowledge/wiki/ (N 文件) · knowledge/inbox/ (M 文件) · knowledge/raw/ (K source)

[OK | FAIL]  schema 校验: a/b 页通过
[OK | FAIL]  ID 唯一性: N 个 id（无冲突 | C 个冲突）
[OK | FAIL]  canonical 引用 + supersedes 对称: ...
[OK | FAIL]  source 单主键: ...
[OK | FAIL]  entity 别名（含链式跳转 / status:redirect）: ...
[OK | FAIL]  inbox: M draft
[OK | FAIL]  PII 扫描（inbox-only | inbox + wiki）: H 命中

派生层已重建（原子写入）:
  .wiki/id_index.json (E entries)
  .wiki/normalized_alias_index.json (E entries)
  .wiki/inbox_index.json (D drafts)

详细错误：
  [ERROR] <CODE> <file>:<line> <field>: <message>
                 hint: <hint>
  ...

详细警告：
  [WARN]  ...

错误: X · 警告: Y
```

`--check-only` 时不写派生层，输出末尾改为：`派生层未重建（--check-only）`。

**JSON 输出**（`--json`）—— 固定结构：

```json
{
  "wiki_lint_version": "0.1.0",
  "ran_at": "<ISO 8601 with tz>",
  "scanned": {
    "wiki_pages": 0,
    "inbox_drafts": 0,
    "inbox_archived": 0,
    "sources": 0,
    "review_queue_items": 0
  },
  "errors": [
    {
      "code": "ID_DUPLICATE",
      "file": "wiki/entities/foo.md",
      "line": 3,
      "field": "id",
      "message": "...",
      "hint": "..."
    }
  ],
  "warnings": [],
  "derived_layers": {
    "id_index_entries": 0,
    "normalized_alias_index_entries": 0,
    "inbox_index_drafts": 0,
    "written": true
  }
}
```

- 每条 `errors[]` / `warnings[]` 必须含 6 字段；缺字段时该项为 `null`（**不**省略字段）
- `derived_layers.written = false` 表示 `--check-only` 模式

#### 1.6 完整 error code 表

实现这些 code（UPPER_SNAKE_CASE）。**新增 code 不允许**，本 spec 是封闭集合：

| code | 触发条件 | 级别 | 关联范围项 |
| --- | --- | --- | --- |
| `MISSING_FIELD` | frontmatter 缺必填字段 | error | #1 |
| `EXTRA_FRONTMATTER` | 4 个上下文层 md 误带 frontmatter | error | #1 |
| `ID_FORMAT` | `id` 不符 `<prefix>_YYYYMMDD_<slug>` | error | #1, #2 |
| `ID_DUPLICATE` | 同 `id` 在多文件出现 | error | #2 |
| `ENUM_INVALID` | 字段值不在合法 enum | error | #1 |
| `DATE_FORMAT` | 日期不符 `YYYY-MM-DD` 或非 ISO 8601 带时区 | error | #1 |
| `HASH_FORMAT` | hash_sha256 不是 64 位小写十六进制 | error | #1, #4 |
| `JSON_VERSION` | JSON 顶层 `version != 1` | error | #1 |
| `TYPE_MISMATCH` | 字段类型不对（如 `auto_capture` 非 bool） | error | #1 |
| `CANONICAL_DANGLING` | canonical 字段引用的 id 在 id_index 找不到 | error | #3 |
| `SUPERSEDES_ASYMMETRY` | supersedes / superseded_by 单向缺失 | error | #3 |
| `SOURCE_KEY_MISMATCH` | source 页 `id != source_id` 或 manifest 三者不一致 | error | #4 |
| `SUMMARY_PATH_MISSING` | summary_page_path 文件不存在 | error | #4 |
| `ALIAS_CONFLICT` | 同一规范化 alias key 映射多个 canonical_id | error | #5 |
| `CANONICAL_CHAIN` | canonical_id 指向非正名页（A→B→C） | error | #5 |
| `REDIRECT_INVALID` | status:redirect 但 canonical_id 缺失或无效 | error | #5 |
| `RESOLVED_ACTION_INVALID` | review_queue.resolved_action 不来自 options.action / manual_resolution / null | error | #1 |
| `INBOX_STATUS_PATH_MISMATCH` | archive/promoted 下 status 非 promoted（dropped 同理） | error | #8 |
| `REVIEW_QUEUE_PATH_DRIFT` | review_queue.evidence.page_path 与 id_index 当前路径不一致 | warning | #8 |
| `STATUS_NOT_ARCHIVED` | 被 superseded 的页 status 不是 archived | warning | #3 |
| `PII_HIT_DRAFT` | inbox draft 命中 PII 正则 | error | #7 |
| `PII_HIT_ARCHIVE` | inbox archive 命中 PII 正则 | warning | #7 |
| `PII_HIT_WIKI` | wiki/ 命中 PII 正则（仅 `--scan-wiki-pii`） | warning | #7 |

### Step 2：写 `scripts/README.md`

完整内容：

```markdown
# scripts/

仓库工具脚本。当前仅 wiki-lint MVP。

## wiki-lint

实现：见 [`wiki_lint.py`](wiki_lint.py)
设计：见 [`../wiki-design/rfcs/RFC-006-wiki-lint-mvp.md`](../wiki-design/rfcs/RFC-006-wiki-lint-mvp.md)

### 安装依赖

\`\`\`bash
pip3 install pyyaml
\`\`\`

Python 3.9+ 必需。

### 用法

\`\`\`bash
python3 scripts/wiki_lint.py                  # 校验 + 重建派生层
python3 scripts/wiki_lint.py --check-only     # 只校验，不写派生层
python3 scripts/wiki_lint.py --json           # 机器可读输出
python3 scripts/wiki_lint.py --scan-wiki-pii  # 加扫 wiki/ PII（默认只扫 inbox）
\`\`\`

退出码：

- `0` = 所有 error 为空（warning 可有）
- `1` = 有 error
- `2` = 配置 / 脚本自身错误

### 覆盖的 lint 范围（8 项）

来自 RFC-006 v2 范围 #1~#8：

1. **schema 校验** — frontmatter 必填字段 + enum + 日期格式 + hash 格式
2. **ID 唯一性** — `<prefix>_YYYYMMDD_<slug>` 全局唯一 + 派生 `.wiki/id_index.json`
3. **canonical 引用 + supersedes 对称** — 所有 ID 引用可解析 + 双向对称
4. **source 单主键** — `source_id == id == summary_page_id`
5. **entity 别名** — alias 唯一 + canonical_id 不链式 + 派生 `.wiki/normalized_alias_index.json`
6. **inbox 派生** — `.wiki/inbox_index.json`
7. **PII 扫描** — 按 `capture_policy.exclude_patterns`
8. **跨流程一致性** — manifest ↔ 摘要页 / review_queue path / inbox archive 状态

### 完整 error code 表

| code | 级别 | 含义 |
| --- | --- | --- |
| `MISSING_FIELD` | error | frontmatter 缺必填字段 |
| `EXTRA_FRONTMATTER` | error | 上下文层 md 误带 frontmatter |
| `ID_FORMAT` | error | id 格式不符 |
| `ID_DUPLICATE` | error | id 在多文件出现 |
| `ENUM_INVALID` | error | 字段值不在合法 enum |
| `DATE_FORMAT` | error | 日期格式不符 |
| `HASH_FORMAT` | error | hash_sha256 不是 64 位小写 hex |
| `JSON_VERSION` | error | JSON 顶层 version != 1 |
| `TYPE_MISMATCH` | error | 字段类型不对 |
| `CANONICAL_DANGLING` | error | 引用 id 找不到 |
| `SUPERSEDES_ASYMMETRY` | error | supersedes / superseded_by 单向缺失 |
| `SOURCE_KEY_MISMATCH` | error | source 主键三者不一致 |
| `SUMMARY_PATH_MISSING` | error | summary_page_path 文件不存在 |
| `ALIAS_CONFLICT` | error | 别名映射多个 canonical_id |
| `CANONICAL_CHAIN` | error | canonical_id 指向非正名页 |
| `REDIRECT_INVALID` | error | status:redirect 但 canonical_id 缺失/无效 |
| `RESOLVED_ACTION_INVALID` | error | resolved_action 来源不合法 |
| `INBOX_STATUS_PATH_MISMATCH` | error | archive 路径与 status 不匹配 |
| `REVIEW_QUEUE_PATH_DRIFT` | warning | evidence.page_path 偏离当前路径 |
| `STATUS_NOT_ARCHIVED` | warning | 被 superseded 但 status 不是 archived |
| `PII_HIT_DRAFT` | error | inbox draft 命中 PII |
| `PII_HIT_ARCHIVE` | warning | inbox archive 命中 PII |
| `PII_HIT_WIKI` | warning | wiki/ 命中 PII（仅 `--scan-wiki-pii`） |

### 派生层

由 lint 生成，**进 `.gitignore`**，可重建：

- `knowledge/.wiki/id_index.json`
- `knowledge/.wiki/normalized_alias_index.json`
- `knowledge/.wiki/inbox_index.json`

派生层写入采用原子模式（同目录唯一临时文件 + `os.replace`），多进程并发安全。

### 调用约定

- ingest Apply / inbox 晋升 apply / 结晶化 完成后**必须**跑 lint，error 时回滚或转入 review_queue
- commit 前建议 `python3 scripts/wiki_lint.py --check-only`
- MVP 不强制 pre-commit hook（留给后续 RFC）

### MVP 不覆盖

见 RFC-006 v2「范围（MVP 不包含）」段：

- auto-fix
- pre-commit / CI 集成
- wiki-context / wiki-graph-refresh
- 健康度评分 / overview.md 自动更新
- wiki-design/rfcs/** / tasks/** 流程层 lint
- hash_sha256 实际值比对
\`\`\`

> 注：上面 markdown 中的 ` ``` ` 围栏在写入文件时是真实代码围栏，不是转义。

### Step 3：改 AGENTS.md

在 `## Commit 规则` 段之前**新增**一节（位置：现有 `## 知识库写入规则` 段之后、`## Commit 规则` 段之前）。

完整新增内容：

```markdown
## lint 触发约束

机制定义见 [RFC-006](wiki-design/rfcs/RFC-006-wiki-lint-mvp.md)。

任何对以下路径的修改，commit 前必须跑 `python3 scripts/wiki_lint.py --check-only` 通过：

- `knowledge/wiki/**`
- `knowledge/inbox/**`
- `knowledge/raw/source_manifest.json`
- `knowledge/.wiki/review_queue.json`
- `knowledge/.wiki/capture_policy.json`

派生层文件（`knowledge/.wiki/id_index.json` / `normalized_alias_index.json` / `inbox_index.json`）由 lint 自动生成，不需要手动维护，也不进 Git。

lint 输出 error 时，应优先修复源数据；确实需要绕过时，必须在 commit message 或 Execution log 段写明绕过原因。

```

### Step 4：改 `wiki-design/02-workflows.md`

修改全部"运行 lint"或单独 "lint" 的指令性出现，统一为 `运行 \`python3 scripts/wiki_lint.py\``。当前已知 hit：

- 第 90 行附近（"摄入资料" Apply 阶段）："运行 lint" → "运行 `python3 scripts/wiki_lint.py`"

执行前先 `grep -n "lint" wiki-design/02-workflows.md` 列出全部出现位置，对**指令性**出现（"运行 lint"、"跑一下 lint"、"lint 一下"等）统一替换。**说明性**出现（如"由 lint 校验"）保持不变。

具体改动以 Codex 执行时实际 grep 结果为准，但**只动指令性句子**，不动表格、不动说明性段落。

### Step 5：改 `wiki-design/05-contracts-and-next-steps.md`

#### 5.1 第三阶段段落标注落地

找到这段（约第 815~826 行）：

```markdown
### 第三阶段：补最小脚本

交付物：

- `scripts/wiki-lint`：检查 frontmatter、断链、source manifest、review queue。
- `scripts/wiki-context`：输出 Agent 会话开始要读的高密度上下文。
- `scripts/wiki-graph-refresh`：生成 `maps/graph-data.json` 和 `maps/graph-insights.md`。
```

在该段第一行（`### 第三阶段：补最小脚本` 之后、`交付物：` 之前）插入一行状态标注：

```markdown
> **状态（2026-05-28）**：`scripts/wiki-lint` 已由 RFC-006 + TASK-006 落地为 `scripts/wiki_lint.py`，覆盖 frontmatter / 断链 / source manifest / review queue / entity alias / inbox / PII 八类校验，并生成 `id_index.json` / `normalized_alias_index.json` / `inbox_index.json` 三类派生层。`wiki-context` / `wiki-graph-refresh` 仍待后续 RFC。
```

不动该段其它部分。

#### 5.2 其它 lint 引用不动

不动 schema 表、字段约束表、Normalized Alias Index Schema 中 "Decision #2 替代版" 段等说明性 lint 引用。这些是已冻结契约，不归 TASK-006 修。

### Step 6：自检验证

```bash
cd /Users/zhangjunwu/workspace/llm-wiki/llm-wiki

set +e

echo "=== A. 基线：空 knowledge/ 跑 lint 应全 OK ==="
python3 scripts/wiki_lint.py
echo "  exit code: $?  (期望 0)"

echo "=== B. 派生层 JSON 合法 + 顶层 schema ==="
for f in knowledge/.wiki/id_index.json knowledge/.wiki/normalized_alias_index.json knowledge/.wiki/inbox_index.json; do
  if python3 -m json.tool "$f" > /dev/null 2>&1; then
    v=$(python3 -c "import json; print(json.load(open('$f')).get('version'))")
    echo "  OK: $f (version=$v, 应 = 1)"
  else
    echo "  FAIL: $f (invalid JSON)"
  fi
done

echo "=== C. --check-only 不写派生层 ==="
rm -f knowledge/.wiki/id_index.json
python3 scripts/wiki_lint.py --check-only
[ -f knowledge/.wiki/id_index.json ] && echo "  FAIL: id_index 被写了" || echo "  OK: --check-only 未写派生层"

echo "=== D. --json 输出固定结构 ==="
python3 scripts/wiki_lint.py --json | python3 -c "
import json, sys
d = json.load(sys.stdin)
required_top = ['wiki_lint_version', 'ran_at', 'scanned', 'errors', 'warnings', 'derived_layers']
for k in required_top:
  assert k in d, f'缺顶层字段: {k}'
print('  OK: 顶层 6 字段齐全')
for e in d['errors'] + d['warnings']:
  for k in ['code', 'file', 'line', 'field', 'message', 'hint']:
    assert k in e, f'errors/warnings 缺字段 {k}'
print('  OK: errors/warnings 6 字段齐全（空数组也通过）')
"

echo "=== E. 11 项错误注入测试（每项注入 → 验 exit=1 + 期望 code → 还原） ==="

inject_and_check() {
  local desc="$1"
  local expected_code="$2"
  local restore_cmd="$3"
  out=$(python3 scripts/wiki_lint.py --json --check-only 2>/dev/null)
  ec=$?
  hit=$(echo "$out" | python3 -c "import json, sys; d=json.load(sys.stdin); print('YES' if any(e['code']=='$expected_code' for e in d['errors']) else 'NO')")
  if [ "$ec" = "1" ] && [ "$hit" = "YES" ]; then
    echo "  OK: [$expected_code] $desc"
  else
    echo "  FAIL: [$expected_code] $desc (exit=$ec, hit=$hit)"
  fi
  eval "$restore_cmd"
}

# E1. MISSING_FIELD: 新建 wiki/entities/lint_test.md 缺 id
mkdir -p knowledge/wiki/entities
cat > knowledge/wiki/entities/lint_test.md <<'TMP'
---
type: entity
status: active
confidence: medium
created: 2026-05-28
updated: 2026-05-28
last_verified: 2026-05-28
review: false
---
# Lint Test
TMP
inject_and_check "缺 id" "MISSING_FIELD" "rm knowledge/wiki/entities/lint_test.md"

# E2. ID_FORMAT
cat > knowledge/wiki/entities/lint_test.md <<'TMP'
---
id: bad_format
type: entity
status: active
confidence: medium
created: 2026-05-28
updated: 2026-05-28
last_verified: 2026-05-28
review: false
---
# Lint Test
TMP
inject_and_check "id 格式不对" "ID_FORMAT" "rm knowledge/wiki/entities/lint_test.md"

# E3. ENUM_INVALID
cat > knowledge/wiki/entities/lint_test.md <<'TMP'
---
id: ent_20260528_lint-test
type: not_a_type
status: active
confidence: medium
created: 2026-05-28
updated: 2026-05-28
last_verified: 2026-05-28
review: false
---
# Lint Test
TMP
inject_and_check "type 不在 enum" "ENUM_INVALID" "rm knowledge/wiki/entities/lint_test.md"

# E4. DATE_FORMAT
cat > knowledge/wiki/entities/lint_test.md <<'TMP'
---
id: ent_20260528_lint-test
type: entity
status: active
confidence: medium
created: 28/05/2026
updated: 2026-05-28
last_verified: 2026-05-28
review: false
---
# Lint Test
TMP
inject_and_check "created 日期非 YYYY-MM-DD" "DATE_FORMAT" "rm knowledge/wiki/entities/lint_test.md"

# E5. HASH_FORMAT
mkdir -p knowledge/wiki/sources
cat > knowledge/wiki/sources/lint_test.md <<'TMP'
---
id: src_20260528_lint-test
type: source
status: active
confidence: high
created: 2026-05-28
updated: 2026-05-28
last_verified: 2026-05-28
review: false
source_id: src_20260528_lint-test
hash_sha256: zzzzzzzz
original_path: raw/sources/lint_test.txt
source_url: null
imported_at: 2026-05-28T00:00:00+08:00
---
# Lint Test
TMP
inject_and_check "hash 非 64 位 hex" "HASH_FORMAT" "rm knowledge/wiki/sources/lint_test.md"

# E6. SOURCE_KEY_MISMATCH
cat > knowledge/wiki/sources/lint_test.md <<'TMP'
---
id: src_20260528_lint-test
type: source
status: active
confidence: high
created: 2026-05-28
updated: 2026-05-28
last_verified: 2026-05-28
review: false
source_id: src_20260528_different
hash_sha256: 0000000000000000000000000000000000000000000000000000000000000000
original_path: raw/sources/lint_test.txt
source_url: null
imported_at: 2026-05-28T00:00:00+08:00
---
# Lint Test
TMP
inject_and_check "source id != source_id" "SOURCE_KEY_MISMATCH" "rm knowledge/wiki/sources/lint_test.md"

# E7. CANONICAL_DANGLING
cat > knowledge/wiki/entities/lint_test.md <<'TMP'
---
id: ent_20260528_lint-test
type: entity
status: active
confidence: medium
created: 2026-05-28
updated: 2026-05-28
last_verified: 2026-05-28
review: false
related_ids: [ent_20260101_does_not_exist]
---
# Lint Test
TMP
inject_and_check "related_ids 断引" "CANONICAL_DANGLING" "rm knowledge/wiki/entities/lint_test.md"

# E8. SUPERSEDES_ASYMMETRY
cat > knowledge/wiki/entities/lint_test_a.md <<'TMP'
---
id: ent_20260528_a
type: entity
status: archived
confidence: medium
created: 2026-05-28
updated: 2026-05-28
last_verified: 2026-05-28
review: false
superseded_by: [ent_20260528_b]
---
# A
TMP
cat > knowledge/wiki/entities/lint_test_b.md <<'TMP'
---
id: ent_20260528_b
type: entity
status: active
confidence: medium
created: 2026-05-28
updated: 2026-05-28
last_verified: 2026-05-28
review: false
---
# B
TMP
inject_and_check "supersedes 单向" "SUPERSEDES_ASYMMETRY" "rm knowledge/wiki/entities/lint_test_a.md knowledge/wiki/entities/lint_test_b.md"

# E9. ALIAS_CONFLICT
cat > knowledge/wiki/entities/lint_test_a.md <<'TMP'
---
id: ent_20260528_a
type: entity
status: active
confidence: medium
created: 2026-05-28
updated: 2026-05-28
last_verified: 2026-05-28
review: false
aliases: [Foo]
---
# Alpha
TMP
cat > knowledge/wiki/entities/lint_test_b.md <<'TMP'
---
id: ent_20260528_b
type: entity
status: active
confidence: medium
created: 2026-05-28
updated: 2026-05-28
last_verified: 2026-05-28
review: false
aliases: [foo]
---
# Beta
TMP
inject_and_check "两 entity 同 alias 规范化冲突" "ALIAS_CONFLICT" "rm knowledge/wiki/entities/lint_test_a.md knowledge/wiki/entities/lint_test_b.md"

# E10. CANONICAL_CHAIN
cat > knowledge/wiki/entities/lint_test_a.md <<'TMP'
---
id: ent_20260528_a
type: entity
status: redirect
confidence: medium
created: 2026-05-28
updated: 2026-05-28
last_verified: 2026-05-28
review: false
canonical_id: ent_20260528_b
---
# A
TMP
cat > knowledge/wiki/entities/lint_test_b.md <<'TMP'
---
id: ent_20260528_b
type: entity
status: redirect
confidence: medium
created: 2026-05-28
updated: 2026-05-28
last_verified: 2026-05-28
review: false
canonical_id: ent_20260528_c
---
# B
TMP
cat > knowledge/wiki/entities/lint_test_c.md <<'TMP'
---
id: ent_20260528_c
type: entity
status: active
confidence: medium
created: 2026-05-28
updated: 2026-05-28
last_verified: 2026-05-28
review: false
---
# C
TMP
inject_and_check "canonical_id 链式 A→B→C" "CANONICAL_CHAIN" "rm knowledge/wiki/entities/lint_test_a.md knowledge/wiki/entities/lint_test_b.md knowledge/wiki/entities/lint_test_c.md"

# E11. PII_HIT_DRAFT
mkdir -p knowledge/inbox
cat > knowledge/inbox/20260528-000000-lint-test.md <<'TMP'
---
id: inb_20260528_000000_lint-test
type: inbox
status: draft
confidence: low
review: true
suggested_target_type: topic
suggested_target_title: 测试
created: 2026-05-28
---
我的手机号 13800138000
TMP
inject_and_check "inbox draft 含 PII 手机号" "PII_HIT_DRAFT" "rm knowledge/inbox/20260528-000000-lint-test.md"

echo "=== F. 还原 + 重新 baseline ==="
rm -f knowledge/.wiki/id_index.json knowledge/.wiki/normalized_alias_index.json knowledge/.wiki/inbox_index.json
python3 scripts/wiki_lint.py > /dev/null
git status --porcelain -uall | cut -c4- | grep -v '^scripts/\|^AGENTS.md\|^wiki-design/02\|^wiki-design/05\|^wiki-design/rfcs/RFC-006\|^wiki-design/tasks/TASK-006\|^wiki-design/rfcs/README.md\|^wiki-design/tasks/README.md' || echo "  OK: 白名单外文件未被动"

echo "=== 全部验证结束 ==="
```

预期：

- A：exit 0（空 knowledge 全 OK）
- B：3 个派生层 valid JSON，version 全 = 1
- C：`--check-only` 后 id_index 不重生
- D：JSON 顶层 6 字段齐全 + errors/warnings 6 字段齐全
- E1~E11：11 个注入 → 每项 `OK: [<CODE>] ...`，无 FAIL
- F：还原干净，白名单外无未跟踪文件

### Step 7a：Commit apply 改动

```bash
git add scripts/ AGENTS.md wiki-design/02-workflows.md wiki-design/05-contracts-and-next-steps.md

git commit -m "$(cat <<'EOF'
[apply rfc-006] implement wiki-lint MVP

实现 RFC-006 v2 的 8 项 lint 范围：

- schema 校验（含 enum / 日期 / hash 格式）
- ID 唯一性 + 派生 id_index.json
- canonical 引用 + supersedes 对称
- source 单主键
- entity 别名 + 派生 normalized_alias_index.json
- inbox 派生 inbox_index.json
- PII 扫描（默认 inbox-only，--scan-wiki-pii 扩展 wiki/）
- 跨流程一致性（manifest / review_queue / inbox archive 路径）

scripts/:
- wiki_lint.py (~XXX 行)
- README.md (用法 + error code 表 + 安装步骤)

文档同步:
- AGENTS.md +「lint 触发约束」段
- wiki-design/02-workflows.md "运行 lint" → "python3 scripts/wiki_lint.py"
- wiki-design/05-contracts-and-next-steps.md 第三阶段标注落地

实现约束:
- Python 3.9+ + PyYAML 单依赖
- 原子写 (<file>.<pid>.<uuid>.tmp + os.replace)
- JSON sort_keys 确定序
- 派生层进 .gitignore (已由 RFC-002/003/004 配置)

Co-Authored-By: Codex <noreply@openai.com>
EOF
)"
```

### Step 7b：在 RFC-006 末尾追加 Applied 段并 commit

```bash
# 在 wiki-design/rfcs/RFC-006-wiki-lint-mvp.md 末尾追加一行：
# (替换 <Step 7a sha> 为实际值)
```

末尾追加：

```markdown

## Applied in <Step 7a sha>
```

```bash
git add wiki-design/rfcs/RFC-006-wiki-lint-mvp.md
git commit -m "[rfc-006] applied in <Step 7a sha>"
```

### Step 8：推进 task status pending → done

1. 修改本文件 frontmatter `status: pending` → `status: done`
2. `updated:` 改为今天
3. 在文件末尾追加 `## Execution log by codex · 2026-05-28` 段，按"完成后报告格式"填写
4. Commit：

```bash
git add wiki-design/tasks/TASK-006-apply-rfc-006.md
git commit -m "[task] TASK-006 done by codex"
```

## 完成后报告格式

把以下内容贴进 `## Execution log by codex · 2026-05-28` 段：

```markdown
## Execution log by codex · 2026-05-28

### 步骤完成情况
- Step 0 Spec review: 通过
- Step 1 scripts/wiki_lint.py: done (XXX 行)
- Step 2 scripts/README.md: done
- Step 3 AGENTS.md: done
- Step 4 wiki-design/02-workflows.md: done (替换 X 处)
- Step 5 wiki-design/05-contracts-and-next-steps.md: done
- Step 6 验证: 输出见下

### 验证输出
\`\`\`
<Step 6 完整输出>
\`\`\`

### Commit
- Step 7a commit sha: <sha>
- Step 7b commit sha: <sha>
- Step 8 commit sha: 本 commit（实际 sha 由提交后回复报告）

### 偏离 / 异常
<列出与指令不一致的地方；没有就写"无"。验证不完美时在此段解释，不改 spec 或绕过。>
```

## Spec review by codex · YYYY-MM-DD

（待 Codex 在 Step 0 填写）

## Execution log by codex · YYYY-MM-DD

（待执行者在 Step 8 填写）

## Evaluation by claude · YYYY-MM-DD

（待评估者填写）
