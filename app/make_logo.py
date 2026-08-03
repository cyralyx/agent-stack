#!/usr/bin/env python3
"""Generate AgentStack logo PNG (512) + ICO from the SVG design (PIL draw)."""
from PIL import Image, ImageDraw, ImageFilter

SIZE = 512
img = Image.new("RGB", (SIZE, SIZE), "#0f172a")
d = ImageDraw.Draw(img, "RGBA")

def hex_to_rgb(h, a=255):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (a,)

BG_TOP = hex_to_rgb("#1a2b4a")
BG_BOTTOM = hex_to_rgb("#0f172a")
# vertical gradient background
for y in range(SIZE):
    t = y / SIZE
    r = int(BG_TOP[0] * (1 - t) + BG_BOTTOM[0] * t)
    g = int(BG_TOP[1] * (1 - t) + BG_BOTTOM[1] * t)
    b = int(BG_TOP[2] * (1 - t) + BG_BOTTOM[2] * t)
    d.line([(0, y), (SIZE, y)], fill=(r, g, b))

BLUE = hex_to_rgb("#38bdf8")
PURPLE = hex_to_rgb("#a78bfa")
GREEN = hex_to_rgb("#34d399")
DARK = hex_to_rgb("#0f172a")

# --- glow layer for hexagon + nodes ---
glow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
gd = ImageDraw.Draw(glow)

# central hexagon
cx, cy = 256, 256
r_hex = 160
hex_pts = [(cx + r_hex * 0.0, cy - r_hex),
           (cx + r_hex * 0.866, cy - r_hex / 2),
           (cx + r_hex * 0.866, cy + r_hex / 2),
           (cx + r_hex * 0.0, cy + r_hex),
           (cx - r_hex * 0.866, cy + r_hex / 2),
           (cx - r_hex * 0.866, cy - r_hex / 2)]
gd.polygon(hex_pts, outline=BLUE, width=14)
gd.polygon(hex_pts, fill=BLUE[:3] + (20,))
# brain node (center)
d.ellipse([cx-52, cy-52, cx+52, cy+52], fill=DARK, outline=BLUE, width=10)
# brain circuits
gd.line([cx-16, cy-12, cx-8, cy-24, cx, cy-12, cx+8, cy-24, cx+16, cy-12], fill=BLUE, width=5, joint="curve")
gd.line([cx-12, cy+12, cx-4, cy, cx+4, cy+12, cx+12, cy], fill=BLUE, width=5, joint="curve")

# hand node (top)
d.ellipse([cx-34, 140-34, cx+34, 140+34], fill=DARK, outline=PURPLE, width=9)
d.line([cx-10, 140, cx+10, 140], fill=PURPLE, width=6)
d.line([cx, 130, cx, 150], fill=PURPLE, width=6)

# vault node (bottom-left)
d.ellipse([168-34, 360-34, 168+34, 360+34], fill=DARK, outline=GREEN, width=9)
d.rectangle([156, 352, 180, 368], outline=GREEN, width=5)

# council node (bottom-right)
d.ellipse([344-34, 360-34, 344+34, 360+34], fill=DARK, outline=PURPLE, width=9)
d.ellipse([344-10, 356-10, 344+10, 356+10], outline=PURPLE, width=5)
d.arc([334, 366, 354, 384], 0, 180, fill=PURPLE, width=5)

# connections
gd.line([cx, 174, cx, 204], fill=BLUE, width=6)
gd.line([cx-16, 228, 196, 326], fill=GREEN, width=6)
gd.line([cx+16, 228, 316, 326], fill=PURPLE, width=6)
gd.ellipse([cx-4, 186, cx+4, 194], fill=BLUE)
gd.ellipse([214, 274, 222, 282], fill=GREEN)
gd.ellipse([290, 274, 298, 282], fill=PURPLE)

# soft blur glow
glow = glow.filter(ImageFilter.GaussianBlur(3))
img = Image.alpha_composite(img.convert("RGBA"), glow)

# rounded corners on the outer square? Full square bg is fine for app icon.
out = img.convert("RGB")

# --- PNG 512 + 256 + 128 + 64 ---
out.save("app/logo.png")
out.resize((256, 256), Image.LANCZOS).save("app/logo-256.png")
out.resize((128, 128), Image.LANCZOS).save("app/logo-128.png")
out.resize((64, 64), Image.LANCZOS).save("app/logo-64.png")

# --- ICO (multi-size) ---
out.save("app/logo.ico", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])

print("logo.png / logo.ico generated")
