"""Procedural score + SFX for "Amerika Tarihi — 15 Saniye".

Everything is synthesized from scratch with numpy/scipy — no samples, no APIs.
Timeline: 6 scenes x 2.5 s at 96 BPM (one 4/4 bar per scene).
Outputs music.wav, sfx.wav and mix.wav (48 kHz stereo) next to this file.
"""
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

SR = 48000
DUR = 15.0
N = int(SR * DUR)
BEAT = 60 / 96  # 0.625 s
rng = np.random.default_rng(1776)
OUT = Path(__file__).resolve().parent


def t_arr(d):
    return np.arange(int(d * SR)) / SR


def lp(x, fc, order=2):
    return sosfilt(butter(order, fc, "low", fs=SR, output="sos"), x)


def hp(x, fc, order=2):
    return sosfilt(butter(order, fc, "high", fs=SR, output="sos"), x)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "band", fs=SR, output="sos"), x)


def adsr(n, a=0.01, d=0.1, s=0.7, r=0.1):
    env = np.full(n, s)
    ai, di, ri = int(a * SR), int(d * SR), int(r * SR)
    ai = min(ai, n)
    env[:ai] = np.linspace(0, 1, ai)
    de = min(ai + di, n)
    env[ai:de] = np.linspace(1, s, de - ai)
    if ri and n > ri:
        env[-ri:] *= np.linspace(1, 0, ri)
    return env


def place(buf, sig, start, gain=1.0, pan=0.0):
    i = int(start * SR)
    if i >= len(buf):
        return
    sig = sig[: len(buf) - i]
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[i : i + len(sig), 0] += sig * gain * l * np.sqrt(2)
    buf[i : i + len(sig), 1] += sig * gain * r * np.sqrt(2)


def midi(m):
    return 440 * 2 ** ((m - 69) / 12)


def saw(f, t, detune=0.0):
    ph = (f * (1 + detune)) * t
    return 2 * (ph - np.floor(ph + 0.5))


# ---------------------------------------------------------------- music ----
def pad_chord(notes, d):
    t = t_arr(d)
    sig = sum(saw(midi(n), t, dt) for n in notes for dt in (-0.004, 0.0, 0.0045))
    sig = lp(sig / (len(notes) * 3), 1400)
    return sig * adsr(len(t), a=0.35, d=0.2, s=0.85, r=0.4)


def brass(note, d):
    t = t_arr(d)
    f = midi(note)
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.2 * t) * np.clip(t * 3, 0, 1)
    ph = np.cumsum(f * vib) / SR
    raw = 2 * (ph - np.floor(ph + 0.5))
    # brightness opens with the attack, like a real horn
    bright = lp(raw, 900) * 0.6 + lp(raw, 2600) * 0.4 * np.clip(t * 8, 0, 1)
    return bright * adsr(len(t), a=0.04, d=0.15, s=0.75, r=0.12)


def timpani(note, d=1.2):
    t = t_arr(d)
    f = midi(note) * (1 + 0.06 * np.exp(-t * 30))
    ph = np.cumsum(f) / SR
    body = np.sin(2 * np.pi * ph) + 0.35 * np.sin(2 * np.pi * 1.5 * ph)
    thump = lp(rng.standard_normal(len(t)), 300) * np.exp(-t * 40) * 0.6
    return (body * np.exp(-t * 3.2) + thump) * 0.9


def snare(d=0.25, amp=1.0):
    t = t_arr(d)
    noise = bp(rng.standard_normal(len(t)), 1500, 7000) * np.exp(-t * 22)
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 35)
    return (noise * 0.8 + tone * 0.5) * amp


def glock(note, d=1.0):
    t = t_arr(d)
    f = midi(note)
    s = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 8)
    return s * np.exp(-t * 3.5)


music = np.zeros((N, 2))

# One chord per half-bar (2 beats). D major; scene 3 turns minor for the war.
chords = [
    ([50, 57, 62, 66], [50, 57, 62, 66]),  # S1 1492  D | D
    ([55, 59, 62, 67], [50, 57, 62, 66]),  # S2 1776  G | D
    ([47, 54, 59, 62], [54, 57, 61, 66]),  # S3 1863  Bm | F#
    ([55, 59, 62, 67], [57, 61, 64, 69]),  # S4 1869  G | A
    ([52, 59, 64, 67], [57, 61, 64, 67]),  # S5 1969  Em | A7
    ([50, 57, 62, 66], [50, 57, 62, 66]),  # S6 2026  D | D
]
for si, (c1, c2) in enumerate(chords):
    s0 = si * 4 * BEAT
    place(music, pad_chord(c1, 2 * BEAT + 0.15), s0, 0.32, -0.3)
    place(music, pad_chord(c2, 2 * BEAT + 0.15 if si < 5 else 3.0), s0 + 2 * BEAT, 0.32, 0.3)
    # bass doubles chord root an octave down
    for k, c in enumerate((c1, c2)):
        t = t_arr(2 * BEAT)
        b = lp(saw(midi(c[0] - 12), t), 400) * adsr(len(t), 0.02, 0.2, 0.6, 0.1)
        place(music, b, s0 + k * 2 * BEAT, 0.35)

# Original fanfare melody (beats, midi, length in beats); starts quiet, grows.
melody = [
    # S1 — a lone horn calls across the sea
    (2, 69, 1), (3, 74, 1),
    # S2 — declaration
    (4, 74, 1.5), (5.5, 76, 0.5), (6, 78, 1), (7, 74, 1),
    # S3 — minor, insistent
    (8, 71, 1), (9, 71, 0.5), (9.5, 73, 0.5), (10, 73, 1.5), (11.5, 69, 0.5),
    # S4 — rising with the rails
    (12, 71, 0.5), (12.5, 74, 0.5), (13, 79, 1), (14, 76, 1), (15, 81, 1),
    # S5 — reaching for the moon
    (16, 79, 1), (17, 83, 1), (18, 81, 1), (19, 85, 1),
    # S6 — home: resolve on D
    (20, 86, 2.0), (22, 81, 0.5), (22.5, 83, 0.5), (23, 86, 1.6),
]
for beat, note, length in melody:
    g = 0.11 + 0.06 * (beat / 24)
    place(music, brass(note - 12, length * BEAT + 0.05), beat * BEAT, g, 0.15)
    if beat >= 16:  # octave double for the finale
        place(music, brass(note, length * BEAT + 0.05), beat * BEAT, g * 0.45, -0.15)

# Timpani on every downbeat, bigger toward the end.
for bar in range(6):
    place(music, timpani(38 if bar % 2 == 0 else 45), bar * 4 * BEAT, 0.35 + 0.05 * bar)
place(music, timpani(38, 2.5), 23 * BEAT, 0.55)

# Military snare during the war and railroad bars, roll into the finale.
for b in range(8, 16):
    place(music, snare(amp=0.8), b * BEAT, 0.22)
    place(music, snare(amp=0.5), (b + 0.5) * BEAT, 0.14)
    if b < 12:
        place(music, snare(amp=0.35), (b + 0.75) * BEAT, 0.12)
for k in range(24):  # roll building into 2026
    place(music, snare(0.12, 0.25 + k / 40), 19 * BEAT + k * BEAT / 24, 0.12)

# Glockenspiel sparkle for 2026.
for k, n in enumerate([86, 90, 93, 98, 93, 98]):
    place(music, glock(n), 20 * BEAT + k * BEAT / 2, 0.08, (-1) ** k * 0.4)

# ------------------------------------------------------------------ sfx ----
sfx = np.zeros((N, 2))


def whoosh(d=0.5):
    t = t_arr(d)
    n = rng.standard_normal(len(t))
    sweep = np.linspace(400, 4000, len(t))
    out = np.zeros_like(n)
    # crude time-varying band-pass via short blocks
    blk = 1024
    for i in range(0, len(n), blk):
        f = sweep[i]
        out[i : i + blk] = bp(n[i : i + blk + 0], f * 0.6, min(f * 1.6, SR / 2 - 100), 1)
    return out * np.sin(np.pi * t / d) ** 2


def gull(d=0.35):
    t = t_arr(d)
    f = 1600 + 900 * np.sin(np.pi * t / d) - 600 * t / d
    ph = np.cumsum(f) / SR
    s = np.sin(2 * np.pi * ph) + 0.4 * np.sin(4 * np.pi * ph)
    return lp(s, 4000) * np.sin(np.pi * t / d) * 0.5


def bell(f0=220, d=2.6):
    t = t_arr(d)
    partials = [(0.5, 1.0, 1.2), (1.0, 0.8, 1.8), (1.19, 0.5, 2.2), (1.56, 0.4, 2.8),
                (2.0, 0.5, 3.2), (2.51, 0.3, 4.0), (3.01, 0.2, 5.0)]
    s = sum(a * np.sin(2 * np.pi * f0 * r * t) * np.exp(-t * dec) for r, a, dec in partials)
    s += np.sin(2 * np.pi * f0 * 1.003 * t) * np.exp(-t * 1.5) * 0.4  # beating
    strike = bp(rng.standard_normal(len(t)), 2000, 8000) * np.exp(-t * 80) * 0.6
    return (s + strike) * 0.35


def scratch(d=0.18):
    t = t_arr(d)
    n = bp(rng.standard_normal(len(t)), 3000, 9000)
    grain = (rng.random(len(t)) > 0.6).astype(float)
    return n * lp(grain, 200) * np.sin(np.pi * t / d)


def cannon(d=1.8):
    t = t_arr(d)
    n = rng.standard_normal(len(t))
    boom = lp(n, 140, 3) * np.exp(-t * 2.5) * 4
    crack = bp(n, 300, 3000) * np.exp(-t * 18)
    sub = np.sin(2 * np.pi * (45 * t - 10 * t**2)) * np.exp(-t * 3)
    return np.tanh((boom + crack + sub) * 1.4) * 0.8


def chuff(d=0.3):
    t = t_arr(d)
    return bp(rng.standard_normal(len(t)), 250, 2500) * np.exp(-t * 14) * (1 - np.exp(-t * 300))


def whistle(d=0.9):
    t = t_arr(d)
    env = adsr(len(t), 0.05, 0.1, 0.9, 0.3)
    s = sum(np.sin(2 * np.pi * f * t) for f in (587, 740, 880)) / 3
    breath = bp(rng.standard_normal(len(t)), 500, 1200) * 0.15
    return (s + breath) * env * 0.6


def beep(f=1000, d=0.12):
    t = t_arr(d)
    return np.sin(2 * np.pi * f * t) * adsr(len(t), 0.003, 0.02, 0.8, 0.02) * 0.5


def rumble(d):
    t = t_arr(d)
    n = rng.standard_normal(len(t))
    r = lp(n, 220, 3) * 3 + bp(n, 400, 2500) * 0.4 * np.clip(t / 0.8, 0, 1)
    mod = 1 + 0.25 * lp(rng.standard_normal(len(t)), 8) * 10
    env = np.clip(t / 0.5, 0, 1) * np.clip((d - t) / 0.4, 0, 1)
    return np.tanh(r * mod * env)


def firework(d=1.4):
    t = t_arr(d)
    n = rng.standard_normal(len(t))
    pop = lp(n, 900) * np.exp(-t * 25) * 2.5
    crackle = np.zeros(len(t))
    for _ in range(70):
        i = int(rng.uniform(0.12, d - 0.05) * SR)
        L = int(0.006 * SR)
        crackle[i : i + L] += rng.standard_normal(L) * np.exp(-np.arange(L) / (L / 4))
    crackle = hp(crackle, 2500) * np.exp(-t * 2.2) * 0.8
    return np.tanh(pop + crackle)


def cymbal_swell(d=1.5):
    t = t_arr(d)
    return hp(rng.standard_normal(len(t)), 5000) * (t / d) ** 2.5 * 0.5


# S1 1492 — ocean waves + gulls
t = t_arr(2.7)
waves = lp(rng.standard_normal(len(t)), 700) * (0.55 + 0.45 * np.sin(2 * np.pi * 0.55 * t - 1.2))
waves += hp(rng.standard_normal(len(t)), 3000) * 0.08 * (0.5 + 0.5 * np.sin(2 * np.pi * 0.55 * t - 1.0))
waves *= np.clip(t / 0.3, 0, 1) * np.clip((2.7 - t) / 0.5, 0, 1)
place(sfx, waves, 0.0, 0.35, -0.2)
place(sfx, gull(), 0.6, 0.12, 0.6)
place(sfx, gull(0.28), 1.3, 0.09, 0.4)

# Transitions between scenes
for k in range(1, 6):
    place(sfx, whoosh(0.45), k * 2.5 - 0.3, 0.16, (-1) ** k * 0.5)

# S2 1776 — quill writing, then the Liberty Bell
for i in range(6):
    place(sfx, scratch(rng.uniform(0.1, 0.22)), 2.75 + i * 0.16, 0.22, -0.3)
place(sfx, bell(), 3.9, 0.55, 0.2)

# S3 1863 — cannons
place(sfx, cannon(), 5.45, 0.6, -0.5)
place(sfx, cannon(), 6.55, 0.5, 0.5)

# S4 1869 — steam train
for i in range(9):
    place(sfx, chuff(), 7.6 + i * BEAT / 2.0 * (1 - i * 0.03), 0.28, 0.2)
place(sfx, whistle(), 8.35, 0.32, -0.2)

# S5 1969 — countdown, liftoff
for i, f in enumerate((880, 880, 880, 1320)):
    place(sfx, beep(f, 0.1 if i < 3 else 0.2), 10.1 + i * 0.3, 0.3)
place(sfx, rumble(2.3), 10.95, 0.55)

# S6 2026 — fireworks
for tt, pan in ((12.75, -0.6), (13.2, 0.5), (13.6, -0.1), (14.0, 0.7)):
    place(sfx, firework(), tt, 0.32, pan)
place(sfx, cymbal_swell(1.4), 12.6, 0.35)


# ------------------------------------------------------------------ mix ----
def norm(x, peak=0.89):
    return x / (np.max(np.abs(x)) + 1e-9) * peak


def fade(x):
    f = int(0.4 * SR)
    x[-f:] *= np.linspace(1, 0, f)[:, None]
    x[: int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))[:, None]
    return x


music = fade(music)
sfx = fade(sfx)
mix = np.tanh(norm(music, 0.6) * 1.1 + norm(sfx, 0.7))
mix = norm(fade(mix), 0.92)

for name, data in (("music", norm(music)), ("sfx", norm(sfx)), ("mix", mix)):
    wavfile.write(OUT / f"{name}.wav", SR, (data * 32767).astype(np.int16))
    print("wrote", OUT / f"{name}.wav")
