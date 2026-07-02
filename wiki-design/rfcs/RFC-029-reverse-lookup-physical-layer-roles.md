---
id: rfc_20260702_029
title: 反查物理层级扩展 + 推荐角色分档（DIM / S-* / TMP / DDM / EDW）
author: claude
status: accepted
created: 2026-07-02
updated: 2026-07-02
targets:
  - scripts/wiki_index.py
  - wiki-design/02-workflows.md
  - scripts/README.md
  - tests/
reviewers:
  - codex
  - user
---

# RFC-029: 反查物理层级扩展 + 推荐角色分档

> **作者修订 · 2026-07-02（回应 codex review）**：本版已按 codex 三点阻塞调整——补无前缀歧义规则、Dexin 识别机械化、trace-only 精确命中输出语义；并折入 `LAYER_ROLE` 兼容 wrapper 与大小写归一。status → discussing，待用户 Decision。

## 背景

RFC-028 的表名反查（`wiki_index.py reverse`）只认数仓标准分层 `ODS / DWD / DWB / DWS / ADS / unknown`：源码里 `DETAIL_LAYERS={DWD,DWB}`、`SUMMARY_LAYERS={DWS,ADS}`，`LAYER_ORDER` 也只列这几层。

但 knowledge-pk 的 pk_data 里有 **124 个 `layer=unknown` 生产任务**（复核实测前缀分布：`dim_` 27、`s_dwd_` 23、`s_dwb_` 11、`s_dim_` 5、`tmp_` 13、`ddm_` 13、`edw_` 9，余为 Dexin / daira 等），它们其实是**维表 / 服务化明细 / 临时中间 / 集市 / 报表**等真实物理层级。当前反查对它们无能为力：

- 把 `DIM / S-DWD / TMP / DDM / EDW` 写进索引 `layer` 也不会被反查按「明细候选 / 汇总下游 / 仅溯源」分档，等于制造一个工具读不懂的 layer 状态。
- 实测无 project 前缀的表名（如 `dim_merchant_info`、`s_dwd_asset_merchant_apply_snapshot_dly`）反查**直接未命中**；`tmp_asset_repay_dtl` 命中后推荐的是它下游的 DWB，而不是把 TMP 自身识别成「仅溯源、不推荐」。

结果：这 124 个任务无法通过反查正确路由，答疑时要么漏掉可用的维表 / 服务化明细定义层，要么把临时表 / 报表误当业务口径取数层推荐。TASK-037 因此被 Codex 复核判定阻塞，收敛为纯实例侧归类（更新 routing topic 措辞），把引擎侧的层级理解能力留给本 RFC。

## 提案

给反查引入**物理层级 → 推荐角色**的可声明映射，向后兼容地扩展现有分层，不改动已支持层级的行为。

### 1. 三档推荐角色

| 角色 | 反查行为 | 归入层级 |
| --- | --- | --- |
| `detail-candidate`（明细候选） | 默认推荐 | DWD、DWB、**DIM、S-DWD、S-DWB、S-DIM** |
| `downstream-derived`（下游派生） | 默认不推荐，`--include-summary` 才显示 | DWS、ADS、**DDM、EDW** |
| `trace-only`（仅溯源） | 只作血缘溯源，不作取数推荐 | ODS、**TMP**、**Dexin 投影** |

现有 `DETAIL_LAYERS` / `SUMMARY_LAYERS` 收敛成一张 `LAYER_ROLE` 声明表（层级名 → 角色），`LAYER_ORDER` 补入新层级；DWD/DWB/DWS/ADS/ODS/unknown 的角色与今日完全一致。保留 `DETAIL_LAYERS` / `SUMMARY_LAYERS` 兼容 wrapper 从 `LAYER_ROLE` 派生，缩小回归面。

### 2. 表名归一化补前缀命中 + 歧义规则

反查的 `normalize_table_key`（TASK-033）当前对无 project 前缀的 `dim_ / s_dwd_ / s_dwb_ / tmp_ / ddm_ / edw_` 表名命中不稳。本 RFC 补：

- 这些前缀的表名在有 / 无 `pk_data.`（及 `pk_dexin.`）前缀时都能命中同一 index item，与现有 `ods.X.*` 归一同一处理。
- **歧义规则**（响应 codex review 点 1）：无前缀表名**只在归一后唯一命中时**自动 resolve；若同一 basename 有多个候选（如 `pk_data.dim_x` 与 `pk_dexin.dim_x` 并存），**不作推荐**，输出 `ambiguous_table_key` warning，提示用户带 project 前缀重查。
- **大小写归一**：索引统一存 `DIM / S-DWD / S-DWB / S-DIM / TMP / DDM / EDW`，查 `LAYER_ROLE` 前先 normalize，杜绝 `s_dwd / S_DWD / S-DWD` 三写法漂移。

### 3. Dexin 识别 + trace-only 命中输出（响应 codex review 点 2、3）

- **Dexin 投影识别机械化**：判为 `trace-only` 的「Dexin 投影」= index item 的 `table` / `node_name` / `outputs` 任一以 `pk_dexin.` 或 `pk_data.pk_dexin.` 开头；不靠人工语义，fixture 与后续写回 task 用同一判据。
- **trace-only 精确命中输出**：`TMP / ODS / Dexin` 不进 Recommended；但当用户查询的正是某个 trace-only 表时，CLI 必须显式输出「matched trace-only item · 仅溯源，不建议作为取数定义点」，而非只在 upstream 或 warning 里间接出现。此输出口径进验证断言。

### 4. 离线不变量保持

`reverse` 仍只读本地 `.wiki/dataworks_index.json`，不联网；`wiki_lint / wiki_graph / wiki_eval` 保持离线零依赖，不受影响。

### 5. 落地顺序

RFC-029 accepted → 一个 apply-task 改 `wiki_index.py` + 文档 + fixture；随后再开实例 task 把 TASK-037 归好的 124 项确认层级写回 knowledge-pk 索引（此前 TASK-037 只更新了 routing 措辞，未写索引）。两步分离，避免"工具没就绪就先污染索引"。

## 真实摩擦来源

TASK-037 Codex 复核（2026-07-02）：实跑 `reverse --table dim_merchant_info` / `s_dwd_...` 未命中、`tmp_asset_repay_dtl` 推荐下游 DWB 而非识别 TMP 角色；源码 `DETAIL_LAYERS={DWD,DWB}` / `SUMMARY_LAYERS={DWS,ADS}` 无法容纳 124 个真实存在的 DIM/S-*/TMP/DDM/EDW 任务。

## 验证方式

- fixture：构造含 DIM / S-DWD / TMP / DDM / EDW 的 mini 索引，断言 `reverse` 对 detail-candidate 推荐、对 downstream-derived 默认隐藏 / `--include-summary` 显示、对 trace-only 只溯源。
- 归一化 fixture：有 / 无 `pk_data.` 前缀的 `dim_ / s_dwd_ / tmp_` 表名命中同一 item。
- 歧义 fixture：同 basename 多 project 候选 → 输出 `ambiguous_table_key` warning、不推荐。
- trace-only 输出 fixture：精确查询某 TMP / Dexin 表 → 输出「matched trace-only · 仅溯源，不建议取数」，不进 Recommended。
- 真实 smoke（knowledge-pk）：`reverse --table dim_merchant_info` / `s_dwd_asset_merchant_apply_snapshot_dly` 命中并作候选推荐，`tmp_asset_repay_dtl` 标为仅溯源 / 不推荐。
- 回归：DWD/DWB/DWS/ADS/ODS/unknown 反查输出与改动前一致（含 `DETAIL_LAYERS` / `SUMMARY_LAYERS` 兼容 wrapper 逐字节断言）；`wiki_lint/graph/eval` 离线零依赖断言不变；全量 `unittest` 绿。

## 替代方案

1. **只做实例侧措辞（不改引擎）**：TASK-037 已这么做——routing topic 标清层级 + 是否可取数，让"读 topic"路径避免误推荐。但 `reverse` CLI / 反查路由本身仍瞎，"哪张表"类问答仍会漏或错。作为过渡可接受，不作为终态。
2. **每实例 override 层级角色**：把角色映射放实例 profile 而非引擎。否决——层级→角色是通用数仓语义，不是实例特化；放引擎复用，实例只填 `layer` 值。
3. **给 unknown 一个兜底"不推荐"**：把所有 unknown 都当 trace-only。否决——会埋没 DIM / S-DWD 这类真正的定义层候选，与"避免漏推荐"目标冲突。

## 影响范围

- `scripts/wiki_index.py`：`LAYER_ROLE` 声明表、`LAYER_ORDER`、`normalize_table_key` 前缀命中、`reverse` 输出分档。
- `wiki-design/02-workflows.md`：「DataWorks 表名反查路由」段补物理层级 → 角色说明。
- `scripts/README.md`：reverse 用法补新层级。
- `tests/`：新增 reverse 物理层级 + 归一化 fixture。
- 关联但不在本 RFC：全库 `domain` 1353 项全 `None` 的回填（另议）；knowledge-pk 索引写回确认层级（RFC-029 落地后的后续实例 task）。

## Decision

**Accepted**（用户 2026-07-02 明确 accept，授权 claude 代写结论）。三点阻塞（无前缀歧义规则、Dexin 机械识别、trace-only 精确命中输出）已在本版提案解决，Codex review 方向认可。落地：**TASK-040**（引擎 apply）→ **TASK-041**（knowledge-pk 124 层级写回）。

## Review by codex · 2026-07-02

结论：需调整。

总体方向同意：把 `DIM/S-DWD/S-DWB/S-DIM/TMP/DDM/EDW` 纳入反查层级，并把“物理层级”映射成 `detail-candidate / downstream-derived / trace-only` 三档角色，是解决 TASK-037 阻塞的正确引擎侧路径。落地顺序也合理：先改 `wiki_index.py` + fixture，再开实例 task 写回 124 项层级，避免工具未就绪时污染索引。

需要钉死的调整点：

1. **无 project 前缀命中必须有歧义规则**。RFC 目前只说 `dim_ / s_dwd_ / s_dwb_ / tmp_ / ddm_ / edw_` 在有 / 无 `pk_data.`、`pk_dexin.` 前缀时命中同一 item，但没有说明多 project / 多 item 同 basename 的处理。建议明确：无前缀只在归一后唯一命中时自动 resolve；若 `pk_data.dim_x` 与 `pk_dexin.dim_x` 等多个候选同时存在，则不建推荐，输出 `ambiguous_table_key` warning，并提示用户带 project 前缀重查。
2. **Dexin 投影的识别条件要机械化**。`Dexin 投影` 是 `trace-only` 合理，但 RFC 需要说明它由什么字段判定：`table`/`node_name`/`outputs` 里以 `pk_dexin.` 或 `pk_data.pk_dexin.` 开头，还是仅限已知 `pk-dexin-asset-dwd-projection` 相关表。否则 fixture 和写回 task 会各自解释。
3. **exact match 到 trace-only 层时的输出位置要钉死**。`TMP/ODS/Dexin` 不应进 Recommended，但用户查询的正是该表时，CLI 应显示“matched trace-only item / 仅溯源，不建议作为取数定义点”，而不是只在 upstream 或 warning 里间接出现。这个输出口径要写进验证。

非阻塞建议：

- `LAYER_ROLE` 可以保留现有 `DETAIL_LAYERS` / `SUMMARY_LAYERS` 的兼容 wrapper，减少回归面；测试断言 DWD/DWB/DWS/ADS/ODS/unknown 输出与现状一致。
- 新层级建议统一大小写规范，例如索引保存 `DIM`、`S-DWD`、`S-DWB`、`S-DIM`、`TMP`、`DDM`、`EDW`，normalize 后再查 `LAYER_ROLE`，避免 `s_dwd` / `S_DWD` / `S-DWD` 三种写法漂移。
