import os
from PIL import Image, ImageDraw

def create_app_icon(output_dir="."):
    sizes = [(1024, 1024), (512, 512), (256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    images = []

    for size in sizes:
        w, h = size
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Rounded rectangle background with vibrant gradient / modern color
        # Red / Violet modern gradient style
        r = int(w * 0.22)
        # Background rounded rect
        draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=(235, 32, 58)) # YouTube/Media Red accent

        # Inner subtle gradient overlay (top-left highlight)
        highlight = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        hdraw = ImageDraw.Draw(highlight)
        hdraw.rounded_rectangle([0, 0, w - 1, int(h * 0.55)], radius=r, fill=(255, 255, 255, 35))
        img = Image.alpha_composite(img, highlight)
        draw = ImageDraw.Draw(img)

        # Draw a sleek Play triangle + Downward arrow combo
        cx, cy = w / 2, h / 2
        s = w / 256.0  # scale factor

        # Download arrow
        arrow_w = 42 * s
        arrow_h = 75 * s
        shaft_top = cy - 50 * s
        shaft_bot = cy + 10 * s

        # Arrow shaft
        draw.rectangle([cx - arrow_w / 2, shaft_top, cx + arrow_w / 2, shaft_bot], fill=(255, 255, 255))
        
        # Arrow head (triangle)
        tip_y = cy + 50 * s
        head_w = 85 * s
        draw.polygon([
            (cx, tip_y),
            (cx - head_w / 2, shaft_bot),
            (cx + head_w / 2, shaft_bot)
        ], fill=(255, 255, 255))

        # Bottom base bar / tray
        tray_y = cy + 65 * s
        tray_h = 16 * s
        tray_w = 110 * s
        draw.rounded_rectangle(
            [cx - tray_w / 2, tray_y, cx + tray_w / 2, tray_y + tray_h],
            radius=int(6 * s) if s >= 0.2 else 1,
            fill=(255, 255, 255)
        )

        images.append(img)

    png_path = os.path.join(output_dir, "app_icon.png")
    ico_path = os.path.join(output_dir, "app_icon.ico")
    icns_path = os.path.join(output_dir, "app_icon.icns")

    # Save PNG (512x512)
    images[1].save(png_path, "PNG")

    # Save ICO for Windows
    ico_sizes = [(s[0], s[1]) for s in sizes if s[0] <= 256]
    images[2].save(ico_path, format="ICO", sizes=ico_sizes)

    # Save ICNS for macOS
    try:
        images[0].save(icns_path, format="ICNS")
    except Exception as e:
        print(f"ICNS save warning: {e}")

    print(f"Generated icons: {png_path}, {ico_path}, {icns_path}")

if __name__ == "__main__":
    create_app_icon()
