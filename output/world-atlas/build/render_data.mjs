// 数据台回归：染色 / 时间轴 / 排行榜 / 对比
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const PORT = 9341;
const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const SHOTS = path.join(HERE, '_shots_data');
const PROFILE = path.join(HERE, '_edgeprofile_d');
const HTML = path.join(ROOT, 'orbis.html');
fs.mkdirSync(SHOTS, { recursive: true });

const W = +(process.env.W || 1600), H = +(process.env.H || 1000);
const edge = spawn(EDGE, ['--headless=new','--no-first-run','--no-default-browser-check',
  '--remote-debugging-port='+PORT,'--user-data-dir='+PROFILE,'--window-size='+W+','+H,
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
let seq = 0; const pending = new Map(); const errs = [];
ws.onmessage = ev => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
  if (m.method === 'Runtime.exceptionThrown') errs.push('EXC ' + (m.params.exceptionDetails?.exception?.description || m.params.exceptionDetails?.text));
  if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error')
    errs.push('ERR ' + m.params.args.map(a => a.value ?? a.description).join(' '));
};
const send = (method, params = {}) => new Promise(res => { const id = ++seq; pending.set(id, res); ws.send(JSON.stringify({ id, method, params })); });
const evalJS = async e => {
  const r = await send('Runtime.evaluate', { expression: e, returnByValue: true, awaitPromise: true });
  if (r.result?.exceptionDetails) errs.push('EVAL ' + r.result.exceptionDetails.text + ' ' + (r.result.exceptionDetails.exception?.description || ''));
  return r.result?.result?.value;
};
await send('Page.enable'); await send('Runtime.enable');
await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: false });
await send('Page.navigate', { url: pathToFileURL(HTML).href });
for (let i = 0; i < 80; i++) { if (await evalJS('document.readyState') === 'complete') break; await sleep(100); }
await sleep(1600);

async function shot(name, scale = 1) {
  const r = await send('Page.captureScreenshot', { format: 'png', clip: { x: 0, y: 0, width: W, height: H, scale }, captureBeyondViewport: false });
  fs.writeFileSync(path.join(SHOTS, name + '.png'), Buffer.from(r.result.data, 'base64'));
  console.log('·', name, await evalJS('JSON.stringify(window.__globe.info())'));
}

// 0 基线
await shot('01_cont');
// 1 人均 GDP 2023
await evalJS("window.__globe.setInd('pc')");
await sleep(1200); await shot('02_pc_2023');
// 2 同指标 2000
await evalJS("window.__globe.setYear(2000)");
await sleep(1200); await shot('03_pc_2000');
// 3 寿命
await evalJS("window.__globe.setYear(2023);window.__globe.setInd('le')");
await sleep(1200); await shot('04_le_2023');
// 4 GDP
await evalJS("window.__globe.setInd('gdp')");
await sleep(1200); await shot('05_gdp_2023');
// 5 最低榜
await evalJS("document.querySelector('#rank .seg button[data-d=\"bot\"]').click()");
await sleep(600); await shot('06_rank_bottom');
// 6 对比
await evalJS("window.__globe.setInd('pc');window.__globe.compare('中国');window.__globe.compare('印度');window.__globe.compare('美国')");
await sleep(1200); await shot('07_compare');
// 7 洲视图 + 染色
await evalJS("window.__globe.continent('AS')");
await sleep(1500); await shot('08_asia_choropleth');
// 7b 在洲视图里拖年份
await evalJS("window.__globe.setYear(2000)");
await sleep(1200); await shot('08b_asia_2000');
// 8 国家视图 + 加入对比
await evalJS("window.__globe.country('中国')");
await sleep(1500); await shot('09_country_cmp');
// 9 返回，确认 dock 回来
await evalJS("window.__globe.back();window.__globe.back()");
await sleep(1200); await shot('10_back');
// 10 播放推进
const y0 = await evalJS("window.__globe.year()");
await evalJS("window.__globe.play(true)");
await sleep(1500);
const y1 = await evalJS("window.__globe.year()");
await evalJS("window.__globe.play(false)");
console.log('play', y0, '->', y1, y1 !== y0 ? 'OK' : 'FAIL');

// 11 回到大洲模式，确认配色复原
await evalJS("window.__globe.cmpClear();window.__globe.setInd('cont')");
await sleep(1000); await shot('11_back_cont');

// 性能：一次整层重绘
const perf = await evalJS(`(function(){
  var t0=performance.now();
  for(var i=0;i<5;i++){ window.__globe.setYear(2000+i); }
  return +( (performance.now()-t0)/5 ).toFixed(1);
})()`);
console.log('setYear 平均耗时 ms =', perf);

console.log('--- errors ---');
console.log(errs.length ? errs.join('\n') : '(none)');
ws.close(); edge.kill();
fs.rmSync(PROFILE, { recursive: true, force: true });
