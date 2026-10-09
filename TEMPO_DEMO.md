# Interactive split tempo demo

Entry point: `tempo.html`; linked from the project page. Based on `project-page`.

Run `python tools/serve_demo.py --port 8000` at the repository root and open `http://127.0.0.1:8000/tempo.html`. The preview server supports HTTP Range requests, required for reliable video seeking; basic `python -m http.server` may reset some MP4s to time zero on seek. No build, framework or external audio is required. Web Audio starts after clicking Enable tempo sound. Sound follows video playback and is muted on pause, seeking, tab hiding, or Ours completion. Volume is adjustable. Video playback rate is unchanged.

The videos are the existing v18 split panels. Left is the **same footage reconstructed under a fixed 15 Hz action clock**, not an independent baseline-policy rollout. Right is recorded execution. Cup/trash are q99; towel is q95. Completion is the second release for cup and last release for towel/trash. This is a demo comparison, not a new evaluation metric.

`static/data/tempo.json` records source rollout IDs, panel filenames, hashes, policy/video offset, completion times and 30 Hz display telemetry. Applied tempo comes from the established seam-aware execution-clock reconstruction. Gauge and sound use the same ±0.12 s display averaging as v18. The common dial scale covers all three traces. Status labels describe pace; they do not infer contact phases.

The synthesized sound makes increasing/decreasing tempo perceptible; it is not recorded robot noise. Panel MP4s retain their original bytes. Downloading a split MP4 does not include the live web gauge or synthesized sound.

Regenerate with `tools/export_tempo_demo.py --analysis-dir <existing-v18-analysis> --asset-dir <existing-v18-assets>`, in the original numpy/pandas/scipy environment with its completion detector. Existing MP4s are copied without transcoding. Python is only used for offline export.

Review this branch before merging. Pushing it does not modify `main` or `project-page`. The maintainer chooses the merge target and publication timing.
