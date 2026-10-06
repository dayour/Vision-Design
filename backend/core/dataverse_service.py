import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

import msal
import requests
from azure.core.exceptions import ClientAuthenticationError
from azure.identity import DefaultAzureCredential

from backend.core.config import settings
from backend.core.pac_cli import PacCliToken, try_acquire_pac_cli_token

logger = logging.getLogger(__name__)


class DataverseError(Exception):
    """Base exception for Dataverse errors."""


class DataverseAuthenticationError(DataverseError):
    """Raised when Dataverse authentication fails."""


class DataverseRecordNotFoundError(DataverseError):
    """Raised when a Dataverse record is not found."""


class DataverseQuotaExceededError(DataverseError):
    """Raised when Dataverse returns a capacity or rate limitation error."""


class DataverseService:
    """Service layer for Microsoft Dataverse interactions."""

    _ASSET_FIELD_MAP: Dict[str, str] = {
        "media_type": "dystudio_media_type",
        "blob_name": "dystudio_blob_name",
        "container": "dystudio_container",
        "url": "dystudio_url",
        "filename": "dystudio_filename",
        "size": "dystudio_size",
        "content_type": "dystudio_content_type",
        "folder_path": "dystudio_folder_path",
        "prompt": "dystudio_prompt",
        "model": "dystudio_model",
        "generation_id": "dystudio_generation_id",
        "summary": "dystudio_summary",
        "description": "dystudio_description",
        "products": "dystudio_products",
        "tags": "dystudio_tags",
        "feedback": "dystudio_feedback",
        "quality": "dystudio_quality",
        "background": "dystudio_background",
        "output_format": "dystudio_output_format",
        "has_transparency": "dystudio_has_transparency",
        "duration": "dystudio_duration",
        "fps": "dystudio_fps",
        "resolution": "dystudio_resolution",
        "analysis": "dystudio_analysis_data",
        "custom_metadata": "dystudio_custom_metadata",
        "width": "dystudio_width",
        "height": "dystudio_height",
        "has_analysis": "dystudio_has_analysis",
        "image_data": "dystudio_image_data",
        "created_at": "createdon",
        "updated_at": "modifiedon",
    }

    _ASSET_SELECT_FIELDS: Tuple[str, ...] = (
        "dystudio_visionassetsid",
        "dystudio_media_type",
        "dystudio_blob_name",
        "dystudio_container",
        "dystudio_url",
        "dystudio_filename",
        "dystudio_size",
        "dystudio_content_type",
        "dystudio_folder_path",
        "dystudio_prompt",
        "dystudio_model",
        "dystudio_generation_id",
        "dystudio_summary",
        "dystudio_description",
        "dystudio_products",
        "dystudio_tags",
        "dystudio_feedback",
        "dystudio_quality",
        "dystudio_background",
        "dystudio_output_format",
        "dystudio_has_transparency",
        "dystudio_duration",
        "dystudio_fps",
        "dystudio_resolution",
        "dystudio_analysis_data",
        "dystudio_custom_metadata",
        "dystudio_width",
        "dystudio_height",
    "dystudio_has_analysis",
    "dystudio_image_data",
        "createdon",
        "modifiedon",
    )

    def __init__(self, session: Optional[requests.Session] = None) -> None:
        if not settings.DATAVERSE_ENVIRONMENT_URL:
            raise DataverseError("Dataverse environment URL is not configured")

        self._environment_url = settings.DATAVERSE_ENVIRONMENT_URL.rstrip("/")
        api_version = settings.DATAVERSE_API_VERSION or "9.2"
        self._api_base = f"{self._environment_url}/api/data/v{api_version}"
        self._assets_table = settings.DATAVERSE_TABLE_VISIONASSETS or "dystudio_visionassets"
        self._tags_table = settings.DATAVERSE_TABLE_ASSETTAGS or "dystudio_assettags"
        self._generation_table = settings.DATAVERSE_TABLE_GENERATIONHISTORY or "dystudio_generationhistories"
        self._relationship_asset_tags = "dystudio_dystudio_assettag_dystudio_visionasset"

        self._use_managed_identity = settings.DATAVERSE_USE_MANAGED_IDENTITY
        self._client_id = settings.DATAVERSE_CLIENT_ID
        self._client_secret = settings.DATAVERSE_CLIENT_SECRET
        self._tenant_id = settings.AZURE_TENANT_ID
        self._use_pac_auth = settings.DATAVERSE_USE_PAC_AUTH
        self._pac_profile_hint = settings.DATAVERSE_PAC_PROFILE

        self._session = session or requests.Session()
        self._token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        self._token_lock = Lock()
        self._msal_app: Optional[msal.ConfidentialClientApplication] = None
        self._last_response_headers: Dict[str, str] = {}

        if not self._use_managed_identity and self._client_id and self._client_secret:
            if not self._tenant_id:
                raise DataverseAuthenticationError(
                    "AZURE_TENANT_ID must be set when using client credentials"
                )
            authority = f"https://login.microsoftonline.com/{self._tenant_id}"
            self._msal_app = msal.ConfidentialClientApplication(
                client_id=self._client_id,
                client_credential=self._client_secret,
                authority=authority,
            )

    # ------------------------------------------------------------------
    # Authentication helpers
    # ------------------------------------------------------------------
    def _authenticate(self) -> str:
        with self._token_lock:
            if self._token and self._token_expiry and datetime.now(timezone.utc) < self._token_expiry:
                return self._token

            scope = f"{self._environment_url}/.default"

            try:
                if self._use_managed_identity:
                    pac_token = self._try_pac_cli_auth()
                    if pac_token:
                        self._token = pac_token.access_token
                        self._token_expiry = pac_token.expires_on
                        return self._token

                    credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
                    token = credential.get_token(scope)
                    self._token = token.token
                    self._token_expiry = datetime.fromtimestamp(token.expires_on, tz=timezone.utc)
                    return self._token

                if self._msal_app:
                    result = self._msal_app.acquire_token_silent([scope], account=None)
                    if not result:
                        result = self._msal_app.acquire_token_for_client(scopes=[scope])
                    if "access_token" not in result:
                        raise DataverseAuthenticationError(result.get("error_description", "Failed to acquire token"))
                    self._token = result["access_token"]
                    expires_in = int(result.get("expires_in", 3600))
                    self._token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in - 60)
                    return self._token

                raise DataverseAuthenticationError("No valid authentication mechanism configured for Dataverse")

            except ClientAuthenticationError as exc:
                raise DataverseAuthenticationError(str(exc)) from exc
            except Exception as exc:  # pragma: no cover - safeguard
                raise DataverseAuthenticationError(str(exc)) from exc

    def _try_pac_cli_auth(self) -> Optional[PacCliToken]:
        if not self._use_pac_auth:
            return None
        return try_acquire_pac_cli_token(
            environment_url=self._environment_url,
            profile_hint=self._pac_profile_hint,
        )

    def _get_headers(self, include_annotations: bool = True, custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        token = self._authenticate()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
        }
        if include_annotations:
            headers["Prefer"] = "odata.include-annotations=\"*\""
        if custom_headers:
            headers.update(custom_headers)
        return headers

    # ------------------------------------------------------------------
    # Generic request helper
    # ------------------------------------------------------------------
    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        expected_status: Tuple[int, ...] = (200, 201, 204),
        include_annotations: bool = True,
    ) -> Optional[Dict[str, Any]]:
        url = f"{self._api_base}/{path.lstrip('/')}"
        response = self._session.request(
            method=method.upper(),
            url=url,
            params=params,
            headers=self._get_headers(include_annotations=include_annotations, custom_headers=headers),
            json=json_body,
            timeout=30,
        )
        self._last_response_headers = dict(response.headers)

        if response.status_code not in expected_status:
            try:
                error_payload = response.json()
            except ValueError:
                error_payload = {"error": {"message": response.text}}

            message = error_payload.get("error", {}).get("message", response.text)
            # Include status code and full response if message is empty
            if not message or message.strip() == "":
                message = f"HTTP {response.status_code}: {response.text[:500]}"
            
            if response.status_code == 404:
                raise DataverseRecordNotFoundError(message)
            if response.status_code == 429 or response.status_code == 503:
                raise DataverseQuotaExceededError(message)
            if response.status_code == 401:
                raise DataverseAuthenticationError(message)

            raise DataverseError(message)

        if response.status_code == 204:
            return None

        if not response.content:
            return None

        try:
            return response.json()
        except ValueError:
            return {"raw": response.text}

    def _request_binary(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None,
        expected_status: Tuple[int, ...] = (200,),
    ) -> Tuple[bytes, Dict[str, str]]:
        url = f"{self._api_base}/{path.lstrip('/')}"
        token = self._authenticate()
        request_headers: Dict[str, str] = {
            "Authorization": f"Bearer {token}",
            "Accept": "*/*",
        }
        if headers:
            request_headers.update(headers)

        response = self._session.request(
            method=method.upper(),
            url=url,
            params=params,
            headers=request_headers,
            data=data,
            timeout=60,
        )
        self._last_response_headers = dict(response.headers)

        if response.status_code not in expected_status:
            message = response.text
            try:
                error_payload = response.json()
                message = error_payload.get("error", {}).get("message", message)
            except ValueError:
                pass

            if response.status_code == 404:
                raise DataverseRecordNotFoundError(message)
            if response.status_code in (429, 503):
                raise DataverseQuotaExceededError(message)
            if response.status_code == 401:
                raise DataverseAuthenticationError(message)

            raise DataverseError(message)

        content = response.content or b""
        return content, dict(response.headers)

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------
    def health_check(self) -> Dict[str, Any]:
        try:
            payload = self._request("GET", "WhoAmI") or {}
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": payload.get("UserId"),
                "organization_id": payload.get("OrganizationId"),
                "environment_url": self._environment_url,
            }
        except DataverseError as exc:
            return {
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(exc),
                "environment_url": self._environment_url,
            }

    # ------------------------------------------------------------------
    # CRUD helpers for assets
    # ------------------------------------------------------------------
    def create_asset_metadata(self, asset_data: Dict[str, Any]) -> Dict[str, Any]:
        payload = self._transform_to_dataverse(asset_data)
        response = self._request("POST", self._assets_table, json_body=payload, expected_status=(204,), include_annotations=False)
        entity_id = self._extract_entity_id(response)
        return self.get_asset_metadata(entity_id, asset_data.get("media_type"))

    def upload_asset_file(
        self,
        asset_id: str,
        file_content: bytes,
        *,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> None:
        if not file_content:
            raise DataverseError("No file content provided for upload")

        headers = {
            "Content-Type": content_type or "application/octet-stream",
            "If-Match": "*",
        }
        if filename:
            headers["x-ms-file-name"] = filename

        self._request_binary(
            "PUT",
            f"{self._assets_table}({asset_id})/dystudio_image_file/$value",
            data=file_content,
            headers=headers,
            expected_status=(204,),
        )

    def download_asset_file(self, asset_id: str) -> Tuple[bytes, Optional[str], Optional[str]]:
        content, headers = self._request_binary(
            "GET",
            f"{self._assets_table}({asset_id})/dystudio_image_file/$value",
            expected_status=(200,),
        )
        content_type = headers.get("Content-Type")
        file_name = headers.get("x-ms-file-name")
        return content, content_type, file_name

    def get_asset_metadata(self, asset_id: str, media_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        try:
            try:
                record = self._request(
                    "GET",
                    f"{self._assets_table}({asset_id})",
                    params={"$select": ",".join(self._ASSET_SELECT_FIELDS)},
                )
            except DataverseError as e:
                # Sometimes Dataverse metadata changes haven't propagated yet and
                # a $select including a recently-added field will fail with
                # "Could not find a property named '...'". In that case retry
                # without $select to retrieve the full record.
                msg = str(e)
                logger.warning(f"Dataverse $select failed for asset {asset_id}: {msg}. Retrying without $select.")
                record = self._request(
                    "GET",
                    f"{self._assets_table}({asset_id})",
                )

            if not record:
                return None
            return self._transform_from_dataverse(record)
        except DataverseRecordNotFoundError:
            return None

    def _get_with_select_fallback(self, path: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Perform a GET with $select if provided in params, but retry without $select
        if Dataverse reports an unknown property (metadata propagation delay).
        Returns the JSON payload or raises DataverseError for other failures.
        """
        params = dict(params or {})
        try:
            return self._request("GET", path, params=params)
        except DataverseError as e:
            msg = str(e)
            if "Could not find a property named" in msg or "does not exist on type" in msg:
                logger.warning(f"Dataverse $select failed for path {path}: {msg}. Retrying without $select.")
                params.pop("$select", None)
                return self._request("GET", path, params=params)
            raise

    def update_asset_metadata(self, asset_id: str, updates: Dict[str, Any], media_type: Optional[str] = None) -> Dict[str, Any]:
        payload = self._transform_to_dataverse(updates, for_update=True)
        self._request(
            "PATCH",
            f"{self._assets_table}({asset_id})",
            json_body=payload,
            expected_status=(204,),
            include_annotations=False,
        )
        return self.get_asset_metadata(asset_id, media_type)  # type: ignore

    def delete_asset_metadata(self, asset_id: str, media_type: Optional[str] = None) -> bool:
        self._request("DELETE", f"{self._assets_table}({asset_id})", expected_status=(204,), include_annotations=False)
        return True

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------
    def query_assets(
        self,
        media_type: Optional[str] = None,
        folder_path: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "createdon",
        order_desc: bool = True,
    ) -> Dict[str, Any]:
        filters: Dict[str, Any] = {}
        if media_type:
            filters["media_type"] = media_type
        if folder_path:
            filters["folder_path"] = folder_path
        if tags:
            filters["tags"] = tags

        filter_query = self._build_odata_filter(filters)
        order_direction = "desc" if order_desc else "asc"
        page_size = max(limit, 1)
        page_offset = max(offset, 0)
        params: Dict[str, Any] = {
            "$select": ",".join(self._ASSET_SELECT_FIELDS),
            "$orderby": f"{self._translate_order_field(order_by)} {order_direction}",
            "$top": page_size,
            "$count": "true",
        }
        if page_offset > 0:
            params["$skip"] = page_offset
        if filter_query:
            params["$filter"] = filter_query

        payload = self._get_with_select_fallback(self._assets_table, params=params)
        return self._format_paged_result(payload, limit=page_size, offset=page_offset)

    def list_asset_metadata(
        self,
        limit: int = 50,
        offset: int = 0,
        media_type: Optional[str] = None,
        folder_path: Optional[str] = None,
        tags: Optional[List[str]] = None,
        order_by: str = "createdon",
        order_desc: bool = True,
    ) -> Dict[str, Any]:
        return self.query_assets(
            media_type=media_type,
            folder_path=folder_path,
            tags=tags,
            limit=limit,
            offset=offset,
            order_by=order_by,
            order_desc=order_desc,
        )

    def search_assets(
        self,
        search_term: str,
        media_type: Optional[str] = None,
        folder_path: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        filters: Dict[str, Any] = {"search": search_term}
        if media_type:
            filters["media_type"] = media_type
        if folder_path:
            filters["folder_path"] = folder_path
        if tags:
            filters["tags"] = tags

        filter_query = self._build_odata_filter(filters)
        page_size = max(limit, 1)
        page_offset = max(offset, 0)
        params: Dict[str, Any] = {
            "$select": ",".join(self._ASSET_SELECT_FIELDS),
            "$orderby": "createdon desc",
            "$top": page_size,
            "$count": "true",
        }
        if page_offset > 0:
            params["$skip"] = page_offset
        if filter_query:
            params["$filter"] = filter_query

        payload = self._get_with_select_fallback(self._assets_table, params=params)
        return self._format_paged_result(payload, limit=page_size, offset=page_offset)

    def get_folder_stats(self, media_type: Optional[str] = None) -> Dict[str, Any]:
        filter_clause = None
        if media_type:
            # Map media_type string to Dataverse CHOICE integer value
            media_type_map = {"image": 100000000, "video": 100000001}
            media_type_value = media_type_map.get(media_type.lower(), media_type)
            filter_clause = f"{self._ASSET_FIELD_MAP['media_type']} eq {media_type_value}"

        apply_parts = ["groupby((dystudio_folder_path),aggregate($count as count))"]
        params = {
            "$apply": ",".join(apply_parts),
            "$orderby": "count desc",
        }
        if filter_clause:
            params["$filter"] = filter_clause

        payload = self._request("GET", self._assets_table, params=params)
        records = payload.get("value", []) if isinstance(payload, dict) else []
        stats: List[Dict[str, Any]] = []
        for record in records:
            folder = record.get("dystudio_folder_path") or ""
            count = record.get("count", 0)
            if folder:
                stats.append({"folder_path": folder, "count": count})

        return {
            "folder_stats": stats,
            "total_folders": len(stats),
        }

    def get_all_folders(self, media_type: Optional[str] = None) -> Dict[str, Any]:
        params = {
            "$select": "dystudio_folder_path",
            "$top": 5000,
        }
        if media_type:
            # Map media_type string to Dataverse CHOICE integer value
            media_type_map = {"image": 100000000, "video": 100000001}
            media_type_value = media_type_map.get(media_type.lower(), media_type)
            params["$filter"] = f"{self._ASSET_FIELD_MAP['media_type']} eq {media_type_value}"
        payload = self._request("GET", self._assets_table, params=params)
        records = payload.get("value", []) if isinstance(payload, dict) else []
        folders = {
            (record.get("dystudio_folder_path") or "").rstrip("/")
            for record in records
            if record.get("dystudio_folder_path")
        }
        folders = {folder for folder in folders if folder}
        return {
            "folders": sorted(folders),
            "total_folders": len(folders),
        }

    def get_recent_assets(self, limit: int = 10, media_type: Optional[str] = None) -> Dict[str, Any]:
        params = {
            "$select": ",".join(self._ASSET_SELECT_FIELDS),
            "$top": limit,
            "$orderby": "createdon desc",
        }
        if media_type:
            # Map media_type string to Dataverse CHOICE integer value
            media_type_map = {"image": 100000000, "video": 100000001}
            media_type_value = media_type_map.get(media_type.lower(), media_type)
            params["$filter"] = f"{self._ASSET_FIELD_MAP['media_type']} eq {media_type_value}"
        payload = self._get_with_select_fallback(self._assets_table, params=params)
        records = payload.get("value", []) if payload else []
        return {
            "items": [self._transform_from_dataverse(record) for record in records],
            "limit": limit,
        }

    def batch_create_metadata(self, assets: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not assets:
            return {"created": 0, "errors": []}

        batch_id = uuid.uuid4().hex
        changeset_id = uuid.uuid4().hex
        boundary = f"batch_{batch_id}"
        changeset_boundary = f"changeset_{changeset_id}"
        lines: List[str] = [f"--{boundary}", f"Content-Type: multipart/mixed; boundary={changeset_boundary}", ""]

        errors: List[str] = []
        created = 0

        for index, asset in enumerate(assets, start=1):
            payload = json.dumps(self._transform_to_dataverse(asset))
            request_lines = [
                f"--{changeset_boundary}",
                "Content-Type: application/http",
                "Content-Transfer-Encoding: binary",
                "",
                f"POST {self._api_base}/{self._assets_table} HTTP/1.1",
                "Content-Type: application/json",
                "",
                payload,
            ]
            lines.extend(request_lines)
        lines.append(f"--{changeset_boundary}--")
        lines.append("")
        lines.append(f"--{boundary}--")
        body = "\r\n".join(lines)

        response = self._session.post(
            f"{self._api_base}/$batch",
            data=body,
            headers={
                **self._get_headers(include_annotations=False, custom_headers={}),
                "Content-Type": f"multipart/mixed; boundary={boundary}",
            },
            timeout=60,
        )

        if response.status_code not in (200, 202):
            errors.append(response.text)
        else:
            created = len(assets)

        return {"created": created, "errors": errors}

    # ------------------------------------------------------------------
    # Tag helpers
    # ------------------------------------------------------------------
    def associate_tags(self, asset_id: str, tag_names: List[str]) -> bool:
        if not tag_names:
            return True

        normalized_lookup: Dict[str, str] = {}
        for tag_name in tag_names:
            normalized = tag_name.strip()
            if not normalized:
                continue
            key = normalized.lower()
            if key not in normalized_lookup:
                normalized_lookup[key] = normalized

        if not normalized_lookup:
            return True

        existing_tags = self._get_tags_lookup(list(normalized_lookup.values()))
        for key, display_name in normalized_lookup.items():
            tag_id = existing_tags.get(key)
            if not tag_id:
                tag_id = self._create_tag(display_name)
            self._associate_tag(asset_id, tag_id)
        return True

    def get_asset_tags(self, asset_id: str) -> List[str]:
        params = {
            "$select": "dystudio_name",
        }
        path = f"{self._assets_table}({asset_id})/{self._relationship_asset_tags}"
        payload = self._request("GET", path, params=params)
        records = payload.get("value", []) if payload else []
        return [record.get("dystudio_name", "") for record in records if record.get("dystudio_name")]

    def search_by_tags(self, tag_names: List[str], match_all: bool = False) -> List[Dict[str, Any]]:
        tags_lookup = self._get_tags_lookup(tag_names)
        if not tags_lookup:
            return []

        filter_parts = []
        for tag_id in tags_lookup.values():
            if match_all:
                filter_parts.append(f"Microsoft.Dynamics.CRM.Contains({self._relationship_asset_tags},guid'{tag_id}')")
            else:
                filter_parts.append(f"Microsoft.Dynamics.CRM.Contains({self._relationship_asset_tags},guid'{tag_id}')")

        filter_query = " and ".join(filter_parts) if match_all else " or ".join(filter_parts)

        params = {
            "$select": ",".join(self._ASSET_SELECT_FIELDS),
            "$filter": filter_query,
        }
        payload = self._request("GET", self._assets_table, params=params)
        records = payload.get("value", []) if payload else []
        return [self._transform_from_dataverse(record) for record in records]

    # ------------------------------------------------------------------
    # Generation history helpers
    # ------------------------------------------------------------------
    def create_generation_history(self, generation_data: Dict[str, Any]) -> str:
        payload = {
            "dystudio_generation_id": generation_data.get("generation_id"),
            "dystudio_name": generation_data.get("generation_id"),  # Required field
            "dystudio_prompt": generation_data.get("prompt"),
            "dystudio_model": generation_data.get("model"),
            "dystudio_status": generation_data.get("status"),
            "dystudio_request_type": generation_data.get("request_type", "100000000"),  # Default to Image
            "dystudio_parameters_json": json.dumps(generation_data.get("parameters", {})),
            "dystudio_started_at": generation_data.get("started_at"),
            "dystudio_result_count": generation_data.get("result_count", 0),
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        response = self._request("POST", self._generation_table, json_body=payload, expected_status=(204,), include_annotations=False)
        return self._extract_entity_id(response)

    def update_generation_status(
        self,
        generation_id: str,
        status: str,
        result_count: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        payload = {
            "dystudio_status": status,
            "dystudio_result_count": result_count,
            "dystudio_error_message": error_message,
        }
        if status.lower() in {"completed", "failed"}:
            payload["dystudio_completed_at"] = datetime.utcnow().isoformat()
        payload = {k: v for k, v in payload.items() if v is not None}
        self._request(
            "PATCH",
            f"{self._generation_table}({generation_id})",
            json_body=payload,
            expected_status=(204,),
            include_annotations=False,
        )
        return True

    def link_assets_to_generation(self, generation_id: str, asset_ids: List[str]) -> bool:
        if not asset_ids:
            return True
        for asset_id in asset_ids:
            payload = {
                f"{self._ASSET_FIELD_MAP['generation_id']}@odata.bind": f"/{self._generation_table}({generation_id})",
            }
            self._request(
                "PATCH",
                f"{self._assets_table}({asset_id})",
                json_body=payload,
                expected_status=(204,),
                include_annotations=False,
            )
        return True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _extract_entity_id(self, response: Optional[Dict[str, Any]]) -> str:
        location = None
        if response:
            location = response.get("@odata.id")
        if not location and self._last_response_headers:
            location = self._last_response_headers.get("OData-EntityId") or self._last_response_headers.get("Location")
        if location:
            return location.split("(")[-1].rstrip(")")
        raise DataverseError("Unable to extract Dataverse entity identifier")

    def _translate_order_field(self, order_by: str) -> str:
        if order_by in ("created_at", "createdon"):
            return "createdon"
        if order_by in ("updated_at", "modifiedon"):
            return "modifiedon"
        return self._ASSET_FIELD_MAP.get(order_by, "createdon")

    def _extract_total_count(self, payload: Optional[Dict[str, Any]], fallback: int) -> int:
        if isinstance(payload, dict):
            raw_count = payload.get("@odata.count")
            if isinstance(raw_count, int):
                return raw_count
            if isinstance(raw_count, str):
                stripped = raw_count.strip()
                if stripped.isdigit():
                    return int(stripped)
        return fallback

    def _format_paged_result(
        self,
        payload: Optional[Dict[str, Any]],
        *,
        limit: int,
        offset: int,
    ) -> Dict[str, Any]:
        records = payload.get("value", []) if isinstance(payload, dict) else []
        items = [self._transform_from_dataverse(record) for record in records]
        total = self._extract_total_count(payload, fallback=len(items))
        has_more = False
        if isinstance(payload, dict) and payload.get("@odata.nextLink"):
            has_more = True
        elif total is not None:
            has_more = (offset + len(items)) < total
        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
        }

    def _escape_odata_string(self, value: str) -> str:
        return value.replace("'", "''")

    def _build_odata_filter(self, filters: Dict[str, Any]) -> str:
        clauses: List[str] = []
        for key, value in filters.items():
            if not value:
                continue
            if key == "media_type":
                media_type_map = {"image": 100000000, "video": 100000001}
                if isinstance(value, str):
                    lookup = media_type_map.get(value.lower())
                    if lookup is not None:
                        clauses.append(f"{self._ASSET_FIELD_MAP['media_type']} eq {lookup}")
                    else:
                        escaped_media = self._escape_odata_string(value)
                        clauses.append(f"{self._ASSET_FIELD_MAP['media_type']} eq '{escaped_media}'")
                else:
                    clauses.append(f"{self._ASSET_FIELD_MAP['media_type']} eq {value}")
            elif key == "folder_path":
                folder = str(value).strip()
                if not folder:
                    continue
                escaped_folder = self._escape_odata_string(folder)
                clauses.append(f"{self._ASSET_FIELD_MAP['folder_path']} eq '{escaped_folder}'")
            elif key == "tags":
                iterable = value if isinstance(value, (list, tuple, set)) else [value]
                tag_filters: List[str] = []
                seen_tags = set()
                for tag in iterable:
                    tag_text = str(tag).strip()
                    if not tag_text:
                        continue
                    escaped_tag = self._escape_odata_string(tag_text)
                    if escaped_tag in seen_tags:
                        continue
                    seen_tags.add(escaped_tag)
                    tag_filters.append(f"contains({self._ASSET_FIELD_MAP['tags']}, '{escaped_tag}')")
                if tag_filters:
                    clauses.append(f"({' or '.join(tag_filters)})")
            elif key == "search":
                search_text = str(value).strip()
                if not search_text:
                    continue
                escaped_value = self._escape_odata_string(search_text)
                search_fields = [
                    "dystudio_prompt",
                    "dystudio_description",
                    "dystudio_summary",
                    "dystudio_products",
                    "dystudio_filename",
                    "dystudio_url",
                ]
                conditions = [f"contains({field}, '{escaped_value}')" for field in search_fields]
                clauses.append(f"({' or '.join(conditions)})")
        return " and ".join(clauses)
    def _transform_to_dataverse(self, data: Dict[str, Any], *, for_update: bool = False) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        for field, column in self._ASSET_FIELD_MAP.items():
            if field not in data:
                continue
            value = data[field]
            if value is None:
                continue
            if field in {"tags", "analysis", "custom_metadata"}:
                payload[column] = json.dumps(value)
            elif field == "generation_id":
                payload[f"{column}@odata.bind"] = f"/{self._generation_table}({value})"
            elif field == "media_type":
                # Map media_type string to Dataverse CHOICE integer value
                media_type_map = {"image": 100000000, "video": 100000001}
                payload[column] = media_type_map.get(value.lower() if isinstance(value, str) else value, value)
            else:
                payload[column] = value
        if not for_update:
            payload.setdefault("dystudio_document_type", "vision_design")
        return payload

    def _transform_from_dataverse(self, record: Dict[str, Any]) -> Dict[str, Any]:
        # Map Dataverse CHOICE integer values back to media_type strings
        media_type_value = record.get("dystudio_media_type")
        media_type_reverse_map = {100000000: "image", 100000001: "video"}
        media_type_str = media_type_reverse_map.get(media_type_value, media_type_value) if media_type_value is not None else None
        
        transformed: Dict[str, Any] = {
            "id": record.get("dystudio_visionassetsid"),
            "media_type": media_type_str,
            "blob_name": record.get("dystudio_blob_name"),
            "container": record.get("dystudio_container"),
            "url": record.get("dystudio_url"),
            "filename": record.get("dystudio_filename"),
            "size": record.get("dystudio_size"),
            "content_type": record.get("dystudio_content_type"),
            "folder_path": record.get("dystudio_folder_path") or "",
            "prompt": record.get("dystudio_prompt"),
            "model": record.get("dystudio_model"),
            "generation_id": record.get("dystudio_generation_id"),
            "summary": record.get("dystudio_summary"),
            "description": record.get("dystudio_description"),
            "products": record.get("dystudio_products"),
            "feedback": record.get("dystudio_feedback"),
            "quality": record.get("dystudio_quality"),
            "background": record.get("dystudio_background"),
            "output_format": record.get("dystudio_output_format"),
            "has_transparency": record.get("dystudio_has_transparency"),
            "duration": record.get("dystudio_duration"),
            "fps": record.get("dystudio_fps"),
            "resolution": record.get("dystudio_resolution"),
            "width": record.get("dystudio_width"),
            "height": record.get("dystudio_height"),
            "has_analysis": record.get("dystudio_has_analysis", False),
            "image_data": record.get("dystudio_image_data"),
            "created_at": record.get("createdon"),
            "updated_at": record.get("modifiedon"),
            "doc_type": "asset_metadata",
        }

        tags_json = record.get("dystudio_tags")
        analysis_json = record.get("dystudio_analysis_data")
        custom_json = record.get("dystudio_custom_metadata")

        transformed["tags"] = self._safe_json_loads(tags_json, default=[])
        transformed["analysis"] = self._safe_json_loads(analysis_json)
        transformed["custom_metadata"] = self._safe_json_loads(custom_json)

        if transformed.get("created_at") and isinstance(transformed["created_at"], str):
            transformed["created_at"] = self._ensure_iso8601(transformed["created_at"])
        else:
            transformed["created_at"] = datetime.utcnow().isoformat()

        if transformed.get("updated_at") and isinstance(transformed["updated_at"], str):
            transformed["updated_at"] = self._ensure_iso8601(transformed["updated_at"])
        else:
            transformed["updated_at"] = transformed["created_at"]

        return transformed

    def _safe_json_loads(self, value: Optional[str], default: Optional[Any] = None) -> Any:
        if not value:
            return default
        if isinstance(value, (list, dict)):
            return value
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return default

    def _ensure_iso8601(self, value: str) -> str:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.astimezone(timezone.utc).isoformat()
        except ValueError:
            return value

    def _get_tags_lookup(self, tag_names: List[str]) -> Dict[str, str]:
        if not tag_names:
            return {}
        clauses = [f"tolower(dystudio_name) eq '{name.lower()}'" for name in tag_names if name]
        if not clauses:
            return {}
        filter_clause = " or ".join(clauses)
        payload = self._request(
            "GET",
            self._tags_table,
            params={"$select": "dystudio_assettagid,dystudio_name", "$filter": filter_clause},
        )
        records = payload.get("value", []) if isinstance(payload, dict) else []
        return {record.get("dystudio_name", "").lower(): record.get("dystudio_assettagid") for record in records if record.get("dystudio_assettagid")}

    def _create_tag(self, tag_name: str) -> str:
        payload = {
            "dystudio_name": tag_name,
            "dystudio_tag_name": tag_name,  # Required field
            "dystudio_usage_count": 0,
        }
        response = self._request("POST", self._tags_table, json_body=payload, expected_status=(204,), include_annotations=False)
        return self._extract_entity_id(response)

    def _associate_tag(self, asset_id: str, tag_id: str) -> None:
        path = f"{self._tags_table}({tag_id})/$ref"
        payload = {"@odata.id": f"{self._api_base}/{self._assets_table}({asset_id})"}
        self._request("POST", path, json_body=payload, expected_status=(204,), include_annotations=False)
