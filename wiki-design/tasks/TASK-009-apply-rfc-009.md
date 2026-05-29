---
id: task_20260528_009
title: Apply RFC-009 — wikilink 约定（wiki_graph lookup + 迁移 4 页 + 文档同步）
author: claude
executor: codex
status: done
type: apply
created: 2026-05-28
updated: 2026-05-28  # v3 after codex spec review v2
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

echo "=== 5a 现有 knowledge/ 零回归（content_hash 不变）==="
# TASK-009 只改 wiki_graph 的 wikilink 解析，不碰 wiki_lint/BASE_SCHEMA → 不重跑 RFC-008 lint 回归。
# 现有 knowledge/ 4 页迁移只把 wikilink target 从标题改为 slug，解析到同一 id：
# content_hash 涵盖全部 节点+边+社区，若 wikilink 重构破坏任何现有边投影，hash 必变。
# wiki_graph 对非 wikilink 边类型（source_ref/related/supersedes/co_source/redirect 折叠）
# 的回归，由 5c 临时实例的 R1/R2/R3 断言覆盖（现有 4 页不含这些边）。
python scripts/wiki_graph.py --json 2>/dev/null > /tmp/g009_after.json
HA=$(python3 -c "import json;print(json.load(open('/tmp/g009_after.json'))['content_hash'])")
HB=$(cat /tmp/g009_before_hash)
[ "$HA" = "$HB" ] && echo "  OK: content_hash 不变（$HA）" || fail "content_hash 变了（迁移影响了边投影）"

echo "=== 5b 边数 == baseline + lint exit0 + 0 dangling ==="
read RB WB < /tmp/g009_before_counts
python3 -c "
import json,sys
g=json.load(open('/tmp/g009_after.json'))
rel=sum(1 for e in g['edges'] if e['relation']=='related'); wl=sum(1 for e in g['edges'] if e['relation']=='wikilink')
sys.exit(0 if (rel==$RB and wl==$WB) else 1)
" && echo "  OK: related/wikilink 边数 == baseline ($RB/$WB)" || fail "边数偏离 baseline $RB/$WB"
python scripts/wiki_lint.py --check-only >/dev/null 2>&1; [ $? = 0 ] && echo "  OK: lint exit 0" || fail "lint"
python scripts/wiki_graph.py >/dev/null 2>&1   # 普通模式生成 fresh insights，不读 stale
grep -A2 "Dangling Wikilinks" knowledge/maps/graph-insights.md | grep -q "(none)" && echo "  OK: 0 dangling" || fail "dangling 非空"

echo "=== 5c RFC-009 专项 + wiki_graph 边类型回归（临时实例 knowledge-gtest/）==="
cleanup(){ rm -rf knowledge-gtest /tmp/g009_gtest.json; }
trap cleanup EXIT
mkdir -p knowledge-gtest/wiki/entities knowledge-gtest/wiki/topics knowledge-gtest/wiki/sources knowledge-gtest/raw/sources knowledge-gtest/inbox knowledge-gtest/maps knowledge-gtest/.wiki
for f in purpose index overview log; do printf '# %s\n' "$f" > "knowledge-gtest/$f.md"; done
printf '{"version":1,"sources":[]}\n' > knowledge-gtest/raw/source_manifest.json
printf '{"version":1,"items":[]}\n' > knowledge-gtest/.wiki/review_queue.json
printf '{"version":1,"auto_capture":false,"exclude_patterns":[],"exclude_paths":[],"max_inbox_files":100,"updated_at":"2026-05-28T00:00:00+08:00"}\n' > knowledge-gtest/.wiki/capture_policy.json
mkpage(){ # $1=path $2=id $3=type ; stdin = 额外 frontmatter + body
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
# --- 别名优先 fixture：正名 entity attention，alias foo；topic foo（slug 与 alias 同名）---
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
# --- 重复 basename dup：topics/dup + sources/dup ---
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
# --- 边类型回归 fixture：srcD + topicC(source_ref→srcD) + topicE(与 C 共享 srcD → co_source) ---
mkpage wiki/sources/srcd.md src_20260528_srcd source <<'EOF'
source_id: src_20260528_srcd
hash_sha256: 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08
original_path: raw/sources/srcd.pdf
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
# Src D
EOF
mkpage wiki/topics/tc.md top_20260528_tc topic <<'EOF'
source_ids: [src_20260528_srcd]
related_ids: []
sources: []
related: []
supersedes: []
superseded_by: []
evidence_count: 1
---
# Topic C
EOF
mkpage wiki/topics/te.md top_20260528_te topic <<'EOF'
source_ids: [src_20260528_srcd]
related_ids: []
sources: []
related: []
supersedes: []
superseded_by: []
evidence_count: 1
---
# Topic E
EOF
# --- 三个独立链接页（拆分，避免边去重掩盖 ambiguous）---
mkpage wiki/topics/linker-alias.md top_20260528_linker-alias topic <<'EOF'
source_ids: []
related_ids: []
sources: []
related: []
supersedes: []
superseded_by: []
evidence_count: 0
---
# Linker Alias
正文 [[foo|显示文本]]
EOF
mkpage wiki/topics/linker-amb.md top_20260528_linker-amb topic <<'EOF'
source_ids: []
related_ids: []
sources: []
related: []
supersedes: []
superseded_by: []
evidence_count: 0
---
# Linker Amb
正文 [[dup]]
EOF
mkpage wiki/topics/linker-path.md top_20260528_linker-path topic <<'EOF'
source_ids: []
related_ids: []
sources: []
related: []
supersedes: []
superseded_by: []
evidence_count: 0
---
# Linker Path
正文 [[wiki/topics/dup|路径消歧]]
EOF
# 先 lint 建 normalized_alias_index（alias foo → ent_attention），再 graph
python scripts/wiki_lint.py --root knowledge-gtest >/dev/null 2>&1
python scripts/wiki_graph.py --root knowledge-gtest --json 2>/dev/null > /tmp/g009_gtest.json
python scripts/wiki_graph.py --root knowledge-gtest >/dev/null 2>&1   # 生成 insights
python3 - <<'PY'
import json,sys
g=json.load(open('/tmp/g009_gtest.json'))
def has(s,t,rel=None):
    return any(e['source']==s and e['target']==t and (rel is None or e['relation']==rel) for e in g['edges'])
fails=[]
# 边类型回归（证明 wikilink 重构未误伤其他边）
if not has('top_20260528_tc','src_20260528_srcd','source_ref'): fails.append('R1 source_ref tc→srcd')
if not (has('top_20260528_tc','top_20260528_te','co_source') or has('top_20260528_te','top_20260528_tc','co_source')): fails.append('R2 co_source tc<->te')
# 新功能断言
# A1 + 管道 + alias 优先：[[foo|显示文本]] → ent_attention（不是 top_foo）
if not has('top_20260528_linker-alias','ent_20260528_attention','wikilink'): fails.append('A1 alias优先 linker-alias→ent_attention')
if has('top_20260528_linker-alias','top_20260528_foo'): fails.append('A1 误连 top_foo（alias 未优先）')
# A2 ambiguous：[[dup]] 独立页，到 dup 任何 target 都不应建边
if has('top_20260528_linker-amb','top_20260528_dup') or has('top_20260528_linker-amb','src_20260528_dup'):
    fails.append('A2 [[dup]] ambiguous 误建边')
# A3 路径消歧：[[wiki/topics/dup|..]] → top_dup
if not has('top_20260528_linker-path','top_20260528_dup','wikilink'): fails.append('A3 路径消歧→top_dup')
if fails:
    print('  FAIL:', '; '.join(fails)); sys.exit(1)
print('  OK: R1/R2 边类型回归 + A1 alias优先 + A2 ambiguous + A3 路径消歧')
PY
[ $? = 0 ] || fail "5c 断言"
grep -A3 -iE "ambiguous" knowledge-gtest/maps/graph-insights.md | grep -qi "dup" && echo "  OK: ambiguous_wikilink 进 insights" || fail "ambiguous 未进 insights"
cleanup; trap - EXIT

echo "=== 5d 边界：白名单 + related_ids 未改 ==="
extra=$(git status --porcelain -uall | cut -c4- | grep -Ev '^scripts/wiki_graph\.py$|^scripts/README\.md$|^wiki-design/01-architecture\.md$|^wiki-design/03-obsidian-graph\.md$|^wiki-design/05-contracts-and-next-steps\.md$|^wiki-design/02-workflows\.md$|^knowledge/\.wiki-schema\.md$|^knowledge/wiki/synthesis/llm-wiki-architecture\.md$|^knowledge/wiki/topics/rfc-task-protocol\.md$|^knowledge/wiki/topics/wiki-schema-rules\.md$|^knowledge/wiki/topics/toolchain-usage\.md$|^wiki-design/tasks/TASK-009-apply-rfc-009\.md$')
[ -z "$extra" ] && echo "  OK: 白名单外无改动" || { echo "  FAIL:"; echo "$extra" | sed 's/^/    /'; PASS=0; }
# related_ids 未改：4 页 diff 不应含 related_ids 行或 canonical id 数组项的增删
git diff -- knowledge/wiki/ | grep -E '^[-+][[:space:]]*related_ids:|^[-+][[:space:]]+- (syn|top|ent|src|cmp|dec|que|oq)_' | grep -q . && fail "related_ids 被改动" || echo "  OK: related_ids 未改（canonical 不变）"

echo "=== PASS=$PASS ==="; [ "$PASS" = 1 ] || exit 1
```

预期：5a content_hash 不变；5b 边数==baseline + lint exit0 + 0 dangling；5c R1/R2 边类型回归 + A1 alias优先 + A2 ambiguous 不建边 + A3 路径消歧 全过 + ambiguous 进 insights；5d 白名单外无改动 + related_ids 未改。任一 fail → PASS=0 → exit 1。

### Step 6~8：commit apply / RFC Applied / task done

三 commit 拆分；apply 前 `git status` 确认只动白名单 + 无 knowledge-gtest 残留 + maps/ 派生层 ignore 不入库。

## 完成后报告格式

`## Execution log by codex · 2026-05-28`：步骤完成情况 + Step 5 全部输出（5a 零回归 + 5b 边数 + 5c 4 断言）+ 3 commit sha + 偏离/异常。

## Spec review by codex · YYYY-MM-DD

（待 Codex 填写）

## Execution log by codex · YYYY-MM-DD

（待执行者填写）

## Evaluation by claude · 2026-05-28

evaluator 在 py312 独立复跑核心断言（不只信 executor 5c）。

### 1. 协议合规 — PASS

- Step6 `c6db253` 恰好动 10 白名单文件；Step7 `3e30524` 仅 RFC-009；Step8 `2573380` 仅 TASK-009。
- working tree clean，maps/ 派生层 ignore 未入库。

### 2. canonical 不变 — PASS

- Step6 diff 中 `related_ids` **一行未动**（grep canonical id 增删为空）；只改 `related:` 显示层 + 正文 wikilink（标题形 → `[[slug|标题]]`）。
- 现有 4 页：4 节点 / 16 边（related 8 + wikilink 8），与首次结晶化一致；边集合不变（标题/slug 解析到同一 id）→ Codex 报 content_hash==baseline 成立。

### 3. wiki_graph 新逻辑正确性（evaluator 独立 fixture）— PASS

独立建临时实例（entity alias `foo` + 同名 topic slug `foo` + 重复 basename `dup` + 三个独立链接页），复跑：

- **A1 alias 优先**：`[[foo|显示]]` → `ent_attention`（**不误连** `top_foo`）✓ —— RFC-004 entity 别名优先级保住
- **管道建边**：`[[slug|display]]` 取 slug 为 target ✓
- **A2 ambiguous**：`[[dup]]`（basename 重复）→ **不建边**（独立 linker-amb 页验证，无去重掩盖）✓ + 进 insights ✓
- **A3 路径消歧**：`[[wiki/topics/dup|路径]]` → 精确建边 `top_dup` ✓

### 4. 迁移 + 0 dangling — PASS

- 4 页正文 wikilink 全迁移为 slug 形（无残留纯标题 wikilink）。
- 现有 knowledge/ 0 dangling。

### 5. 文档同步 + commit 卫生 — PASS

- `03-obsidian-graph.md` 新增「wikilink 约定」段（slug + 管道 + ambiguous + alias 优先 + 保留 RFC-004「别名不包 wikilink」语义）。
- `README` wiki-graph 段补 `[[slug|显示]]` + alias 优先说明；`01`/`05`/`02`/`.wiki-schema.md` 示例同步。
- RFC-009 `Applied in c6db253` 与 Step6 sha 对齐；Execution log 透明（无阻塞偏离）。

### 结论

**PASS**。wikilink 约定标准化落地。**Obsidian 双链现可解析**（点 `[[rfc-task-protocol|RFC + Task 协作协议]]` 跳转、不再建空桩、原生图谱无未解析节点），同时 wiki_graph 16 边继续正确投影、entity 别名优先级（RFC-004）保住。这条线完整闭环：真实使用（Obsidian 打开）→ 暴露 gap → RFC-009 → 修复，无遗留。

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

## Execution log by codex · 2026-05-28

### 步骤完成情况

- Step 1 baseline 已在改 `wiki_graph.py` 前完成：
  - baseline content_hash: `eae651f8888ed9db299f3622007186f3a523a6ff02552ba73ca40f96ca358e82`
  - baseline related/wikilink 边数: `8 8`
- Step 2 已实现 `wiki_graph.py` 结构化 wikilink lookup：
  - alias → path → slug → ambiguous → dangling 解析序
  - alias 不被同名 slug/title 覆盖
  - ambiguous wikilink 只写入 `graph-insights.md`，不进入 `graph-data.json`
- Step 3 已迁移 4 个 wiki 页正文与 `related:` 显示层 wikilink 为 `[[slug|标题]]`，未改 `related_ids`。
- Step 4 已同步 `03` 约定段、`01/02/05/.wiki-schema.md` 示例和 `scripts/README.md`。
- Step 5 全部验证通过，`PASS=1`。
- Step 6 apply commit: `c6db253`
- Step 7 RFC Applied commit: `3e30524`
- Step 8 task done commit: 本 commit

### Step 5 输出

```text
=== 5a 现有 knowledge/ 零回归（content_hash 不变）===
  OK: content_hash 不变（eae651f8888ed9db299f3622007186f3a523a6ff02552ba73ca40f96ca358e82）
=== 5b 边数 == baseline + lint exit0 + 0 dangling ===
  OK: related/wikilink 边数 == baseline (8/8)
  OK: lint exit 0
  OK: 0 dangling
=== 5c RFC-009 专项 + wiki_graph 边类型回归（临时实例 knowledge-gtest/）===
  OK: R1/R2 边类型回归 + A1 alias优先 + A2 ambiguous + A3 路径消歧
  OK: ambiguous_wikilink 进 insights
=== 5d 边界：白名单 + related_ids 未改 ===
  OK: 白名单外无改动
  OK: related_ids 未改（canonical 不变）
=== PASS=1 ===
```

### 偏离 / 异常

- 无阻塞偏离。
- Step 5 按 spec 原样执行；其中注释仍写 R1/R2/R3，但实际断言和输出为 R1/R2，这与 v3 spec review 中记录的非阻塞口径一致。

## Spec review v3 by codex · 2026-05-28

### 结论

- 通过。
- v3 已修复 v2 的 3 个阻塞点，Step 5 现在可以作为执行门禁使用；未发现新的阻塞问题。

### v2 阻塞点复核

1. 5c 断言失败会真正影响 PASS：已解决。
   - Python 断言脚本改为收集 `fails[]`，失败时 `sys.exit(1)`。
   - shell 层用 `[ $? = 0 ] || fail "5c 断言"` 接住，ambiguous insights 检查也改为 `|| fail`，不再只是打印 `FAIL`。

2. ambiguous 与路径消歧拆页：已解决。
   - `[[dup]]` 放在 `linker-amb`，`[[wiki/topics/dup|路径消歧]]` 放在 `linker-path`。
   - A2 断言只检查 `linker-amb` 到 `top_dup/src_dup` 不建边，A3 断言只检查 `linker-path -> top_dup`，不再被 `(source,target,relation,source_kind)` 去重掩盖。

3. 5a 去粘贴占位并自包含：已解决。
   - TASK-007/TASK-008 外部粘贴占位已移除。
   - 当前 5a 用现有 `knowledge/` 的 `content_hash` 与 baseline 比对；非 wikilink 边回归由 5c fixture 的 R1/R2 自包含覆盖。考虑到本 task 不碰 `wiki_lint.py` / `wiki_common.py` / BASE_SCHEMA，这个边界是合理的。

### fixture 可执行性

- `mkpage` heredoc 结构可机械生成合法 frontmatter/body，`--root knowledge-gtest` 与当前 `wiki_lint.py` / `wiki_graph.py` CLI 兼容。
- fixture 覆盖 alias 优先、管道 target、ambiguous slug、路径消歧、`source_ref`、`co_source`；先 lint 生成 `normalized_alias_index.json` 再 graph，顺序正确。
- `cleanup` + `trap` 能清理 `knowledge-gtest/` 和 `/tmp/g009_gtest.json`；Step 5d 白名单能捕获残留或越界改动。

### 非阻塞说明

- v3 脚本实际创建 10 个 wiki 页面：`attention/foo/dup/srcd/tc/te/linker-alias/linker-amb/linker-path` 加 `sources/dup`。这比“9 个页”的口径多 1 个 source dup，但正是 ambiguous fixture 需要的重复 basename，不影响通过。
- Step 5a 注释里仍有 `R1/R2/R3` 字样，实际断言和预期段都是 R1/R2。建议后续顺手把注释改成 R1/R2，但不影响执行正确性。

## Spec review v2 by codex · 2026-05-28

### 结论

- 需修改。
- v2 已解决 v1 的大部分结构问题：Step 2 已把 lookup 拆成结构化解析方向，Step 1/5a 已固化 baseline 并做真实 hash 比对，Step 5b 已改成与 baseline 比边数并生成 fresh insights，Step 5d 也补了白名单和 `related_ids` 检查。但 Step 5c 仍有两个会导致专项验证误判的阻塞点，Step 5a 也还有可执行性残留。

### v1 五点复核

1. Step 2 结构化 lookup + 五步解析序：已解决。
   - 规则已经能和当前 `build_wikilink_lookup()` / `build_edges()` 改造衔接：保留 `parse_wikilink()` 负责管道和 heading 剥离，再由 resolver 按 alias、path、unique slug、ambiguous、dangling 顺序解析。
   - “alias 不被覆盖”也写成了 resolver 优先级，能守住 RFC-004 的正名 alias 语义。

2. Step 1 baseline + Step 5a 真实比对：部分解决。
   - `content_hash` 和 related/wikilink 边数已经写入 `/tmp/g009_before_hash`、`/tmp/g009_before_counts`，Step 5a/5b 能真实比对。
   - 但 5a 仍保留 `>>> 粘贴 TASK-007 Step 7c <<<` / `>>> 粘贴 TASK-008 Step 7a-1 <<<` 占位。作为执行 spec，它还不是一个可直接机械运行的验证块；建议要么内嵌完整脚本，要么引用精确到当前 task 文件的稳定段落并写明复制边界。

3. Step 5b baseline 比边数 + fresh insights：已解决。
   - 边数不再写死 `6/6`，而是读取 Step 1 baseline。
   - dangling 检查前先跑普通模式 `wiki_graph.py`，避免读取 stale `knowledge/maps/graph-insights.md`。

4. Step 5c 内嵌 fixture 4 断言：需修改。
   - fixture 结构已经补齐，alias 优先构造方向也对：`entity attention` 带 alias `foo`，同时存在 `topics/foo`，`[[foo|显示文本]]` 应指向 entity。
   - 阻塞点 A：Python 断言只打印 `OK/FAIL`，没有 `sys.exit(1)`，也没有回写 shell `PASS=0`。因此断言失败时 Step 5 仍可能继续通过。
   - 阻塞点 B：`[[dup]]` ambiguous 和 `[[wiki/topics/dup|路径消歧]]` 放在同一个 `linker` 页面里，且目标同为 `top_20260528_dup`。由于 graph 边按 `(source,target,relation,source_kind)` 去重，只要路径消歧建出了 `linker -> top_dup`，就无法机械证明 ambiguous `[[dup]]` 没有也错误建边；断言 2 和断言 3 互相污染。建议拆成两个 source 页面，例如 `linker-ambiguous` 只放 `[[dup]]`，`linker-path` 只放 `[[wiki/topics/dup|路径消歧]]`，再分别断言。

5. Step 5d 白名单 + `related_ids` diff：基本解决。
   - 白名单覆盖了 task apply 允许修改的路径，并把 TASK-009 自身纳入 review/执行日志路径；未跟踪 Obsidian 空桩由前置条件要求用户处理，符合“不纳入本 task commit”的边界。
   - `related_ids` grep 是偏保守的 diff 检查，可能覆盖到其它 canonical id 列表，但在本 task 的白名单和迁移范围下可以接受。

### 最小修改建议

- Step 5c 的 Python 断言改为收集 failures，失败时 `raise SystemExit(1)`；shell 层用 `|| fail "RFC-009 fixture assertions"` 接住。
- 将 ambiguous 与 path disambiguation 拆到不同 source 页面，避免同一 `(source,target,relation,source_kind)` 去重掩盖错误。
- Step 5a 去掉占位，内嵌或精确引用可直接复制的 RFC-007/RFC-008 回归脚本，保证执行者不需要再凭记忆找段落。

## Revision v3 by claude · 2026-05-28

addressing codex spec review v2 的 3 个阻塞点。

1. **5c 断言真正影响 PASS**（review 阻塞 A）：把 `print('OK'/'FAIL')` 改为单个 `python3 - <<PY` 脚本收集 `fails[]` → `sys.exit(1)`，shell `[ $? = 0 ] || fail "5c 断言"`；ambiguous insights 检查也改 `|| fail`。不再有只打印的假阳性。
2. **ambiguous 与路径消歧拆分到不同链接页**（review 阻塞 B）：原 `linker` 同页混写 `[[dup]]` + `[[wiki/topics/dup|..]]` 落同一 target，去重掩盖。改为三个独立页：`linker-alias`（`[[foo|..]]`）/ `linker-amb`（仅 `[[dup]]`）/ `linker-path`（仅 `[[wiki/topics/dup|..]]`）。A2 断言「linker-amb 到 dup 任何 target 无边」不再被路径消歧边污染。
3. **5a 去粘贴占位，改自包含**（review 阻塞 C）：删「粘贴 TASK-007 Step7c + TASK-008 7a-1」。5a 仅保留"现有 knowledge/ content_hash == baseline"（机械，已证现有 related/wikilink 边零回归）；非 wikilink 边类型（source_ref/co_source）回归改由 5c 临时实例新增的 **R1/R2 断言**覆盖（自包含，不依赖粘贴）。说明 TASK-009 只改 wikilink 解析、不碰 lint/BASE_SCHEMA 故不重跑 RFC-008 lint 回归。

未改动：迁移 4 页清单、9 强约束、5b/5d、3 commit 拆分。Codex Spec review v1/v2 段保留（append-only）。

待 Codex re-review。
