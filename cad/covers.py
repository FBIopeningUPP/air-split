"""Snap-on key covers: one per half, for carrying the keyboard in a bag.

A 1.6 mm top 1 mm above the keycaps (so no key is pressed and the board stays asleep), a skirt that hugs the case
wall, and four flexible snap tabs whose hooks follow the case's rounded bottom edge and catch under it. The top edge
has a 45 degree chamfer and the name is pressed into the top. A notch leaves the power switch and reset hole free.

Prints top face down with no supports: the chamfer and the hooks' faces are all 45 degrees or steeper, the slots and
the switch notch open upward on the bed. Built with OpenCascade (for the chamfer), meshed for the STL.
"""
import math
from shapely.geometry import box, Polygon
from shapely.affinity import translate, scale
from shapely.ops import unary_union
import geom as G

CLEAR = 0.25          # gap between the skirt and the case wall
WALL = 1.6            # skirt thickness
TOP = 1.6             # top thickness
HEAD = 1.0            # gap between the keycap tops and the underside of the top
CHAMFER = 1.2         # 45 degree chamfer on the top outer edge
SKIRT_Z = 1.0         # the skirt stops here (above the case's bottom round); only the tabs reach lower
TAB_W = 20.0          # snap tab width
SLOT_W = 0.8          # slots either side of a tab, so it can flex
SLOT_TOP = 11.0       # slots run up to here
HOOK_GAP = 0.05       # hooks stay this far off the case surface
NOTCH_TOP = 6.5       # power switch / reset notch in the back skirt
TEXT = {"L": "AIR75", "R": "SPLIT"}
TEXT_H, TEXT_DEPTH = 9.0, 0.5

def z_ceiling():
    return G.thickness()["cap_top"] + HEAD

def z_top():
    return z_ceiling() + TOP

def hook_profile():
    """(d, z) outline of a hook: d is the distance inward from the case wall. Its upper face follows the case's
    rounded bottom edge (HOOK_GAP away), its lower face is a 45 degree lead-in back to the skirt."""
    R = G.EDGE_RB
    pts = [(-CLEAR, R + CLEAR)]                     # 45 degrees from the skirt onto the curve: no flat ledge
    n = 12
    for i in range(n + 1):
        z = R * (1 - i / n)
        pts.append((G.soft(z, R) - HOOK_GAP, z))
    tip = G.soft(0.0, R) - HOOK_GAP
    pts.append((-CLEAR, -(tip + CLEAR)))           # 45 degree lead-in
    return pts

def z_bottom():
    return -(G.soft(0.0, G.EDGE_RB) - HOOK_GAP + CLEAR)

def wall_span(outline, y, inward):
    """x range of the straight part of the front (inward=+1) or back (inward=-1) wall."""
    line = outline.intersection(box(-1e3, y + inward * 0.02 - 1e-3, 1e3, y + inward * 0.02 + 1e-3))
    return line.bounds[0] + 6.0, line.bounds[2] - 6.0

def tabs(h):
    """[(wall, x0, x1)]: two tabs on the front wall, two on the back, clear of the switch notch."""
    ob = h["bounds"]
    out = []
    n0, n1 = notch_x(h)
    for wall, y, inward in (("front", ob[1], 1), ("back", ob[3], -1)):
        a, b = wall_span(h["outline"], y, inward)
        for f in (0.22, 0.78):
            c = a + (b - a) * f
            if wall == "back" and c + TAB_W / 2 + SLOT_W + 3 > n0 and c - TAB_W / 2 - SLOT_W - 3 < n1:
                c = n0 - TAB_W / 2 - SLOT_W - 4 if c < (n0 + n1) / 2 else n1 + TAB_W / 2 + SLOT_W + 4
            out.append((wall, c - TAB_W / 2, c + TAB_W / 2))
    return out

def notch_x(h):
    xs = [h["comp"]["slide"]["cx"], h["comp"]["rst"]["cx"]]
    return min(xs) - 7.5, max(xs) + 7.5

def name_polys(h):
    txt = G.engraving(TEXT[h["side"]], size=10.0)
    b = txt.bounds
    k = TEXT_H / (b[3] - b[1])
    txt = scale(txt, k, k, origin=(0, 0))
    b = txt.bounds
    ob = h["bounds"]
    cx, cy = (ob[0] + ob[2]) / 2, (ob[1] + ob[3]) / 2 - 8.0
    return translate(txt, cx - (b[0] + b[2]) / 2, cy - (b[1] + b[3]) / 2)

def cover_parts(h):
    """(body_ops, finish_ops): body_ops make the shell that gets chamfered, finish_ops cut and add the rest."""
    outline = h["outline"]
    outer = outline.buffer(CLEAR + WALL, join_style=1, resolution=6).simplify(0.02)
    # the right half's seam has the V tongue standing proud of the wall: leave room for it
    body_xy = outline.union(h["tongue"]) if h["side"] == "R" else outline
    inner = body_xy.buffer(CLEAR, join_style=1, resolution=6).simplify(0.02)
    zb, zc, zt = z_bottom(), z_ceiling(), z_top()
    body = [("add", "poly", outer, zb, zt)]          # chamfered while still a solid block, then hollowed
    ob = h["bounds"]
    tb = tabs(h)
    keep = []
    for wall, x0, x1 in tb:
        y = ob[1] if wall == "front" else ob[3]
        keep.append(box(x0, y - 6.0, x1, y + 6.0))
    fin = [("sub", "poly", inner, zb - 1.0, zc),
           ("sub", "poly", outer.buffer(3.0).difference(unary_union(keep)), zb - 1.0, SKIRT_Z)]
    for wall, x0, x1 in tb:
        y = ob[1] if wall == "front" else ob[3]
        for xa in (x0 - SLOT_W, x1):
            fin.append(("sub", "box", (xa, y - 6.0, xa + SLOT_W, y + 6.0), zb - 1.0, SLOT_TOP))
    n0, n1 = notch_x(h)
    fin.append(("sub", "box", (n0, ob[3] - 2.0, n1, ob[3] + 6.0), zb - 1.0, NOTCH_TOP))
    fin.append(("sub", "poly", name_polys(h), zt - TEXT_DEPTH, zt + 1.0))
    prof = hook_profile()
    for wall, x0, x1 in tb:
        if wall == "front":
            pts = [(ob[1] + d, z) for d, z in prof]
        else:
            pts = [(ob[3] - d, z) for d, z in prof]
        fin.append(("add", "prismX", pts, x0, x1))
    return body, fin
