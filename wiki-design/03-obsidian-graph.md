# Obsidian 与知识图谱

## Obsidian 的角色

Obsidian 不作为后端，而作为人工工作台：

- 浏览 Markdown 正本。
- 用 `[[slug|显示文本]]` 形成可视化图谱。
- 用 Backlinks 发现上下文。
- 用 Bases 或 Dataview 类能力做 dashboard。
- 人工调整标题、拆分页面、合并重复主题、处理 review。

Agent 负责摄入、整理、补链、生成 insight；Obsidian 负责人类理解和审查。

## Wikilink 规则

重要概念第一次出现时使用 `[[slug|显示文本]]`。

适合建链接的对象：

- 可以独立成页的概念。
- 需要长期追踪的实体。
- 重要工具、框架、项目。
- 决策、主题、方法论。
- 与当前页面存在明确关系的内容。

不建议链接：

- 普通动词和形容词。
- 只出现一次且没有长期价值的词。
- 为了增加图谱密度而滥用链接。

## Wikilink 约定

wikilink target 使用目标页文件名 slug，而不是 H1 标题：

```markdown
[[rfc-task-protocol|RFC + Task 协作协议]]
[[wiki/topics/rfc-task-protocol|RFC + Task 协作协议]]
```

- `|` 前是解析 target；`|` 后是显示文本。
- target 不含 `/` 时按 basename slug 匹配；全局唯一才建边。
- target 含 `/` 时按实例根相对路径去 `.md` 精确匹配，用于消除跨类型同名 slug。
- basename slug 重复时不建边，`wiki_graph` 只在 `graph-insights.md` 记录 `ambiguous_wikilink`。
- entity 别名仍优先走 `normalized_alias_index.json`；用户原文里的别名不要包成 wikilink，附正名 `[[slug|正名]]`。

## 图谱分层

### 第一层：Obsidian 原生图谱

由 Markdown 中的 `[[slug|显示文本]]` 直接形成。

优点：

- 简单。
- 稳定。
- 人可编辑。
- 与 Obsidian Backlinks 天然兼容。

### 第二层：增强图谱

> 状态（2026-05-28）：第二层 MVP 由 RFC-007 + TASK-007 落地为 scripts/wiki_graph.py，
> 实现 canonical 引用 + wikilink + co_source（共享来源）三类边 + 社区检测 + insights。
> 共享 tag / 共同邻居 / 类型亲和 / 共现 等计算关系留后续增强。第三层（graphify）待后续 RFC。

在 wikilink 之外，额外计算关系：

- 共享来源。
- 共享 tag。
- 共享 related。
- 共同邻居。
- 页面类型亲和。
- 同一 synthesis 或 decision 中共同出现。

这层可以生成：

```text
knowledge/maps/graph-data.json
knowledge/maps/graph-insights.md
```

### 第三层：机器图谱

可选引入 LightRAG 或类似系统抽取实体关系。

用于：

- 多跳问答。
- 实体关系检索。
- 发现隐藏连接。
- 辅助 Agent 召回相关页面。

注意：机器图谱是派生层，不是知识正本。

## 关系类型

人工或半自动标注关系时，可以先用少量稳定类型：

| 关系 | 含义 |
| --- | --- |
| `supports` | 支持某个判断 |
| `contradicts` | 与某个判断冲突 |
| `depends_on` | 依赖某个概念、工具或前提 |
| `compares_with` | 可比较对象 |
| `derived_from` | 来源于某个资料或结论 |
| `updates` | 更新旧结论 |
| `questions` | 指向开放问题 |

## Dashboard 设计

如果使用 Obsidian Bases，可以建立：

```text
dashboards/review.base
dashboards/sources.base
dashboards/entities.base
dashboards/questions.base
dashboards/decisions.base
```

推荐视图：

- 待审核页面：`review = true`
- 低置信度结论：`confidence = low`
- 最近更新：按 `updated` 排序
- 开放问题：`type = open-question`
- 决策记录：`type = decision`
- 来源库：`type = source`
- 孤立页面：由图谱刷新任务生成

## Graph Insights

`graph-insights.md` 可以包含：

- 最大知识社区。
- 孤立节点。
- 高中心性页面。
- 新增强连接。
- 可能重复的主题。
- 需要合并或拆分的页面。
- 缺少来源的关键结论。

Agent 生成 insight 时只提出建议，不应自动大规模重构页面。
