---
id: rfc_20260707_033
title: 每机器环境配置抽象 — bin/wiki 覆盖在线工具 + 实例 root 别名 + doctor
author: claude
status: proposed
created: 2026-07-07
updated: 2026-07-07
targets:
  - bin/wiki
  - scripts/wiki_common.py
  - scripts/README.md
  - wiki-design/02-workflows.md
  - tests/
reviewers:
  - codex
  - user
---

# RFC-033: 每机器环境配置抽象

## 背景

引擎与知识库现在跑在多台机器上（本地 macOS + 生产云端），**每机器差异的路径/解释器正在泄漏进跨机器共享的正本文档**，腐烂已经开始：

- knowledge-pk 的 `ops/incremental-knowledgization.md` 已同时写死两套机器路径（本地 `/Users/zhangjunwu/soft/anaconda3/...` 与云端 `/home/js_zhangjunwu/miniconda3-py311/...`），并出现「不要使用不存在的 `.../envs/codex-node/bin/python`」的防坑注记——即 agent 已在生产环境猜错过一次 Python 路径。
- pk `AGENTS.md` 里也定义了每机器变量（`ENGINE_ROOT` / `PYTHON_BIN`）；每加一台机器，正本就要再堆一段。
- 引擎 task 文件的验证命令普遍写死 `/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python ...` 全路径。

三类配置现状混在一起，需要分层：

| 类别 | 例子 | 应放 | 现状 |
| --- | --- | --- | --- |
| 凭证 | `ALIBABA_CLOUD_ACCESS_KEY_*` | env-only，不落文件 | 已正确 |
| **每机器路径/解释器** | 引擎根、Python、实例根 | 每机器本地配置，不进 Git | **泄漏进正本** |
| 逻辑约定 | region、project 96107、流程红线 | 正本文档 | 已正确 |

**引擎已有半套机制**（RFC-022）：`bin/wiki` wrapper 从自身位置推导引擎根并自动 `cd`（`ENGINE_ROOT` 本可消灭）；`.wiki-cli.conf`（gitignored，每机器）已承载 `python=` 解释器配置，发现链 `WIKI_PY` env → conf → conda py312 → python3。问题是 wrapper **只覆盖 `lint/graph/eval/init` 四个离线工具**——`wiki_freshness` / `wiki_index` / `dataworks_client`（含 RFC-032 evidence）都不在内，于是 runbook 一到在线工具就只能裸写 `PYTHON_BIN` + `cd ENGINE_ROOT`。

## 提案

### 1. `bin/wiki` 子命令扩展（覆盖在线工具）

| 新子命令 | 映射 |
| --- | --- |
| `wiki freshness ...` | `scripts/wiki_freshness.py ...` |
| `wiki index ...` | `scripts/wiki_index.py ...`（含 `reverse` / `origin` / `datasource-map`）|
| `wiki evidence ...` | `scripts/dataworks_client.py evidence ...` |

既有四个子命令行为不变（回归保障）。wrapper 保持薄：只做解释器发现 + `cd` 引擎根 + exec，不做参数改写。

### 2. 实例 root 别名（`.wiki-cli.conf` 扩展 + Python 公共层解析）

- conf 新增行式键：`root.<alias>=<绝对路径>`，例如本地 `root.pk=/Users/zhangjunwu/workspace/obsidian/knowledge-pk`、云端 `root.pk=/home/js_zhangjunwu/knowledge-pk`。
- **别名解析放 `wiki_common` 的实例根解析处**（而非 wrapper 做字符串改写）：`--root @pk` → 读引擎根 `.wiki-cli.conf` 的 `root.pk`。这样不经 wrapper 直调 `python3 scripts/wiki_lint.py --root @pk` 同样生效，且引号/空格处理稳。
- 别名未配置时报错必须可执行：提示「在 <引擎根>/.wiki-cli.conf 加一行 root.pk=<本机路径>」。
- 正本文档从此只写 `@pk`，机器差异各自在本机 conf 配一次。

### 3. conf 安全红线

`.wiki-cli.conf` 只允许路径/解释器类键（`python=` / `root.*=`）。**禁止放凭证**：读取方（wrapper 与 `wiki_common`）发现 conf 内容匹配凭证样式（`ALIBABA`、`ACCESS_KEY`、`SECRET`、`password`、`token`）时直接报错拒跑——延续禁词硬门禁风格。凭证仍 env-only（不变）。

### 4. `wiki doctor`（新机器排障入口）

打印：引擎根、解释器命令与 `--version`、conf 路径与已配置别名（路径存在性 ✓/✗）、DataWorks 凭证 env **是否存在**（只报 present/absent，严禁打印值）。云端「猜错 python」这类问题从试错变成一条命令自检。

### 5. 文档收敛（引擎侧本 RFC；实例侧另 task）

- 引擎：`scripts/README.md`（wiki CLI 段重写：conf 模板 + 别名 + doctor）、`wiki-design/02-workflows.md`「推荐命令形态」段更新；**新 task 验证命令一律写 `wiki <sub>`，不再写 conda 全路径**（既有 task 文档是历史记录，不回改）。
- 实例侧后续 task（pk 仓）：`AGENTS.md` 删每机器变量段、`ops/incremental-knowledgization.md` 前置段缩成「本机 `.wiki-cli.conf` 已初始化（模板见引擎 README）」+ 命令全部改 `wiki <sub> --root @pk`。

## 真实摩擦来源

用户 2026-07-07 提出「环境变量在不同机器会变化，是否应抽象单独配置」；直接证据：pk runbook 已堆两套机器路径与防坑注记、codex 生产环境猜错 Python 路径、AGENTS.md 承载每机器变量。

## 验证方式

- 回归：`lint/graph/eval/init` 四个既有子命令行为不变（含解释器发现链）；全量 unittest 绿。
- 新子命令映射 smoke：`wiki freshness --help` / `wiki index reverse ...` / `wiki evidence --help` 均正确转发。
- 别名 fixture：`--root @pk` 解析到 conf 配置路径；未配置别名 → 报错含「加一行 root.pk=」提示；`@` 开头但非别名语义不误伤（如确有 `@` 开头目录时的行为钉死——建议 `@` 保留为别名前缀，真实路径不得以 `@` 开头，报错说明）。
- conf 安全 fixture：conf 含凭证样式串 → 拒跑。
- doctor 输出断言不含任何 env 值（只有 present/absent）。
- **双机验证**：本地 macOS 与生产云端各配 `.wiki-cli.conf` 后，runbook 第 1 步命令以 `wiki freshness --root @pk --incremental-deployments --project-id 96107` 形式跑通（codex 有云端环境，由其验证）。

## 替代方案

1. **每机器一个 env 文件（`~/.llm-wiki.env`）+ 文档教 source**：仍要求使用者记得 source、且 `cd ENGINE_ROOT` 摩擦仍在；wrapper 方案把这两步都消掉。否决为主方案，但 conf 机制与其不冲突。
2. **文档里维护多套机器路径段**：现状，已证明会腐烂（每机器一段、防坑注记堆积）。否决。
3. **把路径配置放各实例仓**：实例仓是跨机器共享的正本，同样装不下每机器差异；且引擎路径与实例无关。否决。

## 影响范围

- `bin/wiki`（子命令扩展 + conf 安全检查 + doctor）。
- `scripts/wiki_common.py`（`@alias` 实例根解析 + conf 读取）。
- `scripts/README.md` / `wiki-design/02-workflows.md`。
- `tests/`（wrapper 回归 + 别名 + 安全 + doctor fixture）。
- 实例侧后续 task（pk 仓）：AGENTS.md / runbook 收敛，不在本 RFC targets。

## Decision

（由用户填写，或用户明确授权某个 Agent 代写。）
