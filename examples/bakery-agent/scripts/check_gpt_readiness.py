#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
DSL_PATH = ROOT / "dify" / "workflows" / "bakery_operation_v1.dify.yml"


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def masked(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def check_dify_dsl() -> list[str]:
    errors: list[str] = []
    if not DSL_PATH.exists():
        return [f"Missing Dify DSL: {DSL_PATH.relative_to(ROOT)}"]
    text = DSL_PATH.read_text(encoding="utf-8", errors="ignore")
    if "provider: openai" not in text:
        errors.append("Dify LLM workflow does not reference provider: openai")
    if "name: gpt-4.1-mini" not in text and "name: gpt-4o" not in text:
        errors.append("Dify LLM workflow does not contain an expected GPT model name")
    return errors


def request_model(base_url: str, api_key: str, model: str, timeout: int) -> tuple[bool, str]:
    url = f"{base_url.rstrip('/')}/models/{model}"
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        return False, f"OpenAI model check failed with HTTP {exc.code}: {body[:200]}"
    except Exception as exc:
        return False, f"OpenAI model check failed: {exc}"

    returned_model = payload.get("id", "")
    if returned_model != model:
        return False, f"OpenAI returned unexpected model id: {returned_model}"
    return True, f"OpenAI model reachable: {returned_model}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check GPT-only readiness for Phase 1.2.")
    parser.add_argument("--require-key", action="store_true", help="Fail if OPENAI_API_KEY is missing.")
    parser.add_argument("--live", action="store_true", help="Call the OpenAI-compatible /models/{model} endpoint.")
    args = parser.parse_args()

    load_dotenv(ENV_PATH)

    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    timeout = int(os.getenv("OPENAI_TIMEOUT_SECONDS", "60") or "60")

    errors = check_dify_dsl()
    report = {
        "phase": "1.2",
        "provider": "openai",
        "base_url": base_url,
        "model": model,
        "api_key_present": bool(api_key),
        "api_key_masked": masked(api_key),
        "dify_dsl_ready": not errors,
        "live_check": "not_requested",
    }

    if args.require_key and not api_key:
        errors.append("OPENAI_API_KEY is required but missing")

    if args.live:
        if not api_key:
            report["live_check"] = "skipped_missing_key"
            if args.require_key:
                errors.append("Cannot run live OpenAI check without OPENAI_API_KEY")
        else:
            ok, message = request_model(base_url, api_key, model, timeout)
            report["live_check"] = "passed" if ok else "failed"
            report["live_message"] = message
            if not ok:
                errors.append(message)

    report["errors"] = errors
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
