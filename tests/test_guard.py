import pytest

from nl2sql.guard import (
    UnsafeQueryError,
    enforce_limit,
    ensure_known_tables,
    ensure_read_only,
    referenced_tables,
)


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


# --- enforce_limit: unbounded queries get a cap, expressed intent is kept ---


def test_appends_limit_to_unbounded_query():
    assert enforce_limit("SELECT * FROM orders", 500) == "SELECT * FROM orders\nLIMIT 500"


def test_respects_an_existing_top_level_limit():
    sql = "SELECT * FROM orders LIMIT 10"
    assert enforce_limit(sql, 500) == sql


def test_respects_limit_with_offset():
    sql = "SELECT * FROM orders LIMIT 10 OFFSET 20"
    assert enforce_limit(sql, 500) == sql


def test_limit_in_a_subquery_does_not_count():
    # The inner LIMIT bounds the subquery, not the result set.
    sql = "SELECT * FROM (SELECT * FROM orders LIMIT 5) t JOIN customers c ON t.customer_id = c.id"
    assert enforce_limit(sql, 500).endswith("\nLIMIT 500")


def test_limit_inside_a_string_literal_does_not_count():
    sql = "SELECT 'no limit 5 here' AS note FROM orders"
    assert enforce_limit(sql, 500).endswith("\nLIMIT 500")


def test_appended_limit_survives_a_trailing_comment():
    out = enforce_limit("SELECT 1 -- note", 500)
    # The newline ends the line comment, so the LIMIT is real SQL.
    assert out == "SELECT 1 -- note\nLIMIT 500"


# --- ensure_known_tables: the query may only touch the schema it was shown ---

ALLOWED = {"orders", "customers"}


def test_finds_tables_after_from_and_join():
    sql = "SELECT * FROM orders o JOIN customers c ON c.id = o.customer_id"
    assert referenced_tables(sql) == {"orders", "customers"}


def test_allows_queries_within_the_schema():
    sql = "SELECT * FROM orders JOIN customers ON customers.id = orders.customer_id"
    assert ensure_known_tables(sql, ALLOWED) == sql


def test_allows_cte_names_defined_in_the_query():
    sql = "WITH recent AS (SELECT * FROM orders) SELECT * FROM recent"
    assert ensure_known_tables(sql, ALLOWED) == sql


def test_rejects_system_catalogs():
    for sql in (
        "SELECT * FROM information_schema.tables",
        "SELECT * FROM pg_catalog.pg_tables",
        "SELECT * FROM duckdb_settings()",
    ):
        with pytest.raises(UnsafeQueryError, match="system catalog"):
            ensure_known_tables(sql, ALLOWED)


def test_rejects_tables_outside_the_schema():
    with pytest.raises(UnsafeQueryError, match="Unknown table"):
        ensure_known_tables("SELECT * FROM salaries", ALLOWED)


def test_table_name_inside_a_literal_is_not_a_reference():
    # The lexer runs first, so "from secrets" inside a string is just text.
    sql = "SELECT 'from secrets' AS note FROM orders"
    assert ensure_known_tables(sql, ALLOWED) == sql
