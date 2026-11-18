#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按需抓取：登录用户点某个国家 → 后台只抓这个国家 → 进待审区 → 管理员通过后生效。

与月度全量的区别：
  - 月度：全量刷新，直接发布（模式一）
  - 按需：只抓被点击的国家，必须人工审核（模式二）

流程：
  request(iso, user)  校验频率与去重，起后台线程
  _job(...)           抓世行 10 项指标 + 贸易出口/进口，合成整份 wb.json（只改这一国），
                      交给 staging 建批次，状态 pending_review
  管理员在「数据审核」页通过 → staging.publish，页面重建
  前端轮询 status()，看到 published 就提示并刷新

限频：每用户每天 MAX_PER_USER 次；同一国家 6 小时内只建一个批次。
"""
import json
import os
import re
import threading
import time
import urllib.request
from datetime import datetime, timedelta, timezone

import staging
import trade_fetch

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
WB = os.path.join(DATA, "wb.json")
TRADE = os.path.join(DATA, "trade.json")
STORE = os.path.join(DATA, "country_requests.json")

MAX_PER_USER = 10          # 每用户每天
DEDUPE_HOURS = 6           # 同一国家去重窗口

# 用户可勾选的 5 个指标（顺序即前端展示顺序）
METRICS = [
    ("pop", "人口"),
    ("gdp", "GDP"),
    ("pc", "人均 GDP"),
    ("exports", "出口前三"),
    ("imports", "进口前三"),
]
METRIC_KEYS = [k for k, _ in METRICS]
TRADE_KEYS = ("exports", "imports")


def normalize_metrics(metrics):
    """把前端传来的勾选列表收敛成合法子集；空/非法时默认全选。"""
    if not metrics:
        return list(METRIC_KEYS)
    if isinstance(metrics, str):
        metrics = [x.strip() for x in metrics.split(",")]
    want = [m for m in METRIC_KEYS if m in set(metrics)]
    return want or list(METRIC_KEYS)

WB_API = "https://api.worldbank.org/v2/country/{iso}/indicator/{code}?format=json&per_page=200&date=2000:2026"
IND = ["gdp", "pc", "pop", "le", "a0", "a65", "urb", "agr", "ind", "srv"]
CODES = {"gdp": "NY.GDP.MKTP.CD", "pc": "NY.GDP.PCAP.CD", "pop": "SP.POP.TOTL",
         "le": "SP.DYN.LE00.IN", "a0": "SP.POP.0014.TO.ZS", "a65": "SP.POP.65UP.TO.ZS",
         "urb": "SP.URB.TOTL.IN.ZS", "agr": "NV.AGR.TOTL.ZS", "ind": "NV.IND.TOTL.ZS",
         "srv": "NV.SRV.TOTL.ZS"}

_LOCK = threading.Lock()


def _now():
    return datetime.now(timezone(timedelta(hours=8)))


def _iso_now():
    return _now().isoformat(timespec="seconds")


def _load():
    try:
        with open(STORE, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _save(rows):
    os.makedirs(DATA, exist_ok=True)
    tmp = STORE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rows[-500:], f, ensure_ascii=False, indent=2)
    os.replace(tmp, STORE)


def _zh(iso):
    try:
        import diffdata
        return diffdata.names().get(iso, iso)
    except Exception:  # noqa: BLE001
        return iso


def _today_count(rows, uid):
    day = _now().strftime("%Y-%m-%d")
    return sum(1 for r in rows if r.get("uid") == uid and (r.get("created") or "")[:10] == day)


def _recent_for(rows, iso):
    cut = _now() - timedelta(hours=DEDUPE_HOURS)
    for r in reversed(rows):
        if r.get("iso3") != iso:
            continue
        try:
            c = datetime.fromisoformat(r["created"])
        except (KeyError, ValueError):
            continue
        if c >= cut and r.get("status") in ("queued", "pending_review", "published"):
            return r
    return None


SNAPSHOT = os.path.join(DATA, "wdi_snapshot.json")
SNAPSHOT_MAX_AGE = 3600     # 全量快照缓存 1 小时，多次按需请求共用


def _snapshot(max_age=SNAPSHOT_MAX_AGE):
    """拉一份世行全量快照并缓存。

    为什么不用单国接口：实测 /country/{iso}/... 在这条网络下 45 秒必超时，
    而 /country/all 只要 1~2 秒。所以统一拉全量再取单国，顺带被多次请求复用。
    """
    try:
        age = time.time() - os.path.getmtime(SNAPSHOT)
    except OSError:
        age = 1e9
    if age < max_age:
        try:
            with open(SNAPSHOT, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            pass

    import fetch_wb
    prev = None
    try:
        with open(WB, encoding="utf-8") as f:
            prev = json.load(f)
    except (OSError, json.JSONDecodeError):
        prev = None
    doc = fetch_wb.build(prev)
    os.makedirs(DATA, exist_ok=True)
    tmp = SNAPSHOT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, SNAPSHOT)
    return doc


def _extract(iso, snap, target_years):
    """从快照里取某国的各指标，按目标年份轴对齐。"""
    src = (snap.get("countries") or {}).get(iso) or {}
    syears = snap.get("years") or []
    idx = {y: i for i, y in enumerate(syears)}
    out = {}
    for key in IND:
        arr = src.get(key)
        if not isinstance(arr, list):
            continue
        row = []
        for y in target_years:
            i = idx.get(y)
            row.append(arr[i] if i is not None and i < len(arr) else None)
        if any(v is not None for v in row):
            out[key] = row
    return out


def _merge_into_wb(iso, series, meta=None):
    """把单国数据合并进整份 wb.json（只改这一行），返回新的 doc。"""
    with open(WB, encoding="utf-8") as f:
        doc = json.load(f)
    years = doc.get("years") or []
    c = doc.setdefault("countries", {}).setdefault(iso, {})
    for key, arr in series.items():
        c[key] = arr
    doc["fetched_at"] = _iso_now()
    doc["country_refresh"] = {"iso3": iso, "at": doc["fetched_at"],
                              "snapshot_years": (meta or {}).get("years")}
    return doc


def _job(rid, iso, reporter_code):
    rows = _load()
    rec = next((r for r in rows if r.get("id") == rid), None)
    if not rec:
        return
    try:
        rec["status"] = "fetching"
        _save(rows)

        snap = _snapshot()
        with open(WB, encoding="utf-8") as f:
            years = json.load(f).get("years") or []
        series = _extract(iso, snap, years)
        if not series:
            raise RuntimeError("世行快照里没有该国的数据")
        doc = _merge_into_wb(iso, series, {"years": snap.get("years")})

        # 贸易（出口/进口）：只抓用户勾选的，失败不阻塞主流程
        wanted = set(rec.get("metrics") or METRIC_KEYS)
        trade_note = []
        for flow, key in (("X", "exports"), ("M", "imports")):
            if key not in wanted:
                continue
            try:
                rr, year = trade_fetch.fetch_country(reporter_code, flow)
                if rr:
                    d = os.path.dirname(trade_fetch._cache_path(flow, iso))
                    os.makedirs(d, exist_ok=True)
                    with open(trade_fetch._cache_path(flow, iso), "w", encoding="utf-8") as f:
                        json.dump({"iso3": iso, "reporter_code": reporter_code, "flow": flow,
                                   "year": year, "rows": sorted(rr, key=lambda x: -x["v"]),
                                   "fetched_at": _iso_now()}, f, ensure_ascii=False)
                    trade_note.append("%s %s" % ("出口" if flow == "X" else "进口", year))
            except Exception as e:  # noqa: BLE001
                trade_note.append("%s失败" % ("出口" if flow == "X" else "进口"))
                print("[ondemand] 贸易失败", iso, flow, e)

        ok, info = staging.create(
            source="按需：%s" % _zh(iso),
            note="用户 %s 请求 %s；贸易：%s" % (
                rec.get("email") or rec.get("uid"),
                "、".join(dict(METRICS).get(k, k) for k in (rec.get("metrics") or METRIC_KEYS)),
                "、".join(trade_note) or ("未选择" if not wanted & set(TRADE_KEYS) else "无")),
            files={"wb.json": doc})
        if not ok:
            raise RuntimeError(str(info))
        rec["status"] = "pending_review"
        rec["batch_id"] = info["id"]
        rec["updated"] = _iso_now()
    except Exception as e:  # noqa: BLE001
        rec["status"] = "failed"
        rec["error"] = str(e)[:200]
        rec["updated"] = _iso_now()
    _save(rows)


def request(iso, user, metrics=None):
    """用户发起按需刷新。返回 (ok, payload)。"""
    iso = (iso or "").upper()
    if not re.match(r"^[A-Z]{3}$", iso):
        return False, "国家代码不合法"
    wanted = normalize_metrics(metrics)
    uid = str(user.get("id"))
    rows = _load()
    with _LOCK:
        dup = _recent_for(rows, iso)
        if dup:
            return True, {"status": dup.get("status"), "batch_id": dup.get("batch_id"),
                          "reused": True, "metrics": dup.get("metrics") or wanted,
                          "message": "该国最近已请求过，等待审核"}
        if _today_count(rows, uid) >= MAX_PER_USER:
            return False, "今天的按需更新次数已用完（%d 次/天）" % MAX_PER_USER

        rid = "r" + _now().strftime("%Y%m%d%H%M%S") + str(int(time.time() * 1000) % 1000)
        rec = {"id": rid, "iso3": iso, "uid": uid, "email": user.get("email"),
               "metrics": wanted, "created": _iso_now(), "status": "queued"}
        rows.append(rec)
        _save(rows)

    # 只要勾了贸易指标才需要 Comtrade 报送号；纯世行指标不查，省一次外网请求
    code = None
    if set(wanted) & set(TRADE_KEYS):
        try:
            rep = trade_fetch.reporters()
            code = rep.get(iso)
        except Exception:  # noqa: BLE001
            code = None
        if not code:
            rec["status"] = "failed"
            rec["error"] = "该国没有 Comtrade 报送，抓不到出口/进口数据；可只勾世行指标重试"
            _save(rows)
            return False, rec["error"]

    threading.Thread(target=_job, args=(rid, iso, code), daemon=True).start()
    return True, {"status": "queued", "id": rid, "metrics": wanted,
                  "message": "已开始抓取，审核通过后会通知你"}


def status(iso, user=None):
    """前端轮询用：返回该国最近一次请求的状态。"""
    iso = (iso or "").upper()
    rows = _load()
    uid = str((user or {}).get("id")) if user else None
    rec = None
    for r in reversed(rows):
        if r.get("iso3") != iso:
            continue
        if uid and r.get("uid") != uid:
            continue
        rec = r
        break
    if not rec:
        return {"iso3": iso, "status": "none"}
    # 批次状态以 staging 为准，避免状态不同步
    if rec.get("batch_id"):
        meta = staging.get_batch(rec["batch_id"])
        if meta:
            if meta.get("status") == "published":
                rec["status"] = "published"
            elif meta.get("status") == "rejected":
                rec["status"] = "rejected"
    return {"iso3": iso, "status": rec.get("status"), "batch_id": rec.get("batch_id"),
            "created": rec.get("created"), "metrics": rec.get("metrics") or METRIC_KEYS,
            "error": rec.get("error")}



# ---------------------------------------------------------------- 详情（5 指标）
_TRADE_CACHE = {"mtime": None, "doc": {}}


def _trade_doc():
    """trade.json 按 mtime 缓存，避免每次请求都读 40KB 文件。"""
    try:
        m = os.path.getmtime(TRADE)
    except OSError:
        return {}
    if _TRADE_CACHE["mtime"] == m:
        return _TRADE_CACHE["doc"] or {}
    try:
        with open(TRADE, encoding="utf-8") as f:
            doc = json.load(f)
    except (OSError, json.JSONDecodeError):
        doc = {}
    _TRADE_CACHE.update(mtime=m, doc=doc if isinstance(doc, dict) else {})
    return _TRADE_CACHE["doc"]


def _usd(v):
    """金额格式化：万亿美元 / 亿美元 / 万美元。"""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "—"
    if v >= 1e12:
        return "%.2f 万亿美元" % (v / 1e12)
    if v >= 1e8:
        return "%s 亿美元" % format(round(v / 1e8), ",")
    if v >= 1e4:
        return "%s 万美元" % format(round(v / 1e4), ",")
    return "%s 美元" % format(round(v), ",")


def _pop_text(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "—"
    if v >= 1e8:
        return "%.2f 亿人" % (v / 1e8)
    if v >= 1e4:
        return "%s 万人" % format(round(v / 1e4), ",")
    return "%s 人" % format(round(v), ",")


def _pc_text(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "—"
    return "%s 美元" % format(int(round(v)), ",")


def _last(series, years):
    """取该指标最近一个非空年份的值（年份一起返回，避免把旧值当成新年份）。"""
    if not isinstance(series, list):
        return None, None
    for i in range(len(series) - 1, -1, -1):
        v = series[i]
        if v is not None:
            return v, (years[i] if i < len(years) else None)
    return None, None


def detail(iso, doc=None, name=None):
    """返回某国 5 个指标的当前（已发布）数值，供前端勾选框展示。

    缺失一律 available=False，前端显示「此数据未公开」，不编造数字。
    """
    iso = (iso or "").upper()
    if not re.match(r"^[A-Z]{3}$", iso):
        return None
    if doc is None:
        try:
            with open(WB, encoding="utf-8") as f:
                doc = json.load(f)
        except (OSError, json.JSONDecodeError):
            doc = {}
    doc = doc or {}
    years = doc.get("years") or []
    c = (doc.get("countries") or {}).get(iso) or {}
    trade = (_trade_doc().get("countries") or {}).get(iso) or {}

    out = {}
    for key, label, src, text_of, reason in (
        ("pop", "人口", "pop", _pop_text, "世界银行 WDI 未收录该国人口数据"),
        ("gdp", "GDP", "gdp", _usd, "世界银行 WDI 未收录该国 GDP 数据"),
        ("pc", "人均 GDP", "pc", _pc_text, "世界银行 WDI 未收录该国人均 GDP 数据"),
    ):
        v, y = _last(c.get(src), years)
        out[key] = {"label": label, "available": v is not None, "value": v, "year": y,
                    "text": text_of(v) if v is not None else "此数据未公开"}
        if v is None:
            out[key]["reason"] = reason

    for key, label, word in (("exports", "出口前三", "出口"), ("imports", "进口前三", "进口")):
        fl = trade.get(key) or {}
        rows = fl.get("top3") or []
        if rows:
            items = []
            for r in rows[:3]:
                share = r.get("share")
                items.append({
                    "hs": r.get("hs"),
                    "zh": r.get("zh") or r.get("en") or ("HS " + str(r.get("hs") or "")),
                    "usd": r.get("usd"),
                    "text": _usd(r.get("usd")),
                    "share_text": ("%.1f%%" % (share * 100)) if isinstance(share, (int, float)) else "",
                })
            out[key] = {"label": label, "available": True, "year": fl.get("year"),
                        "total_usd": fl.get("total_usd"), "total_text": _usd(fl.get("total_usd")),
                        "rows": items}
        else:
            out[key] = {"label": label, "available": False, "text": "此数据未公开",
                        "reason": "联合国 Comtrade 暂无该国%s数据" % word}

    return {
        "iso3": iso,
        "name": name or _zh(iso),
        "updated": doc.get("fetched_at"),
        "years": years,
        "metrics": out,
    }


def list_requests(limit=50):
    rows = _load()
    out = []
    for r in reversed(rows[-limit:]):
        r = dict(r)
        r["name"] = _zh(r.get("iso3"))
        out.append(r)
    return out
