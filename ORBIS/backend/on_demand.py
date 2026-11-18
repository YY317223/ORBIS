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
STORE = os.path.join(DATA, "country_requests.json")

MAX_PER_USER = 10          # 每用户每天
DEDUPE_HOURS = 6           # 同一国家去重窗口
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

        # 贸易（出口/进口），失败不阻塞主流程
        trade_note = []
        for flow, key in (("X", "exports"), ("M", "imports")):
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
            note="用户 %s 请求；贸易：%s" % (rec.get("email") or rec.get("uid"), "、".join(trade_note) or "无"),
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


def request(iso, user):
    """用户发起按需刷新。返回 (ok, payload)。"""
    iso = (iso or "").upper()
    if not re.match(r"^[A-Z]{3}$", iso):
        return False, "国家代码不合法"
    uid = str(user.get("id"))
    rows = _load()
    with _LOCK:
        dup = _recent_for(rows, iso)
        if dup:
            return True, {"status": dup.get("status"), "batch_id": dup.get("batch_id"),
                          "reused": True, "message": "该国最近已请求过，等待审核"}
        if _today_count(rows, uid) >= MAX_PER_USER:
            return False, "今天的按需更新次数已用完（%d 次/天）" % MAX_PER_USER

        rid = "r" + _now().strftime("%Y%m%d%H%M%S") + str(int(time.time() * 1000) % 1000)
        rec = {"id": rid, "iso3": iso, "uid": uid, "email": user.get("email"),
               "created": _iso_now(), "status": "queued"}
        rows.append(rec)
        _save(rows)

    try:
        rep = trade_fetch.reporters()
        code = rep.get(iso)
    except Exception:  # noqa: BLE001
        code = None
    if not code:
        rec["status"] = "failed"
        rec["error"] = "该国没有 Comtrade 报送，无法按需抓取贸易数据"
        _save(rows)
        return False, rec["error"]

    threading.Thread(target=_job, args=(rid, iso, code), daemon=True).start()
    return True, {"status": "queued", "id": rid, "message": "已开始抓取，审核通过后会通知你"}


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
            "created": rec.get("created"), "error": rec.get("error")}


def list_requests(limit=50):
    rows = _load()
    out = []
    for r in reversed(rows[-limit:]):
        r = dict(r)
        r["name"] = _zh(r.get("iso3"))
        out.append(r)
    return out
