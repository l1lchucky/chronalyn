#!/usr/bin/env python3
"""Generate the Chronalyn social preview image (1280x640).

Dark, minimal, provider-neutral: brand name, tagline, and the
Hermes -> Chronalyn -> Hindsight + Mnemosyne architecture.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 640
BG = (15, 17, 26)  # near-black navy
PANEL = (24, 28, 42)  # card background
ACCENT = (99, 102, 241)  # indigo
TEXT = (226, 230, 240)  # near-white
MUTED = (148, 156, 178)  # gray-blue
GREEN = (52, 211, 153)  # mnemosyne accent
BLUE = (96, 165, 250)  # hindsight accent

OUT = Path(__file__).resolve().parent.parent / "docs" / "assets" / "chronalyn-social-preview.png"

img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)


def font(size, bold=False):
    try:
        return ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            size,
        )
    except Exception:
        return ImageFont.load_default()


f_title = font(72, bold=True)
f_sub = font(30)
f_node = font(26, bold=True)
f_small = font(20)
f_tag = font(22, bold=True)

# Title block
d.text((64, 56), "Chronalyn", font=f_title, fill=TEXT)
d.text((64, 150), "Memory orchestration for Hermes Agent", font=f_sub, fill=MUTED)

# Architecture: three panels (generous margins, arrows clear of text)
panels = [
    (80, 260, 300, 360, "Hermes Agent", "memory provider contract", ACCENT),
    (440, 260, 656, 360, "Chronalyn", "orchestration layer", TEXT),
    (796, 260, 1200, 360, "Hindsight + Mnemosyne", "persistent memory + checkpoints", GREEN),
]
for x0, y0, x1, y1, title, sub, color in panels:
    d.rounded_rectangle([x0, y0, x1, y1], radius=16, fill=PANEL, outline=color, width=2)
    d.text((x0 + 24, y0 + 30), title, font=f_node, fill=color)
    d.text((x0 + 24, y0 + 76), sub, font=f_small, fill=MUTED)


# Arrows
def arrow(x0, y0, x1, y1):
    d.line([x0, y0, x1, y1], fill=MUTED, width=4)
    # arrowhead
    import math

    ang = math.atan2(y1 - y0, x1 - x0)
    for da in (0.4, -0.4):
        d.line(
            [x1, y1, x1 - 22 * math.cos(ang - da), y1 - 22 * math.sin(ang - da)],
            fill=MUTED,
            width=4,
        )


arrow(300, 310, 440, 310)
arrow(656, 310, 796, 310)

# Footer: one provider
d.text((64, 440), "Hermes sees one memory provider.", font=f_tag, fill=TEXT)
d.text(
    (64, 486),
    "Hindsight handles persistent memory, recall, and reflection;",
    font=f_small,
    fill=MUTED,
)
d.text(
    (64, 516),
    "Mnemosyne keeps verified checkpoints and bounded fallback.",
    font=f_small,
    fill=MUTED,
)
d.text(
    (64, 570),
    "hermes plugins install l1lchucky/hermes-memory-router",
    font=f_small,
    fill=BLUE,
)

img.save(OUT)
print(f"saved {OUT}")
