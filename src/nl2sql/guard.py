"""Safety guard: only allow a single read-only SELECT statement.

The LLM can suggest anything; this module is the hard boundary that prevents a
generated query from mutating or dropping data. It runs before any query
reaches the database.
"""

import re

FORBIDDEN_KEYWORDS = {
    "insert", "update", "delete", "drop", "alter", "create", "truncate",
    "replace", "merge", "grant", "revoke", "attach", "detach", "copy",
    "pragma", "install", "load", "call", "export", "import",
}


class UnsafeQueryError(Exception):
    """Raised when a query is not a single read-only SELECT."""


def ensure_read_only(sql: str) -> str:
    """Return the sanitized query, or raise UnsafeQueryError.

    Rules:
      - exactly one statement (no stacked queries)
      - must start with SELECT or WITH
      - must not contain any data-modifying keyword
    """
    stripped = sql.strip().rstrip(";").strip()
    if not stripped:
        raise UnsafeQueryError("Empty query.")

    if ";" in stripped:
        raise UnsafeQueryError("Multiple statements are not allowed.")

    first_word = stripped.split(None, 1)[0].lower()
    if first_word not in ("select", "with"):
        raise UnsafeQueryError(f"Only SELECT queries are allowed, got '{first_word}'.")

    lowered = stripped.lower()
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", lowered):
            raise UnsafeQueryError(f"Forbidden keyword '{keyword}' in query.")

    return stripped
