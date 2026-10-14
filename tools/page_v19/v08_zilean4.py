"""Zilean v4 (feedback 3): v2 layout, but the 3D end-effector path shows only the current phase(s).

Phases are cut at the gripper events (pick 1, place 1, pick 2, place 2 -> 5 phases). The phases occupied by the two
runners (ours at rollout time T, the 1/15-s clock at tau^-1(T)) are drawn in white with their action ticks and fade
in/out as the runners move on. Also: video legend (ours = tempo q99, ghost = 1/15 s), 1x real-time badge, displayed
speed-up smoothed over +-0.12 s, split times on the progress race, optional ghost limited to the end-effector
(--ghost-focus: soft ellipse around the ghost's projected fingertip, camera from v06b).
"""
import argparse, json, math
import numpy as np, pandas as pd, cv2
from PIL import Image, ImageDraw
import v02_render
from v01_tempo_clock import tempo_clock
from v02_render import load_panel, frame_at, font, badge, write, gold_vignette, speed_color, GOLD, CYAN, FPS
from v03_stabilize import stabilize
from v19_segments import segments, seg_index
from v04_fk import fk, fk_pose
from v05_zilean2 import gripper_events, View3D

BG, FG, DIM, PANEL = (16, 17, 24), (238, 238, 242), (150, 152, 165), (26, 28, 38)
W, H = 1600, 900
CROP = (0, 406, 40, 700)

SPLIT = False  # --split: no overlay; left = the same footage slowed to 1 action / (1/15 s), right = ours (real time)

def split_badges(d, box, T, done_t, label, col, font, badge, off=0.0):
    """Timer (green Done at done_t) and the side label on one split video box (x, y, w, h); shown as time since the
    policy start (T + off)."""
    x, y, w, h = box
    badge(d, (x + 14, y + 14), f"{max(0.0, min(T, done_t) + off):5.1f} s" if T < done_t else f"Done ({done_t + off:.2f}s)", font("mono", 22),
          (30, 30, 30) if T < done_t else (34, 160, 70))
    badge(d, (x + w // 2, y + h - 14), label, font("Bold", 19), (14, 14, 18), fg=col, anchor="md")

OFFSET = 0.0   # displayed time = clip time + OFFSET = time since the policy start (rollout log)
WT = lambda x: max(0.0, x + OFFSET)
PRE = 0.0      # --start-at-policy: render from the policy start (clip time -OFFSET), holding the first frame (2026-10-14)
PRE_T = PRE_R = PRE_TAU = None   # rollout-log rate / clock in clip time, used before the clip's first frame

from v26_gauge import pct
GAUGE = False   # --gauge: speedometer on the ours split video (v26)
RATE_LOG = []   # per output frame (T, displayed ours rate, ours done) for the engine sound (v26)

SEGMODE = "A"  # 3D segments: "A" per hand gesture, "B" pick/place phases (--segments)
CAUSE = None  # (clip-time grid, cause per sample: 0 model tempo, 1 arm limits, 2 gripper speed) set by __main__
CAUSE_TEXT = {0: "robot limits not binding", 1: "capped by the arm's vel / acc limits", 2: "capped by the gripper speed"}
def cause_at(T, win=0.12):
    if CAUSE is None: return 0
    g, cz = CAUSE; m = (g >= T - win) & (g <= T + win)
    return int(np.bincount(cz[m], minlength=3).argmax()) if m.any() else 0

def cause_on_clip(t0_log, cz0, lag, D, dt=0.005):
    g = np.arange(0.0, D + 1e-9, dt); tl = g + lag
    i = np.clip(np.searchsorted(t0_log, tl), 0, len(t0_log) - 1)
    cz = np.where((tl < t0_log[0]) | (tl > t0_log[-1]), 0, cz0[i])
    return g, cz.astype(int)
PX = 1.0  # work-frame pixels per page-panel pixel (Drive original: > 1)

def ghost(now, slow, alpha, focus=None, lo=25, hi=70):
    kb = int(7 * PX) // 2 * 2 + 1
    diff = cv2.GaussianBlur(np.abs(now - slow).max(2), (kb, kb), 0)
    m = np.clip((diff - lo) / (hi - lo), 0, 1) * alpha
    if focus is not None: m = m * focus
    tint = slow * 0.7 + np.array(CYAN, np.float32) * 0.3
    return now * (1 - m[..., None]) + tint * m[..., None]

def focus_mask(shape, uv, ax=80, ay=120, dy=-30):
    """Soft flat-top ellipse around the ghost's fingertip (centre shifted up towards the wrist)."""
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]].astype(np.float32)
    ax, ay, dy = ax * PX, ay * PX, dy * PX
    rr = ((xx - uv[0]) / ax) ** 2 + ((yy - uv[1] - dy) / ay) ** 2
    return np.exp(-rr ** 2)

def fit_crop_valid(Hs, shape, crop):
    """Shrink `crop` (x0, x1, y0, y1) about its centre, aspect kept, until no stabilized frame has a replicated
    (uncovered) border inside it: minimal crop, the panel then shows real pixels only (feedback 2026-10-06)."""
    h, w = shape; ones = np.full((h, w), 255, np.uint8); valid = ones.copy()
    for H_ in Hs:
        valid &= cv2.warpPerspective(ones, H_, (w, h), flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT)
    x0, x1, y0, y1 = crop; cx, cy, hw, hh = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
    for s_ in np.arange(1.0, 0.5, -0.002):
        r_ = (int(np.floor(cx - hw * s_)), int(np.ceil(cx + hw * s_)), int(np.floor(cy - hh * s_)), int(np.ceil(cy + hh * s_)))
        if r_[0] >= 0 and r_[2] >= 0 and r_[1] <= w and r_[3] <= h and valid[r_[2]:r_[3], r_[0]:r_[1]].all(): return r_, s_
    return crop, 1.0

def phase_names(events):
    names, n = [], {"pick": 0, "place": 0}
    for _, lab in events:
        lab = "pick" if lab == "grasp" else lab
        n[lab] += 1
        names.append(("reach" if lab == "pick" else "carry") + f" → {lab} {n[lab]}")
    return names + ["retreat"]

QNAMES = {0: "q90", 1: "q95", 2: "q99"}  # tempo columns of the action expert (user: q90/q95/q99)

def extend_to_stop(stem, t, r, tau, q, steps, v_stop=0.05, hold_ms=30):
    """The client log ends at ctrl-c while the arm may still be braking. Append the NUC log's measured joints (1 kHz,
    same tick counter) until the arm stops; the braking tail runs at r = 1 on both clocks (no policy timing)."""
    nl = json.load(open(stem + "_episode.json"))["nuc_log"]
    tick, qn = np.asarray(nl["tick"]), np.asarray(nl["q"], float)
    k_end = int(steps["execution_tick"].iloc[-1]); sel = tick > k_end
    if not sel.any(): return t, r, tau, q
    tt = t[-1] + (tick[sel] - k_end) / 1000.0; qq = qn[sel]
    sp = np.linalg.norm(np.gradient(qq, tt, axis=0), axis=1)
    stop = next((i for i in range(len(tt) - hold_ms) if (sp[i:i + hold_ms] < v_stop).all()), len(tt) - 1)
    tt, qq = tt[:stop + 1:10], qq[:stop + 1:10]
    return (np.r_[t, tt], np.r_[r, np.ones(len(tt))], np.r_[tau, tau[-1] + (tt - t[-1])], np.vstack([q, qq]))

def clip_timebase(t, r, tau, q, steps, lag, D, dt=0.005):
    """Rollout arrays -> clip time [0, D] (clip t=0 is rollout t=lag). Outside the policy (before its start or after the
    arm stopped) the robot stands still and both clocks run at r = 1."""
    if lag < t[0]:
        tt = np.arange(lag - dt, t[0], dt)
        t, r, tau, q = np.r_[tt, t], np.r_[np.ones(len(tt)), r], np.r_[tau[0] - (t[0] - tt), tau], np.vstack([np.repeat(q[:1], len(tt), 0), q])
    if lag + D > t[-1]:
        tt = np.arange(t[-1] + dt, lag + D + dt, dt)
        t, r, tau, q = np.r_[t, tt], np.r_[r, np.ones(len(tt))], np.r_[tau, tau[-1] + tt - t[-1]], np.vstack([q, np.repeat(q[-1:], len(tt), 0)])
    tg = np.arange(0.0, D + 1e-9, dt); tl = tg + lag
    r2 = np.interp(tl, t, r); tau2 = np.interp(tl, t, tau) - np.interp(lag, t, tau)
    q2 = np.stack([np.interp(tl, t, q[:, j]) for j in range(7)], 1)
    steps = steps.copy(); steps["t"] = steps["t"] - lag
    return tg, r2, tau2, q2, steps

def render(frames, t, r, tau, steps, chunks, cam=None, alpha=0.4, ghost_focus=False, col=2, t_end=None, q=None, rm=None):
    """t, r, tau, q may extend past the policy end t_end (braking tail, extend_to_stop)."""
    qname = QNAMES.get(col, f"col {col}")
    if q is None: q = steps[[f"q{i}" for i in range(1, 8)]].to_numpy()
    if t_end is None: t_end = t[-1]
    t_stop, tau_stop = t[-1], tau[-1]
    tau_end = float(np.interp(t_end, t, tau)); dur = tau_stop + 1.6
    ts_steps = steps["t"].to_numpy()
    ee = fk(q)
    ev = [e_ for e_ in gripper_events(ts_steps, steps["closure_meas"].to_numpy()) if 0 < e_[0] < t_end]
    ev_t = [a for a, _ in ev]
    bounds = [t[0]] + ev_t + [t_stop]                    # phase i = [bounds[i], bounds[i+1]]
    pnames = phase_names(ev)
    phase_of = lambda tt: int(np.clip(np.searchsorted(ev_t, tt, side="right"), 0, len(ev_t)))
    tick_t = np.array([float(np.interp(k / 15, tau, t)) for k in range(int(tau_end * 15) + 1)])
    ticks = np.stack([np.interp(tick_t, t, ee[:, j]) for j in range(3)], 1)
    chunk_xyz = [fk(np.asarray(c["actions"])[:, :7]) for c in chunks]
    chunk_rate = [np.exp(np.asarray(c["tempo"])[:, col]) for c in chunks]
    pid = steps["plan_id"].to_numpy()
    win = 0.12
    ct, cr = (np.r_[PRE_T[PRE_T < t[0]], t], np.r_[PRE_R[PRE_T < t[0]], r]) if PRE_T is not None else (t, r)
    r_disp = lambda T: float(np.mean(np.interp(np.linspace(T - win, T + win, 25), ct, cr)))
    if rm is None: rm = r
    rm_disp = lambda T: float(np.mean(np.interp(np.linspace(T - win, T + win, 25), t, rm)))
    x0c, x1c, y0c, y1c = CROP
    ph = H - 40; pw = int((x1c - x0c) * ph / (y1c - y0c))
    view = View3D.from_camera(ee, (pw + 70, 100, 1040, 590), cam["P"]) if cam is not None else View3D(ee, (pw + 70, 100, 1040, 590))
    eex = lambda tt: np.array([np.interp(tt, t, ee[:, j]) for j in range(3)])
    if ghost_focus:
        P, off = np.array(cam["P"]), np.r_[cam["offset_flange_m"], 1.0]
        tip = np.einsum("nij,j->ni", fk_pose(q), off)[:, :3]
        def tip_uv(tt):
            X = np.r_[[np.interp(tt, t, tip[:, j]) for j in range(3)], 1.0] @ P.T
            return X[:2] / X[2]
    ev_names = [(float(np.interp(a, t, tau)), nm.split("→ ")[1], a) for (a, _), nm in zip(ev, pnames)]
    segb, segn = segments(ev, t[0], t_stop, SEGMODE, (), None)   # 3D: each runner's current segment only
    fade_f, fade_s = np.zeros(len(segn)), np.zeros(len(segn)); k_fade = 1 - math.exp(-1 / (FPS * 0.12))
    for n in range(int((dur + PRE) * FPS)):
        T = n / FPS - PRE
        t_slow = float(np.interp(T, tau, t)) if T < tau_stop else t_stop
        t_fast = min(T, t_stop)
        rnow = r_disp(T) if T < t_end else 1.0
        RATE_LOG.append((T, float(r_disp(T)) if T < t_end else 1.0, bool(T >= t_end)))
        rmod = rm_disp(T) if T < t_end else 1.0
        act = float(np.interp(T, t, tau)) if T < t_end else tau_end
        if T < 0 and PRE_TAU is not None: act = float(np.interp(T, PRE_T, PRE_TAU))   # before the clip: log clock
        now = frame_at(frames, t_fast, nearest=True)                  # real time: whole source frames
        slow = frame_at(frames, t_slow, nearest=True)                 # the same source frames, slowed down
        if True:                                                       # identical frames at the end -> exact overlap
            img = ghost(now, slow, alpha, focus_mask(now.shape[:2], tip_uv(t_slow)) if ghost_focus else None)
        else:
            img = now
        img = img[y0c:y1c, x0c:x1c]
        img = gold_vignette(img, 0.8 * min(max((rnow - 1) / 1.2, 0), 1))
        img = cv2.resize(img, (pw, ph), interpolation=cv2.INTER_CUBIC)
        cv = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(cv, "RGBA")
        cv.paste(Image.fromarray(img.clip(0, 255).astype(np.uint8)), (20, 20))
        badge(d, (36, 36), f"{WT(T):4.2f} s" if T < t_end else f"Done ({WT(t_end):.2f}s)", font("mono", 24),
              (30, 30, 30) if T < t_end else (34, 160, 70))
        badge(d, (20 + pw - 16, 36), "1× REAL TIME", font("Black", 20), (20, 20, 20), fg=FG, anchor="ra")
        # legend: what is the video, what is the ghost
        lx, ly = 20 + pw - 16, 20 + ph - 16
        d.rounded_rectangle((lx - 352, ly - 66, lx + 6, ly + 8), 10, fill=(14, 14, 18, 215))
        d.ellipse((lx - 338, ly - 54, lx - 324, ly - 40), fill=GOLD)
        d.text((lx - 314, ly - 47), f"Video: Ours, tempo {qname}", font=font("Bold", 19), fill=GOLD, anchor="lm")
        d.ellipse((lx - 338, ly - 24, lx - 324, ly - 10), outline=CYAN, width=3)
        d.text((lx - 314, ly - 17), "Ghost: 1 action / (1/15 s)", font=font("Bold", 19), fill=CYAN, anchor="lm")
        # --- header
        hx = 1100
        d.text((hx, 40), "SPEED-UP (EXECUTED)", font=font("Black", 24), fill=DIM)
        if T < t_end:
            d.text((hx - 6, 66), pct(rnow), font=font("Black", 150), fill=speed_color(rnow) if rnow > 1.01 else (200, 200, 200))
            d.text((hx, 250), ("faster" if rnow >= 1 else "slower") + " than one action per 1/15 s", font=font("Bold", 24), fill=FG)
        else:
            d.text((hx - 6, 66), pct(WT(tau_end) / WT(t_end)), font=font("Black", 150), fill=speed_color(WT(tau_end) / WT(t_end)))
            d.text((hx, 250), f"overall: done in {WT(t_end):.2f} s instead of {WT(tau_end):.2f} s", font=font("Bold", 24), fill=FG)
        if T < t_end:
            cz_ = cause_at(T)
            d.text((hx, 286), f"model {qname} target {pct(rmod)} → executed {pct(rnow)}", font=font("Regular", 19), fill=DIM)
            d.text((hx, 312), CAUSE_TEXT[cz_], font=font("Bold" if cz_ else "Regular", 19), fill=(255, 150, 90) if cz_ else DIM)
        else:
            d.text((hx, 286), f"model {qname} tempo, executed", font=font("Regular", 19), fill=DIM)
            d.text((hx, 312), "within the robot's limits", font=font("Regular", 19), fill=DIM)
        n_ours, n_slow = int(WT(act) * 15), int(WT(min(T, tau_end)) * 15)
        d.text((hx, 380), "ACTIONS EXECUTED", font=font("Black", 20), fill=DIM)
        d.text((hx, 410), f"{n_ours:3d}", font=font("mono", 64), fill=GOLD); d.text((hx + 150, 440), "ours", font=font("Bold", 22), fill=GOLD)
        d.text((hx, 490), f"{n_slow:3d}", font=font("mono", 64), fill=CYAN); d.text((hx + 150, 520), "1 action / (1/15 s)", font=font("Bold", 22), fill=CYAN)
        d.text((hx, 590), f"in the same {WT(T):.2f} s of wall-clock time" if T < t_end else
               f"ours finished at {WT(t_end):.2f} s · now {WT(min(T, tau_end)):.2f} s", font=font("Regular", 19), fill=DIM)
        # --- 3D panel: only the phases the runners are in
        p_fast, p_slow = phase_of(t_fast), phase_of(t_slow)
        sf, ss = seg_index(segb, t_fast), seg_index(segb, t_slow)
        oh = lambda i: np.eye(len(segn))[i]
        fade_f += (oh(sf) - fade_f) * (1.0 if n == 0 else k_fade); fade_s += (oh(ss) - fade_s) * (1.0 if n == 0 else k_fade)
        d.rounded_rectangle((pw + 50, 20, 1060, 640), 14, fill=PANEL)
        d.text((pw + 70, 34), "End-effector path", font=font("Bold", 20), fill=FG)
        d.text((pw + 250, 30), f"ours: {segn[sf]}", font=font("Bold", 17), fill=GOLD)
        if ss != sf:
            d.text((pw + 250, 52), f"1/15 s: {segn[ss]}", font=font("Bold", 17), fill=CYAN)
        d.text((pw + 70, 78), "current phase only · white dot = one action, 1/15 s apart", font=font("Regular", 15), fill=DIM)
        for fd, col in ((fade_s, CYAN), (fade_f, (240, 240, 248))):   # each runner: its own segment only
            for i, a in enumerate(fd):
                if a < 0.02: continue
                sel = (t >= segb[i]) & (t <= segb[i + 1]); seg = ee[sel][::3]
                if len(seg) < 2: continue
                d.line(view(seg), fill=(*col, int(170 * a)), width=3)
                for p_ in ticks[(tick_t >= segb[i]) & (tick_t <= segb[i + 1])]:
                    (u, v), = view(p_); d.ellipse((u - 3, v - 3, u + 3, v + 3), fill=(*col, int(235 * a)))
        k = int(np.clip(np.searchsorted(ts_steps, t_fast, side="right") - 1, 0, len(ts_steps) - 1)); p_id = int(pid[k])
        if T < t_end and 1 <= p_id <= len(chunks):
            uv = view(chunk_xyz[p_id - 1]); d.line(uv, fill=(140, 110, 40, 200), width=2)
            for (u, v), rr in zip(uv, chunk_rate[p_id - 1]):
                d.ellipse((u - 5, v - 5, u + 5, v + 5), outline=speed_color(rr), width=2)
        for tt0, col in ((t_slow, CYAN), (t_fast, GOLD)):
            tr = view(np.array([eex(tt0 - 0.25 * j / 12) for j in range(13)]))
            for j in range(12):
                d.line(tr[j] + tr[j + 1], fill=(*col, int(230 * (1 - j / 12))), width=6)
        for tt0, col, rad in ((t_slow, CYAN, 9), (t_fast, GOLD, 11)):
            (u, v), = view(eex(tt0))
            d.ellipse((u - rad, v - rad, u + rad, v + rad), fill=col, outline=(0, 0, 0), width=2)
        f15 = font("Regular", 15)
        d.text((pw + 70, 592), "● ours", font=f15, fill=GOLD)
        d.text((pw + 150, 592), "● 1 action / (1/15 s)", font=f15, fill=CYAN)
        d.text((pw + 70, 613), "○ running action chunk (ring colour = step speed-up)", font=f15, fill=DIM)
        # --- race on the action clock, with split times
        d.rounded_rectangle((pw + 50, 660, W - 20, H - 20), 14, fill=PANEL)
        d.text((pw + 70, 672), "Task progress", font=font("Bold", 18), fill=FG)
        lx0, lx1 = pw + 250, W - 120
        X = lambda f: lx0 + (lx1 - lx0) * min(max(f, 0), 1)
        for a, name, _ in ev_names:
            x = X(a / tau_end)
            for yy in range(700, 862, 8): d.line((x, yy, x, yy + 4), fill=(80, 82, 96), width=1)
            d.text((x, 694), name, font=font("Regular", 14), fill=DIM, anchor="mb")
        d.line((X(1), 698, X(1), 862), fill=FG, width=3)
        d.text((X(1) + 8, 694), "done", font=font("Bold", 15), fill=FG, anchor="lb")
        lanes = [("Ours", f"tempo {qname}", act / tau_end, GOLD, 742, t_end, -1),
                 ("Without tempo", "1 action / (1/15 s)", min(T, tau_end) / tau_end, CYAN, 820, tau_end, 1)]
        for name, sub, f, col, y, fin, side in lanes:
            d.text((pw + 70, y - 18), name, font=font("Bold", 20), fill=col)
            d.text((pw + 70, y + 6), sub, font=font("Regular", 15), fill=DIM)
            d.rounded_rectangle((lx0, y - 8, lx1, y + 8), 8, fill=(44, 46, 58))
            if f > 0: d.rounded_rectangle((lx0, y - 8, X(f), y + 8), 8, fill=tuple(int(c * 0.65) for c in col))
            for a, _, a_t in ev_names:  # split: wall time at which this runner reached the event
                if f * tau_end >= a - 1e-9:
                    d.text((X(a / tau_end), y + side * 22), f"{WT(a_t) if col == GOLD else WT(a):.2f}", font=font("mono", 14),
                           fill=col, anchor="mm")
            d.ellipse((X(f) - 13, y - 13, X(f) + 13, y + 13), fill=col, outline=(0, 0, 0), width=2)
            if f >= 1 - 1e-6:
                d.text((X(1) + 22, y), f"{WT(fin):.2f} s", font=font("mono", 22), fill=col, anchor="lm")
        if SPLIT:   # same HUD (cut from the overlay canvas), two plain videos side by side + the 3D panel
            sh = 600; sw = int(round((x1c - x0c) * sh / (y1c - y0c))) // 2 * 2
            vid = lambda f_: Image.fromarray(cv2.resize(f_[y0c:y1c, x0c:x1c], (sw, sh), interpolation=cv2.INTER_AREA).clip(0, 255).astype(np.uint8))
            sp = Image.new("RGB", (W, H), BG); ds = ImageDraw.Draw(sp, "RGBA")
            bl, br = (20, 20, sw, sh), (40 + sw, 20, sw, sh)
            sp.paste(vid(slow), bl[:2]); sp.paste(vid(now), br[:2])
            split_badges(ds, bl, T, tau_end, "Without tempo · 1 action / (1/15 s)", CYAN, font, badge, OFFSET)
            split_badges(ds, br, T, t_end, f"Ours · tempo {qname}", GOLD, font, badge, OFFSET)
            if GAUGE:
                from v26_gauge import draw_gauge
                Rg = int(min(72, br[2] * 0.2)); gx, gy = br[0] + br[2] - Rg - 22, br[1] + Rg + 24
                if T < t_end: draw_gauge(ds, gx, gy, Rg, rnow, font)
                else:
                    avg_ = WT(tau_end) / WT(t_end); draw_gauge(ds, gx, gy, Rg, avg_, font, label="avg " + pct(avg_))
            race = cv.crop((pw + 50, 660, W - 20, H - 20)); rw = 2 * sw + 20
            sp.paste(race.resize((rw, int(race.height * rw / race.width)), Image.LANCZOS), (20, 40 + sh))
            x0r = 2 * sw + 60; wr = W - 16 - x0r
            p3 = cv.crop((pw + 50, 20, 1060, 640)); h3 = 560; p3 = p3.resize((int(p3.width * h3 / p3.height), h3), Image.LANCZOS)
            sp.paste(p3, (x0r + (wr - p3.width) // 2, 20))
            hd = cv.crop((1080, 20, W - 20, 340)); ac = cv.crop((1080, 360, W - 20, 640)); sc_ = 0.75
            hd = hd.resize((int(hd.width * sc_), int(hd.height * sc_)), Image.LANCZOS); ac = ac.resize((int(ac.width * sc_), int(ac.height * sc_)), Image.LANCZOS)
            gx = x0r + (wr - hd.width - ac.width - 20) // 2
            sp.paste(hd, (gx, 600)); sp.paste(ac, (gx + hd.width + 20, 610))
            yield np.asarray(sp); continue
        yield np.asarray(cv)

if __name__ == "__main__":
    import imageio_ffmpeg
    v02_render.FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
    ap = argparse.ArgumentParser()
    ap.add_argument("--stem", required=True); ap.add_argument("--web", required=True); ap.add_argument("--camera", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--ghost-focus", action="store_true")
    ap.add_argument("--task", required=True, choices=["cup", "towel"], help="completion rule (v25)")
    ap.add_argument("--gauge", action="store_true", help="speedometer on the ours split video")
    ap.add_argument("--start-at-policy", action="store_true", help="start at the policy start (0.0 s), first frame held")
    ap.add_argument("--rate-log", default=None, help="write per-frame ours rate JSON (engine sound)")
    ap.add_argument("--split", action="store_true", help="side-by-side: slowed footage left, ours right (no overlay)")
    ap.add_argument("--segments", default="A", choices=["A", "B"], help="3D panel segments")
    ap.add_argument("--preview", default=None, help="comma list of output frame indices -> jpg")
    ap.add_argument("--orig", default=None, help="Drive original, 30 fps CFR (frame-aligned with the page clip)")
    ap.add_argument("--orig-affine", default=None, help="a,tx,ty: page-panel px = a * original px + (tx, ty) (v13)")
    ap.add_argument("--work-width", type=int, default=812, help="original is resampled to at most this width")
    a = ap.parse_args()
    SEGMODE = a.segments; SPLIT = a.split; GAUGE = a.gauge
    cam = json.load(open(a.camera)); v02_render.LAG = cam["lag_s"]
    crop = tuple(cam.get("crop", (418, 824, 68, 790)))
    if cam.get("t_hold_video_s"): v02_render.T_HOLD = cam["t_hold_video_s"]
    col = int(json.load(open(a.stem + "_episode.json"))["tempo"])
    t, r, tau, _, rm, cz0 = tempo_clock(a.stem, col=col, return_model=True, return_cause=True)   # r = applied, rm = model
    steps = pd.read_csv(a.stem + "_steps.csv"); chunks = json.load(open(a.stem + "_chunks.json"))["queries"]
    t_log_end = t[-1]
    t0_log, rm0 = t.copy(), rm.copy()
    t, r, tau, q = extend_to_stop(a.stem, t, r, tau, steps[[f"q{i}" for i in range(1, 8)]].to_numpy(), steps)
    t_stop = t[-1]
    # Time base = the page clip (as on the project page): clip t=0 is rollout t=lag, the clip ends where the page shows
    # its own Done label (D). Resample onto clip time; after the arm stopped it simply stands still (r = 1).
    lag = cam["lag_s"]; D = v02_render.T_HOLD + 1.0 / FPS
    rm = np.interp(np.arange(0.0, D + 1e-9, 0.005) + lag, t0_log, rm0, left=1.0, right=1.0)
    CAUSE = cause_on_clip(t0_log, cz0, lag, D)
    from v25_completion import completion, clock_at
    t_comp = completion(a.stem, a.task); off_g = clock_at(t, tau, lag)          # log clocks at the clip start
    if a.start_at_policy:   # log rate / clock before the clip, in clip time (displayed clock = clip time + lag)
        PRE = lag; PRE_T = t - lag; PRE_R = r.copy(); PRE_TAU = tau - lag
    t, r, tau, q, steps = clip_timebase(t, r, tau, q, steps, lag, D)
    tau = tau + (off_g - lag)   # ghost lookup so that both runs share the wall clock since the policy start
    OFFSET = lag
    v02_render.LAG = 0.0
    t_end = t_comp - lag   # Done = paper completion (clip time)
    print(f"tempo column {col} ({QNAMES.get(col)}); rollout log ends {t_log_end:.3f} s, arm stopped {t_stop:.3f} s; "
          f"clip = rollout [{lag:.3f}, {lag + D:.3f}] s -> completion ours {t_comp:.3f} s vs 1 action/(1/15 s) {float(np.interp(t_end, t, tau)) + lag:.3f} s (since policy start)")
    n_need = int(v02_render.T_HOLD * FPS) + 10
    if a.orig:
        # Drive original: same frames as the page clip, panel px = sa * orig px + (tx, ty). Work frames = orig * m;
        # camera (fitted on panel px) and crop are mapped into work px, k = m / sa work px per panel px.
        sa, tx, ty = (float(v) for v in a.orig_affine.split(","))
        cap, src = cv2.VideoCapture(a.orig), []
        while len(src) < n_need:
            ok, f_ = cap.read()
            if not ok: break
            m = min(1.0, a.work_width / f_.shape[1])
            src.append(cv2.cvtColor(cv2.resize(f_, None, fx=m, fy=m, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB).astype(np.float32))
        k = m / sa; PX = k
        A = np.array([[k, 0, -tx * k], [0, k, -ty * k], [0, 0, 1.0]]); cam = dict(cam, P=(A @ np.array(cam["P"])).tolist())
        hh, ww = src[0].shape[:2]
        CROP = (max(0, int(round((CROP[0] - tx) * k))), min(ww, int(round((CROP[1] - tx) * k))),
                max(0, int(round((CROP[2] - ty) * k))), min(hh, int(round((CROP[3] - ty) * k))))
        print(f"original {a.orig}: {len(src)} frames, work {ww}x{hh}, {k:.3f} work px per panel px, crop {CROP}")
        frames, Hs_, _ = stabilize(src)
        CROP, s_ = fit_crop_valid(Hs_, frames[0].shape[:2], CROP); print(f"valid crop {CROP} (x{1 / s_:.3f} zoom)", flush=True)
    else:
        frames, Hs_, _ = stabilize(load_panel(a.web, *crop)[:n_need])
        CROP, s_ = fit_crop_valid(Hs_, frames[0].shape[:2], CROP); print(f"valid crop {CROP} (x{1 / s_:.3f} zoom)", flush=True)
    gen = render(frames, t, r, tau, steps, chunks, cam, ghost_focus=a.ghost_focus, col=col, t_end=t_end, q=q, rm=rm)
    if a.preview:
        want = sorted(int(x) for x in a.preview.split(","))
        for n, f in enumerate(gen):
            if n in want: Image.fromarray(f).save(a.out.replace(".jpg", f"_{n}.jpg"))
            if n >= want[-1]: break
    else:
        import subprocess
        pw = int((CROP[1] - CROP[0]) * (H - 40) / (CROP[3] - CROP[2])) // 2 * 2
        panel = a.out.replace(".mp4", "_panel.mp4")
        def pipe(path, w, h):
            return subprocess.Popen([v02_render.FFMPEG, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
                                     f"{w}x{h}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                                     "-crf", "18", "-movflags", "+faststart", path], stdin=subprocess.PIPE)
        if SPLIT:   # panel = the two videos with their labels
            sw = int(round((CROP[1] - CROP[0]) * 600 / (CROP[3] - CROP[2]))) // 2 * 2; box = (20, 20, 2 * sw + 20, 600)
        else:
            box = (20, 20, pw, H - 40)   # the left ghost video only
        p_full, p_panel = pipe(a.out, W, H), pipe(panel, box[2], box[3])
        for f in gen:
            p_full.stdin.write(f.tobytes())
            p_panel.stdin.write(np.ascontiguousarray(f[box[1]:box[1] + box[3], box[0]:box[0] + box[2]]).tobytes())
        for p_ in (p_full, p_panel): p_.stdin.close(); p_.wait()
        print("wrote", a.out, "and", panel)
        if a.rate_log:
            json.dump({"fps": FPS, "frames": [{"T": T_, "r": r_, "done": d_} for T_, r_, d_ in RATE_LOG]}, open(a.rate_log, "w"))
            print("rate log", a.rate_log, len(RATE_LOG), "frames", flush=True)
