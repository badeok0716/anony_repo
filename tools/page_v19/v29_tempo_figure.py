"""Inline SVG for the page (2026-10-11; 2026-10-15: brace over the 8 action cells -> "q50 retimed action"): the action expert's 32-dim step output (7 joints, gripper, 3 tempo channels at
dims 8-10, padding) -> q50 (default step 1/15 s) and the q90/q95/q99 channels -> the same 15-step chunk on a time axis,
whose step spacing shrinks with the predicted per-step speed-up. Data: cup rollout 041209, chunk 2 (query 1: grasp, lift, carry), joint 2."""
import json, sys, numpy as np

def figure(chunks_json, k=1, joint=1):
    q = json.load(open(chunks_json))["queries"][k]
    a = np.array(q["actions"])[:, joint]; rate = np.exp(np.array(q["tempo"]))           # (15, 3)
    a0 = float(q["state"][joint])                                                       # where the chunk starts
    rows = [("q50 retimed action", "default step · 1/15 s", np.full(15, 1.0), "#0ea5e9")] + \
           [(n, "tempo channel", rate[:, i], c) for i, (n, c) in enumerate((("q90", "#8b5cf6"), ("q95", "#16a34a"), ("q99", "#d97706")))]
    W, H = 1000, 404; out = [f'<svg class="tempo-fig" viewBox="0 0 {W} {H}" role="img" aria-label="The action expert outputs 32 values per step: 7 joints and the gripper (the action, retimed at the default step as q50) and three tempo channels at dims 8-10. Each channel retimes the same 15-step action chunk.">']
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
    # brace over the 8 action cells (7 joints + gripper): the q50 row is this action at the default step (2026-10-15)
    bx, bw, br = x0 + cw + 4, 5, 6; byt, byb = y0, y0 + 8 * (ch + 2) - 2; bym = (byt + byb) / 2
    out.append(f'<path d="M{bx},{byt} Q{bx + bw},{byt} {bx + bw},{byt + br} L{bx + bw},{bym - br} Q{bx + bw},{bym} {bx + 2 * bw},{bym} '
               f'Q{bx + bw},{bym} {bx + bw},{bym + br} L{bx + bw},{byb - br} Q{bx + bw},{byb} {bx},{byb}" fill="none" stroke="#0ea5e9" stroke-width="1.6"/>')
    T("7 joints", x0 - 8, y0 + 3.5 * (ch + 2) + 4, 11, 400, "end", "#59636e")
    T("gripper", x0 - 8, y0 + 7 * (ch + 2) + 9, 11, 400, "end", "#59636e")
    T("tempo ×3", x0 - 8, tempo_y[1] + 4, 11, 600, "end", "#b45309")
    T("dims 8–10", x0 - 8, tempo_y[1] + 17, 10, 400, "end", "#b45309")
    T("padding", x0 - 8, y0 + 12 * (ch + 2) + 10, 11, 400, "end", "#8c959f")
    T("(dims 11–31)", x0 - 8, y0 + 12 * (ch + 2) + 23, 10, 400, "end", "#8c959f")
    # --- rows: q50 on top, then q90 / q95 / q99
    rx0, rx1, ry0, rh, lx = 400, 975, 60, 78, 256
    tx = lambda t: rx0 + 40 + (rx1 - rx0 - 60) * t                    # 0..1 s
    lo, hi = min(a.min(), a0), max(a.max(), a0); amp = 44
    T("time →", rx1, ry0 - 18, 11, 400, "end", "#59636e"); out.append(f'<text x="{rx0 + 14}" y="{ry0 + 2 * rh - 6}" font-size="11" fill="#59636e" text-anchor="middle" transform="rotate(-90 {rx0 + 14} {ry0 + 2 * rh - 6})">action (joint 2) →</text>'); T("same 15-step action chunk", (rx0 + rx1) / 2 + 20, ry0 - 18, 13, 600, "middle")
    for g in (0, 0.25, 0.5, 0.75, 1.0):
        out.append(f'<line x1="{tx(g)}" y1="{ry0 - 8}" x2="{tx(g)}" y2="{ry0 + 4 * rh - 12}" stroke="#eef0f3"/>')
        T(f"{g:g} s", tx(g), ry0 + 4 * rh + 4, 10, 400, "middle", "#8c959f")
    for r_, (name, sub, rate_k, col) in enumerate(rows):
        yc = ry0 + r_ * rh; t = np.r_[0, np.cumsum((1 / 15) / rate_k)]
        Y = lambda v: yc + 52 - amp * (v - lo) / (hi - lo + 1e-9)
        pts = [(tx(t[i + 1]), Y(a[i])) for i in range(15)]
        sx, sy0 = tx(0), Y(a0)                                    # chunk start: the arm's state when the chunk begins
        out.append(f'<line x1="{sx:.1f}" y1="{sy0:.1f}" x2="{pts[0][0]:.1f}" y2="{pts[0][1]:.1f}" stroke="{col}" stroke-width="1.6" stroke-dasharray="3 3"/>')
        out.append(f'<circle cx="{sx:.1f}" cy="{sy0:.1f}" r="5" fill="#fff" stroke="{col}" stroke-width="1.8" stroke-dasharray="2.5 2"/>')
        T(name, lx, yc + 32, 15, 700, "start", col); T(sub, lx, yc + 48, 10, 400, "start", "#59636e")
        out.append(f'<polyline points="{" ".join(f"{px:.1f},{py:.1f}" for px, py in pts)}" fill="none" stroke="{col}" stroke-width="2" stroke-opacity="0.75"/>')
        for px, py in pts: out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.6" fill="#fff" stroke="{col}" stroke-width="1.8"/>')
        T(f"{t[-1]:.2f} s", pts[-1][0] + 10, pts[-1][1] + 4, 11, 600, "start", col)
        # connector from the tempo cells (q50: dashed, no channel)
        sx0, sy = (x0 + cw + 2, tempo_y[r_ - 1]) if r_ else (bx + 2 * bw + 1, bym)   # q50: from the brace tip
        out.append(f'<path d="M{sx0},{sy} C{sx0 + 38},{sy} {lx - 40},{yc + 27} {lx - 6},{yc + 27}" fill="none" stroke="{col}" stroke-width="1.6" stroke-opacity="0.8"/>')
    out.append(f'<circle cx="{rx0 + 46}" cy="{H - 14}" r="5" fill="#fff" stroke="#59636e" stroke-width="1.6" stroke-dasharray="2.5 2"/>')
    T("chunk start (arm state when the chunk begins)", rx0 + 58, H - 10, 11, 400, "start", "#59636e")
    out.append(f'<circle cx="{rx0 + 360}" cy="{H - 14}" r="4" fill="#fff" stroke="#59636e" stroke-width="1.6"/>')
    T("predicted waypoints", rx0 + 370, H - 10, 11, 400, "start", "#59636e")
    out.append("</svg>")
    return "\n".join(out)

if __name__ == "__main__":
    print(figure(sys.argv[1]))
