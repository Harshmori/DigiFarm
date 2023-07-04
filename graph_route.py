import datetime as dt
from flask import Blueprint, render_template, request
import mysql.connector.pooling
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.style as style
import io
import base64

graph_bp = Blueprint('graph', __name__)

# Set up a connection pool
pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="mydb_pool",
        pool_size=2,  
        host="hostname",
        user="username",
        password="password",
        database="db_name"
)

@graph_bp.route('/graph')
def graph():
    user_agent = request.user_agent.string
    is_mobile = 'Mobile' in user_agent
    commodity = request.args.get('commodity')
    market = request.args.get('market')
    district = request.args.get('district')

    # Acquire a connection from the pool
    connection = pool.get_connection()

    # Create a cursor
    cursor = connection.cursor()

    # Retrieve data for generating the graph based on the selected parameters
    query = "SELECT arrival_date, modal_price FROM prices WHERE commodity = %s AND market = %s AND district = %s ORDER BY arrival_date DESC"
    cursor.execute(query, (commodity, market, district))
    data = cursor.fetchall()

    # Release the connection
    cursor.close()
    connection.close()

    num_values = min(len(data), 10)  # Get the minimum of available data and 10
    dates = [row[0].strftime("%d %b %Y") for row in data[:num_values]][::-1]  # Format dates as dd mm yyyy and reverse the order
    prices = [row[1] / 5 for row in data[:num_values]][::-1]  # Divide modal prices by 5 and reverse the order

    # Apply a different style to the plot (optional)
    style.use('default')

    # Set custom font properties
    font_family = 'Arial'
    font_size = 12

    # Set custom colors for the plot
    line_color = 'steelblue'
    marker_color = 'darkorange'

    # Generate the graph using Matplotlib
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(dates, prices, marker='o', linestyle='-', linewidth=2, markersize=6, color=line_color)
    ax.set_xlabel('Date', fontfamily=font_family, fontsize=font_size, fontweight='bold')
    ax.set_ylabel('Modal Price (20 kg)', fontfamily=font_family, fontsize=font_size, fontweight='bold')
    ax.set_title(f'{commodity} Prices in {market}, {district}', fontfamily=font_family, fontsize=14, fontweight='bold')
    ax.tick_params(axis='x', rotation=45, labelsize=10)
    ax.xaxis.set_major_locator(plt.MaxNLocator(num_values))  # Show maximum of available x-axis tick labels

    # Customize the grid style and color
    plt.grid(True, linestyle='--', linewidth=0.5, alpha=0.7, color='lightgray')

    # Customize the line and marker colors
    ax.lines[0].set_color(line_color)
    ax.lines[0].set_markerfacecolor(marker_color)
    ax.lines[0].set_markeredgecolor(marker_color)

    # Add data labels to the points
    for i, price in enumerate(prices):
        ax.annotate(f'{price:.2f}', (dates[i], price), xytext=(0, 5), textcoords='offset points', ha='center', fontsize=8)

    plt.tight_layout()

    # Convert the graph to a base64-encoded string
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    image_data = base64.b64encode(buffer.getvalue()).decode()

    # Pass the commodity, market, district, and base64-encoded image data to the template
    if is_mobile:
        return render_template('mobile/graph.html', commodity=commodity, market=market, district=district, image_data=image_data)
    else:
        return render_template('desktop/graph.html', commodity=commodity, market=market, district=district, image_data=image_data)
