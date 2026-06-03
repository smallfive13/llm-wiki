# Purpose

> 这是 llm-wiki **引擎自带的最小知识库实例**：base schema（无 profile）样板 + 工具自测样本 + 系统自我说明的初版。读者是 clone / 使用本引擎的人，以及维护引擎的 AI。

## 定位与边界

- **是什么**：base schema 下「一个合法实例长什么样」的样板；供 `wiki_lint` / `wiki_graph` / `wiki_eval` 自测；以「系统讲自己」的方式演示 8 类页面写法。
- **不是什么**：**不是系统的权威或最新说明**。最新、完整的设计以 `wiki-design/rfcs/`（RFC 正本）为准；面向人的体系化说明见 personal 实例的系统页（architecture / trust-quality-loop / usage-mechanics / knowledge-organization 等）。
- **收什么**：能体现各类页面、足以自测工具链的最小样本；**不**追外部知识、**不**逐个 RFC 同步。本实例内页面 confidence 一般为 `medium`（样板快照，不声称权威）。

## 长期目标

保持一个「永远合法、可自测」的最小样板。系统能力的真实演进记录在 RFC + personal 库，不在此处重复维护。

---

更新此页时同步更新 `log.md`。
