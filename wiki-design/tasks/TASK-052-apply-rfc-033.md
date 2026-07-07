---
id: task_20260707_052
title: Apply RFC-033 — bin/wiki 在线子命令 + @alias 解析收敛 + conf 两级安全 + doctor（含云端 smoke 硬 gate）
author: claude
executor: codex
status: pending
type: apply
created: 2026-07-07
updated: 2026-07-07
related_rfcs: [RFC-033]
---

# TASK-052: Apply RFC-033 引擎侧

## 目标

按 RFC-033 落引擎四件事：① `bin/wiki` 增 `freshness` / `index` / `evidence` 子命令（evidence 为固定 argv 前缀映射）；② `wiki_common` 实现 `@alias` 实例根解析并**替换五个脚本的调用点**；③ `.wiki-cli.conf` 结构化两级安全（key 白名单 + 高置信凭证 hard fail + 弱关键词 doctor warning）；④ `wiki doctor`。文档同步。**done 判定含生产云端 smoke 证据（硬 gate）。**

## 前置条件

- RFC-033 accepted（Decision 已登记）。引擎 working tree clean。
- 云端环境：`/home/js_zhangjunwu/llm-wiki`（引擎）/ `/home/js_zhangjunwu/knowledge-pk`（实例）/ `/home/js_zhangjunwu/miniconda3-py311/bin/python`。**若本会话无法到达云端 shell**（codex review 时 SSH identity 缺失），实现+本地验证完成后**停在云端 gate**，把「待云端执行的命令清单 + 通过标准」写进 Execution log 等 maintainer 提供通道或代跑，**不得推 done**。

## 强约束

1. **回归头等**：`lint/graph/eval/init` 四个既有子命令行为不变（含解释器发现链 `WIKI_PY` → conf `python=` → conda py312 → python3）；全量 unittest 绿。
2. **wrapper 边界**：不解析/重写用户参数；仅允许命令映射添加固定 argv 前缀（`wiki evidence` → prepend `evidence` 转发 `dataworks_client.py`）。
3. **@alias 解析在 `wiki_common`，且必须替换调用点**：`wiki_lint / wiki_graph / wiki_eval / wiki_freshness / wiki_index` 的 instance root 解析统一走公共 helper——仅新增 helper 不替换调用点**不算落地**。grammar `^[A-Za-z][A-Za-z0-9_-]*$`；`@<alias>` 为保留语义（真实目录须写 `./@pk`）；三类报错（未配置→提示加 `root.pk=` 行 / 名非法→给 grammar / 路径不存在→给解析后路径）。
4. **conf 结构化两级安全**（不做 substring 全文扫描）：key 白名单只有 `python=` / `root.<alias>=`，未知 key 拒跑；高置信凭证样式（`ALIBABA_CLOUD_ACCESS_KEY_*`、`ACCESS_KEY_ID/SECRET=`、`LTAI` 前缀、`password/token/secret\s*[:=]`、`bearer\s+`）拒跑；路径 value 含弱关键词（无赋值形态）仅 doctor warning，不拒跑、不提供关闭扫描开关。
5. **doctor 零泄漏**：输出引擎根 / 解释器与版本 / conf 路径与别名（路径存在性）/ 凭证 env **present/absent**——严禁打印任何 env 值。
6. **云端 smoke 硬 gate**（RFC 验证方式钉死）：云端 conf 写 `python=/home/js_zhangjunwu/miniconda3-py311/bin/python` + `root.pk=/home/js_zhangjunwu/knowledge-pk`，跑 `./bin/wiki doctor` 与 `./bin/wiki freshness --root @pk --help`；通过标准：doctor 无凭证值、解释器版本正常、`@pk` 解析到云端 pk 路径、`freshness --help` exit 0。**无云端证据不得 done**。
7. 离线三件套零依赖不变；不改 knowledge-pk 仓内容（那是 TASK-053）。

## 步骤

1. `bin/wiki`：三个新子命令映射 + `doctor` + conf 结构化解析与两级安全（bash 侧至少 key 白名单 + 高置信拒跑；弱关键词 warning 可由 doctor 输出）。
2. `scripts/wiki_common.py`：conf 读取 + `@alias` 解析 helper；替换五脚本调用点（保持各脚本对外 CLI 行为不变，仅 root 参数语义扩展）。
3. `tests/test_task_052.py`：四旧子命令回归（fake 解释器 fixture）/ 新子命令转发（含 evidence 前缀）/ 别名三类报错 + `./@pk` 不触发 / 五脚本调用点全生效断言 / conf 安全双向 fixture（`ACCESS_KEY_SECRET=`、`LTAI...`、`password=` 拒跑；`root.tk=/data/tokenized-features` 不拒跑且 doctor warning；未知 key 拒跑）/ doctor 无 env 值断言 / 离线隔离。
4. `scripts/README.md`（wiki CLI 段重写：conf 模板 + 别名 + doctor + 新子命令）+ `wiki-design/02-workflows.md`「推荐命令形态」段更新。
5. 本地验证全过 → **云端 gate**（约束 6；到不了云端则按前置条件停等）。
6. 引擎 commit；RFC-033 登记 `## Applied in <sha>`。

## 验证

```bash
cd /Users/zhangjunwu/workspace/llm-wiki/llm-wiki   # 本地侧
./bin/wiki lint --root @pk --check-only; echo lint=$?          # 需本机 conf 已配 root.pk
./bin/wiki freshness --root @pk --help >/dev/null; echo freshness=$?
./bin/wiki evidence --help >/dev/null; echo evidence=$?
./bin/wiki doctor
python3 -m unittest tests.test_task_052 2>&1 | tail -2
python3 -m unittest discover -s tests 2>&1 | tail -2
python3 -c "import sys; sys.path.insert(0,'scripts'); import wiki_lint,wiki_graph,wiki_eval; print('泄漏:', [m for m in sys.modules if any(k in m.lower() for k in ('dataworks','alibabacloud','sqlglot'))] or '无')"
# 云端侧（硬 gate）见强约束 6
```

## 完成后报告格式

- 四件事实现位置 + conf 两级安全判定逻辑
- 本地验证输出（回归 / 新子命令 / 别名 / 安全双向 / doctor）
- **云端 smoke 证据**（doctor 与 freshness --help 输出，脱敏）或「停等 gate」说明
- commit sha + RFC-033 Applied、偏离或异常

## Execution log by codex · <date>

## Evaluation by claude · <date>
