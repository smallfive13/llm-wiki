---
id: rfc_20260603_016
title: ingest v2 — visibility 分级 + 脱敏分级 + 富媒体（图片多模态）
author: claude
status: proposed
created: 2026-06-03
updated: 2026-06-03
targets:
  - scripts/wiki_common.py
  - scripts/wiki_lint.py
  - scripts/wiki_init.py
  - scripts/README.md
  - knowledge/.wiki-schema.md
  - wiki-design/02-workflows.md
reviewers:
  - codex
  - user
---

# RFC-016: ingest v2 — visibility 分级 + 脱敏分级 + 富媒体

## 背景

datawarehouse 库首次 ingest 一批**内部 Wiki（需登录、含大量图片）**的技术文档时（真实使用驱动 gap），暴露三处 ingest 缺口：

1. **脱敏一刀切过严**：当前红线把人员/IP/表名/邮箱全脱，但**知识库本身是内部的**——这些信息对数仓答疑有用、不该脱；只有 token / AKSK / password / 密钥 / 连接串才是真红线。结果 source 被脱得"没内容"。
2. **无来源分级**：内部文档 vs 公开资料该有不同固化/脱敏策略，当前无字段区分。
3. **富媒体丢失**：原文大量图片（架构图 / 血缘图 / 截图）全部丢失、未落地、未解析——而图对后续检索/答疑价值很大。

用户决策（2026-06-03）：① 脱敏放宽到只脱密钥类，其余暂不脱（库本身内部）；② 来源分级、且与 backlog 的 `visibility` 统一；③ ingest 要有多模态解析能力，答疑能携带图片。

## 提案

三模块。**工具链（lint/graph/eval）保持纯机械零 LLM 不变**；多模态解析是**写入 AI 的职责**（Claude/Codex 都具备），工具只校验产物（引用是否完整）。

### M1：`visibility` 分级（统一页面级 + source 级）

新增 **core optional 字段** `visibility`，取值 `public | internal | private`：

| 取值 | 含义 |
| --- | --- |
| `public` | 公开资料（外部可见、可固化原文/图） |
| `internal` | 公司 / 团队内部（涵盖 backlog 的 team 语义） |
| `private` | 个人私密 |

- 适用：所有 wiki 页 frontmatter + `source_manifest` 每条 source（来源分级）。
- **库级默认**：`capture_policy.json` 加 `default_visibility`（datawarehouse=`internal`、personal=`private`）；页面不写则继承库默认。
- lint 校验 enum；不写不报错（optional，回退库默认）。

### M2：脱敏分级（硬底线 + 软项按库配）

把 `capture_policy` 的脱敏拆两层：

- **硬底线 `hard_redact`**（任何库、任何 visibility **永远脱**，命中即 **error 阻断**）：token / AKSK / `password` / 密钥 / 连接串 / 私钥。这是不可放宽的安全底线。
- **软项 `soft_redact`**（按库可配，命中按库 policy 报 warning 或忽略）：人员 / 邮箱 / IP / 手机 / 客户信息 / 表名等。
- **datawarehouse**：内部库，`soft_redact` 清空（只留硬底线）——人员/IP/表名等不再脱。
- **personal / 默认新库**：保持较严（软项默认开），按需放宽。

> 与 RFC-012 一致：硬底线是 error（违规），软项是 warning（提示）。`visibility: public` 的库/页软项应更严（公开前别带内部信息）。

### M3：富媒体（图片落地 + 多模态描述 + 嵌入引用）

- **实例加 `assets/` 目录**（wiki_init scaffold 新增；进 git——图是知识的一部分）。
- **图片落地**：ingest 时图片存 `assets/<source_id>-<NN>.<ext>`（确定命名）。
- **多模态解析（写入 AI 做）**：对每张图，AI 用多模态生成 **alt + 文字描述**，描述进正本（供检索/答疑）。工具不解析图内容。
- **引用约定**：正文用 Obsidian 嵌入 `![[assets/<file>]]`，紧跟一段文字描述。答疑时 AI 检索到含图页 → 自然能把图（assets 路径）和描述一起带出。
- **lint 校验**（纯机械）：① `![[assets/..]]` / `![](assets/..)` 引用的文件在 `assets/` 真实存在（断引 → error，类似 wikilink dangling）；② 可选 warning：嵌入图缺紧邻描述。
- **安全**：图片按所在 source 的 `visibility` + 脱敏策略处理；`internal`/`private` 的图不外发；含硬底线信息的图不落地（AI 写入时判断）。

### 多模态解析定位（关键边界）

- 工具（lint/graph/eval）**永不读图内容**——只校验"引用完整 + 描述在不在"，保持确定性、零 LLM、可 CI。
- 图 → 可检索文字 = **写入 AI 的职责**：ingest/crystallize 时由有多模态的 AI（Claude/Codex）生成描述。
- 这样既得多模态能力，又不破坏工具链的纯机械性。

## 范围（不做 → Backlog）

| 议题 | 不做的理由 | 触发条件 |
| --- | --- | --- |
| 公开 URL 自动抓取落地（web adapter） | 本 RFC 聚焦"已读到的内容怎么存好"，抓取是另一环 | 需批量 ingest 公开网页时 |
| 图片向量检索 / 以图搜图 | 需向量基础设施，违背零 LLM 工具链 | 接入检索层（backlog 查询路由） |
| 自动 PII 模型识别（NER） | 当前正则 + AI 写入判断够用 | 误漏严重时 |
| `visibility` 驱动的访问控制 / 加密 | 本 RFC 只做标注 + 脱敏策略，不做强访问控制 | 有多租户/外发需求时 |

## 替代方案

| 决策点 | 选择 | 拒绝 |
| --- | --- | --- |
| 来源分级 vs 通用 visibility | **统一 `visibility`（页面+source 通用）** | 只给 source 加 tier（割裂，backlog visibility 还得再来一次） |
| 图解析谁做 | **写入 AI 多模态（工具零 LLM）** | 工具内置 OCR/多模态（破坏确定性、引重依赖） |
| 脱敏 | **硬底线 error + 软项按库 warning** | 一刀切全脱（过严、source 没内容）/ 全不脱（密钥泄漏） |
| 图存哪 | **实例 `assets/` 进 git** | 外链（断）/ 不存只留描述（丢原图、答疑不能带图） |
| 图描述存哪 | **进正本（紧邻嵌入）** | 只存 alt（信息太少，检索不到） |

## 影响范围

### 改动
- `scripts/wiki_common.py`：BASE_SCHEMA 加 `visibility` enum（core optional）；`capture_policy` 契约加 `default_visibility` + `hard_redact`/`soft_redact` 结构；assets 引用规则常量。
- `scripts/wiki_lint.py`：`visibility` enum 校验；脱敏分级（硬底线 error / 软项 warning）；assets 图引用断引校验（+ 可选缺描述 warning）。
- `scripts/wiki_init.py`：scaffold 加 `assets/`；新库 `capture_policy` 模板含 `default_visibility` + 两层脱敏。
- `knowledge/.wiki-schema.md`：补 `visibility` / 脱敏分级 / 富媒体引用约定（并 `--sync-schema` 同步实例）。
- `wiki-design/02-workflows.md`：ingest 富媒体步骤 + 多模态解析 + 脱敏分级流程。
- `scripts/README.md`：相应说明。

### 不改动
- 工具链零 LLM / 纯机械 / 确定性、退出码语义（新增校验里 enum/断引是 error、缺描述/软项是 warning，符合既有分级）。
- 既有 8 类页面、稳定 ID、canonical/display 双层。

### 落地后数据动作（TASK 内，外部实例迁移、单独提交）
- datawarehouse：`capture_policy` 放宽（soft 清空）、`default_visibility: internal`；**重新 ingest 那批内部文档**（带图 + 不过度脱敏 + 补回 source 内容）。
- 各库 `--sync-schema` 同步 `.wiki-schema.md`。

### 零回归验证
- 现有 personal/engine 实例：不写 `visibility` 时行为不变（optional 回退默认）、lint 不新增 error。
- assets 断引校验：fixture 覆盖"嵌入图存在/缺失"。
- 脱敏分级：fixture 覆盖硬底线 error、软项按库 warning/忽略。
- 多模态描述：工具不读图，只校验引用——确定性不依赖图内容。

## TASK 拆分建议（用户同意 M3 可分阶段）

- **TASK-016a**：M1 visibility + M2 脱敏分级（schema/lint/capture_policy/wiki_init 模板/文档）+ datawarehouse capture_policy 放宽。较轻、纯配置与校验。
- **TASK-016b**：M3 富媒体（assets scaffold + 图引用校验 + ingest 富媒体流程规范）+ datawarehouse 重新 ingest（带图）。较重。

## Review by codex · YYYY-MM-DD

（待 Codex 追加）

## Decision

（待用户填写，或授权某 Agent 代写）
