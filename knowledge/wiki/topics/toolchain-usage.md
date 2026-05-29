---
id: top_20260528_toolchain-usage
type: topic
status: active
confidence: high
created: 2026-05-28
updated: 2026-05-28
last_verified: 2026-05-28
review: false
source_ids: []
related_ids:
  - syn_20260528_llm-wiki-architecture
  - top_20260528_wiki-schema-rules
sources: []
related:
  - "[[llm-wiki-architecture|llm-wiki 系统架构]]"
  - "[[wiki-schema-rules|知识库 Schema 与页面规则]]"
supersedes: []
superseded_by: []
evidence_count: 3
---

# 工具链与使用说明

> `scripts/` 下的命令怎么用：环境、lint、graph、多实例、capture / ingest 工作流。schema 规则见 [[wiki-schema-rules|知识库 Schema 与页面规则]]，整体见 [[llm-wiki-architecture|llm-wiki 系统架构]]。

## 运行环境

统一 conda `py312`（Python 3.12）+ PyYAML（唯一外部依赖）：

```bash
conda activate py312
python -c "import yaml" || pip install pyyaml
```

## wiki-lint（机械校验 + 派生索引）

```bash
python3 scripts/wiki_lint.py                  # 校验 + 重建派生层
python3 scripts/wiki_lint.py --check-only     # 只校验，不写派生层
python3 scripts/wiki_lint.py --json           # 机器可读输出（stdout 纯 JSON）
python3 scripts/wiki_lint.py --scan-wiki-pii  # 额外扫 wiki/ PII（默认只扫 inbox）
python3 scripts/wiki_lint.py --root knowledge-bizA   # 指定实例根
```

退出码：`0` 无 error / `1` 有 error / `2` 配置或脚本错误。覆盖 8 类校验（schema / ID 唯一 / canonical 引用 + supersedes 对称 / source 单主键 / entity 别名 / inbox / PII / 跨流程一致性）+ 33 个 error code（含 10 个 `PROFILE_*`）。生成派生层 `id_index` / `normalized_alias_index` / `inbox_index`。

## wiki-graph（第二层增强图谱）

```bash
python3 scripts/wiki_graph.py            # 生成 maps/ 三文件
python3 scripts/wiki_graph.py --json     # 输出 graph-data，不落盘（只读）
python3 scripts/wiki_graph.py --root knowledge-bizA
```

产出（全部 gitignore 派生层）：`maps/graph-data.json`（节点 + 边 + 社区 + content_hash）、`maps/knowledge-graph.md`（概览）、`maps/graph-insights.md`（孤立 / hub / 社区 / 跨类型连接 / dangling wikilink）。5 类边：`source_ref` / `related` / `supersedes` / `wikilink` / `co_source`。

## 多实例复用

一套引擎服务多个业务知识库：

```bash
python3 scripts/wiki_lint.py  --root knowledge-风控
python3 scripts/wiki_graph.py --root knowledge-客服
```

`--root` 指实例根（缺省 `knowledge/`）。各实例可放 `.wiki-profile.json` 定制 schema（见 [[wiki-schema-rules|知识库 Schema 与页面规则]]）。

## 调用约定

- 改 `knowledge/wiki/`、`inbox/`、`source_manifest.json`、`review_queue.json`、`capture_policy.json` 后，commit 前必须跑 `wiki_lint.py --check-only` 通过（AGENTS.md 约束）。
- ingest Apply / inbox 晋升 / 结晶化完成后建议刷新 `wiki_graph.py`。
- 派生层不进 Git；不要手动维护。

## capture / ingest 工作流

- **capture（低门槛）**：默认建议模式（回答末尾 `💡 建议 capture`），用户说"存"才写 `inbox/`；`capture_policy.json` 开 `auto_capture` 才自动写；PII 一律降级建议。
- **ingest（摄入资料）**：Triage（登记 source_manifest + entity alias matching + 进 review_queue）→ Apply（写 `wiki/sources/` 摘要 + 联动 entities/topics + 回填 manifest + 刷图 + lint）。
- **inbox 晋升**：消化 inbox → 按主题分组 + alias matching → 用户决策晋升/合并/丢弃 → 移到 `inbox/archive/`。
- **结晶化**：抽稳定结论 → 写对应页面 + wikilink → 更新 `log.md`（本页即一次结晶化产物）。

## 引用

- `scripts/README.md`（完整用法 + error code 表）
- `wiki-design/02-workflows.md`（摄入 / capture / 晋升 / 图谱刷新 workflow）

## 置信度与缺口

- 置信度：high
- 缺口：未封装统一 CLI（`wiki ingest` 等仍为分步）；pre-commit hook / CI 集成未做。
