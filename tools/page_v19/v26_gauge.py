"""Speedometer drawn on the 'ours' video of the split renders (user 2026-10-11): log scale, 1x at the top, slower to the
left, faster to the right, so the non-uniform (dynamic) speed-up is visible at a glance."""
import math
LO, HI = 0.4, 2.5          # dial range (x), symmetric in log about 1x
TICKS = (0.5, 0.75, 1.0, 1.5, 2.0, 2.5)

def angle(r):
    """-90 deg (left) .. 0 (top, 1x) .. +90 deg (right), log scale."""
    r = min(max(r, LO), HI)
    return 90.0 * (math.log(r) / math.log(HI)) if r >= 1 else -90.0 * (math.log(r) / math.log(LO))

def _pt(cx, cy, rad, deg):
    a = math.radians(deg); return cx + rad * math.sin(a), cy - rad * math.cos(a)

def draw_gauge(d, cx, cy, R, r, font, label=None, gold=(240, 170, 30), slow=(110, 160, 230)):
    """d: ImageDraw (RGBA); (cx, cy) dial centre; R radius."""
    d.rounded_rectangle((cx - R - 12, cy - R - 12, cx + R + 12, cy + int(R * 0.5)), 12, fill=(14, 14, 18, 205))
    for deg0 in range(-90, 90, 3):          # coloured arc: blue = slower than 1x, gold = faster
        col = slow if deg0 < 0 else gold
        fade = abs(deg0 + 1.5) / 90.0
        c = tuple(int(70 + (cc - 70) * (0.35 + 0.65 * fade)) for cc in col)
        d.line((*_pt(cx, cy, R - 4, deg0), *_pt(cx, cy, R - 4, deg0 + 3)), fill=c + (255,), width=7)
    for tv in TICKS:
        a = angle(tv)
        d.line((*_pt(cx, cy, R - 12, a), *_pt(cx, cy, R + 1, a)), fill=(235, 235, 240, 255), width=2 if tv != 1.0 else 3)
        if tv in (0.5, 1.0, 2.0):
            d.text(_pt(cx, cy, R - 24, a), f"{tv:g}×", font=font("Bold", max(10, int(R * 0.2))), fill=(220, 220, 228), anchor="mm")
    a = angle(r)
    d.line((cx, cy, *_pt(cx, cy, R - 10, a)), fill=(255, 255, 255, 255), width=4)
    d.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), fill=(255, 255, 255, 255))
    d.text((cx, cy + 6), label or f"×{r:.2f}", font=font("Black", max(13, int(R * 0.32))),
           fill=gold if r > 1.01 else (slow if r < 0.99 else (235, 235, 240)), anchor="mt")
