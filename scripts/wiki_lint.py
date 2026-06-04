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
from dataclasses import dataclass
from datetime import datetime
from datetime import date as date_cls
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import yaml
except Exception as exc:  # pragma: no cover - exercised by environment
    print(f"wiki-lint config error: PyYAML unavailable: {exc}", file=sys.stderr)
    sys.exit(2)

from wiki_common import (
    BASE_SCHEMA,
    LOCAL_TZ,
    MarkdownDoc,
    PROFILE_ERROR_CODES,
    ProfileIssue,
    effective_id_regex,
    first_h1,
    is_stale,
    load_markdown as common_load_markdown,
    load_profile,
    merge_schema,
    normalize_alias,
    now_iso,
    profile_name,
    staleness_age_days,
    staleness_threshold,
    strip_code_spans,
    rel_to_knowledge as common_rel_to_knowledge,
    type_prefix,
    validate_profile,
    write_json_atomic,
)


VERSION = "0.1.0"
ROOT = Path.cwd().resolve()
INSTANCE_ROOT = ROOT / "knowledge"
SCHEMA = BASE_SCHEMA
PROFILE_NAME = "base"
PROFILE_ISSUES: List[ProfileIssue] = []

PAGE_TYPES: set = set()
PAGE_STATUSES: set = set()
CONFIDENCES: set = set()
VISIBILITIES: set = set()
INBOX_STATUSES: set = set()
SUGGESTED_TYPES: set = set()
SOURCE_TYPES: set = set()
SOURCE_STATUSES: set = set()
SOURCE_ADAPTERS: set = set()
REVIEW_TYPES: set = set()
REVIEW_STATUSES: set = set()
PRIORITIES: set = set()

TYPE_PREFIX: Dict[str, str] = {}
WIKI_ID_RE = re.compile(r"^$")
INBOX_ID_RE = re.compile(r"^$")
INBOX_FILE_RE = re.compile(r"^$")
DATE_RE = re.compile(r"^$")
ISO_RE = re.compile(r"^$")
HASH_RE = re.compile(r"^$")

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
    "STALE_PAGE",
    "UNVERIFIED_HIGH",
    "CAPTURE_POLICY_LEGACY",
    "SOFT_REDACT_HIT",
    "HARD_REDACT_HIT",
    "IMAGE_DANGLING",
    "IMAGE_PATH_ESCAPE",
    "IMAGE_HARD_REDACT",
    "IMAGE_NO_DESCRIPTION",
} | PROFILE_ERROR_CODES

MARKDOWN_IMAGE_RE = re.compile(r"!\[([^\]\n]*)\]\(([^)\n]+)\)")
OBSIDIAN_IMAGE_RE = re.compile(r"!\[\[([^\]\n]+)\]\]")
NONLOCAL_IMAGE_SCHEMES = ("http://", "https://", "data:", "mailto:")

ERROR_LEVEL = dict(BASE_SCHEMA["error_level"])


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


def rel_to_knowledge(path: Path) -> str:
    return common_rel_to_knowledge(path, INSTANCE_ROOT)


def rel_to_repo(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _repo_root() -> Path:
    root = Path.cwd().resolve()
    if not (root / "scripts").is_dir():
        print("wiki-lint config error: must run from repo root containing scripts/", file=sys.stderr)
        sys.exit(2)
    return root


def _instance_root(repo_root: Path, raw_root: Optional[str]) -> Path:
    path = Path(raw_root) if raw_root else repo_root / "knowledge"
    if not path.is_absolute():
        path = repo_root / path
    path = path.resolve()
    if not path.is_dir():
        print(f"wiki-lint config error: instance root not found: {path}", file=sys.stderr)
        sys.exit(2)
    return path


def configure(args: argparse.Namespace) -> None:
    global ROOT, INSTANCE_ROOT, SCHEMA, PROFILE_NAME, PROFILE_ISSUES
    global PAGE_TYPES, PAGE_STATUSES, CONFIDENCES, VISIBILITIES, INBOX_STATUSES, SUGGESTED_TYPES
    global SOURCE_TYPES, SOURCE_STATUSES, SOURCE_ADAPTERS, REVIEW_TYPES, REVIEW_STATUSES, PRIORITIES
    global TYPE_PREFIX, WIKI_ID_RE, INBOX_ID_RE, INBOX_FILE_RE, DATE_RE, ISO_RE, HASH_RE, ERROR_LEVEL

    ROOT = _repo_root()
    INSTANCE_ROOT = _instance_root(ROOT, args.root)
    profile = load_profile(INSTANCE_ROOT)
    PROFILE_NAME = profile_name(profile)
    PROFILE_ISSUES = validate_profile(profile, BASE_SCHEMA)
    SCHEMA = BASE_SCHEMA if PROFILE_ISSUES else merge_schema(BASE_SCHEMA, profile)

    PAGE_TYPES = set(SCHEMA["page_types"].keys())
    PAGE_STATUSES = set(SCHEMA["core_enums"]["status"])
    CONFIDENCES = set(SCHEMA["core_enums"]["confidence"])
    VISIBILITIES = set(SCHEMA["core_enums"].get("visibility", []))
    INBOX_STATUSES = set(SCHEMA["inbox"]["statuses"])
    SUGGESTED_TYPES = set(SCHEMA["inbox"]["suggested_types"])
    source_contract = SCHEMA["json_contracts"]["source_manifest"]
    review_contract = SCHEMA["json_contracts"]["review_queue"]
    SOURCE_TYPES = set(source_contract["source_types"])
    SOURCE_STATUSES = set(source_contract["statuses"])
    SOURCE_ADAPTERS = set(source_contract["adapters"])
    REVIEW_TYPES = set(review_contract["types"])
    REVIEW_STATUSES = set(review_contract["statuses"])
    PRIORITIES = set(review_contract["priorities"])
    TYPE_PREFIX = type_prefix(SCHEMA)
    WIKI_ID_RE = effective_id_regex(SCHEMA)
    INBOX_ID_RE = re.compile(SCHEMA["inbox"]["id_pattern"])
    INBOX_FILE_RE = re.compile(SCHEMA["inbox"]["file_pattern"])
    DATE_RE = re.compile(SCHEMA["format_patterns"]["date"])
    ISO_RE = re.compile(SCHEMA["format_patterns"]["iso"])
    HASH_RE = re.compile(SCHEMA["format_patterns"]["hash"])
    ERROR_LEVEL = dict(SCHEMA["error_level"])


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


def read_json(path: Path, errors: List[Issue]) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        errors.append(Issue("TYPE_MISMATCH", rel_to_knowledge(path), None, None, f"JSON 解析失败: {exc}", "修复 JSON 格式"))
        return {}


def load_markdown(path: Path) -> MarkdownDoc:
    return common_load_markdown(path, INSTANCE_ROOT)


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


def add_trust_warnings(doc: MarkdownDoc, now: date_cls, issues: Dict[str, List[Issue]]) -> None:
    page_type = doc.fm.get("type")
    status_value = doc.fm.get("status")
    last_verified = doc.fm.get("last_verified")
    threshold = staleness_threshold(page_type, SCHEMA)
    age = staleness_age_days(last_verified, now)
    if is_stale(page_type, status_value, last_verified, now, SCHEMA):
        add_issue(
            issues,
            issue(
                "STALE_PAGE",
                doc.rel,
                line_for(doc, "last_verified"),
                "last_verified",
                f"距上次核实 {age} 天，超过阈值 {threshold} 天",
                "复核后更新 last_verified，或下调 confidence / 改 status: stale",
            ),
        )
    if (
        status_value == "active"
        and page_type not in {"source", "query"}
        and doc.fm.get("confidence") == "high"
        and doc.fm.get("review") is False
    ):
        add_issue(
            issues,
            issue(
                "UNVERIFIED_HIGH",
                doc.rel,
                line_for(doc, "review"),
                "review",
                "高置信但未经人工确认：确认后置 `review: true`，否则考虑降为 medium。",
                "确认后置 review: true，否则考虑降为 medium",
            ),
        )


def is_list(value: Any) -> bool:
    return isinstance(value, list)


def check_list_type(doc: MarkdownDoc, field: str, issues: Dict[str, List[Issue]]) -> None:
    if field in doc.fm and not isinstance(doc.fm.get(field), list):
        add_issue(issues, issue("TYPE_MISMATCH", doc.rel, line_for(doc, field), field, f"{field} 必须是数组", "使用 YAML list 或 []"))


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


def _patterns_from_redact_config(value: Any, rel: str, field: str, issues: Dict[str, List[Issue]]) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        patterns = value
    elif isinstance(value, dict):
        if "patterns" not in value:
            add_issue(issues, issue("TYPE_MISMATCH", rel, None, field, f"{field} 必须包含 patterns 数组", "使用 {\"patterns\": [...]} 或字符串数组"))
            return []
        patterns = value.get("patterns")
    else:
        add_issue(issues, issue("TYPE_MISMATCH", rel, None, field, f"{field} 必须是对象或字符串数组", "使用 {\"patterns\": [...]} 或字符串数组"))
        return []
    if not isinstance(patterns, list) or not all(isinstance(item, str) for item in patterns):
        add_issue(issues, issue("TYPE_MISMATCH", rel, None, field, f"{field}.patterns 必须是字符串数组", "使用字符串数组"))
        return []
    return list(patterns)


def _validate_regex_patterns(patterns: List[str], rel: str, field: str, issues: Dict[str, List[Issue]]) -> None:
    for pat in patterns:
        try:
            re.compile(str(pat), re.IGNORECASE)
        except re.error:
            add_issue(issues, issue("TYPE_MISMATCH", rel, None, field, f"正则无效: {pat}", "修正正则"))


def default_visibility(capture_policy: Dict[str, Any]) -> str:
    value = capture_policy.get("default_visibility")
    return value if isinstance(value, str) and value in VISIBILITIES else "private"


def effective_visibility(raw: Any, capture_policy: Dict[str, Any]) -> str:
    return raw if isinstance(raw, str) and raw in VISIBILITIES else default_visibility(capture_policy)


def normalized_redact_patterns(capture_policy: Dict[str, Any], issues: Dict[str, List[Issue]]) -> Tuple[List[str], List[str]]:
    rel = ".wiki/capture_policy.json"
    contract = SCHEMA["json_contracts"]["capture_policy"]
    hard = _patterns_from_redact_config(capture_policy.get("hard_redact"), rel, "hard_redact", issues)
    if "hard_redact" not in capture_policy:
        hard = _patterns_from_redact_config(contract.get("hard_redact"), rel, "hard_redact", issues)
    soft = _patterns_from_redact_config(capture_policy.get("soft_redact"), rel, "soft_redact", issues)
    if "soft_redact" not in capture_policy and "exclude_patterns" in capture_policy:
        legacy = capture_policy.get("exclude_patterns")
        if isinstance(legacy, list) and all(isinstance(item, str) for item in legacy):
            soft = list(legacy)
    _validate_regex_patterns(hard, rel, "hard_redact", issues)
    _validate_regex_patterns(soft, rel, "soft_redact" if "soft_redact" in capture_policy else "exclude_patterns", issues)
    return hard, soft


def scan_markdown_files() -> Tuple[List[MarkdownDoc], List[MarkdownDoc], List[MarkdownDoc]]:
    wiki_docs = [load_markdown(p) for p in sorted((INSTANCE_ROOT / "wiki").glob("**/*.md"))]
    inbox_docs = [load_markdown(p) for p in sorted((INSTANCE_ROOT / "inbox").glob("*.md"))]
    inbox_archived = [load_markdown(p) for p in sorted((INSTANCE_ROOT / "inbox/archive").glob("**/*.md"))]
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


def validate_wiki_docs(wiki_docs: List[MarkdownDoc], issues: Dict[str, List[Issue]], now: date_cls) -> None:
    required_common = SCHEMA["core_required_fields"]
    for doc in wiki_docs:
        if not doc.has_frontmatter:
            add_issue(issues, issue("MISSING_FIELD", doc.rel, 1, None, "wiki 页面缺少 frontmatter", "补齐标准 frontmatter"))
            continue
        require_fields(doc, required_common, issues)
        check_enum(doc, "type", PAGE_TYPES, issues)
        check_enum(doc, "status", PAGE_STATUSES, issues)
        check_enum(doc, "confidence", CONFIDENCES, issues)
        check_enum(doc, "visibility", VISIBILITIES, issues)
        check_bool(doc, "review", issues)
        for field in ("created", "updated", "last_verified"):
            check_date_field(doc, field, issues)
        add_trust_warnings(doc, now, issues)
        if "id" in doc.fm and not validate_wiki_id(doc.fm.get("id"), doc.fm.get("type")):
            add_issue(issues, issue("ID_FORMAT", doc.rel, line_for(doc, "id"), "id", "wiki 页面 id 格式不符或 prefix 与 type 不匹配", "使用 <prefix>_YYYYMMDD_<slug>"))
        if doc.fm.get("status") == "redirect" and doc.fm.get("type") != "entity":
            add_issue(issues, issue("ENUM_INVALID", doc.rel, line_for(doc, "status"), "status", "redirect 只能用于 entity 页", "改为合法状态或改为 entity"))
        for field in SCHEMA["canonical_list_fields"] + ["aliases"]:
            check_list_type(doc, field, issues)
        page_type_cfg = SCHEMA["page_types"].get(str(doc.fm.get("type")), {})
        require_fields(doc, page_type_cfg.get("required_fields", []), issues)
        for field, allowed in SCHEMA.get("field_enums", {}).items():
            if field in doc.fm:
                check_enum(doc, field, set(allowed), issues)
        if doc.fm.get("type") == "source":
            for field in SCHEMA["source_required_fields"]:
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
    required = SCHEMA["inbox"]["required_fields"]
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
        if doc.path.parent == INSTANCE_ROOT / "inbox" and not validate_inbox_filename(doc.path.name):
            add_issue(issues, issue("ID_FORMAT", doc.rel, None, "filename", "inbox 文件名必须是 YYYYMMDD-HHmmss-<slug>.md", "使用秒级文件名"))
        if "/archive/promoted/" in doc.rel and doc.fm.get("status") != "promoted":
            add_issue(issues, issue("INBOX_STATUS_PATH_MISMATCH", doc.rel, line_for(doc, "status"), "status", "archive/promoted 下 status 必须是 promoted", "修正 status"))
        if "/archive/dropped/" in doc.rel and doc.fm.get("status") != "dropped":
            add_issue(issues, issue("INBOX_STATUS_PATH_MISMATCH", doc.rel, line_for(doc, "status"), "status", "archive/dropped 下 status 必须是 dropped", "修正 status"))


def validate_context_docs(issues: Dict[str, List[Issue]]) -> None:
    for name in SCHEMA["context_docs"]:
        path = INSTANCE_ROOT / name
        if path.exists() and path.read_text(encoding="utf-8").startswith("---\n"):
            add_issue(issues, issue("EXTRA_FRONTMATTER", rel_to_knowledge(path), 1, None, "上下文层 markdown 不应有 frontmatter", "移除 frontmatter"))


def validate_json_contracts(id_index: Dict[str, MarkdownDoc], issues: Dict[str, List[Issue]]) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    source_manifest_path = INSTANCE_ROOT / SCHEMA["json_contracts"]["source_manifest"]["path"]
    review_queue_path = INSTANCE_ROOT / SCHEMA["json_contracts"]["review_queue"]["path"]
    capture_policy_path = INSTANCE_ROOT / SCHEMA["json_contracts"]["capture_policy"]["path"]
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
    if "exclude_patterns" in capture_policy:
        if not (isinstance(capture_policy.get("exclude_patterns"), list) and all(isinstance(x, str) for x in capture_policy.get("exclude_patterns", []))):
            add_issue(issues, issue("TYPE_MISMATCH", ".wiki/capture_policy.json", None, "exclude_patterns", "exclude_patterns 必须是字符串数组", "使用字符串数组"))
        else:
            add_issue(
                issues,
                issue(
                    "CAPTURE_POLICY_LEGACY",
                    ".wiki/capture_policy.json",
                    None,
                    "exclude_patterns",
                    "capture_policy 仍使用 v1 exclude_patterns；lint 已按 soft_redact legacy alias 兼容",
                    "迁移到 hard_redact / soft_redact / default_visibility",
                ),
            )
    if not (isinstance(capture_policy.get("max_inbox_files"), int) and capture_policy.get("max_inbox_files") > 0):
        add_issue(issues, issue("TYPE_MISMATCH", ".wiki/capture_policy.json", None, "max_inbox_files", "max_inbox_files 必须是正整数", "设置为正整数"))
    if "default_visibility" in capture_policy and capture_policy.get("default_visibility") not in VISIBILITIES:
        add_issue(issues, issue("ENUM_INVALID", ".wiki/capture_policy.json", None, "default_visibility", "default_visibility 非法", "使用 public/internal/private"))
    normalized_redact_patterns(capture_policy, issues)

    for idx, src in enumerate(source_manifest.get("sources", []) if isinstance(source_manifest.get("sources", []), list) else []):
        rel = "raw/source_manifest.json"
        for field in SCHEMA["json_contracts"]["source_manifest"]["required_fields"]:
            if field not in src:
                add_issue(issues, issue("MISSING_FIELD", rel, None, field, f"sources[{idx}] 缺少 {field}", "补齐字段"))
        if src.get("source_type") not in SOURCE_TYPES:
            add_issue(issues, issue("ENUM_INVALID", rel, None, "source_type", "source_type 非法", "使用合法 source_type"))
        if src.get("status") not in SOURCE_STATUSES:
            add_issue(issues, issue("ENUM_INVALID", rel, None, "status", "source status 非法", "使用合法 status"))
        if src.get("adapter") not in SOURCE_ADAPTERS:
            add_issue(issues, issue("ENUM_INVALID", rel, None, "adapter", "adapter 非法", "使用合法 adapter"))
        if "visibility" in src and src.get("visibility") not in VISIBILITIES:
            add_issue(issues, issue("ENUM_INVALID", rel, None, "visibility", f"sources[{idx}].visibility 非法", "使用 public/internal/private"))
        if not (isinstance(src.get("hash_sha256"), str) and HASH_RE.match(src.get("hash_sha256", ""))):
            add_issue(issues, issue("HASH_FORMAT", rel, None, "hash_sha256", "hash_sha256 必须是 64 位小写十六进制", "重新计算 hash"))
        check_date_json(src.get("imported_at"), rel, "imported_at", issues)
        check_date_json(src.get("last_ingested_at"), rel, "last_ingested_at", issues)
        sid, summary_id = src.get("source_id"), src.get("summary_page_id")
        if summary_id is not None and summary_id != sid:
            add_issue(issues, issue("SOURCE_KEY_MISMATCH", rel, None, "summary_page_id", "summary_page_id 必须等于 source_id 或 null", "统一 source_id"))
        summary_path = src.get("summary_page_path")
        if summary_path is not None:
            full = INSTANCE_ROOT / str(summary_path)
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


def compile_patterns(patterns: List[str], field: str, issues: Dict[str, List[Issue]]) -> List[Tuple[str, re.Pattern[str]]]:
    compiled: List[Tuple[str, re.Pattern[str]]] = []
    for pat in patterns:
        try:
            compiled.append((pat, re.compile(str(pat), re.IGNORECASE)))
        except re.error:
            add_issue(issues, issue("TYPE_MISMATCH", ".wiki/capture_policy.json", None, field, f"正则无效: {pat}", "修正正则"))
    return compiled


def scan_pii(inbox_docs: List[MarkdownDoc], archived: List[MarkdownDoc], wiki_docs: List[MarkdownDoc], capture_policy: Dict[str, Any], scan_wiki: bool, issues: Dict[str, List[Issue]]) -> int:
    hard_patterns, soft_patterns = normalized_redact_patterns(capture_policy, issues)
    hard_compiled = compile_patterns(hard_patterns, "hard_redact", issues)
    soft_compiled = compile_patterns(soft_patterns, "soft_redact", issues)
    hits = 0

    def scan_doc(doc: MarkdownDoc) -> None:
        nonlocal hits
        text = doc.path.read_text(encoding="utf-8")
        visibility = effective_visibility(doc.fm.get("visibility"), capture_policy)
        for lineno, line in enumerate(text.splitlines(), start=1):
            for raw, regex in hard_compiled:
                if regex.search(line):
                    hits += 1
                    add_issue(issues, issue("HARD_REDACT_HIT", doc.rel, lineno, None, f"命中 hard_redact pattern {raw!r}", "移除密钥/凭证/连接串等硬底线敏感内容"))
                    return
            for raw, regex in soft_compiled:
                if regex.search(line):
                    hits += 1
                    hint = "公开内容命中 soft_redact；发布前请确认可公开" if visibility == "public" else "按库策略人工确认或脱敏"
                    add_issue(issues, issue("SOFT_REDACT_HIT", doc.rel, lineno, None, f"命中 soft_redact pattern {raw!r}", hint))
                    return

    for doc in inbox_docs:
        scan_doc(doc)
    for doc in archived:
        scan_doc(doc)
    if scan_wiki:
        for doc in wiki_docs:
            scan_doc(doc)
    return hits


def body_line_for_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def clean_markdown_target(raw: str, *, obsidian: bool = False) -> str:
    target = raw.strip()
    if obsidian:
        target = target.split("|", 1)[0].strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1].strip()
    return target


def is_nonlocal_image_target(target: str) -> bool:
    return target.lower().startswith(NONLOCAL_IMAGE_SCHEMES)


def path_is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def image_refs(doc: MarkdownDoc) -> List[Dict[str, Any]]:
    stripped = strip_code_spans(doc.body)
    refs: List[Dict[str, Any]] = []
    for match in MARKDOWN_IMAGE_RE.finditer(stripped):
        refs.append(
            {
                "target": clean_markdown_target(match.group(2)),
                "alt": match.group(1).strip(),
                "line": body_line_for_offset(stripped, match.start()),
            }
        )
    for match in OBSIDIAN_IMAGE_RE.finditer(stripped):
        refs.append(
            {
                "target": clean_markdown_target(match.group(1), obsidian=True),
                "alt": "",
                "line": body_line_for_offset(stripped, match.start()),
            }
        )
    refs.sort(key=lambda item: item["line"])
    return refs


def image_description_near_line(doc: MarkdownDoc, line_number: int) -> str:
    lines = doc.body.splitlines()
    if line_number < 1 or line_number > len(lines):
        return ""
    idx = line_number - 1
    chunks: List[str] = []
    for candidate in [lines[idx], *lines[idx + 1 : idx + 4]]:
        cleaned = MARKDOWN_IMAGE_RE.sub(" ", candidate)
        cleaned = OBSIDIAN_IMAGE_RE.sub(" ", cleaned)
        cleaned = cleaned.strip()
        if cleaned:
            chunks.append(cleaned)
    return "\n".join(chunks)


def manifest_image_text_by_source(source_manifest: Dict[str, Any]) -> Dict[str, str]:
    def collect(value: Any, active: bool = False) -> List[str]:
        if isinstance(value, str):
            return [value] if active else []
        if isinstance(value, list):
            result: List[str] = []
            for item in value:
                result.extend(collect(item, active))
            return result
        if isinstance(value, dict):
            result = []
            for key, item in value.items():
                key_active = active or any(token in str(key).lower() for token in ("note", "caption", "description"))
                result.extend(collect(item, key_active))
            return result
        return []

    result: Dict[str, str] = {}
    sources = source_manifest.get("sources", [])
    if not isinstance(sources, list):
        return result
    for src in sources:
        if not isinstance(src, dict) or not isinstance(src.get("source_id"), str):
            continue
        text = "\n".join(collect(src))
        if text:
            result[src["source_id"]] = text
    return result


def source_ids_for_doc(doc: MarkdownDoc) -> List[str]:
    ids: List[str] = []
    if isinstance(doc.fm.get("source_ids"), list):
        ids.extend(str(item) for item in doc.fm.get("source_ids", []) if isinstance(item, str))
    if isinstance(doc.fm.get("source_id"), str):
        ids.append(str(doc.fm["source_id"]))
    return list(dict.fromkeys(ids))


def first_pattern_hit(text: str, compiled: List[Tuple[str, re.Pattern[str]]]) -> Optional[str]:
    if not text:
        return None
    for raw, regex in compiled:
        if regex.search(text):
            return raw
    return None


def validate_image_refs(
    wiki_docs: List[MarkdownDoc],
    source_manifest: Dict[str, Any],
    capture_policy: Dict[str, Any],
    issues: Dict[str, List[Issue]],
) -> None:
    hard_patterns, _soft_patterns = normalized_redact_patterns(capture_policy, issues)
    hard_compiled = compile_patterns(hard_patterns, "hard_redact", issues)
    manifest_texts = manifest_image_text_by_source(source_manifest)
    instance_root = INSTANCE_ROOT.resolve()

    for doc in wiki_docs:
        doc_manifest_text = "\n".join(manifest_texts.get(src_id, "") for src_id in source_ids_for_doc(doc))
        for ref in image_refs(doc):
            target = ref["target"]
            line = ref["line"]
            if not target or is_nonlocal_image_target(target):
                continue
            target_path = (doc.path.parent / target).resolve()
            description = image_description_near_line(doc, line)
            scan_text = "\n".join(
                item
                for item in [
                    target,
                    target_path.name,
                    rel_to_knowledge(target_path) if path_is_relative_to(target_path, instance_root) else str(target_path),
                    description,
                    doc_manifest_text,
                ]
                if item
            )
            matched_pattern = first_pattern_hit(scan_text, hard_compiled)
            if matched_pattern:
                add_issue(
                    issues,
                    issue(
                        "IMAGE_HARD_REDACT",
                        doc.rel,
                        line,
                        None,
                        f"图片引用或相邻说明命中 hard_redact pattern {matched_pattern!r}",
                        "移除敏感路径/文件名/说明，含硬底线信息的图不要落地",
                    ),
                )
            if not path_is_relative_to(target_path, instance_root):
                add_issue(
                    issues,
                    issue(
                        "IMAGE_PATH_ESCAPE",
                        doc.rel,
                        line,
                        None,
                        f"图片引用逃出实例根: {target}",
                        "使用实例根内 raw/sources/assets/ 的相对路径",
                    ),
                )
                continue
            if not target_path.exists():
                add_issue(
                    issues,
                    issue(
                        "IMAGE_DANGLING",
                        doc.rel,
                        line,
                        None,
                        f"图片引用目标不存在: {target}",
                        "修正相对路径或补齐 raw/sources/assets/ 文件",
                    ),
                )
            if not description:
                add_issue(
                    issues,
                    issue(
                        "IMAGE_NO_DESCRIPTION",
                        doc.rel,
                        line,
                        None,
                        f"图片引用缺少紧邻描述文本: {target}",
                        "在图片同一行或随后 3 行补充多模态描述",
                    ),
                )


def run_lint(args: argparse.Namespace) -> Tuple[int, Dict[str, Any], str]:
    issues: Dict[str, List[Issue]] = {"errors": [], "warnings": []}
    for item in PROFILE_ISSUES:
        add_issue(issues, issue(item.code, ".wiki-profile.json", None, item.field, item.message, item.hint))
    if PROFILE_ISSUES:
        data = {
            "wiki_lint_version": VERSION,
            "ran_at": now_iso(),
            "scanned": {
                "wiki_pages": 0,
                "inbox_drafts": 0,
                "inbox_archived": 0,
                "sources": 0,
                "review_queue_items": 0,
            },
            "errors": [i.as_json() for i in issues["errors"]],
            "warnings": [i.as_json() for i in issues["warnings"]],
            "derived_layers": {
                "id_index_entries": 0,
                "normalized_alias_index_entries": 0,
                "inbox_index_drafts": 0,
                "written": False,
            },
        }
        return 1, data, human_output(data, 0, args)

    validate_context_docs(issues)
    wiki_docs, inbox_docs, archived_docs = scan_markdown_files()
    validate_wiki_docs(wiki_docs, issues, args.now)
    validate_inbox_docs(inbox_docs, archived_docs, issues)
    id_index = build_id_index(wiki_docs, issues)
    validate_canonical(wiki_docs, id_index, issues)
    source_manifest, review_queue, capture_policy = validate_json_contracts(id_index, issues)
    alias_entries = build_alias_index(wiki_docs, id_index, issues)
    inbox_index = build_inbox_index(inbox_docs, issues)
    validate_image_refs(wiki_docs, source_manifest, capture_policy, issues)
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
        write_json_atomic(INSTANCE_ROOT / ".wiki/id_index.json", {"version": 1, "updated_at": now_iso(), "entries": id_entries})
        write_json_atomic(INSTANCE_ROOT / ".wiki/normalized_alias_index.json", {"version": 1, "updated_at": now_iso(), "entries": alias_entries})
        write_json_atomic(INSTANCE_ROOT / ".wiki/inbox_index.json", inbox_index)

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


def _lint_state() -> Dict[str, Any]:
    return {
        "ROOT": ROOT,
        "INSTANCE_ROOT": INSTANCE_ROOT,
        "SCHEMA": SCHEMA,
        "PROFILE_NAME": PROFILE_NAME,
        "PROFILE_ISSUES": list(PROFILE_ISSUES),
        "PAGE_TYPES": set(PAGE_TYPES),
        "PAGE_STATUSES": set(PAGE_STATUSES),
        "CONFIDENCES": set(CONFIDENCES),
        "VISIBILITIES": set(VISIBILITIES),
        "INBOX_STATUSES": set(INBOX_STATUSES),
        "SUGGESTED_TYPES": set(SUGGESTED_TYPES),
        "SOURCE_TYPES": set(SOURCE_TYPES),
        "SOURCE_STATUSES": set(SOURCE_STATUSES),
        "SOURCE_ADAPTERS": set(SOURCE_ADAPTERS),
        "REVIEW_TYPES": set(REVIEW_TYPES),
        "REVIEW_STATUSES": set(REVIEW_STATUSES),
        "PRIORITIES": set(PRIORITIES),
        "TYPE_PREFIX": dict(TYPE_PREFIX),
        "WIKI_ID_RE": WIKI_ID_RE,
        "INBOX_ID_RE": INBOX_ID_RE,
        "INBOX_FILE_RE": INBOX_FILE_RE,
        "DATE_RE": DATE_RE,
        "ISO_RE": ISO_RE,
        "HASH_RE": HASH_RE,
        "ERROR_LEVEL": dict(ERROR_LEVEL),
    }


def _restore_lint_state(state: Dict[str, Any]) -> None:
    global ROOT, INSTANCE_ROOT, SCHEMA, PROFILE_NAME, PROFILE_ISSUES
    global PAGE_TYPES, PAGE_STATUSES, CONFIDENCES, VISIBILITIES, INBOX_STATUSES, SUGGESTED_TYPES
    global SOURCE_TYPES, SOURCE_STATUSES, SOURCE_ADAPTERS, REVIEW_TYPES, REVIEW_STATUSES, PRIORITIES
    global TYPE_PREFIX, WIKI_ID_RE, INBOX_ID_RE, INBOX_FILE_RE, DATE_RE, ISO_RE, HASH_RE, ERROR_LEVEL

    ROOT = state["ROOT"]
    INSTANCE_ROOT = state["INSTANCE_ROOT"]
    SCHEMA = state["SCHEMA"]
    PROFILE_NAME = state["PROFILE_NAME"]
    PROFILE_ISSUES = state["PROFILE_ISSUES"]
    PAGE_TYPES = state["PAGE_TYPES"]
    PAGE_STATUSES = state["PAGE_STATUSES"]
    CONFIDENCES = state["CONFIDENCES"]
    VISIBILITIES = state["VISIBILITIES"]
    INBOX_STATUSES = state["INBOX_STATUSES"]
    SUGGESTED_TYPES = state["SUGGESTED_TYPES"]
    SOURCE_TYPES = state["SOURCE_TYPES"]
    SOURCE_STATUSES = state["SOURCE_STATUSES"]
    SOURCE_ADAPTERS = state["SOURCE_ADAPTERS"]
    REVIEW_TYPES = state["REVIEW_TYPES"]
    REVIEW_STATUSES = state["REVIEW_STATUSES"]
    PRIORITIES = state["PRIORITIES"]
    TYPE_PREFIX = state["TYPE_PREFIX"]
    WIKI_ID_RE = state["WIKI_ID_RE"]
    INBOX_ID_RE = state["INBOX_ID_RE"]
    INBOX_FILE_RE = state["INBOX_FILE_RE"]
    DATE_RE = state["DATE_RE"]
    ISO_RE = state["ISO_RE"]
    HASH_RE = state["HASH_RE"]
    ERROR_LEVEL = state["ERROR_LEVEL"]


def evaluate_instance(root: Path, *, now: Optional[date_cls] = None, scan_wiki_pii: bool = False) -> Dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[1]
    requested_root = Path(root).resolve()
    if not requested_root.is_dir():
        return {
            "exit_code": 2,
            "data": {
                "wiki_lint_version": VERSION,
                "ran_at": now_iso(),
                "scanned": {"wiki_pages": 0, "inbox_drafts": 0, "inbox_archived": 0, "sources": 0, "review_queue_items": 0},
                "errors": [],
                "warnings": [],
                "derived_layers": {"id_index_entries": 0, "normalized_alias_index_entries": 0, "inbox_index_drafts": 0, "written": False},
            },
            "human": f"wiki-lint config error: instance root not found: {requested_root}",
        }
    original_cwd = Path.cwd()
    state = _lint_state()
    args = argparse.Namespace(
        root=str(requested_root),
        check_only=True,
        json_output=False,
        scan_wiki_pii=scan_wiki_pii,
        now=now or datetime.now(LOCAL_TZ).date(),
    )
    try:
        os.chdir(repo_root)
        configure(args)
        code, data, human = run_lint(args)
        return {"exit_code": code, "data": data, "human": human}
    except SystemExit as exc:
        return {
            "exit_code": int(exc.code) if isinstance(exc.code, int) else 2,
            "data": {
                "wiki_lint_version": VERSION,
                "ran_at": now_iso(),
                "scanned": {"wiki_pages": 0, "inbox_drafts": 0, "inbox_archived": 0, "sources": 0, "review_queue_items": 0},
                "errors": [],
                "warnings": [],
                "derived_layers": {"id_index_entries": 0, "normalized_alias_index_entries": 0, "inbox_index_drafts": 0, "written": False},
            },
            "human": "wiki-lint config error",
        }
    finally:
        os.chdir(original_cwd)
        _restore_lint_state(state)


def status(ok: bool) -> str:
    return "[OK]    " if ok else "[FAIL]  "


def human_output(data: Dict[str, Any], pii_hits: int, args: argparse.Namespace) -> str:
    errors, warnings = data["errors"], data["warnings"]
    scanned = data["scanned"]
    derived = data["derived_layers"]
    lines = [
        f"wiki-lint v{VERSION}",
        "================",
        f"实例: {INSTANCE_ROOT} · profile: {PROFILE_NAME}",
        f"扫描: {INSTANCE_ROOT.name}/wiki/ ({scanned['wiki_pages']} 文件) · {INSTANCE_ROOT.name}/inbox/ ({scanned['inbox_drafts']} draft) · {INSTANCE_ROOT.name}/raw/ ({scanned['sources']} source)",
        "",
        f"{status(not any(e['code'] in {'MISSING_FIELD','EXTRA_FRONTMATTER','ENUM_INVALID','DATE_FORMAT','HASH_FORMAT','JSON_VERSION','TYPE_MISMATCH','ID_FORMAT'} for e in errors))}schema 校验: {scanned['wiki_pages'] + scanned['inbox_drafts']} 页扫描",
        f"{status(not any(e['code'] in {'ID_DUPLICATE','ID_FORMAT'} for e in errors))}ID 唯一性: {derived['id_index_entries']} 个 id",
        f"{status(not any(e['code'] in {'CANONICAL_DANGLING','SUPERSEDES_ASYMMETRY'} for e in errors))}canonical 引用 + supersedes 对称",
        f"{status(not any(e['code'] in {'SOURCE_KEY_MISMATCH','SUMMARY_PATH_MISSING'} for e in errors))}source 单主键",
        f"{status(not any(e['code'] in {'ALIAS_CONFLICT','CANONICAL_CHAIN','REDIRECT_INVALID'} for e in errors))}entity 别名（含链式跳转 / status:redirect）: {derived['normalized_alias_index_entries']} entries",
        f"{status(not any(e['code'] == 'INBOX_STATUS_PATH_MISMATCH' for e in errors))}inbox: {derived['inbox_index_drafts']} draft",
        f"{status(not any(e['code'].startswith('PII_HIT') or e['code'] == 'HARD_REDACT_HIT' for e in errors))}脱敏扫描（{'inbox + wiki' if args.scan_wiki_pii else 'inbox-only'}）: {pii_hits} 命中",
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


def main() -> int:
    parser = argparse.ArgumentParser(description="wiki-lint MVP")
    parser.add_argument("--root", help="实例根目录；缺省为 ./knowledge")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--scan-wiki-pii", action="store_true")
    parser.add_argument("--now", type=lambda value: datetime.strptime(value, "%Y-%m-%d").date(), help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.now is None:
        args.now = datetime.now(LOCAL_TZ).date()
    configure(args)
    print(f"wiki-lint instance root: {INSTANCE_ROOT} · profile: {PROFILE_NAME}", file=sys.stderr)
    code, data, text = run_lint(args)
    if args.json_output:
        print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(text)
    return code

if __name__ == "__main__":
    sys.exit(main())
