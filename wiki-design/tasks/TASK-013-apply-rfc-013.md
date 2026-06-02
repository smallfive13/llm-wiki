---
id: task_20260602_013
title: Apply RFC-013 — wiki_graph wikilink 解析鲁棒性（strip_code_spans + parse_wikilink 转义 + fixture）
author: claude
executor: codex
status: pending
type: apply
created: 2026-06-02
updated: 2026-06-02
related_rfcs: [RFC-013]
---

# TASK-013: Apply RFC-013 — wiki_graph wikilink 解析鲁棒性

## 目标

修 wiki_graph 的两个 wikilink false-positive 缺陷：① 解析前用**轻量状态机**剥离 code 段（inline + fenced），使 code 内 `[[...]]` 示例不再被当真链接；② `parse_wikilink` 还原表格转义 `\|`，使表格内 `[[slug\|显示]]` 正确解析。只让解析器向 Obsidian 实际行为看齐，不改 wikilink 约定。

## 前置条件

- RFC-013 status: accepted（已满足，Decision by claude 2026-06-02）。
- working tree clean（除本 task 文件）。
- 环境：`conda run -n py312 python`。

## 强约束

1. **只动解析器**：`scripts/wiki_common.py`（新增 `strip_code_spans`）+ `scripts/wiki_graph.py`（`build_edges` 用 stripped body、`parse_wikilink` 还原转义）+ `scripts/README.md` + 测试。不改 core schema、不改 wikilink 约定（RFC-009）、不改 lint 行为与退出码。
2. **零数据改动**：不碰任何 knowledge 数据（personal journey 表格的链接恢复**不在本 task**，另开数据小 task）。
3. **轻量状态机，不是单正则**（措辞收紧——RFC-013 codex re-review 非阻塞）：`strip_code_spans` 必须是逐行 + 逐字符状态机实现；spec / README / 代码注释一律称"轻量状态机"，不写"正则/字符串处理即可"。
4. **canonical 不经此函数**：`source_ids/related_ids/supersedes/...` 来自 frontmatter，不走 `strip_code_spans`；只有正文 wikilink 扫描用 stripped body。
5. **确定性**：等长空白替换（保留换行/长度），不删除；沿用既有原子写 + 确定序。

## 步骤

> Step 0 spec-review：通读后若与现有 `build_edges`(`scripts/wiki_graph.py:292` 一带)、`parse_wikilink`(216-218)、`WIKILINK_RE`(39) 结构或 ambiguous 检测有冲突/歧义，先在 Execution log 提出再动手。

1. **`wiki_common.py` 新增 `strip_code_spans(text) -> str`**（轻量两阶段状态机，把 code 段替换成等长空白、保留 `\n`）：
   - **阶段 1（逐行）剥 fenced block**：
     - 开围栏：行首可选缩进（≤3 空格）+ ≥3 个相同 fence 字符（`` ` `` 或 `~`）+ 可选 info string。
     - 闭围栏：同种 fence 字符、长度 ≥ 开围栏、行首可选缩进、其后无非空白。
     - 未闭合：从开围栏行到 EOF 全部视为 fenced。
     - 围栏行 + 块内行整行替换等长空白。
   - **阶段 2（仅非 fenced 行）剥 inline code**：
     - 按 backtick run 长度匹配：开 run N 个反引号，仅由**恰好 N 个**反引号闭合（短不关长）。
     - 未闭合 run：不剥离，按普通文本处理。
     - 命中 span（含两端反引号）替换等长空白。

2. **`wiki_graph.py` — `build_edges` 用 stripped body**：提取 wikilink 时改 `WIKILINK_RE.finditer(strip_code_spans(doc.body))`。其余 edge 类型（canonical、co_source）不变。

3. **`wiki_graph.py` — `parse_wikilink` 还原转义**，顺序钉死：
   ```python
   def parse_wikilink(raw: str) -> str:
       raw = raw.replace("\\|", "|")              # ① 还原表格转义管道
       target = raw.split("|", 1)[0].split("#", 1)[0]  # ② 去显示文本 ③ 去 anchor
       return target.strip().rstrip("\\").strip()      # ④ 兜底去尾部反斜杠
   ```

4. **`scripts/README.md`**：wiki_graph 段注明"wikilink 解析跳过 code 段（轻量状态机）、兼容表格转义管道 `\|`"。

5. **测试 / fixture**（标准库 unittest，沿用 TASK-012 风格）：
   - **主 fixture**：一页同时含 (a) 真实正文 wikilink、(b) inline code wikilink、(c) fenced block wikilink、(d) 表格 `[[slug\|显示]]`。直接调 `build_edges` / `strip_code_spans`，断言：
     - (a) 真实边保留；(d) 表格转义边正确建立（指向真实 slug）；
     - (b)(c) code 内 link **不产生 edge / dangling / ambiguous**。
   - **显式边界覆盖**（RFC-013 codex re-review 非阻塞，必须全覆盖）：`~~~` fence、带 info string 的 fence、closing fence 比 opening 长、行首缩进 fence、未闭合 fence、未闭合 inline run、多反引号 inline code、code 内重复 slug（不产生 false ambiguous）。
   - **辅助回归**：对 personal + 引擎实例跑 graph，断言 `dangling_wikilinks` / `ambiguous_wikilinks` 不增、已知 false-positive 减少（personal 6→0；引擎 toolchain-usage 降噪）、真实边集合不减。

6. **跑验证（见下）→ commit**（最终 working tree clean）。

## 验证

```bash
ENGINE=/Users/zhangjunwu/workspace/llm-wiki/llm-wiki
PY="/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python"
PERSONAL=/Users/zhangjunwu/workspace/obsidian/knowledge/personal

# 1) 单测全绿
cd $ENGINE && $PY -m unittest -v tests.test_task_013

# 2) personal：dangling 应 6→0（先存 JSON 再解析，避免 conda 管道问题）
cd $ENGINE && $PY scripts/wiki_graph.py --root $PERSONAL   # 重建 maps/
grep -A6 'Dangling' $PERSONAL/maps/graph-insights.md       # 期望 (none)
grep -A3 '知识健康度' $PERSONAL/maps/graph-insights.md      # 概览仍在

# 3) personal lint 仍 exit 0
cd $ENGINE && $PY scripts/wiki_lint.py --root $PERSONAL --check-only; echo "exit=$?"

# 4) 引擎实例 graph：dangling 不增（toolchain-usage 含 code 示例应降噪）
cd $ENGINE && $PY scripts/wiki_graph.py --root knowledge
grep -A6 'Dangling' $ENGINE/knowledge/maps/graph-insights.md
```

## 完成后报告格式

- Step 0 spec-review 结论（含歧义/偏离）
- 每步改动文件 + 关键代码位置（`strip_code_spans` 算法摘要）
- 验证 1~4 实际输出（尤其 personal dangling 6→0、真实边集合对比）
- 新增测试清单（含所有边界用例）+ 全绿输出
- commit sha
- 偏离或异常

## Execution log by codex · <date>

（执行者填写）

## Evaluation by claude · <date>

（评估者填写）
