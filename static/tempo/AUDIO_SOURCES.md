# Audio sources (sound preview page only; the main page has no sound)

Both options are rev-synced (tools/page_v19/v41_rev_sync_audio.py): the recording's rpm is tracked, and its real rev-up
plays while the executed speed-up rises, its real rev-down while it falls, as 80 ms grains taken where the recording has the
rpm the dial calls for. Denoised (spectral subtraction), +6 dB below 150 Hz, 6 kHz low-pass.

- A: "Lambo Start Up Sound" by JaimeLopes, Freesound #564373 (Lamborghini Huracán EVO Spyder V10),
  https://freesound.org/people/JaimeLopes/sounds/564373/ — CC0 1.0. Only 1.15–4.2 s is used (start-up and the clean idle
  after it); the later part with voices, birds and children is not used.
- B: "ferrari355underhood4.mp3" by enginemusic, Freesound #43484, https://freesound.org/people/enginemusic/sounds/43484/
  — CC BY 3.0 (https://creativecommons.org/licenses/by/3.0/), attribution required. Used: rev-up 2–7 s, drop 7.0–7.6 s,
  steady 0.6–1.9 s; denoised, cut and resequenced.
