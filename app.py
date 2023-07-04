from flask import Flask, render_template, request
import datetime as dt
import requests
from datetime import datetime
from mysql.connector import pooling
from graph_route import graph_bp

app = Flask(__name__)

# Configure database connection pool
mydb_pool = None

def create_connection_pool():
    global mydb_pool
    mydb_pool = pooling.MySQLConnectionPool(
        pool_name="mydb_pool",
        pool_size=3,  
        host="hostname",
        user="username",
        password="password",
        database="db_name"
    )

def get_database_connection():
    global mydb_pool
    if mydb_pool is None:
        create_connection_pool()
    return mydb_pool.get_connection()

# Set up the API endpoint and API key
endpoint = 'https://api.data.gov.in/catalog/6141ea17-a69d-4713-b600-0a43c8fd9a6c'
api_key = 'YOUR_API_KEY'

# Set the parameters for the API request
params = {
    'api-key': api_key,
    'format': 'json',
    'filters[state]': 'Gujarat',
    'limit': '1000'
}

def format_date(date_str):
    date_obj = datetime.strptime(date_str, '%d/%m/%Y')
    formatted_date = date_obj.strftime('%Y-%m-%d')
    return formatted_date

def run_script():
            response = requests.get(endpoint, params=params)
            data = response.json()
            connection = get_database_connection()
            cursor = connection.cursor()
            for row in data['records']:
                sql = "INSERT IGNORE INTO prices (commodity, market, district, state, min_price, max_price, modal_price, arrival_date) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
                values = (
                    row["commodity"],
                    row["market"],
                    row["district"],
                    row["state"],
                    row["min_price"],
                    row["max_price"],
                    row["modal_price"],
                    format_date(row["arrival_date"])
                )
                cursor.execute(sql, values)
            connection.commit()
            cursor.close()
            connection.close()
            print("Data updated successfully!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

@app.route('/', methods=['GET', 'POST'])
def index():
    run_script()
    user_agent = request.user_agent.string
    is_mobile = 'Mobile' in user_agent
    if is_mobile:
        # Fetch unique districts from the database
        connection = get_database_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT DISTINCT district FROM prices")
        districts = cursor.fetchall()

        today = dt.date.today()
        date = dt.date.today().strftime('%d / %m / %Y, %A')

        selected_district = request.args.get('district')
        selected_market = request.args.get('market')

        if selected_district:
            # Fetch unique markets based on the selected district
            cursor.execute("SELECT DISTINCT market FROM prices WHERE district=%s", (selected_district,))
            markets = cursor.fetchall()
        else:
            markets = []

        # Fetch commodity data for the selected market
        cursor.execute("SELECT * FROM prices WHERE arrival_date=%s", (today,))
        commodities = cursor.fetchall()

        cursor.close()
        connection.close()

        return render_template('mobile/index.html', districts=districts, markets=markets,
                               selected_district=selected_district, selected_market=selected_market,
                               commodities=commodities, today=today, date=date)
    else:
        today = dt.date.today()
        yesterday = today - dt.timedelta(days=1)
        yesterday_str = yesterday.strftime('%Y-%m-%d')

        if request.method == 'POST':
            district = request.form.get('district')
            market = request.form.get('market')
            commodity = request.form.get('commodity')
            date = request.form.get('date')

            query = "SELECT * FROM prices WHERE 1=1"
            if district:
                query += f" AND district = '{district}'"
            if market:
                query += f" AND market = '{market}'"
            if commodity:
                query += f" AND commodity = '{commodity}'"
            if date:
                query += f" AND arrival_date = '{date}'"

            query += " ORDER BY arrival_date DESC"

            connection = get_database_connection()
            cursor = connection.cursor()
            cursor.execute(query)
            prices = cursor.fetchall()
            cursor.close()
            connection.close()
        else:
            connection = get_database_connection()
            cursor = connection.cursor()
            cursor.execute(
                f"SELECT DISTINCT *, arrival_date FROM prices WHERE arrival_date >= DATE_SUB('{yesterday_str}', INTERVAL 1 DAY) ORDER BY arrival_date DESC")
            prices = cursor.fetchall()
            cursor.close()
            connection.close()

        if not prices:
            found = False
            days = 1
            while not found:
                past_date = yesterday - dt.timedelta(days=days)
                past_date_str = past_date.strftime('%Y-%m-%d')
                connection = get_database_connection()
                cursor = connection.cursor()
                cursor.execute(f"SELECT * FROM prices WHERE arrival_date = '{past_date_str}'")
                prices = cursor.fetchall()
                cursor.close()
                connection.close()
                if prices:
                    found = True
                else:
                    days += 1
            date = past_date.strftime('%d / %m / %Y, %A')
        else:
            date = prices[0][8].strftime('%d / %m / %Y, %A')

        connection = get_database_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT DISTINCT district FROM prices")
        districts = cursor.fetchall()
        cursor.execute("SELECT DISTINCT arrival_date FROM prices ORDER BY arrival_date ASC")
        dates = cursor.fetchall()
        cursor.execute("SELECT DISTINCT market FROM prices ORDER BY market ASC")
        markets = cursor.fetchall()
        cursor.execute("SELECT DISTINCT commodity FROM prices")
        commodities = cursor.fetchall()
        cursor.close()
        connection.close()

        return render_template('desktop/index.html', prices=prices, date=date, dates=dates,
                               districts=districts, markets=markets, commodities=commodities)

app.register_blueprint(graph_bp)

if __name__ == '__main__':
    app.run(debug=True)

