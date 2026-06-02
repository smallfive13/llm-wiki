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

- 从 lint 拿：errors / warnings（含 `STALE_PAGE` / `UNVERIFIED_HIGH` 命中）、页面总数。
- 从 graph 拿：nodes（`in_degree` / `out_degree` / orphan）、`dangling_wikilinks` / `ambiguous_wikilinks`。

> TASK 阶段钉死 lint/graph 的可 import 入口（返回结构化结果而非只打印）。

### Health score：4 个可解释维度（规则化，非黑箱）

每维度 0–100，加权汇总。权重写进 BASE_SCHEMA 常量、可解释：

| 维度 | 定义 | 默认权重 |
| --- | --- | --- |
| **integrity 完整性** | lint error=0 且 dangling=0 且 ambiguous=0 → 100；每类结构问题按比例扣分 | **0.40** |
| **freshness 新鲜度** | `active` 页中**非 stale** 占比 ×100 | 0.20 |
| **endorsement 背书率** | **high 置信页**（`active`、type∉{source,query}、`confidence:high`）中 `review:true` 占比 ×100；无 high 页记 100 | 0.20 |
| **connectivity 连通度** | 非 orphan 页（`in_degree`+`out_degree`>0）占比 ×100 | 0.20 |

- 总分 = Σ(维度分 × 权重)，四舍五入到整数（0–100）。
- integrity 权重最高：结构正确（不断引/不重复）是底线，比"新不新鲜"更重要。
- **endorsement 只盯 high 页**：与 RFC-012 `UNVERIFIED_HIGH` 一致——只有 high 主张要求人背书；medium/low 页 `review:false` 是正常态，不拉低分（否则会惩罚像本调研这种诚实标 medium 的页）。
- **空库**（0 页）特判：返回 score=null + 状态 `empty`，不参与趋势。
- 输出**维度分解**而非只给总分——让人知道是哪一块拖后腿（如 endorsement 60 = 一堆页没背书）。

### 趋势（可选写入，进 git）

- 默认只算 + 输出，不落盘。
- `--snapshot` 时追加一条到 `<root>/.wiki/eval_history.jsonl`（`{ts, score, dims, pages}`）。
- **进 git**（不在 .gitignore 派生层）：趋势是**不可重建的时间序列**，有审计价值；用 `--snapshot` 显式触发避免 commit 噪音。

### CI / 阈值闸

- `--check`：总分 < 阈值（BASE_SCHEMA 默认，如 70）则非零退出，适配 CI / pre-push。
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

### 零回归验证
- `wiki_eval` 是纯新增只读工具：不改数据、不改 lint/graph 现有输出。
- 确定性：同一库快照两次分数一致（无时间戳进分数计算）。
- 在 personal 实例验证：当前 9 页（8 个 high 全 `review:true` + 1 个 medium comparison）/ 0 stale / 0 orphan / 0 dangling → 四维全 100（endorsement 只看 8 个 high 页、全背书）→ **总分 100**。
- 引擎实例（4 页，部分 `review:false` 的 high 页）应得 < 100，维度分解能指出 endorsement 偏低。

## Review by codex · YYYY-MM-DD

（待 Codex 追加）

## Decision

（待用户填写，或授权某 Agent 代写）
