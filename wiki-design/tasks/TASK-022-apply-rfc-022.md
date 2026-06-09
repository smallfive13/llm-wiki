---
id: task_20260609_022
title: Apply RFC-022 — bin/wiki CLI 薄 wrapper
author: claude
executor: codex
status: pending
type: apply
created: 2026-06-09
updated: 2026-06-09
related_rfcs: [RFC-022]
---

# TASK-022: Apply RFC-022 — bin/wiki CLI 薄 wrapper

## 目标

新增引擎仓 `bin/wiki`（bash + 数组 argv 构造）统一入口，转发 `lint` / `graph` / `eval` / `init` 到 `scripts/wiki_*.py`；同步文档（README / 02 / skill）；加等价性 / cwd / 透传 / 边界测试。不改任何现有脚本逻辑。

## 前置条件

- RFC-022 status: accepted（Decision by claude 2026-06-09）。
- working tree clean（除本 task）。
- 环境：`/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python`（完整命令，勿塞 zsh 变量）。

## 强约束（RFC-022 argv 规则钉死）

1. **bash + 数组**：shebang `#!/usr/bin/env bash`，`set -euo pipefail`，`chmod +x`；解释器经 `read -r -a INTERP <<< "$str"` 拆 argv；`exec "${INTERP[@]}" "$SCRIPT" "$@"`。
2. **定位引擎根**：`SELF="$(cd -P "$(dirname "$0")" && pwd)"`、`ENGINE="$(cd -P "$SELF/.." && pwd)"`；执行前 `cd "$ENGINE"`（解 `must run from repo root`）。**不支持 symlink**；分发靠 `<engine>/bin` 入 `PATH`。
3. **解释器解析顺序**：`WIKI_PY` → `.wiki-cli.conf` 的 `python=` → `conda run --no-capture-output -n py312 python`（`command -v conda` 命中）→ `python3`。
4. **子命令 `case` 白名单**：`lint`/`graph`/`eval`/`init` → 对应 `wiki_*.py`；**未知子命令报错退出、不裸拼脚本名**。
5. **用户参数恒 `"$@"` 透传**，不二次拆词；退出码由 `exec` 透传（lint error 1 / config error 2）。
6. **空解释器防御**：空 `WIKI_PY` / 空 `python=` **不得**留空数组直接 `exec`——给清晰报错或回退；`WIKI_PY` 指向不存在命令 → 清晰 stderr + 非 0。
7. **不改**：`scripts/wiki_*.py` 任何逻辑、core schema、实例数据。

## 步骤

> **Step 0 spec-review**：核对 `wiki_lint.py` / `wiki_graph.py` / `wiki_eval.py` / `wiki_init.py` 的 argparse 入口（确认 `python wiki_X.py [args]` 调用形态一致）、repo-root 检查位置（`cd "$ENGINE"` 解决）、`.gitignore` 现有结构（`.wiki-cli.conf` 放哪）；确认目标 bash 支持（macOS `/usr/bin/env bash`）。发现歧义先提。

1. **`bin/wiki`**：按强约束 1-6 实现；`chmod +x`。
2. **`.gitignore`**：忽略 `.wiki-cli.conf`（每机器配置，不进 Git）。
3. **`scripts/README.md`**：`wiki <sub>` 用法、解释器解析顺序、与直接调脚本的等价关系、`WIKI_PY` / `.wiki-cli.conf` 说明。
4. **`wiki-design/02-workflows.md`**：把「推荐命令形态」从长 conda 命令更新为 `wiki <sub>`，落地原"未来 wiki CLI"占位（保留底层 `python scripts/...` 仍可用的说明）。
5. **`skill/wiki/SKILL.md`**：调用入口改 `wiki <sub>`，**保留 `WIKI_PY` / 硬编码 python 路径兜底**（skill 在无 `wiki` PATH 时仍可用）。
6. **测试 `tests/test_task_022.py`**（subprocess 调 `bin/wiki`，测试内用 `WIKI_PY` 指向 py312 解释器以确定性）：
   - **等价性**：`wiki lint --root knowledge --check-only` / `eval --root knowledge` / `lint --root knowledge --check-docs` 的 stdout 与退出码，与直接 `python scripts/wiki_*.py ...` 逐项一致。
   - **任意 cwd**：从非引擎目录（如 `/tmp`）跑 `wiki lint --root <abs knowledge>` 成功（不再 `must run from repo root`）。
   - **解释器**：`WIKI_PY` 覆盖生效；`WIKI_PY` 指向不存在命令 → 清晰 stderr + 非 0；空 `python=` → 回退 / 报错、**不空 exec**。
   - **透传**：含空格参数（`--root "<tmp>/space dir"` 或等效 fixture）证明 `"$@"` 未被拆坏；`--force` / `--sync-schema` 透传；lint error → exit 1、config error → exit 2。
   - **未知子命令** → 报错 + 非 0 退出。
7. 跑验证 → commit（引擎一个 commit）。

## 验证

```bash
cd /Users/zhangjunwu/workspace/llm-wiki/llm-wiki
chmod +x bin/wiki
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest -v tests.test_task_022
# 等价性手验（wrapper vs 直接调）
export WIKI_PY="/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python"
./bin/wiki lint --root knowledge --check-only; echo "wiki lint exit=$?"
./bin/wiki eval --root knowledge | tail -3
# 任意 cwd
(cd /tmp && /Users/zhangjunwu/workspace/llm-wiki/llm-wiki/bin/wiki lint --root /Users/zhangjunwu/workspace/llm-wiki/llm-wiki/knowledge --check-only); echo "anycwd exit=$?"
# 未知子命令
./bin/wiki bogus 2>&1 | head -2; echo "bogus exit=$?"
# 现有套件不回归（未改脚本）
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest tests.test_task_020a tests.test_task_021a tests.test_task_021b
```

## 完成后报告格式

- Step 0 spec-review 结论（argparse 入口形态、.gitignore 落点、bash 可用性）
- 改动文件 + 关键位置（bin/wiki argv 构造、.gitignore、README/02/skill）
- 验证输出（test_task_022 各断言、等价性、任意 cwd、未知子命令、回归）
- commit sha
- 偏离或异常

## Execution log by codex · <date>

（执行者填写）

## Evaluation by claude · <date>

（评估者填写）
