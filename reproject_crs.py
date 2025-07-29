import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling

# List of input raster files
input_rasters = ['Assets_AI/Bucharest_map_1.tif', 'Assets_AI/Bucharest_map_2.tif','Assets_AI/Bucharest_map_3.tif', 'Assets_AI/Bucharest_map_4.tif']
output_rasters = ['Coordinate_rasters/output_raster_1.tif', 'Coordinate_rasters/output_raster_2.tif','Coordinate_rasters/output_raster_3.tif', 'Coordinate_rasters/output_raster_4.tif']

# Desired target CRS (WGS84 - EPSG:4326)
target_crs = 'EPSG:4326'

# Loop through the input files and process each one
for input_raster, output_raster in zip(input_rasters, output_rasters):
    with rasterio.open(input_raster) as src:
        print(f"Processing {input_raster}")
        print(f"Input CRS: {src.crs}")
        print(f"Input bounds: {src.bounds}")

        # Calculate the transform and new dimensions for the output raster
        transform, width, height = calculate_default_transform(
            src.crs, target_crs, src.width, src.height, *src.bounds)

        # Prepare metadata for the output raster
        kwargs = src.meta.copy()
        kwargs.update({
            'crs': target_crs,  # Update CRS to target CRS
            'transform': transform,  # Apply the new affine transformation
            'width': width,  # New width (reprojected)
            'height': height  # New height (reprojected)
        })

        # Create the output raster and apply reprojection
        with rasterio.open(output_raster, 'w', **kwargs) as dst:
            for i in range(1, src.count + 1):  # Iterate over all bands (if multiple bands)
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=target_crs,
                    resampling=Resampling.nearest  # Adjust resampling method as needed
                )

        print(f"Reprojection for {input_raster} completed and saved as '{output_raster}'.")

print("Reprojection for all files completed.")
