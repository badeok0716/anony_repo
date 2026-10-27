"""All 30 ours-q99 cube runs: success, misses, smoothness (2026-10-27)."""
import json, csv, os, sys
import numpy as np
D = sys.argv[1]; marks = json.load(open(D + "/marks_cube_all.json")); rows = []
for rel, mk in marks.items():
    R = list(csv.DictReader(open(os.path.join(D, rel))))
    t = np.array([float(r["t"]) for r in R]); p = np.array([[float(r["ee_x"]), float(r["ee_y"]), float(r["ee_z"])] for r in R])
    pid = np.array([int(float(r["plan_id"] or 0)) for r in R]); g = np.array([float(r["closure_meas"] or 0) for r in R])
    t_end = mk[-1] if len(mk) == 9 else min(60.0, t[-1]); m = t <= t_end; t, p, pid, g = t[m], p[m], pid[m], g[m]
    closed, n_g = False, 0
    for x in g:
        if not closed and x > 0.5: closed, n_g = True, n_g + 1
        elif closed and x < 0.3: closed = False
    ps = np.stack([np.convolve(p[:, j], np.ones(5) / 5, mode="same") for j in range(3)], 1); dt = np.gradient(t)
    v = np.gradient(ps, axis=0) / dt[:, None]; a = np.gradient(v, axis=0) / dt[:, None]; j = np.gradient(a, axis=0) / dt[:, None]
    jn = np.linalg.norm(j, axis=1)[10:-10]
    b = np.flatnonzero(np.diff(pid) != 0) + 1; b = b[(b > 10) & (b < len(t) - 10)]
    dv = np.linalg.norm(v[b + 3] - v[b - 3], axis=1); db = [abs(v[i + 3, 2] - v[i - 3, 2]) for i in b if v[i, 2] < -0.03]
    big = (dv > 0.12).sum() / (t_end / 60)
    rows.append((os.path.basename(rel)[3:18], len(mk), mk[-1] if len(mk) == 9 else None, n_g - len(mk), np.sqrt(np.mean(jn ** 2)), dv.mean(), np.mean(db), big))
print("episode          ok  done   miss  jerkRMS chunkDV descDV  bigJumps/min   (run 2 = re-launch from 10:39)")
for r in sorted(rows, key=lambda r: r[5]):
    tag = "*" if r[0] == "20261021_105456" else " "
    run = "run2" if r[0] >= "20261021_103900" else "run1"
    print(f"{tag}{r[0]} {r[1]}/9 {('%.1f' % r[2]) if r[2] else '  -  ':>6} {r[3]:4d}  {r[4]:7.1f} {r[5]:.4f}  {r[6]:.4f}  {r[7]:6.1f}   {run}")
