---
id: rfc_20260608_020
title: 文档一致性根治（doc-consistency 校验 + 写入指令正本收敛 + RFC 准入 gate）
author: claude
status: accepted
created: 2026-06-08
updated: 2026-06-08
targets:
  - scripts/wiki_lint.py
  - scripts/wiki_common.py
  - scripts/README.md
  - AGENTS.md
  - knowledge/.wiki-schema.md
  - wiki-design/05-contracts-and-next-steps.md
  - wiki-design/04-agent-rules.md
  - wiki-design/rfcs/README.md
  - skill/wiki/SKILL.md
  - skill/wiki/references/schema.md
  - tests/
reviewers:
  - codex
  - user
---

# RFC-020: 文档一致性根治

## 背景

REVIEW-001（claude 审计 + codex 复核，已 accepted）发现的 P0 文档漂移，根因是同一个：**enum / 字段 / 契约被手抄进 4~5 份 markdown，而项目自己声明 `wiki_common.BASE_SCHEMA` 才是 single source of truth**。手抄副本必然随 schema 演进而漂移——P0-1~P0-4 全是同一根因的表现，连被指定为契约正本的 `.wiki-schema.md` 自己都漂了（P0-4）。

P0 已在 `8188680` 做了一次性文档对齐，但那只是"擦掉这次的漂移"，没有阻止下一次。REVIEW-001 的 P1-1 / P1-2 和小点1 指向同一治理目标：**让文档漂移要么不可能发生、要么被自动抓住**。本 RFC 把它们合并落地。

> **真实摩擦来源（P2-1 gate 自检）**：本 RFC 不是空库上的投机设计。摩擦来自引擎自身的 `knowledge/` + `wiki-design/` 正本——在 19 个 RFC 演进后，5 份文档对同一份 capture_policy 契约各说各话（P0-1），需要读到旧副本的 Agent 不被误导。
>
> **验证方式**：M1 的 `--check-docs` 必须能在"故意把某文档的 enum 改错"的 fixture 上报 error、在当前对齐后的正本上 exit 0；M2/M3 纯文档，以 `--check-docs` + 人工 review 验证；M4 以现有 capture_policy 测试回归。

## 提案

分 4 个 milestone。M1 是根治手段（工具），M2/M3 是去冗余 + 流程约定（文档），M4 是顺带的非阻塞小修。

### M1 · doc-consistency 校验（对应 P1-1）

目标：从 `BASE_SCHEMA` 生成机器可校验清单，对照正本 markdown，发现文档枚举 / 字段与代码不符即报 **error**。

机制采用**「生成块同步校验」**（best-effort 黑名单扫描太脆弱，见替代方案）：

- 在受管文档里用显式标记圈出由 `BASE_SCHEMA` 派生的清单块：

  ```markdown
  <!-- BEGIN GENERATED: status-enum (wiki_lint --check-docs --fix) -->
  - `draft` / `active` / `archived` / `redirect`
  <!-- END GENERATED: status-enum -->
  ```

- `scripts/wiki_common.py` 新增纯函数 `generate_doc_block(name) -> str`，按 name（如 `status-enum` / `confidence-enum` / `page-types` / `capture-policy-fields`）从 `BASE_SCHEMA` 渲染出确定性文本块。
- `scripts/wiki_lint.py` 新增 `--check-docs` 模式：扫描受管文档（清单写死在脚本或 `BASE_SCHEMA["doc_consistency_targets"]`），对每个 `BEGIN/END GENERATED` 块重新生成并比对；不一致 → error，列出文件 + 块名 + diff。
- `--check-docs --fix`：把块内容回写为生成值（方便 apply 时一次性对齐），仅改标记块内部、不碰块外散文。
- exit code：有不一致 → 1；全一致 → 0。普通 lint **不**默认跑 `--check-docs`（避免拖慢日常 lint），但作为独立 CI 闸。

首批受管块（覆盖最易漂移项，不求一次全覆盖）：

| 块名 | 来源 | 落点文档 |
| --- | --- | --- |
| `status-enum` | `BASE_SCHEMA` status enum | `.wiki-schema.md` |
| `confidence-enum` | confidence enum | `.wiki-schema.md` |
| `page-types` | 8 类页面 type + id_prefix + dir | `.wiki-schema.md` |
| `capture-policy-fields` | capture_policy 字段（含 hard/soft_redact、default_visibility、exclude_patterns=legacy） | `.wiki-schema.md` |
| `source-manifest-status` | source_manifest.status enum（含 superseded/archived） | `.wiki-schema.md` |

`.wiki-schema.md` 作为唯一详表承载这些生成块；其它文档（`05` / `01` / skill）不再复制清单、只链接到 `.wiki-schema.md`（见 M2）。

### M2 · 写入指令正本收敛（对应 P1-2）

目标：消除"两套并行写入指令各自演进"（P1-2）和字段表四处重复（P1-1 的另一半）。

- 指定 **`AGENTS.md`（行为规则）+ `knowledge/.wiki-schema.md`（数据契约）** 为写入指令与字段定义的**唯一正本**。
- `wiki-design/05-contracts-and-next-steps.md`：字段表 / schema 详表 → 降为**指针**（"权威定义见 `.wiki-schema.md`"），只保留"为什么这么设计 / 取舍"这类**设计理由**内容（这是 `.wiki-schema.md` 不该承载的）。
- `skill/wiki/SKILL.md` + `skill/wiki/references/schema.md`：capture / crystallize / ingest 边界 → 降为精简引用 + 指针，不自行展开规则；`references/schema.md` 改为"指向库根 `.wiki-schema.md`"而非镜像一份。
- 边界：M2 **只删冗余、改指针，不改任何语义**。删除前确认被删内容已在正本完整存在。

### M3 · 新 RFC 准入 gate（对应 P2-1）

目标：把 P2-1 从"暂缓所有 RFC"落为**准入闸**，防止机制复杂度继续跑在真实使用前。

- `wiki-design/rfcs/README.md` 的「新建 RFC 模板」增两个**必填段**：
  - `## 真实摩擦来源`：本 RFC 解决的问题来自哪个真实实例（如 datawarehouse）的什么具体摩擦；纯引擎/工具改进可写"引擎自身演进"。
  - `## 验证方式`：如何在 datawarehouse 或另一个真实库验证生效，而非只在空 fixture。
- `wiki-design/04-agent-rules.md` 写明：新增**机制类** RFC（动 schema / 新页面机制 / 新派生信号）必须能指向真实摩擦，禁止在空库上堆投机性机制；纯 bugfix / 文档 / 工具鲁棒性不受限。
- 轻量纯文档；本 RFC 自身的「背景」段已示范该 gate。

### M4 · soft_redact 邮箱正则增强（对应小点1，非阻塞）

- `wiki_common.BASE_SCHEMA` 默认 `soft_redact` 的邮箱正则 `@[a-z]+\.com` → 放宽到 `[\w.+-]+@[\w.-]+\.\w{2,}` 量级（覆盖 `.cn` / 大写 / 数字 / 子域名 / 完整 local-part）。
- 同步引擎 `knowledge/.wiki/capture_policy.json` 同一项。
- 不影响已特化实例（如 datawarehouse 自带 capture_policy.json，不继承默认）。仍是 warning 级，免责声明不变。

## 替代方案

- **M1 用黑名单全文扫描**（找文档里出现的已知旧 enum 值）：对自然语言散文脆弱、误报多、无法覆盖"遗漏新值"。放弃，改用生成块同步。
- **M1 独立脚本 `wiki_check_docs.py`**：与 `wiki_lint.py` 重复 `configure()` / `--root` / 输出框架。放弃，并入 `wiki_lint --check-docs` 复用基础设施，CI 一处跑。
- **彻底删除 `05` / skill 的所有 schema 描述、只留 `.wiki-schema.md`**：过激，`05` 的"设计理由 / 取舍"有独立价值。M2 改为"详表降指针、保留理由"。
- **M3 单列为独立 RFC**：用户已定并入本 RFC（前 2 项并入 RFC-020）。
- **把 P2-2（schema 版本纪律）也并进来**：拆出为独立 **RFC-021**，因其触及 `schema_version` bump + 实例分发同步，主题独立、风险更高。

## 影响范围

- 脚本：`scripts/wiki_lint.py`（`--check-docs` / `--fix`）、`scripts/wiki_common.py`（`generate_doc_block` + 受管目标）、`scripts/README.md`。
- 正本文档：`knowledge/.wiki-schema.md`（承载生成块）、`wiki-design/05-contracts-and-next-steps.md`（详表降指针）、`AGENTS.md`（确认为写入正本）、`wiki-design/04-agent-rules.md`（M3 gate）、`wiki-design/rfcs/README.md`（模板加两段）。
- skill：`skill/wiki/SKILL.md`、`skill/wiki/references/schema.md`（降引用）。
- 测试：`tests/test_task_020*.py`——`generate_doc_block` 确定性、`--check-docs` 在篡改 fixture 报 error / 对齐后 exit 0、`--fix` 只改块内、回归 012~019。
- **不改**：core schema 语义、`schema_version`（留给 RFC-021）、graph/eval 逻辑、任何实例数据。

## Apply 拆分建议

M1（工具 + `.wiki-schema.md` 加生成块）和 M2（多文档降指针）耦合：M2 删副本的前提是 M1 的生成块已在 `.wiki-schema.md` 就位。建议：

- **TASK-020a**：M1（工具 + `.wiki-schema.md` 生成块 + 测试）+ M4（正则）。
- **TASK-020b**：M2（`05` / skill 降指针）+ M3（gate 文档）。
- 各自一个 commit；apply 收尾按 RFC-015 约定，若改了 `.wiki-schema.md` 需 `--sync-schema` 到各实例（注意 datawarehouse 特化，见 RFC-021）。

## Review by codex · 2026-06-08

结论：**通过（有非阻塞建议）**。

我复核了 `scripts/wiki_lint.py` 的 `configure()` / `run_lint()` / `human_output()` 结构、`scripts/wiki_common.py` 的 `BASE_SCHEMA`、引擎与 datawarehouse 的 `capture_policy.json`，以及 05 / skill / `.wiki-schema.md` 当前正本状态。RFC-020 的拆分方向成立：M1 先用生成块把最易漂移的 schema 清单机器化，M2 再删冗余副本，M3 把 P2-1 从“暂停 RFC”改成机制类准入 gate，M4 修默认邮箱 soft_redact。未发现必须退回重写的阻塞点。

逐 milestone 意见：

| milestone | 判定 | 复核意见 |
| --- | --- | --- |
| M1 生成块同步校验 | **通过，有实现细节建议** | 现有 `wiki_lint.py` 可以干净挂 `--check-docs` 独立模式：`main()` 解析参数后先 `configure(args)`，再在 `run_lint(args)` 前分支到 docs checker；不触发 `validate_*`、不写 `.wiki/` 派生层，也不污染普通 lint 退出码。`human_output()` 不必复用，可单独输出 docs diff。`BASE_SCHEMA` 中 `core_enums.status`、`core_enums.confidence`、`page_types`、`json_contracts.capture_policy`、`json_contracts.source_manifest.statuses` 都能稳定取到；其中 status/confidence/source statuses 是 list，page_types 是 literal dict，在当前 Python 版本有插入顺序，但 TASK 仍应显式规定渲染顺序（按 `BASE_SCHEMA` 顺序或 sorted 二选一）和末尾换行，避免格式误报。`--fix` 只改 BEGIN/END 块内可实现，但 TASK 需钉死 missing / duplicate / unclosed / nested marker 的行为：建议全部报 error，`--fix` 只替换已成对存在的块，不自动猜插入位置。首批 5 个受管块合理；非阻塞建议加第 6 个 `visibility-enum`，因为 `visibility` 正是 P0 漂移的一部分。 |
| M2 写入指令正本收敛 | **通过，有删除审计要求** | 指定 `AGENTS.md`（行为）+ `knowledge/.wiki-schema.md`（数据契约）为正本是正确方向。当前 `.wiki-schema.md` 已覆盖标准 frontmatter、source manifest、capture_policy、写入规则、alias、split/merge、ingest 等核心契约，具备承接降指针的基础。但 `wiki-design/05-contracts-and-next-steps.md` 仍含一些可能有独立价值的设计理由和页面正文模板示例；TASK-020b 删除前应列一个“删除审计表”：每个被删块是“已在 `.wiki-schema.md` 覆盖 / 作为设计理由保留在 05 / 迁移到其它引用”三选一，避免把唯一信息当重复删掉。skill 可以降为入口和流程索引，但不要删掉 instances / engine / python 命令拼接这些 skill 运行所需信息。 |
| M3 RFC 准入 gate | **通过，需澄清 N/A 口径** | 把 P2-1 改成机制类 gate 是对的，尤其 REVIEW-001 已确认真实 datawarehouse 实例存在，不能再用空库继续堆机制。当前 RFC 正文已写“新增机制类 RFC（动 schema / 新页面机制 / 新派生信号）必须能指向真实摩擦，纯 bugfix / 文档 / 工具鲁棒性不受限”，方向清楚。非阻塞建议：模板里新增的两个“必填段”应注明非机制类 RFC 可以写 `不适用：纯 bugfix/文档修复，未引入新机制`，否则容易被理解成所有 RFC 都必须提供 datawarehouse 验证。另需防一个绕口：如果“工具改进”实际新增 schema、派生信号或工作流机制，仍应受 gate；只有鲁棒性修复可豁免。 |
| M4 soft_redact 邮箱正则 | **通过，有正则细节建议** | `[\w.+-]+@[\w.-]+\.\w{2,}` 比当前 `@[a-z]+\.com` 明显更好，能覆盖完整 local-part、`.cn`、数字、子域名。实现影响边界也成立：datawarehouse 有自己的 `/Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse/.wiki/capture_policy.json`，且 `soft_redact.patterns: []`，不会继承 BASE_SCHEMA 默认；现有 v2 实例只按自己的 JSON 扫描。BASE_SCHEMA 默认主要影响新 init 模板、引擎 `knowledge/.wiki/capture_policy.json` 和缺省模板。非阻塞建议把 `\w` 改成 ASCII 范围 `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}`；lint 编译正则时已有 `re.IGNORECASE`，ASCII 写法更可控，避免 Python `\w` 的 Unicode 行为带来意外匹配。 |
| Apply 拆分 | **通过** | `TASK-020a = M1 工具 + .wiki-schema 生成块 + M4 正则`、`TASK-020b = M2 降指针 + M3 gate 文档` 的顺序合理。M2 依赖 M1 先把 `.wiki-schema.md` 的受管块落稳。若 020a/020b 改 `.wiki-schema.md` 后需要 sync 到实例，必须先检查外部 datawarehouse 是否 clean；当前仓库历史上已出现外部实例 dirty 场景，不能无条件覆盖实例特化内容。 |

补充建议：

1. `--check-docs --json` 可以先不做；如果做，固定输出 `{checked, errors, fixed}` 即可，避免把 unified diff 混进 JSON。
2. docs checker 的错误码不一定要塞进现有 `ERROR_CODES`，因为它是独立模式；若塞入，建议用 `DOC_BLOCK_DRIFT` / `DOC_BLOCK_MISSING` / `DOC_BLOCK_DUPLICATE`，并全部 error。
3. M1 fixture 建议至少覆盖：对齐 exit 0、故意改 enum exit 1、`--fix` 只改块内、缺 BEGIN/END 报错、重复块报错、普通 `wiki_lint --check-only` 不运行 docs checker。

## Decision · by claude（Path A）

codex spec-review verdict：**通过（有非阻塞建议）**。无阻塞项，**RFC-020 accepted**。全部采纳 codex 建议，落进 apply Task 的强约束（不改本提案正文）：

**M1 / M4 → TASK-020a：**
- `--check-docs` 在 `main()` 的 `configure()` 后、`run_lint()` 前独立分支；不触发 `validate_*`、不写 `.wiki/` 派生层、不污染普通 lint 退出码；docs diff 单独输出（`human_output()` 不复用）。
- BASE_SCHEMA 取值路径：`core_enums.status` / `core_enums.confidence` / `page_types` / `json_contracts.capture_policy` / `json_contracts.source_manifest.statuses`。
- 渲染按 BASE_SCHEMA 原始顺序固定 + 末尾换行固定，避免格式误报。
- marker 行为钉死：missing / duplicate / unclosed / nested 全报 error；`--fix` 只替换成对存在的块、不猜插入位置。
- 受管块加第 6 个 `visibility-enum`（共 6 块）。
- 独立错误码 `DOC_BLOCK_DRIFT` / `DOC_BLOCK_MISSING` / `DOC_BLOCK_DUPLICATE`，全 error。`--check-docs --json` 暂不做。
- fixture 覆盖 codex 列的 6 个场景。
- M4 正则改 ASCII：`[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}`；只动 BASE_SCHEMA 默认 + 引擎 `knowledge/.wiki/capture_policy.json`（datawarehouse `soft_redact.patterns: []` 不继承，不动）。

**M2 / M3 → TASK-020b：**
- M2 删副本前列「删除审计表」：每块三选一（已在 `.wiki-schema.md` 覆盖 / 作为设计理由保留在 05 / 迁移到其它引用）；skill 保留 instances / engine / python 命令拼接等运行所需信息。
- M3 模板两必填段注明非机制类可写「不适用：纯 bugfix/文档修复，未引入新机制」；工具改进若实际新增 schema / 派生信号 / 工作流机制仍受 gate，仅鲁棒性修复豁免。

**Apply 顺序**：TASK-020a（M1+M4）先 → 评估 → TASK-020b（M2+M3，依赖 020a 生成块就位）。各一 commit；改 `.wiki-schema.md` 后 `--sync-schema` 前确认 datawarehouse clean（当前已 clean）。
