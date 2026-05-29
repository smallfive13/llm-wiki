---
id: rfc_20260529_010
title: wiki init 脚手架（外部 vault 实例 + 叠加已有 vault + git 初始化）
author: claude
status: proposed
created: 2026-05-29
updated: 2026-05-29
targets:
  - scripts/wiki_init.py
  - scripts/README.md
  - wiki-design/02-workflows.md
reviewers:
  - codex
  - user
---

# RFC-010: wiki init 脚手架

## 背景

多实例已被工具层支持（`--root`，RFC-008），但缺"建一个新实例"的脚手架。用户实测验证了三个事实，引出本 RFC：

1. **手动 `cp knowledge/` 有坑**：当前 `knowledge/` 已含 llm-wiki 自身的 4 页 + 上下文层内容（首次结晶化），直接 cp 会带 meta 内容 + stale 派生层；且根 `.gitignore` 是 `*` + 白名单模式，新目录名整个被 `*` 吞掉不进 git。
2. **`--root` 支持仓库外绝对路径**（已实测）：引擎在 llm-wiki repo 跑，`--root` 指向任意外部实例。
3. **用户实际布局**：`/Users/zhangjunwu/workspace/obsidian/knowledge/<业务域>/` 每个是一个 **Obsidian vault 实例**（`personal/` 是第一个，已是空 vault：含 `.obsidian/` + 默认 `欢迎.md`），引擎留 llm-wiki repo 共享，实例进 git。

需要一个 `wiki init` 把"建合法实例"固化成一条命令，正确处理：外部路径、叠加到已有 vault（不覆盖 `.obsidian/`/用户笔记）、git 初始化 + 派生层 `.gitignore`。

> **决策前提（已定）**：单仓多实例形态 = 引擎单一来源（llm-wiki/scripts）+ 多个外部 vault 实例；实例进 git。"改 workflow 零同步"红利由共享引擎保证（见 `knowledge/wiki/topics/toolchain-usage.md`）。

## 提案

新增 `scripts/wiki_init.py`：把一个目录初始化为合法 wiki 实例（标准骨架），叠加安全、git 可选。

### CLI

```bash
conda activate py312
python3 scripts/wiki_init.py --root <实例路径> [--profile NAME] [--git] [--git-root <repo路径>]
```

| 选项 | 含义 |
| --- | --- |
| `--root <path>`（必填） | 实例根（绝对或相对仓库根；可指向外部 vault） |
| `--profile NAME` | 同时生成 `.wiki-profile.json` 模板（profile 名 = NAME） |
| `--git` | 确保实例数据进 git：在 `--git-root`（缺省 = `--root`）确保是 git repo（缺则 `git init`），并写/追加 `.gitignore` 派生层 + `.obsidian/` 排除规则 |
| `--git-root <path>` | git repo 根（多 vault 共一 repo 时指向容器层，如 `obsidian/knowledge/`） |

退出码：`0` 成功；`2` 配置/参数错误。

### 1. 建标准骨架（复刻 knowledge/ 结构，幂等叠加）

按当前 `knowledge/` 骨架（TASK-005 定义）创建——**已存在的文件一律跳过不覆盖**：

- **14 个 `.gitkeep` 空目录**：`raw/sources/`、`wiki/{sources,entities,topics,comparisons,synthesis,decisions,queries,open-questions}/`、`inbox/`、`inbox/archive/{promoted,dropped}/`、`maps/`、`.wiki/`
- **4 个上下文层占位 md（无 frontmatter）**：`purpose.md`（写"<实例名> 知识库目的"占位）/ `index.md` / `overview.md` / `log.md`（首条 `## YYYY-MM-DD · Initialized` 记录，注明引擎版本 + profile）
- **`.wiki-schema.md`**：拷贝当前引擎的 `knowledge/.wiki-schema.md`（base schema 人读镜像，通用、不含 llm-wiki 业务内容）；若 `--profile`，追加 profile 摘要段
- **3 个 JSON 契约**：`raw/source_manifest.json`（空 sources）/ `.wiki/review_queue.json`（空 items）/ `.wiki/capture_policy.json`（RFC-003 默认值）

### 2. 叠加已有 vault（安全语义）

- 目标可能已是 Obsidian vault（`.obsidian/` + 用户笔记如 `欢迎.md`）。init **只补缺失的骨架文件**，对已存在的任何文件（含 `.obsidian/`、用户 md、已建骨架）**跳过不动**。
- **幂等**：重复跑结果一致，不破坏已有内容。
- 输出报告：列出"新建 N 个 / 跳过 M 个已存在"，便于核对没误覆盖。

### 3. `--git`：实例进 git + 派生层 .gitignore

- 在 `--git-root`（缺省 `--root`）确保是 git repo（不是则 `git init`）。
- 写/追加该 repo 的 `.gitignore`（幂等，不重复追加）：
  ```
  # wiki 派生层（可重建，不进 Git）
  **/.wiki/id_index.json
  **/.wiki/inbox_index.json
  **/.wiki/normalized_alias_index.json
  **/.wiki/cache.json
  **/maps/graph-data.json
  **/maps/knowledge-graph.md
  **/maps/graph-insights.md
  # Obsidian 每机器配置
  **/.obsidian/workspace.json
  **/.obsidian/workspace-mobile.json
  ```
  > 用 `**/` 通配（非写死路径前缀），多 vault 共一 repo 时对所有实例生效——避免重蹈引擎仓库 `.gitignore` 写死 `knowledge/` 前缀的覆盖盲区。
  > `.obsidian/` 只忽略 `workspace*.json`（每机器易变），保留主题/插件配置可同步（团队 vault 常见做法）。

### 4. init 后自检

init 末尾自动跑 `wiki_lint.py --root <实例> --check-only`，应 exit 0（空实例无 error）；非 0 则报告并退出非 0，提示实例未就绪。

### 范围（MVP 不包含 → 留后续）

- **`wiki sync`**（引擎演进后重生成各实例 `.wiki-schema.md` 镜像）：留后续 RFC；当前 `.wiki-schema.md` stale 只是文档漂移，不影响校验（工具读 BASE_SCHEMA）。
- **Agent 自动认 active 实例**：AGENTS.md / capture 仍默认 `knowledge/`；让 Agent 自动往指定实例 ingest/capture 的指向机制（如 `.wiki-instances.json` + 会话声明）留 RFC-011。
- **迁移现有 `knowledge/` 内容**到新实例：本 RFC 只建空实例。
- **删除/重置实例**：不做。

## 替代方案

### A. git repo 层级（多 vault 共一 repo vs 每域各自）

| 方案 | 评价 |
| --- | --- |
| **`obsidian/knowledge/` 一个 repo 包多 vault（推荐）** | 多业务域共一 git 历史/备份；`--git-root` 指容器层；`.gitignore` 用 `**/` 通配覆盖所有域 |
| 每域各自 repo | 独立权限/历史；但每个都要 init repo + .gitignore，碎 |

推荐 A；用户 Decision 时确认。

### B. `.wiki-schema.md` 来源

| 方案 | 评价 |
| --- | --- |
| **拷贝当前引擎 `knowledge/.wiki-schema.md` 模板（MVP）** | 简单；它是通用 base 镜像 |
| 从 `BASE_SCHEMA` 程序生成 | 更准（永不 stale），但要写 schema→markdown 渲染器，留 `wiki sync` RFC |

### C. 叠加 vs 全新

只支持**叠加**（已存在文件跳过）——因目标常是已有 vault；不提供"清空重建"（危险）。

### D. `.obsidian/` gitignore 粒度

| 方案 | 评价 |
| --- | --- |
| **仅 `workspace*.json`（推荐）** | 每机器易变项忽略，主题/插件配置可同步 |
| 整个 `.obsidian/` | 保守，但团队 vault 丢失共享配置 |

## 影响范围

### 新增

- `scripts/wiki_init.py`（约 250~400 行 Python：骨架生成 + 叠加跳过 + git/.gitignore + 自检）

### 改动正本

- `scripts/README.md`：新增 wiki init 段（用法 + 选项 + 叠加语义 + git）
- `wiki-design/02-workflows.md`：「实例初始化」workflow 指向 `wiki_init.py`

### 不改动

- `AGENTS.md`（Agent active 实例指向留 RFC-011）
- `wiki_lint.py` / `wiki_graph.py` / `wiki_common.py` / `BASE_SCHEMA`（init 复用它们，不改）
- 引擎仓库 `.gitignore`（wiki_init.py 在 `scripts/` 下,已被 `!scripts/**` 放行）
- 现有 `knowledge/` 实例

### 依赖

- Python 3.12 + PyYAML（与引擎同款）；`--git` 调用系统 `git`（subprocess）。

### 验证

- init `personal`（外部 vault，含已有 `.obsidian/`+`欢迎.md`）：报告"新建骨架 / 跳过 .obsidian、欢迎.md"；`.obsidian/`、`欢迎.md` 原样保留。
- init 后 `wiki_lint --root personal --check-only` exit 0；`wiki_graph --root personal` 出空图。
- `--git`：personal 所在 repo 有 `.gitignore` 含派生层规则；派生层不被 git 跟踪。
- **幂等**：重复 init 无新建、无覆盖。
- 临时实例专项 fixture（建在 knowledge/ 外，trap 清理）。

### 风险

1. **误覆盖用户 vault 文件**（最高）：叠加必须严格"已存在即跳过"；专项 fixture 验证已有 `.obsidian/`+md 原样保留。
2. **git init 在错误层级**：`--git-root` 缺省 `--root` 可能不是用户想要的 repo 根；报告明确打印"git repo: <path>"供核对。
3. **`.gitignore` 通配符**：`**/maps/...` 可能误伤同 repo 其它非 wiki 的 maps 目录；MVP 可接受（知识 repo 一般无此冲突），文档注明。
4. **跨平台 git 调用**：subprocess git 失败（无 git/权限）要 graceful 报错，不留半初始化状态。

## Review by codex · YYYY-MM-DD

（待 Codex 追加）

## Decision

（待用户填写或授权 Agent 代写）
