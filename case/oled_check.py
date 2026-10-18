"""Check the OLED renderer: the firmware's C code and the viewer's JavaScript twin must draw identical frames.

Builds a realistic script (typing a sentence at about 70 WPM, holding Fn, the link coming up, battery levels arriving),
runs it through zmk-config/src/air75_oled/render.c (compiled with the host gcc) and viewer/oled_render.js (node),
compares every frame byte for byte, and writes animated previews out/oled_right.gif and out/oled_left.gif.
Run after gen_zmk.py.
"""
import json, os, random, subprocess, sys, tempfile
import numpy as np
from PIL import Image, ImageFilter
import oled_art
from layout import build

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SRC = os.path.join(ROOT, "zmk-config", "src", "air75_oled")
OUT = os.path.join(ROOT, "out")
W, H = 128, 32
CENTRAL, PERIPHERAL = 0, 1
LINK_OPEN, LINK_CONNECTED = 0, 1

def positions():
    keys = build()
    by_label = {}
    for i, k in enumerate(keys):
        by_label.setdefault(k["label"], []).append(i)
    return keys, by_label

def script(role):
    """Script lines plus the ms time of each D (frame) line."""
    keys, L = positions()
    rnd = random.Random(7)
    text = "the quick brown fox jumps over the lazy dog 1234 and keeps typing faster"
    events = []                       # (t_ms, line)
    t = 1900                          # start typing just after the boot screen
    for i, ch in enumerate(text):
        if ch == " ":
            pos = L["Space"][(i // 7) % 2]
        else:
            pos = L[ch.upper()][0]
        if i == 44:                   # hold Fn, tap 1 and 2 (F1, F2), let go
            fn = L["Fn"][0]
            events += [(t, f"K {fn} 1"), (t + 120, f"K {L['1'][0]} 1"), (t + 180, f"K {L['1'][0]} 0"),
                       (t + 300, f"K {L['2'][0]} 1"), (t + 360, f"K {L['2'][0]} 0"), (t + 520, f"K {fn} 0")]
            t += 640
        events += [(t, f"K {pos} 1"), (t + 55 + rnd.randint(0, 30), f"K {pos} 0")]
        t += 120 + rnd.randint(0, 90) - min(i, 40)
    end = t + 8000                    # WPM counts down over 6 s, then everything settles
    lines = [f"I {role} 12345"]
    ev = sorted(events)
    j, tm, frames = 0, 0, []
    fn_pos = L["Fn"][0]
    fn_down = False
    presses = []
    while tm <= end:
        while j < len(ev) and ev[j][0] <= tm:
            line = ev[j][1]
            p, d = int(line.split()[1]), int(line.split()[2])
            if p == fn_pos:
                fn_down = d == 1
            if d == 1:
                presses.append(ev[j][0])
            lines.append(line)
            j += 1
        presses = [p for p in presses if tm - p < 6000]
        wpm = round(len(presses) / 5 * 60 / 6)
        link = LINK_OPEN if tm < 2600 else LINK_CONNECTED
        batt_peer = 255 if tm < 3000 else 86
        if role == CENTRAL:
            lines.append(f"T 91 {batt_peer} 1 {link} {1 if fn_down else 0} {wpm}")
        else:                         # the left half only knows its own battery and its link to the right half
            lines.append(f"T 86 255 0 {link} 0 0")
        dt = 20
        lines.append(f"S {dt}")
        tm += dt
        lines.append("D")
        frames.append(tm)
    return "\n".join(lines) + "\n", frames

def run_c(scr):
    exe = os.path.join(tempfile.gettempdir(), "air75_oled_sim")
    cmd = ["gcc", "-std=c99", "-O2", "-Wall", "-Wextra", "-Werror", "-I", SRC, "-o", exe,
           os.path.join(HERE, "oled_sim", "harness.c"), os.path.join(SRC, "render.c")]
    subprocess.run(cmd, check=True)
    return subprocess.run([exe], input=scr, capture_output=True, text=True, check=True).stdout

def run_js(scr):
    art = os.path.join(tempfile.gettempdir(), "air75_oled_art.json")
    json.dump(oled_art.js_data(), open(art, "w"))
    return subprocess.run(["node", os.path.join(HERE, "oled_sim", "harness.js"),
                           os.path.join(ROOT, "viewer", "oled_render.js"), art],
                          input=scr, capture_output=True, text=True, check=True).stdout

def frames_of(out):
    fr = []
    for line in out.splitlines():
        if line.startswith("D "):
            b = bytes.fromhex(line[2:])
            fr.append(np.unpackbits(np.frombuffer(b, dtype=np.uint8)).reshape(H, W))
    return fr

def oled_image(px, scale=4):
    """One frame as it looks on the module: pixel grid, warm-white pixels with a soft glow."""
    big = np.kron(px, np.ones((scale, scale), dtype=np.uint8))
    grid = np.ones((scale, scale), dtype=np.uint8); grid[-1, :] = 0; grid[:, -1] = 0
    big = big * np.tile(grid, (H, W))
    lit = Image.fromarray((big * 255).astype(np.uint8))
    glow = lit.filter(ImageFilter.GaussianBlur(3))
    base = np.zeros((H * scale, W * scale, 3), dtype=np.float32) + np.array([8, 9, 12], dtype=np.float32)
    g = np.asarray(glow, dtype=np.float32)[..., None] / 255.0
    l = np.asarray(lit, dtype=np.float32)[..., None] / 255.0
    col = np.array([214, 238, 255], dtype=np.float32)
    img = base + g * col * 0.55 + l * (col - base)
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))

def gif(frames, path, every=4, scale=3):
    imgs = [oled_image(f, scale) for f in frames[::every]]
    pad = Image.new("RGB", (imgs[0].width + 18, imgs[0].height + 18), (18, 20, 24))
    out = []
    for im in imgs:
        p = pad.copy(); p.paste(im, (9, 9)); out.append(p.convert("P", palette=Image.ADAPTIVE, colors=32))
    out[0].save(path, save_all=True, append_images=out[1:], duration=20 * every, loop=0, optimize=True)

def main():
    hdr = os.path.join(SRC, "air75_oled_data.h")
    if open(hdr).read() != oled_art.c_header():
        print("BAD air75_oled_data.h is stale: run gen_zmk.py"); return 1
    bad = 0
    for role, name in ((CENTRAL, "right"), (PERIPHERAL, "left")):
        scr, times = script(role)
        c, js = run_c(scr), run_js(scr)
        cl, jl = c.splitlines(), js.splitlines()
        diff = [i for i, (a, b) in enumerate(zip(cl, jl)) if a != b]
        same = len(cl) == len(jl) and not diff
        fr = frames_of(c)
        lit = [int(f.sum()) for f in fr]
        redraws = sum(1 for line in cl if line == "S 1")
        print(("OK  " if same else "BAD ") + f"{name}: C and JavaScript frames identical ({len(fr)} frames, "
              f"{redraws} need a redraw, up to {max(lit)} lit pixels)" + ("" if same else f", first difference at line {diff[0] if diff else len(min(cl, jl))}"))
        bad += not same
        idle = cl[-2] == "S 0"
        print(("OK  " if idle else "BAD ") + f"{name}: screen stops redrawing once typing stops")
        bad += not idle
        gif(fr[:int(len(fr) * 0.66)], os.path.join(OUT, f"oled_{name}.gif"))   # boot and typing; skip the idle tail
        oled_image(fr[int(len(fr) * 0.62)]).save(os.path.join(OUT, f"oled_{name}.png"))
    print(f"OLED CHECKS FAILED: {bad}")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
