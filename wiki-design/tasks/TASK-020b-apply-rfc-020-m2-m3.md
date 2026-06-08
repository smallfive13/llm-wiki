---
id: task_20260608_020b
title: Apply RFC-020 M2+M3 — 写入指令正本收敛（05/skill 降指针）+ 新 RFC 准入 gate
author: claude
executor: codex
status: pending
type: apply
created: 2026-06-08
updated: 2026-06-08
related_rfcs: [RFC-020]
---

# TASK-020b: Apply RFC-020 M2+M3

## 目标

落地 RFC-020 M2（写入指令 + 字段定义正本收敛：`AGENTS.md`（行为）+ `knowledge/.wiki-schema.md`（数据契约）为**唯一正本**；`wiki-design/05-contracts-and-next-steps.md` 的字段表 / schema 详表降为**指针**、只留设计理由；`skill/wiki/` 降为精简引用 + 指针）+ M3（新 RFC 准入 gate：`rfcs/README.md` RFC 模板加「真实摩擦来源」「验证方式」必填段 + `04-agent-rules.md` 写明 gate 适用边界）。M1 / M4 已由 TASK-020a 闭环。

## 前置条件

- RFC-020 status: accepted；TASK-020a status: done（6 个生成块已在 `.wiki-schema.md` 就位、`--check-docs` exit 0）。
- working tree clean（除本 task）。
- 环境：`/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python`（完整命令，勿塞 zsh 变量）。

## 强约束

1. **M2 只删冗余 / 改指针，不改任何语义**。删除前必须先产出「删除审计表」：每个被删块标三选一——(a) 已在 `.wiki-schema.md` 完整覆盖；(b) 属设计理由 / 取舍，保留在 05；(c) 迁移到其它引用。**不得把唯一信息当重复删掉。**
2. **skill 降引用但保留运行所需信息**：`instances.json` 用法、`engine` 字段、python 命令拼接、库识别 / 选择流程、lint/graph 校验投影步骤必须留；只删与 `AGENTS.md` / `.wiki-schema.md` 重复的字段表 / 规则镜像。
3. **M3 gate 适用边界写清**：两必填段允许非机制类 RFC 写「不适用：纯 bugfix / 文档修复，未引入新机制」；gate 只约束**机制类**（动 schema / 新页面机制 / 新派生信号 / 新工作流机制）；纯鲁棒性 / bugfix / 文档豁免；但"工具改进"若实际引入新机制仍受 gate。
4. **不改**：scripts 行为、core schema 语义、`schema_version`、任何实例数据。
5. 预期**不改 `knowledge/.wiki-schema.md`**（它已是正本）；若确需微调，apply 收尾按 RFC-015 `--sync-schema`（datawarehouse 当前 clean）。仅改 05 / skill / 04 / rfcs README 不触发 sync。

## 步骤

> **Step 0 spec-review**：通读 `05-contracts-and-next-steps.md` 全文，逐段分类「字段表 / schema 详表（可降指针）」vs「设计理由 / 取舍 / 下一步（保留）」；通读 `skill/wiki/SKILL.md` + `skill/wiki/references/schema.md`，分类「规则 / 字段镜像（降引用）」vs「运行信息（保留）」；核对 `rfcs/README.md`「新建 RFC 模板」段与 `04-agent-rules.md` 结构。**先把删除审计表草案贴出来，确认无误再动手删。**

1. **M2-05**：`05-contracts` 的字段表 / `Capture Policy Schema` / `Wiki Profile Schema` / `Capture Item Schema` / `Inbox Index Schema` 等**详表** → 降为指针「权威定义见 `knowledge/.wiki-schema.md` 的 <对应段>」，保留每段的设计理由 / 取舍。P0 刚更新过的 `Capture Policy Schema` 段同样降指针（它现在与 `.wiki-schema.md` 重复）。
2. **M2-skill**：`skill/wiki/SKILL.md` 三种写入模式 → 精简为「以库根 `AGENTS.md` + `.wiki-schema.md` 为准」+ 操作入口；`skill/wiki/references/schema.md` → 改为指向库根 `.wiki-schema.md`、不再镜像字段表。保留 instances / engine / python / 库识别等运行信息。
3. **M3-模板**：`wiki-design/rfcs/README.md`「新建 RFC 模板」加 `## 真实摩擦来源` + `## 验证方式` 两必填段，并注明非机制类可写「不适用：纯 bugfix / 文档修复，未引入新机制」。
4. **M3-rules**：`wiki-design/04-agent-rules.md` 加一节写 gate 适用边界（机制类必填真实摩擦 + 验证；鲁棒性 / 文档 / bugfix 豁免；工具改进若引入新机制仍受限）。
5. 跑验证 → commit（引擎一个 commit）。

## 验证

```bash
cd /Users/zhangjunwu/workspace/llm-wiki/llm-wiki
# M2 降指针不应破坏 .wiki-schema.md 的 6 个生成块
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root knowledge --check-docs; echo "check-docs exit=$?"
# 普通 lint 仍 exit 0
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root knowledge --check-only; echo "lint exit=$?"
# 全量回归（含 020a）
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest tests.test_task_012 tests.test_task_013 tests.test_task_014 tests.test_task_015 tests.test_task_016a tests.test_task_016b tests.test_task_017 tests.test_task_019 tests.test_task_020a
# 人工：删除审计表逐条核对；rg 抽查 05 / skill 不再保留与 .wiki-schema 重复的 enum / 字段详表
```

## 完成后报告格式

- Step 0 spec-review 结论 + **删除审计表**（每删块三选一标注 a/b/c）
- 改动文件 + 关键位置（05 降指针处、skill 降引用处、rfcs 模板两段、04 gate 节）
- 验证输出（check-docs exit 0、check-only exit 0、回归、审计表核对结论）
- commit sha
- 偏离或异常

## Execution log by codex · <date>

（执行者填写）

## Evaluation by claude · <date>

（评估者填写）
