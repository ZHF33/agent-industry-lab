#!/usr/bin/env python3
from pathlib import Path
import re
import sys
import json

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "README.md",
    ".env.example",
    "docker-compose.yml",
    "configs/models.example.yml",
    "configs/api_providers.example.yml",
    "configs/agent_config.yml",
    "configs/platform_rules.yml",
    "knowledge/raw/.gitkeep",
    "knowledge/processed/.gitkeep",
    "knowledge/products/.gitkeep",
    "knowledge/brand/.gitkeep",
    "knowledge/customers/.gitkeep",
    "knowledge/marketing/.gitkeep",
    "knowledge/competitors/.gitkeep",
    "knowledge/platforms/.gitkeep",
    "knowledge/campaigns/.gitkeep",
    "knowledge/templates/product.schema.example.json",
    "knowledge/templates/brand.schema.example.json",
    "knowledge/templates/campaign.schema.example.json",
    "scripts/normalize_knowledge.py",
    "scripts/build_knowledge_index.py",
    "scripts/build_agent_context.py",
    "scripts/check_gpt_readiness.py",
    "scripts/check_image_readiness.py",
    "scripts/check_publish_readiness.py",
    "scripts/enhance_image_prompt.py",
    "scripts/generate_openai_image.py",
    "scripts/generate_approved_images.py",
    "scripts/select_image_variant.py",
    "scripts/prepare_publish_draft.py",
    "scripts/record_manual_publish.py",
    "scripts/create_approval_package.py",
    "scripts/update_approval_status.py",
    "scripts/list_approval_queue.py",
    "scripts/revise_from_approval.py",
    "scripts/init_local_db.py",
    "scripts/sync_approval_to_db.py",
    "scripts/run_dify_workflow_test.py",
    "scripts/run_content_operation.py",
    "scripts/query_ops_status.py",
    "scripts/ops_dashboard.py",
    "scripts/apply_next_action.py",
    "scripts/run_v2_acceptance.py",
    "scripts/verify_run_artifacts.py",
    "scripts/agent_http_api.py",
    "scripts/check_system_health.py",
    "scripts/production_readiness.py",
    "scripts/audit_runtime_artifacts.py",
    "scripts/cleanup_runtime_artifacts.ps1",
    "scripts/export_n8n_workflow_state.ps1",
    "scripts/start_agent_http_api.ps1",
    "scripts/stop_agent_http_api.ps1",
    "scripts/run_agent_http_api.cmd",
    "scripts/export_dify_prompts.py",
    "n8n/workflows/v2_full_content_pipeline_webhook.json",
    "n8n/workflows/v2_content_operation_webhook.json",
    "n8n/workflows/v2_approval_review_webhook.json",
    "n8n/workflows/v2_image_generation_webhook.json",
    "n8n/workflows/v2_image_selection_webhook.json",
    "n8n/workflows/v2_publish_draft_webhook.json",
    "n8n/workflows/v2_publish_record_webhook.json",
    "n8n/workflows/v2_publish_mock_webhook.json",
    "services/__init__.py",
    "services/approval_service.py",
    "services/revision_service.py",
    "services/asset_service.py",
    "services/knowledge_service.py",
    "services/image_service.py",
    "services/image_generation_service.py",
    "services/image_selection_service.py",
    "services/publish_service.py",
    "services/publisher_service.py",
    "services/video_service.py",
    "services/db_service.py",
    "services/db_sync_service.py",
    "services/dify_client.py",
    "services/image_prompt_service.py",
    "services/operation_log_service.py",
    "services/campaign_service.py",
    "services/task_service.py",
    "docs/verification.md",
]

ENV_KEYS = [
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_MODEL",
    "OPENAI_TIMEOUT_SECONDS",
    "OPENAI_IMAGE_MODEL",
    "OPENAI_IMAGE_SIZE",
    "OPENAI_IMAGE_QUALITY",
    "ANTHROPIC_API_KEY",
    "SEEDANCE_API_KEY",
    "KLING_API_KEY",
    "DIFY_API_KEY",
    "DIFY_BASE_URL",
    "N8N_BASE_URL",
    "N8N_WEBHOOK_SECRET",
    "N8N_BASIC_AUTH_USER",
    "N8N_BASIC_AUTH_PASSWORD",
    "N8N_ENCRYPTION_KEY",
    "AGENT_API_URL",
    "AGENT_API_ALLOW_LIVE_IMAGE",
    "AGENT_API_TOKEN",
    "FEISHU_APP_ID",
    "FEISHU_APP_SECRET",
    "PUBLISH_CONNECTOR_MODE",
    "MOCK_PUBLISH_ENABLED",
    "XIAOHONGSHU_PUBLISH_ENABLED",
    "XIAOHONGSHU_PUBLISH_TOKEN",
    "DOUYIN_PUBLISH_ENABLED",
    "DOUYIN_PUBLISH_TOKEN",
]

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)(api[_-]?key|secret)\s*[:=]\s*['\"][^'\"\n]{12,}['\"]"),
]

SKIP_DIRS = {".venv", ".docker", "__pycache__", ".git", ".pytest_cache"}
SKIP_LARGE_SUFFIXES = {".sqlite3", ".db"}
SKIP_LARGE_PATH_PREFIXES = {
    Path("runs/generated_images"),
}


def fail(message: str, errors: list[str]) -> None:
    errors.append(message)


def main() -> int:
    errors: list[str] = []

    for rel in REQUIRED_FILES:
        if not (ROOT / rel).exists():
            fail(f"Missing required file: {rel}", errors)

    env_text = (ROOT / ".env.example").read_text(encoding="utf-8")
    for key in ENV_KEYS:
        if f"{key}=" not in env_text:
            fail(f".env.example missing {key}", errors)

    for prompt in (ROOT / "dify" / "prompts").glob("*.md"):
        if not prompt.read_text(encoding="utf-8").strip():
            fail(f"Empty prompt file: {prompt.relative_to(ROOT)}", errors)

    required_terms = ["输入变量", "输出变量", "Prompt", "JSON", "失败处理"]
    for workflow in (ROOT / "dify" / "workflows").glob("*.workflow.md"):
        text = workflow.read_text(encoding="utf-8")
        for term in required_terms:
            if term not in text:
                fail(f"{workflow.relative_to(ROOT)} missing {term}", errors)

    for rel in [
        "knowledge/raw",
        "knowledge/processed",
        "knowledge/standard",
        "knowledge/products",
        "knowledge/brand",
        "knowledge/customers",
        "knowledge/marketing",
        "knowledge/competitors",
        "knowledge/platforms",
        "knowledge/campaigns",
        "knowledge/templates",
    ]:
        if not (ROOT / rel).is_dir():
            fail(f"Missing knowledge dir: {rel}", errors)

    for schema in (ROOT / "knowledge" / "templates").glob("*.json"):
        try:
            data = json.loads(schema.read_text(encoding="utf-8"))
        except Exception as exc:
            fail(f"Invalid knowledge template JSON: {schema.relative_to(ROOT)} ({exc})", errors)
            continue
        for key in ["id", "type", "name", "tags", "source_file", "confidence", "fields", "todo"]:
            if key not in data:
                fail(f"{schema.relative_to(ROOT)} missing key {key}", errors)

    scan_ext = {".md", ".yml", ".yaml", ".json", ".py", ".sh", ".example"}
    for path in ROOT.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in scan_ext:
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in SECRET_PATTERNS:
                if pattern.search(text):
                    fail(f"Possible hardcoded secret in {path.relative_to(ROOT)}", errors)

    large_files = [
        p
        for p in ROOT.rglob("*")
        if p.is_file()
        and not any(part in SKIP_DIRS for part in p.parts)
        and not any(p.relative_to(ROOT).is_relative_to(prefix) for prefix in SKIP_LARGE_PATH_PREFIXES)
        and p.suffix.lower() not in SKIP_LARGE_SUFFIXES
        and p.stat().st_size > 1_000_000
    ]
    for path in large_files:
        fail(f"Unexpected large file: {path.relative_to(ROOT)}", errors)

    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
