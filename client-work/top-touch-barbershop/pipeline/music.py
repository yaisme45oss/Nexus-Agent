#!/usr/bin/env python3
"""Original 120 BPM dark-trap bed for the Top Touch promo, synced to the edit.
Bars are 2.0 s (bar k starts at 2k s); impacts at 1.5 (fireball), 14 / 18 (cutout freezes), 20 (AFTER), 24 (end card)."""
import numpy as np, sys, wave
from scipy import signal

OUT = sys.argv[1]
SR = 48000; TOT = 30.0; N = int(SR * TOT)
rng = np.random.default_rng(3)
L = np.zeros(N); R = np.zeros(N)
SEND = np.zeros((2, N))          # reverb send
KENV = np.zeros(N)               # sidechain envelope from kicks
STEP = 0.125


def sos(kind, f, order=4):
    return signal.butter(order, f, btype=kind, fs=SR, output='sos')


def filt(x, kind, f, order=4):
    return signal.sosfilt(sos(kind, f, order), x)


def tt(d): return np.arange(int(SR * d)) / SR


def place(sig, t, g=1.0, pan=0.0, send=0.0):
    i = int(round(t * SR))
    if i >= N: return
    sig = sig[:N - i]
    gl, gr = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    L[i:i + len(sig)] += sig * g * gl * 1.414; R[i:i + len(sig)] += sig * g * gr * 1.414
    if send:
        SEND[0, i:i + len(sig)] += sig * g * send * gl; SEND[1, i:i + len(sig)] += sig * g * send * gr


def place_st(sl, sr_, t, g=1.0, send=0.0):
    i = int(round(t * SR)); n = min(len(sl), N - i)
    if n <= 0: return
    L[i:i + n] += sl[:n] * g; R[i:i + n] += sr_[:n] * g
    if send:
        SEND[0, i:i + n] += sl[:n] * g * send; SEND[1, i:i + n] += sr_[:n] * g * send


# ------------------------------------------------------------- instruments
def kick():
    t = tt(0.5)
    f = 46 + 120 * np.exp(-t * 32)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6.5)
    click = filt(rng.normal(0, 1, len(t)), 'highpass', 2500) * np.exp(-t * 350) * 0.35
    return np.tanh((s + click) * 1.8) * 0.9


def clap():
    t = tt(0.35); n = rng.normal(0, 1, len(t))
    env = np.zeros(len(t))
    for d in (0.0, 0.011, 0.022):
        i = int(d * SR); env[i:] += np.exp(-(t[: len(t) - i]) * 140) * 0.8
    i = int(0.03 * SR); env[i:] += np.exp(-(t[: len(t) - i]) * 14) * 0.55
    return filt(n * env, 'bandpass', [900, 3800], 2) * 1.6


def hat(open_=False):
    t = tt(0.32 if open_ else 0.06)
    n = filt(rng.normal(0, 1, len(t)), 'highpass', 7000)
    return n * np.exp(-t * (9 if open_ else 70)) * 0.5


def b808(freq, dur):
    t = tt(dur + 0.06)
    f = freq * (1 + 0.6 * np.exp(-t * 28))
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * 0.8 + 0.45 * np.sin(2 * ph) + 0.15 * np.sin(3 * ph)
    env = np.minimum(1, t / 0.004) * np.exp(-t * 0.9)
    rel = np.clip((dur + 0.06 - t) / 0.06, 0, 1)
    return np.tanh(s * 2.8) * env * rel * 0.55


def saw(f, t, ph=0.0): return 2 * ((f * t + ph) % 1) - 1


def pad(freqs, dur, cut=1300):
    t = tt(dur)
    l = np.zeros(len(t)); r = np.zeros(len(t))
    for f in freqs:
        for d, side in ((-0.11, 0), (0.0, 2), (0.12, 1)):
            v = saw(f * 2 ** (d / 12), t, rng.random())
            if side in (0, 2): l += v
            if side in (1, 2): r += v
    env = np.minimum(1, t / 0.35) * np.clip((dur - t) / 0.45, 0, 1)
    l = filt(l, 'lowpass', cut, 2) * env; r = filt(r, 'lowpass', cut, 2) * env
    return l * 0.11, r * 0.11


def bell(f, dur=1.2):
    t = tt(dur)
    mod = 2.6 * np.exp(-t * 3) * np.sin(2 * np.pi * f * 3.5 * t)
    return np.sin(2 * np.pi * f * t + mod) * np.exp(-t * 3.2) * 0.32


def noise_sweep(dur, f0, f1, shape='rise'):
    """band-limited noise whose centre moves f0->f1 (crossfaded filter bank)"""
    t = tt(dur); n = rng.normal(0, 1, len(t))
    cents = np.geomspace(150, 10000, 10)
    pos = np.log(np.geomspace(f0, f1, len(t)))
    out = np.zeros(len(t))
    for c in cents:
        band = filt(n, 'bandpass', [c / 1.5, min(c * 1.5, SR / 2 - 100)], 2)
        w = np.exp(-((pos - np.log(c)) / 0.55) ** 2)
        out += band * w
    if shape == 'rise':
        env = (t / dur) ** 2.2
    else:  # whoosh bell
        env = np.sin(np.pi * t / dur) ** 2
    return out * env


def whoosh(dur=0.45, up=True):
    a = noise_sweep(dur, 400 if up else 4000, 4500 if up else 350, 'bell') * 0.5
    return a


def impact(big=True):
    t = tt(2.4 if big else 1.2)
    f = 62 * np.exp(-t * 0.9) + 26
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * (1.6 if big else 3.5))
    crash = filt(rng.normal(0, 1, len(t)), 'lowpass', 5000) * np.exp(-t * (2.2 if big else 5))
    snap = filt(rng.normal(0, 1, len(t)), 'bandpass', [200, 2000], 2) * np.exp(-t * 30)
    return np.tanh((sub * 0.9 + crash * 0.4 + snap * 0.6) * 1.3) * (1.0 if big else 0.7)


def rev_cymbal(dur=0.9):
    t = tt(dur)
    n = filt(rng.normal(0, 1, len(t)), 'highpass', 3500)
    return n * (t / dur) ** 3 * 0.45


def tick():
    t = tt(0.05)
    return filt(rng.normal(0, 1, len(t)), 'bandpass', [2000, 6000], 2) * np.exp(-t * 120) * 0.6


# ------------------------------------------------------------- arrangement
NOTE = lambda m: 440 * 2 ** ((m - 69) / 12)
PROG = [  # (808 root midi, pad chord midis, bell notes)
    (36, [60, 63, 67], [79, 75, 72, 70]),   # Cm
    (32, [56, 60, 63], [75, 72, 68, 67]),   # Ab
    (39, [63, 67, 70], [79, 75, 70, 67]),   # Eb
    (34, [58, 62, 65], [77, 74, 70, 65]),   # Bb
]
K = kick(); CL = clap(); HC = hat(); HO = hat(True)


def drum_kick(t, g=1.0):
    place(K, t, g)
    i = int(t * SR); e = np.exp(-tt(0.35) * 9); n = min(len(e), N - i)
    if n > 0: KENV[i:i + n] = np.maximum(KENV[i:i + n], e[:n] * g)


# intro riser 0 -> 1.5
place(noise_sweep(1.5, 300, 7000) * 0.55, 0.0, 1.0, 0.0, 0.2)
rt = tt(1.5)
place(np.sin(2 * np.pi * np.cumsum(110 * 2 ** (rt / 1.5 * 2)) / SR) * (rt / 1.5) ** 2 * 0.12, 0.0)
for k in range(12):
    tk = 0.75 + k * 0.0625
    place(HC, tk, 0.25 + 0.5 * k / 12, (-0.3, 0.3)[k % 2])
place(tick(), 0.10, 0.9, -0.2, 0.3); place(tick(), 0.42, 0.9, 0.2, 0.3)
place(rev_cymbal(0.9), 0.6, 0.9, 0, 0.3)
place(impact(True), 1.5, 0.95, 0, 0.35)
place(whoosh(0.5, False), 1.55, 0.6, 0.3, 0.2)

for bar in range(1, 15):
    t0 = bar * 2.0
    if t0 >= 28.5: break
    root, chord, bells = PROG[(bar - 1) % 4]
    sec = ('intro' if bar == 1 else 'A' if bar <= 4 else 'B' if bar <= 10 else 'break' if bar == 11 else 'end')
    # pad every bar
    pl, pr = pad([NOTE(m) for m in chord], 2.05, 900 if sec in ('intro', 'break') else 1500)
    place_st(pl, pr, t0, 1.0, 0.25)
    if sec == 'intro':
        drum_kick(t0, 0.8); place(b808(NOTE(root), 1.9), t0, 0.9)
        for s in range(0, 16, 4): place(HC, t0 + s * STEP, 0.3, 0.25)
        continue
    if sec == 'break':  # moody: no kick, 808 + build roll into the end card
        place(b808(NOTE(root), 1.0), t0, 0.8)
        for s in range(4, 16):
            sub = 2 if s >= 12 else 1
            for q in range(sub):
                place(CL, t0 + s * STEP + q * STEP / 2, 0.15 + 0.5 * (s - 4) / 12, 0, 0.2)
        place(noise_sweep(1.0, 400, 9000) * 0.5, t0 + 1.0, 1.0, 0, 0.2)
        place(rev_cymbal(0.7), t0 + 1.3, 0.9)
        continue
    kicks = [0, 10] if sec in ('A', 'end') else [0, 3, 10, 11]
    for s in kicks:
        drum_kick(t0 + s * STEP, 1.0 if s in (0, 10) else 0.8)
    place(CL, t0 + 8 * STEP, 0.9, 0, 0.25)
    if sec == 'B' and bar % 2 == 0:
        place(CL, t0 + 15 * STEP, 0.35, 0, 0.2)
    # hats
    if sec in ('A', 'end'):
        for s in range(0, 16, 2): place(HC, t0 + s * STEP, 0.45 if s % 4 == 0 else 0.3, 0.25)
        place(HO, t0 + 14 * STEP, 0.35, -0.25)
    else:
        for s in range(16):
            if bar % 2 == 1 and s >= 12:   # triplet-ish roll
                for q in range(3): place(HC, t0 + s * STEP + q * STEP / 3, 0.28, 0.25 - 0.1 * q)
            else:
                place(HC, t0 + s * STEP, 0.42 if s % 2 == 0 else 0.22, 0.25)
        place(HO, t0 + 6 * STEP, 0.3, -0.25); place(HO, t0 + 14 * STEP, 0.3, -0.25)
    # 808
    place(b808(NOTE(root), 1.15), t0, 0.95)
    place(b808(NOTE(root), 0.6), t0 + 10 * STEP, 0.85)
    if sec == 'B':
        place(b808(NOTE(root + 12), 0.25), t0 + 3 * STEP, 0.55)
    # bells
    for j, s in enumerate((0, 3, 6, 10)):
        place(bell(NOTE(bells[j])), t0 + s * STEP, 0.55 if sec != 'end' else 0.45, (-0.4, 0.4, -0.2, 0.3)[j], 0.45)

# accents synced to picture
for t, big in ((14.0, False), (18.0, False), (20.0, False), (24.0, True)):
    place(impact(big), t, 0.8 if not big else 0.95, 0, 0.35)
for t in (4.0, 7.0, 10.0, 12.0, 15.0, 19.0, 23.0):
    place(whoosh(0.4, True), t - 0.2, 0.35, (-0.5, 0.5)[int(t) % 2], 0.15)
for t in (6.0, 11.0, 16.0, 21.0):          # whip pans
    place(whoosh(0.3, False), t - 0.15, 0.45, 0.6, 0.1)
place(whoosh(0.5, True), 19.5, 0.5, -0.6, 0.15)  # before/after wipe
for k in range(4):                           # montage flashes 23-24
    place(tick(), 23.0 + k * 0.25, 0.8, (-0.3, 0.3)[k % 2], 0.3)
# outro shimmer + final sub
for m, d in ((84, 0.0), (79, 0.06), (75, 0.12), (72, 0.18)):
    place(bell(NOTE(m), 1.5), 28.5 + d, 0.5, (m % 3 - 1) * 0.4, 0.6)
pl, pr = pad([NOTE(60), NOTE(63), NOTE(67), NOTE(72)], 1.5, 2200)
place_st(pl, pr, 28.5, 0.6, 0.4)
place(b808(NOTE(36), 1.4), 28.5, 0.55)

# ------------------------------------------------------------- mix
# sidechain duck everything except kicks/impacts is approximated by ducking the pad/808 bus lightly
duck = 1 - 0.28 * KENV
L *= duck; R *= duck
ir_t = tt(1.6)
for ch, sig in ((0, L), (1, R)):
    ir = rng.normal(0, 1, len(ir_t)) * np.exp(-ir_t * 3.2)
    ir = filt(ir, 'lowpass', 6000, 2); ir /= np.sqrt(np.sum(ir ** 2))
    wet = signal.fftconvolve(SEND[ch], ir)[:N] * 0.55
    sig += wet
mix = np.stack([L, R])
mix = signal.sosfilt(sos('highpass', 38, 4), mix, axis=1)
mix = mix + signal.sosfilt(sos('bandpass', [2500, 6000], 2), mix, axis=1) * 0.25  # presence lift
mix = mix * (1.05 / np.max(np.abs(mix)))  # gain-stage into a gentle soft clip
mix = np.tanh(mix * 1.15) / np.tanh(1.15)
fade = np.ones(N); fl = int(0.35 * SR); fade[-fl:] = np.linspace(1, 0, fl) ** 2
mix *= fade
mix *= 0.89 / np.max(np.abs(mix))
pcm = (mix.T * 32767).astype('<i2')
with wave.open(OUT, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print('wrote', OUT, f'{N / SR:.1f}s', 'rms', float(np.sqrt(np.mean(mix ** 2))))
