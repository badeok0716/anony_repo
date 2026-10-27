"""Smoothness of fully-successful ours-q99 runs (2026-10-27): jerk RMS, descent jerk, velocity jump across chunk switches."""
import json, csv, os, sys
import numpy as np
D = sys.argv[1]; marks = json.load(open(D + "/marks.json"))
def metrics(path, t_end):
    rows = list(csv.DictReader(open(path)))
    t = np.array([float(r["t"]) for r in rows]); p = np.array([[float(r["ee_x"]), float(r["ee_y"]), float(r["ee_z"])] for r in rows])
    pid = np.array([int(float(r["plan_id"] or 0)) for r in rows]); m = t <= t_end; t, p, pid = t[m], p[m], pid[m]
    ps = np.stack([np.convolve(p[:, j], np.ones(5) / 5, mode="same") for j in range(3)], 1); dt = np.gradient(t)
    v = np.gradient(ps, axis=0) / dt[:, None]; a = np.gradient(v, axis=0) / dt[:, None]; j = np.gradient(a, axis=0) / dt[:, None]
    jn = np.linalg.norm(j, axis=1)[10:-10]
    desc = v[:, 2] < -0.03; desc[:10] = desc[-10:] = False
    b = np.flatnonzero(np.diff(pid) != 0) + 1; b = b[(b > 10) & (b < len(t) - 10)]
    dv = np.linalg.norm(v[b + 3] - v[b - 3], axis=1)
    db = [abs(v[i + 3, 2] - v[i - 3, 2]) for i in b if v[i, 2] < -0.03]
    return np.sqrt(np.mean(jn ** 2)), np.sqrt(np.mean(j[desc, 2] ** 2)), dv.mean(), np.mean(db) if db else np.nan, np.percentile(dv, 95)
res = {"banana": [], "cube": []}
for rel, mk in marks.items():
    task, total = ("banana", 2) if "banana" in rel else ("cube", 9)
    r = metrics(os.path.join(D, rel), mk[total - 1]); res[task].append((os.path.basename(rel)[3:18], mk[total - 1]) + r)
for task, rows in res.items():
    print(f"== {task} (sorted by descent jerk; current pick marked *)")
    cur = "20261022_084414" if task == "banana" else "20261021_111052"
    for e in sorted(rows, key=lambda x: x[3]):
        print(("*" if e[0] == cur else " "), f"{e[0]} done {e[1]:5.1f}s  jerkRMS {e[2]:6.1f}  descentJz {e[3]:6.1f}  chunkDV {e[4]:.4f}  descentChunkDV {e[5]:.4f}  chunkDV_p95 {e[6]:.4f}")
