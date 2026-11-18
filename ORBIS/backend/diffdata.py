#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""待审数据与线上数据的差异计算（给管理后台的「数据审核」用）。

原来的对比只到「字段级」（countries 条目数相同、fetched_at 已更新），管理员看不出
到底哪个国家、哪个指标动了。这里把它算到「国家 × 指标」粒度，并附带最新一年的
同比亮点，让每次抓取的变化一眼可见。
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA_JS = os.path.join(ROOT, "data.js")

IND_LABEL = {
    "gdp": "GDP 总量", "pc": "人均 GDP", "pop": "人口", "le": "预期寿命",
    "a0": "0–14 岁占比", "a65": "65+ 占比", "urb": "城镇化率",
}
IND_UNIT = {"gdp": "美元", "pc": "美元", "pop": "人", "le": "岁",
            "a0": "%", "a65": "%", "urb": "%"}
CORE = ("gdp", "pc", "pop", "le")
_NAMES = None


def names():
    """ISO3 -> 中文名，从项目 data.js 里取，取不到就退回 ISO3。"""
    global _NAMES
    if _NAMES is not None:
        return _NAMES
    out = {}
    try:
        with open(DATA_JS, encoding="utf-8") as f:
            raw = f.read()
        doc = json.loads(raw.split("=", 1)[1].strip().rstrip(";"))
        for c in doc.get("countries") or []:
            iso = (c.get("iso3") or "").upper()
            if iso:
                out[iso] = c.get("n") or iso
    except Exception:  # noqa: BLE001
        out = {}
    _NAMES = out
    return out


def _nm(iso):
    return names().get(iso, iso)


def _last(arr):
    """返回 (值, 下标) —— 最后一个非空。"""
    if not arr:
        return None, None
    for i in range(len(arr) - 1, -1, -1):
        if arr[i] is not None:
            return arr[i], i
    return None, None


def _fmt(v, key):
    if v is None:
        return "—"
    if key == "gdp":
        return "%.2f 万亿" % (v / 1e12) if abs(v) >= 1e12 else "%.1f 亿" % (v / 1e8)
    if key == "pop":
        return "%.2f 亿" % (v / 1e8) if v >= 1e8 else "%.0f 万" % (v / 1e4)
    if key == "pc":
        return "%s 美元" % format(round(v), ",")
    if key == "le":
        return "%.1f 岁" % v
    return "%.2f" % v


def _pct(old, new):
    if old in (None, 0) or new is None:
        return None
    return (new - old) / abs(old) * 100


def build_wb_diff(old, new):
    """old/new 均为 wb.json 结构；old 可能为 None（首次发布）。

    刻意把两件事分开算：
      - 新增年份：新版本多出来的年份有多少国家有值（这是「长了一格」，不是修订）
      - 历史修订：共同年份里，同一年的数值被世行改了多少（这才是需要人眼核对的）
    """
    oy = (old or {}).get("years") or []
    ny = new.get("years") or []
    oc = (old or {}).get("countries") or {}
    nc = new.get("countries") or {}

    if not old:
        return {"kind": "wb", "first": True,
                "summary": "首次发布：暂无历史数据可对比（%s 起，%d 个国家/地区）" % (
                    ny[0] if ny else "?", len(nc))}

    added_years = [y for y in ny if y not in oy]
    removed_years = [y for y in oy if y not in ny]
    added_iso = sorted(set(nc) - set(oc))
    removed_iso = sorted(set(oc) - set(nc))
    common = [y for y in ny if y in oy]
    lc = common[-1] if common else None          # 共同年份的最新一年
    latest = ny[-1] if ny else None

    # 新增年份各自有多少国家有值
    added_stats = []
    for y in added_years:
        j = ny.index(y)
        n = sum(1 for c in nc.values()
                if isinstance(c.get("pop"), list) and j < len(c["pop"]) and c["pop"][j] is not None)
        added_stats.append({"year": y, "countries": n})

    indicators, revisions_total, movers = [], 0, []
    yidx = [(oy.index(y), ny.index(y), y) for y in common]   # (旧下标, 新下标, 年份)
    revised_years = set()
    revised_isos = set()
    for key in CORE:
        if key not in (new.get("indicators") or {}):
            continue
        rev = 0
        local = []
        for iso, c in nc.items():
            o = oc.get(iso)
            if not o:
                continue
            nseries = c.get(key) or []
            oseries = o.get(key) or []
            for oi, ni, y in yidx:
                nv = nseries[ni] if ni < len(nseries) else None
                ov = oseries[oi] if oi < len(oseries) else None
                if nv is None or ov is None or nv == ov:
                    continue
                rev += 1
                revised_years.add(y)
                revised_isos.add(iso)
                local.append({"iso": iso, "name": _nm(iso), "key": key,
                              "label": IND_LABEL.get(key, key), "year": y,
                              "old": ov, "new": nv, "pct": _pct(ov, nv)})
        revisions_total += rev
        local.sort(key=lambda x: abs(x["pct"] or 0), reverse=True)
        movers.extend(local[:4])

        ow = (oc.get("WLD") or {}).get(key) or []
        nw = (nc.get("WLD") or {}).get(key) or []
        base_old = ow[oy.index(lc)] if lc in oy and len(ow) > oy.index(lc) else None
        base_new = nw[ny.index(lc)] if lc in ny and len(nw) > ny.index(lc) else None
        last_new = nw[ny.index(latest)] if latest in ny and len(nw) > ny.index(latest) else None
        indicators.append({
            "key": key, "label": IND_LABEL.get(key, key), "unit": IND_UNIT.get(key, ""),
            "revisions": rev,
            "base_year": lc,
            "world_base_old": {"v": base_old, "text": _fmt(base_old, key)},
            "world_base_new": {"v": base_new, "text": _fmt(base_new, key)},
            "world_base_pct": _pct(base_old, base_new),
            "latest_year": latest,
            "world_latest": {"v": last_new, "text": _fmt(last_new, key)},
            "world_latest_pct": _pct(base_new, last_new),
        })

    movers.sort(key=lambda x: abs(x["pct"] or 0), reverse=True)
    movers = movers[:12]

    parts = []
    if added_stats:
        parts.append("新增年份 %s" % "、".join("%d（%d 国）" % (a["year"], a["countries"]) for a in added_stats))
    if revisions_total:
        ys = sorted(revised_years)
        parts.append("历史修订 %d 处，涉及 %d 国%s" % (
            revisions_total, len(revised_isos),
            "（年份 %s）" % "、".join(str(y) for y in ys) if len(ys) <= 6 else ""))
    if added_iso:
        parts.append("新增国家 %d 个" % len(added_iso))
    if removed_iso:
        parts.append("减少国家 %d 个" % len(removed_iso))
    summary = "；".join(parts) if parts else "与线上完全一致：没有新增年份，也没有历史修订"

    return {
        "kind": "wb",
        "changed": bool(added_years or revisions_total or added_iso or removed_iso),
        "summary": summary,
        "years": {"old": [oy[0], oy[-1]] if oy else [], "new": [ny[0], ny[-1]] if ny else [],
                  "added": added_years, "removed": removed_years},
        "added_stats": added_stats,
        "revised_years": sorted(revised_years),
        "revised_countries": len(revised_isos),
        "countries": {"old": len(oc), "new": len(nc),
                      "added": added_iso[:20], "removed": removed_iso[:20]},
        "indicators": indicators,
        "revisions": revisions_total,
        "movers": movers,
        "events": len(new.get("events") or []),
        "source_updated": new.get("source_updated"),
        "fetched_at": new.get("fetched_at"),
        "highlights": highlights(new),
    }


def highlights(new, min_pop=5_000_000, top=6):
    """最新一年里，主要国家（人口 > 500 万）的 GDP 同比与人口变化。"""
    years = new.get("years") or []
    cs = new.get("countries") or {}
    if len(years) < 2:
        return {"gdp": [], "pop": [], "year": years[-1] if years else None}
    yi, pi = len(years) - 1, len(years) - 2

    def collect(key, weight_key, min_w):
        rows = []
        for iso, c in cs.items():
            a = c.get(key) or []
            if len(a) <= yi:
                continue
            nv, ov = a[yi], a[pi]
            if nv is None or ov in (None, 0):
                continue
            w = (c.get(weight_key) or [None] * len(years))[pi] if weight_key else None
            if min_w and (w is None or w < min_w):
                continue
            rows.append({"iso": iso, "name": _nm(iso), "pct": (nv - ov) / abs(ov) * 100,
                         "new": nv, "old": ov})
        rows.sort(key=lambda x: x["pct"], reverse=True)
        return rows

    gdp_rows = collect("gdp", "pop", min_pop)
    pop_rows = collect("pop", None, None)
    return {"year": years[yi], "prev_year": years[pi],
            "gdp": {"up": gdp_rows[:top],
                    "down": [r for r in reversed(gdp_rows) if r["pct"] < 0][:top]},
            "pop": {"up": pop_rows[:top],
                    "down": [r for r in reversed(pop_rows) if r["pct"] < 0][:top]}}


def build_fx_diff(old, new):
    oc = (old or {}).get("currencies") or {}
    nc = new.get("currencies") or {}
    if not old:
        return {"kind": "fx", "first": True,
                "summary": "首次发布：%d 个币种" % len(nc)}
    movers, changed = [], 0
    for code, rec in nc.items():
        o = oc.get(code)
        nv = (rec or {}).get("rate")
        ov = (o or {}).get("rate")
        if ov and nv and ov != nv:
            changed += 1
            movers.append({"code": code, "name": (rec or {}).get("name") or code,
                           "old": ov, "new": nv, "pct": (nv - ov) / ov * 100,
                           "d7": (rec or {}).get("d7")})
    movers.sort(key=lambda x: abs(x["pct"]), reverse=True)
    return {
        "kind": "fx",
        "changed": bool(changed),
        "summary": ("%d 个币种汇率变化" % changed) if changed else "汇率与线上一致，无变动",
        "date": {"old": (old or {}).get("date"), "new": new.get("date")},
        "counts": {"old": len(oc), "new": len(nc)},
        "movers": movers[:12],
    }


def compare(name, old, new):
    if name == "wb.json":
        return build_wb_diff(old, new)
    if name == "fx.json":
        return build_fx_diff(old, new)
    return None


# ---------------------------------------------------------------- 逐国明细
CORE_LABEL = {"pop": "人口", "gdp": "GDP", "pc": "人均 GDP"}


def _cell(old_series, new_series, oy, ny, key):
    """取某国某指标：新值 + 旧值，供表格显示「未变 / 旧→新」。"""
    def last(series, years):
        if not series:
            return None, None
        for i in range(len(years) - 1, -1, -1):
            if i < len(series) and series[i] is not None:
                return series[i], years[i]
        return None, None

    nv, ny_ = last(new_series, ny)
    ov, oy_ = last(old_series, oy)
    changed = (nv is not None and ov is not None and nv != ov)
    return {
        "v": nv, "y": ny_, "text": _fmt(nv, key),
        "old": ov, "old_y": oy_, "old_text": _fmt(ov, key),
        "changed": changed,
        "pct": _pct(ov, nv) if changed else None,
    }


def country_rows(old, new, trade_doc=None, sort="gdp"):
    """逐国一行：人口 / GDP / 人均 GDP / 出口前三。

    与线上比没有变化的国家同样返回（changed=False），由前端决定是否过滤。
    """
    oy = (old or {}).get("years") or []
    ny = new.get("years") or []
    oc = (old or {}).get("countries") or {}
    nc = new.get("countries") or {}

    rows = []
    nmap = names()          # data.js 里的国家表；用它把世行的地区聚合值（WLD/EAS…）滤掉
    for iso, c in nc.items():
        if iso not in nmap:
            continue
        o = oc.get(iso) or {}
        row = {"iso": iso, "name": _nm(iso), "changed": False,
               "pop": _cell(o.get("pop"), c.get("pop"), oy, ny, "pop"),
               "gdp": _cell(o.get("gdp"), c.get("gdp"), oy, ny, "gdp"),
               "pc": _cell(o.get("pc"), c.get("pc"), oy, ny, "pc")}
        row["changed"] = any(row[k]["changed"] for k in ("pop", "gdp", "pc"))
        t = None
        try:
            import trade as _trade
            t = _trade.for_country(iso)
        except Exception:  # noqa: BLE001
            t = None
        row["exports"] = (t or {}).get("exports")
        row["imports"] = (t or {}).get("imports")
        rows.append(row)

    key = {"gdp": "gdp", "pop": "pop", "pc": "pc"}.get(sort, "gdp")
    rows.sort(key=lambda r: (r[key]["v"] is None, -(r[key]["v"] or 0)))
    return {
        "rows": rows,
        "total": len(rows),
        "changed": sum(1 for r in rows if r["changed"]),
        "with_exports": sum(1 for r in rows if r["exports"]),
        "with_imports": sum(1 for r in rows if r["imports"]),
        "source": {"updated": new.get("source_updated"), "fetched_at": new.get("fetched_at")},
        "years": {"old": [oy[0], oy[-1]] if oy else [], "new": [ny[0], ny[-1]] if ny else []},
    }
