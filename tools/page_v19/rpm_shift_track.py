import wave, numpy as np, sys
from scipy import signal, ndimage
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
SR = 48000; E = "/storage/always216/ROBOT/tempo_viz_20261004/engine_cc0/"
def track_ratio(m, ref_t, lo=80, hi=2500, bpo=96, smin=-0.4, smax=1.0):
    f, t, Z = signal.stft(m, SR, nperseg=8192, noverlap=8192 - 480); M = np.log(np.abs(Z) + 1e-7)
    lf = lo * 2 ** (np.arange(int(np.log2(hi / lo) * bpo)) / bpo)
    G = np.stack([np.interp(lf, f, M[:, j]) for j in range(M.shape[1])], 1)
    G = G - ndimage.uniform_filter1d(G, bpo // 2, axis=0)                 # whiten: keep the harmonic pattern
    jr = np.argmin(abs(t - ref_t)); ref = G[:, max(0, jr - 10):jr + 10].mean(1)
    shifts = np.arange(int(smin * bpo), int(smax * bpo) + 1); sc = np.zeros((len(shifts), G.shape[1]))
    for k, s in enumerate(shifts):
        a = ref[max(0, -s):len(ref) - max(0, s)]; b = G[max(0, s):G.shape[0] - max(0, -s)]
        sc[k] = (a[:, None] * b).sum(0) / (np.linalg.norm(a) * np.linalg.norm(b, axis=0) + 1e-9)
    r = 2 ** (shifts[np.argmax(sc, 0)] / bpo)
    return t, ndimage.median_filter(r, 9), sc.max(0)
if __name__ == "__main__":
    w = wave.open(E + "cc0_43484.wav"); x = np.frombuffer(w.readframes(w.getnframes()), "<i2").reshape(-1, 2).astype(float).T / 32767
    t, r, q = track_ratio(x.mean(0), 1.2)
    for tt in np.arange(0, 18.2, 0.25): i = np.argmin(abs(t - tt)); print(f"{tt:5.2f}s ratio {r[i]:.3f} corr {q[i]:.2f}")
    plt.figure(figsize=(14, 4)); plt.plot(t, r); plt.plot(t, q, alpha=0.4); plt.grid(); plt.savefig("/storage/always216/ROBOT/tempo_viz_20261004/sound_test/f355_ratio.png", dpi=65)
