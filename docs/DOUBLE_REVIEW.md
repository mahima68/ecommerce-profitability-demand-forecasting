# E-commerce Profitability & Forecasting System — double review

Two review passes completed from the original UCI workbook before GitHub upload. No upload has been performed.

## Pass 1: clean rebuild and financial review

Created a separate copy with no previous processed data or generated reports. Rebuilt directly from `online_retail_II.xlsx`, then generated Power BI files. Checked exclusions, cross-sheet overlap, returns, assumed costs, complete periods, pricing, and the accounting bridge. Ran the full suite in a freshly installed Python environment: **51 tests passed**.

## Pass 2: second clean rebuild and independent checks

Created another empty-data copy and rebuilt directly from the workbook. All 16 core reports match the first pass byte for byte. Both processed Parquet files and SQLite databases also match byte for byte. The second copy passed **51 tests** in a separate test process using the fresh environment. Dependency checks found no conflicts.

Separate audit code, without importing the project's calculation functions, independently reconstructed cross-sheet record multiplicities, product reference costs, financial amounts, monthly/product/country totals, rolling forecast predictions (including a separate NumPy ridge solution), Welch p-values and intervals, and full SQLite totals. All checks agree. A read-only comparison against PostgreSQL 18.6 verified all nine additive metrics by month, product, and country on **1,032,897 rows**.

Each Power BI rebuild passed **39 Microsoft JSON schema checks**. Browser checks confirmed November 2011 totals, a top-five result with five rows, and an explicit message for unavailable forecasts. The source workbook checksum and structured evidence are saved in `reports/double_review.json` and `reports/build_manifest.json`.

## Issues fixed

- Local analyst now respects explicit result counts such as “top 5.”
- Price-decrease wording such as “price drops by 5%” no longer becomes an increase.
- Forecast requests for unavailable months no longer silently return a different historical period.
- Planner numeric arguments reject booleans.
- Experiment analysis rejects missing customer IDs and invalid significance/business thresholds.
- Rolling forecast origin labels now show the Sunday through which training data was observed.
- Docker dashboard configuration no longer depends on the optional database password. The separate PostgreSQL configuration retains its nonempty-password requirement.
- Docker build exclusions protect secret files and avoid copying raw workbooks, SQLite, audit exceptions, or Power BI files into the image.
- Project title standardized to **E-commerce Profitability & Forecasting System**.

## Remaining verification limits

Power BI Desktop refresh/rendering, live OpenAI API requests, Docker runtime execution, remain unverified. This review does not declare those integrations complete. Profitability uses assumed costs; pricing uses assumed elasticity; the experiment is simulated; forecasts concern December 2011 rather than the present day. The validation-selected forecasting model did not beat the recent-mean baseline on the test set, and both results remain visible.

## Free project scope update

After the two rebuild reviews, private key setup was added and the paid planner was disabled by default behind explicit server opt-in. The current full suite passes 53 tests. The chosen project uses Streamlit and the deterministic local analyst; Power BI, paid OpenAI requests, and Docker are optional. Live GenAI is not claimed as validated. GitHub upload is complete, all 118 initially published files matched their local blob checksums, and its initial automated check passed. The dashboard is deployed on Streamlit Community Cloud; all seven pages, a changed pricing scenario, a calculated local analyst answer, and unavailable-date handling were verified. The deployed Python 3.12 runtime uses PyArrow 24.0.0, now pinned in requirements; the 53-test local suite passes with this version.
