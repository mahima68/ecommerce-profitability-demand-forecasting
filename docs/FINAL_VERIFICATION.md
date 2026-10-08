# Final verification — 9 October 2026

Two separate clean environments rebuilt the project from the original UCI workbook. **55 tests passed in each environment.** Both dependency checks passed.

Each review independently reconstructed the cleaning rules, all nine financial/unit metrics by month, product and country, forecast model equations and selection, and Welch tests and confidence intervals. Both SQLite databases and the real PostgreSQL database reconciled. The two rebuilt datasets match every value and type in the published dataset; twelve core reports match byte for byte.

A missing preceding month previously allowed a misleading sales-change comparison. The calculation now rejects it, and the dashboard explains why. Regression tests cover both behaviors. The old validation report was also replaced.

The public dashboard was previously verified. Rechecking the reviewed correction on the hosted app is in progress. Detailed evidence: `reports/final_verification.json`.

Costs remain explicit assumptions, the experiment is simulated, and forecasts concern historical 2011 data. Paid OpenAI calls are disabled and were not tested live. Docker runtime and Power BI Desktop rendering are optional and unvalidated; Power BI was skipped by request. These checks cannot guarantee that no future error will occur.
