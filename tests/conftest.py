from pathlib import Path
import sys
import json
import pytest
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ecommerce.data import ROOT, clean, calculate


@pytest.fixture
def assumptions():
    return json.loads((ROOT / 'assumptions.json').read_text())


@pytest.fixture
def facts(assumptions):
    raw = pd.DataFrame({'Invoice': ['1', 'C1', '2', '3'],
        'StockCode': ['12345', '12345', '12345', '23456'],
        'Quantity': [10, -2, 5, 4], 'Price': [10., 10., 10., 20.],
        'InvoiceDate': ['2011-01-01', '2011-01-15', '2011-02-01', '2011-02-15'],
        'Description': ['First', 'First', 'First', 'Second'], 'Country': ['UK'] * 4})
    cleaned, _, _ = clean(raw)
    return calculate(cleaned, assumptions)[0]
