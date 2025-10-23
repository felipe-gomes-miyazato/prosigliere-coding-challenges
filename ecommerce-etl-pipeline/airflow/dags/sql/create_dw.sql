-- Postgres schema for Data Warehouse (sales-focused)
-- Run this in your Postgres DW instance to create tables used by the solution

CREATE TABLE IF NOT EXISTS dim_product (
    product_id INTEGER PRIMARY KEY,
    name TEXT,
    category TEXT
);

CREATE INDEX IF NOT EXISTS idx_product_category ON dim_product(category);

CREATE TABLE IF NOT EXISTS dim_customer (
    customer_id INTEGER PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    email TEXT
);

CREATE INDEX IF NOT EXISTS idx_customer_email ON dim_customer(email);

CREATE TABLE IF NOT EXISTS dim_time (
    time_id SERIAL PRIMARY KEY,
    order_datetime TIMESTAMP,
    order_date DATE,
    order_hour INTEGER
);

-- Make order_datetime unique so upserts by order_datetime can use ON CONFLICT
CREATE UNIQUE INDEX IF NOT EXISTS ux_dim_time_order_datetime ON dim_time(order_datetime);

CREATE TABLE IF NOT EXISTS fact_order_item (
    order_item_id SERIAL PRIMARY KEY,
    order_id INTEGER,
    product_id INTEGER REFERENCES dim_product(product_id),
    customer_id INTEGER REFERENCES dim_customer(customer_id),
    quantity INTEGER,
    price NUMERIC(12,2), -- price in original currency
    currency CHAR(3),
    price_usd NUMERIC(12,2), -- normalized to USD
    revenue_usd NUMERIC(12,2),
    order_datetime TIMESTAMP
);

-- Performance indexes for common queries
CREATE INDEX IF NOT EXISTS idx_fact_order_datetime ON fact_order_item(order_datetime);
CREATE INDEX IF NOT EXISTS idx_fact_product ON fact_order_item(product_id);
CREATE INDEX IF NOT EXISTS idx_fact_customer ON fact_order_item(customer_id);
CREATE INDEX IF NOT EXISTS idx_fact_revenue ON fact_order_item(revenue_usd DESC);

-- Convenience aggregated tables
CREATE TABLE IF NOT EXISTS agg_product_performance (
    product_id INTEGER PRIMARY KEY,
    total_quantity BIGINT,
    total_revenue_usd NUMERIC(18,2)
);

CREATE TABLE IF NOT EXISTS agg_hourly_performance (
    order_hour INTEGER PRIMARY KEY,
    total_quantity BIGINT,
    total_revenue_usd NUMERIC(18,2)
);
