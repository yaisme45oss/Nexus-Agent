"""Synthesize a 27s, 120 BPM soundtrack with SFX synced to the KabinKu reel timeline."""
import sys
import numpy as np
from scipy.signal import butter, lfilter, sosfilt, fftconvolve
from scipy.io import wavfile

SR = 44100
DUR = 27.0
N = int(SR * DUR)
rs = np.random.default_rng(7)
L = np.zeros(N); R = np.zeros(N)          # dry bus
RL = np.zeros(N); RR = np.zeros(N)        # reverb send
DUCKED_L = np.zeros(N); DUCKED_R = np.zeros(N)  # sidechained bus

def mtof(m): return 440.0 * 2 ** ((m - 69) / 12)
def env_exp(n, tau): return np.exp(-np.arange(n) / (tau * SR))
def place(bufL, bufR, sig, t, gain=1.0, pan=0.0):
    i = int(round(t * SR))
    if i >= N: return
    sig = sig[: N - i]
    gl = gain * np.sqrt(0.5 * (1 - pan)); gr = gain * np.sqrt(0.5 * (1 + pan))
    bufL[i:i + len(sig)] += sig * gl; bufR[i:i + len(sig)] += sig * gr
def hp(x, f, o=2): return sosfilt(butter(o, f, 'hp', fs=SR, output='sos'), x)
def lp(x, f, o=2): return sosfilt(butter(o, f, 'lp', fs=SR, output='sos'), x)
def bp(x, lo, hi, o=2): return sosfilt(butter(o, [lo, hi], 'bp', fs=SR, output='sos'), x)
def saw(f, n, phase=0.0):
    t = np.arange(n) / SR
    out = np.zeros(n)
    k = 1
    while k * f < 12000 and k <= 40:   # band-limited additive saw
        out += np.sin(2 * np.pi * k * f * t + phase * k) / k
        k += 1
    return out * 0.6

# ---------------- instruments ----------------
def kick():
    n = int(0.45 * SR); t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * env_exp(n, 0.16)
    s[:200] += rs.uniform(-1, 1, 200) * np.linspace(.6, 0, 200)
    return np.tanh(s * 1.6) * 0.95
def clap():
    n = int(0.3 * SR); s = np.zeros(n)
    noise = bp(rs.uniform(-1, 1, n), 900, 3500)
    for d in (0, 0.011, 0.022):
        i = int(d * SR); e = env_exp(n - i, 0.008 if d < .02 else 0.07)
        s[i:] += noise[: n - i] * e
    return s * 1.2
def hat(open_=False):
    n = int((0.25 if open_ else 0.06) * SR)
    s = hp(rs.uniform(-1, 1, n), 7000) * env_exp(n, 0.07 if open_ else 0.014)
    return s
def impact():
    n = int(1.8 * SR); t = np.arange(n) / SR
    f = 30 + 70 * np.exp(-t * 5)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(n, 0.55)
    nz = lp(rs.uniform(-1, 1, n), 1800) * env_exp(n, 0.12)
    return np.tanh((sub * 1.2 + nz * 0.7) * 1.3)
def whoosh(dur=0.45, lo=300, hi=5000, rise=True):
    n = int(dur * SR); x = rs.uniform(-1, 1, n); out = np.zeros(n)
    blk = 512; zi = None
    for i in range(0, n, blk):
        p = i / n; p = p if rise else 1 - p
        fc = lo * (hi / lo) ** p
        b, a = butter(2, [fc * 0.7, min(fc * 1.4, SR / 2 - 100)], 'bp', fs=SR)
        if zi is None: zi = np.zeros(max(len(a), len(b)) - 1)
        y, zi = lfilter(b, a, x[i:i + blk], zi=zi); out[i:i + blk] = y
    e = np.sin(np.pi * np.linspace(0, 1, n)) ** 2
    e = e * (np.linspace(0.3, 1, n) if rise else 1)
    return out * e * 2.2
def riser(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 180 * (8 ** (t / dur))
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.25
    return (whoosh(dur, 400, 9000) * 0.8 + tone) * np.linspace(0, 1, n) ** 2
def blip(f0=900, f1=1500, dur=0.09):
    n = int(dur * SR); t = np.arange(n) / SR
    f = f0 + (f1 - f0) * np.minimum(t / 0.03, 1)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(n, dur / 3)
def ding(f=1760):
    n = int(0.6 * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.5 * t) + .25 * np.sin(2 * np.pi * f * 2.01 * t)) * env_exp(n, 0.12) * 0.5
def tick():
    n = int(0.02 * SR); return hp(rs.uniform(-1, 1, n), 3000) * env_exp(n, 0.003)
def pluck(m, dur=0.35):
    n = int(dur * SR); f = mtof(m)
    s = saw(f, n) * env_exp(n, 0.09)
    return lp(s, 3200)
def pad_chord(ms, dur, cutoff=1800):
    n = int(dur * SR); sl = np.zeros(n); sr_ = np.zeros(n)
    for m in ms:
        f = mtof(m)
        sl += saw(f * 0.997, n, 0.3); sr_ += saw(f * 1.003, n, 1.1)
    a = np.minimum(np.arange(n) / (0.04 * SR), 1) * np.minimum((n - np.arange(n)) / (0.08 * SR), 1)
    return lp(sl, cutoff) * a / len(ms), lp(sr_, cutoff) * a / len(ms)
def bass_note(m, dur):
    n = int(dur * SR); f = mtof(m)
    s = saw(f, n) * 0.7 + np.sin(2 * np.pi * f / 2 * np.arange(n) / SR) * 0.8
    a = np.minimum(np.arange(n) / 80, 1) * env_exp(n, 0.25) * 0.6 + 0.4 * np.minimum(np.arange(n) / 80, 1)
    a *= np.minimum((n - np.arange(n)) / 300, 1)
    return np.tanh(lp(s, 700) * a * 1.4)

BEAT = 0.5; BAR = 2.0
CH = {'C': [60, 64, 67, 72], 'G': [59, 62, 67, 71], 'Am': [60, 64, 69, 72], 'F': [60, 65, 69, 72]}
BASS = {'C': 36, 'G': 43, 'Am': 45, 'F': 41}
PROG = ['C', 'G', 'Am', 'F']

K = kick(); CL = clap(); HC = hat(); HO = hat(True)
kick_times = []

# ---------------- arrangement ----------------
# Intro 0-2: filtered pad (F->G feel), ticking hats, blips on word changes, riser
pl, pr = pad_chord(CH['F'], 1.0, 700); place(DUCKED_L, DUCKED_R, pl, 0.0, .5); place(DUCKED_L, DUCKED_R, pr, 0.0, .5)
pl, pr = pad_chord(CH['G'], 1.0, 1100); place(DUCKED_L, DUCKED_R, pl, 1.0, .55); place(DUCKED_L, DUCKED_R, pr, 1.0, .55)
for i in range(16):
    place(L, R, HC, i * 0.125, 0.12 + 0.012 * i, 0.3)
place(L, R, K, 0.04, 0.55)
for k, t in enumerate([0.42, 0.80, 1.18, 1.56]):
    place(L, R, blip(700 + 120 * k, 1300 + 160 * k), t, 0.33, -0.2 + 0.13 * k)
    place(RL, RR, blip(700 + 120 * k, 1300 + 160 * k), t, 0.2)
place(L, R, riser(1.0), 1.0, 0.5)

# Main groove 2.0 - 26.0 (CTA bars 23-26 lighter)
for bar in range(12):
    t0 = 2.0 + bar * BAR
    if t0 >= 26.0: break
    ch = PROG[bar % 4]
    lightcta = t0 >= 23.0
    breakdown = 22.0 <= t0 < 23.0
    # pads (sidechained)
    pl, pr = pad_chord(CH[ch], BAR, 2400 if not lightcta else 1600)
    place(DUCKED_L, DUCKED_R, pl, t0, .55); place(DUCKED_L, DUCKED_R, pr, t0, .55)
    for b in range(4):
        tb = t0 + b * BEAT
        if tb >= 26.0: break
        if not (breakdown and b >= 2):
            place(L, R, K, tb, 0.9); kick_times.append(tb)
        if b in (1, 3) and not breakdown:
            place(L, R, CL, tb, 0.42, 0.05); place(RL, RR, CL, tb, 0.25)
        place(L, R, HO, tb + 0.25, 0.16 if not lightcta else 0.1, 0.35)
        for s16 in range(4):
            place(L, R, HC, tb + s16 * .125, 0.07, -0.3)
        # bass on 8ths, root + octave on offbeat
        for e8 in range(2):
            m = BASS[ch] + (12 if e8 == 1 else 0)
            place(DUCKED_L, DUCKED_R, bass_note(m, 0.24), tb + e8 * .25, 0.42 if not lightcta else 0.3)
    # pluck arp from 4.0, 16ths
    if t0 >= 4.0:
        tones = CH[ch]
        for s in range(16):
            ts = t0 + s * .125
            if ts >= 26.0: break
            m = tones[[0, 1, 2, 3, 2, 1, 3, 2][s % 8]] + 12
            g = 0.13 if not lightcta else 0.09
            pan = -0.45 if s % 2 == 0 else 0.45
            place(L, R, pluck(m), ts, g, pan); place(RL, RR, pluck(m), ts, g * .6)

# snare/clap roll build 22.0 -> 23.0
for i in range(16):
    tt = 22.0 + i * (1.0 / 16)
    place(L, R, CL, tt, 0.12 + 0.25 * i / 15, 0)
place(L, R, riser(1.0), 22.0, 0.55)

# final chord hit 26.0 -> 27.0
pl, pr = pad_chord(CH['C'] + [48], 1.0, 2600)
fade = np.linspace(1, 0, len(pl)) ** 1.5
place(L, R, pl * fade, 26.0, .7); place(L, R, pr * fade, 26.0, .7)
place(RL, RR, (pl + pr) * fade, 26.0, .4)
place(L, R, K, 26.0, 0.9); place(L, R, impact() * 0.5, 26.0, 0.5)

# ---------------- SFX synced to picture ----------------
place(L, R, impact(), 2.0, 0.85)                          # cabin lands
place(RL, RR, impact(), 2.0, 0.25)
for t in (3.25, 7.22, 11.72, 15.95, 19.4, 22.7):          # transitions
    w = whoosh(0.5, 250, 6000)
    place(L, R, w, t, 0.32, -0.3); place(L, R, whoosh(0.5, 300, 7000), t + .01, 0.32, 0.3)
for t in (4.0, 4.5, 5.0):                                  # reason rows
    place(L, R, blip(500, 1100, .1), t, 0.28); place(RL, RR, blip(500, 1100, .1), t, 0.15)
for t in (7.5, 8.5, 9.5, 10.5):                            # card swipes
    place(L, R, whoosh(0.28, 900, 7000), t - 0.06, 0.22, 0.4)
for t in (12.4, 12.9, 13.4, 13.9):                         # process steps
    place(L, R, blip(600, 900, .08), t, 0.25)
for k, t in enumerate((14.35, 14.45, 14.55, 14.65)):       # checkmarks
    place(L, R, ding(1568 * 2 ** (k * 2 / 12)), t, 0.16, -0.3 + .2 * k); place(RL, RR, ding(1568 * 2 ** (k * 2 / 12)), t, 0.12)
for t in (16.75, 17.0, 17.25):                             # dimension lines
    place(L, R, whoosh(0.4, 2000, 9000), t, 0.12)
    for j in range(8): place(L, R, tick(), t + 0.25 + j * 0.06, 0.12)
for t in (17.65, 17.9, 18.15):                             # chips
    place(L, R, blip(800, 1200, .07), t, 0.18)
tt = 19.85                                                 # year slot roll ratchet
while tt < 20.75:
    place(L, R, tick(), tt, 0.22, rs.uniform(-.3, .3)); tt += 0.025 + 0.09 * ((tt - 19.85) / 0.9) ** 2
place(L, R, ding(2093), 20.75, 0.18)
for t in (20.75, 20.88, 21.01): place(L, R, blip(700, 1000, .06), t, 0.18)
place(L, R, whoosh(0.5, 400, 5000), 20.95, 0.25)            # tapes
place(L, R, impact(), 23.0, 0.8)                           # CTA hit
place(L, R, blip(500, 1400, .12), 24.1, 0.35); place(RL, RR, ding(2349), 24.15, 0.25)
place(L, R, ding(2637), 24.18, 0.12, .4)
place(L, R, whoosh(0.6, 2000, 10000), 25.3, 0.12)          # shine

# ---------------- mix ----------------
# sidechain envelope from kick times
sc = np.ones(N)
for kt in kick_times:
    i = int(kt * SR); n = int(0.42 * SR)
    seg = 1 - 0.65 * np.exp(-np.arange(n) / (0.09 * SR))
    j = min(N, i + n); sc[i:j] = np.minimum(sc[i:j], seg[: j - i])
L += DUCKED_L * sc; R += DUCKED_R * sc
RL += (DUCKED_L * sc) * 0.3; RR += (DUCKED_R * sc) * 0.3
# reverb: decaying noise IR
irn = int(1.3 * SR)
ir_l = rs.normal(0, 1, irn) * env_exp(irn, 0.35); ir_r = rs.normal(0, 1, irn) * env_exp(irn, 0.35)
ir_l = lp(ir_l, 6000); ir_r = lp(ir_r, 6000)
ir_l /= np.sqrt(np.sum(ir_l ** 2)); ir_r /= np.sqrt(np.sum(ir_r ** 2))
L += fftconvolve(hp(RL, 250), ir_l)[:N] * 0.35
R += fftconvolve(hp(RR, 250), ir_r)[:N] * 0.35
mix = np.stack([L, R], 1)
mix = hp(mix.T, 30).T
mix = np.tanh(mix / np.max(np.abs(mix)) * 1.6) * 0.89
fadeout = np.ones(N); fo = int(0.25 * SR); fadeout[-fo:] = np.linspace(1, 0, fo)
mix *= fadeout[:, None]
wavfile.write(sys.argv[1], SR, (mix * 32767).astype(np.int16))
print('wrote', sys.argv[1], mix.shape, 'peak', np.abs(mix).max())
