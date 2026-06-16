---
id: rfc_20260610_024
title: wiki_init 固化实例 .ignore（检索默认跳过非正本目录，加速 agent 答疑）
author: claude
status: proposed
created: 2026-06-10
updated: 2026-06-10
targets:
  - scripts/wiki_init.py
  - scripts/README.md
  - tests/
reviewers:
  - codex
  - user
---

# RFC-024: wiki_init 固化实例 .ignore

## 背景

本会话排查"机器人答疑慢"时定位到一个真实病灶：agent（codex）在知识库根 `rg <词>` 会命中 `raw/` 原文与 `source_manifest.json`——`rg "Quick BI"` 在 datawarehouse 命中 **21 个文件，其中 5 个是 raw 原文/manifest**（未提炼、冗长、含已 supersede 的旧口径），codex 被引去读它们 → 多轮 tool call + 上下文膨胀。

已给 datawarehouse（`knowledge-cmn`）和 personal **手动加 `.ignore`**（ripgrep/fd 原生读，对 agent 透明、不影响 `wiki_lint`/`wiki_graph` 的 Python 扫描）止血：命中 21→16、raw 命中归零、`raw/dropbox/` 保留可搜。实测有效。

但这是手动补的。**新初始化的库（尤其后续每个团队库）不会自带**，又得手动补一遍——该把它固化进 `wiki_init`，成为实例的标准产物。

## 提案

`wiki_init` 在 scaffold 实例时写入实例根 `.ignore`，内容与已验证的手动版一致：

```
# 检索优化（rg / fd 原生读 .ignore，对 agent 答疑透明；不影响 wiki_lint/graph 的 Python 扫描）。
# 答疑只需 wiki/ + 上下文层（purpose/index/overview/log）；原始材料、图片、派生层、图谱不参与全文检索。
# ingest 若需检索已归档原文，用 `rg --no-ignore` 或显式路径；raw/dropbox/（待处理投料）刻意保留可搜。
raw/sources/
raw/source_manifest.json
maps/
.wiki/
```

实现要点：

- 新增 `IGNORE_LINES` 常量（与 `GITIGNORE_LINES` 并列）。
- **总是写**，不依赖 `--git`——`.ignore` 是检索优化，与 git 无关（区别于 `.gitignore` 仅在 `--git` 时由 `ensure_gitignore` 写）。
- **幂等**：参照 `ensure_gitignore` 的"缺行补齐、不覆盖文件既有内容"语义——重跑 `wiki_init`、或叠加到已有 vault（用户可能已手加 `.ignore` 行）时，只补缺失行、保留用户自定义行，不整文件覆盖。
- 落在 `create_skeleton`（与其它实例文件同批），计入 counters（created/skipped）。
- `.ignore` 进 Git（实例根文件，团队共享此优化；不被 `.gitignore` 屏蔽）。

边界：

- **不屏蔽** `raw/dropbox/`（ingest 要搜投料）、`inbox/`、`wiki/`、上下文层。
- **不改** `wiki_lint` / `wiki_graph` 行为（它们用 Python `os.walk`/glob，不读 `.ignore`）；不改 schema、`schema_version`。
- 现有实例：`knowledge`（引擎自带 demo）apply 时补一份；`personal` / `knowledge-cmn` 已手动加，apply 时确认内容一致即可（幂等不会重复写）。

## 真实摩擦来源

机制类，证据具体：本会话 codex 答疑慢，实测 `rg` 在 datawarehouse 命中 21 文件含 5 个 raw（原文+manifest）；手动加 `.ignore` 后降到 16、raw 归零、答疑链路已止血。新库不自带 = 每个团队库都要重踩一次。

## 验证方式

机制类，apply 后须验证：

- **fixture**：`wiki_init` 建临时实例 → 实例根有 `.ignore` 且内容 == `IGNORE_LINES`；其中放一个 `raw/sources/x.md` 含某词 + `wiki/topics/y.md` 含同词 → `rg <词> <实例>` 只命中 wiki/，不命中 raw/sources。
- **幂等**：对已有 `.ignore`（含一行用户自定义）的实例重跑 `wiki_init` → 用户行保留、缺失标准行补齐、已存在标准行不重复。
- **不依赖 --git**：不带 `--git` 跑也写 `.ignore`。
- **零副作用**：`wiki_lint --check-only` / `wiki_graph` 在带 `.ignore` 的实例上行为不变（专测或对现有实例 smoke）。
- **回归**：wiki_init 既有测试 + 012~024 套件全过。

## 替代方案

- **答疑话术里让 codex 只搜 wiki/**：靠 prompt 自觉，不可靠；`.ignore` 是机制级、对所有 rg 调用透明。**放弃**（话术可作辅助，不作主手段）。
- **用 `.gitignore` 屏蔽**：错位——`.gitignore` 管 git 跟踪、`.ignore` 管 rg 检索范围，两者正交；`raw/` 要进 git（原料归档）但要跳检索，只能用 `.ignore`。**放弃**。
- **全局 `~/.config/git/ignore` 或 `RIPGREP_CONFIG_PATH`**：不随仓分发，团队成员/CI 没有。**放弃**——优化必须随实例走。

## 影响范围

- `scripts/wiki_init.py`：`IGNORE_LINES` 常量 + `create_skeleton`（或新 `ensure_ignore`）写入 + 幂等逻辑 + counters。
- `scripts/README.md`：`wiki_init` 产物说明补 `.ignore`。
- `tests/`：`test_task_025*.py`（fixture + 幂等）。
- 现有实例（apply 时，非引擎 targets）：`knowledge` 补 `.ignore`；`personal`/`knowledge-cmn` 确认一致。
- **不改**：core schema、`schema_version`、`wiki_lint`/`wiki_graph` 逻辑、实例知识数据。

## Apply 拆分建议

单 **TASK-025**：`wiki_init` 改动 + 测试 + README + `knowledge` 实例补 `.ignore`（引擎仓一个 commit；personal/knowledge-cmn 已有，无需动）。

## Review by codex · YYYY-MM-DD

（由 codex 追加，不覆盖本提案正文。）

## Decision

（由用户填写，或用户明确授权某 Agent 代写。）
