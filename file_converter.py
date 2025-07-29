import rasterio
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image
from skimage.transform import resize
from affine import Affine
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.crs import CRS
import os

#Function that classifies the fire risk based on the grayscale value
def fire_risk_from_grayscale(pixel_value):
    if pixel_value > 180:
        return 'Very Low'
    elif pixel_value > 120:
        return 'Low'
    elif pixel_value > 80:
        return 'Medium'
    else:
        return 'High'

# Function to classify the color of each pixel (using RGB or grayscale values)
def classify_vegetation(r, g, b, is_rgb=True):
    if is_rgb:
        # RGB-based classification
        # Green tones are high vegetation
        if g > 100 and r < 80 and b < 80:
            return 'High_Vegetation'
        # Yellow and Orange tones are medium vegetation
        elif g > 100 and r > 80 and b < 80:
            return 'Medium_Vegetation'
        # Red and brown tones are low/no vegetation
        elif r > 100 and g < 80 and b < 80:
            return 'Low_Vegetation'
        # Grey tones represent urban areas (e.g., cities)
        else:
            return 'Urban'
    else:
        # Grayscale-based classification
        # Higher values correspond to higher vegetation (arbitrary threshold for demonstration)
        if r > 150:
            return 'High_Vegetation'
        elif r > 100:
            return 'Medium_Vegetation'
        else:
            return 'Low_Vegetation'

# Function to process the TIF file and extract data for the CSV
def process_tif_to_csv(tif_file_paths, output_dir='csv_chunks', batch_size=28_000_000, scale_factor=0.5):
    os.makedirs(output_dir, exist_ok=True)
    file_counter = 1
    data_batch = []
    for tif_file_path in tif_file_paths:
        with rasterio.open(tif_file_path) as src:
            # Check the number of bands
            num_bands = src.count
            print(f"Number of bands in {tif_file_path}: {num_bands}")

            # If the image has 3 bands (RGB), assume it's an RGB image
            if num_bands >= 3:
                image_data = src.read([1, 2, 3])  # RGB channels are in bands 1, 2, 3
                image_data = np.moveaxis(image_data, 0, -1)  # Reorganize to shape (height, width, 3)
                is_rgb = True
            else:
                # If it's a single band, we assume it's grayscale (1-band image)
                image_data = src.read(1)  # Read single band
                image_data = np.expand_dims(image_data, axis=-1)  # Reshape to (height, width, 1)
                is_rgb = False

                """# Check and reproject if the CRS is not EPSG:4326
                if src.crs != CRS.from_epsg(4326):
                    # Reproject to EPSG:4326
                    dst_crs = CRS.from_epsg(4326)  # Target CRS (WGS84)
                    transform, width, height = calculate_default_transform(
                        src.crs, dst_crs, src.width, src.height, *src.bounds)

                    # Create an empty array to hold the reprojected data
                    reprojected_image = np.empty((height, width, num_bands), dtype=np.uint8)

                    # Perform the reprojection for each band
                    for band in range(num_bands):
                        reproject(
                            source=rasterio.band(src, band + 1),  # Read the band (1-based index)
                            destination=reprojected_image[:, :, band],
                            src_transform=src.transform,
                            src_crs=src.crs,
                            dst_transform=transform,
                            dst_crs=dst_crs,
                            resampling=Resampling.nearest
                        )

                    image_data_resized = reprojected_image  # Reprojected image data

                else:
                    image_data_resized = image_data  # No need to reproject if already EPSG:4326"""

            # Downsample factor (e.g., 0.5 for 2x smaller, 0.25 for 4x smaller)
            scale_factor = 0.5

            if is_rgb:
                resized = resize(image_data,
                                 (int(image_data.shape[0] * scale_factor), int(image_data.shape[1] * scale_factor), 3),
                                 anti_aliasing=True)
            else:
                resized = resize(image_data,
                                 (int(image_data.shape[0] * scale_factor), int(image_data.shape[1] * scale_factor), 1),
                                 anti_aliasing=True)
            image_data_resized = (resized * 255).astype(np.uint8)  # convert back to uint8 if needed

            # Extract metadata (for example, georeferencing)
            transform = src.transform
            width, height = image_data_resized.shape[1], image_data_resized.shape[0]

            # Process each pixel (in a vectorized way)
            for i in range(height):
                for j in range(width):
                    if is_rgb:  # RGB image
                        r, g, b = image_data_resized[i, j]
                    else:  # Single-band image, grayscale
                        r = g = b = image_data_resized[i, j]  # Use the same value for all channels

                    # Classify the vegetation based on RGB or grayscale values
                    zone_type = classify_vegetation(r, g, b, is_rgb)

                    # Calculate the latitude and longitude for this pixel
                    lon, lat = transform * (j, i)

                    #Calculate the fire risk
                    zone_risk=fire_risk_from_grayscale(r)

                    # Add the data for this pixel
                    data_batch.append({
                        'Latitude': lat,
                        'Longitude': lon,
                        'Vegetation_Density': zone_type,
                        'Fire_Risk': zone_risk  # Placeholder, you can use a more advanced classification here
                    })

                    # Write in chunks
                    if len(data_batch) >= batch_size:
                        out_path = os.path.join(output_dir, f"forest_data_part_{file_counter}.csv")
                        pd.DataFrame(data_batch).to_csv(out_path, index=False)
                        print(f"Saved chunk {file_counter}: {out_path}")
                        file_counter += 1
                        data_batch = []
    # Write remaining data
    if data_batch:
        out_path = os.path.join(output_dir, f"forest_data_{file_counter}.csv")
        pd.DataFrame(data_batch).to_csv(out_path, index=False)
        print(f"Saved final chunk {file_counter}: {out_path}")

    # Convert the data into a Pandas DataFrame and save as CSV
    #df = pd.DataFrame(data)
    #df.to_csv('forest_data.csv', index=False)
    print("CSV file created successfully!")

# Function to display the TIF images
def display_tif_images(tif_file_paths):
    fig, axes = plt.subplots(1, len(tif_file_paths), figsize=(15, 5))

    for ax, tif_file_path in zip(axes, tif_file_paths):
        img = Image.open(tif_file_path)
        ax.imshow(img)
        ax.set_title(tif_file_path)
        ax.axis('off')

    plt.tight_layout()
    plt.show()


# List of TIF files to process
tif_file_paths = ["Coordinate_rasters/output_raster_1.tif", "Coordinate_rasters/output_raster_2.tif","Coordinate_rasters/output_raster_3.tif", "Coordinate_rasters/output_raster_4.tif"]

# Display the images
#display_tif_images(tif_file_paths)

# Process the TIF files and create the CSV
process_tif_to_csv(tif_file_paths)




"""
import rasterio
import numpy as np
import pandas as pd
from rasterio.windows import Window

# Function to classify vegetation based on pixel color
def classify_vegetation(r, g, b, is_rgb=True):
    if is_rgb:
        if g > 100 and r < 80 and b < 80:
            return 'High_Vegetation'
        elif g > 100 and r > 80 and b < 80:
            return 'Medium_Vegetation'
        elif r > 100 and g < 80 and b < 80:
            return 'Low_Vegetation'
        else:
            return 'Urban'
    else:
        if r > 150:
            return 'High_Vegetation'
        elif r > 100:
            return 'Medium_Vegetation'
        else:
            return 'Low_Vegetation'

# Tiling-enabled function that supports both 1-band and 3-band TIF files
def process_tif_to_csv(tif_file_paths):
    data = []
    tile_size = 512  # You can adjust this depending on memory limits

    for tif_file_path in tif_file_paths:
        with rasterio.open(tif_file_path) as src:
            num_bands = src.count
            width, height = src.width, src.height
            transform = src.transform

            print(f"Processing {tif_file_path} | Bands: {num_bands} | Size: {width}x{height}")

            is_rgb = num_bands >= 3  # Treat anything with 3+ bands as RGB

            for row in range(0, height, tile_size):
                for col in range(0, width, tile_size):
                    win_height = min(tile_size, height - row)
                    win_width = min(tile_size, width - col)
                    window = Window(col, row, win_width, win_height)

                    # Read the image tile
                    if is_rgb:
                        try:
                            tile_data = src.read([1, 2, 3], window=window)  # shape: (3, h, w)
                            tile_data = np.moveaxis(tile_data, 0, -1)      # shape: (h, w, 3)
                        except:
                            print(f" RGB read failed in {tif_file_path}, falling back to grayscale.")
                            is_rgb = False
                    if not is_rgb:
                        tile_data = src.read(1, window=window)
                        tile_data = np.expand_dims(tile_data, axis=-1)  # shape: (h, w, 1)

                    # Process every pixel in the tile
                    for i in range(tile_data.shape[0]):
                        for j in range(tile_data.shape[1]):
                            if is_rgb:
                                r, g, b = tile_data[i, j]
                            else:
                                val = tile_data[i, j][0]
                                r = g = b = val  # Use the same value for grayscale

                            zone_type = classify_vegetation(r, g, b, is_rgb)
                            global_i = row + i
                            global_j = col + j
                            lon, lat = transform * (global_j, global_i)

                            data.append({
                                'Latitude': lat,
                                'Longitude': lon,
                                'Vegetation_Density': zone_type,
                                'Fire_Risk': 'Unknown'  # Placeholder
                            })

    # Convert the collected data to CSV
    df = pd.DataFrame(data)
    df.to_csv('forest_data.csv', index=False)
    print(" CSV file created successfully!")

# List of TIF files to process
tif_file_paths = ["Assets_AI/Bucharest_map_1.tif", "Assets_AI/Bucharest_map_2.tif"]

# Process them
process_tif_to_csv(tif_file_paths)
"""