"""Builds two README images from the renders:
    docs/images/stats.png       the strip of big numbers under the banner
    docs/images/colorways.jpg   the six colourway tiles (build/renders/cw_*.png from render.js) in a labelled 3 x 2 sheet
Run by render.js; needs Pillow."""
import glob, os, sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "cad"))
import geom as G
from layout import build
import tents as TN
import paths

TILES = os.path.join(paths.BUILD, "renders")
COLORWAYS = [  # (tile, name, what it is)
    ("cw_cobalt", "Cobalt", "cobalt PLA · chalk + ink, signal accents"),
    ("cw_bone", "Bone", "bone PLA · chalk + ink, signal accents"),
    ("cw_graphite", "Graphite", "graphite PLA · ink + smoke, signal accents"),
    ("cw_sage", "Sage", "sage PLA · chalk + moss, mustard accents"),
    ("cw_signal", "Signal", "signal orange PETG · ink + chalk"),
    ("cw_lilac", "Lilac", "lilac PLA · chalk + plum, butter accents"),
]


def font(size, bold=False):
    for f in (("Inter-SemiBold.otf" if bold else "Inter-Regular.otf"), ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")):
        hits = glob.glob(f"/usr/share/fonts/**/{f}", recursive=True) + glob.glob(f"/Library/Fonts/{f}") + glob.glob(f"C:/Windows/Fonts/{f}")
        if hits:
            return ImageFont.truetype(hits[0], size)
    return ImageFont.load_default(size)


def stats():
    keys = build()
    items = [(f"{G.H_TOTAL:.1f}", "mm", "table to plate", True), (str(len(keys)), "keys", "65 %, in two halves", False),
             ("2", "OLEDs", "custom animations", False), ("0", "PCBs", "wired by hand", False),
             (str(len(TN.ANGLES)), "tent angles", "magnetic wedges", False)]
    W, H = 2400, 360
    im = Image.new("RGB", (W, H), (20, 21, 24)); d = ImageDraw.Draw(im)
    big, unit, sub = font(150, True), font(44, True), font(36)
    cw = W / len(items)
    for i, (n, u, s, accent) in enumerate(items):
        cx = cw * (i + 0.5)
        wn, wu = d.textlength(n, font=big), d.textlength(u, font=unit)
        x0 = cx - (wn + 14 + wu) / 2
        d.text((x0, 40), n, font=big, fill=(232, 85, 45) if accent else (242, 239, 232))
        d.text((x0 + wn + 14, 132), u, font=unit, fill=(242, 239, 232))
        d.text((cx - d.textlength(s, font=sub) / 2, 250), s, font=sub, fill=(160, 162, 168))
        if i:
            d.line([(cw * i, 70), (cw * i, 290)], fill=(48, 50, 56), width=2)
    out = os.path.join(paths.IMAGES, "stats.png")
    im.save(out, optimize=True)
    print("written", os.path.relpath(out, paths.ROOT))


def colorways():
    tiles = [(Image.open(os.path.join(TILES, t + ".png")).convert("RGB"), n, s) for t, n, s in COLORWAYS
             if os.path.exists(os.path.join(TILES, t + ".png"))]
    if len(tiles) < len(COLORWAYS):
        print("colourway tiles missing: run node viewer/render.js colorways"); return
    tw, th = tiles[0][0].size
    sheet = Image.new("RGB", (tw * 3, th * 2), (216, 215, 210)); d = ImageDraw.Draw(sheet)
    name, sub = font(46, True), font(28)
    for i, (im, n, s) in enumerate(tiles):
        x, y = (i % 3) * tw, (i // 3) * th
        sheet.paste(im, (x, y))
        d.text((x + 34, y + 26), n, font=name, fill=(31, 35, 40))
        d.text((x + 34, y + 84), s, font=sub, fill=(90, 95, 102))
        if i % 3:
            d.line([(x, y), (x, y + th)], fill=(200, 199, 194), width=2)
        if i >= 3:
            d.line([(x, y), (x + tw, y)], fill=(200, 199, 194), width=2)
    sheet = sheet.resize((2400, round(sheet.height * 2400 / sheet.width)), Image.LANCZOS)
    out = os.path.join(paths.IMAGES, "colorways.jpg")
    sheet.save(out, quality=88)
    print("written", os.path.relpath(out, paths.ROOT))


if __name__ == "__main__":
    stats()
    colorways()
