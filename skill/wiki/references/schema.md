# llm-wiki schema 参考入口

本文件不再镜像字段表或页面模板，避免与库根 `.wiki-schema.md` 漂移。写入时请把它当作索引，而不是契约正本。

## 权威正本

按顺序读取目标库文件：

1. `<root>/AGENTS.md`（如果存在）：目标库的行为规则。
2. `<root>/.wiki-schema.md`：页面类型、frontmatter、JSON 契约、引用格式、ingest 规则和最小模板。
3. `<root>/.wiki-profile.json`（如果存在）：base schema 之外的实例扩展。
4. 引擎仓 `AGENTS.md`：通用多 Agent 协作、RFC/TASK、lint 触发规则。

如果本 skill 与上述文件冲突，以目标库 `AGENTS.md` 和 `.wiki-schema.md` 为准。

## 运行信息

运行工具时从 `skill/wiki/instances.json` 取：

- `engine`：llm-wiki 引擎仓路径。
- `python`：完整 Python 命令，通常已包含 conda py312。
- `instances[]`：每个库的 `root`、`label`、`aliases`。

不要把 `python` 塞进 shell 变量；它是多词命令，在 zsh 下会导致 word-splitting 问题。直接拼完整命令：

```bash
cd <engine> && <python> scripts/wiki_lint.py --root <root> --check-only
cd <engine> && <python> scripts/wiki_graph.py --root <root>
```

## 写入流程索引

- capture / crystallize / ingest 三种入口见 `SKILL.md`。
- 字段、模板、capture policy、source manifest、review queue、source-gap、图片引用、答案引用格式见 `<root>/.wiki-schema.md`。
- 批量 ingest 续传先跑 `cd <engine> && <python> scripts/wiki_lint.py --root <root> --ingest-status`，以 manifest status 为单一事实源。
- 写完必须跑 lint，必要时跑 graph，并更新 `<root>/log.md`。
