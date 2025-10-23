from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

def run_etl_to_postgres(**kwargs):
    # This function will run inside the Airflow container and can reach the Postgres containers
    from etl.transform import load_csv, transform_and_normalize, aggregate_performance
    from etl.currency_api import CurrencyClient
    from etl.load_postgres import get_conn, init_dw, upsert_dim_products, upsert_dim_customers, insert_fact_order_items, upsert_agg_products, upsert_agg_hourly, upsert_dim_time
    from pathlib import Path

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
        
    with conn_db2.cursor() as cur:
        cur.execute("SELECT * FROM products")
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
    upsert_dim_products(conn, dim_p)
    upsert_dim_customers(conn, dim_c)
    
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
