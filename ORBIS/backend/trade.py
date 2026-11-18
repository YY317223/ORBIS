#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""出口 / 进口前三的贸易数据（UN Comtrade，HS 2 位章）。

文件：data/trade.json
{
  "generated_at": "...", "source": "UN Comtrade（…）",
  "countries": {
    "CHN": {"exports": {"year":2025, "total_usd":..., "top3":[...]},
            "imports": {"year":2025, "total_usd":..., "top3":[...]}}
  }
}

没有该文件、或某国缺某项时，界面显示「暂无数据」，不影响人口/GDP 等指标。
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
TRADE = os.path.join(DATA, "trade.json")
_cache = {"mtime": None, "doc": None}


def load():
    """带 mtime 缓存：文件没更新就不重复解析。"""
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


def _norm(rec):
    """兼容老格式（国家级 top3 直接挂载）：统一成 {exports, imports}。"""
    if not isinstance(rec, dict):
        return None
    if "exports" in rec or "imports" in rec:
        return rec
    if rec.get("top3"):
        return {"exports": {"year": rec.get("year"), "total_usd": rec.get("total_usd"),
                            "top3": rec["top3"]}, "imports": None}
    return None


def for_country(iso):
    doc = load() or {}
    return _norm((doc.get("countries") or {}).get(iso))


def coverage():
    doc = load()
    if not doc:
        return {"ready": False, "exports": 0, "imports": 0,
                "generated_at": None, "source": None}
    cs = doc.get("countries") or {}
    ex = sum(1 for v in cs.values() if (_norm(v) or {}).get("exports"))
    im = sum(1 for v in cs.values() if (_norm(v) or {}).get("imports"))
    return {"ready": True, "exports": ex, "imports": im,
            "countries": len(cs), "generated_at": doc.get("generated_at"),
            "source": doc.get("source")}
