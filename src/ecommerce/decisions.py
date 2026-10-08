import numpy as np
import pandas as pd
from .data import METRICS, aggregate, product_table


def profit_bridge(df, month, previous=None):
    current_period = pd.Period(month, 'M')
    previous = previous or str(current_period - 1)
    totals = aggregate(df, ['month']).set_index('month')
    if month not in totals.index or previous not in totals.index:
        raise ValueError('Both comparison months must have data.')
    before, after = totals.loc[previous], totals.loc[month]
    drivers = {'Net revenue': after.net_revenue - before.net_revenue,
               'COGS effect': before.assumed_cogs - after.assumed_cogs,
               'Marketplace fee effect': before.assumed_marketplace_fees - after.assumed_marketplace_fees,
               'Advertising effect': before.assumed_advertising - after.assumed_advertising}
    b = aggregate(df[df.month.eq(previous)], ['product_id']).set_index('product_id')
    a = aggregate(df[df.month.eq(month)], ['product_id']).set_index('product_id')
    ids = a.index.union(b.index)
    product_changes = pd.DataFrame({'product_id': ids,
        'profit_change': a.modeled_contribution_profit.reindex(ids, fill_value=0).to_numpy()
                         - b.modeled_contribution_profit.reindex(ids, fill_value=0).to_numpy()})
    return {'month': month, 'previous': previous,
        'previous_profit': float(before.modeled_contribution_profit),
        'current_profit': float(after.modeled_contribution_profit),
        'change': float(after.modeled_contribution_profit - before.modeled_contribution_profit),
        'drivers': {k: float(v) for k, v in drivers.items()},
        'product_changes': product_changes.sort_values('profit_change')}


def simulate(df, price_change=0.05, elasticity=-1.0, advertising_change=0.0):
    """Constant-elasticity scenario, not an estimated causal demand response."""
    if not -0.3 <= price_change <= 0.3 or not -3 <= elasticity <= 0:
        raise ValueError('Price change must be within ±30%; elasticity within -3 to 0.')
    if not -1 <= advertising_change <= 1:
        raise ValueError('Advertising change must be within -100% to +100%.')
    if df.empty:
        raise ValueError('No transactions in this selection.')
    ratio = 1 + price_change
    demand_ratio = ratio ** elasticity
    # Preserve the observed return proportion and fee-refund policy. Advertising is
    # an independently changed spend budget, with no assumed acquisition effect.
    baseline = {k: float(df[k].sum()) for k in METRICS}
    scenario = baseline.copy()
    for key in ['gross_revenue', 'refunds', 'net_revenue', 'assumed_marketplace_fees']:
        scenario[key] *= ratio * demand_ratio
    for key in ['sold_units', 'returned_units', 'assumed_cogs']:
        scenario[key] *= demand_ratio
    scenario['assumed_advertising'] *= 1 + advertising_change
    scenario['modeled_contribution_profit'] = (scenario['net_revenue'] - scenario['assumed_cogs']
        - scenario['assumed_marketplace_fees'] - scenario['assumed_advertising'])
    for values in [baseline, scenario]:
        values['modeled_contribution_margin'] = (values['modeled_contribution_profit'] / values['net_revenue']
                                                if values['net_revenue'] > 0 else None)
    return {'baseline': baseline, 'scenario': scenario,
        'profit_change': scenario['modeled_contribution_profit'] - baseline['modeled_contribution_profit'],
        'demand_change': demand_ratio - 1,
        'assumptions': {'price_change': price_change, 'elasticity': elasticity,
                        'advertising_change': advertising_change}}


def product_momentum(df, month):
    previous = str(pd.Period(month, 'M') - 1)
    a = aggregate(df[df.month.eq(month)], ['product_id']).set_index('product_id')
    b = aggregate(df[df.month.eq(previous)], ['product_id']).set_index('product_id')
    result = a[['net_revenue', 'modeled_contribution_profit', 'sold_units']].join(
        b[['sold_units']].rename(columns={'sold_units': 'previous_sold_units'}), how='outer').fillna(0)
    result['unit_change'] = result.sold_units - result.previous_sold_units
    result['unit_change_pct'] = result.unit_change / result.previous_sold_units.where(result.previous_sold_units > 0)
    names = product_table(df).set_index('product_id').description
    result['description'] = result.index.map(names)
    return result.reset_index().sort_values('unit_change')
