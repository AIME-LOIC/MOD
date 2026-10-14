#!/usr/bin/env python3
"""
Compound Ops — REALCITY: the destroyed war city, built in Blender.

Design language (researched from COD:MW NYC / Manhattan ground zero):
  * Manhattan-style dense grid: avenues + crosstown streets + a diagonal Broadway cut
  * Brownstone/brick rowhouses with NY fire escapes, water towers on blocky tenements
  * REAL window openings (piers/sills/lintels — no painted-on windows, no single colors)
  * Destroyed landmarks: Empire-State-style limestone tower with snapped mast,
    glass titan stump, Chrysler-style leaning spire, collapsed TV broadcast mast
  * Times Square burns: dead neon billboards, subway entrances, steam grates,
    scaffolding, burnt yellow-cab hulks
  * War dressing: burnt vehicle hulks, tank wrecks, craters, hedgehogs, sandbags,
    sagging power lines, bent lampposts, shipping containers, harbor + piers
Everything is vertex-colored per face (weathered, jittered shades) — no textures,
no flat single-color slabs (the game reads COLOR_0 straight into vertexColors). Node names drive the game's collider/material routing
(building_/destroyed_landmark_/rubble_/vehicle_/road_/sidewalk_/park_/terrain_/
waterfront_/pier_/water_/glass_/fire_/deco_ — deco/glass/fire are visual-only).

Run with your Blender:
  /home/aime/Downloads/blender-5.2.2-linux-x64/blender --background --python tools/build_realcity.py
Output: compound_game_kit/warzone_city.glb (world-space verts, Y-up via export_yup)
"""
import bpy, bmesh, math, random, os, sys

R = random.Random(20260929)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'compound_game_kit', 'warzone_city.glb')

def RND(a, b): return R.uniform(a, b)
def RI(a, b): return R.randint(a, b)

# ---------------------------------------------------------------- palette
def C(r, g, b): return (r, g, b)
CONC    = C(.62, .60, .55)   # concrete
CONC_D  = C(.50, .48, .44)
CONC_BR = C(.42, .40, .36)
PANEL_G = C(.56, .59, .53)   # khrushchyovka panel tints
PANEL_B = C(.45, .51, .55)
PANEL_S = C(.60, .57, .49)
BRICK_R = C(.47, .29, .21)
BRICK_O = C(.52, .40, .28)
PAINT_BLUE = C(.28, .40, .52)
PAINT_RED  = C(.52, .20, .16)
PAINT_GRN  = C(.38, .44, .32)
ROOF_TAR = C(.29, .28, .26)
RUST    = C(.45, .26, .14)
SOOT    = C(.12, .11, .10)
SOOT2   = C(.22, .20, .18)
GRASS   = C(.30, .36, .19)
GRASS_D = C(.23, .29, .15)
DIRT    = C(.44, .38, .28)
ASPH    = C(.195, .205, .225)
ASPH_D  = C(.16, .17, .19)
MARK_W  = C(.72, .71, .65)
MARK_Y  = C(.66, .56, .20)
LIMESTN = C(.66, .64, .58)   # Manhattan limestone / pre-war facades
GLASS_B = C(.22, .30, .38)   # blue-black curtain glass
CAB_Y   = C(.68, .53, .12)   # NYC yellow-cab ochre (burnt)
SCREEN_A = C(.30, .08, .24)  # dead neon magenta
SCREEN_B = C(.08, .26, .30)  # dead neon cyan
SCREEN_C = C(.30, .28, .06)  # dead amber
WATER_D = C(.055, .095, .115)
SAND    = C(.60, .54, .40)
WOOD_W  = C(.44, .33, .20)
GLASS_D = C(.10, .145, .165)
METAL   = C(.34, .35, .37)
DARK    = C(.09, .09, .10)
WHITE   = C(.78, .77, .74)
CANOPY  = C(.22, .30, .16)
CROSS_R = C(.62, .12, .10)
CONT_R  = C(.50, .22, .14)
CONT_B  = C(.16, .28, .38)
CONT_G  = C(.24, .36, .22)
TIRE    = C(.055, .055, .06)

def j(c, k=.05):
    return (max(0., min(1., c[0] + RND(-k, k))),
            max(0., min(1., c[1] + RND(-k, k))),
            max(0., min(1., c[2] + RND(-k, k))))

_gid = [0]
def nid(label):
    _gid[0] += 1
    return f"{label}_{_gid[0]:05d}"

# ---------------------------------------------------------------- part writer
# Game space: x east, y UP, z south.  Blender space: (x, -z, y) so the glTF
# exporter's +Y-up conversion lands the city exactly on game coordinates.
class Part:
    __slots__ = ('name', 'v', 'f', 'c')
    def __init__(self, name):
        self.name, self.v, self.f, self.c = nid(name), [], [], []

    def _gb(self, gx, gz, gy):  # game -> blender
        return (gx, -gz, gy)

    def quadB(self, a, b, c2, d, rgb):
        i = len(self.v)
        self.v += [a, b, c2, d]
        self.f += [(i, i + 1, i + 2), (i, i + 2, i + 3)]
        for _ in range(4):
            self.c.append(rgb)

    def quadg(self, A, B, C2, D, rgb):
        """game-space corners (x, z, y)"""
        self.quadB(*[self._gb(*p) for p in (A, B, C2, D)], rgb)

    def boxg(self, x0, x1, y0, y1, z0, z1, top=None, side=None, bot=None, jj=.05):
        top = top or side; side = side or top; bot = bot or top
        s1, s2, s3, s4 = j(side, jj), j(side, jj), j(side, jj), j(side, jj)
        self.quadg((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1), s1)  # +z
        self.quadg((x1, y0, z0), (x0, y0, z0), (x0, y1, z0), (x1, y1, z0), s2)  # -z
        self.quadg((x1, y0, z1), (x1, y0, z0), (x1, y1, z0), (x1, y1, z1), s3)  # +x
        self.quadg((x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0), s4)  # -x
        self.quadg((x0, y1, z1), (x1, y1, z1), (x1, y1, z0), (x0, y1, z0), j(top, jj))
        self.quadg((x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1), j(bot, jj))

    def beam(self, A, B, w, rgb, sq=.45):
        """box from game-point A to B (any direction) — rebar, cables, poles, tilted slabs"""
        a, b = self._gb(*A), self._gb(*B)
        d = [b[i] - a[i] for i in range(3)]
        L = math.sqrt(sum(x * x for x in d))
        if L < 1e-5: return
        d = [x / L for x in d]
        up = (0, 0, 1) if abs(d[2]) < .9 else (1, 0, 0)
        r = [d[1] * up[2] - d[2] * up[1], d[2] * up[0] - d[0] * up[2], d[0] * up[1] - d[1] * up[0]]
        rl = math.sqrt(sum(x * x for x in r)) or 1
        r = [x / rl * w / 2 for x in r]
        u = [d[1] * r[2] - d[2] * r[1], d[2] * r[0] - d[0] * r[2], d[0] * r[1] - d[1] * r[0]]
        ul = math.sqrt(sum(x * x for x in u)) or 1
        u = [x / ul * w / 2 * sq for x in u]
        P = []
        for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            for e in (a, b):
                P.append((e[0] + su * r[0] + sv * u[0], e[1] + su * r[1] + sv * u[1], e[2] + su * r[2] + sv * u[2]))
        A0, B0, C0, D0, A1, B1, C1, D1 = P
        col = j(rgb, .04)
        self.quadB(A0, B0, C0, D0, col); self.quadB(A1, D1, C1, B1, col)
        self.quadB(A0, A1, B1, B0, col); self.quadB(B0, B1, C1, C0, col)
        self.quadB(C0, C1, D1, D0, col); self.quadB(D0, D1, A1, A0, col)

    def cylg(self, cx, cz, y0, y1, r, rgb, n=12, cap=True):
        """vertical prism (game Y axis)"""
        rb, rt = [], []
        for i in range(n):
            a = 2 * math.pi * i / n
            rb.append(self._gb(cx + math.cos(a) * r, cz + math.sin(a) * r, y0))
            rt.append(self._gb(cx + math.cos(a) * r, cz + math.sin(a) * r, y1))
        for i in range(n):
            k = (i + 1) % n
            self.quadB(rb[i], rb[k], rt[k], rt[i], j(rgb, .04))
        if cap:
            cb = self._gb(cx, cz, y0); ct = self._gb(cx, cz, y1)
            for i in range(1, n - 1):
                self.quadB(cb, rb[i], rt[i], rt[i], j(rgb, .04))  # degenerate-safe cap quads
                self.f.pop(); self.f.pop(); [self.c.pop() for _ in range(4)]
                self.triB(cb, rb[i], rb[i + 1], j(rgb, .04))
                self.triB(ct, rt[i + 1], rt[i], j(rgb, .04))

    def triB(self, a, b, c2, rgb):
        i = len(self.v)
        self.v += [a, b, c2]
        self.f += [(i, i + 1, i + 2)]
        for _ in range(3):
            self.c.append(rgb)

PARTS = []
def emit_all():
    for p in PARTS:
        me = bpy.data.meshes.new(p.name)
        me.from_pydata(p.v, [], p.f)
        me.validate(verbose=False)
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bm.to_mesh(me); bm.free()
        try:
            ca = me.color_attributes.new(name="Col", type='BYTE_COLOR', domain='POINT')
        except Exception:
            ca = me.color_attributes.new(name="Col", type='FLOAT_COLOR', domain='POINT')
        for i, c in enumerate(p.c):
            ca.data[i].color = (c[0], c[1], c[2], 1.0)
        ob = bpy.data.objects.new(p.name, me)
        bpy.context.scene.collection.objects.link(ob)

def P(name):
    p = Part(name)
    PARTS.append(p)
    return p

# ================================================================ terrain & streets
def ground():
    p = P('terrain_ground')
    p.boxg(-140, 140, -0.35, 0.0, -130, 108, top=DIRT, side=CONC_BR)
    # gentle soil patches + grass spill so the base isn't one flat color
    for i in range(90):
        x, z = RND(-135, 135), RND(-125, 103)
        w, d = RND(3, 12), RND(3, 12)
        q = P('terrain_patch')
        q.boxg(x, x + w, -0.32, RND(-.06, .02), z, z + d, top=j(GRASS_D if R.random() < .55 else DIRT, .08), side=DIRT)

def road(x0, x1, z0, z1):
    p = P('road_asph')
    p.boxg(x0, x1, -0.1, 0.09, z0, z1, top=ASPH, side=ASPH_D)
    # patch stains
    for i in range(int((x1 - x0) * (z1 - z0) / 60) + 2):
        px, pz = RND(x0, x1 - 2), RND(z0, z1 - 2)
        q = P('road_stain')
        q.boxg(px, px + RND(1.2, 3.4), -0.1, 0.095, pz, pz + RND(1.2, 3.4), top=j(ASPH_D if R.random() < .6 else CONC_BR, .03))

def road_marks(x0, x1, z0, z1, horiz):
    """center dashes + edge lines"""
    if horiz:
        for u in range(int(x0), int(x1) - 3, 5):
            p = P('deco_mark'); p.boxg(u, u + 2.3, .09, .115, (z0 + z1) / 2 - .09, (z0 + z1) / 2 + .09, top=MARK_Y, side=MARK_Y)
        for z in (z0 + .5, z1 - .5):
            for u in range(int(x0), int(x1) - 3, 7):
                p = P('deco_mark'); p.boxg(u, u + 2.6, .09, .112, z - .07, z + .07, top=MARK_W, side=MARK_W)
    else:
        for v in range(int(z0), int(z1) - 3, 5):
            p = P('deco_mark'); p.boxg((x0 + x1) / 2 - .09, (x0 + x1) / 2 + .09, .09, .115, v, v + 2.3, top=MARK_Y, side=MARK_Y)
        for x in (x0 + .5, x1 - .5):
            for v in range(int(z0), int(z1) - 3, 7):
                p = P('deco_mark'); p.boxg(x - .07, x + .07, .09, .112, v, v + 2.6, top=MARK_W, side=MARK_W)

def crosswalk(x, z, horiz):
    for i in range(6):
        p = P('deco_zebra')
        if horiz: p.boxg(x - 3.2, x + 3.2, .09, .115, z - 3 + i * 1.05, z - 2.6 + i * 1.05, top=MARK_W, side=MARK_W)
        else:     p.boxg(x - 3 + i * 1.05, x - 2.6 + i * 1.05, .09, .115, z - 3.2, z + 3.2, top=MARK_W, side=MARK_W)

def sidewalk(x0, x1, z0, z1):
    p = P('sidewalk_walk')
    p.boxg(x0, x1, -0.1, 0.2, z0, z1, top=CONC_D, side=CONC_BR)
    for i in range(int(max(x1 - x0, z1 - z0) / 3)):  # expansion joints
        q = P('deco_joint')
        if x1 - x0 >= z1 - z0: q.boxg(x0 + i * 3, x0 + i * 3 + .04, .1, .2, z0, z1, top=CONC_BR, side=CONC_BR)
        else: q.boxg(x0, x1, .1, .2, z0 + i * 3, z0 + i * 3 + .04, top=CONC_BR, side=CONC_BR)

def crater(x, z, r=4):
    p = P('terrain_crater')
    p.boxg(x - r, x + r, -.45, .02, z - r, z + r, top=SOOT2, side=DIRT)
    for i in range(9):  # ejecta lips
        a = RND(0, 6.28)
        m = P('terrain_ejecta')
        m.beam((x + math.cos(a) * r, z + math.sin(a) * r, .05), (x + math.cos(a) * (r + RND(1.5, 3)), z + math.sin(a) * (r + RND(1.5, 3)), RND(.15, .45)), RND(1, 2.2), j(DIRT, .07), sq=1)
    q = P('deco_scorch')
    q.boxg(x - r * 1.5, x + r * 1.5, .021, .03, z - r * 1.5, z + r * 1.5, top=SOOT, side=SOOT)

# ================================================================ buildings
FLH = 3.2

def wall_with_windows(p, horiz, fixed, u0, u1, y0, y1, wallc, door_u=None, damage=0):
    """One wall side: piers + real window openings (sill+lintel), optional door bay."""
    L = u1 - u0
    n = max(1, round((L - 2.2) / 4.2))
    bay = (L - 1.2) / n
    win_w = min(2.0, bay - 1.4)
    h = y1 - y0
    sill_h, lin_h = .95, h - 2.45
    cur = u0 + .6
    for b in range(n):
        wu = u0 + .6 + b * bay + (bay - win_w) / 2
        # pier from cur to window start
        if wu - cur > .05:
            if horiz: p.boxg(cur, wu, y0, y1, fixed - .12, fixed + .12, side=j(wallc, .06))
            else:     p.boxg(fixed - .12, fixed + .12, y0, y1, cur, wu, side=j(wallc, .06))
        if door_u is not None and wu - 0.2 <= door_u <= wu + win_w + 0.2 and y0 < .1:
            # ground doorway: leave gap, deco lintel above
            if horiz: p.boxg(wu, wu + win_w, y0 + 2.35, y1, fixed - .12, fixed + .12, side=j(wallc, .06))
            else:     p.boxg(fixed - .12, fixed + .12, y0 + 2.35, y1, wu, wu + win_w, side=j(wallc, .06))
            q = P('deco_doorframe')
            if horiz: q.boxg(wu - .12, wu + win_w + .12, y0, y0 + 2.4, fixed - .16, fixed + .16, top=j(wallc, .04), side=j(SOOT2, .03))
            cur = wu + win_w
            continue
        # sill + lintel (real opening between)
        dmg = damage >= 1 and R.random() < .38
        if not dmg:
            if horiz: p.boxg(wu, wu + win_w, y0, y0 + sill_h, fixed - .12, fixed + .12, side=j(wallc, .07))
            else:     p.boxg(fixed - .12, fixed + .12, y0, y0 + sill_h, wu, wu + win_w, side=j(wallc, .07))
            if lin_h > .1:
                if horiz: p.boxg(wu, wu + win_w, y0 + h - lin_h, y1, fixed - .12, fixed + .12, side=j(wallc, .07))
                else:     p.boxg(fixed - .12, fixed + .12, y0 + h - lin_h, y1, wu, wu + win_w, side=j(wallc, .07))
            g = P('glass_win')
            if horiz: g.boxg(wu + .06, wu + win_w - .06, y0 + sill_h, y0 + h - lin_h, fixed - .05, fixed + .05, side=j(GLASS_D, .05))
            else:     g.boxg(fixed - .05, fixed + .05, y0 + sill_h, y0 + h - lin_h, wu + .06, wu + win_w - .06, side=j(GLASS_D, .05))
        else:  # blown out: jagged shards left
            if horiz: p.boxg(wu, wu + win_w, y0, y0 + RND(.2, .5), fixed - .12, fixed + .12, side=j(wallc, .08))
            else:     p.boxg(fixed - .12, fixed + .12, y0, y0 + RND(.2, .5), wu, wu + win_w, side=j(wallc, .08))
            if R.random() < .5:
                q = P('deco_shard')
                if horiz: q.boxg(wu, wu + win_w * RND(.3, .7), y0 + h - lin_h - RND(.2, .6), y0 + h - lin_h, fixed - .1, fixed + .1, side=j(wallc, .08))
        cur = wu + win_w
    if cur < u1 - .05:
        if horiz: p.boxg(cur, u1, y0, y1, fixed - .12, fixed + .12, side=j(wallc, .06))
        else:     p.boxg(fixed - .12, fixed + .12, y0, y1, cur, u1 - .6 + .6, side=j(wallc, .06))

def res_block(cx, cz, w, d, floors, style='panel', damage=0):
    """Enterable khrushchyovka: per-floor windows, interior slabs, dogleg stairs to roof."""
    x0, x1, z0, z1 = cx - w / 2, cx + w / 2, cz - d / 2, cz + d / 2
    base = {0: PANEL_G, 1: PANEL_B, 2: PANEL_S, 3: BRICK_R, 4: BRICK_O, 5: CONC_D}[style] if isinstance(style, int) else \
           {'panel': PANEL_G, 'blue': PANEL_B, 'sand': PANEL_S, 'brick': BRICK_R, 'brick2': BRICK_O, 'grey': CONC_D}[style]
    p = P('building_res')
    p.boxg(x0 - .3, x1 + .3, 0, .35, z0 - .3, z1 + .3, top=CONC_BR, side=CONC_BR)   # foundation
    sx0, sx1 = x0 + .5, x1 - 2.1   # stair core lane (west)
    hx0, hx1 = sx0, sx0 + 1.7
    hz0, hz1 = z0 + 1.0, z0 + 1.0 + 4.2
    hole = (hx0, hx1, hz0, hz1)
    for f in range(floors):
        y0, y1 = f * FLH, (f + 1) * FLH
        fc = j(base, .05)
        # tint shifts per floor (panel seams) + soot gradient on damaged blocks
        tint = (fc[0] * (1 - .06 * (f % 2)), fc[1] * (1 - .06 * (f % 2)), fc[2] * (1 - .05 * (f % 2)))
        if damage >= 2 and f >= floors - 2:
            tint = (tint[0] * .55, tint[1] * .52, tint[2] * .5)
        dmg = damage if f >= floors - (2 if damage >= 2 else 1) else (1 if damage == 1 else 0)
        wall_with_windows(p, True, z0, x0, x1, y0, y1, tint, damage=dmg)                       # north
        wall_with_windows(p, True, z1, x0, x1, y0, y1, tint, door_u=cx if f == 0 else None, damage=dmg)  # south + door
        wall_with_windows(p, False, x0, z0 + .6, z1 - .6, y0, y1, tint, damage=dmg)            # west
        wall_with_windows(p, False, x1, z0 + .6, z1 - .6, y0, y1, tint, damage=dmg)            # east
        # floor slabs (stair hole left open)
        slab_y = (f + 1) * FLH
        for i, (a0, a1, b0, b1) in enumerate([
                (x0 + .2, x1 - .2, z0 + .2, hole[2]),
                (x0 + .2, hole[0], hole[2], hole[3]),
                (hole[1], x1 - .2, hole[2], hole[3]),
                (x0 + .2, x1 - .2, hole[3], z1 - .2)]):
            if damage >= 2 and f == floors - 1 and i == RI(0, 3): continue  # blown slab
            p.boxg(a0, a1, slab_y - .22, slab_y, b0, b1, top=j(CONC_D, .05), side=CONC_BR, bot=CONC_BR)
        # dogleg stairs in the core (rise .49 pairs, run .56 — under the game's .56 step-up)
        dirn = 1 if f % 2 == 0 else -1
        steps = 13
        for i in range(0, steps, 2):
            yy = y0 + (i + 2) * FLH / steps
            za = hz0 + (i / steps) * 3.6 if dirn > 0 else hz1 - (i + 2) / steps * 3.6
            zb = za + 2 * 3.6 / steps
            p.boxg(hx0, hx1, yy - FLH / steps * 2, yy, za, zb, top=j(CONC_D, .04), side=CONC_BR)
        lz0, lz1 = (hz1 - 1.1, hz1) if dirn > 0 else (hz0, hz0 + 1.1)
        p.boxg(hx0, hx1, (f + 1) * FLH - .18, (f + 1) * FLH, lz0, lz1, top=CONC_D)
        # interior partitions + clutter (lower floors only)
        if f < 2:
            p.boxg(cx - .1, cx + .1, y0, y1 - .3, z0 + 2.2, z0 + 6.4, side=j(WHITE, .05))
            for k in range(3):
                p.boxg(RND(x0 + 2, x1 - 4), RND(x0 + 2, x1 - 4) + RND(.7, 1.4), y0, y0 + RND(.4, .9), RND(z0 + 2, z1 - 3), None or RND(z0 + 2, z1 - 3) + RND(.7, 1.4), top=j(WOOD_W if R.random() < .5 else CONC_BR, .06), side=CONC_BR)
        # balconies every other floor on the south face
        if f % 2 == 1:
            q = P('deco_balcony')
            q.boxg(cx - 1.6, cx + 1.6, y0 + .02, y0 + .14, z1 + .1, z1 + 1.1, top=j(CONC_D, .05), side=CONC_BR)
            q.boxg(cx - 1.6, cx + 1.6, y0 + .14, y0 + 1.1, z1 + 1.0, z1 + 1.08, side=j(METAL, .06))
            q.boxg(cx - 1.6, cx - 1.5, y0 + .14, y0 + 1.1, z1 + .1, z1 + 1.1, side=j(METAL, .06))
            q.boxg(cx + 1.5, cx + 1.6, y0 + .14, y0 + 1.1, z1 + .1, z1 + 1.1, side=j(METAL, .06))
    # roof
    ry = floors * FLH
    for (a0, a1, b0, b1) in [(x0 - .2, x1 + .2, z0 - .2, hole[2]), (x0 - .2, hole[0], hole[2], hole[3]),
                             (hole[1], x1 + .2, hole[2], hole[3]), (x0 - .2, x1 + .2, hole[3], z1 + .2)]:
        if damage >= 2 and R.random() < .4: continue
        p.boxg(a0, a1, ry, ry + .15, b0, b1, top=j(ROOF_TAR, .05), side=CONC_BR)
    for (a0, a1, b0, b1) in [(x0 - .2, x1 + .2, z0 - .2, z0 + .08), (x0 - .2, x1 + .2, z1 - .08, z1 + .2),
                             (x0 - .2, x0 + .08, z0 - .2, z1 + .2), (x1 - .08, x1 + .2, z0 - .2, z1 + .2)]:
        p.boxg(a0, a1, ry + .15, ry + .75, b0, b1, top=j(CONC_D, .05), side=j(tint if damage < 2 else SOOT2, .05))
    p.boxg(hx0 - .3, hx1 + .3, ry, ry + 2.3, hz0 - .3, hz1 + .3, top=j(ROOF_TAR, .04), side=j(CONC_D, .05))  # stair bulkhead
    if damage < 2:
        p.boxg(x1 - 3.4, x1 - 2.2, ry + .15, ry + 1.5, z0 + 1.5, z0 + 2.7, top=j(METAL, .06), side=j(RUST, .08))  # water tank
        q = P('deco_antenna'); q.beam((cx, cz, ry + .75), (cx + RND(-.6, .6), cz + RND(-.6, .6), ry + RND(3.4, 4.6)), .14, METAL)
    if damage >= 1:  # scorch the facade
        q = P('deco_sootfacade')
        q.boxg(x0 + RND(1, 4), x0 + RND(5, 8), .1, ry * RND(.35, .8), z1 + .13, z1 + .17, top=SOOT, side=SOOT)
    if damage >= 2:  # collapsed corner: rubble + rebar + tilted slab
        for i in range(6):
            m = P('rubble_pile')
            s = RND(.7, 2.2)
            bx, bz = x1 - RND(0, 5), z1 - RND(0, 5)
            m.boxg(bx, bx + s, 0, RND(.3, 1.6), bz, bz + s * RND(.6, 1.4), top=j(CONC_BR if R.random() < .6 else BRICK_R, .09), side=CONC_BR)
        for i in range(4):
            q = P('deco_rebar')
            q.beam((x1 - RND(0, 4), z1 - RND(0, 4), .2), (x1 + RND(-1, 2), z1 + RND(-1, 2), RND(1.5, 3.4)), .06, DARK, sq=.3)

def house(cx, cz, w=9.5, d=8.5, two=True, brick=True):
    x0, x1, z0, z1 = cx - w / 2, cx + w / 2, cz - d / 2, cz + d / 2
    wallc = BRICK_R if brick else j(PANEL_S, .04)
    p = P('building_house')
    p.boxg(x0 - .2, x1 + .2, 0, .3, z0 - .2, z1 + .2, top=CONC_BR, side=CONC_BR)
    fl = 2 if two else 1
    for f in range(fl):
        y0, y1 = f * 3.0, (f + 1) * 3.0
        wall_with_windows(p, True, z0, x0, x1, y0, y1, wallc, damage=1 if R.random() < .4 else 0)
        wall_with_windows(p, True, z1, x0, x1, y0, y1, wallc, door_u=cx if f == 0 else None)
        wall_with_windows(p, False, x0, z0, z1, y0, y1, wallc)
        wall_with_windows(p, False, x1, z0, z1, y0, y1, wallc)
        if f < fl - 1:
            p.boxg(x0 + .2, x1 - .2, y1 - .2, y1, z0 + .2, z0 + 3.4, top=CONC_D)   # slab (stair gap east)
            p.boxg(x0 + .2, x1 - .2, y1 - .2, y1, z0 + 6.2, z1 - .2, top=CONC_D)
            p.boxg(x0 + .2, x0 + 4.2, y1 - .2, y1, z0 + 3.4, z0 + 6.2, top=CONC_D)
        for i in range(4):  # interior stair to next floor / roof
            yy = y0 + (i + 1) * 3.0 / 4
            p.boxg(x1 - 2.4, x1 - .5, yy - .75 / 2, yy, z0 + .8 + i * .7, z0 + 1.5 + i * .7, top=j(WOOD_W, .06))
        if f:  # NY fire escape on the south face (deco, bent zaba rails)
            q = P('deco_fireescape')
            q.boxg(x1 - 3.2, x1 - .4, f * 3.0 + .02, f * 3.0 + .14, z1 + .1, z1 + 1.0, top=j(METAL, .07), side=j(RUST, .09))
            q.beam((x1 - 3.0, z1 + .95, f * 3.0), (x1 - 3.0, z1 + .95, f * 3.0 - 3), .05, j(METAL, .06), sq=.3)
            q.beam((x1 - .6, z1 + .95, f * 3.0), (x1 - .6, z1 + .95, f * 3.0 - 3), .05, j(METAL, .06), sq=.3)
    ry = fl * 3.0
    p.boxg(x0 - .2, x1 + .2, ry, ry + .15, z0 - .2, z1 + .2, top=j(ROOF_TAR, .05))  # flat roof
    # gable
    q = P('deco_gable')
    q.beam((x0 - .3, z1 / 1, ry), ((x0 + x1) / 2, z1 / 1, ry + 1.5), .3, j(ROOF_TAR, .05), sq=1)  # placeholder ridge ends
    for (zz, sgn) in ((z0, 1), (z1, -1)):
        r = P('deco_roofplate')
        r.beam((x0 - .35, zz, ry + .1), ((x0 + x1) / 2, zz + sgn * .0, ry + 1.7), .34, j(BRICK_R if brick else CONC_D, .06), sq=1)
    p.boxg(x1 - 2.6, x1 - 1.8, ry + .2, ry + 2.2, z0 + 1.2, z0 + 2.0, top=j(BRICK_R, .06), side=BRICK_R)  # chimney
    p.boxg(cx - 1.6, cx + 1.6, .05, .18, z1 + .6, z1 + 2.2, top=CONC_D)  # porch step

# ================================================================ landmarks
def destroyed_tower(cx, cz, w, d, stump, cc=CONC_BR, mast=False):
    """Collapsed high-rise: concrete core, broken slabs, rubble sea, rebar forest."""
    x0, x1, z0, z1 = cx - w / 2, cx + w / 2, cz - d / 2, cz + d / 2
    p = P('destroyed_landmark_tower')
    p.boxg(x0, x1, 0, stump * FLH * .9, z0, z1, top=j(cc, .08), side=j(j(cc, .75) if R.random() < .5 else SOOT2, .07))  # stump shell
    p.boxg(cx - 1.4, cx + 1.4, 0, stump * FLH * .9 + RND(6, 12), cz - 1.4, cz + 1.4, top=j(CONC_D, .05), side=j(CONC_BR, .06))  # core
    if mast:  # the antenna mast snapped at an angle (Empire State silhouette)
        q = P('destroyed_landmark_mast')
        q.beam((cx, cz, stump * FLH * .9 + 8), (cx + RND(1.5, 3.2), cz + RND(-2, 2), stump * FLH * .9 + RND(13, 17)), .55, j(METAL, .05), sq=.6)
    for f in range(stump):
        y = (f + 1) * FLH * .9
        for i in range(3):  # broken slab ledges
            a0 = x0 + RND(0, w * .4); a1 = a0 + RND(2, w * .45)
            b0 = z0 + RND(0, d * .5); b1 = b0 + RND(2, d * .4)
            if R.random() < .6:
                q = P('destroyed_landmark_slab')
                q.boxg(a0, a1, y - .2, y, b0, b1, top=j(CONC_BR, .07), side=SOOT2)
        if R.random() < .7:  # hanging slab chunk
            q = P('destroyed_landmark_hang')
            q.beam((RND(x0, x1), RND(z0, z1), y + .1), (RND(x0, x1), RND(z0, z1), y + RND(.8, 2)), RND(1.5, 3), j(CONC_BR, .08), sq=.8)
    for i in range(10):  # rebar forest on top
        q = P('deco_rebar')
        q.beam((RND(x0, x1), RND(z0, z1), stump * FLH * .9), (RND(x0, x1), RND(z0, z1), stump * FLH * .9 + RND(1, 3.6)), .05, DARK, sq=.25)
    for i in range(14):  # rubble sea around
        m = P('rubble_pile')
        s = RND(1, 3.4)
        bx, bz = cx + RND(-w, w) * .8, cz + RND(-d, d) * .8
        m.boxg(bx, bx + s, 0, RND(.3, 2.2), bz, bz + s, top=j(CONC_BR if R.random() < .55 else BRICK_O if R.random() < .5 else SOOT2, .1), side=CONC_BR)
    for i in range(3):
        q = P('deco_sootfacade')
        q.boxg(x0 + RND(0, w - 4), x0 + RND(4, w), 0, stump * FLH * .9 * RND(.5, 1), z1 + .13, z1 + .17, top=SOOT, side=SOOT)

def leaning_tower(cx, cz, w, d, floors):
    """Half-destroyed tower leaning as it rises (sheared floors)."""
    x0, z0 = cx - w / 2, cz - d / 2
    p = P('destroyed_landmark_leaning')
    for f in range(floors):
        y0, y1 = f * FLH * .95, (f + 1) * FLH * .95
        ox = f * .55  # shear east
        p.boxg(x0 + ox, x0 + ox + w, y0, y1, z0, z0 + d, top=j(CONC_BR if f % 2 else SOOT2, .07), side=j(CONC_D if f % 3 else SOOT2, .07))
        # broken edge on one side
        if R.random() < .7:
            q = P('destroyed_landmark_slab')
            q.boxg(x0 + ox + RND(0, w - 4), x0 + ox + RND(4, w), y1, y1 + .18, z0 + RND(0, d - 3), z0 + RND(3, d), top=j(CONC_BR, .07))
    ry = floors * FLH * .95
    for i in range(8):
        q = P('deco_rebar')
        q.beam((x0 + RND(0, w), z0 + RND(0, d), ry), (x0 + RND(0, w), z0 + RND(0, d), ry + RND(1, 3)), .05, DARK, sq=.25)

def fissure(cx, cz, rx, rz):
    """Torn ground: dark pit (walkable bed), tilted slabs, embers, rubble ramp out."""
    p = P('water_fissure')
    p.boxg(cx - rx, cx + rx, -2.4, -1.6, cz - rz, cz + rz, top=SOOT, side=SOOT2)  # bed
    p.boxg(cx - rx - .8, cx + rx + .8, -.6, .04, cz - rz - .8, cz + rz + .8, top=SOOT2, side=DIRT)  # torn rim
    for i in range(7):
        q = P('destroyed_landmark_edge')
        q.beam((cx + RND(-rx, rx), cz + RND(-rz, rz), -1.5), (cx + RND(-rx, rx) * 1.4, cz + RND(-rz, rz) * 1.4, RND(.4, 2.6)), RND(1, 2.6), j(CONC_BR, .09), sq=.9)
    for i in range(5):
        q = P('fire_ember')
        q.boxg(cx + RND(-rx, rx) - .4, cx + RND(-rx, rx) + .4, -1.58, -1.55, cz + RND(-rz, rz) - .4, cz + RND(-rz, rz) + .4, top=CROSS_R, side=CROSS_R)
    for i in range(2):  # rubble ramps to climb out
        for s in range(4):
            m = P('rubble_ramp')
            m.boxg(cx - rx + 1 + s * 1.1, cx - rx + 2.1 + s * 1.1, -1.6 + s * .42, -.6 + s * .42, cz + rz * (s - 1.5) * .3, cz + rz * (s - 1.5) * .3 + 1.4, top=j(CONC_BR, .08))

def times_square(cx, cz):
    """Burned-out Times Square corner: billboard pylons with dead neon screens."""
    for i, off in enumerate((-8.5, 0, 8.5)):
        bx = cx + off
        h = RND(8, 12)
        p = P('building_ts_pylon')
        p.boxg(bx - 1.1, bx + 1.1, 0, h, cz - .7, cz + .7, top=j(SOOT2, .05), side=j(CONC_D, .06))
        q = P('deco_screen')
        nf = max(1, int(h / 4))
        for f in range(nf):
            sc = [SCREEN_A, SCREEN_B, SCREEN_C][RI(0, 2)]
            if R.random() < .45: sc = j(SOOT, .03)  # some screens burnt to black
            q.boxg(bx - 1.35, bx + 1.35, f * 4 + .4, f * 4 + 3.1, cz - .95, cz - .88, top=j(sc, .1), side=METAL)
        if R.random() < .6:  # one fallen slab of neon glass below
            r = P('rubble_pile')
            r.boxg(bx - 1.2, bx + RND(.5, 1.6), 0, RND(.2, .6), cz + .8, cz + RND(2, 3.4), top=j([SCREEN_A, SCREEN_B, SCREEN_C][RI(0, 2)], .12), side=SOOT2)
    for i in range(4):  # ticker scaffolds between pylons
        q = P('deco_scaffold')
        a = cx - 10.5 + i * 7
        q.boxg(a - .5, a + .5, 4.2, 4.5, cz + .8, cz + 1.2, top=j(METAL, .06), side=METAL)

def subway_entrance(x, z, horiz=True):
    """NYC subway entrance: green railings + a dark stair head going down (deco, walk-through)."""
    p = P('deco_subway')
    L, Wd = (4.6, 2.2) if horiz else (2.2, 4.6)
    x0, x1, z0, z1 = x - L / 2, x + L / 2, z - Wd / 2, z + Wd / 2
    p.boxg(x0, x1, .0, .12, z0, z1, top=j(SOOT, .04), side=SOOT2)              # stair head
    g = PAINT_GRN
    for (a0, a1, b0, b1) in [(x0, x0 + .1, z0, z1), (x1 - .1, x1, z0, z1),
                             (x0, x1, z0, z0 + .1), (x0, x1, z1 - .1, z1)]:
        p.beam(((a0 + a1) / 2, (b0 + b1) / 2, 0), ((a0 + a1) / 2, (b0 + b1) / 2, 1.05), .08, j(g, .07), sq=.5)
    q = P('deco_subwaysign')
    q.boxg(x - .5, x + .5, 1.05, 1.55, z - .5, z - .42, top=j(g, .05), side=g)  # station lamp box

def steam_vent(x, z):
    """Junction steam grate — a warm ember patch the engine's fire pass will glow."""
    q = P('deco_steam')
    q.boxg(x - 1.1, x + 1.1, .02, .1, z - 1.1, z + 1.1, top=j(SOOT2, .04), side=SOOT)
    r = P('fire_ember')
    r.boxg(x - .8, x + .8, .1, .13, z - .8, z + .8, top=j(CROSS_R, .16), side=CROSS_R)

def broadway():
    """The famous diagonal cutting across the Manhattan grid (walks the_plaza's east flank)."""
    A, B = (2, 96), (72, -96)
    p = P('road_broadway')
    dx, dz = B[0] - A[0], B[1] - A[1]
    L = math.hypot(dx, dz)
    nx, ny = -dz / L, dx / L
    for sgn, rgb in ((0, j(ASPH, .04)),):
        w = 7.0
        p.quadg((A[0] + nx * w / 2, A[1] + ny * w / 2, .1), (B[0] + nx * w / 2, B[1] + ny * w / 2, .1),
                (B[0] - nx * w / 2, B[1] - ny * w / 2, .1), (A[0] - nx * w / 2, A[1] - ny * w / 2, .1), rgb)
    for i in range(38):  # center dashes down the diagonal
        t = (i + .5) / 38
        mx2, mz2 = A[0] + dx * t, A[1] + dz * t
        q = P('deco_mark')
        q.quadg((mx2 - nx * .12, mz2 - ny * .12, .115), (mx2 + nx * .12, mz2 + ny * .12, .115),
                (mx2 + 1.3 / L * dx - nx * .12, mz2 + 1.3 / L * dz - ny * .12, .115),
                (mx2 + 1.3 / L * dx + nx * .12, mz2 + 1.3 / L * dz + ny * .12, .115), j(MARK_Y, .05))
    for i in range(6):  # sidewalk ramps/stain along the cut
        t = RND(.1, .9)
        q = P('road_stain')
        q.quadg((A[0] + dx * t - nx * 4.4, A[1] + dz * t - ny * 4.4, .105),
                (A[0] + dx * t + dx / L * RND(1, 3) - nx * 4.4, A[1] + dz * t + dz / L * RND(1, 3) - ny * 4.4, .105),
                (A[0] + dx * t + dx / L * RND(1, 3) + nx * 4.4, A[1] + dz * t + dz / L * RND(1, 3) + ny * 4.4, .105),
                (A[0] + dx * t + nx * 4.4, A[1] + dz * t + ny * 4.4, .105), j(ASPH_D, .05))

def scaffold_row(x, z, w=8, along_x=True):
    """Sidewalk scaffolding shed against a facade (deco; the game treats deco as visual-only)."""
    p = P('deco_scaffold')
    depths = ((0, 2.1),) if along_x else ((0, 2.1),)
    legs = [(-w / 2, .2), (w / 2, .2), (-w / 2, 2.1), (w / 2, 2.1)]
    for (lx, lz) in legs:
        p.beam((x + lx, z + lz, 0), (x + lx, z + lz, 6.4), .16, j(RUST, .07), sq=.5)
    for yy in (3.1, 6.1):
        p.boxg(x - w / 2, x + w / 2, yy, yy + .12, z + .1, z + 2.2, top=j(WOOD_W, .07), side=j(WOOD_W, .09))

def stadium(cx, cz):
    rx, rz = 27, 21
    p = P('building_stadium')
    for i in range(26):  # oval outer stands
        a = 2 * math.pi * i / 26
        if i in (5, 6, 18, 19): continue  # entry corridors
        bx, bz = cx + math.cos(a) * (rx + 3), cz + math.sin(a) * (rz + 3)
        p.boxg(bx - 2.2, bx + 2.2, 0, RND(8, 9.5), bz - 2.2, bz + 2.2, top=j(CONC_D, .06), side=j(CONC_BR if i % 2 else SOOT2, .07))
        for s in range(5):  # raked rows
            rr = 1 - s * .16
            p.boxg(cx + math.cos(a) * rx * rr - 1.6, cx + math.cos(a) * rx * rr + 1.6, s * 1.15, s * 1.15 + 1.15,
                   cz + math.sin(a) * rz * rr - 1.6, cz + math.sin(a) * rz * rr + 1.6, top=j(CONC_D, .05))
    q = P('terrain_pitch')
    q.boxg(cx - rx + 4, cx + rx - 4, .02, .12, cz - rz + 4, cz + rz - 4, top=j(GRASS_D, .06), side=DIRT)
    m = P('deco_centercircle')
    m.cylg(cx, cz, .12, .14, 5, MARK_W, n=14)
    for i in range(4):  # collapsed roof section + pylons
        a = RND(0, 6.28)
        p.boxg(cx + math.cos(a) * (rx + 2), cx + math.cos(a) * (rx + 2) + 1.6, 9.5, 12.5, cz + math.sin(a) * (rz + 2), cz + math.sin(a) * (rz + 2) + 1.6, top=j(METAL, .08), side=SOOT2)
    for sx in (-1, 1):
        l = P('deco_floodlight')
        l.beam((cx + sx * (rx + 5), cz, 0), (cx + sx * (rx + 5), cz, 16), .5, METAL)
        l.boxg(cx + sx * (rx + 5) - 1.6, cx + sx * (rx + 5) + 1.6, 16, 17.4, cz - 1.6, cz + 1.6, top=j(MARK_W, .04), side=METAL)
    for i in range(8):  # collapsed stands rubble
        m = P('rubble_pile')
        s = RND(1, 2.6)
        m.boxg(cx + RND(-rx, rx) - s, cx + RND(-rx, rx), 0, RND(.4, 1.8), cz + RND(-rz, rz), cz + RND(-rz, rz) + s, top=j(CONC_BR, .09))

def hospital(cx, cz):
    w, d, fls = 20, 13, 4
    x0, x1, z0, z1 = cx - w / 2, cx + w / 2, cz - d / 2, cz + d / 2
    p = P('building_hospital')
    p.boxg(x0 - .3, x1 + .3, 0, .35, z0 - .3, z1 + .3, top=CONC_D, side=CONC_BR)
    for f in range(fls):
        y0, y1 = f * 3.3, (f + 1) * 3.3
        wall_with_windows(p, True, z0, x0, x1, y0, y1, WHITE)
        wall_with_windows(p, True, z1, x0, x1, y0, y1, WHITE, door_u=cx if f == 0 else None)
        wall_with_windows(p, False, x0, z0, z1, y0, y1, WHITE)
        wall_with_windows(p, False, x1, z0, z1, y0, y1, WHITE)
        if f: p.boxg(x0 + .3, x1 - .3, y0, y0 + .2, z0 + .3, z1 - .3, top=j(PALE if False else CONC_D, .04))
    ry = fls * 3.3
    p.boxg(x0 - .2, x1 + .2, ry, ry + .18, z0 - .2, z1 + .2, top=j(CONC_D, .04))
    q = P('deco_cross')  # red cross on the facade
    q.boxg(cx - .5, cx + .5, ry - 2.6, ry - .6, z0 - .16, z0 - .12, top=CROSS_R, side=CROSS_R)
    q.boxg(cx - 1.4, cx + 1.4, ry - 1.9, ry - 1.3, z0 - .16, z0 - .12, top=CROSS_R, side=CROSS_R)
    p.boxg(cx - 3, cx + 3, 0, .25, z1 + 1.2, z1 + 4.2, top=CONC_D)  # entrance canopy
    q = P('deco_helipad')
    q.cylg(cx, cz, ry + .18, ry + .3, 4.4, CONC_BR, n=14)
    q.boxg(cx - 1.6, cx + 1.6, ry + .3, ry + .34, cz - .25, cz + .25, top=MARK_W, side=MARK_W)
    q.boxg(cx - .25, cx + .25, ry + .3, ry + .34, cz - 1.6, cz + 1.6, top=MARK_W, side=MARK_W)

def police(cx, cz):
    w, d, fls = 15, 11, 3
    x0, x1, z0, z1 = cx - w / 2, cx + w / 2, cz - d / 2, cz + d / 2
    p = P('building_police')
    p.boxg(x0 - .3, x1 + .3, 0, .35, z0 - .3, z1 + .3, top=CONC_D, side=CONC_BR)
    for f in range(fls):
        y0, y1 = f * 3.2, (f + 1) * 3.2
        wall_with_windows(p, True, z0, x0, x1, y0, y1, PANEL_S)
        wall_with_windows(p, True, z1, x0, x1, y0, y1, PANEL_S, door_u=cx if f == 0 else None)
        wall_with_windows(p, False, x0, z0, z1, y0, y1, PANEL_S)
        wall_with_windows(p, False, x1, z0, z1, y0, y1, PANEL_S)
        if f:
            p.boxg(x0 + .3, x1 - .3, y0, y0 + .2, z0 + .3, z1 - .3, top=CONC_D)
        q = P('deco_trim')  # blue band per floor
        q.boxg(x0 - .05, x1 + .05, y1 - .3, y1 - .12, z0 - .16, z0 - .12, top=PAINT_BLUE, side=PAINT_BLUE)
    ry = fls * 3.2
    p.boxg(x0 - .2, x1 + .2, ry, ry + .18, z0 - .2, z1 + .2, top=j(CONC_D, .04))
    q = P('deco_siren')
    q.boxg(cx - .8, cx + .8, ry + .18, ry + .8, z0 + 2, z0 + 2.6, top=PAINT_BLUE, side=PAINT_BLUE)
    p.boxg(x1 + .1, x1 + 5.5, 0, 2.2, z0 - 1, z0 + 8, top=j(CONC_BR, .06), side=CONC_BR)  # yard wall
    for i in range(3):  # barred holding windows
        q = P('deco_bars')
        q.boxg(x1 - .2, x1 - .1, 1.0, 2.4, z0 + 1.5 + i * 3, z0 + 2.9 + i * 3, top=DARK, side=DARK)

# ================================================================ industry & harbor
def warehouse(cx, cz, w=24, d=14):
    x0, x1, z0, z1 = cx - w / 2, cx + w / 2, cz - d / 2, cz + d / 2
    p = P('building_warehouse')
    p.boxg(x0 - .2, x1 + .2, 0, .3, z0 - .2, z1 + .2, top=CONC_BR, side=CONC_BR)
    gate = (x0 + x1) / 2
    p.boxg(x0, gate - 3, 0, 6.2, z1 - .15, z1 + .15, side=j(METAL, .06))         # front with gate gap
    p.boxg(gate + 3, x1, 0, 6.2, z1 - .15, z1 + .15, side=j(METAL, .06))
    p.boxg(x0, x1, 0, 6.2, z0 - .15, z0 + .15, side=j(RUST if R.random() < .4 else METAL, .07))
    p.boxg(x0 - .15, x0 + .15, 0, 6.2, z0, z1, side=j(METAL, .06))
    p.boxg(x1 - .15, x1 + .15, 0, 6.2, z0, z1, side=j(METAL, .06))
    p.boxg(x0 - .3, x1 + .3, 6.2, 6.5, z0 - .3, z1 + .3, top=j(RUST, .07), side=METAL)  # roof
    for i in range(5):  # skylight strips
        q = P('glass_skylight')
        q.boxg(x0 + 2 + i * 4.4, x0 + 4.4 + i * 4.4, 6.5, 6.55, cz - 1, cz + 1, top=GLASS_D, side=GLASS_D)
    for i in range(7):  # crates & shelving inside
        s = RND(.8, 1.6)
        p.boxg(RND(x0 + 2, x1 - 3), RND(x0 + 2, x1 - 3) + s, 0, s, RND(z0 + 2, z1 - 3), RND(z0 + 2, z1 - 3) + s, top=j(WOOD_W if R.random() < .6 else CONT_G, .07))
    q = P('deco_pipe')
    q.beam((x0 + .3, z0 + 1, 5.2), (x1 - .3, z0 + 1, 5.2), .3, j(RUST, .06))

def silo(cx, cz, r=2.3, h=10):
    p = P('building_silo')
    p.cylg(cx, cz, 0, h, r, j(PANEL_S, .05), n=12)
    p.cylg(cx, cz, h, h + .8, r * 1.08, j(RUST, .06), n=12)
    q = P('deco_ladder')
    q.beam((cx + r + .1, cz, 0), (cx + r + .1, cz, h), .3, DARK, sq=.2)

def chimney(cx, cz, h=19):
    p = P('building_chimney')
    p.cylg(cx, cz, 0, h, 1.15, j(BRICK_O, .05), n=10)
    q = P('deco_sootfacade')
    q.cylg(cx, cz, h - 3, h, 1.16, SOOT, n=10)

def container(cx, cz, ry=0):
    p = P('building_container')
    cc = [CONT_R, CONT_B, CONT_G, RUST][RI(0, 3)]
    p.boxg(cx - 3, cx + 3, 0, 2.5, cz - 1.25, cz + 1.25, top=j(cc, .05), side=j(cc, .08))

def harbor():
    # quay walls + water bed (client pushes the swim zone z -95..-58)
    p = P('waterfront_quay')
    p.boxg(-130, 130, -2.8, 1.1, -58.5, -52.5, top=j(CONC_D, .05), side=CONC_BR)
    p.boxg(-130, 130, -2.8, -2.4, -95.5, -58.5, top=WATER_D, side=WATER_D)  # bed
    for px in (-120, -100, 120):  # bollards
        q = P('deco_bollard')
        q.cylg(px, -55.5, 1.1, 1.7, .28, DARK, n=8)
    for cxp in (-60, 60):  # piers
        q = P('pier_deck')
        for i in range(14):
            q.boxg(cxp - 1.6, cxp + 1.6, 1.05, 1.25, -58 - i * 2.2, -56.2 - i * 2.2, top=j(WOOD_W, .07), side=WOOD_W)
        for i in range(7):
            for sx in (-1.4, 1.4):
                q.boxg(cxp + sx - .18, cxp + sx + .18, -2.6, 1.3, -57.5 - i * 4.6, -57.1 - i * 4.6, top=WOOD_W, side=WOOD_W)
    # destroyed center pier
    q = P('pier_broken')
    for i in range(4):
        q.boxg(-3 + RND(-1, 1), 1 + RND(-1, 1), 1.0 + RND(-.6, .2), 1.25, -58 - i * 2.4, -56.4 - i * 2.4, top=j(WOOD_W, .1), side=WOOD_W)
    # crane
    c = P('building_crane')
    c.boxg(28, 30.4, 0, 1.2, -56.5, -54.1, top=CONC_BR, side=CONC_BR)
    c.boxg(28.6, 29.8, 1.2, 13, -55.8, -54.6, top=j(METAL, .06), side=j(PAINT_RED, .07))
    j2 = P('deco_jib')
    j2.beam((29.2, -55.2, 12.6), (29.2, -55.2 + 17, 12.2), .5, j(PAINT_RED, .06), sq=.5)
    j2.beam((29.2, -55.2, 12.6), (29.2, -55.2 - 5, 12.4), .5, j(PAINT_RED, .06), sq=.5)
    j2.beam((29.2, -60, 12.3), (29.2, -66, 4.2), .06, DARK, sq=.2)  # hook cable
    # barge, beached + listing
    b = P('vehicle_barge')
    b.boxg(-38, -24, -1.4, .9, -72, -66, top=j(RUST, .07), side=j(RUST, .08))
    b.boxg(-38, -30, -2.2, .4, -72, -66, top=j(RUST, .07), side=SOOT2)  # sunk stern
    b.boxg(-34, -29, .9, 2.6, -70.5, -67.5, top=j(SOOT2, .05), side=RUST)  # wheelhouse
    for cx2 in (80, 86, 92, 80, 86):  # container yard
        container(cx2, -62 + (8 if cx2 < 84 else 0) * RI(0, 1))

def tv_tower(cx, cz):
    p = P('destroyed_landmark_tvtower')  # collapsed broadcast mast, half the spire sheared off
    p.cylg(cx, cz, 0, 30, 2.0, j(CONC_D, .04), n=10)
    p.cylg(cx, cz, 30, 33, 4.4, j(PANEL_B, .05), n=10)   # observation ring
    q = P('glass_tv')
    q.cylg(cx, cz, 31, 32.6, 4.45, GLASS_D, n=10)
    p.cylg(cx, cz, 33, 44, 1.0, j(CONC_D, .04), n=8)
    q = P('deco_mastfall')  # the fallen spire section, bent across the harbor edge
    q.beam((cx + 3, cz - 2, 44), (cx + 16, cz + 9, .8), .8, j(METAL, .07), sq=.55)
    for i in range(4):  # guy wires
        a = 2 * math.pi * i / 4 + .4
        q = P('deco_guy')
        q.beam((cx, cz, 22), (cx + math.cos(a) * 14, cz + math.sin(a) * 14, .3), .04, DARK, sq=.15)
    for sx, sz in ((-6, -6), (6, -6), (-6, 6), (6, 6)):  # leg braces at base
        q = P('building_tvleg')
        q.beam((cx + sx * .6, cz + sz * .6, 0), (cx + sx * 5, cz + sz * 5, 7), .5, j(METAL, .06), sq=.6)
        q.beam((cx + sx * 5, cz + sz * 5, 7), (cx + sx * .9, cz + sz * .9, 12), .4, j(METAL, .06), sq=.6)

# ================================================================ war dressing
def burnt_car(x, z, kind=0):
    p = P('vehicle_hulk')
    L, W = (4.6, 1.85) if kind == 0 else (5.2, 2.0) if kind == 1 else (10.5, 2.5) if kind == 2 else (4.7, 1.9)
    h = 1.05 if kind != 2 else 2.2
    col = j(CAB_Y, .09) if kind == 3 else j(SOOT if R.random() < .6 else RUST, .08)
    p.boxg(x - L / 2, x + L / 2, .25, .25 + h * .55, z - W / 2, z + W / 2, top=j(SOOT, .07), side=col)
    p.boxg(x - L * .18, x + L * .22, .25 + h * .55, .35 + h, z - W * .42, z + W * .42, top=j(GLASS_D if R.random() < .5 else SOOT, .06), side=j(SOOT2, .06))
    for (wx, wz) in ((L * .32, W * .45), (L * .32, -W * .45), (-L * .32, W * .45), (-L * .32, -W * .45)):
        p.boxg(x + wx - .32, x + wx + .32, 0, .5, z + wz - .12, z + wz + .12, top=TIRE, side=TIRE)
    if kind == 3:  # yellow cab: checker band + bent TAXI roof sign
        q = P('deco_cabband')
        q.boxg(x - L * .42, x + L * .42, .25 + h * .42, .25 + h * .42 + .12, z - W / 2, z - W / 2 + .06, top=j(WHITE, .08), side=WHITE)
        q.boxg(x - L * .42, x + L * .42, .25 + h * .42, .25 + h * .42 + .12, z + W / 2 - .06, z + W / 2, top=j(WHITE, .08), side=WHITE)
        t = P('deco_taxisign')
        t.boxg(x - .45, x + .45, .25 + h, .25 + h + .5, z - .2, z + .2, top=j(CAB_Y, .1), side=j(SOOT2, .06))
        t.beam((x + .2, z, .25 + h + .5), (x + .9, z + .2, .25 + h + .1), .06, METAL, sq=.4)  # bent
    q = P('deco_hood')
    q.beam((x + L * .42, z, .25 + h * .55), (x + L * .42 + RND(.4, 1), z + RND(-.3, .3), .25 + h * .55 + RND(.5, 1.1)), 1.5, j(RUST, .08), sq=.6)
    q = P('deco_scorch')
    q.boxg(x - L, x + L, .021, .03, z - W - .6, z + W + .6, top=SOOT, side=SOOT)

def tank_wreck(x, z, ang=0):
    p = P('vehicle_tank')
    c = j(j(METAL, .05), .0)
    p.boxg(x - 3.2, x + 3.2, .3, 1.35, z - 1.25, z + 1.25, top=j(SOOT2, .06), side=j(SOOT2 if R.random() < .5 else PAINT_GRN, .07))
    p.boxg(x - 3.3, x + 3.3, .1, .55, z - 1.5, z - 1.15, top=TIRE, side=DARK)
    p.boxg(x - 3.3, x + 3.3, .1, .55, z + 1.15, z + 1.5, top=TIRE, side=DARK)
    p.cylg(x - .5, z, 1.35, 2.0, 1.1, j(PAINT_GRN, .06), n=10)
    q = P('deco_gun')
    q.beam((x - .5, z, 1.7), (x - .5 - 4.2 * math.cos(ang), z + 4.2 * math.sin(ang) - 3.4, 1.9), .22, DARK, sq=.5)

def hedgehog(x, z):
    p = P('building_hedgehog')
    s = RND(.85, 1.25)
    for (a, b) in (((x - s, z - s, .1), (x + s, z + s, s * 1.2)),
                   ((x - s, z + s, .1), (x + s, z - s, s * 1.2)),
                   ((x, z - s, .05), (x, z + s, s * 1.2))):
        p.beam(a, b, .16, j(METAL, .07), sq=.4)

def sandbags(x, z, w, horiz=True):
    p = P('building_sandbags')
    for r in range(2):
        n = int(w / .75)
        for i in range(n):
            bx = x + (i * .75 if horiz else 0) + RND(-.05, .05)
            bz = z + (0 if horiz else i * .75) + RND(-.05, .05)
            p.boxg(bx - .38, bx + .38, r * .48, .48 + r * .48, bz - .26, bz + .26, top=j(SAND, .07), side=j(SAND, .09))

def jersey(x, z, horiz=True):
    p = P('building_jersey')
    for i in range(3):
        bx = x + i * 2.1 if horiz else x
        bz = z if horiz else z + i * 2.1
        if horiz: p.boxg(bx, bx + 2, .0, .8, bz - .3, bz + .3, top=j(CONC_D, .06), side=j(CONC_BR, .06))
        else:     p.boxg(bx - .3, bx + .3, .0, .8, bz, bz + 2, top=j(CONC_D, .06), side=j(CONC_BR, .06))

def rubble_pile(x, z, big=False):
    p = P('rubble_pile')
    for i in range(RI(4, 7 if big else 5)):
        s = RND(.5, 2.4 if big else 1.4)
        bx, bz = x + RND(-1.6, 1.6), z + RND(-1.6, 1.6)
        cc = CONC_BR if R.random() < .55 else (BRICK_O if R.random() < .5 else SOOT2)
        p.boxg(bx, bx + s, 0, RND(.25, 1.6 if big else .9), bz, bz + s * RND(.6, 1.3), top=j(cc, .1), side=cc)
    if R.random() < .6:
        q = P('deco_rebar')
        q.beam((x, z, .1), (x + RND(-1, 1), z + RND(-1, 1), RND(1, 2.6)), .05, DARK, sq=.3)

def powerline(x, z, lean=False):
    p = P('building_powerpole')
    top = 8.3 if not lean else 7.2
    p.boxg(x - .14, x + .14, 0, top, z - .14, z + .14, top=j(WOOD_W, .06), side=j(WOOD_W, .08))
    p.boxg(x - 1.3, x + 1.3, top - .5, top - .3, z - .1, z + .1, side=WOOD_W)
    if lean:
        q = P('deco_polelean')
        q.beam((x, z, top - 2), (x + RND(1, 2.4), z + RND(-1, 1), top - RND(.6, 1.6)), .18, WOOD_W)

def lamppost(x, z, bent=False):
    p = P('deco_lamp')
    if bent:
        p.beam((x, z, 0), (x + RND(.8, 1.8), z + RND(-.5, .5), RND(3.4, 4.6)), .14, METAL)
    else:
        p.boxg(x - .08, x + .08, 0, 5.4, z - .08, z + .08, side=METAL)
        p.boxg(x, x + 1.3, 5.3, 5.44, z - .07, z + .07, side=METAL)
        p.boxg(x + 1.1, x + 1.5, 5.1, 5.34, z - .12, z + .12, top=j(MARK_W, .05), side=METAL)

def tree(x, z, dead=None):
    dead = R.random() < .45 if dead is None else dead
    p = P('building_treetrunk')
    h = RND(3.4, 6)
    p.beam((x, z, 0), (x + RND(-.3, .3), z + RND(-.3, .3), h), RND(.3, .5), j(WOOD_W, .07), sq=.6)
    if dead:
        q = P('deco_branch')
        for i in range(3):
            q.beam((x, z, h * RND(.5, .95)), (x + RND(-1.6, 1.6), z + RND(-1.6, 1.6), h + RND(-.4, 1.2)), .1, WOOD_W, sq=.4)
    else:
        q = P('deco_canopy')
        for i in range(3):
            s = RND(1.6, 2.8)
            q.boxg(x - s / 2, x + s / 2, h * (.55 + i * .18), h * (.55 + i * .18) + RND(.5, 1), z - s / 2, z + s / 2, top=j(CANOPY, .08), side=CANOPY)

def fire_site(x, z):
    p = P('fire_burn')
    p.boxg(x - 2.4, x + 2.4, .021, .035, z - 2.4, z + 2.4, top=SOOT, side=SOOT)
    for i in range(4):
        q = P('fire_ember')
        q.boxg(x + RND(-2, 2) - .3, x + RND(-2, 2) + .3, .035, .09, z + RND(-2, 2) - .3, z + RND(-2, 2) + .3, top=j(CROSS_R, .12), side=CROSS_R)

# ================================================================ assemble the city
def streets():
    AV = [-108, -72, -36, 0, 36, 72, 108]
    ST = [96, 60, 24, -12, -48]
    for x in AV:
        z0, z1 = (-96, 96) if x in (-36, 0, 36) else (-52, 96)
        road(x - 3.5, x + 3.5, z0, z1)
        road_marks(x - 3.5, x + 3.5, z0, z1, False)
        if z0 < -50: road(x - 3.5, x + 3.5, -96, -58.5)
    for z in ST:
        road(-122, 122, z - 3.5, z + 3.5)
        road_marks(-122, 122, z - 3.5, z + 3.5, True)
    # sidewalks flanking every avenue/street
    for x in AV:
        z0, z1 = (-96, 96) if x in (-36, 0, 36) else (-52, 96)
        sidewalk(x - 5.2, x - 3.5, z0, z1); sidewalk(x + 3.5, x + 5.2, z0, z1)
    for z in ST:
        sidewalk(-122, 122, z - 5.2, z - 3.5); sidewalk(-122, 122, z + 3.5, z + 5.2)
    for x in (-36, 0, 36):
        for z in ST:
            crosswalk(x, z, x in (-36, 0, 36) and True)
            crosswalk(x, z, False)

CELLS = {
    (-90, 78): 'park', (-54, 78): 'park', (-90, 42): 'park', (-54, 42): 'park',
    (-18, 78): 'hospital', (18, 78): 'houses', (54, 78): 'res', (90, 78): 'houses',
    (-18, 42): 'res', (18, 42): 'res', (54, 42): 'police', (90, 42): 'res',
    (-90, 6): 'res', (-54, 6): 'houses', (-18, 6): 'res', (18, 6): 'houses', (54, 6): 'res', (90, 6): 'res',
    (-90, -30): 'industry', (-54, -30): 'industry', (-18, -30): 'industry',
    (18, -30): 'downtown', (54, -30): 'downtown', (90, -30): 'downtown',
}

def build_cells():
    # NYC tenement mix: brick/brownstone first, the odd painted panel block after
    styles = ['brick', 'brick2', 'brick', 'sand', 'grey', 'panel', 'blue']
    for (gx, gz), kind in CELLS.items():
        if kind == 'res':
            # spawn-plaza clear radius
            if math.hypot(gx, gz - 30) < 34: continue
            res_block(gx, gz, 16, 12, RI(5, 9), styles[RI(0, len(styles) - 1)], damage=[0, 0, 1, 1, 2][RI(0, 4)])
            if R.random() < .5: res_block(gx + 4, gz + 6.5, 9, 8, RI(4, 6), styles[RI(0, len(styles) - 1)], damage=RI(0, 1))
        elif kind == 'houses':
            if math.hypot(gx, gz - 30) < 34: continue
            for (ox, oz) in ((-6.5, -5.5), (6.5, -5.5), (-6.5, 6), (6.5, 6)):
                if R.random() < .85:
                    house(gx + ox, gz + oz, brick=R.random() < .6)
        elif kind == 'hospital':
            hospital(gx, gz)
        elif kind == 'police':
            police(gx, gz)
        elif kind == 'industry':
            r = R.random()
            if r < .45: warehouse(gx, gz)
            elif r < .6: silo(gx - 4, gz); silo(gx + 2, gz + 3, r=1.8, h=8)
            elif r < .75: chimney(gx, gz)
            else:
                warehouse(gx, gz, 18, 12)
                container(gx + 7, gz - 3); container(gx + 7, gz + 1)
        elif kind == 'downtown':
            if gx == 18:  # Empire-State-style landmark: limestone stump + snapped mooring mast
                destroyed_tower(gx, gz, 22, 18, 4, cc=LIMESTN, mast=True)
                if R.random() < 1: rubble_pile(gx + 14, gz + 11, True)
            elif gx == 54:  # fissure + Chrysler-style leaning spire
                fissure(gx - 2, gz + 12, 9, 6)
                leaning_tower(gx + 6, gz - 2, 15, 15, 7)
            else:  # glass titan stump + the burned Times Square corner on Broadway
                destroyed_tower(gx, gz, 18, 20, 3, cc=GLASS_B)
                burnt_car(gx - 8, gz + 13, 1)
    times_square(28, 24)

def park():
    p = P('park_lawn')
    for (gx, gz) in ((-90, 78), (-54, 78), (-90, 42), (-54, 42)):
        p.boxg(gx - 14, gx + 14, -.05, .12, gz - 12, gz + 12, top=j(GRASS, .07), side=DIRT)
    # pond
    q = P('water_pond')
    q.cylg(-72, 60, -.9, -.75, 11, WATER_D, n=16)
    r = P('park_pondrim')
    r.cylg(-72, 60, -.8, .1, 11.6, j(SAND, .05), n=16)
    # paths
    for (a, b, horiz) in ((-108, -36, False), (-108, -36, True)):
        s = P('sidewalk_path')
        if horiz: s.boxg(-112, -32, -.05, .16, 59.2, 60.8, top=j(CONC_D, .05))
        else: s.boxg(-72.8, -71.2, -.05, .16, 26, 94, top=j(CONC_D, .05))
    for i in range(26):  # trees
        tree(-104 + RND(0, 68), 32 + RND(0, 60))
    for i in range(6):  # tents + benches + sandbag ring
        t = P('deco_tent')
        tx, tz = RND(-104, -40), RND(30, 88)
        t.beam((tx - 1.3, tz, 0), (tx + 1.3, tz, 1.4), 2.4, j(PAINT_GRN, .08), sq=.9)
        b = P('deco_bench')
        b.boxg(tx + 2, tx + 3.2, .25, .35, tz, tz + .5, top=WOOD_W)
    sandbags(-78, 48, 5)

def plaza():
    """Spawn plaza: monument, crater, sandbags — keep (0,30) r<10 clear."""
    p = P('sidewalk_plaza')
    p.boxg(-14, 14, -.05, .2, 12, 48, top=j(CONC_D, .05), side=CONC_BR)
    m = P('building_monument')
    m.boxg(-2, 2, .2, 1.6, 40, 44, top=j(CONC_BR, .05), side=j(CONC_D, .05))
    m.boxg(-.7, .7, 1.6, 6.5, 41.3, 42.7, top=j(CONC_BR, .06), side=j(PANEL_S, .05))
    q = P('deco_flag')
    q.beam((0, 42, 6.5), (3.2, 42.6, 6.2), .12, METAL)  # snapped flag arm
    crater(-8, 22, 3.4)
    sandbags(-6, 36, 5); sandbags(7, 34, 4)
    jersey(-13, 30, False); jersey(13, 32, False)
    rubble_pile(9, 20)

def dressing():
    # burnt & wrecked vehicles along streets — half of them are burned yellow cabs
    spots = [(-36, 12, 0), (-72, 42, 1), (36, 42, 0), (72, 12, 2), (-108, 78, 0), (108, 60, 1),
             (-36, -30, 0), (0, -12, 2), (90, 78, 0), (-90, 6, 1), (54, 24, 0), (-54, -12, 0),
             (-36, 60, 3), (36, 78, 3), (-72, 6, 3), (72, 42, 3), (-108, 24, 3), (108, -18, 3),
             (-90, -12, 3), (18, 60, 3), (-18, -48, 0), (90, 42, 0), (-54, 60, 1), (36, -48, 3)]
    for (x, z, k) in spots:
        burnt_car(x, z, k)
    tank_wreck(20, -6, .8); tank_wreck(-100, -18, 2.1)
    for i in range(16): hedgehog(RND(-118, 118), RND(-50, 92))
    for i in range(10): jersey(RND(-110, 110), RND(-48, 90), R.random() < .5)
    for i in range(18): rubble_pile(RND(-115, 115), RND(-50, 92), R.random() < .3)
    for i in range(12): fire_site(RND(-110, 110), RND(-48, 88))
    # NYC street furniture: subway entrances on the sidewalks, steam grates, scaffolds
    for (sx, sz, h) in ((4.35, 60, True), (-4.35, -12, True), (4.35, -48, True), (-4.35, 24, True),
                        (36, 65.35, True), (-72, 29.35, True), (-100, 89.35, True), (72, -29.35, True),
                        (108, 65.35, True), (18, -41.35, True)):
        subway_entrance(sx, sz, h)
    for i in range(12):
        steam_vent(RND(-115, 115) // 1, RND(-48, 92) // 1)
    scaffold_row(28, 31.5, 9); scaffold_row(-72, 11.5, 9); scaffold_row(90, 51.5, 9)
    # power lines along the avenues
    for i, x in enumerate((-100, -64, -28, 28, 64, 100)):
        powerline(x, 40 + (i % 3) * 18, lean=R.random() < .3)
        if i < 5:  # sagging cables between poles
            q = P('deco_cable')
            q.beam((x, 40 + (i % 3) * 18, 7.9), (x + 36, 40 + ((i + 1) % 3) * 18, 7.9), .05, DARK, sq=.15)
    for i in range(14): lamppost(RND(-115, 115), RND(-46, 90), R.random() < .35)

def build():
    ground()
    streets()
    broadway()
    build_cells()
    park()
    plaza()
    harbor()
    tv_tower(0, 108)
    dressing()
    crater(64, 76, 5); crater(-30, 66, 4.2); crater(4, -70, 5)
    emit_all()

def export():
    kw = dict(filepath=OUT, export_format='GLB', export_yup=True, export_apply=False,
              export_materials='NONE', export_extras=False, export_cameras=False, export_lights=False)
    known = {p.identifier for p in bpy.ops.export_scene.gltf.get_rna_type().properties}
    bpy.ops.export_scene.gltf(**{k: v for k, v in kw.items() if k in known})
    sz = os.path.getsize(OUT)
    print(f"[realcity] exported {OUT} ({sz/1e6:.2f} MB, {_gid[0]} nodes)")

if __name__ == '__main__':
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    build()
    export()
