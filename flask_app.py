from flask import Flask, render_template, send_from_directory, request, jsonify
from flask import send_file
from folium.plugins import MarkerCluster
import pyarrow.parquet as pq
from collections import Counter
import pandas as pd
import numpy as np
import geopandas as gpd
import plotly.express as px
import plotly.graph_objs as go
import plotly.io as pio
import folium
from folium import raster_layers,Element
from datetime import datetime,timedelta
import random
import threading
import json
import typing_extensions
import os
import h3
from waitress import serve
from utlis import resource_path
import logger
import logging
from DataBaseLogIn import DB_FILE,get_db_connection,init_db
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

#DB init
init_db()
# File where we log access timestamps
access_log_file = resource_path('csv_support/access_logs.csv')

# Load the Natural Earth Countries shapefile manually downloaded
shapefile_path = resource_path('Assets_AI/Country_shape.shp')

#logging.basicConfig(filename='app.log', level=logging.INFO)

# Load the shapefile using GeoPandas
world = gpd.read_file(shapefile_path)
world = world.set_crs('EPSG:4326', allow_override=True)

# Filter the map for Romania
romania = world[world['SOVEREIGNT'] == 'Romania']

risk_counter = Counter()
CHUNK_SIZE=1000000
MAX_POINTS_PER_CHUNK=500
PARQUET_FILE = resource_path('csv_support/Final_sheet.parquet')

# Load Parquet once for API access
def load_parquet_data():
    df = pd.read_parquet(PARQUET_FILE)
    df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
    df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
    df.dropna(subset=['Latitude', 'Longitude', 'Vegetation_Density'], inplace=True)
    return df

# Convert coordinates to H3 and aggregate
def get_h3_aggregated(df, resolution=7):
    df['h3_index'] = df.apply(lambda row: h3.geo_to_h3(row['Latitude'], row['Longitude'], resolution), axis=1)
    grouped = df.groupby('h3_index').agg({
        'Latitude': 'mean',
        'Longitude': 'mean',
        'Vegetation_Density': lambda x: x.mode()[0],
        'h3_index': 'count'
    }).rename(columns={'h3_index': 'count'}).reset_index()
    return grouped

def load_filtered_parquet_first_million(bbox):
    # Read only the first 1,000,000 rows
    table = pq.read_table(PARQUET_FILE, columns=['Latitude', 'Longitude', 'Vegetation_Density'])
    limited_table = table.slice(0, 1_000_000)
    df = limited_table.to_pandas()

    # Filter by bounding box
    west, south, east, north = bbox
    df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
    df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
    df.dropna(subset=['Latitude', 'Longitude'], inplace=True)

    df = df[
        (df['Latitude'] >= south) & (df['Latitude'] <= north) &
        (df['Longitude'] >= west) & (df['Longitude'] <= east)
    ]
    return df
@app.route('/api/points')
def api_points():
    try:
        bbox_param = request.args.get('bbox')
        if not bbox_param:
            return jsonify({'error': 'No bounding box provided'}), 400

        west, south, east, north = map(float, bbox_param.split(','))
        bbox = (west, south, east, north)

        df = load_filtered_parquet_first_million(bbox)
        if df.empty:
            return jsonify([])

        grouped = get_h3_aggregated(df)
        points = grouped.to_dict(orient='records')
        return jsonify(points)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def create_fire_risk_map_overlay():
    # Create a basic Folium map centered on Romania
    m = folium.Map(
        location=[45.9432, 24.9668],
        zoom_start=7,
        min_zoom=4,
        max_zoom=14,
        max_bounds=True
    )
    map_id = m.get_name()

    alias_script = Element(f"""
    <script>
        document.addEventListener("DOMContentLoaded", function() {{
            window.myMap = {map_id};
            window.centerMap = function(lat, lon, zoom = 10) {{
                if (window.myMap) {{
                    window.myMap.setView([lat, lon], zoom);
                }} else {{
                    console.error("Map is undefined!");
                }}
            }};
        }});
    </script>
    """)
    m.get_root().html.add_child(alias_script)

    # Add Romania to the map
    folium.GeoJson(romania).add_to(m)
    marker_cluster = MarkerCluster().add_to(m)

    df = pd.read_parquet(resource_path('csv_support/Final_sheet.parquet'))

    # Clean and convert coordinates
    df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
    df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
    df.dropna(subset=['Latitude', 'Longitude', 'Vegetation_Density'], inplace=True)

    risk_counter.update(df['Vegetation_Density'].value_counts().to_dict())

    # Plot each data point with color based on vegetation type
    for _, row in df.iterrows():
        veg = row['Vegetation_Density']
        color = {
            'Low_Vegetation': 'yellow',
            'Medium_Vegetation': 'orange',
            'High_Vegetation': 'red'
        }.get(veg, 'gray')
        if color=="yellow":
            r="Low"
        elif color=="orange":
            r="Medium"
        else:
            r="High"
        folium.CircleMarker(
            location=[row['Latitude'], row['Longitude']],
            radius=4,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.5,
            popup=f"Vegetation: {veg} | Fire risk: {r}"
        ).add_to(marker_cluster)

    # Load regions from GeoJSON
    with open(resource_path('reg_graphs/regions.geojson'), 'r') as f:
        regions_data = json.load(f)

    # Add the region polygons and overlay logic
    for feature in regions_data['features']:
        region_id = feature['properties']['id']
        region_name = feature['properties'].get('name', region_id)

        # Coordinates for bounds
        bounds = feature['geometry']['coordinates'][0]
        lats = [pt[1] for pt in bounds]
        lons = [pt[0] for pt in bounds]
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)
        image_bounds = [[min_lat, min_lon], [max_lat, max_lon]]

        # PNG path derived from TIFF
        image_url = resource_path(f'Maps/overlays/{region_id}.png')

        # Create the image overlay (but keep it hidden by default)
        img_overlay = raster_layers.ImageOverlay(
            name=f'{region_name} Overlay',
            image=image_url,
            bounds=image_bounds,
            opacity=0.7,
            interactive=True,
            cross_origin=False,
            zindex=1,
            show=False  # Initially hidden
        )

        # Add GeoJSON polygon to the map with click functionality
        geojson_layer = folium.GeoJson(
            feature,
            name=region_name,
            style_function=lambda x: {
                'fillColor': 'green',
                'color': 'black',
                'weight': 1,
                'fillOpacity': 0.3
            },
            tooltip=folium.GeoJsonTooltip(
                fields=['name'],
                aliases=['Region:'],
                sticky=True
            ),
            highlight_function=lambda x: {
                'weight': 3,
                'fillColor': 'orange',
                'fillOpacity': 0.6
            }
        ).add_to(m)

        # Add a popup with the image when the polygon is clicked
        popup_html = f'''
           <div style="text-align:center;">
               <b>{region_name}</b><br>
               <img src="/overlays/{region_id}.png" width="300px" />
           </div>
           '''

        # Attach the popup to the polygon
        folium.Popup(popup_html, max_width=400).add_to(geojson_layer)

    map_id = m.get_name()
    alias_script = Element(f"""
    <script>
        var map = {map_id};

        // Add a JS function to center the map from the search bar
        function centerMap(lat, lon, zoom=10) {{
            if (typeof map !== 'undefined') {{
                map.setView([lat, lon], zoom);
            }} else {{
                console.error('Map is undefined!');
            }}
        }}
    </script>
    """)
    m.get_root().html.add_child(alias_script)
    # Save the map to a static HTML file
    map_path = resource_path(os.path.join('Maps', 'server_romania_map.html'))
    m.save(map_path)

    return m

# Static map for initial load (without 20M points)
def create_fire_risk_map():
    # Create a basic Folium map centered on Romania
    m = folium.Map(
        location=[45.9432, 24.9668],
        zoom_start=7,
        min_zoom=4,
        max_zoom=14,
        max_bounds=True
    )

    # Add Romania to the map
    folium.GeoJson(romania).add_to(m)
    marker_cluster = MarkerCluster().add_to(m)

    df = pd.read_parquet(resource_path('csv_support/Final_sheet.parquet'))

    # Clean and convert coordinates
    df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
    df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
    df.dropna(subset=['Latitude', 'Longitude', 'Vegetation_Density'], inplace=True)

    risk_counter.update(df['Vegetation_Density'].value_counts().to_dict())

    # Plot each data point with color based on vegetation type
    for _, row in df.iterrows():
        veg = row['Vegetation_Density']
        color = {
            'Low_Vegetation': 'yellow',
            'Medium_Vegetation': 'orange',
            'High_Vegetation': 'red'
        }.get(veg, 'gray')

        folium.CircleMarker(
            location=[row['Latitude'], row['Longitude']],
            radius=4,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.5,
            popup=f"Vegetation: {veg}"
        ).add_to(marker_cluster)

    # Load regions from GeoJSON
    with open(resource_path('reg_graphs/regions.geojson'), 'r') as f:
        regions_data = json.load(f)

    # Add the region polygons and overlay logic
    for feature in regions_data['features']:
        region_id = feature['properties']['id']
        region_name = feature['properties'].get('name', region_id)

        # Coordinates for bounds
        bounds = feature['geometry']['coordinates'][0]
        lats = [pt[1] for pt in bounds]
        lons = [pt[0] for pt in bounds]
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)
        image_bounds = [[min_lat, min_lon], [max_lat, max_lon]]

        # PNG path derived from TIFF
        image_url = resource_path(f'Maps/overlays/{region_id}.png')

        # Create the image overlay (but keep it hidden by default)
        img_overlay = raster_layers.ImageOverlay(
            name=f'{region_name} Overlay',
            image=image_url,
            bounds=image_bounds,
            opacity=0.7,
            interactive=True,
            cross_origin=False,
            zindex=1,
            show=False  # Initially hidden
        )

        # Add GeoJSON polygon to the map with click functionality
        geojson_layer = folium.GeoJson(
            feature,
            name=region_name,
            style_function=lambda x: {
                'fillColor': 'green',
                'color': 'black',
                'weight': 1,
                'fillOpacity': 0.3
            },
            tooltip=folium.GeoJsonTooltip(
                fields=['name'],
                aliases=['Region:'],
                sticky=True
            ),
            highlight_function=lambda x: {
                'weight': 3,
                'fillColor': 'orange',
                'fillOpacity': 0.6
            }
        ).add_to(m)

        # Add a popup with the image when the polygon is clicked
        popup_html = f'''
           <div style="text-align:center;">
               <b>{region_name}</b><br>
               <img src="/overlays/{region_id}.png" width="300px" />
           </div>
           '''

        # Attach the popup to the polygon
        folium.Popup(popup_html, max_width=400).add_to(geojson_layer)

    # Save the map to a static HTML file
    map_path = resource_path(os.path.join('Maps', 'server_romania_map.html'))
    m.save(map_path)

    return map_path

# Function to log access timestamp
def log_access():
    timestamp = datetime.now()
    # Append the access time to a CSV file (for simplicity)
    with open(access_log_file, 'a') as f:
        f.write(f"{timestamp}\n")

# Track server access by logging the timestamp for each request
@app.before_request
def track_access():
    logging.info(f"Accessed server at:{datetime.now()}")
    log_access()

# Function to generate the diagnostic charts
def create_diagnostic_charts():
    df = pd.read_parquet(PARQUET_FILE, columns=['Vegetation_Density'])
    risk_counter.update(df['Vegetation_Density'].value_counts().to_dict())
    labels = list(risk_counter.keys())
    values = list(risk_counter.values())
    fig1 = px.pie(names=labels, values=values, title="Fire Risk Distribution by Vegetation Density")
    fig1_html = fig1.to_html(full_html=False)

    fig2_html=""
    if os.path.exists(access_log_file):
        df_log = pd.read_csv(access_log_file, header=None, names=['timestamp'])
        df_log['timestamp'] = pd.to_datetime(df_log['timestamp'])
        df_last_24h = df_log[df_log['timestamp'] > (datetime.now() - pd.Timedelta(days=1))].copy()
        df_last_24h['hour'] = df_last_24h['timestamp'].dt.hour
        access_count_per_hour = df_last_24h.groupby('hour').size().reset_index(name='access_count')
        fig2 = px.bar(access_count_per_hour, x='hour', y='access_count',
                      title="Server Accesses in the Last 24 Hours",
                      labels={'hour': 'Hour of Day', 'access_count': 'Number of Accesses'})
        fig2_html = fig2.to_html(full_html=False)

    # Simulated Animated Line Chart: Fire Risk Over Time
    now = datetime.now()
    simulated_data = pd.DataFrame({
        'timestamp': [now - timedelta(minutes=5 * i) for i in range(100)][::-1],
        'risk_level': np.random.uniform(0.2, 1.0, 100)
    })

    fig3 = px.line(
        simulated_data,
        x='timestamp',
        y='risk_level',
        title='Simulated Fire Risk Over Time',
        template='plotly_dark'
    )
    fig3.update_traces(line=dict(color='lime', width=3))
    fig3.update_layout(
        plot_bgcolor='black',
        paper_bgcolor='black',
        font_color='white',
        xaxis_title="Time",
        yaxis_title="Risk Level"
    )
    fig3_html = fig3.to_html(full_html=False)

    return fig1_html + fig2_html + fig3_html

map_path = create_fire_risk_map()
@app.route('/')
def index():
    # Generate the map
    logging.info("Main map accessed")
    return send_file(map_path)

@app.route('/complete_map')
def complete_map():
    logging.info("Complete map shown in app")
    return send_file(resource_path("Maps/server_romania_map_1.html"))

@app.route('/ai_map')
def graph_map():
    logging.info("Ai map accesed in app")
    return send_file(resource_path("Maps/predicted_romania_map.html"))

@app.route('/dynamic_map')
def dynamic_map():
    logging.info("Dynamic map accessed")
    return render_template('index.html')

@app.route("/romania-geojson")
def romania_geojson():
    gdf = gpd.read_file(resource_path("Country_shape.shp"))  # Adjust the path to your shapefile
    romania = gdf[gdf['SOVEREIGNT'] == 'Romania']
    return jsonify(romania.__geo_interface__)

@app.route('/diagnostics')
def diagnostics():
    logging.info("Diagnostics accessed")
    # Generate the diagnostic chart
    chart_html = create_diagnostic_charts()
    # Return a page that displays the chart
    return render_template('diagnostics.html', chart=chart_html)


p = pd.read_parquet(resource_path('csv_support/Final_sheet.parquet'))

# Convert categorical fire risk to numeric
risk_map = {
    "Very Low": 0.2,
    "Low": 0.4,
    "Medium": 0.6,
    "High": 0.8,
    "Very High": 1.0
}
p['risk_level'] = p['Fire_Risk'].map(risk_map).fillna(0.0)

# Generate synthetic timestamps for simulation
p['timestamp'] = pd.date_range(start=datetime.now(), periods=len(p), freq='s')

# Global counter for streaming simulation
current_index = {'value': 0}
lock = threading.Lock()  # thread-safe access if needed

@app.route('/api/fire-risk-data')
def stream_data():
    with lock:
        i = current_index['value']
        if i >= len(p):
            current_index['value'] = 0  # reset to loop, or just return []
            i = 0

        row = p.iloc[i]
        current_index['value'] += 1

    return jsonify([{
        'timestamp': row['timestamp'].isoformat(),
        'risk_level': row['risk_level']
    }])

allowed_extensions = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@app.route('/overlays/<filename>')
def serve_overlay(filename):
    # Sanitize the filename and ensure it's an allowed extension
    if allowed_file(filename):
        return send_from_directory(resource_path('Maps/overlays'), filename)
    else:
        return "File type not allowed", 403

@app.errorhandler(404)
def not_found(error):
    logging.error(f"An page impossibility load occurred: {error}")
    return render_template(resource_path('templates/404.html')), 404

@app.errorhandler(500)
def internal_error(error):
    logging.error(f"An internal error occurred: {error}")
    return render_template(resource_path('templates/500.html')), 500


import sqlite3


@app.route('/users', methods=['GET'])
def get_users():
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users').fetchall()
    conn.close()
    return jsonify([dict(user) for user in users])

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    purpose = data.get('purpose')

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (name, email, password, purpose) VALUES (?, ?, ?, ?)",
                       (name, email, password, purpose))
        conn.commit()
        return jsonify({'message': 'Signup successful'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Email already exists'}), 409
    finally:
        conn.close()

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name, password FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()

    if row and row[1] == password:
        return jsonify({"name": row[0]}), 200
    else:
        return jsonify({"error": "Invalid credentials"}), 401

@app.route("/api/user/<email>", methods=["GET"])
def get_user_data(email):
    conn = get_db_connection()
    user = conn.execute("SELECT name, password FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    if user:
        return jsonify({"name": user["name"], "password": user["password"]})
    return jsonify({}), 404

@app.route("/api/update_password", methods=["POST"])
def update_password():
    data = request.get_json()
    email = data.get("email")
    new_password = data.get("new_password")

    conn = get_db_connection()
    conn.execute("UPDATE users SET password = ? WHERE email = ?", (new_password, email))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route("/api/delete_account", methods=["DELETE"])
def delete_account():
    data = request.get_json()
    email = data.get("email")

    conn = get_db_connection()
    conn.execute("DELETE FROM users WHERE email = ?", (email,))
    conn.commit()
    conn.close()
    return jsonify({"status": "deleted"})

import requests

api_key = "1710d2b44fd9b115d0fef3d47360bc16"

@app.route('/api/weather-tiles/<layer>/<z>/<x>/<y>.png')
def proxy_weather_tile(layer, z, x, y):
    tile_url = f"https://tile.openweathermap.org/map/{layer}/{z}/{x}/{y}.png?appid={api_key}"
    response = requests.get(tile_url)
    return (response.content, response.status_code, {
        'Content-Type': response.headers['Content-Type'],
        'Cache-Control': 'no-cache'
    })

@app.route('/api/weather')
def proxy_weather_data():
    lat = request.args.get('lat')
    lon = request.args.get('lon')

    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    response = requests.get(url)
    return jsonify(response.json()), response.status_code


"""
@app.before_request
def debug_headers():
    print("Proto:", request.headers.get('X-Forwarded-Proto'))
    print("Method:", request.method)
    print("URL:", request.url)

@app.route('/headers', methods=['GET', 'POST'])
def headers():
    headers = dict(request.headers)
    print(headers)  # This will log all headers to your Flask console
    return jsonify(headers)"""

if __name__ == '__main__':
    serve(app, host='127.0.0.1', port=5000)

