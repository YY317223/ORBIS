# -*- coding: utf-8 -*-
"""真正透视的 3D 沙盘效果图：倾斜立体板块 + 光照 + 城市立体标记（少而精）"""
import json, io, math

d = json.load(io.open('_base.json', encoding='utf-8'))
main, cities = d['main'], d['cities']
W, H = 680, 470

# 透视参数：绕 X 轴倾斜 TILT 角，焦距 F 决定近大远小强度
CX, CY = 340, 250
K = 8.2              # 水平比例
TILT = math.radians(34)
COST, SINT = math.cos(TILT), math.sin(TILT)
F = 420              # 焦距：越小透视越强
THICK = 20           # 板块厚度（像素）

def project(lon, lat):
    x = (lon - 105) * math.cos(math.radians(35)) * K
    y = -(lat - 36) * K           # 北为负、南为正
    # 倾斜后：南边(y大)离观察者近 → 分母小 → 放大
    persp = F / (F - y * SINT)
    sx = CX + x * persp
    sy = CY + y * COST * persp
    return sx, sy, persp

def ring_pts(pts):
    return [project(lo, la) for lo, la in pts]

def svg_path(pts, dy=0):
    return 'M' + ' '.join('%.1f,%.1f' % (x, y + dy) for x, y, _ in pts) + 'Z'

p = []
p.append('<svg viewBox="0 0 %d %d" width="100%%" xmlns="http://www.w3.org/2000/svg">' % (W, H))
p.append('<defs>')
p.append('<linearGradient id="top" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1d4a63"/><stop offset="0.55" stop-color="#14384e"/><stop offset="1" stop-color="#0d283a"/></linearGradient>')
p.append('<linearGradient id="side" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0d2a3d"/><stop offset="1" stop-color="#061722"/></linearGradient>')
p.append('<linearGradient id="col" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#a8642a"/><stop offset="0.45" stop-color="#ffd9a0"/><stop offset="1" stop-color="#c67d34"/></linearGradient>')
p.append('<radialGradient id="halo"><stop offset="0" stop-color="#4fd8e8" stop-opacity="0.35"/><stop offset="1" stop-color="#4fd8e8" stop-opacity="0"/></radialGradient>')
p.append('<filter id="g" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')
p.append('<filter id="gs" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="1.5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')
p.append('</defs>')
p.append('<rect width="%d" height="%d" fill="#040a12"/>' % (W, H))
# 背景氛围光
p.append('<ellipse cx="340" cy="270" rx="300" ry="180" fill="url(#halo)" opacity="0.3"/>')
# 地面网格（透视，在板块下方）
p.append('<g stroke="#123b52" stroke-width="0.5" opacity="0.35">')
for i in range(-6, 7):
    gx = CX + i * 55
    p.append('<line x1="%.1f" y1="90" x2="%.1f" y2="440"/>' % (gx, gx))
for i in range(9):
    gy = 110 + i * 38
    p.append('<line x1="40" y1="%.1f" x2="640" y2="%.1f"/>' % (gy, gy))
p.append('</g>')

pts = ring_pts(main)
# 1) 底部投影（悬浮感）
p.append('<path d="%s" fill="#000" opacity="0.35" transform="translate(6,44)"/>' % svg_path(pts))
# 2) 板块侧面：整块轮廓下移 THICK，先画底（露出的部分就是侧面）
p.append('<path d="%s" fill="url(#side)" stroke="#0a2030" stroke-width="0.8"/>' % svg_path(pts, THICK))
# 3) 板块顶面（受光面）
p.append('<path d="%s" fill="url(#top)" stroke="#f0a868" stroke-width="1.6" filter="url(#gs)"/>' % svg_path(pts))
# 4) 顶面上加一层高光边（北缘偏亮，模拟光照）
p.append('<path d="%s" fill="none" stroke="#ffd9a0" stroke-width="0.7" opacity="0.5" transform="translate(0,-1.5)"/>' % svg_path(pts))

# 城市：只让核心城市有立体柱，其余贴地光点
KEY = {'北京', '上海', '广州', '深圳', '重庆', '成都', '武汉', '西安', '杭州', '沈阳', '乌鲁木齐', '拉萨'}
# 按人口排序，重要的后画（压在上层）
major = [c for c in cities if c['n'] in KEY]
minor = [c for c in cities if c['n'] not in KEY]

def draw_minor(ct):
    x, y, sc = project(ct['lo'], ct['la'])
    r = 1.3 + math.log10(1 + ct['p'] / 1e5) * 0.5
    p.append('<ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f" fill="#5fd0e8" opacity="0.55"/>' % (x, y, r, r * 0.6))
    p.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="#b8f0ff" opacity="0.9"/>' % (x, y - 1, r * 0.6))

def draw_major(ct):
    x, y, sc = project(ct['lo'], ct['la'])
    h = (12 + math.log10(1 + ct['p'] / 1e5) * 17) * sc
    w = 5.5 * sc
    cap = bool(ct.get('c'))
    col = 'col' if cap else 'col'
    # 投影阴影（斜向右下）
    p.append('<ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f" fill="#000" opacity="0.3"/>' % (x + h * 0.3, y + 2, w * 0.9, w * 0.3))
    # 柱体（梯形：顶部略窄，强化透视）
    p.append('<path d="M%.1f,%.1f L%.1f,%.1f L%.1f,%.1f L%.1f,%.1f Z" fill="url(#%s)"/>' % (
        x - w/2, y, x + w/2, y, x + w*0.35, y - h, x - w*0.35, y - h, col))
    # 顶面
    p.append('<ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f" fill="#ffe4b8" filter="url(#g)"/>' % (x, y - h, w*0.35, w*0.16))
    # 地面基座
    p.append('<ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f" fill="none" stroke="#ffd9a0" stroke-width="0.9" opacity="0.75"/>' % (x, y, w*0.9, w*0.3))
    # 标注（仅前 8）
    if ct['n'] in {'北京','上海','广州','深圳','重庆','成都','武汉','乌鲁木齐'}:
        tw = len(ct['n']) * 10 + 8
        lx, ly = x + 8, y - h - 6
        if lx + tw > W - 10: lx = x - tw - 8
        p.append('<path d="M%.1f,%.1f L%.1f,%.1f" stroke="#8ab6cc" stroke-width="0.6" opacity="0.7"/>' % (x, y-h, lx if lx>x else lx+tw, ly+6))
        p.append('<rect x="%.1f" y="%.1f" width="%d" height="15" rx="3" fill="#081725" stroke="#2b6a85" stroke-width="0.6" opacity="0.93"/>' % (lx, ly-5, tw))
        p.append('<text x="%.1f" y="%.1f" fill="#d8f0fb" font-size="10.5" font-family="sans-serif">%s</text>' % (lx+4, ly+6, ct['n']))

for ct in sorted(minor, key=lambda c: c['la']):
    draw_minor(ct)
for ct in sorted(major, key=lambda c: c['la']):
    draw_major(ct)

# 标题 + 图例
p.append('<rect x="20" y="18" width="212" height="28" rx="5" fill="#081725" stroke="#1d4a63" stroke-width="0.6"/>')
p.append('<circle cx="35" cy="32" r="3" fill="#7fe8ff" filter="url(#g)"/>')
p.append('<text x="46" y="36" fill="#cfe8f5" font-size="12" font-family="sans-serif">中国 · 城市 3D 沙盘</text>')
p.append('<rect x="20" y="425" width="330" height="34" rx="5" fill="#081725" stroke="#1d4a63" stroke-width="0.6"/>')
p.append('<rect x="32" y="435" width="4" height="13" fill="#ffd9a0"/>')
p.append('<text x="42" y="446" fill="#9fc4d8" font-size="10" font-family="sans-serif">首都/核心城市 · 立体柱</text>')
p.append('<circle cx="220" cy="441" r="2.5" fill="#7fe8ff"/>')
p.append('<text x="230" y="445" fill="#9fc4d8" font-size="10" font-family="sans-serif">其他城市 · 光点</text>')
p.append('<text x="660" y="446" text-anchor="end" fill="#5f8298" font-size="10" font-family="sans-serif">真实坐标与人口 · 透视投影</text>')
p.append('</svg>')

svg = ''.join(p)
io.open('_sandbox.svg', 'w', encoding='utf-8').write(svg)
html = '<!DOCTYPE html><html><head><meta charset=utf-8><style>*{margin:0;padding:0}body{background:#040a12;width:%dpx;height:%dpx;overflow:hidden}svg{width:100%%;height:100%%}</style></head><body>%s</body></html>' % (W, H, svg)
io.open('_sandbox.html', 'w', encoding='utf-8').write(html)
print('sandbox generated, len', len(svg))
