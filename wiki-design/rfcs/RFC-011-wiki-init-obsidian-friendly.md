---
id: rfc_20260601_011
title: wiki_init Obsidian 友好初始化（排除派生层 + 结构化上下文层占位）
author: claude
status: proposed
created: 2026-06-01
updated: 2026-06-01
targets:
  - scripts/wiki_init.py
  - scripts/README.md
reviewers:
  - codex
  - user
---

# RFC-011: wiki_init Obsidian 友好初始化

> **编号澄清**：RFC-010 正文曾把 RFC-011 预留给"Agent 自动认 active 实例"。该需求现已被 Claude 侧 `wiki` skill（实例注册表 + 自然语言认库）吸收，引擎层指向机制降级为编号待定的后续 RFC（仅当 Codex 也要独立写知识时才需要）。本 RFC-011 编号改用于这个真实落地的 wiki_init 增强——遵循"编号以实际创建为准"。

## 背景

`wiki_init`（RFC-010）能正确建实例骨架 + 进 git，但在 Obsidian 里**实际打开后暴露两个体验问题**（真实使用驱动）：

1. **派生层混进 Obsidian 图谱**：`maps/knowledge-graph.md`、`maps/graph-insights.md` 是 wiki_graph 生成的派生产物，Obsidian 把它们当普通笔记显示在关系图谱里 → 一堆孤立噪音节点。（`.wiki/` 是点开头目录，Obsidian 默认已忽略。）
2. **上下文层是空壳占位**：wiki_init 建的 `index.md` / `overview.md` 只有 `# Index` 一行，没导航价值，在图谱里也孤立。

刚才手动给 `personal` 修了这两点（写 `.obsidian/app.json` 排除 `maps/`+`.wiki/`、把上下文层填成结构化导航）。应**固化进 wiki_init**，让以后每个业务库（风控/客服…）init 时自动带上，不必每次手动修。

## 提案

`wiki_init` 新增两件事（都在叠加安全前提下）。

### 1. Obsidian 排除派生层（写/合并 `.obsidian/app.json`）

init 时确保 `<root>/.obsidian/app.json` 的 `userIgnoreFilters` 含 `maps/` 和 `.wiki/`：

- `.obsidian/` 或 `app.json` 不存在 → 创建 `app.json = {"userIgnoreFilters": ["maps/", ".wiki/"]}`
- `app.json` 已存在 → 读 JSON，`userIgnoreFilters` **union 加入** `maps/`+`.wiki/`（去重），**其它键原样保留、已有过滤项一个不删**，写回

> 这是对 RFC-010"叠加安全"的有意扩展：wiki/ 文件是"已存在即跳过"，但 `app.json` 这一个配置文件改为"**合并 union**"——只往 `userIgnoreFilters` 加值，绝不删/改用户已有的任何键值。是 wiki_init 唯一会"修改已存在文件"的地方，范围严格限定在这一个键。

### 2. 上下文层结构化占位

把 `index.md` / `overview.md` 从空壳升级为有用骨架（仍**无 frontmatter**，lint 反向校验通过）：

- `index.md`：
  ```markdown
  # Index

  知识库入口。

  ## 主题

  （随知识增长，在此用 [[slug|标题]] 链接各页）

  ## 导航

  - [Purpose](purpose.md) — 知识库目的
  - [Overview](overview.md) — 主题总览
  - [Log](log.md) — 变更日志
  ```
- `overview.md`：带"主题（待填）"+ 健康度表骨架
- `purpose.md`：保持现有占位（已够）

> **不预填知识页 wikilink**：init 是建空库，此时没有任何 wiki 页可链。入口 wikilink 的维护是写知识时的事（由 skill 在 crystallize 时顺带更新 index，或人工）——本 RFC 只给"更好的起始骨架 + 导航链接"。

### 范围（MVP 不包含）

- **自动维护 index 的知识页入口**：留给 skill/后续（写知识时更新）。
- **其它 Obsidian 配置**（主题/插件/graph 样式）：不碰，只动 `userIgnoreFilters`。
- **回填已建实例**：本 RFC 改 wiki_init 影响**新 init**；`personal` 已手动修好，不需回填；其它存量实例如有需要，重跑 wiki_init（幂等 + 合并语义保证安全）即可补上。

## 替代方案

### A. `.obsidian/app.json` 处理方式

| 方案 | 评价 |
| --- | --- |
| **总是确保 app.json 含排除规则（合并 union）（推荐）** | 知识库实例大概率用 Obsidian 看；合并不覆盖，安全；非 Obsidian 用户忽略它无害 |
| 仅当 `.obsidian/` 已存在时才合并 | 漏掉"还没用 Obsidian 打开过"的新实例 |
| `--obsidian` 开关控制 | 多一个参数，默认行为不够省心 |

### B. 上下文层占位

| 方案 | 评价 |
| --- | --- |
| **结构化骨架 + 导航链接，不预填知识页 wikilink（推荐）** | 空库没页面可链；骨架已比空壳有用 |
| 预填知识页 wikilink | init 时无页面，做不到 |
| 维持空壳 | 不解决孤立/无导航 |

## 影响范围

### 改动正本

- `scripts/wiki_init.py`：新增 ① app.json 合并 userIgnoreFilters ② 上下文层结构化模板
- `scripts/README.md`：wiki init 段补 Obsidian 友好说明

### 不改动

- `wiki_lint.py` / `wiki_graph.py` / `wiki_common.py` / `BASE_SCHEMA`（上下文层仍无 frontmatter，lint 行为不变）
- RFC-010 的其它行为（骨架/3 JSON/--git/--profile/自检/类型冲突）
- 现有 `personal` 实例（已手动修好）

### 验证（TASK 机械断言，临时实例，trap 清理）

- **app.json 不存在** → init 后 `.obsidian/app.json` 含 `maps/`+`.wiki/`。
- **app.json 已存在且有用户自定义键/过滤项** → init 后用户键值**全部保留** + 多了 `maps/`+`.wiki/`（用 checksum 比对"非 userIgnoreFilters 部分"或逐键断言）。
- **幂等**：第二次 init，app.json 不重复加 `maps/`（union 去重）。
- 上下文层 index/overview 含导航骨架；`wiki_lint --root <实例> --check-only` 仍 exit 0（无 frontmatter）。
- 沿用 RFC-010 既有验证（叠加 checksum / 类型冲突 / --git / profile）全过 —— 重跑 TASK-010 Step 5 防回归。

### 风险

1. **合并 app.json 误删用户配置**（最高）：只对 `userIgnoreFilters` 做 union 加值，其它键深拷原样写回；专项 fixture 验证"用户自定义键值不变"。
2. **app.json 非法 JSON**（用户手改坏了）：读取失败时不静默覆盖 → 报 warning 跳过 app.json 合并（不阻断 init），或 exit 2 提示用户修；TASK 定其一。
3. **上下文层模板改动**：确保仍无 frontmatter（lint EXTRA_FRONTMATTER 会拦）；导航用相对 md 链接 + 主题区用 wikilink 占位说明。

## Review by codex · YYYY-MM-DD

（待 Codex 追加）

## Decision

（待用户填写或授权 Agent 代写）
