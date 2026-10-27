"""THE STRANGER — procedural score + sound design.

Everything except the narration is synthesized here from scratch:
guitar (Karplus-Strong), whistle lead, timpani, honky-tonk piano,
wind, hooves, horse snort, rope, coat brush, boots + spurs, saloon
door creak, crowd murmur, clock, hawk cry.

Usage: python3 sound_design.py <narration.mp3> <out_dir>
Writes stems + soundtrack.wav (24 s, 48 kHz stereo).
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy import signal

SR = 48000
DUR = 24.0
N = int(SR * DUR)
T0 = 3.0  # narration start in film time
rng = np.random.default_rng(1873)


# ---------------------------------------------------------------- helpers
def secs(t):
    return int(round(t * SR))


def bus():
    return np.zeros((2, N))


def place(b, x, t, gain=1.0, pan=0.0):
    """Add mono x into stereo bus b at time t with constant-power pan."""
    i = secs(t)
    if i >= N:
        return
    x = x[: N - i]
    ang = (pan + 1) * np.pi / 4
    b[0, i : i + len(x)] += x * gain * np.cos(ang)
    b[1, i : i + len(x)] += x * gain * np.sin(ang)


def env_adsr(n, a=0.005, d=0.1, s=0.6, r=0.2):
    t = np.arange(n) / SR
    dur = n / SR
    e = np.where(t < a, t / max(a, 1e-6), 1.0)
    e = np.where((t >= a) & (t < a + d), 1 - (1 - s) * (t - a) / d, e)
    e = np.where(t >= a + d, s, e)
    rel = np.clip((dur - t) / r, 0, 1)
    return e * rel


def bp(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], btype="band", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def lp(x, f, order=2):
    sos = signal.butter(order, f, btype="low", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def hp(x, f, order=2):
    sos = signal.butter(order, f, btype="high", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def noise(n):
    return rng.standard_normal(n)


def note(name):
    names = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6,
             "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
    p, o = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((names[p] + 12 * (o + 1) - 69) / 12)


def reverb(b, seconds=2.2, wet=0.25, predelay=0.02, damp=4000):
    """Stereo convolution with decorrelated exponential noise tails."""
    n = secs(seconds)
    t = np.arange(n) / SR
    out = np.copy(b) * (1 - wet * 0.5)
    for ch in range(2):
        ir = noise(n) * np.exp(-6.9 * t / seconds)
        ir = lp(ir, damp)
        ir = np.concatenate([np.zeros(secs(predelay)), ir])
        ir /= np.sqrt(np.sum(ir ** 2))
        out[ch] += signal.fftconvolve(b[ch], ir)[:N] * wet
    return out


# ---------------------------------------------------------- instruments
def pluck(freq, dur=2.5, bright=0.5, decay=0.996):
    n = secs(dur)
    period = int(SR / freq)
    buf = lp(noise(period), 1500 + 6000 * bright, 1)
    # Karplus-Strong with averaging lowpass, vectorised one period at a time
    total = n + period + 1
    y = np.zeros(total)
    y[1 : period + 1] = buf
    for s in range(period + 1, total, period):
        e = min(s + period, total)
        y[s:e] = decay * 0.5 * (y[s - period : e - period] + y[s - period - 1 : e - period - 1])
    out = y[period + 1 :]
    # guitar body resonances
    body = bp(out, 90, 260) * 0.6 + bp(out, 380, 900) * 0.4 + out * 0.5
    return body * env_adsr(n, 0.001, 0.05, 1.0, 0.08)


def strum(chord, t, b, gain=0.35, spread=0.022, dur=3.0, down=True, pan=-0.15):
    freqs = [note(x) for x in chord]
    if not down:
        freqs = freqs[::-1]
    for k, f in enumerate(freqs):
        place(b, pluck(f, dur, 0.45), t + k * spread, gain * (0.9 + 0.2 * rng.random()), pan + 0.05 * k)


def whistle(points, t, b, gain=0.22, pan=0.12):
    """points: list of (time_offset, note_name, hold). Gliding whistle line."""
    total = points[-1][0] + points[-1][2] + 0.4
    n = secs(total)
    tt = np.arange(n) / SR
    f = np.zeros(n)
    amp = np.zeros(n)
    for k, (off, nm, hold) in enumerate(points):
        fr = note(nm)
        i0, i1 = secs(off), secs(off + hold)
        f[i0:] = fr
        # small scoop into each note
        sc = min(secs(0.06), i1 - i0)
        f[i0 : i0 + sc] = fr * (0.94 + 0.06 * np.linspace(0, 1, sc))
        a = env_adsr(i1 - i0 + secs(0.18), 0.04, 0.1, 0.85, 0.18)
        seg = slice(i0, min(n, i0 + len(a)))
        amp[seg] = np.maximum(amp[seg], a[: seg.stop - seg.start])
    f = signal.savgol_filter(f, 801, 2)
    vib = 1 + 0.012 * np.sin(2 * np.pi * 5.6 * tt) * np.clip(tt * 2, 0, 1)
    ph = 2 * np.pi * np.cumsum(f * vib) / SR
    tone = np.sin(ph) + 0.08 * np.sin(2 * ph)
    breath = bp(noise(n), 1500, 5000) * 0.03
    place(b, (tone + breath) * amp, t, gain, pan)


def timpani(freq, t, b, gain=0.6, dur=2.5):
    n = secs(dur)
    tt = np.arange(n) / SR
    f = freq * (1 + 0.15 * np.exp(-tt * 18))
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = (np.sin(ph) + 0.4 * np.sin(1.5 * ph) + 0.2 * np.sin(1.99 * ph)) * np.exp(-tt * 2.2)
    x += lp(noise(n), 400) * np.exp(-tt * 30) * 0.5
    place(b, x, t, gain, 0)


def piano_note(freq, dur=1.2, vel=1.0):
    """Detuned 'tack' piano: additive partials with slight inharmonicity."""
    n = secs(dur)
    tt = np.arange(n) / SR
    x = np.zeros(n)
    for det in (-1.6, 0.0, 1.9):  # honky-tonk detune in cents-ish Hz
        for h in range(1, 9):
            fh = freq * h * (1 + 0.0004 * h * h) + det * h * 0.6
            if fh > SR / 2.2:
                break
            x += np.sin(2 * np.pi * fh * tt) * (0.7 ** h) * np.exp(-tt * (1.6 + 0.9 * h))
    x += hp(noise(n), 2000) * np.exp(-tt * 120) * 0.25  # hammer tack
    return x * vel * 0.18 * env_adsr(n, 0.002, 0.02, 1.0, 0.06)


def wind(n, base=0.5):
    x = lp(noise(n), 900, 2) + 0.3 * bp(noise(n), 300, 2500)
    tt = np.arange(n) / SR
    gust = 0.55 + 0.45 * np.sin(2 * np.pi * 0.11 * tt + 1.3) * np.sin(2 * np.pi * 0.047 * tt)
    whistle_tone = bp(noise(n), 700, 760, 2) * 3 * np.clip(gust - 0.6, 0, 1)
    return (x * gust + whistle_tone) * base


def hoof(soft=1.0, dirt=True):
    n = secs(0.12)
    tt = np.arange(n) / SR
    thump = np.sin(2 * np.pi * (140 + 80 * np.exp(-tt * 60)) * tt) * np.exp(-tt * 45)
    click = bp(noise(n), 700, 2500) * np.exp(-tt * 90) * 0.6
    grit = bp(noise(n), 2000, 7000) * np.exp(-tt * 35) * (0.25 if dirt else 0.05)
    return (thump + click + grit) * soft


def snort(dur=0.7):
    n = secs(dur)
    tt = np.arange(n) / SR
    flutter = 0.6 + 0.4 * np.sin(2 * np.pi * 28 * tt)
    x = bp(noise(n), 250, 1800) * flutter + 0.4 * bp(noise(n), 2000, 5000)
    e = np.exp(-((tt - 0.12) ** 2) / 0.004) + 0.6 * np.exp(-((tt - 0.38) ** 2) / 0.012)
    return x * e


def swish(dur=0.22):
    n = secs(dur)
    tt = np.arange(n) / SR
    x = noise(n)
    # sweeping bandpass via short-time blend
    lo = bp(x, 800, 2500)
    hi = bp(x, 2500, 7000)
    m = tt / dur
    e = np.sin(np.pi * np.clip(m, 0, 1)) ** 2
    return (lo * (1 - m) + hi * m) * e


def boot_step(spur=True):
    n = secs(0.35)
    tt = np.arange(n) / SR
    wood = (np.sin(2 * np.pi * 95 * tt) * np.exp(-tt * 40)
            + bp(noise(n), 300, 1200) * np.exp(-tt * 55) * 0.7
            + np.sin(2 * np.pi * 420 * tt) * np.exp(-tt * 70) * 0.3)
    x = wood
    if spur:
        jingle = np.zeros(n)
        for k, f in enumerate((3120, 4410, 5230, 6170, 3870)):
            d0 = secs(0.015 * k)
            jingle[d0:] += np.sin(2 * np.pi * f * tt[: n - d0]) * np.exp(-tt[: n - d0] * 22) * 0.22
        x = x + jingle
    return x


def creak(dur=0.9, f0=180, f1=120):
    n = secs(dur)
    tt = np.arange(n) / SR
    f = np.linspace(f0, f1, n) * (1 + 0.08 * np.sin(2 * np.pi * 7 * tt))
    # stick-slip: pulse train with jittered period through resonances
    ph = np.cumsum(f) / SR
    pulses = (np.diff(np.floor(ph), prepend=0) > 0).astype(float)
    pulses *= 0.6 + 0.4 * rng.random(n)
    x = bp(pulses, 400, 900) * 2 + bp(pulses, 1200, 2600) * 1.4 + bp(pulses, 2800, 4200) * 0.5
    return x * env_adsr(n, 0.05, 0.2, 0.8, 0.25)


def door_thud():
    n = secs(0.3)
    tt = np.arange(n) / SR
    return (np.sin(2 * np.pi * 110 * tt) * np.exp(-tt * 30)
            + bp(noise(n), 200, 900) * np.exp(-tt * 40) * 0.6)


def murmur(dur):
    n = secs(dur)
    tt = np.arange(n) / SR
    x = np.zeros(n)
    for v in range(9):
        f1 = 350 + 300 * rng.random()
        f2 = 1100 + 800 * rng.random()
        voice = bp(noise(n), f1, f1 + 250) + 0.6 * bp(noise(n), f2, f2 + 400)
        rate = 3.5 + 2.5 * rng.random()
        syl = np.clip(np.sin(2 * np.pi * rate * tt + rng.random() * 6) * 1.4 - 0.2, 0, 1)
        phrase = np.clip(np.sin(2 * np.pi * (0.25 + 0.3 * rng.random()) * tt + rng.random() * 6) + 0.3, 0, 1)
        x += voice * syl * phrase
    # an occasional laugh burst
    for k in range(3):
        c = rng.random() * dur * 0.8
        x += bp(noise(n), 500, 1400) * np.clip(np.sin(2 * np.pi * 7 * tt) , 0, 1) * np.exp(-((tt - c) ** 2) / 0.05) * 1.5
    return x


def glass_clink():
    n = secs(0.6)
    tt = np.arange(n) / SR
    x = sum(np.sin(2 * np.pi * f * tt) * np.exp(-tt * d) * a
            for f, d, a in ((2630, 9, 0.5), (4120, 12, 0.35), (6890, 18, 0.2)))
    return x + hp(noise(n), 4000) * np.exp(-tt * 200) * 0.2


def clock_tick(tock=False):
    n = secs(0.12)
    tt = np.arange(n) / SR
    f = 1800 if tock else 2400
    return (np.sin(2 * np.pi * f * tt) * np.exp(-tt * 140)
            + hp(noise(n), 3000) * np.exp(-tt * 300) * 0.5
            + np.sin(2 * np.pi * 600 * tt) * np.exp(-tt * 90) * 0.4)


def hawk(dur=1.1):
    n = secs(dur)
    tt = np.arange(n) / SR
    f = 2900 - 1200 * (tt / dur) ** 0.7 + 120 * np.sin(2 * np.pi * 34 * tt)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.3 * bp(noise(n), 2000, 4500)
    x *= np.sin(2 * np.pi * 34 * tt) * 0.25 + 0.75  # raspy AM
    e = np.clip(tt / 0.05, 0, 1) * np.clip((dur - tt) / 0.5, 0, 1)
    return x * e


def drone(freq, dur, gain=1.0):
    n = secs(dur)
    tt = np.arange(n) / SR
    x = np.zeros(n)
    for det in (-0.4, 0.0, 0.5):
        ph = 2 * np.pi * (freq + det) * tt
        x += signal.sawtooth(ph) * 0.3
    x = lp(x, 700)
    trem = 0.75 + 0.25 * np.sin(2 * np.pi * 6.5 * tt)
    return x * trem * env_adsr(n, 1.2, 0.1, 1.0, 1.2) * gain


# ---------------------------------------------------------------- score
def build_music():
    m = bus()
    # Title (0-3): lone low strum, timpani, whistle theme
    timpani(note("E2"), 0.15, m, 0.55)
    strum(["E2", "B2", "E3", "G3", "B3", "E4"], 0.2, m, 0.28, spread=0.03, dur=4.0)
    whistle([(0.0, "B4", 0.3), (0.34, "E5", 0.9), (1.3, "D5", 0.2), (1.54, "B4", 0.2),
             (1.78, "G4", 0.45), (2.28, "A4", 0.22), (2.54, "B4", 0.6)], 0.3, m, 0.2)
    # Under narration (3.0-10.3): fingerpicked Em - C - Am - B7, kept soft
    timpani(note("E2"), 3.0, m, 0.4)
    beat = 60 / 84
    prog = [(["E2", "B2", "G3", "B3", "E4", "B3"], 3.0),
            (["C3", "G3", "C4", "E4", "G3", "E4"], 3.0 + 6 * beat / 2 * 1),
            (["A2", "E3", "A3", "C4", "E3", "C4"], 3.0 + 12 * beat / 2),
            (["B2", "F#3", "A3", "D#4", "F#3", "B3"], 3.0 + 18 * beat / 2)]
    for chord, start in prog:
        for k in range(6):
            nm = chord[k]
            place(m, pluck(note(nm), 2.2, 0.35), start + k * beat / 2, 0.16 * (1.15 if k == 0 else 1), -0.2 + 0.08 * k)
    # small whistle answer in the narration gap after "arrived."
    whistle([(0.0, "G4", 0.25), (0.3, "F#4", 0.25), (0.6, "E4", 0.6)], 6.95, m, 0.07)
    # Tension (10.0-12.6): low tremolo drone as he approaches the doors
    place(m, drone(note("E2"), 3.4, 0.22), 9.9, 1.0, 0)
    place(m, drone(note("F2"), 2.2, 0.08), 11.0, 1.0, 0.2)
    # Silence after the piano stops, then a slow dread drone (16.2-19.6)
    place(m, drone(note("E1") * 2, 3.8, 0.18), 16.0, 1.0, 0)
    # Finale sting (19.5-24)
    timpani(note("E2"), 19.5, m, 0.75, 3.5)
    strum(["E2", "B2", "E3", "G3", "B3", "E4"], 19.52, m, 0.4, spread=0.035, dur=4.5)
    whistle([(0.0, "B4", 0.3), (0.35, "E5", 2.4)], 19.9, m, 0.2)
    strum(["E2", "B2", "E3", "G3", "B3", "E4"], 22.3, m, 0.18, spread=0.05, dur=1.7, down=False)
    return m


def build_piano():
    """Diegetic ragtime piano 12.35 -> abrupt stop at 14.58 ("stopped")."""
    p = bus()
    bpm = 132
    b8 = 60 / bpm / 2
    start, stop = 12.35, 14.58
    # oom-pah left hand C - G7, bouncy right hand
    left = ["C3", "G3", "E3", "G3", "G2", "F3", "D3", "F3"]
    right = ["E5", "G5", "C6", "G5", "A5", "G5", "E5", "D5",
             "F5", "G5", "B5", "G5", "F5", "E5", "D5", "B4"]
    t = start
    i = 0
    while t < stop - 0.05:
        dur = min(0.9, stop - t)
        if i % 2 == 0:
            ln = left[(i // 2) % len(left)]
            place(p, piano_note(note(ln), dur, 1.0 if (i // 2) % 2 == 0 else 0.7), t, 1.0, -0.25)
        place(p, piano_note(note(right[i % len(right)]), dur, 0.8), t, 0.9, 0.2)
        t += b8
        i += 1
    # the stop: one clumsy dissonant cluster, cut dead
    cl = sum(piano_note(note(n), 0.35, 1.0) for n in ("C4", "C#4", "F#4", "G4"))
    place(p, cl, stop, 0.9, 0)
    p[:, secs(stop + 0.33):] = 0
    return p


def build_sfx():
    ext = bus()   # exterior world
    intr = bus()  # interior world
    # wind across the whole exterior, dipped inside the saloon (13.6-19.5)
    w = wind(N, 0.08)
    tt = np.arange(N) / SR
    wenv = np.interp(tt, [0, 2, 13.4, 13.7, 19.3, 19.8, 24], [0.6, 1, 1, 0.35, 0.35, 0.8, 0.5])
    ext[0] += w * wenv
    ext[1] += np.roll(w, 900) * wenv
    place(ext, hawk(), 1.0, 0.05, 0.5)
    # hooves: distant approach 3.1-7.6, slowing to a stop at the rail ~8.6
    t = 3.1
    k = 0
    while t < 8.55:
        dist = np.interp(t, [3.1, 7.6, 8.6], [0.18, 0.65, 0.8])
        step = np.interp(t, [3.1, 7.4, 8.6], [0.26, 0.26, 0.4])
        pan = np.interp(t, [3.1, 8.5], [-0.5, 0.15])
        place(ext, lp(hoof(1.0), 1500 + 5000 * dist), t + 0.02 * rng.random(), 0.35 * dist, pan)
        t += step * (1.35 if k % 4 == 3 else 0.88)
        k += 1
    place(ext, snort(), 8.75, 0.32, 0.1)
    # tack jingle + rope tying 9.0-9.9
    for k, tr in enumerate((9.0, 9.18, 9.42, 9.6, 9.78)):
        place(ext, bp(noise(secs(0.14)), 1500, 4500) * np.hanning(secs(0.14)), tr, 0.14, 0.05)
    place(ext, creak(0.5, 320, 260) * 0.4, 9.3, 0.18, 0.1)  # rope tightening on the rail
    # coat brushing 10.35-11.4 with dust puffs
    for tr in (10.4, 10.78, 11.15):
        place(ext, swish(), tr, 0.22, -0.1)
    place(ext, snort(0.5), 11.25, 0.12, 0.35)
    # boots + spurs on the boardwalk, then the saloon doors
    for k, tr in enumerate((11.72, 12.08, 12.44, 12.8, 13.14)):
        place(ext, boot_step(), tr, 0.3, -0.05 + 0.05 * (k % 2))
    place(ext, creak(1.0, 190, 120), 12.5, 0.32, -0.15)
    place(ext, creak(0.7, 160, 210), 12.6, 0.18, 0.2)
    # doors swing back behind him (heard from inside)
    place(intr, door_thud(), 13.35, 0.28, 0)
    place(intr, door_thud(), 13.8, 0.16, 0)
    place(intr, creak(0.5, 140, 120), 13.4, 0.12, 0)
    # interior crowd 12.3 -> drops out just after the piano stops
    mm = murmur(2.6)
    mm *= np.clip((2.6 - np.arange(len(mm)) / SR) / 0.25, 0, 1)
    place(intr, mm, 12.3, 0.05, 0)
    for tr, pn in ((12.9, -0.4), (13.9, 0.35)):
        place(intr, glass_clink(), tr, 0.12, pn)
    place(intr, glass_clink(), 15.2, 0.07, 0.4)  # someone sets a glass down in the silence
    # chair scrape on the turn
    place(intr, creak(0.45, 90, 70) * 0.6, 14.9, 0.1, -0.3)
    # the silence: wall clock, floorboard, a single spur step
    for k, tr in enumerate(np.arange(15.0, 19.6, 0.75)):
        place(intr, clock_tick(k % 2 == 1), tr, 0.16, 0.3)
    place(intr, creak(0.6, 110, 95), 17.2, 0.14, 0)
    place(intr, boot_step(), 18.4, 0.28, 0)
    return ext, intr


def load_narration(path):
    raw = subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
        check=True, capture_output=True).stdout
    x = np.frombuffer(raw, np.float32).astype(np.float64)
    x = hp(x, 70)
    # gentle presence + warmth
    x = x + 0.25 * bp(x, 2500, 5000) + 0.15 * bp(x, 150, 350)
    return x / np.max(np.abs(x)) * 0.9


def write_wav(path, b):
    b = np.clip(b, -1, 1)
    pcm = (b.T * 32767).astype("<i2").tobytes()
    import wave
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm)


def main():
    narr_path, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)

    narr = bus()
    place(narr, load_narration(narr_path), T0, 1.0, 0)
    narr = reverb(narr, 0.6, 0.06, damp=3000)

    music = reverb(build_music(), 2.6, 0.32)
    piano = build_piano()
    # outside the saloon the piano is muffled through the walls (cut inside at 13.6)
    tt = np.arange(N) / SR
    inside = np.clip((tt - 13.45) / 0.25, 0, 1)
    muff = np.stack([lp(piano[c], 900, 2) for c in range(2)])
    piano = reverb(piano * inside + muff * (1 - inside) * 0.55, 0.9, 0.18, damp=5000)
    ext, intr = build_sfx()
    ext = reverb(ext, 1.6, 0.12)
    intr_m = np.stack([lp(intr[c], 1200, 2) for c in range(2)])
    intr = reverb(intr * inside + intr_m * (1 - inside) * 0.6, 1.0, 0.2, damp=5000)

    # duck music under narration words
    speech = np.abs(narr[0]) + np.abs(narr[1])
    envl = lp(speech, 4)
    duck = 1 - 0.72 * np.clip(envl / (np.max(envl) * 0.25), 0, 1)

    stems = {"narration": narr, "music": music * duck * 0.8, "piano": piano * 0.4,
             "sfx_exterior": ext, "sfx_interior": intr}
    for k, v in stems.items():
        write_wav(out / f"{k}.wav", v * 0.9)
    mix = sum(stems.values())
    # fade in/out + soft limiter
    fade = np.clip(tt / 0.4, 0, 1) * np.clip((DUR - tt) / 1.6, 0, 1)
    mix = mix * fade
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)
    mix = mix / np.max(np.abs(mix)) * 0.89
    write_wav(out / "soundtrack_raw.wav", mix)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(out / "soundtrack_raw.wav"),
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", str(SR), str(out / "soundtrack.wav")],
                   check=True)
    print("ok", out / "soundtrack.wav")


if __name__ == "__main__":
    main()
