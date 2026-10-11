"""Visible first-motion time of every panel in a rendered portrait ladder (frame-difference energy inside each panel)."""
import sys, subprocess, numpy as np, imageio_ffmpeg
FF = imageio_ffmpeg.get_ffmpeg_exe(); W, H, gap, head = 352, 626, 12, 40; CW = 4 * W + 5 * gap; CW += CW % 2; CH = H + head + gap; CH += CH % 2
raw = subprocess.run([FF, "-v", "error", "-i", sys.argv[1], "-t", "1.5", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, CH, CW).astype(np.float32)
for i in range(4):
    x = gap + i * (W + gap); p = fr[:, head + 60:head + H - 70, x:x + W]          # skip timer and badge
    e = np.abs(np.diff(p, axis=0)).mean((1, 2)); k = int(np.argmax(e > max(1.0, 4 * np.median(e[:3]) + 0.3)))
    print(f"panel {i}: first motion at {(k + 1) / 30:.2f} s  energy[0:45:3]={np.round(e[0:45:3], 1).tolist()}")
