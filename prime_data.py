# Import necessary libraries
import rasterio
import numpy as np
import pandas as pd
import folium
from folium import raster_layers
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib


# --- Step 1: Extract Features from GeoTIFF and Create CSV ---
def read_tif(file_path):
    with rasterio.open(file_path) as src:
        img_data = src.read(1)  # Read the first band
        metadata = src.meta
        bounds = src.bounds
        transform = src.transform
    return img_data, metadata, bounds, transform


def georeference_to_lat_lon(row, col, transform):
    """Convert pixel row, col to latitude, longitude"""
    lon, lat = rasterio.transform.xy(transform, row, col)
    return lat, lon


def generate_csv_from_tif(img_data, metadata, bounds, transform, output_csv):
    rows, cols = img_data.shape
    data = []

    for row in range(rows):
        for col in range(cols):
            # Convert pixel position to lat, lon
            lat, lon = georeference_to_lat_lon(row, col, transform)

            # Example features (you can modify this based on your actual analysis)
            vegetation_density = img_data[row, col]  # This could be a vegetation index
            fire_risk = calculate_fire_risk(vegetation_density, lat, lon)  # Placeholder
            urban_proximity = calculate_urban_proximity(lat, lon)  # Placeholder
            slope = calculate_slope(lat, lon)  # Placeholder

            # Add data to list
            data.append([lat, lon, vegetation_density, fire_risk, urban_proximity, slope])

    # Create DataFrame
    df = pd.DataFrame(data,
                      columns=['Latitude', 'Longitude', 'Vegetation_Density', 'Fire_Risk', 'Urban_Proximity', 'Slope'])

    # Save to CSV
    df.to_csv(output_csv, index=False)
    print(f"CSV saved as {output_csv}")


def calculate_fire_risk(vegetation_density, lat, lon):
    """Placeholder for fire risk calculation based on vegetation and other factors"""
    return vegetation_density * 0.5  # Example logic


def calculate_urban_proximity(lat, lon):
    """Placeholder for proximity to urban areas (example)"""
    return 1 if (lat < 46.0 and lon < 26.0) else 0  # Example: closer to urban areas in Romania


def calculate_slope(lat, lon):
    """Placeholder for slope calculation"""
    return np.random.uniform(0, 45)  # Random slope for now


# --- Step 2: Map the Data with Colors (Fire Risk Zones) ---
def create_fire_risk_map(csv_file, output_map):
    df = pd.read_csv(csv_file)
    map_center = [45.9432, 24.9668]  # Romania's approximate coordinates
    m = folium.Map(location=map_center, zoom_start=6)

    def get_color(fire_risk):
        if fire_risk > 0.7:
            return 'red'
        elif fire_risk > 0.3:
            return 'orange'
        else:
            return 'yellow'

    for _, row in df.iterrows():
        fire_risk = row['Fire_Risk']
        color = get_color(fire_risk)

        folium.CircleMarker(
            location=[row['Latitude'], row['Longitude']],
            radius=5,
            color=color,
            fill=True,
            fill_opacity=0.6
        ).add_to(m)

    m.save(output_map)
    print(f"Map saved as {output_map}")


# --- Step 3: AI Model for Fire Risk Prediction ---
def train_fire_risk_model(csv_file):
    df = pd.read_csv(csv_file)
    X = df[['Vegetation_Density', 'Urban_Proximity', 'Slope']]
    y = df['Fire_Risk']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
    rf_model.fit(X_train, y_train)

    y_pred = rf_model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Model Accuracy: {accuracy * 100:.2f}%")

    joblib.dump(rf_model, 'fire_risk_model.pkl')


# --- Main Program Flow ---
def main():
    tif_file = 'Assets_AI/Bucharest_map_1.tif'  # Path to your TIF file
    output_csv = 'forest_data.csv'
    output_map = 'fire_risk_map.html'

    # Step 1: Read TIF and generate CSV
    img_data, metadata, bounds, transform = read_tif(tif_file)
    generate_csv_from_tif(img_data, metadata, bounds, transform, output_csv)

    # Step 2: Generate Fire Risk Map
    create_fire_risk_map(output_csv, output_map)

    # Step 3: Train AI Model
    train_fire_risk_model(output_csv)


if __name__ == "__main__":
    main()
