---
id: top_20260528_rfc-task-protocol
type: topic
status: active
confidence: medium
created: 2026-05-28
updated: 2026-06-03
last_verified: 2026-06-03
review: false
source_ids: []
related_ids:
  - syn_20260528_llm-wiki-architecture
sources: []
related:
  - "[[llm-wiki-architecture|llm-wiki 系统架构]]"
supersedes: []
superseded_by: []
evidence_count: 2
---

# RFC + Task 协作协议

> Codex 与 Claude Code 在同一仓库协作的两层机制：RFC 管「要不要这么改」，Task 管「怎么做、谁来做」。全程 append-only + git 留痕，互不覆盖。隶属 [[llm-wiki-architecture|llm-wiki 系统架构]]。

## 为什么需要

两个 Agent 同时编辑设计正本会冲突、会互相回退。解法：**结构化提案 + 执行通道 + 只追加留痕**，让协作可审查、可回放。

## RFC 层（决策）

- 位置：`wiki-design/rfcs/RFC-NNN-<slug>.md`
- frontmatter：`id / title / author / status / created / updated / targets / reviewers`
- 正文四段：背景 / 提案 / 替代方案 / 影响范围
- status 流转：`proposed → discussing → accepted / rejected / superseded`
- **只有 accepted 的 RFC 才能 apply 到 targets 正本**
- 另一 Agent 只追加 `## Review by <agent> · <date>`，不改原作者正文
- 用户负责 `## Decision`（或明确授权 Agent 代写）
- apply 后登记 `## Applied in <commit-sha>`

## Task 层（执行）

- 位置：`wiki-design/tasks/TASK-NNN-<slug>.md`
- frontmatter：`id / title / author / executor / status / type / related_rfcs`
- 正文骨架：目标 / 前置条件 / 强约束 / 步骤 / 验证 / 完成后报告格式（定稿不重写）
- status 流转：`pending → in-progress → done / failed`；`pending → cancelled`
- executor 追加 `## Execution log`，evaluator 追加 `## Evaluation`
- 一份 task 关联 0 或多个 RFC；失败修补另开新 task

## 关键纪律

1. **Step 0 spec review gate**：task 执行前 Codex 先 review spec，抓出 spec 级 bug 才进执行（实践中拦下大量问题）。
2. **append-only**：任何 Agent 不能覆盖他人段落，全靠追加 + git history 审计。
3. **white list 强约束**：每个 apply task 列死可动文件，executor 越界即失败。
4. **零回归验证**：改动已稳定组件后必须重跑既有验证（结构等价 / content_hash）。
5. **透明报告**：偏离 / 失误如实写进 Execution log，不掩盖。

## 典型一轮

```
用户提需求 → Claude 写 RFC（proposed）→ Codex review → 用户 Decision（accepted）
→ Claude 写 Task spec → Codex spec review（收敛到通过）→ Codex 执行 + 自检
→ Claude evaluate（独立复跑）→ done
```

## commit 约定

`[rfc-NNN]` / `[apply rfc-NNN]` / `[task]` / `[claude]` / `[codex]` 前缀 + `Co-Authored-By` 标注协作来源。

## 引用

- 机制定义：`wiki-design/rfcs/RFC-001`（协作）、`RFC-005`（Task 通道）
- 入口规则：`AGENTS.md`
- 索引：`wiki-design/rfcs/README.md` / `wiki-design/tasks/README.md`

## 置信度与缺口

- 置信度：high（RFC-001~008 + TASK-001~008 全程实践）
- 缺口：跨 Agent 自动调用（目前靠人工转述）；pre-commit hook 强制 lint 未落地。
