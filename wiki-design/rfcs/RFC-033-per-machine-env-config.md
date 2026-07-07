---
id: rfc_20260707_033
title: 每机器环境配置抽象 — bin/wiki 覆盖在线工具 + 实例 root 别名 + doctor
author: claude
status: accepted
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

> **作者修订 · 2026-07-07（吸收 codex review 三点调整）**：① 别名 grammar 钉死 + `@` 保留语义 + root 解析**收敛替换各脚本调用点**（仅加 helper 不算落地）；② conf 安全从「禁词全文硬拒」改为「**结构化 key 白名单 + 高置信 secret hard fail + 弱关键词仅 doctor warning**」（避免 `tokenized-features` 类路径误伤）；③ wrapper 表述改为「不解析/重写用户参数，仅允许命令映射添加固定 argv 前缀」。另澄清时序：codex 要求的生产云端 smoke 涉及本提案新功能（doctor / freshness 子命令），accepted 前尚不存在，故钉为 **apply-task done 的硬 gate**（实现后、宣布落地前必须出云端证据）。status → discussing，待用户 Decision。

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

既有四个子命令行为不变（回归保障）。wrapper 保持薄：只做解释器发现 + `cd` 引擎根 + exec；**不解析、不重写任何用户参数**，仅允许在命令映射层添加固定 argv 前缀（如 `wiki evidence` → prepend `evidence` 后转发 `dataworks_client.py`，不碰 `--root` 等用户参数）。

### 2. 实例 root 别名（`.wiki-cli.conf` 扩展 + Python 公共层解析）

- conf 新增行式键：`root.<alias>=<绝对路径>`，例如本地 `root.pk=/Users/zhangjunwu/workspace/obsidian/knowledge-pk`、云端 `root.pk=/home/js_zhangjunwu/knowledge-pk`。
- **别名 grammar 钉死**（codex review）：`^[A-Za-z][A-Za-z0-9_-]*$`。任何 raw `--root` 参数形如 `@<alias>` 即为**保留别名语义**；真实目录若确实叫 `@pk`，必须写 `./@pk`，裸 `@pk` 不走真实路径。
- **别名解析放 `wiki_common` 并收敛替换调用点**：`wiki_lint / wiki_graph / wiki_eval / wiki_freshness / wiki_index` 各自的 instance root 解析统一改走 `wiki_common` 公共 helper——**仅新增 helper 而不替换调用点不算落地**（否则直调脚本 / 测试 / CI 继续绕过别名）。这样不经 wrapper 直调 `python3 scripts/wiki_lint.py --root @pk` 同样生效。
- 报错区分三类且必须可执行：alias 未配置（提示「在 <引擎根>/.wiki-cli.conf 加一行 root.pk=<本机路径>」）/ alias 名非法（给 grammar）/ 解析后路径不存在（给解析到的路径）。
- 正本文档从此只写 `@pk`，机器差异各自在本机 conf 配一次。

### 3. conf 安全红线（codex review 修订：结构化两级，不做禁词全文硬拒）

`.wiki-cli.conf` 由读取方（wrapper 与 `wiki_common`）**结构化解析**，不做 substring 全文扫描（`token/password/secret` 可能合法出现在目录名，如 `tokenized-features`，全文硬拒会误伤路径）：

- **key 白名单**：只允许 `python=` 与 `root.<alias>=`；未知 key → **hard fail 拒跑**。
- **高置信凭证样式 → hard fail**：key 或 value 匹配 `ALIBABA_CLOUD_ACCESS_KEY_*`、`ACCESS_KEY_ID=` / `ACCESS_KEY_SECRET=`、`LTAI` 前缀、`password\s*[:=]`、`token\s*[:=]`、`secret\s*[:=]`、`bearer\s+` 时拒跑。
- **弱关键词 → 仅 warning**：路径 value 中出现 `token/password/secret` 词面（无 `:=` 赋值形态）只在 `wiki doctor` 报 warning，不拒跑；确要 fail-closed 的团队用 symlink / 换别名路径规避，不提供关闭凭证扫描的开关。

凭证仍 env-only（不变）。

### 4. `wiki doctor`（新机器排障入口）

打印：引擎根、解释器命令与 `--version`、conf 路径与已配置别名（路径存在性 ✓/✗）、DataWorks 凭证 env **是否存在**（只报 present/absent，严禁打印值）。云端「猜错 python」这类问题从试错变成一条命令自检。

### 5. 文档收敛（引擎侧本 RFC；实例侧另 task）

- 引擎：`scripts/README.md`（wiki CLI 段重写：conf 模板 + 别名 + doctor）、`wiki-design/02-workflows.md`「推荐命令形态」段更新；**新 task 验证命令一律写 `wiki <sub>`，不再写 conda 全路径**（既有 task 文档是历史记录，不回改）。
- 实例侧后续 task（pk 仓）：`AGENTS.md` 删每机器变量段、`ops/incremental-knowledgization.md` 前置段缩成「本机 `.wiki-cli.conf` 已初始化（模板见引擎 README）」+ 命令全部改 `wiki <sub> --root @pk`。

## 真实摩擦来源

用户 2026-07-07 提出「环境变量在不同机器会变化，是否应抽象单独配置」；直接证据：pk runbook 已堆两套机器路径与防坑注记、codex 生产环境猜错 Python 路径、AGENTS.md 承载每机器变量。

## 验证方式

- 回归：`lint/graph/eval/init` 四个既有子命令行为不变（含解释器发现链）；全量 unittest 绿。
- 新子命令映射 smoke：`wiki freshness --help` / `wiki index reverse ...` / `wiki evidence --help` 均正确转发（evidence 为固定 argv 前缀映射）。
- 别名 fixture：`--root @pk` 解析到 conf 配置路径且**五个脚本调用点全部生效**；三类报错各自断言（未配置 / 名非法 / 路径不存在）；`./@pk` 形式走真实路径不触发别名。
- conf 安全 fixture 双向：高置信凭证样式（`ACCESS_KEY_SECRET=...`、`LTAI...`、`password=...`）→ 拒跑；**合法路径含弱关键词**（如 `root.tk=/data/tokenized-features`）→ 不拒跑、doctor 出 warning。未知 key → 拒跑。
- doctor 输出断言不含任何 env 值（只有 present/absent）。
- **双机验证（apply-task done 的硬 gate，非 accepted 前置——功能实现前云端无从 smoke）**：本地跑通后，由有云端 shell 的执行者在 `/home/js_zhangjunwu/llm-wiki/.wiki-cli.conf` 写入 `python=` 与 `root.pk=`，跑 `./bin/wiki doctor` 与 `./bin/wiki freshness --root @pk --help`；通过标准（codex 钉死）：doctor 不打印任何凭证值、解释器版本正常、`@pk` 解析到 `/home/js_zhangjunwu/knowledge-pk`、`freshness --help` exit 0。**无云端证据不得把 apply-task 推 done**。

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

**Accepted**（用户 2026-07-07 明确 accept，授权 claude 代写结论）。codex review 三点调整（结构化 key 白名单 + 两级凭证扫描 / 别名 grammar + 调用点收敛 / evidence 固定 argv 前缀语义）已吸收进正文；云端 smoke 时序澄清为 **apply-task done 硬 gate**（新功能 accepted 前无从 smoke）。落地：**TASK-052**（引擎 apply，含云端 gate）→ **TASK-053**（pk 实例收敛：AGENTS.md / runbook 去机器路径）。

## Review by codex

日期：2026-07-07

结论：**需调整**。方向成立，建议用户暂不 `accepted`，先按下面 3 个调整点修 RFC/实现说明，并补一条真正的生产云端 smoke 证据后再接受。

### 复核证据

- 本地现状符合 RFC 背景：`bin/wiki` 当前只支持 `lint/graph/eval/init`，`./bin/wiki freshness --help` 返回 `wiki: unknown subcommand: freshness`，exit 2；直调 `python3 scripts/wiki_freshness.py --help` 和 `python3 scripts/dataworks_client.py evidence --help` 可用。
- 本地 wrapper 既有链路可用：`./bin/wiki lint --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk --check-only` exit 0，输出 `错误: 0 · 警告: 0`。
- 现有 tests 不是 RFC-033 本身，但当前 `python3 tests/test_task_033.py` 8 tests OK，说明 reverse/index 相关基线没坏。
- 生产云端路径从 pk 正本文档可见：引擎 `/home/js_zhangjunwu/llm-wiki`，实例 `/home/js_zhangjunwu/knowledge-pk`，解释器 `/home/js_zhangjunwu/miniconda3-py311/bin/python`；未发现已知真实路径以 `@` 开头的反例。
- 我没有完成生产云端实际执行：本机会话没有 SSH identity，`ssh -o BatchMode=yes js_zhangjunwu@cbdhdpfatfat029089 ...` 和 root/user 变体均被远端关闭；本机 Aliyun CLI profile 也显示 invalid region，不能可靠走云助手。因此双机 smoke 仍是 `accepted` 前必须补的证据。

### 1. 别名前缀与解析层

`@pk` 作为别名前缀可以接受。当前已知云端路径都是 `/home/...` 绝对路径，没有反例。需要把 RFC 写实一点：任何 raw `--root` 参数只要形如 `@<alias>` 就是保留别名语义；真实相对目录若确实叫 `@pk`，必须写成 `./@pk`，不要让裸 `@pk` 走真实路径。

解析应放 `wiki_common`，不是 wrapper。理由是当前 `wiki_lint.py`、`wiki_graph.py`、`wiki_eval.py`、`wiki_freshness.py`、`wiki_index.py` 都各自有 instance root 解析函数；如果只在 wrapper 层改写，直调脚本、测试、CI 或 agent 手动执行会继续绕过别名。实施时要把这些重复的 root 解析收敛到 `wiki_common` 的公共 helper；仅新增 helper 但不替换调用点不算落地。

建议别名 grammar 明确为 `^[A-Za-z][A-Za-z0-9_-]*$`，报错区分三类：alias 未配置、alias 名非法、解析后路径不存在。

### 2. conf 安全拒跑

RFC 里的禁词清单方向正确，但不能用简单 substring 全文扫描。`token`、`password`、`secret` 都可能合法出现在目录名里，例如 `tokenized-features`、`password-policy-notes`、`secretariat`，直接拒跑会误伤路径配置。

建议改成两级策略：

- hard fail：未知 key、凭证形 key、以及高置信凭证值，例如 `ALIBABA_CLOUD_ACCESS_KEY_*`、`ACCESS_KEY_ID=...`、`ACCESS_KEY_SECRET=...`、`LTAI...`、`password\s*[:=]`、`token\s*[:=]`、`bearer\s+...`、`secret\s*[:=]`。
- weak keyword：普通路径 value 中出现 `token/password/secret` 只在 `wiki doctor` 里 warning，不拒跑；如果团队仍想 fail closed，应提供更换 symlink/path alias 的处理建议，而不是让用户把凭证扫描关掉。

这样能守住“凭证不进 conf”，同时避免合法路径被词面误伤。

### 3. `wiki evidence` 转发

`wiki evidence ...` 映射到 `dataworks_client.py evidence ...` 需要 wrapper 注入固定的 `evidence` argv，这和 RFC 里“wrapper 不做参数改写”的表述有轻微冲突。我的判断：允许 wrapper 在 subcommand dispatch 层 prepend 固定子命令是可以接受的，因为它不解析、不改写用户参数，也不碰 `--root`。

如果想更干净，可以新增极薄 `scripts/wiki_evidence.py`，内部调用 `dataworks_client.main(["evidence", *argv])`，这样 wrapper 仍是一律 `exec script "$@"`。但为少加文件，我倾向保留固定 argv 注入，并把 RFC 文案改成“wrapper 不做用户参数解析/重写；仅允许命令映射添加固定 argv 前缀”。

### 4. 双机可行性

本地等价链路可以支持这个设计，但生产云端尚未由我跑通。accepted 前应由有云端 shell 的执行者在 `/home/js_zhangjunwu/llm-wiki/.wiki-cli.conf` 写入：

```ini
python=/home/js_zhangjunwu/miniconda3-py311/bin/python
root.pk=/home/js_zhangjunwu/knowledge-pk
```

然后在云端跑：

```bash
cd /home/js_zhangjunwu/llm-wiki
./bin/wiki doctor
./bin/wiki freshness --root @pk --help
```

通过标准：doctor 不打印任何凭证值，解释器版本正常，`@pk` 解析到 `/home/js_zhangjunwu/knowledge-pk`，`freshness --help` exit 0。

### 给用户的 Decision 建议

建议 Decision 写：`requested changes`。改完 RFC 后再进入 `accepted`，且 `accepted` 前必须补生产云端 smoke 结果。核心方向不需要推翻，主要是把 conf 安全扫描从“禁词全文硬拒”改为“结构化 key 白名单 + 高置信 secret hard fail”，并明确 evidence 的 wrapper 转发语义。
