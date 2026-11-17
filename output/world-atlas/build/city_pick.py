# -*- coding: utf-8 -*-
"""国家城市选点：省会成为骨架 → 稀疏播种保证区域覆盖 → 人口补足密度。

为什么改：原实现按人口降序取前 18 个，中国这种人口大国会把乌鲁木齐（357 万，第 19 位）、
喀什、拉萨、西宁全部截掉，新疆 / 西藏 / 青海在地图上一片空白。

三级选择：
1. 骨架 —— 国家首都（≤2）+ 省级行政中心（Natural Earth 的 Admin-1 capital）。
   省级单位在 34 个以内的国家（中国 32、印度 34、巴西 29…）全部收录，
   「每个省至少一城」成为硬保证，不再靠人口排名撞运气；
   省级单位过多的国家（俄罗斯 89、美国 50、日本 40）不做硬保证，回落到 2、3 级。
2. 稀疏播种 —— 按人口降序扫描，只有与已选城市都相距 > 700km 才接受，
   覆盖人烟稀少但有重要城市的地区。
3. 人口补足 —— 剩余名额按人口降序填满，恢复城市群的密度。
名额 = 12 + 0.62·√(面积平方度)，接入省会后抬到 省会数+4，整体夹在 [14, 46]。
"""

import math

R_EARTH = 6371.0
SPREAD_KM = 700.0
FORCE = ("香港", "澳门", "台北")
ADMIN1_MAX = 34          # 省级单位超过这个数就不做「省会全覆盖」
QUOTA_MIN, QUOTA_MAX = 14, 46


def _km(a, b):
    lon1, lat1 = a
    lon2, lat2 = b
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R_EARTH * math.asin(min(1.0, math.sqrt(h)))


def quota(area_deg, admin1=0):
    n = 12 + 0.62 * math.sqrt(max(area_deg or 0, 0))
    if 6 <= admin1 <= ADMIN1_MAX:
        n = max(n, admin1 + 10)  # 省会是骨架，另留 10 个名额给非省会的超大城市 + 偏远重镇（深圳、喀什…）
    return int(max(QUOTA_MIN, min(QUOTA_MAX, round(n))))


def is_district(name):
    """县 / 区级条目（莎车县、海拉尔区、桃园区…）不是城市，剔除，避免顶掉真正的地级市。"""
    return bool(name) and name[-1] in "县区" and name not in ("香港", "澳门")


def pick_cities(lst, area_deg, quota_override=None):
    """lst 已按 (首都优先, 人口降序) 排好，元素可带 c=国家首都、r=省级行政中心。"""
    if not lst:
        return []
    admin1 = [c for c in lst if c.get("r")]
    n = quota_override or quota(area_deg, len(admin1))
    if len(lst) <= n:
        return [dict(c) for c in lst]

    pos = lambda c: (c["lo"], c["la"])
    picks = []
    chosen = set()

    def take(c):
        picks.append(c)
        chosen.add(c.get("e") or c["n"])

    # 1. 骨架：国家首都 → 省级行政中心 → 特别行政区
    for c in [c for c in lst if c.get("c")][:2]:
        take(c)
    for c in admin1:
        if len(picks) >= n - 2:
            break
        if (c.get("e") or c["n"]) not in chosen:
            take(c)
    for c in lst:
        if c["n"] in FORCE and c["n"] not in chosen and len(picks) < n:
            take(c)

    # 2. 稀疏播种（给人口补足预留 12% 名额，避免边远小城占满、超大城市反而落选）
    reserve = max(2, int(round(n * 0.12)))
    seed_cap = min(n - reserve, max(len(picks) + 1, int(round(n * 0.55))))
    for c in lst:
        if len(picks) >= seed_cap:
            break
        key = c.get("e") or c["n"]
        if key in chosen:
            continue
        if all(_km(pos(c), pos(p)) > SPREAD_KM for p in picks):
            take(c)

    # 3. 人口补足
    for c in lst:
        if len(picks) >= n:
            break
        key = c.get("e") or c["n"]
        if key not in chosen:
            take(c)

    picks.sort(key=lambda c: (-(c.get("c") or 0), -(c.get("r") or 0), -(c.get("p") or 0)))
    return [dict(c) for c in picks]
