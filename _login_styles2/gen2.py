# -*- coding: utf-8 -*-
"""ORBIS 登录页 —— 第二批风格探索（版式 + 视觉语言都换掉）"""
import io, os, math, itertools

OUT = 'C:/0_workspace/项目二2/_login_styles2'
os.makedirs(OUT, exist_ok=True)
_uid = itertools.count(1)

SANS = '"Segoe UI","PingFang SC","Microsoft YaHei",system-ui,-apple-system,sans-serif'
SERIF = 'Georgia,"Songti SC","Times New Roman","SimSun",serif'
MONO = 'Consolas,"SF Mono","Courier New",monospace'


def globe(size, hi, mid, lo, line, lop=0.45, tilt=20, nlat=5, nlon=7, shade=True):
    """正交投影球体 + 经纬线（SVG，精确计算）"""
    R = size / 2.0
    u = 'gl%d' % next(_uid)
    ct, st = math.cos(math.radians(tilt)), math.sin(math.radians(tilt))
    p = []
    for i in range(1, nlat + 1):
        phi = math.radians(-90 + 180.0 * i / (nlat + 1))
        r = R * math.cos(phi)
        cy = R + R * math.sin(phi) * ct
        p.append('<ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f"/>' % (R, cy, r, max(.5, r * st)))
    for i in range(1, nlon + 1):
        th = math.pi * i / (nlon + 1)
        p.append('<ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f"/>' % (R, R, R * math.sin(th), R * ct))
    shade_c = ('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="url(#%s_s)"/>' % (R, R, R, u)) if shade else ''
    return (
        '<svg width="%d" height="%d" viewBox="0 0 %d %d" style="display:block">'
        '<defs>'
        '<radialGradient id="%s" cx="32%%" cy="24%%" r="80%%">'
        '<stop offset="0" stop-color="%s"/><stop offset="45%%" stop-color="%s"/><stop offset="100%%" stop-color="%s"/>'
        '</radialGradient>'
        '<radialGradient id="%s_s" cx="34%%" cy="26%%" r="72%%">'
        '<stop offset="55%%" stop-color="#000" stop-opacity="0"/><stop offset="100%%" stop-color="#000" stop-opacity="0.62"/>'
        '</radialGradient>'
        '<clipPath id="%s_c"><circle cx="%.1f" cy="%.1f" r="%.1f"/></clipPath>'
        '</defs>'
        '<circle cx="%.1f" cy="%.1f" r="%.1f" fill="url(#%s)"/>'
        '<g clip-path="url(#%s_c)" fill="none" stroke="%s" stroke-width="0.9" opacity="%s">%s</g>'
        '%s'
        '</svg>'
    ) % (size, size, size, size, u, hi, mid, lo, u, u, R, R, R, R, R, R, u, u, line, lop, ''.join(p), shade_c)


TABS = '<div class="tabs"><button class="on">登录</button><button>注册</button></div>'
FIELDS = '''<label class="fld"><span>邮箱</span><input type="email" value="2106812162@qq.com"></label>
      <label class="fld"><span>密码</span><input type="password" value="········"></label>
      <div class="row"><label class="chk"><input type="checkbox" checked><span>保持登录 30 天</span></label><a class="lnk">忘记密码</a></div>
      <button class="go">登录并进入</button>
      <div class="or">或</div>
      <button class="guest">以访客身份浏览</button>'''

FEATS = [('01', '全球 200+ 国家', 'GDP · 人口 · 寿命 · 汇率实时数据'),
         ('02', '对比与分享', '链接记住状态，一键生成分享图'),
         ('03', '变化提醒', '关注国家数据大变，邮件自动通知')]


def doc(title, css, body, w=1440, h=900):
    html = '''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><title>%s</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:%dpx;height:%dpx;overflow:hidden}
body{font-family:%s;-webkit-font-smoothing:antialiased}
button,input{font:inherit;color:inherit}
%s
</style></head><body>
%s
</body></html>''' % (title, w, h, SANS, css, body)
    return html


# ============ E 纸白编辑 ============
E_CSS = '''
body{background:#f2eee4;color:#1b1812;display:flex;flex-direction:column}
.rule{position:absolute;background:#cdc5b3}
.hd{display:flex;justify-content:space-between;align-items:center;padding:26px 64px;border-bottom:1px solid #d8d0bd;position:relative;z-index:5}
.hd .l{display:flex;align-items:baseline;gap:14px}
.hd .l b{font-size:15px;letter-spacing:.36em;font-weight:700}
.hd .l i{font-style:normal;font-size:10.5px;letter-spacing:.18em;color:#8b8371}
.hd .r{font-size:11px;letter-spacing:.16em;color:#8b8371;display:flex;gap:26px}
.hd .r b{color:#b4552d;font-weight:600}
.main{flex:1;display:grid;grid-template-columns:1fr 560px;position:relative}
.left{padding:78px 0 0 64px;position:relative}
.tag{display:flex;align-items:center;gap:12px;font-size:10.5px;letter-spacing:.26em;color:#b4552d;font-weight:600;margin-bottom:30px}
.tag em{font-style:normal;width:34px;height:1px;background:#b4552d;display:block}
h1{font-family:__FS__;font-size:74px;line-height:1.05;letter-spacing:-.01em;font-weight:400}
h1 i{font-style:italic;color:#b4552d}
.sub{margin-top:24px;font-size:14px;line-height:1.9;color:#6b6455;max-width:410px}
.dl{margin-top:56px;max-width:470px}
.dl>div{display:grid;grid-template-columns:34px 1fr;align-items:baseline;gap:10px;
  padding:15px 0;border-top:1px solid #dbd3c0}
.dl>div:last-child{border-bottom:1px solid #dbd3c0}
.dl i{font-style:normal;font-family:__FM__;font-size:10px;color:#b4552d}
.dl b{font-size:13.5px;font-weight:600;letter-spacing:.02em}
.dl small{display:block;font-size:11.5px;color:#8b8371;margin-top:5px;font-weight:400}
.gwrap{position:absolute;left:-118px;bottom:-236px;opacity:.09;filter:grayscale(1)}
.src{position:absolute;left:64px;bottom:34px;font-size:10.5px;color:#948b78;letter-spacing:.06em}
.right{border-left:1px solid #d8d0bd;padding:0 72px;display:flex;flex-direction:column;justify-content:center;position:relative;background:rgba(255,255,255,.34)}
.right:before{content:"02 / SIGN IN";position:absolute;top:34px;right:72px;font-size:10px;letter-spacing:.22em;color:#a89f8b}
h2{font-family:__FS__;font-size:31px;font-weight:400;letter-spacing:.01em}
.cs{font-size:12px;color:#7d7565;margin:10px 0 34px;letter-spacing:.02em}
.tabs{display:flex;gap:30px;border-bottom:1px solid #d8d0bd;margin-bottom:30px}
.tabs button{background:none;border:0;cursor:pointer;padding:0 0 11px;font-size:12.5px;letter-spacing:.14em;
  color:#9a9280;position:relative}
.tabs button.on{color:#1b1812;font-weight:600}
.tabs button.on:after{content:"";position:absolute;left:0;right:0;bottom:-1px;height:2px;background:#1b1812}
.fld{display:block;margin-bottom:26px}
.fld span{display:block;font-size:10px;letter-spacing:.2em;color:#8b8371;margin-bottom:9px}
.fld input{width:100%;background:none;border:0;border-bottom:1px solid #c9c0ac;padding:6px 0 10px;font-size:14px;color:#1b1812;outline:none;letter-spacing:.02em}
.fld input:focus{border-color:#1b1812}
.row{display:flex;justify-content:space-between;align-items:center;font-size:11.5px;color:#7d7565;margin:6px 0 34px}
.chk{display:flex;align-items:center;gap:8px;cursor:pointer}
.chk input{accent-color:#b4552d;width:13px;height:13px}
.lnk{color:#7d7565;text-decoration:underline;text-underline-offset:3px;cursor:pointer}
.go{width:100%;padding:16px;background:#1b1812;color:#f6f2e9;border:0;cursor:pointer;
  font-size:12.5px;letter-spacing:.22em;font-weight:600;border-radius:1px}
.or{text-align:center;font-size:10px;letter-spacing:.2em;color:#a89f8b;margin:20px 0}
.guest{width:100%;padding:14px;background:none;border:1px solid #c9c0ac;color:#4a4436;cursor:pointer;
  font-size:12px;letter-spacing:.14em;border-radius:1px}
.foot{font-size:10px;color:#a89f8b;margin-top:26px;line-height:1.8;letter-spacing:.04em}
.foot b{color:#b4552d;font-weight:400}
'''
E_CSS = E_CSS.replace('__FS__', SERIF).replace('__FM__', MONO)

E_BODY = '''<div class="hd">
  <div class="l"><b>ORBIS</b><i>EARTH DATA ATLAS</i></div>
  <div class="r"><span>世界银行 WDI</span><span>Frankfurter 111 家央行</span><b>v2.4</b></div>
</div>
<div class="main">
  <div class="left">
    <div class="tag"><em></em>用数据重新认识这颗星球</div>
    <h1>用数据<br>重新认识<i>这颗星球</i>。</h1>
    <p class="sub">把 200 多个国家的经济、人口与健康指标，画成一颗可以旋转的地球。拖动它，看数字在二十五年里如何改变一个国家的形状。</p>
    <div class="dl">
      <div><i>01</i><span><b>全球 200+ 国家</b><small>GDP · 人口 · 寿命 · 汇率实时数据</small></span></div>
      <div><i>02</i><span><b>对比与分享</b><small>链接记住状态，一键生成分享图</small></span></div>
      <div><i>03</i><span><b>变化提醒</b><small>关注国家数据大变，邮件自动通知</small></span></div>
    </div>
    <div class="gwrap">__GLOBE__</div>
    <div class="src">数据源：世界银行 WDI · Frankfurter（111 家央行） · 更新于 2026-11</div>
  </div>
  <div class="right">
    <h2>欢迎回来</h2>
    <p class="cs">登录以使用完整账户功能 · 游客可免费浏览地球</p>
    __TABS__
    __FIELDS__
    <p class="foot">继续即表示同意<b>服务条款</b>与<b>隐私政策</b><br>管理员请从 <b>/admin</b> 入口登录，此处使用邮箱账号</p>
  </div>
</div>'''
E_BODY = E_BODY.replace('__GLOBE__', globe(380, '#8d8574', '#5d564a', '#2c2721', '#1b1812', .9, 18, 6, 8))
E_BODY = E_BODY.replace('__TABS__', TABS).replace('__FIELDS__', FIELDS)


# ============ F 深空聚焦 ============
F_CSS = '''
body{background:#04080f;overflow:hidden;position:relative;display:grid;place-items:center}
.sky{position:absolute;inset:0;background:radial-gradient(ellipse 90% 70% at 50% 8%,#12314f 0%,#0a1a2c 34%,#050a12 70%,#03060b 100%)}
.stars{position:absolute;inset:0;opacity:.55}
.planet{position:absolute;left:50%;bottom:-560px;transform:translateX(-50%);filter:drop-shadow(0 0 90px rgba(56,132,196,.35))}
.haze{position:absolute;left:50%;bottom:-40px;transform:translateX(-50%);width:1500px;height:420px;
  background:radial-gradient(ellipse at 50% 100%,rgba(86,168,226,.28),transparent 66%);filter:blur(30px)}
.orbit{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%) rotate(-16deg);width:1180px;height:1180px;
  border-radius:50%;border:1px solid rgba(120,190,235,.1)}
.orbit.b{width:980px;height:980px;transform:translate(-50%,-50%) rotate(22deg);border-style:dashed;border-color:rgba(120,190,235,.08)}
.shade{position:absolute;inset:0;z-index:4;pointer-events:none;
  background:radial-gradient(ellipse 64% 60% at 50% 46%,rgba(3,8,15,.8) 0%,rgba(3,8,15,.5) 52%,rgba(3,8,15,.06) 80%,transparent 92%)}
.card{position:relative;z-index:6;width:426px;padding:38px 38px 26px;border-radius:20px;
  background:linear-gradient(170deg,rgba(15,32,52,.95),rgba(6,14,24,.96));
  border:1px solid rgba(120,180,220,.16);backdrop-filter:blur(22px);
  box-shadow:0 44px 110px rgba(0,0,0,.72),0 0 0 1px rgba(150,205,240,.04),inset 0 1px 0 rgba(170,215,245,.13)}
.top{display:flex;align-items:center;justify-content:center;gap:11px;margin-bottom:26px}
.top .g{width:26px;height:26px;border-radius:50%;overflow:hidden;box-shadow:0 0 18px rgba(90,170,225,.55)}
.top b{font-size:13px;letter-spacing:.34em;font-weight:600;color:#dcecf8}
h2{font-size:21px;font-weight:600;text-align:center;color:#eef7ff;letter-spacing:.02em}
.cs{font-size:12px;color:#6f93ac;text-align:center;margin:9px 0 26px;letter-spacing:.02em}
.tabs{display:flex;gap:4px;padding:4px;border-radius:11px;background:rgba(255,255,255,.05);margin-bottom:22px;
  border:1px solid rgba(120,180,220,.1)}
.tabs button{flex:1;padding:9px;border:0;border-radius:8px;background:none;color:#7e9db4;font-size:12.5px;cursor:pointer;letter-spacing:.06em}
.tabs button.on{background:rgba(127,200,238,.16);color:#b6e4fa;font-weight:600}
.fld{display:block;margin-bottom:14px}
.fld span{display:block;font-size:11px;color:#7e9db4;margin-bottom:7px;letter-spacing:.04em}
.fld input{width:100%;padding:12px 13px;border-radius:9px;background:rgba(255,255,255,.04);
  border:1px solid rgba(120,180,220,.16);font-size:13px;color:#e8f5ff;outline:none}
.fld input:focus{border-color:rgba(127,208,238,.55);background:rgba(127,208,238,.07)}
.row{display:flex;justify-content:space-between;align-items:center;font-size:11.5px;color:#7e9db4;margin:2px 0 18px}
.chk{display:flex;align-items:center;gap:7px;cursor:pointer}
.chk input{accent-color:#5fb8dc;width:13px;height:13px}
.lnk{color:#7e9db4;text-decoration:none;cursor:pointer}
.go{width:100%;padding:13px;border:0;border-radius:9px;cursor:pointer;font-size:13.5px;font-weight:700;
  background:linear-gradient(135deg,#8bd9f5,#4fa8d8);color:#04141f;letter-spacing:.04em;
  box-shadow:0 10px 30px rgba(79,168,216,.32)}
.or{position:relative;text-align:center;font-size:10.5px;color:#5f8197;margin:16px 0}
.or:before,.or:after{content:"";position:absolute;top:50%;width:44%;height:1px;background:rgba(120,170,205,.14)}
.or:before{left:0}.or:after{right:0}
.guest{width:100%;padding:12px;border-radius:9px;background:none;border:1px solid rgba(120,170,205,.2);
  color:#9dbdd2;font-size:12.5px;cursor:pointer}
.strip{display:flex;justify-content:center;gap:0;margin-top:24px;font-size:10.5px;color:#62839a;letter-spacing:.04em}
.strip span{padding:0 13px;border-right:1px solid rgba(120,170,205,.12)}
.strip span:last-child{border:0}
.foot{text-align:center;font-size:9.5px;color:#54748a;margin-top:16px;letter-spacing:.04em}
'''

F_BODY = '''<div class="sky"></div>
<svg class="stars" width="1440" height="900"><g fill="#cfe6fb">__STARS__</g></svg>
<div class="orbit"></div><div class="orbit b"></div>
<div class="planet">__PLANET__</div>
<div class="haze"></div>
<div class="shade"></div>
<div class="card">
  <div class="top"><div class="g">__MINI__</div><b>ORBIS</b></div>
  <h2>欢迎回来</h2>
  <p class="cs">用数据重新认识这颗星球 · 数据可视化平台</p>
  __TABS__
  __FIELDS__
  <div class="strip"><span>200+ 国家</span><span>对比分享</span><span>变化提醒</span></div>
  <p class="foot">数据源 World Bank WDI · Frankfurter</p>
</div>'''

_stars = ''.join('<circle cx="%d" cy="%d" r="%.1f" opacity="%.2f"/>' % (
    (i * 197 + 43) % 1440, (i * 331 + 71) % 900, 0.6 + (i % 3) * 0.45, 0.25 + (i % 5) * 0.12) for i in range(150))
F_BODY = F_BODY.replace('__STARS__', _stars)
F_BODY = F_BODY.replace('__PLANET__', globe(1320, '#3d88bd', '#12456b', '#04101a', '#9fd4f2', .13, 20, 7, 9))
F_BODY = F_BODY.replace('__MINI__', globe(26, '#8fd0ff', '#3a82c8', '#123a6a', '#bfe2ff', .45, 18, 3, 4))
F_BODY = F_BODY.replace('__TABS__', TABS).replace('__FIELDS__', FIELDS)


# ============ G 电影海报 ============
G_CSS = r"""
body{background:#04060a;position:relative;overflow:hidden}
.stars{position:absolute;inset:0;opacity:.85;pointer-events:none}
.planet{position:absolute;right:-460px;bottom:-620px;opacity:.95;filter:drop-shadow(0 0 110px rgba(58,136,196,.45))}
.rim{position:absolute;right:-460px;bottom:-620px;width:1400px;height:1400px;border-radius:50%;
  background:radial-gradient(circle at 34% 26%,transparent 60%,rgba(255,186,120,.13) 67%,transparent 73%)}
.vig{position:absolute;inset:0;background:
  linear-gradient(180deg,rgba(2,4,8,.86) 0%,rgba(2,4,8,.1) 26%,rgba(2,4,8,.2) 62%,rgba(2,4,8,.94) 100%),
  radial-gradient(ellipse 70% 60% at 22% 42%,rgba(4,8,16,.55),transparent 70%)}
.side-note{position:absolute;right:36px;top:120px;z-index:8;writing-mode:vertical-rl;
  font-size:9px;letter-spacing:.34em;color:rgba(196,218,238,.5);text-transform:uppercase}
.hd{position:relative;z-index:9;display:flex;justify-content:space-between;align-items:center;padding:30px 72px}
.hd .l{display:flex;align-items:center;gap:12px}
.hd .l b{font-size:13px;letter-spacing:.4em;color:#eaf2fb;font-weight:600}
.hd .l i{font-style:normal;font-size:9.5px;letter-spacing:.2em;color:#7f8ea1;padding-left:12px;border-left:1px solid rgba(160,190,220,.18)}
.hd .r{display:flex;align-items:center;gap:22px;font-size:12px;color:#8b9aab;letter-spacing:.06em}
.hd .r b{color:#f0a868;font-weight:500;cursor:pointer}
.hero{position:relative;z-index:8;padding:0 72px;margin-top:70px}
.eyebrow{font-size:10.5px;letter-spacing:.34em;color:#f0a868;margin-bottom:22px}
h1{font-size:120px;line-height:.92;letter-spacing:.14em;font-weight:200;color:#f4f8fc;
  text-shadow:0 0 90px rgba(120,180,230,.28)}
.hero h2{margin-top:24px;font-size:28px;font-weight:300;letter-spacing:.1em;color:#d7e4f1}
.hero p{margin-top:16px;font-size:13px;line-height:1.95;color:#93a7bb;max-width:462px;letter-spacing:.03em}
.spec{display:flex;margin-top:38px;width:486px;border-top:1px solid rgba(150,190,225,.16);padding-top:20px}
.spec>div{flex:1;min-width:0}
.spec>div+div{padding-left:20px;border-left:1px solid rgba(150,190,225,.12)}
.spec b{display:block;font-size:30px;font-weight:200;color:#eff6fc;line-height:1;letter-spacing:.01em}
.spec span{display:block;margin-top:9px;font-size:9px;letter-spacing:.18em;color:#6b8094}
.src{margin-top:30px;font-size:9.5px;letter-spacing:.14em;color:#4e6274}
.axis{position:relative;margin-top:50px;width:486px;height:1px;
  background:linear-gradient(90deg,rgba(150,190,225,.32),rgba(150,190,225,.05))}
.axis em{position:absolute;top:-3px;width:1px;height:7px;background:rgba(150,190,225,.38)}
.axis span{position:absolute;top:11px;font-size:9px;letter-spacing:.14em;color:#5b7082;transform:translateX(-50%)}
.axis span.end{transform:translateX(-100%)}
.axis .mk{position:absolute;top:-4px;left:58%;width:9px;height:9px;border-radius:50%;background:#f0a868;
  box-shadow:0 0 14px rgba(240,168,104,.8)}
.axis .cap{position:absolute;top:-26px;left:0;font-size:9px;letter-spacing:.24em;color:#7d8ea1;transform:none}
.dock{position:absolute;left:0;right:0;bottom:0;z-index:10;
  background:linear-gradient(180deg,rgba(10,16,26,.5),rgba(6,10,16,.9));
  border-top:1px solid rgba(150,190,225,.14);backdrop-filter:blur(18px);padding:22px 72px 24px}
.dl1{display:flex;align-items:center;gap:26px;font-size:9.5px;letter-spacing:.22em;color:#6d8194;margin-bottom:20px}
.dl1 .hint{flex:1;color:#5b7082;white-space:nowrap}
.dl1 b{color:#f0a868;font-weight:500;white-space:nowrap}
.tabs{display:flex;gap:22px}
.tabs button{background:none;border:0;cursor:pointer;color:#5f7386;padding:0 0 5px;letter-spacing:.2em;font-size:10px}
.tabs button.on{color:#eaf2fb;border-bottom:1px solid #f0a868}
.frm{display:flex;align-items:flex-end;gap:34px}
.fld{flex:0 0 306px;position:relative}
.rgroup{display:flex;align-items:center;gap:20px;margin-left:auto;padding-bottom:2px}
.orx{font-size:9.5px;letter-spacing:.18em;color:#5f7386}
.glink{font-size:11.5px;color:#a9bccd;text-decoration:none;cursor:pointer;
  border-bottom:1px solid rgba(150,190,225,.22);padding-bottom:2px;letter-spacing:.04em}
.glink:hover{color:#f0a868;border-color:#f0a868}
.fld span{display:block;font-size:9.5px;letter-spacing:.22em;color:#7d8e9f;margin-bottom:8px}
.fld input{width:100%;background:none;border:0;border-bottom:1px solid rgba(150,190,225,.22);
  padding:4px 0 10px;font-size:14px;color:#eef5fc;outline:none;letter-spacing:.02em}
.fld input:focus{border-color:#f0a868}
.go{padding:13px 34px;border:0;cursor:pointer;font-size:12px;letter-spacing:.24em;font-weight:600;
  background:#f0a868;color:#20160a;border-radius:2px;white-space:nowrap}
.go:hover{background:#f6bb85}
.chk{display:flex;align-items:center;gap:7px;font-size:10.5px;color:#7d8e9f;letter-spacing:.06em;cursor:pointer}
.chk input{accent-color:#f0a868;width:12px;height:12px}
"""

G_BODY = """<div class="planet">__PLANET__</div><div class="rim"></div><div class="vig"></div>
<svg class="stars" width="1440" height="900"><g fill="#dcebf9">__STARS2__</g></svg>
<div class="side-note">ORBIS · 217 COUNTRIES · 1990—2025</div>
<div class="hd">
  <div class="l"><b>ORBIS</b><i>EARTH / DATA / ATLAS</i></div>
  <div class="r"><span>还没有账号？</span><b>立即注册 →</b></div>
</div>
<div class="hero">
  <div class="eyebrow">CHAPTER 01 — 数据可视化平台</div>
  <h1>ORBIS</h1>
  <h2>用数据重新认识这颗星球</h2>
  <p>拖动这颗星球，看 GDP、人口与寿命在二十五年里如何改变一个国家的形状。</p>
  <div class="spec">
    <div><b>217</b><span>覆盖国家</span></div>
    <div><b>25</b><span>年份跨度</span></div>
    <div><b>4</b><span>核心指标</span></div>
    <div><b>6h</b><span>同步周期</span></div>
  </div>
  <p class="src">数据源：世界银行 WDI · Frankfurter（111 家央行）· 更新于 2026-11</p>
  <div class="axis"><span class="cap">拖动地球 · 查看任一国家的 25 年变化</span>
    <em style="left:0"></em><em style="left:25%"></em><em style="left:50%"></em><em style="left:75%"></em><em style="left:100%"></em>
    <span style="left:0;transform:none">1990</span><span style="left:25%">2000</span><span style="left:50%">2010</span>
    <span style="left:75%">2018</span><span style="left:100%" class="end">2025</span>
    <i class="mk"></i>
  </div>
</div>
<div class="dock">
  <div class="dl1">
    <div class="tabs"><button class="on">登录</button><button>注册</button></div>
    <span class="hint">登录以使用完整账户功能 · 游客可免费浏览地球</span>
    <b>管理员入口 /admin</b>
  </div>
  <div class="frm">
    <label class="fld"><span>邮箱</span><input type="email" value="2106812162@qq.com"></label>
    <label class="fld"><span>密码</span><input type="password" value="········"></label>
    <div class="rgroup">
      <label class="chk"><input type="checkbox" checked>记住我</label>
      <button class="go">进入 →</button>
      <span class="orx">或</span>
      <a class="glink">以访客身份浏览</a>
    </div>
  </div>
</div>"""
G_BODY = G_BODY.replace('__PLANET__', globe(1180, '#3c81b4', '#123f63', '#030d16', '#a8d6f0', .12, 22, 7, 9))
import math as _m
def _mk_stars():
    out = []
    for i in range(520):
        x = (i * 311 + 89) % 1440
        y = (i * 173 + 7) % 780
        d = _m.hypot(x - 1310, y - 930)
        if d < 625:
            continue
        out.append('<circle cx="%d" cy="%d" r="%.1f" opacity="%.2f"/>' % (
            x, y, .5 + (i % 3) * .35, .18 + (i % 5) * .13))
    return ''.join(out[:170])
_st2 = _mk_stars()
G_BODY = G_BODY.replace('__STARS2__', _st2)

# ============ H 双色分屏 ============
H_CSS = '''
body{display:grid;grid-template-columns:600px 1fr;background:#f6f7f9}
.side{background:#0a1420;padding:44px 48px 36px;display:flex;flex-direction:column;position:relative;overflow:hidden}
.side .gl{position:absolute;left:-200px;bottom:-432px;opacity:.3}
.hd{display:flex;align-items:center;gap:11px;position:relative;z-index:3}
.hd b{font-size:13px;letter-spacing:.36em;color:#e6f1fa;font-weight:600}
.hd i{font-style:normal;font-size:9px;letter-spacing:.2em;color:#6b869c;margin-left:auto;font-family:__FM__}
.ttl{margin-top:66px;position:relative;z-index:3}
.live{display:inline-flex;align-items:center;gap:7px;font-size:9.5px;letter-spacing:.24em;color:#5ee6a8;
  font-family:__FM__;margin-bottom:18px}
.live em{width:6px;height:6px;border-radius:50%%;background:#5ee6a8;box-shadow:0 0 10px #5ee6a8;display:block}
.ttl h1{font-size:34px;line-height:1.32;font-weight:600;color:#f2f8fd;letter-spacing:.02em}
.ttl p{margin-top:14px;font-size:12px;line-height:1.85;color:#7b96ab;max-width:400px}
.stats{margin-top:40px;position:relative;z-index:3;display:flex;flex-direction:column;gap:20px}
.st{display:grid;grid-template-columns:76px 1fr 68px;align-items:center;gap:14px;font-family:__FM__}
.st .k{font-size:10px;letter-spacing:.1em;color:#6b869c}
.st .bar{height:3px;background:rgba(120,170,205,.14);position:relative;border-radius:2px}
.st .bar i{position:absolute;left:0;top:0;bottom:0;background:linear-gradient(90deg,#4fa8d8,#5ee6a8);border-radius:2px}
.st .v{font-size:11.5px;color:#c3d8e6;text-align:right}
.sfoot{margin-top:auto;position:relative;z-index:3;display:flex;justify-content:space-between;
  font-size:9.5px;letter-spacing:.1em;color:#55708a;font-family:__FM__;padding-top:16px;
  border-top:1px solid rgba(120,170,205,.12)}
.sfoot b{color:#5ee6a8;font-weight:400}
.main{display:grid;place-items:center;position:relative}
.main:before{content:"";position:absolute;left:0;top:0;bottom:0;width:1px;background:#e2e6ec}
.serial{position:absolute;top:40px;right:56px;font-size:10px;letter-spacing:.22em;color:#adb6c2;font-family:__FM__}
.card{width:404px;background:#fff;border-radius:16px;padding:36px 36px 28px;
  box-shadow:0 22px 60px rgba(20,40,70,.09),0 2px 6px rgba(20,40,70,.05);border:1px solid #eceff3}
h2{font-size:22px;font-weight:600;color:#101a26;letter-spacing:.01em}
.cs{font-size:12px;color:#8a94a2;margin:8px 0 26px}
.tabs{display:flex;gap:4px;padding:4px;background:#f1f3f6;border-radius:10px;margin-bottom:24px}
.tabs button{flex:1;padding:9px;border:0;border-radius:8px;background:none;color:#8a94a2;font-size:12.5px;cursor:pointer}
.tabs button.on{background:#fff;color:#101a26;font-weight:600;box-shadow:0 1px 3px rgba(20,40,70,.12)}
.fld{display:block;margin-bottom:16px}
.fld span{display:block;font-size:11px;color:#7a8593;margin-bottom:7px}
.fld input{width:100%;padding:12px 13px;border-radius:9px;border:1px solid #dfe4ea;font-size:13px;color:#101a26;outline:none;background:#fbfcfd}
.fld input:focus{border-color:#0a1420;background:#fff;box-shadow:0 0 0 3px rgba(10,20,32,.06)}
.row{display:flex;justify-content:space-between;align-items:center;font-size:11.5px;color:#8a94a2;margin:4px 0 20px}
.chk{display:flex;align-items:center;gap:7px;cursor:pointer}
.chk input{accent-color:#0a1420;width:13px;height:13px}
.lnk{color:#8a94a2;cursor:pointer;text-decoration:none}
.go{width:100%;padding:13px;border:0;border-radius:9px;background:#0a1420;color:#fff;font-size:13.5px;
  font-weight:600;cursor:pointer;letter-spacing:.04em}
.go:hover{background:#16273c}
.or{position:relative;text-align:center;font-size:10.5px;color:#b3bcc7;margin:16px 0}
.or:before,.or:after{content:"";position:absolute;top:50%%;width:44%%;height:1px;background:#e6eaef}
.or:before{left:0}.or:after{right:0}
.guest{width:100%;padding:12px;border-radius:9px;background:#fff;border:1px solid #dfe4ea;color:#4a5462;font-size:12.5px;cursor:pointer}
.guest:hover{background:#f7f9fb}
.foot{font-size:10px;color:#adb6c2;text-align:center;margin-top:20px;line-height:1.8}
.foot b{color:#0a1420;font-weight:500}
'''
H_CSS = H_CSS.replace('__FM__', MONO).replace('50%%','50%').replace('44%%','44%')

H_BODY = '''<div class="side">
  <div class="gl">__GLOBE__</div>
  <div class="hd"><b>ORBIS</b><i>AUTH / v2.4</i></div>
  <div class="ttl">
    <div class="live"><em></em>LIVE DATASET</div>
    <h1>一颗可以旋转的<br>世界经济年鉴</h1>
    <p>200+ 国家的 GDP、人口、寿命与汇率，全部落在同一颗球面上。数据每 6 小时与世界银行同步一次。</p>
  </div>
  <div class="stats">
    <div class="st"><span class="k">GDP 总量</span><span class="bar"><i style="width:92%"></i></span><span class="v">$105.4T</span></div>
    <div class="st"><span class="k">总人口</span><span class="bar"><i style="width:78%"></i></span><span class="v">8.09B</span></div>
    <div class="st"><span class="k">平均寿命</span><span class="bar"><i style="width:64%"></i></span><span class="v">73.4 y</span></div>
    <div class="st"><span class="k">国家覆盖</span><span class="bar"><i style="width:100%"></i></span><span class="v">217</span></div>
  </div>
  <div class="sfoot"><span>WORLD BANK WDI</span><span>UPDATED <b>2026-11-17</b></span></div>
</div>
<div class="main">
  <div class="serial">01 — SIGN IN</div>
  <div class="card">
    <h2>欢迎回来</h2>
    <p class="cs">登录以使用完整账户功能 · 游客可免费浏览</p>
    __TABS__
    __FIELDS__
    <p class="foot">继续即表示同意服务条款与隐私政策<br>管理员请从 <b>/admin</b> 入口登录</p>
  </div>
</div>'''
H_BODY = H_BODY.replace('__GLOBE__', globe(840, '#5ba6da', '#1c5586', '#061826', '#a8d6f0', .15, 20, 6, 8))
H_BODY = H_BODY.replace('__TABS__', TABS).replace('__FIELDS__', FIELDS)


# ============ I 网格浮卡 ============
I_CSS = '''
body{background:#e9edf3;position:relative;overflow:hidden}
.grid{position:absolute;inset:0;background-image:linear-gradient(rgba(24,58,92,.055) 1px,transparent 1px),
  linear-gradient(90deg,rgba(24,58,92,.055) 1px,transparent 1px);background-size:34px 34px}
.blob{position:absolute;border-radius:50%}
.b1{width:900px;height:900px;left:-330px;top:-260px;background:radial-gradient(circle at 40% 40%,rgba(90,150,210,.16),transparent 66%)}
.b2{width:700px;height:700px;right:-180px;bottom:-240px;background:radial-gradient(circle at 50% 50%,rgba(240,168,104,.13),transparent 66%)}
.hd{position:absolute;left:56px;right:56px;top:34px;display:flex;justify-content:space-between;align-items:center;z-index:6}
.hd .l{display:flex;align-items:center;gap:12px}
.hd .l b{font-size:14px;letter-spacing:.34em;color:#0e2233;font-weight:700}
.hd .l i{font-style:normal;font-size:9.5px;letter-spacing:.18em;color:#8296a8;padding-left:12px;border-left:1px solid #ccd6e0}
.hd .r{display:flex;gap:10px;font-size:11px;color:#5d7285}
.hd .r span{padding:7px 15px;border-radius:20px;border:1px solid #d3dbe4;background:rgba(255,255,255,.7)}
.hd .r span.on{background:#0e2233;color:#fff;border-color:#0e2233}
.scene{position:absolute;inset:0;display:grid;place-items:center;grid-template-columns:1fr;z-index:5;perspective:1400px}
.card{width:452px;background:linear-gradient(165deg,#10293f,#0a1a29 60%,#081520);border-radius:20px;padding:36px 36px 26px;
  border:1px solid rgba(140,190,230,.16);
  box-shadow:0 50px 90px -30px rgba(10,30,50,.55),0 2px 0 rgba(255,255,255,.5) inset;
  transform:rotateY(5deg) rotateX(2deg) translateX(-215px);transform-style:preserve-3d}
.card:after{content:"";position:absolute;inset:0;border-radius:20px;pointer-events:none;
  background:linear-gradient(160deg,rgba(255,255,255,.07),transparent 42%)}
.brand{display:flex;align-items:center;gap:10px;margin-bottom:24px}
.brand b{font-size:12px;letter-spacing:.34em;color:#dcecf8;font-weight:600}
.brand i{font-style:normal;font-size:9px;letter-spacing:.16em;color:#6f8ea6;margin-left:auto}
h2{font-size:21px;font-weight:600;color:#eff8ff}
.cs{font-size:11.5px;color:#7a99b0;margin:8px 0 22px}
.tabs{display:flex;gap:4px;padding:4px;border-radius:10px;background:rgba(255,255,255,.05);margin-bottom:20px}
.tabs button{flex:1;padding:9px;border:0;border-radius:7px;background:none;color:#7a99b0;font-size:12px;cursor:pointer}
.tabs button.on{background:rgba(127,200,238,.16);color:#b6e4fa;font-weight:600}
.fld{display:block;margin-bottom:14px}
.fld span{display:block;font-size:10.5px;color:#7a99b0;margin-bottom:6px}
.fld input{width:100%;padding:11px 12px;border-radius:8px;background:rgba(255,255,255,.045);
  border:1px solid rgba(140,190,230,.16);font-size:12.5px;color:#e8f5ff;outline:none}
.fld input:focus{border-color:rgba(127,208,238,.55);background:rgba(127,208,238,.08)}
.row{display:flex;justify-content:space-between;align-items:center;font-size:11px;color:#7a99b0;margin:2px 0 18px}
.chk{display:flex;align-items:center;gap:7px;cursor:pointer}
.chk input{accent-color:#6fc4e8;width:12px;height:12px}
.lnk{color:#7a99b0;cursor:pointer;text-decoration:none}
.go{width:100%;padding:12px;border:0;border-radius:8px;cursor:pointer;font-size:13px;font-weight:700;
  background:linear-gradient(135deg,#8bd9f5,#4fa8d8);color:#04141f;letter-spacing:.03em;
  box-shadow:0 8px 24px rgba(79,168,216,.3)}
.or{position:relative;text-align:center;font-size:10px;color:#5f8197;margin:15px 0}
.or:before,.or:after{content:"";position:absolute;top:50%;width:44%;height:1px;background:rgba(120,170,205,.14)}
.or:before{left:0}.or:after{right:0}
.guest{width:100%;padding:11px;border-radius:8px;background:none;border:1px solid rgba(140,190,230,.2);
  color:#9dbdd2;font-size:12px;cursor:pointer}
.foot{font-size:9.5px;color:#5c7a8e;text-align:center;margin-top:18px;letter-spacing:.03em}
.previews{position:absolute;right:56px;top:50%;transform:translateY(-50%);width:330px;display:flex;flex-direction:column;gap:16px;z-index:4}
.pv{background:rgba(255,255,255,.86);border-radius:14px;padding:18px 18px 16px;border:1px solid #dfe6ee;
  box-shadow:0 18px 40px -18px rgba(20,45,75,.28);backdrop-filter:blur(8px)}
.pv .h{display:flex;justify-content:space-between;align-items:center;font-size:11px;color:#7c8fa1;margin-bottom:12px}
.pv .h b{font-size:12px;color:#132a3d;font-weight:600;letter-spacing:.02em}
.pv .n{font-size:26px;font-weight:700;color:#0e2233;letter-spacing:-.01em}
.pv .n em{font-style:normal;font-size:11px;font-weight:500;color:#8fa1b2;margin-left:5px}
.pv .bar{display:flex;align-items:flex-end;gap:4px;height:38px;margin-top:12px}
.pv .bar i{flex:1;background:linear-gradient(180deg,#7fc4e8,#3f86b8);border-radius:2px 2px 0 0;display:block}
.pv .up{font-size:11px;color:#c9482c;font-weight:600}
.pv.dk{background:rgba(14,34,51,.9);border-color:rgba(140,190,230,.18)}
.pv.dk .h b{color:#dcecf8}.pv.dk .h{color:#7a99b0}.pv.dk .n{color:#eaf5fd}
.pv.dk .n em{color:#7a99b0}
.pv.dk .bar i{background:linear-gradient(180deg,#f0a868,#c47a3c)}
.note{font-size:10px;color:#7c8fa1;letter-spacing:.04em;text-align:right;padding-right:4px}
'''

I_BODY = '''<div class="grid"></div><div class="blob b1"></div><div class="blob b2"></div>
<div class="hd">
  <div class="l"><b>ORBIS</b><i>EARTH DATA ATLAS</i></div>
  <div class="r"><span class="on">登录</span><span>注册</span><span>访客浏览</span></div>
</div>
<div class="scene">
  <div class="card">
    <div class="brand">__MINI__<b>ORBIS</b><i>v2.4</i></div>
    <h2>欢迎回来</h2>
    <p class="cs">登录以使用完整账户功能 · 游客可免费浏览</p>
    __TABS__
    __FIELDS__
    <p class="foot">继续即表示同意服务条款与隐私政策 · 管理员入口 /admin</p>
  </div>
</div>
<div class="previews">
  <div class="pv">
    <div class="h"><b>中国</b><span>GDP · 2025</span></div>
    <div class="n">$19.53<em>万亿</em></div>
    <div class="bar"><i style="height:38%"></i><i style="height:46%"></i><i style="height:55%"></i><i style="height:62%"></i><i style="height:74%"></i><i style="height:85%"></i><i style="height:94%"></i></div>
    <div class="up" style="margin-top:9px">↑ 4.8% 同比</div>
  </div>
  <div class="pv dk">
    <div class="h"><b>德国</b><span>人均寿命</span></div>
    <div class="n">81.2<em>岁</em></div>
    <div class="bar"><i style="height:52%"></i><i style="height:58%"></i><i style="height:64%"></i><i style="height:70%"></i><i style="height:76%"></i><i style="height:81%"></i><i style="height:88%"></i></div>
  </div>
  <div class="note">拖动地球即可查看任意国家 · 数据每周同步</div>
</div>'''
I_BODY = I_BODY.replace('__MINI__', globe(22, '#8fd0ff', '#3a82c8', '#123a6a', '#bfe2ff', .5, 18, 3, 4))
I_BODY = I_BODY.replace('__TABS__', TABS).replace('__FIELDS__', FIELDS)


# ============ J 瑞士色块 ============
J_CSS = '''
body{display:grid;grid-template-columns:520px 1fr;background:#fff}
.side{background:#10344e;position:relative;padding:46px 44px;display:flex;flex-direction:column;overflow:hidden}
.side .gl{position:absolute;right:-236px;bottom:-300px;opacity:.3}
.sq{width:26px;height:26px;background:#e8b04b}
.hd{display:flex;align-items:center;gap:14px;position:relative;z-index:3}
.hd b{font-size:13px;letter-spacing:.32em;color:#eaf4fb;font-weight:700}
.hd i{font-style:normal;font-size:9.5px;letter-spacing:.16em;color:#8fa9bd;margin-left:auto}
.big{margin-top:96px;position:relative;z-index:3}
.big h1{font-size:76px;line-height:1.06;letter-spacing:-.02em;color:#fff;font-weight:800}
.bar{width:64px;height:6px;background:#e8b04b;margin:28px 0 26px}
.big p{font-size:12.5px;line-height:1.9;color:#9fb8ca;max-width:340px;letter-spacing:.02em}
.lst{margin-top:auto;position:relative;z-index:3}
.lst div{display:grid;grid-template-columns:26px 1fr;gap:12px;padding:13px 0;border-top:1px solid rgba(160,195,220,.18);align-items:baseline}
.lst div:last-child{border-bottom:1px solid rgba(160,195,220,.18)}
.lst i{font-style:normal;font-size:9.5px;color:#e8b04b;font-weight:700;letter-spacing:.06em}
.lst b{font-size:12px;color:#ddecf6;font-weight:600;letter-spacing:.02em}
.lst small{display:block;font-size:10.5px;color:#87a3b8;margin-top:4px;font-weight:400}
.main{display:grid;place-items:center;position:relative;padding:0 80px}
.serial{position:absolute;top:42px;right:56px;font-size:10px;letter-spacing:.24em;color:#a8b4c0}
.serial b{color:#10344e}
.formbox{width:100%;max-width:420px}
.topline{display:flex;justify-content:space-between;align-items:flex-end;border-bottom:2px solid #10344e;padding-bottom:14px;margin-bottom:34px}
.tabs{display:flex;gap:30px}
.tabs button{background:none;border:0;cursor:pointer;padding:0;font-size:13px;letter-spacing:.16em;color:#a8b4c0}
.tabs button.on{color:#10344e;font-weight:800}
.topline span{font-size:9.5px;letter-spacing:.2em;color:#a8b4c0}
h2{font-size:40px;line-height:1.1;font-weight:800;color:#10344e;letter-spacing:-.01em;margin-bottom:12px}
.cs{font-size:12px;color:#8b97a3;margin-bottom:36px;letter-spacing:.02em}
.fld{display:block;margin-bottom:20px}
.fld span{display:block;font-size:9.5px;letter-spacing:.2em;color:#8b97a3;margin-bottom:8px}
.fld input{width:100%;padding:13px 14px;border:1.5px solid #10344e;border-radius:0;font-size:13px;color:#10344e;outline:none;background:#fff}
.fld input:focus{box-shadow:4px 4px 0 #e8b04b;background:#fdfbf6}
.row{display:flex;justify-content:space-between;align-items:center;font-size:11px;color:#8b97a3;margin:8px 0 26px}
.chk{display:flex;align-items:center;gap:8px;cursor:pointer}
.chk input{accent-color:#10344e;width:13px;height:13px}
.lnk{color:#10344e;cursor:pointer;text-decoration:none;border-bottom:1px solid #10344e;padding-bottom:1px}
.go{width:100%;padding:15px;background:#10344e;color:#fff;border:0;border-radius:0;cursor:pointer;
  font-size:12.5px;font-weight:800;letter-spacing:.2em}
.go:hover{background:#e8b04b;color:#10344e}
.or{text-align:center;font-size:9.5px;letter-spacing:.24em;color:#a8b4c0;margin:18px 0}
.guest{width:100%;padding:13px;background:#fff;border:1.5px solid #d8dee4;border-radius:0;color:#5a6773;
  font-size:11.5px;letter-spacing:.14em;cursor:pointer}
.guest:hover{border-color:#10344e;color:#10344e}
.foot{font-size:9.5px;color:#a8b4c0;margin-top:26px;line-height:1.9;letter-spacing:.04em}
.foot b{color:#10344e;font-weight:600}
'''

J_BODY = '''<div class="side">
  <div class="gl">__GLOBE__</div>
  <div class="hd"><span class="sq"></span><b>ORBIS</b><i>EST. 2024</i></div>
  <div class="big">
    <h1>从太空<br>看地球</h1>
    <div class="bar"></div>
    <p>200+ 国家的经济与人口数据，落在同一颗球面上。拖动它，看二十五年里一个国家如何改变形状。</p>
  </div>
  <div class="lst">
    <div><i>01</i><span><b>全球 200+ 国家</b><small>GDP · 人口 · 寿命 · 汇率实时数据</small></span></div>
    <div><i>02</i><span><b>对比与分享</b><small>链接记住状态，一键生成分享图</small></span></div>
    <div><i>03</i><span><b>变化提醒</b><small>关注国家数据大变，邮件自动通知</small></span></div>
  </div>
</div>
<div class="main">
  <div class="serial">01 / <b>SIGN IN</b></div>
  <div class="formbox">
    <div class="topline">
      <div class="tabs"><button class="on">登录</button><button>注册</button></div>
      <span>ORBIS ACCOUNT</span>
    </div>
    <h2>欢迎<br>回来</h2>
    <p class="cs">登录以使用完整账户功能 · 游客可免费浏览地球</p>
    __FIELDS__
    <p class="foot">继续即表示同意<b>服务条款</b>与<b>隐私政策</b><br>数据源：世界银行 WDI · Frankfurter · 管理员入口 /admin</p>
  </div>
</div>'''
J_BODY = J_BODY.replace('__GLOBE__', globe(720, '#67b0e0', '#1e5a8c', '#0a2439', '#bfe2ff', .2, 20, 6, 8))
J_BODY = J_BODY.replace('__FIELDS__', FIELDS)

FILES = [
    ('E_纸白编辑', E_CSS, E_BODY), ('F_深空聚焦', F_CSS, F_BODY), ('G_电影海报', G_CSS, G_BODY),
    ('H_双色分屏', H_CSS, H_BODY), ('I_网格浮卡', I_CSS, I_BODY), ('J_瑞士色块', J_CSS, J_BODY),
]
for name, css, body in FILES:
    io.open(os.path.join(OUT, name + '.html'), 'w', encoding='utf-8').write(doc(name, css, body))
    print('wrote', name)
