from PIL import Image, ImageDraw, ImageFont
import os
from dashboard_data import (
    get_warehouse_conn,
    fetch_daily_kpis,
    fetch_top_products,
    fetch_hourly_revenue,
    fetch_revenue_heatmap,
    format_currency
)

# Connect to warehouse and fetch data
conn = get_warehouse_conn()
kpis = fetch_daily_kpis(conn)
top_products = fetch_top_products(conn)
hourly_revenue = fetch_hourly_revenue(conn)
heatmap_data = fetch_revenue_heatmap(conn)

# Wider layout with better spacing and consistent box sizes
W, H = 1280, 800
bg = (255, 255, 255)
card = (245, 247, 250)
accent = (40, 116, 166)
text = (30, 30, 30)
grid = (220, 220, 220)

img = Image.new('RGB', (W, H), color=bg)
d = ImageDraw.Draw(img)

# Fonts: use default PIL font or try arial
try:
    font_h = ImageFont.truetype('arial.ttf', 28)
    font_kpi = ImageFont.truetype('arial.ttf', 24)
    font_text = ImageFont.truetype('arial.ttf', 16)
    font_small = ImageFont.truetype('arial.ttf', 14)
except Exception:
    font_h = ImageFont.load_default()
    font_kpi = ImageFont.load_default()
    font_text = ImageFont.load_default()
    font_small = ImageFont.load_default()

# Header with accent bar
d.rectangle([(0,0),(W,80)], fill=accent)
d.text((30,20), 'eCommerce Analytics Dashboard', font=font_h, fill=(255,255,255))

# KPIs - wider boxes with consistent spacing
kpi_w = 290  # Wider KPI boxes
kpi_h = 100
kpi_gap = 20

# Get top product info
top_product = top_products[0] if top_products else {'name': 'No data', 'total_revenue': 0}

for i, (label, val) in enumerate([
    ('Daily Revenue (USD)', format_currency(kpis['total_revenue'])),
    ('Total Orders', f"{kpis['total_orders']:,}"),
    ('Avg Order Value', format_currency(kpis['avg_order_value'])),
    ('Top Product', f"{top_product['name']}\n{format_currency(top_product['total_revenue'])} revenue")
]):
    x = 30 + i*(kpi_w + kpi_gap)
    y = 100
    # KPI box with subtle shadow
    d.rectangle([(x+2,y+2),(x+kpi_w+2,y+kpi_h+2)], fill=(230,230,230))
    d.rectangle([(x,y),(x+kpi_w,y+kpi_h)], fill=card, outline=grid)
    d.text((x+15,y+15), label, font=font_kpi, fill=text)
    # Multi-line support for values
    if '\n' in val:
        v1, v2 = val.split('\n')
        d.text((x+15,y+50), v1, font=font_text, fill=accent)  # Reduced font for product name
        d.text((x+15,y+75), v2, font=font_text, fill=text)
    else:
        d.text((x+15,y+50), val, font=font_h, fill=accent)

# Left panel: Top Products table (same height as revenue chart)
panel_y = 220
panel_h = 350
left_w = 600

# Add shadow first
d.rectangle([(32,panel_y+2),(32+left_w,panel_y+panel_h+2)], fill=(230,230,230))
d.rectangle([(30,panel_y),(30+left_w,panel_y+panel_h)], fill=card, outline=grid)
d.text((45,panel_y+15), 'Top Products (by Revenue)', font=font_kpi, fill=text)

# Column headers
headers = ['Rank', 'Product', 'Units Sold', 'Revenue (USD)']
header_x = [60, 120, 380, 480]
for x, h in zip(header_x, headers):
    d.text((x,panel_y+60), h, font=font_text, fill=text)

# Table rows with actual data from warehouse
for i, product in enumerate(top_products):
    y = panel_y + 95 + i*40
    row = [
        str(i + 1),
        product['name'],
        f"{product['total_units']:,}",
        format_currency(product['total_revenue'])
    ]
    for val, x in zip(row, header_x):
        d.text((x,y), val, font=font_text, fill=text)

# Right panel: Revenue by Hour chart
right_x = 30 + left_w + 20  # Align with KPI grid
right_w = left_w

# Add shadow first
d.rectangle([(right_x+2,panel_y+2),(right_x+right_w+2,panel_y+panel_h+2)], fill=(230,230,230))
d.rectangle([(right_x,panel_y),(right_x+right_w,panel_y+panel_h)], fill=card, outline=grid)
d.text((right_x+15,panel_y+15), 'Revenue by Hour', font=font_kpi, fill=text)

# Y-axis labels and gridlines
max_revenue = 5000
y_steps = 5
for i in range(y_steps + 1):
    y = panel_y + panel_h - 60 - (i * (panel_h-120)//y_steps)
    val = f'${int(max_revenue * i/y_steps):,}'
    d.text((right_x+15,y-10), val, font=font_small, fill=text)
    # Grid line
    d.line([(right_x+70,y),(right_x+right_w-30,y)], fill=grid)

# Revenue line chart
if hourly_revenue:
    # Setup chart dimensions
    chart_margin = 60
    chart_x = right_x + chart_margin
    chart_y = panel_y + chart_margin
    chart_w = right_w - (chart_margin * 2)
    chart_h = panel_h - (chart_margin * 2)
    
    # Get data points
    hours = [int(row['hour']) for row in hourly_revenue]
    revenues = [float(row['revenue']) for row in hourly_revenue]
    
    # Calculate scales
    max_revenue = max(revenues) if revenues else 0
    min_revenue = min(revenues) if revenues else 0
    y_padding = max_revenue * 0.1  # Add 10% padding
    
    # Draw axes
    d.line([(chart_x, chart_y), (chart_x, chart_y + chart_h)], fill=grid)  # Y-axis
    d.line([(chart_x, chart_y + chart_h), (chart_x + chart_w, chart_y + chart_h)], fill=grid)  # X-axis
    
    # Y-axis labels and gridlines
    num_y_ticks = 5
    for i in range(num_y_ticks + 1):
        y_val = max_revenue * (1 - i/num_y_ticks)
        y_pos = chart_y + (i * chart_h/num_y_ticks)
        # Grid line
        d.line([(chart_x, y_pos), (chart_x + chart_w, y_pos)], fill=grid)
        # Label
        d.text((chart_x - 55, y_pos - 10), format_currency(y_val), font=font_small, fill=text)
    
    # X-axis labels (every 3 hours)
    for hour in range(0, 24, 3):
        x_pos = chart_x + (hour * chart_w/23)  # 23 intervals for 24 hours
        # Label
        d.text((x_pos - 10, chart_y + chart_h + 10), f'{hour}h', font=font_small, fill=text)
    
    # Draw the line chart
    if len(hours) > 1:
        points = []
        for i, (hour, rev) in enumerate(zip(hours, revenues)):
            x = chart_x + (hour * chart_w/23)
            y = chart_y + chart_h - (rev * chart_h/max_revenue) if max_revenue > 0 else chart_y + chart_h
            points.append((x, y))
        
        # Draw line segments
        for i in range(len(points)-1):
            d.line([points[i], points[i+1]], fill=accent, width=2)
            
        # Draw points
        for x, y in points:
            d.ellipse([(x-3, y-3), (x+3, y+3)], fill=accent)

# Bottom panel: Heatmap (Day vs Hour)
heat_y = panel_y + panel_h + 30
heat_h = 150

# Add shadow and panel
d.rectangle([(32,heat_y+2),(W-28,heat_y+heat_h+2)], fill=(230,230,230))
d.rectangle([(30,heat_y),(W-30,heat_y+heat_h)], fill=card, outline=grid)

# Title with more space
d.text((45,heat_y+20), 'Revenue Heatmap: Day of Week vs Hour', font=font_kpi, fill=text)

# Heatmap visualization from warehouse data
days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

# Calculate better spacing
label_width = 50  # Space for day labels
hour_label_height = 25  # Space for hour labels
chart_start_x = 85  # More space for day labels
chart_start_y = heat_y + 60  # More space for title and hour labels

# Recalculate cell sizes with margins
available_width = W - chart_start_x - 40  # Leave margin on right
cell_w = available_width // 24
cell_h = (heat_h - hour_label_height - 70) // 7  # Leave space for labels and padding

# Organize heatmap data
heatmap = {}
max_heatmap_value = 0
for row in heatmap_data:
    day = int(row['day_of_week'])
    hour = int(row['hour'])
    revenue = row['revenue']
    heatmap[(day, hour)] = revenue
    max_heatmap_value = max(max_heatmap_value, revenue)

# Add day labels
for i, day in enumerate(days):
    d.text((35,heat_y+50+i*cell_h), day, font=font_small, fill=text)

# Add hour labels
for h in range(24):
    if h % 2 == 0:  # Show every other hour
        d.text((75+h*cell_w,heat_y+30), f'{h:02d}h', font=font_small, fill=text)

# Add day labels (centered vertically with cells)
for i, day in enumerate(days):
    y = chart_start_y + (i * cell_h) + (cell_h // 2) - 6  # Center text vertically
    d.text((35, y), day, font=font_small, fill=text)

# Add hour labels with better spacing
for h in range(24):
    if h % 3 == 0:  # Show every third hour for less clutter
        x = chart_start_x + (h * cell_w) + (cell_w // 2) - 10  # Center text
        d.text((x, heat_y + 35), f'{h:02d}h', font=font_small, fill=text)

# Draw heatmap cells
cell_padding = 1  # Add small gap between cells
for day in range(7):
    for hour in range(24):
        revenue = heatmap.get((day, hour), 0)
        intensity = int(255 * (revenue / max_heatmap_value)) if max_heatmap_value > 0 else 0
        
        x = chart_start_x + hour * cell_w
        y = chart_start_y + day * cell_h
        
        # Convert to RGB with better color gradient
        bg_factor = 1 - (intensity / 255)
        cell_rgb = (
            int(40 * (1 - bg_factor) + 245 * bg_factor),
            int(116 * (1 - bg_factor) + 247 * bg_factor),
            int(166 * (1 - bg_factor) + 250 * bg_factor)
        )
        
        # Draw cell with padding
        d.rectangle([
            (x + cell_padding, y + cell_padding),
            (x + cell_w - cell_padding, y + cell_h - cell_padding)
        ], fill=cell_rgb, outline=grid)

outdir = os.path.dirname(__file__) or '.'
out = os.path.join(outdir, '..', 'dashboard_mockup.png')
img.save(out)
print('Saved', out)
