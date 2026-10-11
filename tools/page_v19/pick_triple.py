"""Chosen triple from all412.npz (user 2026-10-12: larger raw spread, tight after alignment): ep371, ep304, ep9
(sorted by raw distance). Writes page_arrays.npz and the wrist frames at the anchors."""
import json, sys, numpy as np, cv2
sys.path.insert(0, '/home/always216/ROBOT/analysis/training_tempo_viz_20261011'); from build_training_figure import SIDECAR
eps = json.load(open(SIDECAR / 'episodes.json'))['episodes']; times = np.load(SIDECAR / 'source_times.npy', mmap_mode='r')
z = np.load('all412.npz'); sel = [371, 304, 9]
ii = [int(np.flatnonzero(z['ep'] == e)[0]) for e in sel]
np.savez('page_arrays.npz', raw_full_xyz_mm=z['raw'][ii], learned_q50_full_xyz_mm=z['al'][ii], episodes=np.array(sel), shown_prefix=12)
pos = z['pose'][ii, :3, 3] * 1000
print("pairwise start distance mm:", [round(float(np.linalg.norm(pos[a] - pos[b])), 1) for a, b in ((0, 1), (0, 2), (1, 2))])
for k, (e, i) in enumerate(zip(sel, ii)):
    E = eps[e]; row = int(z['row'][i]); cap = cv2.VideoCapture(E['video_path'])
    sec = float(E['video_episode_start_s'] + times[row] - times[E['row_start']])
    cap.set(cv2.CAP_PROP_POS_FRAMES, round(sec * cap.get(cv2.CAP_PROP_FPS))); ok, im = cap.read(); assert ok
    cv2.imwrite(f'/tmp/claude-1011/train_obs_new_{k + 1}.jpg', im, [cv2.IMWRITE_JPEG_QUALITY, 90])
    print(f"demo {'ABC'[k]}: ep{e} frame {int(z['frame'][i])} row {row} {E['source']['recording_id']}")
