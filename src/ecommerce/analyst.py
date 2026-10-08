"""An allowlisted planner selects Python tools; rendered numbers are never LLM text."""
import json
import os
import re
from .data import complete_months, product_table
from .decisions import profit_bridge, simulate, product_momentum

SUPPORTED = ['top_products', 'profit_drivers', 'forecast', 'pricing', 'declining_products', 'unsupported']


def local_plan(question):
    q = question.lower()
    month_match = re.search(r'\b(20\d{2}-(?:0[1-9]|1[0-2]))\b', q)
    product_match = re.search(r'\b(?:product|sku)\s+([0-9]{5}[a-z]*)\b', q)
    percentage = re.search(r'([+-]?\d+(?:\.\d+)?)\s*%', q)
    price = float(percentage.group(1)) / 100 if percentage else .05
    if re.search(r'\b(decrease\w*|lower\w*|reduc\w*|drop\w*|cut\w*)\b', q) and price > 0:
        price = -price
    limit_match = re.search(r'\b(?:top|best|show)\s+(\d+)\b', q)
    # Explicitly unsupported domains never receive invented responses.
    if re.search(r'\b(salary|weather|customer name|email|password|delete|drop table|sql|inventory|stockout|causal|causality)\b', q):
        intent = 'unsupported'
    elif re.search(r'\b(forecast|predict|next month|next four|next 4)\b', q):
        intent = 'forecast'
    elif re.search(r'\b(price|pricing|what if|scenario)\b', q):
        intent = 'pricing'
    elif re.search(r'\b(declining|losing sales|sales fall|sales fell|sales drop)\b', q):
        intent = 'declining_products'
    elif re.search(r'\b(why|driver|fell|fall|decrease|change)\b', q):
        intent = 'profit_drivers'
    elif re.search(r'\b(top|best|profitable|promotion|promote|profit)\b', q):
        intent = 'top_products'
    else:
        intent = 'unsupported'
    return {'intent': intent, 'month': month_match.group(1) if month_match else None,
            'product_id': product_match.group(1).upper() if product_match else None,
            'price_change': price, 'elasticity': -1.0,
            'limit': int(limit_match.group(1)) if limit_match else 10}


def openai_plan(question, client=None, model=None):
    from .private_settings import load_private_settings
    load_private_settings()
    if client is None:
        from openai import OpenAI
        client = OpenAI(timeout=30, max_retries=1)
    model = model or os.getenv('OPENAI_MODEL')
    if not model:
        raise ValueError('Configure OPENAI_MODEL with a model available to your API account.')
    properties = {
        'intent': {'type': 'string', 'enum': SUPPORTED},
        'month': {'type': ['string', 'null'], 'description': 'YYYY-MM explicitly requested; null uses latest complete month.'},
        'product_id': {'type': ['string', 'null']},
        'price_change': {'type': 'number', 'description': 'Fraction between -0.3 and 0.3; default 0.05.'},
        'elasticity': {'type': 'number', 'description': 'Assumed elasticity between -3 and 0; default -1.'},
        'limit': {'type': 'integer', 'description': '1 to 20; default 10.'}}
    response = client.responses.create(model=model, store=False,
        instructions='Select a read-only analysis tool. Do not calculate or answer with numbers. '
                     'Historical UCI data is from 2009-2011. Route questions about unavailable data, '
                     'causal proof, secrets, executable SQL, or destructive actions to unsupported. '
                     'Never convert today into a historical month. Respect explicit month/product IDs.',
        input=question[:2000],
        tools=[{'type': 'function', 'name': 'run_analysis', 'description': 'Run a deterministic retail analysis.',
                'strict': True, 'parameters': {'type': 'object', 'properties': properties,
                        'required': list(properties), 'additionalProperties': False}}],
        tool_choice={'type': 'function', 'name': 'run_analysis'}, parallel_tool_calls=False)
    calls = [item for item in response.output if item.type == 'function_call']
    if len(calls) != 1 or calls[0].name != 'run_analysis':
        raise ValueError('The planner did not return one supported analysis call.')
    return validate_plan(json.loads(calls[0].arguments))


def validate_plan(plan):
    if set(plan) != {'intent', 'month', 'product_id', 'price_change', 'elasticity', 'limit'}:
        raise ValueError('Unexpected planner parameters.')
    if plan['intent'] not in SUPPORTED:
        raise ValueError('Unsupported analysis tool.')
    if plan['month'] is not None and (not isinstance(plan['month'], str) or
        not re.fullmatch(r'20\d{2}-(0[1-9]|1[0-2])', plan['month'])):
        raise ValueError('Invalid month.')
    if plan['product_id'] is not None and (not isinstance(plan['product_id'], str) or
        not re.fullmatch(r'\d{5}[A-Za-z]*', plan['product_id'])):
        raise ValueError('Invalid product identifier.')
    if type(plan['limit']) is not int or not 1 <= plan['limit'] <= 20:
        raise ValueError('Limit must be 1–20.')
    for key, low, high in [('price_change', -.3, .3), ('elasticity', -3, 0)]:
        if type(plan[key]) not in (int, float) or not low <= plan[key] <= high:
            raise ValueError(f'Invalid {key}.')
    return plan


def execute(plan, df, future):
    plan = validate_plan(plan)
    month = plan['month'] or complete_months(df)[-1]
    intent = plan['intent']
    selected = df[df.month.eq(month)]
    product = plan['product_id']
    if product:
        selected = selected[selected.product_id.eq(product)]
    if intent == 'unsupported':
        return {'title': 'Question outside the available analysis',
                'text': 'Ask about profitable products, monthly profit drivers, declining sales, price scenarios, or forecasts. No result has been invented.',
                'table': None}
    if intent != 'forecast' and selected.empty:
        raise ValueError('No data for the requested month or product.')
    if intent == 'top_products':
        table = product_table(selected).head(plan['limit'])
        text = f'Products ranked by modeled contribution profit in {month}. Promotion labels are screening rules, not estimates of advertising response.'
        title = 'Top products'
    elif intent == 'profit_drivers':
        source = df if product is None else df[df.product_id.eq(product)]
        result = profit_bridge(source, month)
        direction = 'increased' if result['change'] >= 0 else 'decreased'
        text = (f"Modeled contribution profit {direction} by £{abs(result['change']):,.2f} "
                f"from {result['previous']} to {month}. This is an accounting bridge, not causal attribution.")
        import pandas as pd
        table = pd.DataFrame({'Driver': list(result['drivers']), 'Profit effect (£)': list(result['drivers'].values())})
        title = 'Profit drivers'
    elif intent == 'forecast':
        table = future[future.series_id.eq(product or 'ALL')]
        if table.empty:
            raise ValueError('No forecast for this product; choose one of the forecasted products.')
        if plan['month'] is not None and not table.week.astype(str).str.startswith(plan['month']).all():
            raise ValueError('Only the four-week historical forecast after 2011-12-04 is available; no forecast for the requested month.')
        total = table.predicted_units.sum()
        text = f"Four-week forecast as of {table.as_of.iloc[0]}: {total:,.0f} units. Expected gross revenue assumes the recent average selling price; returns are not forecast."
        title = 'Sales forecast'
    elif intent == 'declining_products':
        source = df if product is None else df[df.product_id.eq(product)]
        table = product_momentum(source, month)
        table = table[table.unit_change.lt(0)].head(plan['limit'])
        text = f'Products with falling sold units in {month} versus the previous month. Changes can reflect seasonality, availability, or demand; the dataset cannot distinguish those causes.'
        title = 'Declining sales'
    else:
        result = simulate(selected, plan['price_change'], plan['elasticity'])
        import pandas as pd
        keys = ['net_revenue', 'assumed_cogs', 'assumed_marketplace_fees', 'assumed_advertising', 'modeled_contribution_profit']
        table = pd.DataFrame({'Metric (£)': [k.replace('_', ' ').capitalize() for k in keys],
            'Baseline': [result['baseline'][k] for k in keys],
            'Scenario': [result['scenario'][k] for k in keys]})
        text = (f"Modeled profit changes by £{result['profit_change']:,.2f} under a {plan['price_change']:+.1%} "
                f"price change and assumed elasticity {plan['elasticity']:.1f}. Demand response is an assumption.")
        title = 'Pricing scenario'
    return {'title': title, 'text': text, 'table': table, 'plan': plan}


def answer(question, df, future, live=False, client=None, model=None):
    plan = openai_plan(question, client, model) if live else local_plan(question)
    result = execute(plan, df, future)
    result['mode'] = 'OpenAI tool planner + Python calculations' if live else 'Local rules + Python calculations (no LLM)'
    return result
