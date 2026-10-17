# Generates public/og-image.png (1200x630) and public/logo.png (512x512).
# Usage: python3 scripts/make_og_image.py public   (needs Pillow + DejaVu fonts)
import sys
from PIL import Image, ImageDraw, ImageFont
out = sys.argv[1]
BG, ACCENT, TEXT, MUTED = "#0f1117", "#5b8cff", "#e6e8ee", "#9aa3b2"
F = "/usr/share/fonts/truetype/dejavu/"

def sparkle(d, cx, cy, s, width):
    # favicon path scaled: big 4-point star + small one, in a 24-unit box
    big = [(12,3),(13.9,7.6),(18.5,9.5),(13.9,11.4),(12,16),(10.1,11.4),(5.5,9.5),(10.1,7.6)]
    small = [(18.5,15.5),(19.3,17.5),(21.3,18.3),(19.3,19.1),(18.5,21.1),(17.7,19.1),(15.7,18.3),(17.7,17.5)]
    for pts in (big, small):
        p = [(cx + (x-12)*s, cy + (y-12)*s) for x, y in pts]
        d.line(p + [p[0]], fill=ACCENT, width=width, joint="curve")

img = Image.new("RGB", (1200, 630), BG)
d = ImageDraw.Draw(img)
glow = Image.new("RGB", (1200, 630), BG)
gd = ImageDraw.Draw(glow)
for r in range(420, 0, -6):
    t = 1 - r/420
    c = tuple(int(b + (v-b)*t*0.35) for b, v in zip((15,17,23),(91,140,255)))
    gd.ellipse([1050-r, 80-r, 1050+r, 80+r], fill=c)
img = Image.blend(img, glow, 1.0)
d = ImageDraw.Draw(img)
d.rounded_rectangle([80, 80, 176, 176], radius=24, fill="#171a23", outline="#2a2f3c", width=2)
sparkle(d, 128, 128, 3.6, 6)
d.text((200, 100), "Academic Co-Pilot", font=ImageFont.truetype(F+"DejaVuSans-Bold.ttf", 44), fill=TEXT)
title = ImageFont.truetype(F+"DejaVuSerif-Bold.ttf", 66)
d.text((80, 250), "From research goal", font=title, fill=TEXT)
d.text((80, 330), "to finished draft.", font=title, fill=TEXT)
d.text((80, 450), "Literature screening · PDF ingestion · Drafting with citations · Data analysis",
       font=ImageFont.truetype(F+"DejaVuSans.ttf", 26), fill=MUTED)
d.text((80, 520), "AI research assistant  ·  Pay as you go", font=ImageFont.truetype(F+"DejaVuSans-Bold.ttf", 28), fill=ACCENT)
img.save(f"{out}/og-image.png", optimize=True)

logo = Image.new("RGB", (512, 512), BG)
ld = ImageDraw.Draw(logo)
sparkle(ld, 256, 256, 19, 30)
logo.save(f"{out}/logo.png", optimize=True)
