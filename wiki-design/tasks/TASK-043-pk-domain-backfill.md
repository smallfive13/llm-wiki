---
id: task_20260702_043
title: knowledge-pk 索引 domain 回填（改善反查按业务域分组）
author: claude
executor: codex
status: done
type: other
created: 2026-07-02
updated: 2026-07-02
related_rfcs: []
---

# TASK-043: knowledge-pk 索引 domain 回填

## 目标

给 `.wiki/dataworks_index.json` 的 items 回填 `domain`（现 1353 项全 `None`），使 `reverse` 的 downstream/候选分组按业务域显示（现在全落 `[unknown]` 组）。**纯实例数据回填**——engine 已消费 `item.domain` 做分组，本 task 不改引擎。承接 TASK-037 open-question 记录的 domain 缺口。

## 前置条件

- 索引 `index_version=2` / 1353 items 在；knowledge-pk working tree clean。

## 强约束

1. **domain 是 pk 业务域，不进引擎硬编码**：取值域 `{asset, coll, risk, user, merchant, capital, oper, mkt, cib, fin}`（沿用 purpose.md / TASK-037）。engine 只按 `item.domain` 分组，域枚举与判据是实例数据。
2. **判据 = 表名关键词 + 血缘**（复用 TASK-037 对 124 unknown 的域判定规则并扩到全量）；判不准的**留空 / unknown，不硬填**。
3. 这是**分类不是背书**：不 auto `review:true`；索引守受管基线（v2 / 1353 / 无代码正文）。
4. 不改引擎、不改 `layer`（TASK-041 已定），只写 `domain`。

## 步骤

1. 定 domain 推断规则表（表名关键词/前缀 → 域，例如 `asset_/listing_/loan_/repay_→asset`、`coll_/case_→coll`、`risk_/audit_/limit_/datacheck_/tasdeeq_→risk`、`user_/device_/applist_→user`、`merchant_/pos_/vendor_→merchant`、`capital_/acct_/trade_→capital`、`oper_/ddp_/pms_→oper`、`mkt_/appsflyer_/signup_→mkt`、`cib_→cib`、`fin_→fin`），blood 复核冲突项。
2. 批量写 index items 的 `domain`；判不准留空。
3. reverse smoke：查一张 asset 表，downstream 候选应分到 `[asset]` 而非 `[unknown]`。
4. lint / graph / eval；commit。

## 验证

```bash
PK=/Users/zhangjunwu/workspace/obsidian/knowledge-pk
python3 -c "import json,collections;d=json.load(open('$PK/.wiki/dataworks_index.json'));print('domain:',dict(collections.Counter(i.get('domain') for i in d['items'])))"   # None 应大幅下降
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_index.py reverse --root $PK --table dwd_asset_loan_list   # 候选分组应显示 [asset]
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root $PK --check-only; echo lint=$?
```

## 完成后报告格式

- domain 推断规则表 + 回填后 domain 分布（None 从 1353 降到 N）
- reverse 分组 smoke（asset 表候选进 [asset]）
- 索引基线确认（v2 / 1353 / 无代码正文）
- lint / graph / eval、commit sha、偏离或异常

## Execution log by codex · 2026-07-03

### Step 0 / 规则确认

- knowledge-pk working tree clean 后开工。
- 当前索引基线：`index_version=2` / `items=1353` / 无 code payload。
- 初始 domain 分布：

```text
None 1263
asset 24
user 24
risk 16
oper 8
merchant 6
coll 5
cib 2
mkt 2
capital 2
fin 1
```

推断规则按表名 / node_name 优先，血缘作为弱补充；已有人工 domain 一律保留，不覆盖 TASK-041 的人工判定。关键词：

```text
asset: asset, loan, listing, repay, debt, deal, bnpl, delay
coll: coll, collection, case, collector, recovery, overdue_debt
risk: risk, audit, limit, datacheck, tasdeeq, pata, seon, blacklist, anti
user: user, device, applist, trackapp, identity, account_cancel, fill_info, h5element, gps, signup, register, ocr
merchant: merchant, vendor, pos, daira, daraz
capital: capital, acct, fund, owing
oper: oper, ddp, pms, call, staff, department, large_screen, conv_remind, service/cs
mkt: mkt, marketing, appsflyer, utm, campaign, channel
cib: cib
fin: fin, erp_dm_op_internation, acct_company, bad_amount, transaction_detail, fund_detail
```

### 写回结果

- 保留已有非空 domain：90 项。
- 从原 None 项回填：1036 项。
- 保留 None：227 项，主要是训练、系统配置、Mongo 水位、未识别 ODS/internal 处理链等不硬判项。

写回后 domain 分布：

```text
asset 175
user 268
cib 5
risk 213
None 227
oper 144
mkt 9
coll 129
fin 17
capital 75
merchant 91
```

### Reverse smoke

```text
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_index.py reverse --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk --table dwd_asset_loan_list

Downstream candidates
---------------------
[asset]
- DWD dwd_asset_loan_list · pk_data.dwd_asset_loan_list · has_knowledge_page · 明细定义层，通常优先作为业务口径候选。
```

### 验证

```text
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk --check-only
lint=0

/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_graph.py --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk --json
graph=0
nodes 1405 edges 1987 dangling 0

/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_eval.py --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk --json
eval=0
score 83
```

### Commits

- knowledge-pk: `4e7dd59` `[pk task-043] backfill dataworks index domains`

## Evaluation by claude · <date>
