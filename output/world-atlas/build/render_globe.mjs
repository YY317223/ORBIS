// 用 Edge CDP 真实渲染 3D 地球，校验 WebGL、拾取对齐与交互状态。
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const PORT = 9334;
const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const SHOTS = path.join(HERE, '_shots_globe');
const PROFILE = path.join(HERE, '_edgeprofile_g');
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
  if (r.result?.exceptionDetails) throw new Error(r.result.exceptionDetails.text);
  return r.result?.result?.value;
}
async function shot(name) {
  const r = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
  const p = path.join(SHOTS, name + '.png');
  fs.writeFileSync(p, Buffer.from(r.result.data, 'base64'));
  console.log('  shot', name, fs.statSync(p).size + 'B');
}
await send('Page.enable'); await send('Runtime.enable');
await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
const url = pathToFileURL(HTML).href;

const dragJS = (x1,y1,x2,y2) => `(()=>{const c=document.querySelector('#globe');const o=(x,y)=>({clientX:x,clientY:y,button:0,pointerId:1,pointerType:'mouse',bubbles:true});c.dispatchEvent(new PointerEvent('pointerdown',o(${x1},${y1})));for(let i=1;i<=10;i++){const x=${x1}+(${x2}-${x1})*i/10,y=${y1}+(${y2}-${y1})*i/10;c.dispatchEvent(new PointerEvent('pointermove',o(x,y)));}c.dispatchEvent(new PointerEvent('pointerup',o(${x2},${y2})));})()`;
const wheelJS = n => `(()=>{const c=document.querySelector('#globe');for(let i=0;i<${n};i++)c.dispatchEvent(new WheelEvent('wheel',{deltaY:-360,clientX:720,clientY:450,bubbles:true,cancelable:true}));})()`;

const scenarios = [
  { name: '01_initial', steps: [[null, 2800]] },
  { name: '02_china', steps: [["window.__globe.select('中国',720,450)", 2000]], probeCenter: true },
  { name: '03_china_zoom', steps: [["window.__globe.select('中国',720,450)", 1700], ["window.__globe.zoomBy(2.6)", 700]] },
  { name: '04_china_pan', steps: [["window.__globe.select('中国',720,450)", 1700], ["window.__globe.panBy(-330,-160)", 700]] },
  { name: '05_switch_japan', steps: [["window.__globe.select('中国')", 1600], ["window.__globe.open('日本')", 1000]] },
  { name: '06_singapore', steps: [["window.__globe.select('新加坡')", 1700]] },
  { name: '07_russia', steps: [["window.__globe.select('俄罗斯')", 1700]] },
  { name: '08_back_to_globe', steps: [["window.__globe.select('法国')", 1700], ["window.__globe.close()", 1000]] },
  { name: '09_rotate', steps: [[dragJS(720,450,1010,540), 900]] },
  { name: '10_globe_zoom', steps: [[wheelJS(6), 900]] },
  { name: '12_city_click', steps: [["window.__globe.select('中国',720,450)", 1800], ["(document.querySelector('#ccities button:nth-of-type(3)')||document.querySelector('#ccities button')).click()", 900]] },
  { name: '13_country_after_city', steps: [["window.__globe.select('日本',720,450)", 1800]] },
  { name: '12_city_click', steps: [["window.__globe.select('中国',720,450)", 1800], ["(document.querySelector('#ccities button:nth-of-type(3)')||document.querySelector('#ccities button')).click()", 900]] },
  { name: '13_country_after_city', steps: [["window.__globe.select('日本',720,450)", 1800]] },
  { name: '11_satellite', steps: [["document.querySelector('#pol').click()", 900]] },
];

for (const s of scenarios) {
  errors.length = 0;
  await send('Page.navigate', { url });
  for (let i = 0; i < 60; i++) { if (await evalJS('document.readyState') === 'complete') break; await sleep(100); }
  await sleep(700);
  for (const [expr, wait] of s.steps) { if (expr) await evalJS(expr); await sleep(wait); }
  await shot(s.name);
  const info = await evalJS(`window.__globe? window.__globe.info() : null`);
  let center = null;
  if (s.probeCenter) center = await evalJS(`window.__globe.pick(window.innerWidth/2, window.innerHeight/2)`);
  console.log('  info', s.name, JSON.stringify(info), s.probeCenter ? ' centerPick=' + JSON.stringify(center) : '');
  if (errors.length) console.log('  ERRORS', errors.slice(0, 6));
}
ws.close(); edge.kill();
fs.rmSync(PROFILE, { recursive: true, force: true });
console.log('done');
