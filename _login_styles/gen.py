# -*- coding: utf-8 -*-
"""生成 4 个登录页风格效果图"""
import io

FORM = '''
<div class="wrap">
  <div class="brand">
    <div class="logo"><span class="orb"></span><span class="lname">ORBIS</span></div>
    <h2>用数据重新认识这颗星球</h2>
    <p class="lead">用数据重新认识我们生活的星球</p>
    <ul class="feat">
      <li><i>01</i><span><b>全球 200+ 国家</b><em>GDP · 人口 · 寿命 · 汇率实时数据</em></span></li>
      <li><i>02</i><span><b>对比与分享</b><em>链接记住状态，一键生成精美分享图</em></span></li>
      <li><i>03</i><span><b>变化追踪</b><em>关注国家数据大变，邮件自动提醒</em></span></li>
    </ul>
    <p class="src">世界银行 WDI · Frankfurter 111 家央行</p>
  </div>
  <div class="card">
    <div class="ctitle">欢迎回来</div>
    <p class="csub">登录以使用完整账户功能</p>
    <div class="tabs"><button class="on">登录</button><button>注册</button></div>
    <label>邮箱<input type="email" placeholder="you@example.com"></label>
    <label>密码<input type="password" placeholder="请输入密码"></label>
    <div class="row"><label class="rem"><input type="checkbox" checked> 记住我 30 天</label><a class="fog">忘记密码?</a></div>
    <button class="go">登录并进入 <span>→</span></button>
    <div class="or"><span>或</span></div>
    <button class="guest">以访客身份浏览</button>
    <p class="foot">登录即表示同意服务条款与隐私政策</p>
  </div>
</div>
'''

BASE = '''<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{width:1280px;height:800px;overflow:hidden;font-family:Inter,"PingFang SC","Microsoft YaHei",sans-serif;background:#03070f;color:#fff}
.wrap{position:relative;z-index:3;width:100%;height:100%;display:flex;align-items:center;justify-content:space-between;padding:0 9% 0 10%}
.brand{width:46%}
.logo{display:flex;align-items:center;gap:13px;margin-bottom:26px}
.orb{width:34px;height:34px;border-radius:50%;display:block}
.lname{font-size:22px;font-weight:700;letter-spacing:.32em}
.brand h2{font-size:38px;font-weight:700;letter-spacing:.03em;line-height:1.2;margin-bottom:12px}
.lead{font-size:15px;letter-spacing:.05em;margin-bottom:38px}
.feat{list-style:none;display:flex;flex-direction:column;gap:19px}
.feat li{display:flex;gap:15px;align-items:flex-start}
.feat i{font-style:normal;font-size:11px;font-weight:600;letter-spacing:.1em;padding-top:3px;min-width:22px}
.feat span{display:flex;flex-direction:column;gap:4px}
.feat b{font-size:14px;font-weight:600}
.feat em{font-style:normal;font-size:12px;opacity:.55}
.src{margin-top:34px;font-size:11px;letter-spacing:.04em;opacity:.4}
.card{width:392px;padding:34px 34px 26px;position:relative}
.ctitle{font-size:23px;font-weight:700;letter-spacing:.02em}
.csub{font-size:12.5px;opacity:.55;margin-top:6px}
.tabs{display:flex;gap:5px;padding:4px;border-radius:9px;margin:24px 0 20px;position:relative}
.tabs button{flex:1;padding:10px;border:0;border-radius:6px;font:inherit;font-size:13px;font-weight:600;cursor:pointer;background:transparent}
.tabs button.on{color:#06121e}
.card label{display:block;font-size:12px;font-weight:500;margin-bottom:15px;letter-spacing:.02em}
.card label input{display:block;width:100%;margin-top:9px;padding:13px 14px;font:inherit;font-size:13px;outline:none;border-radius:8px}
.card label input::placeholder{opacity:.38}
.row{display:flex;justify-content:space-between;align-items:center;margin:-3px 0 20px;font-size:12px}
.rem{display:flex!important;align-items:center;gap:7px;cursor:pointer;font-size:12px!important}
.rem input{width:auto!important;margin:0!important;padding:0!important;accent-color:#5fc8f0}
.fog{cursor:pointer;text-decoration:none}
.go,.guest{width:100%;padding:14px;font:inherit;font-size:14px;font-weight:700;border-radius:9px;cursor:pointer;letter-spacing:.02em}
.go span{margin-left:8px}
.or{text-align:center;font-size:11px;opacity:.35;margin:15px 0;position:relative}
.or:before,.or:after{content:"";position:absolute;top:50%;width:43%;height:1px;background:rgba(255,255,255,.13)}
.or:before{left:0}.or:after{right:0}
.foot{text-align:center;font-size:10.5px;opacity:.35;margin-top:16px}
</style></head><body>
__BG__
__EXTRA__
FORM
</body></html>'''


def orb_gradient(c1, c2, c3):
    return ('background:radial-gradient(circle at 32%% 28%%,%s 0%%,%s 38%%,%s 72%%,#06121f 100%%)'
            % (c1, c2, c3))

# ---------- A 深空地球 ----------
A = {
 'bg': '''<div style="position:absolute;inset:0;background:radial-gradient(ellipse at 24% 55%,#0d2b45 0%,#061525 45%,#02060d 82%)"></div>
<div style="position:absolute;left:-8%;top:50%;transform:translateY(-50%);width:720px;height:720px;border-radius:50%;
  background:radial-gradient(circle at 32% 30%,#3f8fd6 0%,#1d5a94 32%,#0d3157 62%,#05182b 100%);
  box-shadow:0 0 120px rgba(60,140,210,.35),inset -40px -30px 90px rgba(0,0,0,.7);opacity:.9">
  <div style="position:absolute;inset:6%;border-radius:50%;border:1px solid rgba(150,200,240,.16);
    background:repeating-linear-gradient(0deg,transparent 0 38px,rgba(140,190,230,.06) 38px 39px)"></div>
</div>
<div style="position:absolute;left:6%;top:50%;transform:translateY(-50%) rotate(-18deg);width:660px;height:660px;
  border-radius:50%;border:1px solid rgba(240,168,104,.22)"></div>
<div style="position:absolute;left:13%;top:50%;transform:translateY(-50%) rotate(24deg);width:560px;height:560px;
  border-radius:50%;border:1px dashed rgba(120,180,230,.18)"></div>''',
 'extra': '',
 'css': '''
 .orb{__ORB__;box-shadow:0 0 22px rgba(90,160,220,.6),inset -4px -5px 9px rgba(0,0,0,.6)}
 .lname{color:#f2f8ff}
 .brand h2{color:#eef6ff}.lead{color:#9fc4dc}.feat i{color:#f0a868}.feat b{color:#dceef8}.feat em{color:#7fa0b6}.src{color:#5f8197}
 .card{background:rgba(9,20,34,.72);border:1px solid rgba(120,175,215,.2);border-radius:16px;
   backdrop-filter:blur(20px);box-shadow:0 24px 70px rgba(0,0,0,.5)}
 .ctitle{color:#f0f8ff}.csub{color:#93b4c9}
 .tabs{background:rgba(255,255,255,.05)}
 .tabs button{color:#8fb0c4}.tabs button.on{background:#f0a868;color:#1a1206}
 .card label{color:#b8d2e2}
 .card label input{background:rgba(255,255,255,.05);border:1px solid rgba(130,180,215,.22);color:#eaf6ff}
 .card label input:focus{border-color:#f0a868}
 .fog{color:#f0a868}.rem{color:#9fb8c9}
 .go{background:linear-gradient(135deg,#f6b877,#e89350);color:#1a1206;box-shadow:0 8px 24px rgba(232,147,80,.28)}
 .guest{background:transparent;color:#a8c8dc;border:1px solid rgba(130,180,215,.28)}
 .or,.foot{color:#7fa0b6}
 '''}
A['css'] = A['css'].replace('__ORB__', orb_gradient('#8FD0FF', '#2E7BD6', '#123A73'))

# ---------- B 赛博霓虹 ----------
B = {
 'bg': '''<div style="position:absolute;inset:0;background:radial-gradient(ellipse at 70% 40%,#241547 0%,#0d0a24 50%,#05030f 85%)"></div>
<div style="position:absolute;inset:0;background-image:linear-gradient(rgba(120,90,220,.07) 1px,transparent 1px),
  linear-gradient(90deg,rgba(120,90,220,.07) 1px,transparent 1px);background-size:44px 44px;
  mask-image:radial-gradient(ellipse at 50% 50%,#000,transparent 78%)"></div>
<div style="position:absolute;left:8%;top:52%;transform:translateY(-50%);width:600px;height:600px;border-radius:50%;
  background:radial-gradient(circle at 35% 30%,rgba(90,230,220,.22),rgba(120,80,230,.12) 45%,transparent 70%);filter:blur(20px)"></div>
<div style="position:absolute;left:0;top:180px;width:100%;height:2px;background:linear-gradient(90deg,transparent,#4de8d0,transparent);opacity:.35"></div>
<div style="position:absolute;left:0;top:560px;width:100%;height:1px;background:linear-gradient(90deg,transparent,#a86cf0,transparent);opacity:.25"></div>''',
 'extra': '',
 'css': '''
 .orb{__ORB__;box-shadow:0 0 22px rgba(90,240,220,.7),inset -4px -5px 9px rgba(0,0,0,.6)}
 .lname{color:#eafcff;text-shadow:0 0 20px rgba(90,240,220,.5)}
 .brand h2{color:#f0faff}.lead{color:#a9b8e0}.feat i{color:#4de8d0}.feat b{color:#e2eaff}.feat em{color:#8a94c0}.src{color:#5f6a9a}
 .card{background:linear-gradient(160deg,rgba(20,16,44,.9),rgba(10,8,26,.92));border:1px solid rgba(120,100,230,.4);border-radius:14px;
   box-shadow:0 0 0 1px rgba(80,230,210,.12),0 20px 60px rgba(80,60,180,.35)}
 .ctitle{color:#eafcff}.csub{color:#9aa6d6}
 .tabs{background:rgba(120,100,230,.12)}
 .tabs button{color:#9aa6d6}.tabs button.on{background:linear-gradient(135deg,#4de8d0,#4d9ae8);color:#06121e;box-shadow:0 0 18px rgba(80,230,210,.4)}
 .card label{color:#bcc6ee}
 .card label input{background:rgba(120,100,230,.09);border:1px solid rgba(120,110,220,.32);color:#eef2ff}
 .card label input:focus{border-color:#4de8d0;box-shadow:0 0 0 2px rgba(80,230,210,.14)}
 .fog{color:#4de8d0}.rem{color:#a0aad4}
 .go{background:linear-gradient(135deg,#4de8d0,#4d9ae8);color:#06121e;box-shadow:0 8px 26px rgba(80,200,220,.4)}
 .guest{background:transparent;color:#b9c4ee;border:1px solid rgba(120,110,220,.38)}
 .or,.foot{color:#8894c4}
 '''}
B['css'] = B['css'].replace('__ORB__', orb_gradient('#8ff8ec', '#4d9ae8', '#7a4de0'))

# ---------- C 极光流光 ----------
C = {
 'bg': '''<div style="position:absolute;inset:0;background:linear-gradient(135deg,#071a24 0%,#0a1424 45%,#120e26 100%)"></div>
<div style="position:absolute;left:-10%;top:-20%;width:900px;height:700px;border-radius:50%;
  background:radial-gradient(ellipse,rgba(80,210,180,.24),transparent 62%);filter:blur(30px)"></div>
<div style="position:absolute;right:-8%;bottom:-15%;width:820px;height:680px;border-radius:50%;
  background:radial-gradient(ellipse,rgba(140,110,230,.26),transparent 62%);filter:blur(30px)"></div>
<div style="position:absolute;left:22%;top:8%;width:520px;height:2px;background:linear-gradient(90deg,transparent,rgba(120,230,200,.5),transparent);transform:rotate(-12deg)"></div>''',
 'extra': '',
 'css': '''
 .orb{__ORB__;box-shadow:0 0 26px rgba(100,220,200,.5),inset -4px -5px 9px rgba(0,0,0,.5)}
 .lname{color:#f0faf8}
 .brand h2{color:#eaf7f4}.lead{color:#a8c9c4}.feat i{color:#7fdcc0}.feat b{color:#dcefe9}.feat em{color:#8fb0aa}.src{color:#6a8d88}
 .card{background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.16);border-radius:22px;
   backdrop-filter:blur(28px);box-shadow:0 24px 70px rgba(0,0,0,.3)}
 .ctitle{color:#f2fbf9}.csub{color:#a9c4bf}
 .tabs{background:rgba(255,255,255,.08)}
 .tabs button{color:#b0c8c3}.tabs button.on{background:rgba(255,255,255,.9);color:#12322c}
 .card label{color:#cfe4df}
 .card label input{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.16);color:#f0faf8}
 .card label input:focus{border-color:#7fdcc0;background:rgba(127,220,192,.1)}
 .fog{color:#7fdcc0}.rem{color:#b0c8c3}
 .go{background:linear-gradient(135deg,#7fdcc0,#5aa9d8);color:#0a2420;box-shadow:0 10px 30px rgba(100,200,190,.3)}
 .guest{background:rgba(255,255,255,.05);color:#d0e4df;border:1px solid rgba(255,255,255,.18)}
 .or,.foot{color:#8fb0aa}
 '''}
C['css'] = C['css'].replace('__ORB__', orb_gradient('#b8f0e0', '#5aa9d8', '#8a6ad0'))

# ---------- D 星际控制台 ----------
D = {
 'bg': '''<div style="position:absolute;inset:0;background:#030b10;
   background-image:linear-gradient(rgba(80,200,180,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(80,200,180,.05) 1px,transparent 1px);
   background-size:60px 60px"></div>
<div style="position:absolute;left:60px;top:60px;width:40px;height:40px;border-left:2px solid #4de8c0;border-top:2px solid #4de8c0;opacity:.6"></div>
<div style="position:absolute;right:60px;bottom:60px;width:40px;height:40px;border-right:2px solid #4de8c0;border-bottom:2px solid #4de8c0;opacity:.6"></div>
<div style="position:absolute;left:10%;top:50%;transform:translateY(-50%);width:520px;height:520px;border-radius:50%;
   background:radial-gradient(circle at 35% 30%,rgba(77,232,192,.18),rgba(20,80,90,.1) 55%,transparent 72%);
   border:1px solid rgba(77,232,192,.18)"></div>
<div style="position:absolute;left:calc(10% + 260px);top:50%;width:700px;height:1px;background:linear-gradient(90deg,rgba(77,232,192,.4),transparent)"></div>
<div style="position:absolute;left:8%;top:14%;font-family:monospace;font-size:10px;color:rgba(77,232,192,.5);letter-spacing:.2em">SYS.ORB // AUTH GATEWAY v2.4</div>''',
 'extra': '',
 'css': '''
 body{font-family:Inter,"PingFang SC",sans-serif}
 .orb{__ORB__;box-shadow:0 0 18px rgba(77,232,192,.6);border-radius:50%}
 .lname{color:#d8fff4;font-family:monospace;letter-spacing:.28em}
 .brand h2{color:#e2fff6;font-size:36px}.lead{color:#8fbdb0;font-family:monospace;font-size:13px}
 .feat i{color:#4de8c0;font-family:monospace}.feat b{color:#d2f5ea}.feat em{color:#7fa89c}.src{color:#5c867b;font-family:monospace}
 .card{background:rgba(4,20,22,.82);border:1px solid rgba(77,232,192,.35);border-radius:0;position:relative;
   box-shadow:0 0 0 1px rgba(77,232,192,.08)}
 .card:before{content:"";position:absolute;left:-1px;top:-1px;width:16px;height:16px;border-left:2px solid #4de8c0;border-top:2px solid #4de8c0}
 .card:after{content:"";position:absolute;right:-1px;bottom:-1px;width:16px;height:16px;border-right:2px solid #4de8c0;border-bottom:2px solid #4de8c0}
 .ctitle{color:#d8fff4;font-family:monospace;letter-spacing:.06em}.csub{color:#8fbdb0;font-family:monospace;font-size:12px}
 .tabs{background:rgba(77,232,192,.08);border-radius:0}
 .tabs button{color:#8fbdb0;border-radius:0;font-family:monospace}.tabs button.on{background:rgba(77,232,192,.16);color:#4de8c0}
 .card label{color:#a8d4c6;font-family:monospace}
 .card label input{background:rgba(77,232,192,.05);border:1px solid rgba(77,232,192,.25);border-radius:0;color:#e2fff6;font-family:monospace}
 .card label input:focus{border-color:#4de8c0;box-shadow:0 0 0 1px rgba(77,232,192,.2)}
 .fog{color:#4de8c0;font-family:monospace}.rem{color:#8fbdb0;font-family:monospace}
 .go{background:#4de8c0;color:#041814;border-radius:0;font-family:monospace;box-shadow:0 0 22px rgba(77,232,192,.3)}
 .guest{background:transparent;color:#8fbdb0;border:1px solid rgba(77,232,192,.3);border-radius:0;font-family:monospace}
 .or,.foot{color:#6f9b8f;font-family:monospace}
 '''}
D['css'] = D['css'].replace('__ORB__', orb_gradient('#a8ffe8', '#3fae8c', '#1a5a52'))

for name, cfg in [('A_深空地球', A), ('B_赛博霓虹', B), ('C_极光流光', C), ('D_星际控制台', D)]:
    html = BASE.replace('__BG__', cfg['bg']).replace('__EXTRA__', cfg['extra']).replace('FORM', FORM)
    html = html.replace('</style>', cfg['css'] + '\n</style>')
    io.open('C:/0_workspace/项目二2/_login_styles/%s.html' % name, 'w', encoding='utf-8').write(html)
    print('wrote', name)
