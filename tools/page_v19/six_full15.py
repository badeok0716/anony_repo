"""Full 15-waypoint travel for the six post-grasp candidates (same anchor rule as ../build_postgrasp.py)."""
import json, sys, numpy as np
sys.path.insert(0, '/home/always216/ROBOT/analysis/tempo_viz_20261004'); from v04_fk import fk
sys.path.insert(0, '/home/always216/ROBOT/analysis/training_tempo_viz_20261011'); from build_training_figure import SIDECAR
prev = json.load(open('/home/always216/ROBOT/analysis/training_tempo_viz_20261011/output/manifest.json'))
eps = json.load(open(SIDECAR / 'episodes.json'))['episodes']
states = np.load(SIDECAR / 'states.npy', mmap_mode='r'); times = np.load(SIDECAR / 'source_times.npy', mmap_mode='r')
actions = np.load(SIDECAR / 'actions.npy', mmap_mode='r'); valid = np.load(SIDECAR / 'horizon_valid_mask.npy', mmap_mode='r')
out = {}
for old in prev['selected_candidates']:
    ei = old['episode']; e = eps[ei]; sl = slice(e['row_start'], e['row_end']); q = np.asarray(states[sl]); t = np.asarray(times[sl])
    p = fk(q[:, :7]) * 1000; g = q[:, 7]
    close = int((c := np.flatnonzero((g[:-1] < .3) & (g[1:] >= .3)) + 1)[c > old['frame']][0])
    release = int((o := np.flatnonzero((g[:-1] >= .3) & (g[1:] < .3)) + 1)[o > close][0])
    lo = max(0, close - 8) + int(np.argmin(p[max(0, close - 8):min(release, close + 20), 2]))
    ids = np.arange(lo, release); start = int(ids[(p[ids, 2] >= p[lo, 2] + 10) & (g[ids] > .5)][0]); row = e['row_start'] + start
    raw = np.stack([np.interp(times[row] + np.arange(1, 16) / 15, t, q[:, k]) for k in range(8)], -1); al = np.asarray(actions[row])
    a = fk(np.vstack([q[start, :7], raw[:, :7]])) * 1000; b = fk(np.vstack([q[start, :7], al[:, :7]])) * 1000
    L = lambda x: float(np.linalg.norm(np.diff(x, axis=0), axis=1).sum())
    out[ei] = dict(raw15=L(a), aligned15=L(b), valid=bool(valid[row].all()), grip_min=float(min(raw[:, 7].min(), al[:, 7].min())),
                   raw_xyz=(a - a[0]).tolist(), aligned_xyz=(b - b[0]).tolist())
    print(f"ep {ei:3d}: raw15 {L(a):6.1f} mm  aligned15 {L(b):6.1f} mm  valid {valid[row].all()}  gripper min {out[ei]['grip_min']:.2f}")
json.dump(out, open('six_full15.json', 'w'))
