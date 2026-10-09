# Interactive tempo demo
Entry: `index.html#inference-time`. Work stays on `hansang/tempo-split-gauge-20261009`; main and project-page are unchanged. Original main demo videos are untouched.

## Preview
Run `python tools/serve_demo.py --port 8731`. This server supports MP4 Range requests. No build or external audio service is needed.

## Split, gauge and sound
Existing v18 split panels are unchanged. The left is the same footage reconstructed under a nominal 15 Hz clock, not a separate baseline rollout. Cup/trash use q99; towel q95. The 1×-centered gauge and sound follow the same applied-tempo telemetry.
F1 recording removed. Web Audio uses five sinusoidal harmonics (weights .48/.24/.14/.09/.05), fundamental `72+105*pace` Hz, lowpass `450+1350*pace` Hz and gain `volume*(.055+.115*pace^1.4)`. Faster motion is higher, brighter and louder. Gain fades on pause/seek/hidden tab/completion; opt-in only, no noise source. A compressor limits peaks. Human listening preference still requires review; automated checks cannot establish pleasantness.

## Three synchronized 3D comparisons
Run chunk starts q50–q90, q50–q95 and q50–q99 together. Fixed isometric 3D, common spatial scale, blue q50 ghost and colored quantile marker.
`tools/export_synced_segment.py` exports the first visible one-second measured motion segment of `v3_20260929_041209`, plus 31 camera frames. A JPEG atlas lets a single animation clock select all six video frames and all six 3D positions without browser video-seek races.
This intentionally replaces the old first predicted proposal: its beginning preceded the video and was not exactly tracked after replanning. The new panel shows a measured motion segment, not a claimed exact execution of a frozen predicted chunk.
Clocks follow existing v20: q99 is recorded time; q50 integrates applied q99 rate; other quantiles use the saved model rate with the recorded q99 cap where limiting. Durations: q50 1.4800 s, q90 1.1980 s, q95 1.1277 s, q99 1.0000 s. These are same-footage timing reconstructions, not independently solved/executed rollouts. q50 means nominal 15 Hz, not a fourth stored prediction channel.
Source timestamp is shared by video and measured FK. Frame quantization is 30 Hz; geometry is sampled at 120 Hz. Restarts reset all panels.

## Gripper afterimage pilot
Cup only, optional. Red-finger localization in the right lane; retain 0.34 s of history and show three ghosts at approximately .10/.20/.30 s. Local red/dark pixels isolate fingers/gripper from tabletop, with a cyan tint and feathering. Left lane is never painted. Reset on seek/task change.
This is a color-keyed visual effect, not SAM2/general-purpose tracking. Occlusion or unfamiliar colors can hide the effect. The earlier standalone `cup_trail_pilot.mp4` is obsolete and is no longer linked; live canvas is the current version.

## Verification (October 10)
Browser checks: three panels progress concurrently and end at index 120, restart works, no page JS errors, mobile has no horizontal overflow. Screenshots inspected for synchronized source footage and visible gripper ghosts. F1 audio is neither fetched nor used. Original real-robot demo section unchanged.
