# E-commerce Profitability & Forecasting System

## Business problem
Revenue alone does not identify profitable products. This historical retail case study combines observed sales with transparent cost scenarios, forecasts, and a simulated price experiment to support product and pricing decisions.

## Data and accounting scope
The UCI Online Retail II workbook contains 1,067,371 rows across two sheets. The December 2010 sheets overlap: 22,523 repeated snapshot lines are removed using exact record matches and occurrence ranks, preserving each sheet's within-record multiplicity. The pipeline models 1,032,897 merchandise lines after separately reporting 6,030 invalid lines, 5,900 non-merchandise lines, and 21 return-only lines without a reference cost. The row partition reconciles. Remaining duplicate-looking lines are retained and counted (11,812) because there is no invoice-line identifier.

Observed modeled-scope net revenue is £18,980,392.51. Modeled contribution profit is £3,368,752.40. Costs are synthetic: unit cost is 55% of each product's median positive-sale price, marketplace fees are 15% of positive sales (less the configured fee refund), and advertising allocation is 8% of positive sales. Returned inventory recovers 100% of assumed cost. These assumptions do not describe actual retailer costs.

## Findings from the executed pipeline
- Highest modeled-profit product: 22423 (REGENCY CAKESTAND 3 TIER), with £314,513.47 net revenue and £62,581.75 modeled profit over the dataset.
- Latest complete calendar month: 2011-11, with £1,432,731.70 net revenue, £340,953.05 modeled profit, and 23.8% modeled margin.
- Its modeled profit changed by £153,308.55 versus 2011-10. The bridge reconciles revenue, COGS, marketplace fee, and advertising changes. It does not prove causes.
- Largest month-over-month modeled-profit decline among complete months: 2010-12, at £-139,507.58. The net-revenue effect was £-640,154.15. Seasonal demand and missing inventory/exposure data limit causal explanations.

## Forecast evaluation
Three candidates are compared: a recent four-week mean, a 52-week seasonal naive forecast, and ridge regression with Fourier seasonality, trend, and lag features. Six rolling four-week origins are used. The first four origins select the model by MAE; the last two form an eight-week test with the selection fixed.

Selected aggregate model: **Seasonal ridge**. Validation MAE: 21,632 units. Test MAE: 27,000 units. Test WAPE: 17.1%. Each origin trains only on prior observations. The model is finally refitted on all complete weeks through 2011-12-04.

The recent four-week mean baseline has test WAPE 12.2%. Selection is based on validation only; a more complex model is not guaranteed to outperform the baseline on new periods.

The next four weeks forecast 476,375 sold units and £886,073.43 gross revenue at the trailing 13-week average selling price. This is a historical demonstration, not a forecast for 2026. Ranges use absolute validation errors with only four observations per horizon; coverage is not guaranteed. Returns, stock constraints, promotion effects, and net profit are not forecast. Top-product forecasts are independent and do not reconcile to the aggregate.

## Pricing sensitivity
For the latest complete month, a +5% price scenario changes modeled profit by £60,703.52 with elasticity 0, £36,023.71 with elasticity -1, and £12,519.13 with elasticity -2. COGS per unit stays fixed, return proportions stay fixed, and advertising is separately adjustable. Elasticity is an assumption, not an estimate from observational data. Use the sensitivity to design a real test.

## Experiment demonstration
A seeded synthetic customer-level experiment assigns 10,000 customers to control and 10,000 to treatment. The primary metric is contribution profit per assigned customer, analyzed with a Welch interval/test. Revenue and conversion are exploratory. Simulated decision: **Meets simulated primary-metric rule**. No real experiment is claimed.

## Practical recommendations
1. Validate actual supplier costs, fees, fulfillment costs, and ad spend before acting on modeled rankings.
2. Investigate low-margin and return-heavy products, then test one price change with customer-level randomization and a prespecified profit metric.
3. Use the baseline comparison and test errors when choosing a forecast; investigate availability and holiday effects before buying inventory from it.

## Implementation
Python/Pandas own calculations. SQLite stores the portable demo. PostgreSQL schema, bulk loading, and matching views support optional database deployment. Streamlit presents product, country, pricing, forecasting, experimentation, and analysis-assistant views. The optional OpenAI planner selects an allowlisted Python function; rendered financial numbers come from deterministic calculations.

## Source
Chen, D. (2012). Online Retail II [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5CG6D. CC BY 4.0. Source page: https://archive.ics.uci.edu/dataset/502/online+retail+ii
