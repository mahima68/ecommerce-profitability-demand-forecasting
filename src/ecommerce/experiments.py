"""Synthetic customer-level experiment; never attributed to UCI transactions."""
import math
import numpy as np
import pandas as pd
from scipy import stats


def required_sample(baseline=.05, absolute_mde=.01, power=.8, alpha=.05):
    if not 0 < baseline < 1 or not 0 < absolute_mde < 1 - baseline:
        raise ValueError('Baseline and detectable lift must imply a rate between 0 and 1.')
    if not .5 < power < 1 or not 0 < alpha < .5:
        raise ValueError('Power must be >50% and <100%; alpha must be >0 and <50%.')
    treatment = baseline + absolute_mde
    pooled = (baseline + treatment) / 2
    numerator = (stats.norm.ppf(1 - alpha / 2) * np.sqrt(2 * pooled * (1 - pooled))
        + stats.norm.ppf(power) * np.sqrt(baseline * (1 - baseline) + treatment * (1 - treatment))) ** 2
    return math.ceil(numerator / absolute_mde ** 2)


def simulate_experiment(n_per_arm=10000, seed=42):
    rng = np.random.default_rng(seed)
    rows = []
    # True generating parameters are simulation settings, not estimates of the retailer.
    for arm, conversion_rate, price in [('control', .05, 20.), ('treatment', .055, 21.)]:
        conversions = rng.binomial(1, conversion_rate, n_per_arm)
        quantities = rng.integers(1, 4, n_per_arm)
        returned = rng.binomial(1, .06, n_per_arm)
        revenue = conversions * quantities * price * (1 - returned)
        cogs = conversions * quantities * 11. * (1 - returned)
        fees = conversions * quantities * price * .15
        advertising = np.full(n_per_arm, .20)
        profit = revenue - cogs - fees - advertising
        rows.append(pd.DataFrame({'customer_id': [f'{arm}-{i}' for i in range(n_per_arm)],
            'arm': arm, 'converted': conversions, 'returned': conversions * returned,
            'revenue': revenue, 'contribution_profit': profit}))
    return pd.concat(rows, ignore_index=True)


def analyze_experiment(df, alpha=.05, minimum_profit_lift=.02):
    if not np.isfinite(alpha) or not 0 < alpha < .5:
        raise ValueError('Alpha must be finite and between 0 and 0.5.')
    if not np.isfinite(minimum_profit_lift) or minimum_profit_lift < 0:
        raise ValueError('Minimum profit lift must be finite and nonnegative.')
    if df.customer_id.isna().any() or df.arm.isna().any():
        raise ValueError('Every customer requires an identifier and assigned arm.')
    if df.customer_id.duplicated().any():
        raise ValueError('One row per randomized customer is required.')
    if set(df.arm.unique()) != {'control', 'treatment'}:
        raise ValueError('Expected control and treatment arms.')
    a = df[df.arm.eq('control')]
    b = df[df.arm.eq('treatment')]
    if min(len(a), len(b)) < 2:
        raise ValueError('At least two customers per arm are required.')
    if not df.converted.isin([0, 1]).all():
        raise ValueError('Converted must be binary.')
    for col in ['contribution_profit', 'revenue']:
        if not np.isfinite(df[col]).all():
            raise ValueError(f'{col} must be finite for every customer.')
    results = []
    # Primary metric: profit per assigned customer (intention to treat).
    for metric in ['contribution_profit', 'revenue']:
        control, treatment = a[metric].to_numpy(), b[metric].to_numpy()
        va, vb = control.var(ddof=1) / len(a), treatment.var(ddof=1) / len(b)
        se = np.sqrt(va + vb)
        delta = float(treatment.mean() - control.mean())
        if se > 0:
            degrees = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
            p = float(2 * stats.t.sf(abs(delta / se), degrees))
            critical = stats.t.ppf(1 - alpha / 2, degrees)
            lower, upper = delta - critical * se, delta + critical * se
        else:
            p, lower, upper = (1.0 if delta == 0 else 0.0), delta, delta
        results.append({'metric': metric, 'control_mean': float(control.mean()),
            'treatment_mean': float(treatment.mean()), 'difference': delta, 'p_value': p,
            'ci_lower': float(lower), 'ci_upper': float(upper),
            'role': 'primary' if metric == 'contribution_profit' else 'exploratory'})
    pa, pb = a.converted.mean(), b.converted.mean()
    pooled = df.converted.mean()
    se_null = np.sqrt(pooled * (1 - pooled) * (1 / len(a) + 1 / len(b)))
    p_conv = float(2 * stats.norm.sf(abs((pb - pa) / se_null))) if se_null else 1.0
    se_ci = np.sqrt(pa * (1 - pa) / len(a) + pb * (1 - pb) / len(b))
    width = stats.norm.ppf(1 - alpha / 2) * se_ci
    results.append({'metric': 'conversion', 'control_mean': float(pa), 'treatment_mean': float(pb),
        'difference': float(pb - pa), 'p_value': p_conv, 'ci_lower': max(-1., float(pb - pa - width)),
        'ci_upper': min(1., float(pb - pa + width)), 'role': 'exploratory'})
    srm = float(stats.chisquare([len(a), len(b)]).pvalue)
    primary = results[0]
    decision = ('Investigate sample ratio mismatch' if srm < .01 else
                'Meets simulated primary-metric rule' if primary['ci_lower'] > minimum_profit_lift else
                'Evidence of harm' if primary['ci_upper'] < 0 else
                'Inconclusive for rollout')
    return {'label': 'SIMULATED EXPERIMENT — not a real UCI A/B test', 'seed': 42,
            'control_n': len(a), 'treatment_n': len(b), 'srm_p_value': srm,
            'alpha': alpha, 'minimum_profit_lift': minimum_profit_lift,
            'decision': decision, 'metrics': results}
