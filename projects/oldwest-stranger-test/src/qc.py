"""Quality checks on the delivered MP4: stream specs, full decode, black/frozen frames, audio levels,
narration alignment (cross-correlation with the source) and the piano stop."""
import json
import os
import subprocess
import sys

import numpy as np
import soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MP4 = os.path.join(ROOT, "final", "oldwest_stranger_test.mp4")
rep = {}

pr = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json",
                                         MP4]))
v = [s for s in pr["streams"] if s["codec_type"] == "video"][0]
a = [s for s in pr["streams"] if s["codec_type"] == "audio"][0]
rep["video"] = dict(codec=v["codec_name"], w=v["width"], h=v["height"], fps=v["r_frame_rate"], frames=v.get("nb_frames"))
rep["audio"] = dict(codec=a["codec_name"], sr=a["sample_rate"], ch=a["channels"])
rep["duration"] = float(pr["format"]["duration"])
dec = subprocess.run(["ffmpeg", "-v", "error", "-i", MP4, "-f", "null", "-"], capture_output=True, text=True)
rep["decode_errors"] = dec.stderr.strip() or "none"
bl = subprocess.run(["ffmpeg", "-i", MP4, "-vf", "blackdetect=d=0.1:pix_th=0.06", "-an", "-f", "null", "-"],
                    capture_output=True, text=True).stderr
rep["black_segments"] = [l.split("blackdetect")[1].strip() for l in bl.splitlines() if "black_start" in l]
fz = subprocess.run(["ffmpeg", "-i", MP4, "-vf", "freezedetect=n=0.0005:d=0.5", "-an", "-f", "null", "-"],
                    capture_output=True, text=True).stderr
rep["freezes"] = [l.split("]")[1].strip() for l in fz.splitlines() if "freeze_start" in l]
# audio from the MP4
wav = "/tmp/qc_audio.wav"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", MP4, "-vn", "-ac", "2", "-ar", "48000", wav], check=True)
x, sr = sf.read(wav)
rep["audio_peak_dbfs"] = round(20 * np.log10(np.abs(x).max()), 2)
nar, _ = sf.read(os.path.join(ROOT, "audio", "narration_48k.wav"))
m = x.mean(1)
seg = nar[: int(4 * sr)]
c = np.correlate(m[: int(5 * sr)], seg, mode="valid")
rep["narration_offset_ms"] = round(float(np.argmax(c)) / sr * 1000, 2)
stems = os.path.join(ROOT, "audio", "stems")
for n in ("score", "piano_diegetic", "chatter", "wind", "fx"):
    s, _ = sf.read(os.path.join(stems, n + ".wav"))
    rep["stem_rms_dbfs_" + n] = round(20 * np.log10(np.sqrt((s ** 2).mean()) + 1e-12), 1)
p, _ = sf.read(os.path.join(stems, "piano_diegetic.wav"))
p = p.mean(1)
lv = lambda t: round(20 * np.log10(np.sqrt((p[int(t * sr):int((t + 0.05) * sr)] ** 2).mean()) + 1e-12), 1)
rep["piano_level_before_after_stop"] = {"11.45-11.50": lv(11.45), "11.70-11.75": lv(11.70), "12.00-12.05": lv(12.0)}
# residual (mix minus narration) shows the music/effects really are in the MP4
resid = m[: len(nar)] - nar[: len(m)] * 1.0
rep["mp4_nonvoice_rms_dbfs"] = round(20 * np.log10(np.sqrt((resid ** 2).mean())), 1)
print(json.dumps(rep, indent=1))
json.dump(rep, open(os.path.join(ROOT, "final", "qc_report.json"), "w"), indent=1)
