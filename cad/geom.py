"""Parametric geometry for the split Air75 case. All units mm. Z up, table at z=0.

Every dimension marked ASSUMED comes from typical low-profile/MX-style values, not from a
datasheet. Print models/print/fit_test_plate.stl first and change the number here if it does not fit.
"""
import math
import numpy as np
from shapely.geometry import Polygon, box, Point
from shapely.ops import unary_union
from layout import build, U, NROWS

# ---- case parameters -------------------------------------------------------
SW_HOLE   = 14.0    # KS-33 plate hole, measured from Gateron's KS-33 STEP model (14.0 x 14.0). Still print the fit test.
PLATE_T   = 1.2     # plate thickness (switch clips need ~1.2-1.5)
INTERIOR  = 5.2     # plate underside -> base top. ASSUMED: switch pins end <=4.0 below plate + wire room; battery is 4.5 tall
BASE_T    = 1.6
H_TOTAL   = BASE_T + INTERIOR + PLATE_T   # 8.0, table -> top of plate
WALL      = 1.6
MARGIN    = 2.8     # key cell edge -> outer side walls (the tightest the row wires climbing the side wall allow)
FRONT_MARGIN = 3.2  # key cell edge -> front wall (the bottom row's wire runs in front of it)
CLOSE_R   = 6.0     # fillet radius on concave outline corners
BAY_D     = 21.0    # back bay depth beyond the top row's cell edge (controller + long battery lie side by side here)
CORNER_R  = 7.0     # outer corner radius of the joined keyboard
SEAM_GAP  = 0.2     # clearance between the two halves along the seam
WALL_SEAM = 1.8     # wall thickness on both sides of the seam (holds magnet pockets)
MAG_D, MAG_T, MAG_Z = 5.0, 1.0, 3.4     # 5 x 1 mm disc magnets, pocket centre height
MAG_POCKET_R, MAG_POCKET_DEPTH = 2.6, 1.1
# V-shaped tongue and groove (45 degree flanks, so both print without supports). Half-width = apex - |z - centre|.
TONGUE_APEX, GROOVE_APEX, TG_ZC = 0.6, 0.85, 6.7
TONGUE_HW, GROOVE_HW = TONGUE_APEX, GROOVE_APEX
TG_END_GROOVE, TG_END_TONGUE = 1.6, 2.0   # both stop short of the outer skin, so outside only the 0.2 mm hairline shows
def tg_slices(apex, dz=0.1):
    out, z = [], TG_ZC - apex
    while z < TG_ZC + apex - 1e-9:
        hw = apex - abs(z + dz / 2 - TG_ZC)
        if hw > 0.04: out.append((z, z + dz, hw))
        z += dz
    return out
STAB_DX   = 11.938  # ASSUMED: 2u plate-mount stabiliser spacing (MX standard)
STAB_W, STAB_H = 6.65, 12.3   # ASSUMED MX plate-mount stab cutout
STAB_Y0, STAB_Y1 = -5.85, 6.45
POST_D    = 5.0
INSERT_D, INSERT_DEPTH = 3.2, 3.5       # M2 x 4 brass heat-set insert
SCREW_D, CSK_D = 2.3, 4.4               # M2 countersunk through base
POSTS = {"L": 8, "R": 10}
WIRE = dict(pin_col=(-4.4, -4.7), pin_dio=(2.6, -5.75), row_dy=-10.45)   # KS-33 pins toward you; row wire offset
CLIP_RELIEF = 15.6

# Gateron KS-33 Low Profile 2.0, measured from its STEP model: 15 x 15 flange on the plate, clips catch 1.2 mm
# under the plate top, body ends 2.55 mm below the plate top, centre post 5.8 mm below, stem top 6.0 above.
KS33 = dict(hole=14.0, flange=15.0, body_below=2.55, post_below=5.8, pins_below=4.95, above=6.0, travel=3.2, well_floor=3.0)
# Low-profile keycap for Gateron LP (nSA / Keychron-LP style). ASSUMED: skirt 3.4 mm above the plate, 4.0 mm tall.
CAP = dict(skirt=3.4, h=4.0)
FOOT_T = 1.5          # 8 mm round silicone feet, 1.5 mm thick, sit 0.5 mm deep in the base recesses

def thickness():
    """Stack-up, table to top, in mm."""
    plate_top = H_TOTAL
    return dict(base=BASE_T, interior=INTERIOR, plate=PLATE_T, case=H_TOTAL,
                switch_top=plate_top + KS33["above"], cap_top=plate_top + CAP["skirt"] + CAP["h"],
                feet=FOOT_T - 0.5, on_desk=plate_top + CAP["skirt"] + CAP["h"] + FOOT_T - 0.5,
                post_clearance=INTERIOR + PLATE_T - KS33["post_below"])

# components (ghost sizes), all lie on the base
MCU    = dict(w=18.0, l=33.0, t=1.6, usb_w=8.94, usb_h=3.26, lift=1.0)  # SuperMini nRF52840 (Pro Micro size), mid-mount USB-C, on 1 mm foam tape; USB faces the side wall
# KP Original 551245 LiPo, 480 mAh (listed), 48 x 14 x 5.1 mm, in stock at Zbotic (India). One per half.
# It is 5.1 mm thick, so it sits in a 0.6 mm pocket in the base to keep 0.7 mm of air under the top skin.
BATT   = dict(l=48.0, w=14.0, t=5.1, pocket=0.6, name="KP 551245")
BATT_L = BATT
def batt_of(side): return BATT
# 0.91" 128x32 SSD1306 I2C OLED module (same part as the Corne LP): PCB 38 x 12 x 1.2, glass 30 x 11.5 x 1.6,
# visible area 24.4 x 7.6. Pins (GND VCC SCL SDA) at one short end, which faces the controller.
OLED = dict(pcb_l=38.4, pcb_w=12.4, pcb_t=1.2, glass_l=30.6, glass_w=12.0, glass_t=1.6, glass_from_pin=7.0,
            win_l=26.0, win_w=8.4, lip=0.4, frame=0.8)
# The OLED sits in a small raised pod behind the top row, tilted toward you so you can read it while typing.
OLED_TILT, POD_LIFT, POD_WALL, POD_REAR = 10.0, 1.0, 1.6, 1.2   # degrees; bezel front above the deck; front/side wall; rear wall
# The pod is a separate small bezel (prints window-face-down, no supports). It sits flat on the deck on two 1.1 mm pegs,
# over a slot that lets the module's lower half drop below the deck.
BEZEL_R, BEZEL_END_R = 0.6, 0.8
# The bezel's outside is one tapered pod: sloped ends and a sloped back that run down onto the deck, rounded corners.
# It prints window-face-down, so every outer face must stay at least 45 degrees from that face. With the 15 degree tilt
# that allows end ramps down to 46 degrees and a back slope down to 30 degrees.
BEZEL_END_RUN = 0.9      # end ramps: 0.9 mm out per mm of height (48 degrees)
BEZEL_TOP_R   = 2.0      # plan-view corner radius of the top face
BEZEL_BASE_R  = 2.5      # corner radius of the footprint on the deck
BEZEL_BACK_MIN_DEG = 32.0
PEG_R, PEG_HOLE_R, PEG_L = 0.55, 0.7, 1.0
EDGE_R  = 2.5         # rounded top edge (outer perimeter; it runs straight across the seam, so the joined board reads as one piece)
EDGE_RB = 0.8         # rounded bottom edge
EDGE_DEG   = 3.0      # the rounded edges are true lofted curves, one ring every 3 degrees of arc (no stair steps)
CORNER_SEGS = 32      # segments per 90 degree outline corner

def soft(u, R):
    """Inset of a rounded edge at distance u from the face it rounds into. Circle, but never steeper than 45 degrees
    in the last bit next to that face, so the edge prints face-down on the bed without drooping (a 'teardrop' round)."""
    if u >= R: return 0.0
    u45 = R * (1 - 1 / math.sqrt(2))
    if u >= u45: return R - math.sqrt(max(0.0, R * R - (R - u) ** 2))
    return R - math.sqrt(R * R - (R - u45) ** 2) + (u45 - u)

def soft_profile(R):
    """(u, inset) samples along a teardrop round of radius R, from the wall (u = R, inset 0) to the face (u = 0).
    The circle part is sampled every EDGE_DEG degrees; the last 45 degree part is straight, so two points do it."""
    pts, n = [], max(2, int(math.ceil(45.0 / EDGE_DEG)))
    for i in range(n + 1):
        f = math.radians(45.0 * i / n)
        pts.append((R * (1 - math.sin(f)), R * (1 - math.cos(f))))
    pts.append((0.0, soft(0.0, R)))
    return pts

def edge_profile():
    """(z, inset) rings for the case's outer skin: rounded bottom edge, straight wall, rounded top edge."""
    bot = [(u, d) for u, d in reversed(soft_profile(EDGE_RB))]          # z = u, from the desk up
    top = [(H_TOTAL - u, d) for u, d in soft_profile(EDGE_R)]           # from the wall up to the deck
    return bot + top

def rrect_ring(b, r, inset=0.0, n=CORNER_SEGS):
    """Counter-clockwise rounded rectangle, bounds b, corner radius r, shrunk by inset. Every inset has the same
    vertex count and angles, so rings at different heights can be lofted into one smooth surface."""
    x0, y0, x1, y1 = b[0] + inset, b[1] + inset, b[2] - inset, b[3] - inset
    rr = r - inset
    out = []
    for cx, cy, a0 in ((x1 - rr, y1 - rr, 0), (x0 + rr, y1 - rr, 90), (x0 + rr, y0 + rr, 180), (x1 - rr, y0 + rr, 270)):
        for i in range(n + 1):
            a = math.radians(a0 + 90.0 * i / n)
            out.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return out
SLIDE  = dict(l=8.6, w=3.7, t=3.5)                           # slide power switch
USB_SLOT = dict(w=11.0, h=6.2)    # sized for the cable overmold so the plug seats fully
PWR_SLOT = dict(w=5.2, h=2.4)
RST_HOLE = 3.0

def rect_poly(cx, cy, w, h):
    return box(cx - w/2, cy - h/2, cx + w/2, cy + h/2)

from functools import lru_cache
from shapely.affinity import translate

@lru_cache(maxsize=1)
def _global():
    """The whole keyboard as one board: rounded outline, split into two halves along a staircase seam."""
    allk = build()
    for k in allk:
        k["gx"] = k["cx"] * U
        k["gy"] = -k["row"] * U
    cellsL = unary_union([rect_poly(k["gx"], k["gy"], k["w"]*U, U) for k in allk if k["side"] == "L"])
    cellsR = unary_union([rect_poly(k["gx"], k["gy"], k["w"]*U, U) for k in allk if k["side"] == "R"])
    allcells = unary_union([cellsL, cellsR])
    minx, miny, maxx, maxy = allcells.bounds
    top_edge = maxy
    bay = box(minx, top_edge - 1, maxx, top_edge + BAY_D - MARGIN)
    T = box(minx, miny, maxx, top_edge + BAY_D - MARGIN)    # the cells tile this rectangle exactly; a clean box avoids hairline cracks
    OB = (minx - MARGIN, miny - FRONT_MARGIN, maxx + MARGIN, top_edge + BAY_D)     # T grown by MARGIN, corners rounded
    O = Polygon(rrect_ring(OB, CORNER_R))
    xcut = {r: max(k["x0"] + k["w"] for k in allk if k["row"] == r and k["side"] == "L") * U for r in range(NROWS)}
    edges = [round(U/2 - k*U, 6) for k in range(NROWS + 1)]      # shared band edges, no hairline gaps
    bands = []
    for r in range(NROWS):
        y0, y1 = edges[r + 1], edges[r]
        if r == 0: y1 = 1000.0
        if r == NROWS - 1: y0 = -1000.0
        bands.append(box(-1000.0, y0, round(xcut[r], 6), y1))
    region = unary_union(bands).buffer(0)
    right = O.difference(region)
    left = O.intersection(region).difference(right.buffer(SEAM_GAP, join_style=2))
    seam = region.boundary.intersection(O)
    mags = [(xcut[r], -r*U) for r in range(NROWS)]
    mags += [(xcut[0], top_edge + (BAY_D - WALL) / 2)]
    ox = {"L": 0.0, "R": min(k["x0"] for k in allk if k["side"] == "R") * U}
    big = box(-1000.0, -1000.0, 1000.0, 1000.0)       # each half's footprint without the outer outline, used to cut
    cutR = big.difference(region)                      # the one-piece lofted skin into the two halves
    cutL = region.difference(cutR.buffer(SEAM_GAP, join_style=2))
    return dict(allk=allk, O=O, OB=OB, left=left, right=right, seam=seam, mags=mags, xcut=xcut, ox=ox,
                top_edge=top_edge, bay_cut=xcut[0], cut=dict(L=cutL, R=cutR))

def half(side):
    g = _global()
    ox = g["ox"][side]
    keys = [dict(k) for k in g["allk"] if k["side"] == side]
    for k in keys:
        k["X"] = k["gx"] - ox
        k["Y"] = k["gy"]
    tr = lambda geom: translate(geom, xoff=-ox)
    cells = [rect_poly(k["X"], k["Y"], k["w"]*U, U) for k in keys]
    outline = tr(g["left"] if side == "L" else g["right"])
    seam = tr(g["seam"])
    seam_d = WALL_SEAM + (SEAM_GAP if side == "L" else 0.0)
    cavity = outline.buffer(-WALL, join_style=1, resolution=24).difference(
        seam.buffer(seam_d, cap_style=2, join_style=2))
    holes, stabs = [], []
    for k in keys:
        holes.append(rect_poly(k["X"], k["Y"], SW_HOLE, SW_HOLE))
        if k["w"] >= 2:
            for sgn in (-1, 1):
                stabs.append(box(k["X"] + sgn*STAB_DX - STAB_W/2, k["Y"] + STAB_Y0,
                                 k["X"] + sgn*STAB_DX + STAB_W/2, k["Y"] + STAB_Y1))
    ob = outline.bounds
    inner_sign = 1 if side == "L" else -1
    inner_x = g["bay_cut"] - ox - (SEAM_GAP if side == "L" else 0.0)
    def xin(d): return inner_x - inner_sign * d
    y_int_top = ob[3] - WALL
    outer_wall = (ob[0] + WALL) if side == "L" else (ob[2] - WALL)
    def xo(d): return outer_wall + inner_sign * d          # distance in from the outer side wall
    comp = {}
    # controller lies along x at the outer end of the bay, USB-C pointing out of the side wall.
    m_top = 2.0
    m_cy = y_int_top - m_top - MCU["w"]/2
    dx = next(d / 10 for d in range(3, 60)
              if cavity.contains(rect_poly(xo(d/10 + MCU["l"]/2), m_cy, MCU["l"], MCU["w"])))
    comp["mcu"]  = dict(cx=xo(dx + MCU["l"]/2), cy=m_cy, w=MCU["l"], h=MCU["w"], usb_gap=dx)
    comp["rst"]  = dict(cx=xo(dx + MCU["l"] + 4.0 + 2.3), cy=y_int_top - 2.5, w=4.6, h=4.6)
    comp["slide"]= dict(cx=xo(dx + MCU["l"] + 4.0 + 4.6 + 4.0 + SLIDE["l"]/2), cy=y_int_top - SLIDE["w"]/2 - 0.1, w=SLIDE["l"], h=SLIDE["w"])
    B = batt_of(side)
    comp["batt"] = dict(cx=xin(3.0 + B["l"]/2), cy=y_int_top - 0.4 - B["w"]/2, w=B["l"], h=B["w"])
    # OLED: in a tilted pod between the controller and the battery, pins toward the controller
    th = math.radians(OLED_TILT)
    Ls = POD_WALL + OLED["pcb_w"] + 0.4 + POD_REAR           # pod top, measured along the slope
    y_f = g["top_edge"] + 0.5                                # pod front stays behind the top-row keycaps
    pose = dict(theta=th, y_f=y_f, z_f=H_TOTAL + POD_LIFT, Ls=Ls, s0=POD_WALL,
                y_b=y_f + Ls * math.cos(th), z_b=H_TOTAL + POD_LIFT + Ls * math.sin(th))
    def sn(s, n):                                           # slope coordinates -> (y, z)
        return (y_f + s * math.cos(th) - n * math.sin(th), pose["z_f"] + s * math.sin(th) + n * math.cos(th))
    pose["sn"] = sn
    mod_y = [sn(pose["s0"], -3.3)[0], sn(pose["s0"] + OLED["pcb_w"] + 0.4, 0)[0]]
    comp["oled"] = dict(cx=xo(dx + MCU["l"] + 6.0 + OLED["pcb_l"]/2), cy=(mod_y[0] + mod_y[1]) / 2, w=OLED["pcb_l"], h=mod_y[1] - mod_y[0])
    z_usb = BASE_T + MCU["lift"] + MCU["t"]/2                # mid-mount: connector centred on the board
    openings = [
        dict(kind="usb",   x=comp["mcu"]["cx"], y=m_cy, zc=z_usb, w=USB_SLOT["w"], h=USB_SLOT["h"], side_wall=True),
        dict(kind="power", x=comp["slide"]["cx"], zc=BASE_T + 2.4, w=PWR_SLOT["w"], h=PWR_SLOT["h"]),
        dict(kind="reset", x=comp["rst"]["cx"],   zc=BASE_T + 2.0, w=RST_HOLE, h=RST_HOLE),
    ]
    keep = [rect_poly(k["X"], k["Y"], 15.6, 15.6) for k in keys] + stabs     # KS-33 clips span 14.8 under the plate
    keep += [rect_poly(c["cx"], c["cy"], c["w"] + 1.2, c["h"] + 1.2) for c in comp.values()]
    # wiring lanes stay clear of screw posts: behind the F-row (columns and rows run to the controller here)
    # and along the outer side wall (row wires climb to the bay here). See routing.py.
    kx0 = min(k["X"] - k["w"] * U / 2 for k in keys); kx1 = max(k["X"] + k["w"] * U / 2 for k in keys)
    top_edge = g["top_edge"]
    keep += [box(kx0 - 5, top_edge - 2.9, kx1 + 5, top_edge + 0.4)]
    keep += [box(kx0 - 5, -1000, kx0 + 0.3, 1000)] if side == "L" else [box(kx1 - 0.3, -1000, kx1 + 5, 1000)]
    from shapely.geometry import LineString
    pc, pd, rdy = WIRE["pin_col"], WIRE["pin_dio"], WIRE["row_dy"]
    for r in sorted({k["row"] for k in keys}):
        rk = [k for k in keys if k["row"] == r]
        x0r = min(k["X"] for k in rk) + pd[0] - 6.5; x1r = max(k["X"] for k in rk) + pd[0] + 6.5
        x0r, x1r = (kx0 - 5, x1r) if side == "L" else (x0r, kx1 + 5)      # row wire continues to the side-wall lane
        keep.append(box(x0r, rk[0]["Y"] + rdy - 1.0, x1r, rk[0]["Y"] + rdy + 1.0))
    for c in sorted({k["col_local"] for k in keys}):
        ck = sorted([k for k in keys if k["col_local"] == c], key=lambda k: k["row"])
        path = []
        for i, k in enumerate(ck):
            q = (k["X"] + pc[0], k["Y"] + pc[1])
            if i: path += [(path[-1][0], k["Y"] + 7.6), (q[0], k["Y"] + 7.6)]
            path.append(q)
        if len(path) > 1:
            keep.append(LineString(path).buffer(1.0))
    # bay: power and reset wires cross between the battery end and the controller
    mcu_in = comp["mcu"]["cx"] - inner_sign * 0 + (MCU["l"] / 2 if side == "L" else -MCU["l"] / 2)
    bat_out = comp["batt"]["cx"] - (B["l"] / 2 if side == "L" else -B["l"] / 2)
    keep.append(box(min(mcu_in, bat_out) - 1, top_edge + 7.0, max(mcu_in, bat_out) + 1, y_int_top))   # front of the bay stays free for a post
    keepu = unary_union(keep).buffer(POST_D/2 + 0.5)
    legal = cavity.buffer(-(POST_D/2 + 1.0)).difference(keepu)
    xs = np.arange(ob[0], ob[2], 1.0); ys = np.arange(ob[1], ob[3], 1.0)
    cand = [(x, y) for x in xs for y in ys if legal.contains(Point(x, y))]
    n = POSTS[side]
    chosen = [min(cand, key=lambda p: (p[0] - ob[0])**2 + (p[1] - ob[1])**2)]
    if side == "L":     # the bay is full on the left: one post in the back channel behind the OLED, beside the slide switch
        sl, bt = comp["slide"], comp["batt"]
        fx = (sl["cx"] + sl["w"] / 2 + bt["cx"] - bt["w"] / 2) / 2
        chosen.append((fx, y_int_top - POST_D / 2 - 0.1))
    while len(chosen) < n:
        chosen.append(max(cand, key=lambda p: min((p[0]-q[0])**2 + (p[1]-q[1])**2 for q in chosen)))
    names = [n for n in comp if n != "oled"]       # the OLED pod sits above the deck; checked on its own below
    for i in range(len(names)):
        a = rect_poly(comp[names[i]]["cx"], comp[names[i]]["cy"], comp[names[i]]["w"], comp[names[i]]["h"])
        assert cavity.contains(a), f"{side}: {names[i]} outside cavity"
        for j in range(i + 1, len(names)):
            b = rect_poly(comp[names[j]]["cx"], comp[names[j]]["cy"], comp[names[j]]["w"], comp[names[j]]["h"])
            assert not a.intersects(b), f"{side}: {names[i]} overlaps {names[j]}"
        for p in holes:
            assert not a.intersects(p.buffer(0.5)), f"{side}: {names[i]} overlaps a switch hole"
    o = comp["oled"]
    frame = rect_poly(o["cx"], o["cy"], o["w"] + 2 * POD_WALL, o["h"])
    for n2 in ("mcu", "batt"):
        c2 = comp[n2]
        assert not frame.intersects(rect_poly(c2["cx"], c2["cy"], c2["w"], c2["h"])), f"{side}: OLED pod hits {n2}"
    assert cavity.contains(frame), f"{side}: OLED pod outside the case"
    # where the glass and the window sit (the glass is offset toward the far end; pins at the near end)
    pin_dir = -inner_sign                                # +1: pins at +x
    gl_c = o["cx"] + pin_dir * (o["w"]/2 - OLED["glass_from_pin"] - OLED["glass_l"]/2)
    oled_glass = rect_poly(gl_c, o["cy"], OLED["glass_l"], OLED["glass_w"])
    oled_win = rect_poly(gl_c, o["cy"], OLED["win_l"], OLED["win_w"])
    # seam hardware, local coordinates
    face_dx = -SEAM_GAP if side == "L" else 0.0
    magnets = [dict(x=mx - ox + face_dx, y=my) for (mx, my) in g["mags"]]
    tongue = tr(seam.__class__ and g["seam"]).buffer(TONGUE_HW, cap_style=2, join_style=2).intersection(tr(g["O"]))
    groove = tr(g["seam"]).buffer(GROOVE_HW, cap_style=2, join_style=2).intersection(tr(g["O"]))
    return dict(side=side, keys=keys, cells=cells, holes=holes, stabs=stabs, outline=outline,
                cavity=cavity, comp=comp, openings=openings, posts=chosen, bounds=ob,
                inner_sign=inner_sign, y_int_top=y_int_top, ox=ox, seam=seam, magnets=magnets,
                tongue=tongue, groove=groove, oled_glass=oled_glass, oled_win=oled_win, oled_pin_dir=pin_dir, oled_pose=pose,
                oled_glass_x=(gl_c - OLED["glass_l"]/2, gl_c + OLED["glass_l"]/2),
                outer=tr(g["O"]), outer_b=(g["OB"][0] - ox, g["OB"][1], g["OB"][2] - ox, g["OB"][3]),
                footprint=tr(g["cut"][side]).intersection(box(ob[0] - 5, ob[1] - 5, ob[2] + 5, ob[3] + 5)))

# ---- op list (backend independent) -----------------------------------------
# ('add'|'sub', 'poly', shapely_polygon, z0, z1)
# ('add'|'sub', 'cyl', (x, y, r), z0, z1)
# ('add'|'sub', 'box', (x0, y0, x1, y1), z0, z1)
# ('add', 'skin', dict(b, r, prof), z0, z1)    lofted rounded-rectangle solid; ('int', ...) intersects
# ('add', 'hull', [(x, y, z), ...], z0, z1)  convex hull of the points
def shell_ops(h):
    z_plate0 = H_TOTAL - PLATE_T
    ops = []
    # outer skin: the whole joined board lofted as one smooth solid (rounded top and bottom edges), cut to this half
    ops.append(("add", "skin", dict(b=h["outer_b"], r=CORNER_R, prof=edge_profile()), 0.0, H_TOTAL))
    ops.append(("int", "poly", h["footprint"], -1.0, H_TOTAL + 1.0))
    ops.append(("sub", "poly", h["cavity"], -1.0, z_plate0))
    # OLED bezel seat: a slot through the deck for the module's lower half, and two peg holes
    o = h["comp"]["oled"]
    ops.append(("sub", "box", (o["cx"] - o["w"]/2 - 0.3, o["cy"] - o["h"]/2 - 0.3, o["cx"] + o["w"]/2 + 0.3, o["cy"] + o["h"]/2 + 0.3), z_plate0 - 0.5, H_TOTAL + 1.0))
    for (px, py) in bezel_pegs(h):
        ops.append(("sub", "cyl", (px, py, PEG_HOLE_R), z_plate0 - 0.5, H_TOTAL + 1.0))
    for (x, y) in h["posts"]:
        ops.append(("add", "cyl", (x, y, POST_D/2), BASE_T, z_plate0 + 0.2))
    for (x, y) in h["posts"]:
        ops.append(("sub", "cyl", (x, y, INSERT_D/2), BASE_T - 0.01, BASE_T + INSERT_DEPTH))
    for p in h["holes"] + h["stabs"]:
        ops.append(("sub", "poly", p, z_plate0 - 0.5, H_TOTAL + 0.5))
    y_out = h["bounds"][3]
    # seam hardware: magnet pockets in the seam walls, tongue (right) and groove (left) above them
    sgn = 1 if h["side"] == "R" else -1       # pocket digs away from the seam face
    for m in h["magnets"]:
        x0 = m["x"] - 0.25 if sgn == 1 else m["x"] - MAG_POCKET_DEPTH
        x1 = m["x"] + MAG_POCKET_DEPTH if sgn == 1 else m["x"] + 0.25
        ops.append(("sub", "prismX", teardrop(m["y"], MAG_Z, MAG_POCKET_R, 1.4), x0, x1))
    seamL, O = h["seam"], h["outer"]
    if h["side"] == "R":
        Oi = O.buffer(-TG_END_TONGUE, join_style=1)
        for z0, z1, hw in tg_slices(TONGUE_APEX):
            ops.append(("add", "poly", seamL.buffer(hw, cap_style=2, join_style=2).intersection(Oi), z0, z1))
    else:
        Oi = O.buffer(-TG_END_GROOVE, join_style=1)
        for z0, z1, hw in tg_slices(GROOVE_APEX):
            ops.append(("sub", "poly", seamL.buffer(hw, cap_style=2, join_style=2).intersection(Oi), z0, z1))
    for o in h["openings"]:
        if o.get("side_wall"):
            ob = h["bounds"]
            xa, xb = ((ob[0] - 0.5, ob[0] + WALL + 0.6) if h["side"] == "L" else (ob[2] - WALL - 0.6, ob[2] + 0.5))
            ops.append(("sub", "prismX", usb_slot_profile(o), xa, xb))
        elif o["kind"] == "power":
            ops.append(("sub", "box", (o["x"] - o["w"]/2, y_out - WALL - 0.5, o["x"] + o["w"]/2, y_out + 0.5),
                        o["zc"] - o["h"]/2, o["zc"] + o["h"]/2))
            on = -1 if h["side"] == "L" else 1            # slide toward the controller = ON (wire it that way)
            ops.append(("sub", "box", (o["x"] + on * (o["w"]/2 + 2.2) - 0.45, y_out - 0.4, o["x"] + on * (o["w"]/2 + 2.2) + 0.45, y_out + 0.5),
                        o["zc"] - 1.3, o["zc"] + 1.3))                                   # bar = ON
            ops.append(("sub", "cylY", (o["x"] - on * (o["w"]/2 + 2.2), o["zc"], 0.7), y_out - 0.4, y_out + 0.5))   # dot = OFF
        elif o["kind"] == "reset":
            ops.append(("sub", "prismY", teardrop(o["x"], o["zc"], o["w"] / 2, 0.6), y_out - WALL - 0.5, y_out + 0.5))
        else:
            ops.append(("sub", "box", (o["x"] - o["w"]/2, y_out - WALL - 0.5, o["x"] + o["w"]/2, y_out + 0.5),
                        o["zc"] - o["h"]/2, o["zc"] + o["h"]/2))
    return ops

USB_TOP_R, USB_BOT_C = 2.0, 1.5
def usb_slot_profile(o, n=10):
    """(y, z) outline of the USB-C opening: upper corners rounded, lower corners 45 degree chamfers (they face down
    while the shell prints upside down, so they must not be round)."""
    y0, y1 = o["y"] - o["w"] / 2, o["y"] + o["w"] / 2
    z0, z1 = o["zc"] - o["h"] / 2, o["zc"] + o["h"] / 2
    r, c = USB_TOP_R, USB_BOT_C
    pts = [(y0 + c, z0), (y1 - c, z0), (y1, z0 + c)]
    pts += [(y1 - r + r * math.cos(a), z1 - r + r * math.sin(a)) for a in np.linspace(0, math.pi / 2, n)]
    pts += [(y0 + r + r * math.cos(a), z1 - r + r * math.sin(a)) for a in np.linspace(math.pi / 2, math.pi, n)]
    pts += [(y0, z0 + c)]
    return pts

def teardrop(c, zc, r, flat, n=40):
    """Outline of a horizontal round hole as a teardrop: the circle, plus 45 degree flanks below it, cut off flat
    'flat' mm wide. It points down because the shell prints upside down, so in the printer it points up."""
    tip = zc - r * math.sqrt(2); zt = tip + flat / 2
    pts = [(c + r * math.sin(f), zc - r * math.cos(f)) for f in np.linspace(math.pi / 4, 2 * math.pi - math.pi / 4, n)]
    return pts + [(c - flat / 2, zt), (c + flat / 2, zt)]

def bezel_box(h):
    o, P = h["comp"]["oled"], h["oled_pose"]
    return (o["cx"] - o["w"]/2 - 0.2 - POD_WALL, P["y_f"], o["cx"] + o["w"]/2 + 0.2 + POD_WALL, P["y_b"])

def bezel_pegs(h):
    x0, y0, x1, y1 = bezel_box(h)
    return [(x0 + 0.75, (y0 + y1) / 2), (x1 - 0.75, (y0 + y1) / 2)]

def bezel_hull_points(h, n=12):
    """Outer shape of the OLED bezel as a point cloud whose convex hull is the pod: the rounded top face in the tilted
    plane, and the rounded footprint on the deck (wider than the top: the ends and the back slope down to it)."""
    from shapely.geometry import Polygon as SP
    P = h["oled_pose"]; sn = P["sn"]
    x0, y0, x1, y1 = bezel_box(h)
    zb = H_TOTAL
    pts = []
    top = SP([(x0, 0.0), (x1, 0.0), (x1, P["Ls"]), (x0, P["Ls"])])           # (x, s) on the top face
    top = top.buffer(-BEZEL_TOP_R, join_style=2).buffer(BEZEL_TOP_R, resolution=n)
    for x, s_ in top.exterior.coords[:-1]:
        y, z = sn(s_, 0.0)
        pts.append((x, y, z))
    hf, hb = P["z_f"] - zb, P["z_b"] - zb                                   # height above the deck, front and back
    y_rb = bezel_back_foot(h)
    foot = SP([(x0 - BEZEL_END_RUN * hf, y0), (x1 + BEZEL_END_RUN * hf, y0), (x1 + BEZEL_END_RUN * hb, y1),
               (x1, y_rb), (x0, y_rb), (x0 - BEZEL_END_RUN * hb, y1)])
    foot = foot.buffer(-BEZEL_BASE_R, join_style=2).buffer(BEZEL_BASE_R, resolution=n)
    for x, y in foot.exterior.coords[:-1]:
        pts.append((x, y, zb))
    return pts

def bezel_back_foot(h):
    """Where the bezel's back slope meets the deck: as far back as the flat deck allows, before the rounded edge."""
    P = h["oled_pose"]
    y_flat = h["bounds"][3] - soft(0.0, EDGE_R)
    y_rb = min(P["y_b"] + (P["z_b"] - H_TOTAL) / math.tan(math.radians(40.0)), y_flat - 0.8)
    back_deg = math.degrees(math.atan2(P["z_b"] - H_TOTAL, y_rb - P["y_b"]))
    assert back_deg >= BEZEL_BACK_MIN_DEG, f"bezel back slope {back_deg:.1f} deg is too shallow to print face-down"
    return y_rb

def bezel_footprint(h):
    """The bezel's outline on the deck (for drawings and checks)."""
    from shapely.geometry import MultiPoint
    return MultiPoint([(x, y) for x, y, z in bezel_hull_points(h) if abs(z - H_TOTAL) < 1e-9]).convex_hull

def bezel_ops(h):
    """The OLED bezel, in its assembled position. A tapered pod whose top is tilted toward you, with a 0.4 mm lip over
    the glass, a glass pocket and a PCB pocket open to the bottom (the module drops in from below)."""
    o, P = h["comp"]["oled"], h["oled_pose"]; sn = P["sn"]
    zb = H_TOTAL
    ops = [("add", "hull", bezel_hull_points(h), zb, P["z_b"])]
    for (px, py) in bezel_pegs(h):
        ops.append(("add", "cyl", (px, py, PEG_R), zb - PEG_L, zb + 0.01))
    def slab(s0, s1, n0, n1):
        return [sn(s0, n0), sn(s1, n0), sn(s1, n1), sn(s0, n1)]
    sA, sB = P["s0"], P["s0"] + OLED["pcb_w"] + 0.4
    nG = -(OLED["lip"] + OLED["glass_t"]); nP = nG - OLED["pcb_t"] - 0.1
    ops.append(("sub", "prismX", slab(sA, sB, nP - 8.0, nG + 0.01), o["cx"] - o["w"]/2 - 0.2, o["cx"] + o["w"]/2 + 0.2))   # PCB, open below
    gx0, gx1 = h["oled_glass_x"]; sc = (sA + sB) / 2
    ops.append(("sub", "prismX", slab(sc - OLED["glass_w"]/2 - 0.2, sc + OLED["glass_w"]/2 + 0.2, nG, -OLED["lip"]), gx0 - 0.2, gx1 + 0.2))   # glass
    wc = (gx0 + gx1) / 2
    ops.append(("sub", "prismX", slab(sc - OLED["win_w"]/2, sc + OLED["win_w"]/2, -OLED["lip"] - 0.1, 2.0), wc - OLED["win_l"]/2, wc + OLED["win_l"]/2))   # window
    return ops

def base_ops(h):
    plate = h["cavity"].buffer(-0.15, join_style=1)
    ops = [("add", "poly", plate, 0.0, BASE_T)]
    b = h["comp"]["batt"]                                 # battery pocket: the 5.1 mm cell drops 0.6 mm into the base
    ops.append(("sub", "poly", rect_poly(b["cx"], b["cy"], b["w"] + 0.8, b["h"] + 0.8), BASE_T - BATT["pocket"], BASE_T + 0.5))
    for (x, y) in h["posts"]:
        ops.append(("sub", "cyl", (x, y, SCREW_D/2), -0.5, BASE_T + 0.5))
        ops.append(("sub", "cone", (x, y, CSK_D/2, SCREW_D/2), 0.0, 1.1))   # countersink
    # four 8 mm rubber-foot recesses on the underside
    for fx, fy in feet(h):
        ops.append(("sub", "cyl", (fx, fy, 4.1), -0.5, 0.5))
    ops.append(("sub", "poly", base_label(h), -0.5, BASE_LABEL_DEPTH))   # name engraved underneath
    import tents                                            # hidden magnets for the tenting wedges, under 0.5 mm of skin
    for x, y in tents.magnets(h):
        ops.append(("sub", "cyl", (x, y, tents.MAG_R), BASE_T - tents.MAG_POCKET, BASE_T + 0.5))
    return ops

BASE_LABEL_DEPTH = 0.4

def base_label(h):
    """The half's name and side, engraved into the underside, read with the half turned over (mirrored in x), placed
    in the biggest clear area away from the screws, feet and the edge."""
    from shapely.affinity import scale as _sc, translate as _tr
    plate = h["cavity"].buffer(-0.15, join_style=1)
    keep_out = unary_union([Point(x, y).buffer(CSK_D / 2 + 1.5) for x, y in h["posts"]] +
                           [Point(x, y).buffer(4.1 + 1.5) for x, y in feet(h)])
    ok = plate.buffer(-3.0).difference(keep_out)
    big = engraving("AIR75" if h["side"] == "L" else "SPLIT", size=10.0)
    small = engraving("LEFT HALF" if h["side"] == "L" else "RIGHT HALF", size=3.6)
    bb, sb = big.bounds, small.bounds
    small = _tr(small, (bb[0] + bb[2]) / 2 - (sb[0] + sb[2]) / 2, bb[1] - 3.0 - sb[3])
    label = _sc(unary_union([big, small]), -1, 1, origin=(0, 0))      # seen from below
    lb = label.bounds
    label = _tr(label, -(lb[0] + lb[2]) / 2, -(lb[1] + lb[3]) / 2)
    best = None
    ob = h["bounds"]
    for x in np.arange(ob[0], ob[2], 2.0):
        for y in np.arange(ob[1], ob[3], 2.0):
            cand = _tr(label, x, y)
            if ok.contains(cand.envelope.buffer(1.0)):
                d = (x - (ob[0] + ob[2]) / 2) ** 2 + (y - (ob[1] + ob[3]) / 2) ** 2
                if best is None or d < best[0]:
                    best = (d, cand)
    assert best is not None, f"{h['side']}: no room for the base label"
    return best[1]

def feet(h):
    """Four 8 mm feet per half, as close to the corners as the base allows, clear of screws and the battery pocket."""
    plate = h["cavity"].buffer(-0.15, join_style=1)
    minx, miny, maxx, maxy = plate.bounds
    bad = unary_union([Point(x, y).buffer(POST_D / 2 + 4.5) for x, y in h["posts"]] +
                      [rect_poly(h["comp"]["batt"]["cx"], h["comp"]["batt"]["cy"], h["comp"]["batt"]["w"] + 9, h["comp"]["batt"]["h"] + 9)])
    ok = plate.buffer(-5.5).difference(bad)
    out = []
    for tx, ty in [(minx + 10, miny + 10), (maxx - 10, miny + 10), (minx + 10, maxy - 10), (maxx - 10, maxy - 10)]:
        best = None
        for x in np.arange(minx, maxx, 1.0):
            for y in np.arange(miny, maxy, 1.0):
                d = (x - tx) ** 2 + (y - ty) ** 2
                if (best is None or d < best[0]) and d < 60 ** 2 and ok.contains(Point(x, y)):
                    best = (d, float(x), float(y))
        if best: out.append((best[1], best[2]))
    return out

def engraving(text, size=7.0):
    """Text outline as shapely polygons (DejaVu Sans Bold), baseline at y=0."""
    from matplotlib.textpath import TextPath
    from matplotlib.font_manager import FontProperties
    tp = TextPath((0, 0), text, size=size, prop=FontProperties(family="DejaVu Sans", weight="bold"))
    polys = [Polygon(p) for p in tp.to_polygons() if len(p) >= 3]
    polys = [p.buffer(0) for p in polys if p.is_valid or p.buffer(0).area > 0]
    polys.sort(key=lambda p: -p.area)
    shapes = []                                     # even-odd: a ring inside an outer ring is a hole
    for p in polys:
        for i, s in enumerate(shapes):
            if s.contains(p):
                shapes[i] = s.difference(p); break
        else:
            shapes.append(p)
    return unary_union(shapes)

def fit_test_ops():
    """Small plate: one 1u switch hole, one 2u hole with stab cutouts. Print this before the full case."""
    ops = [("add", "poly", box(-14, -12, 56, 12), 0.0, PLATE_T)]
    ops.append(("sub", "poly", rect_poly(0, 0, SW_HOLE, SW_HOLE), -0.5, PLATE_T + 0.5))
    ox = 36.0
    ops.append(("sub", "poly", rect_poly(ox, 0, SW_HOLE, SW_HOLE), -0.5, PLATE_T + 0.5))
    for sgn in (-1, 1):
        ops.append(("sub", "poly", box(ox + sgn*STAB_DX - STAB_W/2, STAB_Y0, ox + sgn*STAB_DX + STAB_W/2, STAB_Y1),
                    -0.5, PLATE_T + 0.5))
    return ops

# ---- SuperMini nRF52840 pinout (component side up, USB-C at the "top" of the pinout card) ------------
# Same order as the Pro Micro / nice!nano v2 footprint. Card coords: x right, y toward USB, mm from board centre.
# 13 pads per side: the extra top pad on each side sits beside the USB-C (left GND, right BATTERY+).
SUPERMINI_LEFT  = ["GND", "D1 P0.06", "D0 P0.08", "GND", "GND", "D2 P0.17", "D3 P0.20", "D4 P0.22", "D5 P0.24",
                   "D6 P1.00", "D7 P0.11", "D8 P1.04", "D9 P1.06"]
SUPERMINI_RIGHT = ["B+", "RAW", "GND", "RST", "3V3", "D21 P0.31", "D20 P0.29", "D19 P0.02", "D18 P1.15",
                   "D15 P1.13", "D14 P1.11", "D16 P0.10", "D10 P0.09"]
SUPERMINI_END   = ["P1.01", "P1.02", "P1.07"]      # three pads near the antenna end
PITCH = 2.54

def supermini_card_pins():
    """Measured off the SuperMini pinout card: 13 pads per side at 2.54 mm, rows 15.24 mm apart, board 33 x 18."""
    pins = []
    for i in range(13):
        y = 15.24 - PITCH * i
        pins.append(dict(name=SUPERMINI_LEFT[i], cx=-7.62, cy=y, side="left", i=i))
        pins.append(dict(name=SUPERMINI_RIGHT[i], cx=7.62, cy=y, side="right", i=i))
    for j, n in enumerate(SUPERMINI_END):
        pins.append(dict(name=n, cx=-4.7 + PITCH * j, cy=-12.2, side="end", i=j))
    return pins

def mcu_pins(side):
    """Pin positions in the half's local coordinates. The USB end points at the outer side wall."""
    c = half(side)["comp"]["mcu"]
    out = []
    for p in supermini_card_pins():
        dx, dy = (-p["cy"], p["cx"]) if side == "L" else (p["cy"], -p["cx"])   # rotate card 90 deg CCW (L) / CW (R)
        out.append(dict(name=p["name"], x=c["cx"] + dx, y=c["cy"] + dy, card=(p["cx"], p["cy"]), row=p["side"], i=p["i"]))
    return out
