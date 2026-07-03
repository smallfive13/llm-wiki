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

## Execution log by codex · 2026-07-03

### Scope

- 已执行 Step 1~3，停在抽查 gate。
- 未执行 Step 4 批量背书；未新增任何 `review: true`。
- pk 阶段提交：`ec12df747226d77bf139e81fbe313bb4a546768c` (`[pk task-048] backfill ODS source bindings`)。

### Step 1 · Index backfill

索引基线：

- `index_version`: 2
- `items`: 1353
- 代码正文：未写入索引

ODS binding 分布：

- `parsed`: 330
- `ambiguous`: 6
- `unparsed`: 0
- `inferred`: 638
- 合计 ODS item: 974

补充说明：

- 6 个 `ambiguous` 均为 DI reader connection list 存在多个 datasource 值，宁可 ambiguous，不硬解析。
- `parsed` reader 类型分布：mysql 247、mongodb 82、sqlserver 1。
- 非 ODS item 未补 binding 字段，验证计数中显示为缺省 379。

### Step 2 · Source pages + AGENTS

- 匹配并更新 ODS source 页：974。
- 正文新增 binding 说明：974。
- `confidence: low -> medium`: 330（仅 parsed ODS source 页）。
- `ambiguous` / `inferred`: 保持 `confidence: low`。
- `review` 字段：未变更。
- `AGENTS.md` 已补充 ODS source binding 与背书分工：`parsed` 只代表机器解析事实，可升 `medium`；`review: true` 仍必须 maintainer 人工确认。

### Step 3 · Stratified sample pack

抽查包落点：

- `/Users/zhangjunwu/workspace/obsidian/knowledge-pk/.wiki/ods_binding_review_samples.json`

抽查包规模：

- `sample_count`: 17
- mysql: 8
- mongodb: 8
- sqlserver: 1

样本清单：

| stepType | file_id | node_name | source_datasource | source_tables |
| --- | --- | --- | --- | --- |
| mysql | 500410074 | `ods.app_server_em_flow_deployment.extract` | `app_server` | `em_flow_deployment` |
| mysql | 500339321 | `ods.audit_center_audit_config_step.extract` | `audit_center` | `audit_config_step` |
| mysql | 500464581 | `ods.information_schema_columns.extract` | `information_schema` | `columns` |
| mysql | 500339196 | `ods.loan_biz_credit_apply_case.extract` | `loan_biz` | `credit_apply_case` |
| mysql | 500480785 | `ods.pak_backend_tb_market_element_config.extract` | `pak_backend` | `tb_market_element_config` |
| mysql | 500579159 | `ods.pak_backend_user_backend_user.extract` | `pak_backend_user` | `backend_user` |
| mysql | 500344219 | `ods.pak_capital_tb_acct_command.extract` | `pak_capital` | `tb_acct_command` |
| mysql | 500429576 | `ods.pak_capsule_box_abtest_group_result.extract` | `pak_capsule_box` | `abtest_group_result` |
| mongodb | 500484273 | `ods_s.loan_biz_autosync_2_loan_apply_contact_confirm_info.extract` | `loan_biz_autosync_2` | `loan_apply_contact_confirm_info` |
| mongodb | 500479224 | `ods.loan_biz_autosync_2_user_feedback.extract` | `loan_biz_autosync_3` | `user_feedback` |
| mongodb | 500579163 | `ods.pak_backend_autosync_2_audit_manual_snapshot.extract` | `pak_backend_autosync_2` | `audit_manual_snapshot` |
| mongodb | 500427691 | `ods.pak_ddp_execute_log_ddp_execute_log.extract` | `pak_ddp_execute_log_autosync_3` | `ddp_execute_log` |
| mongodb | 500344639 | `ods_pak_thirdparty_data_tasdeeq_f` | `pak_thirdparty_data` | `Tasdeeq` |
| mongodb | 500633492 | `ods.pak_thirdparty_data_autosync_1_abnormalphotocheck.extract` | `pak_thirdparty_data_autosync_1` | `abnormalPhotoCheck` |
| mongodb | 500415648 | `ods.pak_thirdparty_data_autosync_1_colossalscan.extract` | `pak_thirdparty_data_autosync_3` | `ColossalScan` |
| mongodb | 500619911 | `ods.pak_vendor_biz_autosync_2_merchant_apply_snapshot.extract` | `pak_vendor_biz_autosync_2` | `merchant_apply_snapshot` |
| sqlserver | 500602981 | `ods.pak_es_cdr_sip_record.extract` | `es_cdr_new` | `SIP_RECORD` |

硬停点：

- 等待 maintainer 核对上述样本。
- 核对通过前，不执行批量 `review:true`。

### Verification

```text
wiki-lint instance root: /Users/zhangjunwu/workspace/obsidian/knowledge-pk · profile: knowledge-pk

wiki-lint v0.1.0
================
实例: /Users/zhangjunwu/workspace/obsidian/knowledge-pk · profile: knowledge-pk
扫描: knowledge-pk/wiki/ (1431 文件) · knowledge-pk/inbox/ (0 draft) · knowledge-pk/raw/ (1354 source)

[OK]    schema 校验: 1431 页扫描
[OK]    ID 唯一性: 1431 个 id
[OK]    canonical 引用 + supersedes 对称
[OK]    source 单主键
[OK]    entity 别名（含链式跳转 / status:redirect）: 0 entries
[OK]    inbox: 0 draft
[OK]    脱敏扫描（inbox/archive）: 0 命中

ingest 进度
===========
状态计数：new 0 · triaged 0 · ingested 1354 · skipped 0 · failed 0 · deleted 0 · superseded 0 · archived 0
triaged 待 apply: 0

待 apply（按 manifest 顺序）：0

派生层未重建（--check-only）

错误: 0 · 警告: 0
```

Additional verification:

- `git diff --check`: pass
- graph: exit 0; nodes 1431; edges 2707; isolated 0
- eval: exit 0; score 82; endorsement 9
- `git diff -U0 -- wiki/sources | rg '^[-+]review:'`: no output

### Deviation / notes

- TASK title says "336 DI"; actual backfill outcome is 330 parsed + 6 ambiguous, matching the parser's safe behavior for multi-datasource DI configurations.
- Step 4 / Step 5 are intentionally not completed in this checkpoint because Step 3 is a hard maintainer gate.

## Maintainer decision · 2026-07-03

**抽查通过**（用户核对 17 样本含分歧行，claude 代记）。批量背书（Step 4）可执行，范围仍限「parsed 且指纹当前」330 页。

**背书语义精确化（用户同时指出）**：本次背书覆盖的是「ODS ← DataWorks 数据源（连接别名）+ 源表」这层 binding；`source_datasource` **是 DataWorks 数据源名，不是线上物理库名**。「数据源别名 → 线上库」的解析需调 DataWorks API（`ListDataSources`/`GetDataSource`），另走 **RFC-031**，不在本次背书范围。背书依据记档时须写明此边界；source 页措辞的精确化（避免把数据源名误读为线上库名）归 RFC-031 实例回填一并处理，避免 330 页二次批量改动。

## Evaluation by claude · <date>
