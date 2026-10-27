"""Render frames from build/oldwest.blend with Cycles (CPU).
usage: python render.py --frames 0-479 [--pct 100] [--samples 64] [--out ../renders/frames] [--every 1]
       python render.py --list 30,150,240 --pct 50 --out ../renders/tests"""
import argparse
import json
import os
import sys
import time

import bpy  # noqa
import addon_utils

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timeline import FPS, SHOTS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ap = argparse.ArgumentParser()
ap.add_argument("--frames", default=None)
ap.add_argument("--list", default=None)
ap.add_argument("--pct", type=int, default=100)
ap.add_argument("--samples", type=int, default=None)
ap.add_argument("--out", default=os.path.join(ROOT, "renders", "frames"))
ap.add_argument("--every", type=int, default=1)
ap.add_argument("--skip-existing", action="store_true")
args = ap.parse_args()

addon_utils.enable("cycles", default_set=True)
bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, "build", "oldwest.blend"))
addon_utils.enable("cycles", default_set=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.render.resolution_percentage = args.pct
sc.render.threads_mode = "AUTO"
if args.samples:
    sc.cycles.samples = args.samples
expo = json.loads(sc["exposure_by_shot"])
# per-shot samples: interiors need more
SHOT_SAMPLES = {"S1_street": 8, "S2_tie": 10, "S3_brush": 10, "S4_step": 12, "S5_piano": 14, "S6_silence": 14}
FAST_GI = {"S5_piano"}
cams = {o.name: o for o in bpy.data.objects if o.type == "CAMERA"}

if args.list:
    frames = [int(x) for x in args.list.split(",")]
else:
    a, b = (int(x) for x in args.frames.split("-"))
    frames = list(range(a, b + 1, args.every))
os.makedirs(args.out, exist_ok=True)


def shot_of(fr):
    t = fr / FPS
    for name, a, b in SHOTS:
        if a - 1e-6 <= t < b - 1e-6:
            return name
    return SHOTS[-1][0]


t_all = time.time()
for fr in frames:
    path = os.path.join(args.out, "f%04d.png" % fr)
    if args.skip_existing and os.path.exists(path):
        continue
    shot = shot_of(fr)
    sc.camera = cams["CAM_" + shot.split("_")[0]]
    sc.view_settings.exposure = expo[shot]
    if not args.samples:
        sc.cycles.samples = SHOT_SAMPLES[shot]
    sc.cycles.use_fast_gi = shot in FAST_GI
    sc.cycles.ao_bounces_render = 1
    sc.frame_set(fr)
    sc.render.filepath = path
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print("RENDERED %d %s %.1fs" % (fr, shot, time.time() - t0), flush=True)
print("TOTAL %.1fs" % (time.time() - t_all))
