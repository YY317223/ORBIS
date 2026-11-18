#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把世行数据（backend/data/wb.json）合并进前端数据文件 data.js，并重建 orbis.html。

这是「数据真正上到用户界面」的那一步：只有这里会改项目里的 data.js / orbis.html。
调用方：
  - 爬虫的自动模式（每月，无需审核）
  - 审核发布（管理员点「通过」之后）

设计原则：
  - 只覆盖数值序列（gdp / pc / pop / le / age / urb / world），几何、城市、国旗等一概不动；
  - 写之前自动备份 data.js 到 data/backups/；
  - 幂等：同一份 wb.json 重复跑结果一致。
"""
import json
import os
import shutil
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(HERE, "data")
WB = os.path.join(DATA, "wb.json")
DATA_JS = os.path.join(ROOT, "data.js")
ORBIS_HTML = os.path.join(ROOT, "orbis.html")
BACKUPS = os.path.join(DATA, "backups")

SERIES = ("gdp", "pc", "pop", "le")


def _now():
    return datetime.now(timezone(timedelta(hours=8)))


def _load_datajs():
    with open(DATA_JS, encoding="utf-8") as f:
        raw = f.read()
    if "=" not in raw:
        raise RuntimeError("data.js 格式不认识（缺少 = 赋值）")
    payload = raw.split("=", 1)[1].strip().rstrip(";")
    return json.loads(payload)


def _dump_datajs(doc):
    body = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    tmp = DATA_JS + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("window.ATLAS_DATA = " + body + ";\n")
    os.replace(tmp, DATA_JS)


def _align(src, years_index, n):
    """把 wb 的 {year: value} 序列对齐到前端年份轴。"""
    out = [None] * n
    for y, v in src.items():
        i = years_index.get(y)
        if i is not None and v is not None:
            out[i] = v
    return out


def version_label(now=None):
    """数据版本号：取「上一个完整月份」，例如 2026-11-17 抓取 -> 2026-10。"""
    now = now or _now()
    first = now.replace(day=1)
    prev = first - timedelta(days=1)
    return prev.strftime("%Y-%m")


def apply(backup=True):
    """把 wb.json 合并进 data.js。返回统计信息。"""
    if not os.path.exists(WB):
        raise RuntimeError("缺少 backend/data/wb.json，先抓取世行数据")
    with open(WB, encoding="utf-8") as f:
        wb = json.load(f)

    years = list(wb.get("years") or [])
    if not years:
        raise RuntimeError("wb.json 没有年份轴")
    idx = {y: i for i, y in enumerate(years)}
    n = len(years)

    doc = _load_datajs()
    meta = doc.setdefault("meta", {})
    old_years = meta.get("years") or []

    # 1) 国家序列
    iso_map = {c.get("iso3"): c for c in doc.get("countries") or [] if c.get("iso3")}
    wb_c = wb.get("countries") or {}
    touched = 0
    filled = {k: 0 for k in SERIES}
    for iso, src in wb_c.items():
        c = iso_map.get(iso)
        if not c:
            continue
        touched += 1
        for k in SERIES:
            series = src.get(k)
            arr = _align({y: v for y, v in zip(years, series or [])}, idx, n)
            c[k] = arr
            filled[k] += sum(1 for v in arr if v is not None)
        # 年龄结构：a0（0-14 岁占比）、a65（65+ 占比），第三项是 15-64
        a0 = src.get("a0")
        a65 = src.get("a65")
        a0v = a0[idx[years[-1]]] if a0 and len(a0) == n else None
        a65v = a65[idx[years[-1]]] if a65 and len(a65) == n else None
        if a0v is None or a65v is None:
            a0v, a65v = _latest_pair(a0, a65, years)
        if a0v is not None and a65v is not None:
            c["age"] = [round(a0v, 2), round(a65v, 2), round(100 - a0v - a65v, 2)]
            c["a0y"] = _latest_year(a0, a65, years)
        urb = src.get("urb")
        if urb:
            uv, uy = _latest_val(urb, years)
            if uv is not None:
                c["urb"] = round(uv, 2)

    # 2) 世界合计
    wld = wb_c.get("WLD") or {}
    world = doc.setdefault("world", {})
    for k in ("gdp", "pc", "pop", "le", "a0", "a65", "urb"):
        series = wld.get(k)
        if series:
            world[k] = _align({y: v for y, v in zip(years, series)}, idx, n)

    # 3) 年份轴与版本
    meta["years"] = years
    meta["updated"] = version_label()
    meta["fetched_at"] = wb.get("fetched_at")
    meta["source_updated"] = wb.get("source_updated")
    meta["data_note"] = ("数值来自世界银行 WDI，未做估算或插值；"
                         "版本号为最近一个完整月份，抓取时间为 fetched_at。")

    if backup and os.path.exists(DATA_JS):
        os.makedirs(BACKUPS, exist_ok=True)
        stamp = _now().strftime("%Y%m%d_%H%M%S")
        bak = os.path.join(BACKUPS, "data.js.%s" % stamp)
        shutil.copyfile(DATA_JS, bak)

    _dump_datajs(doc)
    return {
        "countries": touched,
        "years": [years[0], years[-1]] if years else [],
        "old_years": [old_years[0], old_years[-1]] if old_years else [],
        "version": meta["updated"],
        "filled": filled,
        "datajs_bytes": os.path.getsize(DATA_JS),
    }


def _latest_val(series, years):
    for i in range(len(years) - 1, -1, -1):
        if i < len(series) and series[i] is not None:
            return series[i], years[i]
    return None, None


def _latest_pair(s1, s2, years):
    for i in range(len(years) - 1, -1, -1):
        a = s1[i] if s1 and i < len(s1) else None
        b = s2[i] if s2 and i < len(s2) else None
        if a is not None and b is not None:
            return a, b
    return None, None


def _latest_year(s1, s2, years):
    _, y = _latest_pair(s1, s2, years)
    return y


def rebuild_page(timeout=300):
    """把新的 data.js 写回 orbis.html，保留页面自身（含登录封面）不动。

    为什么不重新跑 frontend/build_globe.py：
      仓库里的 orbis.html 已经打过「编辑部式登录封面」补丁（login-src/patch_gate.py），
      而 frontend/globe_template.html 还是改版前的旧封面。用模板重建会把新封面
      覆盖回旧的科技风线框地球。所以这里只做数据段的替换。
    """
    if not os.path.exists(ORBIS_HTML):
        raise RuntimeError("找不到 orbis.html，无法写入数据")
    with open(ORBIS_HTML, encoding="utf-8") as f:
        html = f.read()
    with open(DATA_JS, encoding="utf-8") as f:
        data = f.read().strip()

    marker = "window.ATLAS_DATA"
    i = html.find(marker)
    if i < 0:
        raise RuntimeError("orbis.html 里找不到 window.ATLAS_DATA 数据段")
    j = html.find("</script>", i)
    if j < 0:
        raise RuntimeError("orbis.html 数据段没有闭合的 </script>")
    if not data.endswith(";"):
        data += ";"

    out = html[:i] + data + "\n" + html[j:]
    tmp = ORBIS_HTML + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(out)
    os.replace(tmp, ORBIS_HTML)
    return {"mode": "inject", "bytes": os.path.getsize(ORBIS_HTML),
            "data_bytes": len(data.encode("utf-8"))}


def apply_and_rebuild(backup=True):
    st = apply(backup=backup)
    st.update(rebuild_page())
    return st


if __name__ == "__main__":
    print(json.dumps(apply_and_rebuild(), ensure_ascii=False, indent=2))
