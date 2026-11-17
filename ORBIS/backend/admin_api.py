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
import threading
from email.header import decode_header

import admin_auth
import auth
import fetch_fx
import fetch_wb
import mailer

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
