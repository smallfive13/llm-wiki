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
    "schema_version": 2,
    "min_compatible_profile_version": 1,
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
        "visibility": ["public", "internal", "private"],
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
            "statuses": ["new", "triaged", "ingested", "skipped", "failed", "deleted", "superseded", "archived"],
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
            "required_fields": ["version", "auto_capture", "exclude_paths", "max_inbox_files", "updated_at"],
            "legacy_fields": ["exclude_patterns"],
            "optional_fields": ["default_visibility", "hard_redact", "soft_redact", "exclude_patterns"],
            "default_visibility": "private",
            "hard_redact": {
                "patterns": [
                    "AKIA[0-9A-Z]{16}",
                    "LTAI[A-Za-z0-9]{12,}",
                    "access[_ -]?key[_ -]?secret",
                    "secret[_ -]?key",
                    "api[_ -]?key\\s*[:=]",
                    "token\\s*[:=]",
                    "bearer\\s+[A-Za-z0-9._-]+",
                    "password\\s*[:=]",
                    "passwd\\s*[:=]",
                    "密钥",
                    "私钥",
                    "连接串",
                    "connection[_ -]?string",
                    "-----BEGIN (RSA |DSA |EC |OPENSSH |)PRIVATE KEY-----",
                ]
            },
            "soft_redact": {
                "patterns": [
                    "客户(姓名|名单|信息)",
                    "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}",
                    "1[3-9]\\d{9}",
                    "\\b(?:\\d{1,3}\\.){3}\\d{1,3}\\b",
                ]
            },
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
    "health_weights": {
        "integrity": 0.4,
        "freshness": 0.2,
        "endorsement": 0.2,
        "connectivity": 0.2,
    },
    "health_threshold": 70,
    "field_enums": {},
    "extra_optional_fields": {},
    "error_level": {
        "REVIEW_QUEUE_PATH_DRIFT": "warning",
        "STATUS_NOT_ARCHIVED": "warning",
        "PII_HIT_ARCHIVE": "warning",
        "PII_HIT_WIKI": "warning",
        "STALE_PAGE": "warning",
        "UNVERIFIED_HIGH": "warning",
        "CAPTURE_POLICY_LEGACY": "warning",
        "SOFT_REDACT_HIT": "warning",
        "HARD_REDACT_HIT": "error",
        "IMAGE_DANGLING": "error",
        "IMAGE_PATH_ESCAPE": "error",
        "IMAGE_HARD_REDACT": "error",
        "IMAGE_NO_DESCRIPTION": "warning",
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


def clamp_0_100(value: float) -> float:
    return max(0.0, min(100.0, value))


def round_half_up(value: float) -> int:
    return int(value + 0.5)


def ingest_progress(source_manifest: Dict[str, Any], statuses: List[str]) -> Dict[str, Any]:
    counts = {status: 0 for status in statuses}
    pending_apply: List[Dict[str, Any]] = []
    other_count = 0
    sources = source_manifest.get("sources", []) if isinstance(source_manifest, dict) else []
    if not isinstance(sources, list):
        sources = []
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            continue
        status = source.get("status")
        if status in counts:
            counts[status] += 1
        else:
            other_count += 1
        if status == "triaged":
            pending_apply.append(
                {
                    "index": index,
                    "source_id": source.get("source_id"),
                    "title": source.get("title"),
                    "status": status,
                    "summary_page_path": source.get("summary_page_path"),
                }
            )
    return {
        "counts": counts,
        "other_count": other_count,
        "pending_apply_count": len(pending_apply),
        "pending_apply": pending_apply,
    }


DOC_CONSISTENCY_TARGETS = [
    {
        "path": "knowledge/.wiki-schema.md",
        "blocks": [
            "page-types",
            "status-enum",
            "confidence-enum",
            "visibility-enum",
            "source-manifest-status",
            "capture-policy-fields",
        ],
    },
]


def generate_doc_block(name: str) -> str:
    schema = BASE_SCHEMA
    if name == "status-enum":
        return "\n".join(f"- `{item}`" for item in schema["core_enums"]["status"]) + "\n"
    if name == "confidence-enum":
        return "\n".join(f"- `{item}`" for item in schema["core_enums"]["confidence"]) + "\n"
    if name == "visibility-enum":
        return "\n".join(f"- `{item}`" for item in schema["core_enums"]["visibility"]) + "\n"
    if name == "source-manifest-status":
        return "\n".join(f"- `{item}`" for item in schema["json_contracts"]["source_manifest"]["statuses"]) + "\n"
    if name == "page-types":
        lines = ["| type | id_prefix | dir |", "| --- | --- | --- |"]
        for page_type, config in schema["page_types"].items():
            lines.append(f"| `{page_type}` | `{config['id_prefix']}` | `{config['dir']}` |")
        return "\n".join(lines) + "\n"
    if name == "capture-policy-fields":
        contract = schema["json_contracts"]["capture_policy"]
        lines = [
            "| field | kind | note |",
            "| --- | --- | --- |",
        ]
        for field in contract["required_fields"]:
            lines.append(f"| `{field}` | required |  |")
        for field in contract["optional_fields"]:
            if field in contract.get("legacy_fields", []):
                note = "legacy alias for `soft_redact`"
            elif field == "default_visibility":
                note = f"default `{contract['default_visibility']}`"
            else:
                note = ""
            lines.append(f"| `{field}` | optional | {note} |")
        return "\n".join(lines) + "\n"
    raise KeyError(f"unknown generated doc block {name!r}")


def begin_doc_block(name: str) -> str:
    return f"<!-- BEGIN GENERATED: {name} (wiki_lint --check-docs --fix) -->"


def end_doc_block(name: str) -> str:
    return f"<!-- END GENERATED: {name} -->"


def generated_doc_block(name: str) -> str:
    return f"{begin_doc_block(name)}\n{generate_doc_block(name)}{end_doc_block(name)}"


def find_generated_doc_blocks(text: str, name: str) -> Dict[str, Any]:
    begin = begin_doc_block(name)
    end = end_doc_block(name)
    begin_positions = [match.start() for match in re.finditer(re.escape(begin), text)]
    end_positions = [match.start() for match in re.finditer(re.escape(end), text)]
    errors: List[str] = []
    if len(begin_positions) == 0 or len(end_positions) == 0:
        errors.append("missing")
    if len(begin_positions) > 1 or len(end_positions) > 1:
        errors.append("duplicate")
    if errors:
        return {"errors": errors, "start": None, "content_start": None, "content_end": None, "end": None, "content": None}
    start = begin_positions[0]
    end_start = end_positions[0]
    if end_start < start:
        return {"errors": ["missing"], "start": None, "content_start": None, "content_end": None, "end": None, "content": None}
    content_start = start + len(begin)
    if text.startswith("\r\n", content_start):
        content_start += 2
    elif text.startswith("\n", content_start):
        content_start += 1
    content_end = end_start
    content = text[content_start:content_end]
    if begin in content or end in content:
        return {"errors": ["duplicate"], "start": start, "content_start": content_start, "content_end": content_end, "end": end_start + len(end), "content": content}
    return {
        "errors": [],
        "start": start,
        "content_start": content_start,
        "content_end": content_end,
        "end": end_start + len(end),
        "content": content,
    }


def _blank_code_text(text: str) -> str:
    return "".join(char if char in "\r\n" else " " for char in text)


def _fence_run(line: str) -> Optional[tuple[str, int, int]]:
    indent = 0
    while indent < len(line) and line[indent] == " ":
        indent += 1
    if indent > 3 or indent >= len(line) or line[indent] not in "`~":
        return None
    char = line[indent]
    end = indent
    while end < len(line) and line[end] == char:
        end += 1
    length = end - indent
    return (char, length, end) if length >= 3 else None


def _is_closing_fence(line: str, fence_char: str, fence_len: int) -> bool:
    run = _fence_run(line)
    if run is None:
        return False
    char, length, end = run
    return char == fence_char and length >= fence_len and line[end:].strip() == ""


def _strip_fenced_blocks(text: str) -> str:
    output: List[str] = []
    in_fence = False
    fence_char = ""
    fence_len = 0
    for line in text.splitlines(keepends=True):
        line_without_eol = line.rstrip("\r\n")
        if in_fence:
            output.append(_blank_code_text(line))
            if _is_closing_fence(line_without_eol, fence_char, fence_len):
                in_fence = False
            continue
        run = _fence_run(line_without_eol)
        if run is not None:
            fence_char, fence_len, _end = run
            in_fence = True
            output.append(_blank_code_text(line))
            continue
        output.append(line)
    return "".join(output)


def _strip_inline_code_line(line: str) -> str:
    chars = list(line)
    i = 0
    while i < len(line):
        if line[i] != "`":
            i += 1
            continue
        opener_start = i
        opener_end = i
        while opener_end < len(line) and line[opener_end] == "`":
            opener_end += 1
        run_len = opener_end - opener_start
        j = opener_end
        closer_end: Optional[int] = None
        while j < len(line):
            if line[j] != "`":
                j += 1
                continue
            run_start = j
            run_end = j
            while run_end < len(line) and line[run_end] == "`":
                run_end += 1
            if run_end - run_start == run_len:
                closer_end = run_end
                break
            j = run_end
        if closer_end is None:
            i = opener_end
            continue
        for index in range(opener_start, closer_end):
            chars[index] = " "
        i = closer_end
    return "".join(chars)


def strip_code_spans(text: str) -> str:
    """Blank Markdown fenced and inline code spans with a lightweight state machine."""
    without_fences = _strip_fenced_blocks(text)
    stripped_lines = []
    for line in without_fences.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        eol = line[len(content) :]
        stripped_lines.append(_strip_inline_code_line(content) + eol)
    return "".join(stripped_lines)


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
        fields.update(contract.get("optional_fields", []))
        fields.update(contract.get("legacy_fields", []))
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

    schema_version = profile.get("schema_version")
    base_version = base.get("schema_version")
    min_version = base.get("min_compatible_profile_version", base_version)
    if type(schema_version) is not int:
        issues.append(
            _profile_issue(
                "PROFILE_SCHEMA_VERSION",
                "schema_version",
                "profile schema_version 缺失或不是整数",
                f"设置为 {min_version} 到 {base_version} 之间的整数",
            )
        )
    elif schema_version < min_version:
        issues.append(
            _profile_issue(
                "PROFILE_SCHEMA_VERSION",
                "schema_version",
                f"profile schema_version {schema_version} 低于当前引擎兼容下界 {min_version}",
                "按 migration note 升级 profile 后重试",
            )
        )
    elif schema_version > base_version:
        issues.append(
            _profile_issue(
                "PROFILE_SCHEMA_VERSION",
                "schema_version",
                f"profile schema_version {schema_version} 高于当前引擎 schema_version {base_version}",
                "升级 llm-wiki 引擎后重试",
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
