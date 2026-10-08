import os
import sqlite3
from pathlib import Path

FACT_COLUMNS = ['line_id', 'invoice', 'product_id', 'description', 'date', 'month', 'week', 'country',
                'quantity', 'unit_price', 'is_return', 'reference_price', 'assumed_unit_cost',
                'gross_revenue', 'refunds', 'net_revenue', 'sold_units', 'returned_units',
                'assumed_cogs', 'assumed_marketplace_fees', 'assumed_advertising', 'modeled_contribution_profit']
ROOT = Path(__file__).resolve().parents[2]


def write_sqlite(df, path):
    with sqlite3.connect(path) as connection:
        facts = df[FACT_COLUMNS].copy()
        facts['date'] = facts.date.astype(str)
        facts['week'] = facts.week.astype(str)
        facts['is_return'] = facts.is_return.astype(int)
        facts.to_sql('fact_sales', connection, if_exists='replace', index=False, chunksize=5000)
        connection.execute('CREATE UNIQUE INDEX idx_line ON fact_sales(line_id)')
        connection.execute('CREATE INDEX idx_product_month ON fact_sales(product_id, month)')
        connection.executescript((ROOT / 'sql/views.sql').read_text())
        total = connection.execute('SELECT SUM(modeled_contribution_profit) FROM fact_sales').fetchone()[0]
        if abs(total - df.modeled_contribution_profit.sum()) > .01:
            raise ValueError('SQL/Python reconciliation failed.')


def load_postgres(df, database_url=None):
    import psycopg
    from psycopg import sql
    url = database_url or os.getenv('DATABASE_URL')
    if not url:
        raise ValueError('Set DATABASE_URL to your PostgreSQL connection string.')
    with psycopg.connect(url) as connection:
        connection.execute((ROOT / 'sql/postgres_schema.sql').read_text())
        connection.execute('TRUNCATE retail_portfolio.fact_sales')
        columns = sql.SQL(', ').join(map(sql.Identifier, FACT_COLUMNS))
        command = sql.SQL('COPY retail_portfolio.fact_sales ({}) FROM STDIN').format(columns)
        facts = df[FACT_COLUMNS].copy()
        facts['is_return'] = facts.is_return.astype(bool)
        with connection.cursor().copy(command) as copy:
            for row in facts.itertuples(index=False, name=None):
                copy.write_row(tuple(value.to_pydatetime() if hasattr(value, 'to_pydatetime') else value for value in row))
        connection.execute('SET search_path TO retail_portfolio')
        connection.execute((ROOT / 'sql/views.sql').read_text())
        total = connection.execute('SELECT SUM(modeled_contribution_profit) FROM fact_sales').fetchone()[0]
        if abs(float(total) - df.modeled_contribution_profit.sum()) > .01:
            raise ValueError('PostgreSQL/Python reconciliation failed.')
