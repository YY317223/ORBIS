#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ORBIS · 本地数据服务（纯标准库）

    python app.py                # 默认 http://127.0.0.1:8765
    python app.py --port 9000
    python app.py --once         # 只抓一次数据就退出（给 cron / 计划任务用）

它做四件事：
  1. 每 12 小时检查一次世界银行数据，抓到新数据就落盘 data/wb.json
  2. 提供 /api/* 给页面：状态灯、在线数据、订阅、取消订阅
  3. 数据「大变」（新增年份或修正超阈值）时，给订阅了该国的邮箱发信
  4. 顺便把 orbis.html 用 HTTP 发出去，这样页面能直接调 API
"""
import argparse
import gzip
import json
import os
import secrets
import sqlite3
import threading
import time
import traceback
import webbrowser
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote

import fetch_wb
import mailer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(HERE, "data")
WB = os.path.join(DATA, "wb.json")
DB = os.path.join(DATA, "subs.db")
PAGE = os.path.join(ROOT, "orbis.html")

HOST = os.environ.get("HOST", "127.0.0.1")   # 公网部署：HOST=0.0.0.0
PORT = int(os.environ.get("PORT", "8765"))
FETCH_HOURS = float(os.environ.get("FETCH_HOURS", "12"))
CHECK_MIN = 10  # 调度线程检查间隔（分钟）

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:%s" % os.environ.get("PORT", "8765"))

CN = {"pc": "人均 GDP", "gdp": "GDP", "pop": "人口", "le": "预期寿命"}
UNIT = {"pc": "美元", "gdp": "美元", "pop": "人", "le": "岁"}

_GZ = {"key": None, "raw": b"", "gz": b""}

STATE = {
    "fetching": False,
    "error": None,
    "last_try": None,
    "doc": None,
    "notified": 0,
}


def now():
    return datetime.now(timezone(timedelta(hours=8)))


def load_doc():
    if STATE["doc"] is not None:
        return STATE["doc"]
    if os.path.exists(WB):
        try:
            with open(WB, encoding="utf-8") as f:
                STATE["doc"] = json.load(f)
        except (OSError, json.JSONDecodeError):
            STATE["doc"] = None
    return STATE["doc"]


def db():
    os.makedirs(DATA, exist_ok=True)
    con = sqlite3.connect(DB, timeout=10)
    con.execute(
        "CREATE TABLE IF NOT EXISTS subs("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " email TEXT UNIQUE NOT NULL,"
        " codes TEXT NOT NULL,"
        " token TEXT NOT NULL,"
        " created TEXT NOT NULL)"
    )
    con.execute(
        "CREATE TABLE IF NOT EXISTS sent(k TEXT PRIMARY KEY, at TEXT NOT NULL)"
    )
    return con


def fmt(code, v):
    if v is None:
        return "—"
    if code == "gdp":
        return "%.2f 万亿美元" % (v / 1e12) if v >= 1e12 else "%.0f 亿美元" % (v / 1e8)
    if code == "pop":
        return "%.2f 亿人" % (v / 1e8) if v >= 1e8 else "%.0f 万人" % (v / 1e4)
    if code == "pc":
        return "%s 美元" % format(int(round(v)), ",")
    return "%.1f 岁" % v


_NAMES = None


def cn_names():
    """从页面数据里取 iso3 -> 中文名，邮件正文用中文。"""
    global _NAMES
    if _NAMES is not None:
        return _NAMES
    _NAMES = {}
    try:
        with open(os.path.join(ROOT, "data.js"), encoding="utf-8") as f:
            s = f.read()
        d = json.loads(s[s.index("{"): s.rindex("}") + 1])
        for c in d.get("countries", []):
            iso = (c.get("iso3") or "").upper()
            if iso and c.get("n"):
                _NAMES[iso] = c["n"]
            for alias in (c.get("alias") or []):
                pass
    except (OSError, ValueError, json.JSONDecodeError):
        pass
    return _NAMES


def name_of(doc, iso):
    return (doc.get("names") or {}).get(iso) or cn_names().get(iso) or iso


def mail_shell(title, body, unsub, when=""):
    """邮件统一外壳：标题 + 正文 + 页脚退订。退订链接必须每封都带。"""
    return (
        "<div style=\"font:15px/1.75 -apple-system,'Segoe UI',Roboto,'PingFang SC',"
        "sans-serif;color:#1b2430;max-width:560px;margin:0 auto;padding:22px 24px;"
        "background:#fff;border:1px solid #e7ecf2;border-radius:12px\">"
        "<div style=\"font-size:11px;letter-spacing:.16em;color:#8b98a8;margin-bottom:10px\">"
        "ORBIS · 数据提醒</div>"
        "<h3 style=\"margin:0 0 12px;font-size:17px;font-weight:600\">%s</h3>%s"
        "<p style=\"margin:18px 0 0;padding-top:12px;border-top:1px solid #eef1f5;"
        "color:#8b98a8;font-size:12.5px\">%s"
        "<a href=\"%s\" style=\"color:#8b98a8\">不想再收，点此退订</a></p></div>"
        % (title, body, ("数据更新于 %s　·　" % when) if when else "", unsub)
    )


def html_page(title, msg, tone="#3f8f5a"):
    """给浏览器看的简单结果页（退订链接点开时用，不是 JSON）。"""
    return ("<!doctype html><html lang=\"zh-CN\"><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<title>%s</title>"
            "<div style=\"font:16px/1.8 -apple-system,'Segoe UI','PingFang SC',sans-serif;"
            "max-width:440px;margin:16vh auto;padding:28px 30px;background:#0d1219;"
            "color:#e8eef7;border-radius:14px;border:1px solid #1e2836\">"
            "<div style=\"font-size:11px;letter-spacing:.18em;color:#6f7d90;margin-bottom:12px\">"
            "ORBIS</div>"
            "<h2 style=\"margin:0 0 10px;font-size:19px;color:%s\">%s</h2>"
            "<p style=\"margin:0;color:#9fb0c4;font-size:14px\">%s</p></div></html>"
            % (title, tone, title, msg))


def notify(doc):
    """把 events 按国家聚合，给订阅者发信；同一事件只发一次。"""
    events = doc.get("events") or []
    if not events:
        return 0
    by_iso = {}
    for e in events:
        by_iso.setdefault(e["iso"], []).append(e)
    con = db()
    sent = 0
    try:
        rows = con.execute("SELECT email, codes, token FROM subs").fetchall()
        for email, codes, token in rows:
            watch = set(x.strip().upper() for x in (codes or "").split(",") if x.strip())
            hit = [iso for iso in by_iso if iso in watch]
            if not hit:
                continue
            lines, html_items, fresh = [], [], False
            for iso in hit:
                for e in by_iso[iso]:
                    key = "%s:%s:%s:%s" % (iso, e["ind"], e["year"], round(float(e["new"]), 2))
                    if con.execute("SELECT 1 FROM sent WHERE k=?", (key,)).fetchone():
                        continue
                    fresh = True
                    arrow = "↑" if e["new"] > e["old"] else "↓"
                    pct = ""
                    if e["ind"] != "le" and e["old"]:
                        pct = "（%+.1f%%）" % ((e["new"] - e["old"]) / abs(e["old"]) * 100)
                    lines.append("%s %s %d 年：%s %s %s%s" % (
                        name_of(doc, iso), CN[e["ind"]], e["year"],
                        fmt(e["ind"], e["old"]), arrow, fmt(e["ind"], e["new"]), pct))
                    html_items.append("<li>%s</li>" % lines[-1])
                    con.execute("INSERT OR IGNORE INTO sent(k,at) VALUES(?,?)",
                                (key, now().isoformat(timespec="seconds")))
            if not fresh:
                continue
            subject = "数据提醒：%s 有新变化" % "、".join(name_of(doc, i) for i in hit[:3])
            unsub = "%s/api/unsubscribe?token=%s" % (BASE_URL, token)
            text = ("你关注的国家数据出现变化：\n\n" + "\n".join(lines) +
                    "\n\n—— ORBIS · 数据更新于 %s\n不想再收：%s"
                    % (doc.get("fetched_at", ""), unsub))
            html = mail_shell("你关注的国家有新变化",
                              "<ul style='margin:0 0 4px;padding-left:20px'>%s</ul>"
                              % "".join(html_items),
                              unsub, doc.get("fetched_at", ""))
            kind, detail = mailer.send(email, subject, text, html, {
                "List-Unsubscribe": "<%s>" % unsub,
                "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
            })
            if kind != "error":
                sent += 1
                print("[notify] %s -> %s (%s)" % (email, subject, kind))
        con.commit()
    finally:
        con.close()
    STATE["notified"] = sent
    return sent


def refresh(force=False):
    if STATE["fetching"]:
        return False
    doc = load_doc()
    if not force and doc:
        try:
            last = datetime.fromisoformat(doc["fetched_at"])
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone(timedelta(hours=8)))
            if now() - last < timedelta(hours=FETCH_HOURS):
                return False
        except (KeyError, ValueError):
            pass
    STATE["fetching"] = True
    STATE["last_try"] = now().isoformat(timespec="seconds")
    try:
        new = fetch_wb.run(verbose=True)
        STATE["doc"] = new
        STATE["error"] = None
        if new.get("events"):
            notify(new)
        return True
    except Exception as e:  # noqa: BLE001
        STATE["error"] = str(e)
        print("[fetch] error:", e)
        traceback.print_exc()
        return False
    finally:
        STATE["fetching"] = False


def scheduler():
    while True:
        try:
            refresh()
        except Exception as e:  # noqa: BLE001
            STATE["error"] = str(e)
        time.sleep(CHECK_MIN * 60)


def status_payload():
    doc = load_doc()
    if not doc:
        return {"ok": False, "error": STATE["error"] or "no data", "fetching": STATE["fetching"]}
    years = doc.get("years") or []
    last = doc.get("fetched_at")
    age_h = None
    try:
        dt = datetime.fromisoformat(last)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone(timedelta(hours=8)))
        age_h = round((now() - dt).total_seconds() / 3600, 1)
    except (TypeError, ValueError):
        pass
    con = db()
    try:
        subs = con.execute("SELECT COUNT(*) FROM subs").fetchone()[0]
    finally:
        con.close()
    return {
        "ok": True,
        "last_fetch": last,
        "age_hours": age_h,
        "source_updated": doc.get("source_updated"),
        "years": [years[0], years[-1]] if years else [],
        "countries": len(doc.get("countries") or {}),
        "events": len(doc.get("events") or []),
        "fetching": STATE["fetching"],
        "error": STATE["error"],
        "mail": "smtp" if mailer.ready() else "outbox",
        "subs": subs,
        "next_check_hours": FETCH_HOURS,
        "server_time": now().isoformat(timespec="seconds"),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "SpaceEarth/1.1"

    def log_message(self, fmt, *args):
        if args and str(args[0]).startswith("/api/status"):
            return
        print("[http] " + fmt % args)

    def _send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(204, b"")

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        u = urlparse(self.path)
        p = unquote(u.path)   # 中文路径在请求行里是 %XX 编码，解出来才能匹配
        q = parse_qs(u.query)
        if p in ("/", "/index.html", "/orbis.html", "/太空地球.html"):
            return self.serve_page()
        if p == "/api/status":
            return self._send(200, status_payload())
        if p == "/api/wb":
            doc = load_doc()
            return self._send(200, doc or {"ok": False})
        if p == "/api/country":
            doc = load_doc() or {}
            iso = (q.get("iso", [""])[0] or "").upper()
            c = (doc.get("countries") or {}).get(iso)
            if not c:
                return self._send(404, {"ok": False, "error": "unknown iso"})
            return self._send(200, {"ok": True, "iso": iso, "years": doc.get("years"), "values": c})
        if p == "/api/subscriptions":
            con = db()
            try:
                rows = con.execute("SELECT email, codes, created FROM subs ORDER BY id DESC LIMIT 200").fetchall()
            finally:
                con.close()
            return self._send(200, {"ok": True, "rows": [
                {"email": r[0], "codes": r[1], "created": r[2]} for r in rows]})
        if p == "/api/unsubscribe":
            token = (q.get("token", [""])[0] or "").strip()
            as_json = (q.get("fmt", [""])[0] or "") == "json"
            if not token:
                if as_json:
                    return self._send(400, {"ok": False, "error": "missing token"})
                return self._send(400, html_page("链接不完整", "这个退订链接少了凭证，换一封邮件点一次试试。",
                                                 "#c9773f"), "text/html; charset=utf-8")
            con = db()
            try:
                cur = con.execute("DELETE FROM subs WHERE token=?", (token,))
                con.commit()
                n = cur.rowcount
            finally:
                con.close()
            if as_json:
                return self._send(200, {"ok": n > 0})
            if n > 0:
                return self._send(200, html_page("已退订", "不会再收到数据提醒了。想重新订阅，回页面留一次邮箱就行。"),
                                  "text/html; charset=utf-8")
            return self._send(404, html_page("已经退订过了", "这个链接对应的订阅已不存在，不用再操作。",
                                             "#8b98a8"), "text/html; charset=utf-8")
        return self._send(404, {"ok": False, "error": "not found"})

    def do_POST(self):
        u = urlparse(self.path)
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self._send(400, {"ok": False, "error": "bad json"})

        if u.path == "/api/subscribe":
            email = (body.get("email") or "").strip().lower()
            codes = [str(x).strip().upper() for x in (body.get("codes") or []) if str(x).strip()]
            if "@" not in email or len(email) < 5 or "." not in email.split("@")[-1]:
                return self._send(400, {"ok": False, "error": "邮箱格式不对"})
            if not codes:
                return self._send(400, {"ok": False, "error": "先选几个国家"})
            con = db()
            try:
                old = con.execute("SELECT token, codes FROM subs WHERE email=?", (email,)).fetchone()
                is_new = old is None
                if old:
                    merged = sorted(set((old[1] or "").split(",")) | set(codes) - {""})
                    con.execute("UPDATE subs SET codes=? WHERE email=?", (",".join(merged), email))
                    token = old[0]
                else:
                    token = secrets.token_urlsafe(12)
                    con.execute(
                        "INSERT INTO subs(email,codes,token,created) VALUES(?,?,?,?)",
                        (email, ",".join(sorted(set(codes))), token, now().isoformat(timespec="seconds")),
                    )
                con.commit()
                n = len(con.execute("SELECT codes FROM subs WHERE email=?", (email,)).fetchone()[0].split(","))
            finally:
                con.close()
            confirm = "skip"
            try:  # 确认信失败不影响订阅本身
                unsub = "%s/api/unsubscribe?token=%s" % (BASE_URL, token)
                names = [cn_names().get(c) or c for c in codes]
                head = "订阅成功" if is_new else "关注范围已更新"
                subject = "%s：%s" % (head, "、".join(names[:3]))
                text = ("%s。现在盯着：%s\n\n"
                        "世界银行公布的新数据里，这些国家出现「大变」（新增年份，或修正超过阈值）时，"
                        "就会发一封邮件到这里。不想要了，点下面的链接即可，一次退干净。\n\n"
                        "—— ORBIS\n退订：%s" % (head, "、".join(names), unsub))
                html = mail_shell(head, "<p style=\"margin:0;color:#42505f\">现在盯着 <b>%s</b>。"
                                        "数据出现「大变」时发信到这里。</p>" % "、".join(names),
                                  unsub, "")
                kind, _ = mailer.send(email, subject, text, html,
                                      {"List-Unsubscribe": "<%s>" % unsub})
                confirm = kind
            except Exception:  # noqa: BLE001
                traceback.print_exc()
            return self._send(200, {"ok": True, "email": email, "codes": codes, "watched": n,
                                    "token": token, "mail": "smtp" if mailer.ready() else "outbox",
                                    "confirm": confirm})

        if u.path == "/api/unsubscribe":
            email = (body.get("email") or "").strip().lower()
            con = db()
            try:
                cur = con.execute("DELETE FROM subs WHERE email=?", (email,))
                con.commit()
                return self._send(200, {"ok": cur.rowcount > 0})
            finally:
                con.close()

        if u.path == "/api/refresh":
            ok = refresh(force=True)
            return self._send(200, {"ok": ok, "status": status_payload()})

        if u.path == "/api/notify":
            doc = load_doc() or {}
            n = notify(doc)
            return self._send(200, {"ok": True, "sent": n})

        return self._send(404, {"ok": False, "error": "not found"})

    def serve_page(self):
        if not os.path.exists(PAGE):
            return self._send(404, "orbis.html 不存在，请先运行 build/build_globe.py", "text/plain; charset=utf-8")
        st = os.stat(PAGE)
        key = (st.st_mtime_ns, st.st_size)
        if _GZ["key"] != key:          # 单文件 11MB，按修改时间缓存一份 gzip，别每次现压
            with open(PAGE, "rb") as f:
                raw = f.read()
            _GZ["raw"] = raw
            _GZ["gz"] = gzip.compress(raw, 6)
            _GZ["key"] = key
        use_gz = "gzip" in (self.headers.get("Accept-Encoding") or "")
        body = _GZ["gz"] if use_gz else _GZ["raw"]
        # 带上编码的 ETag：同一个页面在 gzip / 原始两种形态下不能共用同一个校验值
        etag = '"%x-%x%s"' % (st.st_mtime_ns, st.st_size, "-gz" if use_gz else "")
        if (self.headers.get("If-None-Match") or "").strip() == etag:
            self.send_response(304)
            self.send_header("ETag", etag)
            self.send_header("Cache-Control", "public, max-age=3600, must-revalidate")
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("ETag", etag)
        self.send_header("Cache-Control", "public, max-age=3600, must-revalidate")
        if use_gz:
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Vary", "Accept-Encoding")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--host", default=HOST, help="监听地址，公网部署用 0.0.0.0")
    ap.add_argument("--once", action="store_true", help="只抓一次数据然后退出")
    ap.add_argument("--no-fetch", action="store_true", help="启动时不抓取，只用已有数据")
    ap.add_argument("--open", action="store_true", help="启动后自动用浏览器打开页面")
    a = ap.parse_args()

    if a.once:
        doc = fetch_wb.run()
        if doc.get("events"):
            notify(doc)
        return

    db().close()
    if not a.no_fetch:
        threading.Thread(target=refresh, args=(True,), daemon=True).start()
    threading.Thread(target=scheduler, daemon=True).start()

    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    st = status_payload()
    url = "http://127.0.0.1:%d" % a.port
    print("=" * 62)
    print(" ORBIS · 数据服务")
    print("   " + url + "   （在线模式：状态灯、真实数据、订阅）")
    print("   数据：%s   国家 %s   邮件：%s" % (
        ("%s（%s）" % (st.get("years"), st.get("last_fetch"))) if st.get("ok") else "尚未就绪",
        st.get("countries"), st.get("mail")))
    print("   抓取节奏：每 %g 小时一次   下次不晚于 %s" % (
        FETCH_HOURS, (now() + timedelta(hours=FETCH_HOURS)).strftime("%m-%d %H:%M")))
    print("   双保险：%s --once 可挂到系统计划任务，每天跑一次" % os.path.basename(__file__))
    print("   Ctrl+C 停止")
    print("=" * 62)
    if a.open:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n[exit] bye")
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
