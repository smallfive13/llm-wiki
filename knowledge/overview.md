# Overview

> 高层综合：这个知识库目前包含什么、围绕什么主题展开、有哪些重要决策、有哪些开放问题。

本实例是**引擎自带的最小样板**（meta：系统讲自己）。定位见 [Purpose](purpose.md)——**最新权威说明以 `wiki-design/rfcs/` 和 personal 实例为准**，本处仅为样板快照。入口见 [llm-wiki 系统架构](wiki/synthesis/llm-wiki-architecture.md)。

## 主要主题

- [llm-wiki 系统架构](wiki/synthesis/llm-wiki-architecture.md)（synthesis）——分层架构、图谱三层、核心原则、RFC 演进
- [RFC + Task 协作协议](wiki/topics/rfc-task-protocol.md)（topic）——Codex/Claude 决策与执行两层机制
- [知识库 Schema 与页面规则](wiki/topics/wiki-schema-rules.md)（topic）——8 类页面 / 稳定 ID / canonical 边界 / 别名 / profile
- [工具链与使用说明](wiki/topics/toolchain-usage.md)（topic）——wiki-lint / wiki-graph / wiki-eval / 多实例 / capture·ingest

> ⚠ 这 4 页是 2026-05-28 的样板快照，未逐个同步 RFC-006~014 的演进，confidence 均为 `medium`。最新内容看 RFC 正本 / personal 库。

## 重要决策

决策记录在 `wiki-design/rfcs/`（**RFC-001~014 全 accepted**）。设计决策由 RFC 承载；本实例无 `wiki/decisions/` 页。

近期演进：RFC-006 wiki-lint / 007 wiki-graph / 008 schema profile / 009 wikilink 约定 / 010·011 wiki_init / **012 trust signal** / **013 解析鲁棒** / **014 wiki-eval 健康度量化**。

## 开放问题

- 第三层机器图谱（graphify）未落地
- 首次外部资料 ingest 尚未发生（source_manifest 链路待激活）
- 部署形态：单仓多实例 + 外部 vault + git 已落地（personal 验证）；多 repo 分发（submodule / 包）未定
- 本样板实例 4 页未持续同步系统演进（已降级 medium，权威说明转交 RFC + personal）

## 知识健康度（via `wiki_eval`）

| 指标 | 当前值 |
| --- | --- |
| wiki 页面总数 | 4 |
| confidence | 4/4 medium（样板快照） |
| review 背书 | 0（样板不要求背书） |
| sources / inbox draft / review_queue pending | 0 / 0 / 0 |

> health score 由 `wiki_eval --root knowledge` 给出；endorsement 维度对 medium 页不扣分（只盯 high）。
