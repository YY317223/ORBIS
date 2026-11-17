# -*- coding: utf-8 -*-
"""给每个国家补一个「大洲」归属（cn 字段：AS/EU/AF/NA/SA/OC/AN）。

数据源: world-countries (npm, ODbL) 的 region + subregion，按 ISO3 / ISO2 / 英文名匹配。
匹配不上的少量 Natural Earth 边角条目（军事基地、缓冲带、冰川等）用 CONT_FIX 人工指定。
可直接运行，对 ../data.js 做增量修补；build_data.py 也会 import 复用同一套规则。
"""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE, "raw")
DATA = os.path.join(BASE, "..", "data.js")
WC_FILE = os.path.join(RAW, "wc_continents.json")

# Natural Earth 里的非标准条目：ISO 与英文名都对不上时人工指定
CONT_FIX = {
    "Akrotiri": "EU",
    "Dhekelia": "EU",
    "Cyprus U.N. Buffer Zone": "EU",
    "N. Cyprus": "EU",
    "Kosovo": "EU",
    "Baikonur": "AS",
    "Siachen Glacier": "AS",
    "Indian Ocean Ter.": "OC",
    "USNB Guantanamo Bay": "NA",
    "Somaliland": "AF",
    "S. Geo. and the Is.": "AN",
    "Fr. S. Antarctic Lands": "AN",
    "Heard I. and McDonald Is.": "AN",
    "Antarctica": "AN",
}


def load_wc():
    with open(WC_FILE, encoding="utf-8") as f:
        wc = json.load(f)
    by3, by2, byname = {}, {}, {}
    for w in wc:
        if w.get("cca3"):
            by3[w["cca3"]] = w
        if w.get("cca2"):
            by2[w["cca2"]] = w
        nm = (w.get("name", {}) or {}).get("common", "")
        if nm:
            byname[nm.lower()] = w
    return by3, by2, byname


def to_cont(w):
    """world-countries 的 region/subregion → 六大洲。"""
    if not w:
        return None
    reg = (w.get("region") or "").strip()
    sub = (w.get("subregion") or "").strip()
    if reg == "Antarctic":
        return "AN"
    if reg == "Africa":
        return "AF"
    if reg == "Asia":
        return "AS"
    if reg == "Europe":
        return "EU"
    if reg == "Oceania":
        return "OC"
    if reg == "Americas":
        return "SA" if sub == "South America" else "NA"
    return None


def build_map(countries):
    """返回 ISO3/英文名 → 大洲代码 的解析函数结果字典。"""
    by3, by2, byname = load_wc()
    out = {}
    for c in countries:
        iso3 = c.get("iso3") or ""
        en = c.get("en") or ""
        code = None
        if iso3:
            code = to_cont(by3.get(iso3) or by2.get(iso3))
        if not code and en:
            code = to_cont(byname.get(en.lower()))
        if not code:
            code = CONT_FIX.get(en)
        out[c.get("id") or c.get("n")] = code or "AS"
    return out


# 有主权争议或属「自由联合」政治实体，一律不打「属地」标签，避免政治定性
DEP_NO_TAG = {"PSE", "ESH", "FLK", "COK", "NIU"}


def dep_set(countries):
    """返回「非主权属地」的键集合（Bermuda、Greenland、Cayman…）。

    world-countries 的 independent 字段为 False 即视为属地/非主权经济体；
    它们在世界银行里是独立统计的经济体，数值本身没错，但和主权国家同榜会让人误解。
    """
    by3, by2, byname = load_wc()
    out = set()
    for c in countries:
        iso3 = c.get("iso3") or ""
        en = c.get("en") or ""
        w = by3.get(iso3) or by2.get(iso3) or byname.get(en.lower())
        if iso3 in DEP_NO_TAG:
            continue
        if w and w.get("independent") is False:
            out.add(c.get("id") or c.get("n"))
    return out


def assign(countries):
    """就地给每个国家写 cn / dep 字段，返回每个大洲的国家数。"""
    m = build_map(countries)
    d = dep_set(countries)
    tally = {}
    for c in countries:
        k = c.get("id") or c.get("n")
        c["cn"] = m.get(k, "AS")
        if k in d:
            c["dep"] = 1
        else:
            c.pop("dep", None)
        tally[c["cn"]] = tally.get(c["cn"], 0) + 1
    return tally


def patch_data_js():
    with open(DATA, encoding="utf-8") as f:
        txt = f.read()
    i = txt.index("{")
    j = txt.rindex("}")
    data = json.loads(txt[i:j + 1])
    tally = assign(data["countries"])
    body = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    with open(DATA, "w", encoding="utf-8") as f:
        f.write("window.ATLAS_DATA = " + body + ";\n")
    print("patched", os.path.abspath(DATA), os.path.getsize(DATA), "bytes")
    print("continents:", dict(sorted(tally.items(), key=lambda kv: -kv[1])))


if __name__ == "__main__":
    patch_data_js()
