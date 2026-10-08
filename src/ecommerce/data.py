from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
METRICS = ['gross_revenue', 'refunds', 'net_revenue', 'assumed_cogs',
           'assumed_marketplace_fees', 'assumed_advertising', 'modeled_contribution_profit',
           'sold_units', 'returned_units']


def read_source(path):
    path = Path(path)
    if path.suffix == '.parquet':
        return pd.read_parquet(path)
    if path.suffix == '.xlsx':
        sheets = pd.read_excel(path, sheet_name=None, dtype={'Invoice': str, 'StockCode': str})
        return pd.concat([v.assign(source_sheet=k) for k, v in sheets.items()], ignore_index=True)
    return pd.read_csv(path, dtype={'Invoice': str, 'StockCode': str})


def clean(raw):
    aliases = {'invoice': 'invoice', 'invoiceno': 'invoice', 'stockcode': 'product_id',
               'description': 'description', 'quantity': 'quantity', 'invoicedate': 'date',
               'price': 'unit_price', 'unitprice': 'unit_price', 'customerid': 'customer_id', 'country': 'country'}
    df = raw.rename(columns={c: aliases.get(str(c).lower().replace(' ', ''), c) for c in raw}).copy()
    required = ['invoice', 'product_id', 'quantity', 'date', 'unit_price']
    if set(required) - set(df):
        raise ValueError(f'Missing columns: {sorted(set(required) - set(df))}')
    df['line_id'] = df['source_line_id'] if 'source_line_id' in df else np.arange(1, len(df) + 1)
    df['date'] = pd.to_datetime(df['date'], errors='coerce', format='mixed')
    for col in ['quantity', 'unit_price']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    for col in ['invoice', 'product_id']:
        df[col] = df[col].astype('string').str.strip()
    for col in ['description', 'country']:
        if col not in df:
            df[col] = 'Unknown'
        df[col] = df[col].fillna('Unknown').astype(str).str.strip()
    conditions = [df[required].isna().any(axis=1),
                  ~np.isfinite(df['quantity']) | ~np.isfinite(df['unit_price']),
                  df['invoice'].eq('') | df['product_id'].eq(''),
                  df['quantity'].eq(0), df['unit_price'].le(0),
                  df['invoice'].str.upper().str.startswith('C').fillna(False) & df['quantity'].gt(0)]
    df['review_reason'] = np.select([c.to_numpy(dtype=bool, na_value=False) for c in conditions],
        ['Missing required field', 'Non-finite number', 'Empty identifier', 'Zero quantity',
         'Nonpositive price', 'Positive-quantity cancellation'], default='')
    rejected = df.loc[df.review_reason.ne('')].copy()
    df = df.loc[df.review_reason.eq('')].copy()
    df['is_return'] = df.quantity.lt(0)
    # An explicit, conservative stock-code rule excludes shipping/adjustment codes.
    merchandise = df.product_id.str.fullmatch(r'\d{5}[A-Za-z]*').fillna(False)
    non_product = df.loc[~merchandise].copy()
    df = df.loc[merchandise].copy()
    df['month'] = df.date.dt.to_period('M').astype(str)
    df['week'] = df.date.dt.to_period('W-SUN').dt.start_time
    df['large_line_flag'] = df.quantity.abs().gt(5000) | df.unit_price.gt(100)
    return df, rejected, non_product


def resolve_sheet_overlap(raw):
    """Remove repeated source snapshots, preserving each sheet's line multiplicity.

    For a record present twice in one sheet and twice in another, keep two lines.
    For counts two and three, keep three. No within-sheet duplicates are removed.
    """
    raw = raw.copy()
    raw['source_line_id'] = np.arange(1, len(raw) + 1)
    if 'source_sheet' not in raw or raw.source_sheet.nunique() < 2:
        return raw, raw.iloc[:0].copy()
    keys = [c for c in raw if c not in ['source_sheet', 'source_line_id']]
    occurrence = raw.groupby(keys + ['source_sheet'], dropna=False, sort=False).cumcount()
    comparison = raw[keys].assign(occurrence=occurrence)
    duplicate = comparison.duplicated(keep='first')
    return raw.loc[~duplicate].copy(), raw.loc[duplicate].copy()


def calculate(df, assumptions):
    numeric_keys = ['unit_cost_share_of_product_reference_price',
        'marketplace_fee_share_of_positive_sales', 'advertising_share_of_positive_sales',
        'returned_inventory_cost_recovery_share', 'marketplace_fee_refund_share']
    for key in numeric_keys:
        value = assumptions[key]
        if not isinstance(value, (int, float)) or not np.isfinite(value) or not 0 <= value <= 1:
            raise ValueError(f'{key} must be finite and between 0 and 1')
    df = df.copy()
    ref = df.loc[~df.is_return].groupby('product_id').unit_price.median()
    df['reference_price'] = df.product_id.map(ref)
    df['assumed_unit_cost'] = df.reference_price * assumptions[numeric_keys[0]]
    uncosted = df.loc[df.assumed_unit_cost.isna()].copy()
    df = df.loc[df.assumed_unit_cost.notna()].copy()
    df['net_revenue'] = df.quantity * df.unit_price
    df['gross_revenue'] = df.net_revenue.clip(lower=0)
    df['refunds'] = -df.net_revenue.clip(upper=0)
    df['sold_units'] = df.quantity.clip(lower=0)
    df['returned_units'] = -df.quantity.clip(upper=0)
    recovery = np.where(df.is_return, assumptions[numeric_keys[3]], 1.0)
    df['assumed_cogs'] = df.quantity * df.assumed_unit_cost * recovery
    df['assumed_marketplace_fees'] = (df.gross_revenue - df.refunds * assumptions[numeric_keys[4]]) * assumptions[numeric_keys[1]]
    df['assumed_advertising'] = df.gross_revenue * assumptions[numeric_keys[2]]
    df['modeled_contribution_profit'] = df.net_revenue - df.assumed_cogs - df.assumed_marketplace_fees - df.assumed_advertising
    return df, uncosted


def aggregate(df, keys):
    result = df.groupby(keys, dropna=False)[METRICS].sum().reset_index()
    result['modeled_contribution_margin'] = result.modeled_contribution_profit / result.net_revenue.where(result.net_revenue > 0)
    result['return_unit_rate'] = result.returned_units / result.sold_units.where(result.sold_units > 0)
    return result


def complete_months(df):
    """Exclude incomplete boundary months rather than comparing partial totals."""
    start = df.date.min().normalize()
    end = df.date.max().normalize()
    months = sorted(df.month.unique())
    return [m for m in months if pd.Period(m).start_time >= start
            and pd.Period(m).end_time.normalize() <= end]


def product_table(df):
    table = aggregate(df, ['product_id'])
    descriptions = df.sort_values('date').groupby('product_id').description.last()
    table['description'] = table.product_id.map(descriptions)
    table['reference_price'] = table.product_id.map(df.groupby('product_id').reference_price.first())
    table['assumed_unit_cost'] = table.product_id.map(df.groupby('product_id').assumed_unit_cost.first())
    table['recommendation'] = np.select(
        [table.modeled_contribution_profit.lt(0), table.modeled_contribution_margin.lt(.1),
         table.modeled_contribution_margin.ge(.2) & table.net_revenue.ge(table.net_revenue.quantile(.75))],
        ['Review cost / returns', 'Review margin', 'Promotion candidate'], default='Monitor')
    return table.sort_values('modeled_contribution_profit', ascending=False)


def save_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, default=str, allow_nan=False))


def sha256(path):
    with open(path, 'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()
