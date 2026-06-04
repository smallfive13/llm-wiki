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

## Review by codex · 2026-06-04

### 结论

- 需修改。
- 方向同意：把 ingest v2 拆成 visibility / 脱敏分级 / 富媒体三块是合理的；工具链继续零 LLM、写入 AI 负责多模态描述也符合既有边界。
- 当前版本还有 5 个阻塞点，主要集中在旧 `capture_policy` 兼容迁移、`visibility` 继承口径、assets 路径兼容、图片安全兜底和 TASK 拆分边界。

### 阻塞点

1. **`capture_policy` 从单层改两层是破坏性契约改动，迁移策略未钉死。**
   - 当前 engine / personal / datawarehouse 三个实例都是 v1 结构：`exclude_patterns` + `exclude_paths` + `max_inbox_files`，lint 也硬校验 `exclude_patterns` 是字符串数组。
   - RFC 直接改为 `hard_redact` / `soft_redact` + `default_visibility`，如果 TASK 只改 lint 模板而不迁移实例，现有库会立刻报 `MISSING_FIELD` / `TYPE_MISMATCH` 或脱敏行为漂移。
   - 建议 v2 明确二选一：
     - 兼容路线：`exclude_patterns` 在 v2 仍允许存在，lint 将其视为 `soft_redact.patterns` 的 legacy alias，并输出 `CAPTURE_POLICY_LEGACY` warning；新模板写 v2 字段，后续 TASK 迁移外部实例。
     - 迁移路线：TASK-016a 必须同时迁移 engine/personal/datawarehouse 的 `capture_policy.json`，且 lint 不再要求 `exclude_patterns`。迁移前后要跑三库 lint。
   - 我倾向兼容路线更稳：先让 lint 接受 v1/v2，TASK-016a 再迁移显式实例，避免外部未知实例被一次性打断。

2. **`visibility` 继承语义还不够机械。**
   - RFC 说页面不写回退 `capture_policy.default_visibility`，source 也适用，但没有定义 lint 输出 / 图谱 / eval 是否需要存 effective visibility。
   - 需要钉死：
     - `visibility` 是 core optional，不进 `core_required_fields`，只在出现时校验 enum。
     - `default_visibility` 缺失时 legacy 默认是什么；建议 `private`，但 datawarehouse 迁移为 `internal`。
     - source_manifest 每条 source 缺 `visibility` 时同样继承 default；如果有 `visibility` 则校验 enum。
     - wiki 页面缺 `visibility` 时 lint 不改文件、不补字段，只在内部计算 effective visibility。
     - `visibility: public` 的页面/source 是否触发更严格 soft policy；如果触发，要定义它是 error 还是 warning。
   - 三档 `public/internal/private` 够用；但 `internal` 是否涵盖 team/公司内部应在正文中明确，避免未来再拆 `team`。

3. **M3 assets 路径与当前 datawarehouse 实际资产布局冲突。**
   - RFC 规定图片落地 `assets/<source_id>-<NN>.<ext>`，引用 `![[assets/<file>]]` / `![](assets/..)`.
   - 但当前 datawarehouse 已有大量图片在 `raw/sources/assets/...`，wiki 页用 `../../raw/sources/assets/...` Markdown 图片引用。若 TASK-016b 只校验 `assets/`，现有数据会被排除在新规则外；若要迁移，又是较大的数据动作。
   - 建议 v2 钉死一种边界：
     - 新规范只认实例根 `assets/`，TASK-016b 负责迁移 datawarehouse 现有 `raw/sources/assets/` 到 `assets/` 并改引用；或
     - MVP 同时允许 `assets/` 与 `raw/sources/assets/`，但推荐新 ingest 写 `assets/`，后续另开迁移。
   - 若选择只认 `assets/`，还要定义文件命名是否允许子目录。`assets/<source_id>-<NN>.<ext>` 对 75+ 张图可行，但失去来源分组；`assets/<source_id>/<NN>.<ext>` 可能更易维护。

4. **"含硬底线信息的图不落地"只靠 AI 判断，工具层没有最低可验证兜底。**
   - 工具不读图内容是合理边界，但如果工具完全不看图，"不落地"无法被 CI 验证。
   - 建议 v2 明确工具层只做可机械检查：
     - 对图片文件名、路径、相邻描述文本、source notes / manifest caption 扫 `hard_redact` 正则，命中 error。
     - 不声明工具能发现图片像素里的 token；把像素内容判断明确归写入 AI + 人工 review。
     - 对 `visibility: public` 的图片要求存在文字描述且描述通过 hard/soft 扫描。
   - 这样不会破坏"工具永不读图内容"，但有最小文本兜底。

5. **TASK 拆分边界需要调整：016a 不应包含 datawarehouse 重新 ingest，016b 也不应同时扛规则和大规模数据重灌。**
   - `TASK-016a` 做 M1/M2 + capture_policy 兼容/迁移合理。
   - `TASK-016b` 做 assets scaffold + lint 断引校验 + 文档合理。
   - 但 "datawarehouse 重新 ingest 那批内部文档（带图）" 是数据迁移/重灌任务，风险和验证面都大，建议拆成 `TASK-016c` 或后续 data task。否则 016b 会同时改工具规则和大量外部数据，失败时不好定位。

### 非阻塞建议

- `visibility` 字段如果要进入 graph 节点，建议在 RFC 明确；如果不进入，先只让 lint 校验也可以。
- `hard_redact` / `soft_redact` 建议定义结构为 `{patterns: [...], enabled: true}` 或直接数组，不要留给 TASK 猜；否则 datawarehouse "soft 清空" 是 `[]` 还是 `{patterns: []}` 不确定。
- assets 进 git 方向可以接受，但建议补文件大小/扩展名软限制（warning），例如单图 > 5MB 或非 png/jpg/jpeg/webp 报 warning，避免仓库体积失控。
- 缺图描述 warning 的机械规则建议钉死为"图片引用后 1-3 个非空文本行内存在非图片文本"，避免 TASK 实现口径漂移。

## Decision

（待用户填写，或授权某 Agent 代写）
