from pathlib import Path
import json
import os
import sys
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))
from ecommerce.data import aggregate, product_table, complete_months
from ecommerce.decisions import profit_bridge, simulate, product_momentum
from ecommerce.experiments import required_sample, analyze_experiment
from ecommerce.analyst import answer
from ecommerce.private_settings import load_private_settings

load_private_settings()

st.set_page_config(page_title='Retail Decisions', page_icon='◈', layout='wide')
st.markdown('''<style>
.stApp {background:#f6f8f5; color:#182d27;}
[data-testid="stSidebar"] {background:#e8eee8;}
[data-testid="stSidebar"] h1 {font-size:1.5rem;}
h1,h2,h3 {letter-spacing:-.035em; color:#173d32;}
h1 {font-size:2.65rem!important; font-weight:650!important;}
[data-testid="stMetric"] {background:white;border:1px solid #dfe7df;border-radius:12px;padding:18px;}
[data-testid="stMetricLabel"] {font-size:.85rem;color:#50685e;}
[data-testid="stMetricValue"] {font-size:1.9rem;color:#173d32;}
.eyebrow {font-size:.76rem;letter-spacing:.14em;color:#597263;font-weight:650;margin-bottom:8px;}
.context {font-size:1rem;color:#52675c;max-width:850px;line-height:1.6;margin-bottom:22px;}
.stMainBlockContainer {padding-top:2.4rem;max-width:1450px;}
</style>''', unsafe_allow_html=True)
px.defaults.template = 'plotly_white'
px.defaults.color_discrete_sequence = ['#27765e', '#b49554', '#6698a1', '#a75b50', '#82947c']


@st.cache_data
def load_data(build_version):
    df = pd.read_parquet(ROOT / 'data/processed/transactions.parquet')
    tables = {name: pd.read_csv(ROOT / f'reports/{name}.csv', dtype={'series_id': str})
              for name in ['forecast_future', 'forecast_scores', 'forecast_backtests', 'forecast_history']}
    quality = json.loads((ROOT / 'reports/quality_report.json').read_text())
    experiment = pd.read_csv(ROOT / 'reports/simulated_experiment.csv')
    return df, tables, quality, experiment


def money(value):
    return f'£{value:,.0f}'


def chart(fig, height=350):
    fig.update_layout(height=height, margin=dict(l=5, r=10, t=35, b=5),
                      paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                      font=dict(color='#355247'), legend_title_text='')
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor='#e3e9e1')
    st.plotly_chart(fig, width='stretch')


def download(table, label, name):
    st.download_button(label, table.to_csv(index=False).encode(), name, 'text/csv')


def display_table(table):
    display = table.copy()
    configuration = {}
    names = {}
    for col in display.columns:
        label = col.replace('_', ' ').capitalize()
        if pd.api.types.is_numeric_dtype(display[col]) and not pd.api.types.is_bool_dtype(display[col]):
            if any(word in col.lower() for word in ['margin', 'rate', 'wape']):
                display[col] *= 100
                label += ' (%)'
                fmt = '%.1f'
            elif any(word in col.lower() for word in ['p_value', 'ci_', 'difference', 'mean']):
                fmt = '%.4f'
            elif col.lower() in ['rows', 'horizon', 'fold', 'limit'] or 'units' in col.lower():
                fmt = '%.0f'
            else:
                fmt = '%.2f'
            if any(word in col.lower() for word in ['revenue', 'profit', 'cogs', 'fees', 'advertising', 'price', 'cost']) and 'margin' not in col and '£' not in label:
                label += ' (£)'
            configuration[label] = st.column_config.NumberColumn(label, format=fmt)
        names[col] = label
    renamed = display.rename(columns=names)
    st.dataframe(renamed, column_config=configuration, width='stretch', hide_index=True)


if not (ROOT / 'data/processed/transactions.parquet').exists():
    st.error('Build the data first: python src/build_project.py. See README.md for setup.')
    st.stop()

manifest_path = ROOT / 'reports/build_manifest.json'
df, tables, quality, experiment = load_data(manifest_path.stat().st_mtime_ns if manifest_path.exists() else 0)
months = complete_months(df)

with st.sidebar:
    st.markdown('## ◈ Retail Decisions')
    st.caption('E-commerce analysis workspace')
    page = st.radio('Explore', ['Overview', 'Products', 'Forecast', 'Pricing', 'Experiment', 'Analyst', 'Methodology'])
    st.divider()
    if page in ['Overview', 'Products', 'Pricing']:
        month = st.selectbox('Complete calendar month', months, index=len(months) - 1)
        country = st.selectbox('Country', ['All countries'] + sorted(df.country.unique().tolist()))
        scoped = df if country == 'All countries' else df[df.country.eq(country)]
        selected = scoped[scoped.month.eq(month)]
        if selected.empty:
            st.info('No transactions for this selection. Choose a different month or country.')
            st.stop()
    else:
        month, country, scoped, selected = months[-1], 'All countries', df, df[df.month.eq(months[-1])]
    st.caption('Historical data: Dec 2009–Dec 2011. Amounts in GBP.')
    with st.expander('Profit assumptions'):
        a = quality['assumptions']
        st.write(f"Unit cost: {a['unit_cost_share_of_product_reference_price']:.0%} of product reference price.")
        st.write(f"Fees: {a['marketplace_fee_share_of_positive_sales']:.0%}. Advertising: {a['advertising_share_of_positive_sales']:.0%}.")
        st.caption('Synthetic costs. Profit excludes overhead, fulfillment costs, and tax.')
    st.download_button('Download case study', (ROOT / 'docs/CASE_STUDY.md').read_text(), 'CASE_STUDY.md')

st.markdown('<div class="eyebrow">RETAIL DECISIONS / HISTORICAL CASE STUDY</div>', unsafe_allow_html=True)
titles = {'Overview': ('Profit beyond revenue', 'See what sold, what contributed profit under stated cost assumptions, and what changed.'),
          'Products': ('Find the products worth reviewing', 'Compare observed sales with modeled margins, returns, and month-over-month demand.'),
          'Forecast': ('Plan the next four weeks', 'Compare forecast methods, inspect test errors, and understand the uncertainty.'),
          'Pricing': ('Explore a price decision', 'Test price and advertising scenarios with explicit assumptions about demand.'),
          'Experiment': ('Test before you roll out', 'Design a customer-level experiment and inspect a reproducible simulated result.'),
          'Analyst': ('Ask the business analyst', 'Ask a question and inspect the calculation behind the answer.'),
          'Methodology': ('Understand the evidence', 'Review the source data, accounting model, exclusions, and evaluation choices.')}
st.title(titles[page][0])
st.markdown(f'<div class="context">{titles[page][1]}</div>', unsafe_allow_html=True)

if page == 'Overview':
    st.caption(f'{month} · {country} · Complete month · Profit is modeled')
    totals = aggregate(selected, ['month']).iloc[0]
    previous_month = str(pd.Period(month, 'M') - 1)
    previous_data = scoped[scoped.month.eq(previous_month)]
    previous = aggregate(previous_data, ['month']).iloc[0] if not previous_data.empty else None
    columns = st.columns(4)
    columns[0].metric('Net revenue', money(totals.net_revenue),
                      money(totals.net_revenue - previous.net_revenue) if previous is not None else None)
    columns[1].metric('Modeled contribution profit', money(totals.modeled_contribution_profit),
                      money(totals.modeled_contribution_profit - previous.modeled_contribution_profit) if previous is not None else None)
    columns[2].metric('Modeled margin', f'{totals.modeled_contribution_margin:.1%}' if pd.notna(totals.modeled_contribution_margin) else 'Unavailable')
    columns[3].metric('Refunds', money(totals.refunds))
    st.caption('Deltas compare the previous calendar month. Net revenue = positive sales less refunds.')
    left, right = st.columns([1.4, 1])
    with left:
        st.subheader('Monthly sales and modeled profit')
        monthly = aggregate(scoped, ['month'])
        monthly = monthly[monthly.month.isin(months)]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=monthly.month, y=monthly.net_revenue, name='Net revenue', line=dict(color='#27765e')))
        fig.add_trace(go.Scatter(x=monthly.month, y=monthly.modeled_contribution_profit, name='Modeled profit', line=dict(color='#b49554')))
        fig.update_layout(yaxis_title='GBP')
        chart(fig)
    with right:
        st.subheader('What changed in profit?')
        try:
            bridge = profit_bridge(scoped, month)
            labels = [previous_month] + list(bridge['drivers']) + [month]
            amounts = [bridge['previous_profit']] + list(bridge['drivers'].values()) + [0]
            waterfall = go.Figure(go.Waterfall(x=labels, y=amounts,
                measure=['absolute'] + ['relative'] * 4 + ['total'],
                increasing=dict(marker=dict(color='#27765e')), decreasing=dict(marker=dict(color='#a75b50'))))
            waterfall.update_xaxes(type='category')
            waterfall.update_layout(yaxis_title='Modeled profit (£)')
            chart(waterfall)
            st.caption('Accounting effects sum to the modeled profit change. They do not establish causal drivers.')
        except ValueError:
            st.info('The preceding month has no data for this country.')
    st.subheader('Products contributing the most modeled profit')
    top = product_table(selected).head(10)
    display_table(top[['product_id', 'description', 'net_revenue', 'modeled_contribution_profit', 'modeled_contribution_margin', 'recommendation']])
    download(aggregate(selected, ['product_id']), 'Download month product totals', 'monthly_products.csv')

elif page == 'Products':
    st.caption(f'{month} · {country} · Profit is modeled')
    products = product_table(selected)
    view = st.selectbox('Product view', ['All products', 'Promotion candidates', 'High revenue / low margin', 'Negative modeled profit', 'Declining sold units'])
    search = st.text_input('Search product code or description')
    if view == 'Promotion candidates':
        products = products[products.recommendation.eq('Promotion candidate')]
    elif view == 'High revenue / low margin':
        products = products[products.net_revenue.ge(products.net_revenue.quantile(.75)) & products.modeled_contribution_margin.lt(.1)]
    elif view == 'Negative modeled profit':
        products = products[products.modeled_contribution_profit.lt(0)]
    elif view == 'Declining sold units':
        products = product_momentum(scoped, month)
        products = products[products.unit_change.lt(0)]
    if search:
        products = products[products.product_id.str.contains(search, case=False, regex=False) | products.description.str.contains(search, case=False, regex=False)]
    if view == 'Declining sold units':
        st.caption('Includes products sold in the previous month but absent this month. No stock-availability data is available.')
    else:
        st.caption('Promotion candidate: margin ≥20% and revenue in the top quarter of products in this selection. This is a screening rule; incremental advertising return is unknown.')
        fig = px.scatter(products, x='net_revenue', y='modeled_contribution_margin', hover_name='description',
                         hover_data=['product_id', 'modeled_contribution_profit'], color='recommendation',
                         labels={'net_revenue': 'Net revenue (£)', 'modeled_contribution_margin': 'Modeled margin'})
        fig.update_yaxes(tickformat='.0%')
        chart(fig, 400)
    st.write(f'{len(products):,} products match this view.')
    display_table(products)
    download(products, 'Download selected products', 'products.csv')

elif page == 'Forecast':
    future, scores, backtests, history = [tables[f'forecast_{k}'] for k in ['future', 'scores', 'backtests', 'history']]
    ids = future.series_id.unique().tolist()
    names = product_table(df).set_index('product_id').description.to_dict()
    identifier = st.selectbox('Forecast series', ids, format_func=lambda x: 'All merchandise' if x == 'ALL' else f'{x} · {names.get(x, "Product")}')
    f = future[future.series_id.eq(identifier)]
    h = history[history.series_id.eq(identifier)].tail(52)
    s = scores[scores.series_id.eq(identifier)]
    test = s[s.selected & s.split.eq('test')].iloc[0]
    st.caption(f"All countries · As of {f.as_of.iloc[0]} · Four-week historical forecast · {f.model.iloc[0]}")
    cols = st.columns(3)
    cols[0].metric('Forecast sold units', f'{f.predicted_units.sum():,.0f}')
    cols[1].metric('Expected gross revenue', money(f.expected_gross_revenue.sum()))
    cols[2].metric('Selected model test WAPE', f'{test.wape:.1%}' if pd.notna(test.wape) else 'Unavailable')
    if pd.notna(test.wape) and test.wape > .5:
        st.warning('This product has high forecast error on the test period. Review its demand pattern before using the forecast for purchasing.')
    st.caption('Revenue uses the trailing 13-week average selling price. Returns and net profit are not forecast.')
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=h.week, y=h.sold_units, name='Observed sold units', line=dict(color='#27765e')))
    fig.add_trace(go.Scatter(x=f.week, y=f.upper_units, mode='lines', line=dict(width=0), showlegend=False))
    fig.add_trace(go.Scatter(x=f.week, y=f.lower_units, mode='lines', line=dict(width=0), fill='tonexty', fillcolor='rgba(180,149,84,.2)', name='Empirical error range'))
    fig.add_trace(go.Scatter(x=f.week, y=f.predicted_units, name='Forecast', line=dict(color='#b49554', dash='dash'), mode='lines+markers'))
    fig.update_layout(yaxis_title='Sold units', xaxis_title='Week starting Monday')
    chart(fig, 420)
    st.caption('Range width comes from four absolute validation errors per horizon. Coverage is not guaranteed. Product forecasts are independent, not a reconciliation to total demand.')
    st.subheader('Compare forecast methods')
    display_table(s)
    st.caption('Model selection uses the first 16 evaluation weeks. Test scores use the following 8 weeks with the selected method fixed. MAE is in units; WAPE is displayed as a percentage.')
    with st.expander('Inspect rolling test predictions'):
        display_table(backtests[backtests.series_id.eq(identifier) & backtests.split.eq('test')])
    download(f, 'Download forecast', 'forecast.csv')

elif page == 'Pricing':
    products = product_table(selected)
    identifier = st.selectbox('Apply scenario to', ['ALL'] + products.product_id.tolist(),
        format_func=lambda x: 'All selected products' if x == 'ALL' else f'{x} · {products.set_index("product_id").description.get(x, "Product")}')
    scenario_data = selected if identifier == 'ALL' else selected[selected.product_id.eq(identifier)]
    left, right = st.columns([1, 1.5])
    with left:
        price_pct = st.slider('Price change (%)', -30, 30, 5, 1)
        elasticity = st.slider('Assumed price elasticity', -3.0, 0.0, -1.0, .1)
        advertising_pct = st.slider('Advertising budget change (%)', -100, 100, 0, 5)
        st.caption('Elasticity -1 means a 1% price increase produces approximately a 1% unit decline. This response is assumed, not fitted to the dataset.')
        st.caption('Advertising changes spend only. No acquisition lift is assumed. COGS per unit and return proportions stay fixed.')
    scenario = simulate(scenario_data, price_pct / 100, elasticity, advertising_pct / 100)
    with right:
        cols = st.columns(2)
        cols[0].metric('Scenario modeled profit', money(scenario['scenario']['modeled_contribution_profit']), money(scenario['profit_change']))
        cols[1].metric('Assumed demand change', f"{scenario['demand_change']:+.1%}")
        comparison = pd.DataFrame({'Metric': ['Net revenue', 'Assumed COGS', 'Assumed fees', 'Assumed advertising', 'Modeled profit'],
            'Baseline': [scenario['baseline'][k] for k in ['net_revenue', 'assumed_cogs', 'assumed_marketplace_fees', 'assumed_advertising', 'modeled_contribution_profit']],
            'Scenario': [scenario['scenario'][k] for k in ['net_revenue', 'assumed_cogs', 'assumed_marketplace_fees', 'assumed_advertising', 'modeled_contribution_profit']]})
        display_table(comparison)
    st.subheader('How sensitive is profit to demand response?')
    sensitivity = pd.DataFrame([{'Price change': p, 'Elasticity': str(e),
        'Modeled profit (£)': simulate(scenario_data, p, e, advertising_pct / 100)['scenario']['modeled_contribution_profit']}
        for e in [0., -1., -2., -3.] for p in np.linspace(-.3, .3, 25)])
    fig = px.line(sensitivity, x='Price change', y='Modeled profit (£)', color='Elasticity')
    fig.update_xaxes(tickformat='.0%')
    chart(fig, 370)
    st.caption(f'{month} · {country} · Scenarios use observed sales as the baseline; no causal price recommendation is made.')
    download(comparison, 'Download scenario', 'pricing_scenario.csv')

elif page == 'Experiment':
    st.info('Simulated experiment. The UCI dataset contains no randomized treatment assignments.')
    left, right = st.columns(2)
    with left:
        st.subheader('Plan the sample size')
        baseline = st.number_input('Baseline conversion (%)', 1.0, 90.0, 5.0, .5) / 100
        mde = st.number_input('Minimum detectable lift (percentage points)', .1, 9.0, 1.0, .1) / 100
        power = st.selectbox('Statistical power', [.8, .9], format_func=lambda x: f'{x:.0%}')
        if baseline + mde >= 1:
            st.warning('Baseline plus lift must be below 100%.')
        else:
            n = required_sample(baseline, mde, power)
            st.metric('Required customers per arm', f'{n:,}')
            st.caption('Approximate two-sided conversion test, alpha 5%. Size the primary profit metric separately using pilot variance.')
    with right:
        st.subheader('Experiment design')
        st.markdown('**Randomization:** customer, sticky 50/50 assignment.\n\n**Primary metric:** contribution profit per assigned customer.\n\n**Guardrails:** conversion, return rate, customer complaints.\n\n**Duration:** fixed in advance; cover weekly cycles and the return window.\n\n**Decision rule:** lower 95% interval for profit lift must exceed £0.02/customer; check assignment balance and guardrails before rollout.')
    result = analyze_experiment(experiment)
    st.subheader('Seeded simulation result')
    st.write(result['decision'])
    st.caption(f"{result['control_n']:,} customers per arm · Sample-ratio check p = {result['srm_p_value']:.3f} · Seed 42")
    display_table(pd.DataFrame(result['metrics']))
    st.caption('Conversion differences are fractions (0.01 = 1 percentage point). Profit/revenue differences are GBP per customer. Secondary tests are exploratory and not corrected for multiple comparisons.')
    with st.expander('Simulation settings and interpretation'):
        st.write('Control conversion 5%, price £20; treatment conversion 5.5%, price £21. Unit cost £11, fee 15%, advertising £0.20/customer, return probability 6%. Treatment demand is generated, not inferred from UCI.')
        st.write('A small p-value does not guarantee a useful profit lift. The primary interval must also clear the business threshold. The demo does not model delayed returns or complaint data, so it cannot establish all rollout guardrails.')
    download(experiment, 'Download simulated customer data', 'simulated_experiment.csv')

elif page == 'Analyst':
    live = False
    st.caption('Free local analyst: Python calculates the results and explains them using predefined rules. No AI subscription or API credits are required. This mode does not use a language model.')
    if os.getenv('ENABLE_LIVE_AI') == 'true':
        has_api = bool(os.getenv('OPENAI_API_KEY') and os.getenv('OPENAI_MODEL'))
        live = st.toggle('Use OpenAI tool planner (paid API)', value=False, disabled=not has_api)
    sample = st.selectbox('Example question', ['Which products generate the most profit?',
        'Why did profitability fall in 2011-01?', 'Which products are losing sales in 2011-11?',
        'What are expected sales over the next four weeks?', 'What if price increases by 5% in 2011-11?'])
    with st.form('analyst_question'):
        question = st.text_area('Your business question', value=sample, max_chars=2000)
        submitted = st.form_submit_button('Run analysis', type='primary')
    if submitted:
        try:
            with st.spinner('Running analysis...'):
                result = answer(question, df, tables['forecast_future'], live=live)
            st.subheader(result['title'])
            st.write(result['text'])
            st.caption(result['mode'])
            if result['table'] is not None:
                display_table(result['table'])
                download(result['table'], 'Download analysis', 'analyst_result.csv')
            if 'plan' in result:
                with st.expander('Inspect selected analysis'):
                    st.json(result['plan'])
        except ValueError as e:
            st.warning(str(e))
        except Exception:
            st.error('The AI provider could not complete the request. Check the server configuration or switch to local analysis.')
    st.caption('Analyst queries use all countries. Missing months, unsupported products, and unavailable data produce an explicit message. All displayed numbers are calculated by Python; the optional LLM selects the analysis only.')

else:
    st.subheader('Source and row reconciliation')
    st.markdown('[UCI Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii) · Chen, D. (2012) · CC BY 4.0 · 2009–2011 UK online gift retailer')
    rows = pd.DataFrame({'Scope': ['Source rows', 'Cross-sheet overlap removed', 'Rejected', 'Non-merchandise', 'Uncosted return-only', 'Modeled merchandise'],
        'Rows': [quality[k] for k in ['input_rows', 'cross_sheet_overlap_removed', 'rejected_rows', 'non_product_rows', 'uncosted_rows', 'modeled_rows']]})
    display_table(rows)
    st.write('Row partition reconciles.' if quality['partition_reconciles'] else 'Row partition does not reconcile.')
    st.write(f"{quality['cross_sheet_overlap_removed']:,} repeated lines removed from the overlapping year sheets. {quality['exact_duplicate_rows_retained']:,} remaining duplicate-looking rows retained. {quality['large_lines_retained']:,} unusually large lines retained and flagged.")
    st.caption('Missing customer IDs are retained for product analytics. Invoice cancellations with negative quantities are kept as returns. Nonpositive prices, zero quantities, invalid fields, and positive-quantity cancellations are reported separately. Merchandise codes must match five digits plus optional letters.')
    st.subheader('Observed and assumed inputs')
    st.markdown('**Observed:** invoice, product, quantity, price, date, customer ID (when present), country.\n\n**Assumed:** unit cost, marketplace fee allocation, ad allocation, return cost recovery, price elasticity. Product categories and advertising exposure are unavailable.\n\n**Contribution profit:** net revenue − assumed COGS − assumed fees − assumed advertising. This excludes overhead, shipping/fulfillment costs, and tax.\n\n**Reference cost:** median positive-sale price per product across the full history × cost share. This is descriptive and must not be used to claim a leakage-free historical profit forecast.')
    st.json(quality['assumptions'])
    st.subheader('Forecast evaluation')
    st.markdown('Only complete Monday–Sunday weeks are modeled. Demand means sold units before returns. Three models are compared with six rolling four-week forecasts. Sixteen validation weeks choose the model; eight later test weeks assess it. Final forecasts refit on all complete history. MAE and WAPE are reported. Empirical error ranges have limited calibration data and are not guaranteed confidence intervals.')
    st.subheader('Reproduce and extend')
    st.markdown('The repository includes source ingestion, cleaning, SQL views, a PostgreSQL bulk loader, financial and forecasting tests, and a case study. Connect actual cost/ad tables before operational use. See README.md for setup and docs/ for the metric dictionary, experiment protocol, and demo script.')
    st.download_button('Download quality report', json.dumps(quality, indent=2), 'quality_report.json', 'application/json')
