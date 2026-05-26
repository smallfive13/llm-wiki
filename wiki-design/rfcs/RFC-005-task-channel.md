---
id: rfc_20260526_005
title: 引入 wiki-design/tasks/ 作为执行指令通道
author: claude
status: accepted
created: 2026-05-26
updated: 2026-05-26
targets:
  - AGENTS.md
  - wiki-design/tasks/
  - wiki-design/rfcs/README.md
reviewers:
  - codex
  - user
---

# RFC-005: 引入 wiki-design/tasks/ 作为执行指令通道

## 背景

当前 Codex 和 Claude Code 之间存在两类信息流：

1. **决策类**（用什么 schema、写什么字段、目录怎么分）→ 通过 RFC 异步对齐，由 RFC-001 设立机制。
2. **执行类**（具体改哪个文件、怎么 commit、按什么顺序）→ 当前还是 chat 一次性 paste，缺持久化、缺审计、缺复现。

执行类通道的现实问题：

- 上下文随会话蒸发。
- 谁、什么时候、做了什么不进 git。
- 失败要重组指令，复现成本高。
- 多 Agent 不同步：Codex 看到的指令 Claude 看不到，事后 evaluate 没源头可对照。

需要一个与 RFC 对称的执行通道，本 RFC 引入 `wiki-design/tasks/` 解决。

## 提案

### 1. 目录结构

```
wiki-design/
├── rfcs/        ← 决策层："要不要这么改"
└── tasks/       ← 执行层："具体怎么做、谁来做"
    ├── README.md
    └── TASK-NNN-<slug>.md
```

文件命名 `TASK-NNN-<slug>.md`，NNN 从 001 起全局递增。

### 2. Frontmatter schema

```yaml
---
id: task_YYYYMMDD_NNN
title: 简短标题
author: claude | codex                   # 指令编写者
executor: codex | claude | user          # 期望执行者
status: pending | in-progress | done | failed | cancelled
type: decision-write | apply | bookkeeping | refactor | other
created: YYYY-MM-DD
updated: YYYY-MM-DD
related_rfcs: []                         # 可选，关联的 RFC id
---
```

### 3. 正文骨架（append-only）

每份 task 包含固定段：

- `## 目标` — 一句话
- `## 前置条件` — 能开始的检查点
- `## 强约束` — 不可违反的规则
- `## 步骤` — 操作清单
- `## 验证` — 自检命令和预期输出
- `## 完成后报告格式` — executor 应贴什么

executor 完成后追加：

- `## Execution log by <executor> · <date>`

evaluator 评估后追加：

- `## Evaluation by <evaluator> · <date>`

**正文 append-only**：上述固定段一旦定稿不重写，只追加 log / evaluation。

### 4. 状态机

```
pending → in-progress → done
                      → failed
pending → cancelled
```

| status | 含义 | 推进者 |
| --- | --- | --- |
| `pending` | 已创建，等开工 | author / executor |
| `in-progress` | 执行中 | executor |
| `done` | 完成 | executor |
| `failed` | 失败 | executor |
| `cancelled` | 撤销 | author / user |

不允许 `done → 其他`、`failed → done`。失败修补另开新 task。

### 5. 与 RFC 的边界

| 维度 | RFC | Task |
| --- | --- | --- |
| 回答 | 要不要这么改 | 怎么改、谁来 |
| status 控制 | 用户 | executor |
| 拒绝形式 | rejected / superseded | cancelled / failed |
| 内容性质 | 决策 | 操作 |

- RFC accepted 不强制产生 Task。轻量 apply 仍可直接 commit。
- Task 不依赖 RFC。日常运维（commit 整理、依赖升级）也可起 Task。
- 一份 Task 可关联多个 RFC（`related_rfcs` 数组）。

## 替代方案

- **只用 chat paste**：当前模式，问题已分析。
- **GitHub Issue / Linear / JIRA**：工具依赖，脱离 git。
- **task 放 `.claude/tasks/` 等 agent 私有目录**：另一个 agent 看不到，违背双向通道目的。
- **task 文件不进 git**：丢失持久化和审计。

## 影响范围

- 新建 `wiki-design/tasks/README.md`（模板 + 状态机 + 索引）
- 新建首份示范 task `wiki-design/tasks/TASK-001-write-rfc-decisions.md`
- 更新 `AGENTS.md` 加"执行指令通过 tasks/ 传递"条款
- 更新 `wiki-design/rfcs/README.md` 索引

## Decision

Accepted. 本 RFC 是追溯性正式化：

- 用户在 2026-05-26 显式提出"新增 task 文件让 Codex 读取执行" 的诉求。
- Claude 提出 A（严格先 RFC 后建）/ B（实用同步建）两条路径，用户选 B。
- 本 RFC 在文件建好的同时一并写入 git，作为机制说明。

不需要 Codex 在本 RFC 上额外 review；Codex 在后续具体 task 执行中如发现机制缺陷，可新开 RFC 修订或 supersede 本 RFC。

用户确认：paic.small.five@gmail.com，2026-05-26。
