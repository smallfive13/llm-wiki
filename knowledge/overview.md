# Overview

> 高层综合：这个知识库目前包含什么、围绕什么主题展开、有哪些重要决策、有哪些开放问题。

当前知识库的内容是**本系统自身的设计**（meta）。入口见 [llm-wiki 系统架构](wiki/synthesis/llm-wiki-architecture.md)。

## 主要主题

- [llm-wiki 系统架构](wiki/synthesis/llm-wiki-architecture.md)（synthesis）——分层架构、图谱三层、核心原则、RFC 演进
- [RFC + Task 协作协议](wiki/topics/rfc-task-protocol.md)（topic）——Codex/Claude 决策与执行两层机制
- [知识库 Schema 与页面规则](wiki/topics/wiki-schema-rules.md)（topic）——8 类页面 / 稳定 ID / canonical 边界 / 别名 / profile
- [工具链与使用说明](wiki/topics/toolchain-usage.md)（topic）——wiki-lint / wiki-graph / 多实例 / capture·ingest

## 重要决策

决策记录在 `wiki-design/rfcs/`（RFC-001~008 全 accepted）。尚无 `wiki/decisions/` 页（设计决策由 RFC 承载）。

## 开放问题

- 第三层机器图谱（graphify）未落地
- 首次外部资料 ingest 尚未发生
- 部署形态（单仓多实例 vs 多 repo）未定

## 知识健康度

| 指标 | 当前值 |
| --- | --- |
| wiki 页面总数 | 4 |
| sources 摘要数 | 0 |
| inbox draft 数 | 0 |
| 最老 draft 年龄（天） | — |
| review_queue pending 数 | 0 |
| 平均 confidence | high（4/4 high） |

> 健康度可由 `wiki_graph` 的 insights 辅助（孤立 / hub / 社区）。当前手动维护。
