"""Rev-synced engine sound for the split videos (user 2026-10-14: keep the Huracan recording; instead of raising the pitch,
make the real rev-up coincide with the speed-up rising and the real rev-down with it falling).

Source: Freesound #564373 "Lambo Start Up Sound" by JaimeLopes (Lamborghini Huracan EVO Spyder V10), CC0.
The recording's own rpm is tracked (harmonic comb on the STFT, firing fundamental ~70 Hz at idle, ~104 Hz at the start-up
peak), giving three real-sound layers:
  rise  = the start-up rev-up (1.15-1.55 s): engine under throttle, rpm going up
  fall  = the rev-down after it (1.60-2.90 s): throttle off, rpm coming down
  idle  = the settled idle (3.2-19.5 s), looped
Target rpm ratio rho(t) = 1 + 0.5 * (speed-up - 1) / 0.9 (speed-up 1.0 -> idle, 1.9 -> the recorded peak), with engine
inertia. Every 20 ms an 80 ms grain is taken from the rise layer (rho going up) or the fall layer (rho coming down) at the
point where the recording has the same rpm, resampled only by the small leftover ratio; when rho is steady the idle loop
plays at rho (a held rpm). Layers crossfade by |d rho / dt|, so the audible rev-ups and rev-downs line up with the dial.
Usage: python v40_rev_sync_audio.py RATE_LOG.json VIDEO.mp4 OUT.mp4"""
import json, subprocess, argparse, wave
import numpy as np
from scipy import signal, ndimage

SR = 48000
FF = "/storage/always216/ROBOT/tempo_viz_20261004/pylib/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2"
E = "/storage/always216/ROBOT/tempo_viz_20261004/engine_cc0/"
# round 8 (2026-10-14): raw recordings, only cut and resequenced (user: denoising made it muffled); Ferrari smoother.
# round 7: only clean parts. Huracan: start-up only (voices/birds/children appear from ~4.3 s on).
# Ferrari 355 (user: 3-7 s accelerates nicely, then drops at 7 s): rise 2-7 s, fall 7.0-7.6 s, steady low 0.6-1.9 s.
SOURCES = {
    "huracan": dict(src=E + "cc0_564373.wav", rise=(1.15, 1.55), fall=(1.60, 2.90), idle=(3.0, 4.2), tracker="comb",
                    idle_lp=None, rho_top=1.5, inertia=(0.10, 0.25), dthr=0.35, xfade=0.04, credit="Freesound #564373 'Lambo Start Up Sound' by JaimeLopes, CC0"),
    "f355": dict(src=E + "cc0_43484.wav", rise=(2.0, 7.0), fall=(7.0, 7.6), idle=(0.6, 1.9), tracker="shift",
                 idle_lp=None, rho_top=1.3, inertia=(0.45, 0.8), dthr=0.25, xfade=0.25, credit="Freesound #43484 'ferrari355underhood4.mp3' by enginemusic, CC BY 3.0"),
}
G, HOP = 3840, 960                                 # 80 ms grains, 20 ms hop (4x overlap)
rng = np.random.default_rng(11)


def read_wav(path):
    w = wave.open(path); x = np.frombuffer(w.readframes(w.getnframes()), "<i2").reshape(-1, w.getnchannels()).astype(float) / 32767
    return x.T


def denoise(x):
    out = []
    for ch in x:
        f, t, Z = signal.stft(ch, SR, nperseg=4096, noverlap=3072)
        M = np.abs(Z); floor = np.percentile(M, 20, axis=1, keepdims=True)
        Gn = signal.lfilter([0.5], [1, -0.5], np.clip(1 - 1.6 * floor / (M + 1e-12), 0.06, 1.0), axis=1)
        _, y = signal.istft(Z * Gn, SR, nperseg=4096, noverlap=3072); out.append(y[:len(ch)])
    return signal.sosfiltfilt(signal.butter(4, 30 / (SR / 2), btype="high", output="sos"), np.stack(out), axis=1)


def track_f0(x, lo, hi):
    """Firing fundamental per 10 ms (harmonic comb, 8 harmonics), median-smoothed."""
    m = x.mean(0); f, t, Z = signal.stft(m, SR, nperseg=8192, noverlap=8192 - 480)
    L = np.log(np.abs(Z) + 1e-6); df = f[1] - f[0]; cands = np.arange(lo, hi, 0.5)
    sc = np.stack([L[np.round(np.arange(1, 9) * c / df).astype(int)].mean(0) for c in cands])
    return t, ndimage.median_filter(cands[np.argmax(sc, 0)], 9)


def inertia(r, up_s, down_s, B=64):
    s = np.empty_like(r); up, dw = 1 - np.exp(-1 / (up_s * SR)), 1 - np.exp(-1 / (down_s * SR)); prev = r[0]
    for i in range(0, len(r), B):
        tgt = r[i:i + B].mean(); a = up if tgt > prev else dw; k = np.arange(1, min(B, len(r) - i) + 1)
        s[i:i + B] = tgt + (prev - tgt) * (1 - a) ** k; prev = s[min(i + B, len(r)) - 1]
    return s


def make_loop(seg, xf):
    k = int(xf * SR); body = seg[:, k:-k]; w = np.sin(np.linspace(0, np.pi / 2, k)) ** 2
    return np.concatenate([body, seg[:, -k:] * (1 - w) + seg[:, :k] * w], axis=1)


def rev_sync(rates, done, fps, which="huracan"):
    C = SOURCES[which]; RISE, FALL, IDLE = C["rise"], C["fall"], C["idle"]
    n = int(len(rates) / fps * SR); tf = np.arange(len(rates)) / fps; ts = np.arange(n) / SR
    r = np.interp(ts, tf, rates); dn = np.interp(ts, tf, done.astype(float)) > 0.5
    if dn.any():                                                      # after done: back to idle
        i0 = np.argmax(dn); k = np.arange(n - i0) / SR; r[i0:] = 1.0 + (r[i0] - 1.0) * np.exp(-k / 0.5)
    s = inertia(r, *C["inertia"])
    rho = 1 + (C["rho_top"] - 1) * np.clip((s - 1) / 0.9, -0.2, 1.0)    # speed-up 1.0 -> steady/idle, 1.9 -> top of the rev-up

    x = read_wav(C["src"])                                            # round 8: the recording as is (no denoising, no EQ)
    if C["tracker"] == "comb":
        t_tr, f0 = track_f0(x[:, :int(IDLE[1] * SR)], 55, 120)
        idle_f0 = float(np.median(f0[(t_tr >= IDLE[0]) & (t_tr <= IDLE[1])]))
        rho_src = np.interp(np.arange(x.shape[1]) / SR, t_tr, f0 / idle_f0)
    else:                                                             # harmonic-pattern shift against the steady segment
        from rpm_shift_track import track_ratio
        t_tr, rt, _ = track_ratio(x.mean(0), 0.5 * (IDLE[0] + IDLE[1])); idle_f0 = float("nan")
        rho_src = np.interp(np.arange(x.shape[1]) / SR, t_tr, rt / np.median(rt[(t_tr >= IDLE[0]) & (t_tr <= IDLE[1])]))
    def layer(a, b):
        i, j = int(a * SR), int(b * SR); return x[:, i:j], rho_src[i:j]
    rise, rr = layer(*RISE); fall, fr = layer(*FALL)
    rr = np.maximum.accumulate(rr); fr = np.minimum.accumulate(np.minimum(fr, fr[0]))   # monotone rev-up / rev-down (drops tracker glitches)
    idle_seg = x[:, int(IDLE[0] * SR):int(IDLE[1] * SR)]
    if C["idle_lp"]: idle_seg = signal.sosfiltfilt(signal.butter(4, C["idle_lp"] / (SR / 2), output="sos"), idle_seg, axis=1)
    idle = make_loop(idle_seg, min(0.4, 0.2 * (IDLE[1] - IDLE[0])))
    rms = lambda z: np.sqrt((z ** 2).mean()) + 1e-12
    ir = rms(idle)
    if which == "huracan": rise *= 2.2 * ir / rms(rise); fall *= 1.3 * ir / rms(fall)   # recorded idle is ~10x quieter
    else: rise *= 1.6 * ir / rms(rise); fall *= 1.3 * ir / rms(fall)

    # idle layer: a held rpm = the idle loop played at rho
    pos = np.cumsum(np.clip(rho, 0.8, 1.6) ** (0.5 if which == "f355" else 1.0)) % idle.shape[1]; a0 = np.floor(pos).astype(int); fa = pos - a0
    y_idle = idle[:, a0] * (1 - fa) + idle[:, (a0 + 1) % idle.shape[1]] * fa

    # rise / fall layers by rpm-matched grains
    drho = np.gradient(rho) * SR
    dsm = ndimage.uniform_filter1d(drho, int(0.06 * SR))
    w_up = np.clip(dsm / C["dthr"], 0, 1) ** 1.5; w_dn = np.clip(-dsm / C["dthr"], 0, 1) ** 1.5   # small changes barely trigger
    y_up = np.zeros((2, n + G)); y_dn = np.zeros((2, n + G)); y_hold = np.zeros((2, n + G)); win = np.hanning(G)
    hold_on = which == "f355"            # long, slow rev-up: its grain at the current rpm = that rpm held under throttle
    for c in range(0, n, HOP):
        tgt = rho[c]
        for buf, src, sr_, wt in ((y_up, rise, rr, w_up[c]), (y_dn, fall, fr, w_dn[c]), (y_hold, rise, rr, 1.0 if hold_on else 0.0)):
            if wt < 0.02: continue
            k = int(np.argmin(np.abs(sr_ - tgt))); q = float(np.clip(tgt / sr_[k], 0.85, 1.18))   # leftover ratio only
            k = int(np.clip(k + rng.integers(-120, 121) - G * q / 2, 0, src.shape[1] - int(G * q) - 2))
            idx = k + np.arange(G) * q; i0 = idx.astype(int); fi = idx - i0
            g = src[:, i0] * (1 - fi) + src[:, i0 + 1] * fi
            buf[:, c:c + G] += g * win * 0.5
    sh = G // 2                                                      # grain centres at c
    y_up = y_up[:, sh:sh + n] if y_up.shape[1] >= sh + n else np.pad(y_up[:, sh:], ((0, 0), (0, sh + n - y_up.shape[1])))
    y_dn = y_dn[:, sh:sh + n] if y_dn.shape[1] >= sh + n else np.pad(y_dn[:, sh:], ((0, 0), (0, sh + n - y_dn.shape[1])))
    wu = ndimage.uniform_filter1d(w_up, int(C["xfade"] * SR)); wd = ndimage.uniform_filter1d(w_dn, int(C["xfade"] * SR))
    if hold_on:
        y_hold = y_hold[:, sh:sh + n] if y_hold.shape[1] >= sh + n else np.pad(y_hold[:, sh:], ((0, 0), (0, sh + n - y_hold.shape[1])))
        hb = np.clip((rho - 1.0) / 0.08, 0, 1); y_idle = y_idle * (1 - hb) + y_hold * hb * 0.8
    y = y_idle * (1 - 0.7 * np.maximum(wu, wd)) * (0.85 + 0.6 * (rho - 1)) + y_up * wu + y_dn * wd

    env = np.ones(n); env[:int(0.03 * SR)] = np.linspace(0, 1, int(0.03 * SR))
    if dn.any():
        i0 = np.argmax(dn); fo = min(n - i0, int(2.0 * SR)); env[i0:i0 + fo] *= np.linspace(1, 0, fo) ** 1.5; env[i0 + fo:] = 0
    y *= env
    print(f"{which}: idle f0 {idle_f0:.1f} Hz; rise rho {rr.min():.2f}-{rr.max():.2f}, fall rho {fr.min():.2f}-{fr.max():.2f}; "
          f"time with rev-up {np.mean(w_up > 0.3) * 100:.0f}%, rev-down {np.mean(w_dn > 0.3) * 100:.0f}%", flush=True)
    return (y / (np.abs(y).max() + 1e-9) * 0.85).astype(np.float32), rho, w_up, w_dn


def write_wav(path, x):
    pcm = (np.clip(x.T, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("log"); ap.add_argument("video"); ap.add_argument("out")
    ap.add_argument("--source", choices=list(SOURCES), default="huracan")
    a = ap.parse_args()
    Lg = json.load(open(a.log)); fr = Lg["frames"]; fps = Lg.get("fps", 30.0)
    rates = np.array([f["r"] for f in fr], float); done = np.array([f["done"] for f in fr], bool)
    hms = subprocess.run([FF, "-i", a.video], capture_output=True, text=True).stderr.split("Duration: ")[1].split(",")[0].split(":")
    nv = int(round((3600 * float(hms[0]) + 60 * float(hms[1]) + float(hms[2])) * fps))
    if nv > len(rates): rates = np.r_[rates, np.full(nv - len(rates), rates[-1])]; done = np.r_[done, np.full(nv - len(done), done[-1])]
    y, rho, wu, wd = rev_sync(rates, done, fps, a.source)
    wav = a.out.replace(".mp4", ".wav"); write_wav(wav, y)
    np.savez(a.out.replace(".mp4", "_sync.npz"), rho=rho[::480], w_up=wu[::480], w_dn=wd[::480], rate=np.interp(np.arange(0, len(rho), 480) / SR, np.arange(len(rates)) / fps, rates))
    subprocess.run([FF, "-v", "error", "-y", "-i", a.video, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", "-movflags", "+faststart", a.out], check=True)
    print("wrote", a.out, f"{len(rates) / fps:.2f} s", flush=True)
