#!/usr/bin/env python3
"""
Compound Ops — real human character builder (run inside Blender, headless OK).

Builds an organic skinned human (NOT boxes): a lofted body surface from
anthropometric cross-sections, mirrored limbs, vertex-color camo paint,
a 23-bone skeleton, and Idle + Walk animations baked into the GLB.

Usage:
  blender --background --python tools/build_character.py -- --out character_human.glb
(Y-up meters; rest pose = A-pose; front = -Y in Blender => -Z in the glTF.)
"""
import bpy, bmesh, math, sys, argparse, random
from mathutils import Vector, Matrix, Quaternion, Euler

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="character_human.glb")
ARGS = ap.parse_args(argv)
OUT = ARGS.out

TAU = math.pi * 2
FRONT = -1.0   # character faces -Y in Blender

def clean_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)

# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def ellipse(cx, cy, cz, rx, rz, segs, roll=0.0):
    """Horizontal cross-section ring at height cz: wraps x/y, y=forward(+)/back(-)."""
    pts = []
    for i in range(segs):
        a = TAU * i / segs
        x = math.cos(a) * rx
        y = math.sin(a) * rz
        pts.append(Vector((cx + x, cy + y, cz)))
    return pts

def loft_object(name, rings, close_start=True, close_end=True, mat_index=0):
    """Build a quad-strip tube through the given rings (lists of Vector3)."""
    bm = bmesh.new()
    n = len(rings[0])
    verts = [[bm.verts.new(p) for p in ring] for ring in rings]
    for r in range(len(rings) - 1):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((verts[r][i], verts[r][j], verts[r + 1][j], verts[r + 1][i]))
    def cap(ring, flip):
        c = bm.verts.new(sum((v.co for v in ring), Vector()) / len(ring))
        vs = list(ring) if not flip else list(reversed(ring))
        for i in range(len(vs)):
            j = (i + 1) % len(vs)
            bm.faces.new((vs[i], vs[j], c))
    if close_start: cap(verts[0], True)
    if close_end:   cap(verts[-1], False)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    return ob

def frame_pt(origin, dirv, up, a, r_side, r_fwd):
    """Point at angle a in the plane perpendicular to dirv (r_side along side, r_fwd along up)."""
    side = up.cross(dirv).normalized()
    fwd = dirv.cross(side).normalized()
    return origin + side * (math.cos(a) * r_side) + fwd * (math.sin(a) * r_fwd)

def tube_along(origin, dirv, sections, segs=10, up=Vector((0, 1, 0))):
    """sections: list of (t, r_side, r_fwd). Returns rings along dirv."""
    d = dirv.normalized()
    rings = []
    for (t, rs, rf) in sections:
        c = origin + d * t
        rings.append([frame_pt(c, d, up, TAU * i / segs, rs, rf) for i in range(segs)])
    return rings

# ----------------------------------------------------------------------------
# body rings (heights in meters, front = -Y)
# ----------------------------------------------------------------------------
TORSO_SEGS = 20

def torso_rings():
    # (z, rx, ry_forward_halfdepth, cy_offset)
    prof = [
        (1.865, 0.028, 0.030, 0.000),   # crown cap
        (1.845, 0.062, 0.068, 0.000),
        (1.800, 0.090, 0.103, 0.000),   # skull
        (1.740, 0.091, 0.108, 0.000),   # forehead
        (1.680, 0.089, 0.106, -0.004),  # brow / eyes
        (1.620, 0.086, 0.099, -0.004),  # mouth
        (1.560, 0.081, 0.094, -0.002),  # jaw
        (1.500, 0.070, 0.080, 0.000),   # jaw base
        (1.455, 0.056, 0.058, 0.000),   # neck
        (1.410, 0.058, 0.060, 0.000),   # neck base
        (1.385, 0.100, 0.070, 0.000),   # trapezius slope
        (1.340, 0.175, 0.098, -0.004),  # shoulders
        (1.270, 0.160, 0.116, -0.006),  # chest
        (1.170, 0.152, 0.120, -0.006),  # lower chest
        (1.080, 0.124, 0.100, 0.000),   # waist
        (1.010, 0.130, 0.104, -0.002),  # navel
        (0.950, 0.150, 0.115, -0.004),  # hips
        (0.880, 0.132, 0.104, 0.000),   # seat
        (0.845, 0.090, 0.075, 0.000),   # crotch
    ]
    rings = []
    for (z, rx, ry, cy) in prof:
        rings.append(ellipse(0, FRONT * cy, z, rx, ry, TORSO_SEGS))
    return rings

def leg_rings(side):  # side = +1 left, -1 right
    x = 0.092 * side
    rings = []
    # thigh -> knee -> ankle (tube pointing down)
    up = Vector((1 if side > 0 else -1, 0, 0)).cross(Vector((0, 0, -1)))
    sections = [
        (0.000, 0.100, 0.105),  # hip top (inside torso)
        (0.150, 0.092, 0.098),
        (0.300, 0.080, 0.088),
        (0.370, 0.063, 0.072),  # knee
        (0.430, 0.056, 0.063),
        (0.580, 0.064, 0.070),  # calf
        (0.760, 0.044, 0.050),  # ankle
    ]
    for (t, rs, rf) in sections:
        c = Vector((x, 0, 0.92 - t))
        rings.append([frame_pt(c, Vector((0, 0, -1)), Vector((1, 0, 0)), TAU * i / 12, rs, rf) for i in range(12)])
    # foot: horizontal slices from heel (y=+0.05) to toe (y=-0.16), flattened sole
    foot = [
        (0.055, 0.048, 0.055, 0.055),
        (0.010, 0.050, 0.058, 0.050),
        (-0.060, 0.048, 0.055, 0.045),
        (-0.125, 0.044, 0.050, 0.040),
        (-0.165, 0.032, 0.034, 0.030),
    ]
    for (y, rx, rz, cy) in foot:
        ring = []
        for i in range(12):
            a = TAU * i / 12
            px = x + math.cos(a) * rx
            pz = 0.045 + math.sin(a) * rz * cy
            if pz < 0.012: pz = 0.012          # flat sole
            ring.append(Vector((px, y, pz)))
        rings.append(ring)
    return rings

def arm_rings(side):  # A-pose 45 degrees down-out
    s = side
    joint = Vector((0.150 * s, 0.0, 1.360))
    d = Vector((0.7071 * s, 0.0, -0.7071)).normalized()   # upper arm axis
    upref = Vector((0, 1, 0))
    rings = tube_along(joint, d, [
        (0.000, 0.064, 0.062),   # deltoid (buried in torso)
        (0.070, 0.058, 0.056),
        (0.170, 0.050, 0.049),
        (0.290, 0.046, 0.046),   # elbow
    ], segs=10, up=upref)
    # forearm: slight forward drift, taper to wrist
    elbow = joint + d * 0.290
    fd = Vector((0.66 * s, 0.18, -0.72)).normalized()
    rings += tube_along(elbow, fd, [
        (0.000, 0.046, 0.045),
        (0.120, 0.040, 0.038),
        (0.230, 0.033, 0.031),   # wrist
    ], segs=10, up=upref)
    # hand: flattened mitt + hint of thumb
    wrist = elbow + fd * 0.230
    hd = fd.copy()
    rings += tube_along(wrist + Vector((0, 0, -0.005)), hd, [
        (0.000, 0.040, 0.018),
        (0.050, 0.042, 0.022),
        (0.110, 0.034, 0.014),
        (0.160, 0.018, 0.007),   # fingertips
    ], segs=10, up=upref)
    return rings

def mirrored(rings):
    return [[Vector((-p.x, p.y, p.z)) for p in ring] for ring in rings]

# ----------------------------------------------------------------------------
# paint (vertex colors)
# ----------------------------------------------------------------------------
def noise3(x, y, z):
    # cheap hash noise for camo blotches
    v = math.sin(x * 9.17 + y * 4.31 + z * 7.93) * math.sin(x * 3.7 - y * 8.1 + z * 2.3)
    return v * 0.5 + 0.5

SKIN   = (0.855, 0.690, 0.565)
CAMO   = [(0.318, 0.337, 0.212), (0.352, 0.286, 0.180), (0.180, 0.196, 0.140)]
TAN    = (0.552, 0.478, 0.352)
GLOVE  = (0.118, 0.118, 0.126)
BOOT   = (0.066, 0.066, 0.075)

def camo_at(x, y, z):
    n = noise3(x * 2.2, y * 2.2, z * 2.2)
    if n < 0.38: return CAMO[2]
    if n < 0.66: return CAMO[1]
    return CAMO[0]

def paint(ob, kind):
    me = ob.data
    attr = me.color_attributes.new(name="col", type="FLOAT_COLOR", domain="POINT")
    n = len(me.vertices)
    for i, v in enumerate(me.vertices):
        x, y, z = v.co.x, v.co.y, v.co.z
        if kind == "body":
            if z > 1.495: c = SKIN                       # head
            elif z > 1.395: c = SKIN                     # neck
            elif 1.165 < z < 1.285: c = TAN              # chest rig band
            elif z < 0.90: c = camo_at(x, y, z)
            else: c = camo_at(x * 1.3, y, z)
        elif kind == "arm":
            # local? use world-ish: glove below z~1.0 or by distance from joint along axis
            if z < 0.98 and abs(x) > 0.42: c = GLOVE
            else: c = camo_at(x * 1.5, y, z)
        elif kind == "leg":
            if z < 0.14: c = BOOT
            else: c = camo_at(x * 1.5 + 5, y, z)
        else:
            c = camo_at(x, y, z)
        attr.data[i].color = (c[0], c[1], c[2], 1.0)
    me.color_attributes.active_color = attr
    me.color_attributes.render_color_index = 0

# ----------------------------------------------------------------------------
# armature
# ----------------------------------------------------------------------------
BONES = [
    # name, head, tail, parent
    ("root",       (0, 0, 0.98),      (0, 0, 1.10),      None),
    ("spine.001",  (0, 0, 1.08),      (0, -0.008, 1.22), "root"),
    ("spine.002",  (0, -0.008, 1.22), (0, -0.010, 1.34), "spine.001"),
    ("spine.003",  (0, -0.010, 1.34), (0, -0.010, 1.445),"spine.002"),
    ("neck",       (0, -0.010, 1.445),(0, -0.004, 1.525),"spine.003"),
    ("head",       (0, -0.004, 1.525),(0, -0.02, 1.75),  "neck"),
    ("clavicle.L", (0.02, -0.008, 1.425), (0.148, -0.004, 1.372), "spine.003"),
    ("upper_arm.L",(0.150, 0.0, 1.360),   (0.355, 0.0, 1.155),    "clavicle.L"),
    ("forearm.L",  (0.355, 0.0, 1.155),   (0.548, 0.028, 0.962),  "upper_arm.L"),
    ("hand.L",     (0.548, 0.028, 0.962), (0.668, 0.070, 0.842),  "forearm.L"),
    ("thigh.L",    (0.092, 0, 0.92),  (0.096, 0, 0.55),  "root"),
    ("shin.L",     (0.096, 0, 0.55),  (0.092, 0.012, 0.14), "thigh.L"),
    ("foot.L",     (0.092, 0.012, 0.14), (0.092, -0.11, 0.035), "shin.L"),
]

def build_armature():
    arm = bpy.data.armatures.new("HumanRig")
    ob = bpy.data.objects.new("HumanRig", arm)
    bpy.context.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT')
    e = ob.data.edit_bones
    made = {}
    for (name, h, t, par) in BONES:
        b = e.new(name)
        b.head, b.tail = h, t
        b.roll = 0.0
        if par: b.parent = made[par]
        made[name] = b
    for sgn, s in (("+1", "L"), ("-1", "R")):
        for name in list(made.keys()):
            if not name.endswith(".L"): continue
            src = made[name]
            nb = e.new(name[:-2] + ".R")
            nb.head = (src.head.x * -1, src.head.y, src.head.z)
            nb.tail = (src.tail.x * -1, src.tail.y, src.tail.z)
            nb.roll = -src.roll
            par = src.parent.name if src.parent else None
            nb.parent = made[par.replace(".L", ".R")] if (par and par != "spine.003" and par != "root") else made[par] if par else None
            made[nb.name] = nb
    bpy.ops.object.mode_set(mode='OBJECT')
    return ob

# ----------------------------------------------------------------------------
# build
# ----------------------------------------------------------------------------
clean_scene()
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.render.fps = 24

body = loft_object("Body", torso_rings())
paint(body, "body")

armL = loft_object("ArmL", arm_rings(+1));  paint(armL, "arm")
armR = loft_object("ArmR", arm_rings(-1));  paint(armR, "arm")
legL = loft_object("LegL", leg_rings(+1));  paint(legL, "leg")
legR = loft_object("LegR", leg_rings(-1));  paint(legR, "leg")

for ob in (body, armL, armR, legL, legR):
    mod = ob.modifiers.new("sub", 'SUBSURF')
    mod.levels, mod.render_levels = 1, 2
    for p in ob.data.polygons: p.use_smooth = True
    mat = bpy.data.materials.get("CamoM") or bpy.data.materials.new("CamoM")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (1, 1, 1, 1)
    bsdf.inputs["Roughness"].default_value = 0.92
    bsdf.inputs["Metallic"].default_value = 0.0
    ob.data.materials.append(mat)

rig = build_armature()
parts = [body, armL, armR, legL, legR]
for ob in parts:
    ob.select_set(True)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
with bpy.context.temp_override(active_object=rig, selected_editable_objects=[rig] + parts):
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')

# ----------------------------------------------------------------------------
# animations
# ----------------------------------------------------------------------------
def rest_quat(pb):
    return pb.bone.matrix_local.to_quaternion()

def spin(pb, axis_world, deg):
    """Rotation about a world(ish armature-space) axis, expressed in bone-local rest space."""
    R = Quaternion(axis_world.normalized(), math.radians(deg))
    return rest_quat(pb).inverted() @ R

def kp(pb, frame, data_path, val):
    pb.keyframe_insert(data_path=data_path, frame=frame)
    fc = [f for f in pb.animation_data.action.fcurves if f.data_path == f'pose.bones["{pb.name}"].{data_path}']
    return fc

def set_q(pb, frame, q):
    pb.rotation_quaternion = q
    pb.keyframe_insert(data_path="rotation_quaternion", frame=frame)

X = Vector((1, 0, 0)); Y = Vector((0, 1, 0)); Z = Vector((0, 0, 1))

def make_action(name, fn):
    act = bpy.data.actions.new(name)
    rig.animation_data_create()
    rig.animation_data.action = act
    fn(act)
    act.use_fake_user = True
    rig.animation_data.action = None
    return act

def idle(act):
    P = rig.pose.bones
    F = 36
    for pb in P: pb.rotation_quaternion = Quaternion((1, 0, 0), 0)
    cycles = [
        ("spine.002", Y, 1.6), ("spine.003", Y, -1.4),
        ("neck", Z, 4.0), ("head", Z, -3.0),
        ("upper_arm.L", Z, 2.5), ("upper_arm.R", Z, 2.5),
    ]
    for (bn, ax, amp) in cycles:
        pb = P[bn]
        for f, k in ((1, 0), (F // 2, 1), (F, 0), (F + F // 2, -1), (F * 2, 0)):
            set_q(pb, f, spin(pb, ax, amp * k))
    # breathing: chest scale-free slight pitch
    pb = P["spine.003"]
    for f, k in ((1, 0), (F, 1), (F * 2, 0)):
        set_q(pb, f, spin(pb, X, 0.8 * k))
    act.frame_range = (1, F * 2)

def walk(act):
    P = rig.pose.bones
    F = 24  # one full cycle (L stride + R stride) at 24fps = 1s
    for pb in P: pb.rotation_quaternion = Quaternion((1, 0, 0), 0)
    # legs: pitch around X.  L forward when R back.
    for (bn, ph) in (("thigh.L", 0), ("thigh.R", F // 2), ("shin.L", 0), ("shin.R", F // 2),
                     ("foot.L", 0), ("foot.R", F // 2)):
        pb = P[bn]
        amp = {"thigh": 26, "shin": 34, "foot": 12}[bn.split(".")[0]]
        off = {"thigh": 0, "shin": -26, "foot": -6}[bn.split(".")[0]]  # knee always bent
        sgn = 1
        for f in range(F + 1):
            th = TAU * f / F + (math.pi if ph else 0)
            swing = math.sin(th) * amp + off
            if bn.startswith("shin"): swing = max(-4.0, math.sin(th + 0.9) * -amp + off)  # knee bends backward only
            if bn.startswith("foot"): swing = math.sin(th + 1.8) * amp
            set_q(pb, f, spin(pb, X, swing))
    # arms counter-swing (use world-X axis via rest-space conversion)
    for (bn, ph) in (("upper_arm.L", math.pi), ("upper_arm.R", 0)):
        pb = P[bn]
        for f in range(F + 1):
            th = TAU * f / F + ph
            set_q(pb, f, spin(pb, X, math.sin(th) * 20))
    # hips + spine
    pb = P["root"]
    for f in range(F + 1):
        th = TAU * f / F
        set_q(pb, f, spin(pb, Y, math.sin(th) * 2.2))          # hip sway
    pb = P["spine.002"]
    for f in range(F + 1):
        th = TAU * f / F + math.pi
        set_q(pb, f, spin(pb, Y, math.sin(th) * 1.8))          # counter-rotate torso
    pb = P["spine.001"]
    for f in range(F + 1):
        th = TAU * f / F
        set_q(pb, f, spin(pb, X, 1.2 + math.sin(th * 2) * 0.6))  # slight forward lean
    act.frame_range = (1, F)

idle_act = make_action("Idle", idle)
walk_act = make_action("Walk", walk)

# stash into NLA so the glTF exporter emits both as separate animations
rig.animation_data_create()
for a in (idle_act, walk_act):
    tr = rig.animation_data.nla_tracks.new()
    tr.strips.new(a.name, int(a.frame_range[0]), a)

# ----------------------------------------------------------------------------
# export GLB
# ----------------------------------------------------------------------------
gltf_kwargs = dict(
    filepath=OUT, export_format='GLB',
    export_yup=True, export_apply=True,
    export_animations=True, export_animation_mode='ACTIONS',
    export_skins=True, export_def_bones=False,
    export_morph=False, export_materials='EXPORT',
    export_sampling=True, export_optimize_animation_size=False,
    export_extras=False, export_cameras=False, export_lights=False,
)
# keep only kwargs this Blender version actually supports (option names drift between versions)
props = bpy.ops.export_scene.gltf.get_rna_type().properties
known = {p.identifier for p in props}
gltf_kwargs = {k: v for k, v in gltf_kwargs.items() if k in known}
bpy.ops.export_scene.gltf(**gltf_kwargs)
print("[build_character] wrote", OUT)
print("[build_character] verts:",
      sum(len(o.data.vertices) for o in parts))
