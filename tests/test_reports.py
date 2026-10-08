import json
import sqlite3
import pandas as pd
import pytest
from ecommerce.data import ROOT, METRICS


def test_executed_reports_reconcile():
    quality = json.loads((ROOT / 'reports/quality_report.json').read_text())
    partition = sum(quality[k] for k in ['cross_sheet_overlap_removed', 'rejected_rows', 'non_product_rows', 'uncosted_rows', 'modeled_rows'])
    assert quality['input_rows'] == partition
    assert quality['cross_sheet_overlap_removed'] == 22523
    assert quality['modeled_rows'] == 1032897
    assert quality['accepted_merchandise_net_revenue'] == pytest.approx(quality['modeled_net_revenue'] + quality['uncosted_net_revenue'])
    products = pd.read_csv(ROOT / 'reports/product_profitability.csv')
    monthly = pd.read_csv(ROOT / 'reports/monthly_profitability.csv')
    countries = pd.read_csv(ROOT / 'reports/country_profitability.csv')
    for metric in METRICS:
        assert products[metric].sum() == pytest.approx(monthly[metric].sum())
        assert countries[metric].sum() == pytest.approx(monthly[metric].sum())
    assert products.net_revenue.sum() == pytest.approx(quality['modeled_net_revenue'])


def test_forecast_periods_and_selected_models():
    future = pd.read_csv(ROOT / 'reports/forecast_future.csv')
    scores = pd.read_csv(ROOT / 'reports/forecast_scores.csv')
    backtests = pd.read_csv(ROOT / 'reports/forecast_backtests.csv')
    assert (pd.to_datetime(future.week) > pd.Timestamp('2011-12-04')).all()
    assert (future.lower_units <= future.predicted_units).all()
    assert (future.upper_units >= future.predicted_units).all()
    for identifier, f in future.groupby('series_id'):
        validation = scores[scores.series_id.eq(identifier) & scores.split.eq('validation')]
        assert f.model.iloc[0] == validation.sort_values('mae').iloc[0].model
    assert (pd.to_datetime(backtests.week) > pd.to_datetime(backtests.origin)).all()
