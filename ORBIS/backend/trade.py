#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""出口数据（各国出口额前三的 HS 商品章）。

数据来自 UN Comtrade，由外部取数工具生成后落到 data/trade.json；
没有这个文件时，逐国对比表里的「出口前三」显示为未接入，不影响其他指标。

文件格式：
{
  "generated_at": "...", "source": "UN Comtrade",
  "countries": {
    "CHN": {"year": 2025, "total_usd": 3.9e12,
            "top3": [{"hs":"85","zh":"电机、电气设备","usd":9199.9e8,"share":0.26}, ...]}
  }
}
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
TRADE = os.path.join(DATA, "trade.json")
_cache = {"mtime": None, "doc": None}


def load():
    """带 mtime 缓存的读取：文件没变就不重复解析。"""
    try:
        st = os.stat(TRADE)
    except OSError:
        return None
    if _cache["mtime"] == st.st_mtime and _cache["doc"] is not None:
        return _cache["doc"]
    try:
        with open(TRADE, encoding="utf-8") as f:
            doc = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    _cache["mtime"], _cache["doc"] = st.st_mtime, doc
    return doc


def coverage():
    doc = load()
    if not doc:
        return {"ready": False, "countries": 0, "generated_at": None}
    cs = doc.get("countries") or {}
    return {"ready": True, "countries": sum(1 for v in cs.values() if v.get("top3")),
            "generated_at": doc.get("generated_at")}
