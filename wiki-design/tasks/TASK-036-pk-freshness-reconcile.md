---
id: task_20260702_036
title: knowledge-pk 增量防腐待复核 — B122/B032 回源比对 + 索引/页面裁决
author: claude
executor: codex
status: done
type: other
created: 2026-07-02
updated: 2026-07-02
related_rfcs: [RFC-028]
---

# TASK-036: knowledge-pk 增量防腐待复核

## 目标

对 `wiki_freshness --incremental-deployments` 报出的近期生产部署变更（复核实跑 dry-run 得 changed≈16 / affected≈27 / index_updates≈3，以 Step 0 为准）做人工级复核，重点 **B122 `file:96107/500610077`** 和 **B032 `file:96107/500581659`**：回源比对代码语义，决定每个变更文件是「纯指纹漂移」还是「口径影响漂移」，据此更新索引指纹 / last_synced，或把受影响口径页标 `stale` / 撤回 `review`，并把需人工背书项写入 review_queue。

## 前置条件

- TASK-035 done（`--incremental-deployments` 增量入口在）。
- DataWorks 凭证在环境变量（region `ap-southeast-1`，project 96107）。
- knowledge-pk 实例 working tree clean。
- 环境：`PY="/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python"`。

## 强约束

1. **两类 drift 分开裁决**，判据是**代码语义**而非指纹变没变：
   - **纯指纹漂移**（格式 / 注释 / 常量重排，业务口径不变）→ 只 `--apply` 更新该文件 index item 的 `code_fingerprint` + `last_synced`，**页面不动**。
   - **口径影响漂移**（JOIN / CASE / 过滤条件 / 枚举 / 主键粒度 / 去重变化）→ 受影响口径页 `status: stale` + `review: false`（若原为 true 必须撤回），并写 `review_queue` type `stale_claim`；对应 source 摘要页正文追加「回源发现 X 变化，待复核」。索引指纹同样更新。
2. **L3 人控红线**：Codex 只能标 `stale` + 入 review_queue，**严禁 auto `review: true`**、严禁改写口径结论为既定事实。最终背书是 maintainer。
3. **默认 dry-run**：先出完整报告（变更文件分类 + 受影响页逐页动作），写回须显式 `--apply`。
4. 凭证只从 env 读，不写入库 / 日志 / 回答；不保存代码正文。
5. 只动 knowledge-pk 实例，不动引擎工具逻辑、不 bump schema。索引写入仍守受管共享基线（`index_version=2`、1353 items、无 volatile、无代码 / 凭证）。

## 步骤

> **Step 0**：跑一次 dry-run 拿当前真实清单（部署量会漂移，以本次实跑为准）。**若 B122 `500610077` / B032 `500581659` 不在默认部署窗口内**：先调大 `--max-pages`；仍缺则直接 `GetFile file:96107/<fileId>` 与索引旧指纹比对，**不因窗口缺失跳过这两个重点文件**。`index_updates` 多于 2（复核时为 3）时，把第 3 个也一并列入裁决。

1. `$PY scripts/wiki_freshness.py --root <pk> --incremental-deployments --project-id 96107 --json` dry-run，导出全部 changed files / affected pages / index updates 清单。
2. 对每个 changed file（至少覆盖 B122 500610077、B032 500581659 两个 index-update 文件 + 其余变更文件）`GetFile` 取当前代码，与索引 `code_fingerprint` 对应的历史语义比对：历史语义从对应 source 摘要页正文 + `last_synced` 推断；无历史正文的判为「仅指纹差异，无法判口径」。
3. 每个文件归入三类：`纯指纹漂移` / `口径影响` / `需 maintainer 深核`（语义不明确的归第三类，不猜）。
4. `纯指纹漂移`：`--apply` 更新索引指纹 + last_synced。
5. `口径影响`：受影响页 `status: stale` + 撤 `review`，写 review_queue，source 页正文补待复核说明。
6. `需 maintainer 深核`：不改页面，只写 review_queue + 一个 open-question（`oq_YYYYMMDD_freshness-drift-<slug>`，含「已知信息 / 待确认」）。
7. 更新 knowledge-pk `log.md` 记本次裁决；lint / eval 过。

## 验证

```bash
PY="/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python"
PK=/Users/zhangjunwu/workspace/obsidian/knowledge-pk
$PY scripts/wiki_freshness.py --root $PK --incremental-deployments --project-id 96107 --check; echo check=$?
$PY scripts/wiki_lint.py --root $PK --check-only; echo lint=$?
$PY scripts/wiki_eval.py --root $PK --json | python3 -c "import sys,json;d=json.load(sys.stdin);print('score',d['score'],'endorsement',d['dims']['endorsement'])"
python3 -c "import json;d=json.load(open('$PK/.wiki/dataworks_index.json'));print('index_version',d['index_version'],'items',len(d['items']))"
```

## 完成后报告格式

- Step 0 dry-run 当前清单（changed / affected / index updates 实际数量）
- 变更文件三类归属表，并列 `deployment_id` / `file_version` / `execute_time`，便于 maintainer 核对比对的是哪次生产部署
- B122 500610077、B032 500581659（及第 3 个 index update）的具体代码语义差异结论；「纯指纹漂移」须附最小语义证据（如「仅注释 / 格式 / 调度包装变化」），不能只写「指纹变但口径不变」
- 受影响页逐页动作（未动 / stale / 撤 review / 入队）
- 索引 diff（哪些文件更新了指纹）、review_queue 新增项、open-question 新增页
- lint / eval / freshness --check 输出、commit sha（每类裁决可单独 commit）
- 偏离或异常

## Execution log by codex · 2026-07-02

### Step 0 dry-run 当前清单

- 默认全量部署扫描：`wiki_freshness --incremental-deployments --project-id 96107 --json` 触发 DataWorks read timeout，未拿到完整清单；按 task fallback 改用当前窗口 `--max-pages 1`。
- 当前窗口：`changed=16`、`affected=27`、`index_updates=3`。
- `index_updates`：
  - `file:96107/500610077` · deployment `2497210` · version `2852` · execute `2026-07-02T12:13:01+08:00` · `ods.pk_vos3000_e_cdr.extract`
  - `file:96107/500362902` · deployment `2496917` · version `28` · execute `2026-07-02T10:57:07+08:00` · `dws_holo.collection_case_repay_anl_hly`
  - `file:96107/500581659` · deployment `2496727` · version `9` · execute `2026-07-02T10:24:06+08:00` · `pk_dexin.dwd_user_login_log_dly`

### 裁决

三项均归为：`需 maintainer 深核`。

原因：本库与索引只保存当前摘要、指纹和回源定位，不保存旧 DataWorks 代码正文。Codex 可以确认当前代码指纹与索引旧指纹不一致，但无法做旧版 / 当前版语义级 diff，因此不能把任何一项判为“纯指纹漂移”，也不能直接判定具体业务口径变化。

### 受影响页动作

- 未改任何页面 `status`。
- 未撤回任何 `review:true`；受影响页原本均为 `review:false`。
- 未更新 `.wiki/dataworks_index.json` 指纹，避免把未人工确认的 drift 结论写入受管索引。
- 新增 `.wiki/review_queue.json` 三条 `stale_claim`：
  - `rev_20260702_001`：B122 `ods.pk_vos3000_e_cdr.extract`
  - `rev_20260702_002`：`dws_holo.collection_case_repay_anl_hly`
  - `rev_20260702_003`：B032 `pk_dexin.dwd_user_login_log_dly`
- 新增 open-question：`wiki/open-questions/freshness-drift-20260702.md` / `oq_20260702_freshness-drift-b122-b032`。
- 更新 `log.md` 顶部记录本轮保守复核。

### 验证

```text
wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk --check-only
错误: 0 · 警告: 0
lint=0

wiki_eval.py --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk --json
score 82 endorsement 10 review_coverage eligible=40 reviewed=4 percent=10

wiki_freshness.py --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk --incremental-deployments --project-id 96107 --max-pages 1 --check
changed_files: 16 · affected_pages: 28 · index_updates: 3
freshness=1
```

`freshness=1` 是预期结果：三项漂移未写回索引，保留给 maintainer 裁决。新增 open-question 因正文引用相关表名，被 freshness 纳入 affected pages，所以 check 输出的 affected pages 从 dry-run 写入前的 27 变为 28。

### Commit

- knowledge-pk commit：`ede60cd` (`[pk task-036] record DataWorks freshness drift review`)

### 偏离或异常

- 默认不带 `--max-pages` 的增量扫描超时；已按 task fallback 使用 `--max-pages 1` 和 fileId 当前指纹证据。
- 没有执行 `--apply` 更新索引，因为缺旧代码正文，无法达成“语义不变”的工程证据标准。

## Evaluation by claude · 2026-07-02

**Verdict: PASS。** 独立核验 knowledge-pk `.wiki/review_queue.json`：

- 3 条 `stale_claim`：`rev_001` B122 → 实为 `ods.pk_vos3000_e_cdr.extract`、`rev_002` `dws_holo` 催收汇总、`rev_003` B032 → `pk_dexin.dwd_user_login_log_dly`；各带 `affected_page_ids` + `evidence(note/quote/page)` + maintainer `options` + `priority`。B032 正确判 `high`（用户登录 / 身份链路），符合影响面。
- **命门达成**：B122 是 ODS 溯源层、无旧代码正文无法判定漂移性质，Codex 没硬猜，正确升级为 maintainer 复核项（`open_dwd_followup` vs `confirm_fingerprint_only`）。
- 守住 L3：索引未自动更新、无 auto `review:true`、`open-questions/freshness-drift-20260702.md` 已建。dry-run 保守裁决到位。

尾巴：3 条 drift 仍 `pending`，等 maintainer 裁决——这本就是 L3 人控的正确停点。


## Review by codex · 2026-07-02

结论：通过（有非阻塞建议）。

核实结果：

- `wiki_freshness.py --incremental-deployments --project-id 96107 --max-pages 1` 当前仍能定位到 B122 `file:96107/500610077` 和 B032 `file:96107/500581659`。本次 dry-run 返回 `changed=16 / affected=27 / index_updates=3`，两个目标 file_id 都在 `changed_files` 内。
- 直接按 fileId 回源也可行：`GetFile file:96107/500610077` 当前指纹为 `sha256:3522bda370d53644a046fc3cc99af478c5e5e1a77839e1f1b50165898c3d6c6b`；`GetFile file:96107/500581659` 当前指纹为 `sha256:14cf2370404baa99dbb9e591cea933a073089d0cdc80cc57784be37b1ddc5a75`。两者均与现有索引旧指纹不同，因此本 task 的“回源比对 + 裁决”确有输入。
- `ListDeployments` 没有 `start_time`，当前定位依赖最近部署页窗口；B122 是高频部署任务，B032 当前也在最近窗口内。为避免执行日窗口漂移，建议 Step 0 增加明确 fallback：若 `--incremental-deployments` 在默认窗口找不到指定 file_id，则先调大 `--max-pages`；仍找不到时直接 `GetFile file:96107/<fileId>` 与索引指纹比对，不因窗口缺失跳过 B122/B032。
- 同意 L3 红线：只能标 `stale`、撤 `review:true`、写 `review_queue` / open-question，严禁自动改回 `review:true` 或把回源事实直接写成已背书口径。

非阻塞建议：

- 完成后报告里把 `deployment_id/file_version/execute_time` 与 fileId 裁决表并列，便于 maintainer 复核“这次比对的是哪次生产部署”。
- 对“纯指纹漂移”建议记录最小语义证据，例如“仅注释/格式/调度包装变化”，不要只写“指纹变化但口径不变”。
