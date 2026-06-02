---
id: task_20260602_012
title: Apply RFC-012 — 实现知识可信度信号（lint 2 warning + graph in/out degree + insights 健康度段 + 文档同步）
author: claude
executor: codex
status: done
type: apply
created: 2026-06-02
updated: 2026-06-02
related_rfcs: [RFC-012]
---

# TASK-012: Apply RFC-012 — 实现知识可信度信号

## 目标

把 RFC-012「形态 A 知识可信度信号」落到工具链：lint 新增 `STALE_PAGE` / `UNVERIFIED_HIGH` 两条 **warning**，wiki_graph 新增 `in_degree` / `out_degree` 计算与 insights「知识健康度」段，并同步 schema 文档。全部只提示、不阻断，不改 core page schema。

## 前置条件

- RFC-012 status: accepted（已满足，Decision by claude 2026-06-02）。
- working tree clean（除本 task 文件）。
- 环境：`conda run -n py312 python`（Python 3.12，PyYAML 已装）。

## 强约束

1. **不改 core page schema / frontmatter 契约**：`confidence` enum、core 必填字段、稳定 ID、source 单主键、canonical 规则、append-only 一律不动。本 task 只扩展工具链 policy 契约。
2. **新增 code 全是 warning**：`STALE_PAGE` / `UNVERIFIED_HIGH` 注册到 `BASE_SCHEMA["error_level"]` 为 `"warning"`，**不得影响 lint 退出码**（exit 1 只由 error 触发）。
3. **staleness 判定逻辑单点实现**：lint 和 graph 都要判断"某页是否 stale"，必须抽到 `wiki_common.py` 一个共享函数（如 `is_stale(doc_or_node, now)`），两处调用同一实现，禁止各写一份。
4. **staleness_days 是 BASE_SCHEMA 常量，不走 profile**：不新增任何 profile 字段 / PROFILE_* 校验。profile extra type 不在阈值表 → 不检查 STALE_PAGE。
5. **degree 口径严格按 RFC §3**：有向边（`source_ref` / `related` / `supersedes` / `wikilink`）贡献 in/out；无向边（`co_source`）只入总 `degree`，不入 in/out。`degree` 既有口径与值保持不变（零回归）。
6. **派生层确定性**：in/out degree、insights health 段输出按确定序（sort_keys / 固定 render 顺序）；沿用既有原子写。
7. **零数据改动**：脚本只读 `knowledge/**` / 各实例数据 + 写派生层；不修改任何现有页面 frontmatter。
8. **测试可控时间**：lint 的"今天"基准须可注入（加隐藏参数 `--now YYYY-MM-DD`，默认 `date.today()`），以便 staleness 边界确定性测试。

## 步骤

> Step 0 先做 spec-review：通读本 spec，若发现与现有代码结构（`wiki_lint.check_page` / `wiki_graph.assign_degree` / `render_insights` / edge 的 `undirected` 标志 / node 是否携带 frontmatter 字段）冲突或歧义，先在 Execution log 提出再动手，不要带着歧义实现。

1. **`wiki_common.py`**
   - `BASE_SCHEMA` 新增 `"staleness_days"`：`{decision:120, synthesis:120, comparison:120, "open-question":120, topic:365, entity:365}`（`source` / `query` / 其它不列 = 不检查）。
   - `error_level` 新增 `"STALE_PAGE": "warning"`、`"UNVERIFIED_HIGH": "warning"`。
   - 新增共享函数 `staleness_threshold(page_type, schema)`（无则返回 None）和 `is_stale(page_type, status, last_verified, now, schema)`：`status=="active"` 且 type 有阈值 且 `(now - last_verified).days > 阈值` → True。`last_verified` 缺失/非法 → 不判 stale（交给既有 DATE_FORMAT 校验）。

2. **`wiki_lint.py` — `STALE_PAGE`**：在 page 校验段（已有 `check_date_field` 之后）调用 `is_stale(...)`，True 则 `add_issue(STALE_PAGE, warning)`，message 含"距上次核实 N 天 / 阈值 M 天"，hint 含"复核后更新 last_verified，或下调 confidence / 改 status: stale"。`--now` 注入今天。

3. **`wiki_lint.py` — `UNVERIFIED_HIGH`**：条件 `status=="active"` 且 `type ∉ {source, query}` 且 `confidence=="high"` 且 `review is False` → warning。文案严格用 RFC §4："高置信但未经人工确认：确认后置 `review: true`，否则考虑降为 medium。"

4. **`wiki_graph.py` — in/out degree**：新增有向度数计算（无向边 `co_source` 跳过，依据 edge 的 `undirected` 标志或 `type=="co_source"`），写入每个 node 的 `in_degree` / `out_degree`。既有 `degree` 不变。确保 node 携带 `type/status/confidence/review/last_verified`（用于 health 段；若未携带则在 build node 时从 frontmatter 补，只读）。

5. **`wiki_graph.py` — insights「知识健康度」段**：在 `render_insights` 追加，复用 `is_stale`（注入 graph 运行时的 now）。render 顺序固定：
   1. trust 概览一行：`verified / unverified-high / stale / orphan / total` 计数（verified = active 且 review:true 且未 stale；orphan = in_degree==0 且 out_degree==0）。
   2. stale 优先列表：排序键 `(-in_degree, -out_degree, id)`。
   3. high-unverified 列表。
   4. 不重复输出 orphan/hub 长列表（明细仍由既有 `Isolated Nodes` / `High Centrality Hubs` 段给出），仅概览给计数。

6. **文档同步**
   - `scripts/README.md`：error code 表加 `STALE_PAGE` / `UNVERIFIED_HIGH`（级别 warning + 触发条件）；wiki_graph 段补 in/out degree + 健康度段说明。
   - `knowledge/.wiki-schema.md`：补 `review` 语义表（false=AI 草拟未确认 / true=人已背书）+ trust 派生层说明 + staleness 阈值表 + "负反馈先撤 review" 不变量。
   - `wiki-design/02-workflows.md`：补"复核/确认"动作（正反馈 `review:true + last_verified=今天`；负反馈先撤 `review`）。

7. **测试 / fixture**（放既有测试目录，沿用现有测试风格）
   - **related 方向性 fixture**（codex re-review #2）：① 单向 related（仅 A `related_ids:[B]`）→ 断言 `B.in_degree>=1, A.out_degree>=1, A.in_degree(来自该边)=0`；② 双向 related（A、B 互写）→ 断言两者 in/out 各计一次。固定现状"不自动补反向边"。
   - **STALE_PAGE 触发集合**：active 超期（报）；active 未超期（不报）；阈值边界（用 `--now` 精确卡 =阈值 不报 / >阈值 报）；`stale/archived/draft/redirect`（不报）；`source/query`（不报）；profile extra type（不报）。
   - **UNVERIFIED_HIGH**：active+high+review:false（报）；review:true（不报）；confidence:medium（不报）；draft/redirect/stale/archived/source/query（不报）。
   - **零回归**：`degree` 既有值不变；现有引擎实例数据跑 lint 无新 error。
   - 至少各覆盖一个 code。

8. **跑验证（见下）→ commit**（一个或多个语义清晰的 commit；最终 working tree clean）。

## 验证

```bash
ENGINE=/Users/zhangjunwu/workspace/llm-wiki/llm-wiki
PY="/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python"

# 1) 引擎实例：无新 error（warning 可有），退出码 0
cd $ENGINE && $PY scripts/wiki_lint.py --root knowledge
echo "exit=$?"   # 期望 0

# 2) personal 实例：5 页均 high+review:false+active → 预期 5 条 UNVERIFIED_HIGH，0 error
$PY scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/knowledge/personal --json \
  | $PY -c "import sys,json;d=json.load(sys.stdin);print('errors',len(d['errors']),'unverified_high',sum(1 for w in d['warnings'] if w['code']=='UNVERIFIED_HIGH'))"
# 期望 errors 0 / unverified_high 5

# 3) staleness 边界（用 --now 注入未来日期，使现有页超期）
$PY scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/knowledge/personal --now 2027-12-31 --json \
  | $PY -c "import sys,json;d=json.load(sys.stdin);print('stale',sum(1 for w in d['warnings'] if w['code']=='STALE_PAGE'))"
# 期望 stale > 0（全部 active topic/synthesis 超 365/120 天）

# 4) graph：in/out degree 字段存在 + health 段输出
$PY scripts/wiki_graph.py --root /Users/zhangjunwu/workspace/obsidian/knowledge/personal --json \
  | $PY -c "import sys,json;d=json.load(sys.stdin);n=next(iter(d['nodes']));print('has in/out', 'in_degree' in d['nodes'][n] and 'out_degree' in d['nodes'][n])"
# 期望 has in/out True

# 5) 测试套件全绿
cd $ENGINE && $PY -m pytest -q   # 或既有测试入口
```

## 完成后报告格式

executor 完成后贴在 Execution log 段：

- Step 0 spec-review 结论（含发现的歧义/偏离及处理）
- 每步实际改动文件 + 关键代码位置
- 验证 1~5 实际输出
- 新增/修改测试清单 + 全绿截图或输出
- commit sha（逐个）
- 偏离或异常

## Execution log by codex · 2026-06-02

### Step 0 spec-review 结论

- 结论：spec 可执行，未发现需要停止实现的阻塞歧义。
- 代码结构契合点：
  - `wiki_lint.py` 没有名为 `check_page` 的函数；实际 wiki page 校验入口是 `validate_wiki_docs()`。两条 warning 已插入在 `created/updated/last_verified` 的 `check_date_field()` 之后，符合“date 校验后插入”的意图。
  - `wiki_graph.py` 的 edge 当前不保存 `undirected` 字段；现有唯一无向边是 `relation == "co_source"`，实现按该 relation 跳过 in/out，保留 `degree` 既有算法。
  - `build_nodes()` 原本已有 `type/status`，缺 `confidence/review/last_verified`；本 task 已补入 node，只读 frontmatter。
  - `is_stale()` 抽到 `wiki_common.py` 不产生循环依赖：`wiki_common` 不 import lint/graph，lint 和 graph 单向 import common。
- 验证脚本注意点：
  - 本地 shell 是 zsh，spec 中 `PY="conda run ..."` 后直接 `$PY` 需要 bash 语义；zsh 下会把整串当命令路径。正式验证用 `bash -lc` 重跑。
  - 验证 #4 原命令把 `d["nodes"]` 当 dict 使用，但 graph-data 中 `nodes` 是 list；原命令会失败。已原样记录失败，并补跑等价修正版：取 `d["nodes"][0]` 检查 `in_degree/out_degree`。

### 实际改动

- `.gitignore`
  - 新增 `tests/` 白名单，确保 task fixture 可版本管理；继续忽略 `tests/__pycache__/`。
- `scripts/wiki_common.py`
  - `BASE_SCHEMA` 新增 `staleness_days` 常量：`decision/synthesis/comparison/open-question=120`，`topic/entity=365`。
  - `error_level` 新增 `STALE_PAGE` / `UNVERIFIED_HIGH`，均为 warning。
  - 新增 `parse_ymd_date()` / `staleness_threshold()` / `staleness_age_days()` / `is_stale()`。
- `scripts/wiki_lint.py`
  - `ERROR_CODES` 新增两条 warning code。
  - 新增隐藏参数 `--now YYYY-MM-DD`，默认当天。
  - `validate_wiki_docs()` 在日期校验后调用 `add_trust_warnings()`。
  - `STALE_PAGE`：仅 `status: active` 且 type 有阈值且 `age > threshold`。
  - `UNVERIFIED_HIGH`：`status: active` 且 `type ∉ {source, query}` 且 `confidence: high` 且 `review is False`。
- `scripts/wiki_graph.py`
  - node 补 `confidence/review/last_verified/in_degree/out_degree`。
  - `assign_degree()` 保持既有 `degree` 算法不变，额外计算 in/out；`co_source` 不进 in/out。
  - `graph-insights.md` 新增「知识健康度」段：概览 → stale priority → high unverified。
- 文档同步：
  - `scripts/README.md`：error code 表、graph in/out degree、健康度段。
  - `knowledge/.wiki-schema.md`：review 语义、负反馈撤背书、staleness 阈值、trust 派生层。
  - `wiki-design/02-workflows.md`：健康检查项与“复核 / 确认”流程。
  - `knowledge/wiki/topics/toolchain-usage.md`：工具链知识页同步 warning 与 graph degree/health 说明。
- 测试：
  - 新增 `tests/test_task_012.py`，使用临时实例 + 标准库 unittest。

### 验证输出

1. 引擎实例 lint，无新 error，exit 0：

```text
wiki-lint instance root: /Users/zhangjunwu/workspace/llm-wiki/llm-wiki/knowledge · profile: base
错误: 0 · 警告: 4
exit=0
```

4 条 warning 均为本仓库现有 4 页 `UNVERIFIED_HIGH`，符合新 warning 语义，不影响 exit。

2. personal 实例 lint，预期 0 error / 5 UNVERIFIED_HIGH：

```text
errors 0 unverified_high 5
```

3. personal 实例未来日期 staleness，预期 stale > 0：

```text
stale 5
```

4. graph in/out degree 字段：

原 spec pipeline 因 `conda run | conda run` stdin 与 `nodes` list/dict 断言问题失败，已补跑修正版：

```text
has in/out True
```

5. 测试套件：

```text
$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m pytest -q
/Users/zhangjunwu/soft/anaconda3/envs/py312/bin/python: No module named pytest
```

py312 当前没有 pytest。按本 task 新增的标准库 unittest fixture 补跑：

```text
test_co_source_keeps_degree_but_skips_in_out ... ok
test_related_edges_are_directed ... ok
test_stale_and_unverified_trigger_sets ... ok

Ran 3 tests in 0.293s
OK
```

额外验证：

```text
$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m py_compile scripts/wiki_common.py scripts/wiki_lint.py scripts/wiki_graph.py tests/test_task_012.py
# exit 0

$ git diff --check
# exit 0

$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --check-only
错误: 0 · 警告: 4
```

### 新增/修改测试清单

- `Task012LintTest.test_stale_and_unverified_trigger_sets`
  - 覆盖 active 超期报、阈值边界不报、stale/archived/draft/redirect 不报、source/query 不报、profile extra type 不报。
  - 覆盖 `UNVERIFIED_HIGH` 的 active+high+review:false 报、review:true/medium/status/type 排除不报。
- `Task012GraphTest.test_related_edges_are_directed`
  - 覆盖 A→B 单向 related 不自动补 B→A，以及 A/B 互写时双方 in/out 各计一次。
- `Task012GraphTest.test_co_source_keeps_degree_but_skips_in_out`
  - 覆盖 `co_source` 保留总 `degree`，但不计入 in/out；同时 source_ref 计入 in/out。

### commit sha

- 本 commit（`[apply rfc-012] implement trust signals`；最终 sha 见执行者报告）

### 偏离或异常

- 验证 #2/#3 原 `conda run | conda run` pipeline 在本机出现下游 JSONDecodeError / 上游 BrokenPipe；改为先保存 JSON 再解析，结果符合预期。
- 验证 #4 原断言命令把 `nodes` list 当 dict；补跑 `d["nodes"][0]` 版本，结果符合预期。
- py312 没有 pytest，因此 `python -m pytest -q` 不可用；已用标准库 unittest 覆盖本 task fixture。

## Evaluation by claude · 2026-06-02

**Verdict: PASS。** 独立复跑全部验证，与 Execution log 一致；实现口径、零回归、触发集合均符合 RFC-012。

### 独立复跑（evaluator 亲自跑，未只信报告）

| 验证 | 结果 |
| --- | --- |
| V1 引擎实例 lint `--check-only` | exit 0，errors 0（零回归核心通过） |
| V2 personal `--json` | errors 0 / `UNVERIFIED_HIGH` **5**（5 页均 active+high+review:false） |
| V3 personal `--now 2027-12-31` | errors 0 / `STALE_PAGE` **5** |
| V4 graph `--json` | 5 节点全部含 `in_degree`/`out_degree`；degree=in+out（无 co_source，符合预期） |
| V5 `unittest tests.test_task_012` | Ran 3 tests OK |

### 核查点逐项

1. **零回归**：引擎 lint exit 0；`assign_degree` 既有 degree 算法（source/target 各 +1）保留不变（diff 确认 + unittest `test_co_source_keeps_degree_but_skips_in_out` 覆盖）。
2. **degree 口径（RFC §3）**：`if edge.relation != "co_source": out[source]+=1; in[target]+=1` —— 无向边只入 degree、不入 in/out，口径正确。
3. **两条 warning 触发集合（RFC §2/§4）**：`STALE_PAGE` 仅 active+有阈值 type；`UNVERIFIED_HIGH` 仅 active 且 type∉{source,query}。unittest 覆盖 stale/archived/draft/redirect/source/query/extra type 全不报。
4. **insights health 段（RFC §6）**：render 顺序「概览→stale→high-unverified」、stale 排序键 `(-in_degree,-out_degree,id)`、orphan=in&out 均 0、不重复 orphan/hub 长列表——全部符合。
5. **is_stale 单点共享（强约束 #3）**：抽到 `wiki_common`，lint 与 graph 共用，无循环依赖。
6. **related 方向性 fixture（codex re-review #2）**：单向 A→B 不补反向、双向各计一次，已钉死。
7. **文档同步**：README error code 表 + .wiki-schema.md（review 语义/负反馈撤背书/staleness/trust）+ 02-workflows.md + toolchain-usage.md 工具链页，齐全。
8. **--now 注入**：实现，staleness 边界可测。

### 偏离评估（均合理，已诚实记录）

- **pytest 不可用 → 标准库 unittest**：py312 未装 pytest，非执行者过失；改用 unittest 反而更贴合本仓"零额外依赖"原则。接受。
- **spec 验证 #4 命令 list/dict bug**：是我 spec 的笔误（`nodes` 是 list 却按 dict 取），Codex 正确修正并记录。spec 缺陷，非实现缺陷。
- **`check_page` → `validate_wiki_docs`**：spec 里函数名是我推测，Codex 找到真实入口并说明。接受。

### Minor observations（不阻断 PASS，记此备后）

1. **toolchain-usage.md 改正文未 bump frontmatter `updated`**：该工具链知识页正文同步了新能力，但 `updated` / `last_verified` 仍是旧值。不违反 lint、不影响功能，但严格的知识卫生应在改内容时更新 `updated`。建议后续 bookkeeping 顺手补（或留待该页首次"复核"时一并更新）。
2. **pytest 环境缺失**：spec/README 若默认"跑 pytest"，未来会反复踩。建议二选一：py312 装 pytest，或把测试入口正式标准化为 `unittest`。Backlog 级，非本 task 范围。

### 结论

RFC-012 形态 A 闭环达成：`review` 语义激活、`STALE_PAGE`/`UNVERIFIED_HIGH` 上线、in/out degree 被依赖度、insights 健康度段全部落地，零 error、零回归。TASK-012 done 确认有效。
