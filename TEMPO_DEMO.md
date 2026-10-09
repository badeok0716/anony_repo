# Interactive split tempo demo

Entry point: `index.html#inference-time`, integrated into the light project-page theme. The old `tempo.html` URL redirects here. Based on `project-page`; all changes stay on `hansang/tempo-split-gauge-20261009` until the maintainer's final review.

Run `python tools/serve_demo.py --port 8000` at the repository root and open `http://127.0.0.1:8000/tempo.html`. The preview server supports HTTP Range requests, required for reliable video seeking; basic `python -m http.server` may reset some MP4s to time zero on seek. No build, framework or external audio is required. Web Audio starts after clicking Enable tempo sound. Sound follows video playback and is muted on pause, seeking, tab hiding, or Ours completion. Volume is adjustable. Video playback rate is unchanged.

The videos are the existing v18 split panels. Left is the **same footage reconstructed under a fixed 15 Hz action clock**, not an independent baseline-policy rollout. Right is recorded execution. Cup/trash are q99; towel is q95. Completion is the second release for cup and last release for towel/trash. This is a demo comparison, not a new evaluation metric.

`static/data/tempo.json` records source rollout IDs, panel filenames, hashes, policy/video offset, completion times and 30 Hz display telemetry. Applied tempo comes from the established seam-aware execution-clock reconstruction. Gauge and sound use the same ±0.12 s display averaging as v18. The common dial scale covers all three traces. Status labels describe pace; they do not infer contact phases.

The optional engine audio is a CC0 F1 recording by lmnmrn; source/license are in `static/audio/ATTRIBUTION.md`. Its playback rate/filter follow tempo. The source does not establish that this is a V10 engine. It is an added sound effect, not recorded robot noise. Panel MP4s retain their original bytes. Downloading a split MP4 does not include the live web gauge or sound.

Regenerate with `tools/export_tempo_demo.py --analysis-dir <existing-v18-analysis> --asset-dir <existing-v18-assets>`, in the original numpy/pandas/scipy environment with its completion detector. Existing MP4s are copied without transcoding. Python is only used for offline export.

Review this branch before merging. Pushing it does not modify `main` or `project-page`. The maintainer chooses the merge target and publication timing.

## October 9 integration

- Original real-robot demo markup and source video URLs are unchanged.
- Gauge: 1× centered, reciprocal logarithmic range 1/3×–3×; numeric values remain actual telemetry.
- Cup gripper-trail pilot: detect red finger pixels in the right lane, feather a local patch of radius 8.5% frame height, blend at up to 0.4 alpha with age decay, retain up to four prior frames for 0.17 s. Reset on seek/task change. No trail on the left lane, no phase/grasp labels, no altered timing. This color-based pilot is not a general object segmentation model; disabled for towel/trash.
- Fixed-chunk lab: first saved Cup query (no RTC prefix), current measured joint state plus 15 predicted joint waypoints, flange FK. q50 denotes the nominal 15 Hz reference clock; three actual log-tempo columns give q90/q95/q99 interval durations `1/(15*exp(tempo))`. Their endpoints are 1.0000 / 0.7909 / 0.7403 / 0.6473 seconds. No solver is rerun, and learned quantiles are not artificially sorted.
- The context video alongside the proposed chunk is the recorded q99 rollout with independent controls. It is not claimed to be a new physical rollout at the selected quantile, or exact tracking of the proposal.
- `tools/export_chunk_demo.py` exports compact geometry/clocks; `tools/render_gripper_pilot.py` makes an optional standalone preview with the same local-trail design.
- Standalone pilot: `static/tempo/cup_trail_pilot.mp4`, 756×600, 30 fps, 195 frames / 6.50 s, rendered successfully by CPU Slurm job 143603. The live effect uses the same design, with browser frame availability governing the retained patches. Neither version is object-mask tracking.
- Browser checks passed: main page body remains white; original four demo video elements remain; gaugeAngle(1)=0; engine MP3 decodes; gain is enabled during playback and muted on pause; live trail pixels occur only in the right lane; all four chunk clocks animate through the 1-second reference; mobile has no horizontal overflow.
