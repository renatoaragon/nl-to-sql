"""CLI: ask a question in English, get an answer from the sample database.

Flow: build schema text -> ask Claude for SQL -> guard it -> run it on DuckDB.
Requires ANTHROPIC_API_KEY in the environment for the LLM step.
"""

import argparse

from nl2sql.db import build_sample_db
from nl2sql.guard import ensure_known_tables, enforce_limit, ensure_read_only
from nl2sql.llm import generate_sql
from nl2sql.schema import list_tables, render_schema


def answer(question: str) -> None:
    conn = build_sample_db()
    schema_text = render_schema(conn)

    raw_sql = generate_sql(question, schema_text)
    # Three gates, narrowing in turn: is it read-only, does it stay inside the
    # schema the model was shown, and is the result set bounded.
    safe_sql = enforce_limit(
        ensure_known_tables(ensure_read_only(raw_sql), list_tables(conn))
    )

    print(f"\nSQL:\n{safe_sql}\n")
    rows = conn.execute(safe_sql).fetchall()
    columns = [d[0] for d in conn.description]

    print(" | ".join(columns))
    for row in rows:
        print(" | ".join(str(v) for v in row))


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask the sample database in English.")
    parser.add_argument("question", help="e.g. 'total revenue per category'")
    args = parser.parse_args()
    answer(args.question)


if __name__ == "__main__":
    main()
