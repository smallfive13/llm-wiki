# wiki skill — 跨项目安装

把 llm-wiki 的「标准写入」能力装进**另一个 Claude Code 环境**（别的项目 / 机器）。一套引擎服务多库；此目录是 skill 的**可分发副本**（随引擎仓 clone）。

## 文件构成

| 文件 | 可移植性 |
| --- | --- |
| `SKILL.md` | ✅ 零绝对路径，原样用 |
| `references/schema.md` | ✅ 零绝对路径，原样用 |
| `instances.json.template` | ⚠️ 模板——必须按本机路径填后另存为 `instances.json` |

> skill **不自包含**：它驱动的引擎脚本（`scripts/wiki_lint.py` 等）和库数据在本机各自的路径，靠 `instances.json` 串起来。

## 安装步骤

### 1. 前置
目标机器需有：
- **llm-wiki 引擎仓**（clone 本仓库）——提供 `scripts/wiki_lint.py` / `wiki_graph.py` / `wiki_eval.py` / `wiki_init.py`；
- **Python 3.12+ + PyYAML**（`pip install pyyaml`，或 conda 环境）。

### 2. 复制 skill 到 Claude Code skills 目录
```bash
cp -r <引擎仓>/skill/wiki ~/.claude/skills/wiki
```

### 3. 配置 instances.json（关键）
```bash
cp ~/.claude/skills/wiki/instances.json.template ~/.claude/skills/wiki/instances.json
```
编辑 `~/.claude/skills/wiki/instances.json`，把占位换成本机真实值：
- `engine` — 这台机上引擎仓的**绝对路径**；
- `python` — 跑工具的命令（如 `python3` / `/path/conda run -n py312 python` / `<venv>/bin/python`）；
- `instances` — 你的每个库：`root`（vault 绝对路径）/ `label` / `aliases`；并设 `default`。

### 4. （每个库）用 wiki_init 建实例
若库还不存在：
```bash
cd <引擎仓>
<python> scripts/wiki_init.py --root <库的绝对路径>     # 已有 git repo 内则不必 --git
```

### 5. 验证
- 在 Claude Code 里 `/wiki` 能调起；
- `cd <引擎仓> && <python> scripts/wiki_lint.py --root <某库> --check-only` → `exit 0`。

装好后：自然语言「记到 X 库：…」「切到 X 库」即可触发。

## 非 Claude agent（Codex / 其它）
它们**读不了 SKILL.md**。让它们按规范整理知识，靠**库根 `AGENTS.md`**（每个实例放一份规范入口）+ 引擎 `scripts/` + `.wiki-schema.md`，不走本 skill。

## 维护
`SKILL.md` / `references/schema.md` 是引擎单一来源的一部分——引擎仓更新后，各环境重新 `cp` 覆盖即可同步（`instances.json` 是本机配置，不覆盖）。
