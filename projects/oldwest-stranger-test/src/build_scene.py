"""Build the complete animated Old West scene and save it as a .blend.
Run:  python build_scene.py  (with the bpy wheel)  -> ../build/oldwest.blend + ../build/events.json"""
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402  (must precede addon_utils)
import addon_utils
from mathutils import Matrix, Vector

import bl_chars as CH
import bl_env as E
import bl_util as U
import music
from bl_util import V, keys, lerp, ramp, smooth, smoother
from timeline import FPS, HORSE_STOP, N_FRAMES, PIANO_STOP, SHOTS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
os.makedirs(BUILD, exist_ok=True)
Z = V((0, 0, 1))
EV = {"hoof": [], "step": [], "door": [], "rein": [], "cloth": [], "foley": [], "keys": []}


def T(fr):
    return fr / FPS


# =====================================================================  scene setup
def setup_scene():
    addon_utils.enable("cycles", default_set=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    addon_utils.enable("cycles", default_set=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 0, N_FRAMES - 1
    sc.cycles.samples = 14
    try:
        sc.cycles.denoising_prefilter = "FAST"
        sc.cycles.denoising_quality = "HIGH"
    except Exception:
        pass
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.03
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    sc.cycles.max_bounces = 5
    sc.cycles.diffuse_bounces = 3
    sc.cycles.glossy_bounces = 2
    sc.cycles.transmission_bounces = 4
    sc.cycles.transparent_max_bounces = 8
    sc.cycles.volume_bounces = 0
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.cycles.blur_glossy = 1.0
    sc.cycles.sample_clamp_indirect = 6.0
    sc.render.use_motion_blur = True
    sc.render.motion_blur_shutter = 0.45
    sc.render.use_persistent_data = True
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_depth = "8"
    sc.view_settings.view_transform = "AgX"
    for look in ("AgX - Medium High Contrast", "Medium High Contrast"):
        try:
            sc.view_settings.look = look
            break
        except Exception:
            pass
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
    return sc


def world_and_sun(sc):
    w = bpy.data.worlds.new("sky")
    sc.world = w
    try:
        w.use_nodes = True
    except Exception:
        pass
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "MULTIPLE_SCATTERING"
    sd = E.SUN_DIR
    sky.sun_elevation = math.asin(sd.z)
    sky.sun_rotation = math.atan2(sd.x, sd.y)
    sky.sun_disc = True
    sky.sun_size = math.radians(1.2)
    try:
        sky.aerosol_density = 2.2
        sky.air_density = 1.2
    except Exception:
        pass
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs[1].default_value = 0.30
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(sky.outputs[0], bg.inputs[0])
    nt.links.new(bg.outputs[0], out.inputs[0])
    ld = bpy.data.lights.new("sun", "SUN")
    ld.energy = 2.7
    ld.color = (1.0, 0.58, 0.30)
    ld.angle = math.radians(0.8)
    so = bpy.data.objects.new("sun", ld)
    so.matrix_world = U.frame_matrix(V((0, 0, 0)), sd, V((1, 0, 0)))
    U.link(so)
    # weak warm skylight bounce from the street (fake GI helper for shadow sides)
    fl = bpy.data.lights.new("street_bounce", "AREA")
    fl.energy = 0.0
    return sky


# =====================================================================  horse path + gait
class HorsePath:
    P = [V((-1.95, 0.7, 0)), V((-1.95, -2.2, 0)), V((-1.25, -4.05, 0)), V((0.35, -4.05, 0))]

    def __init__(self):
        self.pts = []
        for i in range(801):
            u = i / 800
            p = ((1 - u) ** 3) * self.P[0] + 3 * ((1 - u) ** 2) * u * self.P[1] + 3 * (1 - u) * u * u * self.P[2] + \
                (u ** 3) * self.P[3]
            self.pts.append(p)
        self.cum = [0.0]
        for a, b in zip(self.pts, self.pts[1:]):
            self.cum.append(self.cum[-1] + (b - a).length)
        self.L = self.cum[-1]
        self.t1 = 2.55
        self.v = self.L / (self.t1 + (HORSE_STOP - self.t1) / 2)

    def s_at(self, t):
        if t <= self.t1:
            return self.v * t
        if t >= HORSE_STOP:
            return self.L
        dt = t - self.t1
        D = HORSE_STOP - self.t1
        return self.v * self.t1 + self.v * (dt - dt * dt / (2 * D))

    def speed(self, t):
        if t <= self.t1:
            return self.v
        if t >= HORSE_STOP:
            return 0.0
        return self.v * (1 - (t - self.t1) / (HORSE_STOP - self.t1))

    def frame_at(self, s):
        """position + yaw at arc length s (extrapolated before 0)."""
        if s <= 0:
            d = (self.pts[1] - self.pts[0]).normalized()
            return self.pts[0] + d * s, math.atan2(d.y, d.x)
        if s >= self.L:
            d = (self.pts[-1] - self.pts[-2]).normalized()
            return self.pts[-1].copy(), math.atan2(d.y, d.x)
        lo, hi = 0, len(self.cum) - 1
        while hi - lo > 1:
            m = (lo + hi) // 2
            if self.cum[m] < s:
                lo = m
            else:
                hi = m
        u = (s - self.cum[lo]) / max(1e-9, self.cum[hi] - self.cum[lo])
        p = self.pts[lo].lerp(self.pts[hi], u)
        a = self.pts[max(lo - 3, 0)]
        b = self.pts[min(hi + 3, len(self.pts) - 1)]
        d = (b - a).normalized()
        return p, math.atan2(d.y, d.x)


STRIDE = 1.55
DUTY = 0.64
OFFS = {"LH": 0.0, "LF": 0.25, "RH": 0.5, "RF": 0.75}


def hoof_rest(k, pos, yaw):
    x = CH.Horse.FRONT_X if k[1] == "F" else CH.Horse.HIND_X
    y = CH.Horse.LEG_Y if k[0] == "L" else -CH.Horse.LEG_Y
    return pos + V((math.cos(yaw) * x - math.sin(yaw) * y, math.sin(yaw) * x + math.cos(yaw) * y, 0))


def horse_hooves(hp, t, phi0=0.15):
    """gait by distance. returns {k: (ground point, curl)} and list of plant events (handled outside)"""
    out = {}
    s = hp.s_at(min(t, HORSE_STOP))
    fpos, fyaw = hp.frame_at(hp.L)
    for k, off in OFFS.items():
        p = s / STRIDE + phi0 - off
        c = math.floor(p)
        u = p - c

        def W(cc):
            sm = (cc + DUTY / 2 + off - phi0) * STRIDE
            sm = min(sm, hp.L)
            q, y = hp.frame_at(sm)
            return hoof_rest(k, q, y)

        if u < DUTY:
            g, curl, lift = W(c), 0.0, 0.0
        else:
            w = (u - DUTY) / (1 - DUTY)
            a, b = W(c), W(c + 1)
            g = a.lerp(b, smoother(w))
            lift = math.sin(math.pi * w)
            g = g + Z * (0.13 * lift if k[1] == "F" else 0.10 * lift)
            curl = -1.1 * math.sin(math.pi * min(1.0, w * 1.15)) if k[1] == "F" else -0.6 * lift
        out[k] = (g, curl, u, c)
    return out


def build_horse_anim(horse, hp, rider_cb):
    """keys horse for all frames. rider_cb(frame, M_root) poses the rider (S1)."""
    final_pos, final_yaw = hp.frame_at(hp.L)
    st = horse_hooves(hp, HORSE_STOP)
    settle = {}
    order = 0
    for k in ("RF", "LH", "LF", "RH"):
        g, curl, u, c = st[k]
        rest = hoof_rest(k, final_pos, final_yaw)
        if u >= DUTY:
            g0 = V((g.x, g.y, 0))
            settle[k] = (g, rest, HORSE_STOP, HORSE_STOP + 0.28)
        elif (g - rest).length > 0.16:
            settle[k] = (g, rest, HORSE_STOP + 0.12 + 0.22 * order, HORSE_STOP + 0.42 + 0.22 * order)
            order += 1
    prev_u = {}
    for fr in range(N_FRAMES):
        t = T(fr)
        s = hp.s_at(min(t, HORSE_STOP))
        pos, yaw = hp.frame_at(s)
        spd = hp.speed(t) / hp.v
        ph = s / STRIDE
        bob = 0.022 * math.cos(4 * math.pi * ph) * spd
        pitch = 0.012 * math.sin(2 * math.pi * ph) * spd
        roll = 0.015 * math.sin(2 * math.pi * ph + 0.5) * spd
        # neck: nod with gait while walking; idle behaviour at the rail
        nod = 0.06 * math.sin(4 * math.pi * ph + 1.2) * spd
        ny = 0.0
        npch = 0.10 + nod
        nr = 0.0
        tail = (0.06 * math.sin(2 * math.pi * ph) * spd, 0.05 * spd)
        ears = (0.0, 0.0)
        breath = 0.006 * math.sin(2 * math.pi * t / 3.1)
        if t > HORSE_STOP:
            # settle + idle at the rail (S2): head lowers a little, ear flicks, tail swish, weight shift
            ts = t - HORSE_STOP
            npch = 0.10 + 0.12 * ramp(t, 4.3, 5.4) - 0.07 * ramp(t, 6.45, 6.9) + 0.02 * math.sin(t * 1.7)
            ny = -0.10 * ramp(t, 5.6, 6.3) + 0.04 * math.sin(t * 0.9)
            nr = 0.04 * math.sin(t * 1.3)
            if 6.45 < t < 7.0:     # slight toss when the rein is pulled snug
                npch -= 0.05 * math.sin(math.pi * (t - 6.45) / 0.55)
            sw = 0.0
            for (t0, amp) in ((5.15, 0.35), (6.75, 0.3), (9.0, 0.25)):
                if t0 < t < t0 + 0.9:
                    sw += amp * math.sin(2 * math.pi * (t - t0) / 0.9) * math.sin(math.pi * (t - t0) / 0.9)
            tail = (sw, 0.04 + 0.02 * math.sin(t))
            el = sum(0.9 * math.exp(-((t - c) / 0.12) ** 2) for c in (4.95, 6.6))
            er = sum(0.9 * math.exp(-((t - c) / 0.12) ** 2) for c in (5.75, 6.62))
            ears = (el, er)
            roll = -0.012 * ramp(t, 5.3, 6.0)
            bob = -0.008 * ramp(t, 5.3, 6.0)
            # deceleration overshoot
            pitch = 0.015 * math.exp(-ts * 5) * math.sin(ts * 12)
        hooves = {}
        hv = horse_hooves(hp, t)
        for k, (g, curl, u, c) in hv.items():
            if t <= HORSE_STOP and fr > 0 and k in prev_u:
                pu, pc = prev_u[k]
                if pu >= DUTY and u < DUTY:
                    EV["hoof"].append(dict(t=t, k=k, pos=list(g), shot="S1"))
            prev_u[k] = (u, c)
            if t > HORSE_STOP:
                g, curl = hoof_rest(k, final_pos, final_yaw), 0.0
                if k in settle:
                    a, b, t0, t1 = settle[k]
                    if t < t1:
                        w = max(0.0, (t - t0) / (t1 - t0))
                        g = a.lerp(b, smoother(w)) + Z * (0.08 * math.sin(math.pi * w) if t >= t0 else 0)
                        g.z = max(g.z, 0.0) if t >= t0 else a.z
                        curl = -0.5 * math.sin(math.pi * w) if t >= t0 else 0.0
                if k == "RH" and t > 5.2:          # rest the right hind leg (hip drop)
                    rr = ramp(t, 5.3, 6.0)
                    g = g + V((math.cos(final_yaw), math.sin(final_yaw), 0)) * 0.10 * rr + Z * 0.025 * rr
                    curl = 0.55 * rr
            hooves[k] = (g, curl)
        neck = (ny, npch, nr)
        horse.key(fr, pos, yaw, bob, pitch, roll, neck, tail, ears, hooves, breath)
        M_root = U.trs(pos + V((0, 0, bob)), yaw, pitch, roll)
        rider_cb(fr, t, pos, yaw, bob, pitch, roll, neck, M_root)
    for k, (a, b, t0, t1) in settle.items():
        EV["hoof"].append(dict(t=t1, k=k, pos=list(b), shot="S2", soft=True))
    EV["hoof"].sort(key=lambda e: e["t"])


# =====================================================================  stranger choreography
RAIL_HAND = [  # right-hand wrist path while tying (S2)
    (4.40, V((1.40, -3.62, 1.14))), (5.00, V((1.44, -3.70, 1.19))), (5.40, V((1.60, -3.72, 1.14))),
    (5.70, V((1.67, -3.72, 1.03))), (5.95, V((1.66, -3.71, 0.95))), (6.20, V((1.57, -3.70, 0.92))),
    (6.40, V((1.50, -3.69, 1.00))), (6.60, V((1.47, -3.67, 1.07))), (6.85, V((1.42, -3.63, 1.04))),
    (7.10, V((1.36, -3.57, 1.00)))]
S2_ROOT = V((1.30, -3.36, 0.0))
S2_YAW = -0.30
S3_ROOT = V((3.05, 0.0, E.FLOOR_Z))
STEPS = [  # (side, lift, plant, x_from, x_to)
    ("L", 9.08, 9.42, 3.05, 3.58), ("R", 9.33, 9.70, 3.05, 4.24),
    ("L", 9.62, 10.00, 3.58, 4.78), ("R", 9.93, 10.28, 4.24, 4.92)]
WALK_ROOT = [(8.97, 3.05), (9.2, 3.10), (9.42, 3.36), (9.70, 3.92), (10.0, 4.48), (10.28, 4.82), (10.5, 4.86)]
STAND_X = 4.86


def stranger_foot(side, t):
    """walking feet (S3/S4/S6) on the floor z=FLOOR_Z. returns ankle, pitch"""
    y = 0.10 if side == "L" else -0.10
    fz = E.FLOOR_Z + 0.08
    x = 3.05
    pitch = 0.0
    lifted = None
    for (sd, lf, pl, x0, x1) in STEPS:
        if sd != side:
            continue
        if t >= pl:
            x = x1
            # heel strike -> flat
            if t < pl + 0.1:
                pitch = -0.18 * (1 - (t - pl) / 0.1)
        elif t >= lf:
            w = (t - lf) / (pl - lf)
            x = lerp(x0, x1, smoother(w))
            lifted = w
            pitch = lerp(0.45, -0.18, smooth(w))
            break
        else:
            x = x0
            if t > lf - 0.16:
                pitch = 0.45 * smooth((t - (lf - 0.16)) / 0.16)
            break
    if lifted is not None:
        z = fz + 0.075 * math.sin(math.pi * lifted) + (0.19 * math.sin(0.45) + 0.08 * math.cos(0.45) - 0.08) * (
            1 - smooth(lifted * 2.5))
    else:
        if pitch > 0:     # heel raised, pivot on toe
            z = E.FLOOR_Z + 0.19 * math.sin(pitch) + 0.08 * math.cos(pitch)
            x = x - (0.19 - 0.19 * math.cos(pitch)) + 0.0
        elif pitch < 0:   # heel strike, pivot on heel (-0.06)
            z = E.FLOOR_Z + 0.06 * math.sin(-pitch) + 0.08 * math.cos(pitch)
        else:
            z = fz
    return V((x, y, z)), pitch


def stranger_pose(t, horse_state):
    """returns pose dict for Person.key"""
    if t < 4.40:      # ---------------- S1 riding
        pos, yaw, bob, pitch, roll, neck, M = horse_state
        seat = M @ CH.Horse.seat_local_static
        fwd = V((math.cos(yaw), math.sin(yaw), 0))
        side = V((-math.sin(yaw), math.cos(yaw), 0))
        pose = dict(root=seat, yaw=yaw, pelvis_z=0.07, torso=(0.0, 0.10 - bob * 2, -roll * 0.5),
                    head=(0.0, 0.05, 0.0), skirt=(-0.12, 0.0), skirt_follow=0.75)
        for s, sd in ((1, "L"), (-1, "R")):
            pose["foot" + sd] = M @ (CH.Horse.stirrup_static[s] + V((0.0, -s * 0.02, 0.0)))
            pose["kpole" + sd] = seat + fwd * 0.9 + side * s * 0.9
            pose["hand" + sd] = M @ V((0.40, s * 0.07, 1.98))
            pose["hdir" + sd] = fwd * 0.6 - Z * 0.4 + side * (-s * 0.2)
            pose["palm" + sd] = -side * s
            pose["fyaw" + sd] = yaw + s * 0.15
        return pose
    if t < 7.10:      # ---------------- S2 tying the reins at the rail
        yaw = S2_YAW
        fwd = V((math.cos(yaw), math.sin(yaw), 0))
        side = V((-math.sin(yaw), math.cos(yaw), 0))
        lean = 0.10 + 0.22 * ramp(t, 5.1, 5.6) - 0.08 * ramp(t, 6.5, 7.0) + 0.06 * ramp(t, 5.75, 6.1) * (1 - ramp(t, 6.2, 6.5))
        pose = dict(root=S2_ROOT.copy(), yaw=yaw, pelvis_z=0.94, torso=(-0.12, lean, 0.03),
                    head=(0.08, 0.38 + 0.05 * ramp(t, 5.6, 6.0), 0.0), skirt=(0.0, 0.02 * math.sin(t * 2)))
        for s, sd in ((1, "L"), (-1, "R")):
            pose["foot" + sd] = S2_ROOT + side * (s * 0.12) + fwd * (0.02 if s > 0 else -0.04) + Z * 0.08
            pose["fyaw" + sd] = yaw + s * 0.12
        rh = keys(t, RAIL_HAND, smooth)
        pose["handR"] = rh
        pose["hdirR"] = V((0.75, -0.1, -0.65))
        pose["palmR"] = V((-0.2, 0.8, -0.4))
        pose["epoleR"] = S2_ROOT + V((0.2, -0.9, 1.0))
        lh = keys(t, [(4.4, V((1.34, -3.45, 1.10))), (4.9, V((1.47, -3.48, 1.12))), (5.3, V((1.54, -3.44, 1.095)))])
        pose["handL"] = lh
        pose["hdirL"] = V((0.9, -0.1, -0.35))
        pose["palmL"] = V((0.1, 0.0, -1.0))
        pose["epoleL"] = S2_ROOT + V((0.0, 0.8, 0.9))
        return pose
    # ---------------- S3 brushing on the porch, S4 walking in, S6 standing inside
    yaw = 0.0
    x = keys(t, WALK_ROOT, smooth) if t >= 8.97 else S3_ROOT.x
    fL, pL = stranger_foot("L", t)
    fR, pR = stranger_foot("R", t)
    walk = ramp(t, 9.0, 9.2) * (1 - ramp(t, 10.2, 10.45))
    # pelvis bob: lowest at double support
    bob = 0.0
    for (sd, lf, pl, x0, x1) in STEPS:
        if lf <= t <= pl:
            bob += 0.018 * math.sin(math.pi * (t - lf) / (pl - lf))
    sway = 0.025 * (math.sin(math.pi * (t - 9.08) / 0.62)) * walk
    root = V((x, sway, E.FLOOR_Z))
    if t > 14.3:     # weight shift onto the left leg (floorboard creak)
        root.y += 0.03 * ramp(t, 14.35, 14.8)
    brush = 1.0 - ramp(t, 8.45, 8.85) if t < 9.0 else 0.0
    torso_pitch = 0.16 * ramp(t, 7.12, 7.3) * (1 - ramp(t, 8.45, 8.85)) + 0.05 * walk
    head_pitch = 0.42 * ramp(t, 7.1, 7.3) * (1 - ramp(t, 8.4, 8.8)) + 0.05 - 0.05 * ramp(t, 12.5, 13.5)
    head_yaw = 0.0
    if t > 12.8:
        head_yaw = 0.16 * ramp(t, 13.0, 13.8) - 0.12 * ramp(t, 14.2, 15.0)
    pose = dict(root=root, yaw=yaw, pelvis_z=0.95 + bob - 0.01 * walk, torso=(0.0, torso_pitch, -sway * 0.5),
                head=(head_yaw, head_pitch, 0.0), footL=fL, footR=fR, fpitchL=pL, fpitchR=pR, fyawL=0.08, fyawR=-0.08)
    # skirt reacts to strokes and walking
    sk = 0.0
    for (c, a) in ((7.42, 0.06), (7.78, 0.06), (8.25, 0.04)):
        sk += a * math.exp(-((t - c) / 0.18) ** 2) * math.sin((t - c) * 14)
    pose["skirt"] = (-0.04 * walk + 0.03 * math.sin(math.pi * 2 * (t - 9.0) / 0.62) * walk, sk)
    # arms
    P_base = root + Z * pose["pelvis_z"]
    hang = {1: V((0.03, 0.235, -0.07)), -1: V((0.03, -0.235, -0.07))}
    for s, sd in ((1, "L"), (-1, "R")):
        swing = -s * 0.12 * math.sin(math.pi * (t - 9.08) / 0.62) * walk
        pose["hand" + sd] = P_base + hang[s] + V((swing, 0, 0.0))
        pose["hdir" + sd] = V((0.15, 0, -1))
        pose["palm" + sd] = V((0, -s, 0))
    if t < 9.0:
        # right hand brushing strokes (local to pelvis base)
        R = [(7.10, V((0.03, -0.235, -0.07))), (7.24, V((0.17, -0.11, 0.30))), (7.50, V((0.19, -0.15, -0.24))),
             (7.62, V((0.18, -0.07, 0.24))), (7.90, V((0.20, -0.13, -0.27))), (8.04, V((0.16, 0.08, 0.38))),
             (8.36, V((0.30, 0.20, 0.06))), (8.55, V((0.10, -0.15, 0.0))), (8.85, V((0.03, -0.235, -0.07)))]
        Lh = [(7.85, V((0.03, 0.235, -0.07))), (8.02, V((0.24, 0.24, 0.05))), (8.40, V((0.25, 0.24, 0.03))),
              (8.70, V((0.03, 0.235, -0.07)))]
        rr = keys(t, R, smooth)
        pose["handR"] = P_base + rr
        pose["hdirR"] = V((0.25, 0.35 if t > 8.0 else 0.1, -1.0)) if t < 8.5 else V((0.15, 0, -1))
        pose["palmR"] = V((-1.0, 0.0, 0.0)) if t < 8.0 else V((-0.3, -1.0, 0.0))
        pose["epoleR"] = P_base + V((-0.2, -0.6, 0.2))
        pose["handL"] = P_base + keys(t, Lh, smooth)
        pose["hdirL"] = V((1.0, 0.0, -0.3)) if 7.95 < t < 8.5 else V((0.15, 0, -1))
        pose["palmL"] = V((0, -0.3, -1)) if 7.95 < t < 8.5 else V((0, -1, 0))
    elif t < 9.95:
        # right hand pushes the door leaf
        push = ramp(t, 9.40, 9.62) * (1 - ramp(t, 9.85, 10.15))
        pose["handR"] = pose["handR"].lerp(P_base + V((0.42, -0.17, 0.42)), push)
        pose["hdirR"] = V((1.0, 0, 0.1)) * push + V((0.15, 0, -1)) * (1 - push)
        pose["palmR"] = V((1.0, 0, 0)) * push + V((0, 1, 0)) * (1 - push)
    return pose


# =====================================================================  rein curves
def make_rein(name, mat):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.0065
    cu.bevel_resolution = 2
    sp = cu.splines.new("POLY")
    sp.points.add(27)
    ob = bpy.data.objects.new(name, cu)
    cu.materials.append(mat)
    U.link(ob)
    return ob


def resample(poly, n):
    seg = [(b - a).length for a, b in zip(poly, poly[1:])]
    total = sum(seg)
    out = []
    for i in range(n):
        d = total * i / (n - 1)
        acc = 0
        for j, L in enumerate(seg):
            if acc + L >= d or j == len(seg) - 1:
                u = (d - acc) / max(L, 1e-9)
                out.append(poly[j].lerp(poly[j + 1], min(1, u)))
                break
            acc += L
    return out


def sag_seg(a, b, sag, n=12):
    pts = []
    for i in range(n + 1):
        u = i / n
        pts.append(a.lerp(b, u) - Z * (sag * math.sin(math.pi * u)))
    return pts


def rein_points(t, bit, hand, s):
    off = V((0, s * 0.012, 0))
    if t < 4.40:
        return sag_seg(bit, hand + off, 0.10)
    y = hand.y
    top = V((E.RAIL_X, y + s * 0.01, E.RAIL_Z + E.RAIL_R + 0.007))
    slack = 0.06 * (1 - ramp(t, 6.45, 6.7)) + 0.012
    if t < 5.40:
        return sag_seg(bit, hand + off, 0.06)
    pts = sag_seg(bit, top, slack)
    if t < 5.95:
        return pts + [hand + off]
    far = V((E.RAIL_X + E.RAIL_R + 0.007, y + s * 0.01, E.RAIL_Z))
    bot = V((E.RAIL_X, y + 0.02 + s * 0.01, E.RAIL_Z - E.RAIL_R - 0.007))
    pts += [far, bot]
    if t < 6.35:
        return pts + [hand + off]
    near = V((E.RAIL_X - E.RAIL_R - 0.007, y + 0.03 + s * 0.01, E.RAIL_Z))
    top2 = V((E.RAIL_X, y + 0.045 + s * 0.01, E.RAIL_Z + E.RAIL_R + 0.007))
    pts += [near, top2]
    tail_hang = hand + off
    if t > 6.95:   # released: free end hangs from the knot
        w = ramp(t, 6.95, 7.3)
        tail_hang = (hand + off).lerp(top2 + V((-0.03, 0.02, -0.28)), w)
    return pts + [tail_hang]


def key_rein(ob, pts, fr):
    pts = resample(pts, 28)
    for i, p in enumerate(pts):
        pt = ob.data.splines[0].points[i]
        pt.co = (p.x, p.y, p.z, 1.0)
        pt.keyframe_insert("co", frame=fr)


# =====================================================================  other characters
def pianist_anim(pn, piano_keys, white_pos):
    ev = music.piano_events()
    P = E.PIANO
    root = V((P["x"], -4.74, E.FLOOR_Z + 0.525))
    yaw = -math.pi / 2

    def keyx(m):
        if m in white_pos:
            return white_pos[m]
        return (white_pos[m - 1] + white_pos[m + 1]) / 2

    hands_ev = {"L": [e for e in ev if e["hand"] == "L"], "R": [e for e in ev if e["hand"] == "R"]}
    stop = PIANO_STOP
    for fr in range(N_FRAMES):
        t = T(fr)
        tt = min(t, stop)
        pose = dict(root=root, yaw=yaw, pelvis_z=0.10, skirt=(0, 0))
        twist = -0.25 * ramp(t, 11.95, 12.6)
        pose["torso"] = (twist, 0.26 - 0.08 * ramp(t, 11.8, 12.4), 0.0)
        pose["head"] = (-0.75 * ramp(t, 12.0, 12.7), 0.35 - 0.3 * ramp(t, 11.9, 12.6), 0.0)
        for s, sd in ((1, "L"), (-1, "R")):
            evs = hands_ev[sd]
            # target x: mean of notes in [tt-0.1, tt+0.3]
            near = [keyx(e["midi"]) for e in evs if tt - 0.1 <= e["t"] <= tt + 0.3]
            if not near:
                prev = [keyx(e["midi"]) for e in evs if e["t"] <= tt]
                near = prev[-2:] if prev else [P["x"] + (0.25 if sd == "L" else -0.1)]
            hx = sum(near) / len(near)
            dip = sum(0.007 * math.exp(-(tt - e["t"]) / 0.05) for e in evs if 0 <= tt - e["t"] < 0.25)
            lift = 0.06 * ramp(t, stop + 0.18, stop + 0.7)
            back = 0.05 * ramp(t, stop + 0.18, stop + 0.7)
            pose["hand" + sd] = V((hx, P["key_y"] + 0.13 + back, P["key_z"] + 0.065 - dip + lift))
            pose["hdir" + sd] = V((0, -1, -0.45))
            pose["palm" + sd] = V((0, 0, -1))
            pose["epole" + sd] = root + V((s * 0.6, 0.3, 0.4))
            pose["foot" + sd] = V((P["x"] + (0.16 if sd == "L" else -0.16), -5.02, E.FLOOR_Z + 0.08))
            pose["fyaw" + sd] = yaw
            pose["kpole" + sd] = root + V((s * 0.2, -1.0, 0.5))
        pn.key(fr, pose)
    for m, k in piano_keys.items():
        k.rotation_mode = "XYZ"
        k.rotation_euler = (0, 0, 0)
        k.keyframe_insert("rotation_euler", frame=0)
    for e in ev:
        k = piano_keys.get(e["midi"])
        if not k:
            continue
        f0 = int(math.floor(e["t"] * FPS))
        f1 = int(math.ceil(min(e["t"] + max(e["dur"], 0.12), PIANO_STOP + 0.05) * FPS))
        if f1 < 0:
            continue
        k.rotation_euler = (0, 0, 0)
        k.keyframe_insert("rotation_euler", frame=max(f0, 0))
        k.rotation_euler = (-0.06, 0, 0)
        k.keyframe_insert("rotation_euler", frame=max(f0 + 1, 1))
        k.keyframe_insert("rotation_euler", frame=max(f1, f0 + 2))
        k.rotation_euler = (0, 0, 0)
        k.keyframe_insert("rotation_euler", frame=max(f1 + 1, f0 + 3))


def seated_pose(root, yaw, twist, hy, hp, hands, feet_fwd=0.42):
    fwd = V((math.cos(yaw), math.sin(yaw), 0))
    side = V((-math.sin(yaw), math.cos(yaw), 0))
    pose = dict(root=root, yaw=yaw, pelvis_z=0.10, torso=(twist, 0.08, 0.0), head=(hy, hp, 0.0), skirt=(0, 0))
    for s, sd in ((1, "L"), (-1, "R")):
        pose["foot" + sd] = V((root.x, root.y, 0)) + fwd * feet_fwd + side * (s * 0.13) + Z * (E.FLOOR_Z + 0.08)
        pose["fyaw" + sd] = yaw + s * 0.15
        pose["kpole" + sd] = root + fwd * 1.0 + Z * 0.5 + side * s * 0.2
        pose["hand" + sd] = hands[s]
        pose["hdir" + sd] = fwd * 0.8 - Z * 0.3
        pose["palm" + sd] = -Z
        pose["epole" + sd] = root + side * s * 0.7 - fwd * 0.3
    return pose


def patrons_anim(A, B, Cc, glass):
    fz = E.FLOOR_Z
    seat = fz + 0.4875
    rootA, yawA = V((8.6, 0.30, seat)), math.pi / 2
    rootB, yawB = V((8.6, 1.70, seat)), -math.pi / 2
    tz = fz + 0.78
    for fr in range(N_FRAMES):
        t = T(fr)
        # --- A: holding a glass, turns to the door, sets the glass down
        turnA = ramp(t, 12.95, 13.6)
        g_up = V((8.72, 0.68, tz + 0.16 + 0.01 * math.sin(t * 2)))
        g_dn = V((8.74, 0.74, tz + 0.0))
        gpos = g_up.lerp(g_dn, ramp(t, 13.25, 13.58))
        handA_R = gpos + V((0.0, -0.07, 0.03))
        handA_L = V((8.42, 0.66, tz + 0.04))
        pa = seated_pose(rootA, yawA, 0.45 * turnA, 1.05 * turnA, 0.05, {1: handA_L, -1: handA_R})
        pa["hdirR"] = V((0.0, 1.0, -0.1))
        pa["palmR"] = V((1.0, 0.0, 0.0))
        A.key(fr, pa)
        glass.location = gpos
        glass.keyframe_insert("location", frame=fr)
        # --- B: idle with cards, turns sharply (chair creak), freezes
        turnB = ramp(t, 12.82, 13.3)
        idle = 0.02 * math.sin(t * 1.3) * (1 - turnB)
        handB_L = V((8.80 + idle, 1.30, tz + 0.04))
        handB_R = V((8.50, 1.30 + idle, tz + 0.045))
        pb = seated_pose(rootB, yawB, -0.42 * turnB, -1.1 * turnB, 0.12 - 0.12 * turnB, {1: handB_L, -1: handB_R})
        B.key(fr, pb)
        # --- C: standing at the bar, right elbow on the counter, turns his head
        yawC = math.radians(165)
        rootC = V((7.45, 2.98, fz))
        fwdC = V((math.cos(yawC), math.sin(yawC), 0))
        sideC = V((-math.sin(yawC), math.cos(yawC), 0))
        turnC = ramp(t, 13.05, 13.7)
        pc = dict(root=rootC, yaw=yawC, pelvis_z=0.95, torso=(0.1 * turnC - 0.15, 0.05, 0.06),
                  head=(-0.9 * turnC + 0.2, 0.08, 0.0), skirt=(0, 0))
        for s, sd in ((1, "L"), (-1, "R")):
            pc["foot" + sd] = rootC + sideC * (s * 0.13) + fwdC * (0.05 if s > 0 else -0.08) + Z * 0.08
            pc["fyaw" + sd] = yawC + s * 0.25
        pc["handR"] = V((7.55, 3.47, fz + 1.20))
        pc["hdirR"] = V((0.3, 0.6, 0.1))
        pc["palmR"] = V((0, 0, -1))
        pc["epoleR"] = rootC + V((0.2, 0.9, 0.9))
        pc["handL"] = rootC + Z * 0.9 + sideC * 0.24 + fwdC * 0.05
        pc["hdirL"] = V((0, 0, -1))
        pc["palmL"] = -sideC
        Cc.key(fr, pc)
    EV["foley"] += [dict(t=12.95, kind="chair_creak", pos=[8.6, 1.7, 0.9]),
                    dict(t=13.58, kind="glass_down", pos=[8.74, 0.74, 1.23]),
                    dict(t=14.55, kind="floor_creak", pos=[STAND_X, 0.0, 0.45])]


# =====================================================================  doors
OPEN_T, OPEN_D, REL_T = 9.55, 0.35, 10.25
AMP = math.radians(80)


def door_angle(t):
    if t < OPEN_T:
        return 0.0
    if t < REL_T:
        return AMP * smoother((t - OPEN_T) / OPEN_D)
    tau = t - REL_T
    return AMP * math.exp(-0.95 * tau) * math.cos(2 * math.pi * tau / 1.15)


def doors_anim(pivots):
    R, L = pivots
    for fr in range(N_FRAMES):
        t = T(fr)
        a = door_angle(t)
        for p, sgn in ((L, 1), (R, -1)):
            p.rotation_mode = "XYZ"
            p.rotation_euler = (0, 0, sgn * a)
            p.keyframe_insert("rotation_euler", frame=fr)
    EV["door"].append(dict(t=OPEN_T + 0.05, amp=1.0, kind="push"))
    k = 0
    while True:
        tau = k * 0.575
        amp = math.exp(-0.95 * tau)
        if amp < 0.06:
            break
        EV["door"].append(dict(t=REL_T + tau + (0.29 if k == 0 else 0.0), amp=amp, kind="swing"))
        k += 1


# =====================================================================  dust puffs
def dust_puffs(coll):
    puffs = [(7.42, V((3.24, -0.17, E.FLOOR_Z + 1.05)), 1.0), (7.80, V((3.25, -0.15, E.FLOOR_Z + 0.98)), 0.9),
             (8.22, V((3.24, 0.18, E.FLOOR_Z + 1.25)), 0.7)]
    for i, (t0, p, a) in enumerate(puffs):
        mat = bpy.data.materials.new("dust%d" % i)
        nt, out = U._nodes(mat)
        vol = nt.nodes.new("ShaderNodeVolumePrincipled")
        vol.inputs["Color"].default_value = (0.75, 0.62, 0.48, 1)
        vol.inputs["Anisotropy"].default_value = 0.55
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = 9.0
        nz.inputs["Detail"].default_value = 4
        tc = nt.nodes.new("ShaderNodeTexCoord")
        nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
        # radial falloff * noise * density
        grad = nt.nodes.new("ShaderNodeTexGradient")
        grad.gradient_type = "SPHERICAL"
        nt.links.new(tc.outputs["Object"], grad.inputs["Vector"])
        mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"
        nt.links.new(grad.outputs["Fac"], mul.inputs[0]); nt.links.new(nz.outputs["Fac"], mul.inputs[1])
        dens = nt.nodes.new("ShaderNodeMath"); dens.operation = "MULTIPLY"; dens.name = "dens"
        nt.links.new(mul.outputs[0], dens.inputs[0])
        nt.links.new(dens.outputs[0], vol.inputs["Density"])
        nt.links.new(vol.outputs[0], out.inputs["Volume"])
        ob = U.prim("sphere", "dust_puff%d" % i, radius=1.0, segs=12, rings=8, mat=mat, coll=coll)
        for fr in range(N_FRAMES):
            t = T(fr)
            u = (t - t0) / 1.1
            if u < 0 or u > 1:
                d, sc = 0.0, 0.01
            else:
                d = 6.0 * a * (1 - u) ** 2 * smooth(u * 8)
                sc = 0.05 + 0.22 * (1 - (1 - u) ** 2)
            dens.inputs[1].default_value = d
            dens.inputs[1].keyframe_insert("default_value", frame=fr)
            ob.location = p + V((-0.04, -0.12, -0.05)) * max(0, u) * 1.5 + V((0, 0, 0.06)) * max(0, u)
            ob.scale = (sc, sc * 1.1, sc * 0.9)
            ob.keyframe_insert("location", frame=fr)
            ob.keyframe_insert("scale", frame=fr)
        EV["cloth"].append(dict(t=t0 - 0.16, dur=0.3, amp=a))


# =====================================================================  cameras
def camera(name, lens, fstop=None):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.sensor_width = 36
    cd.clip_start = 0.05
    cd.clip_end = 5000
    if fstop:
        cd.dof.use_dof = True
        cd.dof.aperture_fstop = fstop
    ob = bpy.data.objects.new(name, cd)
    U.link(ob)
    return ob


def look(cam, pos, tgt, fr, roll=0.0, focus=None):
    d = (tgt - pos).normalized()
    m = U.frame_matrix(pos, -d, Z)       # camera looks down -Z; X must be horizontal-ish
    # rebuild with x = right
    right = d.cross(Z).normalized()
    up = right.cross(d).normalized()
    mm = Matrix(((right.x, up.x, -d.x, pos.x), (right.y, up.y, -d.y, pos.y), (right.z, up.z, -d.z, pos.z),
                 (0, 0, 0, 1)))
    if roll:
        mm = mm @ Matrix.Rotation(roll, 4, "Z")
    U.key_matrix(cam, mm, fr)
    if focus is not None and cam.data.dof.use_dof:
        cam.data.dof.focus_distance = focus
        cam.data.dof.keyframe_insert("focus_distance", frame=fr)


def cameras(horse_track, shots):
    cams = {}
    c1 = camera("CAM_S1", 30, 5.6)
    c2 = camera("CAM_S2", 35, 2.0)
    c3 = camera("CAM_S3", 40, 2.8)
    c4 = camera("CAM_S4", 24, 4.0)
    c5 = camera("CAM_S5", 42, 2.8)
    c6 = camera("CAM_S6", 32, 4.0)
    cams.update(S1_street=c1, S2_tie=c2, S3_brush=c3, S4_step=c4, S5_piano=c5, S6_silence=c6)
    for fr in range(N_FRAMES):
        t = T(fr)
        # S1: low street, slow crane-up + push, horse approaching against the low sun
        u = smooth(t / 4.4)
        pos = V((1.25, -15.2, 1.05)).lerp(V((0.75, -13.4, 1.65)), u)
        hpos = horse_track[min(fr, len(horse_track) - 1)]
        tgt = V((-0.6, 0.5, 1.9)).lerp(hpos + V((0.2, 0, 1.25)), smooth(min(1, t / 4.2)))
        look(c1, pos, tgt, fr, focus=(hpos - pos).length)
        # S2: medium -> close on the gloved hands at the rail (backlit)
        u = smoother((t - 4.4) / 2.7)
        pos = V((2.55, -4.85, 1.50)).lerp(V((2.10, -4.55, 1.16)), u)
        tgt = V((1.36, -3.42, 1.30)).lerp(V((1.57, -3.70, 1.02)), u)
        look(c2, pos, tgt, fr, focus=(V((1.45, -3.62, 1.15)).lerp(V((1.57, -3.70, 1.02)), u) - pos).length)
        c2.data.lens = lerp(36, 50, u)
        c2.data.keyframe_insert("lens", frame=fr)
        # S3: profile on the porch, slight arc
        u = smooth((t - 7.1) / 1.87)
        pos = V((3.52, -2.95, 1.92)).lerp(V((3.40, -2.62, 1.86)), u)
        tgt = V((3.06, 0.0, 1.70)).lerp(V((3.05, 0.0, 1.68)), u)
        look(c3, pos, tgt, fr, focus=(V((3.05, 0, 1.3)) - pos).length)
        # S4: low behind the boots, following through the doors
        u = smooth((t - 8.97) / 1.96)
        pos = V((2.30, 0.10, 0.63)).lerp(V((3.30, 0.04, 0.64)), u)
        tgt = V((4.5, 0.0, 0.98)).lerp(V((5.6, 0.0, 1.05)), u)
        look(c4, pos, tgt, fr, focus=max(0.6, keys(t, WALK_ROOT, smooth) - pos.x))
        # S5: piano hands
        u = smooth((t - 10.93) / 1.8)
        pos = V((9.15, -4.74, 1.74)).lerp(V((9.08, -4.78, 1.70)), u)
        tgt = V((8.00, -5.20, 1.20)).lerp(V((8.02, -5.15, 1.24)), u)
        look(c5, pos, tgt, fr, focus=(V((8.15, -5.12, 1.24)) - pos).length)
        # S6: wide interior towards the stranger in the doorway, slow push
        u = smooth((t - 12.73) / 3.27)
        pos = V((13.5, -1.25, 1.58)).lerp(V((11.75, -0.85, 1.55)), u)
        tgt = V((4.6, 0.30, 1.40)).lerp(V((4.8, 0.2, 1.42)), u)
        look(c6, pos, tgt, fr, focus=(V((STAND_X, 0, 1.4)) - pos).length)
    return cams


# =====================================================================  main
def main():
    random.seed(1)
    sc = setup_scene()
    world_and_sun(sc)
    coll = sc.collection
    E.materials()
    E.ground(coll)
    E.town(coll)
    E.saloon(coll)
    E.text_sign(coll)
    E.props_exterior(coll)
    pivots = E.batwing_doors(coll)
    E.interior(coll)
    white_pos = {}
    pkeys = E.piano(coll, white_pos)
    E.lamps(coll)
    C = CH.char_materials()
    horse = CH.Horse(C, coll)
    CH.Horse.seat_local_static = horse.seat_local
    CH.Horse.stirrup_static = horse.stirrup_local
    stranger = CH.Person("stranger", C, coll, top="coat", sleeves="coat", hands="glove", hat="cowboy", skirt=True,
                         beard=True, gunbelt=True, bandana=True)
    pianist = CH.Person("pianist", C, coll, top="vest", sleeves="white", legs="trousers", hat="bowler",
                        hands="skin_pale", skirt=False, skin="skin_pale", beard=False, hatmat="vest", curl=(0.45, 0.5))
    patA = CH.Person("patronA", C, coll, top="jacket", sleeves="jacket", hat="cowboy", hands="skin", skirt=False,
                     beard=True, hatmat="hat", curl=(0.9, 1.0))
    patB = CH.Person("patronB", C, coll, top="blue", sleeves="blue", hat="cowboy", hands="skin", skirt=False,
                     beard=True, hatmat="band", curl=(0.5, 0.6))
    patC = CH.Person("patronC", C, coll, top="darkcoat", sleeves="darkcoat", hat="cowboy", hands="skin", skirt=True,
                     beard=True, hatmat="band")
    glass = U.lathe("whiskey_glass", [(0.03, 0.0), (0.034, 0.085), (0.032, 0.09)], segs=14, mat=E.M["glass"],
                    coll=coll, close_top=False)
    liquor = U.lathe("whiskey", [(0.028, 0.004), (0.031, 0.04), (0.001, 0.041)], segs=14,
                     mat=U.principled("whiskey_m", (0.45, 0.18, 0.04), rough=0.1, transmission=0.6), coll=coll)
    U.parent(liquor, glass, keep=False)
    reins = {s: make_rein("rein_%d" % s, C["leather"]) for s in (1, -1)}

    hp = HorsePath()
    horse_track = []

    def rider_cb(fr, t, pos, yaw, bob, pitch, roll, neck, M):
        horse_track.append(pos.copy())
        pose = stranger_pose(t, (pos, yaw, bob, pitch, roll, neck, M))
        stranger.key(fr, pose)
        if t < 7.4:
            for s in (1, -1):
                bit = horse.world_bit(pos, yaw, bob, pitch, roll, neck, s)
                hd = pose["hand" + ("L" if s > 0 else "R")] if t < 4.4 else pose["handR"]
                hdir = pose.get("hdir" + ("L" if s > 0 else "R"), V((0, 0, -1))) if t < 4.4 else pose["hdirR"]
                grip = hd + hdir.normalized() * 0.09
                key_rein(reins[s], rein_points(t, bit, grip, s), fr)

    build_horse_anim(horse, hp, rider_cb)
    # stepping events for audio
    for (sd, lf, pl, x0, x1) in STEPS:
        EV["step"].append(dict(t=pl, side=sd, x=x1, surface="porch" if x1 < 4.0 else "floor"))
    EV["step"].insert(0, dict(t=9.10, side="L", x=3.05, surface="porch", scuff=True))
    EV["rein"] += [dict(t=5.42, kind="over_rail"), dict(t=5.97, kind="wrap"), dict(t=6.22, kind="wrap2"),
                   dict(t=6.62, kind="snug")]
    pianist_anim(pianist, pkeys, white_pos)
    patrons_anim(patA, patB, patC, glass)
    doors_anim(pivots)
    dust_puffs(coll)
    cams = cameras(horse_track, SHOTS)
    # camera switching markers + per-shot exposure
    expo = {"S1_street": -0.55, "S2_tie": -0.45, "S3_brush": -0.45, "S4_step": -0.2, "S5_piano": 0.6,
            "S6_silence": 0.6}
    for name, a, b in SHOTS:
        m = sc.timeline_markers.new(name, frame=int(round(a * FPS)))
        m.camera = cams[name]
    sc.camera = cams["S1_street"]
    json.dump(dict(shots=SHOTS, exposure=expo, hp_len=hp.L, hp_v=hp.v, events=EV),
              open(os.path.join(BUILD, "events.json"), "w"), indent=1, default=list)
    sc["exposure_by_shot"] = json.dumps(expo)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(BUILD, "oldwest.blend"))
    print("saved; horse path L=%.2f v=%.2f, hoof events=%d" % (hp.L, hp.v, len(EV["hoof"])))


if __name__ == "__main__":
    main()
