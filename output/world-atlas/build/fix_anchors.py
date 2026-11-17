# -*- coding: utf-8 -*-
"""增量修补 data.js：重算每个国家的锚点（视觉中心）与面积，供洲视图国名标注与聚焦使用。"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geo_anchor import anchor_from_ll

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data.js")

s = open(DATA, encoding="utf-8").read()
cut = s.index("{")
end = s.rindex("}") + 1
D = json.loads(s[cut:end])

bad = []
mov = []
for c in D["countries"]:
    lon, lat, ar = anchor_from_ll(c.get("ll") or [])
    if ar <= 0:
        bad.append(c["n"])
        continue
    d = abs(lon - c["clon"]) + abs(lat - c["clat"])
    if d > 3:
        mov.append((c["n"], round(c["clon"], 1), round(c["clat"], 1), lon, lat, round(d, 1)))
    c["clon"], c["clat"], c["ar"] = lon, lat, ar

out = "window.ATLAS_DATA = " + json.dumps(D, ensure_ascii=False, separators=(",", ":")) + ";\n"
open(DATA, "w", encoding="utf-8").write(out)

print("anchors fixed:", len(D["countries"]) - len(bad), "| skipped:", len(bad), bad[:6])
print("moved >3deg:", len(mov))
for m in sorted(mov, key=lambda x: -x[5])[:14]:
    print("  ", m)
