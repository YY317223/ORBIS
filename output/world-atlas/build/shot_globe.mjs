// 地球首屏截图：核对晨昏线、大气与染色观感
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const PORT = 9351;
const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const SHOTS = path.join(HERE, '_shots_extra');
const PROFILE = path.join(HERE, '_edgeprofile_g');
const HTML = path.join(ROOT, 'orbis.html');
fs.mkdirSync(SHOTS, { recursive: true });

const W = 1600, H = 1000;
const edge = spawn(EDGE, ['--headless=new', '--no-first-run', '--no-default-browser-check',
  '--remote-debugging-port=' + PORT, '--user-data-dir=' + PROFILE, '--window-size=' + W + ',' + H,
  '--force-device-scale-factor=1', '--use-angle=swiftshader', '--enable-unsafe-swiftshader',
  '--ignore-gpu-blocklist', '--enable-webgl', '--run-all-compositor-stages-before-draw', 'about:blank'], { stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));
let wsUrl;
for (let i = 0; i < 80; i++) {
  try {
    const r = await fetch(`http://127.0.0.1:${PORT}/json/list`); const l = await r.json();
    const t = l.find(x => x.type === 'page'); if (t) { wsUrl = t.webSocketDebuggerUrl; break; }
  } catch (_) { }
  await sleep(250);
}
const ws = new WebSocket(wsUrl);
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
let seq = 0; const pending = new Map(); const errs = [];
ws.onmessage = ev => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
  if (m.method === 'Runtime.exceptionThrown') errs.push('EXC ' + (m.params.exceptionDetails?.exception?.description || ''));
};
const send = (method, params = {}) => new Promise(res => { const id = ++seq; pending.set(id, res); ws.send(JSON.stringify({ id, method, params })); });
const evalJS = async e => (await send('Runtime.evaluate', { expression: e, returnByValue: true, awaitPromise: true })).result?.result?.value;
await send('Page.enable'); await send('Runtime.enable');
await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: false });
await send('Page.navigate', { url: pathToFileURL(HTML).href });
for (let i = 0; i < 80; i++) { if (await evalJS('document.readyState') === 'complete') break; await sleep(100); }
await sleep(2600);
async function shot(n) {
  const r = await send('Page.captureScreenshot', { format: 'png', clip: { x: 0, y: 0, width: W, height: H, scale: 1 } });
  fs.writeFileSync(path.join(SHOTS, n + '.png'), Buffer.from(r.result.data, 'base64'));
  console.log('·', n);
}
await shot('g1_globe_initial');
// 转到非洲一侧，看另一段晨昏线
await evalJS("window.__globe.faceTo(-20,10,2.6)");
await sleep(1600);
await shot('g2_globe_africa');
// 选指标染色后再看一次
await evalJS("window.__globe.setInd('pc');window.__globe.setYear(2023)");
await sleep(1200);
await shot('g3_globe_tinted');
console.log('errors:', errs.length ? errs.join('\n') : '(none)');
ws.close(); edge.kill();
fs.rmSync(PROFILE, { recursive: true, force: true });
