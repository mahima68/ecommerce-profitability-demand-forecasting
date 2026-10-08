DROP VIEW IF EXISTS monthly_profitability;
CREATE VIEW monthly_profitability AS
SELECT month, SUM(gross_revenue) AS gross_revenue, SUM(refunds) AS refunds,
       SUM(net_revenue) AS net_revenue, SUM(assumed_cogs) AS assumed_cogs,
       SUM(assumed_marketplace_fees) AS assumed_marketplace_fees,
       SUM(assumed_advertising) AS assumed_advertising,
       SUM(modeled_contribution_profit) AS modeled_contribution_profit,
       CASE WHEN SUM(net_revenue) > 0 THEN SUM(modeled_contribution_profit) / SUM(net_revenue) END AS modeled_contribution_margin
FROM fact_sales GROUP BY month;
DROP VIEW IF EXISTS product_profitability;
CREATE VIEW product_profitability AS
SELECT product_id, SUM(net_revenue) AS net_revenue,
       SUM(modeled_contribution_profit) AS modeled_contribution_profit,
       SUM(sold_units) AS sold_units, SUM(returned_units) AS returned_units,
       CASE WHEN SUM(net_revenue) > 0 THEN SUM(modeled_contribution_profit) / SUM(net_revenue) END AS modeled_contribution_margin
FROM fact_sales GROUP BY product_id;
