# -*- coding: utf-8 -*-
"""ORBIS 登录页 —— 第三组：全部落在项目既有的深空 / 数据语汇里
文案沿用现有页面（含新的副标题），只换视觉语言。"""
import io, os, sys, math

sys.path.insert(0, 'C:/0_workspace/项目二2/_login_styles2')
from gen2 import globe, doc  # 复用正交投影球体与文档模板

OUT = 'C:/0_workspace/项目二2/_login_styles3'
os.makedirs(OUT, exist_ok=True)

TABS = '<div class="tabs"><button class="on">登录</button><button>注册</button></div>'
FIELDS = '''<label class="fld"><span>邮箱</span><input type="email" value="2106812162@qq.com"></label>
    <label class="fld"><span>密码</span><input type="password" value="········"></label>
    <div class="row"><label class="chk"><input type="checkbox" checked><span>保持登录 30 天</span></label><a class="lnk">忘记密码</a></div>
    <button class="go">登录并进入</button>
    <div class="or">或</div>
    <button class="guest">以访客身份浏览</button>'''

WORD = 'ORBIS'

# ======================================================= K 极光深空
K_CSS = '''
body{background:#04080f;position:relative;overflow:hidden}
.bg{position:absolute;inset:0;background:radial-gradient(ellipse 80% 60% at 30% 0%,#0d2038 0%,#071322 40%,#04080f 78%)}
.aur{position:absolute;border-radius:50%;filter:blur(70px);opacity:.5}
.a1{width:900px;height:420px;left:-160px;top:-140px;background:radial-gradient(ellipse,rgba(64,214,196,.5),transparent 65%);transform:rotate(-12deg)}
.a2{width:760px;height:380px;left:340px;top:-180px;background:radial-gradient(ellipse,rgba(96,132,240,.45),transparent 65%);transform:rotate(8deg)}
.a3{width:620px;height:340px;left:880px;top:-120px;background:radial-gradient(ellipse,rgba(150,104,232,.4),transparent 66%);transform:rotate(-6deg)}
.stars{position:absolute;inset:0;opacity:.5}
.planet{position:absolute;right:-400px;bottom:-540px;opacity:.92;filter:drop-shadow(0 0 90px rgba(56,132,196,.3))}
.vig{position:absolute;inset:0;background:radial-gradient(ellipse 60% 50% at 22% 55%,rgba(3,6,12,.5),transparent 72%)}
.stage{position:relative;z-index:6;height:100%;display:grid;grid-template-columns:1fr 1fr;align-items:center}
.left{padding-left:104px}
.logo{display:flex;align-items:center;gap:12px;margin-bottom:26px}
.logo b{font-size:14px;letter-spacing:.36em;color:#e7f4fb;font-weight:600}
.logo i{font-style:normal;font-size:9px;letter-spacing:.18em;color:#6d8ba4;padding-left:12px;border-left:1px solid rgba(140,190,225,.2)}
.card{width:412px;padding:34px 34px 26px;border-radius:18px;border:1px solid transparent;
  background:linear-gradient(165deg,rgba(11,24,40,.78),rgba(7,15,26,.86)) padding-box,
    linear-gradient(150deg,rgba(110,235,212,.4),rgba(90,140,240,.16) 45%,rgba(158,112,236,.34)) border-box;
  backdrop-filter:blur(22px);box-shadow:0 40px 100px rgba(0,0,0,.6),inset 0 1px 0 rgba(170,220,245,.1)}
h2{font-size:21px;font-weight:600;color:#eef8ff;letter-spacing:.02em}
.cs{font-size:11.5px;color:#7493ab;margin:9px 0 22px}
.tabs{display:flex;gap:4px;padding:4px;border-radius:10px;background:rgba(255,255,255,.05);margin-bottom:22px;
  border:1px solid rgba(120,180,220,.1)}
.tabs button{flex:1;padding:9px;border:0;border-radius:7px;background:none;color:#7c9bb2;font-size:12.5px;cursor:pointer;letter-spacing:.06em}
.tabs button.on{background:linear-gradient(135deg,rgba(104,232,210,.2),rgba(104,150,240,.16));color:#b8f0e6;font-weight:600}
.fld{display:block;margin-bottom:14px}
.fld span{display:block;font-size:10.5px;color:#7c9bb2;margin-bottom:7px;letter-spacing:.04em}
.fld input{width:100%;padding:12px 13px;border-radius:9px;background:rgba(255,255,255,.045);
  border:1px solid rgba(120,180,220,.16);font-size:13px;color:#eaf6ff;outline:none}
.fld input:focus{border-color:rgba(104,232,210,.6);background:rgba(104,232,210,.07)}
.row{display:flex;justify-content:space-between;align-items:center;font-size:11.5px;color:#7c9bb2;margin:2px 0 18px}
.chk{display:flex;align-items:center;gap:7px;cursor:pointer}
.chk input{accent-color:#68e8d2;width:13px;height:13px}
.lnk{color:#7c9bb2;text-decoration:none;cursor:pointer}
.go{width:100%;padding:13px;border:0;border-radius:9px;cursor:pointer;font-size:13.5px;font-weight:700;
  background:linear-gradient(135deg,#8ef0dc,#5aa8e8);color:#05171d;letter-spacing:.04em;
  box-shadow:0 10px 30px rgba(90,200,210,.28)}
.or{position:relative;text-align:center;font-size:10px;color:#5f8197;margin:15px 0}
.or:before,.or:after{content:"";position:absolute;top:50%;width:44%;height:1px;background:rgba(120,170,205,.14)}
.or:before{left:0}.or:after{right:0}
.guest{width:100%;padding:11px;border-radius:9px;background:none;border:1px solid rgba(120,170,205,.22);
  color:#9dbdd2;font-size:12px;cursor:pointer}
.foot{font-size:9.5px;color:#54748a;text-align:center;margin-top:18px;line-height:1.7;letter-spacing:.03em}
.right{position:relative;padding-right:104px;text-align:right;align-self:start;padding-top:92px}
.right .kick{font-size:10px;letter-spacing:.3em;color:#7ff0dc;margin-bottom:22px}
.right h1{font-size:46px;line-height:1.34;font-weight:300;color:#f0f8ff;letter-spacing:.04em}
.right h1 b{font-weight:600}
.right p{margin-top:18px;font-size:12.5px;line-height:1.95;color:#9dbad0;letter-spacing:.02em;margin-left:auto;max-width:372px}
.chips{display:flex;gap:10px;justify-content:flex-end;margin-top:32px}
.chip{padding:10px 16px;border-radius:10px;border:1px solid rgba(120,190,225,.18);background:rgba(10,24,38,.55);
  backdrop-filter:blur(10px);text-align:left}
.chip b{display:block;font-size:19px;font-weight:300;color:#eaf6ff;line-height:1}
.chip span{display:block;margin-top:6px;font-size:9px;letter-spacing:.14em;color:#6d8ba4}
'''

K_BODY = '''<div class="bg"></div><div class="aur a1"></div><div class="aur a2"></div><div class="aur a3"></div>
<svg class="stars" width="1440" height="900"><g fill="#dbeaf8">__STARS__</g></svg>
<div class="planet">__PLANET__</div><div class="vig"></div>
<div class="stage">
  <div class="left">
    <div class="logo"><b>ORBIS</b><i>EARTH DATA ATLAS</i></div>
    <div class="card">
      __TABS__
      <h2>欢迎回来</h2>
      <p class="cs">登录以使用完整账户功能 · 游客可免费浏览地球</p>
      __FIELDS__
      <p class="foot">管理员入口 → 此处请用邮箱登录，不是管理员账号<br>数据源：世界银行 WDI · Frankfurter（111 家央行）</p>
    </div>
  </div>
  <div class="right">
    <div class="kick">EARTH DATA ATLAS / 217 COUNTRIES</div>
    <h1>用数据重新认识<br><b>这颗星球</b><br>看数字如何改变世界</h1>
    <p>200+ 国家的 GDP、人口、寿命与汇率，落在同一颗球面上。25 年，一条时间轴，一个国家形状的变化。</p>
  </div>
</div>'''

K_BODY = K_BODY.replace('__TABS__', TABS).replace('__FIELDS__', FIELDS)
K_BODY = K_BODY.replace('__PLANET__', globe(1060, '#3a86bd', '#0f3a5c', '#030d16', '#a8d8f4', .12, 20, 7, 9))
K_BODY = K_BODY.replace('__STARS__', ''.join(
    '<circle cx="%d" cy="%d" r="%.1f" opacity="%.2f"/>' % ((i * 467 + 31) % 1440, (i * 233 + 17) % 760, .5 + (i % 3) * .35, .16 + (i % 5) * .11)
    for i in range(150)))


# ======================================================= L 星图连线
L_CSS = '''
body{background:#050a13;position:relative;overflow:hidden;display:grid;grid-template-columns:600px 1fr}
.vig{position:absolute;inset:0;background:radial-gradient(ellipse 70% 70% at 78% 42%,#0b1a2c 0%,#060c16 48%,#04080f 82%)}
.map{position:absolute;inset:0;z-index:2}
.panel{position:relative;z-index:5;background:linear-gradient(180deg,rgba(6,13,22,.92),rgba(5,10,18,.96));
  border-right:1px solid rgba(130,175,215,.14);display:flex;flex-direction:column;justify-content:center;padding:0 68px}
.logo{display:flex;align-items:center;gap:12px;margin-bottom:44px}
.logo b{font-size:14px;letter-spacing:.36em;color:#e7f4fb;font-weight:600}
.logo i{font-style:normal;font-size:9px;letter-spacing:.18em;color:#6d8ba4;padding-left:12px;border-left:1px solid rgba(140,190,225,.2)}
h2{font-size:26px;font-weight:600;color:#eef8ff;letter-spacing:.02em}
.cs{font-size:11.5px;color:#7493ab;margin:10px 0 26px}
.tabs{display:flex;gap:28px;border-bottom:1px solid rgba(130,175,215,.16);margin-bottom:26px}
.tabs button{background:none;border:0;cursor:pointer;padding:0 0 11px;font-size:12px;letter-spacing:.14em;color:#6f8ca6;position:relative}
.tabs button.on{color:#eaf6ff;font-weight:600}
.tabs button.on:after{content:"";position:absolute;left:0;right:0;bottom:-1px;height:1.5px;background:#68e8d2}
.fld{display:block;margin-bottom:20px}
.fld span{display:block;font-size:10px;letter-spacing:.16em;color:#6f8ca6;margin-bottom:8px}
.fld input{width:100%;background:none;border:0;border-bottom:1px solid rgba(130,175,215,.24);
  padding:5px 0 10px;font-size:13.5px;color:#eaf6ff;outline:none;letter-spacing:.02em}
.fld input:focus{border-color:#68e8d2}
.row{display:flex;justify-content:space-between;align-items:center;font-size:11px;color:#6f8ca6;margin:2px 0 24px}
.chk{display:flex;align-items:center;gap:7px;cursor:pointer}
.chk input{accent-color:#68e8d2;width:12px;height:12px}
.lnk{color:#6f8ca6;text-decoration:none;cursor:pointer}
.go{width:100%;padding:14px;border:0;border-radius:8px;cursor:pointer;font-size:12.5px;font-weight:700;
  letter-spacing:.18em;background:#68e8d2;color:#04161a}
.go:hover{background:#8bf0dd}
.or{position:relative;text-align:center;font-size:9.5px;letter-spacing:.16em;color:#4e6a80;margin:16px 0}
.or:before,.or:after{content:"";position:absolute;top:50%;width:44%;height:1px;background:rgba(120,170,205,.14)}
.or:before{left:0}.or:after{right:0}
.guest{width:100%;padding:12px;border-radius:8px;background:none;border:1px solid rgba(130,175,215,.2);
  color:#93b3c8;font-size:11.5px;cursor:pointer;letter-spacing:.06em}
.guest:hover{border-color:rgba(104,232,210,.5);color:#b8f0e6}
.foot{font-size:9.5px;color:#4e6a80;margin-top:22px;line-height:1.8;letter-spacing:.03em}
.foot b{color:#68e8d2;font-weight:400}
.side{position:relative;z-index:5;display:flex;flex-direction:column;justify-content:space-between;padding:34px 56px 40px;text-align:right}
.side .top{font-size:9.5px;letter-spacing:.26em;color:#5d7b93}
.side .bot{font-size:9.5px;letter-spacing:.2em;color:#5d7b93;display:flex;justify-content:flex-end;gap:30px}
.legend{position:absolute;left:660px;bottom:44px;z-index:6;font-family:Consolas,monospace}
.legend div{display:flex;align-items:center;gap:9px;font-size:9px;letter-spacing:.1em;color:#6d8ba4;margin-top:9px}
.legend i{width:5px;height:5px;border-radius:50%;display:block}
.legend .t{font-size:9px;letter-spacing:.22em;color:#8fb0c8;margin-bottom:13px}
'''

# 节点按真实经纬度摆放（右半区 620—1400 / 80—760），连线取地缘邻接
_PTS = {'USA': (-98, 39), 'CAN': (-106, 56), 'MEX': (-102, 23), 'BRA': (-52, -12), 'ARG': (-64, -35),
        'GBR': (-2, 54), 'DEU': (10, 51), 'RUS': (60, 58), 'EGY': (31, 27), 'NGA': (8, 9),
        'ZAF': (24, -29), 'IND': (78, 22), 'CHN': (105, 35), 'JPN': (138, 36), 'IDN': (113, -2),
        'AUS': (134, -25)}
_EDGES = [('USA', 'CAN'), ('USA', 'MEX'), ('MEX', 'BRA'), ('BRA', 'ARG'), ('GBR', 'DEU'),
          ('DEU', 'RUS'), ('DEU', 'EGY'), ('RUS', 'CHN'), ('CHN', 'JPN'), ('CHN', 'IND'),
          ('IND', 'IDN'), ('IDN', 'AUS'), ('NGA', 'ZAF'), ('EGY', 'NGA'), ('ARG', 'ZAF')]
_LABELS = {'CHN': ('19.5T', 16, -14), 'USA': ('28.7T', -14, -20), 'DEU': ('4.7T', 14, 18),
           'BRA': ('2.1T', 14, 18), 'IND': ('3.9T', -52, 16), 'JPN': ('4.2T', 16, 16)}


def _xy(k):
    lon, lat = _PTS[k]
    x = 620 + (lon + 180) / 360.0 * 780
    y = 80 + (75 - lat) / 130.0 * 660
    return x, y


def _map_svg():
    lines, dots, txt = [], [], []
    for a_, b_ in _EDGES:
        x1, y1 = _xy(a_); x2, y2 = _xy(b_)
        lines.append('<line x1="%.0f" y1="%.0f" x2="%.0f" y2="%.0f"/>' % (x1, y1, x2, y2))
    for k in _PTS:
        x, y = _xy(k)
        big = k in _LABELS
        dots.append('<circle cx="%.0f" cy="%.0f" r="%.1f" fill="#8fe6ff" stroke="none" opacity="%.2f"/>'
                    % (x, y, 3.2 if big else 2.0, .9 if big else .5))
        if k in _LABELS:
            val, dx, dy = _LABELS[k]
            txt.append('<text x="%.0f" y="%.0f" font-family="Consolas,monospace" font-size="8.5" '
                       'letter-spacing="1.1" fill="#7fa6c2">%s · %s</text>' % (x + dx, y + dy, k, val))
    return ('<svg class="map" width="1440" height="900" viewBox="0 0 1440 900">'
            '<circle cx="1010" cy="420" r="330" fill="none" stroke="rgba(120,190,230,.07)" stroke-dasharray="3 7"/>'
            '<circle cx="1010" cy="420" r="438" fill="none" stroke="rgba(120,190,230,.05)" stroke-dasharray="2 9"/>'
            '<g stroke="#56a0c8" stroke-width="0.8" opacity="0.38">%s</g>'
            '<g>%s</g><g opacity="0.9">%s</g></svg>') % (''.join(lines), ''.join(dots), ''.join(txt))

L_BODY = '''<div class="vig"></div>__MAP__
<div class="panel">
  <div class="logo"><b>ORBIS</b><i>EARTH DATA ATLAS</i></div>
  <h2>欢迎回来</h2>
  <p class="cs">登录以使用完整账户功能 · 游客可免费浏览地球</p>
  __TABS__
  __FIELDS__
  <p class="foot"><b>管理员入口 →</b> 此处请用邮箱登录，不是管理员账号<br>数据源：世界银行 WDI · Frankfurter（111 家央行）</p>
</div>
<div class="side">
  <div class="top">GLOBAL ECONOMY · 217 COUNTRIES · 1990—2025</div>
  <div class="bot"><span>用数据重新认识这颗星球</span></div>
</div>
<div class="legend">
  <div class="t">NODE / ECONOMY SCALE</div>
  <div><i style="background:#8fe6ff"></i>GDP &gt; 4T</div>
  <div><i style="background:#5e9cbd"></i>GDP &lt; 4T</div>
</div>'''
L_BODY = L_BODY.replace('__MAP__', _map_svg()).replace('__TABS__', TABS).replace('__FIELDS__', FIELDS)


# ======================================================= M 任务控制台
M_CSS = '''
body{background:#04080c;position:relative;overflow:hidden;display:flex;flex-direction:column;
  font-family:Consolas,"SF Mono",monospace}
.grid{position:absolute;inset:0;background-image:linear-gradient(rgba(70,190,210,.045) 1px,transparent 1px),
  linear-gradient(90deg,rgba(70,190,210,.045) 1px,transparent 1px);background-size:38px 38px}
.rail{position:relative;z-index:6;display:flex;align-items:center;gap:26px;padding:0 34px;height:44px;
  border-bottom:1px solid rgba(90,200,220,.14);background:rgba(6,14,20,.7);font-size:9.5px;letter-spacing:.16em;color:#5f8b9c}
.rail b{color:#cdeef6;font-weight:600;letter-spacing:.3em}
.rail .sep{width:1px;height:12px;background:rgba(90,200,220,.18)}
.rail .ok{color:#5ee6a8;display:flex;align-items:center;gap:6px}
.rail .ok i{width:5px;height:5px;border-radius:50%;background:#5ee6a8;box-shadow:0 0 8px #5ee6a8}
.rail .right{margin-left:auto;display:flex;gap:22px}
.body{flex:1;position:relative;z-index:6;display:grid;grid-template-columns:1fr 560px;align-items:center}
.tel{padding:0 34px 0 56px}
.tel .cap{font-size:9.5px;letter-spacing:.2em;color:#f0a868;margin-bottom:20px;font-family:Consolas,"SF Mono",monospace}
.tel h1{font-size:30px;line-height:1.45;color:#e8f6fb;font-weight:600;letter-spacing:.02em;font-family:"Segoe UI","Microsoft YaHei",sans-serif}
.tel p{margin-top:14px;font-size:11.5px;line-height:1.9;color:#7a9aab;max-width:330px;font-family:"Segoe UI","Microsoft YaHei",sans-serif}
.rows{margin-top:34px;width:360px}
.rows .r{display:grid;grid-template-columns:56px 1fr 54px;gap:12px;align-items:center;padding:9px 0;
  border-top:1px solid rgba(90,200,220,.12);font-size:9.5px;color:#5f8b9c;letter-spacing:.1em}
.rows .r:last-child{border-bottom:1px solid rgba(90,200,220,.12)}
.rows .b{height:2px;background:rgba(90,200,220,.12);position:relative}
.rows .b i{position:absolute;left:0;top:0;bottom:0;background:linear-gradient(90deg,#3aa8c8,#5ee6a8)}
.rows .v{color:#a9d4e0;text-align:right}
.panelwrap{padding-right:56px;position:relative}
.bgholo{position:absolute;left:430px;top:40px;z-index:3;opacity:.55;pointer-events:none;
  -webkit-mask-image:radial-gradient(circle at 50% 45%,#000 40%,transparent 74%);
  mask-image:radial-gradient(circle at 50% 45%,#000 40%,transparent 74%)}
.card{position:relative;background:rgba(5,13,19,.94);border:1px solid rgba(90,200,220,.24);padding:30px 28px 22px;
  font-family:"Segoe UI","Microsoft YaHei",sans-serif}
.card .hdr{font-family:Consolas,"SF Mono",monospace}
.card:before,.card:after{content:"";position:absolute;width:14px;height:14px;border:1.5px solid #5ee6a8}
.card:before{left:-1px;top:-1px;border-right:0;border-bottom:0}
.card:after{right:-1px;bottom:-1px;border-left:0;border-top:0}
.card .hdr{display:flex;justify-content:space-between;align-items:baseline;font-size:9px;letter-spacing:.2em;color:#4f7688;margin-bottom:20px}
h2{font-size:17px;color:#dff4fa;letter-spacing:.06em;font-weight:600}
.cs{font-size:11px;letter-spacing:.02em;color:#6d92a4;margin:9px 0 22px}
.tabs{display:flex;gap:2px;margin-bottom:20px;border:1px solid rgba(90,200,220,.2)}
.tabs button{flex:1;padding:8px;background:none;border:0;color:#557b8d;font-size:10px;letter-spacing:.14em;cursor:pointer;font-family:inherit}
.tabs button.on{background:rgba(94,230,168,.12);color:#5ee6a8}
.fld{display:block;margin-bottom:16px}
.fld span{display:block;font-size:10px;letter-spacing:.08em;color:#6d92a4;margin-bottom:7px}
.fld input{width:100%;padding:10px 11px;background:rgba(90,200,220,.05);border:1px solid rgba(90,200,220,.22);
  font-size:12px;color:#dff4fa;outline:none;font-family:inherit;letter-spacing:.04em}
.fld input:focus{border-color:#5ee6a8;box-shadow:0 0 0 2px rgba(94,230,168,.1)}
.row{display:flex;justify-content:space-between;align-items:center;font-size:9px;letter-spacing:.1em;color:#557b8d;margin:2px 0 18px}
.chk{display:flex;align-items:center;gap:7px;cursor:pointer}
.chk input{accent-color:#5ee6a8;width:11px;height:11px}
.lnk{color:#5ee6a8;text-decoration:none;cursor:pointer}
.go{width:100%;padding:12px;border:0;cursor:pointer;font-size:11px;letter-spacing:.2em;font-weight:700;
  background:#5ee6a8;color:#04140f;font-family:inherit}
.go:hover{background:#8bf5c6}
.or{position:relative;text-align:center;font-size:8.5px;letter-spacing:.2em;color:#3f5f70;margin:15px 0}
.or:before,.or:after{content:"";position:absolute;top:50%;width:42%;height:1px;background:rgba(90,200,220,.14)}
.or:before{left:0}.or:after{right:0}
.guest{width:100%;padding:11px;background:none;border:1px solid rgba(90,200,220,.22);color:#7fa8ba;
  font-size:10px;letter-spacing:.14em;cursor:pointer;font-family:inherit}
.guest:hover{border-color:#5ee6a8;color:#5ee6a8}
.foot{font-size:9px;letter-spacing:.02em;color:#4f7284;margin-top:16px;line-height:1.9}
.foot b{color:#f0a868;font-weight:400}
.bottom{position:relative;z-index:6;height:38px;border-top:1px solid rgba(90,200,220,.12);display:flex;
  align-items:center;gap:24px;padding:0 34px;font-size:8.5px;letter-spacing:.18em;color:#3f5f70;background:rgba(6,14,20,.7)}
.bottom .r{margin-left:auto;display:flex;gap:22px}
.bottom b{color:#7fa8ba;font-weight:400}
'''

M_BODY = '''<div class="grid"></div>
<div class="bgholo">__HOLO__</div>
<div class="rail"><b>ORBIS</b><span class="sep"></span>
  <span class="ok"><i></i>SYSTEM ONLINE</span><span class="sep"></span>
  <span>FEED / WDI · FRANKFURTER</span>
  <div class="right"><span>AUTH / v2.4</span><span>2026-11-17 14:23</span><span id="lat">LATENCY 42ms</span></div>
</div>
<div class="body">
  <div class="tel">
    <div class="cap">// 用数据重新认识这颗星球</div>
    <h1>用数据重新认识这颗星球<br>看数据如何改变一个国家</h1>
    <p>217 个国家的 GDP、人口、寿命与汇率，全部落在同一颗球面上，每 6 小时与世界银行同步。</p>
    <div class="rows">
      <div class="r"><span>GDP</span><span class="b"><i style="width:92%"></i></span><span class="v">105.4T</span></div>
      <div class="r"><span>POP</span><span class="b"><i style="width:78%"></i></span><span class="v">8.09B</span></div>
      <div class="r"><span>LIFE</span><span class="b"><i style="width:64%"></i></span><span class="v">73.4Y</span></div>
      <div class="r"><span>FX</span><span class="b"><i style="width:100%"></i></span><span class="v">111 CB</span></div>
    </div>
  </div>
  <div class="panelwrap">
    <div class="card">
      <div class="hdr"><span>SEC.01 / SIGN IN</span><span>SECURE</span></div>
      <h2>欢迎回来</h2>
      <p class="cs">登录以使用完整账户功能 · 游客可免费浏览地球</p>
      __TABS__
      __FIELDS__
      <p class="foot"><b>管理员入口 →</b> 此处请用邮箱登录，不是管理员账号</p>
    </div>
  </div>
</div>
<div class="bottom"><span>DATA SOURCE / WORLD BANK WDI · FRANKFURTER</span>
  <div class="r"><span>217 COUNTRIES</span><span>1990—2025</span><span><b>SESSION</b> IDLE</span></div>
</div>'''
M_BODY = M_BODY.replace('__HOLO__', globe(900, 'rgba(46,140,180,.5)', 'rgba(18,66,92,.45)', 'rgba(4,14,20,.4)', 'rgba(110,220,235,.5)', .5, 20, 7, 9, shade=False))
M_BODY = M_BODY.replace('__TABS__', TABS).replace('__FIELDS__', FIELDS)


# ======================================================= N 蓝金夜航
N_CSS = '''
body{background:#060b14;position:relative;overflow:hidden;display:grid;place-items:center}
.bg{position:absolute;inset:0;background:
  radial-gradient(ellipse 60% 50% at 14% 88%,rgba(214,158,84,.16),transparent 62%),
  radial-gradient(ellipse 70% 60% at 78% 12%,rgba(52,104,168,.2),transparent 66%),
  linear-gradient(165deg,#0a1220 0%,#070d18 55%,#050a12 100%)}
.eng{position:absolute;right:-260px;top:-160px;opacity:.5}
.eng2{position:absolute;left:-320px;bottom:-380px;opacity:.32}
.rule{position:absolute;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,rgba(214,175,116,.28),transparent)}
.r1{top:96px}.r2{bottom:62px}
.wrap{position:relative;z-index:6;width:590px;text-align:center}
.mark{display:inline-flex;align-items:center;gap:12px;font-size:10px;letter-spacing:.34em;color:#c9a06a;margin-bottom:22px}
.mark em{width:26px;height:1px;background:rgba(214,175,116,.5);display:block}
h1{font-family:Georgia,"Songti SC","Times New Roman",serif;font-size:34px;font-weight:400;
  letter-spacing:.22em;color:#f4efe4;margin-left:.24em;white-space:nowrap}
.sub{font-family:Georgia,"Songti SC",serif;margin-top:14px;font-size:15px;letter-spacing:.14em;color:#c3b8a4}
.tag{margin-top:10px;font-size:10.5px;letter-spacing:.16em;color:#6f7f92}
.dia{display:flex;align-items:center;gap:12px;justify-content:center;margin:26px 0 24px}
.dia i{width:4px;height:4px;background:rgba(214,175,116,.7);display:block;transform:rotate(45deg)}
.dia span{height:1px;width:120px;background:linear-gradient(90deg,transparent,rgba(214,175,116,.32),transparent)}
h2{font-family:Georgia,"Songti SC",serif;font-size:23px;font-weight:400;color:#f2ebdd;letter-spacing:.06em}
.cs{font-size:11px;color:#7c8b9c;margin:10px 0 26px;letter-spacing:.06em}
.tabs{display:flex;justify-content:center;gap:0;margin-bottom:26px}
.tabs button{background:none;border:0;cursor:pointer;padding:0 22px;font-size:11.5px;letter-spacing:.18em;color:#6f7f92;
  position:relative;font-family:inherit}
.tabs button+button{border-left:1px solid rgba(214,175,116,.2)}
.tabs button.on{color:#e8d5b0}
.fld{display:block;text-align:left;margin-bottom:20px}
.fld span{display:block;font-size:9.5px;letter-spacing:.22em;color:#7c8b9c;margin-bottom:9px}
.fld input{width:100%;background:none;border:0;border-bottom:1px solid rgba(214,175,116,.26);
  padding:5px 0 11px;font-size:13.5px;color:#f4efe4;outline:none;letter-spacing:.04em}
.fld input:focus{border-color:#d6af74}
.row{display:flex;justify-content:space-between;align-items:center;font-size:10.5px;color:#7c8b9c;margin:4px 0 26px}
.chk{display:flex;align-items:center;gap:7px;cursor:pointer}
.chk input{accent-color:#d6af74;width:12px;height:12px}
.lnk{color:#a08b6d;text-decoration:none;cursor:pointer;letter-spacing:.06em}
.go{width:100%;padding:15px;border:0;cursor:pointer;font-size:12px;letter-spacing:.26em;font-weight:600;
  background:linear-gradient(135deg,#e2bd82,#c99a55);color:#241a0c;border-radius:2px;
  box-shadow:0 12px 34px rgba(201,154,85,.22)}
.go:hover{background:linear-gradient(135deg,#efcd96,#d6a862)}
.or{position:relative;text-align:center;font-size:9.5px;letter-spacing:.22em;color:#5f7085;margin:18px 0}
.or:before,.or:after{content:"";position:absolute;top:50%;width:44%;height:1px;background:rgba(214,175,116,.16)}
.or:before{left:0}.or:after{right:0}
.guest{width:100%;padding:13px;background:none;border:1px solid rgba(214,175,116,.24);color:#c3b8a4;
  font-size:11px;letter-spacing:.14em;cursor:pointer;border-radius:2px}
.guest:hover{border-color:rgba(214,175,116,.6);color:#e8d5b0}
.foot{font-size:9px;color:#5f7085;margin-top:24px;line-height:1.9;letter-spacing:.06em}
.foot b{color:#c9a06a;font-weight:400}
.edge{position:absolute;z-index:6;font-size:9px;letter-spacing:.24em;color:#67788d}
.e1{left:56px;top:52px}.e2{right:56px;top:52px}.e3{left:56px;bottom:46px}.e4{right:56px;bottom:46px}
'''

N_BODY = '''<div class="bg"></div>
<div class="eng">__G1__</div><div class="eng2">__G2__</div>
<div class="rule r1"></div><div class="rule r2"></div>
<div class="edge e1">ORBIS / ATLAS</div><div class="edge e2">用数据重新认识这颗星球</div>
<div class="edge e3">WORLD BANK WDI · FRANKFURTER</div><div class="edge e4">EST. 2024</div>
<div class="wrap">
  <div class="mark"><em></em>ORBIS<em></em></div>
  <h1>用数据重新认识这颗星球</h1>
  <p class="sub">217 个国家 · 25 年 · 4 项指标</p>
  <p class="tag">DATA ATLAS OF THE WORLD</p>
  <div class="dia"><span></span><i></i><span></span></div>
  <h2>欢迎回来</h2>
  <p class="cs">登录以使用完整账户功能 · 游客可免费浏览地球</p>
  __TABS__
  __FIELDS__
  <p class="foot"><b>管理员入口 →</b> 此处请用邮箱登录，不是管理员账号</p>
</div>'''
N_BODY = N_BODY.replace('__TABS__', TABS).replace('__FIELDS__', FIELDS)
N_BODY = N_BODY.replace('__G1__', globe(760, 'rgba(226,196,150,.22)', 'rgba(150,120,80,.12)', 'rgba(20,20,26,.1)', 'rgba(226,196,150,.55)', .55, 24, 7, 9, shade=False))
N_BODY = N_BODY.replace('__G2__', globe(820, 'rgba(150,190,230,.16)', 'rgba(90,130,180,.08)', 'rgba(10,16,26,.05)', 'rgba(160,190,220,.4)', .4, 20, 6, 8, shade=False))


# =======================================================
FILES = [('K_极光深空', K_CSS, K_BODY), ('L_星图连线', L_CSS, L_BODY),
         ('M_任务控制台', M_CSS, M_BODY), ('N_蓝金夜航', N_CSS, N_BODY)]
for name, css, body in FILES:
    io.open(os.path.join(OUT, name + '.html'), 'w', encoding='utf-8').write(doc(name, css, body))
    print('wrote', name)
