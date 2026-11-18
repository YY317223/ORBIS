#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""项目内置的贸易数据抓取（UN Comtrade，出口/进口 HS 2 位章）。

为什么要单独做：Comtrade 免费接口限速严（约 45 秒/国）、每日配额有限，
全量 213 国要跑几个小时，所以必须
  - 逐国缓存，断了能续；
  - 挂在后台线程里跑，不阻塞 HTTP；
  - 配额用尽时立刻停下并记录状态，等下一轮（明天）自动续上。

产物：
  data/trade_cache/X/<ISO3>.json   出口缓存
  data/trade_cache/M/<ISO3>.json   进口缓存
  data/trade_progress.json         进度与状态（管理台读它）
  data/trade.json                  合并后的成品（页面与审核页读它）
"""
import json
import os
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

import hs2

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CACHE_X = os.path.join(DATA, "trade_cache", "X")
CACHE_M = os.path.join(DATA, "trade_cache", "M")
OUT = os.path.join(DATA, "trade.json")
PROGRESS = os.path.join(DATA, "trade_progress.json")
REPORTERS = os.path.join(DATA, "comtrade_reporters.json")

BASE = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
REPORT_URL = "https://comtradeapi.un.org/files/v1/app/reference/Reporters.json"
UA = "ORBIS/1.0 (own data service; contact admin)"
FALLBACK_YEARS = (2025, 2024, 2023, 2022)
FLOW_NAME = {"X": "出口", "M": "进口"}

_LOCK = threading.Lock()
_STATE = {"running": False}


def _now():
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


class QuotaExceeded(Exception):
    pass


# ---------------------------------------------------------------- 进度文件
def _write_progress(d):
    d = dict(d)
    d["updated_at"] = _now()
    tmp = PROGRESS + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    os.replace(tmp, PROGRESS)


def read_progress():
    try:
        with open(PROGRESS, encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict):
            d["running"] = bool(_STATE.get("running"))
            return d
    except (OSError, json.JSONDecodeError):
        pass
    return {"running": bool(_STATE.get("running")), "phase": None}


# ---------------------------------------------------------------- 国家与报告国
def _countries():
    """从 projects 的 data.js 读国家表（与前端一致）。"""
    import diffdata
    return sorted(diffdata.names().keys())


def reporters(force=False):
    if not force and os.path.exists(REPORTERS):
        try:
            with open(REPORTERS, encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, dict) and d:
                return d
        except (OSError, json.JSONDecodeError):
            pass
    req = urllib.request.Request(REPORT_URL, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        doc = json.loads(r.read().decode("utf-8"))
    out = {}
    for row in doc.get("results") or []:
        iso = (row.get("reporterCodeIsoAlpha3") or "").upper()
        code = row.get("reporterCode")
        if iso and isinstance(code, int):
            out[iso] = code
    os.makedirs(DATA, exist_ok=True)
    tmp = REPORTERS + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    os.replace(tmp, REPORTERS)
    return out


# ---------------------------------------------------------------- 抓取
def _get(url, timeout=40, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 403:
                body = ""
                try:
                    body = e.read()[:200].decode("utf-8", "replace")
                except Exception:  # noqa: BLE001
                    pass
                if "uota" in body:
                    raise QuotaExceeded("Comtrade 每日配额已用尽")
                raise RuntimeError("HTTP 403 %s" % body[:80])
            if e.code == 429:
                ra = e.headers.get("Retry-After")
                wait = float(ra) if ra and ra.replace(".", "").isdigit() else 15.0 * (i + 1)
                time.sleep(max(wait, 10))
                continue
            if e.code in (400, 404):
                raise RuntimeError("HTTP %s" % e.code)
            time.sleep(5 * (i + 1))
        except Exception as e:  # noqa: BLE001
            last = e
            if i == tries - 1:
                raise RuntimeError(str(e)[:100])
            time.sleep(5 * (i + 1))
    raise RuntimeError("重试失败: %s" % str(last)[:80])


def _rows_of(j):
    err = (j.get("error") or "").strip()
    if err:
        raise RuntimeError(err[:80])
    rows, years = [], set()
    for r in j.get("data") or []:
        cmd = str(r.get("cmdCode") or "")
        if len(cmd) != 2 or not cmd.isdigit() or cmd in ("98", "99"):
            continue
        v = r.get("primaryValue")
        if v is None:
            v = r.get("fobvalue")
        if v is None or v <= 0:
            continue
        rows.append({"hs": cmd, "v": float(v)})
        years.add(str(r.get("period")))
    return rows, (sorted(years)[-1] if years else None)


def fetch_country(code, flow):
    """先取最新年份，空则逐年回退。"""
    rows, year = _rows_of(_get("%s?reporterCode=%d&partnerCode=0&flowCode=%s&cmdCode=AG2" % (BASE, code, flow)))
    if rows:
        return rows, year
    for y in FALLBACK_YEARS:
        rows, year = _rows_of(_get("%s?reporterCode=%d&period=%d&partnerCode=0&flowCode=%s&cmdCode=AG2"
                                   % (BASE, code, y, flow)))
        if rows:
            return rows, year
        time.sleep(2)
    return [], None


def _cache_path(flow, iso):
    return os.path.join(CACHE_X if flow == "X" else CACHE_M, "%s.json" % iso)


def _has_cache(flow, iso):
    p = _cache_path(flow, iso)
    if not os.path.exists(p):
        return False
    try:
        with open(p, encoding="utf-8") as f:
            return bool(json.load(f).get("rows"))
    except (OSError, json.JSONDecodeError):
        return False


def _count(flow):
    d = CACHE_X if flow == "X" else CACHE_M
    if not os.path.isdir(d):
        return 0
    n = 0
    for fn in os.listdir(d):
        if fn.endswith(".json"):
            try:
                if json.load(open(os.path.join(d, fn), encoding="utf-8")).get("rows"):
                    n += 1
            except Exception:  # noqa: BLE001
                pass
    return n


def coverage():
    return {"exports": _count("X"), "imports": _count("M"),
            "countries": len(_countries())}


# ---------------------------------------------------------------- 合并成品
def build_trade_json():
    doc = {"generated_at": _now(),
           "source": "UN Comtrade（HS 2 位章，partner=World；出口 X / 进口 M）",
           "countries": {}}

    def load_flow(flow):
        d = CACHE_X if flow == "X" else CACHE_M
        out = {}
        if not os.path.isdir(d):
            return out
        for fn in os.listdir(d):
            if not fn.endswith(".json"):
                continue
            try:
                rec = json.load(open(os.path.join(d, fn), encoding="utf-8"))
            except Exception:  # noqa: BLE001
                continue
            rows = rec.get("rows") or []
            if not rows:
                continue
            total = sum(r["v"] for r in rows) or 0.0
            out[rec["iso3"]] = {
                "year": rec.get("year"),
                "total_usd": round(total, 2),
                "top3": [{"hs": r["hs"], "zh": hs2.zh(r["hs"]),
                          "en": hs2.en(r["hs"]),
                          "usd": round(r["v"], 2),
                          "share": round(r["v"] / total, 4) if total else None}
                         for r in rows[:3]],
            }
        return out

    ex, im = load_flow("X"), load_flow("M")
    for iso in set(ex) | set(im):
        doc["countries"][iso] = {"exports": ex.get(iso), "imports": im.get(iso)}

    os.makedirs(DATA, exist_ok=True)
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, OUT)
    return {"countries": len(doc["countries"]), "exports": len(ex), "imports": len(im),
            "bytes": os.path.getsize(OUT)}


# ---------------------------------------------------------------- 主流程
def run_flow(flow, pause=4.0, budget=None, on_tick=None):
    """抓一轮某个流向。返回 {done, nodata, failed, quota, seconds}。"""
    t0 = time.time()
    iso_list = _countries()
    rep = reporters()
    todo = [i for i in iso_list if i in rep and not _has_cache(flow, i)]
    total_known = len([i for i in iso_list if i in rep])
    result = {"done": 0, "nodata": 0, "failed": 0, "quota": False, "seconds": 0}

    for idx, iso in enumerate(todo, 1):
        if budget and (time.time() - t0) > budget:
            result["stopped_by_budget"] = True
            break
        state = {"running": True, "flow": flow, "phase": FLOW_NAME.get(flow, flow),
                 "current": iso, "index": idx, "todo": len(todo),
                 "have": _count(flow), "total": total_known,
                 "quota": False, "started_at": None}
        _write_progress(state)
        try:
            rows, year = fetch_country(rep[iso], flow)
        except QuotaExceeded as e:
            result["quota"] = True
            state.update({"quota": True, "error": str(e)})
            _write_progress(state)
            break
        except Exception as e:  # noqa: BLE001
            result["failed"] += 1
            time.sleep(8)
            continue

        rec = {"iso3": iso, "reporter_code": rep[iso], "flow": flow,
               "year": year, "rows": sorted(rows, key=lambda x: -x["v"]), "fetched_at": _now()}
        os.makedirs(os.path.dirname(_cache_path(flow, iso)), exist_ok=True)
        tmp = _cache_path(flow, iso) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp, _cache_path(flow, iso))
        if rows:
            result["done"] += 1
        else:
            result["nodata"] += 1
        time.sleep(pause)

    result["seconds"] = round(time.time() - t0, 1)
    return result


def run(mode="both", pause=4.0, budget=None):
    """后台线程入口：先出口后进口，最后合并。"""
    with _LOCK:
        if _STATE.get("running"):
            return False
        _STATE["running"] = True
    try:
        flows = {"x": ["X"], "m": ["M"], "both": ["X", "M"]}.get(mode, ["X", "M"])
        summary = {}
        for f in flows:
            summary[f] = run_flow(f, pause=pause, budget=budget)
            if summary[f].get("quota"):
                break
        summary["build"] = build_trade_json()
        _write_progress({"running": False, "phase": "完成", "summary": summary,
                         "coverage": coverage(), "quota": any(
                             (v or {}).get("quota") for k, v in summary.items() if isinstance(v, dict))})
        return summary
    finally:
        _STATE["running"] = False


def status():
    cov = coverage()
    p = read_progress()
    p["coverage"] = cov
    p["ready"] = os.path.exists(OUT)
    return p
