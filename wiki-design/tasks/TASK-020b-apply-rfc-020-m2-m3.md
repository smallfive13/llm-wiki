---
id: task_20260608_020b
title: Apply RFC-020 M2+M3 — 写入指令正本收敛（05/skill 降指针）+ 新 RFC 准入 gate
author: claude
executor: codex
status: done
type: apply
created: 2026-06-08
updated: 2026-06-08
related_rfcs: [RFC-020]
---

# TASK-020b: Apply RFC-020 M2+M3

## 目标

落地 RFC-020 M2（写入指令 + 字段定义正本收敛：`AGENTS.md`（行为）+ `knowledge/.wiki-schema.md`（数据契约）为**唯一正本**；`wiki-design/05-contracts-and-next-steps.md` 的字段表 / schema 详表降为**指针**、只留设计理由；`skill/wiki/` 降为精简引用 + 指针）+ M3（新 RFC 准入 gate：`rfcs/README.md` RFC 模板加「真实摩擦来源」「验证方式」必填段 + `04-agent-rules.md` 写明 gate 适用边界）。M1 / M4 已由 TASK-020a 闭环。

## 前置条件

- RFC-020 status: accepted；TASK-020a status: done（6 个生成块已在 `.wiki-schema.md` 就位、`--check-docs` exit 0）。
- working tree clean（除本 task）。
- 环境：`/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python`（完整命令，勿塞 zsh 变量）。

## 强约束

1. **M2 只删冗余 / 改指针，不改任何语义**。删除前必须先产出「删除审计表」：每个被删块标三选一——(a) 已在 `.wiki-schema.md` 完整覆盖；(b) 属设计理由 / 取舍，保留在 05；(c) 迁移到其它引用。**不得把唯一信息当重复删掉。**
2. **skill 降引用但保留运行所需信息**：`instances.json` 用法、`engine` 字段、python 命令拼接、库识别 / 选择流程、lint/graph 校验投影步骤必须留；只删与 `AGENTS.md` / `.wiki-schema.md` 重复的字段表 / 规则镜像。
3. **M3 gate 适用边界写清**：两必填段允许非机制类 RFC 写「不适用：纯 bugfix / 文档修复，未引入新机制」；gate 只约束**机制类**（动 schema / 新页面机制 / 新派生信号 / 新工作流机制）；纯鲁棒性 / bugfix / 文档豁免；但"工具改进"若实际引入新机制仍受 gate。
4. **不改**：scripts 行为、core schema 语义、`schema_version`、任何实例数据。
5. 预期**不改 `knowledge/.wiki-schema.md`**（它已是正本）；若确需微调，apply 收尾按 RFC-015 `--sync-schema`（datawarehouse 当前 clean）。仅改 05 / skill / 04 / rfcs README 不触发 sync。

## 步骤

> **Step 0 spec-review**：通读 `05-contracts-and-next-steps.md` 全文，逐段分类「字段表 / schema 详表（可降指针）」vs「设计理由 / 取舍 / 下一步（保留）」；通读 `skill/wiki/SKILL.md` + `skill/wiki/references/schema.md`，分类「规则 / 字段镜像（降引用）」vs「运行信息（保留）」；核对 `rfcs/README.md`「新建 RFC 模板」段与 `04-agent-rules.md` 结构。**先把删除审计表草案贴出来，确认无误再动手删。**

1. **M2-05**：`05-contracts` 的字段表 / `Capture Policy Schema` / `Wiki Profile Schema` / `Capture Item Schema` / `Inbox Index Schema` 等**详表** → 降为指针「权威定义见 `knowledge/.wiki-schema.md` 的 <对应段>」，保留每段的设计理由 / 取舍。P0 刚更新过的 `Capture Policy Schema` 段同样降指针（它现在与 `.wiki-schema.md` 重复）。
2. **M2-skill**：`skill/wiki/SKILL.md` 三种写入模式 → 精简为「以库根 `AGENTS.md` + `.wiki-schema.md` 为准」+ 操作入口；`skill/wiki/references/schema.md` → 改为指向库根 `.wiki-schema.md`、不再镜像字段表。保留 instances / engine / python / 库识别等运行信息。
3. **M3-模板**：`wiki-design/rfcs/README.md`「新建 RFC 模板」加 `## 真实摩擦来源` + `## 验证方式` 两必填段，并注明非机制类可写「不适用：纯 bugfix / 文档修复，未引入新机制」。
4. **M3-rules**：`wiki-design/04-agent-rules.md` 加一节写 gate 适用边界（机制类必填真实摩擦 + 验证；鲁棒性 / 文档 / bugfix 豁免；工具改进若引入新机制仍受限）。
5. 跑验证 → commit（引擎一个 commit）。

## 验证

```bash
cd /Users/zhangjunwu/workspace/llm-wiki/llm-wiki
# M2 降指针不应破坏 .wiki-schema.md 的 6 个生成块
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root knowledge --check-docs; echo "check-docs exit=$?"
# 普通 lint 仍 exit 0
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root knowledge --check-only; echo "lint exit=$?"
# 全量回归（含 020a）
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest tests.test_task_012 tests.test_task_013 tests.test_task_014 tests.test_task_015 tests.test_task_016a tests.test_task_016b tests.test_task_017 tests.test_task_019 tests.test_task_020a
# 人工：删除审计表逐条核对；rg 抽查 05 / skill 不再保留与 .wiki-schema 重复的 enum / 字段详表
```

## 完成后报告格式

- Step 0 spec-review 结论 + **删除审计表**（每删块三选一标注 a/b/c）
- 改动文件 + 关键位置（05 降指针处、skill 降引用处、rfcs 模板两段、04 gate 节）
- 验证输出（check-docs exit 0、check-only exit 0、回归、审计表核对结论）
- commit sha
- 偏离或异常

## Execution log by codex · 2026-06-08

Step 0 spec-review 结论：通过，无阻塞。`05-contracts-and-next-steps.md` 的 schema 详表与字段表均可降为指针；设计理由、职责划分、实施顺序保留。`skill/wiki/` 可删除字段镜像，但必须保留 instances / engine / python / 库识别 / lint / graph / log 运行信息；已确认这些运行信息保留。`rfcs/README.md` 与 `04-agent-rules.md` 有清晰模板和 gate 落点。

删除审计表：

| 位置 | 块 | 判定 | 处理 |
| --- | --- | --- | --- |
| `wiki-design/05-contracts-and-next-steps.md` | `Review Queue Schema` JSON 示例 + 字段表 | (a) 已由 `.wiki-schema.md` 覆盖字段契约；(b) review queue 设计理由保留 | 降为指针，保留人工审查入口、canonical/display 分工、source_gap 晋升说明 |
| `05` | `Source Manifest Schema` 顶层格式 + 字段表 | (a) 已由 `.wiki-schema.md` 覆盖字段契约 | 降为指针，保留 source 单主键、manifest status 单一事实源 |
| `05` | `Capture Item Schema` 位置/命名/frontmatter/字段表/lint 表 | (a) `.wiki-schema.md` 覆盖 inbox/capture item 契约；(b) inbox 不算 wiki 页面理由保留 | 降为指针，保留低摩擦缓冲层与 archive 口径 |
| `05` | `Capture Policy Schema` JSON 示例 + 字段约束 | (a) `.wiki-schema.md` + `BASE_SCHEMA` 覆盖；(b) PII 降级设计理由保留 | 降为指针，保留 auto_capture opt-in、hard/soft redact、visibility effective 语义 |
| `05` | `Wiki Profile Schema` 示例/字段表/错误码 | (a) `.wiki-schema.md` + lint 覆盖；(b) 只增不改 / core invariant 保留 | 降为指针，保留 profile 扩展边界和不可改写不变量 |
| `05` | `Inbox Index Schema` 顶层格式 + 字段表 | (a) `.wiki-schema.md` 覆盖派生层格式；(b) 派生层非正本保留 | 降为指针 |
| `05` | `Normalized Alias Index Schema` 顶层格式 + 字段表 | (a) `.wiki-schema.md` 覆盖；(b) alias/redirect 设计理由保留 | 降为指针，保留派生层与算法实现边界 |
| `05` | `Frontmatter 生命周期字段` YAML + 字段表 | (a) `.wiki-schema.md` generated blocks + frontmatter 段覆盖 | 降为指针，保留“字段名不要变体膨胀”原则 |
| `05` | `最小页面模板` 六类模板 | (a) `.wiki-schema.md` 是模板正本 | 改为指针，保留 source/entity/query 的设计边界 |
| `05` | `答案引用格式` 示例 | (a) `.wiki-schema.md` 覆盖；(b) 引用优先级和 INFERRED 边界保留 | 降为指针，保留引用设计意图 |
| `skill/wiki/SKILL.md` | `schema 速查` 字段镜像 | (a) `.wiki-schema.md` 覆盖；(c) skill 保留操作入口 | 删除速查表，改为读取 `<root>/AGENTS.md` + `<root>/.wiki-schema.md` |
| `skill/wiki/references/schema.md` | frontmatter / 页面模板 / inbox / canonical / alias / ingest / profile 详表 | (a) `.wiki-schema.md` + `AGENTS.md` 覆盖；(c) skill 保留运行信息与流程入口 | 改成精简引用文档，保留 instances/engine/python/lint/graph 运行信息 |
| `wiki-design/rfcs/README.md` | RFC 模板 | (c) 迁移为准入模板要求 | 增加「真实摩擦来源」「验证方式」两段 |
| `wiki-design/04-agent-rules.md` | 新 RFC gate | (b) 新行为规则正本 | 增加机制类适用边界与“不适用”口径 |

改动文件与关键位置：

- `wiki-design/05-contracts-and-next-steps.md`：Review Queue / Source Manifest / Capture Item / Capture Policy / Wiki Profile / Inbox Index / Normalized Alias Index / Frontmatter / 最小页面模板 / 答案引用格式均降为 `.wiki-schema.md` 指针；保留设计理由与实施顺序。
- `skill/wiki/SKILL.md`：新增“写入正本”段；三种写入模式改为按库根 `AGENTS.md` + `.wiki-schema.md` 执行；保留 `instances.json`、`engine`、`python`、库识别、lint/graph/log/report。
- `skill/wiki/references/schema.md`：改为 schema 参考入口；只保留权威正本、运行信息和流程索引。
- `wiki-design/rfcs/README.md`：RFC 模板新增 `## 真实摩擦来源` 和 `## 验证方式`，含非机制类“不适用”写法。
- `wiki-design/04-agent-rules.md`：新增“新机制 RFC 准入 Gate”节，限定机制类适用范围和豁免口径。

验证输出：

```text
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root knowledge --check-docs; echo "check-docs exit=$?"
受管块: 6
错误: 0
check-docs exit=0
```

```text
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root knowledge --check-only; echo "lint exit=$?"
派生层未重建（--check-only）
错误: 0 · 警告: 0
lint exit=0
```

```text
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest tests.test_task_012 tests.test_task_013 tests.test_task_014 tests.test_task_015 tests.test_task_016a tests.test_task_016b tests.test_task_017 tests.test_task_019 tests.test_task_020a
Ran 56 tests in 10.912s
OK
```

人工审计抽查：

```text
rg '^### 顶层格式|^### 字段约束|^[|] 字段 [|]|type: source \\||status: draft \\||confidence: low|source \\| `wiki/sources|schema 速查|^## 标准 frontmatter|^## 各类页面模板|^## inbox capture item' wiki-design/05-contracts-and-next-steps.md skill/wiki/SKILL.md skill/wiki/references/schema.md
无命中
```

```text
rg 'instances|engine|python|scripts/wiki_lint.py|scripts/wiki_graph.py|--ingest-status|\\.wiki-schema|AGENTS.md' skill/wiki/SKILL.md skill/wiki/references/schema.md
确认 skill 保留 instances/engine/python、库识别、lint、graph、--ingest-status、AGENTS.md 与 .wiki-schema.md 指针。
```

偏离或异常：无。未修改 `knowledge/.wiki-schema.md`、scripts 行为、core schema、`schema_version` 或任何实例数据。

Commit：本提交（sha 见最终报告）。

## Evaluation by claude · <date>

（评估者填写）
