/* Runs zmk-config/src/air75_oled/render.c on a script from stdin and prints every frame (see oled_check.py). */
#include <stdio.h>
#include <string.h>
#include "render.h"

int main(void) {
    static struct air_oled s;
    static uint8_t fb[AIR_FB_BYTES];
    char cmd[8];
    while (scanf("%7s", cmd) == 1) {
        if (!strcmp(cmd, "I")) {
            unsigned role, seed;
            if (scanf("%u %u", &role, &seed) != 2) return 1;
            air_oled_init(&s, (uint8_t)role, seed);
        } else if (!strcmp(cmd, "T")) {
            unsigned b, bp, p, l, ly, w;
            if (scanf("%u %u %u %u %u %u", &b, &bp, &p, &l, &ly, &w) != 6) return 1;
            air_oled_set_status(&s, (uint8_t)b, (uint8_t)bp, (uint8_t)p, (uint8_t)l, (uint8_t)ly, (uint16_t)w);
        } else if (!strcmp(cmd, "K")) {
            unsigned pos, down;
            if (scanf("%u %u", &pos, &down) != 2) return 1;
            air_oled_key(&s, pos, down != 0);
        } else if (!strcmp(cmd, "S")) {
            int dt;
            if (scanf("%d", &dt) != 1) return 1;
            printf("S %d\n", air_oled_step(&s, dt) ? 1 : 0);
        } else if (!strcmp(cmd, "D")) {
            air_oled_draw(&s, fb);
            printf("D ");
            for (int i = 0; i < AIR_FB_BYTES; i++) printf("%02x", fb[i]);
            printf("\n");
        }
    }
    return 0;
}
