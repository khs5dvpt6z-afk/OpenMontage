"""Frontier town + saloon environment (procedural, all geometry built in code)."""
import math
import random

import bpy
from mathutils import Vector

import bl_util as U
from bl_util import V

X, Y, Z = V((1, 0, 0)), V((0, 1, 0)), V((0, 0, 1))

# key layout constants (world metres)
SALOON_FRONT_X = 4.0
FLOOR_Z = 0.45            # porch + saloon floor top
DOOR_HALF = 0.85          # door opening half width
DOOR_HINGE_Y = 0.82
DOOR_LEAF_W = 0.80
DOOR_LEAF_Z = (0.90, 2.10)
RAIL_X, RAIL_Z = 1.60, 1.00
RAIL_Y = (-5.45, -2.65)
RAIL_R = 0.055
PIANO = dict(x=8.2, y_wall=-5.85, key_y=-5.22, key_z=1.18, width=1.30)
SUN_DIR = V((-0.30, 0.954, 0.105)).normalized()    # direction TOWARDS the sun (elev ~6 deg)

M = {}   # materials


def materials():
    M["wood_front"] = U.wood_mat("wood_front", warm=(0.36, 0.21, 0.11), gray=(0.42, 0.37, 0.31), weathered=0.55,
                                 paint=(0.55, 0.47, 0.36), paint_amt=0.6)
    M["wood_dark"] = U.wood_mat("wood_dark", warm=(0.22, 0.12, 0.06), gray=(0.30, 0.26, 0.21), weathered=0.4)
    M["wood_gray"] = U.wood_mat("wood_gray", warm=(0.30, 0.22, 0.15), gray=(0.42, 0.40, 0.36), weathered=0.8)
    M["wood_red"] = U.wood_mat("wood_red", warm=(0.30, 0.12, 0.07), gray=(0.38, 0.30, 0.25), weathered=0.45,
                               paint=(0.33, 0.10, 0.07), paint_amt=0.8)
    M["wood_floor"] = U.wood_mat("wood_floor", warm=(0.30, 0.17, 0.09), gray=(0.34, 0.28, 0.21), weathered=0.35,
                                 rough=0.7)
    M["wood_int"] = U.wood_mat("wood_int", warm=(0.27, 0.14, 0.07), gray=(0.30, 0.22, 0.15), weathered=0.25,
                               rough=0.75)
    M["wood_polish"] = U.wood_mat("wood_polish", warm=(0.16, 0.07, 0.03), gray=(0.2, 0.1, 0.05), weathered=0.1,
                                  rough=0.35, bump=0.1)
    M["dirt"] = U.dirt_mat("dirt")
    M["glass"] = U.glass_mat("glass")
    M["iron"] = U.principled("iron", (0.05, 0.045, 0.04), rough=0.55, metal=0.8)
    M["paint_sign"] = U.noisy_mat("paint_sign", (0.78, 0.70, 0.55), (0.62, 0.52, 0.38), scale=30, rough=0.8, bump=0.1)
    M["mesa"] = U.haze_mat("mesa", (0.30, 0.16, 0.09), haze=(0.98, 0.58, 0.36), dist=1400.0, strength=1.1)
    M["far_bldg"] = U.haze_mat("far_bldg", (0.16, 0.10, 0.07), haze=(0.95, 0.58, 0.36), dist=380.0, strength=1.0)
    M["bottle_g"] = U.principled("bottle_g", (0.05, 0.12, 0.05), rough=0.12, spec=0.8, coat=0.5)
    M["bottle_b"] = U.principled("bottle_b", (0.15, 0.06, 0.02), rough=0.12, spec=0.8, coat=0.5)
    M["brass"] = U.principled("brass", (0.55, 0.38, 0.14), rough=0.3, metal=1.0)
    M["lamp_glow"] = U.emission_mat("lamp_glow", (1.0, 0.62, 0.28), 18.0)
    M["felt"] = U.noisy_mat("felt", (0.09, 0.16, 0.08), (0.06, 0.12, 0.06), scale=40, rough=1.0, bump=0.05)
    M["canvas"] = U.noisy_mat("canvas", (0.28, 0.20, 0.12), (0.12, 0.09, 0.07), scale=3, rough=0.9, bump=0.05)
    M["ivory"] = U.principled("ivory", (0.78, 0.72, 0.58), rough=0.35)
    M["ebony"] = U.principled("ebony", (0.02, 0.018, 0.015), rough=0.3)
    M["water"] = U.principled("water", (0.02, 0.03, 0.025), rough=0.05, spec=0.6)
    M["hay"] = U.noisy_mat("hay", (0.55, 0.42, 0.18), (0.35, 0.25, 0.10), scale=60, rough=1.0, bump=0.3)
    return M


# ---------------------------------------------------------------- planked wall helper
def plank_wall(bb, origin, u, length, height, normal, openings=(), plank_w=0.21, thick=0.04, vertical=True,
               jitter=0.006, gap=0.008, battens=True):
    """Wall in a local (u along wall, v up) frame. openings: list of (u0, u1, v0, v1)."""
    n = normal.normalized()
    u = u.normalized()
    if vertical:
        count = max(1, int(length / plank_w))
        w = length / count
        for i in range(count):
            u0, u1 = i * w, (i + 1) * w
            segs = [(0.0, height)]
            for (a0, a1, b0, b1) in openings:
                if u1 > a0 and u0 < a1:
                    new = []
                    for (s0, s1) in segs:
                        if s1 <= b0 or s0 >= b1:
                            new.append((s0, s1))
                        else:
                            if s0 < b0:
                                new.append((s0, b0))
                            if s1 > b1:
                                new.append((b1, s1))
                    segs = new
            r = random.random()
            for (s0, s1) in segs:
                if s1 - s0 < 0.02:
                    continue
                c = origin + u * ((u0 + u1) / 2) + Z * ((s0 + s1) / 2) + n * (random.uniform(-jitter, jitter))
                bb.box(c, (s1 - s0, w - gap, thick), ax=Z, ay=u, az=n, rnd=r)
            if battens and i % 1 == 0 and i > 0:
                bsegs = segs
                for (s0, s1) in bsegs:
                    if s1 - s0 < 0.02:
                        continue
                    c = origin + u * u0 + Z * ((s0 + s1) / 2) + n * (thick * 0.5 + 0.012)
                    bb.box(c, (s1 - s0, 0.055, 0.025), ax=Z, ay=u, az=n)
    else:
        count = max(1, int(height / plank_w))
        h = height / count
        for i in range(count):
            v0, v1 = i * h, (i + 1) * h
            segs = [(0.0, length)]
            for (a0, a1, b0, b1) in openings:
                if v1 > b0 and v0 < b1:
                    new = []
                    for (s0, s1) in segs:
                        if s1 <= a0 or s0 >= a1:
                            new.append((s0, s1))
                        else:
                            if s0 < a0:
                                new.append((s0, a0))
                            if s1 > a1:
                                new.append((a1, s1))
                    segs = new
            for (s0, s1) in segs:
                # split long runs into board lengths
                pos = s0
                while pos < s1 - 0.01:
                    L = min(s1 - pos, random.uniform(2.5, 4.5))
                    c = origin + u * (pos + L / 2) + Z * ((v0 + v1) / 2) + n * random.uniform(-jitter, jitter)
                    bb.box(c, (L - 0.004, h - gap, thick), ax=u, ay=Z, az=n)
                    pos += L


def frame_opening(bb, origin, u, n, a0, a1, b0, b1, w=0.09, d=0.07, sill=True):
    """trim boards around an opening on a wall."""
    c = lambda uu, vv: origin + u * uu + Z * vv + n * 0.035
    bb.box(c(a0 - w / 2, (b0 + b1) / 2), (b1 - b0 + 2 * w, w, d), ax=Z, ay=u, az=n)
    bb.box(c(a1 + w / 2, (b0 + b1) / 2), (b1 - b0 + 2 * w, w, d), ax=Z, ay=u, az=n)
    bb.box(c((a0 + a1) / 2, b1 + w / 2), (a1 - a0 + 2 * w + 0.06, w * 1.3, d), ax=u, ay=Z, az=n)
    if sill:
        bb.box(c((a0 + a1) / 2, b0 - w / 2) + n * 0.02, (a1 - a0 + 2 * w + 0.08, w, d + 0.06), ax=u, ay=Z, az=n)


def window(bb, origin, u, n, a0, a1, b0, b1, coll, name, glass=True, curtains=None):
    frame_opening(bb, origin, u, n, a0, a1, b0, b1)
    # mullions
    mid = (a0 + a1) / 2
    bb.box(origin + u * mid + Z * ((b0 + b1) / 2), (b1 - b0, 0.04, 0.05), ax=Z, ay=u, az=n)
    for k in (1, 2):
        vv = b0 + (b1 - b0) * k / 3
        bb.box(origin + u * mid + Z * vv, (a1 - a0, 0.035, 0.05), ax=u, ay=Z, az=n)
    if glass:
        c = origin + u * mid + Z * ((b0 + b1) / 2)
        g = U.mesh_obj(name + "_glass", [c + u * (a0 - mid) + Z * (b0 - (b0 + b1) / 2),
                                         c + u * (a1 - mid) + Z * (b0 - (b0 + b1) / 2),
                                         c + u * (a1 - mid) + Z * (b1 - (b0 + b1) / 2),
                                         c + u * (a0 - mid) + Z * (b1 - (b0 + b1) / 2)],
                       [(0, 1, 2, 3)], M["glass"], coll=coll)
    if curtains:
        for side in (a0 + 0.12, a1 - 0.12):
            cc = origin + u * side + Z * ((b0 + b1) / 2 + 0.05) - n * 0.08
            U.prim("cube", name + "_curt", loc=cc, scale=(0.0, 0, 0), mat=curtains, coll=coll, smooth_shade=False)
            ob = bpy.context.scene.objects[-1] if False else None


def building(name, front_origin, u, width, depth, height, ff_height, mat, coll, door=None, windows=(),
             porch=False, roof_mat=None, awning=False):
    """Generic false-front building. front_origin = left-bottom of front wall (ground), u runs along front,
    n = outward normal (towards the street)."""
    bb = U.BoxBatch()
    n = Z.cross(u).normalized()   # outward normal (towards the street)
    d = -n  # into the building
    openings = []
    if door:
        openings.append(door)
    openings += list(windows)
    plank_wall(bb, front_origin, u, width, ff_height, n, openings)
    for (a0, a1, b0, b1) in windows:
        window(bb, front_origin, u, n, a0, a1, b0, b1, coll, name + "_w%d" % int(a0 * 10))
    if door:
        a0, a1, b0, b1 = door
        frame_opening(bb, front_origin, u, n, a0, a1, b0, b1, sill=False)
        # closed door panel set back a little
        c = front_origin + u * ((a0 + a1) / 2) + Z * ((b0 + b1) / 2) - n * 0.06
        bb.box(c, (b1 - b0, a1 - a0, 0.05), ax=Z, ay=u, az=n)
    # cornice on false front
    bb.box(front_origin + u * (width / 2) + Z * (ff_height + 0.06) + n * 0.06, (width + 0.3, 0.14, 0.22),
           ax=u, ay=Z, az=n)
    bb.box(front_origin + u * (width / 2) + Z * (height + 0.1) + n * 0.05, (width + 0.1, 0.1, 0.12),
           ax=u, ay=Z, az=n)
    # side walls (horizontal clapboard) and back
    for side in (0, 1):
        o = front_origin + u * (width * side) + d * 0.0
        plank_wall(bb, o, d, depth, height, u * (1 if side else -1), (), plank_w=0.2, vertical=False)
    plank_wall(bb, front_origin + d * depth, u, width, height, -n, (), plank_w=0.2, vertical=False)
    # simple gable roof planes behind the false front
    rm = roof_mat or M["wood_gray"]
    ridge = height + 1.0
    for s in (0, 1):
        a = front_origin + u * (width * 0.5) + Z * ridge
        b = front_origin + u * (width * s) + Z * height
        mid = (a + b) / 2 + d * (depth / 2)
        ax = (b - a).normalized()
        bb.box(mid, ((b - a).length + 0.2, depth + 0.2, 0.06), ax=ax, ay=d, az=ax.cross(d).normalized())
    if porch:
        pd = 1.6
        for i in range(int(width / 0.16)):
            c = front_origin + u * (0.08 + i * 0.16) + n * (pd / 2) + Z * 0.38
            bb.box(c, (pd, 0.15, 0.04), ax=n, ay=u, az=Z)
        bb.box(front_origin + u * (width / 2) + n * (pd - 0.05) + Z * 0.22, (width, 0.08, 0.3), ax=u, ay=n, az=Z)
        for p in (0.15, width - 0.15):
            bb.box(front_origin + u * p + n * (pd - 0.1) + Z * 1.6, (3.2, 0.12, 0.12), ax=Z, ay=u, az=n)
        a = front_origin + u * (width / 2) + n * (pd / 2) + Z * 3.1
        bb.box(a, (pd + 0.2, width + 0.2, 0.06), ax=n, ay=u, az=Z)
    ob = bb.build(name, mat, coll)
    return ob


# ---------------------------------------------------------------- the saloon
def saloon(coll):
    fx = SALOON_FRONT_X
    bb = U.BoxBatch()      # exterior front/side planks
    bi = U.BoxBatch()      # interior surfaces
    bf = U.BoxBatch()      # floors (porch + interior)
    # front wall: u along +Y from y=-6, normal -X
    o = V((fx, -6.0, 0.0))
    door = (6.0 - DOOR_HALF, 6.0 + DOOR_HALF, FLOOR_Z, 3.05)
    w1 = (6.0 - 3.9 - 0.68, 6.0 - 3.9 + 0.68, 1.45, 2.85)
    w2 = (6.0 + 3.9 - 0.68, 6.0 + 3.9 + 0.68, 1.45, 2.85)
    plank_wall(bb, o, Y, 12.0, 6.3, -X, [door, w1, w2], plank_w=0.22)
    for i, w in enumerate((w1, w2)):
        window(bb, o, Y, -X, *w, coll, "saloon_w%d" % i)
    frame_opening(bb, o, Y, -X, *door, sill=False)
    # transom over the door
    bb.box(o + Y * 6.0 + Z * 3.2 - X * 0.04, (0.12, 2.0, 0.08), ax=Z, ay=Y, az=-X)
    # cornice + stepped false-front top
    bb.box(o + Y * 6.0 + Z * 6.36 - X * 0.07, (12.4, 0.16, 0.24), ax=Y, ay=Z, az=-X)
    bb.box(o + Y * 6.0 + Z * 4.55 - X * 0.05, (12.2, 0.12, 0.14), ax=Y, ay=Z, az=-X)
    for yy in (0.2, 11.8):
        bb.box(o + Y * yy + Z * 3.2 - X * 0.07, (6.4, 0.18, 0.12), ax=Z, ay=Y, az=-X)
    # sign board
    bb.box(o + Y * 6.0 + Z * 5.35 - X * 0.09, (0.95, 6.4, 0.05), ax=Z, ay=Y, az=-X)
    bb.box(o + Y * 6.0 + Z * 5.85 - X * 0.12, (0.06, 6.6, 0.07), ax=Z, ay=Y, az=-X)
    bb.box(o + Y * 6.0 + Z * 4.85 - X * 0.12, (0.06, 6.6, 0.07), ax=Z, ay=Y, az=-X)
    # side walls (clapboard) y=-6 and y=+6, x from 4 to 16
    for side, yy in ((-1, -6.0), (1, 6.0)):
        plank_wall(bb, V((fx, yy, 0)), X, 12.0, 4.5, Y * side, (), plank_w=0.2, vertical=False)
    plank_wall(bb, V((fx + 12.0, -6, 0)), Y, 12.0, 4.5, X, (), plank_w=0.2, vertical=False)
    # roof
    for s in (-1, 1):
        a = V((fx + 6, 0, 5.4))
        b = V((fx + 6, 6.2 * s, 4.5))
        ax = (b - a).normalized()
        bb.box((a + b) / 2, ((b - a).length, 12.3, 0.07), ax=ax, ay=X, az=ax.cross(X).normalized())
    ext = bb.build("saloon_exterior", M["wood_front"], coll)

    # porch deck: planks run along Y, x from 2.4 to 4.0
    px0, px1 = 2.4, fx
    n_planks = int((px1 - px0) / 0.145)
    for i in range(n_planks):
        xx = px0 + 0.0725 + i * 0.145
        yy = -6.0
        while yy < 6.0 - 0.01:
            L = min(6.0 - yy, random.uniform(1.8, 3.6))
            bf.box(V((xx, yy + L / 2, FLOOR_Z - 0.02)), (L - 0.006, 0.137, 0.04), ax=Y, ay=X, az=Z)
            yy += L
    # fascia + joists under porch
    bf.box(V((px0 - 0.03, 0, FLOOR_Z - 0.2)), (12.0, 0.06, 0.36), ax=Y, ay=X, az=Z)
    for yy in (-5.9, 5.9):
        bf.box(V(((px0 + px1) / 2, yy, FLOOR_Z - 0.2)), (px1 - px0, 0.06, 0.36), ax=X, ay=Y, az=Z)
    # steps in front of the door (two treads)
    for k, (sx, sz) in enumerate(((px0 - 0.32, 0.22), (px0 - 0.16, 0.34))):
        pass
    bf.box(V((px0 - 0.17, 0, 0.11)), (0.34, 2.2, 0.22), ax=X, ay=Y, az=Z)
    bf.box(V((px0 - 0.17, 0, 0.215)), (0.36, 2.25, 0.035), ax=X, ay=Y, az=Z)
    # interior floor planks along X
    for i in range(int(11.8 / 0.145)):
        yy = -5.9 + 0.0725 + i * 0.145
        xx = fx
        while xx < fx + 11.9:
            L = min(fx + 11.95 - xx, random.uniform(2.0, 4.0))
            bf.box(V((xx + L / 2, yy, FLOOR_Z - 0.02)), (L - 0.006, 0.137, 0.04), ax=X, ay=Y, az=Z)
            xx += L
    # threshold board
    bf.box(V((fx + 0.03, 0, FLOOR_Z + 0.005)), (0.16, 2 * DOOR_HALF, 0.03), ax=X, ay=Y, az=Z)
    floor = bf.build("floors", M["wood_floor"], coll)

    # porch posts + roof
    bp = U.BoxBatch()
    for yy in (-5.9, -2.1, 2.1, 5.9):
        bp.box(V((2.52, yy, (FLOOR_Z + 3.15) / 2)), (3.15 - FLOOR_Z, 0.13, 0.13), ax=Z, ay=X, az=Y)
        # brackets
        for s in (-1, 1):
            c = V((2.52, yy + s * 0.22, 2.95))
            ax = V((0, s, 0.9)).normalized()
            bp.box(c, (0.42, 0.06, 0.06), ax=ax, ay=X, az=ax.cross(X))
    bp.box(V((2.52, 0, 3.17)), (12.2, 0.16, 0.16), ax=Y, ay=X, az=Z)
    for i in range(int(1.8 / 0.2) + 1):
        xx = 2.35 + i * 0.2
        bp.box(V((xx, 0, 3.27 + (xx - 2.35) * 0.08)), (12.4, 0.19, 0.03), ax=Y, ay=X, az=Z)
    # hitching rail (posts + round rail added separately)
    for yy in (-5.25, -2.85):
        bp.box(V((RAIL_X, yy, 0.55)), (1.1, 0.12, 0.12), ax=Z, ay=X, az=Y, rnd=0.3)
    bp.build("porch_posts", M["wood_gray"], coll)
    rail = U.prim("cyl", "hitch_rail", loc=(RAIL_X, sum(RAIL_Y) / 2, RAIL_Z), rot=(math.pi / 2, 0, 0),
                  radius=RAIL_R, depth=RAIL_Y[1] - RAIL_Y[0], segs=16, mat=M["wood_gray"], coll=coll)
    rm = rail.data
    uvl = rm.uv_layers.new(name="UVMap")
    for poly in rm.polygons:
        for li in poly.loop_indices:
            co = rm.vertices[rm.loops[li].vertex_index].co
            uvl.data[li].uv = (co.z * 1.0, math.atan2(co.y, co.x) * RAIL_R)
    at = rm.attributes.new("prand", "FLOAT", "POINT")
    at.data.foreach_set("value", [0.8] * len(rm.vertices))

    # interior walls (horizontal boards) slightly inside the exterior walls
    ix0, ix1, iy0, iy1 = fx + 0.06, fx + 11.94, -5.94, 5.94
    door_i = (6.0 - DOOR_HALF - 0.06, 6.0 + DOOR_HALF + 0.06, 0.0, 3.05)
    plank_wall(bi, V((ix0, iy0, FLOOR_Z)), Y, iy1 - iy0, 3.6,
               X, [(w1[0] - 0.06, w1[1] + 0.06, w1[2] - FLOOR_Z, w1[3] - FLOOR_Z),
                   (w2[0] - 0.06, w2[1] + 0.06, w2[2] - FLOOR_Z, w2[3] - FLOOR_Z),
                   (door_i[0] - 0.06, door_i[1] - 0.06, 0, 2.6)], plank_w=0.18, vertical=False)
    for side, yy in ((1, iy0), (-1, iy1)):
        plank_wall(bi, V((ix0, yy, FLOOR_Z)), X, ix1 - ix0, 3.6, Y * side,
                   [], plank_w=0.18, vertical=False)
    plank_wall(bi, V((ix1, iy0, FLOOR_Z)), Y, iy1 - iy0, 3.6, -X, [], plank_w=0.18, vertical=False)
    # wainscot rail + ceiling + beams
    for (a, b, nrm) in ((V((ix0, iy0, 0)), V((ix0, iy1, 0)), X), (V((ix0, iy0, 0)), V((ix1, iy0, 0)), Y),
                        (V((ix0, iy1, 0)), V((ix1, iy1, 0)), -Y), (V((ix1, iy0, 0)), V((ix1, iy1, 0)), -X)):
        ax = (b - a).normalized()
        bi.box((a + b) / 2 + Z * (FLOOR_Z + 1.0) + nrm * 0.03, ((b - a).length, 0.07, 0.04), ax=ax, ay=Z, az=nrm)
        bi.box((a + b) / 2 + Z * (FLOOR_Z + 0.08) + nrm * 0.02, ((b - a).length, 0.16, 0.03), ax=ax, ay=Z, az=nrm)
    for i in range(int((iy1 - iy0) / 0.16)):
        yy = iy0 + 0.08 + i * 0.16
        bi.box(V(((ix0 + ix1) / 2, yy, FLOOR_Z + 3.62)), (ix1 - ix0, 0.15, 0.03), ax=X, ay=Y, az=Z)
    for xx in (6.5, 9.5, 12.5):
        bi.box(V((xx, 0, FLOOR_Z + 3.5)), (iy1 - iy0, 0.18, 0.22), ax=Y, ay=X, az=Z)
    bi.build("saloon_interior", M["wood_int"], coll)

    # interior window glass already from exterior window(); side window openings get glass too
    for (cx, cy, nrm) in ((5.8 + fx, iy1, -Y), (7.6 + fx, iy0, Y)):
        pass
    return ext


def batwing_doors(coll):
    """two swinging leaves; returns pivot empties (rotate about Z)."""
    piv = []
    for s in (-1, 1):
        e = U.empty("door_pivot_%s" % ("R" if s < 0 else "L"), loc=(SALOON_FRONT_X + 0.02, s * DOOR_HINGE_Y, 0), coll=coll)
        bb = U.BoxBatch()
        z0, z1 = DOOR_LEAF_Z
        w = DOOR_LEAF_W
        # local frame: leaf extends from hinge toward centre (-s*Y)
        dirn = V((0, -s, 0))
        c = lambda t, z: dirn * t + Z * z
        bb.box(c(0.04, (z0 + z1) / 2), (z1 - z0, 0.08, 0.045), ax=Z, ay=dirn, az=X)       # hinge stile
        bb.box(c(w - 0.04, (z0 + z1 - 0.15) / 2), (z1 - z0 - 0.15, 0.08, 0.045), ax=Z, ay=dirn, az=X)
        bb.box(c(w / 2, z0 + 0.05), (0.1, w, 0.045), ax=Z, ay=dirn, az=X)
        bb.box(c(w / 2, z0 + 0.55), (0.08, w, 0.045), ax=Z, ay=dirn, az=X)
        # curved top rail approximated by 6 segments descending toward the centre
        for k in range(6):
            t0, t1 = k / 6 * w, (k + 1) / 6 * w
            h0 = z1 - 0.15 * (1 - math.cos(math.pi * (t0 / w))) / 2
            h1 = z1 - 0.15 * (1 - math.cos(math.pi * (t1 / w))) / 2
            pa, pb = c(t0, h0 - 0.04), c(t1, h1 - 0.04)
            ax = (pb - pa).normalized()
            bb.box((pa + pb) / 2, ((pb - pa).length + 0.01, 0.08, 0.045), ax=ax, ay=ax.cross(X), az=X)
        # louvers between rails
        for k in range(9):
            zz = z0 + 0.62 + k * 0.075
            if zz > z1 - 0.2:
                break
            bb.box(c(w / 2, zz), (0.065, w - 0.12, 0.012), ax=Z.copy(), ay=dirn, az=X, rnd=0.2)
        # lower panel
        bb.box(c(w / 2, z0 + 0.3), (0.42, w - 0.12, 0.02), ax=Z, ay=dirn, az=X)
        ob = bb.build("door_leaf_%s" % ("R" if s < 0 else "L"), M["wood_red"], coll)
        ob.location = e.location
        U.parent(ob, e)
        # brass hinges
        for zz in (z0 + 0.15, z1 - 0.2):
            h = U.prim("cyl", "hinge", loc=(SALOON_FRONT_X + 0.02, s * DOOR_HINGE_Y, zz), radius=0.018, depth=0.12,
                       segs=8, mat=M["brass"], coll=coll)
            U.parent(h, e)
        piv.append(e)
    return piv


def text_sign(coll):
    cu = bpy.data.curves.new("sign_text", "FONT")
    cu.body = "SALOON"
    cu.size = 0.62
    cu.extrude = 0.012
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.space_character = 1.15
    ob = bpy.data.objects.new("sign_text", cu)
    ob.location = (SALOON_FRONT_X - 0.125, 0, 5.36)
    ob.rotation_euler = (math.pi / 2, 0, -math.pi / 2)
    cu.materials.append(M["paint_sign"])
    U.link(ob, coll)
    return ob


# ---------------------------------------------------------------- props
def barrel(name, loc, coll, h=0.9, r=0.3):
    prof = [(r * 0.86, 0), (r * 0.95, h * 0.2), (r, h * 0.5), (r * 0.95, h * 0.8), (r * 0.86, h)]
    ob = U.lathe(name, prof, segs=20, mat=M["wood_dark"], coll=coll)
    me = ob.data
    uvl = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uvl.data[li].uv = (co.z * 2, math.atan2(co.y, co.x) * r * 3)
    at = me.attributes.new("prand", "FLOAT", "POINT")
    at.data.foreach_set("value", [random.random()] * len(me.vertices))
    ob.location = loc
    for zz in (0.12, 0.5, 0.88):
        rr = r * (0.9 if zz != 0.5 else 1.0) + 0.006
        hoop = U.lathe(name + "_hoop", [(rr, h * zz - 0.03), (rr, h * zz + 0.03)], segs=20, mat=M["iron"],
                       coll=coll, close_top=False, close_bottom=False)
        hoop.location = loc
    return ob


def crate(bb, c, s):
    for i in range(3):
        bb.box(V(c) + Z * (-s / 2 + s / 6 + i * s / 3), (s, s / 3 - 0.01, s), ax=X, ay=Z, az=Y)


def props_exterior(coll):
    random.seed(11)
    barrel("barrel1", V((2.75, -5.4, FLOOR_Z)), coll)
    barrel("barrel2", V((3.3, -5.55, FLOOR_Z)), coll, h=0.8, r=0.27)
    barrel("barrel3", V((2.8, 5.3, FLOOR_Z)), coll)
    bb = U.BoxBatch()
    crate(bb, (3.05, 4.5, FLOOR_Z + 0.25), 0.5)
    crate(bb, (3.1, 4.45, FLOOR_Z + 0.75), 0.45)
    # water trough across the street side
    t = V((-4.2, -1.0, 0))
    bb.box(t + V((0, 0, 0.3)), (0.6, 2.0, 0.05), ax=Z, ay=Y, az=X)
    bb.box(t + V((0.33, 0, 0.3)), (0.6, 2.0, 0.05), ax=Z, ay=Y, az=X)
    bb.box(t + V((-0.33, 0, 0.3)), (0.6, 2.0, 0.05), ax=Z, ay=Y, az=X)
    for s in (-1, 1):
        bb.box(t + V((0, s * 1.0, 0.3)), (0.6, 0.71, 0.05), ax=Z, ay=X, az=Y)
    bb.box(t + V((0, 0, 0.03)), (2.0, 0.71, 0.05), ax=Y, ay=X, az=Z)
    # bench on the saloon porch
    for yy in (2.6, 4.0):
        bb.box(V((3.75, yy, FLOOR_Z + 0.22)), (0.44, 0.06, 0.32), ax=Z, ay=Y, az=X)
    bb.box(V((3.75, 3.3, FLOOR_Z + 0.46)), (1.6, 0.36, 0.05), ax=Y, ay=X, az=Z)
    # corral fence west side (empty lot lets the low sun down the street)
    for i in range(12):
        yy = 7.0 + i * 2.2
        bb.box(V((-6.0, yy, 0.7)), (1.4, 0.12, 0.12), ax=Z, ay=X, az=Y)
        if i < 11:
            for zz in (0.55, 1.1):
                bb.box(V((-6.0, yy + 1.1, zz + random.uniform(-0.03, 0.03))), (2.25, 0.08, 0.1), ax=Y, ay=X, az=Z)
    bb.build("props_ext", M["wood_gray"], coll)
    w = U.mesh_obj("trough_water", [t + V((-0.3, -0.98, 0.5)), t + V((0.3, -0.98, 0.5)), t + V((0.3, 0.98, 0.5)),
                                    t + V((-0.3, 0.98, 0.5))], [(0, 1, 2, 3)], M["water"], coll=coll)
    # wagon wheel leaning on the general store
    wheel(V((4.25, -8.6, 0.62)), coll)


def wheel(c, coll, r=0.6):
    bb = U.BoxBatch()
    n = 16
    for i in range(n):
        a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
        p0 = c + V((0, math.cos(a0) * r, math.sin(a0) * r))
        p1 = c + V((0, math.cos(a1) * r, math.sin(a1) * r))
        ax = (p1 - p0).normalized()
        bb.box((p0 + p1) / 2, ((p1 - p0).length + 0.02, 0.07, 0.06), ax=ax, ay=X, az=ax.cross(X))
    for i in range(12):
        a = 2 * math.pi * i / 12
        d = V((0, math.cos(a), math.sin(a)))
        bb.box(c + d * r / 2, (r - 0.05, 0.035, 0.035), ax=d, ay=X, az=d.cross(X))
    ob = bb.build("wagon_wheel", M["wood_gray"], coll)
    ob.rotation_euler = (0, 0.18, 0)
    return ob


def town(coll):
    random.seed(5)
    # east side (same side as the saloon), fronts at x ~ 4.3, normal -X, u = +Y
    building("store_s", V((4.4, -15.0, 0)), Y, 8.4, 9, 4.2, 5.6, M["wood_gray"], coll,
             door=(3.6, 4.8, 0.4, 2.6), windows=[(1.0, 2.6, 1.0, 2.5), (5.8, 7.4, 1.0, 2.5)], porch=True)
    building("bank_n", V((4.6, 6.6, 0)), Y, 6.5, 8, 4.0, 5.2, M["wood_red"], coll,
             door=(2.8, 3.8, 0.4, 2.5), windows=[(0.8, 2.2, 1.0, 2.4), (4.4, 5.8, 1.0, 2.4)], porch=True)
    building("hotel_n", V((4.4, 13.8, 0)), Y, 9.0, 10, 6.2, 7.3, M["wood_front"], coll,
             door=(4.0, 5.0, 0.4, 2.5),
             windows=[(1.0, 2.3, 1.0, 2.4), (6.6, 7.9, 1.0, 2.4), (1.0, 2.3, 3.8, 5.2), (4.0, 5.2, 3.8, 5.2),
                      (6.6, 7.9, 3.8, 5.2)], porch=True)
    building("livery_n", V((5.0, 24.5, 0)), Y, 7.0, 9, 3.6, 4.6, M["wood_gray"], coll,
             door=(2.0, 5.0, 0.0, 3.0), windows=[], porch=False)
    building("east_far", V((5.0, 33.0, 0)), Y, 6.0, 7, 3.2, 4.0, M["wood_dark"], coll,
             door=(2.4, 3.4, 0.4, 2.4), windows=[(0.6, 1.8, 1.0, 2.2)], porch=False)
    # west side, fronts at x=-5.5 facing +X, u = -Y so that the wall faces +X
    building("assay_w", V((-5.6, -5.0, 0)), -Y, 9.0, 8, 4.0, 5.4, M["wood_front"], coll,
             door=(4.0, 5.0, 0.4, 2.5), windows=[(1.0, 2.6, 1.0, 2.5), (6.4, 8.0, 1.0, 2.5)], porch=True)
    building("smith_w", V((-5.8, 5.0, 0)), -Y, 8.5, 8, 3.8, 4.8, M["wood_gray"], coll,
             door=(3.0, 5.5, 0.0, 2.8), windows=[(0.8, 2.0, 1.1, 2.3)], porch=False)
    building("office_w", V((-5.6, -15.5, 0)), -Y, 8.0, 8, 4.0, 5.0, M["wood_red"], coll,
             door=(3.6, 4.6, 0.4, 2.5), windows=[(1.0, 2.5, 1.0, 2.4), (5.6, 7.0, 1.0, 2.4)], porch=True)
    # far silhouettes down the street (beyond the lot, west side further away)
    random.seed(9)
    for i, yy in enumerate((48, 56, 63)):
        building("far_e%d" % i, V((6.0 + i, yy, 0)), Y, 6.0, 7, 3.5 + i * 0.4, 4.4 + i * 0.3, M["far_bldg"], coll,
                 door=None, windows=[], porch=False)
    # water tower
    bt = U.BoxBatch()
    tc = V((14.0, 70.0, 0))
    for (dx, dy) in ((-1.2, -1.2), (1.2, -1.2), (-1.2, 1.2), (1.2, 1.2)):
        bt.box(tc + V((dx, dy, 3.5)), (7.0, 0.22, 0.22), ax=Z, ay=X, az=Y)
    bt.build("tower_legs", M["far_bldg"], coll)
    tank = U.lathe("tower_tank", [(1.9, 7.0), (1.9, 9.6), (1.2, 10.4), (0.05, 10.8)], segs=24, mat=M["far_bldg"],
                   coll=coll)
    tank.location = tc
    # distant mesas (a few large hazy blocks with sloped sides)
    random.seed(3)
    for i in range(9):
        ang = math.radians(-60 + i * 15 + random.uniform(-5, 5))
        dist = random.uniform(900, 1700)
        cx, cy = math.sin(ang) * dist, math.cos(ang) * dist
        w = random.uniform(150, 420)
        h = random.uniform(40, 140) * dist / 1200
        prof = [(w, 0), (w * 0.82, h * 0.55), (w * 0.62, h), (0.01, h)]
        m = U.lathe("mesa%d" % i, prof, segs=7, mat=M["mesa"], coll=coll, smooth_shade=False, sx=1.0, sy=0.5)
        m.location = (cx, cy, -5)
        m.rotation_euler = (0, 0, ang + random.uniform(-0.5, 0.5))


def ground(coll):
    n = 60
    size = 260.0
    verts, faces = [], []
    for j in range(n + 1):
        for i in range(n + 1):
            x = -size / 2 + size * i / n
            y = -size / 2 + 40 + size * j / n
            # gentle wheel ruts along the street (x=-2.2 and x=0.2)
            z = 0.0
            for rx in (-2.4, 0.1):
                z -= 0.0 * math.exp(-((x - rx) / 0.35) ** 2)
            verts.append((x, y, z))
    for j in range(n):
        for i in range(n):
            a = j * (n + 1) + i
            faces.append((a, a + 1, a + n + 2, a + n + 1))
    g = U.mesh_obj("ground", verts, faces, M["dirt"], coll=coll)
    far = U.mesh_obj("ground_far", [(-3000, -200, -0.05), (3000, -200, -0.05), (3000, 3000, -0.05),
                                    (-3000, 3000, -0.05)], [(0, 1, 2, 3)], M["mesa"], coll=coll)
    return g


# ---------------------------------------------------------------- interior furniture
def interior(coll):
    random.seed(21)
    fz = FLOOR_Z
    bb = U.BoxBatch()     # furniture (dark polished)
    bw = U.BoxBatch()     # rough wood
    # bar along north wall: front face y=3.4, x 7.0..12.6
    bx0, bx1 = 7.0, 12.6
    for i in range(int((bx1 - bx0) / 0.16)):
        bb.box(V((bx0 + 0.08 + i * 0.16, 3.42, fz + 0.55)), (1.1, 0.155, 0.04), ax=Z, ay=X, az=Y)
    bb.box(V(((bx0 + bx1) / 2, 3.75, fz + 1.13)), (bx1 - bx0 + 0.2, 0.75, 0.06), ax=X, ay=Y, az=Z)
    bb.box(V((bx0 - 0.02, 3.8, fz + 0.55)), (1.1, 0.8, 0.05), ax=Z, ay=Y, az=X)
    # foot rail (brass) added as cylinder below
    # back bar shelves
    for zz in (1.1, 1.55, 2.0):
        bb.box(V(((bx0 + bx1) / 2, 5.65, fz + zz)), (bx1 - bx0, 0.4, 0.04), ax=X, ay=Y, az=Z)
    bb.box(V(((bx0 + bx1) / 2, 5.75, fz + 0.5)), (bx1 - bx0, 0.35, 1.0), ax=X, ay=Y, az=Z)
    # tables + chairs
    tables = [V((8.6, 1.0)), V((10.6, -2.4)), V((12.0, 1.6)), V((6.6, -2.8))]
    chairs = []
    for ti, tcen in enumerate(tables):
        top = U.lathe("table%d" % ti, [(0.001, fz + 0.74), (0.5, fz + 0.74), (0.5, fz + 0.78), (0.001, fz + 0.78)],
                      segs=28, mat=M["wood_polish"], coll=coll)
        top.location = (tcen.x, tcen.y, 0)
        leg = U.lathe("tleg%d" % ti, [(0.05, fz), (0.04, fz + 0.4), (0.06, fz + 0.74)], segs=10, mat=M["wood_polish"],
                      coll=coll)
        leg.location = (tcen.x, tcen.y, 0)
        base = U.lathe("tbase%d" % ti, [(0.25, fz), (0.2, fz + 0.04), (0.04, fz + 0.06)], segs=16,
                       mat=M["wood_polish"], coll=coll)
        base.location = (tcen.x, tcen.y, 0)
        for k in range(3 if ti else 2):
            if ti == 0:
                ang = [-math.pi / 2, math.pi / 2][k]
            else:
                ang = k * 2 * math.pi / 3 + ti
            cpos = tcen + V((math.cos(ang), math.sin(ang))) * 0.72
            chairs.append((cpos, ang + math.pi))
    for ci, (cp, face) in enumerate(chairs):
        chair(bb, V((cp.x, cp.y, fz)), face)
    bb.build("furniture", M["wood_polish"], coll)
    rail = U.prim("cyl", "bar_footrail", loc=((bx0 + bx1) / 2, 3.25, fz + 0.15), rot=(0, math.pi / 2, 0),
                  radius=0.025, depth=bx1 - bx0, segs=10, mat=M["brass"], coll=coll)
    # bottles on back bar + on tables
    random.seed(4)
    for zz in (1.12, 1.57, 2.02):
        xx = bx0 + 0.2
        while xx < bx1 - 0.2:
            h = random.uniform(0.24, 0.32)
            b = U.lathe("bottle", [(0.035, 0), (0.037, h * 0.65), (0.012, h * 0.85), (0.012, h)], segs=10,
                        mat=random.choice([M["bottle_g"], M["bottle_b"]]), coll=coll)
            b.location = (xx, 5.6 + random.uniform(-0.05, 0.05), fz + zz + 0.02)
            xx += random.uniform(0.12, 0.3)
    b = U.lathe("bottle_t", [(0.04, 0), (0.042, 0.2), (0.013, 0.26), (0.013, 0.31)], segs=12, mat=M["bottle_b"],
                coll=coll)
    b.location = (8.75, 1.15, fz + 0.78)
    b2 = U.lathe("bottle_t2", [(0.04, 0), (0.042, 0.2), (0.013, 0.26), (0.013, 0.31)], segs=12, mat=M["bottle_g"],
                 coll=coll)
    b2.location = (12.1, 1.5, fz + 0.78)
    # cards on table 0
    for k in range(5):
        U.mesh_obj("card%d" % k, [(0, 0, 0), (0.06, 0, 0), (0.06, 0.09, 0), (0, 0.09, 0)], [(0, 1, 2, 3)],
                   M["ivory"], coll=coll).location = (8.35 + k * 0.03 + random.uniform(0, .02),
                                                      0.85 + random.uniform(-0.05, 0.05), fz + 0.782)
    # picture frame on the south wall
    bw.box(V((11.5, -5.86, fz + 2.1)), (1.2, 0.9, 0.05), ax=X, ay=Z, az=Y)
    U.mesh_obj("painting", [(11.0, -5.82, fz + 1.75), (12.0, -5.82, fz + 1.75), (12.0, -5.82, fz + 2.45),
                            (11.0, -5.82, fz + 2.45)], [(0, 1, 2, 3)], M["canvas"], coll=coll)
    # spittoon / stove
    stove = U.lathe("stove", [(0.25, fz), (0.3, fz + 0.2), (0.3, fz + 0.8), (0.2, fz + 0.95), (0.06, fz + 1.0),
                              (0.06, fz + 3.6)], segs=16, mat=M["iron"], coll=coll)
    stove.location = (14.5, -3.8, 0)
    bw.build("int_rough", M["wood_dark"], coll)
    return chairs


def chair(bb, p, face):
    f = V((math.cos(face), math.sin(face), 0))
    s = V((-f.y, f.x, 0))
    for (a, b) in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        bb.box(p + f * (0.18 * a) + s * (0.18 * b) + Z * 0.23, (0.46, 0.035, 0.035), ax=Z, ay=f, az=s)
    bb.box(p + Z * 0.47, (0.42, 0.42, 0.035), ax=f, ay=s, az=Z)
    for b in (1, -1):
        bb.box(p - f * 0.19 + s * (0.18 * b) + Z * 0.72, (0.5, 0.035, 0.035), ax=Z, ay=f, az=s)
    bb.box(p - f * 0.19 + Z * 0.92, (0.42, 0.08, 0.025), ax=s, ay=Z, az=f)
    bb.box(p - f * 0.19 + Z * 0.7, (0.42, 0.05, 0.02), ax=s, ay=Z, az=f)


def piano(coll, white_keys_out):
    """upright piano against the south wall; returns key objects keyed by midi."""
    P = PIANO
    bb = U.BoxBatch()
    x0, x1 = P["x"] - 0.78, P["x"] + 0.78
    yb = P["y_wall"] + 0.03
    fz = FLOOR_Z
    # case
    bb.box(V((P["x"], yb + 0.3, fz + 0.7)), (1.6, 0.6, 1.4), ax=X, ay=Y, az=Z)       # lower+upper body (behind)
    bb.box(V((P["x"], yb + 0.25, fz + 1.4)), (1.62, 0.5, 0.06), ax=X, ay=Y, az=Z)    # lid
    for s in (-1, 1):
        bb.box(V((P["x"] + s * 0.8, yb + 0.45, fz + 0.75)), (0.06, 0.9, 1.5), ax=X, ay=Y, az=Z)   # cheeks
    bb.box(V((P["x"], yb + 0.62, fz + 0.36)), (1.5, 0.05, 0.6), ax=X, ay=Y, az=Z)      # lower panel
    bb.box(V((P["x"], P["key_y"] - 0.02, P["key_z"] - 0.06)), (1.56, 0.32, 0.06), ax=X, ay=Y, az=Z)  # key bed
    bb.box(V((P["x"], P["key_y"] - 0.17, P["key_z"] + 0.12)), (1.5, 0.04, 0.25), ax=X, ay=Y, az=Z)  # fallboard back
    bb.box(V((P["x"], yb + 0.5, fz + 1.05)), (1.4, 0.04, 0.55), ax=X, ay=Y, az=Z)        # music desk
    # bench
    bb.box(V((P["x"], -4.62, fz + 0.5)), (0.95, 0.38, 0.05), ax=X, ay=Y, az=Z)
    for (a, b) in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        bb.box(V((P["x"] + a * 0.42, -4.62 + b * 0.15, fz + 0.24)), (0.05, 0.05, 0.48), ax=X, ay=Y, az=Z)
    bb.build("piano_case", M["wood_polish"], coll)
    # sheet music
    U.mesh_obj("sheet", [(P["x"] - 0.25, yb + 0.47, fz + 1.0), (P["x"] + 0.25, yb + 0.47, fz + 1.0),
                         (P["x"] + 0.25, yb + 0.43, fz + 1.3), (P["x"] - 0.25, yb + 0.43, fz + 1.3)],
               [(0, 1, 2, 3)], M["paint_sign"], coll=coll)
    # candle holders / lamp on top
    keys = {}
    # keys: midi 36..96 (5 octaves), white key width 0.0235
    wk = 0.0233
    whites = [m for m in range(36, 97) if (m % 12) in (0, 2, 4, 5, 7, 9, 11)]
    total = len(whites) * wk
    # the pianist faces -Y, so his left (low notes) is +X: pitch increases towards -X
    white_pos = {}
    for i, m in enumerate(whites):
        white_pos[m] = P["x"] + total / 2 - (i + 0.5) * wk
    for m in range(36, 97):
        if m in white_pos:
            xx = white_pos[m]
            k = U.prim("cube", "key_%d" % m, loc=(0, 0, 0), mat=M["ivory"], coll=coll, smooth_shade=False)
            for v in k.data.vertices:
                v.co.x *= wk - 0.0015
                v.co.y *= 0.15
                v.co.z *= 0.02
                v.co.y += 0.075     # pivot at back of key (towards the wall)
            k.location = (xx, P["key_y"] - 0.075, P["key_z"])
        else:
            xx = (white_pos[m - 1] + white_pos[m + 1]) / 2
            k = U.prim("cube", "key_%d" % m, loc=(0, 0, 0), mat=M["ebony"], coll=coll, smooth_shade=False)
            for v in k.data.vertices:
                v.co.x *= 0.012
                v.co.y *= 0.095
                v.co.z *= 0.02
                v.co.y += 0.0475
                v.co.z += 0.012
            k.location = (xx, P["key_y"] - 0.075, P["key_z"])
        keys[m] = k
    white_keys_out.update(white_pos)
    return keys


def lamps(coll):
    """hanging oil lamps + their lights."""
    out = []
    for (x, y, z) in ((7.0, 0.8, FLOOR_Z + 2.6), (10.8, -1.4, FLOOR_Z + 2.6), (10.0, 3.8, FLOOR_Z + 2.4)):
        glass = U.lathe("lamp_glass", [(0.02, -0.12), (0.07, -0.05), (0.06, 0.06), (0.03, 0.12)], segs=12,
                        mat=M["lamp_glow"], coll=coll)
        glass.location = (x, y, z)
        shade = U.lathe("lamp_shade", [(0.28, 0.12), (0.06, 0.24), (0.01, 0.26)], segs=16, mat=M["brass"], coll=coll,
                        close_bottom=False)
        shade.location = (x, y, z)
        chain = U.prim("cyl", "lamp_rod", loc=(x, y, (z + 0.26 + FLOOR_Z + 3.55) / 2), radius=0.008,
                       depth=FLOOR_Z + 3.55 - z - 0.26, segs=6, mat=M["iron"], coll=coll)
        ld = bpy.data.lights.new("lamp", "POINT")
        ld.energy = 140.0
        ld.color = (1.0, 0.58, 0.26)
        ld.shadow_soft_size = 0.06
        lo = bpy.data.objects.new("lamp_light", ld)
        lo.location = (x, y, z - 0.02)
        U.link(lo, coll)
        out.append(lo)
    # candle on the piano + wall sconce near it
    P = PIANO
    cz = FLOOR_Z + 1.43
    holder = U.lathe("candle_holder", [(0.05, 0.0), (0.02, 0.02), (0.015, 0.12), (0.04, 0.14)], segs=12,
                     mat=M["brass"], coll=coll)
    holder.location = (P["x"] + 0.55, P["y_wall"] + 0.25, cz)
    candle = U.prim("cyl", "candle", radius=0.012, depth=0.12, segs=10, mat=M["ivory"], coll=coll,
                    loc=(P["x"] + 0.55, P["y_wall"] + 0.25, cz + 0.2))
    flame = U.prim("sphere", "flame", radius=0.01, segs=8, rings=6, mat=M["lamp_glow"], coll=coll,
                   loc=(P["x"] + 0.55, P["y_wall"] + 0.25, cz + 0.275), scale=(1, 1, 1.8))
    for (loc, en, sz) in (((P["x"] + 0.55, P["y_wall"] + 0.28, cz + 0.29), 18.0, 0.02),
                          ((P["x"] - 1.2, P["y_wall"] + 0.25, FLOOR_Z + 2.15), 70.0, 0.05)):
        ld = bpy.data.lights.new("piano_light", "POINT")
        ld.energy = en
        ld.color = (1.0, 0.56, 0.24)
        ld.shadow_soft_size = sz
        lo = bpy.data.objects.new("piano_light", ld)
        lo.location = loc
        U.link(lo, coll)
    sconce = U.lathe("sconce", [(0.02, -0.1), (0.07, -0.02), (0.06, 0.08), (0.03, 0.14)], segs=12,
                     mat=M["lamp_glow"], coll=coll)
    sconce.location = (P["x"] - 1.2, P["y_wall"] + 0.25, FLOOR_Z + 2.12)
    # soft warm bounce from the ceiling (stands in for interior GI)
    ad = bpy.data.lights.new("ceiling_bounce", "AREA")
    ad.shape = "RECTANGLE"
    ad.size, ad.size_y = 9.0, 9.0
    ad.energy = 260.0
    ad.color = (1.0, 0.66, 0.42)
    ao = bpy.data.objects.new("ceiling_bounce", ad)
    ao.location = (10.0, 0.0, FLOOR_Z + 3.4)
    U.link(ao, coll)
    return out
