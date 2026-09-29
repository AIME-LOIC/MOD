#!/usr/bin/env python3
"""
Compound Ops — authored GLB assets (uses tools/glbkit.py, no pip deps).

Outputs into compound_game_kit/:
  car_sedan.glb car_van.glb car_pickup.glb   (Car_ nodes -> the game's vehicle prefix)
  house_small.glb house_duplex.glb           (House_ nodes -> enterable interiors)
  skyscraper.glb                             (Tower_ nodes: floors, rooms, stairs, lift lobby)
  hotel.glb                                  (Hotel_ nodes: guest floors + rooftop pool)

Run:  python3 tools/build_assets.py
"""
import os, math, sys
sys.path.insert(0, os.path.dirname(__file__))
from glbkit import box, cyl, write_glb, T, Rx, Ry, Rz, S, mat_mul, placed

OUT = os.path.join(os.path.dirname(__file__), '..', 'compound_game_kit')

# palette (r,g,b 0..1)
STEEL   = (.28,.30,.33); GLASS = (.36,.52,.62); DARKG = (.18,.26,.32)
TIRE    = (.08,.08,.09); CHROME = (.62,.64,.68); LAMP = (1.0,.84,.5)
CONCRETE= (.55,.53,.50); CONC2 = (.48,.46,.44); RED = (.45,.12,.10)
WOOD    = (.42,.30,.18); BRICK = (.50,.28,.20); PALE = (.72,.70,.66)
WHITE   = (.82,.82,.80); TRIM = (.25,.27,.30); GOLD=(.72,.60,.30)
WATER   = (.20,.42,.55); SAND=(.74,.68,.52); GREEN=(.25,.38,.20)

def wheel(name, x, z, r=.34, w=.24):
    """Tire (flattened cylinder, axle along X) + chrome hubcap."""
    m = mat_mul(T(x, r, z), Rz(math.pi/2))
    return [cyl(f"{name}_tire", r, w, TIRE, seg=12, m=m),
            cyl(f"{name}_hub", r*.55, w+.04, CHROME, seg=10, m=m)]

def build_car(kind):
    L = {"sedan": 4.6, "van": 5.2, "pickup": 5.4}[kind]
    Wd = {"sedan": 1.86, "van": 2.0, "pickup": 2.0}[kind]
    body_h = {"sedan": .62, "van": 1.5, "pickup": .95}[kind]
    body_y = {"sedan": .58, "van": .85, "pickup": .78}[kind]
    color = {"sedan": (.30,.34,.38), "van": (.55,.52,.46), "pickup": (.36,.28,.22)}[kind]
    P = []
    P.append(box(f"Car_{kind}_body", L, body_h, Wd, color, T(0, body_y, 0)))
    if kind == "sedan":
        P.append(box("Car_sedan_cabin", 2.3, .55, Wd*.9, DARKG, T(-.1, body_y+body_h/2+.28, 0)))
        P.append(box("Car_sedan_windshield", 2.28, .5, Wd*.86, GLASS, T(1.05, body_y+body_h/2+.26, 0)))
        P.append(box("Car_sedan_glassL", 2.0, .4, .06, GLASS, T(-.1, body_y+body_h/2+.30, Wd*.45)))
        P.append(box("Car_sedan_glassR", 2.0, .4, .06, GLASS, T(-.1, body_y+body_h/2+.30, -Wd*.45)))
        P.append(box("Car_sedan_hood", 1.1, .18, Wd*.96, color, T(1.7, body_y+body_h/2+.06, 0)))
        P.append(box("Car_sedan_trunk", .9, .18, Wd*.96, color, T(-1.85, body_y+body_h/2+.06, 0)))
        P.append(box("Car_sedan_grille", .08, .22, Wd*.8, CHROME, T(L/2+.02, body_y, 0)))
    elif kind == "van":
        P.append(box("Car_van_windshield", 1.9, .8, Wd*.92, GLASS, T(1.7, body_y+body_h/2-.15, 0)))
        P.append(box("Car_van_glassL", 2.6, .55, .06, GLASS, T(-.2, body_y+body_h/2-.05, Wd*.5)))
        P.append(box("Car_van_glassR", 2.6, .55, .06, GLASS, T(-.2, body_y+body_h/2-.05, -Wd*.5)))
        P.append(box("Car_van_rack", 3.0, .1, Wd*.7, STEEL, T(-.4, body_y+body_h/2+.18, 0)))
    else:  # pickup
        P.append(box("Car_pickup_cab", 1.7, .8, Wd*.95, color, T(.5, body_y+body_h/2+.4, 0)))
        P.append(box("Car_pickup_glassF", 1.66, .6, Wd*.85, GLASS, T(1.1, body_y+body_h/2+.42, 0)))
        P.append(box("Car_pickup_bed", 2.3, .55, Wd*.98, CONC2, T(-1.5, body_y+body_h/2+.18, 0)))
    for (nm, wx, wz) in [("FL", L/2-.85, Wd/2), ("FR", L/2-.85, -Wd/2), ("RL", -L/2+.85, Wd/2), ("RR", -L/2+.85, -Wd/2)]:
        P += wheel(f"Car_{kind}_wheel{nm}", wx, wz)
    P.append(box(f"Car_{kind}_bumperF", .18, .3, Wd*.98, TRIM, T(L/2+.06, .42, 0)))
    P.append(box(f"Car_{kind}_bumperR", .18, .3, Wd*.98, TRIM, T(-L/2-.06, .42, 0)))
    P.append(box(f"Car_{kind}_lightL", .1, .16, .4, LAMP, T(L/2+.04, body_y+.12, Wd*.32)))
    P.append(box(f"Car_{kind}_lightR", .1, .16, .4, LAMP, T(L/2+.04, body_y+.12, -Wd*.32)))
    return P

def interior_floor(P, prefix, x0, x1, z0, z1, y, wall_h, col, doors=("N",)):
    """Walls around a rect floor with door gaps; door side N = -z. Returns nothing, appends parts."""
    t = .18
    def seg(nm, ax, az, bx, bz):
        cx, cz = (ax+bx)/2, (az+bz)/2
        ln = math.hypot(bx-ax, bz-az)
        ang = math.atan2(bz-az, bx-ax)
        if abs(math.cos(ang)) > .9:  # along x
            # split for door gap
            P.append(box(nm, ln, wall_h, t, col, T(cx, y+wall_h/2, cz)))
        else:
            P.append(box(nm, t, wall_h, ln, col, T(cx, y+wall_h/2, cz)))
    seg(f"{prefix}_wallN", x0, z0, x1, z0)
    seg(f"{prefix}_wallS", x0, z1, x1, z1)
    seg(f"{prefix}_wallW", x0, z0, x0, z1)
    seg(f"{prefix}_wallE", x1, z0, x1, z1)
    P.append(box(f"{prefix}_floor", x1-x0, .14, z1-z0, PALE, T((x0+x1)/2, y+.07, (z0+z1)/2)))

def door_gap(P, prefix, side, cx, y, h=2.2, w=1.3, col=TRIM):
    """Simple doorframe pair flanking a gap in the wall (gap = no geometry)."""
    if side in ("W", "E"):
        t = .18
        P.append(box(f"{prefix}_doorjamb{side}a", t, h, .5, col, T(cx, y+h/2, -w/2-.25)))
        P.append(box(f"{prefix}_doorjamb{side}b", t, h, .5, col, T(cx, y+h/2, w/2+.25)))
    else:
        P.append(box(f"{prefix}_doorjamb{side}a", .5, h, .18, col, T(cx-w/2-.25, y+h/2, 0)))
        P.append(box(f"{prefix}_doorjamb{side}b", .5, h, .18, col, T(cx+w/2+.25, y+h/2, 0)))

def staircase(P, prefix, x, z, y0, y1, width=1.3, steps=None, dir=1):
    """Straight stair along +x (dir=-1 mirrors it within the same strip): switchback flights."""
    run = 2.6
    steps = steps or max(6, int((y1-y0)/.32))
    for i in range(steps):
        sy = y0 + (y1-y0)*i/steps
        sx = x+run*(i+.5)/steps if dir > 0 else x+run-(i+.5)*run/steps
        P.append(box(f"{prefix}_step{i}", run/steps+.02, .12, width, CONCRETE,
                     T(sx, sy+.06, z)))

def stair_hole(x, z):
    """Hole rectangle (x0,x1,z0,z1) above a staircase so flights can pass through slabs."""
    return (x-.3, x+2.9, z-.85, z+.85)

def slab_with_hole(P, name, Wd, Dp, y, hole, col=CONCRETE):
    """Floor slab with a stairwell opening: 4 boxes framing the hole."""
    hx0, hx1, hz0, hz1 = hole
    def slabp(nm, x0, x1, z0, z1):
        if x1-x0 < .05 or z1-z0 < .05: return
        P.append(box(nm, x1-x0, .26, z1-z0, col, T((x0+x1)/2, y+.13, (z0+z1)/2)))
    slabp(f"{name}_a", -Wd/2, hx0, -Dp/2, Dp/2)
    slabp(f"{name}_b", hx1, Wd/2, -Dp/2, Dp/2)
    slabp(f"{name}_c", hx0, hx1, -Dp/2, hz0)
    slabp(f"{name}_d", hx0, hx1, hz1, Dp/2)

def build_house(kind):
    P = []
    if kind == "small":
        Wd, Dp = 10, 8
        P.append(box("House_small_base", Wd, .3, Dp, CONC2, T(0, .15, 0)))
        # ground floor: living room + kitchen, front door on -z
        interior_floor(P, "House_small_GF", -Wd/2, Wd/2, -Dp/2, Dp/2, .3, 2.9, PALE)
        P.append(box("House_small_wallN", Wd, 2.9, .18, BRICK, T(0, .3+1.45, -Dp/2)))
        # south wall with door gap: two segments
        P.append(box("House_small_wallSa", 3.35, 2.9, .18, BRICK, T(-Wd/4-1.65/2, .3+1.45, Dp/2)))
        P.append(box("House_small_wallSb", 3.35, 2.9, .18, BRICK, T(Wd/4+1.65/2, .3+1.45, Dp/2)))
        P.append(box("House_small_wallW", .18, 2.9, Dp, BRICK, T(-Wd/2, .3+1.45, 0)))
        P.append(box("House_small_wallE", .18, 2.9, Dp, BRICK, T(Wd/2, .3+1.45, 0)))
        P.append(box("House_small_partition", .18, 2.9, 4.2, PALE, T(1.4, .3+1.45, .9)))
        staircase(P, "House_small_st", -Wd/2+.9, 1.2, .3, 3.5)
        # upper floor slab + rooms
        P.append(box("House_small_slab", Wd, .22, Dp, CONCRETE, T(0, 3.4, 0)))
        P.append(box("House_small_UF_wallN", Wd, 2.5, .18, BRICK, T(0, 3.5+1.25, -Dp/2)))
        P.append(box("House_small_UF_wallSa", 3.85, 2.5, .18, BRICK, T(-Wd/4+0.2, 3.5+1.25, Dp/2)))
        P.append(box("House_small_UF_wallSb", 3.85, 2.5, .18, BRICK, T(Wd/4-0.2, 3.5+1.25, Dp/2)))
        P.append(box("House_small_UF_wallW", .18, 2.5, Dp, BRICK, T(-Wd/2, 3.5+1.25, 0)))
        P.append(box("House_small_UF_wallE", .18, 2.5, Dp, BRICK, T(Wd/2, 3.5+1.25, 0)))
        P.append(box("House_small_UF_partition", .18, 2.5, Dp, PALE, T(0.4, 3.5+1.25, 0)))
        P.append(box("House_small_roof", Wd+.5, .3, Dp+.5, RED, T(0, 6.15, 0)))
        P.append(box("House_small_parapetN", Wd+.5, .5, .15, TRIM, T(0, 6.55, -(Dp+.5)/2+.08)))
        P.append(box("House_small_parapetS", Wd+.5, .5, .15, TRIM, T(0, 6.55, (Dp+.5)/2-.08)))
        P.append(box("House_small_parapetW", .15, .5, Dp+.5, TRIM, T(-(Wd+.5)/2+.08, 6.55, 0)))
        P.append(box("House_small_parapetE", .15, .5, Dp+.5, TRIM, T((Wd+.5)/2-.08, 6.55, 0)))
        # windows: glass panes mounted in wall openings (visual; low sills vaultable)
        for wx in (-2.6, 0, 2.6):
            P.append(box(f"House_small_win{wx}", 1.1, 1.1, .1, GLASS, T(wx, 1.7, -Dp/2+.05)))
            P.append(box(f"House_small_winS{wx}", 1.1, 1.1, .1, GLASS, T(wx, 1.7, Dp/2-.05)))
        for wz in (-1.6, 1.6):
            P.append(box(f"House_small_winW{wz}", .1, 1.1, 1.1, GLASS, T(-Wd/2+.05, 1.7, wz)))
        # porch
        P.append(box("House_small_porch", 3.4, .25, 1.8, CONCRETE, T(0, .12, Dp/2+1.0)))
        P.append(box("House_small_porchroof", 3.4, .16, 2.0, RED, T(0, 2.7, Dp/2+1.0)))
        P.append(box("House_small_pillarL", .18, 2.6, .18, WOOD, T(-1.5, 1.4, Dp/2+1.8)))
        P.append(box("House_small_pillarR", .18, 2.6, .18, WOOD, T(1.5, 1.4, Dp/2+1.8)))
    else:  # duplex: two stacked apartments + shared stair
        Wd, Dp = 12, 9
        P.append(box("House_duplex_base", Wd, .3, Dp, CONC2, T(0, .15, 0)))
        for fl, (y0, ch, pre) in enumerate([(.3, 2.8, "House_duplex_A"), (3.4, 2.8, "House_duplex_B")]):
            interior_floor(P, f"{pre}_rooms", -Wd/2, Wd/2, -Dp/2, Dp/2, y0, ch, PALE if fl == 0 else PALE)
            P.append(box(f"{pre}_wallN", Wd, ch, .18, PALE, T(0, y0+ch/2, -Dp/2)))
            P.append(box(f"{pre}_wallSa", 4.35, ch, .18, PALE, T(-Wd/4-.5, y0+ch/2, Dp/2)))
            P.append(box(f"{pre}_wallSb", 4.35, ch, .18, PALE, T(Wd/4+.5, y0+ch/2, Dp/2)))
            P.append(box(f"{pre}_wallW", .18, ch, Dp, PALE, T(-Wd/2, y0+ch/2, 0)))
            P.append(box(f"{pre}_wallE", .18, ch, Dp, PALE, T(Wd/2, y0+ch/2, 0)))
            P.append(box(f"{pre}_part1", .18, ch, 3.6, WHITE, T(-1.6, y0+ch/2, 1.0)))
            P.append(box(f"{pre}_part2", .18, ch, 3.6, WHITE, T(1.9, y0+ch/2, 1.0)))
        P.append(box("House_duplex_slab", Wd, .22, Dp, CONCRETE, T(0, 3.3, 0)))
        staircase(P, "House_duplex_st", -Wd/2+.9, 1.2, .3, 3.5)
        staircase(P, "House_duplex_st2", -Wd/2+.9, 1.2, 3.4, 6.4)
        P.append(box("House_duplex_roof", Wd+.5, .3, Dp+.5, CONCRETE, T(0, 6.5, 0)))
        P.append(box("House_duplex_ac1", .9, .5, .9, STEEL, T(2.5, 6.9, -1.5)))
        P.append(box("House_duplex_ac2", .9, .5, .9, STEEL, T(3.6, 6.9, -1.2)))
        P.append(box("House_duplex_water", 1.1, 1.3, 1.1, PALE, T(-3.0, 7.2, 1.4)))
    return P

def build_skyscraper():
    """Enterable tower: lobby, N office floors (rooms + stairs + lift lobby), rooftop pad."""
    P = []
    Wd, Dp = 26, 20
    floors = 12
    fh = 3.4
    P.append(box("Tower_foundation", Wd+2, .45, Dp+2, CONC2, T(0, .22, 0)))
    P.append(box("Tower_liftshaft_glass", 2.8, floors*fh+3.5, .12, GLASS, T(-Wd/2+4.0, (floors*fh+3.5)/2+.5, -Dp/2+9.1)))
    stair_x, stair_z = -Wd/2+1.4, -Dp/2+3.2
    hole = stair_hole(stair_x, stair_z)
    for f in range(floors):
        y = .5 + f*fh
        tag = f"Tower_F{f:02d}"
        # perimeter walls with a south entrance gap on F0
        if f == 0:
            P.append(box(f"{tag}_wallSa", 8.4, fh, .22, GLASS, T(-Wd/4-1.0, y+fh/2, Dp/2)))
            P.append(box(f"{tag}_wallSb", 8.4, fh, .22, GLASS, T(Wd/4+1.0, y+fh/2, Dp/2)))
        else:
            P.append(box(f"{tag}_wallS", Wd, fh, .22, GLASS, T(0, y+fh/2, Dp/2)))
            for wx in range(3):
                P.append(box(f"{tag}_winS{wx}", 4.2, 1.9, .1, DARKG, T(-6+wx*6, y+1.9, Dp/2-.05)))
        P.append(box(f"{tag}_wallN", Wd, fh, .22, GLASS, T(0, y+fh/2, -Dp/2)))
        P.append(box(f"{tag}_wallW", .22, fh, Dp, GLASS, T(-Wd/2, y+fh/2, 0)))
        P.append(box(f"{tag}_wallE", .22, fh, Dp, GLASS, T(Wd/2, y+fh/2, 0)))
        # floor slab with stairwell opening (ceilings stay walkable elsewhere)
        if f > 0:
            slab_with_hole(P, f"{tag}_slab", Wd, Dp, y, hole)
        else:
            P.append(box(f"{tag}_slab", Wd, .26, Dp, CONCRETE, T(0, y+.13, 0)))
        # office partitions: 3 rooms per floor
        for px in (-Wd/4, Wd/4):
            P.append(box(f"{tag}_roomdiv{px}", .16, fh-.3, Dp-8, WHITE, T(px, y+(fh-.3)/2, 2)))
        P.append(box(f"{tag}_deskrow", 6.5, .8, .5, WOOD, T(0, y+.45, -Dp/4)))
        P.append(box(f"{tag}_sofa", 2.6, .5, .9, RED, T(Wd/4, y+.3, 3.5)))
        # switchback stairs on the west wall (alternate direction per floor) + a visible lift car
        staircase(P, f"{tag}_st", stair_x, stair_z, y, y+fh, 1.2, steps=8, dir=1 if f % 2 == 0 else -1)
        P.append(box(f"{tag}_liftcar", 2.2, 2.4, 2.2, CHROME, T(-Wd/2+4.0, y+.1, -Dp/2+7.6)))
    # roof: parapet, AC units, helipad — hole above the top flight so the roof is reachable
    yr = .5 + floors*fh
    slab_with_hole(P, "Tower_roof", Wd, Dp, yr, hole)
    P.append(box("Tower_parapetN", Wd, .9, .2, CONCRETE, T(0, yr+.75, -Dp/2+.1)))
    P.append(box("Tower_parapetS", Wd, .9, .2, CONCRETE, T(0, yr+.75, Dp/2-.1)))
    P.append(box("Tower_parapetW", .2, .9, Dp, CONCRETE, T(-Wd/2+.1, yr+.75, 0)))
    P.append(box("Tower_parapetE", .2, .9, Dp, CONCRETE, T(Wd/2-.1, yr+.75, 0)))
    P.append(box("Tower_helipad", 8, .18, 8, CONCRETE, T(4, yr+.36, 2)))
    P.append(box("Tower_helipadH", 3.4, .06, .8, WHITE, T(4, yr+.48, 2)))
    P.append(box("Tower_helipadH2", .8, .06, 3.4, WHITE, T(4, yr+.48, 2)))
    for i in range(3):
        P.append(box(f"Tower_ac{i}", 1.4, .8, 1.4, STEEL, T(-8+i*2.6, yr+.7, -6)))
    P.append(box("Tower_antenna", .3, 7, .3, STEEL, T(0, yr+3.8, 0)))
    P.append(box("Tower_sign", 6, 1.1, .18, GOLD, T(0, yr+2.4, Dp/2-.05)))
    return P

def build_hotel():
    """Hotel: lobby, 8 guest floors (4 rooms each, beds), rooftop pool + bar."""
    P = []
    Wd, Dp = 30, 18
    floors, fh = 8, 3.5
    P.append(box("Hotel_foundation", Wd+2, .45, Dp+2, CONC2, T(0, .22, 0)))
    stair_x, stair_z = Wd/2-8.5, -Dp/2+2.0
    hole = stair_hole(stair_x, stair_z)
    for f in range(floors):
        y = .4 + f*fh
        tag = f"Hotel_F{f:02d}"
        P.append(box(f"{tag}_wallS", Wd, fh, .22, PALE, T(0, y+fh/2, Dp/2)))
        P.append(box(f"{tag}_wallN", Wd, fh, .22, PALE, T(0, y+fh/2, -Dp/2)))
        P.append(box(f"{tag}_wallW", .22, fh, Dp, PALE, T(-Wd/2, y+fh/2, 0)))
        P.append(box(f"{tag}_wallE", .22, fh, Dp, PALE, T(Wd/2, y+fh/2, 0)))
        if f == 0:  # lobby
            P.append(box("Hotel_lobby_desk", 6, 1.1, .8, WOOD, T(-3, y+.55, -2)))
            P.append(box("Hotel_lobby_glass", Wd-4, 2.2, .1, GLASS, T(0, y+1.4, Dp/2-.06)))
            P.append(box("Hotel_lobby_sofa", 3.2, .5, 1.0, RED, T(4, y+.3, -3)))
            staircase(P, "Hotel_lobby_st", stair_x, stair_z, y, y+fh, 1.3, steps=9)
        else:
            # guest floor: slab with stairwell first, then 4 rooms around a center corridor
            slab_with_hole(P, f"{tag}_slab", Wd, Dp, y, hole)
            # 4 guest rooms: center corridor along x
            P.append(box(f"{tag}_corridor", Wd-10, .04, 2.4, PALE, T(0, y+.04, 0)))
            for i, px in enumerate((-Wd/4-1.5, Wd/4+1.5)):
                P.append(box(f"{tag}_div{i}", .16, fh-.3, Dp/2-2.5, WHITE, T(px, y+(fh-.3)/2, -Dp/4-1)))
                P.append(box(f"{tag}_divB{i}", .16, fh-.3, Dp/2-2.5, WHITE, T(px, y+(fh-.3)/2, Dp/4+1)))
            for i, (bx, bz) in enumerate([(-Wd/4-4.0, -Dp/4), (-Wd/4+1.5, -Dp/4), (Wd/4-1.5, -Dp/4), (Wd/4+4.0, -Dp/4)]):
                P.append(box(f"{tag}_bed{i}", 1.9, .5, 1.4, WHITE, T(bx, y+.25, bz)))
                P.append(box(f"{tag}_pillow{i}", 1.6, .18, .5, GOLD, T(bx, y+.55, bz-.45)))
            staircase(P, f"{tag}_st", stair_x, stair_z, y, y+fh, 1.3, steps=9, dir=1 if f % 2 == 0 else -1)
    yr = .4 + floors*fh
    slab_with_hole(P, "Hotel_roof", Wd, Dp, yr, hole)
    # rooftop pool: real water zone in game (water_y known from node name)
    P.append(box("Hotel_pool_basin", 9, .5, 5, WHITE, T(-7, yr+.55, 0)))
    P.append(box("Hotel_pool_water", 8.2, .18, 4.2, WATER, T(-7, yr+.72, 0)))
    P.append(box("Hotel_pool_deck", 12, .12, 7, SAND, T(-6, yr+.36, 1)))
    for i in range(4):
        P.append(box(f"Hotel_lounge{i}", .9, .4, .9, WHITE, T(-2+i*1.3, yr+.56, 3.2)))
    P.append(box("Hotel_bars", 5, 1.0, .8, WOOD, T(4, yr+.8, 2)))
    P.append(box("Hotel_barroof", 5.6, .2, 2.6, RED, T(4, yr+2.6, 2)))
    P.append(box("Hotel_barpostL", .16, 2.6, .16, WOOD, T(1.6, yr+1.6, 3.0)))
    P.append(box("Hotel_barpostR", .16, 2.6, .16, WOOD, T(6.4, yr+1.6, 3.0)))
    P.append(box("Hotel_parapetN", Wd, 1.0, .2, CONCRETE, T(0, yr+.8, -Dp/2+.1)))
    P.append(box("Hotel_parapetS", Wd, 1.0, .2, CONCRETE, T(0, yr+.8, Dp/2-.1)))
    P.append(box("Hotel_parapetW", .2, 1.0, Dp, CONCRETE, T(-Wd/2+.1, yr+.8, 0)))
    P.append(box("Hotel_parapetE", .2, 1.0, Dp, CONCRETE, T(Wd/2-.1, yr+.8, 0)))
    P.append(box("Hotel_sign", 7, 1.3, .2, GOLD, T(6, yr+2.8, Dp/2-.05)))
    P.append(box("Hotel_ac", 1.4, .8, 1.4, STEEL, T(10, yr+.7, -5)))
    return P

if __name__ == "__main__":
    jobs = [
        ("car_sedan.glb", build_car("sedan")),
        ("car_van.glb", build_car("van")),
        ("car_pickup.glb", build_car("pickup")),
        ("house_small.glb", build_house("small")),
        ("house_duplex.glb", build_house("duplex")),
        ("skyscraper.glb", build_skyscraper()),
        ("hotel.glb", build_hotel()),
    ]
    for fn, parts in jobs:
        path = os.path.join(OUT, fn)
        n = write_glb(path, parts, name=fn)
        print(f"{fn}: {len(parts)} parts, {n/1024:.0f} KB")
