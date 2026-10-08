CREATE SCHEMA IF NOT EXISTS retail_portfolio;
CREATE TABLE IF NOT EXISTS retail_portfolio.fact_sales (
    line_id BIGINT PRIMARY KEY,
    invoice TEXT NOT NULL, product_id TEXT NOT NULL, description TEXT NOT NULL,
    date TIMESTAMP NOT NULL, month TEXT NOT NULL, week TIMESTAMP NOT NULL, country TEXT NOT NULL,
    quantity DOUBLE PRECISION NOT NULL, unit_price DOUBLE PRECISION NOT NULL CHECK (unit_price > 0),
    is_return BOOLEAN NOT NULL,
    reference_price DOUBLE PRECISION NOT NULL, assumed_unit_cost DOUBLE PRECISION NOT NULL,
    gross_revenue DOUBLE PRECISION NOT NULL, refunds DOUBLE PRECISION NOT NULL, net_revenue DOUBLE PRECISION NOT NULL,
    sold_units DOUBLE PRECISION NOT NULL, returned_units DOUBLE PRECISION NOT NULL,
    assumed_cogs DOUBLE PRECISION NOT NULL, assumed_marketplace_fees DOUBLE PRECISION NOT NULL,
    assumed_advertising DOUBLE PRECISION NOT NULL, modeled_contribution_profit DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_product_month ON retail_portfolio.fact_sales(product_id, month);
