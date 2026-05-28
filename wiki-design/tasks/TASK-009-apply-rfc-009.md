---
id: task_20260528_009
title: Apply RFC-009 — wikilink 约定（wiki_graph lookup + 迁移 4 页 + 文档同步）
author: claude
executor: codex
status: pending
type: apply
created: 2026-05-28
updated: 2026-05-28
related_rfcs:
  - rfc_20260528_009
---

# TASK-009: Apply RFC-009 — wikilink 约定标准化

## 目标

落地 `[[slug|显示文本]]` wikilink 约定。执行完成后：

- `wiki_graph` lookup 保证 alias 优先 + 路径 key + slug 歧义 `ambiguous_wikilink`
- 4 个现有 wiki 页 wikilink 迁移为 `[[slug|标题]]`
- 03 增 wikilink 约定段；01/05/02/.wiki-schema.md 示例同步；README 补说明
- Obsidian 点击 wikilink 不再建空桩

## 前置条件

- 仓库根：`/Users/zhangjunwu/workspace/llm-wiki/llm-wiki`
- HEAD 含 **RFC-009 status: accepted**（commit `24c4b9a` 及之后）
- working tree clean（先手动删 2 个 Obsidian 空桩：`knowledge/RFC + Task 协作协议.md`、`knowledge/知识库 Schema 与页面规则.md`）
- 已读 RFC-009 全文（含 Decision 6 条约束 + v1/v2 review）
- 已读 `scripts/wiki_graph.py` 的 `parse_wikilink()` / `build_wikilink_lookup()` 现有实现
- conda `py312` + PyYAML

## 强约束

1. **只动以下路径**：
   - `scripts/wiki_graph.py`（lookup alias 优先 + 路径 key + ambiguous）
   - `scripts/README.md`
   - `wiki-design/01-architecture.md` / `03-obsidian-graph.md` / `05-contracts-and-next-steps.md` / `02-workflows.md`
   - `knowledge/.wiki-schema.md`
   - `knowledge/wiki/synthesis/llm-wiki-architecture.md`
   - `knowledge/wiki/topics/rfc-task-protocol.md` / `wiki-schema-rules.md` / `toolchain-usage.md`
2. 本 TASK-009 文件按 Step 0 / 末步编辑；RFC-009 按倒数第二步追加 Applied。
3. **不动** `wiki_lint.py` / `wiki_common.py`（本 task 不碰 lint）、其它 RFC/task、AGENTS.md、.gitignore、其它 knowledge 页。
4. **canonical `related_ids` 不变**（只改显示层 wikilink + `related:` 字段）。
5. 必须先经 Codex spec review（Step 0）。
6. PyYAML 唯一外部依赖；preflight 必跑（conda py312）。
7. **wiki_graph 改动零回归**：重跑 RFC-007 fixture（content_hash）+ RFC-008 零回归（结构等价），任一回归即失败。
8. **alias 优先不可破坏 RFC-004**：lookup 改动必须保证 entity 别名 key 不被同名 slug/title 覆盖。
9. commit 拆三个：apply 改动 / RFC-009 Applied / task done。

## 工作流

```
Step 0  Codex spec review + commit
        ▼
Step 1  抓 baseline（改 wiki_graph 前）：knowledge/ 现状 + 一个回归 fixture，
        存 graph content_hash + lint --json（去时间字段）
        ▼
Step 2  改 wiki_graph.py：build_wikilink_lookup alias 优先 + 路径 key 登记 +
        slug 歧义 ambiguous_wikilink（insights）
        ▼
Step 3  迁移 4 页 wikilink → [[slug|标题]]（正文 + related: 字段）
        ▼
Step 4  文档同步：03 wikilink 约定段 / 01·05·02·.wiki-schema 示例 / README
        ▼
Step 5  自检验证
          5a 零回归：RFC-007 fixture content_hash + RFC-008 结构等价
          5b 4 页迁移后：wiki_lint exit 0 + wiki_graph 0 dangling + related 边数不变
          5c RFC-009 专项 4 断言：管道建边 / 重复 slug ambiguous / 路径消歧 / alias 优先
        ▼
Step 6  commit apply [apply rfc-009]
Step 7  RFC-009 追加 ## Applied in <Step6 sha> + commit [rfc-009]
Step 8  task done + Execution log + commit [task]
```

## 步骤

### Step 0：Spec review

末尾追加 `## Spec review by codex · 2026-05-28`，检查：完整性（6 约束覆盖）/ 可执行性（lookup 改法 + 5c 断言机械可跑）/ 边界（不碰 lint，related_ids 不变）/ 风险。commit `[task] TASK-009 spec review by codex (conclusion: <...>)`。

### Step 1：抓 baseline（改 wiki_graph 前）

```bash
conda activate py312; set +e
# 现状 knowledge/（4 页）graph content_hash + lint
python scripts/wiki_graph.py --json 2>/dev/null | python3 -c "import json,sys;print('before graph content_hash:', json.load(sys.stdin)['content_hash'])"
# 复用 TASK-008 的 mk_regress 回归 fixture（注入 knowledge/ → 抓 hash → 还原），存 /tmp/g009_before.txt
```

> baseline 用于 Step 5a 证明 wiki_graph 改动对**现有边投影零影响**（content_hash 不变）。

### Step 2：wiki_graph lookup 改造

按 RFC-009 Decision #1 #2：

- 保留 `parse_wikilink()` 现有管道/heading 剥离
- **`build_wikilink_lookup()` 改造**：保证 `normalized_alias_index` key 优先——两阶段 lookup（先 alias，未命中再 slug/path），或 add_lookup 不覆盖 alias key
- **补路径 key 登记**：除 `Path(doc.rel).stem`（basename slug）外，登记实例根相对路径去 `.md`（如 `wiki/topics/foo`）
- target 解析：含 `/` → 路径精确匹配；不含 `/` → basename slug；basename 重复 → 不建边 + `ambiguous_wikilink`
- `ambiguous_wikilink` **只进 graph-insights.md**（与 dangling 并列段），不进 graph-data.json

### Step 3：迁移 4 页

| 文件 | wikilink 改动 |
| --- | --- |
| `synthesis/llm-wiki-architecture.md` | `[[RFC + Task 协作协议]]`→`[[rfc-task-protocol\|RFC + Task 协作协议]]`；`[[知识库 Schema 与页面规则]]`→`[[wiki-schema-rules\|知识库 Schema 与页面规则]]`；`[[工具链与使用说明]]`→`[[toolchain-usage\|工具链与使用说明]]` |
| `topics/rfc-task-protocol.md` | `[[llm-wiki 系统架构]]`→`[[llm-wiki-architecture\|llm-wiki 系统架构]]` |
| `topics/wiki-schema-rules.md` | `[[llm-wiki 系统架构]]` / `[[工具链与使用说明]]` → slug 形 |
| `topics/toolchain-usage.md` | `[[llm-wiki 系统架构]]` / `[[知识库 Schema 与页面规则]]` → slug 形 |

正文 + frontmatter `related:` 字段都改；**`related_ids` canonical 不动**。

### Step 4：文档同步

- `03-obsidian-graph.md`：新增「wikilink 约定」段（slug-based + 管道 + 路径消歧 + ambiguous）
- `01-architecture.md`：`[[某篇来源摘要]]`/`[[LightRAG]]`/`[[Agent-native Wiki]]` 等标题形示例改 slug 形或标注占位
- `05` / `02` / `knowledge/.wiki-schema.md`：answer-reference + entity alias 示例改 `[[slug|display]]`，**保留 RFC-004「别名不包 wikilink」语义**（正确 `self-attention（正名 [[attention|Attention]]）`）
- `scripts/README.md`：wiki-graph 段补管道/路径/ambiguous 说明

### Step 5：自检验证

```bash
conda activate py312; set +e
PASS=1; fail(){ echo "  FAIL: $1"; PASS=0; }

echo "=== 5a 零回归 ==="
# RFC-007 fixture（复制 TASK-007 Step7c）：content_hash 仍确定一致
# RFC-008 结构等价（复制 TASK-008 Step7a-1 mk_regress + strip diff）
# >>> 粘贴 TASK-007 Step7c + TASK-008 7a-1 <<<
# 关键：现有 knowledge/ 4 页 graph content_hash == Step1 baseline（wikilink target 从标题变 slug
#       但都解析到同一 id，related/wikilink 边不变 → content_hash 应不变）

echo "=== 5b 4 页迁移后 ==="
python scripts/wiki_lint.py --check-only >/dev/null 2>&1; [ $? = 0 ] && echo "  OK lint exit0" || fail "lint"
python scripts/wiki_graph.py --json 2>/dev/null | python3 -c "
import json,sys; g=json.load(sys.stdin)
rel=[e for e in g['edges'] if e['relation']=='related']
wl=[e for e in g['edges'] if e['relation']=='wikilink']
print(f'  related 边: {len(rel)} (期望 6) · wikilink 边: {len(wl)} (期望 6)')
"
grep -A2 "Dangling Wikilinks" knowledge/maps/graph-insights.md | grep -q "(none)" && echo "  OK 0 dangling" || fail "dangling 非空"

echo "=== 5c RFC-009 专项（临时实例 knowledge-gtest/，knowledge/ 外）==="
# 断言 1: [[slug|Title]] 建 wikilink 边
# 断言 2: 重复 basename slug → 不建边 + ambiguous_wikilink insights
# 断言 3: [[wiki/topics/foo|Foo]] 路径消歧建边
# 断言 4: entity 别名 key == 某 slug 时 alias 优先（建别名页 + 同名 slug topic，[[name]] 解析到正名 entity）
# >>> 见下方 fixture 脚本，trap 清理 <<<

echo "=== PASS=$PASS ==="; [ "$PASS" = 1 ] || exit 1
```

> 5a/5c 的完整脚本：5a 复制 TASK-007 Step7c + TASK-008 Step7a-1（不复制各自 F/白名单段）；5c 仿 TASK-008 7b 的临时实例 + trap 清理，建 4 个断言 fixture。executor 写死成可跑 shell，贴完整输出进 Execution log。

### Step 6~8：commit apply / RFC Applied / task done

三 commit 拆分；apply 前 `git status` 确认只动白名单 + 无 knowledge-gtest 残留 + maps/ 派生层 ignore 不入库。

## 完成后报告格式

`## Execution log by codex · 2026-05-28`：步骤完成情况 + Step 5 全部输出（5a 零回归 + 5b 边数 + 5c 4 断言）+ 3 commit sha + 偏离/异常。

## Spec review by codex · YYYY-MM-DD

（待 Codex 填写）

## Execution log by codex · YYYY-MM-DD

（待执行者填写）

## Evaluation by claude · YYYY-MM-DD

（待评估者填写）
