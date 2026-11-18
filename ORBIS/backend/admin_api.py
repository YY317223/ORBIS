#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""管理员控制台的数据查询与操作（供 app.py 路由调用）。
所有函数返回 (http_code, dict)，敏感字段已脱敏。
"""
import email
import json
import os
import re
import sqlite3
import tempfile
import threading
from email.header import decode_header

import admin_auth
import auth
import fetch_fx
import fetch_wb
import mailer
import page_data

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
WB = os.path.join(DATA, "wb.json")
FX = os.path.join(DATA, "fx.json")
SUBDB = os.path.join(DATA, "subs.db")
USERDB = os.path.join(DATA, "users.db")
OUTBOX = os.path.join(DATA, "outbox")
CONFIG = os.path.join(HERE, "config.json")


def _conn(path, readonly=True):
    if not os.path.exists(path):
        return None
    if readonly:
        uri = "file:%s?mode=ro" % path.replace("\\", "/")
        try:
            return sqlite3.connect(uri, uri=True, timeout=10)
        except sqlite3.Error:
            return None
    return sqlite3.connect(path, timeout=10)


def _rows(path, sql, args=()):
    con = _conn(path)
    if not con:
        return []
    try:
        cur = con.execute(sql, args)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    except sqlite3.Error:
        return []
    finally:
        con.close()


def _count(path, table):
    con = _conn(path)
    if not con:
        return 0
    try:
        return con.execute("SELECT COUNT(*) FROM %s" % table).fetchone()[0]
    except sqlite3.Error:
        return 0
    finally:
        con.close()


def _fmeta(path):
    if not os.path.exists(path):
        return None
    st = os.stat(path)
    return {"size": st.st_size, "mtime": __import__("datetime").datetime.fromtimestamp(
        st.st_mtime, __import__("datetime").timezone(__import__("datetime").timedelta(hours=8))
    ).isoformat(timespec="seconds")}


def overview(state, status_payload):
    st = status_payload() or {}
    outbox_n = len([f for f in os.listdir(OUTBOX) if f.endswith(".eml")]) if os.path.isdir(OUTBOX) else 0
    data = {
        "ok": True,
        "status": st,
        "users": _count(USERDB, "users"),
        "sessions": _count(USERDB, "sessions"),
        "subs": _count(SUBDB, "subs"),
        "sent": _count(SUBDB, "sent"),
        "outbox": outbox_n,
        "mail": "smtp" if mailer.ready() else "outbox",
        "fetch": {
            "fetching": bool(state.get("fetching")),
            "fx_fetching": bool(state.get("fx_fetching")),
            "last_try": state.get("last_try"),
            "error": state.get("error"),
        },
        "admin_default_password": admin_auth.is_default_password(),
    }
    return 200, data


def users(page=1, size=20, q=""):
    page = max(1, int(page or 1))
    size = min(100, max(1, int(size or 20)))
    where, args = "", []
    if q:
        where = "WHERE email LIKE ?"
        args = ["%" + q + "%"]
    total = 0
    con = _conn(USERDB)
    if con:
        try:
            total = con.execute("SELECT COUNT(*) FROM users " + where, args).fetchone()[0]
        except sqlite3.Error:
            pass
        finally:
            con.close()
    rows = _rows(USERDB,
                 "SELECT id,email,coins,member,since,created FROM users %s "
                 "ORDER BY id DESC LIMIT ? OFFSET ?" % where,
                 args + [size, (page - 1) * size])
    for r in rows:
        r["member"] = bool(r["member"])
    return 200, {"ok": True, "total": total, "page": page, "size": size, "rows": rows}


def subscriptions(page=1, size=20, q=""):
    page = max(1, int(page or 1))
    size = min(100, max(1, int(size or 20)))
    where, args = "", []
    if q:
        where = "WHERE email LIKE ? OR codes LIKE ?"
        args = ["%" + q + "%", "%" + q.upper() + "%"]
    total = 0
    con = _conn(SUBDB)
    if con:
        try:
            total = con.execute("SELECT COUNT(*) FROM subs " + where, args).fetchone()[0]
        except sqlite3.Error:
            pass
        finally:
            con.close()
    rows = _rows(SUBDB,
                 "SELECT id,email,codes,created FROM subs %s ORDER BY id DESC LIMIT ? OFFSET ?" % where,
                 args + [size, (page - 1) * size])
    for r in rows:
        r["count"] = len([x for x in (r.get("codes") or "").split(",") if x.strip()])
    return 200, {"ok": True, "total": total, "page": page, "size": size, "rows": rows}


def delete_subscription(email):
    con = _conn(SUBDB, readonly=False)
    if not con:
        return 404, {"ok": False, "error": "数据库不存在"}
    try:
        n = con.execute("DELETE FROM subs WHERE email=?", (email,)).rowcount
        con.commit()
        return 200, {"ok": True, "deleted": n}
    finally:
        con.close()


def data_status(load_doc, load_fx):
    wb = load_doc() or {}
    fx = load_fx() or {}
    out = {
        "ok": True,
        "wb": {
            "fetched_at": wb.get("fetched_at"), "source_updated": wb.get("source_updated"),
            "years": [wb.get("years", [None])[0], wb.get("years", [None])[-1]] if wb.get("years") else [],
            "countries": len(wb.get("countries") or {}), "events": len(wb.get("events") or []),
            "meta": _fmeta(WB),
        },
        "fx": {
            "date": fx.get("date"), "updated": fx.get("updated"), "base": fx.get("base"),
            "source": fx.get("source"), "count": len(fx.get("currencies") or {}),
            "meta": _fmeta(FX),
        },
    }
    return 200, out


def events(limit=50):
    doc = None
    try:
        doc = json.load(open(WB, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    ev = (doc or {}).get("events") or []
    return 200, {"ok": True, "total": len(ev), "rows": ev[:max(1, min(200, int(limit or 50)))]}


def refresh(kind, do_refresh, do_refresh_fx):
    """异步触发，不阻塞 HTTP。返回已受理。"""
    kind = (kind or "all").lower()
    if kind not in ("wb", "fx", "all"):
        return 400, {"ok": False, "error": "kind 只能是 wb/fx/all"}
    def job():
        try:
            if kind in ("wb", "all"):
                do_refresh(force=True)
            if kind in ("fx", "all"):
                do_refresh_fx(force=True)
        except Exception as e:
            print("[admin] refresh error:", e)
    threading.Thread(target=job, daemon=True).start()
    return 200, {"ok": True, "started": True, "kind": kind}


def _decode(s):
    try:
        parts = decode_header(s or "")
        return "".join(p.decode(enc or "utf-8", "replace") if isinstance(p, bytes) else p
                       for p, enc in parts)
    except Exception:
        return s or ""


def outbox():
    files = []
    if os.path.isdir(OUTBOX):
        for name in sorted(os.listdir(OUTBOX), reverse=True):
            if not name.endswith(".eml"):
                continue
            path = os.path.join(OUTBOX, name)
            try:
                msg = email.message_from_binary_file(open(path, "rb"))
                files.append({
                    "name": name,
                    "to": _decode(msg.get("To")),
                    "subject": _decode(msg.get("Subject")),
                    "date": msg.get("Date"),
                    "size": os.path.getsize(path),
                })
            except Exception:
                files.append({"name": name, "to": "", "subject": "", "date": "", "size": 0})
    return 200, {"ok": True, "files": files[:200]}


def outbox_read(name, raw=False):
    if not name or "/" in name or "\\" in name or ".." in name or not name.endswith(".eml"):
        return 400, {"ok": False, "error": "非法文件名"}
    path = os.path.join(OUTBOX, name)
    if not os.path.exists(path):
        return 404, {"ok": False, "error": "文件不存在"}
    if raw:
        return 200, open(path, "rb").read()
    try:
        msg = email.message_from_binary_file(open(path, "rb"))
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", "replace")
                    break
        else:
            body = msg.get_payload(decode=True).decode(
                msg.get_content_charset() or "utf-8", "replace")
        return 200, {"ok": True, "headers": {
            "to": _decode(msg.get("To")), "subject": _decode(msg.get("Subject")),
            "date": msg.get("Date")}, "text": body[:20000]}
    except Exception as e:
        return 500, {"ok": False, "error": str(e)}


def mail_test(to, subject, text, send):
    if not to or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", to):
        return 400, {"ok": False, "error": "收件邮箱格式不对"}
    subject = subject or "ORBIS 后台测试邮件"
    text = text or "这是一封来自 ORBIS 管理后台的测试邮件。"
    try:
        kind, detail = send(to, subject, text)
        return 200, {"ok": kind != "error", "kind": kind, "detail": str(detail)[:300]}
    except Exception as e:
        return 500, {"ok": False, "error": str(e)}


def settings():
    cfg = {}
    try:
        cfg = json.load(open(CONFIG, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    smtp = cfg.get("smtp") or {}
    return 200, {"ok": True, "username": admin_auth.username(), "smtp": {
        "host": smtp.get("host", ""), "port": smtp.get("port", 465),
        "ssl": smtp.get("ssl", True), "from": smtp.get("from", ""),
        "user": smtp.get("user", ""),
        "configured": bool(smtp.get("host") and smtp.get("password")),
    }, "default_password": admin_auth.is_default_password()}


def change_password(old, new):
    ok, err = admin_auth.set_password(new, old)
    return (200 if ok else 400), {"ok": ok, "error": err}


# ============================================================
# 待审数据通道（独立暂存区，不影响现有自动抓取/发布流程）
# ============================================================
import staging as _stage


def stage_list():
    return 200, {"ok": True, "rows": _stage.list_batches(),
                 "targets": list(_stage.PUBLISH_TARGETS.keys())}


def stage_get(bid):
    meta = _stage.get_batch(bid)
    if not meta:
        return 404, {"ok": False, "error": "批次不存在"}
    return 200, {"ok": True, "batch": meta}


def stage_preview(bid, name, limit=5):
    data = _stage.preview(bid, name, limit)
    if data is None:
        return 404, {"ok": False, "error": "文件不存在或无法解析"}
    return 200, {"ok": True, "name": name, "data": data}


def stage_compare(bid, name):
    diffs = _stage.compare(bid, name)
    if diffs is None:
        return 400, {"ok": False, "error": "该文件不支持差异对比"}
    return 200, {"ok": True, **diffs}


def stage_countries(bid, name="wb.json"):
    """逐国明细（人口 / GDP / 人均 / 出口前三），无变化的国家也返回。"""
    data = _stage.countries(bid, name)
    if data is None:
        return 404, {"ok": False, "error": "批次或文件不存在"}
    try:
        import trade
        data["trade"] = trade.coverage()
    except Exception:  # noqa: BLE001
        data["trade"] = {"ready": False}
    return 200, {"ok": True, **data}


def stage_fetch(kind, do_notify=None):
    """抓取新数据到暂存区（不覆盖正式文件）。kind: wb / fx / all。"""
    kind = (kind or "wb").lower()
    if kind not in ("wb", "fx", "all"):
        return 400, {"ok": False, "error": "kind 只能是 wb/fx/all"}
    files = {}
    note = []
    try:
        if kind in ("wb", "all"):
            doc = fetch_wb.build()
            files["wb.json"] = doc
            note.append("世行数据 %s（%d 国，%d 事件）" % (
                doc.get("fetched_at"), len(doc.get("countries") or {}),
                len(doc.get("events") or [])))
    except Exception as e:  # noqa: BLE001
        return 500, {"ok": False, "error": "世行数据抓取失败: %s" % e}
    if kind in ("fx", "all"):
        old_out = fetch_fx.OUT
        try:
            # 抓到临时文件再把内容交给 staging，避免碰正式 fx.json
            fd, tmppath = tempfile.mkstemp(prefix="fxstage_", suffix=".json", dir=_stage.STAGE)
            os.close(fd)
            fetch_fx.OUT = tmppath
            doc = fetch_fx.run(verbose=False)
            files["fx.json"] = doc
            note.append("汇率 %s（%d 币种）" % (doc.get("date"), len(doc.get("currencies") or {})))
            try:
                os.remove(tmppath)
            except OSError:
                pass
        except Exception as e:  # noqa: BLE001
            return 500, {"ok": False, "error": "汇率抓取失败: %s" % e}
        finally:
            fetch_fx.OUT = old_out
    ok, info = _stage.create(source="fetch:" + kind, note="；".join(note), files=files)
    if not ok:
        return 500, {"ok": False, "error": str(info)}
    return 200, {"ok": True, "batch": info}


def stage_publish(bid, names=None, reload_doc=None, reload_fx=None, do_notify=None):
    ok, info = _stage.publish(bid, names)
    if not ok:
        return 400, {"ok": False, "error": str(info)}
    # 发布后刷新内存缓存，让页面/接口立刻用上新数据（不影响调度线程）
    try:
        published = info.get("published") or []
        if "wb.json" in published:
            doc = reload_doc() if reload_doc else None
            if doc and do_notify:
                do_notify(doc)   # 发布时触发订阅提醒（与原自动流程一致）
            # 审核通过 = 数据正式上页面：合并进 data.js 并重建 orbis.html
            try:
                info["page"] = page_data.apply_and_rebuild()
            except Exception as e:  # noqa: BLE001
                info["page"] = {"error": str(e)[:200]}
                print("[admin] 审核发布后重建页面失败:", e)
        if "fx.json" in published and reload_fx:
            reload_fx()
    except Exception as e:  # noqa: BLE001
        print("[admin] post-publish refresh error:", e)
    return 200, {"ok": True, **info}


def stage_reject(bid):
    ok, info = _stage.reject(bid)
    return (200 if ok else 400), {"ok": ok, **({"error": info} if not ok else info)}


# ============================================================
# 爬虫应用：两种更新模式
#   auto   = 每月自动更新，抓完直接上页面，不审核
#   review = 实时更新，抓完进待审区，管理员通过后才上页面
# ============================================================
import crawler as _crawler


def crawler_status():
    try:
        return 200, _crawler.status()
    except Exception as e:  # noqa: BLE001
        return 500, {"ok": False, "error": str(e)}


def crawler_config(day, hour, minute, enabled):
    try:
        cfg = _crawler.load_cfg()
        a = cfg["auto"]
        a["day"] = max(1, min(28, int(day)))
        a["hour"] = max(0, min(23, int(hour)))
        a["minute"] = max(0, min(59, int(minute)))
        a["enabled"] = bool(enabled)
        cfg["next_run"] = _crawler._iso(_crawler.next_occurrence(a["day"], a["hour"], a["minute"]))
        _crawler.save_cfg(cfg)
        return 200, {"ok": True, "auto": a, "next_run": cfg["next_run"]}
    except Exception as e:  # noqa: BLE001
        return 400, {"ok": False, "error": str(e)}


def crawler_run(mode):
    """mode=auto: 后台直接更新；mode=review: 抓到待审区等管理员审批。"""
    mode = (mode or "auto").lower()
    if mode == "auto":
        def job():
            ok, info = _crawler.run_auto(trigger="admin")
            print("[admin] 自动更新完成:", ok, info.get("error") or info.get("version"))
        threading.Thread(target=job, daemon=True).start()
        return 200, {"ok": True, "started": True, "mode": "auto",
                     "note": "抓取完成后直接更新到页面，无需审核"}
    if mode == "review":
        return stage_fetch("all")
    return 400, {"ok": False, "error": "mode 只能是 auto / review"}
