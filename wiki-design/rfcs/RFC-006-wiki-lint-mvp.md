---
id: rfc_20260527_006
title: 引入 wiki-lint MVP，闭合 RFC-002/003/004 的约束
author: claude
status: proposed
created: 2026-05-27
updated: 2026-05-27
targets:
  - scripts/wiki_lint.py
  - AGENTS.md
  - wiki-design/02-workflows.md
  - wiki-design/05-contracts-and-next-steps.md
  - .gitignore
reviewers:
  - codex
  - user
---

# RFC-006: 引入 wiki-lint MVP，闭合 RFC-002/003/004 的约束

## 背景

RFC-001~005 已 accepted + applied，schema 完全冻结，`knowledge/` 骨架已落地（TASK-005）。但有一个明显缺口：**所有 schema 约束目前只靠 Agent 人肉遵守，没有任何机械保障**。

具体而言，下列约束在 schema 层有明确定义，在执行层完全缺失：

| 约束 | 设计来源 | 现状 |
| --- | --- | --- |
| frontmatter 必填字段（id / type / status / ...） | 01-architecture / RFC-002 | 无校验 |
| `id` 格式 `<prefix>_YYYYMMDD_<slug>` 全局唯一 | RFC-002 | 无校验 |
| source 单主键 `source_id == id == summary_page_id` | RFC-002 / 05 | 无校验 |
| `related_ids` / `source_ids` / `supersedes` / `superseded_by` / `canonical_id` 指向真实存在的 id | 01 canonical 边界 | 无校验 |
| `aliases` 在所有 entity 中唯一 + 不与其它 `canonical_id` 冲突 | RFC-004 | 无校验 |
| `status: redirect` 必须有 `canonical_id` 指向有效 entity | RFC-004 | 无校验 |
| inbox `id` 格式 `inb_YYYYMMDD_HHmmss_<slug>` | RFC-003 | 无校验 |
| capture_policy.exclude_patterns 的 PII 正则扫描 | RFC-003 | 无执行体 |
| 派生层文件（id_index / inbox_index / normalized_alias_index）生成 | RFC-002/003/004 | 无生成者 |

结果：

1. **Agent 可能写出违反约束的页面**（如 `source_id != id`、断引 `related_ids`、重复 alias），靠下一个 Agent 阅读时才发现。
2. **ingest / 晋升流程缺关键依赖**：`02-workflows.md` 写"运行 lint"和"按 alias matching 找候选"，但实际没有 `normalized_alias_index.json`，alias matching 无法机械执行。
3. **PII 兜底名义存在实际缺失**：`capture_policy.json.exclude_patterns` 列了 6 条正则，没人在跑。
4. **健康度检查、`overview.md` 健康度表无数据源**：`TASK-005` 自留注释"健康度由 `wiki-lint`（未实现）周期性更新"。

ingest 还没真正跑过任何一次（`knowledge/wiki/` 全空）。在首次 ingest 之前补 lint 比之后补成本低得多——之后补需要回扫存量。

## 提案

引入 **wiki-lint MVP**：一个 Python 脚本 + 派生层生成器 + 报告输出，**只覆盖 RFC-001~005 已定义的约束**，不引入新规则。

### 范围（MVP 包含）

1. **schema 校验**（按 RFC-002 / RFC-003 / RFC-004 写的字段表）
   - `wiki/**/*.md` 的 frontmatter 必填字段、`id` 格式、enum 值
   - `inbox/*.md` 的 frontmatter（含 status / suggested_target_type）
   - 4 个上下文层 md (`purpose/index/overview/log`) 不要 frontmatter（反向校验）

2. **ID 唯一性 + 派生 `id_index.json`**
   - 收集 `wiki/**` 所有 `id`，校验全局唯一
   - 同日同 slug 冲突 → 强制 `_NN` 后缀
   - 输出 `.wiki/id_index.json` = `{ id: path }`

3. **canonical 引用完整性**
   - `source_ids` / `related_ids` / `supersedes` / `superseded_by` / `canonical_id` 中每个 id 都能在 `id_index` 找到
   - `review_queue.json.evidence[].page_id` / `affected_page_ids` 同理
   - `source_manifest.summary_page_id` 同理

4. **source 单主键**
   - 每个 `wiki/sources/*.md`：`frontmatter.id == frontmatter.source_id`
   - 每个 `source_manifest.sources[*]`：`summary_page_id` 为 null 或等于 `source_id`，且等于对应摘要页 `id`
   - `summary_page_path` 文件存在

5. **entity 别名机制 + 派生 `normalized_alias_index.json`**
   - 收集所有 entity 的 `aliases` + 正名 title
   - 规范化（lowercase / 去空格 / 连字符 / 中文全半角 / 复数）
   - 校验唯一性（无冲突 alias 指向多个 canonical_id）
   - `status: redirect` 的 entity 必须有 `canonical_id` 指向真实正名页
   - 输出 `.wiki/normalized_alias_index.json` = `{ normalized: canonical_id }`

6. **inbox 派生 `inbox_index.json`**
   - 扫 `inbox/*.md`（不含 archive），按 RFC-003 schema 输出 draft 计数 + 最近 N 摘要

7. **PII 扫描**
   - 读 `capture_policy.json.exclude_patterns`
   - 扫 `inbox/*.md` 与（可选）`wiki/**/*.md`
   - 命中 → 输出 warning + 文件 + 行号；inbox 命中且 `status: draft` → 升级为 error

8. **跨流程一致性**
   - `summary_page_id` 已生成时其指向的页 `id` 必须存在且 type=source
   - `review_queue.items[].evidence[].page_path` 与 `page_id` 在 id_index 中一致（即 path 是 id 当前路径）

### 范围（MVP 不包含 → 留给后续 RFC）

- `wiki-context` / `wiki-graph-refresh`（05 第三阶段的另两个脚本）
- 自动修复（auto-fix）
- 健康度评分 / `overview.md` 自动更新
- 断链建议、孤立页检测、`review:true` 长期未处理告警（→ Backlog "review queue SLA"）
- pre-commit hook 集成（先手动跑，hook 由后续 RFC 决定）
- CI 集成

### 触发与输出

```bash
# 手动跑（MVP 默认）
python scripts/wiki_lint.py                  # 校验 + 重建派生层
python scripts/wiki_lint.py --check-only     # 只校验，不写派生层
python scripts/wiki_lint.py --json           # 机器可读输出
```

退出码：

- `0` = 所有 error 段为空（warning 可有）
- `1` = 有 error
- `2` = 配置 / 脚本自身错误

输出格式（人类可读，默认）：

```
wiki-lint v0.1.0
================
扫描: knowledge/wiki/ (0 文件) · knowledge/inbox/ (0 文件) · knowledge/raw/ (0 source)

[OK]      schema 校验: 0/0 页通过
[OK]      ID 唯一性: 0 个 id（无冲突）
[OK]      canonical 引用: 0/0 完整
[OK]      source 单主键: 0/0
[OK]      entity 别名: 0 个 alias / 0 个正名
[OK]      inbox: 0 draft
[OK]      PII 扫描: 0 命中

派生层已重建:
  .wiki/id_index.json (0 entries)
  .wiki/normalized_alias_index.json (0 entries)
  .wiki/inbox_index.json (0 drafts)

错误: 0 · 警告: 0
```

### 实现约束

- **语言**：Python 3.9+，**只用标准库** + `PyYAML`（一个依赖，frontmatter 解析）。理由：仓库零依赖现状，Python 在所有 dev / CI 环境都有。
- **文件位置**：`scripts/wiki_lint.py`（单文件起步，未来可拆模块）。
- **配置**：直接读 `knowledge/.wiki/capture_policy.json`，**不**引入新配置文件。
- **退出语义**：error 阻塞（exit 1），warning 通过但提示。
- **幂等**：多次运行结果一致；派生层文件按确定序写入。
- **零网络 / 零 LLM**：纯机械检查，不调用任何模型。
- **可重建**：派生层从 0 重建 ≤ 1 秒（小规模 knowledge）。

### 与现有流程的衔接

| 流程 | lint 怎么衔接 |
| --- | --- |
| ingest Apply 阶段 | apply 完成后**必须**跑 lint，error 时回滚或转入 review_queue |
| inbox 晋升 apply 阶段 | 同上 |
| 结晶化 / crystallize | 同上 |
| capture 写入 inbox | inbox PII 扫描必须 inline 跑（auto_capture: true 路径必经） |
| commit | MVP 不强制 pre-commit hook，但建议人工跑 `wiki-lint --check-only` |

对 02-workflows.md 的具体改动：把所有"运行 lint"句子改为"运行 `python scripts/wiki_lint.py`"。

对 05-contracts-and-next-steps.md 第三阶段的改动：把 `scripts/wiki-lint` 状态从"待实现"标为本 RFC 落地范围；`wiki-context` / `wiki-graph-refresh` 仍待后续 RFC。

对 AGENTS.md 的改动：在「commit 规则」前加一节「lint 触发约束」：

```
## lint 触发约束

任何对 knowledge/wiki/、knowledge/inbox/、knowledge/raw/source_manifest.json、
knowledge/.wiki/review_queue.json、knowledge/.wiki/capture_policy.json 的修改，
commit 前必须跑 `python scripts/wiki_lint.py --check-only` 通过。

派生层文件（.wiki/id_index.json 等）由 lint 自动生成，不需要手动维护，也不进 Git。
```

对 .gitignore 的改动：无（id_index / inbox_index / normalized_alias_index 已在 RFC-002/003/004 加入）。

## 替代方案

### A. 触发方式

| 方案 | 优点 | 缺点 |
| --- | --- | --- |
| **MVP: 手动跑** | 实现最简单；不绑 git hook；不需 CI | 依赖人工 / Agent 自觉 |
| pre-commit hook | 强制保障 | 需要安装步骤；hook 失败有时令人困惑；与 commit 拆分策略冲突 |
| CI 跑 | 不漏 | 需要 GitHub Actions / 类似环境；本仓库尚未配 CI |
| pre-commit + CI 双保险 | 最稳 | 工程量翻倍，MVP 不必要 |

**推荐**：MVP 手动 + AGENTS.md 写明触发约束。pre-commit hook 留给 RFC-007 决定（先看 lint 实际表现）。

### B. 实现语言

| 方案 | 优点 | 缺点 |
| --- | --- | --- |
| **Python + PyYAML** | dev 环境普遍可用；frontmatter 解析成熟；标准库够 | 引入 1 个 pip 依赖 |
| Python 纯标准库（手写 YAML 解析） | 零依赖 | YAML 多行 / 锚点处理复杂，易出 bug |
| Node.js + gray-matter | npm 生态丰富 | 引入 package.json / node_modules 整套 |
| Shell + yq | 极轻 | 多文件聚合校验难写；yq 不一定预装 |

**推荐**：Python + PyYAML。仓库 Mac 环境已有 python3，PyYAML 单依赖可接受。

### C. MVP 范围

| 方案 | 范围 | 评估 |
| --- | --- | --- |
| **本 RFC: 1~8 项全做** | schema + 唯一性 + canonical + source + alias + inbox + PII + 派生 | 闭合所有现有约束 |
| 仅做 1~4 项 | schema + 唯一性 + canonical + source | 留 alias / inbox / PII 后做 |
| 仅做派生层 | 不校验，只生成 index | alias matching 能用，但不挡错 |

**推荐**：1~8 项全做。每项实现成本可控（每项约 30~60 行 Python），分散做反而增加重复扫描成本。

### D. 输出方式

| 方案 | 评估 |
| --- | --- |
| **人类可读 + `--json` 选项** | MVP 推荐：既好读又能机器解析 |
| 只人类可读 | 后续 CI 集成时要改 |
| 只 JSON | 日常跑不友好 |

## 影响范围

### 新增

- `scripts/wiki_lint.py`（约 400~600 行 Python）
- `scripts/` 目录及其 README（说明 MVP 范围 + 用法）

### 改动正本

- `AGENTS.md`：+ 一节「lint 触发约束」
- `wiki-design/02-workflows.md`：把所有"运行 lint"改为具体命令
- `wiki-design/05-contracts-and-next-steps.md`：第三阶段 lint 状态标记落地
- 无需改 `knowledge/.wiki-schema.md`（schema 没变，只是补执行体）

### 不改动

- `.gitignore`（派生层路径已在 RFC-002/003/004 排除）
- `knowledge/` 数据（lint 只读 + 写派生层）
- 任何 RFC-001~005 的 schema 定义

### 依赖

- 引入 PyYAML（dev 依赖，需在 README / scripts/README 中标注 `pip install pyyaml`）。
- 如果团队偏好 zero-dependency，可降级到纯标准库 + 简化 YAML 解析（只支持本仓库实际用到的 frontmatter 子集）。

### 与 Backlog 议题的关系

| Backlog 议题 | 本 RFC 关系 |
| --- | --- |
| evidence 结构化 | 不冲突，未来 evidence schema 一变 lint 跟着改 |
| review queue SLA | 本 RFC 不做 SLA / 长期 pending 检测，留给后续 RFC |
| Wiki 健康度指标 | 本 RFC 提供数据底座（id_index 等），健康度计算留后 |
| 双 Agent 并发写入约束 | 不冲突，lint 校验静态约束，并发是 commit 顺序问题 |
| visibility / PII 字段 | 本 RFC 用现有 exclude_patterns，未来 visibility 字段加入后 lint 跟着扩 |

### 风险

1. **PyYAML 单依赖**：极成熟，风险低，但若团队完全反对外部依赖，需走「纯标准库」替代方案。
2. **MVP 与首次 ingest 时间窗**：lint 应在首次 ingest 之前落地，否则会出现"有数据但无校验"的窗口期。建议 RFC accepted 后立即开 TASK-006 落地。
3. **派生层重建成本**：MVP 是全量扫描，规模 < 1000 页时 < 1 秒，规模上去后再考虑增量。
4. **PII 误报**：当前 6 条正则是初始规则，可能误伤；MVP 命中只是 warning（draft 升 error），可调。
5. **lint 自身 bug**：lint 写错可能阻塞合法写入。MVP 提供 `--check-only` 和明确错误信息缓解；严重时 Agent 可绕过（在 Execution log 中说明原因）。

## Review by codex · YYYY-MM-DD

（待 Codex 追加）

## Decision

（待用户填写或授权 Agent 代写）
