import rasterio
import matplotlib.pyplot as plt
import numpy as np
import os
import numpy as np
from PIL import Image

# Input directory containing your TIFF files
input_dir = "Assets_AI/"
output_dir = "overlays/"

# Ensure output directory exists
os.makedirs(output_dir, exist_ok=True)

# Loop over all .tif files in the input directory
for tif_file in os.listdir(input_dir):
    if tif_file.endswith(".tif"):  # Process only .tif files
        tif_path = os.path.join(input_dir, tif_file)
        output_path = os.path.join(output_dir, tif_file.replace(".tif", ".png"))

        print(f"Processing: {tif_path}")

        # Open the .tif file
        with rasterio.open(tif_path) as src:
            count = src.count
            print(f"  Bands detected: {count}")

            if count >= 3:
                # If at least 3 bands, assume RGB
                image = src.read([1, 2, 3])  # Read first 3 bands (R, G, B)
                image = np.transpose(image, (1, 2, 0))  # Convert to (H, W, 3)
            else:
                # If only 1 band, treat as grayscale
                image = src.read(1)  # Read single band (H, W)
                image = np.stack([image] * 3, axis=-1)  # Convert grayscale to 3-channel image

            # Normalize image for visualization
            image = image.astype(np.float32)
            image -= image.min()  # Min-Max normalization
            image /= image.max()

            # Resize image before saving as PNG (to reduce file size)
            img = Image.fromarray((image * 255).astype(np.uint8))  # Convert back to uint8 for saving
            img = img.convert("RGB")  # Convert to ensure compatibility
            img = img.resize((800, 800))  # Resize to 800x800 pixels
            img.save(output_path, format="PNG", optimize=True)
            print(f"PNG saved at: {output_path}")

            # Get bounds for Leaflet overlay
            bounds = src.bounds
            print(f"Bounds for overlay: [[{bounds.bottom}, {bounds.left}], [{bounds.top}, {bounds.right}]]")

        print("File completed!")

