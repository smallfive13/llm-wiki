---
id: task_20260622_028
title: Apply RFC-027 M1+M2 — asset-mapping profile + 代码梳理/传导口径方法论
author: claude
executor: codex
status: done
type: apply
created: 2026-06-22
updated: 2026-06-22
related_rfcs: [RFC-027]
---

# TASK-028: Apply RFC-027 M1+M2

## 目标

把 RFC-027 已 accepted 的 M1+M2 落地：knowledge-pk 新增 `asset-mapping` 结构化页型（业务概念 ↔ 物理表字段）+ 代码梳理 7 维方法论 + 传导口径约定。**零外部接口依赖**（不碰 fun-cli / 数据地图）。M3+M4（失效检测/回源）是 deferred，本 task 不做。

## 前置条件

- RFC-027 status: accepted（Decision by claude 2026-06-22，M1+M2 范围）。
- 引擎 working tree clean（除本 task）。
- 环境：`/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python`（完整命令，不塞 shell 变量）。

## 强约束

1. **asset-mapping profile（钉死，写 `knowledge-pk/.wiki-profile.json`，RFC-008 overlay，只增不改 base）**：
   - `type=asset-mapping`；`id_prefix=asm`；`dir=wiki/asset-mappings`。
   - required（base 之外）：`business_concept`、`physical_table`。
   - optional：`physical_field`、`business_aliases`。
   - **不加** `lineage_upstream`（血缘只用 `related_ids`，方向 当前页→上游）；**不加**代码锚点字段（`dataworks_ref`/`code_fingerprint`/`last_synced` 属 M3 deferred）。
2. **value_mapping / caveats / 血缘说明 → 正文**，不进 frontmatter（frontmatter 只放轻量可检索字段）。
3. **引擎 `scripts/wiki_common.py` 不改**；引擎改动仅 `wiki-design/02-workflows.md`（+ `scripts/README.md` 若确需）。**不 bump schema_version**。
4. **血缘权威性**：人工 `related_ids` 是血缘正本；方法论文档须写明 fun-cli / 数据地图自动血缘"不一定准"，仅作 ingest 人工参考，不自动写库。
5. 示例页用 **draft 占位**（`status: draft` + `confidence: low`）：物理表/字段/枚举为示意，注明"待 ingest 真实 DataWorks 代码补全"——本 task 不依赖真实代码数据（fun-cli 未登录）。
6. doc-consistency 不破（`wiki_lint --check-docs` 通过）。

## 步骤

> **Step 0 spec-review**：核对 `knowledge-pk/.wiki-profile.json` 现状 + RFC-008 profile overlay 支持的字段（`extra_page_types` / required / optional / `id_prefix` / `dir`）；确认 `asset-mapping` 加法合法、`asm` 前缀不撞 base、`wiki/asset-mappings` 目录约定一致。核对 `02-workflows.md` 现有结构找方法论落点（团队贡献节附近）。歧义先提。

1. **`knowledge-pk/.wiki-profile.json`**：加 `asset-mapping` 页型（强约束 1）。
2. **`wiki-design/02-workflows.md`**：新增「代码 → 口径知识」节——
   - 代码梳理 7 维：口径与定义 / 血缘数据流 / 关键逻辑（说明非代码）/ 设计决策（为什么）/ 调度运行特性 / 踩坑 / 适用边界；反面：不贴整段代码、不逐行翻译、不沉淀一次性查询。
   - 传导口径：定义点唯一 / 下游记增量 / `related_ids` 血缘链（当前页→上游）/ source-gap 占位（RFC-018）/ 同名不同口径 → `open-question`｜`decision`。
   - 血缘权威性（强约束 4）。
   - `asset-mapping` 页型用途（业务概念↔表字段，支撑业务词检索）。
3. **`knowledge-pk/AGENTS.md`**：节 5 profile 演进处或新增小节，引用 02 的「代码→口径知识」+ asset-mapping 写法 + 血缘权威性（pk 特定：DataWorks 代码梳理）。
4. **示例页** `knowledge-pk/wiki/asset-mappings/<slug>.md`（draft 占位，强约束 5）：合法 asset-mapping frontmatter + 正文骨架（物理落点 / 取值映射表格 / 血缘上游 / 坑·适用边界 / 来源）。
5. 校验投影（pk 实例）：`wiki_lint --root <pk>` exit 0；`wiki_graph --root <pk>` 0 dangling；`wiki_eval --root <pk> --json`。
6. doc-consistency：`wiki_lint --check-docs`（引擎）通过。
7. 提交：引擎一个 commit（02 + README 若改）；knowledge-pk 实例单独 commit（profile + AGENTS + 示例页）。push GitLab。

## 验证

```bash
cd /Users/zhangjunwu/workspace/llm-wiki/llm-wiki
PK=/Users/zhangjunwu/workspace/obsidian/knowledge-pk
# profile 生效 + 示例页过校验
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root "$PK"; echo "pk_lint=$?"   # exit 0
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_graph.py --root "$PK"
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_eval.py --root "$PK" --json | head -20
# 业务词检索命中示例 asset-mapping 页（rg 在 pk 库，验 business_concept/aliases 可被检索）
rg -l "收款渠道|business_concept" "$PK/wiki/asset-mappings" || true
# doc-consistency
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --check-docs; echo "docs=$?"
# 引擎离线回归（无 fun-cli 依赖）
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest discover -s tests 2>&1 | tail -2
```

## 完成后报告格式

- Step 0 结论（.wiki-profile.json 落点、02 方法论落点、asm 前缀/目录确认）
- 改动文件 + 关键位置（profile 页型、02 新节、AGENTS、示例页）
- 验证输出（pk lint/graph/eval、检索命中、--check-docs、回归、引擎 + pk commit sha + push）
- 偏离或异常

## Execution log by codex · 2026-06-22

### Step 0 结论

- `knowledge-pk` 原本没有 `.wiki-profile.json`，可以按 RFC-008 通过 `extra_page_types` 增量增加页型。
- base schema 当前前缀为 `cmp/dec/ent/oq/que/src/syn/top`，inbox 为 `inb`；`asm` 不冲突。`wiki/asset-mappings` 也不冲突现有 base 目录。
- `asset-mapping` 的 required/optional 字段均为新增 profile 字段：`business_concept`、`physical_table`、`physical_field`、`business_aliases`，不触碰 core frontmatter。
- `wiki-design/02-workflows.md` 的团队贡献 / dropbox ingest 段之后是合适落点，可承接代码 ingest 方法论并和后续 capture 流程分开。
- 不需要改 `scripts/wiki_common.py`，不 bump `schema_version`，不接 fun-cli / 数据地图接口。

### 改动文件

引擎仓：

- `wiki-design/02-workflows.md`：新增「代码 → 口径知识」节，覆盖 7 维梳理、反面约束、`asset-mapping` 用途、口径传导和血缘权威性。

knowledge-pk 仓：

- `.wiki-profile.json`：新增 `asset-mapping` profile，`id_prefix=asm`，目录 `wiki/asset-mappings`。
- `wiki/asset-mappings/payment-channel.md`：新增 draft/low 示例占位页，物理表、字段和枚举均标明待真实 DataWorks 代码 ingest 后补。
- `AGENTS.md`：补充 `asset-mapping` 写法、代码 ingest 定位、血缘权威性和当前 dropbox 黑名单扫描口径。
- `log.md`：按本库 AGENTS 记录本次 profile / 示例页更新与验证结果。

### 验证输出

```text
$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk --check-only
wiki-lint instance root: /Users/zhangjunwu/workspace/obsidian/knowledge-pk · profile: knowledge-pk
扫描: knowledge-pk/wiki/ (1 文件) · knowledge-pk/inbox/ (0 draft) · knowledge-pk/raw/ (0 source)
错误: 0 · 警告: 0
pk_lint_exit=0

$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_graph.py --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk
wiki-graph: 1 nodes, 0 edges, 1 communities
pk_graph_exit=0

$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_eval.py --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk --json
{
  "dims": {
    "connectivity": 0,
    "endorsement": 100,
    "freshness": 100,
    "integrity": 100
  },
  "pages": 1,
  "review_coverage": {
    "eligible": 0,
    "percent": 100,
    "reviewed": 0,
    "unreviewed": []
  },
  "score": 80,
  "status": "ok",
  "weakest_dim": "connectivity"
}
pk_eval_exit=0

$ rg -n "收款渠道|business_concept|asset-mapping" /Users/zhangjunwu/workspace/obsidian/knowledge-pk/wiki/asset-mappings /Users/zhangjunwu/workspace/obsidian/knowledge-pk/.wiki-profile.json
/Users/zhangjunwu/workspace/obsidian/knowledge-pk/.wiki-profile.json:7:      "type": "asset-mapping",
/Users/zhangjunwu/workspace/obsidian/knowledge-pk/.wiki-profile.json:12:        "business_concept",
/Users/zhangjunwu/workspace/obsidian/knowledge-pk/wiki/asset-mappings/payment-channel.md:3:type: asset-mapping
/Users/zhangjunwu/workspace/obsidian/knowledge-pk/wiki/asset-mappings/payment-channel.md:17:business_concept: 收款渠道
/Users/zhangjunwu/workspace/obsidian/knowledge-pk/wiki/asset-mappings/payment-channel.md:24:# 收款渠道字段映射（示例占位）
pk_rg_exit=0

$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --check-docs
受管块: 6
错误: 0
check_docs_exit=0

$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest discover -s tests 2>&1 | tail -2
OK
tests_tail_exit=0
```

### Commit / push

- knowledge-pk commit: `8e1edcfd5e804273a39cfbe039d3c9aaab56d482`，已 push 到 `http://git.ppdaicorp.com/international_data/knowledge-pk.git main`。
- 引擎 commit: 本提交，最终 SHA 见执行回报；将 push 到 `http://git.ppdaicorp.com/international_data/llm-wiki.git main`。

### 偏离或异常

- 无 fun-cli / 数据地图调用。
- 未修改 `scripts/wiki_common.py`，未 bump `schema_version`。
- 额外更新 `knowledge-pk/log.md` 是按该实例 `AGENTS.md` 的本地记录要求执行。

## Evaluation by claude · <date>

（评估者填写）
