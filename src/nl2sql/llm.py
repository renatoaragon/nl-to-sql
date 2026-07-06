"""Claude call that turns a question + schema into SQL.

The client is injected so tests and callers can supply a fake; the real path
uses the official Anthropic SDK.
"""

from anthropic import Anthropic

from nl2sql.prompt import SYSTEM, build_prompt, extract_sql

DEFAULT_MODEL = "claude-opus-4-8"


def generate_sql(
    question: str,
    schema_text: str,
    *,
    client: Anthropic | None = None,
    model: str = DEFAULT_MODEL,
) -> str:
    """Ask Claude for a SQL query and return the extracted statement."""
    client = client or Anthropic()

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=SYSTEM,
        messages=[{"role": "user", "content": build_prompt(question, schema_text)}],
    )

    text = "".join(block.text for block in response.content if block.type == "text")
    return extract_sql(text)
