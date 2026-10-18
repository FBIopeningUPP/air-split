"""3D wire routes and diodes for both halves, with a clearance check against every part in the case.

Local frame of each half (same as geom.half): x right, y toward the back, z up from the table.
Every switch is mounted with its two pins toward you (the front edge of the keyboard).

Heights (mm above the table; base top 1.6, plate underside 6.8, plate top 8.0):
    switch bodies end 5.45 (8.0 - 2.55), pins 3.05, centre posts 2.2 (KS-33 STEP)
    column wires 5.05 (against the switch bottoms), diodes 4.4, row wires 3.75
    SuperMini on 1 mm foam: board 2.6-4.2, parts on it up to 5.05

Runs to the controller:
    rows climb the outer side wall in one bundle, then run behind the F-row (y lane ROW_Y)
    columns leave the F-row key and run behind the F-row (y lane COL_Y)
    pads on the board edge facing the keys are reached from the front at z 4.7;
    pads on the far edge are reached by crossing over the board at z OVER (under the top skin)
    power and reset wires run across the bay at z 5.6 and drop onto their pads

    python3 routing.py   -> clearance report + build/wiring.json (used by the viewer and the guide)
"""
import os, json, math
import numpy as np
from shapely.geometry import Point, box
import geom as G
from layout import U
from gen_zmk import ROW_PINS, COL_PINS_L, COL_PINS_R

from paths import BUILD as OUT
R_W = 0.3                                   # 30 AWG silicone, ~0.6 mm over the insulation
H, PT, BT = G.H_TOTAL, G.PLATE_T, G.BASE_T
Z_SWB = H - G.KS33["body_below"]            # 5.45
Z_COL, Z_DIO, Z_ROW = Z_SWB - 0.4, Z_SWB - 1.05, Z_SWB - 1.7
PIN_COL, PIN_DIO, ROW_DY = G.WIRE["pin_col"], G.WIRE["pin_dio"], G.WIRE["row_dy"]
DIO_A, DIO_K = -6.2, -9.9                   # diode body (DO-35, 3.7 long), relative to the key centre
TOP = G._global()["top_edge"]               # back edge of the F-row cells
ROW_Y, COL_Y = TOP - 2.3, TOP - 1.55        # lanes behind the F-row switch bodies (bodies end at TOP - 2.6)
Z_FRONT, OVER, Z_BAY = 4.75, 6.35, 5.6
BOARD_TOP = BT + G.MCU["lift"] + G.MCU["t"]  # 4.2
ROWC = ["#d1342f", "#e8851a", "#c9a227", "#2e9d4a", "#8a4fd0", "#c2417a"]
COLC = ["#1f5fa8", "#2b78c9", "#3c93d9", "#18a0b8", "#0e8f8f", "#3a6fd8", "#5a54c9", "#2d8bb0", "#4a6fa0"]


def build(side):
    h = G.half(side)
    keys = h["keys"]
    pins = {p["name"].split()[0]: p for p in G.mcu_pins(side)}
    gnds = [p for p in G.mcu_pins(side) if p["name"] == "GND"]
    mc = h["comp"]["mcu"]
    front_y = mc["cy"] - mc["h"] / 2
    sgn = 1 if side == "L" else -1                     # +1: the controller is at low x
    kx0 = min(k["X"] - k["w"] * U / 2 for k in keys); kx1 = max(k["X"] + k["w"] * U / 2 for k in keys)
    lane_x = kx0 - 0.75 if side == "L" else kx1 + 0.75
    wires, diodes = [], []

    def W(name, col, pts, r=R_W, kind="signal", joints=None):
        wires.append(dict(n=name, c=col, p=[[round(float(a), 3) for a in q] for q in pts], r=r, kind=kind,
                          j=joints if joints is not None else [0, len(pts) - 1]))

    def to_pad(p, start, z_lane, lane_y, offset_i=0):
        """from `start` (on a lane behind the F-row) to pad p; returns the remaining polyline"""
        px, py = p["x"], p["y"]
        facing_front = py < mc["cy"]
        if facing_front:
            return [start, [px, lane_y, z_lane], [px, lane_y, Z_FRONT], [px, py - 0.9, Z_FRONT], [px, py, BOARD_TOP + 0.35]]
        jx = px + 1.15 * (1 if offset_i % 2 == 0 else -1)
        return [start, [jx, lane_y, z_lane], [jx, lane_y, OVER], [jx, py - 1.3, OVER], [px, py - 1.3, OVER],
                [px, py, BOARD_TOP + 0.35]]

    # --- per key: diode, column chain, row chain ---
    rows, cols = {}, {}
    for k in keys:
        X, Y = k["X"], k["Y"]
        dx = X + PIN_DIO[0]
        roomy = h["cavity"].buffer(-0.4)
        std = [Point(dx, Y + y).buffer(1.0) for y in (DIO_A, DIO_K, ROW_DY)]
        k["row_x"] = dx
        if all(roomy.contains(s) for s in std):
            a, kk = [dx, Y + DIO_A, Z_DIO], [dx, Y + DIO_K, Z_DIO]
            diodes.append(dict(a=a, k=kk, key=k["label"]))
            W(f"diode lead {k['label']}", "#9aa0a6", [[dx, Y + PIN_DIO[1], Z_SWB - 0.1], a], 0.22, "lead")
            W(f"diode lead {k['label']}", "#9aa0a6", [kk, [dx, Y + ROW_DY, Z_ROW]], 0.22, "lead")
        else:                       # next to the seam: diode lies sideways, pointing away from the seam
            d = -sgn
            a, kk = [dx + d * 0.4, Y - 6.75, Z_DIO], [dx + d * 4.1, Y - 6.75, Z_DIO]
            diodes.append(dict(a=a, k=kk, key=k["label"]))
            W(f"diode lead {k['label']}", "#9aa0a6", [[dx, Y + PIN_DIO[1], Z_SWB - 0.1], [dx, Y - 6.75, Z_DIO], a], 0.22, "lead")
            W(f"diode lead {k['label']}", "#9aa0a6", [kk, [dx + d * 5.4, Y - 6.75, Z_DIO], [dx + d * 5.4, Y + ROW_DY, Z_ROW]], 0.22, "lead")
            k["row_x"] = dx + d * 5.4
        rows.setdefault(k["row"], []).append(k)
        cols.setdefault(k["col_local"], []).append(k)
    colpins = COL_PINS_L if side == "L" else COL_PINS_R
    # what a column wire (z 4.75-5.35) can run into: centre posts, pins, stabilisers, diodes, screw posts, case walls
    from shapely.ops import unary_union
    from shapely.prepared import prep
    from shapely.geometry import LineString
    blk = []
    for k in keys:
        blk.append(Point(k["X"], k["Y"]).buffer(1.65))
        blk.append(Point(k["X"] + PIN_DIO[0], k["Y"] + PIN_DIO[1]).buffer(0.5))
    for dd in diodes:
        blk.append(LineString([dd["a"][:2], dd["k"][:2]]).buffer(0.95))
    blk += [s for s in h["stabs"]] + [Point(x, y).buffer(G.POST_D / 2) for x, y in h["posts"]]
    blocked = (prep(unary_union(blk).buffer(R_W + 0.15)), prep(h["cavity"].buffer(-(R_W + 0.2))))

    # rows: wire along the row, then out to the side-wall lane, up to the bay, to the pad
    for r, ks in sorted(rows.items()):
        ks.sort(key=lambda k: k["X"])
        pts = [[k["row_x"], k["Y"] + ROW_DY, Z_ROW] for k in ks]
        if side == "R": pts = pts[::-1]
        W(f"R{r} row wire", ROWC[r], pts, kind="row", joints=list(range(len(pts))))
        p = pins[f"D{ROW_PINS[r]}"]
        z_l = 2.05 + 0.5 * r
        y_end = pts[-1][1]
        if r == max(rows):          # bottom row: cut the corner, the case corner is rounded
            run = [pts[-1], [lane_x + sgn * 6.0, y_end, Z_ROW], [lane_x, y_end + 6.0, z_l], [lane_x, ROW_Y, z_l]]
        else:
            run = [pts[-1], [lane_x, y_end, Z_ROW], [lane_x, y_end, z_l], [lane_x, ROW_Y, z_l]]
        run += to_pad(p, [lane_x, ROW_Y, z_l], z_l, ROW_Y, r)[1:]
        W(f"R{r} run → D{ROW_PINS[r]} ({p['name'].split()[-1]})", ROWC[r], run, kind="row")

    # columns: chain down the column, then from the F-row key to the lane behind it, to the pad
    order = sorted(cols, key=lambda c: abs(min(k["X"] for k in cols[c]) - mc["cx"]))
    for c, ks in sorted(cols.items()):
        ks.sort(key=lambda k: k["row"])
        pts, joints = [], []
        for i, k in enumerate(ks):           # shortest clear path between consecutive pins, found on a 0.5 mm grid
            q = [k["X"] + PIN_COL[0], k["Y"] + PIN_COL[1], Z_COL]
            if i:
                pts += [[x, y, Z_COL] for x, y in grid_path(blocked, pts[-1][:2], q[:2])[1:-1]]
            joints.append(len(pts)); pts.append(q)
        W(f"C{c} column wire", COLC[c % 9], pts, kind="col", joints=joints)
        pk = colpins[c] if isinstance(colpins[c], str) else f"D{colpins[c]}"
        p = pins[pk]
        lvl = order.index(c)
        z_l = 2.05 + 0.42 * lvl
        top = pts[0]
        run = [top, [top[0], COL_Y, Z_COL], [top[0], COL_Y, z_l]]
        run += to_pad(p, [top[0], COL_Y, z_l], z_l, COL_Y, c + 1)[1:]
        W(f"C{c} run → {pk} ({p['name'].split()[-1]})", COLC[c % 9], run, kind="col")

    # power: battery + -> slide switch middle pin, outer pin -> B+; battery - -> GND; reset button -> RST and GND
    b, sl, rs = h["comp"]["batt"], h["comp"]["slide"], h["comp"]["rst"]
    pcm_x = b["cx"] - sgn * (b["w"] / 2 + 0.4)            # leads leave the protection-board end, facing the controller
    sl_pin = lambda i: [sl["cx"] + 2.0 * i, sl["cy"] - sl["h"] / 2 - 0.3, BT + 1.75]
    rs_pin = lambda i: [rs["cx"] + 2.25 * i, rs["cy"] - rs["h"] / 2 - 0.3, BT + 1.6]

    x_rise = mc["cx"] + sgn * (mc["w"] / 2 + 1.6)          # gap between the board's inner end and the OLED frame
    Z_LOW = BT + 1.0                                        # under the OLED and its frame

    def to_board(p, pts, y_track):
        """from the gap beside the board: up, across the board at Z_BAY, down onto pad p"""
        px, py = p["x"], p["y"]
        side_off = 1.0 if py < mc["cy"] else -1.0
        return pts + [[x_rise, y_track, Z_BAY], [px, y_track, Z_BAY], [px, py + side_off, Z_BAY], [px, py, BOARD_TOP + 0.35]]

    def bay_to(p, start, y_track, name, col, kind):
        pts = [start, [start[0], y_track, Z_LOW], [x_rise, y_track, Z_LOW]]
        W(name, col, to_board(p, pts, y_track), kind=kind)

    bp = [pcm_x, b["cy"] + 3.0, BT + 2.0]; bm = [pcm_x, b["cy"] - 3.0, BT + 2.0]
    s0 = sl_pin(0)
    W("battery + → switch middle pin", "#d1342f",
      [bp, [pcm_x - sgn * 1.0, bp[1], Z_LOW], [pcm_x - sgn * 1.0, 22.9, Z_LOW], [s0[0], 22.9, Z_LOW], [s0[0], s0[1], s0[2]]], kind="power")
    bay_to(pins["B+"], sl_pin(-sgn), 23.2, "switch outer pin → B+", "#d1342f", "power")
    gnd_main = [p for p in G.mcu_pins(side) if p["name"] == "GND" and p["row"] == "right"][0]
    bay_to(gnd_main, bm, 22.4, "battery − → GND", "#222222", "power")
    bay_to(pins["RST"], rs_pin(-sgn), 21.6, "reset button → RST", "#5b6068", "signal")
    gl = [p for p in G.mcu_pins(side) if p["name"] == "GND" and p["row"] == "left"]
    bay_to(gl[1], rs_pin(sgn), 20.8, "reset button → GND", "#222222", "signal")
    # OLED: 4 wires from its pins (underside of the module, at the end facing the controller) to the board
    o, P = h["comp"]["oled"], h["oled_pose"]
    pin_x = o["cx"] - sgn * (o["w"] / 2 - 1.6)
    sc = P["s0"] + (G.OLED["pcb_w"] + 0.4) / 2
    n_bot = -(G.OLED["lip"] + G.OLED["glass_t"] + G.OLED["pcb_t"])
    for i, (nm, pad, col) in enumerate((("GND", gl[2], "#222222"), ("VCC", pins["3V3"], "#c0392b"),
                                        ("SCL", pins["D3"], "#c77d00"), ("SDA", pins["D2"], "#b8860b"))):
        y, zp = P["sn"](sc - 3.81 + 2.54 * i, n_bot)           # pin on the underside of the tilted module
        pts = [[pin_x, y, zp], [pin_x, y, 3.8], [x_rise, y, 3.8]]
        W(f"OLED {nm} → {pad['name'].split()[0]}", col, to_board(pad, pts, y), kind="oled")
    return dict(wires=wires, diodes=diodes, h=h)


def grid_path(blocked, a, b, step=0.5, pad=16.0):
    """A* on a 0.5 mm grid between two column pins (turns cost extra); returns a simplified [(x, y), ...] from a to b."""
    import heapq
    bad, ok = blocked
    x0, x1 = min(a[0], b[0]) - pad, max(a[0], b[0]) + pad
    y0, y1 = min(a[1], b[1]) - 4, max(a[1], b[1]) + 4
    nx, ny = int((x1 - x0) / step) + 1, int((y1 - y0) / step) + 1
    cell = lambda p: (int(round((p[0] - x0) / step)), int(round((p[1] - y0) / step)))
    pos = lambda c: (x0 + c[0] * step, y0 + c[1] * step)
    A, B = cell(a), cell(b)
    free = {}
    def is_free(c):
        if c not in free:
            p = pos(c)
            near = min(math.dist(p, a), math.dist(p, b)) < 1.3
            free[c] = near or (ok.contains(Point(p)) and not bad.contains(Point(p)))
        return free[c]
    start = (A, None)
    dist = {start: 0}; prev = {}
    q = [(abs(A[0] - B[0]) + abs(A[1] - B[1]), 0, start)]
    goal = None
    while q:
        f, g, st = heapq.heappop(q)
        if g > dist.get(st, 1e18): continue
        c, d = st
        if c == B: goal = st; break
        for dv in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (c[0] + dv[0], c[1] + dv[1])
            if not (0 <= n[0] < nx and 0 <= n[1] < ny) or not is_free(n): continue
            ng = g + 1 + (0 if d is None or d == dv else 3)
            ns = (n, dv)
            if ng < dist.get(ns, 1e18):
                dist[ns] = ng; prev[ns] = st
                heapq.heappush(q, (ng + abs(n[0] - B[0]) + abs(n[1] - B[1]), ng, ns))
    if goal is None:
        raise RuntimeError(f"no clear path from {a} to {b}")
    cells = [goal[0]]; st = goal
    while st in prev:
        st = prev[st]; cells.append(st[0])
    cells.reverse()
    pts = [pos(c) for c in cells]
    pts[0], pts[-1] = tuple(a), tuple(b)
    out = [pts[0]]                               # keep only the corners
    for i in range(1, len(pts) - 1):
        p0, p1, p2 = out[-1], pts[i], pts[i + 1]
        if abs((p1[0] - p0[0]) * (p2[1] - p1[1]) - (p1[1] - p0[1]) * (p2[0] - p1[0])) > 1e-9:
            out.append(p1)
    out.append(pts[-1])
    return out


# ---------------- clearance check ----------------
def obstacles(h):
    """(name, shapely 2D footprint, z0, z1) of everything a wire must not pass through."""
    obs = []
    for k in h["keys"]:
        X, Y = k["X"], k["Y"]
        obs.append((f"switch {k['label']}", box(X - 6.9, Y - 6.9, X + 6.9, Y + 6.9), Z_SWB, H))
        obs.append((f"post {k['label']}", Point(X, Y).buffer(1.65), H - G.KS33["post_below"], Z_SWB))
        for (px, py) in (PIN_COL, PIN_DIO):
            obs.append((f"pin {k['label']}", box(X + px - 0.45, Y + py - 0.3, X + px + 0.45, Y + py + 0.3), H - G.KS33["pins_below"], Z_SWB))
    for s in h["stabs"]:
        obs.append(("stabiliser", s.buffer(-0.15), H - PT - 3.2, H))
    for (x, y) in h["posts"]:
        obs.append(("screw post", Point(x, y).buffer(G.POST_D / 2), BT, H))
    c = h["comp"]
    obs.append(("battery", box(c["batt"]["cx"] - c["batt"]["w"] / 2, c["batt"]["cy"] - c["batt"]["h"] / 2, c["batt"]["cx"] + c["batt"]["w"] / 2, c["batt"]["cy"] + c["batt"]["h"] / 2),
                BT - G.BATT["pocket"], BT - G.BATT["pocket"] + G.BATT["t"]))
    obs.append(("slide switch", box(c["slide"]["cx"] - 4.3, c["slide"]["cy"] - 1.85, c["slide"]["cx"] + 4.3, c["slide"]["cy"] + 1.85), BT, BT + 3.9))
    o = c["oled"]
    obs.append(("OLED module", box(o["cx"] - o["w"] / 2, o["cy"] - o["h"] / 2, o["cx"] + o["w"] / 2, o["cy"] + o["h"] / 2), 6.2, H + 8))
    obs.append(("reset button", box(c["rst"]["cx"] - 2.25, c["rst"]["cy"] - 1.75, c["rst"]["cx"] + 2.25, c["rst"]["cy"] + 1.75), BT, BT + 3.5))
    m = c["mcu"]
    obs.append(("SuperMini board", box(m["cx"] - m["w"] / 2, m["cy"] - m["h"] / 2, m["cx"] + m["w"] / 2, m["cy"] + m["h"] / 2), BT, BOARD_TOP))
    obs.append(("SuperMini parts", box(m["cx"] - m["w"] / 2 + 2.2, m["cy"] - 6.0, m["cx"] + m["w"] / 2 - 2.2, m["cy"] + 6.0), BOARD_TOP, 5.1))
    return obs


def check(side, data):
    h = data["h"]
    from shapely.prepared import prep
    obs = obstacles(h)
    pre = {rad: [(n, prep(fp.buffer(rad)), z0, z1, fp.buffer(rad).bounds) for n, fp, z0, z1 in obs] for rad in (0.22, R_W, 0.93)}
    inside = prep(h["cavity"].buffer(-R_W))
    hits = []
    items = data["wires"] + [dict(n=f"diode {d['key']}", p=[d["a"], d["k"]], r=0.93, j=[0]) for d in data["diodes"]]
    for w in items:
        pts = np.array(w["p"], float)
        ends = [pts[i] for i in w["j"]]
        for a, b in zip(pts[:-1], pts[1:]):
            n = max(2, int(np.linalg.norm(b - a) / 0.25) + 1)
            for t in np.linspace(0, 1, n):
                q = a + (b - a) * t
                if ends and min(np.linalg.norm(q[:2] - e[:2]) for e in ends) < 1.2:
                    continue                                   # the joint itself: wire meets its pin / pad
                if not inside.contains(Point(q[0], q[1])):
                    hits.append((w["n"], "case wall", q)); break
                if q[2] - w["r"] < BT + 0.05 or q[2] + w["r"] > H - PT - 0.05:
                    hits.append((w["n"], "base/plate", q)); break
                for name, fp, z0, z1, bb in pre[w["r"]]:
                    if z0 - w["r"] < q[2] < z1 + w["r"] and bb[0] <= q[0] <= bb[2] and bb[1] <= q[1] <= bb[3] and fp.contains(Point(q[0], q[1])):
                        hits.append((w["n"], name, q)); break
                else:
                    continue
                break
    return hits


def length(w):
    p = np.array(w["p"]); return float(np.sum(np.linalg.norm(p[1:] - p[:-1], axis=1)))


if __name__ == "__main__":
    out = {}
    for side, nm in (("L", "left"), ("R", "right")):
        d = build(side)
        hits = check(side, d)
        tot = sum(length(w) for w in d["wires"])
        print(f"{nm}: {len(d['wires'])} wires, {len(d['diodes'])} diodes, {tot/1000:.2f} m of wire, {len(hits)} clearance problems")
        seen = set()
        for n, what, q in hits:
            if (n, what) in seen: continue
            seen.add((n, what)); print(f"   {n:38s} hits {what:22s} at ({q[0]:.1f}, {q[1]:.1f}, {q[2]:.2f})")
        out[nm] = dict(wires=d["wires"], diodes=d["diodes"], total_m=round(tot / 1000, 2))
    json.dump(out, open(os.path.join(OUT, "wiring.json"), "w"))
