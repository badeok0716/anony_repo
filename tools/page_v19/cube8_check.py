import json, csv, numpy as np
R = "/home/always216/ROBOT/analysis/zeroshot_20261027/raw/v3_20261021_101743"
Q = json.load(open(R + "_chunks.json"))["queries"]
S = list(csv.DictReader(open(R + "_steps.csv"))); t = np.array([float(r["t"]) for r in S])
ee = np.array([[float(r[k]) for k in ("ee_x", "ee_y", "ee_z")] for r in S]); sp = np.convolve(np.linalg.norm(np.gradient(ee, t, axis=0), axis=1), np.ones(5) / 5, mode="same")
print(" t_query  rate_pred  rate_used(cap)  chunk_runs_s  next_query_in_s  starved?  min_speed_before_next")
starve = []
for i, q in enumerate(Q[:-1]):
    r = np.exp(np.array(q["tempo"]))[:, 2]; cap = q.get("rate_cap") or 99; ru = np.minimum(r, cap)
    dur = float(np.sum(1 / (15 * ru))); nxt = Q[i + 1]["t"] - q["t"]
    m = (t >= q["t"]) & (t < Q[i + 1]["t"]); vmin = sp[m].min() if m.any() else np.nan
    st = dur < nxt; starve.append((q["t"], st, r.mean()))
    if 35.5 <= q["t"] <= 38.5: print(f"{q['t']:7.2f}  {r.mean():8.2f}  {ru.mean():10.2f}      {dur:8.2f}       {nxt:8.2f}       {'YES' if st else 'no ':>4}     {vmin:.3f}")
st = np.array([s[1] for s in starve]); tt = np.array([s[0] for s in starve]); rr = np.array([s[2] for s in starve])
print(f"\nwhole episode: chunks that run out before the next one arrives: {st.sum()} of {len(st)}")
blocks = []; cur = None
for a, b in zip(tt, st):
    if b and cur is None: cur = [a, a]
    elif b: cur[1] = a
    elif cur is not None: blocks.append(cur); cur = None
print("starved stretches (start-end s, >=2 chunks):", [(round(a, 1), round(b, 1)) for a, b in blocks if b > a])
print(f"predicted q99 rate: episode median {np.median(rr):.2f}, p95 {np.percentile(rr, 95):.2f}; 35.8-38.0 s mean {rr[(tt > 35.8) & (tt < 38.0)].mean():.2f}")
