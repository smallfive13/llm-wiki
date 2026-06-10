---
id: task_20260610_023
title: 团队开放基建 — datawarehouse 带历史拆库上 GitLab + 引擎仓推送 + CI 门禁 + 投料约定
author: claude
executor: codex
status: pending
type: other
created: 2026-06-10
updated: 2026-06-10
related_rfcs: []
---

# TASK-023: 团队开放基建

## 目标

把 datawarehouse 知识库开放给团队（8 人，内部 GitLab，全员用 AI agent）：**带历史**拆出 datawarehouse 独立仓推 GitLab + 引擎仓推 GitLab + GitLab CI 三道门禁（lint / PII / eval）+ `raw/dropbox/` 投料约定 + 库根 `AGENTS.md` 团队投料节 + 本地实例切换到新仓。协作模型已定：**成员只投料、不写正本、不碰 manifest**；maintainer（用户或其授权 AI）按 RFC-019 triage→apply 统一 ingest；`review: true` 仅 maintainer 可盖。

> 协议定版（RFC-023 团队贡献协议）由 claude 另行起草走 RFC 流程，不在本 task 内。

## 前置条件

- **用户提供两个内部 GitLab 空仓地址**：`<DW_REPO_URL>`（datawarehouse 实例仓）+ `<ENGINE_REPO_URL>`（llm-wiki 引擎仓）。**未提供则停下报告，不要自行创建或猜测地址。**
- 数据仓 `/Users/zhangjunwu/workspace/obsidian/knowledge` git clean；引擎仓 clean（除本 task）。
- 拆库预演已完成：分支 `dw-split-preview`（15 commits，`git subtree split -P datawarehouse`）已存在于数据仓；全历史凭证扫描 0 真实命中（唯一命中为 capture_policy.json 的规则 pattern 自身）。直接复用该分支，**不要重新 split**。
- 环境：`/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python`（完整命令）；或引擎 `bin/wiki`（`WIKI_PY` 已知）。

## 强约束

1. **不动 personal/**：拆库、推送、本地切换全程不得触碰 `obsidian/knowledge/personal/`；personal 留在原本地仓。
2. **不改引擎 scripts 逻辑 / core schema**：本 task 是 ops + 实例文档 + CI 配置。
3. **带历史推送用现成分支**：`git push <DW_REPO_URL> dw-split-preview:main`；引擎 `git push <ENGINE_REPO_URL> main`。推送失败（权限/网络）停下报告。
4. **新实例仓必须补根 `.gitignore`**（split 子树不含原仓根 ignore）：派生层（`.wiki/id_index.json` / `inbox_index.json` / `normalized_alias_index.json` / `cache.json` / `search_index/` / `lightrag/`、`maps/graph-data.json` / `knowledge-graph.md` / `graph-insights.md`）+ Obsidian 每机器配置（`workspace*.json` / `themes/` / `appearance.json`）+ `.DS_Store`；**显式放行 `!.wiki/schema_sync.json`**（RFC-021 实例正本元数据）。
5. **CI 三道门禁缺一不可**：`wiki_lint --check-only`（exit 0）、`wiki_lint --scan-wiki-pii`（exit 0）、`wiki_eval --check`（按引擎默认阈值）。CI 内引擎获取用 `CI_JOB_TOKEN` clone `<ENGINE_REPO_URL>`，依赖只装 `pyyaml`。
6. **投料区约定**：`raw/dropbox/` 只放原料；成员 MR 不得改 `wiki/**`、`raw/source_manifest.json`、`.wiki/**`、上下文层（purpose/index/overview/log）——本约定写入 AGENTS.md 与 dropbox README（写入 AI 约定 + MR review 把关；CI 不新增机械检查，引擎零改动）。
7. **本地切换不丢状态**：新 clone 后 datawarehouse 的 lint / PII / eval 必须与切换前一致（33 页 / 0 错 0 警 / eval 100）；`~/.claude/skills/wiki/instances.json` 的 `datawarehouse.root` 更新为新 clone 路径；旧目录保留为只读审计、不再写入。
8. 数据仓与引擎仓的 commit 分开；新实例仓上的基建改动（.gitignore / CI / dropbox / AGENTS）在**新仓**单独 commit。

## 步骤

> **Step 0 spec-review**：向用户确认 `<DW_REPO_URL>` / `<ENGINE_REPO_URL>` 已建空仓 + 本机对内部 GitLab 的认证方式（ssh/https）；核对 `dw-split-preview` 分支存在且尖部对应 `[schema-sync] datawarehouse sync schema mirror by codex`；核对原仓根 `.gitignore` 内容（作为约束 4 的来源）；确认 GitLab runner 可用镜像（默认按 `image: python:3.12` 写，若用户告知 runner 受限再调整）。有歧义先提。

1. **推引擎仓**：`git -C /Users/zhangjunwu/workspace/llm-wiki/llm-wiki push <ENGINE_REPO_URL> main`。
2. **推实例仓（带历史）**：`git -C /Users/zhangjunwu/workspace/obsidian/knowledge push <DW_REPO_URL> dw-split-preview:main`。
3. **本地 clone 新仓**：`git clone <DW_REPO_URL> /Users/zhangjunwu/workspace/obsidian/datawarehouse`（与 knowledge 平级，Obsidian 可独立开 vault）。后续 4-6 步在新 clone 内进行。
4. **新仓根 `.gitignore`**：按强约束 4 写入。
5. **`.gitlab-ci.yml`**（单 stage 三 job 或一 job 三步，executor 定，但三道门禁的退出码必须分别生效）：
   ```yaml
   # 形态示意（executor 按实际调整）
   image: python:3.12
   validate:
     script:
       - pip install pyyaml
       - git clone https://gitlab-ci-token:${CI_JOB_TOKEN}@<ENGINE_HOST_PATH>.git engine
       - python engine/scripts/wiki_lint.py --root . --check-only
       - python engine/scripts/wiki_lint.py --root . --scan-wiki-pii
       - python engine/scripts/wiki_eval.py --root . --check
   ```
   注意 `--root .`（实例仓根即库根）；engine clone 目录加进 `.gitignore`。
6. **投料区 + 文档**：
   - 建 `raw/dropbox/.gitkeep` + `raw/dropbox/README.md`：投料规则（一份原料一个子目录 `YYYYMMDD-<标题>/`，放文档/链接清单/截图；不碰 wiki/、manifest、.wiki/；走 MR；硬红线不收 AK/SK、password、token、私钥、密钥、连接串、可复用登录凭证、客户级 PII——与 purpose.md 一致）。
   - `AGENTS.md` 追加「团队投料与 ingest」节：成员角色（只投料）/ maintainer 角色（RFC-019 triage→apply、逐份 commit、`review:true` 仅 maintainer）/ MR + CI 流程 / dropbox→manifest 登记由 ingest AI 做。
   - `log.md` 记一条团队开放基建。
7. **新仓 commit + push**：基建改动（4-6）一个 commit，push 到 GitLab `main`。
8. **本地实例切换**：更新 `~/.claude/skills/wiki/instances.json` 的 `datawarehouse.root` → `/Users/zhangjunwu/workspace/obsidian/datawarehouse`；旧 `obsidian/knowledge/datawarehouse/` 不删除、不再写入（审计保留），在原仓 `datawarehouse/AGENTS.md` 顶部加一行废弃指引（指向新仓）并在原仓 commit。
9. **验证**（见下）→ 回填 Execution log。

## 验证

```bash
ENGINE=/Users/zhangjunwu/workspace/llm-wiki/llm-wiki
NEWDW=/Users/zhangjunwu/workspace/obsidian/datawarehouse
# 新 clone 全绿（与切换前一致：33 页 / 0 错 0 警 / eval 100）
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python $ENGINE/scripts/wiki_lint.py --root $NEWDW --check-only; echo "lint=$?"
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python $ENGINE/scripts/wiki_lint.py --root $NEWDW --scan-wiki-pii; echo "pii=$?"
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python $ENGINE/scripts/wiki_eval.py --root $NEWDW | grep -i score
# 历史完整：新仓 log 15+1(基建) commits、首 commit 为 init
git -C $NEWDW log --oneline | tail -1
# .gitignore 生效：跑过 lint 后新仓 status 仍 clean（派生层未被跟踪）
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python $ENGINE/scripts/wiki_lint.py --root $NEWDW >/dev/null; git -C $NEWDW status --short
# schema_sync.json 仍被跟踪（放行生效）
git -C $NEWDW ls-files .wiki/schema_sync.json
# instances.json 指向新仓后 skill 链路可用（personal 不受影响）
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python $ENGINE/scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/knowledge/personal --check-only; echo "personal=$?"
# CI：push 后由用户在 GitLab 确认首条 pipeline 绿（executor 本地无法验证，报告中注明待用户确认）
```

## 完成后报告格式

- Step 0 结论（两仓地址、认证方式、runner 镜像确认）
- 各步执行命令 + 关键输出（推送、clone、基建 commit sha——新仓 / 原数据仓 / 涉及的所有 commit）
- 验证输出（新仓全绿、历史完整、.gitignore 生效、schema_sync 跟踪、personal 不受影响）
- 待用户事项（GitLab pipeline 首跑确认、团队成员权限分配建议：实例仓 Developer、引擎仓 maintainer-only）
- 偏离或异常

## Execution log by codex · <date>

（执行者填写）

## Evaluation by claude · <date>

（评估者填写）
