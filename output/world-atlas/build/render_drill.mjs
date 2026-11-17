// 三级下钻（大洲 → 国家 → 城市）真实渲染回归：Edge headless CDP + SwiftShader
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const PORT = 9336;
const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const SHOTS = path.join(HERE, '_shots_drill');
const PROFILE = path.join(HERE, '_edgeprofile_d');
const HTML = path.join(ROOT, 'orbis.html');
fs.mkdirSync(SHOTS, { recursive: true });

const edge = spawn(EDGE, [
  '--headless=new', '--no-first-run', '--no-default-browser-check',
  '--remote-debugging-port=' + PORT, '--user-data-dir=' + PROFILE,
  '--window-size=1440,900', '--force-device-scale-factor=1',
  '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist',
  '--enable-webgl', '--run-all-compositor-stages-before-draw', 'about:blank'
], { stdio: 'ignore' });

const sleep = ms => new Promise(r => setTimeout(r, ms));
async function waitTarget() {
  for (let i = 0; i < 80; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${PORT}/json/list`);
      const list = await r.json();
      const t = list.find(x => x.type === 'page');
      if (t) return t.webSocketDebuggerUrl;
    } catch (_) {}
    await sleep(250);
  }
  throw new Error('Edge CDP 未就绪');
}
const wsUrl = await waitTarget();
const ws = new WebSocket(wsUrl);
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
let seq = 0; const pending = new Map(); const errors = [];
ws.onmessage = ev => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); return; }
  if (m.method === 'Runtime.exceptionThrown') errors.push(m.params.exceptionDetails.text + ' ' + (m.params.exceptionDetails.exception?.description || ''));
  if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') errors.push('console: ' + m.params.args.map(a => a.value || a.description).join(' '));
};
function send(method, params = {}) {
  return new Promise((res, rej) => {
    const id = ++seq; pending.set(id, res);
    ws.send(JSON.stringify({ id, method, params }));
    setTimeout(() => { if (pending.has(id)) { pending.delete(id); rej(new Error('timeout ' + method)); } }, 30000);
  });
}
async function evalJS(expr) {
  const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.result?.exceptionDetails) throw new Error(r.result.exceptionDetails.text + ' ' + (r.result.exceptionDetails.exception?.description || ''));
  return r.result?.result?.value;
}
async function shot(name) {
  const r = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
  const p = path.join(SHOTS, name + '.png');
  fs.writeFileSync(p, Buffer.from(r.result.data, 'base64'));
  console.log('  shot', name);
}
await send('Page.enable'); await send('Runtime.enable');
await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
const url = pathToFileURL(HTML).href;

const tapGlobe = (x, y) => `(()=>{const c=document.querySelector('#globe');const o=(t,xx,yy)=>({clientX:xx,clientY:yy,button:0,pointerId:1,pointerType:'mouse',bubbles:true});c.dispatchEvent(new PointerEvent('pointerdown',o('d',${x},${y})));c.dispatchEvent(new PointerEvent('pointerup',o('u',${x},${y})));})()`;
const tapMap = (x, y) => `(()=>{const c=document.querySelector('#cmap');const o=(xx,yy)=>({clientX:xx,clientY:yy,button:0,pointerId:2,pointerType:'mouse',bubbles:true});c.dispatchEvent(new PointerEvent('pointerdown',o(${x},${y})));c.dispatchEvent(new PointerEvent('pointerup',o(${x},${y})));})()`;

// 把某地转到正面，再点它的屏幕坐标 —— 端到端验证「真点击」
const clickAt = (lat, lon, wait = 700) => [
  [`window.__globe.faceTo(${lon},${lat},2.4)`, wait],
  [`(function(){var p=window.__globe.screenOf(${lat},${lon});var c=document.querySelector('#globe');var o={clientX:p[0],clientY:p[1],button:0,pointerId:1,pointerType:'mouse',bubbles:true};c.dispatchEvent(new PointerEvent('pointerdown',o));c.dispatchEvent(new PointerEvent('pointerup',o));})()`, 1500]
];

const scenarios = [
  { name: '01_globe_continents', steps: [[null, 3000]] },
  { name: '02_click_asia', steps: [...clickAt(34, 100, 900), [null, 400]] },
  { name: '03_asia_view', steps: [["window.__globe.continent('AS')", 1500]] },
  { name: '04_asia_click_china', steps: [["window.__globe.continent('AS')", 1600], ["(function(){var p=window.__globe.viewScreen(35,103);document.querySelector('#cmap').dispatchEvent(new PointerEvent('pointerdown',{clientX:p[0],clientY:p[1],button:0,pointerId:3,pointerType:'mouse',bubbles:true}));document.querySelector('#cmap').dispatchEvent(new PointerEvent('pointerup',{clientX:p[0],clientY:p[1],button:0,pointerId:3,pointerType:'mouse',bubbles:true}));})()", 1600]] },
  { name: '05_china_cities', steps: [["window.__globe.country('中国')", 1700]] },
  { name: '06_back_to_asia', steps: [["window.__globe.continent('AS')", 1500], ["window.__globe.country('日本')", 1400], ["window.__globe.back()", 1200]] },
  { name: '07_back_to_globe', steps: [["window.__globe.continent('AS')", 1500], ["window.__globe.back()", 1200]] },
  { name: '08_europe', steps: [["window.__globe.continent('EU')", 1600]] },
  { name: '09_africa', steps: [["window.__globe.continent('AF')", 1600]] },
  { name: '10_north_america', steps: [["window.__globe.continent('NA')", 1600]] },
  { name: '11_south_america', steps: [["window.__globe.continent('SA')", 1600]] },
  { name: '12_oceania', steps: [["window.__globe.continent('OC')", 1600]] },
  { name: '13_asia_zoom', steps: [["window.__globe.continent('EU')", 1500], ["window.__globe.zoomBy(2.4)", 700]] },
  { name: '14_satellite', steps: [["document.querySelector('#pol').click()", 900]] },
  { name: '15_search', steps: [["(function(){var q=document.querySelector('#q');q.value='巴西';q.dispatchEvent(new Event('input'));document.querySelector('#sugg .sg').click();})()", 1800]] },
  { name: '16_small_viewport', steps: [["window.__globe.continent('AS')", 1500]], w: 900, h: 640 },
];

for (const s of scenarios) {
  errors.length = 0;
  await send('Emulation.setDeviceMetricsOverride', { width: s.w || 1440, height: s.h || 900, deviceScaleFactor: 1, mobile: false });
  await send('Page.navigate', { url });
  for (let i = 0; i < 80; i++) { if (await evalJS('document.readyState') === 'complete') break; await sleep(100); }
  await sleep(900);
  for (const [expr, wait] of s.steps) { if (expr) await evalJS(expr); await sleep(wait); }
  await shot(s.name);
  const info = await evalJS(`window.__globe? window.__globe.info() : null`);
  console.log('  info', JSON.stringify(info));
  if (errors.length) console.log('  ERRORS', errors.slice(0, 6));
}
ws.close(); edge.kill();
fs.rmSync(PROFILE, { recursive: true, force: true });
console.log('done');
