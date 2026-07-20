"""Introspect a DuckDB connection and render its schema as text for the prompt."""

import duckdb


def list_tables(conn: duckdb.DuckDBPyConnection) -> set[str]:
    """The tables the model is shown — and therefore the only ones it may use."""
    rows = conn.execute(
        """
        select table_name
        from information_schema.tables
        where table_schema = 'main'
        """
    ).fetchall()
    return {name for (name,) in rows}


def render_schema(conn: duckdb.DuckDBPyConnection) -> str:
    """Return a compact `table(col type, ...)` description of every table."""
    tables = conn.execute(
        """
        select table_name
        from information_schema.tables
        where table_schema = 'main'
        order by table_name
        """
    ).fetchall()

    lines: list[str] = []
    for (table,) in tables:
        cols = conn.execute(
            """
            select column_name, data_type
            from information_schema.columns
            where table_name = ?
            order by ordinal_position
            """,
            [table],
        ).fetchall()
        col_desc = ", ".join(f"{name} {dtype}" for name, dtype in cols)
        lines.append(f"{table}({col_desc})")

    return "\n".join(lines)
