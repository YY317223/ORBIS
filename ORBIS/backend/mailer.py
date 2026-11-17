#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""邮件发送：有 SMTP 配置就发，没有就写 .eml 到 data/outbox（可导入邮件客户端）。

config.json 示例（与 app.py 同目录）：
{
  "smtp": {"host": "smtp.qq.com", "port": 465, "ssl": true,
           "user": "you@qq.com", "password": "授权码", "from": "ORBIS <you@qq.com>"}
}
"""
import json
import os
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr, formatdate

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OUTBOX = os.path.join(DATA, "outbox")
CONFIG = os.path.join(HERE, "config.json")


def config():
    if not os.path.exists(CONFIG):
        return {}
    try:
        with open(CONFIG, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def ready():
    return bool((config().get("smtp") or {}).get("host"))


def build(to, subject, text, html=None, headers=None):
    m = EmailMessage()
    m["Subject"] = subject
    m["From"] = config().get("smtp", {}).get("from") or "space-earth@localhost"
    m["To"] = to
    m["Date"] = formatdate(localtime=True)
    for k, v in (headers or {}).items():
        m[k] = v
    m.set_content(text)
    if html:
        m.add_alternative(html, subtype="html")
    return m


def send(to, subject, text, html=None, headers=None):
    """返回 ('smtp'|'outbox'|'error', detail)"""
    msg = build(to, subject, text, html, headers)
    c = (config().get("smtp") or {})
    if not c.get("host"):
        os.makedirs(OUTBOX, exist_ok=True)
        name = "%s_%s.eml" % (datetime.now().strftime("%Y%m%d-%H%M%S"), abs(hash(to)) % 100000)
        path = os.path.join(OUTBOX, name)
        with open(path, "wb") as f:
            f.write(bytes(msg))
        print("[mail] SMTP 未配置，已写入 %s" % path)
        return "outbox", path
    try:
        host, port = c["host"], int(c.get("port", 465))
        ctx = ssl.create_default_context()
        if c.get("ssl", True):
            with smtplib.SMTP_SSL(host, port, timeout=30, context=ctx) as s:
                s.login(c["user"], c["password"])
                s.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=30) as s:
                s.starttls(context=ctx)
                s.login(c["user"], c["password"])
                s.send_message(msg)
        print("[mail] 已发送 -> %s" % to)
        return "smtp", to
    except Exception as e:  # noqa: BLE001
        print("[mail] 发送失败 %s: %s" % (to, e))
        return "error", str(e)
