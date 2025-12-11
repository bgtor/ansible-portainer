from __future__ import annotations

import json
import uuid

from urllib.parse import urlencode
from typing import Literal, Any, overload
from enum import Enum

from ansible.module_utils.urls import fetch_url
from ansible.module_utils.basic import AnsibleModule


def encode_multipart_formdata(fields: dict) -> tuple[bytes, str]:
    """
    Encode fields as multipart/form-data with support for files
    fields: dict of field_name: value
           - For files: value should be tuple (filename, file_content, mime_type)
           - For regular fields: value is a string or list
    """
    boundary = str(uuid.uuid4())
    parts = []

    for key, value in fields.items():
        # Handle lists by repeating the key
        if isinstance(value, list):
            for item in value:
                parts.append(f"--{boundary}\r\n".encode("utf-8"))
                parts.append(
                    f'Content-Disposition: form-data; name="{key}[]"\r\n\r\n'.encode("utf-8")
                )
                parts.append(f"{item}\r\n".encode("utf-8"))
        # Handle file upload: (filename, content, mime_type)
        elif isinstance(value, tuple) and len(value) == 3:
            filename, file_content, mime_type = value
            parts.append(f"--{boundary}\r\n".encode("utf-8"))
            parts.append(
                f'Content-Disposition: form-data; name="{key}"; filename="{filename}"\r\n'.encode(
                    "utf-8"
                )
            )
            parts.append(f"Content-Type: {mime_type}\r\n\r\n".encode("utf-8"))
            # File content should already be bytes
            if isinstance(file_content, str):
                file_content = file_content.encode("utf-8")
            parts.append(file_content)
            parts.append(b"\r\n")
        # Handle regular field
        else:
            parts.append(f"--{boundary}\r\n".encode("utf-8"))
            parts.append(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"))
            parts.append(f"{value}\r\n".encode("utf-8"))

    parts.append(f"--{boundary}--\r\n".encode("utf-8"))

    body = b"".join(parts)
    content_type = f"multipart/form-data; boundary={boundary}"

    return body, content_type


class PortainerApiError(Exception):
    def __init__(
        self,
        message,
        status: int | None = None,
        body: Any | None = None,
        url: str | None = None,
        method: str | None = None,
        data: dict | None = None,
    ):
        super().__init__(message)
        self.status = status
        self.body = body
        self.url = url
        self.method = method
        self.data = data


class BodyFormat(Enum):
    JSON = "json"
    FORM_DATA = "form-data"


class RequestMethod(Enum):
    GET = "GET"
    PUT = "PUT"
    POST = "POST"
    DELETE = "DELETE"


class PortainerClient:

    class exc:
        PortainerApiError = PortainerApiError

    ARGSPEC = dict(
        portainer_url=dict(type="str", required=True),
        portainer_token=dict(type="str", required=True, no_log=True),
        validate_certs=dict(type="bool", default=True),
        timeout=dict(type="int", default=30),
    )

    def __init__(self, module: AnsibleModule):
        self.module = module

        self.portainer_url = module.params["portainer_url"].rstrip("/")
        self.portainer_token = module.params["portainer_token"]
        self.timeout = module.params["timeout"]

        self.headers = {
            "X-API-Key": self.portainer_token,
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        return self._make_request(RequestMethod.GET, endpoint, params=params)

    def post(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        body_format: BodyFormat | None = None,
        params: dict | None = None,
    ) -> dict[str, Any]:
        return self._make_request(
            RequestMethod.POST, endpoint=endpoint, data=data, body_format=body_format, params=params
        )

    def put(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        body_format: BodyFormat | None = None,
        params: dict | None = None,
    ) -> dict[str, Any]:
        return self._make_request(
            RequestMethod.PUT, endpoint=endpoint, data=data, body_format=body_format, params=params
        )

    def delete(self, endpoint: str, params: dict | None = None):
        return self._make_request(RequestMethod.DELETE, endpoint=endpoint, params=params)

    @overload
    def _make_request(
        self,
        method: RequestMethod,
        endpoint: str,
        return_info: Literal[False] = False,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        body_format: BodyFormat | None = None,
    ) -> Any: ...

    @overload
    def _make_request(
        self,
        method: RequestMethod,
        endpoint: str,
        return_info: Literal[True],
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        body_format: BodyFormat | None = None,
    ) -> dict[str, Any]: ...

    def _make_request(
        self,
        method: RequestMethod,
        endpoint: str,
        return_info: bool = False,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        body_format: BodyFormat | None = None,
    ) -> Any:
        """Make HTTP request to Portainer API"""
        url = f"{self.portainer_url}/api{endpoint}"
        body_format = BodyFormat.JSON if not body_format else body_format
        data = {} if data is None else data

        if params:
            # Convert booleans to lowercase strings
            params_converted = {
                k: str(v).lower() if isinstance(v, bool) else v for k, v in params.items()
            }
            url = f"{url}?{urlencode(params_converted)}"

        _data = None
        if body_format == BodyFormat.JSON:
            _data = json.dumps(data)
        elif body_format == BodyFormat.FORM_DATA:
            _data, content_type = encode_multipart_formdata(data)
            self.headers.update({"Content-Type": content_type})

        resp, info = fetch_url(
            self.module,
            url,
            method=method.value,
            headers=self.headers,
            data=_data,
            force=True,
            timeout=self.timeout,
        )

        if return_info:
            return info

        if info["status"] not in [200, 201, 204]:
            raise PortainerApiError(
                f"{info['msg']}",
                status=info["status"],
                body=info.get("body", ""),
                url=url,
                method=method.value,
                data=data,
            )

        if resp:
            body = resp.read()

            if body:
                return json.loads(body)
        return None

    def ping(self):
        info = self._make_request(RequestMethod.GET, "/system/status", return_info=True)

        if info["status"] not in [200]:
            self.module.warn("Cannot reach portainer - check IP and port.")
            self.module.fail_json(
                msg=f"Portainer server not reachable: {info['msg']}",
                status=info["status"],
                body=info.get("body", ""),
            )
