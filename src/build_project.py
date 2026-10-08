import argparse
from pathlib import Path
import json
import sys
import pandas as pd
from ecommerce.data import ROOT, read_source, clean, calculate, aggregate, product_table, complete_months, save_json, sha256, resolve_sheet_overlap
from ecommerce.decisions import product_momentum
from ecommerce.forecast import forecast_all
from ecommerce.experiments import simulate_experiment, analyze_experiment, required_sample
from ecommerce.database import write_sqlite, load_postgres
from ecommerce.reporting import write_case_study


def build(source, postgres=False):
    reports, processed = ROOT / 'reports', ROOT / 'data/processed'
    reports.mkdir(exist_ok=True, parents=True)
    processed.mkdir(exist_ok=True, parents=True)
    print('Reading transaction data...', flush=True)
    raw = read_source(source)
    cache = raw.copy()
    for col in cache.select_dtypes(include=['object']).columns:
        cache[col] = cache[col].astype('string')
    cache_path = ROOT / 'data/raw/source_cache.parquet'
    if Path(source).resolve() != cache_path.resolve():
        cache.to_parquet(cache_path, index=False)
    resolved_source, overlap = resolve_sheet_overlap(raw)
    data, rejected, non_product = clean(resolved_source)
    assumptions = json.loads((ROOT / 'assumptions.json').read_text())
    modeled, uncosted = calculate(data, assumptions)
    modeled.to_parquet(processed / 'transactions.parquet', index=False)
    for name, table in [('rejected_rows', rejected), ('non_product_rows', non_product), ('uncosted_rows', uncosted), ('cross_sheet_overlap', overlap)]:
        table.to_csv(reports / f'{name}.csv', index=False)
    products = product_table(modeled)
    products.to_csv(reports / 'product_profitability.csv', index=False)
    months = complete_months(modeled)
    monthly = aggregate(modeled, ['month'])
    monthly['complete_month'] = monthly.month.isin(months)
    monthly.to_csv(reports / 'monthly_profitability.csv', index=False)
    aggregate(modeled, ['country']).to_csv(reports / 'country_profitability.csv', index=False)
    aggregate(modeled, ['product_id', 'month']).to_parquet(processed / 'product_month.parquet', index=False)
    product_momentum(modeled, months[-1]).to_csv(reports / 'product_momentum.csv', index=False)
    quality = {'input_rows': len(raw), 'rejected_rows': len(rejected), 'non_product_rows': len(non_product),
        'merchandise_rows': len(data), 'uncosted_rows': len(uncosted), 'modeled_rows': len(modeled),
        'cross_sheet_overlap_removed': len(overlap),
        'partition_reconciles': len(raw) == len(overlap) + len(rejected) + len(non_product) + len(uncosted) + len(modeled),
        'exact_duplicate_rows_retained': int(resolved_source.drop(columns=['source_sheet', 'source_line_id'], errors='ignore').duplicated().sum()),
        'missing_customer_ids_retained': int(modeled.get('customer_id', pd.Series(dtype=float)).isna().sum()),
        'large_lines_retained': int(modeled.large_line_flag.sum()),
        'date_start': str(modeled.date.min()), 'date_end': str(modeled.date.max()),
        'complete_months': months, 'rejection_reasons': rejected.review_reason.value_counts().to_dict(),
        'accepted_merchandise_net_revenue': float((data.quantity * data.unit_price).sum()),
        'modeled_net_revenue': float(modeled.net_revenue.sum()),
        'uncosted_net_revenue': float((uncosted.quantity * uncosted.unit_price).sum()),
        'non_product_net_revenue': float((non_product.quantity * non_product.unit_price).sum()),
        'assumptions': assumptions}
    save_json(reports / 'quality_report.json', quality)
    print(f'Cleaned {len(raw):,} source rows; forecasting...', flush=True)
    forecast = forecast_all(modeled)
    for key in ['future', 'scores', 'backtests', 'history']:
        forecast[key].to_csv(reports / f'forecast_{key}.csv', index=False)
    save_json(reports / 'forecast_skipped.json', forecast['skipped'])
    experiment = simulate_experiment()
    experiment.to_csv(reports / 'simulated_experiment.csv', index=False)
    result = analyze_experiment(experiment)
    result['conversion_sample_size_per_arm'] = required_sample()
    save_json(reports / 'experiment_results.json', result)
    print('Building SQL database and case study...', flush=True)
    write_sqlite(modeled, processed / 'retail.sqlite')
    if postgres:
        load_postgres(modeled)
    write_case_study(modeled, monthly, products, forecast, quality, result, assumptions)
    manifest = {'source_file': Path(source).name,
        'source_sha256': sha256(source), 'assumptions_sha256': sha256(ROOT / 'assumptions.json'),
        'python_version': sys.version.split()[0], 'pandas_version': pd.__version__,
        'snapshot': 'Historical UCI retail case study; not current sales',
        'source_url': 'https://archive.ics.uci.edu/dataset/502/online+retail+ii',
        'source_code_sha256': {str(f.relative_to(ROOT)): sha256(f) for f in sorted(ROOT.rglob('*.py'))
                              if '__pycache__' not in str(f) and '.venv' not in f.parts},
        'sqlite_verified': True, 'postgres_verified': postgres}
    workbook = ROOT / 'data/raw/online_retail_II.xlsx'
    if workbook.exists():
        manifest['original_workbook_sha256'] = sha256(workbook)
    save_json(reports / 'build_manifest.json', manifest)
    print('Complete. Launch with: python -m streamlit run app.py', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=ROOT / 'data/raw/online_retail_II.xlsx')
    parser.add_argument('--postgres', action='store_true')
    args = parser.parse_args()
    build(args.input, args.postgres)
