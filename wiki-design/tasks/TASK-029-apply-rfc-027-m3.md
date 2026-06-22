---
id: task_20260622_029
title: Apply RFC-027 M3 — DataWorks 直连失效检测（dataworks_client + wiki_freshness + 代码锚点）
author: claude
executor: codex
status: done
type: apply
created: 2026-06-22
updated: 2026-06-22
related_rfcs: [RFC-027]
---

# TASK-029: Apply RFC-027 M3

## 目标

落地 RFC-027 M3（失效检测，L2）：用**阿里云 DataWorks 官方 SDK**（region `ap-southeast-1`）直连，新增 `dataworks_client` + `wiki_freshness` 脚本 + 页面代码锚点字段，实现"上游代码/表结构变 → 标记待复核"。**机器只筛不写正本**（默认只读）。不做 M4（回源，TASK-030）。

## 前置条件

- RFC-027 M3 accepted（Decision 补充 by claude 2026-06-22，访问层 = 官方 DataWorks SDK）。
- codex 已有阿里云 DataWorks 对接经验；AK/SK + region(`ap-southeast-1`) 凭证就绪（环境变量 / `.env`）。
- 引擎 working tree clean。环境：`/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python`（完整命令）。

## 强约束

1. **凭证只从环境变量读**（`ALIBABA_CLOUD_ACCESS_KEY_ID/SECRET`），**绝不写入任何文件 / git 库 / 日志 / 报告输出**；`.env` 进 gitignore。
2. **访问层隔离**：新增 `scripts/dataworks_client.py`（官方 SDK 封装）+ `scripts/wiki_freshness.py`（仅这两个 import/调 SDK）；`wiki_lint/graph/eval` 保持**离线零 SDK 依赖**（测试须断言它们不 import dataworks SDK / dataworks_client）。
3. **`wiki_freshness` 默认只读**：输出 freshness report（JSON + human）+ review_queue 建议，**不改任何 frontmatter `status`**；写回须显式 `--apply-stale`（或留 maintainer 人工）。修复 codex review 阻塞③"检测失效不自动重写"。
4. **exit 码**：成功但有 drift / auth warning → **exit 0**；脚本参数/配置错 → **exit 2**；`--check` 模式遇 drift → **exit 1**（给 CI gate）。
5. **代码锚点字段**：`asset-mapping`（及可选 `topic`/`decision`）frontmatter 加 **optional** `dataworks_ref` / `code_fingerprint` / `last_synced`；pk profile（或引擎 `extra_optional_fields`）登记，**不进 required**、不 bump base、不 bump schema_version。
6. **指纹钉死**（Decision 补充）：`fingerprint_version=dw-code-v1`；`code_sha256` = GetFile content 规范化（UTF-8 / LF / strip 尾空白 / 多文件按 path 排序拼接）；存储 `sha256:<hex>`；`dataworks_ref` = `table:<project>.<table>` 或 `file:<project>/<fileId>`。
7. **接口事实由实跑核实回填**：API 真实返回字段路径（GetFile 的 content 在哪个字段、GetMetaTableBasicInfo 的 LastDdlTime 字段名）以 Step 0 实跑为准，写进 Execution log；不靠记忆硬编。
8. 凭证缺失 / 无权限 / 表或文件不存在 / 网络失败 → **warning 非 crash**（归一为 freshness report 里的 warning 行）。

## 步骤

> **Step 0 实跑核实（必做）**：用官方 `alibabacloud_dataworks_public` SDK + 现有凭证(`ap-southeast-1`)实跑 `ListFiles`/`GetFile`、`GetMetaTableBasicInfo`、`GetMetaTableColumn`，把**脱敏后的真实返回 shape** 写进 Execution log，确认：GetFile 代码内容字段路径、LastDdlTime 字段名、错误/无权限返回形态。歧义或与 Decision 冲突先提，不擅自改算法。

1. **`scripts/dataworks_client.py`**：官方 SDK 封装，凭证从 env、region `ap-southeast-1`；方法如 `get_file_code(ref)`→规范化 content、`get_table_ddl_time(table)`、`get_table_columns(table)`；错误归一。
2. **`scripts/wiki_freshness.py`**：扫库读页代码锚点 → 调 client 算当前指纹 → 与锚点比对 → 输出 report（JSON + human）+ review_queue；默认只读；`--apply-stale` 写回 `status`；`--check` CI 模式；`--root` 多实例；`--json`。exit 码同强约束 4。
3. **代码锚点字段**：pk `.wiki-profile.json`（asset-mapping optional）+ 必要时引擎 `extra_optional_fields` 支持 topic/decision；`02-workflows` 说明锚点字段与 freshness 流程（接 RFC-025 巡检）。
4. **测试 `tests/test_task_029.py`**：mock SDK 返回（用 Step 0 真实 shape）——指纹稳定 / drift 检测命中 / 默认只读不改 status / `--apply-stale` 写回 / exit 码三态 / 凭证缺失 warning 不 crash；**断言 `wiki_lint`/`wiki_graph`/`wiki_eval` 不 import dataworks SDK / dataworks_client**。
5. **`scripts/README.md`**：`wiki_freshness` 用法 + 凭证 env 说明 + 离线工具边界声明。
6. **真实 smoke**：对一张真实表/文件实跑 `wiki_freshness`（用 `@unittest.skipUnless` 凭证存在，或文档化手动命令），确认能拉到 DDL time / 代码并算出指纹。
7. 引擎一个 commit + push；pk profile 单独 commit（若改）。

## 验证

```bash
cd /Users/zhangjunwu/workspace/llm-wiki/llm-wiki
PY="/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python"
# 离线工具不依赖 SDK（断言在测试里；命令验回归）
$PY -m unittest -v tests.test_task_029 2>&1 | tail -3
$PY -m unittest discover -s tests 2>&1 | tail -2
# freshness 在无锚点库默认只读 exit 0
$PY scripts/wiki_freshness.py --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk --json; echo "fresh=$?"
# --check 无 drift exit 0
$PY scripts/wiki_freshness.py --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk --check; echo "check=$?"
# 真实 smoke（凭证存在时）：拉一张真实表的 DDL time / 代码指纹
```

## 完成后报告格式

- Step 0 实跑核实结论（GetFile content 字段路径、LastDdlTime 字段名、脱敏返回 shape、错误形态）
- 改动文件 + 关键位置（client、freshness、锚点字段、测试断言离线）
- 验证输出（test_029、回归、freshness 只读/--check/--apply-stale、真实 smoke、commit sha + push）
- 偏离或异常（尤其与 Decision 指纹/算法的任何出入，先说明再处理）

## Execution log by codex · 2026-06-22

### Step 0 实跑核实结论

使用 `/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python`，凭证仅从 `ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET` 读取，未打印 AK/SK。

- SDK 包：当前 py312 环境可用的是官方包 `alibabacloud-dataworks-public20200518`，Python import 名为 `alibabacloud_dataworks_public20200518`。
- region / endpoint：`ap-southeast-1` / `dataworks.ap-southeast-1.aliyuncs.com`。
- `ListFiles(project_id=96107, need_content=False)` 成功；首个 file shape keys 脱敏记录为 `AbsoluteFolderPath, AutoParsing, BizId, BusinessId, CommitStatus, ConnectionName, Content, CreateTime, CreateUser, CurrentVersion, FileDescription, FileFolderId, FileId, FileName, FileType, IsMaxCompute, LastEditTime, LastEditUser, NodeId, Owner, ParentId, UseType`。
- `GetFile` 成功；代码内容字段路径确认是 `Data.File.Content`，本次 smoke 内容长度非 0；指纹输出只记录 `sha256` 前缀与长度 71。
- `SearchMetaTables` 未带 cluster 时返回 `Invalid.Meta.ClusterId`；本 task 表锚点改用已知 `TableGuid = odps.<project>.<table>` 口径，不依赖 SearchMetaTables。
- `GetMetaTableBasicInfo(table_guid=odps.pk_data.dwb_risk_user_limit_dtl)` 成功；DDL 字段确认是 `Data.LastDdlTime`。
- `GetMetaTableColumn(table_guid=...)` 成功；列字段 shape keys 为 `Caption, ColumnGuid, ColumnName, ColumnType, Comment, IsForeignKey, IsPartitionColumn, IsPrimaryKey, Position`。

真实 SDK smoke 输出：

```text
{
  "get_file": {
    "content_path": "Data.File.Content",
    "fingerprint_len": 71,
    "fingerprint_prefix": "sha256"
  },
  "get_meta_table_basic_info": {
    "last_ddl_field": "Data.LastDdlTime",
    "last_ddl_present": true
  },
  "get_meta_table_column": {
    "column_count_sample": 28,
    "first_column_keys": [
      "Caption",
      "ColumnGuid",
      "ColumnName",
      "ColumnType",
      "Comment",
      "IsForeignKey",
      "IsPartitionColumn",
      "IsPrimaryKey",
      "Position"
    ]
  },
  "region": "ap-southeast-1",
  "sdk_package": "alibabacloud_dataworks_public20200518"
}
```

### 改动文件

- `scripts/dataworks_client.py`：新增 DataWorks SDK 隔离访问层；凭证只读 env；实现 `file:<project>/<fileId>` / `table:<project>.<table>` ref 解析、`dw-code-v1` 指纹、`GetFile.Data.File.Content`、`GetMetaTableBasicInfo.Data.LastDdlTime` 和列信息读取。
- `scripts/wiki_freshness.py`：新增在线 freshness 检测；默认只读；`--check` 遇 drift exit 1；`--apply-stale` 才写 `status: stale`。
- `tests/test_task_029.py`：覆盖指纹稳定、drift 检测、默认只读、`--apply-stale`、三态 exit、凭证缺失 warning、离线工具不 import SDK / dataworks client。
- `.gitignore`：加入 `.env`，防止本地凭证文件入库。
- `scripts/README.md`、`wiki-design/02-workflows.md`：补 DataWorks freshness 锚点字段、用法、离线边界和 exit 码。
- `/Users/zhangjunwu/workspace/obsidian/knowledge-pk/.wiki-profile.json`：为 `asset-mapping`、`topic`、`decision` 增加 optional `dataworks_ref` / `code_fingerprint` / `last_synced`。

### 验证输出

```text
$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest -v tests.test_task_029
Ran 9 tests in 0.589s
OK (skipped=1)
```

```text
$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python -m unittest discover -s tests
Ran 117 tests in 67.470s
OK (skipped=1)
```

```text
$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_freshness.py --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk --json
"scanned": {"anchors": 0, "wiki_pages": 1}
"drift_count": 0
"warnings": []
fresh=0

$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_freshness.py --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk --check
wiki_pages: 1 · anchors: 0 · drift: 0
check=0
```

```text
$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --root /Users/zhangjunwu/workspace/obsidian/knowledge-pk --check-only
错误: 0 · 警告: 0
pk_lint=0

$ /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python scripts/wiki_lint.py --check-docs
受管块: 6
错误: 0
check_docs=0
```

临时真实表锚点 fixture：

```text
readonly_exit=0
readonly_drift=1 updates=0 item_status=drift

wiki_pages: 1 · anchors: 1 · drift: 1
- drift: wiki/asset-mappings/payment-channel.md · table:pk_data.dwb_risk_user_limit_dtl · LastDdlTime newer than last_synced
check_exit=1

apply_exit=0
apply_drift=1 updates=['wiki/asset-mappings/payment-channel.md'] status_stale=True
```

### Commit / push

- knowledge-pk profile commit：`ffaa57c599811f3db4a87570dfc9d5dd6127cf3f`，已 push `http://git.ppdaicorp.com/international_data/knowledge-pk.git main`。
- 引擎 commit：本 task 提交（最终 sha 见执行回报）。

### 偏离或异常

- DataWorks 官方 SDK 的安装包名是 `alibabacloud-dataworks-public20200518`，Python import 名为 `alibabacloud_dataworks_public20200518`；实现按当前官方包实际 import 名落地。
- `SearchMetaTables` 在未提供 `ClusterId` 时返回 `Invalid.Meta.ClusterId`，因此表锚点不走搜索，直接使用 `odps.<project>.<table>` 的 `TableGuid`。
- 真实 smoke 临时脚本曾因 `sys.path` 和测试脚本错误假设 client 暴露 AK/SK 属性失败；repo 实现未暴露凭证属性，最终改为临时脚本直接从 env 构造 SDK 后通过，未打印任何密钥。

## Evaluation by claude · <date>

（评估者填写）
