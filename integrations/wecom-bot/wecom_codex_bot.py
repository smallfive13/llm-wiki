#!/usr/bin/env python3
"""企微智能机器人（长连接）→ 本机 codex 只读答疑桥接。

协议：企业微信「智能机器人长连接」（developer.work.weixin.qq.com/document/path/101463）
  wss 连接 → aibot_subscribe 订阅 → 收 aibot_msg_callback → 回 aibot_respond_msg，30s ping。

架构：
  收消息 → 立即回执「查询中」 → 入队（单 worker 串行）→ git pull 知识库
  → codex exec -C <KB_ROOT> -s read-only -o <tmp> "<答疑话术+问题>" → 回答案。

配置（环境变量）：
  WECOM_BOT_ID      机器人 BotID（企微后台·长连接接入处获取）
  WECOM_BOT_SECRET  长连接专用 Secret（注意不是回调模式的 Token/EncodingAESKey）
  KB_ROOT           知识库本地 clone（默认 ~/workspace/obsidian/datawarehouse）
  CODEX_BIN         codex 可执行（默认 codex）
  CODEX_TIMEOUT     单次答疑超时秒（默认 240）

运行：
  export WECOM_BOT_ID=... WECOM_BOT_SECRET=...
  /Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python wecom_codex_bot.py
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from collections import OrderedDict
from pathlib import Path

import websockets

WS_URL = "wss://openws.work.weixin.qq.com"
BOT_ID = os.environ.get("WECOM_BOT_ID", "")
BOT_SECRET = os.environ.get("WECOM_BOT_SECRET", "")
KB_ROOT = Path(os.environ.get("KB_ROOT", str(Path.home() / "workspace/obsidian/datawarehouse")))
CODEX_BIN = os.environ.get("CODEX_BIN", "codex")
CODEX_TIMEOUT = int(os.environ.get("CODEX_TIMEOUT", "240"))
PING_INTERVAL = 30
TEXT_CHUNK = 1800  # 企微单条 text 长度保守上限（字节级更严，按字符保守切）

ANSWER_PROMPT = (
    "你是团队数仓知识库的答疑机器人。只读使用本知识库：先看 purpose.md 和 index.md，"
    "从 wiki/ 下的页面找依据回答，结尾注明依据页面；frontmatter 里 review: true 的页面优先采信，"
    "review: false 的页面采信时说明未经人工背书。知识库没有的内容明确说没有，不要编造。"
    "不要写入任何文件。回答用简洁中文。问题：{question}"
)


def log(*args: object) -> None:
    print(time.strftime("[%Y-%m-%d %H:%M:%S]"), *args, flush=True)


def req_id() -> str:
    return uuid.uuid4().hex[:16]


class Dedup:
    """msgid 去重（重连后服务器可能重推未确认消息）。"""

    def __init__(self, cap: int = 512) -> None:
        self._seen: OrderedDict[str, None] = OrderedDict()
        self._cap = cap

    def seen(self, msgid: str) -> bool:
        if msgid in self._seen:
            return True
        self._seen[msgid] = None
        if len(self._seen) > self._cap:
            self._seen.popitem(last=False)
        return False


def git_pull() -> None:
    try:
        subprocess.run(
            ["git", "-C", str(KB_ROOT), "pull", "--ff-only"],
            capture_output=True, timeout=60, check=False,
        )
    except Exception as exc:  # pull 失败用旧数据答疑，不阻塞
        log("WARN git pull failed:", exc)


def ask_codex(question: str) -> str:
    git_pull()
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp:
        out_path = tmp.name
    try:
        proc = subprocess.run(
            [CODEX_BIN, "exec", "-C", str(KB_ROOT), "-s", "read-only",
             "-o", out_path, ANSWER_PROMPT.format(question=question)],
            capture_output=True, timeout=CODEX_TIMEOUT, text=True,
        )
        answer = Path(out_path).read_text(encoding="utf-8").strip()
        if proc.returncode != 0 and not answer:
            log("codex exec rc=", proc.returncode, proc.stderr[-500:])
            return "查询失败（codex 执行异常），请稍后再试或联系 maintainer。"
        return answer or "查询完成但未取得回答，请换个问法试试。"
    except subprocess.TimeoutExpired:
        return f"查询超时（>{CODEX_TIMEOUT}s），请把问题拆小一点再试。"
    finally:
        Path(out_path).unlink(missing_ok=True)


def extract_question(body: dict) -> str | None:
    if body.get("msgtype") != "text":
        return None
    content = (body.get("text") or {}).get("content", "").strip()
    return content or None


async def send(ws, payload: dict) -> None:
    await ws.send(json.dumps(payload, ensure_ascii=False))


async def respond_text(ws, body: dict, content: str) -> None:
    """回复文本。注：body 内的会话定位字段（chatid/msgid）以官方文档
    aibot_respond_msg 一节为准；若服务端返回字段错误码，按文档调整此处。"""
    base = {"chatid": body.get("chatid", ""), "msgid": body.get("msgid", "")}
    chunks = [content[i:i + TEXT_CHUNK] for i in range(0, len(content), TEXT_CHUNK)] or [""]
    for chunk in chunks:
        await send(ws, {
            "cmd": "aibot_respond_msg",
            "headers": {"req_id": req_id()},
            "body": {**base, "msgtype": "text", "text": {"content": chunk}},
        })


async def worker(ws, queue: asyncio.Queue) -> None:
    while True:
        body = await queue.get()
        question = extract_question(body)
        if question is None:
            await respond_text(ws, body, "目前只支持文本提问；文档投料请走 knowledge-cmn 的 MR 流程（见仓库 raw/dropbox/README.md）。")
            queue.task_done()
            continue
        log("Q:", question[:80])
        answer = await asyncio.to_thread(ask_codex, question)
        log("A:", answer[:80].replace("\n", " "))
        await respond_text(ws, body, answer)
        queue.task_done()


async def heartbeat(ws) -> None:
    while True:
        await asyncio.sleep(PING_INTERVAL)
        await send(ws, {"cmd": "ping", "headers": {"req_id": req_id()}})


async def run_once(dedup: Dedup) -> None:
    async with websockets.connect(WS_URL, max_size=10 * 1024 * 1024) as ws:
        await send(ws, {
            "cmd": "aibot_subscribe",
            "headers": {"req_id": req_id()},
            "body": {"bot_id": BOT_ID, "secret": BOT_SECRET},
        })
        first = json.loads(await ws.recv())
        if first.get("body", {}).get("errcode", first.get("errcode", 0)) != 0:
            raise RuntimeError(f"subscribe failed: {first}")
        log("subscribed, bot online.")

        queue: asyncio.Queue = asyncio.Queue()
        tasks = [asyncio.create_task(heartbeat(ws)), asyncio.create_task(worker(ws, queue))]
        try:
            async for raw in ws:
                msg = json.loads(raw)
                cmd = msg.get("cmd", "")
                if cmd == "pong":
                    continue
                if cmd == "aibot_msg_callback":
                    body = msg.get("body", {})
                    if dedup.seen(str(body.get("msgid", ""))):
                        continue
                    await respond_text(ws, body, "收到，正在查询知识库…（约 1 分钟）")
                    await queue.put(body)
                else:
                    log("event:", cmd)
        finally:
            for t in tasks:
                t.cancel()


async def main() -> None:
    if not BOT_ID or not BOT_SECRET:
        sys.exit("缺少 WECOM_BOT_ID / WECOM_BOT_SECRET 环境变量")
    if not (KB_ROOT / "purpose.md").exists():
        sys.exit(f"KB_ROOT 不是知识库实例：{KB_ROOT}")
    dedup = Dedup()
    backoff = 2
    while True:
        try:
            await run_once(dedup)
            backoff = 2
        except Exception as exc:
            log(f"connection lost: {exc!r}; reconnect in {backoff}s")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)


if __name__ == "__main__":
    asyncio.run(main())
