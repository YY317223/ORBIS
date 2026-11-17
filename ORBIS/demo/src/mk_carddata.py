# -*- coding: utf-8 -*-
"""为国别卡片（搭档那版地球里的右侧档案卡）生成一份精简数据。

用法：
    python build/mk_carddata.py

输入：
    build/app_data.json   26 年 × 12 指标（Atlas 的库）
    build/wld.json        全球合计 / 人均 / 预期寿命
    build/flags.json      国旗（base64 PNG）
    build/adm.json        一级行政区（只取「叫什么」和「几个」）
    build/world110.json   topojson，用来算陆地邻国
输出：
    build/card_data.js    window.__PCARD__ = {...}

为什么要单独生成一份：
    index.html 里那份是给整个 Atlas 用的（含地级市几何、时间轴状态等）。
    演示版只需要「一个国家 + 26 年 + 邻国」，拎出来 230KB 左右，
    直接内联进 orbis_demo.html，双击就能跑，不依赖任何接口。
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = lambda *p: os.path.join(ROOT, 'build', *p)
OUT = B('card_data.js')


def load(name):
    with open(B(name), encoding='utf-8') as f:
        return json.load(f)


data = load('app_data.json')
wld = load('wld.json')
flags = load('flags.json')
adm = load('adm.json')
topo = load('world110.json')

index, series = data['index'], data['series']

# ---- 数字 id → ISO3（topojson 里几何只有数字 id）----
num2iso = {}
for k, v in index.items():
    if v.get('num'):
        num2iso[str(v['num'])] = k


def arcs_of(geom):
    """把 Polygon / MultiPolygon 的 arcs 拍平成一串环索引。"""
    out = set()

    def walk(a):
        if isinstance(a, list):
            for x in a:
                walk(x)
        elif isinstance(a, int):
            out.add(a if a >= 0 else ~a)

    walk(geom.get('arcs') or [])
    return out


geoms = topo['objects']['countries']['geometries']
arcsets = []
for g in geoms:
    arcsets.append(arcs_of(g))

# 共用同一条弧 = 接壤（topojson.neighbors 的判据）
nei = {}
for i, g in enumerate(geoms):
    iso = num2iso.get(str(g.get('id')))
    if not iso:
        continue
    hit = []
    a = arcsets[i]
    if a:
        for j, other in enumerate(geoms):
            if j == i or not (a & arcsets[j]):
                continue
            k = num2iso.get(str(other.get('id')))
            if k and k != iso and k in series:
                hit.append(k)
    nei[iso] = sorted(set(hit))

# ---- 一级行政区（卡片上「进入 xx · n 个区域」那行）----
sub = {}
for iso, v in adm.items():
    lv1 = v.get('lv1') or []
    if lv1:
        sub[iso] = {'u': v.get('u') or '一级行政区', 'n': len(lv1)}

keep_series = ['gdp', 'pop', 'life', 'gdppc', 'g14', 'g65', 'urb', 'growth', 'co2', 'fert', 'g14y', 'g65y']
slim_series = {}
for iso, s in series.items():
    slim_series[iso] = {k: s.get(k) for k in keep_series}

out = {
    'years': data['years'],
    'index': {k: {kk: v.get(kk) for kk in ('zh', 'en', 'iso2', 'num', 'r', 'i', 'na')} for k, v in index.items()},
    'series': slim_series,
    'wld': {'gdp': wld['gdp'], 'pc': wld['pc'], 'lp': wld['lp'], 'pd': wld['pd']},
    'flags': flags,
    'nei': nei,
    'sub': sub,
}

js = 'window.__PCARD__ = ' + json.dumps(out, ensure_ascii=False, separators=(',', ':')) + ';\n'
with open(OUT, 'w', encoding='utf-8') as f:
    f.write(js)

print('%s  %.1f KB' % (os.path.relpath(OUT, ROOT), len(js.encode()) / 1024))
print('国家 %d / 有邻国 %d / 有一级行政区 %d' % (len(slim_series), sum(1 for v in nei.values() if v), len(sub)))
print('俄罗斯邻国：', ' '.join(nei.get('RUS', [])))
