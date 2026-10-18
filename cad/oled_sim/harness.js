// Runs viewer/oled_render.js on the same script as harness.c and prints every frame (see oled_check.py).
const fs = require('fs');
const AirOled = require(process.argv[2]);
const ART = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const tok = fs.readFileSync(0, 'utf8').split(/\s+/).filter(Boolean);
let i = 0, o = null, out = [];
const fb = new Uint8Array(AirOled.FB_BYTES);
while (i < tok.length) {
  const c = tok[i++];
  if (c === 'I') { const role = +tok[i++], seed = +tok[i++]; o = AirOled.create(ART, role, seed); }
  else if (c === 'T') { const v = tok.slice(i, i + 6).map(Number); i += 6; o.set_status(...v); }
  else if (c === 'K') { const pos = +tok[i++], down = +tok[i++]; o.key(pos, down !== 0); }
  else if (c === 'S') { const dt = +tok[i++]; out.push('S ' + (o.step(dt) ? 1 : 0)); }
  else if (c === 'D') { o.draw(fb); out.push('D ' + Buffer.from(fb).toString('hex')); }
}
process.stdout.write(out.join('\n') + '\n');
