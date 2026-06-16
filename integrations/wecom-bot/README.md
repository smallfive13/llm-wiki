# wecom-bot — 企微智能机器人 → 本机 codex 答疑桥接

把企微「智能机器人（长连接 WebSocket 模式）」接到本机 codex，对团队知识库（knowledge-cmn 本地 clone）做**只读答疑**。无需公网回调、无需常驻服务器——机器人主动连企微，跑在任意一台不关机的机器上即可。

```
企微群 @机器人 / 单聊提问
  → wss://openws.work.weixin.qq.com（长连接，aibot_msg_callback）
  → 本服务（先回执「查询中」，单 worker 串行排队）
  → git pull 知识库 → codex exec -C <库> -s read-only（只读沙箱，防写库）
  → aibot_respond_msg 回答案（注明依据页面与背书状态）
```

## 运行

```bash
export WECOM_BOT_ID=<企微后台·机器人·长连接接入处的 BotID>
export WECOM_BOT_SECRET=<长连接专用 Secret>          # 不是回调模式的 Token/AESKey
export KB_ROOT=/Users/zhangjunwu/workspace/obsidian/datawarehouse   # 可省略（默认即此）
/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python integrations/wecom-bot/wecom_codex_bot.py
```

依赖：py312 环境的 `websockets`（已有）+ 本机已登录的 `codex` CLI。

## 行为与边界

- **只读**：codex 跑在 `-s read-only` 沙箱，机器人入口不可能写知识库；写入仍走 dropbox MR + maintainer ingest（见知识库 `raw/dropbox/README.md`）。
- **串行**：单 worker 排队（一次一个问题，约 30–90s）；收到即回执"查询中"。
- **新鲜度**：答疑前 `git pull --ff-only`，按 `KB_PULL_INTERVAL`（默认 300s）节流——高频提问不会每问都付一次 pull 网络往返；pull 失败用本地现有版本（log 警告）。
- **检索加速**：知识库自带 `.ignore`，rg/fd 答疑时跳过 `raw/`（原文+图片）/`maps/`/`.wiki/`，命中只落在 wiki/ 提炼页，避免 codex 被引去啃冗长原文（`raw/dropbox/` 刻意保留可搜，供 ingest）。
- **去重**：按 msgid 去重，重连后服务器重推不会重复答。
- **非文本消息**：提示走 MR 投料流程（机器人不收文件）。
- **同一机器人同时只能有一条长连接**：新连接会顶掉旧连接（企微协议约束），别在两台机器同时跑。

## 已验证 / 待验证

- ✅ codex exec 只读答疑链路（本机实测，答案带依据页面 + 背书状态）。
- ⚠️ `aibot_respond_msg` 的 body 会话定位字段（chatid/msgid）按官方文档 [101463](https://developer.work.weixin.qq.com/document/path/101463) 合理推断实现；首次真连如遇字段错误码，对照该文档「被动回复」一节微调 `respond_text()`。

## 后续（不在本桥接范围）

- 机器人收文件自动建 dropbox MR（与 RFC-024 自动评审合流）。
- 主动推送（CI 失败 / 新 MR / ingest 完成提醒）——长连接协议本身支持主动 push，可在 worker 外加任务。
