"""All 412 cup demos at the same post-grasp anchor rule (first grasp; first frame >= 10 mm above the local minimum with
closure > 0.5): raw and learned-q50 12-waypoint labels (flange FK), start pose. Writes all412.npz for triple search."""
import json, sys, numpy as np
sys.path.insert(0, '/home/always216/ROBOT/analysis/tempo_viz_20261004'); from v04_fk import fk, fk_pose
sys.path.insert(0, '/home/always216/ROBOT/analysis/training_tempo_viz_20261011'); from build_training_figure import SIDECAR
eps = json.load(open(SIDECAR / 'episodes.json'))['episodes']
states = np.load(SIDECAR / 'states.npy', mmap_mode='r'); times = np.load(SIDECAR / 'source_times.npy', mmap_mode='r')
actions = np.load(SIDECAR / 'actions.npy', mmap_mode='r'); valid = np.load(SIDECAR / 'horizon_valid_mask.npy', mmap_mode='r')
N = 12; keep = dict(ep=[], row=[], frame=[], raw=[], al=[], pose=[], gmin=[])
for ei, e in enumerate(eps):
    sl = slice(e['row_start'], e['row_end']); q = np.asarray(states[sl]); t = np.asarray(times[sl]); g = q[:, 7]
    try:
        close = int((np.flatnonzero((g[:-1] < .3) & (g[1:] >= .3)) + 1)[0])
        release = int((o := np.flatnonzero((g[:-1] >= .3) & (g[1:] < .3)) + 1)[o > close][0])
        p = fk(q[:, :7]) * 1000
        lo = max(0, close - 8) + int(np.argmin(p[max(0, close - 8):min(release, close + 20), 2]))
        ids = np.arange(lo, release); start = int(ids[(p[ids, 2] >= p[lo, 2] + 10) & (g[ids] > .5)][0])
    except IndexError:
        continue
    row = e['row_start'] + start
    if not valid[row].all() or times[row] + 15 / 15 > t[-1]: continue
    raw = np.stack([np.interp(times[row] + np.arange(1, 16) / 15, t, q[:, k]) for k in range(8)], -1); al = np.asarray(actions[row])
    a = fk(np.vstack([q[start, :7], raw[:N, :7]])) * 1000; b = fk(np.vstack([q[start, :7], al[:N, :7]])) * 1000
    keep['ep'].append(ei); keep['row'].append(row); keep['frame'].append(start); keep['raw'].append(a - a[0]); keep['al'].append(b - b[0])
    keep['pose'].append(fk_pose(q[start:start + 1, :7])[0]); keep['gmin'].append(min(raw[:N, 7].min(), al[:N, 7].min()))
np.savez('all412.npz', **{k: np.asarray(v) for k, v in keep.items()})
L = lambda x: np.linalg.norm(np.diff(x, axis=1), axis=2).sum(1)
r, l = L(np.asarray(keep['raw'])), L(np.asarray(keep['al']))
print(len(keep['ep']), "episodes; raw12 mm p5/50/95", np.percentile(r, [5, 50, 95]).round(0), "aligned12", np.percentile(l, [5, 50, 95]).round(0))
