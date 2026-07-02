---
id: task_20260702_037
title: knowledge-pk Unknown 层 124 任务人工归类（实例侧）— 归类清单 + routing 措辞 + open-question（索引/反查改动见 RFC-029）
author: claude
executor: codex
status: done
type: other
created: 2026-07-02
updated: 2026-07-02
related_rfcs: [RFC-028]
---

# TASK-037: knowledge-pk Unknown 层归类（实例侧）

> **作者调整 · 2026-07-02（executor 未开工前）**：Codex 复核判定原设计阻塞——`wiki_index.py reverse` 硬编码只认 `ODS/DWD/DWB/DWS/ADS/unknown`（`DETAIL_LAYERS={DWD,DWB}` / `SUMMARY_LAYERS={DWS,ADS}`），把 `DIM/S-DWD/TMP/DDM/EDW` 写进索引 `layer` 只会制造工具读不懂的状态，且无前缀表名（如 `dim_merchant_info`）反查还未命中。故本 task **收敛为纯实例侧归类**：产出人工归类 + 更新 routing topic 措辞 + open-question，**不改索引 `layer`、不碰引擎**。让反查理解新物理层级 / 推荐角色的引擎改动另走 **RFC-029**；RFC-029 accepted + applied 后，再开后续 task 把确认层级写回索引。

## 目标

对索引里 124 个 `layer=unknown` 任务做**人工归类**（物理层级 + 主题域 + 反查推荐角色），沉淀成：① 归类清单；② 更新 3 个 unknown routing topic 措辞，让「答疑读 topic」路径不再误把 TMP / DDM / EDW 当业务口径推荐；③ open-question 记录「索引 layer 写回 + reverse 角色支持」待 RFC-029。**本 task 不改索引 `layer`、不改引擎。**

## 前置条件

- 索引 `index_version=2`、1353 items 在。TASK-033 反查归一化在。
- knowledge-pk working tree clean；`PY` 同 TASK-036。

## 强约束

1. **命名前缀是线索不是判据**，必须结合 `inputs`/`outputs` 血缘确认后再定层级。归类规则（初判 → 血缘复核）：
   | 前缀 | 物理层级 | 反查推荐角色（待 RFC-029 落地） | 说明 |
   | --- | --- | --- | --- |
   | `dim_` | DIM 维表 | 明细候选（可推荐） | 解释枚举 / 映射，是可解释口径的定义层 |
   | `s_dwd_` | S-DWD 服务化明细 | 明细候选（可推荐） | 服务化落地的 DWD，接近业务定义点 |
   | `s_dwb_` | S-DWB 服务化宽表 | 明细候选（可推荐） | 服务化宽表定义点 |
   | `s_dim_` | S-DIM 服务化维 | 明细候选（可推荐） | 服务化维表 |
   | `tmp_` | TMP 临时 | 不推荐（仅溯源） | 稳定性 / 消费范围需人工确认，不背书为口径 |
   | `ddm_` | DDM 集市 | 下游派生（默认不推荐） | 面向应用 / 分析加工，非取数定义层 |
   | `edw_` | EDW 报表 | 下游派生（默认不推荐） | 财务 / 运营 / AUM / 国际化报表 |
   | `pk_dexin.*` | Dexin 投影 | 溯源（默认不推荐） | 不替代主域定义点（见 pk-dexin-asset-dwd-projection） |
   （复核实测前缀分布：`dim_` 27、`s_dwd_` 23、`s_dwb_` 11、`s_dim_` 5、`tmp_` 13、`ddm_` 13、`edw_` 9，余为 Dexin / daira 等。）
2. **主题域**从 `{asset, coll, risk, user, merchant, capital, oper, mkt, cib, fin}` 选，依据表名 + 血缘判定；判不准的留空 + open-question，不硬填。
3. **不写索引 `layer`/`domain`**（避免 unsupported 值污染反查）；归类结果只落 wiki 页（归类清单 + routing topic）。索引写回等 RFC-029。
4. **不碰引擎**（`wiki_index.py` 等）；引擎侧改动全部走 RFC-029。
5. routing topic 措辞要显式标出每项的「物理层级 + 是否可作口径取数」，让 AI 读 topic 就能避免误推荐——这是本 task 在 reverse 未修好前仍能交付「避免误推荐」价值的关键。

## 步骤

1. 导出 124 unknown 清单（`table` / `inputs` / `outputs` / 命名前缀）。
2. 按规则表逐个定 物理层级 + 主题域 + 反查角色，血缘复核存疑项（存疑保留待定 + open-question）。
3. 归类结果落一页：建议 `maps/` 或 `wiki/topics/` 下的「unknown 归类清单」，或并入 3 个 routing topic 的表格列。**不写 `.wiki/dataworks_index.json`。**
4. 更新 3 个 unknown routing topic：把已确认项措辞从「层级暂为 unknown」改为「物理层级 = X、反查角色 = Y、是否可作口径取数 = 是/否」；仍存疑的少数保留 unknown + 关联 open-question。
5. 建 open-question `oq_20260702_unknown-layer-reverse-support`：记「已知信息（124 项已人工归类、规则表、前缀分布）/ 待确认（索引 layer 写回 + reverse 角色支持需 RFC-029）」，**顺带记全库 `domain` 1353 项全 None 的缺口**。
6. lint / graph / eval。

## 验证

（本 task 不改索引，故不校验 unknown 计数下降；校验落在「索引未变」+ wiki 页 lint。）

```bash
PY="/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python"
PK=/Users/zhangjunwu/workspace/obsidian/knowledge-pk
# 索引未被改：layer 分布应不变、unknown 仍 124
python3 -c "import json,collections;d=json.load(open('$PK/.wiki/dataworks_index.json'));print(dict(collections.Counter(i['layer'] for i in d['items'])))"
git -C $PK status --short .wiki/dataworks_index.json   # 期望无输出（索引未动）
$PY scripts/wiki_lint.py --root $PK --check-only; echo lint=$?
$PY scripts/wiki_graph.py --root $PK 2>&1 | tail -3   # 无 dangling / orphan
```

## 完成后报告格式

- 124 项归类结果表（物理层级 + 主题域 + 反查角色），存疑保留待定的清单
- 3 个 routing topic 措辞改动摘要（每项标物理层级 + 是否可作口径取数）
- open-question 新增页（含 RFC-029 待办 + domain 全空缺口）
- 确认索引未被改动（layer 分布不变、git status 干净）
- lint / graph / eval、commit sha、偏离或异常

## Execution log by codex · 2026-07-02

### 范围

按调整后的缩版 task 执行：只做 knowledge-pk 实例侧归类，不改 `.wiki/dataworks_index.json`，不改 `scripts/wiki_index.py`。

### 归类结果

- 当前索引 layer 分布保持不变：`{'unknown': 124, 'DWD': 174, 'DWB': 45, 'DWS': 36, 'ODS': 974}`。
- 124 个 unknown 的实例侧归类已落到 `wiki/topics/unknown-layer-classification.md`。
- 角色分布：
  - DIM / `detail-candidate`: 27
  - S-DWD / `detail-candidate`: 23
  - S-DWB / `detail-candidate`: 11
  - S-DIM / `detail-candidate`: 5
  - DDM / `downstream-derived`: 13
  - EDW / `downstream-derived`: 9
  - TMP / `trace-only`: 13
  - Dexin 投影 / `trace-only`: 1
  - 待定 / `unknown`: 22
- 主题域分布：asset 24、user 24、risk 16、oper 10、merchant 6、coll 5、fin 4、capital 3、cib 2、mkt 2、unknown 28。

### 文件变更

- 新增 `wiki/topics/unknown-layer-classification.md`：124 项人工归类清单。
- 更新 3 个 routing topic：
  - `wiki/topics/unknown-asset-coll-risk-user-routing.md`
  - `wiki/topics/unknown-fin-capital-oper-mkt-cib-merchant-routing.md`
  - `wiki/topics/unknown-other-sync-report-routing.md`
- 新增 open-question `wiki/open-questions/unknown-layer-reverse-support.md`，记录 RFC-029 与后续索引写回待办。
- 更新 `log.md`。

### 验证

```text
git status --short .wiki/dataworks_index.json
(no output)

python count layer
{'unknown': 124, 'DWD': 174, 'DWB': 45, 'DWS': 36, 'ODS': 974}
unknown 124

wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk --check-only
错误: 0 · 警告: 0
lint=0

wiki_graph.py --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk
wiki-graph: 1396 nodes, 1880 edges, 54 communities
```

### Commit

- knowledge-pk commit：`6b8d5a3` (`[pk task-037] document unknown layer classification`)

### 偏离或异常

- 未做索引写回，符合缩版 task 边界。
- 22 个条目仍为待定，因命名和血缘不足以稳定判定，已保留在归类清单和 open-question 后续处理。

## Evaluation by claude · 2026-07-02

**Verdict: PASS（缩版范围内）。** 独立核验：

- 索引 layer 分布不变（`unknown` 仍 124）、`git status` 索引干净——守住「不写 unsupported layer」的核心约束。
- 124 项归类落 `wiki/topics/unknown-layer-classification.md`：`detail-candidate` 66（DIM 27 / S-DWD 23 / S-DWB 11 / S-DIM 5）、`downstream-derived` 22（DDM 13 / EDW 9）、`trace-only` 14（TMP 13 / Dexin 1）、待定 22。22 待定诚实保留，不硬判。
- `open-questions/unknown-layer-reverse-support.md` 已建，承接 RFC-029 + domain 全空缺口。

「避免误推荐」价值已通过 3 个 routing topic 措辞交付；反查 CLI 真正修复待 RFC-029 + TASK-041 写回。


## Review by codex · 2026-07-02

结论：阻塞，需要先调整设计。

阻塞点：

1. 现有 `wiki_index.py reverse` 不支持本 task 拟新增的真实层级角色。源码里 `DETAIL_LAYERS={"DWD","DWB"}`、`SUMMARY_LAYERS={"DWS","ADS"}`、`LAYER_ORDER` 也只有 `ODS/DWD/DWB/DWS/ADS/unknown`。`DIM/S-DWD/S-DWB/S-DIM/TMP/DDM/EDW` 即使写进索引，也不会按“明细候选 / 汇总下游 / 溯源不推荐”自动分档。
2. 实跑 smoke 证实当前验证命令不可直接成立：`reverse --table dim_merchant_info`、`reverse --table s_dwd_asset_merchant_apply_snapshot_dly` 均未命中；`reverse --table pk_data.tmp_asset_repay_dtl` 命中后推荐的是下游 `DWB dwb_asset_repay_dtl`，不是把 TMP 自身识别成“仅溯源、不推荐”的角色。
3. 当前索引确有 124 个 `unknown`，其中命名前缀分布包含 `dim_` 27、`s_dwd_` 23、`s_dwb_` 11、`s_dim_` 5、`tmp_` 13、`ddm_` 13、`edw_` 9。归类需求真实存在，但“只改 pk 实例索引，不碰引擎”无法达成 task 写的反查行为目标。

建议调整：

- 不要按当前设计直接把 `layer` 改成 `DIM/S-DWD/S-DWB/TMP/DDM/EDW` 并期待 reverse 正确推荐；这会制造一个工具不理解的新 layer 状态。
- 先开引擎侧 RFC / task 定义“物理层级”和“反查角色”的映射，例如新增 role 层或扩展 `DETAIL_LAYERS` / `SUMMARY_LAYERS` / `LAYER_ORDER`，并补无 project 前缀表名的 alias 命中策略。
- 若必须先做实例侧工作，建议把本 task 缩小为：导出 124 项人工归类表、更新 routing topic / open-question 记录待引擎支持的规则，不写 `.wiki/dataworks_index.json` 的 unsupported layer 值。

规则表评价：

- `DIM/S-DWD/S-DWB/S-DIM` 作为可推荐定义层、`TMP/DDM/EDW` 默认不推荐的方向合理。
- `pk_dexin.*` 默认不替代主域定义点也合理。
- 但这些规则目前属于“设计规则”，还不是现有 `wiki_index.py reverse` 能执行的规则。
