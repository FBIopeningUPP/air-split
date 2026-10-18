"""Writes the showcase README.md. guide.py calls write() with its numbers, so every figure comes from the model."""
import os
import paths


def pic(name, alt, width=None, ext="jpg"):
    """An image that swaps to its dark version when GitHub is in dark mode."""
    w = f' width="{width}"' if width else ""
    return (f'<picture><source media="(prefers-color-scheme: dark)" srcset="docs/images/{name}_dark.{ext}">'
            f'<img src="docs/images/{name}.{ext}" alt="{alt}"{w}></picture>')


def write(g):
    G, T, P, info, keys, bL = g["G"], g["T"], g["P"], g["info"], g["keys"], g["bL"]
    TN, CV = g["TN"], g["CV"]
    lifts = " / ".join(f"{a}°" for a in TN.ANGLES)
    md = f"""<h1 align="center">Air75 Split</h1>

<p align="center"><b>A {len(keys)}-key wireless keyboard that snaps together on magnets, or pulls apart into a split.</b><br>
{G.H_TOTAL:.0f} mm case · animated OLED on each half · handwired, no PCB · every part prints with no supports</p>

<p align="center">
  <img src="https://img.shields.io/badge/keys-{len(keys)}-555?style=flat-square" alt="{len(keys)} keys">
  <img src="https://img.shields.io/badge/case-{G.H_TOTAL:.0f}%20mm-555?style=flat-square" alt="{G.H_TOTAL:.0f} mm case">
  <img src="https://img.shields.io/badge/firmware-ZMK-555?style=flat-square" alt="ZMK firmware">
  <img src="https://img.shields.io/badge/wireless-nRF52840%20%C3%97%202-555?style=flat-square" alt="2 x nRF52840">
  <img src="https://img.shields.io/badge/supports-none-555?style=flat-square" alt="prints with no supports">
</p>

<p align="center">{pic("render_hero", "Air75 Split, joined, in graphite with ivory keycaps")}</p>

<p align="center">
  <a href="docs/BUILD.md"><b>Build guide</b></a> ·
  <a href="models/print"><b>Print files</b></a> ·
  <a href="firmware"><b>Firmware</b></a> ·
  <a href="viewer/index.html"><b>3D viewer</b></a> ·
  <a href="bom/index.html"><b>Parts list</b></a>
</p>

| **Layout** | {len(keys)} keys, 65 % (an Air75 without its function row), {info['L'][2]} left + {info['R'][2]} right |
|---|---|
| **Size** | {g['JW']:.0f} × {bL[3]-bL[1]:.1f} mm joined |
| **Thickness** | {G.H_TOTAL:.1f} mm case, {T['on_desk']:.1f} mm on the desk with keycaps |
| **Switches** | Gateron KS-33 low profile 2.0 |
| **Brains** | 2 × SuperMini nRF52840, ZMK over Bluetooth, right half talks to the computer |
| **Screens** | 2 × 0.91" 128 × 32 OLED with custom animated firmware |
| **Power** | 2 × 3.7 V LiPo, 48 × 14 × 5.1 mm, one per half |
| **Extras** | snap-on travel covers, magnetic tenting wedges ({lifts}) |

## The screens

Each half has a 0.91" OLED in a printed pod tilted {G.OLED_TILT:.0f}° toward you. They run custom firmware, not ZMK's stock status screen.

<p align="center">{pic("render_oled", "Right screen in the dark: WPM counter and spectrum bars")}</p>

<p align="center">
  <img src="docs/images/oled_right.gif" width="49%" alt="Right screen animation">
  <img src="docs/images/oled_left.gif" width="49%" alt="Left screen animation">
</p>

- **Right:** spectrum bars that jump where you type, a big seven-segment WPM counter, Bluetooth profile, layer and both batteries.
- **Left:** a live map of its {info['L'][2]} keys with ripples from every press, the link to the right half and its battery.
- The screens only redraw while something moves, and switch off when the keyboard sleeps. The 3D viewer runs the same drawing code: a check runs the C and the JavaScript on one typing session and compares every frame byte for byte.

## Joined or split

<p align="center">
  {pic("render_tented", "Halves split and tented on magnetic wedges", "49%")}
  {pic("render_apart", "Halves pulled apart, showing the magnet seam", "49%")}
</p>

- The halves meet on a staircase seam that follows the key edges, held by {len(g['hL']['magnets'])} pairs of magnets with a tongue and groove to keep them level. Joined, only a hairline shows.
- Split them and clip on a magnetic tenting wedge: {lifts}. Each wedge sockets over the rubber feet so it can't slide, and its magnets are hidden in the base.

## Slim

<p align="center">
  {pic("render_slim", "Low view of the case edge", "49%")}
  {pic("render_section", "Cutaway through the case", "49%")}
</p>

{G.BASE_T:.1f} mm base, {G.INTERIOR:.1f} mm inside for wires, diodes, battery and controller, {G.PLATE_T:.1f} mm switch plate: **{G.H_TOTAL:.1f} mm** in all, with a {G.EDGE_R} mm rounded edge. The battery sits in a pocket in the base and the controller lies flat beside the screen.

## Inside

<p align="center">{pic("render_exploded", "Exploded view with every part labelled")}</p>

<p align="center">
  {pic("render_inside", "See-through case with switches and wiring", "49%")}
  {pic("render_wiring", "Underside wiring with the base off", "49%")}
</p>

Every wire and diode has a real 3D route, checked against every switch, post, screw, the battery, the controller and the walls: no collisions on either half. The [wiring sheets](docs/images/wiring_left.png) show them all, ready to solder.

## Travel covers

<p align="center">{pic("render_covers", "Smoke snap-on covers over both halves")}</p>

Smoke PETG covers snap on over the keys for the bag. The top clears the keycaps by {CV.HEAD:.0f} mm, so nothing gets pressed and the board stays asleep. Four flexible tabs hook under the case edge.

## Colours

<p align="center">
  {pic("render_sage", "Sage case", "32%")}
  {pic("render_slate", "Slate case with sky keycaps", "32%")}
  {pic("render_chalk", "Chalk case with graphite keycaps", "32%")}
</p>


## Build one

1. **Print:** everything in [`models/print/`](models/print) is already the right way up and needs no supports. Start with the fit-test plate.
2. **Buy:** the [parts list](bom/index.html) (about 20 parts, all common), or the table in the [build guide](docs/BUILD.md#parts-both-halves).
3. **Wire:** follow the [wiring sheets](docs/images/wiring_left.png): {g['WIRE_M']:.1f} m of 30 AWG wire and {len(keys)} diodes.
4. **Flash:** drop the ready-built `.uf2` files from [`firmware/`](firmware) on each half.

The [build guide](docs/BUILD.md) has the full details: layout, Fn layer, screens, covers, tenting, thickness, printing, wiring pins, firmware and assembly.

To see it in 3D, download [`viewer/index.html`](viewer/index.html) and open it in a browser. You can orbit, explode it, see inside, type on it and watch the screens, try colours and tenting, and export images.

<details>
<summary><b>What's in the repo, and how to rebuild it</b></summary>

{g['REPO'].replace('## What\'s in the repo', '').strip()}

</details>
## Status

The design is complete and checked in software: the models, wire routes, print orientation and firmware all build and pass their checks. **Nobody has built one yet**, so the first build is the real test. Print the fit-test plate first.
"""
    open(os.path.join(paths.ROOT, "README.md"), "w").write(md)
    print("README.md written,", len(md.split()), "words")
