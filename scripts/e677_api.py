from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Any


API_BASE_URL = "https://eq677.icarm.cloud"
MANIFEST_URL = f"{API_BASE_URL}/manifest.json"
TOKEN_ENV = "EQ677_API_TOKEN"


def configure_utf8_stdio() -> None:
    """Make Windows console output safe for manifest comments containing Unicode."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def is_url(path_or_url: str) -> bool:
    return path_or_url.startswith("http://") or path_or_url.startswith("https://")


def api_url(path: str) -> str:
    if is_url(path):
        return path
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{API_BASE_URL}{path}"


def fetch_json(path_or_url: str) -> Any:
    if is_url(path_or_url):
        with urllib.request.urlopen(path_or_url, timeout=60) as response:
            return json.load(response)
    return json.loads(Path(path_or_url).read_text(encoding="utf-8"))


def fetch_text(path_or_url: str) -> str:
    if is_url(path_or_url):
        with urllib.request.urlopen(path_or_url, timeout=60) as response:
            return response.read().decode("utf-8")
    return Path(path_or_url).read_text(encoding="utf-8")


def load_manifest(path_or_url: str = MANIFEST_URL) -> dict[str, Any]:
    data = fetch_json(path_or_url)
    if not isinstance(data, dict) or not isinstance(data.get("magmas"), list):
        raise ValueError("manifest must be an object with a magmas array")
    return data


def table_url(record_or_hash: dict[str, Any] | str) -> str:
    if isinstance(record_or_hash, dict):
        url = record_or_hash.get("url")
        if isinstance(url, str) and url:
            return url
        canonical_hash = record_or_hash.get("canonical_hash")
        if not isinstance(canonical_hash, str):
            raise ValueError("record has neither url nor canonical_hash")
    else:
        canonical_hash = record_or_hash
    return api_url(f"/magma/{canonical_hash}/table.txt")


def auth_token(token: str | None = None) -> str:
    token = token or os.environ.get(TOKEN_ENV)
    if not token:
        raise ValueError(f"authenticated API calls require ${TOKEN_ENV}")
    return token


def api_request(
    method: str,
    path: str,
    *,
    body: bytes | None = None,
    content_type: str | None = None,
    token: str | None = None,
) -> Any:
    headers: dict[str, str] = {}
    if content_type is not None:
        headers["Content-Type"] = content_type
    if token is not None:
        headers["Authorization"] = f"Bearer {auth_token(token)}"
    request = urllib.request.Request(api_url(path), data=body, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=60) as response:
        raw = response.read()
        content_type_header = response.headers.get("content-type", "")
    if "application/json" in content_type_header:
        return json.loads(raw.decode("utf-8"))
    return raw.decode("utf-8")


def authenticated_json_post(path: str, payload: dict[str, Any], token: str | None = None) -> Any:
    return api_request(
        "POST",
        path,
        body=json.dumps(payload).encode("utf-8"),
        content_type="application/json",
        token=auth_token(token),
    )


def submit_table(table_text: str, *, content_type: str = "text/plain", token: str | None = None) -> Any:
    if content_type not in {"text/plain", "application/json"}:
        raise ValueError("submit content type must be text/plain or application/json")
    return api_request(
        "POST",
        "/submit",
        body=table_text.encode("utf-8"),
        content_type=content_type,
        token=auth_token(token),
    )


def post_magma_comment(canonical_hash: str, content: str, token: str | None = None) -> Any:
    return authenticated_json_post(f"/magma/{canonical_hash}/comment", {"content": content}, token)


def post_size_comment(size: int, content: str, token: str | None = None) -> Any:
    return authenticated_json_post(f"/size/{size}/comment", {"content": content}, token)


def post_display_reorder(canonical_hash: str, display_reorder: str | None, token: str | None = None) -> Any:
    return authenticated_json_post(
        f"/magma/{canonical_hash}/display-reorder",
        {"display_reorder": display_reorder},
        token,
    )
