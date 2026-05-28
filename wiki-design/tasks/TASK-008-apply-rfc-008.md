---
id: task_20260528_008
title: Apply RFC-008 — 实现 schema profile 机制（BASE_SCHEMA 抽取 + profile overlay + --root）
author: claude
executor: codex
status: pending
type: apply
created: 2026-05-28
updated: 2026-05-28
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
        │ 通过 → Step 1
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

### Step 1：`wiki_common.BASE_SCHEMA`

把 `wiki_lint.py` 现有内联 schema 常量**逐一**收拢到 `wiki_common.py` 的 `BASE_SCHEMA`（结构见 RFC-008 #1），**内容不增不删**。至少覆盖：

- 8 类 page type → `id_prefix`（token，无下划线）+ `dir`
- inbox：`id_prefix: "inb"`（秒级时间戳格式另存）
- core 必填字段 / `status` / `confidence` core enum
- source / entity 专属字段（source_id/hash_sha256/aliases/canonical_id...）
- 三个 JSON 契约 enum（source_manifest / review_queue / capture_policy）

提供 `effective_id_regex(schema)`：由 schema 的 `id_prefix` 集合动态拼 `^(src|ent|...|<extra>)_\d{8}_...`。

### Step 2：`wiki_lint` 读 BASE_SCHEMA（纯抽取，逻辑不变）

把 wiki_lint 内联字面量改为读 `BASE_SCHEMA`。**此步先不接 profile**——只验证"把常量挪个位置"后行为等价（Step 7a 的一部分可在此 mini 验证）。不改 error code 集合 / run_lint 返回 / 退出码。

### Step 3：profile 加载 + 自校验 + merge

`wiki_common`：

- `load_profile(instance_root)`：读 `<root>/.wiki-profile.json`，不存在返回空 profile
- `validate_profile(profile, base)`：跑 10 个 `PROFILE_*` 检查（RFC-008 #4 表），返回 issues
- `merge_schema(base, profile)`：profile 自校验通过后产出 effective schema（page_types ∪ extra；新字段 enum；extra optional fields）

10 个 PROFILE_* 严格按 RFC-008 #4 表实现（SCHEMA_VERSION / PREFIX_FORMAT / PREFIX_COLLISION / TYPE_COLLISION / DIR_INVALID / FIELD_INVALID / FIELD_OVERLAP / CORE_SHADOW / ENUM_UNKNOWN_FIELD / OPTFIELD_UNKNOWN_TYPE）。任一 error → lint exit 1，不产出 effective schema。

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

echo "=== Preflight ==="
python --version
python -c "import yaml; print('PyYAML', yaml.__version__)" || { echo FAIL; exit 2; }

echo "=== 7a. 零回归（无 profile，默认 knowledge/）==="
echo "--- lint 空库 --check-only exit 0 ---"
python scripts/wiki_lint.py --check-only >/dev/null 2>&1; echo "  exit: $? (期望 0)"
echo "--- 重跑 RFC-006 E1~E11：复制 TASK-006 Step 6 的 Preflight + A~E（不复制 F）"
echo "    结构等价口径：human 输出去时间行 / --json 去 ran_at 后比对；E1~E11 code 全 HIT ---"
# >>> 粘贴 TASK-006 Step6 的 Preflight+A~E（E1~E11 注入→验 code→还原）<<<
echo "--- 重跑 RFC-007 fixture：复制 TASK-007 Step 7c（含 trap + 全 .wiki 快照 + content_hash）"
echo "    断言 redirect 折叠/5 类边/alias 解析/co_source/content_hash 确定性/永不写 .wiki ---"
# >>> 粘贴 TASK-007 Step7c <<<
echo "  （E1~E11 + RFC-007 fixture 全 OK = base 行为零回归；任一 FAIL = 失败）"

echo "=== 7b. profile 专项（临时实例 knowledge-gtest/，建在 knowledge/ 外）==="
cleanup_gtest() { rm -rf knowledge-gtest /tmp/g8*.json 2>/dev/null; }
trap cleanup_gtest EXIT
mkdir -p knowledge-gtest/wiki/cases knowledge-gtest/wiki/entities knowledge-gtest/raw/sources knowledge-gtest/inbox knowledge-gtest/maps knowledge-gtest/.wiki
printf '{"version":1,"sources":[]}\n' > knowledge-gtest/raw/source_manifest.json
printf '{"version":1,"items":[]}\n' > knowledge-gtest/.wiki/review_queue.json
printf '{"version":1,"auto_capture":false,"exclude_patterns":[],"exclude_paths":[],"max_inbox_files":100,"updated_at":"2026-05-28T00:00:00+08:00"}\n' > knowledge-gtest/.wiki/capture_policy.json
# 合法 profile：extra type case
cat > knowledge-gtest/.wiki-profile.json <<'EOF'
{
  "schema_version": 1,
  "profile": "gtest",
  "extra_page_types": [
    { "type": "case", "id_prefix": "case", "dir": "wiki/cases",
      "required_fields": ["case_id"], "optional_fields": [] }
  ],
  "extra_field_enums": {},
  "extra_optional_fields": {}
}
EOF
# case 页（合法）
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
echo "--- lint 接受 extra type case 页（无 ID_FORMAT/ENUM_INVALID）---"
python scripts/wiki_lint.py --root knowledge-gtest --json --check-only 2>/dev/null | python3 -c "
import json,sys; d=json.load(sys.stdin)
bad=[e for e in d['errors'] if e['code'] in ('ID_FORMAT','ENUM_INVALID') and 'c1.md' in (e.get('file') or '')]
print('  OK: case 页被接受' if not bad else f'  FAIL: {bad}')
"
echo "--- graph 把 case 投影为节点 ---"
python scripts/wiki_graph.py --root knowledge-gtest --json 2>/dev/null | python3 -c "
import json,sys; g=json.load(sys.stdin)
print('  OK: case 节点在图中' if any(n['id']=='case_20260528_c1' for n in g['nodes']) else '  FAIL: case 未进图')
"
echo "--- 坏 profile 触发 PROFILE_*（prefix 撞 base 'ent'）---"
cat > knowledge-gtest/.wiki-profile.json <<'EOF'
{ "schema_version": 1, "profile": "bad",
  "extra_page_types": [ { "type": "x", "id_prefix": "ent", "dir": "wiki/x", "required_fields": [], "optional_fields": [] } ] }
EOF
python scripts/wiki_lint.py --root knowledge-gtest --json --check-only 2>/dev/null | python3 -c "
import json,sys; d=json.load(sys.stdin)
print('  OK: PROFILE_PREFIX_COLLISION 触发' if any(e['code']=='PROFILE_PREFIX_COLLISION' for e in d['errors']) else '  FAIL: 未触发')
"

echo "=== 7c. --root 清理无残留 ==="
cleanup_gtest; trap - EXIT
echo "--- 默认 knowledge/ 仍正常（回归确认）---"
python scripts/wiki_lint.py --check-only >/dev/null 2>&1; echo "  默认 exit: $? (期望 0)"
echo "=== 白名单检查 ==="
extra=$(git status --porcelain -uall | cut -c4- | grep -Ev '^scripts/wiki_common\.py$|^scripts/wiki_lint\.py$|^scripts/wiki_graph\.py$|^scripts/README\.md$|^knowledge/\.wiki-schema\.md$|^wiki-design/01-architecture\.md$|^wiki-design/05-contracts-and-next-steps\.md$|^wiki-design/tasks/TASK-008-apply-rfc-008\.md$')
if [ -z "$extra" ]; then echo "  OK: 白名单外无改动"; else echo "  FAIL:"; echo "$extra" | sed 's/^/    /'; fi
echo "=== 验证结束 ==="
```

预期：7a 零回归全 OK（E1~E11 + RFC-007 fixture）；7b case 被接受 + 进图 + 坏 profile 报 PROFILE_PREFIX_COLLISION；7c 清理后白名单外无改动、默认实例仍 exit 0。

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

## Execution log by codex · YYYY-MM-DD

（待执行者填写）

## Evaluation by claude · YYYY-MM-DD

（待评估者填写）
