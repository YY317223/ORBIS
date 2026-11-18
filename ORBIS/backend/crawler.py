#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""爬虫应用：两种更新模式。

模式一 · 每月自动更新（无需审核）
    到点自动抓世行 + 汇率，直接覆盖正式数据，并重建 data.js / orbis.html。
    用户刷新页面就能看到新数据。记录写进 data/crawler_log.json。

模式二 · 实时更新（需管理员审批）
    抓取结果只进 staging 暂存区，管理员在「数据审核」页人工检查后点通过，
    才由 page_data 合并进 data.js 并重建页面。

调度：scheduler_loop 每 60 秒检查一次，到点触发模式一。由 app.py 启动。
"""
import json
import os
import threading
import time
from datetime import datetime, timedelta, timezone

import fetch_fx
import fetch_wb
import page_data

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CONFIG = os.path.join(DATA, "crawler.json")
LOG = os.path.join(DATA, "crawler_log.json")
LOCK = threading.Lock()

DEFAULT_CFG = {
    "auto": {"enabled": True, "day": 5, "hour": 6, "minute": 0},
    "last_run": None,
    "last_result": None,
    "next_run": None,
}


def _now():
    return datetime.now(timezone(timedelta(hours=8)))


def _iso(dt):
    return dt.isoformat(timespec="seconds")


def load_cfg():
    try:
        with open(CONFIG, encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, json.JSONDecodeError):
        cfg = {}
    out = json.loads(json.dumps(DEFAULT_CFG))
    out["auto"].update(cfg.get("auto") or {})
    for k in ("last_run", "last_result", "next_run"):
        if cfg.get(k):
            out[k] = cfg[k]
    return out


def save_cfg(cfg):
    os.makedirs(DATA, exist_ok=True)
    tmp = CONFIG + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CONFIG)


def next_occurrence(day, hour, minute, after=None):
    """下一次「每月 day 号 hour:minute」。day 超出当月天数时取当月最后一天。"""
    after = after or _now()
    y, m = after.year, after.month
    for _ in range(14):
        # 当月候选
        if m == 12:
            ny, nm = y + 1, 1
        else:
            ny, nm = y, m + 1
        last_day = (datetime(ny, nm, 1) - timedelta(days=1)).day
        d = min(max(1, int(day)), last_day)
        cand = datetime(y, m, d, int(hour), int(minute), tzinfo=after.tzinfo)
        if cand > after:
            return cand
        y, m = ny, nm
    return after + timedelta(days=30)


def _log(entry):
    rows = []
    try:
        with open(LOG, encoding="utf-8") as f:
            rows = json.load(f)
        if not isinstance(rows, list):
            rows = []
    except (OSError, json.JSONDecodeError):
        rows = []
    entry["at"] = _iso(_now())
    rows.insert(0, entry)
    tmp = LOG + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rows[:60], f, ensure_ascii=False, indent=2)
    os.replace(tmp, LOG)


def recent_log(limit=10):
    try:
        with open(LOG, encoding="utf-8") as f:
            rows = json.load(f)
        return (rows if isinstance(rows, list) else [])[: max(1, int(limit))]
    except (OSError, json.JSONDecodeError):
        return []


def run_auto(trigger="manual"):
    """模式一：抓取 → 直接发布 → 重建页面。不经过审核。"""
    if not LOCK.acquire(blocking=False):
        return False, "已有更新任务在执行"
    t0 = time.time()
    try:
        wb_ok, fx_ok, err = True, True, []
        try:
            doc = fetch_wb.run(verbose=False)
            wb_note = "%s 年轴 %s-%s" % (doc.get("fetched_at"), doc.get("years")[0], doc.get("years")[-1])
        except Exception as e:  # noqa: BLE001
            wb_ok = False
            wb_note = str(e)[:120]
            err.append("世行: %s" % str(e)[:120])
        try:
            fx_doc = fetch_fx.run(verbose=False)
            fx_note = "%s %d 币种" % (fx_doc.get("date"), len(fx_doc.get("currencies") or {}))
        except Exception as e:  # noqa: BLE001
            fx_ok = False
            fx_note = str(e)[:120]
            err.append("汇率: %s" % str(e)[:120])

        page = None
        if wb_ok:
            try:
                page = page_data.apply_and_rebuild()
            except Exception as e:  # noqa: BLE001
                err.append("页面重建: %s" % str(e)[:160])

        # 贸易数据（出口/进口前三）在后台续抓：限速严，给它 30 分钟预算，
        # 抓不完下次接着来，不影响本次更新时间。
        trade_started = False
        try:
            import trade_fetch
            if not trade_fetch.status().get("running"):
                threading.Thread(target=trade_fetch.run, kwargs={"mode": "both", "budget": 1800},
                                 daemon=True).start()
                trade_started = True
        except Exception as e:  # noqa: BLE001
            err.append("贸易抓取: %s" % str(e)[:120])

        ok = wb_ok and fx_ok and page is not None
        entry = {
            "mode": "auto", "trigger": trigger, "ok": ok,
            "wb": wb_note, "fx": fx_note,
            "version": (page or {}).get("version"),
            "years": (page or {}).get("years"),
            "countries": (page or {}).get("countries"),
            "page_bytes": (page or {}).get("bytes"),
            "seconds": round(time.time() - t0, 1),
            "trade_started": trade_started,
            "error": "；".join(err) or None,
        }
        _log(entry)

        cfg = load_cfg()
        cfg["last_run"] = entry["at"]
        cfg["last_result"] = {"ok": ok, "mode": trigger, "version": entry.get("version"),
                              "error": entry["error"]}
        a = cfg["auto"]
        cfg["next_run"] = _iso(next_occurrence(a["day"], a["hour"], a["minute"]))
        save_cfg(cfg)
        return ok, entry
    finally:
        LOCK.release()


def status():
    cfg = load_cfg()
    a = cfg["auto"]
    nxt = cfg.get("next_run") or _iso(next_occurrence(a["day"], a["hour"], a["minute"]))
    pending = []
    try:
        import staging
        pending = [b for b in staging.list_batches() if b.get("status") == "pending"]
    except Exception:  # noqa: BLE001
        pending = []
    return {
        "ok": True,
        "auto": a,
        "next_run": nxt,
        "last_run": cfg.get("last_run"),
        "last_result": cfg.get("last_result"),
        "pending_batches": len(pending),
        "log": recent_log(8),
        "version": page_data.version_label(),
        "now": _iso(_now()),
    }


def scheduler_loop(stop_event=None, interval=60):
    """常驻线程：到点触发模式一。"""
    time.sleep(3)  # 让服务先起来
    while not (stop_event and stop_event.is_set()):
        try:
            cfg = load_cfg()
            a = cfg["auto"]
            if a.get("enabled"):
                nxt = cfg.get("next_run")
                due_at = datetime.fromisoformat(nxt) if nxt else next_occurrence(
                    a["day"], a["hour"], a["minute"])
                if _now() >= due_at:
                    print("[crawler] 自动更新开始：%s" % _iso(_now()))
                    ok, info = run_auto(trigger="schedule")
                    print("[crawler] 自动更新%s：%s" % ("成功" if ok else "失败", info.get("error") or info.get("version")))
        except Exception as e:  # noqa: BLE001
            print("[crawler] 调度异常:", e)
        time.sleep(interval)


if __name__ == "__main__":
    import sys
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").lower()
    if cmd == "auto":
        ok, info = run_auto(trigger="cli")
        print(json.dumps({"ok": ok, "info": info}, ensure_ascii=False, indent=2))
        sys.exit(0 if ok else 1)
    elif cmd == "next":
        cfg = load_cfg()
        a = cfg["auto"]
        print("下次自动更新:", _iso(next_occurrence(a["day"], a["hour"], a["minute"])))
    else:
        print(json.dumps(status(), ensure_ascii=False, indent=2))
