"""Support check for the print-ready STLs. A face needs support when it points down more steeply than 45 degrees,
is not on the bed, and is not a short flat bridge. Flat down-facing patches narrower than 0.6 mm are layer steps
(the rounded edges, the V tongue), which every printer handles."""
import os, glob, numpy as np, trimesh
from shapely.geometry import Polygon
from shapely.ops import unary_union

from paths import PRINT as D
MAX_BRIDGE = 12.0

def analyse(path):
    m = trimesh.load(path)
    nz = m.face_normals[:, 2]
    zc = m.triangles_center[:, 2]
    off_bed = zc > 0.05
    steep = off_bed & (nz < -0.7072) & (nz > -0.999)          # sloped overhang steeper than 45 deg
    flat = off_bed & (nz <= -0.999)
    steep_area = float(m.area_faces[steep].sum())
    worst_bridge, worst_where = 0.0, None
    for z in np.unique(np.round(zc[flat], 3)):
        idx = np.where(flat & (np.abs(zc - z) < 1e-3))[0]
        P = unary_union([Polygon(m.triangles[i][:, :2]).buffer(1e-4) for i in idx])
        for p in getattr(P, "geoms", [P]):
            if p.area < 1e-3: continue
            # span = the narrowest way across: twice the largest inset that still leaves something
            lo, hi = 0.0, 30.0
            for _ in range(18):
                mid = (lo + hi) / 2
                (lo, hi) = (mid, hi) if not p.buffer(-mid).is_empty else (lo, mid)
            span = 2 * lo
            if span > worst_bridge:
                worst_bridge, worst_where = span, (round(p.centroid.x, 1), round(p.centroid.y, 1), round(float(z), 2))
    return steep_area, worst_bridge, worst_where

def run():
    out = []
    for f in sorted(glob.glob(os.path.join(D, "*.stl"))):
        n = os.path.basename(f)[:-4]
        a, br, wh = analyse(f)
        ok = a < 2.0 and br <= MAX_BRIDGE
        out.append((n, ok, f"steep overhang {a:.1f} mm2, widest flat bridge {br:.1f} mm" + (f" at {wh}" if wh else "")))
    return out

if __name__ == "__main__":
    for r in run(): print(r)
