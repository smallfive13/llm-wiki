---
id: task_20260526_003
title: Apply RFC-003 — 把 capture 机制和 inbox 缓冲层落到 AGENTS / 01 / 02 / 04 / 05
author: claude
executor: codex
status: done
type: apply
created: 2026-05-27
updated: 2026-05-27  # v2 after codex spec review v1
related_rfcs:
  - rfc_20260526_003
---

# TASK-003: Apply RFC-003 — capture 机制 + inbox 缓冲层

## 目标

把 RFC-003 落到 5 个正本，以 **Revision v2** 为落地依据（不是原 Proposal 第 2 节）：

- `AGENTS.md`
- `wiki-design/01-architecture.md`
- `wiki-design/02-workflows.md`
- `wiki-design/04-agent-rules.md`
- `wiki-design/05-contracts-and-next-steps.md`

执行完成后，Agent 能从 AGENTS.md 读到 capture 规则、从 01 知道 `inb_` prefix、从 02 知道被动 capture 和 inbox 晋升流程、从 04 知道会话开始读 inbox_index.json、从 05 拿到 Capture Item Schema 和 Capture Policy Schema 两份完整契约。

## 前置条件

- 仓库根目录：`/Users/zhangjunwu/workspace/llm-wiki/llm-wiki`
- HEAD 包含 **TASK-002 已 done**（commit `5633239` 及之后），即 01 已有"稳定 ID 规则" / prefix 表 / Cross-ref 字段说明三节，05 已有 capture_item id 所依赖的 `inb_` 兼容点。
- working tree clean
- 已读 `wiki-design/rfcs/RFC-003-inbox-capture-layer.md`（重点是 `## Revision v2 by claude` 段 + `## Decision` 段两条 apply-time 约束）
- 已读 `wiki-design/tasks/README.md` 理解 task 规则
- 已读 TASK-002 的 Execution log 和 Evaluation，理解 apply 类 task 工作流惯例
- **本 task 不动 RFC-002 / RFC-004 相关内容**

## 强约束

违反任一即视为执行失败，应在 Execution log 写明并把 status 改为 failed：

1. **只动 6 个文件**：`AGENTS.md`、`wiki-design/01-architecture.md`、`wiki-design/02-workflows.md`、`wiki-design/04-agent-rules.md`、`wiki-design/05-contracts-and-next-steps.md`、`.gitignore`。其它一律不动。
2. **不创建** `knowledge/` 任何文件或目录（属于 TASK-005）。
3. **不动** `wiki-design/README.md`、任何 RFC 文件、**其它** TASK 文件。
   - 本 TASK-003 文件本身按 Step 0 / 7 / 8 允许编辑（追加 Spec review、推进 status、追加 Execution log）。
4. **保留** 5 个正本中所有不被本 task 覆盖的章节段落。
5. **必须先经 Codex spec review（Step 0）**：在 Step 0 通过前 status 保持 pending，不可执行 Step 1~7。
6. **落地依据**：以 RFC-003 **Revision v2** 段为准；**不**按原 Proposal 第 2 节"被动 capture 例外"落地。具体替换关系见各 Step。
7. **两条 apply-time 约束必须体现**：
   - PII 正则非完整：`capture_policy.json` 默认 `exclude_patterns` 的描述必须显式标注"非完整 PII 检测"。
   - 默认 `exclude_paths` 收紧：示例值为 `[]`（空数组）；**不得**默认放 `"wiki/decisions/**"`。
8. **不引入** RFC-002 / RFC-004 之外的新概念。`inb_` prefix 是 RFC-003 在 RFC-002 prefix 表上的扩展，可加。
9. **schema 一致性**：所有新增的 frontmatter / JSON 例子必须与 TASK-002 落地后的 01/05 schema 一致（含 `id` 字段格式）。
10. 三个 commit 分别：Step 0 Spec review（codex 写时自行 commit）/ Step 7 正本改动 / Step 8 task status 推进。

## 工作流

```
Step 0  Codex spec review (本 task 文件，追加 Spec review 段) + 单独 commit
        │
        │  通过 → Step 1
        │  需修改 → Claude 改 spec → 重新进入 Step 0
        │
        ▼
Step 1~5  Codex 执行 6 个文件的编辑（Step 5 含 5d/5e，覆盖 05 + .gitignore）
        │
        ▼
Step 6  自检验证
        │
        ▼
Step 7  Commit 正本改动（6 文件一次性 commit，[apply rfc-003] 前缀）
        │
        ▼
Step 8  推进 task status pending → done + 追加 Execution log + commit
```

## 步骤

### Step 0：Spec review（执行前必跑）

在本 task 文件末尾追加：

```markdown
## Spec review by codex · 2026-05-27

### 完整性
- [ ] Revision v2 段所有 apply 边界是否全部覆盖
- [ ] Decision 段两条 apply-time 约束（PII 非完整 / exclude_paths 默认收紧）是否落实到 spec
- [ ] 新内容是否仅来自 RFC-003（不混 002/004）

### 可执行性
- [ ] 每个 Step 是否有明确的 anchor / 新内容
- [ ] 验证步骤是否可机械跑（set +e / grep -c / 显式 echo "应为 X"）

### 风险
- 列出可能踩坑的地方

### 结论
- 通过 / 需修改 (列出建议)
```

如果"需修改"，Codex 不要自行改 spec；只给出建议，由 Claude 修订。Spec review 段一旦写入，**status 字段不改**（保持 pending）。Codex 自行 commit 这次 Spec review 改动（commit message：`[task] TASK-003 spec review by codex (conclusion: <通过/需修改>)`）。

### Step 1：更新 `AGENTS.md`

在现有 "知识库写入规则" 段末尾、"## Commit 规则" 之后是另一个 `##` 段——确认 "知识库写入规则" 是文件最末一段。在该段末尾追加一个新的 `###` 子节：

```markdown
### 低摩擦 capture（capture 缓冲层）

机制定义见 [RFC-003](wiki-design/rfcs/RFC-003-inbox-capture-layer.md) Revision v2。

- **默认**：Agent 识别到值得 capture 的内容时，只在回答末尾**建议** capture，格式：
  ```
  💡 建议 capture：<一句话摘要> · 类型 suggested: <topic|entity|decision|...>
     回复 "存" 或 "capture" 即写入 inbox/。
  ```
- **自动 capture（opt-in）**：仅当项目根目录存在 `knowledge/.wiki/capture_policy.json` 且其中 `auto_capture: true` 时，Agent 才可直接写 `knowledge/inbox/`。
- **自动 capture 也必须可见**：即使开启 auto，每次写入必须在回答末尾输出：
  ```
  ✏️ 已 capture：inbox/<filename> · <一句话摘要>
  ```
  禁止"无声写入"。
- **PII 兜底**：内容包含密钥、token、客户姓名、身份证号、邮箱、电话、明确标记的内部业务信息时，**无论 auto_capture 开关**，一律降级为"建议 capture"模式，不自动写入。规则化的 PII pattern 由 lint 维护，**注意：内置正则只是初始规则，不代表完整 PII 检测**。
- **严禁绕过 inbox 直接写 `knowledge/wiki/`**。

inbox 写入不算"长期沉淀"，仅是 capture 缓冲层。promotion workflow 见 [wiki-design/02-workflows.md](wiki-design/02-workflows.md) "Inbox 晋升" 段。Capture Item / Capture Policy schema 见 [wiki-design/05-contracts-and-next-steps.md](wiki-design/05-contracts-and-next-steps.md) "Capture Item Schema" / "Capture Policy Schema" 段。
```

### Step 2：更新 `wiki-design/01-architecture.md`

#### 2a：在 "稳定 ID 规则" 子节的 prefix 表末尾加 `inb_` 行

找到现有 prefix 表（应有 source / entity / topic / comparison / synthesis / decision / query / open-question 共 8 行）。在 `open-question` 行**之后**追加：

```markdown
| inbox（capture item，非 wiki 页面类型） | `inb_` | `inb_20260526_153012_attention-complexity` |
```

注意：inbox 不是 wiki 页面类型，不进"页面类型"表；只在 prefix 表里出现一行以保持 ID 命名空间统一。

#### 2b：在 "稳定 ID 规则" 子节的 source 单主键约束段后插入一行 inbox 备注

在 `**source 单主键约束**：...` 这段的下方（**同日冲突** 段之前）插入：

```markdown
**inbox capture item**：`inb_` prefix 的文件不属于 `knowledge/wiki/`，独立放在 `knowledge/inbox/`，schema 见 [05-contracts-and-next-steps.md](05-contracts-and-next-steps.md) "Capture Item Schema" 段。capture item 不参与主图谱、不作引用来源、不进 wiki 页面 lint。
```

#### 2c：在 "正本与派生层" 段的"知识正本"列表末尾加 inbox 相关条目

找到"知识正本"列表（应已有 `knowledge/raw/source_manifest.json` / `knowledge/wiki/**` / `knowledge/.wiki/review_queue.json` 等条目）。在该列表末尾追加两行：

```text
knowledge/inbox/**
knowledge/.wiki/capture_policy.json
```

并在"派生数据"列表末尾（`knowledge/.wiki/id_index.json` 之后）追加：

```text
knowledge/.wiki/inbox_index.json
```

### Step 3：更新 `wiki-design/02-workflows.md`

#### 3a：新增 "被动 capture（建议 / 自动）" 段

在现有"结晶化"段**之前**插入新段（保持 `## h2` 级别）：

~~~markdown
## 被动 capture（建议 / 自动）

触发：普通对话中 Agent 识别到值得长期保留的片段（设计取舍 / 排查结论 / 明确事实 / 用户决策性发言）。机制定义见 [RFC-003](rfcs/RFC-003-inbox-capture-layer.md) Revision v2 + AGENTS.md "低摩擦 capture" 段。

流程：

```
检查 knowledge/.wiki/capture_policy.json 是否存在 + auto_capture 开关
  ├── 不存在 / auto_capture: false → 默认"建议 capture"模式
  │     └── 在回答末尾输出：💡 建议 capture：<摘要> · 类型 suggested: <type>
  │           用户回复"存"/"capture" → 写 knowledge/inbox/YYYYMMDD-HHmmss-<slug>.md
  │
  └── auto_capture: true → 检查 exclude_patterns / exclude_paths
        ├── 命中任一 PII 正则 / 排除路径 → 强制降级为"建议 capture"
        └── 未命中 → 直接写 inbox/
              └── 在回答末尾输出：✏️ 已 capture：inbox/<filename> · <摘要>
```

约束：

- 写入路径只能是 `knowledge/inbox/`，**严禁绕过 inbox 直接写 `knowledge/wiki/`**
- 文件命名：`YYYYMMDD-HHmmss-<slug>.md`，秒级时间戳；同秒冲突追加 `-NN`
- 不允许"无声写入"，必须在回答末尾可见报告
- frontmatter 必须含 `id: inb_<ts>_<slug>` / `type: inbox` / `status: draft` 等字段（详见 [05-contracts-and-next-steps.md](05-contracts-and-next-steps.md) "Capture Item Schema"）
~~~

#### 3b：在 3a 新增段之后、"结晶化" 段之前再加 "Inbox 晋升" 段

~~~markdown
## Inbox 晋升

触发语义：

```
消化 inbox
整理一下 inbox
把 inbox 里的东西梳理进 wiki
```

流程：

```
列出所有 status: draft 的 inbox 文件（读 knowledge/inbox/*.md）
-> 按主题分组（Agent 建议）
-> 对每组提议：
   - 晋升为 wiki/topics/、wiki/entities/、wiki/decisions/ 等新页面
   - 合并到已有页面（按标题/alias 匹配找候选）
   - 丢弃（确认无价值）
-> 用户决策每一项
-> apply：
   - 晋升：移动内容到 wiki/<type>/，新建页面带完整 frontmatter（含 RFC-002 stable id）；
     原 inbox 文件移动到 knowledge/inbox/archive/promoted/<filename>，frontmatter 改 status: promoted
   - 合并：内容并入目标页；原 inbox 文件移到 archive/promoted/，可在目标页 supersedes 中记 inbox id
   - 丢弃：原 inbox 文件移到 archive/dropped/<filename>，frontmatter 改 status: dropped
```

定期触发：建议每周一次，或 `knowledge/inbox/*.md` 文件数超过 `capture_policy.max_inbox_files`（默认 100）时主动提醒。

健康度统计**只计 `knowledge/inbox/*.md`**（即 draft 状态），archive 不计入告警阈值。
~~~

### Step 4：更新 `wiki-design/04-agent-rules.md`

#### 4a：在"读取规则"段的读取列表末尾追加 inbox_index.json

找到当前读取列表（应已有 `.wiki-schema.md` / `purpose.md` / `index.md` / `overview.md` / `log.md` / `.wiki/review_queue.json`）。在 `.wiki/review_queue.json` 之后追加一行：

```text
knowledge/.wiki/inbox_index.json
```

#### 4b：在"写入规则"段末尾追加 capture 例外说明

在该段（"只有在用户明确表达..." 列表）末尾追加：

```markdown
**capture 例外**：被动 capture 的写入目标是 `knowledge/inbox/`，不算"长期沉淀"，规则见 [AGENTS.md](../AGENTS.md) "低摩擦 capture" 段和 [02-workflows.md](02-workflows.md) "被动 capture" 段。inbox 写入仍受 `capture_policy.json` 与 PII 兜底约束，不能绕过去直接写 `knowledge/wiki/`。
```

### Step 5：更新 `wiki-design/05-contracts-and-next-steps.md`

#### 5a：更新 "目标文件关系" 树和职责划分表

在 `log.md` 之后、`raw/` 之前插入 inbox 块：

```text
  inbox/
    archive/
      promoted/
      dropped/
```

在 `.wiki/` 块内 `review_queue.json` 之后插入两行：

```text
    capture_policy.json
    inbox_index.json
```

（与已有 `cache.json` / `search_index/` / `lightrag/` / `id_index.json` 共处一块）

在"职责划分"表末尾追加 4 行：

```markdown
| `knowledge/inbox/` | capture 缓冲层；draft 文件等待 promotion | 是 |
| `knowledge/inbox/archive/{promoted,dropped}/` | 归档；不计入健康度告警阈值 | 是 |
| `knowledge/.wiki/capture_policy.json` | capture 控制策略，团队级共享 | 是 |
| `knowledge/.wiki/inbox_index.json` | inbox 索引，由 lint 生成，可重建 | 否 |
```

#### 5b：新增 "Capture Item Schema" 整段

插入位置：在 "Source Manifest Schema" 段之后、"Frontmatter 生命周期字段" 段之前。整段如下（保持 `## h2` 级别）：

~~~markdown
## Capture Item Schema

Inbox 文件不算 `wiki/**/*.md` 页面，独立为 **capture item**，schema 不混入"页面类型"表。

### 位置

`knowledge/inbox/`，平级于 `wiki/`、`raw/`、`maps/`、`.wiki/`。

进 Git 知识正本，但**不计入主图谱**、**不参与综合**、**不作为引用来源**。

### 文件命名

`YYYYMMDD-HHmmss-<slug>.md`，时间戳到秒级。同秒冲突时追加 `-NN` 短序号。

### 归档目录

promoted / dropped 文件移动到 `knowledge/inbox/archive/<status>/<filename>`：

```
knowledge/inbox/
├── 20260526-153012-attention-complexity.md     # status: draft
├── 20260526-160045-rag-vs-graphrag.md          # status: draft
└── archive/
    ├── promoted/
    │   └── 20260520-091200-tx-isolation.md     # status: promoted
    └── dropped/
        └── 20260518-143300-misc.md             # status: dropped
```

健康度统计**只计 `knowledge/inbox/*.md`**（即 draft 状态），archive 不计入告警阈值。

### Frontmatter 字段

```yaml
---
id: inb_20260526_153012_attention-complexity     # inb_ prefix，slug 紧跟秒级时间戳
type: inbox                                       # 不进入 wiki 页面类型枚举
status: draft                                     # draft | promoted | dropped
created: 2026-05-26
captured_from: "chat-20260526-1530"               # 来源会话/上下文标识，可选
confidence: low
review: true
suggested_target_type: topic                      # Agent 建议晋升后的类型
suggested_target_title: "Attention 复杂度讨论"
---
```

| 字段 | 说明 |
| --- | --- |
| `id` | `inb_YYYYMMDD_HHmmss_<slug>`；inb_ 是 [01-architecture.md](01-architecture.md) "稳定 ID 规则" prefix 表的扩展 |
| `type` | 固定为 `inbox`；**不参与 wiki 页面 lint**（不校验 sources / related 完整性） |
| `status` | `draft` / `promoted` / `dropped` |
| `created` | 创建日期 |
| `captured_from` | 来源会话或上下文标识，可选 |
| `confidence` | `low` / `medium` / `high`，默认 `low` |
| `review` | 默认 `true` |
| `suggested_target_type` | Agent 建议晋升时的目标页面类型（`topic` / `entity` / `decision` / ...） |
| `suggested_target_title` | Agent 建议晋升时的标题 |

正文：不超过 30 行。可带 `[[wikilink]]`，但不强制。

### Capture item 不参与的 lint

- sources / related 完整性
- canonical cross-ref 校验
- 主图谱节点统计
- evidence_count 一致性

参与的 lint：

- `knowledge/inbox/*.md` 文件数（仅 draft 状态）
- 最老 draft 年龄
- 超过阈值（默认 30 天）未处理 draft 告警
- `capture_policy.json` schema 校验
~~~

#### 5c：新增 "Capture Policy Schema" 整段

紧跟 5b 之后插入：

~~~markdown
## Capture Policy Schema

路径：`knowledge/.wiki/capture_policy.json`

用途：控制 Agent 是否被允许直接写入 `knowledge/inbox/`，以及哪些内容/路径默认不自动 capture。属于知识正本（进 Git，团队级可共享）。

### 顶层格式

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
  "updated_at": "2026-05-26T15:00:00+08:00"
}
```

### 字段约束

| 字段 | 含义 |
| --- | --- |
| `version` | schema 版本，当前 `1` |
| `auto_capture` | 是否允许 Agent 直接写 `knowledge/inbox/`，**默认 `false`**（必须用户主动 opt-in） |
| `exclude_patterns` | 正则数组，命中任一就降级为"建议 capture"模式，不自动写入 |
| `exclude_paths` | glob 数组，Agent 在涉及这些路径的对话中不自动 capture。**默认空数组**——决策类讨论是 capture 的高价值场景，不应被默认排除 |
| `max_inbox_files` | inbox/ 文件超过此数时停止自动 capture，强制 promotion；默认 100 |
| `updated_at` | ISO 8601 时间戳 |

### 重要约束（apply 时必须显式标注）

> **`exclude_patterns` 中的默认正则仅是初始规则，不代表完整 PII 检测**。生产用法必须由 lint 规则、人工 review 规则和组织安全规范共同保障。Agent 不得把这套正则当作唯一 PII 兜底。

### PII 降级流程

```
对话内容 → 命中 exclude_patterns 任一正则？
  ├── 是 → 强制降级为"建议 capture"模式（无论 auto_capture 开关）
  └── 否 → 检查 exclude_paths
        ├── 命中 → 强制降级为"建议 capture"
        └── 未命中 → 按 auto_capture 开关决定写入或建议
```
~~~

#### 5d：新增 "Inbox Index Schema" 整段

紧跟 5c 之后插入（保持 `## h2` 级别）：

~~~markdown
## Inbox Index Schema

路径：`knowledge/.wiki/inbox_index.json`

用途：Agent 会话开始读取的 inbox 高密度索引；提供 draft 数量、最老 draft 年龄和最近 N 条 draft 轻摘要，避免 Agent 把全部 draft 正文拉进上下文。

**派生层**（由 `wiki-lint` 扫描 `knowledge/inbox/*.md` 生成；可重建；进 `.gitignore`，不作为知识正本）。

### 顶层格式

```json
{
  "version": 1,
  "draft_count": 12,
  "oldest_draft_age_days": 8,
  "recent_drafts": [
    {
      "filename": "20260526-153012-attention-complexity.md",
      "summary": "Attention 复杂度讨论",
      "captured_at": "2026-05-26T15:30:12+08:00"
    }
  ],
  "updated_at": "2026-05-26T16:00:00+08:00"
}
```

### 字段约束

| 字段 | 含义 |
| --- | --- |
| `version` | schema 版本，当前 `1` |
| `draft_count` | `knowledge/inbox/*.md` 中 `status: draft` 的文件数；**不含** `archive/` |
| `oldest_draft_age_days` | 最老 draft 距今天数，按 frontmatter `created` 计算 |
| `recent_drafts[]` | 最近 N 条 draft 的轻摘要数组，默认 `N = 10` |
| `recent_drafts[].filename` | inbox 文件名（不含路径） |
| `recent_drafts[].summary` | 摘要文本，优先来自 frontmatter `suggested_target_title`，回退到正文首句 |
| `recent_drafts[].captured_at` | ISO 8601 时间戳，优先 frontmatter `created`，回退到文件名解析的秒级时间戳 |
| `updated_at` | 索引重建时刻，ISO 8601 |

### 生成时机

- `wiki-lint` 每次扫描时重新生成
- 新 capture 写入 / promotion / drop 后建议触发重建

### 不包含

- draft 正文（保持索引高密度，正文按需另读）
- `archive/promoted/` 或 `archive/dropped/` 的文件
~~~

#### 5e：更新 `.gitignore`

`inbox_index.json` 属于派生层（同 `id_index.json`）。在 `.gitignore` 末尾追加（紧贴 `knowledge/.wiki/id_index.json` 之后）：

```
knowledge/.wiki/inbox_index.json
```

注意这是本 task 唯一动到 5 个正本之外的文件，对应 强约束 #1 把白名单从 5 个扩到 6 个的来源。

### Step 6：自检验证

```bash
cd /Users/zhangjunwu/workspace/llm-wiki/llm-wiki

set +e

echo "=== 1. AGENTS.md 含'低摩擦 capture'子节（应 ≥ 1）==="
echo "命中: $(grep -c '^### 低摩擦 capture' AGENTS.md)"

echo "=== 2. AGENTS.md 引用 RFC-003 + 02-workflows + 05-contracts（每项应 ≥ 1 次命中）==="
echo "  RFC-003-inbox-capture-layer 命中次数: $(grep -oE 'RFC-003-inbox-capture-layer' AGENTS.md | wc -l)"
echo "  02-workflows.md 命中次数: $(grep -oE '02-workflows.md' AGENTS.md | wc -l)"
echo "  05-contracts-and-next-steps.md 命中次数: $(grep -oE '05-contracts-and-next-steps.md' AGENTS.md | wc -l)"

echo "=== 3. 01-architecture.md prefix 表含 inb_ 行（应 ≥ 1）==="
echo "命中: $(grep -c '| \`inb_\` |' wiki-design/01-architecture.md)"

echo "=== 4. 01-architecture.md inbox capture item 备注存在（应 ≥ 1）==="
echo "命中: $(grep -c 'inbox capture item' wiki-design/01-architecture.md)"

echo "=== 5. 01-architecture.md 派生数据列表含 inbox_index.json（应 ≥ 1）==="
echo "命中: $(grep -c 'knowledge/.wiki/inbox_index.json' wiki-design/01-architecture.md)"

echo "=== 6. 02-workflows.md 含两段新 h2（应 = 2）==="
echo "命中: $(grep -cE '^## (被动 capture（建议 / 自动）|Inbox 晋升)' wiki-design/02-workflows.md)"

echo "=== 7. 04-agent-rules.md 读取列表含 inbox_index.json（应 ≥ 1）==="
echo "命中: $(grep -c 'knowledge/.wiki/inbox_index.json' wiki-design/04-agent-rules.md)"

echo "=== 8. 04-agent-rules.md 写入规则段含 'capture 例外'（应 ≥ 1）==="
echo "命中: $(grep -c 'capture 例外' wiki-design/04-agent-rules.md)"

echo "=== 9. 05 含 Capture Item / Capture Policy / Inbox Index 三段（应 = 3）==="
echo "命中: $(grep -cE '^## (Capture (Item|Policy) Schema|Inbox Index Schema)' wiki-design/05-contracts-and-next-steps.md)"

echo "=== 10. 05 capture_policy.json 默认 exclude_paths 不含 wiki/decisions/**（应 = 0）==="
echo "命中: $(grep -c 'wiki/decisions/\*\*' wiki-design/05-contracts-and-next-steps.md)"

echo "=== 11. 05 含 PII 非完整警示（应 ≥ 1）==="
echo "命中: $(grep -c '不代表完整 PII 检测' wiki-design/05-contracts-and-next-steps.md)"

echo "=== 12. 05 目标文件关系树含 inbox/ 和 capture_policy.json（应各 ≥ 1）==="
echo "inbox/: $(grep -c '^  inbox/$' wiki-design/05-contracts-and-next-steps.md)"
echo "capture_policy.json: $(grep -c 'capture_policy.json' wiki-design/05-contracts-and-next-steps.md)"

echo "=== 13. 白名单外文件不应被动（应输出空 stat） ==="
git diff --stat 5633239..HEAD -- wiki-design/README.md wiki-design/rfcs/

echo "=== 14. tasks/ 除 TASK-003 外其它 task 应未动 ==="
git diff --name-only 5633239..HEAD -- wiki-design/tasks/ | grep -v 'TASK-003-apply-rfc-003.md' || echo "  (no other task files modified)"

echo "=== 15. knowledge/ 不应存在 ==="
if [ -d knowledge/ ]; then echo "FAIL: knowledge/ exists"; else echo "OK: knowledge/ absent"; fi

echo "=== 16. .gitignore 含 inbox_index.json（应 ≥ 1）==="
echo "命中: $(grep -c 'knowledge/.wiki/inbox_index.json' .gitignore)"

echo "=== 17. 05 含 Inbox Index Schema 字段表（应 ≥ 1，验证 5d 内容完整）==="
echo "命中 'draft_count' 字段: $(grep -c 'draft_count' wiki-design/05-contracts-and-next-steps.md)"
echo "命中 'oldest_draft_age_days' 字段: $(grep -c 'oldest_draft_age_days' wiki-design/05-contracts-and-next-steps.md)"
```

预期：

- 1：≥ 1
- 2：三项**各**应 ≥ 1（按出现次数，不是行数）
- 3：≥ 1
- 4：≥ 1
- 5：≥ 1
- 6：= 2
- 7：≥ 1
- 8：≥ 1
- 9：= 3（含新增 Inbox Index Schema）
- 10：= 0 ← 这条是 Decision 第 2 条 apply 约束
- 11：≥ 1 ← 这条是 Decision 第 1 条 apply 约束
- 12：inbox/ ≥ 1，capture_policy.json ≥ 1
- 13：`git diff --stat` 输出空
- 14：无输出 / "(no other task files modified)"
- 15：`OK: knowledge/ absent`
- 16：≥ 1（Inbox Index Schema 派生层进 .gitignore）
- 17：两个字段名各 ≥ 1（确认 Inbox Index Schema 字段表完整）

### Step 7：Commit 正本改动

```bash
git add AGENTS.md wiki-design/01-architecture.md wiki-design/02-workflows.md wiki-design/04-agent-rules.md wiki-design/05-contracts-and-next-steps.md .gitignore

git commit -m "$(cat <<'EOF'
[apply rfc-003] capture mechanism + inbox buffer layer

按 RFC-003 Revision v2 落地：

- AGENTS.md：新增"低摩擦 capture（capture 缓冲层）"子节，
  含建议模式 / opt-in auto / 可见报告 / PII 兜底 / 严禁绕过 inbox 五条
- 01-architecture.md：prefix 表加 inb_ 行；capture item 边界说明；
  正本/派生层列表加 inbox/、capture_policy.json、inbox_index.json
- 02-workflows.md：新增"被动 capture（建议 / 自动）"和"Inbox 晋升"两节
- 04-agent-rules.md：读取列表加 inbox_index.json；写入规则段加 capture 例外
- 05-contracts-and-next-steps.md：目标文件关系树和职责划分表更新；
  新增 Capture Item Schema + Capture Policy Schema + Inbox Index Schema 三整段
- .gitignore：追加 knowledge/.wiki/inbox_index.json（派生层，同 id_index.json）

两条 apply-time 约束已落实（来自 Decision 段补充）：
- exclude_patterns 默认正则显式标注"非完整 PII 检测"
- exclude_paths 默认为空数组，不含 wiki/decisions/**

Co-Authored-By: Codex <noreply@openai.com>
EOF
)"
```

### Step 8：推进 task status pending → done

完成 Step 7 后：

1. 修改本文件 frontmatter `status: pending` → `status: done`
2. `updated:` 改为今天（如不同日则更新）
3. 在文件末尾追加 `## Execution log by codex · 2026-05-27` 段，按"完成后报告格式"填写
4. Commit：

```bash
git add wiki-design/tasks/TASK-003-apply-rfc-003.md
git commit -m "[task] TASK-003 done by codex"
```

## 完成后报告格式

把以下内容贴进 `## Execution log by codex · 2026-05-27` 段：

```markdown
## Execution log by codex · 2026-05-27

### 步骤完成情况
- Step 0 Spec review: 通过
- Step 1 AGENTS.md: done
- Step 2 01-architecture: done
  - 2a prefix 表加 inb_ 行: done
  - 2b inbox capture item 备注: done
  - 2c 正本/派生层列表追加: done
- Step 3 02-workflows: done
  - 3a 被动 capture 新段: done
  - 3b Inbox 晋升 新段: done
- Step 4 04-agent-rules: done
  - 4a 读取列表加 inbox_index.json: done
  - 4b 写入规则加 capture 例外: done
- Step 5 05-contracts + .gitignore: done
  - 5a 目标文件关系树 + 职责划分表更新: done
  - 5b Capture Item Schema 新段: done
  - 5c Capture Policy Schema 新段: done
  - 5d Inbox Index Schema 新段: done
  - 5e .gitignore 追加 inbox_index.json: done
- Step 6 验证: 输出见下

### 验证输出
\`\`\`
<Step 6 全部 grep / git diff 输出>
\`\`\`

### Commit
- Step 7 commit sha: <sha>
- Step 8 commit sha: 本 commit（实际 sha 由提交后回复报告）

### 偏离 / 异常
<列出与指令不一致的地方；没有就写"无"。>
```

## Spec review by codex · 2026-05-27

### 完整性
- [x] Revision v2 的主路径基本覆盖：默认建议 capture、auto_capture opt-in、可见报告、PII 降级、秒级文件名、`type: inbox` 不进 wiki 页面类型、`inb_` prefix、只读 `inbox_index.json`、archive promoted/dropped、Markdown inbox 进 Git，都已经映射到 Step 1~5。
- [x] Decision 两条 apply-time 约束已嵌入 spec：`exclude_patterns` 明确标注"不代表完整 PII 检测"；`exclude_paths` 示例为 `[]`，没有默认 `"wiki/decisions/**"`。
- [ ] Revision v2 第 6 条只读 `inbox_index.json` 的**索引结构**没有落成 schema。Step 4 只让 `04-agent-rules.md` 读取 `knowledge/.wiki/inbox_index.json`，Step 5 只把它列入职责划分表，但没有定义 `draft_count`、`oldest_draft_age_days`、`recent_drafts`、`updated_at` 等结构。建议在 05 增加一个短的 `Inbox Index Schema` 小节，或在 Capture Item Schema 的 lint/健康度部分明确该派生 JSON 的字段。
- [x] 新内容边界基本清楚，未混入 RFC-004 的 aliases / canonical_id / redirect；`inb_` 是对 TASK-002 稳定 ID prefix 表的明确扩展，兼容 RFC-002。

### 可执行性
- [x] 5 个目标文件的修改顺序合理：先 AGENTS 行为规则，再 01 架构边界，再 02 workflow，再 04 agent 草案同步，最后 05 schema 契约。
- [x] 大部分编辑 anchor 清晰：01 的 prefix 表 / 正本派生列表、02 的结晶化前插入点、04 的读取/写入规则、05 的 Source Manifest 后插入点都存在。
- [ ] Step 6 第 2 项验证会误判：命令是 `grep -cE 'RFC-003-inbox-capture-layer|02-workflows.md|05-contracts-and-next-steps.md' AGENTS.md`，`grep -c` 统计的是**匹配行数**，不是匹配次数。按 Step 1 给出的 AGENTS 文案，RFC-003 在一行，02 和 05 很可能同在最后一个长段落里，因此实际命中可能是 2 行，但预期写成 `≥ 3`。建议二选一：把 Step 1 最后一段拆成两行/两个 bullet，确保 02 和 05 分别占一行；或把验证改为 `grep -oE ... | wc -l` 按出现次数统计。
- [x] Step 6 第 10 / 11 项能捕获 Decision 两条约束：第 10 项检查 `wiki/decisions/**` 不残留，第 11 项检查 "不代表完整 PII 检测"。
- [x] Step 6 采用 `set +e`、`grep -c` 和显式"应为 X"输出，整体可机械执行。

### 风险
- 如果不补 `Inbox Index Schema`，后续 Agent 会知道"读 inbox_index.json"，但不知道该文件的稳定字段，容易各自生成不同结构。
- 如果不修 Step 6 第 2 项，后续 apply 即使内容正确也可能验证失败，或者执行者被迫临场改格式来满足计数。
- AGENTS.md 中包含 emoji 示例，符合 RFC-003 原文，但如果后续希望全仓库 ASCII，需要另开 RFC 统一；本 task 不应临时改。

### 结论
- 需修改。建议先补齐 `inbox_index.json` 派生索引结构，并修正 Step 6 第 2 项的行数/次数验证歧义后，再进入 Step 1~8。

## Execution log by codex · YYYY-MM-DD

（待执行者在 Step 8 填写）

## Evaluation by claude · YYYY-MM-DD

（待评估者填写）

## Spec review v2 by codex · 2026-05-27

### v1 阻塞点复核
- [x] `Inbox Index Schema` 已补齐。字段覆盖 `version`、`draft_count`、`oldest_draft_age_days`、`recent_drafts[]`、`recent_drafts[].filename`、`summary`、`captured_at`、`updated_at`，并明确派生层、生成时机、不包含正文和 archive 文件，足以让后续 Agent / lint 稳定生成与读取。
- [x] Step 6 第 2 项已解决行数 vs 命中次数歧义。现在用 `grep -oE ... | wc -l` 分别统计 `RFC-003-inbox-capture-layer`、`02-workflows.md`、`05-contracts-and-next-steps.md` 的出现次数，预期也改成三项各自 `>= 1`。

### 配套调整复核
- [x] `.gitignore` 已纳入白名单：强约束 #1 从 5 个目标扩为 6 个文件，Step 5e 明确 `knowledge/.wiki/inbox_index.json` 紧贴 `id_index.json` 后追加。
- [x] Step 5e 与 Step 7 commit 范围一致：`git add` 已包含 `.gitignore`，commit message 也说明 `.gitignore` 追加 `inbox_index.json`。
- [x] Step 6 第 16 项验证 `.gitignore` 包含 `knowledge/.wiki/inbox_index.json`，第 17 项验证 `Inbox Index Schema` 至少包含 `draft_count` 和 `oldest_draft_age_days`，能捕获 v1 漏项。
- [x] Decision 两条 apply-time 约束仍可被 Step 6 第 10 / 11 项捕获：`exclude_paths` 不含 `wiki/decisions/**`，并包含"不代表完整 PII 检测"警示。

### 兼容性
- [x] `inb_` 作为 TASK-002 prefix 表扩展，且明确 capture item 非 `knowledge/wiki/` 页面类型，兼容稳定 ID schema。
- [x] Capture Item frontmatter 包含 `id`，格式为 `inb_YYYYMMDD_HHmmss_<slug>`，与 RFC-003 / TASK-002 的命名空间设计一致。
- [x] `inbox_index.json` 标注为派生层并进入 `.gitignore`，与 `id_index.json` 的处理方式一致。

### 注意项
- workflow 描述里仍有“Step 1~5 Codex 执行 5 个文件的编辑 / Step 7 5 文件一次性 commit”的旧口径，但强约束 #1、Step 5e、Step 7 `git add` 和验证第 16 项都已经明确是 6 个文件。该残留不影响执行，可在后续整理 task 文案时顺手修正。

### 结论
- 通过。可以进入 Step 1~8。

## Execution log by codex · 2026-05-27

### 步骤完成情况
- Step 0 Spec review: 通过
- Step 1 AGENTS.md: done
- Step 2 01-architecture: done
  - 2a prefix 表加 inb_ 行: done
  - 2b inbox capture item 备注: done
  - 2c 正本/派生层列表追加: done
- Step 3 02-workflows: done
  - 3a 被动 capture 新段: done
  - 3b Inbox 晋升 新段: done
- Step 4 04-agent-rules: done
  - 4a 读取列表加 inbox_index.json: done
  - 4b 写入规则加 capture 例外: done
- Step 5 05-contracts + .gitignore: done
  - 5a 目标文件关系树 + 职责划分表更新: done
  - 5b Capture Item Schema 新段: done
  - 5c Capture Policy Schema 新段: done
  - 5d Inbox Index Schema 新段: done
  - 5e .gitignore 追加 inbox_index.json: done
- Step 6 验证: 输出见下

### 验证输出
```
=== 1. AGENTS.md 含'低摩擦 capture'子节（应 ≥ 1）===
命中: 1
=== 2. AGENTS.md 引用 RFC-003 + 02-workflows + 05-contracts（每项应 ≥ 1 次命中）===
  RFC-003-inbox-capture-layer 命中次数:        1
  02-workflows.md 命中次数:        2
  05-contracts-and-next-steps.md 命中次数:        2
=== 3. 01-architecture.md prefix 表含 inb_ 行（应 ≥ 1）===
命中: 1
=== 4. 01-architecture.md inbox capture item 备注存在（应 ≥ 1）===
命中: 1
=== 5. 01-architecture.md 派生数据列表含 inbox_index.json（应 ≥ 1）===
命中: 1
=== 6. 02-workflows.md 含两段新 h2（应 = 2）===
命中: 2
=== 7. 04-agent-rules.md 读取列表含 inbox_index.json（应 ≥ 1）===
命中: 1
=== 8. 04-agent-rules.md 写入规则段含 'capture 例外'（应 ≥ 1）===
命中: 1
=== 9. 05 含 Capture Item / Capture Policy / Inbox Index 三段（应 = 3）===
命中: 3
=== 10. 05 capture_policy.json 默认 exclude_paths 不含 wiki/decisions/**（应 = 0）===
命中: 0
=== 11. 05 含 PII 非完整警示（应 ≥ 1）===
命中: 1
=== 12. 05 目标文件关系树含 inbox/ 和 capture_policy.json（应各 ≥ 1）===
inbox/: 1
capture_policy.json: 4
=== 13. 白名单外文件不应被动（应输出空 stat） ===
=== 14. tasks/ 除 TASK-003 外其它 task 应未动 ===
wiki-design/tasks/README.md
=== 15. knowledge/ 不应存在 ===
OK: knowledge/ absent
=== 16. .gitignore 含 inbox_index.json（应 ≥ 1）===
命中: 1
=== 17. 05 含 Inbox Index Schema 字段表（应 ≥ 1，验证 5d 内容完整）===
命中 'draft_count' 字段: 2
命中 'oldest_draft_age_days' 字段: 2
```

### Commit
- Step 7 commit sha: fd32feb61a8b29e7ebb730b759d21612135b26aa
- Step 8 commit sha: 本 commit（实际 sha 由提交后回复报告）

### 偏离 / 异常
- Step 6 第 14 项使用 `5633239..HEAD` 范围，命中了本轮开始前已有的 `465a40e` 对 `wiki-design/tasks/README.md` 的 task 索引改动；当前 Step 1~5 工作区改动只包含 6 个白名单文件，未改其它 task 文件。
