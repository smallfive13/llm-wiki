---
id: task_20260622_030
title: Apply RFC-027 M4 — 答疑回源策略（默认信库 + 触发式回源 DataWorks）
author: claude
executor: codex
status: pending
type: apply
created: 2026-06-22
updated: 2026-06-22
related_rfcs: [RFC-027]
---

# TASK-030: Apply RFC-027 M4

## 目标

落地 RFC-027 M4（答疑回源，L1+L3）：把"默认信库 + 触发式回源 DataWorks 当前代码"写成 agent 答疑约定（pk AGENTS 答疑节 + 引擎 02-workflows）。**纯文档约定，不改 scripts**（回源复用 M3 已就绪的 `dataworks_client`）。RFC-027 最后一块。

## 前置条件

- RFC-027 M3 applied（TASK-029，`dataworks_client` + `wiki_freshness` 就绪）。
- 引擎 working tree clean。环境：`/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python`。

## 强约束

1. **不改 scripts**（纯文档：引擎 `02-workflows.md` + knowledge-pk `AGENTS.md` 答疑节）；回源动作复用现有 `dataworks_client`，不新增访问层、不碰凭证逻辑。
2. **触发写成内容/状态规则，不靠"识别请求来源"**（企微/CLI/其它渠道统一同一约定；agent 以库为 cwd 读 AGENTS）。
3. **决策树（钉死）**：
   - **用库不回源**（默认、最常见）：命中页 `review:true` + 未 `stale` + 问的是业务语义/定义/口径含义。
   - **回源**（调 `dataworks_client` 查当前代码/表结构，合并答）：命中页 `stale`，或 `review:false` 且问题关键，或问题语义含"当前实现/最新/线上怎么算/代码里怎么写/字段从哪来/哪张表/口径细节"等"要当前精确事实"信号。
   - **未命中**：仅当属**数仓/表/字段/代码/口径类**问题才回源（先定位表→查代码）+ 登记 source-gap；**非数仓类问题未命中 → 答"库内无依据"，不调 SDK**。
4. **L3 人控**：回源发现与库口径不一致 → 标 maintainer 复核（接 trust loop），**不自动改正本**。
5. **答疑出处**：保持现有约定——回答末尾「来源」列依据 source 页的 `source_url`；回源补充的当前代码事实注明"实时取自 DataWorks（region ap-southeast-1）、未经人工背书"。
6. doc-consistency 不破（`wiki_lint --check-docs`）。

## 步骤

> **Step 0 spec-review**：核对 pk `AGENTS.md` 节 7 答疑现状 + 引擎 `02-workflows.md` 现有结构（M3 的 freshness 段、团队/巡检段），找回源约定落点，避免与既有答疑/source_url 约定重复或冲突。歧义先提。

1. **`wiki-design/02-workflows.md`**：新增/扩展「答疑回源」约定——决策树（强约束 3）+ 触发内容规则 + 范围限定 + L3 人控 + 回源出处标注。通用层。
2. **`knowledge-pk/AGENTS.md`** 节 7：答疑回源（指向 02 通用约定 + pk 特定：DataWorks 代码回源用 `dataworks_client`，region `ap-southeast-1`，凭证 env）。
3. doc-consistency：`wiki_lint --check-docs` 通过。
4. 提交：引擎一个 commit（02）；knowledge-pk 单独 commit（AGENTS）。push GitLab。

## 验证

```bash
cd /Users/zhangjunwu/workspace/llm-wiki/llm-wiki
PY="/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python"
$PY scripts/wiki_lint.py --check-docs; echo "docs=$?"   # exit 0
$PY scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk; echo "pk_lint=$?"  # exit 0
$PY -m unittest discover -s tests 2>&1 | tail -2   # 纯文档，回归不应受影响
```

## 完成后报告格式

- Step 0 结论（02/AGENTS 回源约定落点）
- 改动文件 + 关键位置（决策树、触发规则、范围限定、L3 人控、出处标注）
- 验证输出（--check-docs、pk lint、回归、引擎 + pk commit sha + push）
- 偏离或异常

## Execution log by codex · <date>

（执行者填写）

## Evaluation by claude · <date>

（评估者填写）
