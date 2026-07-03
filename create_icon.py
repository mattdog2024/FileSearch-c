"""Create a simple icon for FileSearch"""
import os

try:
    from PIL import Image, ImageDraw, ImageFont

    # Create 256x256 icon
    img = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw rounded rectangle background (blue gradient effect)
    draw.rounded_rectangle([10, 10, 246, 246], radius=40, fill=(33, 150, 243, 255))

    # Draw search magnifying glass
    draw.ellipse([60, 60, 180, 180], outline='white', width=12)
    draw.line([(140, 140), (200, 200)], fill='white', width=16)

    # Save as ICO
    script_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(script_dir, 'icon.ico')
    img.save(icon_path, format='ICO', sizes=[(256, 256)])
    print(f"Icon created: {icon_path}")

except ImportError:
    # Fallback: create a minimal valid ICO file using raw bytes
    # This is a 16x16 single-color icon
    import struct

    script_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(script_dir, 'icon.ico')

    # Minimal ICO header + BMP data
    ico_data = bytearray()
    # ICO header
    ico_data.extend(struct.pack('<HHH', 0, 1, 1))  # reserved, type=icon, count=1
    # Image directory entry
    ico_data.extend(struct.pack('<BBBBHHII',
        16, 16, 0, 0,  # width, height, colors, reserved
        1, 32,  # planes, bpp
        40 + 16*16*4 + 16*16//8,  # size of bitmap info + pixels + mask
        22  # offset to bitmap data
    ))
    # BMP info header
    ico_data.extend(struct.pack('<IIIHHIIIIII',
        40,  # header size
        16, 16*2,  # width, height (doubled for XOR+AND masks)
        1, 32,  # planes, compression
        16*16*4, 0, 0, 0, 0  # image size, resolution
    ))
    # Pixel data (blue color)
    for y in range(16):
        for x in range(16):
            ico_data.extend(struct.pack('<BBBB', 243, 150, 33, 255))  # BGRA blue
    # AND mask (1 bit per pixel, padded to 4 bytes)
    for y in range(16):
        ico_data.extend(b'\x00' * ((16 + 31) // 32 * 4))

    with open(icon_path, 'wb') as f:
        f.write(ico_data)
    print(f"Icon created (fallback): {icon_path}")
