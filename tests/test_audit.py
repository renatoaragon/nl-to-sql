import json

from nl2sql.audit import OUTCOME_EXECUTED, OUTCOME_REJECTED, record_query


def test_records_an_executed_query(tmp_path):
    path = tmp_path / "logs" / "audit.jsonl"  # parent dir created by the writer

    entry = record_query(str(path), "total per category", "SELECT 1", OUTCOME_EXECUTED)

    assert entry["outcome"] == OUTCOME_EXECUTED
    assert path.exists()
    line = json.loads(path.read_text(encoding="utf-8").strip())
    assert line["question"] == "total per category"
    assert line["sql"] == "SELECT 1"
    assert line["detail"] == ""
    assert "ts" in line


def test_rejection_keeps_the_guard_reason(tmp_path):
    path = tmp_path / "audit.jsonl"

    record_query(str(path), "drop everything", "DROP TABLE orders",
                 OUTCOME_REJECTED, "Only SELECT queries are allowed, got 'drop'.")

    line = json.loads(path.read_text(encoding="utf-8").strip())
    assert line["outcome"] == OUTCOME_REJECTED
    assert "Only SELECT" in line["detail"]
    # The offending SQL is kept for review, not swallowed.
    assert line["sql"] == "DROP TABLE orders"


def test_appends_rather_than_overwrites(tmp_path):
    path = tmp_path / "audit.jsonl"

    record_query(str(path), "q1", "SELECT 1", OUTCOME_EXECUTED)
    record_query(str(path), "q2", "SELECT 2", OUTCOME_EXECUTED)

    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert [json.loads(x)["question"] for x in lines] == ["q1", "q2"]
