---
id: task_20260601_011
title: Apply RFC-011 — wiki_init Obsidian 友好增强
author: claude
executor: codex
status: pending
type: apply
created: 2026-06-01
updated: 2026-06-01
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
grep -q '`\[\[slug|标题\]\]`' "$E/index.md" && echo "  OK: 主题区是 inline code" || echo "  (核对 index 主题区 inline code)"
cd "$(git rev-parse --show-toplevel)" 2>/dev/null
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root "$E" --check-only >/dev/null 2>&1; [ $? = 0 ] && echo "  OK: lint exit 0" || fail "lint"

echo "=== 3b 重跑 TASK-010 Step 5 防回归 ==="
echo "  >>> 逐字复制 TASK-010 Step 5（5a~5f）在此重跑;任一 FAIL = RFC-010 行为回归 = 本 task 失败 <<<"

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
