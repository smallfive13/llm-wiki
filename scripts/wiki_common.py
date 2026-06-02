#!/usr/bin/env python3
"""Shared pure helpers for llm-wiki maintenance scripts."""

from __future__ import annotations

import json
import os
import re
import uuid
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


LOCAL_TZ = timezone(timedelta(hours=8))


BASE_SCHEMA: Dict[str, Any] = {
    "schema_version": 1,
    "page_types": {
        "source": {"id_prefix": "src", "dir": "wiki/sources", "required_fields": [], "optional_fields": []},
        "entity": {"id_prefix": "ent", "dir": "wiki/entities", "required_fields": [], "optional_fields": []},
        "topic": {"id_prefix": "top", "dir": "wiki/topics", "required_fields": [], "optional_fields": []},
        "comparison": {"id_prefix": "cmp", "dir": "wiki/comparisons", "required_fields": [], "optional_fields": []},
        "synthesis": {"id_prefix": "syn", "dir": "wiki/synthesis", "required_fields": [], "optional_fields": []},
        "decision": {"id_prefix": "dec", "dir": "wiki/decisions", "required_fields": [], "optional_fields": []},
        "query": {"id_prefix": "que", "dir": "wiki/queries", "required_fields": [], "optional_fields": []},
        "open-question": {"id_prefix": "oq", "dir": "wiki/open-questions", "required_fields": [], "optional_fields": []},
    },
    "inbox": {
        "id_prefix": "inb",
        "statuses": ["draft", "promoted", "dropped"],
        "suggested_types": ["topic", "entity", "comparison", "synthesis", "decision", "query", "open-question"],
        "required_fields": [
            "id",
            "type",
            "status",
            "confidence",
            "review",
            "suggested_target_type",
            "suggested_target_title",
            "created",
        ],
        "id_pattern": r"^inb_(\d{8})_(\d{6})_([a-z0-9][a-z0-9-]*)(?:-(\d{2,3}))?$",
        "file_pattern": r"^(\d{8})-(\d{6})-([a-z0-9][a-z0-9-]*)(?:-\d{2,3})?\.md$",
    },
    "format_patterns": {
        "date": r"^\d{4}-\d{2}-\d{2}$",
        "iso": r"^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})(\.\d+)?(Z|[+-]\d{2}:?\d{2})$",
        "hash": r"^[0-9a-f]{64}$",
    },
    "core_required_fields": ["id", "type", "status", "confidence", "created", "updated", "last_verified", "review"],
    "core_enums": {
        "status": ["draft", "active", "stale", "archived", "redirect"],
        "confidence": ["low", "medium", "high"],
    },
    "canonical_list_fields": ["source_ids", "related_ids", "supersedes", "superseded_by"],
    "source_required_fields": ["source_id", "hash_sha256", "original_path", "source_url", "imported_at"],
    "entity_fields": ["aliases", "canonical_id"],
    "json_contracts": {
        "source_manifest": {
            "path": "raw/source_manifest.json",
            "required_fields": [
                "source_id",
                "title",
                "source_type",
                "hash_sha256",
                "original_path",
                "source_url",
                "imported_at",
                "last_ingested_at",
                "status",
                "summary_page_id",
                "summary_page_path",
                "adapter",
            ],
            "source_types": ["pdf", "markdown", "web", "chat", "image", "manual", "code"],
            "statuses": ["new", "triaged", "ingested", "skipped", "failed", "deleted"],
            "adapters": ["local_file", "web_clipper", "manual", "llm_wiki_app", "custom"],
        },
        "review_queue": {
            "path": ".wiki/review_queue.json",
            "item_required_fields": [],
            "types": ["contradiction", "duplicate", "missing_page", "confirm", "suggestion", "source_gap", "stale_claim"],
            "statuses": ["pending", "resolved", "dismissed"],
            "priorities": ["low", "medium", "high"],
        },
        "capture_policy": {
            "path": ".wiki/capture_policy.json",
            "required_fields": ["version", "auto_capture", "exclude_patterns", "exclude_paths", "max_inbox_files", "updated_at"],
            "version": 1,
        },
    },
    "context_docs": ["purpose.md", "index.md", "overview.md", "log.md"],
    "staleness_days": {
        "decision": 120,
        "synthesis": 120,
        "comparison": 120,
        "open-question": 120,
        "topic": 365,
        "entity": 365,
    },
    "field_enums": {},
    "extra_optional_fields": {},
    "error_level": {
        "REVIEW_QUEUE_PATH_DRIFT": "warning",
        "STATUS_NOT_ARCHIVED": "warning",
        "PII_HIT_ARCHIVE": "warning",
        "PII_HIT_WIKI": "warning",
        "STALE_PAGE": "warning",
        "UNVERIFIED_HIGH": "warning",
    },
}

PROFILE_ERROR_CODES = {
    "PROFILE_SCHEMA_VERSION",
    "PROFILE_PREFIX_FORMAT",
    "PROFILE_PREFIX_COLLISION",
    "PROFILE_TYPE_COLLISION",
    "PROFILE_DIR_INVALID",
    "PROFILE_FIELD_INVALID",
    "PROFILE_FIELD_OVERLAP",
    "PROFILE_CORE_SHADOW",
    "PROFILE_ENUM_UNKNOWN_FIELD",
    "PROFILE_OPTFIELD_UNKNOWN_TYPE",
}

PROFILE_NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")
PROFILE_TYPE_RE = re.compile(r"^[a-z][a-z0-9-]*$")
PROFILE_PREFIX_RE = re.compile(r"^[a-z]{2,5}$")
PROFILE_FIELD_RE = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass
class MarkdownDoc:
    path: Path
    rel: str
    fm: Dict[str, Any]
    body: str
    line_map: Dict[str, int]
    has_frontmatter: bool


@dataclass
class ProfileIssue:
    code: str
    field: Optional[str]
    message: str
    hint: str


def now_iso() -> str:
    return datetime.now(LOCAL_TZ).replace(microsecond=0).isoformat()


def parse_ymd_date(value: Any) -> Optional[date]:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def staleness_threshold(page_type: Any, schema: Dict[str, Any]) -> Optional[int]:
    thresholds = schema.get("staleness_days", {})
    if not isinstance(thresholds, dict):
        return None
    value = thresholds.get(str(page_type))
    return value if isinstance(value, int) and value >= 0 else None


def staleness_age_days(last_verified: Any, now: date) -> Optional[int]:
    verified = parse_ymd_date(last_verified)
    if verified is None:
        return None
    return (now - verified).days


def is_stale(page_type: Any, status: Any, last_verified: Any, now: date, schema: Dict[str, Any]) -> bool:
    threshold = staleness_threshold(page_type, schema)
    age = staleness_age_days(last_verified, now)
    return status == "active" and threshold is not None and age is not None and age > threshold


def rel_to_knowledge(path: Path, root: Path) -> str:
    path = path.resolve()
    root = root.resolve()
    legacy = root / "knowledge"
    bases = [legacy, root] if legacy.exists() else [root]
    for base in bases:
        try:
            return path.relative_to(base).as_posix()
        except ValueError:
            continue
    return path.as_posix()


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


def effective_id_regex(schema: Dict[str, Any]) -> re.Pattern[str]:
    prefixes = [str(cfg["id_prefix"]) for cfg in schema.get("page_types", {}).values()]
    pattern = "|".join(re.escape(prefix) for prefix in prefixes)
    return re.compile(rf"^({pattern})_(\d{{8}})_([a-z0-9][a-z0-9-]*)(?:_(\d{{2,3}}))?$")


def type_prefix(schema: Dict[str, Any], include_inbox: bool = True) -> Dict[str, str]:
    prefixes = {page_type: str(cfg["id_prefix"]) for page_type, cfg in schema.get("page_types", {}).items()}
    if include_inbox:
        prefixes["inbox"] = str(schema.get("inbox", {}).get("id_prefix", "inb"))
    return prefixes


def base_field_names(schema: Dict[str, Any]) -> Set[str]:
    fields: Set[str] = set(schema.get("core_required_fields", []))
    fields.update(schema.get("canonical_list_fields", []))
    fields.update(schema.get("source_required_fields", []))
    fields.update(schema.get("entity_fields", []))
    for contract in schema.get("json_contracts", {}).values():
        fields.update(contract.get("required_fields", []))
        fields.update(contract.get("item_required_fields", []))
    fields.update(schema.get("inbox", {}).get("required_fields", []))
    fields.update(schema.get("core_enums", {}).keys())
    fields.update(schema.get("field_enums", {}).keys())
    return fields


def load_profile(instance_root: Path) -> Dict[str, Any]:
    path = instance_root / ".wiki-profile.json"
    if not path.exists():
        return {}
    import yaml

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data if isinstance(data, dict) else {"__invalid_profile_shape__": data}


def profile_name(profile: Dict[str, Any]) -> str:
    value = profile.get("profile")
    return value if isinstance(value, str) and value else "base"


def _profile_issue(code: str, field: str, message: str, hint: str) -> ProfileIssue:
    return ProfileIssue(code, field, message, hint)


def _as_string_list(value: Any) -> Optional[List[str]]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    return value


def validate_profile(profile: Dict[str, Any], base: Dict[str, Any]) -> List[ProfileIssue]:
    if not profile:
        return []
    issues: List[ProfileIssue] = []
    if "__invalid_profile_shape__" in profile:
        return [
            _profile_issue(
                "PROFILE_FIELD_INVALID",
                ".wiki-profile.json",
                ".wiki-profile.json 顶层必须是 object",
                "使用 JSON object 格式",
            )
        ]

    if profile.get("schema_version") != base.get("schema_version"):
        issues.append(
            _profile_issue(
                "PROFILE_SCHEMA_VERSION",
                "schema_version",
                "profile schema_version 与 BASE_SCHEMA 不兼容",
                f"设置为 {base.get('schema_version')}",
            )
        )

    name = profile.get("profile")
    if name is not None and (not isinstance(name, str) or not PROFILE_NAME_RE.match(name)):
        issues.append(_profile_issue("PROFILE_FIELD_INVALID", "profile", "profile 名称格式非法", "使用 ^[a-z][a-z0-9-]*$"))

    base_types = set(base.get("page_types", {}).keys())
    base_prefixes = {str(cfg["id_prefix"]) for cfg in base.get("page_types", {}).values()}
    base_prefixes.add(str(base.get("inbox", {}).get("id_prefix", "inb")))
    base_dirs = {str(cfg["dir"]).rstrip("/") for cfg in base.get("page_types", {}).values()}
    base_fields = base_field_names(base)

    extra_page_types = profile.get("extra_page_types", [])
    if extra_page_types is None:
        extra_page_types = []
    if not isinstance(extra_page_types, list):
        issues.append(_profile_issue("PROFILE_FIELD_INVALID", "extra_page_types", "extra_page_types 必须是数组", "使用 [] 或对象数组"))
        extra_page_types = []

    extra_types: Set[str] = set()
    extra_prefixes: Set[str] = set()
    extra_dirs: Set[str] = set()
    new_fields: Set[str] = set()

    for idx, item in enumerate(extra_page_types):
        loc = f"extra_page_types[{idx}]"
        if not isinstance(item, dict):
            issues.append(_profile_issue("PROFILE_FIELD_INVALID", loc, "extra_page_types 条目必须是 object", "补齐 type/id_prefix/dir"))
            continue

        page_type = item.get("type")
        if not isinstance(page_type, str) or not PROFILE_TYPE_RE.match(page_type):
            issues.append(_profile_issue("PROFILE_FIELD_INVALID", f"{loc}.type", "type 格式非法", "使用 ^[a-z][a-z0-9-]*$"))
        elif page_type in base_types or page_type in extra_types:
            issues.append(_profile_issue("PROFILE_TYPE_COLLISION", f"{loc}.type", f"type {page_type!r} 与已有类型冲突", "换用新的 type"))
        else:
            extra_types.add(page_type)

        prefix = item.get("id_prefix")
        if not isinstance(prefix, str) or not PROFILE_PREFIX_RE.match(prefix):
            issues.append(_profile_issue("PROFILE_PREFIX_FORMAT", f"{loc}.id_prefix", "id_prefix 格式非法", "使用 2-5 位小写字母，不含下划线"))
        elif prefix in base_prefixes or prefix in extra_prefixes:
            issues.append(_profile_issue("PROFILE_PREFIX_COLLISION", f"{loc}.id_prefix", f"id_prefix {prefix!r} 与已有 prefix 冲突", "换用新的 prefix"))
        else:
            extra_prefixes.add(prefix)

        directory = item.get("dir")
        if not isinstance(directory, str):
            issues.append(_profile_issue("PROFILE_DIR_INVALID", f"{loc}.dir", "dir 必须是字符串", "使用 wiki/<dir>"))
        else:
            normalized_dir = directory.rstrip("/")
            parts = Path(normalized_dir).parts
            if not normalized_dir.startswith("wiki/") or ".." in parts or normalized_dir in base_dirs or normalized_dir in extra_dirs:
                issues.append(_profile_issue("PROFILE_DIR_INVALID", f"{loc}.dir", "dir 必须在 wiki/ 下且不能冲突/逃逸", "使用未占用的 wiki/<dir>"))
            else:
                extra_dirs.add(normalized_dir)

        required = _as_string_list(item.get("required_fields", []))
        optional = _as_string_list(item.get("optional_fields", []))
        if required is None:
            issues.append(_profile_issue("PROFILE_FIELD_INVALID", f"{loc}.required_fields", "required_fields 必须是字符串数组", "使用 [] 或字段名数组"))
            required = []
        if optional is None:
            issues.append(_profile_issue("PROFILE_FIELD_INVALID", f"{loc}.optional_fields", "optional_fields 必须是字符串数组", "使用 [] 或字段名数组"))
            optional = []
        for field in required + optional:
            if not PROFILE_FIELD_RE.match(field):
                issues.append(_profile_issue("PROFILE_FIELD_INVALID", f"{loc}.{field}", f"字段名 {field!r} 格式非法", "使用 ^[a-z][a-z0-9_]*$"))
            elif field in base_fields:
                issues.append(_profile_issue("PROFILE_CORE_SHADOW", f"{loc}.{field}", f"字段 {field!r} 覆盖 base/core 字段", "profile 只能新增字段"))
            else:
                new_fields.add(field)
        for field in sorted(set(required).intersection(optional)):
            issues.append(_profile_issue("PROFILE_FIELD_OVERLAP", f"{loc}.{field}", f"字段 {field!r} 同时出现在 required/optional", "只保留在一个列表"))

    extra_optional_fields = profile.get("extra_optional_fields", {}) or {}
    if not isinstance(extra_optional_fields, dict):
        issues.append(_profile_issue("PROFILE_FIELD_INVALID", "extra_optional_fields", "extra_optional_fields 必须是 object", "使用 type -> 字段数组"))
        extra_optional_fields = {}
    known_types = base_types.union(extra_types)
    for page_type, fields in extra_optional_fields.items():
        if page_type not in known_types:
            issues.append(_profile_issue("PROFILE_OPTFIELD_UNKNOWN_TYPE", f"extra_optional_fields.{page_type}", f"type {page_type!r} 不存在", "使用 base type 或 extra type"))
            continue
        field_list = _as_string_list(fields)
        if field_list is None:
            issues.append(_profile_issue("PROFILE_FIELD_INVALID", f"extra_optional_fields.{page_type}", "optional fields 必须是字符串数组", "使用 [] 或字段名数组"))
            continue
        for field in field_list:
            if not PROFILE_FIELD_RE.match(field):
                issues.append(_profile_issue("PROFILE_FIELD_INVALID", f"extra_optional_fields.{page_type}.{field}", f"字段名 {field!r} 格式非法", "使用 ^[a-z][a-z0-9_]*$"))
            elif field in base_fields:
                issues.append(_profile_issue("PROFILE_CORE_SHADOW", f"extra_optional_fields.{page_type}.{field}", f"字段 {field!r} 覆盖 base/core 字段", "profile 只能新增字段"))
            else:
                new_fields.add(field)

    extra_field_enums = profile.get("extra_field_enums", {}) or {}
    if not isinstance(extra_field_enums, dict):
        issues.append(_profile_issue("PROFILE_FIELD_INVALID", "extra_field_enums", "extra_field_enums 必须是 object", "使用 field -> enum 数组"))
        extra_field_enums = {}
    for field, values in extra_field_enums.items():
        if not isinstance(field, str) or not PROFILE_FIELD_RE.match(field):
            issues.append(_profile_issue("PROFILE_FIELD_INVALID", f"extra_field_enums.{field}", "enum 字段名格式非法", "使用 ^[a-z][a-z0-9_]*$"))
            continue
        if field in base_fields:
            issues.append(_profile_issue("PROFILE_CORE_SHADOW", f"extra_field_enums.{field}", f"字段 {field!r} 是 base/core 字段", "profile 不可改写 base 字段 enum"))
        elif field not in new_fields:
            issues.append(_profile_issue("PROFILE_ENUM_UNKNOWN_FIELD", f"extra_field_enums.{field}", f"字段 {field!r} 未由 profile 声明", "先在 required/optional 字段中声明"))
        if _as_string_list(values) is None:
            issues.append(_profile_issue("PROFILE_FIELD_INVALID", f"extra_field_enums.{field}", "enum 值必须是字符串数组", "使用字符串数组"))

    return issues


def merge_schema(base: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
    schema = deepcopy(base)
    if not profile:
        return schema

    page_types = schema.setdefault("page_types", {})
    for item in profile.get("extra_page_types", []) or []:
        page_type = item["type"]
        page_types[page_type] = {
            "id_prefix": item["id_prefix"],
            "dir": item["dir"].rstrip("/"),
            "description": item.get("description"),
            "required_fields": list(item.get("required_fields", [])),
            "optional_fields": list(item.get("optional_fields", [])),
        }

    schema.setdefault("field_enums", {}).update(profile.get("extra_field_enums", {}) or {})
    extra_optional = schema.setdefault("extra_optional_fields", {})
    for page_type, fields in (profile.get("extra_optional_fields", {}) or {}).items():
        extra_optional.setdefault(page_type, [])
        for field in fields:
            if field not in extra_optional[page_type]:
                extra_optional[page_type].append(field)

    suggested = schema.setdefault("inbox", {}).setdefault("suggested_types", [])
    for page_type in page_types:
        if page_type != "source" and page_type not in suggested:
            suggested.append(page_type)
    return schema
