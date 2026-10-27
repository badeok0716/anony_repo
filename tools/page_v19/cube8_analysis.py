"""Why does ours-q99 cube run 101743 twitch around the 8th cube (35-45 s)? (2026-10-27)"""
import sys, json, csv
import numpy as np
sys.path.insert(0, "/home/always216/ROBOT/analysis/tempo_viz_20261004")
from v04_fk import fk
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
R = "/home/always216/ROBOT/analysis/zeroshot_20261027/raw/v3_20261021_101743"
C = json.load(open(R + "_chunks.json")); Q = C["queries"]
S = list(csv.DictReader(open(R + "_steps.csv")))
t = np.array([float(r["t"]) for r in S]); ee = np.array([[float(r[k]) for k in ("ee_x", "ee_y", "ee_z")] for r in S])
gc = np.array([float(r["closure_cmd"] or 0) for r in S]); gm = np.array([float(r["closure_meas"] or 0) for r in S])
pid = np.array([int(float(r["plan_id"] or 0)) for r in S]); stall = np.array([float(r["stall_s"] or 0) for r in S])
v = np.gradient(ee, t, axis=0); sp = np.linalg.norm(v, axis=1)
sp_s = np.convolve(sp, np.ones(5) / 5, mode="same")
marks = [m["t_s"] for m in json.load(open(R + "_episode.json"))["marks"]]

# per query: predicted EE path (FK of the 15 joint waypoints), tempo, info
rows = []
prev = None
for q in Q:
    A = np.array(q["actions"]); P = fk(A[:, :7]); rate = np.exp(np.array(q["tempo"]))[:, 2]   # col 2 = q99
    info = q.get("info") or {}
    div = np.nan
    if prev is not None:
        # previous chunk's waypoints still ahead at this query time vs the new chunk's waypoints (same index offset)
        dt_q = q["t"] - prev["t"]; k0 = int(round(dt_q * 15 * np.mean(prev["rate"][:5])))
        n = min(15 - k0, 15)
        if n > 2: div = float(np.mean(np.linalg.norm(prev["P"][k0:k0 + n] - P[:n], axis=1))) * 1000
    g_pred = A[:, 7]
    rows.append(dict(t=q["t"], P=P, rate=rate, div=div, kind=info.get("kind"), seam=info.get("seam"), gap=info.get("seam_gap_mrad"),
                     retime=info.get("retime"), capped=q.get("rate_capped"), rtc=q.get("rtc_prefix_len"), g0=float(g_pred[0]), gmin=float(g_pred.min()), gmax=float(g_pred.max()),
                     reason=info.get("reason"), skipped=info.get("skipped"), z0=float(P[0, 2]), zend=float(P[-1, 2])))
    prev = rows[-1]
def table(a, b):
    print(f"{'t':>6} {'div_mm':>7} {'rate_mean':>9} {'capped':>6} {'kind':>8} {'seam':>11} {'gap_mrad':>8} {'retime':>6} {'rtc':>3} {'grip pred 0/min/max':>20} {'z0->z14 mm':>12}")
    for r in rows:
        if a <= r["t"] <= b:
            print(f"{r['t']:6.2f} {r['div']:7.1f} {np.mean(r['rate']):9.2f} {str(r['capped']):>6} {str(r['kind']):>8} {str(r['seam']):>11} {r['gap'] if r['gap'] is None else round(r['gap'],1)!s:>8} {r['retime'] if r['retime'] is None else round(r['retime'],2)!s:>6} {r['rtc']!s:>3} "
                  f"{r['g0']:.2f}/{r['gmin']:.2f}/{r['gmax']:.2f}{'':>6} {r['z0']*1000:5.0f}->{r['zend']*1000:4.0f}")
print("success marks:", [round(m, 1) for m in marks])
print("\n== 8th cube window 34-46 s"); table(34, 46)
print("\n== comparison: 2nd-3rd cube 4.5-13.8 s"); table(4.5, 13.8)
win = lambda a, b: [r for r in rows if a <= r["t"] <= b]
for lab, (a, b) in (("cube 8 (35.3-44.9)", (35.3, 44.9)), ("cubes 2-7 (4.5-35.3)", (4.5, 35.3)), ("cube 9 (44.9-52.9)", (44.9, 52.9))):
    w = win(a, b); dv = [r["div"] for r in w if not np.isnan(r["div"])]
    m = (t >= a) & (t <= b)
    print(f"{lab}: queries {len(w)}, plan change (div) mean {np.mean(dv):.1f} mm, p90 {np.percentile(dv, 90):.1f} mm; ee speed mean {sp[m].mean():.3f}; "
          f"speed reversals/s {np.sum(np.diff(np.sign(np.diff(sp_s[m]))) != 0) / (b - a):.1f}; stall_s max {stall[m].max():.2f}; gripper cmd toggles {np.sum(np.abs(np.diff((gc[m] > 0.5).astype(int))))}")
fig, ax = plt.subplots(4, 1, figsize=(15, 12), sharex=True)
m = (t >= 33) & (t <= 47)
ax[0].plot(t[m], ee[m, 2] * 1000, "k"); ax[0].set_ylabel("ee z (mm)")
ax0 = ax[0].twinx(); ax0.plot(t[m], gc[m], "r", alpha=0.6, label="gripper cmd"); ax0.plot(t[m], gm[m], "m--", alpha=0.6, label="gripper meas"); ax0.legend(loc="upper right")
ax[1].plot(t[m], sp_s[m], "b"); ax[1].set_ylabel("ee speed (m/s)")
for b in t[m][np.flatnonzero(np.diff(pid[m]) != 0) + 1]: ax[1].axvline(b, color="gray", lw=0.4)
w = win(33, 47); ax[2].stem([r["t"] for r in w], [r["div"] for r in w]); ax[2].set_ylabel("plan change vs previous chunk (mm)")
ax[3].plot([r["t"] for r in w], [np.mean(r["rate"]) for r in w], "o-"); ax[3].set_ylabel("q99 rate (mean over chunk)")
for a_ in ax:
    for mk in marks: a_.axvline(mk, color="green", lw=1.2, ls=":")
plt.tight_layout(); plt.savefig("/home/always216/ROBOT/analysis/zeroshot_20261027/cube8_analysis.png", dpi=60)
