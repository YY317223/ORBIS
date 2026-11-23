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
import fetch_fx
import mailer
import auth
import admin_auth
import admin_api
import crawler
import on_demand

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(HERE, "data")
WB = os.path.join(DATA, "wb.json")
FX = os.path.join(DATA, "fx.json")
FX_HOURS = float(os.environ.get("FX_HOURS", "6"))   # 汇率刷新间隔（央行牌价每天发布，6h 足够跟上）
DB = os.path.join(DATA, "subs.db")
PAGE = os.path.join(ROOT, "orbis.html")
ADMIN_PAGE = os.path.join(ROOT, "admin.html")

HOST = os.environ.get("HOST", "127.0.0.1")   # 公网部署：HOST=0.0.0.0
PORT = int(os.environ.get("PORT", "8765"))
FETCH_HOURS = float(os.environ.get("FETCH_HOURS", "12"))
CHECK_MIN = 10  # 调度线程检查间隔（分钟）

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:%s" % os.environ.get("PORT", "8765"))
# 允许跨域带凭据的来源（本地 file:// 打开时用在线地址登录）
CORS_ORIGINS = set(x.strip() for x in os.environ.get(
    "CORS_ORIGINS",
    "http://8.137.183.172:8080,http://localhost:8080,http://127.0.0.1:8080"
).split(",") if x.strip())

CN = {"pc": "人均 GDP", "gdp": "GDP", "pop": "人口", "le": "预期寿命"}
UNIT = {"pc": "美元", "gdp": "美元", "pop": "人", "le": "岁"}

_GZ = {"key": None, "raw": b"", "gz": b""}

STATE = {
    "fetching": False,
    "error": None,
    "last_try": None,
    "doc": None,
    "doc_key": None,
    "fx": None,
    "fx_fetching": False,
    "notified": 0,
}


def load_fx():
    """读汇率缓存（文件优先于内存，便于外部手动更新 fx.json 后即时生效）。"""
    try:
        if os.path.exists(FX):
            with open(FX, encoding="utf-8") as f:
                STATE["fx"] = json.load(f)
    except (OSError, json.JSONDecodeError):
        pass
    return STATE["fx"]


def refresh_fx(force=False):
    """汇率刷新：独立节奏，失败不影响主数据。返回是否真的抓了。"""
    if STATE["fx_fetching"]:
        return False
    fx = STATE["fx"] or load_fx()
    if not force and fx:
        try:
            last = datetime.fromisoformat(fx["updated"])
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone(timedelta(hours=8)))
            if now() - last < timedelta(hours=FX_HOURS):
                return False
        except (KeyError, ValueError):
            pass
    STATE["fx_fetching"] = True
    try:
        STATE["fx"] = fetch_fx.run(verbose=True)
        print("[fx] refreshed at", now().isoformat(timespec="seconds"))
        return True
    except Exception as e:  # noqa: BLE001
        print("[fx] error:", e)
        traceback.print_exc()
        return False
    finally:
        STATE["fx_fetching"] = False


def now():
    return datetime.now(timezone(timedelta(hours=8)))


def load_doc():
    """读 wb.json（按 mtime 缓存）。

    为什么要看 mtime：发布新数据（审核通过 / 全量抓取）会直接覆盖 wb.json，
    但进程里的缓存不会自己失效——旧实现在发布后仍然返回旧 doc，
    导致 /api/country、/api/country/detail 拿到的是改之前的数。
    """
    try:
        st = os.stat(WB)
    except OSError:
        return STATE["doc"]
    key = (st.st_mtime_ns, st.st_size)
    if STATE["doc"] is not None and STATE.get("doc_key") == key:
        return STATE["doc"]
    try:
        with open(WB, encoding="utf-8") as f:
            STATE["doc"] = json.load(f)
        STATE["doc_key"] = key
    except (OSError, json.JSONDecodeError):
        STATE["doc"] = None
        STATE["doc_key"] = None
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
    """邮件统一外壳：品牌头 + 正文 + CTA + 页脚退订。
       邮件客户端不支持 flex/grid，全部用 table + 内联样式，保证 QQ/Outlook/Gmail 一致。
       退订链接必须每封都带（符合 List-Unsubscribe 规范）。"""
    site = BASE_URL.rstrip("/")
    when_line = ("世界银行 WDI · 更新于 %s" % when) if when else "世界银行 WDI · 官方数据"
    return (
    "<table role=\"presentation\" cellpadding=\"0\" cellspacing=\"0\" border=\"0\" width=\"100%%\" "
    "style=\"background:#eef2f7;padding:28px 12px;font-family:-apple-system,BlinkMacSystemFont,"
    "'Segoe UI',Roboto,'PingFang SC','Microsoft YaHei',sans-serif\">"
    "<tr><td align=\"center\">"
    "<table role=\"presentation\" cellpadding=\"0\" cellspacing=\"0\" border=\"0\" width=\"600\" "
    "style=\"width:100%%;max-width:600px;background:#ffffff;border-radius:14px;overflow:hidden;"
    "box-shadow:0 6px 28px rgba(15,30,55,.09)\">"
    # 品牌头（深色）
    "<tr><td style=\"background:#0d1a2b;padding:18px 28px\">"
    "<table role=\"presentation\" cellpadding=\"0\" cellspacing=\"0\" border=\"0\" width=\"100%%\"><tr>"
    "<td style=\"color:#f0a868;font-size:17px;font-weight:700;letter-spacing:.22em\">ORBIS</td>"
    "<td align=\"right\" style=\"color:#8fa8c4;font-size:10px;letter-spacing:.16em\">DATA INTELLIGENCE</td>"
    "</tr></table></td></tr>"
    # 标题区
    "<tr><td style=\"padding:26px 28px 8px\">"
    "<div style=\"color:#f0a868;font-size:10px;font-weight:600;letter-spacing:.18em;margin-bottom:9px\">"
    "数据监测提醒</div>"
    "<div style=\"color:#152238;font-size:21px;font-weight:700;line-height:1.45;margin-bottom:7px\">%s</div>"
    "<div style=\"color:#8b98a8;font-size:12px\">%s</div>"
    "</td></tr>"
    # 正文
    "<tr><td style=\"padding:14px 28px 26px\">%s</td></tr>"
    # CTA
    "<tr><td style=\"padding:0 28px 28px\">"
    "<table role=\"presentation\" cellpadding=\"0\" cellspacing=\"0\" border=\"0\"><tr>"
    "<td style=\"background:#f0a868;border-radius:8px\">"
    "<a href=\"%s/\" style=\"display:inline-block;padding:12px 24px;color:#1a1206;font-size:13px;"
    "font-weight:700;text-decoration:none\">打开 ORBIS 查看完整数据 →</a>"
    "</td></tr></table></td></tr>"
    # 页脚
    "<tr><td style=\"background:#f7f9fc;border-top:1px solid #e7ecf2;padding:18px 28px\">"
    "<div style=\"color:#9aa6b5;font-size:11px;line-height:1.9\">"
    "数据来源：世界银行 World Development Indicators（WDI）· 边界仅作示意<br>"
    "你收到这封邮件，是因为在 ORBIS 订阅了这些国家的数据变化提醒。"
    "</div>"
    "<div style=\"color:#b2bcc8;font-size:11px;margin-top:10px\">"
    "<a href=\"%s\" style=\"color:#8b98a8;text-decoration:underline\">退订提醒</a>"
    "　·　<a href=\"%s/\" style=\"color:#8b98a8;text-decoration:underline\">访问网站</a>"
    "</div></td></tr>"
    "</table></td></tr></table>"
    % (title, when_line, body, site, unsub, site)
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
                    up = e["new"] > e["old"]
                    arrow = "↑" if up else "↓"
                    pct = ""
                    pct_html = ""
                    if e["ind"] != "le" and e["old"]:
                        pv = (e["new"] - e["old"]) / abs(e["old"]) * 100
                        pct = "（%+.1f%%）" % pv
                        # 涨=红、跌=绿（中国习惯），徽章用浅底深字
                        badge_bg = "#fdecea" if up else "#e8f5ee"
                        badge_fg = "#c0392b" if up else "#1e8449"
                        pct_html = ("<span style=\"display:inline-block;padding:3px 9px;border-radius:12px;"
                                    "background:%s;color:%s;font-size:12px;font-weight:700;margin-left:10px\">"
                                    "%s%.1f%%</span>" % (badge_bg, badge_fg, "+" if up else "", pv))
                    lines.append("%s %s %d 年：%s %s %s%s" % (
                        name_of(doc, iso), CN[e["ind"]], e["year"],
                        fmt(e["ind"], e["old"]), arrow, fmt(e["ind"], e["new"]), pct))
                    # 数据卡片：table 布局，兼容 QQ/Outlook
                    val_color = "#c0392b" if up else "#1e8449"
                    html_items.append(
                        "<table role=\"presentation\" cellpadding=\"0\" cellspacing=\"0\" border=\"0\" "
                        "width=\"100%%\" style=\"margin-bottom:10px;background:#f8fafc;border:1px solid #e7ecf2;"
                        "border-left:3px solid %s;border-radius:8px\">"
                        "<tr><td style=\"padding:14px 16px\">"
                        "<div style=\"color:#152238;font-size:14px;font-weight:700;margin-bottom:8px\">"
                        "%s <span style=\"color:#8b98a8;font-weight:400;font-size:12px\">· %s · %d 年</span></div>"
                        "<div style=\"white-space:nowrap\">"
                        "<span style=\"color:#8b98a8;font-size:13px\">%s</span>"
                        "<span style=\"color:#b2bcc8;margin:0 8px\">→</span>"
                        "<span style=\"color:%s;font-size:17px;font-weight:700\">%s</span>%s"
                        "</div></td></tr></table>"
                        % (val_color, name_of(doc, iso), CN[e["ind"]], e["year"],
                           fmt(e["ind"], e["old"]), val_color, fmt(e["ind"], e["new"]), pct_html)
                    )
                    con.execute("INSERT OR IGNORE INTO sent(k,at) VALUES(?,?)",
                                (key, now().isoformat(timespec="seconds")))
            if not fresh:
                continue
            names = "、".join(name_of(doc, i) for i in hit[:3])
            subject = "[ORBIS] %s 的数据出现变化" % names
            unsub = "%s/api/unsubscribe?token=%s" % (BASE_URL, token)
            text = ("你关注的 %d 个国家数据出现变化：\n\n" % len(hit) + "\n".join(lines) +
                    "\n\n—— ORBIS · 数据更新于 %s\n不想再收：%s"
                    % (doc.get("fetched_at", ""), unsub))
            headline = "你关注的 %d 个国家有新变化" % len(hit)
            if len(hit) == 1:
                headline = "%s 的数据有新变化" % name_of(doc, hit[0])
            html = mail_shell(headline,
                              "".join(html_items),
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
        STATE["doc_key"] = None     # 让下次 load_doc() 重新对 mtime
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
        try:
            refresh_fx()
        except Exception as e:  # noqa: BLE001
            print("[fx] scheduler error:", e)
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
    fx_doc = STATE["fx"] or load_fx()
    fx_status = None
    if fx_doc:
        fx_status = {
            "date": fx_doc.get("date"),
            "updated": fx_doc.get("updated"),
            "count": len(fx_doc.get("currencies") or {}),
        }
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
        "fx": fx_status,
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
        # CORS：回显来源以支持带凭据的跨域（本地 file:// 打开时也能登录）。
        # 只允许网站自身与 null(file://)，不开放给任意第三方站点。
        origin = self.headers.get("Origin", "")
        allow = origin if (origin in CORS_ORIGINS or origin == "null") else "null"
        self.send_header("Access-Control-Allow-Origin", allow)
        self.send_header("Access-Control-Allow-Credentials", "true")
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

    def _admin_token(self):
        return admin_auth.token_from_cookie(self.headers.get("Cookie"))

    def _admin_guard(self):
        """管理接口统一鉴权。未登录返回 False（调用方需直接 return）。"""
        if not admin_auth.valid(self._admin_token()):
            self._send(401, {"ok": False, "error": "管理员未登录"})
            return False
        return True

    def do_GET(self):
        u = urlparse(self.path)
        p = unquote(u.path)   # 中文路径在请求行里是 %XX 编码，解出来才能匹配
        q = parse_qs(u.query)
        # ---- 管理后台：静态页 + 需鉴权的 GET 接口 ----
        if p in ("/admin", "/admin/"):
            if not os.path.exists(ADMIN_PAGE):
                return self._send(404, "admin.html 不存在", "text/plain; charset=utf-8")
            body = open(ADMIN_PAGE, "rb").read()
            return self._send(200, body, "text/html; charset=utf-8",
                              {"Cache-Control": "no-store"})
        if p == "/api/admin/login":
            return self._send(200, {"ok": True, "authed": bool(admin_auth.valid(self._admin_token()))})
        if p.startswith("/api/admin/"):
            if not self._admin_guard():
                return
            ep = p[len("/api/admin/"):]
            one = lambda k, d="": (q.get(k, [d])[0] or d)
            if ep == "me":
                return self._send(200, {"ok": True, "admin": True})
            if ep == "overview":
                code, data = admin_api.overview(STATE, status_payload)
                return self._send(code, data)
            if ep == "users":
                code, data = admin_api.users(one("page", 1), one("size", 20), one("q"))
                return self._send(code, data)
            if ep == "subscriptions":
                code, data = admin_api.subscriptions(one("page", 1), one("size", 20), one("q"))
                return self._send(code, data)
            if ep == "data/status":
                code, data = admin_api.data_status(load_doc, load_fx)
                return self._send(code, data)
            if ep == "events":
                code, data = admin_api.events(one("limit", 50))
                return self._send(code, data)
            if ep == "mail/outbox":
                code, data = admin_api.outbox()
                return self._send(code, data)
            if ep == "mail/read":
                code, data = admin_api.outbox_read(one("name"), one("raw") == "1")
                ctype = "text/plain; charset=utf-8" if one("raw") == "1" and code == 200 else "application/json; charset=utf-8"
                return self._send(code, data, ctype)
            if ep == "settings":
                code, data = admin_api.settings()
                return self._send(code, data)
            # 待审数据通道
            if ep == "staging/list":
                code, data = admin_api.stage_list()
                return self._send(code, data)
            if ep.startswith("staging/get/"):
                code, data = admin_api.stage_get(unquote(ep[len("staging/get/"):]))
                return self._send(code, data)
            if ep.startswith("staging/preview/"):
                parts = ep[len("staging/preview/"):].split("/")
                if len(parts) != 2:
                    return self._send(400, {"ok": False, "error": "参数不完整"})
                code, data = admin_api.stage_preview(unquote(parts[0]), unquote(parts[1]), one("limit", 5))
                return self._send(code, data)
            if ep.startswith("staging/compare/"):
                parts = ep[len("staging/compare/"):].split("/")
                if len(parts) != 2:
                    return self._send(400, {"ok": False, "error": "参数不完整"})
                code, data = admin_api.stage_compare(unquote(parts[0]), unquote(parts[1]))
                return self._send(code, data)
            if ep.startswith("staging/countries/"):
                parts = ep[len("staging/countries/"):].split("/")
                if len(parts) != 2:
                    return self._send(400, {"ok": False, "error": "参数不完整"})
                code, data = admin_api.stage_countries(unquote(parts[0]), unquote(parts[1]))
                return self._send(code, data)
            # 爬虫状态
            if ep == "crawler/status":
                code, data = admin_api.crawler_status()
                return self._send(code, data)
            if ep == "trade/status":
                code, data = admin_api.trade_status()
                return self._send(code, data)
            return self._send(404, {"ok": False, "error": "unknown admin api"})
        if p.startswith("/assets/"):
            return self.serve_asset(p)
        if p in ("/", "/index.html", "/orbis.html", "/太空地球.html"):
            return self.serve_page()
        if p == "/api/auth/me":
            tok = auth.token_from_cookie(self.headers.get("Cookie"))
            u = auth.user_by_token(tok)
            return self._send(200, {"ok": True, "user": u})
        if p == "/api/status":
            return self._send(200, status_payload())
        if p == "/api/wb":
            doc = load_doc()
            return self._send(200, doc or {"ok": False})
        if p == "/api/predict":
            try:
                import predict as _predict
                iso = (q.get("iso", [""])[0] or "")
                ref = (q.get("ref", [""])[0] or "") or None
                return self._send(200, _predict.predict(iso, ref))
            except Exception as e:  # noqa: BLE001
                return self._send(500, {"ok": False, "error": "预测失败: %s" % e})
        if p == "/api/fx":
            fx = STATE["fx"] or load_fx()
            # 数据过时就后台刷新，本次先返回缓存（不阻塞响应）
            if fx:
                try:
                    last = datetime.fromisoformat(fx["updated"])
                    if last.tzinfo is None:
                        last = last.replace(tzinfo=timezone(timedelta(hours=8)))
                    if now() - last >= timedelta(hours=FX_HOURS):
                        threading.Thread(target=refresh_fx, daemon=True).start()
                except (KeyError, ValueError):
                    pass
            return self._send(200, fx or {"ok": False})
        if p == "/api/country":
            doc = load_doc() or {}
            iso = (q.get("iso", [""])[0] or "").upper()
            c = (doc.get("countries") or {}).get(iso)
            if not c:
                return self._send(404, {"ok": False, "error": "unknown iso"})
            return self._send(200, {"ok": True, "iso": iso, "years": doc.get("years"), "values": c})
        if p == "/api/country/detail":
            iso = (q.get("iso", [""])[0] or "").upper()
            doc = load_doc() or {}
            data = on_demand.detail(iso, doc)
            if data is None:
                return self._send(404, {"ok": False, "error": "unknown iso"})
            data["name"] = name_of(doc, iso)
            return self._send(200, {"ok": True, **data})
        if p == "/api/country/status":
            iso = (q.get("iso", [""])[0] or "").upper()
            usr = auth.user_by_token(auth.token_from_cookie(self.headers.get("Cookie")))
            return self._send(200, {"ok": True, **on_demand.status(iso, usr)})
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

        # ---- 管理后台 POST 接口（登录免鉴权，其余统一鉴权）----
        if u.path == "/api/admin/login":
            ip = self.client_address[0] if self.client_address else "unknown"
            ok, payload = admin_auth.login(body.get("username"), body.get("password"), ip)
            extra = None
            if ok:
                extra = {"Set-Cookie": admin_auth.cookie_header(payload["token"])}
            return self._send(200 if ok else 401, {"ok": ok, **payload}, extra=extra)
        if u.path.startswith("/api/admin/"):
            if not self._admin_guard():
                return
            ep = u.path[len("/api/admin/"):]
            if ep == "logout":
                admin_auth.logout(self._admin_token())
                return self._send(200, {"ok": True},
                                  extra={"Set-Cookie": admin_auth.cookie_header("", 0)})
            if ep == "data/refresh":
                code, data = admin_api.refresh(body.get("kind"), refresh, refresh_fx)
                return self._send(code, data)
            if ep == "subs/delete":
                code, data = admin_api.delete_subscription((body.get("email") or "").strip().lower())
                return self._send(code, data)
            if ep == "mail/test":
                code, data = admin_api.mail_test(body.get("to"), body.get("subject"),
                                                 body.get("text"), mailer.send)
                return self._send(code, data)
            if ep == "password":
                code, data = admin_api.change_password(body.get("old"), body.get("new"))
                return self._send(code, data)
            if ep == "username":
                ok, err = admin_auth.set_username(body.get("username"), body.get("password"))
                return self._send(200 if ok else 400, {"ok": ok, "error": err})
            # 待审数据通道
            if ep == "staging/fetch":
                code, data = admin_api.stage_fetch(body.get("kind"))
                return self._send(code, data)
            if ep == "staging/publish":
                code, data = admin_api.stage_publish(
                    body.get("id"), body.get("names"),
                    reload_doc=load_doc, reload_fx=load_fx, do_notify=notify)
                return self._send(code, data)
            if ep == "staging/reject":
                code, data = admin_api.stage_reject(body.get("id"))
                return self._send(code, data)
            # 爬虫：两种更新模式
            if ep == "crawler/config":
                code, data = admin_api.crawler_config(
                    body.get("day", 5), body.get("hour", 6),
                    body.get("minute", 0), body.get("enabled", True))
                return self._send(code, data)
            if ep == "crawler/run":
                code, data = admin_api.crawler_run(body.get("mode"))
                return self._send(code, data)
            if ep == "trade/run":
                code, data = admin_api.trade_run(body.get("mode"))
                return self._send(code, data)
            return self._send(404, {"ok": False, "error": "unknown admin api"})

        # 按需抓取：登录用户点国家触发
        if u.path == "/api/country/request":
            usr = auth.user_by_token(auth.token_from_cookie(self.headers.get("Cookie")))
            if not usr:
                return self._send(401, {"ok": False, "error": "登录后才能请求更新该国数据"})
            ok, payload = on_demand.request(body.get("iso3"), usr, body.get("metrics"))
            if ok:
                return self._send(200, {"ok": True, **payload})
            return self._send(400, {"ok": False, "error": payload})

        # ---- 真实账号系统 ----
        if u.path == "/api/auth/register":
            ok, payload = auth.register(body.get("email"), body.get("password"))
            if not ok:
                return self._send(400, {"ok": False, **payload})
            # 注册后直接登录，省一次输入
            ok2, login_payload = auth.login(body.get("email"), body.get("password"))
            if ok2:
                return self._send(200, {"ok": True, **login_payload},
                                  extra={"Set-Cookie": auth.cookie_header(login_payload["token"]).split(": ", 1)[1]})
            return self._send(200, {"ok": True, **payload})
        if u.path == "/api/auth/login":
            ok, payload = auth.login(body.get("email"), body.get("password"), body.get("remember", True))
            if not ok:
                return self._send(401, {"ok": False, **payload})
            return self._send(200, {"ok": True, **payload},
                              extra={"Set-Cookie": auth.cookie_header(
                                  payload["token"], None if body.get("remember", True) else 86400).split(": ", 1)[1]})
        if u.path == "/api/auth/logout":
            tok = auth.token_from_cookie(self.headers.get("Cookie"))
            auth.logout(tok)
            return self._send(200, {"ok": True}, extra={"Set-Cookie": auth.cookie_header("", 0).split(": ", 1)[1]})
        if u.path == "/api/auth/buy":
            tok = auth.token_from_cookie(self.headers.get("Cookie"))
            ok, payload = auth.buy_member(tok)
            return self._send(200 if ok else 400, {"ok": ok, **payload})

        if u.path == "/api/subscribe":
            email = (body.get("email") or "").strip().lower()
            codes = []
            for x in (body.get("codes") or []):
                c = str(x).strip().upper()
                if c and c not in codes:
                    codes.append(c)
            if "@" not in email or len(email) < 5 or "." not in email.split("@")[-1]:
                return self._send(400, {"ok": False, "error": "邮箱格式不对"})
            if len(codes) > 60:
                return self._send(400, {"ok": False, "error": "一次最多订阅 60 个国家"})
            if not codes:
                return self._send(400, {"ok": False, "error": "先选几个国家"})
            con = db()
            try:
                old = con.execute("SELECT token, codes FROM subs WHERE email=?", (email,)).fetchone()
                is_new = old is None
                if old:
                    merged = sorted((set((old[1] or "").split(",")) | set(codes)) - {""})
                    con.execute("UPDATE subs SET codes=? WHERE email=?", (",".join(merged), email))
                    token = old[0]
                else:
                    token = secrets.token_urlsafe(12)
                    con.execute(
                        "INSERT INTO subs(email,codes,token,created) VALUES(?,?,?,?)",
                        (email, ",".join(sorted(set(codes))), token, now().isoformat(timespec="seconds")),
                    )
                con.commit()
                final = con.execute("SELECT codes FROM subs WHERE email=?", (email,)).fetchone()[0]
                final_codes = sorted([c for c in (final or "").split(",") if c])
                n = len(final_codes)
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
                chips = "".join(
                    "<span style=\"display:inline-block;padding:6px 12px;margin:0 6px 6px 0;"
                    "background:#eef4fb;color:#2c5f96;border-radius:16px;font-size:12px;font-weight:600\">%s</span>"
                    % n for n in names)
                html = mail_shell(
                    head,
                    "<div style=\"color:#5d6b7d;font-size:13px;line-height:1.9;margin-bottom:14px\">"
                    "已为你建立数据监测。以下国家一旦有<b style=\"color:#152238\">新增年份</b>或"
                    "<b style=\"color:#152238\">大幅修订</b>，第一时间发信到这里。</div>"
                    "<div style=\"margin-bottom:6px\">%s</div>"
                    "<div style=\"margin-top:16px;padding:12px 14px;background:#f8fafc;border-radius:8px;"
                    "color:#8b98a8;font-size:12px;line-height:1.8\">"
                    "监测指标：GDP 总量 · 人均 GDP · 总人口 · 预期寿命<br>"
                    "数据来源：世界银行 WDI，服务端每 12 小时自动检查一次。</div>" % chips,
                    unsub, "")
                kind, _ = mailer.send(email, subject, text, html,
                                      {"List-Unsubscribe": "<%s>" % unsub})
                confirm = kind
            except Exception:  # noqa: BLE001
                traceback.print_exc()
            return self._send(200, {"ok": True, "email": email, "codes": final_codes, "watched": n,
                                    "is_new": is_new, "token": token,
                                    "mail": "smtp" if mailer.ready() else "outbox",
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
            fx_ok = refresh_fx(force=True)
            return self._send(200, {"ok": ok, "fx_ok": fx_ok, "status": status_payload()})

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

    ASSET_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
                   ".webp": "image/webp", ".svg": "image/svg+xml", ".gif": "image/gif",
                   ".html": "text/html; charset=utf-8",
                   ".css": "text/css; charset=utf-8", ".js": "application/javascript; charset=utf-8",
                   ".woff2": "font/woff2", ".ico": "image/x-icon", ".mp4": "video/mp4"}

    def serve_asset(self, p):
        """静态资源（国家文化照片等），只允许 /assets/ 下、禁止目录穿越。"""
        rel = p.lstrip("/")
        if not rel.startswith("assets/") or ".." in rel:
            return self._send(404, "not found", "text/plain; charset=utf-8")
        path = os.path.join(ROOT, rel)
        if not os.path.isfile(path):
            return self._send(404, "not found", "text/plain; charset=utf-8")
        ext = os.path.splitext(path)[1].lower()
        ctype = self.ASSET_TYPES.get(ext, "application/octet-stream")
        st = os.stat(path)
        etag = '"%x-%x"' % (st.st_mtime_ns, st.st_size)
        if (self.headers.get("If-None-Match") or "").strip() == etag:
            self.send_response(304)
            self.send_header("ETag", etag)
            self.send_header("Cache-Control", "public, max-age=604800")
            self.end_headers()
            return
        with open(path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("ETag", etag)
        self.send_header("Cache-Control", "public, max-age=604800")
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
        refresh_fx(force=True)
        return

    db().close()
    load_fx()
    if not a.no_fetch:
        threading.Thread(target=refresh, args=(True,), daemon=True).start()
        threading.Thread(target=refresh_fx, daemon=True).start()
    threading.Thread(target=scheduler, daemon=True).start()
    # 爬虫的「每月自动更新」常驻线程（模式一）
    threading.Thread(target=crawler.scheduler_loop, daemon=True).start()

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
