---
id: task_20260702_043
title: knowledge-pk 索引 domain 回填（改善反查按业务域分组）
author: claude
executor: codex
status: pending
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

## Execution log by codex · <date>

## Evaluation by claude · <date>
