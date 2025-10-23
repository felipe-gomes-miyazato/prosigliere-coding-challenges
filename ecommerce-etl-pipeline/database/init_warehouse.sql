




-- Postgres schema for Data Warehouse (sales-focused)
-- Run this in your Postgres DW instance to create tables used by the solution

-- Dimension tables with proper indexes
CREATE TABLE IF NOT EXISTS dim_product (
    product_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_dim_product_category ON dim_product(category);

CREATE TABLE IF NOT EXISTS dim_customer (
    customer_id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_dim_customer_name ON dim_customer(first_name, last_name);
CREATE INDEX IF NOT EXISTS idx_dim_customer_email ON dim_customer(email);

CREATE TABLE IF NOT EXISTS dim_time (
    time_id SERIAL PRIMARY KEY,
    order_datetime TIMESTAMP NOT NULL,
    order_date DATE NOT NULL,
    order_hour INTEGER NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Add a unique index to allow ON CONFLICT(upsert) on order_datetime
CREATE UNIQUE INDEX IF NOT EXISTS ux_dim_time_order_datetime ON dim_time(order_datetime);
CREATE INDEX IF NOT EXISTS idx_dim_time_date ON dim_time(order_date);
CREATE INDEX IF NOT EXISTS idx_dim_time_components ON dim_time(year, month, day);

-- Fact table with proper indexes and constraints
CREATE TABLE IF NOT EXISTS fact_order_item (
    order_item_id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL,
    product_id INTEGER REFERENCES dim_product(product_id),
    customer_id INTEGER REFERENCES dim_customer(customer_id),
    time_id INTEGER REFERENCES dim_time(time_id),
    quantity INTEGER NOT NULL,
    price NUMERIC(12,2) NOT NULL,
    currency CHAR(3) NOT NULL,
    price_usd NUMERIC(12,2) NOT NULL,
    revenue_usd NUMERIC(12,2) NOT NULL,
    order_datetime TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

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
