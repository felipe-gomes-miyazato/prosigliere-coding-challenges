from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.log.logging_mixin import LoggingMixin
from datetime import datetime, timedelta
from etl.transform import load_csv, transform_and_normalize, aggregate_performance
from etl.currency_api import CurrencyClient
from etl.load_postgres import (
    get_conn, init_dw, upsert_dim_products, upsert_dim_customers,
    insert_fact_order_items, upsert_agg_products, upsert_agg_hourly,
    upsert_dim_time
)
from pathlib import Path

logger = LoggingMixin().log

def extract_from_sources(**kwargs):
    from etl.load_postgres import get_conn
    logger.info("Starting data extraction from source databases")
    
    db1 = dict(host='postgres_db1', port=5432, dbname='ecommerce_orders', user='postgres', password='postgres')
    db2 = dict(host='postgres_db2', port=5432, dbname='ecommerce_products', user='postgres', password='postgres')
    
    conn_db1 = get_conn(**db1)
    conn_db2 = get_conn(**db2)
    
    data = {}
    
    with conn_db1.cursor() as cur:
        logger.info("Extracting from DB1")
        cur.execute("SELECT * FROM orders")
        data['orders'] = cur.fetchall()
        cur.execute("SELECT * FROM customers")
        data['customers'] = cur.fetchall()
        cur.execute("SELECT * FROM order_items")
        data['order_items'] = cur.fetchall()
    
    with conn_db2.cursor() as cur:
        logger.info("Extracting from DB2")
        cur.execute("SELECT * FROM product_descriptions")
        data['products'] = cur.fetchall()
    
    logger.info("Data extraction complete", extra={
        "orders": len(data['orders']),
        "customers": len(data['customers']),
        "order_items": len(data['order_items']),
        "products": len(data['products'])
    })
    return data

def transform_data(**kwargs):
    from etl.transform import transform_and_normalize
    from etl.currency_api import CurrencyClient
    
    ti = kwargs['task_instance']
    data = ti.xcom_pull(task_ids='extract_from_sources')
    logger.info("Starting data transformation")
    
    client = CurrencyClient()
    transformed_data = transform_and_normalize(data, client)
    
    logger.info("Data transformation complete", extra={
        "dimensions": {k: len(v) for k,v in transformed_data.items() if k != 'facts'}
    })
    return transformed_data

def load_dimensions(**kwargs):
    from etl.load_postgres import get_conn, upsert_dim_products, upsert_dim_customers, upsert_dim_time
    
    ti = kwargs['task_instance']
    data = ti.xcom_pull(task_ids='transform_data')
    logger.info("Loading dimension tables")
    
    dw = dict(host='postgres_warehouse', port=5432, dbname='data_warehouse', user='postgres', password='postgres')
    conn = get_conn(**dw)
    
    with conn:
        upsert_dim_products(conn, data['products'])
        upsert_dim_customers(conn, data['customers'])
        upsert_dim_time(conn, data['time'])
    
    logger.info("Dimension tables loaded successfully")

def load_facts(**kwargs):
    from etl.load_postgres import get_conn, insert_fact_order_items
    
    ti = kwargs['task_instance']
    data = ti.xcom_pull(task_ids='transform_data')
    logger.info("Loading fact table")
    
    dw = dict(host='postgres_warehouse', port=5432, dbname='data_warehouse', user='postgres', password='postgres')
    conn = get_conn(**dw)
    
    with conn:
        insert_fact_order_items(conn, data['facts'])
    
    logger.info("Fact table loaded successfully", extra={"rows": len(data['facts'])})

def update_aggregates(**kwargs):
    from etl.load_postgres import get_conn, upsert_agg_products, upsert_agg_hourly
    from etl.transform import aggregate_performance
    
    logger.info("Updating aggregate tables")
    
    dw = dict(host='postgres_warehouse', port=5432, dbname='data_warehouse', user='postgres', password='postgres')
    conn = get_conn(**dw)
    
    with conn:
        upsert_agg_products(conn)
        upsert_agg_hourly(conn)
    
    logger.info("Aggregate tables updated successfully")

# DAG definition
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'ecommerce_etl_to_postgres',
    default_args=default_args,
    description='ETL from source databases to data warehouse',
    schedule_interval=timedelta(days=1),
    start_date=datetime(2025, 10, 22),
    catchup=False,
    tags=['ecommerce', 'etl'],
)

# Create tasks
extract_task = PythonOperator(
    task_id='extract_from_sources',
    python_callable=extract_from_sources,
    provide_context=True,
    dag=dag,
)

transform_task = PythonOperator(
    task_id='transform_data',
    python_callable=transform_data,
    provide_context=True,
    dag=dag,
)

load_dimensions_task = PythonOperator(
    task_id='load_dimensions',
    python_callable=load_dimensions,
    provide_context=True,
    dag=dag,
)

load_facts_task = PythonOperator(
    task_id='load_facts',
    python_callable=load_facts,
    provide_context=True,
    dag=dag,
)

update_aggregates_task = PythonOperator(
    task_id='update_aggregates',
    python_callable=update_aggregates,
    provide_context=True,
    dag=dag,
)

# Set task dependencies
extract_task >> transform_task >> [load_dimensions_task, load_facts_task] >> update_aggregates_task

def run_etl_to_postgres(**kwargs):
    """ETL process to extract from source DBs, transform, and load into Postgres DW."""
    # In container network, hostnames are the service names from docker-compose
    db1 = dict(host='postgres_db1', port=5432, dbname='ecommerce_orders', user='postgres', password='postgres')
    db2 = dict(host='postgres_db2', port=5432, dbname='ecommerce_products', user='postgres', password='postgres')
    dw = dict(host='postgres_warehouse', port=5432, dbname='data_warehouse', user='postgres', password='postgres')

    # Read data directly from source databases
    conn_db1 = get_conn(**db1)
    conn_db2 = get_conn(**db2)

    with conn_db1.cursor() as cur:
        cur.execute("SELECT * FROM orders")
        orders = cur.fetchall()
        cur.execute("SELECT * FROM customers")
        customers = cur.fetchall()
        cur.execute("SELECT * FROM order_items")
        order_items = cur.fetchall()
        
    # Source DB2 contains product_descriptions (init_db2.sql). Select and alias base_price->price
    with conn_db2.cursor() as cur:
        cur.execute("SELECT id, name, category, description, base_price AS price, currency FROM product_descriptions")
        products = cur.fetchall()
        
    conn_db1.close()
    conn_db2.close()

    cc = CurrencyClient()
    dim_p, dim_c, facts = transform_and_normalize(orders, order_items, products, customers, cc)
    prod_rows, hour_rows = aggregate_performance(facts)

    # Load into DW
    conn = get_conn(**dw)
    init_dw(conn)

    # First, populate dimensions
    # Ensure dim tables contain entries for all referenced product/customer IDs
    fact_product_ids = {f['product_id'] for f in facts}
    dim_product_ids = {p['product_id'] for p in dim_p}
    missing_product_ids = fact_product_ids - dim_product_ids
    placeholder_products = [{'product_id': pid, 'name': f'unknown_{pid}', 'category': None} for pid in missing_product_ids]

    fact_customer_ids = {f['customer_id'] for f in facts}
    dim_customer_ids = {c['customer_id'] for c in dim_c}
    missing_customer_ids = fact_customer_ids - dim_customer_ids
    placeholder_customers = [{'customer_id': cid, 'first_name': None, 'last_name': None, 'email': None} for cid in missing_customer_ids]

    # Upsert known products/customers first, then placeholders so FK constraints won't block fact inserts
    if dim_p:
        upsert_dim_products(conn, dim_p)
    if placeholder_products:
        upsert_dim_products(conn, placeholder_products)

    if dim_c:
        upsert_dim_customers(conn, dim_c)
    if placeholder_customers:
        upsert_dim_customers(conn, placeholder_customers)

    # Extract unique timestamps and populate time dimension
    unique_times = {fact['order_datetime'] for fact in facts}
    time_rows = []
    for dt in unique_times:
        time_rows.append({
            'order_datetime': dt,
            'order_date': dt.date(),
            'order_hour': dt.hour,
            'year': dt.year,
            'month': dt.month,
            'day': dt.day,
            'day_of_week': dt.isoweekday()
        })
    upsert_dim_time(conn, time_rows)

    # Now load facts with time dimension references
    insert_fact_order_items(conn, facts)

    # Finally, update aggregations
    upsert_agg_products(conn, prod_rows)
    upsert_agg_hourly(conn, hour_rows)

    conn.close()


default_args = {
'owner': 'airflow',
'depends_on_past': False,
'retries': 1,
'retry_delay': timedelta(minutes=5),
}

with DAG('ecommerce_etl_to_postgres', start_date=datetime(2025,1,1), schedule_interval='@daily', default_args=default_args, catchup=False) as dag:
    run_etl = PythonOperator(
        task_id='run_etl_to_postgres',
        python_callable=run_etl_to_postgres,
        provide_context=True
    )
