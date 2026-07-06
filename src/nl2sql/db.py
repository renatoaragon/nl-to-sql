"""Build an in-memory sample database so the tool runs with no external setup."""

import duckdb

SEED_SQL = """
create table customers (
    customer_id integer,
    name        varchar,
    country     varchar
);

insert into customers values
    (1, 'Ana',   'PT'),
    (2, 'Bruno', 'ES'),
    (3, 'Carla', 'FR'),
    (4, 'Diego', 'PT');

create table orders (
    order_id    integer,
    customer_id integer,
    order_date  date,
    category    varchar,
    amount      double
);

insert into orders values
    (1, 1, date '2025-01-05', 'books',       25.00),
    (2, 1, date '2025-01-09', 'electronics', 199.90),
    (3, 2, date '2025-01-11', 'books',       12.50),
    (4, 3, date '2025-02-02', 'home',        60.00),
    (5, 4, date '2025-02-14', 'electronics', 120.00),
    (6, 4, date '2025-02-20', 'books',        9.99);
"""


def build_sample_db() -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(":memory:")
    conn.execute(SEED_SQL)
    return conn
