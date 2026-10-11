"""Inline SVG for the page (2026-10-11): the action expert's 32-dim step output (7 joints, gripper, 3 tempo channels at
dims 8-10, padding) -> q50 (default step 1/15 s) and the q90/q95/q99 channels -> the same 15-step chunk on a time axis,
whose step spacing shrinks with the predicted per-step speed-up. Data: cup rollout 041209, chunk 0, joint 2."""
import json, sys, numpy as np

def figure(chunks_json, k=0, joint=1):
    q = json.load(open(chunks_json))["queries"][k]
    a = np.array(q["actions"])[:, joint]; rate = np.exp(np.array(q["tempo"]))           # (15, 3)
    rows = [("q50", "default step · 1/15 s", np.full(15, 1.0), "#0ea5e9")] + \
           [(n, "tempo channel", rate[:, i], c) for i, (n, c) in enumerate((("q90", "#8b5cf6"), ("q95", "#16a34a"), ("q99", "#d97706")))]
    W, H = 1000, 330; out = [f'<svg class="tempo-fig" viewBox="0 0 {W} {H}" role="img" aria-label="The action expert outputs 32 values per step; dims 8-10 are three tempo channels. Each channel retimes the same 15-step action chunk.">']
    T = lambda s, x, y, sz=13, w=400, anc="start", col="#1f2328": out.append(
        f'<text x="{x}" y="{y}" font-size="{sz}" font-weight="{w}" text-anchor="{anc}" fill="{col}">{s}</text>')
    # --- left: one step of the output vector
    x0, y0, cw, ch = 118, 46, 70, 11
    T("action expert output", x0 + cw / 2, 22, 13, 600, "middle"); T("one step · 32 dims", x0 + cw / 2, 37, 11, 400, "middle", "#59636e")
    cells = [("j", i) for i in range(7)] + [("g", 7)] + [("t", 8), ("t", 9), ("t", 10)] + [("p", i) for i in range(11, 15)]
    y = y0; tempo_y = []
    for kind, i in cells:
        fill = {"j": "#dbe4ef", "g": "#cbd5e1", "t": "#fde7c2", "p": "#f3f4f6"}[kind]
        stroke = "#d97706" if kind == "t" else "#cbd5e1"
        out.append(f'<rect x="{x0}" y="{y}" width="{cw}" height="{ch}" rx="2" fill="{fill}" stroke="{stroke}" stroke-width="{1.4 if kind == "t" else 0.8}"/>')
        if kind == "t": tempo_y.append(y + ch / 2)
        y += ch + 2
    T("⋮", x0 + cw / 2, y + 12, 14, 600, "middle", "#8c959f"); y_end = y + 18
    T("7 joints", x0 - 8, y0 + 3.5 * (ch + 2) + 4, 11, 400, "end", "#59636e")
    T("gripper", x0 - 8, y0 + 7 * (ch + 2) + 9, 11, 400, "end", "#59636e")
    T("tempo ×3", x0 - 8, tempo_y[1] + 4, 11, 600, "end", "#b45309")
    T("dims 8–10", x0 - 8, tempo_y[1] + 17, 10, 400, "end", "#b45309")
    T("padding", x0 - 8, y0 + 12 * (ch + 2) + 10, 11, 400, "end", "#8c959f")
    T("(dims 11–31)", x0 - 8, y0 + 12 * (ch + 2) + 23, 10, 400, "end", "#8c959f")
    # --- rows: q50 on top, then q90 / q95 / q99
    rx0, rx1, ry0, rh, lx = 400, 975, 58, 66, 256
    tx = lambda t: rx0 + 40 + (rx1 - rx0 - 60) * t                    # 0..1 s
    lo, hi = a.min(), a.max()
    T("time →", rx1, ry0 - 18, 11, 400, "end", "#59636e"); out.append(f'<text x="{rx0 + 14}" y="{ry0 + 2 * rh - 6}" font-size="11" fill="#59636e" text-anchor="middle" transform="rotate(-90 {rx0 + 14} {ry0 + 2 * rh - 6})">action (joint 2) →</text>'); T("same 15-step action chunk", (rx0 + rx1) / 2 + 20, ry0 - 18, 13, 600, "middle")
    for g in (0, 0.25, 0.5, 0.75, 1.0):
        out.append(f'<line x1="{tx(g)}" y1="{ry0 - 8}" x2="{tx(g)}" y2="{ry0 + 4 * rh - 12}" stroke="#eef0f3"/>')
        T(f"{g:g} s", tx(g), ry0 + 4 * rh + 2, 10, 400, "middle", "#8c959f")
    for r_, (name, sub, rate_k, col) in enumerate(rows):
        yc = ry0 + r_ * rh; t = np.r_[0, np.cumsum((1 / 15) / rate_k)]
        pts = [(tx(t[i + 1]), yc + 38 - 30 * (a[i] - lo) / (hi - lo + 1e-9)) for i in range(15)]
        T(name, lx, yc + 26, 15, 700, "start", col); T(sub, lx, yc + 42, 10, 400, "start", "#59636e")
        out.append(f'<polyline points="{" ".join(f"{px:.1f},{py:.1f}" for px, py in pts)}" fill="none" stroke="{col}" stroke-width="2" stroke-opacity="0.75"/>')
        for px, py in pts: out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.6" fill="#fff" stroke="{col}" stroke-width="1.8"/>')
        T(f"{t[-1]:.2f} s", pts[-1][0] + 10, pts[-1][1] + 4, 11, 600, "start", col)
        # connector from the tempo cells (q50: dashed, no channel)
        sy = tempo_y[r_ - 1] if r_ else tempo_y[0] - 26
        dash = ' stroke-dasharray="4 4"' if r_ == 0 else ""
        out.append(f'<path d="M{x0 + cw + 2},{sy} C{x0 + cw + 40},{sy} {lx - 40},{yc + 21} {lx - 6},{yc + 21}" fill="none" stroke="{col}" stroke-width="1.6"{dash} stroke-opacity="0.8"/>')
    out.append("</svg>")
    return "\n".join(out)

if __name__ == "__main__":
    print(figure(sys.argv[1]))
