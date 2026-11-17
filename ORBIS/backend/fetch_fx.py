#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 Frankfurter API 抓央行参考汇率，落 data/fx.json。

数据源：Frankfurter (https://frankfurter.dev) — 聚合 111 家央行/官方机构，
含欧洲央行 ECB 参考汇率。免费、无需 key、开源。这是央行参考价（每日发布），
不是分时市场报价。纯标准库实现。

输出结构：
{
  "date": "2026-11-16",          # 最新牌价日期
  "base": "USD",
  "updated": ISO时间,
  "source": "Frankfurter (111 central banks, incl. ECB)",
  "currencies": {
     "CNY": { "rate": 6.6656,    # 1 USD = 6.6656 CNY
              "d7": -0.34,        # 7 天前至今，本币相对美元升跌幅(%)
              "d30": -0.27,       # 30 天
              "symbol": "¥", "name": "Chinese Yuan" },
     ...
  }
}
注意 d7/d30 用"本币升跌幅"口径：数值为负 = 本币相对美元升值(更值钱)。
"""
import json
import os
import ssl
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OUT = os.path.join(DATA, "fx.json")
API = "https://api.frankfurter.dev/v2"
UA = "ORBIS/1.0 (exchange-rate monitor)"

# ISO3 -> ISO4217 货币代码（源自 mledoze/countries，仅保留 Frankfurter 支持的法币）
ISO3_CCY = {
    "ABW":"AWG", "AFG":"AFN", "AGO":"AOA", "AIA":"XCD", "ALA":"EUR", "ALB":"ALL",
    "AND":"EUR", "ARE":"AED", "ARG":"ARS", "ARM":"AMD", "ASM":"USD", "ATF":"EUR",
    "ATG":"XCD", "AUS":"AUD", "AUT":"EUR", "AZE":"AZN", "BDI":"BIF", "BEL":"EUR",
    "BEN":"XOF", "BFA":"XOF", "BGD":"BDT", "BGR":"EUR", "BHR":"BHD", "BHS":"BSD",
    "BIH":"BAM", "BLR":"BYN", "BLZ":"BZD", "BMU":"BMD", "BOL":"BOB", "BRA":"BRL",
    "BRB":"BBD", "BRN":"BND", "BTN":"BTN", "BWA":"BWP", "CAF":"XAF", "CAN":"CAD",
    "CHE":"CHF", "CHL":"CLP", "CHN":"CNY", "CIV":"XOF", "CMR":"XAF", "COD":"CDF",
    "COG":"XAF", "COL":"COP", "COM":"KMF", "CPV":"CVE", "CRI":"CRC", "CUB":"CUP",
    "CUW":"XCG", "CYM":"KYD", "CYP":"EUR", "CZE":"CZK", "DEU":"EUR", "DJI":"DJF",
    "DMA":"XCD", "DNK":"DKK", "DOM":"DOP", "DZA":"DZD", "ECU":"USD", "EGY":"EGP",
    "ERI":"ERN", "ESH":"DZD", "ESP":"EUR", "EST":"EUR", "ETH":"ETB", "FIN":"EUR",
    "FJI":"FJD", "FLK":"FKP", "FRA":"EUR", "FRO":"DKK", "GAB":"XAF", "GBR":"GBP",
    "GEO":"GEL", "GGY":"GBP", "GHA":"GHS", "GIN":"GNF", "GMB":"GMD", "GNB":"XOF",
    "GNQ":"XAF", "GRC":"EUR", "GRD":"XCD", "GRL":"DKK", "GTM":"GTQ", "GUM":"USD",
    "GUY":"GYD", "HND":"HNL", "HRV":"EUR", "HTI":"HTG", "HUN":"HUF", "IDN":"IDR",
    "IMN":"GBP", "IND":"INR", "IOT":"USD", "IRL":"EUR", "IRN":"IRR", "IRQ":"IQD",
    "ISL":"ISK", "ISR":"ILS", "ITA":"EUR", "JAM":"JMD", "JEY":"GBP", "JOR":"JOD",
    "JPN":"JPY", "KAZ":"KZT", "KEN":"KES", "KGZ":"KGS", "KHM":"KHR", "KIR":"AUD",
    "KNA":"XCD", "KOR":"KRW", "KWT":"KWD", "LAO":"LAK", "LBN":"LBP", "LBR":"LRD",
    "LBY":"LYD", "LCA":"XCD", "LIE":"CHF", "LKA":"LKR", "LSO":"LSL", "LTU":"EUR",
    "LUX":"EUR", "LVA":"EUR", "MAF":"EUR", "MAR":"MAD", "MDA":"MDL", "MDG":"MGA",
    "MDV":"MVR", "MEX":"MXN", "MHL":"USD", "MKD":"MKD", "MLI":"XOF", "MLT":"EUR",
    "MMR":"MMK", "MNE":"EUR", "MNG":"MNT", "MNP":"USD", "MOZ":"MZN", "MRT":"MRU",
    "MSR":"XCD", "MUS":"MUR", "MWI":"MWK", "MYS":"MYR", "NAM":"NAD", "NCL":"XPF",
    "NER":"XOF", "NFK":"AUD", "NGA":"NGN", "NIC":"NIO", "NIU":"NZD", "NLD":"EUR",
    "NOR":"NOK", "NPL":"NPR", "NZL":"NZD", "OMN":"OMR", "PAK":"PKR", "PAN":"PAB",
    "PCN":"NZD", "PER":"PEN", "PHL":"PHP", "PLW":"USD", "PNG":"PGK", "POL":"PLN",
    "PRI":"USD", "PRK":"KPW", "PRT":"EUR", "PRY":"PYG", "PSE":"EGP", "PYF":"XPF",
    "QAT":"QAR", "ROU":"RON", "RUS":"RUB", "RWA":"RWF", "SAU":"SAR", "SDN":"SDG",
    "SEN":"XOF", "SGP":"SGD", "SGS":"SHP", "SHN":"GBP", "SLB":"SBD", "SLE":"SLE",
    "SLV":"USD", "SMR":"EUR", "SOM":"SOS", "SPM":"EUR", "SRB":"RSD", "SSD":"SSP",
    "STP":"STN", "SUR":"SRD", "SVK":"EUR", "SVN":"EUR", "SWE":"SEK", "SWZ":"SZL",
    "SXM":"XCG", "SYC":"SCR", "SYR":"SYP", "TCA":"USD", "TCD":"XAF", "TGO":"XOF",
    "THA":"THB", "TJK":"TJS", "TKM":"TMT", "TLS":"USD", "TON":"TOP", "TTO":"TTD",
    "TUN":"TND", "TUR":"TRY", "TUV":"AUD", "TZA":"TZS", "UGA":"UGX", "UKR":"UAH",
    "URY":"UYU", "USA":"USD", "UZB":"UZS", "VCT":"XCD", "VEN":"VES", "VGB":"USD",
    "VIR":"USD", "VNM":"VND", "VUT":"VUV", "WLF":"XPF", "WSM":"WST", "YEM":"YER",
    "ZAF":"ZAR", "ZMB":"ZMW", "ZWE":"BWP"
}

# 多货币映射时取唯一币种，减少请求批次
QUOTES = sorted(set(ISO3_CCY.values()))
CCY_NAME = {}   # 运行时从 /v2/currencies 补全


def _get(url, tries=3):
    ctx = ssl.create_default_context()
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=45, context=ctx) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as e:
            last = e
            time.sleep(1.5 * (i + 1))
    raise RuntimeError("fx fetch failed: %s" % last)


def _chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def run(verbose=False):
    """抓最新汇率 + 近 31 天历史，算 7/30 天涨跌，落盘。返回 fx 文档。"""
    global CCY_NAME
    # 货币元数据（名称/符号）
    try:
        for c in _get(API + "/currencies"):
            if c.get("type") == "currency":
                CCY_NAME[c["iso_code"]] = {"name": c.get("name"), "symbol": c.get("symbol")}
    except Exception:
        CCY_NAME = {}

    today = datetime.now(timezone(timedelta(hours=8))).date()
    d30 = today - timedelta(days=32)
    rows = []
    # 分批请求，每批 ~30 个币种，避免 URL 过长
    for batch in _chunks(QUOTES, 30):
        q = ",".join(batch)
        url = "%s/rates?base=USD&quotes=%s&from=%s&to=%s" % (
            API, q, d30.isoformat(), today.isoformat())
        try:
            rows.extend(_get(url))
        except Exception as e:
            if verbose:
                print("[fx] batch failed:", e)
    if not rows:
        raise RuntimeError("no fx data fetched")

    latest = {}
    hist = {}
    for r in rows:
        q, dt, v = r.get("quote"), r.get("date"), r.get("rate")
        if not q or v is None:
            continue
        if q not in latest or dt > latest[q]["date"]:
            latest[q] = {"date": dt, "rate": v}
        hist.setdefault(q, []).append((dt, v))

    def rate_ago(q, days):
        """取距离今天 days 天之前最近的一条历史价。"""
        arr = sorted(hist.get(q, []))
        if not arr:
            return None
        target = (today - timedelta(days=days)).isoformat()
        pick = None
        for dt, v in arr:
            if dt <= target:
                pick = v
            else:
                break
        return pick

    out = {
        "date": max((x["date"] for x in latest.values()), default=today.isoformat()),
        "base": "USD",
        "updated": datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
        "source": "Frankfurter (111 central banks, incl. ECB reference rates)",
        "unit": "1 USD = X 本币",
        "currencies": {},
    }
    for q, info in latest.items():
        meta = CCY_NAME.get(q, {})
        rate = info["rate"]

        def pct(days):
            old = rate_ago(q, days)
            if not old:
                return None
            # 本币升跌幅 = (old rate / new rate - 1) * 100
            # 1 USD 能换的本币变少(rate下降) = 本币升值 = 正值
            return round((old / rate - 1) * 100, 2)

        out["currencies"][q] = {
            "rate": rate,
            "d7": pct(7),
            "d30": pct(30),
            "symbol": meta.get("symbol") or q,
            "name": meta.get("name") or q,
            "date": info["date"],
        }

    os.makedirs(DATA, exist_ok=True)
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, OUT)
    if verbose:
        print("[fx] saved %d currencies, date=%s" % (len(out["currencies"]), out["date"]))
    return out


if __name__ == "__main__":
    run(verbose=True)
