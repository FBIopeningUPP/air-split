import os, sys, json, base64
import numpy as np, trimesh
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "case"))
import geom as G
from layout import U

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out", "stl")

def enc(a):
    return base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()

def mesh(name):
    m = trimesh.load(os.path.join(OUT, name + ".stl"))
    return dict(v=enc(m.vertices.astype(np.float32)), i=enc(m.faces.astype(np.uint32)))

import oled_art
POS = {(k["row"], round(k["x0"], 3)): i for i, k in enumerate(G._global()["allk"])}   # keymap position of each key
WIRING = json.load(open(os.path.join(OUT, "..", "wiring.json")))
data = dict(H=G.H_TOTAL, PLATE=G.PLATE_T, BASE=G.BASE_T, SWH=G.SW_HOLE, U=U, MCU=G.MCU, BATT=G.BATT,
            MAG=dict(r=G.MAG_D/2, t=G.MAG_T, z=G.MAG_Z), SLIDE=G.SLIDE, STAB_DX=G.STAB_DX,
            KS33=G.KS33, CAP=G.CAP, OLED=G.OLED, EDGE_R=G.EDGE_R, EDGE_RB=G.EDGE_RB, T=G.thickness(), INTERIOR=G.INTERIOR, FOOT_T=G.FOOT_T, PIN=G.WIRE,
            CARD=[[p["name"], p["cx"], p["cy"], p["side"]] for p in G.supermini_card_pins()])
for s, nm in (("L", "left"), ("R", "right")):
    h = G.half(s)
    b = h["bounds"]
    data[s] = dict(
        shell=mesh(f"{nm}_shell"), base=mesh(f"{nm}_base"), bezel=mesh(f"{nm}_oled_bezel"), cover=mesh(f"{nm}_cover"),
        bounds=[b[0], b[1], b[2], b[3]],
        keys=[[round(k["X"], 3), round(k["Y"], 3), k["w"], k["label"], k["row"], k["col_local"], POS[(k["row"], round(k["x0"], 3))]] for k in h["keys"]],
        comp={n: [c["cx"], c["cy"], c["w"], c["h"]] for n, c in h["comp"].items()}, side=s,
        posts=len(h["posts"]), ox=h["ox"],
        magnets=[[round(m["x"], 3), round(m["y"], 3)] for m in h["magnets"]],
        postxy=[[round(float(x), 2), round(float(y), 2)] for x, y in h["posts"]],
        feet=[[round(float(x), 2), round(float(y), 2)] for x, y in G.feet(h)],
        wiring=WIRING["left" if s == "L" else "right"],
        oled_win=list(h["oled_win"].bounds), oled_glass=list(h["oled_glass"].bounds), oled_pin_dir=h["oled_pin_dir"],
        oled_pose={k: h["oled_pose"][k] for k in ("theta", "y_f", "z_f", "y_b", "z_b", "s0", "Ls")}, oled_glass_x=list(h["oled_glass_x"]),
        batt_l=G.batt_of(s)["l"], batt_name=G.BATT["name"],
    )

TEMPLATE = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "template.html")).read()
data["OLED_ART"] = oled_art.js_data()
RENDER_JS = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "oled_render.js")).read()
html = TEMPLATE.replace("/*DATA*/", json.dumps(data, separators=(",", ":"))).replace("/*OLED_RENDER*/", RENDER_JS)
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html"), "w").write(html)
print("viewer written", round(len(html)/1e6, 2), "MB")
