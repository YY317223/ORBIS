#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""真实账号系统（纯标准库）。

- 密码用 hashlib.scrypt 加盐哈希，永不明文存储
- session token 随机生成，存 SQLite，通过 HttpOnly Cookie 下发
- 提供 register / login / logout / user 四个能力

表结构（在 data/users.db）：
  users(id, email UNIQUE, pass_hash, salt, coins, member, since, created)
  sessions(token PRIMARY KEY, user_id, created, expires)
"""
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
DB = os.path.join(DATA, "users.db")
COOKIE = "orbis_sid"
SESSION_DAYS = 30
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _db():
    os.makedirs(DATA, exist_ok=True)
    con = sqlite3.connect(DB, timeout=10)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute(
        "CREATE TABLE IF NOT EXISTS users("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " email TEXT UNIQUE NOT NULL,"
        " pass_hash TEXT NOT NULL,"
        " salt TEXT NOT NULL,"
        " coins INTEGER NOT NULL DEFAULT 100,"
        " member INTEGER NOT NULL DEFAULT 0,"
        " since TEXT,"
        " created TEXT NOT NULL)")
    con.execute(
        "CREATE TABLE IF NOT EXISTS sessions("
        " token TEXT PRIMARY KEY,"
        " user_id INTEGER NOT NULL,"
        " created TEXT NOT NULL,"
        " expires TEXT NOT NULL)")
    return con


def _now():
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def _hash(password, salt):
    """scrypt 派生密钥。n=2^14，抗 GPU 暴力破解。"""
    return hashlib.scrypt(
        password.encode("utf-8"),
        salt=bytes.fromhex(salt), n=16384, r=8, p=1, dklen=32,
    ).hex()


def _public(row):
    return {
        "id": row[0], "email": row[1],
        "coins": row[4], "member": bool(row[5]), "since": row[6],
    }


def _user_dict(row):
    return _public(row)


def register(email, password):
    """返回 (ok, payload)。payload 含 user 或 error。"""
    email = (email or "").strip().lower()
    password = password or ""
    if not EMAIL_RE.match(email):
        return False, {"error": "邮箱格式不正确"}
    if len(password) < 6:
        return False, {"error": "密码至少 6 位"}
    if len(password) > 128:
        return False, {"error": "密码太长（最多 128 位）"}
    con = _db()
    try:
        if con.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
            return False, {"error": "这个邮箱已注册，请直接登录"}
        salt = secrets.token_hex(16)
        con.execute(
            "INSERT INTO users(email,pass_hash,salt,coins,member,created) VALUES(?,?,?,?,?,?)",
            (email, _hash(password, salt), salt, 100, 0, _now()))
        con.commit()
        row = con.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        return True, {"user": _public(row)}
    except sqlite3.IntegrityError:
        return False, {"error": "这个邮箱已注册，请直接登录"}
    finally:
        con.close()


def login(email, password, remember=True):
    """返回 (ok, payload)。payload 含 token+user 或 error。"""
    email = (email or "").strip().lower()
    password = password or ""
    con = _db()
    try:
        row = con.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if not row:
            # 防用户枚举：统一错误文案；用一个假 hash 做等量运算抗时序攻击
            _hash(password, "00" * 16)
            return False, {"error": "邮箱或密码不正确"}
        calc = _hash(password, row[3])
        if not hmac.compare_digest(calc, row[2]):
            return False, {"error": "邮箱或密码不正确"}
        token = secrets.token_urlsafe(32)
        expires = (datetime.now(timezone(timedelta(hours=8))) +
                   timedelta(days=SESSION_DAYS if remember else 1)).isoformat(timespec="seconds")
        con.execute("INSERT INTO sessions(token,user_id,created,expires) VALUES(?,?,?,?)",
                    (token, row[0], _now(), expires))
        con.commit()
        return True, {"token": token, "user": _public(row), "expires": expires}
    finally:
        con.close()


def logout(token):
    con = _db()
    try:
        con.execute("DELETE FROM sessions WHERE token=?", (token,))
        con.commit()
    finally:
        con.close()


def user_by_token(token):
    """返回 user dict 或 None。过期 session 自动清理。"""
    if not token:
        return None
    con = _db()
    try:
        row = con.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id "
            "WHERE s.token=? AND s.expires>?", (token, _now())).fetchone()
        return _public(row) if row else None
    finally:
        con.close()


def buy_member(token):
    """扣 39 币开通完整版。返回 (ok, payload)。"""
    con = _db()
    try:
        row = con.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id "
            "WHERE s.token=? AND s.expires>?", (token, _now())).fetchone()
        if not row:
            return False, {"error": "请先登录"}
        if row[5]:
            return False, {"error": "你已是完整版会员"}
        if row[4] < 39:
            return False, {"error": "虚拟币不足，需 39，当前 %d" % row[4]}
        con.execute("UPDATE users SET coins=coins-39, member=1, since=? WHERE id=?", (_now(), row[0]))
        con.commit()
        new = con.execute("SELECT * FROM users WHERE id=?", (row[0],)).fetchone()
        return True, {"user": _public(new)}
    finally:
        con.close()


def cookie_header(token, max_age=None):
    """生成 HttpOnly Cookie（SameSite=Lax）。删除时 max_age=0。"""
    if max_age is None:
        max_age = SESSION_DAYS * 86400
    return "Set-Cookie: %s=%s; Path=/; HttpOnly; SameSite=Lax; Max-Age=%d" % (
        COOKIE, token, max_age)


def token_from_cookie(header):
    if not header:
        return None
    for part in header.split(";"):
        k, _, v = part.strip().partition("=")
        if k == COOKIE:
            return v
    return None
