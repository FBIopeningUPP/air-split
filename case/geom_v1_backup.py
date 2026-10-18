"""Parametric geometry for the split Air75 case. All units mm. Z up, table at z=0.

Every dimension marked ASSUMED comes from typical low-profile/MX-style values, not from a
datasheet. Print case/fit_test_plate.stl first and change the number here if it does not fit.
"""
import math
import numpy as np
from shapely.geometry import Polygon, box, Point
from shapely.ops import unary_union
from layout import build, U

# ---- case parameters -------------------------------------------------------
SW_HOLE   = 13.9    # ASSUMED KS-33 plate hole (square). Verify with the fit-test plate.
PLATE_T   = 1.2     # plate thickness (switch clips need ~1.2-1.5)
INTERIOR  = 5.2     # plate underside -> base top. ASSUMED: switch pins end <=4.0 below plate + wire room; battery is 4.5 tall
BASE_T    = 1.6
H_TOTAL   = BASE_T + INTERIOR + PLATE_T   # 8.0, table -> top of plate
WALL      = 1.6
MARGIN    = 3.2     # key cell edge -> outer wall
CLOSE_R   = 6.0     # fillet radius on concave outline corners
BAY_D     = 26.0    # back bay depth beyond the F-row cell edge (controller + battery live here)
STAB_DX   = 11.938  # ASSUMED: 2u plate-mount stabiliser spacing (MX standard)
STAB_W, STAB_H = 6.65, 12.3   # ASSUMED MX plate-mount stab cutout
STAB_Y0, STAB_Y1 = -5.85, 6.45
POST_D    = 5.0
INSERT_D, INSERT_DEPTH = 3.2, 3.5       # M2 x 4 brass heat-set insert
SCREW_D, CSK_D = 2.3, 4.4               # M2 countersunk through base
POSTS = {"L": 8, "R": 10}

# components (ghost sizes), all lie on the base
MCU    = dict(w=18.0, l=22.5, t=1.0, usb_w=9.0, usb_h=3.2)   # SuperMini nRF52840, USB-C toward back wall
BATT   = dict(l=38.0, w=8.0, t=4.5)                          # 120 mAh LiPo (WLY450838-style)
SLIDE  = dict(l=8.6, w=3.7, t=3.5)                           # slide power switch
USB_SLOT = dict(w=9.6, h=3.8)
PWR_SLOT = dict(w=5.2, h=2.4)
RST_HOLE = 3.0

def rect_poly(cx, cy, w, h):
    return box(cx - w/2, cy - h/2, cx + w/2, cy + h/2)

def half(side):
    keys = [k for k in build() if k["side"] == side]
    ox = min(k["x0"] for k in keys) * U
    for k in keys:
        k["X"] = k["cx"] * U - ox
        k["Y"] = -k["row"] * U
    cells = [rect_poly(k["X"], k["Y"], k["w"]*U, U) for k in keys]
    cellu = unary_union(cells)
    minx, miny, maxx, maxy = cellu.bounds
    top_edge = maxy                      # = row0 cell top
    bay = box(minx, top_edge - 1, maxx, top_edge + BAY_D - MARGIN)
    shape = unary_union([cellu, bay])
    outline = shape.buffer(MARGIN + CLOSE_R, join_style=1, resolution=24).buffer(-CLOSE_R, join_style=1, resolution=24)
    cavity = outline.buffer(-WALL, join_style=1, resolution=24)
    holes, stabs = [], []
    for k in keys:
        holes.append(rect_poly(k["X"], k["Y"], SW_HOLE, SW_HOLE))
        if k["w"] >= 2:
            for sgn in (-1, 1):
                stabs.append(box(k["X"] + sgn*STAB_DX - STAB_W/2, k["Y"] + STAB_Y0,
                                 k["X"] + sgn*STAB_DX + STAB_W/2, k["Y"] + STAB_Y1))
    # back-bay layout, measured from the inner (towards the other half) end of the outline
    ob = outline.bounds
    inner_sign = 1 if side == "L" else -1
    inner_x = ob[2] if side == "L" else ob[0]
    def xin(d): return inner_x - inner_sign * d
    y_int_top = ob[3] - WALL
    comp = {}
    mcu_y = y_int_top - 0.3 - MCU["l"]/2
    comp["mcu"]  = dict(cx=xin(17.0), cy=mcu_y, w=MCU["w"], h=MCU["l"])
    comp["batt"] = dict(cx=xin(53.0), cy=y_int_top - 6.0, w=BATT["l"], h=BATT["w"])
    comp["slide"]= dict(cx=xin(84.0), cy=y_int_top - SLIDE["w"]/2 - 0.1, w=SLIDE["l"], h=SLIDE["w"])
    rst_x = xin(30.0)
    comp["rst"]  = dict(cx=rst_x, cy=y_int_top - 2.5, w=4.6, h=4.6)
    # wall openings: (cx, z_center, w, h, kind)
    z_usb = BASE_T + MCU["t"] + MCU["usb_h"]/2
    openings = [
        dict(kind="usb",   x=comp["mcu"]["cx"],   zc=z_usb, w=USB_SLOT["w"], h=USB_SLOT["h"]),
        dict(kind="power", x=comp["slide"]["cx"], zc=BASE_T + 2.4, w=PWR_SLOT["w"], h=PWR_SLOT["h"]),
        dict(kind="reset", x=comp["rst"]["cx"],   zc=BASE_T + 2.0, w=RST_HOLE, h=RST_HOLE),
    ]
    # posts: farthest-first sampling on a grid of legal points
    keep = [rect_poly(k["X"], k["Y"], 14.6, 14.6) for k in keys] + stabs
    keep += [rect_poly(c["cx"], c["cy"], c["w"] + 1.2, c["h"] + 1.2) for c in comp.values()]
    keepu = unary_union(keep).buffer(POST_D/2 + 0.5)
    legal = cavity.buffer(-(POST_D/2 + 1.0)).difference(keepu)
    xs = np.arange(ob[0], ob[2], 1.0); ys = np.arange(ob[1], ob[3], 1.0)
    cand = [(x, y) for x in xs for y in ys if legal.contains(Point(x, y))]
    n = POSTS[side]
    chosen = [min(cand, key=lambda p: (p[0] - ob[0])**2 + (p[1] - ob[1])**2)]
    while len(chosen) < n:
        chosen.append(max(cand, key=lambda p: min((p[0]-q[0])**2 + (p[1]-q[1])**2 for q in chosen)))
    # sanity: components must not overlap each other, the switches, or the cavity wall
    names = list(comp)
    for i in range(len(names)):
        a = rect_poly(comp[names[i]]["cx"], comp[names[i]]["cy"], comp[names[i]]["w"], comp[names[i]]["h"])
        assert cavity.contains(a), f"{side}: {names[i]} outside cavity"
        for j in range(i + 1, len(names)):
            b = rect_poly(comp[names[j]]["cx"], comp[names[j]]["cy"], comp[names[j]]["w"], comp[names[j]]["h"])
            assert not a.intersects(b), f"{side}: {names[i]} overlaps {names[j]}"
        for p in holes:
            assert not a.intersects(p.buffer(0.5)), f"{side}: {names[i]} overlaps a switch hole"
    return dict(side=side, keys=keys, cells=cells, holes=holes, stabs=stabs, outline=outline,
                cavity=cavity, comp=comp, openings=openings, posts=chosen, bounds=ob,
                inner_sign=inner_sign, y_int_top=y_int_top)

# ---- op list (backend independent) -----------------------------------------
# ('add'|'sub', 'poly', shapely_polygon, z0, z1)
# ('add'|'sub', 'cyl', (x, y, r), z0, z1)
# ('add'|'sub', 'box', (x0, y0, x1, y1), z0, z1)
def shell_ops(h):
    z_plate0 = H_TOTAL - PLATE_T
    ops = [("add", "poly", h["outline"], 0.0, H_TOTAL),
           ("sub", "poly", h["cavity"], -1.0, z_plate0)]
    for (x, y) in h["posts"]:
        ops.append(("add", "cyl", (x, y, POST_D/2), BASE_T, z_plate0 + 0.2))
    for (x, y) in h["posts"]:
        ops.append(("sub", "cyl", (x, y, INSERT_D/2), BASE_T - 0.01, BASE_T + INSERT_DEPTH))
    for p in h["holes"] + h["stabs"]:
        ops.append(("sub", "poly", p, z_plate0 - 0.5, H_TOTAL + 0.5))
    y_out = h["bounds"][3]
    for o in h["openings"]:
        if o["kind"] == "reset":
            ops.append(("sub", "cyl", None, None, None))  # placeholder replaced below
            ops.pop()
            ops.append(("sub", "cylY", (o["x"], o["zc"], o["w"]/2), y_out - WALL - 0.5, y_out + 0.5))
        else:
            ops.append(("sub", "box", (o["x"] - o["w"]/2, y_out - WALL - 0.5, o["x"] + o["w"]/2, y_out + 0.5),
                        o["zc"] - o["h"]/2, o["zc"] + o["h"]/2))
    return ops

def base_ops(h):
    plate = h["cavity"].buffer(-0.15, join_style=1)
    ops = [("add", "poly", plate, 0.0, BASE_T)]
    for (x, y) in h["posts"]:
        ops.append(("sub", "cyl", (x, y, SCREW_D/2), -0.5, BASE_T + 0.5))
        ops.append(("sub", "cone", (x, y, CSK_D/2, SCREW_D/2), 0.0, 1.1))   # countersink
    # four 8 mm rubber-foot recesses on the underside
    minx, miny, maxx, maxy = plate.bounds
    for fx, fy in [(minx+12, miny+12), (maxx-12, miny+12), (minx+12, maxy-12), (maxx-12, maxy-12)]:
        if plate.contains(Point(fx, fy).buffer(5)):
            ops.append(("sub", "cyl", (fx, fy, 4.1), -0.5, 0.5))
    return ops

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
