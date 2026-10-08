# Final verification — 9 October 2026

Two separate clean environments rebuilt the project from the original UCI workbook. **55 tests passed in each environment.** Both dependency checks passed.

Each review independently reconstructed the cleaning rules, all nine financial/unit metrics by month, product and country, forecast model equations and selection, and Welch tests and confidence intervals. Both SQLite databases and the real PostgreSQL database reconciled. The two rebuilt datasets match every value and type in the published dataset; twelve core reports match byte for byte.

A missing preceding month previously allowed a misleading sales-change comparison. The calculation now rejects it, and the dashboard explains why. Regression tests cover both behaviors. The old validation report was also replaced.

GitHub CI passed for reviewed commit `21cb6bfc1d3fec2136e1f43f82d8b86e6051e8e5`. Two repository hash checks and two integrity/exclusion checks of each downloadable archive passed. The hosting automatic reload produced an import error; a user-authorized full restart recovered the app. All seven pages then passed two complete live reviews. Additional controls verified the 7% pricing scenario (£390,444 modeled profit), free analyst profit bridge (£101,057.82 decline), unsupported future-forecast warning, and corrected missing-month comparison message. No current error was observed in these checks. Detailed evidence: `reports/final_verification.json`.

Costs remain explicit assumptions, the experiment is simulated, and forecasts concern historical 2011 data. Paid OpenAI calls are disabled and were not tested live. Docker runtime and Power BI Desktop rendering are optional and unvalidated; Power BI was skipped by request. These checks cannot guarantee that no future error will occur.
