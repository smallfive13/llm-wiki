---
id: task_20260602_013
title: Apply RFC-013 — wiki_graph wikilink 解析鲁棒性（strip_code_spans + parse_wikilink 转义 + fixture）
author: claude
executor: codex
status: done
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

## Execution log by codex · 2026-06-02

### Step 0 spec-review

- 结论：通过，未发现阻塞歧义。
- 与现有结构契合点：
  - `scripts/wiki_graph.py` 的 `WIKILINK_RE` 仍为正文 `[[...]]` 扫描入口；只需把 `doc.body` 替换成 `strip_code_spans(doc.body)`。
  - `parse_wikilink()` 是独立函数，能直接按 spec 顺序改为还原 `\|` → 去 display → 去 anchor → `rstrip("\\")` 兜底。
  - `build_edges()` 已返回 `edges / dangling / ambiguous`，适合临时 fixture 直接断言，不依赖 `--json`。
  - canonical 边与 `co_source` 均来自 frontmatter / source aggregation，不经过正文扫描；本实现未改这些路径。
- 偏离/异常：
  - 初次用 `PY="/Users/.../conda run -n py312 python"` 在 zsh 中抓基线时变量未拆分，命令报 `no such file or directory`；未改仓库。后续验证改用 bash 或显式 conda/python 路径。
  - `conda run ... python - <<'PY'` 方式没有带出脚本输出；后续直接用 spec 命令和 `envs/py312/bin/python` 做边集对比。

### 改动文件与关键位置

- `scripts/wiki_common.py`
  - 新增 `strip_code_spans(text)` 及私有 helper。
  - 算法：阶段 1 逐行剥 fenced block，支持 `` ` `` / `~`、长度 >= 3、闭合同字符且长度 >= 开围栏、行首缩进 <= 3、未闭合到 EOF；阶段 2 仅在非 fenced 行内按 backtick-run 长度剥 inline code，短 delimiter 不关闭长 delimiter，未闭合 run 不剥离；所有 code span 均替换为等长空白并保留换行。
- `scripts/wiki_graph.py`
  - import `strip_code_spans`。
  - `parse_wikilink(raw)` 改为先 `raw.replace("\\|", "|")`，再取 `|` 前、`#` 前 target，最后 `strip().rstrip("\\").strip()`。
  - `build_edges()` 的正文 wikilink 扫描改为 `WIKILINK_RE.finditer(strip_code_spans(doc.body))`；canonical `source_ids/related_ids/supersedes` 与 `co_source` 不变。
- `scripts/README.md`
  - wiki_graph Wikilink 解析段补充：正文扫描跳过 fenced / inline code，兼容表格转义管道 `\|`。
- `tests/test_task_013.py`
  - 新增标准库 unittest，直接调用 `strip_code_spans` / `build_edges`。

### 验证输出

#### 1) 单测全绿

```text
test_fenced_block_boundaries (tests.test_task_013.StripCodeSpansTest.test_fenced_block_boundaries) ... ok
test_inline_backtick_run_boundaries (tests.test_task_013.StripCodeSpansTest.test_inline_backtick_run_boundaries) ... ok
test_preserves_length_and_newlines (tests.test_task_013.StripCodeSpansTest.test_preserves_length_and_newlines) ... ok
test_unclosed_fence_strips_to_eof (tests.test_task_013.StripCodeSpansTest.test_unclosed_fence_strips_to_eof) ... ok
test_build_edges_keeps_real_and_table_links_but_ignores_code_links (tests.test_task_013.WikilinkParsingTest.test_build_edges_keeps_real_and_table_links_but_ignores_code_links) ... ok
test_canonical_edges_do_not_use_stripped_body (tests.test_task_013.WikilinkParsingTest.test_canonical_edges_do_not_use_stripped_body) ... ok
test_code_duplicate_slug_does_not_create_false_ambiguous (tests.test_task_013.WikilinkParsingTest.test_code_duplicate_slug_does_not_create_false_ambiguous) ... ok
test_parse_wikilink_unescapes_table_pipe_before_display_and_anchor (tests.test_task_013.WikilinkParsingTest.test_parse_wikilink_unescapes_table_pipe_before_display_and_anchor) ... ok

----------------------------------------------------------------------
Ran 8 tests in 0.004s

OK
```

#### 2) personal graph：dangling 6→0

执行前现有 `personal/maps/graph-insights.md` 的 Dangling Wikilinks：

```text
- slug (from top_20260601_wiki-skill-layer, wiki/topics/wiki-skill-layer.md)
- slug\ (from top_20260602_knowledge-architecture, wiki/topics/knowledge-architecture.md)
- attention (from top_20260602_usage-mechanics, wiki/topics/usage-mechanics.md)
- slug (from top_20260602_usage-mechanics, wiki/topics/usage-mechanics.md)
- wikilink (from top_20260602_usage-mechanics, wiki/topics/usage-mechanics.md)
- 某标题 (from top_20260602_usage-mechanics, wiki/topics/usage-mechanics.md)
```

执行后：

```text
wiki-graph instance root: /Users/zhangjunwu/workspace/obsidian/knowledge/personal · profile: personal

wiki-graph: 8 nodes, 47 edges, 1 communities

## Dangling Wikilinks

- (none)

## Ambiguous Wikilinks

- (none)
## 知识健康度

verified 0 · unverified-high 8 · stale 0 · orphan 0 · total 8
```

#### 3) personal lint 仍 exit 0

```text
wiki-lint instance root: /Users/zhangjunwu/workspace/obsidian/knowledge/personal · profile: personal

wiki-lint v0.1.0
================
实例: /Users/zhangjunwu/workspace/obsidian/knowledge/personal · profile: personal
扫描: personal/wiki/ (8 文件) · personal/inbox/ (0 draft) · personal/raw/ (0 source)

[OK]    schema 校验: 8 页扫描
[OK]    ID 唯一性: 8 个 id
[OK]    canonical 引用 + supersedes 对称
[OK]    source 单主键
[OK]    entity 别名（含链式跳转 / status:redirect）: 0 entries
[OK]    inbox: 0 draft
[OK]    PII 扫描（inbox-only）: 0 命中

派生层未重建（--check-only）

错误: 0 · 警告: 8

exit=0
```

警告均为既有 `UNVERIFIED_HIGH`，非本 task 新增 error。

#### 4) 引擎实例 graph：dangling 不增

```text
wiki-graph instance root: /Users/zhangjunwu/workspace/llm-wiki/llm-wiki/knowledge · profile: base

wiki-graph: 4 nodes, 16 edges, 1 communities

## Dangling Wikilinks

- (none)

## Ambiguous Wikilinks

- (none)
```

#### 真实边集合对比

```text
== engine edge compare ==
profile=base before_edges=16 after_edges=16 missing_before_edges=0 added_edges=0
dangling_after=0 ambiguous_after=0
== personal edge compare ==
profile=personal before_edges=47 after_edges=47 missing_before_edges=0 added_edges=0
dangling_after=0 ambiguous_after=0
```

### 新增测试清单

- `strip_code_spans` 保持等长、保留换行。
- inline code 内 `[[...]]` 不进入 graph。
- fenced block 内 `[[...]]` 不进入 graph。
- 表格 `[[slug\|显示]]` 解析到真实 slug。
- `~~~` fence、带 info string fence、closing fence 比 opening 长、行首 <= 3 空格缩进 fence。
- 未闭合 fence 剥到 EOF。
- 未闭合 inline run 不剥离。
- 多反引号 inline code 短 delimiter 不关长。
- code 内重复 slug 不产生 false ambiguous。
- canonical `related_ids` 不经 `strip_code_spans`，仍建 canonical edge。

### Commit

- apply commit: `ba17ac2ae272b451a6a52a6eedda0126345b9855`

### 偏离或异常

- 未改任何 `knowledge/wiki/**` 源数据；personal journey 表格链接恢复未做，符合 task 边界。
- 运行 graph 生成/刷新了被 ignore 的 `maps/*` 派生层；未纳入 Git。
- `git diff --check` 通过；提交实现后非 ignored working tree clean。

## Evaluation by claude · <date>

（评估者填写）
