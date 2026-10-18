/*
 * Air75 Split animated OLED screens: the pixel renderer. See render.h.
 * Keep this file and viewer/oled_render.js in step: cad/oled_check.py compares their frames.
 */
#include <string.h>

#include "air75_oled_data.h"
#include "render.h"

/* ---- tuning (integer units: heights in 1/65536 px, times in ms) ---- */
#define BAR_MAX (21 << 16)      /* 21 px tall */
#define GRAV 45                 /* 1/65536 px per ms^2 */
#define V_MAX 14000             /* fastest a bar can rise */
#define PEAK_HOLD 350           /* ms a peak dot waits before it falls */
#define PEAK_FALL 1000          /* 1/65536 px per ms */
#define JITTER_STEP 3000        /* wpm x ms per random bump */
#define PULSE_DECAY 300
#define HEAT_DECAY 110          /* 65535 -> 0 in about 600 ms */
#define RING_SPEED 15           /* 1/256 px per ms: about 59 px/s */
#define RING_MAX 96             /* px */
#define GHOST 100               /* brightness of unlit seven-segment segments, 0..255 */
#define MAP_Y0 8

static const int32_t IMPULSE[5] = {14000, 11000, 8000, 5000, 2500};
static const uint8_t BAYER[4][4] = {{0, 8, 2, 10}, {12, 4, 14, 6}, {3, 11, 1, 9}, {15, 7, 13, 5}};
/* seven-segment digit, 9 x 16 px: segments a b c d e f g as x0 y0 x1 y1 */
static const uint8_t SEG[7][4] = {{2, 0, 6, 1}, {7, 2, 8, 6}, {7, 9, 8, 13}, {2, 14, 6, 15},
                                  {0, 9, 1, 13}, {0, 2, 1, 6}, {2, 7, 6, 8}};
static const uint8_t DIGIT_SEGS[10] = {0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F};

/* ---- helpers ---- */
static uint32_t rnd(struct air_oled *s) {
    uint32_t x = s->rng;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    s->rng = x;
    return x;
}

static int dith(int x, int y, int level) { return BAYER[y & 3][x & 3] < ((level * 17) >> 8); }

static void pset(uint8_t *fb, int x, int y, int on) {
    if (x < 0 || x >= AIR_W || y < 0 || y >= AIR_H) {
        return;
    }
    int i = y * (AIR_W / 8) + (x >> 3);
    uint8_t m = (uint8_t)(0x80 >> (x & 7));
    if (on) {
        fb[i] |= m;
    } else {
        fb[i] &= (uint8_t)~m;
    }
}

static void pxor(uint8_t *fb, int x, int y) {
    if (x < 0 || x >= AIR_W || y < 0 || y >= AIR_H) {
        return;
    }
    fb[y * (AIR_W / 8) + (x >> 3)] ^= (uint8_t)(0x80 >> (x & 7));
}

static void fill(uint8_t *fb, int x0, int y0, int x1, int y1, int on) {
    for (int y = y0; y <= y1; y++) {
        for (int x = x0; x <= x1; x++) {
            pset(fb, x, y, on);
        }
    }
}

/* level 0..255; mode 0: only light pixels, 1: light or clear every pixel in the box */
static void fill_dither(uint8_t *fb, int x0, int y0, int x1, int y1, int level, int mode) {
    for (int y = y0; y <= y1; y++) {
        for (int x = x0; x <= x1; x++) {
            int on = dith(x, y, level);
            if (on || mode) {
                pset(fb, x, y, on);
            }
        }
    }
}

static void frame(uint8_t *fb, int x0, int y0, int x1, int y1) {
    for (int x = x0; x <= x1; x++) {
        pset(fb, x, y0, 1);
        pset(fb, x, y1, 1);
    }
    for (int y = y0; y <= y1; y++) {
        pset(fb, x0, y, 1);
        pset(fb, x1, y, 1);
    }
}

static int text_w(const char *str) {
    int n = (int)strlen(str);
    return n ? n * 4 - 1 : 0;
}

static void glyph(uint8_t *fb, int x, int y, char c, int on, int scale) {
    int i = (int)(unsigned char)c - 32;
    if (i < 0 || i >= 96) {
        return;
    }
    for (int r = 0; r < 5; r++) {
        for (int col = 0; col < 3; col++) {
            if (AIR_FONT[i][r] & (4 >> col)) {
                fill(fb, x + col * scale, y + r * scale, x + col * scale + scale - 1, y + r * scale + scale - 1, on);
            }
        }
    }
}

static void text(uint8_t *fb, int x, int y, const char *str, int on) {
    for (int i = 0; str[i]; i++) {
        glyph(fb, x + i * 4, y, str[i], on, 1);
    }
}

/* text in an inverted chip; returns the x just past the chip */
static int chip(uint8_t *fb, int x, const char *str) {
    int w = text_w(str);
    fill(fb, x, 0, x + w + 1, 6, 1);
    text(fb, x + 1, 1, str, 0);
    return x + w + 2;
}

static void digit7(uint8_t *fb, int x, int y, int d) {
    int segs = d < 0 ? 0 : DIGIT_SEGS[d];
    for (int i = 0; i < 7; i++) {
        if (segs & (1 << i)) {
            fill(fb, x + SEG[i][0], y + SEG[i][1], x + SEG[i][2], y + SEG[i][3], 1);
        } else {
            fill_dither(fb, x + SEG[i][0], y + SEG[i][1], x + SEG[i][2], y + SEG[i][3], GHOST, 0);
        }
    }
}

/* three seven-segment digits at x 91..121, y 10..25; leading zeros (or every digit if n < 0) glow faintly */
static void big_number(uint8_t *fb, int n) {
    if (n > 999) {
        n = 999;
    }
    digit7(fb, 91, 10, n >= 100 ? n / 100 : -1);
    digit7(fb, 102, 10, n >= 10 ? (n / 10) % 10 : -1);
    digit7(fb, 113, 10, n >= 0 ? n % 10 : -1);
}

static void battery_bar(uint8_t *fb, int x, int pct) {
    frame(fb, x, 1, x + 11, 5);
    if (pct > 100) {
        fill_dither(fb, x + 1, 2, x + 10, 4, 70, 0); /* unknown */
        return;
    }
    int w = (pct * 10 + 50) / 100;
    if (w > 0) {
        fill(fb, x + 1, 2, x + w, 4, 1);
    }
}

static void u2s(char *buf, int v) { /* small unsigned int to text */
    char tmp[6];
    int n = 0;
    do {
        tmp[n++] = (char)('0' + v % 10);
        v /= 10;
    } while (v > 0 && n < 5);
    for (int i = 0; i < n; i++) {
        buf[i] = tmp[n - 1 - i];
    }
    buf[n] = 0;
}

static void circle(uint8_t *fb, int cx, int cy, int r, int level, int ymin, int xmax) {
    int x = r, y = 0, err = 1 - r;
    while (x >= y) {
        const int px[8] = {cx + x, cx + y, cx - y, cx - x, cx - x, cx - y, cx + y, cx + x};
        const int py[8] = {cy + y, cy + x, cy + x, cy + y, cy - y, cy - x, cy - x, cy - y};
        for (int i = 0; i < 8; i++) {
            if (py[i] >= ymin && px[i] <= xmax && dith(px[i], py[i], level)) {
                pset(fb, px[i], py[i], 1);
            }
        }
        y++;
        if (err < 0) {
            err += 2 * y + 1;
        } else {
            x--;
            err += 2 * (y - x) + 1;
        }
    }
}

/* ---- state ---- */
void air_oled_init(struct air_oled *s, uint8_t role, uint32_t seed) {
    memset(s, 0, sizeof(*s));
    s->role = role;
    s->rng = seed ? seed : 0x2545F491u;
    s->batt = 255;
    s->batt_peer = 255;
    s->dirty = 1;
    s->blink_phase = -1;
}

void air_oled_set_status(struct air_oled *s, uint8_t batt, uint8_t batt_peer, uint8_t profile, uint8_t link,
                         uint8_t layer, uint16_t wpm) {
    if (s->batt != batt || s->batt_peer != batt_peer || s->profile != profile || s->link != link ||
        s->layer != layer || s->wpm != wpm) {
        s->batt = batt;
        s->batt_peer = batt_peer;
        s->profile = profile;
        s->link = link;
        s->layer = layer;
        s->wpm = wpm;
        s->dirty = 1;
    }
}

static void kick(struct air_oled *s, int b, int32_t imp) {
    if (b < 0 || b >= AIR_BARS) {
        return;
    }
    int32_t v = s->bar_v[b] > 0 ? s->bar_v[b] : 0;
    v += imp;
    s->bar_v[b] = v > V_MAX ? V_MAX : v;
}

void air_oled_key(struct air_oled *s, uint32_t position, bool pressed) {
    if (position >= AIR_NKEYS) {
        return;
    }
    if (s->role == AIR_CENTRAL) {
        if (!pressed) {
            return;
        }
        int b = AIR_KEY_QX[position] * AIR_BARS / 64;
        if (b > AIR_BARS - 1) {
            b = AIR_BARS - 1;
        }
        for (int d = 0; d < 5; d++) {
            kick(s, b - d, IMPULSE[d]);
            if (d) {
                kick(s, b + d, IMPULSE[d]);
            }
        }
        s->pulse = 65535;
    } else {
        int k = AIR_KEY_LEFT[position];
        if (k >= AIR_LKEYS) {
            return;
        }
        s->held[k] = pressed ? 1 : 0;
        if (pressed) {
            s->heat[k] = 65535;
            struct air_ring *r = &s->ring[s->next_ring];
            s->next_ring = (uint8_t)((s->next_ring + 1) % AIR_RINGS);
            r->x = (2 * AIR_KEY_X0Q[position] + AIR_KEY_WQ[position]) * 5 / 8;
            r->y = MAP_Y0 + AIR_KEY_ROW[position] * 5 + 2;
            r->r = 0;
            r->on = 1;
        }
    }
    s->dirty = 1;
}

static int moving(const struct air_oled *s) {
    if (s->role == AIR_CENTRAL) {
        if (s->pulse > 0 || s->wpm_disp != (int32_t)s->wpm * 16) {
            return 1;
        }
        for (int i = 0; i < AIR_BARS; i++) {
            if (s->bar_h[i] > 0 || s->bar_v[i] != 0 || s->peak[i] > 0) {
                return 1;
            }
        }
    } else {
        for (int i = 0; i < AIR_LKEYS; i++) {
            if (!s->held[i] && s->heat[i] > 0) {
                return 1;
            }
        }
        for (int i = 0; i < AIR_RINGS; i++) {
            if (s->ring[i].on) {
                return 1;
            }
        }
    }
    return 0;
}

bool air_oled_step(struct air_oled *s, int32_t dt) {
    if (dt < 0) {
        dt = 0;
    }
    if (dt > 100) {
        dt = 100;
    }
    int before = moving(s);
    uint32_t t0 = s->t;
    s->t += (uint32_t)dt;

    if (s->role == AIR_CENTRAL) {
        s->jitter += (int32_t)s->wpm * dt;
        while (s->jitter >= JITTER_STEP) {
            s->jitter -= JITTER_STEP;
            uint32_t r = rnd(s);
            int32_t v = s->bar_v[r % AIR_BARS];
            v = (v > 0 ? v : 0) + 4000 + (int32_t)((r >> 8) % 5000);
            s->bar_v[r % AIR_BARS] = v > V_MAX ? V_MAX : v;
        }
        for (int i = 0; i < AIR_BARS; i++) {
            int32_t h = s->bar_h[i], v = s->bar_v[i];
            for (int ms = 0; ms < dt; ms++) {
                v -= GRAV;
                h += v;
                if (h <= 0) {
                    h = 0;
                    v = 0;
                }
                if (h >= BAR_MAX) {
                    h = BAR_MAX;
                    if (v > 0) {
                        v = 0;
                    }
                }
                if (h > s->peak[i]) {
                    s->peak[i] = h;
                    s->peak_hold[i] = PEAK_HOLD;
                } else if (s->peak_hold[i] > 0) {
                    s->peak_hold[i]--;
                } else if (s->peak[i] > 0) {
                    s->peak[i] -= PEAK_FALL;
                    if (s->peak[i] < h) {
                        s->peak[i] = h;
                    }
                }
            }
            s->bar_h[i] = h;
            s->bar_v[i] = v;
        }
        s->pulse -= PULSE_DECAY * dt;
        if (s->pulse < 0) {
            s->pulse = 0;
        }
        int32_t diff = (int32_t)s->wpm * 16 - s->wpm_disp;
        int32_t stepv = diff * dt / 200;
        if (stepv == 0 && diff != 0 && dt > 0) {
            stepv = diff > 0 ? 1 : -1;
        }
        s->wpm_disp += stepv;
    } else {
        for (int i = 0; i < AIR_LKEYS; i++) {
            if (s->held[i]) {
                s->heat[i] = 65535;
            } else {
                s->heat[i] -= HEAT_DECAY * dt;
                if (s->heat[i] < 0) {
                    s->heat[i] = 0;
                }
            }
        }
        for (int i = 0; i < AIR_RINGS; i++) {
            if (s->ring[i].on) {
                s->ring[i].r += RING_SPEED * dt;
                if ((s->ring[i].r >> 8) > RING_MAX) {
                    s->ring[i].on = 0;
                }
            }
        }
    }

    int need = before || moving(s) || s->dirty || t0 < AIR_BOOT_MS;
    int blinking = s->role == AIR_CENTRAL ? s->link == AIR_LINK_OPEN : s->link != AIR_LINK_CONNECTED;
    if (blinking) {
        int32_t ph = (int32_t)(s->t / (s->role == AIR_CENTRAL ? 400 : 300));
        if (ph != s->blink_phase) {
            s->blink_phase = ph;
            need = 1;
        }
    }
    s->dirty = 0;
    return need != 0;
}

/* ---- drawing ---- */
static void draw_boot(const struct air_oled *s, uint8_t *fb) {
    const char *word = "AIR75";
    int x0 = 35, y0 = 3;
    for (int i = 0; i < 5; i++) {
        glyph(fb, x0 + i * 12, y0, word[i], 1, 3);
    }
    int sweep = (int)(s->t * 100 / AIR_BOOT_MS) - 20;
    for (int y = y0; y < y0 + 15; y++) {
        for (int x = x0; x < x0 + 57; x++) {
            int d = (x - x0) - (y - y0) - sweep;
            if (d >= 0 && d < 5) {
                pxor(fb, x, y);
            }
        }
    }
    const char *sub = s->role == AIR_CENTRAL ? "RIGHT" : "LEFT";
    text(fb, (AIR_W - text_w(sub)) / 2, 22, sub, 1);
    for (int x = x0; x < x0 + 57; x += 2) {
        pset(fb, x, 30, 1);
    }
    fill(fb, x0, 30, x0 + (int)(s->t * 57 / AIR_BOOT_MS), 30, 1);
}

static void draw_central(const struct air_oled *s, uint8_t *fb) {
    char buf[8];
    /* status: [BT 2] link   BASE / [FN]   L ▮▮▮  R ▮▮▮ */
    int x;
    if (s->link == AIR_LINK_USB) {
        x = chip(fb, 0, "USB");
    } else {
        buf[0] = 'B';
        buf[1] = 'T';
        buf[2] = (char)('1' + s->profile % 9);
        buf[3] = 0;
        x = chip(fb, 0, buf);
    }
    x += 2;
    if (s->link == AIR_LINK_CONNECTED || s->link == AIR_LINK_USB) {
        fill(fb, x, 2, x + 2, 4, 1);
    } else if (s->link == AIR_LINK_LOST) {
        glyph(fb, x, 1, 'X', 1, 1);
    } else if ((s->t / 400) % 2 == 0) {
        frame(fb, x, 2, x + 2, 4);
    }
    if (s->layer == 0) {
        text(fb, 36, 1, "BASE", 1);
    } else if (s->layer == 1) {
        chip(fb, 36, "FN");
    } else {
        buf[0] = 'L';
        u2s(buf + 1, s->layer);
        chip(fb, 36, buf);
    }
    glyph(fb, 93, 1, 'L', 1, 1);
    battery_bar(fb, 97, s->batt_peer);
    glyph(fb, 112, 1, 'R', 1, 1);
    battery_bar(fb, 116, s->batt);
    for (x = 0; x < AIR_W; x += 2) {
        pset(fb, x, 8, 1);
    }

    /* spectrum bars, 2 px wide, segmented every third row, with falling peak dots */
    for (int i = 0; i < AIR_BARS; i++) {
        int bx = i * 3;
        int h = s->bar_h[i] >> 16;
        for (int k = 0; k < h; k++) {
            if (k % 3 != 2) {
                pset(fb, bx, 31 - k, 1);
                pset(fb, bx + 1, 31 - k, 1);
            }
        }
        int p = s->peak[i] >> 16;
        if (p > 0) {
            pset(fb, bx, 31 - p, 1);
            pset(fb, bx + 1, 31 - p, 1);
        }
    }
    for (int y = 10; y < AIR_H; y += 2) {
        pset(fb, 84, y, 1);
    }

    /* big seven-segment WPM; leading zeros glow faintly like unlit segments */
    int n = s->wpm_disp >> 4;
    big_number(fb, n < 0 ? 0 : n);
    text(fb, AIR_W - text_w("WPM"), 27, "WPM", 1);
    if (s->pulse > 0) {
        fill_dither(fb, 111, 28, 113, 30, s->pulse >> 8, 0);
    }
}

static void draw_peripheral(const struct air_oled *s, uint8_t *fb) {
    /* status: AIR75  LINK *            [battery] */
    text(fb, 0, 1, "AIR75", 1);
    text(fb, 24, 1, "LINK", 1);
    if (s->link == AIR_LINK_CONNECTED) {
        fill(fb, 41, 2, 43, 4, 1);
    } else {
        int n = (int)((s->t / 300) % 4);
        for (int i = 0; i < n; i++) {
            pset(fb, 41 + i * 2, 5, 1);
        }
    }
    frame(fb, 113, 1, 126, 5);
    pset(fb, 127, 2, 1);
    pset(fb, 127, 3, 1);
    pset(fb, 127, 4, 1);
    if (s->batt <= 100) {
        int w = (s->batt * 12 + 50) / 100;
        if (w > 0) {
            fill(fb, 114, 2, 113 + w, 4, 1);
        }
    }
    for (int x = 36; x < AIR_W; x += 2) { /* divider; the key map below reaches up to row 8 */
        pset(fb, x, 8, 1);
    }

    /* sonar ripples from every key press (a ring and a fainter one trailing it) */
    for (int i = 0; i < AIR_RINGS; i++) {
        if (s->ring[i].on) {
            int r = s->ring[i].r >> 8;
            int lvl = 255 - r * 255 / RING_MAX;
            circle(fb, s->ring[i].x, s->ring[i].y, r, lvl, 9, 82);
            if (r > 6) {
                circle(fb, s->ring[i].x, s->ring[i].y, r - 6, lvl / 2, 9, 82);
            }
        }
    }
    /* mini-map of the left half: crisp key outlines that fill solid when pressed, then fade */
    for (int p = 0; p < AIR_NKEYS; p++) {
        int k = AIR_KEY_LEFT[p];
        if (k >= AIR_LKEYS) {
            continue;
        }
        int x0 = AIR_KEY_X0Q[p] * 5 / 4;
        int x1 = (AIR_KEY_X0Q[p] + AIR_KEY_WQ[p]) * 5 / 4 - 2;
        int y0 = MAP_Y0 + AIR_KEY_ROW[p] * 5;
        fill(fb, x0, y0, x1, y0 + 3, 0);
        frame(fb, x0, y0, x1, y0 + 3);
        fill_dither(fb, x0 + 1, y0 + 1, x1 - 1, y0 + 2, s->heat[k] >> 8, 0);
    }
    for (int y = 10; y < AIR_H; y += 2) {
        pset(fb, 84, y, 1);
    }
    /* the left half's battery in big digits, like the WPM counter on the right */
    big_number(fb, s->batt <= 100 ? s->batt : -1);
    text(fb, AIR_W - text_w("BAT%"), 27, "BAT%", 1);
}

void air_oled_draw(const struct air_oled *s, uint8_t *fb) {
    memset(fb, 0, AIR_FB_BYTES);
    if (s->t < AIR_BOOT_MS) {
        draw_boot(s, fb);
    } else if (s->role == AIR_CENTRAL) {
        draw_central(s, fb);
    } else {
        draw_peripheral(s, fb);
    }
}
