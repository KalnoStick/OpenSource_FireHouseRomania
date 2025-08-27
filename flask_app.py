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

init_db()

access_log_file = resource_path('csv_support/access_logs.csv')

# Natural Earth Countries shapefile
shapefile_path = resource_path('Assets_AI/Country_shape.shp')

#logging.basicConfig(filename='app.log', level=logging.INFO)

world = gpd.read_file(shapefile_path)
world = world.set_crs('EPSG:4326', allow_override=True)

romania = world[world['SOVEREIGNT'] == 'Romania']

risk_counter = Counter()
CHUNK_SIZE=1000000
MAX_POINTS_PER_CHUNK=500
PARQUET_FILE = resource_path('csv_support/Final_sheet.parquet')

def load_parquet_data():
    df = pd.read_parquet(PARQUET_FILE)
    df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
    df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
    df.dropna(subset=['Latitude', 'Longitude', 'Vegetation_Density'], inplace=True)
    return df

# Coordinates to H3 and aggregate
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
    # First 1,000,000 rows
    table = pq.read_table(PARQUET_FILE, columns=['Latitude', 'Longitude', 'Vegetation_Density'])
    limited_table = table.slice(0, 1_000_000)
    df = limited_table.to_pandas()

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

#FireRiskMap-Creation for other elements
def create_fire_risk_map_overlay():
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

    folium.GeoJson(romania).add_to(m)
    marker_cluster = MarkerCluster().add_to(m)

    df = pd.read_parquet(resource_path('csv_support/Final_sheet.parquet'))

    df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
    df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
    df.dropna(subset=['Latitude', 'Longitude', 'Vegetation_Density'], inplace=True)

    risk_counter.update(df['Vegetation_Density'].value_counts().to_dict())

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

    with open(resource_path('reg_graphs/regions.geojson'), 'r') as f:
        regions_data = json.load(f)

    # Regions and overlay logic
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

        image_url = resource_path(f'Maps/overlays/{region_id}.png')

        #Image Overlay hidden by default
        img_overlay = raster_layers.ImageOverlay(
            name=f'{region_name} Overlay',
            image=image_url,
            bounds=image_bounds,
            opacity=0.7,
            interactive=True,
            cross_origin=False,
            zindex=1,
            show=False
        )

        # GeoJSON polygon with click functionality
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

        popup_html = f'''
           <div style="text-align:center;">
               <b>{region_name}</b><br>
               <img src="/overlays/{region_id}.png" width="300px" />
           </div>
           '''

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
    map_path = resource_path(os.path.join('Maps', 'server_romania_map.html'))
    m.save(map_path)

    return m

# Static map for initial load (without 20M points)
def create_fire_risk_map():
    m = folium.Map(
        location=[45.9432, 24.9668],
        zoom_start=7,
        min_zoom=4,
        max_zoom=14,
        max_bounds=True
    )

    folium.GeoJson(romania).add_to(m)
    marker_cluster = MarkerCluster().add_to(m)

    df = pd.read_parquet(resource_path('csv_support/Final_sheet.parquet'))

    df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
    df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
    df.dropna(subset=['Latitude', 'Longitude', 'Vegetation_Density'], inplace=True)

    risk_counter.update(df['Vegetation_Density'].value_counts().to_dict())

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

    with open(resource_path('reg_graphs/regions.geojson'), 'r') as f:
        regions_data = json.load(f)

    for feature in regions_data['features']:
        region_id = feature['properties']['id']
        region_name = feature['properties'].get('name', region_id)

        bounds = feature['geometry']['coordinates'][0]
        lats = [pt[1] for pt in bounds]
        lons = [pt[0] for pt in bounds]
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)
        image_bounds = [[min_lat, min_lon], [max_lat, max_lon]]

        image_url = resource_path(f'Maps/overlays/{region_id}.png')

        img_overlay = raster_layers.ImageOverlay(
            name=f'{region_name} Overlay',
            image=image_url,
            bounds=image_bounds,
            opacity=0.7,
            interactive=True,
            cross_origin=False,
            zindex=1,
            show=False
        )

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

        popup_html = f'''
           <div style="text-align:center;">
               <b>{region_name}</b><br>
               <img src="/overlays/{region_id}.png" width="300px" />
           </div>
           '''

        folium.Popup(popup_html, max_width=400).add_to(geojson_layer)

    map_path = resource_path(os.path.join('Maps', 'server_romania_map.html'))
    m.save(map_path)

    return map_path

#===LOG LOGIC===
def log_access():
    timestamp = datetime.now()
    with open(access_log_file, 'a') as f:
        f.write(f"{timestamp}\n")

@app.before_request
def track_access():
    logging.info(f"Accessed server at:{datetime.now()}")
    log_access()

#===DIAGNOSTICS LOGIC===
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

#===DEFAULT ROUTE-TESTING===
@app.route('/')
def index():
    logging.info("Main map accessed")
    return send_file(map_path)

#===MAPS-DIVERSE===
@app.route('/complete_map')
def complete_map():
    logging.info("Complete map shown in app")
    return send_file(resource_path("Maps/server_romania_map_1.html"))

@app.route('/ai_map')
def graph_map():
    logging.info("Ai map accesed in app")
    return send_file(resource_path("Maps/predicted_romania_map.html"))

@app.route("/romania-geojson")
def romania_geojson():
    gdf = gpd.read_file(resource_path("Country_shape.shp"))  # Adjust the path to your shapefile
    romania = gdf[gdf['SOVEREIGNT'] == 'Romania']
    return jsonify(romania.__geo_interface__)

@app.route('/diagnostics')
def diagnostics():
    logging.info("Diagnostics accessed")
    chart_html = create_diagnostic_charts()
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

p['timestamp'] = pd.date_range(start=datetime.now(), periods=len(p), freq='s')

# Global counter - streaming simulation
current_index = {'value': 0}
lock = threading.Lock()

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
    if allowed_file(filename):
        return send_from_directory(resource_path('Maps/overlays'), filename)
    else:
        return "File type not allowed", 403

#===ERROR HANDLER===
@app.errorhandler(404)
def not_found(error):
    logging.error(f"An page impossibility load occurred: {error}")
    return render_template(resource_path('templates/404.html')), 404

@app.errorhandler(500)
def internal_error(error):
    logging.error(f"An internal error occurred: {error}")
    return render_template(resource_path('templates/500.html')), 500


import sqlite3

#===DATA BASE===
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

from SensoInfo import OPENWEATHER_API_KEY
api_key = OPENWEATHER_API_KEY

#===OPENWEATHER INJECTION===
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

#===MANIPULATE AI MAP===
from DynamicNASAFireRiskZones import get_fires_gdf,predict_grid,evaluate_vs_firms,gdf_to_featurecollection,downsample_by_risk
from SensoInfo import MAP_KEY_NASA_FIRMS as MAP_KEY
from shapely.geometry import Point

def craate_gdf_locally():
    world = gpd.read_file("Assets_AI/Country_shape.shp")
    if world.crs is None:
        world = world.set_crs("EPSG:4326")
    elif world.crs.to_epsg() != 4326:
        world = world.to_crs(4326)

    rom = world[world["SOVEREIGNT"] == "Romania"]
    rom_union = rom.geometry.union_all()
    min_lat, max_lat = 43.6, 48.3
    min_lon, max_lon = 20.2, 29.7
    step = 0.05

    lats = np.arange(min_lat, max_lat, step)
    lons = np.arange(min_lon, max_lon, step)
    coords = [(la, lo) for la in lats for lo in lons]

    grid_df = pd.DataFrame(coords, columns=["Latitude", "Longitude"])
    grid_gdf = gpd.GeoDataFrame(
        grid_df,
        geometry=[Point(lo, la) for la, lo in coords],
        crs="EPSG:4326"
    )
    grid_gdf = grid_gdf[grid_gdf.geometry.intersects(rom_union)]
    return grid_gdf

@app.get("/api/fires")
def api_fires():
    fires = get_fires_gdf(MAP_KEY)  # EPSG:4326
    return jsonify(gdf_to_featurecollection(fires))

@app.get("/api/predictions")
def api_predictions():
    grid_gdf = craate_gdf_locally()
    preds = predict_grid(grid_gdf)
    cols = ["Predicted_Fire_Risk","Predicted_Vegetation"]
    slim = gpd.GeoDataFrame(preds[cols], geometry=preds.geometry, crs=preds.crs)

    ratio = float(request.args.get("ratio", 0.4))  # default: 40%
    sampled = downsample_by_risk(slim, ratio=ratio, weights={1: 1, 2: 2, 3: 3, 4: 4})
    return jsonify(gdf_to_featurecollection(sampled))
    #return jsonify(gdf_to_featurecollection(slim))

from shapely.geometry import Polygon
from math import sqrt
import traceback
def _hexagon(cx: float, cy: float, R: float) -> Polygon:
    angles = np.deg2rad([0, 60, 120, 180, 240, 300])
    xs = cx + R * np.cos(angles)
    ys = cy + R * np.sin(angles)
    return Polygon(np.column_stack([xs, ys]))
@app.get("/api/prediction_polygons")
def api_prediction_polygons():
    try:
        step_deg   = float(request.args.get("step_deg", 0.05))
        simplify_m = float(request.args.get("simplify_m", 300))
        margin     = float(request.args.get("margin", 0.95))

        grid_gdf = craate_gdf_locally()
        preds    = predict_grid(grid_gdf)

        if preds.empty:
            return jsonify({"type":"FeatureCollection","features":[]})

        lat = preds["Latitude"].to_numpy()
        m_per_deg_lat = 111_132.0
        m_per_deg_lon = (40_075_016.6856 * np.cos(np.deg2rad(lat))) / 360.0

        step_m_lat = step_deg * m_per_deg_lat
        step_m_lon = step_deg * m_per_deg_lon

        R_fit_vert = step_m_lat / sqrt(3.0)
        R_fit_horz = step_m_lon / 2.0
        R = np.minimum(R_fit_vert, R_fit_horz) * margin

        centers_m = preds.to_crs(3857)
        xs = centers_m.geometry.x.to_numpy()
        ys = centers_m.geometry.y.to_numpy()
        risk = preds["Predicted_Fire_Risk"].to_numpy()

        hex_polys = [_hexagon(x, y, r) for x, y, r in zip(xs, ys, R)]
        cells_m = gpd.GeoDataFrame({"Predicted_Fire_Risk": risk}, geometry=hex_polys, crs=3857)
        dissolved = cells_m.dissolve(by="Predicted_Fire_Risk", as_index=False)

        if simplify_m > 0:
            dissolved["geometry"] = dissolved.geometry.simplify(simplify_m, preserve_topology=True)

        out4326 = dissolved.to_crs(4326)[["Predicted_Fire_Risk","geometry"]]
        return jsonify(gdf_to_featurecollection(out4326))

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
@app.get("/api/metrics")
def api_metrics():
    grid_gdf = craate_gdf_locally()
    fires = get_fires_gdf(MAP_KEY)
    preds = predict_grid(grid_gdf)
    m = evaluate_vs_firms(preds, fires)
    return jsonify(m)

@app.get("/firmsimportedmap")
def load():
    return send_file(resource_path("templates/AI_GENERATED_MAP.html"))

#===OPEN WITH GOOGLE MAPS===
def streetview_available(lat, lon):
    meta_url=("https://www.google.com/maps/@"
              f"?api=1&map_action=pano&viewpoint={lat},{lon}")
    r = requests.get(meta_url, timeout=10).json()
    return r.get("status") == "OK"
#https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=LAT,LON
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

