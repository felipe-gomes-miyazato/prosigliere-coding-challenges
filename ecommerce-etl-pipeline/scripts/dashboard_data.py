import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta

def get_warehouse_conn():
    """Connect to the data warehouse"""
    return psycopg2.connect(
        host="localhost",
        port=5434,  # warehouse port from docker-compose
        dbname="data_warehouse",
        user="postgres",
        password="postgres",
        cursor_factory=RealDictCursor,
        application_name='dashboard_mockup'  # For debugging connection issues
    )

def fetch_daily_kpis(conn):
    """Fetch KPIs for all time since we're just starting"""
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            COALESCE(SUM(quantity * price_usd), 0) as total_revenue,
            COALESCE(COUNT(DISTINCT order_id), 0) as total_orders,
            COALESCE(ROUND(AVG(price_usd), 2), 0) as avg_order_value
        FROM fact_order_item
    """)
    result = cur.fetchone()
    
    # Log the results for debugging
    print("KPI Query Results:", dict(result))
    return result

def fetch_top_products(conn, limit=5):
    """Fetch top products by revenue"""
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            p.name,
            SUM(f.quantity) as total_units,
            SUM(f.quantity * f.price_usd) as total_revenue
        FROM fact_order_item f
        JOIN dim_product p ON p.product_id = f.product_id
        GROUP BY p.product_id, p.name
        ORDER BY total_revenue DESC
        LIMIT %s
    """, (limit,))
    return cur.fetchall()

def fetch_hourly_revenue(conn):
    """Fetch revenue by hour aggregated across all days"""
    cur = conn.cursor()
    cur.execute("""
        WITH hours AS (
            SELECT generate_series(0, 23) as hour
        )
        SELECT 
            h.hour,
            COALESCE(SUM(f.quantity * f.price_usd), 0) as revenue
        FROM hours h
        LEFT JOIN fact_order_item f ON 
            EXTRACT(HOUR FROM f.order_datetime) = h.hour
        GROUP BY h.hour
        ORDER BY h.hour
    """)
    result = cur.fetchall()
    
    # Log the results for debugging
    print("Hourly Revenue Results:", [dict(row) for row in result])
    return result

def fetch_revenue_heatmap(conn):
    """Fetch revenue heatmap data (day of week vs hour)"""
    cur = conn.cursor()
    cur.execute("""
        WITH RECURSIVE
        days AS (
            SELECT generate_series(0, 6) as day_of_week
        ),
        hours AS (
            SELECT generate_series(0, 23) as hour
        ),
        day_hour_grid AS (
            SELECT day_of_week, hour
            FROM days CROSS JOIN hours
        )
        SELECT 
            g.day_of_week,
            g.hour,
            COALESCE(SUM(f.quantity * f.price_usd), 0) as revenue
        FROM day_hour_grid g
        LEFT JOIN fact_order_item f ON 
            EXTRACT(DOW FROM f.order_datetime) = g.day_of_week AND
            EXTRACT(HOUR FROM f.order_datetime) = g.hour AND
            f.order_datetime >= NOW() - INTERVAL '7 days'
        GROUP BY 
            g.day_of_week,
            g.hour
        ORDER BY g.day_of_week, g.hour
    """)
    return cur.fetchall()

def format_currency(value):
    """Format currency values to k notation"""
    if value is None:
        return '$0.00'
    if value >= 1000:
        return f"${value/1000:.1f}k"
    return f"${value:.2f}"

if __name__ == "__main__":
    # Test the functions
    conn = get_warehouse_conn()
    print("KPIs:", fetch_daily_kpis(conn))
    print("\nTop Products:", fetch_top_products(conn))
    print("\nHourly Revenue:", fetch_hourly_revenue(conn))
    print("\nHeatmap Data:", fetch_revenue_heatmap(conn))
    conn.close()