# -*- coding: utf-8 -*-
"""增量回填城市字段 r（省级行政中心 = 1）。

起因：fix_cities.py 写回时把 r 删掉以省体积，导致前端无法区分「省会」与「普通城市」，
城市图上只有首都与普通点两级。本脚本只补字段、不改已选城市集合。

匹配键优先用 (iso3, 英文名)，回退 (iso3, 中文名)；同一键冲突时取 max（省会优先）。
"""
import json
import os

try:
    from opencc import OpenCC
    t2s = OpenCC("t2s").convert
except Exception:  # noqa
    t2s = lambda s: s

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
DATA = os.path.join(ROOT, "data.js")
CITYF = os.path.join(HERE, "raw", "ne_places10m.geojson")

# 中国行政区划在 Natural Earth 里有噪声（抚顺、昭通被误标为 Admin-1 capital），
# 改用显式名单：23 省省会 + 5 自治区首府 + 4 直辖市（北京按首都处理）。
CN_PROV = {
    "北京", "天津", "石家庄", "太原", "呼和浩特", "沈阳", "长春", "哈尔滨",
    "上海", "南京", "杭州", "合肥", "福州", "南昌", "济南", "郑州", "武汉",
    "长沙", "广州", "南宁", "海口", "重庆", "成都", "贵阳", "昆明", "拉萨",
    "西安", "兰州", "西宁", "银川", "乌鲁木齐",
}

gj = json.loads(open(CITYF, encoding="utf-8").read())
by_e, by_n = {}, {}
for ft in gj["features"]:
    pr = ft.get("properties", {})
    a3 = (pr.get("ADM0_A3") or "").upper()
    if a3 in ("TWN", "HKG", "MAC"):
        continue                  # 台港澳不作省级中心标记（沿用既有口径）
    if not a3:
        continue
    adm1 = 1 if "Admin-1 capital" in (pr.get("FEATURECLA") or "") else 0
    if not adm1:
        continue
    e = (pr.get("NAME") or "").strip()
    n = t2s((pr.get("NAME_ZH") or "").strip())
    if a3 == "CHN" and n not in CN_PROV:
        continue
    if e:
        by_e[(a3, e)] = 1
    if n:
        by_n[(a3, n)] = 1

s = open(DATA, encoding="utf-8").read()
cut, end = s.index("{"), s.rindex("}") + 1
D = json.loads(s[cut:end])

hit = miss = 0
missed = []
for c in D["countries"]:
    a3 = (c.get("iso3") or "").upper()
    for ct in c.get("city") or []:
        ct.pop("r", None)
        e = (ct.get("e") or "").strip()
        n = (ct.get("n") or "").strip()
        if (a3, e) in by_e or (a3, n) in by_n:
            ct["r"] = 1
            hit += 1
        elif ct.get("c") != 1:
            miss += 1
            if len(missed) < 20:
                missed.append(a3 + "/" + n)

out = "window.ATLAS_DATA = " + json.dumps(D, ensure_ascii=False, separators=(",", ":")) + ";\n"
open(DATA, "w", encoding="utf-8").write(out)

cn = next(c for c in D["countries"] if c["n"] == "中国")
prov = [x["n"] for x in cn["city"] if x.get("r")]
print("回填 r=1:", hit, "| 未命中(非首都):", miss)
print("中国省会", len(prov), ":", " ".join(prov))
if missed:
    print("部分未命中:", " ".join(missed))
print("size", os.path.getsize(DATA))
