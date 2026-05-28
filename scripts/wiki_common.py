#!/usr/bin/env python3
"""Shared pure helpers for llm-wiki maintenance scripts."""

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional


LOCAL_TZ = timezone(timedelta(hours=8))


@dataclass
class MarkdownDoc:
    path: Path
    rel: str
    fm: Dict[str, Any]
    body: str
    line_map: Dict[str, int]
    has_frontmatter: bool


def now_iso() -> str:
    return datetime.now(LOCAL_TZ).replace(microsecond=0).isoformat()


def rel_to_knowledge(path: Path, root: Path) -> str:
    return path.relative_to(root / "knowledge").as_posix()


def _normalize_yaml_dates(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat() if value.tzinfo is not None else value
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, list):
        return [_normalize_yaml_dates(v) for v in value]
    if isinstance(value, dict):
        return {k: _normalize_yaml_dates(v) for k, v in value.items()}
    return value


def load_markdown(path: Path, root: Optional[Path] = None) -> MarkdownDoc:
    import yaml

    text = path.read_text(encoding="utf-8")
    rel = rel_to_knowledge(path, root) if root is not None else path.as_posix()
    if not text.startswith("---\n"):
        return MarkdownDoc(path, rel, {}, text, {}, False)
    end = text.find("\n---", 4)
    if end == -1:
        return MarkdownDoc(path, rel, {}, text, {}, False)
    fm_text = text[4:end]
    body_start = text.find("\n", end + 4)
    body = "" if body_start == -1 else text[body_start + 1 :]
    parsed = yaml.safe_load(fm_text) or {}
    if not isinstance(parsed, dict):
        parsed = {}
    parsed = _normalize_yaml_dates(parsed)
    line_map: Dict[str, int] = {}
    for i, line in enumerate(fm_text.splitlines(), start=2):
        m = re.match(r"^([A-Za-z0-9_]+)\s*:", line)
        if m and m.group(1) not in line_map:
            line_map[m.group(1)] = i
    return MarkdownDoc(path, rel, parsed, body, line_map, True)


def first_h1(doc: MarkdownDoc) -> str:
    for line in doc.body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return Path(doc.rel).stem


def normalize_alias(text: str) -> str:
    trans = str.maketrans(
        {
            "，": ",",
            "。": ".",
            "（": "(",
            "）": ")",
            "！": "!",
            "？": "?",
            "：": ":",
            "；": ";",
            "“": '"',
            "”": '"',
            "‘": "'",
            "’": "'",
        }
    )
    text = text.translate(trans).lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text


def write_json_atomic(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(f"{path}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)
