import csv
import datetime
from pathlib import Path
from .currency_api import CurrencyClient


def load_csv(path):
    rows = []
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def transform_and_normalize(orders, products, customers, currency_client: CurrencyClient):
    """Transform database rows into DW-ready fact and dimension rows.
    
    Args:
        orders: List of tuples from orders table (id, customer_id, order_date, total_amount, currency, status)
        products: List of tuples from products table (id, name, category)
        customers: List of tuples from customers table (id, name, email, registration_date, country)
    
    Outputs:
        - dim_product list
        - dim_customer list
        - fact_order_item list
        - dim_time list
    """
    # Convert tuples to dictionaries for easier processing
    product_map = {p[0]: {'product_id': p[0], 'name': p[1], 'category': p[2]} for p in products}
    customer_map = {c[0]: {'customer_id': c[0], 'name': c[1], 'email': c[2]} for c in customers}

    dim_product = []
    for p in products:
        dim_product.append({
            'product_id': p[0],
            'name': p[1],
            'category': p[2]
        })

    dim_customer = []
    for c in customers:
        dim_customer.append({
            'customer_id': int(c['customer_id']),
            'first_name': c['first_name'],
            'last_name': c['last_name'],
            'email': c.get('email')
        })

    fact_rows = []
    for o in orders:
        odt = datetime.datetime.fromisoformat(o['order_datetime'])
        order_date = odt.date()
        currency = o.get('currency', 'USD')
        rate = currency_client.get_rate(order_date, currency, 'USD')
        price = float(o['price'])
        quantity = int(o['quantity'])
        price_usd = round(price * rate, 2)
        revenue_usd = round(price_usd * quantity, 2)
        fact_rows.append({
            'order_id': int(o['order_id']),
            'product_id': int(o['product_id']),
            'customer_id': int(o['customer_id']),
            'quantity': quantity,
            'price': price,
            'currency': currency,
            'price_usd': price_usd,
            'revenue_usd': revenue_usd,
            'order_datetime': odt
        })

    return dim_product, dim_customer, fact_rows


def aggregate_performance(fact_rows):
    prod_agg = {}
    hour_agg = {}
    for r in fact_rows:
        pid = r['product_id']
        prod_agg.setdefault(pid, {'total_quantity':0,'total_revenue_usd':0.0})
        prod_agg[pid]['total_quantity'] += r['quantity']
        prod_agg[pid]['total_revenue_usd'] += r['revenue_usd']

        hour = r['order_datetime'].hour
        hour_agg.setdefault(hour, {'total_quantity':0,'total_revenue_usd':0.0})
        hour_agg[hour]['total_quantity'] += r['quantity']
        hour_agg[hour]['total_revenue_usd'] += r['revenue_usd']

    prod_rows = [{'product_id':k,'total_quantity':v['total_quantity'],'total_revenue_usd':round(v['total_revenue_usd'],2)} for k,v in prod_agg.items()]
    hour_rows = [{'order_hour':k,'total_quantity':v['total_quantity'],'total_revenue_usd':round(v['total_revenue_usd'],2)} for k,v in hour_agg.items()]
    return prod_rows, hour_rows
