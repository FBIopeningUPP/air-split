"""Air75-style layout without the function row (a 65 % board), split into two halves.

Units: keys are described in key-units (1u = 19.05 mm).
Split rule: a key whose centre is left of x = 7.0u goes to the left half.
The 6.25u spacebar is replaced by two 2u spaces (one per half) plus an extra Fn key: 70 keys.
Matrix columns follow physical x position, so handwired column wires run almost straight.
"""
import json, math, os

U = 19.05
SPLIT_X = 7.0

# (label, width_u, zmk_binding_base)
ROWS = [   # 65 %: the Air75 without its function row. Esc takes the ` spot, Del sits beside Backspace.
    [("Esc",1,"&kp ESC")] + [(str(i%10),1,f"&kp N{i%10}") for i in range(1,11)]
        + [("-",1,"&kp MINUS"),("=",1,"&kp EQUAL"),("Bksp",2,"&kp BSPC"),("Del",1,"&kp DEL")],
    [("Tab",1.5,"&kp TAB")] + [(c,1,f"&kp {c}") for c in "QWERTYUIOP"]
        + [("[",1,"&kp LBKT"),("]",1,"&kp RBKT"),("\\",1.5,"&kp BSLH"),("PgUp",1,"&kp PG_UP")],
    [("Caps",1.75,"&kp CAPS")] + [(c,1,f"&kp {c}") for c in "ASDFGHJKL"]
        + [(";",1,"&kp SEMI"),("'",1,"&kp SQT"),("Enter",2.25,"&kp RET"),("PgDn",1,"&kp PG_DN")],
    [("Shift",2.25,"&kp LSHFT")] + [(c,1,f"&kp {c}") for c in "ZXCVBNM"]
        + [(",",1,"&kp COMMA"),(".",1,"&kp DOT"),("/",1,"&kp FSLH"),("Shift",1.75,"&kp RSHFT"),
           ("Up",1,"&kp UP"),("End",1,"&kp END")],
    [("Ctrl",1.25,"&kp LCTRL"),("Win",1.25,"&kp LGUI"),("Alt",1.25,"&kp LALT"),
     ("Space",2,"&kp SPACE"),("Fn",1.25,"&mo 1"),
     ("Space",2,"&kp SPACE"),("Alt",1.5,"&kp RALT"),("Menu",1.25,"&kp K_APP"),("Ctrl",1.25,"&kp RCTRL"),
     ("Left",1,"&kp LEFT"),("Down",1,"&kp DOWN"),("Right",1,"&kp RIGHT")],
]
NROWS = len(ROWS)

# Fn layer overrides: (row, label) -> binding. Everything else is &trans.
FN = {(0, "Esc"): "&kp GRAVE", (0, "Del"): "&kp INS", (0, "Bksp"): "&kp DEL"}
FN.update({(0, lab): f"&kp F{i + 1}" for i, lab in enumerate(["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "="])})
FN.update({
    (1, "PgUp"): "&kp HOME", (3, "End"): "&kp PSCRN", (1, "\\"): "&bootloader",
    (1, "Q"): "&bt BT_SEL 0", (1, "W"): "&bt BT_SEL 1", (1, "E"): "&bt BT_SEL 2", (1, "R"): "&bt BT_SEL 3", (1, "T"): "&bt BT_CLR",
    (1, "Y"): "&out OUT_USB", (1, "U"): "&out OUT_BLE",
    (1, "["): "&kp C_BRI_DN", (1, "]"): "&kp C_BRI_UP",
    (4, "Left"): "&kp C_PREV", (4, "Right"): "&kp C_NEXT", (3, "Up"): "&kp C_VOL_UP", (4, "Down"): "&kp C_VOL_DN",
    (3, "M"): "&kp C_MUTE", (1, "P"): "&kp C_PP",
})

def build():
    keys = []
    for r, row in enumerate(ROWS):
        x = 0.0
        for label, w, bind in row:
            cx = x + w/2
            side = "L" if cx < SPLIT_X - 0.01 else "R"
            keys.append(dict(row=r, label=label, w=w, x0=x, cx=cx, side=side, bind=bind))
            x += w
        assert abs(x-16.0) < 1e-9, (r, x)
    # matrix columns from physical x
    for k in keys:
        if k["side"] == "L":
            k["col_local"] = int(math.floor(k["cx"]))
        else:
            k["col_local"] = int(math.floor(k["cx"] - SPLIT_X))
    # fn bindings
    seen = {}
    for k in keys:
        key = (k["row"], k["label"])
        k["fn"] = FN.get(key, "&trans") if not (k["label"]=="Fn") else "&trans"
    # a duplicated label on a row (e.g. Shift/Alt/Space/Ctrl) never appears in FN, so no ambiguity
    return keys

def halves(keys):
    return {s: [k for k in keys if k["side"] == s] for s in "LR"}

def validate(keys):
    h = halves(keys)
    errs = []
    for s, ks in h.items():
        seen = set()
        for k in ks:
            rc = (k["row"], k["col_local"])
            if rc in seen: errs.append(f"{s} duplicate matrix cell {rc} ({k['label']})")
            seen.add(rc)
    return errs, {s: (NROWS, 1+max(k["col_local"] for k in ks), len(ks)) for s, ks in h.items()}

def ascii_layout(keys):
    out = []
    for r in range(NROWS):
        line = ""
        for k in [k for k in keys if k["row"] == r]:
            width = max(3, int(round(k["w"]*4)))
            cell = k["label"][:width-1].center(width-1)
            line += "|" + cell
            if k["side"] == "L" and k is [q for q in keys if q["row"]==r and q["side"]=="L"][-1]:
                line += "|  ||  "
        out.append(line + "|")
    return "\n".join(out)

if __name__ == "__main__":
    ks = build()
    errs, info = validate(ks)
    print("keys:", len(ks), "| per half (rows, cols, keys):", info)
    print("errors:", errs or "none")
    print(ascii_layout(ks))
    from paths import BUILD
    json.dump(ks, open(os.path.join(BUILD, "layout.json"), "w"), indent=1)
