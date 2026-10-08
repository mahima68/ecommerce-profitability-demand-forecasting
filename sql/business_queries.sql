-- PostgreSQL: SET search_path TO retail_portfolio;
-- SQLite: open data/processed/retail.sqlite.
SELECT * FROM product_profitability ORDER BY modeled_contribution_profit DESC LIMIT 10;

SELECT * FROM product_profitability
WHERE net_revenue > 10000 AND modeled_contribution_margin < 0.10 ORDER BY net_revenue DESC;

-- Boundary months may be partial.
SELECT month, modeled_contribution_profit,
       modeled_contribution_profit - LAG(modeled_contribution_profit) OVER (ORDER BY month) AS profit_change
FROM monthly_profitability ORDER BY month;

SELECT product_id,
       SUM(CASE WHEN month = '2011-11' THEN net_revenue ELSE 0 END)
       - SUM(CASE WHEN month = '2011-10' THEN net_revenue ELSE 0 END) AS revenue_change
FROM fact_sales WHERE month IN ('2011-10', '2011-11')
GROUP BY product_id ORDER BY revenue_change LIMIT 10;

-- Expected reconciliation error is close to zero.
SELECT SUM(net_revenue - assumed_cogs - assumed_marketplace_fees
           - assumed_advertising - modeled_contribution_profit) AS reconciliation_error
FROM fact_sales;
