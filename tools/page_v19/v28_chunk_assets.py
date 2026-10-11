"""Page chunk section assets (2026-10-11): one recorded q99 Cup run replayed on four clocks (q50 = 1 action / (1/15 s),
q90, q95, q99; v20 rule, wall clock since the policy start, Done = paper completion v25).
Writes to OUT/: chunk_q50.mp4 (plain), chunk_q{90,95,99}.mp4 (that clock + the q50 ghost, alpha 0.4), each with the
engine sound of its own clock (v27), and chunk.json for the page (per-frame source times, projected path, B segments,
action dots, predicted chunk waypoints)."""
import argparse, json, subprocess
import numpy as np, pandas as pd, cv2
from PIL import Image
import v02_render
from v02_render import FPS
from v01_tempo_clock import tempo_clock
from v03_stabilize import stabilize
from v04_fk import fk
from v05_zilean2 import gripper_events, View3D
from v08_zilean4 import extend_to_stop, clip_timebase, fit_crop_valid, CROP as CROP0
from v19_segments import segments
from v25_completion import completion
from v27_engine_audio import engine, write_wav
import v08_zilean4

NAMES = ["q50", "q90", "q95", "q99"]; COLS = [None, 0, 1, 2]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stem", required=True); ap.add_argument("--camera", required=True); ap.add_argument("--orig", required=True)
    ap.add_argument("--orig-affine", required=True); ap.add_argument("--out", required=True); ap.add_argument("--height", type=int, default=720)
    a = ap.parse_args()
    import imageio_ffmpeg; ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cam = json.load(open(a.camera)); lag = cam["lag_s"]; v02_render.T_HOLD = cam["t_hold_video_s"]; D = v02_render.T_HOLD + 1.0 / FPS
    t, r, tau, _, rm2 = tempo_clock(a.stem, col=2, return_model=True)
    steps = pd.read_csv(a.stem + "_steps.csv"); chunks = json.load(open(a.stem + "_chunks.json"))["queries"]
    t0, r0 = t.copy(), r.copy()
    models = {c: tempo_clock(a.stem, col=c, return_model=True)[4] for c in (0, 1)}; models[2] = rm2
    t, r, tau, q = extend_to_stop(a.stem, t, r, tau, steps[[f"q{i}" for i in range(1, 8)]].to_numpy(), steps)
    tg, r99, tau1, q, steps = clip_timebase(t, r, tau, q, steps, lag, D)
    m_on = lambda c: np.interp(tg + lag, t0, models[c], left=1.0, right=1.0)
    capped = r99 < m_on(2) - 1e-6
    tp = np.arange(t0[0], lag, 0.005); r99p = np.interp(tp, t0, r0); capp = r99p < np.interp(tp, t0, models[2]) - 1e-6
    t_comp = completion(a.stem, "cup") - lag
    rates, clocks = [], []
    for c in COLS:
        rc = np.ones_like(tg) if c is None else (r99 if c == 2 else np.where(capped, np.minimum(m_on(c), r99), m_on(c)))
        rc = np.maximum(rc, 1e-3)
        rcp = np.ones_like(tp) if c is None else (r99p if c == 2 else np.where(capp, np.minimum(np.interp(tp, t0, models[c]), r99p), np.interp(tp, t0, models[c])))
        off = t0[0] + float(np.sum(np.diff(np.r_[tp, lag]) * (r99p / np.maximum(rcp, 1e-3))))
        clocks.append(off + np.concatenate([[0.0], np.cumsum(np.diff(tg) * (r99 / rc)[1:])])); rates.append(rc)
    done = [float(np.interp(t_comp, tg, ck)) for ck in clocks]
    print("done since policy start:", dict(zip(NAMES, [round(d, 3) for d in done])), flush=True)
    # footage (as v08 --orig)
    sa, tx, ty = (float(v) for v in a.orig_affine.split(","))
    capv, src = cv2.VideoCapture(a.orig), []
    while len(src) < int(v02_render.T_HOLD * FPS) + 10:
        ok, f_ = capv.read()
        if not ok: break
        m = min(1.0, 812 / f_.shape[1])
        src.append(cv2.cvtColor(cv2.resize(f_, None, fx=m, fy=m, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB).astype(np.float32))
    k = m / sa; hh, ww = src[0].shape[:2]; v08_zilean4.PX = k
    P = np.array([[k, 0, -tx * k], [0, k, -ty * k], [0, 0, 1.0]]) @ np.array(cam["P"])
    crop = (max(0, int(round((CROP0[0] - tx) * k))), min(ww, int(round((CROP0[1] - tx) * k))),
            max(0, int(round((CROP0[2] - ty) * k))), min(hh, int(round((CROP0[3] - ty) * k))))
    frames, Hs, _ = stabilize(src); crop, _ = fit_crop_valid(Hs, frames[0].shape[:2], crop)
    x0c, x1c, y0c, y1c = crop; Hh = a.height; Ww = int(round((x1c - x0c) * Hh / (y1c - y0c))) // 2 * 2
    fat = lambda tt: v02_render.frame_at(frames, min(max(tt, 0.0), D - 1e-6), nearest=True)
    dur = max(ck[-1] for ck in clocks) + 0.6; nT = int(dur * FPS); Tg = np.arange(nT) / FPS
    tcs = [np.interp(Tg, ck, tg) for ck in clocks]
    # videos
    for i, nm in enumerate(NAMES):
        silent = f"{a.out}/chunk_{nm}_silent.mp4"
        p = subprocess.Popen([ffmpeg, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{Ww}x{Hh}", "-r", str(FPS), "-i", "-",
                              "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-movflags", "+faststart", silent], stdin=subprocess.PIPE)
        for n in range(nT):
            now = fat(tcs[i][n])
            img = now if i == 0 else v08_zilean4.ghost(now, fat(tcs[0][n]), 0.4)
            img = cv2.resize(img[y0c:y1c, x0c:x1c], (Ww, Hh), interpolation=cv2.INTER_AREA)
            p.stdin.write(np.ascontiguousarray(img.clip(0, 255).astype(np.uint8)).tobytes())
        p.stdin.close(); p.wait()
        win = 0.12
        rr = np.array([np.mean(np.interp(np.linspace(tc - win, tc + win, 25), tg, rates[i])) for tc in tcs[i]])
        dn = Tg >= done[i]
        x = engine(rr, dn, FPS); wav = f"{a.out}/chunk_{nm}.wav"; write_wav(wav, x)
        subprocess.run([ffmpeg, "-v", "error", "-y", "-i", silent, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                        "-b:a", "160k", "-shortest", "-movflags", "+faststart", f"{a.out}/chunk_{nm}.mp4"], check=True)
        print("wrote", nm, flush=True)
    # page data
    ee = fk(q); view = View3D.from_camera(ee, (0, 0, 1000, 1000), P)
    proj = lambda X: [[round(u, 1), round(v, 1)] for u, v in view(np.atleast_2d(X))]
    ts = steps["t"].to_numpy(); pid = steps["plan_id"].to_numpy()
    ev = [e for e in gripper_events(ts, steps["closure_meas"].to_numpy()) if 0 < e[0] < t_comp + 0.5]
    segb, segn = segments(ev, tg[0], tg[-1], "B")
    sel = np.arange(0, len(tg), 3)                                  # 200 Hz grid -> every 15 ms
    tau_done = float(np.interp(t_comp, tg, tau1))
    tick_t = [float(np.interp(kk / 15, tau1, tg)) for kk in range(int(np.interp(tg[-1], tg, tau1) * 15) + 1)]
    plan_t = []; last = None
    for tt_, p_ in zip(ts, pid):
        if p_ != last and 1 <= p_ <= len(chunks): plan_t.append([round(float(tt_), 4), int(p_)]); last = p_
    J = {"fps": FPS, "names": NAMES, "done": [round(d, 4) for d in done], "lag": lag, "clip_done": round(t_comp, 4),
         "T": [round(x, 4) for x in Tg], "tc": [[round(float(x), 4) for x in tc] for tc in tcs],
         "rate": [[round(float(np.interp(x, tg, rates[i])), 3) for x in tcs[i]] for i in range(4)],
         "path_t": [round(float(x), 4) for x in tg[sel]], "path": proj(ee[sel]),
         "seg_bounds": [round(float(b), 4) for b in segb], "seg_names": segn,
         "ticks": proj(np.stack([np.interp(tick_t, tg, ee[:, j]) for j in range(3)], 1)), "tick_t": [round(x, 4) for x in tick_t],
         "plans": plan_t, "chunks": {str(i + 1): proj(fk(np.asarray(c["actions"])[:, :7])) for i, c in enumerate(chunks)},
         "video_size": [Ww, Hh], "source": a.stem}
    json.dump(J, open(f"{a.out}/chunk.json", "w"), separators=(",", ":"))
    print("wrote chunk.json", flush=True)

if __name__ == "__main__":
    main()
