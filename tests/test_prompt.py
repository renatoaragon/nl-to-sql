from nl2sql.prompt import build_prompt, extract_sql


def test_build_prompt_includes_question_and_schema():
    prompt = build_prompt("how many orders?", "orders(order_id integer)")
    assert "how many orders?" in prompt
    assert "orders(order_id integer)" in prompt


def test_extract_sql_from_fenced_block():
    text = "Here you go:\n```sql\nSELECT count(*) FROM orders\n```\nHope it helps."
    assert extract_sql(text) == "SELECT count(*) FROM orders"


def test_extract_sql_without_fence():
    assert extract_sql("SELECT 1") == "SELECT 1"


def test_extract_sql_generic_fence():
    text = "```\nSELECT 1\n```"
    assert extract_sql(text) == "SELECT 1"
