/*
 * Air75 Split animated OLED screens: the pixel renderer.
 *
 * Pure C, integer maths only, no ZMK or LVGL: status_screen.c feeds it key presses and status and copies the frame
 * buffer to the display. viewer/oled_render.js is a line-by-line JavaScript twin, and case/oled_check.py runs both on
 * the same script of key presses and checks every frame matches byte for byte.
 *
 * Right half (central): spectrum-analyzer bars that jump where you type across the whole board, peak dots, a big
 * seven-segment WPM counter, Bluetooth profile, layer and both batteries.
 * Left half (peripheral): a live mini-map of the left half's keys that glow and fade, with a ripple from every key
 * press, plus link status and battery.
 */
#pragma once
#include <stdbool.h>
#include <stdint.h>

#define AIR_W 128
#define AIR_H 32
#define AIR_FB_BYTES (AIR_W * AIR_H / 8) /* row-major, 16 bytes per row, leftmost pixel = bit 7 */
#define AIR_BARS 27
#define AIR_RINGS 6
#define AIR_MAXKEYS 32
#define AIR_BOOT_MS 1600

enum air_role { AIR_CENTRAL = 0, AIR_PERIPHERAL = 1 };
enum air_link { AIR_LINK_OPEN = 0, AIR_LINK_CONNECTED = 1, AIR_LINK_LOST = 2, AIR_LINK_USB = 3 };

struct air_ring {
    int32_t x, y, r; /* centre in px, radius in 1/256 px */
    uint8_t on;
};

struct air_oled {
    uint8_t role;
    uint32_t t;   /* ms since start */
    uint32_t rng; /* xorshift32 state, never 0 */
    /* status, set with air_oled_set_status() */
    uint8_t batt, batt_peer; /* 0..100, 255 = unknown */
    uint8_t profile, link, layer;
    uint16_t wpm;
    /* right half */
    int32_t bar_h[AIR_BARS], bar_v[AIR_BARS], peak[AIR_BARS], peak_hold[AIR_BARS];
    int32_t wpm_disp; /* shown WPM x 16, eases toward wpm */
    int32_t jitter;
    int32_t pulse;
    /* left half */
    int32_t heat[AIR_MAXKEYS];
    uint8_t held[AIR_MAXKEYS];
    struct air_ring ring[AIR_RINGS];
    uint8_t next_ring;
    /* redraw bookkeeping */
    uint8_t dirty;
    int32_t blink_phase;
};

void air_oled_init(struct air_oled *s, uint8_t role, uint32_t seed);
void air_oled_set_status(struct air_oled *s, uint8_t batt, uint8_t batt_peer, uint8_t profile, uint8_t link,
                         uint8_t layer, uint16_t wpm);
void air_oled_key(struct air_oled *s, uint32_t position, bool pressed);
/* Advance the animation by dt ms (clamped to 0..100). Returns true when the frame needs to be drawn again. */
bool air_oled_step(struct air_oled *s, int32_t dt);
void air_oled_draw(const struct air_oled *s, uint8_t *fb);
