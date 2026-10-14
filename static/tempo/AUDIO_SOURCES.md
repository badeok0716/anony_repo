# Audio sources (sound preview page only; the main page has no sound)

Recording: "Lambo Start Up Sound" by JaimeLopes, Freesound #564373 (Lamborghini Huracán EVO Spyder V10),
https://freesound.org/people/JaimeLopes/sounds/564373/ — CC0 1.0 (public domain). Denoised (spectral subtraction).

- A, rev-synced (tools/page_v19/v40_rev_sync_audio.py): the recording's rpm is tracked; its real rev-up (1.15–1.55 s) plays
  while the speed-up rises and its real rev-down (1.60–2.90 s) while it falls, as 80 ms grains taken where the recording has
  the rpm the dial calls for; a steady speed-up holds the idle (3.2–19.5 s) at that rpm.
- B, previous (tools/page_v19/v39_engine_audio.py): the start-up, then the idle loop a little faster and louder with the speed-up.
