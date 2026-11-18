#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把「按需更新」按钮注入 orbis.html。

为什么用注入而不是改模板：orbis.html 是构建产物（内联了 three.js / 贴图 / 数据），
且登录封面是 login-src 补丁打上去的，直接重建会丢。这里只在 </body> 前插入一段
自包含脚本，并用标记包裹，重复注入会自动替换旧块，不会叠加。

由 page_data.rebuild_page() 在每次写数据后调用，保证数据更新后按钮依然在。
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ORBIS_HTML = os.path.join(ROOT, "orbis.html")

MARK_START = "<!-- __ONDEMAND_START__ -->"
MARK_END = "<!-- __ONDEMAND_END__ -->"

BLOCK = MARK_START + """
<script>
(function(){
  var CUR=null, TIMER=null, LOGGED=null;
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
    var host=document.querySelector('#ctitle'); if(!host) return null;
    var b=document.getElementById('odBtn');
    if(!b){
      b=document.createElement('button');
      b.id='odBtn';
      b.style.cssText='margin-left:auto;padding:5px 10px;border-radius:7px;border:1px solid rgba(200,160,106,.55);'+
        'background:rgba(200,160,106,.12);color:#d8b784;font:11px/1.2 inherit;cursor:pointer;white-space:nowrap';
      host.appendChild(b);
    }
    return b;
  }
  function setBtn(b,text,disabled){
    if(!b) return;
    b.textContent=text; b.disabled=!!disabled;
    b.style.opacity=disabled?'0.55':'1'; b.style.cursor=disabled?'default':'pointer';
  }
  function doRequest(iso,b){
    setBtn(b,'提交中…',true);
    api('/api/country/request',{method:'POST',body:{iso3:iso}}).then(function(r){
      if(!r.ok){ setBtn(b,'请求实时更新',false); alert(r.error||'请求失败'); return; }
      if(r.status==='published'){ setBtn(b,'已是最新',true); return; }
      setBtn(b, r.status==='pending_review'?'待审核…':'抓取中…', true);
      poll(iso,b);
    });
  }
  function poll(iso,b){
    if(TIMER) clearInterval(TIMER);
    var n=0;
    TIMER=setInterval(function(){
      n++;
      api('/api/country/status?iso='+iso).then(function(r){
        if(r.status==='published'){
          clearInterval(TIMER); TIMER=null;
          setBtn(b,'已更新，刷新中…',true);
          setTimeout(function(){ location.reload(); }, 1200);
        } else if(r.status==='rejected'||r.status==='failed'){
          clearInterval(TIMER); TIMER=null;
          setBtn(b,'请求实时更新',false);
          alert('该国的更新未通过审核或抓取失败，稍后再试');
        } else if(r.status==='pending_review'){ setBtn(b,'待审核…',true); }
        else if(n>180){ clearInterval(TIMER); TIMER=null; setBtn(b,'请求实时更新',false); }
      });
    }, 5000);
  }
  function sync(){
    var nEl=document.querySelector('#cname'), eEl=document.querySelector('#cen');
    if(!nEl||!nEl.textContent) return;
    var iso=isoOf(nEl.textContent.trim(), eEl?eEl.textContent.trim():'');
    if(!iso||iso===CUR) return;
    CUR=iso;
    var b=btn(); if(!b) return;
    setBtn(b,'请求实时更新',false);
    if(LOGGED===null){
      api('/api/auth/me').then(function(r){ LOGGED=!!(r.user); if(!LOGGED) setBtn(b,'登录后可请求更新',true); });
    } else if(!LOGGED){ setBtn(b,'登录后可请求更新',true); return; }
    b.onclick=function(){ if(LOGGED) doRequest(iso,b); };
  }
  setInterval(sync, 700);
})();
</script>
""" + MARK_END


def apply(html):
    """注入或替换脚本块。"""
    if MARK_START in html and MARK_END in html:
        return re.sub(re.escape(MARK_START) + r".*?" + re.escape(MARK_END), BLOCK, html, flags=re.S)
    i = html.rfind("</body>")
    if i < 0:
        return html + BLOCK
    return html[:i] + BLOCK + "\n" + html[i:]


def patch_file(path=None):
    path = path or ORBIS_HTML
    with open(path, encoding="utf-8") as f:
        html = f.read()
    out = apply(html)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(out)
    os.replace(tmp, path)
    return {"path": path, "injected": MARK_START in out, "bytes": os.path.getsize(path)}


if __name__ == "__main__":
    print(patch_file())
