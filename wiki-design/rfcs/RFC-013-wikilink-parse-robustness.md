---
id: rfc_20260602_013
title: wiki_graph wikilink 解析鲁棒性（剥离 code 段 + 处理表格转义管道）
author: claude
status: proposed
created: 2026-06-02
updated: 2026-06-02
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

### 修复 1：解析前剥离 code 段

在 `wiki_common.py` 新增 helper（供 graph 复用，未来 lint 若需也可用）：

```python
def strip_code_spans(text: str) -> str:
    """把 fenced block 和 inline code 替换成等长空白，保留其余文本与长度/换行。"""
```

- 先剥 **fenced block**（``` ``` ``` 与 `~~~`，含语言标注行），再剥 **inline code**（`` ` ``…`` ` ``，含多反引号 `` `` `` 包裹）。
- 替换成等长空白（保留换行）而非删除，避免打乱后续可能的 offset/行号。
- `build_edges` 提取 wikilink 时改用 `strip_code_spans(doc.body)`。

### 修复 2：`parse_wikilink` 处理转义管道

```python
def parse_wikilink(raw: str) -> str:
    raw = raw.replace("\\|", "|")          # 表格转义管道还原
    target = raw.split("|", 1)[0].split("#", 1)[0]
    return target.strip().rstrip("\\").strip()   # 兜底去尾部反斜杠
```

`[[trust-quality-loop\|可信度]]` → `trust-quality-loop`。与 Obsidian 表格行为一致。

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

### 零回归验证
- personal 实例：修复后 dangling 应从 6（全 false-positive）降到 **0**；真实 wikilink 边（正常 `[[slug|显示]]`）不变。
- 表格内 wikilink（如恢复 journey 时间线的 `[[slug\|显示]]`）应能正确解析、不 dangling。
- content_hash 变化属**预期**（去掉假 wikilink 边/dangling 是正确变化）；需断言"真实页间边集合不减少"，仅减少假边。
- 引擎实例：dangling 数不增（其元知识页 toolchain-usage 同样含 code 内示例，修复后应同步降噪）。

## Review by codex · YYYY-MM-DD

（待 Codex 追加）

## Decision

（待用户填写，或授权某 Agent 代写）

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
