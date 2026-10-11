"""Baseline ladder videos for the demo page (2026-10-12): four real rollouts per task, started together, real time.
1 Default 1x + PD | 2 Default 1x + high-gain PD | 3 1x + our controller | 4 Ours + our controller.
Each panel: title, model/controller line, timer (stops when its clip ends), outcome badge; a clip that ends early holds
its last frame (dimmed). Usage: python v30_baseline_ladder.py TASK OUT.mp4"""
import sys, json, subprocess, os
import numpy as np, cv2
from PIL import Image, ImageDraw
from v02_render import font
import imageio_ffmpeg
FF = imageio_ffmpeg.get_ffmpeg_exe(); FPS = 30
O = "/storage/always216/ROBOT/tempo_viz_20261004"; DEMO = "/storage/always216/ROBOT/demo"; REP = O + "/drive/rep"
BG, FG, DIM = (16, 17, 24), (238, 238, 242), (160, 162, 175)
RED, GREEN, AMBER, BLUE = (220, 38, 38), (34, 160, 70), (217, 119, 6), (59, 130, 246)

# Per panel: title, path, cx (crop centre), crop_aspect (None = panel aspect), trim (start frame; None = detect onset),
# off (s added to the displayed timer: ours = rollout lag, i.e. time since the policy start), done (clip s after the trim
# when the task completes, paper rule: last cup / towel fold / paper ball released; None = no success), cut (clip s),
# end (badge shown at the clip end when there is no success).  Ours: done = v25 completion - lag (cup 3.162, towel 4.487,
# trash 48.26 s since policy start). Cup baselines without logs: last cup released, read off the video frames.
TASKS = {
 "cup": dict(portrait=True, panels=[
   dict(title="Default 1× + PD", path=REP + "/cup/cup(w／o control,tempo align).MOV", done=8.2),
   dict(title="Default 1× + high-gain PD", path=DEMO + "/Cup_demo/cup_raw_1x_high_gain_pd_failure.mov", end=("failure", RED)),
   dict(title="Default 1× + our controller", path=DEMO + "/Cup_demo/cup_raw_1x_control.mov", done=4.2),
   dict(title="Ours (q99) + our controller", path=O + "/orig/cup_sdr30.mp4", trim=0, off=0.264, done=3.162 - 0.264)]),
 "towel": dict(portrait=True, panels=[
   dict(title="Default 1× + PD", path=REP + "/towel/towel(w／o control, tempo align)", cx=0.30, crop_aspect=0.80, end=("failure", RED)),
   dict(title="Default 1× + high-gain PD", path=DEMO + "/Towel_demo/towel_raw_1x_high_gain_pd_j7error.MOV", end=("failure · stopped", RED)),
   dict(title="Default 1× + our controller", path=DEMO + "/Towel_demo/towel_raw_1x_failure.mov", cut=10.0, end=("failure · 10 s timeout", RED)),
   dict(title="Ours (q95) + our controller", path=O + "/orig/towel_30.mp4", trim=0, off=0.451, done=4.487 - 0.451)]),
 "trash": dict(portrait=False, panels=[
   dict(title="Default 1× + PD", path=REP + "/trash/trash(w／o control, tempo align)", trim=82, end=("0 / 15", RED)),
   dict(title="Default 1× + high-gain PD", path=DEMO + "/Trash_demo/trash_raw_1x_high_gain_pd_reflex_red_light.mov", end=("0 / 15 · reflex stop, red light", RED)),
   dict(title="Default 1× + our controller", path=DEMO + "/Trash_demo/trash_raw_1x_control.mov", end=("9 / 15", AMBER)),
   dict(title="Ours (q99) + our controller", path=O + "/drive/trash_ours.mp4", trim=80, off=0.128, done=48.26 - 0.128, done_text="15 / 15")]),
}

def onset(frames, k=3):
    """First frame where the arm starts moving: frame-difference energy above 3x the still-scene floor for k frames."""
    g = [cv2.resize(cv2.cvtColor(f, cv2.COLOR_RGB2GRAY), (96, 160 if f.shape[0] > f.shape[1] else 54)).astype(np.float32) for f in frames]
    e = np.array([np.abs(g[i + 1] - g[i]).mean() for i in range(len(g) - 1)])
    floor = np.median(e[:10]) if len(e) > 10 else e.min()
    thr = max(3 * floor, floor + 0.6)
    for i in range(len(e) - k):
        if np.all(e[i:i + k] > thr): return max(0, i - 1)
    return 0

def sdr_frames(path, W, H, cx, crop_aspect=None, trim=None):
    """Decode with ffmpeg (HLG -> SDR tonemap if needed, autorotate), centre-crop to W:H around relative x cx, resize."""
    info = subprocess.run([FF, "-hide_banner", "-i", path], capture_output=True, text=True).stderr
    vf = "zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=mobius:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p," if "arib-std-b67" in info else ""
    vf += f"fps={FPS},scale=-2:{H * 2}"
    p = subprocess.run([FF, "-v", "error", "-i", path, "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
    import re
    m = re.findall(r", (\d{3,4})x(\d{3,4})", info)
    # probe decoded size from the byte count
    hh = H * 2; n_px = len(p.stdout) // 3
    # decoded width: find w such that n_px % (w*hh) == 0 using the aspect of the first video stream
    w0, h0 = int(m[0][0]), int(m[0][1])
    if "rotation of -90" in info or "rotation of 90" in info: w0, h0 = h0, w0
    ww = int(round(w0 * hh / h0 / 2)) * 2
    fr = np.frombuffer(p.stdout, np.uint8).reshape(-1, hh, ww, 3)
    ca = crop_aspect or W / H
    tw = min(ww, int(round(hh * ca)))                          # crop width at decoded height
    x0 = int(np.clip(cx * ww - tw / 2, 0, max(0, ww - tw)))
    if crop_aspect is None:
        out = [cv2.resize(f[:, x0:x0 + tw], (W, H), interpolation=cv2.INTER_AREA) for f in fr]
    else:                                                      # zoom out: fit the wider crop to the panel width, pad
        h2 = int(round(W / ca)); pad = (H - h2) // 2
        out = []
        for f in fr:
            c = np.full((H, W, 3), 16, np.uint8); c[pad:pad + h2] = cv2.resize(f[:, x0:x0 + tw], (W, h2), interpolation=cv2.INTER_AREA); out.append(c)
    k0 = onset(out) if trim is None else trim   # trash: handheld shake fools the detector -> frames set by eye/log
    print(f"  {os.path.basename(path)}: onset frame {k0} ({k0 / FPS:.2f} s) of {len(out)}", flush=True)
    return out[k0:]

def main(task, out):
    cfg = TASKS[task]; portrait = cfg["portrait"]
    W, H = (352, 626) if portrait else (632, 356)
    clips = []
    for pn in cfg["panels"]:
        c = sdr_frames(pn["path"], W, H, pn.get("cx", 0.5), pn.get("crop_aspect"), pn.get("trim"))
        if pn.get("cut"): c = c[:int(round(pn["cut"] * FPS)) + 1]
        clips.append(c)
    n = max(len(c) for c in clips) + FPS                         # +1 s hold
    head, gap = 40, 12
    if portrait: CW, CH = 4 * W + 5 * gap, H + head + gap; pos = [(gap + i * (W + gap), head) for i in range(4)]
    else: CW, CH = 2 * W + 3 * gap, 2 * (H + head) + 2 * gap; pos = [(gap + (i % 2) * (W + gap), head + (i // 2) * (H + head + gap)) for i in range(4)]
    CW += CW % 2; CH += CH % 2
    p = subprocess.Popen([FF, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{CW}x{CH}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    fb = font("Bold", 22)
    def bottom(d, x, y, txt, col):
        tw = d.textlength(txt, font=fb)
        d.rounded_rectangle((x + W / 2 - tw / 2 - 14, y + H - 54, x + W / 2 + tw / 2 + 14, y + H - 16), 9, fill=col + (240,))
        d.text((x + W / 2, y + H - 35), txt, font=fb, fill=(255, 255, 255), anchor="mm")
    for k in range(n):
        cv = Image.new("RGB", (CW, CH), BG); d = ImageDraw.Draw(cv, "RGBA")
        for i, (pn, c, (x, y)) in enumerate(zip(cfg["panels"], clips, pos)):
            ended = k >= len(c); f = c[min(k, len(c) - 1)]
            img = Image.fromarray(f)
            if ended and not pn.get("done"): img = Image.blend(img, Image.new("RGB", img.size, (0, 0, 0)), 0.35)
            cv.paste(img, (x, y))
            d.text((x, y - 30), pn["title"], font=font("Bold", 20), fill=(245, 197, 66) if i == 3 else FG)
            t = min(k, len(c) - 1) / FPS; off = pn.get("off", 0.0); done = pn.get("done")
            if done is not None and t >= done:                     # completion: timer turns green and stops
                txt = f"Done {done + off:.2f} s"; fill = GREEN + (235,)
            else:
                txt = f"{t + off:5.1f} s"; fill = (20, 20, 24, 210)
            tw = d.textlength(txt, font=font("mono", 18))
            d.rounded_rectangle((x + 8, y + 8, x + 24 + tw, y + 38), 7, fill=fill)
            d.text((x + 16, y + 23), txt, font=font("mono", 18), fill=FG, anchor="lm")
            if done is not None and t >= done:
                bottom(d, x, y, f"{pn.get('done_text', 'success')} · {done + off:.2f} s", GREEN)
            elif ended and pn.get("end"):
                bottom(d, x, y, *pn["end"])
        p.stdin.write(np.asarray(cv).tobytes())
    p.stdin.close(); p.wait(); print("wrote", out, n / FPS, "s", [len(c) / FPS for c in clips], flush=True)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
