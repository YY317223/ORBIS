# -*- coding: utf-8 -*-
"""ORBIS 登录页 —— 第四组：结构差异最大的五版，全部采用新副标题"""
import io, os, sys, math

sys.path.insert(0, 'C:/0_workspace/项目二2/_login_styles2')
from gen2 import globe, doc

OUT = 'C:/0_workspace/项目二2/_login_styles4'
os.makedirs(OUT, exist_ok=True)

TABS = '<div class="tabs"><button class="on">登录</button><button>注册</button></div>'
FIELDS = '''<label class="fld"><span>邮箱</span><input type="email" value="2106812162@qq.com"></label>
    <label class="fld"><span>密码</span><input type="password" value="········"></label>
    <div class="row"><label class="chk"><input type="checkbox" checked><span>保持登录 30 天</span></label><a class="lnk">忘记密码</a></div>
    <button class="go">登录并进入</button>
    <div class="or">或</div>
    <button class="guest">以访客身份浏览</button>'''


def stars(n=150, seed=1, maxy=860):
    out = []
    for i in range(n):
        x = (i * 467 + seed * 71) % 1440
        y = (i * 233 + seed * 37) % maxy
        out.append('<circle cx="%d" cy="%d" r="%.1f" opacity="%.2f"/>' %
                   (x, y, .5 + (i % 3) * .35, .14 + (i % 5) * .1))
    return ''.join(out)


def dot_globe(cx, cy, R, color='#5ce08c', step=7, tilt=20):
    """点阵球：正交投影 + 背面剔除，用于终端风格"""
    t = math.radians(tilt); ct, st = math.cos(t), math.sin(t)
    pts = []
    lat = -84
    while lat <= 84:
        lon = 0
        while lon < 360:
            la, lo = math.radians(lat), math.radians(lon)
            x = math.cos(la) * math.sin(lo)
            y = math.sin(la)
            z = math.cos(la) * math.cos(lo)
            y2 = y * ct - z * st
            z2 = y * st + z * ct
            if z2 > 0:
                pts.append('<rect x="%.1f" y="%.1f" width="2.2" height="2.2" fill="%s" opacity="%.2f"/>' %
                           (cx + R * x, cy - R * y2, color, .38 + .62 * z2))
            lon += step
        lat += step
    sz = 2 * cx
    return '<svg width="%d" height="%d" viewBox="0 0 %d %d"><circle cx="%d" cy="%d" r="%d" fill="none" stroke="%s" stroke-opacity=".22"/>%s</svg>' % (sz, sz, sz, sz, cx, cy, R, color, ''.join(pts))


# ========================================================== O 玻璃穹顶
O_CSS = '''
body{background:radial-gradient(ellipse 90% 85% at 74% 40%,#1d2d68 0%,#101945 42%,#060a1c 100%);position:relative;overflow:hidden}
.grid{position:absolute;inset:0;background-image:linear-gradient(rgba(160,190,255,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(160,190,255,.035) 1px,transparent 1px);background-size:62px 62px}
.orb{position:absolute;right:-90px;top:56px;width:880px;height:880px;border-radius:50%;overflow:hidden;
  background:linear-gradient(150deg,rgba(160,195,255,.18),rgba(60,95,200,.06) 45%,rgba(8,16,48,.52));
  border:1px solid rgba(180,212,255,.24);
  box-shadow:inset -60px -50px 140px rgba(3,6,24,.62),inset 28px 26px 90px rgba(190,220,255,.12),0 0 150px rgba(70,120,255,.16)}
.orb .wire{position:absolute;left:46px;top:46px;opacity:.52}
.pill{position:absolute;z-index:4;padding:9px 15px;border-radius:999px;background:rgba(12,22,58,.66);
  border:1px solid rgba(170,205,255,.26);backdrop-filter:blur(12px);font-size:11px;color:#d6e5ff;
  box-shadow:0 14px 32px rgba(0,0,0,.35);letter-spacing:.02em}
.pill b{color:#9fd8ff;font-weight:600;margin-left:10px}
.p1{right:248px;top:142px}.p2{right:66px;top:428px}.p3{right:352px;bottom:146px}
.left{position:relative;z-index:6;padding-left:112px;height:100%;display:flex;flex-direction:column;justify-content:center;width:660px}
.logo{display:flex;align-items:center;gap:12px;margin-bottom:20px}
.logo b{font-size:14px;letter-spacing:.36em;color:#eef5ff;font-weight:600}
.logo i{font-style:normal;font-size:9px;letter-spacing:.18em;color:#8fa8d4;padding-left:12px;border-left:1px solid rgba(160,200,255,.24)}
h1{font-size:37px;line-height:1.34;font-weight:300;color:#f4f8ff;letter-spacing:.02em;margin-bottom:12px}
h1 b{font-weight:600}
.lead{font-size:12.5px;line-height:1.95;color:#a3b7dc;max-width:430px;margin-bottom:28px}
.card{width:416px;padding:28px 30px 24px;border-radius:16px;background:rgba(9,16,42,.74);
  border:1px solid rgba(160,200,255,.2);backdrop-filter:blur(24px);box-shadow:0 36px 90px rgba(0,0,0,.45)}
h2{font-size:20px;font-weight:600;color:#f0f6ff}
.cs{font-size:11px;color:#8ea6ce;margin:7px 0 20px}
.tabs{display:flex;gap:4px;padding:4px;border-radius:9px;background:rgba(255,255,255,.05);margin-bottom:20px;border:1px solid rgba(150,190,255,.12)}
.tabs button{flex:1;padding:8px;border:0;border-radius:6px;background:none;color:#8ea6ce;font-size:12px;cursor:pointer}
.tabs button.on{background:linear-gradient(135deg,rgba(120,165,255,.28),rgba(110,220,255,.16));color:#dceeff;font-weight:600}
.fld{display:block;margin-bottom:14px}
.fld span{display:block;font-size:10.5px;color:#8ea6ce;margin-bottom:7px}
.fld input{width:100%;padding:11px 13px;border-radius:8px;background:rgba(255,255,255,.05);border:1px solid rgba(150,190,255,.18);font-size:13px;color:#eef5ff;outline:none}
.fld input:focus{border-color:rgba(140,200,255,.65)}
.row{display:flex;justify-content:space-between;align-items:center;font-size:11px;color:#8ea6ce;margin:2px 0 17px}
.chk{display:flex;align-items:center;gap:7px;cursor:pointer}.chk input{accent-color:#7fb4ff;width:12px;height:12px}
.lnk{color:#8ea6ce;text-decoration:none;cursor:pointer}
.go{width:100%;padding:12px;border:0;border-radius:8px;cursor:pointer;font-size:13px;font-weight:700;background:linear-gradient(135deg,#9ec4ff,#6ea8ff);color:#081634}
.or{position:relative;text-align:center;font-size:10px;color:#6d85ad;margin:14px 0}
.or:before,.or:after{content:"";position:absolute;top:50%;width:44%;height:1px;background:rgba(150,190,255,.14)}
.or:before{left:0}.or:after{right:0}
.guest{width:100%;padding:10px;border-radius:8px;background:none;border:1px solid rgba(150,190,255,.24);color:#b9ccef;font-size:11.5px;cursor:pointer}
.foot{font-size:9.5px;color:#7388af;margin-top:16px;line-height:1.7}
'''
O_BODY = '''<div class="grid"></div>
<div class="orb"><div class="wire">__WIRE__</div></div>
<div class="pill p1">CHN · GDP <b>19.5T</b></div>
<div class="pill p2">IND · 人口 <b>1.43B</b></div>
<div class="pill p3">DEU · 寿命 <b>81.3y</b></div>
<div class="left">
  <div class="logo"><b>ORBIS</b><i>EARTH DATA ATLAS</i></div>
  <h1>用数据重新认识<br><b>这颗星球</b></h1>
  <p class="lead">217 个国家的 GDP、人口与寿命，落在同一颗球面上。拖动、对比、分享，看见二十五年里的变化。</p>
  <div class="card">__TABS__<h2>欢迎回来</h2><p class="cs">登录以使用完整账户功能 · 游客可免费浏览地球</p>__FIELDS__
  <p class="foot">管理员入口 → 此处请用邮箱登录，不是管理员账号<br>数据源：世界银行 WDI · Frankfurter（111 家央行）</p></div>
</div>'''
O_BODY = (O_BODY.replace('__TABS__', TABS).replace('__FIELDS__', FIELDS)
          .replace('__WIRE__', globe(788, 'rgba(150,200,255,.2)', 'rgba(90,150,240,.12)', 'rgba(20,40,100,.2)', 'rgba(175,215,255,.62)', .48, 24, 8, 10, shade=False)))

# ========================================================== P 终端登录
P_CSS = '''
body{background:#050906;color:#b9f2c9;position:relative;overflow:hidden}
.scan{position:absolute;inset:0;z-index:20;pointer-events:none;background:repeating-linear-gradient(0deg,rgba(120,255,160,.035) 0px,rgba(120,255,160,.035) 1px,transparent 1px,transparent 4px)}
.glow{position:absolute;inset:0;background:radial-gradient(ellipse 68% 74% at 68% 46%,rgba(28,130,78,.17),transparent 72%)}
.vig{position:absolute;inset:0;background:radial-gradient(ellipse 80% 76% at 50% 50%,transparent 45%,rgba(0,0,0,.66) 100%)}
.dot{position:absolute;right:28px;top:22px;opacity:.85;filter:drop-shadow(0 0 20px rgba(80,240,140,.28))}
.hud{position:absolute;right:58px;top:36px;font-family:Consolas,monospace;font-size:10px;letter-spacing:.2em;color:#4f9c6c}
.hud b{color:#7ae6a0;font-weight:400}
.main{position:relative;z-index:8;padding:80px 0 0 104px;width:700px}
.prompt{font-family:Consolas,monospace;font-size:11px;letter-spacing:.16em;color:#54b87a}
h1{font-size:37px;line-height:1.42;font-weight:400;color:#d8ffe6;letter-spacing:.04em;margin:18px 0 12px}
h1 span{color:#6ee39a}
.lead{font-size:12.5px;color:#82b897;line-height:1.95;max-width:470px}
.meta{font-family:Consolas,monospace;font-size:10px;color:#4c9267;letter-spacing:.12em;margin-top:22px;line-height:1.9}
.term{margin-top:26px;width:516px;border:1px solid rgba(90,220,140,.3);background:rgba(5,18,10,.76);padding:22px 26px 24px;
  box-shadow:0 0 60px rgba(40,160,90,.08),inset 0 0 40px rgba(30,120,70,.05)}
.tabs{display:flex;gap:18px;margin-bottom:16px;border-bottom:1px solid rgba(90,220,140,.22)}
.tabs button{background:none;border:0;cursor:pointer;padding:0 0 8px;font-size:11.5px;color:#4f9c6c;letter-spacing:.08em;position:relative}
.tabs button.on{color:#8bf0ad;font-weight:600}
.tabs button.on:after{content:"";position:absolute;left:0;right:0;bottom:-1px;height:1px;background:#5ce08c}
.line{font-family:Consolas,monospace;font-size:10.5px;color:#52a874;letter-spacing:.14em;margin-bottom:16px}
.line b{color:#8bf0ad;font-weight:400}
.fld{display:flex;align-items:center;border-bottom:1px dashed rgba(90,220,140,.28);padding:7px 0;margin-bottom:15px}
.fld i{font-style:normal;font-family:Consolas,monospace;color:#63d98d;margin-right:12px;font-size:13px}
.fld span{font-size:11px;color:#79b991;width:58px}
.fld input{flex:1;background:none;border:0;outline:none;color:#d9ffe7;font-size:13px}
.fld input::placeholder{color:#3f7655}
.row{display:flex;justify-content:space-between;align-items:center;font-size:11px;color:#6fae87;margin:1px 0 20px}
.chk{display:flex;align-items:center;gap:7px;cursor:pointer}.chk input{accent-color:#5ce08c;width:12px;height:12px}
.lnk{color:#6fae87;text-decoration:none;cursor:pointer}
.go{width:100%;padding:12px;border:1px solid #5ce08c;background:rgba(92,224,140,.16);color:#b9ffd1;font-size:13px;font-weight:600;cursor:pointer;letter-spacing:.1em}
.go:hover{background:rgba(92,224,140,.28)}
.or{text-align:center;font-family:Consolas,monospace;font-size:10px;color:#43785a;margin:14px 0;letter-spacing:.2em}
.guest{width:100%;padding:10px;border:1px dashed rgba(90,220,140,.28);background:none;color:#8fceaa;font-size:11.5px;cursor:pointer}
.foot{font-family:Consolas,monospace;font-size:9px;color:#3f7655;margin-top:16px;letter-spacing:.08em}
.cursor{display:inline-block;width:7px;height:13px;background:#6ee39a;vertical-align:-2px;animation:bl 1s steps(1) infinite}
@keyframes bl{50%{opacity:0}}
'''
P_BODY = '''<div class="glow"></div><div class="vig"></div>
<div class="dot">__DOTS__</div>
<div class="hud">SYS ONLINE · <b>LATENCY 42ms</b> · WDI / FRANKFURTER</div>
<div class="main">
  <div class="prompt">&gt; ORBIS --mode=atlas --year=1990..2025</div>
  <h1>用数据重新认识<span>这颗星球</span></h1>
  <p class="lead">217 个国家，4 项指标，25 年跨度。把世界装进一颗可以拖动的球里。</p>
  <p class="meta">DATASET 217 / 25Y / WDI 4.2 · SYNC 6H<br>STATUS: READY &nbsp;·&nbsp; VIEW: GLOBE</p>
  <div class="term">
    <div class="line">── AUTHENTICATION <b>REQUIRED</b> ────────────────</div>
    __TABS__
    <label class="fld"><i>&gt;</i><span>邮箱</span><input type="email" value="2106812162@qq.com"></label>
    <label class="fld"><i>&gt;</i><span>密码</span><input type="password" value="········"></label>
    <div class="row"><label class="chk"><input type="checkbox" checked><span>保持登录 30 天</span></label><a class="lnk">忘记密码</a></div>
    <button class="go">登录并进入 <span class="cursor"></span></button>
    <div class="or">────────── 或 ──────────</div>
    <button class="guest">以访客身份浏览（只读）</button>
    <div class="foot">ADMIN / USE EMAIL ACCOUNT · WORLD BANK WDI · FRANKFURTER</div>
  </div>
</div><div class="scan"></div>'''
P_BODY = P_BODY.replace('__TABS__', TABS).replace('__DOTS__', dot_globe(420, 420, 330, '#5ce08c', 7, 12))

# ========================================================== Q 冷白数据台
Q_CSS = '''
body{background:#e9eef4;color:#16233b;position:relative;overflow:hidden}
.grid{position:absolute;inset:0;background-image:linear-gradient(rgba(30,60,110,.055) 1px,transparent 1px),linear-gradient(90deg,rgba(30,60,110,.055) 1px,transparent 1px);background-size:48px 48px}
.hd{position:absolute;left:72px;right:88px;top:34px;display:flex;justify-content:space-between;align-items:center;font-size:10px;letter-spacing:.18em;color:#6b7c98}
.hd b{font-size:13px;letter-spacing:.26em;color:#142744}
.hd em{font-style:normal;color:#5070a8}
.left{position:relative;z-index:4;width:800px;padding:0 0 0 72px;margin-top:126px}
h1{font-size:43px;line-height:1.3;font-weight:600;color:#12244a;letter-spacing:-.01em;max-width:660px}
h1 em{font-style:normal;color:#2f6bff}
.lead{margin-top:18px;font-size:12.5px;line-height:1.95;color:#5a6d8d;max-width:560px}
.table{margin-top:34px;width:614px;background:#fff;border:1px solid #d6dfec;border-radius:10px;box-shadow:0 18px 42px rgba(30,55,100,.08);overflow:hidden}
.tr{display:grid;grid-template-columns:1.1fr .9fr .7fr 1.3fr;align-items:center;padding:11px 18px;border-bottom:1px solid #e9eef6;font-size:11px;color:#283c5e}
.tr:last-child{border-bottom:0}
.th{font-size:9px;letter-spacing:.16em;color:#8b9ab1;background:#f6f8fc;padding-top:9px;padding-bottom:9px}
.tr b{font-weight:600}
.up{color:#d13b2f}.down{color:#1a9b68}
.bar{display:block;width:100%;height:5px;background:#e8eef7;border-radius:3px;overflow:hidden}
.bar i{display:block;height:100%;background:#2f6bff;border-radius:3px}
.src{font-size:9.5px;color:#8b9ab1;margin-top:14px;letter-spacing:.04em}
.trend{margin-top:24px;width:614px;background:#fff;border:1px solid #d6dfec;border-radius:10px;padding:17px 20px 12px;box-shadow:0 18px 42px rgba(30,55,100,.07)}
.trend .tt{font-size:9px;letter-spacing:.16em;color:#8b9ab1;margin-bottom:10px}
.card{position:absolute;right:88px;top:142px;z-index:6;width:430px;background:#fff;border:1px solid #d6dfec;border-radius:12px;padding:32px 34px 26px;box-shadow:0 32px 72px rgba(25,50,95,.15)}
.card h2{font-size:21px;font-weight:600;color:#142744}
.cs{font-size:11px;color:#7e8da5;margin:8px 0 22px}
.tabs{display:flex;gap:28px;border-bottom:1px solid #e3eaf3;margin-bottom:22px}
.tabs button{background:none;border:0;padding:0 0 10px;font-size:12px;color:#8b9ab1;cursor:pointer;position:relative}
.tabs button.on{color:#17306a;font-weight:600}
.tabs button.on:after{content:"";position:absolute;left:0;right:0;bottom:-1px;height:2px;background:#2f6bff}
.fld{display:block;margin-bottom:17px}
.fld span{display:block;font-size:10px;letter-spacing:.1em;color:#7e8da5;margin-bottom:7px}
.fld input{width:100%;padding:11px 12px;border:1px solid #dbe3ee;border-radius:7px;background:#fbfcfe;font-size:13px;color:#142744;outline:none}
.fld input:focus{border-color:#2f6bff;background:#fff}
.row{display:flex;justify-content:space-between;align-items:center;font-size:11px;color:#7e8da5;margin:2px 0 18px}
.chk{display:flex;align-items:center;gap:7px;cursor:pointer}.chk input{accent-color:#2f6bff;width:12px;height:12px}
.lnk{color:#5b7cc2;text-decoration:none;cursor:pointer}
.go{width:100%;padding:13px;border:0;border-radius:7px;background:#2f6bff;color:#fff;font-size:13px;font-weight:600;cursor:pointer}
.or{position:relative;text-align:center;font-size:10px;color:#9aa8bd;margin:14px 0}
.or:before,.or:after{content:"";position:absolute;top:50%;width:43%;height:1px;background:#e3eaf3}
.or:before{left:0}.or:after{right:0}
.guest{width:100%;padding:11px;border:1px solid #dbe3ee;border-radius:7px;background:#fff;color:#5b6e8e;font-size:11.5px;cursor:pointer}
.foot{font-size:9.5px;color:#9aa8bd;margin-top:18px;line-height:1.7}
'''
Q_BODY = '''<div class="grid"></div>
<div class="hd"><b>ORBIS</b><span>DATA ATLAS <em>/</em> 1990—2025 <em>/</em> 217 COUNTRIES</span></div>
<div class="left">
  <h1>用数据重新认识<br><em>这颗星球</em></h1>
  <p class="lead">不是一张静态地图。把 25 年的 GDP、人口、寿命与汇率叠在同一颗球面上，拖动就能比较。</p>
  <div class="table">
    <div class="tr th"><span>国家</span><span>GDP</span><span>同比</span><span>相对强度</span></div>
    <div class="tr"><b>美国</b><span>28.7 T</span><span class="up">+2.8%</span><span><i class="bar"><i style="width:100%"></i></i></span></div>
    <div class="tr"><b>中国</b><span>19.5 T</span><span class="up">+5.2%</span><span><i class="bar"><i style="width:68%"></i></i></span></div>
    <div class="tr"><b>德国</b><span>4.7 T</span><span class="down">−0.3%</span><span><i class="bar"><i style="width:16%"></i></i></span></div>
    <div class="tr"><b>印度</b><span>3.9 T</span><span class="up">+7.1%</span><span><i class="bar"><i style="width:14%"></i></i></span></div>
  </div>
  <p class="src">数据源：世界银行 WDI · Frankfurter（111 家央行）· 更新于 2026-11</p>
  <div class="trend"><div class="tt">25 年趋势 · 四国 GDP（归一化）</div>__TREND__</div>
</div>
<div class="card">__TABS__<h2>欢迎回来</h2><p class="cs">登录以使用完整账户功能 · 游客可免费浏览地球</p>__FIELDS__
<p class="foot">管理员入口 → 此处请用邮箱登录，不是管理员账号<br>你的对比与订阅会保存在账户中</p></div>'''
def trend_svg():
    out = ['<svg width="574" height="112" viewBox="0 0 574 112">']
    for gy in (18, 46, 74):
        out.append('<line x1="0" y1="%d" x2="574" y2="%d" stroke="#edf2f8"/>' % (gy, gy))
    for i, c in enumerate(['#2f6bff', '#d13b2f', '#8a7dff', '#1a9b68']):
        pts = []
        for j in range(26):
            x = 6 + j * 22
            y = 92 - 64 * (j / 25.0) ** (.7 + i * .14) - i * 3 + (j % 4) * 2
            pts.append('%d,%d' % (x, max(8, y)))
        out.append('<polyline fill="none" stroke="%s" stroke-width="1.7" points="%s"/>' % (c, ' '.join(pts)))
    for i, y in enumerate(['1990', '2000', '2010', '2025']):
        lx = 558 if i == 3 else i * 190
        anchor = ' text-anchor="end"' if i == 3 else ''
        out.append('<text x="%d" y="108" font-size="8" fill="#9aa8bd" font-family="Consolas,monospace"%s>%s</text>' % (lx, anchor, y))
    out.append('</svg>')
    return ''.join(out)

Q_BODY = Q_BODY.replace('__TABS__', TABS).replace('__FIELDS__', FIELDS).replace('__TREND__', trend_svg())

# ========================================================== R 蓝图轨道（登录页 + 管理员入口）
R_CSS = '''
body{background:#040a13;position:relative;overflow:hidden;color:#d7ecf7}
.grid{position:absolute;inset:0;background-image:linear-gradient(rgba(90,190,225,.055) 1px,transparent 1px),linear-gradient(90deg,rgba(90,190,225,.055) 1px,transparent 1px);background-size:40px 40px}
.schem{position:absolute;right:10px;top:70px;width:820px;height:820px;z-index:2}
.anno{position:absolute;z-index:4;font-family:Consolas,monospace;font-size:9px;letter-spacing:.12em;color:#7fb2c9;background:rgba(4,11,20,.86);padding:6px 9px;border-left:1px solid #f0a868;line-height:1.7}
.a1{right:500px;top:126px}.a2{right:74px;top:250px}.a3{right:300px;bottom:96px}
.anno b{color:#89d8f2;font-weight:400}
.line1{position:absolute;right:470px;top:170px;width:130px;height:1px;background:rgba(110,200,235,.35);transform:rotate(28deg);transform-origin:right center;z-index:3}
.rail{position:absolute;right:24px;top:118px;bottom:88px;width:1px;background:rgba(110,190,225,.2);z-index:4}
.rail i{position:absolute;left:-4px;width:9px;height:1px;background:rgba(140,215,245,.6)}
.rail span{position:absolute;left:-44px;font-family:Consolas,monospace;font-size:8.5px;color:#547e96;letter-spacing:.08em}
.left{position:relative;z-index:6;width:590px;padding:0 0 0 106px;height:100%;display:flex;flex-direction:column;justify-content:center}
.logo{display:flex;align-items:center;gap:12px;margin-bottom:30px}
.logo b{font-size:14px;letter-spacing:.34em;color:#eaf7ff;font-weight:600}
.logo i{font-style:normal;font-size:9px;letter-spacing:.16em;color:#5d8ea8;padding-left:12px;border-left:1px solid rgba(110,190,225,.24)}
.kick{font-family:Consolas,monospace;font-size:10px;letter-spacing:.24em;color:#f0a868;margin-bottom:13px}
h1{font-size:38px;line-height:1.3;font-weight:300;color:#eaf6ff;letter-spacing:.02em;margin-bottom:11px}
h1 b{font-weight:600;color:#8fe0f7}
.lead{font-size:11.5px;color:#779bb1;line-height:1.8;max-width:440px;margin-bottom:26px}
.panel{width:410px;border:1px solid rgba(110,190,225,.26);background:rgba(5,14,24,.86);padding:24px 28px 20px;position:relative}
.panel:before,.panel:after{content:"";position:absolute;width:12px;height:12px;border-color:#8fe0f7;border-style:solid}
.panel:before{left:-1px;top:-1px;border-width:1.5px 0 0 1.5px}
.panel:after{right:-1px;bottom:-1px;border-width:0 1.5px 1.5px 0}
.tabs{display:flex;gap:26px;border-bottom:1px solid rgba(110,190,225,.18);margin-bottom:22px}
.tabs button{background:none;border:0;padding:0 0 10px;cursor:pointer;font-size:12px;color:#6b93aa;position:relative;letter-spacing:.08em}
.tabs button.on{color:#eaf6ff;font-weight:600}
.tabs button.on:after{content:"";position:absolute;left:0;right:0;bottom:-1px;height:1.5px;background:#8fe0f7}
.fld{display:flex;align-items:center;gap:12px;margin-bottom:15px}
.fld em{font-style:normal;font-family:Consolas,monospace;font-size:9px;color:#f0a868;width:16px}
.fld span{font-size:10.5px;color:#6b93aa;width:36px}
.fld input{flex:1;background:rgba(110,190,225,.05);border:1px solid rgba(110,190,225,.18);padding:9px 11px;font-size:12.5px;color:#e4f4ff;outline:none}
.fld input:focus{border-color:#8fe0f7}
.row{display:flex;justify-content:space-between;align-items:center;font-size:10.5px;color:#6b93aa;margin:2px 0 18px}
.chk{display:flex;align-items:center;gap:7px;cursor:pointer}.chk input{accent-color:#8fe0f7;width:12px;height:12px}
.lnk{color:#6b93aa;text-decoration:none;cursor:pointer}
.go{width:100%;padding:12px;border:1px solid #8fe0f7;background:rgba(143,224,247,.12);color:#d6f6ff;font-size:12.5px;font-weight:600;letter-spacing:.14em;cursor:pointer}
.or{position:relative;text-align:center;font-size:9px;color:#547e96;margin:12px 0}
.or:before,.or:after{content:"";position:absolute;top:50%;width:43%;height:1px;background:rgba(110,190,225,.15)}
.or:before{left:0}.or:after{right:0}
.guest{display:block;width:100%;padding:10px;border:1px solid rgba(110,190,225,.2);background:none;color:#86aec4;font-size:11.5px;cursor:pointer;text-align:center;text-decoration:none}
.admin{display:flex;align-items:center;gap:12px;margin-top:15px;padding:10px 12px;text-decoration:none;
  border:1px solid rgba(240,168,104,.36);border-left:2px solid #f0a868;background:rgba(240,168,104,.07);cursor:pointer}
.admin:hover{background:rgba(240,168,104,.13)}
.admin .ico{flex:0 0 18px;display:flex}
.admin .t{flex:1;min-width:0}
.admin b{display:block;font-size:11.5px;color:#f5c48f;font-weight:600;letter-spacing:.08em}
.admin small{display:block;margin-top:3px;font-family:Consolas,monospace;font-size:8.5px;letter-spacing:.12em;color:#a1866a}
.admin em{font-style:normal;color:#f0a868;font-size:15px;line-height:1}
.note{margin-top:9px;font-size:9.5px;color:#5d7e96;line-height:1.7}
.foot{font-family:Consolas,monospace;font-size:9px;color:#4d758c;margin-top:14px;line-height:1.7}
.railbar{position:absolute;left:106px;bottom:32px;right:62px;height:1px;background:rgba(110,190,225,.18);z-index:5}
.railbar span{position:absolute;top:-5px;width:1px;height:11px;background:rgba(140,215,245,.5)}
.railbar em{position:absolute;top:10px;font-family:Consolas,monospace;font-size:8.5px;color:#4d758c;font-style:normal}
'''
R_BODY = '''<div class="grid"></div>
<div class="schem">
  <svg width="820" height="820" viewBox="0 0 820 820">
    <circle cx="410" cy="410" r="300" fill="none" stroke="rgba(120,205,240,.16)" stroke-dasharray="2 8"/>
    <circle cx="410" cy="410" r="345" fill="none" stroke="rgba(120,205,240,.1)" stroke-dasharray="1 11"/>
    <g stroke="rgba(120,205,240,.18)"><line x1="410" y1="18" x2="410" y2="802"/><line x1="18" y1="410" x2="802" y2="410"/></g>
    <g stroke="rgba(150,220,245,.4)"><line x1="400" y1="410" x2="420" y2="410"/><line x1="410" y1="400" x2="410" y2="420"/></g>
    <g transform="translate(90,90)">__WIRE__</g>
    <g fill="#f0a868"><circle cx="702" cy="214" r="3.5"/><circle cx="150" cy="640" r="2.5"/></g>
  </svg>
</div>
<div class="line1"></div>
<div class="anno a1">ORBIT / <b>1.00 R</b><br>INCLINATION 23.4°</div>
<div class="anno a2">GRATICULE <b>8×10</b><br>ORTHOGRAPHIC</div>
<div class="anno a3">NODE <b>CHN 19.5T</b><br>Δ +5.2% YOY</div>
<div class="rail">__TICKS__</div>
<div class="left">
  <div class="logo"><b>ORBIS</b><i>ATLAS / SCHEMATIC 01</i></div>
  <div class="kick">用数据重新认识这颗星球</div>
  <h1>欢迎回来，<b>探索者</b></h1>
  <p class="lead">登录以使用完整账户功能 · 游客可免费浏览地球</p>
  <div class="panel">
    <div class="tabs"><button class="on">登录</button><button>注册</button></div>
    <label class="fld"><em>01</em><span>邮箱</span><input type="email" value="2106812162@qq.com"></label>
    <label class="fld"><em>02</em><span>密码</span><input type="password" value="········"></label>
    <div class="row"><label class="chk"><input type="checkbox" checked><span>保持登录 30 天</span></label><a class="lnk">忘记密码</a></div>
    <button class="go">登录并进入</button>
    <div class="or">或</div>
    <a class="guest">以访客身份浏览</a>
    <a class="admin" href="/admin">
      <span class="ico"><svg width="17" height="17" viewBox="0 0 17 17" fill="none" stroke="#f0a868" stroke-width="1.2"><rect x="3" y="7.2" width="11" height="7.5" rx="1"/><path d="M5.6 7.2V5.1a2.9 2.9 0 0 1 5.8 0v2.1"/><circle cx="8.5" cy="11" r="1"/></svg></span>
      <span class="t"><b>管理员登录</b><small>ADMIN CONSOLE · /admin</small></span><em>→</em>
    </a>
    <div class="note">管理员账号与普通用户分离，普通邮箱账号无法进入管理后台。</div>
    <div class="foot">WORLD BANK WDI · FRANKFURTER · 111 CENTRAL BANKS</div>
  </div>
</div>
<div class="railbar">__MARKS__</div>'''
_ticks = ''.join('<i style="top:%dpx"></i><span style="top:%dpx">%d</span>' % (i * 148, i * 148 - 4, 1990 + i * 7) for i in range(5))
_marks = ''.join('<span style="left:%d%%"></span><em style="left:%d%%">%s</em>' % (i * 25, i * 25, y) for i, y in enumerate(['1990', '2000', '2010', '2018', '2025']))
R_BODY = (R_BODY.replace('__WIRE__', globe(640, 'rgba(90,175,215,.14)', 'rgba(40,110,160,.1)', 'rgba(4,16,28,.18)', 'rgba(150,225,250,.66)', .46, 20, 8, 11, shade=False))
          .replace('__TICKS__', _ticks).replace('__MARKS__', _marks))

# ========================================================== S Bento 卡片墙
S_CSS = '''
body{background:#060910;position:relative;overflow:hidden}
.wrap{position:absolute;inset:26px;display:grid;grid-template-columns:repeat(4,1fr);grid-template-rows:repeat(3,1fr);gap:13px}
.cell{background:#0d1420;border:1px solid rgba(120,165,205,.13);border-radius:15px;overflow:hidden;position:relative}
.hero{grid-column:1/4;grid-row:1/3;background:radial-gradient(ellipse 62% 88% at 88% 72%,#173355 0%,#0e1c30 55%,#0b1422 100%)}
.login{grid-column:4/5;grid-row:1/4;padding:30px 26px;background:linear-gradient(180deg,#101a2a,#0b1220);display:flex;flex-direction:column;justify-content:center}
.m1{grid-column:1/2;grid-row:3/4;padding:22px 24px}
.m2{grid-column:2/3;grid-row:3/4;padding:22px 24px}
.m3{grid-column:3/4;grid-row:3/4;padding:22px 24px}
.hero .txt{position:relative;z-index:4;padding:44px 46px}
.logo{display:flex;align-items:center;gap:11px;margin-bottom:32px}
.logo b{font-size:13px;letter-spacing:.34em;color:#eaf4ff;font-weight:600}
.logo i{font-style:normal;font-size:9px;letter-spacing:.16em;color:#7091b0;padding-left:11px;border-left:1px solid rgba(140,190,230,.22)}
h1{font-size:44px;line-height:1.28;font-weight:300;color:#f1f8ff;letter-spacing:.01em;max-width:600px}
h1 b{font-weight:600;color:#8ad7ff}
.lead{margin-top:16px;font-size:12.5px;color:#8faac4;line-height:1.9;max-width:470px}
.chips{display:flex;gap:10px;margin-top:26px}
.chip{padding:10px 16px;border:1px solid rgba(130,190,230,.2);border-radius:9px;background:rgba(10,22,38,.5)}
.chip b{display:block;font-size:19px;font-weight:300;color:#eaf6ff;line-height:1}
.chip span{display:block;font-size:9px;color:#6f91b0;margin-top:6px;letter-spacing:.1em}
.hero .planet{position:absolute;right:-90px;bottom:-230px;z-index:2;opacity:.82;filter:drop-shadow(0 0 60px rgba(60,140,205,.3))}
.hero .cap{position:absolute;left:46px;bottom:26px;font-family:Consolas,monospace;font-size:9px;letter-spacing:.2em;color:#5d7e9c;z-index:5}
.login .lglogo{position:absolute;top:28px;left:26px;display:flex;align-items:center;gap:8px;font-size:11px;letter-spacing:.28em;color:#cfe6f7;font-weight:600}
.login .lgstat{position:absolute;bottom:20px;left:26px;right:26px;display:flex;justify-content:space-between;font-family:Consolas,monospace;font-size:8.5px;color:#5d7e9c;letter-spacing:.1em}
.login h2{font-size:21px;color:#eef7ff;font-weight:600;margin:16px 0 5px}
.login .cs{font-size:10.5px;color:#7e9bb6;margin-bottom:20px;line-height:1.6}
.tabs{display:flex;gap:18px;border-bottom:1px solid rgba(130,180,220,.16);margin-bottom:20px}
.tabs button{background:none;border:0;cursor:pointer;padding:0 0 9px;font-size:11.5px;color:#7091b0;position:relative}
.tabs button.on{color:#eaf6ff;font-weight:600}
.tabs button.on:after{content:"";position:absolute;left:0;right:0;bottom:-1px;height:1.5px;background:#7dd3fc}
.fld{display:block;margin-bottom:15px}
.fld span{display:block;font-size:10px;color:#7e9bb6;margin-bottom:7px}
.fld input{width:100%;padding:10px 11px;border-radius:7px;background:rgba(255,255,255,.045);border:1px solid rgba(130,180,220,.18);font-size:12.5px;color:#eaf6ff;outline:none}
.fld input:focus{border-color:#7dd3fc}
.row{display:flex;justify-content:space-between;align-items:center;font-size:10.5px;color:#7e9bb6;margin:2px 0 18px}
.chk{display:flex;align-items:center;gap:6px;cursor:pointer}.chk input{accent-color:#7dd3fc;width:11px;height:11px}
.lnk{color:#7e9bb6;text-decoration:none;cursor:pointer}
.go{width:100%;padding:12px;border:0;border-radius:7px;background:linear-gradient(135deg,#8cdcff,#6aa9ff);color:#06192c;font-size:12.5px;font-weight:700;cursor:pointer}
.or{position:relative;text-align:center;font-size:9px;color:#5d7e9c;margin:13px 0}
.or:before,.or:after{content:"";position:absolute;top:50%;width:43%;height:1px;background:rgba(130,180,220,.14)}
.or:before{left:0}.or:after{right:0}
.guest{width:100%;padding:10px;border-radius:7px;background:none;border:1px solid rgba(130,180,220,.2);color:#9ab8cf;font-size:11px;cursor:pointer}
.foot{font-size:9px;color:#5d7e9c;margin-top:16px;line-height:1.65}
.mtitle{font-family:Consolas,monospace;font-size:9px;letter-spacing:.18em;color:#6f91b0;margin-bottom:14px}
.big{font-size:30px;font-weight:300;color:#eaf6ff;line-height:1}
.m1 .up{color:#ff7a6b;font-size:11px;margin-top:10px}
.spark{margin-top:12px;height:44px;width:100%}
.donut{position:absolute;right:16px;bottom:14px;width:76px;height:76px;border-radius:50%;background:conic-gradient(#7dd3fc 0 34%,#8a7dff 34% 62%,#f0a868 62% 82%,#2c405c 82% 100%);
  -webkit-mask:radial-gradient(circle,transparent 56%,#000 57%);mask:radial-gradient(circle,transparent 56%,#000 57%)}
.m2 .lg{font-size:11px;color:#91aac0;line-height:1.9;margin-top:6px}
.yr{display:flex;justify-content:space-between;margin-top:22px;font-family:Consolas,monospace;font-size:9px;color:#6f91b0}
.yr b{color:#8ad7ff;font-weight:400}
.track{height:3px;background:#1d2c42;border-radius:2px;margin-top:9px;position:relative}
.track i{position:absolute;left:72%;top:-3px;width:9px;height:9px;border-radius:50%;background:#7dd3fc;box-shadow:0 0 12px rgba(125,211,252,.8)}
'''
S_BODY = '''<div class="wrap">
  <div class="cell hero">
    <div class="txt">
      <div class="logo"><b>ORBIS</b><i>WORLD DATA ATLAS</i></div>
      <h1>用数据重新认识<br><b>这颗星球</b></h1>
      <p class="lead">217 个国家 · 25 年 · 4 项指标。拖动球体，看数字如何重塑国界。</p>
      <div class="chips"><div class="chip"><b>217</b><span>覆盖国家</span></div><div class="chip"><b>25</b><span>年份跨度</span></div><div class="chip"><b>6h</b><span>同步周期</span></div></div>
    </div>
    <div class="planet">__PLANET__</div>
    <div class="cap">WORLD BANK WDI · FRANKFURTER · 111 CENTRAL BANKS</div>
  </div>
  <div class="cell login">
    <div class="lglogo">ORBIS</div>
    <h2>欢迎回来</h2><p class="cs">登录以使用完整账户功能 · 游客可免费浏览地球</p>
    __TABS__ __FIELDS__
    <p class="foot">管理员入口 → 此处请用邮箱登录，不是管理员账号</p>
    <div class="lgstat"><span>WDI / 2026-11</span><span>217 · 25Y · 4</span></div>
  </div>
  <div class="cell m1"><div class="mtitle">GDP / CHN 2025</div><div class="big">19.5<span style="font-size:13px"> T</span></div>
    <div class="up">↑ +5.2% 同比</div><div class="spark">__SPARK__</div></div>
  <div class="cell m2"><div class="mtitle">DATA SOURCES</div>
    <div class="lg">世界银行 WDI<br>Frankfurter · 111 家央行<br>本地缓存 · 6 小时同步</div><div class="donut"></div></div>
  <div class="cell m3"><div class="mtitle">TIME RANGE</div>
    <div class="big">1990—2025</div><div class="yr"><span>1990</span><b>2025</b></div><div class="track"><i></i></div></div>
</div>'''
_spark = ('<svg width="270" height="44" viewBox="0 0 270 44"><polyline fill="none" stroke="#7dd3fc" stroke-width="1.6" points="' +
          ' '.join('%d,%d' % (i * 10, 36 - int(26 * (i / 27.0) ** .8) + (i % 3) * 3) for i in range(28)) + '"/></svg>')
S_BODY = (S_BODY.replace('__TABS__', TABS).replace('__FIELDS__', FIELDS).replace('__SPARK__', _spark)
          .replace('__PLANET__', globe(700, '#3d80b8', '#123f63', '#030d16', '#9fd4f2', .42, 20, 6, 8)))


FILES = [('O_玻璃穹顶', O_CSS, O_BODY), ('P_终端登录', P_CSS, P_BODY),
         ('Q_冷白数据台', Q_CSS, Q_BODY), ('R_蓝图轨道', R_CSS, R_BODY),
         ('S_Bento卡片墙', S_CSS, S_BODY)]
for name, css, body in FILES:
    io.open(os.path.join(OUT, name + '.html'), 'w', encoding='utf-8').write(doc(name, css, body))
    print('wrote', name)

CARDS = ''.join('''<div class="card"><a href="%s.html"><img src="%s.png" alt="%s"></a>
<div class="meta"><span class="no">%s</span><b>%s</b></div><p>%s</p></div>''' %
                (n.split('_')[0], n.split('_')[0], n, chr(ord('O') + i), n.split('_')[1], d)
                for i, (n, _, _, d) in enumerate([
                    (FILES[0][0], 0, 0, '巨型半透明玻璃球 + 浮动数据胶囊，消费级产品的通透质感。'),
                    (FILES[1][0], 0, 0, 'CRT 绿字点阵球与命令行输入，完全跳出常规网页登录框。'),
                    (FILES[2][0], 0, 0, '冷白数据台：细网格、真实数据表与蓝色强调，最像分析产品。'),
                    (FILES[3][0], 0, 0, '工程蓝图登录页：表单为主视觉，底部独立琥珀色「管理员登录 /admin」入口。'),
                    (FILES[4][0], 0, 0, 'Bento 卡片墙：表单只是其中一格，先看到产品再登录。')]))

GALLERY = '''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><title>ORBIS 登录风格 · 第四组</title>
<style>*{margin:0;padding:0;box-sizing:border-box}body{background:#0a1018;color:#dce8f4;font-family:"Segoe UI","Microsoft YaHei",sans-serif;padding:40px 56px 28px}
h1{font-size:24px;font-weight:300;letter-spacing:.1em;margin-bottom:8px}.sub{font-size:11px;color:#7892a8;letter-spacing:.1em;margin-bottom:28px}
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:22px}.card{background:#111b27;border:1px solid rgba(120,170,210,.14);border-radius:12px;overflow:hidden}
.card a{display:block;line-height:0}.card img{width:100%;display:block}.meta{display:flex;align-items:center;gap:12px;padding:14px 18px 4px}
.meta .no{font-family:Consolas,monospace;font-size:11px;color:#7dd3fc;border:1px solid rgba(125,211,252,.3);padding:2px 7px;border-radius:4px}
.meta b{font-size:14px;font-weight:500;letter-spacing:.06em}.card p{padding:4px 18px 16px;font-size:11px;color:#8199ae;line-height:1.7}
.foot{display:flex;justify-content:space-between;margin-top:26px;padding-top:16px;border-top:1px solid rgba(120,170,210,.14);font-size:10px;color:#5f778c;letter-spacing:.06em}
</style></head><body><h1>ORBIS · 登录页第四组</h1><p class="sub">五种结构完全不同的方向 · 1440×900 实际渲染 · 点击缩略图打开可编辑 HTML</p>
<div class="grid">__CARDS__</div>
<div class="foot"><span>文案统一为「用数据重新认识这颗星球」</span><span>ORBIS · 用数据重新认识这颗星球</span></div>
</body></html>'''.replace('__CARDS__', CARDS)
io.open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8').write(GALLERY)
print('wrote gallery')
