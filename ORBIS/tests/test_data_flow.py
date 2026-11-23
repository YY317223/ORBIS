#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ORBIS 数据正确性与审核流程测试。

数据测试直接读 wb.json；流程测试直接调 staging/predict 模块，不依赖服务。
"""
import json
import os
import shutil
import sys
import unittest

BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
sys.path.insert(0, BACKEND)

import predict  # noqa: E402
import staging  # noqa: E402


class TestDataIntegrity(unittest.TestCase):
    """数据完整性"""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(BACKEND, "data", "wb.json"), encoding="utf-8") as f:
            cls.doc = json.load(f)

    def test_030_array_length_aligned(self):
        """TC-DATA-001 各国指标数组长度 = 年份数"""
        n = len(self.doc["years"])
        bad = []
        for iso, c in self.doc["countries"].items():
            for k in self.doc["indicators"]:
                if k in c and len(c[k]) != n:
                    bad.append("%s.%s=%d" % (iso, k, len(c[k])))
        self.assertEqual(bad, [], "数组长度不齐: %s" % bad[:5])

    def test_031_china_population_turning_negative(self):
        """TC-DATA-002 中国人口 2022 起转负（已知事实校验）"""
        s = predict._series(self.doc, "CHN", "pop")
        d = dict(s)
        self.assertGreater(d[2021] - d[2020], 0, "2021 人口应仍正增长")
        self.assertLess(d[2022] - d[2021], 0, "2022 人口应转负")

    def test_032_japan_aging_crossed(self):
        """TC-DATA-003 日本老龄化拐点已过"""
        r = predict.predict_aging(self.doc, "JPN")
        self.assertEqual(r["status"], "crossed")

    def test_033_predict_boundary_incomplete_data(self):
        """TC-DATA-004 缺测严重的国家不崩溃，返回 ok:false 或合理结果"""
        r = predict.predict("AKT")  # Akrotiri，数据基本为空
        self.assertIn("ok", r)
        if not r["ok"]:
            self.assertTrue("reason" in r or "error" in r, "失败时应给出原因")


class TestStagingFlow(unittest.TestCase):
    """数据审核通道：创建→差异→驳回"""

    def setUp(self):
        # 每个测试独立暂存区，避免污染真实数据
        self.orig_stage = staging.STAGE
        self.tmp_stage = os.path.join(os.path.dirname(self.orig_stage), "_test_staging")
        shutil.rmtree(self.tmp_stage, ignore_errors=True)
        staging.STAGE = self.tmp_stage
        staging.INDEX = os.path.join(self.tmp_stage, "index.json")

    def tearDown(self):
        shutil.rmtree(self.tmp_stage, ignore_errors=True)
        staging.STAGE = self.orig_stage
        staging.INDEX = os.path.join(self.orig_stage, "index.json")

    def test_040_staging_create_list_get(self):
        """TC-FLOW-001 创建批次→列表可见→详情完整"""
        ok, meta = staging.create(source="unittest", note="测试批次",
                                  files={"fx.json": {"date": "2026-11-23",
                                                     "currencies": {"USD": 1.0}}})
        self.assertTrue(ok, meta)
        rows = staging.list_batches()
        self.assertEqual(len(rows), 1)
        detail = staging.get_batch(meta["id"])
        self.assertEqual(detail["status"], "pending")
        self.assertIn("fx.json", detail["files_detail"])
        self.assertTrue(detail["files_detail"]["fx.json"]["publishable"])

    def test_041_staging_reject(self):
        """TC-FLOW-002 驳回批次后列表清空"""
        ok, meta = staging.create(source="unittest", files={"fx.json": {"date": "x"}})
        self.assertTrue(ok)
        ok2, _ = staging.reject(meta["id"])
        self.assertTrue(ok2)
        self.assertEqual(len(staging.list_batches()), 0)

    def test_042_staging_summary(self):
        """TC-FLOW-003 摘要生成正确（wb 按国家数/事件数）"""
        fake = {"fetched_at": "2026-11-23T10:00:00+08:00", "years": [2000, 2025],
                "countries": {"CHN": {}, "USA": {}}, "events": [{}]}
        ok, meta = staging.create(source="unittest", files={"wb.json": fake})
        self.assertTrue(ok)
        detail = staging.get_batch(meta["id"])
        s = detail["files_detail"]["wb.json"]["summary"]
        self.assertEqual(s["countries"], 2)
        self.assertEqual(s["events"], 1)
        self.assertEqual(s["years"], [2000, 2025])

    def test_043_staging_duplicate_publish_guard(self):
        """TC-FLOW-004 已发布批次不能重复发布"""
        # 用临时目标路径，避免碰真实 wb.json
        orig_targets = dict(staging.PUBLISH_TARGETS)
        tmp_target = os.path.join(self.tmp_stage, "published_fx.json")
        staging.PUBLISH_TARGETS = {"fx.json": tmp_target}
        try:
            ok, meta = staging.create(source="unittest", files={"fx.json": {"date": "2026-11-23"}})
            self.assertTrue(ok)
            ok1, _ = staging.publish(meta["id"])
            self.assertTrue(ok1)
            ok2, err = staging.publish(meta["id"])
            self.assertFalse(ok2)
            self.assertIn("已发布", err)
        finally:
            staging.PUBLISH_TARGETS = orig_targets


if __name__ == "__main__":
    unittest.main(verbosity=2)
