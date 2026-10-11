"""Training-time tempo figure for the demo page (2026-10-12; restyle of output/cup412_postgrasp_three.*).
Same three post-grasp cup observations and the same real label arrays (../output/plotted_arrays.npz: all 15 stored
waypoints of the chunk, flange displacement from each start); grey dashed lines join the same waypoint index across demos. Drawn as inline SVG in the page theme:
- side view (Y right, Z up; X spans < 17 mm so the side view hides little), identical scale for both rows;
- per-example distance strips: one dot per waypoint (1/15 s) at its cumulative path length, so waypoint spacing and the
  distance covered in 0.8 s compare without overlapping lines. No numbers on the plots, no fitted curves."""
import json, sys, numpy as np

COL = ["#4f46e5", "#e11d48", "#0f766e"]            # indigo, rose, teal (distinct from the page's tempo colours)
SHAPE = ["circle", "square", "triangle"]

def marker(shape, x, y, c, r=4.2):
    if shape == "circle": return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="#fff" stroke="{c}" stroke-width="1.8"/>'
    if shape == "square": return f'<rect x="{x - r:.1f}" y="{y - r:.1f}" width="{2 * r}" height="{2 * r}" fill="#fff" stroke="{c}" stroke-width="1.8"/>'
    h = r * 1.15; return f'<path d="M{x:.1f},{y - h:.1f} L{x + h:.1f},{y + h * 0.8:.1f} L{x - h:.1f},{y + h * 0.8:.1f} Z" fill="#fff" stroke="{c}" stroke-width="1.8"/>'

def build(npz, img_urls):
    z = np.load(npz); n = z["raw_full_xyz_mm"].shape[1] - 1          # the whole 15-step chunk (1.0 s at 15 Hz)
    raw = z["raw_full_xyz_mm"][:, :n + 1] - z["raw_full_xyz_mm"][:, :1]   # demos A, B, C = ep164, ep167, ep49
    lrn = z["learned_q50_full_xyz_mm"][:, :n + 1] - z["learned_q50_full_xyz_mm"][:, :1]
    sgn = 1 if np.mean(raw[:, -1, 1]) >= 0 else -1                     # motion to the right
    W, H = 1000, 560
    o = [f'<svg class="train-fig" viewBox="0 0 {W} {H}" role="img" aria-label="Three similar post-grasp observations; one 15-waypoint action chunk each, before and after tempo alignment.">']
    T = lambda s, x, y, sz=13, w=400, a="start", c="#1f2328": o.append(f'<text x="{x}" y="{y}" font-size="{sz}" font-weight="{w}" text-anchor="{a}" fill="{c}">{s}</text>')
    # left: observations
    T("Similar observations", 20, 24, 14, 600); T("wrist camera, right after grasp", 20, 41, 11, 400, "start", "#59636e")
    for i, url in enumerate(img_urls):
        y = 58 + i * 160
        o.append(f'<rect x="18" y="{y - 2}" width="148" height="148" rx="6" fill="none" stroke="{COL[i]}" stroke-width="3"/>')
        o.append(f'<image href="{url}" x="20" y="{y}" width="144" height="144" preserveAspectRatio="xMidYMid slice"/>')
        o.append(marker(SHAPE[i], 182, y + 72, COL[i], 5))
        T(f"demo {'ABC'[i]}", 194, y + 77, 12, 600, "start", COL[i])
    # shared side-view scale
    allp = np.concatenate([raw, lrn]); ys, zs = sgn * allp[..., 1], allp[..., 2]
    ymin, ymax, zmin, zmax = ys.min(), ys.max(), zs.min(), zs.max()
    pw, ph = 230, 170; s = min(pw / (ymax - ymin), ph / (zmax - zmin))
    lmax = max(np.linalg.norm(np.diff(a, axis=1), axis=2).sum(1).max() for a in (raw, lrn)) * 1.06
    def row(arr, y0, title, sub, stat):
        T(title, 300, y0 - 34, 15, 600); T(sub, 300, y0 - 16, 11, 400, "start", "#59636e")
        px = lambda p: (300 + 10 + (sgn * p[1] - ymin) * s, y0 + ph + 4 - (p[2] - zmin) * s)
        o.append(f'<rect x="300" y="{y0 - 4}" width="{pw + 20}" height="{ph + 16}" rx="8" fill="#f6f8fa" stroke="#e5e7eb"/>')
        for k in range(1, len(arr[0])):                              # same waypoint index across demos A-B-C
            q3 = [px(a[k]) for a in arr]
            o.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in q3)}" fill="none" stroke="#9ca3af" stroke-width="0.9" stroke-dasharray="3 3"/>')
        for i, a in enumerate(arr):
            pts = [px(p) for p in a]
            o.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" fill="none" stroke="{COL[i]}" stroke-width="1.6" stroke-opacity="0.7"/>')
            for x, y in pts[1:]: o.append(marker(SHAPE[i], x, y, COL[i], 3.3))
        x0s, y0s = px(arr[0][0]); o.append(f'<circle cx="{x0s:.1f}" cy="{y0s:.1f}" r="4" fill="#59636e"/>')
        T("side view (Y–Z) · ● start", 300, y0 + ph + 26, 10, 400, "start", "#8c959f")
        # distance strips
        sx0, sx1 = 590, 960; L = lambda d: sx0 + (sx1 - sx0) * d / lmax
        T("distance along the path · dot = waypoint (1/15 s) · dashed = same waypoint", sx0, y0 + 6, 11, 400, "start", "#59636e")
        for v in range(0, int(lmax) + 1, 100):
            o.append(f'<line x1="{L(v):.1f}" y1="{y0 + 16}" x2="{L(v):.1f}" y2="{y0 + 150}" stroke="#eef0f3"/>')
            T(f"{v} mm", L(v), y0 + 166, 10, 400, "middle", "#8c959f")
        ds = [np.r_[0, np.cumsum(np.linalg.norm(np.diff(a, axis=0), axis=1))] for a in arr]
        for k in range(1, len(ds[0])):                               # same waypoint index across demos A-B-C
            q3 = [(L(d[k]), y0 + 40 + i * 40) for i, d in enumerate(ds)]
            o.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in q3)}" fill="none" stroke="#9ca3af" stroke-width="0.9" stroke-dasharray="3 3"/>')
        for i, a in enumerate(arr):
            d = ds[i]; yy = y0 + 40 + i * 40
            o.append(f'<line x1="{L(0):.1f}" y1="{yy}" x2="{L(d[-1]):.1f}" y2="{yy}" stroke="{COL[i]}" stroke-width="2" stroke-opacity="0.35"/>')
            for dv in d[1:]: o.append(marker(SHAPE[i], L(dv), yy, COL[i], 3.6))
            T(f"{d[-1]:.0f} mm", L(d[-1]) + 10, yy + 4, 11, 600, "start", COL[i])
        T(stat, sx1, y0 - 16, 12, 600, "end", "#1f2328")
    m = lambda a: np.linalg.norm(np.diff(a, axis=1), axis=2).sum(1)
    cv = lambda v: np.std(v) / np.mean(v) * 100
    rr, ll = m(raw), m(lrn)
    row(raw, 70, "Original timing", "raw labels: the operator's pace", f"{rr.min():.0f}–{rr.max():.0f} mm per chunk · spread {cv(rr):.0f}%")
    # speed prior box between the rows
    o.append(f'<rect x="300" y="276" width="660" height="38" rx="10" fill="#eef4ff" stroke="#bfd2f8"/>')
    T("Learned speed prior → retime every demonstration to its q50 (median) clock", 630, 300, 13, 600, "middle", "#1d4ed8")
    o.append('<path d="M630,262 L630,274 M624,268 L630,275 L636,268" stroke="#1d4ed8" stroke-width="1.6" fill="none"/>')
    o.append('<path d="M630,316 L630,330 M624,324 L630,331 L636,324" stroke="#1d4ed8" stroke-width="1.6" fill="none"/>')
    row(lrn, 372, "Tempo-aligned", "labels on the learned q50 clock", f"{ll.min():.0f}–{ll.max():.0f} mm per chunk · spread {cv(ll):.0f}%")
    o.append("</svg>")
    return "\n".join(o), dict(raw_mm=rr.round(1).tolist(), aligned_mm=ll.round(1).tolist(), cv_raw=round(cv(rr), 1), cv_aligned=round(cv(ll), 1))

if __name__ == "__main__":
    svg, stats = build(sys.argv[1], sys.argv[2:5]); open(sys.argv[5], "w").write(svg); print(json.dumps(stats))
