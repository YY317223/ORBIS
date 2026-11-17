// 单场景高清截图：用于人工核对标签排布
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const PORT = 9337;
const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const SHOTS = path.join(HERE, '_shots_drill');
const PROFILE = path.join(HERE, '_edgeprofile_s');
const HTML = path.join(ROOT, 'orbis.html');
fs.mkdirSync(SHOTS, { recursive: true });

const edge = spawn(EDGE, ['--headless=new','--no-first-run','--no-default-browser-check',
  '--remote-debugging-port='+PORT,'--user-data-dir='+PROFILE,'--window-size=1600,1000',
  '--force-device-scale-factor=1','--use-angle=swiftshader','--enable-unsafe-swiftshader',
  '--ignore-gpu-blocklist','--enable-webgl','--run-all-compositor-stages-before-draw','about:blank'],{stdio:'ignore'});
const sleep = ms => new Promise(r => setTimeout(r, ms));
let wsUrl;
for (let i = 0; i < 80; i++) {
  try { const r = await fetch(`http://127.0.0.1:${PORT}/json/list`); const l = await r.json();
        const t = l.find(x => x.type === 'page'); if (t) { wsUrl = t.webSocketDebuggerUrl; break; } } catch (_) {}
  await sleep(250);
}
const ws = new WebSocket(wsUrl);
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
let seq = 0; const pending = new Map();
ws.onmessage = ev => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } };
const send = (method, params = {}) => new Promise(res => { const id = ++seq; pending.set(id, res); ws.send(JSON.stringify({ id, method, params })); });
const evalJS = async e => (await send('Runtime.evaluate', { expression: e, returnByValue: true, awaitPromise: true })).result?.result?.value;
await send('Page.enable'); await send('Runtime.enable');
await send('Emulation.setDeviceMetricsOverride', { width: 1600, height: 1000, deviceScaleFactor: 1, mobile: false });
await send('Page.navigate', { url: pathToFileURL(HTML).href });
for (let i = 0; i < 80; i++) { if (await evalJS('document.readyState') === 'complete') break; await sleep(100); }
await sleep(1400);

const jobs = process.argv.slice(2);   // 例如 EU 或 China
for (const j of jobs) {
  if (j.startsWith('C:')) {
    await evalJS(`window.__globe.country(${JSON.stringify(j.slice(2))})`);
  } else {
    await evalJS(`window.__globe.continent(${JSON.stringify(j)})`);
  }
  await sleep(1800);
  const r = await send('Page.captureScreenshot', { format: 'png', clip: { x: 0, y: 0, width: 1600, height: 1000, scale: 1.6 }, captureBeyondViewport: false });
  fs.writeFileSync(path.join(SHOTS, 'hd_' + j + '.png'), Buffer.from(r.result.data, 'base64'));
  console.log('hd', j, await evalJS('JSON.stringify(window.__globe.info())'));
  await evalJS('window.__globe.back()');
  await sleep(600);
}
ws.close(); edge.kill();
fs.rmSync(PROFILE, { recursive: true, force: true });
