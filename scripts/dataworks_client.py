#!/usr/bin/env python3
"""Thin DataWorks SDK access layer for llm-wiki freshness checks.

This module is intentionally isolated from wiki_lint/wiki_graph/wiki_eval. It
imports the official Alibaba Cloud DataWorks SDK lazily so offline tools remain
usable without SDK or network access.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, List, Optional, Sequence, Tuple

from wiki_common import LOCAL_TZ


DEFAULT_REGION = "ap-southeast-1"
DEFAULT_ENDPOINT = "dataworks.ap-southeast-1.aliyuncs.com"
FINGERPRINT_VERSION = "dw-code-v1"
FINGERPRINT_PREFIX = "sha256:"


class DataWorksClientError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class DataWorksRef:
    kind: str
    project: str
    file_id: Optional[int] = None
    table: Optional[str] = None

    @property
    def raw(self) -> str:
        if self.kind == "file":
            return f"file:{self.project}/{self.file_id}"
        return f"table:{self.project}.{self.table}"

    @property
    def table_guid(self) -> str:
        if self.kind != "table" or not self.table:
            raise DataWorksClientError("INVALID_REF", "table_guid only exists for table refs")
        return f"odps.{self.project}.{self.table}"


@dataclass(frozen=True)
class DataWorksFileCode:
    ref: DataWorksRef
    content: str
    content_path: str
    sort_path: str
    fingerprint: str


@dataclass(frozen=True)
class DataWorksTableInfo:
    ref: DataWorksRef
    last_ddl_time_ms: Optional[int]
    last_ddl_time_iso: Optional[str]
    columns: List[dict[str, Any]]


FILE_REF_RE = re.compile(r"^file:([^/]+)/(\d+)$")
TABLE_REF_RE = re.compile(r"^table:([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)$")


def obj_to_map(value: Any) -> Any:
    return value.to_map() if hasattr(value, "to_map") else value


def parse_ref(raw: str) -> DataWorksRef:
    text = str(raw or "").strip()
    m = FILE_REF_RE.match(text)
    if m:
        return DataWorksRef(kind="file", project=m.group(1), file_id=int(m.group(2)))
    m = TABLE_REF_RE.match(text)
    if m:
        return DataWorksRef(kind="table", project=m.group(1), table=m.group(2))
    raise DataWorksClientError(
        "INVALID_REF",
        "dataworks_ref must be file:<project>/<fileId> or table:<project>.<table>",
    )


def normalize_code_content(content: Any) -> str:
    if isinstance(content, bytes):
        text = content.decode("utf-8")
    else:
        text = str(content if content is not None else "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in text.split("\n")).strip()


def code_sha256(files: Sequence[Tuple[str, Any]]) -> str:
    normalized = [
        normalize_code_content(content)
        for _path, content in sorted(((str(path), content) for path, content in files), key=lambda item: item[0])
    ]
    payload = "\n".join(normalized).encode("utf-8")
    return FINGERPRINT_PREFIX + hashlib.sha256(payload).hexdigest()


def epoch_ms_to_iso(value: Any) -> Optional[str]:
    if not isinstance(value, int):
        return None
    return datetime.fromtimestamp(value / 1000, tz=LOCAL_TZ).replace(microsecond=0).isoformat()


def _sdk_modules() -> tuple[Any, Any, Any]:
    try:
        from alibabacloud_dataworks_public20200518.client import Client
        from alibabacloud_dataworks_public20200518 import models
        from alibabacloud_tea_openapi import models as open_api_models
    except ModuleNotFoundError as exc:
        raise DataWorksClientError("SDK_MISSING", f"DataWorks SDK unavailable: {exc}") from exc
    return Client, models, open_api_models


def _safe_error(exc: Exception) -> DataWorksClientError:
    message = str(exc)
    for name in ("ALIBABA_CLOUD_ACCESS_KEY_ID", "ALIBABA_CLOUD_ACCESS_KEY_SECRET"):
        value = os.environ.get(name)
        if value:
            message = message.replace(value, "<redacted>")
    return DataWorksClientError(type(exc).__name__, message[:500])


class DataWorksClient:
    def __init__(self, client: Any, models: Any) -> None:
        self._client = client
        self._models = models

    @classmethod
    def from_env(cls, *, region: str = DEFAULT_REGION) -> "DataWorksClient":
        access_key_id = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID")
        access_key_secret = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET")
        if not access_key_id or not access_key_secret:
            raise DataWorksClientError(
                "AUTH_MISSING",
                "missing ALIBABA_CLOUD_ACCESS_KEY_ID or ALIBABA_CLOUD_ACCESS_KEY_SECRET",
            )
        Client, models, open_api_models = _sdk_modules()
        config = open_api_models.Config(access_key_id=access_key_id, access_key_secret=access_key_secret)
        config.region_id = region
        config.endpoint = f"dataworks.{region}.aliyuncs.com"
        return cls(Client(config), models)

    def get_file_code(self, raw_ref: str) -> DataWorksFileCode:
        ref = parse_ref(raw_ref)
        if ref.kind != "file" or ref.file_id is None:
            raise DataWorksClientError("INVALID_REF", "get_file_code requires file:<project>/<fileId>")
        kwargs: dict[str, Any] = {"file_id": ref.file_id}
        if ref.project.isdigit():
            kwargs["project_id"] = int(ref.project)
        else:
            kwargs["project_identifier"] = ref.project
        try:
            body = obj_to_map(self._client.get_file(self._models.GetFileRequest(**kwargs)).body)
        except Exception as exc:
            raise _safe_error(exc) from exc
        file_info = ((body or {}).get("Data") or {}).get("File") or {}
        content = file_info.get("Content")
        if not isinstance(content, str):
            raise DataWorksClientError("CONTENT_MISSING", "GetFile response missing Data.File.Content")
        sort_path = str(file_info.get("FileName") or ref.raw)
        fingerprint = code_sha256([(sort_path, content)])
        return DataWorksFileCode(ref=ref, content=content, content_path="Data.File.Content", sort_path=sort_path, fingerprint=fingerprint)

    def get_table_info(self, raw_ref: str, *, page_size: int = 100) -> DataWorksTableInfo:
        ref = parse_ref(raw_ref)
        if ref.kind != "table":
            raise DataWorksClientError("INVALID_REF", "get_table_info requires table:<project>.<table>")
        try:
            basic_body = obj_to_map(
                self._client.get_meta_table_basic_info(self._models.GetMetaTableBasicInfoRequest(table_guid=ref.table_guid)).body
            )
            columns_body = obj_to_map(
                self._client.get_meta_table_column(
                    self._models.GetMetaTableColumnRequest(table_guid=ref.table_guid, page_num=1, page_size=page_size)
                ).body
            )
        except Exception as exc:
            raise _safe_error(exc) from exc
        data = (basic_body or {}).get("Data") or {}
        columns = ((columns_body or {}).get("Data") or {}).get("ColumnList") or []
        if not isinstance(columns, list):
            columns = []
        last_ddl = data.get("LastDdlTime")
        return DataWorksTableInfo(
            ref=ref,
            last_ddl_time_ms=last_ddl if isinstance(last_ddl, int) else None,
            last_ddl_time_iso=epoch_ms_to_iso(last_ddl),
            columns=[item for item in columns if isinstance(item, dict)],
        )

    def get_file_fingerprint(self, raw_ref: str) -> str:
        return self.get_file_code(raw_ref).fingerprint
