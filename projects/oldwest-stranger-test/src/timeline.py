"""Master timeline, derived from the measured narration (faster-whisper small.en word timestamps
+ ffmpeg silencedetect). All times in seconds; video is 30 fps, frame f shows time f/30."""

FPS = 30
NARRATION_DURATION = 14.681          # measured (ffprobe on decoded WAV)
VIDEO_DURATION = 16.0                # narration + 1.32 s natural tail
N_FRAMES = int(VIDEO_DURATION * FPS)  # 480 frames: 0..479

# Measured phrase timings (word-level)
PHRASES = {
    "p1_by_sundown":      (0.00, 3.92),   # "By sundown, the whole town knew a stranger had arrived."
    "p2_tied_horse":      (4.74, 6.94),   # "He tied his horse outside the saloon,"
    "p3_brushed_dust":    (7.24, 8.76),   # "brushed the dust from his coat,"
    "p4_stepped_inside":  (9.12, 10.20),  # "and stepped inside."
    "p5_piano_stopped":   (11.04, 12.22), # "The piano stopped."   ("stopped" starts 11.58)
    "p6_nobody":          (13.14, 14.26), # "Nobody said a word."
}

# Shot list (start, end) seconds -- cuts placed in the narration pauses
SHOTS = [
    ("S1_street",  0.00, 4.40),
    ("S2_tie",     4.40, 7.10),
    ("S3_brush",   7.10, 8.97),
    ("S4_step",    8.97, 10.93),
    ("S5_piano",  10.93, 12.73),
    ("S6_silence", 12.73, VIDEO_DURATION),
]

PIANO_STOP = 11.60        # on the onset of "stopped" (11.58)
HORSE_STOP = 3.85         # horse halts at the rail (end of hoofbeats)


def f(t):
    """seconds -> frame number"""
    return int(round(t * FPS))


def shot_at(t):
    for name, a, b in SHOTS:
        if a <= t < b:
            return name
    return SHOTS[-1][0]
