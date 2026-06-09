---
id: rfc_20260609_022
title: wiki CLI 薄 wrapper（统一入口，消除 conda / cwd / 路径摩擦）
author: claude
status: proposed
created: 2026-06-09
updated: 2026-06-09
targets:
  - bin/wiki
  - scripts/README.md
  - wiki-design/02-workflows.md
  - skill/wiki/SKILL.md
reviewers:
  - codex
  - user
---

# RFC-022: wiki CLI 薄 wrapper

## 背景

REVIEW-001 小点2：全链路调用脚本的摩擦很高，每条命令都是

```
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root <abs> --check-only
```

——又长、又要先 `cd` 到引擎根（`wiki_lint:162` / `wiki_graph:50` 有 `must run from repo root containing scripts/` 硬检查），还要记完整 conda 路径。`skill/wiki/` 至今靠硬编码 python 全路径绕开，`02-workflows.md` 里也一直挂着"未来 `wiki` CLI"的占位。

这不是空库投机，是每天真实发生的操作摩擦（见"真实摩擦来源"）。一个薄 wrapper 能把它压成 `wiki lint --root <x>`。

## 提案

新增引擎仓 `bin/wiki`——一个**薄**可执行包装脚本（无新依赖、不改任何现有脚本逻辑），把 4 个子命令转发到对应脚本：

| 子命令 | 转发到 |
| --- | --- |
| `wiki lint [args]` | `scripts/wiki_lint.py` |
| `wiki graph [args]` | `scripts/wiki_graph.py` |
| `wiki eval [args]` | `scripts/wiki_eval.py` |
| `wiki init [args]` | `scripts/wiki_init.py` |

设计要点：

1. **自动定位引擎根 + cd**：wrapper 用自身路径推出引擎根（`dirname $0/..`），执行前 `cd` 到引擎根，消除 `must run from repo root` 摩擦——用户可在任意 cwd 跑 `wiki lint --root <x>`。
2. **python 解释器解析顺序**（避免硬编码用户机器路径、又能在用户 zsh 下工作）：
   - `$WIKI_PY`（用户一次性导出完整命令，如 `export WIKI_PY="/Users/.../conda run -n py312 python"`）→
   - 引擎根 `.wiki-cli.conf` 里的 `python=` 行（可选，进 `.gitignore`，每机器配置）→
   - `conda run -n py312 python`（若 `conda` 在 PATH）→
   - `python3`（兜底）。
   解析到的解释器只用于 `exec` 对应脚本。
3. **全透传**：子命令之后的所有参数原样传给脚本（`--root` / `--check-only` / `--check-docs` / `--ingest-status` / `--scan-wiki-pii` / `--sync-schema` / `--force` 等无需 wrapper 感知）。**退出码原样透传**。
4. **不改脚本默认**：`--root` 缺省仍由各脚本决定（`knowledge`）；wrapper 不注入默认。
5. **薄**：wrapper 只做"定位根 + 解析解释器 + cd + exec"，**零业务逻辑**；新增子命令时只加一行映射。

形态建议 POSIX shell（`bin/wiki`，`chmod +x`，无 import 启动开销）；具体语言留 Step 0 / 替代方案权衡。

## 真实摩擦来源

机制类，证据具体：

- 本会话内几乎每条工具调用都得写整段 `/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_*.py --root <abs>`；多次因 cwd 不在引擎根触发 `must run from repo root`（本会话 personal 复核时刚踩过）。
- codex 多次踩 zsh `$PY` 变量 word-split 导致 `exit 127`（记录在多个 Task 偏离里），正是因为没有稳定入口、只能拼长命令。
- `skill/wiki/` 不得不硬编码 python 全路径；REVIEW-001 小点2 已点名。

## 验证方式

机制类，apply 后须验证：

- **等价性**：`wiki lint --root <x>` / `graph` / `eval` / `init` 的 stdout 与退出码，与直接 `python scripts/wiki_*.py ...` **逐项一致**（至少 `lint --check-only`、`eval`、`lint --check-docs` 三条对拍）。
- **任意 cwd**：从 `/tmp` 等非引擎目录跑 `wiki lint --root <abs>` 成功（不再 `must run from repo root`）。
- **解释器解析**：`WIKI_PY` 覆盖生效；未设时按顺序回退；解析失败给清晰报错而非 traceback。
- **透传**：`--root` / `--force` / `--sync-schema` 等参数与退出码透传正确（含 lint error 时 exit 1、config error exit 2）。
- **skill 自洽**：`skill/wiki/SKILL.md` 改用 `wiki` 入口后，库识别 / lint / graph / eval 流程仍可走通（保留 `WIKI_PY` 兜底说明）。

## 替代方案

- **python entry point（`pip install -e` + console_scripts）**：要打包 / 安装步骤，比薄 shell 重；这是个人 + 多 agent 直接跑仓库的项目，免安装的 `bin/wiki` 更合适。**放弃**。
- **shell alias / 函数**：不可分发、不进 Git、每机器手配。**放弃**。
- **Makefile target**（`make lint root=x`）：语法不如子命令直观，传参别扭。**放弃**。
- **维持现状**：摩擦持续、易错。**放弃**。

## 影响范围

- 新增 `bin/wiki`（可执行）。
- `.gitignore`：放行 / 忽略 `.wiki-cli.conf`（若采纳，每机器配置不进 Git）。
- `scripts/README.md`：`wiki` 用法、解释器解析顺序、与直接调脚本的等价关系。
- `wiki-design/02-workflows.md`：把"推荐命令形态"从长命令更新为 `wiki <sub>`，落地原"未来 wiki CLI"占位。
- `skill/wiki/SKILL.md`：调用入口改 `wiki <sub>`，保留 `WIKI_PY` / 硬路径兜底。
- **不改**：`scripts/wiki_*.py` 任何逻辑、core schema、实例数据。

## Apply 拆分建议

单 Task（TASK-022）：`bin/wiki` + `.gitignore` + 文档（README / 02 / skill）+ 等价性/cwd/透传测试。改动小且自洽，不必拆 a/b。

## Review by codex · YYYY-MM-DD

（由 codex 追加，不覆盖本提案正文。）

## Decision

（由用户填写，或用户明确授权某 Agent 代写。）

## Review by codex · 2026-06-09

结论：需修改。

整体方向成立：新增薄 `bin/wiki` wrapper 确实能解决 REVIEW-001 小点2 指出的高频摩擦；只暴露 `lint` / `graph` / `eval` / `init` 四个用户命令也合理，`wiki_common.py` 作为库不应暴露成子命令。gate 自检两段合格，真实摩擦来源具体，验证方式也覆盖了等价性、任意 cwd、解释器解析、透传和 skill 自洽。单 TASK-022 落地是合理拆分。

### 阻塞点

1. **POSIX shell + 多词 `WIKI_PY` + 参数原样透传的实现算法未钉死。**

   RFC 同时要求 POSIX shell、`WIKI_PY="/Users/.../conda run -n py312 python"` 这种多词解释器命令、以及子命令参数含空格 / `--` / 特殊字符时原样透传。这里不能只写成“解析到的解释器用于 `exec`”。

   需要在 RFC 正文或 TASK spec 里明确采用哪一种：

   - 改成 bash/zsh wrapper，用数组保存解释器 argv 和用户 argv，然后 `exec "${interp[@]}" "$script" "$@"`。
   - 保持 POSIX shell，但明确 `WIKI_PY` / `.wiki-cli.conf python=` 只接受简单 shell words，内部用受控 word-splitting 构造解释器 argv，并单独保证用户参数始终用 `"$@"` 透传；同时承认解释器路径本身不能含空格。
   - 改成小 Python wrapper，用 `shlex.split()` 解析 `WIKI_PY` / config，再 `subprocess` / `os.execvp` 传 argv。

   反例：如果 POSIX shell 里写 `INTERP="$WIKI_PY"; exec "$INTERP" "$SCRIPT" "$@"`，`/Users/.../conda run -n py312 python` 会被当成一个可执行文件名，直接失败；如果简单不加引号展开解释器，又容易把用户参数透传和 shell word-splitting 混在一起，复发本仓已多次记录的变量拆词问题。

### 逐项意见

1. **形态：部分同意。**

   `bin/wiki` 薄 wrapper 是合适形态；自动 `cd` 到引擎根也能解决 `wiki_lint.py:162` 和 `wiki_graph.py:50` 的 repo-root 检查。需要在实现约束里写清路径定位：至少用带引号的 `dirname` + `pwd -P`，例如从实际 `bin/wiki` 所在目录推出 engine root。若希望支持把 `wiki` 软链到别处，还需额外处理 symlink；若不支持 symlink，应明确推荐把 `<engine>/bin` 加入 PATH。

2. **解释器解析：需修改后再通过。**

   解析顺序 `WIKI_PY > .wiki-cli.conf > conda run -n py312 python > python3` 合理；`conda run` 启动慢但可接受，因为 `WIKI_PY` 可覆盖。关键是解释器 argv 与用户 argv 的构造必须机械钉死，并验证退出码透传：lint error exit 1、config error exit 2、`init --sync-schema --force` 参数完整透传。

   另建议默认 fallback 若使用 conda，可考虑 `conda run --no-capture-output -n py312 python`，避免长任务输出被 conda 缓冲；这不是阻塞。

3. **子命令范围：同意。**

   `lint` / `graph` / `eval` / `init` 覆盖当前用户入口；`wiki_common.py` 是 shared lib，不暴露正确。新增子命令时只扩映射，不把业务逻辑写进 wrapper。

4. **gate 自检：通过。**

   「真实摩擦来源」不是空泛描述，明确指向长 conda 命令、cwd repo-root 检查、zsh word-split、skill 硬编码。 「验证方式」也足够落到 TASK：等价性、任意 cwd、解释器覆盖、透传、退出码和 skill 自洽都应测。

5. **Apply 拆分：同意。**

   单 TASK-022 足够；这是一处 wrapper + 文档 + 等价性测试的小改动，不需要拆 a/b。

### 建议修订

把“设计要点 2/3”合并补强为一个明确的“argv 构造规则”小节，写清 wrapper 使用的 shell 类型、解释器命令如何从字符串变成 argv、用户参数如何用 `"$@"` 原样透传、以及是否支持解释器路径含空格 / symlink 安装。修完后我预计可通过。
