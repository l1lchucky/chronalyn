#!/usr/bin/env python3
"""Chronalyn brand asset generator.

Builds the three public brand assets deterministically from shared vector
geometry (the "open arc" mark), so the images are crisp at any size, have
correct spelling, and never contain AI artifacts:

    docs/assets/chronalyn-icon.png               square mark, transparent
    docs/assets/chronalyn-logo.png               [mark] Chronalyn wordmark, transparent
    docs/assets/chronalyn-social-preview.png     1280x640 brand card, navy

Regeneration requires Pillow (development-only dependency, not a runtime
dependency of Chronalyn):

    python -m pip install pillow
    python scripts/make-social-preview.py

The mark is an open arc: a circle with a deliberate gap that reads as the
letter C and as continuity / history. It is intentionally not a spinner,
clock, or sync icon.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ASSETS = Path(__file__).resolve().parent.parent / "docs" / "assets"

# Palette (restrained: navy ink, off-white, one teal accent).
NAVY = (14, 20, 32)        # #0E1420
OFF_WHITE = (242, 244, 248)  # #F2F4F8
MUTED = (154, 163, 178)      # #9AA3B2
TEAL = (45, 212, 191)        # #2DD4BF

FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
FONT_DEJAVU_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def draw_open_arc(
    d: ImageDraw.ImageDraw,
    center: tuple[float, float],
    radius: float,
    color: tuple[int, int, int],
    width: float,
    gap_deg: float = 42.0,
    rotation_deg: float = 0.0,
    cap: str = "round",
) -> None:
    """Draw an open arc (a C-like ring) as a filled annular wedge.

    Rendering as a polygon (outer radius minus inner radius) gives one smooth
    continuous stroke with no polyline segment seams. gap_deg is the angular
    size of the missing segment; rotation_deg places the gap.
    """
    start = rotation_deg + gap_deg / 2
    end = rotation_deg + 360 - gap_deg / 2
    inner = radius - width / 2
    outer = radius + width / 2
    steps = 128
    pts: list[tuple[float, float]] = []
    for i in range(steps + 1):
        ang = math.radians(start + (end - start) * i / steps)
        pts.append((center[0] + outer * math.cos(ang), center[1] + outer * math.sin(ang)))
    for i in range(steps, -1, -1):
        ang = math.radians(start + (end - start) * i / steps)
        pts.append((center[0] + inner * math.cos(ang), center[1] + inner * math.sin(ang)))
    d.polygon(pts, fill=color)
    # Round caps at both ends.
    for a in (start, end):
        x = center[0] + radius * math.cos(math.radians(a))
        y = center[1] + radius * math.sin(math.radians(a))
        d.ellipse([x - width / 2, y - width / 2, x + width / 2, y + width / 2], fill=color)


# --------------------------------------------------------------------------
# Icon: square, transparent, centered open-arc mark with generous padding.
# --------------------------------------------------------------------------
def make_icon(size: int = 512) -> Image.Image:
    pad = size * 0.22
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = cy = size / 2
    radius = (size / 2) - pad
    stroke = size * 0.09
    draw_open_arc(d, (cx, cy), radius, TEAL, stroke)
    return img


# --------------------------------------------------------------------------
# Logo: horizontal wordmark [mark] Chronalyn on transparent.
# --------------------------------------------------------------------------
def make_logo(mark_px: int = 220) -> Image.Image:
    text = "Chronalyn"
    f = font(FONT_BOLD, 128)
    bbox = f.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    gap = 34
    pad = 24
    W = pad * 2 + mark_px + gap + tw
    H = pad * 2 + max(mark_px, th)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Mark centered vertically, slightly optically corrected.
    mark_center_y = H / 2 + mark_px * 0.02
    radius = mark_px * 0.42
    stroke = mark_px * 0.10
    draw_open_arc(d, (pad + mark_px / 2, mark_center_y), radius, TEAL, stroke)
    # Wordmark, vertically centered on cap height.
    ty = (H - th) / 2 - bbox[1]
    d.text((pad + mark_px + gap, ty), text, font=f, fill=NAVY)
    return img


# --------------------------------------------------------------------------
# Social preview: 1280x640 brand card. Brand-first, no architecture.
# --------------------------------------------------------------------------
def make_social_preview() -> Image.Image:
    # Render at 2x and downscale for crisp text edges.
    SCALE = 2
    W, H = 1280 * SCALE, 640 * SCALE
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)

    # Very subtle top-right ambient glow (single soft radial, restrained).
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    gx, gy, gr = W - 480, 240, 840
    for i in range(gr, 0, -12):
        a = int(10 * (1 - i / gr))
        od.ellipse([gx - i, gy - i, gx + i, gy + i], fill=(45, 212, 191, a))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    d = ImageDraw.Draw(img)

    # Mark: large open arc centered above the wordmark.
    mark_r = 184
    mark_cx, mark_cy = W / 2, 436
    draw_open_arc(d, (mark_cx, mark_cy), mark_r, TEAL, 52)

    # Wordmark.
    f_word = font(FONT_BOLD, 192)
    bbox = f_word.getbbox("Chronalyn")
    d.text(
        ((W - (bbox[2] - bbox[0])) / 2 - bbox[0], 704),
        "Chronalyn",
        font=f_word,
        fill=OFF_WHITE,
    )

    # Tagline.
    f_tag = font(FONT_DEJAVU_BOLD, 68)
    tag = "Give Hermes a past it can actually use."
    tb = f_tag.getbbox(tag)
    d.text(
        ((W - (tb[2] - tb[0])) / 2 - tb[0], 956),
        tag,
        font=f_tag,
        fill=MUTED,
    )

    # Supporting line.
    f_sub = font(FONT_REG, 48)
    sub = "Long-term memory for Hermes Agent"
    sb = f_sub.getbbox(sub)
    d.text(
        ((W - (sb[2] - sb[0])) / 2 - sb[0], 1092),
        sub,
        font=f_sub,
        fill=MUTED,
    )
    return img.resize((1280, 640), Image.LANCZOS)


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    icon = make_icon(512)
    icon.save(ASSETS / "chronalyn-icon.png")
    logo = make_logo()
    logo.save(ASSETS / "chronalyn-logo.png")
    social = make_social_preview()
    social.save(ASSETS / "chronalyn-social-preview.png")
    print("saved:")
    print("  docs/assets/chronalyn-icon.png")
    print("  docs/assets/chronalyn-logo.png")
    print("  docs/assets/chronalyn-social-preview.png")


if __name__ == "__main__":
    main()
