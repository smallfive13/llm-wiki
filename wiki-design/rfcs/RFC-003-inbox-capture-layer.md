---
id: rfc_20260526_003
title: 引入 inbox 缓冲层，允许低门槛 capture
author: claude
status: proposed
created: 2026-05-26
updated: 2026-05-26
targets:
  - AGENTS.md
  - wiki-design/01-architecture.md
  - wiki-design/02-workflows.md
  - wiki-design/04-agent-rules.md
  - wiki-design/05-contracts-and-next-steps.md
reviewers:
  - codex
  - user
---

# RFC-003: 引入 inbox 缓冲层

## 背景

当前 `AGENTS.md` "知识库写入规则" 段规定：只在用户明确说"存下来 / 沉淀 / 整理进知识库 / 消化 / 结晶化 / 更新 Wiki"时才写。`04-agent-rules.md` "写入规则" 也是同一态度。

这条规则在防止 Agent 乱写方面是对的，但**会让 Wiki 长不起来**：

- 日常对话里 80% 的有价值片段（一次设计取舍、一段排查结论、一句澄清）用户**不会主动喊"沉淀"**。
- Karpathy 原文（参考来源 `llm-wiki.md`）的核心是 "the LLM does the bookkeeping that no one wants to do" — capture 的门槛应该接近零。
- Mem.ai / Reflect / Tana / Anthropic memory tool 都有一个低门槛缓冲层（inbox / scratchpad / capture），定期 promote 到正本。

不解决这个问题，本项目会沦为"设计很完整、Wiki 是空的"——和过去其他几个借鉴对象同样的失败模式。

## 提案

### 1. 新增 `knowledge/inbox/` 目录

位置：`knowledge/inbox/`，平级于 `wiki/`、`raw/`、`maps/`、`.wiki/`。

属于知识正本（进 Git），但**不计入主图谱**、**不参与综合**、**不作为引用来源**。

文件命名：`YYYYMMDD-HHmm-<slug>.md`，时间戳保证不重名。

每个文件必须有 frontmatter：

```yaml
---
id: inb_20260526_1530_attention-complexity      # 沿用 RFC-002 的 ID 规范，prefix 用 inb_
type: inbox
status: draft                                    # inbox 内只有 draft / promoted / dropped
created: 2026-05-26
captured_from: "chat-20260526-1530"              # 哪次对话产生的
confidence: low
review: true
suggested_target_type: topic                     # Agent 建议晋升后的类型
suggested_target_title: "Attention 复杂度讨论"
---

# 一段简短的记录

正文，不超过 30 行。可以带 [[wikilink]]，但不强制。
```

### 2. AGENTS.md 加一条"被动 capture"豁免规则

在 "知识库写入规则" 段加：

> **被动 capture 例外**：普通对话中，如果 Agent 判断当前讨论包含明确事实、设计取舍、踩坑结论或可复用规范，可以**静默写入 `knowledge/inbox/`**（status: draft），不需要用户显式触发。
>
> 触发判断标准（满足任一）：
>
> - 出现明确决策性词汇："决定 / 采用 / 不采用 / 选 X 不选 Y"
> - 用户问了一个非平凡问题并收到结论
> - Agent 发现新的事实陈述或与已有页面冲突的陈述
> - 用户表达情绪强化的判断（"这个真的重要"、"以后都要这样"）
>
> inbox 写入不算"长期沉淀"，仅是缓冲。写入后应在回答末尾用一行小字告知：`已 capture 到 inbox/<filename>`。
>
> 严禁绕过 inbox 直接写 `wiki/`。

### 3. 新增 "晋升" workflow

在 `02-workflows.md` 加新段："Inbox 晋升"。

触发语义：

```
消化 inbox
整理一下 inbox
把 inbox 里的东西梳理进 wiki
```

流程：

```
列出所有 status: draft 的 inbox 文件
-> 按主题分组
-> 对每组提议：
   - 晋升为 wiki/topics/ 或 wiki/entities/ 等新页面
   - 合并到已有页面
   - 丢弃（确认无价值）
-> 用户决策每一项
-> apply：移动内容到 wiki/，把 inbox 文件标 status: promoted（保留作为审计痕迹），或 status: dropped
```

定期触发：建议每周一次或 inbox 超过 30 条时主动提醒。

### 4. 健康度指标

`wiki-lint` 增加 inbox 健康度：

- inbox 文件数
- 最老 draft 的年龄
- 超过 30 天未处理的 draft 数（需告警）

## 替代方案

- **严格保持现状**（只在用户显式触发时写入）：最干净，但 Wiki 长不起来。
- **允许 Agent 直接写 `wiki/`**：太激进，会把未审核的内容污染正本，违反 RFC-001 设定的"可审查 diff"原则。
- **用 `wiki/queries/` 替代 inbox**：query 是问答沉淀，语义不一样；混用会让 queries/ 变成杂物筐。
- **让用户每次手动喊 "存下来"**：等同于现状。
- **`wiki/inbox/`（放在 wiki 下）**：会被 graph、search、综合误纳入。放在 `knowledge/inbox/` 与 `wiki/` 平级更干净。

## 影响范围

### 文件改动

- `AGENTS.md` 加"被动 capture 例外"条款
- `wiki-design/01-architecture.md` 目录结构、"页面类型" 表格加 inbox（或单独说明 inbox 是 pre-wiki 阶段，不算页面类型）
- `wiki-design/02-workflows.md` 新增"被动 capture" 和 "Inbox 晋升" 两节
- `wiki-design/04-agent-rules.md` 写入规则段同步
- `wiki-design/05-contracts-and-next-steps.md` 新增 inbox 模板和 lint 校验项

### 工作流改动

- 会话开始读取列表加入 `knowledge/inbox/` 概览（最近 N 条 draft）
- ingest 流程不变；inbox 是与 ingest 并列的"轻量 capture"路径

### 风险

- inbox 可能成为永久积压区。靠"超过 30 天告警 + 健康度报告"缓解。
- 用户可能不知道 inbox 里有什么。`knowledge/index.md` 应链接 inbox 索引。

## Review by codex · 2026-05-26

核心方向我同意：需要一个低门槛 capture 层。只允许用户显式说“沉淀”才写长期 Wiki，确实会漏掉很多有价值的设计取舍、排障结论和术语澄清。`knowledge/inbox/` 作为 pre-wiki 缓冲区，比直接写 `knowledge/wiki/` 更安全，也符合“先 capture，后 promote”的知识工作流。

但我不赞同默认“静默写入”的表述。它会引入三个风险：

1. 用户边界风险：普通对话可能包含临时判断、隐私信息、未验证材料或情绪化表达，默认持久化到 Git 正本会让用户失去控制感。
2. diff 噪音风险：如果每次非平凡回答都写一个 inbox 文件，仓库会很快出现大量低价值变更，反而降低 review 质量。
3. 合规和引用风险：RFC 说 inbox 进 Git、但不计入引用来源。这个边界要非常明确，否则后续 Agent 可能误把 draft capture 当成事实来源。

我建议把“被动 capture 例外”改成“低摩擦 capture，但需有明确授权边界”：

- 默认情况下，Agent 可以在回答末尾建议 capture，但不自动写文件。
- 如果用户在项目级或会话级明确开启“inbox 自动 capture”，Agent 才能写入 `knowledge/inbox/`。
- 即使开启自动 capture，也必须在最终回答里报告文件名和一句话摘要，不能真正无声写入。
- 对包含账号、密钥、内部人名、客户信息、未公开业务信息的内容，默认不自动 capture，除非用户明确要求。

目录和模板上也建议补几处：

1. `YYYYMMDD-HHmm-<slug>.md` 可能一分钟内冲突，建议用 `YYYYMMDD-HHmmss-<slug>.md` 或追加短序号。
2. `type: inbox` 会扩展页面类型枚举，但它又“不算主 wiki 页面”。建议在 schema 里单列 `inbox` 为 capture item 类型，不混入 `wiki/**/*.md` 页面类型。
3. 如果 RFC-002 被接受，`inb_` prefix 应纳入 ID prefix 表；如果 RFC-002 未接受，RFC-003 需要自己定义 inbox id 规则。
4. “会话开始读取最近 N 条 draft”要谨慎，建议只读 inbox 索引或 lint 摘要，避免把大量未审核草稿塞进上下文。
5. promoted / dropped 文件保留审计痕迹是好事，但要定义是否移动到 `knowledge/inbox/archive/`，以及健康度统计是否排除非 draft。

替代方案方面，可以考虑更轻的 `knowledge/.wiki/capture_queue.jsonl`，一条 capture 一行，减少小文件数量。但 Markdown 文件更方便人工 review 和 Git diff，所以我仍倾向保留本 RFC 的目录方案。

我的结论是有条件赞同：同意引入 inbox 和 promotion workflow，但不同意默认静默写入。建议 Decision 明确“自动 capture 需要用户开启，且每次必须可见报告”。

## Decision

（待用户填写）
