from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


def workflow_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/v1/workflows/run"


def call_workflow(base_url: str, api_key: str, payload: dict[str, Any], timeout: int = 240, *, label: str = "Dify") -> dict[str, Any]:
    request = urllib.request.Request(
        workflow_url(base_url),
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"{label} request failed HTTP {exc.code}: {body}") from exc
