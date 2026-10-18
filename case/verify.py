"""Geometry checks on the built meshes. Run after build.py."""
import numpy as np, trimesh, geom as G, build as B

hL, hR = G.half("L"), G.half("R")
OUT = "../out/stl/"
shL, shR = trimesh.load(OUT + "left_shell.stl"), trimesh.load(OUT + "right_shell.stl")
bsL, bsR = trimesh.load(OUT + "left_base.stl"), trimesh.load(OUT + "right_base.stl")
bad = 0
def check(name, ok):
    global bad
    bad += (not ok)
    print(("OK  " if ok else "BAD ") + name)

# 1. watertight
for n, m in (("left shell", shL), ("right shell", shR), ("left base", bsL), ("right base", bsR)):
    check(f"{n} watertight", m.is_watertight)

# 2. joined halves do not interpenetrate
mL = B.run_manifold(G.shell_ops(hL)); mR = B.run_manifold(G.shell_ops(hR)).translate((hR["ox"], 0, 0))
check(f"joined shells overlap {(mL ^ mR).volume():.4f} mm3", (mL ^ mR).volume() < 1e-6)
bL = B.run_manifold(G.base_ops(hL)); bR = B.run_manifold(G.base_ops(hR)).translate((hR["ox"], 0, 0))
check("joined bases do not overlap", (bL ^ bR).volume() < 1e-6)

# 3. outline of the joined board
g = G._global()
check("outline is one clean polygon", g["O"].geom_type == "Polygon" and len(g["O"].interiors) == 0)
check(f"seam is a single line ({g['seam'].geom_type})", g["seam"].geom_type == "LineString")

# 4. magnet pockets
for mA, mB in zip(hL["magnets"], hR["magnets"]):
    xl, xr = mA["x"], mB["x"] + hR["ox"]
    pl = np.array([[xl - 0.5, mA["y"], G.MAG_Z]]); pr = np.array([[mB["x"] + 0.5, mB["y"], G.MAG_Z]])
    sl = np.array([[xl - G.MAG_POCKET_DEPTH - 0.4, mA["y"], G.MAG_Z]]); sr = np.array([[mB["x"] + G.MAG_POCKET_DEPTH + 0.4, mB["y"], G.MAG_Z]])
    ok = (not shL.contains(pl)[0]) and (not shR.contains(pr)[0]) and shL.contains(sl)[0] and shR.contains(sr)[0] \
         and abs((xr - xl) - G.SEAM_GAP) < 1e-6
    check(f"magnet pocket pair at y={mA['y']:.1f} aligned, open, walled", ok)

# 5. every component, hole, post, opening
for s, h, sh, bs in (("L", hL, shL, bsL), ("R", hR, shR, bsR)):
    yo = h["bounds"][3]
    for o in h["openings"]:
        if o.get("side_wall"):
            px = h["bounds"][0] + 0.8 if s == "L" else h["bounds"][2] - 0.8
            p, q = [px, o["y"], o["zc"]], [px, o["y"], o["zc"] + o["h"]/2 + 0.6]
        else:
            p, q = [o["x"], yo - 0.8, o["zc"]], [o["x"], yo - 0.8, o["zc"] + o["h"]/2 + 0.8]
        check(f"{s} {o['kind']} opening open", not sh.contains(np.array([p]))[0])
        check(f"{s} {o['kind']} wall solid above", sh.contains(np.array([q]))[0])
    k = h["keys"][5]
    check(f"{s} switch hole empty", not sh.contains(np.array([[k["X"], k["Y"], G.H_TOTAL - 0.6]]))[0])
    check(f"{s} plate solid beside hole", sh.contains(np.array([[k["X"] + G.SW_HOLE/2 + 1.0, k["Y"], G.H_TOTAL - 0.6]]))[0])
    x, y = h["posts"][0]
    check(f"{s} insert hole empty", not sh.contains(np.array([[x, y, G.BASE_T + 2.0]]))[0])
    check(f"{s} post above insert solid", sh.contains(np.array([[x, y, G.BASE_T + G.INSERT_DEPTH + 0.6]]))[0])
    check(f"{s} base screw hole empty", not bs.contains(np.array([[x, y, 0.3]]))[0])
    c = h["comp"]["batt"]
    check(f"{s} battery bay is empty", not sh.contains(np.array([[c["cx"], c["cy"], 3.0]]))[0])
    # every post screw hole must land inside the base outline
    check(f"{s} all {len(h['posts'])} posts inside base", all(bs.bounds[0][0] < px < bs.bounds[1][0] for px, _ in h["posts"]))

# 6b. OLED bezel: window open, lip solid, pockets open, sits on the deck without touching the shell; rounded edges
import math
for s_, h, sh in (("L", hL, shL), ("R", hR, shR)):
    nm = "left" if s_ == "L" else "right"
    bz = trimesh.load(OUT + f"{nm}_oled_bezel.stl")
    check(f"{s_} OLED bezel watertight", bz.is_watertight)
    P = h["oled_pose"]; o = h["comp"]["oled"]; gx0, gx1 = h["oled_glass_x"]; wc = (gx0 + gx1) / 2
    sc = P["s0"] + (G.OLED["pcb_w"] + 0.4) / 2
    y, z = P["sn"](sc, -0.2); check(f"{s_} OLED window open", not bz.contains(np.array([[wc, y, z]]))[0])
    y, z = P["sn"](sc + G.OLED["glass_w"] / 2 - 0.5, -0.2); check(f"{s_} OLED lip over the glass edge", bz.contains(np.array([[wc, y, z]]))[0])
    y, z = P["sn"](sc, -G.OLED["lip"] - 0.8); check(f"{s_} OLED glass pocket open", not bz.contains(np.array([[wc, y, z]]))[0])
    y, z = P["sn"](sc, -3.0); check(f"{s_} OLED PCB pocket open to the bottom", not bz.contains(np.array([[o["cx"], y, max(z, G.H_TOTAL + 0.1)]]))[0])
    y, z = P["sn"](P["s0"] / 2, -0.8); check(f"{s_} bezel front wall solid", bz.contains(np.array([[o["cx"], y, z]]))[0])
    check(f"{s_} OLED top is tilted ({G.OLED_TILT} deg, {P['z_f']:.1f} -> {P['z_b']:.1f} mm)", P["z_b"] > P["z_f"] + 3)
    mb = B.run_manifold(G.bezel_ops(h)); ms = B.run_manifold(G.shell_ops(h))
    check(f"{s_} bezel and shell do not overlap ({(mb ^ ms).volume():.4f} mm3)", (mb ^ ms).volume() < 1e-6)
    check(f"{s_} bezel sits on the deck (bottom at {bz.bounds[0][2] + G.PEG_L:.2f} mm)", abs(bz.bounds[0][2] + G.PEG_L - G.H_TOTAL) < 1e-3)
    y, z = P["sn"](sc, -2.6); check(f"{s_} deck slot open under the module", not sh.contains(np.array([[o["cx"], y, G.H_TOTAL - 0.6]]))[0])
    for (px, py) in G.bezel_pegs(h):
        check(f"{s_} peg hole open and peg present", (not sh.contains(np.array([[px, py, G.H_TOTAL - 0.6]]))[0]) and bz.contains(np.array([[px, py, G.H_TOTAL - 0.5]]))[0])
    # the bezel's outer wall is closed all the way round near the deck (the pocket must not break out of the back)
    from shapely.geometry import Polygon as _SP
    closed = True
    for zz in np.arange(G.H_TOTAL + 0.02, P["z_f"] - 0.02, 0.1):          # below the tilted top face
        sec = bz.section(plane_origin=[0, 0, zz], plane_normal=[0, 0, 1])
        if sec is None: continue
        for poly in sec.to_2D()[0].polygons_full:
            outer = _SP(poly.exterior)
            if outer.convex_hull.area - outer.area > 0.05: closed = False
    check(f"{s_} bezel wall closed all round near the deck (no slit at the back)", closed)
    fp = G.bezel_footprint(h); y_flat = h["bounds"][3] - G.soft(0.0, G.EDGE_R)
    check(f"{s_} bezel footprint stays on the flat deck (back foot {fp.bounds[3]:.2f} < {y_flat:.2f} mm)", fp.bounds[3] < y_flat - 0.5)
    ob = h["bounds"]; xm = (ob[0] + ob[2]) / 2
    check(f"{s_} top edge rounded ({G.EDGE_R} mm)", not sh.contains(np.array([[xm, ob[1] + 0.5, G.H_TOTAL - 0.1]]))[0]
          and sh.contains(np.array([[xm, ob[1] + 1.8, G.H_TOTAL - 0.1]]))[0])
    check(f"{s_} bottom edge rounded ({G.EDGE_RB} mm)", not sh.contains(np.array([[xm, ob[1] + 0.2, 0.05]]))[0]
          and sh.contains(np.array([[xm, ob[1] + 0.2, G.EDGE_RB + 0.2]]))[0])
    check(f"{s_} front wall solid below the round", sh.contains(np.array([[xm, ob[1] + 0.3, G.H_TOTAL - 2.6]]))[0])

# 6c. the joined top surface is continuous across the seam (round runs straight through, faces flush)
g = G._global(); yb = g["top_edge"] + G.BAY_D - G.MARGIN
xs0 = g["xcut"][0]
for dz in (0.05, 1.0, 2.0):
    yb_ = yb - G.soft(dz, G.EDGE_R) - 0.05
    pl = shL.contains(np.array([[xs0 - 1.3, yb_, G.H_TOTAL - dz]]))[0]
    pr = shR.contains(np.array([[xs0 + 1.1 - hR["ox"], yb_, G.H_TOTAL - dz]]))[0]
    check(f"rounded back edge matches across the seam at {dz} mm below the top", pl == pr)

# 6. tongue and groove
xs, y = G._global()["xcut"][1], -19.05 + 6.0
check("tongue present on right shell", shR.contains(np.array([[xs - 0.4 - hR["ox"], y, 6.7]]))[0])
check("groove present in left shell", not shL.contains(np.array([[xs - 0.4, y, 6.7]]))[0])
# the groove and tongue stop inside the case: at the front and back faces the seam is only a hairline
for yy, nm_ in ((hL["bounds"][1] + 0.6, "front"), (hL["bounds"][3] - 0.6, "back")):
    xcut = G._global()["xcut"][0 if nm_ == "back" else G.NROWS - 1]
    check(f"seam is a clean hairline at the {nm_} face (groove does not break through)",
          bool(shL.contains(np.array([[xcut - G.SEAM_GAP - 0.3, yy, G.TG_ZC]]))[0]))
# 6d. snap-on key covers
import covers as CV
import manifold3d as _m
def _man(tm):
    return _m.Manifold(_m.Mesh(vert_properties=np.asarray(tm.vertices, dtype=np.float32), tri_verts=np.asarray(tm.faces, dtype=np.uint32)))
for s_, nm in (("L", "left"), ("R", "right")):
    h = G.half(s_)
    cv = trimesh.load(OUT + f"{nm}_cover.stl")
    sh = trimesh.load(OUT + f"{nm}_shell.stl"); bz = trimesh.load(OUT + f"{nm}_oled_bezel.stl")
    check(f"{s_} cover watertight", cv.is_watertight)
    ov = (_man(cv) ^ _man(sh)).volume() + (_man(cv) ^ _man(bz)).volume()
    check(f"{s_} cover clears the case and the OLED bezel ({ov:.4f} mm3 overlap)", ov < 1e-3)
    T = G.thickness()
    pts = np.array([[k["X"], k["Y"], T["cap_top"] + 0.05] for k in h["keys"]] + [[k["X"], k["Y"], CV.z_ceiling() - 0.05] for k in h["keys"]])
    check(f"{s_} cover sits {CV.z_ceiling() - T['cap_top']:.1f} mm above the keycaps (no key is pressed)", not cv.contains(pts).any())
    ob = h["bounds"]
    hooks_ok = True
    for wall, x0, x1 in CV.tabs(h):
        y = ob[1] + 0.3 if wall == "front" else ob[3] - 0.3
        p = np.array([[(x0 + x1) / 2, y, 0.05]])
        hooks_ok &= bool(cv.contains(p)[0]) and not bool(sh.contains(p)[0])
    check(f"{s_} all {len(CV.tabs(h))} snap hooks reach under the case's bottom edge", hooks_ok)
    check(f"{s_} cover tabs stay above the desk (lowest point {cv.bounds[0][2]:.2f} mm, feet at -1.0)", cv.bounds[0][2] > -(G.FOOT_T - 0.5))
    sl = h["comp"]["slide"]
    check(f"{s_} power switch reachable through the cover's notch",
          not cv.contains(np.array([[sl["cx"], ob[3] + CV.CLEAR + CV.WALL / 2, 4.0]]))[0])

# 7. printability: every part as it sits in out/stl/print_ready
import printcheck
for name, ok, msg in printcheck.run():
    check(f"print: {name}: {msg}", ok)
print("FAILED CHECKS:", bad)
