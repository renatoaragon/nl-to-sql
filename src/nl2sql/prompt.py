"""Prompt construction and SQL extraction — pure functions, no network."""

import re

SYSTEM = (
    "You are a careful data analyst. You translate a natural-language question "
    "into a single read-only DuckDB SQL SELECT query. "
    "Rules: return only the SQL, wrapped in a ```sql code block. "
    "Never write INSERT, UPDATE, DELETE, DROP or any statement that changes data. "
    "Use only the tables and columns provided in the schema."
)


def build_prompt(question: str, schema_text: str) -> str:
    return (
        f"Database schema:\n{schema_text}\n\n"
        f"Question: {question}\n\n"
        "Write one DuckDB SELECT query that answers it."
    )


def extract_sql(text: str) -> str:
    """Pull the SQL out of a model response, tolerating fenced code blocks."""
    fenced = re.search(r"```(?:sql)?\s*(.+?)```", text, re.DOTALL | re.IGNORECASE)
    candidate = fenced.group(1) if fenced else text
    return candidate.strip()
