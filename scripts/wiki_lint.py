#!/usr/bin/env python3
"""wiki-lint MVP for llm-wiki.

Pure mechanical checks for the knowledge/ data layer. The script never mutates
knowledge source data; only derived .wiki indexes are written when not in
--check-only mode.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import yaml
except Exception as exc:  # pragma: no cover - exercised by environment
    print(f"wiki-lint config error: PyYAML unavailable: {exc}", file=sys.stderr)
    sys.exit(2)


VERSION = "0.1.0"
LOCAL_TZ = timezone(timedelta(hours=8))

PAGE_TYPES = {
    "source",
    "entity",
    "topic",
    "comparison",
    "synthesis",
    "decision",
    "query",
    "open-question",
}
PAGE_STATUSES = {"draft", "active", "stale", "archived", "redirect"}
CONFIDENCES = {"low", "medium", "high"}
INBOX_STATUSES = {"draft", "promoted", "dropped"}
SUGGESTED_TYPES = {
    "topic",
    "entity",
    "comparison",
    "synthesis",
    "decision",
    "query",
    "open-question",
}
SOURCE_TYPES = {"pdf", "markdown", "web", "chat", "image", "manual", "code"}
SOURCE_STATUSES = {"new", "triaged", "ingested", "skipped", "failed", "deleted"}
SOURCE_ADAPTERS = {"local_file", "web_clipper", "manual", "llm_wiki_app", "custom"}
REVIEW_TYPES = {
    "contradiction",
    "duplicate",
    "missing_page",
    "confirm",
    "suggestion",
    "source_gap",
    "stale_claim",
}
REVIEW_STATUSES = {"pending", "resolved", "dismissed"}
PRIORITIES = {"low", "medium", "high"}

TYPE_PREFIX = {
    "source": "src",
    "entity": "ent",
    "topic": "top",
    "comparison": "cmp",
    "synthesis": "syn",
    "decision": "dec",
    "query": "que",
    "open-question": "oq",
    "inbox": "inb",
}
WIKI_ID_RE = re.compile(
    r"^(src|ent|top|cmp|syn|dec|que|oq)_(\d{8})_([a-z0-9][a-z0-9-]*)(?:_(\d{2,3}))?$"
)
INBOX_ID_RE = re.compile(r"^inb_(\d{8})_(\d{6})_([a-z0-9][a-z0-9-]*)(?:-(\d{2,3}))?$")
INBOX_FILE_RE = re.compile(r"^(\d{8})-(\d{6})-([a-z0-9][a-z0-9-]*)(?:-\d{2,3})?\.md$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ISO_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})(\.\d+)?(Z|[+-]\d{2}:?\d{2})$"
)
HASH_RE = re.compile(r"^[0-9a-f]{64}$")

ERROR_CODES = {
    "MISSING_FIELD",
    "EXTRA_FRONTMATTER",
    "ID_FORMAT",
    "ID_DUPLICATE",
    "ENUM_INVALID",
    "DATE_FORMAT",
    "HASH_FORMAT",
    "JSON_VERSION",
    "TYPE_MISMATCH",
    "CANONICAL_DANGLING",
    "SUPERSEDES_ASYMMETRY",
    "SOURCE_KEY_MISMATCH",
    "SUMMARY_PATH_MISSING",
    "ALIAS_CONFLICT",
    "CANONICAL_CHAIN",
    "REDIRECT_INVALID",
    "RESOLVED_ACTION_INVALID",
    "INBOX_STATUS_PATH_MISMATCH",
    "REVIEW_QUEUE_PATH_DRIFT",
    "STATUS_NOT_ARCHIVED",
    "PII_HIT_DRAFT",
    "PII_HIT_ARCHIVE",
    "PII_HIT_WIKI",
}

ERROR_LEVEL = {
    "REVIEW_QUEUE_PATH_DRIFT": "warning",
    "STATUS_NOT_ARCHIVED": "warning",
    "PII_HIT_ARCHIVE": "warning",
    "PII_HIT_WIKI": "warning",
}


@dataclass
class Issue:
    code: str
    file: Optional[str]
    line: Optional[int]
    field: Optional[str]
    message: str
    hint: Optional[str]

    def as_json(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "file": self.file,
            "line": self.line,
            "field": self.field,
            "message": self.message,
            "hint": self.hint,
        }


@dataclass
class MarkdownDoc:
    path: Path
    rel: str
    fm: Dict[str, Any]
    body: str
    line_map: Dict[str, int]
    has_frontmatter: bool


def rel_to_knowledge(path: Path) -> str:
    return path.relative_to(ROOT / "knowledge").as_posix()


def rel_to_repo(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def now_iso() -> str:
    return datetime.now(LOCAL_TZ).replace(microsecond=0).isoformat()


def is_valid_date(value: Any) -> bool:
    if not isinstance(value, str) or not DATE_RE.match(value):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def parse_iso_tz(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    m = ISO_RE.match(value)
    if not m:
        return False
    date_part, time_part, frac_part, tz_part = m.groups()
    try:
        datetime.strptime(date_part, "%Y-%m-%d")
        datetime.strptime(time_part, "%H:%M:%S")
        if frac_part:
            # Digits only after the leading dot; precision itself is not restricted.
            int(frac_part[1:] or "0")
        if tz_part != "Z":
            raw = tz_part[1:]
            if ":" in raw:
                hh_s, mm_s = raw.split(":", 1)
            else:
                hh_s, mm_s = raw[:2], raw[2:]
            hh, mm = int(hh_s), int(mm_s)
            if hh > 23 or mm > 59:
                return False
        return True
    except ValueError:
        return False


def normalize_yaml_dates(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat() if value.tzinfo is not None else value
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, list):
        return [normalize_yaml_dates(v) for v in value]
    if isinstance(value, dict):
        return {k: normalize_yaml_dates(v) for k, v in value.items()}
    return value


def read_json(path: Path, errors: List[Issue]) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        errors.append(Issue("TYPE_MISMATCH", rel_to_knowledge(path), None, None, f"JSON 解析失败: {exc}", "修复 JSON 格式"))
        return {}


def load_markdown(path: Path) -> MarkdownDoc:
    text = path.read_text(encoding="utf-8")
    rel = rel_to_knowledge(path)
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
    parsed = normalize_yaml_dates(parsed)
    line_map: Dict[str, int] = {}
    for i, line in enumerate(fm_text.splitlines(), start=2):
        m = re.match(r"^([A-Za-z0-9_]+)\s*:", line)
        if m and m.group(1) not in line_map:
            line_map[m.group(1)] = i
    return MarkdownDoc(path, rel, parsed, body, line_map, True)


def issue(code: str, file: Optional[str], line: Optional[int], field: Optional[str], message: str, hint: str) -> Issue:
    if code not in ERROR_CODES:
        raise ValueError(f"unknown code {code}")
    return Issue(code, file, line, field, message, hint)


def add_issue(issues: Dict[str, List[Issue]], item: Issue) -> None:
    level = ERROR_LEVEL.get(item.code, "error")
    issues["warnings" if level == "warning" else "errors"].append(item)


def line_for(doc: MarkdownDoc, field: Optional[str]) -> Optional[int]:
    return doc.line_map.get(field or "")


def require_fields(doc: MarkdownDoc, fields: Iterable[str], issues: Dict[str, List[Issue]]) -> None:
    for field in fields:
        if field not in doc.fm or doc.fm.get(field) is None:
            add_issue(issues, issue("MISSING_FIELD", doc.rel, None, field, f"缺少必填字段 {field}", "补齐 frontmatter 字段"))


def check_enum(doc: MarkdownDoc, field: str, allowed: set, issues: Dict[str, List[Issue]]) -> None:
    if field in doc.fm and doc.fm.get(field) not in allowed:
        add_issue(
            issues,
            issue(
                "ENUM_INVALID",
                doc.rel,
                line_for(doc, field),
                field,
                f"{field}={doc.fm.get(field)!r} 不在合法取值中",
                f"使用: {', '.join(sorted(allowed))}",
            ),
        )


def check_bool(doc: MarkdownDoc, field: str, issues: Dict[str, List[Issue]]) -> None:
    if field in doc.fm and not isinstance(doc.fm.get(field), bool):
        add_issue(issues, issue("TYPE_MISMATCH", doc.rel, line_for(doc, field), field, f"{field} 必须是 bool", "使用 true 或 false"))


def validate_wiki_id(value: Any, page_type: Any) -> bool:
    if not isinstance(value, str):
        return False
    m = WIKI_ID_RE.match(value)
    if not m:
        return False
    prefix, ymd = m.group(1), m.group(2)
    if page_type in TYPE_PREFIX and TYPE_PREFIX[page_type] != prefix:
        return False
    try:
        datetime.strptime(ymd, "%Y%m%d")
        return True
    except ValueError:
        return False


def validate_inbox_id(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    m = INBOX_ID_RE.match(value)
    if not m:
        return False
    try:
        datetime.strptime(m.group(1), "%Y%m%d")
        datetime.strptime(m.group(2), "%H%M%S")
        return True
    except ValueError:
        return False


def validate_inbox_filename(name: str) -> bool:
    m = INBOX_FILE_RE.match(name)
    if not m:
        return False
    try:
        datetime.strptime(m.group(1), "%Y%m%d")
        datetime.strptime(m.group(2), "%H%M%S")
        return True
    except ValueError:
        return False


def check_date_field(doc: MarkdownDoc, field: str, issues: Dict[str, List[Issue]]) -> None:
    if field in doc.fm and not is_valid_date(doc.fm.get(field)):
        add_issue(issues, issue("DATE_FORMAT", doc.rel, line_for(doc, field), field, f"{field} 必须是 YYYY-MM-DD", "使用有效日期"))


def is_list(value: Any) -> bool:
    return isinstance(value, list)


def check_list_type(doc: MarkdownDoc, field: str, issues: Dict[str, List[Issue]]) -> None:
    if field in doc.fm and not isinstance(doc.fm.get(field), list):
        add_issue(issues, issue("TYPE_MISMATCH", doc.rel, line_for(doc, field), field, f"{field} 必须是数组", "使用 YAML list 或 []"))


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


def canonical_fields(doc: MarkdownDoc) -> List[Tuple[str, str]]:
    result: List[Tuple[str, str]] = []
    for field in ("source_ids", "related_ids", "supersedes", "superseded_by"):
        value = doc.fm.get(field, [])
        if isinstance(value, list):
            result.extend((field, str(v)) for v in value)
    if doc.fm.get("canonical_id") not in (None, ""):
        result.append(("canonical_id", str(doc.fm.get("canonical_id"))))
    return result


def json_version(data: Dict[str, Any], rel: str, issues: Dict[str, List[Issue]]) -> None:
    if data.get("version") != 1:
        add_issue(issues, issue("JSON_VERSION", rel, None, "version", "JSON 顶层 version 必须等于 1", "设置为 1"))


def check_iso_field(data: Dict[str, Any], rel: str, field: str, issues: Dict[str, List[Issue]], allow_missing: bool = False, allow_null: bool = False) -> None:
    if field not in data:
        if not allow_missing:
            add_issue(issues, issue("MISSING_FIELD", rel, None, field, f"缺少字段 {field}", "补齐字段"))
        return
    value = data.get(field)
    if value is None and allow_null:
        return
    if not parse_iso_tz(value):
        add_issue(issues, issue("DATE_FORMAT", rel, None, field, f"{field} 必须是带时区 ISO 8601", "使用 YYYY-MM-DDTHH:MM:SS+08:00"))


def check_date_json(value: Any, rel: str, field: str, issues: Dict[str, List[Issue]], allow_null: bool = False) -> None:
    if value is None and allow_null:
        return
    if not parse_iso_tz(value):
        add_issue(issues, issue("DATE_FORMAT", rel, None, field, f"{field} 必须是带时区 ISO 8601", "使用 YYYY-MM-DDTHH:MM:SS+08:00"))


def write_json_atomic(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(f"{path}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


def scan_markdown_files() -> Tuple[List[MarkdownDoc], List[MarkdownDoc], List[MarkdownDoc]]:
    wiki_docs = [load_markdown(p) for p in sorted((ROOT / "knowledge/wiki").glob("**/*.md"))]
    inbox_docs = [load_markdown(p) for p in sorted((ROOT / "knowledge/inbox").glob("*.md"))]
    inbox_archived = [load_markdown(p) for p in sorted((ROOT / "knowledge/inbox/archive").glob("**/*.md"))]
    return wiki_docs, inbox_docs, inbox_archived


def build_id_index(wiki_docs: List[MarkdownDoc], issues: Dict[str, List[Issue]]) -> Dict[str, MarkdownDoc]:
    index: Dict[str, MarkdownDoc] = {}
    seen: Dict[str, MarkdownDoc] = {}
    for doc in wiki_docs:
        pid = doc.fm.get("id")
        if not isinstance(pid, str):
            continue
        if pid in seen:
            add_issue(issues, issue("ID_DUPLICATE", doc.rel, line_for(doc, "id"), "id", f"id {pid!r} 重复", f"已在 {seen[pid].rel} 出现"))
        else:
            seen[pid] = doc
            index[pid] = doc
    return index


def validate_wiki_docs(wiki_docs: List[MarkdownDoc], issues: Dict[str, List[Issue]]) -> None:
    required_common = [
        "id",
        "type",
        "status",
        "confidence",
        "created",
        "updated",
        "last_verified",
        "review",
    ]
    for doc in wiki_docs:
        if not doc.has_frontmatter:
            add_issue(issues, issue("MISSING_FIELD", doc.rel, 1, None, "wiki 页面缺少 frontmatter", "补齐标准 frontmatter"))
            continue
        require_fields(doc, required_common, issues)
        check_enum(doc, "type", PAGE_TYPES, issues)
        check_enum(doc, "status", PAGE_STATUSES, issues)
        check_enum(doc, "confidence", CONFIDENCES, issues)
        check_bool(doc, "review", issues)
        for field in ("created", "updated", "last_verified"):
            check_date_field(doc, field, issues)
        if "id" in doc.fm and not validate_wiki_id(doc.fm.get("id"), doc.fm.get("type")):
            add_issue(issues, issue("ID_FORMAT", doc.rel, line_for(doc, "id"), "id", "wiki 页面 id 格式不符或 prefix 与 type 不匹配", "使用 <prefix>_YYYYMMDD_<slug>"))
        if doc.fm.get("status") == "redirect" and doc.fm.get("type") != "entity":
            add_issue(issues, issue("ENUM_INVALID", doc.rel, line_for(doc, "status"), "status", "redirect 只能用于 entity 页", "改为合法状态或改为 entity"))
        for field in ("source_ids", "related_ids", "supersedes", "superseded_by", "aliases"):
            check_list_type(doc, field, issues)
        if doc.fm.get("type") == "source":
            for field in ("source_id", "hash_sha256", "original_path", "source_url", "imported_at"):
                if field not in doc.fm:
                    add_issue(issues, issue("MISSING_FIELD", doc.rel, None, field, f"source 页缺少 {field}", "补齐 source 字段"))
            if doc.fm.get("id") != doc.fm.get("source_id"):
                add_issue(issues, issue("SOURCE_KEY_MISMATCH", doc.rel, line_for(doc, "source_id"), "source_id", "source 页 id 必须等于 source_id", "统一为同一 src_ id"))
            if "hash_sha256" in doc.fm and not (isinstance(doc.fm.get("hash_sha256"), str) and HASH_RE.match(doc.fm.get("hash_sha256"))):
                add_issue(issues, issue("HASH_FORMAT", doc.rel, line_for(doc, "hash_sha256"), "hash_sha256", "hash_sha256 必须是 64 位小写十六进制", "重新计算并填入小写 sha256"))
            if "imported_at" in doc.fm and not parse_iso_tz(doc.fm.get("imported_at")):
                add_issue(issues, issue("DATE_FORMAT", doc.rel, line_for(doc, "imported_at"), "imported_at", "imported_at 必须是带时区 ISO 8601", "使用 YYYY-MM-DDTHH:MM:SS+08:00"))
        if doc.fm.get("type") == "entity":
            canonical_id = doc.fm.get("canonical_id")
            if canonical_id not in (None, "") and doc.fm.get("status") != "redirect":
                add_issue(issues, issue("REDIRECT_INVALID", doc.rel, line_for(doc, "canonical_id"), "canonical_id", "canonical_id 非空的 entity 必须 status: redirect", "改 status 或清空 canonical_id"))


def validate_inbox_docs(docs: List[MarkdownDoc], archived: List[MarkdownDoc], issues: Dict[str, List[Issue]]) -> None:
    required = ["id", "type", "status", "confidence", "review", "suggested_target_type", "suggested_target_title", "created"]
    for doc in docs + archived:
        if not doc.has_frontmatter:
            add_issue(issues, issue("MISSING_FIELD", doc.rel, 1, None, "inbox 文件缺少 frontmatter", "补齐 capture item frontmatter"))
            continue
        require_fields(doc, required, issues)
        check_enum(doc, "type", {"inbox"}, issues)
        check_enum(doc, "status", INBOX_STATUSES, issues)
        check_enum(doc, "confidence", CONFIDENCES, issues)
        check_enum(doc, "suggested_target_type", SUGGESTED_TYPES, issues)
        check_bool(doc, "review", issues)
        check_date_field(doc, "created", issues)
        if "id" in doc.fm and not validate_inbox_id(doc.fm.get("id")):
            add_issue(issues, issue("ID_FORMAT", doc.rel, line_for(doc, "id"), "id", "inbox id 必须是 inb_YYYYMMDD_HHmmss_<slug>", "补齐秒级时间戳"))
        if doc.path.parent == ROOT / "knowledge/inbox" and not validate_inbox_filename(doc.path.name):
            add_issue(issues, issue("ID_FORMAT", doc.rel, None, "filename", "inbox 文件名必须是 YYYYMMDD-HHmmss-<slug>.md", "使用秒级文件名"))
        if "/archive/promoted/" in doc.rel and doc.fm.get("status") != "promoted":
            add_issue(issues, issue("INBOX_STATUS_PATH_MISMATCH", doc.rel, line_for(doc, "status"), "status", "archive/promoted 下 status 必须是 promoted", "修正 status"))
        if "/archive/dropped/" in doc.rel and doc.fm.get("status") != "dropped":
            add_issue(issues, issue("INBOX_STATUS_PATH_MISMATCH", doc.rel, line_for(doc, "status"), "status", "archive/dropped 下 status 必须是 dropped", "修正 status"))


def validate_context_docs(issues: Dict[str, List[Issue]]) -> None:
    for name in ("purpose.md", "index.md", "overview.md", "log.md"):
        path = ROOT / "knowledge" / name
        if path.exists() and path.read_text(encoding="utf-8").startswith("---\n"):
            add_issue(issues, issue("EXTRA_FRONTMATTER", rel_to_knowledge(path), 1, None, "上下文层 markdown 不应有 frontmatter", "移除 frontmatter"))


def validate_json_contracts(id_index: Dict[str, MarkdownDoc], issues: Dict[str, List[Issue]]) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    source_manifest_path = ROOT / "knowledge/raw/source_manifest.json"
    review_queue_path = ROOT / "knowledge/.wiki/review_queue.json"
    capture_policy_path = ROOT / "knowledge/.wiki/capture_policy.json"
    source_manifest = read_json(source_manifest_path, issues)
    review_queue = read_json(review_queue_path, issues)
    capture_policy = read_json(capture_policy_path, issues)
    json_version(source_manifest, "raw/source_manifest.json", issues)
    json_version(review_queue, ".wiki/review_queue.json", issues)
    json_version(capture_policy, ".wiki/capture_policy.json", issues)
    if "updated_at" in source_manifest:
        check_iso_field(source_manifest, "raw/source_manifest.json", "updated_at", issues, allow_missing=True)
    if "updated_at" in review_queue:
        check_iso_field(review_queue, ".wiki/review_queue.json", "updated_at", issues, allow_missing=True)
    check_iso_field(capture_policy, ".wiki/capture_policy.json", "updated_at", issues)
    if not isinstance(source_manifest.get("sources", []), list):
        add_issue(issues, issue("TYPE_MISMATCH", "raw/source_manifest.json", None, "sources", "sources 必须是数组", "使用 []"))
    if not isinstance(review_queue.get("items", []), list):
        add_issue(issues, issue("TYPE_MISMATCH", ".wiki/review_queue.json", None, "items", "items 必须是数组", "使用 []"))
    if not isinstance(capture_policy.get("auto_capture"), bool):
        add_issue(issues, issue("TYPE_MISMATCH", ".wiki/capture_policy.json", None, "auto_capture", "auto_capture 必须是 bool", "使用 true/false"))
    if not (isinstance(capture_policy.get("exclude_paths"), list) and all(isinstance(x, str) for x in capture_policy.get("exclude_paths", []))):
        add_issue(issues, issue("TYPE_MISMATCH", ".wiki/capture_policy.json", None, "exclude_paths", "exclude_paths 必须是字符串数组", "使用 [] 或字符串数组"))
    if not (isinstance(capture_policy.get("exclude_patterns"), list) and all(isinstance(x, str) for x in capture_policy.get("exclude_patterns", []))):
        add_issue(issues, issue("TYPE_MISMATCH", ".wiki/capture_policy.json", None, "exclude_patterns", "exclude_patterns 必须是字符串数组", "使用字符串数组"))
    if not (isinstance(capture_policy.get("max_inbox_files"), int) and capture_policy.get("max_inbox_files") > 0):
        add_issue(issues, issue("TYPE_MISMATCH", ".wiki/capture_policy.json", None, "max_inbox_files", "max_inbox_files 必须是正整数", "设置为正整数"))

    for idx, src in enumerate(source_manifest.get("sources", []) if isinstance(source_manifest.get("sources", []), list) else []):
        rel = "raw/source_manifest.json"
        for field in ("source_id", "title", "source_type", "hash_sha256", "original_path", "source_url", "imported_at", "last_ingested_at", "status", "summary_page_id", "summary_page_path", "adapter"):
            if field not in src:
                add_issue(issues, issue("MISSING_FIELD", rel, None, field, f"sources[{idx}] 缺少 {field}", "补齐字段"))
        if src.get("source_type") not in SOURCE_TYPES:
            add_issue(issues, issue("ENUM_INVALID", rel, None, "source_type", "source_type 非法", "使用合法 source_type"))
        if src.get("status") not in SOURCE_STATUSES:
            add_issue(issues, issue("ENUM_INVALID", rel, None, "status", "source status 非法", "使用合法 status"))
        if src.get("adapter") not in SOURCE_ADAPTERS:
            add_issue(issues, issue("ENUM_INVALID", rel, None, "adapter", "adapter 非法", "使用合法 adapter"))
        if not (isinstance(src.get("hash_sha256"), str) and HASH_RE.match(src.get("hash_sha256", ""))):
            add_issue(issues, issue("HASH_FORMAT", rel, None, "hash_sha256", "hash_sha256 必须是 64 位小写十六进制", "重新计算 hash"))
        check_date_json(src.get("imported_at"), rel, "imported_at", issues)
        check_date_json(src.get("last_ingested_at"), rel, "last_ingested_at", issues)
        sid, summary_id = src.get("source_id"), src.get("summary_page_id")
        if summary_id is not None and summary_id != sid:
            add_issue(issues, issue("SOURCE_KEY_MISMATCH", rel, None, "summary_page_id", "summary_page_id 必须等于 source_id 或 null", "统一 source_id"))
        summary_path = src.get("summary_page_path")
        if summary_path is not None:
            full = ROOT / "knowledge" / str(summary_path)
            if not full.exists():
                add_issue(issues, issue("SUMMARY_PATH_MISSING", rel, None, "summary_page_path", "summary_page_path 文件不存在", "修正路径或置 null"))
            elif summary_id:
                doc = id_index.get(str(summary_id))
                if not doc or doc.fm.get("type") != "source" or doc.fm.get("id") != sid:
                    add_issue(issues, issue("SOURCE_KEY_MISMATCH", rel, None, "summary_page_id", "摘要页 id/type/source_id 不一致", "修正 source 主键"))

    for idx, item in enumerate(review_queue.get("items", []) if isinstance(review_queue.get("items", []), list) else []):
        rel = ".wiki/review_queue.json"
        if item.get("type") not in REVIEW_TYPES:
            add_issue(issues, issue("ENUM_INVALID", rel, None, "type", f"items[{idx}].type 非法", "使用合法 type"))
        if item.get("status") not in REVIEW_STATUSES:
            add_issue(issues, issue("ENUM_INVALID", rel, None, "status", f"items[{idx}].status 非法", "使用合法 status"))
        if item.get("priority") not in PRIORITIES:
            add_issue(issues, issue("ENUM_INVALID", rel, None, "priority", f"items[{idx}].priority 非法", "使用合法 priority"))
        check_date_json(item.get("created_at"), rel, "created_at", issues)
        check_date_json(item.get("updated_at"), rel, "updated_at", issues)
        check_date_json(item.get("resolved_at"), rel, "resolved_at", issues, allow_null=True)
        actions = {opt.get("action") for opt in item.get("options", []) if isinstance(opt, dict)}
        resolved_action = item.get("resolved_action")
        if resolved_action not in actions and resolved_action not in (None, "manual_resolution"):
            add_issue(issues, issue("RESOLVED_ACTION_INVALID", rel, None, "resolved_action", "resolved_action 来源不合法", "使用 options.action/manual_resolution/null"))
        for field in ("affected_page_ids", "source_ids"):
            for page_id in item.get(field, []) if isinstance(item.get(field, []), list) else []:
                if page_id not in id_index:
                    add_issue(issues, issue("CANONICAL_DANGLING", rel, None, field, f"{page_id} 不存在", "修正 canonical id"))
        for evidence in item.get("evidence", []) if isinstance(item.get("evidence", []), list) else []:
            page_id = evidence.get("page_id") if isinstance(evidence, dict) else None
            if page_id and page_id not in id_index:
                add_issue(issues, issue("CANONICAL_DANGLING", rel, None, "evidence.page_id", f"{page_id} 不存在", "修正 page_id"))
            if page_id in id_index and isinstance(evidence, dict) and evidence.get("page_path"):
                current = id_index[page_id].rel
                if evidence.get("page_path") != current:
                    add_issue(issues, issue("REVIEW_QUEUE_PATH_DRIFT", rel, None, "evidence.page_path", f"page_path {evidence.get('page_path')} != {current}", "同步当前路径"))

    return source_manifest, review_queue, capture_policy


def validate_canonical(wiki_docs: List[MarkdownDoc], id_index: Dict[str, MarkdownDoc], issues: Dict[str, List[Issue]]) -> None:
    for doc in wiki_docs:
        for field, ref in canonical_fields(doc):
            if ref not in id_index:
                add_issue(issues, issue("CANONICAL_DANGLING", doc.rel, line_for(doc, field), field, f"引用 id {ref} 不存在", "修正或移除引用"))
    for doc in wiki_docs:
        src_id = doc.fm.get("id")
        if not isinstance(src_id, str):
            continue
        for old_id in doc.fm.get("supersedes", []) if isinstance(doc.fm.get("supersedes", []), list) else []:
            target = id_index.get(str(old_id))
            if target and src_id not in (target.fm.get("superseded_by") or []):
                add_issue(issues, issue("SUPERSEDES_ASYMMETRY", doc.rel, line_for(doc, "supersedes"), "supersedes", f"{old_id} 未反向 superseded_by {src_id}", "补齐双向关系"))
        for new_id in doc.fm.get("superseded_by", []) if isinstance(doc.fm.get("superseded_by", []), list) else []:
            target = id_index.get(str(new_id))
            if target and src_id not in (target.fm.get("supersedes") or []):
                add_issue(issues, issue("SUPERSEDES_ASYMMETRY", doc.rel, line_for(doc, "superseded_by"), "superseded_by", f"{new_id} 未反向 supersedes {src_id}", "补齐双向关系"))
            if doc.fm.get("status") != "archived":
                add_issue(issues, issue("STATUS_NOT_ARCHIVED", doc.rel, line_for(doc, "status"), "status", "被 superseded 的页应 archived", "设置 status: archived"))
        if doc.fm.get("type") == "entity":
            canonical_id = doc.fm.get("canonical_id")
            if doc.fm.get("status") == "redirect" and not canonical_id:
                add_issue(issues, issue("REDIRECT_INVALID", doc.rel, line_for(doc, "canonical_id"), "canonical_id", "redirect entity 必须有 canonical_id", "指向正名 entity"))
            if canonical_id:
                target = id_index.get(str(canonical_id))
                if not target or target.fm.get("type") != "entity":
                    add_issue(issues, issue("REDIRECT_INVALID", doc.rel, line_for(doc, "canonical_id"), "canonical_id", "canonical_id 必须指向有效 entity", "指向正名 entity"))
                elif target.fm.get("canonical_id") not in (None, ""):
                    add_issue(issues, issue("CANONICAL_CHAIN", doc.rel, line_for(doc, "canonical_id"), "canonical_id", "canonical_id 不允许链式跳转", "直接指向正名页"))


def build_alias_index(wiki_docs: List[MarkdownDoc], id_index: Dict[str, MarkdownDoc], issues: Dict[str, List[Issue]]) -> Dict[str, Dict[str, str]]:
    entries: Dict[str, Dict[str, str]] = {}

    def add_alias(doc: MarkdownDoc, form: str, source: str) -> None:
        if not form:
            return
        canonical_id = doc.fm.get("id") if doc.fm.get("canonical_id") in (None, "") else doc.fm.get("canonical_id")
        if not isinstance(canonical_id, str):
            return
        key = normalize_alias(form)
        if not key:
            return
        if key in entries and entries[key]["canonical_id"] != canonical_id:
            add_issue(issues, issue("ALIAS_CONFLICT", doc.rel, line_for(doc, "aliases"), "aliases", f"alias {form!r} 同时映射 {entries[key]['canonical_id']} 和 {canonical_id}", "人工消歧"))
            return
        entries.setdefault(
            key,
            {"canonical_id": canonical_id, "matched_form": form, "source": source},
        )

    for doc in wiki_docs:
        if doc.fm.get("type") != "entity":
            continue
        if doc.fm.get("status") == "redirect":
            add_alias(doc, str(doc.fm.get("id", "")), "redirect")
        else:
            add_alias(doc, first_h1(doc), "title")
            for alias_value in doc.fm.get("aliases", []) if isinstance(doc.fm.get("aliases", []), list) else []:
                add_alias(doc, str(alias_value), "alias")
    return dict(sorted(entries.items()))


def captured_at_for(doc: MarkdownDoc, issues: Dict[str, List[Issue]]) -> Optional[str]:
    m = INBOX_FILE_RE.match(doc.path.name)
    if m:
        try:
            dt = datetime.strptime(f"{m.group(1)}{m.group(2)}", "%Y%m%d%H%M%S").replace(tzinfo=LOCAL_TZ)
            return dt.isoformat()
        except ValueError:
            pass
    created = doc.fm.get("created")
    if is_valid_date(created):
        dt = datetime.strptime(created, "%Y-%m-%d").replace(tzinfo=LOCAL_TZ)
        return dt.isoformat()
    add_issue(issues, issue("DATE_FORMAT", doc.rel, line_for(doc, "created"), "created", "无法解析 captured_at", "修正文件名或 created"))
    return None


def build_inbox_index(inbox_docs: List[MarkdownDoc], issues: Dict[str, List[Issue]]) -> Dict[str, Any]:
    drafts = [doc for doc in inbox_docs if doc.fm.get("status") == "draft"]
    today = datetime.now(LOCAL_TZ).date()
    oldest: Optional[int] = None
    recent: List[Tuple[str, Dict[str, str]]] = []
    for doc in drafts:
        created = doc.fm.get("created")
        if is_valid_date(created):
            age = (today - datetime.strptime(created, "%Y-%m-%d").date()).days
            oldest = age if oldest is None else max(oldest, age)
        cap = captured_at_for(doc, issues)
        if not cap:
            continue
        summary = str(doc.fm.get("suggested_target_title") or "")
        if not summary:
            summary = next((line.strip() for line in doc.body.splitlines() if line.strip()), "")
        recent.append((cap, {"filename": doc.path.name, "summary": summary[:80], "captured_at": cap}))
    recent.sort(key=lambda item: item[0], reverse=True)
    return {
        "version": 1,
        "draft_count": len(drafts),
        "oldest_draft_age_days": oldest,
        "recent_drafts": [item for _, item in recent[:10]],
        "updated_at": now_iso(),
    }


def scan_pii(inbox_docs: List[MarkdownDoc], archived: List[MarkdownDoc], wiki_docs: List[MarkdownDoc], capture_policy: Dict[str, Any], scan_wiki: bool, issues: Dict[str, List[Issue]]) -> int:
    patterns = capture_policy.get("exclude_patterns", [])
    compiled = []
    for pat in patterns if isinstance(patterns, list) else []:
        try:
            compiled.append((pat, re.compile(str(pat), re.IGNORECASE)))
        except re.error:
            add_issue(issues, issue("TYPE_MISMATCH", ".wiki/capture_policy.json", None, "exclude_patterns", f"正则无效: {pat}", "修正正则"))
    hits = 0

    def scan_doc(doc: MarkdownDoc, code: str) -> None:
        nonlocal hits
        text = doc.path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            for raw, regex in compiled:
                if regex.search(line):
                    hits += 1
                    add_issue(issues, issue(code, doc.rel, lineno, None, f"命中 PII pattern {raw!r}", "人工检查或移除敏感内容"))
                    return

    for doc in inbox_docs:
        scan_doc(doc, "PII_HIT_DRAFT" if doc.fm.get("status") == "draft" else "PII_HIT_ARCHIVE")
    for doc in archived:
        scan_doc(doc, "PII_HIT_ARCHIVE")
    if scan_wiki:
        for doc in wiki_docs:
            scan_doc(doc, "PII_HIT_WIKI")
    return hits


def run_lint(args: argparse.Namespace) -> Tuple[int, Dict[str, Any], str]:
    issues: Dict[str, List[Issue]] = {"errors": [], "warnings": []}
    validate_context_docs(issues)
    wiki_docs, inbox_docs, archived_docs = scan_markdown_files()
    validate_wiki_docs(wiki_docs, issues)
    validate_inbox_docs(inbox_docs, archived_docs, issues)
    id_index = build_id_index(wiki_docs, issues)
    validate_canonical(wiki_docs, id_index, issues)
    source_manifest, review_queue, capture_policy = validate_json_contracts(id_index, issues)
    alias_entries = build_alias_index(wiki_docs, id_index, issues)
    inbox_index = build_inbox_index(inbox_docs, issues)
    pii_hits = scan_pii(inbox_docs, archived_docs, wiki_docs, capture_policy, args.scan_wiki_pii, issues)

    id_entries = {
        pid: {"path": doc.rel, "type": doc.fm.get("type"), "status": doc.fm.get("status")}
        for pid, doc in sorted(id_index.items())
    }
    derived = {
        "id_index_entries": len(id_entries),
        "normalized_alias_index_entries": len(alias_entries),
        "inbox_index_drafts": inbox_index["draft_count"],
        "written": not args.check_only,
    }
    if not args.check_only:
        write_json_atomic(ROOT / "knowledge/.wiki/id_index.json", {"version": 1, "updated_at": now_iso(), "entries": id_entries})
        write_json_atomic(ROOT / "knowledge/.wiki/normalized_alias_index.json", {"version": 1, "updated_at": now_iso(), "entries": alias_entries})
        write_json_atomic(ROOT / "knowledge/.wiki/inbox_index.json", inbox_index)

    scanned = {
        "wiki_pages": len(wiki_docs),
        "inbox_drafts": len([d for d in inbox_docs if d.fm.get("status") == "draft"]),
        "inbox_archived": len(archived_docs),
        "sources": len(source_manifest.get("sources", [])) if isinstance(source_manifest.get("sources", []), list) else 0,
        "review_queue_items": len(review_queue.get("items", [])) if isinstance(review_queue.get("items", []), list) else 0,
    }
    data = {
        "wiki_lint_version": VERSION,
        "ran_at": now_iso(),
        "scanned": scanned,
        "errors": [i.as_json() for i in issues["errors"]],
        "warnings": [i.as_json() for i in issues["warnings"]],
        "derived_layers": derived,
    }
    text = human_output(data, pii_hits, args)
    return (1 if issues["errors"] else 0), data, text


def status(ok: bool) -> str:
    return "[OK]    " if ok else "[FAIL]  "


def human_output(data: Dict[str, Any], pii_hits: int, args: argparse.Namespace) -> str:
    errors, warnings = data["errors"], data["warnings"]
    scanned = data["scanned"]
    derived = data["derived_layers"]
    lines = [
        f"wiki-lint v{VERSION}",
        "================",
        f"扫描: knowledge/wiki/ ({scanned['wiki_pages']} 文件) · knowledge/inbox/ ({scanned['inbox_drafts']} draft) · knowledge/raw/ ({scanned['sources']} source)",
        "",
        f"{status(not any(e['code'] in {'MISSING_FIELD','EXTRA_FRONTMATTER','ENUM_INVALID','DATE_FORMAT','HASH_FORMAT','JSON_VERSION','TYPE_MISMATCH','ID_FORMAT'} for e in errors))}schema 校验: {scanned['wiki_pages'] + scanned['inbox_drafts']} 页扫描",
        f"{status(not any(e['code'] in {'ID_DUPLICATE','ID_FORMAT'} for e in errors))}ID 唯一性: {derived['id_index_entries']} 个 id",
        f"{status(not any(e['code'] in {'CANONICAL_DANGLING','SUPERSEDES_ASYMMETRY'} for e in errors))}canonical 引用 + supersedes 对称",
        f"{status(not any(e['code'] in {'SOURCE_KEY_MISMATCH','SUMMARY_PATH_MISSING'} for e in errors))}source 单主键",
        f"{status(not any(e['code'] in {'ALIAS_CONFLICT','CANONICAL_CHAIN','REDIRECT_INVALID'} for e in errors))}entity 别名（含链式跳转 / status:redirect）: {derived['normalized_alias_index_entries']} entries",
        f"{status(not any(e['code'] == 'INBOX_STATUS_PATH_MISMATCH' for e in errors))}inbox: {derived['inbox_index_drafts']} draft",
        f"{status(not any(e['code'].startswith('PII_HIT') for e in errors))}PII 扫描（{'inbox + wiki' if args.scan_wiki_pii else 'inbox-only'}）: {pii_hits} 命中",
        "",
    ]
    if args.check_only:
        lines.append("派生层未重建（--check-only）")
    else:
        lines.extend(
            [
                "派生层已重建（原子写入）:",
                f"  .wiki/id_index.json ({derived['id_index_entries']} entries)",
                f"  .wiki/normalized_alias_index.json ({derived['normalized_alias_index_entries']} entries)",
                f"  .wiki/inbox_index.json ({derived['inbox_index_drafts']} drafts)",
            ]
        )
    if errors:
        lines.extend(["", "详细错误:"])
        lines.extend(format_issue("ERROR", e) for e in errors)
    if warnings:
        lines.extend(["", "详细警告:"])
        lines.extend(format_issue("WARN", w) for w in warnings)
    lines.extend(["", f"错误: {len(errors)} · 警告: {len(warnings)}"])
    return "\n".join(lines)


def format_issue(level: str, item: Dict[str, Any]) -> str:
    loc = item.get("file") or "(unknown)"
    if item.get("line") is not None:
        loc = f"{loc}:{item['line']}"
    field = item.get("field") or "-"
    return f"  [{level}] {item['code']} {loc} {field}: {item['message']}\n                 hint: {item.get('hint')}"


def find_root() -> Path:
    root = Path.cwd().resolve()
    if not (root / "knowledge").is_dir():
        print("wiki-lint config error: must run from repo root containing knowledge/", file=sys.stderr)
        sys.exit(2)
    return root


def main() -> int:
    parser = argparse.ArgumentParser(description="wiki-lint MVP")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--scan-wiki-pii", action="store_true")
    args = parser.parse_args()
    code, data, text = run_lint(args)
    if args.json_output:
        print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(text)
    return code


ROOT = find_root()


if __name__ == "__main__":
    sys.exit(main())
