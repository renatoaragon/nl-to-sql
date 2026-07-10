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


# --- Normalization: literals and comments must not cause false rejections ---


def test_allows_keyword_inside_string_literal():
    sql = "SELECT 'please drop table orders' AS note"
    assert ensure_read_only(sql) == sql


def test_allows_semicolon_inside_string_literal():
    sql = "SELECT ';' AS separator"
    assert ensure_read_only(sql) == sql


def test_allows_keyword_inside_line_comment():
    sql = "SELECT 1 -- update this note later"
    assert ensure_read_only(sql) == sql


def test_allows_keyword_inside_block_comment():
    sql = "SELECT 1 /* delete nothing, just a comment */"
    assert ensure_read_only(sql) == sql


def test_allows_quoted_identifier_named_like_keyword():
    sql = 'SELECT "insert" FROM events'
    assert ensure_read_only(sql) == sql


def test_allows_escaped_quotes_within_literal():
    # The '' escape keeps the lexer inside the literal: everything here is a
    # plain string value, not a second statement.
    sql = "SELECT 'a''; drop table orders; --' AS tricky"
    assert ensure_read_only(sql) == sql


# --- Hardening: attacks the raw-text scan used to miss or mishandle ---


def test_rejects_statement_stacked_after_block_comment():
    with pytest.raises(UnsafeQueryError):
        ensure_read_only("SELECT 1 /* x */; DROP TABLE orders")


def test_rejects_keyword_when_literal_closes_before_it():
    with pytest.raises(UnsafeQueryError):
        ensure_read_only("SELECT 'done'; DELETE FROM orders")


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM read_csv_auto('/etc/passwd')",
        "SELECT * FROM read_parquet('secrets.parquet')",
        "SELECT * FROM glob('**')",
    ],
)
def test_rejects_filesystem_table_functions(sql):
    with pytest.raises(UnsafeQueryError):
        ensure_read_only(sql)


def test_rejects_dollar_quoted_strings():
    with pytest.raises(UnsafeQueryError):
        ensure_read_only("SELECT $$drop table orders$$")


def test_rejects_unterminated_string():
    with pytest.raises(UnsafeQueryError):
        ensure_read_only("SELECT 'oops")


def test_rejects_comment_only_query():
    with pytest.raises(UnsafeQueryError):
        ensure_read_only("-- nothing but a comment")
