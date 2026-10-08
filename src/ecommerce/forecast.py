"""Four-week rolling forecasts with a separate model-selection and test window."""
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

MODELS = ['Recent 4-week mean', 'Seasonal naive (52 weeks)', 'Seasonal ridge']


def weekly_series(df, product_id=None):
    # First and final incomplete weeks are excluded using dataset boundaries.
    start = df.date.min().normalize()
    end = df.date.max().normalize()
    first = start + pd.Timedelta(days=(7 - start.weekday()) % 7)
    final_monday = end - pd.Timedelta(days=end.weekday())
    if end.weekday() < 6:
        final_monday -= pd.Timedelta(weeks=1)
    index = pd.date_range(first, final_monday, freq='W-MON')
    selected = df if product_id is None else df[df.product_id.eq(product_id)]
    units = selected.groupby('week').sold_units.sum().reindex(index, fill_value=0)
    units.name = 'sold_units'
    return units


def features(history, t):
    value = [t / 52]
    for k in range(1, 4):
        value.extend([np.sin(2 * np.pi * k * t / 52), np.cos(2 * np.pi * k * t / 52)])
    value.extend([history[t - 1], np.mean(history[t - 4:t]), history[t - 52]])
    return value


def predict(history, model, horizon=4):
    y = np.asarray(history, dtype=float)
    if len(y) < 60:
        raise ValueError('At least 60 complete weeks are required.')
    if model == MODELS[0]:
        return np.repeat(y[-4:].mean(), horizon)
    if model == MODELS[1]:
        return np.array([y[len(y) - 52 + h] for h in range(horizon)])
    if model != MODELS[2]:
        raise ValueError('Unknown forecasting model.')
    x = [features(y, t) for t in range(52, len(y))]
    reg = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
    reg.fit(x, y[52:])
    extended = list(y)
    predictions = []
    for h in range(horizon):
        estimate = max(0, float(reg.predict([features(extended, len(extended))])[0]))
        predictions.append(estimate)
        extended.append(estimate)
    return np.array(predictions)


def errors(actual, predicted):
    actual, predicted = np.asarray(actual), np.asarray(predicted)
    denominator = np.abs(actual).sum()
    return {'mae': float(np.mean(np.abs(actual - predicted))),
            'wape': float(np.abs(actual - predicted).sum() / denominator) if denominator > 0 else None,
            'bias': float(np.mean(predicted - actual))}


def evaluate_series(series, series_id='ALL'):
    if len(series) < 84 or (series > 0).sum() < 30:
        raise ValueError('Insufficient history for the 24-week evaluation window.')
    records = []
    # First 16 weeks select the model; last 8 weeks are an untouched test.
    origins = range(len(series) - 24, len(series) - 3, 4)
    for fold, origin in enumerate(origins):
        for model in MODELS:
            estimates = predict(series.iloc[:origin], model)
            actual = series.iloc[origin:origin + 4]
            for h in range(4):
                records.append({'series_id': series_id, 'model': model, 'fold': fold + 1,
                    'split': 'validation' if fold < 4 else 'test',
                    'origin': str((series.index[origin - 1] + pd.Timedelta(days=6)).date()),
                    'week': str(actual.index[h].date()), 'horizon': h + 1,
                    'actual_units': float(actual.iloc[h]), 'predicted_units': float(estimates[h])})
    predictions = pd.DataFrame(records)
    scores = []
    for (model, split), rows in predictions.groupby(['model', 'split']):
        scores.append({'series_id': series_id, 'model': model, 'split': split,
                       **errors(rows.actual_units, rows.predicted_units)})
    scores = pd.DataFrame(scores)
    validation = scores[scores.split.eq('validation')].sort_values('mae')
    chosen = validation.iloc[0].model
    scores['selected'] = scores.model.eq(chosen)
    calibration = predictions[predictions.model.eq(chosen) & predictions.split.eq('validation')]
    final = predict(series, chosen)
    future = []
    for h, point in enumerate(final, 1):
        residuals = calibration[calibration.horizon.eq(h)]
        width = float(np.quantile(np.abs(residuals.actual_units - residuals.predicted_units), .9))
        future.append({'series_id': series_id, 'week': str((series.index[-1] + pd.Timedelta(weeks=h)).date()),
            'model': chosen, 'predicted_units': float(point), 'lower_units': max(0, float(point - width)),
            'upper_units': float(point + width), 'range_label': 'Empirical error range; coverage not guaranteed'})
    return pd.DataFrame(future), scores, predictions


def forecast_all(df, top_n=8):
    complete = weekly_series(df)
    boundary = complete.index[-1] + pd.Timedelta(days=7)
    available = df[df.date.lt(boundary)]
    ids = available.groupby('product_id').sold_units.sum().nlargest(top_n).index.tolist()
    futures, scores, backtests, histories = [], [], [], []
    skipped = []
    for identifier in ['ALL'] + ids:
        series = complete if identifier == 'ALL' else weekly_series(df, identifier)
        try:
            future, score, backtest = evaluate_series(series, identifier)
        except ValueError as e:
            skipped.append({'series_id': identifier, 'reason': str(e)})
            continue
        selected = available if identifier == 'ALL' else available[available.product_id.eq(identifier)]
        recent = selected[selected.date.ge(complete.index[-1] - pd.Timedelta(weeks=12))]
        average_price = recent.gross_revenue.sum() / recent.sold_units.sum() if recent.sold_units.sum() else 0
        future['assumed_average_selling_price'] = average_price
        future['expected_gross_revenue'] = future.predicted_units * average_price
        future['as_of'] = str((boundary - pd.Timedelta(days=1)).date())
        futures.append(future)
        scores.append(score)
        backtests.append(backtest)
        histories.append(pd.DataFrame({'series_id': identifier, 'week': series.index,
                                     'sold_units': series.to_numpy()}))
    return {'future': pd.concat(futures, ignore_index=True),
            'scores': pd.concat(scores, ignore_index=True),
            'backtests': pd.concat(backtests, ignore_index=True),
            'history': pd.concat(histories, ignore_index=True), 'skipped': skipped}
