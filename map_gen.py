import pandas as pd
import folium
from folium import plugins

# Function to load and process CSV data
def load_data(csv_path):
    # Read CSV
    df = pd.read_csv(csv_path)
    # Display the first few rows of the dataset to check if it loaded correctly
    print(df.head())
    return df


# Function to map fire risk to colors based on Vegetation_Density
def get_risk_color(risk):
    """Map fire risk level to color."""
    risk_color_map = {
        'Low_Vegetation': 'red',  # High risk (red)
        'Medium_Vegetation': 'orange',  # Medium risk (orange)
        'High_Vegetation': 'yellow',  # Low risk (yellow)
        'Urban': 'gray'  # Urban areas might not be relevant, colored gray
    }
    return risk_color_map.get(risk, 'gray')  # Default to gray if the risk level is unknown


# Function to create an interactive map of Romania based on the CSV data
def create_interactive_map(df):
    # Create a Folium map centered on Romania's approximate coordinates
    m = folium.Map(location=[45.9432, 24.9668], zoom_start=7)

    # Loop through each row in the CSV data and plot the point on the map
    for index, row in df.iterrows():
        # Get latitude, longitude, and fire risk (Vegetation_Density)
        lat = row['Latitude']
        lon = row['Longitude']
        risk = row['Vegetation_Density']

        # Map the vegetation density (fire risk) to a color
        color = get_risk_color(risk)

        # Create a popup message with some details about the point
        popup_message = f"Lat: {lat}, Lon: {lon}<br>Fire Risk: {risk}"

        # Create a marker on the map for each point
        folium.CircleMarker(
            location=[lat, lon],
            radius=15,  # Size of the circle
            color=color,  # Color based on the vegetation/fire risk
            fill=True,  # Fill the circle
            fill_color=color,  # Fill color matches the border color
            fill_opacity=0.7,  # Transparency of the fill
            popup=popup_message  # Show details when clicked
        ).add_to(m)

    # Save the map to an HTML file
    m.save('Maps/romania_calamity_map.html')
    print("Interactive map saved as 'romania_calamity_map.html'")


# Main program to load data and create the interactive map
def main():
    # Path to the CSV file with coordinates and vegetation/fire risk data
    csv_path = 'test.csv'

    # Load the data from CSV
    df = load_data(csv_path)

    # Create an interactive map with calamity risk data
    create_interactive_map(df)


if __name__ == "__main__":
    main()
