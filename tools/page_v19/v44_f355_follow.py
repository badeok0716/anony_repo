"""Ferrari F355 sound that keeps the recording's slow pull (user 2026-10-14: the charm is how 3-7 s drags the rpm up slowly;
80 ms grains lost it). No grains, no denoising: the recording plays forward continuously at ~1x and only its read position
steers towards the rpm the dial calls for.

Source: Freesound #43484 "ferrari355underhood4.mp3" by enginemusic, CC BY 3.0 (attribution required).
  rise = 2.0-7.0 s (rpm ratio ~1.02 -> 1.37, a slow pull), fall = 7.0-7.6 s (the drop).
Target rpm ratio rho(t) = 1 + 0.37 * (speed-up - 1) / 0.9 with engine inertia. Read pointer, every 10 ms:
  in rise: p* = where the rise has rho(t). Speed v = clip(1 - 0.4 * (p - p*), 0.85, 1.15) (always forward, ~1x, so the pull is
           heard as recorded). Far ahead of p* (> 1.2 s, ~0.08 in rpm ratio): if the speed-up is dropping fast -> go to the fall at the same rpm,
           otherwise jump back to p* (80 ms crossfade; the sweep is slow, so the jump is barely audible). End of rise -> fall.
  in fall: play at 1x; when it reaches the target rpm while the speed-up rises again, or ends -> back to rise at p*.
Usage: python v43_f355_follow.py RATE_LOG.json VIDEO.mp4 OUT.mp4"""
import json, subprocess, argparse, wave
import numpy as np
from scipy import ndimage
from rpm_shift_track import track_ratio

SR = 48000
FF = "/storage/always216/ROBOT/tempo_viz_20261004/pylib/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2"
SRC = "/storage/always216/ROBOT/tempo_viz_20261004/engine_cc0/cc0_43484.wav"
RISE, FALL, REF = (2.0, 7.0), (7.0, 7.6), 1.25
B = 480                      # 10 ms control blocks
XF = int(0.08 * SR)
XF2 = int(0.15 * SR)         # jump crossfade (round 9)
LOOSE = False


def read_wav(path):
    w = wave.open(path); return np.frombuffer(w.readframes(w.getnframes()), "<i2").reshape(-1, w.getnchannels()).astype(float).T / 32767


def inertia(r, up_s, down_s):
    s = np.empty_like(r); prev = r[0]; up, dw = 1 - np.exp(-B / (up_s * SR)), 1 - np.exp(-B / (down_s * SR))
    for i in range(len(r)):
        prev += (up if r[i] > prev else dw) * (r[i] - prev); s[i] = prev
    return s


def follow(rates, done, fps):
    x = read_wav(SRC); N = x.shape[1]
    t_tr, rt, _ = track_ratio(x.mean(0), REF)
    rho_src = np.interp(np.arange(N) / SR, t_tr, rt / np.median(rt[(t_tr > 0.6) & (t_tr < 1.9)]))
    a, b = int(RISE[0] * SR), int(RISE[1] * SR); rise_rho = np.maximum.accumulate(rho_src[a:b])
    c, d = int(FALL[0] * SR), int(FALL[1] * SR); fall_rho = np.minimum.accumulate(np.minimum(rho_src[c:d], rise_rho[-1]))
    top = rise_rho[-1]

    n = int(len(rates) / fps * SR); nb = n // B + 1
    tb = np.arange(nb) * B / SR; tf = np.arange(len(rates)) / fps
    r = np.interp(tb, tf, rates); dn = np.interp(tb, tf, done.astype(float)) > 0.5
    if dn.any():
        i0 = np.argmax(dn); r[i0:] = 1.0 + (r[i0] - 1.0) * np.exp(-(tb[i0:] - tb[i0]) / 0.6)
    s = inertia(r, 0.35, 0.6)
    rho = 1 + (top - 1) * np.clip((s - 1) / 0.9, 0, 1)
    drho = np.gradient(rho) / (B / SR); drho = ndimage.uniform_filter1d(drho, 8)

    p_of = lambda curve, val, off: off + int(np.clip(np.searchsorted(curve, val), 0, len(curve) - 1))
    # round 9: no drop segment (its air-release hiss is gone); start at the bottom of the pull for every task (gradual, as in
    # trash); LOOSE = follow the dial more loosely so the recording runs on longer.
    thr_back, vmin, vmax, gain, quick = (3.0, 0.9, 1.1, 0.25, False) if LOOSE else (1.2, 0.85, 1.15, 0.4, True)
    y = np.zeros((2, n + 2 * XF2)); p = float(a); jumps = 0; pending = None
    for k in range(nb):
        o = k * B
        if o >= n: break
        target = p_of(rise_rho, rho[k], a); e = (p - target) / SR
        jump_to = None
        if p >= b - int(0.25 * SR) or (not dn[k] and (e > thr_back or (quick and e > 0.5 and drho[k] < -0.2))):   # never run into the drop
            jump_to = float(min(target, b - 2 * SR))                 # back down the pull, smoothly (no drop sound)
        v = float(np.clip(1 - gain * e, vmin, vmax))
        if jump_to is not None:
            jumps += 1; L = min(XF2, n + XF2 - o); idx = p + np.arange(L) * v; i0 = np.clip(idx.astype(int), 0, N - 2); fr = idx - i0
            y[:, o:o + L] += (x[:, i0] * (1 - fr) + x[:, i0 + 1] * fr) * np.sin(np.linspace(np.pi / 2, 0, L)) ** 2
            p = jump_to; pending = np.sin(np.linspace(0, np.pi / 2, L)) ** 2
        idx = p + np.arange(B) * v; i0 = np.clip(idx.astype(int), 0, N - 2); fr = idx - i0
        blk = x[:, i0] * (1 - fr) + x[:, i0 + 1] * fr
        if pending is not None:
            m = min(B, len(pending)); blk[:, :m] *= pending[:m]; pending = pending[B:] if len(pending) > B else None
        y[:, o:o + B] += blk; p += B * v
    y = y[:, :n]
    env = np.ones(n); env[:int(0.03 * SR)] = np.linspace(0, 1, int(0.03 * SR))
    if dn.any():
        i0 = int(np.argmax(dn) * B); fo = min(n - i0, int(2.0 * SR)); env[i0:i0 + fo] *= np.linspace(1, 0, fo) ** 1.5; env[i0 + fo:] = 0
    y *= env
    print(f"f355 follow{' (loose)' if LOOSE else ''}: rise rho {rise_rho[0]:.2f}-{top:.2f}; jumps {jumps} ({jumps / (n / SR):.2f}/s)", flush=True)
    return (y / (np.abs(y).max() + 1e-9) * 0.85).astype(np.float32)


def write_wav(path, x):
    pcm = (np.clip(x.T, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("log"); ap.add_argument("video"); ap.add_argument("out")
    ap.add_argument("--loose", action="store_true")
    a_ = ap.parse_args(); LOOSE = a_.loose
    Lg = json.load(open(a_.log)); fr = Lg["frames"]; fps = Lg.get("fps", 30.0)
    rates = np.array([f["r"] for f in fr], float); done = np.array([f["done"] for f in fr], bool)
    hms = subprocess.run([FF, "-i", a_.video], capture_output=True, text=True).stderr.split("Duration: ")[1].split(",")[0].split(":")
    nv = int(round((3600 * float(hms[0]) + 60 * float(hms[1]) + float(hms[2])) * fps))
    if nv > len(rates): rates = np.r_[rates, np.full(nv - len(rates), rates[-1])]; done = np.r_[done, np.full(nv - len(done), done[-1])]
    y = follow(rates, done, fps)
    wav = a_.out.replace(".mp4", ".wav"); write_wav(wav, y)
    subprocess.run([FF, "-v", "error", "-y", "-i", a_.video, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", "-movflags", "+faststart", a_.out], check=True)
    print("wrote", a_.out, flush=True)
