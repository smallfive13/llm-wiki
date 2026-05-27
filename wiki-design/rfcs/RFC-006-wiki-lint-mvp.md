---
id: rfc_20260527_006
title: 引入 wiki-lint MVP，闭合 RFC-002/003/004 的约束
author: claude
status: proposed
created: 2026-05-27
updated: 2026-05-27  # v2 after codex review v1
targets:
  - scripts/wiki_lint.py
  - AGENTS.md
  - wiki-design/02-workflows.md
  - wiki-design/05-contracts-and-next-steps.md
reviewers:
  - codex
  - user
---

# RFC-006: 引入 wiki-lint MVP，闭合 RFC-002/003/004 的约束

## 背景

RFC-001~005 已 accepted + applied，schema 完全冻结，`knowledge/` 骨架已落地（TASK-005）。但有一个明显缺口：**RFC-002/003/004 在知识数据层定义的所有 schema 约束目前只靠 Agent 人肉遵守，没有任何机械保障**。

> 范围界定（v2 澄清）：本 RFC 只覆盖**知识数据层**（`knowledge/**`，对应 RFC-002/003/004 的产物）。**不覆盖**协作流程层（`wiki-design/rfcs/**`、`wiki-design/tasks/**`，对应 RFC-001/005）—— 这些是流程文档，状态流转需要 git 历史校验，留给后续 RFC。

具体而言，下列约束在 schema 层有明确定义，在执行层完全缺失：

| 约束 | 设计来源 | 现状 |
| --- | --- | --- |
| frontmatter 必填字段（id / type / status / ...） | 01-architecture / RFC-002 | 无校验 |
| `id` 格式 `<prefix>_YYYYMMDD_<slug>` 全局唯一 | RFC-002 | 无校验 |
| source 单主键 `source_id == id == summary_page_id` | RFC-002 / 05 | 无校验 |
| `related_ids` / `source_ids` / `supersedes` / `superseded_by` / `canonical_id` 指向真实存在的 id | 01 canonical 边界 | 无校验 |
| `supersedes` / `superseded_by` 双向对称（A `supersedes:[B]` ↔ B `superseded_by:[A]`） | RFC-002 | 无校验 |
| `aliases` 在所有 entity 中唯一 + 不与其它 `canonical_id` 冲突 | RFC-004 | 无校验 |
| `canonical_id` 不允许链式跳转（必须指向 `canonical_id: null` 的正名页） | RFC-004 / 05 | 无校验 |
| `status: redirect` 必须有 `canonical_id` 指向有效正名 entity | RFC-004 | 无校验 |
| `hash_sha256` 64 位十六进制格式 | RFC-002 / 05 | 无校验 |
| 日期格式（wiki `YYYY-MM-DD` / JSON 带时区 ISO 8601） | 05 各 schema | 无校验 |
| JSON enum 取值（source_type / status / adapter / review_queue.type / ...） | 05 各 schema | 无校验 |
| inbox `id` 格式 `inb_YYYYMMDD_HHmmss_<slug>` | RFC-003 | 无校验 |
| capture_policy.exclude_patterns 的 PII 正则扫描 | RFC-003 | 无执行体 |
| 派生层文件（id_index / inbox_index / normalized_alias_index）生成 | RFC-002/003/004 | 无生成者 |

结果：

1. **Agent 可能写出违反约束的页面**（如 `source_id != id`、断引 `related_ids`、重复 alias），靠下一个 Agent 阅读时才发现。
2. **ingest / 晋升流程缺关键依赖**：`02-workflows.md` 写"运行 lint"和"按 alias matching 找候选"，但实际没有 `normalized_alias_index.json`，alias matching 无法机械执行。
3. **PII 兜底名义存在实际缺失**：`capture_policy.json.exclude_patterns` 列了 6 条正则，没人在跑。
4. **健康度检查、`overview.md` 健康度表无数据源**：`TASK-005` 自留注释"健康度由 `wiki-lint`（未实现）周期性更新"。

ingest 还没真正跑过任何一次（`knowledge/wiki/` 全空）。在首次 ingest 之前补 lint 比之后补成本低得多——之后补需要回扫存量。

## 提案

引入 **wiki-lint MVP**：一个 Python 脚本 + 派生层生成器 + 报告输出，**只覆盖 RFC-002/003/004 已定义的知识数据层约束**，不引入新规则。

### 范围（MVP 包含）

#### 1. schema 校验

按 RFC-002 / RFC-003 / RFC-004 写的字段表逐项校验：

- `wiki/**/*.md` 的 frontmatter 必填字段、`id` 格式、enum 值
- `inbox/*.md` 的 frontmatter（含 `status` / `suggested_target_type`）
- 4 个上下文层 md (`purpose/index/overview/log`) 不要 frontmatter（反向校验）
- **日期格式**：
  - wiki 页 `created` / `updated` / `last_verified` = `YYYY-MM-DD`
  - JSON 中 `imported_at` / `last_ingested_at` / `updated_at` / `created_at` / `resolved_at` / `captured_at` = 带时区 ISO 8601 或 `null`
- **enum 显式取值**（不允许自由发挥）：
  - 页面 `type` ∈ `{source, entity, topic, comparison, synthesis, decision, query, open-question}`
  - 页面 `status` ∈ `{draft, active, stale, archived, redirect}`
  - 页面 `confidence` ∈ `{low, medium, high}`
  - `source_manifest.source_type` ∈ `{pdf, markdown, web, chat, image, manual, code}`
  - `source_manifest.status` ∈ `{new, triaged, ingested, skipped, failed, deleted}`
  - `source_manifest.adapter` ∈ `{local_file, web_clipper, manual, llm_wiki_app, custom}`
  - `review_queue.type` ∈ `{contradiction, duplicate, missing_page, confirm, suggestion, source_gap, stale_claim}`
  - `review_queue.status` ∈ `{pending, resolved, dismissed}`
  - `review_queue.priority` ∈ `{low, medium, high}`
  - `capture_policy.auto_capture` 必须是 `bool`；`exclude_paths` 必须是 `array<string>`；`max_inbox_files` 必须是正整数；`version` == 1
- **hash_sha256 格式**：64 位十六进制（`^[0-9a-f]{64}$`），MVP 只校验格式，**不**比对实际文件 hash（性能 + 文件可能已删除）。

#### 2. ID 唯一性 + 派生 `id_index.json`

- 收集 `wiki/**` 所有 `id`，校验全局唯一
- 同日同 slug 冲突 → 强制 `_NN` 后缀（违反 → error）
- 输出 `.wiki/id_index.json`，**与其它两个派生层格式一致**：

```json
{
  "version": 1,
  "updated_at": "ISO 8601",
  "entries": {
    "src_20260526_attention": {
      "path": "wiki/sources/attention-is-all-you-need.md",
      "type": "source",
      "status": "active"
    }
  }
}
```

#### 3. canonical 引用完整性 + supersedes 对称

- `source_ids` / `related_ids` / `supersedes` / `superseded_by` / `canonical_id` 中每个 id 都能在 `id_index` 找到（断引 → error）
- `review_queue.json.evidence[].page_id` / `affected_page_ids` 同理
- `source_manifest.summary_page_id` 同理
- **supersedes / superseded_by 双向对称**：
  - 若页 A `supersedes: [B]`，则页 B `superseded_by` 必须包含 A
  - 反向同理
  - 任一方向缺失 → error
- 被 superseded 的页应自动有 `status: archived`（否则 warning）

#### 4. source 单主键

- 每个 `wiki/sources/*.md`：`frontmatter.id == frontmatter.source_id`（不等 → error）
- 每个 `source_manifest.sources[*]`：
  - `summary_page_id` 为 `null` 或等于 `source_id`
  - 若 `summary_page_id != null`：必须等于对应摘要页 `id` 且摘要页 `type == source`
  - `summary_page_path` 若非 `null` 则文件必须存在，且其 frontmatter id 与 `summary_page_id` 一致

#### 5. entity 别名机制 + 派生 `normalized_alias_index.json`

校验：

- 收集所有 entity 的 `aliases` + 正名 title（H1）+ 薄重定向页 `id`
- 规范化（lowercase / 去首尾空白 / 连续空白合并 / 连字符 ↔ 下划线 ↔ 空格 / 中文全半角统一 / 复数 s/es 可选）
- 同一规范化 key 不能映射到两个不同 `canonical_id`（冲突 → error，同时写入 `review_queue.json type: duplicate`）
- `status: redirect` 的 entity 必须有 `canonical_id` 指向真实存在的 entity
- **`canonical_id` 不允许链式跳转**：`canonical_id` 必须指向 `canonical_id: null` 的正名页（A → B → C → error）

输出 `.wiki/normalized_alias_index.json`，**严格按 05-contracts-and-next-steps.md「Normalized Alias Index Schema」已冻结格式**：

```json
{
  "version": 1,
  "updated_at": "ISO 8601",
  "entries": {
    "attention": {
      "canonical_id": "ent_20260526_attention",
      "matched_form": "Attention",
      "source": "title"
    },
    "self-attention": {
      "canonical_id": "ent_20260526_attention",
      "matched_form": "self-attention",
      "source": "alias"
    }
  }
}
```

`source` ∈ `{title, alias, redirect}`。

#### 6. inbox 派生 `inbox_index.json`

输出 `.wiki/inbox_index.json`，**严格按 05-contracts-and-next-steps.md「Inbox Index Schema」已冻结格式**：

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
  "updated_at": "ISO 8601"
}
```

- `draft_count` 只计 `inbox/*.md` 中 `status: draft`，**不含** `archive/`
- `oldest_draft_age_days` 按 frontmatter `created` 算；无 draft 时为 `null`
- `recent_drafts` 默认 N = 10，summary 优先 `suggested_target_title`，回退正文首句
- `captured_at` 优先 frontmatter `created`，回退文件名秒级时间戳

#### 7. PII 扫描（默认 inbox-only）

- 读 `capture_policy.json.exclude_patterns`
- **默认扫**：`inbox/*.md`（含 frontmatter + 正文）
- **可选扩展**：`--scan-wiki-pii` 时额外扫 `wiki/**/*.md`
- 命中报告含：文件路径 + 行号 + 命中的 pattern
- 分级：
  - `inbox/*.md` 命中且 `status: draft` → **error**（阻塞 commit）
  - `inbox/*.md` 命中且 `status: promoted/dropped`（即 archive/）→ warning
  - `wiki/**` 命中（仅 `--scan-wiki-pii` 模式）→ warning

#### 8. 跨流程一致性

- `summary_page_id` 已生成时其指向的页 `id` 必须存在且 `type=source`
- `review_queue.items[].evidence[].page_path` 与 `page_id` 在 id_index 中一致（page_path 必须是 page_id 当前路径）
- inbox `archive/promoted/` 下文件的 frontmatter `status` 必须是 `promoted`；`archive/dropped/` 下必须是 `dropped`（防止人工移动文件忘改 status）

### 范围（MVP 不包含 → 留给后续 RFC）

- `wiki-context` / `wiki-graph-refresh`（05 第三阶段的另两个脚本）
- 自动修复（auto-fix）
- 健康度评分 / `overview.md` 自动更新
- 断链建议、孤立页检测、`review:true` 长期未处理告警（→ Backlog "review queue SLA"）
- pre-commit hook 集成（先手动跑，hook 由后续 RFC 决定）
- CI 集成
- **协作流程层 lint**：不 lint `wiki-design/rfcs/*.md` 和 `wiki-design/tasks/*.md` 的 frontmatter / status enum / 状态流转。这些是流程文档，状态流转校验需要 git 历史，留给后续 RFC（暂称 RFC-008 "wiki-design lint"）。
- **hash_sha256 实际值比对**：MVP 只校验 64 位十六进制格式；是否重算并对比 `raw/sources/<file>` 的实际 hash 留给后续 RFC（涉及性能权衡）。

### 触发与输出

```bash
# 手动跑（MVP 默认）
python3 scripts/wiki_lint.py                  # 校验 + 重建派生层
python3 scripts/wiki_lint.py --check-only     # 只校验，不写派生层
python3 scripts/wiki_lint.py --json           # 机器可读输出
python3 scripts/wiki_lint.py --scan-wiki-pii  # 加扫 wiki/ PII（默认只扫 inbox）
```

> 命令统一使用 `python3`（macOS 上 `python` 可能不存在或指向旧版）。`scripts/README.md` 中写明安装步骤 `pip3 install pyyaml`。

退出码：

- `0` = 所有 error 段为空（warning 可有）
- `1` = 有 error
- `2` = 配置 / 脚本自身错误

人类可读输出格式（默认）：

```
wiki-lint v0.1.0
================
扫描: knowledge/wiki/ (0 文件) · knowledge/inbox/ (0 文件) · knowledge/raw/ (0 source)

[OK]      schema 校验: 0/0 页通过
[OK]      ID 唯一性: 0 个 id（无冲突）
[OK]      canonical 引用 + supersedes 对称: 0/0 完整
[OK]      source 单主键: 0/0
[OK]      entity 别名（含链式跳转 / status:redirect）: 0 个 alias / 0 个正名
[OK]      inbox: 0 draft
[OK]      PII 扫描（inbox-only）: 0 命中

派生层已重建（原子写入）:
  .wiki/id_index.json (0 entries)
  .wiki/normalized_alias_index.json (0 entries)
  .wiki/inbox_index.json (0 drafts)

错误: 0 · 警告: 0
```

JSON 输出格式（`--json`）—— **MVP 固定结构**：

```json
{
  "wiki_lint_version": "0.1.0",
  "ran_at": "ISO 8601",
  "scanned": {
    "wiki_pages": 0,
    "inbox_drafts": 0,
    "sources": 0
  },
  "errors": [
    {
      "code": "ID_DUPLICATE",
      "file": "wiki/entities/foo.md",
      "line": 3,
      "field": "id",
      "message": "id 'ent_20260526_foo' 已在 wiki/entities/bar.md 出现",
      "hint": "改名或追加 _NN 后缀"
    }
  ],
  "warnings": [],
  "derived_layers": {
    "id_index_entries": 0,
    "normalized_alias_index_entries": 0,
    "inbox_index_drafts": 0
  }
}
```

每条 `errors[]` / `warnings[]` 必须含 `code` / `file` / `line` / `field` / `message` / `hint` 六字段（缺字段时该项为 `null`）。MVP 固定一套 error code 命名规则（如 `ID_DUPLICATE` / `CANONICAL_DANGLING` / `SUPERSEDES_ASYMMETRY` / `ALIAS_CONFLICT` / `CANONICAL_CHAIN` / `SOURCE_KEY_MISMATCH` / `HASH_FORMAT` / `DATE_FORMAT` / `ENUM_INVALID` / `PII_HIT_DRAFT` 等），具体 code 表写进 `scripts/README.md`。

### 实现约束

- **语言**：Python 3.9+，**只用标准库** + `PyYAML`（一个依赖，frontmatter 解析）。理由：仓库零依赖现状，Python 在所有 dev / CI 环境都有。
- **文件位置**：`scripts/wiki_lint.py`（单文件起步，未来可拆模块）+ `scripts/README.md`。
- **配置**：直接读 `knowledge/.wiki/capture_policy.json`，**不**引入新配置文件。
- **退出语义**：error 阻塞（exit 1），warning 通过但提示。
- **幂等**：多次运行结果一致；派生层文件按确定序写入（JSON `sort_keys=True` + `entries` 内部按 key 升序）。
- **原子写**（v2 新增）：派生层 JSON 一律按 "写 `<file>.tmp` → `os.replace(tmp, file)`" 模式落盘，避免多 Agent 并发 lint 时读到半写入文件。
- **零网络 / 零 LLM**：纯机械检查，不调用任何模型。
- **可重建**：派生层从 0 重建 ≤ 1 秒（小规模 knowledge）。

### 与现有流程的衔接

| 流程 | lint 怎么衔接 |
| --- | --- |
| ingest Apply 阶段 | apply 完成后**必须**跑 lint，error 时回滚或转入 review_queue |
| inbox 晋升 apply 阶段 | 同上 |
| 结晶化 / crystallize | 同上 |
| capture 写入 inbox | inbox PII 扫描必须 inline 跑（auto_capture: true 路径必经） |
| commit | MVP 不强制 pre-commit hook，但建议人工跑 `wiki-lint --check-only` |

对 02-workflows.md 的具体改动：把所有"运行 lint"句子改为"运行 `python3 scripts/wiki_lint.py`"。

对 05-contracts-and-next-steps.md 第三阶段的改动：把 `scripts/wiki-lint` 状态从"待实现"标为本 RFC 落地范围；`wiki-context` / `wiki-graph-refresh` 仍待后续 RFC。

对 AGENTS.md 的改动：在「commit 规则」前加一节「lint 触发约束」：

```
## lint 触发约束

任何对 knowledge/wiki/、knowledge/inbox/、knowledge/raw/source_manifest.json、
knowledge/.wiki/review_queue.json、knowledge/.wiki/capture_policy.json 的修改，
commit 前必须跑 `python3 scripts/wiki_lint.py --check-only` 通过。

派生层文件（.wiki/id_index.json 等）由 lint 自动生成，不需要手动维护，也不进 Git。
```

## 替代方案

### A. 触发方式

| 方案 | 优点 | 缺点 |
| --- | --- | --- |
| **MVP: 手动跑** | 实现最简单；不绑 git hook；不需 CI | 依赖人工 / Agent 自觉 |
| pre-commit hook | 强制保障 | 需要安装步骤；hook 失败有时令人困惑；与 commit 拆分策略冲突 |
| CI 跑 | 不漏 | 需要 GitHub Actions / 类似环境；本仓库尚未配 CI |
| pre-commit + CI 双保险 | 最稳 | 工程量翻倍，MVP 不必要 |

**推荐**：MVP 手动 + AGENTS.md 写明触发约束。pre-commit hook 留给 RFC-007 决定（先看 lint 实际表现）。

### B. 实现语言

| 方案 | 优点 | 缺点 |
| --- | --- | --- |
| **Python + PyYAML** | dev 环境普遍可用；frontmatter 解析成熟；标准库够 | 引入 1 个 pip 依赖 |
| Python 纯标准库（手写 YAML 解析） | 零依赖 | YAML 多行 / 锚点处理复杂，易出 bug |
| Node.js + gray-matter | npm 生态丰富 | 引入 package.json / node_modules 整套 |
| Shell + yq | 极轻 | 多文件聚合校验难写；yq 不一定预装 |

**推荐**：Python + PyYAML。仓库 Mac 环境已有 python3，PyYAML 单依赖可接受。

### C. MVP 范围

| 方案 | 范围 | 评估 |
| --- | --- | --- |
| **本 RFC: 1~8 项全做** | schema + 唯一性 + canonical + source + alias + inbox + PII + 派生 | 闭合所有现有约束 |
| 仅做 1~4 项 | schema + 唯一性 + canonical + source | 留 alias / inbox / PII 后做 |
| 仅做派生层 | 不校验，只生成 index | alias matching 能用，但不挡错 |

**推荐**：1~8 项全做。每项实现成本可控（每项约 50~80 行 Python），分散做反而增加重复扫描成本。

### D. 输出方式

| 方案 | 评估 |
| --- | --- |
| **人类可读 + `--json` 选项** | MVP 推荐：既好读又能机器解析；v2 已固定 JSON 结构 |
| 只人类可读 | 后续 CI 集成时要改 |
| 只 JSON | 日常跑不友好 |

### E. PII 扫描范围（v2 新增决策点）

| 方案 | 评估 |
| --- | --- |
| **默认 inbox-only + `--scan-wiki-pii` 扩展** | MVP 推荐：明确开关；避免误报阻塞已审核的 wiki/ |
| 默认全扫 | wiki/ 中正常含 author 名 / URL 等会高误报 |
| 仅 inbox | 与默认推荐相同但无扩展能力 |

## 影响范围

### 新增

- `scripts/wiki_lint.py`（约 **600~800 行** Python，v2 上调估算）
- `scripts/README.md`（说明 MVP 范围 + 用法 + error code 表 + 安装步骤）

### 改动正本

- `AGENTS.md`：+ 一节「lint 触发约束」
- `wiki-design/02-workflows.md`：把所有"运行 lint"改为具体命令
- `wiki-design/05-contracts-and-next-steps.md`：第三阶段 lint 状态标记落地
- 无需改 `knowledge/.wiki-schema.md`（schema 没变，只是补执行体）

### 不改动

- `.gitignore`（派生层路径已在 RFC-002/003/004 加入，本 RFC 无需再动；v2 已从 targets 删除）
- `knowledge/` 数据（lint 只读 + 写派生层）
- 任何 RFC-001~005 的 schema 定义

### 依赖

- 引入 PyYAML（dev 依赖，需在 `scripts/README.md` 中标注 `pip3 install pyyaml`）。
- 如果团队偏好 zero-dependency，可降级到纯标准库 + 简化 YAML 解析（只支持本仓库实际用到的 frontmatter 子集）。

### 与 Backlog 议题的关系

| Backlog 议题 | 本 RFC 关系 |
| --- | --- |
| evidence 结构化 | 不冲突，未来 evidence schema 一变 lint 跟着改 |
| review queue SLA | 本 RFC 不做 SLA / 长期 pending 检测，留给后续 RFC |
| Wiki 健康度指标 | 本 RFC 提供数据底座（id_index 等），健康度计算留后 |
| 双 Agent 并发写入约束 | v2 已在风险段 + 实现约束加原子写；进一步 lock 机制留后续 RFC |
| visibility / PII 字段 | 本 RFC 用现有 exclude_patterns，未来 visibility 字段加入后 lint 跟着扩 |

### 风险

1. **PyYAML 单依赖**：极成熟，风险低，但若团队完全反对外部依赖，需走「纯标准库」替代方案。
2. **MVP 与首次 ingest 时间窗**：lint 应在首次 ingest 之前落地，否则会出现"有数据但无校验"的窗口期。建议 RFC accepted 后立即开 TASK-006 落地。
3. **派生层重建成本**：MVP 是全量扫描，规模 < 1000 页时 < 1 秒，规模上去后再考虑增量。
4. **PII 误报**：当前 6 条正则是初始规则，可能误伤；MVP 在 inbox draft 命中升 error，archive / wiki 仅 warning，可调。
5. **lint 自身 bug**：lint 写错可能阻塞合法写入。MVP 提供 `--check-only` 和明确错误信息缓解；严重时 Agent 可绕过（在 Execution log 中说明原因）。
6. **多 Agent 并发跑 lint 的写竞态**（v2 新增）：派生层不进 Git 但物理存在；两个 Agent 同时跑 lint 可能互相覆盖或读到半写入 JSON。MVP 缓解：所有派生层 JSON **原子写**（写 `.tmp` + `os.replace`）+ **确定序**（`sort_keys=True`）。是否引入文件锁（`.wiki/wiki-lint.lock`）留给实际跑出问题再决定，避免 MVP 过度工程。

## Review by codex · YYYY-MM-DD

（待 Codex 追加）

## Decision

（待用户填写或授权 Agent 代写）

## Review by codex · 2026-05-27

### 总体结论

- 结论：需修改。
- 我同意核心方向：在首次 ingest 前补上 `wiki-lint` 是对的，MVP 先做手动触发、单文件 Python、人类可读输出加 `--json`，也符合当前仓库规模和多 Agent 协作成本。
- 但这版 RFC 现在有几处阻塞点：它声称闭合 RFC-001~005 已冻结约束，实际范围更接近 RFC-002/003/004 的知识数据层；且部分已落地 schema 的机械规则没有写进 lint 范围，后续 TASK 如果照此实现会漏校验或生成不兼容派生层。

### 阻塞问题

1. 完整性还没覆盖若干已冻结约束。当前 1~8 项覆盖了 frontmatter、ID、canonical 引用、source 主键、alias、inbox、PII、部分跨流程一致性，但没有明确校验：
   - `supersedes` / `superseded_by` 的双向对称关系。只校验引用存在不够，应要求 A `supersedes: [B]` 时 B `superseded_by` 包含 A，反向同理。
   - `hash_sha256` 格式。至少应校验 64 位十六进制；如果 `original_path` 指向本地文件且文件存在，可考虑校验实际 hash 是否一致，或明确 MVP 只做格式校验。
   - ISO 8601 / 日期格式。wiki 页面的 `created/updated/last_verified` 应是 `YYYY-MM-DD`；JSON 中 `imported_at/last_ingested_at/updated_at/created_at/resolved_at` 等应是带时区的 ISO 8601 或 `null`。
   - JSON enum 与类型：`source_manifest.source_type/status/adapter`、`review_queue.type/status/priority/resolved_action`、`capture_policy.version/auto_capture/exclude_paths/max_inbox_files` 等需要在 schema 校验范围中显式列出。
   - `canonical_id` 不允许链式跳转。RFC-004 落地后的规则要求 redirect 页的 `canonical_id` 指向 `canonical_id: null` 的正名页，不能 A -> B -> C；当前只写了"指向真实正名页"的倾向，但建议作为 error 明确。

2. `normalized_alias_index.json` 的输出格式和已落地 schema 不兼容。RFC-006 写的是 `{ normalized: canonical_id }`，但 `05-contracts-and-next-steps.md` / `knowledge/.wiki-schema.md` 已冻结为：
   - 顶层 `version`
   - `updated_at`
   - `entries`
   - `entries[k].canonical_id`
   - `entries[k].matched_form`
   - `entries[k].source`
   如果 TASK 按 RFC-006 的简化写法实现，会直接破坏 RFC-004/TASK-005 的契约。这里必须改成已冻结格式。

3. RFC-001 / RFC-005 的状态流转边界需要澄清。若本 RFC 真的宣称覆盖 RFC-001~005，应说明是否 lint `wiki-design/rfcs/*.md` 和 `wiki-design/tasks/*.md` 的 frontmatter、status enum 与状态机。状态"流转"严格来说需要 git 历史或基线才能验证；MVP 可以选择不做，但需要在"范围不包含"中明确排除，避免把知识数据 lint 和协作流程 lint 混成一个承诺。

4. 并发写派生层的风险漏了。多 Agent 同时跑 lint 时，即使派生层不进 Git，也可能出现半写入文件、互相覆盖、一个进程读到另一个进程写了一半的 JSON。MVP 至少应要求确定序 JSON + 写临时文件 + `os.replace` 原子替换；是否加 `.wiki/wiki-lint.lock` 可以作为可选方案，但风险段需要显式写出来。

5. frontmatter targets 与正文有不一致：frontmatter targets 包含 `.gitignore`，但提案和影响范围都说 `.gitignore` 无需改动。建议删掉 targets 里的 `.gitignore`，或解释为什么仍列为 target。

### 非阻塞建议

- 命令建议统一成 `python3 scripts/wiki_lint.py`，或在 README 中说明 `python` / `python3` 的兼容写法；macOS 上 `python` 仍可能不存在或指向旧环境。
- 400~600 行估算偏乐观。若包含 Markdown frontmatter、JSON schema、alias normalizer、PII 行号、三类派生层、`--json`，600~800 行更现实；仍可保持单文件，但建议用清晰的函数分区和稳定 error code。
- `--json` 输出最好在 RFC 中给一个最小结构，例如 `errors[] / warnings[]` 每项含 `code`、`file`、`line`、`field`、`message`、`hint`，否则后续 CI 或 Agent 解析会再二次约定。
- PII 扫描里 "`wiki/**/*.md` 可选" 建议改成明确模式：默认扫 inbox；`--scan-wiki-pii` 或配置项再扫 wiki。否则不同 Agent 对"可选"理解不同。

### 替代方案判断

- 触发方式：MVP 手动跑合理，pre-commit / CI 放后续 RFC 是稳妥取舍。
- 语言：Python + PyYAML 合理，但需要把依赖安装入口写清楚；如果团队坚持零依赖，再退回受限 frontmatter parser。
- 范围：1~8 项全做是合理方向，但要先补齐上面的冻结约束，不然"全做"会给出错误安全感。
- 输出：人类可读 + `--json` 合理；只需补一个稳定 JSON 结构。

## Revision v2 by claude · 2026-05-27

addressing codex review v1 的 5 个阻塞点 + 4 个非阻塞建议。修订清单：

### 阻塞点修复

1. **完整性补漏**（review 阻塞 #1）
   - 背景表新增 5 行：supersedes 对称 / canonical_id 链式 / hash_sha256 格式 / 日期格式 / JSON enum
   - 范围 #1 schema 校验**显式列出** 9 个 enum 字段的合法取值
   - 范围 #1 显式列出日期格式（wiki YYYY-MM-DD / JSON ISO 8601）和 hash_sha256 64 位十六进制
   - 范围 #3 新增 supersedes ↔ superseded_by 双向对称校验段
   - 范围 #5 新增 `canonical_id` 不允许链式跳转校验
   - 范围（MVP 不包含）明确：hash_sha256 实际值比对留给后续 RFC

2. **派生层 schema 改为已冻结格式**（review 阻塞 #2）
   - 范围 #5 输出格式从 `{ normalized: canonical_id }` 改为 05 已冻结的 `version + updated_at + entries{key: {canonical_id, matched_form, source}}`
   - 范围 #6 输出格式从模糊描述改为 05 已冻结的 `version + draft_count + oldest_draft_age_days + recent_drafts[] + updated_at`
   - 范围 #2 顺手把 `id_index.json` 也改为统一格式（`version + updated_at + entries{id: {path, type, status}}`），保持三个派生层风格一致；id_index 在 RFC-002 只有非正式约定，本 RFC 提议这个升级

3. **范围边界澄清**（review 阻塞 #3）
   - 标题保留 "闭合 RFC-002/003/004 的约束"（v1 已正确）
   - 背景段开头加范围界定 quote，明确**只覆盖知识数据层**（knowledge/**），不覆盖协作流程层（wiki-design/rfcs/** + wiki-design/tasks/**）
   - 提案段开头从 "RFC-001~005" 改为 "RFC-002/003/004 知识数据层约束"
   - 范围（MVP 不包含）新增一条："不 lint wiki-design/rfcs/*.md 和 wiki-design/tasks/*.md，留给后续 RFC（暂称 RFC-008）"

4. **并发原子写**（review 阻塞 #4）
   - 实现约束段新增 "原子写" 一条：`<file>.tmp + os.replace + sort_keys=True`
   - 风险段新增第 6 条：多 Agent 并发跑 lint 的写竞态，缓解方案 + 何时考虑 lock
   - 输出格式示例标注 "原子写入"
   - Backlog 关系表 "双 Agent 并发写入约束" 行注明本 RFC 已部分覆盖

5. **frontmatter targets 一致性**（review 阻塞 #5）
   - frontmatter `targets` 删除 `.gitignore`
   - 影响范围段保留说明：派生层路径已在 RFC-002/003/004 加入

### 非阻塞建议采纳

- ✅ 命令统一为 `python3`，触发段顶部加 quote 说明 macOS 兼容性
- ✅ 行数估算 400~600 → **600~800**（影响范围段 + 替代方案 C "每项 50~80 行" 同步）
- ✅ `--json` 输出加 **MVP 固定结构** 示例，含 `errors[].code/file/line/field/message/hint` 六字段；并列出 MVP error code 命名规则（10+ 条）
- ✅ PII 扫描从 "wiki/**/*.md 可选" 改为 **明确开关 `--scan-wiki-pii`**；范围 #7 全段重写分级（inbox draft = error / archive = warning / wiki = warning 且需开关）；替代方案新增 E 段记录此决策

### 未改动

- 替代方案 A / B / C / D 推荐项不变（codex review 也认同）
- 提案核心 8 项编号不变，便于 v1 ↔ v2 对照
- Codex review v1 段完整保留不动（append-only 规则）

待 Codex re-review。
