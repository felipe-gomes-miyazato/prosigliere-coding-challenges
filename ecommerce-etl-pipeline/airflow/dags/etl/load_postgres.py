import psycopg2
from psycopg2.extras import execute_values
from pathlib import Path

def get_conn(host, port, dbname, user, password):
    return psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=password)

def init_dw(conn):
    cur = conn.cursor()
    # Execute the DW DDL (already provided in solution/sql/create_dw.sql)
    sql = Path(__file__).resolve().parents[1] / 'sql' / 'create_dw.sql'
    with open(sql, 'r', encoding='utf-8') as f:
        cur.execute(f.read())
    conn.commit()

def upsert_dim_products(conn, rows):
    cur = conn.cursor()
    values = [(r['product_id'], r['name'], r.get('category')) for r in rows]
    execute_values(cur, "INSERT INTO dim_product(product_id,name,category) VALUES %s ON CONFLICT (product_id) DO UPDATE SET name=EXCLUDED.name, category=EXCLUDED.category", values)
    conn.commit()

def upsert_dim_customers(conn, rows):
    cur = conn.cursor()
    values = [(r['customer_id'], r['first_name'], r['last_name'], r.get('email')) for r in rows]
    execute_values(cur, "INSERT INTO dim_customer(customer_id,first_name,last_name,email) VALUES %s ON CONFLICT (customer_id) DO UPDATE SET first_name=EXCLUDED.first_name, last_name=EXCLUDED.last_name, email=EXCLUDED.email", values)
    conn.commit()

def insert_fact_order_items(conn, rows):
    cur = conn.cursor()
    # Ensure order_datetime is a Python datetime for psycopg2 to handle TIMESTAMP correctly.
    # Accept datetimes or ISO strings (defensive), convert strings to Python datetime.
    from datetime import datetime
    def ensure_dt(v):
        if v is None:
            return None
        if isinstance(v, str):
            # try isoformat parse
            try:
                return datetime.fromisoformat(v)
            except Exception:
                return datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
        return v

    values = [(
        r['order_id'],
        r['product_id'],
        r['customer_id'],
        r['quantity'],
        r['price'],
        r['currency'],
        r['price_usd'],
        r['revenue_usd'],
        ensure_dt(r['order_datetime'])
    ) for r in rows]
    execute_values(cur, "INSERT INTO fact_order_item(order_id,product_id,customer_id,quantity,price,currency,price_usd,revenue_usd,order_datetime) VALUES %s", values)
    conn.commit()

def upsert_agg_products(conn, rows):
    cur = conn.cursor()
    values = [(r['product_id'], r['total_quantity'], r['total_revenue_usd']) for r in rows]
    execute_values(cur, "INSERT INTO agg_product_performance(product_id,total_quantity,total_revenue_usd) VALUES %s ON CONFLICT (product_id) DO UPDATE SET total_quantity=EXCLUDED.total_quantity, total_revenue_usd=EXCLUDED.total_revenue_usd", values)
    conn.commit()

def upsert_agg_hourly(conn, rows):
    cur = conn.cursor()
    values = [(r['order_hour'], r['total_quantity'], r['total_revenue_usd']) for r in rows]
    execute_values(cur, "INSERT INTO agg_hourly_performance(order_hour,total_quantity,total_revenue_usd) VALUES %s ON CONFLICT (order_hour) DO UPDATE SET total_quantity=EXCLUDED.total_quantity, total_revenue_usd=EXCLUDED.total_revenue_usd", values)
    conn.commit()

def upsert_dim_time(conn, rows):
    cur = conn.cursor()
    values = [(
        r['order_datetime'],
        r['order_date'],
        r['order_hour'],
        r['year'],
        r['month'],
        r['day'],
        r['day_of_week']
    ) for r in rows]
    execute_values(cur, """
        INSERT INTO dim_time(
            order_datetime,
            order_date,
            order_hour,
            year,
            month,
            day,
            day_of_week
        ) VALUES %s 
        ON CONFLICT (order_datetime) DO UPDATE SET
            order_date=EXCLUDED.order_date,
            order_hour=EXCLUDED.order_hour,
            year=EXCLUDED.year,
            month=EXCLUDED.month,
            day=EXCLUDED.day,
            day_of_week=EXCLUDED.day_of_week
    """, values)
    conn.commit()
