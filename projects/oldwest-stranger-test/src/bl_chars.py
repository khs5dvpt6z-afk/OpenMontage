"""Procedural low-poly characters (people + horse) with analytic IK, keyed per frame.
Every limb segment is an unparented object whose world matrix is computed in Python each frame;
static accessories are parented to the moving parts."""
import math

import bpy
from mathutils import Matrix, Vector

import bl_util as U
from bl_util import V

Z = V((0, 0, 1))


# =====================================================================================  loft helper
def loft(name, sections, mat=None, segs=16, coll=None, cap0=True, cap1=True, subsurf=1):
    """sections: list of (center Vector, x_axis Vector (cross 'height' dir), y_axis Vector, a, b)
    produces an elliptic tube (a along x_axis, b along y_axis)."""
    verts, faces = [], []
    for (c, xa, ya, a, b) in sections:
        for i in range(segs):
            t = 2 * math.pi * i / segs
            verts.append(c + xa * (a * math.cos(t)) + ya * (b * math.sin(t)))
    ns = len(sections)
    for j in range(ns - 1):
        for i in range(segs):
            i2 = (i + 1) % segs
            faces.append([j * segs + i, j * segs + i2, (j + 1) * segs + i2, (j + 1) * segs + i])
    if cap0:
        verts.append(sections[0][0])
        ci = len(verts) - 1
        for i in range(segs):
            faces.append([ci, (i + 1) % segs, i])
    if cap1:
        verts.append(sections[-1][0])
        ci = len(verts) - 1
        base = (ns - 1) * segs
        for i in range(segs):
            faces.append([ci, base + i, base + (i + 1) % segs])
    ob = U.mesh_obj(name, verts, faces, mat, smooth_shade=True, coll=coll)
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.shade_smooth()
    if subsurf:
        m = ob.modifiers.new("sub", "SUBSURF")
        m.levels = subsurf
        m.render_levels = subsurf
    return ob


def path_loft(name, pts, radii, up=V((0, 0, 1)), mat=None, segs=16, coll=None, subsurf=1, cap0=True, cap1=True):
    """loft along polyline pts with radii [(a_up, b_side)]. side axis = tangent x up."""
    secs = []
    n = len(pts)
    for i, p in enumerate(pts):
        if i == 0:
            t = pts[1] - pts[0]
        elif i == n - 1:
            t = pts[-1] - pts[-2]
        else:
            t = pts[i + 1] - pts[i - 1]
        t.normalize()
        side = t.cross(up)
        if side.length < 1e-5:
            side = V((0, 1, 0))
        side.normalize()
        upv = side.cross(t).normalized()
        secs.append((p, upv, side, radii[i][0], radii[i][1]))
    return loft(name, secs, mat, segs, coll, cap0, cap1, subsurf)


# =====================================================================================  materials
def char_materials():
    C = {}
    C["skin"] = U.noisy_mat("skin", (0.40, 0.25, 0.17), (0.33, 0.20, 0.14), scale=40, rough=0.55, bump=0.08)
    C["hairdark"] = U.noisy_mat("hairdark", (0.05, 0.035, 0.025), (0.12, 0.08, 0.05), scale=200, rough=0.8, bump=0.4)
    C["socket"] = U.principled("socket", (0.08, 0.04, 0.03), rough=0.6)
    C["skin_pale"] = U.noisy_mat("skin_pale", (0.52, 0.35, 0.26), (0.46, 0.30, 0.22), scale=40, rough=0.5, bump=0.05)
    C["stubble"] = U.noisy_mat("stubble", (0.18, 0.12, 0.09), (0.30, 0.20, 0.14), scale=300, rough=0.8, bump=0.1)
    C["coat"] = U.noisy_mat("coat", (0.40, 0.31, 0.21), (0.28, 0.21, 0.14), scale=9, rough=0.95, bump=0.25,
                            sheen=0.4, detail=8)
    C["hat"] = U.noisy_mat("hat", (0.14, 0.10, 0.07), (0.20, 0.15, 0.10), scale=12, rough=0.9, bump=0.1, sheen=0.3)
    C["band"] = U.principled("hatband", (0.05, 0.035, 0.025), rough=0.6)
    C["trousers"] = U.noisy_mat("trousers", (0.17, 0.15, 0.13), (0.24, 0.21, 0.17), scale=15, rough=0.95, bump=0.2)
    C["boots"] = U.noisy_mat("boots", (0.09, 0.055, 0.035), (0.16, 0.10, 0.06), scale=20, rough=0.45, bump=0.15)
    C["glove"] = U.noisy_mat("glove", (0.33, 0.20, 0.10), (0.25, 0.15, 0.08), scale=30, rough=0.7, bump=0.15)
    C["shirt"] = U.noisy_mat("shirt", (0.62, 0.57, 0.48), (0.52, 0.47, 0.39), scale=20, rough=0.9, bump=0.1, sheen=0.3)
    C["white"] = U.noisy_mat("white_shirt", (0.72, 0.68, 0.60), (0.62, 0.58, 0.50), scale=20, rough=0.85, bump=0.1)
    C["vest"] = U.noisy_mat("vest", (0.07, 0.065, 0.07), (0.11, 0.10, 0.10), scale=40, rough=0.6, bump=0.05)
    C["jacket"] = U.noisy_mat("jacket", (0.22, 0.14, 0.08), (0.16, 0.10, 0.06), scale=12, rough=0.9, bump=0.2)
    C["blue"] = U.noisy_mat("blueshirt", (0.20, 0.24, 0.28), (0.15, 0.18, 0.21), scale=20, rough=0.9, bump=0.1)
    C["darkcoat"] = U.noisy_mat("darkcoat", (0.07, 0.07, 0.075), (0.11, 0.10, 0.10), scale=12, rough=0.9, bump=0.2)
    C["bandana"] = U.noisy_mat("bandana", (0.36, 0.08, 0.05), (0.26, 0.05, 0.03), scale=25, rough=0.9, bump=0.1)
    C["belt"] = U.principled("gunbelt", (0.13, 0.07, 0.04), rough=0.5)
    C["brass"] = U.principled("cartridge", (0.6, 0.42, 0.18), rough=0.3, metal=1.0)
    C["iron"] = U.principled("gunmetal", (0.04, 0.04, 0.045), rough=0.4, metal=0.9)
    C["grip"] = U.principled("grip", (0.25, 0.17, 0.10), rough=0.4)
    C["eye"] = U.principled("eye", (0.01, 0.01, 0.01), rough=0.1, spec=0.8)
    # horse
    C["horse"] = U.noisy_mat("horse_coat", (0.26, 0.11, 0.05), (0.17, 0.07, 0.03), scale=3, rough=0.48, bump=0.05,
                             sheen=0.3)
    C["horse_dark"] = U.noisy_mat("horse_points", (0.035, 0.025, 0.02), (0.06, 0.04, 0.03), scale=8, rough=0.5,
                                  bump=0.05)
    C["hair"] = U.noisy_mat("horse_hair", (0.02, 0.016, 0.014), (0.06, 0.045, 0.035), scale=2, rough=0.45, bump=0.6,
                            stretch=(1, 1, 30), coord="Object")
    C["hoof"] = U.principled("hoof", (0.06, 0.055, 0.05), rough=0.5)
    C["leather"] = U.noisy_mat("tack", (0.20, 0.09, 0.04), (0.13, 0.06, 0.03), scale=25, rough=0.4, bump=0.1)
    C["blanket"] = U.noisy_mat("blanket", (0.40, 0.09, 0.05), (0.18, 0.12, 0.08), scale=6, rough=1.0, bump=0.2,
                               stretch=(1, 8, 1))
    C["bedroll"] = U.noisy_mat("bedroll", (0.30, 0.26, 0.18), (0.22, 0.19, 0.14), scale=20, rough=1.0, bump=0.2)
    C["steel"] = U.principled("steel", (0.35, 0.33, 0.30), rough=0.3, metal=1.0)
    return C


# =====================================================================================  person
class Person:
    L_UP, L_FORE, L_THIGH, L_SHIN = 0.29, 0.265, 0.46, 0.44

    def __init__(self, name, C, coll, top="coat", sleeves="coat", legs="trousers", hat="cowboy", hands="glove",
                 skirt=True, skin="skin", beard=True, gunbelt=False, bandana=False, hatmat="hat", scale=1.0,
                 curl=(0.55, 0.75)):
        self.name, self.C, self.coll = name, C, coll
        self.curl = curl
        self.parts = {}
        self.scale = scale
        mk = lambda key, ob: self.parts.__setitem__(key, ob)
        # pelvis
        p = U.prim("sphere", name + "_pelvis", radius=1.0, segs=16, rings=10, mat=C[legs], coll=coll)
        for v in p.data.vertices:
            v.co = V((v.co.x * 0.13, v.co.y * 0.175, v.co.z * 0.12))
        mk("pelvis", p)
        # torso (origin at waist pivot)
        prof = [(0.001, -0.06), (0.15, -0.05), (0.155, 0.08), (0.175, 0.25), (0.19, 0.38), (0.185, 0.45),
                (0.12, 0.52), (0.06, 0.55), (0.001, 0.56)]
        t = U.lathe(name + "_torso", prof, segs=20, mat=C[top], coll=coll, sx=0.62)
        mk("torso", t)
        if top == "coat":
            # collar + lapels
            col = U.lathe(name + "_collar", [(0.085, 0.50), (0.105, 0.56), (0.11, 0.60)], segs=16, mat=C["coat"],
                          coll=coll, close_top=False, close_bottom=False, sx=0.85)
            U.parent(col, t)
            sm = col.modifiers.new("solid", "SOLIDIFY"); sm.thickness = 0.01
            # open front showing shirt + vest strip
            st = U.prim("cube", name + "_shirtfront", mat=C["vest"], coll=coll, smooth_shade=False)
            for v in st.data.vertices:
                v.co = V((v.co.x * 0.02 + 0.112, v.co.y * 0.075, v.co.z * 0.42 + 0.24))
            U.parent(st, t)
        if bandana:
            bd = U.lathe(name + "_bandana", [(0.072, 0.47), (0.08, 0.53), (0.065, 0.57)], segs=16, mat=C["bandana"],
                         coll=coll, close_top=False, close_bottom=False)
            U.parent(bd, t)
            tri = U.mesh_obj(name + "_bandana_tip", [(0.06, -0.06, 0.53), (0.06, 0.06, 0.53), (0.115, 0.0, 0.40)],
                             [(0, 1, 2)], C["bandana"], coll=coll)
            U.parent(tri, t)
        # head (origin at neck pivot)
        hp = U.empty(name + "_neck", coll=coll)
        mk("neck", hp)
        neck = U.capsule(name + "_neckm", 0.12, 0.052, 0.05, mat=C[skin], coll=coll)
        U.parent(neck, hp)
        head = U.prim("sphere", name + "_head", radius=1.0, segs=20, rings=14, mat=C[skin], coll=coll)
        for v in head.data.vertices:
            x, y, z = v.co
            sx = 0.098 + (0.01 if x > 0 and z < 0 else 0)
            v.co = V((x * sx, y * 0.082, z * 0.118 + 0.19))
        U.parent(head, hp)
        jaw = U.prim("sphere", name + "_jaw", radius=1.0, segs=16, rings=10, mat=C["stubble" if beard else skin],
                     coll=coll)
        for v in jaw.data.vertices:
            v.co = V((v.co.x * 0.075 + 0.035, v.co.y * 0.072, v.co.z * 0.055 + 0.125))
        U.parent(jaw, hp)
        nose = U.mesh_obj(name + "_nose", [(0.092, -0.016, 0.19), (0.092, 0.016, 0.19), (0.115, 0, 0.165),
                                           (0.09, -0.018, 0.16), (0.09, 0.018, 0.16), (0.085, 0, 0.215)],
                          [(0, 2, 1), (0, 3, 2), (1, 2, 4), (3, 4, 2), (0, 1, 5)], C[skin], coll=coll)
        U.parent(nose, hp)
        if beard:
            mus = U.prim("sphere", name + "_mustache", radius=1.0, segs=12, rings=8, mat=C["hairdark"], coll=coll)
            for v in mus.data.vertices:
                x, y, z = v.co
                v.co = V((x * 0.014 + 0.098, y * 0.042, z * 0.012 + 0.152 - 0.012 * (y * y)))
            U.parent(mus, hp)
            bd = U.prim("sphere", name + "_beard", radius=1.0, segs=16, rings=10, mat=C["hairdark"], coll=coll)
            for v in bd.data.vertices:
                x, y, z = v.co
                v.co = V((x * 0.072 + 0.04, y * 0.074, z * 0.05 + 0.115))
            U.parent(bd, hp)
        for s_ in (-1, 1):
            eb = U.prim("cube", name + "_eyebrow", mat=C["hairdark"], coll=coll, smooth_shade=False)
            for v in eb.data.vertices:
                v.co = V((v.co.x * 0.01 + 0.093, v.co.y * 0.03 + s_ * 0.034, v.co.z * 0.008 + 0.222))
            U.parent(eb, hp)
            sock = U.prim("sphere", name + "_socket", radius=1.0, segs=10, rings=6, mat=C["socket"], coll=coll)
            for v in sock.data.vertices:
                v.co = V((v.co.x * 0.012 + 0.083, v.co.y * 0.02 + s_ * 0.033, v.co.z * 0.012 + 0.205))
            U.parent(sock, hp)
        brow = U.prim("sphere", name + "_brow", radius=1.0, segs=12, rings=8, mat=C[skin], coll=coll)
        for v in brow.data.vertices:
            v.co = V((v.co.x * 0.02 + 0.085, v.co.y * 0.07, v.co.z * 0.018 + 0.225))
        U.parent(brow, hp)
        for s in (-1, 1):
            ear = U.prim("sphere", name + "_ear", radius=1.0, segs=10, rings=6, mat=C[skin], coll=coll)
            for v in ear.data.vertices:
                v.co = V((v.co.x * 0.025 - 0.005, v.co.y * 0.012 + s * 0.083, v.co.z * 0.035 + 0.19))
            U.parent(ear, hp)
            eye = U.prim("sphere", name + "_eye", radius=0.011, segs=8, rings=6, mat=C["eye"], coll=coll,
                         loc=(0.085, s * 0.033, 0.205))
            U.parent(eye, hp)
        if hat == "cowboy":
            crown = U.lathe(name + "_crown", [(0.103, 0.0), (0.104, 0.07), (0.095, 0.115), (0.07, 0.135),
                                              (0.001, 0.125)], segs=24, mat=C[hatmat], coll=coll, sx=1.13)
            for v in crown.data.vertices:          # centre crease + front pinch
                if v.co.z > 0.1:
                    v.co.z -= 0.025 * math.exp(-(v.co.y / 0.04) ** 2)
                if v.co.x > 0.05 and v.co.z > 0.06:
                    v.co.y *= 0.85
            band = U.lathe(name + "_hband", [(0.1045, 0.005), (0.1048, 0.03)], segs=24, mat=C["band"], coll=coll,
                           sx=1.13, close_top=False, close_bottom=False)
            brim_v, brim_f = [], []
            nseg = 32
            rings = [0.095, 0.15, 0.205]
            for i in range(nseg):
                a = 2 * math.pi * i / nseg
                for r in rings:
                    x, y = math.cos(a) * r * 1.12, math.sin(a) * r
                    zc = 0.04 * ((abs(y) / 0.2) ** 2) * (r - 0.095) / 0.11 - 0.012 * (x / 0.23) * ((r - 0.095) / 0.11)
                    brim_v.append((x, y, zc))
            for i in range(nseg):
                i2 = (i + 1) % nseg
                for j in range(2):
                    brim_f.append([i * 3 + j, i * 3 + j + 1, i2 * 3 + j + 1, i2 * 3 + j])
            brim = U.mesh_obj(name + "_brim", brim_v, brim_f, C[hatmat], smooth_shade=True, coll=coll)
            sm = brim.modifiers.new("solid", "SOLIDIFY"); sm.thickness = 0.008
            hat_e = U.empty(name + "_hat", coll=coll)
            for o in (crown, band, brim):
                U.parent(o, hat_e, keep=False)
            hat_e.location = (0.004, 0, 0.268)
            hat_e.rotation_euler = (0, 0.1, 0)
            U.parent(hat_e, hp, keep=False)
        elif hat == "bowler":
            crown = U.lathe(name + "_crown", [(0.1, 0.0), (0.104, 0.05), (0.095, 0.1), (0.06, 0.13), (0.001, 0.135)],
                            segs=24, mat=C[hatmat], coll=coll, sx=1.12)
            brim = U.lathe(name + "_brim", [(0.1, 0.0), (0.14, 0.01), (0.15, 0.02)], segs=24, mat=C[hatmat],
                           coll=coll, sx=1.12, close_top=False, close_bottom=False)
            sm = brim.modifiers.new("solid", "SOLIDIFY"); sm.thickness = 0.006
            hat_e = U.empty(name + "_hat", coll=coll)
            for o in (crown, brim):
                U.parent(o, hat_e, keep=False)
            hat_e.location = (0.0, 0, 0.268)
            hat_e.rotation_euler = (0, 0.05, 0)
            U.parent(hat_e, hp, keep=False)
        # arms
        for s, side in ((1, "L"), (-1, "R")):
            ua = U.capsule(name + "_upper" + side, self.L_UP, 0.056, 0.047, mat=C[sleeves], coll=coll)
            fa = U.capsule(name + "_fore" + side, self.L_FORE, 0.047, 0.038, mat=C[sleeves], coll=coll)
            if sleeves == "coat":
                cuff = U.lathe(name + "_cuff" + side, [(0.046, self.L_FORE - 0.05), (0.052, self.L_FORE - 0.0)],
                               segs=12, mat=C["coat"], coll=coll, close_top=False, close_bottom=False)
                U.parent(cuff, fa, keep=False)
            mk("upper" + side, ua)
            mk("fore" + side, fa)
            mk("hand" + side, self._hand(name + "_hand" + side, C[hands] if hands in C else C[skin], s))
            # legs
            th = U.capsule(name + "_thigh" + side, self.L_THIGH, 0.078, 0.058, mat=C[legs], coll=coll)
            sh = U.capsule(name + "_shin" + side, self.L_SHIN, 0.055, 0.042, mat=C[legs], coll=coll)
            mk("thigh" + side, th)
            mk("shin" + side, sh)
            mk("boot" + side, self._boot(name + "_boot" + side, C["boots"]))
        if skirt:
            for s_, sd in ((1, "L"), (-1, "R")):
                a0, a1 = (math.radians(42), math.radians(181)) if s_ > 0 else (math.radians(179), math.radians(318))
                mk("skirt" + sd, self._skirt_half(name + "_skirt" + sd, C[top], a0, a1, s_))
        if gunbelt:
            gb = U.lathe(name + "_gunbelt", [(0.165, -0.065), (0.168, -0.02)], segs=24, mat=C["belt"], coll=coll,
                         close_top=False, close_bottom=False, sx=0.82)
            U.parent(gb, p, keep=False)
            gb.rotation_euler = (0, 0.12, 0)
            hol = U.prim("cube", name + "_holster", mat=C["belt"], coll=coll, smooth_shade=False)
            for v in hol.data.vertices:
                v.co = V((v.co.x * 0.07, v.co.y * 0.035, v.co.z * 0.2))
            hol.location = (0.01, -0.175, -0.17)
            hol.rotation_euler = (0.08, 0.12, 0)
            U.parent(hol, p, keep=False)
            grip = U.prim("cube", name + "_grip", mat=C["grip"], coll=coll, smooth_shade=False)
            for v in grip.data.vertices:
                v.co = V((v.co.x * 0.03 - 0.03, v.co.y * 0.025, v.co.z * 0.09))
            grip.location = (0.0, -0.18, -0.02)
            grip.rotation_euler = (0.0, 0.5, 0)
            U.parent(grip, p, keep=False)
            for k in range(9):
                a = math.radians(140 + k * 9)
                cart = U.prim("cyl", name + "_cart", radius=0.006, depth=0.04, segs=6, mat=C["brass"], coll=coll,
                              loc=(math.cos(a) * 0.14, math.sin(a) * 0.17, -0.04))
                U.parent(cart, p, keep=False)
        self.has_skirt = skirt

    def _skirt_half(self, name, mat, a0, a1, s):
        """one half of a long duster skirt with soft vertical folds; origin at the waist."""
        na, nz = 16, 9
        verts, faces = [], []
        for j in range(nz):
            v = j / (nz - 1)
            z = 0.10 - 0.70 * v
            r = 0.200 + 0.085 * (v ** 1.15)
            for i in range(na + 1):
                a = a0 + (a1 - a0) * i / na
                fold = 1.0 + 0.045 * math.sin(a * 9.0 + s) * v + 0.02 * math.sin(a * 23.0) * v
                verts.append((math.cos(a) * r * fold * 0.86, math.sin(a) * r * fold, z - 0.015 * math.sin(a * 5) * v))
        for j in range(nz - 1):
            for i in range(na):
                q = [j * (na + 1) + i, j * (na + 1) + i + 1, (j + 1) * (na + 1) + i + 1, (j + 1) * (na + 1) + i]
                faces.append(q)
        ob = U.mesh_obj(name, verts, faces, mat, smooth_shade=True, coll=self.coll)
        sm = ob.modifiers.new("solid", "SOLIDIFY"); sm.thickness = 0.012
        sub = ob.modifiers.new("sub", "SUBSURF"); sub.levels = 1; sub.render_levels = 1
        return ob

    def _hand(self, name, mat, s):
        """hand along +Z (wrist at origin), palm normal +X; four curled fingers + thumb."""
        coll = self.coll
        c1, c2 = self.curl
        palm = U.prim("cube", name, mat=mat, coll=coll, smooth_shade=True)
        for v in palm.data.vertices:
            x, y, z = v.co
            v.co = V((x * 0.03, y * 0.082, z * 0.088 + 0.048))
        bv = palm.modifiers.new("bev", "BEVEL"); bv.width = 0.011; bv.segments = 3
        ty = -s      # thumb side (+Y for the right hand)
        for i, (yy, ln) in enumerate(((0.029, 1.0), (0.010, 1.08), (-0.009, 1.02), (-0.027, 0.85))):
            y = yy * ty
            base = V((0.002, y, 0.088))
            d1 = V((math.sin(c1), 0, math.cos(c1)))
            d2 = V((math.sin(c1 + c2), 0, math.cos(c1 + c2)))
            l1, l2 = 0.044 * ln, 0.040 * ln
            for (b, d, l, r) in ((base, d1, l1, 0.0105), (base + d1 * l1, d2, l2, 0.0095)):
                f = U.capsule(name + "_f%d" % i, l, r, r * 0.92, mat=mat, coll=coll, segs=8)
                f.matrix_world = U.frame_matrix(b, d, V((0, 1, 0)).cross(d))
                U.parent(f, palm, keep=True)
        tb = V((0.012, ty * 0.036, 0.022))
        td1 = V((0.35, ty * 0.55, 0.75)).normalized()
        td2 = V((0.65, ty * 0.25, 0.7)).normalized()
        for (b, d, l, r) in ((tb, td1, 0.045, 0.012), (tb + td1 * 0.045, td2, 0.035, 0.0105)):
            f = U.capsule(name + "_t", l, r, r * 0.9, mat=mat, coll=coll, segs=8)
            f.matrix_world = U.frame_matrix(b, d, V((1, 0, 0)))
            U.parent(f, palm, keep=True)
        return palm

    def _boot(self, name, mat):
        coll = self.coll
        shaft = U.lathe(name, [(0.052, -0.04), (0.056, 0.10), (0.058, 0.2)], segs=14, mat=mat, coll=coll,
                        close_top=False)
        foot = U.prim("cube", name + "_foot", mat=mat, coll=coll, smooth_shade=False)
        for v in foot.data.vertices:
            x, y, z = v.co
            xx = 0.065 + x * 0.25        # -0.06..0.19
            w = 0.043 if xx < 0.12 else 0.043 - (xx - 0.12) * 0.25
            zt = -0.015 if xx < 0.05 else -0.015 - (xx - 0.05) * 0.18
            v.co = V((xx, y * 2 * w, -0.08 + (z + 0.5) * (zt + 0.08) + (0.012 if (z < 0 and xx < -0.0) else 0)))
        sub = foot.modifiers.new("bev", "BEVEL"); sub.width = 0.012; sub.segments = 2
        U.parent(foot, shaft, keep=False)
        heel = U.prim("cube", name + "_heel", mat=mat, coll=coll, smooth_shade=False)
        for v in heel.data.vertices:
            v.co = V((v.co.x * 0.055 - 0.03, v.co.y * 0.07, v.co.z * 0.03 - 0.065))
        U.parent(heel, shaft, keep=False)
        # spur
        sp = U.prim("cyl", name + "_spur", radius=0.017, depth=0.004, segs=10, mat=self.C["steel"], coll=coll,
                    loc=(-0.085, 0, -0.055), rot=(math.pi / 2, 0, 0))
        U.parent(sp, shaft, keep=False)
        return shaft

    # ----------------------------------------------------------------- per-frame posing
    def key(self, frame, pose):
        P = self.parts
        root = pose["root"]
        yaw = pose["yaw"]
        fwd = V((math.cos(yaw), math.sin(yaw), 0))
        side = V((-math.sin(yaw), math.cos(yaw), 0))       # +Y local = left
        M_root = U.trs(root, yaw)
        pt = pose.get("pelvis_tilt", (0.0, 0.0))
        M_pel = M_root @ Matrix.Translation(V((0, 0, pose.get("pelvis_z", 0.95)))) @ \
            Matrix.Rotation(pt[0], 4, "Y") @ Matrix.Rotation(pt[1], 4, "X")
        U.key_matrix(P["pelvis"], M_pel, frame)
        tw, tp, tr = pose.get("torso", (0.0, 0.0, 0.0))
        M_waist = M_pel @ Matrix.Translation(V((0, 0, 0.06))) @ U.rot_z(tw) @ Matrix.Rotation(tp, 4, "Y") @ \
            Matrix.Rotation(tr, 4, "X")
        U.key_matrix(P["torso"], M_waist, frame)
        hy, hpch, hr = pose.get("head", (0.0, 0.0, 0.0))
        M_neck = M_waist @ Matrix.Translation(V((0.0, 0, 0.5))) @ U.rot_z(hy) @ Matrix.Rotation(hpch, 4, "Y") @ \
            Matrix.Rotation(hr, 4, "X")
        U.key_matrix(P["neck"], M_neck, frame)
        skirt_M = M_pel @ Matrix.Translation(V((0, 0, 0.08)))
        fwd_w = (M_waist.to_3x3() @ V((1, 0, 0))).normalized()
        side_w = (M_waist.to_3x3() @ V((0, 1, 0))).normalized()
        up_w = (M_waist.to_3x3() @ V((0, 0, 1))).normalized()
        for s, sd in ((1, "L"), (-1, "R")):
            # arm
            sh = M_waist @ V((-0.01, s * 0.185, 0.43))
            hand = pose["hand" + sd]
            pole = pose.get("epole" + sd, sh - fwd_w * 0.35 + side_w * (s * 0.25) - up_w * 0.4)
            elbow, wrist = U.ik2(sh, hand, self.L_UP, self.L_FORE, pole)
            U.key_matrix(P["upper" + sd], U.frame_matrix(sh, elbow - sh, fwd_w), frame)
            U.key_matrix(P["fore" + sd], U.frame_matrix(elbow, wrist - elbow, fwd_w), frame)
            hdir = pose.get("hdir" + sd, wrist - elbow)
            palm = pose.get("palm" + sd, -side_w * s)
            U.key_matrix(P["hand" + sd], U.frame_matrix(wrist, hdir, palm), frame)
            # leg
            hip = M_pel @ V((0.0, s * 0.092, -0.04))
            ank = pose["foot" + sd]
            fy = pose.get("fyaw" + sd, yaw)
            ff = V((math.cos(fy), math.sin(fy), 0))
            kpole = pose.get("kpole" + sd, hip + ff * 1.0 - Z * 0.2)
            knee, ankle = U.ik2(hip, ank, self.L_THIGH, self.L_SHIN, kpole)
            U.key_matrix(P["thigh" + sd], U.frame_matrix(hip, knee - hip, ff), frame)
            if self.has_skirt:
                # coat half follows its thigh (pitch) and spreads with it (roll)
                loc = M_pel.inverted().to_3x3() @ (knee - hip)
                pitch = math.atan2(loc.x, -loc.z)
                lat = math.atan2(loc.y, -loc.z)
                sp, sr = pose.get("skirt", (0.0, 0.0))
                k = pose.get("skirt_follow", 0.6)
                Ms = skirt_M @ Matrix.Rotation(sr + 0.75 * lat, 4, "X") @ Matrix.Rotation(-k * pitch + sp, 4, "Y")
                U.key_matrix(P["skirt" + sd], Ms, frame)
            U.key_matrix(P["shin" + sd], U.frame_matrix(knee, ankle - knee, ff), frame)
            fp = pose.get("fpitch" + sd, 0.0)
            U.key_matrix(P["boot" + sd], Matrix.Translation(ankle) @ U.rot_z(fy) @ Matrix.Rotation(fp, 4, "Y"), frame)
        return M_waist, M_neck


# =====================================================================================  horse
class Horse:
    FRONT_X, HIND_X, LEG_Y = 0.50, -0.70, 0.165
    HIP_Z_F, HIP_Z_H = 1.00, 1.08
    L_F = (0.45, 0.42)
    L_H = (0.50, 0.46)
    FET = 0.15                  # fetlock height above ground at stance
    NECK_PIVOT = V((0.58, 0, 1.32))

    def __init__(self, C, coll):
        self.C, self.coll = C, coll
        self.root = U.empty("horse_root", coll=coll)
        # ---- body
        prof = [(-1.06, 1.33, 0.06, 0.06), (-1.0, 1.30, 0.21, 0.19), (-0.88, 1.27, 0.31, 0.28),
                (-0.68, 1.24, 0.35, 0.32), (-0.42, 1.21, 0.36, 0.33), (-0.15, 1.19, 0.37, 0.345),
                (0.15, 1.19, 0.37, 0.34), (0.40, 1.21, 0.37, 0.32), (0.58, 1.22, 0.35, 0.28),
                (0.74, 1.18, 0.30, 0.23), (0.86, 1.12, 0.19, 0.16), (0.91, 1.09, 0.06, 0.06)]
        secs = [(V((x, 0, zc)), V((0, 0, 1)), V((0, 1, 0)), h, w) for (x, zc, h, w) in prof]
        self.body = loft("horse_body", secs, C["horse"], segs=20, coll=coll)
        # withers bump + croup
        for (cx, cz, rx, rz, ry) in ((0.42, 1.52, 0.28, 0.09, 0.12), (-0.78, 1.5, 0.25, 0.08, 0.22)):
            b = U.prim("sphere", "horse_bump", radius=1.0, segs=16, rings=10, mat=C["horse"], coll=coll)
            for v in b.data.vertices:
                v.co = V((v.co.x * rx + cx, v.co.y * ry, v.co.z * rz + cz))
            U.parent(b, self.body, keep=False)
        U.parent(self.body, self.root, keep=False)
        # ---- neck + head (origin at neck pivot)
        self.neck = U.empty("horse_neck", coll=coll)
        npts = [V((0.0, 0, 0.0)), V((0.18, 0, 0.18)), V((0.33, 0, 0.38)), V((0.43, 0, 0.55))]
        nr = [(0.30, 0.18), (0.25, 0.14), (0.2, 0.11), (0.16, 0.095)]
        nk = path_loft("horse_neckm", npts, nr, up=V((0, 0, 1)), mat=C["horse"], segs=16, coll=coll, cap1=False)
        U.parent(nk, self.neck, keep=False)
        # head: from poll down to muzzle
        hp0 = V((0.42, 0, 0.60))
        hdir = V((0.6, 0, -0.8)).normalized()
        hpts = [hp0 + hdir * d for d in (-0.04, 0.06, 0.18, 0.32, 0.45, 0.55, 0.6)]
        hr = [(0.08, 0.075), (0.14, 0.095), (0.15, 0.10), (0.11, 0.085), (0.095, 0.075), (0.09, 0.07), (0.05, 0.05)]
        hd = path_loft("horse_head", hpts, hr, up=V((1, 0, 0.6)), mat=C["horse"], segs=16,
                       coll=coll)
        U.parent(hd, self.neck, keep=False)
        muz = U.prim("sphere", "horse_muzzle", radius=1.0, segs=14, rings=10, mat=C["horse_dark"], coll=coll)
        mc = hp0 + hdir * 0.55
        for v in muz.data.vertices:
            v.co = V((v.co.x * 0.075 + mc.x, v.co.y * 0.075, v.co.z * 0.085 + mc.z))
        U.parent(muz, self.neck, keep=False)
        # mane ridge
        mpts = [V((0.0, 0, 0.27)), V((0.12, 0, 0.40)), V((0.26, 0, 0.55)), V((0.38, 0, 0.66)), V((0.43, 0, 0.70))]
        mr = [(0.07, 0.03), (0.075, 0.032), (0.07, 0.03), (0.06, 0.028), (0.04, 0.02)]
        mane = path_loft("horse_mane", mpts, mr, up=V((-1, 0, 1)), mat=C["hair"], segs=10, coll=coll)
        U.parent(mane, self.neck, keep=False)
        fl = path_loft("horse_forelock", [hp0 + V((0.0, 0, 0.06)), hp0 + V((0.08, 0, -0.04)), hp0 + V((0.14, 0, -0.12))],
                       [(0.03, 0.04), (0.025, 0.035), (0.01, 0.015)], up=V((1, 0, 0)), mat=C["hair"], segs=8,
                       coll=coll)
        U.parent(fl, self.neck, keep=False)
        # eyes + nostrils + bridle
        for s in (-1, 1):
            e = U.prim("sphere", "horse_eye", radius=0.022, segs=10, rings=8, mat=C["eye"], coll=coll,
                       loc=tuple(hp0 + hdir * 0.13 + V((0.03, s * 0.09, 0.0))))
            U.parent(e, self.neck, keep=False)
        self.bit = {}
        for (d, r) in ((0.08, 0.1), (0.42, 0.105)):
            ring = U.lathe("bridle", [(r, -0.012), (r, 0.012)], segs=16, mat=C["leather"], coll=coll,
                           close_top=False, close_bottom=False, sx=0.8)
            c = hp0 + hdir * d
            ring.matrix_world = U.frame_matrix(c, hdir, V((0, 0, 1)))
            U.parent(ring, self.neck)
        for s in (-1, 1):
            # cheek strap
            a = hp0 + hdir * 0.08 + V((0, s * 0.085, 0))
            b = hp0 + hdir * 0.5 + V((0, s * 0.07, 0))
            st = U.capsule("cheek", (b - a).length, 0.008, 0.008, mat=C["leather"], coll=coll, segs=6)
            st.matrix_world = U.frame_matrix(a, b - a, V((0, s, 0)))
            U.parent(st, self.neck)
            bitp = hp0 + hdir * 0.5 + V((0.0, s * 0.075, -0.03))
            br = U.prim("sphere", "bitring", radius=0.018, segs=8, rings=6, mat=C["steel"], coll=coll, loc=tuple(bitp))
            U.parent(br, self.neck)
            self.bit[s] = bitp       # local to neck pivot
        # ears (separate pivots for flicks)
        self.ears = {}
        for s in (-1, 1):
            ep = U.empty("horse_ear_piv", loc=tuple(hp0 + V((-0.02, s * 0.06, 0.07))), coll=coll)
            ear = U.lathe("horse_ear", [(0.03, 0.0), (0.028, 0.06), (0.012, 0.12), (0.001, 0.14)], segs=8,
                          mat=C["horse"], coll=coll, sx=0.55)
            U.parent(ear, ep, keep=False)
            ep.rotation_euler = (s * -0.25, -0.15, 0)
            U.parent(ep, self.neck, keep=True)
            self.ears[s] = ep
        self.neck.location = self.NECK_PIVOT
        U.parent(self.neck, self.root, keep=False)
        self.neck.location = self.NECK_PIVOT
        # ---- tail (origin at dock)
        self.tail = U.empty("horse_tail", loc=(-1.04, 0, 1.36), coll=coll)
        tp = [V((0, 0, 0)), V((-0.1, 0, -0.08)), V((-0.16, 0, -0.3)), V((-0.17, 0, -0.55)), V((-0.14, 0, -0.78))]
        trr = [(0.05, 0.05), (0.06, 0.07), (0.07, 0.10), (0.06, 0.09), (0.02, 0.04)]
        tl = path_loft("horse_tailm", tp, [(b, a) for (a, b) in trr], up=V((1, 0, 0)), mat=C["hair"], segs=10,
                       coll=coll)
        U.parent(tl, self.tail, keep=False)
        U.parent(self.tail, self.root, keep=False)
        self.tail.location = (-1.04, 0, 1.36)
        # ---- saddle + tack (children of body)
        self._saddle()
        # ---- legs
        self.legs = {}
        for key, x, hipz, L, dark in (("LF", self.FRONT_X, self.HIP_Z_F, self.L_F, True),
                                      ("RF", self.FRONT_X, self.HIP_Z_F, self.L_F, True),
                                      ("LH", self.HIND_X, self.HIP_Z_H, self.L_H, True),
                                      ("RH", self.HIND_X, self.HIP_Z_H, self.L_H, True)):
            front = key[1] == "F"
            up = U.capsule("horse_up_" + key, L[0], 0.10 if front else 0.12, 0.05, mat=C["horse"], coll=coll)
            lo = U.capsule("horse_lo_" + key, L[1], 0.045, 0.038, mat=C["horse_dark"] if dark else C["horse"],
                           coll=coll)
            past = U.capsule("horse_pastern_" + key, 0.12, 0.042, 0.04, mat=C["horse_dark"], coll=coll, segs=10)
            hf = U.lathe("horse_hoof_" + key, [(0.062, 0.0), (0.052, 0.07), (0.045, 0.085), (0.001, 0.086)],
                         segs=14, mat=C["hoof"], coll=coll, sx=1.1)
            self.legs[key] = (up, lo, past, V((x, self.LEG_Y if key[0] == "L" else -self.LEG_Y, hipz)), L, front, hf)

    def _saddle(self):
        C, coll, b = self.C, self.coll, self.body
        # blanket
        bv, bf = [], []
        nx, nu = 6, 9
        for i in range(nx):
            x = -0.32 + 0.66 * i / (nx - 1)
            for j in range(nu):
                a = -math.pi * 0.5 + math.pi * j / (nu - 1)        # around the back
                r = 0.39
                bv.append((x, math.sin(a) * 0.36, 1.27 + math.cos(a) * r))
        for i in range(nx - 1):
            for j in range(nu - 1):
                bf.append([i * nu + j, (i + 1) * nu + j, (i + 1) * nu + j + 1, i * nu + j + 1])
        bl = U.mesh_obj("saddle_blanket", bv, bf, C["blanket"], smooth_shade=True, coll=coll)
        sm = bl.modifiers.new("solid", "SOLIDIFY"); sm.thickness = 0.02
        U.parent(bl, b, keep=False)
        # seat / tree
        seat = U.prim("sphere", "saddle_seat", radius=1.0, segs=18, rings=10, mat=C["leather"], coll=coll)
        for v in seat.data.vertices:
            x, y, z = v.co
            v.co = V((x * 0.3 + 0.02, y * 0.29, z * 0.09 + 1.645 - 0.05 * (x ** 2)))
        U.parent(seat, b, keep=False)
        for (x, z, h) in ((0.27, 1.70, 0.11), (-0.24, 1.70, 0.07)):
            cv = U.prim("sphere", "saddle_fork", radius=1.0, segs=14, rings=8, mat=C["leather"], coll=coll)
            for v in cv.data.vertices:
                v.co = V((v.co.x * 0.07 + x, v.co.y * 0.17, v.co.z * h + z))
            U.parent(cv, b, keep=False)
        horn = U.lathe("saddle_horn", [(0.025, 0), (0.02, 0.08), (0.045, 0.1), (0.001, 0.115)], segs=10,
                       mat=C["leather"], coll=coll)
        horn.location = (0.3, 0, 1.77)
        U.parent(horn, b, keep=False)
        horn.location = (0.3, 0, 1.77)
        for s in (-1, 1):
            fender = U.prim("cube", "saddle_fender", mat=C["leather"], coll=coll, smooth_shade=False)
            for v in fender.data.vertices:
                v.co = V((v.co.x * 0.24 + 0.05, v.co.y * 0.012 + s * 0.385, v.co.z * 0.36 + 1.33))
            U.parent(fender, b, keep=False)
            leather = U.prim("cube", "stirrup_leather", mat=C["leather"], coll=coll, smooth_shade=False)
            for v in leather.data.vertices:
                v.co = V((v.co.x * 0.05 + 0.05, v.co.y * 0.01 + s * 0.40, v.co.z * 0.3 + 1.12))
            U.parent(leather, b, keep=False)
            st = U.lathe("stirrup", [(0.07, -0.03), (0.075, 0.03)], segs=10, mat=C["leather"], coll=coll,
                         close_top=False, close_bottom=False, sx=0.9)
            st.rotation_euler = (math.pi / 2, 0, 0)
            st.location = (0.05, s * 0.41, 0.98)
            U.parent(st, b, keep=False)
            st.location = (0.05, s * 0.41, 0.98)
            st.rotation_euler = (math.pi / 2, 0, 0)
            bag = U.prim("cube", "saddlebag", mat=C["leather"], coll=coll, smooth_shade=False)
            for v in bag.data.vertices:
                v.co = V((v.co.x * 0.26 - 0.48, v.co.y * 0.09 + s * 0.36, v.co.z * 0.26 + 1.38))
            bm = bag.modifiers.new("bev", "BEVEL"); bm.width = 0.03; bm.segments = 2
            U.parent(bag, b, keep=False)
        cin = U.lathe("cinch", [(0.37, -0.03), (0.37, 0.03)], segs=24, mat=C["leather"], coll=coll,
                      close_top=False, close_bottom=False, sx=1.0, sy=1.0)
        cin.rotation_euler = (0, math.pi / 2, 0)
        cin.location = (0.22, 0, 1.2)
        cin.scale = (1.0, 0.95, 1.0)
        U.parent(cin, b, keep=False)
        cin.location = (0.22, 0, 1.2)
        cin.rotation_euler = (0, math.pi / 2, 0)
        roll = U.prim("cyl", "bedroll", radius=0.085, depth=0.62, segs=14, mat=C["bedroll"], coll=coll,
                      loc=(-0.36, 0, 1.68), rot=(math.pi / 2, 0, 0))
        U.parent(roll, b, keep=False)
        roll.location = (-0.36, 0, 1.68)
        roll.rotation_euler = (math.pi / 2, 0, 0)
        self.seat_local = V((0.0, 0, 1.70))
        self.stirrup_local = {1: V((0.05, 0.41, 1.05)), -1: V((0.05, -0.41, 1.05))}

    # ----------------------------------------------------------------- per-frame posing
    def key(self, frame, pos, yaw, bob=0.0, pitch=0.0, roll=0.0, neck=(0.0, 0.0, 0.0), tail=(0.0, 0.0),
            ears=(0.0, 0.0), hooves=None, breath=0.0):
        """hooves: dict key-> (world ground point, curl angle)"""
        M_root = U.trs(pos + V((0, 0, bob)), yaw, pitch, roll)
        U.key_matrix(self.root, M_root, frame)
        self.body.scale = (1.0, 1.0 + breath, 1.0 + breath * 0.6)
        self.body.keyframe_insert("scale", frame=frame)
        ny, np_, nr = neck
        q = (U.rot_z(ny) @ Matrix.Rotation(np_, 4, "Y") @ Matrix.Rotation(nr, 4, "X")).to_quaternion()
        U.key_local(self.neck, self.NECK_PIVOT, q, frame)
        tq = (Matrix.Rotation(tail[0], 4, "X") @ Matrix.Rotation(tail[1], 4, "Y")).to_quaternion()
        U.key_local(self.tail, V((-1.04, 0, 1.36)), tq, frame)
        for s, a in zip((1, -1), ears):
            ep = self.ears[s]
            ep.rotation_mode = "XYZ"
            ep.rotation_euler = (s * -0.25 + s * a * 0.3, -0.15 - a * 0.5, s * a * 0.6)
            ep.keyframe_insert("rotation_euler", frame=frame)
        fwd = V((math.cos(yaw), math.sin(yaw), 0))
        for k, (up, lo, past, hip_local, L, front, hf) in self.legs.items():
            hip = M_root @ hip_local
            g, curl = hooves[k]
            Rh = U.rot_z(yaw) @ Matrix.Rotation(curl, 4, "Y")
            U.key_matrix(hf, Matrix.Translation(g) @ Rh, frame)
            top = g + Rh.to_3x3() @ V((0.03, 0, 0.075))
            fet = top + Rh.to_3x3() @ V((-0.065, 0, 0.10))
            pole = hip + fwd * (1.2 if front else -1.2) - Z * 0.4
            j, fet2 = U.ik2(hip, fet, L[0], L[1], pole)
            U.key_matrix(up, U.frame_matrix(hip, j - hip, fwd), frame)
            U.key_matrix(lo, U.frame_matrix(j, fet2 - j, fwd), frame)
            U.key_matrix(past, U.frame_matrix(fet2, top - fet2, fwd), frame)

    def world_bit(self, pos, yaw, bob, pitch, roll, neck, s):
        M_root = U.trs(pos + V((0, 0, bob)), yaw, pitch, roll)
        ny, np_, nr = neck
        Mn = M_root @ Matrix.Translation(self.NECK_PIVOT) @ U.rot_z(ny) @ Matrix.Rotation(np_, 4, "Y") @ \
            Matrix.Rotation(nr, 4, "X")
        return Mn @ self.bit[s]
