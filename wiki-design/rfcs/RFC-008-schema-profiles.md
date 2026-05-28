---
id: rfc_20260528_008
title: 业务 schema profile 机制（base + 可扩展 overlay，支持多实例复用）
author: claude
status: proposed
created: 2026-05-28
updated: 2026-05-28
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

- 业务想加页类型 `case`（prefix `case_`）→ `wiki_lint.py` 报 `ID_FORMAT` / `ENUM_INVALID`
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

**关键性质：无 profile 时 == 当前行为，字节级不变**（现有 `knowledge/` 不写 profile 即纯 base）。这是零回归的保证。

### 1. base schema 显性化

把现在散在 `wiki_lint.py` 各处的 schema 常量收拢到 `scripts/wiki_common.py` 的单一 `BASE_SCHEMA` 结构（**内容等于 RFC-002~007 冻结的现状，不新增不删减**）：

```python
BASE_SCHEMA = {
  "schema_version": 1,
  "page_types": {
    "source": {"prefix": "src_", "dir": "wiki/sources"},
    "entity": {"prefix": "ent_", "dir": "wiki/entities"},
    "topic": {"prefix": "top_", "dir": "wiki/topics"},
    "comparison": {"prefix": "cmp_", "dir": "wiki/comparisons"},
    "synthesis": {"prefix": "syn_", "dir": "wiki/synthesis"},
    "decision": {"prefix": "dec_", "dir": "wiki/decisions"},
    "query": {"prefix": "que_", "dir": "wiki/queries"},
    "open-question": {"prefix": "oq_", "dir": "wiki/open-questions"},
  },
  "core_required_fields": ["id","type","status","confidence","created","updated","last_verified","review"],
  "core_enums": {
    "status": ["draft","active","stale","archived","redirect"],
    "confidence": ["low","medium","high"],
  },
  # source / entity 专属字段、JSON 契约 enum 等同样纳入
}
```

`wiki_lint.py` 现有校验改为读 `BASE_SCHEMA`（而非内联字面量），**逻辑不变、行为不变**——这一步只是"把常量挪个位置"，靠 Step 验证字节级等价。

### 2. 每实例 profile

实例根放 `.wiki-profile.json`（**canonical config，进 git，类比 `capture_policy.json`**）；不存在时等价空 profile（纯 base）：

```json
{
  "schema_version": 1,
  "profile": "risk-control",
  "enabled_base_types": ["source","entity","topic","decision","open-question"],
  "extra_page_types": [
    {
      "type": "case",
      "prefix": "case_",
      "dir": "wiki/cases",
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

### 3. profile 能做 / 不能做（扩展边界）

**能（只增）**：

- `enabled_base_types`：选用 base 8 类的子集（缺省 = 全部）
- `extra_page_types`：新页类型（新 `type` + 新 `prefix` + `dir` + 额外必填/可选字段）
- `extra_field_enums`：为**新字段**声明 enum
- `extra_optional_fields`：给某类型加可选字段

**不能（核心不变量，profile 碰不到）**：

| 锁死项 | 原因 |
| --- | --- |
| 稳定 ID 格式 `<prefix>_YYYYMMDD_<slug>`（及 inbox `inb_..._HHmmss_...`） | RFC-002 根基，跨业务一致工具才可复用 |
| canonical 引用语义（`source_ids`/`related_ids`/`supersedes`/`superseded_by`/`canonical_id`） | 图谱 + lint 基础 |
| source 单主键 / inbox 必经缓冲 / 派生层不入正本 | 跨业务普适结构纪律 |
| core 必填字段、`status`/`confidence` core enum | 不可删改，profile 只能在**新字段**上加 enum |
| PII 兜底下限 | 安全红线，profile 只能加严不能放松 |

### 4. profile 自校验（新增 lint 检查）

加载 profile 时校验（违规 → 新 error code）：

- `PROFILE_PREFIX_COLLISION`：`extra_page_types[].prefix` 撞 base 9 个或彼此重复
- `PROFILE_PREFIX_FORMAT`：prefix 不符 `^[a-z]{2,5}_$`
- `PROFILE_TYPE_COLLISION`：`extra_page_types[].type` 撞 base 类型名
- `PROFILE_CORE_SHADOW`：`extra_*_fields` 试图覆盖 core 必填字段名 / core enum
- `PROFILE_ENABLED_UNKNOWN`：`enabled_base_types` 含非 base 类型
- `PROFILE_SCHEMA_VERSION`：profile 的 `schema_version` 与引擎 `BASE_SCHEMA.schema_version` 不兼容

### 5. 工具 `--root` 参数

`wiki_lint.py` / `wiki_graph.py` 加 `--root <instance>`（缺省自动探测 `knowledge/`，**向后兼容**）：

```bash
python3 scripts/wiki_lint.py --root knowledge-bizA        # 单仓多实例
python3 scripts/wiki_lint.py                              # 缺省 knowledge/（现状不变）
```

`--root` 让工具对准任一实例，部署无关（单仓 `--root knowledge-bizA`；多 repo 各自 `--root .`）。effective schema = `merge(BASE_SCHEMA, <root>/.wiki-profile.json)`。

### 6. `.wiki-schema.md` 与文档

- 实例的 `.wiki-schema.md` = base schema 文档 + 本实例 profile 摘要（apply 时说明如何生成/维护）
- `01-architecture.md` 增"多实例 + schema profile"概念段
- `05-contracts-and-next-steps.md` 增 **Wiki Profile Schema** 段（`.wiki-profile.json` 字段契约）

### 范围（MVP 不包含 → 留后续）

- **跨实例联邦 / 共享 entity**：各实例隔离，不做跨库引用 / 全局 alias（后续 RFC）
- **部署机制**：引擎打包分发、多 repo submodule、CI 编排——等部署形态决策
- **路线 a 全 schema-driven**：base 仍留代码，不整体数据化
- **profile 删除/重定义 core**：明确禁止（见 #3）
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
| **实例根 `.wiki-profile.json`（推荐）** | 与 capture_policy 并列，canonical，随实例走，部署无关 |
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
- `scripts/wiki_lint.py`：校验改读 effective schema（base+profile）；新增 6 个 PROFILE_* error code；加 `--root`。**无 profile 时行为字节级不变**
- `scripts/wiki_graph.py`：节点类型集 / prefix 改读 effective schema；加 `--root`
- `scripts/README.md`：profile 机制 + `--root` 用法 + 新 error code
- `knowledge/.wiki-schema.md`：增 profile 概念 + 本实例（空 profile）说明
- `wiki-design/01-architecture.md`：增"多实例 + schema profile"段
- `wiki-design/05-contracts-and-next-steps.md`：增 **Wiki Profile Schema** 契约段

### 不改动

- RFC-002~007 的核心不变量（profile 不可碰）
- 现有 `knowledge/` 实例数据（不写 profile = 纯 base）
- inbox / capture / 派生层机制

### 与既有约束的衔接

- **lint 零回归是硬关**：BASE_SCHEMA 抽取 + profile 合并层落地后，TASK 必须重跑 RFC-006 Step 6 全量（E1~E11）+ RFC-007 fixture，确认**无 profile 时行为不变**，再加 profile 专项测试。
- effective schema 影响 wiki_graph 的节点类型集——graph 也要重测。

### 风险

1. **BASE_SCHEMA 抽取回归**：把内联 enum 收拢成常量，易抄漏。缓解：抽取后字节级对比 lint 输出（无 profile 应与 refactor 前完全一致）。
2. **profile 合并语义复杂度**：enabled_base_types + extra_page_types + extra_enums 的合并顺序与冲突。缓解：profile 自校验在合并前拦截非法 profile。
3. **prefix 空间耗尽 / 冲突**：业务各自加 prefix 可能撞。缓解：`PROFILE_PREFIX_COLLISION` 强制唯一。
4. **schema_version 演进**：引擎升级 base schema 后老 profile 兼容性。缓解：profile 带 `schema_version`，不兼容时 `PROFILE_SCHEMA_VERSION` 报错提示迁移。
5. **多实例后 `--root` 误用**：跑错实例。缓解：`--root` 缺省仍 `knowledge/`；工具输出回显当前 root + profile 名。
6. **范围膨胀**：联邦 / 部署 / 路线 a 都明确划在 MVP 外，防止 RFC 失焦。

## Review by codex · YYYY-MM-DD

（待 Codex 追加）

## Decision

（待用户填写或授权 Agent 代写）
