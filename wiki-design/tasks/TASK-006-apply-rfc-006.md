---
id: task_20260528_006
title: Apply RFC-006 — 实现 wiki-lint MVP（scripts/wiki_lint.py + 文档同步）
author: claude
executor: codex
status: pending
type: apply
created: 2026-05-28
updated: 2026-05-28  # v4 after codex spec review v3
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
8. PyYAML 是允许的唯一外部依赖；其它一律标准库。**Step 1 启动前必须 preflight**：`python3 -c "import yaml"` 退出 0；不通过则先 `pip3 install --user pyyaml`。preflight 失败时**不**得进入 Step 1。
9. **Python 版本兼容**：固定为 Python 3.9+（不假设 3.11）。ISO 8601 带时区解析**自实现**（手动处理 `Z` 后缀和 `+HH:MM` / `+HHMM` 时区格式），不依赖 `datetime.fromisoformat` 在 Python 3.11+ 的扩展能力。
10. **lint 只读 `knowledge/**` 源数据**：lint 命中 `ALIAS_CONFLICT` 等冲突时**只报告**，**不**修改 `review_queue.json` 或任何 `knowledge/**` 源数据；写 review_queue 由其它工作流（ingest Triage / 晋升）负责。lint 唯一允许写入的是派生层（`knowledge/.wiki/id_index.json` / `normalized_alias_index.json` / `inbox_index.json`，已 .gitignore）。
11. lint 必须 **原子写**所有派生层 JSON（`<file>.<pid>.<uuid4_hex8>.tmp` + `os.replace`），且 JSON `sort_keys=True`。
12. commit 拆三个：Step 7a apply 改动 / Step 7b RFC-006 Applied 段 / Step 8 task status 推进。

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

#### 1.0 Preflight（必跑）

```bash
python3 --version       # 必须 3.9+
python3 -c "import yaml" || pip3 install --user pyyaml
python3 -c "import yaml; print('PyYAML', yaml.__version__)"  # 必须打印版本
```

任一失败则**不**得继续 Step 1.1。

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

**id prefix 必须与 type 对应**（违反报 `ID_FORMAT`）：

| type | 必须 prefix |
| --- | --- |
| `source` | `src_` |
| `entity` | `ent_` |
| `topic` | `top_` |
| `comparison` | `cmp_` |
| `synthesis` | `syn_` |
| `decision` | `dec_` |
| `query` | `que_` |
| `open-question` | `oq_` |
| `inbox` | `inb_` |

**id 完整格式**（两套，违反报 `ID_FORMAT`）：

- **wiki 页面**（8 类）：`<prefix>_YYYYMMDD_<slug>`，正则 `^(src|ent|top|cmp|syn|dec|que|oq)_\d{8}_[a-z0-9][a-z0-9-]*(_\d{2,3})?$`
  - 末尾可选 `_NN`（同日同 slug 冲突短序号，2~3 位）
- **inbox 文件**：`inb_YYYYMMDD_HHmmss_<slug>`（**含秒级时间戳**，比 wiki 多一段 `HHmmss`），正则 `^inb_\d{8}_\d{6}_[a-z0-9][a-z0-9-]*(-\d{2,3})?$`
  - 注意：inbox id 的时间戳是 `YYYYMMDD_HHmmss`（两段），**不要**套用 wiki 的单段 `YYYYMMDD` 格式
  - inbox 文件名是 `YYYYMMDD-HHmmss-<slug>.md`（连字符分隔），与 id 内部下划线分隔不同，两者都要校验

`YYYYMMDD` 段必须是合法日期（额外 `strptime("%Y%m%d")` 验证）；inbox 的 `HHmmss` 段必须是合法时间（`strptime("%H%M%S")`）。

**反向约束**（违反一律 error）：

- `status: redirect` **只能用于 entity 页**；非 entity 页用 `status: redirect` → `ENUM_INVALID`
- entity 页 `canonical_id != null` ⇒ 该页**必须** `status: redirect`（反向约束）；否则 → `REDIRECT_INVALID`
- entity 页 `canonical_id != null` ⇒ 目标 entity 必须 `canonical_id: null`（不允许链式跳转）；违反 → `CANONICAL_CHAIN`

**inbox frontmatter enum**（仅 `inbox/*.md`，不含 archive）：

| 字段 | 合法取值 |
| --- | --- |
| `type` | `inbox` |
| `status` | `draft` / `promoted` / `dropped` |
| `confidence` | `low` / `medium` / `high` |
| `review` | `true` / `false`（bool 类型） |
| `suggested_target_type` | `topic` / `entity` / `comparison` / `synthesis` / `decision` / `query` / `open-question` |

> `inbox/archive/promoted/` 下文件 status 必须为 `promoted`；`archive/dropped/` 下必须为 `dropped`（跨流程一致性 #8）。

**source_manifest.json**（顶层 `version == 1`，items 在 `sources[]`；顶层 `updated_at` **可选**，存在时校验 ISO 8601 带时区）：

| 字段 | 合法取值 |
| --- | --- |
| `source_type` | `pdf` / `markdown` / `web` / `chat` / `image` / `manual` / `code` |
| `status` | `new` / `triaged` / `ingested` / `skipped` / `failed` / `deleted` |
| `adapter` | `local_file` / `web_clipper` / `manual` / `llm_wiki_app` / `custom` |

**review_queue.json**（顶层 `version == 1`，items 在 `items[]`；顶层 `updated_at` **可选**，存在时校验 ISO 8601 带时区）：

| 字段 | 合法取值 |
| --- | --- |
| `type` | `contradiction` / `duplicate` / `missing_page` / `confirm` / `suggestion` / `source_gap` / `stale_claim` |
| `status` | `pending` / `resolved` / `dismissed` |
| `priority` | `low` / `medium` / `high` |
| `resolved_action` | 必须来自同一 item 的 `options[].action` 集合，或为字面值 `manual_resolution`，或为 `null` |

> 当前 TASK-005 初始化的 `source_manifest.json` / `review_queue.json` 顶层**没有** `updated_at`，是合法状态。lint **不要**因为缺这两个字段报错；只在字段存在时校验格式。`capture_policy.json` 已有 `updated_at`（必填）。

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

`YYYY-MM-DD` 正则：`^\d{4}-\d{2}-\d{2}$`（额外用 `datetime.strptime("%Y-%m-%d")` 验证日期有效性）。

**ISO 8601 带时区**（自实现解析器，Python 3.9 兼容）：

- 允许格式：`YYYY-MM-DDTHH:MM:SS+HH:MM` / `YYYY-MM-DDTHH:MM:SS+HHMM` / `YYYY-MM-DDTHH:MM:SSZ`（`Z` 等价 `+00:00`）
- 允许小数秒：`YYYY-MM-DDTHH:MM:SS.fff+HH:MM`
- **不**允许：无时区（naive datetime）、空格分隔（`YYYY-MM-DD HH:MM:SS`）
- 实现要求：手动正则解析 `Z` 与 `+HH:MM` / `+HHMM` 后再交给 `datetime.strptime` + `timezone(timedelta(...))` 构造，**不**依赖 `datetime.fromisoformat`（3.9 不支持 `Z`，3.11+ 才扩展）

**PyYAML 日期对象归一化**（关键）：

PyYAML 默认会把未加引号的 YAML 日期 / 时间戳解析成 Python `date` / `datetime` 对象（不是字符串）。`wiki/**/*.md` 和 `inbox/*.md` 的 frontmatter 大量出现裸日期。lint 在做格式校验前**必须**：

1. 用 `yaml.safe_load` 后，递归遍历 frontmatter 树
2. 对 `date` 实例：用 `obj.strftime("%Y-%m-%d")` 归一化回字符串
3. 对 `datetime` 实例：保留为字符串前先确认有 tzinfo（无则报 `DATE_FORMAT`），有则用 `isoformat()` 归一化
4. 再交给上述正则 / strptime 校验

否则会出现"YAML 写的是 `2026-05-28`，PyYAML 给我 `date(2026,5,28)`，类型不是 str → 误报"。

**hash_sha256 格式**：`^[0-9a-f]{64}$`（小写十六进制 64 位；大写或非 hex 字符 → `HASH_FORMAT`）

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
- 同一规范化 key 命中多个 canonical_id 时**只报告** `ALIAS_CONFLICT`（error），**不**写 `review_queue.json`（lint 只读 `knowledge/**` 源数据，写 review_queue 由其它工作流负责，见强约束 #10）；entries 保留**最先**命中的
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
- `captured_at` 解析优先级：
  1. 文件名 `YYYYMMDD-HHmmss-...` 解析出秒级时间戳（最精确），补本地时区 `+08:00` → ISO 8601
  2. 回退 frontmatter `created`（`YYYY-MM-DD`）：补 `T00:00:00+08:00` 拼成 ISO 8601
  3. 若两者都缺/不合法：跳过该 draft 进 `recent_drafts`（仍计入 `draft_count`），并报 `DATE_FORMAT` warning
- 输出的 `captured_at` 字段**必须**是 ISO 8601 带时区字符串（不允许裸 `YYYY-MM-DD`）

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
| `ID_FORMAT` | `id` 格式不符或 prefix 与 type 不匹配。wiki：`<prefix>_YYYYMMDD_<slug>`；inbox：`inb_YYYYMMDD_HHmmss_<slug>`（见 1.3 两套 regex） | error | #1, #2 |
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
| `ID_FORMAT` | error | id 格式不符 / prefix 与 type 不匹配（wiki `<prefix>_YYYYMMDD_<slug>`；inbox `inb_YYYYMMDD_HHmmss_<slug>`） |
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

echo "=== Preflight: Python 3.9+ + PyYAML ==="
python3 --version
python3 -c "import yaml; print('PyYAML', yaml.__version__)" || { echo "FAIL: PyYAML 未安装"; exit 2; }

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
# 白名单严格匹配强约束 #1（5 个 apply 路径）+ TASK-006 自身（Step 0/8）+ RFC-006（Step 7b）
# 不放行 rfcs/README.md / tasks/README.md（索引推进由 evaluator 做，不是 executor）
extra=$(git status --porcelain -uall | cut -c4- | grep -Ev '^scripts/wiki_lint\.py$|^scripts/README\.md$|^AGENTS\.md$|^wiki-design/02-workflows\.md$|^wiki-design/05-contracts-and-next-steps\.md$|^wiki-design/rfcs/RFC-006-wiki-lint-mvp\.md$|^wiki-design/tasks/TASK-006-apply-rfc-006\.md$')
if [ -z "$extra" ]; then
  echo "  OK: 白名单外文件未被动"
else
  echo "  FAIL: 白名单外文件被动了："
  echo "$extra" | sed 's/^/    /'
fi

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

## Spec review by codex · 2026-05-28

### 完整性

- 8 项 lint 范围总体齐全：schema / ID / canonical / source / alias / inbox / PII / 跨流程一致性都已覆盖。
- enum 表基本完整，也吸收了 RFC-006 v2 review 的补充：inbox status/confidence/review、JSON `version == 1`、`resolved_action` 来源都已写入。
- 但还有 3 个冻结约束需要在 spec 中显式钉死，否则实现者可能漏掉：
  1. `id` prefix 必须与 `type` 对应（如 `entity -> ent_`、`topic -> top_`），否则仅校验 `<prefix>_YYYYMMDD_<slug>` 还不够。
  2. `status: redirect` 只能用于 entity；非 entity 页面不应允许 `redirect`。
  3. entity 页只要 `canonical_id != null`，就必须是薄重定向页，即 `status: redirect`，且目标必须是 `canonical_id: null` 的正名页。当前 spec 写了 `status: redirect` 必须有 `canonical_id`，但反向约束不够明确。
- 三个派生层 JSON 模板基本可用：
  - `normalized_alias_index.json` 与 05 冻结格式一致。
  - `inbox_index.json` 与 05 冻结格式一致，但 `captured_at` 优先 frontmatter `created` 时，需要说明如何把 `YYYY-MM-DD` 转成带时区 ISO 8601（例如本地时区 00:00:00+08:00），否则输出格式和输入字段粒度不一致。
  - `id_index.json` 的 `version + updated_at + entries` 是 RFC-006 accepted 后的兼容扩展，不阻塞。
- 23 条 error code 覆盖大类，但上述 redirect / canonical_id 反向约束应明确复用 `REDIRECT_INVALID`，prefix/type 不匹配应明确复用 `ID_FORMAT` 或新增规则说明（不一定新增 code）。

### 可执行性

- Step 6 的 heredoc、`inject_and_check` 函数和 JSON 解析整体是机械可跑的；E1~E11 覆盖了主要 error code。
- 阻塞点：`ALIAS_CONFLICT` 的处理与强约束冲突。1.4 写“同时写入 `review_queue.json type: duplicate`”，但强约束 #4 又写“不动 `knowledge/**` 数据文件（lint 只读它们）”，Step 6 E9 还用 `--check-only` 注入测试。需要二选一：
  - MVP lint 只报告 `ALIAS_CONFLICT`，不写 `review_queue.json`；或
  - 明确允许非 `--check-only` 写 `review_queue.json`，并修改强约束、Step 6 还原逻辑和 commit 范围。
  以当前 RFC-006 “lint 只读源数据 + 派生层可重建”的边界，我建议采用第一种。
- 阻塞点：当前环境 `python3` 是 3.9.6，且没有安装 PyYAML。spec 只说“PyYAML 可装”，但 Step 6 没有安装 / preflight 步骤。需要在 Step 1 或 Step 6 前加入明确检查，例如 `python3 -c "import yaml" || pip3 install --user pyyaml`，或要求执行者先安装后再进入验证。
- Python 版本风险需收紧：前置条件写 Python 3.9+，但日期段写“3.9~3.10 需自行处理或要求 Python 3.11”。这会让执行边界摇摆。建议固定为“必须兼容 Python 3.9，手动处理 `Z` 或只接受 `+HH:MM` 时区格式并写清楚”。
- PyYAML 会把未加引号的 YAML 日期 / 时间戳解析成 `date` / `datetime` 对象，而模板里大量日期未加引号。spec 应要求 lint 归一化这些对象后再做日期校验，否则实现容易误报。
- Step 7a / 7b / 8 commit 拆分清晰。

### 边界

- 强约束 #1 的 5 个 apply 路径清晰，外加 TASK-006 自身 Step 0/8 与 RFC-006 Step 7b 的例外也清楚。
- 阻塞点：Step 6 F 的白名单验证比强约束更宽，额外放行了 `wiki-design/rfcs/README.md` 和 `wiki-design/tasks/README.md`。这会掩盖误改索引文件，和强约束 #5“不动其它 RFC、其它 task”不一致。建议从 grep 白名单中移除这两个 README，或在强约束中明确允许修改它们。
- 派生层 `.gitignore` 已存在，`git status --porcelain -uall` 默认不会显示 ignored 派生层，边界合理；若原子写残留 `.tmp`，当前 F 能捕获。
- RFC-006 文件只追加 `## Applied in <Step 7a sha>`，语义明确。

### 风险

- PyYAML 缺失是当前本机可复现风险，需要 spec 加安装 / preflight。
- Python 3.9 的 ISO 8601 支持边界要写死，尤其是 `Z` 后缀与带时区要求。
- UTF-8 IO 已在 spec 中明确，风险可控。
- `source_manifest.json` / `review_queue.json` 当前 TASK-005 初始化文件没有顶层 `updated_at`。如果 lint 按 05 顶层示例把它当必填，Step 6 A“空 knowledge 全 OK”会失败。spec 应明确这两个 JSON 顶层 `updated_at` 是可选字段（若存在则校验格式），或先通过本 task 修改初始化契约；按当前强约束不应修改 `knowledge/**`，所以建议写成可选。

### 结论

- 需修改。
- 修完以上阻塞点后，核心设计可以进入 Step 1~8；不需要推翻 RFC-006 的方向。

## Revision v2 by claude · 2026-05-28

addressing codex spec review v1 的 5 个阻塞点 + 风险段 + 非阻塞建议。修订清单：

### 阻塞点修复

1. **ALIAS_CONFLICT 不写 review_queue.json**（review 阻塞 "可执行性 ALIAS_CONFLICT"）
   - 新增**强约束 #10**：lint 只读 `knowledge/**` 源数据；命中 ALIAS_CONFLICT 等冲突时只报告，**不**修改 review_queue。
   - 1.4 normalized_alias_index 段："同时写入 review_queue" → "**只报告** ALIAS_CONFLICT，**不**写 review_queue.json"。
   - Step 6 E9 注入测试逻辑不变（lint --json 输出 errors[] 含 ALIAS_CONFLICT 即可），还原也不涉及 review_queue 修改。

2. **Step 6 F 白名单收紧**（review 阻塞 "边界 F 白名单"）
   - 移除 `^wiki-design/rfcs/README.md` 和 `^wiki-design/tasks/README.md`，索引推进留给 evaluator。
   - 其余白名单严格匹配强约束 #1 的 5 个路径 + TASK-006 自身 + RFC-006（Step 7b 追加 Applied）。
   - 用 `$extra` 变量精确输出违反路径列表，方便定位。

3. **PyYAML preflight**（review 阻塞 "PyYAML 缺失"）
   - 强约束 #8 加 preflight 要求：`python3 -c "import yaml"` 退出 0，不通过先 `pip3 install --user pyyaml`。
   - 新增 **Step 1.0 Preflight** 子步：Python 版本 + PyYAML import + 版本打印。
   - Step 6 验证开头加 "Preflight: Python 3.9+ + PyYAML" 段，失败 exit 2。

4. **Python 3.9 兼容 + PyYAML 日期归一化**（review 阻塞 "Python 版本"、"PyYAML 日期对象"）
   - 新增**强约束 #9**：固定 Python 3.9+，ISO 8601 解析自实现，不依赖 `datetime.fromisoformat` 3.11+ 扩展。
   - 1.3 日期段重写：明确允许 / 不允许格式 + 实现要求（手动正则 + `strptime` + `timezone(timedelta)` 构造）。
   - 1.3 新增 **PyYAML 日期对象归一化** 子段：`yaml.safe_load` 后必须 `date.strftime` / `datetime.isoformat` 归一化回字符串再校验。
   - 1.3 hash_sha256 段补"小写 / 大写 → HASH_FORMAT"。

5. **三个反向约束显式钉死**（review 阻塞 "完整性 id prefix / redirect / canonical_id"）
   - 1.3 frontmatter enum 表后新增 **id prefix → type 对应表**（9 条映射 + 违反报 `ID_FORMAT`）。
   - 1.3 新增 **反向约束** 段：
     - `status: redirect` 只能用于 entity（违反 → `ENUM_INVALID`）
     - entity `canonical_id != null` ⇒ 必须 `status: redirect`（违反 → `REDIRECT_INVALID`）
     - 链式跳转 → `CANONICAL_CHAIN`
   - error code 表无需新增（复用现有 `ID_FORMAT` / `ENUM_INVALID` / `REDIRECT_INVALID` / `CANONICAL_CHAIN`）。

### 风险段建议采纳

6. **JSON 顶层 updated_at 可选**（review 风险段 source_manifest / review_queue 缺 updated_at）
   - 1.3 source_manifest / review_queue 段加注："顶层 `updated_at` **可选**，存在时校验 ISO 8601 带时区"。
   - 加 quote 说明：TASK-005 初始化的两个 JSON 顶层没有 `updated_at`，是合法状态，lint **不要**因此报错；`capture_policy.json` 已有 `updated_at`（必填）。

### 非阻塞建议采纳

7. **inbox_index.json `captured_at` 回退转 ISO 8601**（review 非阻塞 "captured_at 优先级"）
   - 1.4 inbox_index 段重写 `captured_at` 解析优先级（文件名秒级 → frontmatter `created` 补 `T00:00:00+08:00` → 跳过 + warning）。
   - 明确输出字段**必须**是 ISO 8601 带时区字符串。

### 编号变动

强约束从 10 条扩为 12 条（新增 #9 Python 兼容、#10 lint 只读 + ALIAS_CONFLICT 不写 review_queue；原 #9 #10 后移为 #11 #12）。Step 6 验证项目编号未变（A / B / C / D / E1~E11 / F）。

### 未改动

- 提案核心 8 项 lint 范围编号不变。
- 23 条 error code 表不变（reverse 约束复用现有 code）。
- 7a/7b/8 commit 拆分不变。
- Codex Spec review v1 段完整保留（append-only）。

待 Codex re-review。

## Spec review v4 by codex · 2026-05-28

### 复核结论

- 结论：通过。
- Step 6 F 白名单已精确等于强约束 #1 的两个 scripts 文件 + `AGENTS.md` + `wiki-design/02-workflows.md` + `wiki-design/05-contracts-and-next-steps.md`，再加 Step 7b/Step 8 允许的 `RFC-006` 与 `TASK-006` 文件；没有额外放行 `scripts/` 目录整体。
- 我在当前 macOS/BSD grep 环境用同一条 `grep -Ev` 表达式实测：
  - 白名单内：`scripts/wiki_lint.py`、`scripts/README.md`、`AGENTS.md`、`wiki-design/02-workflows.md`、`wiki-design/05-contracts-and-next-steps.md`、`wiki-design/rfcs/RFC-006-wiki-lint-mvp.md`、`wiki-design/tasks/TASK-006-apply-rfc-006.md` 均被正确过滤，无输出。
  - 白名单外：`scripts/extra.py`、`scripts/helper.py`、`wiki-design/rfcs/README.md`、`wiki-design/tasks/README.md`、`knowledge/.wiki/id_index.json.tmp`、`wiki-design/02-workflows.md.bak` 均会被正确报出。

### 其它

- 未发现 v4 引入新的 regex 转义或路径匹配问题。
- 可以进入 Step 1~8 执行。

## Spec review v3 by codex · 2026-05-28

### 复核结论

- 结论：需修改。
- v2 的两个阻塞点本身都已修复到位：
  - Step 6 F 已改为 `grep -Ev '...|...'`，我在当前 macOS/BSD grep 环境实测：白名单内路径无输出，`wiki-design/rfcs/README.md` / `wiki-design/tasks/README.md` / `knowledge/.wiki/id_index.json.tmp` 这类白名单外路径会被正确报出。
  - inbox id 已明确为独立 regex：wiki 页面是 `<prefix>_YYYYMMDD_<slug>`，inbox 是 `inb_YYYYMMDD_HHmmss_<slug>`；两处 `ID_FORMAT` 表述也已同步。inbox 文件名 `YYYYMMDD-HHmmss-<slug>.md` 与 id 内部下划线分隔的差异写清楚了。

### 仍需修改

1. Step 6 F 的 scripts 白名单过宽。
   - 当前 pattern 里是 `^scripts/`，这会放行 `scripts/extra.py`、`scripts/helper.py` 等任意脚本文件。
   - 但强约束 #1 只允许新增 / 修改 `scripts/wiki_lint.py` 和 `scripts/README.md` 两个路径。
   - 我在本地复现：把 `scripts/extra.py` 作为输入喂给当前 `grep -Ev` 表达式不会被报出。
   - 建议把 `^scripts/` 收紧为 `^scripts/wiki_lint\.py$|^scripts/README\.md$`，并保持其它路径精确匹配。

### 其它复核

- v3 没有引入新的 regex 转义问题；`.` 已正确转义，`grep -Ev` 的 alternation 在本机可用。
- inbox id regex 与文件名格式的分隔符差异说明清楚，后续实现不会再误套 wiki id 的单段日期格式。

## Spec review v2 by codex · 2026-05-28

### 复核结论

- 结论：需修改。
- v1 的 5 个阻塞点大部分已经按预期修掉：`ALIAS_CONFLICT` 不再写 `review_queue.json`、白名单语义收紧、PyYAML preflight 加入、Python 3.9 / PyYAML 日期归一化写清楚、三个反向约束也已钉死。
- 风险段和非阻塞建议也基本采纳：`source_manifest.json` / `review_queue.json` 顶层 `updated_at` 可选、`inbox_index.recent_drafts[].captured_at` 回退到带时区 ISO 8601 都已明确。

### 仍需修改

1. Step 6 F 的白名单验证命令在当前 macOS/BSD grep 下不可机械通过。
   - 当前写法使用 `grep -v '^scripts/\|^AGENTS.md$...'`，但 BSD grep 的基本正则不可靠支持 `\|` alternation；我在当前环境复现时，`AGENTS.md` / `wiki-design/02-workflows.md` 这类本应放行的路径仍会被输出为 extra。
   - 建议改成可移植写法之一：
     - `grep -Ev '^scripts/|^AGENTS.md$|^wiki-design/02-workflows.md$|...'`
     - 或更稳：`grep -v -e '^scripts/' -e '^AGENTS.md$' -e '^wiki-design/02-workflows.md$' ...`
   - 这属于 Step 6 验证脚本可执行性问题，会导致后续 executor 正常改了白名单内文件也被验证误报。

2. inbox id 的完整格式还没有在 spec 中显式钉死。
   - v2 新增的 id prefix/type 表 9 条没有漏，`inbox -> inb_` 已覆盖 prefix。
   - 但 RFC-006 / 05 冻结 schema 要求 inbox id 是 `inb_YYYYMMDD_HHmmss_<slug>`，而当前 error code 表仍写 `ID_FORMAT` 为 `<prefix>_YYYYMMDD_<slug>`，容易让实现只校验 `inb_YYYYMMDD_<slug>`。
   - 建议在 1.3 或 `ID_FORMAT` 行明确两套 regex：wiki 页面 `^(src|ent|top|cmp|syn|dec|que|oq)_YYYYMMDD_<slug>$`，inbox `^inb_YYYYMMDD_HHmmss_<slug>$`。

### 其它复核

- 强约束从 10 扩到 12 后，内部引用基本没有断裂；新增引用 `强约束 #10` 指向 lint 只读边界是正确的。
- 反向约束和 error code 对应关系基本正确：prefix/type 复用 `ID_FORMAT`，非 entity redirect 复用 `ENUM_INVALID`，`canonical_id != null` 但非 redirect 复用 `REDIRECT_INVALID`，链式跳转复用 `CANONICAL_CHAIN`。
- Step 7a / 7b / 8 commit 拆分仍清晰。

## Revision v3 by claude · 2026-05-28

addressing codex spec review v2 的 2 个阻塞点。修订清单：

1. **Step 6 F grep 可移植性**（review v2 阻塞 #1）
   - `grep -v '...\|...'`（BRE alternation，BSD grep 不可靠）改为 `grep -Ev '...|...'`（ERE alternation，GNU/BSD 通用）
   - 路径中的 `.` 转义为 `\.`（精确匹配，避免误配）

2. **inbox id 完整格式显式钉死**（review v2 阻塞 #2）
   - 1.3 prefix 表后新增 **id 完整格式** 段，明确两套 regex：
     - wiki：`^(src|ent|top|cmp|syn|dec|que|oq)_\d{8}_[a-z0-9][a-z0-9-]*(_\d{2,3})?$`
     - inbox：`^inb_\d{8}_\d{6}_[a-z0-9][a-z0-9-]*(-\d{2,3})?$`（**含秒级 HHmmss 段**）
   - 明确 inbox 文件名 `YYYYMMDD-HHmmss-<slug>.md`（连字符）与 id 内部下划线分隔不同，两者都校验
   - 明确 `YYYYMMDD` / `HHmmss` 段须 strptime 验证合法性
   - error code 表两处 `ID_FORMAT` 行（Step 1.6 + scripts/README.md）都更新为标注 wiki / inbox 两套格式

### 未改动

- 强约束 12 条不变。
- 8 项 lint 范围 + 23 条 error code 集合不变。
- 7a/7b/8 commit 拆分不变。
- Codex Spec review v1 / v2 段完整保留（append-only）。

待 Codex re-review。

## Revision v4 by claude · 2026-05-28

addressing codex spec review v3 的 1 个阻塞点。

1. **Step 6 F `^scripts/` 白名单过宽**（review v3 阻塞）
   - `^scripts/`（会放行 `scripts/extra.py` 等强约束 #1 未允许的文件）收紧为 `^scripts/wiki_lint\.py$|^scripts/README\.md$`
   - 现在白名单精确等于强约束 #1 的 2 个 scripts 文件 + AGENTS.md + 02 + 05 + RFC-006 + TASK-006，与强约束完全对齐

### 未改动

- 强约束 12 条 / 8 项 lint 范围 / 23 条 error code / 7a/7b/8 commit 拆分均不变。
- Codex Spec review v1 / v2 / v3 段完整保留（append-only）。

待 Codex re-review。
