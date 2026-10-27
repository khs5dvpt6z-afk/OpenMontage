"""Original score + diegetic saloon-piano note lists (composed for this test; no external material).
Shared by the audio synthesizer and by the Blender scene (piano key animation)."""
import random

from timeline import PIANO_STOP

# ---------------------------------------------------------------- saloon piano (diegetic)
PIANO_BPM = 108.0
PIANO_BEAT = 60.0 / PIANO_BPM
PIANO_T0 = -0.494  # already playing when the film starts; a note lands at 11.45 so the stop cuts it

# Right-hand melody: (beat, midi, length_in_beats)  -- G major, 8 bars of 2/4
_MELODY = [
    (0, 71, .5), (.5, 74, .5), (1, 79, .75), (1.75, 78, .25),
    (2, 76, .5), (2.5, 74, .5), (3, 71, 1),
    (4, 72, .5), (4.5, 76, .5), (5, 79, .5), (5.5, 76, .5),
    (6, 74, .5), (6.5, 71, .5), (7, 67, 1),
    (8, 69, .5), (8.5, 72, .5), (9, 78, .75), (9.75, 76, .25),
    (10, 74, .5), (10.5, 72, .5), (11, 69, 1),
    (12, 71, .5), (12.5, 74, .25), (12.75, 76, .25), (13, 74, .5), (13.5, 71, .5),
    (14, 69, .5), (14.5, 66, .5), (15, 67, 1),
]
# Left hand oom-pah per bar: (bass, chord)
_BARS = [
    (43, (55, 59, 62)), (38, (55, 59, 62)), (48, (55, 60, 64)), (43, (55, 59, 62)),
    (45, (54, 57, 60, 62)), (50, (54, 57, 60, 62)), (43, (55, 59, 62)), (38, (54, 57, 60, 62)),
]


def piano_events(seed=7):
    """List of dicts {t, midi, dur, vel, hand}. Notes at/after PIANO_STOP are not played."""
    rng = random.Random(seed)
    ev = []
    for rep in range(3):
        base = rep * 16
        for b, m, l in _MELODY:
            ev.append(dict(beat=base + b, midi=m, dur=l, vel=0.75 + 0.15 * rng.random(), hand="R"))
            if rep >= 1 and l >= 1:          # thicker second chorus: add a lower sixth
                ev.append(dict(beat=base + b, midi=m - 8 if m - 8 > 60 else m - 9, dur=l,
                               vel=0.5, hand="R"))
        for i, (bass, chord) in enumerate(_BARS):
            bb = base + 2 * i
            ev.append(dict(beat=bb, midi=bass, dur=.9, vel=0.8, hand="L"))
            for c in chord:
                ev.append(dict(beat=bb + 1, midi=c, dur=.45, vel=0.55, hand="L"))
    out = []
    for e in ev:
        t = PIANO_T0 + e["beat"] * PIANO_BEAT + rng.uniform(-0.012, 0.012)
        if t >= PIANO_STOP - 0.02:
            continue
        out.append(dict(t=t, midi=e["midi"], dur=e["dur"] * PIANO_BEAT, vel=e["vel"], hand=e["hand"]))
    out.sort(key=lambda e: e["t"])
    return out


# ---------------------------------------------------------------- score (non-diegetic)
GUITAR_STEP = 0.30   # eighth note in a slow 6/8
_GUITAR_BARS = [
    [40, 55, 59, 64, 59, 55], [40, 55, 59, 64, 59, 55],     # Em
    [48, 52, 55, 60, 55, 52],                               # C
    [45, 52, 57, 60, 57, 52],                               # Am
    [47, 51, 57, 59, 57, 51],                               # B7
]


def guitar_events(seed=3):
    rng = random.Random(seed)
    ev = []
    t = 0.05
    for bar in _GUITAR_BARS:
        for i, m in enumerate(bar):
            ev.append(dict(t=t + rng.uniform(-0.008, 0.008), midi=m,
                           vel=(0.9 if i == 0 else 0.55 + 0.15 * rng.random())))
            t += GUITAR_STEP
    ev.append(dict(t=t, midi=40, vel=0.6))      # last low E rings out under "stepped inside"
    ev.append(dict(t=t + 0.02, midi=47, vel=0.4))
    return ev


# Low strings: (start, end, [midi...])
STRINGS = [
    (0.0, 3.75, [40, 47, 52]),
    (3.6, 5.55, [36, 43, 48]),
    (5.4, 7.35, [45, 52, 57]),
    (7.2, 9.6, [47, 54, 59]),
]
# final, very soft tension note after the silence
TENSION = (13.25, 16.0, [40, 47])
