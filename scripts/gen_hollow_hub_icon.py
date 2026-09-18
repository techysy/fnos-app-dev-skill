#!/usr/bin/env python3
"""Generate a Material-Symbols-outlined-style 'hub' network app icon with HOLLOW ring nodes.

Matches the official 9Router `material-symbols-outlined` hub logo: orange diagonal-gradient
rounded square + white hollow-ring hub with **1 center node + 5 surrounding nodes in a
pentagon** (total 6 rings: one large center + five smaller outer).

IMPORTANT:
- The raw Material Symbols outlined SVG <path> has FILLED discs, not hollow rings. Draw hollow
  rings manually to match the authentic look.
- Node count/layout was CONFIRMED against the official logo reference: 6 rings total (1 center
  + 5 outer pentagon). Earlier attempts wrongly used a 4-node cross — the user corrected it.

Usage:
    cd <repo>   # must be where ICON.PNG / app/ui/images/ live
    python3 gen_hollow_hub_icon.py            # writes all 5 fnOS icon sizes
    python3 gen_hollow_hub_icon.py preview    # optional: write a 512 preview to /tmp

Outputs: ICON.PNG (64), ICON_256.PNG (256), app/ui/images/icon_{64,128,256}.png
"""
from PIL import Image, ImageDraw
import math, sys

# 9Router official brand gradient (globals.css --color-brand-500 / --color-brand-700)
C1 = (0xE5, 0x6A, 0x4A)   # top-left  brand-500
C2 = (0xa6, 0x40, 0x27)   # bottom-right brand-700
CORNER_FRAC = 0.24        # rounded-rect radius as fraction of size
R_FRAC = 0.30             # surrounding-node distribution radius (center -> node center)
CENTER_R_FRAC = 0.12      # center ring radius (fraction of size) — larger than outer nodes
NODE_R_FRAC = 0.075       # outer node ring radius (fraction of size)
STROKE_FRAC = 0.045       # line/ring stroke width (fraction of size; medium-bold)

def lerp(a, b, t):
    return int(a + (b - a) * t)

def make_gradient_bg(w, h, c1, c2, radius):
    """True diagonal gradient (top-left -> bottom-right) + rounded-corner alpha mask."""
    img = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        for x in range(w):
            t = (x + y) / (w + h - 2)
            d.point((x, y), fill=(lerp(c1[0], c2[0], t), lerp(c1[1], c2[1], t), lerp(c1[2], c2[2], t), 255))
    mask = Image.new("L", (w, h), 0)
    dm = ImageDraw.Draw(mask)
    dm.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
    img.putalpha(mask)
    return img

def draw_hollow_hub(icon, size, cx, cy, R, center_r, node_r, stroke):
    """Draw a hollow-ring hub: 1 center + 5 surrounding pentagon nodes, lines at ring edges."""
    d = ImageDraw.Draw(icon)
    # 5 surrounding nodes in a pentagon, starting at top (-90deg), clockwise
    positions = []
    for i in range(5):
        ang = math.radians(-90 + i * 72)
        positions.append((cx + R * math.cos(ang), cy + R * math.sin(ang)))
    # connecting lines: from center-ring edge to each outer-ring edge (don't cross interiors)
    for (x, y) in positions:
        dx, dy = x - cx, y - cy
        dist = math.hypot(dx, dy)
        ux, uy = dx / dist, dy / dist
        d.line([cx + ux * center_r, cy + uy * center_r, x - ux * node_r, y - uy * node_r],
               fill=(255, 255, 255, 255), width=stroke)
    # center node as hollow ring (larger than outer)
    d.ellipse([cx - center_r, cy - center_r, cx + center_r, cy + center_r],
              outline=(255, 255, 255, 255), width=stroke)
    # surrounding nodes as hollow rings (smaller)
    for (x, y) in positions:
        d.ellipse([x - node_r, y - node_r, x + node_r, y + node_r],
                  outline=(255, 255, 255, 255), width=stroke)
    return icon

def make_icon(size):
    icon = make_gradient_bg(size, size, C1, C2, int(size * CORNER_FRAC))
    draw_hollow_hub(icon, size,
                    size / 2, size / 2,
                    int(size * R_FRAC), int(size * CENTER_R_FRAC), int(size * NODE_R_FRAC),
                    max(2, int(size * STROKE_FRAC)))
    return icon

def main():
    targets = [(64, "ICON.PNG"), (256, "ICON_256.PNG"),
               (64, "app/ui/images/icon_64.png"), (128, "app/ui/images/icon_128.png"),
               (256, "app/ui/images/icon_256.png")]
    for s, path in targets:
        make_icon(s).save(path)
        print("saved", path)
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        make_icon(512).save("/tmp/hollow_hub_icon_preview.png")
        print("preview /tmp/hollow_hub_icon_preview.png")

if __name__ == "__main__":
    main()
