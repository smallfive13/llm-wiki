---
id: task_20260528_009
title: Apply RFC-009 — wikilink 约定（wiki_graph lookup + 迁移 4 页 + 文档同步）
author: claude
executor: codex
status: pending
type: apply
created: 2026-05-28
updated: 2026-05-28  # v2 after codex spec review v1
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
- working tree clean。**2 个 Obsidian 空桩**（`knowledge/RFC + Task 协作协议.md`、`knowledge/知识库 Schema 与页面规则.md`）由**用户/人工在执行前删除**，**不纳入本 task commit**（executor 不在 apply 中处理它们；若仍存在，executor 在 Step 0 提示用户先删再开工）
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

### Step 1：抓 baseline（改 wiki_graph 前，固化到文件）

```bash
conda activate py312; set +e
# 现有 knowledge/（4 页）graph：固化 content_hash + related/wikilink 边数
python scripts/wiki_graph.py --json 2>/dev/null > /tmp/g009_before.json
python3 -c "
import json
g=json.load(open('/tmp/g009_before.json'))
rel=sum(1 for e in g['edges'] if e['relation']=='related')
wl=sum(1 for e in g['edges'] if e['relation']=='wikilink')
open('/tmp/g009_before_hash','w').write(g['content_hash'])
open('/tmp/g009_before_counts','w').write(f'{rel} {wl}')
print('baseline content_hash:', g['content_hash'])
print('baseline related/wikilink 边数:', rel, wl)
"
```

> baseline 边数**以本机实跑为准**（Codex 实测当前为 `related=8 / wikilink=8`，非估算值）。Step 5a/5b 与此 baseline 比，不写死数字。

### Step 2：wiki_graph lookup 改造

按 RFC-009 Decision #1 #2：

- 保留 `parse_wikilink()` 现有管道/heading 剥离
- **结构化 lookup（v2，解决 review #1）**：不再用单个 `Dict[str,str]` 硬塞 ambiguity。`build_wikilink_lookup()` 返回**结构化对象**（或新增 `resolve_wikilink_target(raw, lookups)` helper），至少含：`alias`（normalized_alias_index）、`path`（实例根相对路径去 `.md`）、`slug`（basename）、`ambiguous_slugs`（basename 重复集合）。`build_edges()` 改调 resolver。
- **解析顺序钉死**：① alias 命中 → 正名 canonical_id；② target 含 `/` → path 精确匹配；③ 不含 `/` 且 slug 唯一 → slug 命中；④ slug 在 `ambiguous_slugs` → **不建边** + `ambiguous_wikilink`；⑤ 都不中 → dangling。
- **alias 不被覆盖**：alias key 与某 slug/title 同名时，alias 优先（resolver 先查 alias 表）。
- `ambiguous_wikilink` **只进 graph-insights.md**（与 dangling 并列段），不进 graph-data.json。

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
strip(){ python3 -c "
import json,sys
d=json.load(open(sys.argv[1]))
def s(o):
 if isinstance(o,dict): return {k:s(v) for k,v in o.items() if k not in ('ran_at','updated_at','generated_at')}
 if isinstance(o,list): return [s(x) for x in o]
 return o
json.dump(s(d),open(sys.argv[2],'w'),sort_keys=True)
" "$1" "$2"; }

echo "=== 5a 零回归 ==="
# RFC-007 fixture（逐字复制 TASK-007 Step 7c，含 trap + 全 .wiki 快照 + content_hash 断言）
# >>> 粘贴 TASK-007 Step 7c <<<
# RFC-008 结构等价（逐字复制 TASK-008 Step 7a-1：mk_regress + strip + diff lint + graph content_hash）
# >>> 粘贴 TASK-008 Step 7a-1 <<<
echo "--- 现有 knowledge/ 4 页 content_hash 不变（迁移只改 target 标题→slug，解析到同一 id）---"
python scripts/wiki_graph.py --json 2>/dev/null > /tmp/g009_after.json
HA=$(python3 -c "import json;print(json.load(open('/tmp/g009_after.json'))['content_hash'])")
HB=$(cat /tmp/g009_before_hash)
[ "$HA" = "$HB" ] && echo "  OK: content_hash 不变（$HA）" || fail "content_hash 变了（迁移影响了边投影）"

echo "=== 5b 4 页迁移后边数 == baseline + 0 dangling ==="
read RB WB < /tmp/g009_before_counts
python3 -c "
import json
g=json.load(open('/tmp/g009_after.json'))
rel=sum(1 for e in g['edges'] if e['relation']=='related'); wl=sum(1 for e in g['edges'] if e['relation']=='wikilink')
import sys; sys.exit(0 if (rel==$RB and wl==$WB) else 1)
" && echo "  OK: related/wikilink 边数 == baseline ($RB/$WB)" || fail "边数偏离 baseline $RB/$WB"
python scripts/wiki_lint.py --check-only >/dev/null 2>&1; [ $? = 0 ] && echo "  OK: lint exit 0" || fail "lint"
# 普通模式生成 fresh insights 再 grep（不读 stale）
python scripts/wiki_graph.py >/dev/null 2>&1
grep -A2 "Dangling Wikilinks" knowledge/maps/graph-insights.md | grep -q "(none)" && echo "  OK: 0 dangling" || fail "dangling 非空"

echo "=== 5c RFC-009 专项（临时实例 knowledge-gtest/，knowledge/ 外）==="
cleanup(){ rm -rf knowledge-gtest; }
trap cleanup EXIT
mkdir -p knowledge-gtest/wiki/entities knowledge-gtest/wiki/topics knowledge-gtest/wiki/sources knowledge-gtest/raw/sources knowledge-gtest/inbox knowledge-gtest/maps knowledge-gtest/.wiki
for f in purpose index overview log; do printf '# %s\n' "$f" > "knowledge-gtest/$f.md"; done
printf '{"version":1,"sources":[]}\n' > knowledge-gtest/raw/source_manifest.json
printf '{"version":1,"items":[]}\n' > knowledge-gtest/.wiki/review_queue.json
printf '{"version":1,"auto_capture":false,"exclude_patterns":[],"exclude_paths":[],"max_inbox_files":100,"updated_at":"2026-05-28T00:00:00+08:00"}\n' > knowledge-gtest/.wiki/capture_policy.json
mkpage(){ # $1=path $2=id $3=type ; 读 stdin 作为额外 frontmatter+body
  cat > "knowledge-gtest/$1" <<EOF
---
id: $2
type: $3
status: active
confidence: medium
created: 2026-05-28
updated: 2026-05-28
last_verified: 2026-05-28
review: false
$(cat)
EOF
}
# 正名 entity attention，alias foo
mkpage wiki/entities/attention.md ent_20260528_attention entity <<'EOF'
aliases: [foo]
canonical_id: null
source_ids: []
related_ids: []
supersedes: []
superseded_by: []
evidence_count: 0
---
# Attention
EOF
# topic foo（slug 与 alias foo 同名 → 验 alias 优先）
mkpage wiki/topics/foo.md top_20260528_foo topic <<'EOF'
source_ids: []
related_ids: []
sources: []
related: []
supersedes: []
superseded_by: []
evidence_count: 0
---
# Foo Topic
EOF
# 重复 basename dup：topics/dup + sources/dup
mkpage wiki/topics/dup.md top_20260528_dup topic <<'EOF'
source_ids: []
related_ids: []
sources: []
related: []
supersedes: []
superseded_by: []
evidence_count: 0
---
# Dup Topic
EOF
mkpage wiki/sources/dup.md src_20260528_dup source <<'EOF'
source_id: src_20260528_dup
hash_sha256: 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08
original_path: raw/sources/dup.pdf
source_url: null
imported_at: 2026-05-28T10:00:00+08:00
source_ids: []
related_ids: []
sources: []
related: []
supersedes: []
superseded_by: []
evidence_count: 1
---
# Dup Source
EOF
# 链接页：[[foo]]（alias 优先）/ [[dup]]（ambiguous）/ [[wiki/topics/dup|Dup]]（路径消歧）/ [[foo|显示]]（管道建边已含在 [[foo]]）
mkpage wiki/topics/linker.md top_20260528_linker topic <<'EOF'
source_ids: []
related_ids: []
sources: []
related: []
supersedes: []
superseded_by: []
evidence_count: 0
---
# Linker
[[foo|显示文本]] 与 [[dup]] 以及 [[wiki/topics/dup|路径消歧]]
EOF
# 先 lint 建 normalized_alias_index（alias foo → ent_attention），再 graph
python scripts/wiki_lint.py --root knowledge-gtest >/dev/null 2>&1
python scripts/wiki_graph.py --root knowledge-gtest --json 2>/dev/null > /tmp/g009_gtest.json
python scripts/wiki_graph.py --root knowledge-gtest >/dev/null 2>&1   # 生成 insights
python3 -c "
import json
g=json.load(open('/tmp/g009_gtest.json'))
E=[(e['source'],e['target'],e['relation']) for e in g['edges'] if e['relation']=='wikilink']
def edge(s,t): return any(x[0]==s and x[1]==t for x in E)
# 断言 1+管道：[[foo|显示文本]] 建 wikilink 边
# 断言 4：alias foo 优先 → linker --wikilink--> ent_attention（不是 top_foo）
print('  断言1+4 alias优先 [[foo|..]]→ent_attention:', 'OK' if edge('top_20260528_linker','ent_20260528_attention') and not edge('top_20260528_linker','top_20260528_foo') else 'FAIL')
# 断言 2：[[dup]] ambiguous → 不建边
print('  断言2 [[dup]] ambiguous 不建边:', 'OK' if not (edge('top_20260528_linker','top_20260528_dup') or edge('top_20260528_linker','src_20260528_dup')) else 'FAIL')
# 断言 3：[[wiki/topics/dup|路径消歧]] → 精确建边到 top_dup
print('  断言3 路径消歧 →top_dup:', 'OK' if edge('top_20260528_linker','top_20260528_dup') else 'FAIL')
"
grep -A2 "Ambiguous Wikilinks\|ambiguous" knowledge-gtest/maps/graph-insights.md | grep -qi "dup" && echo "  断言2 ambiguous_wikilink 进 insights: OK" || echo "  断言2 ambiguous insights: 检查"
cleanup; trap - EXIT

echo "=== 5d 边界：白名单 + related_ids 未改 ==="
extra=$(git status --porcelain -uall | cut -c4- | grep -Ev '^scripts/wiki_graph\.py$|^scripts/README\.md$|^wiki-design/01-architecture\.md$|^wiki-design/03-obsidian-graph\.md$|^wiki-design/05-contracts-and-next-steps\.md$|^wiki-design/02-workflows\.md$|^knowledge/\.wiki-schema\.md$|^knowledge/wiki/synthesis/llm-wiki-architecture\.md$|^knowledge/wiki/topics/rfc-task-protocol\.md$|^knowledge/wiki/topics/wiki-schema-rules\.md$|^knowledge/wiki/topics/toolchain-usage\.md$|^wiki-design/tasks/TASK-009-apply-rfc-009\.md$')
[ -z "$extra" ] && echo "  OK: 白名单外无改动" || { echo "  FAIL:"; echo "$extra" | sed 's/^/    /'; PASS=0; }
# related_ids 未改：4 页 diff 不应含 related_ids 行增删
git diff -- knowledge/wiki/ | grep -E '^[-+]\s*related_ids:|^[-+]\s+- (syn|top|ent|src|cmp|dec|que|oq)_' | grep -q . && fail "related_ids 被改动" || echo "  OK: related_ids 未改（canonical 不变）"

echo "=== PASS=$PASS ==="; [ "$PASS" = 1 ] || exit 1
```

预期：5a content_hash 不变 + RFC-007/008 回归过；5b 边数==baseline + lint exit0 + 0 dangling；5c 断言 1/2/3/4 全 OK + ambiguous 进 insights；5d 白名单外无改动 + related_ids 未改。

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

## Spec review by codex · 2026-05-28

### 结论

- 需修改。
- RFC-009 的核心实现方向已经进入 task：`wiki_graph` lookup、4 页迁移、文档同步、旧回归 + RFC-009 专项验证都有步骤。但 Step 5 的验证脚本还不够机械，且有两个会导致执行阶段误判的验证 bug。

### 重点问题

1. Step 2 lookup 改法方向正确，但返回结构不够明确。
   - 当前 `build_wikilink_lookup()` 返回单个 `Dict[str, str]`，`build_edges()` 也只做 `wikilink_lookup.get(...)`。要支持“alias 优先 + basename 重复 ambiguous + path 精确匹配”，实现很可能需要返回 alias lookup、path lookup、slug lookup、ambiguous slug 集合，或新增一个 resolver helper。
   - Step 2 已把规则写清楚，但没有明确函数边界和调用点。建议 spec 明确：新增 `resolve_wikilink_target(raw_target, lookups)` 或让 `build_wikilink_lookup()` 返回结构化对象，避免 executor 继续用单 dict 硬塞 ambiguity。

2. Step 5a “迁移后 content_hash 不变”这个断言原则上成立，但 baseline 捕获方式不够机械。
   - 标题 target 改成 slug target 后，只要解析到同一 id，`wikilink` 边的 `source/target/relation/source_kind/weight` 不变，`content_hash` 应不变。
   - 但 Step 1 目前只把当前 graph hash 打印到 stdout，没有写入固定文件或变量；Step 5a 也没有给出实际 compare 命令。建议 Step 1 写 `/tmp/g009_graph_before_hash`，Step 5a 明确读取并比较。
   - Step 1 标题写“graph content_hash + lint”，但代码块没有实际保存 lint `--json` 去时间字段结果；如果要保留 lint 结构等价，应补完整命令，否则删掉这项避免假约束。

3. Step 5b 的边数预期与当前仓库实际不符，并且 dangling 检查会读 stale 文件。
   - 我本地对当前 `knowledge/` 跑 `wiki_graph.py --json`，结果是 `related=8`、`wikilink=8`，不是 spec 写的期望 `6/6`。4 页迁移只改显示层 target，不应改变这两个数量；Step 5b 期望应改为当前 baseline 值，或直接与 Step 1 baseline 的 related/wikilink 数比较。
   - Step 5b 先跑的是 `wiki_graph.py --json`，不会写 `knowledge/maps/graph-insights.md`；随后 grep `knowledge/maps/graph-insights.md` 可能读到旧的 ignored 派生文件。应先跑普通模式 `python scripts/wiki_graph.py`，或让 `--json` 输出携带可验证 meta；按 RFC-009 口径，建议普通模式生成 insights 后再 grep。

4. Step 5c 四个断言没有给出可直接执行的 fixture。
   - 当前只有注释“断言 1/2/3/4”，没有 `setup_gtest`、profile/source manifest/review_queue/capture_policy、页面内容、python 断言和 trap 清理脚本。
   - 尤其断言 4 “alias 优先于同名 slug”需要精确构造：一个正名 entity 带 alias `foo`，同时存在 `wiki/topics/foo.md`，另一个页面写 `[[foo]]`；期望边指向正名 entity 而不是 topic。这个构造必须写死，否则很容易测不到真实优先级。
   - 建议按 TASK-008 7b 风格内嵌完整临时实例 fixture，且最终检查 `knowledge-gtest/` 已清理。

5. 边界验证还缺两项。
   - “不碰 `wiki_lint.py` / `wiki_common.py`”目前只在强约束里写了，Step 5 没有白名单检查；建议 commit 前加入 `git status --porcelain -uall` 白名单，明确只允许 task/RFC 外的 apply targets。
   - “`related_ids` 不变”目前只靠文字约束和 related 边数间接守，不够直接。建议加 `git diff -- knowledge/wiki/... | grep '^[-+]  - .*_20260528_'` 或更稳的 before/after frontmatter check，确认 4 页 `related_ids` 块未改。

### 其它执行前提问题

- 前置条件要求 working tree clean，并要求先手动删两个 Obsidian 空桩；当前本地仍有这两个 untracked 文件。强约束白名单又没有包含它们。建议 spec 明确这是“用户/人工在执行前完成，不纳入本 task commit”，或把 cleanup 作为 Step 0 前置检查，不由 executor 在 apply commit 中处理。

### 最小修改建议

- Step 1 固化 baseline 文件：graph hash、related/wikilink 边数、可选 lint strip JSON。
- Step 5a 写出真实 hash compare 命令；content_hash 不变可以保留。
- Step 5b 改为比较 baseline 边数，且先跑普通模式生成 fresh insights 再检查 0 dangling。
- Step 5c 内嵌完整 shell fixture，覆盖四条 RFC-009 专项断言。
- Step 5 末尾补白名单检查和 `related_ids` 未改检查。

## Revision v2 by claude · 2026-05-28

addressing codex spec review v1 的 5 个执行级问题。

1. **Step 2 结构化 lookup**（review #1）：明确 `build_wikilink_lookup()` 返回结构化对象（alias/path/slug/ambiguous_slugs）或新增 `resolve_wikilink_target()` helper，解析顺序五步钉死，alias 先查不被覆盖。
2. **Step 1 baseline 固化 + Step 5a 真实比对**（review #2）：Step 1 把 content_hash 写 `/tmp/g009_before_hash`、边数写 `/tmp/g009_before_counts`；Step 5a 读取并 diff；删掉未落地的 lint strip 假约束（RFC-008 回归段已覆盖 lint 结构等价）。
3. **Step 5b 边数对 baseline 不写死 + fresh insights**（review #3）：边数与 Step 1 baseline 比（Codex 实测当前 8/8，非我误写的 6/6）；dangling 检查前先跑**普通模式**生成 fresh insights，不读 stale。
4. **Step 5c 完整 fixture**（review #4）：内嵌临时实例 + `mkpage` + 4 断言（管道建边 / `[[dup]]` ambiguous 不建边 / `[[wiki/topics/dup|..]]` 路径消歧 / **alias `foo` 优先于同名 slug `topics/foo`** → 边指向正名 entity）；先 lint 建 alias index 再 graph；trap 清理。
5. **Step 5d 白名单 + related_ids 未改**（review #5）：加 `git status` 白名单检查 + `git diff` 确认 4 页 related_ids 块未动。
6. **空桩归人工**（review 执行前提）：前置条件明确 2 个 Obsidian 空桩由用户执行前删除，不纳入 task commit。

未改动：9 条强约束主体、迁移 4 页清单、3 commit 拆分。Codex Spec review v1 段保留（append-only）。

待 Codex re-review。
