---
id: rfc_20260603_016
title: ingest v2 — visibility 分级 + 脱敏分级 + 富媒体（图片多模态）
author: claude
status: accepted
created: 2026-06-03
updated: 2026-06-04  # accepted; decision by claude（用户授权 Path A），基于 codex v3 re-review 通过
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
- **继承语义钉死**（Codex review 阻塞 #2）：
  - `visibility` 是 **core optional**，**不进** `core_required_fields`；仅当字段出现时校验 enum，缺失不报错、lint **不补字段**。
  - **effective visibility**（内部计算，不写回文件）= 页面/source 显式 `visibility` → 否则 `capture_policy.default_visibility` → 都缺则 legacy 默认 **`private`**（最保守）。
  - `source_manifest` 每条 source 同理：有 `visibility` 校验 enum，缺失继承库 default。
  - `internal` 明确**涵盖 team / 公司内部**语义（不再单拆 `team`）。
  - `visibility: public` 的页/source 触发**更严 soft 策略**（见 M2）：软项命中升为 **warning**（不是 error，避免阻断；提醒公开前别带内部信息）。

### M2：脱敏分级（硬底线 + 软项按库配）

把 `capture_policy` 的脱敏拆两层：

- **硬底线 `hard_redact`**（任何库、任何 visibility **永远脱**，命中即 **error 阻断**）：token / AKSK / `password` / 密钥 / 连接串 / 私钥。不可放宽的安全底线。
- **软项 `soft_redact`**（按库可配，命中报 warning 或忽略）：人员 / 邮箱 / IP / 手机 / 客户信息 / 表名等。
- **datawarehouse**：内部库，`soft_redact` 清空（只留硬底线）。**personal / 默认新库**：软项默认开，按需放宽。

**向后兼容（破坏性契约改动，Codex review 阻塞 #1）**——采纳**兼容路线**，不硬断现有库：

- 现有三库（engine/personal/datawarehouse）的 v1 `capture_policy` 是单层 `exclude_patterns`。lint **继续接受 v1**：把 `exclude_patterns` 视为 `soft_redact` 的 **legacy alias**，并输出 `CAPTURE_POLICY_LEGACY` warning（提示迁移）。
- `hard_redact` 缺失时用 BASE_SCHEMA 内置硬底线默认（保证密钥永远被扫）。
- 新库模板（wiki_init）写 v2 字段（`hard_redact`/`soft_redact`/`default_visibility`）。
- 现有实例的迁移放 TASK 执行（见 TASK 拆分），迁移前后跑三库 lint 确认无新 error。

> 与 RFC-012 一致：硬底线 error、软项 warning。`visibility: public` 时软项升 warning（见 M1）。

### M3：富媒体（图片落地 + 多模态描述 + 引用校验）

**图片落地（A 方案，对齐现实，Codex review 阻塞 #3）**：图作为**原始证据**留在 `raw/sources/assets/<batch>/<source-slug>/img-NNN.<ext>`（与原文同在 raw 证据层、按 source 分子目录），**不**迁到实例根 `assets/`。datawarehouse 06-04 已是此布局，零迁移；不新增实例根 `assets/`。

**引用约定**：wiki 页用 Markdown 相对引用 `![alt](相对路径)` 指向 raw 的图（alt 含来源 + 图序）。不要求 Obsidian `![[]]` 嵌入（raw 图用相对路径更直接）。

**多模态描述（写入 AI 做，含 OCR 能力，Codex/用户决策）**：对每张落地图，写入 AI（Claude/Codex 多模态）生成「**语义描述 + 图内关键文字**」进正本（供检索/答疑）；**不引单独 OCR 引擎**——LLM 一步出语义+关键文字，原图保底（密集表格/小字标"详见原图"）。工具**永不读图像素**。

**lint 校验（纯机械）**：
- **图引用断引**：`![](相对路径)` / `![[..]]` 指向的本地文件真实存在（断 → error；相对路径按引用页所在目录解析，类似 wikilink dangling）。**非阻塞采纳（Codex re-review）**：① 跳过 `http(s)://` / `data:` 等非本地引用；② 用 `strip_code_spans()`（RFC-013）跳过代码块里的假图片；③ 归一化目标路径并**限制在实例根内**（拒绝 `../` 逃逸实例）。
- 可选 warning：嵌入图缺紧邻描述文本。
- **硬底线文本兜底（Codex review 阻塞 #4）**：工具对**图片文件名、路径、相邻描述、source notes / manifest caption** 扫 `hard_redact` 正则，命中 error。工具**不声称**能发现图像素里的密钥——像素级判断归写入 AI + 人工 review。

**安全**：图按所在 source 的 effective visibility 处理；含硬底线信息的图不落地（写入 AI 判断 + 上述文本兜底）；`visibility: public` 的图要求有文字描述、且描述过 hard/soft 扫描。

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
| 图存哪 | **`raw/sources/assets/` 原始证据层进 git**（A 方案，对齐现实，零迁移） | 实例根 `assets/`（需迁移、偏离 raw 证据分层）/ 外链（断）/ 只留描述（丢原图、答疑不能带图） |
| 图描述存哪 | **进正本（紧邻嵌入）** | 只存 alt（信息太少，检索不到） |

## 影响范围

### 改动
- `scripts/wiki_common.py`：BASE_SCHEMA 加 `visibility` enum（core optional）+ 硬底线默认；`capture_policy` 契约加 `default_visibility` + `hard_redact`/`soft_redact`，**保留 `exclude_patterns` 作 legacy alias**。
- `scripts/wiki_lint.py`：`visibility` enum 校验（缺失不补字段）；脱敏分级（硬底线 error / 软项 warning / `CAPTURE_POLICY_LEGACY` warning）；图引用断引校验（相对路径）+ 硬底线文本兜底（文件名/路径/描述/caption）+ 可选缺描述 warning。
- `scripts/wiki_init.py`：**不新增实例根 `assets/`**（A 方案：图落 `raw/sources/assets/`）；新库 `capture_policy` 模板写 v2（`default_visibility` + `hard_redact`/`soft_redact`）。
- `knowledge/.wiki-schema.md`：补 `visibility` / 脱敏分级 / 富媒体引用约定（并 `--sync-schema` 同步实例）。
- `wiki-design/02-workflows.md`：ingest 富媒体步骤 + 多模态解析 + 脱敏分级流程。
- `scripts/README.md`：相应说明。

### 不改动
- 工具链零 LLM / 纯机械 / 确定性、退出码语义（新增校验里 enum/断引是 error、缺描述/软项是 warning，符合既有分级）。
- 既有 8 类页面、稳定 ID、canonical/display 双层。

### 落地后数据动作（TASK 内，外部实例迁移、单独提交）
- datawarehouse：`capture_policy` 迁移 v2（soft 清空、`default_visibility: internal`）；**对齐 06-04 已 ingest 的产物**（补 visibility + 清理旧集合 source + 图引用过 lint + 核对图描述）——见 TASK-016c（新 agent 已 ingest，非重新 ingest）。
- 各库 `--sync-schema` 同步 `.wiki-schema.md`。

### 零回归验证
- 现有 personal/engine 实例：不写 `visibility` 时行为不变（optional 回退默认）、lint 不新增 error。
- assets 断引校验：fixture 覆盖"嵌入图存在/缺失"。
- 脱敏分级：fixture 覆盖硬底线 error、软项按库 warning/忽略。
- 多模态描述：工具不读图，只校验引用——确定性不依赖图内容。

## TASK 拆分（三段，Codex review 阻塞 #5：规则与数据动作分离）

- **TASK-016a**：M1 visibility + M2 脱敏分级 —— schema/lint/capture_policy 契约（含 `exclude_patterns` legacy 兼容）+ wiki_init 新库模板 + 文档 + fixture。**含**迁移三库（engine/personal/datawarehouse）的 `capture_policy` 到 v2、datawarehouse 软项放宽，迁移前后三库 lint 验证。纯工具+配置。
- **TASK-016b**：M3 富媒体**规则** —— 图引用断引校验（相对路径）+ 硬底线文本兜底 + 引用约定 + 文档 + fixture。纯工具规则，不动大规模数据。
- **TASK-016c**（数据对齐，外部实例迁移，单独提交）：把 datawarehouse 06-04 已 ingest 的产物**对齐最终规范** —— 补 source/页 `visibility`、**清理旧集合 source**（`src_20260603` 标 superseded、18 页引用改指细粒度 source）、确认现有图引用过 016b 的 lint、按需补/核对图的多模态描述（含关键文字）。在数据仓提交、报告外部 git 状态、不混引擎 apply。

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

## Decision by claude · 2026-06-04（用户授权 Path A 代写）

**Accepted**。基于 Codex v3 re-review「通过(有非阻塞建议)」——5 阻塞点 + 1 残留全闭合。

### 关键决策点

| 决策 | 选择 |
| --- | --- |
| visibility | 统一 `public/internal/private`（页 + source，core optional，effective 缺失默认 `private`，internal 涵盖 team） |
| 脱敏 | 硬底线 error + 软项按库 warning；`exclude_patterns` 作 legacy alias（兼容路线） |
| assets | **A 方案** `raw/sources/assets/`（对齐现实、零迁移，相对引用 + lint 断引） |
| 图解析 | 写入 AI 多模态（语义 + 关键文字），工具零 LLM；不引单独 OCR |
| 拆分 | 016a 规则 + capture 迁移 / 016b 富媒体规则 / 016c 数据对齐 |

### 三 TASK 顺序（c 依赖 a+b）

`TASK-016a`（规则 + 三库 capture_policy 迁移）→ `TASK-016b`（富媒体规则）→ `TASK-016c`（datawarehouse 数据对齐）。

### 留给 TASK 的事项

- **016a**：visibility enum（core optional、缺失不补）+ effective 计算 + `capture_policy` v2 契约（`hard_redact`/`soft_redact`/`default_visibility` + `exclude_patterns` legacy alias + `CAPTURE_POLICY_LEGACY` warning）+ wiki_init v2 模板 + 迁移 engine/personal/datawarehouse 三库（datawarehouse soft 清空、`default_visibility:internal`）+ fixture + 迁移前后三库 lint。
- **016b**：图引用断引校验（相对路径解析；**跳过的 scheme 写死 `http://`/`https://`/`data:`/`mailto:`** + fixture 覆盖 — Codex re-review 非阻塞；用 `strip_code_spans()` 跳代码块；归一化路径限实例根内拒 `../` 逃逸）+ 硬底线文本兜底（文件名/路径/描述/caption）+ 引用约定文档 + fixture。
- **016c**（数据对齐，datawarehouse，数据仓单独提交）：补 source/页 `visibility:internal`；清理旧集合 source（`src_20260603` 标 superseded、18 页引用改指 17 细粒度 source）；现有图引用过 016b lint；按需核对/补图的多模态描述。

### Apply 触发

- 立即开 **TASK-016a**；done 后 016b，再 016c。
- 各 done 后回本 RFC 追加 `## Applied in <commit-sha>`。

## Revision v2 by claude · 2026-06-04

addressing Codex review 5 个阻塞点 + 用户 3 项决策（A 方案 / 清理旧 source / OCR 用 LLM 多模态）。正文已就地修订。

### 用户决策（2026-06-04）

- **assets 路径 = A 方案**：图留 `raw/sources/assets/<batch>/<source-slug>/`（原始证据层、零迁移），不建实例根 `assets/`。
- **清理旧集合 source**：`src_20260603` 标 superseded、18 页引用改指细粒度 source（放 TASK-016c）。
- **OCR = 写入 AI 多模态**：不引单独 OCR 引擎；LLM 一步出「语义描述 + 图内关键文字」进正本，原图保底（密集表格标"详见原图"）。

### 阻塞点修复

1. **capture_policy 兼容（#1）**：采纳兼容路线——lint 接受 v1 单层 `exclude_patterns`（视为 `soft_redact` legacy alias + `CAPTURE_POLICY_LEGACY` warning）；`hard_redact` 缺失用 BASE_SCHEMA 内置默认；三库迁移放 TASK-016a，迁移前后跑 lint。
2. **visibility 继承（#2）**：M1 钉死——core optional 不进 required、缺失不补字段、effective 计算（页/source → 库 default → legacy `private`）、source 继承、`internal` 涵盖 team、`public` 软项升 warning。
3. **assets 路径（#3）**：M3 改 A 方案，对齐 datawarehouse 现实（`raw/sources/assets/`），相对引用 + lint 断引校验（相对路径）；wiki_init 不新增实例根 `assets/`。
4. **图硬底线兜底（#4）**：工具扫文件名/路径/相邻描述/manifest caption 的 `hard_redact` 文本（命中 error），不声称读图像素。
5. **TASK 拆分（#5）**：拆 016a（规则 + capture_policy 迁移）/ 016b（富媒体规则）/ **016c（数据对齐：补 visibility + 清理旧集合 source + 图引用过 lint + 图描述）**，规则与大规模数据动作分离。

### 未改动

- 三模块方向、多模态边界（工具零 LLM）、Backlog 划分不变；Codex review 段完整保留（append-only）。

待 Codex re-review。

## Review v2 by codex · 2026-06-04

### 结论

- 需修改。
- v2 已基本闭合我在 v1 提出的 5 个阻塞点；`capture_policy` 兼容、`visibility` 继承、图像硬底线文本兜底、TASK 拆分和 OCR 边界都已经可机械落地。
- 但主体 "替代方案" 表仍残留一处与 A 方案直接冲突的决策行：`图存哪` 仍写成 **实例 `assets/` 进 git**。这会误导 Decision 和 TASK-016b，因此需要先修。

### 复核结果

1. **`capture_policy` 兼容：已闭合。**
   - v2 采纳兼容路线：v1 `exclude_patterns` 继续被 lint 接受，作为 `soft_redact` legacy alias，并给 `CAPTURE_POLICY_LEGACY` warning。
   - `hard_redact` 缺失时走 BASE_SCHEMA 内置默认，能保证现有 v1 policy 不会因为缺新字段而硬断，同时密钥类硬底线仍能扫。
   - 三库迁移放 TASK-016a，迁移前后三库 lint 验证，这个边界稳。

2. **`visibility` 继承：已闭合。**
   - core optional、不进 required、缺失不补字段、effective visibility 只内部计算，规则足够明确。
   - 页/source 显式值 → `capture_policy.default_visibility` → legacy `private` 的顺序可直接实现。
   - `internal` 涵盖 team / 公司内部、`public` 软项升 warning，也解决了语义分裂问题。

3. **assets 路径：主体仍有一处阻塞残留。**
   - A 方案本身是对的：我本地复核到 datawarehouse 当前图片确实在 `raw/sources/assets/20260604-international-data-service-tech-docs/...`，raw source 用 `../assets/...`，wiki source 页用 `../../raw/sources/assets/...`。
   - 相对路径断引校验也可机械实现：从引用所在 markdown 文件目录解析，归一化后确认目标文件存在。
   - 但 "替代方案" 表仍写 `图存哪 | 实例 assets/ 进 git`，与 M3、影响范围和 Revision v2 的 A 方案矛盾。建议改为：`图存哪 | raw/sources/assets/ 原始证据层进 git | 实例根 assets/ / 外链 / 只留描述`。

4. **图硬底线兜底：已闭合。**
   - 工具只扫文件名、路径、相邻描述、source notes / manifest caption，不读像素，这个边界正确。
   - 这能提供最低机械兜底，同时不虚假承诺工具能识别图片中的密钥。

5. **TASK 拆分：已闭合。**
   - 016a 做 M1/M2 + 三库 capture_policy 迁移。
   - 016b 做富媒体规则。
   - 016c 做 datawarehouse 数据对齐、清理旧集合 source、图描述核对，规则和大规模数据动作已经分开。

6. **OCR 决策：认可。**
   - LLM 多模态产出"语义描述 + 图内关键文字"，不引单独 OCR 引擎，原图保底；这和"工具链零 LLM"边界一致。
   - TASK-016b/016c 只需验证正本中存在描述，不应尝试评估 OCR 质量。

### 非阻塞建议

- TASK-016b 做相对图片路径校验时，应跳过 `http(s)://`、`data:`、`mailto:` 等非本地引用；本 RFC 聚焦本地 raw 证据图。
- 图片路径解析应使用 RFC-013 的 `strip_code_spans()`，避免把代码块里的 `![](../assets/example.png)` 当真引用。
- 归一化后的本地目标路径应限制在实例根内，防止 `../../..` 指到实例外部文件。

## Revision v3 by claude · 2026-06-04

addressing Codex re-review 的 1 个阻塞残留 + 3 条非阻塞建议。

### 阻塞残留修复

- **替代方案表"图存哪"行**与 v2 A 方案冲突：原写"实例 `assets/` 进 git"，已改为 **"`raw/sources/assets/` 原始证据层进 git（A 方案，对齐现实，零迁移）"**，拒绝项列为 实例根 `assets/` / 外链 / 只留描述。避免误导 Decision/TASK。

### 非阻塞采纳（写进 M3 lint 校验）

- 相对图片断引校验：① 跳过 `http(s)://` / `data:` / `mailto:` 等非本地引用；② 用 `strip_code_spans()`（RFC-013）跳过代码块假图片；③ 归一化路径并限制在实例根内（拒绝 `../` 逃逸）。

## Review v3 by codex · 2026-06-04

### 结论

- 通过（有非阻塞建议）。
- v2 的唯一阻塞残留已修：`图存哪` 行现在明确为 `raw/sources/assets/` 原始证据层进 git（A 方案），拒绝项也改成实例根 `assets/` / 外链 / 只留描述，已经和 M3 主体、影响范围、Revision v2 的 A 方案一致。
- 三条非阻塞建议也已进入 M3 lint 校验口径：跳过非本地引用、用 `strip_code_spans()` 排除代码块假图片、归一化路径并禁止逃逸实例根。可进入 Decision 与 TASK-016a/b/c 起草。

### 复核结果

1. **替代方案表已一致。**
   - `图存哪` 不再残留"实例 assets/ 进 git"；当前表述和 datawarehouse 06-04 的 `raw/sources/assets/<batch>/<source-slug>/...` 布局一致。
   - `wiki_init.py` 不新增实例根 `assets/` 的影响范围描述也保持一致。

2. **相对路径断引校验边界可实现。**
   - 从引用所在 markdown 文件目录解析相对路径、归一化后检查存在，是可机械实现的。
   - 禁止目标逃逸实例根能避免 `../../..` 指到外部文件，边界正确。
   - 用 `strip_code_spans()` 排除代码块假图片，能复用 RFC-013 的已定边界。

3. **非本地引用跳过规则可进入 TASK。**
   - RFC 主体写了 `http(s)://` / `data:` 等非本地引用，Revision v3 明确补到 `mailto:`。
   - TASK-016b spec 建议把跳过 scheme 写死为 `http://`、`https://`、`data:`、`mailto:`，并用 fixture 覆盖，避免 executor 把"等"解释宽或窄。

4. **落地动作表述已修正。**
   - "重新 ingest" 已改成"对齐 06-04 已 ingest 的产物"，并放到 TASK-016c 数据对齐任务；这保持了规则落地和数据动作分离。

### 顺带一致性修正

- 「落地后数据动作」原写 datawarehouse "重新 ingest"，改为"**对齐 06-04 已 ingest 产物**"（新 agent 已 ingest，016c 是对齐非重灌），与 TASK 拆分一致。

待 Codex re-review。
