# Air75 Split — handwired, wireless, low-profile, 65 %

An Air75-style keyboard without the function row (a 65 % layout), in two printed halves that snap together on magnets into one 311 x 119.5 mm board, and pull apart when you want a split. Handwired, no PCB, wireless (ZMK over BLE), 8 mm slim case with a 2.5 mm rounded edge all round, and a small 0.91" OLED on each half in a bezel tilted 15° toward you. Blank keycaps. **Every part prints flat with no supports.**

| | Left half | Right half |
|---|---|---|
| Keys | 30 | 40 |
| Outline | 141.1 x 119.5 mm | 184.2 x 119.5 mm |
| Case thickness (desk to plate top) | 8.0 mm | 8.0 mm |
| With keycaps, on its feet | 16.4 mm | 16.4 mm |
| OLED bezel (front / back edge) | 9.0 / 13.0 mm | same |
| Matrix | 5 rows x 7 cols | 5 rows x 9 cols |
| Controller | SuperMini nRF52840 (peripheral) | SuperMini nRF52840 (central, talks to the computer) |
| Battery | KP Original 551245, 48 x 14 x 5.1 mm | same |
| Display | 0.91" 128 x 32 OLED (SSD1306, I2C) | same |

Total 70 keys: the Air75 minus its function row, with the 6.25u spacebar replaced by two 2u spaces (one per half) and an extra 1.25u Fn key on the left. Esc sits where ` was and Del sits beside Backspace; everything from the F-row lives on the Fn layer. Behind the top row is a 21 mm back bay with the controller, the OLED and the battery side by side.

```
|Esc| 1 | 2 | 3 | 4 | 5 | 6 |  ||  | 7 | 8 | 9 | 0 | - | = |  Bksp |Del|
| Tab | Q | W | E | R | T |  ||  | Y | U | I | O | P | [ | ] |  \  |PgU|
| Caps | A | S | D | F | G |  ||  | H | J | K | L | ; | ' | Enter  |PgD|
| Shift  | Z | X | C | V | B |  ||  | N | M | , | . | / |Shift | Up|End|
|Ctrl|Win |Alt | Space | Fn |  ||  | Space | Alt |Menu|Ctrl|Lef|Dow|Rig|
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
- Each sits in a small printed bezel behind the top row, tilted 15° toward you so you can read it while typing. The bezel's front edge is 1.0 mm above the deck and its back edge 13.0 mm above the desk, still below the keycap tops (15.4 mm).
- The bezel is its own part so the case prints without supports. It prints window-face-down (so the face around the screen gets the smooth bed finish), sits flat on the deck, and locates on two 1.1 mm pegs. The lower half of the module drops through a slot in the deck.
- The bezel is a tapered pod: its ends slope down onto the deck at 48°, its back at 58°, with rounded corners, so it blends into the case instead of sitting on it like a box. The ends are close to the gentlest slope that still prints face-down without supports (46°); the back is as gentle as the deck behind it allows. Its back wall is solid all the way down to the deck.
- The glass sits in a pocket under a 0.4 mm lip with a 26.0 x 8.4 mm window. Push the module into the bezel from underneath, then put a dab of hot glue at each end of its circuit board.
- Thread the 4 wires through the deck slot, then glue the bezel down with a thin line of CA glue (or 0.2 mm double-sided tape) around its base.
- Remove any header pins and solder the 4 wires straight to the pads from the back of the module.
- Both screens run custom animated firmware (`zmk-config/src/air75_oled/`). Each plays a short "AIR75" boot sweep.
- **Right half:** spectrum-analyzer bars that jump at the spot on the board where you type, with peak dots that hang and fall; a big seven-segment WPM counter whose unlit segments glow faintly; the Bluetooth profile and link; the active layer (an inverted FN tag while you hold Fn); and both halves' batteries.
- **Left half:** a live map of its 30 keys that fill when pressed and fade out, sonar ripples from every key press, the link to the right half, and its battery in big digits.

  ![Right screen](out/oled_right.gif) ![Left screen](out/oled_left.gif)

- The 3D viewer runs the same drawing code: `case/oled_check.py` runs the C renderer and the viewer's JavaScript copy on the same typing session and checks every frame matches byte for byte.
- Battery: the screens only redraw while something moves (25 frames a second while you type, nothing when you stop), and ZMK turns them off when the keyboard goes idle. The bus to the screens runs at 400 kHz, so a full frame takes about 12 ms. To go back to ZMK's plain status screen, add `CONFIG_ZMK_DISPLAY_STATUS_SCREEN_BUILT_IN=y` to `zmk-config/config/air75_split.conf`.

## Key covers

Two snap-on covers, one per half, for carrying the keyboard in a bag (`out/stl/print_ready/left_cover.stl`, `right_cover.stl`). The viewer's **Covers** view shows them snapping on.

- The top sits 1.0 mm above the keycaps, so nothing presses a key and the keyboard stays asleep in the bag.
- Four snap tabs per cover (two front, two back) flex out on slots and hook under the case's rounded bottom edge. Their hooks follow the edge 0.05 mm away and reach 0.42 mm under it. Push the cover straight down until it clicks; pull at a front corner to take it off.
- The tabs stop above the desk, so a covered half still stands on its feet. A notch in the back skirt keeps the power switch and reset hole reachable: switch the halves off before packing them.
- The covers only go on with the halves apart (the skirt wraps the seam side too). The right cover leaves room for the V tongue on the seam.
- Top edge: a 45° chamfer, which prints cleanly face-down. "AIR75" and "SPLIT" are pressed 0.5 mm into the tops.
- Print in smoke or clear PETG so the keys and screens show through: top face down, no supports, 0.2 mm layers, 4 walls (the 1.6 mm walls print solid). About 113 g for the pair.
- Snap fit depends on your printer. If a cover is too tight, sand the hooks lightly; if too loose, a thin strip of tape on the hook face firms it up.

## How the halves join

- The seam is a staircase that follows key-cell edges, so no switch is cut. Gap is 0.2 mm.
- 6 magnet pockets per half (5 x 1 mm N52 discs, pockets 5.2 mm wide, 1.1 mm deep), including one in the back bay. They face each other across the seam.
- A V-shaped tongue on the right half slides into a matching groove on the left half, about 6 to 7 mm above the desk. It stops the halves stepping up or down against each other. Its 45° flanks print cleanly without supports. Both stop 1.6 to 2.0 mm inside the outer wall, so from outside you only see the hairline.
- The 2.5 mm rounded edge runs straight across the seam and both seam faces are flat, so joined, the halves read as one piece with just a hairline between them.
- To join: line the halves up side by side, then push them together horizontally.
- **Magnet polarity:** glue the magnets so each pair attracts. Stack them on the bench first and mark the faces with a pen before gluing.
- Joined, the halves behave as one board, but each is still its own wireless unit (two batteries, two controllers).

## Thickness

`out/thickness_profile.png` is a true-scale section with every layer dimensioned. Heights are from the desk:

| Layer | Thickness | Top at |
|---|---|---|
| Base plate | 1.6 mm | 1.6 mm |
| Inside space (wires, diodes, battery, controller) | 5.2 mm | 6.8 mm |
| Switch plate | 1.2 mm | **8.0 mm (case total)** |
| OLED bezel | tilted 15° | 9.0 mm front, 13.0 mm back |
| Keycap (skirt 3.4 mm up, cap 4.0 mm tall) | | 15.4 mm |
| Silicone feet (1.5 mm, sit 0.5 mm in a recess) | +1.0 mm | **16.4 mm on the desk** |

- Below the plate: the KS-33 body reaches 2.55 mm below the plate top, its pins 4.95 mm and its centre post 5.8 mm. The post clears the base by 0.6 mm.
- The battery is 5.1 mm thick and sits in a 0.6 mm pocket in the base, leaving 0.7 mm of air above it.
- The SuperMini lies on 1 mm foam tape: its tallest part (USB-C) tops out at 5.0 mm, under a 6.8 mm ceiling.
- Expected weight: about 353 g for the whole keyboard (case in PLA about 87 g). An estimate, nothing has been weighed.

## Files

```
out/stl/            STLs in their assembled position: left/right shell, base, OLED bezel, key cover, fit_test_plate
out/stl/print_ready/  the same parts already turned the way they go on the bed: open in the slicer and print
out/step/           same parts as STEP
out/*.png           top views, thickness section, wiring sheets (every wire and diode, real routes)
out/wiring.json     3D route of every wire and diode (used by the viewer)
case/               Python that generates everything. Edit geom.py or layout.py, re-run
firmware/           ready-built .uf2 files for both halves and settings_reset
zmk-config/         firmware source: push to GitHub, Actions builds the .uf2 files
zmk-config/src/air75_oled/  the animated screens (render.c draws, status_screen.c connects it to ZMK)
out/oled_*.gif      what each screen shows while you type
viewer/index.html   the 3D studio viewer
bom/index.html      the interactive parts list
```

Regenerate after changing anything:

```
cd case
python3 gen_zmk.py && python3 build.py && python3 verify.py && python3 check_step.py   # verify includes the support check
python3 routing.py     # wire routes + clearance report (should say 0 problems on both halves)
python3 oled_check.py  # screens: C and viewer frames identical, writes out/oled_*.gif
python3 drawings.py && python3 wiring.py && python3 profile.py && python3 guide.py
cd ../viewer && python3 build_viewer.py
```

## Before you print: check these

The switch numbers come from Gateron's KS-33 STEP model, but the stabilizers and printer tolerance are still unknowns. Print `out/stl/fit_test_plate.stl` first (one 1u hole, one 2u hole with stabilizer cutouts, about 15 minutes).

1. **Switch hole** is 14.0 mm square. The switch should click in and hold. If your printer prints holes small, add 0.1 to `SW_HOLE`.
2. **Stabilizer cutouts** use the standard MX plate-mount shape. Gateron's low-profile stabilizers may differ.
3. **Battery:** KP Original 551245 from Zbotic (listed in stock), 48 x 14 x 5.1 mm, 480 mAh listed. Measure it including its protection board: it must be 48 mm or shorter and 5.1 mm or thinner. Real capacity is likely 300 to 400 mAh.
4. **SuperMini** is modelled at 33 x 18 x 1.6 mm with a mid-mount USB-C, from its pinout card.
5. **USB-C slot** is 11.0 x 6.2 mm so the cable's plastic head can enter. Very chunky cable heads may not fit.

## Parts (both halves)

| Qty | Part | Notes |
|---|---|---|
| 2 | SuperMini nRF52840 | nice!nano-compatible, built-in LiPo charger |
| 70 (+5 spare) | Gateron KS-33 low-profile 2.0 switches | Meckeys sells packs of 10 (Red is the quietest of their three) |
| 5 | Gateron low-profile plate-mount 2u stabilizers | Bksp, Enter, left Shift, both spaces |
| 70 | 1N4148 diodes, DO-35 | |
| 1 set | Blank low-profile keycaps for Gateron LP | sizes below; or print them |
| 2 | 0.91" 128 x 32 OLED, SSD1306, I2C | GND VCC SCL SDA |
| 2 | KP Original 551245 LiPo | 48 x 14 x 5.1 mm, Zbotic |
| 12 | N52 disc magnets, 5 x 1 mm | 6 per half |
| 2 | Slide switch (SS-12D10 class) | power |
| 2 | Right-angle tactile switch | reset |
| 18 | M2 x 4 brass heat-set inserts | 8 left, 10 right |
| 18 (+4) | M2 x 5 countersunk screws | |
| 1 | 30 AWG silicone wire | 7.7 m routed, buy 10 m in 4+ colours |
| 8 | 8 mm round silicone feet, 1.5 mm thick | 4 per half |
| 1 | 1 mm double-sided foam tape, Kapton tape, hot glue, CA glue | controller, OLED, battery, bezel |

Keycaps needed:

| Size | Count |
|---|---|
| 1u | 54 |
| 1.25u | 6 |
| 1.5u | 3 |
| 1.75u | 2 |
| 2u | 3 |
| 2.25u | 2 |

You need two 2u keycaps for the spacebars plus one for Backspace. Low-profile sets usually include one or two 2u keys, so check before buying, or print them.

## Print

Every part prints with **no supports**. Open the files in `out/stl/print_ready/`; they are already turned the right way up.

| Part | On the bed | Why |
|---|---|---|
| Shell (x2) | switch plate face down | the plate gets the smooth bed finish; walls, posts and the seam grow straight up |
| Base (x2) | flat, outside face down | foot recesses and countersinks bridge or slope at 45° or less |
| OLED bezel (x2) | window face down | the face around the screen gets the bed finish; the pegs end up on top |
| Key cover (x2) | top face down | the top gets the bed finish; skirt and snap tabs grow straight up |
| Fit test plate | flat | |

How the shapes help:

- **Rounded edges** (2.5 mm top, 0.8 mm bottom) are "teardrop" rounds: a true circle, but never steeper than 45° next to the face that sits on the bed, so they print face-down without drooping. They are modelled as true curves (one ring every 3° of arc, real curved faces in the STEP files), so the only steps left are your printer's layers: 0.2 mm is fine, 0.12 mm or 0.1 mm is smoother.
- **Magnet pockets and the reset hole** are teardrop-shaped holes, so their tops (which face down in the printer) never overhang more than 45°.
- **Tongue and groove** have 45° V flanks. The USB-C opening has rounded upper corners and 45° chamfered lower corners (the lower ones face down while printing). The USB-C and power slots are short flat bridges (under 12 mm).
- `verify.py` scans every print-ready part for faces that would need support: at most 0.4 mm² of steep surface per part (rounding noise), widest flat bridge 8.2 mm (the foot recesses).

Settings: PLA or PETG, 0.2 mm layers, 3 to 4 walls, 15 to 20 % infill, a smooth PEI or glass bed for a glossy top. About 87 g of filament for everything. For an even smoother look, lightly sand the rounded edges with 400 then 800 grit.

## Wiring

Every wire and diode has a real 3D route (`case/routing.py`), checked against every switch body, centre post, pin, stabilizer, screw post, the battery, the controller, the OLED and the case walls: **0 clearance problems** on both halves.

- Sheets: `out/wiring_left.png`, `out/wiring_right.png` show each half from underneath with every wire and diode, and the SuperMini with every pad named. The viewer's **Wiring** view shows the same in 3D; hover a wire for its name.
- Mount every switch with its two pins toward you. The column wire goes to the left pin (seen from the top); the other pin goes to the diode, band toward the row wire. Firmware is `col2row`.
- Rows climb the outer side wall, then run behind the top row to the controller. Columns leave their top-row key and run behind the top row too.
- Power, reset and OLED wires run under the OLED, then over the controller to its pads.

Rows (both halves are the same):

| Row | Pin |
|---|---|
| R0 | D21 |
| R1 | D20 |
| R2 | D19 |
| R3 | D18 |
| R4 | D15 |

Left half columns:

| Column | Pin |
|---|---|
| C0 | D4 |
| C1 | D5 |
| C2 | D6 |
| C3 | D7 |
| C4 | D8 |
| C5 | D9 |
| C6 | D1 |

Right half columns:

| Column | Pin |
|---|---|
| C0 | D4 |
| C1 | D5 |
| C2 | D6 |
| C3 | D7 |
| C4 | D8 |
| C5 | D9 |
| C6 | D1 |
| C7 | D0 |
| C8 | DP1.01 |

Battery + goes through the power switch to **B+**; battery − to the **GND** on the right row. Reset button between **RST** and a **GND** on the left row.

## Firmware

Ready-built firmware is in `firmware/`: `air75_split_left.uf2`, `air75_split_right.uf2` and `settings_reset.uf2`, compiled from `zmk-config/` against ZMK v0.3 for the `nice_nano_v2` board (left: 240 KB of flash, right: 282 KB; both well under the 792 KB limit).

1. Double-tap reset on a SuperMini to get its USB drive, then drop a `.uf2` on it.
2. Flash `settings_reset` to both halves first, then `air75_split_left` to the left half and `air75_split_right` to the right.
3. Power both on. They pair to each other; then pair the keyboard with your computer.

To change the keymap and rebuild: create a GitHub repo from `zmk-config/` and push. Actions builds the same three files.

- The **right** half is the central (bigger job, talks to the computer) and runs its radio at +8 dBm; the left runs at 0 dBm.
- The firmware compiles cleanly, but it has not been tried on a real keyboard yet.

## Assembly

1. Fit test, then print the case.
2. Press the 18 heat-set inserts into the post holes from below.
3. Clip the 5 stabilizers into the plate, then all switches.
4. Wire the matrix. Test each key.
5. Fit each OLED into its bezel (hot glue), thread its wires through the deck slot and glue the bezel onto its pegs, the SuperMini on foam tape with its USB-C in the side wall, and the battery in its pocket. Solder battery + through the slide switch to B+, battery − to GND. The bar next to the power slot is ON (slide toward the controller), the dot is OFF.
6. Flash, test, then close the base with the countersunk screws.
7. Glue the magnets into the seam pockets (polarity check first), then slide the halves together.
8. Stick the 8 mm feet into the recesses.
