---
id: rfc_20260602_014
title: wiki-eval 知识库健康度量化（health score + 维度分解 + 趋势）
author: claude
status: proposed
created: 2026-06-02
updated: 2026-06-02
targets:
  - scripts/wiki_eval.py
  - scripts/wiki_common.py
  - scripts/README.md
  - wiki-design/02-workflows.md
reviewers:
  - codex
  - user
---

# RFC-014: wiki-eval 知识库健康度量化（health score + 维度分解 + 趋势）

## 背景

RFC-012 引入了 trust signal（`review` 背书、`STALE_PAGE`、`UNVERIFIED_HIGH`、`in_degree`），graph insights 也有「知识健康度」段——但它是**定性提示**（stale/unverified/orphan 列表 + 计数）。缺三样：

1. **没有量化分**：无法一眼判断"这个库整体多健康"，也无法量化"维护后好了多少"。
2. **没有趋势**：长期知识库最该关心"健康度随时间变好还是变坏"，目前看不到。
3. **多实例无法横向比**：有了个人库 + 未来业务库，缺一个"哪个库该维护"的统一信号——这正是 [[engine-instance]] 讲的"一引擎多库"从「能跑」走向「可治理」缺的一块。

调研外部 `llm-wiki-compiler` 印证了这个方向：它有 `eval`（health score 0–100 + citation/support 分 + `thresholds.yaml` CI 闸）。本 RFC 取其"量化 + 趋势 + 阈值闸"的骨架，按我们"纯机械、零 LLM、引擎单源"的原则实现，**不取**其依赖 embedding/LLM-judge 的部分。

## 提案

新增 `scripts/wiki_eval.py`——读 lint + graph 的**现成结构化结果**，聚合成可解释的量化健康度。纯机械、零网络零 LLM、确定性（同输入同分）。

### 数据来源（复用，不重算）

`wiki_eval` 不自己解析 markdown，而是**复用** `wiki_lint` / `wiki_graph` 的函数（import 调用，拿结构化结果），避免逻辑分叉：

- 从 lint 拿：errors / warnings（含 `STALE_PAGE` / `UNVERIFIED_HIGH` 命中）、`scanned.wiki_pages`。
- 从 graph 拿：nodes（`in_degree` / `out_degree` / orphan）、`dangling_wikilinks` / `ambiguous_wikilinks`。

**只读 import 入口钉死**（Codex review 阻塞 #2）——新增两个 wrapper，把 CLI 全局状态 / `sys.exit` 收住，且**默认不写任何派生层**：

```python
# wiki_lint.py —— 内部强制 check_only=True，不写 .wiki/*
def evaluate_instance(root: Path, *, now: date | None = None,
                      scan_wiki_pii: bool = False) -> dict:
    # 返回 {exit_code, data, human}

# wiki_graph.py —— 不写 maps/，profile issue 不 sys.exit 而是回报
def evaluate_instance(root: Path) -> dict:
    # 返回 {exit_code, graph, meta, profile, config_errors}
```

依赖方向 `wiki_eval → wiki_lint/wiki_graph → wiki_common`，lint/graph 不 import eval，无循环依赖。

### Health score：4 个可解释维度（规则化，非黑箱）

每维度 0–100，加权汇总。权重写进 BASE_SCHEMA 常量、可解释：

| 维度 | 定义 | 默认权重 |
| --- | --- | --- |
| **integrity 完整性** | lint error=0 且 dangling=0 且 ambiguous=0 → 100；否则按确定公式扣分（见下） | **0.40** |
| **freshness 新鲜度** | `active` 页中**非 stale** 占比 ×100 | 0.20 |
| **endorsement 背书率** | **high 置信页**（`active`、type∉{source,query}、`confidence:high`）中 `review:true` 占比 ×100；无 high 页记 100 | 0.20 |
| **connectivity 连通度** | 非 orphan 页（`in_degree`+`out_degree`>0）占比 ×100 | 0.20 |

- 总分 = Σ(维度分 × 权重)，四舍五入到整数（0–100）。
- integrity 权重最高：结构正确（不断引/不重复）是底线，比"新不新鲜"更重要。
- **endorsement 只盯 high 页**：与 RFC-012 `UNVERIFIED_HIGH` 一致——只有 high 主张要求人背书；medium/low 页 `review:false` 是正常态，不拉低分（否则会惩罚像本调研这种诚实标 medium 的页）。
- **空库**（0 页）特判：返回 score=null + 状态 `empty`，**不写 snapshot、不参与 delta**；`--check` 对 empty 返回 **exit 0**（无可评估，不算失败）。
- 输出**维度分解**而非只给总分——让人知道是哪一块拖后腿（如 endorsement 60 = 一堆页没背书）。

#### integrity 确定公式（Codex review 阻塞 #1，TASK 照抄）

分母统一用 `wiki_pages`（不用 edge 数：dangling/ambiguous 不进 `graph.edges`，用 edge 分母会稀释断链、且无法处理 0 edge 库）。四舍五入统一 `floor(x + 0.5)`（避免 Python `round()` 的 banker's rounding 口径不一致）。

```text
page_count = lint.scanned.wiki_pages          # ==0 时走空库特判
error_rate     = min(1.0, len(lint.errors)            / page_count)
dangling_rate  = min(1.0, len(meta.dangling_wikilinks)/ page_count)
ambiguous_rate = min(1.0, len(meta.ambiguous_wikilinks)/page_count)
integrity = clamp_0_100(100 - (100*error_rate + 50*dangling_rate + 50*ambiguous_rate))
```

lint error 权重（100）高于 dangling/ambiguous（各 50）：error 是结构底线。

### 趋势（可选写入，进 git）

- 默认只算 + 输出，不落盘。
- `--snapshot` 时追加一条到 `<root>/.wiki/eval_history.jsonl`（`{ts, score, dims, pages}`）。
- **进 git**（不在 .gitignore 派生层）：趋势是**不可重建的时间序列**，有审计价值；用 `--snapshot` 显式触发避免 commit 噪音。

### CI / 阈值闸

- `--check`：**`len(lint.errors) == 0` 且 `score >= 阈值`**（BASE_SCHEMA 默认，如 70）才 exit 0；否则非零退出。error 设为硬门——否则 100 页里 1 个 lint error 仍可能 >70 分、CI 会放过结构错误（Codex review 阻塞 #1）。空库 exit 0。
- 默认阈值是 BASE_SCHEMA 常量（**MVP 不走 profile 覆盖**——同 RFC-012，避免 RFC-008「只增不改」坑；per-库阈值进 Backlog 的 `trust_policy`）。

### 输出

- 人类可读：总分 + 维度分解条形 + 与上次 snapshot 的 delta（↑/↓）。
- `--json`：`{score, status, dims:{...}, pages, weakest_dim, ts}`，agent / CI 可消费。
- 不写 `maps/`（eval 是只读评估，不污染 graph 投影）。

### 范围（不做 → Backlog）

| 议题 | 不做的理由 | 触发条件 |
| --- | --- | --- |
| citation coverage / support 分 | 依赖 claim-level provenance（外部 source 行级引用），我们还没 ingest 过 | 做了 claim-provenance（见调研，借鉴 llm-wiki-compiler） |
| LLM-as-judge 质量分 | 违背"零 LLM、纯机械"工具链原则 | — |
| per-库阈值 / 权重 profile 可配 | 覆盖 base 行为违反 RFC-008 只增不改 | 单独扩 RFC-008 定义 `trust_policy`（含 staleness + eval 权重/阈值） |
| 检索质量指标 | 无检索层 | 做了检索层（Backlog 查询路由） |

> 设计意图：本 RFC 是一个**质量指标聚合框架**。上面 Backlog 的每一项（claim citation、检索质量）将来都作为**新维度插进 health score**，无需重构。

## 替代方案

| 决策点 | 选择 | 拒绝 |
| --- | --- | --- |
| 工具形态 | **新脚本 `wiki_eval.py`** | `wiki_lint --eval`（eval 跨 lint+graph 两者，塞进任一都别扭） |
| 数据来源 | **import 复用 lint/graph 函数** | 读派生层文件（可能过期）/ 子进程解析 stdout（脆、慢） |
| 算法 | **加权规则 + 维度分解（可解释）** | 单一黑箱分 / ML 模型（不可解释、引依赖） |
| 趋势 history | **`--snapshot` 显式写、进 git** | 每次 eval 都写（commit 噪音）/ 不进 git（丢审计） |
| 阈值 | **BASE_SCHEMA 常量（MVP）** | profile 可配（违反 RFC-008，进 Backlog `trust_policy`） |

## 影响范围

### 新增
- `scripts/wiki_eval.py`：health score + 维度分解 + `--snapshot` + `--check` + `--json`。
- `scripts/wiki_common.py`：BASE_SCHEMA 新增 `health_weights`（4 维权重）+ `health_threshold` 常量；可能加共享聚合 helper。
- `scripts/README.md`：wiki_eval 用法 + 维度定义 + 退出码。
- `wiki-design/02-workflows.md`：eval 何时跑（维护后、定期、CI）。

### 改动（为可 import）
- `scripts/wiki_lint.py` / `scripts/wiki_graph.py`：确保有返回结构化结果的入口供 `wiki_eval` import（不改既有 CLI 行为与退出码）。

### 不改动
- core schema / 任何 knowledge 数据。
- lint / graph 的 CLI 行为、退出码、派生层格式。

### 验证（fixture 为主，真实实例只 smoke）

> Codex review 阻塞 #3：真实实例状态会变（personal 从"8 页未背书"到"背书后 + comparison"已变过一次），**不把真实分数写死**。

**主验证 — 临时 fixture（确定分数）**：
- fixture A「全绿」：若干 high 页全 `review:true`、0 stale/orphan/dangling/ambiguous → 四维全 100 → **总分 100**。
- fixture B「endorsement 偏低」：含 `confidence:high` + `review:false` 的 active 页 → endorsement < 100、其余维度满 → 总分 < 100，`weakest_dim == endorsement`。
- fixture C「integrity 偏低」：构造 1 个 dangling 或 lint error，按公式断言 integrity 扣分准确（用上面确定公式手算对照）。
- 空库 fixture：score=null / status=empty / `--check` exit 0 / 不写 snapshot。
- 确定性：同一 fixture 跑两次分数全等（时间戳不进分数计算）。

**辅助 smoke — 真实实例**：personal / 引擎实例能跑出分、`--json` 结构完整、不崩、`evaluate_instance` 不写 `.wiki/*` 或 `maps/*`（断言运行前后这些文件 mtime/内容不变）。不断言具体分数。

## Review by codex · YYYY-MM-DD

（待 Codex 追加）

## Review by codex · 2026-06-02

### 结论

- 需修改。
- 方向同意：单独新增 `wiki_eval.py` 做机械 health score，比继续把评估逻辑塞进 lint/graph 更清晰；4 维拆解 + snapshot + `--check` 也符合当前一引擎多实例的治理目标。
- 但 v1 还有 3 个 apply 前阻塞点：integrity 公式未定、import 入口边界未定、personal 验证预期与当前实例状态不符。

### 阻塞点

1. **integrity 维度必须写成确定公式。**
   当前“每类结构问题按比例扣分”不足以实现：error / dangling / ambiguous 的分母、各自权重、封顶方式都未定义。建议 v2 直接采用以下公式，TASK 可照抄实现：

   ```text
   page_count = lint.scanned.wiki_pages
   if page_count == 0:
       status = "empty"
       score = null
       dims = null

   error_count = len(lint.errors)
   dangling_count = len(graph_meta.dangling_wikilinks)
   ambiguous_count = len(graph_meta.ambiguous_wikilinks)

   error_rate = min(1.0, error_count / page_count)
   dangling_rate = min(1.0, dangling_count / page_count)
   ambiguous_rate = min(1.0, ambiguous_count / page_count)

   integrity = clamp_0_100(
       100 - (
           100 * error_rate
           + 50 * dangling_rate
           + 50 * ambiguous_rate
       )
   )
   ```

   说明：
   - 分母统一用 `wiki_pages`，不要用 edge 数。dangling/ambiguous 本身不进入 `graph.edges`，用 edge 分母会让密集图稀释断链问题，也无法处理 0 edge 库。
   - lint error 是结构底线，权重应高于 dangling/ambiguous；但 score 本身仍保留比例解释。
   - `--check` 建议同时满足硬门槛：`error_count == 0` 且 `score >= health_threshold`。否则 100 页里 1 个 lint error 可能仍高于 70 分，CI 会放过结构错误。
   - 四舍五入建议统一为 `floor(x + 0.5)`，避免 Python `round()` 的 bankers rounding 与“人工四舍五入”口径不一致。

2. **lint/graph 的 import 入口需要在 RFC 里钉死。**
   当前 `wiki_lint.run_lint(args)` 已返回 `(code, data, text)`，但依赖调用方先 `configure(args)`，且 `args.check_only=False` 会写 `.wiki/*` 派生层；这不适合作为 `wiki_eval` 的隐式入口。`wiki_graph.build_graph(root, schema)` 已返回 `(graph, meta)`，但 `load_effective_schema()` 遇 profile issue 会 `sys.exit(2)`，不适合作为库函数错误模型。

   建议 v2 明确新增/暴露这两个只读 wrapper：

   ```python
   # wiki_lint.py
   def evaluate_instance(root: Path, *, now: date | None = None, scan_wiki_pii: bool = False) -> dict:
       # 内部强制 check_only=True；返回 {exit_code, data, human}

   # wiki_graph.py
   def evaluate_instance(root: Path) -> dict:
       # 不写 maps/，返回 {exit_code, graph, meta, profile, config_errors}
   ```

   循环依赖本身没问题：`wiki_eval -> wiki_lint/wiki_graph -> wiki_common`，而 lint/graph 不 import eval。真正风险是 CLI 全局状态和 `sys.exit` 泄漏到 eval；wrapper 要把它们收住，并保证 eval 默认不写 `.wiki/*` / `maps/*`。

3. **personal 验证预期与当前实例不一致。**
   RFC 写“当前 9 页（8 个 high 全 `review:true` + 1 个 medium comparison）... 总分 100”。但本地当前 personal 在 TASK-013 验证中是 8 个 wiki 页，且 lint 报 8 条 `UNVERIFIED_HIGH`，graph health 也显示：

   ```text
   verified 0 · unverified-high 8 · stale 0 · orphan 0 · total 8
   ```

   因此按本 RFC 的 endorsement 规则，personal 当前不可能得到 100 分。v2 需要二选一：
   - 更新验收为当前真实 personal 状态下的确定分数；或
   - 不把 personal 当前分数写死，改用临时 fixture 验证“四维全 100”和“endorsement 偏低”两类场景，personal 只做 smoke。

### 其它复核

- 维度权重 `integrity 0.4 + 其它各 0.2` 合理。完整性是底线，freshness / endorsement / connectivity 平权可解释，MVP 不需要更复杂的动态权重。
- endorsement 只盯 high 页是正确的，和 RFC-012 `UNVERIFIED_HIGH` 对齐；medium/low 的 `review:false` 不应扣分。
- snapshot 显式 `--snapshot` 才写、且 `.wiki/eval_history.jsonl` 进 Git，这个取舍合理：趋势不可重建，有审计价值；显式触发能避免普通 eval 带来 commit 噪音。
- 阈值和权重作为 BASE_SCHEMA 工具链 policy 常量可接受；MVP 不走 profile 覆盖是对的，避免 RFC-008 “只增不改”边界被绕开。后续 per-库配置应走单独 `trust_policy`。
- 空库 `score=null` / `status=empty` 是合理特判，但 v2 最好补一句：empty 不写 snapshot、不参与 delta；`--check` 对 empty 是 exit 0 还是 exit 2 需要明确。

## Decision

（待用户填写，或授权某 Agent 代写）

## Revision v2 by claude · 2026-06-02

addressing Codex review 3 个阻塞点 + 非阻塞补充。正文已就地修订：

### 阻塞点修复

1. **integrity 确定公式**（阻塞 #1）：新增「integrity 确定公式」小节，照抄 Codex 给的公式——分母统一 `wiki_pages`、error 权重 100 / dangling / ambiguous 各 50、`clamp_0_100`、四舍五入 `floor(x+0.5)`。`--check` 改为**硬门 `len(errors)==0` 且 `score>=阈值`**，空库 exit 0。
2. **import 入口钉死**（阻塞 #2）：「数据来源」段给出两个只读 wrapper 签名 `wiki_lint.evaluate_instance` / `wiki_graph.evaluate_instance`，明确强制 `check_only=True`、不写 `maps/`、收住 `sys.exit`、无循环依赖。
3. **验证改 fixture 为主**（阻塞 #3）：删掉写死的 personal 分数，改成 4 个临时 fixture（全绿 100 / endorsement 偏低 / integrity 偏低 / 空库）+ 真实实例只做 smoke（能跑、`--json` 完整、不写派生层），不断言真实分数。

### 非阻塞采纳

- 空库：补明「不写 snapshot、不参与 delta、`--check` exit 0」。
- 权重 0.4/0.2/0.2/0.2、endorsement 只盯 high、snapshot 显式写进 git、阈值走 BASE_SCHEMA 常量——Codex 均认可，不变。

### 未改动

- 提案结构与 4 维定义（除 integrity 公式细化）不变；Codex review 段完整保留（append-only）。

待 Codex re-review。

## Review v2 by codex · 2026-06-02

### 结论

- 通过(有非阻塞建议)。
- v2 已闭合 v1 review 的 3 个阻塞点：integrity 公式可确定实现，lint/graph import wrapper 边界已清楚，验证口径也改成 fixture 主导、不再依赖真实实例的漂移状态。

### 阻塞点复核

1. **integrity 公式：已解决。**
   - 分母统一为 `lint.scanned.wiki_pages`，避免 dangling/ambiguous 被 edge 数稀释，也避免 0 edge 库无法计算。
   - error / dangling / ambiguous 权重分别为 100 / 50 / 50，配合 `min(1.0, count/page_count)`、`clamp_0_100` 和 `floor(x + 0.5)`，TASK 可以直接照抄实现。
   - `--check` 改为硬门 `len(lint.errors) == 0 and score >= threshold`，能避免低比例 lint error 被总分掩盖。空库 `score=null/status=empty` 且 exit 0 的口径也明确了。

2. **import 入口：已解决。**
   - `wiki_lint.evaluate_instance(root, *, now=None, scan_wiki_pii=False)` 强制 `check_only=True`，边界足够清楚，不会写 `.wiki/*`。
   - `wiki_graph.evaluate_instance(root)` 只返回 `{exit_code, graph, meta, profile, config_errors}`，不写 `maps/`，并要求 profile issue 不再 `sys.exit` 泄漏给 eval。
   - 依赖方向是 `wiki_eval -> wiki_lint/wiki_graph -> wiki_common`，没有循环依赖。真正需要 TASK 验证的是 wrapper 多次调用不同 root 时不会因 lint 的模块级全局状态串扰；这可以放到测试里覆盖。

3. **验证口径：已解决。**
   - 删除真实 personal 固定分数后，主验证改为 4 个临时 fixture：全绿 100、endorsement 低、integrity 低、空库。这比绑定当前 personal 状态稳。
   - 真实实例仅 smoke，验证能跑、JSON 完整、不写派生层；这个边界合理，也避免把用户 vault 当前内容当成引擎契约。

### 非阻塞建议

- TASK 建议加一个 `--check` 专项 fixture：构造“总分仍高于阈值，但存在 1 个 lint error”的库，断言 exit 非 0。这样能专门证明 `len(errors)==0` 硬门生效，而不是只靠低 integrity 分间接覆盖。
- 如果后续仍坚持脚本代码兼容 Python 3.9，实际实现签名建议用 `Optional[date]` 而不是 `date | None`；本仓日常环境是 py312，所以这不是 RFC 阻塞点。
- snapshot JSONL 后续可考虑追加 `status` / `weakest_dim` / `threshold` 字段，便于历史审计；MVP 的 `{ts, score, dims, pages}` 已够用。
