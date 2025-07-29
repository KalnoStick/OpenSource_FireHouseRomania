import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import folium
import pyarrow.parquet as pq
import dask.dataframe as dd
import geopandas as gpd
from shapely.geometry import Point
from flask_app import create_fire_risk_map_overlay

# Load the Parquet file using Dask
df = dd.read_parquet('csv_support/fire_data.parquet', columns=['Latitude', 'Longitude', 'Vegetation_Density', 'Fire_Risk'])

# Convert categorical columns using Dask map with metadata
df['Vegetation_Density'] = df['Vegetation_Density'].map({
    'High_Vegetation': 1, 'Medium_Vegetation': 2, 'Low_Vegetation': 3, 'Urban': 4
}, meta=('Vegetation_Density', 'int64'))

df['Fire_Risk'] = df['Fire_Risk'].map({
    'Very Low': 1, 'Low': 2, 'Medium': 3, 'High': 4, 'Unknown': 0
}, meta=('Fire_Risk', 'int64'))

# Sample only a portion of the data for training
sample_df = df[df['Fire_Risk'] != 0].sample(frac=0.05, random_state=42).compute()

# Separate known and unknown fire risk labels
known_data = sample_df  # Already filtered
unknown_data = pd.DataFrame(columns=sample_df.columns)  # empty for now (preserves structure)

'''
# Separate known and unknown fire risk labels
known_data = df[df['Fire_Risk'] != 0]  # Known fire risk values
unknown_data = df[df['Fire_Risk'] == 0]  # Unknown fire risk values
'''
# Prepare features (X) and target variable (y) for both vegetation zones and fire risk
X = known_data[['Latitude', 'Longitude', 'Vegetation_Density']]  # Features for training
y_vegetation = known_data['Vegetation_Density']  # Vegetation prediction target
y_fire_risk = known_data['Fire_Risk']  # Fire risk prediction target

# Train models
if len(X) > 0:
    X_train, X_test, y_train_veg, y_test_veg = train_test_split(X, y_vegetation, test_size=0.2, random_state=42)
    vegetation_clf = RandomForestClassifier(n_estimators=100, random_state=42)
    vegetation_clf.fit(X_train, y_train_veg)
    print(f"Vegetation Model Accuracy: {accuracy_score(y_test_veg, vegetation_clf.predict(X_test)):.2f}")

    X_train, X_test, y_train_fire, y_test_fire = train_test_split(X, y_fire_risk, test_size=0.2, random_state=42)
    fire_risk_clf = RandomForestClassifier(n_estimators=100, random_state=42)
    fire_risk_clf.fit(X_train, y_train_fire)
    print(f"Fire Risk Model Accuracy: {accuracy_score(y_test_fire, fire_risk_clf.predict(X_test)):.2f}")

    # Predict missing data only if there are any
    if not unknown_data.empty:
        X_unknown = unknown_data[['Latitude', 'Longitude', 'Vegetation_Density']]
        unknown_data['Vegetation_Density'] = vegetation_clf.predict(X_unknown)
        unknown_data['Fire_Risk'] = fire_risk_clf.predict(X_unknown)

    # Combine known and predicted
    complete_df = pd.concat([known_data, unknown_data])
else:
    raise ValueError("No data available for training.")

# You can skip saving to CSV if memory is a concern
# complete_df.to_csv('updated_forest_data.csv', index=False)
print("Model trained and predictions made!")

# Rough bounding box of Romania
min_lat, max_lat = 43.6, 48.3
min_lon, max_lon = 20.2, 29.7

# Define grid resolution (adjust for performance/memory)
step = 0.05  # ~5km per step

# Generate the grid of coordinates
latitudes = np.arange(min_lat, max_lat, step)
longitudes = np.arange(min_lon, max_lon, step)
grid_coords = [(lat, lon) for lat in latitudes for lon in longitudes]

# Create DataFrame from generated coordinates
grid_df = pd.DataFrame(grid_coords, columns=["Latitude", "Longitude"])

# Add a dummy vegetation density column to match training format
# You can set all to the most frequent class or infer from nearby known data
grid_df["Vegetation_Density"] = 2  # e.g., medium

# Load the full shapefile (containing many countries)
world_shape = gpd.read_file("Assets_AI/Country_shape.shp")  # Replace with your file path
romania_shape = world_shape[world_shape['SOVEREIGNT'] == 'Romania']

# Convert grid to GeoDataFrame and filter points within Romania
geometry = [Point(lon, lat) for lat, lon in grid_coords]
grid_gdf = gpd.GeoDataFrame(grid_df, geometry=geometry, crs="EPSG:4326")
grid_gdf = grid_gdf[grid_gdf.within(romania_shape.unary_union)]

# Convert back to DataFrame for prediction
grid_df = pd.DataFrame({
    'Latitude': grid_gdf['Latitude'],
    'Longitude': grid_gdf['Longitude'],
    'Vegetation_Density': grid_gdf['Vegetation_Density']
})

# Predict vegetation zone
grid_df['Predicted_Vegetation'] = vegetation_clf.predict(grid_df[['Latitude', 'Longitude', 'Vegetation_Density']])

# Predict fire risk
grid_df['Predicted_Fire_Risk'] = fire_risk_clf.predict(grid_df[['Latitude', 'Longitude', 'Vegetation_Density']])

map_romania = create_fire_risk_map_overlay()#folium.Map(location=[45.9432, 24.9668], zoom_start=6)

# Reduce number of points for visualization (for performance)
sampled_grid = grid_df.sample(n=750, random_state=42)

# Decode color maps
vegetation_colors = {1: 'green', 2: 'yellow', 3: 'saddlebrown', 4: 'gray'}
fire_risk_colors = {1: 'green', 2: 'yellow', 3: 'orange', 4: 'red', 5: 'saddlebrown'}

for _, row in sampled_grid.iterrows():
    lat, lon = row['Latitude'], row['Longitude']
    veg = row['Predicted_Vegetation']
    risk = row['Predicted_Fire_Risk']

    if risk==2.0:
        display_risk="Low"
    elif risk==1.0:
        display_risk="Very Low"
    elif risk==3.0:
        display_risk="Medium"
    elif risk==4.0:
        display_risk="High"

    if risk==3.0:
        display_veg="High_Vegetation"
    elif risk==4.0:
        display_veg="Urban"
    elif risk==1.0:
        display_veg="Low_Vegetation"
    elif risk==2.0:
        display_veg="Medium_Vegetation"
    # Color logic as before
    veg_color = vegetation_colors.get(veg, 'gray')
    fire_color = fire_risk_colors.get(risk, 'gray')

    folium.CircleMarker(
        location=[lat, lon],
        radius=3,
        color=fire_color,
        fill=True,
        fill_color=fire_color,
        fill_opacity=0.4,
        popup=f"Risk: {display_risk} | Vegetation: {display_veg}"
    ).add_to(map_romania)

#map_romania.save("Maps/predicted_romania_map.html")
map_romania.save("Maps/server_romania_map_1.html")
print("Map saved to Maps/predicted_romania_map_1.html")

