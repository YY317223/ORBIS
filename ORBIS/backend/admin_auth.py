#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""管理员认证（与用户账号体系完全隔离）。

- 独立密码：环境变量 ADMIN_PASSWORD 优先；否则 data/admin.json 存 scrypt 哈希；
  两者都没有时用默认密码并自动生成哈希（后台设置页可改）。
- 独立会话：data/admin.db 的 admin_sessions 表，Cookie 名 orbis_admin。
  普通用户的 orbis_sid 无法提权。
- 登录限流：同一 IP 连续 5 次失败锁 15 分钟。
纯标准库实现。
"""
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
DB = os.path.join(DATA, "admin.db")
CFG = os.path.join(DATA, "admin.json")
COOKIE = "orbis_admin"
SESSION_HOURS = 12
DEFAULT_USER = "admin"          # 默认管理员账号
DEFAULT_PASSWORD = "orbis2026"
MAX_FAILS = 5
LOCK_MIN = 15
_fails = {}          # ip -> [fail_count, lock_until_ts]


def _now():
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def _db():
    os.makedirs(DATA, exist_ok=True)
    con = sqlite3.connect(DB, timeout=10)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute(
        "CREATE TABLE IF NOT EXISTS admin_sessions("
        " token TEXT PRIMARY KEY, created TEXT NOT NULL, expires TEXT NOT NULL)")
    return con


def _hash(password, salt):
    return hashlib.scrypt(password.encode("utf-8"), salt=bytes.fromhex(salt),
                          n=16384, r=8, p=1, dklen=32).hex()


def _credential():
    """返回 (salt, hash, source)。source: env / file / default。"""
    env = os.environ.get("ADMIN_PASSWORD")
    if env:
        salt = "00" * 16
        return salt, _hash(env, salt), "env"
    try:
        if os.path.exists(CFG):
            c = json.load(open(CFG, encoding="utf-8"))
            if c.get("salt") and c.get("password_hash"):
                # 仍是默认密码时用 default 标记，让后台能提示用户修改
                src = "default" if c.get("is_default") else "file"
                return c["salt"], c["password_hash"], src
    except (OSError, json.JSONDecodeError):
        pass
    # 首次：用默认密码，落哈希到 admin.json
    salt = secrets.token_hex(16)
    os.makedirs(DATA, exist_ok=True)
    with open(CFG, "w", encoding="utf-8") as f:
        json.dump({"salt": salt, "password_hash": _hash(DEFAULT_PASSWORD, salt),
                   "is_default": True,
                   "note": "管理员密码哈希。请用后台设置页修改，或设置环境变量 ADMIN_PASSWORD。"},
                  f, ensure_ascii=False, indent=2)
    return salt, _hash(DEFAULT_PASSWORD, salt), "default"


def _password_ok(password):
    salt, h, _ = _credential()
    return hmac.compare_digest(_hash(password or "", salt), h)


def username():
    """当前管理员账号。优先环境变量 ADMIN_USER，其次 admin.json，最后默认 admin。"""
    env = os.environ.get("ADMIN_USER")
    if env:
        return env
    try:
        if os.path.exists(CFG):
            c = json.load(open(CFG, encoding="utf-8"))
            if c.get("username"):
                return c["username"]
    except (OSError, json.JSONDecodeError):
        pass
    return DEFAULT_USER


def set_username(new_user, password):
    """改管理员账号，需验证当前密码。返回 (ok, error)。"""
    import re
    new_user = (new_user or "").strip().lower()
    if not re.match(r"^[a-z0-9_]{3,24}$", new_user):
        return False, "账号需 3–24 位小写字母/数字/下划线"
    if os.environ.get("ADMIN_USER"):
        return False, "账号由环境变量 ADMIN_USER 管理，请改环境变量后重启"
    if not _password_ok(password):
        return False, "密码不正确，不能修改账号"
    c = {}
    try:
        if os.path.exists(CFG):
            c = json.load(open(CFG, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    c["username"] = new_user
    os.makedirs(DATA, exist_ok=True)
    with open(CFG, "w", encoding="utf-8") as f:
        json.dump(c, f, ensure_ascii=False, indent=2)
    return True, None


def is_default_password():
    return _credential()[2] == "default"


def set_password(new_password, old_password=None):
    """修改管理员密码。需提供旧密码（除非当前是默认密码）。返回 (ok, error)。"""
    if not new_password or len(new_password) < 8:
        return False, "新密码至少 8 位"
    if _credential()[2] != "default":
        if not old_password or not _password_ok(old_password):
            return False, "旧密码不正确"
    elif old_password and not _password_ok(old_password):
        return False, "旧密码不正确"
    if os.environ.get("ADMIN_PASSWORD"):
        return False, "当前密码由环境变量 ADMIN_PASSWORD 管理，请改环境变量后重启服务"
    salt = secrets.token_hex(16)
    os.makedirs(DATA, exist_ok=True)
    with open(CFG, "w", encoding="utf-8") as f:
        json.dump({"salt": salt, "password_hash": _hash(new_password, salt),
                   "is_default": False,
                   "note": "管理员密码哈希。请用后台设置页修改，或设置环境变量 ADMIN_PASSWORD。"},
                  f, ensure_ascii=False, indent=2)
    return True, None


def locked(ip):
    cnt, until = _fails.get(ip, [0, 0])
    return cnt >= MAX_FAILS and time.time() < until


def login(user, password, ip="unknown"):
    """账号 + 密码双因子校验。返回 (ok, payload)。"""
    if locked(ip):
        left = int((_fails[ip][1] - time.time()) / 60) + 1
        return False, {"error": "尝试次数过多，请 %d 分钟后再试" % left}
    # 即便账号错也做一次哈希，抗时序攻击
    ok = _password_ok(password)
    if (user or "").strip().lower() != username():
        ok = False
    if not ok:
        cnt, until = _fails.get(ip, [0, 0])
        if time.time() > until:
            cnt, until = 0, 0
        cnt += 1
        _fails[ip] = [cnt, time.time() + LOCK_MIN * 60 if cnt >= MAX_FAILS else 0]
        left = MAX_FAILS - cnt
        return False, {"error": "密码不正确" + ("，还可尝试 %d 次" % left if left > 0 else "，账号已锁定")}
    _fails.pop(ip, None)
    token = secrets.token_urlsafe(32)
    expires = (datetime.now(timezone(timedelta(hours=8))) +
               timedelta(hours=SESSION_HOURS)).isoformat(timespec="seconds")
    con = _db()
    try:
        con.execute("INSERT INTO admin_sessions(token,created,expires) VALUES(?,?,?)",
                    (token, _now(), expires))
        con.commit()
    finally:
        con.close()
    return True, {"token": token, "expires": expires, "default_password": is_default_password()}


def valid(token):
    if not token:
        return False
    con = _db()
    try:
        row = con.execute("SELECT 1 FROM admin_sessions WHERE token=? AND expires>?",
                          (token, _now())).fetchone()
        return bool(row)
    finally:
        con.close()


def logout(token):
    con = _db()
    try:
        con.execute("DELETE FROM admin_sessions WHERE token=?", (token,))
        con.commit()
    finally:
        con.close()


def cookie_header(token, max_age=None):
    if max_age is None:
        max_age = SESSION_HOURS * 3600
    return "%s=%s; Path=/; HttpOnly; SameSite=Strict; Max-Age=%d" % (COOKIE, token, max_age)


def token_from_cookie(header):
    if not header:
        return None
    for part in header.split(";"):
        k, _, v = part.strip().partition("=")
        if k == COOKIE:
            return v
    return None
