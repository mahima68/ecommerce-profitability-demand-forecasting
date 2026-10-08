from .data import ROOT
from .decisions import profit_bridge, simulate


def write_case_study(df, monthly, products, forecast, quality, experiment, assumptions):
    complete = monthly[monthly.complete_month]
    latest = complete.iloc[-1]
    bridge = profit_bridge(df, latest.month)
    top = products.iloc[0]
    future = forecast['future'][forecast['future'].series_id.eq('ALL')]
    scores = forecast['scores'][forecast['scores'].series_id.eq('ALL') & forecast['scores'].selected]
    test = scores[scores.split.eq('test')].iloc[0]
    validation = scores[scores.split.eq('validation')].iloc[0]
    scenarios = [simulate(df[df.month.eq(latest.month)], .05, e) for e in [0., -1., -2.]]
    falling = complete.copy()
    falling['change'] = falling.modeled_contribution_profit.diff()
    worst = falling.loc[falling.change.idxmin()]
    decline = profit_bridge(df, worst.month)
    text = f'''# E-commerce Profitability & Forecasting System

## Business problem
Revenue alone does not identify profitable products. This historical retail case study combines observed sales with transparent cost scenarios, forecasts, and a simulated price experiment to support product and pricing decisions.

## Data and accounting scope
The UCI Online Retail II workbook contains {quality['input_rows']:,} rows across two sheets. The December 2010 sheets overlap: {quality['cross_sheet_overlap_removed']:,} repeated snapshot lines are removed using exact record matches and occurrence ranks, preserving each sheet's within-record multiplicity. The pipeline models {quality['modeled_rows']:,} merchandise lines after separately reporting {quality['rejected_rows']:,} invalid lines, {quality['non_product_rows']:,} non-merchandise lines, and {quality['uncosted_rows']:,} return-only lines without a reference cost. The row partition reconciles. Remaining duplicate-looking lines are retained and counted ({quality['exact_duplicate_rows_retained']:,}) because there is no invoice-line identifier.

Observed modeled-scope net revenue is £{df.net_revenue.sum():,.2f}. Modeled contribution profit is £{df.modeled_contribution_profit.sum():,.2f}. Costs are synthetic: unit cost is {assumptions['unit_cost_share_of_product_reference_price']:.0%} of each product's median positive-sale price, marketplace fees are {assumptions['marketplace_fee_share_of_positive_sales']:.0%} of positive sales (less the configured fee refund), and advertising allocation is {assumptions['advertising_share_of_positive_sales']:.0%} of positive sales. Returned inventory recovers {assumptions['returned_inventory_cost_recovery_share']:.0%} of assumed cost. These assumptions do not describe actual retailer costs.

## Findings from the executed pipeline
- Highest modeled-profit product: {top.product_id} ({top.description}), with £{top.net_revenue:,.2f} net revenue and £{top.modeled_contribution_profit:,.2f} modeled profit over the dataset.
- Latest complete calendar month: {latest.month}, with £{latest.net_revenue:,.2f} net revenue, £{latest.modeled_contribution_profit:,.2f} modeled profit, and {latest.modeled_contribution_margin:.1%} modeled margin.
- Its modeled profit changed by £{bridge['change']:,.2f} versus {bridge['previous']}. The bridge reconciles revenue, COGS, marketplace fee, and advertising changes. It does not prove causes.
- Largest month-over-month modeled-profit decline among complete months: {worst.month}, at £{decline['change']:,.2f}. The net-revenue effect was £{decline['drivers']['Net revenue']:,.2f}. Seasonal demand and missing inventory/exposure data limit causal explanations.

## Forecast evaluation
Three candidates are compared: a recent four-week mean, a 52-week seasonal naive forecast, and ridge regression with Fourier seasonality, trend, and lag features. Six rolling four-week origins are used. The first four origins select the model by MAE; the last two form an eight-week test with the selection fixed.

Selected aggregate model: **{future.model.iloc[0]}**. Validation MAE: {validation.mae:,.0f} units. Test MAE: {test.mae:,.0f} units. Test WAPE: {test.wape:.1%}. Each origin trains only on prior observations. The model is finally refitted on all complete weeks through {future.as_of.iloc[0]}.

The recent four-week mean baseline has test WAPE {forecast['scores'].loc[forecast['scores'].series_id.eq('ALL') & forecast['scores'].model.eq('Recent 4-week mean') & forecast['scores'].split.eq('test'), 'wape'].iloc[0]:.1%}. Selection is based on validation only; a more complex model is not guaranteed to outperform the baseline on new periods.

The next four weeks forecast {future.predicted_units.sum():,.0f} sold units and £{future.expected_gross_revenue.sum():,.2f} gross revenue at the trailing 13-week average selling price. This is a historical demonstration, not a forecast for 2026. Ranges use absolute validation errors with only four observations per horizon; coverage is not guaranteed. Returns, stock constraints, promotion effects, and net profit are not forecast. Top-product forecasts are independent and do not reconcile to the aggregate.

## Pricing sensitivity
For the latest complete month, a +5% price scenario changes modeled profit by £{scenarios[0]['profit_change']:,.2f} with elasticity 0, £{scenarios[1]['profit_change']:,.2f} with elasticity -1, and £{scenarios[2]['profit_change']:,.2f} with elasticity -2. COGS per unit stays fixed, return proportions stay fixed, and advertising is separately adjustable. Elasticity is an assumption, not an estimate from observational data. Use the sensitivity to design a real test.

## Experiment demonstration
A seeded synthetic customer-level experiment assigns {experiment['control_n']:,} customers to control and {experiment['treatment_n']:,} to treatment. The primary metric is contribution profit per assigned customer, analyzed with a Welch interval/test. Revenue and conversion are exploratory. Simulated decision: **{experiment['decision']}**. No real experiment is claimed.

## Practical recommendations
1. Validate actual supplier costs, fees, fulfillment costs, and ad spend before acting on modeled rankings.
2. Investigate low-margin and return-heavy products, then test one price change with customer-level randomization and a prespecified profit metric.
3. Use the baseline comparison and test errors when choosing a forecast; investigate availability and holiday effects before buying inventory from it.

## Implementation
Python/Pandas own calculations. SQLite stores the portable demo. PostgreSQL schema, bulk loading, and matching views support optional database deployment. Streamlit presents product, country, pricing, forecasting, experimentation, and analysis-assistant views. The optional OpenAI planner selects an allowlisted Python function; rendered financial numbers come from deterministic calculations.

## Source
Chen, D. (2012). Online Retail II [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5CG6D. CC BY 4.0. Source page: https://archive.ics.uci.edu/dataset/502/online+retail+ii
'''
    (ROOT / 'docs/CASE_STUDY.md').write_text(text)
