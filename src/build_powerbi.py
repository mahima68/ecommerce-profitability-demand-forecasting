"""Author portable PBIP/PBIR files and a monthly product-country semantic model.

Schema validation is separate from refresh/render validation in Power BI Desktop.
"""
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'powerbi'
BASE = 'https://developer.microsoft.com/json-schemas/fabric/'


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding='utf-8')


def column(name, kind='double', hidden=False):
    return {'name': name, 'dataType': kind, 'sourceColumn': name,
            'summarizeBy': 'none', 'isHidden': hidden}


def table(name, columns, source, measures=None):
    result = {'name': name, 'columns': columns,
              'partitions': [{'name': name, 'mode': 'import',
                              'source': {'type': 'm', 'expression': source}}]}
    if measures:
        result['measures'] = measures
    return result


def projection(entity, name, measure=False):
    return {'field': {'Measure' if measure else 'Column': {
        'Expression': {'SourceRef': {'Entity': entity}}, 'Property': name}},
        'queryRef': f'{entity}.{name}', 'nativeQueryRef': name}


def literal(value):
    return {'expr': {'Literal': {'Value': value}}}


def visual(page, name, kind, title, roles, x, y, w, h):
    value = {'$schema': BASE + 'item/report/definition/visualContainer/2.0.0/schema.json',
             'name': name, 'position': {'x': x, 'y': y, 'z': 0, 'width': w, 'height': h, 'tabOrder': 0},
             'visual': {'visualType': kind, 'query': {'queryState': {
                 role: {'projections': fields} for role, fields in roles.items()}},
                 'visualContainerObjects': {'title': [{'properties': {
                     'show': literal('true'), 'text': literal("'" + title.replace("'", "''") + "'"),
                     'fontSize': literal('14D'), 'titleWrap': literal('true')}}]},
                 'drillFilterOtherVisuals': True}}
    save(page / 'visuals' / name / 'visual.json', value)


def build():
    data_dir = OUT / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_parquet(ROOT / 'data/processed/transactions.parquet')
    metrics = ['gross_revenue', 'refunds', 'net_revenue', 'sold_units', 'returned_units',
               'assumed_cogs', 'assumed_marketplace_fees', 'assumed_advertising', 'modeled_contribution_profit']
    facts = df.groupby(['month', 'product_id', 'country'], dropna=False)[metrics].sum().reset_index()
    facts['month'] = facts.month + '-01'
    facts.to_csv(data_dir / 'monthly_product_country.csv', index=False)
    products = df.sort_values('date').drop_duplicates('product_id', keep='last')[['product_id', 'description']]
    products.to_csv(data_dir / 'products.csv', index=False)
    forecast = pd.read_csv(ROOT / 'reports/forecast_future.csv')
    forecast.to_csv(data_dir / 'forecast.csv', index=False)
    months = pd.read_csv(ROOT / 'reports/monthly_profitability.csv')[['month', 'complete_month']]
    months['month'] = months.month + '-01'
    months.to_csv(data_dir / 'months.csv', index=False)
    for metric in metrics:
        if abs(facts[metric].sum() - df[metric].sum()) > .01:
            raise ValueError(f'Power BI export reconciliation failed: {metric}')

    def csv_source(file, types):
        pairs = ', '.join('{"' + k + '", ' + v + '}' for k, v in types.items())
        return ['let', f'    Source = Csv.Document(File.Contents(DataFolder & "/{file}"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),',
                '    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),',
                f'    Typed = Table.TransformColumnTypes(Headers, {{{pairs}}}, "en-GB")', 'in', '    Typed']

    money = '£#,0.00;(£#,0.00);£0.00'
    measures = []
    for label, col in [('Net Revenue', 'net_revenue'), ('Modeled Contribution Profit', 'modeled_contribution_profit'),
                       ('Gross Revenue', 'gross_revenue'), ('Refunds', 'refunds'), ('Sold Units', 'sold_units'),
                       ('Returned Units', 'returned_units'), ('Assumed COGS', 'assumed_cogs'),
                       ('Assumed Fees', 'assumed_marketplace_fees'), ('Assumed Advertising', 'assumed_advertising')]:
        measures.append({'name': label, 'expression': f'SUM(FactSales[{col}])',
                         'formatString': '#,0' if 'Units' in label else money})
    measures += [{'name': 'Modeled Margin', 'expression': 'IF([Net Revenue] > 0, DIVIDE([Modeled Contribution Profit], [Net Revenue]))', 'formatString': '0.0%'},
                 {'name': 'Return Unit Rate', 'expression': 'DIVIDE([Returned Units], [Sold Units])', 'formatString': '0.0%'}]
    types = {'month': 'type date', 'product_id': 'type text', 'country': 'type text', **{m: 'type number' for m in metrics}}
    tables = [table('FactSales', [column('month', 'dateTime', True), column('product_id', 'string', True),
                                 column('country', 'string', True)] + [column(m, hidden=True) for m in metrics], ['FactSource'], measures),
              table('Products', [column('product_id', 'string'), column('description', 'string')], csv_source('products.csv', {'product_id': 'type text', 'description': 'type text'})),
              table('Months', [column('month', 'dateTime'), column('complete_month', 'boolean')], csv_source('months.csv', {'month': 'type date', 'complete_month': 'type logical'})),
              table('Countries', [column('country', 'string')], ['Table.Distinct(Table.SelectColumns(FactSource, {"country"}))']),
              table('Forecast', [column(c, 'dateTime' if c in ['week', 'as_of'] else 'double' if c in ['predicted_units', 'lower_units', 'upper_units', 'assumed_average_selling_price', 'expected_gross_revenue'] else 'string', c in ['predicted_units', 'lower_units', 'upper_units', 'expected_gross_revenue']) for c in forecast.columns],
                    csv_source('forecast.csv', {c: 'type date' if c in ['week', 'as_of'] else 'type number' if c in ['predicted_units', 'lower_units', 'upper_units', 'assumed_average_selling_price', 'expected_gross_revenue'] else 'type text' for c in forecast.columns}),
                    [{'name': label, 'expression': f'IF(HASONEVALUE(Forecast[series_id]), SUM(Forecast[{col}]), CALCULATE(SUM(Forecast[{col}]), Forecast[series_id] = "ALL"))', 'formatString': money if col == 'expected_gross_revenue' else '#,0'} for label, col in [('Predicted Units', 'predicted_units'), ('Lower Range', 'lower_units'), ('Upper Range', 'upper_units'), ('Expected Gross Revenue', 'expected_gross_revenue')]])]
    model = {'name': 'RetailAnalytics', 'compatibilityLevel': 1567, 'model': {
        'culture': 'en-GB', 'defaultPowerBIDataSourceVersion': 'powerBI_V3',
        'annotations': [{'name': 'PBI_QueryOrder', 'value': json.dumps(['DataFolder', 'FactSource', 'FactSales', 'Products', 'Months', 'Countries', 'Forecast'])}],
        'expressions': [{'name': 'DataFolder', 'kind': 'm', 'expression': '"' + str(data_dir.resolve()).replace('"', '""') + '" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]'},
                        {'name': 'FactSource', 'kind': 'm', 'expression': csv_source('monthly_product_country.csv', types)}],
        'tables': tables,
        'relationships': [{'name': f'Fact_{dim}', 'fromTable': 'FactSales', 'fromColumn': key,
                           'toTable': dim, 'toColumn': key, 'crossFilteringBehavior': 'oneDirection'}
                          for dim, key in [('Products', 'product_id'), ('Months', 'month'), ('Countries', 'country')]]}}
    semantic = OUT / 'Retail.SemanticModel'
    save(semantic / 'definition.pbism', {'$schema': BASE + 'item/semanticModel/definitionProperties/1.0.0/schema.json', 'version': '1.0', 'settings': {}})
    save(semantic / 'model.bim', model)
    report = OUT / 'Retail.Report'
    save(OUT / 'Retail.pbip', {'$schema': BASE + 'pbip/pbipProperties/1.0.0/schema.json', 'version': '1.0', 'artifacts': [{'report': {'path': 'Retail.Report'}}], 'settings': {'enableAutoRecovery': True}})
    save(report / 'definition.pbir', {'$schema': BASE + 'item/report/definitionProperties/2.0.0/schema.json', 'version': '4.0', 'datasetReference': {'byPath': {'path': '../Retail.SemanticModel'}}})
    definition = report / 'definition'
    save(definition / 'version.json', {'$schema': BASE + 'item/report/definition/versionMetadata/1.0.0/schema.json', 'version': '1.0.0'})
    save(definition / 'report.json', {'$schema': BASE + 'item/report/definition/report/1.0.0/schema.json', 'layoutOptimization': 'None', 'themeCollection': {}})
    page_order = ['Overview', 'Products', 'Countries', 'Forecast']
    save(definition / 'pages/pages.json', {'$schema': BASE + 'item/report/definition/pagesMetadata/1.0.0/schema.json', 'pageOrder': page_order, 'activePageName': 'Overview'})
    for name in page_order:
        page = definition / 'pages' / name
        caption = name + (' — historical forecast; empirical ranges, no guaranteed coverage' if name == 'Forecast' else ' — observed revenue; modeled costs and profit')
        save(page / 'page.json', {'$schema': BASE + 'item/report/definition/page/1.0.0/schema.json', 'name': name, 'displayName': caption, 'displayOption': 'FitToPage', 'width': 1280, 'height': 720})
        if name != 'Forecast':
            visual(page, 'MonthFilter', 'slicer', 'Month', {'Values': [projection('Months', 'month')]}, 20, 10, 340, 90)
            visual(page, 'CountryFilter', 'slicer', 'Country', {'Values': [projection('Countries', 'country')]}, 380, 10, 430, 90)
            visual(page, 'CompleteFilter', 'slicer', 'Complete month? Final December is partial', {'Values': [projection('Months', 'complete_month')]}, 830, 10, 430, 90)
            for i, metric in enumerate(['Net Revenue', 'Modeled Contribution Profit', 'Modeled Margin', 'Return Unit Rate']):
                visual(page, f'KPI{i}', 'card', metric, {'Values': [projection('FactSales', metric, True)]}, 20 + i * 315, 115, 300, 125)
        if name == 'Overview':
            visual(page, 'RevenueTrend', 'lineChart', 'Monthly revenue and modeled profit (£)', {'Category': [projection('Months', 'month')], 'Y': [projection('FactSales', m, True) for m in ['Net Revenue', 'Modeled Contribution Profit']]}, 20, 260, 780, 440)
            visual(page, 'CostTable', 'tableEx', 'Costs are assumed: COGS 55%, fees 15%, ads 8%', {'Values': [projection('Months', 'month')] + [projection('FactSales', m, True) for m in ['Assumed COGS', 'Assumed Fees', 'Assumed Advertising', 'Refunds']]}, 820, 260, 440, 440)
        elif name == 'Products':
            visual(page, 'ProductTable', 'tableEx', 'Product profitability and returns — select column header to sort', {'Values': [projection('Products', c) for c in ['product_id', 'description']] + [projection('FactSales', m, True) for m in ['Net Revenue', 'Modeled Contribution Profit', 'Modeled Margin', 'Sold Units', 'Returned Units']]}, 20, 260, 1240, 440)
        elif name == 'Countries':
            visual(page, 'CountryBars', 'clusteredBarChart', 'Modeled contribution profit by country', {'Category': [projection('Countries', 'country')], 'Y': [projection('FactSales', 'Modeled Contribution Profit', True)]}, 20, 260, 600, 440)
            visual(page, 'CountryTable', 'tableEx', 'Country revenue, modeled margin and returns', {'Values': [projection('Countries', 'country')] + [projection('FactSales', m, True) for m in ['Net Revenue', 'Modeled Contribution Profit', 'Modeled Margin', 'Return Unit Rate']]}, 640, 260, 620, 440)
        else:
            visual(page, 'SeriesFilter', 'slicer', 'Choose ALL for total business; product forecasts are separate', {'Values': [projection('Forecast', 'series_id')]}, 20, 10, 1240, 90)
            visual(page, 'FutureTrend', 'lineChart', 'Four historical weeks after Dec 4, 2011 — choose one series', {'Category': [projection('Forecast', 'week')], 'Y': [projection('Forecast', m, True) for m in ['Predicted Units', 'Lower Range', 'Upper Range']]}, 20, 120, 780, 580)
            visual(page, 'ForecastTable', 'tableEx', 'Aggregate and product series overlap; do not sum across series', {'Values': [projection('Forecast', c) for c in ['series_id', 'week', 'model', 'range_label']] + [projection('Forecast', m, True) for m in ['Predicted Units', 'Expected Gross Revenue']]}, 820, 120, 440, 580)
    save(ROOT / 'reports/powerbi_verification.json', {'authoring_complete': True, 'desktop_refresh_verified': False, 'desktop_render_verified': False, 'fact_grain': 'month × product × country', 'fact_rows': len(facts), 'additive_metrics_reconciled': metrics, 'source_rows': len(df)})
    print(f'Power BI project authored: {len(facts):,} aggregate rows, 4 pages. Desktop refresh/render pending.')


if __name__ == '__main__':
    build()
