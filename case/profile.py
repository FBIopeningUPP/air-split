"""Side section through the left half with the full thickness stack-up dimensioned."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch
import geom as G
from layout import U

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
T = G.thickness()
h = G.half("L")
ob = h["bounds"]
COL = dict(shell="#3b3f45", base="#5a5f66", cap="#e9e6df", capedge="#8a8578", body="#22252a",
           top="#d9dde1", stem="#c8463c", batt="#c9cdd2", kap="#e7a92b", foot="#7d8a6a", pcb="#16213a", dim="#b3261e")
H, PT, BT = G.H_TOTAL, G.PLATE_T, G.BASE_T
K, C = G.KS33, G.CAP
import trimesh, numpy as np
from matplotlib.patches import Polygon as MPoly
_gx = h["oled_glass_x"]; X_SECT = (_gx[0] + _gx[1]) / 2      # cut through the middle of the OLED window
STL = os.path.join(OUT, "stl")

def mesh_section(ax, name, fc):
    m = trimesh.load(os.path.join(STL, name + ".stl"))
    sec = m.section(plane_origin=[X_SECT, 0, 0], plane_normal=[1, 0, 0])
    if sec is None: return
    for ent in sec.discrete:
        pts = np.asarray(ent)
        ax.add_patch(MPoly(pts[:, 1:3], closed=True, fc=fc, ec="none"))
rows = sorted({k["row"] for k in h["keys"]})
ys = {r: -r * U for r in rows}

def section(ax, detail=False):
    y0, y1 = (ys[1] - 13, ys[1] + 13) if detail else (ob[1], ob[3])
    W = G.WALL
    if not detail:                                      # the real shell, base and bezel, sliced from the STLs
        mesh_section(ax, "left_base", COL["base"]); mesh_section(ax, "left_shell", COL["shell"])
        mesh_section(ax, "left_oled_bezel", "#4b5058")
        P = h["oled_pose"]; sn = P["sn"]; O_ = G.OLED
        sA = P["s0"] + 0.2; sc = P["s0"] + (O_["pcb_w"] + 0.4) / 2
        nG = -(O_["lip"] + O_["glass_t"]); nP = nG - O_["pcb_t"]
        ax.add_patch(MPoly([sn(sA, nP), sn(sA + O_["pcb_w"], nP), sn(sA + O_["pcb_w"], nG), sn(sA, nG)], fc=COL["pcb"], ec="none"))
        ax.add_patch(MPoly([sn(sc - O_["glass_w"]/2, nG), sn(sc + O_["glass_w"]/2, nG), sn(sc + O_["glass_w"]/2, -O_["lip"]), sn(sc - O_["glass_w"]/2, -O_["lip"])],
                           fc="#0d0f12", ec="none"))
        ax.add_patch(MPoly([sn(sc - O_["win_w"]/2, -O_["lip"] - 0.05), sn(sc + O_["win_w"]/2, -O_["lip"] - 0.05), sn(sc + O_["win_w"]/2, -O_["lip"] + 0.05), sn(sc - O_["win_w"]/2, -O_["lip"] + 0.05)],
                           fc="#5ec8ff", ec="none"))
    else:
        edges = [y0] + [ys[1] - K["hole"] / 2, ys[1] + K["hole"] / 2] + [y1]
        for i in range(0, len(edges), 2):
            ax.add_patch(Rectangle((edges[i], H - PT), edges[i + 1] - edges[i], PT, fc=COL["shell"], ec="none"))
        ax.add_patch(Rectangle((y0, 0), y1 - y0, BT, fc=COL["base"], ec="none"))
    krows = [1] if detail else rows
    for r in krows:
        if not detail and not any(abs(k["X"] - X_SECT) < 7 for k in h["keys"] if k["row"] == r): continue
        y = ys[r]
        ax.add_patch(Rectangle((y - K["hole"] / 2, H - PT), K["hole"], PT, fc=COL["body"], ec="none"))
        ax.add_patch(Rectangle((y - 6.9, H - K["body_below"]), 13.8, K["body_below"] - PT, fc=COL["body"], ec="none"))
        ax.add_patch(Rectangle((y - 1.5, H - K["post_below"]), 3.0, K["post_below"] - K["body_below"], fc=COL["body"], ec="none"))
        ax.add_patch(Rectangle((y - K["flange"] / 2, H), K["flange"], 0.6, fc=COL["top"], ec="#999", lw=0.3))
        ax.add_patch(Rectangle((y - 6.5, H + 0.6), 13.0, 2.0, fc=COL["top"], ec="#999", lw=0.3))
        ax.add_patch(Rectangle((y - 1.0, H + 2.6), 2.0, K["above"] - 2.6, fc=COL["stem"], ec="none"))
        ax.add_patch(FancyBboxPatch((y - (U - 1.6) / 2 + 0.6, H + C["skirt"]), U - 1.6 - 1.2, C["h"],
                                    boxstyle="round,pad=0,rounding_size=0.9", fc=COL["cap"], ec=COL["capedge"], lw=0.6))
    # back bay: battery and controller sit on the base
    b = h["comp"]["batt"]
    if detail: return
    if abs(b["cx"] - X_SECT) < b["w"] / 2:
        ax.add_patch(Rectangle((b["cy"] - b["h"] / 2, BT - G.BATT["pocket"]), b["h"], G.BATT["t"], fc=COL["batt"], ec="#888", lw=0.5))
    # feet
    for fy in (y0 + 12, y1 - 12):
        ax.add_patch(Rectangle((fy - 4, -(G.FOOT_T - 0.5)), 8, G.FOOT_T, fc=COL["foot"], ec="none"))

def vdim(ax, x, z0, z1, text, side=1, fs=8):
    ax.annotate("", (x, z0), (x, z1), arrowprops=dict(arrowstyle="<->", color=COL["dim"], lw=0.8, shrinkA=0, shrinkB=0))
    ax.text(x + side * 1.2, (z0 + z1) / 2, text, color=COL["dim"], fontsize=fs, va="center", ha="left" if side > 0 else "right")

fig = plt.figure(figsize=(16, 7.0))
ax = fig.add_axes([0.03, 0.66, 0.94, 0.30])
section(ax)
ax.plot([ob[1] - 8, ob[3] + 40], [-(G.FOOT_T - 0.5)] * 2, color="#999", lw=0.8)
xr = ob[3] + 4
vdim(ax, xr, 0, H, f"case {H:.1f} mm")
vdim(ax, xr + 16, 0, T["cap_top"], f"with keycaps {T['cap_top']:.1f} mm")
vdim(ax, ob[1] - 4, -(G.FOOT_T - 0.5), T["cap_top"], f"on the desk {T['on_desk']:.1f} mm", side=-1)
ax.text(ob[1], T["cap_top"] + 10, "Section through the OLED, left half, sliced from the real STLs. True scale. Front of the keyboard is on the left.",
        fontsize=10, color="#222")
P_ = h["oled_pose"]
ax.annotate(f"OLED bezel, tilted {G.OLED_TILT:.0f}°\n{P_['z_f']:.1f} mm front, {P_['z_b']:.1f} mm back", (P_["y_b"] - 4, P_["z_b"] - 0.6), (P_["y_b"] - 26, P_["z_b"] + 3.2),
            fontsize=8, color=COL["dim"], arrowprops=dict(arrowstyle="-", color=COL["dim"], lw=0.6))
ax.annotate(f"{G.EDGE_R} mm rounded edge", (ob[1] + 0.5, H - 0.4), (ob[1] - 30, H + 7), fontsize=8, color=COL["dim"],
            arrowprops=dict(arrowstyle="-", color=COL["dim"], lw=0.6))
ax.set_xlim(ob[1] - 34, ob[3] + 52); ax.set_ylim(-4, T["cap_top"] + 13); ax.set_aspect("equal"); ax.axis("off")

# detail: one key, 6x
ax2 = fig.add_axes([0.03, 0.03, 0.52, 0.58])
section(ax2, detail=True)
y = ys[1]
ax2.set_xlim(y - 30, y + 40); ax2.set_ylim(-2.2, T["cap_top"] + 1.5); ax2.set_aspect("equal"); ax2.axis("off")
xd = y + 14.5
vdim(ax2, xd, 0, BT, f"base {BT} mm", fs=8.5)
vdim(ax2, xd, BT, H - PT, f"inside {G.INTERIOR} mm", fs=8.5)
vdim(ax2, xd, H - PT, H, f"plate {PT} mm", fs=8.5)
vdim(ax2, y - 2.6, BT, H - K["post_below"], f"post clears base by {T['post_clearance']:.1f} mm", side=-1, fs=8.5)
vdim(ax2, y - 13.5, H, H + C["skirt"], f"cap skirt {C['skirt']} mm\n(travel {K['travel']} mm)", side=-1, fs=8.5)
vdim(ax2, y - 13.5, H + C["skirt"], T["cap_top"], f"keycap {C['h']} mm", side=-1, fs=8.5)
vdim(ax2, xd, H, H + K["above"], f"KS-33 above plate {K['above']} mm", fs=8.5)
ax2.text(y - 29, T["cap_top"] + 0.9, "One key, enlarged (KS-33 sizes from Gateron's STEP model)", fontsize=10)

ax3 = fig.add_axes([0.60, 0.05, 0.37, 0.55]); ax3.axis("off")
rows_t = [("Base plate", f"{BT:.1f} mm"), ("Inside space (wires, battery, board)", f"{G.INTERIOR:.1f} mm"),
          ("Switch plate", f"{PT:.1f} mm"), ("Case total (table to plate top)", f"{H:.1f} mm"),
          ("KS-33 stem top (hidden inside the cap)", f"{T['switch_top']:.1f} mm"), ("Top of keycaps", f"{T['cap_top']:.1f} mm"),
          ("On the desk, with 1.5 mm feet", f"{T['on_desk']:.1f} mm"),
          ("Battery (in a 0.6 mm pocket) / air above it", f"{G.BATT['t']:.1f} / {G.INTERIOR + G.BATT['pocket'] - G.BATT['t']:.1f} mm"),
          ("SuperMini on 1 mm foam, top of USB-C", f"{G.BASE_T + G.MCU['lift'] + G.MCU['t']/2 + G.MCU['usb_h']/2:.1f} mm")]
ax3.text(0, 1.0, "Thickness stack-up (from the table)", fontsize=12, weight="bold", va="top")
for i, (a, b) in enumerate(rows_t):
    yy = 0.88 - i * 0.085
    ax3.text(0, yy, a, fontsize=10.5, va="top"); ax3.text(1.0, yy, b, fontsize=10.5, va="top", ha="right", family="monospace",
                                                          weight="bold" if "total" in a or "desk" in a else "normal")
ax3.text(0, 0.06, "Keycap height assumes Gateron-LP style caps (skirt 3.4, cap 4.0 mm). \nOther low-profile caps change the top two lines by about 1 mm.",
         fontsize=8.5, color="#555", va="top", wrap=True)
plt.savefig(os.path.join(OUT, "thickness_profile.png"), dpi=130, facecolor="#fbfaf7")
print("profile written")
