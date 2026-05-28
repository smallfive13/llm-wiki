# scripts/

仓库工具脚本。当前包含 wiki-lint / wiki-graph MVP。

## wiki-lint

实现：见 [`wiki_lint.py`](wiki_lint.py)
设计：见 [`../wiki-design/rfcs/RFC-006-wiki-lint-mvp.md`](../wiki-design/rfcs/RFC-006-wiki-lint-mvp.md)

### 运行环境

本仓库标准 Python 环境为 **conda `py312`（Python 3.12）**：

```bash
conda activate py312
python -c "import yaml" || pip install pyyaml
```

代码本身兼容 Python 3.9+（向前兼容 3.12），但日常运行、graphify 集成（需 ≥3.10）统一用 `py312`，避免多环境漂移。下文命令在已 `conda activate py312` 的前提下 `python` 与 `python3` 等价。

### 用法

```bash
python3 scripts/wiki_lint.py                  # 校验 + 重建派生层
python3 scripts/wiki_lint.py --check-only     # 只校验，不写派生层
python3 scripts/wiki_lint.py --json           # 机器可读输出
python3 scripts/wiki_lint.py --scan-wiki-pii  # 加扫 wiki/ PII（默认只扫 inbox）
```

退出码：

- `0` = 所有 error 为空（warning 可有）
- `1` = 有 error
- `2` = 配置 / 脚本自身错误

### 覆盖的 lint 范围（8 项）

来自 RFC-006 v2 范围 #1~#8：

1. **schema 校验** — frontmatter 必填字段 + enum + 日期格式 + hash 格式
2. **ID 唯一性** — `<prefix>_YYYYMMDD_<slug>` 全局唯一 + 派生 `.wiki/id_index.json`
3. **canonical 引用 + supersedes 对称** — 所有 ID 引用可解析 + 双向对称
4. **source 单主键** — `source_id == id == summary_page_id`
5. **entity 别名** — alias 唯一 + canonical_id 不链式 + 派生 `.wiki/normalized_alias_index.json`
6. **inbox 派生** — `.wiki/inbox_index.json`
7. **PII 扫描** — 按 `capture_policy.exclude_patterns`
8. **跨流程一致性** — manifest <-> 摘要页 / review_queue path / inbox archive 状态

### 完整 error code 表

| code | 级别 | 含义 |
| --- | --- | --- |
| `MISSING_FIELD` | error | frontmatter 缺必填字段 |
| `EXTRA_FRONTMATTER` | error | 上下文层 md 误带 frontmatter |
| `ID_FORMAT` | error | id 格式不符 / prefix 与 type 不匹配（wiki `<prefix>_YYYYMMDD_<slug>`；inbox `inb_YYYYMMDD_HHmmss_<slug>`） |
| `ID_DUPLICATE` | error | id 在多文件出现 |
| `ENUM_INVALID` | error | 字段值不在合法 enum |
| `DATE_FORMAT` | error | 日期格式不符 |
| `HASH_FORMAT` | error | hash_sha256 不是 64 位小写 hex |
| `JSON_VERSION` | error | JSON 顶层 version != 1 |
| `TYPE_MISMATCH` | error | 字段类型不对 |
| `CANONICAL_DANGLING` | error | 引用 id 找不到 |
| `SUPERSEDES_ASYMMETRY` | error | supersedes / superseded_by 单向缺失 |
| `SOURCE_KEY_MISMATCH` | error | source 主键三者不一致 |
| `SUMMARY_PATH_MISSING` | error | summary_page_path 文件不存在 |
| `ALIAS_CONFLICT` | error | 别名映射多个 canonical_id |
| `CANONICAL_CHAIN` | error | canonical_id 指向非正名页 |
| `REDIRECT_INVALID` | error | status:redirect 但 canonical_id 缺失/无效 |
| `RESOLVED_ACTION_INVALID` | error | resolved_action 来源不合法 |
| `INBOX_STATUS_PATH_MISMATCH` | error | archive 路径与 status 不匹配 |
| `REVIEW_QUEUE_PATH_DRIFT` | warning | evidence.page_path 偏离当前路径 |
| `STATUS_NOT_ARCHIVED` | warning | 被 superseded 但 status 不是 archived |
| `PII_HIT_DRAFT` | error | inbox draft 命中 PII |
| `PII_HIT_ARCHIVE` | warning | inbox archive 命中 PII |
| `PII_HIT_WIKI` | warning | wiki/ 命中 PII（仅 `--scan-wiki-pii`） |

### 派生层

由 lint 生成，**进 `.gitignore`**，可重建：

- `knowledge/.wiki/id_index.json`
- `knowledge/.wiki/normalized_alias_index.json`
- `knowledge/.wiki/inbox_index.json`

派生层写入采用原子模式（同目录唯一临时文件 + `os.replace`），多进程并发安全。

### 调用约定

- ingest Apply / inbox 晋升 apply / 结晶化 完成后**必须**跑 lint，error 时回滚或转入 review_queue
- commit 前建议 `python3 scripts/wiki_lint.py --check-only`
- MVP 不强制 pre-commit hook（留给后续 RFC）

### MVP 不覆盖

见 RFC-006 v2「范围（MVP 不包含）」段：

- auto-fix
- pre-commit / CI 集成
- wiki-context / wiki-graph-refresh
- 健康度评分 / overview.md 自动更新
- wiki-design/rfcs/** / tasks/** 流程层 lint
- hash_sha256 实际值比对

## wiki-graph

实现：见 [`wiki_graph.py`](wiki_graph.py)
设计：见 [`../wiki-design/rfcs/RFC-007-wiki-graph.md`](../wiki-design/rfcs/RFC-007-wiki-graph.md)

### 用法

```bash
python3 scripts/wiki_graph.py         # 生成 knowledge/maps/ 三个派生文件
python3 scripts/wiki_graph.py --json  # 只输出 graph-data，不落盘
```

输出文件：

- `knowledge/maps/graph-data.json`
- `knowledge/maps/knowledge-graph.md`
- `knowledge/maps/graph-insights.md`

### 边类型

MVP 只投影显式 canonical 数据、wikilink，以及由显式 source 字段计算出的共享来源边：

- `source_ref`：`source_ids[]`，`source_kind: canonical`
- `related`：`related_ids[]`，`source_kind: canonical`
- `supersedes`：`supersedes[]`，`source_kind: canonical`
- `wikilink`：正文 `[[...]]` 解析，`source_kind: wikilink`
- `co_source`：两个页面共享 `source_ids[]`，`source_kind: computed`

### MVP 不覆盖

- graphify / LightRAG 第三层机器图谱
- 推断边或语义关系类型
- 交互式 HTML 可视化
- 共享 tag、共同邻居、类型亲和、共现等后续计算关系
