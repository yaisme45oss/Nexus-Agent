#!/usr/bin/env python3
"""Generate the Veo image-to-video shop clips through the Gemini API.

The API key is NOT read here: the session's network proxy injects the x-goog-api-key header for
generativelanguage.googleapis.com (saved as a network secret in the environment settings).
Outside that setup, export GEMINI_API_KEY and it is sent as the header instead.

usage: veo_gen.py <stills_dir> <out_dir> [shot ...]     (default: all shots)
       veo_gen.py --models                               (list Veo models the key can use)
"""
import base64, json, os, sys, time, urllib.request, urllib.error

API = 'https://generativelanguage.googleapis.com/v1beta'
NEG = 'people, person, hands, faces, text, captions, watermark, logo, signage, distortion, warping, flicker'
SHOTS = {
    'corridor': ('9:16', 'Slow cinematic dolly forward down the centre aisle of a luxury all-black barbershop. The ceiling of round white disc lights switches on row by row from the back of the room toward the camera, each light blooming softly. Light haze, floating dust in the beams, polished black-and-white geometric floor tiles. Moody premium commercial, anamorphic film look, shallow depth of field. No people, no text, no logos.'),
    'chairdisc': ('9:16', 'Slow orbiting camera arc around a black tufted leather barber chair in a dark luxury barbershop under a ceiling of glowing round disc lights. A soft golden light sweep glides across the leather as the camera moves. Gentle haze, cinematic contrast, shallow depth of field. No people, no text, no logos.'),
    'ceilingup': ('9:16', 'Low-angle camera slowly rotating clockwise while pushing in beneath a dramatic ceiling of glowing round disc lights, black walls with brass sconces, barber chairs below. Lights flicker on in a ripple. Cinematic, premium, high contrast. No people, no text, no logos.'),
    'chairwall': ('9:16', 'Rack focus from soft blur to tack-sharp on a black tufted barber chair beneath two brass wall sconces and framed portraits on a matte black wall. Camera eases back slightly, warm sconce light glows on. Cinematic luxury mood. No people, no text, no logos.'),
    'lounge': ('16:9', 'Slow lateral slide across a luxury barbershop waiting lounge: tan leather sofa, glass coffee table, sputnik bubble chandelier twinkling, blue accent light glowing behind an arched wall, barber chairs in the background. Cinematic, warm, moody. No people, no text, no logos.'),
    'window': ('16:9', 'Gentle push-in on a window bar counter in a modern barbershop: tall stools, wooden floor, open shelving, mini fridge. Outside the window, green trees sway softly and daylight shifts. Calm, premium, cinematic. No people, no text, no logos.'),
    'wide': ('9:16', 'Slow symmetrical push-in down a wide luxury barbershop: two rows of black barber chairs, a ceiling covered in glowing round disc lights, black-and-white geometric floor. Lights pulse gently. Elegant, cinematic, dark and premium. No people, no text, no logos.'),
}


def call(method, url, body=None, raw=False):
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body is not None else None)
    req.add_header('Content-Type', 'application/json')
    if os.environ.get('GEMINI_API_KEY'):
        req.add_header('x-goog-api-key', os.environ['GEMINI_API_KEY'])
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            data = r.read()
            return data if raw else json.loads(data)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'{e.code} {e.reason}: {e.read().decode(errors="replace")[:600]}') from None


def veo_models():
    out, tok = [], ''
    while True:
        r = call('GET', f'{API}/models?pageSize=200' + (f'&pageToken={tok}' if tok else ''))
        out += [m for m in r.get('models', []) if 'veo' in m['name'] and 'predictLongRunning' in m.get('supportedGenerationMethods', [])]
        tok = r.get('nextPageToken')
        if not tok:
            return out


def pick_model(models):
    # prefer the newest full-quality model; fall back to anything Veo
    def score(m):
        n = m['name']
        ver = [int(x) for x in ''.join(c if c.isdigit() else ' ' for c in n.split('veo-')[-1]).split()[:2]] + [0, 0]
        return (ver[0], ver[1], 'fast' not in n, 'preview' not in n)
    return sorted(models, key=score)[-1]['name']


def generate(model, shot, stills, out_dir):
    ar, prompt = SHOTS[shot]
    img = base64.b64encode(open(f'{stills}/{shot}.jpg', 'rb').read()).decode()
    params = {'aspectRatio': ar, 'negativePrompt': NEG, 'durationSeconds': 8}
    variants = [{'bytesBase64Encoded': img, 'mimeType': 'image/jpeg'}, {'inlineData': {'mimeType': 'image/jpeg', 'data': img}}]
    last = None
    for image in variants:
        try:
            op = call('POST', f'{API}/{model}:predictLongRunning', {'instances': [{'prompt': prompt, 'image': image}], 'parameters': params})
            break
        except RuntimeError as e:
            last = e
            if not str(e).startswith('400'):
                raise
    else:
        raise last
    name = op['name']
    print(f'{shot}: started {name}', flush=True)
    t0 = time.time()
    while not op.get('done'):
        time.sleep(10)
        op = call('GET', f'{API}/{name}')
        if time.time() - t0 > 900:
            raise RuntimeError(f'{shot}: timed out waiting for Veo')
    if 'error' in op:
        raise RuntimeError(f'{shot}: {op["error"]}')
    resp = op.get('response', {})
    samples = (resp.get('generateVideoResponse') or resp).get('generatedSamples') or resp.get('generatedVideos') or []
    if not samples:
        raise RuntimeError(f'{shot}: no video in response (possibly filtered): {json.dumps(resp)[:600]}')
    uri = samples[0]['video']['uri']
    data = call('GET', uri, raw=True)
    path = f'{out_dir}/{shot}.mp4'
    open(path, 'wb').write(data)
    print(f'{shot}: saved {path} ({len(data) / 1e6:.1f} MB, {time.time() - t0:.0f}s)', flush=True)


if __name__ == '__main__':
    if sys.argv[1:] == ['--models']:
        for m in veo_models():
            print(m['name'], '-', m.get('displayName', ''))
        sys.exit(0)
    stills, out_dir = sys.argv[1], sys.argv[2]
    shots = sys.argv[3:] or list(SHOTS)
    os.makedirs(out_dir, exist_ok=True)
    model = os.environ.get('VEO_MODEL') or pick_model(veo_models())
    print('model:', model, flush=True)
    failed = []
    for s in shots:
        try:
            generate(model, s, stills, out_dir)
        except Exception as e:  # keep going so one filtered shot doesn't sink the batch
            print(f'{s}: FAILED {e}', flush=True); failed.append(s)
    print('done; failed:', failed or 'none')
