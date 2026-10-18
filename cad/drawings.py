import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon as MPoly
import geom as G

from paths import IMAGES as OUT

def poly_patch(ax, p, **kw):
    for g in (p.geoms if hasattr(p, "geoms") else [p]):
        ax.add_patch(MPoly(list(g.exterior.coords), closed=True, **kw))
        for i in g.interiors:
            ax.add_patch(MPoly(list(i.coords), closed=True, fc="white", ec=kw.get("ec"), lw=kw.get("lw", 1)))

def draw(side):
    h = G.half(side)
    fig, ax = plt.subplots(figsize=(13 if side == "R" else 10.5, 10.4))
    poly_patch(ax, h["outline"], fc="#e9e4d8", ec="#333", lw=1.4)
    poly_patch(ax, h["cavity"], fc="#f7f4ec", ec="#999", lw=0.6)
    for k, c in zip(h["keys"], h["cells"]):
        xs, ys = c.exterior.xy
        ax.plot(xs, ys, color="#c9c2b0", lw=0.5)
    for p in h["holes"]:
        poly_patch(ax, p, fc="#fff", ec="#222", lw=0.8)
    for p in h["stabs"]:
        poly_patch(ax, p, fc="#fff", ec="#b33", lw=0.8)
    for k in h["keys"]:
        ax.text(k["X"], k["Y"], k["label"], ha="center", va="center", fontsize=6.5, color="#555")
    for (x, y) in h["posts"]:
        ax.add_patch(Circle((x, y), G.POST_D/2, fc="#d9a441", ec="#7a5a10", lw=0.8))
        ax.add_patch(Circle((x, y), G.INSERT_D/2, fc="white", ec="#7a5a10", lw=0.6))
    for mg in h["magnets"]:
        ax.add_patch(Circle((mg["x"], mg["y"]), G.MAG_D/2, fc="#c0392b", ec="#7b241c", lw=0.7, alpha=.85))
    cols = {"mcu": "#4a7fb5", "batt": "#6aa84f", "slide": "#a64d79", "rst": "#cc7a00", "oled": "#2b2f36"}
    names = {"mcu": "SuperMini\nnRF52840", "batt": "LiPo KP 551245", "slide": "power", "rst": "RST", "oled": "OLED 0.91\""}
    for n, c in h["comp"].items():
        ax.add_patch(Rectangle((c["cx"]-c["w"]/2, c["cy"]-c["h"]/2), c["w"], c["h"], fc=cols[n], ec="#222", alpha=.55, lw=.8))
        ax.text(c["cx"], c["cy"], names[n], ha="center", va="center", fontsize=6.5)
    ob = h["bounds"]
    for o in h["openings"]:
        ax.plot([o["x"]-o["w"]/2, o["x"]+o["w"]/2], [ob[3], ob[3]], color="#d33", lw=3)
        ax.text(o["x"], ob[3]+2.2, o["kind"], ha="center", fontsize=7, color="#d33")
    ax.set_aspect("equal"); ax.set_xlim(ob[0]-6, ob[2]+6); ax.set_ylim(ob[1]-6, ob[3]+9)
    ax.set_title(f"{'LEFT' if side=='L' else 'RIGHT'} half, top view. outline {ob[2]-ob[0]:.1f} x {ob[3]-ob[1]:.1f} mm, "
                 f"{G.H_TOTAL:.1f} mm thick. Red dots = magnet pockets on the seam.", fontsize=9)
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, f"case_{'left' if side=='L' else 'right'}_top.png"), dpi=130, facecolor="#fbfaf7")
    plt.close()

def draw_joined():
    from shapely.affinity import translate
    hs = {s: G.half(s) for s in "LR"}
    fig, ax = plt.subplots(figsize=(17, 9.4))
    for s, h in hs.items():
        sh = h["ox"]
        o = translate(h["outline"], xoff=sh)
        poly_patch(ax, o, fc="#e9e4d8" if s == "L" else "#e2e6ea", ec="#333", lw=1.2)
        poly_patch(ax, translate(h["cavity"], xoff=sh), fc="#f7f4ec" if s == "L" else "#f2f4f6", ec="#aaa", lw=0.5)
        for p in h["holes"]:
            poly_patch(ax, translate(p, xoff=sh), fc="#fff", ec="#222", lw=0.6)
        for p in h["stabs"]:
            poly_patch(ax, translate(p, xoff=sh), fc="#fff", ec="#b33", lw=0.6)
        for k in h["keys"]:
            ax.text(k["X"] + sh, k["Y"], k["label"], ha="center", va="center", fontsize=5.5, color="#666")
        for (x, y) in h["posts"]:
            ax.add_patch(Circle((x + sh, y), G.POST_D/2, fc="#d9a441", ec="#7a5a10", lw=0.6))
        for mg in h["magnets"]:
            ax.add_patch(Circle((mg["x"] + sh, mg["y"]), G.MAG_D/2, fc="#c0392b", ec="#7b241c", lw=0.6, alpha=.85))
        cols = {"mcu": "#4a7fb5", "batt": "#6aa84f", "slide": "#a64d79", "rst": "#cc7a00", "oled": "#2b2f36"}
        for n, c in h["comp"].items():
            ax.add_patch(Rectangle((c["cx"] + sh - c["w"]/2, c["cy"] - c["h"]/2), c["w"], c["h"], fc=cols[n], ec="#222", alpha=.55, lw=.6))
    g = G._global()
    ax.set_aspect("equal"); b = g["O"].bounds
    ax.set_xlim(b[0] - 6, b[2] + 6); ax.set_ylim(b[1] - 6, b[3] + 6)
    ax.set_title(f"Both halves joined: {b[2]-b[0]:.1f} x {b[3]-b[1]:.1f} mm, {G.H_TOTAL:.1f} mm thick. "
                 "Staircase seam follows the key edges; red dots are magnet pockets.", fontsize=9)
    ax.axis("off"); plt.tight_layout()
    plt.savefig(os.path.join(OUT, "case_joined_top.png"), dpi=120, facecolor="#fbfaf7"); plt.close()

if __name__ == "__main__":
    for s in "LR":
        draw(s)
    draw_joined()
    print("drawings done")
