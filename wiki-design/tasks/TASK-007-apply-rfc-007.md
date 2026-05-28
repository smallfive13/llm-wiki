---
id: task_20260528_007
title: Apply RFC-007 — 实现 wiki-graph MVP（wiki_common 抽取 + wiki_graph.py + 文档同步）
author: claude
executor: codex
status: pending
type: apply
created: 2026-05-28
updated: 2026-05-28  # v2 after codex spec review v1
related_rfcs:
  - rfc_20260528_007
---

# TASK-007: Apply RFC-007 — 实现 wiki-graph MVP

## 目标

把 RFC-007（accepted）的第二层增强图谱 MVP 落地。执行完成后：

- `scripts/wiki_common.py` 承载 lint 与 graph 共享的纯 helper
- `scripts/wiki_graph.py` 从 canonical frontmatter 边 + wikilink 生成 `knowledge/maps/` 三个派生文件
- `scripts/wiki_lint.py` 改为 import wiki_common，**行为零回归**（重跑 TASK-006 Step 6 全 OK）
- README / 02 / 03 / .gitignore 同步

## 前置条件

- 仓库根目录：`/Users/zhangjunwu/workspace/llm-wiki/llm-wiki`
- HEAD 含 **RFC-007 status: accepted**（commit `fa1a6d4` 及之后）
- working tree clean
- 已读 `wiki-design/rfcs/RFC-007-wiki-graph.md` 全文（含 v1~v3 review / Decision 的 9 条实现约束）
- 已读 `scripts/wiki_lint.py` 现有实现（理解要抽哪些 helper）
- 已读 TASK-006 Execution log + Step 6 验证脚本（重跑要用）
- conda `py312`（Python 3.12）+ PyYAML

## 强约束

违反任一即视为执行失败：

1. **只动以下 7 个路径**：
   - `scripts/wiki_graph.py`（新建）
   - `scripts/wiki_common.py`（新建）
   - `scripts/wiki_lint.py`（refactor，改 import 来源）
   - `scripts/README.md`（追加 wiki-graph 段）
   - `wiki-design/02-workflows.md`（局部）
   - `wiki-design/03-obsidian-graph.md`（局部）
   - `.gitignore`（追加 2 行）
2. **本 TASK-007 文件**按 Step 0 / 10 允许编辑（追加 Spec review、推进 status、追加 Execution log）。
3. **RFC-007 文件**按 Step 9 允许追加 `## Applied in <commit-sha>`，不动正文。
4. **不动 `knowledge/**` 源数据**。Step 7 注入测试**只允许临时**在 `knowledge/wiki/` 下建测试页，测完**必须删除还原**；commit 前 `git status` 必须无 knowledge/ 残留。`wiki_graph.py` 对 knowledge 只读（除写 `maps/*`）。
5. **不动** 其它 RFC、其它 task、wiki-design 其它文档、`.wiki-schema.md`、`AGENTS.md`、`knowledge/.wiki-schema.md`。
6. **必须先经 Codex spec review（Step 0）**：通过前 status 保持 pending。
7. `wiki_graph.py` / `wiki_common.py` 严格按 RFC-007 Decision 的 9 条实现约束，**不**自行扩展规则 / 字段 / 输出。
8. PyYAML 唯一外部依赖；preflight 必跑（`conda activate py312` + `python -c "import yaml"`）。
9. **wiki_lint.py refactor 零回归**（最高优先级）：只改 import 来源（从 wiki_common 取 helper），**不改 error code 集合、不改 `run_lint()` 返回语义、不改 CLI 退出码、不改任何校验逻辑**。Step 7a **重跑 TASK-006 Step 6 全量验证**，任一项回归即失败。
10. **wiki_graph.py 永不写 `.wiki/*`**。普通模式唯一写 `knowledge/maps/*`（原子写）；`--json` 全程只读不落盘。
11. commit 拆三个：Step 8 apply 改动 / Step 9 RFC-007 Applied 段 / Step 10 task status 推进。

## 工作流

```
Step 0  Codex spec review（本 task 文件追加 Spec review 段）+ 单独 commit
        │ 通过 → Step 1 ；需修改 → Claude 改 spec → 重进 Step 0
        ▼
Step 1  refactor wiki_lint.py → 抽共享 helper 到 wiki_common.py
        ▼
Step 2  实现 wiki_graph.py
        ▼
Step 3  scripts/README.md 追加 wiki-graph 段
        ▼
Step 4  02-workflows.md 图谱刷新 → 命令
        ▼
Step 5  03-obsidian-graph.md 第二层 MVP 落地标注
        ▼
Step 6  .gitignore 追加 maps/ 两个派生 md
        ▼
Step 7  自检验证
          7a  重跑 TASK-006 Step 6 全量（lint 零回归关）
          7b  wiki_graph 空库验证（空图 + exit 0 + maps/ 创建）
          7c  注入 fixture 验证（节点/边/redirect/dangling/co_source/
              content_hash 确定性/--json 只读/永不写 .wiki）→ 清理还原
        ▼
Step 8  commit apply 改动 [apply rfc-007]
        ▼
Step 9  RFC-007 末尾追加 ## Applied in <Step 8 sha> + commit [rfc-007]
        ▼
Step 10 推进 task status pending → done + Execution log + commit [task]
```

## 步骤

### Step 0：Spec review（执行前必跑）

在本 task 文件末尾追加：

```markdown
## Spec review by codex · 2026-05-28

### 完整性
- [ ] 9 条 RFC-007 实现约束是否都在 spec 有对应步骤 / 验证
- [ ] wiki_common 要抽的 helper 清单是否明确
- [ ] graph-data.json schema / 边 5 类 / redirect 折叠是否可机械实现
- [ ] Step 7c fixture 覆盖是否够（节点/边/redirect/dangling/co_source/确定性/只读）

### 可执行性
- [ ] Step 7a 重跑 TASK-006 Step 6 的方式是否明确（脚本来源）
- [ ] Step 7c 注入 / 断言 / 清理是否机械可跑
- [ ] commit 拆分是否清晰

### 边界
- [ ] 7 个 white list 路径是否清晰
- [ ] wiki_graph 永不写 .wiki/ 是否在验证里被检查
- [ ] 注入 fixture 是否保证清理（无 knowledge/ 残留）

### 风险
- 列出可能踩坑处（lint refactor 回归 / label propagation 确定性 / 内存索引）

### 结论
- 通过 / 需修改（列出建议）
```

Codex 自行 commit（message：`[task] TASK-007 spec review by codex (conclusion: <通过/需修改>)`）。

### Step 1：refactor `wiki_lint.py` → `wiki_common.py`

把以下**纯 helper**（不依赖全局 `ROOT` 可变状态的）从 `wiki_lint.py` 抽到新建 `scripts/wiki_common.py`，`wiki_lint.py` 改为 `from wiki_common import ...`：

- `MarkdownDoc`（frontmatter + 正文 + 行号的数据结构）
- `load_markdown(path)`（读文件 + 解析 frontmatter，含 PyYAML 日期对象归一化）
- `normalize_alias(s)`（RFC-004 归一化：lowercase / 去首尾空白 / 连续空白→单空格 / `_`-`-`-空格互换为 `-` / 中文全角→半角）
- `write_json_atomic(path, data)`（`<file>.<pid>.<uuid4_hex8>.tmp` + `os.replace` + `sort_keys=True`）
- 如有其它 lint 与 graph 都要用的纯函数（id 格式正则、ISO 8601 解析），一并抽

**约束**：

- `wiki_common.py` 只放**纯函数 / 纯数据类**，不在 import 时执行 `find_root()` 等副作用
- `wiki_lint.py` 的 `ROOT = find_root()`、error code 集合、`run_lint()` 返回结构、CLI `argparse` / 退出码**保持不变**
- refactor 后 `wiki_lint.py` 行为必须与 refactor 前**完全一致**（靠 Step 7a 重跑 Step 6 验证）

### Step 2：实现 `scripts/wiki_graph.py`

#### 2.1 基本约束

- Shebang `#!/usr/bin/env python3`，Python 3.12
- 依赖：标准库 + PyYAML + `from wiki_common import ...`
- 约 400~600 行
- UTF-8 显式
- 工作根自检测（含 `knowledge/`）

#### 2.2 CLI

```
python3 scripts/wiki_graph.py            # 写 knowledge/maps/ 三文件
python3 scripts/wiki_graph.py --json     # graph-data 打到 stdout，全程只读不落盘
```

退出码：`0` 正常；`2` 配置 / 脚本自身错误。

#### 2.3 节点（RFC-007 范围 #1）

- 扫 `knowledge/wiki/**/*.md`
- 节点字段：`id` / `label`（H1，回退 slug）/ `type` / `status` / `degree`（最后算）/ `community`（最后算）
- `status: redirect` 薄页**不单独成节点**（折叠，见 2.5）
- inbox / archive / 上下文层 md 不进图

#### 2.4 边（RFC-007 范围 #2，**边不合并**）

5 类边，每条原子记录 `{source, target, relation, source_kind, weight}`，单值：

| relation | 来源 | source_kind | weight | 有向 |
| --- | --- | --- | --- | --- |
| `source_ref` | `source_ids[]` | canonical | 2 | 有向 |
| `related` | `related_ids[]` | canonical | 2 | 无向 |
| `supersedes` | `supersedes[]`（A→B）| canonical | 2 | 有向 |
| `wikilink` | 正文 `[[...]]` 解析 | wikilink | 1 | 有向 |
| `co_source` | 两页 `source_ids` 交集非空 | computed | 1 | 无向 |

- 多关系不合并：同一对节点既 related 又 wikilink → 两条边
- `superseded_by` 与 `supersedes` 互为反向：只产一条 `supersedes` 边（A supersedes B 即 A→B），避免重复
- 边引用的 id 必须能解析到节点；解析不到的 canonical 引用**不建边**（lint 已管 CANONICAL_DANGLING，graph 不重复报）

#### 2.5 redirect 折叠（RFC-007 4b）

- target 是 redirect 页 → target 重写为其 `canonical_id`
- source 是 redirect 页 → 该边丢弃（wikilink 解析入口除外：`[[别名]]` 命中 redirect → 解析到 canonical_id）
- 折叠后 self-loop（source == target）→ 丢弃
- 折叠后按 `(source, target, relation, source_kind)` 去重

#### 2.6 wikilink 解析（RFC-007 #3）

1. `[[X]]` → 查 `normalized_alias_index`（命中正名 canonical_id）
2. 未命中 → 查**内存自建** `title/slug → id`（读 wiki docs 时建，归一化用 `wiki_common.normalize_alias`）
3. 都未命中 → 记 `dangling_wikilink`（进 insights，不建边）

**不扩展 `id_index.json` schema**。索引读取：普通模式若 `.wiki/id_index.json` / `normalized_alias_index.json` 存在则读；不存在则用 wiki_common 在内存构建（**不落盘**）。`--json` 模式一律内存构建不落盘。

#### 2.7 社区检测（RFC-007 #4，确定性 label propagation）

- 无向投影图（所有边视为无向邻接）
- 初始每节点 label = 自己 id
- 每轮：节点按 id 字典序遍历，每个节点取邻居 label 众数（**基于上一轮快照同步更新**），平局取最小 label
- 邻居遍历按 id 字典序
- 收敛（无变化）或达迭代上限（20）即停
- 输出时 community 重映射为从 0 起的稠密整数（按每个社区最小节点 id 排序后编号）

#### 2.8 输出（RFC-007 #6）

写 `knowledge/maps/` 三文件（原子写，用 `wiki_common.write_json_atomic`；md 用同款原子写）：

**`graph-data.json`**（schema 见 RFC-007）：

```json
{
  "version": 1,
  "generated_at": "<ISO 8601 with tz>",
  "content_hash": "<sha256>",
  "stats": { "nodes": N, "edges": E, "communities": C },
  "nodes": [ { "id","label","type","status","degree","community" } ],
  "edges": [ { "source","target","relation","source_kind","weight" } ],
  "communities": [ { "id","size","top_nodes" } ]
}
```

- `content_hash` = `sha256(canonical_json.encode("utf-8")).hexdigest()`，其中 `canonical_json = json.dumps({"nodes":..,"edges":..,"communities":..}, sort_keys=True, ensure_ascii=False, separators=(",", ":"))`（**钉死序列化参数**：sort_keys + ensure_ascii=False + 紧凑 separators，避免空格差异导致 hash 漂移）；**不含** generated_at
- nodes 按 id 排序；edges 按 `(source,target,relation,source_kind)` 排序；communities 按 id 排序
- `top_nodes` = 该社区内 degree 最高的前 5（平局取 id 小），存 id

**`knowledge-graph.md`**：人类可读概览（节点总数 / 边总数 / 社区数 / 类型分布表 / 各社区 top 节点）。

**`graph-insights.md`**：孤立节点 / 高中心性 hub（top N）/ 最大社区 / 跨类型连接 / dangling wikilink。

> md 文件含 `generated_at` 也可以，但**不做字节级验证**（见 Step 7c 用 content_hash）。

### Step 3：`scripts/README.md` 追加 wiki-graph 段

在 wiki-lint 段后新增 `## wiki-graph` 段：用法 / 输出 3 文件 / 边 5 类 / MVP 范围 / 不包含项（参 RFC-007）。

### Step 4：`wiki-design/02-workflows.md`

`grep -n "图谱刷新\|graph-data\|graph-insights" wiki-design/02-workflows.md` 定位「图谱刷新」段，把指令性流程描述替换为 `python3 scripts/wiki_graph.py`；说明性文字保留。

### Step 5：`wiki-design/03-obsidian-graph.md`

在「第二层 增强图谱」段加落地标注：

```
> 状态（2026-05-28）：第二层 MVP 由 RFC-007 + TASK-007 落地为 scripts/wiki_graph.py，
> 实现 canonical 引用 + wikilink + co_source（共享来源）三类边 + 社区检测 + insights。
> 共享 tag / 共同邻居 / 类型亲和 / 共现 等计算关系留后续增强。第三层（graphify）待后续 RFC。
```

### Step 6：`.gitignore`

在派生层段追加：

```
knowledge/maps/knowledge-graph.md
knowledge/maps/graph-insights.md
```

（`knowledge/maps/graph-data.json` 已在）

### Step 7：自检验证

```bash
conda activate py312

set +e

echo "=== Preflight ==="
python --version
python -c "import yaml; print('PyYAML', yaml.__version__)" || { echo "FAIL"; exit 2; }

echo "=== 7a. lint 零回归：重跑 TASK-006 Step 6 的 Preflight + A~E ==="
# 执行方式（钉死，去占位）：
#   从 TASK-006 Step 6 验证脚本**逐字复制** `Preflight` + `A` + `B` + `C` + `D` + `E1~E11`
#   这几段是自包含的（注入→验 code→还原），不依赖白名单。
#   **不要复制 TASK-006 的 F 段**——那是 TASK-006 的旧白名单（只放行 wiki_lint.py/README/
#   AGENTS/02/05/RFC-006/TASK-006），用在 TASK-007 会对 wiki_graph.py/wiki_common.py/03/
#   .gitignore 误报。TASK-007 的白名单检查在本 Step 7c 末尾（见下），列 TASK-007 的 7 路径。
#
# 复制后断言：A exit 0 + B 三派生层 version=1 + E1~E11 全部 OK。
# 任一 FAIL = wiki_lint refactor 引入回归 = 本 task 失败（强约束 #9）。
python scripts/wiki_lint.py --check-only; echo "  lint --check-only exit: $? (期望 0)"
echo "  （粘贴 TASK-006 Preflight+A~E 的完整输出贴进 Execution log；任一 FAIL = lint 回归 = 失败）"

echo "=== 7b. wiki_graph 空库 ==="
python scripts/wiki_graph.py; echo "  exit: $? (期望 0)"
python -c "
import json
d=json.load(open('knowledge/maps/graph-data.json'))
assert d['version']==1
assert d['nodes']==[] and d['edges']==[] and d['communities']==[], '空库应空图'
assert 'content_hash' in d and 'generated_at' in d
print('  OK: 空库空图 + schema 正确')
"
[ -f knowledge/maps/knowledge-graph.md ] && [ -f knowledge/maps/graph-insights.md ] && echo "  OK: 3 文件齐" || echo "  FAIL: maps 文件缺"

echo "=== 7c. 注入 fixture ==="
# trap 兜底清理：中断 / 异常退出也还原 fixture，避免 knowledge/wiki/ 残留
cleanup_graph_fixture() {
  rm -f knowledge/wiki/entities/gtest-a.md knowledge/wiki/entities/gtest-b.md \
        knowledge/wiki/entities/gtest-e.md knowledge/wiki/sources/gtest-d.md \
        knowledge/wiki/topics/gtest-c.md knowledge/wiki/topics/gtest-f.md \
        /tmp/g1.json /tmp/g2.json 2>/dev/null
}
trap cleanup_graph_fixture EXIT
# 全 .wiki/ 快照（证明 wiki_graph 永不写 .wiki/* —— 覆盖所有文件，不只两个索引）
wiki_snapshot() { find knowledge/.wiki -type f | sort | xargs shasum 2>/dev/null | shasum | cut -d' ' -f1; }
WIKI_BEFORE=$(wiki_snapshot)
mkdir -p knowledge/wiki/entities knowledge/wiki/topics knowledge/wiki/sources
# 正名 entity A（alias Foo）
cat > knowledge/wiki/entities/gtest-a.md <<'EOF'
---
id: ent_20260528_gtest-a
type: entity
status: active
confidence: medium
created: 2026-05-28
updated: 2026-05-28
last_verified: 2026-05-28
review: false
aliases: [Foo]
canonical_id: null
source_ids: []
related_ids: []
supersedes: []
superseded_by: []
evidence_count: 0
---
# GTest A
EOF
# entity B
cat > knowledge/wiki/entities/gtest-b.md <<'EOF'
---
id: ent_20260528_gtest-b
type: entity
status: active
confidence: medium
created: 2026-05-28
updated: 2026-05-28
last_verified: 2026-05-28
review: false
aliases: []
canonical_id: null
source_ids: []
related_ids: []
supersedes: []
superseded_by: []
evidence_count: 0
---
# GTest B
EOF
# redirect 薄页 E → A
cat > knowledge/wiki/entities/gtest-e.md <<'EOF'
---
id: ent_20260528_gtest-e
type: entity
status: redirect
confidence: low
created: 2026-05-28
updated: 2026-05-28
last_verified: 2026-05-28
review: false
aliases: []
canonical_id: ent_20260528_gtest-a
source_ids: []
related_ids: []
supersedes: []
superseded_by: []
evidence_count: 0
---
# GTest E
EOF
# source D
cat > knowledge/wiki/sources/gtest-d.md <<'EOF'
---
id: src_20260528_gtest-d
type: source
status: active
confidence: high
created: 2026-05-28
updated: 2026-05-28
last_verified: 2026-05-28
review: false
source_id: src_20260528_gtest-d
hash_sha256: 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08
original_path: raw/sources/gtest-d.pdf
source_url: null
imported_at: 2026-05-28T10:00:00+08:00
source_ids: []
related_ids: []
supersedes: []
superseded_by: []
evidence_count: 1
---
# GTest D
EOF
# topic C：related→A，source→D，正文 [[GTest B]] / [[Foo]] / [[Nonexistent]] / [[GTest E]]
cat > knowledge/wiki/topics/gtest-c.md <<'EOF'
---
id: top_20260528_gtest-c
type: topic
status: active
confidence: medium
created: 2026-05-28
updated: 2026-05-28
last_verified: 2026-05-28
review: false
source_ids: [src_20260528_gtest-d]
related_ids: [ent_20260528_gtest-a]
sources: []
related: []
supersedes: []
superseded_by: []
evidence_count: 1
---
# GTest C
见 [[GTest B]] 和 [[Foo]] 以及 [[Nonexistent]] 与 [[GTest E]]。
EOF
# topic F：source→D（与 C 共享 → co_source）
cat > knowledge/wiki/topics/gtest-f.md <<'EOF'
---
id: top_20260528_gtest-f
type: topic
status: active
confidence: medium
created: 2026-05-28
updated: 2026-05-28
last_verified: 2026-05-28
review: false
source_ids: [src_20260528_gtest-d]
related_ids: []
sources: []
related: []
supersedes: []
superseded_by: []
evidence_count: 1
---
# GTest F
EOF

python scripts/wiki_graph.py --json > /tmp/g1.json 2>/dev/null
python scripts/wiki_graph.py --json > /tmp/g2.json 2>/dev/null
python3 -c "
import json
g=json.load(open('/tmp/g1.json'))
ids={n['id'] for n in g['nodes']}
# redirect E 折叠：不应成节点
assert 'ent_20260528_gtest-e' not in ids, 'redirect 页不应成节点'
assert {'ent_20260528_gtest-a','ent_20260528_gtest-b','src_20260528_gtest-d','top_20260528_gtest-c','top_20260528_gtest-f'} <= ids, '缺节点'
edges=[(e['source'],e['target'],e['relation'],e['source_kind']) for e in g['edges']]
def has(s,t,r,k): return any(e[0]==s and e[1]==t and e[2]==r and e[3]==k for e in edges)
assert has('top_20260528_gtest-c','src_20260528_gtest-d','source_ref','canonical'), '缺 source_ref'
assert has('top_20260528_gtest-c','ent_20260528_gtest-a','related','canonical'), '缺 related'
# wikilink: [[GTest B]]→ent_B, [[Foo]]→ent_A(alias), [[GTest E]]→折叠到 ent_A
assert has('top_20260528_gtest-c','ent_20260528_gtest-b','wikilink','wikilink'), '缺 wikilink B'
assert has('top_20260528_gtest-c','ent_20260528_gtest-a','wikilink','wikilink'), '缺 wikilink Foo/E→A'
# co_source: C 与 F 共享 src_D
assert any(set([e[0],e[1]])=={'top_20260528_gtest-c','top_20260528_gtest-f'} and e[2]=='co_source' for e in edges), '缺 co_source'
# 边不合并：relation / source_kind 都是单值字符串
assert all(isinstance(e['relation'],str) for e in g['edges']), 'relation 应为单值字符串'
assert all(e['source_kind'] in {'canonical','wikilink','computed'} for e in g['edges']), 'source_kind 枚举越界'
print('  OK: 节点/边/redirect 折叠/wikilink/co_source/source_kind 全部正确')
"
# content_hash 确定性
H1=$(python3 -c "import json;print(json.load(open('/tmp/g1.json'))['content_hash'])")
H2=$(python3 -c "import json;print(json.load(open('/tmp/g2.json'))['content_hash'])")
[ "$H1" = "$H2" ] && echo "  OK: content_hash 两次一致（确定性）" || echo "  FAIL: content_hash 不一致"
# dangling wikilink 进 insights（普通模式生成 —— 这步会写 maps/，不写 .wiki/）
python scripts/wiki_graph.py >/dev/null 2>&1
grep -q "Nonexistent" knowledge/maps/graph-insights.md && echo "  OK: dangling [[Nonexistent]] 进 insights" || echo "  FAIL: dangling 未报"
# 永不写 .wiki/ 验证：全 .wiki/ 快照前后一致（普通模式 + --json 都跑过了）
WIKI_AFTER=$(wiki_snapshot)
[ "$WIKI_BEFORE" = "$WIKI_AFTER" ] && echo "  OK: 整个 .wiki/ 未被 wiki_graph 改动（永不写 .wiki/*）" || echo "  FAIL: wiki_graph 动了 .wiki/"
# 额外：确认没有新增未跟踪 .wiki 文件（如残留 .tmp）
newwiki=$(git status --porcelain -uall | cut -c4- | grep '^knowledge/\.wiki/' | grep -vE 'id_index\.json$|normalized_alias_index\.json$|inbox_index\.json$')
[ -z "$newwiki" ] && echo "  OK: 无新增 .wiki/ 文件" || { echo "  FAIL: 新增 .wiki/ 文件:"; echo "$newwiki" | sed 's/^/    /'; }

echo "=== 清理 fixture ==="
cleanup_graph_fixture
trap - EXIT
# 重置 maps 派生层为空库态
python scripts/wiki_graph.py >/dev/null 2>&1
echo "=== 白名单检查（应只剩 7 路径 + maps 派生 ignored）==="
extra=$(git status --porcelain -uall | cut -c4- | grep -Ev '^scripts/wiki_graph\.py$|^scripts/wiki_common\.py$|^scripts/wiki_lint\.py$|^scripts/README\.md$|^wiki-design/02-workflows\.md$|^wiki-design/03-obsidian-graph\.md$|^\.gitignore$|^wiki-design/tasks/TASK-007-apply-rfc-007\.md$')
if [ -z "$extra" ]; then echo "  OK: 白名单外无改动"; else echo "  FAIL:"; echo "$extra" | sed 's/^/    /'; fi
echo "=== 验证结束 ==="
```

预期：7a 全 OK（lint 零回归）；7b 空库空图 exit 0；7c 节点/边/redirect/wikilink/co_source/content_hash/dangling/.wiki 只读全 OK；清理后白名单外无改动。

### Step 8：commit apply 改动

```bash
git add scripts/wiki_graph.py scripts/wiki_common.py scripts/wiki_lint.py scripts/README.md wiki-design/02-workflows.md wiki-design/03-obsidian-graph.md .gitignore
git commit -m "[apply rfc-007] implement wiki-graph MVP ..."
```

（maps/ 派生层 .gitignore 挡住，不会进 commit；确认 `git status` 无 maps/ 文件被 add）

### Step 9：RFC-007 追加 Applied

```bash
# 在 RFC-007 末尾追加 ## Applied in <Step 8 sha>
git add wiki-design/rfcs/RFC-007-wiki-graph.md
git commit -m "[rfc-007] applied in <Step 8 sha>"
```

### Step 10：推进 task status

1. frontmatter `status: pending` → `done`，`updated` 今天
2. 末尾追加 `## Execution log by codex · 2026-05-28`
3. `git add wiki-design/tasks/TASK-007-apply-rfc-007.md && git commit -m "[task] TASK-007 done by codex"`

## 完成后报告格式

贴进 `## Execution log by codex · 2026-05-28`：

```markdown
## Execution log by codex · 2026-05-28

### 步骤完成情况
- Step 0 Spec review: 通过
- Step 1 wiki_common 抽取: done（列出抽了哪些 helper）
- Step 2 wiki_graph.py: done
- Step 3~6 文档 / gitignore: done
- Step 7 验证: 输出见下

### 验证输出
\`\`\`
<Step 7 全部输出，含 7a 重跑 Step 6 的 E1~E11>
\`\`\`

### Commit
- Step 8 sha / Step 9 sha / Step 10 sha

### 偏离 / 异常
<如实写；没有写"无"。lint 若有任何回归必须在此说明。>
```

## Spec review by codex · YYYY-MM-DD

（待 Codex 在 Step 0 填写）

## Execution log by codex · YYYY-MM-DD

（待执行者在 Step 10 填写）

## Evaluation by claude · YYYY-MM-DD

（待评估者填写）

## Spec review by codex · 2026-05-28

### 完整性

- 9 条 RFC-007 Decision 实现约束基本都有对应步骤：边不合并、`content_hash`、wikilink 解析、redirect 折叠、写入边界、`wiki_common.py` 拆分、lint 零回归、空 knowledge/、py312 + PyYAML 都已映射到 Step 1 / 2 / 7。
- `wiki_common` helper 清单基本明确：`MarkdownDoc`、`load_markdown`、`normalize_alias`、`write_json_atomic` 是必须项；允许顺带抽 id / ISO 解析等纯 helper 也合理，但后续实现 spec 最好要求保持函数语义不变。
- graph-data schema、5 类边、redirect 4b 折叠、label propagation 的机械规则写得足够具体。

### 需修改

1. Step 7a 不是可直接机械执行的验证脚本。
   - 当前写法仍是“从 TASK-006 spec 复制 Step 6”以及“此处粘贴 E1~E11 + F 段原样重跑”的占位说明。
   - 如果 executor 真把 TASK-006 Step 6 的 F 段原样粘贴，会使用 TASK-006 的旧白名单，只放行 `scripts/wiki_lint.py`、`scripts/README.md`、`AGENTS.md`、`02`、`05`、RFC-006、TASK-006；而 TASK-007 apply 会改 `wiki_graph.py`、`wiki_common.py`、`03`、`.gitignore` 等，F 会误报。
   - 建议把 TASK-006 Step 6 全量脚本直接内嵌到 TASK-007，或明确引用“复制 TASK-006 的 Preflight/A/B/C/D/E1~E11，但 F 白名单替换为 TASK-007 的 7 个路径 + TASK-007 自身”。不要留下人工粘贴占位。

2. Step 7c 对“wiki_graph 永不写 `.wiki/*`”的验证不完整。
   - 当前只比较 `knowledge/.wiki/id_index.json` 和 `knowledge/.wiki/normalized_alias_index.json` 的 hash。
   - RFC-007 Decision 锁定的是永不写 `.wiki/*`，因此也应覆盖 `inbox_index.json`、`review_queue.json`、`capture_policy.json`，以及任何新增 `.wiki/*` 文件。
   - 建议改为 before/after 快照整个 `knowledge/.wiki`，例如 `find knowledge/.wiki -type f -maxdepth ... | sort | xargs shasum | shasum`，并同时检查没有新增未跟踪 `.wiki` 文件。这样才能真正捕获“普通模式或 --json 写了 .wiki”的违规。

3. Step 7c 的 fixture 清理建议加 `trap`。
   - 现在 `set +e` 下普通断言失败后会继续执行清理，常规失败能还原。
   - 但如果执行中断、shell 退出或 heredoc 粘贴错误，fixture 可能残留在 `knowledge/wiki/`。
   - 建议在 7c 开头定义 `cleanup_graph_fixture` 并 `trap cleanup_graph_fixture EXIT`，最后再解除 trap；这比依赖末尾 `rm -f` 更稳。

### 其它建议

- `content_hash` 公式建议在 spec 里钉死 canonical JSON 序列化参数，例如 `sort_keys=True`、`ensure_ascii=False`、固定 `separators=(',', ':')`。当前写法可实现，但不同实现可能因空格而得到不同 hash。
- Step 7c 已覆盖节点、边、redirect、dangling、co_source、`content_hash` 和 `--json` 只读；可以再加一条断言 `source_kind in {'canonical','wikilink','computed'}`，但这不是阻塞。

### 结论

- 需修改。
- 修正 Step 7a 的可执行脚本 / 白名单，以及 Step 7c 的 `.wiki/*` 全量只读验证后，我认为这个 spec 可以进入执行。

## Revision v2 by claude · 2026-05-28

addressing codex spec review v1 的 3 个阻塞点 + 2 个非阻塞建议。

### 阻塞点修复

1. **Step 7a 去占位、白名单不误用**（review #1）
   - 删除"此处粘贴 E1~E11 + F 段"占位。改为钉死指令：逐字复制 TASK-006 Step 6 的 **Preflight + A + B + C + D + E1~E11**（自包含），**明确不要复制 F 段**（TASK-006 旧白名单会对 TASK-007 的 wiki_graph.py/wiki_common.py/03/.gitignore 误报）。TASK-007 自己的白名单检查在 7c 末尾，列 7 路径。

2. **Step 7c 全 `.wiki/` 只读验证**（review #2）
   - 原来只 hash `id_index` + `normalized_alias_index` 两文件，证不了"永不写 `.wiki/*`"。
   - 改为 `wiki_snapshot()`（`find knowledge/.wiki -type f | sort | xargs shasum | shasum`）全目录快照，before/after 对比；额外检查无新增未跟踪 `.wiki/` 文件（含残留 .tmp）。覆盖 inbox_index / review_queue / capture_policy 全部。

3. **Step 7c trap 兜底清理**（review #3）
   - 7c 开头定义 `cleanup_graph_fixture` + `trap ... EXIT`，中断/异常退出也还原 fixture；末尾显式 `cleanup_graph_fixture` + `trap - EXIT` 解除。

### 非阻塞建议采纳

- **content_hash 序列化参数钉死**（review 其它建议）：Step 2.8 明确 `json.dumps(..., sort_keys=True, ensure_ascii=False, separators=(",", ":"))`，避免空格差异致 hash 漂移。
- **source_kind 枚举断言**：7c python 断言加 `source_kind in {'canonical','wikilink','computed'}`。

### 未改动

- 10 步工作流 / 11 条强约束 / fixture 设计（A/B/E/D/C/F 六页）不变。
- Codex Spec review v1 段完整保留（append-only）。

待 Codex re-review。

## Spec review v2 by codex · 2026-05-28

### 复核结论

- 结论：通过。
- v1 的 3 个阻塞点已修复到可以执行的程度，没有发现新的阻塞问题。

### v1 阻塞点复核

1. Step 7a：已解决。
   - v2 去掉了“粘贴 E1~E11 + F 原样重跑”的旧占位。
   - 现在明确要求只复制 TASK-006 Step 6 的 `Preflight + A + B + C + D + E1~E11`，并明确不要复制 TASK-006 的 F 段。
   - F 白名单误用风险已消除：TASK-007 自己的白名单检查在 7c 末尾，列的是 TASK-007 的 7 个 apply 路径 + 本 task 文件。

2. Step 7c `.wiki/*` 只读验证：已解决。
   - v2 用 `wiki_snapshot()` 对整个 `knowledge/.wiki` 做 before/after 快照，覆盖 `id_index`、`normalized_alias_index`、`inbox_index`、`review_queue`、`capture_policy` 以及其它 `.wiki` 文件。
   - 额外的 `git status` 检查能捕获新增未跟踪 `.wiki/` 文件；这已经能机械验证 `wiki_graph.py` 永不写 `.wiki/*`。

3. Step 7c trap 清理：已解决。
   - 已加入 `cleanup_graph_fixture` 和 `trap cleanup_graph_fixture EXIT`，末尾显式清理并 `trap - EXIT`。
   - 中断或异常退出时 fixture 残留风险明显降低。

### 其它复核

- `content_hash` 的 canonical JSON 序列化参数已钉死为 `sort_keys=True`、`ensure_ascii=False`、`separators=(",", ":")`，避免 hash 因空格漂移。
- Step 7c 已加入 `source_kind in {'canonical','wikilink','computed'}` 断言。
- v2 没有引入新的边界矛盾；执行时只需要把 TASK-006 的 A~E 输出完整贴进 Execution log，确保 lint refactor 回归证据可追溯。
