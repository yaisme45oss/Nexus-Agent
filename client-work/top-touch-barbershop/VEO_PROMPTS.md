# Veo prompts for the Top Touch shop shots

The promo currently animates the shop photos with motion graphics: camera moves, ceiling lights that switch on, light sweeps, rack focus and dust. To swap any of them for a Google Veo clip:

1. Open Veo in your browser (Flow at labs.google/flow or the Gemini app) and pick **image to video** (frames to video).
2. Upload the matching still from `stills/` and set the length to **8s**. Use **9:16** for every shot except `lounge` and `window`, which play inside a landscape panel and need **16:9**.
3. Paste the prompt. Generate 2–4 takes and keep the best.
4. Save the clip as `veo/<shot-name>.mp4` (e.g. `veo/corridor.mp4`) and send it back. The renderer will use the clip in place of the animated still for that shot.

Every prompt ends with "no people, no text, no logos". Veo sometimes invents customers or signage, and invented signage would clash with the real branding.

| Shot (still) | Where it plays in the promo | Prompt |
|---|---|---|
| `corridor.jpg` | 1.75–4.0s, title card behind "TOP TOUCH" | Slow cinematic dolly forward down the centre aisle of a luxury all-black barbershop. The ceiling of round white disc lights switches on row by row from the back of the room toward the camera, each light blooming softly. Light haze, floating dust in the beams, polished black-and-white geometric floor tiles. Moody premium commercial, anamorphic film look, shallow depth of field. No people, no text, no logos. |
| `chairdisc.jpg` | 4.0–6.0s, "LUXURY / IN EVERY DETAIL" | Slow orbiting camera arc around a black tufted leather barber chair in a dark luxury barbershop under a ceiling of glowing round disc lights. A soft golden light sweep glides across the leather as the camera moves. Gentle haze, cinematic contrast, shallow depth of field. No people, no text, no logos. |
| `ceilingup.jpg` | 6.0–7.0s, "BUILT FOR" | Low-angle camera slowly rotating clockwise while pushing in beneath a dramatic ceiling of glowing round disc lights, black walls with brass sconces, barber chairs below. Lights flicker on in a ripple. Cinematic, premium, high contrast. No people, no text, no logos. |
| `chairwall.jpg` | 7.0–8.0s, "COMFORT & STYLE" | Rack focus from soft blur to tack-sharp on a black tufted barber chair beneath two brass wall sconces and framed portraits on a matte black wall. Camera eases back slightly, warm sconce light glows on. Cinematic luxury mood. No people, no text, no logos. |
| `lounge.jpg` | 8.0–9.0s, "PREMIUM" panel | Slow lateral slide across a luxury barbershop waiting lounge: tan leather sofa, glass coffee table, sputnik bubble chandelier twinkling, blue accent light glowing behind an arched wall, barber chairs in the background. Cinematic, warm, moody. No people, no text, no logos. |
| `window.jpg` | 9.0–10.0s, "GROOMING EXPERIENCE" panel | Gentle push-in on a window bar counter in a modern barbershop: tall stools, wooden floor, open shelving, mini fridge. Outside the window, green trees sway softly and daylight shifts. Calm, premium, cinematic. No people, no text, no logos. |
| `wide.jpg` | 24.0–28.5s, end card background | Slow symmetrical push-in down a wide luxury barbershop: two rows of black barber chairs, a ceiling covered in glowing round disc lights, black-and-white geometric floor. Lights pulse gently. Elegant, cinematic, dark and premium. No people, no text, no logos. |
