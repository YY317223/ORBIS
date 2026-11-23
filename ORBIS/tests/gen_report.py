#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 unittest 结果转成 HTML 测试报告（纯标准库）。

运行：先跑测试生成 _result.txt，再 python3 gen_report.py
输出：test_report.html
"""
import html
import os
import re
import datetime
from string import Template

HERE = os.path.dirname(os.path.abspath(__file__))
RESULT = os.path.join(HERE, "_result.txt")
OUT = os.path.join(HERE, "test_report.html")

with open(RESULT, encoding="utf-8") as f:
    raw = f.read()

# 解析每个用例：名称行 + 结果行
cases = []
lines = raw.splitlines()
for i, line in enumerate(lines):
    m = re.match(r"^(TC-[\w-]+)\s+(.+?)\s*\.\.\.\s*(ok|FAIL|ERROR|skipped.*)$", line)
    if m:
        code, title, status = m.groups()
        cases.append({"code": code, "title": title.strip(),
                      "status": "PASS" if status == "ok" else status.upper()})
# 兼容 text 在上一行的格式（unittest verbosity=2 会分两行）
if not cases:
    for i, line in enumerate(lines):
        if line.startswith("TC-") and i + 1 < len(lines):
            m2 = re.search(r"\.\.\.\s*(ok|FAIL|ERROR)", lines[i + 1])
            if m2:
                code, title = line.split(" ", 1)
                cases.append({"code": code, "title": title.strip(),
                              "status": "PASS" if m2.group(1) == "ok" else m2.group(1)})

total = len(cases)
passed = sum(1 for c in cases if c["status"] == "PASS")
failed = total - passed
rate = (passed / total * 100) if total else 0
now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

rows = "".join(
    '<tr><td class="mono">%s</td><td>%s</td><td><span class="badge %s">%s</span></td></tr>'
    % (html.escape(c["code"]), html.escape(c["title"]),
       "pass" if c["status"] == "PASS" else "fail", c["status"])
    for c in cases
)

doc = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>ORBIS 测试报告</title>
<style>
*{box-sizing:border-box}body{margin:0;font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:#0d1218;color:#dfe9ef}
.wrap{max-width:900px;margin:0 auto;padding:40px 24px}
h1{font-size:28px;margin:0 0 6px;color:#f2f5f7;letter-spacing:.04em}
.sub{color:#8a9aa6;font-size:13px;margin-bottom:32px}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:32px}
.card{background:#151d26;border:1px solid #253242;border-radius:12px;padding:18px}
.card .k{font-size:11px;color:#8a9aa6;letter-spacing:.08em}
.card .v{font-size:30px;font-weight:600;margin-top:6px;font-variant-numeric:tabular-nums}
.card.pass .v{color:#5DCAA5}.card.fail .v{color:#E24B4A}.card.rate .v{color:#F0A868}
h2{font-size:16px;margin:0 0 14px;color:#f2f5f7;border-left:3px solid #F0A868;padding-left:10px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:10px 12px;color:#8a9aa6;font-weight:500;border-bottom:1px solid #253242}
td{padding:9px 12px;border-bottom:1px solid #1c2733}
.mono{font-family:ui-monospace,Consolas,monospace;color:#9fb4c4;font-size:12px}
.badge{display:inline-block;padding:2px 9px;border-radius:5px;font-size:11px}
.badge.pass{background:rgba(93,202,165,.14);color:#5DCAA5}
.badge.fail{background:rgba(226,75,74,.14);color:#E24B4A}
.note{margin-top:26px;padding:14px 16px;border:1px dashed #2c3b4b;border-radius:10px;color:#8a9aa6;font-size:12px;line-height:1.8}
@media(max-width:640px){.cards{grid-template-columns:repeat(2,1fr)}}
</style></head><body><div class="wrap">
<h1>ORBIS · 测试报告</h1>
<div class="sub">生成时间：$now · Python unittest · 纯标准库</div>
<div class="cards">
  <div class="card"><div class="k">用例总数</div><div class="v">$total</div></div>
  <div class="card pass"><div class="k">通过</div><div class="v">$passed</div></div>
  <div class="card fail"><div class="k">失败</div><div class="v">$failed</div></div>
  <div class="card rate"><div class="k">通过率</div><div class="v">$rate</div></div>
</div>
<h2>测试用例明细</h2>
<table><thead><tr><th>编号</th><th>用例名称</th><th>结果</th></tr></thead><tbody>$rows</tbody></table>
<div class="note">
<b>测试范围</b>：接口契约（状态/数据/汇率/预测/鉴权）、数据完整性（261国×26年×10指标）、
预测边界（高收入国家不适用陷阱评分、非法国家不崩溃）、审核流程（批次创建/驳回/摘要/重复发布防护）。<br>
<b>测试驱动修复</b>：TC-PRED-005 发现 tier1.structure 顶层缺少 confidence/note，
与其他预测项结构不一致，已修复 predict.py 并回归通过。<br>
<b>未覆盖</b>：前端动画（headless 下 rAF 冻结，改用逻辑断言）、性能压测、SMTP 真实发信（未配置）。
</div>
</div></body></html>
"""
subst = Template(doc).substitute(now=now, total=total, passed=passed, failed=failed,
                                   rate="%.0f" % rate, rows=rows)

with open(OUT, "w", encoding="utf-8") as f:
    f.write(subst)
print("wrote", OUT, "| cases=%d pass=%d fail=%d rate=%.0f%%" % (total, passed, failed, rate))
