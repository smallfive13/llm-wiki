# Codex / Claude Code 规则草案

本文件可作为未来 `AGENTS.md`、`CLAUDE.md` 或 Skill 指令的基础。

## 与 `.wiki-schema.md` 的关系

- `knowledge/.wiki-schema.md` 定义知识库的数据契约：目录、页面类型、frontmatter、source manifest、review queue、引用格式。
- 根目录 `AGENTS.md` 定义 Agent 行为：什么时候读取、什么时候写入、如何 triage、如何引用、如何保持 Git diff 可审查。
- 本文件是未来根目录 `AGENTS.md` 的草案；不要把字段 schema 只写在这里，否则其他 Agent 和脚本无法稳定复用。

## 语言

- 默认使用中文。
- 文件名可以使用中文或英文，但应保持稳定、简洁、可搜索。

## 读取规则

回答项目长期知识相关问题前，优先读取：

```text
knowledge/.wiki-schema.md
knowledge/purpose.md
knowledge/index.md
knowledge/overview.md
knowledge/log.md
knowledge/.wiki/review_queue.json
knowledge/.wiki/inbox_index.json
```

然后再按标题、tag、wikilink 和全文搜索读取相关页面。

## 写入规则

只有在用户明确表达以下意图时，才写入长期 Wiki：

- “存下来”
- “沉淀”
- “整理进知识库”
- “消化这篇资料”
- “结晶化”
- “更新 Wiki”

**capture 例外**：被动 capture 的写入目标是 `knowledge/inbox/`，不算"长期沉淀"，规则见 [AGENTS.md](../AGENTS.md) "低摩擦 capture" 段和 [02-workflows.md](02-workflows.md) "被动 capture" 段。inbox 写入仍受 `capture_policy.json` 与 PII 兜底约束，不能绕过去直接写 `knowledge/wiki/`。

普通问答默认只读。

## 内容规则

- 每个页面尽量带 frontmatter。
- 重要概念使用 `[[wikilink]]`。
- 强结论必须尽量标注来源。
- 回答时用固定引用格式：正文使用 `[1]`，末尾列出 wiki 页面、source 页面和原始资料路径。
- 不确定内容进入 `wiki/open-questions/`。
- 重要取舍进入 `wiki/decisions/`。
- 多来源综合进入 `wiki/synthesis/`。
- 单个来源摘要进入 `wiki/sources/`。
- 一次重要更新后写入 `log.md`。

## Ingest 子链接规则

摄入 source 时，Agent 必须处理正文里的子链接，但不自动递归。

- 内部文档链接：脱掉 token / 内部 URL，但保留"链向 X 文档"的语义；目标值得收时建子 source，占位 source 用 `status: draft` + `confidence: low`，父 source 用 `related_ids` / `related` 关联子 source。
- source-gap：只有子链接与当前 source 的知识内容相关，且目标未抓到或未 ingest 时，才建 `wiki/open-questions/*-source-gap.md`。正文至少包含 `## 已知信息` 和 `## 待确认`，说明父文档发现处、当前抓到的信息、缺口和补抓条件。
- 弱相关链接：导航、页脚、泛工单入口、广告、站点通用帮助入口等不建 source-gap。
- 外部链接：只保留脱敏后的外链说明，不建 source、不跟进。
- 不递归：不自动跟内链 / 外链继续 ingest；用户明确要求补抓某个子文档时，作为新的独立 ingest 处理。

`review_queue.type: source_gap` 只作为 triage 阶段临时队列或人工审查入口；决定长期保留的缺口应晋升为 `wiki/open-questions/*-source-gap.md`，使其可被图谱、查询和回答阶段看见。

## 审核规则

大规模更新前先输出 triage：

```text
将新增哪些页面
将更新哪些页面
有哪些冲突或低置信度内容
有哪些开放问题
是否需要人工确认
```

小规模结晶化可以直接写入，但必须保持 diff 清晰。

如果用户选择“稍后审阅”或存在不确定冲突，把待办写入 `knowledge/.wiki/review_queue.json`，不要只写在对话里。

## 禁止事项

- 不要把 `.wiki/` 中的索引缓存当作知识正本。
- 不要无来源地重写历史结论。
- 不要为了图谱好看滥加 wikilink。
- 不要一次性重构大量页面，除非用户明确要求。
- 不要把 Qoder Repo Wiki 当成本项目必须实现的功能。

## Git 规则

- 每次知识库更新应可通过 Git diff 审查。
- 不提交无关本地资料，尤其是大型 PDF、Excel、私密笔记。
- 如果需要上传 GitHub，先确认目标仓库、公开/私有属性和需要纳入版本管理的范围。
