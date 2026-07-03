---
id: task_20260703_048
title: knowledge-pk ODS binding 回填（336 DI）+ 分层抽查 gate + 批量背书
author: claude
executor: codex
status: pending
type: other
created: 2026-07-03
updated: 2026-07-03
related_rfcs: [RFC-030]
---

# TASK-048: knowledge-pk ODS binding 回填 + 抽查 gate

## 目标

用 TASK-047 的解析器把 336 个 DI ODS 任务的源表 binding 回填进 knowledge-pk 索引与 source 页，产出**分层抽查包**交 maintainer 核对；抽查通过后按 RFC-030 §3 批量背书 parsed 页。PYODPS3 638 项标 `inferred` 不解析。

## 前置条件

- **TASK-047 done**（解析器 + binding diff 在）。
- knowledge-pk working tree clean；DataWorks 凭证在 env。

## 强约束

1. **回填范围**：974 个 ODS item——DI 336 走解析（按结果落 `parsed` / `ambiguous` / `unparsed`），PYODPS3 638 统一 `source_binding: inferred`。索引守受管基线（`index_version=2` / 1353 items / 无代码正文）。
2. **source 页正文**：`parsed` 页补一行「线上源表（解析自同步任务配置）：`<datasource>.<tables>`」；`ambiguous` 页写明 warning 原因；`inferred` 页补「按命名推断，未经核实」标注（RFC-030 §4 答疑口径落地）。
3. **confidence 联动**（扩展 TASK-045 规则，写入 pk `AGENTS.md`）：`parsed` 的 ODS source 页 `low → medium`；`ambiguous` / `unparsed` / `inferred` 保持 `low`。
4. **抽查 gate（硬停点）**：回填完成后产出分层抽查包——按 reader stepType 分层（mysql / mongodb 各 ≥8，sqlserver 仅 1 个必含），按 `source_datasource` 去重；每样本含 `file_id` / `node_name` / stepType / `source_datasource` / `source_tables` / DataWorks 控制台核对入口。**产出后停下等 maintainer 核对**，不得先行背书。
5. **批量背书（gate 通过后）**：maintainer 确认抽查通过 → 对「`parsed` 且指纹当前」页批量 `review: true`，背书依据（样本量 / 日期 / 解析器 commit / 索引 snapshot）记入 `log.md` 与 review_queue 决议。`ambiguous` / `unparsed` / `inferred` **一律不背书**。maintainer 未确认前，L3 红线全程有效。
6. 每阶段（索引回填 / source 页正文 / AGENTS.md / 批量背书）单独 commit；lint / graph / eval 全过。

## 步骤

1. 用 TASK-047 解析器批量处理 336 个 DI（`GetFile` → parse），回填索引四字段；PYODPS3 标 inferred。报四态分布。
2. source 页正文按约束 2 批量补行；confidence 按约束 3 联动；AGENTS.md 规则扩展。
3. 产出分层抽查包（约束 4），追加到本 task Execution log，**停下等 maintainer**。
4. maintainer 核对通过 → 批量背书（约束 5）；未通过 → 记录问题、修解析器另开 task，不背书。
5. lint / graph / eval；`log.md` 收尾。

## 验证

```bash
PK=/Users/zhangjunwu/workspace/obsidian/knowledge-pk
python3 -c "import json,collections;d=json.load(open('$PK/.wiki/dataworks_index.json'));print('binding:',dict(collections.Counter(i.get('source_binding','缺省') for i in d['items'])));print('version',d['index_version'],'items',len(d['items']))"
grep -rl "解析自同步任务配置" $PK/wiki/sources --include='*.md' | wc -l    # ≈ parsed 数
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root $PK --check-only; echo lint=$?
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_eval.py --root $PK --json | python3 -c "import sys,json;d=json.load(sys.stdin);print('score',d['score'],'endorsement',d['dims']['endorsement'])"
```

## 完成后报告格式

- 四态分布（parsed / ambiguous / unparsed / inferred 各多少）+ 索引基线确认
- source 页正文改动数、confidence 变化数、AGENTS.md 规则段
- 分层抽查包（样本清单）+ maintainer 核对记录
- 批量背书数（或未背书原因）、review_queue 决议
- lint / graph / eval、per-阶段 commit sha、偏离或异常

## Execution log by codex · <date>

## Evaluation by claude · <date>
