# -*- coding: utf-8 -*-
"""国家锚点：从 ll 量化环推算「视觉中心」（落在国土内部），并把面积换算成平方度。

为什么不用顶点平均：小岛多、形状呈新月形的国家（克罗地亚、格鲁吉亚、津巴布韦等）
顶点平均会把中心甩到邻国甚至大西洋里，洲视图的国名标签就会飘到错的国家上。

做法：
1. 按 |鞋带面积| 选主陆块（最大的那个环），远洋飞地不参与；
2. 主陆块 bbox 上开 N×N 栅格，奇偶规则逐行扫线判定格心是否在国土内；
3. 内部格做多源 BFS 求「到边界的最短格距」，取最大者为视觉中心 —— 相当于 raster 版 polylabel，
   新月形、L 形、细长国都能得到落在国土内的点。
"""


def decode_ring(a):
    """ll 环解码为经纬度点列。存储格式 [x0,y0,dx,dy,...]，x=(lon+180)*100、y=(90-lat)*100。"""
    x, y = a[0], a[1]
    pts = [(x / 100.0 - 180.0, 90.0 - y / 100.0)]
    for i in range(2, len(a), 2):
        x += a[i]
        y += a[i + 1]
        pts.append((x / 100.0 - 180.0, 90.0 - y / 100.0))
    return pts


def ring_area(pts):
    """鞋带面积（平方度），取绝对值。"""
    s = 0.0
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        s += x0 * y1 - x1 * y0
    if s == 0.0 and len(pts) >= 3:
        x0, y0 = pts[-1]
        x1, y1 = pts[0]
        s += x0 * y1 - x1 * y0
    return abs(s) / 2.0


def _fill_spans(pts, y, x0, x1):
    """水平线 y 与环的所有交点的 x 坐标（奇偶规则用）。"""
    xs = []
    n = len(pts)
    for i in range(n - 1):
        ya = pts[i][1]
        yb = pts[i + 1][1]
        if (ya > y) != (yb > y):
            t = (y - ya) / (yb - ya)
            xs.append(pts[i][0] + t * (pts[i + 1][0] - pts[i][0]))
    xs.sort()
    return xs


def visual_center(pts, N=88):
    """返回落在环内部的视觉中心点 (lon, lat)。"""
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    bx0, bx1, by0, by1 = min(xs), max(xs), min(ys), max(ys)

    # 面积极小 / 退化：退回 bbox 中心
    if bx1 - bx0 < 1e-6 or by1 - by0 < 1e-6:
        return (bx0 + bx1) / 2.0, (by0 + by1) / 2.0

    cx = (bx1 - bx0) / N
    cy = (by1 - by0) / N

    # 逐行扫线：得到每行内部格的起止列
    rows = []
    for r in range(N):
        y = by0 + (r + 0.5) * cy
        xcross = _fill_spans(pts, y, bx0, bx1)
        spans = []
        for i in range(0, len(xcross) - 1, 2):
            a = int(round((xcross[i] - bx0) / cx - 0.5))
            b = int(round((xcross[i + 1] - bx0) / cx - 0.5))
            if a < 0:
                a = 0
            if b > N - 1:
                b = N - 1
            if b >= a:
                spans.append((a, b))
        rows.append(spans)

    idx = lambda r, c: r * N + c
    inside = bytearray(N * N)
    for r in range(N):
        for a, b in rows[r]:
            for c in range(a, b + 1):
                inside[idx(r, c)] = 1

    if not any(inside):
        # 栅格太粗、国土比一个格还窄：按 bbox 中心
        return (bx0 + bx1) / 2.0, (by0 + by1) / 2.0

    # 多源 BFS：边界格（贴栅格外沿或邻格在外的内部格）距离为 1
    from collections import deque
    dist = [0] * (N * N)
    q = deque()
    for r in range(N):
        for c in range(N):
            i = idx(r, c)
            if not inside[i]:
                continue
            edge = (r == 0 or r == N - 1 or c == 0 or c == N - 1 or
                    not inside[idx(r - 1, c)] or not inside[idx(r + 1, c)] or
                    not inside[idx(r, c - 1)] or not inside[idx(r, c + 1)])
            if edge:
                dist[i] = 1
                q.append(i)
    while q:
        i = q.popleft()
        r, c = divmod(i, N)
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            rr, cc = r + dr, c + dc
            if 0 <= rr < N and 0 <= cc < N:
                j = idx(rr, cc)
                if inside[j] and dist[j] == 0:
                    dist[j] = dist[i] + 1
                    q.append(j)

    best, bi = -1, -1
    for i in range(N * N):
        if dist[i] > best:
            best, bi = dist[i], i
    r, c = divmod(bi, N)

    lon = bx0 + (c + 0.5) * cx
    lat = by0 + (r + 0.5) * cy

    # 超出 ±180 的（跨日界线的环经度连续化后可能越界）折回
    while lon > 180.0:
        lon -= 360.0
    while lon < -180.0:
        lon += 360.0
    return round(lon, 3), round(lat, 3)


def anchor_from_ll(ll):
    """从 ll 环数组算锚点：返回 (lon, lat, 主陆块面积平方度)。"""
    if not ll:
        return 0.0, 0.0, 0.0
    best, best_area = None, -1.0
    for a in ll:
        if len(a) < 8:
            continue
        pts = decode_ring(a)
        ar = ring_area(pts)
        if ar > best_area:
            best_area, best = ar, pts
    if best is None:
        # 环过小（礁、环礁）量化后退化：退回所有环的 bbox 中心
        xs, ys = [], []
        for a in ll:
            for p in decode_ring(a):
                xs.append(p[0])
                ys.append(p[1])
        if not xs:
            return 0.0, 0.0, 0.0
        lon = (min(xs) + max(xs)) / 2.0
        lat = (min(ys) + max(ys)) / 2.0
        while lon > 180.0:
            lon -= 360.0
        while lon < -180.0:
            lon += 360.0
        return round(lon, 3), round(max(-85.0, min(85.0, lat)), 3), 0.001
    lon, lat = visual_center(best)
    return lon, lat, max(round(best_area, 3), 0.001)
