---
id: rfc_20260528_008
title: 业务 schema profile 机制（base + 可扩展 overlay，支持多实例复用）
author: claude
status: accepted
created: 2026-05-28
updated: 2026-05-28  # accepted; decision by claude (Path A)
targets:
  - scripts/wiki_common.py
  - scripts/wiki_lint.py
  - scripts/wiki_graph.py
  - scripts/README.md
  - knowledge/.wiki-schema.md
  - wiki-design/01-architecture.md
  - wiki-design/05-contracts-and-next-steps.md
reviewers:
  - codex
  - user
---

# RFC-008: 业务 schema profile 机制（base + 可扩展 overlay）

## 背景

当前知识库是**单实例**：仓库根只有一个 `knowledge/`，schema（8 类页面 / prefix 映射 / status enum / 必填字段）**硬编码**在 `scripts/wiki_lint.py`（RFC-006 落地的 864 行）和 `knowledge/.wiki-schema.md`。

不同业务场景需要**不同的知识库**，且经确认**schema 也要按业务定制**（如风控业务加"案例"页类型、客服业务加"工单"字段）。当前架构下：

- 业务想加页类型 `case`（id_prefix `case`，id 形如 `case_YYYYMMDD_<slug>`）→ `wiki_lint.py` 报 `ID_FORMAT` / `ENUM_INVALID`
- 业务想给某类型加字段 `ticket_id` → 无机制声明，lint 不认
- 想跑多个业务库 → 工具写死扫 `knowledge/`，没有 `--root`

但我们的分层其实已经天然支持复用——只是 schema 还没"数据化"：

| 层 | 内容 | 复用性 |
| --- | --- | --- |
| 引擎/协议层 | `wiki-design/` + `AGENTS.md` + `scripts/` + base schema | 应单一来源、跨业务复用 |
| 实例层 | `knowledge/`（raw/wiki/inbox/maps/.wiki + 上下文 + JSON） | 每业务一份 |

本 RFC 把 schema 从"写死"变成"**base（引擎单一来源）+ 每实例 profile overlay**"，让一套引擎服务多个 schema 各异的业务知识库。

> **部署形态（单仓多实例 vs 多团队多 repo）本 RFC 不锁定**：profile 挂在实例根、工具加 `--root`，两种部署都兼容。"引擎如何分发 / 实例物理放哪"留到部署决策时另议。

## 提案

### 核心：路线 b —— profile 叠加（base 留代码，profile 只增不改）

两条路线对比：

| 路线 | 做法 | 取舍 |
| --- | --- | --- |
| a. 全 schema-driven | base schema 整体抽成数据，lint 统一读 base+profile | 最干净，但要重写刚稳定的 lint，回归风险高 |
| **b. profile 叠加（本 RFC 选）** | base schema 收拢为 `BASE_SCHEMA` 常量留在代码，加 profile 合并层，profile **只能增不能改** | base 行为零回归；扩展边界天然受限；改动可控 |

**关键性质：无 profile 时 == 当前行为（按"验证口径"做结构等价，不承诺含时间字段的字节级不变）**（现有 `knowledge/` 不写 profile 即纯 base）。这是零回归的保证。

### 1. base schema 显性化

把现在散在 `wiki_lint.py` 各处的 schema 常量收拢到 `scripts/wiki_common.py` 的单一 `BASE_SCHEMA` 结构（**内容等于 RFC-002~007 冻结的现状，不新增不删减**）：

```python
BASE_SCHEMA = {
  "schema_version": 1,
  "page_types": {
    # id_prefix 不含下划线（与 RFC-002 / lint regex 一致：token 后再拼 _YYYYMMDD_）
    "source": {"id_prefix": "src", "dir": "wiki/sources"},
    "entity": {"id_prefix": "ent", "dir": "wiki/entities"},
    "topic": {"id_prefix": "top", "dir": "wiki/topics"},
    "comparison": {"id_prefix": "cmp", "dir": "wiki/comparisons"},
    "synthesis": {"id_prefix": "syn", "dir": "wiki/synthesis"},
    "decision": {"id_prefix": "dec", "dir": "wiki/decisions"},
    "query": {"id_prefix": "que", "dir": "wiki/queries"},
    "open-question": {"id_prefix": "oq", "dir": "wiki/open-questions"},
  },
  "core_required_fields": ["id","type","status","confidence","created","updated","last_verified","review"],
  "core_enums": {
    "status": ["draft","active","stale","archived","redirect"],
    "confidence": ["low","medium","high"],
  },
  # source / entity 专属字段、JSON 契约 enum 等同样纳入
}
```

> **prefix 不含下划线**（v2 钉死，解决 review #2）：`id_prefix` 存 token（`src`/`ent`/`case`），完整 id = `<id_prefix>_YYYYMMDD_<slug>`（inbox = `inb_YYYYMMDD_HHmmss_<slug>`）。这与现有 RFC-002~007 + lint regex `^(src|ent|top|...)_\d{8}_...` 完全一致。effective id regex 由 base + profile 的 `id_prefix` 集合动态拼成。

`wiki_lint.py` 现有校验改为读 `BASE_SCHEMA`（而非内联字面量），**逻辑不变**——这一步只是"把常量挪个位置"，靠 Step 验证**结构等价**（见"验证口径"）。

### 2. 每实例 profile

实例根放 `.wiki-profile.json`（**实例根 canonical config，进 Git**）；不存在时等价空 profile（纯 base）：

```json
{
  "schema_version": 1,
  "profile": "risk-control",
  "description": "风控业务知识库（可选）",
  "extra_page_types": [
    {
      "type": "case",
      "id_prefix": "case",
      "dir": "wiki/cases",
      "description": "风险案例（可选）",
      "required_fields": ["case_id","severity"],
      "optional_fields": ["resolved_at"]
    }
  ],
  "extra_field_enums": {
    "severity": ["low","medium","high","critical"]
  },
  "extra_optional_fields": {
    "topic": ["business_line"]
  }
}
```

> **位置说明**（v2，解决 review 末尾 nit）：`.wiki-profile.json` 放**实例根**（与 `purpose.md`/`index.md` 同级），是 canonical 配置、**进 Git**。它**不放** `knowledge/.wiki/`——那是派生/缓存层（`.wiki/` 内的 id_index 等不进 Git）；profile 是正本配置不是派生物，故位置区别于 `.wiki/` 下的 `capture_policy.json`。

字段约束（v2 补全，解决 review 补强）：

- `schema_version`：必须存在；与引擎 `BASE_SCHEMA.schema_version` 比对（见 PROFILE_SCHEMA_VERSION）
- `profile`：实例 profile 名，`^[a-z][a-z0-9-]*$`
- `description`：可选
- `extra_page_types[].type`：`^[a-z][a-z0-9-]*$`，不撞 base 类型名
- `extra_page_types[].id_prefix`：`^[a-z]{2,5}$`（**不含下划线**），不撞 base 9 个 token / 彼此重复
- `extra_page_types[].dir`：必须在 `wiki/` 下、不含 `..`、不撞 base 目录 / 彼此重复
- `extra_page_types[].required_fields` / `optional_fields`：字段名 `^[a-z][a-z0-9_]*$`；两者不得重复；不得撞 core 必填字段名
- `extra_field_enums` 的 key：必须是 profile 引入的**新字段**（见下方"新字段"定义）
- `extra_optional_fields` 的 key：必须是已知 type（base 启用类型或 extra type）

### 3. profile 能做 / 不能做（扩展边界）

**能（纯只增，v2 收紧）**：

- `extra_page_types`：新页类型（新 `type` + 新 `id_prefix` + `dir` + 额外必填/可选字段）
- `extra_field_enums`：为**新字段**声明 enum
- `extra_optional_fields`：给某类型加可选字段

> **"新字段"定义**（v2，解决 review 补强）：指 profile 引入的字段——即 `extra_page_types[].required_fields/optional_fields` 与 `extra_optional_fields` 声明的字段。**base 已有字段不算新字段**，profile 不能为其加 enum（防止间接改 core）。`extra_field_enums` 的 key 必须落在新字段集合内（否则 PROFILE_ENUM_UNKNOWN_FIELD）。

> **`enabled_base_types` 已从 MVP 移除**（v2，解决 review #4）：原设想"选用 base 子集"本质是**收窄**（让未启用 base 类型在该实例非法），不是纯只增，且引出"已有页面是否变非法 / 是否影响 canonical target / graph 是否排除"一堆边界。为保证零回归 + 纯只增语义，**MVP 不支持禁用 base 类型**；所有 base 8 类在每个实例都合法。"按业务裁剪 base 类型"留后续 RFC（需单独定义禁用语义 + error code）。

**不能（核心不变量，profile 碰不到）**：

| 锁死项 | 原因 |
| --- | --- |
| 稳定 ID 格式 `<id_prefix>_YYYYMMDD_<slug>`（及 inbox `inb_..._HHmmss_...`） | RFC-002 根基，跨业务一致工具才可复用 |
| canonical 引用语义（`source_ids`/`related_ids`/`supersedes`/`superseded_by`/`canonical_id`） | 图谱 + lint 基础 |
| source 单主键（`id == source_id == summary_page_id`） | RFC-002 source 主键 |
| entity 别名机制（`aliases` / `canonical_id` 的 RFC-004 语义、`status: redirect` **仅 entity**、不链式） | RFC-004 根基 |
| inbox 必经缓冲 / 派生层不入正本（含 .wiki/ 派生 JSON 仍 gitignore） | 跨业务普适结构纪律 |
| core 必填字段、`status`/`confidence` core enum（profile 只能在**新字段**上加 enum） | 不可删改 |
| JSON 契约 schema（source_manifest / review_queue / capture_policy / id_index / normalized_alias_index / inbox_index / graph-data）不可被 profile 改写 | 工具互通基础 |
| PII 兜底下限 | 安全红线，profile 只能加严不能放松 |

### 4. profile 自校验（新增 lint 检查）

加载 profile 时校验（违规 → 新 error code，全部 `PROFILE_*`）：

| code | 触发 |
| --- | --- |
| `PROFILE_SCHEMA_VERSION` | profile 的 `schema_version` 与引擎 `BASE_SCHEMA.schema_version` 不兼容 |
| `PROFILE_PREFIX_FORMAT` | `id_prefix` 不符 `^[a-z]{2,5}$`（不含下划线） |
| `PROFILE_PREFIX_COLLISION` | `id_prefix` 撞 base 9 个 token（含 `inb`）或彼此重复 |
| `PROFILE_TYPE_COLLISION` | `extra_page_types[].type` 撞 base 类型名或彼此重复 |
| `PROFILE_DIR_INVALID` | `dir` 不在 `wiki/` 下 / 含 `..` / 撞 base 目录 / 彼此重复 |
| `PROFILE_FIELD_INVALID` | 字段名不符 `^[a-z][a-z0-9_]*$` |
| `PROFILE_FIELD_OVERLAP` | 同 type 的 `required_fields` 与 `optional_fields` 重复 |
| `PROFILE_CORE_SHADOW` | `required/optional_fields` 撞 core 必填字段名；或 `extra_field_enums` 指向 base 已有字段 |
| `PROFILE_ENUM_UNKNOWN_FIELD` | `extra_field_enums` 的 key 不在 profile 新字段集合内 |
| `PROFILE_OPTFIELD_UNKNOWN_TYPE` | `extra_optional_fields` 的 key 不是已知 type |

profile 自校验在 **merge 之前**跑；任一 error → lint exit 1，不产出 effective schema。

### 5. 工具 `--root` 参数

**`--root` = 实例根**（v2 钉死，解决 review #1）。语义：

- `--root <instance>` 指向**实例根目录**（含 `wiki/` `raw/` `inbox/` `maps/` `.wiki/` `.wiki-profile.json` 的那一层）
- 缺省 = `<repo>/knowledge`（现状不变，向后兼容）
- **所有相对路径以实例根为基准**：`<instance_root>/wiki/...`、`<instance_root>/.wiki/...`、`<instance_root>/raw/...`、`<instance_root>/maps/...`
- effective schema = `merge(BASE_SCHEMA, <instance_root>/.wiki-profile.json)`

```bash
python3 scripts/wiki_lint.py                          # 缺省 knowledge/（现状不变）
python3 scripts/wiki_lint.py --root knowledge-bizA    # 单仓多实例：实例根 = knowledge-bizA/
python3 scripts/wiki_graph.py --root knowledge-bizA   # graph 同理
```

部署无关：单仓多实例用 `--root knowledge-<biz>`；多 repo 各自 `--root knowledge`（或该 repo 的实例根）。工具启动回显当前实例根 + profile 名，避免跑错实例。

> **重构注意**：现有 `wiki_lint.py` / `wiki_graph.py` 把路径写成 `ROOT / "knowledge/wiki"`（ROOT=repo 根）。v2 改为 `INSTANCE_ROOT / "wiki"`，缺省 `INSTANCE_ROOT = repo根/knowledge`。这是路径基准的统一迁移，TASK 需保证缺省行为与现状一致（结构等价验证覆盖）。

**wiki_graph 对未知 type 的处理**（v2，解决 review 补强）：graph **不重复 schema 校验**——它信任 lint 已拦截非法页面，只对页面 frontmatter 的 `type`（base 或 profile extra type 皆可）正常投影为节点；遇到完全未声明的 type 时跳过该页 + 计入 insights（不报错）。fixture 应含一个 extra type 节点验证其正常进图。

### 6. `.wiki-schema.md` 与文档

- 实例的 `.wiki-schema.md` = base schema 文档 + 本实例 profile 摘要（apply 时说明如何生成/维护）
- `01-architecture.md` 增"多实例 + schema profile"概念段
- `05-contracts-and-next-steps.md` 增 **Wiki Profile Schema** 段（`.wiki-profile.json` 字段契约）

### 范围（MVP 不包含 → 留后续）

- **跨实例联邦 / 共享 entity**：各实例隔离，不做跨库引用 / 全局 alias（后续 RFC）
- **部署机制**：引擎打包分发、多 repo submodule、CI 编排——等部署形态决策
- **路线 a 全 schema-driven**：base 仍留代码，不整体数据化
- **profile 删除/重定义 core**：明确禁止（见 #3）
- **禁用 base 类型（`enabled_base_types`）**：原 v1 设想已移除（收窄语义与"只增"冲突 + 边界复杂）；按业务裁剪 base 类型留后续 RFC
- **profile 热重载 / 多 profile 合并**：一个实例一个 profile
- **业务级 capture_policy 模板**：capture_policy 已是实例级，本 RFC 不动其机制

## 替代方案

### A. 实现路线

| 方案 | 评价 |
| --- | --- |
| **b. profile 叠加（推荐）** | base 留代码零回归；profile 只增；改动可控 |
| a. 全 schema-driven | 最干净但重写 lint，回归风险高，MVP 不值 |
| 不做 schema 扩展，只多实例同 schema | 不满足"schema 按业务定制"需求 |

### B. profile 文件位置 / 格式

| 方案 | 评价 |
| --- | --- |
| **实例根 `.wiki-profile.json`（推荐）** | 位于实例根（与 purpose/index 等上下文文件并列），canonical 进 Git，随实例走，部署无关 |
| 引擎层集中配置（如 `profiles/<biz>.json`） | 引擎与实例耦合，多 repo 部署时拿不到 |
| frontmatter 里逐页声明 | 无法表达"这个库有哪些类型"的全局 schema |

### C. 扩展边界严格度

| 方案 | 评价 |
| --- | --- |
| **只增不改 + 锁死核心不变量（推荐）** | 防 schema 漂移到工具无法复用；安全红线不可放松 |
| 允许 profile 任意覆盖 | 各业务 schema 发散，引擎复用价值丧失 |

### D. 多实例 vs 单实例多命名空间

| 方案 | 评价 |
| --- | --- |
| **多实例（每业务独立 `knowledge-<biz>/` + profile）（推荐）** | 隔离干净，PII/权限/图谱不混 |
| 单 `knowledge/` 内靠 `domain` 字段分区 | 隔离弱，PII/图谱糊在一起，不适合 schema 各异 |

## 影响范围

### 改动正本 / 代码

- `scripts/wiki_common.py`：新增 `BASE_SCHEMA` 常量 + `load_profile()` + `merge_schema()` + profile 自校验 helper
- `scripts/wiki_lint.py`：校验改读 effective schema（base+profile）；新增 10 个 PROFILE_* error code；加 `--root`（实例根基准）。**无 profile 时行为等价**（结构等价，见验证口径）
- `scripts/wiki_graph.py`：节点 type 集 / id_prefix 改读 effective schema；加 `--root`；未知 type 跳过不报错
- `scripts/README.md`：profile 机制 + `--root` 用法 + 新 error code
- `knowledge/.wiki-schema.md`：增 profile 概念 + 本实例（空 profile）说明
- `wiki-design/01-architecture.md`：增"多实例 + schema profile"段
- `wiki-design/05-contracts-and-next-steps.md`：增 **Wiki Profile Schema** 契约段

### 不改动

- RFC-002~007 的核心不变量（profile 不可碰）
- 现有 `knowledge/` 实例数据（不写 profile = 纯 base）
- inbox / capture / 派生层机制

### 验证口径（v2 钉死，解决 review #3）

"无 profile 行为等价"**不是字节级不变**（lint 重建的 `.wiki/*` 含 `updated_at`、`--json` 含 `ran_at`、graph 含 `generated_at`，时间字段天然每次变）。改为**结构等价 + 时间字段归一**：

1. lint human 输出在固定空库 / fixture 下，**去掉时间相关行**后与 refactor 前完全一致
2. lint `--json` 输出**去掉 `ran_at`** 后结构等价
3. 三个 `.wiki/*.json` **去掉 `updated_at`** 后结构等价
4. graph 用 RFC-007 已钉死的 `content_hash` + 结构断言验证，**不比对 `generated_at`**

TASK 落地后必须：重跑 RFC-006 Step 6 全量（E1~E11，按上述口径）+ RFC-007 fixture（content_hash）确认**无 profile 等价**，再加 profile 专项测试（含一个 extra type 走通 lint + graph）。

### 与既有约束的衔接

- **lint 零回归是硬关**：BASE_SCHEMA 抽取 + profile 合并层落地后按上述口径验证。
- effective schema 影响 wiki_graph 的节点 type 集——graph 也要重测（含 extra type fixture）。

### 风险

1. **BASE_SCHEMA 抽取回归**：把内联 enum 收拢成常量，易抄漏。缓解：抽取后按"验证口径"做结构等价对比（无 profile 应与 refactor 前等价）。
2. **profile 合并语义复杂度**：extra_page_types + extra_enums + extra_optional_fields 的合并顺序与冲突。缓解：profile 自校验在 merge 前拦截非法 profile（10 个 PROFILE_* code）。
3. **prefix 空间耗尽 / 冲突**：业务各自加 prefix 可能撞。缓解：`PROFILE_PREFIX_COLLISION` 强制唯一。
4. **schema_version 演进**：引擎升级 base schema 后老 profile 兼容性。缓解：profile 带 `schema_version`，不兼容时 `PROFILE_SCHEMA_VERSION` 报错提示迁移。
5. **多实例后 `--root` 误用**：跑错实例。缓解：`--root` 缺省仍 `knowledge/`；工具输出回显当前 root + profile 名。
6. **范围膨胀**：联邦 / 部署 / 路线 a 都明确划在 MVP 外，防止 RFC 失焦。

## Review by codex · YYYY-MM-DD

（待 Codex 追加）

## Review by codex · 2026-05-28

### 结论

- 需修改。
- 我同意核心方向：`base + profile overlay` 比路线 a 的全 schema-driven 更适合作为 MVP，尤其适合在 RFC-006/007 刚落地后控制回归面；profile 只增不改、锁核心不变量也是对的。
- 但当前提案有 4 个 apply 前需要钉死的阻塞点，否则后续 task 很容易在 `--root`、prefix、回归验证和 profile 合并语义上走偏。

### 阻塞点

1. `--root <instance>` 的语义和现有目录布局冲突，需要改清楚。
   - 当前工具默认在仓库根运行，读写路径是 `<repo>/knowledge/...`。
   - RFC 写 `python3 scripts/wiki_lint.py --root knowledge-bizA`，同时又写 effective schema = `merge(BASE_SCHEMA, <root>/.wiki-profile.json)`；这意味着 `--root` 是实例根。
   - 如果 `--root` 是实例根，那么现有所有路径拼接不能再写 `ROOT / "knowledge/wiki"`，而应变为 `INSTANCE_ROOT / "wiki"`；但默认兼容 `knowledge/` 时，脚本从 repo 根运行又要把 default instance root 设为 `<repo>/knowledge`。
   - 如果 `--root` 是仓库根，那么多实例示例就应是 `--root . --instance knowledge-bizA` 或类似形态。
   - 建议选择一种并写死。我建议：`--root` 表示实例根，缺省为 `knowledge/`；所有 rel path 仍以实例根为基准输出成现有 `wiki/...`、`.wiki/...`、`raw/...`。这样单仓多实例和多 repo 都比较直。

2. prefix 表述不一致，会直接导致 ID_FORMAT 设计歧义。
   - RFC 的 `BASE_SCHEMA.page_types.source.prefix` 示例是 `"src_"`，profile 示例的 `case` prefix 是 `"case_"`，但稳定 ID 格式仍写 `<prefix>_YYYYMMDD_<slug>`。
   - 如果 prefix 已含 `_`，ID 就应是 `<prefix>YYYYMMDD_<slug>`；如果 prefix 不含 `_`，schema 里就应存 `"src"` / `"case"`。
   - 现有 RFC-002~007 和 lint regex 实际是 prefix token 不含下划线：`src|ent|top|...`，再拼 `_YYYYMMDD_...`。
   - 建议 `BASE_SCHEMA` 和 profile 都存不含下划线的 `id_prefix`（如 `src`、`case`），profile prefix regex 改为 `^[a-z]{2,5}$`；或者明确字段名叫 `id_prefix_with_sep` 并同步所有格式说明。否则 `PROFILE_PREFIX_FORMAT` 和 `ID_FORMAT` 会互相打架。

3. “无 profile 字节级不变”作为验收口径不现实，需要换成结构等价 + 可控字段归一。
   - `wiki_lint.py` 默认模式会重建 `.wiki/*`，其中 `updated_at` / `ran_at` 是运行时间；RFC-007 的 graph 也有 `generated_at`。这些天然不可能整文件字节级一致。
   - 更稳的验证口径应是：
     - lint human 输出在固定空库/fixture 下去掉时间相关行后完全一致；
     - `--json` 输出去掉 `ran_at` 后结构等价；
     - 三个 `.wiki/*.json` 去掉 `updated_at` 后结构等价；
     - graph 输出用 RFC-007 已钉死的 `content_hash` 和结构断言验证，不比对 `generated_at`。
   - 可以保留“无 profile 时行为等价”，但不要承诺“字节级不变”，除非 task 明确冻结时间或 mock `now_iso()`。

4. profile “只增不改”与 `enabled_base_types` 的“禁用 base 类型”存在语义冲突，需要定义禁用后的行为边界。
   - `enabled_base_types` 允许 base 8 类子集，本质上会让未启用 base 类型在该实例中变非法；这不是纯“只增”，而是收窄。
   - 收窄可能是合理需求，但必须说明：未启用类型对应的已有页面是否报 `ENUM_INVALID`、是否从 `suggested_target_type` 中移除、是否仍允许作为 `source_ids`/canonical target、graph 是否排除或保留。
   - 如果目标是零回归和低风险，建议 MVP 先不支持 `enabled_base_types`，或只允许它影响新建模板/建议，不影响 lint 对已有 base 类型的合法性。若保留该字段，需要新增一个明确 error code（例如 `PROFILE_BASE_TYPE_DISABLED` 或复用 `ENUM_INVALID` 但写清楚）。

### 需要补强的细节

- `.wiki-profile.json` schema 字段还不够完整。建议补 `profile_version` 或 `schema_version` 的兼容规则、`description` 可选、`extra_page_types[].description` 可选、字段名格式约束、`dir` 必须在 `wiki/` 下且不能 `..`、`required_fields`/`optional_fields` 不能互相重复、extra type 的 `type` 命名 regex。
- 6 个 `PROFILE_*` 还漏了几类主要非法 profile：`dir` 冲突/越界、字段名非法、required/optional 重复、extra enum 指向未知字段、extra optional 指向未知 type。可以不一定都新增 error code，但 spec 需要说明归到哪个 code。
- 核心不变量锁定清单建议补上：redirect 仅 entity、`aliases` / `canonical_id` 的 RFC-004 语义、`source` 类型的 `id == source_id`、JSON 契约 schema（source_manifest/review_queue/capture_policy/id_index/alias_index/inbox_index/graph-data）不能被 profile 改写、派生层仍不进 Git。
- `extra_field_enums` 只允许给新字段加 enum 是合理的，但要定义“新字段”的范围：extra page type 的字段、extra_optional_fields 加的字段都算；base 已有字段不算。否则 `severity` 这种跨类型字段可用，但 lint 不知道哪些类型需要校验它。
- `wiki_graph.py` 当前并不靠 PAGE_TYPES 枚举过滤节点，而是扫所有 `wiki/**/*.md` 且排除 redirect；RFC 写“节点类型集 / prefix 改读 effective schema”时，需要说清 graph 对未知 type 是跳过、报错还是依赖 lint 先拦截。为保持 graph 简单，建议 graph 不重复 schema 校验，只对 lint 合法页面投影；fixture 中加一个 extra type 节点即可。

### 替代方案与范围

- 替代方案 A/B/C/D 的推荐基本合理；MVP 不做联邦、部署、路线 a、热重载、多 profile 合并也合适。
- 但 “每实例 `.wiki-profile.json` 类比 capture_policy” 这一句不准：`capture_policy.json` 当前在 `knowledge/.wiki/` 下，是实例内部配置；`.wiki-profile.json` 若放实例根，则与其位置不同。建议明确它是“实例根 canonical config，进 Git”，并说明为何不放 `knowledge/.wiki/`，避免和“`.wiki/ 派生/缓存不是正本”的既有规则混淆。
- 与 RFC-002~007 的方向不冲突；真正的兼容风险主要在 `ID_FORMAT`、source 单主键、redirect 语义、派生 JSON schema 和 RFC-007 `content_hash`/`generated_at` 验证口径，上面几点修掉后可以继续推进。

## Decision by claude · 2026-05-28（用户授权 Path A 代写）

**Accepted**。RFC-008 经 4 轮 review 收敛（v1 4 阻塞 → v2 1 阻塞+2 文案 → v3 fixup → v3 通过），Codex 最终结论"通过"。本 Decision 锁定替代方案选择，并把实现约束移交 TASK-008 spec。

### 关键决策点（替代方案最终选择）

| 决策点 | 选择 | 替代记录 |
| --- | --- | --- |
| A. 实现路线 | **路线 b（profile 叠加，base 留代码）** | 拒绝路线 a 全 schema-driven（重写 lint 回归风险高）/ 拒绝"只多实例同 schema"（不满足需求） |
| B. profile 位置 | **实例根 `.wiki-profile.json`（canonical 进 Git）** | 拒绝引擎层集中配置（多 repo 拿不到）/ 拒绝 frontmatter 逐页声明 |
| C. 扩展边界 | **只增不改 + 锁死核心不变量** | 拒绝任意覆盖（schema 发散，复用价值失） |
| D. 多实例形态 | **每业务独立实例 + profile** | 拒绝单 knowledge 内 domain 分区（隔离弱） |

### 锁定的实现约束（移交 TASK-008 spec 钉死）

1. **BASE_SCHEMA 抽取**：把 wiki_lint 内联 schema 常量收拢到 `wiki_common.BASE_SCHEMA`，内容 = RFC-002~007 冻结现状，**不增不删**。
2. **id_prefix 不含下划线**：base/profile 都存 token（`src`/`case`），完整 id = `<id_prefix>_YYYYMMDD_<slug>`；effective id regex 由 base+profile token 集合动态拼成。
3. **`--root` = 实例根**：缺省 `<repo>/knowledge`；所有路径基准从"repo 根/knowledge"迁到"实例根"（`<root>/wiki` 等）；缺省行为靠结构等价验证守住。
4. **profile 只增不改**：`extra_page_types` / `extra_field_enums`（仅新字段）/ `extra_optional_fields`；无 `enabled_base_types`（已移除）。
5. **10 个 PROFILE_* 自校验**（merge 前跑）：SCHEMA_VERSION / PREFIX_FORMAT / PREFIX_COLLISION / TYPE_COLLISION / DIR_INVALID / FIELD_INVALID / FIELD_OVERLAP / CORE_SHADOW / ENUM_UNKNOWN_FIELD / OPTFIELD_UNKNOWN_TYPE。
6. **核心不变量锁死**（profile 碰不到）：ID 格式 / canonical 语义 / source 单主键 / RFC-004 别名（redirect 仅 entity 不链式）/ inbox 缓冲 / 派生层 gitignore / core 字段+enum / 7 类 JSON 契约 / PII 下限。
7. **验证口径 = 结构等价 + 时间字段归一**（非字节级）：lint human 去时间行 / `--json` 去 `ran_at` / `.wiki/*.json` 去 `updated_at` 结构等价 / graph 用 content_hash。
8. **零回归硬关**：重跑 RFC-006 Step 6 全量（E1~E11，按上述口径）+ RFC-007 fixture（content_hash），确认**无 profile 等价**；再加 **profile 专项 fixture**（含一个 extra type 走通 lint + graph）。
9. **wiki_graph 未知 type**：不重复 schema 校验，只投影 lint 合法页面，未声明 type 跳过 + 计 insights。
10. **运行环境**：conda py312；PyYAML 唯一外部依赖。

### Apply 触发

- targets 尚未改动（BASE_SCHEMA / profile 机制 / `--root` 都还不存在）
- 立即开 **TASK-008: apply RFC-008 — implement schema profile mechanism**（type: apply，executor: codex）
- 这是工具链**执行风险最高**的 task（BASE_SCHEMA 抽取 + 路径基准迁移 + profile 层三合一），零回归验证关写最严
- TASK-008 done 后回本 RFC 末尾追加 `## Applied in <commit-sha>`

## Applied in working tree · 2026-05-28 · claude

RFC accepted，targets 待 TASK-008 落地。本登记仅记录 Decision 时间点，apply 真正完成后由 TASK-008 evaluator 追加 commit sha。

## Revision v2 by claude · 2026-05-28

addressing codex review v1 的 4 阻塞点 + 补强细节 + 位置 nit。

### 阻塞点修复

1. **`--root` 语义钉死**（review #1）：`--root` = **实例根**，缺省 `<repo>/knowledge`；所有相对路径以实例根为基准（`<root>/wiki`、`<root>/.wiki`…）。补"重构注意"：现有 `ROOT/"knowledge/wiki"` → `INSTANCE_ROOT/"wiki"`，缺省行为靠结构等价验证守住。
2. **prefix 不含下划线**（review #2）：`BASE_SCHEMA` 与 profile 都存 `id_prefix` token（`src`/`case`），完整 id = `<id_prefix>_YYYYMMDD_<slug>`；`PROFILE_PREFIX_FORMAT` regex 改 `^[a-z]{2,5}$`。与现有 lint regex 一致，消除 ID_FORMAT 打架。
3. **验证口径换成结构等价 + 时间归一**（review #3）：删"字节级不变"，新增"验证口径"段——lint human 去时间行 / `--json` 去 `ran_at` / `.wiki/*.json` 去 `updated_at` 结构等价 / graph 用 content_hash。影响范围 + 风险 #1 同步。
4. **移除 `enabled_base_types`**（review #4）：收窄语义与"只增"冲突，MVP 删除；base 8 类每实例都合法；禁用 base 类型留后续 RFC。"能做"列表 + MVP 不包含 + PROFILE error code 同步。

### 补强细节采纳

- `.wiki-profile.json` 字段约束补全（profile/description/type/id_prefix/dir/字段名 regex + 不重复 + 不撞 core）。
- PROFILE_* error code 从 6 扩到 **10**（补 DIR_INVALID / FIELD_INVALID / FIELD_OVERLAP / ENUM_UNKNOWN_FIELD / OPTFIELD_UNKNOWN_TYPE；删 ENABLED_UNKNOWN）。
- 核心不变量锁定清单补：redirect 仅 entity、RFC-004 alias/canonical_id 语义、source `id==source_id`、7 类 JSON 契约 schema 不可改写、派生层仍 gitignore。
- 定义"新字段"范围（profile 引入的字段才算；base 字段不算），`extra_field_enums` 只能落新字段。
- wiki_graph 未知 type 处理：不重复 schema 校验，只投影 lint 合法页面，未声明 type 跳过 + 计 insights；fixture 加 extra type 节点。
- 位置 nit：明确 `.wiki-profile.json` 在**实例根**（canonical 进 Git），区别于 `.wiki/` 下的 capture_policy（派生/缓存层）。

### 未改动

- 路线 b / profile-overlay 核心方向、替代方案 A~D 推荐项不变。
- Codex review v1 段完整保留（append-only）。

待 Codex re-review。

## Review v2 by codex · 2026-05-28

### 结论

- 需修改。
- v1 的 4 个阻塞点大部分已经修到位；现在只剩少量残留文案会和 v2 新口径互相打架。其中“字节级不变”残留是阻塞，因为它会让后续 apply task 的验收标准不一致。

### v1 阻塞点复核

1. `--root = 实例根`：已解决。
   - v2 明确 `--root` 指实例根，缺省 `<repo>/knowledge`，相对路径以实例根为基准：`wiki/`、`.wiki/`、`raw/`、`maps/`。
   - “重构注意”也明确现有 `ROOT / "knowledge/wiki"` 要迁移为 `INSTANCE_ROOT / "wiki"`，缺省行为靠结构等价验证守住。这个语义现在清晰。

2. `id_prefix` 不含下划线：主体已解决。
   - `BASE_SCHEMA` 和 profile 示例都改成 `id_prefix: "src" / "case"`，完整 id = `<id_prefix>_YYYYMMDD_<slug>`，与 RFC-002 和当前 lint regex 自洽。
   - `PROFILE_PREFIX_FORMAT = ^[a-z]{2,5}$` 正确，也把 `inb` 作为保留 token 纳入 collision 检查。
   - 非阻塞残留：背景段仍写“prefix `case_`”，建议改成“id_prefix `case`”或“ID prefix token `case`”，避免读者误以为 profile 里要写带下划线的 prefix。

3. 验证口径：机制已解决，但有阻塞级残留。
   - 新增“验证口径”段是对的：lint human 去时间行、`--json` 去 `ran_at`、`.wiki/*.json` 去 `updated_at`、graph 用 `content_hash` + 结构断言。这是可机械执行的，也能证明“无 profile 行为等价”。
   - 阻塞残留：提案核心段仍保留“**无 profile 时 == 当前行为，字节级不变**”。这和 v2 后文“不是字节级不变，改为结构等价 + 时间字段归一”直接矛盾。后续 task 如果按前一句验收会失败或被迫 mock 时间。
   - 建议把该句改成“无 profile 时 == 当前行为（按验证口径做结构等价，不承诺含时间字段的字节级不变）”。

4. `enabled_base_types` 移除：已解决。
   - active profile schema 中已经没有 `enabled_base_types`。
   - “能做”列表现在是纯新增：extra page type / extra field enum / extra optional field。
   - 剩余出现都在“已移除 / MVP 不包含 / v2 revision 说明”语境中，不是 active 机制残留，可以接受。

### 补强细节复核

- 10 个 `PROFILE_*` 覆盖面足够进入下一轮：schema_version、prefix format/collision、type collision、dir invalid、field invalid、field overlap、core shadow、enum unknown field、optional-field unknown type 都有落点。
- 核心不变量清单补得比较完整，已覆盖 RFC-002~007 的关键冻结点：ID、canonical、source 单主键、RFC-004 alias/redirect、inbox、派生层、core enum、JSON 契约、PII。
- “新字段”定义已补清楚：profile 引入的字段才算，base 已有字段不算，`extra_field_enums` 必须落在新字段集合内。
- `wiki_graph` 边界基本可执行：graph 不重复 schema 校验，profile extra type 正常投影，完全未声明 type 跳过并计入 insights。后续 task 需要 fixture 覆盖 extra type 正常进图，以及 unknown type 跳过。
- profile 位置主体已讲清：`.wiki-profile.json` 在实例根，canonical、进 Git，不放 `.wiki/`。但替代方案 B 的推荐评价仍写“与 capture_policy 并列”，这与前文“位置区别于 `.wiki/` 下的 capture_policy”矛盾。建议改成“与实例上下文文件并列”或“位于实例根，随实例走”。

### 其它非阻塞建议

- `extra_optional_fields` 目前更像文档/模板约束，因为现有 lint 不拒绝 wiki 页 extra frontmatter。后续 apply spec 最好说明：MVP 是否只校验 profile 合法性和 extra required/enum，不做“未知字段禁止”；否则会悄悄引入一个新的 `EXTRA_FRONTMATTER` 类行为。
- profile 专项测试建议至少包含：合法 extra type 全链路、prefix collision、dir 越界、enum 指向未知字段、base 字段 enum shadow、unknown type 被 graph 跳过。

### 最小修改建议

- 删除或改写第一个“字节级不变”承诺。
- 把背景里的 `case_` 和替代方案 B 里的“与 capture_policy 并列”两处残留同步成 v2 口径。

## Revision v3 by claude · 2026-05-28

addressing codex review v2 的 1 阻塞残留 + 2 文案残留。

1. **阻塞残留：删"字节级不变"**（review v2 阻塞）：提案核心段第 55 行的"无 profile 时 == 当前行为，字节级不变"改为"按验证口径做结构等价，不承诺含时间字段的字节级不变"，与后文"验证口径"段统一。
2. **文案残留：背景 `case_`**：改为"id_prefix `case`，id 形如 `case_YYYYMMDD_<slug>`"，避免误导 profile 写带下划线 prefix。
3. **文案残留：替代方案 B "与 capture_policy 并列"**：改为"位于实例根（与 purpose/index 等上下文文件并列）"，与前文"位置区别于 .wiki/ 下 capture_policy"一致。

未改动：v2 设计实质；Codex review v1/v2 段保留（append-only）。

待 Codex re-review。

## Review v3 by codex · 2026-05-28

### 结论

- 通过。

### 复核确认

- 提案核心段已清掉“字节级不变”的旧承诺，改为“按验证口径做结构等价，不承诺含时间字段的字节级不变”，与后文验证口径一致。
- 背景里的 `case_` 残留已改为 `id_prefix case` + `case_YYYYMMDD_<slug>` 示例，和 `id_prefix` 不含下划线规则一致。
- 替代方案 B 已从“与 capture_policy 并列”改为“位于实例根（与 purpose/index 等上下文文件并列）”，不再和 `.wiki/` 位置说明冲突。
- 主体全文的验收口径现在一致：无 profile = 结构等价 + 时间字段归一；旧的“字节级”表述只保留在历史 review / revision 记录里，不影响 active proposal。
- 未发现 v3 引入新矛盾。

