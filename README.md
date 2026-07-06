# nl-to-sql

![CI](https://github.com/renatoaragon/nl-to-sql/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11-blue)
![Claude](https://img.shields.io/badge/Claude-Anthropic_SDK-a78bfa)
![DuckDB](https://img.shields.io/badge/DuckDB-embedded-FFF000)
![License](https://img.shields.io/badge/license-MIT-green)

Ask a database questions in plain English. This tool sends the schema and your
question to **Claude** (via the official Anthropic SDK), gets back a SQL query,
**guards it so only read-only `SELECT`s can run**, and executes it on a local
**DuckDB** sample database.

> Built to show a practical data + AI pattern done safely: the LLM proposes,
> a deterministic guard disposes. A generated `DROP TABLE` never reaches the
> database — the guard rejects anything that isn't a single `SELECT`.

## How it works

```
question ──▶ render schema ──▶ Claude (NL → SQL) ──▶ safety guard ──▶ DuckDB ──▶ rows
                                                          │
                                        rejects INSERT / UPDATE / DELETE / DROP,
                                        stacked statements, and non-SELECT queries
```

- `schema.py` — introspects DuckDB into a compact `table(col type, …)` string.
- `llm.py` — calls Claude with the schema and question; extracts the SQL.
- `guard.py` — the hard boundary: single statement, must start with
  `SELECT`/`WITH`, no data-modifying keywords. Raises `UnsafeQueryError` otherwise.
- `app.py` — wires it together into a CLI.

## Quickstart

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-...        # needed only for the live LLM step

PYTHONPATH=src python -m nl2sql.app "total revenue per category"
```

Example output:

```
SQL:
SELECT category, sum(amount) AS total FROM orders GROUP BY category

category | total
books | 47.49
electronics | 319.9
home | 60.0
```

## Safety guard

The guard is the point of the project. Whatever the model returns, only a
single read-only query runs:

```python
ensure_read_only("SELECT * FROM orders")          # ok
ensure_read_only("DROP TABLE orders")             # UnsafeQueryError
ensure_read_only("SELECT 1; DELETE FROM orders")  # UnsafeQueryError (stacked)
```

## Tests

```bash
pytest -q
```

The suite covers the guard (mutations, stacked statements, CTEs), prompt
building and SQL extraction, and schema rendering — **none of it calls the API**,
so CI runs green without an API key. The Claude call is isolated behind an
injectable client.

## Design notes

- **LLM proposes, code disposes** — the safety boundary is deterministic and
  unit-tested, never delegated to the model.
- **Injectable client** — `generate_sql(..., client=...)` lets tests and callers
  swap in a fake; the default uses the real Anthropic SDK.
- **Zero external setup** — the sample database is built in-memory, so the repo
  runs and tests out of the box.

## License

MIT — see [LICENSE](LICENSE).
