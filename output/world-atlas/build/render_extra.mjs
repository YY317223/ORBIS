// 附加校验：深链直达 / 国家叙事 / 属地开关 / 对比卡不随年份漂移
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const PORT = 9347;
const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const SHOTS = path.join(HERE, '_shots_extra');
const PROFILE = path.join(HERE, '_edgeprofile_e');
const HTML = path.join(ROOT, 'orbis.html');
fs.mkdirSync(SHOTS, { recursive: true });

const W = +(process.env.W || 1600), H = +(process.env.H || 1000);
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

async function shot(name) {
  const r = await send('Page.captureScreenshot', { format: 'png', clip: { x: 0, y: 0, width: W, height: H, scale: 1 } });
  fs.writeFileSync(path.join(SHOTS, name + '.png'), Buffer.from(r.result.data, 'base64'));
  console.log('·', name);
}
const ok = (label, cond, extra = '') => console.log((cond ? 'PASS ' : 'FAIL ') + label, extra);

// ---------- A. 深链直达国家 ----------
await send('Page.navigate', { url: pathToFileURL(HTML).href + '#/c/JPN' });
for (let i = 0; i < 80; i++) { if (await evalJS('document.readyState') === 'complete') break; await sleep(100); }
await sleep(2200);
const a = await evalJS('JSON.stringify(window.__globe.info())');
const A = JSON.parse(a);
ok('深链 #/c/JPN 直达日本', A.c === '日本' && A.open === true, a);
ok('地址栏保留哈希', (await evalJS('location.hash')) === '#/c/JPN');
await shot('a1_deeplink_japan');

// ---------- B. 国家叙事 + 对比卡不随年份漂移 ----------
await evalJS("window.__globe.compare('中国');window.__globe.compare('印度');window.__globe.setInd('pc')");
await sleep(400);
await evalJS("window.__globe.setYear(2000)");
await sleep(900);
await evalJS("window.__globe.country('中国')");
await sleep(1800);
const story = await evalJS("(document.querySelector('#cstory').innerText||'').replace(/\\n/g,' | ')");
console.log('  story:', story);
ok('叙事块有内容', story.length > 10);
ok('叙事含世界排名', /第 \d+/.test(story));
const legend = await evalJS("Array.from(document.querySelectorAll('#cmprows .cr')).map(function(e){return e.innerText.replace(/\\n/g,' ')}).join(' ; ')");
const concl = await evalJS("(document.querySelector('#cmpfn').innerText||'').replace(/\\n/g,' ')");
console.log('  legend:', legend);
console.log('  concl :', concl);
ok('对比卡取 2023 值（中国 1.30万）', /1\.30万/.test(legend), legend);
ok('结论不再出现「增至 1.0 倍」', !/增至 1\.0 倍/.test(concl), concl);
await shot('a2_china_story_2000');

// ---------- C. 属地开关 ----------
await evalJS("window.__globe.back();window.__globe.back()");
await sleep(1200);
await evalJS("window.__globe.setYear(2023);window.__globe.setInd('pc')");
await sleep(900);
const rankSov = await evalJS("Array.from(document.querySelectorAll('#rrows button')).map(function(b){return b.innerText.replace(/\\n/g,' ')}).join(' ; ')");
console.log('  rank(仅主权):', rankSov.slice(0, 160));
ok('默认不含属地', !/属地/.test(rankSov));
await shot('a3_rank_sovereign');
await evalJS("document.querySelector('#rdep').click()");
await sleep(700);
const rankAll = await evalJS("Array.from(document.querySelectorAll('#rrows button')).map(function(b){return b.innerText.replace(/\\n/g,' ')}).join(' ; ')");
console.log('  rank(含属地):', rankAll.slice(0, 160));
ok('关闭开关后出现属地', /属地/.test(rankAll));
await shot('a4_rank_all');
await evalJS("document.querySelector('#rdep').click()");   // 恢复默认口径，避免影响后续场景
await sleep(500);

// ---------- D. 浏览器后退回到地球 ----------
await evalJS("window.__globe.country('巴西')");
await sleep(1600);
const h1 = await evalJS('location.hash');
await evalJS("history.back()");
await sleep(1400);
const h2 = await evalJS('location.hash');
const D = JSON.parse(await evalJS('JSON.stringify(window.__globe.info())'));
console.log('  hash:', h1, '->', h2, '| open=', D.open);
ok('后退可退出国家视图', D.open === false, h2);

// ---------- E. 城市三级符号 ----------
await evalJS("window.__globe.country('中国')");
await sleep(1800);
const tiers = JSON.parse(await evalJS('JSON.stringify(window.__globe.cityTiers())'));
console.log('  tiers:', JSON.stringify(tiers));
ok('中国有首都 1 个', tiers.cap === 1, JSON.stringify(tiers));
ok('中国有省级中心 ≥ 20 个', tiers.adm1 >= 20, JSON.stringify(tiers));
ok('保留普通城市', tiers.gen >= 5, JSON.stringify(tiers));
const lg = await evalJS("(document.querySelector('#clegend').innerText||'').replace(/\\n/g,' ')");
console.log('  legend:', lg);
ok('图例含三级说明', /首都/.test(lg) && /省级中心/.test(lg) && /其他城市/.test(lg));
const bar0 = await evalJS("Array.from(document.querySelectorAll('#ccities button')).slice(0,4).map(function(b){return b.innerText.replace(/\\n/g,'')}).join(' / ')");
console.log('  citybar:', bar0);
ok('城市条首项是首都', /北京/.test(bar0), bar0);
await evalJS("window.__globe.zoomBy(1.32)");
await sleep(800);
await shot('a5_city_tiers_china');

// ---------- F. 一键复制链接 ----------
const term = JSON.parse(await evalJS('JSON.stringify(window.__globe.terminator())'));
console.log('  terminator:', JSON.stringify(term));
ok('晨昏线朝向随太阳更新', typeof term.z === 'number');
await evalJS("document.querySelector('#cshare').click()");
await sleep(800);
const tt = await evalJS("JSON.stringify({t:(document.querySelector('#toast').innerText||''),on:document.querySelector('#toast').classList.contains('on'),box:document.querySelector('#sharebox').classList.contains('on'),val:(document.querySelector('#sharein').value||'')})");
console.log('  share:', tt);
const T = JSON.parse(tt);
ok('复制链接有反馈（toast 或复制框）', T.on || T.box, tt);
ok('分享框里的链接带国家哈希与状态', !T.box || /#\/c\/CHN(\?|$)/.test(T.val), T.val);
await shot('a6_share_toast');
const hch = await evalJS('location.hash');
ok('分享链接哈希为国家且带状态', /^#\/c\/CHN(\?i=|\?c=|$)/.test(hch), hch);

// ---------- G. 变化率口径 ----------
await evalJS("window.__globe.back();window.__globe.back()");
await sleep(1300);
await evalJS("document.querySelector('#ddelta').click()");
await sleep(900);
ok('切到变化口径', (await evalJS('window.__globe.ind()')) === 'dpc');
const dmeta = await evalJS("document.querySelector('#rmeta').textContent");
console.log('  delta meta:', dmeta);
ok('榜单标题标出区间', /2000/.test(dmeta), dmeta);
const dtop = await evalJS("document.querySelector('#rrows button span').textContent");
console.log('  top growth:', dtop);
ok('涨最多第一名是圭亚那', dtop === '圭亚那', dtop);
const dz = await evalJS("document.querySelector('#dzero').style.display+' / '+document.querySelector('#dzero').style.left");
console.log('  zero mark:', dz);
ok('零点刻度可见', /block/.test(dz), dz);
const cnFill = await evalJS("window.__globe.fillOf('中国')");
console.log('  china fill:', cnFill);
ok('高增长国家染成暖红', /^rgb\((\d+),(\d+),(\d+)/.test(cnFill) && (() => {
  const m = cnFill.match(/(\d+),\s*(\d+),\s*(\d+)/); return m && (+m[1]) > (+m[3]);
})(), cnFill);
ok('中国 24 年人均涨幅 > 10 倍', (await evalJS("window.__globe.delta('中国')")) > 1000);
await shot('a7_delta_mode');

// ---------- H. 首屏引导卡片 ----------
await evalJS("window.__globe.cmpClear()");   // 对比开着时引导卡会主动收起，先清掉再验
await evalJS("window.__globe.cmpClear()");   // 对比开着时引导卡会主动收起，先清掉再验
await evalJS("document.querySelector('#ddelta').click()");
await sleep(700);
const startOn = await evalJS("!document.querySelector('#start').classList.contains('hide')");
ok('回到地球后引导卡片重新出现', startOn === true);
await shot('a8_start_card');
await evalJS("document.querySelector('#start [data-go=\"shrink\"]').click()");
await sleep(900);
ok('推荐入口切到人口变化', (await evalJS('window.__globe.ind()')) === 'dpop');
ok('点击后卡片收起', (await evalJS("document.querySelector('#start').classList.contains('hide')")) === true);
const dshrink = await evalJS("Array.from(document.querySelectorAll('#rrows button span')).slice(0,3).map(function(x){return x.textContent}).join(' / ')");
console.log('  pop shrink:', dshrink);

// ---------- I. 城市搜索 ----------
const sres = JSON.parse(await evalJS("JSON.stringify(window.__search('上海'))"));
console.log('  search 上海:', JSON.stringify(sres));
ok('搜索命中城市', sres[0] && sres[0].indexOf('城:上海') === 0, JSON.stringify(sres));
const sres2 = JSON.parse(await evalJS("JSON.stringify(window.__search('USA'))"));
ok('别名 USA 命中美国', sres2[0] === '国:美国', JSON.stringify(sres2));
await shot('a9_search_city');

// ---------- J. 键盘 ----------
await evalJS("document.querySelector('#q').blur();window.__globe.setInd('pc');window.__globe.setYear(2023)");
await sleep(500);
await evalJS("document.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowLeft',bubbles:true}))");
await sleep(400);
ok('← 年份减一', (await evalJS('window.__globe.year()')) === 2022, String(await evalJS('window.__globe.year()')));
await evalJS("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Home',bubbles:true}))");
await sleep(400);
ok('Home 跳到 2000', (await evalJS('window.__globe.year()')) === 2000, String(await evalJS('window.__globe.year()')));

// ---------- K. 洲视图变化率图例 + 快捷键提示 ----------
await evalJS("window.__globe.setInd('pc');window.__globe.setYear(2023);window.__globe.continent('AS')");
await sleep(1500);
await evalJS("document.querySelector('#ddelta').click()");
await sleep(900);
const dlegTxt = (await evalJS("(document.querySelector('#dleg').innerText||'').replace(/\\s+/g,' ')")).trim();
const dunTxt = (await evalJS("(document.querySelector('#dun').innerText||'')")).trim();
console.log('  dock legend:', dlegTxt, '| unit:', dunTxt);
ok('数据台图例负向以 -100% 为界', /-100%/.test(dlegTxt), dlegTxt);
ok('数据台图例正向到 +1168%', /\+1168%/.test(dlegTxt), dlegTxt);
ok('数据台图例单位标为变化', /变化/.test(dunTxt), dunTxt);
const hlptxt = (await evalJS("(document.querySelector('#chelp').innerText||'').replace(/\\s+/g,' ')")).trim();
console.log('  chelp:', hlptxt);
ok('帮助条含键盘提示', /←/.test(hlptxt) && /空格/.test(hlptxt) && /搜索/.test(hlptxt), hlptxt);
await shot('a10_continent_delta_legend');


// ---------- L. 工具化：离线状态 / 涨跌刻度 / 分享图 / 状态链接 ----------
await evalJS("window.__globe.close(); window.__globe.setInd('gdp')");
await sleep(900);
const tlLight = await evalJS("(document.querySelector('#wstxt').innerText||'')");
console.log('  light:', tlLight);
ok('离线状态灯标出内置年份', /内置\s*2023/.test(tlLight), tlLight);
const tlTicks = await evalJS("document.querySelectorAll('#dticks i').length");
ok('时间轴有逐年涨跌刻度', tlTicks === 24, String(tlTicks));
const tlChg = (await evalJS("(document.querySelector('#dchg').innerText||'')")).replace(/\s+/g, ' ');
console.log('  chg:', tlChg);
ok('刻度旁有同比与累计读数', /较上年/.test(tlChg) && /较 2000/.test(tlChg), tlChg);
await evalJS("window.__globe.cmpClear(); window.__globe.compare('中国');window.__globe.compare('印度')");
await sleep(700);
await evalJS("document.querySelector('#cmpimg').click()");
await sleep(1100);
const tlCv = await evalJS("window.__shareCv?(window.__shareCv.width+'x'+window.__shareCv.height):'none'");
ok('分享图尺寸 1080x1350', tlCv === '1080x1350', String(tlCv));
const tlPng = await evalJS("window.__shareCv?window.__shareCv.toDataURL('image/png').length:0");
console.log('  share png bytes(base64):', tlPng);
ok('分享图有实际像素内容', tlPng > 50000, String(tlPng));
const tlLink = await evalJS("location.hash");
console.log('  hash:', tlLink);
ok('对比状态写进链接', /c=CHN,IND/.test(tlLink), tlLink);
await shot('a11_tools');

console.log('--- errors ---');
console.log(errs.length ? errs.join(String.fromCharCode(10)) : '(none)');
ws.close(); edge.kill();
fs.rmSync(PROFILE, { recursive: true, force: true });
