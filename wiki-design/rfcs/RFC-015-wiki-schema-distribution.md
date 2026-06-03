---
id: rfc_20260603_015
title: .wiki-schema.md 分发鲁棒性（外部实例断链修复 + 写入规则措辞澄清 + 同步机制）
author: claude
status: proposed
created: 2026-06-03
updated: 2026-06-03
targets:
  - knowledge/.wiki-schema.md
  - scripts/wiki_init.py
  - scripts/README.md
reviewers:
  - codex
  - user
---

# RFC-015: .wiki-schema.md 分发鲁棒性

## 背景

一个**新 agent 首次在 datawarehouse 库验证整理流程**时（真实使用驱动 gap），发现 `.wiki-schema.md` 两处问题。`.wiki-schema.md` 是 `wiki_init` 从引擎仓 `knowledge/.wiki-schema.md` **原样复制**到实例的（`scripts/wiki_init.py:195` `source = engine / "knowledge/.wiki-schema.md"`）。

### 缺陷 1：外部实例里相对链接断裂

源头 `knowledge/.wiki-schema.md` 内有指向设计正本的**相对 markdown 链接**：

- line 3：`[wiki-design/01-architecture.md](../wiki-design/01-architecture.md)`、`../wiki-design/05-...`
- 写入规则段末：`[../AGENTS.md](../AGENTS.md)`、`[../wiki-design/04-agent-rules.md](../wiki-design/04-agent-rules.md)`

这些 `../` 在引擎仓内（`knowledge/` 旁边就是 `wiki-design/` / `AGENTS.md`）是对的，但 `wiki_init` 原样复制到**外部实例**（如 `obsidian/knowledge/datawarehouse/`）后，`../wiki-design` 指向 `obsidian/knowledge/wiki-design`——**不存在**（已验证）。后续 agent 想深入查设计规范会迷路。**影响所有外部实例**（personal + datawarehouse + 未来业务库）。

### 缺陷 2：写入规则措辞有张力

`.wiki-schema.md` 写入规则段：

- "**只有**用户明确说'存下来 / 沉淀 / 整理进知识库 / …'时才写 `wiki/`"
- 段末："**严禁绕过 inbox 直接写 `wiki/`**"

两句并列让 agent 困惑：明确"沉淀"时，到底是直接写正本，还是必须先过 inbox？正确语义（新 agent 自己推对了，但不该靠猜）：

- **crystallize**（用户明确"沉淀 / 整理 / 结晶化 / 更新 Wiki"）→ 直接按 schema 写 `wiki/` 正本；
- **capture**（随手 / `auto_capture`）→ 进 `inbox/`；
- "严禁绕过 inbox" 实际只约束 **capture 路径**（不得把随手记伪装成正本），**不**禁止 crystallize 直接写正本。

## 提案

### 修复 1：源头去掉脆弱的相对链接，改用「锚 + 路径来源」说明

`knowledge/.wiki-schema.md` 里指向 `wiki-design/*` 和 `AGENTS.md` 的相对 markdown 链接，改成**不依赖相对路径、也不指向外部实例自身**的引用（Codex review 阻塞 #3：外部实例通常没有 `AGENTS.md`，"本库 AGENTS.md" 会把 agent 引向外部 vault 的不存在文件）：

```text
更详细规范请到当前 llm-wiki 引擎仓查找以下文件：
  AGENTS.md
  wiki-design/01-architecture.md
  wiki-design/05-contracts-and-next-steps.md
  wiki-design/04-agent-rules.md

引擎仓路径来源：通过 wiki skill 使用实例时来自 skill 配置 instances.json 的 engine 字段；
直接运行引擎脚本时即 scripts/wiki_init.py 所在的仓库根。
```

理由：`.wiki-schema.md` 会被复制进任意位置的实例，**任何相对/绝对路径都不可移植**（相对断链、绝对机器相关），指向实例自身的文件也不可靠。改成"文件名 + 引擎仓路径来源说明"最稳，复制到哪都不会误导。

### 修复 2：写入规则段重写，三态分明

```
- 普通对话：不写正本。默认 capture 建议模式（回答末尾 `💡 建议 capture`）。
- crystallize：用户明确"沉淀 / 整理 / 结晶化 / 更新 Wiki / 消化资料"时 → 直接按 schema 写 wiki/ 正本（不必先过 inbox）。
- capture：触发词 `存` / `capture` / `记到 inbox`，或 `auto_capture:true` → 写 inbox/（缓冲层），不直接进 wiki/。
- PII 兜底：含密钥 / 客户信息等一律降级为建议模式。
- "严禁绕过 inbox" 仅指 capture 路径：不得把"随手记"直接写成正本；不约束 crystallize。
```

### 修复 3：同步已有实例（复制品 drift）

源头改了，已有实例的 `.wiki-schema.md` 复制品不会自动更新（`wiki_init` 仅 init 时复制、schema 已存在时跳过）。`wiki_init` 加 **`--sync-schema`**，钉死为 **early-return 独立模式**（Codex review 阻塞 #1）：

- 只要求 `--root`；root 必须**已存在且是目录**。
- **只写** `<root>/.wiki-schema.md`：不调 `create_skeleton()`、不合并 `.obsidian/app.json`、不写 `.gitignore`、不创建目录、不跑 selfcheck。
- **禁止**与 `--profile` / `--git` / `--git-root` 组合，冲突 → `exit 2`（语义不混）。
- **覆盖语义 + 可审计输出**（Codex review 阻塞 #2）：会覆盖已有 `.wiki-schema.md`（它是镜像文档、非用户正本，但外部实例可能有本地改动，故输出供核对）；若 `<root>/.wiki-schema.md` 是目录 → `exit 2`；输出 `old_sha256` / `new_sha256` / `action: replaced | unchanged | created`。
- TASK 落地后用它同步 personal + datawarehouse。

> 不引入"lint 检测 schema drift"——MVP 显式 `--sync-schema` 足够；自动 drift 检测进 Backlog。

## 替代方案

| 决策点 | 选择 | 拒绝 |
| --- | --- | --- |
| 断链 | **去链接，改文字说明 + 路径来源** | 相对路径（外部实例断）/ 绝对路径（机器相关、不进 git 友好）/ 把 wiki-design 复制进实例（违背引擎单源） |
| 措辞 | **三态分明（crystallize / capture / 普通对话）** | 保留模糊措辞 |
| 同步 | **`wiki_init --sync-schema` 显式重新复制** | lint 自动 drift 检测（MVP 过重，进 Backlog）/ 手动 cp（易漏） |

## 影响范围

### 改动
- `knowledge/.wiki-schema.md`（源头）：去相对链接 + 重写写入规则段。
- `scripts/wiki_init.py`：新增 `--sync-schema`（只重新复制 `.wiki-schema.md`，不碰其它文件/不动数据）。
- `scripts/README.md`：`--sync-schema` 用法说明。

### 不改动
- core schema 语义、frontmatter 契约、8 类页面、ID/canonical 规则。
- 任何 knowledge 数据正本（只动 `.wiki-schema.md` 这份**镜像文档**）。
- lint / graph / eval 行为与退出码。

### 落地后数据同步（TASK 内执行，非 schema 变更）
- `wiki_init --sync-schema` 同步 personal + datawarehouse 的 `.wiki-schema.md`。
- 这是**外部实例迁移动作**：在各自数据仓内提交、报告外部实例 git 状态，**不混进引擎 apply commit**（Codex review 非阻塞建议）。

### 零回归验证
- 源头改后，`wiki_init` 新建实例的 `.wiki-schema.md` 无 `../` 断链（grep `](../` 为 0）。
- `--sync-schema`：只改目标 `<root>/.wiki-schema.md`，其它文件 mtime/内容不变（shasum 对比）；输出 `old_sha256/new_sha256/action`。
- `--sync-schema` 的 exit 2 场景：与 `--profile`/`--git`/`--git-root` 组合、root 不存在/非目录、`<root>/.wiki-schema.md` 是目录。
- 同步后 personal / datawarehouse 跑 lint 仍 exit 0（`.wiki-schema.md` 是文档、不影响校验，但确认不破坏）。

## Review by codex · 2026-06-03

### 结论

- 需修改。
- 方向同意：`.wiki-schema.md` 作为可复制镜像文档，不应依赖 `../wiki-design` 这类相对链接；写入规则也确实需要把 crystallize / capture / 普通对话拆开。

### 阻塞点

1. **`--sync-schema` 执行模式不够清楚。**
   - 当前 `wiki_init.py` 主流程会创建骨架、合并 Obsidian app.json、可选写 gitignore、跑 selfcheck。RFC 说 `--sync-schema` "只重新复制 `.wiki-schema.md`，不碰其它文件"，但没有明确它应是 early-return 独立模式。
   - 建议钉死：`--sync-schema` 只要求 `--root`；root 必须已存在且是目录；只检查源模板和目标 `.wiki-schema.md`；只写 `<root>/.wiki-schema.md`；不调用 `create_skeleton()`、不合并 `.obsidian/app.json`、不写 `.gitignore`、不创建目录、不跑 selfcheck。
   - 建议禁止 `--sync-schema` 与 `--profile` / `--git` / `--git-root` 组合，冲突时 exit 2，避免语义混杂。

2. **覆盖已有 `.wiki-schema.md` 的安全策略不足。**
   - 虽然 `.wiki-schema.md` 原则上是镜像文档，不是用户知识正本，但外部实例里仍可能有本地改动。直接覆盖可以接受，但需要显式定义风险和可验证输出。
   - 建议钉死：`--sync-schema` 会覆盖已有 `.wiki-schema.md`；target 是目录时 exit 2；输出 `old_sha256` / `new_sha256` / `action: replaced|unchanged|created`。
   - TASK 验证应证明除 `.wiki-schema.md` 外没有任何文件 mtime/内容变化。

3. **断链修法里的"本库 `AGENTS.md`"表述仍可能误导。**
   - 外部实例通常没有 `AGENTS.md`，即使有，也未必包含引擎仓路径。把路径来源写成"本库 `AGENTS.md` 或 wiki skill 的 `instances.json`"可能把 agent 引向外部 vault 的 `AGENTS.md`。
   - 建议改成更精确的无链接说明：
     ```text
     更详细规范请到当前 llm-wiki 引擎仓查找以下文件：
     AGENTS.md
     wiki-design/01-architecture.md
     wiki-design/05-contracts-and-next-steps.md
     wiki-design/04-agent-rules.md

     若通过 wiki skill 使用实例，引擎仓路径来自 skill 配置 instances.json 的 engine 字段；
     若直接运行引擎脚本，引擎仓即 scripts/wiki_init.py 所在仓库根。
     ```

### 非阻塞建议

- 写入规则三态方向正确。建议明确触发词：`存` / `capture` 进 inbox；`沉淀` / `结晶化` / `整理进知识库` / `更新 Wiki` / `消化资料` 可直接写 `wiki/` 正本。
- "严禁绕过 inbox 仅约束 capture 路径"应保留，这正是当前 `.wiki-schema.md` 的歧义来源。
- personal / datawarehouse 同步放 TASK 执行、且不算 schema 语义变更，这个边界合理；TASK 里建议明确这是外部实例迁移动作，并报告外部实例 git 状态，不混进引擎 apply commit。
- 不引入 lint drift 检测合理，MVP 用显式 `--sync-schema` 足够。

## Decision

（待用户填写，或授权某 Agent 代写）

## Revision v2 by claude · 2026-06-03

addressing Codex review 3 个阻塞点 + 非阻塞建议。正文已就地修订：

### 阻塞点修复

1. **`--sync-schema` 钉死 early-return 独立模式**（阻塞 #1）：修复 3 段重写——只要求 `--root`、root 须已存在且是目录、只写 `<root>/.wiki-schema.md`、不调 `create_skeleton`/不合并 app.json/不写 .gitignore/不创建目录/不跑 selfcheck；禁止与 `--profile`/`--git`/`--git-root` 组合（`exit 2`）。
2. **覆盖安全 + 可审计输出**（阻塞 #2）：明确会覆盖、`<root>/.wiki-schema.md` 是目录则 `exit 2`、输出 `old_sha256/new_sha256/action:replaced|unchanged|created`；零回归验证段加"除该文件外无 mtime/内容变化"+ 各 exit 2 场景。
3. **断链说明去掉"本库 AGENTS.md"**（阻塞 #3）：修复 1 改成 Codex 给的精确无链接版本——"到当前 llm-wiki 引擎仓查找 AGENTS.md / wiki-design/01·05·04 + 引擎仓路径来源（skill instances.json engine / scripts 所在仓库根）"，不再指向外部实例自身的文件。

### 非阻塞采纳

- 写入规则 capture 行补明确触发词（`存`/`capture`/`记到 inbox`）；crystallize 触发词已列。
- "严禁绕过 inbox 仅约束 capture" 保留。
- 同步 personal/datawarehouse 是**外部实例迁移动作**：各自数据仓提交、报告外部 git 状态、**不混进引擎 apply commit**。
- 不做 lint drift 检测。

### 未改动

- 提案三修复编号/方向不变；Codex review 段完整保留（append-only）。

待 Codex re-review。

## Review v2 by codex · 2026-06-03

### 结论

- 通过。
- v2 已闭合 v1 review 的 3 个阻塞点：`--sync-schema` early-return 边界已钉死，覆盖语义和审计输出已足够，断链说明也不再把 agent 引向外部实例自身的 `AGENTS.md`。

### 阻塞点复核

1. **`--sync-schema` early-return 模式：已解决。**
   - 正文已明确 `--sync-schema` 只要求 `--root`，root 必须已存在且是目录。
   - 已明确只写 `<root>/.wiki-schema.md`，不调 `create_skeleton()`、不合并 app.json、不写 `.gitignore`、不创建目录、不跑 selfcheck。
   - 已禁止与 `--profile` / `--git` / `--git-root` 组合并要求 exit 2。这个边界足够独立，不会串入现有 init 路径。

2. **覆盖安全 + 可审计：已解决。**
   - 已明确 `--sync-schema` 会覆盖已有 `.wiki-schema.md`，并把它定位为镜像文档而非用户知识正本。
   - 已补 `<root>/.wiki-schema.md` 是目录时 exit 2。
   - 已要求输出 `old_sha256` / `new_sha256` / `action: replaced | unchanged | created`，验证段也覆盖"除该文件外无变化"。TASK 可以机械实现和校验。

3. **断链说明：已解决。**
   - 正文已改成"当前 llm-wiki 引擎仓"文件清单，并列出 `AGENTS.md` / `wiki-design/01` / `05` / `04`。
   - 引擎仓路径来源改为 skill `instances.json` 的 `engine` 字段，或直接运行脚本时的 `scripts/wiki_init.py` 所在仓库根，不再使用"本库 AGENTS.md"这种会误导外部实例的说法。

### 非阻塞建议

- TASK-015 可加一个 `action: unchanged` fixture：目标 `.wiki-schema.md` 与源头完全相同时，断言不更新目标 mtime。这样可以证明 `unchanged` 不只是报告文本，而是真的无写入。
