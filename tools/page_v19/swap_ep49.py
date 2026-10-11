"""Replace demo C (ep125, aligned 321 mm) by ep49 (aligned 310 mm; user 2026-10-12): wrist frame at the same anchor rule,
arrays for [164, 167, 49] from six_full15.json -> page_arrays.npz (same keys as ../output/plotted_arrays.npz)."""
import json, sys, numpy as np, cv2
sys.path.insert(0, '/home/always216/ROBOT/analysis/training_tempo_viz_20261011'); from build_training_figure import SIDECAR
six = json.load(open('six_full15.json')); eps = json.load(open(SIDECAR / 'episodes.json'))['episodes']
times = np.load(SIDECAR / 'source_times.npy', mmap_mode='r')
sel = [164, 167, 49]
np.savez('page_arrays.npz', raw_full_xyz_mm=np.array([six[str(e)]['raw_xyz'] for e in sel]),
         learned_q50_full_xyz_mm=np.array([six[str(e)]['aligned_xyz'] for e in sel]), episodes=np.array(sel), shown_prefix=15)
# wrist frame for ep49 at its anchor (the anchor row is recomputed exactly as in six_full15.py)
sys.path.insert(0, '/home/always216/ROBOT/analysis/tempo_viz_20261004'); from v04_fk import fk
prev = json.load(open('/home/always216/ROBOT/analysis/training_tempo_viz_20261011/output/manifest.json'))
states = np.load(SIDECAR / 'states.npy', mmap_mode='r')
old = [o for o in prev['selected_candidates'] if o['episode'] == 49][0]; e = eps[49]; sl = slice(e['row_start'], e['row_end'])
q = np.asarray(states[sl]); p = fk(q[:, :7]) * 1000; g = q[:, 7]
close = int((c := np.flatnonzero((g[:-1] < .3) & (g[1:] >= .3)) + 1)[c > old['frame']][0])
release = int((o := np.flatnonzero((g[:-1] >= .3) & (g[1:] < .3)) + 1)[o > close][0])
lo = max(0, close - 8) + int(np.argmin(p[max(0, close - 8):min(release, close + 20), 2]))
ids = np.arange(lo, release); start = int(ids[(p[ids, 2] >= p[lo, 2] + 10) & (g[ids] > .5)][0]); row = e['row_start'] + start
cap = cv2.VideoCapture(e['video_path']); sec = float(e['video_episode_start_s'] + times[row] - times[e['row_start']])
cap.set(cv2.CAP_PROP_POS_FRAMES, round(sec * cap.get(cv2.CAP_PROP_FPS))); ok, im = cap.read(); assert ok
cv2.imwrite('/home/always216/ROBOT/anony_repo_tempo_demo/static/tempo/train_obs_3.jpg', im, [cv2.IMWRITE_JPEG_QUALITY, 90])
print("ep49 frame", start, "row", row, "video", e['video_path'].split('/')[-1], f"{sec:.2f}s", im.shape)
