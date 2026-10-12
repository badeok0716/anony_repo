"""Sound tracks for the inference-time split videos, round 3 (user 2026-10-12: synthesized engine sounded like a motorbike,
the clock ticks were grating).

  --mode engine   : a REAL recording, CC0: Freesound #585215 "Car Engine: Maserati GranTurismo Switch to Sport Mode and
                    Launch" by myeclecticself (4.7 L Ferrari-built V8). The steady idle (0.3-4.8 s) is denoised (spectral
                    subtraction against the per-bin noise floor, 30 Hz high-pass, 8 kHz low-pass), turned into a seamless
                    loop (0.4 s crossfade) and played as a varispeed 'tape': playback speed = pitch = engine speed, following
                    the executed speed-up with engine inertia (1x = recorded idle, +40% = 1.4x). Slightly louder and brighter
                    while speeding up. After 'done' the engine settles back and fades out.
  --mode musicbox : no clicks. A music-box (celesta-like) note on every 3 executed actions of Ours, walking a major
                    pentatonic pattern (never dissonant), pitched up a little with the speed-up, in the right channel; a
                    soft low marimba note once per second (= 15 actions at 1/15 s) in the left channel as the fixed clock.
                    Slower than 1/15 s -> the notes bend down with a soft low 'whoom'. A chord arpeggio marks completion.
                    Soft room reverb.
Usage: python v36_tempo_audio.py RATE_LOG.json VIDEO.mp4 OUT.mp4 --mode engine|musicbox"""
import json, subprocess, argparse, wave
import numpy as np
from scipy import signal

SR = 48000
FF = "/storage/always216/ROBOT/tempo_viz_20261004/pylib/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2"
SRC = "/storage/always216/ROBOT/tempo_viz_20261004/engine_cc0/cc0_585215.wav"
rng = np.random.default_rng(3)


def per_sample(rates, done, fps):
    n = int(len(rates) / fps * SR); tf = np.arange(len(rates)) / fps; ts = np.arange(n) / SR
    return n, np.interp(ts, tf, rates), np.interp(ts, tf, done.astype(float)) > 0.5


def inertia(r, up_s, down_s, B=64):
    s = np.empty_like(r); up, dw = 1 - np.exp(-1 / (up_s * SR)), 1 - np.exp(-1 / (down_s * SR)); prev = r[0]
    for i in range(0, len(r), B):
        tgt = r[i:i + B].mean(); a = up if tgt > prev else dw; k = np.arange(1, min(B, len(r) - i) + 1)
        s[i:i + B] = tgt + (prev - tgt) * (1 - a) ** k; prev = s[min(i + B, len(r)) - 1]
    return s


def read_wav(path):
    w = wave.open(path); x = np.frombuffer(w.readframes(w.getnframes()), "<i2").reshape(-1, w.getnchannels()).astype(float) / 32767
    return x.T


def denoise(x, t0, t1):
    """Spectral subtraction: noise floor per bin = 20th percentile of the magnitude over the whole clip."""
    out = []
    for ch in x:
        f, t, Z = signal.stft(ch, SR, nperseg=4096, noverlap=3072)
        M = np.abs(Z); floor = np.percentile(M, 20, axis=1, keepdims=True)
        G = np.clip(1 - 1.6 * floor / (M + 1e-12), 0.06, 1.0)
        G = signal.lfilter([0.5], [1, -0.5], G, axis=1)               # smooth the gain in time (no musical noise)
        _, y = signal.istft(Z * G, SR, nperseg=4096, noverlap=3072); out.append(y[:len(ch)])
    y = np.stack(out)
    y = signal.sosfiltfilt(signal.butter(4, 30 / (SR / 2), btype="high", output="sos"), y, axis=1)
    y = signal.sosfiltfilt(signal.butter(6, 8000 / (SR / 2), output="sos"), y, axis=1)
    return y[:, int(t0 * SR):int(t1 * SR)]


def make_loop(seg, xf=0.4):
    k = int(xf * SR); a = seg[:, :k]; body = seg[:, k:-k] if seg.shape[1] > 3 * k else seg[:, k:]
    tail = seg[:, -k:]; w = np.sin(np.linspace(0, np.pi / 2, k)) ** 2
    return np.concatenate([body, tail * (1 - w) + a * w], axis=1)       # end crossfades into the start


def engine(rates, done, fps):
    n, r, dn = per_sample(rates, done, fps)
    if dn.any():
        i0 = np.argmax(dn); k = np.arange(n - i0) / SR; r[i0:] = 0.95 + (r[i0] - 0.95) * np.exp(-k / 0.6)
    s = inertia(r, 0.12, 0.35)
    loop = make_loop(denoise(read_wav(SRC), 0.3, 4.8)); L = loop.shape[1]
    pos = np.cumsum(np.clip(s, 0.6, 2.2)) % L                        # varispeed read pointer (pitch = speed = rpm)
    i0 = np.floor(pos).astype(int); fr = pos - i0; i1 = (i0 + 1) % L
    y = loop[:, i0] * (1 - fr) + loop[:, i1] * fr
    ds = np.gradient(s) * SR; thr = np.clip(signal.lfilter([0.0005], [1, -0.9995], np.clip(ds, 0, None)) * 2.0, 0, 1)
    hi = y - signal.sosfilt(signal.butter(2, 1200 / (SR / 2), output="sos"), y, axis=1)
    y = y + 0.6 * thr * hi                                           # brighter while speeding up
    y *= (0.8 + 0.25 * thr + 0.12 * np.clip(s - 1, -0.3, 1))
    env = np.ones(n); fi = int(0.3 * SR); env[:fi] = np.linspace(0, 1, fi) ** 2
    if dn.any():
        i0 = np.argmax(dn); fo = min(n - i0, int(1.8 * SR)); env[i0:i0 + fo] *= np.linspace(1, 0, fo) ** 1.5; env[i0 + fo:] = 0
    y *= env
    y = np.tanh(1.2 * y / (np.percentile(np.abs(y), 99.7) + 1e-9)) * 0.8   # gentle limiter
    return (y / (np.abs(y).max() + 1e-9) * 0.8).astype(np.float32)


def note(f, L, kind):
    t = np.arange(L) / SR; att = np.minimum(1, t / 0.004)
    if kind == "box":       # music box / celesta: slightly inharmonic partials, the upper ones die fast
        z = (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.55) + 0.35 * np.sin(2 * np.pi * 2.0 * f * t) * np.exp(-t / 0.25)
             + 0.12 * np.sin(2 * np.pi * 5.4 * f * t) * np.exp(-t / 0.08))
    else:                   # marimba: warm, short, low
        z = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.35) + 0.25 * np.sin(2 * np.pi * 4.0 * f * t) * np.exp(-t / 0.05)
    return z * att


def reverb(x, rt=1.1, wet=0.22):
    L = int(rt * SR); t = np.arange(L) / SR
    ir = rng.standard_normal((2, L)) * np.exp(-6.9 * t / rt)
    ir = signal.sosfilt(signal.butter(2, 3500 / (SR / 2), output="sos"), ir, axis=1); ir /= np.sqrt((ir ** 2).sum(1, keepdims=True))
    w = np.stack([signal.fftconvolve(x[c], ir[c])[:x.shape[1]] for c in range(2)])
    return x * (1 - wet) + w * wet * 3.0


def musicbox(rates, done, fps):
    n, r, dn = per_sample(rates, done, fps)
    t_done = np.argmax(dn) / SR if dn.any() else None
    Lc, Rc = np.zeros(n), np.zeros(n)
    PENT = 523.25 * 2 ** (np.array([0, 2, 4, 7, 9, 12, 14, 16]) / 12)            # C major pentatonic, C5..E6
    PATTERN = [0, 2, 4, 5, 4, 2, 3, 1]
    act = np.cumsum(np.where(dn, 0, r)) * 15 / SR
    for k in range(1, int(act[-1] / 3) + 1):                                       # a note every 3 executed actions
        i = int(np.searchsorted(act, 3 * k))
        if i >= n: break
        rr = float(np.clip(r[i], 0.6, 2.2)); f = PENT[PATTERN[k % len(PATTERN)]] * rr ** 0.25
        z = note(f, int(0.9 * SR), "box") * (0.55 if rr >= 0.97 else 0.4)
        if i + len(z) < n: Rc[i:i + len(z)] += z
    for i in (np.arange(0, n / SR, 1.0) * SR).astype(int):                         # fixed clock: once per 15 actions
        z = note(130.81, int(0.6 * SR), "marimba") * 0.5
        if i + len(z) < n: Lc[i:i + len(z)] += z
    slow = (r < 0.97) & (~dn); edges = np.flatnonzero(slow[1:] & ~slow[:-1]) + 1; last = -SR
    for i in edges:                                                                # slower than 1/15 s: soft whoom
        if i - last < 0.8 * SR: continue
        last = i; Ls = int(0.7 * SR); t = np.arange(Ls) / SR
        f = 180 * np.exp(-t / 0.35) + 60
        z = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / t[-1]) * 0.35
        if i + Ls < n: Lc[i:i + Ls] += z; Rc[i:i + Ls] += z
    if t_done is not None:                                                         # completion: C-E-G-C arpeggio
        i = int(t_done * SR)
        for j, f in enumerate([523.25, 659.25, 783.99, 1046.5]):
            z = note(f, int(1.4 * SR), "box") * 0.5; s0 = i + j * int(0.07 * SR)
            if s0 + len(z) < n: Rc[s0:s0 + len(z)] += z; Lc[s0:s0 + len(z)] += 0.5 * z
    st = np.stack([0.75 * Lc + 0.25 * Rc, 0.25 * Lc + 0.75 * Rc])
    st = reverb(st)
    fo = int(0.5 * SR); env = np.ones(n); env[-fo:] = np.linspace(1, 0, fo); st *= env
    return (st / (np.abs(st).max() + 1e-9) * 0.75).astype(np.float32)


def write_wav(path, x):
    pcm = (np.clip(x.T, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("log"); ap.add_argument("video"); ap.add_argument("out")
    ap.add_argument("--mode", choices=["engine", "musicbox"], required=True)
    a = ap.parse_args()
    Lg = json.load(open(a.log)); fr = Lg["frames"]; fps = Lg.get("fps", 30.0)
    rates = np.array([f["r"] for f in fr], float); done = np.array([f["done"] for f in fr], bool)
    hms = subprocess.run([FF, "-i", a.video], capture_output=True, text=True).stderr.split("Duration: ")[1].split(",")[0].split(":")
    nv = int(round((3600 * float(hms[0]) + 60 * float(hms[1]) + float(hms[2])) * fps))
    if nv > len(rates): rates = np.r_[rates, np.full(nv - len(rates), rates[-1])]; done = np.r_[done, np.full(nv - len(done), done[-1])]
    x = engine(rates, done, fps) if a.mode == "engine" else musicbox(rates, done, fps)
    wav = a.out.replace(".mp4", ".wav"); write_wav(wav, x)
    subprocess.run([FF, "-v", "error", "-y", "-i", a.video, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", "-movflags", "+faststart", a.out], check=True)
    print("wrote", a.out, a.mode, f"{len(rates) / fps:.2f} s", flush=True)
