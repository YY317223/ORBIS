#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把「按需更新」入口注入 orbis.html。

为什么用注入而不是改模板：orbis.html 是构建产物（内联了 three.js / 贴图 / 数据），
且登录封面是 login-src 补丁打上去的，直接重建会丢。这里只在 </body> 前插入一段
自包含脚本，并用标记包裹，重复注入会自动替换旧块，不会叠加。

由 page_data.rebuild_page() 在每次写数据后调用，保证数据更新后入口依然在。

交互（2026-11 改版）：
  点「请求实时更新」→ 弹出 5 个指标勾选框（人口 / GDP / 人均 GDP / 出口前三 / 进口前三）
  → 勾好后点「开始抓取」→ 只抓勾选的指标 → 进待审区 → 管理员通过后前端自动刷新
  → 结果区按勾选顺序列出实时数值；没有的数据明确显示「此数据未公开」，不编造。
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ORBIS_HTML = os.path.join(ROOT, "orbis.html")

MARK_START = "<!-- __ONDEMAND_START__ -->"
MARK_END = "<!-- __ONDEMAND_END__ -->"

# 放在 <head> 最前面的极小块：先把登录封面压住，等确认没有 session 再放出来。
# 为什么必须放在 head：orbis.html 是 6.7MB 单文件，浏览器可能在解析到文末脚本之前
# 就已经把封面画出来了；只有一开始就压住，才不会出现「登录页闪一下」。
HEAD_START = "<!-- __OD_GATE_START__ -->"
HEAD_END = "<!-- __OD_GATE_END__ -->"
HEAD_BLOCK = HEAD_START + r"""
<style id="odGateCss">
html.od-gate-wait #authgate{opacity:0!important;pointer-events:none!important}
html.od-gate-wait,html.od-gate-wait body{background:#08090B}
/* 查登录态期间先盖一层和封面同色的底，避免露出半成品界面。
   延迟 0.2s 才淡入：网络正常时根本看不到，只有真的慢才出现。 */
html.od-gate-wait::before{content:"";position:fixed;inset:0;z-index:99997;background:#08090B;
  opacity:0;animation:odVeil .18s ease .2s forwards}
html.od-gate-wait::after{content:"正在加载";position:fixed;left:0;right:0;bottom:46px;z-index:99998;
  text-align:center;letter-spacing:.32em;color:#7d8ea2;font:11px/1 "PingFang SC","Microsoft YaHei",sans-serif;
  opacity:0;animation:odVeil .2s ease .3s forwards}
@keyframes odVeil{to{opacity:1}}
/* 自动恢复登录时顺手跳过「欢迎来到 ORBIS」：刷新不是登录，不该再放一遍 3.7 秒的封面 */
html.od-skip-welcome #welcome{display:none!important}
</style>
<script>try{document.documentElement.classList.add('od-gate-wait')}catch(e){}</script>
""" + HEAD_END

BLOCK = MARK_START + r"""
<style id="odCss">
#odMask{position:fixed;inset:0;z-index:99999;display:none;align-items:center;justify-content:center;
  background:rgba(3,7,13,.66);backdrop-filter:blur(7px);-webkit-backdrop-filter:blur(7px);padding:16px}
#odMask.on{display:flex}
#odBox{width:min(480px,100%);max-height:calc(100vh - 40px);overflow:auto;border-radius:16px;
  background:linear-gradient(180deg,rgba(17,24,36,.985),rgba(10,15,24,.99));
  border:1px solid rgba(120,160,220,.26);box-shadow:0 26px 70px rgba(0,0,0,.6);
  color:#EAF1FA;font:13px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}
#odBox .od-hd{display:flex;align-items:center;gap:8px;padding:15px 16px 10px}
#odBox .od-hd b{font-size:14.5px;font-weight:650;letter-spacing:.01em}
#odBox .od-hd span{color:#6C819A;font-size:11.5px}
#odBox .od-x{margin-left:auto;width:26px;height:26px;border-radius:8px;border:1px solid rgba(120,160,220,.22);
  background:transparent;color:#9DB0C6;cursor:pointer;font-size:13px;line-height:1}
#odBox .od-x:hover{color:#fff;border-color:rgba(120,160,220,.5)}
#odBox .od-sub{padding:0 16px 8px;color:#6C819A;font-size:11px;line-height:1.6}
#odBox .od-ms{padding:2px 16px 6px;display:flex;flex-direction:column;gap:7px}
#odBox .od-m{display:flex;align-items:center;gap:9px;padding:9px 11px;border-radius:10px;cursor:pointer;
  background:rgba(255,255,255,.028);border:1px solid rgba(120,160,220,.16);transition:border-color .18s,background .18s}
#odBox .od-m:hover{border-color:rgba(200,160,106,.45);background:rgba(200,160,106,.06)}
#odBox .od-m input{width:15px;height:15px;accent-color:#F0A868;cursor:pointer;margin:0}
#odBox .od-m i{font-style:normal;font-size:12.5px;color:#EAF1FA}
#odBox .od-m em{margin-left:auto;font-style:normal;font-size:10.5px;color:#6C819A}
#odBox .od-state{margin:10px 16px 0;padding:8px 11px;border-radius:9px;font-size:11.5px;line-height:1.55;
  background:rgba(127,178,255,.08);border:1px solid rgba(127,178,255,.22);color:#9DB0C6}
#odBox .od-state.ok{background:rgba(120,200,150,.1);border-color:rgba(120,200,150,.3);color:#8fd6a8}
#odBox .od-state.err{background:rgba(240,149,149,.1);border-color:rgba(240,149,149,.3);color:#F09595}
#odBox .od-state.wait{background:rgba(240,168,104,.1);border-color:rgba(240,168,104,.3);color:#E8BE8A}
#odBox .od-res{margin:10px 16px 0;display:flex;flex-direction:column;gap:7px}
#odBox .od-r{display:grid;grid-template-columns:104px 1fr;gap:10px;align-items:start;padding:9px 11px;
  border-radius:10px;background:rgba(255,255,255,.022);border:1px solid rgba(120,160,220,.13)}
#odBox .od-r .k{color:#9DB0C6;font-size:11.5px;padding-top:1px}
#odBox .od-r .k s{display:block;text-decoration:none;color:#5d7286;font-size:10px;margin-top:2px}
#odBox .od-r .v{color:#fff;font-size:13.5px;font-weight:600;letter-spacing:.01em;word-break:break-word}
#odBox .od-r .v.miss{color:#7f8fa3;font-weight:500;font-size:12.5px}
#odBox .od-r .v.miss s{display:block;text-decoration:none;color:#63748a;font-weight:400;font-size:10.5px;margin-top:3px}
#odBox .od-tr{display:flex;align-items:baseline;gap:6px;margin-top:5px;font-size:11.5px;color:#c9d6e6;font-weight:400}
#odBox .od-tr i{font-style:normal;width:14px;color:#6C819A;font-size:10px;flex:0 0 auto}
#odBox .od-tr .hs{color:#6C819A;font-size:10px;flex:0 0 auto}
#odBox .od-tr .nm{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#odBox .od-tr em{margin-left:auto;font-style:normal;color:#E8BE8A;white-space:nowrap}
#odBox .od-tr em s{text-decoration:none;color:#6C819A;margin-left:5px;font-size:10px}
#odBox .od-tr em .d{text-decoration:none;color:#7f8fa3;margin-left:5px;font-size:9.5px;font-weight:400}
/* 更新前后对照：旧值划掉 → 新值，右边跟涨跌标签 */
#odBox .v.cmp{display:flex;flex-wrap:wrap;align-items:baseline;gap:6px}
#odBox .v.cmp .o{color:#7f8fa3;font-weight:500;font-size:12.5px;text-decoration:line-through;
  text-decoration-color:rgba(240,168,104,.55)}
#odBox .v.cmp .ar{font-style:normal;color:#5d7286;font-size:11px;font-weight:400}
#odBox .v.cmp .n{color:#fff}
#odBox .dlt{font-size:10.5px;padding:1px 5px;border-radius:5px;font-weight:650;letter-spacing:.02em}
#odBox .dlt.up{color:#F09595;background:rgba(240,149,149,.13)}
#odBox .dlt.down{color:#6FCF97;background:rgba(111,207,151,.13)}
#odBox .dlt.flat{color:#7f8fa3;background:rgba(255,255,255,.05);font-weight:500}
#odBox .od-note{margin:8px 16px 0;color:#6C819A;font-size:10.5px;line-height:1.6}
#odBox .od-r.chg{border-color:rgba(240,168,104,.42);background:rgba(200,160,106,.07);
  animation:odFlash 1.6s ease-out 1}
@keyframes odFlash{0%{background:rgba(240,168,104,.22)}100%{background:rgba(200,160,106,.07)}}
#odBox .od-reload{display:none}
#odBox .od-foot{display:flex;gap:8px;align-items:center;padding:14px 16px 16px}
#odBox .od-foot button{height:33px;padding:0 15px;border-radius:9px;font:inherit;font-size:12.5px;cursor:pointer}
#odBox .od-go{border:1px solid rgba(240,168,104,.6);background:rgba(240,168,104,.16);color:#F0A868;font-weight:600}
#odBox .od-go:hover:not(:disabled){background:rgba(240,168,104,.26)}
#odBox .od-go:disabled{opacity:.5;cursor:default}
#odBox .od-ghost{border:1px solid rgba(120,160,220,.24);background:transparent;color:#9DB0C6}
#odBox .od-ghost:hover{color:#fff;border-color:rgba(120,160,220,.5)}
#odBox .od-meta{margin-left:auto;color:#5d7286;font-size:10px}
@media (max-width:520px){
  #odBox .od-r{grid-template-columns:82px 1fr}
  #odBox .od-ms{padding:2px 12px 6px} #odBox .od-res{margin:10px 12px 0}
  #odBox .od-state{margin:10px 12px 0} #odBox .od-hd,#odBox .od-foot{padding-left:12px;padding-right:12px}
}
</style>
<script>
(function(){
  var CUR=null, TIMER=null, LOGGED=null, ISO=null, NAME=null, SEL=null, DETAIL=null, BASE=null, STATE='idle';
  var METRICS=[['pop','人口'],['gdp','GDP'],['pc','人均 GDP'],['exports','出口前三'],['imports','进口前三']];
  var M=null;   /* 弹窗 DOM 引用 */

  function esc(s){ return String(s==null?'':s).replace(/[&<>"]/g,function(c){
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }

  function api(p,o){
    o=o||{}; o.credentials='include';
    if(o.body){o.headers={'Content-Type':'application/json'};o.body=JSON.stringify(o.body)}
    return fetch(p,o).then(function(r){return r.json().catch(function(){return {}})})
      .catch(function(){return {}});
  }
  function isoOf(name,en){
    var cs=(window.ATLAS_DATA||{}).countries||[];
    for(var i=0;i<cs.length;i++){ if(cs[i].n===name||cs[i].en===en) return cs[i].iso3; }
    return null;
  }
  function btn(){
    /* 挂在操作栏 #cacts 里：标题区 #ctitle 被 #cmap 画布盖住，鼠标点不到 */
    var host=document.querySelector('#cacts')||document.querySelector('#ctitle');
    if(!host) return null;
    var b=document.getElementById('odBtn');
    if(!b){
      b=document.createElement('button');
      b.id='odBtn';
      b.type='button';
      b.style.cssText='position:relative;z-index:30;padding:6px 10px;border-radius:7px;'+
        'border:1px solid rgba(200,160,106,.55);background:rgba(200,160,106,.12);color:#d8b784;'+
        'font:11px/1.2 inherit;cursor:pointer;white-space:nowrap;margin-left:6px';
      host.appendChild(b);
    }
    return b;
  }
  function setBtn(b,text,disabled){
    if(!b) return;
    b.textContent=text; b.disabled=!!disabled;
    b.style.opacity=disabled?'0.55':'1'; b.style.cursor=disabled?'default':'pointer';
  }

  /* ---------------- 弹窗 ---------------- */
  function build(){
    if(M) return M;
    var mask=document.createElement('div'); mask.id='odMask';
    mask.innerHTML=
      '<div id="odBox" role="dialog" aria-modal="true">'+
        '<div class="od-hd"><b>实时更新</b><span id="odName"></span>'+
          '<button class="od-x" id="odX" title="关闭">✕</button></div>'+
        '<div class="od-sub" id="odSub">勾选要抓取的指标（可多选，最多 5 项）。勾选后点「开始抓取」，'+
          '结果先经管理员审核，通过后这里自动显示实时数值。</div>'+
        '<div class="od-ms" id="odMs"></div>'+
        '<div class="od-state" id="odState">选好指标后点「开始抓取」</div>'+
        '<div class="od-note" id="odNote"></div>'+
        '<div class="od-res" id="odRes"></div>'+
        '<div class="od-foot"><button class="od-go" id="odGo">开始抓取</button>'+
          '<button class="od-ghost od-reload" id="odReload">刷新页面</button>'+
          '<button class="od-ghost" id="odCancel">关闭</button>'+
          '<span class="od-meta" id="odMeta"></span></div>'+
      '</div>';
    document.body.appendChild(mask);
    M={mask:mask, box:mask.querySelector('#odBox'), name:mask.querySelector('#odName'),
       ms:mask.querySelector('#odMs'), state:mask.querySelector('#odState'),
       note:mask.querySelector('#odNote'),
       res:mask.querySelector('#odRes'), go:mask.querySelector('#odGo'),
       reload:mask.querySelector('#odReload'),
       meta:mask.querySelector('#odMeta'), sub:mask.querySelector('#odSub')};
    M.ms.innerHTML=METRICS.map(function(m){
      return '<label class="od-m"><input type="checkbox" data-k="'+m[0]+'" checked>'+
             '<i>'+esc(m[1])+'</i></label>';
    }).join('');
    M.box.querySelectorAll('.od-m input').forEach(function(c){
      c.onchange=function(){ SEL=checked(); if(STATE==='idle'||STATE==='done'||STATE==='failed') refreshIdle(); };
    });
    mask.querySelector('#odX').onclick=close;
    mask.querySelector('#odCancel').onclick=close;
    mask.onclick=function(e){ if(e.target===mask) close(); };
    M.go.onclick=start;
    M.reload.onclick=function(){ location.reload(); };
    document.addEventListener('keydown',function(e){ if(e.key==='Escape'&&M&&M.mask.classList.contains('on')) close(); });
    return M;
  }
  function checked(){
    var out=[];
    M.box.querySelectorAll('.od-m input').forEach(function(c){ if(c.checked) out.push(c.dataset.k); });
    return out;
  }
  function setState(text,kind){
    M.state.textContent=text;
    M.state.className='od-state'+(kind?' '+kind:'');
    M.state.style.display=text?'':'none';
  }
  function close(){
    if(TIMER){ clearInterval(TIMER); TIMER=null; }
    if(M&&M.mask) M.mask.classList.remove('on');
  }

  /* ---------------- 渲染 ---------------- */
  function rowHTML(label,value,year,miss,why){
    return '<div class="od-r"><div class="k">'+esc(label)+
      (year?'<s>'+esc(year)+' 年</s>':'')+'</div>'+
      (miss?'<div class="v miss">此数据未公开'+(why?'<s>'+esc(why)+'</s>':'')+'</div>'
           :'<div class="v">'+esc(value)+'</div>')+'</div>';
  }
  function tradeHTML(v){
    if(!v.available) return rowHTML(v.label,'',v.year,true,v.reason);
    var rows=(v.rows||[]).map(function(r,i){
      return '<div class="od-tr"><i>'+(i+1)+'</i><span class="hs">HS'+esc(r.hs)+'</span>'+
        '<span class="nm" title="'+esc(r.zh)+'">'+esc(r.zh)+'</span>'+
        '<em>'+esc(r.text)+(r.share_text?'<s>'+esc(r.share_text)+'</s>':'')+'</em></div>';
    }).join('');
    return '<div class="od-r"><div class="k">'+esc(v.label)+
      (v.year?'<s>'+esc(v.year)+' 年</s>':'')+'</div>'+
      '<div class="v">合计 '+esc(v.total_text||'—')+rows+'</div></div>';
  }
  function render(sel){
    var d=DETAIL; if(!d){ M.res.innerHTML=''; return; }
    var m=d.metrics||{}, html=[];
    for(var i=0;i<METRICS.length;i++){
      var k=METRICS[i][0];
      if(sel&&sel.indexOf(k)<0) continue;
      var v=m[k]; if(!v) continue;
      if(k==='exports'||k==='imports') html.push(tradeHTML(v));
      else if(v.available) html.push(rowHTML(v.label,v.text,v.year));
      else html.push(rowHTML(v.label,'',v.year,true,v.reason));
    }
    M.res.innerHTML=html.join('');
    M.meta.textContent=d.updated?('数据时间 '+String(d.updated).replace('T',' ').slice(0,16)):'';
  }

  /* ---------- 更新前后对照 ---------- */
  function pct(oldV,newV){
    if(typeof oldV!=='number'||typeof newV!=='number'||!oldV) return null;
    return (newV-oldV)/oldV*100;
  }
  function dltHTML(oldV,newV){
    if(typeof oldV!=='number'||typeof newV!=='number') return '';
    if(oldV===newV) return '<span class="dlt flat">与上次一致</span>';
    var p=pct(oldV,newV);
    var cls=newV>oldV?'up':(newV<oldV?'down':'flat');
    var txt=(p===null)?'有变化':((p>0?'+':'')+p.toFixed(2)+'%');
    return '<span class="dlt '+cls+'">'+txt+'</span>';
  }
  function cmpRow(label,year,oldText,newText,oldV,newV,miss,why){
    if(miss){
      return '<div class="od-r"><div class="k">'+esc(label)+
        (year?'<s>'+esc(year)+' 年</s>':'')+'</div>'+
        '<div class="v miss">此数据未公开'+(why?'<s>'+esc(why)+'</s>':'')+'</div></div>';
    }
    var changed=(oldText && oldText!==newText);
    return '<div class="od-r'+(changed?' chg':'')+'"><div class="k">'+esc(label)+
      (year?'<s>'+esc(year)+' 年</s>':'')+'</div>'+
      '<div class="v cmp">'+
        (changed?'<span class="o">'+esc(oldText)+'</span><i class="ar">→</i>':'')+
        '<span class="n">'+esc(newText)+'</span>'+dltHTML(oldV,newV)+
      '</div></div>';
  }
  function tradeCmp(v,old){
    if(!v.available) return cmpRow(v.label,v.year,'','',null,null,true,v.reason);
    old=old||{};
    var hasOld=(old.rows||[]).length>0;   /* 没有基线时不要谎报「新增」 */
    var om={};
    (old.rows||[]).forEach(function(r){ om[r.hs]=r; });
    var rows=(v.rows||[]).map(function(r,i){
      var o=om[r.hs];
      var d='';
      if(!o){ if(hasOld) d='<span class="d">新增</span>'; }
      else if(typeof o.usd==='number'&&typeof r.usd==='number'&&o.usd!==r.usd){
        var p=pct(o.usd,r.usd);
        if(p!==null) d='<span class="d">'+((p>0?'+':'')+p.toFixed(1)+'%')+'</span>';
      }
      return '<div class="od-tr"><i>'+(i+1)+'</i><span class="hs">HS'+esc(r.hs)+'</span>'+
        '<span class="nm" title="'+esc(r.zh)+'">'+esc(r.zh)+'</span>'+
        '<em>'+esc(r.text)+(r.share_text?'<s>'+esc(r.share_text)+'</s>':'')+d+'</em></div>';
    }).join('');
    var changed=(old.total_text && old.total_text!==v.total_text);
    return '<div class="od-r'+(changed?' chg':'')+'"><div class="k">'+esc(v.label)+
      (v.year?'<s>'+esc(v.year)+' 年</s>':'')+'</div>'+
      '<div class="v cmp">'+
        (changed?'<span class="o">合计 '+esc(old.total_text)+'</span><i class="ar">→</i>':'')+
        '<span class="n">合计 '+esc(v.total_text||'—')+'</span>'+
        dltHTML(old.total_usd,v.total_usd)+'</div>'+
      '<div class="v" style="margin-top:2px">'+rows+'</div></div>';
  }
  /* 对比渲染：BASE 是点开弹窗时的已发布值，DETAIL 是刚抓到的新值 */
  function renderDiff(sel){
    var now=DETAIL; if(!now){ return 0; }
    var base=(BASE&&BASE.metrics)||{}, m=now.metrics||{}, html=[];
    for(var i=0;i<METRICS.length;i++){
      var k=METRICS[i][0];
      if(sel&&sel.indexOf(k)<0) continue;
      var v=m[k]; if(!v) continue;
      var o=base[k];
      if(k==='exports'||k==='imports') html.push(tradeCmp(v,o));
      else if(v.available) html.push(cmpRow(v.label,v.year,o&&o.text,v.text,o&&o.value,v.value));
      else html.push(cmpRow(v.label,v.year,'','',null,null,true,v.reason));
    }
    var out=html.join('');
    M.res.innerHTML=out;
    M.meta.textContent=now.updated?('数据时间 '+String(now.updated).replace('T',' ').slice(0,16)):'';
    return (out.match(/od-r chg/g)||[]).length;
  }
  function renderSel(){
    var sel=checked();
    M.res.innerHTML='<div class="od-state" style="margin:0">将抓取：'+
      esc(sel.map(function(k){ for(var i=0;i<METRICS.length;i++) if(METRICS[i][0]===k) return METRICS[i][1]; return k; })
             .join('、')||'（未勾选）')+'</div>';
    M.go.disabled=!sel.length;
    if(STATE==='idle'||STATE==='done'||STATE==='failed'){
      /* 状态条只在有事要说时出现，避免和上面这行「将抓取」重复 */
      setState(sel.length?'':'至少勾选 1 个指标','');
    }
  }
  /* 未开始/已结束时的默认展示：登录用户看「将抓取」清单，游客直接看当前已发布数值 */
  function refreshIdle(){
    M.note.textContent='';
    M.reload.style.display='none';
    M.go.style.display='';
    if(M.go.textContent==='刷新页面') M.go.textContent='开始抓取';
    if(LOGGED===false){ render(checked()); return; }
    renderSel();
  }
  function loadDetail(then){
    api('/api/country/detail?iso='+encodeURIComponent(ISO)).then(function(d){
      if(d&&d.ok){ DETAIL=d; }
      if(then) then(d);
    });
  }

  /* ---------------- 流程 ---------------- */
  function open(iso,name){
    build();
    ISO=iso; NAME=name||iso; SEL=null; DETAIL=null; BASE=null; STATE='idle';
    M.name.textContent=name||iso;
    M.note.textContent='';
    M.reload.style.display='none';
    M.go.style.display='';
    M.box.querySelectorAll('.od-m input').forEach(function(c){ c.checked=true; });
    M.go.disabled=false; M.go.textContent='开始抓取';
    M.mask.classList.add('on');
    setState('正在读取该国当前已发布的数据…','');
    M.res.innerHTML='';
    api('/api/auth/me').then(function(r){
      LOGGED=!!(r&&r.user);
      if(!LOGGED){
        setState('未登录：下面是该国当前已发布的数值；请求实时更新需要先登录账号','wait');
        M.go.disabled=true; M.go.textContent='登录后才能请求';
      }
      refreshIdle();
    });
    loadDetail(function(){
      /* 记录「抓取前」的值，发布后拿它做对比 */
      if(DETAIL && !BASE) BASE=DETAIL;
      refreshIdle();
    });
  }

  function start(){
    var sel=checked();
    if(!sel.length){ return; }
    if(LOGGED===false){ setState('请先登录，再请求更新该国数据','err'); return; }
    STATE='running';
    SEL=sel.slice();
    M.note.textContent='';
    M.reload.style.display='none';
    M.go.style.display='';
    M.go.disabled=true; M.go.textContent='抓取中…';
    setState('正在抓取 ' + sel.length + ' 个指标…勾了出口/进口会慢一些（每国约 45 秒）','wait');
    api('/api/country/request',{method:'POST',body:{iso3:ISO,metrics:sel}}).then(function(r){
      if(!r||!r.ok){
        STATE='failed'; M.go.disabled=false; M.go.textContent='重试';
        setState((r&&r.error)||'请求失败，稍后再试','err');
        var b=document.getElementById('odBtn'); setBtn(b,'请求实时更新',false);
        return;
      }
      if(r.status==='published'){
        /* 别的用户 6 小时内刚更新过：直接展示当前值，不和旧值对比（本来就一样） */
        STATE='done'; M.go.disabled=false; M.go.textContent='重新抓取';
        setState('该国 6 小时内刚更新过，下面是当前数据','ok');
        loadDetail(function(){ render(SEL||sel); });
        return;
      }
      if(r.status==='pending_review'){
        STATE='review'; M.go.textContent='待审核…';
        setState('数据已抓取，等待管理员审核通过后自动显示','wait');
        loadDetail(function(){ render(SEL||sel); });
        poll();
        return;
      }
      STATE='fetching';
      setState('抓取中…抓好后会进入待审区，审核通过这里会自动更新','wait');
      loadDetail(function(){ render(sel); });
      poll();
    });
  }

  function poll(){
    if(TIMER) clearInterval(TIMER);
    var n=0;
    TIMER=setInterval(function(){
      n++;
      api('/api/country/status?iso='+encodeURIComponent(ISO)).then(function(r){
        var st=r&&r.status;
        if(st==='published'){
          clearInterval(TIMER); TIMER=null;
          STATE='done';
          /* 不刷新页面：就地换成「旧值 → 新值」对照，让用户直接看到这次更新带来了什么 */
          loadDetail(function(){
            var n=renderDiff(SEL);
            var t=(DETAIL&&DETAIL.updated)?('（'+String(DETAIL.updated).replace('T',' ').slice(11,16)+' 抓取）'):'';
            setState(n?('已更新'+t+'：'+n+' 项有新数值，左边是更新前，右边是刚发布的实时值')
                      :('已更新'+t+'：数据源本次没有新数值，各项与上次一致'),'ok');
            M.go.style.display='none';
            M.reload.style.display='inline-block';
            M.note.textContent='地图和左侧面板仍是更新前的数字，点「刷新页面」可同步整页。';
          });
        } else if(st==='rejected'||st==='failed'){
          clearInterval(TIMER); TIMER=null;
          STATE='failed';
          M.go.disabled=false; M.go.textContent='重试';
          setState(st==='rejected'?'这次更新没通过审核，数据没有改动':'抓取失败：'+(r.error||'稍后再试'),'err');
          var b=document.getElementById('odBtn'); setBtn(b,'请求实时更新',false);
        } else if(st==='pending_review'){
          STATE='review'; M.go.textContent='待审核…';
          setState('数据已抓取，等待管理员审核通过后自动显示','wait');
        } else if(st==='fetching'||st==='queued'){
          setState('抓取中…（'+(n*5)+' 秒）','wait');
        } else if(n>150){
          clearInterval(TIMER); TIMER=null;
          STATE='failed'; M.go.disabled=false; M.go.textContent='重试';
          setState('等了 12 分钟还没结果，可以先关掉；审核通过后再点一次「请求实时更新」查看','err');
        }
      });
    },5000);
  }

  /* ---------------- 登录态自动恢复（不留闪烁） ----------------
     页面刷新（包括按需更新发布后的自动刷新）时后端 session 还在，但登录封面会重新出现。
     做法分两段：
       1) <head> 里先给 <html> 加 od-gate-wait，把封面压成透明（只留深色底 + 加载层）；
       2) 这里查 /api/auth/me —— 有 session 就替用户点掉即将出现的「以 xxx 直接进入」，
          确认没 session 才把封面放出来。
     所以正常用户永远看不到登录页闪一下；退出登录的人还是会正常看到登录页。 */
  (function resumeSession(){
    var revealed=false, waited=0;
    function reveal(){ if(revealed) return; revealed=true; document.documentElement.classList.remove('od-gate-wait'); }
    function waitEnter(){
      waited+=120;
      var b=document.getElementById('ag-go'), g=document.getElementById('authgate');
      if(b && g && (b.textContent||'').indexOf('直接进入')>=0){
        window.__odResume=1;
        /* 刷新不是「登录」，不重播欢迎画面；用一个临时 class 压住，
           4 秒后自动摘掉，不影响同一页面里之后的正常登录流程 */
        var root=document.documentElement;
        root.classList.add('od-skip-welcome');
        setTimeout(function(){ root.classList.remove('od-skip-welcome'); },4200);
        b.click();                 /* 等价于用户点「以 xxx 直接进入」 */
        setTimeout(reveal,120);    /* 等封面自己进 .gone 淡出，再放行，避免露出任何一帧 */
        return;
      }
      if(waited>2600){ reveal(); return; }
      setTimeout(waitEnter,120);
    }
    fetch('/api/auth/me',{credentials:'include'})
      .then(function(r){ return r.json(); })
      .then(function(d){ if(d && d.user){ waitEnter(); } else { reveal(); } })
      .catch(function(){ reveal(); });
    setTimeout(reveal,3500);       /* 兜底：任何异常都不留黑屏 */
  })();

  /* ---------------- 挂载入口 ---------------- */
  function sync(){
    var nEl=document.querySelector('#cname'), eEl=document.querySelector('#cen');
    if(!nEl||!nEl.textContent) return;
    var iso=isoOf(nEl.textContent.trim(), eEl?eEl.textContent.trim():'');
    if(!iso||iso===CUR) return;
    CUR=iso;
    var b=btn(); if(!b) return;
    setBtn(b,'请求实时更新',false);
    b.onclick=function(){
      var iso2=CUR; if(!iso2) return;
      open(iso2, nEl.textContent.trim());
    };
  }
  setInterval(sync, 700);
})();
</script>
""" + MARK_END


def _inject_body(html):
    """注入或替换文末脚本块。"""
    if MARK_START in html and MARK_END in html:
        return re.sub(re.escape(MARK_START) + r".*?" + re.escape(MARK_END), BLOCK, html, flags=re.S)
    i = html.rfind("</body>")
    if i < 0:
        return html + BLOCK
    return html[:i] + BLOCK + "\n" + html[i:]


def _inject_head(html):
    """把「压住登录封面」的小块插到 <head> 最前面；重复调用只替换不叠加。"""
    if HEAD_START in html and HEAD_END in html:
        return re.sub(re.escape(HEAD_START) + r".*?" + re.escape(HEAD_END), HEAD_BLOCK, html,
                      count=1, flags=re.S)
    i = html.find("<head>")
    if i >= 0:
        j = i + len("<head>")
        return html[:j] + "\n" + HEAD_BLOCK + html[j:]
    i = html.find("<body")
    if i >= 0:
        return html[:i] + HEAD_BLOCK + "\n" + html[i:]
    return HEAD_BLOCK + html


def apply(html):
    """页头压封面 + 文末脚本，两处一起处理（重复调用安全）。

    page_data.rebuild_page() 只调这一个函数，所以把两块都放在这里，
    避免以后加的东西在重建页面时被漏掉。
    """
    return _inject_body(_inject_head(html))


def patch_file(path=None):
    path = path or ORBIS_HTML
    with open(path, encoding="utf-8") as f:
        html = f.read()
    out = apply(html)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(out)
    os.replace(tmp, path)
    return {"path": path, "injected": MARK_START in out, "gate": HEAD_START in out,
            "bytes": os.path.getsize(path)}


if __name__ == "__main__":
    print(patch_file())
