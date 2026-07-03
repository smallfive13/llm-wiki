---
id: task_20260703_050
title: knowledge-pk 数据源解析表生成 + source_database 回填 + 核对 gate + 措辞精确化
author: claude
executor: codex
status: pending
type: other
created: 2026-07-03
updated: 2026-07-03
related_rfcs: [RFC-031]
---

# TASK-050: knowledge-pk 数据源解析回填 + 措辞精确化

## 目标

用 TASK-049 的解析能力：① 生成 pk `.wiki/datasource_map.json`（65 数据源）；② 索引 parsed 项回填 `source_database`/`source_db_type`；③ 产出 maintainer **逐个核对清单**（硬停 gate）；④ 核对通过后批量精确化 source 页措辞（消化 TASK-048 遗留：datasource 是别名、补线上库信息）。**不改任何 `review` 字段**——RFC-031 §5：核对通过后该层信息随原背书页生效，无需重新背书。

## 前置条件

- **TASK-049 done**（sanitized DTO + map + 巡检在）。
- knowledge-pk working tree clean；凭证在 env。

## 强约束

1. **map 生成**：全量 65 数据源 → `.wiki/datasource_map.json`（受管共享基线：稳定排序、无 volatile、无敏感串）；pk `.gitignore` 显式 allowlist、`.ignore` 屏蔽检索。落地后对文件跑禁词扫描（TASK-049 清单），0 命中才算过。
2. **索引回填**：仅 `source_binding=parsed` 且 map 中 `resolution` 成功的项写 `source_database`/`source_db_type`；`resolution: failed` 的项不写。索引守受管基线（v2 / 1353 / 无代码正文）。
3. **核对 gate（硬停点）**：产出核对清单——至少覆盖被 parsed 页引用的 46 个数据源（`datasource_name → db_type:database_name`，附 DataWorks 数据源管理页入口），**逐个核对而非抽样**（总量小）。产出后停下等 maintainer，未通过不得进入措辞精确化。
4. **措辞精确化（gate 通过后）**：
   - parsed + 解析成功页（330 内）：正文行改为「同步来源：DataWorks 数据源 `<ds>`（线上库 `<db_type>:<database>`）· 源表 `<tables>`」。
   - parsed + `resolution: failed`：保留数据源名 + 注明「线上库待确认」。
   - **不改 `review` / `last_verified` / `confidence`**（该层是 maintainer 已核对的机器事实附加，非重新背书；`updated` 日期正常更新）。
5. 每阶段单独 commit（map / 索引 / 措辞）；lint / graph / eval 全过；`log.md` 记录（含"线上库信息经 maintainer 逐个核对"依据）。

## 步骤

1. 生成 map + 禁词扫描 + `.gitignore`/`.ignore` 落位；commit。
2. 索引回填 `source_database`/`source_db_type`；报分布（成功/failed 数）；commit。
3. 产出核对清单（46+ 条）追加到本 task Execution log，**硬停等 maintainer**。
4. maintainer 通过 → 按约束 4 批量措辞精确化；不通过 → 记问题、修正后重出清单，不动页面。
5. freshness 数据源巡检 smoke（dry-run 应 no-op）；lint / graph / eval；log.md 收尾。

## 验证

```bash
PK=/Users/zhangjunwu/workspace/obsidian/knowledge-pk
python3 -c "
import json
m=json.load(open('$PK/.wiki/datasource_map.json'))
entries=m.get('datasources',m) if isinstance(m,dict) else m
import collections
print('entries',len(entries))"
grep -rEc "jdbc:|://|password|accessKey|username|endpoint" $PK/.wiki/datasource_map.json && echo "禁词命中！" || echo "禁词 0 命中"
python3 -c "import json,collections;d=json.load(open('$PK/.wiki/dataworks_index.json'));print('source_database 覆盖:',sum(1 for i in d['items'] if i.get('source_database')));print('version',d['index_version'],'items',len(d['items']))"
grep -rl "线上库" $PK/wiki/sources --include='*.md' | wc -l   # gate 通过后 ≈ parsed 成功数
git -C $PK diff HEAD~1 --stat -- 'wiki/sources/*.md' | tail -1
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root $PK --check-only; echo lint=$?
```

## 完成后报告格式

- map 条目数 + 禁词扫描结果 + `.gitignore`/`.ignore` 落位
- 索引回填分布（成功 / failed）+ 基线确认
- 核对清单 + maintainer 核对记录
- 措辞精确化页数（parsed 成功 / failed 两类）+ 确认 review 字段零变更
- 巡检 smoke、lint / graph / eval、per-阶段 commit sha、偏离或异常

## Execution log by codex · 2026-07-03

### Scope

- 已执行 Step 1~3，停在数据源逐个核对 gate。
- 未执行 Step 4；未改 330 个 source 页正文措辞。
- 未改任何 `review` / `last_verified` / `confidence`。

### Step 1 · datasource_map baseline

- 生成：`/Users/zhangjunwu/workspace/obsidian/knowledge-pk/.wiki/datasource_map.json`
- 条目数：65
- resolution：`parsed 64` / `failed 1`
- 类型分布：mysql 47 / mongodb 15 / sqlserver 1 / odps 1 / holo 1
- 禁词扫描：0 命中（`jdbc:` / `://` / host / address / endpoint / port / username / password / accessKey / secret / token）
- `.gitignore`：已 allowlist `!.wiki/datasource_map.json`
- `.ignore`：已有 `.wiki/`，会屏蔽 datasource map 进入全文检索
- pk commit：`fefd09b97d5cffac440239783370d96835fbad42` (`[pk task-050] add datasource map baseline`)

### Step 2 · index backfill

- 索引：`.wiki/dataworks_index.json`
- `index_version`: 2
- `items`: 1353
- `source_binding=parsed`: 330
- `source_database` 覆盖：330
- `source_db_type` 覆盖：330
- parsed 但解析失败：0
- pk commit：`6489483b675faf02c7e4cec6ad61d37c9defb8e1` (`[pk task-050] attach source databases to index`)

说明：

- 对 index 全文用裸词 `port` 扫描会误命中业务表名中的 `report`，因此禁词硬门禁以 RFC-031/TASK-049 定义的 datasource map 输出为准；map 扫描 0 命中。
- 本阶段只回填受管索引，不改 source 页正文。

### Step 3 · maintainer review checklist

硬停点：

- 以下 46 个 datasource 是 TASK-048 parsed 页实际引用的去重集合。
- 请 maintainer 逐个核对 `datasource_name -> db_type:database_name`。
- 通过前不得进入 Step 4 的 source 页措辞精确化。

| datasource_name | db_type:database_name | parsed_items | console |
| --- | --- | ---: | --- |
| `app_server` | `mysql:app_server` | 2 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=app_server) |
| `audit_center` | `mysql:audit_center` | 9 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=audit_center) |
| `es_cdr_new` | `sqlserver:es_cdr` | 1 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=es_cdr_new) |
| `information_schema` | `mysql:information_schema` | 1 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=information_schema) |
| `loan_biz` | `mysql:loan_biz` | 11 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=loan_biz) |
| `loan_biz_autosync_2` | `mongodb:loan_biz` | 3 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=loan_biz_autosync_2) |
| `loan_biz_autosync_3` | `mongodb:loan_biz` | 2 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=loan_biz_autosync_3) |
| `pak_backend` | `mysql:pak_backend` | 1 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=pak_backend) |
| `pak_backend_autosync_2` | `mongodb:pak_backend` | 1 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=pak_backend_autosync_2) |
| `pak_backend_user` | `mysql:pak_backend_user` | 1 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=pak_backend_user) |
| `pak_capital` | `mysql:pak_capital` | 23 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=pak_capital) |
| `pak_capsule_box` | `mysql:pak_capsule_box` | 2 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=pak_capsule_box) |
| `pak_cds_autoflow` | `mysql:pak_cds_autoflow` | 12 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=pak_cds_autoflow) |
| `pak_ddp_execute_log_autosync_3` | `mongodb:pak_ddp_execute_log` | 1 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=pak_ddp_execute_log_autosync_3) |
| `pak_dmp` | `mysql:pak_dmp` | 1 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=pak_dmp) |
| `pak_gpms_autoflow` | `mysql:pak_gpms_autoflow` | 12 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=pak_gpms_autoflow) |
| `pak_gpms_cas` | `mysql:pak_gpms_cas` | 2 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=pak_gpms_cas) |
| `pak_listing` | `mysql:pak_listing` | 2 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=pak_listing) |
| `pak_listing_autosync_3` | `mysql:pak_listing` | 26 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=pak_listing_autosync_3) |
| `pak_loan_markting` | `mysql:pak_loan_markting` | 7 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=pak_loan_markting) |
| `pak_ppdai_cs_crm` | `mysql:pak_ppdai_cs_crm` | 3 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=pak_ppdai_cs_crm) |
| `pak_ppdai_cs_voice` | `mysql:pak_ppdai_cs_voice` | 2 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=pak_ppdai_cs_voice) |
| `pak_ppdai_train` | `mysql:pak_ppdai_train` | 11 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=pak_ppdai_train) |
| `pak_sdk_data` | `mysql:pak_sdk_data` | 2 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=pak_sdk_data) |
| `pak_sword` | `mysql:pak_sword` | 27 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=pak_sword) |
| `pak_thirdparty_data` | `mongodb:pak_thirdparty_data` | 2 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=pak_thirdparty_data) |
| `pak_thirdparty_data_autosync_1` | `mongodb:pak_thirdparty_data` | 6 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=pak_thirdparty_data_autosync_1) |
| `pak_thirdparty_data_autosync_3` | `mongodb:pak_thirdparty_data` | 4 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=pak_thirdparty_data_autosync_3) |
| `pak_vendor_biz` | `mysql:pak_vendor_biz` | 18 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=pak_vendor_biz) |
| `pak_vendor_biz_autosync_2` | `mongodb:pak_vendor_biz` | 2 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=pak_vendor_biz_autosync_2) |
| `pak_xtms` | `mysql:pak_xtms` | 12 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=pak_xtms) |
| `pak_xtms_agent` | `mysql:pak_xtms_agent` | 2 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=pak_xtms_agent) |
| `pak_xtms_call` | `mysql:pak_xtms_call` | 1 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=pak_xtms_call) |
| `pk_vos3000` | `mysql:vos3000` | 1 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=pk_vos3000) |
| `ppdai_cas` | `mysql:ppdai_cas` | 1 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=ppdai_cas) |
| `ppdai_pk_rhino` | `mysql:ppdai_pk_rhino` | 1 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=ppdai_pk_rhino) |
| `ppdai_site_msg` | `mysql:ppdai_site_msg` | 1 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=ppdai_site_msg) |
| `ppdai_sms_base` | `mysql:ppdai_sms_base` | 5 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=ppdai_sms_base) |
| `ppdai_sms_message_2019` | `mysql:ppdai_sms_message_2019` | 4 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=ppdai_sms_message_2019) |
| `risk` | `mysql:risk` | 3 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=risk) |
| `risk_public` | `mysql:risk` | 2 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=risk_public) |
| `sdk_backend` | `mongodb:sdk_backend` | 6 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=sdk_backend) |
| `sdk_backend_autosync_2` | `mongodb:sdk_backend` | 2 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=sdk_backend_autosync_2) |
| `sdk_backend_autosync_3` | `mongodb:sdk_backend` | 29 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=sdk_backend_autosync_3) |
| `sdk_backend_autosync_4` | `mongodb:sdk_backend` | 24 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=sdk_backend_autosync_4) |
| `user_main_autosync_2` | `mysql:user_main` | 39 | [DataWorks](https://dataworks.console.aliyun.com/?projectId=96107#/datasource?name=user_main_autosync_2) |

### Verification at gate

- pk lint after map/index: exit 0（0 错 0 警）。
- pk graph after map/index: exit 0；nodes 1431 / edges 2707 / dangling 0 / isolated 0。
- pk eval after map/index: exit 0；score 82 / integrity 100 / connectivity 100 / review_coverage 6/70。
- pk working tree clean after two pk commits.
- `wiki/sources/*.md` 未修改，Step 4 未执行。

## Evaluation by claude · <date>
