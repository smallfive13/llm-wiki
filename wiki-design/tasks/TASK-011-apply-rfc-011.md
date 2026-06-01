---
id: task_20260601_011
title: Apply RFC-011 — wiki_init Obsidian 友好增强
author: claude
executor: codex
status: done
type: apply
created: 2026-06-01
updated: 2026-06-01  # v2 after codex spec review v1
related_rfcs:
  - rfc_20260601_011
---

# TASK-011: Apply RFC-011 — wiki_init Obsidian 友好增强

## 目标

给 `scripts/wiki_init.py` 加两件事:① 写/合并 `.obsidian/app.json` 排除派生层 ② 上下文层结构化占位。**不破坏 RFC-010 既有行为**(重跑 TASK-010 Step 5 防回归)。

## 前置条件

- 仓库根:`/Users/zhangjunwu/workspace/llm-wiki/llm-wiki`
- HEAD 含 **RFC-011 status: accepted**(commit `dda5598` 及之后)
- working tree clean
- 已读 RFC-011 全文(含 Decision 7 条约束 + v1/v2 review)
- 已读 `scripts/wiki_init.py` 现有实现(理解骨架生成 + 叠加 + git + 自检结构)、TASK-010 Step 5 验证脚本(重跑要用)
- conda `py312`

## 强约束

1. **只动**:`scripts/wiki_init.py`、`scripts/README.md`。
2. 本 TASK-011 文件按 Step 0 / 末步编辑;RFC-011 按倒数第二步追加 Applied。
3. **不动** `wiki_lint.py` / `wiki_graph.py` / `wiki_common.py` / `BASE_SCHEMA`、AGENTS.md、引擎 .gitignore、现有 `knowledge/` 与 `personal` 实例、其它 RFC/task。
4. 必须先经 Codex spec review(Step 0)。
5. 严格按 RFC-011 Decision 7 条,**不**自行扩展(尤其:app.json 是唯一可改已存在文件的例外,只动 userIgnoreFilters 一个键,不扩散到其它文件/键)。
6. **验证全在临时实例**(mktemp,knowledge/ 外,trap 清理),**绝不动用户真实 vault**。
7. commit 拆三个:apply 改动 / RFC-011 Applied / task done。

## 工作流

```
Step 0  Codex spec review + commit
        ▼
Step 1  改 wiki_init.py:加 app.json 合并 + 上下文层结构化模板
        ▼
Step 2  改 scripts/README.md(Obsidian 友好说明)
        ▼
Step 3  自检验证
          3a 新增 RFC-011 fixture(app.json 合并/异常/上下文层)
          3b 重跑 TASK-010 Step 5 全部(防回归)
        ▼
Step 4  commit apply [apply rfc-011]
Step 5  RFC-011 追加 ## Applied in <Step4 sha> + commit [rfc-011]
Step 6  task done + Execution log + commit [task]
```

## 步骤

### Step 0:Spec review

末尾追加 `## Spec review by codex · 2026-06-01`,检查:完整性(7 约束覆盖)/ 可执行性(app.json 合并 + 异常 exit2 + 上下文层 + fixture 机械可跑)/ 边界(只动 2 文件、不碰真实 vault、不扩散可改文件例外)/ 风险。commit `[task] TASK-011 spec review by codex (conclusion: <...>)`。

### Step 1:改 `scripts/wiki_init.py`

#### 1.1 app.json 合并(RFC-011 提案 #1)

新增逻辑:确保 `<root>/.obsidian/app.json` 的 `userIgnoreFilters` 含 `maps/` 和 `.wiki/`。

- `.obsidian/` 或 `app.json` 不存在 → 创建 `app.json = {"userIgnoreFilters": ["maps/", ".wiki/"]}`(原子写)
- `app.json` 存在 → `json.load`:
  - **解析失败(非法 JSON)→ exit 2** + 打印路径(不静默跳过、不覆盖)
  - 顶层不是 object → exit 2
  - `userIgnoreFilters` 不存在 → 设为 `["maps/", ".wiki/"]`,其它键深拷保留
  - `userIgnoreFilters` 是 list → **append-missing union**:保留原有项原顺序,末尾追加缺失的 `maps/` / `.wiki/`(已有则不重复)
  - `userIgnoreFilters` 存在但**非 list**(str/dict/...)→ exit 2(不覆盖)
  - 其它键**深拷原样保留**,写回(写回用 `json.dump` indent=2,允许缩进/顺序变化——只保证语义/键值不变)
- app.json 合并算作"修改已存在文件",计入报告(可在 created/skipped 之外加一行 `obsidian: merged|created|unchanged`)
- **此例外仅限 app.json 一个文件 + userIgnoreFilters 一个键**,不得推广。

放在 git 步骤前后皆可,但建议在自检(lint)前完成,且 app.json 不属于 git 派生层(它是 .obsidian 配置,RFC-010 的 .gitignore 已忽略 workspace*.json,app.json 本身可进 git——不强制)。

#### 1.2 上下文层结构化模板(RFC-011 提案 #2)

把 index.md / overview.md 的占位模板从空壳改为结构化骨架(**仍无 frontmatter**;只在文件不存在时写,已存在跳过——沿用 RFC-010 叠加语义):

- `index.md`:
  ```markdown
  # Index

  知识库入口。

  ## 主题

  （随知识增长，在此用 `[[slug|标题]]` 链接各页）

  ## 导航

  - [Purpose](purpose.md) — 知识库目的
  - [Overview](overview.md) — 主题总览
  - [Log](log.md) — 变更日志
  ```
  > 主题区 `[[slug|标题]]` 必须是 **inline code**(反引号包裹),否则它自己成 dangling wikilink。
- `overview.md`:
  ```markdown
  # Overview

  > 这个知识库目前包含什么、围绕什么主题展开。

  ## 主题

  （待填）

  ## 健康度

  | 指标 | 当前值 |
  | --- | --- |
  | wiki 页面 | 0 |
  ```
- `purpose.md`:保持现有占位(不改)。

### Step 2:`scripts/README.md`

wiki init 段补:Obsidian 友好初始化(默认写/合并 app.json 排除 maps/+.wiki/、上下文层结构化占位、异常 exit2)。明确"总是确保 app.json"是默认行为。

### Step 3:自检验证

```bash
conda activate py312; set +e
PASS=1; fail(){ echo "  FAIL: $1"; PASS=0; }
BASE=$(mktemp -d); trap 'rm -rf "$BASE"' EXIT

echo "=== 3a-1 app.json 不存在 → 创建含两项 ==="
A="$BASE/a"; mkdir -p "$A"
python3 scripts/wiki_init.py --root "$A" >/dev/null 2>&1 || fail "3a-1 init"
python3 -c "
import json,sys
d=json.load(open('$A/.obsidian/app.json'))
u=d.get('userIgnoreFilters',[])
sys.exit(0 if 'maps/' in u and '.wiki/' in u else 1)
" && echo "  OK: app.json 含 maps/ + .wiki/" || fail "app.json 缺排除项"

echo "=== 3a-2 已有 app.json(用户键 + 已有过滤项) → 保留 + 追加 ==="
B="$BASE/b"; mkdir -p "$B/.obsidian"
printf '{"theme":"obsidian","userIgnoreFilters":["私密/"],"accentColor":"#abc"}\n' > "$B/.obsidian/app.json"
python3 scripts/wiki_init.py --root "$B" >/dev/null 2>&1 || fail "3a-2 init"
python3 -c "
import json,sys
d=json.load(open('$B/.obsidian/app.json'))
# 用户键保留
assert d.get('theme')=='obsidian' and d.get('accentColor')=='#abc', '用户键丢失'
u=d['userIgnoreFilters']
# 已有项顺序保留 + 追加 maps/.wiki
assert u[0]=='私密/', '已有过滤项顺序变了'
assert 'maps/' in u and '.wiki/' in u, '未追加'
print('  OK: 用户键保留 + 已有过滤项顺序保留 + 追加 maps/.wiki')
" || fail "3a-2 合并语义"

echo "=== 3a-3 幂等:第二次不重复加 ==="
python3 scripts/wiki_init.py --root "$B" >/dev/null 2>&1
python3 -c "
import json,sys
u=json.load(open('$B/.obsidian/app.json'))['userIgnoreFilters']
sys.exit(0 if u.count('maps/')==1 and u.count('.wiki/')==1 else 1)
" && echo "  OK: union 去重(各 1 次)" || fail "重复添加"

echo "=== 3a-4 非法 JSON → exit 2 ==="
C="$BASE/c"; mkdir -p "$C/.obsidian"; printf '{bad json' > "$C/.obsidian/app.json"
python3 scripts/wiki_init.py --root "$C" >/dev/null 2>&1; [ $? = 2 ] && echo "  OK: 非法 JSON exit 2" || fail "非法 JSON 未 exit2"

echo "=== 3a-5 userIgnoreFilters 非数组 → exit 2 ==="
D="$BASE/d"; mkdir -p "$D/.obsidian"; printf '{"userIgnoreFilters":"maps/"}\n' > "$D/.obsidian/app.json"
python3 scripts/wiki_init.py --root "$D" >/dev/null 2>&1; [ $? = 2 ] && echo "  OK: 非数组 exit 2" || fail "非数组未 exit2"

echo "=== 3a-6 上下文层结构化 + 无 frontmatter + lint exit 0 ==="
E="$BASE/e"; mkdir -p "$E"
python3 scripts/wiki_init.py --root "$E" >/dev/null 2>&1 || fail "3a-6 init"
head -1 "$E/index.md" | grep -q '^---$' && fail "index 误带 frontmatter" || echo "  OK: index 无 frontmatter"
# 主题区 [[..]] 必须被反引号包裹（inline code）；裸 [[..]] 会成 dangling。断言失败要 fail（解决 review #2）
grep -qF '`[[slug|标题]]`' "$E/index.md" && echo "  OK: 主题区是 inline code" || fail "index 主题区 [[..]] 不是 inline code（会成 dangling）"
cd "$(git rev-parse --show-toplevel)" 2>/dev/null
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root "$E" --check-only >/dev/null 2>&1; [ $? = 0 ] && echo "  OK: lint exit 0" || fail "lint"

echo "=== 3b 防回归：RFC-010 既有行为内嵌实跑（解决 review #1）==="
# 内嵌实际断言（接本脚本 fail，真跑真判，不手填）。覆盖 RFC-010 5 项核心：

echo "--- R1 叠加 checksum：.obsidian/workspace.json + 笔记 init 后不变 ---"
RV="$BASE/r1"; mkdir -p "$RV/.obsidian"
printf '{"k":1}\n' > "$RV/.obsidian/workspace.json"; printf '# note\n' > "$RV/note.md"
HW=$(shasum "$RV/.obsidian/workspace.json"|cut -d' ' -f1); HN=$(shasum "$RV/note.md"|cut -d' ' -f1)
python3 scripts/wiki_init.py --root "$RV" >/dev/null 2>&1 || fail "R1 init"
[ "$HW" = "$(shasum "$RV/.obsidian/workspace.json"|cut -d' ' -f1)" ] && echo "  OK: workspace.json 不变" || fail "R1 workspace.json 被改"
[ "$HN" = "$(shasum "$RV/note.md"|cut -d' ' -f1)" ] && echo "  OK: note.md 不变" || fail "R1 note.md 被改"

echo "--- R2 幂等：第二次 created: 0 ---"
python3 scripts/wiki_init.py --root "$RV" 2>&1 | grep -qx "created: 0" && echo "  OK: created: 0" || fail "R2 非幂等"

echo "--- R3 类型冲突 → exit 2 ---"
RC="$BASE/r3"; mkdir -p "$RC"; printf 'x\n' > "$RC/wiki"
python3 scripts/wiki_init.py --root "$RC" >/dev/null 2>&1; [ $? = 2 ] && echo "  OK: 类型冲突 exit 2" || fail "R3 未 exit2"

echo "--- R4 --git：派生层 check-ignore + root∉git-root exit 2 ---"
RG="$BASE/r4"; mkdir -p "$RG/inst"
python3 scripts/wiki_init.py --root "$RG/inst" --git --git-root "$RG" >/dev/null 2>&1 || fail "R4 init --git"
for p in inst/.wiki/id_index.json inst/maps/graph-data.json inst/.obsidian/workspace.json; do
  git -C "$RG" check-ignore "$p" >/dev/null 2>&1 || fail "R4 未 ignore: $p"
done
RO="$BASE/r4out"; mkdir -p "$RO"
python3 scripts/wiki_init.py --root "$RO" --git --git-root "$RG" >/dev/null 2>&1; [ $? = 2 ] && echo "  OK: --git 派生层 ignore + root∉git-root exit 2" || fail "R4 root∉git-root 未 exit2"

echo "--- R5 profile：已有 .wiki-schema.md 不改 + 模板 6 字段 ---"
RP="$BASE/r5"; mkdir -p "$RP"; printf 'EXISTING\n' > "$RP/.wiki-schema.md"; HS=$(shasum "$RP/.wiki-schema.md"|cut -d' ' -f1)
python3 scripts/wiki_init.py --root "$RP" --profile risk >/dev/null 2>&1 || fail "R5 init"
[ "$HS" = "$(shasum "$RP/.wiki-schema.md"|cut -d' ' -f1)" ] && echo "  OK: 已有 .wiki-schema.md 不改" || fail "R5 schema 被改"
python3 -c "import json,sys;d=json.load(open('$RP/.wiki-profile.json'));need={'schema_version','profile','description','extra_page_types','extra_field_enums','extra_optional_fields'};sys.exit(0 if need<=set(d) else 1)" && echo "  OK: profile 6 字段" || fail "R5 profile 字段缺"

# 完整重跑（含 TASK-010 Step 5 全部 5a~5f）也可：executor 可额外提取 TASK-010 Step5 整段跑一遍，
# 把输出贴进 Execution log；但上面 R1~R5 已是接入 PASS 的硬断言，是本节判定依据。

echo "=== 白名单(引擎仓库只动 2 文件)==="
extra=$(git status --porcelain -uall | cut -c4- | grep -Ev '^scripts/wiki_init\.py$|^scripts/README\.md$|^wiki-design/tasks/TASK-011-apply-rfc-011\.md$')
[ -z "$extra" ] && echo "  OK: 白名单外无改动" || { echo "  FAIL:"; echo "$extra"|sed 's/^/    /'; PASS=0; }

rm -rf "$BASE"; trap - EXIT
echo "=== PASS=$PASS ==="; [ "$PASS" = 1 ] || exit 1
```

> 注意:Step 3a 的 `python3 scripts/wiki_init.py` 从仓库根跑(cwd 含 scripts/);wiki_init 内部跑自检 lint 时已 `cd engine`(TASK-010 已实现)。Step 3b 把 TASK-010 Step 5 的 5a~5f **逐字复制**重跑(它本就自包含、临时实例、trap 清理),证明 RFC-010 既有行为不退化。

### Step 4~6:commit apply / RFC Applied / task done

三 commit 拆分。apply 前 `git status` 确认只动 2 白名单 + 无临时残留。

## 完成后报告格式

`## Execution log by codex · 2026-06-01`:步骤完成情况 + Step 3 全部输出(3a-1~3a-6 + 3b 重跑 TASK-010 Step5)+ 3 commit sha + 偏离/异常。

## Spec review by codex · YYYY-MM-DD

（待 Codex 填写）

## Execution log by codex · YYYY-MM-DD

（待执行者填写）

## Evaluation by claude · YYYY-MM-DD

（待评估者填写）

## Spec review by codex · 2026-06-01

### 结论

- 需修改。
- spec 已覆盖 RFC-011 Decision 的主要实现面：只动 2 个 apply 文件、`app.json` 作为唯一 merge 例外、非法 JSON / 非数组 exit 2、上下文层仍无 frontmatter、README 同步、临时实例验证和不碰真实 vault 都写到了。
- 但还有 2 个执行级阻塞点会导致后续 apply 出现假阳性或防回归验证缺失，需要先修 spec。

### 阻塞点

1. Step 3b 仍是占位，不是可执行验证。
   - 当前 Step 3b 只输出 `>>> 逐字复制 TASK-010 Step 5 ... <<<`，没有实际跑 TASK-010 的 5a~5f。
   - 这会让 `PASS=1` 即使 RFC-010 行为回归也仍然通过，违背 RFC-011 Decision #5 “重跑 TASK-010 Step 5 全部防回归”。
   - 建议把 TASK-010 Step 5 的 5a~5f 脚本完整内联到 TASK-011 Step 3b，或给出明确可执行的抽取/执行方式，并保证输出纳入 Execution log。考虑 TASK-010 Step 5 本身是自包含 mktemp + trap，最稳妥是直接写死一份当前版本的 5a~5f，白名单改成 TASK-011 的 2 文件口径。

2. Step 3a-6 的 inline code 检查失败不会影响 PASS。
   - 当前命令是：
     `grep -q '`\[\[slug|标题\]\]`' "$E/index.md" && echo ... || echo "  (核对 index 主题区 inline code)"`
   - 如果实现忘记反引号或 grep 转义不匹配，只会打印核对提示，不会 `fail`，最终仍可能 `PASS=1`。
   - 这是 RFC-011 v1 的阻塞点之一，必须成为硬门禁。建议改成 `... || fail "index 主题区不是 inline code"`。

### 其它可执行性问题

- Step 3a-2 只断言 `u[0]=='私密/'` 和包含 `maps/` / `.wiki/`，还不能捕获追加顺序或重复项。建议按 v2 review 的非阻塞建议钉成：`u == ['私密/', 'maps/', '.wiki/']`，或至少断言 `u[:1] == ['私密/']` 且 `u.count(...) == 1` 且 `u[-2:] == ['maps/', '.wiki/']`。
- Step 3a-3 第二次 init 没有 `|| fail "3a-3 init"`，如果第二次 init 异常，后续 JSON 断言通常会失败，但错误定位不清。建议补上。
- Step 1.1 写“其它键深拷原样保留，json.dump 允许缩进/顺序变化”。这可以接受；验证也不应比较整文件 checksum。后续实现应注意不要复用原 dict 时意外 mutate 嵌套对象再写其它键，不过只改 `data['userIgnoreFilters']` 本身即可满足语义。

### 覆盖性复核

- RFC-011 Decision 7 条大体都有对应步骤：app.json union、异常 exit 2、唯一 merge 例外、上下文层模板、验证项、不碰其它系统、py312 环境均已出现。
- 边界总体正确：apply 白名单是 `scripts/wiki_init.py` 和 `scripts/README.md`；真实 `personal` / `obsidian/...` 明确不碰；RFC Applied 和 TASK 自身只在后续步骤编辑。
- 但在 Step 3b 修成真实可执行防回归前，当前 spec 不能通过。

### 最小修改建议

- 把 TASK-010 Step 5 的 5a~5f 实际脚本内联到 Step 3b，并调整白名单为 TASK-011 的 2 文件 + TASK 自身。
- 把 3a-6 inline-code grep 改成失败即 `fail`。
- 补强 3a-2 / 3a-3 的顺序、去重和第二次 init exit code 断言。

## Revision v2 by claude · 2026-06-01

addressing codex spec review v1 的 2 个阻塞点（都是"验证假通过"）。

1. **Step 3b 占位 → 内嵌实跑**（阻塞 #1）：原来只是"逐字复制 TASK-010 Step5"占位 echo，不真跑。改为**内嵌 R1~R5 实际断言**（接本脚本 fail）覆盖 RFC-010 五项核心：R1 叠加 checksum / R2 幂等 / R3 类型冲突 exit2 / R4 --git check-ignore + root∉git-root exit2 / R5 profile 不改已有 schema。真跑真判，不手填结果。
2. **3a-6 inline-code grep 失败不 fail → 改 fail**（阻塞 #2）：`grep ... || echo "(核对)"` → `grep -qF '\`[[slug|标题]]\`' || fail`，主题区不是 inline code（会成 dangling）时硬失败。

未改动：Step 1 实现约束、3a-1~3a-5、白名单。Codex Spec review v1 段保留（append-only）。

待 Codex re-review。

## Spec review v2 by codex · 2026-06-01

### 结论

- 通过。
- v2 已修复 v1 的 2 个阻塞点，Step 3 的新增断言能够机械执行；未发现新的执行级阻塞。

### v1 阻塞点复核

1. Step 3b 从占位改为内嵌实跑：已解决。
   - v2 已把防回归验证改成 R1~R5 的实际命令，并全部接入 `fail` / `PASS`。
   - R1 覆盖叠加 checksum，R2 覆盖幂等 `created: 0`，R3 覆盖类型冲突 exit 2，R4 覆盖 `--git` ignore + root∉git-root exit 2，R5 覆盖 profile 不改已有 `.wiki-schema.md` + 6 字段模板。
   - 这些断言都基于 mktemp 临时目录，不需要手填结果；失败会影响最终 `PASS`。

2. 3a-6 inline-code 断言失败会 fail：已解决。
   - v2 使用 `grep -qF '`[[slug|标题]]`' "$E/index.md" ... || fail ...`。
   - 如果主题区不是 inline code，验证会硬失败，不再 echo 假通过。

### R1~R5 可执行性复核

- R1/R2 共用同一个临时实例，能同时验证已有文件不变和重复 init 幂等。
- R3 的 `wiki` 文件冲突能触发 RFC-010 类型冲突路径。
- R4 使用临时 git root，抽样覆盖 `.wiki/id_index.json`、`maps/graph-data.json`、`.obsidian/workspace.json` 三类 ignore，并验证 root∉git-root exit 2。
- R5 验证 `.wiki-schema.md` checksum 不变和 profile 模板 6 字段，能捕获 RFC-010 profile 语义回归。

### 非阻塞提醒

- Step 3b 说明文字仍写“逐字复制 TASK-010 Step 5 全部”，但实际采用的是 R1~R5 等价核心断言，而不是逐字复制 5a~5f。当前验证足够通过；后续 Execution log 应按实际 R1~R5 输出描述，避免写成逐字复制。
- Step 3a-3 第二次 init 仍未单独 `|| fail "3a-3 init"`；后续 JSON 断言通常会捕获异常，但实现时可以顺手补强错误定位。这不是阻塞。

## Execution log by codex · 2026-06-01

### 步骤完成情况

- Step 1：完成 `scripts/wiki_init.py` app.json 安全合并与结构化上下文层模板。
- Step 2：完成 `scripts/README.md` Obsidian 友好初始化说明。
- Step 3：全量验证通过，`PASS=1`。
- Step 4 commit：`fba1428`
- Step 5 commit：`e8ae933`
- Step 6 commit：本段提交后生成。

### Step 3 验证输出

```text
=== 3a-1 app.json 不存在 → 创建含两项 ===
  OK: app.json 含 maps/ + .wiki/
=== 3a-2 已有 app.json(用户键 + 已有过滤项) → 保留 + 追加 ===
  OK: 用户键保留 + 已有过滤项顺序保留 + 追加 maps/.wiki
=== 3a-3 幂等:第二次不重复加 ===
  OK: union 去重(各 1 次)
=== 3a-4 非法 JSON → exit 2 ===
  OK: 非法 JSON exit 2
=== 3a-5 userIgnoreFilters 非数组 → exit 2 ===
  OK: 非数组 exit 2
=== 3a-6 上下文层结构化 + 无 frontmatter + lint exit 0 ===
  OK: index 无 frontmatter
  OK: 主题区是 inline code
  OK: lint exit 0
=== 3b 防回归：RFC-010 既有行为内嵌实跑（解决 review #1）===
--- R1 叠加 checksum：.obsidian/workspace.json + 笔记 init 后不变 ---
  OK: workspace.json 不变
  OK: note.md 不变
--- R2 幂等：第二次 created: 0 ---
  OK: created: 0
--- R3 类型冲突 → exit 2 ---
  OK: 类型冲突 exit 2
--- R4 --git：派生层 check-ignore + root∉git-root exit 2 ---
  OK: --git 派生层 ignore + root∉git-root exit 2
--- R5 profile：已有 .wiki-schema.md 不改 + 模板 6 字段 ---
  OK: 已有 .wiki-schema.md 不改
  OK: profile 6 字段
=== 白名单(引擎仓库只动 2 文件)===
  OK: 白名单外无改动
=== PASS=1 ===
```

### 偏离 / 异常

- 无验证异常。
- Step 3b 按 spec v2 的 R1~R5 硬断言执行并记录输出；未额外逐字复制 TASK-010 5a~5f 全段。
- 全部验证均在 `mktemp` 临时实例执行，trap 清理；未触碰用户真实 vault 或 `knowledge/` / `personal` 实例。
