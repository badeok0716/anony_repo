#!/usr/bin/env python3
"""Build a side-by-side Baseline | Ours comparison video with ffmpeg.

Both clips play at 1x. Each panel gets an elapsed-time timer. The clip that
finishes first freezes on its last frame and shows "Done (X.Xs)" until the
other one ends. A "1x REAL-TIME - NOT SPED UP" badge sits in the footer.
All metadata, audio and data streams are dropped.

Text is rendered through the libass `ass` filter, so this works with ffmpeg
builds that lack `drawtext`.

Example:
  python3 tools/make_comparison.py --baseline base.mov --ours ours.mov \
      --out videos/cup.mp4 --poster videos/cup.jpg --height 720 \
      --fonts-dir /usr/share/fonts/truetype/lato
"""
import argparse
import os
import re
import subprocess
import tempfile

FPS = 30
GAP = 12  # white gutter between the two panels, px


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def run_bytes(cmd):
    return subprocess.run(cmd, capture_output=True, check=True).stdout


def probe(ffmpeg, path):
    """Return (video duration in s, is_hdr) by decoding the video stream once."""
    info = run([ffmpeg, "-hide_banner", "-i", path]).stderr
    stream = next(l for l in info.splitlines() if "Video:" in l)
    hdr = bool(re.search(r"arib-std-b67|smpte2084", stream))
    out = run([ffmpeg, "-hide_banner", "-i", path, "-map", "0:v:0", "-f", "null", "-"]).stderr
    h, m, s = re.findall(r"time=(\d+):(\d+):([\d.]+)", out)[-1]
    return int(h) * 3600 + int(m) * 60 + float(s), hdr


def ass_time(t):
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def rounded_rect(w, h, r):
    return (f"m {r} 0 l {w - r} 0 b {w} 0 {w} 0 {w} {r} l {w} {h - r} b {w} {h} {w} {h} {w - r} {h} "
            f"l {r} {h} b 0 {h} 0 {h} 0 {h - r} l 0 {r} b 0 0 0 0 {r} 0")


def ass_color(hex_rgb, alpha=0):
    r, g, b = hex_rgb[0:2], hex_rgb[2:4], hex_rgb[4:6]
    return f"&H{alpha:02X}{b}{g}{r}&".upper()


REALTIME_TEXT = "1\u00d7 REAL-TIME \u00b7 NOT SPED UP"


def ink_extent(ffmpeg, fonts_dir, style, text):
    """Render `text` once with libass and return (left offset, width) of the drawn pixels
    relative to its \\pos anchor, so boxes can be fitted to what is actually drawn."""
    W, H, x0 = 3000, 300, 20
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "measure.ass")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join([
            "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
            "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
            "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            style, "", "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
            f"Dialogue: 0,0:00:00.00,0:00:01.00,{style.split(',')[0].split(': ')[1]},,0,0,0,,"
            f"{{\\pos({x0},{H // 2})}}{text}", ""]))
    raw = run_bytes([ffmpeg, "-v", "error", "-f", "lavfi", "-i", f"color=black:s={W}x{H}:d=1",
                     "-vf", f"ass={path}:fontsdir={fonts_dir},format=gray", "-frames:v", "1",
                     "-f", "rawvideo", "-"])
    cols = [x for x in range(W) if any(raw[y * W + x] > 60 for y in range(0, H, 2))]
    return cols[0] - x0, cols[-1] - cols[0] + 1


def circle(r):
    k = 0.5523 * r
    return (f"m {r} 0 b {r + k} 0 {2 * r} {r - k} {2 * r} {r} b {2 * r} {r + k} {r + k} {2 * r} {r} {2 * r} "
            f"b {r - k} {2 * r} 0 {r + k} 0 {r} b 0 {r - k} {r - k} 0 {r} 0")


def build_ass(W, H, panels, label_h, footer_h, total, unit, fonts_dir, ffmpeg):
    """panels: list of dicts with x, w, label, color, dur, finishes_first.
    unit: text size reference in px (panel height x text scale)."""
    fs_label = round(unit * 0.062)
    fs_footer = round(unit * 0.048)
    fs_timer = round(unit * 0.050)
    # keep the widest badge ("Done (XX.Xs)") inside the narrowest panel
    min_w = min(p["w"] for p in panels)
    fs_timer = min(fs_timer, int((min_w * 0.8 - 24) / (12 * 0.602)))
    pad = round(fs_timer * 0.45)
    box_h = round(fs_timer * 1.5)
    inset = round(unit * 0.025)

    badge_style = (f"Style: Badge,Lato,{fs_footer},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,"
                   f"100,100,{max(1, round(fs_footer * 0.06))},0,1,0,0,4,0,0,0,1")
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}",
        "WrapStyle: 2", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Label,Lato,{fs_label},&H00222222,&H00222222,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1",
        badge_style,
        f"Style: Timer,DejaVu Sans Mono,{fs_timer},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,4,0,0,0,1",
        f"Style: Box,Lato,10,&H00000000,&H00000000,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1",
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    def ev(layer, t0, t1, style, text):
        lines.append(f"Dialogue: {layer},{ass_time(t0)},{ass_time(t1)},{style},,0,0,0,,{text}")

    # "1x real-time" badge: dark pill with a red dot, centred in the footer strip
    ink_dx, tw = ink_extent(ffmpeg, fonts_dir, badge_style, REALTIME_TEXT)
    pill_h = round(fs_footer * 1.45)
    r_dot = round(fs_footer * 0.22)
    bpad, gap = round(fs_footer * 0.62), round(fs_footer * 0.38)
    pill_w = round(bpad + 2 * r_dot + gap + tw + bpad)
    px, py = (W - pill_w) // 2, H - footer_h + (footer_h - pill_h) // 2
    cy = py + pill_h // 2
    ev(0, 0, total, "Box", f"{{\\pos({px},{py})\\p1\\1c{ass_color('1F2328')}}}{rounded_rect(pill_w, pill_h, pill_h // 2)}")
    ev(1, 0, total, "Box", f"{{\\pos({px + bpad},{cy - r_dot})\\p1\\1c{ass_color('EF4444')}}}{circle(r_dot)}")
    ev(1, 0, total, "Badge", f"{{\\pos({px + bpad + 2 * r_dot + gap - ink_dx},{cy})}}{REALTIME_TEXT}")
    for p in panels:
        cx = p["x"] + p["w"] // 2
        ev(0, 0, total, "Label", f"{{\\pos({cx},{label_h // 2})\\1c{ass_color(p['color'])}}}{p['label']}")

        bx, by = p["x"] + inset, label_h + inset
        timer_w = round(fs_timer * 0.602 * len(f"{p['dur']:.1f} s") + 2 * pad)  # fits the longest reading
        ticks = int(p["dur"] * 10)
        for k in range(ticks + 1):
            t0, t1 = k / 10, min((k + 1) / 10, p["dur"])
            if t1 <= t0:
                continue
            ev(1, t0, t1, "Timer", f"{{\\pos({bx + pad},{by + box_h // 2})}}{k / 10:.1f} s")
        ev(0, 0, p["dur"], "Box",
           f"{{\\pos({bx},{by})\\p1\\1c&H000000&\\1a&H66&}}{rounded_rect(timer_w, box_h, pad // 2)}")
        if p["dur"] < total:
            if p["finishes_first"]:
                text = f"Done ({p['dur']:.1f}s)"
                w = round(fs_timer * 0.602 * len(text) + 2 * pad)
                fill, alpha = "16A34A", 0x00
            else:  # the longer clip: freeze its timer during the end hold
                text = f"{p['dur']:.1f} s"
                w, fill, alpha = timer_w, "000000", 0x66
            ev(0, p["dur"], total, "Box",
               f"{{\\pos({bx},{by})\\p1\\1c{ass_color(fill)}\\1a&H{alpha:02X}&}}{rounded_rect(w, box_h, pad // 2)}")
            ev(1, p["dur"], total, "Timer", f"{{\\pos({bx + pad},{by + box_h // 2})}}{text}")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--ours", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--poster", help="optional JPEG poster (first frame)")
    for side in ("baseline", "ours"):
        ap.add_argument(f"--trim-{side}", default="", metavar="START:END",
                        help="keep only this span in seconds, e.g. 2.1:10.7 or 2.1: (to the end)")
        ap.add_argument(f"--crop-{side}", default="", metavar="W:H:X:Y",
                        help="ffmpeg crop applied before scaling, in upright source pixels")
    ap.add_argument("--height", type=int, default=540, help="panel height in px")
    ap.add_argument("--text-scale", type=float, default=1.0,
                    help="scale overlay text; raise it for wide videos that are shown downscaled")
    ap.add_argument("--hold-end", type=float, default=1.0, help="seconds to hold the final frame")
    ap.add_argument("--crf", type=int, default=24)
    ap.add_argument("--max-mb", type=float, default=9.5, help="re-encode at a capped bitrate above this")
    ap.add_argument("--fonts-dir", required=True, help="directory with Lato and DejaVu Sans Mono fonts")
    ap.add_argument("--ffmpeg", default="ffmpeg")
    a = ap.parse_args()

    clips = [("Baseline", a.baseline, "555555"), ("Ours", a.ours, "1D4ED8")]
    info = [probe(a.ffmpeg, path) for _, path, _ in clips]
    trims, crops = [a.trim_baseline, a.trim_ours], [a.crop_baseline, a.crop_ours]
    spans = []
    for (full, _), t in zip(info, trims):
        start, _, end = t.partition(":")
        start = float(start or 0)
        end = min(float(end), full) if end else full
        spans.append((start, end))
    durs = [end - start for start, end in spans]
    total = max(durs) + a.hold_end
    first = durs.index(min(durs))

    H = a.height
    unit = H * a.text_scale
    label_h, footer_h = round(unit * 0.11), round(unit * 0.105)

    # panel widths after scaling to a common height (even, as scale=-2 does)
    widths = []
    for (_, path, _), crop in zip(clips, crops):
        vf = (f"crop={crop}," if crop else "") + f"scale=-2:{H}"
        out = run([a.ffmpeg, "-hide_banner", "-v", "verbose", "-i", path, "-frames:v", "1",
                   "-vf", vf, "-f", "null", "-"]).stderr
        w = int(re.findall(r"-> w:(\d+) h:\d+", out)[-1])
        widths.append(w)
    W = widths[0] + GAP + widths[1]
    Htot = H + label_h + footer_h
    Htot += Htot % 2

    panels = []
    x = 0
    for i, ((label, _, color), w) in enumerate(zip(clips, widths)):
        panels.append(dict(x=x, w=w, label=label, color=color, dur=durs[i], finishes_first=(i == first)))
        x += w + GAP

    tmp = tempfile.mkdtemp()
    ass_path = os.path.join(tmp, "overlay.ass")
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(build_ass(W, Htot, panels, label_h, footer_h, total, unit, a.fonts_dir, a.ffmpeg))

    tonemap = ("zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,"
               "zscale=t=bt709:m=bt709:r=tv,")
    chains = []
    for i, (_, hdr) in enumerate(info):
        pre = f"trim=start={spans[i][0]:.3f}:end={spans[i][1]:.3f},setpts=PTS-STARTPTS,"
        pre += tonemap if hdr else ""
        pre += f"crop={crops[i]}," if crops[i] else ""
        chains.append(
            f"[{i}:v:0]{pre}fps={FPS},scale=-2:{H}:flags=lanczos:out_color_matrix=bt709:out_range=tv,"
            f"setsar=1,format=yuv420p,tpad=stop_mode=clone:stop_duration={total - durs[i] + 0.5:.3f}[v{i}]")
    chains.append(f"[v0]pad=iw+{GAP}:ih:0:0:white[l]")
    chains.append(f"[l][v1]hstack=inputs=2,pad=iw:{Htot}:0:{label_h}:white,"
                  f"ass={ass_path}:fontsdir={a.fonts_dir},format=yuv420p[out]")
    graph = ";".join(chains)

    def encode(extra):
        cmd = [a.ffmpeg, "-hide_banner", "-v", "error", "-y", "-i", a.baseline, "-i", a.ours,
               "-filter_complex", graph, "-map", "[out]", "-t", f"{total:.3f}",
               "-an", "-sn", "-dn", "-map_metadata", "-1", "-map_chapters", "-1",
               "-c:v", "libx264", "-preset", "slow", "-profile:v", "high", "-pix_fmt", "yuv420p",
               "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
               "-movflags", "+faststart", *extra, a.out]
        r = run(cmd)
        if r.returncode:
            raise SystemExit(r.stderr)

    encode(["-crf", str(a.crf)])
    size_mb = os.path.getsize(a.out) / 2**20
    if size_mb > a.max_mb:
        kbps = int(a.max_mb * 0.95 * 8 * 1024 / total)
        encode(["-b:v", f"{kbps}k", "-maxrate", f"{int(kbps * 1.5)}k", "-bufsize", f"{kbps * 2}k"])
        size_mb = os.path.getsize(a.out) / 2**20

    if a.poster:
        r = run([a.ffmpeg, "-hide_banner", "-v", "error", "-y", "-i", a.out, "-frames:v", "1",
                 "-q:v", "4", "-map_metadata", "-1", a.poster])
        if r.returncode:
            raise SystemExit(r.stderr)

    print(f"{a.out}: {W}x{Htot}, {total:.2f}s, {size_mb:.2f} MB | "
          f"baseline {durs[0]:.2f}s ({spans[0][0]:.2f}-{spans[0][1]:.2f}), "
          f"ours {durs[1]:.2f}s ({spans[1][0]:.2f}-{spans[1][1]:.2f})")


if __name__ == "__main__":
    main()
