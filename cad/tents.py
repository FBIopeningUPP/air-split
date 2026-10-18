"""Magnetic tenting wedges: one bar under the inner edge of each half (the seam side), in 5, 10 and 15 degrees.

Each wedge sockets over the half's two inner rubber feet (so it cannot slide), and two 5 x 1 mm magnets in its top face
pull on two magnets hidden in the base (in pockets on the base's inside face, under 0.5 mm of plastic). The half then
rests on its outer feet and the wedge, tilted by the wedge's angle about the outer edge of its outer feet.

Prints top face down with no supports: the foot sockets and magnet pockets are short bridges on the bed side.
"""
import math
import numpy as np
from shapely.geometry import Point, LineString
from shapely.ops import unary_union
import geom as G

ANGLES = (5, 10, 15)
FOOT_R = 4.0                     # 8 mm rubber feet
SOCKET_R, SOCKET_DEPTH = 4.4, 1.3
BAR_R = 12.0                     # the wedge is a stadium this far around the two inner feet
MAG_R, MAG_POCKET = 2.6, 1.1     # 5 x 1 mm discs
SKIN = G.BASE_T - MAG_POCKET     # plastic between the base magnet and the wedge magnet

def desk_z():
    """The rubber feet's underside, in the half's own frame."""
    return 0.5 - G.FOOT_T

def inner_outer(h):
    f = G.feet(h)
    xs = sorted({round(x, 3) for x, y in f})
    inner_x = max(xs) if h["side"] == "L" else min(xs)
    inner = [p for p in f if abs(p[0] - inner_x) < 1e-3]
    outer = [p for p in f if abs(p[0] - inner_x) >= 1e-3]
    return inner, outer

def pivot_x(h):
    """The half tips on the outer edge of its outer feet."""
    _, outer = inner_outer(h)
    return min(x for x, y in outer) - FOOT_R if h["side"] == "L" else max(x for x, y in outer) + FOOT_R

def sign(h):
    return 1 if h["side"] == "L" else -1          # direction from the pivot toward the inner edge

def footprint(h):
    inner, _ = inner_outer(h)
    return LineString(inner).buffer(BAR_R, resolution=24).intersection(h["outline"].buffer(-1.0))   # stays under the case

def magnets(h):
    """Two magnet spots inside the wedge, clear of the feet, screws and the battery pocket."""
    inner, _ = inner_outer(h)
    (x0, y0), (x1, y1) = sorted(inner, key=lambda p: p[1])
    fp = footprint(h).buffer(-(MAG_R + 2.0))
    b = h["comp"]["batt"]
    bad = unary_union([Point(x, y).buffer(G.CSK_D / 2 + MAG_R + 1.5) for x, y in h["posts"]] +
                      [Point(x, y).buffer(4.1 + MAG_R + 1.5) for x, y in G.feet(h)] +
                      [G.rect_poly(b["cx"], b["cy"], b["w"] + 0.8 + 2 * MAG_R + 3, b["h"] + 0.8 + 2 * MAG_R + 3)])
    ok = h["cavity"].buffer(-(MAG_R + 2.0)).intersection(fp).difference(bad)
    out = []
    for f in (0.3, 0.7):
        tx, ty = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
        cands = [(tx + dx, ty + dy) for dx in np.arange(-8, 8.1, 0.5) for dy in np.arange(-15, 15.1, 0.5)
                 if ok.contains(Point(tx + dx, ty + dy))]
        assert cands, f"{h['side']}: no room for a tenting magnet"
        out.append(min(cands, key=lambda p: (p[0] - tx) ** 2 + (p[1] - ty) ** 2))
    return out

def desk_plane(h, angle):
    """z of the desk under x, in the half's frame, when the half is tented by angle degrees."""
    xp, s, t = pivot_x(h), sign(h), math.tan(math.radians(angle))
    return lambda x: desk_z() - t * s * (x - xp)

def wedge_ops(h, angle):
    fp = footprint(h)
    dz = desk_plane(h, angle)
    b = fp.bounds
    zlow = min(dz(b[0]), dz(b[2])) - 2.0
    x0, x1 = b[0] - 5, b[2] + 5
    below = [(x0, dz(x0)), (x1, dz(x1)), (x1, zlow - 50), (x0, zlow - 50)]
    ops = [("add", "poly", fp, zlow, 0.0),
           ("sub", "prismY", below, b[1] - 5, b[3] + 5)]
    inner, _ = inner_outer(h)
    for x, y in inner:
        ops.append(("sub", "cyl", (x, y, SOCKET_R), -SOCKET_DEPTH, 1.0))
    for x, y in magnets(h):
        ops.append(("sub", "cyl", (x, y, MAG_R), -MAG_POCKET, 1.0))
    return ops

def lift(h, angle):
    """How high the wedge lifts the inner edge of the half (mm)."""
    ob = h["bounds"]
    edge = ob[2] if h["side"] == "L" else ob[0]
    return math.tan(math.radians(angle)) * abs(edge - pivot_x(h))
