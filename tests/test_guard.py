import pytest

from nl2sql.guard import UnsafeQueryError, ensure_read_only


def test_allows_plain_select():
    assert ensure_read_only("SELECT * FROM orders") == "SELECT * FROM orders"


def test_allows_cte():
    sql = "WITH t AS (SELECT 1 AS x) SELECT x FROM t"
    assert ensure_read_only(sql) == sql


def test_strips_trailing_semicolon():
    assert ensure_read_only("SELECT 1;") == "SELECT 1"


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM orders",
        "DROP TABLE orders",
        "UPDATE orders SET amount = 0",
        "INSERT INTO orders VALUES (1)",
        "TRUNCATE orders",
    ],
)
def test_rejects_mutations(sql):
    with pytest.raises(UnsafeQueryError):
        ensure_read_only(sql)


def test_rejects_stacked_statements():
    with pytest.raises(UnsafeQueryError):
        ensure_read_only("SELECT 1; DROP TABLE orders")


def test_rejects_empty():
    with pytest.raises(UnsafeQueryError):
        ensure_read_only("   ")
