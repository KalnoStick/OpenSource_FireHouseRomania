from PIL import Image
import pillow_avif
img = Image.open("Assests_image/bk_3.avif")
img.save("Assests_image/bk_3_conv.png")  # Then use in PyQt
