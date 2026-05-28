---
id: task_20260528_008
title: Apply RFC-008 — 实现 schema profile 机制（BASE_SCHEMA 抽取 + profile overlay + --root）
author: claude
executor: codex
status: pending
type: apply
created: 2026-05-28
updated: 2026-05-28  # v2 after codex spec review v1
related_rfcs:
  - rfc_20260528_008
---

# TASK-008: Apply RFC-008 — 实现 schema profile 机制

## 目标

把 RFC-008（accepted）的 base + profile overlay 机制落地。执行完成后：

- `wiki_common.BASE_SCHEMA` 收拢 RFC-002~007 冻结 schema（不增不删）
- `wiki_lint.py` / `wiki_graph.py` 读 effective schema = `merge(BASE_SCHEMA, profile)`，加 `--root`（实例根基准）
- profile 自校验（10 个 `PROFILE_*`）
- **无 profile 时行为等价**（结构等价，非字节级）——这是零回归硬关
- README / .wiki-schema.md / 01 / 05 同步

## 前置条件

- 仓库根：`/Users/zhangjunwu/workspace/llm-wiki/llm-wiki`
- HEAD 含 **RFC-008 status: accepted**（commit `1c5740a` 及之后）
- working tree clean
- 已读 RFC-008 全文（含 Decision 的 10 条实现约束）
- 已读 `scripts/wiki_lint.py` / `scripts/wiki_graph.py` / `scripts/wiki_common.py` 现有实现
- 已读 TASK-006 Step 6（E1~E11）+ TASK-007 Step 7c（fixture）——重跑要用
- conda `py312` + PyYAML

## 强约束

违反任一即视为执行失败：

1. **只动以下路径**：
   - `scripts/wiki_common.py`（加 BASE_SCHEMA + profile helper）
   - `scripts/wiki_lint.py`（读 effective schema + --root + PROFILE_* code）
   - `scripts/wiki_graph.py`（读 effective schema + --root + 未知 type 跳过）
   - `scripts/README.md`
   - `knowledge/.wiki-schema.md`
   - `wiki-design/01-architecture.md`
   - `wiki-design/05-contracts-and-next-steps.md`
2. **本 TASK-008 文件**按 Step 0 / 9 编辑。
3. **RFC-008 文件**按 Step 8 追加 `## Applied in <sha>`。
4. **不动 `knowledge/**` 源数据**。验证用的临时实例 / profile / fixture 必须建在 `knowledge/` **以外**（如 `knowledge-gtest/`）或测完即删；commit 前 `git status` 无 knowledge/ 残留、无临时实例残留。
5. **不动** 其它 RFC/task、wiki-design 其它文档、AGENTS.md、.gitignore（本 task 不需要改 .gitignore）。
6. **必须先经 Codex spec review（Step 0）**。
7. 严格按 RFC-008 Decision 10 条实现约束，**不**自行扩展。
8. PyYAML 唯一外部依赖；preflight 必跑。
9. **BASE_SCHEMA = RFC-002~007 冻结现状，不增不删**；core 不变量（ID 格式 / canonical / source 单主键 / RFC-004 别名 / inbox / 派生层 / core 字段 enum / 7 类 JSON 契约 / PII）profile 碰不到。
10. **零回归硬关**（最高优先级）：无 profile 时 lint/graph 行为等价（结构等价口径，见 Step 7）。Step 7a/7b 任一回归即失败。
11. **`wiki_graph` 永不写 `.wiki/*`**（沿用 RFC-007）；`wiki_lint` 派生层只写 `.wiki/`；两者写盘都以 `--root` 实例根为基准。
12. commit 拆三个：Step 7→ 不，commit 在 Step 8a/8b/9（见工作流）。

## 工作流

```
Step 0  Codex spec review + 单独 commit
        │ 通过 → Step 1.0
        ▼
Step 1.0 抓 baseline（改代码前！）：用未改的 lint/graph 跑回归 fixture，
         存 /tmp/lint_before.json + /tmp/graph_before.json（去时间字段）
        ▼
Step 1  wiki_common: 加 BASE_SCHEMA（抽取 wiki_lint 内联 schema 常量）
        ▼
Step 2  wiki_lint: 校验改读 effective schema；逻辑不变（先不接 profile，纯抽取）
        ▼
Step 3  wiki_common: load_profile + 10 个 PROFILE_* 自校验 + merge_schema
        ▼
Step 4  wiki_lint + wiki_graph: 加 --root（实例根基准）+ 接 effective schema
                                wiki_graph 未知 type 跳过
        ▼
Step 5  文档：README / .wiki-schema.md / 01 / 05
        ▼
Step 6  （并入 Step 1~5，无独立步骤）
        ▼
Step 7  自检验证
          7a  零回归（无 profile）：重跑 RFC-006 E1~E11（结构等价）+ RFC-007 fixture（content_hash）
          7b  profile 专项：临时实例 + extra type 走通 lint+graph + 坏 profile 触发 PROFILE_*
          7c  --root：对临时实例跑通；清理无残留
        ▼
Step 8a commit apply 改动 [apply rfc-008]
Step 8b RFC-008 追加 ## Applied in <8a sha> + commit [rfc-008]
        ▼
Step 9  task status done + Execution log + commit [task]
```

## 步骤

### Step 0：Spec review

末尾追加：

```markdown
## Spec review by codex · 2026-05-28

### 完整性
- [ ] 10 条 RFC-008 Decision 约束是否都有步骤/验证
- [ ] BASE_SCHEMA 抽取范围是否覆盖 wiki_lint 现有所有内联 schema 常量
- [ ] 10 个 PROFILE_* 是否都有触发用例
- [ ] effective schema 如何影响 lint（id regex/enum/必填）与 graph（type 集）说清

### 可执行性
- [ ] Step 7a 零回归（结构等价口径）是否机械可跑
- [ ] Step 7b 临时实例 fixture 是否完整（含 .wiki-profile.json + case 页 + 坏 profile）
- [ ] Step 7c --root + 清理是否无残留

### 边界
- [ ] 7 路径白名单；临时实例建在 knowledge/ 外且清理
- [ ] core 不变量 profile 碰不到，验证里有体现

### 风险
- BASE_SCHEMA 抄漏 / 路径基准迁移 / profile 合并

### 结论
- 通过 / 需修改
```

commit：`[task] TASK-008 spec review by codex (conclusion: <...>)`。

### Step 1.0：抓 baseline（**改任何代码前必跑**）

用**未改动**的 lint/graph 对一套确定性回归 fixture 抓基线，供 Step 7a 做 before/after 结构等价对比。

```bash
conda activate py312
set +e
# 回归 fixture 注入 knowledge/（改代码前用默认 knowledge/，因为此时还没 --root）
mk_regress() {
  mkdir -p knowledge/wiki/entities knowledge/wiki/topics knowledge/wiki/sources
  cat > knowledge/wiki/entities/rg-a.md <<'EOF'
---
id: ent_20260528_rg-a
type: entity
status: active
confidence: medium
created: 2026-05-28
updated: 2026-05-28
last_verified: 2026-05-28
review: false
aliases: [RgAlias]
canonical_id: null
source_ids: []
related_ids: []
supersedes: []
superseded_by: []
evidence_count: 0
---
# Rg A
EOF
  cat > knowledge/wiki/sources/rg-c.md <<'EOF'
---
id: src_20260528_rg-c
type: source
status: active
confidence: high
created: 2026-05-28
updated: 2026-05-28
last_verified: 2026-05-28
review: false
source_id: src_20260528_rg-c
hash_sha256: 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08
original_path: raw/sources/rg-c.pdf
source_url: null
imported_at: 2026-05-28T10:00:00+08:00
source_ids: []
related_ids: []
supersedes: []
superseded_by: []
evidence_count: 1
---
# Rg C
EOF
  cat > knowledge/wiki/topics/rg-b.md <<'EOF'
---
id: top_20260528_rg-b
type: topic
status: active
confidence: medium
created: 2026-05-28
updated: 2026-05-28
last_verified: 2026-05-28
review: false
source_ids: [src_20260528_rg-c]
related_ids: [ent_20260528_rg-a]
sources: []
related: []
supersedes: []
superseded_by: []
evidence_count: 1
---
# Rg B
正文 [[RgAlias]] 与 [[Ghost]]
EOF
  # 一个 ENUM_INVALID（坏 status）触发错误路径
  cat > knowledge/wiki/topics/rg-bad.md <<'EOF'
---
id: top_20260528_rg-bad
type: topic
status: not_a_status
confidence: medium
created: 2026-05-28
updated: 2026-05-28
last_verified: 2026-05-28
review: false
source_ids: []
related_ids: []
sources: []
related: []
supersedes: []
superseded_by: []
evidence_count: 0
---
# Rg Bad
EOF
}
rm_regress() { rm -f knowledge/wiki/entities/rg-a.md knowledge/wiki/sources/rg-c.md knowledge/wiki/topics/rg-b.md knowledge/wiki/topics/rg-bad.md; }
# 去时间字段后存 JSON（结构等价基准）
strip_json() { python3 -c "
import json,sys,re
d=json.load(open(sys.argv[1]))
def strip(o):
    if isinstance(o,dict): return {k:strip(v) for k,v in o.items() if k not in ('ran_at','updated_at','generated_at')}
    if isinstance(o,list): return [strip(x) for x in o]
    return o
json.dump(strip(d),open(sys.argv[2],'w'),sort_keys=True,ensure_ascii=False,indent=2)
" "$1" "$2"; }

trap rm_regress EXIT
mk_regress
python scripts/wiki_lint.py --json --check-only > /tmp/lint_before_raw.json 2>/dev/null
strip_json /tmp/lint_before_raw.json /tmp/lint_before.json
python scripts/wiki_graph.py --json > /tmp/graph_before_raw.json 2>/dev/null
strip_json /tmp/graph_before_raw.json /tmp/graph_before.json
echo "baseline content_hash: $(python3 -c "import json;print(json.load(open('/tmp/graph_before_raw.json')).get('content_hash'))")"
rm_regress; trap - EXIT
# 把 mk_regress/rm_regress/strip_json 三个函数原样保留到 Step 7a 复用
```

> Step 1.0 与 Step 7a 用**完全相同的 fixture**（`mk_regress`）。Step 7a 在 refactor 后重跑并和 `/tmp/lint_before.json` / `/tmp/graph_before.json` 比对。

### Step 1：`wiki_common.BASE_SCHEMA`（封闭清单）

把 `wiki_lint.py` 现有内联 schema / 契约常量**逐一**收拢到 `wiki_common.py` 的 `BASE_SCHEMA`（结构见 RFC-008 #1），**内容不增不删**。

**封闭清单**（v2，解决 review #4——必须全覆盖，不是"至少"）。下列现有 lint 常量逐一纳入 BASE_SCHEMA（或由它派生）：

- page type / prefix：`TYPE_PREFIX`（8 类 → token，无下划线）+ 各 `dir`
- id 正则：`WIKI_ID_RE` / `INBOX_ID_RE` / `INBOX_FILE_RE`（改由 `effective_id_regex(schema)` 动态生成，base 集合等价现有）
- 页面 enum：core `status` / `confidence`
- inbox：`INBOX_STATUSES` / `SUGGESTED_TYPES` / inbox required fields / `id_prefix: "inb"`
- source manifest：`SOURCE_TYPES` / `SOURCE_STATUSES` / `SOURCE_ADAPTERS` + manifest required fields
- review queue：`REVIEW_TYPES` / `REVIEW_STATUSES` / `PRIORITIES` + review item required fields
- capture policy：required fields + version 约束
- core 必填字段、canonical list fields、source 专属 required fields（source_id/hash_sha256/...）、entity 专属（aliases/canonical_id）
- context docs 四文件名（purpose/index/overview/log，无 frontmatter 反向校验）

> **不进 BASE_SCHEMA 的**（保持代码常量即可）：纯算法常量（PII 正则来自 capture_policy 非 schema、label propagation 轮数、原子写临时名规则等）。executor 在 Execution log 列出"哪些进了 BASE_SCHEMA / 哪些保持代码常量"，便于 evaluator 核对无抄漏。

提供 `effective_id_regex(schema)`：由 schema 的 `id_prefix` 集合动态拼 `^(src|ent|...|<extra>)_\d{8}_...`；base-only 时必须与现有 `WIKI_ID_RE` 等价。

### Step 2：`wiki_lint` 读 BASE_SCHEMA（纯抽取，逻辑不变）

把 wiki_lint 内联字面量改为读 `BASE_SCHEMA`。**此步先不接 profile**——只验证"把常量挪个位置"后行为等价（Step 7a 的一部分可在此 mini 验证）。不改 error code 集合 / run_lint 返回 / 退出码。

### Step 3：profile 加载 + 自校验 + merge

`wiki_common`：

- `load_profile(instance_root)`：读 `<root>/.wiki-profile.json`，不存在返回空 profile
- `validate_profile(profile, base)`：跑 10 个 `PROFILE_*` 检查（RFC-008 #4 表），返回 issues
- `merge_schema(base, profile)`：profile 自校验通过后产出 effective schema（page_types ∪ extra；新字段 enum；extra optional fields）

10 个 PROFILE_* 严格按 RFC-008 #4 表实现（SCHEMA_VERSION / PREFIX_FORMAT / PREFIX_COLLISION / TYPE_COLLISION / DIR_INVALID / FIELD_INVALID / FIELD_OVERLAP / CORE_SHADOW / ENUM_UNKNOWN_FIELD / OPTFIELD_UNKNOWN_TYPE）。任一 error → lint exit 1，不产出 effective schema。

**merge 顺序钉死**（v2，解决 review 风险）：① `validate_profile`（10 个 PROFILE_* 全跑）→ 有 error 即 exit 1 停止 ② merge `page_types`（base ∪ extra）③ 计算 `effective_id_regex` / prefix→type map ④ 合并新字段 enum + extra optional fields ⑤ 再做页面/文档校验。

### Step 4：`--root` + 接 effective schema + graph

- 两脚本加 `--root <instance>`（缺省 `<repo>/knowledge`）；**所有路径基准**从 `ROOT/"knowledge/..."` 迁到 `INSTANCE_ROOT/"..."`
- 启动回显当前实例根 + profile 名
- `wiki_lint`：校验用 `merge_schema(BASE_SCHEMA, load_profile(root))`；profile 非法时先报 PROFILE_* 并 exit 1
- `wiki_graph`：节点 type 集 / id_prefix 取自 effective schema；**未知 type 跳过 + 计 insights，不报错**（不重复 schema 校验）
- `wiki_graph` 仍永不写 `.wiki/*`；写 `<root>/maps/*`

### Step 5：文档

- `scripts/README.md`：profile 机制 + `--root` 用法 + 10 个 PROFILE_* + 多实例说明
- `knowledge/.wiki-schema.md`：增 "schema profile" 概念段（本实例无 profile = 纯 base）
- `wiki-design/01-architecture.md`：增"多实例 + schema profile"段
- `wiki-design/05-contracts-and-next-steps.md`：增 **Wiki Profile Schema** 契约段（`.wiki-profile.json` 字段，RFC-008 #2）

### Step 7：自检验证

```bash
conda activate py312
set +e
PASS=1; fail(){ echo "  FAIL: $1"; PASS=0; }

echo "=== Preflight ==="
python --version
python -c "import yaml; print('PyYAML', yaml.__version__)" || { echo FAIL; exit 2; }

echo "=== 7a-1. 零回归：refactor 后重跑 baseline fixture，与 Step 1.0 before 结构等价 ==="
# 复用 Step 1.0 的 mk_regress / rm_regress / strip_json（原样保留）
trap rm_regress EXIT
mk_regress
python scripts/wiki_lint.py --json --check-only > /tmp/lint_after_raw.json 2>/dev/null
strip_json /tmp/lint_after_raw.json /tmp/lint_after.json
python scripts/wiki_graph.py --json > /tmp/graph_after_raw.json 2>/dev/null
strip_json /tmp/graph_after_raw.json /tmp/graph_after.json
diff -q /tmp/lint_before.json /tmp/lint_after.json >/dev/null && echo "  OK: lint --json 结构等价（去时间字段）" || fail "lint 结构不等价（回归！）"
HB=$(python3 -c "import json;print(json.load(open('/tmp/graph_before_raw.json')).get('content_hash'))")
HA=$(python3 -c "import json;print(json.load(open('/tmp/graph_after_raw.json')).get('content_hash'))")
[ "$HB" = "$HA" ] && echo "  OK: graph content_hash 一致（$HB）" || fail "graph content_hash 漂移（回归！）"
rm_regress; trap - EXIT

echo "=== 7a-2. --root knowledge 与默认调用等价 ==="
python scripts/wiki_lint.py --json --check-only > /tmp/def_raw.json 2>/dev/null
python scripts/wiki_lint.py --root knowledge --json --check-only > /tmp/root_raw.json 2>/dev/null
strip_json /tmp/def_raw.json /tmp/def.json; strip_json /tmp/root_raw.json /tmp/root.json
diff -q /tmp/def.json /tmp/root.json >/dev/null && echo "  OK: 默认 == --root knowledge（去时间字段）" || fail "--root knowledge 与默认不等价（路径迁移 bug）"

echo "=== 7b. profile 专项（临时实例 knowledge-gtest/，建在 knowledge/ 外）==="
cleanup_gtest(){ rm -rf knowledge-gtest /tmp/g8*.json 2>/dev/null; }
trap cleanup_gtest EXIT
setup_gtest(){
  rm -rf knowledge-gtest
  mkdir -p knowledge-gtest/wiki/cases knowledge-gtest/wiki/topics knowledge-gtest/raw/sources knowledge-gtest/inbox knowledge-gtest/maps knowledge-gtest/.wiki
  # 上下文层四文件（验证 instance-root 路径迁移）
  for f in purpose index overview log; do printf '# %s\n' "$f" > "knowledge-gtest/$f.md"; done
  printf '{"version":1,"sources":[]}\n' > knowledge-gtest/raw/source_manifest.json
  printf '{"version":1,"items":[]}\n' > knowledge-gtest/.wiki/review_queue.json
  printf '{"version":1,"auto_capture":false,"exclude_patterns":[],"exclude_paths":[],"max_inbox_files":100,"updated_at":"2026-05-28T00:00:00+08:00"}\n' > knowledge-gtest/.wiki/capture_policy.json
}
write_profile(){ cat > knowledge-gtest/.wiki-profile.json; }
has_code(){ python3 -c "import json,sys;d=json.load(sys.stdin);print('YES' if any(e['code']=='$1' for e in d['errors']) else 'NO')"; }

# --- 7b-1. 合法 profile：extra type case 走通 lint + graph ---
setup_gtest
write_profile <<'EOF'
{ "schema_version":1, "profile":"gtest",
  "extra_page_types":[ {"type":"case","id_prefix":"case","dir":"wiki/cases","required_fields":["case_id"],"optional_fields":[]} ],
  "extra_field_enums":{}, "extra_optional_fields":{} }
EOF
cat > knowledge-gtest/wiki/cases/c1.md <<'EOF'
---
id: case_20260528_c1
type: case
status: active
confidence: medium
created: 2026-05-28
updated: 2026-05-28
last_verified: 2026-05-28
review: false
case_id: CASE-001
source_ids: []
related_ids: []
supersedes: []
superseded_by: []
evidence_count: 0
---
# Case 1
EOF
python scripts/wiki_lint.py --root knowledge-gtest --check-only >/dev/null 2>&1
[ $? = 0 ] && echo "  OK: 合法 case 页 lint exit 0" || fail "合法 case 页未通过 lint"
python scripts/wiki_graph.py --root knowledge-gtest --json 2>/dev/null | python3 -c "import json,sys;g=json.load(sys.stdin);sys.exit(0 if any(n['id']=='case_20260528_c1' for n in g['nodes']) else 1)" && echo "  OK: case 节点进图" || fail "case 未进图"

# --- 7b-2. case 缺 required field case_id → MISSING_FIELD ---
cat > knowledge-gtest/wiki/cases/c1.md <<'EOF'
---
id: case_20260528_c1
type: case
status: active
confidence: medium
created: 2026-05-28
updated: 2026-05-28
last_verified: 2026-05-28
review: false
source_ids: []
related_ids: []
supersedes: []
superseded_by: []
evidence_count: 0
---
# Case 1
EOF
r=$(python scripts/wiki_lint.py --root knowledge-gtest --json --check-only 2>/dev/null | has_code MISSING_FIELD)
[ "$r" = YES ] && echo "  OK: case 缺 case_id → MISSING_FIELD" || fail "profile required_field 未校验"
rm -f knowledge-gtest/wiki/cases/c1.md

# --- 7b-3. unknown type 跳过 + 计 insights ---
cat > knowledge-gtest/wiki/topics/unk.md <<'EOF'
---
id: zzz_20260528_unk
type: zzz_unknown
status: active
confidence: low
created: 2026-05-28
updated: 2026-05-28
last_verified: 2026-05-28
review: false
source_ids: []
related_ids: []
supersedes: []
superseded_by: []
evidence_count: 0
---
# Unknown
EOF
python scripts/wiki_graph.py --root knowledge-gtest --json 2>/dev/null | python3 -c "import json,sys;g=json.load(sys.stdin);sys.exit(0 if not any(n.get('type')=='zzz_unknown' for n in g['nodes']) else 1)" && echo "  OK: unknown type 未进图节点" || fail "unknown type 误进图"
python scripts/wiki_graph.py --root knowledge-gtest >/dev/null 2>&1
grep -q "unknown" knowledge-gtest/maps/graph-insights.md && echo "  OK: unknown type 计入 insights" || fail "unknown type 未计 insights"
rm -f knowledge-gtest/wiki/topics/unk.md

# --- 7b-4. 10 个 PROFILE_* 全覆盖（每个坏 profile 触发对应 code）---
chk_profile(){ # $1=expected_code  (stdin = profile json)
  write_profile
  r=$(python scripts/wiki_lint.py --root knowledge-gtest --json --check-only 2>/dev/null | has_code "$1")
  [ "$r" = YES ] && echo "  OK: [$1]" || fail "[$1] 未触发"
}
chk_profile PROFILE_SCHEMA_VERSION <<'EOF'
{"schema_version":999,"profile":"p","extra_page_types":[]}
EOF
chk_profile PROFILE_PREFIX_FORMAT <<'EOF'
{"schema_version":1,"profile":"p","extra_page_types":[{"type":"x","id_prefix":"BAD_","dir":"wiki/x","required_fields":[],"optional_fields":[]}]}
EOF
chk_profile PROFILE_PREFIX_COLLISION <<'EOF'
{"schema_version":1,"profile":"p","extra_page_types":[{"type":"x","id_prefix":"ent","dir":"wiki/x","required_fields":[],"optional_fields":[]}]}
EOF
chk_profile PROFILE_TYPE_COLLISION <<'EOF'
{"schema_version":1,"profile":"p","extra_page_types":[{"type":"entity","id_prefix":"xe","dir":"wiki/x","required_fields":[],"optional_fields":[]}]}
EOF
chk_profile PROFILE_DIR_INVALID <<'EOF'
{"schema_version":1,"profile":"p","extra_page_types":[{"type":"x","id_prefix":"xx","dir":"../escape","required_fields":[],"optional_fields":[]}]}
EOF
chk_profile PROFILE_FIELD_INVALID <<'EOF'
{"schema_version":1,"profile":"p","extra_page_types":[{"type":"x","id_prefix":"xx","dir":"wiki/x","required_fields":["Bad-Field"],"optional_fields":[]}]}
EOF
chk_profile PROFILE_FIELD_OVERLAP <<'EOF'
{"schema_version":1,"profile":"p","extra_page_types":[{"type":"x","id_prefix":"xx","dir":"wiki/x","required_fields":["foo"],"optional_fields":["foo"]}]}
EOF
chk_profile PROFILE_CORE_SHADOW <<'EOF'
{"schema_version":1,"profile":"p","extra_page_types":[{"type":"x","id_prefix":"xx","dir":"wiki/x","required_fields":["status"],"optional_fields":[]}]}
EOF
chk_profile PROFILE_ENUM_UNKNOWN_FIELD <<'EOF'
{"schema_version":1,"profile":"p","extra_page_types":[],"extra_field_enums":{"status":["a"]}}
EOF
chk_profile PROFILE_OPTFIELD_UNKNOWN_TYPE <<'EOF'
{"schema_version":1,"profile":"p","extra_page_types":[],"extra_optional_fields":{"no_such_type":["foo"]}}
EOF

echo "=== 7c. 清理 + 默认实例回归确认 ==="
cleanup_gtest; trap - EXIT
python scripts/wiki_lint.py --check-only >/dev/null 2>&1; [ $? = 0 ] && echo "  OK: 默认 knowledge/ 仍 exit 0" || fail "默认实例被搞挂"
echo "=== 白名单检查（Step 8a commit 前；RFC-008 在 8b 单独提交不在此白名单）==="
extra=$(git status --porcelain -uall | cut -c4- | grep -Ev '^scripts/wiki_common\.py$|^scripts/wiki_lint\.py$|^scripts/wiki_graph\.py$|^scripts/README\.md$|^knowledge/\.wiki-schema\.md$|^wiki-design/01-architecture\.md$|^wiki-design/05-contracts-and-next-steps\.md$|^wiki-design/tasks/TASK-008-apply-rfc-008\.md$')
[ -z "$extra" ] && echo "  OK: 白名单外无改动" || { echo "  FAIL:"; echo "$extra" | sed 's/^/    /'; PASS=0; }
echo "=== 验证结束：PASS=$PASS（1=全过）==="
```

预期：7a-1 lint 结构等价 + graph content_hash 一致（零回归）；7a-2 默认==--root knowledge；7b-1~3 case 走通 lint+graph、required field 校验、unknown type 跳过+计 insights；7b-4 十个 PROFILE_* 全部触发；7c 清理后默认实例 exit 0、白名单外无改动。任一 fail → PASS=0 → 本 task 失败。

### Step 8a：commit apply

```bash
git add scripts/wiki_common.py scripts/wiki_lint.py scripts/wiki_graph.py scripts/README.md knowledge/.wiki-schema.md wiki-design/01-architecture.md wiki-design/05-contracts-and-next-steps.md
git commit -m "[apply rfc-008] implement schema profile mechanism ..."
```

确认 `git status` 无 knowledge-gtest/ / maps/ 残留被 add。

### Step 8b：RFC-008 Applied

```bash
# RFC-008 末尾追加 ## Applied in <8a sha>
git add wiki-design/rfcs/RFC-008-schema-profiles.md
git commit -m "[rfc-008] applied in <8a sha>"
```

### Step 9：task done

frontmatter status → done + 追加 Execution log + `git commit -m "[task] TASK-008 done by codex"`。

## 完成后报告格式

```markdown
## Execution log by codex · 2026-05-28

### 步骤完成情况
- Step 0~5: done（列要点：BASE_SCHEMA 抽了哪些常量 / PROFILE_* 实现 / --root）
- Step 7 验证: 输出见下

### 验证输出
\`\`\`
<Step 7 全部输出，含 7a 的 E1~E11 + RFC-007 fixture>
\`\`\`

### Commit
- Step 8a / 8b / 9 sha

### 偏离 / 异常
<如实写；lint/graph 任何回归必须说明>
```

## Spec review by codex · YYYY-MM-DD

（待 Codex 填写）

## Spec review by codex · 2026-05-28

### 完整性

- 结论：需修改。
- RFC-008 的主路径（BASE_SCHEMA、profile overlay、`--root` 实例根、文档同步、apply/RFC/task 三段提交）都有对应步骤。
- BASE_SCHEMA 抽取范围写得还不够全。当前 `wiki_lint.py` 内联 schema 不只包括 8 类 page type、core enum、source/entity 字段和“三个 JSON 契约 enum”，还包括：
  - `INBOX_STATUSES`、`SUGGESTED_TYPES`
  - `SOURCE_TYPES`、`SOURCE_STATUSES`、`SOURCE_ADAPTERS`
  - `REVIEW_TYPES`、`REVIEW_STATUSES`、`PRIORITIES`
  - `TYPE_PREFIX`、`WIKI_ID_RE`、`INBOX_ID_RE`、`INBOX_FILE_RE`
  - source manifest / review queue / capture policy 的 required field 列表
  - context docs 四文件名、canonical list fields、source 专属 required fields、inbox required fields
  这些都属于“schema 常量或契约常量”。Spec 的“至少覆盖”容易让 executor 只抽一部分，建议列成封闭清单或明确哪些保持代码常量不进 BASE_SCHEMA。
- 10 个 `PROFILE_*` 在实现步骤里都列到了，但 Step 7b 只验证了 `PROFILE_PREFIX_COLLISION`。这不满足 Step 0 自己要求的“10 个 PROFILE_* 是否都有触发用例”，也无法发现 profile 自校验漏实现。

### 可执行性

- Step 7a 仍不可机械执行：它要求“粘贴 TASK-006 Step 6 的 Preflight+A~E”和“粘贴 TASK-007 Step 7c”，但没有内嵌脚本，也没有说明怎么把旧脚本里的 `knowledge/` 路径、`python3`/py312、白名单段、fixture 清理和 TASK-008 当前白名单结合起来。TASK-007 已经因为类似复制方式出现过白名单/环境偏差，建议把 7a 需要跑的脚本直接写死到 TASK-008，或至少给出可复制的完整 shell block。
- “结构等价口径”没有真正落成命令。当前 7a 只回归了 E1~E11 code 命中，并没有保存 refactor 前 baseline，也没有去掉 `ran_at` / `updated_at` 后做 JSON 结构比较。若目标是证明无 profile 等价，spec 需要给出机械命令，例如：
  - apply 前先生成 `/tmp/before_lint_check.json`、`/tmp/before_id_index.json` 等；
  - apply 后生成对应 after；
  - 用 Python 递归删除 `ran_at` / `updated_at` 后比较。
  否则“结构等价”只是口头约束。
- Step 7b 临时实例 fixture 有可跑通的雏形，但断言逻辑偏弱：
  - `python scripts/wiki_lint.py --root knowledge-gtest --json --check-only ... | python3 -c ...` 只检查没有 `ID_FORMAT/ENUM_INVALID`，没有检查 exit code 是否为 0，也没有检查 `case_id` required field 真被校验。
  - 坏 profile 测试只覆盖 prefix collision；缺少 `SCHEMA_VERSION / PREFIX_FORMAT / TYPE_COLLISION / DIR_INVALID / FIELD_INVALID / FIELD_OVERLAP / CORE_SHADOW / ENUM_UNKNOWN_FIELD / OPTFIELD_UNKNOWN_TYPE`。
  - 临时实例没有 `purpose.md/index.md/overview.md/log.md`，这对当前 lint 没问题，但如果 Step 4 后 context docs path 迁移有 bug，7b 不会捕捉；可以在 fixture 里补这四个无 frontmatter文件，顺带验证 instance-root 基准。
- `--root` 对临时实例理论上能跑通，但 spec 没有要求验证默认 `knowledge/` 与 `--root knowledge` 两种调用等价。路径基准迁移风险很高，建议 7a/7c 加一项：默认调用和 `--root knowledge` 在去时间字段后结构等价。

### 边界

- 临时实例建在 `knowledge-gtest/` 且有 `trap` 清理，方向正确。
- 白名单漏了 RFC-008 文件本身。Step 8b 会追加 `wiki-design/rfcs/RFC-008-schema-profiles.md`，而 Step 7 白名单在 Step 8a 前跑可以不放行 RFC；但如果 executor 复跑验证或日志整理时机不同会误报。建议说明白名单检查只在 Step 8a 前执行，或把 Step 8b 前后检查拆开。
- core 不变量“profile 碰不到”没有在验证体现。至少应有坏 profile 用例覆盖：
  - `PROFILE_CORE_SHADOW`：给 `status` / `confidence` / `id` 加 enum 或 required/optional shadow
  - `PROFILE_ENUM_UNKNOWN_FIELD`：enum 指向 base 字段或未知字段
  - `PROFILE_DIR_INVALID`：dir 逃逸 `../` 或不在 `wiki/`
  这样才能证明 profile 不能改 core / 不能越界。
- `wiki_graph` 未知 type 跳过 + 计 insights 在 Step 4 写了，但 Step 7 没有验证 unknown type 被跳过，也没有验证 “计入 insights”。建议新增一个未声明 type 页，断言 graph 不含该节点，`graph-insights.md` 或 JSON meta 中有 unknown type 记录；否则实现可能直接忽略而没有 insights。

### 风险

- BASE_SCHEMA 抄漏是最大风险；当前 spec 还没把 lint 中所有内联契约列成封闭清单。
- 路径基准迁移风险高；`wiki_lint.py` 当前至少有 `ROOT / "knowledge/wiki"`、`ROOT / "knowledge/inbox"`、`ROOT / "knowledge/raw/source_manifest.json"`、`ROOT / "knowledge/.wiki/*.json"`、`ROOT / "knowledge" / summary_path` 等多处硬编码，`wiki_graph.py` 也有 `.wiki` 和 `maps` 硬编码。Spec 应要求用 `INSTANCE_ROOT` 统一替换，并验证默认调用、`--root knowledge`、`--root knowledge-gtest` 三路。
- profile 合并顺序建议写死：先 validate profile → merge page_types → 计算 id regex/prefix map → 再校验文档。现在方向有，但顺序没有足够机械。

### 结论

- 需修改。
- 建议修订 Step 1 的 BASE_SCHEMA 封闭清单、Step 7a 的完整可执行零回归脚本、Step 7b 的 10 个 PROFILE_* 触发用例，以及 `--root knowledge` 等价验证后再进入执行。

## Execution log by codex · YYYY-MM-DD

（待执行者填写）

## Evaluation by claude · YYYY-MM-DD

（待评估者填写）

## Revision v2 by claude · 2026-05-28

addressing codex spec review v1 的 5 阻塞点。

1. **Step 1 BASE_SCHEMA 封闭清单**（review #4）：用 Codex 给的实际常量清单（TYPE_PREFIX / WIKI_ID_RE / INBOX_ID_RE / INBOX_FILE_RE / INBOX_STATUSES / SUGGESTED_TYPES / SOURCE_TYPES·STATUSES·ADAPTERS / REVIEW_TYPES·STATUSES·PRIORITIES / 各 required fields / context docs 四文件名）列成**封闭清单**，并要求 executor 在 log 列"哪些进 BASE_SCHEMA / 哪些保持代码常量"。
2. **Step 1.0 baseline + Step 7a 结构等价落成命令**（review #1/#2）：新增 Step 1.0（改代码前抓 baseline），定义确定性回归 fixture（mk_regress）+ strip_json（递归删 ran_at/updated_at/generated_at）。Step 7a refactor 后重跑同 fixture，`diff` lint 结构 + 比 graph content_hash。去"粘贴 TASK-006/007"占位。
3. **Step 7a-2 --root knowledge 等价**（review #5）：默认调用 vs `--root knowledge` 去时间字段后 `diff` 等价，守路径基准迁移。
4. **Step 7b 十个 PROFILE_* 全覆盖**（review #3）：`chk_profile` + 10 个坏 profile，逐个触发 SCHEMA_VERSION/PREFIX_FORMAT/PREFIX_COLLISION/TYPE_COLLISION/DIR_INVALID/FIELD_INVALID/FIELD_OVERLAP/CORE_SHADOW/ENUM_UNKNOWN_FIELD/OPTFIELD_UNKNOWN_TYPE。
5. **Step 7b unknown type + case required field + 上下文层路径**（review #5/边界）：临时实例补 purpose/index/overview/log 四文件（验路径迁移）；case 缺 case_id → MISSING_FIELD；unknown type 断言不进图节点 + 计 insights。
6. **merge 顺序钉死**（review 风险）：Step 3 加 validate→merge page_types→算 id regex→合并字段→文档校验五步。
7. **白名单时机**（review 边界）：注明白名单检查在 Step 8a 前；RFC-008 在 8b 单独提交不在此白名单。

未改动：12 条强约束主体、9 步工作流骨架。Codex Spec review v1 段保留（append-only）。

待 Codex re-review。
