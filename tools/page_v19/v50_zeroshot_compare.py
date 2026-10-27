"""Zero-shot comparison videos (2026-10-27), in the page's existing banana format (white canvas 1932x726, two panels,
titles, timers, "1x REAL-TIME - NOT SPED UP" pill), from the exterior camera of 138-PC rollouts (robolab_v3 20261021/22).
Added like the fine-tuned ladders: a success counter per panel (operator success marks), a green "Done" timer when the run
completes (last success mark), an outcome badge when a clip ends. Clock = time since the policy start (ext video t=0 =
policy start: its length equals duration_s). Usage: python v50_zeroshot_compare.py TASK OUT.mp4"""
import sys, json, subprocess
import numpy as np, cv2
from PIL import Image, ImageDraw
sys.path.insert(0, "/home/always216/ROBOT/analysis/tempo_viz_20261004")
from v02_render import font
import imageio_ffmpeg
FF = imageio_ffmpeg.get_ffmpeg_exe(); FPS = 30
RAW = "/home/always216/ROBOT/analysis/zeroshot_20261027/raw/"
W, H = 1932, 726; PW, PH = 958, 539; GAP = 16; X0 = (W - 2 * PW - GAP) // 2; Y0 = 92
GREEN, RED, BLUE, GREY = (34, 160, 70), (220, 38, 38), (43, 63, 186), (90, 90, 96)
TASKS = {
    "banana": dict(total=2, timeout=30.0, unit="bananas", panels=[
        dict(title="Baseline (Default 1×)", col=GREY, ep="v3_20261022_103537"),
        dict(title="Ours (q99)", col=BLUE, ep="v3_20261022_085244")]),
    "cube": dict(total=9, timeout=60.0, unit="cubes", panels=[
        dict(title="Baseline (Default 1×)", col=GREY, ep="v3_20261021_095416"),
        dict(title="Ours (q99)", col=BLUE, ep="v3_20261021_105456")]),
}


def frames(path):
    p = subprocess.run([FF, "-v", "error", "-i", path, "-vf", f"fps={FPS},scale={PW}:{PH}:flags=bicubic", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       capture_output=True, check=True)
    return np.frombuffer(p.stdout, np.uint8).reshape(-1, PH, PW, 3)


def badge(d, cx, y, txt, col, f):
    tw = d.textlength(txt, font=f)
    d.rounded_rectangle((cx - tw / 2 - 14, y - 19, cx + tw / 2 + 14, y + 19), 9, fill=col + (240,))
    d.text((cx, y), txt, font=f, fill=(255, 255, 255), anchor="mm")


def main(task, out):
    cfg = TASKS[task]; clips, info = [], []
    for pn in cfg["panels"]:
        ep = json.load(open(RAW + pn["ep"] + "_episode.json"))
        marks = sorted(m["t_s"] for m in ep["marks"])
        fr = frames(RAW + pn["ep"] + "_exterior.mp4")
        n_lim = int(round(cfg["timeout"] * FPS)) + 1
        fr = fr[:n_lim]
        done = marks[-1] if len(marks) >= cfg["total"] else None
        timed_out = len(fr) >= n_lim - 1 and done is None
        clips.append(fr); info.append(dict(marks=marks, done=done, timed_out=timed_out))
        print(pn["ep"], f"{len(fr) / FPS:.2f} s, marks {[round(m, 1) for m in marks]}, done {done}, timeout {timed_out}", flush=True)
    n = max(len(c) for c in clips) + FPS
    proc = subprocess.Popen([FF, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    fT, fM, fB, fP = font("Bold", 30), font("mono", 26), font("Bold", 24), font("Bold", 22)
    for k in range(n):
        cv = Image.new("RGB", (W, H), (255, 255, 255)); d = ImageDraw.Draw(cv, "RGBA")
        for i, (pn, c, inf) in enumerate(zip(cfg["panels"], clips, info)):
            x = X0 + i * (PW + GAP); ended = k >= len(c); t = min(k, len(c) - 1) / FPS
            img = Image.fromarray(c[min(k, len(c) - 1)])
            if ended and inf["done"] is None: img = Image.blend(img, Image.new("RGB", img.size, (0, 0, 0)), 0.35)
            cv.paste(img, (x, Y0))
            d.text((x + PW / 2, 46), pn["title"], font=fT, fill=pn["col"], anchor="mm")
            done = inf["done"]
            if done is not None and t >= done:
                txt, fill = f"Done {done:.2f} s", GREEN + (235,)
            else:
                txt, fill = f"{t:5.1f} s", (20, 20, 24, 210)
            tw = d.textlength(txt, font=fM)
            d.rounded_rectangle((x + 12, Y0 + 12, x + 36 + tw, Y0 + 50), 8, fill=fill)
            d.text((x + 24, Y0 + 31), txt, font=fM, fill=(240, 240, 244), anchor="lm")
            ns = sum(1 for m in inf["marks"] if m <= t)                         # success counter
            ctr = f"{ns} / {cfg['total']} {cfg['unit']}"; cw = d.textlength(ctr, font=fB)
            d.rounded_rectangle((x + PW - 36 - cw, Y0 + 12, x + PW - 12, Y0 + 50), 8, fill=((GREEN if ns == cfg["total"] else (20, 20, 24)) + (225,)))
            d.text((x + PW - 24 - cw, Y0 + 31), ctr, font=fB, fill=(255, 255, 255), anchor="lm")
            if done is not None and t >= done:
                badge(d, x + PW / 2, Y0 + PH - 40, f"{cfg['total']} / {cfg['total']} · {done:.2f} s", GREEN, fB)
            elif ended:
                badge(d, x + PW / 2, Y0 + PH - 40, f"{ns} / {cfg['total']}" + (f" · {cfg['timeout']:g} s timeout" if inf["timed_out"] else ""), RED, fB)
        pill = "1× REAL-TIME · NOT SPED UP"; pw_ = d.textlength(pill, font=fP)
        d.rounded_rectangle((W / 2 - pw_ / 2 - 40, H - 52, W / 2 + pw_ / 2 + 20, H - 14), 10, fill=(32, 34, 40))
        d.ellipse((W / 2 - pw_ / 2 - 26, H - 39, W / 2 - pw_ / 2 - 14, H - 27), fill=RED)
        d.text((W / 2 - pw_ / 2, H - 33), pill, font=fP, fill=(255, 255, 255), anchor="lm")
        proc.stdin.write(np.asarray(cv).tobytes())
    proc.stdin.close(); proc.wait(); print("wrote", out, f"{n / FPS:.2f} s", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
