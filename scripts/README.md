# scripts/

仓库工具脚本。当前包含 wiki-lint / wiki-graph MVP。

## wiki CLI wrapper

实现：见 [`../bin/wiki`](../bin/wiki)
设计：见 [`../wiki-design/rfcs/RFC-022-wiki-cli-wrapper.md`](../wiki-design/rfcs/RFC-022-wiki-cli-wrapper.md)

`bin/wiki` 是薄 wrapper，只做引擎根定位、Python 解释器解析、子命令映射和参数透传；不包含业务逻辑，不改变 `scripts/wiki_*.py` 默认行为。它会从自身位置推出引擎根并 `cd` 过去，因此可在任意 cwd 调用。

```bash
bin/wiki lint --root knowledge --check-only
bin/wiki graph --root knowledge
bin/wiki eval --root knowledge --json
bin/wiki init --root /abs/path/to/instance --sync-schema --force
```

子命令映射：

| wrapper | 等价脚本 |
| --- | --- |
| `wiki lint [args]` | `python scripts/wiki_lint.py [args]` |
| `wiki graph [args]` | `python scripts/wiki_graph.py [args]` |
| `wiki eval [args]` | `python scripts/wiki_eval.py [args]` |
| `wiki init [args]` | `python scripts/wiki_init.py [args]` |

解释器解析顺序：

1. 环境变量 `WIKI_PY`，例如 `export WIKI_PY="/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python"`。
2. 引擎根 `.wiki-cli.conf` 的 `python=` 行。
3. `conda run --no-capture-output -n py312 python`（当 `conda` 在 `PATH` 中）。
4. `python3`。

`bin/wiki` 使用 bash 数组执行：解释器命令先拆成 argv，用户参数始终用 `"$@"` 原样透传，退出码由目标脚本透传。解释器 token 不支持空格；`.wiki-cli.conf` 是每机器配置，已 gitignore。`bin/wiki` 不支持 symlink 安装，推荐把 `<engine>/bin` 加入 `PATH`，或直接调用 `<engine>/bin/wiki`。

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
python3 scripts/wiki_lint.py --scan-wiki-pii  # 加扫 wiki/ 与 raw/dropbox/ 文本 PII（默认扫 inbox/archive）
python3 scripts/wiki_lint.py --ingest-status  # 只读 source_manifest，输出批量 ingest 进度
python3 scripts/wiki_lint.py --check-docs     # 只校验 BASE_SCHEMA 生成文档块
python3 scripts/wiki_lint.py --check-docs --fix # 只修复 GENERATED 块内部
```

退出码：

- `0` = 所有 error 为空（warning 可有）
- `1` = 有 error
- `2` = 配置 / 脚本自身错误

### 覆盖的 lint 范围

来自 RFC-006 v2 范围 #1~#8：

1. **schema 校验** — frontmatter 必填字段 + enum + 日期格式 + hash 格式
2. **ID 唯一性** — `<prefix>_YYYYMMDD_<slug>` 全局唯一 + 派生 `.wiki/id_index.json`
3. **canonical 引用 + supersedes 对称** — 所有 ID 引用可解析 + 双向对称
4. **source 单主键** — `source_id == id == summary_page_id`
5. **entity 别名** — alias 唯一 + canonical_id 不链式 + 派生 `.wiki/normalized_alias_index.json`
6. **inbox 派生** — `.wiki/inbox_index.json`
7. **脱敏扫描** — 按 `capture_policy.hard_redact` / `soft_redact`，兼容 legacy `exclude_patterns`
8. **跨流程一致性** — manifest <-> 摘要页 / review_queue path / inbox archive 状态

`source_manifest.sources[].status` 合法值：`new` / `triaged` / `ingested` / `skipped` / `failed` / `deleted` / `superseded` / `archived`。

普通 lint 的 human/json 输出包含 `ingest_progress`：全量统计各 status，并把 `triaged` 条目列为待 apply 清单（human 默认显示前 20 条）。`--ingest-status` 只读取并基本校验 `raw/source_manifest.json`，不扫描 wiki 页面、不写 `.wiki/` 派生层；退出码只由 manifest 读取 / schema error 决定，`--json --ingest-status` 输出固定 JSON 结构。

`--check-docs` 是独立文档一致性闸：只比对受管 `BEGIN/END GENERATED` 块与 `wiki_common.BASE_SCHEMA` 的生成结果，不运行普通 lint、不扫描 wiki 页面、不写 `.wiki/` 派生层。`--fix` 仅在 `--check-docs` 下有效，只替换已成对存在的生成块内部；缺失、重复或未闭合 marker 不会自动猜位置。

`--scan-wiki-pii` 会把脱敏扫描范围从默认 `inbox/archive` 扩展为 `inbox/archive + wiki + raw/dropbox`。`raw/dropbox/**` 使用二进制黑名单 + UTF-8 解码防御：图片、PDF、Office、压缩包、媒体、编译产物和常见二进制数据文件按扩展名跳过；其它文件（包括代码、SQL、配置、日志、SVG、notebook、无扩展名文本）一律尝试 UTF-8 解码并只跑 `hard_redact` / `soft_redact`，不做 schema / frontmatter 校验。非黑名单文件解码失败时跳过该文件并给 `DROPBOX_DECODE_FAILED` warning，表示红线未验证，需要 maintainer 人工核查。`scanned.dropbox_texts` 只统计成功解码并纳入扫描的 dropbox 文本数，不是 dropbox 全文件数。

后续 RFC 增强：

9. **图引用校验** — wiki 正文图片引用只校验文本路径：跳过代码块和 `http://` / `https://` / `data:` / `mailto:`，本地相对路径必须解析到实例根内且目标存在；图片路径、文件名、相邻描述和 manifest caption/notes 会按 `hard_redact` 做硬底线兜底，工具不读图像素。

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
| `STALE_PAGE` | warning | active 页超过对应 type 的 staleness 阈值未复核 |
| `UNVERIFIED_HIGH` | warning | active 非 source/query 页 `confidence: high` 但 `review: false` |
| `CAPTURE_POLICY_LEGACY` | warning | capture_policy 仍使用 v1 `exclude_patterns` |
| `SOFT_REDACT_HIT` | warning | 内容命中 soft_redact，需按库策略确认或脱敏 |
| `HARD_REDACT_HIT` | error | 内容命中 hard_redact，必须移除密钥/凭证/连接串等硬底线敏感内容 |
| `DROPBOX_DECODE_FAILED` | warning | `raw/dropbox/` 非黑名单文件无法按 UTF-8 解码，已跳过脱敏扫描，需人工核查 |
| `IMAGE_DANGLING` | error | wiki 正文图片引用目标不存在 |
| `IMAGE_PATH_ESCAPE` | error | 图片引用归一化后逃出实例根 |
| `IMAGE_HARD_REDACT` | error | 图片路径、文件名、相邻描述或 manifest 图说明命中 hard_redact |
| `IMAGE_NO_DESCRIPTION` | warning | 图片引用缺少同一行或随后 3 行内的多模态描述 |
| `DOC_BLOCK_DRIFT` | error | `--check-docs` 下生成块内容与 BASE_SCHEMA 不一致 |
| `DOC_BLOCK_MISSING` | error | `--check-docs` 下生成块缺失或未闭合 |
| `DOC_BLOCK_DUPLICATE` | error | `--check-docs` 下生成块重复或嵌套 |
| `PROFILE_SCHEMA_VERSION` | error | `.wiki-profile.json` schema_version 缺失、非整数或超出引擎兼容范围 |
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

`wiki_lint.py` 使用 `wiki_common.BASE_SCHEMA` 作为当前 base schema。实例根可放 `.wiki-profile.json` 叠加只增扩展；缺省没有 profile 时等价纯 base。`BASE_SCHEMA["schema_version"]` 随引擎契约递增，`BASE_SCHEMA["min_compatible_profile_version"]` 表示仍可接受的最老 profile 版本；profile `schema_version` 必须是整数且落在 `[min_compatible_profile_version, schema_version]` 内。低于下界表示需要迁移 profile，高于 base 表示实例 profile 需要更新版引擎。

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

### 度数与知识健康度

graph 节点同时输出三类度数：

- `degree`：既有无向总度数，所有边都给 source/target 各 +1，用于粗略中心性。
- `in_degree`：有向边 target 被指向次数，用作"被依赖度"主指标。
- `out_degree`：有向边 source 指出次数，用作辅助排序。

`source_ref` / `related` / `supersedes` / `wikilink` 贡献 `in_degree` / `out_degree`；`co_source` 只进入总 `degree`，不进入 in/out。`related_ids[]` 按现有实现是当前页到目标页的单向边，不自动补反向边。

`maps/graph-insights.md` 含「知识健康度」段，固定输出：

1. trust 概览：`verified / reviewed-eligible / unverified-high / stale / orphan / total`
2. stale 优先列表：按 `in_degree desc, out_degree desc, id` 排序
3. 未背书应背书页：active 且非 source/query 且 `review: false`，按 `in_degree desc, out_degree desc, id` 排序
4. high-unverified 列表，作为高置信未背书页的高优先子集

orphan/hub 长列表仍由既有 `Isolated Nodes` / `High Centrality Hubs` 段提供，健康度段不重复展开。

### Wikilink 解析

`wiki_graph.py` 保留 Obsidian 兼容写法：正文 wikilink 扫描会先用轻量状态机跳过 fenced / inline code 段，解析 target 时兼容表格转义管道 `\|`，并只取 `|` 前、`#` 前的 target：

- alias 优先：先查 `normalized_alias_index.json`，避免同名 slug/title 覆盖 RFC-004 entity 别名。
- slug 匹配：`[[rfc-task-protocol|RFC + Task 协作协议]]` 按文件 basename 匹配；basename 全局唯一才建边。
- 路径消歧：`[[wiki/topics/rfc-task-protocol|RFC + Task 协作协议]]` 按实例根相对路径去 `.md` 精确匹配。
- ambiguous：basename 重复时不建边，只在 `graph-insights.md` 的 `Ambiguous Wikilinks` 段提示；不写入 `graph-data.json`。
- code 段跳过：`` `[[example]]` `` 与 fenced block 内的 `[[example]]` 不建边、不报 dangling / ambiguous。
- 表格转义：Markdown 表格里的 `[[slug\|显示标题]]` 会还原为 `slug` 解析。

### MVP 不覆盖

- graphify / LightRAG 第三层机器图谱
- 推断边或语义关系类型
- 交互式 HTML 可视化
- 共享 tag、共同邻居、类型亲和、共现等后续计算关系

## wiki-eval

实现：见 [`wiki_eval.py`](wiki_eval.py)
设计：见 [`../wiki-design/rfcs/RFC-014-wiki-eval-health-score.md`](../wiki-design/rfcs/RFC-014-wiki-eval-health-score.md)

`wiki_eval.py` 只读复用 `wiki_lint.evaluate_instance` 和 `wiki_graph.evaluate_instance` 的结构化结果，聚合为 0-100 健康分、四个维度分解、趋势快照和 CI 闸。普通运行不写 `.wiki/*` 或 `maps/*`；只有显式 `--snapshot` 会追加 `<root>/.wiki/eval_history.jsonl`。

### 用法

```bash
python3 scripts/wiki_eval.py
python3 scripts/wiki_eval.py --root /abs/path/to/knowledge --json
python3 scripts/wiki_eval.py --root knowledge --snapshot
python3 scripts/wiki_eval.py --root knowledge --check
```

`--root` 与 wiki-lint / wiki-graph 一致，指向实例根；缺省为引擎仓库下的 `knowledge/`。

### 维度

| 维度 | 公式 |
| --- | --- |
| `integrity` | `clamp_0_100(100 - (100*error_rate + 50*dangling_rate + 50*ambiguous_rate))` |
| `freshness` | `active` 页中非 `STALE_PAGE` 的比例；无 active 页记 100 |
| `endorsement` | 应背书页（`active` 且非 source/query）中 `review: true` 的比例；无应背书页记 100 |
| `connectivity` | `in_degree + out_degree > 0` 的节点比例；空图记 100 |

`integrity` 的三个 rate 都以 `lint.scanned.wiki_pages` 为分母，并各自 `min(1.0, count/page_count)`。总分使用 `BASE_SCHEMA.health_weights`（默认 0.4/0.2/0.2/0.2）加权，统一 `floor(x+0.5)` 四舍五入。空库输出 `score: null`、`status: empty`、`dims: null`。

`--json` 输出额外包含 `review_coverage`：

```json
{
  "eligible": 13,
  "reviewed": 0,
  "percent": 0,
  "unreviewed": [{"id": "top_20260601_example", "type": "topic", "in_degree": 3, "out_degree": 2}]
}
```

`unreviewed` 按 `in_degree desc, out_degree desc, id` 排序。RFC-025 起 `endorsement` 从 high 页背书率改为应背书页复核覆盖率，既有 `.wiki/eval_history.jsonl` 中旧 snapshot 的 `dims.endorsement` 与新值不可直接横向比较。

### 退出码

- 普通运行：能完成评估即 exit 0。
- `--check`：空库 exit 0；非空实例需同时满足 lint error 为 0、graph config error 为 0、score >= `BASE_SCHEMA.health_threshold`（默认 70），否则 exit 1。
- 配置错误由 lint/graph wrapper 收敛为结构化结果，不通过 `sys.exit` 泄漏到 eval。

## wiki-init

实现：见 [`wiki_init.py`](wiki_init.py)
设计：见 [`../wiki-design/rfcs/RFC-010-wiki-init.md`](../wiki-design/rfcs/RFC-010-wiki-init.md)

`wiki_init.py` 用于把任意目录初始化为合法 wiki 实例。它只补缺失骨架，已存在同类型路径会跳过；如果应建目录处已有文件，或应建文件处已有目录，会以 exit 2 报配置错误。它不会覆盖已有 Obsidian 配置、用户笔记或既有 wiki 契约文件。

默认会确保实例根存在 `.obsidian/app.json`，并把 `maps/` 与 `.wiki/` 加入 Obsidian 的 `userIgnoreFilters`，避免派生层进入 Obsidian 图谱。已有 `app.json` 会做安全合并：只对 `userIgnoreFilters` append-missing union，保留已有过滤项顺序和其它键；非法 JSON 或 `userIgnoreFilters` 非数组会 exit 2，不静默跳过也不覆盖。

### 用法

```bash
conda activate py312
python3 scripts/wiki_init.py --root <实例路径> [--profile NAME] [--git] [--git-root <repo路径>]
python3 scripts/wiki_init.py --root <实例路径> --sync-schema [--force]
```

| 选项 | 含义 |
| --- | --- |
| `--root <path>` | 实例根。相对路径按引擎仓库根解析，也可传外部绝对路径 |
| `--profile NAME` | 仅在缺失时创建最小 `.wiki-profile.json`；不会修改已存在 `.wiki-schema.md` |
| `--git` | 确保 `--git-root` 是 git repo，并写入派生层与 `.obsidian/workspace*.json` ignore 规则 |
| `--git-root <path>` | git repo 根；缺省为 `--root`，且 `--root` 必须位于其内 |
| `--sync-schema` | 仅从引擎源头重新同步 `.wiki-schema.md` 镜像文档，然后退出 |
| `--force` | 仅可与 `--sync-schema` 组合；跳过本地修改保护并覆盖 `.wiki-schema.md` |

### 同步 schema 镜像

`--sync-schema` 是独立模式，只要求 `--root` 指向已存在的实例根。它只写 `<root>/.wiki-schema.md` 与 `<root>/.wiki/schema_sync.json`，不创建骨架、不合并 `.obsidian/app.json`、不写 `.gitignore`、不跑 selfcheck，也不创建其它目录。

覆盖前保护：

- `<root>/.wiki-schema.md` 缺失：写入引擎镜像，并写 `.wiki/schema_sync.json`。
- 目标 hash 等于当前引擎模板：不重写 schema；若 sync 元数据缺失或陈旧，会修复 `.wiki/schema_sync.json` 并报告 `action: metadata_repaired`。
- 目标 hash 等于 `.wiki/schema_sync.json.last_synced_engine_sha256`：说明实例自上次同步后未本地改动，可安全覆盖。
- 其它情况：默认拒绝并打印 unified diff，exit 1；确认特化已外移后再加 `--force`。

`.wiki/schema_sync.json` 记录上次同步的引擎模板字节级 sha256，是实例正本审计状态，应该进 Git。

互斥规则：

- `--sync-schema` 不能与 `--profile`、`--git`、`--git-root` 组合；组合使用会 exit 2。
- `--force` 不能脱离 `--sync-schema` 单独使用；否则 exit 2。
- root 不存在、root 不是目录、或 `<root>/.wiki-schema.md` 是目录时 exit 2。

稳定报告行：

```text
old_sha256: <64hex|null>
new_sha256: <64hex>
action: created|replaced|unchanged|metadata_repaired|refused|forced
```

`action` 取值包括 `created` / `replaced` / `unchanged` / `metadata_repaired` / `refused` / `forced`。`action: unchanged` 表示目标内容和 sync 元数据都已经等于引擎源头，脚本不会重写 schema，也不会更新 schema mtime。

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
- `.wiki/capture_policy.json`，默认 v2：`auto_capture: false`、`default_visibility: private`、`hard_redact` 内置硬底线、`soft_redact` 默认软项、`exclude_paths: []`、`max_inbox_files: 100`
- `.obsidian/app.json`，默认创建或合并 `userIgnoreFilters: ["maps/", ".wiki/"]`
- `.ignore`，默认让 rg/fd 跳过 `raw/sources/`、`raw/source_manifest.json`、`maps/`、`.wiki/`，保留 `raw/dropbox/` 可搜；该文件不依赖 `--git`，已有文件只补缺失标准行并保留用户自定义行

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

## wiki-freshness

实现：见 [`wiki_freshness.py`](wiki_freshness.py)
访问层：见 [`dataworks_client.py`](dataworks_client.py)

`wiki_freshness.py` 是在线巡检工具，用 DataWorks 官方 SDK 检查 wiki 页面里的上游代码 / 表结构锚点是否漂移。它与离线工具隔离：`wiki_lint.py`、`wiki_graph.py`、`wiki_eval.py` 不 import DataWorks SDK，也不需要网络或凭证。

### 凭证

只从环境变量读取：

```bash
export ALIBABA_CLOUD_ACCESS_KEY_ID=...
export ALIBABA_CLOUD_ACCESS_KEY_SECRET=...
```

不要把 AK/SK 写入仓库、`.env`、Execution log 或报告输出；本仓 `.gitignore` 显式忽略 `.env`。

### 锚点字段

实例 profile 可把以下字段声明为某些页型的 optional 字段：

- `dataworks_ref`：`file:<project>/<fileId>` 或 `table:<project>.<table>`
- `code_fingerprint`：`sha256:<hex>`，只用于 file ref
- `last_synced`：最近人工确认时间，表锚点用于和 `LastDdlTime` 比较

指纹算法固定为 `dw-code-v1`：`GetFile` 返回的 `Data.File.Content` 先按 UTF-8 / LF / 行尾空白 strip / 整体 strip 规范化；多文件时按 path 排序后拼接，再取 sha256，保存为 `sha256:<hex>`。

表结构锚点使用 `GetMetaTableBasicInfo.Data.LastDdlTime` 与 `last_synced` 比较；列清单来自 `GetMetaTableColumn.Data.ColumnList`，用于报告和后续人工判断。

### 用法

```bash
python3 scripts/wiki_freshness.py --root /abs/path/to/knowledge
python3 scripts/wiki_freshness.py --root /abs/path/to/knowledge --json
python3 scripts/wiki_freshness.py --root /abs/path/to/knowledge --check
python3 scripts/wiki_freshness.py --root /abs/path/to/knowledge --apply-stale
```

默认只读，只输出 report 和 review_queue 建议，不改任何页面。`--apply-stale` 才会把 drift 页写成 `status: stale`，不改 `code_fingerprint`、`last_synced` 或其它字段。

退出码：

- `0`：运行完成；有 drift / auth warning 也返回 0
- `1`：`--check` 下发现 drift
- `2`：参数或实例路径配置错误

## wiki-index

实现：见 [`wiki_index.py`](wiki_index.py)
访问层：见 [`dataworks_client.py`](dataworks_client.py)

`wiki_index.py` 是 DataWorks 专属的在线索引工具，用官方 SDK 拉生产调度节点并生成实例内的受管共享基线。它与离线工具隔离：`wiki_lint.py`、`wiki_graph.py`、`wiki_eval.py` 不 import `wiki_index.py`、`dataworks_client.py` 或 DataWorks SDK。

生产过滤规则：

- 清单源是 `ListNodes(project_env="PROD")`。
- 只保留 `Repeatability == true` 且 `SchedulerType == "NORMAL"` 的节点。
- `SchedulerType == "PAUSE"` 不进入主索引。
- `ListFiles(node_id=<prod node id>)` 用来反查设计态 `FileId`；`CommitStatus` 只作为辅助字段，不作为生产过滤依据。

索引默认写到实例根 `.wiki/dataworks_index.json`。这是受管共享基线，应进 Git，但 `.ignore` 默认屏蔽 `.wiki/`，所以不会进入全文检索。索引不包含代码原文、凭证或客户级样本；只保留路径、输出表、分层、指纹和同步信息。JSON 稳定排序，固定 `index_version`，没有每次运行都会变化的 `generated_at`。

用法：

```bash
python3 scripts/wiki_index.py --root /abs/path/to/knowledge-pk --project-id 96107 --project-identifier pk_data
python3 scripts/wiki_index.py --root /abs/path/to/knowledge-pk --project-id 96107 --project-identifier pk_data --json
python3 scripts/wiki_index.py --root /abs/path/to/knowledge-pk --project-id 96107 --project-identifier pk_data --write
```

默认是 dry-run，只打印将写入的摘要；只有显式 `--write` 才更新 `.wiki/dataworks_index.json`。
