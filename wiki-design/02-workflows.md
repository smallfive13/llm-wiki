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

## 实例初始化

触发语义：

```text
初始化一个新的 wiki 实例
把这个 Obsidian vault 接成 llm-wiki 实例
给外部 knowledge 目录补 wiki 骨架
```

流程：

```bash
conda activate py312
python3 scripts/wiki_init.py --root <实例路径> [--profile NAME] [--git] [--git-root <repo路径>]
```

约束：

- `--root` 是实例根；共享引擎仍在 llm-wiki 仓库，lint / graph 通过 `--root` 指向实例。
- init 只补缺失骨架；同类型已存在路径跳过，类型冲突 exit 2，不覆盖 `.obsidian/`、用户 md、已建 schema 或 JSON 契约。
- 上下文层使用通用占位内容，不拷贝当前 `knowledge/` 的 llm-wiki meta。
- `--profile NAME` 只在缺失时创建最小 `.wiki-profile.json`；即使带 profile，也不修改已存在 `.wiki-schema.md`。
- `--git` 要求实例根位于 `--git-root` 内，写入派生层和 `.obsidian/workspace*.json` ignore 规则，并保持幂等。
- init 末尾自动跑 `wiki_lint.py --root <实例> --check-only`；失败时实例视为未就绪。

## Schema 升级 / 分发

触发语义：

```text
同步实例 schema
把外部知识库的 .wiki-schema.md 升级到当前引擎
```

流程：

```bash
conda activate py312
python3 scripts/wiki_init.py --root <实例路径> --sync-schema
```

约束：

- `BASE_SCHEMA["schema_version"]` 每次 schema 契约变更递增；`min_compatible_profile_version` 表示仍接受的最老 profile 版本。profile 低于下界要按 migration note 先迁移，高于 base 要升级引擎。
- `.wiki-schema.md` 是引擎镜像，不写实例特化；实例差异放在 `.wiki-profile.json`、`.wiki/capture_policy.json`、`purpose.md` 或库根 `AGENTS.md`。
- `--sync-schema` 使用 `.wiki/schema_sync.json` 的 `last_synced_engine_sha256` 做覆盖前保护：缺失则写入；已等于引擎模板则 no-op 或修复元数据；等于上次同步 hash 则安全覆盖；否则默认拒绝并打印 diff。
- 确认实例特化已外移后，可显式加 `--force` 首次纳管或强制覆盖。`--force` 只允许和 `--sync-schema` 组合。
- `.wiki/schema_sync.json` 是同步审计状态，应进 Git；它不是可重建派生层。

多实例推荐形态：

```text
llm-wiki/                         # 共享引擎与脚本
obsidian/knowledge/               # 一个 git repo 包多个 vault
  personal/                       # 一个 wiki 实例 / Obsidian vault
  work/                           # 另一个 wiki 实例 / Obsidian vault
```

`personal` 等真实用户 vault 的初始化应在对应 task/evaluation 明确通过后手动触发，不作为普通 apply task 的隐式副作用。

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
- [1] [[example|页面名]] · wiki/topics/example.md · 支撑：一句话说明
- [2] [[source-summary|来源摘要]] · wiki/sources/example.md · 原始资料：raw/sources/example.pdf
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
   - 批量 ingest 时先全量轻扫：只看目录 / 文件名 / 元信息 / 标题 / hash / source_type，允许写粗摘要或占位、alias 候选和 manifest 记录；不要读完所有长正文，不做图片多模态，不写详细 source 正文
   - manifest 新条目先写 `status: triaged`，`summary_page_id: null`，`summary_page_path: null`
   - 富媒体处理：原始图片证据落在 `raw/sources/assets/`，写入 AI 生成语义描述和关键文字摘录；wiki 正文使用相对 `![alt](../../raw/sources/assets/...)` 引用，并在同一行或随后 3 行写紧邻描述
   - 富媒体安全兜底：含 hard_redact 信息的图片不落地；工具只扫图片文件名、路径、相邻描述和 manifest caption/notes，不读图像像素
   - **子链接处理**（写入 AI 约定，不新增工具强制）：
     - 内部文档链接：脱掉 token / 内部 URL，但保留"父文档链向 X 文档"的语义事实；目标值得收时建子 source，正文未抓到时用 `status: draft` + `confidence: low` 占位，父 source 通过 `related_ids` + `related` 关联子 source
     - source-gap 登记：只有与当前 source 知识内容相关、且目标未抓到或未 ingest 时，才建 `wiki/open-questions/oq_YYYYMMDD_<slug>-source-gap.md`；导航、页脚、泛工单入口等弱相关链接不做
     - source-gap 正文必须包含 `## 已知信息` 和 `## 待确认`；`source_ids` 指父 source + 子 source 占位（如有），说明发现处、当前抓到的元信息、缺什么以及为什么没抓到
     - 外部链接：只在正文保留脱敏后的外链说明，不建 source、不跟进
     - 不递归：绝不自动跟着内链 / 外链继续 ingest；用户显式要求补抓某个子文档时，视为一次新的独立 ingest
   - **entity alias matching**：对每个识别到的实体名，依次：
     1. 在所有 entity 页的 `id` / H1 标题 / `aliases` 中查找完全匹配，或在 `knowledge/.wiki/normalized_alias_index.json` 中查规范化匹配
     2. 命中 → 复用现有页面（更新 `last_verified`，必要时补充 alias 到正名页）
     3. 未命中但与已有实体 title/alias 编辑距离 < 阈值 → 写入 `review_queue.json type: duplicate`，由人确认
     4. 完全未命中 → 新建 entity 页（默认 `canonical_id: null`，仅当确需薄重定向时建别名页并 `status: redirect`）
   - 判断新增页面、更新页面、冲突点、开放问题
   - 写入 review queue 或展示计划
   - 运行 `python3 scripts/wiki_lint.py --ingest-status` 查看 apply 清单；`triaged` 是待 apply，`ingested` / `failed` / `skipped` 等只进入计数

2. Apply 阶段
   - 按 apply 清单逐份处理；只有短小且同质的材料可一批最多 3 份，含图、子链接或长正文的材料必须逐份
   - 写入 wiki/sources/
   - 更新 entities/topics/synthesis/decisions
   - 更新 index/overview/log
   - 运行 `python3 scripts/wiki_lint.py`；通过后把对应 manifest 条目改为 `status: ingested`，回填 `summary_page_id` / `summary_page_path`
   - 每份 source 完成后单独 commit；失败则把 manifest 条目改为 `status: failed` 并在 `notes` 记录原因，方便新会话从 lint 进度段续传
   - 刷新图谱和搜索索引
```

补抓 source-gap 时，不从父 source 自动递归；应把待补子文档作为新的 ingest 输入，补齐后把对应 `*-source-gap` open-question 标为 `status: archived`，并在正文记录收尾结果。

Triage 如果需要异步人工处理，应写入 `knowledge/.wiki/review_queue.json`，字段见
[05-contracts-and-next-steps.md](05-contracts-and-next-steps.md)。不要让 Agent 自由发挥 review 字段名。

## 团队贡献

适用于开放给团队成员投料的实例库。目标是让成员能低成本提交原料，同时保持 wiki 正本、manifest 和人工背书由 maintainer 统一控制。

### 角色

| 角色 | 能做 | 不能做 |
| --- | --- | --- |
| 成员（Developer） | 改 `raw/dropbox/**`、提 MR；用 agent 只读答疑 | 改 `wiki/**`、`raw/source_manifest.json`、`.wiki/**`、上下文层（`purpose.md` / `index.md` / `overview.md` / `log.md`）；直推 `main` |
| maintainer | 审批 MR、merge；本机按 RFC-019 ingest；设置 `review: true` 背书；管理 GitLab 权限 | 允许未审核成员直接写正本 |

### 投料约定

- 一份原料一个子目录：`raw/dropbox/YYYYMMDD-<标题>/`。
- 子目录内放原料文件、链接清单、截图和一句话说明（来源链接 / 业务背景 / 想解决的问题）。
- 硬红线在入口即适用：不投 AK/SK、password、token、私钥、密钥、连接串、可复用登录凭证、客户级 PII。实例库可在 `purpose.md` 里写清内部共享边界。
- 成员可以让 agent 代办建分支、放文件、push、开 MR，但 agent 仍只能写 `raw/dropbox/**`。

### GitLab 机制要求

- `main` 必须是 protected branch：Developer 不可直推。
- MR 必须 maintainer approve，且 CI 全绿后才能 merge。
- 实例仓 CI 至少跑三道门禁：`wiki_lint --check-only`、`wiki_lint --scan-wiki-pii`、`wiki_eval --check`。
- 引擎仓对成员只读或 maintainer-only 写，避免成员误改工具链。

### 单 writer ingest

wiki 正本只有一个 writer：maintainer 本机的 ingest 会话。这是当前规模下的设计约束，用来避免 `raw/source_manifest.json` 单文件并发冲突；成员侧并发只落在 `raw/dropbox/` 不同子目录。

maintainer 节奏：

```text
git pull
-> wiki lint --ingest-status 看 manifest 清单
-> 按 RFC-019 triage -> apply 逐份 ingest
-> 每份 source 完成后单独 commit
-> git push
```

dropbox 队列语义：

- `raw/dropbox/` 只保留待处理原料。
- ingest 完成后，把原料从 `raw/dropbox/<dir>/` 移入 `raw/sources/<日期>-<slug>/` 正式归档；图片进入 `raw/sources/assets/`。
- 移位后必须同步更新 `raw/source_manifest.json` 的 `original_path`，并重算或确认 `hash_sha256` 指向正式归档后的原始资料内容。
- manifest 条目通过 lint 后再改为 `status: ingested`，回填 `summary_page_id` / `summary_page_path`。
- 失败时把 manifest 条目改为 `status: failed`，在 `notes` 写清原因；dropbox 原料保留或移入失败归档由实例约定决定，但必须能从 manifest 续传。

扩 maintainer 条件：

- 单 maintainer 吞吐不够时，只指定 1-2 名骨干同装引擎。
- 多 maintainer 仍采用粗串行：ingest 前 `pull`，做完立即 `push`，避免同时编辑 manifest。
- 如果粗串行仍不够，再另开 RFC 评估 manifest 拆文件或更强队列机制，不在当前模式提前建设。

### Dropbox 脱敏扫描

`wiki_lint --scan-wiki-pii` 会扫描 `raw/dropbox/**` 中除已知二进制扩展名外的所有 UTF-8 文本，只跑 `hard_redact` / `soft_redact`，不做 schema/frontmatter 校验。代码、SQL、配置、日志、SVG、notebook 和无扩展名文本都会尝试纳入扫描；图片、PDF、Office、压缩包、媒体、编译产物和常见二进制数据文件按扩展名跳过。非黑名单文件如果无法按 UTF-8 解码，会产生 `DROPBOX_DECODE_FAILED` warning，表示红线未验证，需要 maintainer 人工核查。二进制内容不读像素或文件内部结构，仍由 MR review 和后续 ingest 兜底。

## 代码 → 口径知识

代码 ingest 的目标不是把代码搬进 wiki，而是把代码背后的业务口径、数据落点和维护经验转成可问答的知识。原始代码仍作为 evidence 留在 `raw/sources/**` 或外部系统，wiki 正本只写摘要、判断和可检索索引。

优先沉淀 7 类信息：

1. 口径与定义：指标、业务对象、状态枚举、过滤条件、时间口径。
2. 血缘数据流：输入表、输出表、关键中间层，以及这些对象之间的方向。
3. 关键逻辑：影响结果的 CASE、JOIN、去重、优先级和异常处理，用业务语言描述，不逐行翻译。
4. 设计决策：为什么这样取数、为什么保留或排除某类数据、历史折中。
5. 调度运行特性：任务依赖、刷新频率、产出 SLA、失败后的人工判断入口。
6. 踩坑：历史误用、字段名相似但口径不同、上下游不一致。
7. 适用边界：哪些场景能用、哪些场景必须回源或重新确认。

不要沉淀：

- 完整代码、可复用凭证、连接串、客户级明细样本。
- 逐行代码解释，除非该行就是业务口径的唯一证据。
- 一次性排查 SQL 或临时脚本，除非已经成为长期流程或稳定规则。

### 业务词到物理字段映射

实例可以通过 RFC-008 profile 增加 `asset-mapping` 页型，用来回答"业务词到底落在哪张表/哪个字段"。frontmatter 只放轻量检索字段，例如 `business_concept`、`physical_table`、`physical_field`、`business_aliases`；取值映射、适用条件、caveats 和示例查询写在正文，避免把高变化内容塞进契约字段。

`asset-mapping` 页必须保持 draft/low，直到真实代码或正式文档 ingest 完成并可追溯到 source。示例页只能写占位和示意值，不能伪装成已背书知识。

### 口径传导

同一业务定义只保留一个权威说明点。下游 topic、query、asset-mapping 只增量说明使用方式，并通过 `related_ids` 指回上游定义点；方向统一为"当前页 → 上游定义/来源页"。如果上游定义还没有入库，先建 `open-question` 的 source-gap，正文写"已知信息 + 待确认"，不要把待确认内容写成事实。

同名但口径不同的字段或指标必须显式拆页，或先建 `decision` / `open-question` 澄清命名冲突。禁止因为字段名相同就自动合并。

### 血缘权威性

wiki 中的血缘关系以人工维护的 `related_ids` 为准。fun-cli、数据地图或其它外部血缘工具只能作为 ingest 参考：它们可能漏掉临时表、视图包装、脚本内动态 SQL、手工调度依赖或跨系统口径，不保证完整准确。工具输出不得自动写入 wiki；maintainer 必须核对后再转成页面关系。

### DataWorks freshness 锚点

profile 可为 `asset-mapping`、`topic`、`decision` 增加可选锚点字段：

- `dataworks_ref`：`file:<project>/<fileId>` 或 `table:<project>.<table>`。
- `code_fingerprint`：DataWorks `GetFile` 代码内容按 `dw-code-v1` 规范化后的 `sha256:<hex>`；只用于 file ref。
- `last_synced`：最近人工确认上游代码 / 表结构的时间，表锚点用它与 `GetMetaTableBasicInfo.Data.LastDdlTime` 比较。

`scripts/wiki_freshness.py` 是单独的在线巡检入口，默认只读：扫描锚点、调用 DataWorks SDK、输出 report 和 review_queue 建议，不修改 frontmatter。只有显式 `--apply-stale` 才把 drift 页改成 `status: stale`；`--check` 在发现 drift 时 exit 1，可作为 CI gate。`wiki_lint.py` / `wiki_graph.py` / `wiki_eval.py` 保持离线，不 import DataWorks SDK。

### 答疑回源

Agent 用知识库答疑时默认先信库，不把 DataWorks 当作每问必查的实时后端。是否回源只看内容和页面状态，不看请求来自企微、CLI 还是其它入口。

决策树：

1. 用库不回源：命中页面 `review: true`、状态不是 `stale`，且用户问的是业务语义、定义或口径含义时，直接基于库回答。
2. 回源合并答：命中页面 `status: stale`，或 `review: false` 且问题关键，或用户明确问"当前实现"、"最新"、"线上怎么算"、"代码里怎么写"、"字段从哪来"、"哪张表"、"口径细节"这类需要当前精确事实的问题时，用 `scripts/dataworks_client.py` 查询 DataWorks 当前代码 / 表结构，再和库内结论合并回答。
3. 未命中：只有数仓、表、字段、代码、口径类问题才回源，并登记 `source-gap`；非数仓类问题未命中时，回答"库内无依据"，不调用 SDK。

回源只复用 M3 的 DataWorks 访问层：`dataworks_client.py`，region `ap-southeast-1`，凭证只从环境变量读取。不要新增旁路访问层，不要把 AK/SK、token、连接串写入库、日志或回答。

L3 人控：如果回源发现 DataWorks 当前实现与库内口径不一致，只能把差异标为 maintainer 复核项（例如 review queue 或 source-gap），不得自动改正本、不得直接设置 `review: true`。

### DataWorks 表名反查路由

当问题是"线上表对应哪张离线表"、"某字段从哪层来"、"哪个 DWD/DWB 更适合答业务口径"这类表名路由问题时，先查本地 `.wiki/dataworks_index.json`，不要直接全量扫 DataWorks。入口：

```bash
python3 scripts/wiki_index.py reverse --root <instance-root> --table <table-name>
```

反查输出必须包含贴源 ODS、下游候选、每个候选的层级说明、是否已有知识页、以及调度血缘 caveat。Agent 使用结果时按以下顺序判断：

1. 优先推荐 DWD / DWB 明细层候选，因为它们通常最接近可解释业务口径。
2. DWS / ADS 仍要展示，但说明它们偏汇总或应用层，不默认当作明细口径。
3. 只有 ODS 且无下游时，返回 ODS 溯源结果并说明"未找到下游候选，需人工继续查"。
4. 反查结果只代表 DataWorks 调度血缘，可能漏掉动态 SQL、脚本内临时表或未登记依赖；不得自动写 wiki 正本。

回答出处：

- 依据库内页面时，回答末尾仍列 source 页的 `source_url`。
- 回源补充的当前代码 / 表结构事实必须标注"实时取自 DataWorks，未经人工背书"。
- 如果同一答案同时包含背书库内结论和实时回源事实，应分清两者，不把实时事实伪装成已 review 的长期知识。

## 被动 capture（建议 / 自动）

触发：普通对话中 Agent 识别到值得长期保留的片段（设计取舍 / 排查结论 / 明确事实 / 用户决策性发言）。机制定义见 [RFC-003](rfcs/RFC-003-inbox-capture-layer.md) Revision v2 + AGENTS.md "低摩擦 capture" 段。

流程：

```text
检查 knowledge/.wiki/capture_policy.json 是否存在 + auto_capture 开关
  ├── 不存在 / auto_capture: false → 默认"建议 capture"模式
  │     └── 在回答末尾输出：💡 建议 capture：<摘要> · 类型 suggested: <type>
  │           用户回复"存"/"capture" → 写 knowledge/inbox/YYYYMMDD-HHmmss-<slug>.md
  │
  └── auto_capture: true → 检查 hard_redact / soft_redact / exclude_paths
        ├── 命中 hard_redact / 排除路径 → 强制降级为"建议 capture"
        ├── 命中 soft_redact → 输出 warning 后降级为"建议 capture"
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
-> 给重要概念加 [[slug|wikilink]]
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
- `confidence: high` 但 `review: false` 的 active 页面。
- 长时间未复核的 active 页面（`STALE_PAGE` warning）。
- 孤立节点。
- 断开的 wikilink。
- 重复主题。
- 同一主题下的冲突结论。

## 知识巡检与复核

建议每周或每次批量 ingest 后做一次巡检：

```bash
python3 scripts/wiki_lint.py --root <实例路径> --check-only
python3 scripts/wiki_graph.py --root <实例路径>
python3 scripts/wiki_eval.py --root <实例路径> --json
```

巡检时同时看五类信号：

- lint 的 `STALE_PAGE` / `UNVERIFIED_HIGH` warning。
- `maps/graph-insights.md` 的 stale 优先列表、未背书应背书页、high-unverified 子集。
- `wiki_eval --json` 的 `score`、`dims.endorsement`、`review_coverage`。
- `.wiki/review_queue.json` 中尚未处理的人工复核项。
- 近期高频使用、被多页引用或新答案反复命中的页面。

盲区：

- 新库或大量新页可能没有 stale warning，不能因为 staleness 空跑就判定内容已复核。
- 不要只看总分；`review_coverage.unreviewed` 才是复核排期的主清单。
- `UNVERIFIED_HIGH` 只覆盖 high 页，medium / low 的 active 非 source/query 页仍可能需要背书。

过时或复核结果按四态处理：

- 本地小修后仍有效：编辑页面，更新 `last_verified`，必要时保留 `status: active`。
- 整体已过时且无替代结论：`review: false`，`status: stale`。
- 被新页面或门户取代：`review: false`，`status: archived`，填写 `superseded_by`。
- 人工确认仍有效：设置 `review: true`，更新 `last_verified`。

入库复核分三档：

1. AI 可直接写 `review: false`：source 摘要、普通问答沉淀、低风险操作记录、检索入口页。
2. 写入后必须进 review queue：权限 / 审批 / 账号 / 生产操作口径，指标定义、分层命名、安全隐私、来源冲突、新 source 推翻旧结论。
3. 必须人工确认后才可背书：设置 `review: true`、非 source/query 页标 `confidence: high`、归档 / 合并 / 拆分 / supersede 等结构调整、标准答案口径页。

不变量：`review: true` 表示“当前仍由人背书”，不是“AI 已处理过”。datawarehouse 这类真实生产实例不要为了抬高 score 突击背书，应按未背书清单逐页复核。

## 复核 / 确认

触发语义：

```text
确认这条知识还对
复核 <page_id>
这条已经过时了
这条不太对但先保留
```

流程：

```text
正反馈 / 认可当前内容
-> 设置 review: true
-> 设置 last_verified: 今天

负反馈 / 已过时
-> 先设置 review: false
-> 设置 status: stale

负反馈 / 不太对但仍现役
-> 先设置 review: false
-> 下调 confidence，必要时写入 review_queue type: stale_claim
```

不变量：`review: true` 表示“当前仍背书”，不是“曾经看过”。任何负反馈必须先撤回 `review`。

## 图谱刷新

触发语义：

```text
刷新知识图谱
生成 graph insights
看看知识库有哪些社区和空白
```

流程：

```bash
python3 scripts/wiki_graph.py
```

## 健康度评估

触发语义：

```text
评估知识库健康度
看看当前 wiki score
跑一次健康检查 / CI check
记录一次趋势快照
```

流程：

```bash
python3 scripts/wiki_eval.py --root <实例路径>
python3 scripts/wiki_eval.py --root <实例路径> --json
python3 scripts/wiki_eval.py --root <实例路径> --snapshot
python3 scripts/wiki_eval.py --root <实例路径> --check
```

运行时机：

- 每次维护后可跑 `wiki_eval.py --json`，确认 lint/graph 聚合分数和最弱维度。
- 定期巡检或人工确认后跑 `--snapshot`，把 `.wiki/eval_history.jsonl` 纳入 Git 作为趋势审计。
- CI / release gate 使用 `--check`：非空实例必须 lint error 为 0、graph config error 为 0，且 score 不低于 `BASE_SCHEMA.health_threshold`；空库 exit 0。

## 推荐命令形态

轻量 CLI 入口为引擎仓 `bin/wiki`。把 `<engine>/bin` 加入 `PATH` 后可直接用 `wiki <sub>`；未加入 PATH 时使用 `<engine>/bin/wiki <sub>`。底层 `python scripts/wiki_*.py ...` 仍可直接调用。

```bash
wiki init --root <实例路径>
wiki lint --root <实例路径> --check-only
wiki graph --root <实例路径>
wiki eval --root <实例路径> --json
```

`wiki` 目前只包装 `init` / `lint` / `graph` / `eval` 四个工具命令；上下文读取、query、ingest、crystallize、review/apply 仍按本文件流程由 Agent 读写 Markdown 与 JSON 正本。
