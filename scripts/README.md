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
python3 scripts/wiki_lint.py --root knowledge # 指定实例根；缺省为 knowledge/
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
| `PROFILE_SCHEMA_VERSION` | error | `.wiki-profile.json` schema_version 与引擎不兼容 |
| `PROFILE_PREFIX_FORMAT` | error | profile `id_prefix` 不是 2-5 位小写字母 |
| `PROFILE_PREFIX_COLLISION` | error | profile `id_prefix` 撞 base/inbox/其它 profile prefix |
| `PROFILE_TYPE_COLLISION` | error | profile 新 type 撞 base/其它 profile type |
| `PROFILE_DIR_INVALID` | error | profile type 目录不在 `wiki/` 下、逃逸或冲突 |
| `PROFILE_FIELD_INVALID` | error | profile 字段名或字段结构非法 |
| `PROFILE_FIELD_OVERLAP` | error | 同一 profile type 的 required/optional 字段重复 |
| `PROFILE_CORE_SHADOW` | error | profile 尝试覆盖 core/base 字段 |
| `PROFILE_ENUM_UNKNOWN_FIELD` | error | profile enum 指向未声明的新字段 |
| `PROFILE_OPTFIELD_UNKNOWN_TYPE` | error | profile optional fields 指向未知 type |

### Schema profile 与多实例

`wiki_lint.py` 使用 `wiki_common.BASE_SCHEMA` 作为 RFC-002~007 的冻结 base schema。实例根可放 `.wiki-profile.json` 叠加只增扩展；缺省没有 profile 时等价纯 base。

`--root` 指向实例根，而不是仓库根：

```bash
python3 scripts/wiki_lint.py --root knowledge-bizA --check-only
python3 scripts/wiki_lint.py --root /abs/path/to/knowledge --json
```

实例根应包含 `wiki/`、`raw/`、`inbox/`、`.wiki/`、`maps/` 和上下文 markdown。profile 只能新增页面类型、新字段 enum、某类型额外可选字段；不能改 core 字段、ID 格式、source 单主键、entity alias/redirect、inbox、JSON 契约或派生层规则。

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
python3 scripts/wiki_graph.py --root knowledge-bizA
python3 scripts/wiki_graph.py --json  # 只输出 graph-data，不落盘
```

输出文件：

- `knowledge/maps/graph-data.json`
- `knowledge/maps/knowledge-graph.md`
- `knowledge/maps/graph-insights.md`

`--root` 与 wiki-lint 一致，指向实例根。`--json` 全程只读；普通模式只写 `<root>/maps/*`，永不写 `<root>/.wiki/*`。graph 读取 effective schema 的页面类型集合；base/profile 声明的类型会进图，完全未声明的 type 会跳过并写入 insights。

### 边类型

MVP 只投影显式 canonical 数据、wikilink，以及由显式 source 字段计算出的共享来源边：

- `source_ref`：`source_ids[]`，`source_kind: canonical`
- `related`：`related_ids[]`，`source_kind: canonical`
- `supersedes`：`supersedes[]`，`source_kind: canonical`
- `wikilink`：正文 `[[slug|显示文本]]` 解析，`source_kind: wikilink`
- `co_source`：两个页面共享 `source_ids[]`，`source_kind: computed`

### Wikilink 解析

`wiki_graph.py` 保留 Obsidian 兼容写法，解析时只取 `|` 前、`#` 前的 target：

- alias 优先：先查 `normalized_alias_index.json`，避免同名 slug/title 覆盖 RFC-004 entity 别名。
- slug 匹配：`[[rfc-task-protocol|RFC + Task 协作协议]]` 按文件 basename 匹配；basename 全局唯一才建边。
- 路径消歧：`[[wiki/topics/rfc-task-protocol|RFC + Task 协作协议]]` 按实例根相对路径去 `.md` 精确匹配。
- ambiguous：basename 重复时不建边，只在 `graph-insights.md` 的 `Ambiguous Wikilinks` 段提示；不写入 `graph-data.json`。

### MVP 不覆盖

- graphify / LightRAG 第三层机器图谱
- 推断边或语义关系类型
- 交互式 HTML 可视化
- 共享 tag、共同邻居、类型亲和、共现等后续计算关系

## wiki-init

实现：见 [`wiki_init.py`](wiki_init.py)
设计：见 [`../wiki-design/rfcs/RFC-010-wiki-init.md`](../wiki-design/rfcs/RFC-010-wiki-init.md)

`wiki_init.py` 用于把任意目录初始化为合法 wiki 实例。它只补缺失骨架，已存在同类型路径会跳过；如果应建目录处已有文件，或应建文件处已有目录，会以 exit 2 报配置错误。它不会覆盖已有 Obsidian 配置、用户笔记或既有 wiki 契约文件。

默认会确保实例根存在 `.obsidian/app.json`，并把 `maps/` 与 `.wiki/` 加入 Obsidian 的 `userIgnoreFilters`，避免派生层进入 Obsidian 图谱。已有 `app.json` 会做安全合并：只对 `userIgnoreFilters` append-missing union，保留已有过滤项顺序和其它键；非法 JSON 或 `userIgnoreFilters` 非数组会 exit 2，不静默跳过也不覆盖。

### 用法

```bash
conda activate py312
python3 scripts/wiki_init.py --root <实例路径> [--profile NAME] [--git] [--git-root <repo路径>]
```

| 选项 | 含义 |
| --- | --- |
| `--root <path>` | 实例根。相对路径按引擎仓库根解析，也可传外部绝对路径 |
| `--profile NAME` | 仅在缺失时创建最小 `.wiki-profile.json`；不会修改已存在 `.wiki-schema.md` |
| `--git` | 确保 `--git-root` 是 git repo，并写入派生层与 `.obsidian/workspace*.json` ignore 规则 |
| `--git-root <path>` | git repo 根；缺省为 `--root`，且 `--root` 必须位于其内 |

稳定报告行：

```text
created: N
skipped: M
conflicts: K
git_root: <path|none>
selfcheck: ok|fail
obsidian: created|merged|unchanged
```

退出码：

- `0` = 初始化完成，末尾 `wiki_lint.py --check-only` 自检通过
- `2` = 配置错误、类型冲突、git 失败或自检失败

### 生成内容

- 14 个标准目录及 `.gitkeep`
- `purpose.md` / `index.md` / `overview.md` / `log.md` 通用占位内容，不拷贝当前 `knowledge/` 的 llm-wiki meta；`index.md` / `overview.md` 使用结构化导航骨架且无 frontmatter
- `.wiki-schema.md` 从引擎 `knowledge/.wiki-schema.md` 拷贝，仅在目标缺失时写入
- `raw/source_manifest.json`
- `.wiki/review_queue.json`
- `.wiki/capture_policy.json`，默认 `auto_capture: false`、`exclude_paths: []`、`max_inbox_files: 100`
- `.obsidian/app.json`，默认创建或合并 `userIgnoreFilters: ["maps/", ".wiki/"]`

### git 与自检

`--git` 会逐行追加以下 ignore 规则且保持幂等：

```gitignore
# wiki 派生层（可重建，不进 Git）
**/.wiki/id_index.json
**/.wiki/inbox_index.json
**/.wiki/normalized_alias_index.json
**/.wiki/cache.json
**/.wiki/search_index/
**/.wiki/lightrag/
**/maps/graph-data.json
**/maps/knowledge-graph.md
**/maps/graph-insights.md
# Obsidian 每机器配置
**/.obsidian/workspace.json
**/.obsidian/workspace-mobile.json
```

初始化末尾会从引擎仓库根执行 `wiki_lint.py --root <实例> --check-only`。脚本可从任意 cwd 调用；自检 subprocess 会显式使用引擎仓库作为 cwd。
