# Top Touch Barbershop: promo reel

A 30-second vertical promo (1080×1920, 30 fps) for **Top Touch Barbershop, SS15 Subang Jaya** (@toptouchbarbershop), produced by Vyntra. It is built from the shop's own Instagram reels and photos, and carries the Vyntra watermark plus a closing Vyntra card.

| File | What it is |
|---|---|
| `TopTouch_Barbershop_Promo_9x16.mp4` | Final video: H.264 at about 10 Mbps, AAC audio, ready for Reels, TikTok and Shorts |
| `cover.jpg` | Cover frame (title card) for the Reels thumbnail |
| `VEO_PROMPTS.md` | Image-to-video prompts for regenerating the shop shots with Google Veo |
| `stills/` | Shop photos taken from the client's interior reel, used as Veo inputs |
| `veo/` | Put Veo clips here as `<shot>.mp4`; the renderer then uses them in place of the animated stills |
| `pipeline/` | The scripts that build the video (see below) |

## Edit structure

| Time | Shot | Treatment |
|---|---|---|
| 0.0–1.75 | Flame spray styling | Hook "NOT JUST / A HAIRCUT"; the fireball lands on the music impact and flashes to white |
| 1.75–4.0 | Corridor photo | Ceiling lights switch on from back to front with bloom and dolly in; "WELCOME TO TOP TOUCH BARBERSHOP", SS15 · Subang Jaya |
| 4.0–10.0 | Shop photos | Photo-to-video moves: orbit with depth parallax plus light sweep (LUXURY), spinning dolly (BUILT FOR), rack focus (COMFORT & STYLE), framed cinema panel (PREMIUM GROOMING EXPERIENCE) |
| 10.0–13.0 | Cut montage | PRECISION, CLEAN LINES, BOLD COLOUR, with zoom and whip transitions |
| 13.0–15.0 | Subject cutout #1 | Freeze frame; client cut out with a white sticker stroke and pop-out; "FADE" behind the subject |
| 15.0–17.0 | Cut montage | SILVER TONES, SHARP STYLING |
| 17.0–19.0 | Subject cutout #2 | Freeze with echo outlines; "NEXT / LEVEL" behind the subject |
| 19.0–21.0 | Before / after | Angled gold wipe from BEFORE to AFTER on the same client |
| 21.0–23.0 | Moody profile | Slow motion with light leak; "YOUR NEXT LOOK / STARTS HERE" |
| 23.0–24.0 | Flash montage | Four shop photos at 0.25s each |
| 24.0–28.5 | End card | TOP TOUCH BARBERSHOP, a "BOOK YOUR SEAT TODAY" button, location, Instagram handle |
| 28.5–30.0 | Vyntra sign-off | Logo reveal, "PRODUCED BY VYNTRA", vyntra.site |

**Photo-to-video:** the shop photos get 2.5D camera moves, not flat zooms. Nearness is modelled as distance from each room's vanishing point, so in a forward dolly the near walls, floor and ceiling rush past while the far end holds, and in a sideways move the foreground slides further than the back of the room (`depth_warp` in `pipeline/render.py`).

The Vyntra logo watermark sits top-right for 0–28.5s, placed to stay clear of the Reels and TikTok side buttons and caption area.

**Music:** an original 120 BPM dark-trap bed synthesized by `pipeline/music.py`, so there is no licensing issue. Impacts are timed to the fireball, both freezes, the AFTER reveal and the end card. If the client would rather use a trending sound, add it in the Instagram or TikTok editor and turn the original audio down.

## Rebuilding

Requirements: ffmpeg, `yt-dlp`, the `fonts-bebas-neue` and `fonts-montserrat` packages, and Python 3.12 with `mediapipe==0.10.14 opencv-python-headless "numpy<2" pillow scipy`.

```bash
W=/path/to/workdir            # holds reels/, shopframes/, assets/, out/
# 1. source reels -> $W/reels/<id>.mp4  (DWeQS8BD6XI DXT8zDtD3ph DYo-8nmPWA9 DX6Y6PXvKG3 DZUfEVUPP73)
# 2. shop photos: frames of DYo-8nmPWA9 at 2 fps -> $W/shopframes/f_%03d.jpg, then
python pipeline/prep_stills.py $W
# 3. cutout masks (frames at DX6Y6PXvKG3 11.0s -> redprofile.png, DZUfEVUPP73 12.9s -> blondfront.png)
python pipeline/cutout.py $W/assets/frames/redprofile.png $W/assets/frames/redprofile_mask.png
python pipeline/cutout.py $W/assets/frames/blondfront.png $W/assets/frames/blondfront_mask.png
# 4. Vyntra logo -> $W/assets/vyntra-logo.png  (from vyntra.site/assets/img/vyntra-logo.png)
# 5. render
python pipeline/music.py $W/out/music.wav
VEO_DIR=$PWD/veo python pipeline/render.py $W full $W/out/video_noaudio.mp4
ffmpeg -i $W/out/video_noaudio.mp4 -i $W/out/music.wav -map 0:v -map 1:a -c:v libx264 -preset slow -crf 20 \
  -maxrate 10M -bufsize 20M -pix_fmt yuv420p -c:a aac -b:a 192k -shortest -movflags +faststart TopTouch_Barbershop_Promo_9x16.mp4
```

**Veo clips via the Gemini API:** `python pipeline/veo_gen.py stills veo` generates all seven shots from `stills/` with the prompts in `VEO_PROMPTS.md` and saves them as `veo/<shot>.mp4`. It needs a Gemini API key, either saved as a network secret for `generativelanguage.googleapis.com` (header `x-goog-api-key`) or exported as `GEMINI_API_KEY`. Billing goes to the Google Cloud project behind that key. Add `--models` to list the Veo models the key can use.

To preview single frames instead of a full render: `python pipeline/render.py $W stills $W/preview/p 3.5,14.5,26`.
