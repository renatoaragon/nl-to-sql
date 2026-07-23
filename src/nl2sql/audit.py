"""An audit trail of what the model proposed and what the guard decided.

When an LLM writes SQL that you then execute, the one record worth keeping is
exactly that: the question asked, the SQL generated, and whether the guard let
it run or blocked it. A blocked query is a security-relevant event, not just an
error, so both outcomes are recorded.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

OUTCOME_EXECUTED = "executed"
OUTCOME_REJECTED = "rejected"


def record_query(
    path: str, question: str, sql: str, outcome: str, detail: str = ""
) -> dict:
    """Append one JSONL audit record and return it.

    ``sql`` is whatever the model produced (for a rejection) or the sanitized
    query that ran (for an execution); ``detail`` carries the guard's reason on
    a rejection.
    """
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "question": question,
        "sql": sql,
        "outcome": outcome,
        "detail": detail,
    }
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry
