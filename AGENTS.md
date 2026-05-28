# Agent 协作规则

本文件是 Codex 和 Claude Code 在本仓库的共同入口规则。除非用户明确给出更高优先级指令，否则两个 Agent 都应先遵守这里的约定。

## 语言

- 默认使用中文回复。
- 面向用户的设计说明、RFC、决策记录优先使用中文。
- 文件名可以使用中文或英文，但应保持稳定、简洁、可搜索。

## 工作边界

- 修改前先查看当前 Git 状态，保留已有未提交改动，不回退他人改动。
- `wiki-design/*.md`、`AGENTS.md`、`knowledge/.wiki-schema.md` 是设计和契约正本，修改时要保持 diff 可审查。
- `.wiki/` 中的索引、缓存和图谱派生文件不是知识正本，除非相关 schema 明确要求纳入版本管理。

## 多 Agent 协作

本仓库由 Codex 和 Claude Code 共同维护。在编辑 `wiki-design/*.md`、`AGENTS.md`、`knowledge/.wiki-schema.md` 这三类正本前，必须：

1. 先去 `wiki-design/rfcs/` 查看是否有 `status != rejected` 的相关 RFC，避免重复提案。
2. 如果是非平凡修改，新建一份 RFC，`status: proposed`，不要直接动正本。
3. 如果只是 typo、措辞、链接修复、格式修复或补全示例，可以直接改，但必须在最终说明或 commit message 里说明改动范围。
4. 看到 `status: proposed` 或 `status: discussing` 的 RFC 时，可以追加 `## Review by <agent> · <date>` 段落，不覆盖原作者内容，不替对方改 status。
5. 只有 `status: accepted` 的 RFC 才能 apply 到 `targets` 列出的正本。改完后回到 RFC 末尾登记 `## Applied in <commit-sha>`；如果本轮没有提交，先登记 `working tree` 和日期。

非平凡修改包括但不限于：

- 新增、删除或重命名 schema 字段。
- 改页面类型、目录结构、source manifest、review queue 或引用格式。
- 改 Agent 工作流、读写权限、协同规则或 lint 规则。
- 新增重要页面类型、重要模板或跨文档契约。

## RFC 规则

- RFC 文件放在 `wiki-design/rfcs/`。
- 文件名使用 `RFC-NNN-<slug>.md`，编号从 001 起递增。
- RFC 必须包含 frontmatter：`id`、`title`、`author`、`status`、`created`、`updated`、`targets`、`reviewers`。
- 正文至少包含四段：`背景`、`提案`、`替代方案`、`影响范围`。
- 另一个 Agent 只追加 review 段落；用户负责最终 `Decision`，或明确授权某个 Agent 代写决策结论。
- status 流转建议为：`proposed -> discussing -> accepted/rejected/superseded`。

## Task 规则

执行类指令（"具体改哪个文件、怎么 commit、按什么顺序"）应通过 `wiki-design/tasks/` 传递，机制定义见 [RFC-005](wiki-design/rfcs/RFC-005-task-channel.md)。

- Task 文件放在 `wiki-design/tasks/`，命名 `TASK-NNN-<slug>.md`。
- Task 必须包含 frontmatter：`id`、`title`、`author`、`executor`、`status`、`type`、`created`、`updated`、`related_rfcs`。
- 正文骨架：`目标 / 前置条件 / 强约束 / 步骤 / 验证 / 完成后报告格式`，一旦定稿不重写。
- executor 完成后追加 `## Execution log by <executor> · <date>`，并推进 `status`。
- evaluator 评估后追加 `## Evaluation by <evaluator> · <date>`，不改动 Execution log。
- 状态机：`pending -> in-progress -> done/failed`；`pending -> cancelled`。不允许 done/failed 之后再翻转，失败修补另开新 task。
- 一份 task 可关联 0 或多个 RFC（`related_rfcs`）；Task 不依赖 RFC。

跨 Agent 执行优先用 task 文件而非 chat-paste。Task 模板和索引见 `wiki-design/tasks/README.md`。

当前 RFC 索引见 `wiki-design/rfcs/README.md`，当前 Task 索引见 `wiki-design/tasks/README.md`。

## 知识库写入规则

- 只有在用户明确表达“存下来”“沉淀”“整理进知识库”“消化这篇资料”“结晶化”“更新 Wiki”等意图时，才写入长期 Wiki。
- 普通问答默认只读。
- 强结论应尽量标注来源；不确定内容进入 `knowledge/wiki/open-questions/` 或 review queue。
- 一次重要知识库更新后，应更新 `knowledge/log.md`。

## lint 触发约束

机制定义见 [RFC-006](wiki-design/rfcs/RFC-006-wiki-lint-mvp.md)。

任何对以下路径的修改，commit 前必须跑 `python3 scripts/wiki_lint.py --check-only` 通过：

- `knowledge/wiki/**`
- `knowledge/inbox/**`
- `knowledge/raw/source_manifest.json`
- `knowledge/.wiki/review_queue.json`
- `knowledge/.wiki/capture_policy.json`

派生层文件（`knowledge/.wiki/id_index.json` / `normalized_alias_index.json` / `inbox_index.json`）由 lint 自动生成，不需要手动维护，也不进 Git。

lint 输出 error 时，应优先修复源数据；确实需要绕过时，必须在 commit message 或 Execution log 段写明绕过原因。

## Commit 规则

- 如果需要提交，commit message 使用清晰 prefix，例如 `[codex]`、`[claude]`、`[rfc-001]`、`[apply rfc-001]`。
- 一个 commit 尽量只覆盖一个 RFC 或一类小修。
- commit message 要能说明动了哪些正本，以及是否对应某个 RFC。

### 低摩擦 capture（capture 缓冲层）

机制定义见 [RFC-003](wiki-design/rfcs/RFC-003-inbox-capture-layer.md) Revision v2。

- **默认**：Agent 识别到值得 capture 的内容时，只在回答末尾**建议** capture，格式：
  ```
  💡 建议 capture：<一句话摘要> · 类型 suggested: <topic|entity|decision|...>
     回复 "存" 或 "capture" 即写入 inbox/。
  ```
- **自动 capture（opt-in）**：仅当项目根目录存在 `knowledge/.wiki/capture_policy.json` 且其中 `auto_capture: true` 时，Agent 才可直接写 `knowledge/inbox/`。
- **自动 capture 也必须可见**：即使开启 auto，每次写入必须在回答末尾输出：
  ```
  ✏️ 已 capture：inbox/<filename> · <一句话摘要>
  ```
  禁止"无声写入"。
- **PII 兜底**：内容包含密钥、token、客户姓名、身份证号、邮箱、电话、明确标记的内部业务信息时，**无论 auto_capture 开关**，一律降级为"建议 capture"模式，不自动写入。规则化的 PII pattern 由 lint 维护，**注意：内置正则只是初始规则，不代表完整 PII 检测**。
- **严禁绕过 inbox 直接写 `knowledge/wiki/`**。

inbox 写入不算"长期沉淀"，仅是 capture 缓冲层。promotion workflow 见 [wiki-design/02-workflows.md](wiki-design/02-workflows.md) "Inbox 晋升" 段。Capture Item / Capture Policy schema 见 [wiki-design/05-contracts-and-next-steps.md](wiki-design/05-contracts-and-next-steps.md) "Capture Item Schema" / "Capture Policy Schema" 段。
