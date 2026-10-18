"""Wiring diagrams drawn from the real routes in routing.py, seen from underneath (the way you solder it).
Each sheet: the whole half with every wire and diode, plus an enlarged SuperMini with every pad named."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch
from matplotlib.transforms import Affine2D
import geom as G
import routing as RT
from gen_zmk import ROW_PINS, COL_PINS_L, COL_PINS_R

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
INK, MUTED, BG = "#1d2026", "#6a6f78", "#fbfaf7"


def sheet(side):
    d = RT.build(side)
    h = d["h"]
    F = lambda x: -x                                   # seen from underneath: mirror x
    fig = plt.figure(figsize=(17, 11.2))
    ax = fig.add_axes([0.02, 0.03, 0.62, 0.9])
    ob = h["bounds"]
    ex, ey = h["outline"].exterior.xy
    ax.fill([F(x) for x in ex], ey, color="#e8e4da", ec="#555", lw=1.0, zorder=0)
    cx, cy = h["cavity"].exterior.xy
    ax.fill([F(x) for x in cx], cy, color="#f6f3ec", ec="#bbb", lw=0.5, zorder=0)
    for k in h["keys"]:
        ax.add_patch(Rectangle((F(k["X"]) - 6.9, k["Y"] - 6.9), 13.8, 13.8, fc="#fff", ec="#9a9a9a", lw=0.6, zorder=1))
        ax.text(F(k["X"]), k["Y"] + 3.0, k["label"], ha="center", va="center", fontsize=6.5, color=MUTED, zorder=2)
        ax.add_patch(Circle((F(k["X"]), k["Y"]), 1.65, fc="#e4e4e4", ec="#aaa", lw=0.4, zorder=2))
    for s in h["stabs"]:
        x, y = s.exterior.xy
        ax.fill([F(v) for v in x], y, color="#d8d8d8", ec="#999", lw=0.4, zorder=1)
    for (x, y) in h["posts"]:
        ax.add_patch(Circle((F(x), y), G.POST_D / 2, fc="#d9a441", ec="#7a5a10", lw=0.6, zorder=2))
    c = h["comp"]
    b = c["batt"]
    ax.add_patch(Rectangle((F(b["cx"]) - b["w"] / 2, b["cy"] - b["h"] / 2), b["w"], b["h"], fc="#cfd3d8", ec="#888", lw=0.7, zorder=1))
    ax.text(F(b["cx"]), b["cy"], "LiPo KP 551245", ha="center", va="center", fontsize=7.5, color="#333", zorder=2)
    pcm = F(b["cx"] - (1 if side == "L" else -1) * (b["w"] / 2 - 2.5))
    ax.add_patch(Rectangle((pcm - 2.5, b["cy"] - b["h"] / 2 + 1), 5, b["h"] - 2, fc="#e7a92b", ec="none", alpha=.8, zorder=2))
    o = c["oled"]
    ax.add_patch(Rectangle((F(o["cx"]) - o["w"] / 2, o["cy"] - o["h"] / 2), o["w"], o["h"], fc="#2b2f36", ec="#111", lw=0.7, alpha=0.35, zorder=5))
    ax.text(F(o["cx"]), o["cy"], "OLED (above the wires)", ha="center", va="center", fontsize=6.5, color="#111", zorder=9)
    for n, lab in (("slide", "power"), ("rst", "reset")):
        q = c[n]
        ax.add_patch(Rectangle((F(q["cx"]) - q["w"] / 2, q["cy"] - q["h"] / 2), q["w"], q["h"], fc="#5c5f66", ec="#222", lw=0.6, zorder=2))
        ax.text(F(q["cx"]), q["cy"] + q["h"] / 2 + 1.2, lab, ha="center", fontsize=6.5, color=INK, zorder=3)
    m = c["mcu"]
    ax.add_patch(Rectangle((F(m["cx"]) - m["w"] / 2, m["cy"] - m["h"] / 2), m["w"], m["h"], fc="#15171b", ec="#000", lw=0.8, zorder=3))
    for p in G.mcu_pins(side):
        ax.add_patch(Circle((F(p["x"]), p["y"]), 0.75, fc="#d9ae4f", ec="#7a5a10", lw=0.4, zorder=4))
    for w in d["wires"]:
        xs = [F(p[0]) for p in w["p"]]; ys = [p[1] for p in w["p"]]
        ax.plot(xs, ys, color=w["c"], lw=0.7 if w["kind"] == "lead" else 1.5, zorder=5 if w["kind"] == "lead" else 6,
                solid_capstyle="round")
    for dd in d["diodes"]:
        (x0, y0), (x1, y1) = dd["a"][:2], dd["k"][:2]
        ax.plot([F(x0), F(x1)], [y0, y1], color="#d36f2a", lw=4.2, solid_capstyle="butt", zorder=7)
        t = 0.8
        ax.plot([F(x0 + (x1 - x0) * t), F(x1)], [y0 + (y1 - y0) * t, y1], color="#111", lw=4.2, solid_capstyle="butt", zorder=8)
    for r in sorted({k["row"] for k in h["keys"]}):
        ks = [k for k in h["keys"] if k["row"] == r]
        yy = ks[0]["Y"] + G.WIRE["row_dy"]
        xe = F(min(k["X"] for k in ks) - 8) if side == "L" else F(max(k["X"] for k in ks) + 8)
        ax.text(xe, yy + 1.2, f"R{r}", fontsize=7.5, color=RT.ROWC[r], weight="bold", va="bottom")
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_xlim(F(ob[2]) - 6, F(ob[0]) + 6); ax.set_ylim(ob[1] - 6, ob[3] + 6)
    ax.set_title(f"{'LEFT' if side == 'L' else 'RIGHT'} half from underneath (base off): every wire and diode where it goes.  "
                 f"{len(d['diodes'])} diodes, about {sum(RT.length(w) for w in d['wires'])/1000:.1f} m of 30 AWG wire.",
                 fontsize=11, color=INK, loc="left")

    # enlarged SuperMini, component side up (how you see it while soldering)
    bx = fig.add_axes([0.655, 0.34, 0.34, 0.6])
    bx.add_patch(FancyBboxPatch((-9, -16.4), 18, 32.8, boxstyle="round,pad=0,rounding_size=0.8", fc="#15171b", ec="#000", lw=1))
    bx.add_patch(Rectangle((-4.47, 10.7), 8.94, 6.7, fc="#b9bec4", ec="#666", lw=0.8))
    bx.text(0, 14, "USB-C", ha="center", va="center", fontsize=8, color="#222")
    bx.add_patch(Rectangle((-3.55, -16.3), 7.1, 2.1, fc="#e3a6a0", ec="none"))
    bx.text(0, -15.25, "antenna", ha="center", va="center", fontsize=6.5, color="#5a2a26")
    chip = Rectangle((-3.5, -9.0), 7, 7, fc="#3a3d42", ec="#111", lw=0.6)
    chip.set_transform(Affine2D().rotate_deg_around(0, -5.5, 45) + bx.transData); bx.add_patch(chip)
    bx.text(0, -5.5, "nRF52840", ha="center", va="center", fontsize=6.5, color="#ddd")
    pins = COL_PINS_L if side == "L" else COL_PINS_R
    ncol = max(k["col_local"] for k in h["keys"]) + 1
    sig = {f"D{p}": (f"R{i} row", RT.ROWC[i]) for i, p in enumerate(ROW_PINS)}
    sig.update({(p if isinstance(p, str) else f"D{p}"): (f"C{i} column", RT.COLC[i % 9]) for i, p in enumerate(pins[:ncol])})
    sig["D2"] = ("OLED SDA", "#b8860b"); sig["D3"] = ("OLED SCL", "#c77d00"); sig["3V3"] = ("OLED VCC", "#c0392b")
    sig["B+"] = ("battery + via switch", "#d1342f"); sig["RST"] = ("reset button", "#5b6068")
    for p in G.supermini_card_pins():
        x, y = p["cx"], p["cy"]
        bx.add_patch(Circle((x, y), 0.85, fc="#d9ae4f", ec="#7a5a10", lw=0.5))
        bx.add_patch(Circle((x, y), 0.4, fc="#15171b", ec="none"))
        if p["side"] == "end":
            bx.text(x, y + 1.2, p["name"], ha="center", fontsize=5.5, color="#bbb", rotation=90, va="bottom")
            if p["name"] in sig and side == "R":
                bx.text(x, y - 3.2, sig[p["name"]][0], ha="center", fontsize=7.2, color=sig[p["name"]][1], weight="bold", va="top")
            continue
        s = sig.get(p["name"].split()[0])
        if p["name"] == "GND" and p["side"] == "right": s = ("battery −", "#222")
        if p["name"] == "GND" and p["side"] == "left" and p["i"] == 3: s = ("reset button", "#222")
        if p["name"] == "GND" and p["side"] == "left" and p["i"] == 4: s = ("OLED GND", "#222")
        ha = "right" if p["side"] == "left" else "left"
        bx.text(x - 1.4 if p["side"] == "left" else x + 1.4, y, p["name"], ha=ha, va="center", fontsize=7.2, color=INK)
        if s:
            bx.text(x - 12.5 if p["side"] == "left" else x + 12.5, y, s[0], ha=ha, va="center", fontsize=7.6, color=s[1], weight="bold")
    bx.set_xlim(-34, 34); bx.set_ylim(-18, 19); bx.set_aspect("equal"); bx.axis("off")
    bx.set_title("SuperMini nRF52840, component side up, USB-C at the top", fontsize=10, color=INK)
    tx = fig.add_axes([0.66, 0.03, 0.33, 0.28]); tx.axis("off")
    notes = [
        "Mount every switch with its pins toward you (front edge).",
        "Column wire = the left pin. The other pin goes to the diode.",
        "Diode band (cathode) goes to the ROW wire (firmware is col2row).",
        "Rows climb the outer side wall; columns run behind the F-row.",
        "Wires to the board's far edge cross over it, under the top skin.",
        "OLED: GND, VCC -> 3V3, SCL -> D3, SDA -> D2 (from its underside).",
        "Battery + -> power switch middle pin; outer pin -> B+.",
        "Battery − -> GND. Wire the switch so ON is toward the controller.",
        "Check every key with a multimeter before closing the case.",
    ]
    for i, n in enumerate(notes):
        tx.text(0, 0.98 - i * 0.125, "• " + n, fontsize=8.8, color=INK, va="top")
    plt.savefig(os.path.join(OUT, f"wiring_{'left' if side == 'L' else 'right'}.png"), dpi=120, facecolor=BG)
    plt.close()


if __name__ == "__main__":
    for s in "LR":
        sheet(s)
    print("wiring diagrams written")
