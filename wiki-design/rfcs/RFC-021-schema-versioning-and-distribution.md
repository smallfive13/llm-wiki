---
id: rfc_20260608_021
title: schema 版本递增纪律 + 实例分发安全（.wiki-schema 镜像 vs 实例特化）
author: claude
status: proposed
created: 2026-06-08
updated: 2026-06-08
targets:
  - scripts/wiki_common.py
  - scripts/wiki_init.py
  - scripts/wiki_lint.py
  - scripts/README.md
  - knowledge/.wiki-schema.md
  - wiki-design/02-workflows.md
reviewers:
  - codex
  - user
---

# RFC-021: schema 版本递增纪律 + 实例分发安全

## 背景

REVIEW-001 的 P2-2：`BASE_SCHEMA.schema_version` 经 RFC-001~020 多次变更后**始终为 1**，且 profile 校验要求 `profile.schema_version == base.schema_version`（`wiki_common.py:626` 严格相等）。两个后果：

1. **无版本递增 / 迁移依据**：不同时间 init 的实例之间无法区分 schema 代次；将来分发 / 升级 `.wiki-schema.md` 没有"从哪升到哪"的依据。RFC-015 解决了分发**断链**，没解决版本**递增**。
2. **严格相等太脆**：一旦 bump，所有 `schema_version: 1` 的旧 profile 立刻报 `PROFILE_SCHEMA_VERSION` error——等于"任何 schema 演进都破坏所有现存 profile"，反而逼着永不 bump。

同时 RFC-020 暴露了一个紧密相关的**分发摩擦**：`--sync-schema` 是**整文件覆盖** `.wiki-schema.md`（`wiki_init.py:132`）。引擎 `knowledge/.wiki-schema.md` 已被 RFC-020 加了 6 个生成块，而 datawarehouse 的 `.wiki-schema.md` 是带**实例特化**的旧镜像（内部共享脱敏边界 `:262`、`soft_redact` 默认空 `:251`、外链处理 `:274`），与引擎差 101 行。直接 `--sync` 会用引擎版覆盖、**丢掉 datawarehouse 的特化措辞**——于是它迟迟不敢同步，越拖越分叉。

这两件事是一体的：**schema 如何安全地演进、并把演进分发 / 升级到已存在的（可能特化的）实例**。

## 提案

分 2 个 milestone。

### M1 · schema 版本递增纪律（兼容范围校验）

引入"最近破坏性版本"作为兼容基线，取代严格相等：

- `BASE_SCHEMA` 加字段：
  - `schema_version`：整数，**每次改 core 字段 / enum / JSON 契约 / 派生行为的 RFC 都 +1**。
  - `min_compatible_profile_version`：最近一次**破坏性**（删 / 改 / 收窄 core）变更后的 `schema_version`；纯**兼容新增**（加可选字段 / 加 enum 值 / 加派生信号）不动它。
- profile 兼容校验（`wiki_common.py` 替换严格相等）：
  - `profile.schema_version >= base.min_compatible_profile_version` → 兼容（base 向前演进、向后兼容旧 profile）。
  - `profile.schema_version > base.schema_version` → error（profile 比引擎还新，引擎太旧，提示升级引擎）。
  - `profile.schema_version < base.min_compatible_profile_version` → error（profile 跨过破坏性变更，需按 migration note 升级），错误码沿用 `PROFILE_SCHEMA_VERSION`，message 指出兼容下界。
- **migration note 纪律**：凡 bump `min_compatible_profile_version`（破坏性）的 RFC，必须在 RFC 内附 `## 迁移` 段（旧实例 / profile 如何升级）。
- **基线落定**：把 RFC-001~020 的累积契约定为 `schema_version: 2`、`min_compatible_profile_version: 1`（这一路没有破坏性 core 变更，故 v1 profile 仍兼容）。从此每个动 schema 的 RFC 显式维护这两个数。

### M2 · 实例分发安全（`.wiki-schema.md` = 引擎镜像，特化外移）

确立单一原则，消除"镜像 vs 特化"冲突：

- **`.wiki-schema.md` 是引擎统一镜像，不承载实例特化**。实例特化只放三处：
  - `.wiki-profile.json`（机器：schema 扩展，已有机制）；
  - `.wiki/capture_policy.json`（机器：脱敏 / visibility 策略，实例级、`--sync` 本就不碰）；
  - `purpose.md` / 库根 `AGENTS.md`（人 / AI 上下文：边界措辞、scope）。
- 依据：datawarehouse 的脱敏特化**本就已经**落在 `capture_policy.json`（`soft_redact: []`）+ `purpose.md` / `AGENTS.md`（内部共享边界）——`.wiki-schema.md` 里那几段特化措辞是**冗余副本**，删掉不丢信息（与 RFC-020 M2「正本收敛」同一思路）。
- `--sync-schema` 增加**覆盖前保护**：覆盖前 diff 实例现有 `.wiki-schema.md` 与引擎版，若实例侧存在引擎版没有的"额外内容"（疑似未外移的特化），**默认拒绝并打印差异**，要求 `--force`（或交互确认）才覆盖；无额外内容时照常同步。防止悄悄删掉未外移的特化。
- **datawarehouse 迁移**（apply 时执行，需用户授权动数据仓）：核对 `.wiki-schema.md:251/262/274` 的特化措辞已在 `purpose.md` / `AGENTS.md` 覆盖 → 删除冗余特化 → `--sync-schema` 引擎版（含 RFC-020 的 6 生成块）→ datawarehouse `lint` / `eval` 仍全绿。

## 真实摩擦来源

机制类，证据具体：

1. RFC-020 给引擎 `knowledge/.wiki-schema.md` 加 6 生成块后，datawarehouse 的 `.wiki-schema.md` 与引擎差 101 行且含实例特化（`:251/:262/:274`），`--sync-schema` 整文件覆盖会丢特化，**当前实际卡着不敢同步**（本会话反复出现的 backlog）。
2. `schema_version` 恒为 1 + 严格相等校验（`wiki_common.py:21/:626`）：20 个 RFC 改 schema 从未 bump，未来升级无迁移依据，且一旦 bump 即破坏所有旧 profile。

## 验证方式

机制类，apply 后须验证：

- **M1 fixture**：profile `schema_version` 在 `[min_compatible_profile_version, schema_version]` 内 → lint pass；低于下界 / 高于引擎 → `PROFILE_SCHEMA_VERSION` error。基线 bump 到 2 后，base profile（无 `.wiki-profile.json`）与 v1 profile 实例均 lint exit 0。
- **M2 fixture**：`--sync-schema` 对"实例有额外内容"的 fixture 默认拒绝 + 打印 diff；`--force` 才覆盖；对"无额外内容"实例正常同步。
- **真实实例 smoke**：datawarehouse 迁移后 `wiki_lint --check-only` / `--scan-wiki-pii` / `wiki_eval` 全绿，脱敏边界在 `purpose.md` / `AGENTS.md` 仍在，`.wiki-schema.md` 与引擎一致（含 6 生成块）。
- **回归**：012~020a 全过。

## 替代方案

- **`.wiki-schema.md` 用 `<!-- INSTANCE-LOCAL -->` marker 做 safe-merge**（保留实例特化段、只覆盖引擎段）：好处是 `.wiki-schema.md` 自包含（agent 首读即见特化）；坏处是 merge 逻辑复杂、特化措辞散落 `.wiki-schema.md`，与 RFC-020 刚做的「正本收敛」张力。**放弃**，改用 M2 的"特化外移 + 覆盖前保护"，更简单且一致；若未来确有"必须写进 `.wiki-schema.md` 的实例特化"需求再引入 marker。
- **schema_version 用 `major.minor`**（major 破坏、minor 兼容）：表达力强但更重。`min_compatible_profile_version` 用单整数即可表达同样的兼容边界，更轻。
- **不 bump、继续恒为 1**：维持现状的脆弱，放弃。

## 影响范围

- `scripts/wiki_common.py`：`BASE_SCHEMA.schema_version`（→2）+ 新增 `min_compatible_profile_version`（=1）；profile 兼容校验从严格相等改为范围校验。
- `scripts/wiki_init.py`：`sync_schema()` 加覆盖前 diff 保护 + `--force`。
- `scripts/wiki_lint.py`：`PROFILE_SCHEMA_VERSION` message 调整（仅措辞 / 边界提示，错误码不变）。
- `scripts/README.md`：`--sync-schema --force` 用法、版本兼容语义。
- `knowledge/.wiki-schema.md`：Schema Profile 段更新版本兼容语义；新增「`.wiki-schema.md` 是引擎镜像、特化外移」原则（注意：profile schema_version 字段已是受 `--check-docs` 影响的契约描述，若涉及生成块需 `--fix` 同步）。
- `wiki-design/02-workflows.md`：schema 升级 / 分发流程（bump 规则、migration note、sync 保护、特化外移）。
- **datawarehouse**（apply 时、外部实例，不在引擎 targets）：删冗余特化措辞 + `--sync` 引擎镜像。
- **不改**：实例的 `capture_policy.json`（机器特化天然保留）、graph/eval 逻辑、wiki 页面数据。

## Apply 拆分建议

- **TASK-021a**：M1（版本纪律：BASE_SCHEMA 两字段 + profile 范围校验 + 基线 bump 到 2 + 文档/fixture）。
- **TASK-021b**：M2（`--sync-schema` 覆盖前保护 + `--force` + 文档/fixture）+ **datawarehouse 迁移**（删冗余特化 → sync → 全绿验证；需用户授权动数据仓）。
- 各一 commit；021b 收尾确认 datawarehouse 与引擎 `.wiki-schema.md` 一致。

## Review by codex · YYYY-MM-DD

（由 codex 追加，不覆盖本提案正文。）

## Decision

（由用户填写，或用户明确授权某 Agent 代写。）

## Review by codex · 2026-06-08

结论：需修改。

总体方向认可：M1 用 `min_compatible_profile_version` 把“引擎版本”和“profile 兼容下界”拆开，是比 `profile.schema_version == base.schema_version` 更可维护的模型；M2 把 `.wiki-schema.md` 定义为引擎镜像、把实例特化外移到 `.wiki-profile.json` / `.wiki/capture_policy.json` / `purpose.md` / `AGENTS.md`，也和 RFC-020 的正本收敛方向一致。当前唯一阻塞是 `--sync-schema` 覆盖前 diff 保护的机械算法没有钉死。

### M1 · 版本纪律

同意核心方向。

- 已核对现状：`scripts/wiki_common.py:21` 仍是 `BASE_SCHEMA["schema_version"] = 1`；`validate_profile()` 当前在 `scripts/wiki_common.py:626` 用严格相等触发 `PROFILE_SCHEMA_VERSION`。
- 范围校验 `profile.schema_version ∈ [base.min_compatible_profile_version, base.schema_version]` 成立。它允许 base 兼容新增后继续接受旧 profile，同时仍能拦住“profile 比引擎新”和“profile 跨过破坏性下界”两类风险。
- 复用 `PROFILE_SCHEMA_VERSION` 是干净的；这是同一类 profile / base 版本不兼容问题，不需要新增 error code。
- 实例核对：引擎内置 `knowledge/` 无 `.wiki-profile.json`；datawarehouse 无 `.wiki-profile.json`；personal 有 `.wiki-profile.json`，内容为 `schema_version: 1`、`profile: personal`、无扩展类型。当前三者 lint 都 exit 0。基线 bump 到 `schema_version: 2`、`min_compatible_profile_version: 1` 后，personal 的 v1 profile 应继续 pass，这一点应纳入 TASK-021a fixture / smoke。

非阻塞建议：

- TASK-021a 里把 `schema_version` 缺失、非整数、低于下界、高于 base 四种 fixture 都钉死，避免 range check 对非 int 产生 Python 比较异常或模糊错误。
- `.wiki-schema.md` 的 Schema Profile 版本文案不在 TASK-020a 的 6 个 generated blocks 中，`--check-docs` 不会自动捕获它。TASK-021a 应单独验证 `.wiki-schema.md` 中 profile 版本兼容文案已更新，不要只依赖 `--check-docs`。

### M2 · 分发安全

datawarehouse 特化外移判断成立，但 sync 保护算法需修改后再执行。

已核对 datawarehouse 三处特化：

- `.wiki-schema.md:251` “本数仓内部库默认 soft_redact 为空”：机器事实已在 `/Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse/.wiki/capture_policy.json` 中体现为 `soft_redact.patterns: []`；`purpose.md:16` / `AGENTS.md:31` 也解释了内部共享边界与硬红线。
- `.wiki-schema.md:262` “内部 OA 链接、Wiki 链接、联系人、邮箱、内部系统入口、截图、水印、项目/业务线名称可以入库”：已由 `purpose.md:16` 和 `AGENTS.md:31` 覆盖。
- `.wiki-schema.md:274` 外链处理“不建 source、不跟进”：已由 `AGENTS.md:37` 覆盖。purpose.md 未逐字写外链处理，但 combined context 已覆盖，不属于唯一信息。

所以方案 B “删 `.wiki-schema.md` 冗余特化，不丢信息”成立。

阻塞点：`--sync-schema` 的“实例侧存在引擎版没有的额外内容”还不是可机械实现的定义。当前 `scripts/wiki_init.py:132` 是整文件覆盖；如果 TASK 只做普通 unified diff，很难区分三类情况：

- 旧引擎镜像的正常陈旧内容；
- 实例本地特化内容；
- 因引擎模板重排 / 删除导致的普通 diff。

这会导致两种不良实现：要么误判正常旧镜像为“有额外内容”而几乎总是拒绝；要么误把实例特化当普通 diff 覆盖掉。RFC 需要在正文中补一个明确算法或收窄语义。可选两条路线：

- 保守路线：已有 `.wiki-schema.md` 只要与引擎模板不完全一致，默认一律拒绝并打印 diff；`--force` 才覆盖。这样简单安全，但要承认“无额外内容时照常同步”只适用于 target 缺失、完全一致或未来有可识别元数据的情况。
- 可识别路线：先引入模板 hash / source version marker 或受管块边界，再只允许自动覆盖可证明来自旧引擎镜像的内容；其它 diff 默认拒绝。这个更自动，但实现更重。

当前 RFC 写法介于两者之间，TASK-021b 会被迫猜。

### Gate 自检

通过。

- `## 真实摩擦来源` 写到了 REVIEW-001 P2-2、RFC-020 后 datawarehouse `.wiki-schema.md` 分叉、`wiki_common.py:21/:626` 具体锚点，证据足够具体。
- `## 验证方式` 覆盖 M1 fixture、M2 fixture、真实实例 smoke、回归，符合 RFC-020 新 gate 的预期。
- 这次 gate 在真实 RFC 上可用；暂不需要调整模板措辞。

### Apply 拆分

拆分合理。

- TASK-021a 做版本纪律，影响 `wiki_common` / `wiki_lint` / `.wiki-schema.md` 文档和 fixture，边界清楚。
- TASK-021b 做 sync 保护和 datawarehouse 迁移，和外部实例操作绑定，应该单独 commit。TASK-021b 必须先检查 `/Users/zhangjunwu/workspace/obsidian/knowledge` clean，再对 datawarehouse 做独立数据仓 commit；不要混入引擎 apply commit。

建议处理顺序：先修 M2 diff 保护算法，再进入 TASK-021a/021b。M1 不需要重做方向，只需在 TASK 中补足类型/缺失 fixture 与 `.wiki-schema.md` 文案验证。
