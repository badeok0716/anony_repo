"""Ferrari F355, one simple rule (user 2026-10-14: no heuristics; speeding up = acceleration sound, slowing down = deceleration
sound; the fade-out must sound like the engine winding down, not revving up again).

Source: Freesound #43484 "ferrari355underhood4.mp3" by enginemusic, CC BY 3.0 (attribution required). Used as recorded,
only its slow rev-up at 2-7 s (rpm ratio 1.02 -> 1.37 of the 0.6-1.9 s idle); the 7 s drop (air-release hiss) is not used.

Engine rpm ratio rho(t) follows the executed speed-up with engine inertia: rho = 1 + 0.5 * (speed-up - 1) / 0.9 (above the recording's 1.37 the read speed adds the rest); after 'done'
it winds down to 0.7 (below idle) while the sound fades. The recording is read at speed v = rho(t) / rho_rec(p), where
rho_rec(p) is the rpm the recording has at read position p: the output always has the target rpm, rising pulls run through the
real rev-up (acceleration), and a falling target slows the read speed so the pitch drops (deceleration). When the recording
drifts too far from the target (ratio outside 0.82-1.2, or the end of the rev-up), the read position moves to the matching
point with a 0.15 s crossfade. Loudness: a little up while accelerating, a little down while decelerating.
Usage: python v45_f355_rpm.py RATE_LOG.json VIDEO.mp4 OUT.mp4"""
import json, subprocess, argparse, wave
import numpy as np
from scipy import ndimage
from rpm_shift_track import track_ratio

SR = 48000
FF = "/storage/always216/ROBOT/tempo_viz_20261004/pylib/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2"
SRC = "/storage/always216/ROBOT/tempo_viz_20261004/engine_cc0/cc0_43484.wav"
RISE = (2.0, 7.0)
B = 480                       # 10 ms control blocks
XF = int(0.15 * SR)


def read_wav(path):
    w = wave.open(path); return np.frombuffer(w.readframes(w.getnframes()), "<i2").reshape(-1, w.getnchannels()).astype(float).T / 32767


def inertia(r, up_s, down_s):
    s = np.empty_like(r); prev = r[0]; up, dw = 1 - np.exp(-B / (up_s * SR)), 1 - np.exp(-B / (down_s * SR))
    for i in range(len(r)):
        prev += (up if r[i] > prev else dw) * (r[i] - prev); s[i] = prev
    return s


def render(rates, done, fps):
    x = read_wav(SRC); N = x.shape[1]
    t_tr, rt, _ = track_ratio(x.mean(0), 1.25)
    rho_rec = np.interp(np.arange(N) / SR, t_tr, rt / np.median(rt[(t_tr > 0.6) & (t_tr < 1.9)]))
    a, b = int(RISE[0] * SR), int(RISE[1] * SR)
    curve = np.maximum.accumulate(rho_rec[a:b]); rho_rec[a:b] = curve; top = curve[-1]; end = b - int(0.3 * SR)

    n = int(len(rates) / fps * SR); nb = n // B + 1
    tb = np.arange(nb) * B / SR; tf = np.arange(len(rates)) / fps
    r = np.interp(tb, tf, rates); dn = np.interp(tb, tf, done.astype(float)) > 0.5
    rho = 1 + 0.5 * np.clip((inertia(r, 0.20, 0.25) - 1) / 0.9, 0, 1)        # speed-up +90% -> 1.5x idle rpm
    ramp = np.clip(tb / 1.5, 0, 1); ramp = ramp * ramp * (3 - 2 * ramp)   # gradual start from the bottom of the rev-up (1.5 s)
    rho = curve[0] + (rho - curve[0]) * ramp
    if dn.any():                                                    # wind down below idle after completion
        i0 = int(np.argmax(dn)); k = tb[i0:] - tb[i0]; rho[i0:] = 0.7 + (rho[i0] - 0.7) * np.exp(-k / 0.8)
    rho = ndimage.uniform_filter1d(rho, 5)
    drho = ndimage.uniform_filter1d(np.gradient(rho) / (B / SR), 10)
    gain = 1 + 0.35 * np.clip(drho / 0.4, 0, 1) - 0.25 * np.clip(-drho / 0.4, 0, 1)

    match = lambda val: a + int(np.clip(np.searchsorted(curve, min(val, top - 1e-3)), 0, end - a))
    y = np.zeros((2, n + 2 * XF)); p = float(a); pending = None; jumps = 0
    for k in range(nb):
        o = k * B
        if o >= n: break
        here = rho_rec[int(min(p, N - 2))]; v = float(np.clip(rho[k] / here, 0.55, 1.7))
        ratio = here / rho[k]
        hi = 1.45 if (drho[k] < -0.05 or dn[k]) else 1.2                # decelerating: let the read speed drop (pitch falls), no move
        lo = 0.82
        if (p >= end or ratio > hi or (ratio < lo and rho[k] <= top)) and not (dn[k] and p < end):
            q = float(match(rho[k]))
            if abs(q - p) > 0.05 * SR:
                jumps += 1; L = XF; idx = p + np.arange(L) * v; i0 = np.clip(idx.astype(int), 0, N - 2); fr = idx - i0
                y[:, o:o + L] += (x[:, i0] * (1 - fr) + x[:, i0 + 1] * fr) * np.sin(np.linspace(np.pi / 2, 0, L)) ** 2 * gain[k]
                p = q; here = rho_rec[int(p)]; v = float(np.clip(rho[k] / here, 0.55, 1.7)); pending = np.sin(np.linspace(0, np.pi / 2, L)) ** 2
        idx = p + np.arange(B) * v; i0 = np.clip(idx.astype(int), 0, N - 2); fr = idx - i0
        blk = (x[:, i0] * (1 - fr) + x[:, i0 + 1] * fr) * gain[k]
        if pending is not None:
            m = min(B, len(pending)); blk[:, :m] *= pending[:m]; pending = pending[B:] if len(pending) > B else None
        y[:, o:o + B] += blk; p += B * v
    y = y[:, :n]
    env = np.ones(n); env[:int(0.03 * SR)] = np.linspace(0, 1, int(0.03 * SR))
    if dn.any():
        i0 = int(np.argmax(dn) * B); fo = min(n - i0, int(2.2 * SR)); env[i0:i0 + fo] *= np.linspace(1, 0, fo) ** 1.3; env[i0 + fo:] = 0
    y *= env
    print(f"f355 rpm: rev-up rho {curve[0]:.2f}-{top:.2f}; position moves {jumps} ({jumps / (n / SR):.2f}/s)", flush=True)
    return (y / (np.abs(y).max() + 1e-9) * 0.85).astype(np.float32), rho, gain


def write_wav(path, x):
    pcm = (np.clip(x.T, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("log"); ap.add_argument("video"); ap.add_argument("out")
    a_ = ap.parse_args()
    Lg = json.load(open(a_.log)); fr = Lg["frames"]; fps = Lg.get("fps", 30.0)
    rates = np.array([f["r"] for f in fr], float); done = np.array([f["done"] for f in fr], bool)
    hms = subprocess.run([FF, "-i", a_.video], capture_output=True, text=True).stderr.split("Duration: ")[1].split(",")[0].split(":")
    nv = int(round((3600 * float(hms[0]) + 60 * float(hms[1]) + float(hms[2])) * fps))
    if nv > len(rates): rates = np.r_[rates, np.full(nv - len(rates), rates[-1])]; done = np.r_[done, np.full(nv - len(done), done[-1])]
    y, rho, gain = render(rates, done, fps)
    wav = a_.out.replace(".mp4", ".wav"); write_wav(wav, y)
    np.savez(a_.out.replace(".mp4", "_rpm.npz"), rho=rho, gain=gain, rate=np.interp(np.arange(len(rho)) * B / SR, np.arange(len(rates)) / fps, rates))
    subprocess.run([FF, "-v", "error", "-y", "-i", a_.video, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", "-movflags", "+faststart", a_.out], check=True)
    print("wrote", a_.out, flush=True)
