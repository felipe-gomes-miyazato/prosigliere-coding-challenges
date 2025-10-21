-- Postgres schema for Data Warehouse (sales-focused)
-- Run this in your Postgres DW instance to create tables used by the solution

CREATE TABLE IF NOT EXISTS dim_product (
    product_id INTEGER PRIMARY KEY,
    name TEXT,
    category TEXT
);

CREATE TABLE IF NOT EXISTS dim_customer (
    customer_id INTEGER PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    email TEXT
);

CREATE TABLE IF NOT EXISTS dim_time (
    time_id SERIAL PRIMARY KEY,
    order_datetime TIMESTAMP,
    order_date DATE,
    order_hour INTEGER
);

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
