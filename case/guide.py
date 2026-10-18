import os, collections
import geom as G
from layout import build, ascii_layout, validate
from gen_zmk import ROW_PINS, COL_PINS_L, COL_PINS_R

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
keys = build()
_, info = validate(keys)
sizes = collections.Counter(k["w"] for k in keys)
cap_rows = "\n".join(f"| {w:g}u | {n} |" for w, n in sorted(sizes.items()))
hL, hR = G.half("L"), G.half("R")
bL, bR = hL["bounds"], hR["bounds"]
OX = hR["ox"]
JW = max(bL[2], bR[2] + OX) - min(bL[0], bR[0] + OX)
NMAG = len(hL["magnets"])
P = hL["oled_pose"]

import json
WJ = json.load(open(os.path.join(OUT, "out", "wiring.json")))
WIRE_M = WJ["left"]["total_m"] + WJ["right"]["total_m"]
T = G.thickness()
VOL = {}
import trimesh
for n in ("left_shell", "left_base", "right_shell", "right_base"):
    VOL[n] = trimesh.load(os.path.join(OUT, "out", "stl", n + ".stl")).volume / 1000
PRINT_G = sum(VOL.values()) * 1.24 * 0.75          # PLA, walls + ~20 % infill come out near 75 % of solid
PARTS_G = len(keys) * (1.6 + 1.3 + 0.15) + 2 * 2.5 + 2 * 9.0 + 2 * 1.5 + 2 * NMAG * 0.15 + 18 * 0.4 + 8 + 10   # switch, cap, diode each; boards, batteries, magnets, screws/inserts, wire, stabs
WEIGHT = PRINT_G + PARTS_G

def pin_table(pins, n):
    return "\n".join(f"| C{i} | D{pins[i]} |" for i in range(n))
row_table = "\n".join(f"| R{i} | D{p} |" for i, p in enumerate(ROW_PINS))

md = f"""# Air75 Split — handwired, wireless, low-profile, 65 %

An Air75-style keyboard without the function row (a 65 % layout), in two printed halves that snap together on magnets into one {JW:.0f} x {bL[3]-bL[1]:.1f} mm board, and pull apart when you want a split. Handwired, no PCB, wireless (ZMK over BLE), 8 mm slim case with a {G.EDGE_R} mm rounded edge all round, and a small 0.91" OLED on each half in a bezel tilted {G.OLED_TILT:.0f}° toward you. Blank keycaps. **Every part prints flat with no supports.**

| | Left half | Right half |
|---|---|---|
| Keys | {info['L'][2]} | {info['R'][2]} |
| Outline | {bL[2]-bL[0]:.1f} x {bL[3]-bL[1]:.1f} mm | {bR[2]-bR[0]:.1f} x {bR[3]-bR[1]:.1f} mm |
| Case thickness (desk to plate top) | {G.H_TOTAL:.1f} mm | {G.H_TOTAL:.1f} mm |
| With keycaps, on its feet | {T['on_desk']:.1f} mm | {T['on_desk']:.1f} mm |
| OLED bezel (front / back edge) | {P['z_f']:.1f} / {P['z_b']:.1f} mm | same |
| Matrix | {info['L'][0]} rows x {info['L'][1]} cols | {info['R'][0]} rows x {info['R'][1]} cols |
| Controller | SuperMini nRF52840 (peripheral) | SuperMini nRF52840 (central, talks to the computer) |
| Battery | KP Original 551245, 48 x 14 x 5.1 mm | same |
| Display | 0.91" 128 x 32 OLED (SSD1306, I2C) | same |

Total {len(keys)} keys: the Air75 minus its function row, with the 6.25u spacebar replaced by two 2u spaces (one per half) and an extra 1.25u Fn key on the left. Esc sits where ` was and Del sits beside Backspace; everything from the F-row lives on the Fn layer. Behind the top row is a {G.BAY_D:.0f} mm back bay with the controller, the OLED and the battery side by side.

```
{ascii_layout(keys)}
```

Left half is everything left of the `||`. The Fn key is the last key in the left half's bottom row.

## Fn layer

| Fn + | Does | Fn + | Does |
|---|---|---|---|
| Esc | ` | 1 … = | F1 … F12 |
| Backspace | Delete | Del | Insert |
| PgUp | Home | End | Print Screen |
| Q W E R | Bluetooth profile 1-4 | T | clear current profile |
| Y | USB output | U | Bluetooth output |
| [ / ] | brightness down / up | P | play / pause |
| M | mute | Up / Down | volume up / down |
| Left / Right | previous / next track | Backslash | bootloader |

## OLEDs

- One 0.91" 128 x 32 SSD1306 module per half, on the SuperMini's I2C pins: **SDA = D2, SCL = D3, VCC = 3V3, GND**.
- Each sits in a small printed bezel behind the top row, tilted {G.OLED_TILT:.0f}° toward you so you can read it while typing. The bezel's front edge is {P['z_f'] - G.H_TOTAL:.1f} mm above the deck and its back edge {P['z_b']:.1f} mm above the desk, still below the keycap tops ({T['cap_top']:.1f} mm).
- The bezel is its own part so the case prints without supports. It prints window-face-down (so the face around the screen gets the smooth bed finish), sits flat on the deck, and locates on two {2*G.PEG_R:.1f} mm pegs. The lower half of the module drops through a slot in the deck.
- The glass sits in a pocket under a {G.OLED['lip']} mm lip with a {G.OLED['win_l']} x {G.OLED['win_w']} mm window. Push the module into the bezel from underneath, then put a dab of hot glue at each end of its circuit board.
- Thread the 4 wires through the deck slot, then glue the bezel down with a thin line of CA glue (or 0.2 mm double-sided tape) around its base.
- Remove any header pins and solder the 4 wires straight to the pads from the back of the module.
- The right half (central) shows its battery, the Bluetooth profile, the active layer and a words-per-minute counter; the left half shows its battery and the link to the right half. ZMK turns the screens off when the keyboard sleeps.

## How the halves join

- The seam is a staircase that follows key-cell edges, so no switch is cut. Gap is {G.SEAM_GAP} mm.
- {NMAG} magnet pockets per half (5 x 1 mm N52 discs, pockets 5.2 mm wide, 1.1 mm deep), including one in the back bay. They face each other across the seam.
- A V-shaped tongue on the right half slides into a matching groove on the left half, about 6 to 7 mm above the desk. It stops the halves stepping up or down against each other. Its 45° flanks print cleanly without supports.
- The {G.EDGE_R} mm rounded edge runs straight across the seam and both seam faces are flat, so joined, the halves read as one piece with just a hairline between them.
- To join: line the halves up side by side, then push them together horizontally.
- **Magnet polarity:** glue the magnets so each pair attracts. Stack them on the bench first and mark the faces with a pen before gluing.
- Joined, the halves behave as one board, but each is still its own wireless unit (two batteries, two controllers).

## Thickness

`out/thickness_profile.png` is a true-scale section with every layer dimensioned. Heights are from the desk:

| Layer | Thickness | Top at |
|---|---|---|
| Base plate | {G.BASE_T:.1f} mm | {G.BASE_T:.1f} mm |
| Inside space (wires, diodes, battery, controller) | {G.INTERIOR:.1f} mm | {G.BASE_T + G.INTERIOR:.1f} mm |
| Switch plate | {G.PLATE_T:.1f} mm | **{G.H_TOTAL:.1f} mm (case total)** |
| OLED bezel | tilted {G.OLED_TILT:.0f}° | {P['z_f']:.1f} mm front, {P['z_b']:.1f} mm back |
| Keycap (skirt {G.CAP['skirt']} mm up, cap {G.CAP['h']} mm tall) | | {T['cap_top']:.1f} mm |
| Silicone feet ({G.FOOT_T} mm, sit 0.5 mm in a recess) | +{T['feet']:.1f} mm | **{T['on_desk']:.1f} mm on the desk** |

- Below the plate: the KS-33 body reaches {G.KS33['body_below']} mm below the plate top, its pins {G.KS33['pins_below']} mm and its centre post {G.KS33['post_below']} mm. The post clears the base by {T['post_clearance']:.1f} mm.
- The battery is {G.BATT['t']:.1f} mm thick and sits in a {G.BATT['pocket']} mm pocket in the base, leaving {G.INTERIOR + G.BATT['pocket'] - G.BATT['t']:.1f} mm of air above it.
- The SuperMini lies on 1 mm foam tape: its tallest part (USB-C) tops out at {G.BASE_T + G.MCU['lift'] + G.MCU['t']/2 + G.MCU['usb_h']/2:.1f} mm, under a {G.H_TOTAL - G.PLATE_T:.1f} mm ceiling.
- Expected weight: about {WEIGHT:.0f} g for the whole keyboard (case in PLA about {PRINT_G:.0f} g). An estimate, nothing has been weighed.

## Files

```
out/stl/            STLs in their assembled position: left/right shell, base, OLED bezel, fit_test_plate
out/stl/print_ready/  the same parts already turned the way they go on the bed: open in the slicer and print
out/step/           same parts as STEP
out/*.png           top views, thickness section, wiring sheets (every wire and diode, real routes)
out/wiring.json     3D route of every wire and diode (used by the viewer)
case/               Python that generates everything. Edit geom.py or layout.py, re-run
firmware/           ready-built .uf2 files for both halves and settings_reset
zmk-config/         firmware source: push to GitHub, Actions builds the .uf2 files
viewer/index.html   the 3D studio viewer
bom/index.html      the interactive parts list
```

Regenerate after changing anything:

```
cd case
python3 gen_zmk.py && python3 build.py && python3 verify.py && python3 check_step.py   # verify includes the support check
python3 routing.py     # wire routes + clearance report (should say 0 problems on both halves)
python3 drawings.py && python3 wiring.py && python3 profile.py && python3 guide.py
cd ../viewer && python3 build_viewer.py
```

## Before you print: check these

The switch numbers come from Gateron's KS-33 STEP model, but the stabilizers and printer tolerance are still unknowns. Print `out/stl/fit_test_plate.stl` first (one 1u hole, one 2u hole with stabilizer cutouts, about 15 minutes).

1. **Switch hole** is {G.SW_HOLE} mm square. The switch should click in and hold. If your printer prints holes small, add 0.1 to `SW_HOLE`.
2. **Stabilizer cutouts** use the standard MX plate-mount shape. Gateron's low-profile stabilizers may differ.
3. **Battery:** KP Original 551245 from Zbotic (listed in stock), 48 x 14 x 5.1 mm, 480 mAh listed. Measure it including its protection board: it must be 48 mm or shorter and 5.1 mm or thinner. Real capacity is likely 300 to 400 mAh.
4. **SuperMini** is modelled at 33 x 18 x 1.6 mm with a mid-mount USB-C, from its pinout card.
5. **USB-C slot** is {G.USB_SLOT['w']} x {G.USB_SLOT['h']} mm so the cable's plastic head can enter. Very chunky cable heads may not fit.

## Parts (both halves)

| Qty | Part | Notes |
|---|---|---|
| 2 | SuperMini nRF52840 | nice!nano-compatible, built-in LiPo charger |
| {len(keys)} (+5 spare) | Gateron KS-33 low-profile 2.0 switches | Meckeys sells packs of 10 (Red is the quietest of their three) |
| 5 | Gateron low-profile plate-mount 2u stabilizers | Bksp, Enter, left Shift, both spaces |
| {len(keys)} | 1N4148 diodes, DO-35 | |
| 1 set | Blank low-profile keycaps for Gateron LP | sizes below; or print them |
| 2 | 0.91" 128 x 32 OLED, SSD1306, I2C | GND VCC SCL SDA |
| 2 | KP Original 551245 LiPo | 48 x 14 x 5.1 mm, Zbotic |
| {NMAG*2} | N52 disc magnets, 5 x 1 mm | {NMAG} per half |
| 2 | Slide switch (SS-12D10 class) | power |
| 2 | Right-angle tactile switch | reset |
| {len(hL['posts']) + len(hR['posts'])} | M2 x 4 brass heat-set inserts | {len(hL['posts'])} left, {len(hR['posts'])} right |
| {len(hL['posts']) + len(hR['posts'])} (+4) | M2 x 5 countersunk screws | |
| 1 | 30 AWG silicone wire | {WIRE_M:.1f} m routed, buy 10 m in 4+ colours |
| 8 | 8 mm round silicone feet, 1.5 mm thick | 4 per half |
| 1 | 1 mm double-sided foam tape, Kapton tape, hot glue, CA glue | controller, OLED, battery, bezel |

Keycaps needed:

| Size | Count |
|---|---|
{cap_rows}

You need two 2u keycaps for the spacebars plus one for Backspace. Low-profile sets usually include one or two 2u keys, so check before buying, or print them.

## Print

Every part prints with **no supports**. Open the files in `out/stl/print_ready/`; they are already turned the right way up.

| Part | On the bed | Why |
|---|---|---|
| Shell (x2) | switch plate face down | the plate gets the smooth bed finish; walls, posts and the seam grow straight up |
| Base (x2) | flat, outside face down | foot recesses and countersinks bridge or slope at 45° or less |
| OLED bezel (x2) | window face down | the face around the screen gets the bed finish; the pegs end up on top |
| Fit test plate | flat | |

How the shapes help:

- **Rounded edges** ({G.EDGE_R} mm top, {G.EDGE_RB} mm bottom) are "teardrop" rounds: a true circle, but never steeper than 45° next to the face that sits on the bed, so they print face-down without drooping. They are modelled as true curves (one ring every 3° of arc, real curved faces in the STEP files), so the only steps left are your printer's layers: 0.2 mm is fine, 0.12 mm or 0.1 mm is smoother.
- **Magnet pockets and the reset hole** are teardrop-shaped holes, so their tops (which face down in the printer) never overhang more than 45°.
- **Tongue and groove** have 45° V flanks. The USB-C and power slots are short flat bridges (under 12 mm).
- `verify.py` scans every print-ready part for faces that would need support: at most 0.4 mm² of steep surface per part (rounding noise), widest flat bridge 8.2 mm (the foot recesses).

Settings: PLA or PETG, 0.2 mm layers, 3 to 4 walls, 15 to 20 % infill, a smooth PEI or glass bed for a glossy top. About {PRINT_G:.0f} g of filament for everything. For an even smoother look, lightly sand the rounded edges with 400 then 800 grit.

## Wiring

Every wire and diode has a real 3D route (`case/routing.py`), checked against every switch body, centre post, pin, stabilizer, screw post, the battery, the controller, the OLED and the case walls: **0 clearance problems** on both halves.

- Sheets: `out/wiring_left.png`, `out/wiring_right.png` show each half from underneath with every wire and diode, and the SuperMini with every pad named. The viewer's **Wiring** view shows the same in 3D; hover a wire for its name.
- Mount every switch with its two pins toward you. The column wire goes to the left pin (seen from the top); the other pin goes to the diode, band toward the row wire. Firmware is `col2row`.
- Rows climb the outer side wall, then run behind the top row to the controller. Columns leave their top-row key and run behind the top row too.
- Power, reset and OLED wires run under the OLED, then over the controller to its pads.

Rows (both halves are the same):

| Row | Pin |
|---|---|
{row_table}

Left half columns:

| Column | Pin |
|---|---|
{pin_table(COL_PINS_L, info['L'][1])}

Right half columns:

| Column | Pin |
|---|---|
{pin_table(COL_PINS_R, info['R'][1])}

Battery + goes through the power switch to **B+**; battery − to the **GND** on the right row. Reset button between **RST** and a **GND** on the left row.

## Firmware

Ready-built firmware is in `firmware/`: `air75_split_left.uf2`, `air75_split_right.uf2` and `settings_reset.uf2`, compiled from `zmk-config/` against ZMK v0.3 for the `nice_nano_v2` board (left: 252 KB of flash, right: 295 KB; both well under the 792 KB limit).

1. Double-tap reset on a SuperMini to get its USB drive, then drop a `.uf2` on it.
2. Flash `settings_reset` to both halves first, then `air75_split_left` to the left half and `air75_split_right` to the right.
3. Power both on. They pair to each other; then pair the keyboard with your computer.

To change the keymap and rebuild: create a GitHub repo from `zmk-config/` and push. Actions builds the same three files.

- The **right** half is the central (bigger job, talks to the computer) and runs its radio at +8 dBm; the left runs at 0 dBm.
- The firmware compiles cleanly, but it has not been tried on a real keyboard yet.

## Assembly

1. Fit test, then print the case.
2. Press the {len(hL['posts']) + len(hR['posts'])} heat-set inserts into the post holes from below.
3. Clip the 5 stabilizers into the plate, then all switches.
4. Wire the matrix. Test each key.
5. Fit each OLED into its bezel (hot glue), thread its wires through the deck slot and glue the bezel onto its pegs, the SuperMini on foam tape with its USB-C in the side wall, and the battery in its pocket. Solder battery + through the slide switch to B+, battery − to GND. The bar next to the power slot is ON (slide toward the controller), the dot is OFF.
6. Flash, test, then close the base with the countersunk screws.
7. Glue the magnets into the seam pockets (polarity check first), then slide the halves together.
8. Stick the 8 mm feet into the recesses.
"""
open(os.path.join(OUT, "README.md"), "w").write(md)
print("README written,", len(md.split()), "words")
