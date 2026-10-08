# Power BI report project

`powerbi/Retail.pbip` is the authored Power BI project. It includes four pages (Overview, Products, Countries, Forecast), financial measures, filter controls, a semantic model, and reconciled CSV data. The report uses Microsoft's supported PBIR format; the semantic model uses TMSL `model.bim`.

The files have been validated against Microsoft's public report JSON schemas. Financial exports reconcile to Python. **The report has not yet been opened, refreshed, or visually checked in Power BI Desktop.** Schema validation cannot confirm visual rendering or successful Power Query/DAX execution. No finished `.pbix` or published report is claimed.

## Open and verify on Windows

1. Copy the entire project folder to the Windows computer, keeping all files inside `powerbi` together.
2. Open `powerbi/Retail.pbip` in current Power BI Desktop. If your installation asks to enable Power BI Project / PBIR support, enable it and restart Desktop.
3. In Transform data → Edit parameters, change `DataFolder` to the absolute path of the copied `powerbi/data` directory.
4. Apply changes and Refresh. The project opens without a cached model, so a refresh is necessary to populate data.
5. With no filters selected, confirm Net Revenue **£18,980,392.51** and Modeled Contribution Profit **£3,368,752.40**. Verify November 2011 net revenue **£1,432,731.70** and modeled profit **£340,953.05**.
6. Check every page, change month/country filters, sort the product table, and verify GBP/percentage formatting. On Forecast, choose `ALL`: predicted units should total approximately **476,375** across the four weeks. Check each individual product separately.
7. Save a `.pbix` copy if desired; publish only after the refresh and visual checks pass.

## Model and limitations

The sales fact grain is month × product × country (126,750 rows), aggregated from the 1,032,897 modeled merchandise lines. Products, Months, and Countries are separate unique-key dimensions with one-to-many, single-direction relationships. Additive values reconcile to the audited full facts. This report cannot drill into invoice/customer transactions because its sales data is aggregated.

The `complete_month` filter marks the partial final month. Select True for complete-month comparisons. Product descriptions use the latest observed description. Cost assumptions are 55% of product reference price, 15% marketplace fees, and 8% advertising; profitability is modeled, not actual business profit.

Forecast is deliberately separate from actual sales. Its aggregate and product series overlap and must not be summed together. Measures use the single selected series or default to the aggregate `ALL` series, including if several products are selected. The forecast is historical, as of December 4, 2011. Its bounds are empirical error ranges with no guaranteed coverage.

Rebuild exports and project definitions using `python src/build_powerbi.py` after rebuilding the main pipeline. Changing source data requires repeating Desktop refresh/render checks. PostgreSQL integration is supplied separately; this report uses portable CSV files and does not require a database connection.

References: [Microsoft PBIR report format](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report), [semantic model project files](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-dataset).
