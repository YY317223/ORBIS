# ORBIS 测试用例表

## 文档说明

本文档为 ORBIS·从太空看地球项目的测试用例集，用于答辩展示与测试交接。测试采用 Python 标准库 unittest + urllib 实现，测试服务端口 18790，生成日期 2026-11-23。全部 21 条用例均已执行通过，通过率 100%。

## 测试执行汇总

| 测试分类 | 用例数 | 通过数 | 失败数 | 通过率 |
|---|---|---|---|---|
| 基础接口 | 4 | 4 | 0 | 100% |
| 预测接口 | 6 | 6 | 0 | 100% |
| 鉴权边界 | 3 | 3 | 0 | 100% |
| 数据完整性 | 4 | 4 | 0 | 100% |
| 审核流程 | 4 | 4 | 0 | 100% |
| 合计 | 21 | 21 | 0 | 100% |

## 一、基础接口测试

| 编号 | 用例名称 | 前置条件 | 测试步骤 | 预期结果 | 优先级 | 实测结果 |
|---|---|---|---|---|---|---|
| TC-API-001 | 状态接口返回必需字段 | 服务已启动 | GET /api/status | HTTP 200；ok=true；含 last_fetch/age_hours/source_updated | P0 | 通过 |
| TC-API-002 | 世行数据规模校验 | wb.json 就绪 | GET /api/wb，检查 years/countries/indicators | 26 年（2000-2025）；≥260 国；10 指标 | P0 | 通过 |
| TC-API-003 | 汇率接口返回币种快照 | fx.json 就绪 | GET /api/fx | 200；含 currencies 字段；币种数 >100 | P0 | 通过 |
| TC-API-004 | 国家详情接口-中国 | wb.json 就绪 | GET /api/country/detail?iso=CHN | 200；ok 不为 false | P1 | 通过 |

## 二、预测接口测试

| 编号 | 用例名称 | 前置条件 | 测试步骤 | 预期结果 | 优先级 | 实测结果 |
|---|---|---|---|---|---|---|
| TC-PRED-001 | 中国预测返回完整两级结构 | wb.json 就绪 | GET /api/predict?iso=CHN | 200；tier1 四项与 tier2 两项齐全；含 disclaimer | P0 | 通过 |
| TC-PRED-002 | 带参照国的收敛预测 | wb.json 就绪 | GET /api/predict?iso=IND&ref=CHN | 200；convergence 含 cagr | P0 | 通过 |
| TC-PRED-003 | 非法 iso 不崩溃 | 服务已启动 | GET /api/predict?iso=XXX | 200；ok=false；含 error（非 500） | P0 | 通过 |
| TC-PRED-004 | 高收入国家陷阱评分边界 | wb.json 就绪 | GET /api/predict?iso=JPN | trap_risk.level = 不适用（日本人均>12k） | P0 | 通过 |
| TC-PRED-005 | 预测项均带 confidence/note | wb.json 就绪 | GET /api/predict?iso=USA，遍历 tier1/tier2 | 每项含 confidence 与 note（发现 structure 缺失后已修复） | P0 | 通过 |
| TC-PRED-006 | 预测区间与数据年份 | wb.json 就绪 | GET /api/predict?iso=CHN，检查 years/peak_year_ci | years=[2000,2025]；forecast 态含 2 元素区间 | P1 | 通过 |

## 三、鉴权边界测试

| 编号 | 用例名称 | 前置条件 | 测试步骤 | 预期结果 | 优先级 | 实测结果 |
|---|---|---|---|---|---|---|
| TC-AUTH-001 | 未登录访问管理接口被拒 | 无管理员 cookie | GET /api/admin/users | 返回 401/403/302，不泄露用户列表 | P0 | 通过 |
| TC-AUTH-002 | 管理员正确密码登录 | admin/orbis2026 | POST /api/admin/login 正确凭据 | 200；ok=true | P0 | 通过 |
| TC-AUTH-003 | 错误密码登录失败 | 错误密码 | POST /api/admin/login 错误凭据 | ok=false 或拒绝 | P0 | 通过 |

## 四、数据完整性测试

| 编号 | 用例名称 | 前置条件 | 测试步骤 | 预期结果 | 优先级 | 实测结果 |
|---|---|---|---|---|---|---|
| TC-DATA-001 | 各国指标数组长度对齐 | wb.json 就绪 | 遍历 261 国×10 指标，比对 len 与 years 长度 | 全部 = 26，无不齐 | P0 | 通过 |
| TC-DATA-002 | 中国人口 2022 转负 | wb.json 就绪 | 读取 CHN.pop 的 2021/2022 差值 | 2021 增量为正；2022 增量为负 | P1 | 通过 |
| TC-DATA-003 | 日本老龄化拐点已过 | wb.json 就绪 | 调用 predict_aging(JPN) | status=crossed | P1 | 通过 |
| TC-DATA-004 | 缺测国家不崩溃 | wb.json 就绪 | predict(AKT) 空数据国家 | ok=false 且给 reason/error，不抛异常 | P1 | 通过 |

## 五、审核流程测试

| 编号 | 用例名称 | 前置条件 | 测试步骤 | 预期结果 | 优先级 | 实测结果 |
|---|---|---|---|---|---|---|
| TC-FLOW-001 | 批次创建-列表-详情 | 临时暂存区 | staging.create → list_batches → get_batch | 1 个批次；status=pending；fx.json publishable | P0 | 通过 |
| TC-FLOW-002 | 驳回批次清空列表 | 已有待审批次 | staging.reject(bid) | ok=true；列表清空 | P0 | 通过 |
| TC-FLOW-003 | 摘要生成正确 | 临时暂存区 | create(wb.json 假数据) → get_batch | countries=2；events=1；years=[2000,2025] | P1 | 通过 |
| TC-FLOW-004 | 重复发布防护 | 临时发布目标 | publish(bid) 两次 | 第一次成功；第二次 ok=false 含"已发布" | P0 | 通过 |

## 覆盖说明与测试驱动修复

测试范围覆盖接口契约（状态、数据、汇率、预测、鉴权）、数据完整性（261 国 × 26 年 × 10 指标）、预测边界（高收入国家陷阱评分必须"不适用"、非法国家不崩溃）、审核流程（创建、驳回、摘要、重复发布防护）四个维度。

其中 TC-PRED-005 是一例测试驱动修复：执行时发现 tier1.structure 顶层缺少 confidence 与 note 字段，与其他预测项结构不一致。据此修复 predict.py 的 predict_structure() 函数，补齐顶层字段后回归通过，并同步至线上。这体现了测试对接口一致性的守护作用。

未覆盖范围：前端动画（headless 环境下 requestAnimationFrame 被冻结，改用逻辑断言而非像素比对）、性能压测、SMTP 真实发信（当前未配置，邮件落盘至 outbox 目录）。
