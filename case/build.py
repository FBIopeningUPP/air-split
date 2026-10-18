"""Build STL (manifold3d) and STEP (OpenCascade) files from the op lists in geom.py."""
import os, sys, math
import numpy as np
import trimesh
import manifold3d as m
from shapely.geometry import Polygon, MultiPolygon
from shapely.geometry.polygon import orient
import geom as G

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
os.makedirs(os.path.join(OUT, "stl"), exist_ok=True)
os.makedirs(os.path.join(OUT, "step"), exist_ok=True)

def polys(p):
    return list(p.geoms) if isinstance(p, MultiPolygon) else [p]

# ---------------- manifold backend ----------------
def skin_mesh(arg):
    """Vertices and triangles of a lofted rounded-rectangle solid: one ring per (z, inset) in arg['prof']."""
    rings = [np.array(G.rrect_ring(arg["b"], arg["r"], d), dtype=float) for _, d in arg["prof"]]
    n, k = len(rings[0]), len(rings)
    V = np.vstack([np.column_stack([r, np.full(n, z)]) for r, (z, _) in zip(rings, arg["prof"])])
    cb, ct = rings[0].mean(axis=0), rings[-1].mean(axis=0)
    V = np.vstack([V, [[cb[0], cb[1], arg["prof"][0][0]], [ct[0], ct[1], arg["prof"][-1][0]]]])
    ib, it = k * n, k * n + 1
    F = []
    for j in range(k - 1):
        a, b = j * n, (j + 1) * n
        for i in range(n):
            i2 = (i + 1) % n
            F += [(a + i, a + i2, b + i2), (a + i, b + i2, b + i)]
    for i in range(n):
        i2 = (i + 1) % n
        F += [(ib, i2, i), (it, (k - 1) * n + i, (k - 1) * n + i2)]
    return V, np.array(F, dtype=np.uint32)

def m_prim(kind, arg, z0, z1):
    if kind == "hull":
        return m.Manifold.hull_points([tuple(map(float, q)) for q in arg])
    if kind == "skin":
        V, F = skin_mesh(arg)
        return m.Manifold(m.Mesh(vert_properties=V.astype(np.float32), tri_verts=F))
    if kind == "poly":
        rings = []
        for p in polys(arg):
            p = orient(p, 1.0)
            rings.append(np.array(p.exterior.coords[:-1], dtype=float))
            for i in p.interiors:
                rings.append(np.array(i.coords[:-1], dtype=float))
        cs = m.CrossSection(rings)
        return m.Manifold.extrude(cs, z1 - z0).translate((0, 0, z0))
    if kind == "cyl":
        x, y, r = arg
        return m.Manifold.cylinder(z1 - z0, r, r, 48).translate((x, y, z0))
    if kind == "cone":
        x, y, r0, r1 = arg
        return m.Manifold.cylinder(z1 - z0, r0, r1, 48).translate((x, y, z0))
    if kind == "cylY":
        x, zc, r = arg
        return m.Manifold.cylinder(z1 - z0, r, r, 48).rotate((-90, 0, 0)).translate((x, z0, zc))
    if kind == "cylX":
        y, zc, r = arg
        return m.Manifold.cylinder(z1 - z0, r, r, 48).rotate((0, 90, 0)).translate((z0, y, zc))
    if kind == "box":
        x0, y0, x1, y1 = arg
        return m.Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))
    if kind == "prismY":          # polygon in the (x, z) plane, extruded along y from z0 to z1 (here: y0, y1)
        from shapely.geometry import Polygon as _P
        p = orient(_P(arg), 1.0)
        uv = np.array([(x, z) for x, z in p.exterior.coords[:-1]], dtype=float)
        return m.Manifold.extrude(m.CrossSection([uv]), z1 - z0).rotate((90, 0, 0)).translate((0, z1, 0))
    if kind == "prismX":          # polygon in the (y, z) plane, extruded along x from z0 to z1 (here: x0, x1)
        from shapely.geometry import Polygon as _P
        p = orient(_P(arg), 1.0)
        uv = np.array([(-z, y) for y, z in p.exterior.coords[:-1]], dtype=float)
        return m.Manifold.extrude(m.CrossSection([uv]), z1 - z0).rotate((0, 90, 0)).translate((z0, 0, 0))
    raise ValueError(kind)

def run_manifold(ops):
    res = None
    for op, kind, arg, z0, z1 in ops:
        t = m_prim(kind, arg, z0, z1)
        if res is None:
            assert op == "add"; res = t
        else:
            res = res + t if op == "add" else (res ^ t if op == "int" else res - t)
    return res

def to_trimesh(man):
    mesh = man.to_mesh()
    return trimesh.Trimesh(vertices=np.array(mesh.vert_properties)[:, :3], faces=np.array(mesh.tri_verts), process=True)

# ---------------- OpenCascade backend ----------------
from OCP.gp import gp_Pnt, gp_Vec, gp_Ax2, gp_Dir, gp_Trsf
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace, BRepBuilderAPI_Transform
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism, BRepPrimAPI_MakeCylinder, BRepPrimAPI_MakeCone, BRepPrimAPI_MakeBox
from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse, BRepAlgoAPI_Cut, BRepAlgoAPI_Common
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire
from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
from OCP.GC import GC_MakeArcOfCircle
from OCP.collections import List_TopoDS_Shape as TopTools_ListOfShape
from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp

def wire(coords):
    mk = BRepBuilderAPI_MakePolygon()
    for x, y in coords[:-1]:
        mk.Add(gp_Pnt(float(x), float(y), 0.0))
    mk.Close()
    return mk.Wire()

def rrect_wire(b, r, inset, z):
    """A rounded rectangle as 4 lines and 4 true arcs at height z (so the STEP skin is made of real curved faces)."""
    x0, y0, x1, y1 = b[0] + inset, b[1] + inset, b[2] - inset, b[3] - inset
    rr = r - inset
    P = lambda x, y: gp_Pnt(float(x), float(y), float(z))
    corners = [(x1 - rr, y1 - rr, 0), (x0 + rr, y1 - rr, 90), (x0 + rr, y0 + rr, 180), (x1 - rr, y0 + rr, 270)]
    arcs = []
    for cx, cy, a0 in corners:
        a, am, a1 = (math.radians(a0 + d) for d in (0, 45, 90))
        p0, pm, p1 = (P(cx + rr * math.cos(t), cy + rr * math.sin(t)) for t in (a, am, a1))
        arcs.append((p0, p1, BRepBuilderAPI_MakeEdge(GC_MakeArcOfCircle(p0, pm, p1).Value()).Edge()))
    mw = BRepBuilderAPI_MakeWire()
    for i in range(4):                                  # arc, then the straight side to the next arc
        mw.Add(arcs[i][2])
        mw.Add(BRepBuilderAPI_MakeEdge(arcs[i][1], arcs[(i + 1) % 4][0]).Edge())
    return mw.Wire()

def hull_solid(points):
    """Convex hull as an OpenCascade solid: the hull's triangles sewn into a shell, then coplanar faces merged."""
    from scipy.spatial import ConvexHull
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid
    from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
    from OCP.TopoDS import TopoDS
    P = np.array(points, dtype=float)
    hull = ConvexHull(P)
    sew = BRepBuilderAPI_Sewing(1e-6)
    c = P.mean(axis=0)
    for tri, eq in zip(hull.simplices, hull.equations):
        a, b, d = P[tri[0]], P[tri[1]], P[tri[2]]
        if np.dot(np.cross(b - a, d - a), eq[:3]) < 0:      # wind each triangle with its normal pointing out
            b, d = d, b
        poly = BRepBuilderAPI_MakePolygon(gp_Pnt(*a), gp_Pnt(*b), gp_Pnt(*d), True)
        sew.Add(BRepBuilderAPI_MakeFace(poly.Wire(), True).Face())
    sew.Perform()
    solid = BRepBuilderAPI_MakeSolid(TopoDS.Shell(sew.SewedShape())).Solid()
    u = ShapeUpgrade_UnifySameDomain(solid, True, True, False); u.Build()
    return u.Shape()

def o_prim(kind, arg, z0, z1):
    if kind == "hull":
        return hull_solid(arg)
    if kind == "skin":
        ts = BRepOffsetAPI_ThruSections(True, True, 1e-6)     # solid, ruled between the rings
        for z, d in arg["prof"]:
            ts.AddWire(rrect_wire(arg["b"], arg["r"], d, z))
        ts.CheckCompatibility(False)
        ts.Build()
        return ts.Shape()
    if kind == "poly":
        shapes = []
        for p in polys(arg):
            p = orient(p, 1.0)
            mf = BRepBuilderAPI_MakeFace(wire(list(p.exterior.coords)), True)
            for i in p.interiors:
                mf.Add(wire(list(i.coords)))
            face = mf.Face()
            prism = BRepPrimAPI_MakePrism(face, gp_Vec(0, 0, z1 - z0)).Shape()
            tr = gp_Trsf(); tr.SetTranslation(gp_Vec(0, 0, z0))
            shapes.append(BRepBuilderAPI_Transform(prism, tr, True).Shape())
        out = shapes[0]
        for s in shapes[1:]:
            out = BRepAlgoAPI_Fuse(out, s).Shape()
        return out
    if kind == "cyl":
        x, y, r = arg
        return BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x, y, z0), gp_Dir(0, 0, 1)), r, z1 - z0).Shape()
    if kind == "cone":
        x, y, r0, r1 = arg
        return BRepPrimAPI_MakeCone(gp_Ax2(gp_Pnt(x, y, z0), gp_Dir(0, 0, 1)), r0, r1, z1 - z0).Shape()
    if kind == "cylY":
        x, zc, r = arg
        return BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x, z0, zc), gp_Dir(0, 1, 0)), r, z1 - z0).Shape()
    if kind == "cylX":
        y, zc, r = arg
        return BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(z0, y, zc), gp_Dir(1, 0, 0)), r, z1 - z0).Shape()
    if kind == "box":
        x0, y0, x1, y1 = arg
        return BRepPrimAPI_MakeBox(gp_Pnt(x0, y0, z0), x1 - x0, y1 - y0, z1 - z0).Shape()
    if kind == "prismY":
        poly = BRepBuilderAPI_MakePolygon()
        for x, z in arg:
            poly.Add(gp_Pnt(x, z0, z))
        poly.Close()
        face = BRepBuilderAPI_MakeFace(poly.Wire(), True).Face()
        return BRepPrimAPI_MakePrism(face, gp_Vec(0, z1 - z0, 0)).Shape()
    if kind == "prismX":
        poly = BRepBuilderAPI_MakePolygon()
        for y, z in arg:
            poly.Add(gp_Pnt(z0, y, z))
        poly.Close()
        face = BRepBuilderAPI_MakeFace(poly.Wire(), True).Face()
        return BRepPrimAPI_MakePrism(face, gp_Vec(z1 - z0, 0, 0)).Shape()
    raise ValueError(kind)

def run_occ(ops, res=None):
    i = 0
    while i < len(ops):
        op = ops[i][0]
        j = i
        tools = []
        while j < len(ops) and ops[j][0] == op:
            _, kind, arg, z0, z1 = ops[j]
            tools.append(o_prim(kind, arg, z0, z1)); j += 1
        if res is None:
            res = tools[0]
            if len(tools) > 1:
                args = TopTools_ListOfShape(); args.Append(res)
                tl = TopTools_ListOfShape()
                for t in tools[1:]: tl.Append(t)
                f = BRepAlgoAPI_Fuse(); f.SetArguments(args); f.SetTools(tl); f.Build(); res = f.Shape()
        else:
            args = TopTools_ListOfShape(); args.Append(res)
            tl = TopTools_ListOfShape()
            for t in tools: tl.Append(t)
            b = BRepAlgoAPI_Fuse() if op == "add" else (BRepAlgoAPI_Common() if op == "int" else BRepAlgoAPI_Cut())
            b.SetArguments(args); b.SetTools(tl); b.Build()
            res = b.Shape()
        i = j
    return res

def write_step(shape, path):
    w = STEPControl_Writer(); w.Transfer(shape, STEP_AS_IS); w.Write(path)

STEP_AS_IS = STEPControl_AsIs

def occ_volume(shape):
    p = GProp_GProps(); BRepGProp.VolumeProperties_s(shape, p); return p.Mass()

MESHES = {}

def make(name, ops, step=True):
    man = run_manifold(ops)
    tm = to_trimesh(man)
    tm.export(os.path.join(OUT, "stl", name + ".stl"))
    MESHES[name] = tm
    info = dict(name=name, watertight=bool(tm.is_watertight), vol_mm3=float(man.volume()),
                bbox=[round(v, 2) for v in (tm.bounds[1] - tm.bounds[0])])
    if step:
        sh = run_occ(ops)
        write_step(sh, os.path.join(OUT, "step", name + ".step"))
        info["step_valid"] = bool(BRepCheck_Analyzer(sh).IsValid())
        info["step_vol_mm3"] = float(occ_volume(sh))
    return info

def chamfer_top(shape, z, d):
    """45 degree chamfer of size d on every edge of the flat top face at height z."""
    from OCP.BRepFilletAPI import BRepFilletAPI_MakeChamfer
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Plane
    from OCP.TopoDS import TopoDS
    mk = BRepFilletAPI_MakeChamfer(shape)
    n = 0
    ex = TopExp_Explorer(shape, TopAbs_FACE)
    while ex.More():
        f = TopoDS.Face(ex.Current())
        srf = BRepAdaptor_Surface(f)
        if srf.GetType() == GeomAbs_Plane:
            pl = srf.Plane()
            if abs(abs(pl.Axis().Direction().Z()) - 1) < 1e-9 and abs(pl.Location().Z() - z) < 1e-6:
                ee = TopExp_Explorer(f, TopAbs_EDGE)
                while ee.More():
                    mk.Add(d, TopoDS.Edge(ee.Current())); n += 1
                    ee.Next()
        ex.Next()
    mk.Build()
    assert mk.IsDone() and n > 0, "chamfer failed"
    return mk.Shape()

def make_cover(name, h):
    """Key cover: built in OpenCascade (the chamfer follows the whole outline), meshed for the STL."""
    import covers as CV
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.StlAPI import StlAPI_Writer
    body, fin = CV.cover_parts(h)
    sh = chamfer_top(run_occ(body), CV.z_top(), CV.CHAMFER)
    sh = run_occ(fin, res=sh)
    write_step(sh, os.path.join(OUT, "step", name + ".step"))
    BRepMesh_IncrementalMesh(sh, 0.01, False, 0.15, True)
    tmp = os.path.join(OUT, "stl", name + ".tmp.stl")
    StlAPI_Writer().Write(sh, tmp)
    tm = trimesh.load(tmp, process=True)
    os.remove(tmp)
    tm.merge_vertices(); tm.fix_normals()
    tm.export(os.path.join(OUT, "stl", name + ".stl"))
    MESHES[name] = tm
    return dict(name=name, watertight=bool(tm.is_watertight), vol_mm3=float(tm.volume),
                bbox=[round(v, 2) for v in (tm.bounds[1] - tm.bounds[0])],
                step_valid=bool(BRepCheck_Analyzer(sh).IsValid()))

def print_pose(name, tm):
    """Copy of a part turned the way it should sit on the bed, resting on z = 0, centred on x/y = 0."""
    t = tm.copy()
    if name.endswith("_shell") or name.endswith("_cover") or "_tent_" in name:   # plate / top face down: it gets the smooth bed finish
        t.apply_transform(trimesh.transformations.rotation_matrix(math.pi, [0, 1, 0]))
    elif name.endswith("_oled_bezel"):                 # window face down: tilt the slope flat, then flip
        th = math.radians(G.OLED_TILT)
        t.apply_transform(trimesh.transformations.rotation_matrix(-th, [1, 0, 0]))
        t.apply_transform(trimesh.transformations.rotation_matrix(math.pi, [0, 1, 0]))
    c = t.bounds.mean(axis=0)
    t.apply_translation([-c[0], -c[1], -t.bounds[0][2]])
    return t

def write_print_ready():
    d = os.path.join(OUT, "stl", "print_ready"); os.makedirs(d, exist_ok=True)
    for name, tm in MESHES.items():
        print_pose(name, tm).export(os.path.join(d, name + ".stl"))

if __name__ == "__main__":
    results = []
    for s in "LR":
        h = G.half(s)
        nm = {"L": "left", "R": "right"}[s]
        results.append(make(f"{nm}_shell", G.shell_ops(h)))
        results.append(make(f"{nm}_base", G.base_ops(h)))
        results.append(make(f"{nm}_oled_bezel", G.bezel_ops(h)))
        results.append(make_cover(f"{nm}_cover", h))
        import tents
        for a in tents.ANGLES:
            results.append(make(f"{nm}_tent_{a}", tents.wedge_ops(h, a)))
    results.append(make("fit_test_plate", G.fit_test_ops()))
    write_print_ready()
    for r in results:
        print(r)
