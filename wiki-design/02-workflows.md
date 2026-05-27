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

推荐回答引用格式：

```text
正文中的关键判断使用 [1]、[2] 标注。

引用：
- [1] [[页面名]] · wiki/topics/example.md · 支撑：一句话说明
- [2] [[来源摘要]] · wiki/sources/example.md · 原始资料：raw/sources/example.pdf
```

如果回答依赖的是 source 摘要页，尽量同时给出原始资料路径或 `source_id`，方便人工回查。

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
   - **entity alias matching**：对每个识别到的实体名，依次：
     1. 在所有 entity 页的 `id` / H1 标题 / `aliases` 中查找完全匹配，或在 `knowledge/.wiki/normalized_alias_index.json` 中查规范化匹配
     2. 命中 → 复用现有页面（更新 `last_verified`，必要时补充 alias 到正名页）
     3. 未命中但与已有实体 title/alias 编辑距离 < 阈值 → 写入 `review_queue.json type: duplicate`，由人确认
     4. 完全未命中 → 新建 entity 页（默认 `canonical_id: null`，仅当确需薄重定向时建别名页并 `status: redirect`）
   - 判断新增页面、更新页面、冲突点、开放问题
   - 写入 review queue 或展示计划

2. Apply 阶段
   - 写入 wiki/sources/
   - 更新 entities/topics/synthesis/decisions
   - 更新 index/overview/log
   - 刷新图谱和搜索索引
   - 运行 lint
```

Triage 如果需要异步人工处理，应写入 `knowledge/.wiki/review_queue.json`，字段见
[05-contracts-and-next-steps.md](05-contracts-and-next-steps.md)。不要让 Agent 自由发挥 review 字段名。

## 被动 capture（建议 / 自动）

触发：普通对话中 Agent 识别到值得长期保留的片段（设计取舍 / 排查结论 / 明确事实 / 用户决策性发言）。机制定义见 [RFC-003](rfcs/RFC-003-inbox-capture-layer.md) Revision v2 + AGENTS.md "低摩擦 capture" 段。

流程：

```text
检查 knowledge/.wiki/capture_policy.json 是否存在 + auto_capture 开关
  ├── 不存在 / auto_capture: false → 默认"建议 capture"模式
  │     └── 在回答末尾输出：💡 建议 capture：<摘要> · 类型 suggested: <type>
  │           用户回复"存"/"capture" → 写 knowledge/inbox/YYYYMMDD-HHmmss-<slug>.md
  │
  └── auto_capture: true → 检查 exclude_patterns / exclude_paths
        ├── 命中任一 PII 正则 / 排除路径 → 强制降级为"建议 capture"
        └── 未命中 → 直接写 inbox/
              └── 在回答末尾输出：✏️ 已 capture：inbox/<filename> · <摘要>
```

约束：

- 写入路径只能是 `knowledge/inbox/`，**严禁绕过 inbox 直接写 `knowledge/wiki/`**
- 文件命名：`YYYYMMDD-HHmmss-<slug>.md`，秒级时间戳；同秒冲突追加 `-NN`
- 不允许"无声写入"，必须在回答末尾可见报告
- frontmatter 必须含 `id: inb_<ts>_<slug>` / `type: inbox` / `status: draft` 等字段（详见 [05-contracts-and-next-steps.md](05-contracts-and-next-steps.md) "Capture Item Schema"）

## Inbox 晋升

触发语义：

```text
消化 inbox
整理一下 inbox
把 inbox 里的东西梳理进 wiki
```

流程：

```text
列出所有 status: draft 的 inbox 文件（读 knowledge/inbox/*.md）
-> 按主题分组（Agent 建议）
-> 对每组提议：
   - 晋升为 wiki/topics/、wiki/entities/、wiki/decisions/ 等新页面
   - 合并到已有页面（按 **alias matching** 找候选，详见"摄入资料" Triage 的 entity alias matching 子流程；entity 类晋升 / 合并必须先跑 alias matching，不等到下一次 ingest）
   - 丢弃（确认无价值）
-> 用户决策每一项
-> apply：
   - 晋升：移动内容到 wiki/<type>/，新建页面带完整 frontmatter（含 RFC-002 stable id）；
     原 inbox 文件移动到 knowledge/inbox/archive/promoted/<filename>，frontmatter 改 status: promoted
   - 合并：内容并入目标页；原 inbox 文件移到 archive/promoted/，可在目标页 supersedes 中记 inbox id
   - 丢弃：原 inbox 文件移到 archive/dropped/<filename>，frontmatter 改 status: dropped
```

> **跨 RFC 协同**：alias matching 逻辑与"摄入资料" Triage 共享同一实现（同一份 `normalized_alias_index.json` 派生索引）。晋升 entity 类 inbox 时禁止跳过 alias matching，否则 inbox 晋升会绕开 entity 消歧机制，导致 wiki 出现重复 entity 页。

定期触发：建议每周一次，或 `knowledge/inbox/*.md` 文件数超过 `capture_policy.max_inbox_files`（默认 100）时主动提醒。

健康度统计**只计 `knowledge/inbox/*.md`**（即 draft 状态），archive 不计入告警阈值。

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
