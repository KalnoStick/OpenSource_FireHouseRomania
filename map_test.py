import sys
import folium
import os
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
from PyQt5.QtWebEngineWidgets import QWebEngineView

# Function to create the Folium map
def create_folium_map():
    romania_center = [45.9432, 24.9668]  # Latitude and Longitude for Romania's central point)
    # Create a map centered around Romania
    romania_map = folium.Map(location=romania_center, zoom_start=7)

    # Define some forest zones (sample coordinates)
    forest_zones = [
        {
            'name': 'Forest Zone 1',
            'coordinates': [
                [40.748817, -73.985428],
                [40.748917, -73.985528],
                [40.749017, -73.985628],
                [40.749117, -73.985728]
            ]
        },
        {
            'name': 'Forest Zone 2',
            'coordinates': [
                [40.750817, -73.986428],
                [40.750917, -73.986528],
                [40.751017, -73.986628],
                [40.751117, -73.986728]
            ]
        }
    ]
    romania_border = [
        [48.2667, 26.0000], [48.2000, 24.8000], [47.4000, 24.3000],
        [46.0000, 23.0000], [45.0000, 23.0000], [44.0000, 24.0000],
        [43.0000, 25.0000], [42.0000, 26.0000], [41.0000, 28.0000],
        [41.0000, 29.0000], [42.0000, 30.0000], [43.0000, 30.0000],
        [44.0000, 29.0000], [45.0000, 28.0000], [45.9432, 24.9668]  # Central point back to close polygon
    ]

    folium.Polygon(
        locations=romania_border,
        color='blue',  # Border color
        weight=2,
        fill=True,
        fill_color='blue',
        fill_opacity=0.1,
        popup="Romania"
    ).add_to(romania_map)
    # Loop through forest zones and add polygons to the map
    for zone in forest_zones:
        folium.Polygon(
            locations=zone['coordinates'],
            color='red',
            weight=2,
            fill=True,
            fill_color='red',
            fill_opacity=0.3,
            popup=zone['name']
        ).add_to(romania_map)

    # Save the map to an HTML file
    map_html_path = os.path.abspath("Maps/forest_zones_map.html")  # Get the absolute path
    print(f"Map saved at: {map_html_path}")  # Output file path to verify
    romania_map.save(map_html_path)
    return map_html_path

# PyQt5 Application to display the map
class MapWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('Forest Zones Map')
        self.setGeometry(100, 100, 800, 600)

        # Create a layout
        layout = QVBoxLayout()

        # Create the map in Folium and get the path to the saved HTML file
        map_html_path = create_folium_map()

        # Create a QWebEngineView to display the HTML map file
        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl.fromLocalFile(map_html_path))  # Load the local HTML file

        # Add the browser to the layout
        layout.addWidget(self.browser)

        # Set the layout for the window
        self.setLayout(layout)

        # Optionally, add a button to close the window
        close_button = QPushButton('Close', self)
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

# Main function to run the application
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MapWindow()
    window.show()
    sys.exit(app.exec_())
