"""Two candidate sound tracks for the inference-time split videos (user 2026-10-12: the v27 harmonic engine sounded cheap).

  --mode supercar : V10-style supercar engine. A firing-pulse train (10 pulses per 2 crank revolutions, fixed per-cylinder
                    amplitude/timing irregularity -> the 'engine orders' that make a real engine sound rich) through
                    exhaust resonators, soft saturation and a throttle-dependent low-pass; rpm follows the executed speed-up
                    (1x = 2600 rpm, +50% = 5000 rpm, 2x = 7600 rpm) with engine inertia; overrun crackle when the speed
                    drops fast; rev-down and fade after 'done'. No broadband noise floor (only pulse-synchronous texture).
  --mode clock    : Zilean-style time effect. Left channel: a low wooden 'tock' every 3 actions of the fixed clock
                    (1 action / (1/15 s) = 5 tocks/s). Right channel: a bright clock 'tick' every 3 executed actions of Ours
                    (5 x speed-up per s), pitched up with speed, over a faint shimmer that rises with the speed-up. When Ours
                    runs slower than the fixed clock, a descending 'time-warp' swoosh plays. A chime marks Ours' completion.
Usage: python v33_tempo_audio.py RATE_LOG.json VIDEO.mp4 OUT.mp4 --mode supercar|clock"""
import sys, json, subprocess, argparse, wave
import numpy as np
from scipy import signal

SR = 48000
FF = "/storage/always216/ROBOT/tempo_viz_20261004/pylib/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2"
rng = np.random.default_rng(7)


def per_sample(rates, done, fps):
    n = int(len(rates) / fps * SR); tf = np.arange(len(rates)) / fps; ts = np.arange(n) / SR
    return n, np.interp(ts, tf, rates), np.interp(ts, tf, done.astype(float)) > 0.5


def inertia(r, up_s, down_s):
    s = np.empty_like(r); s[0] = r[0]; up, dw = 1 - np.exp(-1 / (up_s * SR)), 1 - np.exp(-1 / (down_s * SR))
    # vectorised one-pole with asymmetric time constants: run in blocks of 64 samples (fast enough, smooth enough)
    B = 64
    for i in range(0, len(r), B):
        prev = s[i - 1] if i else r[0]
        tgt = r[i:i + B].mean(); a = up if tgt > prev else dw
        k = np.arange(1, min(B, len(r) - i) + 1)
        s[i:i + B] = tgt + (prev - tgt) * (1 - a) ** k
    return s


def resonator(x, f, q):
    b, a = signal.iirpeak(f / (SR / 2), q); return signal.lfilter(b, a, x)


def supercar(rates, done, fps):
    n, r, dn = per_sample(rates, done, fps)
    if dn.any():                                                   # after done: back to idle (0.75x) quickly
        i0 = np.argmax(dn); k = np.arange(n - i0) / SR; r[i0:] = 0.75 + (r[i0] - 0.75) * np.exp(-k / 0.5)
    s = inertia(r, 0.10, 0.28)
    rpm = np.clip(2600 * s ** 1.6, 1500, 8800)
    ds = np.gradient(s) * SR
    thr = np.clip(0.35 + ds / 1.2, 0, 1)                           # throttle: opens when speeding up
    thr = signal.lfilter([0.002], [1, -0.998], thr) / 1.0
    # firing pulses: cycle phase (1 cycle = 2 revolutions = 10 firings)
    cyc = np.cumsum(rpm / 120.0) / SR
    amp = np.array([1.0, 0.86, 1.08, 0.93, 1.12, 0.9, 1.04, 0.84, 1.1, 0.95])
    off = np.array([0, .011, -.006, .014, -.01, .004, -.013, .008, -.004, .012])
    x = np.zeros(n)
    k0, k1 = int(np.floor(cyc[0] * 10)), int(np.floor(cyc[-1] * 10))
    pulse = np.hanning(int(0.0016 * SR)) ** 2                       # ~1.6 ms exhaust pulse
    for k in range(k0 + 1, k1 + 1):
        c = k // 10; j = k % 10
        tpos = (c + (j + off[j] * 10) / 10.0)
        i = int(np.searchsorted(cyc, tpos))
        if i + len(pulse) >= n: break
        x[i:i + len(pulse)] += amp[j] * pulse * (0.9 + 0.2 * rng.random())
    x -= signal.lfilter([1], [1, -0.9995], x) * (1 - 0.9995)        # remove DC drift
    # exhaust / body resonances (big bore, long pipes) + induction howl
    y = (1.0 * resonator(x, 95, 1.6) + 0.9 * resonator(x, 210, 2.2) + 0.7 * resonator(x, 430, 3.0)
         + 0.45 * resonator(x, 860, 4.0) + 0.25 * resonator(x, 1700, 5.0) + 0.6 * x)
    # throttle-dependent brightness: blend a low-passed and the full signal
    lo = signal.sosfilt(signal.butter(4, 900 / (SR / 2), output="sos"), y)
    y = lo + (y - lo) * (0.25 + 0.75 * thr)
    y = np.tanh(2.2 * y / (np.percentile(np.abs(y), 99.5) + 1e-9)) # snarl
    # overrun crackle: sparse pops when the speed falls fast
    dec = np.clip(-ds / 1.5, 0, 1); pops = np.zeros(n)
    for i in np.flatnonzero(rng.random(n) < np.where(dec > 0.35, dec, 0) * 6 / SR):
        L = int(SR * (0.004 + 0.01 * rng.random())); e = np.exp(-np.arange(L) / (0.0018 * SR))
        if i + L < n: pops[i:i + L] += (rng.random(L) * 2 - 1) * e * (0.6 + 0.6 * rng.random())
    pops = signal.sosfilt(signal.butter(2, [300 / (SR / 2), 3500 / (SR / 2)], btype="band", output="sos"), pops)
    y = y + 0.8 * pops
    y = signal.sosfilt(signal.butter(2, 35 / (SR / 2), btype="high", output="sos"), y)   # no rumble below 35 Hz
    y = signal.sosfilt(signal.butter(4, 7000 / (SR / 2), output="sos"), y)              # no fizz above 7 kHz
    level = np.clip(0.55 + 0.3 * thr + 0.15 * (s - 1), 0.35, 1.0)
    y *= level
    env = np.ones(n); fi = int(0.25 * SR); env[:fi] = np.linspace(0, 1, fi) ** 2
    if dn.any():
        i0 = np.argmax(dn); fo = min(n - i0, int(1.6 * SR)); env[i0:i0 + fo] *= np.linspace(1, 0, fo) ** 1.6; env[i0 + fo:] = 0
    y *= env
    st = np.stack([y, np.roll(y, int(0.0004 * SR))])               # a touch of width
    return (st / (np.abs(st).max() + 1e-9) * 0.8).astype(np.float32)


def _click(f_list, decay, L, bright=1.0):
    t = np.arange(L) / SR; e = np.exp(-t / decay)
    z = sum(a * np.sin(2 * np.pi * f * t) for f, a in f_list) * e
    att = np.minimum(1, t / 0.0004); return z * att * bright


def clock(rates, done, fps):
    n, r, dn = per_sample(rates, done, fps)
    t_done = np.argmax(dn) / SR if dn.any() else None
    L, R = np.zeros(n), np.zeros(n)
    tock = _click([(520, 1.0), (1040, 0.35), (1560, 0.12)], 0.035, int(0.12 * SR))          # wooden, low
    # fixed clock: 15 actions/s -> a tock every 3 actions (5 per s), the whole video
    for i in (np.arange(0, n / SR, 3 / 15) * SR).astype(int):
        if i + len(tock) < n: L[i:i + len(tock)] += 0.55 * tock
    # Ours: executed actions = 15 * integral(rate); a tick every 3 actions, pitch rises with speed
    act = np.cumsum(np.where(dn, 0, r)) * 15 / SR
    for k in range(1, int(act[-1] / 3) + 1):
        i = int(np.searchsorted(act, 3 * k))
        if i >= n: break
        p = float(np.clip(r[i], 0.6, 2.2)) ** 0.5
        tk = _click([(2400 * p, 1.0), (3700 * p, 0.55), (5200 * p, 0.25)], 0.012, int(0.05 * SR))
        if i + len(tk) < n: R[i:i + len(tk)] += 0.7 * tk
    # shimmer that rises with the speed-up (soft, no noise)
    s = inertia(r, 0.15, 0.3); up = np.clip((s - 1) / 0.8, 0, 1) * (~dn)
    ph = 2 * np.pi * np.cumsum(660 * s ** 0.7) / SR
    shim = (np.sin(ph) + 0.5 * np.sin(2.01 * ph) + 0.25 * np.sin(3.02 * ph)) * 0.06 * up
    R += shim; L += 0.4 * shim
    # slowdown swoosh: when Ours runs slower than the fixed clock (rate < 0.97), a falling 'time-warp' tone
    slow = (r < 0.97) & (~dn); edges = np.flatnonzero(slow[1:] & ~slow[:-1]) + 1
    last = -SR
    for i in edges:
        if i - last < 0.6 * SR: continue
        last = i; Ls = int(0.55 * SR); t = np.arange(Ls) / SR
        f = 320 * np.exp(-t / 0.18) + 70; z = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.22) * np.minimum(1, t / 0.02)
        z += 0.5 * np.sin(2 * np.pi * np.cumsum(f * 1.5) / SR) * np.exp(-t / 0.15)
        if i + Ls < n: L[i:i + Ls] += 0.5 * z; R[i:i + Ls] += 0.5 * z
    # completion chime on Ours
    if t_done is not None:
        i = int(t_done * SR); Lc = int(1.2 * SR)
        ch = _click([(1318.5, 1.0), (1975.5, 0.6), (2637, 0.3)], 0.35, Lc)
        if i + Lc < n: R[i:i + Lc] += 0.5 * ch; L[i:i + Lc] += 0.25 * ch
    # fixed clock fades over the last 0.4 s of the video
    fo = int(0.4 * SR); env = np.ones(n); env[-fo:] = np.linspace(1, 0, fo); env[:int(0.05 * SR)] = np.linspace(0, 1, int(0.05 * SR))
    st = np.stack([L * env, R * env])
    # crossfeed so it still works on one speaker
    st = np.stack([0.8 * st[0] + 0.2 * st[1], 0.2 * st[0] + 0.8 * st[1]])
    st = signal.sosfilt(signal.butter(2, 60 / (SR / 2), btype="high", output="sos"), st, axis=1)
    return (st / (np.abs(st).max() + 1e-9) * 0.8).astype(np.float32)


def write_wav(path, x):
    pcm = (np.clip(x.T, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("log"); ap.add_argument("video"); ap.add_argument("out")
    ap.add_argument("--mode", choices=["supercar", "clock"], required=True)
    a = ap.parse_args()
    Lg = json.load(open(a.log)); fr = Lg["frames"]; fps = Lg.get("fps", 30.0)
    rates = np.array([f["r"] for f in fr], float); done = np.array([f["done"] for f in fr], bool)
    hms = subprocess.run([FF, "-i", a.video], capture_output=True, text=True).stderr.split("Duration: ")[1].split(",")[0].split(":")
    dur = 3600 * float(hms[0]) + 60 * float(hms[1]) + float(hms[2])
    nv = int(round(dur * fps))                                     # pad the log to the video length (hold the end)
    if nv > len(rates): rates = np.r_[rates, np.full(nv - len(rates), rates[-1])]; done = np.r_[done, np.full(nv - len(done), done[-1])]
    x = supercar(rates, done, fps) if a.mode == "supercar" else clock(rates, done, fps)
    wav = a.out.replace(".mp4", ".wav"); write_wav(wav, x)
    subprocess.run([FF, "-v", "error", "-y", "-i", a.video, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", "-movflags", "+faststart", a.out], check=True)
    print("wrote", a.out, a.mode, f"{len(rates) / fps:.2f} s", flush=True)
