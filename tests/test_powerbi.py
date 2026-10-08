import json
import pandas as pd
import pytest
from ecommerce.data import ROOT


def test_powerbi_financial_exports_and_dimension_keys():
    base = ROOT / 'powerbi/data'
    facts = pd.read_csv(base / 'monthly_product_country.csv', dtype={'product_id': str})
    products = pd.read_csv(base / 'products.csv', dtype={'product_id': str})
    months = pd.read_csv(base / 'months.csv')
    actual = pd.read_csv(ROOT / 'reports/monthly_profitability.csv')
    assert not facts.duplicated(['month', 'product_id', 'country']).any()
    assert products.product_id.is_unique and months.month.is_unique
    assert set(facts.product_id).issubset(products.product_id)
    assert set(facts.month).issubset(months.month)
    for metric in facts.select_dtypes('number').columns:
        assert facts[metric].sum() == pytest.approx(actual[metric].sum(), abs=.01)
    assert months.loc[months.month.eq('2011-12-01'), 'complete_month'].item() == False


def test_powerbi_visual_fields_exist_and_do_not_mix_forecast_with_facts():
    root = ROOT / 'powerbi'
    model = json.loads((root / 'Retail.SemanticModel/model.bim').read_text())['model']
    tables = {t['name']: {c['name'] for c in t['columns']} | {m['name'] for m in t.get('measures', [])} for t in model['tables']}
    for path in (root / 'Retail.Report').rglob('visual.json'):
        value = json.loads(path.read_text())
        for state in value['visual']['query']['queryState'].values():
            for item in state['projections']:
                field = next(iter(item['field'].values()))
                entity = field['Expression']['SourceRef']['Entity']
                assert field['Property'] in tables[entity]
    assert all('Forecast' not in [r['fromTable'], r['toTable']] for r in model['relationships'])
    forecast_table = next(t for t in model['tables'] if t['name'] == 'Forecast')
    assert all('HASONEVALUE' in m['expression'] and '"ALL"' in m['expression'] for m in forecast_table['measures'])
