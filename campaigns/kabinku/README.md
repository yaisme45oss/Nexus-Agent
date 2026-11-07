# KabinKu campaign kit

Promo video + promotion plan for **KabinKu Cabin & Container** (https://www.kabinku.com.my), a Klang-based modular cabin builder.

## Deliverables

| File | Use |
|---|---|
| `deliverables/KabinKu_Reel_9x16.mp4` | 1080×1920, 27s, 30fps, H.264 + AAC, −14 LUFS. Instagram/Facebook Reels & Stories, TikTok, YouTube Shorts, WhatsApp Status, Meta ads 9:16 placements |
| `deliverables/KabinKu_Feed_4x5.mp4` | 1080×1350 crop of the same cut for Facebook/Instagram feed ads |
| `deliverables/cover_9x16.jpg` | Cover / thumbnail frame |
| `deliverables/storyboard/` | One still per scene |
| `PROMOTION_PLAN.md` | Audiences, funnel, channels, budget, 90-day roadmap, KPIs, ad copy (BM + EN), website fixes |

All on-screen text sits inside the Reels/TikTok safe area, and every message is readable with the sound off.

## The cut (27s, 120 BPM, cuts on the beat)

| Time | Scene | Motion / effect | Source |
|---|---|---|---|
| 0.0–2.0 | **Hook:** "NAK BINA" + rolling word (HOMESTAY? / PEJABAT? / SEKOLAH? / PERNIAGAAN?) | Slot-roll words, photo cards pop and stack | Site project photos |
| 2.0–3.5 | **Drop:** "BINA SECARA MODULAR" | Green cabin cut-out falls and lands: squash, camera shake, dust particles, flash; cabin overlaps the headline for depth | Hand-masked cut-out of KabinKu's product render |
| 3.5–7.5 | **Kenapa pilih KabinKu?** Kos terkawal · Siap pantas · Kualiti dijamin | Whip-pan in, Ken Burns, icon pops on beats | 2-storey project photo |
| 7.5–12 | **Sesuai untuk:** Homestay · Pejabat · Asrama · Industri | Diagonal wipe reveals with amber slab, label roll, card counter | 4 project photos |
| 12–16 | **Dari reka bentuk hingga pemasangan** (4 steps) | Timeline draws down, thumbnails wipe in, steps tick to ✓ | Exploded diagram, factory, crane, site team |
| 16–19.5 | **Dibina untuk tahan lama** | Cream colour-wipe, cabin slides in, dimension lines draw with count-up 2800 / 5950 / 3000 mm, spec chips | Cut-out + KabinKu spec sheet |
| 19.5–23 | **Sejak 2015:** Johor → Kelantan, CIDB G3 · MOF Bumiputera · TNB | Shutter reveal, 3-column parallax photo wall, slot-machine year, crossing location tapes | 21 project photos |
| 23–27 | **CTA:** Minta sebut harga terperinci → WhatsApp 013-337 9262 | Logo drops and swings on its crane hook, pulsing WhatsApp button, sparkle burst, shine | KabinKu logo |

Music and SFX are synthesized in `motion/music.py` (no licensing needed). They include impacts on the landing and the CTA, whooshes on every transition, and ticks and dings on the UI beats.

## Re-rendering / editing

The video is an HTML timeline (`motion/index.src.html`) where every element is a pure function of time `t`, so any frame renders identically.

```bash
cd campaigns/kabinku/motion
npm install            # fonts, icons, playwright
npm run build          # inlines icons -> index.html
npm run frames         # 810 JPEG frames via headless Chromium (~1 min with 4 workers, see render.js args)
npm run music          # soundtrack -> music.wav (needs python3 + numpy + scipy, ffmpeg)
npm run encode && npm run feed
```

Change copy, phone numbers or timing directly in `index.src.html` (timings are the `WT`, `UT`, `PT` arrays and the `P(t, start, duration)` calls). Photos in `motion/assets/` come from kabinku.com.my; `c*.png` are background-removed cut-outs.
