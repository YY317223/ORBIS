# -*- coding: utf-8 -*-
"""增量修补 data.js 的城市清单：按「人口 + 空间覆盖」重选，避免西部整片空白。"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from city_pick import pick_cities, is_district

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
DATA = os.path.join(ROOT, "data.js")
CITYF = os.path.join(HERE, "raw", "ne_places10m.geojson")

try:
    from opencc import OpenCC
    t2s = OpenCC("t2s").convert
except Exception as e:  # noqa
    print("!! opencc 不可用:", e)
    t2s = lambda s: s

gj = json.loads(open(CITYF, encoding="utf-8").read())
bucket = {}
for ft in gj["features"]:
    pr = ft.get("properties", {})
    a3 = (pr.get("ADM0_A3") or "").upper()
    sub = a3 in ("TWN", "HKG", "MAC")
    if sub:
        a3 = "CHN"
    co = (ft.get("geometry") or {}).get("coordinates")
    if not co or not a3:
        continue
    pop = pr.get("POP_MAX") or pr.get("POP_MIN") or 0
    feat = pr.get("FEATURECLA") or ""
    cap = 1 if (pr.get("ADM0CAP") == 1 or "Admin-0 capital" in feat) else 0
    adm1 = 1 if "Admin-1 capital" in feat else 0
    if sub:
        cap = 0
        adm1 = 0      # 台港澳的县市级条目不算省级中心，否则会挤掉大陆省会
    if not cap and (not pop or pop < 30000):
        continue
    nm = t2s((pr.get("NAME_ZH") or "").strip()) or (pr.get("NAME") or "").strip()
    if a3 in ("CHN", "TWN") and is_district(nm):
        continue          # 县/区级条目（莎车县、海拉尔区…）不是城市
    bucket.setdefault(a3, []).append({
        "n": nm,
        "e": (pr.get("NAME") or "").strip(),
        "lo": round(co[0], 3), "la": round(co[1], 3),
        "p": int(pop) if pop else 0, "c": cap, "r": adm1,
    })
for k in bucket:
    bucket[k].sort(key=lambda x: (-x["c"], -x["p"]))

s = open(DATA, encoding="utf-8").read()
cut, end = s.index("{"), s.rindex("}") + 1
D = json.loads(s[cut:end])

before = sum(len(c.get("city") or []) for c in D["countries"])
gain = []
for c in D["countries"]:
    cand = bucket.get(c.get("iso3") or "", [])
    if not cand:
        continue
    old = c.get("city") or []
    c["city"] = [{k: v for k, v in x.items() if k != "r"} for x in pick_cities(cand, c.get("ar"))]
    if len(c["city"]) > len(old):
        gain.append((c["n"], len(old), len(c["city"])))
after = sum(len(c.get("city") or []) for c in D["countries"])

out = "window.ATLAS_DATA = " + json.dumps(D, ensure_ascii=False, separators=(",", ":")) + ";\n"
open(DATA, "w", encoding="utf-8").write(out)

print("cities:", before, "->", after, "| countries expanded:", len(gain))
for g in sorted(gain, key=lambda x: -(x[2] - x[1]))[:12]:
    print("  ", g)
cn = next(c for c in D["countries"] if c["n"] == "中国")
print("中国", len(cn["city"]), "城:", " ".join(x["n"] for x in cn["city"]))
