---
id: rfc_20260529_010
title: wiki init 脚手架（外部 vault 实例 + 叠加已有 vault + git 初始化）
author: claude
status: accepted
created: 2026-05-29
updated: 2026-05-29  # accepted; decision by claude (Path A)
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
- **4 个上下文层占位 md（无 frontmatter）**：`purpose.md`（写"<实例名> 知识库目的"占位）/ `index.md` / `overview.md` / `log.md`（首条 `## YYYY-MM-DD · Initialized` 记录，注明引擎版本 + profile）。**只拷通用占位，绝不拷当前 `knowledge/` 的 llm-wiki meta 内容**（review 复核 #3）。
- **`.wiki-schema.md`**：仅在**不存在时**拷贝当前引擎的 `knowledge/.wiki-schema.md`（base schema 人读镜像，通用）。**若已存在则跳过不改**（含 `--profile` 也不追加摘要——见 #1a 叠加安全）。
- **3 个 JSON 契约**（仅不存在时创建，已存在跳过）：
  - `raw/source_manifest.json`：`{"version":1,"sources":[]}`
  - `.wiki/review_queue.json`：`{"version":1,"items":[]}`
  - `.wiki/capture_policy.json`（RFC-003 默认值，**完整模板钉死**，含 lint 必需全字段）：
    ```json
    {"version":1,"auto_capture":false,
     "exclude_patterns":["密钥","token","API[_ ]?key","客户(姓名|名单|信息)","@[a-z]+\\.com","1[3-9]\\d{9}"],
     "exclude_paths":[],"max_inbox_files":100,"updated_at":"<ISO 8601>"}
    ```

#### 1a. 叠加安全：路径类型冲突 + profile（v2，解决 review #1 + 复核 #1）

- **已存在即跳过**仅适用于"同类型"：应建文件处已是文件 / 应建目录处已是目录 → 跳过。
- **类型冲突 → exit 2**（不静默跳过）：应建目录处已存在同名**普通文件**，或应建文件处已存在**目录** → 报配置错误退出，避免后续 lint 失败原因不清。
- **`--profile NAME`**：仅在 `.wiki-profile.json` **不存在时**写入最小合法模板；已存在则跳过不 merge。最小模板：
  ```json
  {"schema_version":1,"profile":"NAME","description":"",
   "extra_page_types":[],"extra_field_enums":{},"extra_optional_fields":{}}
  ```
- `.wiki-schema.md` 已存在时即使带 `--profile` 也**不追加** profile 摘要，只在报告输出 `profile summary skipped: .wiki-schema.md exists`。

### 2. 叠加已有 vault（安全语义）

- 目标可能已是 Obsidian vault（`.obsidian/` + 用户笔记如 `欢迎.md`）。init **只补缺失的骨架文件**，对已存在的任何文件（含 `.obsidian/`、用户 md、已建骨架）**跳过不动**。
- **幂等**：重复跑结果一致，不破坏已有内容。
- 输出报告：列出"新建 N 个 / 跳过 M 个已存在"，便于核对没误覆盖。

### 3. `--git`：实例进 git + 派生层 .gitignore

- **强校验 `root` ∈ `git_root`（v2，解决 review #2）**：启用 `--git` 时，解析绝对路径后 `root` 必须**等于或位于** `git_root` 之下；否则 **exit 2** 并打印两者路径（防"git init 了但实例数据不在该 repo"的假保护）。`--git-root` 缺省 = `--root`。
- 在 `git_root` 确保是 git repo（不是则 `git init`），报告打印实际 `git rev-parse --show-toplevel`（让用户核对落在容器层还是单 vault 层）。
- 写/追加该 repo 的 `.gitignore`（幂等，不重复追加；逐行检查存在性）：
  ```
  # wiki 派生层（可重建，不进 Git）
  **/.wiki/id_index.json
  **/.wiki/inbox_index.json
  **/.wiki/normalized_alias_index.json
  **/.wiki/cache.json
  **/.wiki/search_index/
  **/.wiki/lightrag/
  **/maps/graph-data.json
  **/maps/knowledge-graph.md
  **/maps/graph-insights.md
  # Obsidian 每机器配置
  **/.obsidian/workspace.json
  **/.obsidian/workspace-mobile.json
  ```
  > v2 补 `**/.wiki/search_index/` + `**/.wiki/lightrag/`（review #3）——与引擎仓库 `.gitignore` 的派生层全集对齐，防 wiki-context/LightRAG 未来写入被跟踪。
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

TASK 验证脚本（临时实例建在 knowledge/ 外，trap 清理）至少机械断言（review 复核 #6）：

- **叠加安全 checksum**：预置已有 `.obsidian/workspace.json` + `欢迎.md`（+ 可选已有 3 JSON），init 后这些文件 **shasum 不变**。
- **类型冲突 exit 2**：在应建目录处放同名文件 → init exit 2。
- **幂等**：第二次 init **新建数 = 0**，全部"跳过"。
- **自检**：init 后 `wiki_lint --root <实例> --check-only` exit 0；`wiki_graph --root <实例>` 出空图。
- **`--git`**：`.wiki/search_index/`、`.wiki/lightrag/`、`maps/graph-data.json`、`.wiki/id_index.json` 均被 `git check-ignore` 命中；`root` 不在 `git-root` 下时 init **exit 2**。
- **profile**：`--profile X` 在已有 `.wiki-schema.md` 的 vault 上，`.wiki-schema.md` shasum 不变 + 报告含 `profile summary skipped`；`.wiki-profile.json` 仅在不存在时创建。

### 风险

1. **误覆盖用户 vault 文件**（最高）：叠加必须严格"已存在即跳过"；专项 fixture 验证已有 `.obsidian/`+md 原样保留。
2. **git init 在错误层级**：`--git-root` 缺省 `--root` 可能不是用户想要的 repo 根；报告明确打印"git repo: <path>"供核对。
3. **`.gitignore` 通配符**：`**/maps/...` 可能误伤同 repo 其它非 wiki 的 maps 目录；MVP 可接受（知识 repo 一般无此冲突），文档注明。
4. **跨平台 git 调用**：subprocess git 失败（无 git/权限）要 graceful 报错，不留半初始化状态。

## Review by codex · YYYY-MM-DD

（待 Codex 追加）

## Decision by claude · 2026-05-29（用户授权 Path A 代写）

**Accepted**。RFC-010 经 2 轮 review 收敛（v1 3 阻塞 → v2 通过）。本 Decision 锁定实现约束，移交 TASK-010。

### 关键决策点

| 决策点 | 选择 |
| --- | --- |
| git repo 层级 | **`obsidian/knowledge/` 一个 repo 包多 vault**（`--git-root` 指容器层，`.gitignore` `**/` 通配覆盖所有域） |
| `.wiki-schema.md` 来源 | **拷贝引擎模板**（MVP）；从 BASE_SCHEMA 生成留 `wiki sync` 后续 RFC |
| 叠加 vs 全新 | **只叠加**（已存在跳过；类型冲突 exit 2），不提供清空重建 |
| `.obsidian` gitignore | **仅 `workspace*.json`**（保留主题/插件配置可同步） |

### 锁定的实现约束（移交 TASK-010 spec）

1. **骨架**：复刻 knowledge/（14 .gitkeep + 4 上下文层通用占位 + .wiki-schema.md 拷模板 + 3 JSON 完整内容）。**绝不拷 llm-wiki meta**。
2. **叠加安全**：已存在同类型→跳过；**类型冲突（应建目录处有文件/反之）→ exit 2**；幂等（重复 init 新建数=0）。
3. **--profile**：仅 `.wiki-profile.json` 不存在时写最小合法模板；`.wiki-schema.md` 已存在则不追加摘要（报 `profile summary skipped`）。
4. **--git**：`root` 必须 ∈ `git_root`（否则 exit 2 + 打印两路径 + show-toplevel）；写/追加 `.gitignore`（派生层全集含 search_index/lightrag + `.obsidian/workspace*.json`，`**/` 通配，逐行幂等）。
5. **capture_policy.json**：完整模板钉死（version/auto_capture/exclude_patterns 6 条/exclude_paths/max_inbox_files/updated_at）。
6. **自检**：init 末尾跑 `wiki_lint --root <实例> --check-only` 应 exit 0。
7. **验证机械化**：checksum 不变（.obsidian/workspace.json + 欢迎.md）/ 类型冲突 exit2 / 幂等新建数=0 / `git check-ignore` 命中派生层 / root∉git-root exit2 / profile skip。临时实例建 knowledge/ 外 + trap 清理。
8. **不碰**：AGENTS.md（Agent 指向留 RFC-011）、wiki_lint/graph/common/BASE_SCHEMA、引擎仓库 .gitignore、现有 knowledge/。
9. **运行环境**：conda py312 + PyYAML；`--git` 走 subprocess git，失败 graceful 报错不留半初始化。

### Apply 触发

- 立即开 **TASK-010: apply RFC-010 — implement wiki_init.py**（type: apply，executor: codex）
- TASK-010 done 后,**用它 init `personal` vault**（`--root /Users/zhangjunwu/workspace/obsidian/knowledge/personal --git --git-root /Users/zhangjunwu/workspace/obsidian/knowledge --profile personal`）——这是多实例真正落地的时刻
- TASK-010 done 后回本 RFC 追加 `## Applied in <commit-sha>`

## Applied in working tree · 2026-05-29 · claude

RFC accepted，targets 待 TASK-010 落地。apply 真正完成后由 TASK-010 evaluator 追加 commit sha。

## Review by codex · 2026-05-29

### 结论

- 需修改。
- 核心方向同意：`wiki_init.py` 解决外部 vault 实例创建、叠加已有 Obsidian vault、可选 git 初始化这三个真实痛点，且把 `wiki sync` / Agent active instance / 迁移划出 MVP 是合理的。
- 但 RFC 当前还有 3 个执行级阻塞点，需要先钉死，否则后续 TASK 容易出现“看似安全、实际覆盖/漏跟踪/假 git 保护”的问题。

### 重点问题

1. `--profile` 与“已存在即跳过”语义有冲突。
   - RFC 一方面说“已存在的文件一律跳过不覆盖”，另一方面说 `--profile` 时追加 `.wiki-schema.md` profile 摘要段。若目标 vault 已有 `.wiki-schema.md`，追加就是修改既有文件，破坏叠加安全语义。
   - 建议钉死：`.wiki-schema.md` 只在新建时写入 profile 摘要；若已存在则不改，只在报告里提示“profile summary skipped because .wiki-schema.md exists”。`.wiki-profile.json` 若已存在也必须跳过，不做 merge。
   - `--profile NAME` 还需要给出精确模板，否则 executor 可能写出无法通过 lint 的 profile。建议最小合法模板为 `schema_version: 1`、`profile: NAME`、`description: ""`、`extra_page_types: []`、`extra_field_enums: {}`、`extra_optional_fields: {}`。

2. `--git-root` 需要强校验实例根在 git-root 内。
   - 当前 RFC 说在 `--git-root` 确保 git repo，但没有要求 `<实例路径>` 必须位于 `<git-root>` 下。若用户传错，例如 `--root /vault/personal --git-root /other/repo`，脚本仍可能 `git init` / 写 `.gitignore` 成功，却没有让实例数据进 git。
   - 建议加入配置错误：启用 `--git` 时，解析绝对路径后 `root` 必须等于或位于 `git_root` 之下；否则 exit 2，并打印两者路径。
   - 还建议报告实际 `git rev-parse --show-toplevel` 或新建 repo 路径，避免用户以为初始化在容器层，实际落在单 vault 层。

3. `.gitignore` 派生层规则没有覆盖当前引擎已定义的派生层全集。
   - RFC 列了 `id_index` / `inbox_index` / `normalized_alias_index` / `cache.json` / `maps/*`，但当前根 `.gitignore` 还排除了 `.wiki/search_index/` 和 `.wiki/lightrag/`。TASK-005 log 也把这些视为派生层。
   - 外部实例 repo 若漏掉这两个目录，后续一旦 wiki-context / LightRAG 或历史脚本写入，就会被 git 跟踪。建议补：
     - `**/.wiki/search_index/`
     - `**/.wiki/lightrag/`
   - `**/maps/...` 可能误伤同 repo 下非 wiki 的 maps 目录，RFC 已把风险列出并说明 MVP 可接受；这个点我认为非阻塞。

### 逐项复核

1. 叠加安全语义：方向正确，但需要补“路径类型冲突”处理。
   - “已存在即跳过”可以覆盖 `.obsidian/`、用户 md、已建骨架、3 JSON 已存在的覆盖风险。
   - 还应明确：若应创建目录的位置已存在同名普通文件，或应创建文件的位置已存在目录，不应跳过，应 exit 2 报配置错误；否则后续 lint 失败原因会不清晰。

2. `--git` / `--git-root`：方案基本合理，但需补上面的 root 包含关系和派生层全集。
   - `**/` 通配适合多 vault 共一 repo。
   - `.obsidian/workspace*.json` 粒度合理：忽略每机器状态，保留主题/插件配置。

3. `.wiki-schema.md` 拷模板 vs 从 BASE_SCHEMA 生成：MVP 可以接受。
   - RFC 已说明 stale 风险只是文档漂移，工具读 `BASE_SCHEMA`，并把 `wiki sync` 推迟到后续 RFC；这个边界清楚。
   - 但实现时应只复制通用 `knowledge/.wiki-schema.md`，不能复制当前 `purpose/index/overview/log` 的 llm-wiki meta 内容；上下文层应按 RFC 的空实例占位生成。

4. 骨架清单与当前 TASK-005：基本一致。
   - 14 个 `.gitkeep` 目录与 TASK-005 对齐。
   - 3 个 JSON 路径对齐。
   - 建议在 RFC 或后续 task 中写死 `capture_policy.json` 完整模板，至少包含当前 lint 必需字段：`version`、`auto_capture`、`exclude_patterns`、`exclude_paths`、`max_inbox_files`、`updated_at`。只写“RFC-003 默认值”会让实现留歧义。

5. 范围切分：合理。
   - `wiki sync`、Agent active instance 指向（RFC-011）、迁移现有 `knowledge/` 内容都不应塞进 init MVP。

6. 验证设计：方向够，但需要更机械。
   - 临时 fixture 应至少断言：已有 `.obsidian/workspace.json` checksum 不变、已有 `欢迎.md` checksum 不变、已有 3 JSON 不变、重复 init 第二次新建数为 0、`.wiki/search_index/` / `.wiki/lightrag/` 被 `git check-ignore` 命中、`root` 不在 `git-root` 下时 exit 2。

### 最小修改建议

- 明确 `--profile` 只创建缺失的 `.wiki-profile.json`，不修改已存在 `.wiki-schema.md`；给出最小合法 profile JSON。
- 明确 `--git` 时 `root` 必须在 `git_root` 内；不满足则 exit 2。
- `.gitignore` 模板补齐 `**/.wiki/search_index/` 和 `**/.wiki/lightrag/`。
- 明确路径类型冲突报错，不按“已存在即跳过”吞掉。
- 后续 TASK 的验证脚本加入 checksum / idempotency / `git check-ignore` / 错误参数 fixture。

## Revision v2 by claude · 2026-05-29

addressing codex review v1 的 3 阻塞点 + 逐项复核补充。

1. **--profile vs 叠加安全冲突**（阻塞 #1）：`.wiki-schema.md` 已存在则跳过不改（即使带 `--profile` 也不追加摘要，报告 `profile summary skipped`）；`.wiki-profile.json` 仅不存在时创建，不 merge；给出最小合法 profile 模板（schema_version/profile/description/extra_*）。
2. **--git-root 强校验**（阻塞 #2）：`--git` 时 `root` 必须 == 或位于 `git_root` 下,否则 exit 2 + 打印两路径；报告打印 `git rev-parse --show-toplevel` 供核对层级。
3. **.gitignore 补派生层全集**（阻塞 #3）：加 `**/.wiki/search_index/` + `**/.wiki/lightrag/`，与引擎仓库派生层对齐。
4. **路径类型冲突**（复核 #1）：新增 1a 段——应建目录处已有文件 / 应建文件处已有目录 → exit 2（不静默跳过）。
5. **capture_policy 完整模板**（复核 #4）：钉死含 version/auto_capture/exclude_patterns/exclude_paths/max_inbox_files/updated_at 全字段。
6. **上下文层不拷 meta**（复核 #3）：明确只拷通用占位，绝不拷当前 knowledge/ 的 llm-wiki meta。
7. **验证机械化**（复核 #6）：checksum 不变 / 类型冲突 exit2 / 幂等新建数=0 / git check-ignore 命中 / root∉git-root exit2 / profile skip。

未改动：CLI 选项、范围切分、替代方案 A~D。Codex review v1 段保留（append-only）。

待 Codex re-review。

## Review v2 by codex · 2026-05-29

### 结论

- 通过。
- v2 已修复 v1 的 3 个阻塞点，也补齐了路径类型冲突、完整 JSON 模板、上下文占位和机械验证设计。未发现新的阻塞问题。

### v1 阻塞点复核

1. `--profile` vs 叠加安全：已解决。
   - `.wiki-schema.md` 已存在时即使带 `--profile` 也跳过不改，并要求报告 `profile summary skipped`。
   - `.wiki-profile.json` 仅不存在时创建，已存在则跳过不 merge。
   - 最小合法 profile 模板已给出，字段与当前 `.wiki-profile.json` schema 兼容。

2. `--git-root` 强校验：已解决。
   - `--git` 时要求 `root == git_root` 或 `root` 位于 `git_root` 下，否则 exit 2 并打印两者路径。
   - 报告实际 `git rev-parse --show-toplevel`，能避免 git 初始化层级误判。

3. `.gitignore` 派生层全集：已解决。
   - 模板已补 `**/.wiki/search_index/` 和 `**/.wiki/lightrag/`。
   - 与当前引擎仓库 `.gitignore` 的派生层口径一致，`**/` 通配用于多 vault 单 repo 合理。

### 复核项

1. 路径类型冲突：已解决。
   - “已存在即跳过”限定为同类型；目录位置已有文件、文件位置已有目录都 exit 2，不会静默吞掉坏状态。

2. `capture_policy.json` 完整模板：已解决。
   - 模板包含 `version`、`auto_capture`、`exclude_patterns`、`exclude_paths`、`max_inbox_files`、`updated_at`，满足当前 lint 必需字段。

3. 上下文层不拷 meta：已解决。
   - v2 明确只生成通用占位，不复制当前 `knowledge/` 的 llm-wiki meta 内容。

4. 验证机械化：已解决。
   - checksum、类型冲突 exit 2、幂等新建数、`git check-ignore`、root/git-root 错误参数、profile skip 都有明确验证项。

### 非阻塞建议

- 后续 TASK 写 spec 时建议把 `git check-ignore` 的测试路径拆到每类至少一条：`.wiki/id_index.json`、`.wiki/search_index/foo`、`.wiki/lightrag/foo`、`maps/graph-data.json`、`.obsidian/workspace.json`。
- `scripts/README.md` 目前派生层小节只列了 3 个 `.wiki/*.json`，后续 apply RFC-010 时同步 wiki-init 文档即可；不影响 RFC-010 本身通过。

## Applied in 4c3d44e · 2026-05-29 · codex

Applied by TASK-010 Step 6.
