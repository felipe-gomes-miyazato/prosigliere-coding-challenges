# Design Process

## Objective
Deliver a Data Warehouse schema and an Airflow-based ETL pipeline to answer two business questions: top-performing products (volume & revenue) and optimal time of day for promotions.

## High-level approach
- Use a star schema with small, focused dimension tables and a fact table for order items. This keeps queries simple and performant for analytical workloads.
- Normalize currency during transform (convert to USD) so downstream analysis compares revenue consistently.
- Build aggregate tables for product and hourly performance to speed up dashboard queries.
- Orchestrate with a single Airflow DAG (PythonOperator) that extracts from source DBs, transforms data into dimensional rows, and upserts into the DW.

## Key design decisions
- Dimensions: `dim_product`, `dim_customer`, `dim_time` (time granularity to hour). The `dim_time.order_datetime` is indexed/unique to support upsert by timestamp.
- Fact: `fact_order_item` stores an order-level snapshot for each order item with both original currency price and `price_usd`/`revenue_usd`.
- Aggregates: `agg_product_performance`, `agg_hourly_performance` maintained by ETL to answer the challenge questions quickly.
- Upsert strategy: use `INSERT ... ON CONFLICT` for idempotent loads of dimensions and aggregates.

## Transformation logic highlights
- Parse and normalize input rows (support tuple/dict shapes because the source SQL drivers return tuples by default).
- Join `order_items` to `orders` to build fact-level rows with price and revenue per item.
- Call CurrencyClient to obtain historical exchange rates and compute USD equivalents.
- Produce `dim_*` rows and `fact` rows; aggregate to product/hour tables as a final step.

## Assumptions
- Source DBs follow the column order in `database/init_db1.sql` and `init_db2.sql`.
- Currency API is available or falls back to demo rates implemented in `currency_api.py`.
- ETL runs in the Airflow container; host machine may not have Airflow/psycopg2 installed (so local imports may fail).

## Running & verification
- Start Docker Compose (provided in repo) and ensure containers are up.
- Enter the Airflow container and run a Python session to import the DAG: `docker exec -it <airflow_webserver> bash` and run a quick Python import to validate dependencies.
- Alternatively, run the DAG from the Airflow UI and monitor task logs.

## Next steps / improvements
- Add unit tests for transform logic (edge cases: missing currency, malformed timestamps, duplicate orders).
- Add schema migrations (e.g., using Flyway or alembic) instead of raw DDL in files.
- Add monitoring/alerting for ETL failures and data drift checks.


*Generated as part of the coding challenge solution.*