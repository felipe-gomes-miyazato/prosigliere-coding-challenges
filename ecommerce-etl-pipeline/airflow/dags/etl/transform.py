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


def _row_to_dict(row, columns):
    if row is None:
        return None
    if isinstance(row, dict):
        return {col: row.get(col) for col in columns}
    return {col: row[idx] for idx, col in enumerate(columns)}


def transform_and_normalize(orders, order_items, products, customers, currency_client: CurrencyClient):
    """Minimal, robust transform: accepts tuple or dict rows from the DB and returns
    (dim_product, dim_customer, fact_rows).
    """
    cust_cols = ['id', 'name', 'email', 'registration_date', 'country']
    order_cols = ['id', 'customer_id', 'order_date', 'total_amount', 'currency', 'status']
    item_cols = ['id', 'order_id', 'product_id', 'quantity', 'unit_price', 'currency']
    prod_cols = ['id', 'name', 'category', 'description', 'price', 'currency']

    dim_product = []
    for p in products:
        pd = _row_to_dict(p, prod_cols)
        pid = int(pd['id'])
        dim_product.append({'product_id': pid, 'name': pd.get('name'), 'category': pd.get('category')})

    dim_customer = []
    for c in customers:
        cd = _row_to_dict(c, cust_cols)
        cid = int(cd['id'])
        name_parts = (cd.get('name') or '').split(None, 1)
        first_name = name_parts[0] if name_parts else ''
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        dim_customer.append({'customer_id': cid, 'first_name': first_name, 'last_name': last_name, 'email': cd.get('email')})

    order_map = {}
    for o in orders:
        od = _row_to_dict(o, order_cols)
        oid = int(od['id'])
        odt = od['order_date']
        if isinstance(odt, str):
            try:
                odt = datetime.datetime.fromisoformat(odt)
            except Exception:
                odt = datetime.datetime.strptime(odt, '%Y-%m-%d %H:%M:%S')
        order_map[oid] = {'order_datetime': odt, 'currency': od.get('currency', 'USD'), 'customer_id': int(od.get('customer_id'))}

    fact_rows = []
    for it in order_items:
        ir = _row_to_dict(it, item_cols)
        order_id = int(ir['order_id'])
        product_id = int(ir['product_id'])
        quantity = int(ir['quantity'])
        unit_price = float(ir['unit_price'])
        order_info = order_map.get(order_id)
        if not order_info:
            continue
        odt = order_info['order_datetime']
        currency = ir.get('currency') or order_info.get('currency') or 'USD'
        rate = currency_client.get_rate(odt.date(), currency, 'USD')
        price_usd = round(unit_price * rate, 2)
        revenue_usd = round(price_usd * quantity, 2)
        fact_rows.append({
            'order_id': order_id,
            'product_id': product_id,
            'customer_id': order_info['customer_id'],
            'quantity': quantity,
            'price': unit_price,
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
        prod_agg.setdefault(pid, {'total_quantity': 0, 'total_revenue_usd': 0.0})
        prod_agg[pid]['total_quantity'] += r['quantity']
        prod_agg[pid]['total_revenue_usd'] += r['revenue_usd']

        hour = r['order_datetime'].hour
        hour_agg.setdefault(hour, {'total_quantity': 0, 'total_revenue_usd': 0.0})
        hour_agg[hour]['total_quantity'] += r['quantity']
        hour_agg[hour]['total_revenue_usd'] += r['revenue_usd']

    prod_rows = [{'product_id': k, 'total_quantity': v['total_quantity'], 'total_revenue_usd': round(v['total_revenue_usd'], 2)} for k, v in prod_agg.items()]
    hour_rows = [{'order_hour': k, 'total_quantity': v['total_quantity'], 'total_revenue_usd': round(v['total_revenue_usd'], 2)} for k, v in hour_agg.items()]
    return prod_rows, hour_rows
