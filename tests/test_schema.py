from nl2sql.db import build_sample_db
from nl2sql.guard import ensure_read_only
from nl2sql.schema import render_schema


def test_schema_lists_tables_and_columns():
    conn = build_sample_db()
    schema = render_schema(conn)
    assert "customers(" in schema
    assert "orders(" in schema
    assert "amount" in schema


def test_generated_select_runs_on_sample_db():
    """End-to-end minus the LLM: a hand-written SELECT passes the guard and runs."""
    conn = build_sample_db()
    sql = ensure_read_only(
        "SELECT category, sum(amount) AS total FROM orders GROUP BY category"
    )
    rows = dict(conn.execute(sql).fetchall())
    assert rows["books"] == 47.49
