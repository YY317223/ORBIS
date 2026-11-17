# -*- coding: utf-8 -*-
"""构建「世界即卡片」原型所需的内联地理 + 指标数据集。

输出: ../data.js  (window.ATLAS_DATA = {...})
数据源:
  - 矢量边界: world-atlas / Natural Earth 1:110m (public domain)，仅作数据可视化示意
  - 指标: World Bank World Development Indicators (API)
  - 中文国名: i18n-iso-countries / ISO 3166
合规处理: 台湾(158)几何并入中国(156)、港澳本已包含在中国要素内、剔除南极洲、
          争议/非正式条目不参与交互、界面显式标注中国领土表述与示意性边界声明。
"""
import base64, json, math, os, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
from geo_anchor import anchor_from_ll
from city_pick import pick_cities, is_district
from geo_anchor import anchor_from_ll
from city_pick import pick_cities, is_district

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE, "raw")
OUT = os.path.join(BASE, "..", "data.js")
os.makedirs(RAW, exist_ok=True)

YEARS = list(range(2000, 2024))

INDICATORS = {
    "gdp": "NY.GDP.MKTP.CD",
    "pc":  "NY.GDP.PCAP.CD",
    "pop": "SP.POP.TOTL",
    "le":  "SP.DYN.LE00.IN",
    "a0":  "SP.POP.0014.TO.ZS",
    "a65": "SP.POP.65UP.TO.ZS",
    "urb": "SP.URB.TOTL.IN.ZS",
}

REGION_ZH = {
    "East Asia & Pacific": "东亚与太平洋",
    "Europe & Central Asia": "欧洲与中亚",
    "Latin America & Caribbean": "拉美与加勒比",
    "Middle East & North Africa": "中东与北非",
    "Middle East, North Africa, Afghanistan & Pakistan": "中东、北非与南亚",
    "North America": "北美",
    "South Asia": "南亚",
    "Sub-Saharan Africa": "撒哈拉以南非洲",
    "Aggregates": "全球",
}
INCOME_ZH = {
    "High income": "高收入",
    "Upper middle income": "中高收入",
    "Lower middle income": "中低收入",
    "Low income": "低收入",
    "Aggregates": "—",
}

# 中国官方表述相关 / Natural Earth 中不是标准 ISO 条目的名称修正
NAME_FIX = {
    "China": "中国", "Taiwan": "中国台湾",
    "Hong Kong S.A.R.": "中国香港", "Macao S.A.R.": "中国澳门",
    "W. Sahara": "西撒哈拉", "N. Cyprus": "北塞浦路斯",
    "Somaliland": "索马里兰", "Kosovo": "科索沃",
    "Dem. Rep. Congo": "刚果（金）", "Congo": "刚果（布）",
    "United States of America": "美国", "United Kingdom": "英国",
    "Russian Federation": "俄罗斯", "Korea, Rep.": "韩国",
    "Korea, Dem. Rep.": "朝鲜", "Iran, Islamic Rep.": "伊朗",
    "Viet Nam": "越南", "Lao PDR": "老挝", "Syrian Arab Republic": "叙利亚",
    "Türkiye": "土耳其", "Czechia": "捷克", "Slovak Republic": "斯洛伐克",
}
NON_ISO = {"N. Cyprus", "Somaliland", "Kosovo", "Hong Kong"}   # 不作为可选国家呈现（港澳台属中国，香港不单列）


def fetch(name, url):
    p = os.path.join(RAW, name)
    if not os.path.exists(p) or os.path.getsize(p) < 200:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=180) as r:
            data = r.read()
        with open(p, "wb") as f:
            f.write(data)
    with open(p, "rb") as f:
        return f.read()


# ---------------------------------------------------------------- 1. 抓取原始数据
jobs = {
    "topo10.json": "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-10m.json",
    "iso.json": "https://cdn.jsdelivr.net/gh/lukes/ISO-3166-Countries-with-Regional-Codes@master/all/all.json",
    "zh.json": "https://cdn.jsdelivr.net/npm/i18n-iso-countries@7.14.0/langs/zh.json",
    "wb_meta.json": "https://api.worldbank.org/v2/country?format=json&per_page=400",
}
for key, code in INDICATORS.items():
    jobs["wb_%s.json" % key] = (
        "https://api.worldbank.org/v2/country/all/indicator/%s?date=2000:2023&format=json&per_page=20000" % code
    )

print("fetching %d resources ..." % len(jobs))
with ThreadPoolExecutor(max_workers=8) as ex:
    results = list(ex.map(lambda kv: (kv[0], fetch(kv[0], kv[1])), jobs.items()))
raw = dict(results)
for k, v in raw.items():
    print("  %-18s %8d B" % (k, len(v)))

topo = json.loads(raw["topo10.json"])
iso_list = json.loads(raw["iso.json"])
zh = json.loads(raw["zh.json"])["countries"]
wb_meta = json.loads(raw["wb_meta.json"])[1]

num2a3, num2a2 = {}, {}
for row in iso_list:
    code = str(row.get("country-code", "")).zfill(3)
    num2a3[code] = row.get("alpha-3")
    num2a2[code] = row.get("alpha-2")

wb_by_iso = {c["id"]: c for c in wb_meta}   # World Bank country.id = ISO alpha-3


def zh_name(num, en):
    if en in NAME_FIX:
        return NAME_FIX[en]
    a2 = num2a2.get(num)
    if a2 and a2 in zh:
        return zh[a2]
    return en


def flag_emoji(a2):
    if not a2 or len(a2) != 2:
        return ""
    return "".join(chr(0x1F1E6 + ord(c) - 65) for c in a2.upper())


FLAGDIR = os.path.join(RAW, "flags")
os.makedirs(FLAGDIR, exist_ok=True)


def flag_uri(a2):
    """内联极小的国旗 PNG；Windows 不渲染区域指示符 emoji，故不用 emoji 作国旗。"""
    if not a2 or len(a2) != 2:
        return ""
    p = os.path.join(FLAGDIR, a2.lower() + ".png")
    if not os.path.exists(p):
        try:
            req = urllib.request.Request("https://flagcdn.com/w40/%s.png" % a2.lower(),
                                         headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=25) as r:
                blob = r.read()
            if len(blob) < 60:
                return ""
            with open(p, "wb") as f:
                f.write(blob)
        except Exception:
            return ""
    with open(p, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")


# ---------------------------------------------------------------- 2. 指标整理
wb = {}
for key in INDICATORS:
    d = json.loads(raw["wb_%s.json" % key])
    rows = d[1] if len(d) > 1 and d[1] else []
    series = {}
    for r in rows:
        iso = r.get("countryiso3code")
        yr = int(r["date"])
        val = r["value"]
        if not iso or yr not in YEARS:
            continue
        series.setdefault(iso, {})[yr] = round(val, 4) if isinstance(val, (int, float)) else None
    wb[key] = series
    print("  indicator %-4s %4d economies" % (key, len(series)))


def arr(series, iso, ndigits=2):
    s = series.get(iso, {})
    return [None if s.get(y) is None else round(s[y], ndigits) for y in YEARS]


def last(series, iso, start=2015):
    s = series.get(iso, {})
    for y in range(YEARS[-1], start - 1, -1):
        if s.get(y) is not None:
            return round(s[y], 2), y
    return None, None


# WLD 聚合作为「全球参照系」
world = {k: arr(wb[k], "WLD") for k in ("gdp", "pc", "pop", "le")}
for k in ("a0", "a65", "urb"):
    world[k] = {"v": last(wb[k], "WLD")[0], "y": last(wb[k], "WLD")[1]}


# ---------------------------------------------------------------- 3. TopoJSON 解码 + Robinson 投影
# Robinson 投影系数表 (纬度 0..90，每 5°)
RX = [1.0000, .9986, .9954, .9900, .9822, .9730, .9600, .9427, .9216, .8962,
      .8679, .8350, .7986, .7597, .7186, .6732, .6213, .5722, .5322]
RY = [0.0000, .0620, .1240, .1860, .2480, .3100, .3720, .4340, .4958, .5571,
      .6176, .6769, .7346, .7903, .8435, .8936, .9394, .9761, 1.0000]


def robinson(lon, lat):
    a = min(abs(lat), 90.0)
    i = min(int(a // 5), 17)
    f = (a - i * 5) / 5.0
    X = RX[i] + (RX[i + 1] - RX[i]) * f
    Y = RY[i] + (RY[i + 1] - RY[i]) * f
    x = 0.8487 * X * math.radians(lon)
    y = 1.3523 * Y * (1 if lat >= 0 else -1)
    return x, y


scale = topo["transform"]["scale"]
translate = topo["transform"]["translate"]
decoded = []
for arc in topo["arcs"]:
    x = y = 0
    pts = []
    for dx, dy in arc:
        x += dx
        y += dy
        pts.append((x * scale[0] + translate[0], y * scale[1] + translate[1]))
    decoded.append(pts)


def arc_points(idx):
    if idx < 0:
        return decoded[~idx][::-1]
    return decoded[idx]


def ring_points(ring):
    pts = []
    for a in ring:
        seg = arc_points(a)
        if pts:
            seg = seg[1:]
        pts.extend(seg)
    return pts


def polygons_of(geom):
    if geom["type"] == "Polygon":
        return [geom["arcs"]]
    return geom["arcs"]


def split_antimeridian(lonlat):
    """把跨越 ±180° 经线的环切开，避免投影后出现横贯全图的色带。
    Natural Earth 的俄罗斯 / 斐济等要素包含 (±180, lat) 相邻点，
    直接连线会在 Robinson 投影下被拉成一条横跨地图的水平长条。"""
    segs, cur = [], []
    for i, pt in enumerate(lonlat):
        if cur and abs(pt[0] - lonlat[i - 1][0]) > 180:
            if len(cur) >= 3:
                segs.append(cur)
            cur = []
        cur.append(pt)
    if len(cur) >= 3:
        segs.append(cur)
    return segs


geoms = topo["objects"]["countries"]["geometries"]
# 合规: 台湾(158) 并入中国(156)
def _as_polygons(geom):
    return [geom["arcs"]] if geom["type"] == "Polygon" else geom["arcs"]
china = next(g for g in geoms if g.get("id") == "156")
taiwan = next(g for g in geoms if g.get("id") == "158")
china["type"] = "MultiPolygon"
china["arcs"] = _as_polygons(china) + _as_polygons(taiwan)
geoms = [g for g in geoms if g.get("id") not in ("158", "010")]  # 去台湾条目、去南极洲

# 先收集所有经纬度点，求投影包围盒，再一次拟合到 viewBox
flat = []
for g in geoms:
    for poly in polygons_of(g):
        for ring in poly:
            flat.extend(ring_points(ring))
proj_all = [robinson(lon, lat) for lon, lat in flat]
minx = min(p[0] for p in proj_all); maxx = max(p[0] for p in proj_all)
miny = min(p[1] for p in proj_all); maxy = max(p[1] for p in proj_all)
W, H, PAD = 1000.0, 480.0, 18.0
S = min((W - 2 * PAD) / (maxx - minx), (H - 2 * PAD) / (maxy - miny))
OX = (W - (maxx - minx) * S) / 2 - minx * S
OY = (H - (maxy - miny) * S) / 2 + maxy * S


def px(lon, lat):
    x, y = robinson(lon, lat)
    return x * S + OX, OY - y * S


def inv_robinson(pxx, pyy):
    """把投影后的坐标反解回 (lon, lat)，用于球面上定位国家质心。"""
    yv = (OY - pyy) / S / 1.3523
    ay = min(max(abs(yv), 0.0), 1.0)
    i = 17
    for k in range(17):
        if RY[k] <= ay <= RY[k + 1]:
            i = k
            break
    span = (RY[i + 1] - RY[i]) or 1.0
    f = (ay - RY[i]) / span
    lat = (i + f) * 5.0 * (1 if yv >= 0 else -1)
    X = RX[i] + (RX[i + 1] - RX[i]) * f
    lon = math.degrees(((pxx - OX) / S) / (0.8487 * X)) if X else 0.0
    return round(lon, 3), round(lat, 3)


def polygon_centroid(pts):
    a = cx = cy = 0.0
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]; x1, y1 = pts[i + 1]
        cr = x0 * y1 - x1 * y0
        a += cr; cx += (x0 + x1) * cr; cy += (y0 + y1) * cr
    if abs(a) < 1e-9:
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        return (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    return cx / (3 * a), cy / (3 * a)


# 并行内联国旗（失败则回退到 ISO 代码徽标）
a2s = sorted({num2a2.get(str(g.get("id", "")).zfill(3)) for g in geoms if g.get("id")} - {None})
with ThreadPoolExecutor(max_workers=16) as ex:
    flagmap = dict(zip(a2s, ex.map(flag_uri, a2s)))
print("inline flags:", sum(1 for v in flagmap.values() if v), "/", len(a2s))

def unwrap_ring(lonlat):
    """把环的经度连续化：跨 ±180° 的点依次加减 360°，避免绘制时被拉成横贯图幅的色带。
    返回值中的经度可能超出 [-180,180]，绘制方按 -360/0/+360 三次平移即可正确回绕。"""
    out, prev = [], None
    for lon, lat in lonlat:
        if prev is not None:
            while lon - prev > 180:
                lon -= 360
            while lon - prev < -180:
                lon += 360
        out.append((lon, lat))
        prev = lon
    return out


# ---------------------------------------------------------------- 城市（Natural Earth 1:10m populated places）
CITYF = os.path.join(RAW, "ne_places10m.geojson")
CITY_MAP = {}          # iso3 -> [city, ...]

# Natural Earth 的 NAME_ZH 实际为繁体，统一转简体
try:
    from opencc import OpenCC
    _t2s = OpenCC("t2s").convert
except Exception as _e:
    print("!! opencc 不可用，城市名将保留繁体:", _e)
    _t2s = lambda s: s
try:
    gj = json.loads(open(CITYF, encoding="utf-8").read()) if os.path.exists(CITYF) else None
except Exception as _e:
    print("!! 城市数据未就绪（可能仍在下载）:", _e)
    gj = None
if gj:
    bucket = {}
    for ft in gj.get("features", []):
        pr = ft.get("properties", {})
        a3 = (pr.get("ADM0_A3") or "").upper()
        sub_region = a3 in ("TWN", "HKG", "MAC")
        if sub_region:
            a3 = "CHN"          # 合规：台湾、香港、澳门属中国
        co = ft.get("geometry", {}).get("coordinates")
        if not co or not a3:
            continue
        pop = pr.get("POP_MAX") or pr.get("POP_MIN") or 0
        nm_zh = _t2s((pr.get("NAME_ZH") or "").strip())
        nm_en = (pr.get("NAME") or "").strip()
        feat = (pr.get("FEATURECLA") or "")
        cap = 1 if (pr.get("ADM0CAP") == 1 or "Admin-0 capital" in feat) else 0
        adm1 = 1 if "Admin-1 capital" in feat else 0
        if sub_region:
            # 合规：台湾/香港/澳门属中国，其城市不作国家级首都标记
            cap = 0
            adm1 = 0          # 也不作省级中心计数
        # 过滤掉没有人口、也没有首都身份的极小居民点，避免地图上堆点
        if not cap and (not pop or pop < 30000):
            continue
        # 县 / 区级条目（莎车县、海拉尔区…）不是城市，会顶掉真正的地级市
        if a3 in ("CHN", "TWN") and is_district(nm_zh):
            continue
        bucket.setdefault(a3, []).append({
            "n": nm_zh or nm_en, "e": nm_en, "lo": round(co[0], 3), "la": round(co[1], 3),
            "p": int(pop) if pop else 0, "c": cap, "r": adm1,
        })
    for a3, lst in bucket.items():
        lst.sort(key=lambda x: (-x["c"], -x["p"]))
        CITY_MAP[a3] = lst          # 全量保留，选点在下方按国家面积做
    print("cities:", sum(len(v) for v in CITY_MAP.values()), "for", len(CITY_MAP), "countries",
          "| with zh name:", sum(1 for v in CITY_MAP.values() for c in v if c["n"] != c["e"]))
else:
    print("!! 缺少", CITYF, "：城市层将为空")

countries = []
for g in geoms:
    num = str(g.get("id", "")).zfill(3) if g.get("id") else ""
    en = g.get("properties", {}).get("name", "")
    iso3 = num2a3.get(num) if num else None
    a2 = num2a2.get(num) if num else None
    parts = []
    biggest, biggest_area = None, -1
    ll = []
    for poly in polygons_of(g):
        for ring in poly:
            # --- 经纬度环（球面着色 / 国界 / 国家详图用），经度连续化后量化到 0.1°
            ur = unwrap_ring(ring_points(ring))
            if len(ur) >= 3:
                # 阈值随环的尺度自适应：微型国家保住形状，大国强抽稀控体积
                xs = [p[0] for p in ur]; ys = [p[1] for p in ur]
                span = max(max(xs) - min(xs), max(ys) - min(ys))
                tol = 0.012 if span < 1.5 else 0.03 if span < 6 else 0.08 if span < 22 else 0.16
                q = [ur[0]]
                for pt in ur[1:]:
                    if abs(pt[0] - q[-1][0]) + abs(pt[1] - q[-1][1]) >= tol:
                        q.append(pt)
                if len(q) >= 3:
                    if q[0] != q[-1]:
                        q.append(q[0])
                    # 0.01° 量化（约 1 km），否则小国会被压成矩形
                    x0 = int(round((q[0][0] + 180) * 100))
                    y0 = int(round((90 - q[0][1]) * 100))
                    flat = [x0, y0]
                    px_, py_ = x0, y0
                    for lon2, lat2 in q[1:]:
                        nx = int(round((lon2 + 180) * 100))
                        ny = int(round((90 - lat2) * 100))
                        flat.append(nx - px_)
                        flat.append(ny - py_)
                        px_, py_ = nx, ny
                    ll.append(flat)
            for seg in split_antimeridian(ring_points(ring)):
                pts = [px(lon, lat) for lon, lat in seg]
                if len(pts) < 3:
                    continue
                # 去重 + 精度压缩
                clean = [pts[0]]
                for p in pts[1:]:
                    if abs(p[0] - clean[-1][0]) + abs(p[1] - clean[-1][1]) >= 0.28:
                        clean.append(p)
                if len(clean) < 3:
                    continue
                d = "M" + "L".join("%.1f,%.1f" % (x, y) for x, y in clean) + "Z"
                parts.append(d)
                area = abs(sum(clean[i][0] * clean[i + 1][1] - clean[i + 1][0] * clean[i][1]
                               for i in range(len(clean) - 1)))
                if area > biggest_area:
                    biggest_area, biggest = area, clean
    if not parts:
        continue
    cx, cy = polygon_centroid(biggest) if biggest else (0, 0)
    # 锚点（国名标注 / 聚焦中心）用「视觉中心」：主陆块内最大内切栅格点，
    # 顶点平均会把克罗地亚、格鲁吉亚这类新月形国家的中心甩进邻国。
    clon, clat, ar_deg = anchor_from_ll(ll)
    meta = wb_by_iso.get(iso3, {}) if iso3 else {}
    reg = (meta.get("region", {}).get("value", "") or "").strip()
    inc = (meta.get("incomeLevel", {}).get("value", "") or "").strip()
    a0v, a0y = last(wb["a0"], iso3) if iso3 else (None, None)
    a65v, _ = last(wb["a65"], iso3) if iso3 else (None, None)
    urbv, _ = last(wb["urb"], iso3) if iso3 else (None, None)
    countries.append({
        "id": num, "iso3": iso3 or "", "n": zh_name(num, en), "en": en,
        "flag": flag_emoji(a2), "fi": flagmap.get(a2, ""),
        "reg": REGION_ZH.get(reg, reg or "其他"),
        "inc": INCOME_ZH.get(inc, inc or "—"),
        "p": "".join(parts), "cx": round(cx, 1), "cy": round(cy, 1), "ar": ar_deg,
        "clon": clon, "clat": clat, "ard": ar_deg,
        "ll": ll, "city": [{k: v for k, v in x.items() if k != "r"} for x in
                            pick_cities(CITY_MAP.get(iso3 or "", []), ar_deg)],
        "gdp": arr(wb["gdp"], iso3), "pc": arr(wb["pc"], iso3),
        "pop": arr(wb["pop"], iso3), "le": arr(wb["le"], iso3, 2),
        "age": [a0v, None if a0v is None or a65v is None else round(100 - a0v - a65v, 2), a65v],
        "a0y": a0y, "urb": urbv,
        "off": en in NON_ISO,     # 非正式条目: 仅作底图形状，不参与点击
    })

countries.sort(key=lambda c: c["n"])

# 大洲归属（AS/EU/AF/NA/SA/OC/AN），供「洲 → 国 → 城」三级下钻使用
try:
    import continents as _cont
    _tally = _cont.assign(countries)
    print("continents:", dict(sorted(_tally.items(), key=lambda kv: -kv[1])))
except Exception as _e:      # 缺 wc_continents.json 时降级，界面仍可运行
    for c in countries:
        c.setdefault("cn", "AS")
    print("!! 大洲归属缺失:", _e)
print("countries:", len(countries), "| with GDP:", sum(1 for c in countries if c["gdp"][-1]))


# ---------------------------------------------------------------- 4. 输出
data = {
    "meta": {
        "years": YEARS,
        "updated": "2026-10-08",
        "projection": "Robinson",
        "viewBox": [0, 0, int(W), int(H)],
        "fit": {"S": round(S, 6), "OX": round(OX, 4), "OY": round(OY, 4),
                "W": W, "H": H},
        "sources": [
            "World Bank · World Development Indicators（GDP / 人均 GDP / 人口 / 预期寿命 / 年龄结构 / 城镇化率）",
            "Natural Earth 1:10m via world-atlas（边界矢量，仅作数据可视化示意）",
        "Natural Earth 1:10m populated places（城市点与人口，中文名经繁简转换）",
        ],
        "indicators": [
            {"k": "gdp", "n": "GDP 总量", "unit": "美元", "code": "NY.GDP.MKTP.CD"},
            {"k": "pc",  "n": "人均 GDP", "unit": "美元", "code": "NY.GDP.PCAP.CD"},
            {"k": "pop", "n": "人口", "unit": "人", "code": "SP.POP.TOTL"},
            {"k": "le",  "n": "预期寿命", "unit": "岁", "code": "SP.DYN.LE00.IN"},
        ],
    },
    "world": world,
    "countries": countries,
}
with open(OUT, "w", encoding="utf-8") as f:
    f.write("window.ATLAS_DATA = ")
    json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    f.write(";\n")
print("wrote", os.path.abspath(OUT), os.path.getsize(OUT), "bytes")
