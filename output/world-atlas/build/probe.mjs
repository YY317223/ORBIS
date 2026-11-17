// 临时探针：跑一段表达式并截图，用于开发期快速验证
// 用法: node probe.mjs "expr1" "expr2" ...
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const PORT = 9361;
const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const SHOTS = path.join(HERE, '_shots_probe');
const PROFILE = path.join(HERE, '_edgeprofile_p');
const HTML = path.join(ROOT, 'orbis.html');
fs.mkdirSync(SHOTS, { recursive: true });

const W = +(process.env.W || 1600), H = +(process.env.H || 1000);
const GL = process.env.GPU === '1'
  ? ['--use-angle=d3d11', '--ignore-gpu-blocklist', '--enable-webgl']
  : ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--enable-webgl'];
const edge = spawn(EDGE, ['--headless=new', '--no-first-run', '--no-default-browser-check',
  '--remote-debugging-port=' + PORT, '--user-data-dir=' + PROFILE, '--window-size=' + W + ',' + H,
  '--force-device-scale-factor=1', ...GL, '--run-all-compositor-stages-before-draw', 'about:blank'], { stdio: 'ignore' });
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
  if (m.method === 'Runtime.exceptionThrown') errs.push('EXC ' + (m.params.exceptionDetails?.exception?.description || m.params.exceptionDetails?.text));
  if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') errs.push('ERR ' + m.params.args.map(a => a.value ?? a.description).join(' '));
};
const send = (method, params = {}) => new Promise(res => { const id = ++seq; pending.set(id, res); ws.send(JSON.stringify({ id, method, params })); });
const evalJS = async e => {
  const r = await send('Runtime.evaluate', { expression: e, returnByValue: true, awaitPromise: true });
  if (r.result?.exceptionDetails) errs.push('EVAL ' + r.result.exceptionDetails.text + ' ' + (r.result.exceptionDetails.exception?.description || ''));
  return r.result?.result?.value;
};
await send('Page.enable'); await send('Runtime.enable');
await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: false });
const url = process.env.URL ? (process.env.URL + (process.env.HASH || ''))
  : (pathToFileURL(HTML).href + (process.env.HASH || ''));
await send('Page.navigate', { url });
for (let i = 0; i < 80; i++) { if (await evalJS('document.readyState') === 'complete') break; await sleep(100); }
await sleep(+(process.env.WAIT || 2400));

let n = 0;
for (const e of process.argv.slice(2)) {
  if (e.startsWith('dataurl:')) {
    const [expr, name] = e.slice(8).split('|');
    const v = await evalJS(expr);
    if (typeof v === 'string' && v.startsWith('data:image')) {
      fs.writeFileSync(path.join(SHOTS, name + '.png'), Buffer.from(v.split(',')[1], 'base64'));
      console.log('dataurl ->', name, Math.round(v.length / 1024) + 'KB');
    } else console.log('dataurl FAILED', String(v).slice(0, 80));
    continue;
  }
  if (e.startsWith('shot:')) {
    n++;
    const r = await send('Page.captureScreenshot', { format: 'png', clip: { x: 0, y: 0, width: W, height: H, scale: 1 } });
    const nm = e.slice(5) || ('p' + n);
    fs.writeFileSync(path.join(SHOTS, nm + '.png'), Buffer.from(r.result.data, 'base64'));
    console.log('shot', nm);
    continue;
  }
  const t0 = Date.now();
  let v;
  try { v = await evalJS(e); } catch (err) { v = 'THROW ' + err.message; }
  console.log('>', e.slice(0, 70), '=>', typeof v === 'object' ? JSON.stringify(v) : v, '(' + (Date.now() - t0) + 'ms)');
  await sleep(+(process.env.GAP || 500));
}
console.log('--- errors ---');
console.log(errs.length ? errs.join('\n') : '(none)');
ws.close(); edge.kill();
fs.rmSync(PROFILE, { recursive: true, force: true });
