#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""基于 wb.json 的中长期趋势预测（纯标准库，现场计算）。

设计原则：
  1. 只用年度序列做中长期外推，不预测具体某月数值。
  2. 给区间而非单点，标注可信度与依据。
  3. 第二档（异常/风险）设明确约束，标"参考性判断"，不当结论。

第一档：人口峰值 / 老龄化拐点 / 人均GDP收敛 / 城镇化与产业
第二档：异常预警(2σ) / 中等收入陷阱风险评分
"""
import json
import math
import os
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
WB = os.path.join(HERE, "data", "wb.json")

MIN_POINTS = 12          # 至少 12 个有效年度点才预测
HORIZON = 15             # 最长外推 15 年（2025 -> 2040）


def _load():
    with open(WB, encoding="utf-8") as f:
        return json.load(f)


def _series(doc, iso, key):
    """返回 [(year, value), ...]，跳过缺测。iso 可为聚合体(如 WLD)。"""
    c = doc["countries"].get(iso)
    if not c or key not in c:
        return []
    out = []
    for y, v in zip(doc["years"], c[key]):
        if v is not None and isinstance(v, (int, float)):
            out.append((y, float(v)))
    return out


def _linfit(xs, ys):
    """最小二乘 y = a*x + b，返回 (a, b)。"""
    n = len(xs)
    if n < 2:
        return 0.0, (ys[0] if ys else 0.0)
    mx, my = sum(xs) / n, sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        return 0.0, my
    a = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den
    return a, my - a * mx


def _tail(series, n=10):
    return series[-n:] if len(series) >= n else series


def _cagr(series, years=10):
    """近 N 年复合增长率。"""
    s = _tail(series, years + 1)
    if len(s) < 2:
        return None
    (y0, v0), (y1, v1) = s[0], s[-1]
    if v0 <= 0 or v1 <= 0 or y1 <= y0:
        return None
    return (v1 / v0) ** (1.0 / (y1 - y0)) - 1.0


def _fmt_year(y):
    return int(y) if y is not None and math.isfinite(y) else None


def _ci(years, spread):
    """返回区间 [早, 晚]。"""
    if years is None or not math.isfinite(years):
        return None
    return [_fmt_year(years - spread), _fmt_year(years + spread)]


def predict_population_peak(doc, iso):
    """人口峰值：近 12 年人口年增量的线性趋势外推到归零。"""
    s = _series(doc, iso, "pop")
    if len(s) < MIN_POINTS:
        return {"ok": False, "reason": "人口数据不足"}
    t = _tail(s, 12)
    diffs = [(t[i][0], t[i][1] - t[i - 1][1]) for i in range(1, len(t))]
    xs = [x for x, _ in diffs]
    ys = [y for _, y in diffs]
    a, b = _linfit(xs, ys)
    last_year = s[-1][0]
    if a >= 0:
        # 仍在加速或平稳：近 12 年平均增量 + 趋势，外推峰值很远
        avg = sum(ys) / len(ys)
        if avg <= 0:
            return {"ok": True, "status": "declining", "peak_year": _fmt_year(last_year),
                    "peak_pop": s[-1][1], "confidence": "中",
                    "note": "人口已进入下降通道，峰值出现在观测期内或临近年份。"}
        return {"ok": True, "status": "growing", "peak_year": None,
                "confidence": "低", "recent_change_per_year": round(avg, 0),
                "note": "近 12 年人口仍净增长，按当前趋势短期内看不到峰值（>15 年）。"}
    # a < 0：增量逐年下降，求增量 = 0 的年份
    yzero = -b / a
    if yzero < last_year:
        return {"ok": True, "status": "declining", "peak_year": _fmt_year(last_year),
                "peak_pop": s[-1][1], "confidence": "中",
                "note": "人口增量已转负，峰值已过或就在当前。"}
    if yzero > last_year + HORIZON:
        return {"ok": True, "status": "growing", "peak_year": None, "confidence": "低",
                "note": "按趋势峰值在 15 年以外，外推不确定性过大，不给出具体年份。"}
    # 峰值人口：用最新值 + 剩余年份的平均增量（梯形近似）
    remaining = max(0, yzero - last_year)
    avg_now = ys[-1]
    peak_pop = s[-1][1] + avg_now * remaining / 2.0
    return {"ok": True, "status": "forecast", "peak_year": _fmt_year(yzero),
            "peak_year_ci": _ci(yzero, 3),
            "peak_pop": round(peak_pop), "confidence": "中高",
            "note": "按近 12 年人口增量下降趋势外推，增量归零年即峰值年。"}


def predict_aging(doc, iso):
    """老龄化拐点：a65 与 a0 两条线性趋势的交点。"""
    a65 = _series(doc, iso, "a65")
    a0 = _series(doc, iso, "a0")
    if len(a65) < MIN_POINTS or len(a0) < MIN_POINTS:
        return {"ok": False, "reason": "年龄结构数据不足"}
    # 对齐年份
    m65 = dict(a65)
    m0 = dict(a0)
    common = sorted(set(m65) & set(m0))[-12:]
    if len(common) < MIN_POINTS:
        return {"ok": False, "reason": "年龄结构年份不齐"}
    y65 = [m65[y] for y in common]
    y0 = [m0[y] for y in common]
    a1, b1 = _linfit(common, y65)
    a2, b2 = _linfit(common, y0)
    if abs(a1 - a2) < 1e-9:
        return {"ok": False, "reason": "两趋势近乎平行，无法求交点"}
    cross = (b2 - b1) / (a1 - a2)
    last = common[-1]
    cur65, cur0 = y65[-1], y0[-1]
    if cur65 >= cur0:
        return {"ok": True, "status": "crossed", "cross_year": _fmt_year(last),
                "confidence": "高", "a65": round(cur65, 1), "a0": round(cur0, 1),
                "note": "老年占比已超过少儿占比，拐点已在观测期内。"}
    if cross > last + HORIZON:
        return {"ok": True, "status": "later", "cross_year": None, "confidence": "低",
                "a65": round(cur65, 1), "a0": round(cur0, 1),
                "note": "按当前趋势拐点在 15 年以外，外推不可靠。"}
    return {"ok": True, "status": "forecast", "cross_year": _fmt_year(cross),
            "cross_year_ci": _ci(cross, 2), "confidence": "中高",
            "a65": round(cur65, 1), "a0": round(cur0, 1),
            "note": "65 岁以上占比与 0-14 岁占比的线性趋势交点。"}


def predict_convergence(doc, iso, ref=None):
    """人均GDP收敛：按近 10 年复合增速外推，算追上参照国/阈值的年份。"""
    pc = _series(doc, iso, "pc")
    if len(pc) < MIN_POINTS:
        return {"ok": False, "reason": "人均GDP数据不足"}
    g = _cagr(pc, 10)
    if g is None or g <= 0:
        return {"ok": True, "status": "stagnant", "cagr": None, "confidence": "低",
                "note": "近 10 年人均GDP无正增长，无法做收敛外推。"}
    out = {"ok": True, "status": "ok", "cagr": round(g * 100, 2),
           "confidence": "中", "last_pc": round(pc[-1][1]), "last_year": pc[-1][0]}
    # 目标 1：固定阈值（高收入线，用 20000 美元作参考）
    target = 20000.0
    if pc[-1][1] < target:
        yrs = math.log(target / pc[-1][1]) / math.log(1 + g)
        if yrs <= HORIZON:
            out["high_income_year"] = _fmt_year(pc[-1][0] + yrs)
            out["high_income_ci"] = _ci(pc[-1][0] + yrs, 4)
    # 目标 2：参照国
    if ref and ref != iso:
        rpc = _series(doc, ref, "pc")
        if len(rpc) >= MIN_POINTS:
            rval = rpc[-1][1]
            rg = _cagr(rpc, 10) or 0.0
            last_y = pc[-1][0]
            # 解 (1+g)^n * pc0 = (1+rg)^n * r0
            denom = math.log((1 + g) / (1 + rg)) if (1 + rg) > 0 else None
            if denom and denom > 1e-9 and rval > pc[-1][1]:
                n = math.log(rval / pc[-1][1]) / denom
                if n <= HORIZON:
                    out["catch_up_year"] = _fmt_year(last_y + n)
                    out["catch_up_ci"] = _ci(last_y + n, 5)
                    out["ref_iso"] = ref
                    out["ref_name"] = doc["countries"].get(ref, {}).get("n", ref)
                else:
                    out["catch_up_year"] = None
                    out["catch_up_note"] = "按当前增速差需 %.0f 年才能追上，超出 15 年外推范围。" % n
            else:
                out["catch_up_year"] = None
                out["catch_up_note"] = "参照国增长更快或增速相近，按当前趋势追不上。"
    out["note"] = ("按近 10 年人均GDP复合增速 %.1f%%/年外推；"
                   "收敛预测假设增速维持，实际会受周期与政策影响。" % (g * 100))
    return out


def predict_structure(doc, iso):
    """城镇化与产业：urb 用饱和逻辑外推，三产占比用线性趋势。"""
    out = {}
    urb = _series(doc, iso, "urb")
    if len(urb) >= MIN_POINTS:
        # 逻辑斯蒂饱和：增速与剩余空间成正比
        last = urb[-1][1]
        tail = _tail(urb, 10)
        slope, _ = _linfit([x for x, _ in tail], [y for _, y in tail])
        cap = 90.0
        room = max(0.0, cap - last)
        # 年增 = slope*(room/(cap-last_at_tail_start)) 的简化：用近期斜率衰减
        recent_slope = slope if slope > 0 else 0.0
        proj = {}
        for h in (5, 10, 15):
            decay = room / max(room + recent_slope * h, 1e-6)
            val = last + recent_slope * h * (0.5 + 0.5 * decay)
            proj[str(h)] = round(min(cap, val), 1)
        out["urbanization"] = {"ok": True, "last": round(last, 1), "last_year": urb[-1][0],
                               "proj_5y": proj["5"], "proj_10y": proj["10"], "proj_15y": proj["15"],
                               "confidence": "中",
                               "note": "城镇化率趋向饱和（假设上限 90%），增速随剩余空间递减。"}
    else:
        out["urbanization"] = {"ok": False, "reason": "城镇化数据不足"}
    ind = {}
    for key, label in (("agr", "农业"), ("ind", "工业"), ("srv", "服务业")):
        s = _series(doc, iso, key)
        if len(s) >= MIN_POINTS:
            t = _tail(s, 12)
            a, b = _linfit([x for x, _ in t], [y for _, y in t])
            y10 = a * (t[-1][0] + 10) + b
            ind[key] = {"label": label, "last": round(t[-1][1], 1),
                        "proj_10y": round(max(0.0, y10), 1),
                        "trend_per_year": round(a, 2)}
        else:
            ind[key] = {"label": label, "ok": False}
    out["industry"] = {"ok": True, "items": ind,
                       "note": "三次产业占比近 12 年线性趋势（占比之和可能≠100，因数据年份略有差异）。"}
    return out


def predict_anomaly(doc, iso):
    """第二档·异常预警：最新值偏离自身线性趋势 2σ 以上。设约束避免误报。"""
    flags = []
    names = {"pc": "人均GDP", "gdp": "GDP总量", "pop": "人口", "le": "预期寿命",
             "urb": "城镇化", "a65": "老年占比", "agr": "农业占比", "ind": "工业占比", "srv": "服务业占比"}
    for key, label in names.items():
        s = _series(doc, iso, key)
        if len(s) < 16:      # 约束 1：至少 16 年才判异常
            continue
        xs = [x for x, _ in s]
        ys = [y for _, y in s]
        a, b = _linfit(xs, ys)
        resid = [y - (a * x + b) for x, y in zip(xs, ys)]
        sd = statistics.pstdev(resid)
        if sd <= 0:
            continue
        latest = resid[-1]
        z = latest / sd
        # 约束 2：偏离 >2σ 且 相对幅度 >5%（避免小基数误报）
        rel = abs(latest) / max(abs(ys[-1]), 1e-9)
        if abs(z) >= 2.0 and rel >= 0.05:
            flags.append({"indicator": key, "label": label,
                          "z": round(z, 2), "direction": "高于趋势" if latest > 0 else "低于趋势",
                          "latest": round(ys[-1], 2)})
    return {"ok": True, "flags": flags, "count": len(flags),
            "confidence": "参考性判断",
            "constraint": "至少 16 年数据 + 偏离自身趋势 2σ 以上 + 相对幅度 5% 以上",
            "note": "异常只表示统计偏离，不等于错误；请结合来源更新与事件判断。"}


def predict_trap_risk(doc, iso):
    """第二档·中等收入陷阱风险：多条件评分（明确为参考性判断）。"""
    pc = _series(doc, iso, "pc")
    if len(pc) < MIN_POINTS:
        return {"ok": False, "reason": "人均GDP数据不足"}
    last = pc[-1][1]
    # 约束 0：高收入国家不适用中等收入陷阱评分
    if last > 12000:
        return {"ok": True, "score": 0, "level": "不适用", "applicable": False,
                "confidence": "参考性判断", "last_pc": round(last),
                "note": "该国人均GDP已超过 $12,000，属高收入经济体，不适用中等收入陷阱评分。"}
    g = _cagr(pc, 10)
    urb = _series(doc, iso, "urb")
    urb_last = urb[-1][1] if urb else None
    conditions = []
    score = 0
    # 条件1：处于中等收入区间 1000-12000
    in_band = 1000 <= last <= 12000
    conditions.append({"name": "处于中等收入区间（$1k–12k）", "hit": in_band})
    if in_band:
        score += 1
    # 条件2：近 10 年人均GDP增速 < 3%
    slow = g is not None and g < 0.03
    conditions.append({"name": "近 10 年人均增速低于 3%", "hit": slow})
    if slow:
        score += 1
    # 条件3：城镇化 40%-75%（转型中段）
    mid_urb = urb_last is not None and 40 <= urb_last <= 75
    conditions.append({"name": "城镇化处于 40%–75% 转型中段", "hit": mid_urb})
    if mid_urb:
        score += 1
    # 条件4：增长停滞（近 5 年人均GDP增幅 < 10%）
    s5 = _tail(pc, 6)
    stagnant = len(s5) >= 2 and s5[-1][1] <= s5[0][1] * 1.10
    conditions.append({"name": "近 5 年人均GDP累计增幅 < 10%", "hit": stagnant})
    if stagnant:
        score += 1
    level = "高" if score >= 3 else ("中" if score == 2 else "低")
    return {"ok": True, "score": score, "level": level,
            "conditions": conditions, "confidence": "参考性判断",
            "note": "四条件评分，仅作结构性风险提示，不构成经济结论；"
                    "高收入国家通常不满足条件 1，评分为低。"}


def predict(iso, ref=None):
    """主入口：返回某国的完整预测结果。"""
    doc = _load()
    iso = (iso or "").upper()
    if iso not in doc["countries"]:
        return {"ok": False, "error": "国家代码不存在: %s" % iso}
    name = doc["countries"][iso].get("n", iso)
    result = {
        "ok": True, "iso": iso, "name": name,
        "years": [doc["years"][0], doc["years"][-1]],
        "generated_from": doc.get("fetched_at"),
        "tier1": {
            "population_peak": predict_population_peak(doc, iso),
            "aging": predict_aging(doc, iso),
            "convergence": predict_convergence(doc, iso, ref),
            "structure": predict_structure(doc, iso),
        },
        "tier2": {
            "anomaly": predict_anomaly(doc, iso),
            "trap_risk": predict_trap_risk(doc, iso),
        },
        "disclaimer": "第一档为趋势外推，给区间不给单点；第二档为参考性判断。"
                      "所有预测基于 2000-2025 年度数据，不构成投资或政策建议。",
    }
    return result


if __name__ == "__main__":
    import sys
    iso = sys.argv[1] if len(sys.argv) > 1 else "CHN"
    ref = sys.argv[2] if len(sys.argv) > 2 else None
    print(json.dumps(predict(iso, ref), ensure_ascii=False, indent=2))
