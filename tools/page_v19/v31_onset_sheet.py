"""Contact sheets of the first seconds of every ladder clip (frame index labels) + frame-difference energy, to set
motion-onset trims by eye. Usage: python v31_onset_sheet.py TASK"""
import sys, numpy as np, cv2
from v30_baseline_ladder import TASKS, sdr_frames, FPS
task = sys.argv[1]; cfg = TASKS[task]; W, H = (176, 313) if cfg["portrait"] else (316, 178)
OUT = "/storage/always216/ROBOT/tempo_viz_20261004/onset_check"
for j, pn in enumerate(cfg["panels"]):
    fr = sdr_frames(pn["path"], W, H, pn.get("cx", 0.5), pn.get("crop_aspect"), 0)
    g = [cv2.cvtColor(f, cv2.COLOR_RGB2GRAY).astype(np.float32) for f in fr[:150]]
    e = [float(np.abs(g[i + 1] - g[i]).mean()) for i in range(len(g) - 1)]
    print(j, pn["title"], "n", len(fr), "energy[0:120:3]", [round(x, 1) for x in e[0:120:3]], flush=True)
    idx = list(range(0, min(len(fr), 120), 3)); cols = 10
    rows = [np.hstack([cv2.putText(fr[i].copy(), str(i), (4, 18), 0, 0.6, (255, 255, 0), 2) if i < len(fr) else np.zeros_like(fr[0])
                       for i in idx[r * cols:(r + 1) * cols] + [10**9] * (cols - len(idx[r * cols:(r + 1) * cols]))]) for r in range((len(idx) + cols - 1) // cols)]
    cv2.imwrite(f"{OUT}/{task}_{j}.jpg", cv2.cvtColor(np.vstack(rows), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 80])
