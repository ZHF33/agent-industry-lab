from services import db_service


def test_db_schema_has_v15_tables(tmp_path):
    db = tmp_path / "ops.sqlite3"
    db_service.init_db(db)
    with db_service.get_connection(db) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"campaigns", "content_runs", "generated_assets", "approval_reviews", "tasks", "campaign_history"} <= tables


def test_query_recent_runs(tmp_path):
    db = tmp_path / "ops.sqlite3"
    with db_service.get_connection(db) as conn:
        db_service.upsert_content_run(conn, {"run_id": "run_a", "approval_status": "pending"})
    with db_service.get_connection(db) as conn:
        assert db_service.query_recent_runs(conn)[0]["run_id"] == "run_a"


def test_legacy_db_tables_are_preserved(tmp_path):
    import sqlite3

    db = tmp_path / "ops.sqlite3"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE content_runs(id INTEGER PRIMARY KEY, package_id TEXT)")
        conn.execute("INSERT INTO content_runs(package_id) VALUES ('old')")
    db_service.init_db(db)
    with sqlite3.connect(db) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        cols = {row[1] for row in conn.execute("PRAGMA table_info(content_runs)")}
    assert "content_runs" in tables
    assert "run_id" in cols
    assert any(name.startswith("content_runs_legacy_") for name in tables)
