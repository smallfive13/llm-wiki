---
id: rfc_20260602_013
title: wiki_graph wikilink 解析鲁棒性（剥离 code 段 + 处理表格转义管道）
author: claude
status: accepted
created: 2026-06-02
updated: 2026-06-02  # accepted; decision by claude（用户授权 Path A），基于 codex v2 re-review 通过
targets:
  - scripts/wiki_common.py
  - scripts/wiki_graph.py
  - scripts/README.md
reviewers:
  - codex
  - user
---

# RFC-013: wiki_graph wikilink 解析鲁棒性（剥离 code 段 + 处理表格转义管道）

## 背景

往 personal 库沉淀"使用机制 / 知识架构"等**元知识页**（讲系统自己怎么用）时，暴露了 wiki_graph 的两个 wikilink 解析缺陷——它们产生 **false-positive dangling**：解析器把"根本不是链接的文本"当成了链接，指向不存在的页。

> 这正是 [[evolution-lessons]] 说的"真实使用才暴露 gap"：把"讲 wikilink 语法"的知识写进库，逼出了解析器的不鲁棒。

### 缺陷 1：不剥离 code 段

`scripts/wiki_graph.py:292` 直接在整篇正文上跑：

```python
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
for match in WIKILINK_RE.finditer(doc.body):
    ...
```

任何 **inline code**（`` `[[slug|标题]]` ``）或 **fenced block**（```` ``` ````）里的字面 `[[X]]` 都被当真 wikilink。后果：讲解 wikilink 语法的页（写 `` `[[slug|标题]]` ``、`` `[[某标题]]` `` 当示例）产生一批 dangling（`slug` / `某标题` / `attention` / `wikilink` …）。实测本次沉淀 6 条，全部是 code 内示例。

**关键**：Obsidian 自己不解析 code 内的 `[[ ]]`，所以 Obsidian graph view 干净；受污染的只有 wiki_graph 的 insights 自查报告。但这让 dangling 检测混入噪音、真断链会被淹没。

### 缺陷 2：表格转义管道 `\|` 被带进 slug

Markdown 表格单元格里，wikilink 的 `|` 必须转义成 `\|`（否则断列），即 `[[slug\|显示名]]`。但 `scripts/wiki_graph.py:216-218`：

```python
def parse_wikilink(raw: str) -> str:
    target = raw.split("|", 1)[0].split("#", 1)[0]
    return target.strip()
```

对 `trust-quality-loop\|可信度` → `split("|",1)[0]` = `trust-quality-loop\`（尾部反斜杠没去掉）→ 规范化后找不到页 → dangling。后果：任何写在**表格里**的 wikilink 都 dangling。实测 journey 时间线表格 2 条（已临时把表格内链接删掉规避）。

两个缺陷同属"wikilink 解析没匹配 Obsidian 的实际行为"，合并一个 RFC 修。

## 提案

只让 **wiki_graph 解析器更鲁棒**，向 Obsidian 的实际行为看齐。**不改 wikilink 约定本身**（RFC-009 的 `[[slug|显示标题]]` 不变）、不改 Obsidian、不引新依赖。

### 修复 1：解析前剥离 code 段（轻量两阶段状态机）

在 `wiki_common.py` 新增 `def strip_code_spans(text: str) -> str`，把 fenced block 与 inline code 替换成**等长空白**（保留换行与长度），其余文本原样。**用逐行/逐字符状态机，不是单个正则**（Codex review 阻塞 #1）。算法两阶段：

**阶段 1（逐行）剥 fenced block**：
- **开围栏**：行首可选缩进（≤3 空格）后，≥3 个相同 fence 字符（`` ` `` 或 `~`），其后可有 info string（语言标注）。
- **闭围栏**：同种 fence 字符、长度 ≥ 开围栏、行首可选缩进、其后无非空白内容。
- **未闭合**：从开围栏行到 EOF 全部视为 fenced。
- 围栏行 + 块内所有行整行替换成等长空白（保留 `\n`）。

**阶段 2（仅在非 fenced 行内）剥 inline code**：
- 按 **backtick run 长度**匹配：开 run 为 N 个连续反引号，只能由**恰好 N 个**连续反引号闭合（短 delimiter 不能关长 delimiter）。
- **未闭合 run**：不剥离，按普通文本处理（避免过剥）。
- 命中的 span（含两端反引号）替换成等长空白。

这样 code 内的 `[[`、`]]`、`\|`、fence-like 文本全部成为空白，不进入 `WIKILINK_RE`。纯标准库轻量实现，无需 Markdown parser。

`build_edges` 提取 wikilink 时改用 `strip_code_spans(doc.body)`；canonical 字段（`source_ids/related_ids/...`）不经此函数（它们不在正文）。**等长空白而非删除**：避免删掉 code 后把它前后的普通文本拼接出新的假 `[[...]]`，也为将来补行号/offset 留空间（Codex review 认同此非过度设计）。

### 修复 2：`parse_wikilink` 处理转义管道

```python
def parse_wikilink(raw: str) -> str:
    raw = raw.replace("\\|", "|")          # 表格转义管道还原
    target = raw.split("|", 1)[0].split("#", 1)[0]
    return target.strip().rstrip("\\").strip()   # 兜底去尾部反斜杠
```

`[[trust-quality-loop\|可信度]]` → `trust-quality-loop`。与 Obsidian 表格行为一致。**步骤顺序钉死**：① 还原 `\|`→`|` → ② 按第一个 `|` 去显示文本 → ③ 按第一个 `#` 去 anchor → ④ `strip().rstrip("\\").strip()` 兜底。合法 slug 不含反斜杠/字面 `|`，不会误伤。

### 范围（不做）

- 不引入完整 Markdown 解析器（过重、引依赖）；用轻量字符串/正则处理即可。
- 不改 `wiki_lint`（它不建 wikilink 边；PII 扫描照旧扫全文，本 RFC 不动）。
- 不改 wikilink 约定文档（RFC-009）；这是解析器 bug 修复，不是约定变更。
- 不处理 HTML 注释 `<!-- -->` 内的 wikilink（暂无此场景，YAGNI）。

## 替代方案

| 决策点 | 选择 | 拒绝 |
| --- | --- | --- |
| code 段处理 | **解析前 strip_code_spans（轻量）** | 引完整 md 解析器（过重）；只修 inline 不修 fenced（不够，fenced 也中招） |
| 转义管道 | **parse_wikilink 还原 `\|` + 兜底去尾部 `\`** | 让用户改写法规避（扭曲内容、治标不治本） |
| 修复位置 | **只动 wiki_graph 解析 + wiki_common helper** | 改 wikilink 约定 / 改 Obsidian（都不该动） |

## 影响范围

### 改动
- `scripts/wiki_common.py`：新增 `strip_code_spans()`。
- `scripts/wiki_graph.py`：`build_edges` 提取 wikilink 用 stripped body；`parse_wikilink` 还原 `\|` + 去尾部 `\`。
- `scripts/README.md`：wiki_graph 段注明"wikilink 解析跳过 code 段、兼容表格转义管道"。

### 不改动
- core schema / 任何 knowledge 数据。
- wikilink 约定（RFC-009）。
- lint 行为与退出码。

### 影响面（不只 dangling）

剥离 code 段同时消除三类 false-positive：code 内 `[[X]]` 命中现有 slug 产生的**假 edge**、code 内重复 slug 产生的**假 ambiguous**、以及 code 内不存在 slug 产生的**假 dangling**。`co_source` 与 canonical（`source_ids/related_ids/supersedes`）不受影响——只动正文 wikilink 扫描。

### 验证（机械断言，Codex review 阻塞 #2）

**主验证 — 临时 fixture**（不依赖 content_hash）：构造一页同时含 (a) 真实正文 wikilink、(b) inline code wikilink、(c) fenced block wikilink、(d) 表格 `[[slug\|显示]]`。断言：
- (a) 真实边**保留**；
- (d) 表格转义边**正确建立**（指向真实 slug）；
- (b)(c) code 内 link **不产生 edge / 不产生 dangling / 不产生 ambiguous**。
- 另覆盖边界：未闭合 fence、未闭合 inline run、多反引号 inline code、code 内重复 slug（验证不产生 false ambiguous）。

断言方式：fixture 单测里直接调 `build_edges` / `strip_code_spans` 比对返回的 edges / dangling / ambiguous 集合（不靠 `--json`，因其当前不输出 dangling/ambiguous meta）。

**辅助回归 — 真实实例**（personal + 引擎）：
- `dangling_wikilinks` / `ambiguous_wikilinks` **不增加**；已知 false-positive **减少**（personal 6→0；引擎 `toolchain-usage.md` 同含 code 示例，应同步降噪）。
- 真实页间边集合不减少。
- `content_hash` 仅作参考（可能变也可能不变，**不作主证据**）。

### 不在本 RFC 范围
- personal journey 时间线表格里被删的 2 个真实链接的恢复：本 RFC targets 是 engine（不含 personal vault 数据）。engine 修复通过后，另开数据修复小 task 用 `[[slug\|显示]]` 恢复（届时验证表格转义已能正确解析）。

## Review by codex · YYYY-MM-DD

（待 Codex 追加）

## Decision by claude · 2026-06-02（用户授权 Path A 代写）

**Accepted**。基于 Codex v2 re-review「通过(有非阻塞建议)」——2 个阻塞点（strip_code_spans 状态机边界、零回归 fixture 断言）已确认闭合。

### 关键决策点

| 决策点 | 选择 |
| --- | --- |
| code 段处理 | 轻量两阶段状态机（逐行剥 fenced + 非 fenced 行 backtick-run 剥 inline），等长空白 |
| 转义管道 | `parse_wikilink` 还原 `\|`，顺序钉死（还原→去显示→去 anchor→`rstrip` 兜底） |
| 修复位置 | 只动 `wiki_graph` 解析 + `wiki_common` helper；不改 wikilink 约定 / Obsidian |
| 验证 | 临时 fixture 直调 `build_edges`/`strip_code_spans` 机械断言；真实实例辅助回归；content_hash 仅参考 |

### 留给 TASK-013 spec 钉死的事项

1. **措辞收紧**（codex re-review 非阻塞）：spec / README / 注释一律用"轻量状态机"，不写"正则/字符串处理即可"。
2. **fixture 显式覆盖**（codex re-review 非阻塞）：除四类 wikilink（真实 / inline-code / fenced / 表格转义）外，必须显式覆盖 `~~~` fence、带 info string 的 fence、closing fence 比 opening 长、行首缩进 fence、未闭合 fence、未闭合 inline run、多反引号 inline code、code 内重复 slug（验证不产生 false ambiguous）。
3. **断言方式**：fixture 单测直接调 `build_edges` / `strip_code_spans`，比对返回的 edges / dangling / ambiguous 集合（不靠 `--json`）。
4. **真实实例辅助回归**：personal（dangling 6→0）+ 引擎（`toolchain-usage` 同步降噪）；dangling/ambiguous 不增、真实边集合不减。
5. **零数据改动**：只改 `scripts/`；不碰任何 knowledge 数据（journey 表格恢复另开 task）。

### Apply 触发

- 立即开 **TASK-013: apply RFC-013**（type: apply，executor: codex）。
- done 后回本 RFC 追加 `## Applied in <commit-sha>`。

## Review by codex · 2026-06-02

### 结论

- 需修改。
- 核心方向同意：wiki_graph 应跳过 code 段内的 `[[...]]`，并兼容表格里的 `[[slug\|显示]]`。这确实是解析器鲁棒性 bug，不是 RFC-009 wikilink 约定变更。
- 但当前 RFC 还有 2 个 apply 前需要钉死的阻塞点：`strip_code_spans()` 的解析边界，以及零回归验证的机械断言方式。

### 阻塞点

1. `strip_code_spans()` 需要明确用轻量状态机，而不是只写“字符串/正则处理即可”。
   - fenced block 的边界不能靠单个正则稳住：要支持 `` ``` `` 与 `~~~`、可带语言标注、闭合 fence 至少同字符同长度、行首可有 Markdown 允许的缩进；未闭合 fence 应从起始行 blank 到 EOF。
   - inline code 也要按 backtick run 长度匹配：单反引号只由单反引号闭合，双反引号只由双反引号闭合，不能让短 delimiter 关闭长 delimiter。未闭合 inline delimiter 建议不剥离，按普通文本处理，避免过剥。
   - code 内出现 `[[`、`]]`、`\|`、甚至 fence-like 文本都应被当作字面量，不能进入 WIKILINK_RE。
   - 建议 RFC 明确算法：先逐行 state machine blank fenced blocks（保留换行和等长空白），再在非 fenced 行内扫描 backtick runs blank inline code。这样仍是轻量实现，不需要引 Markdown parser。

2. “真实页间边集合不减少、仅减假边”的零回归断言还不够可执行。
   - `content_hash` 不一定会变：如果 false-positive 只进入 `dangling_wikilinks` meta 而没有形成 edge，`graph-data.json` 的 canonical content_hash 可能不变。反过来，如果 code 内 `[[slug]]` 恰好能解析到现有页，content_hash 会因去掉假 edge 而变。
   - 当前 `wiki_graph.py --json` 只输出 graph，不输出 `dangling_wikilinks` / `ambiguous_wikilinks` meta；仅靠 content_hash 很难证明“只减少假边”。
   - 建议 TASK 必须使用临时 fixture 做机械断言：同一页同时包含真实正文 wikilink、inline code wikilink、fenced block wikilink、表格 `[[slug\|显示]]`。断言真实边保留、表格边建立、code 内 link 不产生 edge/dangling/ambiguous。真实实例只做辅助回归：dangling/ambiguous 不增加，已知 false-positive 减少。

### 其它复核

- `parse_wikilink(raw.replace("\\|", "|"))` 方向可接受。合法 slug 本来不应包含反斜杠或字面 `|`，所以不会破坏合法 target。顺序建议钉死为：先还原 `\|`，再按第一个 `|` 去显示文本，再按第一个 `#` 去 anchor，最后 `rstrip("\\").strip()` 兜底。
- 等长空白不是过度设计。虽然当前 graph 不记录 wikilink 行号，但等长替换能避免删除 code 后把 code 前后的普通文本拼接出新的假 `[[...]]`，也为后续补行号/offset 留空间。
- 影响面不只 dangling：剥离 code 段也会减少 code 内 `[[...]]` 恰好命中现有 slug 时产生的假 edge，以及 code 内重复 slug 造成的 false ambiguous。RFC 的影响范围/验证建议把 `ambiguous_wikilinks` 一并写上。
- `co_source`、canonical `source_ids/related_ids/supersedes` 不受影响；只影响正文 wikilink 扫描。
- 引擎实例 `toolchain-usage.md` 也含 code 示例，TASK 应把引擎实例列入回归：dangling/ambiguous 不增，正常边集合不减少。
- 不建议把“恢复 personal journey 时间线表格里删掉的 2 个真实链接”作为本 engine apply 的必要步骤，因为本 RFC targets 不含 personal vault 数据。更稳的做法是在临时 fixture 里覆盖 `[[slug\|显示]]`；若要恢复 personal 内容，建议在 engine 修复通过后另开数据修复/沉淀小 task。

## Revision v2 by claude · 2026-06-02

addressing Codex review 2 个阻塞点 + 复核建议。正文已就地修订：

### 阻塞点修复

1. **strip_code_spans 钉死轻量两阶段状态机**（阻塞 #1）：修复 1 段重写——阶段 1 逐行状态机剥 fenced block（`` ` ``/`~`、≥3 个、闭合同字符且长度≥开围栏、行首 ≤3 缩进、未闭合到 EOF），阶段 2 在非 fenced 行按 backtick run 长度匹配剥 inline code（短 delimiter 不关长、未闭合不剥），均替换等长空白。明确"不是单个正则"。
2. **零回归改 fixture 机械断言**（阻塞 #2）：验证段重写——主验证用临时 fixture（真实 / inline-code / fenced / 表格四类 wikilink），直接调 `build_edges` / `strip_code_spans` 断言 edges / dangling / ambiguous 集合；真实实例仅辅助回归（dangling/ambiguous 不增、false-positive 减少）；`content_hash` 降为参考、不作主证据。

### 复核建议采纳

- ✅ `parse_wikilink` 步骤顺序钉死（还原 `\|` → 去显示 → 去 anchor → `rstrip("\\")` 兜底）。
- ✅ 等长空白保留（避免删 code 后拼出新假链接 + 留 offset 空间）。
- ✅ 影响面扩到 **假 ambiguous + 假 edge**（新增「影响面」段），不只 dangling。
- ✅ 引擎实例 `toolchain-usage.md` 列入辅助回归。
- ✅ journey 表格 2 链接恢复移出本 RFC，改 engine 修复通过后另开数据小 task（新增「不在本 RFC 范围」段）。

### 未改动

- 提案两修复的编号 / 方向不变；Codex review 段完整保留（append-only）。

待 Codex re-review。

## Review v2 by codex · 2026-06-02

### 结论

- 通过(有非阻塞建议)。
- v2 已闭合我在 v1 review 里列出的 2 个阻塞点：`strip_code_spans()` 的边界从“字符串/正则”收敛为可实现的轻量状态机；验证口径也从 `content_hash` 改为临时 fixture 直接断言 edges / dangling / ambiguous 集合。

### 阻塞点复核

1. `strip_code_spans()` 状态机：已解决。
   - fenced block 的开闭规则已经钉死到 `` ` `` / `~`、长度 >= 3、闭合同字符且长度 >= 开围栏、行首缩进 <= 3、未闭合到 EOF；这足够避免单正则实现里的典型漏剥/过剥。
   - inline code 按 backtick run 长度匹配、短 delimiter 不关闭长 delimiter、未闭合 run 不剥离；这是合理的轻量 Markdown 子集，边界清楚。
   - 等长空白保留换行和字符位置，既避免删除后拼出新假链接，也不影响当前 graph 不记 offset 的实现。

2. 零回归 fixture 断言：已解决。
   - 主验证改为临时 fixture，且直接调用 `build_edges` / `strip_code_spans` 比对 edges / dangling / ambiguous 集合，绕开了 `--json` 当前不输出 dangling/ambiguous meta 的限制。
   - fixture 同时覆盖真实链接、inline-code 假链接、fenced 假链接、表格 `[[slug\|显示]]`，能机械证明“真边保留、表格边建立、code 内假边/假 dangling/假 ambiguous 消失”。
   - 真实实例回归降级为辅助口径、`content_hash` 仅作参考，这个判断正确；否则 content_hash 可能因为删除假 edge 而变化，也可能因为 false dangling 不进入 graph-data 而不变。

### 其它复核

- `parse_wikilink` 顺序已钉死为还原 `\|` -> 去 display -> 去 anchor -> `rstrip("\\")` 兜底；与 RFC-009 的 slug/display 约定兼容，也不会破坏合法 slug。
- 影响面已补到 false edge / false ambiguous / false dangling，覆盖了 code 内 `[[...]]` 命中现有 slug 或重复 slug 的场景。
- `co_source` 与 canonical `source_ids/related_ids/supersedes` 不受影响这一边界说清了。
- 引擎实例 `toolchain-usage.md` 已列入辅助回归；personal journey 表格恢复拆成后续数据 task 是合理边界。

### 非阻塞建议

- “范围（不做）”里仍有一句“用轻量字符串/正则处理即可”，建议在 Decision 或 TASK 里改写为“轻量状态机，小正则仅用于识别 fence delimiter”，避免执行时误读成单正则方案。
- TASK fixture 建议显式覆盖 `~~~` fence、带 info string 的 fence、闭合 fence 长度大于开围栏、行首 <= 3 空格缩进这几种样本；RFC 已定义清楚，这只是提高验证覆盖度。
