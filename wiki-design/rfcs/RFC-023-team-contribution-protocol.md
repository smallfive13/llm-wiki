---
id: rfc_20260610_023
title: 团队贡献协议（投料 → MR → CI → 单 writer ingest）+ dropbox 脱敏扫描
author: claude
status: proposed
created: 2026-06-10
updated: 2026-06-10
targets:
  - scripts/wiki_lint.py
  - scripts/README.md
  - wiki-design/02-workflows.md
  - tests/
reviewers:
  - codex
  - user
---

# RFC-023: 团队贡献协议

## 背景

TASK-023 已把 datawarehouse 实例开放到内部 GitLab（`knowledge-cmn`，8 人团队，全员用 AI agent）：带历史拆库、CI 三道门禁、`raw/dropbox/` 投料区、库根 `AGENTS.md` 投料节均已落地。但这套协作模式目前只存在于**实例仓的文档初版 + 本会话讨论**里，引擎正本（`02-workflows.md`）没有"团队贡献"这一节——下一个团队库要重新发明一遍。

同时落地后发现一个**机制缺口**：`wiki_lint --scan-wiki-pii` 的扫描对象是 `inbox + archive + wiki` 三组文档（`wiki_lint.py:1133` `scan_pii(inbox_docs, archived_docs, wiki_docs, ...)`），**不覆盖 `raw/dropbox/`**。成员投进来的原料若混入 AKSK / password / token，CI 三道门禁全部抓不到，只能靠 maintainer 人工审 MR——硬红线"任何库不可放宽"的承诺在团队入口处出现了盲区。

## 提案

两部分：M1 把协议写进引擎正本（文档），M2 补 dropbox 脱敏扫描（机制）。

### M1 · 团队贡献协议定版（`02-workflows.md` 新增「团队贡献」节）

把以下协议写为引擎标准模式（适用于任何开放给团队的实例库），实例仓的 `AGENTS.md` / `raw/dropbox/README.md` 与之对齐：

**角色**

| 角色 | 能做 | 不能做 |
| --- | --- | --- |
| 成员（Developer） | 改 `raw/dropbox/**`、提 MR；用 agent 只读答疑 | 改 `wiki/**`、`raw/source_manifest.json`、`.wiki/**`、上下文层（purpose/index/overview/log）；直推 main |
| maintainer | 审批 MR、merge；本机按 RFC-019 ingest；`review: true` 背书；管 GitLab 权限 | —— |

**投料约定**（成员侧，零引擎知识要求）

- 一份原料一个子目录 `raw/dropbox/YYYYMMDD-<标题>/`，内含原料文件 + 一句话说明（来源链接 / 业务背景 / 想解决的问题）。
- 硬红线在入口即适用：不投 AK/SK、password、token、私钥、密钥、连接串、可复用登录凭证、客户级 PII（与实例 `purpose.md` 一致）。
- 投料走 MR；成员的 agent 可代办「建分支 → 放文件 → push → 开 MR」全程。

**GitLab 机制要求**（不靠自觉）

- `main` 设 protected branch（Developer 不可直推）；MR 必须 maintainer approve + CI 全绿才可 merge。
- 引擎仓对成员只读（Reporter / maintainer-only 写）。

**maintainer ingest（单 writer 模式）**

- wiki 正本**只有一个 writer**：maintainer 本机的 ingest 会话。这是设计而非权宜——它使 manifest 单文件并发冲突（backlog 旧问题）在当前规模下不发生；成员侧并发只落在 dropbox 不同子目录，天然无冲突。
- 节奏：`git pull` → `wiki lint --ingest-status` 看清单 → 按 RFC-019 triage→apply 逐份 ingest → 每份 commit → `git push`。断点续传靠 manifest status。
- **dropbox 队列语义**：ingest 完成的原料从 `raw/dropbox/<dir>/` **移入** `raw/sources/<日期>-<slug>/` 正式归档（图片进 `raw/sources/assets/`），dropbox 始终只剩待处理项。
- 扩 maintainer 的条件：单 maintainer 吞吐不够时，指定 1~2 名骨干同装引擎，约定「ingest 前 pull、做完即 push」粗串行；届时再评估 manifest 拆文件（不提前做）。

### M2 · `--scan-wiki-pii` 扩展覆盖 `raw/dropbox/`（机制）

- `wiki_lint --scan-wiki-pii` 的扫描范围从 `inbox + archive + wiki` 扩展为 **`inbox + archive + wiki + raw/dropbox/**`（文本文件）**。
- 范围钉死：只扫 dropbox 下文本类文件（按扩展名白名单：`.md` / `.txt` / `.csv` / `.json` / `.yaml` / `.yml` / `.html`，executor 可在 Task 内微调），二进制（图片 / pdf / office）跳过——与现有"图片靠路径与紧邻描述扫描"的哲学一致，不引入新解析依赖。
- 命中语义与现行一致：`hard_redact` 命中 → error；`soft_redact` 命中 → warning。dropbox 文件不是 wiki 页，**不做任何 schema / frontmatter 校验**，只跑文本 redact 扫描。
- human 输出的「脱敏扫描」行注明范围（`inbox + wiki + dropbox`）。
- **CI 零改动自动获益**：`knowledge-cmn` 的 `.gitlab-ci.yml` 已在跑 `--scan-wiki-pii`，引擎升级后 MR 中的投料原料即被硬红线扫描覆盖，盲区闭合。
- 普通 lint（不带 flag）行为不变；`raw/sources/`（已 ingest 原文）**暂不纳入**——存量 17 份原文是经 ingest 流程把过关的，全量纳入可能产生历史误报，留作后续观察（若需要，单独小 RFC）。

## 真实摩擦来源

机制类，证据具体：

1. **扫描盲区是落地后的真实发现**：`wiki_lint.py:1133` 的 `scan_pii` 仅收 inbox/archive/wiki 三组文档；`knowledge-cmn` CI 三道门禁对 `raw/dropbox/` 原料文本零覆盖，而这恰是 8 人团队即将开始写入的唯一入口。
2. **协议只存在于实例文档初版**：TASK-023 把投料约定写进了 `knowledge-cmn` 的 AGENTS/README，但引擎 `02-workflows.md` 无此模式——第二个团队库无从复用；且「单 writer / 队列语义 / 扩权条件」等本会话讨论定下的关键设计尚无正本。

## 验证方式

- **M2 fixture**：dropbox 放含 `AKIA...` 的 `.md` → `--scan-wiki-pii` exit 1 + `HARD_REDACT_HIT`；含邮箱（soft 项非空的库）→ warning；干净 dropbox → 0 命中；图片 / 二进制文件跳过不报错；普通 lint（无 flag）不受 dropbox 内容影响；`--check-only` 行为不变。
- **真实库 smoke**：`knowledge-cmn` 本地 clone 跑 `--scan-wiki-pii` exit 0（当前 dropbox 仅 README/.gitkeep）；datawarehouse 旧目录与 personal 回归不受影响。
- **CI 验证**：引擎仓推送后，`knowledge-cmn` 提一个含红线 fixture 的测试 MR，确认 pipeline 红；删除后绿（由用户在 GitLab 侧确认）。
- **回归**：012~022 测试套件全过。

## 替代方案

- **新增独立 flag `--scan-dropbox`**：CI 要加第四行、文档要多一个概念；而「投料原料」与「inbox 草稿」在"待入库文本要过红线"语义上同类，并入现有 flag 更顺，CI 还零改动。**放弃**。
- **CI 加机械路径检查（成员 MR 只许动 dropbox）**：GitLab protected branch + maintainer approve 已是机制兜底，再加 CI diff 路径检查属重复建设；且 maintainer 自己的 ingest 提交会触发误报需要豁免逻辑。**暂不做**，靠 MR review；若实际出现越界再补。
- **云端 agent 自动 ingest**（GitLab scheduled pipeline 跑 LLM）：当前无云端 agent 凭证 / 运行环境，单 writer 本机 ingest 已闭环。**远期**。
- **成员直接写正式页（过 CI 即可）**：用户已拍板"只投料"；质量与 manifest 并发两个问题都会回来。**已否**。

## 影响范围

- `scripts/wiki_lint.py`：`scan_pii` 调用处增加 dropbox 文本文档组（仅 redact 扫描，不进 schema 校验）；human 输出范围措辞。
- `scripts/README.md`：`--scan-wiki-pii` 范围说明更新。
- `wiki-design/02-workflows.md`：新增「团队贡献（投料 → MR → CI → 单 writer ingest）」节。
- `tests/`：`test_task_024*.py` fixture。
- 实例仓 `knowledge-cmn`（apply 时、不在引擎 targets）：`AGENTS.md` / `raw/dropbox/README.md` 与 02 定版措辞对齐（如有出入）；CI 无需改动。
- **不改**：core schema、`schema_version`（M2 是行为扩展不动契约结构，若 codex review 认为应 bump 再议）、graph / eval、`raw/sources/` 扫描范围、manifest 结构。

## Apply 拆分建议

单 **TASK-024**：M2 引擎改动 + 测试 + M1 文档（02-workflows）一个引擎 commit；`knowledge-cmn` 对齐措辞（若需）单独实例仓 commit。含红线 fixture 的 CI 测试 MR 由用户配合在 GitLab 验证。

## Review by codex · YYYY-MM-DD

（由 codex 追加，不覆盖本提案正文。）

## Decision

（由用户填写，或用户明确授权某 Agent 代写。）
