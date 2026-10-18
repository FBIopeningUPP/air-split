/*
 * Air75 Split animated OLED screens: ZMK glue. Key presses arrive as events and are queued; an LVGL timer on the
 * display thread reads the status, steps the animation (render.c) and copies changed pixels to a canvas. When
 * nothing moves it sends nothing to the display, and ZMK blanks the screen when the keyboard goes idle.
 */
#include <string.h>

#include <zephyr/kernel.h>
#include <zephyr/spinlock.h>

#include <lvgl.h>

#include <zmk/display/status_screen.h>
#include <zmk/event_manager.h>
#include <zmk/events/position_state_changed.h>

#if IS_ENABLED(CONFIG_ZMK_BATTERY_REPORTING)
#include <zmk/battery.h>
#endif

#define AIR_IS_CENTRAL (!IS_ENABLED(CONFIG_ZMK_SPLIT) || IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL))

#if AIR_IS_CENTRAL
#include <zmk/endpoints.h>
#include <zmk/keymap.h>
#include <zmk/wpm.h>
#if IS_ENABLED(CONFIG_ZMK_BLE)
#include <zmk/ble.h>
#endif
#if IS_ENABLED(CONFIG_ZMK_SPLIT_BLE_CENTRAL_BATTERY_LEVEL_FETCHING)
#include <zmk/events/battery_state_changed.h>
#endif
#elif IS_ENABLED(CONFIG_ZMK_SPLIT_BLE)
#include <zmk/split/bluetooth/peripheral.h>
#endif

#include "render.h"

/* With inversion-on in the devicetree, an LVGL black pixel lights up on the SSD1306. */
#if IS_ENABLED(CONFIG_AIR75_OLED_SWAP_COLORS)
#define AIR_LIT lv_color_white()
#define AIR_DARK lv_color_black()
#else
#define AIR_LIT lv_color_black()
#define AIR_DARK lv_color_white()
#endif

static struct air_oled st;
static uint8_t fb[AIR_FB_BYTES], shown[AIR_FB_BYTES];
static bool shown_valid;
static lv_color_t cbuf[AIR_W * AIR_H];
static lv_obj_t *canvas;
static int64_t last_ms;

/* ---- key presses: queued from the event thread, drained on the display thread ---- */
#define QN 32
static uint8_t q_pos[QN], q_down[QN];
static uint32_t q_head, q_tail;
static struct k_spinlock q_lock;

static int air_key_listener(const zmk_event_t *eh) {
    const struct zmk_position_state_changed *ev = as_zmk_position_state_changed(eh);
    if (ev != NULL) {
        k_spinlock_key_t key = k_spin_lock(&q_lock);
        if (q_head - q_tail < QN) {
            q_pos[q_head % QN] = (uint8_t)ev->position;
            q_down[q_head % QN] = ev->state ? 1 : 0;
            q_head++;
        }
        k_spin_unlock(&q_lock, key);
    }
    return ZMK_EV_EVENT_BUBBLE;
}

ZMK_LISTENER(air75_oled, air_key_listener);
ZMK_SUBSCRIPTION(air75_oled, zmk_position_state_changed);

#if AIR_IS_CENTRAL && IS_ENABLED(CONFIG_ZMK_SPLIT_BLE_CENTRAL_BATTERY_LEVEL_FETCHING)
static uint8_t peer_batt = 255;

static int air_peer_batt_listener(const zmk_event_t *eh) {
    const struct zmk_peripheral_battery_state_changed *ev = as_zmk_peripheral_battery_state_changed(eh);
    if (ev != NULL) {
        peer_batt = ev->state_of_charge;
    }
    return ZMK_EV_EVENT_BUBBLE;
}

ZMK_LISTENER(air75_oled_peer_batt, air_peer_batt_listener);
ZMK_SUBSCRIPTION(air75_oled_peer_batt, zmk_peripheral_battery_state_changed);
#endif

/* ---- status, read on the display thread ---- */
static void poll_status(void) {
    uint8_t batt = 255, batt_peer = 255, profile = 0, link = AIR_LINK_CONNECTED, layer = 0;
    uint16_t wpm = 0;
#if IS_ENABLED(CONFIG_ZMK_BATTERY_REPORTING)
    batt = zmk_battery_state_of_charge();
#endif
#if AIR_IS_CENTRAL
    struct zmk_endpoint_instance ep = zmk_endpoints_selected();
    if (ep.transport == ZMK_TRANSPORT_USB) {
        link = AIR_LINK_USB;
    } else {
        profile = ep.ble.profile_index;
#if IS_ENABLED(CONFIG_ZMK_BLE)
        if (zmk_ble_active_profile_is_open()) {
            link = AIR_LINK_OPEN;
        } else if (zmk_ble_active_profile_is_connected()) {
            link = AIR_LINK_CONNECTED;
        } else {
            link = AIR_LINK_LOST;
        }
#endif
    }
    layer = zmk_keymap_highest_layer_active();
    wpm = (uint16_t)zmk_wpm_get_state();
#if IS_ENABLED(CONFIG_ZMK_SPLIT_BLE_CENTRAL_BATTERY_LEVEL_FETCHING)
    batt_peer = peer_batt;
#endif
#elif IS_ENABLED(CONFIG_ZMK_SPLIT_BLE)
    link = zmk_split_bt_peripheral_is_connected() ? AIR_LINK_CONNECTED : AIR_LINK_OPEN;
#endif
    air_oled_set_status(&st, batt, batt_peer, profile, link, layer, wpm);
}

/* ---- copy the changed rows/bytes of the frame buffer to the canvas ---- */
static void blit(void) {
    int y0 = AIR_H, y1 = -1, b0 = AIR_W / 8, b1 = -1;
    for (int y = 0; y < AIR_H; y++) {
        for (int b = 0; b < AIR_W / 8; b++) {
            int i = y * (AIR_W / 8) + b;
            if (shown_valid && fb[i] == shown[i]) {
                continue;
            }
            shown[i] = fb[i];
            for (int k = 0; k < 8; k++) {
                cbuf[y * AIR_W + b * 8 + k] = (fb[i] & (0x80 >> k)) ? AIR_LIT : AIR_DARK;
            }
            y0 = MIN(y0, y);
            y1 = MAX(y1, y);
            b0 = MIN(b0, b);
            b1 = MAX(b1, b);
        }
    }
    shown_valid = true;
    if (y1 >= 0) {
        lv_area_t a = {.x1 = (lv_coord_t)(b0 * 8), .y1 = (lv_coord_t)y0,
                       .x2 = (lv_coord_t)(b1 * 8 + 7), .y2 = (lv_coord_t)y1};
        lv_obj_invalidate_area(canvas, &a);
    }
}

static void air_tick(lv_timer_t *timer) {
    ARG_UNUSED(timer);
    int64_t now = k_uptime_get();
    int32_t dt = (int32_t)(now - last_ms);
    last_ms = now;

    for (;;) {
        k_spinlock_key_t key = k_spin_lock(&q_lock);
        if (q_tail == q_head) {
            k_spin_unlock(&q_lock, key);
            break;
        }
        uint8_t pos = q_pos[q_tail % QN], down = q_down[q_tail % QN];
        q_tail++;
        k_spin_unlock(&q_lock, key);
        air_oled_key(&st, pos, down != 0);
    }
    poll_status();
    if (air_oled_step(&st, dt)) {
        air_oled_draw(&st, fb);
        blit();
    }
}

lv_obj_t *zmk_display_status_screen(void) {
    lv_obj_t *screen = lv_obj_create(NULL);
    lv_obj_set_style_bg_color(screen, AIR_DARK, LV_PART_MAIN);
    lv_obj_set_style_bg_opa(screen, LV_OPA_COVER, LV_PART_MAIN);
    lv_obj_set_style_pad_all(screen, 0, LV_PART_MAIN);
    lv_obj_clear_flag(screen, LV_OBJ_FLAG_SCROLLABLE);

    canvas = lv_canvas_create(screen);
    lv_canvas_set_buffer(canvas, cbuf, AIR_W, AIR_H, LV_IMG_CF_TRUE_COLOR);
    lv_obj_align(canvas, LV_ALIGN_TOP_LEFT, 0, 0);

    air_oled_init(&st, AIR_IS_CENTRAL ? AIR_CENTRAL : AIR_PERIPHERAL, k_cycle_get_32());
    poll_status();
    air_oled_step(&st, 0);
    air_oled_draw(&st, fb);
    blit();
    last_ms = k_uptime_get();
    lv_timer_create(air_tick, CONFIG_AIR75_OLED_FRAME_MS, NULL);
    return screen;
}
