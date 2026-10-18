/*
 * Air75 Split animated OLED screens: JavaScript twin of zmk-config/src/air75_oled/render.c.
 * Same integer maths, same order of operations. case/oled_check.py runs both on one script of key presses and
 * checks every frame matches byte for byte, so the viewer shows exactly what the keyboard will.
 * AirOled.create(ART, role, seed) -> state; ART = { font, keys } from case/oled_art.py.
 */
(function (root) {
  var W = 128, H = 32, FB_BYTES = W * H / 8, BARS = 27, RINGS = 6, MAXKEYS = 32, BOOT_MS = 1600;
  var CENTRAL = 0, PERIPHERAL = 1, LINK_OPEN = 0, LINK_CONNECTED = 1, LINK_LOST = 2, LINK_USB = 3;
  var BAR_MAX = 21 << 16, GRAV = 45, V_MAX = 14000, PEAK_HOLD = 350, PEAK_FALL = 1000, JITTER_STEP = 3000,
    PULSE_DECAY = 300, HEAT_DECAY = 110, RING_SPEED = 15, RING_MAX = 96, GHOST = 100, MAP_Y0 = 8;
  var IMPULSE = [14000, 11000, 8000, 5000, 2500];
  var BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]];
  var SEG = [[2, 0, 6, 1], [7, 2, 8, 6], [7, 9, 8, 13], [2, 14, 6, 15], [0, 9, 1, 13], [0, 2, 1, 6], [2, 7, 6, 8]];
  var DIGIT_SEGS = [0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F];
  function idiv(a, b) { return (a / b) | 0; }          // C integer division (truncates toward zero)

  function create(ART, role, seed) {
    var F = ART.font, KQX = ART.keys.qx, KX0 = ART.keys.x0q, KW = ART.keys.wq, KROW = ART.keys.row, KLEFT = ART.keys.left,
      NKEYS = ART.keys.n, LKEYS = ART.keys.n_left;
    var s = {
      role: role, t: 0, rng: (seed >>> 0) || 0x2545F491, batt: 255, batt_peer: 255, profile: 0, link: 0, layer: 0, wpm: 0,
      bar_h: new Int32Array(BARS), bar_v: new Int32Array(BARS), peak: new Int32Array(BARS), peak_hold: new Int32Array(BARS),
      wpm_disp: 0, jitter: 0, pulse: 0, heat: new Int32Array(MAXKEYS), held: new Uint8Array(MAXKEYS),
      ring: [], next_ring: 0, dirty: 1, blink_phase: -1
    };
    for (var i = 0; i < RINGS; i++) s.ring.push({ x: 0, y: 0, r: 0, on: 0 });

    function rnd() {
      var x = s.rng;
      x = (x ^ (x << 13)) >>> 0; x = (x ^ (x >>> 17)) >>> 0; x = (x ^ (x << 5)) >>> 0;
      s.rng = x; return x;
    }
    function dith(x, y, level) { return BAYER[y & 3][x & 3] < ((level * 17) >> 8); }
    function pset(fb, x, y, on) {
      if (x < 0 || x >= W || y < 0 || y >= H) return;
      var i = y * (W / 8) + (x >> 3), m = 0x80 >> (x & 7);
      if (on) fb[i] |= m; else fb[i] &= ~m;
    }
    function pxor(fb, x, y) { if (x < 0 || x >= W || y < 0 || y >= H) return; fb[y * (W / 8) + (x >> 3)] ^= 0x80 >> (x & 7); }
    function fill(fb, x0, y0, x1, y1, on) { for (var y = y0; y <= y1; y++) for (var x = x0; x <= x1; x++) pset(fb, x, y, on); }
    function fill_dither(fb, x0, y0, x1, y1, level, mode) {
      for (var y = y0; y <= y1; y++) for (var x = x0; x <= x1; x++) { var on = dith(x, y, level); if (on || mode) pset(fb, x, y, on); }
    }
    function frame(fb, x0, y0, x1, y1) {
      for (var x = x0; x <= x1; x++) { pset(fb, x, y0, 1); pset(fb, x, y1, 1); }
      for (var y = y0; y <= y1; y++) { pset(fb, x0, y, 1); pset(fb, x1, y, 1); }
    }
    function text_w(str) { return str.length ? str.length * 4 - 1 : 0; }
    function glyph(fb, x, y, c, on, scale) {
      var i = c.charCodeAt(0) - 32; if (i < 0 || i >= 96) return;
      for (var r = 0; r < 5; r++) for (var col = 0; col < 3; col++)
        if (F[i][r] & (4 >> col)) fill(fb, x + col * scale, y + r * scale, x + col * scale + scale - 1, y + r * scale + scale - 1, on);
    }
    function text(fb, x, y, str, on) { for (var i = 0; i < str.length; i++) glyph(fb, x + i * 4, y, str[i], on, 1); }
    function chip(fb, x, str) { var w = text_w(str); fill(fb, x, 0, x + w + 1, 6, 1); text(fb, x + 1, 1, str, 0); return x + w + 2; }
    function digit7(fb, x, y, d) {
      var segs = d < 0 ? 0 : DIGIT_SEGS[d];
      for (var i = 0; i < 7; i++) {
        if (segs & (1 << i)) fill(fb, x + SEG[i][0], y + SEG[i][1], x + SEG[i][2], y + SEG[i][3], 1);
        else fill_dither(fb, x + SEG[i][0], y + SEG[i][1], x + SEG[i][2], y + SEG[i][3], GHOST, 0);
      }
    }
    function big_number(fb, n) {
      if (n > 999) n = 999;
      digit7(fb, 91, 10, n >= 100 ? idiv(n, 100) : -1);
      digit7(fb, 102, 10, n >= 10 ? idiv(n, 10) % 10 : -1);
      digit7(fb, 113, 10, n >= 0 ? n % 10 : -1);
    }
    function battery_bar(fb, x, pct) {
      frame(fb, x, 1, x + 11, 5);
      if (pct > 100) { fill_dither(fb, x + 1, 2, x + 10, 4, 70, 0); return; }
      var w = idiv(pct * 10 + 50, 100); if (w > 0) fill(fb, x + 1, 2, x + w, 4, 1);
    }
    function circle(fb, cx, cy, r, level, ymin, xmax) {
      var x = r, y = 0, err = 1 - r;
      while (x >= y) {
        var px = [cx + x, cx + y, cx - y, cx - x, cx - x, cx - y, cx + y, cx + x];
        var py = [cy + y, cy + x, cy + x, cy + y, cy - y, cy - x, cy - x, cy - y];
        for (var i = 0; i < 8; i++) if (py[i] >= ymin && px[i] <= xmax && dith(px[i], py[i], level)) pset(fb, px[i], py[i], 1);
        y++;
        if (err < 0) err += 2 * y + 1; else { x--; err += 2 * (y - x) + 1; }
      }
    }

    function set_status(batt, batt_peer, profile, link, layer, wpm) {
      if (s.batt !== batt || s.batt_peer !== batt_peer || s.profile !== profile || s.link !== link || s.layer !== layer || s.wpm !== wpm) {
        s.batt = batt; s.batt_peer = batt_peer; s.profile = profile; s.link = link; s.layer = layer; s.wpm = wpm; s.dirty = 1;
      }
    }
    function kick(b, imp) {
      if (b < 0 || b >= BARS) return;
      var v = s.bar_v[b] > 0 ? s.bar_v[b] : 0; v += imp; s.bar_v[b] = v > V_MAX ? V_MAX : v;
    }
    function key(position, pressed) {
      if (position < 0 || position >= NKEYS) return;
      if (s.role === CENTRAL) {
        if (!pressed) return;
        var b = idiv(KQX[position] * BARS, 64); if (b > BARS - 1) b = BARS - 1;
        for (var d = 0; d < 5; d++) { kick(b - d, IMPULSE[d]); if (d) kick(b + d, IMPULSE[d]); }
        s.pulse = 65535;
      } else {
        var k = KLEFT[position]; if (k >= LKEYS) return;
        s.held[k] = pressed ? 1 : 0;
        if (pressed) {
          s.heat[k] = 65535;
          var r = s.ring[s.next_ring]; s.next_ring = (s.next_ring + 1) % RINGS;
          r.x = idiv((2 * KX0[position] + KW[position]) * 5, 8); r.y = MAP_Y0 + KROW[position] * 5 + 2; r.r = 0; r.on = 1;
        }
      }
      s.dirty = 1;
    }
    function moving() {
      var i;
      if (s.role === CENTRAL) {
        if (s.pulse > 0 || s.wpm_disp !== s.wpm * 16) return 1;
        for (i = 0; i < BARS; i++) if (s.bar_h[i] > 0 || s.bar_v[i] !== 0 || s.peak[i] > 0) return 1;
      } else {
        for (i = 0; i < LKEYS; i++) if (!s.held[i] && s.heat[i] > 0) return 1;
        for (i = 0; i < RINGS; i++) if (s.ring[i].on) return 1;
      }
      return 0;
    }
    function step(dt) {
      dt = dt | 0; if (dt < 0) dt = 0; if (dt > 100) dt = 100;
      var before = moving(), t0 = s.t, i;
      s.t += dt;
      if (s.role === CENTRAL) {
        s.jitter += s.wpm * dt;
        while (s.jitter >= JITTER_STEP) {
          s.jitter -= JITTER_STEP;
          var r = rnd(), v0 = s.bar_v[r % BARS];
          v0 = (v0 > 0 ? v0 : 0) + 4000 + ((r >>> 8) % 5000);
          s.bar_v[r % BARS] = v0 > V_MAX ? V_MAX : v0;
        }
        for (i = 0; i < BARS; i++) {
          var h = s.bar_h[i], v = s.bar_v[i];
          for (var ms = 0; ms < dt; ms++) {
            v -= GRAV; h += v;
            if (h <= 0) { h = 0; v = 0; }
            if (h >= BAR_MAX) { h = BAR_MAX; if (v > 0) v = 0; }
            if (h > s.peak[i]) { s.peak[i] = h; s.peak_hold[i] = PEAK_HOLD; }
            else if (s.peak_hold[i] > 0) s.peak_hold[i]--;
            else if (s.peak[i] > 0) { s.peak[i] -= PEAK_FALL; if (s.peak[i] < h) s.peak[i] = h; }
          }
          s.bar_h[i] = h; s.bar_v[i] = v;
        }
        s.pulse -= PULSE_DECAY * dt; if (s.pulse < 0) s.pulse = 0;
        var diff = s.wpm * 16 - s.wpm_disp, stepv = idiv(diff * dt, 200);
        if (stepv === 0 && diff !== 0 && dt > 0) stepv = diff > 0 ? 1 : -1;
        s.wpm_disp += stepv;
      } else {
        for (i = 0; i < LKEYS; i++) {
          if (s.held[i]) s.heat[i] = 65535;
          else { s.heat[i] -= HEAT_DECAY * dt; if (s.heat[i] < 0) s.heat[i] = 0; }
        }
        for (i = 0; i < RINGS; i++) if (s.ring[i].on) { s.ring[i].r += RING_SPEED * dt; if ((s.ring[i].r >> 8) > RING_MAX) s.ring[i].on = 0; }
      }
      var need = before || moving() || s.dirty || t0 < BOOT_MS;
      var blinking = s.role === CENTRAL ? s.link === LINK_OPEN : s.link !== LINK_CONNECTED;
      if (blinking) {
        var ph = idiv(s.t, s.role === CENTRAL ? 400 : 300);
        if (ph !== s.blink_phase) { s.blink_phase = ph; need = 1; }
      }
      s.dirty = 0;
      return !!need;
    }

    function draw_boot(fb) {
      var word = 'AIR75', x0 = 35, y0 = 3, x, y;
      for (var i = 0; i < 5; i++) glyph(fb, x0 + i * 12, y0, word[i], 1, 3);
      var sweep = idiv(s.t * 100, BOOT_MS) - 20;
      for (y = y0; y < y0 + 15; y++) for (x = x0; x < x0 + 57; x++) { var d = (x - x0) - (y - y0) - sweep; if (d >= 0 && d < 5) pxor(fb, x, y); }
      var sub = s.role === CENTRAL ? 'RIGHT' : 'LEFT';
      text(fb, idiv(W - text_w(sub), 2), 22, sub, 1);
      for (x = x0; x < x0 + 57; x += 2) pset(fb, x, 30, 1);
      fill(fb, x0, 30, x0 + idiv(s.t * 57, BOOT_MS), 30, 1);
    }
    function draw_central(fb) {
      var x, i, y;
      if (s.link === LINK_USB) x = chip(fb, 0, 'USB');
      else x = chip(fb, 0, 'BT' + String.fromCharCode(49 + s.profile % 9));
      x += 2;
      if (s.link === LINK_CONNECTED || s.link === LINK_USB) fill(fb, x, 2, x + 2, 4, 1);
      else if (s.link === LINK_LOST) glyph(fb, x, 1, 'X', 1, 1);
      else if (idiv(s.t, 400) % 2 === 0) frame(fb, x, 2, x + 2, 4);
      if (s.layer === 0) text(fb, 36, 1, 'BASE', 1);
      else if (s.layer === 1) chip(fb, 36, 'FN');
      else chip(fb, 36, 'L' + String(s.layer));
      glyph(fb, 93, 1, 'L', 1, 1); battery_bar(fb, 97, s.batt_peer);
      glyph(fb, 112, 1, 'R', 1, 1); battery_bar(fb, 116, s.batt);
      for (x = 0; x < W; x += 2) pset(fb, x, 8, 1);
      for (i = 0; i < BARS; i++) {
        var bx = i * 3, h = s.bar_h[i] >> 16;
        for (var k = 0; k < h; k++) if (k % 3 !== 2) { pset(fb, bx, 31 - k, 1); pset(fb, bx + 1, 31 - k, 1); }
        var p = s.peak[i] >> 16;
        if (p > 0) { pset(fb, bx, 31 - p, 1); pset(fb, bx + 1, 31 - p, 1); }
      }
      for (y = 10; y < H; y += 2) pset(fb, 84, y, 1);
      var n = s.wpm_disp >> 4; big_number(fb, n < 0 ? 0 : n);
      text(fb, W - text_w('WPM'), 27, 'WPM', 1);
      if (s.pulse > 0) fill_dither(fb, 111, 28, 113, 30, s.pulse >> 8, 0);
    }
    function draw_peripheral(fb) {
      var i, x, y;
      text(fb, 0, 1, 'AIR75', 1); text(fb, 24, 1, 'LINK', 1);
      if (s.link === LINK_CONNECTED) fill(fb, 41, 2, 43, 4, 1);
      else { var nd = idiv(s.t, 300) % 4; for (i = 0; i < nd; i++) pset(fb, 41 + i * 2, 5, 1); }
      frame(fb, 113, 1, 126, 5); pset(fb, 127, 2, 1); pset(fb, 127, 3, 1); pset(fb, 127, 4, 1);
      if (s.batt <= 100) { var w = idiv(s.batt * 12 + 50, 100); if (w > 0) fill(fb, 114, 2, 113 + w, 4, 1); }
      for (x = 36; x < W; x += 2) pset(fb, x, 8, 1);
      for (i = 0; i < RINGS; i++) if (s.ring[i].on) {
        var r = s.ring[i].r >> 8, lvl = 255 - idiv(r * 255, RING_MAX);
        circle(fb, s.ring[i].x, s.ring[i].y, r, lvl, 9, 82);
        if (r > 6) circle(fb, s.ring[i].x, s.ring[i].y, r - 6, idiv(lvl, 2), 9, 82);
      }
      for (var p = 0; p < NKEYS; p++) {
        var k = KLEFT[p]; if (k >= LKEYS) continue;
        var x0 = idiv(KX0[p] * 5, 4), x1 = idiv((KX0[p] + KW[p]) * 5, 4) - 2, y0 = MAP_Y0 + KROW[p] * 5;
        fill(fb, x0, y0, x1, y0 + 3, 0); frame(fb, x0, y0, x1, y0 + 3);
        fill_dither(fb, x0 + 1, y0 + 1, x1 - 1, y0 + 2, s.heat[k] >> 8, 0);
      }
      for (y = 10; y < H; y += 2) pset(fb, 84, y, 1);
      big_number(fb, s.batt <= 100 ? s.batt : -1);
      text(fb, W - text_w('BAT%'), 27, 'BAT%', 1);
    }
    function draw(fb) {
      fb.fill(0);
      if (s.t < BOOT_MS) draw_boot(fb); else if (s.role === CENTRAL) draw_central(fb); else draw_peripheral(fb);
    }
    return { state: s, set_status: set_status, key: key, step: step, draw: draw };
  }
  var api = { create: create, W: W, H: H, FB_BYTES: FB_BYTES, CENTRAL: CENTRAL, PERIPHERAL: PERIPHERAL,
    LINK_OPEN: LINK_OPEN, LINK_CONNECTED: LINK_CONNECTED, LINK_LOST: LINK_LOST, LINK_USB: LINK_USB };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.AirOled = api;
})(this);
