---
id: task_20260602_014
title: Apply RFC-014 — wiki-eval 健康度量化（health score + 维度分解 + 趋势 + CI 闸）
author: claude
executor: codex
status: pending
type: apply
created: 2026-06-02
updated: 2026-06-02
related_rfcs: [RFC-014]
---

# TASK-014: Apply RFC-014 — wiki-eval 健康度量化

## 目标

新增 `scripts/wiki_eval.py`：import 复用 lint/graph 的只读 wrapper，算 0–100 health score（4 加权维度 + 维度分解）+ `--snapshot` 趋势 + `--check` CI 阈值闸 + `--json`。纯机械、零网络零 LLM、确定性。

## 前置条件

- RFC-014 status: accepted（已满足，Decision by claude 2026-06-02）。
- working tree clean（除本 task 文件）。
- 环境：`conda run -n py312 python`。

## 强约束

1. **纯新增只读工具**：`wiki_eval` 不改任何 knowledge 数据、不写 `.wiki/*`（除 `--snapshot`）、不写 `maps/*`。
2. **复用而非重算**：health 指标来自 `wiki_lint` / `wiki_graph`，不在 eval 里另写 markdown 解析。
3. **不改 lint/graph 的 CLI 行为与退出码**：只新增 `evaluate_instance` 只读 wrapper。
4. **确定性**：同输入同分；时间戳不进分数计算；四舍五入统一 `floor(x+0.5)`。
5. **阈值/权重是 BASE_SCHEMA 常量**，不走 profile（per-库配置进 Backlog `trust_policy`）。

## 步骤

> Step 0 spec-review：核对 `wiki_lint.run_lint`/`configure`、`wiki_graph.build_graph`/`load_effective_schema` 现状，确认 wrapper 能收住全局状态 + `sys.exit`；发现歧义先提。

1. **`wiki_lint.py` 新增只读 wrapper**：
   ```python
   def evaluate_instance(root: Path, *, now: date | None = None,
                         scan_wiki_pii: bool = False) -> dict:
       # 内部强制 check_only=True（绝不写 .wiki/*）；返回 {exit_code, data, human}
   ```
   不改既有 `run_lint` / CLI 行为。

2. **`wiki_graph.py` 新增只读 wrapper**：
   ```python
   def evaluate_instance(root: Path) -> dict:
       # 不写 maps/；profile issue 不 sys.exit，收进 config_errors
       # 返回 {exit_code, graph, meta, profile, config_errors}
   ```

3. **`wiki_common.py`**：BASE_SCHEMA 新增 `health_weights`（`{integrity:0.4, freshness:0.2, endorsement:0.2, connectivity:0.2}`）+ `health_threshold`（默认 70）。可加共享 `clamp_0_100` / `round_half_up`。

4. **`wiki_eval.py`** 实现 4 维 + 总分：
   - **integrity**（照抄 RFC 确定公式）：分母 `lint.scanned.wiki_pages`；`error_rate/dangling_rate/ambiguous_rate = min(1.0, count/page_count)`；`integrity = clamp_0_100(100 - (100*error_rate + 50*dangling_rate + 50*ambiguous_rate))`。
   - **freshness**：`active` 页中非 `STALE_PAGE` 占比 ×100（active=0 时记 100）。
   - **endorsement**：`active` 且 type∉{source,query} 且 `confidence:high` 的页中 `review:true` 占比 ×100；无此类页记 100。
   - **connectivity**：`in_degree+out_degree>0` 占比 ×100。
   - 总分 = `round_half_up(Σ dim×weight)`，clamp 0–100。
   - **空库**（page_count==0）：score=null、status=empty、dims=null。

5. **CLI**：`--json`（`{score,status,dims,pages,weakest_dim,ts}`）、`--snapshot`（追加 `<root>/.wiki/eval_history.jsonl`，空库不写）、`--check`（`len(errors)==0` 且 `score>=health_threshold` → exit 0，空库 exit 0，否则非零）、`--root`。人类可读默认输出含维度分解 + 与上次 snapshot 的 delta。

6. **`.gitignore`**：确保 `<root>/.wiki/eval_history.jsonl` **不被** `.wiki/` 派生层规则吞掉（趋势进 git，需白名单）。

7. **文档**：`scripts/README.md`（wiki_eval 用法 + 4 维定义 + integrity 公式 + 退出码）；`wiki-design/02-workflows.md`（eval 何时跑：维护后 / 定期 / CI）。

8. **测试**（标准库 unittest，沿用 TASK-012/013 风格，直接调 `wiki_eval` 计算函数 + wrapper）：
   - **fixture A 全绿**：若干 high+review:true 页、0 stale/orphan/dangling/ambiguous → 四维 100、总分 **100**。
   - **fixture B endorsement 偏低**：含 high+review:false active 页 → endorsement<100、weakest_dim==`endorsement`。
   - **fixture C integrity 偏低**：构造 1 dangling（或 lint error）→ 按公式手算对照 integrity 扣分准确。
   - **空库**：score=null、status=empty、`--check` exit 0、不写 snapshot。
   - **确定性**：同 fixture 跑两次结果全等。
   - **多 root 防串扰**（Codex re-review 非阻塞）：连续对两个不同 root 调 `evaluate_instance`，断言结果互不污染。
   - **真实实例 smoke**：personal/引擎能跑出分、`--json` 完整、**断言运行前后 `.wiki/*` 与 `maps/*` 未变**（不写派生层）；不断言具体分数。

9. **跑验证（见下）→ commit**（最终 working tree clean）。

## 验证

```bash
ENGINE=/Users/zhangjunwu/workspace/llm-wiki/llm-wiki
PY="/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python"
PERSONAL=/Users/zhangjunwu/workspace/obsidian/knowledge/personal

# 1) 单测全绿
cd $ENGINE && $PY -m unittest -v tests.test_task_014

# 2) personal smoke：跑出分 + 不写派生层（前后对比 .wiki/maps mtime）
cd $ENGINE && $PY scripts/wiki_eval.py --root $PERSONAL --json

# 3) 引擎实例 smoke
cd $ENGINE && $PY scripts/wiki_eval.py --root knowledge --json

# 4) --check 行为（personal 当前应通过；构造低分 fixture 验证非零）
cd $ENGINE && $PY scripts/wiki_eval.py --root $PERSONAL --check; echo "exit=$?"

# 5) 既有套件不回归
cd $ENGINE && $PY -m unittest -v tests.test_task_012 tests.test_task_013
```

## 完成后报告格式

- Step 0 spec-review 结论（含歧义/偏离）
- 每步改动文件 + 关键位置（wrapper 实现、integrity 公式落点）
- 验证 1~5 实际输出（fixture A/B/C 分数、personal/引擎 smoke、--check 退出码、不写派生层证据）
- 新增测试清单（含多 root 防串扰 + 不写派生层断言）
- commit sha
- 偏离或异常

## Execution log by codex · <date>

（执行者填写）

## Evaluation by claude · <date>

（评估者填写）
