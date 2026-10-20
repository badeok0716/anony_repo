"""Follow one harmonic line of an engine recording (2026-10-20): start from the strongest peak in [f_lo, f_hi] at t0,
then each 10 ms frame take the peak within +-6 % of the previous frequency. Returns times and the line's frequency ratio
to its value at t0 (= rpm ratio, since every harmonic scales with rpm)."""
import numpy as np
from scipy import signal, ndimage
SR = 48000

def ridge(x_mono, t0, t1, f_lo, f_hi, tol=0.06):
    seg = x_mono[int(t0 * SR):int(t1 * SR)]
    f, t, Z = signal.stft(seg, SR, nperseg=16384, noverlap=16384 - 480); M = np.abs(Z)
    j0 = slice(0, 10); band = (f >= f_lo) & (f <= f_hi)
    fc = f[band][np.argmax(M[band][:, j0].mean(1))]; out = []
    for j in range(M.shape[1]):
        hw = max(tol * fc, 1.6 * (f[1] - f[0])); k = np.flatnonzero((f >= fc - hw) & (f <= fc + hw))   # at least 3 bins
        kk = k[np.argmax(M[k, j])]
        if 0 < kk < len(f) - 1:                                     # parabolic peak interpolation
            a, b, c = np.log(M[kk - 1:kk + 2, j] + 1e-12); den = a - 2 * b + c; d = float(np.clip(0.5 * (a - c) / den, -0.5, 0.5)) if den < -1e-9 else 0.0; fc = f[kk] + d * (f[1] - f[0])
        else: fc = f[kk]
        out.append(fc)
    out = ndimage.median_filter(np.array(out), 15)
    return t0 + t, out / np.median(out[:10]), out
