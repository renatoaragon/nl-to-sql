"""Safety guard: only allow a single read-only SELECT statement.

The LLM can suggest anything; this module is the hard boundary that prevents a
generated query from mutating or dropping data. It runs before any query
reaches the database.

The guard first **normalizes** the query with a minimal lexer — blanking out
string literals, quoted identifiers and comments — and only then scans for
forbidden constructs. Scanning raw text gets both directions wrong: an innocent
``SELECT 'drop'`` trips the keyword check (false positive), while scanning is
the only thing standing between the database and a real payload, so it cannot
afford blind spots either.
"""

import re

FORBIDDEN_KEYWORDS = {
    "insert", "update", "delete", "drop", "alter", "create", "truncate",
    "replace", "merge", "grant", "revoke", "attach", "detach", "copy",
    "pragma", "install", "load", "call", "export", "import",
}

# DuckDB table functions that touch the filesystem. Read-only in SQL terms,
# but they read arbitrary paths — out of bounds for a query endpoint.
FORBIDDEN_FUNCTIONS = {
    "read_csv", "read_csv_auto", "read_parquet", "read_json", "read_json_auto",
    "read_ndjson", "read_ndjson_auto", "read_text", "read_blob", "glob",
}


class UnsafeQueryError(Exception):
    """Raised when a query is not a single read-only SELECT."""


def _normalize(sql: str) -> str:
    """Blank out string literals, quoted identifiers and comments.

    A character-level scan tracking four states: single-quoted strings (with
    ``''`` escaping), double-quoted identifiers, ``--`` line comments and
    ``/* */`` block comments. What remains is bare SQL structure, safe to scan
    for keywords without being fooled by payloads hidden in comments or
    tripped by innocent words inside literals.
    """
    out = []
    i, n = 0, len(sql)
    state = None  # None | "str" | "ident" | "line" | "block"
    while i < n:
        ch = sql[i]
        nxt = sql[i + 1] if i + 1 < n else ""
        if state is None:
            if ch == "'":
                state = "str"
            elif ch == '"':
                state = "ident"
            elif ch == "-" and nxt == "-":
                state = "line"
                i += 1
            elif ch == "/" and nxt == "*":
                state = "block"
                i += 1
            else:
                out.append(ch)
        elif state == "str":
            if ch == "'" and nxt == "'":
                i += 1  # escaped quote, still inside the literal
            elif ch == "'":
                state = None
                out.append("''")  # placeholder keeps surrounding tokens apart
        elif state == "ident":
            if ch == '"':
                state = None
                out.append('""')
        elif state == "line":
            if ch == "\n":
                state = None
                out.append("\n")
        elif state == "block":
            if ch == "*" and nxt == "/":
                state = None
                i += 1
        i += 1

    if state in ("str", "ident"):
        raise UnsafeQueryError("Unterminated string literal or quoted identifier.")
    return "".join(out)


def ensure_read_only(sql: str) -> str:
    """Return the sanitized query, or raise UnsafeQueryError.

    Rules (checked on the normalized text, so literals and comments can
    neither hide an attack nor cause a false rejection):
      - exactly one statement (no stacked queries)
      - must start with SELECT or WITH
      - must not contain any data-modifying keyword
      - must not call filesystem table functions (read_csv, glob, ...)
    """
    if "$$" in sql:
        # Dollar-quoted strings would need their own lexer state; queries over
        # this schema never need them, so reject rather than guess.
        raise UnsafeQueryError("Dollar-quoted strings are not supported.")

    normalized = _normalize(sql).strip().rstrip(";").strip()
    if not normalized:
        raise UnsafeQueryError("Query is empty (or only comments).")

    if ";" in normalized:
        raise UnsafeQueryError("Multiple statements are not allowed.")

    first_word = normalized.split(None, 1)[0].lower()
    if first_word not in ("select", "with"):
        raise UnsafeQueryError(f"Only SELECT queries are allowed, got '{first_word}'.")

    lowered = normalized.lower()
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", lowered):
            raise UnsafeQueryError(f"Forbidden keyword '{keyword}' in query.")

    for function in FORBIDDEN_FUNCTIONS:
        if re.search(rf"\b{function}\s*\(", lowered):
            raise UnsafeQueryError(
                f"Function '{function}' reads from the filesystem and is not allowed."
            )

    return sql.strip().rstrip(";").strip()


DEFAULT_MAX_ROWS = 1000

_TRAILING_LIMIT = re.compile(r"\blimit\s+\d+\s*(offset\s+\d+\s*)?$")


def enforce_limit(sql: str, max_rows: int = DEFAULT_MAX_ROWS) -> str:
    """Cap the result size: append a LIMIT when the query has none on top.

    Asked "show me the orders", the model happily generates an unbounded
    ``SELECT *`` — correct SQL, and a memory bomb on a real table. A query that
    already ends in its own top-level LIMIT is respected (the model expressed
    an intent; a limit inside a subquery does not bound the outer query, so it
    doesn't count). The check runs on the normalized text, the appended clause
    on its own line so a trailing ``--`` comment can't swallow it.
    """
    normalized = _normalize(sql).strip().rstrip(";").strip().lower()
    if _TRAILING_LIMIT.search(normalized):
        return sql
    return f"{sql}\nLIMIT {max_rows}"
