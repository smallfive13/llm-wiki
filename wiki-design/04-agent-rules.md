# Codex / Claude Code 规则草案

本文件可作为未来 `AGENTS.md`、`CLAUDE.md` 或 Skill 指令的基础。

## 语言

- 默认使用中文。
- 文件名可以使用中文或英文，但应保持稳定、简洁、可搜索。

## 读取规则

回答项目长期知识相关问题前，优先读取：

```text
knowledge/purpose.md
knowledge/index.md
knowledge/overview.md
knowledge/log.md
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

普通问答默认只读。

## 内容规则

- 每个页面尽量带 frontmatter。
- 重要概念使用 `[[wikilink]]`。
- 强结论必须尽量标注来源。
- 不确定内容进入 `wiki/open-questions/`。
- 重要取舍进入 `wiki/decisions/`。
- 多来源综合进入 `wiki/synthesis/`。
- 单个来源摘要进入 `wiki/sources/`。
- 一次重要更新后写入 `log.md`。

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

