---
id: task_20260610_023
title: 团队开放基建 — datawarehouse 带历史拆库上 GitLab + 引擎仓推送 + CI 门禁 + 投料约定
author: claude
executor: codex
status: done
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

## Execution log by codex · 2026-06-10

### Step 0 结论

- 远端地址：
  - 引擎仓：`http://git.ppdaicorp.com/international_data/llm-wiki.git`
  - datawarehouse 实例仓：`http://git.ppdaicorp.com/international_data/knowledge-cmn.git`
- 认证方式：HTTP Git 凭证已在本机可用；`git ls-remote` 对两个空仓均 exit 0。
- `dw-split-preview` 已存在：`b4d39d548a365021cf7c9acfeffb9f8bcefbd33f`，尖部为 `[schema-sync] datawarehouse sync schema mirror by codex`，共 15 commits；未重新 split。
- 原数据仓 `/Users/zhangjunwu/workspace/obsidian/knowledge` 与引擎仓均 clean；`personal/` 未触碰。
- CI runner 未给出额外限制，按 `image: python:3.12` 写入。

### 执行记录

```text
$ git push http://git.ppdaicorp.com/international_data/llm-wiki.git main
To http://git.ppdaicorp.com/international_data/llm-wiki.git
 * [new branch]      main -> main
```

```text
$ git push http://git.ppdaicorp.com/international_data/knowledge-cmn.git dw-split-preview:main
To http://git.ppdaicorp.com/international_data/knowledge-cmn.git
 * [new branch]      dw-split-preview -> main
```

```text
$ git clone http://git.ppdaicorp.com/international_data/knowledge-cmn.git /Users/zhangjunwu/workspace/obsidian/datawarehouse
Cloning into '/Users/zhangjunwu/workspace/obsidian/datawarehouse'...
```

新实例仓基建改动：

- 新增根 `.gitignore`：忽略 `.wiki/*_index.json`、`.wiki/cache.json`、`.wiki/search_index/`、`.wiki/lightrag/`、`maps/*` 派生层、`engine/`、Obsidian workspace/themes/appearance、`.DS_Store`；显式放行 `!.wiki/schema_sync.json`。
- 新增 `.gitlab-ci.yml`：单 job 三道门禁，CI 内用 `CI_JOB_TOKEN` clone `llm-wiki`，依次跑 `wiki_lint --check-only`、`wiki_lint --scan-wiki-pii`、`wiki_eval --check`，全部 `--root .`。
- 新增 `raw/dropbox/.gitkeep` 与 `raw/dropbox/README.md`。
- `AGENTS.md` 追加团队投料与 ingest 节；`log.md` 记录团队开放基建。

```text
$ git commit -m "[team] add datawarehouse opening infrastructure"
[main 1aa9840] [team] add datawarehouse opening infrastructure
 6 files changed, 103 insertions(+)
 create mode 100644 .gitignore
 create mode 100644 .gitlab-ci.yml
 create mode 100644 raw/dropbox/.gitkeep
 create mode 100644 raw/dropbox/README.md

$ git push origin main
To http://git.ppdaicorp.com/international_data/knowledge-cmn.git
   b4d39d5..1aa9840  main -> main
```

本地切换：

- `~/.claude/skills/wiki/instances.json` 的 `datawarehouse.root` 已改为 `/Users/zhangjunwu/workspace/obsidian/datawarehouse`。
- 旧目录 `/Users/zhangjunwu/workspace/obsidian/knowledge/datawarehouse/AGENTS.md` 顶部新增废弃指引，保留审计、不再写入。

```text
$ git -C /Users/zhangjunwu/workspace/obsidian/knowledge commit -m "[datawarehouse] mark split directory read-only"
[main 609aeed] [datawarehouse] mark split directory read-only
 1 file changed, 2 insertions(+)
```

### 验证输出

```text
$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python /Users/zhangjunwu/workspace/llm-wiki/llm-wiki/scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/datawarehouse --check-only; echo "lint=$?"
扫描: datawarehouse/wiki/ (33 文件) · datawarehouse/inbox/ (0 draft) · datawarehouse/raw/ (18 source)
错误: 0 · 警告: 0
lint=0
```

```text
$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python /Users/zhangjunwu/workspace/llm-wiki/llm-wiki/scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/datawarehouse --scan-wiki-pii; echo "pii=$?"
扫描: datawarehouse/wiki/ (33 文件) · datawarehouse/inbox/ (0 draft) · datawarehouse/raw/ (18 source)
脱敏扫描（inbox + wiki）: 0 命中
错误: 0 · 警告: 0
pii=0
```

```text
$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python /Users/zhangjunwu/workspace/llm-wiki/llm-wiki/scripts/wiki_eval.py --root /Users/zhangjunwu/workspace/obsidian/datawarehouse | grep -i score
score: 100/100
```

```text
$ git -C /Users/zhangjunwu/workspace/obsidian/datawarehouse log --oneline | wc -l
16
$ git -C /Users/zhangjunwu/workspace/obsidian/datawarehouse log --oneline | tail -1
7e953b8 init datawarehouse 数仓知识库实例
$ git ls-remote http://git.ppdaicorp.com/international_data/knowledge-cmn.git refs/heads/main
1aa984054cdfc498b598bd0cc1f0b739d3bc3eb8	refs/heads/main
```

```text
$ cd /Users/zhangjunwu/workspace/llm-wiki/llm-wiki
$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/datawarehouse >/dev/null
$ git -C /Users/zhangjunwu/workspace/obsidian/datawarehouse status --short
(no output)
$ git -C /Users/zhangjunwu/workspace/obsidian/datawarehouse ls-files .wiki/schema_sync.json
.wiki/schema_sync.json
```

```text
$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python /Users/zhangjunwu/workspace/llm-wiki/llm-wiki/scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/knowledge/personal --check-only; echo "personal=$?"
扫描: personal/wiki/ (11 文件) · personal/inbox/ (0 draft) · personal/raw/ (0 source)
错误: 0 · 警告: 0
personal=0
```

### commit sha

- 引擎远端初始推送：`c52af4d8331f474519a4c723a3fd3c9dcc1cad77`
- datawarehouse 历史分支推送基线：`b4d39d548a365021cf7c9acfeffb9f8bcefbd33f`
- 新 datawarehouse 仓基建 commit：`1aa984054cdfc498b598bd0cc1f0b739d3bc3eb8`
- 原 `/Users/zhangjunwu/workspace/obsidian/knowledge` 审计指引 commit：`609aeed406540a27fb271d8c607eeff69601fb9f`
- 本 task 执行记录 commit：见最终报告。

### 待用户事项

- 在 GitLab 确认 `knowledge-cmn` 首条 pipeline 通过；本地无法直接读取 GitLab pipeline 状态。
- 团队权限建议：`knowledge-cmn` 给团队成员 Developer；`llm-wiki` 引擎仓保持 maintainer-only 或更严格权限。

### 偏离或异常

- 未使用 SSH；本机对 GitLab HTTP 远端已有可用凭证，按用户提供的 HTTP URL 推送。
- `.gitignore` 生效验证第一次在新仓 cwd 直接调用引擎脚本绝对路径，触发既有 repo-root 检查；已按正确方式从引擎根重跑验证并通过。
- 本 task 未新增 CI 机械限制成员越界路径；按强约束只写入 AGENTS/dropbox 约定，由 MR review 把关。

## Evaluation by claude · <date>

（评估者填写）
