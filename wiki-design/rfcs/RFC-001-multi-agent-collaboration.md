---
id: rfc_20260526_001
title: 引入 Codex 与 Claude Code 的 RFC 协作机制
author: codex
status: accepted
created: 2026-05-26
updated: 2026-05-26
targets:
  - AGENTS.md
  - .gitignore
  - wiki-design/rfcs/README.md
reviewers:
  - claude
  - user
---

# RFC-001: 引入 Codex 与 Claude Code 的 RFC 协作机制

## 背景

本仓库会由 Codex 和 Claude Code 共同维护。当前风险不是简单的 Git 文本冲突，而是两个 Agent 在不同会话中独立推导设计，导致契约、目录、schema 和实现顺序逐渐分叉。

用户希望两个 Agent 在改正本前先通过同一份可审查产物对齐：先提案，再 review，再由用户决策，最后才 apply 到设计正本或知识库契约。

## 提案

引入一个最小协作机制：

- 根目录新增 `AGENTS.md`，把多 Agent 协作规则写成硬约束。
- 新增 `wiki-design/rfcs/`，所有非平凡正本修改先在这里提案。
- RFC 使用固定 frontmatter 和四段正文：背景、提案、替代方案、影响范围。
- 另一个 Agent 只追加 `Review by <agent>` 段落，不覆盖原作者内容。
- 用户写 `Decision` 或明确授权 Agent 代写决策。
- 只有 `status: accepted` 的 RFC 才能 apply 到 `targets`。
- apply 后在 RFC 末尾登记 commit sha；如果未提交，先登记 working tree 状态。

## 替代方案

方案一：只靠 Git diff 和 commit message 协同。这个方案成本最低，但无法让另一个 Agent 提前看到设计意图，用户仍然会成为唯一对齐通道。

方案二：一开始就引入 `agent/codex` 和 `agent/claude` 分支。这个方案更严格，但对当前轻量设计文档阶段偏重，等 RFC 机制不够用时再叠加。

方案三：把所有讨论留在聊天记录里。这个方案短期方便，但不可检索、不可 review，也无法随仓库迁移。

## 影响范围

- 新增 `AGENTS.md`，作为 Codex 和 Claude Code 的共同规则入口。
- 更新 `.gitignore`，确保 `AGENTS.md` 能进入版本管理。
- 新增 `wiki-design/rfcs/README.md`，维护 RFC 索引、状态说明和模板。
- 新增本 RFC，记录协作机制本身的启动决策。
- 不修改现有 `wiki-design/01-architecture.md` 到 `wiki-design/05-contracts-and-next-steps.md` 正文。

## Decision

Accepted. 用户在 2026-05-26 要求实现 Codex 与 Claude Code 的协同机制，并提供 Claude Code 的 RFC 目录 + AGENTS.md 方案作为参考。本次先落最小可用版本，后续如需拆分九条具体设计建议，再按本 RFC 机制逐条新建提案。

## Applied in working tree · 2026-05-26 · codex

已创建：

- `AGENTS.md`
- `.gitignore`
- `wiki-design/rfcs/README.md`
- `wiki-design/rfcs/RFC-001-multi-agent-collaboration.md`
