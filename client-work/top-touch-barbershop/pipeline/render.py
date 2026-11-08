#!/usr/bin/env python3
"""Top Touch Barbershop promo — motion-graphics renderer.
usage: render.py <scratch_dir> full <out.mp4>
       render.py <scratch_dir> stills <out_prefix> t1,t2,...
"""
import cv2, numpy as np, subprocess, math, sys, os
from PIL import Image, ImageDraw, ImageFont

S = sys.argv[1]; MODE = sys.argv[2]; OUT = sys.argv[3]
TIMES = [float(x) for x in sys.argv[4].split(',')] if MODE == 'stills' else None

W, H, FPS = 1080, 1920, 30
TOTAL = 30.0
REELS = f'{S}/reels'; ASSETS = f'{S}/assets'
BEBAS = '/usr/share/fonts/opentype/bebas-neue/BebasNeue-Bold.otf'
MBLACK = '/usr/share/fonts/truetype/montserrat/Montserrat-Black.ttf'
MBOLD = '/usr/share/fonts/truetype/montserrat/Montserrat-Bold.ttf'
MSEMI = '/usr/share/fonts/truetype/montserrat/Montserrat-SemiBold.ttf'

# colours are BGR float
GOLD_TOP = np.array([128, 218, 248], np.float32) / 255
GOLD_BOT = np.array([38, 124, 180], np.float32) / 255
GOLD = np.array([74, 170, 216], np.float32) / 255
WHITE = np.array([1, 1, 1], np.float32)
BLACK = np.array([0, 0, 0], np.float32)
LUM = np.array([0.114, 0.587, 0.299], np.float32)


# ---------------------------------------------------------------- easing
def c01(x): return 0.0 if x < 0 else 1.0 if x > 1 else float(x)
def eo(x): x = c01(x); return 1 - (1 - x) ** 3
def ei(x): x = c01(x); return x ** 3
def eio(x): x = c01(x); return x * x * (3 - 2 * x)
def bo(x, s=1.9): x = c01(x) - 1; return 1 + x * x * ((s + 1) * x + s)


# ---------------------------------------------------------------- global look
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r2 = ((xx - W / 2) / (W / 2)) ** 2 * 0.55 + ((yy - H / 2) / (H / 2)) ** 2 * 0.75
VIG = np.clip(1 - 0.40 * _r2 ** 1.15, 0.35, 1)[..., None].astype(np.float32)
SH = np.array([0.028, 0.012, -0.012], np.float32)   # teal-ish shadows
HI = np.array([-0.03, 0.0, 0.035], np.float32)      # warm highlights


def look(img, sat=0.9, con=1.1, warm=1.0, vig=True):
    l = (img @ LUM)[..., None]
    x = l + (img - l) * sat
    x = 0.5 + (x - 0.5) * con
    x = x + ((1 - l) * SH + l * HI) * warm
    if vig:
        x = x * VIG
    return np.clip(x, 0, 1)


rng = np.random.default_rng(11)
GRAIN = [cv2.resize(cv2.GaussianBlur(rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32), (0, 0), 0.6),
                    (W, H), interpolation=cv2.INTER_LINEAR)[..., None] for _ in range(6)]


def grain(img, fi, amt=0.028):
    return img + GRAIN[fi % len(GRAIN)] * amt


def vgrad(img, y0, y1, strength, up=False):
    """darken a vertical band smoothly for text legibility"""
    g = np.zeros((H, 1, 1), np.float32)
    ys = np.arange(H, dtype=np.float32)
    mid, half = (y0 + y1) / 2, (y1 - y0) / 2
    g[:, 0, 0] = np.clip(1 - np.abs(ys - mid) / half, 0, 1) ** 0.8
    return img * (1 - strength * g)


# ---------------------------------------------------------------- geometry helpers
def warp(img, M, size=(W, H), border=cv2.BORDER_REFLECT):
    return cv2.warpAffine(img, M, size, flags=cv2.INTER_LINEAR, borderMode=border)


def zoom(img, s, cx=W / 2, cy=H / 2):
    if abs(s - 1) < 1e-4:
        return img
    M = np.float32([[s, 0, cx - s * cx], [0, s, cy - s * cy]])
    return warp(img, M)


def zoomblur(img, s, amt, n=5, cx=W / 2, cy=H / 2):
    if amt < 0.004:
        return zoom(img, s, cx, cy)
    acc = np.zeros_like(img)
    for k in range(n):
        acc += zoom(img, s * (1 + amt * k / (n - 1)), cx, cy)
    return acc / n


def cam(img, s=1.0, rot=0.0, tx=0.0, ty=0.0, size=(W, H)):
    """cover-fit a still into frame then scale/rotate/translate (Ken Burns / dolly)"""
    ih, iw = img.shape[:2]; ow, oh = size
    c = max(ow / iw, oh / ih)
    M = cv2.getRotationMatrix2D((iw / 2, ih / 2), rot, c * s)
    M[0, 2] += ow / 2 + tx - iw / 2
    M[1, 2] += oh / 2 + ty - ih / 2
    return warp(img, M, size)


_dw = {}
VP = {'corridor': (0.45, 0.42), 'ceilingup': (0.5, 0.6), 'wide': (0.5, 0.42), 'corridor2': (0.55, 0.42),
      'chairs': (0.55, 0.45), 'chairdisc': (0.62, 0.38)}


def depth_warp(img, vpn, a=0.0, tx=0.0, ty=0.0):
    """2.5D camera move on a still. Nearness N grows with distance from the room's vanishing point
    (walls/floor/ceiling converge there), so a forward dolly magnifies near areas more than the far end
    (a = dolly amount) and a sideways truck slides near areas further than far ones (tx/ty, px at N=1)."""
    if a < 1e-4 and abs(tx) < 0.05 and abs(ty) < 0.05:
        return img
    h, w = img.shape[:2]; key = (h, w, vpn)
    if key not in _dw:
        gy, gx = np.mgrid[0:h, 0:w].astype(np.float32)
        vx, vy = vpn[0] * w, vpn[1] * h
        R = max(math.hypot(vx, vy), math.hypot(w - vx, vy), math.hypot(vx, h - vy), math.hypot(w - vx, h - vy))
        _dw[key] = (gx, gy, vx, vy, (np.hypot(gx - vx, gy - vy) / R).astype(np.float32))
    gx, gy, vx, vy, N = _dw[key]
    f = 1.0 / (1.0 + a * N)
    mx = vx + (gx - vx) * f - tx * N
    my = vy + (gy - vy) * f - ty * N
    return cv2.remap(img, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def shake(img, amt, t):
    if amt < 0.5:
        return img
    dx = amt * math.sin(t * 91.0) * math.cos(t * 37.0)
    dy = amt * math.sin(t * 73.0 + 1.3)
    M = np.float32([[1.02, 0, dx - 0.01 * W], [0, 1.02, dy - 0.01 * H]])
    return warp(img, M)


def hshift_blur(img, dx, blur):
    x = warp(img, np.float32([[1, 0, dx], [0, 1, 0]]))
    k = int(blur)
    return cv2.blur(x, (k, 1)) if k > 2 else x


def sharpen(img, amt=0.6):
    b = cv2.GaussianBlur(img, (0, 0), 2.0)
    return np.clip(img + (img - b) * amt, 0, 1)


def to_white(img, p):
    return img + (1 - img) * p


# ---------------------------------------------------------------- transitions
def tr_in(img, lt, kind):
    if kind == 'zoom':
        p = lt / 0.2
        if p < 1: img = zoomblur(img, 1 + 0.22 * (1 - eo(p)), 0.10 * (1 - p))
    elif kind == 'whip':
        p = lt / 0.18
        if p < 1: img = hshift_blur(img, W * 0.35 * (1 - eo(p)), 140 * (1 - p))
    elif kind == 'flash':
        p = lt / 0.28
        if p < 1: img = to_white(img, 1 - eo(p))
    elif kind == 'black':
        p = lt / 0.2
        if p < 1: img = img * eo(p)
    return img


def tr_out(img, rem, kind):
    if kind == 'zoom':
        p = 1 - rem / 0.17
        if p > 0: img = to_white(zoomblur(img, 1 + 0.2 * ei(p), 0.10 * p), 0.35 * p)
    elif kind == 'whip':
        p = 1 - rem / 0.15
        if p > 0: img = hshift_blur(img, -W * 0.35 * ei(p), 140 * p)
    elif kind == 'flash':
        p = 1 - rem / 0.12
        if p > 0: img = to_white(img, ei(p))
    elif kind == 'black':
        p = 1 - rem / 0.25
        if p > 0: img = img * (1 - eio(p))
    return img


# ---------------------------------------------------------------- particles / light
NP = 90
PX = rng.uniform(0, W, NP); PY = rng.uniform(0, H, NP)
PVX = rng.uniform(-18, 18, NP); PVY = rng.uniform(-45, -6, NP)
PR = rng.uniform(1.0, 3.2, NP); PA = rng.uniform(0.2, 0.75, NP); PPH = rng.uniform(0, 6.28, NP)


def dust(img, gt, strength=1.0):
    lay = np.zeros((H // 4, W // 4), np.float32)
    for i in range(NP):
        x = (PX[i] + PVX[i] * gt) % W; y = (PY[i] + PVY[i] * gt) % H
        a = PA[i] * (0.55 + 0.45 * math.sin(gt * 2.3 + PPH[i]))
        cv2.circle(lay, (int(x / 4), int(y / 4)), max(1, int(round(PR[i]))), float(a), -1, lineType=cv2.LINE_AA)
    lay = cv2.GaussianBlur(lay, (0, 0), 0.9)
    lay = cv2.resize(lay, (W, H), interpolation=cv2.INTER_LINEAR)
    return img + lay[..., None] * np.array([0.7, 0.88, 1.0], np.float32) * 0.55 * strength


_sy, _sx = np.mgrid[0:H // 8, 0:W // 8].astype(np.float32) * 8


def leak(img, p, y=0.35, color=(0.25, 0.55, 1.0), strength=0.55):
    """warm light leak sweeping right->left, screen blended"""
    if p <= 0 or p >= 1:
        return img
    cx = W * (1.25 - 1.5 * p); cy = H * y
    d2 = ((_sx - cx) ** 2 + ((_sy - cy) * 0.6) ** 2) / (W * 0.55) ** 2
    blob = np.exp(-d2) * math.sin(math.pi * p) * strength
    blob = cv2.resize(blob, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
    lay = blob * np.array(color, np.float32)
    return 1 - (1 - img) * (1 - lay)


_u = ((xx * 0.8 + yy * 0.6) / (W * 0.8 + H * 0.6)).astype(np.float32)


def sweep(img, pos, width=0.06, strength=0.35, color=(0.75, 0.9, 1.0)):
    """diagonal specular light sweep (pos 0..1 across frame)"""
    if pos < -0.2 or pos > 1.2:
        return img
    band = np.exp(-((_u - pos) / width) ** 2)[..., None]
    l = (img @ LUM)[..., None]
    return img + band * strength * (0.35 + l) * np.array(color, np.float32)


# ---------------------------------------------------------------- text / layers
_fc = {}


def F(path, size):
    k = (path, size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(path, size)
    return _fc[k]


def text_mask(txt, path, size, tracking=0.0):
    f = F(path, size)
    asc, desc = f.getmetrics()
    if tracking == 0:
        w = int(math.ceil(f.getlength(txt)))
    else:
        w = int(math.ceil(sum(f.getlength(c) for c in txt) + tracking * (len(txt) - 1)))
    pad = int(size * 0.3) + 10
    img = Image.new('L', (w + 2 * pad, asc + desc + 2 * pad), 0)
    d = ImageDraw.Draw(img)
    if tracking == 0:
        d.text((pad, pad), txt, font=f, fill=255)
    else:
        x = pad
        for ch in txt:
            d.text((x, pad), ch, font=f, fill=255); x += f.getlength(ch) + tracking
    m = np.asarray(img, np.float32) / 255
    ys, xs = np.where(m > 0.02)
    q = 6
    return m[max(ys.min() - q, 0):ys.max() + q + 1, max(xs.min() - q, 0):xs.max() + q + 1]


def gold_fill(h, w):
    g = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    # brighter band in the upper-middle like polished metal
    g2 = np.clip(1 - np.abs(np.linspace(0, 1, h, dtype=np.float32) - 0.32) / 0.18, 0, 1)[:, None, None]
    col = GOLD_TOP * (1 - g) + GOLD_BOT * g
    return np.clip(col + g2 * 0.12, 0, 1) * np.ones((1, w, 1), np.float32)


def colorize(m, color):
    h, w = m.shape
    if isinstance(color, str) and color == 'gold':
        rgb = gold_fill(h, w) * m[..., None]
    else:
        rgb = np.asarray(color, np.float32)[None, None, :] * m[..., None]
    return rgb.astype(np.float32), m[..., None].astype(np.float32)


def add_shadow(layer, blur=14, off=(0, 8), op=0.7):
    rgb, a = layer; h, w = a.shape[:2]
    p = int(blur * 2.5) + max(abs(off[0]), abs(off[1]))
    A = np.zeros((h + 2 * p, w + 2 * p), np.float32)
    A[p + off[1]:p + off[1] + h, p + off[0]:p + off[0] + w] = a[..., 0]
    A = (cv2.GaussianBlur(A, (0, 0), blur) * op)[..., None]
    R = np.zeros((h + 2 * p, w + 2 * p, 3), np.float32)
    R[p:p + h, p:p + w] = rgb + R[p:p + h, p:p + w] * (1 - a)
    A[p:p + h, p:p + w] = a + A[p:p + h, p:p + w] * (1 - a)
    return R, A


def outline_layer(m, color, width=4):
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * width + 1, 2 * width + 1))
    pad = width + 2
    mp = cv2.copyMakeBorder(m, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)
    d = cv2.dilate(mp, k)
    ring = np.clip(d - mp, 0, 1)
    return colorize(ring, color)


_tc = {}


def T(txt, path, size, color=WHITE, tracking=0.0, shadow=True, outline=False):
    ck = color if isinstance(color, str) else tuple(np.round(np.asarray(color), 3))
    k = (txt, path, size, ck, round(tracking, 2), shadow, outline)
    if k not in _tc:
        m = text_mask(txt, path, size, tracking)
        lay = outline_layer(m, color, 5) if outline else colorize(m, color)
        if shadow:
            lay = add_shadow(lay, blur=max(6, size // 14), off=(0, max(3, size // 30)), op=0.75)
        _tc[k] = lay
    return _tc[k]


def resize_layer(layer, s):
    rgb, a = layer; h, w = a.shape[:2]
    nw, nh = max(1, int(round(w * s))), max(1, int(round(h * s)))
    return (cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_LINEAR),
            cv2.resize(a, (nw, nh), interpolation=cv2.INTER_LINEAR)[..., None])


def rot_layer(layer, deg, s=1.0):
    rgb, a = layer; h, w = a.shape[:2]
    D = int(math.hypot(h, w) * s) + 4
    M = cv2.getRotationMatrix2D((w / 2, h / 2), deg, s)
    M[0, 2] += D / 2 - w / 2; M[1, 2] += D / 2 - h / 2
    rgb2 = cv2.warpAffine(rgb, M, (D, D), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    a2 = cv2.warpAffine(a[..., 0], M, (D, D), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)[..., None]
    return rgb2, a2


def paste(dst, layer, cx, cy, op=1.0, scale=1.0, clip=None):
    if op <= 0.001:
        return
    if abs(scale - 1) > 1e-3:
        layer = resize_layer(layer, scale)
    rgb, a = layer
    h, w = a.shape[:2]; DH, DW = dst.shape[:2]
    x0 = int(round(cx - w / 2)); y0 = int(round(cy - h / 2))
    X0, Y0, X1, Y1 = max(x0, 0), max(y0, 0), min(x0 + w, DW), min(y0 + h, DH)
    if clip:
        X0, Y0, X1, Y1 = max(X0, clip[0]), max(Y0, clip[1]), min(X1, clip[2]), min(Y1, clip[3])
    if X1 <= X0 or Y1 <= Y0:
        return
    sr = rgb[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0]; sa = a[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0] * op
    dst[Y0:Y1, X0:X1] = sr * op + dst[Y0:Y1, X0:X1] * (1 - sa)


def anim_text(dst, layer, cx, cy, lt, t_in, t_out=None, style='rise', dur=0.35, op=1.0):
    if lt < t_in:
        return
    p = (lt - t_in) / dur
    o = op
    dy_out = 0
    if t_out is not None and lt > t_out:
        q = c01((lt - t_out) / 0.18)
        o *= 1 - q; dy_out = -40 * eo(q)
        if o <= 0.001:
            return
    h, w = layer[1].shape[:2]
    if style == 'rise':
        e = eo(p)
        dy = (1 - e) * h * 0.9
        paste(dst, layer, cx, cy + dy + dy_out, op=o * c01(p * 2.5),
              clip=(0, int(cy - h / 2 + dy_out), W, int(cy + h / 2 + dy_out) + 1))
    elif style == 'pop':
        paste(dst, layer, cx, cy + dy_out, op=o * c01(p * 4), scale=0.55 + 0.45 * bo(p))
    elif style == 'slam':  # drops in from big
        paste(dst, layer, cx, cy + dy_out, op=o * c01(p * 3), scale=1 + 0.9 * (1 - eo(p)))
    elif style == 'left':
        paste(dst, layer, cx - (1 - eo(p)) * W * 0.7, cy + dy_out, op=o * c01(p * 3))
    elif style == 'right':
        paste(dst, layer, cx + (1 - eo(p)) * W * 0.7, cy + dy_out, op=o * c01(p * 3))
    else:  # fade
        paste(dst, layer, cx, cy + dy_out, op=o * eo(p))


def shine_layer(layer, pos, width=0.12, strength=0.9):
    """specular sweep across a layer (pos 0..1)"""
    rgb, a = layer; h, w = a.shape[:2]
    u = (np.arange(w, dtype=np.float32)[None, :] / w)[..., None] + (np.arange(h, dtype=np.float32)[:, None, None] / h) * 0.25
    band = np.exp(-((u - pos) / width) ** 2) * strength
    return np.clip(rgb + band * a, 0, 1), a


def hline(dst, cx, cy, w, th=4, color='gold', op=1.0):
    if w < 2:
        return
    m = np.ones((th, int(w)), np.float32)
    # soft ends
    ramp = np.clip(np.minimum(np.arange(int(w)), np.arange(int(w))[::-1]) / 30.0, 0, 1)
    m = m * ramp[None, :]
    lay = colorize(m, color)
    paste(dst, add_shadow(lay, blur=6, off=(0, 2), op=0.6), cx, cy, op=op)


# ---------------------------------------------------------------- icons / button
def pin_icon(size, color='gold'):
    s = size * 4
    im = Image.new('L', (s, int(s * 1.35)), 0); d = ImageDraw.Draw(im)
    r = s * 0.42
    d.ellipse((s / 2 - r, s * 0.06, s / 2 + r, s * 0.06 + 2 * r), fill=255)
    d.polygon([(s / 2 - r * 0.78, s * 0.06 + r * 1.55), (s / 2 + r * 0.78, s * 0.06 + r * 1.55), (s / 2, s * 1.32)], fill=255)
    rr = r * 0.42; cy = s * 0.06 + r
    d.ellipse((s / 2 - rr, cy - rr, s / 2 + rr, cy + rr), fill=0)
    m = np.asarray(im.resize((size, int(size * 1.35)), Image.LANCZOS), np.float32) / 255
    return add_shadow(colorize(m, color), blur=5, off=(0, 2), op=0.7)


def ig_icon(size, color='gold'):
    s = size * 4
    im = Image.new('L', (s, s), 0); d = ImageDraw.Draw(im)
    lw = int(s * 0.1)
    d.rounded_rectangle((lw // 2, lw // 2, s - lw // 2, s - lw // 2), radius=int(s * 0.28), outline=255, width=lw)
    r = s * 0.22
    d.ellipse((s / 2 - r, s / 2 - r, s / 2 + r, s / 2 + r), outline=255, width=lw)
    rd = s * 0.06
    d.ellipse((s * 0.74 - rd, s * 0.26 - rd, s * 0.74 + rd, s * 0.26 + rd), fill=255)
    m = np.asarray(im.resize((size, size), Image.LANCZOS), np.float32) / 255
    return add_shadow(colorize(m, color), blur=5, off=(0, 2), op=0.7)


def button(txt, w, h, size):
    s = 3
    im = Image.new('L', (w * s, h * s), 0); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w * s - 1, h * s - 1), radius=h * s // 2, fill=255)
    btn = np.asarray(im.resize((w, h), Image.LANCZOS), np.float32) / 255
    tm = text_mask(txt, MBLACK, size, tracking=2)
    th, tw = tm.shape
    t = np.zeros_like(btn)
    y0 = (h - th) // 2; x0 = (w - tw) // 2
    t[y0:y0 + th, x0:x0 + tw] = tm
    rgb = gold_fill(h, w) * (btn * (1 - t))[..., None] + np.array([0.06, 0.06, 0.06], np.float32) * (btn * t)[..., None]
    lay = (rgb.astype(np.float32), btn[..., None])
    return add_shadow(lay, blur=18, off=(0, 10), op=0.6)


# ---------------------------------------------------------------- media
_clips = {}


def clip(name, start, dur, crop=None):
    k = (name, start, dur, crop)
    if k not in _clips:
        vf = 'fps=30'
        if crop:
            vf += f',crop={crop}'
        vf += f',scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H}'
        cmd = ['ffmpeg', '-v', 'error', '-ss', f'{start:.3f}', '-t', f'{dur + 0.15:.3f}', '-i', f'{REELS}/{name}.mp4',
               '-vf', vf, '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-']
        raw = subprocess.run(cmd, capture_output=True, check=True).stdout
        _clips[k] = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
    return _clips[k]


def vframe(name, start, dur, src_t, crop=None):
    arr = clip(name, start, dur, crop)
    i = int(round((src_t - start) * FPS))
    return arr[max(0, min(len(arr) - 1, i))].astype(np.float32) / 255


VEO_DIR = os.environ.get('VEO_DIR', f'{S}/veo')


def veo(name, lt, start=0.8, size=(W, H)):
    """frame from a user-supplied Veo clip (veo/<name>.mp4) if present, else None"""
    path = f'{VEO_DIR}/{name}.mp4'
    if not os.path.exists(path):
        return None
    k = ('veo', name, size)
    if k not in _clips:
        w, h = size
        cmd = ['ffmpeg', '-v', 'error', '-i', path, '-vf',
               f'fps=30,scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,crop={w}:{h}',
               '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-']
        raw = subprocess.run(cmd, capture_output=True, check=True).stdout
        _clips[k] = np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)
    arr = _clips[k]
    i = int(round((start + lt) * FPS))
    return arr[max(0, min(len(arr) - 1, i))].astype(np.float32) / 255


def load_still(n):
    return cv2.imread(f'{ASSETS}/stills/{n}.png').astype(np.float32) / 255


STILL = {n: load_still(n) for n in ['chairwall', 'chairdisc', 'corridor', 'ceilingup', 'corridor2', 'chairs', 'wide',
                                     'lounge', 'loungetv', 'window']}

# lamp-wave data for the corridor still (lights switch on from the back to the front)
_c = STILL['corridor']
_L = (_c @ LUM)
LAMP = cv2.GaussianBlur(np.clip((_L - 0.6) / 0.28, 0, 1), (0, 0), 1.5)[..., None]
_ch, _cw = _L.shape
_gy, _gx = np.mgrid[0:_ch, 0:_cw].astype(np.float32)
LAMP_D = (np.hypot(_gx - _cw * 0.5, (_gy - _ch * 0.36) * 0.9) / (_cw * 0.95)).astype(np.float32)[..., None]


def corridor_lamps(lt, t0=0.0, dur=1.1):
    wave = -0.1 + 1.25 * eo((lt - t0) / dur)
    on = np.clip((wave - LAMP_D) / 0.1, 0, 1)
    img = _c * (1 - 0.88 * LAMP * (1 - on))
    small = cv2.resize(_c * LAMP * on, (_cw // 4, _ch // 4), interpolation=cv2.INTER_AREA)
    bloom = cv2.resize(cv2.GaussianBlur(small, (0, 0), 7), (_cw, _ch), interpolation=cv2.INTER_LINEAR)
    return img + bloom * 0.9


# ---------------------------------------------------------------- cutouts
def load_cutout(name, stroke=12):
    img = cv2.imread(f'{ASSETS}/frames/{name}.png').astype(np.float32) / 255
    m = cv2.imread(f'{ASSETS}/frames/{name}_mask.png', cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255
    mb = (m > 0.5).astype(np.uint8)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * stroke + 1, 2 * stroke + 1))
    D = cv2.GaussianBlur(cv2.dilate(mb, k).astype(np.float32), (0, 0), 1.6)
    D = np.maximum(D, m)
    ys, xs = np.where(mb > 0)
    cx, cy = xs.mean(), ys.mean()
    glow = np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * 420.0 ** 2)))[..., None].astype(np.float32)
    return dict(img=img, m=m[..., None], D=D[..., None], cx=cx, cy=cy, bottom=float(ys.max()), glow=glow,
                shadow=cv2.GaussianBlur(D, (0, 0), 22)[..., None])


CUT = {'red': load_cutout('redprofile'), 'blond': load_cutout('blondfront')}


def cutout_comp(c, lf, behind, echo=False, glow_col=GOLD):
    F_ = look(c['img'], sat=0.95, con=1.12)
    l = (F_ @ LUM)[..., None]
    bg = (l * 0.85 + F_ * 0.15) * 0.34 + c['glow'] * glow_col * 0.32 * eo(lf / 0.4)
    behind(bg, lf)
    s = 1 + 0.045 * bo(lf / 0.35)
    ax, ay = c['cx'], c['bottom']
    M = np.float32([[s, 0, ax - s * ax], [0, s, ay - s * ay]])
    D = cv2.warpAffine(c['D'][..., 0], M, (W, H))[..., None]
    m = cv2.warpAffine(c['m'][..., 0], M, (W, H))[..., None]
    sub = cv2.warpAffine(F_, M, (W, H))
    shd = np.roll(cv2.warpAffine(c['shadow'][..., 0], M, (W, H)), 24, axis=0)[..., None]
    out = bg * (1 - 0.7 * shd)
    if echo:
        for k, a in ((3, 0.07), (2, 0.12), (1, 0.2)):
            off = int(55 * k * eo(lf / 0.5))
            for sgn in (-1, 1):
                e = np.roll(D, sgn * off, axis=1)
                out = out * (1 - e * a * 0.6) + e * a * 0.6 * WHITE
    stroke = np.clip(D - m, 0, 1)
    subj = sub * m + WHITE * stroke
    return subj + out * (1 - D)


# ---------------------------------------------------------------- watermark
_logo = cv2.imread(f'{ASSETS}/vyntra-logo.png', cv2.IMREAD_UNCHANGED).astype(np.float32) / 255
LOGO = (_logo[..., :3] * _logo[..., 3:4], _logo[..., 3:4])
WM_SIZE = int(os.environ.get('WM_SIZE', 980))
WM_OP = float(os.environ.get('WM_OP', 0.12))
WM = resize_layer(LOGO, WM_SIZE / 512)


# ================================================================ segments
def segA(lt, dur, gt):  # hook: flame / fireball
    img = look(vframe('DXT8zDtD3ph', 2.2, 1.9, 2.25 + lt), sat=0.95, con=1.12)
    img = zoom(img, 1.05 + 0.05 * lt / dur, W / 2, H * 0.42)
    img = vgrad(img, 700, 1150, 0.45)
    if lt >= 1.5:
        img = shake(img, 22 * (1 - c01((lt - 1.5) / 0.25)), gt)
    img = tr_in(img, lt, 'black')
    anim_text(img, T('NOT JUST', BEBAS, 210, WHITE), W / 2, 850, lt, 0.10, 1.38, 'rise')
    anim_text(img, T('A HAIRCUT', BEBAS, 210, 'gold'), W / 2, 1030, lt, 0.42, 1.38, 'rise')
    rem = dur - lt
    if rem < 0.22:
        img = to_white(img, eo(1 - rem / 0.22))
    return img


def segB(lt, dur, gt):  # title over corridor — lights switch on
    img = veo('corridor', lt)
    if img is None:
        base = corridor_lamps(lt, 0.05, 1.1)
        base = base * (0.6 + 0.4 * eo(lt / 0.9))
        base = depth_warp(base, VP['corridor'], a=0.34 * eio(lt / dur))
        img = cam(base, 1.0 + 0.035 * eio(lt / dur), 0, 0, -10 * lt)
    img = look(img, sat=0.92, con=1.06)
    img = vgrad(img, 560, 1260, 0.62)
    img = dust(img, gt, 0.8)
    img = tr_in(img, lt, 'flash')
    img = tr_out(img, dur - lt, 'zoom')
    anim_text(img, T('WELCOME TO', MSEMI, 44, WHITE, tracking=14), W / 2, 700, lt, 0.25, None, 'rise')
    top = T('TOP TOUCH', BEBAS, 270, 'gold')
    if 0.9 < lt < 1.7:
        top = shine_layer(top, (lt - 0.9) / 0.8 * 1.4 - 0.2)
    anim_text(img, top, W / 2, 850, lt, 0.35, None, 'pop', dur=0.45)
    trk = 8 + 18 * eo((lt - 0.55) / 1.2)
    anim_text(img, T('BARBERSHOP', MBLACK, 64, WHITE, tracking=round(trk)), W / 2, 1010, lt, 0.55, None, 'fade', dur=0.3)
    hline(img, W / 2, 1082, 560 * eo((lt - 0.7) / 0.5), 4)
    anim_text(img, T('SS15  ·  SUBANG JAYA', MSEMI, 40, 'gold', tracking=8), W / 2, 1140, lt, 0.85, None, 'rise')
    return img


def segC(lt, dur, gt):  # luxury chair — orbit + light sweep
    p = lt / dur
    img = veo('chairdisc', lt)
    if img is None:
        base = depth_warp(STILL['chairdisc'], VP['chairdisc'], a=0.10 * eio(p), tx=60 - 120 * eio(p))
        img = cam(base, 1.2 - 0.06 * eio(p), -1.6 + 2.6 * eio(p), 30 - 60 * eio(p), 10)
    img = look(img, sat=0.95, con=1.06)
    img = sweep(img, -0.2 + 1.4 * eio((lt - 0.25) / 1.3), 0.07, 0.4)
    img = vgrad(img, 300, 820, 0.55)
    img = dust(img, gt)
    img = tr_in(img, lt, 'zoom')
    img = tr_out(img, dur - lt, 'whip')
    anim_text(img, T('LUXURY', BEBAS, 250, WHITE), W / 2, 470, lt, 0.12, None, 'rise')
    anim_text(img, T('IN EVERY DETAIL', MBLACK, 52, 'gold', tracking=10), W / 2, 640, lt, 0.4, None, 'rise')
    return img


def segD(lt, dur, gt):  # ceiling — spinning dolly
    p = lt / dur
    img = veo('ceilingup', lt)
    if img is None:
        base = depth_warp(STILL['ceilingup'], VP['ceilingup'], a=0.45 * eio(p))
        img = cam(base, 1.1 + 0.12 * eio(p), 6 * eio(p), 0, 0)
    img = look(img, sat=0.95, con=1.06)
    img = vgrad(img, 1150, 1550, 0.6)
    img = dust(img, gt)
    img = tr_in(img, lt, 'whip')
    img = tr_out(img, dur - lt, 'zoom')
    anim_text(img, T('BUILT FOR', BEBAS, 220, WHITE), W / 2, 1350, lt, 0.08, None, 'rise')
    return img


def segE(lt, dur, gt):  # chair wall — rack focus + pull back
    p = lt / dur
    img = veo('chairwall', lt)
    if img is None:
        img = cam(STILL['chairwall'], 1.16 - 0.1 * eio(p), 0, 0, 0)
    sig = 14 * (1 - eo(lt / 0.45))
    if sig > 0.3:
        img = cv2.GaussianBlur(img, (0, 0), sig)
    img = look(img, sat=0.95, con=1.06)
    img = vgrad(img, 380, 820, 0.55)
    img = dust(img, gt)
    img = tr_in(img, lt, 'zoom')
    img = tr_out(img, dur - lt, 'flash')
    anim_text(img, T('COMFORT & STYLE', BEBAS, 165, 'gold'), W / 2, 600, lt, 0.08, None, 'rise')
    return img


def segF(lt, dur, gt):  # cinema panel: lounge -> window
    name = 'lounge' if lt < 1.0 else 'window'
    st = STILL[name]
    pw = 1000; ph = int(round(pw * st.shape[0] / st.shape[1]))
    bg = cv2.GaussianBlur(cv2.resize(cam(st, 1.3, 0, 0, 0), (W // 4, H // 4), interpolation=cv2.INTER_AREA), (0, 0), 6)
    bg = cv2.resize(bg, (W, H), interpolation=cv2.INTER_LINEAR) * 0.33
    ll = lt if lt < 1.0 else lt - 1.0
    pan = veo(name, ll, size=(pw, ph))
    if pan is None:
        pan = cam(st, 1.18 + 0.04 * ll, 0, 60 - 120 * eio(ll), 0, size=(pw, ph))
    pan = look(pan, sat=0.95, con=1.06, vig=False)
    if lt >= 1.0 and ll < 0.2:  # slide transition inside panel
        q = eo(ll / 0.2)
        prev = look(cam(STILL['lounge'], 1.22, 0, -60, 0, size=(pw, ph)), sat=0.95, con=1.06, vig=False)
        sh = int(pw * q)
        pan = np.concatenate([prev[:, sh:], pan[:, :sh]], axis=1) if sh > 0 else prev
    img = bg
    border = np.ones((ph + 8, pw + 8), np.float32)
    paste(img, add_shadow(colorize(border, 'gold'), blur=24, off=(0, 14), op=0.8), W / 2, H / 2)
    paste(img, (pan, np.ones((ph, pw, 1), np.float32)), W / 2, H / 2)
    img = dust(img, gt, 0.7)
    img = tr_in(img, lt, 'flash') if lt < 0.3 else img
    img = tr_out(img, dur - lt, 'zoom')
    yt = H / 2 - ph / 2 - 120; yb = H / 2 + ph / 2 + 95
    anim_text(img, T('PREMIUM', BEBAS, 200, WHITE), W / 2, yt, lt, 0.1, None, 'rise')
    anim_text(img, T('GROOMING EXPERIENCE', MBLACK, 54, 'gold', tracking=8), W / 2, yb, lt, 0.3, None, 'rise')
    return img


def video_seg(name, start, lt, dur, gt, text, color, tin, tout, crop=None, speed=1.0, sharp=0.0, ty=1300, push=0.04):
    img = vframe(name, start, dur * speed + 0.1, start + lt * speed, crop)
    if sharp:
        img = sharpen(img, sharp)
    img = look(img, sat=0.92, con=1.12)
    img = zoom(img, 1.0 + push * lt / dur)
    img = vgrad(img, ty - 220, ty + 220, 0.5)
    img = tr_in(img, lt, tin)
    img = tr_out(img, dur - lt, tout)
    if text:
        anim_text(img, T(text, BEBAS, 200, color), W / 2, ty, lt, 0.06, None, 'slam', dur=0.22)
    return img


def segG(lt, dur, gt): return video_seg('DX6Y6PXvKG3', 4.2, lt, dur, gt, 'PRECISION', WHITE, 'zoom', 'cut')
def segH(lt, dur, gt): return video_seg('DZUfEVUPP73', 22.0, lt, dur, gt, 'CLEAN LINES', 'gold', 'whip', 'cut')
def segI(lt, dur, gt): return video_seg('DZUfEVUPP73', 24.0, lt, dur, gt, 'BOLD COLOUR', WHITE, 'zoom', 'flash')


def cut_seg(key, name, start, lt, dur, gt, live, behind, echo=False, caption=None):
    if lt < live:
        img = look(vframe(name, start, live + 0.1, start + lt), sat=0.92, con=1.12)
        img = zoom(img, 1.0 + 0.05 * lt / live)
        img = tr_in(img, lt, 'zoom')
        p = 1 - (live - lt) / 0.1
        if p > 0:
            img = zoomblur(img, 1.05 + 0.04 * p, 0.05 * p)
        return img
    lf = lt - live
    img = cutout_comp(CUT[key], lf, behind, echo)
    img = shake(img, 16 * (1 - c01(lf / 0.22)), gt)
    if lf < 0.12:
        img = to_white(img, 0.85 * (1 - lf / 0.12))
    if caption:
        hline(img, W / 2, 1488, 420 * eo((lf - 0.25) / 0.4), 3)
        anim_text(img, T(caption, MBLACK, 42, WHITE, tracking=8), W / 2, 1545, lf, 0.3, None, 'rise')
    img = tr_out(img, dur - lt, 'zoom')
    return img


def behind_red(bg, lf):
    anim_text(bg, T('SKIN', MBLACK, 92, WHITE, tracking=40, shadow=False), W / 2 - 20, 190, lf, 0.08, None, 'rise')
    lay = T('FADE', BEBAS, 500, 'gold', shadow=False)
    paste(bg, lay, W / 2 - 20 + 120 * (1 - eo(lf / 0.6)) - 30 * lf, 445, op=c01(lf / 0.12))


def segJ(lt, dur, gt):
    return cut_seg('red', 'DX6Y6PXvKG3', 10.0, lt, dur, gt, 1.0, behind_red, caption='PRECISION IN EVERY FADE')


def segK(lt, dur, gt):
    return video_seg('DWeQS8BD6XI', 11.5, lt, dur, gt, 'SILVER TONES', 'gold', 'zoom', 'whip', crop='720:870:0:0', sharp=0.7)


def segL(lt, dur, gt): return video_seg('DZUfEVUPP73', 26.6, lt, dur, gt, 'SHARP STYLING', WHITE, 'whip', 'flash')


def behind_blond(bg, lf):
    paste(bg, T('NEXT', BEBAS, 300, WHITE, shadow=False), W / 2 - 160 * (1 - eo(lf / 0.6)) + 25 * lf, 225, op=c01(lf / 0.12))
    paste(bg, T('LEVEL', BEBAS, 330, 'gold', shadow=False), W / 2 + 160 * (1 - eo(lf / 0.6)) - 25 * lf, 470, op=c01((lf - 0.08) / 0.12))


def segM(lt, dur, gt):
    return cut_seg('blond', 'DZUfEVUPP73', 11.9, lt, dur, gt, 1.0, behind_blond, echo=True, caption='COLOUR  ·  TEXTURE  ·  STYLE')


def segN(lt, dur, gt):  # before / after wipe
    before = look(vframe('DX6Y6PXvKG3', 4.8, 1.1, 4.8 + min(lt, 1.0)), sat=0.85, con=1.08)
    after = look(vframe('DX6Y6PXvKG3', 31.5, 1.6, 31.5 + max(lt - 0.5, 0)), sat=0.95, con=1.14)
    p = eio((lt - 0.55) / 0.4)
    xl = W + 120 - (W + 240) * p
    tan = math.tan(math.radians(8))
    xline = xl + (yy - H / 2) * tan
    mask = np.clip((xline - xx) / 2.0 + 0.5, 0, 1)[..., None]  # 1 = before side
    img = before * mask + after * (1 - mask)
    if 0 < p < 1:
        d = np.abs(xx - xline)
        line = np.clip(1 - (d - 3) / 2, 0, 1)[..., None]
        glowl = np.exp(-(d / 28) ** 2)[..., None] * 0.6
        img = img * (1 - line) + GOLD * line + glowl * GOLD
    img = vgrad(img, 1250, 1600, 0.55)
    img = tr_in(img, lt, 'zoom')
    img = tr_out(img, dur - lt, 'whip')
    anim_text(img, T('BEFORE', BEBAS, 190, WHITE, tracking=6), W / 2, 1420, lt, 0.05, 0.55, 'rise')
    anim_text(img, T('AFTER', BEBAS, 220, 'gold', tracking=6), W / 2, 1420, lt, 0.95, None, 'slam', dur=0.25)
    return img


def segO(lt, dur, gt):  # moody profile slow-mo + light leak
    img = look(vframe('DXT8zDtD3ph', 10.0, 1.7, 10.0 + 0.75 * lt), sat=0.9, con=1.12)
    img = zoom(img, 1.0 + 0.08 * eio(lt / dur), W * 0.55, H * 0.4)
    img = leak(img, (lt - 0.1) / 1.6, 0.3)
    img = vgrad(img, 1150, 1550, 0.55)
    img = dust(img, gt, 0.6)
    img = tr_in(img, lt, 'whip')
    img = tr_out(img, dur - lt, 'flash')
    anim_text(img, T('YOUR NEXT LOOK', BEBAS, 175, WHITE), W / 2, 1265, lt, 0.12, None, 'rise')
    anim_text(img, T('STARTS HERE', BEBAS, 175, 'gold'), W / 2, 1420, lt, 0.45, None, 'rise')
    return img


def segP(lt, dur, gt):  # rapid still montage
    names = ['corridor2', 'chairs', 'wide', 'ceilingup']
    i = min(int(lt / 0.25), 3); ll = lt - i * 0.25
    base = depth_warp(STILL[names[i]], VP[names[i]], a=0.4 * eo(ll / 0.25))
    img = cam(base, 1.2 - 0.06 * eo(ll / 0.25), (-2, 2, -1.5, 1.5)[i], 0, 0)
    img = look(img, sat=0.95, con=1.08)
    if ll < 0.06:
        img = to_white(img, 0.7 * (1 - ll / 0.06))
    return img


def segQ(lt, dur, gt):  # end card
    img = veo('wide', lt)
    if img is None:
        base = depth_warp(STILL['wide'], VP['wide'], a=0.28 * eio(lt / dur))
        img = cam(base, 1.16 - 0.04 * eio(lt / dur), 0, 0, 0)
    sig = 9 * eo(lt / 0.7)
    if sig > 0.3:
        img = cv2.GaussianBlur(img, (0, 0), sig)
    img = look(img, sat=0.9, con=1.05) * (1 - 0.62 * eo(lt / 0.7))
    img = dust(img, gt, 0.9)
    img = tr_in(img, lt, 'flash')
    top = T('TOP TOUCH', BEBAS, 280, 'gold')
    if 1.4 < lt < 2.3:
        top = shine_layer(top, (lt - 1.4) / 0.9 * 1.4 - 0.2)
    anim_text(img, top, W / 2, 740, lt, 0.12, None, 'pop', dur=0.45)
    trk = 6 + 20 * eo((lt - 0.35) / 1.5)
    anim_text(img, T('BARBERSHOP', MBLACK, 66, WHITE, tracking=round(trk)), W / 2, 905, lt, 0.35, None, 'fade', dur=0.3)
    hline(img, W / 2, 978, 540 * eo((lt - 0.5) / 0.5), 4)
    if lt > 0.7:
        pulse = 1 + 0.025 * math.sin((lt - 0.7) * 6.5) if lt > 1.2 else 1.0
        b = BTN
        if 2.2 < lt < 3.0:
            b = shine_layer(b, (lt - 2.2) / 0.8 * 1.4 - 0.2, 0.1, 0.6)
        paste(img, b, W / 2, 1110, op=c01((lt - 0.7) * 5), scale=(0.6 + 0.4 * bo((lt - 0.7) / 0.4)) * pulse)
    tl = T('SS15, SUBANG JAYA', MBOLD, 46, WHITE, tracking=3)
    ic = PIN
    gap = 22
    tot = ic[1].shape[1] + gap + tl[1].shape[1]
    x0 = W / 2 - tot / 2
    anim_text(img, ic, x0 + ic[1].shape[1] / 2, 1268, lt, 1.0, None, 'rise')
    anim_text(img, tl, x0 + ic[1].shape[1] + gap + tl[1].shape[1] / 2, 1268, lt, 1.0, None, 'rise')
    tl2 = T('@toptouchbarbershop', MBOLD, 46, WHITE, tracking=1)
    ic2 = IG
    tot2 = ic2[1].shape[1] + gap + tl2[1].shape[1]
    x1 = W / 2 - tot2 / 2
    anim_text(img, ic2, x1 + ic2[1].shape[1] / 2, 1352, lt, 1.2, None, 'rise')
    anim_text(img, tl2, x1 + ic2[1].shape[1] + gap + tl2[1].shape[1] / 2, 1352, lt, 1.2, None, 'rise')
    img = tr_out(img, dur - lt, 'black')
    return img


def segR(lt, dur, gt):  # Vyntra sign-off
    img = np.zeros((H, W, 3), np.float32)
    g = np.exp(-(((xx - W / 2) ** 2 + (yy - 860) ** 2) / (2 * 380.0 ** 2)))[..., None]
    img = img + g * np.array([0.85, 0.42, 0.08], np.float32) * (0.22 + 0.06 * math.sin(lt * 5)) * eo(lt / 0.4)
    s = 0.45 + 0.55 * bo(lt / 0.55)
    lay = rot_layer(LOGO, -25 * (1 - eo(lt / 0.55)), s * 400 / 512)
    if 0.6 < lt < 1.3:
        lay = shine_layer(lay, (lt - 0.6) / 0.7 * 1.4 - 0.2, 0.1, 0.5)
    paste(img, lay, W / 2, 860, op=c01(lt / 0.15))
    anim_text(img, T('PRODUCED BY VYNTRA', MSEMI, 36, WHITE, tracking=12), W / 2, 1150, lt, 0.45, None, 'rise', op=0.85)
    anim_text(img, T('vyntra.site', MSEMI, 32, 'gold', tracking=4), W / 2, 1215, lt, 0.6, None, 'rise')
    rem = dur - lt
    if rem < 0.2:
        img = img * eo(rem / 0.2)
    return img


BTN = button('BOOK YOUR SEAT TODAY', 760, 118, 44)
PIN = pin_icon(40)
IG = ig_icon(44)

TIMELINE = [  # (start, end, fn, label)
    (0.00, 1.75, segA, 'hook'), (1.75, 4.00, segB, 'title'), (4.00, 6.00, segC, 'luxury'),
    (6.00, 7.00, segD, 'built'), (7.00, 8.00, segE, 'comfort'), (8.00, 10.00, segF, 'premium'),
    (10.00, 11.00, segG, 'precision'), (11.00, 12.00, segH, 'lines'), (12.00, 13.00, segI, 'colour'),
    (13.00, 15.00, segJ, 'cut-red'), (15.00, 16.00, segK, 'silver'), (16.00, 17.00, segL, 'sharp'),
    (17.00, 19.00, segM, 'cut-blond'), (19.00, 21.00, segN, 'before-after'), (21.00, 23.00, segO, 'moody'),
    (23.00, 24.00, segP, 'montage'), (24.00, 28.50, segQ, 'endcard'), (28.50, 30.00, segR, 'vyntra'),
]


def render(fi):
    gt = fi / FPS
    for i, (a, b, fn, _) in enumerate(TIMELINE):
        if a <= gt < b or (i == len(TIMELINE) - 1 and gt >= a):
            break
    img = fn(gt - a, b - a, gt)
    if gt < 28.5:  # Vyntra watermark: large, centred, semi-transparent; fades out into the sign-off card
        paste(img, WM, W / 2, H / 2, op=WM_OP * (1 - c01((gt - 28.2) / 0.3)))
    img = grain(img, fi)
    return np.clip(img * 255 + 0.5, 0, 255).astype(np.uint8), i


if MODE == 'stills':
    for t in TIMES:
        fr, _ = render(int(round(t * FPS)))
        cv2.imwrite(f'{OUT}_{t:05.2f}.jpg', cv2.resize(fr, (W // 2, H // 2), interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 88])
        _clips.clear()
    print('ok')
else:
    N = int(round(TOTAL * FPS))
    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}',
                            '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '16',
                            '-pix_fmt', 'yuv420p', OUT], stdin=subprocess.PIPE)
    cur = -1
    for fi in range(N):
        fr, si = render(fi)
        if si != cur:
            _clips.clear(); cur = si
            print(f'{fi / FPS:5.2f}s  segment {si} {TIMELINE[si][3]}', flush=True)
        enc.stdin.write(fr.tobytes())
    enc.stdin.close(); enc.wait()
    print('done', OUT)
