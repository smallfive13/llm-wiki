---
id: task_20260604_016c
title: Apply RFC-016 数据对齐 — datawarehouse 已 ingest 产物对齐最终规范
author: claude
executor: codex
status: done
type: apply
created: 2026-06-04
updated: 2026-06-04
related_rfcs: [RFC-016]
---

# TASK-016c: datawarehouse 数据对齐

## 目标

把 datawarehouse 06-04 已 ingest 的产物对齐 RFC-016 最终规范：补 `visibility`、清理旧集合 source、确认图引用过 016b lint、核对图的多模态描述。**纯数据动作**（外部实例迁移），在数据仓单独提交，不混引擎 apply。

## 前置条件

- TASK-016a + TASK-016b done（visibility/脱敏/图校验规则已落地）。
- datawarehouse 数据仓 working tree clean（先确认 06-04 那批产物已提交；若未提交，先让用户/执行者提交基线）。

## 强约束

1. **纯数据动作**：只改 datawarehouse 实例数据（wiki 页 / source_manifest / capture_policy），不改引擎 scripts。
2. **append/迁移要可追溯**：source 清理用 `supersedes`/`status: archived`，不硬删（保留审计）。
3. **在数据仓提交**，报告外部 git 状态，不进引擎仓。

## 步骤

> Step 0：先 `git -C <数据仓> status` 确认 06-04 产物已是干净基线（17 source + 75 图 + 13 知识页）。不干净先提交基线再开工。

1. **补 visibility**：
   - `capture_policy.default_visibility: internal`（016a 可能已做；确认）。
   - 各 source（source_manifest + source 页 frontmatter）+ 各 wiki 页：按需显式标 `visibility: internal`（或依赖库默认继承——二选一，记录策略；建议依赖默认、只在例外页显式标，避免冗余）。

2. **清理旧集合 source**（用户决策"清理"）：
   - 旧集合 `src_20260603_international-data-service-tech-docs`：标 `status: archived` + `superseded_by`（指向 17 个细粒度 source，或指向 synthesis 门户，择一记录）。
   - 把仍引用集合 source_id 的 ~18 页的 `source_ids` 改指对应**细粒度 source**（按主题对应）。
   - source_manifest 里旧集合条目 status 改 `superseded`（若 enum 不支持则 `archived` + 备注）。

3. **图引用过 016b lint**：跑 016b 的图引用校验,现有 75 张图的相对引用应全部解析（无 `IMAGE_DANGLING`）；若有断引（路径口径不符）→ 修引用路径使其符合 016b 校验。

4. **核对图描述**：抽查图的多模态描述（语义 + 关键文字）是否到位；缺的按需补（写入 AI 多模态）。OCR 全文不强求（原图保底）。

5. 跑校验 → 数据仓提交 → 报告。

## 验证

```bash
ENGINE=/Users/zhangjunwu/workspace/llm-wiki/llm-wiki
PY="/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python"
DW=/Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse

cd $ENGINE
$PY scripts/wiki_lint.py --root $DW          # exit 0，无 IMAGE_DANGLING、无旧集合悬挂引用
$PY scripts/wiki_graph.py --root $DW          # 0 dangling
$PY scripts/wiki_eval.py --root $DW --json    # score 合理（visibility 不影响 score）
# 确认旧集合 source 不再被任何页 source_ids 引用（除其自身 superseded 链）
grep -rl 'src_20260603_international-data-service-tech-docs' $DW/wiki | grep -v sources/international || echo "OK 无悬挂引用"
```

## 完成后报告格式

- Step 0 基线确认（06-04 产物 git 状态）
- visibility 策略（显式 vs 继承）+ 改了哪些
- 旧集合 source 清理：archived/superseded + 改了哪些页的 source_ids
- 图引用 lint 结果（IMAGE_DANGLING 数）+ 图描述核对
- 数据仓 commit sha + 外部 git 状态
- 偏离或异常

## Execution log by codex · 2026-06-04

- Step 0 基线确认：`git -C /Users/zhangjunwu/workspace/obsidian/knowledge status --short` 输出为空；数据仓 HEAD 为 `129c612c113e2e41ba1b82192f547e0a3fe31b66`，确认 06-04 ingest 基线和 016a 迁移已提交。
- visibility 策略：依赖库默认继承，不在每个页面显式冗余标注。`datawarehouse/.wiki/capture_policy.json` 已由 016a 设为 `default_visibility: internal`；本 task 未改 capture_policy，也未新增页面级 `visibility`。
- 旧集合 source 清理：
  - `wiki/sources/international-data-service-tech-docs.md`：`status: active -> archived`，`superseded_by: [syn_20260603_international-data-service-tech-knowledge]`，正文追加归档说明，说明 2026-06-04 已拆分为 17 个细粒度 source，由 synthesis 门户聚合，保留审计但不再作为新页面 `source_ids` 引用。
  - `wiki/synthesis/international-data-service-tech-knowledge.md`：`supersedes: [src_20260603_international-data-service-tech-docs]`，形成 supersedes 对称链。
  - 17 个细粒度 source 页：从 `related_ids` 和显示层 `related` 移除旧集合 source 引用；其中 `source-aliyun-data-analysis.md` 与 `source-idn-cloud-sensitive-query.md` 移除后改为 `related_ids: []` / `related: []`，避免 YAML 空键。
  - `raw/source_manifest.json`：旧集合 source 条目 `status: ingested -> deleted`，notes 写明该 source 是历史集合、已由 17 个细粒度 source + synthesis 门户替代。偏离说明：当前 engine 的 `source_manifest.status` enum 不支持 `superseded` 或 `archived`，为保持 lint exit 0，使用支持的 `deleted` 表示不再作为活跃 ingest source 使用，并在 notes 保留审计语义。
  - 结构化 frontmatter 校验：旧集合 ID 在 `source_ids` 中出现次数为 0；旧集合 ID 只保留在旧集合页自身和 synthesis `supersedes` 链里。
- 图引用 lint 结果 + 图描述核对：
  - `wiki_lint.py --root datawarehouse`：错误 0、警告 0，无 `IMAGE_DANGLING`。
  - datawarehouse 75 张图引用解析通过。
  - 图片描述覆盖：9 个含图 source 页的图片数和 `关键词：` 紧邻描述行数一致：`aliyun-practice-pitfalls 9/9`、`dataworks-smart-baseline 8/8`、`dw-common-qa 19/19`、`insert-overwrite 5/5`、`jingwei-region-time-setting 3/3`、`quickbi-dynamic-dim-metric 17/17`、`quickbi-pitfalls 5/5`、`sql-best-practices 5/5`、`sync-online-table-mapping 4/4`。

验证输出：

```text
$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse; echo "lint exit=$?"
wiki-lint instance root: /Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse · profile: base

wiki-lint v0.1.0
================
实例: /Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse · profile: base
扫描: datawarehouse/wiki/ (30 文件) · datawarehouse/inbox/ (0 draft) · datawarehouse/raw/ (18 source)

[OK]    schema 校验: 30 页扫描
[OK]    ID 唯一性: 30 个 id
[OK]    canonical 引用 + supersedes 对称
[OK]    source 单主键
[OK]    entity 别名（含链式跳转 / status:redirect）: 0 entries
[OK]    inbox: 0 draft
[OK]    脱敏扫描（inbox-only）: 0 命中

派生层已重建（原子写入）:
  .wiki/id_index.json (30 entries)
  .wiki/normalized_alias_index.json (0 entries)
  .wiki/inbox_index.json (0 drafts)

错误: 0 · 警告: 0

lint exit=0
```

```text
$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_graph.py --root /Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse; echo "graph exit=$?"
wiki-graph instance root: /Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse · profile: base

wiki-graph: 30 nodes, 177 edges, 2 communities

graph exit=0

$ rg -n "Dangling Wikilinks|Ambiguous Wikilinks|- \\(none\\)" /Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse/maps/graph-insights.md
## Dangling Wikilinks
- (none)
## Ambiguous Wikilinks
- (none)
```

```text
$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_eval.py --root /Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse --json; echo "eval exit=$?"
{
  "dims": {
    "connectivity": 100,
    "endorsement": 100,
    "freshness": 100,
    "integrity": 100
  },
  "pages": 30,
  "score": 100,
  "status": "ok",
  "ts": "2026-06-04T16:25:39+08:00",
  "weakest_dim": "integrity"
}

eval exit=0
```

```text
$ python3 - <<'PY'
... structured frontmatter check ...
old source_id in source_ids count: 0
old id frontmatter reference files: 2
('wiki/sources/international-data-service-tech-docs.md', 'src_20260603_international-data-service-tech-docs', 'source', 'archived')
('wiki/synthesis/international-data-service-tech-knowledge.md', 'syn_20260603_international-data-service-tech-knowledge', 'synthesis', 'active')
image description coverage:
source-aliyun-practice-pitfalls.md: images=9, keyword_lines=9
source-dataworks-smart-baseline.md: images=8, keyword_lines=8
source-dw-common-qa.md: images=19, keyword_lines=19
source-insert-overwrite.md: images=5, keyword_lines=5
source-jingwei-region-time-setting.md: images=3, keyword_lines=3
source-quickbi-dynamic-dim-metric.md: images=17, keyword_lines=17
source-quickbi-pitfalls.md: images=5, keyword_lines=5
source-sql-best-practices.md: images=5, keyword_lines=5
source-sync-online-table-mapping.md: images=4, keyword_lines=4
```

- 数据仓 commit sha：`64c9f5d9b109c45f333d04817ab3e35f0a0a1fa2`
- 外部 git 状态：提交后 `git -C /Users/zhangjunwu/workspace/obsidian/knowledge status --short` 输出为空。
- 偏离或异常：
  - task 给出的简单 grep 会把 synthesis 门户的有意 `supersedes` 链也输出，因此不能作为“无悬挂 source_ids”的唯一判断；本次使用结构化 frontmatter 校验确认旧集合 ID 不再出现在任何页面的 `source_ids`。
  - 首轮 lint 发现两个移除旧集合引用后的 source 页出现 `related_ids:` 空键，已改为 `related_ids: []` / `related: []` 后重跑通过。

## Evaluation by claude · 2026-06-04

**Verdict: PASS。** 独立复跑全部验证；旧集合清理、visibility 继承、图描述覆盖、数据仓边界均达标。

### 独立复跑

| 验证 | 结果 |
| --- | --- |
| dw lint `--check-only` | 0 error / 0 warning（含 supersedes 对称校验通过） |
| dw graph | 30 节点 / 177 边 / 0 dangling / 0 ambiguous |
| dw eval | score 100（archived 旧集合不计 endorsement） |
| 旧集合 source_id 在 `source_ids` 引用 | **0**（结构化校验，只留 archived 页自身 + synthesis supersedes 链） |
| 数据仓改动范围 | 20 文件全在 datawarehouse；提交后 clean |

### 核查点

1. **旧集合 source 清理（用户决策）**：`src_20260603` → `archived` + `superseded_by: synthesis`，synthesis `supersedes` 对称链（lint exit 0 证明对称）；17 细粒度 source 移除旧集合 related；source_ids 悬挂 0。
2. **visibility 继承策略**：依赖库 `default_visibility: internal`、不逐页冗余写——符合 RFC-016 M1「缺失继承」设计，避免 30 页冗余。
3. **图描述覆盖**：9 个含图 source 页的图片数 = 描述行数（如 dw-common-qa 19/19、quickbi-dynamic 17/17），75 图 0 dangling。
4. **数据仓边界**：只改 datawarehouse 数据，不混引擎；数据仓单独 commit `64c9f5d`。

### 偏离评估（合理，记一个小 backlog）

- **source_manifest enum 缺 `superseded`/`archived`**：执行者用 `status: deleted` + notes 表"旧集合不再活跃"（enum 不支持更精确的 superseded）。这是合理 workaround，但暴露一个 schema 小 gap——`source_manifest.status` 没有 page 那样的 archived/superseded 语义。**建议进 backlog**（小：给 source_manifest.status 加 `superseded`/`archived`），不阻断本 task。
- grep 不精确 → 改结构化校验；related_ids 空键 → `[]`。均合理修正。

### 结论

**RFC-016（ingest v2）三部曲全部闭环**：M1 visibility + M2 脱敏分级（016a）→ M3 富媒体规则（016b）→ datawarehouse 数据对齐（016c）。数仓库现在 = 内部不过度脱敏 + 75 图带描述可检索 + source 细粒度可溯源 + 旧集合清理 + eval 100。TASK-016c done 确认有效。
