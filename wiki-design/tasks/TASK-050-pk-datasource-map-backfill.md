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

## Execution log by codex · <date>

## Evaluation by claude · <date>
