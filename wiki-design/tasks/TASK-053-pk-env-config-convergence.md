---
id: task_20260707_053
title: knowledge-pk 环境配置收敛 — AGENTS.md / runbook 去机器路径，改 wiki <sub> --root @pk
author: claude
executor: codex
status: pending
type: other
created: 2026-07-07
updated: 2026-07-07
related_rfcs: [RFC-033]
---

# TASK-053: knowledge-pk 环境配置收敛

## 目标

RFC-033 引擎能力就绪后，把 knowledge-pk 正本文档里的**每机器路径/解释器全部清除**：`AGENTS.md` 删每机器变量段、`ops/incremental-knowledgization.md` 前置段收敛 + 全部命令改 `wiki <sub> --root @pk` 形式。此后新机器接入只需初始化本机 `.wiki-cli.conf` 一次，正本不再随机器增长。

## 前置条件

- **TASK-052 done**（含云端 smoke 证据——云端 conf 已在 052 gate 写好并验证）。
- 本地 `.wiki-cli.conf` 已配 `root.pk=`（052 本地验证时已建）。
- knowledge-pk working tree clean。

## 强约束

1. **只删每机器差异，不删逻辑约定**：`ENGINE_ROOT` / `PYTHON_BIN` / conda 全路径 / `/Users/...`、`/home/js_...` 绝对路径 / 「不要使用不存在的 ...python」防坑注记 → 全部清除；region `ap-southeast-1`、project `96107`、流程红线、L3 约束 → 原样保留。
2. **命令形态统一**：runbook / AGENTS.md 中的引擎命令一律 `wiki <sub> [args] --root @pk`（或无 root 的 `wiki evidence ...`）；不再出现 `cd $ENGINE_ROOT`、`$PYTHON_BIN`、conda 全路径。
3. 前置段收敛为一句：「本机 `<引擎根>/.wiki-cli.conf` 已初始化（`python=` + `root.pk=`，模板与排障见引擎 `scripts/README.md` 的 wiki CLI 段；自检 `wiki doctor`）」。
4. 改完后**实测**：本机按新文档逐条跑 runbook 第 1 步与收尾 lint/graph/eval 命令，全部可执行——文档改写不允许只改字面不验证。
5. 不动 wiki 页面正文 / 索引 / review 字段；这是纯运营文档收敛。

## 步骤

1. 盘点：`grep -rn "ENGINE_ROOT\|PYTHON_BIN\|/Users/zhangjunwu\|/home/js_zhangjunwu\|conda run\|anaconda3\|miniconda3" AGENTS.md ops/ purpose.md` 列出全部残留点，报数。
2. `AGENTS.md`：删每机器变量段，指向引擎 README 的 conf 机制；命令示例改 `wiki <sub> --root @pk`。
3. `ops/incremental-knowledgization.md`：前置段按约束 3 收敛；流程各步命令改写；「依赖的引擎能力」表补 RFC-033 行。
4. 逐条实测改写后的命令（约束 4）；lint / graph / eval 过。
5. `log.md` 记录；commit（pk 仓）。

## 验证

```bash
PK=/Users/zhangjunwu/workspace/obsidian/knowledge-pk   # 本地写法仅用于本 task 验证描述
grep -rn "ENGINE_ROOT\|PYTHON_BIN\|/home/js_zhangjunwu\|anaconda3\|miniconda3\|conda run" $PK/AGENTS.md $PK/ops/ && echo "残留！" || echo "机器路径 0 残留"
wiki lint --root @pk --check-only; echo lint=$?
wiki freshness --root @pk --incremental-deployments --project-id 96107 --json >/dev/null; echo freshness=$?   # dry-run
wiki eval --root @pk --json | python3 -c "import sys,json;print('score',json.load(sys.stdin)['score'])"
```

## 完成后报告格式

- 盘点残留点数 → 清除后 0 残留证明（grep 输出）
- AGENTS.md / runbook 改动摘要（删了什么、命令形态前后对比一例）
- 新文档命令逐条实测输出
- lint / graph / eval、commit sha、偏离或异常

## Execution log by codex · <date>

## Evaluation by claude · <date>
