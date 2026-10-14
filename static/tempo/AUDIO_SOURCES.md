# Audio sources

Engine sound in the inference-time split videos (static/tempo/split_{trash,cup,towel}.mp4):
"ferrari355underhood4.mp3" by enginemusic, Freesound #43484, https://freesound.org/people/enginemusic/sounds/43484/
— CC BY 3.0 (https://creativecommons.org/licenses/by/3.0/), attribution required (credited under the video on index.html).

Used as recorded (no denoising, no EQ), only its slow rev-up at 2–7 s, cut and resequenced (tools/page_v19/v45_f355_rpm.py):
the recording is read at speed = target rpm / recorded rpm, so the engine always has the rpm the dial calls for (speeding up
runs through the real rev-up, slowing down lowers the pitch); every video starts at the bottom of the rev-up; after the task
is done the engine winds down below idle while fading out. The drop at 7.0–7.6 s (air-release hiss) is not used.
All other videos on the page have no sound.
