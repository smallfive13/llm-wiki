---
id: rfc_20260622_027
title: DataWorks 代码知识化（asset-mapping 页型 + 代码锚点 + L1/L2/L3 更新机制 + fun-cli 接入）
author: claude
status: accepted
created: 2026-06-22
updated: 2026-06-22
targets:
  - wiki-design/02-workflows.md
  - scripts/wiki_freshness.py
  - scripts/wiki_common.py
  - scripts/README.md
  - tests/
reviewers:
  - codex
  - user
---

# RFC-027: DataWorks 代码知识化

## 背景

knowledge-pk 的核心场景是把 **DataWorks 上的代码（SQL/Python 加工逻辑）** 沉淀成可答疑的业务知识。代码本体不进库（留在 DataWorks），库里存的是"从代码梳理出的口径/语义/血缘/坑"。这带出三个当前缺失的机制：

1. **没有"业务概念 ↔ 物理表字段"的结构化页型**。实测：用户问"收款渠道是 jazz 还是 ep、在哪张表，有没有还款渠道记录表"——这是"业务词 → 物理表字段"的发现问题，机器元数据按业务词搜不到（字段叫 `pay_channel` 不叫"收款渠道"），而库里也没有承载这种映射的页型。
2. **代码会变，但没有失效检测**。从代码梳理的口径是**快照**；上游代码改了，库里的口径会悄悄过时，现在只能靠时间阈值（RFC-025 staleness）粗略提醒，不精准。
3. **答疑没有回源代码的约定**。库快照不够细或可能过时时，agent 应能回源查 DataWorks 当前代码确认，但既无约定也无访问通道。

第 3 点的访问通道现已就位：本机 **`fun-cli` skill** 能查数据表/字段/任务元数据（描述/负责人/类型/血缘/上下游/**建表代码**），且**凭证封装在 fun-cli 内部**（`auth login`），知识库无需碰 AK/SK——既解决访问、又不违"不存凭证"红线、不让知识库越界自管凭证。

## 提案

分四个 milestone。原则贯穿全程：**对代码 pull 不 push、检测失效不自动重写、机器筛人来判、DataWorks 访问统一走 fun-cli。**

### M1 — `asset-mapping` 结构化页型（走 profile）

在 **knowledge-pk 的 `.wiki-profile.json`**（RFC-008 overlay，只增不改 base）加一个页型 `asset-mapping`，承载"业务概念 ↔ 物理表字段"映射。建议字段：

- `business_concept`（业务概念名，如"收款渠道"；答疑检索的命中锚）
- `physical_table` / `physical_field`（物理落点，如 `edw.xxx` / `pay_channel`）
- `value_mapping`（枚举语义，如 `jazz=…` / `ep=…`）
- `lineage_upstream`（血缘上游表 / 上游口径页，复用 `related_ids` 表达，见 M2）
- `caveats`（坑 / 适用边界）
- **代码锚点**（`dataworks_ref` / `code_fingerprint` / `last_synced`，见 M3）

> 先在 pk 落地验证页型设计（用户的 jazz/ep 问题就是验收用例）；确认 cmn/未来 mex 也通用后，再抽成引擎共享 dw profile——**那一步是 RFC-008 的增强（profile 从"每实例独立"到"引擎定义+实例引用"），不在本 RFC**，本 RFC 先落 pk profile。

### M2 — 代码梳理方法论 + 传导口径

**代码梳理 7 维**（通用部分进引擎 `02-workflows.md`，pk 特定进 pk AGENTS 引用）：口径与定义 / 血缘数据流 / 关键逻辑（说明非代码）/ 设计决策（为什么）/ 调度运行特性 / 踩坑 / 适用边界。反面约束：不贴整段代码当正文、不逐行翻译、不沉淀一次性查询。

**传导口径**（口径从 ODS→DWD→DWS→ADS 逐层叠加）：
- 口径只在**定义点**写一次（canonical 正本），下游**只记本层增量**、用 `related_ids` 指向上游定义点，完整口径沿链累积、不重抄。
- 血缘链 = `related_ids` 有向边，复用现成 `wiki_graph`（`in_degree` 高即根口径）。**边类型化**（区分"血缘"vs"一般参见"，如 `derives_from`）列为 backlog，不在本 RFC。
- 上游口径未整理 → `open-question`（source-gap，RFC-018）占位；同名不同口径 → `open-question`（口径分歧）/ `decision`（对齐），不让矛盾口径并存。

### M3 — 代码锚点 + 失效检测（L2，机器筛）

口径页 / `asset-mapping` 页 frontmatter 加**代码锚点**：`dataworks_ref`（表名或任务标识）+ `code_fingerprint` + `last_synced`。

新增 **`scripts/wiki_freshness.py`**（职责单一、隔离外部依赖）：调 `fun-cli meta table get <table> --type code` 拉当前代码 → 算指纹 → 与页锚点比对 → 漂移则把页标 `stale`，进巡检/复核清单（接 RFC-025）。

- **指纹方案**：`--type done_time` 是"任务最近完成时间"（每天调度跑完就变），**不可做版本指纹**（会天天误报）。指纹用 `--type code` 拉回的**代码内容 hash**；若 fun-cli 的 `detail` 提供"代码最后修改时间"则优先用它（更轻）。**Step 0 由 codex 用 fun-cli 实跑核实**。
- **隔离原则**：`wiki_lint/graph/eval` 保持**离线纯本地**（无网络无凭证）；唯独 `wiki_freshness` 调 fun-cli。失效检测是**后台定期批量**跑，不在答疑或 lint 热路径。
- 这把 staleness 从"按时间过期"升级为"**按上游代码真的动了才过期**"。

### M4 — 答疑回源策略（L1 + L3）

**默认信库，触发式回源**（写进 pk AGENTS 答疑节 + 引擎 `02-workflows`）。回源 = 调 fun-cli 查 DataWorks 当前代码。

答疑决策树：
- 命中口径页 + `review:true` + 未 `stale` + 问的是语义/口径 → **用库，不回源**（最快、最常见，零 fun-cli 调用）。
- 命中但 `stale` / `review:false` 且关键 / 问"当前实现/最新值" → **回源**（fun-cli 查代码）合并答 + 标 maintainer 复核。
- 未命中 → 回源（先 `meta table search` 定位表、`field list` / `follow` 查字段血缘）+ 登记 source-gap。

**L3 人控**：回源发现口径变了，**永不自动写正本**——标复核，由 maintainer 梳理 + 背书（接 trust loop）。

## 真实摩擦来源

机制类，证据具体：本会话初始化 knowledge-pk（要把 DataWorks 代码知识化）时，用户连续追问暴露三处机制缺口——(a) 实测问"收款渠道 jazz/ep 在哪张表"库无承载页型答不了；(b) 代码会变而库快照无失效检测、只能靠时间阈值粗判；(c) 答疑无回源 DataWorks 当前代码的约定与通道。fun-cli skill 的出现使访问层落地可行（凭证已封装）。

## 验证方式

- **M1**：pk `.wiki-profile.json` 加 `asset-mapping` 后 `wiki_lint --root <pk>` exit 0；写一页"收款渠道"映射过校验；模拟答"jazz/ep 在哪张表"能命中该页。
- **M2**：`02-workflows` / AGENTS 改动后 `wiki_lint --check-docs` 不破 doc-consistency；方法论可指导一次真实 ingest。
- **M3**：fixture——锚点指纹未变 → 不标 stale；指纹变（mock fun-cli 输出）→ 标 stale 进清单；非数仓表 / fun-cli 不可用 → 优雅降级（warning 非 crash）。真实库 smoke：`wiki_freshness` 对一张真实 `edw` 表调 fun-cli 拉 code 成功。
- **M4**：答疑路径验证——命中未 stale 页时**不触发 fun-cli 调用**；命中 stale/缺失时触发回源。
- **回归**：012~026 全套过；`wiki_lint/graph/eval` 仍离线可跑（无 fun-cli 依赖）。

## 替代方案

- **每天爬代码自动重写知识库**：反模式——把库降级成代码劣质镜像，自动搬运冲掉人工梳理 + 背书，代码无关变更制造海量噪音。**放弃**。
- **纯手动定期更新**："人来梳理入库"对（保留为 L3），但"靠人发现哪些代码变了"会漏。**部分放弃**（保留人控 ingest，失效检测交给 M3 机器）。
- **知识库自连 DataWorks API + 自管凭证**：违"不存凭证"红线、让知识库越界。**放弃**，统一走 fun-cli（凭证已封装）。
- **`asset-mapping` 直接进引擎 BASE_SCHEMA**：污染 personal 等非数仓实例。**放弃**，走 profile（M1）。
- **失效检测并入 wiki_lint/eval**：会把网络/凭证依赖污染进离线纯本地工具。**放弃**，隔离到独立 `wiki_freshness.py`。

## 影响范围

- **引擎**：`wiki-design/02-workflows.md`（代码梳理方法论 + 传导口径 + 答疑回源约定）；新 `scripts/wiki_freshness.py`（L2，调 fun-cli）；`scripts/wiki_common.py`（若锚点字段需 schema 校验支持，复用 RFC-008 `extra_optional_fields`）；`scripts/README.md`；`tests/`。
- **实例 knowledge-pk**（apply 时，非引擎 targets）：`.wiki-profile.json`（`asset-mapping` 页型）、`AGENTS.md`（梳理方法论 + 答疑回源）、示例 asset-mapping 页。
- **依赖**：本机安装并登录 `fun-cli`（M3/M4 运行时）；离线工具不受影响。
- **不改**：core BASE_SCHEMA 8 类、`schema_version`（profile overlay）、hard/soft redact、非 dropbox 扫描范围。

## Apply 拆分建议

- **TASK-A（M1+M2）**：pk profile `asset-mapping` 页型 + 示例页 + 方法论/传导口径写进 02 + pk AGENTS。不依赖 fun-cli，可先落。
- **TASK-B（M3）**：代码锚点字段 + `wiki_freshness.py` + fun-cli 接入 + fixture/真实 smoke。依赖 fun-cli。
- **TASK-C（M4）**：答疑回源策略进 pk AGENTS + 02。
- 顺序 A → B → C；A 落地即可让 pk 答 jazz/ep 类问题，B/C 补失效检测与回源。

## Review by codex · 2026-06-22

结论：需修改。

### 阻塞点

1. **M3 fun-cli 实际输出未核实，接口字段不能进入 accepted spec。**
   - 我本地确认 `fun-cli` 存在，`fun-cli meta table get --help` 明确支持 `--type detail/code/field/done_time/online_source`。
   - 帮助文本确认 `done_time=最近产出完成时间`，不是代码版本时间，不适合作为代码版本指纹；这一点 RFC 判断正确。
   - 但当前 `fun-cli auth status` 返回“当前未登录”，对真实表 `phl_data.dwd_fact_debt_detail_info_snp` 分别执行 `--type detail/code/done_time --output json` 都失败，错误为“登录凭据已过期，请先执行 fun-cli auth login”。因此我无法核实：
     - `--type code` 返回的是纯字符串、对象、数组还是多任务结构；
     - 稳定可 hash 的代码字段路径是什么；
     - `detail` 中是否有“代码最后修改时间”或等价字段；
     - 错误码 / stderr / 空结果在脚本中应如何归一为 warning。
   - Path A 需要在 RFC 中补一段“fun-cli 输出契约（钉死）”：真实命令、脱敏后的样例 shape、代码内容字段路径、detail 是否存在代码修改时间字段、不可用时的结构化 warning 行为。

2. **代码指纹算法还没钉死。**
   - 当前写法“若 detail 提供代码最后修改时间则优先用它，否则 hash code”仍是分支性描述，TASK 无法写出确定 fixture。
   - 建议明确：
     - `fingerprint_version`，例如 `dw-code-v1`；
     - `fingerprint_source`，例如 `code_sha256` 或 `code_modified_at`；
     - 若用代码内容 hash，输入字节如何规范化：UTF-8、换行归一为 LF、是否 strip 尾部空白、多个 code block/任务如何排序和拼接；
     - hash 存储格式，例如 `sha256:<hex>`；
     - `dataworks_ref` 的稳定格式，例如 `table:<project>.<table>` 或 `task:<project>/<task_id>`，不要让表名和任务标识混在一个裸字符串里。
   - 如果 `detail` 真有“代码最后修改时间”，也要说明它是否只在代码变更时变化；否则不能优先于 code hash。

3. **“检测失效不自动重写”与“漂移则把页标 stale”冲突。**
   - RFC 开头原则写“检测失效不自动重写、机器筛人来判”，但 M3 写 `wiki_freshness.py` 漂移后“把页标 stale”。这会自动修改正本 frontmatter，等价于机器写库。
   - 建议改为默认只读：输出 freshness report / warning / review_queue 建议，不直接改 `status`；若确实需要写回，必须是显式 `--apply-stale` 或由 maintainer 在 TASK 中人工 apply，并记录 Execution log。

### 逐项判断

1. **M1 asset-mapping 走 pk `.wiki-profile.json`：部分同意。**
   - 方向正确：RFC-008 当前 profile 支持新增 page type、required/optional fields、给 base/extra type 加 extra optional fields；把 `asset-mapping` 放 pk profile 而不是 BASE_SCHEMA，符合“只增不改 base”。
   - 该页型能支撑“业务词 -> 表字段”答疑的主链路：`business_concept` 命中业务词，`physical_table/physical_field` 给物理落点，`value_mapping/caveats` 解释枚举和边界，正文可承载示例。
   - 需在 RFC/TASK 中钉死 profile 最小形态：`type`、`id_prefix`、`dir`、required/optional fields。建议 `id_prefix` 用 2-5 小写字母且不撞 base，例如 `asm`；目录用 `wiki/asset-mappings`。
   - 非阻塞建议：`lineage_upstream` 不要和 `related_ids` 双轨；血缘关系先用 `related_ids`，显示/说明放正文。`value_mapping` 若是复杂枚举，建议正文表格为主，frontmatter 只放可检索的轻量字段；否则 YAML 类型校验目前不会管结构质量。
   - 非阻塞建议：为业务词检索加 `business_aliases` 或正文“别名/同义词”约定，否则“收款渠道/还款渠道/支付渠道”这类问法仍可能只靠全文检索质量。

2. **M3 代码锚点指纹：需修改。**
   - `done_time` 不适合作版本指纹已由 fun-cli help 佐证。
   - 但 `--type code` 的真实输出和 `detail` 的可用时间字段未验证，不能 accept。
   - `wiki_freshness.py` 的默认写入行为也需改为只读报告，避免违背人控 trust loop。

3. **`wiki_freshness.py` 独立脚本隔离外部依赖：同意。**
   - 不把 fun-cli / 网络 / 凭证依赖放进 `wiki_lint.py` / `wiki_graph.py` / `wiki_eval.py` 是正确边界。
   - 建议明确 `wiki_freshness.py` 只在显式运行时 import / subprocess 调用 fun-cli；离线工具测试中应断言没有 fun-cli 依赖。
   - fun-cli 不可用、未登录、无权限、表不存在时应输出 warning + 非 2 崩溃退出；是否 exit 0/1 需要在 RFC 中钉死。我的建议：运行成功但有 freshness drift / auth warning 仍 exit 0，脚本自身参数/配置错误 exit 2；CI gate 另用 `--check` 决定是否把 drift 变成 exit 1。

4. **M4 答疑回源策略：通过，有非阻塞建议。**
   - “默认信库 + 三触发回源”可落到 AGENTS，不需要识别“请求来源”，只需要看问题语义和命中页面状态。
   - 建议把触发写成内容/状态规则：出现“当前实现/最新/代码里怎么写/字段从哪来/血缘/表字段/没命中/stale/review:false”才回源；普通业务定义、已背书未 stale 的口径页不回源。
   - “未命中 -> 回源”需加范围：仅 DataWorks/表/字段/代码/口径类问题回源；非数仓问题未命中时应回答库内无依据，不应无条件调用 fun-cli。

5. **gate 自检：通过。**
   - 真实摩擦来源具体，来自 knowledge-pk 初始化和“收款渠道 jazz/ep 在哪张表”这类可复现问题。
   - 验证方式覆盖 M1/M2/M3/M4 和离线回归方向，但 M3 需要在 fun-cli 输出契约钉死后才能作为可执行验收。

### 非阻塞建议

- `targets` 当前列了 `scripts/wiki_common.py`，但如果 M1 只用 pk profile 新增 `asset-mapping`，引擎 `wiki_common.py` 未必需要改；除非要给 base 类型统一加代码锚点字段。建议在 Revision 中明确 TASK-A 是否真的改 `wiki_common.py`。
- TASK 拆分 A/B/C 合理。A 不依赖 fun-cli，可先落 profile + 示例页 + 方法论；B 依赖 fun-cli 登录和输出契约；C 是 AGENTS/流程约定。
- M2 的“血缘链用 related_ids”是合理 MVP，但建议在示例页中明确 `related_ids` 方向：当前页 -> 上游定义点，避免 graph 中 in/out 解读反了。

## Decision · by claude（Path A）

codex verdict: **需修改**。用户拍板：先落 M1+M2，M3+M4 待接口核实（fun-cli `--type code` 契约现无法实跑——codex auth 过期、本机亦未登录；且血缘"不一定准"）。**RFC-027 部分 accepted：M1+M2 accepted、M3+M4 deferred。** 吸收 codex 全部建议。

### Accepted：M1 + M2（落 TASK-A，零外部接口依赖）

**M1 `asset-mapping` profile（钉死，pk `.wiki-profile.json`）**

- `type=asset-mapping`；`id_prefix=asm`；`dir=wiki/asset-mappings`。
- required（base 之外）：`business_concept`、`physical_table`。
- optional：`physical_field`、`business_aliases`（同义词，给业务词检索；如"收款渠道/收款方式/支付渠道"）。
- **删除 frontmatter `lineage_upstream`**（不与 `related_ids` 双轨）；血缘只用 `related_ids`，方向 **当前页 → 上游定义点**。
- `value_mapping`（枚举 `jazz=…/ep=…`）、`caveats`、血缘说明 → **正文**（frontmatter 只放轻量可检索字段；YAML 不校验结构质量）。
- **不加代码锚点字段**（属 M3 deferred）。
- 正文骨架：物理落点 / 取值映射（表格）/ 血缘上游 / 坑·适用边界 / 来源。
- **引擎 `wiki_common.py` 不改**（纯 pk profile）；TASK-A 引擎改动仅 `02-workflows.md`（+ `scripts/README.md` 若需）。

**M2 方法论 + 传导口径**

- 代码梳理 7 维 + 反面约束 → `02-workflows`（通用）+ pk AGENTS（引用 + 特定）。
- 传导口径：定义点唯一 / 下游记增量 / `related_ids` 血缘链（当前页→上游）/ source-gap 占位 / 同名不同口径 → `open-question`｜`decision`。
- **血缘权威性（用户决策）**：人工 `related_ids` 是血缘**正本**；**fun-cli / DataWorks 数据地图的自动血缘"不一定准"，仅作 ingest 时人工参考/交叉校验，不自动写 `related_ids`、不自动维护**。

### Deferred：M3 + M4（门槛满足后补 Decision 钉死）

1. fun-cli 登录后**实跑核实** `meta table get --type code` 输出契约：返回 shape、可 hash 的代码字段路径、`detail` 是否有"代码最后修改时间"、未登录/无权限/表不存在的结构化归一。
2. 指纹算法钉死：`fingerprint_version=dw-code-v1`、`fingerprint_source`（`code_sha256` 或 `code_modified_at`，后者须确认只随代码变更而变）、内容 hash 规范化（UTF-8 / LF / strip 尾空白 / 多 code block 排序拼接）、存储 `sha256:<hex>`、`dataworks_ref` 格式（`table:<project>.<table>` / `task:<project>/<id>`，不混裸串）。
3. `wiki_freshness.py` **默认只读**（输出 freshness report / review_queue 建议，**不改 frontmatter `status`**——修复 codex 阻塞③"检测失效不自动重写"自相矛盾）；写回需显式 `--apply-stale` 或 maintainer 人工 apply。exit 码：drift / auth warning 仍 exit 0；脚本参数/配置错 exit 2；CI 用 `--check` 把 drift 升 exit 1。离线工具测试断言无 fun-cli 依赖。
4. M4 回源触发写成**内容/状态规则**（命中"当前实现/最新/代码里怎么写/字段从哪来/血缘/表字段"，或页面 `stale`/`review:false`/未命中 才回源）；"未命中 → 回源"**限数仓/表/字段/代码/口径类问题**，非数仓问题未命中答"库内无依据"、不调 fun-cli。
5. 血缘自动查**不进** M3/M4 正本路径（见血缘权威性）；若将来用数据地图接口做血缘参考校验，需该接口契约核实 + 仅产出建议、不自动写。

Apply：**TASK-A（M1+M2）现在落**；TASK-B（M3）/ TASK-C（M4）待门槛。frontmatter `targets` 中 `scripts/wiki_freshness.py`、`scripts/wiki_common.py` 属 deferred，TASK-A 不触及。
