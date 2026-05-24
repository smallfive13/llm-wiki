# Agent 触发工作流

## 基本原则

Codex / Claude Code 是触发器、整理者和审核助手，不应该成为无约束的后台写入程序。

每次写入 Wiki 都应该满足：

- 有明确触发意图。
- 有可审查 diff。
- 有来源、置信度和更新时间。
- 不确定内容进入 `open-questions/`，不要硬写成结论。

## 会话开始

当 Agent 需要理解项目知识时，优先读取：

```text
knowledge/purpose.md
knowledge/index.md
knowledge/overview.md
knowledge/log.md
```

如果用户只是问普通问题，默认只读，不自动更新 Wiki。

## 查询

触发语义：

```text
查一下知识库里关于 X 的内容
基于已有 Wiki 回答 X
这个结论之前有没有讨论过
```

流程：

```text
读 index/overview
-> 搜索相关 wikilink、标题、标签
-> 读取相关页面
-> 必要时查派生索引
-> 回答并标注来源
-> 用户要求沉淀时，再写入 wiki/queries/
```

## 摄入资料

触发语义：

```text
把这篇文章消化进知识库
把这个 PDF 整理进 Wiki
把这些讨论沉淀一下
```

推荐两步摄入：

```text
1. Triage 阶段
   - 识别来源类型
   - 计算 hash
   - 生成来源摘要
   - 判断新增页面、更新页面、冲突点、开放问题
   - 写入 review queue 或展示计划

2. Apply 阶段
   - 写入 wiki/sources/
   - 更新 entities/topics/synthesis/decisions
   - 更新 index/overview/log
   - 刷新图谱和搜索索引
   - 运行 lint
```

## 结晶化

触发语义：

```text
把今天的讨论结晶化
把我们刚才的思路存进知识库
把这段对话整理成长期知识
```

流程：

```text
抽取稳定结论
-> 区分事实、判断、决策、开放问题
-> 写入对应页面
-> 给重要概念加 [[wikilink]]
-> 更新 log
```

结晶化适合沉淀：

- 已达成的设计原则。
- 方案取舍。
- 后续需要验证的问题。
- 可以复用的操作规范。

## 健康检查

触发语义：

```text
检查知识库健康
lint 一下 Wiki
看看有没有孤立页面或过期结论
```

检查项：

- 没有 frontmatter 的页面。
- 没有来源的强结论。
- `review: true` 的页面。
- 孤立节点。
- 断开的 wikilink。
- 重复主题。
- 长时间未更新的 active 页面。
- 同一主题下的冲突结论。

## 图谱刷新

触发语义：

```text
刷新知识图谱
生成 graph insights
看看知识库有哪些社区和空白
```

流程：

```text
扫描 wiki/**/*.md
-> 提取 wikilink、sources、related、tags
-> 生成 graph-data.json
-> 生成 knowledge-graph.md
-> 生成 graph-insights.md
```

## 推荐命令形态

未来可以封装轻量 CLI。

```bash
wiki init
wiki context
wiki query "LightRAG 和 Wiki 怎么结合"
wiki ingest path/to/source.pdf
wiki crystallize path/to/chat.md
wiki lint
wiki graph refresh
wiki review
wiki apply
```

在没有 CLI 前，Agent 可以直接按同样流程修改 Markdown 文件。

