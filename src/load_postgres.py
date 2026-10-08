import argparse
import getpass
import json
import os
from datetime import datetime, timezone
from urllib.parse import quote
import pandas as pd
import psycopg
from ecommerce.data import ROOT
from ecommerce.database import load_postgres

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--local', action='store_true', help='Use the default initialized Postgres.app server.')
    args = parser.parse_args()
    url = ('postgresql://127.0.0.1:5432/' + quote(getpass.getuser(), safe='')) if args.local else os.getenv('DATABASE_URL')
    if not url:
        raise SystemExit('Set DATABASE_URL securely, or use --local for Postgres.app.')
    data = pd.read_parquet(ROOT / 'data/processed/transactions.parquet')
    load_postgres(data, url)
    metrics = ['net_revenue', 'modeled_contribution_profit', 'gross_revenue', 'refunds',
               'assumed_cogs', 'assumed_marketplace_fees', 'assumed_advertising', 'sold_units', 'returned_units']
    with psycopg.connect(url, connect_timeout=10) as conn:
        conn.execute('SET search_path TO retail_portfolio')
        version = conn.execute('SHOW server_version').fetchone()[0]
        count = conn.execute('SELECT COUNT(*) FROM fact_sales').fetchone()[0]
        if count != len(data):
            raise ValueError('PostgreSQL row count does not reconcile.')
        for metric in metrics:
            total = conn.execute(f'SELECT SUM({metric}) FROM fact_sales').fetchone()[0]
            if abs(float(total) - data[metric].sum()) > .01:
                raise ValueError(f'PostgreSQL total does not reconcile: {metric}')
        for key, view, checks in [('month', 'monthly_profitability', metrics[:7]),
                                  ('product_id', 'product_profitability', ['net_revenue', 'modeled_contribution_profit', 'sold_units', 'returned_units'])]:
            # Identifiers come exclusively from the fixed lists above.
            rows = conn.execute(f'SELECT {key}, ' + ', '.join(checks) + f' FROM {view}').fetchall()
            actual = pd.DataFrame(rows, columns=[key] + checks).set_index(key).sort_index()
            expected = data.groupby(key)[checks].sum().sort_index()
            # Parquet StringDtype and psycopg object strings have equivalent values
            # but Index.equals can reject their different backing dtypes.
            actual.index = actual.index.astype('object')
            expected.index = expected.index.astype('object')
            if not actual.index.equals(expected.index) or (actual.astype(float) - expected).abs().to_numpy().max() > .01:
                raise ValueError(f'PostgreSQL view does not reconcile: {view}')
    result = {'verified_at_utc': datetime.now(timezone.utc).isoformat(), 'postgres_version': version,
              'rows': count, 'totals_reconciled': metrics, 'monthly_view_verified': True, 'product_view_verified': True}
    (ROOT / 'reports/postgres_verification.json').write_text(json.dumps(result, indent=2))
    manifest_path = ROOT / 'reports/build_manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['postgres_verified'] = True
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f'PostgreSQL {version}: {count:,} rows loaded; financial totals and both SQL views verified.')
