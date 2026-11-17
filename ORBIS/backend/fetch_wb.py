#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从世界银行 API 拉取四项指标，落盘为页面可直接消费的 wb.json。

只用标准库。可单独运行：python fetch_wb.py
"""
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OUT = os.path.join(DATA, "wb.json")

API = "https://api.worldbank.org/v2/country/all/indicator/{ind}?format=json&per_page=20000&date={y0}:{y1}"
IND = {
    "pc": "NY.GDP.PCAP.CD",
    "gdp": "NY.GDP.MKTP.CD",
    "pop": "SP.POP.TOTL",
    "le": "SP.DYN.LE00.IN",
    # 结构类指标：与前端内置的年龄结构 / 城镇化率对齐，保证年份同步
    "a0": "SP.POP.0014.TO.ZS",
    "a65": "SP.POP.65UP.TO.ZS",
    "urb": "SP.URB.TOTL.IN.ZS",
    # 三大产业增加值占 GDP 比重：给"主要营收业务"做兜底（无具体产业标签的国家用）
    "agr": "NV.AGR.TOTL.ZS",
    "ind": "NV.IND.TOTL.ZS",
    "srv": "NV.SRV.TOTL.ZS",
}
# 变化提醒只盯这 4 个核心指标，避免新增结构指标把订阅邮件刷屏
EVENT_IND = ("pc", "gdp", "pop", "le")
Y0, Y1 = 2000, 2026
UA = "space-earth/1.0 (+local data tool)"


def _get(url, tries=3):
    ctx = ssl.create_default_context()
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=45, context=ctx) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as e:
            last = e
            time.sleep(1.5 * (i + 1))
    raise RuntimeError("fetch failed: %s" % last)


def fetch_indicator(code, ind, y0=Y0, y1=Y1):
    """返回 (rows, lastupdated)。rows: [(iso3, year, value)]"""
    url = API.format(ind=ind, y0=y0, y1=y1)
    payload = _get(url)
    if not isinstance(payload, list) or len(payload) < 2 or payload[1] is None:
        raise RuntimeError("unexpected payload for %s" % code)
    meta = payload[0] or {}
    rows = []
    for it in payload[1]:
        iso = (it.get("countryiso3code") or "").upper()
        try:
            year = int(it.get("date"))
        except (TypeError, ValueError):
            continue
        v = it.get("value")
        if not iso or v is None:
            continue
        rows.append((iso, year, float(v)))
    return rows, meta.get("lastupdated") or ""


def build(previous=None):
    years = list(range(Y0, Y1 + 1))
    idx = {y: i for i, y in enumerate(years)}
    countries = {}
    lastupdates = []
    counts = {}
    for code, ind in IND.items():
        rows, lu = fetch_indicator(code, ind)
        lastupdates.append(lu)
        counts[code] = len(rows)
        for iso, year, v in rows:
            c = countries.setdefault(iso, {})
            arr = c.setdefault(code, [None] * len(years))
            arr[idx[year]] = v
    # 补齐缺列，保证各指标长度一致
    for iso, c in countries.items():
        for code in IND:
            if code not in c:
                c[code] = [None] * len(years)

    # 按实际有值的最大年份裁剪：世行还没发布的年份（如 2026）不占位，
    # 等它发布了，下次抓取年份轴自动就长一格。
    max_used = Y0
    for c in countries.values():
        for code in IND:
            arr = c.get(code) or []
            for i, v in enumerate(arr):
                if v is not None and years[i] > max_used:
                    max_used = years[i]
    if max_used > Y0:
        keep = max_used - Y0 + 1
        years = years[:keep]
        for c in countries.values():
            for code in IND:
                c[code] = (c.get(code) or [])[:keep]

    now = datetime.now(timezone(timedelta(hours=8)))
    doc = {
        "fetched_at": now.isoformat(timespec="seconds"),
        "source_updated": max([x for x in lastupdates if x] or [""]),
        "years": years,
        "indicators": IND,
        "counts": counts,
        "countries": countries,
    }
    doc["events"] = diff(previous, doc) if previous else []
    return doc


def _last(arr):
    if not arr:
        return None, None
    for i in range(len(arr) - 1, -1, -1):
        if arr[i] is not None:
            return arr[i], i
    return None, None


def diff(old, new):
    """找出「大变」：新增年份、或最新值相对上次抓取变动超过阈值。"""
    if not old:
        return []
    oc = old.get("countries") or {}
    nc = new.get("countries") or {}
    old_years = old.get("years") or []
    new_years = new.get("years") or []
    thresh = {"pc": 0.05, "gdp": 0.05, "pop": 0.01, "le": 0.02}  # le 用绝对年差
    events = []
    added_year = new_years[-1] if new_years and new_years[-1] not in old_years else None
    for iso, c in nc.items():
        o = oc.get(iso)
        if not o:
            continue
        for code in EVENT_IND:
            nv, ni = _last(c.get(code))
            ov, oi = _last(o.get(code))
            if nv is None or ov is None or nv == ov:
                continue
            if added_year is not None and ni is not None and new_years[ni] == added_year:
                events.append({
                    "iso": iso, "ind": code, "kind": "new_year",
                    "year": new_years[ni], "old": ov, "new": nv,
                })
                continue
            if code == "le":
                if abs(nv - ov) >= thresh[code]:
                    events.append({"iso": iso, "ind": code, "kind": "revision",
                                   "year": new_years[ni], "old": ov, "new": nv})
            else:
                base = abs(ov) if ov else 0
                if base and abs(nv - ov) / base >= thresh[code]:
                    events.append({"iso": iso, "ind": code, "kind": "revision",
                                   "year": new_years[ni], "old": ov, "new": nv})
    return events


def load_previous():
    if not os.path.exists(OUT):
        return None
    try:
        with open(OUT, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def save(doc):
    os.makedirs(DATA, exist_ok=True)
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, OUT)
    return OUT


def run(verbose=True):
    prev = load_previous()
    doc = build(prev)
    save(doc)
    if verbose:
        print("[fetch] %s  years=%s..%s  countries=%d  events=%d  source=%s" % (
            doc["fetched_at"], doc["years"][0], doc["years"][-1],
            len(doc["countries"]), len(doc["events"]), doc["source_updated"]))
    return doc


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print("[fetch] FAILED:", e, file=sys.stderr)
        sys.exit(1)
