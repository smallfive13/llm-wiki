---
id: task_20260526_001
title: 把 RFC-002/003/004 的 Decision 落到文件并 commit
author: claude
executor: codex
status: done
type: decision-write
created: 2026-05-26
updated: 2026-05-26
related_rfcs:
  - rfc_20260526_002
  - rfc_20260526_003
  - rfc_20260526_004
---

# TASK-001: 把 RFC-002/003/004 的 Decision 落到文件并 commit

## 目标

把用户的 Decision 段写入三份已完成 review 的 RFC，翻转 status 为 accepted，更新 RFC 索引表，并做一次 commit 收尾。

## 前置条件

- 仓库根目录：`/Users/zhangjunwu/workspace/llm-wiki/llm-wiki`
- 当前 HEAD 已包含：RFC-001 Applied marker (`a7b5c40`)、RFC-003 `## Revision v2 by claude` 和 `## Review v2 by codex` 段。这些是 HEAD 中的既有内容，**不得 revert**。
- working tree 在开始执行时应是 clean（无未提交改动）。如不是，先用 `git status` 报告异常，不要自行 stash。
- 已读过 `AGENTS.md`、`wiki-design/rfcs/README.md`、`wiki-design/tasks/README.md`、`wiki-design/rfcs/RFC-005-task-channel.md`，理解 RFC 协作和 Task 通道规则。

## 强约束

违反任一即视为执行失败，应在 Execution log 写明并把 status 改为 failed：

1. **不修改** `## 背景` / `## 提案` / `## 替代方案` / `## 影响范围` 四段原作者正文。
2. **不修改** 任何 `## Review by codex` / `## Review v2 by codex` 段。
3. **不修改** RFC-003 的 `## Revision v2 by claude` 段。
4. **只替换** `## Decision` 段下方的占位文字（如"（待用户填写）"）为下方指定的 Decision 文本。
5. **frontmatter 只动两处**：`status: proposed` → `status: accepted`；`updated` 字段保持 `2026-05-26`（可在后面加 ` # accepted` 注释）。
6. 所有改动**一次性 commit**，commit message 见步骤 6。
7. 不动 `wiki-design/01~05*.md` 任何 pre-RFC baseline 文件。
8. 不动 RFC-005、tasks/ 目录任何文件。

## 步骤

### Step 1：RFC-002

文件：`wiki-design/rfcs/RFC-002-stable-page-ids.md`

1. frontmatter：`status: proposed` → `status: accepted`
2. 替换 `## Decision` 段下方的整行 `（待用户填写）` 为：

```markdown
Accepted with conditions. 采纳 RFC-002 的核心方向（页面稳定 ID 作为机器主键，wikilink 作为显示层），但 apply 时必须落实以下修正：

1. **ID 永不变**：`id` 一旦创建，不随 slug、title、path 任何变化而改变。slug 仅为创建时的可读提示，不是当前标题的镜像。文档和 schema 应显式声明这一约束。
2. **source 单主键**：source 类型页面规定 `id == source_id`，避免 `source_manifest.source_id` 与页面 frontmatter `id` 长期漂移。其它页面类型不受此约束。
3. **字段命名收敛**：把建议的 `sources_by_id` 改为 `source_ids`，对应新增 `related_ids`，作为 canonical 字段；现有 `sources` / `related` 改为可选的 Obsidian 显示层（保留 wikilink 写法但不参与 lint 完整性校验）。
4. **派生层归位**：`id_index.json` 路径加入 `.gitignore`，与 `cache.json` 等同列为可重建派生层。
5. **拆分语义**：拆出的新页面拿新 ID；旧页面如部分内容保留，原 ID 不变；如完全被取代，标 `status: archived` + `superseded_by: [新 ID]`。
6. **合并语义**：被合并页保留壳 frontmatter，`status: archived` + `superseded_by: [合并目标 ID]`，正文清空或仅留一行重定向说明。
7. **冲突命名**：同日同类型同 slug 冲突时追加短序号，例如 `ent_20260526_attention_002`，由 lint 强制全局唯一。
8. **canonical 边界完整化**：apply 时需逐一标注 `review_queue.evidence.page`、答案引用 path、未来图谱节点 key 是 canonical ID 还是仅显示 path，不留模糊地带。

Apply 责任：由 codex 或 claude 任一执行，commit message 必须带 `[apply rfc-002]` 前缀。

用户确认：paic.small.five@gmail.com，2026-05-26。
```

### Step 2：RFC-003

文件：`wiki-design/rfcs/RFC-003-inbox-capture-layer.md`

1. frontmatter：`status: proposed` → `status: accepted`
2. 替换 `## Decision` 段下方的整行 `（待用户填写。如同意 Revision v2 方向，建议把 status 改为 discussing 并发给 codex 复核。）` 为：

```markdown
Accepted, apply per Revision v2. Codex 已在 Review v2 中确认赞同 9 条修订。

落地依据：以 Revision v2 "Apply 边界" 段为准；原 Proposal 第 2 节"被动 capture 例外"在 apply 时由 Revision v2 第 1 节"低摩擦 capture，需明确授权"整段替换。

补充 Codex Review v2 提出的两条 apply 时约束：

1. **PII 正则非完整方案**：`capture_policy.json` 中 `exclude_patterns` 的默认正则仅是初始规则。apply 时相关文档（`05-contracts-and-next-steps.md` Capture Policy Schema 段）必须明确标注"非完整 PII 检测，需 lint 规则、人工规则和组织安全规范共同保障"。Agent 不得把这套正则当作唯一兜底。
2. **`exclude_paths` 默认值收紧**：Revision v2 示例 `capture_policy.json` 中 `exclude_paths` 里的 `"wiki/decisions/**"` apply 时删除。决策类讨论是 capture 的高价值场景，不应被默认排除。如团队后续需要排除，自行追加。

Apply 顺序：建议在 RFC-002 apply 完成后开始，inbox ID prefix `inb_` 才能纳入统一规范。如先于 RFC-002，按 Revision v2 第 5 节"未 RFC-002 时的备用 ID 规则"过渡。

Apply 责任：由 codex 或 claude 任一执行，commit message 必须带 `[apply rfc-003]` 前缀。

用户确认：paic.small.five@gmail.com，2026-05-26。
```

### Step 3：RFC-004

文件：`wiki-design/rfcs/RFC-004-entity-aliases.md`

1. frontmatter：`status: proposed` → `status: accepted`
2. 替换 `## Decision` 段下方的整行 `（待用户填写）` 为：

```markdown
Accepted with conditions, gated on RFC-002. 采纳 RFC-004 的核心方向（entity aliases 作为一等公民、canonical_id 处理别名重定向），但必须满足以下条件：

1. **顺序约束**：RFC-002 必须先 apply 完成，本 RFC 才能开始 apply。`canonical_id` 字段值必须是 RFC-002 定义的稳定 ID 格式。
2. **lint 规则修正**（采纳 Codex 提议，替换原 RFC 提案 "3. lint 校验" 中第二条）：
   - 如果 `canonical_id != null`：该页必须是薄重定向页，`aliases` 应为空或只含本页标题的严格同义写法。
   - `canonical_id` 必须指向 `canonical_id: null` 的正名页。
   - 不允许链式 canonical（A→B→C）。
   - 同一 alias 字符串不能同时出现在两个正名 entity 的 `aliases` 中；冲突时 lint 写入 `review_queue.json type: duplicate`。
3. **alias 规范化（新增）**：lint / ingest 维护派生 `normalized_alias_index`，覆盖大小写、空格、连字符、中文全/半角、英文复数。原始 `aliases` 字段保留人类写法，规范化索引仅用于匹配。
4. **薄页 status 新枚举值**：别名薄页 frontmatter 用 `status: redirect`（新增枚举），不参与主图谱节点，不计入综合，仅作入口跳转。`status` 枚举更新到 `01-architecture.md` 字段表。
5. **答案引用示例修正**：99% 情况下别名不是独立页面，回答中遇到别名应写为 `self-attention（正名 [[Attention]]）` 而非 `[[self-attention]]（正名 [[Attention]]）`，避免制造不存在的 wikilink。原 RFC 第 4 节示例同步修正。
6. **跨 RFC 协同**：如果 RFC-003 accepted，inbox 晋升 workflow 必须复用同一套 alias matching，不等到 ingest。
7. **alias 来源记录**：不强制，但允许在正文或未来结构化字段记录某 alias 来自哪个 source，避免 Agent 自造同义词。

Apply 责任：由 codex 或 claude 任一执行（必须在 RFC-002 apply 完成后），commit message 必须带 `[apply rfc-004]` 前缀。

用户确认：paic.small.five@gmail.com，2026-05-26。
```

### Step 4：更新 RFC 索引

文件：`wiki-design/rfcs/README.md`

把索引表中 RFC-002 / 003 / 004 三行的 `status` 列从 `proposed` 改为 `accepted`。RFC-001 / RFC-005 行不动。

### Step 5：自检验证

跑：

```bash
cd /Users/zhangjunwu/workspace/llm-wiki/llm-wiki

# 1. 三份 RFC 的 status 都应该是 accepted
grep -E "^status:" wiki-design/rfcs/RFC-00[234]*.md

# 2. RFC-001 的 Applied 段必须保留为 a7b5c40
grep "Applied in a7b5c40" wiki-design/rfcs/RFC-001-multi-agent-collaboration.md

# 3. RFC-003 的 Revision v2 和 Review v2 段必须保留
grep -E "^## (Revision v2 by claude|Review v2 by codex)" wiki-design/rfcs/RFC-003-inbox-capture-layer.md

# 4. README 索引表 RFC-002~004 status 应该是 accepted
grep -E "RFC-00[234]" wiki-design/rfcs/README.md

# 5. baseline 文件不应被改动（diff 应为空）
git diff wiki-design/01-architecture.md wiki-design/02-workflows.md wiki-design/04-agent-rules.md wiki-design/05-contracts-and-next-steps.md wiki-design/README.md
```

预期：
- 第 1 步：3 行 `status: accepted`
- 第 2、3 步：各 1 行命中
- 第 4 步：RFC-002~004 三行的 status 列都是 accepted
- 第 5 步：无输出（baseline 未被动）

### Step 6：Commit

```bash
git add wiki-design/rfcs/

git commit -m "$(cat <<'EOF'
[rfcs] decisions accepted for RFC-002/003/004 + bookkeeping

- RFC-001: Applied marker updated to commit a7b5c40
- RFC-002: accepted with 8 apply conditions
  (id stability, source_id unification, field naming, derived layer in .gitignore,
   split/merge semantics, name conflict suffix, canonical boundary completeness)
- RFC-003: Revision v2 (opt-in capture, PII guard, capture item schema, archive layout)
  + Codex Review v2 confirming acceptance
  + accepted with 2 apply notes (PII regex not exhaustive, default exclude_paths trimmed)
- RFC-004: accepted with 7 apply conditions
  (gated on RFC-002, lint rule fix, alias normalization, status: redirect,
   citation example fix, cross-RFC sync with RFC-003, optional alias source tracking)
- wiki-design/rfcs/README.md: status column updated to accepted for RFC-002~004

Co-Authored-By: Codex <noreply@openai.com>
EOF
)"
```

### Step 7：把 task 本身推进到 done

完成 Step 6 后：

1. frontmatter `status: pending` → `status: done`
2. `updated:` 改为今天
3. 追加 `## Execution log by codex · 2026-05-26` 段（见下方格式）
4. 再做一次 commit：

```bash
git add wiki-design/tasks/TASK-001-write-rfc-decisions.md
git commit -m "[task] TASK-001 done by codex"
```

## 完成后报告格式

把以下内容贴进 `## Execution log by codex · 2026-05-26` 段：

```markdown
## Execution log by codex · 2026-05-26

### 步骤完成情况
- Step 1 RFC-002: <done | skipped | failed: reason>
- Step 2 RFC-003: <done | skipped | failed: reason>
- Step 3 RFC-004: <done | skipped | failed: reason>
- Step 4 README index: <done | skipped | failed: reason>

### 验证输出
\`\`\`
<Step 5 全部 grep / git diff 输出>
\`\`\`

### Commit
- Step 6 commit sha: <sha>
- Step 7 commit sha: <sha>

### 偏离 / 异常
<列出与指令不一致的地方；没有就写"无"。>
```

## Execution log by codex · 2026-05-26

### 步骤完成情况
- Step 1 RFC-002: done
- Step 2 RFC-003: done
- Step 3 RFC-004: done
- Step 4 README index: done

### 验证输出
```
$ grep -E "^status:" wiki-design/rfcs/RFC-00[234]*.md
wiki-design/rfcs/RFC-002-stable-page-ids.md:status: accepted
wiki-design/rfcs/RFC-003-inbox-capture-layer.md:status: accepted
wiki-design/rfcs/RFC-003-inbox-capture-layer.md:status: draft                                    # inbox 内只有 draft / promoted / dropped
wiki-design/rfcs/RFC-004-entity-aliases.md:status: accepted
wiki-design/rfcs/RFC-004-entity-aliases.md:status: active
wiki-design/rfcs/RFC-004-entity-aliases.md:status: active

$ grep "Applied in a7b5c40" wiki-design/rfcs/RFC-001-multi-agent-collaboration.md
## Applied in a7b5c40

$ grep -E "^## (Revision v2 by claude|Review v2 by codex)" wiki-design/rfcs/RFC-003-inbox-capture-layer.md
## Revision v2 by claude · 2026-05-26
## Review v2 by codex · 2026-05-26

$ grep -E "RFC-00[234]" wiki-design/rfcs/README.md
| [rfc_20260526_002](RFC-002-stable-page-ids.md) | 给 Wiki 页面引入稳定 ID | accepted | claude | `wiki-design/01-architecture.md`, `wiki-design/05-contracts-and-next-steps.md` |
| [rfc_20260526_003](RFC-003-inbox-capture-layer.md) | 引入 inbox 缓冲层，允许低门槛 capture | accepted | claude | `AGENTS.md`, `wiki-design/01-architecture.md`, `wiki-design/02-workflows.md`, `wiki-design/04-agent-rules.md`, `wiki-design/05-contracts-and-next-steps.md` |
| [rfc_20260526_004](RFC-004-entity-aliases.md) | 给 entity 加 aliases 和 canonical_id | accepted | claude | `wiki-design/01-architecture.md`, `wiki-design/02-workflows.md`, `wiki-design/05-contracts-and-next-steps.md` |
以下议题已在 review 中识别但尚未拆成 RFC。当 RFC-002 ~ RFC-004 落地后再视情况启动。

$ git diff wiki-design/01-architecture.md wiki-design/02-workflows.md wiki-design/04-agent-rules.md wiki-design/05-contracts-and-next-steps.md wiki-design/README.md
```

### Commit
- Step 6 commit sha: f387851
- Step 7 commit sha: this commit; exact sha reported by codex after commit creation

### 偏离 / 异常
- Step 5 第 1 条 grep 使用 `^status:`，会额外命中 RFC-003 / RFC-004 中 fenced 示例的 `status: draft` / `status: active`。未修改这些 Proposal 示例；三份 RFC frontmatter 均已是 `status: accepted`。
- Step 7 commit sha 无法在同一个 commit 内容中预先写入精确值，因为 commit sha 只有提交完成后才产生。实际 sha 由 Codex 完成后在最终回复报告。

## Evaluation by claude · YYYY-MM-DD

（待评估者填写）
