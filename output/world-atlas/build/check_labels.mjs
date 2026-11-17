// 复核：洲视图里每个国名标签是否落在该国质心附近（偏差 > 40px 视为异常）
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const PORT = 9338;
const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const PROFILE = path.join(HERE, '_edgeprofile_v');
const HTML = path.join(ROOT, 'orbis.html');

const edge = spawn(EDGE, ['--headless=new','--no-first-run','--no-default-browser-check',
  '--remote-debugging-port='+PORT,'--user-data-dir='+PROFILE,'--window-size=1440,900',
  '--force-device-scale-factor=1','--use-angle=swiftshader','--enable-unsafe-swiftshader',
  '--ignore-gpu-blocklist','--enable-webgl','about:blank'],{stdio:'ignore'});
const sleep = ms => new Promise(r => setTimeout(r, ms));
let wsUrl;
for (let i = 0; i < 80; i++) {
  try { const r = await fetch(`http://127.0.0.1:${PORT}/json/list`); const l = await r.json();
        const t = l.find(x => x.type === 'page'); if (t) { wsUrl = t.webSocketDebuggerUrl; break; } } catch (_) {}
  await sleep(250);
}
const ws = new WebSocket(wsUrl);
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
let seq = 0; const pending = new Map(); const errors = [];
ws.onmessage = ev => { const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); return; }
  if (m.method === 'Runtime.exceptionThrown') errors.push(m.params.exceptionDetails.text);
};
const send = (method, params = {}) => new Promise(res => { const id = ++seq; pending.set(id, res); ws.send(JSON.stringify({ id, method, params })); });
const evalJS = async e => { const r = await send('Runtime.evaluate', { expression: e, returnByValue: true, awaitPromise: true });
  if (r.result?.exceptionDetails) throw new Error(r.result.exceptionDetails.text); return r.result?.result?.value; };
await send('Page.enable'); await send('Runtime.enable');
await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
await send('Page.navigate', { url: pathToFileURL(HTML).href });
for (let i = 0; i < 80; i++) { if (await evalJS('document.readyState') === 'complete') break; await sleep(100); }
await sleep(1200);

for (const k of ['AS','EU','AF','NA','SA','OC']) {
  await evalJS(`window.__globe.continent('${k}')`);
  await sleep(1300);
  const rows = await evalJS(`(function(){
    var out=[], D=window.ATLAS_DATA, byName={};
    D.countries.forEach(function(c){ byName[c.n]=c; });
    window.__globe.labels().forEach(function(l){
      var c=byName[l.n]; if(!c) { out.push([l.n,'??',0,0]); return; }
      var p=window.__globe.viewScreen(c.clat,c.clon);
      out.push([l.n, Math.round(l.x-p[0]), Math.round(l.y-p[1])]);
    });
    return out;
  })()`);
  const bad = rows.filter(r => Math.abs(r[1]) > 45 || Math.abs(r[2]) > 30);
  console.log(k, 'labels=' + rows.length, 'offcenter=' + bad.length, JSON.stringify(bad.slice(0, 8)));
  await evalJS('window.__globe.back()'); await sleep(500);
}
if (errors.length) console.log('ERRORS', errors);
ws.close(); edge.kill();
fs.rmSync(PROFILE, { recursive: true, force: true });
