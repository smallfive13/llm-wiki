---
id: review_20260608_001
title: llm-wiki 框架与内容审计（文档漂移 / 定义冗余 / 规模失衡）
author: claude
status: proposed
created: 2026-06-08
updated: 2026-06-08
reviewers:
  - codex
  - user
scope:
  - AGENTS.md
  - wiki-design/01-architecture.md
  - wiki-design/02-workflows.md
  - wiki-design/03-obsidian-graph.md
  - wiki-design/04-agent-rules.md
  - wiki-design/05-contracts-and-next-steps.md
  - wiki-design/README.md
  - knowledge/.wiki-schema.md
  - knowledge/index.md
  - skill/wiki/SKILL.md
---

# REVIEW-001: 框架与内容审计

本文件是一次跨正本的整体 review，不是 schema 变更提案。结论按优先级排列：每条给出**证据位置**、**问题**、**建议动作**。被接受的条目应各自拆成独立 RFC 落地，本 review 只负责把问题登记清楚。

审计范围：`AGENTS.md` + `wiki-design/01~05` + `wiki-design/README.md` + `knowledge/.wiki-schema.md` + `knowledge/index.md` + `skill/wiki/`，对照 `scripts/wiki_common.py` 的 `BASE_SCHEMA` 与实际 `knowledge/.wiki/capture_policy.json`。当前演进进度：RFC-001~019 已 accepted/applied。

## 总体判断

工程纪律明显高于同类"AI 知识库"项目，方向正确。值得保留的核心优点：

- 正本 / 派生层分离干净，派生层一律可重建、进 `.gitignore`。
- 稳定 ID（`<prefix>_YYYYMMDD_<slug>`，永不随标题 / slug / 路径变化）。
- canonical 引用（按 ID，lint 严格校验）与显示层 wikilink 双轨分离。
- RFC → Task → Evaluation 的可审查多 Agent 协作闭环。
- capture → inbox → promote 的低摩擦缓冲，配 PII 兜底。
- profile 只允许增量、不能改 core 不变量的多实例约束。

需要优化的问题集中在三类：**文档漂移**、**定义冗余**、**规模与产出失衡**。

## P0 · 文档已出现实质漂移

正本之间已经不一致，会直接误导读到旧副本的 Agent。

### P0-1 capture_policy 的 PII schema 三处不一致

实际 `knowledge/.wiki/capture_policy.json` 与 `knowledge/.wiki-schema.md` 已升级为两级脱敏 + visibility：`hard_redact` / `soft_redact` / `default_visibility`（RFC-012 / RFC-016 之后的形态）。但：

- `wiki-design/05-contracts-and-next-steps.md`「Capture Policy Schema」段仍是旧的单层 `exclude_patterns`，未提 hard/soft 分级，也未提 visibility。
- `AGENTS.md`「低摩擦 capture」段仍按单层"规则化 PII pattern"描述，未提 hard/soft 分级与 `visibility`。
- `wiki-design/02-workflows.md`「被动 capture」段已经用了 `hard_redact` / `soft_redact`。

即同一份契约，三处正本各说各话。

**建议**：以 `.wiki-schema.md` + 实际 JSON 为准，统一回填 `05-contracts` 和 `AGENTS.md`；旧 `exclude_patterns` 仅作为 lint 接受的 legacy alias 在文档里标注，不再作为推荐写法。

### P0-2 index 状态行过期

`knowledge/index.md`「当前状态」写"Schema 版本：RFC-001~008 applied"，实际已 apply 到 RFC-019，落后 11 个 RFC。

**建议**：把该行改为指向 `wiki-design/rfcs/README.md` 索引，而不是手写一个会过期的区间；或在 apply RFC 的 Task 收尾步骤里强制更新此行。

### P0-3 README 推荐目录混入未落地结构

`wiki-design/README.md` 与 `01-architecture.md` 的"推荐目录"仍列着 `dashboards/*.base`、`.wiki/cache.json`、`.wiki/search_index/`、`.wiki/lightrag/`，这些尚未实现，读者会误认为是现状。

**建议**：把未落地项移入单独的"规划中 / 暂不做"段（`05-contracts` 末尾已有"暂不做"段，可合并到那里统一管理），现状目录只列真实存在的结构。

### P0 根因

enum / 字段 / 契约被**手抄进 4~5 份 markdown**，而项目自己声明 `wiki_common.BASE_SCHEMA` 才是 single source of truth。手抄副本必然随 schema 演进而漂移——上面三条都是同一根因的表现。

## P1 · 定义冗余放大维护成本

### P1-1 字段表四处重复

frontmatter 字段表几乎一字不差地出现在 `01-architecture.md`、`05-contracts-and-next-steps.md`、`knowledge/.wiki-schema.md`、`skill/wiki/references/schema.md` 四处；PII 免责声明、别名引用规则、拆分 / 合并语义也是多副本。每改一次 schema 要同步 4 个位置，P0 的漂移正是这么产生的。

**建议**：

- 让 `knowledge/.wiki-schema.md` 成为"数据长什么样"的**唯一**详表。`01` / `05` / skill 只保留"为什么这么设计"和指针链接，不再复制字段表。
- 新增 `scripts/wiki_check_docs.py`（或并入 lint 的 `--check-docs` 模式）：从 `BASE_SCHEMA` 生成 enum / 字段清单，对照指定 markdown，发现文档枚举值与 `BASE_SCHEMA` 不符即报 error。现有 `tests/test_task_*.py` 只测脚本行为，没有任何测试守护"文档 ↔ 代码"一致性，这正是漂移缺口。

### P1-2 两套并行写入指令

`AGENTS.md`「知识库写入规则」与 `skill/wiki/SKILL.md`「三种写入模式」是两套并行的写入指令，capture / crystallize / ingest 的边界措辞已略有出入。

**建议**：指定其一为正本（建议 `AGENTS.md` + `.wiki-schema.md`），skill 只做精简引用，避免两套规则各自演进。

## P2 · 规模与产出失衡

### P2-1 规范复杂度远跑在真实使用前

19 个 RFC、19 个 Task，一套两级脱敏 + alias 消歧 + 图谱社区检测 + 健康度评分的 schema——但 `knowledge/wiki/` 实际只有 **4 个页面**（1 synthesis + 3 topic），inbox 0 条，且这 4 页讲的是 llm-wiki 自身。绝大部分机制（entity 别名薄页、source-gap open-question、co_source 边、health score）未被真实知识量压测过。

风险有二：一是过度设计，某些精细机制可能在真用起来前就被推翻；二是反馈回路缺失，继续在空库上加规范，无法验证哪些设计真正有用。

**建议**：暂缓新增 RFC，先拿 1~2 个**真实、有体量**的知识库（如你自己某领域的笔记 / 资料）跑通 ingest → promote → query → eval 全流程，用真实摩擦驱动下一批优化，而不是在空库上继续堆规范。

### P2-2 schema 始终停在 version 1，缺迁移纪律

base schema 经过 19 个 RFC 已多次变更，但 `schema_version` 始终为 `1`，且 profile 要求 `schema_version` 与引擎严格相等。这意味着不同时间初始化的外部实例之间没有版本区分，将来分发 / 升级 `.wiki-schema.md` 时没有迁移依据。RFC-015 处理了分发断链，但未解决版本递增。

**建议**：给 `BASE_SCHEMA` 引入真实的版本递增纪律——凡改动 core 字段 / enum / JSON 契约的 RFC 必须 bump `schema_version`，并在 RFC 内附一段 migration note（旧实例如何升级）。

## 小点

- `capture_policy.json` 的 `soft_redact` 邮箱正则 `@[a-z]+\.com` 偏弱：漏掉 `.cn` / 大写 / 数字 / 子域名。文档虽反复声明"不是完整 PII 检测"，但既已内置就尽量别明显漏，建议至少放宽到 `[\w.+-]+@[\w-]+\.\w+` 量级。
- 全链路依赖 `conda activate py312` + 手动 `cd <engine>`，skill 里靠硬编码 python 全路径绕开。`02-workflows.md`「推荐命令形态」里那个"未来 `wiki` CLI"值得提前做一个薄 wrapper，显著降低使用摩擦与出错率。

## 建议处理顺序

1. **先修 P0**（纯文档对齐，无 schema 风险）：P0-1 capture_policy 三处对齐、P0-2 index 状态行、P0-3 README 目录标注。可在一个 `[docs]` commit 内完成，不需走 RFC（属 typo / 措辞 / 链接修复范畴）。
2. **再立 P1-1 的 doc-consistency 检查**（独立 RFC）：这是防止 P0 复发的根治手段。
3. **P1-2 / P2 各拆独立 RFC**，但 P2-1 的"先用真实库压测"建议在写新 RFC 前先做。

## Review by codex · YYYY-MM-DD

（留给 codex 追加，不覆盖本文。）

## Decision

（由用户填写，或用户明确授权某 Agent 代写。）

## Review by codex · 2026-06-08

结论：**需修改**。

我逐项打开正本和现有实例复核后，同意 REVIEW-001 的主线：确实存在文档漂移、定义冗余和部分流程/规模失衡。但 **P2-1 不能按原文成立**：审计只按引擎自带 `knowledge/` 的 4 页空库判断，漏算了真实在用的 `/Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse`。当前本机实测该实例 lint 通过，包含 33 个 wiki 页面、18 个 source manifest 条目、93 个图片文件（注意外部仓库当前 dirty；用户提示的 32/17/75 是较早或已提交基线口径）。RFC-016~019 的确已经由这个真实库摩擦驱动，因此“几乎没真实压测、建议暂缓新增 RFC”需要改写为“后续 RFC 必须继续以真实实例摩擦为输入，并先收敛 datawarehouse 当前 in-progress 数据基线”。

逐条判定如下：

| 条目 | 判定 | 复核意见 |
| --- | --- | --- |
| P0-1 capture_policy PII schema 漂移 | **同意，需小修措辞** | `wiki-design/05-contracts-and-next-steps.md` 的 `Capture Policy Schema` 仍是旧 `exclude_patterns` 单层写法，且 `PII 降级流程` 仍写“命中 exclude_patterns”。`knowledge/.wiki/capture_policy.json`、`knowledge/.wiki-schema.md` 已是 `default_visibility` + `hard_redact` + `soft_redact`，`wiki-design/02-workflows.md` 也已按 hard/soft 描述。`AGENTS.md` 不直接写 `exclude_patterns`，但仍只有泛化“规则化 PII pattern”口径并指向旧 05 schema，未表达 hard/soft/default_visibility，因此核心漂移成立。 |
| P0-2 index 状态行过期 | **同意** | `knowledge/index.md` 当前仍写 `Schema 版本：RFC-001~008 applied`，而 RFC 索引已到 RFC-019 accepted/applied 语义。建议改成指向 `wiki-design/rfcs/README.md`，避免继续手写区间。 |
| P0-3 推荐目录混入未落地结构 | **同意** | `wiki-design/README.md` 推荐目录列 `dashboards/`、`.wiki/cache.json`、`.wiki/search_index/`、`.wiki/lightrag/`；`wiki-design/01-architecture.md` 派生数据也列 `cache.json/search_index/lightrag`。当前引擎实例未落地这些路径；`.gitignore` 里有这些项只能说明规划或忽略策略，不能说明已实现。 |
| P1-1 字段表四处重复 | **同意** | `01`、`05`、`.wiki-schema.md`、`skill/wiki/references/schema.md` 都在不同粒度复制 frontmatter / JSON 契约 / alias / split-merge 等规则。skill 侧不是完全“一字不差”，但足以形成维护多副本。新增 doc-consistency 检查方向正确；当前测试主要守工具行为，未守“文档枚举/字段 vs BASE_SCHEMA”一致性。 |
| P1-2 两套并行写入指令 | **同意** | `AGENTS.md` 有“知识库写入规则”和“低摩擦 capture”，`skill/wiki/SKILL.md` 有“capture / crystallize / ingest 三种写入模式”。两者边界已经不完全一致：skill 的 capture PII 仍是旧泛化口径，也未表达 hard/soft/default_visibility；AGENTS 又指向 05 的旧 Capture Policy Schema。建议指定 AGENTS + `.wiki-schema.md` 为正本，skill 只保留执行入口和引用。 |
| P2-1 规范复杂度远跑在真实使用前 | **部分同意，必须重写** | 引擎自带 `knowledge/` 确实只有 4 页、0 source、0 inbox，不能压测所有机制；但 REVIEW 漏算真实 datawarehouse 实例。该实例当前 `wiki_lint --check-only` 为 error 0 / warning 0，扫描到 33 wiki 页、18 source；图片素材当前 93 个文件，且 RFC-016~019 均由其真实 ingest 摩擦推动。原文“几乎没真实压测”作为全局结论不成立。可保留的结论是：引擎示例库规模太小，不应再用空库证明新机制；新增 RFC 应要求提供真实实例复现/验证证据。 |
| P2-2 schema 始终 version 1 | **同意，需区分兼容/破坏** | `scripts/wiki_common.py` 的 `BASE_SCHEMA["schema_version"]` 仍为 1，profile 校验严格要求相等；`.wiki-schema.md` 示例也写 `schema_version: 1`。RFC-012~019 已增加 policy 常量、visibility、capture_policy v2、source status 等行为/契约，但没有版本递增或 migration note 纪律。不是所有兼容新增都必须立刻 bump，但 core enum / JSON 契约 / profile 可见行为变更应有明确 bump 或兼容策略。 |
| 小点：soft_redact 邮箱正则偏弱 | **同意，非阻塞** | `scripts/wiki_common.py` base soft_redact 和引擎 `capture_policy.json` 仍含 `@[a-z]+\.com`，确实漏 `.cn`、数字、子域名、完整 local-part。免责声明降低了风险，但默认规则明显弱，建议在 P0/P1 之后修。 |
| 小点：缺薄 wrapper，命令摩擦高 | **同意，非阻塞** | 当前只有 `wiki_init.py/wiki_lint.py/wiki_graph.py/wiki_eval.py`，没有统一 `wiki` CLI；`skill/wiki/SKILL.md` 还专门提醒不要把多词 conda 命令塞进 zsh 变量。这说明操作摩擦是真问题。 |

我补充两个 REVIEW 漏掉的问题：

1. `knowledge/.wiki-schema.md` 自身也有漂移：前文仍写“base schema 是 RFC-002~007 冻结的契约”，但 BASE_SCHEMA 后续已经承载 RFC-012~019 的 staleness、health、visibility、capture_policy v2、source status、ingest progress 等变化。这个应并入 P0 或 P1-1。
2. `knowledge/.wiki-schema.md` 末尾“写入规则”仍写“内容含密钥 / 客户姓名 / 内部业务等一律降级”，没有同步 hard/soft/default_visibility 的新边界；这与 P0-1 是同根漂移，修 P0 时应一并处理。

建议处理顺序：**基本同意但要调整**。

1. 先修 P0 文档漂移，范围应扩到 `.wiki-schema.md` 的“RFC-002~007”过期句和末尾写入规则；可作为纯文档对齐处理。
2. 随后做 P1-1 doc-consistency 检查，避免同类漂移复发。
3. P1-2 单独收敛 AGENTS / skill 职责边界。
4. P2-1 不应写成“暂缓所有新增 RFC”，应改成 gate：新增 RFC 必须说明来自哪个真实实例摩擦、如何在 datawarehouse 或另一个真实库验证；同时先把 datawarehouse 当前 dirty 工作树收敛成可引用基线。
5. P2-2 单独 RFC 讨论 schema_version / migration note 纪律。

只读验证已跑：

```text
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root knowledge --check-only
扫描: knowledge/wiki/ (4 文件) · knowledge/inbox/ (0 draft) · knowledge/raw/ (0 source)
错误: 0 · 警告: 0

/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse --check-only
扫描: datawarehouse/wiki/ (33 文件) · datawarehouse/inbox/ (0 draft) · datawarehouse/raw/ (18 source)
错误: 0 · 警告: 0
```
