---
name: wiki
description: 把知识按 llm-wiki 标准沉淀进个人或业务知识库（Obsidian vault 实例）。当用户想把内容整理 / 记录 / 沉淀 / 结晶化进知识库、个人库、某个业务库，或说"存进 inbox""capture 一下""消化这篇资料""整理 inbox""存下来供以后参考"时，使用此 skill。即使用户没说"知识库"三字，只要表达"把这个记下来供长期学习 / 参考"的沉淀意图、且涉及一个已配置的库，也应触发。它会：识别目标库 → 按库根 AGENTS.md 与 .wiki-schema.md 写合法页面 → 跑 wiki_lint 校验 + wiki_graph 投影 + 更新 log。不要在普通问答、临时草稿、或与已配置知识库无关的写作里触发。
---

# wiki — 知识库标准写入

把知识按 llm-wiki 引擎的 schema 标准，写进指定的知识库实例（支持个人库 + 多个业务库），并机械校验 + 投影图谱。一套引擎服务多库，库的清单在 `instances.json`。

## 第一步永远是：确定目标库

读本 skill 目录下的 `instances.json`：

- `default` — 用户没指明库时用它
- `engine` — llm-wiki 引擎路径（跑 lint/graph 的地方）
- `python` — 跑工具的 python 命令（已含 conda py312 环境，可直接用）
- `instances` — 每个库的 `root`（vault 路径）/ `label` / `aliases`

识别目标库：

- 用户话里出现某库的 `label` 或 `aliases`（如"风控""个人库"）→ 用那个库
- 用户说"切到 X 库 / 用 X 库" → 设为本会话 active，之后默认它
- 都没提 → 用 `default`
- 库名不在注册表 → **告诉用户"未配置 X 库，在 instances.json 加一行 {root, label, aliases}"，不要瞎写到别处**

确认目标库后记住它的 `root`，后续所有路径都是 `<root>/...`。

## 写入正本

字段、模板和 JSON 契约不在 skill 里镜像维护。写入前按顺序读取：

1. `<root>/AGENTS.md`（如果存在）：目标库的行为规则和团队约定。
2. `<root>/.wiki-schema.md`：目标库的数据契约、页面模板、JSON 契约和引用格式。
3. `<root>/.wiki-profile.json`（如果存在）：目标库额外 schema profile。
4. 引擎仓 `AGENTS.md`：通用 Agent 协作与 lint 规则。

如果 skill 文案与目标库正本冲突，以目标库 `AGENTS.md` 和 `.wiki-schema.md` 为准。

## 三种写入模式

判断用户意图属于哪种，按对应方式写。

### capture（随手存，最轻）

触发："存一下""capture""记到 inbox"。

- 写到 `<root>/inbox/YYYYMMDD-HHmmss-<slug>.md`
- 字段和文件命名按 `<root>/.wiki-schema.md` 的 inbox 段
- 不进 `wiki/`，是缓冲层，以后用户说"整理 inbox"时再晋升
- PII / visibility / capture policy 以 `<root>/.wiki/capture_policy.json` 和 `.wiki-schema.md` 为准；命中硬底线时只建议，不自动写

### crystallize（整理成正式页面）

触发："整理 / 结晶化 / 沉淀进知识库""把这个主题写进去"。

1. 抽稳定结论，区分事实 / 判断 / 决策 / 开放问题
2. 按 `<root>/.wiki-schema.md` 选择页面类型和模板，写到 `<root>/wiki/<dir>/<slug>.md`
3. 写完整 frontmatter、正文、canonical ID 引用和显示层 wikilink
4. 多个相关页用 `related_ids`（canonical，按 ID）互联；`related`（显示层 wikilink）同步

### ingest（摄入 raw 资料）

触发："消化这篇 PDF / 文章""把这份资料整理进来"。

- 资料应在 `<root>/raw/sources/`
- 两步走：
  - **Triage**：算 hash、登记 `raw/source_manifest.json`、抽实体做 alias matching、冲突进 `.wiki/review_queue.json`、给用户审阅计划（先不写 wiki/）
  - **Apply**：写 `wiki/sources/` 摘要页、联动 entities/topics、回填 manifest
- 批量 ingest、子链接、source-gap 和图片规则以 `<root>/.wiki-schema.md` 与引擎 `AGENTS.md` 为准

## 写完必做：校验 + 投影 + log

从 `instances.json` 取 `engine`、`python`、目标库 `root`。优先使用 `<engine>/bin/wiki` 入口；它会自动 `cd` 到引擎根，并把参数原样透传给底层脚本。若 `bin/wiki` 不存在或本机环境不支持，可回退到旧方式：`cd <engine> && <python> scripts/wiki_*.py ...`。回退时**把 `python` 字段直接拼成完整命令跑，不要塞进 shell 变量**——`python` 字段是多词命令（如 `/path/conda run -n py312 python`），在 zsh 下未加引号的变量不会 word-split，`$P scripts/...` 会报 127 command not found。

如需强制指定 wrapper 使用的解释器，可在命令前设置：

```bash
export WIKI_PY="<python>"
```

1. **校验**（必须 exit 0，否则修到过为止 —— 不过 lint 不算完成）：
   ```bash
   <engine>/bin/wiki lint --root <root> --check-only
   # 例：/Users/.../llm-wiki/bin/wiki lint --root /Users/.../personal --check-only
   ```
2. **投影图谱**（重建派生层 + insights）：
   ```bash
   <engine>/bin/wiki graph --root <root>
   ```
3. **更新 `<root>/log.md`**：按时间倒序追加一段，记本次写了哪些页 + lint exit + graph 节点/边数。

> `bin/wiki` 会自动定位并 `cd <engine>`；直接调用底层脚本时仍必须手动 `cd <engine>`，否则 lint / graph 的 repo 检测会失败。`conda run` 首次可能慢/有 stderr 噪音，以最终 `错误: 0` 和 exit 0 为准。

## 报告

写完告诉用户：目标库 + 新建/更新了哪些页 + lint exit 0 + graph 节点/边数 + 0 dangling。派生层（`.wiki/*_index.json`、`maps/*`）由工具自动管，不要手动碰、不要 commit（已 gitignore）。

## git（用户的数据仓，不擅自提交）

实例在用户的 git repo（如 `obsidian/knowledge/`）。写完**不要替用户 commit**——提醒他自己 `git add -A && git commit`，或他明确要求时再代劳。
