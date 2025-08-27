import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.model_selection import KFold
import folium
import pyarrow.parquet as pq
import dask.dataframe as dd
import geopandas as gpd
from shapely.geometry import Point
from flask_app import create_fire_risk_map_overlay

df = dd.read_parquet('csv_support/fire_data.parquet', columns=['Latitude', 'Longitude', 'Vegetation_Density', 'Fire_Risk'])

# Convertion categorical columns using Dask map with metadata
veg_map_sn = {'High_Vegetation':1,'Medium_Vegetation':2,'Low_Vegetation':3,'Urban':4}
risk_map_sn = {'Very Low':1,'Low':2,'Medium':3,'High':4,'Unknown':0}

df['Vegetation_Density'] = df['Vegetation_Density'].map(veg_map_sn, meta=('Vegetation_Density','float64')).fillna(0).astype('int64')
df['Fire_Risk'] = df['Fire_Risk'].map(risk_map_sn, meta=('Fire_Risk','float64')).fillna(0).astype('int64')

sample_df = df[df['Fire_Risk'] != 0].sample(frac=0.05, random_state=42).compute()

known_data = sample_df
unknown_data = pd.DataFrame(columns=sample_df.columns)  # empty

'''
# Separate known and unknown fire risk labels
known_data = df[df['Fire_Risk'] != 0]  # Known fire risk values
unknown_data = df[df['Fire_Risk'] == 0]  # Unknown fire risk values
'''

x_veg = known_data[['Latitude', 'Longitude']].values  # Features for training
y_veg = known_data['Vegetation_Density'].values  # Vegetation prediction target
#y_fire_risk = known_data['Fire_Risk']  # Fire risk prediction target

#Data Shuffle-accuracy
kf = KFold(n_splits=5, shuffle=True, random_state=42)
veg_oof = np.zeros(len(known_data), dtype=int)

# Model Training
"""
if len(X) > 0:
    X_train, X_test, y_train_veg, y_test_veg = train_test_split(X, y_vegetation, test_size=0.2, random_state=42)
    vegetation_clf = RandomForestClassifier(n_estimators=100, random_state=42)
    vegetation_clf.fit(X_train, y_train_veg)
    print(f"Vegetation Model Accuracy: {accuracy_score(y_test_veg, vegetation_clf.predict(X_test)):.2f}")

    X_train, X_test, y_train_fire, y_test_fire = train_test_split(X, y_fire_risk, test_size=0.2, random_state=42)
    fire_risk_clf = RandomForestClassifier(n_estimators=100, random_state=42)
    fire_risk_clf.fit(X_train, y_train_fire)
    print(f"Fire Risk Model Accuracy: {accuracy_score(y_test_fire, fire_risk_clf.predict(X_test)):.2f}")
"""

for tr, va in kf.split(x_veg):
    m = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    m.fit(x_veg[tr],y_veg[tr])
    veg_oof[va] = m.predict(x_veg[va])

#Complete=pred+model veg
vegetation_clf = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
vegetation_clf.fit(x_veg, y_veg)

#Fire model + prediction
x_fire = np.c_[known_data['Latitude'].values,
               known_data['Longitude'].values,
               veg_oof]
y_fire = known_data['Fire_Risk'].values

fire_risk_clf = RandomForestClassifier(n_estimators=300, random_state=42, n_jobs=-1)
fire_risk_clf.fit(x_fire, y_fire)
"""    # Predict missing data
    if not unknown_data.empty:
        X_unknown = unknown_data[['Latitude', 'Longitude']]
        unknown_data['Vegetation_Density'] = vegetation_clf.predict(X_unknown)
        unknown_data['Fire_Risk'] = fire_risk_clf.predict(X_unknown)

    complete_df = pd.concat([known_data, unknown_data])
else:
    raise ValueError("No data available for training.")"""

# complete_df.to_csv('updated_forest_data.csv', index=False)
print("Model trained and predictions made!")

# Bounding box of Romania
min_lat, max_lat = 43.6, 48.3
min_lon, max_lon = 20.2, 29.7

# Grid resolution
step = 0.05  # 5km/step

# Grid of coordinates
latitudes = np.arange(min_lat, max_lat, step)
longitudes = np.arange(min_lon, max_lon, step)
grid_coords = [(lat, lon) for lat in latitudes for lon in longitudes]

# DataFrame from generated coordinates
grid_df = pd.DataFrame(grid_coords, columns=["Latitude", "Longitude"])

#grid_df["Vegetation_Density"] = 2

world_shape = gpd.read_file("Assets_AI/Country_shape.shp")
romania_shape = world_shape[world_shape['SOVEREIGNT'] == 'Romania']

# Point filter
geometry = [Point(lon, lat) for lat, lon in grid_coords]
grid_gdf = gpd.GeoDataFrame(grid_df, geometry=geometry, crs="EPSG:4326")
grid_gdf = grid_gdf[grid_gdf.within(romania_shape.unary_union)]

# Back to DataFrame for prediction
grid_df = pd.DataFrame({
    'Latitude': grid_gdf['Latitude'],
    'Longitude': grid_gdf['Longitude']
})

# Predict vegetation zone
grid_df['Predicted_Vegetation'] = vegetation_clf.predict(grid_df[['Latitude', 'Longitude']].values)

# Predict fire risk
grid_df['Predicted_Fire_Risk'] = fire_risk_clf.predict(
    np.c_[grid_df['Latitude'].values, grid_df['Longitude'].values, grid_df['Predicted_Vegetation'].values]
)

map_romania = create_fire_risk_map_overlay()

# Number of points for visualization
sampled_grid = grid_df.sample(n=750, random_state=42)

vegetation_colors = {1: 'green', 2: 'yellow', 3: 'saddlebrown', 4: 'gray'}
fire_risk_colors = {1: 'green', 2: 'yellow', 3: 'orange', 4: 'red', 5: 'saddlebrown'}

for _, row in sampled_grid.iterrows():
    lat, lon = row['Latitude'], row['Longitude']
    veg = row['Predicted_Vegetation']
    risk = row['Predicted_Fire_Risk']

    veg_name = {1: 'High_Vegetation', 2: 'Medium_Vegetation', 3: 'Low_Vegetation', 4: 'Urban'}[int(veg)]
    risk_name = {1: 'Very Low', 2: 'Low', 3: 'Medium', 4: 'High'}[int(risk)]

    veg_color = vegetation_colors.get(veg, 'gray')
    fire_color = fire_risk_colors.get(risk, 'gray')

    folium.CircleMarker(
        location=[lat, lon],
        radius=3,
        color=fire_color,
        fill=True,
        fill_color=fire_color,
        fill_opacity=0.4,
        popup=f"Risk: {risk_name} | Vegetation: {veg_name}"
    ).add_to(map_romania)

#map_romania.save("Maps/predicted_romania_map.html")
map_romania.save("Maps/server_romania_map_1.html")
print("Map saved to Maps/predicted_romania_map_1.html")

import joblib
import os

os.makedirs("models", exist_ok=True)
joblib.dump(vegetation_clf, "models/vegetation_rf.joblib")
joblib.dump(fire_risk_clf, "models/fire_rf.joblib")