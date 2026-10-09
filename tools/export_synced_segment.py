"""Export one measured motion segment and video frames on the v18/v20 clocks.

Alternative quantiles replay the same footage, not independent robot rollouts.
"""
import argparse
import json
import sys
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--analysis-dir', required=True)
p.add_argument('--stem', required=True)
p.add_argument('--video', required=True)
p.add_argument('--camera', required=True)
p.add_argument('--out', default='static/data/segment.json')
a = p.parse_args()
sys.path.insert(0, a.analysis_dir)
import cv2
import numpy as np
import pandas as pd
from v01_tempo_clock import tempo_clock
from v04_fk import fk

lag = json.loads(Path(a.camera).read_text())['lag_s']
t, applied, _, _, model99 = tempo_clock(a.stem, col=2, return_model=True)
models = [tempo_clock(a.stem, col=c, return_model=True)[4] for c in (0, 1)] + [model99]
# A visible first-approach segment, entirely within recorded footage.
clip = np.linspace(0, 1, 121)
logt = clip + lag
r99 = np.interp(logt, t, applied)
model = [np.interp(logt, t, v) for v in models]
capped = r99 < model[2] - 1e-6
rates = [np.ones_like(clip)] + [np.where(capped, np.minimum(m, r99), m) for m in model[:2]] + [r99]
clocks = {}
for name, rate in zip(('q50', 'q90', 'q95', 'q99'), rates):
    ratio = r99 / np.maximum(rate, 1e-3)
    clocks[name] = np.r_[0, np.cumsum(np.diff(clip) * ratio[1:])].tolist()
steps = pd.read_csv(a.stem + '_steps.csv')
q = np.stack([np.interp(logt, steps.t, steps[f'q{i}']) for i in range(1, 8)], axis=1)
xyz = fk(q)
# Decode only one second; a compact atlas avoids asynchronous browser seeks.
cap = cv2.VideoCapture(a.video)
fps = cap.get(cv2.CAP_PROP_FPS)
assert abs(fps - 30) < .1, fps
w, h, columns, count = 180, 300, 8, 31
atlas = np.full((4*h, columns*w, 3), 255, np.uint8)
for i in range(count):
    ok, frame = cap.read()
    assert ok, i
    scale = min(w/frame.shape[1], h/frame.shape[0])
    frame = cv2.resize(frame, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    y, x = (i//columns)*h+(h-frame.shape[0])//2, (i%columns)*w+(w-frame.shape[1])//2
    atlas[y:y+frame.shape[0], x:x+frame.shape[1]] = frame
cap.release()
image_path = Path('static/tempo/chunk_atlas.jpg')
assert cv2.imwrite(str(image_path), atlas, [cv2.IMWRITE_JPEG_QUALITY, 90])
result = dict(source_rollout=Path(a.stem).name, clip_time=clip.tolist(), xyz=xyz.tolist(), clocks=clocks,
              atlas=dict(src=str(image_path), width=w, height=h, columns=columns, count=count, fps=fps),
              semantics='Same measured first-approach segment and footage; v20 counterfactual clocks, not separate physical executions. q50 is nominal 15 Hz.',
              video_lag_s=lag)
Path(a.out).write_text(json.dumps(result, separators=(',', ':'))+'\n')
print({k: v[-1] for k, v in clocks.items()})
