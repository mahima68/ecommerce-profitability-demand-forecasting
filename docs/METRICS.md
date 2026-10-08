# Metric dictionary

All amounts are GBP. Every profit metric uses modeled costs.

| Metric | Definition | Important boundary |
|---|---|---|
| Gross revenue | Sum of positive quantity × positive selling price | Before refunds; no VAT/shipping adjustment inferred |
| Refunds | Absolute value of negative quantity × price | Refund lines can refer to sales in earlier months |
| Net revenue | Gross revenue − refunds | Modeled merchandise scope excludes uncosted return-only products |
| Sold units | Sum of positive quantities | A gross demand proxy, not unmet demand |
| Returned units | Absolute sum of negative quantities | No one-to-one matching to earlier sale lines |
| Reference price | Median unit price on positive-sale lines, by product | Full-history descriptive reference |
| Assumed unit cost | Reference price × configured cost share | Held fixed under price scenarios |
| Assumed COGS | Quantity × unit cost, with configurable recovery on returns | Assumes recoverable inventory can reverse cost |
| Assumed fees | Fee rate × (gross revenue − refunds × fee-refund share) | Synthetic marketplace scenario |
| Assumed advertising | Ad allocation rate × gross revenue | Synthetic allocation, not actual ad attribution |
| Modeled contribution profit | Net revenue − COGS − fees − advertising | Excludes fulfillment, overhead, and taxes |
| Modeled contribution margin | Modeled profit / net revenue | Unavailable if net revenue ≤0 |
| Return unit rate | Returned units / sold units in selected period | Can exceed 100% due to cross-period returns |
| MAE | Mean absolute forecast error | Sold units per week |
| WAPE | Sum absolute error / sum actual sold units | Ratio; unavailable when actual demand sums to zero |
| Forecast bias | Mean(prediction − actual) | Positive means overforecasting |
| Expected gross revenue | Forecast units × trailing 13-week weighted average price | Price stability assumed; returns not forecast |

## Data model

The fact table grain is a source invoice line. `line_id` is its original source-order identifier, not a supplier-provided unique key. `product_id`, `month`, `week`, and `country` are grouping dimensions. The year sheets overlap in December 2010. Exact matching records across sheets are assigned within-sheet occurrence ranks, then deduplicated on record + occurrence, retaining the maximum multiplicity observed in either sheet. This removes repeated snapshots without removing ambiguous duplicates within one sheet. Remaining duplicate-looking lines are retained and counted. Invoice numbers are not unique across lines and must not be used as primary keys.

Non-merchandise stock codes are separated using the explicit pattern `five digits + optional letters`. This heuristic is auditable but is not a validated product taxonomy. No categories have been invented.

## Period boundaries

Only full calendar months appear in monthly comparison controls. Only full Monday–Sunday weeks enter forecasts. The partial final month/week remains in the cleaned facts, but is not compared as if it were complete. The latest forecast origin is December 4, 2011; the project does not forecast the present day.

## Price scenario

`demand_multiplier = (1 + price_change) ** assumed_elasticity`.

Revenue and fees scale with price × demand. Quantities and COGS scale with demand. The observed return proportion stays fixed. Advertising budget changes independently; no demand response to advertising is assumed. Scenarios reuse the observed month as their baseline and do not estimate causal price elasticity.

## Forecast design

Candidates: four-week moving average, 52-week seasonal naive, seasonal ridge. Ridge uses standardized trend, annual Fourier terms, last-week demand, four-week mean, and a 52-week lag, with fixed alpha 10. Four-week predictions are recursive. Each fold trains on preceding observations only. First 16 rolling evaluation weeks select the model by MAE; final 8 test weeks do not influence selection. Final deployment refits the selected method on all complete weeks.

Error ranges use a 90th percentile of four absolute validation errors per horizon. They are exploratory empirical ranges with little calibration data, not guaranteed 90% intervals. Independent top-product forecasts are not reconciled to the aggregate.

The top-eight product cohort is selected by sold units available at the final forecast origin. Its historical test results describe that retrospectively selected cohort, not a prospective assessment of every catalog product. The aggregate evaluation does not depend on selecting a product cohort.
