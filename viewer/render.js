// Renders the README images from the 3D viewer: still shots and a turntable GIF.
//
//   node viewer/render.js                 all shots
//   node viewer/render.js hero top        only these
//
// Needs Playwright (npm i -g playwright) and ffmpeg for the GIF. If the machine can't reach the CDN, point THREE_DIR at
// a local copy of three@0.128.0 (the folder that holds build/ and examples/).
const path = require('path'), fs = require('fs'), { execFileSync } = require('child_process');
const { chromium } = require('playwright');

const ROOT = path.join(__dirname, '..');
const IMG = path.join(ROOT, 'docs', 'images');
const TMP = path.join(ROOT, 'build', 'renders');
const W = 1920, H = 1080, SS = 2;                   // final size, supersampling factor

// cam: [azimuth deg (0 = from the front), elevation deg, share of the frame width the board fills, target shift x, y, z mm]
const SHOTS = {
  hero:     { view: 'asm', lights: 'day', type: 1500, cam: [-26, 30, 0.84, 0, 0, 0] },
  top:      { view: 'asm', lights: 'day', cam: [0, 89.5, 0.84, 0, 0, 0] },
  slim:     { view: 'asm', lights: 'day', cam: [-58, 5, 1.7, -95, -20, 6] },
  oled:     { view: 'asm', lights: 'night', type: 3000, close: 'oled', bg: 'black' },
  tented:   { view: 'asm', lights: 'day', tent: 10, cam: [0, 14, 0.8, 0, 0, 10] },
  covers:   { view: 'covers', lights: 'day', cover: 2400, cam: [-26, 30, 0.82, 0, 0, 0] },
  exploded: { view: 'explode', lights: 'day', cam: [-30, 20, 0.6, 0, 0, 24] },
  inside:   { view: 'inside', lights: 'day', cam: [-24, 40, 0.84, 0, 0, 0] },
  wiring:   { view: 'wiring', lights: 'day', cam: [0, -62, 0.84, 0, 0, 0] },
  apart:    { view: 'apart', lights: 'day', cam: [-18, 42, 0.84, 0, 0, 0] },
  section:  { view: 'section', lights: 'day', cam: [70, 14, 2.4, 0, 0, 6, 'cut'] },
  sage:     { view: 'asm', lights: 'day', colors: [2, 0], cam: [-26, 30, 0.84, 0, 0, 0], size: [1280, 720] },
  slate:    { view: 'asm', lights: 'day', colors: [3, 4], cam: [-26, 30, 0.84, 0, 0, 0], size: [1280, 720] },
  chalk:    { view: 'asm', lights: 'day', colors: [1, 1], cam: [-26, 30, 0.84, 0, 0, 0], size: [1280, 720] },
};

async function setup(page, s) {
  await page.evaluate((s) => {
    const A = window.__air75;
    A.setView(s.view); A.setLights(s.lights);
    if (s.colors) {
      document.querySelectorAll('#caseSw .sw')[s.colors[0]].click();
      document.querySelectorAll('#capSw .sw')[s.colors[1]].click();
    }
    if (s.tent) A.setTent(s.tent);
    if (s.close) A.closeUp(s.close);
  }, s);
  if (s.type) {                                     // type for a while so the screens have something to show
    const text = 'the quick brown fox jumps over the lazy dog ';
    const t0 = Date.now();
    for (let i = 0; Date.now() - t0 < s.type; i++) {
      const ch = text[i % text.length], code = ch === ' ' ? 'Space' : 'Key' + ch.toUpperCase();
      await page.evaluate((c) => window.__air75.press(c), code);
      await page.waitForTimeout(60);
      await page.evaluate((c) => window.__air75.release(c), code);
      await page.waitForTimeout(70);
    }
  }
  await page.waitForTimeout(1200);                  // camera flights finish
  if (s.cover !== undefined) await page.evaluate((ms) => window.__air75.coverAt(ms), s.cover);
  if (s.cam) await page.evaluate((cam) => {
    const A = window.__air75, T = A.THREE, c = A.controls, m = A.center();
    A.stop();
    const tgt = m.c.clone().add(new T.Vector3(cam[3], cam[4], cam[5]));
    if (cam[6] === 'cut') tgt.x = A.cutX() + cam[3];                                       // section: aim at the cut face
    const half = Math.atan(Math.tan(T.MathUtils.degToRad(A.camera.fov) / 2) * 16 / 9);   // horizontal half-angle of a 16:9 frame
    const d0 = m.size.x / (2 * cam[2] * Math.tan(half));                                   // cam[2]: share of the frame width the board fills
    const az = cam[0] * Math.PI / 180, el = cam[1] * Math.PI / 180;
    A.camera.position.set(tgt.x + d0 * Math.cos(el) * Math.sin(az), tgt.y - d0 * Math.cos(el) * Math.cos(az), tgt.z + d0 * Math.sin(el));
    c.target.copy(tgt); c.autoRotate = false; c.update(); A.redraw();
  }, s.cam);
  await page.waitForTimeout(400);
}

async function still(page, name, s) {
  await setup(page, s);
  const [w, h] = s.size || [W, H];
  const url = await page.evaluate((o) => window.__air75.snapshot(o), { shape: '16:9', size: String(w * SS), bg: s.bg || 'studio', out: [w, h], fmt: 'image/jpeg' });
  const f = path.join(IMG, `render_${name}.jpg`);
  fs.writeFileSync(f, Buffer.from(url.split(',')[1], 'base64'));
  console.log(`${f}  ${(fs.statSync(f).size / 1024).toFixed(0)} KB`);
}

async function turntable(page) {
  const s = { view: 'asm', lights: 'day', type: 1500, cam: [-26, 26, 0.58, 0, 0, 0] };
  await setup(page, s);
  fs.mkdirSync(TMP, { recursive: true });
  const N = 72, text = 'air75 split keeps typing ';
  for (let i = 0; i < N; i++) {
    const ch = text[i % text.length], code = ch === ' ' ? 'Space' : /\d/.test(ch) ? 'Digit' + ch : 'Key' + ch.toUpperCase();
    await page.evaluate(([i, N, code]) => {
      const A = window.__air75, c = A.controls, T = A.THREE;
      const off = A.camera.position.clone().sub(c.target);
      off.applyAxisAngle(new T.Vector3(0, 0, 1), 2 * Math.PI / N);
      A.camera.position.copy(c.target).add(off); c.update(); A.press(code); A.redraw();
    }, [i, N, code]);
    await page.waitForTimeout(110);
    await page.evaluate((code) => window.__air75.release(code), code);
    await page.waitForTimeout(40);
    const url = await page.evaluate(() => window.__air75.snapshot({ shape: '16:9', size: '1920', bg: 'studio', out: [960, 540], fmt: 'image/png' }));
    fs.writeFileSync(path.join(TMP, `f${String(i).padStart(3, '0')}.png`), Buffer.from(url.split(',')[1], 'base64'));
  }
  const gif = path.join(IMG, 'turntable.gif'), pal = path.join(TMP, 'palette.png');
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-framerate', '12', '-i', path.join(TMP, 'f%03d.png'), '-vf', 'scale=640:-1:flags=lanczos,palettegen=max_colors=96:stats_mode=diff', pal]);
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-framerate', '12', '-i', path.join(TMP, 'f%03d.png'), '-i', pal, '-lavfi', 'scale=640:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle', gif]);
  console.log(`${gif}  ${(fs.statSync(gif).size / 1024).toFixed(0)} KB`);
}

(async () => {
  const want = process.argv.slice(2);
  const browser = await chromium.launch({ executablePath: fs.existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : undefined,
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 740, height: 900 } });   // narrow: the side panel doesn't push the model off centre
  page.on('pageerror', (e) => console.error('page error:', e.message));
  if (process.env.THREE_DIR) await page.route('https://cdn.jsdelivr.net/npm/three@0.128.0/**', (r) =>
    r.fulfill({ path: path.join(process.env.THREE_DIR, r.request().url().split('three@0.128.0/')[1]), contentType: 'application/javascript' }));
  await page.route('https://fonts.googleapis.com/**', (r) => r.abort());
  await page.addInitScript(() => { try { localStorage.clear(); } catch (e) {} });
  await page.goto('file://' + path.join(__dirname, 'index.html'));
  await page.waitForFunction(() => window.__air75 && window.__air75.snapshot, null, { timeout: 120000 });
  for (const [name, s] of Object.entries(SHOTS)) if (!want.length || want.includes(name)) await still(page, name, s);
  if (!want.length || want.includes('turntable')) await turntable(page);
  await browser.close();
})();
