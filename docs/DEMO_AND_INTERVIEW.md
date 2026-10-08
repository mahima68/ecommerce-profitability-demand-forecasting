# Five-minute portfolio demo

1. **Overview:** explain why revenue alone is insufficient. Show the latest complete month, observed revenue, modeled margin, and the accounting bridge. State that costs are assumed.
2. **Products:** identify promotion candidates and high-revenue products with weak margins. Explain why ad attribution and actual costs are needed before acting.
3. **Forecast:** show the baseline comparison, separate validation/test windows, and the four-week forecast as of December 2011. Explain why the selected model can lose to a baseline on the test set.
4. **Pricing:** move the price slider and compare elasticity assumptions. Explain the fixed unit cost and independent advertising spend budget.
5. **Experiment:** show the sample-size calculator and clearly label the seeded simulation. Distinguish statistical evidence from a useful profit lift.
6. **Analyst:** ask “Why did profitability fall in 2011-01?” Expand the selected analysis. Show that displayed figures come from Python functions.

## Questions to be ready for

**How did you obtain costs?** The public dataset has none. I modeled an explicit illustrative cost scenario, separated observed facts from assumptions, and documented the actual cost tables needed for operational deployment.

**How did you handle returns?** I retained negative quantities, reversed revenue, modeled configurable inventory recovery and fee refunds, and separately reported return-only products that lack a price reference.

**How did you handle duplicates?** I discovered that both year sheets repeat December 2010 transactions. I removed exact repeated snapshots across sheets with occurrence ranks, preserving the maximum line multiplicity per record. Remaining within-sheet duplicates are ambiguous without unique source line IDs, so I counted and retained them and documented the sensitivity risk.

**How did you avoid forecast leakage?** Forecast features are built from preceding weeks at each rolling origin. Model selection uses 16 validation weeks; the following 8 weeks are a separate test. The profit cost reference uses full history and is explicitly descriptive, not a leakage-free historical cost forecast.

**Why not use a more complicated forecast?** The baseline is competitive. I selected by a prespecified validation metric and reported test performance honestly. More history and holiday/availability data would be needed to establish robustness.

**Does the pricing simulator predict outcomes?** It calculates conditional scenarios under assumed elasticity. It is not a causal estimate. A randomized experiment with actual financial metrics is needed to validate a price change.

**What does the AI do?** The optional LLM converts the question into a strictly structured, allowlisted analysis call. Python executes it and renders the numeric answer. A local rules-based mode works without an API key. Live AI has to be tested with an account before claiming a production integration.

## Resume wording

Use only claims you can explain and demonstrate:

- Built an e-commerce decision dashboard over 1.07M historical retail transactions, combining auditable cleaning, SQL profitability views, pricing sensitivity, and product analysis under explicit cost assumptions.
- Evaluated three weekly forecasting methods with rolling validation and a separate eight-week test, reporting 17.1% test WAPE for the validation-selected seasonal ridge model alongside stronger baseline test results.
- Implemented a seeded customer-level experiment demonstration and an allowlisted analysis assistant that renders financial results from deterministic Python calculations.

Do not claim actual business profit improvement, a real randomized trial, live GenAI validation, or public deployment until those have occurred.
