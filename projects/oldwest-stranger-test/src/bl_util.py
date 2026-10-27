"""Geometry, material and math helpers for the Old West test scene (Blender 5.2 bpy)."""
import math
import random

import bpy
from mathutils import Matrix, Quaternion, Vector

V = Vector


# ------------------------------------------------------------------ math
def smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def smoother(x):
    x = min(1.0, max(0.0, x))
    return x * x * x * (x * (x * 6 - 15) + 10)


def lerp(a, b, t):
    return a + (b - a) * t


def ramp(t, t0, t1):
    if t1 <= t0:
        return 1.0 if t >= t1 else 0.0
    return smooth((t - t0) / (t1 - t0))


def keys(t, pts, ease=smooth):
    """piecewise interpolation through [(time, value), ...] (values: float or Vector)."""
    if t <= pts[0][0]:
        return pts[0][1].copy() if hasattr(pts[0][1], "copy") else pts[0][1]
    for (ta, va), (tb, vb) in zip(pts, pts[1:]):
        if t <= tb:
            u = ease((t - ta) / (tb - ta)) if tb > ta else 1.0
            return va + (vb - va) * u
    v = pts[-1][1]
    return v.copy() if hasattr(v, "copy") else v


def frame_matrix(origin, z_axis, x_hint):
    z = z_axis.normalized()
    x = x_hint - z * x_hint.dot(z)
    if x.length < 1e-6:
        x = V((1, 0, 0)) if abs(z.x) < 0.9 else V((0, 1, 0))
        x = x - z * x.dot(z)
    x.normalize()
    y = z.cross(x)
    m = Matrix((
        (x.x, y.x, z.x, origin.x),
        (x.y, y.y, z.y, origin.y),
        (x.z, y.z, z.z, origin.z),
        (0, 0, 0, 1)))
    return m


def ik2(root, target, l1, l2, pole):
    d_vec = target - root
    d = d_vec.length
    d = min(max(d, abs(l1 - l2) + 1e-3), (l1 + l2) * 0.9995)
    dirn = d_vec.normalized()
    a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
    h = math.sqrt(max(l1 * l1 - a * a, 0.0))
    p = pole - root
    p = p - dirn * p.dot(dirn)
    if p.length < 1e-6:
        p = V((0, 0, 1))
    p.normalize()
    joint = root + dirn * a + p * h
    end = root + dirn * d
    return joint, end


def rot_z(a):
    return Matrix.Rotation(a, 4, "Z")


def trs(loc, yaw=0.0, pitch=0.0, roll=0.0):
    return Matrix.Translation(loc) @ rot_z(yaw) @ Matrix.Rotation(pitch, 4, "Y") @ Matrix.Rotation(roll, 4, "X")


# ------------------------------------------------------------------ scene objects
def link(obj, coll=None):
    (coll or bpy.context.scene.collection).objects.link(obj)
    return obj


def mesh_obj(name, verts, faces, mat=None, uvs=None, attrs=None, smooth_shade=False, coll=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    if uvs is not None:
        uvl = me.uv_layers.new(name="UVMap")
        i = 0
        for poly in me.polygons:
            for li in poly.loop_indices:
                uvl.data[li].uv = uvs[i]
                i += 1
    if attrs:
        for an, vals in attrs.items():
            at = me.attributes.new(an, "FLOAT", "POINT")
            at.data.foreach_set("value", vals)
    me.validate()
    me.update()
    if smooth_shade:
        me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    if mat:
        me.materials.append(mat)
    link(ob, coll)
    return ob


class BoxBatch:
    """Accumulates oriented boxes ("planks") into one mesh with UVs along the plank length
    and a per-plank random attribute 'prand'."""

    def __init__(self):
        self.v, self.f, self.uv, self.r = [], [], [], []

    def box(self, c, size, ax=V((1, 0, 0)), ay=V((0, 1, 0)), az=V((0, 0, 1)), rnd=None):
        c = V(c)
        hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
        r = random.random() if rnd is None else rnd
        base = len(self.v)
        corners = []
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    corners.append((sx, sy, sz))
                    self.v.append(c + ax * (sx * hx) + ay * (sy * hy) + az * (sz * hz))
                    self.r.append(r)
        idx = {k: i for i, k in enumerate(corners)}
        quads = [
            [(-1, -1, -1), (-1, 1, -1), (-1, 1, 1), (-1, -1, 1)],
            [(1, -1, -1), (1, -1, 1), (1, 1, 1), (1, 1, -1)],
            [(-1, -1, -1), (-1, -1, 1), (1, -1, 1), (1, -1, -1)],
            [(-1, 1, -1), (1, 1, -1), (1, 1, 1), (-1, 1, 1)],
            [(-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1)],
            [(-1, -1, 1), (-1, 1, 1), (1, 1, 1), (1, -1, 1)],
        ]
        for q in quads:
            self.f.append([base + idx[k] for k in q])
            for (sx, sy, sz) in q:
                self.uv.append((sx * hx + r * 7.3, sy * hy + sz * hz + r * 13.1))

    def build(self, name, mat, coll=None):
        return mesh_obj(name, self.v, self.f, mat, uvs=self.uv, attrs={"prand": self.r}, coll=coll)


def prim(kind, name, loc=(0, 0, 0), scale=(1, 1, 1), rot=(0, 0, 0), mat=None, segs=24, rings=12,
         depth=1.0, radius=1.0, radius2=None, smooth_shade=True, coll=None, subsurf=0):
    """Create primitive via bmesh-free data so it works headless."""
    import bmesh
    bm = bmesh.new()
    if kind == "sphere":
        bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=radius)
    elif kind == "cyl":
        bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=radius,
                              radius2=radius if radius2 is None else radius2, depth=depth)
    elif kind == "cube":
        bmesh.ops.create_cube(bm, size=1.0)
    elif kind == "torus":
        pass
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth_shade:
        me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    ob.scale = scale
    ob.rotation_euler = rot
    if mat:
        me.materials.append(mat)
    link(ob, coll)
    if subsurf:
        m = ob.modifiers.new("sub", "SUBSURF")
        m.levels = subsurf
        m.render_levels = subsurf
    return ob


def lathe(name, profile, segs=24, mat=None, coll=None, close_top=True, close_bottom=True,
          sx=1.0, sy=1.0, smooth_shade=True, arc=None):
    """Revolve [(r, z), ...] around Z. arc=(a0, a1) for partial revolve (open surface)."""
    verts, faces = [], []
    full = arc is None
    a0, a1 = (0.0, 2 * math.pi) if full else arc
    n = segs if full else segs + 1
    for i in range(n):
        a = a0 + (a1 - a0) * i / segs
        for (r, z) in profile:
            verts.append((r * math.cos(a) * sx, r * math.sin(a) * sy, z))
    np_ = len(profile)
    for i in range(segs):
        i2 = (i + 1) % n if full else i + 1
        for j in range(np_ - 1):
            faces.append([i * np_ + j, i2 * np_ + j, i2 * np_ + j + 1, i * np_ + j + 1])
    if full:
        if close_bottom and profile[0][0] > 1e-4:
            faces.append([i * np_ for i in range(segs)][::-1])
        if close_top and profile[-1][0] > 1e-4:
            faces.append([i * np_ + np_ - 1 for i in range(segs)])
    ob = mesh_obj(name, verts, faces, mat, smooth_shade=smooth_shade, coll=coll)
    return ob


def capsule(name, length, r0, r1=None, mat=None, segs=14, coll=None, flat=1.0):
    """Tapered capsule along +Z from 0 to length (origin at joint)."""
    r1 = r0 if r1 is None else r1
    prof = []
    for i in range(5):
        a = -math.pi / 2 + (math.pi / 2) * i / 4
        prof.append((r0 * math.cos(a), r0 * math.sin(a) * 0.9))
    for i in range(1, 6):
        z = length * i / 6
        prof.append((lerp(r0, r1, i / 6), z))
    for i in range(5):
        a = (math.pi / 2) * i / 4
        prof.append((r1 * math.cos(a), length + r1 * math.sin(a) * 0.9))
    prof.append((0.0005, length + r1 * 0.9))
    prof[0] = (0.0005, -r0 * 0.9)
    return lathe(name, prof, segs=segs, mat=mat, coll=coll, sx=1.0, sy=flat)


def parent(child, par, keep=True):
    mw = child.matrix_world.copy()
    child.parent = par
    if keep:
        child.matrix_parent_inverse = par.matrix_world.inverted()
        child.matrix_world = mw


def empty(name, loc=(0, 0, 0), coll=None):
    e = bpy.data.objects.new(name, None)
    e.location = loc
    link(e, coll)
    return e


def key_matrix(ob, m, frame):
    loc, rot, sc = m.decompose()
    ob.rotation_mode = "QUATERNION"
    ob.location = loc
    ob.rotation_quaternion = rot
    ob.keyframe_insert("location", frame=frame)
    ob.keyframe_insert("rotation_quaternion", frame=frame)


def key_local(ob, loc, quat, frame, scale=None):
    ob.rotation_mode = "QUATERNION"
    ob.location = loc
    ob.rotation_quaternion = quat
    ob.keyframe_insert("location", frame=frame)
    ob.keyframe_insert("rotation_quaternion", frame=frame)
    if scale is not None:
        ob.scale = scale
        ob.keyframe_insert("scale", frame=frame)


# ------------------------------------------------------------------ materials
def _sock(socks, ident):
    for s in socks:
        if s.identifier == ident:
            return s
    raise KeyError(ident)


def MA(n):
    return _sock(n.inputs, "A_Color")


def MB(n):
    return _sock(n.inputs, "B_Color")


def MO(n):
    return _sock(n.outputs, "Result_Color")


def _nodes(mat):
    try:
        mat.use_nodes = True
    except Exception:
        pass
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    return nt, out


def principled(name, color, rough=0.6, metal=0.0, sheen=0.0, spec=0.5, emission=None, emit_str=0.0,
               coat=0.0, alpha=1.0, transmission=0.0):
    mat = bpy.data.materials.new(name)
    nt, out = _nodes(mat)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if sheen:
        b.inputs["Sheen Weight"].default_value = sheen
    b.inputs["Specular IOR Level"].default_value = spec
    if coat:
        b.inputs["Coat Weight"].default_value = coat
    if emission:
        b.inputs["Emission Color"].default_value = (*emission, 1)
        b.inputs["Emission Strength"].default_value = emit_str
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
    if transmission:
        b.inputs["Transmission Weight"].default_value = transmission
    nt.links.new(b.outputs[0], out.inputs[0])
    mat.diffuse_color = (*color, 1)
    return mat


def noisy_mat(name, c1, c2, scale=8.0, rough=0.7, bump=0.15, detail=6.0, sheen=0.0, coord="Object",
              stretch=(1, 1, 1), rough2=None, fac_pow=1.0):
    """Principled material whose color varies between c1/c2 with noise (cloth, leather, hide)."""
    mat = bpy.data.materials.new(name)
    nt, out = _nodes(mat)
    L = nt.links.new
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = stretch
    L(tc.outputs[coord], mp.inputs[0])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = detail
    L(mp.outputs[0], nz.inputs["Vector"])
    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 0.3
    cr.color_ramp.elements[0].color = (*c1, 1)
    cr.color_ramp.elements[1].position = 0.75
    cr.color_ramp.elements[1].color = (*c2, 1)
    L(nz.outputs["Fac"], cr.inputs[0])
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    L(cr.outputs[0], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    if sheen:
        b.inputs["Sheen Weight"].default_value = sheen
        b.inputs["Sheen Roughness"].default_value = 0.6
    if bump:
        bp = nt.nodes.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = bump
        bp.inputs["Distance"].default_value = 0.01
        L(nz.outputs["Fac"], bp.inputs["Height"])
        L(bp.outputs[0], b.inputs["Normal"])
    L(b.outputs[0], out.inputs[0])
    mat.diffuse_color = (*c1, 1)
    return mat


def wood_mat(name, warm=(0.32, 0.19, 0.10), gray=(0.36, 0.32, 0.27), dark=(0.10, 0.065, 0.04),
             weathered=0.5, rough=0.82, bump=0.35, paint=None, paint_amt=0.0):
    """Weathered plank material: grain along UV.u, per-plank variation from 'prand' attribute.
    optional peeling paint layer."""
    mat = bpy.data.materials.new(name)
    nt, out = _nodes(mat)
    L = nt.links.new
    N = nt.nodes.new
    uv = N("ShaderNodeUVMap")
    sep = N("ShaderNodeSeparateXYZ")
    L(uv.outputs[0], sep.inputs[0])
    att = N("ShaderNodeAttribute")
    att.attribute_name = "prand"
    # grain coordinates: (u*0.6, v*45)
    comb = N("ShaderNodeCombineXYZ")
    m1 = N("ShaderNodeMath"); m1.operation = "MULTIPLY"; m1.inputs[1].default_value = 0.6
    m2 = N("ShaderNodeMath"); m2.operation = "MULTIPLY"; m2.inputs[1].default_value = 45.0
    L(sep.outputs[0], m1.inputs[0]); L(sep.outputs[1], m2.inputs[0])
    L(m1.outputs[0], comb.inputs[0]); L(m2.outputs[0], comb.inputs[1])
    L(att.outputs["Fac"], comb.inputs[2])
    grain = N("ShaderNodeTexNoise"); grain.inputs["Scale"].default_value = 2.5
    grain.inputs["Detail"].default_value = 8; grain.inputs["Roughness"].default_value = 0.65
    L(comb.outputs[0], grain.inputs["Vector"])
    big = N("ShaderNodeTexNoise"); big.inputs["Scale"].default_value = 0.8; big.inputs["Detail"].default_value = 3
    comb2 = N("ShaderNodeCombineXYZ")
    L(sep.outputs[0], comb2.inputs[0]); L(sep.outputs[1], comb2.inputs[1]); L(att.outputs["Fac"], comb2.inputs[2])
    L(comb2.outputs[0], big.inputs["Vector"])
    # base: warm vs gray by plank random + big noise
    mixw = N("ShaderNodeMath"); mixw.operation = "MULTIPLY_ADD"
    L(att.outputs["Fac"], mixw.inputs[0]); mixw.inputs[1].default_value = 0.6
    L(big.outputs["Fac"], mixw.inputs[2])
    mixw2 = N("ShaderNodeMath"); mixw2.operation = "SUBTRACT"; mixw2.use_clamp = True
    L(mixw.outputs[0], mixw2.inputs[0]); mixw2.inputs[1].default_value = 1.0 - weathered
    c_wg = N("ShaderNodeMix"); c_wg.data_type = "RGBA"
    MA(c_wg).default_value = (*warm, 1); MB(c_wg).default_value = (*gray, 1)
    L(mixw2.outputs[0], c_wg.inputs[0])
    gr = N("ShaderNodeValToRGB")
    gr.color_ramp.elements[0].position = 0.35; gr.color_ramp.elements[0].color = (1, 1, 1, 1)
    gr.color_ramp.elements[1].position = 0.75; gr.color_ramp.elements[1].color = (0.0, 0.0, 0.0, 1)
    L(grain.outputs["Fac"], gr.inputs[0])
    c_d = N("ShaderNodeMix"); c_d.data_type = "RGBA"
    L(gr.outputs[0], c_d.inputs[0])
    c_d.inputs[0].default_value = 0.5
    L(MO(c_wg), MA(c_d)); MB(c_d).default_value = (*dark, 1)
    # fac = (1-gr)*0.55
    inv = N("ShaderNodeMath"); inv.operation = "MULTIPLY"; inv.inputs[1].default_value = 0.8
    gsep = N("ShaderNodeSeparateColor")
    L(gr.outputs[0], gsep.inputs[0])
    inv2 = N("ShaderNodeMath"); inv2.operation = "SUBTRACT"; inv2.inputs[0].default_value = 1.0
    L(gsep.outputs[0], inv2.inputs[1]); L(inv2.outputs[0], inv.inputs[0])
    L(inv.outputs[0], c_d.inputs[0])
    col_out = MO(c_d)
    if paint is not None and paint_amt > 0:
        pn = N("ShaderNodeTexNoise"); pn.inputs["Scale"].default_value = 6.0; pn.inputs["Detail"].default_value = 10
        L(comb2.outputs[0], pn.inputs["Vector"])
        pr = N("ShaderNodeValToRGB")
        pr.color_ramp.elements[0].position = 0.5 - paint_amt * 0.3
        pr.color_ramp.elements[1].position = 0.53 - paint_amt * 0.3
        L(pn.outputs["Fac"], pr.inputs[0])
        cm = N("ShaderNodeMix"); cm.data_type = "RGBA"
        L(pr.outputs[0], cm.inputs[0]); L(col_out, MA(cm)); MB(cm).default_value = (*paint, 1)
        col_out = MO(cm)
    b = N("ShaderNodeBsdfPrincipled")
    L(col_out, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    b.inputs["Specular IOR Level"].default_value = 0.35
    bp = N("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump; bp.inputs["Distance"].default_value = 0.004
    L(grain.outputs["Fac"], bp.inputs["Height"])
    L(bp.outputs[0], b.inputs["Normal"])
    L(b.outputs[0], out.inputs[0])
    mat.diffuse_color = (*warm, 1)
    return mat


def dirt_mat(name):
    mat = bpy.data.materials.new(name)
    nt, out = _nodes(mat)
    L = nt.links.new
    N = nt.nodes.new
    tc = N("ShaderNodeTexCoord")
    n1 = N("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 0.35; n1.inputs["Detail"].default_value = 6
    n2 = N("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 9.0; n2.inputs["Detail"].default_value = 12
    n3 = N("ShaderNodeTexVoronoi"); n3.inputs["Scale"].default_value = 30.0
    for n in (n1, n2, n3):
        L(tc.outputs["Object"], n.inputs["Vector"])
    cr = N("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 0.35; cr.color_ramp.elements[0].color = (0.30, 0.20, 0.12, 1)
    cr.color_ramp.elements[1].position = 0.7; cr.color_ramp.elements[1].color = (0.52, 0.38, 0.25, 1)
    L(n1.outputs["Fac"], cr.inputs[0])
    mix = N("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
    mix.inputs[0].default_value = 0.35
    L(cr.outputs[0], MA(mix)); L(n2.outputs["Color"], MB(mix))
    b = N("ShaderNodeBsdfPrincipled")
    L(MO(mix), b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.95
    b.inputs["Specular IOR Level"].default_value = 0.2
    add = N("ShaderNodeMath"); add.operation = "ADD"
    L(n2.outputs["Fac"], add.inputs[0])
    sc = N("ShaderNodeMath"); sc.operation = "MULTIPLY"; sc.inputs[1].default_value = 0.5
    L(n3.outputs["Distance"], sc.inputs[0]); L(sc.outputs[0], add.inputs[1])
    bp = N("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.5; bp.inputs["Distance"].default_value = 0.02
    L(add.outputs[0], bp.inputs["Height"]); L(bp.outputs[0], b.inputs["Normal"])
    L(b.outputs[0], out.inputs[0])
    mat.diffuse_color = (0.45, 0.33, 0.22, 1)
    return mat


def emission_mat(name, color, strength):
    mat = bpy.data.materials.new(name)
    nt, out = _nodes(mat)
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs[0].default_value = (*color, 1)
    e.inputs[1].default_value = strength
    nt.links.new(e.outputs[0], out.inputs[0])
    return mat


def glass_mat(name, tint=(0.75, 0.72, 0.6), dirt=0.25):
    """cheap window glass: transparent + glossy mix (no refraction noise)."""
    mat = bpy.data.materials.new(name)
    nt, out = _nodes(mat)
    N = nt.nodes.new
    L = nt.links.new
    tr = N("ShaderNodeBsdfTransparent"); tr.inputs[0].default_value = (*tint, 1)
    gl = N("ShaderNodeBsdfGlossy"); gl.inputs["Roughness"].default_value = 0.08
    fr = N("ShaderNodeFresnel"); fr.inputs[0].default_value = 1.5
    mx = N("ShaderNodeMixShader")
    L(fr.outputs[0], mx.inputs[0]); L(tr.outputs[0], mx.inputs[1]); L(gl.outputs[0], mx.inputs[2])
    df = N("ShaderNodeBsdfDiffuse"); df.inputs[0].default_value = (0.35, 0.3, 0.24, 1)
    mx2 = N("ShaderNodeMixShader"); mx2.inputs[0].default_value = dirt
    L(mx.outputs[0], mx2.inputs[1]); L(df.outputs[0], mx2.inputs[2])
    L(mx2.outputs[0], out.inputs[0])
    return mat


def haze_mat(name, base, haze=(0.95, 0.6, 0.38), dist=900.0, strength=1.0):
    """distant silhouette material blended to a warm haze by camera distance."""
    mat = bpy.data.materials.new(name)
    nt, out = _nodes(mat)
    N = nt.nodes.new
    L = nt.links.new
    b = N("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (*base, 1)
    b.inputs["Roughness"].default_value = 1.0
    cd = N("ShaderNodeCameraData")
    dv = N("ShaderNodeMath"); dv.operation = "DIVIDE"; dv.inputs[1].default_value = -dist
    L(cd.outputs["View Distance"], dv.inputs[0])
    ex = N("ShaderNodeMath"); ex.operation = "EXPONENT"
    L(dv.outputs[0], ex.inputs[0])
    inv = N("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0
    L(ex.outputs[0], inv.inputs[1])
    em = N("ShaderNodeEmission"); em.inputs[0].default_value = (*haze, 1); em.inputs[1].default_value = strength
    mx = N("ShaderNodeMixShader")
    L(inv.outputs[0], mx.inputs[0]); L(b.outputs[0], mx.inputs[1]); L(em.outputs[0], mx.inputs[2])
    L(mx.outputs[0], out.inputs[0])
    return mat
