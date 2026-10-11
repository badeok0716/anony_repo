"""Engine-like tempo sound for the demo videos (user 2026-10-11: F1-style grand rev; previous thin/whiny tones, a dull
bass tone and a real V10 recording (noisy, speed change unclear) were all rejected).

Pure harmonic synthesis, no noise: 'rpm' s(t) = displayed speed-up with engine inertia (attack 0.12 s, release 0.30 s);
firing fundamental f0 = 62 Hz * s^1.25 (1x = 62 Hz, 2x = 148 Hz, 0.6x = 33 Hz); harmonics 1/n^0.85 shaped by two
body resonances and a brightness low-pass that opens with throttle (ds/dt > 0) and rpm; half-order lope for a V-engine
weight; soft tanh drive; slight stereo detune. After 'done' the engine spools down to idle and fades out.
Usage: python v27_engine_audio.py RATE_LOG.json VIDEO.mp4 OUT.mp4 [--rate-key r]"""
import sys, json, subprocess, argparse
import numpy as np

SR = 48000

def engine(rates, done, fps=30.0, base=62.0):
    n = int(len(rates) / fps * SR)
    tf = np.arange(len(rates)) / fps; ts = np.arange(n) / SR
    r = np.interp(ts, tf, rates); dn = np.interp(ts, tf, done.astype(float)) > 0.5
    # after done: spool down towards idle 0.85x over ~0.8 s
    if dn.any():
        i0 = np.argmax(dn); k = np.arange(n - i0) / SR
        r[i0:] = 0.85 + (r[i0] - 0.85) * np.exp(-k / 0.35)
    # engine inertia (one-pole, asymmetric)
    s = np.empty(n); s[0] = r[0]; up, dw = 1 - np.exp(-1 / (0.12 * SR)), 1 - np.exp(-1 / (0.30 * SR))
    for i in range(1, n):
        a = up if r[i] > s[i - 1] else dw; s[i] = s[i - 1] + a * (r[i] - s[i - 1])
    ds = np.gradient(s) * SR
    k_ = int(0.05 * SR); thr = np.convolve(np.clip(ds / 1.5, 0, 1), np.ones(k_) / k_, mode="same")   # throttle 0..1
    f0 = base * np.power(np.maximum(s, 0.3), 1.25)
    phase = 2 * np.pi * np.cumsum(f0) / SR
    fc = 700 + 1800 * thr + 650 * np.clip(s - 1, -0.5, 1.6)                      # brightness opens with throttle / rpm
    out = np.zeros((2, n))
    for ch, det in ((0, 1.0), (1, 1.004)):
        y = 0.35 * np.sin(0.5 * phase * det)                                     # half-order lope (V-engine weight)
        for h in range(1, 72):
            fh = h * f0
            if np.all(fh > 6000): break
            body = 1 + 0.9 * np.exp(-((fh - 320) / 140) ** 2) + 0.6 * np.exp(-((fh - 880) / 260) ** 2)
            amp = h ** -0.85 * body / (1 + (fh / fc) ** 4)
            y += amp * np.sin(h * phase * det + 0.37 * h * h)
        out[ch] = y
    level = np.clip(0.55 + 0.35 * thr + 0.18 * (s - 1), 0.35, 1.1)
    out = np.tanh(1.5 * out * level) 
    env = np.ones(n); fi = int(0.2 * SR); env[:fi] = np.linspace(0, 1, fi)
    if dn.any():
        i0 = np.argmax(dn); fo = min(n - i0, int(1.4 * SR)); env[i0:i0 + fo] *= np.linspace(1, 0, fo) ** 1.5; env[i0 + fo:] = 0
    out *= env
    return (out / (np.abs(out).max() + 1e-9) * 0.7).astype(np.float32)

def write_wav(path, x):
    import wave
    pcm = (np.clip(x.T, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("log"); ap.add_argument("video"); ap.add_argument("out")
    ap.add_argument("--rate-key", default="r"); ap.add_argument("--done-key", default="done")
    a = ap.parse_args()
    L = json.load(open(a.log)); fr = L["frames"]
    rates = np.array([f[a.rate_key] for f in fr], float); done = np.array([f[a.done_key] for f in fr], bool)
    x = engine(rates, done, L.get("fps", 30.0))
    wav = a.out.replace(".mp4", "_engine.wav"); write_wav(wav, x)
    import imageio_ffmpeg
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-y", "-i", a.video, "-i", wav, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", a.out], check=True)
    print("wrote", a.out, f"{len(rates) / L.get('fps', 30.0):.2f} s", flush=True)
