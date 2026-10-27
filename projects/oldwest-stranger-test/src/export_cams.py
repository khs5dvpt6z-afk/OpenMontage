"""Dump the active camera position/orientation per frame (for audio spatialisation)."""
import json
import os
import sys

import bpy  # noqa
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timeline import FPS, N_FRAMES, SHOTS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, "build", "oldwest.blend"))
sc = bpy.context.scene
out = []
for fr in range(N_FRAMES):
    t = fr / FPS
    shot = [n for n, a, b in SHOTS if a - 1e-6 <= t < b - 1e-6]
    shot = shot[0] if shot else SHOTS[-1][0]
    cam = bpy.data.objects["CAM_" + shot.split("_")[0]]
    sc.frame_set(fr)
    m = cam.matrix_world
    out.append(dict(t=t, shot=shot, pos=list(m.translation), right=list(m.col[0][:3]), fwd=list(-m.col[2].xyz)))
json.dump(out, open(os.path.join(ROOT, "build", "cams.json"), "w"))
print("cams", len(out))
