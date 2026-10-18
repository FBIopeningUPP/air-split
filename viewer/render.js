// Renders the README images from the 3D viewer, each in a light and a dark version that match GitHub's page colours.
//
//   node viewer/render.js                  everything
//   node viewer/render.js hero split       only these (stills by name, or turntable / split / covers for the GIFs)
//
// Needs Playwright (npm i -g playwright) and ffmpeg. If the machine can't reach the CDN, point THREE_DIR at a local copy
// of three@0.128.0 (the folder that holds build/ and examples/).
const path = require('path'), fs = require('fs'), { execFileSync } = require('child_process');
const { chromium } = require('playwright');

const ROOT = path.join(__dirname, '..');
const IMG = path.join(ROOT, 'docs', 'images');
const TMP = path.join(ROOT, 'build', 'renders');
const THEMES = [['', '#ffffff', '#1f2328'], ['_dark', '#0d1117', '#e6edf3']];   // file suffix, GitHub page colour, text colour
const W = 1920, H = 1080, SS = 2;                                               // still size, supersampling

// cam: [azimuth deg (0 = from the front), elevation deg, share of the frame width the board fills, target shift x, y, z mm, 'cut']
const ISO = [-26, 30, 0.84, 0, 0, 0];
const SHOTS = {
  hero:     { view: 'asm', type: 1500, cam: [-26, 28, 0.82, 0, 0, 0] },
  oled:     { view: 'asm', lights: 'night', type: 3000, close: 'oled', themes: [['', '#0d1117'], ['_dark', '#0d1117']] },
  top:      { view: 'asm', cam: [0, 89.5, 0.84, 0, 0, 0] },
  slim:     { view: 'asm', cam: [-58, 5, 1.7, -95, -20, 6] },
  tented:   { view: 'asm', tent: 10, cam: [0, 14, 0.8, 0, 0, 10] },
  covers:   { view: 'covers', cover: 2400, cam: [-26, 30, 0.82, 0, 0, 0] },
  exploded: { view: 'explode', cam: [-22, 18, 0.52, 0, 0, 4], labels: true },
  inside:   { view: 'inside', cam: [-24, 40, 0.84, 0, 0, 0] },
  wiring:   { view: 'wiring', cam: [0, -62, 0.84, 0, 0, 0] },
  apart:    { view: 'apart', cam: [-18, 42, 0.84, 0, 0, 0] },
  section:  { view: 'section', cam: [70, 14, 2.4, 0, 0, 6, 'cut'] },
  sage:     { view: 'asm', colors: [2, 0], cam: ISO, size: [1280, 720] },
  slate:    { view: 'asm', colors: [3, 4], cam: ISO, size: [1280, 720] },
  chalk:    { view: 'asm', colors: [1, 1], cam: ISO, size: [1280, 720] },
};
// the exploded view's labels: [text, half, part, point inside the part's box (fractions), side of the picture]
const LABELS = [
  ['Printed keycaps', 'L', 'caps', [0.15, 0.2, 1], 'left'],
  ['KS-33 low-profile switches', 'L', 'sw', [0.12, 0.3, 0.6], 'left'],
  ['8 mm printed case', 'L', 'shell', [0.04, 0.15, 0.5], 'left'],
  ['Base, hidden magnets', 'L', 'base', [0.2, 0.15, 0.5], 'left'],
  ['0.91" OLED, tilted 10°', 'R', 'screens', [0.5, 0.9, 1], 'right'],
  ['nRF52840 + LiPo', 'R', 'elec', [0.5, 0.6, 0.5], 'right'],
  ['Handwired, 70 diodes', 'R', 'wire', [0.8, 0.3, 0.5], 'right'],
];

async function setup(page, s) {
  await page.evaluate((s) => {
    const A = window.__air75;
    A.setView(s.view); A.setLights(s.lights || 'day');
    document.querySelectorAll('#caseSw .sw')[s.colors ? s.colors[0] : 0].click();
    document.querySelectorAll('#capSw .sw')[s.colors ? s.colors[1] : 0].click();
    if (s.tent) A.setTent(s.tent);
    if (s.close) A.closeUp(s.close);
    if (s.gap) { A.ui.gap.value = s.gap; A.layout(); }
  }, s);
  if (s.type) await type(page, s.type);
  await page.waitForTimeout(1200);                  // camera flights finish
  if (s.cover !== undefined) await page.evaluate((ms) => window.__air75.coverAt(ms), s.cover);
  if (s.cam) await aim(page, s.cam);
  await page.waitForTimeout(400);
}

async function type(page, ms) {                     // type for a while so the screens have something to show
  const text = 'the quick brown fox jumps over the lazy dog ', t0 = Date.now();
  for (let i = 0; Date.now() - t0 < ms; i++) {
    const ch = text[i % text.length], code = ch === ' ' ? 'Space' : 'Key' + ch.toUpperCase();
    await page.evaluate((c) => window.__air75.press(c), code); await page.waitForTimeout(60);
    await page.evaluate((c) => window.__air75.release(c), code); await page.waitForTimeout(70);
  }
}

async function aim(page, cam) {
  await page.evaluate((cam) => {
    const A = window.__air75, T = A.THREE, c = A.controls, m = A.center();
    A.stop();
    const tgt = m.c.clone().add(new T.Vector3(cam[3], cam[4], cam[5]));
    if (cam[6] === 'cut') tgt.x = A.cutX() + cam[3];                                        // section: aim at the cut face
    const half = Math.atan(Math.tan(T.MathUtils.degToRad(A.camera.fov) / 2) * 16 / 9);      // horizontal half-angle of a 16:9 frame
    const d0 = m.size.x / (2 * cam[2] * Math.tan(half));                                    // cam[2]: share of the frame width the board fills
    const az = cam[0] * Math.PI / 180, el = cam[1] * Math.PI / 180;
    A.camera.position.set(tgt.x + d0 * Math.cos(el) * Math.sin(az), tgt.y - d0 * Math.cos(el) * Math.cos(az), tgt.z + d0 * Math.sin(el));
    c.target.copy(tgt); c.autoRotate = false; c.update(); A.redraw();
  }, cam);
}

async function shots(page, o) {
  return (await page.evaluate((o) => window.__air75.shots(o), o)).map((u) => Buffer.from(u.split(',')[1], 'base64'));
}

async function still(page, name, s) {
  await setup(page, s);
  const [w, h] = s.size || [W, H], themes = s.themes || THEMES;
  let labels;
  if (s.labels) labels = await page.evaluate((L) => L.map((l) => ({ text: l[0], pt: window.__air75.point(l[1], l[2], l[3]), side: l[4] })), LABELS);
  const bufs = await shots(page, { size: w * SS, out: [w, h], bgs: themes.map((t) => t[1]), ink: THEMES.map((t) => t[2]), labels, fmt: 'image/jpeg' });
  themes.forEach((t, i) => {
    const f = path.join(IMG, `render_${name}${t[0]}.jpg`);
    fs.writeFileSync(f, bufs[i]);
    console.log(`${path.relative(ROOT, f)}  ${(bufs[i].length / 1024).toFixed(0)} KB`);
  });
}

// GIFs: render every frame once, write one frame set per theme, then encode each with its own palette
async function animate(page, name, s, frames, step, fps, width) {
  await setup(page, s);
  const dir = path.join(TMP, name); fs.rmSync(dir, { recursive: true, force: true }); fs.mkdirSync(dir, { recursive: true });
  const out = [width, Math.round(width * 9 / 16)];
  for (let i = 0; i < frames; i++) {
    await step(i);
    await page.waitForTimeout(60);
    const bufs = await shots(page, { size: out[0] * 2, out, bgs: THEMES.map((t) => t[1]), fmt: 'image/png' });
    THEMES.forEach((t, k) => fs.writeFileSync(path.join(dir, `f${t[0] || '_light'}_${String(i).padStart(3, '0')}.png`), bufs[k]));
  }
  for (const t of THEMES) {
    const inp = path.join(dir, `f${t[0] || '_light'}_%03d.png`), pal = path.join(dir, `palette${t[0]}.png`), gif = path.join(IMG, `${name}${t[0]}.gif`);
    execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-framerate', String(fps), '-i', inp, '-vf', 'palettegen=max_colors=96:stats_mode=diff', pal]);
    execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-framerate', String(fps), '-i', inp, '-i', pal, '-lavfi', 'paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle', gif]);
    console.log(`${path.relative(ROOT, gif)}  ${(fs.statSync(gif).size / 1024).toFixed(0)} KB`);
  }
}

const ease = (k) => k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;

async function turntable(page) {
  const N = 60, text = 'air75 split keeps typing ';
  await animate(page, 'turntable', { view: 'asm', type: 1500, cam: [-26, 26, 0.58, 0, 0, 0] }, N, async (i) => {
    const ch = text[i % text.length], code = ch === ' ' ? 'Space' : 'Key' + ch.toUpperCase();
    await page.evaluate(([N, code]) => {
      const A = window.__air75, c = A.controls, T = A.THREE;
      const off = A.camera.position.clone().sub(c.target);
      off.applyAxisAngle(new T.Vector3(0, 0, 1), 2 * Math.PI / N);
      A.camera.position.copy(c.target).add(off); c.update(); A.press(code); A.redraw();
    }, [N, code]);
    await page.waitForTimeout(90);
    await page.evaluate((code) => window.__air75.release(code), code);
  }, 12, 640);
}

async function split(page) {
  // joined -> pulled apart -> tented on the 10 degree wedges -> back down -> joined
  const plan = [];
  const seg = (n, f) => { for (let i = 0; i < n; i++) plan.push(f(n > 1 ? i / (n - 1) : 1)); };
  seg(6, () => [0, 0, 0]);
  seg(12, (k) => [70 * ease(k), 0, 0]);
  seg(3, () => [70, 0, 0]);
  seg(12, (k) => [70, 10 * ease(k), 10]);
  seg(8, () => [70, 10, 10]);
  seg(12, (k) => [70, 10 * (1 - ease(k)), 10]);
  seg(12, (k) => [70 * (1 - ease(k)), 0, 0]);
  await animate(page, 'split', { view: 'asm', gap: 70, cam: [0, 20, 0.86, 0, 0, 8] }, plan.length, async (i) => {
    await page.evaluate(([gap, a, wedge]) => {
      const A = window.__air75; A.ui.gap.value = gap; A.tilt(a, a > 0 ? wedge : 0); A.redraw();
    }, plan[i]);
  }, 12, 480);
}

async function covers(page) {
  const N = 40;
  await animate(page, 'covers', { view: 'covers', cam: [-26, 30, 0.82, 0, 0, 0] }, N, async (i) => {
    await page.evaluate((ms) => window.__air75.coverAt(ms), (i / N) * 6000);              // the viewer's 6 s drop-on, rest, lift-off loop
    await page.waitForTimeout(150);
  }, 8, 480);
}

// banner for posts: title, subtitle, pills, and the two halves apart in cream with dark modifiers and orange accents
async function banner(page) {
  const BG = '#141414', ORANGE = 0xe8552d, DARK = 0x2d3035;
  await setup(page, { view: 'asm', colors: [1, 0], gap: 46, type: 2500 });
  await page.evaluate(([O, K]) => {
    const A = window.__air75;
    A.tint(['L:Tab', 'L:Caps', 'L:Shift', 'L:Ctrl', 'L:Win', 'L:Alt', 'L:Space', 'R:Space', 'R:Alt', 'R:Menu', 'R:Ctrl', 'R:Shift',
            'R:Bksp', 'R:Del', 'R:\\', 'R:PgUp', 'R:PgDn', 'R:End', 'R:Up', 'R:Down', 'R:Left', 'R:Right'], K);
    A.tint(['L:Esc', 'L:Fn', 'R:Enter'], O);
  }, [ORANGE, DARK]);
  await aim(page, [-14, 36, 0.66, 0, 16, 16]);
  await page.waitForTimeout(400);
  const W2 = 2000, H2 = 1125;
  const [img] = await page.evaluate((o) => window.__air75.shots(o), { size: W2 * 2, out: [W2, H2], bgs: [BG], fmt: 'image/png' });
  const url = await page.evaluate(async ([img, W2, H2, BG]) => {
    await document.fonts.load('600 10px Inter'); await document.fonts.load('500 10px Inter');
    const c = document.createElement('canvas'); c.width = W2; c.height = 1000; const x = c.getContext('2d');
    x.fillStyle = BG; x.fillRect(0, 0, W2, 1000);
    const g = x.createRadialGradient(W2 / 2, 520, 0, W2 / 2, 520, 1100); g.addColorStop(0, 'rgba(255,255,255,0.05)'); g.addColorStop(1, 'rgba(255,255,255,0)');
    x.fillStyle = g; x.fillRect(0, 0, W2, 1000);
    const im = new Image(); im.src = img; await im.decode();
    x.globalCompositeOperation = 'lighten'; x.drawImage(im, 0, 1000 - H2 + 40); x.globalCompositeOperation = 'source-over';
    x.textAlign = 'center'; x.textBaseline = 'alphabetic';
    x.fillStyle = '#f2efe8'; x.font = '600 150px Inter, sans-serif'; x.fillText('Snap70', W2 / 2, 175);
    x.fillStyle = '#a3a3a3'; x.font = '400 40px Inter, sans-serif';
    x.fillText('Split wireless keyboard \u00b7 8 mm thin \u00b7 snaps together on magnets', W2 / 2, 255);
    const pills = ['70 KEYS', 'ZMK', 'nRF52840', 'KS-33 LOW PROFILE', 'ANIMATED OLEDS'];
    x.font = '600 26px Inter, sans-serif'; const ph = 50, gap = 14, padx = 22;
    const ws = pills.map((p) => x.measureText(p).width + padx * 2), tot = ws.reduce((a, b) => a + b, 0) + gap * (pills.length - 1);
    let px = (W2 - tot) / 2; const py = 300;
    pills.forEach((p, i) => {
      x.beginPath(); x.roundRect(px, py, ws[i], ph, ph / 2);
      if (i === 0) { x.fillStyle = '#e8552d'; x.fill(); x.fillStyle = '#ffffff'; }
      else { x.strokeStyle = '#4a4a4a'; x.lineWidth = 2; x.stroke(); x.fillStyle = '#e6e6e6'; }
      x.textAlign = 'center'; x.fillText(p, px + ws[i] / 2, py + ph / 2 + 9); px += ws[i] + gap;
    });
    return c.toDataURL('image/jpeg', 0.93);
  }, [img, W2, H2, BG]);
  const f = path.join(IMG, 'banner.jpg');
  fs.writeFileSync(f, Buffer.from(url.split(',')[1], 'base64'));
  console.log(`${path.relative(ROOT, f)}  ${(fs.statSync(f).size / 1024).toFixed(0)} KB`);
}

(async () => {
  const want = process.argv.slice(2);
  const pick = (n) => !want.length || want.includes(n);
  const browser = await chromium.launch({ executablePath: fs.existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : undefined,
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 740, height: 900 } });   // narrow: the side panel doesn't push the model off centre
  page.on('pageerror', (e) => console.error('page error:', e.message));
  if (process.env.THREE_DIR) await page.route('https://cdn.jsdelivr.net/npm/three@0.128.0/**', (r) =>
    r.fulfill({ path: path.join(process.env.THREE_DIR, r.request().url().split('three@0.128.0/')[1]), contentType: 'application/javascript' }));
  await page.route('https://fonts.googleapis.com/**', (r) => r.abort());
  await page.addInitScript(() => { try { localStorage.clear(); } catch (e) {} });
  await page.goto('file://' + path.join(__dirname, 'index.html'));
  await page.waitForFunction(() => window.__air75 && window.__air75.shots, null, { timeout: 120000 });
  fs.mkdirSync(IMG, { recursive: true });
  for (const [name, s] of Object.entries(SHOTS)) if (pick(name)) await still(page, name, s);
  if (want.includes('banner')) await banner(page);
  if (pick('split')) await split(page);
  if (pick('covers')) await covers(page);
  if (pick('turntable')) await turntable(page);
  await browser.close();
})();
