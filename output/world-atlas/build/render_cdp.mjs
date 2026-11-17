// 用 Edge DevTools Protocol 按真实时间渲染各交互状态，并捕获页面异常。
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const PORT = 9333;
const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const SHOTS = path.join(HERE, '_shots');
const PROFILE = path.join(HERE, '_edgeprofile');
const HTML = path.join(ROOT, '世界即卡片.html');
fs.mkdirSync(SHOTS, { recursive: true });

const edge = spawn(EDGE, [
  '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
  '--remote-debugging-port=' + PORT, '--user-data-dir=' + PROFILE,
  '--window-size=1440,900', '--force-device-scale-factor=1', 'about:blank'
], { stdio: 'ignore' });

const sleep = ms => new Promise(r => setTimeout(r, ms));
async function waitTarget() {
  for (let i = 0; i < 60; i++) {
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
    setTimeout(() => { if (pending.has(id)) { pending.delete(id); rej(new Error('timeout ' + method)); } }, 20000);
  });
}
async function evalJS(expr) {
  const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.result?.exceptionDetails) throw new Error(r.result.exceptionDetails.text);
  return r.result?.result?.value;
}
async function shot(name, clipRect) {
  const params = { format: 'png', captureBeyondViewport: false };
  if (clipRect) params.clip = { ...clipRect, scale: 2 };
  const r = await send('Page.captureScreenshot', params);
  const p = path.join(SHOTS, name + '.png');
  fs.writeFileSync(p, Buffer.from(r.result.data, 'base64'));
  console.log('  shot', name, fs.statSync(p).size + 'B');
}
async function cardRect() {
  return await evalJS(`(()=>{const b=document.querySelector('#card').getBoundingClientRect();return {x:b.x,y:b.y,width:b.width,height:b.height}})()`);
}
const wheelJS = n => `(()=>{const m=document.querySelector('#map');for(let i=0;i<${n};i++)m.dispatchEvent(new WheelEvent('wheel',{deltaY:-140,clientX:720,clientY:450,bubbles:true,cancelable:true}));})()`;
const dragJS = (x1,y1,x2,y2) => `(()=>{const m=document.querySelector('#map');const o=(x,y)=>({clientX:x,clientY:y,button:0,pointerId:1,pointerType:'mouse',bubbles:true});m.dispatchEvent(new PointerEvent('pointerdown',o(${x1},${y1})));for(let i=1;i<=8;i++){const x=${x1}+(${x2}-${x1})*i/8,y=${y1}+(${y2}-${y1})*i/8;m.dispatchEvent(new PointerEvent('pointermove',o(x,y)));}m.dispatchEvent(new PointerEvent('pointerup',o(${x2},${y2})));})()`;
await send('Page.enable'); await send('Runtime.enable');
await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
const url = pathToFileURL(HTML).href;

const click = n => `(()=>{const i=ATLAS_DATA.countries.findIndex(c=>c.n===${JSON.stringify(n)});document.querySelector('[data-i="'+i+'"]').dispatchEvent(new MouseEvent('click',{bubbles:true}))})()`;
const scenarios = [
  { name: '01_initial', steps: [] },
  { name: '02_china', steps: [[click('中国'), 1500]] },
  { name: '03_charts', detail: true, steps: [[click('中国'), 1400], ["document.querySelector('#card-scroll').scrollTop=640", 500]] },
  { name: '04_deep', detail: true, steps: [[click('中国'), 1400], ["document.querySelector('#more').click();document.querySelector('#card-scroll').scrollTop=1200", 600]] },
  { name: '05_usa_pc_2010', steps: [[click('美国'), 1400], ["document.querySelector('[data-k=\"pc\"]').click();const r=document.querySelector('#year-range');r.value=2010;r.dispatchEvent(new Event('input',{bubbles:true}))", 700]] },
  { name: '06_closed', steps: [[click('日本'), 1400], ["document.querySelector('#ocean').dispatchEvent(new MouseEvent('click',{bubbles:true}))", 900]] },
  { name: '07_search', steps: [["(()=>{const q=document.querySelector('#q');q.value='德国';q.dispatchEvent(new Event('input',{bubbles:true}))})()", 350], ["document.querySelector('.sug.act').click()", 1800]] },
  { name: '08_switch', steps: [[click('中国'), 1000], [click('巴西'), 1000]] },
  { name: '09_info', steps: [["document.querySelector('#info-btn').click()", 450]] },
  { name: '10_nodata', detail: true, steps: [[click('朝鲜'), 1000]] },
  { name: '11_esc', steps: [[click('中国'), 1000], ["document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))", 600]] },
  { name: '12_zoom', steps: [[wheelJS(14), 800]], zoom: true },
  { name: '13_drag', steps: [[click('中国'), 1200], [dragJS(720,450,1080,520), 700]] },
];

for (const s of scenarios) {
  errors.length = 0;
  await send('Page.navigate', { url });
  for (let i = 0; i < 40; i++) { if (await evalJS('document.readyState') === 'complete') break; await sleep(100); }
  await sleep(500);
  for (const [expr, wait] of s.steps) { await evalJS(expr); await sleep(wait); }
  await shot(s.name);
  if (s.detail) { const cr = await cardRect(); if (cr && cr.width > 0) await shot(s.name + '_detail', cr); }
  if (s.zoom) await shot(s.name + '_full');
  const probe = await evalJS(`(()=>{const v=document.querySelector('#map').getAttribute('viewBox').split(' ').map(Number);const k=1000/v[2];const L=document.querySelector('#leader');return {card:!!document.querySelector('#card.on'),name:(document.querySelector('.card-head .nm')||{}).textContent||'',year:document.querySelector('#tl-year').textContent,metric:document.querySelector('#legend-name').textContent,scroll:(document.querySelector('#card-scroll')||{}).scrollTop,deep:!!document.querySelector('#deep.on'),vb:document.querySelector('#map').getAttribute('viewBox'),leader:document.querySelector('#leader').classList.contains('on'),leaderKids:L.children.length,leaderOp:getComputedStyle(L).opacity,k:+k.toFixed(2),labels:[...document.querySelectorAll('#labels .lbl')].filter(e=>e.style.display!=='none').length}})()`);
  console.log('  state', s.name, JSON.stringify(probe));
  if (errors.length) console.log('  ERRORS', errors.slice(0, 5));
}
ws.close(); edge.kill();
fs.rmSync(PROFILE, { recursive: true, force: true });
console.log('done');
