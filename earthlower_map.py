import pandas as pd
import geopandas as gpd
import folium
from branca.element import MacroElement
from jinja2 import Template
from folium import raster_layers
import os
import rasterio
import json
import stat

# Load the Natural Earth Countries shapefile manually downloaded
shapefile_path = 'Assets_AI/Country_shape.shp'

# Load the shapefile using GeoPandas
world = gpd.read_file(shapefile_path)
#print(world.columns)
world = world.set_crs('EPSG:4326', allow_override=True)
#print(world.crs)

# Filter the map for Romania
romania = world[world['SOVEREIGNT'] == 'Romania']

# Load your fire risk data CSV
df = pd.read_csv('csv_chunks/forest_data_part_1.csv',encoding='utf-8')
df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
df.dropna(subset=['Latitude', 'Longitude', 'Vegetation_Density'], inplace=True)
print(df.tail())

# Create a basic Folium map centered on Romania
m = folium.Map(location=[45.9432, 24.9668], zoom_start=7)

# Add Romania to the map
folium.GeoJson(romania).add_to(m)

# Optionally, add a marker for a specific location (example: Bucharest)
folium.Marker(
    location=[44.4268, 26.1025],
    popup='Bucharest',
    icon=folium.Icon(color='blue')
).add_to(m)

# Plot fire risk data points on the map with color based on Vegetation_Density
for _, row in df.iterrows():
    veg = row['Vegetation_Density']
    color = {'Low_Vegetation': 'yellow', 'Medium_Vegetation': 'orange', 'High_Vegetation': 'red'}.get(veg, 'gray')

    folium.CircleMarker(
        location=[row['Latitude'], row['Longitude']],
        radius=6,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.6,
        popup=f"Vegetation: {veg}"
    ).add_to(m)

# Save the map as an HTML file
#m.save('Maps/romania_fire_risk_map.html')

# === 1. Load regions from GeoJSON ===
with open('reg_graphs/regions.geojson', 'r') as f:
    regions_data = json.load(f)

image_overlays = {}

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
    image_url = f'Maps/overlays/{region_id}.png'

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

    # Store the overlay in the image_overlays dictionary
    image_overlays[region_id] = img_overlay

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
           <img src="overlays/{region_id}.png" width="300px" />
       </div>
       '''

    # Attach the popup to the polygon
    folium.Popup(popup_html, max_width=400).add_to(geojson_layer)

# Save the map with all overlays
m.save("Maps/romania_fire_risk_map.html")

print("Fire risk map saved as 'romania_fire_risk_map.html'.")
print("Final map crated!")