---
id: task_20260526_004
title: Apply RFC-004 — entity aliases / canonical_id / status:redirect / normalized_alias_index
author: claude
executor: codex
status: pending
type: apply
created: 2026-05-27
updated: 2026-05-27
related_rfcs:
  - rfc_20260526_004
  - rfc_20260526_002
  - rfc_20260526_003
---

# TASK-004: Apply RFC-004 — entity aliases 机制

## 目标

把 RFC-004 Decision 中的 7 条 apply 条件落到 4 个正本：

- `wiki-design/01-architecture.md`
- `wiki-design/02-workflows.md`
- `wiki-design/05-contracts-and-next-steps.md`
- `.gitignore`

执行完成后：

- Entity frontmatter 拿到 `aliases` / `canonical_id` 两字段（含薄重定向页规则）
- 页面 status 枚举增加 `redirect`
- 摄入 Triage 必跑 alias matching；Inbox 晋升 workflow（TASK-003 刚加）也复用同一套
- 05 多一段 Normalized Alias Index Schema（同 Inbox Index Schema 模式）
- 答案引用示例改成不引用别名 wikilink

## 前置条件

- 仓库根目录：`/Users/zhangjunwu/workspace/llm-wiki/llm-wiki`
- HEAD 包含 **TASK-003 已 done**（commit `567a83f` 及之后），即：
  - 01 已有 "稳定 ID 规则" / "Cross-ref 字段说明" / inb_ prefix
  - 02 已有 "被动 capture（建议 / 自动）" 和 "Inbox 晋升" 两段
  - 05 已有 "Capture Item Schema" / "Capture Policy Schema" / "Inbox Index Schema" 三段
  - .gitignore 已含 id_index.json / inbox_index.json
- working tree clean
- 已读 `wiki-design/rfcs/RFC-004-entity-aliases.md`（重点 Decision 7 条）
- 已读 `wiki-design/tasks/README.md` 理解 task 规则
- 已读 TASK-002 / TASK-003 Evaluation，理解 apply 类 task 工作流惯例
- **本 task 不动 RFC-002 / RFC-003 相关已落地内容**（除 Decision #6 要求的 Inbox 晋升 workflow 增量）

## 强约束

违反任一即视为执行失败，应在 Execution log 写明并把 status 改为 failed：

1. **只动 4 个文件**：`wiki-design/01-architecture.md`、`wiki-design/02-workflows.md`、`wiki-design/05-contracts-and-next-steps.md`、`.gitignore`。其它一律不动。
2. **不创建** `knowledge/` 任何文件或目录（属于 TASK-005）。
3. **不动** `AGENTS.md`、`wiki-design/04-agent-rules.md`、`wiki-design/README.md`、任何 RFC 文件、**其它** TASK 文件。
   - 本 TASK-004 文件本身按 Step 0 / 6 / 7 允许编辑（追加 Spec review、推进 status、追加 Execution log）。
4. **保留** 4 个正本中所有不被本 task 覆盖的章节段落。**特别**：TASK-003 刚加的 "被动 capture" 段、Capture Item / Policy / Inbox Index Schema 三段不允许结构性改动（只允许 Inbox 晋升段做 alias matching 增量）。
5. **必须先经 Codex spec review（Step 0）**：在 Step 0 通过前 status 保持 pending，不可执行 Step 1~6。
6. **lint 规则替换**：Step 1d 写 lint 规则时，按 Decision #2 的新规则，**不**采用原 RFC 提案 "3. lint 校验" 第二条（"一个 id 不能既出现在某页 canonical_id 又自己有非空 aliases"——这条已被 Codex review 判定为误伤正常用法）。
7. **答案引用示例修正**：Step 3c 写答案引用示例时按 Decision #5，`self-attention（正名 [[Attention]]）` 而非 `[[self-attention]]（正名 [[Attention]]）`。
8. **alias 来源记录**（Decision #7）不强制写入字段，仅在 entity 模板下方加一句"可选：alias 来源记录"备注。不新增结构化字段。
9. **schema 一致性**：所有新增字段 / JSON 示例与 TASK-002/003 落地后的 schema 一致（含 `id` 格式、`status` 枚举扩展为 5 个值、与 inb_ / capture_policy 不冲突）。
10. 三个 commit 分别：Step 0 Spec review（codex 写时自行 commit）/ Step 6 正本改动 / Step 7 task status 推进。

## 工作流

```
Step 0  Codex spec review (本 task 文件，追加 Spec review 段) + 单独 commit
        │
        │  通过 → Step 1
        │  需修改 → Claude 改 spec → 重新进入 Step 0
        │
        ▼
Step 1~4  Codex 执行 4 个文件的编辑
        │
        ▼
Step 5  自检验证（基于 working tree 状态，不用 commit-range baseline）
        │
        ▼
Step 6  Commit 正本改动（4 文件一次性 commit，[apply rfc-004] 前缀）
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
- [ ] Decision 7 条是否全部覆盖到 Step 1~4
- [ ] 跨 RFC 协同（Decision #6 要求 Inbox 晋升 workflow 复用 alias matching）是否在 Step 2b 体现
- [ ] 新内容是否仅来自 RFC-004（不混 002/003）

### 可执行性
- [ ] 每个 Step 是否有明确的 anchor / 新内容
- [ ] 验证步骤是否基于 working tree（不踩 TASK-003 evaluate 沉淀的 baseline leak 坑）

### 风险
- 列出可能踩坑的地方

### 结论
- 通过 / 需修改 (列出建议)
```

如果"需修改"，Codex 不要自行改 spec；只给出建议，由 Claude 修订。Spec review 段一旦写入，**status 字段不改**（保持 pending）。Codex 自行 commit 这次 Spec review 改动（commit message：`[task] TASK-004 spec review by codex (conclusion: <通过/需修改>)`）。

### Step 1：更新 `wiki-design/01-architecture.md`

#### 1a：Frontmatter 字段表加 `aliases` / `canonical_id` 两行 + `status` 扩枚举

找到字段表（应是 Frontmatter section 中由 TASK-002 落地的 16 行表）。

(i) 把 `status` 行的"值列"从 `draft、active、stale、archived` 改为：

```markdown
| `status` | `draft`、`active`、`stale`、`archived`、`redirect`（`redirect` 仅用于 entity 别名薄页，不参与主图谱节点） |
```

(ii) 在 `evidence_count` 行**之前**新增两行：

```markdown
| `aliases` | （仅 entity）已知别名字符串数组，保留人类写法；规范化匹配由派生 `normalized_alias_index.json` 维护 |
| `canonical_id` | （仅 entity）若为 `null` 则本页是正名页；若指向某 `id` 则本页是薄重定向页，必须 `status: redirect` |
```

#### 1b：在 "稳定 ID 规则" 子节末尾追加 "entity 别名薄页" 备注

在该子节末尾（`**slug 不是当前标题镜像**` 段之后、`### 拆分与合并语义` 之前）插入：

```markdown
**entity 别名薄页**：极少数情况下，别名以独立页面形式存在（外部已有 wikilink 散布、不便迁移），该页 frontmatter 用 `canonical_id` 指向正名页 `id`，`status: redirect`，不参与主图谱节点 / 综合 / 引用来源。99% 的别名应只放在正名页的 `aliases` 列表里，不建薄页。详见 [05-contracts-and-next-steps.md](05-contracts-and-next-steps.md) "Normalized Alias Index Schema" 段和 entity 模板。
```

#### 1c：在 "正本与派生层" 段的"派生数据"列表末尾加一行

找到派生数据列表（应已含 `id_index.json` / `inbox_index.json` 等）。末尾追加：

```text
knowledge/.wiki/normalized_alias_index.json
```

#### 1d：在 "Cross-ref 字段说明" 表的 canonical 表里加一行

在 canonical 表（"下列引用是 canonical 的"）的 "页面 frontmatter" 行末尾追加 `canonical_id` 字段，即：

```markdown
| 页面 frontmatter | `id`、`source_ids`、`related_ids`、`supersedes`、`superseded_by`、`canonical_id`（entity 别名薄页指向） |
```

aliases 不列为 canonical（它是字符串数组，不是 ID 引用，由 normalized_alias_index 派生处理）。

### Step 2：更新 `wiki-design/02-workflows.md`

#### 2a：在 "摄入资料" 段的 Triage 阶段加 alias matching 子流程

找到 "摄入资料" 段下的 Triage 流程描述（应已有 "1. Triage 阶段" 列表，含 "识别来源类型"、"计算 hash"、"生成来源摘要"、"判断新增页面、更新页面、冲突点、开放问题"、"写入 review queue 或展示计划"）。

在 "判断新增页面、更新页面、冲突点、开放问题" 之**前**插入一条新子项：

```markdown
   - **entity alias matching**：对每个识别到的实体名，依次：
     1. 在所有 entity 页的 `id` / H1 标题 / `aliases` 中查找完全匹配，或在 `knowledge/.wiki/normalized_alias_index.json` 中查规范化匹配
     2. 命中 → 复用现有页面（更新 `last_verified`，必要时补充 alias 到正名页）
     3. 未命中但与已有实体 title/alias 编辑距离 < 阈值 → 写入 `review_queue.json type: duplicate`，由人确认
     4. 完全未命中 → 新建 entity 页（默认 `canonical_id: null`，仅当确需薄重定向时建别名页并 `status: redirect`）
```

#### 2b：在 "Inbox 晋升" 段加 alias matching 复用步骤（Decision #6）

找到 "Inbox 晋升" 段的"流程"代码块（TASK-003 刚加）。该代码块当前是：

```text
列出所有 status: draft 的 inbox 文件（读 knowledge/inbox/*.md）
-> 按主题分组（Agent 建议）
-> 对每组提议：
   - 晋升为 wiki/topics/、wiki/entities/、wiki/decisions/ 等新页面
   - 合并到已有页面（按标题/alias 匹配找候选）
   - 丢弃（确认无价值）
-> 用户决策每一项
-> apply：
   ...
```

把 "合并到已有页面（按标题/alias 匹配找候选）" 这一行**替换为**：

```text
   - 合并到已有页面（按 **alias matching** 找候选，详见"摄入资料" Triage 的 entity alias matching 子流程；entity 类晋升 / 合并必须先跑 alias matching，不等到下一次 ingest）
```

并在该代码块**之后**追加一段说明：

```markdown
> **跨 RFC 协同**：alias matching 逻辑与"摄入资料" Triage 共享同一实现（同一份 `normalized_alias_index.json` 派生索引）。晋升 entity 类 inbox 时禁止跳过 alias matching，否则 inbox 晋升会绕开 entity 消歧机制，导致 wiki 出现重复 entity 页。
```

### Step 3：更新 `wiki-design/05-contracts-and-next-steps.md`

#### 3a：Frontmatter 生命周期字段段 加 `aliases` / `canonical_id` 字段表行

找到该段的字段表（应有 TASK-002 落地的 id / type / status / source_ids / related_ids / 等行）。

(i) 把 `status` 行的值列扩枚举：

```markdown
| `status` | `draft`、`active`、`stale`、`archived`、`redirect`（`redirect` 仅 entity 别名薄页） |
```

(ii) 在 `evidence_count` 行**之前**新增两行：

```markdown
| `aliases` | （仅 entity）已知别名字符串数组；规范化匹配走派生 `normalized_alias_index.json` |
| `canonical_id` | （仅 entity）`null` = 正名页；指向某 `id` = 薄重定向页，必须配 `status: redirect` |
```

#### 3b：Entity 模板 frontmatter 加 `aliases` / `canonical_id` 字段

找到 "## Entity 模板" 段的 yaml 块。在 `related_ids: []` 行**之后**插入两行：

```yaml
aliases: []                                # entity 已知别名字符串数组（人类写法）；正名页可有，薄重定向页应为空
canonical_id: null                         # null = 正名页；指向某 ent_id = 薄重定向页（须 status: redirect）
```

并在 Entity 模板 yaml 块**之后**追加一段备注：

```markdown
> **别名管理**：99% 的别名应只放在正名页的 `aliases` 列表里。仅在外部已有 wikilink 散布到某别名时，才建薄重定向页（`canonical_id` 指向正名页 + `status: redirect`，正文留一行"重定向到 [[正名]]" 即可）。
>
> **alias 来源**（可选，不强制）：alias 字符串可在正文里附上 source 引用，例如：
> ```
> ## 别名来源
> - "SDPA" → [[src_xxx_attention-paper]]
> ```
> 未来如需结构化此关系，另开 RFC。本期不引入新 frontmatter 字段。
```

#### 3c：答案引用格式段 修正示例（Decision #5）

找到 "答案引用格式" 段。如果当前段中有 "[[self-attention]]（正名 [[Attention]]）" 这类示例，替换为 "self-attention（正名 [[Attention]]）"。

如果当前段没有此示例，则在 "答案引用格式" 段开头的 `引用边界` blockquote **之后**追加一段说明：

```markdown
**别名引用规则**：如果用户原话用了某 entity 的别名（如 "self-attention"），Agent 回答时应保留用户原写法并附正名 wikilink，**不要把别名包成 wikilink**：

- 正确：`self-attention（正名 [[Attention]]）`
- 错误：`[[self-attention]]（正名 [[Attention]]）`（除非别名薄页确实存在）

后续段落引用统一用正名 `[[Attention]]`。
```

#### 3d：新增 "Normalized Alias Index Schema" 整段

紧跟 "Inbox Index Schema" 段之后插入（保持 `## h2` 级别）：

~~~markdown
## Normalized Alias Index Schema

路径：`knowledge/.wiki/normalized_alias_index.json`

用途：把所有 entity 页的 `aliases`（以及 H1 标题、别名薄页 `id`）规范化后建立倒排索引，供摄入 Triage 和 Inbox 晋升做 entity 消歧。

**派生层**（由 `wiki-lint` 扫描 `knowledge/wiki/entities/*.md` 生成；可重建；进 `.gitignore`，不作为知识正本）。

### 顶层格式

```json
{
  "version": 1,
  "updated_at": "2026-05-27T10:00:00+08:00",
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
    },
    "自注意力": {
      "canonical_id": "ent_20260526_attention",
      "matched_form": "自注意力",
      "source": "alias"
    },
    "sdpa": {
      "canonical_id": "ent_20260526_attention",
      "matched_form": "SDPA",
      "source": "alias"
    }
  }
}
```

### 字段约束

| 字段 | 含义 |
| --- | --- |
| `version` | schema 版本，当前 `1` |
| `updated_at` | 索引重建时刻，ISO 8601 |
| `entries` | normalized key → entity 信息映射 |
| `entries[k]` | 规范化字符串作为 key |
| `entries[k].canonical_id` | 指向正名页 `id`（不指向薄重定向页 `id`，链式跳转在 lint 阶段平展） |
| `entries[k].matched_form` | 原始未规范化字符串 |
| `entries[k].source` | `title` / `alias` / `redirect`（来源是 H1 标题 / aliases 字段 / 薄重定向页） |

### 规范化规则

至少覆盖：

- 大小写折叠（`Attention` ↔ `attention`）
- 首尾空白与连续空白合并
- 连字符 / 下划线 / 空格 互换（`self-attention` ↔ `self attention` ↔ `self_attention`）
- 中文全角 / 半角统一（`，` ↔ `,`、`（` ↔ `(`）
- 英文复数尾 `s` / `es`（可选；歧义较大时不规范化）

规范化算法本身的具体实现留给 `wiki-lint`；本 schema 只规定**结果格式**。

### lint 校验（Decision #2 替代版）

- 所有 `canonical_id` 指向必须存在
- 若某页 `canonical_id != null`：该页必须是薄重定向页，`aliases` 应为空或只含本页标题严格同义写法，且 `status` 必须是 `redirect`
- `canonical_id` 必须指向 `canonical_id: null` 的正名页（不允许链式：A → B → C）
- 同一规范化 alias key 不能映射到两个不同 `canonical_id`；冲突时 lint 写入 `review_queue.json type: duplicate`

### 生成时机

- `wiki-lint` 每次扫描重新生成
- 新 entity 创建 / aliases 字段变化后建议触发重建

### 不包含

- 非 entity 类型页面
- inbox draft（inbox 晋升时若涉及 entity，先做 alias matching 再决定晋升路径）
~~~

### Step 4：更新 `.gitignore`

在文件末尾追加（紧贴 `knowledge/.wiki/inbox_index.json` 之后）：

```
knowledge/.wiki/normalized_alias_index.json
```

### Step 5：自检验证

**baseline 用 working tree 状态**，不再用 commit-range（沉淀自 TASK-003 evaluation）。

```bash
cd /Users/zhangjunwu/workspace/llm-wiki/llm-wiki

set +e

echo "=== 0. 白名单文件检查（应只看到这 4 个）==="
diff <(git diff --name-only | sort) <(printf "%s\n" .gitignore wiki-design/01-architecture.md wiki-design/02-workflows.md wiki-design/05-contracts-and-next-steps.md | sort)
echo "diff exit: $? (0 = OK)"

echo "=== 1. 01 字段表含 aliases / canonical_id 两行（应各 ≥ 1）==="
echo "aliases 行: $(grep -cE '^\| \`aliases\`' wiki-design/01-architecture.md)"
echo "canonical_id 行: $(grep -cE '^\| \`canonical_id\`' wiki-design/01-architecture.md)"

echo "=== 2. 01 status 行含 redirect 枚举（应 ≥ 1）==="
echo "命中: $(grep -cE '^\| \`status\`.*redirect' wiki-design/01-architecture.md)"

echo "=== 3. 01 派生数据列表含 normalized_alias_index.json（应 ≥ 1）==="
echo "命中: $(grep -c 'normalized_alias_index.json' wiki-design/01-architecture.md)"

echo "=== 4. 01 entity 别名薄页备注存在（应 ≥ 1）==="
echo "命中: $(grep -c 'entity 别名薄页' wiki-design/01-architecture.md)"

echo "=== 5. 02 摄入资料 Triage 含 entity alias matching（应 ≥ 1）==="
echo "命中: $(grep -c 'entity alias matching' wiki-design/02-workflows.md)"

echo "=== 6. 02 Inbox 晋升段含 alias matching 复用说明（应 ≥ 1）==="
echo "命中: $(grep -c '跨 RFC 协同' wiki-design/02-workflows.md)"

echo "=== 7. 05 字段表 aliases / canonical_id 两行（应各 ≥ 1）==="
echo "aliases 行: $(grep -cE '^\| \`aliases\`' wiki-design/05-contracts-and-next-steps.md)"
echo "canonical_id 行: $(grep -cE '^\| \`canonical_id\`' wiki-design/05-contracts-and-next-steps.md)"

echo "=== 8. 05 status 行含 redirect 枚举（应 ≥ 1）==="
echo "命中: $(grep -cE '^\| \`status\`.*redirect' wiki-design/05-contracts-and-next-steps.md)"

echo "=== 9. 05 Entity 模板 frontmatter 含 aliases / canonical_id（应各 ≥ 1）==="
echo "aliases: $(grep -cE '^aliases:' wiki-design/05-contracts-and-next-steps.md)"
echo "canonical_id: $(grep -cE '^canonical_id:' wiki-design/05-contracts-and-next-steps.md)"

echo "=== 10. 05 答案引用规则含别名引用纠正示例（应 ≥ 1）==="
echo "命中: $(grep -c '别名引用规则\|self-attention（正名' wiki-design/05-contracts-and-next-steps.md)"

echo "=== 11. 05 含 Normalized Alias Index Schema 段（应 = 1）==="
echo "命中: $(grep -cE '^## Normalized Alias Index Schema' wiki-design/05-contracts-and-next-steps.md)"

echo "=== 12. 05 Normalized Alias Index Schema 字段完整（应各 ≥ 1）==="
echo "entries: $(grep -c '\"entries\"' wiki-design/05-contracts-and-next-steps.md)"
echo "canonical_id 字段: $(grep -c 'canonical_id' wiki-design/05-contracts-and-next-steps.md)"
echo "matched_form: $(grep -c 'matched_form' wiki-design/05-contracts-and-next-steps.md)"

echo "=== 13. .gitignore 含 normalized_alias_index.json（应 ≥ 1）==="
echo "命中: $(grep -c 'normalized_alias_index.json' .gitignore)"

echo "=== 14. lint 规则修正（应有 redirect / canonical 不链式 / alias 冲突写 duplicate 三条）==="
echo "redirect 约束: $(grep -c 'status.*必须是.*redirect' wiki-design/05-contracts-and-next-steps.md)"
echo "不允许链式: $(grep -c '不允许链式' wiki-design/05-contracts-and-next-steps.md)"
echo "duplicate 写入: $(grep -cE 'type: duplicate|type.*duplicate' wiki-design/05-contracts-and-next-steps.md)"

echo "=== 15. knowledge/ 不应存在 ==="
if [ -d knowledge/ ]; then echo "FAIL: knowledge/ exists"; else echo "OK: knowledge/ absent"; fi

echo "=== 16. AGENTS.md / 04 / README / rfcs 不应被本轮改动 ==="
git diff --name-only | grep -E '^(AGENTS.md|wiki-design/04-agent-rules.md|wiki-design/README.md|wiki-design/rfcs/)' || echo "  (none)"
```

预期：

- 0：`diff exit: 0`（4 文件且仅这 4 个）
- 1：aliases ≥ 1，canonical_id ≥ 1
- 2：≥ 1
- 3：≥ 1
- 4：≥ 1
- 5：≥ 1
- 6：≥ 1
- 7：aliases ≥ 1，canonical_id ≥ 1
- 8：≥ 1
- 9：aliases ≥ 1，canonical_id ≥ 1
- 10：≥ 1
- 11：= 1
- 12：entries ≥ 1，canonical_id ≥ 1，matched_form ≥ 1
- 13：≥ 1
- 14：三条各 ≥ 1
- 15：`OK: knowledge/ absent`
- 16：`(none)`

### Step 6：Commit 正本改动

```bash
git add wiki-design/01-architecture.md wiki-design/02-workflows.md wiki-design/05-contracts-and-next-steps.md .gitignore

git commit -m "$(cat <<'EOF'
[apply rfc-004] entity aliases + canonical_id + status:redirect + normalized index

Decision 7 条全部落地：

- 01-architecture.md：
  - 字段表加 aliases / canonical_id 两行
  - status 枚举扩 redirect（仅 entity 别名薄页）
  - 派生数据列表加 normalized_alias_index.json
  - 稳定 ID 规则段加 entity 别名薄页备注
  - Cross-ref 表 canonical 列加 canonical_id
- 02-workflows.md：
  - 摄入资料 Triage 加 entity alias matching 子流程
  - Inbox 晋升段引用同一套 alias matching（Decision #6 跨 RFC 协同）
- 05-contracts-and-next-steps.md：
  - Frontmatter 字段表加 aliases / canonical_id
  - Entity 模板 frontmatter 加 aliases / canonical_id + 备注
  - 答案引用格式段加别名引用规则（Decision #5 修正示例）
  - 新增 Normalized Alias Index Schema 整段（schema + lint 替代规则 + 规范化规则）
- .gitignore：追加 knowledge/.wiki/normalized_alias_index.json（派生层）

未引入的部分：
- alias 来源记录仅留正文备注，不新增结构化字段（Decision #7）
- 不改 review_queue / source_manifest schema（RFC 影响范围明确不动）

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
git add wiki-design/tasks/TASK-004-apply-rfc-004.md
git commit -m "[task] TASK-004 done by codex"
```

## 完成后报告格式

把以下内容贴进 `## Execution log by codex · 2026-05-27` 段：

```markdown
## Execution log by codex · 2026-05-27

### 步骤完成情况
- Step 0 Spec review: 通过
- Step 1 01-architecture: done
  - 1a 字段表加 aliases/canonical_id + status 扩枚举: done
  - 1b 稳定 ID 规则段加 entity 别名薄页备注: done
  - 1c 派生数据列表加 normalized_alias_index.json: done
  - 1d Cross-ref 表加 canonical_id: done
- Step 2 02-workflows: done
  - 2a 摄入资料 Triage 加 entity alias matching: done
  - 2b Inbox 晋升段 alias matching 复用 + 跨 RFC 协同备注: done
- Step 3 05-contracts: done
  - 3a 字段表加 aliases/canonical_id + status 扩枚举: done
  - 3b Entity 模板加 aliases/canonical_id + 备注: done
  - 3c 答案引用格式段加别名引用规则: done
  - 3d Normalized Alias Index Schema 新段: done
- Step 4 .gitignore: done
- Step 5 验证: 输出见下

### 验证输出
\`\`\`
<Step 5 全部 grep / diff 输出>
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
- [x] Decision 7 条主体均已映射到 Step 1~4：
  - #1 顺序约束：前置条件要求 HEAD 包含 TASK-003，且 TASK-003 已建立在 TASK-002 之后；`canonical_id` 在 1a / 3a / 3b / 3d 中均按稳定 `id` 引用。
  - #2 lint 规则替换：3d 的 "lint 校验（Decision #2 替代版）" 覆盖 redirect 页约束、指向正名页、不允许链式 canonical、alias 冲突写 `review_queue.json type: duplicate`，没有沿用原 RFC 中会误伤正名页 aliases 的规则。
  - #3 alias 规范化：1c / 2a / 3d / Step 4 覆盖 `normalized_alias_index.json`、规范化规则和 `.gitignore`。
  - #4 `status: redirect`：1a / 3a 扩展 status 枚举，1b / 3b / 3d 说明薄重定向页语义。
  - #5 答案引用示例：3c 使用 `self-attention（正名 [[Attention]]）`，且明确不要把别名包成 wikilink。
  - #6 跨 RFC 协同：2b 改 TASK-003 的 Inbox 晋升段，让 entity 类晋升 / 合并先跑同一套 alias matching。
  - #7 alias 来源记录：3b 只放正文备注，不新增结构化字段，符合 Decision。
- [ ] 05 的目标文件关系树 / 职责划分表没有同步 `knowledge/.wiki/normalized_alias_index.json`。3d 虽然新增 schema 段并声明路径，但当前 05 顶部树和职责表已经列出 `id_index.json` / `inbox_index.json`；如果不把 normalized alias index 也加入，契约页内部会出现"有 schema 段但目标结构表缺项"的不一致。建议在 Step 3 增加一小步：目标文件关系树 `.wiki/` 下加 `normalized_alias_index.json`，职责划分表加一行"entity alias 规范化索引，由 lint 生成，可重建"，并在 Step 5 增加验证。
- [x] 新内容边界基本只来自 RFC-004；除 Decision #6 所需的 Inbox 晋升增量外，没有要求改 RFC-002/003 已落地 schema。

### 可执行性
- [x] Step 2b 的 old string 与 TASK-003 实际产出精确匹配。当前 `wiki-design/02-workflows.md` 的 Inbox 晋升代码块中确有 `   - 合并到已有页面（按标题/alias 匹配找候选）`，可按 spec 替换。
- [x] Step 5 改为 working tree + sorted diff 白名单，能避免 TASK-003 evaluation 暴露的 commit-range baseline leak；第 0 项会直接捕获白名单外文件，第 16 项补查 AGENTS / 04 / README / rfcs。
- [ ] Step 3b 的编辑 anchor 不够精确。当前 05 中没有 `## Entity 模板` heading，实际 heading 是 `### Entity`；同时 `related_ids: []` 在多个模板里重复出现。建议把 anchor 改为当前真实段落 `### Entity`，并给出包含 `id: {{ENTITY_ID}}` 到 `related_ids: []` 的 old_string / new_string，避免误插到 Source / Topic 等模板。
- [x] 其它 anchor 基本清晰：01 的 Frontmatter 表、稳定 ID 规则、派生数据列表、Cross-ref 表；02 的 Triage / Inbox 晋升；05 的 Frontmatter 生命周期字段、答案引用格式、Inbox Index Schema 后插入点；.gitignore 紧贴 `inbox_index.json`。

### 兼容性
- [x] 与 TASK-002 兼容：`canonical_id` 指向稳定页面 `id`，`canonical_id` 被加入 canonical cross-ref 表；`aliases` 明确不是 canonical ID 引用，而是字符串数组，由派生索引处理。
- [x] 与 TASK-003 兼容：`inb_` / Capture Item / Capture Policy / Inbox Index Schema 不被结构性改动；Inbox 晋升只增加 alias matching 复用逻辑。
- [x] `status: redirect` 只扩展 wiki 页面生命周期枚举，不影响 Capture Item 的 `draft/promoted/dropped` 状态集。
- [x] `review_queue.json type: duplicate` 已是现有枚举，不需要新增 queue 类型。

### 风险
- 如果不更新 05 顶部树和职责表，后续 Agent 可能只看结构总览而漏掉 `normalized_alias_index.json`，造成生成 / 忽略规则不一致。
- 如果不修 Step 3b anchor，执行者用字符串替换时容易把 `aliases` / `canonical_id` 插入错误模板；这个风险比普通措辞问题更接近执行失败。
- 强约束 #6 写成 "Step 1d 写 lint 规则" 但实际 lint 规则在 Step 3d；内容没有缺失，但建议顺手改成 Step 3d，减少执行时误读。

### 结论
- 需修改。建议 Claude 先补 05 目标文件关系树 / 职责划分表同步与验证项，并把 Step 3b 的 Entity 模板 anchor 改成当前文件里的精确 old_string 后，再进入 Step 1~7。
