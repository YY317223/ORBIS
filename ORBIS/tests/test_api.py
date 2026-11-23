#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ORBIS 接口契约测试（纯标准库 unittest + urllib）。

覆盖：正常返回结构、参数缺失、非法国家、鉴权边界、预测边界。
运行前需启动测试服务：PORT=18790 python3 app.py（在 backend/ 下）
"""
import json
import os
import unittest
import urllib.error
import urllib.request

BASE = os.environ.get("TEST_BASE", "http://127.0.0.1:18790")


def get(path, timeout=20):
    try:
        with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, None


def post(path, payload, cookie=None, timeout=30):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=data,
                                 headers={"Content-Type": "application/json"})
    if cookie:
        req.add_header("Cookie", cookie)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8")), r.headers.get("Set-Cookie")
    except urllib.error.HTTPError as e:
        return e.code, None, None


class TestBasicAPI(unittest.TestCase):
    """基础数据接口"""

    def test_001_status_structure(self):
        """TC-API-001 状态接口返回必需字段"""
        code, d = get("/api/status")
        self.assertEqual(code, 200)
        self.assertTrue(d.get("ok"))
        for k in ("last_fetch", "age_hours", "source_updated"):
            self.assertIn(k, d, "status 缺少字段: %s" % k)

    def test_002_wb_data_scale(self):
        """TC-API-002 世行数据规模 261国×26年×10指标"""
        code, d = get("/api/wb")
        self.assertEqual(code, 200)
        self.assertEqual(len(d["years"]), 26)
        self.assertGreaterEqual(len(d["countries"]), 260)
        self.assertEqual(len(d["indicators"]), 10)
        self.assertEqual(d["years"][0], 2000)
        self.assertEqual(d["years"][-1], 2025)

    def test_003_fx_structure(self):
        """TC-API-003 汇率接口返回币种快照"""
        code, d = get("/api/fx")
        self.assertEqual(code, 200)
        self.assertIn("currencies", d)
        self.assertGreater(len(d["currencies"]), 100)

    def test_004_country_detail(self):
        """TC-API-004 国家详情接口-中国"""
        code, d = get("/api/country/detail?iso=CHN")
        self.assertEqual(code, 200)
        self.assertTrue(d.get("ok") is not False)


class TestPredictAPI(unittest.TestCase):
    """预测接口（重点模块）"""

    def test_010_predict_normal(self):
        """TC-PRED-001 中国预测返回完整两级结构"""
        code, d = get("/api/predict?iso=CHN")
        self.assertEqual(code, 200)
        self.assertTrue(d.get("ok"))
        self.assertEqual(d["iso"], "CHN")
        for k in ("population_peak", "aging", "convergence", "structure"):
            self.assertIn(k, d["tier1"], "tier1 缺少: %s" % k)
        for k in ("anomaly", "trap_risk"):
            self.assertIn(k, d["tier2"], "tier2 缺少: %s" % k)
        self.assertIn("disclaimer", d)

    def test_011_predict_with_ref(self):
        """TC-PRED-002 带参照国的收敛预测"""
        code, d = get("/api/predict?iso=IND&ref=CHN")
        self.assertEqual(code, 200)
        self.assertTrue(d.get("ok"))
        cv = d["tier1"]["convergence"]
        self.assertIn("cagr", cv)

    def test_012_predict_invalid_iso(self):
        """TC-PRED-003 非法 iso 返回 ok:false 而非 500"""
        code, d = get("/api/predict?iso=XXX")
        self.assertEqual(code, 200)
        self.assertFalse(d.get("ok"))
        self.assertIn("error", d)

    def test_013_predict_high_income_trap_na(self):
        """TC-PRED-004 高收入国家陷阱评分必须为'不适用'（边界约束）"""
        code, d = get("/api/predict?iso=JPN")
        self.assertEqual(code, 200)
        trap = d["tier2"]["trap_risk"]
        self.assertEqual(trap["level"], "不适用", "日本人均>12k，不应评陷阱风险")

    def test_014_predict_confidence_present(self):
        """TC-PRED-005 每个预测项都带 confidence 与 note"""
        code, d = get("/api/predict?iso=USA")
        self.assertEqual(code, 200)
        for name, item in list(d["tier1"].items()) + list(d["tier2"].items()):
            if isinstance(item, dict):
                self.assertIn("confidence", item, "%s 缺少 confidence" % name)
                self.assertIn("note", item, "%s 缺少 note" % name)

    def test_015_predict_year_range(self):
        """TC-PRED-006 预测基于 2000-2025，给区间不给单点"""
        code, d = get("/api/predict?iso=CHN")
        self.assertEqual(d["years"], [2000, 2025])
        pp = d["tier1"]["population_peak"]
        if pp.get("status") == "forecast":
            self.assertIn("peak_year_ci", pp)
            self.assertEqual(len(pp["peak_year_ci"]), 2)


class TestAuthBoundary(unittest.TestCase):
    """鉴权边界"""

    def test_020_admin_without_auth(self):
        """TC-AUTH-001 未登录访问管理接口被拒绝"""
        code, d = get("/api/admin/users")
        self.assertIn(code, (401, 403, 302), "未登录不应能读用户列表")

    def test_021_admin_login_ok(self):
        """TC-AUTH-002 管理员正确密码登录成功"""
        code, d, cookie = post("/api/admin/login",
                               {"username": "admin", "password": "orbis2026"})
        self.assertEqual(code, 200)
        self.assertTrue(d.get("ok"))

    def test_022_admin_login_wrong(self):
        """TC-AUTH-003 错误密码登录失败"""
        code, d, _ = post("/api/admin/login",
                          {"username": "admin", "password": "wrong-pass"})
        self.assertIn(code, (200, 401, 403))
        if code == 200:
            self.assertFalse(d.get("ok"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
