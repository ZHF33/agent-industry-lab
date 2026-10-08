from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_cleanup_script_removes_all_pytest_tmp_variants():
    script = (ROOT / "scripts" / "cleanup_runtime_artifacts.ps1").read_text(encoding="utf-8")
    assert '-Filter ".pytest_tmp*"' in script
    assert '-Filter "pytest_tmp*"' in script
    assert 'Join-Path $Root "runs"' in script


def test_cleanup_script_removes_n8n_database_inspect_files():
    script = (ROOT / "scripts" / "cleanup_runtime_artifacts.ps1").read_text(encoding="utf-8")
    assert 'n8n_database_inspect.sqlite*' in script


def test_export_n8n_workflow_state_script_exists_and_is_readonly():
    script = (ROOT / "scripts" / "export_n8n_workflow_state.ps1").read_text(encoding="utf-8")
    assert "docker cp" in script
    assert "inspect_n8n_workflows.py" in script
    assert "publish:workflow" not in script


def test_gitignore_excludes_pytest_tmp_variants():
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".pytest_tmp*/" in gitignore
    assert "runs/pytest_tmp*/" in gitignore
    assert "data/generated_images_runtime/" in gitignore
