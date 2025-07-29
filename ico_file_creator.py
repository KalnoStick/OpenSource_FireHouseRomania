from PIL import Image

def convert_jpg_to_ico(input_png, output_ico):
    # Open the PNG image file
    with Image.open(input_png) as img:
        # Convert to ICO format and save
        img.save(output_ico, format='ICO')
    print(f"Conversion successful! Saved as {output_ico}")

# Input and output file names
input_png = "Assests_image/icon_img.png"  # Replace with the path to your JPG file
output_ico = "Assests_image/icon.ico"  # Replace with the desired output path for the ICO file

convert_jpg_to_ico(input_png, output_ico)