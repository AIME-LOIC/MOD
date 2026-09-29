#!/usr/bin/env python3
"""
glbkit — tiny dependency-free GLB writer (pure python, stdlib only).

Geometry = list of parts: (name, verts[(x,y,z)], faces[(a,b,c)], color rgb 0-1, matrix or None)
matrix = 4x4 column-major like glTF (m[12],m[13],m[14] = translation).

The game builds colliders from node names, so part names matter (Car_/House_/Tower_...).
"""
import json, struct, math

def xform(m, p):
    x, y, z = p
    return (m[0]*x + m[4]*y + m[8]*z + m[12],
            m[1]*x + m[5]*y + m[9]*z + m[13],
            m[2]*x + m[6]*y + m[10]*z + m[14])

def tr(m, x, y, z):
    return (m[0]*x + m[4]*y + m[8]*z + m[12],
            m[1]*x + m[5]*y + m[9]*z + m[13],
            m[2]*x + m[6]*y + m[10]*z + m[14])

def mat_mul(a, b):
    # column-major 4x4
    out = [0.0]*16
    for c in range(4):
        for r in range(4):
            out[c*4+r] = sum(a[k*4+r]*b[c*4+k] for k in range(4))
    return out

def T(x=0, y=0, z=0):
    return [1,0,0,0, 0,1,0,0, 0,0,1,0, x,y,z,1]

def S(sx=1, sy=1, sz=1):
    return [sx,0,0,0, 0,sy,0,0, 0,0,sz,0, 0,0,0,1]

def Ry(a):
    c, s = math.cos(a), math.sin(a)
    return [c,0,-s,0, 0,1,0,0, s,0,c,0, 0,0,0,1]

def Rx(a):
    c, s = math.cos(a), math.sin(a)
    return [1,0,0,0, 0,c,s,0, 0,-s,c,0, 0,0,0,1]

def Rz(a):
    c, s = math.cos(a), math.sin(a)
    return [c,s,0,0, -s,c,0,0, 0,0,1,0, 0,0,0,1]

import math  # noqa: E402  (used above via guard import too)

# ---------------- per-instance transform helper: compose T*Ry*S ----------------
def placed(x, y, z, ang=0.0, sx=1, sy=1, sz=1):
    return mat_mul(T(x, y, z), mat_mul(Ry(ang), S(sx, sy, sz)))

def box(name, sx, sy, sz, color, m=None, x=0, y=0, z=0):
    """Axis-aligned box sx*sy*sz, centered at (x,y,z) in local space (m = parent matrix)."""
    m = m if m is not None else T(x, y, z)
    hx, hy, hz = sx/2, sy/2, sz/2
    verts = [(-hx,-hy,-hz),(hx,-hy,-hz),(hx,hy,-hz),(-hx,hy,-hz),
             (-hx,-hy, hz),(hx,-hy, hz),(hx,hy, hz),(-hx,hy, hz)]
    verts = [xform(m, v) for v in verts]
    faces = [(0,2,1),(0,3,2),(4,5,6),(4,6,7),(0,1,5),(0,5,4),(2,3,7),(2,7,6),(0,4,7),(0,7,3),(1,2,6),(1,6,5)]
    return (name, verts, faces, color)

def cyl(name, r, h, color, seg=14, m=None, x=0, y=0, z=0):
    """Vertical cylinder (Y axis), centered, capped."""
    m = m if m is not None else T(x, y, z)
    verts, faces = [], []
    for i in range(seg):
        a = 2*math.pi*i/seg
        verts.append((math.cos(a)*r, -h/2, math.sin(a)*r))
    for i in range(seg):
        a = 2*math.pi*i/seg
        verts.append((math.cos(a)*r, h/2, math.sin(a)*r))
    verts.append((0,-h/2,0)); ci_b = len(verts)-1
    verts.append((0, h/2,0)); ci_t = len(verts)-1
    for i in range(seg):
        j = (i+1) % seg
        faces.append((i, j, seg+j)); faces.append((i, seg+j, seg+i))
        faces.append((ci_b, j, i))
        faces.append((ci_t, seg+i, seg+j))
    verts = [xform(m, v) for v in verts]
    return (name, verts, faces, color)

def write_glb(path, parts, name="asset"):
    """parts: list of (nodename, verts, faces, rgb). One mesh per part => per-node colliders in game."""
    buffers = []   # (bytes) accumulated
    gltf = {"asset": {"version": "2.0", "generator": "glbkit (Compound Ops)"},
            "scene": 0, "scenes": [{"nodes": list(range(len(parts)))}],
            "nodes": [], "meshes": [], "accessors": [], "bufferViews": [], "buffers": []}
    bin = bytearray()

    def acc_from(data, comp_type, type_str, count):
        nonlocal bin
        off = len(bin)
        pad = (4 - off % 4) % 4
        bin += b'\0'*pad
        off = len(bin)
        bin += data
        gltf["bufferViews"].append({"buffer": 0, "byteOffset": off, "byteLength": len(data)})
        idx = len(gltf["bufferViews"]) - 1
        mn, mx = None, None
        return idx, mn, mx

    for (nm, verts, faces, rgb) in parts:
        # positions with min/max (required for POSITION)
        pos = b''.join(struct.pack('<3f', *v) for v in verts)
        mn = [min(v[i] for v in verts) for i in range(3)]
        mx = [max(v[i] for v in verts) for i in range(3)]
        off = len(bin); pad = (4 - off % 4) % 4
        bin += b'\0'*pad; off = len(bin)
        bin += pos
        pv = len(gltf["bufferViews"])
        gltf["bufferViews"].append({"buffer": 0, "byteOffset": off, "byteLength": len(pos)})
        pi = len(gltf["accessors"])
        gltf["accessors"].append({"bufferView": pv, "componentType": 5126, "count": len(verts),
                                  "type": "VEC3", "min": mn, "max": mx})
        # colors: VEC4 normalized ubyte per vertex
        cdata = bytes(bytearray(b for v in verts for b in (int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255), 255)))
        off = len(bin); pad = (4 - off % 4) % 4
        bin += b'\0'*pad; off = len(bin)
        bin += cdata
        cv = len(gltf["bufferViews"])
        gltf["bufferViews"].append({"buffer": 0, "byteOffset": off, "byteLength": len(cdata)})
        ci = len(gltf["accessors"])
        gltf["accessors"].append({"bufferView": cv, "componentType": 5121, "count": len(verts),
                                  "type": "VEC4", "normalized": True})
        # indices (uint32)
        idata = b''.join(struct.pack('<I', i) for f in faces for i in f)
        off = len(bin); pad = (4 - off % 4) % 4
        bin += b'\0'*pad; off = len(bin)
        bin += idata
        iv = len(gltf["bufferViews"])
        gltf["bufferViews"].append({"buffer": 0, "byteOffset": off, "byteLength": len(idata)})
        ii = len(gltf["accessors"])
        gltf["accessors"].append({"bufferView": iv, "componentType": 5125, "count": len(faces)*3,
                                  "type": "SCALAR"})
        mesh_idx = len(gltf["meshes"])
        gltf["meshes"].append({"primitives": [{"attributes": {"POSITION": pi, "COLOR_0": ci},
                                               "indices": ii, "mode": 4}]})
        gltf["nodes"].append({"name": nm, "mesh": mesh_idx})
    gltf["buffers"] = [{"byteLength": len(bin)}]
    js = json.dumps(gltf, separators=(',', ':')).encode()
    padj = (4 - len(js) % 4) % 4
    js += b' ' * padj
    total = 12 + 8 + len(js) + 8 + len(bin)
    with open(path, 'wb') as f:
        f.write(struct.pack('<III', 0x46546C67, 2, total))
        f.write(struct.pack('<II', len(js), 0x4E4F534A)); f.write(js)
        f.write(struct.pack('<II', len(bin), 0x004E4942)); f.write(bytes(bin))
    return total
