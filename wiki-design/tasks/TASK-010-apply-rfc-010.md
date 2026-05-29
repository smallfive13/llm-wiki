---
id: task_20260529_010
title: Apply RFC-010 — 实现 wiki_init.py 脚手架
author: claude
executor: codex
status: pending
type: apply
created: 2026-05-29
updated: 2026-05-29
related_rfcs:
  - rfc_20260529_010
---

# TASK-010: Apply RFC-010 — 实现 wiki_init.py

## 目标

落地 `scripts/wiki_init.py`：把任意目录(含外部 Obsidian vault)初始化为合法 wiki 实例,叠加安全、git 可选。执行完成后可用它 init 用户的 `personal` vault。

## 前置条件

- 仓库根:`/Users/zhangjunwu/workspace/llm-wiki/llm-wiki`
- HEAD 含 **RFC-010 status: accepted**（commit `dfd8f94` 及之后）
- working tree clean
- 已读 RFC-010 全文(含 Decision 9 条约束 + v1/v2 review)
- 已读 `scripts/wiki_lint.py` 的 `_repo_root` / `_instance_root` / `configure`(理解 --root 解析)、`knowledge/.wiki-schema.md`(拷贝源)
- conda `py312` + PyYAML

## 强约束

1. **只动以下路径**:
   - `scripts/wiki_init.py`(新建)
   - `scripts/README.md`(追加 wiki init 段)
   - `wiki-design/02-workflows.md`(加实例初始化 workflow)
2. 本 TASK-010 文件按 Step 0 / 末步编辑;RFC-010 按倒数第二步追加 Applied。
3. **不动** `wiki_lint.py` / `wiki_graph.py` / `wiki_common.py` / `BASE_SCHEMA`、AGENTS.md、引擎仓库 `.gitignore`、现有 `knowledge/`、其它 RFC/task。
4. 必须先经 Codex spec review(Step 0)。
5. PyYAML 唯一外部依赖;preflight 必跑(conda py312)。
6. 严格按 RFC-010 Decision 9 条约束,**不**自行扩展。
7. **wiki_init.py 绝不覆盖已存在文件**(叠加安全):同类型已存在→跳过;类型冲突→exit 2;不静默覆盖。
8. **验证(Step 5)在临时实例做,建在 knowledge/ 外,trap 清理**;**绝不动用户真实 vault**(`obsidian/...`)——init personal 是 Step 6 由用户/evaluator 在 evaluate 后手动跑,不在本 task。
9. commit 拆三个:apply 改动 / RFC-010 Applied / task done。

## 工作流

```
Step 0  Codex spec review + commit
        ▼
Step 1  实现 scripts/wiki_init.py
        ▼
Step 2  scripts/README.md 追加 wiki init 段
        ▼
Step 3  wiki-design/02-workflows.md 加实例初始化 workflow
        ▼
Step 4  preflight + 基本冒烟(临时空实例 init → lint --check-only exit 0)
        ▼
Step 5  自检验证(临时实例,trap 清理):叠加 checksum / 类型冲突 / 幂等 /
        --git check-ignore / root∉git-root / profile skip
        ▼
Step 6  commit apply [apply rfc-010]
Step 7  RFC-010 追加 ## Applied in <Step6 sha> + commit [rfc-010]
Step 8  task done + Execution log + commit [task]
        ▼
       （done 后:用户/evaluator 手动 init personal vault,不在本 task commit 内）
```

## 步骤

### Step 0：Spec review

末尾追加 `## Spec review by codex · 2026-05-29`,检查:完整性(9 约束覆盖)/ 可执行性(骨架生成 + 叠加 + git + 自检机械可跑)/ 边界(只动 3 路径,不碰用户 vault)/ 风险。commit `[task] TASK-010 spec review by codex (conclusion: <...>)`。

### Step 1：实现 `scripts/wiki_init.py`

按 RFC-010 提案 #1~#4 实现:

#### 1.1 基本约束
- Shebang `#!/usr/bin/env python3`,Python 3.12,标准库 + PyYAML(实际 init 不一定需 yaml,但 preflight 统一)
- 约 250~400 行,UTF-8 显式
- 可从任意 cwd 跑(不强制 repo 根——init 是建实例,不依赖引擎 repo 结构;但拷 `.wiki-schema.md` 模板需定位引擎,见 1.3)

#### 1.2 CLI
```
python3 scripts/wiki_init.py --root <path> [--profile NAME] [--git] [--git-root <path>]
```
退出码:`0` 成功 / `2` 配置错误(类型冲突 / root∉git-root / git 失败 / 自检失败)。

#### 1.3 建骨架(复刻 knowledge/,叠加跳过)
- 14 个 `.gitkeep` 空目录(RFC-010 #1 清单)
- 4 个上下文层占位 md(**通用占位,绝不拷 llm-wiki meta**):
  - `purpose.md`:`# Purpose\n\n> <实例名> 知识库目的(占位,待填)。`
  - `index.md` / `overview.md`:空占位标题
  - `log.md`:`# Log\n\n## <date> · Initialized\n\nInitialized by wiki_init (engine: llm-wiki, profile: <NAME 或 base>)。`
- `.wiki-schema.md`:**仅不存在时**从引擎 `<engine_repo>/knowledge/.wiki-schema.md` 拷贝(引擎定位:脚本自身路径 `Path(__file__).resolve().parent.parent`);已存在跳过
- 3 JSON(仅不存在时,完整内容见 RFC-010 #1,capture_policy `updated_at` 用当前 ISO 8601)

#### 1.4 叠加安全(RFC-010 #1a)
- 应建文件处已是文件 / 应建目录处已是目录 → 跳过(计 skip)
- 类型冲突(应建目录处是文件 / 应建文件处是目录)→ **exit 2** + 打印冲突路径
- 幂等:重复跑 新建数=0

#### 1.5 --profile(RFC-010 #1a)
- 仅 `.wiki-profile.json` 不存在时写最小模板(`schema_version/profile/description/extra_*`)
- `.wiki-schema.md` 已存在时不追加摘要,报告输出 `profile summary skipped: .wiki-schema.md exists`

#### 1.6 --git(RFC-010 #3)
- 强校验:`root` 必须 == 或位于 `git_root`(缺省 `root`)下;否则 **exit 2** + 打印两路径
- `git_root` 非 repo 则 `subprocess git init`;打印 `git rev-parse --show-toplevel`
- 写/追加 `.gitignore`(RFC-010 #3 全 12 行,逐行检查存在性,幂等)
- git subprocess 失败 graceful 报错(exit 2),不留半初始化

#### 1.7 自检(RFC-010 #4)
- init 末尾跑 `wiki_lint.py --root <实例> --check-only`(subprocess,引擎路径定位同 1.3);exit≠0 则报告 + 本脚本 exit 2
- 报告:新建 N / 跳过 M / git repo 路径 / 自检结果

### Step 2~3：文档
- `scripts/README.md`:wiki init 段(用法 + 选项表 + 叠加语义 + git + 自检)
- `wiki-design/02-workflows.md`:「实例初始化」workflow 段(`wiki_init.py` 命令 + 多实例说明)

### Step 4：preflight + 冒烟
```bash
conda activate py312
python -c "import yaml" || pip install pyyaml
# 冒烟:临时空目录 init → 自检 exit 0
T=$(mktemp -d)
python3 scripts/wiki_init.py --root "$T"; echo "init exit: $?"
python3 scripts/wiki_lint.py --root "$T" --check-only >/dev/null 2>&1; echo "lint exit: $? (期望 0)"
rm -rf "$T"
```

### Step 5：自检验证(临时实例,knowledge/ 外,trap 清理)

```bash
conda activate py312; set +e
PASS=1; fail(){ echo "  FAIL: $1"; PASS=0; }
BASE=$(mktemp -d); trap 'rm -rf "$BASE"' EXIT

echo "=== 5a 叠加安全:预置已有文件 init 后 checksum 不变 ==="
V="$BASE/vault"; mkdir -p "$V/.obsidian"
printf '{"x":1}\n' > "$V/.obsidian/workspace.json"
printf '# 欢迎\n' > "$V/欢迎.md"
H1=$(shasum "$V/.obsidian/workspace.json" | cut -d' ' -f1)
H2=$(shasum "$V/欢迎.md" | cut -d' ' -f1)
python3 scripts/wiki_init.py --root "$V" >/dev/null 2>&1; echo "  init exit: $?"
[ "$H1" = "$(shasum "$V/.obsidian/workspace.json" | cut -d' ' -f1)" ] && echo "  OK: workspace.json 未变" || fail "workspace.json 被改"
[ "$H2" = "$(shasum "$V/欢迎.md" | cut -d' ' -f1)" ] && echo "  OK: 欢迎.md 未变" || fail "欢迎.md 被改"
[ -f "$V/.wiki/capture_policy.json" ] && echo "  OK: 骨架已叠加" || fail "骨架没建"

echo "=== 5b 幂等:第二次 init 新建数 0 ==="
OUT=$(python3 scripts/wiki_init.py --root "$V" 2>&1)
echo "$OUT" | grep -qE "新建 0|created 0|新建.*0 " && echo "  OK: 第二次新建 0" || echo "  (核对报告新建数: $(echo "$OUT" | grep -iE '新建|created'))"

echo "=== 5c 类型冲突 exit 2 ==="
C="$BASE/conflict"; mkdir -p "$C"
printf 'x\n' > "$C/wiki"   # 应建目录 wiki/ 处放了文件
python3 scripts/wiki_init.py --root "$C" >/dev/null 2>&1; [ $? = 2 ] && echo "  OK: 类型冲突 exit 2" || fail "类型冲突未 exit 2"

echo "=== 5d --git: check-ignore 派生层 + root∉git-root exit2 ==="
G="$BASE/repo"; mkdir -p "$G/personal"
python3 scripts/wiki_init.py --root "$G/personal" --git --git-root "$G" >/dev/null 2>&1; echo "  init --git exit: $?"
for p in personal/.wiki/id_index.json personal/.wiki/search_index/ personal/.wiki/lightrag/ personal/maps/graph-data.json; do
  git -C "$G" check-ignore "$p" >/dev/null 2>&1 && echo "  OK ignore: $p" || fail "未 ignore: $p"
done
# root 不在 git-root 下 → exit 2
OUT_DIR="$BASE/outside"; mkdir -p "$OUT_DIR"
python3 scripts/wiki_init.py --root "$OUT_DIR" --git --git-root "$G" >/dev/null 2>&1; [ $? = 2 ] && echo "  OK: root∉git-root exit 2" || fail "root∉git-root 未 exit 2"

echo "=== 5e profile: 已有 .wiki-schema.md 时不改 + .wiki-profile.json 仅不存在时建 ==="
P="$BASE/pf"; mkdir -p "$P"; printf 'EXISTING\n' > "$P/.wiki-schema.md"
HS=$(shasum "$P/.wiki-schema.md" | cut -d' ' -f1)
python3 scripts/wiki_init.py --root "$P" --profile risk >/dev/null 2>&1
[ "$HS" = "$(shasum "$P/.wiki-schema.md" | cut -d' ' -f1)" ] && echo "  OK: 已有 .wiki-schema.md 未改" || fail ".wiki-schema.md 被改"
[ -f "$P/.wiki-profile.json" ] && python3 -c "import json;d=json.load(open('$P/.wiki-profile.json'));assert d['profile']=='risk'" && echo "  OK: profile 模板已建" || fail "profile 模板"

echo "=== 5f 白名单(引擎仓库只动 3 路径)==="
extra=$(git status --porcelain -uall | cut -c4- | grep -Ev '^scripts/wiki_init\.py$|^scripts/README\.md$|^wiki-design/02-workflows\.md$|^wiki-design/tasks/TASK-010-apply-rfc-010\.md$')
[ -z "$extra" ] && echo "  OK: 白名单外无改动" || { echo "  FAIL:"; echo "$extra"|sed 's/^/    /'; PASS=0; }

rm -rf "$BASE"; trap - EXIT
echo "=== PASS=$PASS ==="; [ "$PASS" = 1 ] || exit 1
```

预期:5a checksum 不变 + 骨架叠加;5b 幂等;5c 类型冲突 exit2;5d 派生层全 ignore + root∉git-root exit2;5e profile 不改已有 schema;5f 白名单干净。

### Step 6~8：commit apply / RFC Applied / task done

三 commit 拆分。apply 前 `git status` 确认只动 3 白名单 + 无临时残留。

> **Step 6 之后(不在本 task commit)**:evaluate PASS 后,由用户/Claude 手动跑 init personal:
> `python3 scripts/wiki_init.py --root /Users/zhangjunwu/workspace/obsidian/knowledge/personal --git --git-root /Users/zhangjunwu/workspace/obsidian/knowledge --profile personal`

## 完成后报告格式

`## Execution log by codex · 2026-05-29`:步骤完成情况 + Step 4 冒烟 + Step 5 全部输出(5a~5f)+ 3 commit sha + 偏离/异常。

## Spec review by codex · YYYY-MM-DD

（待 Codex 填写）

## Execution log by codex · YYYY-MM-DD

（待执行者填写）

## Evaluation by claude · YYYY-MM-DD

（待评估者填写）

## Spec review by codex · 2026-05-29

### 结论

- 需修改。
- spec 已覆盖 RFC-010 Decision 的主体路径：3 个 apply target、叠加安全、profile、git-root 校验、完整 `capture_policy`、临时 fixture、不碰用户 vault、三 commit 拆分都在。引擎路径用 `Path(__file__).resolve().parent.parent` 定位脚本所在仓库，作为拷贝 `.wiki-schema.md` 的来源是可靠的。
- 但还有 3 个执行级阻塞点会导致后续 apply 出现假阳性或任意 cwd 运行失败，需要先修 spec。

### 阻塞点

1. `wiki_lint.py` subprocess 必须显式 `cwd=<engine_repo>`。
   - TASK 1.1 要求 `wiki_init.py` 可从任意 cwd 跑；1.7 又要求 init 末尾 subprocess 跑 `wiki_lint.py --root <实例> --check-only`。
   - 当前 `wiki_lint.py` 的 `_repo_root()` 是 `Path.cwd()`，且要求 cwd 下存在 `scripts/`。所以如果 `wiki_init.py` 从外部 cwd 运行，只用脚本绝对路径调用 `wiki_lint.py` 仍会失败。
   - 建议在 1.7 钉死调用方式：`subprocess.run([sys.executable, str(engine_repo / "scripts/wiki_lint.py"), "--root", str(root), "--check-only"], cwd=engine_repo, ...)`。Step 5/Step 4 也应增加一个“从非 repo cwd 调用 wiki_init.py 仍成功”的 fixture，否则这个约束测不到。

2. Step 5b 幂等检查不会影响 PASS。
   - 现在 `grep` 到“新建 0”时打印 OK；否则只打印“核对报告新建数”，没有 `fail`，最终 `PASS` 仍可能是 1。
   - 这正好是 RFC-010 的核心安全约束之一，必须成为硬门禁。
   - 建议要求 `wiki_init.py` 输出稳定、可解析的计数行，例如 `created: N` / `skipped: M` / `conflicts: K`，然后 Step 5b 断言 `created: 0`，失败时 `fail "第二次 init 新建数非 0"`。只靠多语言 grep 报告不稳。

3. Step 5d 没有验证 `.gitignore` 全部锁定规则。
   - Decision #4 要求派生层全集 + `.obsidian/workspace*.json`。当前只 `git check-ignore` 了 4 个路径：`id_index`、`search_index/`、`lightrag/`、`graph-data.json`。
   - 这不能捕获漏写 `inbox_index.json`、`normalized_alias_index.json`、`cache.json`、`maps/knowledge-graph.md`、`maps/graph-insights.md`、`.obsidian/workspace.json`、`.obsidian/workspace-mobile.json` 的实现错误。
   - 建议 Step 5d 遍历 RFC-010 模板中的所有非注释规则对应样例路径，或直接 `grep -Fx` 检查 `.gitignore` 必须包含完整规则清单，再配合 `git check-ignore` 抽样。

### 其它可执行性问题

- Step 4 冒烟只 `echo` exit code，不把 init/lint 非 0 接入 PASS 或 exit。虽然 Step 5 会覆盖大部分路径，但 smoke 作为 gate 应显式失败。
- Step 5a、5d、5e 中 `wiki_init.py` exit code 也多处只打印不校验。建议所有期望成功的 init 调用都写成 `python3 ... || fail "..."`。
- 5e 只校验 `.wiki-profile.json` 的 `profile` 字段，建议顺手断言最小模板的 6 个顶层字段都存在，避免实现少字段但 lint 仍未被该分支清晰定位。

### 边界与风险判断

- 不碰用户真实 `personal` vault、全部验证在 `mktemp` 且 trap 清理，这个边界正确。
- 白名单只允许 `scripts/wiki_init.py`、`scripts/README.md`、`wiki-design/02-workflows.md` 和 TASK 自身，方向正确；Step 7 追加 RFC Applied 不在 Step 5 apply 白名单内也合理。
- git subprocess 失败处理已在 1.6 提到，但 spec 还应明确失败时允许已创建骨架保留还是要回滚；至少不要承诺“完全不留半初始化”而没有可验证 rollback 机制。建议表述为“git 失败 exit 2，不写临时文件；已按叠加语义创建的骨架不回滚，并在报告中说明”。

### 最小修改建议

- 1.7 明确 `wiki_lint.py` subprocess `cwd=engine_repo`，并在 Step 5 增加非 repo cwd 调用 fixture。
- 规定 `wiki_init.py` 输出稳定计数格式；Step 5b 失败时必须 `fail`。
- Step 5d 覆盖完整 `.gitignore` 规则清单，至少包含 `.obsidian/workspace*.json` 和所有 `.wiki` / `maps` 派生层。
- 所有期望成功的 init/smoke 调用都接入 PASS gate。
