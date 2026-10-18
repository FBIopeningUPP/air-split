"""Where every generated file goes. All scripts import their paths from here."""
import os

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
STL = os.path.join(ROOT, "models", "stl")          # parts in their assembled position
PRINT = os.path.join(ROOT, "models", "print")      # the same parts turned the way they go on the bed
STEP = os.path.join(ROOT, "models", "step")
IMAGES = os.path.join(ROOT, "docs", "images")      # drawings, wiring sheets, OLED previews, renders
BUILD = os.path.join(ROOT, "build")                # intermediate data (layout.json, wiring.json), not committed
ZMK = os.path.join(ROOT, "firmware", "zmk-config")
VIEWER = os.path.join(ROOT, "viewer")

for d in (STL, PRINT, STEP, IMAGES, BUILD):
    os.makedirs(d, exist_ok=True)
