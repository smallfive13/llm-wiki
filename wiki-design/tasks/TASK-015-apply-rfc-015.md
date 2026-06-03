---
id: task_20260603_015
title: Apply RFC-015 — .wiki-schema.md 分发鲁棒性（断链修复 + 写入规则 + --sync-schema）
author: claude
executor: codex
status: done
type: apply
created: 2026-06-03
updated: 2026-06-03
related_rfcs: [RFC-015]
---

# TASK-015: Apply RFC-015 — .wiki-schema.md 分发鲁棒性

## 目标

修 `.wiki-schema.md`（wiki_init 复制给实例的镜像文档）的两个缺陷：① 外部实例里 `../wiki-design/`、`../AGENTS.md` 相对链接断裂；② 写入规则 crystallize/capture 措辞张力。并加 `wiki_init --sync-schema` 把更新后的源头同步到已有实例。

## 前置条件

- RFC-015 status: accepted（Decision by claude 2026-06-03）。
- working tree clean（除本 task 文件）。
- 环境：`conda run -n py312 python`。

## 强约束

1. **只动镜像文档 + wiki_init**：`knowledge/.wiki-schema.md`（源头）+ `scripts/wiki_init.py`（加 `--sync-schema`）+ `scripts/README.md`。不改 core schema 语义、frontmatter 契约、8 类页面、ID/canonical 规则。
2. **不改 lint/graph/eval 行为与退出码**；不改 `wiki_init` 既有 init 路径行为。
3. **`--sync-schema` 是 early-return 独立模式**：绝不串入 skeleton / app.json 合并 / gitignore / 目录创建 / selfcheck。
4. **零数据正本改动**：knowledge 数据正本（wiki 页）不动；`.wiki-schema.md` 是镜像文档可改。
5. **外部实例同步另算**：personal/datawarehouse 的 `.wiki-schema.md` 同步在各自数据仓提交，**不混进本引擎 apply commit**。

## 步骤

> Step 0 spec-review：核对 `wiki_init.py` 主流程（`create_skeleton` / app.json 合并 / gitignore / selfcheck 的调用点），确认 `--sync-schema` 能在参数解析后 early-return、不触达这些；发现歧义先提。

1. **源头 `knowledge/.wiki-schema.md` — 断链修复（RFC 修复 1）**：
   - line 3 的 `[..](../wiki-design/01-architecture.md)` / `../wiki-design/05-...` 和写入规则段末的 `[../AGENTS.md](../AGENTS.md)` / `[../wiki-design/04-agent-rules.md](..)` 全部去掉相对链接，替换成 RFC 修复 1 的**无链接文字块**（"到当前 llm-wiki 引擎仓查找 AGENTS.md / wiki-design/01·05·04 + 引擎仓路径来源说明"）。
   - 验证：`grep '](\.\./' knowledge/.wiki-schema.md` 输出为空。

2. **源头 `knowledge/.wiki-schema.md` — 写入规则段重写（RFC 修复 2）**：按三态（普通对话 / crystallize 直接写正本 / capture 进 inbox + 触发词）重写；"严禁绕过 inbox" 限定为仅约束 capture 路径。

3. **`scripts/wiki_init.py` — 新增 `--sync-schema`（RFC 修复 3）**：
   - 参数解析后 **early-return 分支**：只要求 `--root`；root 不存在或非目录 → `exit 2`；与 `--profile`/`--git`/`--git-root` 同时出现 → `exit 2`（互斥）。
   - 源 = `engine/knowledge/.wiki-schema.md`；目标 = `<root>/.wiki-schema.md`；若目标是目录 → `exit 2`。
   - 计算 `old_sha256`（目标不存在则 null）/ `new_sha256`；内容一致 → **不写、不更新 mtime**，`action: unchanged`；目标缺失 → 写，`action: created`；不同 → 覆盖写，`action: replaced`。
   - 输出 `old_sha256` / `new_sha256` / `action`。**只写这一个文件**，不调 `create_skeleton()`、不合并 app.json、不写 .gitignore、不创建目录、不跑 selfcheck。

4. **`scripts/README.md`**：补 `--sync-schema` 用法、互斥规则、输出字段、退出码。

5. **测试**（标准库 unittest，沿用既有风格，直接调 wiki_init 的 sync 入口）：
   - `action: replaced`（目标旧内容 → 更新为源头）；
   - `action: created`（目标缺失 → 写入）；
   - **`action: unchanged`（目标已与源一致 → 不写、mtime 不变）**（Codex re-review 非阻塞建议；用写前/写后 `os.stat().st_mtime_ns` 断言相等）；
   - `exit 2` 场景：`--sync-schema` 同时带 `--profile`/`--git`/`--git-root`、root 不存在、root 非目录、`<root>/.wiki-schema.md` 是目录；
   - **隔离**：构造一个含其它文件的临时实例，`--sync-schema` 后断言除 `.wiki-schema.md` 外所有文件 mtime/内容不变。
   - 新建实例无断链：`wiki_init --root <tmp>` 后 `grep '](\.\./' <tmp>/.wiki-schema.md` 为空。

6. **跑验证（见下）→ commit**（引擎改动一个 commit；最终 working tree clean）。

7. **落地同步（引擎 commit 之后，单独执行，不进引擎 commit）**：
   - `wiki_init --sync-schema --root <personal>` 和 `--root <datawarehouse>`，把更新后 `.wiki-schema.md` 同步过去；
   - 在数据仓 `obsidian/knowledge` 提交（单独 commit），报告其 git 状态；
   - 同步后两库 `wiki_lint` 仍 exit 0。

## 验证

```bash
ENGINE=/Users/zhangjunwu/workspace/llm-wiki/llm-wiki
PY="/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python"

# 1) 单测全绿
cd $ENGINE && $PY -m unittest -v tests.test_task_015

# 2) 源头无断链
grep '](\.\./' knowledge/.wiki-schema.md && echo "FAIL 仍有断链" || echo "OK 无 ../ 链接"

# 3) sync-schema 互斥与退出码
$PY scripts/wiki_init.py --sync-schema --root /tmp/nonexist; echo "root 不存在 exit=$?"   # 期望 2
$PY scripts/wiki_init.py --sync-schema --git --root /tmp/x; echo "组合 --git exit=$?"     # 期望 2

# 4) 新建实例无断链
$PY scripts/wiki_init.py --root /tmp/dw_test && grep '](\.\./' /tmp/dw_test/.wiki-schema.md && echo FAIL || echo "OK 新实例无断链"

# 5) 既有套件不回归
cd $ENGINE && $PY -m unittest -v tests.test_task_012 tests.test_task_013 tests.test_task_014

# 6)（引擎 commit 后，单独）同步真实实例
$PY scripts/wiki_init.py --sync-schema --root /Users/zhangjunwu/workspace/obsidian/knowledge/personal
$PY scripts/wiki_init.py --sync-schema --root /Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse
```

## 完成后报告格式

- Step 0 spec-review 结论（含歧义/偏离）
- 改动文件 + 关键位置（断链替换、写入规则段、`--sync-schema` early-return 落点）
- 验证 1~5 输出（单测、无断链、互斥退出码、隔离证据）
- 落地同步（步骤 7）：sync 输出 action、数据仓 commit sha、外部实例 git 状态
- commit sha（引擎 apply 与数据仓同步分开）
- 偏离或异常

## Execution log by codex · 2026-06-03

### Step 0 spec-review

结论：通过，可以执行。

- `wiki_init.py` 主流程在 `main()` 中依次进入 `create_root -> create_skeleton -> ensure_obsidian_app -> ensure_git -> run_selfcheck`。
- `--sync-schema` 必须放在参数解析、`engine_repo()` / `resolve_from_engine()` 之后，并在 `create_root()` 之前 early-return，才能保证不触达 skeleton、app.json、gitignore、目录创建和 selfcheck。
- 无歧义或偏离需要先提。

### 改动文件与关键位置

- `knowledge/.wiki-schema.md`：顶部去掉 `../wiki-design` 相对链接，改成"当前 llm-wiki 引擎仓 + 文件清单 + 引擎路径来源"文字块；`## 写入规则` 改为普通对话 / crystallize / capture 三态，明确"严禁绕过 inbox"只约束 capture 路径。
- `scripts/wiki_init.py`：新增 `sha256_file()` / `write_sync_report()` / `sync_schema()`；`build_parser()` 增加 `--sync-schema`；`main()` 在既有 init 主流程前新增 early-return 分支，并禁止与 `--profile` / `--git` / `--git-root` 组合。
- `scripts/README.md`：补 `--sync-schema` 用法、互斥规则、报告字段和退出码语义。
- `tests/test_task_015.py`：新增 sync-schema CLI 测试。

### 验证 1~5 输出

```text
# 1) 单测全绿
test_new_instance_schema_has_no_parent_links ... ok
test_sync_schema_creates_missing_file ... ok
test_sync_schema_only_changes_schema_file ... ok
test_sync_schema_rejects_conflicting_options ... ok
test_sync_schema_rejects_invalid_roots_and_directory_target ... ok
test_sync_schema_replaces_existing_file ... ok
test_sync_schema_unchanged_does_not_touch_mtime ... ok

Ran 7 tests in 2.208s
OK
```

```text
# 2) 源头无断链
OK 无 ../ 链接
```

```text
# 3) sync-schema 互斥与退出码
config error: --sync-schema root must exist and be a directory: /private/tmp/nonexist-task015
root 不存在 exit=2

config error: --sync-schema cannot be combined with --profile/--git/--git-root
组合 --git exit=2
```

```text
# 4) 新建实例无断链
created: 39
skipped: 0
conflicts: 0
git_root: none
selfcheck: ok
obsidian: created

OK 新实例无断链
```

```text
# 5) 既有套件不回归
Ran 20 tests in 1.666s
OK
```

### 落地同步（Step 7）

```text
# personal sync
old_sha256: 0ace5bd83ea6512ddb0c9dfc67e83b573337784af547f580a24c1c78fe9bf39e
new_sha256: 6f416bebba5085a1dd1dba264a46bd0cdbc094ce8b4a7c04e1bc2d6834203ea9
action: replaced

# datawarehouse sync
old_sha256: e6b7f93328576e8d7f3c1e2ec63b6419e17905ee9155ed364941ff93207a6320
new_sha256: 6f416bebba5085a1dd1dba264a46bd0cdbc094ce8b4a7c04e1bc2d6834203ea9
action: replaced
```

同步后 lint：

```text
personal: 错误: 0 · 警告: 0
datawarehouse: 错误: 0 · 警告: 0
```

外部数据仓 `/Users/zhangjunwu/workspace/obsidian/knowledge`：

- 同步前 git status：clean，branch `main`。
- 只修改 `personal/.wiki-schema.md` 和 `datawarehouse/.wiki-schema.md`。
- 外部数据仓 commit：`3877285fcd26593e31f493256ce784e7046a46a8` (`[sync schema] refresh llm-wiki schema mirrors`)。
- 同步后 git status：clean。

### Commit

- 引擎 apply commit：`a836db43eed9074be8cc1c8fd10e654c4f7ba1e6`
- 外部数据仓同步 commit：`3877285fcd26593e31f493256ce784e7046a46a8`

### 偏离或异常

- 验证里 `conda run` 包装非零退出命令时会额外输出 `ERROR conda.cli.main_run...`，但脚本实际 exit code 分别为 2，符合 spec。

## Evaluation by claude · 2026-06-03

**Verdict: PASS。** 独立复跑全部验证；断链根除、三实例镜像统一、零回归、改动范围合规。

### 独立复跑

| 验证 | 结果 |
| --- | --- |
| `unittest tests.test_task_015` | 7 tests OK（created/replaced/unchanged-不改mtime/exit2 互斥/无效root/隔离/新实例无断链） |
| 断链 `grep '](\.\./'` | engine 源头 / personal / datawarehouse **全 0** |
| 三份 `.wiki-schema.md` SHA | **完全一致**（源头 + 两库同步后统一） |
| `--sync-schema` exit 2 | root 不存在 → exit 2 ✓ |
| 回归 012/013/014 | 20 tests OK |

### 核查点

1. **断链根除（RFC 修复 1）**：源头 + 两个外部实例 `.wiki-schema.md` 均无 `../` 相对链接；新建实例也无断链（单测 `test_new_instance_schema_has_no_parent_links`）。
2. **分发统一**：三个实例的 `.wiki-schema.md` 现在 SHA 完全一致——`--sync-schema` 把 personal（旧版）和 datawarehouse 都拉齐到源头最新，**分发 drift 问题实证解决**。
3. **`--sync-schema` early-return + 安全（RFC 修复 3）**：7 单测覆盖 created/replaced/unchanged（mtime 不变）/互斥 exit2/无效 root/target 目录/隔离（除该文件外无变化）。
4. **改动范围合规**：引擎 commit 仅 `.wiki-schema.md`+`wiki_init.py`+README+tests，未碰 lint/graph/eval、未改既有 init 路径；外部同步 `3877285` 仅 2 个镜像、在数据仓单独提交，**未混进引擎 apply**（符合强约束 5）。
5. **同步后两库 lint 0/0**：`.wiki-schema.md` 更新不破坏校验。

### 偏离评估（合理）

- `conda run` 包装非零退出时输出 `ERROR conda.cli...` stderr：预期噪音，实际 exit code 为 2，符合 spec。接受。

### 结论

RFC-015 闭环达成。这一轮是个完整的 **dogfood 闭环**：新 agent 上手数仓库 → 发现 `.wiki-schema.md` 断链 + 措辞张力 → RFC-015 → 修复 + `--sync-schema` 拉齐三实例。"工具/分发鲁棒性三连"（RFC-013 解析 / 014 量化 / 015 分发）收尾。TASK-015 done 确认有效。
