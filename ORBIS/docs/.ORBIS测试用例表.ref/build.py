# -*- coding: utf-8 -*-
"""ORBIS 测试用例表：汇总 + 用例明细，openpyxl 一次生成。"""
try:
    import openpyxl
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "openpyxl>=3.1.0"])
    import openpyxl

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.formatting.rule import CellIsRule
from openpyxl.utils import get_column_letter


def xl_color(css_hex: str) -> str:
    value = css_hex.removeprefix("#").upper()
    if len(value) != 6:
        raise ValueError("Expected #RRGGBB, got: " + css_hex)
    return "FF" + value


XL_HEADER = xl_color("#2F5597")     # 深蓝表头
XL_HEADER_FONT = xl_color("#FFFFFF")
XL_TITLE = xl_color("#1F3864")
XL_LIGHT = xl_color("#D9E2F3")      # 浅蓝
XL_GRAY = xl_color("#F2F2F2")
XL_BORDER = xl_color("#BFBFBF")
XL_PASS_BG = xl_color("#C6EFCE")
XL_PASS_FONT = xl_color("#006100")
XL_FAIL_BG = xl_color("#FFC7CE")
XL_FAIL_FONT = xl_color("#9C0006")
XL_WARN_BG = xl_color("#FFEB9C")

thin = Side(style="thin", color=XL_BORDER)
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)

# ============ 数据：21 条真实测试用例 ============
# 编号, 分类, 用例名称, 前置条件, 测试步骤, 预期结果, 优先级, 实测结果
CASES = [
    ("TC-API-001", "基础接口", "状态接口返回必需字段", "服务已启动",
     "GET /api/status", "HTTP 200；ok=true；含 last_fetch/age_hours/source_updated", "P0", "通过"),
    ("TC-API-002", "基础接口", "世行数据规模校验", "wb.json 就绪",
     "GET /api/wb，检查 years/countries/indicators", "26 年(2000-2025)；≥260 国；10 指标", "P0", "通过"),
    ("TC-API-003", "基础接口", "汇率接口返回币种快照", "fx.json 就绪",
     "GET /api/fx", "200；含 currencies 字段；币种数 >100", "P0", "通过"),
    ("TC-API-004", "基础接口", "国家详情接口-中国", "wb.json 就绪",
     "GET /api/country/detail?iso=CHN", "200；ok 不为 false", "P1", "通过"),

    ("TC-PRED-001", "预测接口", "中国预测返回完整两级结构", "wb.json 就绪",
     "GET /api/predict?iso=CHN", "200；tier1 四项+tier2 两项齐全；含 disclaimer", "P0", "通过"),
    ("TC-PRED-002", "预测接口", "带参照国的收敛预测", "wb.json 就绪",
     "GET /api/predict?iso=IND&ref=CHN", "200；convergence 含 cagr", "P0", "通过"),
    ("TC-PRED-003", "预测接口", "非法 iso 不崩溃", "服务已启动",
     "GET /api/predict?iso=XXX", "200；ok=false；含 error（非 500）", "P0", "通过"),
    ("TC-PRED-004", "预测接口", "高收入国家陷阱评分边界", "wb.json 就绪",
     "GET /api/predict?iso=JPN", "trap_risk.level = 不适用（日本人均>12k）", "P0", "通过"),
    ("TC-PRED-005", "预测接口", "预测项均带 confidence/note", "wb.json 就绪",
     "GET /api/predict?iso=USA，遍历 tier1/tier2", "每项含 confidence 与 note（发现 structure 缺失后已修复）", "P0", "通过"),
    ("TC-PRED-006", "预测接口", "预测区间与数据年份", "wb.json 就绪",
     "GET /api/predict?iso=CHN，检查 years/peak_year_ci", "years=[2000,2025]；forecast 态含 2 元素区间", "P1", "通过"),

    ("TC-AUTH-001", "鉴权边界", "未登录访问管理接口被拒", "无管理员 cookie",
     "GET /api/admin/users", "返回 401/403/302，不泄露用户列表", "P0", "通过"),
    ("TC-AUTH-002", "鉴权边界", "管理员正确密码登录", "admin/orbis2026",
     "POST /api/admin/login 正确凭据", "200；ok=true", "P0", "通过"),
    ("TC-AUTH-003", "鉴权边界", "错误密码登录失败", "错误密码",
     "POST /api/admin/login 错误凭据", "ok=false 或拒绝", "P0", "通过"),

    ("TC-DATA-001", "数据完整性", "各国指标数组长度对齐", "wb.json 就绪",
     "遍历 261 国×10 指标，比对 len 与 years 长度", "全部 = 26，无不齐", "P0", "通过"),
    ("TC-DATA-002", "数据完整性", "中国人口 2022 转负", "wb.json 就绪",
     "读取 CHN.pop 的 2021/2022 差值", "2021 增量>0；2022 增量<0", "P1", "通过"),
    ("TC-DATA-003", "数据完整性", "日本老龄化拐点已过", "wb.json 就绪",
     "调用 predict_aging(JPN)", "status=crossed", "P1", "通过"),
    ("TC-DATA-004", "数据完整性", "缺测国家不崩溃", "wb.json 就绪",
     "predict(AKT) 空数据国家", "ok=false 且给 reason/error，不抛异常", "P1", "通过"),

    ("TC-FLOW-001", "审核流程", "批次创建-列表-详情", "临时暂存区",
     "staging.create → list_batches → get_batch", "1 个批次；status=pending；fx.json publishable", "P0", "通过"),
    ("TC-FLOW-002", "审核流程", "驳回批次清空列表", "已有待审批次",
     "staging.reject(bid)", "ok=true；列表清空", "P0", "通过"),
    ("TC-FLOW-003", "审核流程", "摘要生成正确", "临时暂存区",
     "create(wb.json 假数据) → get_batch", "countries=2；events=1；years=[2000,2025]", "P1", "通过"),
    ("TC-FLOW-004", "审核流程", "重复发布防护", "临时发布目标",
     "publish(bid) 两次", "第一次成功；第二次 ok=false 含'已发布'", "P0", "通过"),
]

wb = Workbook()
wb.properties.title = "ORBIS测试用例表"

# ---------- Sheet 1: 测试汇总 ----------
ws = wb.active
ws.title = "测试汇总"
ws.merge_cells("A1:E1")
ws["A1"] = "ORBIS 测试用例执行汇总"
ws["A1"].font = Font(size=16, bold=True, color=XL_TITLE)
ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws.row_dimensions[1].height = 30

ws.merge_cells("A2:E2")
ws["A2"] = "测试方式：Python unittest + urllib（纯标准库） · 测试服务 PORT=18790 · 生成日期 2026-11-23"
ws["A2"].font = Font(size=10, color=XL_HEADER)
ws["A2"].alignment = Alignment(horizontal="center")

# 锚点：第4行表头，第5-11行分类数据，第12行合计
headers = ["测试分类", "用例数", "通过数", "失败数", "通过率"]
for c, h in enumerate(headers, 1):
    cell = ws.cell(row=4, column=c, value=h)
    cell.font = Font(bold=True, color=XL_HEADER_FONT)
    cell.fill = PatternFill("solid", fgColor=XL_HEADER)
    cell.alignment = Alignment(horizontal="center", vertical="center")
    cell.border = BORDER

cats = []
for row in CASES:
    if row[1] not in cats:
        cats.append(row[1])

r = 5
for cat in cats:
    ws.cell(row=r, column=1, value=cat)
    ws.cell(row=r, column=2, value='=COUNTIF(测试用例!B:B,A%d)' % r)
    ws.cell(row=r, column=3, value='=COUNTIFS(测试用例!B:B,A%d,测试用例!H:H,"通过")' % r)
    ws.cell(row=r, column=4, value='=COUNTIFS(测试用例!B:B,A%d,测试用例!H:H,"失败")' % r)
    ws.cell(row=r, column=5, value='=IF(OR(B%d="",B%d=0),"",C%d/B%d)' % (r, r, r, r))
    ws.cell(row=r, column=5).number_format = "0.0%"
    for c in range(1, 6):
        ws.cell(row=r, column=c).border = BORDER
        ws.cell(row=r, column=c).alignment = Alignment(horizontal="center")
    r += 1

total_row = r
ws.cell(row=total_row, column=1, value="合计")
ws.cell(row=total_row, column=2, value="=SUM(B5:B%d)" % (total_row - 1))
ws.cell(row=total_row, column=3, value="=SUM(C5:C%d)" % (total_row - 1))
ws.cell(row=total_row, column=4, value="=SUM(D5:D%d)" % (total_row - 1))
ws.cell(row=total_row, column=5, value='=IF(OR(B%d="",B%d=0),"",C%d/B%d)' % (total_row, total_row, total_row, total_row))
ws.cell(row=total_row, column=5).number_format = "0.0%"
for c in range(1, 6):
    cell = ws.cell(row=total_row, column=c)
    cell.font = Font(bold=True, color=XL_HEADER_FONT)
    cell.fill = PatternFill("solid", fgColor=XL_HEADER)
    cell.border = BORDER
    cell.alignment = Alignment(horizontal="center")

note_row = total_row + 2
ws.merge_cells(start_row=note_row, start_column=1, end_row=note_row, end_column=5)
ws.cell(row=note_row, column=1,
        value="说明：TC-PRED-005 曾发现 structure 顶层缺 confidence/note，已修复 predict.py 并回归通过——测试驱动修复实例。")
ws.cell(row=note_row, column=1).font = Font(size=10, color=XL_FAIL_FONT)
ws.cell(row=note_row, column=1).alignment = Alignment(wrap_text=True, vertical="center")
ws.row_dimensions[note_row].height = 30

ws.column_dimensions["A"].width = 16
ws.column_dimensions["B"].width = 12
ws.column_dimensions["C"].width = 12
ws.column_dimensions["D"].width = 12
ws.column_dimensions["E"].width = 12
ws.freeze_panes = "A5"

# ---------- Sheet 2: 测试用例 ----------
ws2 = wb.create_sheet("测试用例")
cols = ["用例编号", "分类", "用例名称", "前置条件", "测试步骤", "预期结果", "优先级", "实测结果"]
widths = [14, 12, 26, 18, 30, 42, 9, 11]

# 第1行表头
for c, (h, w) in enumerate(zip(cols, widths), 1):
    cell = ws2.cell(row=1, column=c, value=h)
    cell.font = Font(bold=True, color=XL_HEADER_FONT)
    cell.fill = PatternFill("solid", fgColor=XL_HEADER)
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = BORDER
    ws2.column_dimensions[get_column_letter(c)].width = w
ws2.row_dimensions[1].height = 24

# 第2行起数据
for i, row in enumerate(CASES, start=2):
    for c, val in enumerate(row, 1):
        cell = ws2.cell(row=i, column=c, value=val)
        cell.border = BORDER
        cell.alignment = Alignment(vertical="center", wrap_text=(c in (3, 4, 5, 6)),
                                   horizontal="center" if c in (1, 2, 7, 8) else "left")
        if i % 2 == 0:
            cell.fill = PatternFill("solid", fgColor=XL_GRAY)
    # 优先级着色
    pc = ws2.cell(row=i, column=7)
    if row[6] == "P0":
        pc.fill = PatternFill("solid", fgColor=XL_WARN_BG)
    # 结果着色（条件格式也会覆盖，这里静态兜底）
    rc = ws2.cell(row=i, column=8)
    if row[7] == "通过":
        rc.fill = PatternFill("solid", fgColor=XL_PASS_BG)
        rc.font = Font(color=XL_PASS_FONT, bold=True)

last_row = 1 + len(CASES)
# 条件格式：结果列 通过/失败
ws2.conditional_formatting.add(
    "H2:H%d" % last_row,
    CellIsRule(operator="equal", formula=['"通过"'],
               fill=PatternFill("solid", fgColor=XL_PASS_BG),
               font=Font(color=XL_PASS_FONT, bold=True)))
ws2.conditional_formatting.add(
    "H2:H%d" % last_row,
    CellIsRule(operator="equal", formula=['"失败"'],
               fill=PatternFill("solid", fgColor=XL_FAIL_BG),
               font=Font(color=XL_FAIL_FONT, bold=True)))

ws2.auto_filter.ref = "A1:H%d" % last_row
ws2.freeze_panes = "A2"
ws2.sheet_view.showGridLines = False

# 打印设置（横向、一页宽）
ws2.page_setup.orientation = "landscape"
ws2.page_setup.fitToWidth = 1
ws2.sheet_properties.pageSetUpPr.fitToPage = True
ws.print_area = "A1:E%d" % note_row

out = "C:/0_workspace/项目二2/ORBIS/docs/ORBIS测试用例表.xlsx"
wb.save(out)
print("wrote", out, "| cases=%d" % len(CASES))
