"""Original synthesized score, diegetic saloon piano, ambience, foley and final mix.
Everything here is generated from code (no samples, no external music). Output:
  audio/stems/*.wav and audio/final_mix.wav (48 kHz, stereo, 24-bit)
The supplied ElevenLabs narration is used unchanged (no time-stretch, pitch or edit), unity gain."""
import json
import math
import os
import sys

import numpy as np
import soundfile as sf
from scipy import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import music  # noqa: E402
from timeline import PIANO_STOP, SHOTS, VIDEO_DURATION  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = 48000
N = int(VIDEO_DURATION * SR)
rng = np.random.default_rng(1880)
tt = np.arange(N) / SR
STEMS = os.path.join(ROOT, "audio", "stems")
os.makedirs(STEMS, exist_ok=True)


def db(x):
    return 10 ** (x / 20.0)


def zeros(ch=1):
    return np.zeros((N, ch)) if ch > 1 else np.zeros(N)


def place(buf, x, t0, gain=1.0):
    i0 = int(round(t0 * SR))
    if i0 >= len(buf):
        return
    if i0 < 0:
        x = x[-i0:]
        i0 = 0
    n = min(len(x), len(buf) - i0)
    buf[i0:i0 + n] += x[:n] * gain


def env_adsr(n, a, d, s, r_start, r, sr=SR):
    t = np.arange(n) / sr
    e = np.where(t < a, t / max(a, 1e-4), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-4)))
    rel = np.where(t > r_start, np.exp(-(t - r_start) / max(r, 1e-4)), 1.0)
    return e * rel


def bp(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], btype="band", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def lp(x, fc, order=2):
    sos = signal.butter(order, fc, btype="low", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def hp(x, fc, order=2):
    sos = signal.butter(order, fc, btype="high", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def reson(x, f, q):
    b, a = signal.iirpeak(f, q, fs=SR)
    return signal.lfilter(b, a, x)


def pink(n):
    w = rng.standard_normal(n)
    b = [0.049922035, -0.095993537, 0.050612699, -0.004408786]
    a = [1, -2.494956002, 2.017265875, -0.522189400]
    return signal.lfilter(b, a, w) * 3.0


def brown(n):
    return lp(np.cumsum(rng.standard_normal(n)) * 0.01, 400) - lp(np.cumsum(rng.standard_normal(n)) * 0.01, 5)


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def S(*arrs):
    """sum signals of different lengths (zero-padded)."""
    n = max(len(a) for a in arrs)
    out = np.zeros(n)
    for a in arrs:
        out[: len(a)] += a
    return out


def stereo(x, pan=0.0):
    """constant-power pan, pan in [-1, 1]"""
    a = (pan + 1) * math.pi / 4
    return np.stack([x * math.cos(a), x * math.sin(a)], axis=1)


def ir(rt60, pre=0.012, er=(), length=None, seed=0, bright=6000):
    r = np.random.default_rng(seed)
    L = int((length or rt60 * 1.3) * SR)
    t = np.arange(L) / SR
    tail = r.standard_normal((L, 2)) * np.exp(-6.9 * t / rt60)[:, None]
    tail[: int(pre * SR)] = 0
    for (d, g) in er:
        i = int(d * SR)
        if i < L:
            tail[i, 0] += g * r.uniform(0.6, 1.0)
            tail[i + int(0.0007 * SR), 1] += g * r.uniform(0.6, 1.0)
    for c in range(2):
        tail[:, c] = lp(tail[:, c], bright)
    tail /= np.sqrt((tail ** 2).sum() / 2)
    return tail


def convolve_st(x, h, wet):
    """x stereo (N,2); h stereo IR. returns dry+wet"""
    out = x.copy()
    for c in range(2):
        out[:, c] += wet * signal.fftconvolve(x[:, c], h[:, c])[: len(x)]
    return out


def mono_to_room(x, h, wet, pan=0.0):
    s = stereo(x, pan)
    return convolve_st(s, h, wet)


IR_STREET = ir(0.35, pre=0.02, er=[(0.031, 0.5), (0.047, 0.35), (0.083, 0.25)], seed=1, bright=5000)
IR_PORCH = ir(0.45, pre=0.008, er=[(0.006, 0.6), (0.017, 0.4), (0.029, 0.3)], seed=2, bright=5000)
IR_SALOON = ir(0.85, pre=0.01, er=[(0.011, 0.5), (0.019, 0.45), (0.027, 0.35), (0.041, 0.3)], seed=3, bright=4500)


# ===================================================================== instruments
def ks_guitar(midi, vel, dur=3.2):
    f = mtof(midi)
    n = int(dur * SR)
    D = int(round(SR / f - 0.5))
    exc = rng.uniform(-1, 1, D + 1)
    exc = lp(np.concatenate([exc, np.zeros(8)]), 2500 + 3000 * vel)[: D + 1]   # soft fingertip pluck
    x = np.zeros(n)
    x[: D + 1] = exc
    g = 0.996 - 0.0006 * max(0, midi - 50) / 10
    a = np.zeros(D + 2)
    a[0] = 1.0
    a[D] = -g * 0.5
    a[D + 1] = -g * 0.5
    y = signal.lfilter([1.0], a, x)
    body = 0.6 * reson(y, 105, 4) + 0.4 * reson(y, 210, 5) + 0.25 * reson(y, 420, 6)
    y = y + 0.5 * body
    y = lp(y, 5200)
    y *= np.exp(-np.arange(n) / SR / 2.6)
    return y * vel


def piano_note(midi, vel, dur, damp_at=None, detune_cents=0.0):
    """honky-tonk upright: inharmonic additive partials, 3 detuned strings, hammer knock."""
    f0 = mtof(midi) * 2 ** (detune_cents / 1200)
    T = min(dur + 0.9, 2.5)
    if damp_at is not None:
        T = min(T, damp_at + 0.25)
    n = int(T * SR)
    t = np.arange(n) / SR
    B = 0.00025 + 0.0004 * max(0, 60 - midi) / 30
    y = np.zeros(n)
    nparts = int(min(12, 9000 / f0))
    bright = 0.6 + 0.6 * vel
    for k in range(1, nparts + 1):
        fk = k * f0 * math.sqrt(1 + B * k * k)
        if fk > 12000:
            break
        amp = (1.0 / k ** 1.05) * math.exp(-(k - 1) * 0.22 / bright)
        dec1 = 2.2 + 0.9 * k + midi * 0.03
        dec2 = 0.35 + 0.12 * k
        e = 0.65 * np.exp(-t * dec1) + 0.35 * np.exp(-t * dec2)
        for dc in (-4.0, 0.0, 4.5):        # three strings, slightly out of tune (old saloon piano)
            ph = rng.uniform(0, 2 * math.pi)
            y += amp * e * np.sin(2 * math.pi * fk * 2 ** (dc / 1200) * t + ph) / 3
    # hammer knock
    kn = rng.standard_normal(int(0.03 * SR)) * np.exp(-np.arange(int(0.03 * SR)) / (0.004 * SR))
    kn = bp(kn, 300, 3000)
    y[: len(kn)] += 0.25 * kn * vel
    # key release / damper
    off = dur if damp_at is None else min(dur, damp_at)
    rel = np.where(t > off, np.exp(-(t - off) / (0.05 if damp_at is not None and off == damp_at else 0.09)), 1.0)
    y *= rel
    return y * vel * 0.5


def bowed(midis, t0, t1, att=0.8, rel=0.9, vib=4.8, bright=1400, level=1.0, tremolo=0.0, cut_at=None):
    """restrained low strings (cello/bass) section: band-limited saws, vibrato, ensemble detune."""
    n0, n1 = int(t0 * SR), min(int((t1 + rel) * SR), N)
    t = np.arange(n1 - n0) / SR
    y = np.zeros(n1 - n0)
    for m in midis:
        f = mtof(m)
        for dv in (-0.12, 0.0, 0.11):
            vibr = 1 + 0.0025 * np.sin(2 * math.pi * (vib + dv) * t + rng.uniform(0, 6))
            phase = 2 * math.pi * f * (1 + dv * 0.01) * np.cumsum(vibr) / SR
            for k in range(1, int(min(24, 6000 / f))):
                y += np.sin(k * phase) / k * (0.75 ** (k / 6)) / 3
    y = lp(y, bright)
    y += 0.02 * bp(rng.standard_normal(len(y)), 800, 3000)       # bow hair noise
    dur = t1 - t0
    e = np.clip(t / att, 0, 1) ** 1.5
    e *= np.where(t > dur, np.exp(-(t - dur) / (rel / 3)), 1.0)
    if tremolo:
        e *= 1 - tremolo * (0.5 + 0.5 * np.sin(2 * math.pi * 7.5 * t))
    out = zeros()
    out[n0:n1] = y * e * level
    if cut_at is not None:
        c = int(cut_at * SR)
        fade = np.ones(N)
        fade[c:] = 0
        fade[c:c + int(0.25 * SR)] = np.linspace(1, 0, int(0.25 * SR))[: N - c]
        out *= fade
    return out


# ===================================================================== perspective helpers
SHOT_T = {n: (a, b) for n, a, b in SHOTS}


def curve(points, smooth_s=0.06):
    """piecewise-linear parameter curve sampled at SR, then lightly smoothed (cut de-clicking)."""
    ts = np.array([p[0] for p in points])
    vs = np.array([p[1] for p in points])
    c = np.interp(tt, ts, vs)
    if smooth_s:
        k = int(smooth_s * SR)
        c = np.convolve(np.pad(c, (k, k), mode="edge"), np.ones(k) / k, mode="same")[k:-k]
    return c


def tv_lowpass(x, fc_curve, block=256):
    """time-varying 2nd-order lowpass (block-wise coefficients, state carried)."""
    y = np.zeros_like(x)
    zi = np.zeros((1, 2))
    for i in range(0, len(x), block):
        fc = float(np.clip(fc_curve[min(i + block // 2, len(fc_curve) - 1)], 80, 20000))
        if fc >= 19000:
            sos = np.array([[1, 0, 0, 1, 0, 0]], dtype=float)
        else:
            sos = signal.butter(2, fc, btype="low", fs=SR, output="sos")
        y[i:i + block], zi = signal.sosfilt(sos, x[i:i + block], zi=zi)
    return y


# ===================================================================== build stems
def build():
    ev = json.load(open(os.path.join(ROOT, "build", "events.json")))["events"]
    cams = json.load(open(os.path.join(ROOT, "build", "cams.json")))

    def cam_at(t):
        return cams[min(int(t * 30), len(cams) - 1)]

    def pan_gain(pos, t, ref=3.0, width=0.85):
        c = cam_at(t)
        d = np.array(pos) - np.array(c["pos"])
        dist = float(np.linalg.norm(d)) + 1e-3
        pan = float(np.clip(np.dot(d / dist, np.array(c["right"])) * 1.2, -1, 1)) * width
        g = 1.0 / (1.0 + max(0.0, dist - 1.0) / ref)
        return pan, g, dist

    # ---------------- narration (unchanged)
    nar, sr = sf.read(os.path.join(ROOT, "audio", "narration_48k.wav"), dtype="float64")
    assert sr == SR
    narr = zeros()
    narr[: len(nar)] = nar[:N]
    nar_st = np.stack([narr, narr], axis=1)

    # sidechain envelope for ducking
    e = np.abs(narr)
    env = signal.lfilter([1], [1, -math.exp(-1 / (0.01 * SR))], e) * (1 - math.exp(-1 / (0.01 * SR)))
    env_db = 20 * np.log10(env + 1e-6)
    speech = (env_db > -42).astype(float)
    # attack 40 ms, release 350 ms
    sm = np.zeros(N)
    a_att, a_rel = math.exp(-1 / (0.04 * SR)), math.exp(-1 / (0.35 * SR))
    acc = 0.0
    for i in range(0, N, 32):          # block-wise follower (cheap)
        target = speech[i:i + 32].max()
        coef = a_att ** 32 if target > acc else a_rel ** 32
        acc = target + (acc - target) * coef
        sm[i:i + 32] = acc

    def duck(depth_db):
        return db(-depth_db * sm)

    # ---------------- score: guitar + low strings + tension note (non-diegetic)
    gtr = zeros()
    for g in music.guitar_events():
        y = ks_guitar(g["midi"], g["vel"])
        place(gtr, y, g["t"])
    gfade = curve([(0, 1), (7.6, 1), (9.4, 0.0), (16, 0)], 0.1)
    gtr *= gfade
    gtr_st = convolve_st(np.stack([gtr * 0.9, gtr * 1.0], axis=1) * 0.5 +
                         np.stack([np.roll(gtr, 240) * 0.1, np.roll(gtr, 120) * 0.0], axis=1), IR_SALOON, 0.18)
    strings = zeros()
    for (a, b, ms) in music.STRINGS:
        strings += bowed(ms, a, b, level=0.30)
    # hold a very low drone into the saloon, cut together with the piano
    strings += bowed([40, 47], 9.4, 11.7, att=1.0, level=0.20, cut_at=PIANO_STOP + 0.02)
    strings *= curve([(0, 1), (PIANO_STOP, 1), (PIANO_STOP + 0.05, 0), (16, 0)], 0.0)
    a, b, ms = music.TENSION
    tension = bowed(ms, a, b, att=1.6, rel=0.6, bright=700, level=0.12, tremolo=0.25)
    tension *= curve([(0, 1), (15.2, 1), (16.0, 0)], 0.0)
    score = gtr_st + convolve_st(stereo(strings, 0.0) + np.stack([strings, -strings], axis=1) * 0.05,
                                 IR_SALOON, 0.25) + convolve_st(stereo(tension, 0), IR_SALOON, 0.3)
    for c in range(2):
        score[:, c] = hp(score[:, c], 40)
    score *= duck(6.5)[:, None]
    score *= db(-14)

    # ---------------- diegetic saloon piano
    pev = music.piano_events()
    pdry = zeros()
    prng = np.random.default_rng(5)
    for p in pev:
        y = piano_note(p["midi"], p["vel"], p["dur"], damp_at=max(0.0, PIANO_STOP - p["t"]),
                       detune_cents=prng.uniform(-6, 6))
        place(pdry, y, p["t"])
    # mechanical stop: dampers + a soft key thud exactly at PIANO_STOP
    th = bp(rng.standard_normal(int(0.05 * SR)), 120, 900) * np.exp(-np.arange(int(0.05 * SR)) / (0.008 * SR))
    place(pdry, th * 0.15, PIANO_STOP + 0.01)
    pdry *= curve([(0, 1), (PIANO_STOP + 0.04, 1), (PIANO_STOP + 0.12, 0.0), (16, 0)], 0.0)
    # camera perspective: muffled street -> clearer at the door -> inside -> close-up
    p_gain = curve([(0, -27), (4.39, -27), (4.41, -25), (7.09, -24), (7.11, -19), (8.96, -18), (8.98, -16),
                    (9.6, -14), (10.1, -11), (10.92, -10), (10.94, -9), (12.7, -9), (16, -9)])
    p_fc = curve([(0, 600), (4.39, 650), (4.41, 800), (7.09, 850), (7.11, 1500), (8.96, 1600), (8.98, 2000),
                  (9.6, 3000), (10.1, 9000), (10.92, 12000), (10.94, 20000), (16, 20000)])
    p_wet = curve([(0, 0.35), (10.0, 0.35), (10.4, 0.45), (10.92, 0.45), (10.94, 0.16), (16, 0.16)])
    pm = tv_lowpass(pdry, p_fc) * db(p_gain)
    piano = np.zeros((N, 2))
    for c in range(2):
        wet = signal.fftconvolve(pm, IR_SALOON[:, c])[:N]
        piano[:, c] = pm * (1 - 0.3 * p_wet) + wet * p_wet
    # pan: piano sits to the right of the door seen from the street; left of frame in S5
    pan = curve([(0, 0.25), (4.39, 0.25), (4.41, 0.35), (7.09, 0.3), (7.11, 0.5), (8.96, 0.5), (8.98, 0.25),
                 (10.92, 0.4), (10.94, -0.35), (12.72, -0.35), (12.74, -0.6), (16, -0.6)])
    ang = (pan + 1) * math.pi / 4
    mid = piano.mean(axis=1)
    piano = np.stack([mid * np.cos(ang), mid * np.sin(ang)], axis=1) * 1.25 + (piano - mid[:, None]) * 0.6
    piano *= duck(curve([(0, 4.0), (10.9, 4.0), (10.95, 2.0), (16, 2.0)], 0.0))[:, None]

    # ---------------- indistinct saloon chatter (formant babble, no intelligible words)
    ch = zeros()
    vowels = [(700, 1220, 2600), (390, 2300, 3000), (300, 870, 2240), (520, 1190, 2390), (640, 1600, 2500),
              (440, 1020, 2240), (360, 1900, 2600)]
    for v in range(7):
        f0 = rng.uniform(95, 170) if v < 6 else rng.uniform(170, 220)
        src = zeros()
        t = tt
        pitch = f0 * (1 + 0.08 * np.sin(2 * math.pi * rng.uniform(0.2, 0.5) * t + rng.uniform(0, 6)) +
                      0.05 * lp(rng.standard_normal(N), 3) * 30)
        ph = 2 * math.pi * np.cumsum(pitch) / SR
        glott = (np.mod(ph, 2 * math.pi) / math.pi - 1.0) * 0.6 + 0.08 * rng.standard_normal(N)
        # syllable envelope: bursts of 3-9 syllables separated by pauses
        envv = zeros()
        ft = np.zeros((N, 3))
        pos = rng.uniform(0, 1.0)
        cur = vowels[0]
        while pos < VIDEO_DURATION:
            nsyl = rng.integers(3, 9)
            for _ in range(nsyl):
                L = rng.uniform(0.12, 0.26)
                i0, i1 = int(pos * SR), min(int((pos + L) * SR), N)
                if i0 >= N:
                    break
                w = np.sin(np.linspace(0, math.pi, i1 - i0)) ** 0.8
                envv[i0:i1] = np.maximum(envv[i0:i1], w * rng.uniform(0.5, 1.0))
                nxt = vowels[rng.integers(len(vowels))]
                for k in range(3):
                    ft[i0:i1, k] = np.linspace(cur[k], nxt[k], i1 - i0)
                cur = nxt
                pos += L
            pos += rng.uniform(0.35, 1.6)
        for k in range(3):
            ft[:, k] = np.where(ft[:, k] == 0, 500 * (k + 1), ft[:, k])
        # formant filtering approximated with 3 fixed-band banks crossfaded by formant position
        out = zeros()
        for k, (lo_, hi_) in enumerate(((250, 900), (800, 2400), (2000, 3200))):
            centers = np.linspace(lo_, hi_, 5)
            bank = [reson(glott, c, 6) for c in centers]
            idx = np.clip((ft[:, k] - lo_) / (hi_ - lo_) * 4, 0, 3.999)
            i_ = idx.astype(int)
            fr_ = idx - i_
            sel = np.zeros(N)
            for j in range(4):
                m = i_ == j
                sel[m] = bank[j][m] * (1 - fr_[m]) + bank[j + 1][m] * fr_[m]
            out += sel * (1.0, 0.5, 0.2)[k]
        place(ch, out * envv * rng.uniform(0.5, 1.0) * 0.25, 0)
    ch += 0.15 * lp(pink(N), 1200) * lp(np.abs(rng.standard_normal(N)), 4) * 6
    ch = hp(lp(ch, 2600), 150)
    # occupants fall silent as he enters (people stop one after another), gone before the piano stops
    ch_fall = curve([(0, 1), (9.7, 1), (10.15, 0.55), (10.6, 0.22), (11.05, 0.06), (11.35, 0.0), (16, 0)], 0.05)
    c_gain = curve([(0, -37), (4.39, -37), (4.41, -33), (7.09, -33), (7.11, -26), (8.96, -25), (8.98, -23),
                    (10.1, -19), (10.92, -18), (10.94, -18), (16, -18)])
    c_fc = curve([(0, 700), (7.09, 750), (7.11, 1200), (8.96, 1300), (8.98, 1500), (10.1, 6000), (16, 6000)])
    cm = tv_lowpass(ch, c_fc) * db(c_gain) * ch_fall
    chatter = convolve_st(np.stack([cm * 0.9, np.roll(cm, 300) * 0.9], axis=1), IR_SALOON, 0.6)
    chatter *= duck(4)[:, None]

    # ---------------- wind (exterior) + room tone (interior)
    wl = pink(N)
    wr = pink(N)
    gust = 0.6 + 0.4 * lp(rng.standard_normal(N), 0.6) * 25
    gust = np.clip(gust, 0.2, 1.4)
    wind = np.stack([bp(wl, 180, 1400) * gust, bp(wr, 200, 1500) * np.roll(gust, 9000)], axis=1)
    whistle = bp(pink(N), 900, 1100) * np.clip(gust - 0.9, 0, None) * 0.6
    wind += np.stack([whistle, whistle * 0.7], axis=1)
    w_gain = curve([(0, -27), (4.39, -27), (4.41, -29), (7.09, -29), (7.11, -31), (8.96, -31), (8.98, -32),
                    (9.9, -34), (10.4, -42), (10.92, -44), (10.94, -54), (12.72, -54), (12.74, -47), (16, -47)])
    wind *= db(w_gain)[:, None] * 6.0
    wind *= duck(2)[:, None]
    room = hp(lp(brown(N), 250), 35) * 0.6 + lp(pink(N), 900) * 0.05
    r_gain = curve([(0, -80), (9.9, -80), (10.4, -56), (10.92, -54), (16, -53)])
    roomtone = stereo(room * db(r_gain), 0.0) + np.stack([np.zeros(N), np.roll(room, 4000) * db(r_gain) * 0.3], 1)

    # ---------------- foley / effects
    fx = np.zeros((N, 2))

    def add_fx(sig, t, pos=None, pan=None, gain=1.0, room=None, wet=0.2, ref=3.0):
        g = 1.0
        if pos is not None:
            p, g, _ = pan_gain(pos, t, ref=ref)
            pan = p if pan is None else pan
        s = stereo(sig * gain * g, pan or 0.0)
        if room is not None:
            s = convolve_st(s, room, wet)
        place(fx, s, t)

    def hoof(front):
        n = int(0.22 * SR)
        t = np.arange(n) / SR
        f = rng.uniform(85, 115) * (1.15 if front else 1.0)
        body = np.sin(2 * math.pi * f * t * (1 - 0.3 * t)) * np.exp(-t / 0.035)
        dirt = bp(rng.standard_normal(n), 250, 1600) * np.exp(-t / 0.02)
        clop = bp(rng.standard_normal(n), 1400, 3200) * np.exp(-t / 0.006) * 0.35
        grit = bp(rng.standard_normal(n), 2000, 6000) * np.exp(-t / 0.07) * 0.06
        return (0.9 * body + 0.7 * dirt + clop + grit) * rng.uniform(0.75, 1.0)

    def creak(f0, dur, rate=(55, 140), q=18, glide=0.0):
        n = int(dur * SR)
        t = np.arange(n) / SR
        rate_c = np.interp(t, [0, dur * 0.5, dur], [rate[0], rate[1], rate[0] * 0.8])
        ph = np.cumsum(rate_c * (1 + 0.2 * rng.standard_normal(n))) / SR
        imp = (np.diff(np.floor(ph), prepend=0) > 0).astype(float)
        imp *= rng.uniform(0.4, 1.0, n)
        y = np.zeros(n)
        segs = 4
        for sgi in range(segs):        # piecewise resonance to approximate a pitch glide
            a0, a1 = sgi * n // segs, (sgi + 1) * n // segs
            fseg = f0 * (1 + glide * (sgi + 0.5) / segs)
            part = np.zeros(n)
            part[a0:a1] = imp[a0:a1]
            for k, fm in enumerate((1.0, 2.13, 3.4)):
                y += reson(part, fseg * fm, q) / (k + 1)
        e = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 0.7
        return y * e

    def knock(f0, n_ms=120, decay=0.03, bright=1.0):
        n = int(n_ms / 1000 * SR)
        t = np.arange(n) / SR
        y = np.zeros(n)
        for fm, a in ((1.0, 1.0), (1.71, 0.6), (2.63, 0.35), (3.9, 0.2)):
            y += a * np.sin(2 * math.pi * f0 * fm * t + rng.uniform(0, 6)) * np.exp(-t / (decay / fm ** 0.5))
        y += bright * bp(rng.standard_normal(n), 1500, 5000) * np.exp(-t / 0.004) * 0.6
        return y

    def jingle(n_ms=220, level=1.0):
        n = int(n_ms / 1000 * SR)
        t = np.arange(n) / SR
        y = np.zeros(n)
        for _ in range(3):
            d = int(rng.uniform(0, 0.03) * SR)
            for f in (rng.uniform(2600, 3200), rng.uniform(4100, 4700), rng.uniform(5900, 6900)):
                seg = np.sin(2 * math.pi * f * t) * np.exp(-t / rng.uniform(0.03, 0.08))
                y[d:] += seg[: n - d] * 0.3
        return y * level

    # hoofbeats: only while the horse is seen walking (S1)
    for h in ev["hoof"]:
        if h["t"] >= 4.38 or h.get("soft"):
            continue
        add_fx(hoof(h["k"][1] == "F"), h["t"], pos=h["pos"], gain=0.55, room=IR_STREET, wet=0.25, ref=4.0)
        if rng.random() < 0.35:
            add_fx(jingle(160, 0.08), h["t"] + 0.02, pos=h["pos"], gain=1.0, ref=4.0)
    # saddle leather creaks synced with the gait (S1) + settle creak at the halt
    for i, h in enumerate([h for h in ev["hoof"] if h["t"] < 4.3 and h["k"][1] == "H"]):
        add_fx(creak(rng.uniform(380, 520), 0.22, rate=(70, 160), q=14), h["t"] + 0.05, pos=h["pos"],
               gain=0.10, ref=4.0)
    add_fx(creak(420, 0.4, rate=(50, 120)), 3.9, pos=[0.35, -4.05, 1.7], gain=0.10, ref=4.0)
    # S2: tack movement, bit jingle on the head toss, reins on the hitching rail
    add_fx(jingle(200, 0.15), 5.75, pan=-0.45, gain=1.0)
    add_fx(jingle(260, 0.22), 6.55, pan=-0.45, gain=1.0)
    add_fx(creak(520, 0.35, rate=(60, 130), q=12), 4.62, pan=-0.3, gain=0.08)
    for r in ev["rein"]:
        n = int(0.3 * SR)
        t = np.arange(n) / SR
        if r["kind"] == "over_rail":
            s = S(knock(150, 160, 0.02, 0.3) * 0.25, bp(rng.standard_normal(n), 900, 3000) * np.exp(-t / 0.05) * 0.2)
        elif r["kind"] in ("wrap", "wrap2"):
            s = S(bp(rng.standard_normal(n), 800, 3500) * np.sin(np.pi * np.clip(t / 0.26, 0, 1)) * 0.22,
                  knock(170, 120, 0.015, 0.2) * 0.12)
        else:
            s = S(creak(650, 0.28, rate=(90, 200), q=16) * 0.5, knock(160, 120, 0.02, 0.4) * 0.15)
        add_fx(s, r["t"], pan=0.05, gain=0.9, room=IR_STREET, wet=0.15)
    # S3: brushing the coat (cloth swishes + soft pats); dust itself is silent
    for c in ev["cloth"]:
        dur = 0.34
        n = int(dur * SR)
        t = np.arange(n) / SR
        sw = bp(pink(n), 700, 5500) * np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.5
        pat = lp(rng.standard_normal(n), 400) * np.exp(-t / 0.015) * 3
        add_fx(S(sw * 0.16, pat * 0.05), c["t"] + 0.1, pan=0.12, gain=c["amp"], room=IR_PORCH, wet=0.2)
    add_fx(bp(pink(int(0.5 * SR)), 300, 2500) * np.hanning(int(0.5 * SR)) * 0.04, 8.55, pan=0.1)  # coat settles
    # S4: boots on the porch / threshold / saloon floor, spurs
    for s_ in ev["step"]:
        surf_f = 135 if s_["surface"] == "porch" else 115
        g = 0.55 if not s_.get("scuff") else 0.18
        sig = S(knock(surf_f * rng.uniform(0.95, 1.05), 260, 0.05, 0.9),
                knock(surf_f * 4.7, 80, 0.008, 0.5) * 0.25)          # heel click
        if s_.get("scuff"):
            n = int(0.25 * SR)
            sig = bp(pink(n), 500, 4000) * np.hanning(n) * 0.5
        room_ = IR_PORCH if s_["surface"] == "porch" else IR_SALOON
        add_fx(sig, s_["t"], pan=0.0, gain=g, room=room_, wet=0.25 if s_["surface"] == "porch" else 0.35)
        add_fx(jingle(240, 0.12), s_["t"] + 0.015, pan=0.05)
    # swinging doors: push + damped swings (hinge squeaks get smaller), leaves knocking lightly on the push
    for d in ev["door"]:
        if d["kind"] == "push":
            s = S(creak(980, 0.45, rate=(110, 260), q=26, glide=0.25) * 0.7, knock(210, 150, 0.03, 0.5) * 0.18)
            add_fx(s, d["t"], pan=0.0, gain=0.6, room=IR_PORCH, wet=0.25)
    for k in range(10):
        tau = 0.2875 + 0.575 * k
        amp = math.exp(-0.95 * tau)
        if amp < 0.1:
            break
        t0 = 10.25 + tau - 0.12
        f = 1050 if k % 2 == 0 else 900
        s = creak(f, 0.28 + 0.1 * amp, rate=(100, 230 * amp + 60), q=26, glide=0.2 if k % 2 else -0.15)
        in_room = t0 > 10.93
        add_fx(s, t0, pan=0.0 if not in_room else -0.12, gain=0.55 * amp ** 1.2 * (0.6 if in_room else 1.0),
               room=IR_SALOON if in_room else IR_PORCH, wet=0.35)
    # S6: chair creak as a patron turns, glass set down, last floorboard creak under the stranger
    for f in ev["foley"]:
        if f["kind"] == "chair_creak":
            add_fx(creak(310, 0.45, rate=(45, 110), q=12), f["t"], pos=f["pos"], gain=0.5, room=IR_SALOON, wet=0.3,
                   ref=4.0)
        elif f["kind"] == "glass_down":
            n = int(0.35 * SR)
            t = np.arange(n) / SR
            ring = sum(np.sin(2 * math.pi * fq * t) * np.exp(-t / 0.09) for fq in (2310, 3870, 5210)) * 0.05
            s = S(knock(260, 120, 0.012, 0.6) * 0.5, ring)
            add_fx(s, f["t"], pos=f["pos"], gain=0.45, room=IR_SALOON, wet=0.3, ref=4.0)
        elif f["kind"] == "floor_creak":
            add_fx(creak(230, 0.6, rate=(35, 90), q=10, glide=-0.1), f["t"], pos=f["pos"], gain=0.55,
                   room=IR_SALOON, wet=0.35, ref=5.0)
    fx *= db(-4)

    # ---------------- sum
    bg = score + piano + chatter + wind + roomtone + fx
    mix = nar_st + bg
    # gentle safety limiter on the background only would change the narration balance; the narration itself
    # peaks at -3.9 dBFS, so we only soft-limit the final sum if needed.
    peak = np.abs(mix).max()
    if peak > db(-1.0):
        mix *= db(-1.0) / peak
    fade = np.ones(N)
    fl = int(0.6 * SR)
    fade[-fl:] = np.linspace(1, 0, fl) ** 1.5
    mix *= fade[:, None]
    for name, s in (("narration", nar_st), ("score", score), ("piano_diegetic", piano), ("chatter", chatter),
                    ("wind", wind), ("roomtone", roomtone), ("fx", fx)):
        sf.write(os.path.join(STEMS, name + ".wav"), s.astype(np.float32), SR, subtype="FLOAT")
    sf.write(os.path.join(ROOT, "audio", "final_mix.wav"), mix, SR, subtype="PCM_24")
    print("peak dBFS %.2f (scaled: %s)" % (20 * math.log10(np.abs(mix).max()), peak > db(-1.0)))


if __name__ == "__main__":
    build()
