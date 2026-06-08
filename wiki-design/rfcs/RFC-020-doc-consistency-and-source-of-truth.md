---
id: rfc_20260608_020
title: 文档一致性根治（doc-consistency 校验 + 写入指令正本收敛 + RFC 准入 gate）
author: claude
status: proposed
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

## Review by codex · YYYY-MM-DD

（由 codex 追加，不覆盖本提案正文。）

## Decision

（由用户填写，或用户明确授权某 Agent 代写。）
