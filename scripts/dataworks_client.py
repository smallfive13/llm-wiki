#!/usr/bin/env python3
"""Thin DataWorks SDK access layer for llm-wiki freshness checks.

This module is intentionally isolated from wiki_lint/wiki_graph/wiki_eval. It
imports the official Alibaba Cloud DataWorks SDK lazily so offline tools remain
usable without SDK or network access.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from hashlib import sha256
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

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


@dataclass(frozen=True)
class DataWorksNode:
    node_id: int
    node_name: str
    project_id: int
    file_id: Optional[int]
    file_name: Optional[str]
    file_path: Optional[str]
    file_version: Optional[int]
    program_type: Optional[str]
    scheduler_type: Optional[str]
    repeatability: bool
    inputs: List[str]
    outputs: List[str]
    tables: List[str]
    fingerprint: Optional[str]
    last_synced: Optional[str]
    paused: bool = False


@dataclass(frozen=True)
class DataWorksDeploymentItem:
    deployment_id: int
    file_id: int
    file_version: Optional[int]
    execute_time_ms: Optional[int]
    execute_time_iso: Optional[str]
    to_environment: Optional[int]


@dataclass(frozen=True)
class DataWorksFileVersion:
    file_version: Optional[int]
    commit_time_ms: Optional[int]
    commit_time_iso: Optional[str]
    commit_user: Optional[str]
    change_type: Optional[str]
    status: Optional[str]
    use_type: Optional[str]
    file_name: Optional[str]
    comment: Optional[str]


@dataclass(frozen=True)
class DataWorksSourceBinding:
    source_binding: str
    source_datasource: Optional[str]
    source_tables: List[str]
    binding_warnings: List[str]


@dataclass(frozen=True)
class DataWorksDatasourceResolution:
    datasource_name: str
    db_type: Optional[str]
    database_name: Optional[str]
    resolution: str
    source_hash: Optional[str] = None
    updated_at: Optional[str] = None


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


def _string_list(value: Any) -> List[str]:
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    if isinstance(value, list):
        result: List[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                result.append(item.strip())
        return result
    return []


def _dedupe(values: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    result: List[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def source_binding_to_index_fields(binding: DataWorksSourceBinding) -> Dict[str, Any]:
    fields: Dict[str, Any] = {"source_binding": binding.source_binding}
    if binding.source_datasource:
        fields["source_datasource"] = binding.source_datasource
    if binding.source_tables:
        fields["source_tables"] = binding.source_tables
    if binding.binding_warnings:
        fields["binding_warnings"] = binding.binding_warnings
    return fields


def source_binding_from_index_item(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        key: item.get(key)
        for key in ("source_binding", "source_datasource", "source_tables", "binding_warnings")
        if key in item
    }


FORBIDDEN_DATASOURCE_OUTPUT_RE = re.compile(
    r"(?i)(jdbc:|://|\\bhost\\b|\\baddress\\b|\\bendpoint\\b|\\bport\\b|\\busername\\b|\\bpassword\\b|accesskey|secret|token)"
)


def sanitize_datasource_map_payload(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def assert_no_datasource_secrets(payload: Any) -> None:
    text = sanitize_datasource_map_payload(payload)
    match = FORBIDDEN_DATASOURCE_OUTPUT_RE.search(text)
    if match:
        raise DataWorksClientError("DATASOURCE_SECRET_LEAK", f"sanitized datasource output contains forbidden token: {match.group(0)}")


def datasource_resolution_to_map(resolution: DataWorksDatasourceResolution) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "datasource_name": resolution.datasource_name,
        "resolution": resolution.resolution,
    }
    if resolution.db_type:
        result["db_type"] = resolution.db_type
    if resolution.database_name:
        result["database_name"] = resolution.database_name
    if resolution.source_hash:
        result["source_hash"] = resolution.source_hash
    if resolution.updated_at:
        result["updated_at"] = resolution.updated_at
    assert_no_datasource_secrets(result)
    return result


def _parse_database_from_jdbc_url(jdbc_url: Any) -> Optional[str]:
    if not isinstance(jdbc_url, str) or not jdbc_url.strip():
        return None
    text = jdbc_url.strip()
    match = re.search(r"(?i)(?:[;?&])databaseName=([^;?&]+)", text)
    if match:
        return match.group(1).strip() or None
    match = re.match(r"(?i)^jdbc:[a-z0-9]+://[^/]+/([^?;]+)", text)
    if match:
        return match.group(1).strip() or None
    return None


def parse_datasource_resolution(item: Dict[str, Any]) -> DataWorksDatasourceResolution:
    name = str(item.get("Name") or "").strip()
    db_type = str(item.get("DataSourceType") or "").strip().lower() or None
    content_text = item.get("Content")
    content: Dict[str, Any] = {}
    if isinstance(content_text, str) and content_text.strip():
        try:
            parsed = json.loads(content_text)
            if isinstance(parsed, dict):
                content = parsed
        except Exception:
            content = {}
    source_hash = sha256(str(content_text or "").encode("utf-8")).hexdigest() if content_text is not None else None
    database_name: Optional[str] = None
    resolution = "failed"
    if isinstance(content.get("database"), str) and content["database"].strip():
        database_name = content["database"].strip()
        resolution = "parsed"
    elif db_type == "mongodb" and isinstance(content.get("authDb"), str) and content["authDb"].strip():
        database_name = content["authDb"].strip()
        resolution = "parsed"
    else:
        database_name = _parse_database_from_jdbc_url(content.get("jdbcUrl"))
        if database_name:
            resolution = "parsed"
    result = DataWorksDatasourceResolution(
        datasource_name=name,
        db_type=db_type,
        database_name=database_name,
        resolution=resolution,
        source_hash=source_hash,
        updated_at=str(item.get("GmtModified") or "").strip() or None,
    )
    datasource_resolution_to_map(result)
    return result


def parse_di_source_binding(content: Any, *, program_type: Optional[str] = "DI") -> DataWorksSourceBinding:
    if program_type and str(program_type).upper() != "DI":
        return DataWorksSourceBinding("inferred", None, [], [])
    try:
        data = json.loads(normalize_code_content(content))
    except Exception:
        return DataWorksSourceBinding("unparsed", None, [], ["content is not valid DI JSON"])
    if not isinstance(data, dict):
        return DataWorksSourceBinding("unparsed", None, [], ["DI JSON top-level is not object"])
    steps = data.get("steps")
    if not isinstance(steps, list):
        return DataWorksSourceBinding("unparsed", None, [], ["DI JSON missing steps list"])

    readers = [step for step in steps if isinstance(step, dict) and step.get("category") == "reader"]
    if not readers:
        return DataWorksSourceBinding("ambiguous", None, [], ["DI JSON has no reader step"])
    if len(readers) > 1:
        return DataWorksSourceBinding("ambiguous", None, [], ["DI JSON has multiple reader steps"])

    reader = readers[0]
    parameter = reader.get("parameter")
    if not isinstance(parameter, dict):
        return DataWorksSourceBinding("ambiguous", None, [], ["reader parameter is not object"])
    step_type = str(reader.get("stepType") or "").lower()
    warnings: List[str] = []
    datasource: Optional[str] = None
    tables: List[str] = []

    if step_type in {"mysql", "sqlserver"}:
        connections = parameter.get("connection")
        if not isinstance(connections, list) or not connections:
            return DataWorksSourceBinding("ambiguous", None, [], [f"{step_type} reader missing connection list"])
        datasources: List[str] = []
        for idx, connection in enumerate(connections):
            if not isinstance(connection, dict):
                warnings.append(f"connection[{idx}] is not object")
                continue
            ds = connection.get("datasource")
            if isinstance(ds, str) and ds.strip():
                datasources.append(ds.strip())
            else:
                warnings.append(f"connection[{idx}] missing datasource")
            connection_tables = _string_list(connection.get("table"))
            if connection_tables:
                tables.extend(connection_tables)
            else:
                warnings.append(f"connection[{idx}] missing table list")
        datasources = _dedupe(datasources)
        tables = _dedupe(tables)
        if len(datasources) == 1:
            datasource = datasources[0]
        elif len(datasources) > 1:
            warnings.append("multiple datasource values in reader connection list")
        if datasource and tables and not warnings:
            return DataWorksSourceBinding("parsed", datasource, tables, [])
        return DataWorksSourceBinding("ambiguous", datasource, tables, warnings or ["mysql/sqlserver reader binding incomplete"])

    if step_type == "mongodb":
        ds = parameter.get("datasource")
        if isinstance(ds, str) and ds.strip():
            datasource = ds.strip()
        else:
            warnings.append("mongodb reader missing datasource")
        tables = _dedupe(_string_list(parameter.get("collectionName")))
        if not tables:
            warnings.append("mongodb reader missing collectionName")
        if datasource and tables and not warnings:
            return DataWorksSourceBinding("parsed", datasource, tables, [])
        return DataWorksSourceBinding("ambiguous", datasource, tables, warnings or ["mongodb reader binding incomplete"])

    return DataWorksSourceBinding("ambiguous", None, [], [f"unsupported reader stepType: {step_type or '<empty>'}"])


def epoch_ms_to_iso(value: Any) -> Optional[str]:
    if not isinstance(value, int):
        return None
    return datetime.fromtimestamp(value / 1000, tz=LOCAL_TZ).replace(microsecond=0).isoformat()


def _int_or_none(value: Any) -> Optional[int]:
    return value if isinstance(value, int) else None


def _string_or_none(value: Any) -> Optional[str]:
    return value if isinstance(value, str) and value else None


def _table_names_from_outputs(outputs: List[str]) -> List[str]:
    tables: List[str] = []
    seen = set()
    for item in outputs:
        text = str(item or "").strip()
        if not text or "." not in text:
            continue
        if text in seen:
            continue
        seen.add(text)
        tables.append(text)
    return tables


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

    def list_file_versions(self, raw_ref: str, *, page_size: int = 10, max_pages: Optional[int] = 1) -> List[DataWorksFileVersion]:
        """List committed versions of a design file, newest first.

        GetFile returns the latest saved draft, which may be newer than every
        committed version; per-file deployment questions should be answered
        here (newest DEPLOYED version), not by scanning deployment records.
        """
        ref = parse_ref(raw_ref)
        if ref.kind != "file" or ref.file_id is None:
            raise DataWorksClientError("INVALID_REF", "list_file_versions requires file:<project>/<fileId>")
        kwargs: dict[str, Any] = {"file_id": ref.file_id}
        if ref.project.isdigit():
            kwargs["project_id"] = int(ref.project)
        else:
            kwargs["project_identifier"] = ref.project
        result: List[DataWorksFileVersion] = []
        page_number = 1
        while True:
            try:
                body = obj_to_map(
                    self._client.list_file_versions(
                        self._models.ListFileVersionsRequest(page_number=page_number, page_size=page_size, **kwargs)
                    ).body
                )
            except Exception as exc:
                raise _safe_error(exc) from exc
            data = (body or {}).get("Data") or {}
            versions = data.get("FileVersions") or []
            if not isinstance(versions, list) or not versions:
                break
            for item in versions:
                if not isinstance(item, dict):
                    continue
                commit_ms = _int_or_none(item.get("CommitTime"))
                result.append(
                    DataWorksFileVersion(
                        file_version=_int_or_none(item.get("FileVersion")),
                        commit_time_ms=commit_ms,
                        commit_time_iso=epoch_ms_to_iso(commit_ms),
                        commit_user=_string_or_none(item.get("CommitUser")),
                        change_type=_string_or_none(item.get("ChangeType")),
                        status=_string_or_none(item.get("Status")),
                        use_type=_string_or_none(item.get("UseType")),
                        file_name=_string_or_none(item.get("FileName")),
                        comment=_string_or_none(item.get("Comment")),
                    )
                )
            total = data.get("TotalCount")
            if max_pages is not None and page_number >= max_pages:
                break
            if not isinstance(total, int) or page_number * page_size >= total:
                break
            page_number += 1
        result.sort(key=lambda version: version.file_version or 0, reverse=True)
        return result

    def get_latest_deployed_version(self, raw_ref: str, *, page_size: int = 10, max_pages: Optional[int] = 5) -> Optional[DataWorksFileVersion]:
        for version in self.list_file_versions(raw_ref, page_size=page_size, max_pages=max_pages):
            if (version.status or "").upper() == "DEPLOYED":
                return version
        return None

    def get_file_version_code(self, raw_ref: str, file_version: int) -> DataWorksFileCode:
        """Fetch the content of one committed file version via GetFileVersion.

        GetFile returns the latest saved draft which may be newer than every
        DEPLOYED version; to answer "what runs in prod", locate the version via
        get_latest_deployed_version() first, then fetch that exact version here.
        Committed versions are immutable.
        """
        ref = parse_ref(raw_ref)
        if ref.kind != "file" or ref.file_id is None:
            raise DataWorksClientError("INVALID_REF", "get_file_version_code requires file:<project>/<fileId>")
        if not isinstance(file_version, int) or file_version <= 0:
            raise DataWorksClientError("INVALID_VERSION", "file_version must be a positive integer")
        kwargs: dict[str, Any] = {"file_id": ref.file_id, "file_version": file_version}
        if ref.project.isdigit():
            kwargs["project_id"] = int(ref.project)
        else:
            kwargs["project_identifier"] = ref.project
        try:
            body = obj_to_map(self._client.get_file_version(self._models.GetFileVersionRequest(**kwargs)).body)
        except Exception as exc:
            raise _safe_error(exc) from exc
        data = (body or {}).get("Data") or {}
        content = data.get("FileContent")
        if not isinstance(content, str):
            raise DataWorksClientError("CONTENT_MISSING", "GetFileVersion response missing Data.FileContent")
        sort_path = str(data.get("FileName") or ref.raw)
        fingerprint = code_sha256([(sort_path, content)])
        return DataWorksFileCode(
            ref=ref,
            content=content,
            content_path="Data.FileContent",
            sort_path=sort_path,
            fingerprint=fingerprint,
        )

    def list_successful_prod_deployment_items(
        self,
        project_id: int,
        *,
        end_execute_time_ms: Optional[int] = None,
        page_size: int = 100,
        max_pages: Optional[int] = None,
    ) -> List[DataWorksDeploymentItem]:
        result: List[DataWorksDeploymentItem] = []
        seen: set[tuple[int, int, Optional[int]]] = set()
        page_number = 1
        while True:
            kwargs: dict[str, Any] = {
                "project_id": project_id,
                "page_number": page_number,
                "page_size": page_size,
                "status": 1,
            }
            if end_execute_time_ms is not None:
                kwargs["end_execute_time"] = end_execute_time_ms
            try:
                body = obj_to_map(self._client.list_deployments(self._models.ListDeploymentsRequest(**kwargs)).body)
            except Exception as exc:
                raise _safe_error(exc) from exc
            data = (body or {}).get("Data") or {}
            deployments = data.get("Deployments") or []
            if not isinstance(deployments, list) or not deployments:
                break
            for deployment in deployments:
                if not isinstance(deployment, dict):
                    continue
                deployment_id = _int_or_none(deployment.get("Id"))
                if deployment_id is None:
                    continue
                result.extend(self.get_successful_prod_deployment_items(project_id, deployment_id))
            total = data.get("TotalCount")
            if max_pages is not None and page_number >= max_pages:
                break
            if not isinstance(total, int) or page_number * page_size >= total:
                break
            page_number += 1
        deduped: List[DataWorksDeploymentItem] = []
        for item in result:
            key = (item.deployment_id, item.file_id, item.file_version)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        deduped.sort(key=lambda item: (item.execute_time_ms or 0, item.deployment_id, item.file_id, item.file_version or 0), reverse=True)
        return deduped

    def get_successful_prod_deployment_items(self, project_id: int, deployment_id: int) -> List[DataWorksDeploymentItem]:
        try:
            body = obj_to_map(
                self._client.get_deployment(
                    self._models.GetDeploymentRequest(project_id=project_id, deployment_id=deployment_id)
                ).body
            )
        except Exception as exc:
            raise _safe_error(exc) from exc
        data = (body or {}).get("Data") or {}
        deployment = data.get("Deployment") or {}
        if not isinstance(deployment, dict):
            deployment = {}
        if deployment.get("Status") != 1 or deployment.get("ToEnvironment") != 2:
            return []
        execute_ms = _int_or_none(deployment.get("ExecuteTime"))
        items = data.get("DeployedItems") or []
        result: List[DataWorksDeploymentItem] = []
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                file_id = _int_or_none(item.get("FileId"))
                if file_id is None:
                    continue
                result.append(
                    DataWorksDeploymentItem(
                        deployment_id=deployment_id,
                        file_id=file_id,
                        file_version=_int_or_none(item.get("FileVersion")),
                        execute_time_ms=execute_ms,
                        execute_time_iso=epoch_ms_to_iso(execute_ms),
                        to_environment=_int_or_none(deployment.get("ToEnvironment")),
                    )
                )
        return result

    def list_nodes_prod_raw(self, project_id: int, *, page_size: int = 100, max_pages: Optional[int] = None) -> List[dict[str, Any]]:
        nodes: List[dict[str, Any]] = []
        page_number = 1
        while True:
            try:
                body = obj_to_map(
                    self._client.list_nodes(
                        self._models.ListNodesRequest(
                            project_id=project_id,
                            project_env="PROD",
                            page_size=page_size,
                            page_number=page_number,
                        )
                    ).body
                )
            except Exception as exc:
                raise _safe_error(exc) from exc
            data = (body or {}).get("Data") or {}
            page_nodes = data.get("Nodes") or []
            if not isinstance(page_nodes, list) or not page_nodes:
                break
            nodes.extend(item for item in page_nodes if isinstance(item, dict))
            total = data.get("TotalCount")
            if max_pages is not None and page_number >= max_pages:
                break
            if not isinstance(total, int) or len(nodes) >= total:
                break
            page_number += 1
        return nodes

    def get_node_prod(self, node_id: int) -> dict[str, Any]:
        try:
            body = obj_to_map(self._client.get_node(self._models.GetNodeRequest(node_id=node_id, project_env="PROD")).body)
        except Exception as exc:
            raise _safe_error(exc) from exc
        data = (body or {}).get("Data") or {}
        return data if isinstance(data, dict) else {}

    def list_node_io_items(self, node_id: int, io_type: str) -> List[str]:
        try:
            body = obj_to_map(
                self._client.list_node_io(
                    self._models.ListNodeIORequest(node_id=node_id, project_env="PROD", io_type=io_type)
                ).body
            )
        except Exception as exc:
            raise _safe_error(exc) from exc
        data = (body or {}).get("Data") or []
        values: List[str] = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    value = item.get("Data") or item.get("TableName")
                    if isinstance(value, str) and value.strip():
                        values.append(value.strip())
        return values

    def list_node_outputs(self, node_id: int) -> List[str]:
        return self.list_node_io_items(node_id, "output")

    def list_node_inputs(self, node_id: int) -> List[str]:
        return self.list_node_io_items(node_id, "input")

    def find_design_file_for_node(self, project_id: int, node_id: int) -> Optional[dict[str, Any]]:
        try:
            body = obj_to_map(
                self._client.list_files(
                    self._models.ListFilesRequest(
                        project_id=project_id,
                        node_id=node_id,
                        page_size=1,
                        page_number=1,
                        need_content=False,
                        need_absolute_folder_path=True,
                    )
                ).body
            )
        except Exception as exc:
            raise _safe_error(exc) from exc
        files = ((body or {}).get("Data") or {}).get("Files") or []
        if isinstance(files, list) and files and isinstance(files[0], dict):
            return files[0]
        return None

    def get_design_file_code(self, project_id: int, file_id: int) -> DataWorksFileCode:
        return self.get_file_code(f"file:{project_id}/{file_id}")

    def list_datasource_resolutions(self, project_id: int, *, page_size: int = 100) -> List[DataWorksDatasourceResolution]:
        result: List[DataWorksDatasourceResolution] = []
        page_number = 1
        while True:
            try:
                body = obj_to_map(
                    self._client.list_data_sources(
                        self._models.ListDataSourcesRequest(
                            project_id=project_id,
                            env_type=1,
                            page_number=page_number,
                            page_size=page_size,
                        )
                    ).body
                )
            except Exception as exc:
                raise _safe_error(exc) from exc
            data = (body or {}).get("Data") or {}
            page_items = data.get("DataSources") or []
            if not isinstance(page_items, list) or not page_items:
                break
            for item in page_items:
                if isinstance(item, dict):
                    result.append(parse_datasource_resolution(item))
            total = data.get("TotalCount")
            if not isinstance(total, int) or len(result) >= total:
                break
            page_number += 1
        result.sort(key=lambda item: item.datasource_name)
        assert_no_datasource_secrets([datasource_resolution_to_map(item) for item in result])
        return result

    def list_prod_nodes(self, project_id: int, *, page_size: int = 100, max_pages: Optional[int] = None) -> List[DataWorksNode]:
        result: List[DataWorksNode] = []
        for item in self.list_nodes_prod_raw(project_id, page_size=page_size, max_pages=max_pages):
            scheduler_type = item.get("SchedulerType")
            repeatability = item.get("Repeatability") is True
            if scheduler_type != "NORMAL" or not repeatability:
                continue
            node_id = item.get("NodeId")
            if not isinstance(node_id, int):
                continue
            node = self.get_node_prod(node_id)
            design_file = self.find_design_file_for_node(project_id, node_id)
            design_file_id = _int_or_none((design_file or {}).get("FileId"))
            file_name = _string_or_none((design_file or {}).get("FileName")) or _string_or_none(node.get("NodeName"))
            folder = _string_or_none((design_file or {}).get("AbsoluteFolderPath"))
            file_path = "/".join(part for part in [folder, file_name] if part)
            inputs = self.list_node_inputs(node_id)
            outputs = self.list_node_outputs(node_id)
            fingerprint: Optional[str] = None
            if design_file_id is not None:
                fingerprint = self.get_design_file_code(project_id, design_file_id).fingerprint
            result.append(
                DataWorksNode(
                    node_id=node_id,
                    node_name=str(node.get("NodeName") or item.get("NodeName") or node_id),
                    project_id=project_id,
                    file_id=design_file_id,
                    file_name=file_name,
                    file_path=file_path or None,
                    file_version=_int_or_none(node.get("FileVersion")),
                    program_type=_string_or_none(node.get("ProgramType")),
                    scheduler_type=_string_or_none(node.get("SchedulerType")) or _string_or_none(scheduler_type),
                    repeatability=repeatability,
                    inputs=_table_names_from_outputs(inputs),
                    outputs=outputs,
                    tables=_table_names_from_outputs(outputs),
                    fingerprint=fingerprint,
                    last_synced=epoch_ms_to_iso(node.get("ModifyTime")) or epoch_ms_to_iso(item.get("ModifyTime")),
                )
            )
        result.sort(key=lambda node: (node.node_name, node.node_id))
        return result


DEFAULT_EVIDENCE_CONTEXT = 5
DEFAULT_EVIDENCE_MAX_LINES = 200


def default_version_cache_dir() -> Path:
    """Engine-side cache for immutable committed-version contents.

    The engine .gitignore is allowlist-style ("*" first), so this directory is
    never tracked by git nor scanned by gitignore-aware search tools. Code
    bodies must not be cached inside any wiki instance.
    """
    return Path(__file__).resolve().parent.parent / ".cache" / "dataworks" / "file_versions"


def version_cache_path(cache_dir: Path, ref: DataWorksRef, file_version: int) -> Path:
    return Path(cache_dir) / f"{ref.project}-{ref.file_id}-v{int(file_version)}.code"


def load_cached_version_code(cache_dir: Path, ref: DataWorksRef, file_version: int) -> Optional[str]:
    path = version_cache_path(cache_dir, ref, file_version)
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return None


def store_cached_version_code(cache_dir: Path, ref: DataWorksRef, file_version: int, content: str) -> Path:
    path = version_cache_path(cache_dir, ref, file_version)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)
    return path


def scan_code_evidence(
    content: Any,
    patterns: Sequence[str],
    *,
    context: int = DEFAULT_EVIDENCE_CONTEXT,
    ignore_case: bool = True,
    max_total_lines: int = DEFAULT_EVIDENCE_MAX_LINES,
) -> Dict[str, Any]:
    """Scan code in-process and return only matched snippets.

    The total number of emitted snippet lines is hard-capped so a pathological
    pattern (e.g. ``.*``) cannot degenerate this mode into a full code dump.
    """
    lines = str(content or "").split("\n")
    flags = re.IGNORECASE if ignore_case else 0
    context = max(0, int(context))
    budget = max(1, int(max_total_lines))
    emitted = 0
    truncated = False
    results: List[Dict[str, Any]] = []
    for raw_pattern in patterns:
        try:
            compiled = re.compile(str(raw_pattern), flags)
        except re.error as exc:
            raise DataWorksClientError("INVALID_PATTERN", f"invalid regex {raw_pattern!r}: {exc}") from exc
        hit_lines = [idx for idx, line in enumerate(lines) if compiled.search(line)]
        ranges: List[Tuple[int, int]] = []
        for idx in hit_lines:
            start = max(0, idx - context)
            end = min(len(lines) - 1, idx + context)
            if ranges and start <= ranges[-1][1] + 1:
                ranges[-1] = (ranges[-1][0], max(ranges[-1][1], end))
            else:
                ranges.append((start, end))
        snippets: List[Dict[str, Any]] = []
        for start, end in ranges:
            if emitted >= budget:
                truncated = True
                break
            take = min(end - start + 1, budget - emitted)
            if take < end - start + 1:
                truncated = True
            snippet_lines = lines[start : start + take]
            emitted += len(snippet_lines)
            snippets.append({"line_start": start + 1, "line_end": start + take, "lines": snippet_lines})
        results.append(
            {
                "pattern": str(raw_pattern),
                "matched": bool(hit_lines),
                "match_count": len(hit_lines),
                "snippets": snippets,
            }
        )
    return {
        "patterns": results,
        "total_snippet_lines": emitted,
        "total_code_lines": len(lines),
        "truncated": truncated,
    }


def render_evidence(report: Dict[str, Any]) -> str:
    lines = [
        "dataworks-client evidence",
        "=========================",
        f"ref: {report['ref']}",
        f"file_version: {report['file_version']} (DEPLOYED)",
        f"commit_time: {report.get('commit_time')}",
        f"fingerprint: {report.get('fingerprint')}",
        f"cache: {report.get('cache')}",
        f"code_lines: {report.get('total_code_lines')} · snippet_lines: {report.get('total_snippet_lines')}"
        + (" · TRUNCATED（收紧 pattern 或调 --max-lines）" if report.get("truncated") else ""),
    ]
    for entry in report.get("patterns", []):
        lines.extend(["", f"Pattern: {entry['pattern']}", f"matched: {entry['matched']} · match_count: {entry['match_count']}"])
        for snippet in entry.get("snippets", []):
            lines.append(f"--- L{snippet['line_start']}-L{snippet['line_end']} ---")
            lines.extend(snippet["lines"])
        if entry["matched"] and not entry.get("snippets"):
            lines.append("(snippets omitted: line budget exhausted)")
    return "\n".join(lines) + "\n"


def run_evidence(args: argparse.Namespace, *, client_factory: Optional[Any] = None) -> int:
    try:
        ref = parse_ref(args.ref)
        if ref.kind != "file":
            raise DataWorksClientError("INVALID_REF", "evidence requires file:<project>/<fileId>")
        cache_dir = Path(args.cache_dir) if args.cache_dir else default_version_cache_dir()
        client = client_factory() if client_factory else DataWorksClient.from_env()
        version = client.get_latest_deployed_version(args.ref)
        if version is None or version.file_version is None:
            print(f"dataworks-client warning: NO_DEPLOYED_VERSION: {args.ref} 未发现 DEPLOYED 版本（已扫描页内）")
            return 1
        content = load_cached_version_code(cache_dir, ref, version.file_version)
        cache_state = "hit"
        if content is None:
            cache_state = "miss"
            content = client.get_file_version_code(args.ref, version.file_version).content
            store_cached_version_code(cache_dir, ref, version.file_version, content)
        fingerprint = code_sha256([(str(version.file_name or ref.raw), content)])
        evidence = scan_code_evidence(
            content,
            args.pattern,
            context=args.context,
            ignore_case=not args.case_sensitive,
            max_total_lines=args.max_lines,
        )
    except DataWorksClientError as exc:
        print(f"dataworks-client warning: {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    report = {
        "ref": args.ref,
        "file_id": ref.file_id,
        "file_version": version.file_version,
        "commit_time": version.commit_time_iso,
        "fingerprint": fingerprint,
        "cache": cache_state,
        **evidence,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_evidence(report), end="")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DataWorks access CLI（evidence：按最新 DEPLOYED 版本取码，只输出证据片段）")
    sub = parser.add_subparsers(dest="command")
    evidence = sub.add_parser("evidence", help="scan latest DEPLOYED version, print matched snippets only")
    evidence.add_argument("--ref", required=True, help="file:<project>/<fileId>")
    evidence.add_argument("--pattern", action="append", required=True, help="regex to match; repeatable")
    evidence.add_argument("--context", type=int, default=DEFAULT_EVIDENCE_CONTEXT, help="context lines around each hit; default 5")
    evidence.add_argument("--max-lines", type=int, default=DEFAULT_EVIDENCE_MAX_LINES, help="hard cap on total snippet lines; default 200")
    evidence.add_argument("--case-sensitive", action="store_true", help="patterns are case-insensitive by default (SQL)")
    evidence.add_argument("--cache-dir", help="override version cache dir; default <engine>/.cache/dataworks/file_versions")
    evidence.add_argument("--json", action="store_true", help="output JSON")
    return parser


def main(argv: Optional[List[str]] = None, *, client_factory: Optional[Any] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "evidence":
        return run_evidence(args, client_factory=client_factory)
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
