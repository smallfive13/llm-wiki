---
id: task_20260604_018
title: Apply RFC-018 — ingest 子链接处理约定（流程文档，不改 scripts）
author: claude
executor: codex
status: done
type: apply
created: 2026-06-04
updated: 2026-06-04
related_rfcs: [RFC-018]
---

# TASK-018: Apply RFC-018 — ingest 子链接处理约定

## 目标

把 RFC-018 的 ingest 子链接处理（关联保留 + source-gap open-question 登记 + 不递归）写进规范文档。**纯约定/流程文档，不改 scripts**。datawarehouse 现状已符合，仅确认对齐。

## 前置条件

- RFC-018 status: accepted（Decision by claude 2026-06-04）。
- working tree clean（除本 task）。

## 强约束

1. **不改 scripts**（lint/graph/eval/init）：source-gap 就是 open-question，现有校验够；本 task 是规范文档。
2. 不改 core schema、page 类型、ID/canonical 规则。
3. datawarehouse **仅确认对齐、不重做**；若有数据微调（补正文骨架/命名）在数据仓单独提交。

## 步骤

> Step 0 spec-review：确认 02-workflows / 04-agent-rules / .wiki-schema 的 ingest 段落落点；发现歧义先提。

1. **`wiki-design/02-workflows.md`**：ingest 流程（triage/apply）补"子链接处理"子步骤：
   - 链接分类（内部文档 / 外部）；
   - 关联保留（脱 token 留"链向 X" + `related_ids`/`related` 关联子 source，子 source 未抓正文时 `draft`/`low` 占位）；
   - source-gap 登记（**触发条件**：与当前 source 相关且目标未抓到/未 ingest 才建；导航/页脚/工单弱相关链接不做）→ open-question `oq_YYYYMMDD_<slug>-source-gap`，正文「已知信息 + 待确认」；
   - 不递归（补抓=独立 ingest）；外链只脱敏说明不建 source。

2. **`wiki-design/04-agent-rules.md`**：Agent ingest 行为补子链接约定（同上要点，精炼）。

3. **`knowledge/.wiki-schema.md`（源头）**：补 ingest 子链接约定 + source-gap open-question 模式 + 与 `review_queue.type: source_gap` 的分工（临时队列→长期待办晋升）。

4. **衍生同步**：skill `references/schema.md`（ingest 段补子链接）+ datawarehouse 库根 `AGENTS.md`（补子链接约定）。引擎 `.wiki-schema.md` 改后用 `--sync-schema` 同步 personal/datawarehouse（参 RFC-017 evaluation 的"改源头 schema → --sync"约定）。

5. **datawarehouse 确认对齐**（数据仓，若需微调单独提交）：`oq_20260604_aliyun-data-analysis-source-gap` 等已符合规范 → 跑 lint 确认 0/0；正文骨架/命名若与新规范有出入则微调。

6. 跑验证 → commit（引擎文档一个 commit；衍生/数据仓同步单独）。

## 验证

```bash
ENGINE=/Users/zhangjunwu/workspace/llm-wiki/llm-wiki
PY="/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python"
DW=/Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse

# 1) 文档落地确认（子链接/source-gap 出现在三处）
grep -lE '子链接|source-gap|source gap' wiki-design/02-workflows.md wiki-design/04-agent-rules.md knowledge/.wiki-schema.md
# 2) 不改 scripts：git diff 仅文档 + 测试不回归
cd $ENGINE && $PY -m unittest tests.test_task_012 tests.test_task_013 tests.test_task_014 tests.test_task_015 tests.test_task_016a tests.test_task_016b tests.test_task_017
# 3) datawarehouse 对齐后 lint
$PY scripts/wiki_lint.py --root $DW --check-only; echo "dw exit=$?"
```

## 完成后报告格式

- Step 0 spec-review 结论
- 改动文件（确认仅文档 + 衍生，无 scripts）
- 验证输出（三处 grep、回归、dw lint）
- `--sync-schema` 结果 + 数据仓 commit sha（若有微调）
- commit sha（引擎/衍生/数据仓分开）
- 偏离或异常

## Execution log by codex · 2026-06-04

- Step 0 spec-review 结论：
  - `wiki-design/02-workflows.md` 的落点是"摄入资料"两步流程中的 Triage 子步骤，子链接处理应与来源摘要、富媒体处理、alias matching 并列。
  - `wiki-design/04-agent-rules.md` 的落点是"内容规则"之后、"审核规则"之前，作为 Agent ingest 行为约定。
  - `knowledge/.wiki-schema.md` 的落点是 JSON 契约之后、富媒体引用之前，补充 ingest 写入职责、source-gap open-question 模式，以及 `review_queue.type: source_gap` 与长期 open-question 的分工。
  - 未发现需先向用户确认的歧义；本 task 保持纯约定 / 流程文档，不改 scripts。

- 改动文件：
  - 引擎正本：`wiki-design/02-workflows.md`、`wiki-design/04-agent-rules.md`、`knowledge/.wiki-schema.md`。
  - 衍生同步：`skill/wiki/references/schema.md`、`/Users/zhangjunwu/workspace/obsidian/knowledge/personal/.wiki-schema.md`、`/Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse/.wiki-schema.md`、`/Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse/AGENTS.md`。
  - 状态记录：`wiki-design/tasks/TASK-018-apply-rfc-018.md`、`wiki-design/tasks/README.md`，以及提交后回填 `wiki-design/rfcs/RFC-018-ingest-sublink-handling.md`。
  - 确认未修改 `scripts/`。

- `--sync-schema` 结果：

```text
personal:
old_sha256: 5b5438835cc5109026492fc87521a52d76f340c7c55e62d837e5b8f0d20fe79c
new_sha256: 72fa784381b745ae4aba192bab0c3d109d5f3a4e1a96d708389bff4010e4e46d
action: replaced
personal-sync exit=0

datawarehouse:
old_sha256: 5b5438835cc5109026492fc87521a52d76f340c7c55e62d837e5b8f0d20fe79c
new_sha256: 72fa784381b745ae4aba192bab0c3d109d5f3a4e1a96d708389bff4010e4e46d
action: replaced
dw-sync exit=0
```

- 验证输出：

```text
$ grep -lE '子链接|source-gap|source gap' wiki-design/02-workflows.md wiki-design/04-agent-rules.md knowledge/.wiki-schema.md skill/wiki/references/schema.md
wiki-design/02-workflows.md
wiki-design/04-agent-rules.md
knowledge/.wiki-schema.md
skill/wiki/references/schema.md

$ git diff --name-only | rg '^scripts/' || true
<no output>

$ conda run -n py312 python -m unittest tests.test_task_012 tests.test_task_013 tests.test_task_014 tests.test_task_015 tests.test_task_016a tests.test_task_016b tests.test_task_017
Ran 41 tests in 6.439s
OK

$ conda run -n py312 python scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse --check-only
错误: 0 · 警告: 0
dw exit=0

$ conda run -n py312 python scripts/wiki_graph.py --root /Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse
wiki-graph: 32 nodes, 205 edges, 2 communities

$ conda run -n py312 python scripts/wiki_eval.py --root /Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse --json
score: 100, status: ok, pages: 32
```

- datawarehouse 对齐确认：
  - `oq_20260604_aliyun-data-analysis-source-gap` 已存在，含 `## 已知信息` / `## 待确认`。
  - 父 source `src_20260604_dw-common-qa` 通过 `related_ids` 指向子 source `src_20260604_aliyun-data-analysis`。
  - 子 source `src_20260604_aliyun-data-analysis` 为 `status: draft` + `confidence: low`，并关联 source-gap。
  - 本 task 未重做 datawarehouse 既有内容。

- commit sha：
  - 外部 schema/AGENTS 同步 commit：`df074d42808dd72dfd261273496d5ecf8a04454e`。
  - 引擎 apply commit：本 Execution log 与实现同轮提交，最终 SHA 在提交完成后确定。
  - RFC Applied 闭环 commit：提交后单独追加。

- 偏离或异常：
  - datawarehouse 仓库执行前已有多处知识页 / manifest 未提交改动；本 task 只新增并提交 `datawarehouse/.wiki-schema.md`、`datawarehouse/AGENTS.md` 和 `personal/.wiki-schema.md`，不回退、不 stage、不提交既有 datawarehouse 内容。
  - 首次尝试用 shell 管道解析 `wiki_eval --json` 输出时，内联 Python 引号导致 JSONDecodeError；已改用直接输出检查，`score: 100` / `status: ok` / `pages: 32`。

## Evaluation by claude · <date>

（评估者填写）
